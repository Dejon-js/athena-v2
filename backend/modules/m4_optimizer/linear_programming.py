import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import pulp
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import structlog

from modules.m4_optimizer.constraints import ConstraintManager
from modules.m4_optimizer.objective_function import ObjectiveFunction
from shared.config import settings
from shared.database import redis_client

logger = structlog.get_logger()


class LinearProgrammingOptimizer:
    """
    PuLP-based linear programming optimizer for DFS lineup construction.
    Generates 150-lineup portfolio maximizing leveraged ceiling.
    """
    
    def __init__(self):
        self.constraint_manager = ConstraintManager()
        self.objective_function = ObjectiveFunction()
        self.lineup_count = settings.lineup_count
        self.salary_cap = settings.salary_cap
        self.timeout_minutes = settings.optimization_timeout_minutes
        
    async def optimize_lineups(
        self, 
        projections: List[Dict[str, Any]], 
        ownership_data: List[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate optimized lineup portfolio.
        
        Args:
            projections: Player projections from Module 2
            ownership_data: Ownership predictions from Module 3
            constraints: Custom optimization constraints
            
        Returns:
            Dict containing optimized lineups and metadata
        """
        logger.info("Starting lineup optimization", 
                   players=len(projections), 
                   target_lineups=self.lineup_count)
        
        start_time = datetime.now()
        
        try:
            player_data = await self._prepare_player_data(projections, ownership_data)
            
            if player_data.empty:
                raise ValueError("No player data available for optimization")
            
            optimization_constraints = await self._setup_constraints(constraints)
            
            lineups = await self._generate_lineup_portfolio(player_data, optimization_constraints)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'lineups': lineups,
                'metadata': {
                    'total_lineups': len(lineups),
                    'target_lineups': self.lineup_count,
                    'execution_time_seconds': execution_time,
                    'execution_time_minutes': execution_time / 60,
                    'target_time_minutes': self.timeout_minutes,
                    'performance_ratio': (self.timeout_minutes * 60) / execution_time,
                    'players_considered': len(player_data),
                    'optimization_id': f"opt_{int(start_time.timestamp())}",
                    'completed_at': datetime.now(timezone.utc).isoformat()
                },
                'constraints_used': optimization_constraints,
                'portfolio_stats': await self._calculate_portfolio_stats(lineups)
            }
            
            await self._export_lineups(result)
            
            logger.info("Lineup optimization completed", 
                       lineups=len(lineups),
                       execution_time_minutes=execution_time/60)
            
            return result
            
        except Exception as e:
            logger.error("Error in lineup optimization", error=str(e))
            raise
    
    async def _prepare_player_data(
        self, 
        projections: List[Dict[str, Any]], 
        ownership_data: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Combine projections and ownership data"""
        
        proj_df = pd.DataFrame(projections)
        own_df = pd.DataFrame(ownership_data)
        
        if proj_df.empty:
            return pd.DataFrame()
        
        if not own_df.empty:
            player_data = proj_df.merge(
                own_df[['player_id', 'projected_ownership', 'leverage_score']], 
                on='player_id', 
                how='left'
            )
        else:
            player_data = proj_df.copy()
            player_data['projected_ownership'] = 10.0
            player_data['leverage_score'] = 1.0
        
        player_data['projected_ownership'] = player_data['projected_ownership'].fillna(10.0)
        player_data['leverage_score'] = player_data['leverage_score'].fillna(1.0)
        
        player_data = player_data[player_data['salary'] > 0]
        player_data = player_data[player_data['projected_points'] > 0]
        
        return player_data
    
    async def _setup_constraints(self, custom_constraints: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Setup optimization constraints"""
        
        default_constraints = {
            'salary_cap': self.salary_cap,
            'positions': {
                'QB': {'min': 1, 'max': 1},
                'RB': {'min': 2, 'max': 3},
                'WR': {'min': 3, 'max': 4},
                'TE': {'min': 1, 'max': 2},
                'DST': {'min': 1, 'max': 1},
                'FLEX': {'min': 1, 'max': 1}
            },
            'stacking_rules': {
                'qb_stack_min': 1,
                'game_stack_max': 4,
                'team_stack_max': 5
            },
            'exposure_limits': {
                'max_exposure': 0.5,
                'min_exposure': 0.0
            },
            'diversity_requirements': {
                'min_unique_players': 8,
                'max_duplicate_lineups': 0
            }
        }
        
        if custom_constraints:
            default_constraints.update(custom_constraints)
        
        return default_constraints
    
    async def _generate_lineup_portfolio(
        self, 
        player_data: pd.DataFrame, 
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate portfolio of optimized lineups with K-Means clustering diversification"""
        
        initial_pool_size = min(5000, self.lineup_count * 20)
        logger.info("Generating initial lineup pool", pool_size=initial_pool_size, target=self.lineup_count)
        
        initial_lineups = []
        used_combinations = set()
        
        for lineup_num in range(initial_pool_size):
            try:
                lineup = await self._optimize_single_lineup(
                    player_data, constraints, initial_lineups, used_combinations
                )
                
                if lineup:
                    initial_lineups.append(lineup)
                    lineup_key = tuple(sorted([p['player_id'] for p in lineup['players']]))
                    used_combinations.add(lineup_key)
                
                if lineup_num % 100 == 0:
                    logger.info("Initial pool generation progress", 
                               completed=lineup_num, 
                               target=initial_pool_size)
                
            except Exception as e:
                logger.error("Error optimizing lineup", lineup_num=lineup_num, error=str(e))
                continue
        
        if len(initial_lineups) <= self.lineup_count:
            logger.warning("Initial pool smaller than target, returning all lineups", 
                         pool_size=len(initial_lineups))
            return initial_lineups
        
        diversified_lineups = await self._apply_kmeans_diversification(initial_lineups)
        
        logger.info("Portfolio diversification completed", 
                   initial_pool=len(initial_lineups),
                   final_count=len(diversified_lineups))
        
        return diversified_lineups
    
    async def _optimize_single_lineup(
        self, 
        player_data: pd.DataFrame, 
        constraints: Dict[str, Any],
        existing_lineups: List[Dict[str, Any]],
        used_combinations: set
    ) -> Optional[Dict[str, Any]]:
        """Optimize single lineup using PuLP"""
        
        prob = pulp.LpProblem("DFS_Lineup_Optimization", pulp.LpMaximize)
        
        player_vars = {}
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            player_vars[player_id] = pulp.LpVariable(f"player_{player_id}", cat='Binary')
        
        objective = self.objective_function.create_leveraged_ceiling_objective(
            player_data, player_vars
        )
        prob += objective
        
        salary_constraint = self.constraint_manager.create_salary_constraint(
            player_data, player_vars, constraints['salary_cap']
        )
        prob += salary_constraint
        
        position_constraints = self.constraint_manager.create_position_constraints(
            player_data, player_vars, constraints['positions']
        )
        for constraint in position_constraints:
            prob += constraint
        
        exposure_constraints = self.constraint_manager.create_exposure_constraints(
            player_data, player_vars, existing_lineups, constraints['exposure_limits']
        )
        for constraint in exposure_constraints:
            prob += constraint
        
        uniqueness_constraints = self.constraint_manager.create_uniqueness_constraints(
            player_data, player_vars, used_combinations
        )
        for constraint in uniqueness_constraints:
            prob += constraint
        
        prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
        
        if prob.status != pulp.LpStatusOptimal:
            logger.warning("Optimization did not find optimal solution", status=prob.status)
            return None
        
        selected_players = []
        total_salary = 0
        total_projected_points = 0
        total_ceiling_points = 0
        total_ownership = 0
        
        for player_id, var in player_vars.items():
            if var.varValue == 1:
                player_row = player_data[player_data['player_id'] == player_id].iloc[0]
                
                player_info = {
                    'player_id': player_id,
                    'name': player_row['name'],
                    'position': player_row['position'],
                    'team': player_row.get('team', ''),
                    'salary': int(player_row['salary']),
                    'projected_points': float(player_row['projected_points']),
                    'ceiling_points': float(player_row['ceiling_points']),
                    'projected_ownership': float(player_row['projected_ownership'])
                }
                
                selected_players.append(player_info)
                total_salary += player_info['salary']
                total_projected_points += player_info['projected_points']
                total_ceiling_points += player_info['ceiling_points']
                total_ownership += player_info['projected_ownership']
        
        if len(selected_players) != 9:
            logger.warning("Invalid lineup size", players=len(selected_players))
            return None
        
        lineup = {
            'lineup_id': f"lineup_{len(existing_lineups) + 1}",
            'players': selected_players,
            'total_salary': total_salary,
            'projected_points': round(total_projected_points, 2),
            'ceiling_points': round(total_ceiling_points, 2),
            'projected_ownership': round(total_ownership, 2),
            'leverage_score': round(total_ceiling_points / max(total_ownership, 1), 2),
            'salary_remaining': constraints['salary_cap'] - total_salary,
            'is_valid': self._validate_lineup(selected_players, constraints)
        }
        
        return lineup
    
    def _validate_lineup(self, players: List[Dict[str, Any]], constraints: Dict[str, Any]) -> bool:
        """Validate lineup meets all constraints"""
        
        if len(players) != 9:
            return False
        
        position_counts = {}
        for player in players:
            pos = player['position']
            position_counts[pos] = position_counts.get(pos, 0) + 1
        
        required_positions = {
            'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'DST': 1
        }
        
        for pos, required in required_positions.items():
            if position_counts.get(pos, 0) < required:
                return False
        
        total_salary = sum(p['salary'] for p in players)
        if total_salary > constraints['salary_cap']:
            return False
        
        return True
    
    async def _calculate_portfolio_stats(self, lineups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate portfolio-level statistics"""
        
        if not lineups:
            return {}
        
        total_projected = sum(l['projected_points'] for l in lineups)
        total_ceiling = sum(l['ceiling_points'] for l in lineups)
        total_ownership = sum(l['projected_ownership'] for l in lineups)
        
        player_exposures = {}
        for lineup in lineups:
            for player in lineup['players']:
                player_id = player['player_id']
                player_exposures[player_id] = player_exposures.get(player_id, 0) + 1
        
        max_exposure = max(player_exposures.values()) if player_exposures else 0
        min_exposure = min(player_exposures.values()) if player_exposures else 0
        
        return {
            'avg_projected_points': round(total_projected / len(lineups), 2),
            'avg_ceiling_points': round(total_ceiling / len(lineups), 2),
            'avg_ownership': round(total_ownership / len(lineups), 2),
            'avg_leverage_score': round((total_ceiling / len(lineups)) / max(total_ownership / len(lineups), 1), 2),
            'unique_players': len(player_exposures),
            'max_player_exposure': max_exposure,
            'min_player_exposure': min_exposure,
            'exposure_distribution': dict(sorted(player_exposures.items(), key=lambda x: x[1], reverse=True)[:20])
        }
    
    async def _export_lineups(self, optimization_result: Dict[str, Any]):
        """Export lineups to CSV format"""
        
        lineups = optimization_result['lineups']
        
        if not lineups:
            return
        
        csv_data = []
        for lineup in lineups:
            row = {}
            
            positions = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST']
            position_counts = {pos: 0 for pos in ['QB', 'RB', 'WR', 'TE', 'DST']}
            
            sorted_players = sorted(lineup['players'], key=lambda x: (x['position'], -x['salary']))
            
            for i, pos in enumerate(positions):
                if i < len(sorted_players):
                    player = sorted_players[i]
                    if pos == 'FLEX' or player['position'] == pos or position_counts[player['position']] < positions.count(player['position']):
                        row[pos] = f"{player['name']} ({player['player_id']})"
                        if player['position'] != 'FLEX':
                            position_counts[player['position']] += 1
                    else:
                        row[pos] = ""
                else:
                    row[pos] = ""
            
            csv_data.append(row)
        
        df = pd.DataFrame(csv_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"/tmp/optimized_lineups_{timestamp}.csv"
        df.to_csv(export_path, index=False)
        
        cache_key = f"lineups_export:{optimization_result['metadata']['optimization_id']}"
        redis_client.setex(cache_key, 3600, export_path)
        
        logger.info("Lineups exported", path=export_path, lineups=len(lineups))
    
    async def _apply_kmeans_diversification(self, lineups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply K-Means clustering to select diversified portfolio of 150 lineups"""
        
        logger.info("Applying K-Means clustering for portfolio diversification", 
                   input_lineups=len(lineups), target_clusters=self.lineup_count)
        
        try:
            feature_vectors = []
            
            for lineup in lineups:
                features = [
                    lineup['total_salary'],
                    lineup['projected_points'],
                    lineup['ceiling_points'],
                    lineup['projected_ownership'],
                    lineup['leverage_score']
                ]
                
                position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DST': 0}
                team_exposure = {}
                
                for player in lineup['players']:
                    pos = player['position']
                    if pos in position_counts:
                        position_counts[pos] += 1
                    
                    team = player.get('team', 'UNKNOWN')
                    team_exposure[team] = team_exposure.get(team, 0) + 1
                
                features.extend([position_counts[pos] for pos in ['QB', 'RB', 'WR', 'TE', 'DST']])
                
                max_team_stack = max(team_exposure.values()) if team_exposure else 0
                features.append(max_team_stack)
                
                salary_std = np.std([p['salary'] for p in lineup['players']])
                features.append(salary_std)
                
                feature_vectors.append(features)
            
            scaler = StandardScaler()
            feature_matrix = scaler.fit_transform(feature_vectors)
            
            kmeans = KMeans(
                n_clusters=self.lineup_count,
                random_state=42,
                n_init=10,
                max_iter=300
            )
            
            cluster_labels = kmeans.fit_predict(feature_matrix)
            
            diversified_lineups = []
            
            for cluster_id in range(self.lineup_count):
                cluster_indices = np.where(cluster_labels == cluster_id)[0]
                
                if len(cluster_indices) == 0:
                    continue
                
                centroid = kmeans.cluster_centers_[cluster_id]
                min_distance = float('inf')
                best_lineup_idx = None
                
                for idx in cluster_indices:
                    distance = np.linalg.norm(feature_matrix[idx] - centroid)
                    if distance < min_distance:
                        min_distance = distance
                        best_lineup_idx = idx
                
                if best_lineup_idx is not None:
                    selected_lineup = lineups[best_lineup_idx].copy()
                    selected_lineup['cluster_id'] = int(cluster_id)
                    selected_lineup['cluster_distance'] = float(min_distance)
                    diversified_lineups.append(selected_lineup)
            
            logger.info("K-Means diversification completed", 
                       clusters_created=len(diversified_lineups),
                       target_clusters=self.lineup_count)
            
            return diversified_lineups
            
        except Exception as e:
            logger.error("Error in K-Means diversification", error=str(e))
            return lineups[:self.lineup_count]

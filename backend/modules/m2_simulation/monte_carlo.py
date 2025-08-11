import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import structlog

from shared.config import settings

logger = structlog.get_logger()


class MonteCarloSimulator:
    """
    High-performance Monte Carlo simulation engine for player fantasy points.
    Generates 100,000 iterations to determine ceiling, floor, and distribution.
    """
    
    def __init__(self):
        self.max_iterations = settings.max_simulation_iterations
        self.correlation_matrix = None
        
    async def run_simulation(self, projections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for all players.
        
        Args:
            projections: List of player projections from Module 2
            
        Returns:
            Dict containing simulation results and distributions
        """
        logger.info("Starting Monte Carlo simulation", 
                   players=len(projections), iterations=self.max_iterations)
        
        start_time = datetime.now()
        
        try:
            simulation_data = await self._prepare_simulation_data(projections)
            
            results = await self._run_parallel_simulation(simulation_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'simulation_results': results,
                'metadata': {
                    'iterations': self.max_iterations,
                    'players_simulated': len(projections),
                    'execution_time_seconds': execution_time,
                    'execution_time_minutes': execution_time / 60,
                    'target_time_minutes': 45,
                    'performance_ratio': (45 * 60) / execution_time,
                    'completed_at': datetime.now(timezone.utc).isoformat()
                }
            }
            
            logger.info("Monte Carlo simulation completed", 
                       execution_time_minutes=execution_time/60,
                       players=len(projections))
            
            return result
            
        except Exception as e:
            logger.error("Error in Monte Carlo simulation", error=str(e))
            raise
    
    async def _prepare_simulation_data(self, projections: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare data for simulation"""
        
        df = pd.DataFrame(projections)
        
        df['mean_points'] = df['projected_points']
        df['std_points'] = (df['ceiling_points'] - df['floor_points']) / 4
        df['min_points'] = df['floor_points']
        df['max_points'] = df['ceiling_points']
        
        return df
    
    async def _run_parallel_simulation(self, simulation_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Run simulation in parallel chunks for performance"""
        
        chunk_size = 10000
        num_chunks = self.max_iterations // chunk_size
        
        tasks = []
        for i in range(num_chunks):
            task = self._simulate_chunk(simulation_data, chunk_size, i)
            tasks.append(task)
        
        chunk_results = await asyncio.gather(*tasks)
        
        combined_results = self._combine_chunk_results(chunk_results, simulation_data)
        
        return combined_results
    
    async def _simulate_chunk(
        self, 
        simulation_data: pd.DataFrame, 
        iterations: int, 
        chunk_id: int
    ) -> np.ndarray:
        """Simulate a chunk of iterations"""
        
        num_players = len(simulation_data)
        results = np.zeros((iterations, num_players))
        
        for i in range(iterations):
            for j, (_, player) in enumerate(simulation_data.iterrows()):
                simulated_points = self._simulate_player_performance(player)
                results[i, j] = simulated_points
        
        return results
    
    def _simulate_player_performance(self, player: pd.Series) -> float:
        """Simulate individual player performance"""
        
        position = player.get('position', 'FLEX')
        mean_points = player.get('mean_points', 10)
        std_points = player.get('std_points', 3)
        min_points = player.get('min_points', 0)
        max_points = player.get('max_points', 30)
        
        if position == 'QB':
            passing_yards = max(0, np.random.normal(250, 50))
            passing_tds = max(0, np.random.poisson(1.5))
            rushing_yards = max(0, np.random.normal(20, 15))
            rushing_tds = np.random.poisson(0.3)
            
            points = (passing_yards * 0.04 + passing_tds * 4 + 
                     rushing_yards * 0.1 + rushing_tds * 6)
            
        elif position == 'RB':
            rushing_yards = max(0, np.random.normal(80, 30))
            rushing_tds = np.random.poisson(0.8)
            receiving_yards = max(0, np.random.normal(20, 15))
            receptions = np.random.poisson(2)
            receiving_tds = np.random.poisson(0.2)
            
            points = (rushing_yards * 0.1 + rushing_tds * 6 + 
                     receiving_yards * 0.1 + receptions * 1 + receiving_tds * 6)
            
        elif position in ['WR', 'TE']:
            receiving_yards = max(0, np.random.normal(60, 25))
            receptions = np.random.negative_binomial(5, 0.5)
            receiving_tds = np.random.poisson(0.5)
            
            points = receiving_yards * 0.1 + receptions * 1 + receiving_tds * 6
            
        elif position == 'DST':
            sacks = np.random.poisson(2)
            interceptions = np.random.poisson(1)
            fumbles = np.random.poisson(0.5)
            tds = np.random.poisson(0.3)
            points_allowed = max(0, np.random.normal(20, 8))
            
            points = (sacks * 1 + interceptions * 2 + fumbles * 2 + tds * 6)
            
            if points_allowed == 0:
                points += 10
            elif points_allowed <= 6:
                points += 7
            elif points_allowed <= 13:
                points += 4
            elif points_allowed <= 20:
                points += 1
            elif points_allowed >= 35:
                points -= 4
            
        else:
            points = max(0, np.random.normal(mean_points, std_points))
        
        return np.clip(points, min_points, max_points)
    
    def _combine_chunk_results(
        self, 
        chunk_results: List[np.ndarray], 
        simulation_data: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Combine results from all chunks"""
        
        all_results = np.vstack(chunk_results)
        
        combined_results = []
        for j, (_, player) in enumerate(simulation_data.iterrows()):
            player_results = all_results[:, j]
            
            result = {
                'player_id': player.get('player_id'),
                'name': player.get('name'),
                'position': player.get('position'),
                'salary': player.get('salary'),
                'simulation_stats': {
                    'mean': float(np.mean(player_results)),
                    'median': float(np.median(player_results)),
                    'std': float(np.std(player_results)),
                    'min': float(np.min(player_results)),
                    'max': float(np.max(player_results)),
                    'percentile_10': float(np.percentile(player_results, 10)),
                    'percentile_25': float(np.percentile(player_results, 25)),
                    'percentile_75': float(np.percentile(player_results, 75)),
                    'percentile_90': float(np.percentile(player_results, 90)),
                    'percentile_95': float(np.percentile(player_results, 95)),
                    'ceiling': float(np.percentile(player_results, 90)),
                    'floor': float(np.percentile(player_results, 10))
                },
                'distribution_data': {
                    'histogram': np.histogram(player_results, bins=20)[0].tolist(),
                    'bin_edges': np.histogram(player_results, bins=20)[1].tolist()
                },
                'iterations': self.max_iterations
            }
            
            combined_results.append(result)
        
        return combined_results
    
    async def calculate_correlations(self, projections: List[Dict[str, Any]]) -> np.ndarray:
        """Calculate correlation matrix between players"""
        
        correlation_factors = {
            'same_team_qb_wr': 0.3,
            'same_team_qb_te': 0.25,
            'same_team_rb_dst': -0.2,
            'same_game_opposing': -0.1,
            'weather_correlation': 0.15
        }
        
        num_players = len(projections)
        correlation_matrix = np.eye(num_players)
        
        for i, player1 in enumerate(projections):
            for j, player2 in enumerate(projections):
                if i != j:
                    correlation = self._calculate_player_correlation(
                        player1, player2, correlation_factors
                    )
                    correlation_matrix[i, j] = correlation
        
        self.correlation_matrix = correlation_matrix
        return correlation_matrix
    
    def _calculate_player_correlation(
        self, 
        player1: Dict[str, Any], 
        player2: Dict[str, Any], 
        factors: Dict[str, float]
    ) -> float:
        """Calculate correlation between two players"""
        
        correlation = 0.0
        
        if player1.get('team') == player2.get('team'):
            pos1, pos2 = player1.get('position'), player2.get('position')
            
            if pos1 == 'QB' and pos2 in ['WR', 'TE']:
                correlation += factors['same_team_qb_wr']
            elif pos1 in ['WR', 'TE'] and pos2 == 'QB':
                correlation += factors['same_team_qb_wr']
            elif pos1 == 'RB' and pos2 == 'DST':
                correlation += factors['same_team_rb_dst']
        
        return np.clip(correlation, -0.5, 0.5)

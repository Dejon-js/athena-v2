import pulp
import pandas as pd
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger()


class ConstraintManager:
    """
    Manages optimization constraints for DFS lineup construction.
    Handles salary cap, positions, stacking, exposure, and uniqueness constraints.
    """
    
    def __init__(self):
        pass
    
    def create_salary_constraint(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable], 
        salary_cap: int
    ) -> pulp.LpConstraint:
        """Create salary cap constraint"""
        
        salary_expr = pulp.lpSum([
            player_vars[row['player_id']] * row['salary']
            for _, row in player_data.iterrows()
        ])
        
        return salary_expr <= salary_cap
    
    def create_position_constraints(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable], 
        position_requirements: Dict[str, Dict[str, int]]
    ) -> List[pulp.LpConstraint]:
        """Create position requirement constraints"""
        
        constraints = []
        
        for position, requirements in position_requirements.items():
            position_players = player_data[player_data['position'] == position]
            
            if position_players.empty:
                continue
            
            position_expr = pulp.lpSum([
                player_vars[row['player_id']]
                for _, row in position_players.iterrows()
            ])
            
            min_req = requirements.get('min', 0)
            max_req = requirements.get('max', 99)
            
            if min_req > 0:
                constraints.append(position_expr >= min_req)
            
            if max_req < 99:
                constraints.append(position_expr <= max_req)
        
        total_players_expr = pulp.lpSum([
            player_vars[row['player_id']]
            for _, row in player_data.iterrows()
        ])
        constraints.append(total_players_expr == 9)
        
        return constraints
    
    def create_stacking_constraints(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable], 
        stacking_rules: Dict[str, Any]
    ) -> List[pulp.LpConstraint]:
        """Create stacking rule constraints"""
        
        constraints = []
        
        qb_stack_min = stacking_rules.get('qb_stack_min', 1)
        if qb_stack_min > 0:
            qb_stack_constraints = self._create_qb_stack_constraints(
                player_data, player_vars, qb_stack_min
            )
            constraints.extend(qb_stack_constraints)
        
        game_stack_max = stacking_rules.get('game_stack_max', 4)
        if game_stack_max < 9:
            game_stack_constraints = self._create_game_stack_constraints(
                player_data, player_vars, game_stack_max
            )
            constraints.extend(game_stack_constraints)
        
        team_stack_max = stacking_rules.get('team_stack_max', 5)
        if team_stack_max < 9:
            team_stack_constraints = self._create_team_stack_constraints(
                player_data, player_vars, team_stack_max
            )
            constraints.extend(team_stack_constraints)
        
        return constraints
    
    def _create_qb_stack_constraints(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable], 
        min_stack_size: int
    ) -> List[pulp.LpConstraint]:
        """Create QB stacking constraints"""
        
        constraints = []
        
        qb_players = player_data[player_data['position'] == 'QB']
        
        for _, qb in qb_players.iterrows():
            qb_team = qb.get('team', '')
            if not qb_team:
                continue
            
            qb_var = player_vars[qb['player_id']]
            
            pass_catchers = player_data[
                (player_data['team'] == qb_team) & 
                (player_data['position'].isin(['WR', 'TE']))
            ]
            
            if pass_catchers.empty:
                continue
            
            pass_catcher_expr = pulp.lpSum([
                player_vars[row['player_id']]
                for _, row in pass_catchers.iterrows()
            ])
            
            constraints.append(pass_catcher_expr >= qb_var * min_stack_size)
        
        return constraints
    
    def _create_game_stack_constraints(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable], 
        max_stack_size: int
    ) -> List[pulp.LpConstraint]:
        """Create game stacking constraints"""
        
        constraints = []
        
        games = player_data.groupby('game_id')['team'].unique()
        
        for game_id, teams in games.items():
            if len(teams) < 2:
                continue
            
            game_players = player_data[player_data['game_id'] == game_id]
            
            game_expr = pulp.lpSum([
                player_vars[row['player_id']]
                for _, row in game_players.iterrows()
            ])
            
            constraints.append(game_expr <= max_stack_size)
        
        return constraints
    
    def _create_team_stack_constraints(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable], 
        max_stack_size: int
    ) -> List[pulp.LpConstraint]:
        """Create team stacking constraints"""
        
        constraints = []
        
        teams = player_data['team'].unique()
        
        for team in teams:
            if pd.isna(team) or team == '':
                continue
            
            team_players = player_data[player_data['team'] == team]
            
            team_expr = pulp.lpSum([
                player_vars[row['player_id']]
                for _, row in team_players.iterrows()
            ])
            
            constraints.append(team_expr <= max_stack_size)
        
        return constraints
    
    def create_exposure_constraints(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable], 
        existing_lineups: List[Dict[str, Any]], 
        exposure_limits: Dict[str, float]
    ) -> List[pulp.LpConstraint]:
        """Create player exposure constraints"""
        
        constraints = []
        
        if not existing_lineups:
            return constraints
        
        max_exposure = exposure_limits.get('max_exposure', 0.5)
        min_exposure = exposure_limits.get('min_exposure', 0.0)
        
        total_lineups = len(existing_lineups) + 1
        
        player_usage = {}
        for lineup in existing_lineups:
            for player in lineup['players']:
                player_id = player['player_id']
                player_usage[player_id] = player_usage.get(player_id, 0) + 1
        
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            current_usage = player_usage.get(player_id, 0)
            
            max_allowed = int(max_exposure * total_lineups)
            min_required = int(min_exposure * total_lineups)
            
            if current_usage >= max_allowed:
                constraints.append(player_vars[player_id] == 0)
            elif current_usage < min_required and total_lineups > 10:
                constraints.append(player_vars[player_id] == 1)
        
        return constraints
    
    def create_uniqueness_constraints(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable], 
        used_combinations: set
    ) -> List[pulp.LpConstraint]:
        """Create lineup uniqueness constraints"""
        
        constraints = []
        
        for combination in used_combinations:
            if len(combination) < 8:
                continue
            
            overlap_expr = pulp.lpSum([
                player_vars.get(player_id, 0)
                for player_id in combination
                if player_id in player_vars
            ])
            
            constraints.append(overlap_expr <= 7)
        
        return constraints
    
    def create_custom_constraints(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable], 
        custom_rules: List[Dict[str, Any]]
    ) -> List[pulp.LpConstraint]:
        """Create custom user-defined constraints"""
        
        constraints = []
        
        for rule in custom_rules:
            rule_type = rule.get('type')
            
            if rule_type == 'force_player':
                player_id = rule.get('player_id')
                if player_id and player_id in player_vars:
                    constraints.append(player_vars[player_id] == 1)
            
            elif rule_type == 'exclude_player':
                player_id = rule.get('player_id')
                if player_id and player_id in player_vars:
                    constraints.append(player_vars[player_id] == 0)
            
            elif rule_type == 'min_salary':
                min_salary = rule.get('min_salary', 0)
                salary_expr = pulp.lpSum([
                    player_vars[row['player_id']] * row['salary']
                    for _, row in player_data.iterrows()
                ])
                constraints.append(salary_expr >= min_salary)
            
            elif rule_type == 'max_team_exposure':
                team = rule.get('team')
                max_players = rule.get('max_players', 3)
                
                team_players = player_data[player_data['team'] == team]
                if not team_players.empty:
                    team_expr = pulp.lpSum([
                        player_vars[row['player_id']]
                        for _, row in team_players.iterrows()
                    ])
                    constraints.append(team_expr <= max_players)
        
        return constraints
    
    def validate_constraints(
        self, 
        lineup: List[Dict[str, Any]], 
        constraints: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Validate lineup against all constraints"""
        
        validation = {
            'salary_valid': True,
            'positions_valid': True,
            'stacking_valid': True,
            'overall_valid': True
        }
        
        total_salary = sum(p['salary'] for p in lineup)
        validation['salary_valid'] = total_salary <= constraints.get('salary_cap', 50000)
        
        position_counts = {}
        for player in lineup:
            pos = player['position']
            position_counts[pos] = position_counts.get(pos, 0) + 1
        
        required_positions = {
            'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'DST': 1
        }
        
        for pos, required in required_positions.items():
            if position_counts.get(pos, 0) != required:
                validation['positions_valid'] = False
                break
        
        validation['overall_valid'] = all(validation.values())
        
        return validation

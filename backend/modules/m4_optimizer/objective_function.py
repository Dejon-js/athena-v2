import pulp
import pandas as pd
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger()


class ObjectiveFunction:
    """
    Defines objective functions for DFS lineup optimization.
    Primary function: Maximize Leveraged Ceiling (ceiling/ownership).
    """
    
    def __init__(self):
        pass
    
    def create_leveraged_ceiling_objective(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable]
    ) -> pulp.LpAffineExpression:
        """
        Create leveraged ceiling objective function.
        Maximizes: Σ (player_ceiling_score / player_projected_ownership)
        """
        
        objective_terms = []
        
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            ceiling_points = player.get('ceiling_points', player.get('projected_points', 10))
            projected_ownership = max(player.get('projected_ownership', 10), 0.1)
            
            leverage_score = ceiling_points / (projected_ownership / 100)
            
            objective_terms.append(player_vars[player_id] * leverage_score)
        
        return pulp.lpSum(objective_terms)
    
    def create_projected_points_objective(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable]
    ) -> pulp.LpAffineExpression:
        """
        Create simple projected points objective function.
        Maximizes: Σ (player_projected_points)
        """
        
        objective_terms = []
        
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            projected_points = player.get('projected_points', 10)
            
            objective_terms.append(player_vars[player_id] * projected_points)
        
        return pulp.lpSum(objective_terms)
    
    def create_ceiling_points_objective(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable]
    ) -> pulp.LpAffineExpression:
        """
        Create ceiling points objective function.
        Maximizes: Σ (player_ceiling_points)
        """
        
        objective_terms = []
        
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            ceiling_points = player.get('ceiling_points', player.get('projected_points', 10))
            
            objective_terms.append(player_vars[player_id] * ceiling_points)
        
        return pulp.lpSum(objective_terms)
    
    def create_value_based_objective(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable]
    ) -> pulp.LpAffineExpression:
        """
        Create value-based objective function.
        Maximizes: Σ (player_projected_points / player_salary * 1000)
        """
        
        objective_terms = []
        
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            projected_points = player.get('projected_points', 10)
            salary = max(player.get('salary', 5000), 1000)
            
            value_score = (projected_points / salary) * 1000
            
            objective_terms.append(player_vars[player_id] * value_score)
        
        return pulp.lpSum(objective_terms)
    
    def create_hybrid_objective(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable],
        weights: Optional[Dict[str, float]] = None
    ) -> pulp.LpAffineExpression:
        """
        Create hybrid objective function combining multiple factors.
        """
        
        if weights is None:
            weights = {
                'leverage': 0.5,
                'projected_points': 0.3,
                'value': 0.2
            }
        
        objective_terms = []
        
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            
            projected_points = player.get('projected_points', 10)
            ceiling_points = player.get('ceiling_points', projected_points)
            projected_ownership = max(player.get('projected_ownership', 10), 0.1)
            salary = max(player.get('salary', 5000), 1000)
            
            leverage_score = ceiling_points / (projected_ownership / 100)
            value_score = (projected_points / salary) * 1000
            
            hybrid_score = (
                weights['leverage'] * leverage_score +
                weights['projected_points'] * projected_points +
                weights['value'] * value_score
            )
            
            objective_terms.append(player_vars[player_id] * hybrid_score)
        
        return pulp.lpSum(objective_terms)
    
    def create_risk_adjusted_objective(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable],
        risk_tolerance: float = 0.5
    ) -> pulp.LpAffineExpression:
        """
        Create risk-adjusted objective function.
        Balances upside potential with downside protection.
        """
        
        objective_terms = []
        
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            
            projected_points = player.get('projected_points', 10)
            ceiling_points = player.get('ceiling_points', projected_points)
            floor_points = player.get('floor_points', projected_points * 0.5)
            
            upside = ceiling_points - projected_points
            downside = projected_points - floor_points
            
            risk_adjusted_score = (
                projected_points + 
                risk_tolerance * upside - 
                (1 - risk_tolerance) * downside
            )
            
            objective_terms.append(player_vars[player_id] * risk_adjusted_score)
        
        return pulp.lpSum(objective_terms)
    
    def create_tournament_objective(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable]
    ) -> pulp.LpAffineExpression:
        """
        Create tournament-focused objective function.
        Emphasizes ceiling and low ownership for GPP tournaments.
        """
        
        objective_terms = []
        
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            
            ceiling_points = player.get('ceiling_points', player.get('projected_points', 10))
            projected_ownership = max(player.get('projected_ownership', 10), 0.1)
            
            ownership_penalty = 1 - (projected_ownership / 100)
            tournament_score = ceiling_points * (1 + ownership_penalty)
            
            objective_terms.append(player_vars[player_id] * tournament_score)
        
        return pulp.lpSum(objective_terms)
    
    def create_cash_game_objective(
        self, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable]
    ) -> pulp.LpAffineExpression:
        """
        Create cash game objective function.
        Emphasizes floor and consistency for cash games.
        """
        
        objective_terms = []
        
        for _, player in player_data.iterrows():
            player_id = player['player_id']
            
            projected_points = player.get('projected_points', 10)
            floor_points = player.get('floor_points', projected_points * 0.5)
            
            consistency_score = (projected_points + floor_points) / 2
            
            objective_terms.append(player_vars[player_id] * consistency_score)
        
        return pulp.lpSum(objective_terms)
    
    def get_objective_function(
        self, 
        objective_type: str, 
        player_data: pd.DataFrame, 
        player_vars: Dict[str, pulp.LpVariable],
        **kwargs
    ) -> pulp.LpAffineExpression:
        """
        Get objective function by type.
        """
        
        if objective_type == 'leveraged_ceiling':
            return self.create_leveraged_ceiling_objective(player_data, player_vars)
        elif objective_type == 'projected_points':
            return self.create_projected_points_objective(player_data, player_vars)
        elif objective_type == 'ceiling_points':
            return self.create_ceiling_points_objective(player_data, player_vars)
        elif objective_type == 'value_based':
            return self.create_value_based_objective(player_data, player_vars)
        elif objective_type == 'hybrid':
            weights = kwargs.get('weights')
            return self.create_hybrid_objective(player_data, player_vars, weights)
        elif objective_type == 'risk_adjusted':
            return self.create_risk_adjusted_objective(player_data, player_vars, kwargs.get('risk_tolerance', 0.5))
        elif objective_type == 'tournament':
            return self.create_tournament_objective(player_data, player_vars)
        elif objective_type == 'cash_game':
            return self.create_cash_game_objective(player_data, player_vars)
        else:
            logger.warning("Unknown objective type, using leveraged_ceiling", objective_type=objective_type)
            return self.create_leveraged_ceiling_objective(player_data, player_vars)

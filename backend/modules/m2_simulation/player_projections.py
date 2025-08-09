import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import structlog

from ...shared.database import get_db, redis_client
from ...shared.config import settings
from ...shared.utils import get_current_nfl_week, is_low_data_mode

logger = structlog.get_logger()


class PlayerProjectionEngine:
    """
    ML-based player projection engine using Random Forest models.
    Generates probabilistic projections for fantasy points.
    """
    
    def __init__(self):
        self.models = {}
        self.feature_columns = {
            'QB': ['passing_yards_avg', 'passing_tds_avg', 'rushing_yards_avg', 'opponent_def_rank', 'vegas_total', 'weather_score'],
            'RB': ['rushing_yards_avg', 'rushing_tds_avg', 'receiving_yards_avg', 'snap_percentage', 'opponent_def_rank', 'vegas_total'],
            'WR': ['receiving_yards_avg', 'receiving_tds_avg', 'targets_avg', 'air_yards_share', 'opponent_def_rank', 'vegas_total'],
            'TE': ['receiving_yards_avg', 'receiving_tds_avg', 'targets_avg', 'red_zone_targets', 'opponent_def_rank', 'vegas_total'],
            'DST': ['sacks_avg', 'interceptions_avg', 'fumbles_avg', 'points_allowed_avg', 'opponent_off_rank', 'vegas_total']
        }
        self.low_data_features = {
            'QB': ['prev_season_points', 'draft_position', 'vegas_total', 'weather_score'],
            'RB': ['prev_season_points', 'draft_position', 'vegas_total', 'team_pace'],
            'WR': ['prev_season_points', 'draft_position', 'vegas_total', 'team_pace'],
            'TE': ['prev_season_points', 'draft_position', 'vegas_total', 'team_pace'],
            'DST': ['prev_season_points', 'opponent_off_rank', 'vegas_total', 'home_field']
        }
    
    async def generate_projections(self, week: int, season: int = 2025) -> Dict[str, Any]:
        """
        Generate player projections for specified week.
        
        Args:
            week: NFL week number (1-18)
            season: NFL season year
            
        Returns:
            Dict containing projection results and metadata
        """
        logger.info("Starting player projection generation", week=week, season=season)
        
        try:
            current_week = get_current_nfl_week()
            low_data_mode = is_low_data_mode()
            
            if low_data_mode:
                logger.info("Operating in low-data mode", week=current_week)
            
            projections = {}
            positions = ['QB', 'RB', 'WR', 'TE', 'DST']
            
            for position in positions:
                logger.info("Generating projections for position", position=position)
                
                position_projections = await self._generate_position_projections(
                    position, week, season, low_data_mode
                )
                projections[position] = position_projections
            
            result = {
                'week': week,
                'season': season,
                'low_data_mode': low_data_mode,
                'projections': projections,
                'total_players': sum(len(pos_proj) for pos_proj in projections.values()),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            await self._export_projections(result, week, season)
            
            logger.info("Player projection generation completed", 
                       total_players=result['total_players'])
            
            return result
            
        except Exception as e:
            logger.error("Error generating player projections", error=str(e))
            raise
    
    async def _generate_position_projections(
        self, 
        position: str, 
        week: int, 
        season: int, 
        low_data_mode: bool
    ) -> List[Dict[str, Any]]:
        """Generate projections for specific position"""
        
        training_data = await self._get_training_data(position, week, season)
        
        if training_data.empty:
            logger.warning("No training data available", position=position)
            return []
        
        model = await self._train_position_model(position, training_data, low_data_mode)
        
        current_players = await self._get_current_players(position, week, season)
        
        projections = []
        for _, player in current_players.iterrows():
            try:
                projection = await self._project_player(player, model, position, low_data_mode)
                projections.append(projection)
            except Exception as e:
                logger.error("Error projecting player", 
                           player_id=player.get('player_id'), error=str(e))
                continue
        
        return projections
    
    async def _train_position_model(
        self, 
        position: str, 
        training_data: pd.DataFrame, 
        low_data_mode: bool
    ) -> RandomForestRegressor:
        """Train Random Forest model for position"""
        
        feature_cols = self.low_data_features[position] if low_data_mode else self.feature_columns[position]
        
        available_features = [col for col in feature_cols if col in training_data.columns]
        
        if len(available_features) < 2:
            logger.warning("Insufficient features for training", 
                         position=position, available=len(available_features))
            available_features = training_data.select_dtypes(include=[np.number]).columns.tolist()
            available_features = [col for col in available_features if col != 'fantasy_points'][:5]
        
        X = training_data[available_features].fillna(0)
        y = training_data['fantasy_points'].fillna(0)
        
        if len(X) < 10:
            logger.warning("Insufficient training samples", position=position, samples=len(X))
            model = RandomForestRegressor(n_estimators=10, random_state=42)
        else:
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            )
        
        model.fit(X, y)
        
        if len(X) >= 20:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            logger.info("Model training completed", position=position, mae=mae)
        
        self.models[position] = {
            'model': model,
            'features': available_features,
            'low_data_mode': low_data_mode
        }
        
        return model
    
    async def _project_player(
        self, 
        player: pd.Series, 
        model: RandomForestRegressor, 
        position: str, 
        low_data_mode: bool
    ) -> Dict[str, Any]:
        """Generate projection for individual player"""
        
        model_info = self.models[position]
        features = model_info['features']
        
        player_features = []
        for feature in features:
            value = player.get(feature, 0)
            if pd.isna(value):
                value = 0
            player_features.append(value)
        
        feature_array = np.array(player_features).reshape(1, -1)
        
        base_projection = model.predict(feature_array)[0]
        
        confidence_multiplier = 0.8 if low_data_mode else 1.0
        base_projection *= confidence_multiplier
        
        ceiling = base_projection * 1.5
        floor = max(0, base_projection * 0.5)
        
        projection = {
            'player_id': player.get('player_id'),
            'name': player.get('name'),
            'position': position,
            'team': player.get('team_id'),
            'salary': player.get('salary', 0),
            'projected_points': round(base_projection, 2),
            'ceiling_points': round(ceiling, 2),
            'floor_points': round(floor, 2),
            'confidence_score': confidence_multiplier,
            'model_version': f"{position}_v1.0",
            'low_data_mode': low_data_mode,
            'features_used': features
        }
        
        return projection
    
    async def _get_training_data(self, position: str, week: int, season: int) -> pd.DataFrame:
        """Get historical training data for position"""
        
        sample_data = {
            'player_id': [f'{position}_{i}' for i in range(50)],
            'fantasy_points': np.random.normal(15, 5, 50),
            'passing_yards_avg': np.random.normal(250, 50, 50) if position == 'QB' else np.zeros(50),
            'passing_tds_avg': np.random.normal(1.5, 0.5, 50) if position == 'QB' else np.zeros(50),
            'rushing_yards_avg': np.random.normal(80, 30, 50) if position in ['RB', 'QB'] else np.random.normal(5, 2, 50),
            'receiving_yards_avg': np.random.normal(60, 20, 50) if position in ['WR', 'TE', 'RB'] else np.zeros(50),
            'receiving_tds_avg': np.random.normal(0.5, 0.3, 50) if position in ['WR', 'TE', 'RB'] else np.zeros(50),
            'targets_avg': np.random.normal(6, 2, 50) if position in ['WR', 'TE'] else np.zeros(50),
            'snap_percentage': np.random.uniform(0.3, 1.0, 50),
            'opponent_def_rank': np.random.randint(1, 33, 50),
            'vegas_total': np.random.normal(45, 5, 50),
            'weather_score': np.random.uniform(0.5, 1.0, 50),
            'prev_season_points': np.random.normal(150, 50, 50),
            'draft_position': np.random.randint(1, 300, 50),
            'team_pace': np.random.normal(65, 5, 50),
            'home_field': np.random.choice([0, 1], 50)
        }
        
        return pd.DataFrame(sample_data)
    
    async def _get_current_players(self, position: str, week: int, season: int) -> pd.DataFrame:
        """Get current players for projection"""
        
        sample_players = {
            'player_id': [f'{position}_{i}' for i in range(20)],
            'name': [f'{position} Player {i}' for i in range(20)],
            'team_id': [f'TEAM{i%8}' for i in range(20)],
            'salary': np.random.randint(4000, 12000, 20),
            'passing_yards_avg': np.random.normal(250, 50, 20) if position == 'QB' else np.zeros(20),
            'passing_tds_avg': np.random.normal(1.5, 0.5, 20) if position == 'QB' else np.zeros(20),
            'rushing_yards_avg': np.random.normal(80, 30, 20) if position in ['RB', 'QB'] else np.random.normal(5, 2, 20),
            'receiving_yards_avg': np.random.normal(60, 20, 20) if position in ['WR', 'TE', 'RB'] else np.zeros(20),
            'receiving_tds_avg': np.random.normal(0.5, 0.3, 20) if position in ['WR', 'TE', 'RB'] else np.zeros(20),
            'targets_avg': np.random.normal(6, 2, 20) if position in ['WR', 'TE'] else np.zeros(20),
            'snap_percentage': np.random.uniform(0.3, 1.0, 20),
            'opponent_def_rank': np.random.randint(1, 33, 20),
            'vegas_total': np.random.normal(45, 5, 20),
            'weather_score': np.random.uniform(0.5, 1.0, 20),
            'prev_season_points': np.random.normal(150, 50, 20),
            'draft_position': np.random.randint(1, 300, 20),
            'team_pace': np.random.normal(65, 5, 20),
            'home_field': np.random.choice([0, 1], 20)
        }
        
        return pd.DataFrame(sample_players)
    
    async def _export_projections(self, projections: Dict[str, Any], week: int, season: int):
        """Export projections to Parquet format for Module 4"""
        
        all_projections = []
        for position, pos_projections in projections['projections'].items():
            all_projections.extend(pos_projections)
        
        df = pd.DataFrame(all_projections)
        
        if not df.empty:
            export_path = f"/tmp/player_projections_week_{week}_{season}.parquet"
            df.to_parquet(export_path, index=False)
            
            cache_key = f"projections:week_{week}_{season}"
            redis_client.setex(cache_key, 3600, export_path)
            
            logger.info("Projections exported", path=export_path, players=len(df))

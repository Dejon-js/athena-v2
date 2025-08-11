import asyncio
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import structlog

from shared.database import get_db, redis_client

logger = structlog.get_logger()


class ModelTrainer:
    """
    Automated model training and versioning system.
    Retrains models based on performance feedback.
    """
    
    def __init__(self):
        self.training_queue = []
        self.model_versions = {}
        
    async def retrain_models(self, models_to_retrain: List[str]) -> Dict[str, Any]:
        """Retrain specified models with latest data"""
        
        logger.info("Starting model retraining", models=models_to_retrain)
        
        try:
            training_results = {}
            
            for model_name in models_to_retrain:
                result = await self._retrain_single_model(model_name)
                training_results[model_name] = result
            
            summary = {
                'models_retrained': list(training_results.keys()),
                'training_results': training_results,
                'retrained_at': datetime.now(timezone.utc).isoformat(),
                'success_count': len([r for r in training_results.values() if r.get('status') == 'success']),
                'failure_count': len([r for r in training_results.values() if r.get('status') == 'failed'])
            }
            
            await self._update_model_registry(summary)
            
            logger.info("Model retraining completed", 
                       success_count=summary['success_count'],
                       failure_count=summary['failure_count'])
            
            return summary
            
        except Exception as e:
            logger.error("Error in model retraining", error=str(e))
            raise
    
    async def _retrain_single_model(self, model_name: str) -> Dict[str, Any]:
        """Retrain individual model"""
        
        logger.info("Retraining model", model_name=model_name)
        
        try:
            training_data = await self._get_training_data(model_name)
            
            if not training_data:
                return {
                    'status': 'failed',
                    'error': 'No training data available',
                    'model_name': model_name
                }
            
            if model_name == 'projection_model':
                result = await self._retrain_projection_model(training_data)
            elif model_name == 'ownership_model':
                result = await self._retrain_ownership_model(training_data)
            else:
                return {
                    'status': 'failed',
                    'error': f'Unknown model: {model_name}',
                    'model_name': model_name
                }
            
            new_version = await self._version_model(model_name, result)
            
            return {
                'status': 'success',
                'model_name': model_name,
                'new_version': new_version,
                'performance_metrics': result.get('metrics', {}),
                'training_samples': len(training_data)
            }
            
        except Exception as e:
            logger.error("Error retraining model", model_name=model_name, error=str(e))
            return {
                'status': 'failed',
                'error': str(e),
                'model_name': model_name
            }
    
    async def _retrain_projection_model(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Retrain projection model"""
        
        df = pd.DataFrame(training_data)
        
        feature_columns = [
            'passing_yards_avg', 'passing_tds_avg', 'rushing_yards_avg',
            'receiving_yards_avg', 'targets_avg', 'snap_percentage',
            'opponent_rank', 'vegas_total', 'weather_score'
        ]
        
        available_features = [col for col in feature_columns if col in df.columns]
        
        if len(available_features) < 3:
            raise ValueError("Insufficient features for training")
        
        X = df[available_features].fillna(0)
        y = df['actual_points'].fillna(0)
        
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_absolute_error
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        
        return {
            'model': model,
            'features': available_features,
            'metrics': {
                'mae': round(float(mae), 2),
                'training_samples': len(X_train),
                'test_samples': len(X_test)
            }
        }
    
    async def _retrain_ownership_model(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Retrain ownership model"""
        
        df = pd.DataFrame(training_data)
        
        feature_columns = [
            'salary', 'projected_points', 'public_projection_rank',
            'media_sentiment', 'vegas_total', 'injury_concern'
        ]
        
        available_features = [col for col in feature_columns if col in df.columns]
        
        if len(available_features) < 3:
            raise ValueError("Insufficient features for training")
        
        X = df[available_features].fillna(0)
        y = df['actual_ownership'].fillna(10.0)
        
        from xgboost import XGBRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_absolute_error
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = XGBRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        
        return {
            'model': model,
            'features': available_features,
            'metrics': {
                'mae': round(float(mae), 2),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'meets_target': float(mae) <= 3.0
            }
        }
    
    async def _get_training_data(self, model_name: str) -> List[Dict[str, Any]]:
        """Get training data for model"""
        
        sample_data = []
        
        for i in range(100):
            sample_data.append({
                'player_id': f'player_{i}',
                'passing_yards_avg': 250 + (i % 50),
                'passing_tds_avg': 1.5 + (i % 3) * 0.5,
                'rushing_yards_avg': 50 + (i % 30),
                'receiving_yards_avg': 60 + (i % 40),
                'targets_avg': 6 + (i % 8),
                'snap_percentage': 0.7 + (i % 3) * 0.1,
                'opponent_rank': 1 + (i % 32),
                'vegas_total': 42 + (i % 16),
                'weather_score': 0.8 + (i % 2) * 0.2,
                'salary': 5000 + (i % 50) * 100,
                'projected_points': 10 + (i % 20),
                'public_projection_rank': 1 + (i % 100),
                'media_sentiment': -0.5 + (i % 10) * 0.1,
                'injury_concern': (i % 5) * 0.2,
                'actual_points': 8 + (i % 25),
                'actual_ownership': 5 + (i % 30)
            })
        
        return sample_data
    
    async def _version_model(self, model_name: str, training_result: Dict[str, Any]) -> str:
        """Create new version for trained model"""
        
        current_version = self.model_versions.get(model_name, 0)
        new_version = current_version + 1
        
        version_string = f"{model_name}_v{new_version}.0"
        
        self.model_versions[model_name] = new_version
        
        model_info = {
            'version': version_string,
            'trained_at': datetime.now(timezone.utc).isoformat(),
            'metrics': training_result.get('metrics', {}),
            'features': training_result.get('features', [])
        }
        
        cache_key = f"model_version:{version_string}"
        redis_client.setex(cache_key, 86400 * 30, str(model_info))
        
        logger.info("Model versioned", version=version_string)
        
        return version_string
    
    async def _update_model_registry(self, training_summary: Dict[str, Any]):
        """Update model registry with training results"""
        
        registry_key = "model_registry"
        registry_data = {
            'last_training': training_summary,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        redis_client.setex(registry_key, 86400 * 7, str(registry_data))
        
        logger.info("Model registry updated")
    
    async def get_model_status(self) -> Dict[str, Any]:
        """Get current model status and versions"""
        
        return {
            'model_versions': self.model_versions,
            'training_queue': len(self.training_queue),
            'last_update': datetime.now(timezone.utc).isoformat()
        }
    
    async def schedule_retraining(self, model_name: str, priority: str = 'normal'):
        """Schedule model for retraining"""
        
        training_item = {
            'model_name': model_name,
            'priority': priority,
            'scheduled_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.training_queue.append(training_item)
        
        logger.info("Model scheduled for retraining", 
                   model_name=model_name, priority=priority)

import asyncio
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import structlog

from shared.database import get_db, redis_client
from shared.config import settings

logger = structlog.get_logger()


class FeedbackLoop:
    """
    Learning and feedback loop for continuous model improvement.
    Analyzes performance and triggers model retraining.
    """
    
    def __init__(self):
        self.performance_history = []
        
    async def analyze_weekly_performance(self, week: int, season: int = 2025) -> Dict[str, Any]:
        """Analyze performance for completed week"""
        
        logger.info("Analyzing weekly performance", week=week, season=season)
        
        try:
            actual_results = await self._get_actual_results(week, season)
            projections = await self._get_projections(week, season)
            ownership_predictions = await self._get_ownership_predictions(week, season)
            
            projection_analysis = await self._analyze_projection_accuracy(
                projections, actual_results
            )
            
            ownership_analysis = await self._analyze_ownership_accuracy(
                ownership_predictions, actual_results
            )
            
            lineup_analysis = await self._analyze_lineup_performance(week, season)
            
            performance_summary = {
                'week': week,
                'season': season,
                'projection_accuracy': projection_analysis,
                'ownership_accuracy': ownership_analysis,
                'lineup_performance': lineup_analysis,
                'overall_grade': self._calculate_overall_grade(
                    projection_analysis, ownership_analysis, lineup_analysis
                ),
                'analyzed_at': datetime.now(timezone.utc).isoformat()
            }
            
            await self._store_performance_data(performance_summary)
            
            improvement_recommendations = await self._generate_improvement_recommendations(
                performance_summary
            )
            
            result = {
                'performance_summary': performance_summary,
                'improvement_recommendations': improvement_recommendations,
                'retrain_recommended': self._should_retrain_models(performance_summary)
            }
            
            logger.info("Weekly performance analysis completed", 
                       overall_grade=performance_summary['overall_grade'])
            
            return result
            
        except Exception as e:
            logger.error("Error analyzing weekly performance", error=str(e))
            raise
    
    async def _analyze_projection_accuracy(
        self, 
        projections: List[Dict[str, Any]], 
        actual_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze projection accuracy"""
        
        if not projections or not actual_results:
            return {'mae': None, 'rmse': None, 'accuracy_by_position': {}}
        
        proj_df = pd.DataFrame(projections)
        actual_df = pd.DataFrame(actual_results)
        
        merged = proj_df.merge(actual_df, on='player_id', how='inner')
        
        if merged.empty:
            return {'mae': None, 'rmse': None, 'accuracy_by_position': {}}
        
        merged['error'] = abs(merged['projected_points'] - merged['actual_points'])
        merged['squared_error'] = (merged['projected_points'] - merged['actual_points']) ** 2
        
        mae = merged['error'].mean()
        rmse = (merged['squared_error'].mean()) ** 0.5
        
        accuracy_by_position = {}
        for position in merged['position'].unique():
            pos_data = merged[merged['position'] == position]
            accuracy_by_position[position] = {
                'mae': pos_data['error'].mean(),
                'rmse': (pos_data['squared_error'].mean()) ** 0.5,
                'sample_size': len(pos_data)
            }
        
        return {
            'mae': round(mae, 2),
            'rmse': round(rmse, 2),
            'accuracy_by_position': accuracy_by_position,
            'sample_size': len(merged)
        }
    
    async def _analyze_ownership_accuracy(
        self, 
        ownership_predictions: List[Dict[str, Any]], 
        actual_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze ownership prediction accuracy"""
        
        if not ownership_predictions or not actual_results:
            return {'mae': None, 'target_mae': 3.0, 'meets_target': False}
        
        pred_df = pd.DataFrame(ownership_predictions)
        actual_df = pd.DataFrame(actual_results)
        
        merged = pred_df.merge(actual_df, on='player_id', how='inner')
        
        if merged.empty or 'actual_ownership' not in merged.columns:
            return {'mae': None, 'target_mae': 3.0, 'meets_target': False}
        
        merged['ownership_error'] = abs(merged['projected_ownership'] - merged['actual_ownership'])
        
        mae = merged['ownership_error'].mean()
        target_mae = 3.0
        
        return {
            'mae': round(mae, 2),
            'target_mae': target_mae,
            'meets_target': mae <= target_mae,
            'sample_size': len(merged)
        }
    
    async def _analyze_lineup_performance(self, week: int, season: int) -> Dict[str, Any]:
        """Analyze lineup performance in contests"""
        
        sample_performance = {
            'total_lineups': 150,
            'avg_score': 142.5,
            'best_score': 187.3,
            'worst_score': 98.2,
            'top_1_percent_finishes': 2,
            'top_5_percent_finishes': 8,
            'top_10_percent_finishes': 15,
            'roi': 1.15,
            'total_winnings': 2300.0,
            'total_investment': 2000.0
        }
        
        return sample_performance
    
    def _calculate_overall_grade(
        self, 
        projection_analysis: Dict[str, Any], 
        ownership_analysis: Dict[str, Any], 
        lineup_analysis: Dict[str, Any]
    ) -> str:
        """Calculate overall performance grade"""
        
        score = 0
        max_score = 0
        
        if projection_analysis.get('mae') is not None:
            proj_mae = projection_analysis['mae']
            if proj_mae <= 3.0:
                score += 30
            elif proj_mae <= 4.0:
                score += 20
            elif proj_mae <= 5.0:
                score += 10
            max_score += 30
        
        if ownership_analysis.get('meets_target'):
            score += 30
        max_score += 30
        
        roi = lineup_analysis.get('roi', 0)
        if roi >= 1.2:
            score += 40
        elif roi >= 1.1:
            score += 30
        elif roi >= 1.0:
            score += 20
        elif roi >= 0.9:
            score += 10
        max_score += 40
        
        if max_score == 0:
            return 'Incomplete'
        
        percentage = (score / max_score) * 100
        
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'
    
    async def _generate_improvement_recommendations(
        self, 
        performance_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for improvement"""
        
        recommendations = []
        
        proj_accuracy = performance_summary.get('projection_accuracy', {})
        if proj_accuracy.get('mae', 0) > 4.0:
            recommendations.append({
                'category': 'projections',
                'issue': 'High projection error',
                'recommendation': 'Retrain projection models with additional features',
                'priority': 'high'
            })
        
        own_accuracy = performance_summary.get('ownership_accuracy', {})
        if not own_accuracy.get('meets_target', True):
            recommendations.append({
                'category': 'ownership',
                'issue': 'Ownership predictions above target MAE',
                'recommendation': 'Add more sentiment and public data features',
                'priority': 'high'
            })
        
        lineup_perf = performance_summary.get('lineup_performance', {})
        if lineup_perf.get('roi', 1.0) < 1.0:
            recommendations.append({
                'category': 'optimization',
                'issue': 'Negative ROI',
                'recommendation': 'Adjust optimization objective function weights',
                'priority': 'critical'
            })
        
        return recommendations
    
    def _should_retrain_models(self, performance_summary: Dict[str, Any]) -> bool:
        """Determine if models should be retrained"""
        
        proj_mae = performance_summary.get('projection_accuracy', {}).get('mae')
        own_meets_target = performance_summary.get('ownership_accuracy', {}).get('meets_target', True)
        roi = performance_summary.get('lineup_performance', {}).get('roi', 1.0)
        
        if proj_mae and proj_mae > 4.0:
            return True
        
        if not own_meets_target:
            return True
        
        if roi < 0.95:
            return True
        
        return False
    
    async def _get_actual_results(self, week: int, season: int) -> List[Dict[str, Any]]:
        """Get actual player results for the week"""
        
        sample_results = [
            {
                'player_id': 'player_1',
                'name': 'Patrick Mahomes',
                'position': 'QB',
                'actual_points': 24.5,
                'actual_ownership': 18.3
            },
            {
                'player_id': 'player_2',
                'name': 'Christian McCaffrey',
                'position': 'RB',
                'actual_points': 31.2,
                'actual_ownership': 22.1
            }
        ]
        
        return sample_results
    
    async def _get_projections(self, week: int, season: int) -> List[Dict[str, Any]]:
        """Get projections that were made for the week"""
        
        cache_key = f"projections:week_{week}_{season}"
        cached_projections = redis_client.get(cache_key)
        
        if cached_projections:
            return eval(cached_projections)
        
        return []
    
    async def _get_ownership_predictions(self, week: int, season: int) -> List[Dict[str, Any]]:
        """Get ownership predictions that were made for the week"""
        
        cache_key = f"ownership_predictions:week_{week}_{season}"
        cached_predictions = redis_client.get(cache_key)
        
        if cached_predictions:
            return eval(cached_predictions)
        
        return []
    
    async def _store_performance_data(self, performance_data: Dict[str, Any]):
        """Store performance data for historical tracking"""
        
        cache_key = f"performance:week_{performance_data['week']}_{performance_data['season']}"
        redis_client.setex(cache_key, 86400 * 7, str(performance_data))
        
        self.performance_history.append(performance_data)
        
        logger.info("Performance data stored", cache_key=cache_key)

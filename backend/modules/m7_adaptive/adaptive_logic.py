import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import structlog

from shared.utils import get_current_nfl_week, is_low_data_mode
from shared.database import get_db, redis_client

logger = structlog.get_logger()


class AdaptiveLogic:
    """
    Early-season adaptive logic for weeks 1-3 operation.
    Switches between low-data and full-data modes automatically.
    """
    
    def __init__(self):
        self.current_mode = None
        self.mode_history = []
        
    async def determine_operational_mode(self, week: int, season: int = 2025) -> Dict[str, Any]:
        """Determine current operational mode based on week"""
        
        logger.info("Determining operational mode", week=week, season=season)
        
        try:
            current_week = get_current_nfl_week()
            low_data_mode = is_low_data_mode()
            
            if low_data_mode:
                mode = 'low_data'
                confidence_multiplier = 0.8
                feature_adjustments = await self._get_low_data_adjustments()
            else:
                mode = 'full_data'
                confidence_multiplier = 1.0
                feature_adjustments = await self._get_full_data_adjustments()
            
            mode_info = {
                'operational_mode': mode,
                'week': week,
                'season': season,
                'current_week': current_week,
                'confidence_multiplier': confidence_multiplier,
                'feature_adjustments': feature_adjustments,
                'transition_week': 5,
                'determined_at': datetime.now(timezone.utc).isoformat()
            }
            
            if self.current_mode != mode:
                await self._handle_mode_transition(self.current_mode, mode)
                self.current_mode = mode
            
            self.mode_history.append(mode_info)
            
            await self._store_mode_info(mode_info)
            
            logger.info("Operational mode determined", 
                       mode=mode, 
                       confidence_multiplier=confidence_multiplier)
            
            return mode_info
            
        except Exception as e:
            logger.error("Error determining operational mode", error=str(e))
            raise
    
    async def _get_low_data_adjustments(self) -> Dict[str, Any]:
        """Get feature adjustments for low-data mode"""
        
        return {
            'feature_weights': {
                'previous_season_data': 1.5,
                'vegas_market_data': 1.3,
                'draft_position': 1.2,
                'preseason_performance': 1.1,
                'in_season_data': 0.3
            },
            'model_adjustments': {
                'projection_confidence': 0.8,
                'ownership_confidence': 0.7,
                'simulation_variance': 1.2
            },
            'data_sources': {
                'prioritize_vegas': True,
                'use_expert_consensus': True,
                'reduce_news_weight': True,
                'increase_historical_weight': True
            }
        }
    
    async def _get_full_data_adjustments(self) -> Dict[str, Any]:
        """Get feature adjustments for full-data mode"""
        
        return {
            'feature_weights': {
                'recent_performance': 1.5,
                'in_season_trends': 1.3,
                'matchup_data': 1.2,
                'injury_reports': 1.1,
                'previous_season_data': 0.8
            },
            'model_adjustments': {
                'projection_confidence': 1.0,
                'ownership_confidence': 1.0,
                'simulation_variance': 1.0
            },
            'data_sources': {
                'prioritize_recent': True,
                'use_full_news_sentiment': True,
                'include_advanced_metrics': True,
                'weight_current_season': True
            }
        }
    
    async def _handle_mode_transition(self, old_mode: Optional[str], new_mode: str):
        """Handle transition between operational modes"""
        
        if old_mode is None:
            logger.info("Initial mode set", mode=new_mode)
            return
        
        logger.info("Mode transition detected", old_mode=old_mode, new_mode=new_mode)
        
        transition_info = {
            'from_mode': old_mode,
            'to_mode': new_mode,
            'transition_time': datetime.now(timezone.utc).isoformat(),
            'actions_taken': []
        }
        
        if old_mode == 'low_data' and new_mode == 'full_data':
            actions = await self._transition_to_full_data()
            transition_info['actions_taken'] = actions
        elif old_mode == 'full_data' and new_mode == 'low_data':
            actions = await self._transition_to_low_data()
            transition_info['actions_taken'] = actions
        
        await self._store_transition_info(transition_info)
    
    async def _transition_to_full_data(self) -> List[str]:
        """Handle transition from low-data to full-data mode"""
        
        actions = [
            'Enable in-season performance weighting',
            'Activate advanced metrics integration',
            'Increase news sentiment analysis weight',
            'Enable full correlation modeling',
            'Activate real-time injury monitoring'
        ]
        
        for action in actions:
            logger.info("Transition action", action=action)
        
        return actions
    
    async def _transition_to_low_data(self) -> List[str]:
        """Handle transition from full-data to low-data mode"""
        
        actions = [
            'Increase previous season data weight',
            'Prioritize Vegas market data',
            'Reduce news sentiment weight',
            'Simplify correlation modeling',
            'Increase expert consensus weight'
        ]
        
        for action in actions:
            logger.info("Transition action", action=action)
        
        return actions
    
    async def apply_mode_adjustments(
        self, 
        base_projections: List[Dict[str, Any]], 
        mode_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply mode-specific adjustments to projections"""
        
        mode = mode_info['operational_mode']
        confidence_multiplier = mode_info['confidence_multiplier']
        
        adjusted_projections = []
        
        for projection in base_projections:
            adjusted = projection.copy()
            
            adjusted['projected_points'] *= confidence_multiplier
            adjusted['ceiling_points'] *= confidence_multiplier
            adjusted['floor_points'] *= confidence_multiplier
            
            adjusted['confidence_score'] = projection.get('confidence_score', 1.0) * confidence_multiplier
            
            if mode == 'low_data':
                adjusted['low_data_mode'] = True
                adjusted['confidence_tag'] = 'Lower Confidence'
            else:
                adjusted['low_data_mode'] = False
                adjusted['confidence_tag'] = 'Standard Confidence'
            
            adjusted_projections.append(adjusted)
        
        logger.info("Mode adjustments applied", 
                   mode=mode, 
                   projections=len(adjusted_projections))
        
        return adjusted_projections
    
    async def get_mode_status(self) -> Dict[str, Any]:
        """Get current mode status and history"""
        
        current_week = get_current_nfl_week()
        low_data_mode = is_low_data_mode()
        
        return {
            'current_mode': 'low_data' if low_data_mode else 'full_data',
            'current_week': current_week,
            'transition_week': 5,
            'weeks_until_transition': max(0, 5 - current_week) if low_data_mode else 0,
            'mode_history': self.mode_history[-5:],
            'last_update': datetime.now(timezone.utc).isoformat()
        }
    
    async def _store_mode_info(self, mode_info: Dict[str, Any]):
        """Store mode information in cache"""
        
        cache_key = f"adaptive_mode:week_{mode_info['week']}_{mode_info['season']}"
        redis_client.setex(cache_key, 86400, str(mode_info))
        
        current_mode_key = "adaptive_mode:current"
        redis_client.setex(current_mode_key, 3600, str(mode_info))
        
        logger.info("Mode info stored", cache_key=cache_key)
    
    async def _store_transition_info(self, transition_info: Dict[str, Any]):
        """Store mode transition information"""
        
        cache_key = f"mode_transition:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        redis_client.setex(cache_key, 86400 * 7, str(transition_info))
        
        logger.info("Transition info stored", cache_key=cache_key)

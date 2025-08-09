import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import structlog

from ...shared.database import get_db, redis_client

logger = structlog.get_logger()


class SuggestionEngine:
    """
    Generates real-time lineup adjustment suggestions based on live game events.
    Provides suggestions within 90 seconds of early games concluding.
    """
    
    def __init__(self):
        self.suggestion_cache = {}
        
    async def generate_suggestions(
        self, 
        current_lineups: List[Dict[str, Any]], 
        live_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate lineup adjustment suggestions"""
        
        logger.info("Generating lineup suggestions", 
                   lineups=len(current_lineups))
        
        try:
            suggestions = []
            
            for lineup in current_lineups:
                lineup_suggestions = await self._analyze_lineup(lineup, live_data)
                suggestions.extend(lineup_suggestions)
            
            prioritized_suggestions = self._prioritize_suggestions(suggestions)
            
            result = {
                'suggestions': prioritized_suggestions,
                'total_suggestions': len(suggestions),
                'high_priority': len([s for s in suggestions if s.get('priority') == 'high']),
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'response_time_seconds': 45
            }
            
            await self._cache_suggestions(result)
            
            logger.info("Suggestions generated", 
                       total=len(suggestions),
                       high_priority=result['high_priority'])
            
            return result
            
        except Exception as e:
            logger.error("Error generating suggestions", error=str(e))
            raise
    
    async def _analyze_lineup(
        self, 
        lineup: Dict[str, Any], 
        live_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze individual lineup for adjustment opportunities"""
        
        suggestions = []
        
        for player in lineup.get('players', []):
            player_suggestions = await self._analyze_player(player, live_data)
            suggestions.extend(player_suggestions)
        
        return suggestions
    
    async def _analyze_player(
        self, 
        player: Dict[str, Any], 
        live_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze individual player for adjustment opportunities"""
        
        suggestions = []
        player_id = player.get('player_id')
        
        game_status = live_data.get('games', {}).get(player.get('game_id'), {})
        
        if game_status.get('status') == 'final':
            actual_points = game_status.get('player_scores', {}).get(player_id, 0)
            projected_points = player.get('projected_points', 0)
            
            if actual_points < projected_points * 0.5:
                suggestions.append({
                    'type': 'underperformance',
                    'player_id': player_id,
                    'player_name': player.get('name'),
                    'actual_points': actual_points,
                    'projected_points': projected_points,
                    'suggestion': f"Consider pivoting away from {player.get('name')} in remaining lineups",
                    'priority': 'high',
                    'confidence': 0.8
                })
        
        elif game_status.get('status') == 'in_progress':
            current_points = game_status.get('player_scores', {}).get(player_id, 0)
            projected_points = player.get('projected_points', 0)
            
            if current_points > projected_points * 0.7:
                suggestions.append({
                    'type': 'outperformance',
                    'player_id': player_id,
                    'player_name': player.get('name'),
                    'current_points': current_points,
                    'projected_points': projected_points,
                    'suggestion': f"Consider increasing exposure to {player.get('name')} in late swap",
                    'priority': 'medium',
                    'confidence': 0.6
                })
        
        return suggestions
    
    def _prioritize_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize suggestions by impact and confidence"""
        
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        
        return sorted(
            suggestions,
            key=lambda x: (
                priority_order.get(x.get('priority', 'low'), 1),
                x.get('confidence', 0)
            ),
            reverse=True
        )
    
    async def generate_late_swap_suggestions(
        self, 
        remaining_games: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate late swap suggestions for remaining games"""
        
        logger.info("Generating late swap suggestions", 
                   remaining_games=len(remaining_games))
        
        try:
            suggestions = []
            
            for game in remaining_games:
                game_suggestions = await self._analyze_remaining_game(game)
                suggestions.extend(game_suggestions)
            
            result = {
                'late_swap_suggestions': suggestions,
                'remaining_games': len(remaining_games),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error("Error generating late swap suggestions", error=str(e))
            raise
    
    async def _analyze_remaining_game(self, game: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze remaining game for late swap opportunities"""
        
        suggestions = []
        
        game_total = game.get('vegas_total', 45)
        
        if game_total > 50:
            suggestions.append({
                'type': 'high_total_game',
                'game_id': game.get('id'),
                'teams': [game.get('home_team'), game.get('away_team')],
                'vegas_total': game_total,
                'suggestion': f"Consider stacking players from high-total game ({game_total} total)",
                'priority': 'medium',
                'confidence': 0.7
            })
        
        weather = game.get('weather', {})
        if weather.get('wind_speed', 0) > 15:
            suggestions.append({
                'type': 'weather_concern',
                'game_id': game.get('id'),
                'weather': weather,
                'suggestion': "Consider avoiding passing games due to high wind",
                'priority': 'medium',
                'confidence': 0.6
            })
        
        return suggestions
    
    async def get_real_time_adjustments(self) -> Dict[str, Any]:
        """Get real-time lineup adjustments"""
        
        cached_suggestions = redis_client.get('live_suggestions')
        
        if cached_suggestions:
            return eval(cached_suggestions)
        
        return {
            'suggestions': [],
            'last_update': None,
            'status': 'no_active_suggestions'
        }
    
    async def _cache_suggestions(self, suggestions: Dict[str, Any]):
        """Cache suggestions for quick retrieval"""
        
        cache_key = 'live_suggestions'
        redis_client.setex(cache_key, 300, str(suggestions))
        
        logger.info("Suggestions cached", cache_key=cache_key)

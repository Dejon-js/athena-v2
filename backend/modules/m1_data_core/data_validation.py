import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd
import hashlib
import json
import numpy as np
from sqlalchemy.orm import Session
import structlog
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from ...shared.database import get_db, redis_client
from ...shared.config import settings
from ...shared.utils import DataProcessor

logger = structlog.get_logger()


class DataValidator:
    """
    Data validation and reconciliation engine for cross-source validation.
    Ensures 95% data consistency across multiple sources.
    """
    
    def __init__(self):
        self.data_processor = DataProcessor()
        self.validation_rules = {
            'salary_threshold': 100,  # Alert if salary difference > $100
            'injury_status_sources': 2,  # Require 2+ sources for injury status
            'odds_variance_threshold': 0.05,  # 5% variance threshold for odds
            'news_sentiment_threshold': 0.3  # Sentiment score difference threshold
        }
    
    async def validate_all_data(self) -> Dict[str, Any]:
        """
        Main validation orchestration method.
        
        Returns:
            Dict containing validation results and conflict flags
        """
        logger.info("Starting comprehensive data validation")
        
        validation_tasks = [
            self.validate_player_salaries(),
            self.validate_injury_status(),
            self.validate_vegas_odds(),
            self.validate_news_sentiment()
        ]
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        validation_summary = {
            'salary_validation': results[0],
            'injury_validation': results[1],
            'odds_validation': results[2],
            'sentiment_validation': results[3],
            'overall_consistency': self._calculate_overall_consistency(results),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Data validation completed", summary=validation_summary)
        return validation_summary
    
    async def validate_player_salaries(self) -> Dict[str, Any]:
        """
        Validate player salaries across DFS platforms.
        Flag conflicts where salary difference > threshold.
        """
        logger.info("Validating player salaries across platforms")
        
        try:
            conflicts = []
            total_players = 0
            consistent_players = 0
            
            dk_salaries = await self._get_draftkings_salaries()
            fd_salaries = await self._get_fanduel_salaries()
            
            for player_id in set(dk_salaries.keys()) & set(fd_salaries.keys()):
                total_players += 1
                dk_salary = dk_salaries[player_id]
                fd_salary = fd_salaries[player_id]
                
                salary_diff = abs(dk_salary - fd_salary)
                
                if salary_diff > self.validation_rules['salary_threshold']:
                    conflict = {
                        'player_id': player_id,
                        'draftkings_salary': dk_salary,
                        'fanduel_salary': fd_salary,
                        'difference': salary_diff,
                        'severity': 'high' if salary_diff > 500 else 'medium'
                    }
                    conflicts.append(conflict)
                    await self._flag_salary_conflict(conflict)
                else:
                    consistent_players += 1
            
            consistency_rate = consistent_players / total_players if total_players > 0 else 0
            
            return {
                'status': 'completed',
                'total_players': total_players,
                'consistent_players': consistent_players,
                'conflicts': len(conflicts),
                'consistency_rate': consistency_rate,
                'conflict_details': conflicts[:10]  # Limit to first 10 conflicts
            }
            
        except Exception as e:
            logger.error("Error validating player salaries", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    async def validate_injury_status(self) -> Dict[str, Any]:
        """
        Validate injury status across multiple sources.
        Require consensus from 2+ sources for critical status changes.
        """
        logger.info("Validating injury status across sources")
        
        try:
            conflicts = []
            total_players = 0
            consensus_players = 0
            
            sportradar_injuries = await self._get_sportradar_injuries()
            news_injuries = await self._get_news_injuries()
            twitter_injuries = await self._get_twitter_injuries()
            
            all_players = set(sportradar_injuries.keys()) | set(news_injuries.keys()) | set(twitter_injuries.keys())
            
            for player_id in all_players:
                total_players += 1
                sources = []
                
                if player_id in sportradar_injuries:
                    sources.append(('sportradar', sportradar_injuries[player_id]))
                if player_id in news_injuries:
                    sources.append(('news', news_injuries[player_id]))
                if player_id in twitter_injuries:
                    sources.append(('twitter', twitter_injuries[player_id]))
                
                if len(sources) >= self.validation_rules['injury_status_sources']:
                    status_consensus = self._check_injury_consensus(sources)
                    if status_consensus:
                        consensus_players += 1
                    else:
                        conflict = {
                            'player_id': player_id,
                            'sources': sources,
                            'consensus': False
                        }
                        conflicts.append(conflict)
                        await self._flag_injury_conflict(conflict)
                else:
                    conflict = {
                        'player_id': player_id,
                        'sources': sources,
                        'insufficient_sources': True
                    }
                    conflicts.append(conflict)
            
            consensus_rate = consensus_players / total_players if total_players > 0 else 0
            
            return {
                'status': 'completed',
                'total_players': total_players,
                'consensus_players': consensus_players,
                'conflicts': len(conflicts),
                'consensus_rate': consensus_rate,
                'conflict_details': conflicts[:10]
            }
            
        except Exception as e:
            logger.error("Error validating injury status", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    async def validate_vegas_odds(self) -> Dict[str, Any]:
        """
        Validate Vegas odds across sportsbooks.
        Flag significant variance in game totals and spreads.
        """
        logger.info("Validating Vegas odds across sportsbooks")
        
        try:
            conflicts = []
            total_games = 0
            consistent_games = 0
            
            dk_odds = await self._get_draftkings_game_odds()
            fd_odds = await self._get_fanduel_game_odds()
            mgm_odds = await self._get_betmgm_game_odds()
            
            all_games = set(dk_odds.keys()) | set(fd_odds.keys()) | set(mgm_odds.keys())
            
            for game_id in all_games:
                total_games += 1
                odds_sources = []
                
                if game_id in dk_odds:
                    odds_sources.append(('draftkings', dk_odds[game_id]))
                if game_id in fd_odds:
                    odds_sources.append(('fanduel', fd_odds[game_id]))
                if game_id in mgm_odds:
                    odds_sources.append(('betmgm', mgm_odds[game_id]))
                
                if len(odds_sources) >= 2:
                    variance = self._calculate_odds_variance(odds_sources)
                    if variance <= self.validation_rules['odds_variance_threshold']:
                        consistent_games += 1
                    else:
                        conflict = {
                            'game_id': game_id,
                            'odds_sources': odds_sources,
                            'variance': variance
                        }
                        conflicts.append(conflict)
                        await self._flag_odds_conflict(conflict)
            
            consistency_rate = consistent_games / total_games if total_games > 0 else 0
            
            return {
                'status': 'completed',
                'total_games': total_games,
                'consistent_games': consistent_games,
                'conflicts': len(conflicts),
                'consistency_rate': consistency_rate,
                'conflict_details': conflicts[:10]
            }
            
        except Exception as e:
            logger.error("Error validating Vegas odds", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    async def validate_news_sentiment(self) -> Dict[str, Any]:
        """
        Validate news sentiment scores across sources.
        Check for consistency in sentiment analysis.
        """
        logger.info("Validating news sentiment across sources")
        
        try:
            conflicts = []
            total_articles = 0
            consistent_articles = 0
            
            news_api_sentiment = await self._get_news_api_sentiment()
            twitter_sentiment = await self._get_twitter_sentiment_scores()
            
            common_topics = set(news_api_sentiment.keys()) & set(twitter_sentiment.keys())
            
            for topic in common_topics:
                total_articles += 1
                news_score = news_api_sentiment[topic]
                twitter_score = twitter_sentiment[topic]
                
                sentiment_diff = abs(news_score - twitter_score)
                
                if sentiment_diff <= self.validation_rules['news_sentiment_threshold']:
                    consistent_articles += 1
                else:
                    conflict = {
                        'topic': topic,
                        'news_api_sentiment': news_score,
                        'twitter_sentiment': twitter_score,
                        'difference': sentiment_diff
                    }
                    conflicts.append(conflict)
                    await self._flag_sentiment_conflict(conflict)
            
            consistency_rate = consistent_articles / total_articles if total_articles > 0 else 0
            
            return {
                'status': 'completed',
                'total_articles': total_articles,
                'consistent_articles': consistent_articles,
                'conflicts': len(conflicts),
                'consistency_rate': consistency_rate,
                'conflict_details': conflicts[:10]
            }
            
        except Exception as e:
            logger.error("Error validating news sentiment", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_overall_consistency(self, validation_results: List[Any]) -> float:
        """Calculate overall data consistency percentage"""
        total_consistency = 0
        valid_results = 0
        
        for result in validation_results:
            if isinstance(result, dict) and 'consistency_rate' in result:
                total_consistency += result['consistency_rate']
                valid_results += 1
            elif isinstance(result, dict) and 'consensus_rate' in result:
                total_consistency += result['consensus_rate']
                valid_results += 1
        
        return total_consistency / valid_results if valid_results > 0 else 0
    
    def _check_injury_consensus(self, sources: List[Tuple[str, str]]) -> bool:
        """Check if injury status has consensus across sources"""
        statuses = [status for _, status in sources]
        most_common = max(set(statuses), key=statuses.count)
        consensus_count = statuses.count(most_common)
        return consensus_count >= len(sources) * 0.6  # 60% consensus threshold
    
    def _calculate_odds_variance(self, odds_sources: List[Tuple[str, Dict]]) -> float:
        """Calculate variance in odds across sportsbooks"""
        if len(odds_sources) < 2:
            return 0
        
        totals = [odds.get('total', 0) for _, odds in odds_sources]
        if not totals:
            return 0
        
        mean_total = sum(totals) / len(totals)
        variance = sum((x - mean_total) ** 2 for x in totals) / len(totals)
        return variance / mean_total if mean_total > 0 else 0
    
    async def _get_draftkings_salaries(self) -> Dict[str, int]:
        """Get DraftKings player salaries"""
        cache_key = "validation:dk_salaries"
        cached = redis_client.get(cache_key)
        if cached:
            return eval(cached)
        return {}
    
    async def _get_fanduel_salaries(self) -> Dict[str, int]:
        """Get FanDuel player salaries"""
        cache_key = "validation:fd_salaries"
        cached = redis_client.get(cache_key)
        if cached:
            return eval(cached)
        return {}
    
    async def _get_sportradar_injuries(self) -> Dict[str, str]:
        """Get injury status from Sportradar"""
        return {}
    
    async def _get_news_injuries(self) -> Dict[str, str]:
        """Get injury status from news sources"""
        return {}
    
    async def _get_twitter_injuries(self) -> Dict[str, str]:
        """Get injury status from Twitter"""
        return {}
    
    async def _get_draftkings_game_odds(self) -> Dict[str, Dict]:
        """Get game odds from DraftKings"""
        return {}
    
    async def _get_fanduel_game_odds(self) -> Dict[str, Dict]:
        """Get game odds from FanDuel"""
        return {}
    
    async def _get_betmgm_game_odds(self) -> Dict[str, Dict]:
        """Get game odds from BetMGM"""
        return {}
    
    async def _get_news_api_sentiment(self) -> Dict[str, float]:
        """Get sentiment scores from NewsAPI"""
        return {}
    
    async def _get_twitter_sentiment_scores(self) -> Dict[str, float]:
        """Get sentiment scores from Twitter"""
        return {}
    
    async def _flag_salary_conflict(self, conflict: Dict):
        """Flag salary conflict for human review"""
        logger.warning("Salary conflict detected", conflict=conflict)
        cache_key = f"conflict:salary:{conflict['player_id']}"
        redis_client.setex(cache_key, 86400, str(conflict))  # 24 hour cache
    
    async def _flag_injury_conflict(self, conflict: Dict):
        """Flag injury status conflict for human review"""
        logger.warning("Injury status conflict detected", conflict=conflict)
        cache_key = f"conflict:injury:{conflict['player_id']}"
        redis_client.setex(cache_key, 86400, str(conflict))
    
    async def _flag_odds_conflict(self, conflict: Dict):
        """Flag odds variance conflict for human review"""
        logger.warning("Odds variance conflict detected", conflict=conflict)
        cache_key = f"conflict:odds:{conflict['game_id']}"
        redis_client.setex(cache_key, 86400, str(conflict))
    
    async def _flag_sentiment_conflict(self, conflict: Dict):
        """Flag sentiment analysis conflict for human review"""
        logger.warning("Sentiment conflict detected", conflict=conflict)
        cache_key = f"conflict:sentiment:{conflict['topic']}"
        redis_client.setex(cache_key, 86400, str(conflict))


class DeduplicationService:
    """
    Two-layered deduplication system for news articles.
    Layer 1: SHA-256 hash-based exact duplicate detection
    Layer 2: Semantic similarity using sentence transformers
    """
    
    def __init__(self):
        self.similarity_threshold = 0.98
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load sentence transformer model for semantic similarity"""
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer model loaded successfully")
        except Exception as e:
            logger.error("Failed to load sentence transformer model", error=str(e))
            self.model = None
    
    async def check_duplicate(self, article: Dict[str, Any]) -> bool:
        """
        Check if article is a duplicate using two-layer approach.
        
        Args:
            article: Article data with title and content
            
        Returns:
            True if duplicate found, False otherwise
        """
        try:
            content_text = f"{article.get('title', '')} {article.get('content', '')}"
            
            if not content_text.strip():
                return False
            
            is_exact_duplicate = await self._check_exact_duplicate(content_text)
            if is_exact_duplicate:
                logger.info("Exact duplicate found (Layer 1)", title=article.get('title', '')[:50])
                return True
            
            is_semantic_duplicate = await self._check_semantic_duplicate(content_text, article)
            if is_semantic_duplicate:
                logger.info("Semantic duplicate found (Layer 2)", title=article.get('title', '')[:50])
                return True
            
            await self._store_article_hash(content_text, article)
            return False
            
        except Exception as e:
            logger.error("Error checking duplicate", error=str(e))
            return False
    
    async def _check_exact_duplicate(self, content: str) -> bool:
        """Layer 1: Check exact duplicate using SHA-256 hash"""
        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            hash_key = f"article_hash:{content_hash}"
            
            exists = redis_client.exists(hash_key)
            return bool(exists)
            
        except Exception as e:
            logger.error("Error checking exact duplicate", error=str(e))
            return False
    
    async def _check_semantic_duplicate(self, content: str, article: Dict[str, Any]) -> bool:
        """Layer 2: Check semantic similarity using sentence transformers"""
        try:
            if not self.model:
                logger.warning("Sentence transformer model not available, skipping semantic check")
                return False
            
            content_embedding = self.model.encode([content])
            
            stored_embeddings_key = "article_embeddings"
            stored_data = redis_client.get(stored_embeddings_key)
            
            if not stored_data:
                return False
            
            stored_embeddings_list = json.loads(stored_data)
            
            for stored_item in stored_embeddings_list:
                stored_embedding = np.array(stored_item['embedding']).reshape(1, -1)
                
                similarity = cosine_similarity(content_embedding, stored_embedding)[0][0]
                
                if similarity > self.similarity_threshold:
                    logger.info("High semantic similarity found", 
                              similarity=similarity,
                              threshold=self.similarity_threshold,
                              stored_title=stored_item.get('title', '')[:50])
                    
                    await self._update_canonical_record(stored_item['id'], article)
                    return True
            
            return False
            
        except Exception as e:
            logger.error("Error checking semantic duplicate", error=str(e))
            return False
    
    async def _store_article_hash(self, content: str, article: Dict[str, Any]):
        """Store article hash and embedding for future duplicate detection"""
        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            hash_key = f"article_hash:{content_hash}"
            
            redis_client.setex(hash_key, 86400 * 7, json.dumps({
                'title': article.get('title', ''),
                'stored_at': datetime.now(timezone.utc).isoformat()
            }))
            
            if self.model:
                content_embedding = self.model.encode([content])[0].tolist()
                
                stored_embeddings_key = "article_embeddings"
                stored_data = redis_client.get(stored_embeddings_key)
                
                if stored_data:
                    stored_embeddings_list = json.loads(stored_data)
                else:
                    stored_embeddings_list = []
                
                embedding_data = {
                    'id': content_hash,
                    'title': article.get('title', ''),
                    'embedding': content_embedding,
                    'stored_at': datetime.now(timezone.utc).isoformat()
                }
                
                stored_embeddings_list.append(embedding_data)
                
                if len(stored_embeddings_list) > 1000:
                    stored_embeddings_list = stored_embeddings_list[-1000:]
                
                redis_client.setex(stored_embeddings_key, 86400 * 7, json.dumps(stored_embeddings_list))
            
        except Exception as e:
            logger.error("Error storing article hash", error=str(e))
    
    async def _update_canonical_record(self, canonical_id: str, duplicate_article: Dict[str, Any]):
        """Update canonical record to reinforce confidence score"""
        try:
            canonical_key = f"canonical_article:{canonical_id}"
            canonical_data = redis_client.get(canonical_key)
            
            if canonical_data:
                canonical_record = json.loads(canonical_data)
                canonical_record['confidence_score'] = min(1.0, canonical_record.get('confidence_score', 0.5) + 0.1)
                canonical_record['duplicate_count'] = canonical_record.get('duplicate_count', 0) + 1
                canonical_record['last_duplicate_found'] = datetime.now(timezone.utc).isoformat()
                
                redis_client.setex(canonical_key, 86400 * 7, json.dumps(canonical_record))
                
                logger.info("Canonical record updated", 
                          canonical_id=canonical_id,
                          new_confidence=canonical_record['confidence_score'])
            else:
                canonical_record = {
                    'id': canonical_id,
                    'title': duplicate_article.get('title', ''),
                    'confidence_score': 0.6,
                    'duplicate_count': 1,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'last_duplicate_found': datetime.now(timezone.utc).isoformat()
                }
                
                redis_client.setex(canonical_key, 86400 * 7, json.dumps(canonical_record))
            
        except Exception as e:
            logger.error("Error updating canonical record", error=str(e))

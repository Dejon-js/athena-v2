import asyncio
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from textblob import TextBlob
import structlog

from shared.database import get_db, redis_client

logger = structlog.get_logger()


class SentimentAnalyzer:
    """
    NLP sentiment analysis for news and social media content.
    Analyzes player and team sentiment to influence ownership predictions.
    """
    
    def __init__(self):
        self.player_keywords = {}
        self.team_keywords = {}
        self.sentiment_cache = {}
        
    async def analyze_news_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze sentiment from news articles.
        
        Args:
            articles: List of news articles with content
            
        Returns:
            Dict containing sentiment scores by player/team
        """
        logger.info("Analyzing news sentiment", articles=len(articles))
        
        try:
            sentiment_results = {
                'player_sentiment': {},
                'team_sentiment': {},
                'overall_sentiment': 0.0,
                'article_count': len(articles),
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            for article in articles:
                article_sentiment = await self._analyze_article_sentiment(article)
                
                for player_id, score in article_sentiment.get('players', {}).items():
                    if player_id not in sentiment_results['player_sentiment']:
                        sentiment_results['player_sentiment'][player_id] = []
                    sentiment_results['player_sentiment'][player_id].append(score)
                
                for team_id, score in article_sentiment.get('teams', {}).items():
                    if team_id not in sentiment_results['team_sentiment']:
                        sentiment_results['team_sentiment'][team_id] = []
                    sentiment_results['team_sentiment'][team_id].append(score)
            
            sentiment_results['player_sentiment'] = {
                player_id: self._aggregate_sentiment_scores(scores)
                for player_id, scores in sentiment_results['player_sentiment'].items()
            }
            
            sentiment_results['team_sentiment'] = {
                team_id: self._aggregate_sentiment_scores(scores)
                for team_id, scores in sentiment_results['team_sentiment'].items()
            }
            
            all_scores = []
            all_scores.extend(sentiment_results['player_sentiment'].values())
            all_scores.extend(sentiment_results['team_sentiment'].values())
            
            if all_scores:
                sentiment_results['overall_sentiment'] = sum(all_scores) / len(all_scores)
            
            logger.info("News sentiment analysis completed", 
                       players=len(sentiment_results['player_sentiment']),
                       teams=len(sentiment_results['team_sentiment']))
            
            return sentiment_results
            
        except Exception as e:
            logger.error("Error analyzing news sentiment", error=str(e))
            raise
    
    async def _analyze_article_sentiment(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment for individual article"""
        
        title = article.get('title', '')
        content = article.get('content', '') or article.get('description', '')
        
        full_text = f"{title} {content}"
        
        if not full_text.strip():
            return {'players': {}, 'teams': {}, 'overall': 0.0}
        
        blob = TextBlob(full_text)
        overall_sentiment = blob.sentiment.polarity
        
        extracted_players = await self._extract_player_mentions(full_text)
        extracted_teams = await self._extract_team_mentions(full_text)
        
        player_sentiments = {}
        for player_id in extracted_players:
            player_context = self._extract_player_context(full_text, player_id)
            if player_context:
                player_blob = TextBlob(player_context)
                player_sentiments[player_id] = player_blob.sentiment.polarity
            else:
                player_sentiments[player_id] = overall_sentiment
        
        team_sentiments = {}
        for team_id in extracted_teams:
            team_context = self._extract_team_context(full_text, team_id)
            if team_context:
                team_blob = TextBlob(team_context)
                team_sentiments[team_id] = team_blob.sentiment.polarity
            else:
                team_sentiments[team_id] = overall_sentiment
        
        return {
            'players': player_sentiments,
            'teams': team_sentiments,
            'overall': overall_sentiment
        }
    
    async def _extract_player_mentions(self, text: str) -> List[str]:
        """Extract player mentions from text"""
        
        common_players = [
            'patrick mahomes', 'josh allen', 'lamar jackson', 'joe burrow',
            'christian mccaffrey', 'derrick henry', 'alvin kamara', 'nick chubb',
            'cooper kupp', 'davante adams', 'tyreek hill', 'stefon diggs',
            'travis kelce', 'mark andrews', 'george kittle', 'darren waller'
        ]
        
        mentioned_players = []
        text_lower = text.lower()
        
        for player in common_players:
            if player in text_lower:
                player_id = player.replace(' ', '_').replace("'", "")
                mentioned_players.append(player_id)
        
        return mentioned_players
    
    async def _extract_team_mentions(self, text: str) -> List[str]:
        """Extract team mentions from text"""
        
        team_names = {
            'chiefs': 'KC', 'bills': 'BUF', 'ravens': 'BAL', 'bengals': 'CIN',
            'panthers': 'CAR', 'titans': 'TEN', 'saints': 'NO', 'browns': 'CLE',
            'rams': 'LAR', 'packers': 'GB', 'dolphins': 'MIA', 'chargers': 'LAC',
            '49ers': 'SF', 'raiders': 'LV', 'eagles': 'PHI', 'cowboys': 'DAL'
        }
        
        mentioned_teams = []
        text_lower = text.lower()
        
        for team_name, team_id in team_names.items():
            if team_name in text_lower:
                mentioned_teams.append(team_id)
        
        return mentioned_teams
    
    def _extract_player_context(self, text: str, player_id: str) -> str:
        """Extract context around player mention"""
        
        player_name = player_id.replace('_', ' ')
        
        sentences = text.split('.')
        
        for sentence in sentences:
            if player_name.lower() in sentence.lower():
                return sentence.strip()
        
        return ""
    
    def _extract_team_context(self, text: str, team_id: str) -> str:
        """Extract context around team mention"""
        
        sentences = text.split('.')
        
        for sentence in sentences:
            if team_id.lower() in sentence.lower():
                return sentence.strip()
        
        return ""
    
    def _aggregate_sentiment_scores(self, scores: List[float]) -> float:
        """Aggregate multiple sentiment scores"""
        
        if not scores:
            return 0.0
        
        return sum(scores) / len(scores)
    
    async def analyze_social_sentiment(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment from social media posts"""
        
        logger.info("Analyzing social media sentiment", posts=len(posts))
        
        try:
            sentiment_results = {
                'player_sentiment': {},
                'team_sentiment': {},
                'trending_topics': [],
                'post_count': len(posts),
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            for post in posts:
                post_sentiment = await self._analyze_post_sentiment(post)
                
                for player_id, score in post_sentiment.get('players', {}).items():
                    if player_id not in sentiment_results['player_sentiment']:
                        sentiment_results['player_sentiment'][player_id] = []
                    sentiment_results['player_sentiment'][player_id].append(score)
                
                for team_id, score in post_sentiment.get('teams', {}).items():
                    if team_id not in sentiment_results['team_sentiment']:
                        sentiment_results['team_sentiment'][team_id] = []
                    sentiment_results['team_sentiment'][team_id].append(score)
            
            sentiment_results['player_sentiment'] = {
                player_id: self._aggregate_sentiment_scores(scores)
                for player_id, scores in sentiment_results['player_sentiment'].items()
            }
            
            sentiment_results['team_sentiment'] = {
                team_id: self._aggregate_sentiment_scores(scores)
                for team_id, scores in sentiment_results['team_sentiment'].items()
            }
            
            logger.info("Social media sentiment analysis completed")
            
            return sentiment_results
            
        except Exception as e:
            logger.error("Error analyzing social sentiment", error=str(e))
            raise
    
    async def _analyze_post_sentiment(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment for individual social media post"""
        
        content = post.get('content', '')
        
        if not content.strip():
            return {'players': {}, 'teams': {}, 'overall': 0.0}
        
        blob = TextBlob(content)
        overall_sentiment = blob.sentiment.polarity
        
        extracted_players = await self._extract_player_mentions(content)
        extracted_teams = await self._extract_team_mentions(content)
        
        player_sentiments = {player_id: overall_sentiment for player_id in extracted_players}
        team_sentiments = {team_id: overall_sentiment for team_id in extracted_teams}
        
        return {
            'players': player_sentiments,
            'teams': team_sentiments,
            'overall': overall_sentiment
        }
    
    async def get_player_sentiment_score(self, player_id: str) -> float:
        """Get aggregated sentiment score for player"""
        
        cache_key = f"sentiment:player:{player_id}"
        cached_score = redis_client.get(cache_key)
        
        if cached_score:
            return float(cached_score)
        
        return 0.0
    
    async def get_team_sentiment_score(self, team_id: str) -> float:
        """Get aggregated sentiment score for team"""
        
        cache_key = f"sentiment:team:{team_id}"
        cached_score = redis_client.get(cache_key)
        
        if cached_score:
            return float(cached_score)
        
        return 0.0
    
    async def store_sentiment_scores(self, sentiment_data: Dict[str, Any]):
        """Store sentiment scores in cache"""
        
        for player_id, score in sentiment_data.get('player_sentiment', {}).items():
            cache_key = f"sentiment:player:{player_id}"
            redis_client.setex(cache_key, 3600, str(score))
        
        for team_id, score in sentiment_data.get('team_sentiment', {}).items():
            cache_key = f"sentiment:team:{team_id}"
            redis_client.setex(cache_key, 3600, str(score))
        
        logger.info("Sentiment scores stored in cache")

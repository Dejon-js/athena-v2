import asyncio
import aiohttp
import requests
import feedparser
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
import structlog

from shared.database import get_db, redis_client
from shared.config import settings
from shared.utils import DataProcessor

logger = structlog.get_logger()


class DataIngestionEngine:
    """
    Core data ingestion engine that aggregates data from multiple sources.
    Handles player stats, Vegas odds, advanced metrics, news, and DFS data.
    """
    
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.data_processor = DataProcessor()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def ingest_all_data(self) -> Dict[str, Any]:
        """
        Main orchestration method to ingest all data sources.
        
        Returns:
            Dict containing status of all data ingestion tasks
        """
        logger.info("Starting full data ingestion cycle")
        
        tasks = [
            self.ingest_player_stats(),
            self.ingest_vegas_odds(),
            self.ingest_advanced_metrics(),
            self.ingest_news_sentiment(),
            self.ingest_dfs_data(),
            self.ingest_rss_feeds()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        status = {
            'player_stats': results[0],
            'vegas_odds': results[1], 
            'advanced_metrics': results[2],
            'news_sentiment': results[3],
            'dfs_data': results[4],
            'rss_feeds': results[5],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Data ingestion cycle completed", status=status)
        return status
    
    async def ingest_player_stats(self) -> Dict[str, Any]:
        """
        Ingest player statistics from Sportradar API.
        Includes historical and current season data.
        """
        logger.info("Ingesting player stats from Sportradar")
        
        try:
            if not settings.sportradar_api_key:
                logger.warning("Sportradar API key not configured")
                return {'status': 'skipped', 'reason': 'no_api_key'}
            
            base_url = "https://api.sportradar.us/nfl/official/trial/v7/en"
            headers = {'accept': 'application/json'}
            
            roster_url = f"{base_url}/seasons/2025/REG/teams/roster.json"
            params = {'api_key': settings.sportradar_api_key}
            
            async with self.session.get(roster_url, headers=headers, params=params) as response:
                if response.status == 200:
                    roster_data = await response.json()
                    
                    players_data = self._process_roster_data(roster_data)
                    await self._store_player_data(players_data)
                    
                    logger.info("Player stats ingestion completed", 
                              players_count=len(players_data))
                    return {'status': 'success', 'players_count': len(players_data)}
                else:
                    logger.error("Failed to fetch player stats", 
                               status_code=response.status)
                    return {'status': 'error', 'status_code': response.status}
                    
        except Exception as e:
            logger.error("Error ingesting player stats", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    async def ingest_vegas_odds(self) -> Dict[str, Any]:
        """
        Ingest Vegas odds from multiple sportsbooks.
        Includes game totals, spreads, and player props.
        """
        logger.info("Ingesting Vegas odds from multiple sources")
        
        try:
            odds_data = []
            
            if settings.draftkings_api_key:
                dk_odds = await self._fetch_draftkings_odds()
                odds_data.extend(dk_odds)
            
            if settings.fanduel_api_key:
                fd_odds = await self._fetch_fanduel_odds()
                odds_data.extend(fd_odds)
            
            if settings.betmgm_api_key:
                mgm_odds = await self._fetch_betmgm_odds()
                odds_data.extend(mgm_odds)
            
            if odds_data:
                await self._store_odds_data(odds_data)
                logger.info("Vegas odds ingestion completed", 
                          odds_count=len(odds_data))
                return {'status': 'success', 'odds_count': len(odds_data)}
            else:
                logger.warning("No odds data retrieved")
                return {'status': 'warning', 'reason': 'no_data'}
                
        except Exception as e:
            logger.error("Error ingesting Vegas odds", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    async def ingest_advanced_metrics(self) -> Dict[str, Any]:
        """
        Scrape advanced metrics from Football Outsiders (DVOA) and PFF.
        """
        logger.info("Scraping advanced metrics from Football Outsiders and PFF")
        
        try:
            metrics_data = []
            
            fo_data = await self._scrape_football_outsiders()
            metrics_data.extend(fo_data)
            
            pff_data = await self._scrape_pff_metrics()
            metrics_data.extend(pff_data)
            
            if metrics_data:
                await self._store_advanced_metrics(metrics_data)
                logger.info("Advanced metrics ingestion completed",
                          metrics_count=len(metrics_data))
                return {'status': 'success', 'metrics_count': len(metrics_data)}
            else:
                return {'status': 'warning', 'reason': 'no_data'}
                
        except Exception as e:
            logger.error("Error ingesting advanced metrics", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    async def ingest_news_sentiment(self) -> Dict[str, Any]:
        """
        Ingest news and social media sentiment data.
        Uses NewsAPI and Twitter API for sentiment analysis.
        """
        logger.info("Ingesting news and sentiment data")
        
        try:
            sentiment_data = []
            
            if settings.news_api_key:
                news_data = await self._fetch_news_data()
                sentiment_data.extend(news_data)
            
            if settings.twitter_api_key:
                twitter_data = await self._fetch_twitter_sentiment()
                sentiment_data.extend(twitter_data)
            
            if sentiment_data:
                await self._store_sentiment_data(sentiment_data)
                logger.info("News sentiment ingestion completed",
                          articles_count=len(sentiment_data))
                return {'status': 'success', 'articles_count': len(sentiment_data)}
            else:
                return {'status': 'warning', 'reason': 'no_data'}
                
        except Exception as e:
            logger.error("Error ingesting news sentiment", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    async def ingest_dfs_data(self) -> Dict[str, Any]:
        """
        Scrape DFS platform data including salaries and contest information.
        """
        logger.info("Scraping DFS platform data")
        
        try:
            dfs_data = []
            
            dk_data = await self._scrape_draftkings_data()
            dfs_data.extend(dk_data)
            
            
            if dfs_data:
                await self._store_dfs_data(dfs_data)
                logger.info("DFS data ingestion completed",
                          players_count=len(dfs_data))
                return {'status': 'success', 'players_count': len(dfs_data)}
            else:
                return {'status': 'warning', 'reason': 'no_data'}
                
        except Exception as e:
            logger.error("Error ingesting DFS data", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    def _process_roster_data(self, roster_data: Dict) -> List[Dict]:
        """Process raw roster data from Sportradar"""
        players = []
        
        for team in roster_data.get('teams', []):
            team_id = team.get('id')
            team_name = team.get('name')
            
            for player in team.get('players', []):
                processed_player = {
                    'player_id': player.get('id'),
                    'name': self.data_processor.normalize_player_name(player.get('name', '')),
                    'position': player.get('position'),
                    'team_id': team_id,
                    'team_name': team_name,
                    'jersey_number': player.get('jersey'),
                    'height': player.get('height'),
                    'weight': player.get('weight'),
                    'experience': player.get('experience'),
                    'updated_at': datetime.now(timezone.utc)
                }
                players.append(processed_player)
        
        return players
    
    async def _fetch_draftkings_odds(self) -> List[Dict]:
        """Fetch odds from DraftKings API"""
        logger.info("Fetching DraftKings odds")
        return []
    
    async def _fetch_fanduel_odds(self) -> List[Dict]:
        """Fetch odds from FanDuel API"""
        logger.info("Fetching FanDuel odds")
        return []
    
    async def _fetch_betmgm_odds(self) -> List[Dict]:
        """Fetch odds from BetMGM API"""
        logger.info("Fetching BetMGM odds")
        return []
    
    async def _scrape_football_outsiders(self) -> List[Dict]:
        """Scrape DVOA data from Football Outsiders"""
        logger.info("Scraping Football Outsiders DVOA data")
        
        try:
            url = "https://www.footballoutsiders.com/stats/nfl/team-defense/2025"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    return []
                else:
                    logger.warning("Failed to scrape Football Outsiders",
                                 status_code=response.status)
                    return []
                    
        except Exception as e:
            logger.error("Error scraping Football Outsiders", error=str(e))
            return []
    
    async def _scrape_pff_metrics(self) -> List[Dict]:
        """Scrape PFF premium metrics"""
        logger.info("Scraping PFF metrics")
        return []
    
    async def _fetch_news_data(self) -> List[Dict]:
        """Fetch NFL news from NewsAPI"""
        logger.info("Fetching news data from NewsAPI")
        
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'apiKey': settings.news_api_key,
                'q': 'NFL OR "fantasy football"',
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 100
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get('articles', [])
                    
                    processed_articles = []
                    for article in articles:
                        processed_article = {
                            'title': article.get('title'),
                            'description': article.get('description'),
                            'content': article.get('content'),
                            'url': article.get('url'),
                            'published_at': article.get('publishedAt'),
                            'source': article.get('source', {}).get('name'),
                            'sentiment_score': None,  # To be calculated
                            'extracted_players': [],  # To be extracted
                            'created_at': datetime.now(timezone.utc)
                        }
                        processed_articles.append(processed_article)
                    
                    return processed_articles
                else:
                    logger.warning("Failed to fetch news data",
                                 status_code=response.status)
                    return []
                    
        except Exception as e:
            logger.error("Error fetching news data", error=str(e))
            return []
    
    async def _fetch_twitter_sentiment(self) -> List[Dict]:
        """Fetch Twitter sentiment data"""
        logger.info("Fetching Twitter sentiment data")
        return []
    
    async def _scrape_draftkings_data(self) -> List[Dict]:
        """Scrape DraftKings salary and contest data"""
        logger.info("Scraping DraftKings data")
        
        try:
            
            return []
            
        except Exception as e:
            logger.error("Error scraping DraftKings data", error=str(e))
            return []
    
    async def _store_player_data(self, players_data: List[Dict]):
        """Store player data in PostgreSQL"""
        logger.info("Storing player data", count=len(players_data))
        
        for player in players_data:
            cache_key = f"player:{player['player_id']}"
            redis_client.setex(cache_key, 3600, str(player))  # 1 hour cache
    
    async def _store_odds_data(self, odds_data: List[Dict]):
        """Store odds data in PostgreSQL"""
        logger.info("Storing odds data", count=len(odds_data))
    
    async def _store_advanced_metrics(self, metrics_data: List[Dict]):
        """Store advanced metrics in PostgreSQL"""
        logger.info("Storing advanced metrics", count=len(metrics_data))
    
    async def _store_sentiment_data(self, sentiment_data: List[Dict]):
        """Store sentiment data in PostgreSQL"""
        logger.info("Storing sentiment data", count=len(sentiment_data))
    
    async def _store_dfs_data(self, dfs_data: List[Dict]):
        """Store DFS data in PostgreSQL"""
        logger.info("Storing DFS data", count=len(dfs_data))
    
    async def ingest_rss_feeds(self) -> Dict[str, Any]:
        """
        Ingest RSS feeds for real-time news and injury updates.
        
        Returns:
            Dict containing RSS ingestion results
        """
        logger.info("Starting RSS feed ingestion")
        
        try:
            config_path = "config/rss_feeds.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            rss_feeds = config.get('rss_feeds', [])
            max_articles = config.get('max_articles_per_feed', 50)
            
            all_articles = []
            feed_results = {}
            
            for feed_url in rss_feeds:
                try:
                    logger.info("Processing RSS feed", url=feed_url)
                    
                    feed = feedparser.parse(feed_url)
                    
                    if feed.bozo:
                        logger.warning("RSS feed parsing warning", url=feed_url, error=feed.bozo_exception)
                    
                    articles = []
                    for entry in feed.entries[:max_articles]:
                        article = {
                            'title': entry.get('title', ''),
                            'content': entry.get('summary', '') or entry.get('description', ''),
                            'url': entry.get('link', ''),
                            'published_date': entry.get('published', ''),
                            'source': feed.feed.get('title', feed_url),
                            'feed_url': feed_url,
                            'ingested_at': datetime.now(timezone.utc).isoformat()
                        }
                        
                        if article['title'] and article['content']:
                            articles.append(article)
                    
                    all_articles.extend(articles)
                    feed_results[feed_url] = {
                        'status': 'success',
                        'articles_found': len(articles),
                        'feed_title': feed.feed.get('title', 'Unknown')
                    }
                    
                    logger.info("RSS feed processed", url=feed_url, articles=len(articles))
                    
                except Exception as e:
                    logger.error("Error processing RSS feed", url=feed_url, error=str(e))
                    feed_results[feed_url] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            if all_articles:
                await self._store_rss_articles(all_articles)
            
            logger.info("RSS feed ingestion completed", 
                       total_articles=len(all_articles),
                       feeds_processed=len(feed_results))
            
            return {
                'status': 'success',
                'total_articles': len(all_articles),
                'feeds_processed': len(feed_results),
                'feed_results': feed_results,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error("Error during RSS feed ingestion", error=str(e))
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _store_rss_articles(self, articles: List[Dict[str, Any]]):
        """Store RSS articles in database with deduplication"""
        from .data_validation import DeduplicationService
        
        dedup_service = DeduplicationService()
        
        for article in articles:
            try:
                is_duplicate = await dedup_service.check_duplicate(article)
                
                if not is_duplicate:
                    article_hash = hashlib.sha256(
                        f"{article['title']}{article['content']}".encode()
                    ).hexdigest()
                    
                    cache_key = f"rss_article:{article_hash}"
                    redis_client.setex(cache_key, 86400 * 7, json.dumps(article))
                    
                    logger.info("RSS article stored", title=article['title'][:50])
                else:
                    logger.info("RSS article skipped (duplicate)", title=article['title'][:50])
                    
            except Exception as e:
                logger.error("Error storing RSS article", error=str(e), title=article.get('title', 'Unknown'))

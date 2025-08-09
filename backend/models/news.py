from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class NewsArticle(Base, TimestampMixin):
    __tablename__ = 'news_articles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String(1000), nullable=False, unique=True)
    
    source = Column(String(100), nullable=False, index=True)
    author = Column(String(200), nullable=True)
    published_at = Column(DateTime, nullable=False, index=True)
    
    extracted_players = Column(JSON, nullable=True)  # List of player IDs mentioned
    extracted_teams = Column(JSON, nullable=True)   # List of team IDs mentioned
    
    sentiment_scores = relationship("SentimentScore", back_populates="article", cascade="all, delete-orphan")


class SentimentScore(Base, TimestampMixin):
    __tablename__ = 'sentiment_scores'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey('news_articles.id'), nullable=False, index=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=True, index=True)
    team_id = Column(String(10), nullable=True, index=True)
    
    sentiment_score = Column(Float, nullable=False)  # -1 to 1 scale
    confidence = Column(Float, nullable=True)        # 0 to 1 scale
    
    sentiment_method = Column(String(50), nullable=False)  # 'textblob', 'vader', 'transformers'
    
    keywords = Column(JSON, nullable=True)  # Keywords that influenced sentiment
    
    article = relationship("NewsArticle", back_populates="sentiment_scores")
    player = relationship("Player")


class SocialMediaPost(Base, TimestampMixin):
    __tablename__ = 'social_media_posts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, index=True)  # 'twitter', 'reddit'
    post_id = Column(String(100), nullable=False, unique=True)
    
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=True)
    posted_at = Column(DateTime, nullable=False, index=True)
    
    likes = Column(Integer, nullable=True)
    retweets = Column(Integer, nullable=True)
    replies = Column(Integer, nullable=True)
    
    extracted_players = Column(JSON, nullable=True)
    extracted_teams = Column(JSON, nullable=True)
    
    sentiment_score = Column(Float, nullable=True)
    influence_score = Column(Float, nullable=True)  # Based on author followers, engagement


class MediaNarrative(Base, TimestampMixin):
    __tablename__ = 'media_narratives'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=True, index=True)
    team_id = Column(String(10), nullable=True, index=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    narrative_type = Column(String(50), nullable=False, index=True)  # 'injury', 'breakout', 'bust', 'matchup'
    narrative_text = Column(Text, nullable=False)
    
    strength = Column(Float, nullable=False)  # How strong the narrative is (0-1)
    recency = Column(Float, nullable=False)   # How recent the narrative is (0-1)
    
    source_count = Column(Integer, nullable=False)  # Number of sources mentioning this narrative
    
    player = relationship("Player")

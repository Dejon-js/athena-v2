from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Game(Base, TimestampMixin):
    __tablename__ = 'games'
    
    id = Column(String(50), primary_key=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    home_team_id = Column(String(10), nullable=False, index=True)
    away_team_id = Column(String(10), nullable=False, index=True)
    home_team_name = Column(String(50), nullable=False)
    away_team_name = Column(String(50), nullable=False)
    
    game_time = Column(DateTime, nullable=False, index=True)
    weather = Column(JSON, nullable=True)
    
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    is_final = Column(Boolean, default=False, nullable=False)
    
    odds = relationship("GameOdds", back_populates="game", cascade="all, delete-orphan")


class GameOdds(Base, TimestampMixin):
    __tablename__ = 'game_odds'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(50), ForeignKey('games.id'), nullable=False, index=True)
    sportsbook = Column(String(20), nullable=False, index=True)  # 'draftkings', 'fanduel', 'betmgm'
    
    home_spread = Column(Float, nullable=True)
    away_spread = Column(Float, nullable=True)
    total_points = Column(Float, nullable=True)
    
    home_moneyline = Column(Integer, nullable=True)
    away_moneyline = Column(Integer, nullable=True)
    
    home_total_implied = Column(Float, nullable=True)
    away_total_implied = Column(Float, nullable=True)
    
    game = relationship("Game", back_populates="odds")


class TeamStats(Base, TimestampMixin):
    __tablename__ = 'team_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(10), nullable=False, index=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    points_scored = Column(Float, nullable=True)
    points_allowed = Column(Float, nullable=True)
    
    total_yards = Column(Float, nullable=True)
    passing_yards = Column(Float, nullable=True)
    rushing_yards = Column(Float, nullable=True)
    
    total_yards_allowed = Column(Float, nullable=True)
    passing_yards_allowed = Column(Float, nullable=True)
    rushing_yards_allowed = Column(Float, nullable=True)
    
    turnovers = Column(Integer, nullable=True)
    turnovers_forced = Column(Integer, nullable=True)
    
    dvoa_offense = Column(Float, nullable=True)
    dvoa_defense = Column(Float, nullable=True)
    
    pace = Column(Float, nullable=True)  # Plays per game


class AdvancedMetrics(Base, TimestampMixin):
    __tablename__ = 'advanced_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    pff_grade = Column(Float, nullable=True)
    pff_receiving_grade = Column(Float, nullable=True)
    pff_run_blocking_grade = Column(Float, nullable=True)
    
    target_share = Column(Float, nullable=True)
    air_yards_share = Column(Float, nullable=True)
    red_zone_targets = Column(Integer, nullable=True)
    
    carries_inside_5 = Column(Integer, nullable=True)
    goal_line_carries = Column(Integer, nullable=True)
    
    pressure_rate = Column(Float, nullable=True)  # For QBs
    time_to_throw = Column(Float, nullable=True)  # For QBs
    
    player = relationship("Player")

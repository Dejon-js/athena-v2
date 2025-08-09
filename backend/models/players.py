from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, AuditMixin


class Player(Base, TimestampMixin):
    __tablename__ = 'players'
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    normalized_name = Column(String(100), nullable=False, index=True)
    position = Column(String(10), nullable=False, index=True)
    team_id = Column(String(10), nullable=False, index=True)
    team_name = Column(String(50), nullable=False)
    jersey_number = Column(Integer, nullable=True)
    height = Column(String(10), nullable=True)
    weight = Column(Integer, nullable=True)
    experience = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    stats = relationship("PlayerStats", back_populates="player", cascade="all, delete-orphan")
    projections = relationship("PlayerProjection", back_populates="player", cascade="all, delete-orphan")


class PlayerStats(Base, TimestampMixin):
    __tablename__ = 'player_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    game_id = Column(String(50), nullable=True, index=True)
    
    passing_yards = Column(Float, nullable=True)
    passing_tds = Column(Integer, nullable=True)
    passing_interceptions = Column(Integer, nullable=True)
    passing_attempts = Column(Integer, nullable=True)
    passing_completions = Column(Integer, nullable=True)
    
    rushing_yards = Column(Float, nullable=True)
    rushing_tds = Column(Integer, nullable=True)
    rushing_attempts = Column(Integer, nullable=True)
    
    receiving_yards = Column(Float, nullable=True)
    receiving_tds = Column(Integer, nullable=True)
    receptions = Column(Integer, nullable=True)
    targets = Column(Integer, nullable=True)
    
    fantasy_points = Column(Float, nullable=True, index=True)
    dk_points = Column(Float, nullable=True)
    fd_points = Column(Float, nullable=True)
    
    snap_count = Column(Integer, nullable=True)
    snap_percentage = Column(Float, nullable=True)
    
    player = relationship("Player", back_populates="stats")


class PlayerProjection(Base, TimestampMixin, AuditMixin):
    __tablename__ = 'player_projections'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    projected_points = Column(Float, nullable=False)
    ceiling_points = Column(Float, nullable=False)
    floor_points = Column(Float, nullable=False)
    
    projected_ownership = Column(Float, nullable=True)
    leverage_score = Column(Float, nullable=True)
    
    passing_yards_proj = Column(Float, nullable=True)
    passing_tds_proj = Column(Float, nullable=True)
    rushing_yards_proj = Column(Float, nullable=True)
    rushing_tds_proj = Column(Float, nullable=True)
    receiving_yards_proj = Column(Float, nullable=True)
    receiving_tds_proj = Column(Float, nullable=True)
    receptions_proj = Column(Float, nullable=True)
    
    confidence_score = Column(Float, nullable=True)
    model_version = Column(String(20), nullable=True)
    
    simulation_data = Column(JSON, nullable=True)
    
    player = relationship("Player", back_populates="projections")


class PlayerSalary(Base, TimestampMixin):
    __tablename__ = 'player_salaries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    platform = Column(String(20), nullable=False, index=True)  # 'draftkings', 'fanduel'
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    salary = Column(Integer, nullable=False)
    position = Column(String(10), nullable=False)
    
    player = relationship("Player")


class InjuryReport(Base, TimestampMixin):
    __tablename__ = 'injury_reports'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    status = Column(String(20), nullable=False, index=True)  # 'out', 'doubtful', 'questionable', 'probable'
    injury_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    
    source = Column(String(50), nullable=False)  # 'sportradar', 'news', 'twitter'
    confidence = Column(Float, nullable=True)
    
    player = relationship("Player")

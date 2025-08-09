from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, AuditMixin


class Lineup(Base, TimestampMixin, AuditMixin):
    __tablename__ = 'lineups'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    total_salary = Column(Integer, nullable=False)
    projected_points = Column(Float, nullable=False)
    ceiling_points = Column(Float, nullable=False)
    floor_points = Column(Float, nullable=False)
    
    projected_ownership = Column(Float, nullable=True)
    leverage_score = Column(Float, nullable=True)
    
    optimization_run_id = Column(String(50), nullable=True, index=True)
    portfolio_rank = Column(Integer, nullable=True)  # Rank within the 150-lineup portfolio
    
    is_submitted = Column(Boolean, default=False, nullable=False)
    actual_points = Column(Float, nullable=True)
    contest_rank = Column(Integer, nullable=True)
    
    players = relationship("LineupPlayer", back_populates="lineup", cascade="all, delete-orphan")


class LineupPlayer(Base, TimestampMixin):
    __tablename__ = 'lineup_players'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lineup_id = Column(Integer, ForeignKey('lineups.id'), nullable=False, index=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    
    position = Column(String(10), nullable=False)  # QB, RB, WR, TE, FLEX, DST
    salary = Column(Integer, nullable=False)
    projected_points = Column(Float, nullable=False)
    actual_points = Column(Float, nullable=True)
    
    lineup = relationship("Lineup", back_populates="players")
    player = relationship("Player")


class OptimizationRun(Base, TimestampMixin, AuditMixin):
    __tablename__ = 'optimization_runs'
    
    id = Column(String(50), primary_key=True)  # UUID
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    objective_function = Column(String(100), nullable=False)  # 'leveraged_ceiling'
    constraints = Column(JSON, nullable=False)  # Optimization constraints used
    
    total_lineups = Column(Integer, nullable=False)
    execution_time_seconds = Column(Float, nullable=False)
    
    avg_projected_points = Column(Float, nullable=True)
    avg_leverage_score = Column(Float, nullable=True)
    
    status = Column(String(20), nullable=False, index=True)  # 'running', 'completed', 'failed'
    error_message = Column(Text, nullable=True)
    
    model_versions = Column(JSON, nullable=True)  # Versions of models used


class StackingRule(Base, TimestampMixin):
    __tablename__ = 'stacking_rules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    rule_type = Column(String(20), nullable=False, index=True)  # 'qb_stack', 'game_stack', 'team_stack'
    positions = Column(JSON, nullable=False)  # List of positions involved
    
    min_players = Column(Integer, nullable=False)
    max_players = Column(Integer, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=1, nullable=False)


class ExposureLimit(Base, TimestampMixin):
    __tablename__ = 'exposure_limits'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    min_exposure = Column(Float, nullable=True)  # Minimum exposure (0-1)
    max_exposure = Column(Float, nullable=True)  # Maximum exposure (0-1)
    
    reason = Column(String(200), nullable=True)  # Why this limit was set
    
    player = relationship("Player")

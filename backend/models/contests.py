from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Contest(Base, TimestampMixin):
    __tablename__ = 'contests'
    
    id = Column(String(50), primary_key=True)
    platform = Column(String(20), nullable=False, index=True)  # 'draftkings', 'fanduel'
    name = Column(String(200), nullable=False)
    
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    entry_fee = Column(Float, nullable=False)
    total_entries = Column(Integer, nullable=False)
    max_entries = Column(Integer, nullable=False)
    
    prize_pool = Column(Float, nullable=False)
    first_place_prize = Column(Float, nullable=False)
    
    start_time = Column(DateTime, nullable=False, index=True)
    is_live = Column(Boolean, default=False, nullable=False)
    is_complete = Column(Boolean, default=False, nullable=False)
    
    contest_type = Column(String(20), nullable=False, index=True)  # 'gpp', 'cash', 'satellite'
    
    entries = relationship("ContestEntry", back_populates="contest", cascade="all, delete-orphan")


class ContestEntry(Base, TimestampMixin):
    __tablename__ = 'contest_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(String(50), ForeignKey('contests.id'), nullable=False, index=True)
    lineup_id = Column(Integer, ForeignKey('lineups.id'), nullable=False, index=True)
    
    entry_number = Column(Integer, nullable=False)  # Entry number within contest
    
    final_rank = Column(Integer, nullable=True)
    final_points = Column(Float, nullable=True)
    prize_won = Column(Float, nullable=True)
    
    contest = relationship("Contest", back_populates="entries")
    lineup = relationship("Lineup")


class ContestResult(Base, TimestampMixin):
    __tablename__ = 'contest_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(String(50), ForeignKey('contests.id'), nullable=False, index=True)
    
    our_best_finish = Column(Integer, nullable=True)
    our_entries_count = Column(Integer, nullable=False)
    our_total_winnings = Column(Float, nullable=True)
    
    roi = Column(Float, nullable=True)  # Return on investment
    
    winning_lineup = Column(JSON, nullable=True)  # Contest winning lineup for analysis
    winning_score = Column(Float, nullable=True)
    
    contest = relationship("Contest")


class PerformanceMetrics(Base, TimestampMixin):
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    week = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)
    
    total_entries = Column(Integer, nullable=False)
    total_investment = Column(Float, nullable=False)
    total_winnings = Column(Float, nullable=False)
    
    weekly_roi = Column(Float, nullable=False)
    cumulative_roi = Column(Float, nullable=False)
    
    best_finish = Column(Integer, nullable=True)
    avg_finish_percentile = Column(Float, nullable=True)
    
    projection_accuracy = Column(Float, nullable=True)  # MAE of projections vs actual
    ownership_accuracy = Column(Float, nullable=True)   # MAE of ownership vs actual
    
    top_1_percent_finishes = Column(Integer, nullable=False, default=0)
    top_5_percent_finishes = Column(Integer, nullable=False, default=0)
    top_10_percent_finishes = Column(Integer, nullable=False, default=0)

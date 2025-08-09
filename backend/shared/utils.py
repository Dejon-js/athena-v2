import logging
import structlog
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from .config import settings

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def get_current_nfl_week() -> int:
    """
    Determine the current NFL week based on the date.
    Returns 1-18 for regular season, 0 for preseason, 19+ for playoffs.
    """
    now = datetime.now(timezone.utc)
    
    season_start = datetime(2025, 9, 4, tzinfo=timezone.utc)
    
    if now < season_start:
        return 0  # Preseason
    
    days_since_start = (now - season_start).days
    week = (days_since_start // 7) + 1
    
    return min(week, 18)  # Cap at 18 for regular season


def is_low_data_mode() -> bool:
    """
    Determine if the system should operate in low-data mode.
    Returns True for weeks 1-3 of the season.
    """
    current_week = get_current_nfl_week()
    return 1 <= current_week <= 3


def validate_lineup(lineup: Dict[str, Any]) -> bool:
    """
    Validate that a lineup meets DFS constraints.
    
    Args:
        lineup: Dictionary containing player selections and metadata
        
    Returns:
        bool: True if lineup is valid, False otherwise
    """
    try:
        total_salary = sum(player.get('salary', 0) for player in lineup.get('players', []))
        if total_salary > settings.salary_cap:
            logger.warning("Lineup exceeds salary cap", total_salary=total_salary)
            return False
        
        positions = [player.get('position') for player in lineup.get('players', [])]
        required_positions = {
            'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'DST': 1, 'FLEX': 1
        }
        
        position_counts = {}
        for pos in positions:
            if pos in ['RB', 'WR', 'TE'] and position_counts.get('FLEX', 0) == 0:
                if position_counts.get(pos, 0) < required_positions.get(pos, 0):
                    position_counts[pos] = position_counts.get(pos, 0) + 1
                else:
                    position_counts['FLEX'] = 1
            else:
                position_counts[pos] = position_counts.get(pos, 0) + 1
        
        for pos, required in required_positions.items():
            if position_counts.get(pos, 0) != required:
                logger.warning("Invalid position count", position=pos, 
                             required=required, actual=position_counts.get(pos, 0))
                return False
        
        return True
        
    except Exception as e:
        logger.error("Error validating lineup", error=str(e))
        return False


def calculate_leverage_score(player_ceiling: float, player_ownership: float) -> float:
    """
    Calculate the leverage score for a player.
    
    Args:
        player_ceiling: Player's ceiling projection
        player_ownership: Player's projected ownership percentage
        
    Returns:
        float: Leverage score (ceiling / ownership)
    """
    if player_ownership <= 0:
        return 0.0
    
    return player_ceiling / (player_ownership / 100.0)


def format_currency(amount: float) -> str:
    """Format amount as currency string"""
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage string"""
    return f"{value:.1f}%"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero"""
    if denominator == 0:
        return default
    return numerator / denominator


def exponential_decay_weight(weeks_ago: int, decay_factor: float = 0.9) -> float:
    """
    Calculate exponential decay weight for historical data.
    
    Args:
        weeks_ago: Number of weeks in the past
        decay_factor: Decay factor (0-1, closer to 1 means slower decay)
        
    Returns:
        float: Weight to apply to historical data
    """
    return decay_factor ** weeks_ago


class DataProcessor:
    """Utility class for common data processing operations"""
    
    @staticmethod
    def normalize_player_name(name: str) -> str:
        """Normalize player name for consistent matching"""
        return name.strip().title().replace(".", "").replace("'", "")
    
    @staticmethod
    def calculate_z_score(value: float, mean: float, std: float) -> float:
        """Calculate z-score for a value"""
        if std == 0:
            return 0.0
        return (value - mean) / std
    
    @staticmethod
    def winsorize(data: pd.Series, lower_percentile: float = 0.05, 
                  upper_percentile: float = 0.95) -> pd.Series:
        """Winsorize data to handle outliers"""
        lower_bound = data.quantile(lower_percentile)
        upper_bound = data.quantile(upper_percentile)
        return data.clip(lower=lower_bound, upper=upper_bound)

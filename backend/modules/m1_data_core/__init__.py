"""
Module 1: Data Core

This module handles all data ingestion, validation, and storage for the ATHENA system.
It aggregates data from multiple sources including player stats, Vegas odds, advanced metrics,
news sentiment, and DFS platform data.
"""

from .data_ingestion import DataIngestionEngine
from .data_validation import DataValidator
from .schedulers import DataScheduler

__all__ = ['DataIngestionEngine', 'DataValidator', 'DataScheduler']

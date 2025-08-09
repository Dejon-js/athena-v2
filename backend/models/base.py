from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, String
from datetime import datetime, timezone

Base = declarative_base()


class TimestampMixin:
    """Mixin to add timestamp fields to models"""
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class AuditMixin:
    """Mixin to add audit fields to models"""
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, default=1, nullable=False)

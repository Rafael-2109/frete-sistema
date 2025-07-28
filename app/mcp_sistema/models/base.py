"""
Base models and mixins for SQLAlchemy models
"""
from sqlalchemy import Column, Integer, DateTime, Boolean, String
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime
from typing import Any, Dict
import json


class TimestampMixin:
    """Mixin for adding timestamp fields to models"""
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True))
    
    def soft_delete(self):
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()


class AuditMixin(TimestampMixin):
    """Mixin for audit fields"""
    
    @declared_attr
    def created_by(cls):
        return Column(String(255))
    
    @declared_attr
    def updated_by(cls):
        return Column(String(255))


class BaseModel:
    """Base model with common functionality"""
    
    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name"""
        return cls.__name__.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif hasattr(value, '__dict__'):
                value = str(value)
            result[column.name] = value
        return result
    
    def to_json(self) -> str:
        """Convert model to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    def update_from_dict(self, data: Dict[str, Any]):
        """Update model from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self):
        """String representation"""
        attrs = []
        for column in self.__table__.columns:
            attrs.append(f"{column.name}={getattr(self, column.name)!r}")
        return f"{self.__class__.__name__}({', '.join(attrs[:3])}...)"


class IdMixin:
    """Mixin for adding ID field"""
    
    id = Column(Integer, primary_key=True, autoincrement=True)


# Combined base class for most models
class BaseEntityModel(BaseModel, IdMixin, TimestampMixin):
    """Base class for entity models with ID and timestamps"""
    pass


class BaseAuditModel(BaseModel, IdMixin, AuditMixin):
    """Base class for models with full audit trail"""
    pass


class BaseSoftDeleteModel(BaseModel, IdMixin, TimestampMixin, SoftDeleteMixin):
    """Base class for models with soft delete capability"""
    pass
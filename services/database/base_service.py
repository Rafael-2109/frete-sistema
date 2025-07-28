"""
Base Service Class for Database Operations

Provides common functionality for all database services including:
- Connection pooling management
- Query optimization utilities
- Error handling
- Performance monitoring
"""

from typing import Any, Dict, List, Optional, TypeVar, Generic
from sqlalchemy.orm import Session, Query
from sqlalchemy.sql import text
from sqlalchemy import and_, or_, func
from datetime import datetime
import logging
from contextlib import contextmanager

from app import db

logger = logging.getLogger(__name__)

T = TypeVar('T')

class BaseService(Generic[T]):
    """Base service class with common database operations"""
    
    def __init__(self, model_class: type[T]):
        self.model_class = model_class
        self.session = db.session
        self._query_count = 0
        self._query_time = 0
        
    @contextmanager
    def transaction(self):
        """Context manager for database transactions with automatic rollback"""
        try:
            yield self.session
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Transaction failed: {str(e)}")
            raise
            
    def get_by_id(self, id: int) -> Optional[T]:
        """Get record by ID with optimized query"""
        try:
            return self.session.get(self.model_class, id)
        except Exception as e:
            logger.error(f"Error fetching {self.model_class.__name__} by id {id}: {str(e)}")
            return None
            
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Get all records with pagination support"""
        query = self.session.query(self.model_class)
        
        if limit:
            query = query.limit(limit)
        
        if offset:
            query = query.offset(offset)
            
        return query.all()
        
    def count(self, **filters) -> int:
        """Count records with optional filters"""
        query = self.session.query(func.count(self.model_class.id))
        
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
                
        return query.scalar() or 0
        
    def create(self, **kwargs) -> T:
        """Create new record"""
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            self.session.commit()
            return instance
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating {self.model_class.__name__}: {str(e)}")
            raise
            
    def update(self, id: int, **kwargs) -> Optional[T]:
        """Update existing record"""
        try:
            instance = self.get_by_id(id)
            if not instance:
                return None
                
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
                    
            self.session.commit()
            return instance
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating {self.model_class.__name__} {id}: {str(e)}")
            raise
            
    def delete(self, id: int) -> bool:
        """Delete record by ID"""
        try:
            instance = self.get_by_id(id)
            if not instance:
                return False
                
            self.session.delete(instance)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting {self.model_class.__name__} {id}: {str(e)}")
            return False
            
    def bulk_create(self, records: List[Dict[str, Any]]) -> List[T]:
        """Bulk create records for better performance"""
        try:
            instances = [self.model_class(**record) for record in records]
            self.session.bulk_save_objects(instances, return_defaults=True)
            self.session.commit()
            return instances
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error bulk creating {self.model_class.__name__}: {str(e)}")
            raise
            
    def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Execute raw SQL query with parameters"""
        try:
            result = self.session.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error executing raw query: {str(e)}")
            raise
            
    def build_query(self) -> Query:
        """Build base query for the model"""
        return self.session.query(self.model_class)
        
    def apply_filters(self, query: Query, filters: Dict[str, Any]) -> Query:
        """Apply filters to query dynamically"""
        for key, value in filters.items():
            if not hasattr(self.model_class, key):
                continue
                
            column = getattr(self.model_class, key)
            
            if value is None:
                query = query.filter(column.is_(None))
            elif isinstance(value, list):
                query = query.filter(column.in_(value))
            elif isinstance(value, dict):
                # Support for complex filters like {'gte': 100, 'lte': 200}
                if 'gte' in value:
                    query = query.filter(column >= value['gte'])
                if 'gt' in value:
                    query = query.filter(column > value['gt'])
                if 'lte' in value:
                    query = query.filter(column <= value['lte'])
                if 'lt' in value:
                    query = query.filter(column < value['lt'])
                if 'like' in value:
                    query = query.filter(column.like(f"%{value['like']}%"))
                if 'ilike' in value:
                    query = query.filter(column.ilike(f"%{value['ilike']}%"))
            else:
                query = query.filter(column == value)
                
        return query
        
    def apply_sorting(self, query: Query, sort_by: str, order: str = 'asc') -> Query:
        """Apply sorting to query"""
        if hasattr(self.model_class, sort_by):
            column = getattr(self.model_class, sort_by)
            if order.lower() == 'desc':
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        return query
        
    def paginate(self, query: Query, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Paginate query results"""
        total = query.count()
        items = query.limit(per_page).offset((page - 1) * per_page).all()
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page * per_page < total
        }
        
    def get_or_create(self, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> tuple[T, bool]:
        """Get existing record or create new one"""
        instance = self.session.query(self.model_class).filter_by(**kwargs).first()
        
        if instance:
            return instance, False
            
        params = kwargs.copy()
        if defaults:
            params.update(defaults)
            
        instance = self.create(**params)
        return instance, True
        
    def update_or_create(self, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> tuple[T, bool]:
        """Update existing record or create new one"""
        instance = self.session.query(self.model_class).filter_by(**kwargs).first()
        
        if instance:
            # Update existing
            for key, value in (defaults or {}).items():
                setattr(instance, key, value)
            self.session.commit()
            return instance, False
        else:
            # Create new
            params = kwargs.copy()
            if defaults:
                params.update(defaults)
            instance = self.create(**params)
            return instance, True
            
    def exists(self, **kwargs) -> bool:
        """Check if record exists"""
        return self.session.query(
            self.session.query(self.model_class).filter_by(**kwargs).exists()
        ).scalar()
        
    def refresh(self, instance: T) -> T:
        """Refresh instance from database"""
        self.session.refresh(instance)
        return instance
        
    def log_performance(self, operation: str, duration: float, record_count: int = 0):
        """Log performance metrics"""
        logger.info(f"Performance: {operation} - Duration: {duration:.3f}s - Records: {record_count}")
        
    @property
    def query_stats(self) -> Dict[str, Any]:
        """Get query statistics"""
        return {
            'query_count': self._query_count,
            'total_time': self._query_time,
            'avg_time': self._query_time / self._query_count if self._query_count > 0 else 0
        }
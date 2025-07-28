"""
Database service for MCP operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import uuid
import logging

from ..models import (
    MCPSessionDB,
    MCPRequestDB,
    MCPResponseDB,
    MCPToolExecution,
    MCPCache,
    RequestMethod,
    ResponseStatus,
    get_db_context
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations"""
    
    @staticmethod
    def create_session(
        client_id: str,
        client_name: Optional[str] = None,
        client_version: Optional[str] = None,
        protocol_version: Optional[str] = None,
        transport: str = "stdio",
        capabilities: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new MCP session"""
        session_id = str(uuid.uuid4())
        
        with get_db_context() as db:
            session = MCPSessionDB(
                session_id=session_id,
                client_id=client_id,
                client_name=client_name,
                client_version=client_version,
                protocol_version=protocol_version,
                transport=transport,
                capabilities=capabilities or {},
                metadata=metadata or {},
                status="active"
            )
            db.add(session)
            db.commit()
            
        logger.info(f"Created session {session_id} for client {client_id}")
        return session_id
    
    @staticmethod
    def get_session(session_id: str) -> Optional[MCPSessionDB]:
        """Get session by ID"""
        with get_db_context() as db:
            return db.query(MCPSessionDB).filter(
                MCPSessionDB.session_id == session_id
            ).first()
    
    @staticmethod
    def update_session_activity(session_id: str):
        """Update session last activity"""
        with get_db_context() as db:
            session = db.query(MCPSessionDB).filter(
                MCPSessionDB.session_id == session_id
            ).first()
            if session:
                session.update_activity()
                db.commit()
    
    @staticmethod
    def close_session(session_id: str):
        """Close a session"""
        with get_db_context() as db:
            session = db.query(MCPSessionDB).filter(
                MCPSessionDB.session_id == session_id
            ).first()
            if session:
                session.close()
                db.commit()
                logger.info(f"Closed session {session_id}")
    
    @staticmethod
    def log_request(
        session_id: str,
        method: RequestMethod,
        endpoint: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Log an MCP request"""
        request_id = str(uuid.uuid4())
        
        with get_db_context() as db:
            request = MCPRequestDB(
                request_id=request_id,
                session_id=session_id,
                method=method,
                endpoint=endpoint,
                params=params,
                headers=headers,
                body=body,
                body_size=len(str(body)) if body else 0,
                client_ip=client_ip,
                user_agent=user_agent
            )
            db.add(request)
            
            # Update session request count
            session = db.query(MCPSessionDB).filter(
                MCPSessionDB.session_id == session_id
            ).first()
            if session:
                session.increment_request_count()
            
            db.commit()
        
        return request_id
    
    @staticmethod
    def log_response(
        request_id: str,
        session_id: str,
        status: ResponseStatus,
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        processing_time: Optional[float] = None,
        tokens_used: Optional[int] = None
    ) -> str:
        """Log an MCP response"""
        response_id = str(uuid.uuid4())
        
        with get_db_context() as db:
            response = MCPResponseDB(
                response_id=response_id,
                request_id=request_id,
                session_id=session_id,
                status=status,
                status_code=status_code,
                headers=headers,
                body=body,
                body_size=len(str(body)) if body else 0,
                error_type=error_type,
                error_message=error_message,
                error_details=error_details,
                processing_time=processing_time,
                tokens_used=tokens_used
            )
            db.add(response)
            
            # Update session metrics
            session = db.query(MCPSessionDB).filter(
                MCPSessionDB.session_id == session_id
            ).first()
            if session:
                if processing_time:
                    session.update_response_time(processing_time)
                if tokens_used:
                    session.add_tokens(tokens_used)
                if status == ResponseStatus.ERROR:
                    session.record_error(error_message or "Unknown error")
            
            db.commit()
        
        return response_id
    
    @staticmethod
    def log_tool_execution(
        request_id: str,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_version: Optional[str] = None,
        tool_category: Optional[str] = None
    ) -> str:
        """Start logging a tool execution"""
        execution_id = str(uuid.uuid4())
        
        with get_db_context() as db:
            execution = MCPToolExecution(
                execution_id=execution_id,
                request_id=request_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_version=tool_version,
                tool_category=tool_category,
                arguments=arguments,
                status="running"
            )
            db.add(execution)
            
            # Update session tool count
            session = db.query(MCPSessionDB).filter(
                MCPSessionDB.session_id == session_id
            ).first()
            if session:
                session.increment_tool_count()
            
            db.commit()
        
        return execution_id
    
    @staticmethod
    def complete_tool_execution(
        execution_id: str,
        status: str = "success",
        result: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        error_stack: Optional[str] = None,
        memory_used: Optional[int] = None,
        cpu_time: Optional[float] = None
    ):
        """Complete a tool execution"""
        with get_db_context() as db:
            execution = db.query(MCPToolExecution).filter(
                MCPToolExecution.execution_id == execution_id
            ).first()
            
            if execution:
                if status == "success":
                    execution.mark_completed(status, result)
                else:
                    execution.mark_failed(error_type, error_message, error_stack)
                
                if memory_used:
                    execution.memory_used = memory_used
                if cpu_time:
                    execution.cpu_time = cpu_time
                
                db.commit()
    
    @staticmethod
    def get_cache(cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached data"""
        with get_db_context() as db:
            cache_entry = db.query(MCPCache).filter(
                MCPCache.cache_key == cache_key
            ).first()
            
            if cache_entry and not cache_entry.is_expired():
                cache_entry.increment_hits()
                db.commit()
                return cache_entry.data
            
            return None
    
    @staticmethod
    def set_cache(
        cache_key: str,
        data: Dict[str, Any],
        cache_type: str = "general",
        expires_in_seconds: Optional[int] = 3600,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Set cache data"""
        expires_at = None
        if expires_in_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        
        with get_db_context() as db:
            # Check if entry exists
            cache_entry = db.query(MCPCache).filter(
                MCPCache.cache_key == cache_key
            ).first()
            
            if cache_entry:
                # Update existing entry
                cache_entry.data = data
                cache_entry.data_size = len(str(data))
                cache_entry.expires_at = expires_at
                cache_entry.updated_at = datetime.utcnow()
            else:
                # Create new entry
                cache_entry = MCPCache(
                    cache_key=cache_key,
                    cache_type=cache_type,
                    data=data,
                    data_size=len(str(data)),
                    expires_at=expires_at,
                    source_type=source_type,
                    source_id=source_id,
                    tags=tags
                )
                db.add(cache_entry)
            
            db.commit()
    
    @staticmethod
    def cleanup_expired_cache():
        """Remove expired cache entries"""
        with get_db_context() as db:
            deleted = db.query(MCPCache).filter(
                and_(
                    MCPCache.expires_at.isnot(None),
                    MCPCache.expires_at < datetime.utcnow()
                )
            ).delete()
            db.commit()
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired cache entries")
    
    @staticmethod
    def get_active_sessions() -> List[MCPSessionDB]:
        """Get all active sessions"""
        with get_db_context() as db:
            return db.query(MCPSessionDB).filter(
                MCPSessionDB.status == "active"
            ).order_by(desc(MCPSessionDB.last_activity)).all()
    
    @staticmethod
    def get_session_summary(session_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive session summary"""
        with get_db_context() as db:
            session = db.query(MCPSessionDB).filter(
                MCPSessionDB.session_id == session_id
            ).first()
            
            if session:
                return session.get_summary()
            
            return None
    
    @staticmethod
    def cleanup_old_sessions(days: int = 7):
        """Clean up old inactive sessions"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with get_db_context() as db:
            deleted = db.query(MCPSessionDB).filter(
                and_(
                    MCPSessionDB.status.in_(["closed", "error"]),
                    MCPSessionDB.last_activity < cutoff_date
                )
            ).delete()
            db.commit()
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old sessions")
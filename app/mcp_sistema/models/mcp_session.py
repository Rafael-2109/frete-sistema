"""
MCP Session tracking models
"""
from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON, Text, Float, Index
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any

from .database import Base
from .base import BaseEntityModel


class MCPSession(Base, BaseEntityModel):
    """Track active MCP sessions"""
    
    __tablename__ = "mcp_sessions"
    
    # Session identification
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    client_id = Column(String(255), nullable=False, index=True)
    client_name = Column(String(255))
    client_version = Column(String(50))
    
    # Session state
    status = Column(String(50), default="active", nullable=False)  # active, paused, closed, error
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    
    # Connection details
    protocol_version = Column(String(20))
    transport = Column(String(50))  # stdio, websocket, http
    capabilities = Column(JSON)  # Client capabilities
    
    # Session metadata
    metadata = Column(JSON)  # Additional session data
    tags = Column(JSON)  # Session tags for filtering
    
    # Resource usage
    request_count = Column(Integer, default=0)
    tool_execution_count = Column(Integer, default=0)
    resource_access_count = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    
    # Performance metrics
    avg_response_time = Column(Float)  # milliseconds
    max_response_time = Column(Float)
    min_response_time = Column(Float)
    
    # Error tracking
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    last_error_at = Column(DateTime(timezone=True))
    
    # Indexes
    __table_args__ = (
        Index('idx_session_client', 'client_id', 'started_at'),
        Index('idx_session_status', 'status', 'last_activity'),
        Index('idx_session_activity', 'last_activity'),
    )
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def increment_request_count(self):
        """Increment request counter"""
        self.request_count += 1
        self.update_activity()
    
    def increment_tool_count(self):
        """Increment tool execution counter"""
        self.tool_execution_count += 1
        self.update_activity()
    
    def increment_resource_count(self):
        """Increment resource access counter"""
        self.resource_access_count += 1
        self.update_activity()
    
    def add_tokens(self, count: int):
        """Add to total tokens used"""
        self.total_tokens_used += count
    
    def record_error(self, error: str):
        """Record error in session"""
        self.error_count += 1
        self.last_error = error
        self.last_error_at = datetime.utcnow()
        self.update_activity()
    
    def update_response_time(self, response_time: float):
        """Update response time metrics"""
        if self.avg_response_time is None:
            self.avg_response_time = response_time
            self.max_response_time = response_time
            self.min_response_time = response_time
        else:
            # Calculate new average
            total_requests = self.request_count or 1
            self.avg_response_time = (
                (self.avg_response_time * (total_requests - 1) + response_time) / total_requests
            )
            # Update min/max
            if response_time > (self.max_response_time or 0):
                self.max_response_time = response_time
            if response_time < (self.min_response_time or float('inf')):
                self.min_response_time = response_time
    
    def close(self):
        """Close the session"""
        self.status = "closed"
        self.ended_at = datetime.utcnow()
    
    def pause(self):
        """Pause the session"""
        self.status = "paused"
        self.update_activity()
    
    def resume(self):
        """Resume the session"""
        self.status = "active"
        self.update_activity()
    
    def is_active(self) -> bool:
        """Check if session is active"""
        return self.status == "active"
    
    def get_duration(self) -> Optional[float]:
        """Get session duration in seconds"""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return (datetime.utcnow() - self.started_at).total_seconds()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "status": self.status,
            "duration": self.get_duration(),
            "request_count": self.request_count,
            "tool_execution_count": self.tool_execution_count,
            "resource_access_count": self.resource_access_count,
            "total_tokens_used": self.total_tokens_used,
            "avg_response_time": self.avg_response_time,
            "error_count": self.error_count
        }
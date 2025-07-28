"""
MCP Logging models for requests, responses, and tool executions
"""
from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON, Text, Float, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from typing import Optional, Dict, Any

from .database import Base
from .base import BaseEntityModel, TimestampMixin


class RequestMethod(enum.Enum):
    """MCP request methods"""
    INITIALIZE = "initialize"
    LIST_RESOURCES = "list_resources"
    READ_RESOURCE = "read_resource"
    LIST_TOOLS = "list_tools"
    CALL_TOOL = "call_tool"
    PING = "ping"
    CUSTOM = "custom"


class ResponseStatus(enum.Enum):
    """Response status types"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


class MCPRequest(Base, BaseEntityModel):
    """Log all MCP requests"""
    
    __tablename__ = "mcp_requests"
    
    # Request identification
    request_id = Column(String(255), unique=True, nullable=False, index=True)
    session_id = Column(String(255), ForeignKey('mcp_sessions.session_id'), nullable=False, index=True)
    
    # Request details
    method = Column(Enum(RequestMethod), nullable=False, index=True)
    endpoint = Column(String(255))
    params = Column(JSON)
    headers = Column(JSON)
    
    # Request body
    body = Column(JSON)
    body_size = Column(Integer)  # bytes
    
    # Client info
    client_ip = Column(String(45))  # IPv4/IPv6
    user_agent = Column(String(500))
    
    # Timing
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_request_session', 'session_id', 'received_at'),
        Index('idx_request_method', 'method', 'received_at'),
    )
    
    # Relationships
    session = relationship("MCPSession", backref="requests")
    response = relationship("MCPResponse", uselist=False, back_populates="request")
    tool_execution = relationship("MCPToolExecution", uselist=False, back_populates="request")
    
    def get_elapsed_time(self) -> Optional[float]:
        """Get elapsed time to response in milliseconds"""
        if hasattr(self, 'response') and self.response:
            return (self.response.sent_at - self.received_at).total_seconds() * 1000
        return None


class MCPResponse(Base, BaseEntityModel):
    """Log all MCP responses"""
    
    __tablename__ = "mcp_responses"
    
    # Response identification
    response_id = Column(String(255), unique=True, nullable=False, index=True)
    request_id = Column(String(255), ForeignKey('mcp_requests.request_id'), unique=True, nullable=False)
    session_id = Column(String(255), ForeignKey('mcp_sessions.session_id'), nullable=False, index=True)
    
    # Response details
    status = Column(Enum(ResponseStatus), nullable=False, index=True)
    status_code = Column(Integer)
    headers = Column(JSON)
    
    # Response body
    body = Column(JSON)
    body_size = Column(Integer)  # bytes
    
    # Error details (if applicable)
    error_type = Column(String(100))
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Performance
    processing_time = Column(Float)  # milliseconds
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Token usage (if applicable)
    tokens_used = Column(Integer)
    
    # Indexes
    __table_args__ = (
        Index('idx_response_session', 'session_id', 'sent_at'),
        Index('idx_response_status', 'status', 'sent_at'),
    )
    
    # Relationships
    request = relationship("MCPRequest", back_populates="response")
    session = relationship("MCPSession", backref="responses")


class MCPToolExecution(Base, BaseEntityModel):
    """Track tool executions"""
    
    __tablename__ = "mcp_tool_executions"
    
    # Execution identification
    execution_id = Column(String(255), unique=True, nullable=False, index=True)
    request_id = Column(String(255), ForeignKey('mcp_requests.request_id'), unique=True, nullable=False)
    session_id = Column(String(255), ForeignKey('mcp_sessions.session_id'), nullable=False, index=True)
    
    # Tool details
    tool_name = Column(String(255), nullable=False, index=True)
    tool_version = Column(String(50))
    tool_category = Column(String(100))
    
    # Execution details
    arguments = Column(JSON)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    
    # Results
    status = Column(String(50), nullable=False)  # pending, running, success, failed, timeout
    result = Column(JSON)
    result_size = Column(Integer)  # bytes
    
    # Performance
    execution_time = Column(Float)  # milliseconds
    memory_used = Column(Integer)  # bytes
    cpu_time = Column(Float)  # milliseconds
    
    # Error tracking
    error_type = Column(String(100))
    error_message = Column(Text)
    error_stack = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Indexes
    __table_args__ = (
        Index('idx_tool_exec_session', 'session_id', 'started_at'),
        Index('idx_tool_exec_name', 'tool_name', 'started_at'),
        Index('idx_tool_exec_status', 'status', 'started_at'),
    )
    
    # Relationships
    request = relationship("MCPRequest", back_populates="tool_execution")
    session = relationship("MCPSession", backref="tool_executions")
    
    def calculate_execution_time(self):
        """Calculate and set execution time"""
        if self.completed_at and self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds() * 1000
    
    def mark_completed(self, status: str = "success", result: Optional[Dict[str, Any]] = None):
        """Mark execution as completed"""
        self.completed_at = datetime.utcnow()
        self.status = status
        if result:
            self.result = result
            self.result_size = len(str(result))
        self.calculate_execution_time()
    
    def mark_failed(self, error_type: str, error_message: str, error_stack: Optional[str] = None):
        """Mark execution as failed"""
        self.completed_at = datetime.utcnow()
        self.status = "failed"
        self.error_type = error_type
        self.error_message = error_message
        self.error_stack = error_stack
        self.calculate_execution_time()


class MCPCache(Base, TimestampMixin):
    """Cache frequently used data"""
    
    __tablename__ = "mcp_cache"
    
    # Cache identification
    cache_key = Column(String(500), primary_key=True)
    cache_type = Column(String(100), nullable=False, index=True)  # tool_result, resource, response
    
    # Cache data
    data = Column(JSON, nullable=False)
    data_size = Column(Integer)  # bytes
    
    # Cache metadata
    expires_at = Column(DateTime(timezone=True), index=True)
    hit_count = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True))
    
    # Source tracking
    source_type = Column(String(100))  # tool, resource, computation
    source_id = Column(String(255))
    
    # Tags for categorization
    tags = Column(JSON)
    
    # Indexes
    __table_args__ = (
        Index('idx_cache_type_expires', 'cache_type', 'expires_at'),
        Index('idx_cache_accessed', 'last_accessed'),
    )
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def increment_hits(self):
        """Increment hit counter and update access time"""
        self.hit_count += 1
        self.last_accessed = datetime.utcnow()
    
    def get_age(self) -> float:
        """Get cache age in seconds"""
        return (datetime.utcnow() - self.created_at).total_seconds()
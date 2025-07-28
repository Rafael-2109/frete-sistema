"""
MCP-specific models
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum


class TransportType(str, Enum):
    """MCP transport types"""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    name: str
    type: str
    description: Optional[str] = None
    required: bool = False
    default: Any = None


class Tool(BaseModel):
    """MCP Tool definition"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: List[ToolParameter] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "calculate_freight",
                "description": "Calculate freight cost",
                "parameters": [
                    {
                        "name": "weight",
                        "type": "number",
                        "description": "Weight in kg",
                        "required": True
                    }
                ]
            }
        }


class Resource(BaseModel):
    """MCP Resource definition"""
    uri: str = Field(..., description="Resource URI")
    name: str = Field(..., description="Resource name")
    description: Optional[str] = Field(None, description="Resource description")
    mime_type: str = Field(default="application/json")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "uri": "freight://orders/12345",
                "name": "Order 12345",
                "description": "Freight order details",
                "mime_type": "application/json"
            }
        }


class MCPRequest(BaseModel):
    """MCP request model"""
    id: Union[str, int] = Field(..., description="Request ID")
    method: str = Field(..., description="Request method")
    params: Optional[Dict[str, Any]] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "req-123",
                "method": "tools/execute",
                "params": {
                    "tool": "calculate_freight",
                    "arguments": {"weight": 100}
                }
            }
        }


class MCPResponse(BaseModel):
    """MCP response model"""
    id: Union[str, int] = Field(..., description="Response ID")
    result: Optional[Any] = Field(default=None)
    error: Optional[Dict[str, Any]] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "req-123",
                "result": {
                    "cost": 150.00,
                    "currency": "BRL"
                }
            }
        }


class MCPServerInfo(BaseModel):
    """MCP server information"""
    name: str
    version: str
    description: Optional[str] = None
    transport: TransportType
    features: Dict[str, bool]
    capabilities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPSession(BaseModel):
    """MCP session information"""
    id: str
    server_info: MCPServerInfo
    client_info: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolExecution(BaseModel):
    """Tool execution record"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
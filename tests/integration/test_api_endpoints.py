"""
Integration tests for all MCP API endpoints
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# Import test utilities
from ..conftest import *


class TestMCPAPIEndpoints:
    """Test suite for MCP API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_list_tools_endpoint(self, client, mock_mcp_service):
        """Test listing available MCP tools"""
        # Mock the MCP service response
        mock_tools = [
            {
                "name": "calculate_freight",
                "description": "Calculate freight costs",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "track_delivery",
                "description": "Track delivery status",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
        mock_mcp_service.list_tools.return_value = mock_tools
        
        # Make request
        response = await client.get("/api/mcp/tools")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "calculate_freight"
        assert data[1]["name"] == "track_delivery"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_execute_tool_endpoint(self, client, mock_mcp_service):
        """Test executing a specific MCP tool"""
        # Mock the MCP service response
        mock_result = {
            "cost": 250.00,
            "estimatedDays": 2,
            "service": "express"
        }
        mock_mcp_service.execute_tool.return_value = mock_result
        
        # Request data
        tool_args = {
            "origin": "São Paulo",
            "destination": "Rio de Janeiro",
            "weight": 1000
        }
        
        # Make request
        response = await client.post(
            "/api/mcp/tools/calculate_freight/execute",
            json=tool_args
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["cost"] == 250.00
        assert data["result"]["estimatedDays"] == 2
        
        # Verify service was called correctly
        mock_mcp_service.execute_tool.assert_called_once_with(
            "calculate_freight",
            tool_args
        )
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_execute_tool_error_handling(self, client, mock_mcp_service):
        """Test error handling in tool execution"""
        # Mock service to raise exception
        mock_mcp_service.execute_tool.side_effect = Exception("Tool execution failed")
        
        # Make request
        response = await client.post(
            "/api/mcp/tools/invalid_tool/execute",
            json={"test": "data"}
        )
        
        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Tool execution failed" in data["detail"]
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_list_resources_endpoint(self, client, mock_mcp_service):
        """Test listing available MCP resources"""
        # Mock the MCP service response
        mock_resources = [
            {
                "name": "freight_database",
                "uri": "resource://freight/db",
                "description": "Freight calculation database"
            },
            {
                "name": "delivery_tracking",
                "uri": "resource://tracking/api",
                "description": "Delivery tracking API"
            }
        ]
        mock_mcp_service.list_resources.return_value = mock_resources
        
        # Make request
        response = await client.get("/api/mcp/resources")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "freight_database"
        assert data[1]["name"] == "delivery_tracking"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_read_resource_endpoint(self, client, mock_mcp_service):
        """Test reading a specific MCP resource"""
        # Mock the MCP service response
        mock_content = {
            "data": "Resource content",
            "metadata": {"version": "1.0", "lastUpdated": "2024-01-01"}
        }
        mock_mcp_service.read_resource.return_value = mock_content
        
        # Make request
        response = await client.get("/api/mcp/resources/freight_database/read")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["content"]["data"] == "Resource content"
        assert data["content"]["metadata"]["version"] == "1.0"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_natural_language_query(self, client, mock_mcp_service):
        """Test natural language query processing"""
        # Mock the MCP service response
        mock_response = {
            "intent": "calculate_freight",
            "parameters": {
                "origin": "São Paulo",
                "destination": "Rio de Janeiro",
                "weight": 1000
            },
            "result": {
                "cost": 250.00,
                "estimatedDays": 2
            }
        }
        mock_mcp_service.process_natural_language.return_value = mock_response
        
        # Request data
        query_data = {
            "query": "Quanto custa enviar 1000kg de São Paulo para Rio de Janeiro?",
            "context": {"user_id": "test-user-123"}
        }
        
        # Make request
        response = await client.post("/api/mcp/query", json=query_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["intent"] == "calculate_freight"
        assert data["result"]["result"]["cost"] == 250.00
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_batch_tool_execution(self, client, mock_mcp_service):
        """Test batch execution of multiple tools"""
        # Mock the MCP service responses
        mock_results = [
            {"toolName": "calculate_freight", "result": {"cost": 250.00}},
            {"toolName": "track_delivery", "result": {"status": "in_transit"}}
        ]
        mock_mcp_service.execute_batch.return_value = mock_results
        
        # Request data
        batch_data = {
            "tools": [
                {
                    "name": "calculate_freight",
                    "arguments": {"origin": "SP", "destination": "RJ", "weight": 1000}
                },
                {
                    "name": "track_delivery",
                    "arguments": {"trackingId": "BR123456789"}
                }
            ]
        }
        
        # Make request
        response = await client.post("/api/mcp/tools/batch", json=batch_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 2
        assert data["results"][0]["toolName"] == "calculate_freight"
        assert data["results"][1]["toolName"] == "track_delivery"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_prompts_endpoint(self, client, mock_mcp_service):
        """Test listing available prompts"""
        # Mock the MCP service response
        mock_prompts = [
            {
                "name": "freight_assistant",
                "description": "Freight calculation assistant prompt",
                "arguments": ["origin", "destination", "weight"]
            }
        ]
        mock_mcp_service.list_prompts.return_value = mock_prompts
        
        # Make request
        response = await client.get("/api/mcp/prompts")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "freight_assistant"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_execute_prompt_endpoint(self, client, mock_mcp_service):
        """Test executing a specific prompt"""
        # Mock the MCP service response
        mock_result = {
            "response": "The freight cost from São Paulo to Rio de Janeiro is R$ 250.00",
            "metadata": {"model": "gpt-4", "tokens": 50}
        }
        mock_mcp_service.execute_prompt.return_value = mock_result
        
        # Request data
        prompt_args = {
            "origin": "São Paulo",
            "destination": "Rio de Janeiro",
            "weight": 1000
        }
        
        # Make request
        response = await client.post(
            "/api/mcp/prompts/freight_assistant/execute",
            json=prompt_args
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "freight cost" in data["result"]["response"]
        assert data["result"]["metadata"]["model"] == "gpt-4"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    async def test_authenticated_endpoints(self, client, mock_mcp_service, auth_headers):
        """Test endpoints requiring authentication"""
        # Test without auth
        response = await client.get("/api/mcp/protected/tools")
        assert response.status_code == 401
        
        # Test with auth
        response = await client.get(
            "/api/mcp/protected/tools",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_rate_limiting(self, client, mock_mcp_service):
        """Test rate limiting on API endpoints"""
        # Make multiple requests quickly
        responses = []
        for i in range(15):  # Assuming limit is 10 per minute
            response = await client.get("/api/mcp/tools")
            responses.append(response)
        
        # Check that some requests were rate limited
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes  # Too Many Requests
        
        # Check rate limit headers
        limited_response = next(r for r in responses if r.status_code == 429)
        assert "X-RateLimit-Limit" in limited_response.headers
        assert "X-RateLimit-Remaining" in limited_response.headers
        assert "X-RateLimit-Reset" in limited_response.headers
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_cors_headers(self, client):
        """Test CORS headers on API responses"""
        response = await client.options("/api/mcp/tools")
        
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_error_response_format(self, client, mock_mcp_service):
        """Test consistent error response format"""
        # Mock service to raise different types of errors
        test_cases = [
            (ValueError("Invalid input"), 400),
            (PermissionError("Access denied"), 403),
            (FileNotFoundError("Resource not found"), 404),
            (Exception("Internal error"), 500)
        ]
        
        for error, expected_status in test_cases:
            mock_mcp_service.execute_tool.side_effect = error
            
            response = await client.post(
                "/api/mcp/tools/test_tool/execute",
                json={"test": "data"}
            )
            
            assert response.status_code == expected_status
            data = response.json()
            assert "error" in data or "detail" in data
            assert "timestamp" in data
            assert "path" in data
            assert "method" in data


class TestMCPWebSocketEndpoints:
    """Test suite for MCP WebSocket endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_websocket_connection(self, websocket_client):
        """Test WebSocket connection establishment"""
        async with websocket_client("/api/mcp/ws") as websocket:
            # Send initial message
            await websocket.send_json({
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Receive response
            response = await websocket.receive_json()
            assert response["type"] == "pong"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_websocket_tool_execution(self, websocket_client, mock_mcp_service):
        """Test tool execution via WebSocket"""
        mock_mcp_service.execute_tool.return_value = {"result": "success"}
        
        async with websocket_client("/api/mcp/ws") as websocket:
            # Send tool execution request
            await websocket.send_json({
                "type": "execute_tool",
                "tool": "calculate_freight",
                "arguments": {"origin": "SP", "destination": "RJ"}
            })
            
            # Receive response
            response = await websocket.receive_json()
            assert response["type"] == "tool_result"
            assert response["result"]["result"] == "success"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_websocket_streaming_response(self, websocket_client, mock_mcp_service):
        """Test streaming responses via WebSocket"""
        async def mock_stream():
            for i in range(5):
                yield {"chunk": i, "data": f"Chunk {i}"}
                await asyncio.sleep(0.1)
        
        mock_mcp_service.execute_streaming.return_value = mock_stream()
        
        async with websocket_client("/api/mcp/ws") as websocket:
            # Send streaming request
            await websocket.send_json({
                "type": "stream_tool",
                "tool": "generate_report",
                "arguments": {"format": "detailed"}
            })
            
            # Receive streaming chunks
            chunks = []
            for i in range(5):
                response = await websocket.receive_json()
                assert response["type"] == "stream_chunk"
                chunks.append(response["data"])
            
            # Receive completion
            response = await websocket.receive_json()
            assert response["type"] == "stream_complete"
            assert len(chunks) == 5
"""
Integration tests for Portfolio MCP integration endpoints
"""
import pytest
import json
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# Import test utilities
from ..conftest import *


class TestPortfolioMCPIntegration:
    """Test suite for Portfolio MCP integration endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_portfolio_health_endpoint(self, flask_client, mock_portfolio_bridge):
        """Test portfolio MCP health check endpoint"""
        # Mock the bridge response
        mock_portfolio_bridge.get_status.return_value = {
            "status": "healthy",
            "components": {
                "mcp_service": "active",
                "portfolio_service": "active",
                "cache": "connected"
            }
        }
        
        # Make request
        response = flask_client.get("/api/portfolio/mcp/health")
        
        # Assertions
        assert response.status_code == 200
        data = response.json
        assert data["status"] == "healthy"
        assert data["components"]["mcp_service"] == "active"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    def test_portfolio_natural_language_query(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test natural language query for portfolio data"""
        # Mock the bridge response
        mock_portfolio_bridge.process_natural_language_query.return_value = {
            "interpretation": {
                "intent": "list_pending_orders",
                "filters": {"status": "pendente", "days": 7}
            },
            "results": [
                {
                    "id": 1,
                    "customer": "Cliente A",
                    "status": "pendente",
                    "value": 5000.00,
                    "created_at": "2024-01-15"
                }
            ],
            "summary": "Encontrei 1 pedido pendente nos últimos 7 dias"
        }
        
        # Request data
        query_data = {
            "query": "Quais pedidos estão pendentes há mais de 7 dias?",
            "context": {
                "user_id": "test-user",
                "workspace_id": "test-workspace"
            }
        }
        
        # Make request
        response = flask_client.post(
            "/api/portfolio/mcp/query",
            json=query_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["interpretation"]["intent"] == "list_pending_orders"
        assert len(data["results"]) == 1
        assert "summary" in data
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    def test_portfolio_analytics_endpoint(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test portfolio analytics with MCP enhancement"""
        # Mock the bridge response
        mock_analytics = {
            "metrics": {
                "total_orders": 150,
                "pending_orders": 25,
                "completed_orders": 120,
                "cancelled_orders": 5,
                "total_value": 450000.00,
                "average_order_value": 3000.00
            },
            "trends": {
                "order_growth": 15.5,
                "value_growth": 22.3,
                "completion_rate": 80.0
            },
            "predictions": {
                "next_month_orders": 165,
                "next_month_value": 495000.00,
                "confidence": 0.85
            },
            "insights": [
                {
                    "type": "opportunity",
                    "title": "Aumento de demanda detectado",
                    "description": "Crescimento de 15% nos pedidos indica oportunidade de expansão",
                    "priority": "high"
                }
            ]
        }
        mock_portfolio_bridge.get_analytics.return_value = mock_analytics
        
        # Request parameters
        params = {
            "period": "monthly",
            "include_predictions": True,
            "include_insights": True
        }
        
        # Make request
        response = flask_client.get(
            "/api/portfolio/mcp/analytics",
            query_string=params,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json
        assert "metrics" in data
        assert data["metrics"]["total_orders"] == 150
        assert "predictions" in data
        assert data["predictions"]["confidence"] == 0.85
        assert "insights" in data
        assert len(data["insights"]) == 1
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    def test_portfolio_monitor_setup(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test setting up portfolio monitoring"""
        # Mock the bridge response
        mock_portfolio_bridge.setup_monitoring.return_value = {
            "monitor_id": "mon_123456",
            "status": "active",
            "conditions": [
                {
                    "type": "threshold",
                    "metric": "pending_orders",
                    "operator": ">",
                    "value": 50
                }
            ],
            "channels": ["email", "webhook"]
        }
        
        # Request data
        monitor_config = {
            "name": "High Pending Orders Alert",
            "conditions": [
                {
                    "type": "threshold",
                    "metric": "pending_orders",
                    "operator": ">",
                    "value": 50
                }
            ],
            "actions": [
                {
                    "type": "notification",
                    "channels": ["email", "webhook"],
                    "recipients": ["admin@example.com"]
                }
            ],
            "frequency": "realtime"
        }
        
        # Make request
        response = flask_client.post(
            "/api/portfolio/mcp/monitors",
            json=monitor_config,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 201
        data = response.json
        assert data["monitor_id"] == "mon_123456"
        assert data["status"] == "active"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    def test_portfolio_batch_operations(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test batch operations on portfolio items"""
        # Mock the bridge response
        mock_portfolio_bridge.execute_batch_operation.return_value = {
            "operation_id": "batch_789",
            "total": 5,
            "successful": 4,
            "failed": 1,
            "results": [
                {"id": 1, "status": "success", "result": "updated"},
                {"id": 2, "status": "success", "result": "updated"},
                {"id": 3, "status": "success", "result": "updated"},
                {"id": 4, "status": "success", "result": "updated"},
                {"id": 5, "status": "error", "error": "Invalid status transition"}
            ]
        }
        
        # Request data
        batch_data = {
            "operation": "update_status",
            "items": [1, 2, 3, 4, 5],
            "parameters": {
                "new_status": "em_processamento",
                "notify": True
            }
        }
        
        # Make request
        response = flask_client.post(
            "/api/portfolio/mcp/batch",
            json=batch_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json
        assert data["total"] == 5
        assert data["successful"] == 4
        assert data["failed"] == 1
        assert len(data["results"]) == 5
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    def test_portfolio_intelligent_search(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test intelligent search with semantic understanding"""
        # Mock the bridge response
        mock_portfolio_bridge.intelligent_search.return_value = {
            "query_understanding": {
                "original": "pedidos urgentes do cliente VIP que ainda não foram enviados",
                "interpreted_filters": {
                    "priority": "urgent",
                    "customer_type": "VIP",
                    "status": ["pendente", "em_processamento"]
                }
            },
            "results": [
                {
                    "id": 101,
                    "customer": "VIP Corp",
                    "priority": "urgent",
                    "status": "pendente",
                    "value": 15000.00,
                    "relevance_score": 0.95
                }
            ],
            "suggestions": [
                "Você também pode buscar por 'pedidos críticos' para incluir prioridade alta"
            ]
        }
        
        # Request data
        search_data = {
            "query": "pedidos urgentes do cliente VIP que ainda não foram enviados",
            "use_ai": True,
            "limit": 20
        }
        
        # Make request
        response = flask_client.post(
            "/api/portfolio/mcp/search",
            json=search_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json
        assert "query_understanding" in data
        assert data["query_understanding"]["interpreted_filters"]["priority"] == "urgent"
        assert len(data["results"]) == 1
        assert data["results"][0]["relevance_score"] == 0.95
        assert "suggestions" in data
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    def test_portfolio_export_with_analysis(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test portfolio export with AI-powered analysis"""
        # Mock the bridge response
        mock_portfolio_bridge.export_with_analysis.return_value = {
            "export_id": "exp_456",
            "format": "excel",
            "file_url": "/downloads/portfolio_analysis_20240115.xlsx",
            "analysis": {
                "summary": "Análise de 150 pedidos exportados",
                "key_findings": [
                    "80% dos pedidos foram concluídos no prazo",
                    "Clientes VIP representam 45% do valor total"
                ],
                "recommendations": [
                    "Focar em reduzir tempo de processamento para pedidos grandes"
                ]
            }
        }
        
        # Request data
        export_params = {
            "format": "excel",
            "filters": {"date_from": "2024-01-01", "date_to": "2024-01-31"},
            "include_analysis": True,
            "analysis_depth": "detailed"
        }
        
        # Make request
        response = flask_client.post(
            "/api/portfolio/mcp/export",
            json=export_params,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json
        assert data["export_id"] == "exp_456"
        assert "file_url" in data
        assert "analysis" in data
        assert len(data["analysis"]["key_findings"]) == 2
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    def test_portfolio_anomaly_detection(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test anomaly detection in portfolio data"""
        # Mock the bridge response
        mock_portfolio_bridge.detect_anomalies.return_value = {
            "anomalies_detected": 3,
            "anomalies": [
                {
                    "type": "unusual_value",
                    "order_id": 202,
                    "description": "Valor do pedido 500% acima da média",
                    "severity": "high",
                    "suggested_action": "Verificar se há erro de digitação"
                },
                {
                    "type": "pattern_deviation",
                    "customer_id": "cust_789",
                    "description": "Cliente com padrão de compra atípico",
                    "severity": "medium",
                    "suggested_action": "Confirmar pedido com cliente"
                }
            ],
            "statistics": {
                "total_analyzed": 500,
                "anomaly_rate": 0.6
            }
        }
        
        # Request parameters
        params = {
            "period": "last_30_days",
            "sensitivity": "medium",
            "check_types": ["value", "pattern", "frequency"]
        }
        
        # Make request
        response = flask_client.get(
            "/api/portfolio/mcp/anomalies",
            query_string=params,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json
        assert data["anomalies_detected"] == 3
        assert len(data["anomalies"]) >= 2
        assert data["anomalies"][0]["severity"] == "high"
        assert "suggested_action" in data["anomalies"][0]
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    def test_portfolio_workflow_automation(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test automated workflow execution"""
        # Mock the bridge response
        mock_portfolio_bridge.execute_workflow.return_value = {
            "workflow_id": "wf_auto_123",
            "execution_id": "exec_456",
            "status": "completed",
            "steps_executed": 4,
            "results": {
                "orders_processed": 25,
                "emails_sent": 25,
                "status_updated": 25,
                "errors": 0
            },
            "execution_time": 5.2
        }
        
        # Request data
        workflow_data = {
            "workflow_type": "daily_pending_orders",
            "parameters": {
                "send_notifications": True,
                "update_status": True,
                "priority_threshold": "high"
            }
        }
        
        # Make request
        response = flask_client.post(
            "/api/portfolio/mcp/workflows/execute",
            json=workflow_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json
        assert data["status"] == "completed"
        assert data["steps_executed"] == 4
        assert data["results"]["orders_processed"] == 25
        assert data["results"]["errors"] == 0
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.cache
    def test_portfolio_caching_behavior(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test caching behavior for portfolio endpoints"""
        # First request - should hit the service
        mock_portfolio_bridge.get_analytics.return_value = {"metrics": {"total": 100}}
        
        response1 = flask_client.get(
            "/api/portfolio/mcp/analytics",
            headers=auth_headers
        )
        assert response1.status_code == 200
        assert mock_portfolio_bridge.get_analytics.call_count == 1
        
        # Second request - should use cache
        response2 = flask_client.get(
            "/api/portfolio/mcp/analytics",
            headers=auth_headers
        )
        assert response2.status_code == 200
        assert mock_portfolio_bridge.get_analytics.call_count == 1  # Not called again
        
        # Check cache headers
        assert "X-Cache" in response2.headers
        assert response2.headers["X-Cache"] == "HIT"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.auth
    def test_portfolio_real_time_updates(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test real-time updates subscription"""
        # Mock the bridge response
        mock_portfolio_bridge.subscribe_to_updates.return_value = {
            "subscription_id": "sub_789",
            "channel": "websocket",
            "events": ["order_created", "order_updated", "order_cancelled"],
            "endpoint": "wss://api.example.com/portfolio/updates"
        }
        
        # Request data
        subscription_data = {
            "events": ["order_created", "order_updated", "order_cancelled"],
            "filters": {"workspace_id": "test-workspace"},
            "channel": "websocket"
        }
        
        # Make request
        response = flask_client.post(
            "/api/portfolio/mcp/subscribe",
            json=subscription_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 201
        data = response.json
        assert data["subscription_id"] == "sub_789"
        assert data["channel"] == "websocket"
        assert "endpoint" in data


class TestPortfolioErrorHandling:
    """Test error handling in portfolio integration"""
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_portfolio_service_unavailable(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test handling when portfolio service is unavailable"""
        # Mock service unavailable
        mock_portfolio_bridge.get_analytics.side_effect = ConnectionError("Service unavailable")
        
        response = flask_client.get(
            "/api/portfolio/mcp/analytics",
            headers=auth_headers
        )
        
        assert response.status_code == 503
        data = response.json
        assert "error" in data
        assert "service unavailable" in data["error"].lower()
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_portfolio_timeout_handling(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test timeout handling for long-running operations"""
        # Mock timeout
        import asyncio
        
        async def slow_operation():
            await asyncio.sleep(10)  # Longer than timeout
            return {"result": "success"}
        
        mock_portfolio_bridge.process_natural_language_query.return_value = slow_operation()
        
        response = flask_client.post(
            "/api/portfolio/mcp/query",
            json={"query": "Complex analysis query"},
            headers=auth_headers,
            timeout=2  # 2 second timeout
        )
        
        assert response.status_code == 504
        data = response.json
        assert "error" in data
        assert "timeout" in data["error"].lower()
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_portfolio_invalid_query_handling(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test handling of invalid natural language queries"""
        # Mock invalid query response
        mock_portfolio_bridge.process_natural_language_query.return_value = {
            "error": "Could not understand query",
            "suggestions": [
                "Try asking about 'pending orders'",
                "Try asking about 'customer analytics'"
            ]
        }
        
        response = flask_client.post(
            "/api/portfolio/mcp/query",
            json={"query": "xyzabc123 gibberish"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json
        assert "error" in data
        assert "suggestions" in data
        assert len(data["suggestions"]) == 2
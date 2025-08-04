"""
Integration test scenarios for MCP system
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import patch

from fastapi.testclient import TestClient
from tests.mcp_sistema.fixtures.sample_data import (
    get_sample_queries_pt_br,
    get_mock_freight_data,
    get_learning_scenarios
)


class TestCompleteUserJourney:
    """Test complete user journeys through the system"""
    
    @pytest.mark.asyncio
    async def test_freight_creation_to_delivery_journey(self, client: TestClient, auth_headers, db_session):
        """Test complete freight lifecycle from creation to delivery"""
        # Step 1: Create shipment via NLP
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "criar embarque urgente para Rio de Janeiro com 50 caixas de eletrônicos"
            }
        )
        
        assert response.status_code == 200
        result = response.json()["data"]
        assert result["intent"] == "create_shipment"
        assert result["action"]["type"] == "create_shipment"
        shipment_id = result["action"]["result"]["shipment_id"]
        
        # Step 2: Calculate freight cost
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": f"calcular frete para o embarque {shipment_id}",
                "use_context": True
            }
        )
        
        assert response.status_code == 200
        freight_value = response.json()["data"]["action"]["result"]["freight_value"]
        assert freight_value > 0
        
        # Step 3: Approve freight
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "aprovar o frete calculado"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["data"]["action"]["result"]["status"] == "approved"
        
        # Step 4: Track shipment
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": f"rastrear embarque {shipment_id}"
            }
        )
        
        assert response.status_code == 200
        tracking = response.json()["data"]["action"]["result"]
        assert tracking["status"] in ["pending", "in_transit"]
        
        # Step 5: Update delivery status
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": f"marcar embarque {shipment_id} como entregue"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["data"]["action"]["result"]["status"] == "delivered"
        
        # Verify learning from journey
        response = client.get(
            f"/api/v1/mcp/history?limit=5",
            headers=auth_headers
        )
        
        history = response.json()["data"]["queries"]
        assert len(history) == 5
        # System should have learned the workflow pattern
    
    @pytest.mark.asyncio
    async def test_batch_operations_journey(self, client: TestClient, auth_headers):
        """Test batch operations with learning"""
        # Step 1: Create multiple shipments
        shipments = []
        cities = ["São Paulo", "Belo Horizonte", "Curitiba"]
        
        for city in cities:
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={
                    "query": f"criar embarque para {city} com 30 volumes"
                }
            )
            shipments.append(response.json()["data"]["action"]["result"]["shipment_id"])
        
        # Step 2: Batch approve with learning
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "aprovar todos os embarques criados hoje"
            }
        )
        
        assert response.status_code == 200
        approved = response.json()["data"]["action"]["result"]["approved_count"]
        assert approved >= 3
        
        # Step 3: Generate consolidated report
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "gerar relatório dos embarques aprovados com análise de custos"
            }
        )
        
        assert response.status_code == 200
        report = response.json()["data"]["action"]["result"]
        assert "total_freight_value" in report
        assert "shipments_by_destination" in report
        
        # Verify system learned batch patterns
        response = client.get(
            "/api/v1/mcp/suggestions?partial=aprovar todos",
            headers=auth_headers
        )
        
        suggestions = response.json()["data"]["suggestions"]
        assert any("embarques" in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_error_recovery_learning(self, client: TestClient, auth_headers):
        """Test system learning from errors and corrections"""
        # Step 1: Make error-prone query
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "aprovar frete 99999"  # Non-existent freight
            }
        )
        
        assert response.status_code == 200
        result = response.json()["data"]
        assert result["action"]["error"] is not None
        query_id = result["query_id"]
        
        # Step 2: Provide feedback
        response = client.post(
            "/api/v1/mcp/feedback/intent",
            headers=auth_headers,
            json={
                "query_id": query_id,
                "feedback": "The freight ID was incorrect",
                "suggestion": "Always validate freight exists before approval"
            }
        )
        
        assert response.status_code == 200
        
        # Step 3: Test improved handling
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "aprovar frete 88888"  # Another non-existent
            }
        )
        
        # System should now suggest validation
        result = response.json()["data"]
        assert "suggestions" in result or "validation_warning" in result


class TestPerformanceUnderLoad:
    """Test system performance under various load conditions"""
    
    @pytest.mark.asyncio
    async def test_concurrent_nlp_processing(self, client: TestClient, auth_headers):
        """Test NLP processing with concurrent requests"""
        import aiohttp
        import asyncio
        
        async def make_request(session, query):
            url = "http://testserver/api/v1/mcp/query"
            headers = auth_headers.copy()
            
            async with session.post(
                url,
                json={"query": query},
                headers=headers
            ) as response:
                return await response.json(), response.status
        
        # Simulate 50 concurrent users
        queries = get_sample_queries_pt_br()[:10] * 5  # 50 queries
        
        async with aiohttp.ClientSession() as session:
            start_time = asyncio.get_event_loop().time()
            
            tasks = [make_request(session, q["query"]) for q in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = asyncio.get_event_loop().time()
        
        # Verify performance
        successful = [r for r in results if not isinstance(r, Exception) and r[1] == 200]
        assert len(successful) >= 45  # At least 90% success rate
        
        avg_time = (end_time - start_time) / len(queries)
        assert avg_time < 0.2  # Average response time under 200ms
    
    @pytest.mark.asyncio
    async def test_cache_effectiveness(self, client: TestClient, auth_headers):
        """Test caching system effectiveness"""
        # Warm up cache with common queries
        common_queries = [
            "verificar status do frete",
            "criar embarque",
            "aprovar frete"
        ]
        
        # First pass - populate cache
        first_times = []
        for query in common_queries * 3:
            start = asyncio.get_event_loop().time()
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": query}
            )
            first_times.append(asyncio.get_event_loop().time() - start)
        
        # Second pass - should hit cache
        second_times = []
        for query in common_queries * 3:
            start = asyncio.get_event_loop().time()
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": query}
            )
            second_times.append(asyncio.get_event_loop().time() - start)
        
        # Cache should improve performance by at least 50%
        avg_first = sum(first_times) / len(first_times)
        avg_second = sum(second_times) / len(second_times)
        assert avg_second < avg_first * 0.5
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, client: TestClient, auth_headers):
        """Test memory usage remains stable under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate load
        for i in range(100):
            # Create diverse queries to prevent caching
            query = f"criar embarque numero {i} para cidade {i % 20}"
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": query}
            )
            
            if i % 10 == 0:
                # Check memory growth
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be limited
                assert memory_growth < 100  # Less than 100MB growth


class TestLearningSystemIntegration:
    """Test learning system integration with real scenarios"""
    
    @pytest.mark.asyncio
    async def test_personalized_learning_journey(self, client: TestClient, auth_headers):
        """Test personalized learning based on user behavior"""
        scenarios = get_learning_scenarios()
        
        for scenario in scenarios:
            # Execute scenario interactions
            for interaction in scenario["interactions"]:
                response = client.post(
                    "/api/v1/mcp/query",
                    headers=auth_headers,
                    json={
                        "query": interaction["query"],
                        "metadata": {"region": interaction.get("region")}
                    }
                )
                
                # Provide feedback if needed
                if interaction["feedback"] == "corrected":
                    client.post(
                        "/api/v1/mcp/feedback/intent",
                        headers=auth_headers,
                        json={
                            "query_id": response.json()["data"]["query_id"],
                            "correct_intent": interaction["intent"]
                        }
                    )
            
            # Verify learning outcomes
            response = client.get(
                "/api/v1/users/learning-profile",
                headers=auth_headers
            )
            
            profile = response.json()["data"]
            
            # Check if expected learning occurred
            if "typo_correction" in scenario["expected_learning"]:
                assert "learned_corrections" in profile
            
            if "query_style" in scenario["expected_learning"]:
                assert profile["preferred_style"] == scenario["expected_learning"]["query_style"]
    
    @pytest.mark.asyncio
    async def test_cross_user_learning(self, client: TestClient, jwt_service):
        """Test learning shared across users while maintaining personalization"""
        # Create multiple users
        users = []
        for i in range(3):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"user{i}",
                    "email": f"user{i}@example.com",
                    "password": "TestPass123!"
                }
            )
            
            login = client.post(
                "/api/v1/auth/login",
                json={
                    "username": f"user{i}",
                    "password": "TestPass123!"
                }
            )
            
            token = login.json()["data"]["access_token"]
            users.append({"id": i, "headers": {"Authorization": f"Bearer {token}"}})
        
        # User 1 discovers new query pattern
        response = client.post(
            "/api/v1/mcp/query",
            headers=users[0]["headers"],
            json={
                "query": "mostrar KPIs operacionais em tempo real"
            }
        )
        
        # System doesn't understand initially
        assert response.json()["data"]["confidence"] < 0.5
        
        # User provides feedback
        client.post(
            "/api/v1/mcp/feedback/intent",
            headers=users[0]["headers"],
            json={
                "query_id": response.json()["data"]["query_id"],
                "correct_intent": "show_operational_dashboard",
                "entities": {"metric_type": "KPI", "mode": "realtime"}
            }
        )
        
        # User 2 tries similar query - should benefit from User 1's feedback
        response = client.post(
            "/api/v1/mcp/query",
            headers=users[1]["headers"],
            json={
                "query": "exibir KPIs de vendas ao vivo"
            }
        )
        
        # Should understand better due to cross-user learning
        assert response.json()["data"]["confidence"] > 0.7
        assert response.json()["data"]["intent"] == "show_operational_dashboard"


class TestRealWorldScenarios:
    """Test real-world business scenarios"""
    
    @pytest.mark.asyncio
    async def test_month_end_closing_scenario(self, client: TestClient, auth_headers):
        """Test month-end closing operations"""
        # Step 1: Check pending approvals
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "listar todos os fretes pendentes de aprovação do mês"
            }
        )
        
        pending_count = response.json()["data"]["action"]["result"]["count"]
        
        # Step 2: Bulk approve valid freights
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "aprovar fretes pendentes com valor menor que 5000 reais"
            }
        )
        
        # Step 3: Generate month-end report
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "gerar relatório de fechamento mensal com análise de margem e inadimplência"
            }
        )
        
        report = response.json()["data"]["action"]["result"]
        assert "total_revenue" in report
        assert "profit_margin" in report
        assert "overdue_payments" in report
        
        # Step 4: Export for accounting
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "exportar dados contábeis do mês em formato Excel"
            }
        )
        
        assert response.json()["data"]["action"]["result"]["file_url"] is not None
    
    @pytest.mark.asyncio
    async def test_emergency_shipment_scenario(self, client: TestClient, auth_headers):
        """Test emergency shipment handling"""
        # Emergency request comes in
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "URGENTE criar embarque expresso para Manaus saída hoje mesmo com 200kg de medicamentos"
            }
        )
        
        # System should recognize urgency
        result = response.json()["data"]
        assert result["priority"] == "urgent"
        assert result["action"]["result"]["express_shipping"] is True
        
        shipment_id = result["action"]["result"]["shipment_id"]
        
        # Find best route
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": f"calcular melhor rota aérea para embarque {shipment_id} com entrega em 24 horas"
            }
        )
        
        route = response.json()["data"]["action"]["result"]
        assert route["transport_mode"] == "air"
        assert route["estimated_hours"] <= 24
        
        # Priority notifications
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": f"notificar gerência sobre embarque urgente {shipment_id}"
            }
        )
        
        assert response.json()["data"]["action"]["result"]["notifications_sent"] > 0
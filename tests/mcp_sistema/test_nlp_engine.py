"""
Tests for NLP engine and query processing
"""
import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

from app.mcp_sistema.services.nlp.nlp_engine import NLPEngine
from app.mcp_sistema.services.nlp.intent_classifier import IntentClassifier
from app.mcp_sistema.services.nlp.context_manager import ContextManager
from app.mcp_sistema.models.mcp_models import QueryLog, UserContext


class TestNLPEngine:
    """Test suite for the main NLP engine"""
    
    @pytest.fixture
    def nlp_engine(self, db_session):
        """Create NLP engine instance"""
        return NLPEngine(db_session)
    
    @pytest.mark.asyncio
    async def test_process_query_basic(self, nlp_engine, sample_queries_pt_br):
        """Test basic query processing"""
        query = sample_queries_pt_br[0]["query"]
        result = await nlp_engine.process_query(query, user_id=1)
        
        assert "intent" in result
        assert "entities" in result
        assert "confidence" in result
        assert result["intent"] == "create_shipment"
        assert result["confidence"] > 0.8
    
    @pytest.mark.asyncio
    async def test_process_query_with_context(self, nlp_engine):
        """Test query processing with context awareness"""
        # First query
        result1 = await nlp_engine.process_query(
            "qual o status do frete 12345",
            user_id=1
        )
        
        # Follow-up query using context
        result2 = await nlp_engine.process_query(
            "e quando foi entregue",  # Refers to previous freight
            user_id=1
        )
        
        assert result2["intent"] == "check_delivery_date"
        assert "freight_id" in result2["entities"]
        assert result2["entities"]["freight_id"] == "12345"  # From context
    
    @pytest.mark.asyncio
    async def test_process_ambiguous_query(self, nlp_engine):
        """Test handling of ambiguous queries"""
        result = await nlp_engine.process_query(
            "cancelar",  # Ambiguous - what to cancel?
            user_id=1
        )
        
        assert result["confidence"] < 0.5
        assert "clarification_needed" in result
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0
    
    @pytest.mark.asyncio
    async def test_process_query_with_typos(self, nlp_engine):
        """Test query processing with typos and corrections"""
        queries_with_typos = [
            ("crear embarque para sao paolo", "create_shipment"),
            ("aprobar frete pendetne", "approve_freight"),
            ("relatorio de entreguas", "generate_report")
        ]
        
        for query, expected_intent in queries_with_typos:
            result = await nlp_engine.process_query(query, user_id=1)
            assert result["intent"] == expected_intent
            assert "corrected_query" in result
    
    @pytest.mark.asyncio
    async def test_multilingual_support(self, nlp_engine):
        """Test support for Portuguese variations"""
        variations = [
            ("criar embarque", "create_shipment"),  # PT-BR
            ("crear embarque", "create_shipment"),  # Spanish influence
            ("create shipment", "create_shipment"),  # English
        ]
        
        for query, expected_intent in variations:
            result = await nlp_engine.process_query(query, user_id=1)
            assert result["intent"] == expected_intent
    
    @pytest.mark.asyncio
    async def test_query_logging(self, nlp_engine, db_session):
        """Test that queries are properly logged"""
        query = "aprovar frete 123"
        result = await nlp_engine.process_query(query, user_id=1)
        
        # Check log was created
        log = db_session.query(QueryLog).filter_by(
            user_id=1,
            query=query
        ).first()
        
        assert log is not None
        assert log.intent == result["intent"]
        assert log.confidence == result["confidence"]
        assert log.response_time is not None
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, nlp_engine, sample_queries_pt_br, performance_metrics):
        """Test NLP processing performance"""
        import time
        
        processing_times = []
        
        for query_data in sample_queries_pt_br:
            start = time.time()
            await nlp_engine.process_query(query_data["query"], user_id=1)
            processing_times.append((time.time() - start) * 1000)
        
        avg_time = sum(processing_times) / len(processing_times)
        assert avg_time < performance_metrics["nlp_processing_time_ms"]
        assert max(processing_times) < performance_metrics["nlp_processing_time_ms"] * 2
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, nlp_engine, sample_queries_pt_br):
        """Test batch query processing"""
        queries = [q["query"] for q in sample_queries_pt_br]
        results = await nlp_engine.process_batch(queries, user_id=1)
        
        assert len(results) == len(queries)
        assert all("intent" in r for r in results)
        assert all(r["confidence"] > 0 for r in results)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, nlp_engine):
        """Test error handling in NLP engine"""
        # Test with None
        result = await nlp_engine.process_query(None, user_id=1)
        assert result["error"] is not None
        
        # Test with empty string
        result = await nlp_engine.process_query("", user_id=1)
        assert result["error"] is not None
        
        # Test with very long query
        long_query = "a" * 10000
        result = await nlp_engine.process_query(long_query, user_id=1)
        assert "error" in result or "truncated" in result


class TestIntentClassifier:
    """Test suite for intent classification"""
    
    @pytest.fixture
    def classifier(self):
        """Create intent classifier instance"""
        return IntentClassifier()
    
    def test_classify_intent_basic(self, classifier, sample_queries_pt_br):
        """Test basic intent classification"""
        for query_data in sample_queries_pt_br:
            intent, confidence = classifier.classify(query_data["query"])
            assert intent == query_data["intent"]
            assert confidence > 0.8
    
    def test_classify_unknown_intent(self, classifier):
        """Test classification of unknown intents"""
        intent, confidence = classifier.classify("fazer cafe com leite")
        assert intent == "unknown"
        assert confidence < 0.5
    
    def test_intent_patterns(self, classifier):
        """Test intent classification patterns"""
        patterns = [
            # Create patterns
            ("criar novo embarque", "create_shipment"),
            ("gerar embarque", "create_shipment"),
            ("novo embarque para", "create_shipment"),
            
            # Status patterns
            ("qual status", "check_status"),
            ("verificar situação", "check_status"),
            ("como está o", "check_status"),
            
            # Approval patterns
            ("aprovar frete", "approve_freight"),
            ("liberar pagamento", "approve_payment"),
            ("autorizar embarque", "approve_shipment")
        ]
        
        for query, expected_intent in patterns:
            intent, _ = classifier.classify(query)
            assert intent == expected_intent
    
    def test_intent_confidence_scores(self, classifier):
        """Test confidence score calculation"""
        # Clear intent
        _, confidence = classifier.classify("criar embarque para São Paulo")
        assert confidence > 0.9
        
        # Ambiguous intent
        _, confidence = classifier.classify("embarque")
        assert confidence < 0.7
        
        # Multiple possible intents
        _, confidence = classifier.classify("frete 123")
        assert 0.4 < confidence < 0.8
    
    def test_intent_training(self, classifier):
        """Test training classifier with new examples"""
        # Add new training examples
        new_examples = [
            ("rastrear entrega", "track_delivery"),
            ("onde está minha carga", "track_delivery"),
            ("localizar embarque", "track_delivery")
        ]
        
        classifier.train(new_examples)
        
        # Test recognition
        intent, confidence = classifier.classify("rastrear meu pedido")
        assert intent == "track_delivery"
        assert confidence > 0.7
    
    def test_intent_similarity(self, classifier):
        """Test intent similarity calculation"""
        base_query = "criar embarque"
        similar_queries = [
            "gerar embarque",
            "novo embarque",
            "fazer embarque"
        ]
        
        for query in similar_queries:
            similarity = classifier.calculate_similarity(base_query, query)
            assert similarity > 0.7
    
    def test_composite_intents(self, classifier):
        """Test classification of composite intents"""
        query = "criar embarque e aprovar frete"
        intents = classifier.classify_multiple(query)
        
        assert len(intents) == 2
        assert any(i[0] == "create_shipment" for i in intents)
        assert any(i[0] == "approve_freight" for i in intents)


class TestContextManager:
    """Test suite for context management"""
    
    @pytest.fixture
    def context_manager(self, db_session):
        """Create context manager instance"""
        return ContextManager(db_session)
    
    @pytest.mark.asyncio
    async def test_store_context(self, context_manager):
        """Test storing user context"""
        context = {
            "current_freight": "12345",
            "current_client": "ABC Corp",
            "last_action": "check_status"
        }
        
        await context_manager.store_context(user_id=1, context=context)
        retrieved = await context_manager.get_context(user_id=1)
        
        assert retrieved == context
    
    @pytest.mark.asyncio
    async def test_update_context(self, context_manager):
        """Test updating existing context"""
        # Store initial context
        initial = {"current_freight": "12345"}
        await context_manager.store_context(1, initial)
        
        # Update context
        update = {"current_client": "XYZ Corp"}
        await context_manager.update_context(1, update)
        
        # Verify merge
        context = await context_manager.get_context(1)
        assert context["current_freight"] == "12345"
        assert context["current_client"] == "XYZ Corp"
    
    @pytest.mark.asyncio
    async def test_context_expiration(self, context_manager):
        """Test context expiration"""
        import asyncio
        
        context = {"temp_data": "value"}
        await context_manager.store_context(1, context, ttl_seconds=1)
        
        # Verify stored
        assert await context_manager.get_context(1) == context
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Verify expired
        assert await context_manager.get_context(1) is None
    
    @pytest.mark.asyncio
    async def test_context_history(self, context_manager):
        """Test maintaining context history"""
        contexts = [
            {"action": "create", "object": "shipment"},
            {"action": "check", "object": "freight"},
            {"action": "approve", "object": "payment"}
        ]
        
        for ctx in contexts:
            await context_manager.add_to_history(1, ctx)
        
        history = await context_manager.get_history(1, limit=2)
        assert len(history) == 2
        assert history[0]["action"] == "approve"  # Most recent first
    
    @pytest.mark.asyncio
    async def test_clear_context(self, context_manager):
        """Test clearing user context"""
        await context_manager.store_context(1, {"data": "value"})
        await context_manager.clear_context(1)
        
        assert await context_manager.get_context(1) is None
    
    @pytest.mark.asyncio
    async def test_multi_user_context(self, context_manager):
        """Test context isolation between users"""
        await context_manager.store_context(1, {"user": "one"})
        await context_manager.store_context(2, {"user": "two"})
        
        ctx1 = await context_manager.get_context(1)
        ctx2 = await context_manager.get_context(2)
        
        assert ctx1["user"] == "one"
        assert ctx2["user"] == "two"
    
    @pytest.mark.asyncio
    async def test_context_relevance(self, context_manager):
        """Test determining context relevance"""
        context = {
            "current_freight": "12345",
            "current_action": "check_status",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await context_manager.store_context(1, context)
        
        # Relevant query
        is_relevant = await context_manager.is_context_relevant(
            1, "quando foi entregue"  # Refers to current freight
        )
        assert is_relevant
        
        # Irrelevant query
        is_relevant = await context_manager.is_context_relevant(
            1, "criar novo usuario"  # Unrelated to context
        )
        assert not is_relevant


class TestNLPIntegration:
    """Integration tests for NLP components"""
    
    @pytest.mark.asyncio
    async def test_full_nlp_pipeline(self, nlp_engine, db_session):
        """Test complete NLP pipeline from query to response"""
        # Simulate conversation flow
        queries = [
            "criar embarque para Rio de Janeiro",
            "adicionar 10 caixas",
            "qual o valor estimado",
            "confirmar e enviar"
        ]
        
        results = []
        for query in queries:
            result = await nlp_engine.process_query(query, user_id=1)
            results.append(result)
        
        # Verify context was maintained
        assert results[1]["entities"].get("shipment_id") is not None
        assert results[2]["entities"].get("shipment_id") == results[1]["entities"]["shipment_id"]
        
        # Verify intent progression
        assert results[0]["intent"] == "create_shipment"
        assert results[1]["intent"] == "add_items"
        assert results[2]["intent"] == "calculate_freight"
        assert results[3]["intent"] == "confirm_shipment"
    
    @pytest.mark.asyncio
    async def test_nlp_learning_from_feedback(self, nlp_engine, db_session):
        """Test NLP learning from user corrections"""
        # Process query with potential misunderstanding
        query = "liberar carga"
        result = await nlp_engine.process_query(query, user_id=1)
        
        # Simulate user correction
        await nlp_engine.learn_from_feedback(
            query_id=result["query_id"],
            correct_intent="release_shipment",
            correct_entities={"action": "release", "object": "shipment"}
        )
        
        # Process similar query
        new_result = await nlp_engine.process_query("liberar embarque", user_id=1)
        assert new_result["intent"] == "release_shipment"
        assert new_result["confidence"] > result["confidence"]
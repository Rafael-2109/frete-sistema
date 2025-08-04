"""
Tests for Claude 4 Sonnet Integration and Fallback System
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from app.mcp_logistica.claude_integration import (
    ClaudeIntegration, ClaudeContext, ClaudeResponse
)
from app.mcp_logistica.nlp_engine import ProcessedQuery
from app.mcp_logistica.intent_classifier import Intent


class TestClaudeIntegration:
    """Test Claude 4 Sonnet integration functionality"""
    
    def test_initialization_with_api_key(self):
        """Test initialization with API key"""
        claude = ClaudeIntegration(api_key='test-key')
        assert claude.api_key == 'test-key'
        assert claude.max_context_queries == 10
        assert hasattr(claude, 'session_contexts')
        
    def test_initialization_without_api_key(self):
        """Test initialization without API key"""
        claude = ClaudeIntegration()
        assert claude.enabled == False
        assert claude.client is None
        
    def test_get_session_context(self, claude_integration):
        """Test session context creation and retrieval"""
        user_id = "user1"
        session_id = "session1"
        
        context = claude_integration._get_session_context(user_id, session_id)
        
        assert isinstance(context, ClaudeContext)
        assert context.user_id == user_id
        assert context.session_id == session_id
        assert context.domain_context == "logistics"
        assert len(context.previous_queries) == 0
        
        # Should retrieve same context
        context2 = claude_integration._get_session_context(user_id, session_id)
        assert context is context2
        
    def test_update_session_context(self, claude_integration):
        """Test updating session context with queries"""
        context = claude_integration._get_session_context("user1", "session1")
        
        # Add queries
        for i in range(15):
            claude_integration._update_session_context(
                context,
                f"Query {i}",
                {'success': True, 'intent': 'buscar'}
            )
            
        # Should keep only last 10
        assert len(context.previous_queries) == 10
        assert context.previous_queries[0]['query'] == "Query 5"
        assert context.previous_queries[-1]['query'] == "Query 14"
        
    def test_generate_claude_prompt(self, claude_integration):
        """Test Claude prompt generation"""
        query = "Quantas entregas atrasadas temos?"
        
        processed = ProcessedQuery(
            original_query=query,
            normalized_query="quantas entregas atrasadas temos",
            tokens=["quantas", "entregas", "atrasadas"],
            intent="contar",
            confidence=0.8,
            entities={'temporal': {'value': 'today', 'type': 'date'}},
            context={'domain': 'entregas'},
            response_format="single_value"
        )
        
        intent = Intent(primary="contar", confidence=0.8)
        context = claude_integration._get_session_context("user1", "session1")
        
        prompt = claude_integration._generate_claude_prompt(query, processed, intent, context)
        
        assert query in prompt
        assert "contar" in prompt
        assert "0.8" in prompt
        assert "temporal" in prompt
        assert "Database Schema Context" in prompt
        
    def test_generate_claude_prompt_with_history(self, claude_integration):
        """Test prompt generation with query history"""
        context = claude_integration._get_session_context("user1", "session1")
        
        # Add previous queries
        context.previous_queries = [
            {'query': 'buscar entregas', 'intent': 'buscar'},
            {'query': 'status pedido 123', 'intent': 'status'}
        ]
        
        processed = Mock()
        processed.entities = {}
        intent = Intent(primary="contar", confidence=0.9)
        
        prompt = claude_integration._generate_claude_prompt("nova consulta", processed, intent, context)
        
        assert "buscar entregas" in prompt
        assert "status pedido 123" in prompt
        
    def test_process_with_fallback_disabled(self, claude_integration):
        """Test fallback when Claude is disabled"""
        claude_integration.enabled = False
        
        result = claude_integration.process_with_fallback(
            "test query",
            Mock(),
            Mock(),
            None,
            {'user_id': 'test'}
        )
        
        assert isinstance(result, ClaudeResponse)
        assert result.success == True
        assert result.response_type == 'disabled'
        assert result.confidence == 0.0
        
    def test_process_with_fallback_low_confidence(self, claude_integration, mock_claude_response):
        """Test fallback triggered by low confidence"""
        # Mock Claude client
        claude_integration.client.messages.create.return_value = mock_claude_response()
        
        processed = Mock()
        processed.entities = {}
        intent = Intent(primary="buscar", confidence=0.5)  # Low confidence
        sql_result = {'success': True, 'data': []}
        
        result = claude_integration.process_with_fallback(
            "consulta ambígua",
            processed,
            intent,
            sql_result,
            {'user_id': 'test', 'session_id': 'test'}
        )
        
        assert result.response_type == 'direct'
        assert result.direct_answer is not None
        assert result.confidence == 0.8
        assert 'fallback_reason' in result.metadata
        
    def test_process_with_fallback_no_entities(self, claude_integration, mock_claude_response):
        """Test fallback triggered by missing entities"""
        claude_integration.client.messages.create.return_value = mock_claude_response()
        
        processed = Mock()
        processed.entities = {}  # No entities
        intent = Intent(primary="buscar", confidence=0.8)
        
        result = claude_integration.process_with_fallback(
            "buscar algo",
            processed,
            intent,
            None,
            {'user_id': 'test', 'session_id': 'test'}
        )
        
        assert result.success == True
        assert result.response_type == 'direct'
        
    def test_process_with_fallback_sql_error(self, claude_integration, mock_claude_response):
        """Test fallback triggered by SQL error"""
        claude_integration.client.messages.create.return_value = mock_claude_response()
        
        processed = Mock()
        processed.entities = {'nf': '123'}
        intent = Intent(primary="status", confidence=0.9)
        sql_result = {'success': False, 'error': 'SQL syntax error'}
        
        result = claude_integration.process_with_fallback(
            "status da nf 123",
            processed,
            intent,
            sql_result,
            {'user_id': 'test', 'session_id': 'test'}
        )
        
        assert result.success == True
        assert 'sql_error' in result.metadata.get('fallback_reason', '')
        
    def test_enhance_sql_results(self, claude_integration, mock_claude_response):
        """Test enhancing SQL results with insights"""
        claude_integration.client.messages.create.return_value = mock_claude_response()
        
        sql_result = {
            'success': True,
            'data': [{'id': 1, 'valor': 100}, {'id': 2, 'valor': 200}],
            'sql': 'SELECT * FROM test'
        }
        
        context = claude_integration._get_session_context("user1", "session1")
        result = claude_integration._enhance_sql_results("query", sql_result, context)
        
        assert result.success == True
        assert result.response_type == 'enhanced'
        assert result.insights is not None
        assert len(result.insights) > 0
        
    def test_enhance_sql_results_empty_data(self, claude_integration):
        """Test enhancement with empty SQL results"""
        sql_result = {
            'success': True,
            'data': [],
            'sql': 'SELECT * FROM test WHERE 1=0'
        }
        
        context = claude_integration._get_session_context("user1", "session1")
        result = claude_integration._enhance_sql_results("query", sql_result, context)
        
        assert result.response_type == 'sql_only'
        assert result.insights is None
        
    def test_summarize_sql_results(self, claude_integration):
        """Test SQL result summarization"""
        # Dict with total
        summary = claude_integration._summarize_sql_results({'total': 42})
        assert summary == "Total count: 42"
        
        # List of items
        summary = claude_integration._summarize_sql_results([{'id': 1}, {'id': 2}])
        assert "2 records" in summary
        
        # Empty list
        summary = claude_integration._summarize_sql_results([])
        assert summary == "No results found"
        
        # Numeric result
        summary = claude_integration._summarize_sql_results(100)
        assert summary == "Numeric result: 100"
        
    def test_extract_suggestions(self, claude_integration):
        """Test suggestion extraction from Claude response"""
        claude_text = """
        Based on your query, here are some insights:
        
        Try: Filtering by date range for better results
        Consider: Adding status filter to narrow down
        You could: Export the results to Excel for analysis
        
        Example: "Show delayed deliveries from last week"
        
        Some other text without suggestions.
        """
        
        suggestions = claude_integration._extract_suggestions(claude_text)
        
        assert len(suggestions) == 3  # Limited to 3
        assert any("Filtering by date" in s for s in suggestions)
        assert any("status filter" in s for s in suggestions)
        
    def test_generate_natural_response(self, claude_integration):
        """Test natural language response generation"""
        query_result = {
            'success': True,
            'data': {'total': 15}
        }
        
        claude_response = ClaudeResponse(
            success=True,
            response_type='hybrid',
            insights=["Houve um aumento de 20% comparado ao mês anterior"],
            suggestions=["Verificar entregas por região", "Analisar por transportadora"]
        )
        
        natural = claude_integration.generate_natural_response(query_result, claude_response)
        
        assert "15 registros" in natural
        assert "20% comparado" in natural
        assert "Sugestões:" in natural
        assert "Verificar entregas" in natural
        
    def test_clear_session_context(self, claude_integration):
        """Test clearing session context"""
        # Create context
        context = claude_integration._get_session_context("user1", "session1")
        context.previous_queries.append({'query': 'test'})
        
        # Clear it
        claude_integration.clear_session_context("user1", "session1")
        
        # Should create new context
        new_context = claude_integration._get_session_context("user1", "session1")
        assert len(new_context.previous_queries) == 0
        assert context is not new_context
        
    def test_get_session_summary(self, claude_integration):
        """Test session summary generation"""
        context = claude_integration._get_session_context("user1", "session1")
        
        # Add some queries
        queries = [
            {'query': 'buscar entregas', 'intent': 'buscar'},
            {'query': 'contar pedidos', 'intent': 'contar'},
            {'query': 'status nf 123', 'intent': 'status'}
        ]
        
        for q in queries:
            context.previous_queries.append(q)
            
        summary = claude_integration.get_session_summary("user1", "session1")
        
        assert summary['session_id'] == "session1"
        assert summary['query_count'] == 3
        assert len(summary['recent_queries']) == 3
        assert 'buscar' in summary['domains_accessed']
        assert 'contar' in summary['domains_accessed']
        
    def test_error_handling_api_call(self, claude_integration):
        """Test error handling in API calls"""
        # Make client raise exception
        claude_integration.client.messages.create.side_effect = Exception("API Error")
        
        processed = Mock()
        processed.entities = {}
        intent = Mock(primary="buscar", confidence=0.5)
        
        result = claude_integration.process_with_fallback(
            "test query",
            processed,
            intent,
            None,
            {'user_id': 'test', 'session_id': 'test'}
        )
        
        assert result.success == False
        assert result.response_type == 'error'
        assert "API Error" in result.direct_answer
        
    def test_complex_intent_processing(self, claude_integration, mock_claude_response):
        """Test processing complex intents that require Claude"""
        claude_integration.client.messages.create.return_value = mock_claude_response()
        
        processed = Mock()
        processed.entities = {'cliente': 'ABC'}
        intent = Intent(primary="analisar", confidence=0.9)  # Complex intent
        
        result = claude_integration.process_with_fallback(
            "analisar padrão de compras do cliente ABC",
            processed,
            intent,
            {'success': True, 'data': []},
            {'user_id': 'test', 'session_id': 'test'}
        )
        
        assert result.success == True
        assert result.response_type in ['direct', 'hybrid']
        
    def test_performance_prompt_generation(self, claude_integration, performance_logger):
        """Test performance of prompt generation"""
        processed = Mock()
        processed.entities = {'nf': '123', 'temporal': {'value': 'today'}}
        intent = Intent(primary="status", confidence=0.8)
        context = claude_integration._get_session_context("user1", "session1")
        
        # Add history
        for i in range(10):
            context.previous_queries.append({'query': f'Query {i}', 'intent': 'test'})
            
        ctx = performance_logger.start("generate_prompt")
        prompt = claude_integration._generate_claude_prompt(
            "status da nf 123",
            processed,
            intent,
            context
        )
        duration = performance_logger.end(ctx)
        
        assert duration < 0.01  # Should be very fast
        assert len(prompt) > 0
        
    def test_session_context_persistence(self, claude_integration):
        """Test session context persistence across calls"""
        user_id = "user1"
        session_id = "session1"
        
        # First call
        result1 = claude_integration.process_with_fallback(
            "primeira consulta",
            Mock(entities={}),
            Intent(primary="buscar", confidence=0.5),
            None,
            {'user_id': user_id, 'session_id': session_id}
        )
        
        # Second call - should have history
        context = claude_integration._get_session_context(user_id, session_id)
        assert len(context.previous_queries) > 0
        assert context.previous_queries[0]['query'] == "primeira consulta"
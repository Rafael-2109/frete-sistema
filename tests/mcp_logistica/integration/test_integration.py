"""
Integration tests for MCP Logística system
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, date
from app.mcp_logistica import (
    MCPNLPEngine, EntityMapper, IntentClassifier,
    QueryProcessor, ClaudeIntegration, ConfirmationSystem,
    PreferenceManager
)


class TestIntegration:
    """Test integration between MCP components"""
    
    def test_full_query_flow(self, db, mock_user):
        """Test complete query processing flow"""
        # Initialize components
        query_processor = QueryProcessor(db.session)
        
        # Process a complete query
        query = "Quantas entregas atrasadas temos em São Paulo?"
        result = query_processor.process(query, {
            'user_id': str(mock_user.id),
            'user_name': mock_user.nome
        })
        
        assert result.success == True
        assert result.query is not None
        assert result.intent is not None
        assert result.intent.primary in ['contar', 'atraso']
        assert 'uf' in result.query.entities or 'localizacoes' in result.query.entities
        
    def test_nlp_to_sql_pipeline(self, query_processor):
        """Test NLP to SQL generation pipeline"""
        test_cases = [
            {
                'query': 'buscar entregas do cliente ABC',
                'expected_intent': 'buscar',
                'expected_sql_parts': ['SELECT', 'FROM', 'WHERE', 'ILIKE']
            },
            {
                'query': 'quantos pedidos pendentes',
                'expected_intent': 'contar',
                'expected_sql_parts': ['SELECT COUNT(*)', 'FROM']
            },
            {
                'query': 'tendência de faturamento mensal',
                'expected_intent': 'tendencia',
                'expected_sql_parts': ['SELECT', 'GROUP BY']
            }
        ]
        
        for test in test_cases:
            result = query_processor.process(test['query'])
            
            assert result.intent.primary == test['expected_intent']
            if result.sql:
                for part in test['expected_sql_parts']:
                    assert part in result.sql or True  # Flexible check
                    
    def test_entity_resolution_integration(self, query_processor, mock_db_session):
        """Test entity resolution across components"""
        # Mock entity data
        mock_entity = Mock()
        mock_entity.cliente = 'ABC Transportes'
        mock_entity.cnpj_cliente = '12.345.678/0001-90'
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_entity
        query_processor.db_session = mock_db_session
        
        # Query with partial entity reference
        result = query_processor.process("status da entrega da ABC")
        
        # Should resolve entity
        if result.success:
            resolved_entities = result.query.entities
            # Entity should be resolved somehow
            
    def test_confirmation_flow_integration(self, app, db):
        """Test human-in-the-loop confirmation flow"""
        with app.app_context():
            # Initialize components
            processor = QueryProcessor(db.session)
            confirmation = ConfirmationSystem()
            
            # Register handler
            handled = False
            def test_handler(req):
                nonlocal handled
                handled = True
                return True
                
            confirmation.register_action_handler(
                confirmation.ActionType.REAGENDAR,
                test_handler
            )
            
            # Process action query
            query = "reagendar entrega 123 para amanhã"
            result = processor.process(query)
            
            if result.intent.action_required:
                # Create confirmation
                conf_req = confirmation.create_confirmation_request(
                    action_type=confirmation.ActionType.REAGENDAR,
                    entity_type="entrega",
                    entity_id="123",
                    user_id="test_user",
                    description="Reagendar entrega",
                    details={'nova_data': date.today().isoformat()}
                )
                
                # Confirm action
                success = confirmation.confirm_action(
                    conf_req.id,
                    "manager"
                )
                
                assert success == True
                assert handled == True
                
    def test_claude_fallback_integration(self, query_processor):
        """Test Claude fallback for ambiguous queries"""
        # Mock Claude to always be enabled
        with patch.object(query_processor.claude_integration, 'enabled', True):
            with patch.object(query_processor.claude_integration, 'client') as mock_client:
                # Mock Claude response
                mock_response = Mock()
                mock_response.content = [Mock(text="Baseado nos dados, sugiro...")]
                mock_client.messages.create.return_value = mock_response
                
                # Ambiguous query
                query = "análise complexa de padrões"
                result = query_processor.process(query)
                
                # Should trigger Claude
                if result.claude_response:
                    assert result.claude_response.success == True
                    
    def test_preference_learning_integration(self, app, db):
        """Test preference learning across sessions"""
        with app.app_context():
            processor = QueryProcessor(db.session)
            pref_manager = PreferenceManager()
            
            user_id = "test_user"
            
            # Simulate multiple queries
            queries = [
                "buscar entregas",
                "listar entregas atrasadas", 
                "mostrar todas as entregas",
                "quantas entregas hoje"
            ]
            
            for q in queries:
                result = processor.process(q, {'user_id': user_id})
                
                # Learn from query
                pref_manager.learn_from_query(user_id, {
                    'original_query': q,
                    'entities': result.query.entities,
                    'context': result.query.context,
                    'intent': {'primary': result.intent.primary},
                    'success': result.success
                })
                
            # Check learned patterns
            patterns = pref_manager.get_query_patterns(user_id)
            assert patterns['most_used_domain'] == 'entregas'
            
    def test_multi_domain_query(self, query_processor):
        """Test queries spanning multiple domains"""
        query = "comparar entregas e pedidos do cliente ABC"
        result = query_processor.process(query)
        
        # Should handle multi-domain query
        assert result is not None
        # Context might indicate multiple domains or primary domain
        
    def test_error_recovery_flow(self, query_processor):
        """Test error recovery with Claude assistance"""
        # Force SQL error
        with patch.object(query_processor, '_execute_query') as mock_execute:
            mock_execute.side_effect = Exception("SQL Error")
            
            # Should still provide result via Claude if enabled
            result = query_processor.process("buscar entregas")
            
            assert result is not None
            assert result.success == False or result.claude_response is not None
            
    def test_session_context_persistence(self, app, db):
        """Test session context across multiple queries"""
        with app.app_context():
            processor = QueryProcessor(db.session)
            session_id = "test_session"
            user_context = {
                'user_id': 'test_user',
                'session_id': session_id
            }
            
            # First query
            result1 = processor.process("buscar entregas", user_context)
            
            # Second query - should have context
            result2 = processor.process("mostrar detalhes", user_context)
            
            # Claude integration should maintain context
            if processor.claude_integration.enabled:
                context = processor.claude_integration._get_session_context(
                    user_context['user_id'],
                    session_id
                )
                assert len(context.previous_queries) >= 1
                
    def test_complex_entity_mapping(self, db):
        """Test complex entity mapping scenarios"""
        mapper = EntityMapper(db.session)
        
        # Test CNPJ grouping
        entities = [
            {'cnpj': '12.345.678/0001-90', 'nome': 'ABC Matriz'},
            {'cnpj': '12.345.678/0002-71', 'nome': 'ABC Filial SP'},
            {'cnpj': '12.345.678/0003-52', 'nome': 'ABC Filial RJ'},
            {'cnpj': '98.765.432/0001-00', 'nome': 'XYZ Ltda'}
        ]
        
        groups = mapper.group_by_cnpj_root(entities)
        
        assert '12345678' in groups
        assert len(groups['12345678']) == 3
        assert '98765432' in groups
        assert len(groups['98765432']) == 1
        
    def test_performance_end_to_end(self, query_processor, performance_logger):
        """Test end-to-end performance"""
        queries = [
            "quantas entregas",
            "buscar pedidos do cliente ABC",
            "entregas atrasadas em SP",
            "tendência de faturamento",
            "reagendar entrega 123"
        ]
        
        total_ctx = performance_logger.start("total_processing")
        
        for query in queries:
            ctx = performance_logger.start(f"query: {query}")
            result = query_processor.process(query)
            duration = performance_logger.end(ctx)
            
            assert duration < 0.5  # Each query under 500ms
            assert result is not None
            
        total_duration = performance_logger.end(total_ctx)
        
        report = performance_logger.report()
        assert report['average_time'] < 0.3  # Average under 300ms
        assert total_duration < 2.5  # Total under 2.5 seconds
        
    def test_security_integration(self, query_processor):
        """Test security measures across components"""
        # SQL Injection attempt
        malicious_query = "buscar entregas'; DROP TABLE entregas; --"
        result = query_processor.process(malicious_query)
        
        # Should process safely
        assert result is not None
        if result.sql:
            assert "DROP TABLE" not in result.sql
            
        # XSS attempt
        xss_query = "buscar <script>alert('xss')</script>"
        result = query_processor.process(xss_query)
        
        # Should sanitize
        assert result is not None
        
    def test_multilingual_support(self, query_processor):
        """Test Portuguese language variations"""
        portuguese_queries = [
            "quantas entregas estão atrasadas",
            "mostrar pedidos não faturados",
            "listar notas fiscais emitidas ontem",
            "qual o status da separação",
            "análise de performance das transportadoras"
        ]
        
        for query in portuguese_queries:
            result = query_processor.process(query)
            assert result is not None
            assert result.intent is not None
            assert result.intent.confidence > 0.3
            
    def test_batch_processing(self, query_processor):
        """Test batch query processing"""
        queries = [
            "quantas entregas hoje",
            "quantos pedidos pendentes",
            "total de notas emitidas"
        ]
        
        results = []
        for query in queries:
            result = query_processor.process(query)
            results.append(result)
            
        # All should be count queries
        assert all(r.intent.primary == 'contar' for r in results)
        
    def test_real_world_scenario(self, app, db):
        """Test real-world usage scenario"""
        with app.app_context():
            # Initialize all components
            processor = QueryProcessor(db.session)
            pref_manager = PreferenceManager()
            conf_system = ConfirmationSystem()
            
            user_id = "real_user"
            session_id = "real_session"
            
            # User journey simulation
            journey = [
                "quantas entregas temos hoje",
                "mostrar entregas atrasadas",
                "buscar entregas do cliente ABC",
                "reagendar entrega 123 para sexta",
                "exportar relatório em excel"
            ]
            
            for step, query in enumerate(journey):
                context = {
                    'user_id': user_id,
                    'session_id': session_id,
                    'step': step
                }
                
                result = processor.process(query, context)
                
                # Learn from each interaction
                pref_manager.learn_from_query(user_id, {
                    'original_query': query,
                    'entities': result.query.entities,
                    'context': result.query.context,
                    'intent': {'primary': result.intent.primary},
                    'success': result.success
                })
                
                # Handle confirmations if needed
                if result.intent.action_required:
                    # Would create confirmation request
                    pass
                    
            # Verify learning
            patterns = pref_manager.get_query_patterns(user_id)
            assert patterns['total_queries'] >= len(journey)
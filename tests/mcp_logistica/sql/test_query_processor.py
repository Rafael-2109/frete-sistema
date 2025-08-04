"""
Tests for Query Processor and SQL Generation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date, datetime
from app.mcp_logistica.query_processor import QueryProcessor, QueryResult
from app.mcp_logistica.intent_classifier import Intent


class TestQueryProcessor:
    """Test query processing and SQL generation"""
    
    def test_initialization(self, query_processor):
        """Test query processor initialization"""
        assert query_processor is not None
        assert hasattr(query_processor, 'nlp_engine')
        assert hasattr(query_processor, 'entity_mapper')
        assert hasattr(query_processor, 'intent_classifier')
        assert hasattr(query_processor, 'query_builders')
        
    def test_process_simple_query(self, query_processor):
        """Test processing simple queries"""
        query = "quantas entregas temos?"
        result = query_processor.process(query)
        
        assert isinstance(result, QueryResult)
        assert result.query is not None
        assert result.intent is not None
        assert result.sql is not None
        
    def test_process_with_user_context(self, query_processor, test_context):
        """Test processing with user context"""
        query = "mostrar minhas entregas"
        result = query_processor.process(query, test_context)
        
        assert result.metadata is not None
        assert 'timestamp' in result.metadata
        
    def test_invalid_intent_handling(self, query_processor):
        """Test handling of queries with missing requirements"""
        # Query without required entity
        query = "mostrar entregas"  # Missing which client/entity
        result = query_processor.process(query)
        
        if not result.success:
            assert result.error is not None
            assert len(result.suggestions) > 0
            
    def test_resolve_entities(self, query_processor):
        """Test entity resolution"""
        entities = {
            'nomes_proprios': ['ABC Transportes'],
            'cnpj': '12.345.678/0001-90',
            'nf': '12345',
            'temporal': {'value': date.today(), 'type': 'date'}
        }
        
        resolved = query_processor._resolve_entities(entities)
        
        assert 'cnpj' in resolved
        assert 'cnpj_root' in resolved
        assert resolved['cnpj_root'] == '12345678'
        assert 'nf' in resolved
        assert 'temporal' in resolved
        
    def test_build_entregas_query(self, query_processor, mock_db_session):
        """Test building queries for entregas domain"""
        query_processor.db_session = mock_db_session
        intent = Intent(primary="buscar", confidence=0.8)
        entities = {
            'clientes': [{
                'tipo': 'exato',
                'entidade': Mock(cliente='ABC Ltda')
            }],
            'uf': 'SP',
            'temporal': {
                'value': date.today(),
                'type': 'date'
            }
        }
        context = {'domain': 'entregas'}
        
        query_obj, sql = query_processor._build_entregas_query(intent, entities, context)
        
        assert sql is not None
        assert "SELECT * FROM entregas_monitoradas" in sql
        assert "WHERE" in sql
        assert "cliente = 'ABC Ltda'" in sql
        assert "uf = 'SP'" in sql
        
    def test_build_entregas_query_atraso(self, query_processor, mock_db_session):
        """Test building delay queries"""
        query_processor.db_session = mock_db_session
        intent = Intent(primary="atraso", confidence=0.9)
        entities = {}
        context = {'domain': 'entregas'}
        
        query_obj, sql = query_processor._build_entregas_query(intent, entities, context)
        
        assert "data_entrega_prevista < CURRENT_DATE" in sql
        assert "entregue = FALSE" in sql
        
    def test_build_pedidos_query(self, query_processor, mock_db_session):
        """Test building queries for pedidos domain"""
        query_processor.db_session = mock_db_session
        intent = Intent(primary="buscar", confidence=0.8)
        entities = {
            'pedido': 'PED-001'
        }
        context = {'domain': 'pedidos'}
        
        query_obj, sql = query_processor._build_pedidos_query(intent, entities, context)
        
        assert "SELECT * FROM pedidos" in sql
        assert "num_pedido = 'PED-001'" in sql
        
    def test_execute_count_query(self, query_processor, mock_db_session):
        """Test count query execution"""
        mock_db_session.query.return_value.count.return_value = 42
        query_processor.db_session = mock_db_session
        
        intent = Intent(primary="contar", confidence=0.9)
        entities = {}
        context = {'domain': 'entregas'}
        
        sql, data = query_processor._execute_query(intent, entities, context)
        
        assert data == 42
        
    def test_execute_list_query(self, query_processor, mock_db_session):
        """Test list query execution"""
        mock_results = [Mock(id=1), Mock(id=2), Mock(id=3)]
        mock_db_session.query.return_value.limit.return_value.all.return_value = mock_results
        query_processor.db_session = mock_db_session
        
        intent = Intent(primary="listar", confidence=0.8)
        entities = {}
        context = {'domain': 'entregas'}
        
        sql, data = query_processor._execute_query(intent, entities, context)
        
        assert isinstance(data, list)
        assert len(data) == 3
        
    def test_execute_status_query(self, query_processor, mock_db_session):
        """Test status query execution"""
        mock_result = Mock(numero_nf='12345', status='em_transito')
        mock_db_session.query.return_value.first.return_value = mock_result
        query_processor.db_session = mock_db_session
        
        intent = Intent(primary="status", confidence=0.9)
        entities = {'nf': '12345'}
        context = {'domain': 'entregas'}
        
        sql, data = query_processor._execute_query(intent, entities, context)
        
        assert data is not None
        
    def test_execute_trend_query(self, query_processor, mock_db_session):
        """Test trend query execution"""
        mock_db_session.query.return_value.filter.return_value.count.return_value = 10
        query_processor.db_session = mock_db_session
        
        intent = Intent(primary="tendencia", confidence=0.8)
        entities = {}
        context = {'domain': 'entregas'}
        
        sql, data = query_processor._execute_query(intent, entities, context)
        
        assert isinstance(data, list)
        assert len(data) == 4  # 4 weeks by default
        assert all('periodo' in item for item in data)
        assert all('quantidade' in item for item in data)
        
    def test_serialize_results(self, query_processor):
        """Test result serialization"""
        # Mock SQLAlchemy objects
        mock_results = []
        for i in range(3):
            obj = Mock()
            obj.__dict__ = {
                'id': i,
                'data_entrega': date.today(),
                'valor': 100.50,
                '_sa_instance_state': 'internal'  # Should be filtered
            }
            mock_results.append(obj)
            
        serialized = query_processor._serialize_results(mock_results)
        
        assert len(serialized) == 3
        assert all('_sa_instance_state' not in item for item in serialized)
        assert all(isinstance(item['data_entrega'], str) for item in serialized)
        
    def test_post_process_count_results(self, query_processor):
        """Test post-processing of count results"""
        intent = Intent(primary="contar", confidence=0.9)
        data = 42
        
        processed = query_processor._post_process_results(data, intent, {})
        
        assert 'total' in processed
        assert processed['total'] == 42
        assert 'contexto' in processed
        
    def test_post_process_list_results(self, query_processor):
        """Test post-processing of list results"""
        intent = Intent(primary="listar", confidence=0.8)
        data = [{'id': 1}, {'id': 2}, {'id': 3}]
        
        processed = query_processor._post_process_results(data, intent, {})
        
        assert 'items' in processed
        assert 'total' in processed
        assert 'resumo' in processed
        assert processed['total'] == 3
        
    def test_generate_clarification_suggestions(self, query_processor):
        """Test generation of clarification suggestions"""
        intent = Intent(primary="buscar", confidence=0.7)
        missing = ['cliente', 'período']
        
        suggestions = query_processor._generate_clarification_suggestions(intent, missing)
        
        assert len(suggestions) > 0
        assert any("cliente" in sug for sug in suggestions)
        assert any("período" in sug for sug in suggestions)
        
    def test_generate_followup_suggestions(self, query_processor):
        """Test generation of follow-up suggestions"""
        intent = Intent(primary="buscar", confidence=0.8)
        data = {'total': 50, 'items': []}
        
        suggestions = query_processor._generate_followup_suggestions(intent, data)
        
        assert len(suggestions) > 0
        assert any("filtrar" in sug.lower() for sug in suggestions)
        
    def test_prepare_metadata(self, query_processor):
        """Test metadata preparation"""
        from app.mcp_logistica.nlp_engine import ProcessedQuery
        
        processed = ProcessedQuery(
            original_query="test",
            normalized_query="test",
            tokens=["test"],
            intent="buscar",
            confidence=0.8,
            entities={},
            context={'domain': 'entregas', 'urgency': False},
            response_format="table"
        )
        
        intent = Intent(primary="buscar", confidence=0.8)
        entities = {'nf': '123'}
        
        metadata = query_processor._prepare_metadata(processed, intent, entities)
        
        assert 'timestamp' in metadata
        assert metadata['confidence'] == 0.8
        assert metadata['domain'] == 'entregas'
        assert 'nf' in metadata['entities_found']
        
    def test_error_handling(self, query_processor):
        """Test error handling in query processing"""
        # Force an error by passing invalid query
        result = query_processor.process(None)
        
        assert result.success == False
        assert result.error is not None
        
    def test_claude_integration_trigger(self, query_processor):
        """Test when Claude integration should be triggered"""
        # Low confidence should trigger Claude
        with patch.object(query_processor.intent_classifier, 'classify') as mock_classify:
            mock_classify.return_value = Intent(primary="buscar", confidence=0.5)
            
            result = query_processor.process("consulta ambígua")
            
            # Check if Claude would be triggered (if enabled)
            assert result.metadata is not None
            
    def test_complex_query_processing(self, query_processor):
        """Test processing complex queries with multiple entities"""
        query = "Quantas entregas atrasadas da empresa ABC em SP nos últimos 7 dias?"
        result = query_processor.process(query)
        
        assert result.query is not None
        assert result.intent is not None
        
        # Should identify multiple entities
        entities = result.query.entities
        assert any(key in entities for key in ['temporal', 'uf', 'nomes_proprios'])
        
    def test_sql_injection_prevention(self, query_processor):
        """Test SQL injection prevention"""
        # Try query with SQL injection attempt
        query = "buscar entregas'; DROP TABLE entregas; --"
        result = query_processor.process(query)
        
        # Should still process safely
        assert result is not None
        if result.sql:
            assert "DROP TABLE" not in result.sql
            
    def test_performance_query_processing(self, query_processor, performance_logger):
        """Test query processing performance"""
        queries = [
            "quantas entregas",
            "status da NF 12345",
            "entregas atrasadas em SP",
            "tendência últimos 30 dias"
        ]
        
        for query in queries:
            ctx = performance_logger.start(f"process: {query}")
            result = query_processor.process(query)
            duration = performance_logger.end(ctx)
            
            assert duration < 0.2  # 200ms max
            assert result is not None
            
    def test_count_context_generation(self, query_processor):
        """Test context generation for counts"""
        test_cases = [
            (0, "Nenhum item encontrado"),
            (1, "Apenas 1 item encontrado"),
            (5, "Poucos itens (5)"),
            (50, "Quantidade moderada (50)"),
            (500, "Grande quantidade (500)")
        ]
        
        for count, expected_context in test_cases:
            context = query_processor._get_count_context(count)
            assert context == expected_context
            
    def test_list_summary_generation(self, query_processor):
        """Test summary generation for lists"""
        items = [
            {'id': 1, 'valor_nf': 100.0, 'cliente': 'ABC'},
            {'id': 2, 'valor_nf': 200.0, 'cliente': 'XYZ'},
            {'id': 3, 'valor_nf': 300.0, 'cliente': 'ABC'}
        ]
        
        summary = query_processor._generate_list_summary(items)
        
        assert summary['total_itens'] == 3
        assert summary['valor_total'] == 600.0
        assert summary['valor_medio'] == 200.0
        assert 'campos_disponiveis' in summary
        
    def test_trend_calculation(self, query_processor):
        """Test trend calculation"""
        data = [
            {'periodo': 'Semana 1', 'quantidade': 10},
            {'periodo': 'Semana 2', 'quantidade': 15},
            {'periodo': 'Semana 3', 'quantidade': 20},
            {'periodo': 'Semana 4', 'quantidade': 25}
        ]
        
        trend = query_processor._calculate_trend(data)
        assert trend == "crescente"
        
        # Decreasing trend
        data.reverse()
        trend = query_processor._calculate_trend(data)
        assert trend == "decrescente"
"""
Tests for MCPNLPEngine - Natural Language Processing in Portuguese
"""

import pytest
from datetime import date, datetime, timedelta
from app.mcp_logistica.nlp_engine import MCPNLPEngine, ProcessedQuery


class TestNLPEngine:
    """Test NLP engine functionality"""
    
    def test_initialization(self, nlp_engine):
        """Test NLP engine initialization"""
        assert nlp_engine is not None
        assert hasattr(nlp_engine, 'temporal_patterns')
        assert hasattr(nlp_engine, 'entity_patterns')
        assert hasattr(nlp_engine, 'stopwords')
        assert len(nlp_engine.stopwords) > 0
        
    def test_normalize_query(self, nlp_engine):
        """Test query normalization"""
        test_cases = [
            # (input, expected)
            ("MOSTRAR ENTREGAS", "mostrar entregas"),
            ("Listar    pedidos", "listar pedidos"),
            ("São Paulo", "sao paulo"),  # Remove acentos
            ("nf 123", "nota fiscal 123"),  # Expand abbreviations
            ("qtd de produtos", "quantidade de produtos"),
            ("transp ABC", "transportadora abc"),
        ]
        
        for input_query, expected in test_cases:
            result = nlp_engine.normalize_query(input_query)
            assert result == expected
            
    def test_tokenize(self, nlp_engine):
        """Test tokenization with stopword removal"""
        query = "mostrar todas as entregas de São Paulo"
        tokens = nlp_engine.tokenize(query)
        
        assert "mostrar" in tokens
        assert "entregas" in tokens
        assert "são" in tokens
        assert "paulo" in tokens
        
        # Stopwords should be removed
        assert "as" not in tokens
        assert "de" not in tokens
        assert "todas" not in tokens
        
    def test_extract_temporal_entities(self, nlp_engine):
        """Test temporal entity extraction"""
        test_cases = [
            ("entregas de hoje", "today"),
            ("pedidos de ontem", "yesterday"),
            ("agendamento para amanhã", "tomorrow"),
            ("relatório desta semana", "current_week"),
            ("vendas da semana passada", "last_week"),
            ("faturamento deste mês", "current_month"),
            ("análise do mês passado", "last_month"),
            ("últimos 7 dias", "last_7_days"),
            ("data 15/03/2024", date(2024, 3, 15)),
        ]
        
        for query, expected_type in test_cases:
            entities = nlp_engine.extract_entities(query, query.lower())
            
            if expected_type == "today":
                assert entities.get('temporal')['value'] == date.today()
            elif expected_type == "yesterday":
                assert entities.get('temporal')['value'] == date.today() - timedelta(days=1)
            elif expected_type == "tomorrow":
                assert entities.get('temporal')['value'] == date.today() + timedelta(days=1)
            elif expected_type in ["current_week", "last_week", "current_month", "last_month"]:
                assert entities.get('temporal')['value'] == expected_type
            elif expected_type == "last_7_days":
                assert entities.get('temporal')['value'] == 'last_7_days'
            elif isinstance(expected_type, date):
                assert entities.get('temporal')['value'] == expected_type
                
    def test_extract_cnpj_entities(self, nlp_engine):
        """Test CNPJ extraction"""
        test_cases = [
            "empresa 12.345.678/0001-90",
            "CNPJ 12345678000190",
            "cliente 12.345.678/0001-90 São Paulo",
        ]
        
        for query in test_cases:
            entities = nlp_engine.extract_entities(query, query.lower())
            assert 'cnpj' in entities
            assert entities['cnpj'] in ['12.345.678/0001-90', '12345678000190']
            
    def test_extract_nf_entities(self, nlp_engine):
        """Test nota fiscal extraction"""
        test_cases = [
            ("NF 12345", "12345"),
            ("nota fiscal 789", "789"),
            ("NFe: 456", "456"),
            ("NF# 111", "111"),
        ]
        
        for query, expected_nf in test_cases:
            entities = nlp_engine.extract_entities(query, query.lower())
            assert 'nf' in entities
            assert entities['nf'] == expected_nf
            
    def test_extract_location_entities(self, nlp_engine):
        """Test location extraction"""
        test_cases = [
            ("entregas em SP", "SP"),
            ("pedidos de MG", "MG"),
            ("clientes do RJ", "RJ"),
            ("transportadora de São Paulo", "São Paulo"),
        ]
        
        for query, expected_location in test_cases:
            entities = nlp_engine.extract_entities(query, query.lower())
            
            if len(expected_location) == 2:  # UF
                assert 'uf' in entities
                assert entities['uf'] == expected_location
            else:  # City
                assert 'localizacoes' in entities
                locations = entities['localizacoes']
                assert any(loc['valor'] == expected_location for loc in locations)
                
    def test_extract_value_entities(self, nlp_engine):
        """Test value extraction"""
        test_cases = [
            ("valor R$ 1.500,00", "1.500,00"),
            ("frete de R$500", "500"),
            ("total: R$ 10.000,00", "10.000,00"),
        ]
        
        for query, expected_value in test_cases:
            entities = nlp_engine.extract_entities(query, query.lower())
            assert 'valor' in entities
            assert expected_value in entities['valor']
            
    def test_classify_intent_basic(self, nlp_engine):
        """Test basic intent classification"""
        test_cases = [
            ("buscar entregas", "buscar"),
            ("mostrar pedidos", "buscar"),
            ("quantas notas fiscais", "contar"),
            ("total de entregas", "contar"),
            ("status do pedido", "status"),
            ("situação da entrega", "status"),
            ("entregas atrasadas", "atraso"),
            ("pedidos pendentes", "atraso"),
        ]
        
        for query, expected_intent in test_cases:
            normalized = nlp_engine.normalize_query(query)
            tokens = nlp_engine.tokenize(normalized)
            entities = nlp_engine.extract_entities(query, normalized)
            
            intent, confidence = nlp_engine.classify_intent(normalized, tokens, entities)
            assert intent == expected_intent
            assert confidence > 0.3  # Should have some confidence
            
    def test_classify_intent_with_confidence(self, nlp_engine):
        """Test intent classification confidence levels"""
        # High confidence query
        high_conf_query = "quantas entregas atrasadas temos"
        normalized = nlp_engine.normalize_query(high_conf_query)
        tokens = nlp_engine.tokenize(normalized)
        entities = nlp_engine.extract_entities(high_conf_query, normalized)
        
        intent, confidence = nlp_engine.classify_intent(normalized, tokens, entities)
        assert confidence > 0.6  # Should have high confidence
        
        # Low confidence query
        low_conf_query = "verificar situação"
        normalized = nlp_engine.normalize_query(low_conf_query)
        tokens = nlp_engine.tokenize(normalized)
        entities = nlp_engine.extract_entities(low_conf_query, normalized)
        
        intent, confidence = nlp_engine.classify_intent(normalized, tokens, entities)
        assert confidence < 0.7  # Should have lower confidence
        
    def test_analyze_context(self, nlp_engine):
        """Test context analysis"""
        test_cases = [
            ("entregas urgentes hoje", {"urgency": True, "domain": "entregas"}),
            ("frete da transportadora ABC", {"urgency": False, "domain": "fretes"}),
            ("pedidos de compra", {"urgency": False, "domain": "pedidos"}),
            ("embarque imediato", {"urgency": True, "domain": "embarques"}),
        ]
        
        for query, expected_context in test_cases:
            entities = nlp_engine.extract_entities(query, query.lower())
            context = nlp_engine.analyze_context(query, entities, None)
            
            assert context['urgency'] == expected_context['urgency']
            assert context['domain'] == expected_context['domain']
            assert 'timestamp' in context
            assert 'query_length' in context
            
    def test_process_query_complete(self, nlp_engine):
        """Test complete query processing"""
        query = "Quantas entregas atrasadas temos em São Paulo hoje?"
        result = nlp_engine.process_query(query)
        
        assert isinstance(result, ProcessedQuery)
        assert result.original_query == query
        assert result.normalized_query == "quantas entregas atrasadas temos em sao paulo hoje?"
        assert len(result.tokens) > 0
        assert result.intent in ["contar", "atraso"]
        assert result.confidence > 0
        assert 'temporal' in result.entities
        assert 'uf' in result.entities or 'localizacoes' in result.entities
        assert result.context['domain'] == 'entregas'
        assert result.response_format in ["single_value", "alert_list"]
        
    def test_generate_sql_basic(self, nlp_engine):
        """Test basic SQL generation"""
        # Count query
        query = "quantas entregas"
        processed = nlp_engine.process_query(query)
        sql = processed.sql_query
        
        assert sql is not None
        assert "SELECT COUNT(*)" in sql
        assert "FROM entregas_monitoradas" in sql
        
        # Search query with entity
        query = "buscar pedidos do cliente ABC"
        processed = nlp_engine.process_query(query)
        sql = processed.sql_query
        
        assert sql is not None
        assert "SELECT *" in sql
        assert "WHERE" in sql
        assert "ILIKE" in sql
        
    def test_generate_sql_with_conditions(self, nlp_engine):
        """Test SQL generation with conditions"""
        # Temporal condition
        query = "entregas de hoje"
        processed = nlp_engine.process_query(query)
        sql = processed.sql_query
        
        assert sql is not None
        assert "DATE(criado_em)" in sql or "data_entrega_prevista" in sql
        
        # Location condition
        query = "pedidos em SP"
        processed = nlp_engine.process_query(query)
        sql = processed.sql_query
        
        assert sql is not None
        assert "uf = 'SP'" in sql
        
        # Delay condition
        query = "entregas atrasadas"
        processed = nlp_engine.process_query(query)
        sql = processed.sql_query
        
        assert sql is not None
        assert "data_entrega_prevista < CURRENT_DATE" in sql
        assert "entregue = FALSE" in sql
        
    def test_determine_response_format(self, nlp_engine):
        """Test response format determination"""
        test_cases = [
            ("contar entregas", "single_value"),
            ("status do pedido", "card"),
            ("buscar clientes", "table"),
            ("tendência de vendas", "chart"),
            ("listar atrasos", "alert_list"),
            ("reagendar entrega", "confirmation_dialog"),
        ]
        
        for query, expected_format in test_cases:
            processed = nlp_engine.process_query(query)
            assert processed.response_format == expected_format
            
    def test_generate_suggestions(self, nlp_engine):
        """Test suggestion generation"""
        # Status query with entity
        query = "status da entrega do cliente ABC"
        processed = nlp_engine.process_query(query)
        
        assert len(processed.suggestions) > 0
        assert any("ABC" in sug for sug in processed.suggestions)
        
        # Delay query
        query = "entregas atrasadas"
        processed = nlp_engine.process_query(query)
        
        assert len(processed.suggestions) > 0
        assert any("transportadora" in sug.lower() for sug in processed.suggestions)
        
    def test_learn_from_feedback(self, nlp_engine):
        """Test learning from user feedback"""
        query = "verificar situação"
        processed = nlp_engine.process_query(query)
        query_id = str(id(processed))
        
        # Provide feedback
        feedback = {
            'correct_intent': False,
            'actual_intent': 'status'
        }
        
        nlp_engine.learn_from_feedback(query_id, feedback)
        
        # Verify it was recorded in history
        assert len(nlp_engine.query_history) > 0
        
    def test_edge_cases(self, nlp_engine):
        """Test edge cases and error handling"""
        # Empty query
        result = nlp_engine.process_query("")
        assert result.intent == "buscar"  # Default intent
        
        # Very long query
        long_query = " ".join(["palavra"] * 100)
        result = nlp_engine.process_query(long_query)
        assert result is not None
        
        # Special characters
        special_query = "buscar @#$% entregas!!!"
        result = nlp_engine.process_query(special_query)
        assert result is not None
        assert "buscar" in result.normalized_query
        assert "entregas" in result.normalized_query
        
    def test_performance(self, nlp_engine, performance_logger):
        """Test NLP engine performance"""
        queries = [
            "quantas entregas atrasadas em SP",
            "status da NF 12345 do cliente ABC",
            "tendência de faturamento últimos 30 dias",
            "reagendar entrega para amanhã",
        ]
        
        for query in queries:
            ctx = performance_logger.start(f"process_query: {query}")
            result = nlp_engine.process_query(query)
            duration = performance_logger.end(ctx)
            
            # Should process in reasonable time
            assert duration < 0.1  # 100ms max
            assert result is not None
            
        report = performance_logger.report()
        assert report['average_time'] < 0.05  # 50ms average
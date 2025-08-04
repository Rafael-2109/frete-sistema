"""
Tests for Intent Classification System
"""

import pytest
from app.mcp_logistica.intent_classifier import IntentClassifier, Intent, ActionType


class TestIntentClassifier:
    """Test intent classification functionality"""
    
    def test_initialization(self, intent_classifier):
        """Test intent classifier initialization"""
        assert intent_classifier is not None
        assert hasattr(intent_classifier, 'intent_patterns')
        assert hasattr(intent_classifier, 'intent_hierarchy')
        assert hasattr(intent_classifier, 'compatible_intents')
        
    def test_intent_patterns_structure(self, intent_classifier):
        """Test intent patterns are properly structured"""
        for intent_name, config in intent_classifier.intent_patterns.items():
            assert 'patterns' in config
            assert 'keywords' in config
            assert isinstance(config['patterns'], list)
            assert isinstance(config['keywords'], list)
            assert len(config['patterns']) > 0
            assert len(config['keywords']) > 0
            
    def test_classify_search_intents(self, intent_classifier):
        """Test classification of search/query intents"""
        test_cases = [
            ("buscar entregas do cliente", "buscar"),
            ("procurar pedidos", "buscar"),
            ("encontrar notas fiscais", "buscar"),
            ("mostrar todos os fretes", "buscar"),
            ("listar transportadoras", "buscar"),
            ("consultar embarques", "buscar"),
        ]
        
        for query, expected_intent in test_cases:
            result = intent_classifier.classify(query)
            assert result.primary == expected_intent
            assert result.confidence > 0
            
    def test_classify_status_intents(self, intent_classifier):
        """Test classification of status intents"""
        test_cases = [
            ("qual o status da entrega", "status"),
            ("situação do pedido 123", "status"),
            ("como está a NF 456", "status"),
            ("onde está minha carga", "status"),
            ("posição do embarque", "status"),
            ("andamento da separação", "status"),
        ]
        
        for query, expected_intent in test_cases:
            result = intent_classifier.classify(query)
            assert result.primary == expected_intent
            
    def test_classify_count_intents(self, intent_classifier):
        """Test classification of counting intents"""
        test_cases = [
            ("quantas entregas hoje", "contar"),
            ("quantos pedidos pendentes", "contar"),
            ("quantidade de notas fiscais", "contar"),
            ("total de fretes", "contar"),
            ("número de atrasos", "contar"),
            ("somar valores", "contar"),
        ]
        
        for query, expected_intent in test_cases:
            result = intent_classifier.classify(query)
            assert result.primary == expected_intent
            
    def test_classify_trend_intents(self, intent_classifier):
        """Test classification of trend/analysis intents"""
        test_cases = [
            ("tendência de entregas", "tendencia"),
            ("evolução das vendas", "tendencia"),
            ("crescimento do faturamento", "tendencia"),
            ("queda nas entregas", "tendencia"),
            ("variação mensal", "tendencia"),
            ("comparar com ano passado", "tendencia"),
        ]
        
        for query, expected_intent in test_cases:
            result = intent_classifier.classify(query)
            assert result.primary == expected_intent
            
    def test_classify_problem_intents(self, intent_classifier):
        """Test classification of problem/alert intents"""
        test_cases = [
            ("entregas atrasadas", "atraso"),
            ("pedidos pendentes há muito tempo", "atraso"),
            ("notas vencidas", "atraso"),
            ("fora do prazo", "atraso"),
            ("não foi entregue", "atraso"),
        ]
        
        for query, expected_intent in test_cases:
            result = intent_classifier.classify(query)
            assert result.primary == expected_intent
            
    def test_classify_action_intents(self, intent_classifier):
        """Test classification of action intents requiring confirmation"""
        test_cases = [
            ("reagendar entrega para amanhã", "reagendar"),
            ("remarcar data de coleta", "reagendar"),
            ("alterar data de entrega", "reagendar"),
            ("cancelar pedido", "cancelar"),
            ("desistir da compra", "cancelar"),
            ("aprovar liberação", "aprovar"),
            ("autorizar despacho", "aprovar"),
        ]
        
        for query, expected_intent in test_cases:
            result = intent_classifier.classify(query)
            assert result.primary == expected_intent
            assert result.action_required == True
            
    def test_classify_with_entities(self, intent_classifier):
        """Test classification considering entities"""
        # Query with NF entity
        entities = {'nf': '12345'}
        result = intent_classifier.classify("verificar 12345", entities)
        assert result.primary == "status"  # Should boost status intent
        
        # Query with temporal entity
        entities = {'temporal': {'value': 'today', 'type': 'date'}}
        result = intent_classifier.classify("análise de vendas", entities)
        assert result.confidence > 0  # Should consider temporal for trend
        
    def test_secondary_intent_detection(self, intent_classifier):
        """Test detection of secondary intents"""
        # Compatible intents
        query = "buscar entregas atrasadas e exportar para excel"
        result = intent_classifier.classify(query)
        
        # Should detect both buscar and exportar
        assert result.primary in ["buscar", "exportar"]
        if result.secondary:
            assert result.secondary in ["buscar", "exportar"]
            
    def test_intent_parameters_extraction(self, intent_classifier):
        """Test extraction of intent-specific parameters"""
        # Reschedule intent
        entities = {'temporal': {'value': '2024-12-25', 'type': 'date'}}
        result = intent_classifier.classify("reagendar para 25/12", entities)
        
        assert result.primary == "reagendar"
        assert 'nova_data' in result.parameters
        assert result.parameters['nova_data'] == '2024-12-25'
        
        # Export intent
        result = intent_classifier.classify("exportar relatório em excel")
        assert result.primary == "exportar"
        assert result.parameters.get('formato') == 'excel'
        
        # Ranking intent
        result = intent_classifier.classify("top 10 maiores clientes")
        assert result.primary == "ranking"
        assert result.parameters.get('limite') == 10
        assert result.parameters.get('ordem') == 'desc'
        
    def test_intent_category_classification(self, intent_classifier):
        """Test intent category classification"""
        test_cases = [
            ("buscar", "consulta"),
            ("status", "consulta"),
            ("tendencia", "analise"),
            ("ranking", "analise"),
            ("atraso", "alerta"),
            ("falha", "alerta"),
            ("reagendar", "acao"),
            ("cancelar", "acao"),
            ("exportar", "relatorio"),
        ]
        
        for intent, expected_category in test_cases:
            category = intent_classifier.get_intent_category(intent)
            assert category == expected_category
            
    def test_followup_suggestions(self, intent_classifier):
        """Test follow-up intent suggestions"""
        # After search
        suggestions = intent_classifier.suggest_followup_intents("buscar")
        assert "status" in suggestions
        assert "exportar" in suggestions
        
        # After delay detection
        suggestions = intent_classifier.suggest_followup_intents("atraso")
        assert "reagendar" in suggestions
        assert "listar" in suggestions
        
        # After counting
        suggestions = intent_classifier.suggest_followup_intents("contar")
        assert "listar" in suggestions
        assert "tendencia" in suggestions
        
    def test_validate_intent_requirements(self, intent_classifier):
        """Test validation of intent requirements"""
        # Valid search with entity
        intent = Intent(primary="buscar", confidence=0.8)
        entities = {'nomes_proprios': ['Cliente ABC']}
        is_valid, missing = intent_classifier.validate_intent_requirements(intent, entities, {})
        assert is_valid == True
        assert len(missing) == 0
        
        # Invalid search without entity
        intent = Intent(primary="buscar", confidence=0.8)
        entities = {}
        is_valid, missing = intent_classifier.validate_intent_requirements(intent, entities, {})
        assert is_valid == False
        assert len(missing) > 0
        assert any("entidade" in m for m in missing)
        
        # Invalid trend without temporal
        intent = Intent(primary="tendencia", confidence=0.8)
        entities = {}
        is_valid, missing = intent_classifier.validate_intent_requirements(intent, entities, {})
        assert is_valid == False
        assert any("período" in m or "data" in m for m in missing)
        
        # Valid reschedule with new date
        intent = Intent(primary="reagendar", confidence=0.9)
        intent.parameters = {'nova_data': '2024-12-25'}
        entities = {}
        is_valid, missing = intent_classifier.validate_intent_requirements(intent, entities, {})
        assert is_valid == True
        
    def test_confidence_calculation(self, intent_classifier):
        """Test confidence score calculation"""
        # High confidence - multiple keywords
        query = "buscar todas as entregas mostrar listar"
        result = intent_classifier.classify(query)
        assert result.confidence > 0.7
        
        # Medium confidence - single keyword
        query = "entregas"
        result = intent_classifier.classify(query)
        assert 0.3 <= result.confidence <= 0.7
        
        # Low confidence - ambiguous
        query = "verificar"
        result = intent_classifier.classify(query)
        assert result.confidence < 0.7
        
    def test_complex_queries(self, intent_classifier):
        """Test classification of complex queries"""
        # Multiple intents
        query = "mostrar entregas atrasadas e calcular multa por atraso"
        result = intent_classifier.classify(query)
        assert result.primary in ["buscar", "atraso", "contar"]
        
        # Action with context
        query = "cancelar pedido 123 por falta de pagamento"
        entities = {'pedido': '123'}
        result = intent_classifier.classify(query, entities)
        assert result.primary == "cancelar"
        assert result.action_required == True
        
    def test_email_extraction(self, intent_classifier):
        """Test email extraction from export intent"""
        query = "exportar relatório e enviar para user@example.com"
        result = intent_classifier.classify(query)
        
        assert result.primary == "exportar"
        if 'email' in result.parameters:
            assert result.parameters['email'] == 'user@example.com'
            
    def test_intent_compatibility(self, intent_classifier):
        """Test intent compatibility rules"""
        # Check compatible intents
        assert "exportar" in intent_classifier.compatible_intents.get("buscar", [])
        assert "exportar" in intent_classifier.compatible_intents.get("status", [])
        assert "tendencia" in intent_classifier.compatible_intents.get("contar", [])
        
    def test_edge_cases(self, intent_classifier):
        """Test edge cases"""
        # Empty query
        result = intent_classifier.classify("")
        assert result.primary == "buscar"  # Default
        assert result.confidence == 0.3
        
        # Query with only stopwords
        result = intent_classifier.classify("a de para com")
        assert result.primary == "buscar"
        assert result.confidence == 0.3
        
        # Very long query
        long_query = " ".join(["palavra"] * 100)
        result = intent_classifier.classify(long_query)
        assert result is not None
        
    def test_action_type_requirements(self, intent_classifier):
        """Test specific action type requirements"""
        # Reschedule without new date
        intent = Intent(primary="reagendar", confidence=0.9, action_required=True)
        entities = {}
        is_valid, missing = intent_classifier.validate_intent_requirements(intent, entities, {})
        assert is_valid == False
        assert any("nova data" in m for m in missing)
        
        # Approve without document type
        intent = Intent(primary="aprovar", confidence=0.9, action_required=True)
        entities = {}
        is_valid, missing = intent_classifier.validate_intent_requirements(intent, entities, {})
        assert is_valid == True  # Should still be valid without specific doc
        
    def test_performance(self, intent_classifier, performance_logger):
        """Test classification performance"""
        queries = [
            "buscar entregas",
            "quantas notas fiscais atrasadas",
            "reagendar entrega para amanhã",
            "tendência de faturamento mensal",
            "exportar relatório em excel",
        ]
        
        for query in queries:
            ctx = performance_logger.start(f"classify: {query}")
            result = intent_classifier.classify(query)
            duration = performance_logger.end(ctx)
            
            assert duration < 0.01  # Should be very fast (< 10ms)
            assert result is not None
            
        report = performance_logger.report()
        assert report['average_time'] < 0.005  # 5ms average
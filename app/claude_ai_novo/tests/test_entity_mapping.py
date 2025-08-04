"""
Unit tests for entity_mapping module
Tests dynamic pattern recognition and entity mapping capabilities
"""

import unittest
from datetime import datetime, timedelta
from app.claude_ai_novo.entity_mapping import (
    EntityMapper, EntityPatternAnalyzer,
    create_entity_mapper, analyze_entities, discover_rules, group_clients_by_company
)


class TestEntityMapper(unittest.TestCase):
    """Test EntityMapper functionality"""
    
    def setUp(self):
        self.mapper = EntityMapper()
    
    def test_extract_cnpj_root(self):
        """Test CNPJ root extraction"""
        # Test various CNPJ formats
        test_cases = [
            ("11.222.333/0001-44", "11222333"),
            ("11222333000144", "11222333"),
            ("11.222.333/0002-55", "11222333"),  # Same root, different branch
            ("99888777000166", "99888777"),
            ("invalid", None),
            ("", None),
            (None, None),
        ]
        
        for cnpj, expected_root in test_cases:
            result = self.mapper.extract_cnpj_root(cnpj)
            self.assertEqual(result, expected_root, f"Failed for CNPJ: {cnpj}")
    
    def test_normalize_client_name(self):
        """Test client name normalization"""
        test_cases = [
            ("ABC Ltda.", "ABC LIMITADA"),
            ("XYZ S.A.", "XYZ SOCIEDADE ANONIMA"),
            ("Comércio e Ind. Beta", "COMERCIO E INDUSTRIA BETA"),
            ("José & Cia", "JOSE & COMPANHIA"),
            ("  empresa   teste  ", "EMPRESA TESTE"),
            ("Açúcar Cristal Ltda", "ACUCAR CRISTAL LIMITADA"),
        ]
        
        for original, expected in test_cases:
            result = self.mapper.normalize_client_name(original)
            self.assertEqual(result, expected, f"Failed for name: {original}")
    
    def test_calculate_name_similarity(self):
        """Test name similarity calculation"""
        test_cases = [
            ("ABC LTDA", "ABC Limitada", 1.0),  # Same after normalization
            ("XYZ Comercio", "XYZ Com.", 1.0),  # Same after abbreviation expansion
            ("Alpha Beta", "Beta Alpha", 0.5),  # Different order
            ("Company A", "Company B", 0.8),  # High similarity
            ("ABC", "XYZ", 0.0),  # No similarity
        ]
        
        for name1, name2, min_expected in test_cases:
            result = self.mapper.calculate_name_similarity(name1, name2)
            self.assertGreaterEqual(result, min_expected - 0.1, 
                                  f"Similarity too low for {name1} vs {name2}")
    
    def test_group_by_cnpj_root(self):
        """Test grouping by CNPJ root"""
        entities = [
            {'id': 1, 'cnpj': '11.222.333/0001-44', 'name': 'Company A Branch 1'},
            {'id': 2, 'cnpj': '11.222.333/0002-55', 'name': 'Company A Branch 2'},
            {'id': 3, 'cnpj': '99.888.777/0001-66', 'name': 'Company B'},
            {'id': 4, 'cnpj': 'invalid_cnpj', 'name': 'Invalid'},
            {'id': 5, 'name': 'No CNPJ'},
        ]
        
        groups = self.mapper.group_by_cnpj_root(entities)
        
        self.assertIn('11222333', groups)
        self.assertEqual(len(groups['11222333']), 2)
        self.assertIn('99888777', groups)
        self.assertEqual(len(groups['99888777']), 1)
        self.assertIn('invalid', groups)
        self.assertIn('missing', groups)
    
    def test_find_similar_clients(self):
        """Test finding similar client names"""
        all_clients = [
            "ABC LIMITADA",
            "ABC LTDA",
            "ABC COMERCIO LTDA",
            "XYZ INDUSTRIA",
            "BETA TRANSPORTES"
        ]
        
        similar = self.mapper.find_similar_clients("ABC Ltd.", all_clients, threshold=0.7)
        
        self.assertTrue(len(similar) >= 2)
        self.assertEqual(similar[0][0], "ABC LIMITADA")  # Best match
        self.assertGreater(similar[0][1], 0.8)  # High similarity
    
    def test_normalize_location(self):
        """Test location normalization"""
        test_cases = [
            ("São Paulo", "SP", "SAO PAULO", "SP", False),
            ("Rio de Janeiro", "RJ", "RIO JANEIRO", "RJ", False),
            ("Belo Horizonte", "MG", "BELO HORIZONTE", "MG", False),
            ("City", "State", "CITY", "ST", True),  # Invalid state
        ]
        
        for city, state, exp_city, exp_state, exp_validation in test_cases:
            result = self.mapper.normalize_location(city, state)
            self.assertEqual(result['city_normalized'], exp_city)
            self.assertEqual(result['state_normalized'], exp_state)
            self.assertEqual(result['needs_validation'], exp_validation)
    
    def test_harmonize_status(self):
        """Test status harmonization"""
        test_cases = [
            ("ABERTO", "order", "open"),
            ("Pendente", "general", "open"),
            ("EMBARCADO", "freight", "shipped"),
            ("Entregue", "delivery", "delivered"),
            ("CANCELADO", "order", "cancelled"),
            ("NF no CD", "delivery", "warehouse"),
            ("COTADO", "freight", "quoted"),
            ("Unknown Status", "general", "unknown status"),
        ]
        
        for status, context, expected in test_cases:
            result = self.mapper.harmonize_status(status, context)
            self.assertEqual(result, expected, f"Failed for status: {status} in context: {context}")
    
    def test_extract_temporal_fields(self):
        """Test temporal field extraction"""
        entity = {
            'id': 1,
            'criado_em': datetime.now(),
            'updated_at': datetime.now(),
            'data_entrega': datetime.now() + timedelta(days=5),
            'vencimento': datetime.now() + timedelta(days=30),
            'agendamento': datetime.now() + timedelta(days=2),
            'nome': 'Test Entity',
            'valor': 100.0,
        }
        
        temporal_fields = self.mapper.extract_temporal_fields(entity)
        
        self.assertIn('creation', temporal_fields)
        self.assertIn('criado_em', temporal_fields['creation'])
        self.assertIn('update', temporal_fields)
        self.assertIn('updated_at', temporal_fields['update'])
        self.assertIn('execution', temporal_fields)
        self.assertIn('data_entrega', temporal_fields['execution'])
        self.assertIn('deadline', temporal_fields)
        self.assertIn('vencimento', temporal_fields['deadline'])
    
    def test_generate_dynamic_query_pattern(self):
        """Test dynamic query pattern generation"""
        filters = {
            'data_inicio': {'start': '2024-01-01', 'end': '2024-01-31'},
            'status': ['ABERTO', 'COTADO'],
            'valor_minimo': {'min': 100.0},
            'valor_maximo': {'max': 1000.0},
            'cliente': '%ABC%',
            'cnpj': '11222333000144',
        }
        
        pattern = self.mapper.generate_dynamic_query_pattern(filters)
        
        self.assertIn('data_inicio', pattern['date_ranges'])
        self.assertIn('ABERTO', pattern['status_filters'])
        self.assertIn('COTADO', pattern['status_filters'])
        self.assertIn('valor_minimo', pattern['numeric_ranges'])
        self.assertIn('valor_maximo', pattern['numeric_ranges'])
        self.assertIn('cliente', pattern['text_searches'])
        self.assertIn('cnpj', pattern['base_filters'])


class TestEntityPatternAnalyzer(unittest.TestCase):
    """Test EntityPatternAnalyzer functionality"""
    
    def setUp(self):
        self.mapper = EntityMapper()
        self.analyzer = EntityPatternAnalyzer(self.mapper)
    
    def test_analyze_entity_patterns(self):
        """Test entity pattern analysis"""
        entities = [
            {
                'id': 1,
                'cnpj': '11.222.333/0001-44',
                'cliente': 'ABC Ltda',
                'status': 'ABERTO',
                'valor': 1000.0,
                'data_pedido': '2024-01-01',
            },
            {
                'id': 2,
                'cnpj': '11.222.333/0002-55',
                'cliente': 'ABC Ltda Filial',
                'status': 'COTADO',
                'valor': 2000.0,
                'data_pedido': '2024-01-02',
            },
            {
                'id': 3,
                'cnpj': '99.888.777/0001-66',
                'cliente': 'XYZ SA',
                'status': 'FATURADO',
                'valor': None,  # Missing value
                'data_pedido': '2024-01-03',
            },
        ]
        
        analysis = self.analyzer.analyze_entity_patterns(entities, 'pedidos')
        
        self.assertEqual(analysis['entity_type'], 'pedidos')
        self.assertEqual(analysis['total_count'], 3)
        self.assertIn('cnpj', analysis['field_patterns'])
        self.assertIn('valor', analysis['field_patterns'])
        
        # Check null percentage calculation
        valor_stats = analysis['field_patterns']['valor']
        self.assertEqual(valor_stats['null_count'], 1)
        self.assertAlmostEqual(valor_stats['null_percentage'], 33.33, places=1)
    
    def test_discover_business_rules(self):
        """Test business rule discovery"""
        entities = [
            # Company A (CNPJ root: 11222333) always uses Transportadora X
            {'cnpj': '11.222.333/0001-44', 'transportadora': 'Trans X', 'status': 'ABERTO'},
            {'cnpj': '11.222.333/0001-44', 'transportadora': 'Trans X', 'status': 'COTADO'},
            {'cnpj': '11.222.333/0002-55', 'transportadora': 'Trans X', 'status': 'FATURADO'},
            {'cnpj': '11.222.333/0002-55', 'transportadora': 'Trans X', 'status': 'ENTREGUE'},
            # Company B uses different transporters
            {'cnpj': '99.888.777/0001-66', 'transportadora': 'Trans Y', 'status': 'ABERTO'},
            {'cnpj': '99.888.777/0001-66', 'transportadora': 'Trans Z', 'status': 'COTADO'},
        ]
        
        rules = self.analyzer.discover_business_rules(entities)
        
        # Should discover CNPJ pattern rule
        cnpj_rules = [r for r in rules if r['type'] == 'cnpj_pattern']
        self.assertTrue(len(cnpj_rules) > 0)
        
        # Check if it found the pattern for company A
        company_a_rules = [r for r in cnpj_rules if '11222333' in r['rule']]
        self.assertTrue(len(company_a_rules) > 0)
        self.assertIn('transportadora', company_a_rules[0]['rule'])


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_create_entity_mapper(self):
        """Test factory function"""
        mapper = create_entity_mapper()
        self.assertIsInstance(mapper, EntityMapper)
    
    def test_analyze_entities(self):
        """Test analyze entities convenience function"""
        entities = [
            {'id': 1, 'name': 'Test 1', 'value': 100},
            {'id': 2, 'name': 'Test 2', 'value': 200},
        ]
        
        analysis = analyze_entities(entities, 'test_entity')
        self.assertEqual(analysis['entity_type'], 'test_entity')
        self.assertEqual(analysis['total_count'], 2)
    
    def test_group_clients_by_company(self):
        """Test group by company convenience function"""
        entities = [
            {'cnpj': '11.222.333/0001-44', 'name': 'Branch 1'},
            {'cnpj': '11.222.333/0002-55', 'name': 'Branch 2'},
            {'cnpj': '99.888.777/0001-66', 'name': 'Other Company'},
        ]
        
        groups = group_clients_by_company(entities)
        self.assertIn('11222333', groups)
        self.assertEqual(len(groups['11222333']), 2)


if __name__ == '__main__':
    unittest.main()
"""
Tests for Entity Mapping System - Dynamic CNPJ-based mapping
"""

import pytest
from unittest.mock import Mock, MagicMock
from app.mcp_logistica.entity_mapper import EntityMapper


class TestEntityMapper:
    """Test entity mapping functionality"""
    
    def test_initialization(self, entity_mapper):
        """Test entity mapper initialization"""
        assert entity_mapper is not None
        assert hasattr(entity_mapper, 'cnpj_pattern')
        assert hasattr(entity_mapper, 'name_cleanup_patterns')
        assert hasattr(entity_mapper, 'ignore_words')
        
    def test_extract_cnpj_root(self, entity_mapper):
        """Test CNPJ root extraction"""
        test_cases = [
            ("12.345.678/0001-90", "12345678"),
            ("12345678000190", "12345678"),
            ("12.345.678/0002-71", "12345678"),  # Different branch
            ("98765432000100", "98765432"),
            ("invalid", None),
            ("", None),
            (None, None),
        ]
        
        for cnpj, expected_root in test_cases:
            result = entity_mapper.extract_cnpj_root(cnpj)
            assert result == expected_root
            
    def test_group_by_cnpj_root(self, entity_mapper):
        """Test grouping entities by CNPJ root"""
        entities = [
            {'cnpj': '12.345.678/0001-90', 'nome': 'Empresa ABC - Matriz'},
            {'cnpj': '12.345.678/0002-71', 'nome': 'Empresa ABC - Filial SP'},
            {'cnpj': '12.345.678/0003-52', 'nome': 'Empresa ABC - Filial RJ'},
            {'cnpj': '98.765.432/0001-00', 'nome': 'Empresa XYZ'},
            {'cnpj': '', 'nome': 'Empresa sem CNPJ'},
        ]
        
        groups = entity_mapper.group_by_cnpj_root(entities)
        
        assert '12345678' in groups
        assert len(groups['12345678']) == 3
        assert '98765432' in groups
        assert len(groups['98765432']) == 1
        assert 'NO_CNPJ' in groups
        assert len(groups['NO_CNPJ']) == 1
        
    def test_normalize_company_name(self, entity_mapper):
        """Test company name normalization"""
        test_cases = [
            ("EMPRESA ABC LTDA", "empresa abc"),
            ("Comercial XYZ S.A.", "xyz"),
            ("Transportes Silva Eireli", "silva"),
            ("Distribuidora Santos ME", "santos"),
            ("Indústria Metal EPP", "metal"),
            ("Logística Express - Filial 01", "express"),
            ("COMERCIO DE PRODUTOS LTDA", "produtos"),
        ]
        
        for original, expected in test_cases:
            result = entity_mapper.normalize_company_name(original)
            assert result == expected
            
    def test_calculate_name_similarity(self, entity_mapper):
        """Test name similarity calculation"""
        test_cases = [
            ("Empresa ABC", "Empresa ABC", 1.0),  # Exact match
            ("Empresa ABC", "ABC Empresa", 0.7),  # Different order
            ("Transportadora Silva", "Silva Transportes", 0.5),  # Partial match
            ("ABC", "XYZ", 0.0),  # No match
            ("", "Empresa", 0.0),  # Empty string
        ]
        
        for name1, name2, min_expected in test_cases:
            result = entity_mapper.calculate_name_similarity(name1, name2)
            assert result >= min_expected
            
    def test_find_similar_entities(self, entity_mapper):
        """Test finding similar entities"""
        candidates = [
            {'nome': 'Empresa ABC Ltda'},
            {'nome': 'ABC Comércio'},
            {'nome': 'Empresa XYZ'},
            {'nome': 'ABC Distribuidora'},
        ]
        
        # Search for ABC
        similar = entity_mapper.find_similar_entities("ABC", candidates, threshold=0.5)
        
        assert len(similar) >= 2  # Should find at least 2 ABC variants
        assert all(score >= 0.5 for _, score in similar)
        assert similar[0][1] >= similar[1][1]  # Should be sorted by score
        
    def test_detect_entity_patterns(self, entity_mapper):
        """Test pattern detection in entities"""
        entities = [
            {
                'cnpj': '12.345.678/0001-90',
                'nome': 'ABC Matriz',
                'cidade': 'São Paulo',
                'uf': 'SP',
                'valor': 1000.00
            },
            {
                'cnpj': '12.345.678/0002-71',
                'nome': 'ABC Filial',
                'cidade': 'Rio de Janeiro',
                'uf': 'RJ',
                'valor': 500.00
            },
            {
                'cnpj': '98.765.432/0001-00',
                'nome': 'XYZ',
                'cidade': 'São Paulo',
                'uf': 'SP',
                'valor': 2000.00
            }
        ]
        
        patterns = entity_mapper.detect_entity_patterns(entities)
        
        assert 'grupos_empresariais' in patterns
        assert '12345678' in patterns['grupos_empresariais']
        assert patterns['grupos_empresariais']['12345678']['filiais'] == 2
        
        assert 'distribuicao_geografica' in patterns
        assert 'SP' in patterns['distribuicao_geografica']
        assert 'RJ' in patterns['distribuicao_geografica']
        
        assert 'padroes_valores' in patterns
        assert patterns['padroes_valores']['valor']['min'] == 500.00
        assert patterns['padroes_valores']['valor']['max'] == 2000.00
        
    def test_resolve_entity_reference_exact(self, entity_mapper, mock_db_session):
        """Test exact entity reference resolution"""
        # Mock query result
        mock_result = Mock()
        mock_result.cliente = "Empresa ABC"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_result
        
        entity_mapper.db_session = mock_db_session
        
        results = entity_mapper.resolve_entity_reference("Empresa ABC", "cliente")
        
        assert len(results) > 0
        assert results[0]['tipo'] == 'exato'
        
    def test_resolve_entity_reference_cnpj(self, entity_mapper, mock_db_session):
        """Test CNPJ-based entity resolution"""
        # Mock CNPJ query results
        mock_results = [
            Mock(cnpj_cliente='12.345.678/0001-90', cliente='ABC Matriz'),
            Mock(cnpj_cliente='12.345.678/0002-71', cliente='ABC Filial'),
        ]
        mock_db_session.query.return_value.filter.return_value.limit.return_value.all.return_value = mock_results
        
        entity_mapper.db_session = mock_db_session
        
        results = entity_mapper.resolve_entity_reference("12.345.678", "cliente")
        
        assert any(r['tipo'] == 'cnpj_parcial' for r in results)
        
    def test_resolve_entity_reference_fuzzy(self, entity_mapper, mock_db_session):
        """Test fuzzy entity resolution"""
        # Mock distinct clients
        mock_clients = [
            ("Empresa ABC Ltda",),
            ("ABC Comércio",),
            ("XYZ Transportes",),
        ]
        mock_db_session.query.return_value.distinct.return_value.limit.return_value.all.return_value = mock_clients
        
        entity_mapper.db_session = mock_db_session
        
        results = entity_mapper.resolve_entity_reference("ABC", "cliente")
        
        fuzzy_results = [r for r in results if r['tipo'] == 'fuzzy']
        assert len(fuzzy_results) > 0
        assert all('score' in r for r in fuzzy_results)
        
    def test_create_entity_mapping_rules(self, entity_mapper, mock_db_session):
        """Test creation of mapping rules from data"""
        # Mock sample data
        mock_data = []
        for i in range(5):
            mock_entity = Mock()
            mock_entity.cnpj_cliente = f'12.345.678/000{i}-00'
            mock_entity.cliente = f'ABC Filial {i}'
            mock_entity.municipio = 'São Paulo'
            mock_entity.uf = 'SP'
            mock_data.append(mock_entity)
            
        mock_db_session.query.return_value.limit.return_value.all.return_value = mock_data
        entity_mapper.db_session = mock_db_session
        
        rules = entity_mapper.create_entity_mapping_rules()
        
        assert 'cnpj_groups' in rules
        assert len(rules['cnpj_groups']) > 0
        
    def test_get_entity_context(self, entity_mapper, mock_db_session):
        """Test getting complete entity context"""
        # Mock resolved entity
        mock_entity = Mock()
        mock_entity.cnpj_cliente = '12.345.678/0001-90'
        mock_entity.cliente = 'ABC Matriz'
        
        # Mock related entities
        mock_related = [
            Mock(cliente='ABC Filial SP', cnpj_cliente='12.345.678/0002-71', municipio='São Paulo', uf='SP'),
            Mock(cliente='ABC Filial RJ', cnpj_cliente='12.345.678/0003-52', municipio='Rio Janeiro', uf='RJ'),
        ]
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_entity
        mock_db_session.query.return_value.filter.return_value.limit.return_value.all.return_value = mock_related
        
        entity_mapper.db_session = mock_db_session
        
        context = entity_mapper.get_entity_context("ABC")
        
        assert 'reference' in context
        assert 'resolved_entities' in context
        assert 'related_entities' in context
        assert 'suggestions' in context
        assert len(context['related_entities']) == 2
        
    def test_special_characters_handling(self, entity_mapper):
        """Test handling of special characters in names"""
        test_cases = [
            "Empresa & Cia",
            "ABC-123 Transportes",
            "XYZ (Brasil)",
            "Comércio @Tech",
        ]
        
        for name in test_cases:
            normalized = entity_mapper.normalize_company_name(name)
            assert normalized is not None
            assert len(normalized) > 0
            
    def test_performance_grouping(self, entity_mapper, performance_logger):
        """Test performance of entity grouping"""
        # Generate large dataset
        entities = []
        for i in range(1000):
            cnpj_base = f"{i//10:08d}"
            entities.append({
                'cnpj': f'{cnpj_base[:2]}.{cnpj_base[2:5]}.{cnpj_base[5:8]}/000{i%10}-00',
                'nome': f'Empresa {i//10} - Filial {i%10}'
            })
            
        ctx = performance_logger.start("group_by_cnpj_root")
        groups = entity_mapper.group_by_cnpj_root(entities)
        duration = performance_logger.end(ctx)
        
        assert len(groups) == 100  # Should have 100 groups
        assert duration < 0.1  # Should be fast even with 1000 entities
        
    def test_similarity_threshold(self, entity_mapper):
        """Test similarity threshold behavior"""
        candidates = [
            {'nome': 'Empresa ABC'},
            {'nome': 'Empresa ABD'},  # One letter different
            {'nome': 'Empresa XYZ'},
        ]
        
        # High threshold
        similar_high = entity_mapper.find_similar_entities("Empresa ABC", candidates, threshold=0.9)
        assert len(similar_high) == 1  # Only exact match
        
        # Low threshold
        similar_low = entity_mapper.find_similar_entities("Empresa ABC", candidates, threshold=0.5)
        assert len(similar_low) >= 2  # Should include ABD
        
    def test_empty_data_handling(self, entity_mapper):
        """Test handling of empty or null data"""
        # Empty entities list
        groups = entity_mapper.group_by_cnpj_root([])
        assert groups == {}
        
        # Entities with missing data
        entities = [
            {'cnpj': None, 'nome': 'Test'},
            {'cnpj': '', 'nome': None},
            {},
        ]
        
        groups = entity_mapper.group_by_cnpj_root(entities)
        assert 'NO_CNPJ' in groups
        assert len(groups['NO_CNPJ']) == 3
        
    def test_pattern_analysis_edge_cases(self, entity_mapper):
        """Test pattern analysis with edge cases"""
        # Single entity
        patterns = entity_mapper.detect_entity_patterns([{'cnpj': '12.345.678/0001-90'}])
        assert patterns is not None
        
        # Entities without values
        entities = [{'nome': 'Test'}, {'nome': 'Test2'}]
        patterns = entity_mapper.detect_entity_patterns(entities)
        assert 'padroes_valores' in patterns
        assert len(patterns['padroes_valores']) == 0
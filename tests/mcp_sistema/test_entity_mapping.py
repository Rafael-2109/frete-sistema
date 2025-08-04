"""
Tests for entity mapping and recognition system
"""
import pytest
from datetime import datetime
from typing import List, Dict, Any

from app.mcp_sistema.models.mcp_models import EntityMapping, QueryLog
from app.mcp_sistema.services.nlp.entity_extractor import EntityExtractor
from app.mcp_sistema.services.nlp.entity_mapper import EntityMapper


class TestEntityMapping:
    """Test suite for entity mapping functionality"""
    
    def test_create_entity_mapping(self, db_session):
        """Test creating a new entity mapping"""
        mapping = EntityMapping(
            entity_type="action",
            entity_value="cancelar",
            mapped_value="cancel",
            confidence=0.93
        )
        db_session.add(mapping)
        db_session.commit()
        
        assert mapping.id is not None
        assert mapping.entity_type == "action"
        assert mapping.entity_value == "cancelar"
        assert mapping.mapped_value == "cancel"
        assert mapping.confidence == 0.93
        assert mapping.created_at is not None
    
    def test_update_entity_mapping_confidence(self, db_session, entity_mappings):
        """Test updating confidence score of existing mapping"""
        mapping = entity_mappings[0]
        original_confidence = mapping.confidence
        
        # Update confidence
        mapping.confidence = 0.99
        mapping.updated_at = datetime.utcnow()
        db_session.commit()
        
        # Verify update
        updated = db_session.query(EntityMapping).filter_by(id=mapping.id).first()
        assert updated.confidence == 0.99
        assert updated.confidence != original_confidence
        assert updated.updated_at is not None
    
    def test_find_mapping_by_value(self, db_session, entity_mappings):
        """Test finding entity mapping by value"""
        # Case insensitive search
        mapping = db_session.query(EntityMapping).filter(
            EntityMapping.entity_value.ilike("são paulo")
        ).first()
        
        assert mapping is not None
        assert mapping.entity_type == "location"
        assert mapping.mapped_value == "SAO_PAULO"
    
    def test_find_best_mapping(self, db_session, entity_mappings):
        """Test finding mapping with highest confidence"""
        # Add duplicate with lower confidence
        low_conf = EntityMapping(
            entity_type="action",
            entity_value="criar",
            mapped_value="make",
            confidence=0.70
        )
        db_session.add(low_conf)
        db_session.commit()
        
        # Find best mapping
        best = db_session.query(EntityMapping).filter_by(
            entity_type="action",
            entity_value="criar"
        ).order_by(EntityMapping.confidence.desc()).first()
        
        assert best.mapped_value == "create"
        assert best.confidence == 0.95
    
    def test_entity_type_filtering(self, db_session, entity_mappings):
        """Test filtering mappings by entity type"""
        actions = db_session.query(EntityMapping).filter_by(
            entity_type="action"
        ).all()
        
        objects = db_session.query(EntityMapping).filter_by(
            entity_type="object"
        ).all()
        
        assert len(actions) == 2
        assert len(objects) == 2
        assert all(m.entity_type == "action" for m in actions)
        assert all(m.entity_type == "object" for m in objects)
    
    def test_bulk_mapping_insert(self, db_session):
        """Test inserting multiple mappings efficiently"""
        mappings = [
            EntityMapping(
                entity_type="status",
                entity_value=value,
                mapped_value=mapped,
                confidence=conf
            )
            for value, mapped, conf in [
                ("pendente", "pending", 0.95),
                ("aprovado", "approved", 0.97),
                ("cancelado", "cancelled", 0.96),
                ("em transito", "in_transit", 0.94),
                ("entregue", "delivered", 0.98)
            ]
        ]
        
        db_session.bulk_save_objects(mappings)
        db_session.commit()
        
        # Verify all inserted
        status_mappings = db_session.query(EntityMapping).filter_by(
            entity_type="status"
        ).all()
        
        assert len(status_mappings) == 5
        assert all(m.confidence > 0.9 for m in status_mappings)
    
    def test_mapping_with_special_characters(self, db_session):
        """Test entity mapping with special characters and accents"""
        special_mappings = [
            ("São José dos Campos", "SAO_JOSE_DOS_CAMPOS"),
            ("Vitória-ES", "VITORIA_ES"),
            ("Brasília/DF", "BRASILIA_DF"),
            ("São Luís", "SAO_LUIS"),
            ("Belém do Pará", "BELEM_DO_PARA")
        ]
        
        for city, code in special_mappings:
            mapping = EntityMapping(
                entity_type="location",
                entity_value=city.lower(),
                mapped_value=code,
                confidence=0.98
            )
            db_session.add(mapping)
        
        db_session.commit()
        
        # Test retrieval
        mapping = db_session.query(EntityMapping).filter(
            EntityMapping.entity_value.ilike("%são josé%")
        ).first()
        
        assert mapping is not None
        assert mapping.mapped_value == "SAO_JOSE_DOS_CAMPOS"
    
    def test_mapping_version_history(self, db_session):
        """Test tracking mapping version changes"""
        mapping = EntityMapping(
            entity_type="action",
            entity_value="rastrear",
            mapped_value="track",
            confidence=0.90,
            version=1
        )
        db_session.add(mapping)
        db_session.commit()
        
        # Update mapping
        mapping.mapped_value = "trace"
        mapping.confidence = 0.95
        mapping.version = 2
        mapping.updated_at = datetime.utcnow()
        db_session.commit()
        
        # Verify version update
        updated = db_session.query(EntityMapping).filter_by(id=mapping.id).first()
        assert updated.version == 2
        assert updated.mapped_value == "trace"
        assert updated.confidence == 0.95
    
    def test_mapping_statistics(self, db_session, entity_mappings):
        """Test gathering statistics about entity mappings"""
        from sqlalchemy import func
        
        # Count by type
        type_counts = db_session.query(
            EntityMapping.entity_type,
            func.count(EntityMapping.id).label('count'),
            func.avg(EntityMapping.confidence).label('avg_confidence')
        ).group_by(EntityMapping.entity_type).all()
        
        type_stats = {tc[0]: {'count': tc[1], 'avg_conf': tc[2]} for tc in type_counts}
        
        assert 'action' in type_stats
        assert 'object' in type_stats
        assert 'location' in type_stats
        assert type_stats['action']['count'] == 2
        assert type_stats['location']['avg_conf'] == 0.99
    
    def test_mapping_search_fuzzy(self, db_session, entity_mappings):
        """Test fuzzy search for entity mappings"""
        # Test with partial match
        results = db_session.query(EntityMapping).filter(
            EntityMapping.entity_value.contains("emb")
        ).all()
        
        assert len(results) == 1
        assert results[0].entity_value == "embarque"
        
        # Test with pattern matching
        results = db_session.query(EntityMapping).filter(
            EntityMapping.entity_value.like("%ar%")
        ).all()
        
        assert len(results) >= 2  # "criar", "aprovar", "embarque"


class TestEntityExtractor:
    """Test suite for entity extraction from queries"""
    
    @pytest.fixture
    def extractor(self):
        """Create entity extractor instance"""
        return EntityExtractor()
    
    def test_extract_entities_basic(self, extractor, sample_queries_pt_br):
        """Test basic entity extraction from Portuguese queries"""
        query = sample_queries_pt_br[0]["query"]
        entities = extractor.extract_entities(query)
        
        assert "action" in entities
        assert "object" in entities
        assert "destination" in entities
        assert entities["action"] == "criar"
        assert entities["object"] == "embarque"
        assert entities["destination"] == "São Paulo"
    
    def test_extract_numeric_entities(self, extractor):
        """Test extraction of numeric entities"""
        query = "mostrar frete numero 12345 com valor de R$ 1.500,00"
        entities = extractor.extract_entities(query)
        
        assert "freight_id" in entities
        assert "value" in entities
        assert entities["freight_id"] == "12345"
        assert entities["value"] == 1500.00
    
    def test_extract_date_entities(self, extractor):
        """Test extraction of date-related entities"""
        queries = [
            ("entregas de hoje", "today"),
            ("fretes da semana passada", "last_week"),
            ("relatório do mês 03/2024", "2024-03"),
            ("embarques entre 01/01/2024 e 31/01/2024", ("2024-01-01", "2024-01-31"))
        ]
        
        for query, expected in queries:
            entities = extractor.extract_entities(query)
            assert "period" in entities or "date_range" in entities
    
    def test_extract_client_entities(self, extractor):
        """Test extraction of client-related entities"""
        query = "fretes do cliente ABC Transportes LTDA pendentes"
        entities = extractor.extract_entities(query)
        
        assert "client" in entities
        assert entities["client"] == "ABC Transportes LTDA"
        assert "status" in entities
        assert entities["status"] == "pendentes"
    
    def test_extract_multiple_entities(self, extractor):
        """Test extraction of multiple entities of same type"""
        query = "aprovar fretes 123, 456 e 789 do cliente XYZ"
        entities = extractor.extract_entities(query)
        
        assert "freight_ids" in entities
        assert isinstance(entities["freight_ids"], list)
        assert len(entities["freight_ids"]) == 3
        assert "123" in entities["freight_ids"]
        assert "789" in entities["freight_ids"]
    
    def test_extract_location_entities(self, extractor):
        """Test extraction of Brazilian location entities"""
        locations = [
            "São Paulo - SP",
            "Rio de Janeiro/RJ",
            "Belo Horizonte (MG)",
            "Porto Alegre RS",
            "Manaus AM"
        ]
        
        for location in locations:
            query = f"embarque para {location}"
            entities = extractor.extract_entities(query)
            assert "destination" in entities
            # Should extract city name without state code
            assert any(part in entities["destination"] for part in location.split()[0:2])
    
    def test_entity_extraction_performance(self, extractor, sample_queries_pt_br, performance_metrics):
        """Test entity extraction performance"""
        import time
        
        start_time = time.time()
        for query_data in sample_queries_pt_br * 20:  # Test with 100 queries
            extractor.extract_entities(query_data["query"])
        
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
        avg_time = elapsed_time / (len(sample_queries_pt_br) * 20)
        
        assert avg_time < performance_metrics["nlp_processing_time_ms"]


class TestEntityMapper:
    """Test suite for entity value mapping"""
    
    @pytest.fixture
    def mapper(self, db_session, entity_mappings):
        """Create entity mapper with test database"""
        return EntityMapper(db_session)
    
    def test_map_entity_value(self, mapper):
        """Test mapping entity value to system value"""
        mapped = mapper.map_entity("action", "criar")
        assert mapped == "create"
        
        mapped = mapper.map_entity("object", "embarque")
        assert mapped == "shipment"
    
    def test_map_unknown_entity(self, mapper):
        """Test mapping unknown entity returns original value"""
        mapped = mapper.map_entity("action", "unknown_action")
        assert mapped == "unknown_action"
    
    def test_map_entities_dict(self, mapper):
        """Test mapping entire entities dictionary"""
        entities = {
            "action": "aprovar",
            "object": "frete",
            "location": "são paulo"
        }
        
        mapped = mapper.map_all_entities(entities)
        
        assert mapped["action"] == "approve"
        assert mapped["object"] == "freight"
        assert mapped["location"] == "SAO_PAULO"
    
    def test_learn_new_mapping(self, mapper, db_session):
        """Test learning new entity mapping from user feedback"""
        # Simulate user correction
        mapper.learn_mapping(
            entity_type="action",
            entity_value="liberar",
            mapped_value="release",
            confidence=0.85
        )
        
        # Verify mapping was saved
        new_mapping = db_session.query(EntityMapping).filter_by(
            entity_value="liberar"
        ).first()
        
        assert new_mapping is not None
        assert new_mapping.mapped_value == "release"
        assert new_mapping.confidence == 0.85
    
    def test_update_mapping_confidence(self, mapper, db_session):
        """Test updating confidence based on usage"""
        # Get current confidence
        mapping = db_session.query(EntityMapping).filter_by(
            entity_value="criar"
        ).first()
        original_conf = mapping.confidence
        
        # Simulate successful usage
        mapper.update_confidence("action", "criar", success=True)
        
        # Check confidence increased
        db_session.refresh(mapping)
        assert mapping.confidence > original_conf
        assert mapping.confidence <= 1.0
    
    def test_mapping_cache(self, mapper):
        """Test entity mapping cache for performance"""
        # First call loads from DB
        mapped1 = mapper.map_entity("action", "criar")
        
        # Second call should use cache
        import time
        start = time.time()
        mapped2 = mapper.map_entity("action", "criar")
        cache_time = time.time() - start
        
        assert mapped1 == mapped2
        assert cache_time < 0.001  # Should be very fast from cache
    
    def test_bulk_mapping(self, mapper):
        """Test mapping multiple entities efficiently"""
        entities_list = [
            {"action": "criar", "object": "embarque"},
            {"action": "aprovar", "object": "frete"},
            {"action": "criar", "object": "frete"}
        ]
        
        mapped_list = mapper.map_multiple(entities_list)
        
        assert len(mapped_list) == 3
        assert mapped_list[0]["action"] == "create"
        assert mapped_list[1]["action"] == "approve"
        assert all("object" in m for m in mapped_list)
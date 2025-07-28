"""
Unit tests for neural processing system
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, mock_open
import json
from src.neural.neural_processor import (
    NeuralProcessor, 
    IntentClassifier,
    EntityExtractor,
    ContextAnalyzer,
    NeuralError
)


class TestNeuralProcessor:
    """Test cases for neural processing system"""
    
    @pytest.fixture
    def neural_processor(self):
        """Create neural processor instance"""
        return NeuralProcessor(
            model_path="test_models/",
            cache_enabled=True
        )
    
    @pytest.fixture
    def sample_freight_query(self):
        """Sample freight-related query"""
        return {
            "query": "Calculate freight cost from São Paulo to Rio de Janeiro for 1000kg",
            "context": {
                "user_id": "test-user",
                "session_id": "test-session",
                "timestamp": "2024-01-15T10:00:00Z"
            }
        }
    
    @pytest.fixture
    def mock_model(self):
        """Mock neural model"""
        model = MagicMock()
        model.predict.return_value = np.array([0.9, 0.05, 0.05])
        return model
    
    def test_process_query_success(self, neural_processor, sample_freight_query):
        """Test successful query processing"""
        with patch.object(neural_processor, 'classify_intent') as mock_classify:
            with patch.object(neural_processor, 'extract_entities') as mock_extract:
                mock_classify.return_value = {
                    "intent": "calculate_freight",
                    "confidence": 0.95
                }
                mock_extract.return_value = {
                    "origin": "São Paulo",
                    "destination": "Rio de Janeiro", 
                    "weight": 1000,
                    "unit": "kg"
                }
                
                result = neural_processor.process_query(sample_freight_query)
                
                assert result["intent"] == "calculate_freight"
                assert result["confidence"] >= 0.9
                assert result["entities"]["origin"] == "São Paulo"
                assert result["entities"]["weight"] == 1000
    
    def test_process_query_with_cache(self, neural_processor, sample_freight_query):
        """Test query processing with caching"""
        # First call - should process normally
        result1 = neural_processor.process_query(sample_freight_query)
        
        # Second call - should use cache
        result2 = neural_processor.process_query(sample_freight_query)
        
        assert result1 == result2
        
        # Verify cache was used (implementation specific)
        cache_key = neural_processor._get_cache_key(sample_freight_query["query"])
        assert cache_key in neural_processor.cache
    
    def test_process_query_invalid_input(self, neural_processor):
        """Test processing with invalid input"""
        invalid_queries = [
            None,
            "",
            {"query": ""},
            {"query": None},
            {"invalid": "structure"}
        ]
        
        for query in invalid_queries:
            with pytest.raises(NeuralError):
                neural_processor.process_query(query)
    
    def test_clear_cache(self, neural_processor, sample_freight_query):
        """Test cache clearing"""
        # Process query to populate cache
        neural_processor.process_query(sample_freight_query)
        assert len(neural_processor.cache) > 0
        
        # Clear cache
        neural_processor.clear_cache()
        assert len(neural_processor.cache) == 0


class TestIntentClassifier:
    """Test cases for intent classification"""
    
    @pytest.fixture
    def intent_classifier(self):
        """Create intent classifier instance"""
        return IntentClassifier(
            model_path="test_models/intent_model.pkl",
            confidence_threshold=0.7
        )
    
    @pytest.fixture
    def freight_intents(self):
        """Common freight-related intents"""
        return {
            "calculate_freight": [
                "Calculate freight cost",
                "How much to ship",
                "Shipping price for",
                "Freight quote for"
            ],
            "track_shipment": [
                "Where is my package",
                "Track order",
                "Shipment status",
                "Delivery tracking"
            ],
            "schedule_pickup": [
                "Schedule a pickup",
                "Book collection",
                "Arrange pickup",
                "Collection booking"
            ]
        }
    
    def test_classify_intent_high_confidence(self, intent_classifier, mock_model):
        """Test classification with high confidence"""
        intent_classifier.model = mock_model
        
        result = intent_classifier.classify("Calculate freight cost from SP to RJ")
        
        assert result["intent"] is not None
        assert result["confidence"] >= 0.7
        assert "top_intents" in result
        assert len(result["top_intents"]) <= 3
    
    def test_classify_intent_low_confidence(self, intent_classifier):
        """Test classification with low confidence"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.4, 0.3, 0.3])
        intent_classifier.model = mock_model
        
        result = intent_classifier.classify("Random unrelated query")
        
        assert result["intent"] == "unknown"
        assert result["confidence"] < 0.7
        assert result["needs_clarification"] is True
    
    def test_classify_intent_batch(self, intent_classifier, freight_intents, mock_model):
        """Test batch intent classification"""
        intent_classifier.model = mock_model
        
        queries = []
        for intent, examples in freight_intents.items():
            queries.extend(examples)
        
        results = intent_classifier.classify_batch(queries)
        
        assert len(results) == len(queries)
        assert all("intent" in r for r in results)
        assert all("confidence" in r for r in results)
    
    def test_retrain_classifier(self, intent_classifier):
        """Test classifier retraining"""
        training_data = [
            ("Calculate shipping cost", "calculate_freight"),
            ("Track my order", "track_shipment"),
            ("Book a pickup", "schedule_pickup")
        ]
        
        with patch('src.neural.neural_processor.train_model') as mock_train:
            mock_train.return_value = MagicMock()
            
            intent_classifier.retrain(training_data)
            
            mock_train.assert_called_once()
            assert intent_classifier.model is not None
    
    def test_save_load_model(self, intent_classifier, tmp_path):
        """Test model save and load"""
        model_path = tmp_path / "test_model.pkl"
        
        # Save model
        intent_classifier.save_model(str(model_path))
        assert model_path.exists()
        
        # Load model
        new_classifier = IntentClassifier(model_path=str(model_path))
        new_classifier.load_model()
        
        assert new_classifier.model is not None


class TestEntityExtractor:
    """Test cases for entity extraction"""
    
    @pytest.fixture
    def entity_extractor(self):
        """Create entity extractor instance"""
        return EntityExtractor(
            patterns_file="test_patterns.json"
        )
    
    @pytest.fixture
    def entity_patterns(self):
        """Entity extraction patterns"""
        return {
            "location": {
                "patterns": [
                    r"from\s+([A-Za-z\s]+)\s+to",
                    r"to\s+([A-Za-z\s]+)",
                    r"in\s+([A-Za-z\s]+)"
                ],
                "type": "string"
            },
            "weight": {
                "patterns": [
                    r"(\d+(?:\.\d+)?)\s*(?:kg|kilogram)",
                    r"(\d+(?:\.\d+)?)\s*(?:ton|t)"
                ],
                "type": "number",
                "unit_conversion": {
                    "kg": 1,
                    "ton": 1000,
                    "t": 1000
                }
            },
            "date": {
                "patterns": [
                    r"(\d{4}-\d{2}-\d{2})",
                    r"(today|tomorrow|next week)"
                ],
                "type": "date"
            }
        }
    
    def test_extract_location_entities(self, entity_extractor):
        """Test location entity extraction"""
        query = "Ship from São Paulo to Rio de Janeiro"
        
        entities = entity_extractor.extract(query, entity_type="location")
        
        assert "origin" in entities
        assert "destination" in entities
        assert entities["origin"] == "São Paulo"
        assert entities["destination"] == "Rio de Janeiro"
    
    def test_extract_weight_entities(self, entity_extractor):
        """Test weight entity extraction with unit conversion"""
        queries = [
            ("Ship 1000kg of cargo", 1000),
            ("Transport 2.5 tons", 2500),
            ("Move 500 kilograms", 500),
            ("Deliver 1.5t of goods", 1500)
        ]
        
        for query, expected_kg in queries:
            entities = entity_extractor.extract(query, entity_type="weight")
            assert "weight" in entities
            assert entities["weight"] == expected_kg
            assert entities["unit"] == "kg"  # Normalized unit
    
    def test_extract_date_entities(self, entity_extractor):
        """Test date entity extraction"""
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        queries = [
            ("Pickup on 2024-01-15", "2024-01-15"),
            ("Deliver today", str(today)),
            ("Schedule for tomorrow", str(tomorrow))
        ]
        
        for query, expected_date in queries:
            entities = entity_extractor.extract(query, entity_type="date")
            assert "date" in entities
            assert entities["date"] == expected_date
    
    def test_extract_multiple_entities(self, entity_extractor):
        """Test extraction of multiple entity types"""
        query = "Ship 1000kg from São Paulo to Rio tomorrow"
        
        entities = entity_extractor.extract_all(query)
        
        assert "origin" in entities
        assert "destination" in entities
        assert "weight" in entities
        assert "date" in entities
        assert entities["weight"] == 1000
        assert entities["origin"] == "São Paulo"
    
    def test_extract_entities_no_match(self, entity_extractor):
        """Test extraction when no entities found"""
        query = "This query has no relevant entities"
        
        entities = entity_extractor.extract_all(query)
        
        assert entities == {} or all(v is None for v in entities.values())
    
    def test_custom_entity_patterns(self, entity_extractor):
        """Test adding custom entity patterns"""
        custom_pattern = {
            "product_code": {
                "patterns": [r"SKU-(\d{6})", r"code:\s*(\w+)"],
                "type": "string"
            }
        }
        
        entity_extractor.add_pattern("product_code", custom_pattern["product_code"])
        
        query = "Ship product SKU-123456 urgently"
        entities = entity_extractor.extract(query, entity_type="product_code")
        
        assert "product_code" in entities
        assert entities["product_code"] == "123456"


class TestContextAnalyzer:
    """Test cases for context analysis"""
    
    @pytest.fixture
    def context_analyzer(self):
        """Create context analyzer instance"""
        return ContextAnalyzer(
            history_limit=10,
            relevance_threshold=0.5
        )
    
    @pytest.fixture
    def conversation_history(self):
        """Sample conversation history"""
        return [
            {
                "query": "Calculate freight from SP to RJ",
                "intent": "calculate_freight",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "query": "For 1000kg",
                "intent": "clarification",
                "timestamp": "2024-01-15T10:00:30Z"
            },
            {
                "query": "Express delivery",
                "intent": "service_selection",
                "timestamp": "2024-01-15T10:01:00Z"
            }
        ]
    
    def test_analyze_context_with_history(self, context_analyzer, conversation_history):
        """Test context analysis with conversation history"""
        current_query = "What's the estimated delivery time?"
        
        context = context_analyzer.analyze(
            query=current_query,
            history=conversation_history
        )
        
        assert "relevant_history" in context
        assert "context_intent" in context
        assert "missing_info" in context
        assert context["requires_clarification"] is False
    
    def test_analyze_context_missing_info(self, context_analyzer):
        """Test detection of missing information"""
        incomplete_query = "Calculate freight cost"
        
        context = context_analyzer.analyze(
            query=incomplete_query,
            history=[]
        )
        
        assert context["requires_clarification"] is True
        assert len(context["missing_info"]) > 0
        assert "origin" in context["missing_info"]
        assert "destination" in context["missing_info"]
    
    def test_merge_context_information(self, context_analyzer, conversation_history):
        """Test merging context from history"""
        current_query = "Use standard packaging"
        
        merged = context_analyzer.merge_context(
            current_query=current_query,
            history=conversation_history
        )
        
        assert "origin" in merged
        assert "destination" in merged
        assert "weight" in merged
        assert "service_type" in merged
        assert merged["packaging"] == "standard"
    
    def test_context_relevance_decay(self, context_analyzer):
        """Test context relevance decreases over time"""
        old_history = [
            {
                "query": "Old query",
                "timestamp": "2024-01-01T10:00:00Z",
                "intent": "calculate_freight"
            }
        ]
        
        current_query = "New freight calculation"
        context = context_analyzer.analyze(
            query=current_query,
            history=old_history,
            current_time="2024-01-15T10:00:00Z"
        )
        
        # Old context should have low relevance
        assert len(context["relevant_history"]) == 0
    
    def test_context_session_boundaries(self, context_analyzer):
        """Test context respects session boundaries"""
        history_multi_session = [
            {
                "query": "Query 1",
                "session_id": "session-1",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "query": "Query 2", 
                "session_id": "session-2",
                "timestamp": "2024-01-15T11:00:00Z"
            }
        ]
        
        context = context_analyzer.analyze(
            query="Current query",
            history=history_multi_session,
            session_id="session-2"
        )
        
        # Should only include same session
        assert all(h["session_id"] == "session-2" for h in context["relevant_history"])


class TestNeuralIntegration:
    """Integration tests for neural processing components"""
    
    @pytest.fixture
    def full_system(self):
        """Create full neural processing system"""
        return {
            "processor": NeuralProcessor(),
            "classifier": IntentClassifier(),
            "extractor": EntityExtractor(),
            "analyzer": ContextAnalyzer()
        }
    
    def test_end_to_end_processing(self, full_system):
        """Test complete processing pipeline"""
        query = {
            "query": "Calculate freight from São Paulo to Rio de Janeiro for 1000kg express delivery",
            "user_id": "test-user",
            "session_id": "test-session"
        }
        
        # Process through full pipeline
        result = full_system["processor"].process_query(query)
        
        assert result["intent"] in ["calculate_freight", "freight_quote"]
        assert result["entities"]["origin"] == "São Paulo"
        assert result["entities"]["destination"] == "Rio de Janeiro"
        assert result["entities"]["weight"] == 1000
        assert result["entities"]["service_type"] == "express"
        assert result["confidence"] > 0.7
    
    def test_multi_turn_conversation(self, full_system):
        """Test multi-turn conversation handling"""
        turns = [
            "I need to ship something",
            "From São Paulo", 
            "To Rio de Janeiro",
            "It weighs 1000kg",
            "Express delivery please"
        ]
        
        history = []
        final_context = None
        
        for turn in turns:
            query = {"query": turn, "session_id": "test-session"}
            result = full_system["processor"].process_query(query, history=history)
            
            history.append({
                "query": turn,
                "result": result,
                "timestamp": "2024-01-15T10:00:00Z"
            })
            
            final_context = result
        
        # Final context should have all information
        assert final_context["entities"].get("origin") == "São Paulo"
        assert final_context["entities"].get("destination") == "Rio de Janeiro"
        assert final_context["entities"].get("weight") == 1000
        assert final_context["entities"].get("service_type") == "express"
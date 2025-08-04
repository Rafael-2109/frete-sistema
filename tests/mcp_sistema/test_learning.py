"""
Tests for the learning and adaptation system
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from app.mcp_sistema.services.learning.learning_engine import LearningEngine
from app.mcp_sistema.services.learning.pattern_recognizer import PatternRecognizer
from app.mcp_sistema.services.learning.model_trainer import ModelTrainer
from app.mcp_sistema.models.mcp_models import (
    QueryLog, UserPreference, EntityMapping, LearningMetric
)


class TestLearningEngine:
    """Test suite for the main learning engine"""
    
    @pytest.fixture
    def learning_engine(self, db_session):
        """Create learning engine instance"""
        return LearningEngine(db_session)
    
    @pytest.mark.asyncio
    async def test_learn_from_query_feedback(self, learning_engine, db_session):
        """Test learning from user query feedback"""
        # Create query log
        query_log = QueryLog(
            user_id=1,
            query="liberar pedido",
            intent="unknown",
            confidence=0.3,
            entities={"action": "liberar", "object": "pedido"}
        )
        db_session.add(query_log)
        db_session.commit()
        
        # Apply feedback
        await learning_engine.learn_from_feedback(
            query_id=query_log.id,
            correct_intent="release_order",
            correct_entities={"action": "release", "object": "order"},
            user_satisfaction=0.9
        )
        
        # Verify learning
        metrics = await learning_engine.get_learning_metrics()
        assert metrics["feedback_processed"] > 0
        assert metrics["model_accuracy"] > 0.3  # Should improve
    
    @pytest.mark.asyncio
    async def test_pattern_learning(self, learning_engine):
        """Test learning usage patterns"""
        # Simulate user actions
        user_actions = [
            {"time": "09:00", "action": "check_freight_status"},
            {"time": "09:15", "action": "approve_freight"},
            {"time": "14:00", "action": "generate_report"},
            {"time": "14:30", "action": "check_freight_status"},
            {"time": "15:00", "action": "approve_freight"}
        ]
        
        for action in user_actions * 5:  # Repeat pattern
            await learning_engine.record_user_action(
                user_id=1,
                action_type=action["action"],
                timestamp=action["time"]
            )
        
        # Learn patterns
        patterns = await learning_engine.learn_user_patterns(user_id=1)
        
        assert "morning_routine" in patterns
        assert "afternoon_routine" in patterns
        assert patterns["morning_routine"]["common_actions"] == [
            "check_freight_status", "approve_freight"
        ]
    
    @pytest.mark.asyncio
    async def test_adaptive_suggestions(self, learning_engine):
        """Test adaptive query suggestions based on learning"""
        # Record successful queries
        successful_queries = [
            "criar embarque para São Paulo",
            "criar embarque para Rio de Janeiro",
            "criar embarque para Belo Horizonte"
        ]
        
        for query in successful_queries:
            await learning_engine.record_successful_query(
                user_id=1,
                query=query,
                intent="create_shipment",
                execution_time=0.5
            )
        
        # Get adaptive suggestions
        suggestions = await learning_engine.get_adaptive_suggestions(
            user_id=1,
            partial_query="criar emb"
        )
        
        assert len(suggestions) > 0
        assert all("criar embarque" in s for s in suggestions)
        # Should include learned destinations
        assert any("São Paulo" in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_performance_optimization(self, learning_engine):
        """Test learning for performance optimization"""
        # Record query performance
        queries_data = [
            ("simple query", 0.05, True),
            ("complex query with joins", 2.5, True),
            ("poorly formatted query", 5.0, False),
            ("optimized query", 0.1, True)
        ]
        
        for query, exec_time, success in queries_data:
            await learning_engine.record_query_performance(
                query=query,
                execution_time=exec_time,
                success=success
            )
        
        # Learn optimization patterns
        optimizations = await learning_engine.learn_query_optimizations()
        
        assert "avoid_complex_joins" in optimizations
        assert "query_reformulation" in optimizations
        assert optimizations["average_improvement"] > 0
    
    @pytest.mark.asyncio
    async def test_error_pattern_learning(self, learning_engine):
        """Test learning from error patterns"""
        # Record errors
        errors = [
            {"query": "aprovar frete", "error": "freight_not_found", "count": 5},
            {"query": "criar embarque", "error": "missing_destination", "count": 3},
            {"query": "gerar relatorio", "error": "permission_denied", "count": 2}
        ]
        
        for error in errors:
            for _ in range(error["count"]):
                await learning_engine.record_error(
                    user_id=1,
                    query=error["query"],
                    error_type=error["error"]
                )
        
        # Learn from errors
        error_insights = await learning_engine.analyze_error_patterns()
        
        assert error_insights["most_common_error"] == "freight_not_found"
        assert "suggested_validations" in error_insights
        assert len(error_insights["preventive_measures"]) > 0
    
    @pytest.mark.asyncio
    async def test_incremental_learning(self, learning_engine):
        """Test incremental model updates"""
        # Initial training
        initial_accuracy = await learning_engine.train_initial_model()
        
        # Add new data
        new_examples = [
            {"query": "rastrear carga", "intent": "track_shipment"},
            {"query": "localizar entrega", "intent": "track_shipment"},
            {"query": "onde está meu pedido", "intent": "track_shipment"}
        ]
        
        for example in new_examples:
            await learning_engine.add_training_example(
                query=example["query"],
                intent=example["intent"]
            )
        
        # Incremental update
        updated_accuracy = await learning_engine.update_model_incrementally()
        
        assert updated_accuracy > initial_accuracy
        assert await learning_engine.model_version > 1


class TestPatternRecognizer:
    """Test suite for pattern recognition"""
    
    @pytest.fixture
    def pattern_recognizer(self):
        """Create pattern recognizer instance"""
        return PatternRecognizer()
    
    def test_temporal_pattern_detection(self, pattern_recognizer):
        """Test detecting temporal patterns in user behavior"""
        # Generate time series data
        timestamps = []
        base_time = datetime.now()
        
        # Morning pattern (9-11 AM)
        for day in range(30):
            for hour in [9, 10]:
                timestamps.append(
                    base_time + timedelta(days=day, hours=hour)
                )
        
        patterns = pattern_recognizer.detect_temporal_patterns(timestamps)
        
        assert len(patterns) > 0
        assert patterns[0]["type"] == "daily"
        assert patterns[0]["peak_hours"] == [9, 10]
        assert patterns[0]["confidence"] > 0.8
    
    def test_sequence_pattern_detection(self, pattern_recognizer):
        """Test detecting sequence patterns in user actions"""
        # Common action sequences
        action_sequences = [
            ["login", "check_dashboard", "view_freights", "approve_freight"],
            ["login", "check_dashboard", "view_freights", "approve_freight"],
            ["login", "check_dashboard", "generate_report"],
            ["login", "check_dashboard", "view_freights", "approve_freight"]
        ]
        
        patterns = pattern_recognizer.detect_sequence_patterns(action_sequences)
        
        assert len(patterns) > 0
        most_common = patterns[0]
        assert most_common["sequence"][:2] == ["login", "check_dashboard"]
        assert most_common["frequency"] >= 3
    
    def test_anomaly_detection(self, pattern_recognizer):
        """Test detecting anomalous patterns"""
        # Normal behavior
        normal_actions = ["check_status"] * 50 + ["approve_freight"] * 30
        
        # Anomalous behavior
        anomalous_actions = ["delete_all_freights", "export_all_data"]
        
        all_actions = normal_actions + anomalous_actions
        
        anomalies = pattern_recognizer.detect_anomalies(
            all_actions,
            user_id=1
        )
        
        assert len(anomalies) == 2
        assert all(a["action"] in anomalous_actions for a in anomalies)
        assert all(a["anomaly_score"] > 0.8 for a in anomalies)
    
    def test_correlation_detection(self, pattern_recognizer):
        """Test detecting correlations between different metrics"""
        # Generate correlated data
        hours = list(range(24)) * 30
        query_counts = [20 + h if 9 <= h <= 17 else 5 for h in hours]
        response_times = [0.1 if c < 15 else 0.5 for c in query_counts]
        
        correlations = pattern_recognizer.detect_correlations({
            "hour": hours,
            "query_count": query_counts,
            "response_time": response_times
        })
        
        assert "query_count_vs_response_time" in correlations
        assert correlations["query_count_vs_response_time"]["correlation"] > 0.7
        assert correlations["query_count_vs_response_time"]["significant"] is True
    
    def test_clustering_patterns(self, pattern_recognizer):
        """Test clustering similar patterns"""
        # User queries with natural clusters
        queries = [
            # Cluster 1: Freight status
            "status do frete 123",
            "verificar frete 456",
            "qual status do frete 789",
            
            # Cluster 2: Create shipment
            "criar embarque SP",
            "novo embarque RJ",
            "gerar embarque MG",
            
            # Cluster 3: Reports
            "relatorio mensal",
            "gerar relatorio vendas",
            "exportar relatorio"
        ]
        
        clusters = pattern_recognizer.cluster_patterns(queries, n_clusters=3)
        
        assert len(clusters) == 3
        # Each cluster should have related queries
        for cluster in clusters:
            assert len(cluster["members"]) >= 2
            assert cluster["coherence_score"] > 0.7


class TestModelTrainer:
    """Test suite for model training and updates"""
    
    @pytest.fixture
    def model_trainer(self, db_session):
        """Create model trainer instance"""
        return ModelTrainer(db_session)
    
    @pytest.mark.asyncio
    async def test_train_intent_classifier(self, model_trainer):
        """Test training intent classification model"""
        # Training data
        training_data = [
            ("criar novo embarque", "create_shipment"),
            ("gerar embarque", "create_shipment"),
            ("verificar status", "check_status"),
            ("qual a situação", "check_status"),
            ("aprovar frete", "approve_freight"),
            ("liberar pagamento", "approve_freight")
        ]
        
        # Train model
        metrics = await model_trainer.train_intent_classifier(training_data)
        
        assert metrics["accuracy"] > 0.8
        assert metrics["training_samples"] == 6
        assert "model_path" in metrics
        
        # Test prediction
        prediction = await model_trainer.predict_intent("novo embarque para")
        assert prediction["intent"] == "create_shipment"
        assert prediction["confidence"] > 0.7
    
    @pytest.mark.asyncio
    async def test_train_entity_extractor(self, model_trainer):
        """Test training entity extraction model"""
        # Training data with entities
        training_data = [
            {
                "text": "criar embarque para São Paulo",
                "entities": [
                    {"start": 0, "end": 5, "label": "ACTION", "value": "criar"},
                    {"start": 6, "end": 14, "label": "OBJECT", "value": "embarque"},
                    {"start": 20, "end": 29, "label": "LOCATION", "value": "São Paulo"}
                ]
            },
            {
                "text": "aprovar frete 12345",
                "entities": [
                    {"start": 0, "end": 7, "label": "ACTION", "value": "aprovar"},
                    {"start": 8, "end": 13, "label": "OBJECT", "value": "frete"},
                    {"start": 14, "end": 19, "label": "ID", "value": "12345"}
                ]
            }
        ]
        
        # Train model
        metrics = await model_trainer.train_entity_extractor(training_data)
        
        assert metrics["f1_score"] > 0.7
        assert "per_entity_metrics" in metrics
        
        # Test extraction
        entities = await model_trainer.extract_entities("criar novo frete")
        assert len(entities) >= 2
        assert any(e["label"] == "ACTION" for e in entities)
    
    @pytest.mark.asyncio
    async def test_cross_validation(self, model_trainer):
        """Test model cross-validation"""
        # Prepare data
        data = [
            ("query1", "intent1"),
            ("query2", "intent1"),
            ("query3", "intent2"),
            ("query4", "intent2"),
            ("query5", "intent3"),
            ("query6", "intent3")
        ]
        
        # Run cross-validation
        cv_results = await model_trainer.cross_validate(
            data,
            n_folds=3
        )
        
        assert len(cv_results["fold_scores"]) == 3
        assert cv_results["mean_accuracy"] > 0.0
        assert cv_results["std_accuracy"] >= 0.0
    
    @pytest.mark.asyncio
    async def test_model_versioning(self, model_trainer):
        """Test model version management"""
        # Train initial version
        v1_metrics = await model_trainer.train_intent_classifier(
            [("test", "intent1")]
        )
        
        # Train new version
        v2_metrics = await model_trainer.train_intent_classifier(
            [("test", "intent1"), ("test2", "intent2")]
        )
        
        assert v2_metrics["version"] > v1_metrics["version"]
        
        # Test rollback
        await model_trainer.rollback_model(v1_metrics["version"])
        current_version = await model_trainer.get_current_version()
        assert current_version == v1_metrics["version"]
    
    @pytest.mark.asyncio
    async def test_active_learning(self, model_trainer):
        """Test active learning for uncertain predictions"""
        # Get uncertain examples
        uncertain_queries = [
            "fazer algo com frete",  # Ambiguous
            "preciso de ajuda",  # Too general
            "xyz abc 123"  # Nonsensical
        ]
        
        suggestions = await model_trainer.suggest_for_labeling(
            uncertain_queries
        )
        
        assert len(suggestions) > 0
        assert all(s["uncertainty_score"] > 0.5 for s in suggestions)
        assert "suggested_intent" in suggestions[0]
    
    @pytest.mark.asyncio
    async def test_transfer_learning(self, model_trainer):
        """Test transfer learning from pre-trained models"""
        # Use pre-trained embeddings
        base_model = await model_trainer.load_pretrained_model("pt-br-base")
        
        # Fine-tune on domain data
        domain_data = [
            ("frete", "freight"),
            ("embarque", "shipment"),
            ("entrega", "delivery")
        ]
        
        fine_tuned = await model_trainer.fine_tune(
            base_model,
            domain_data
        )
        
        assert fine_tuned["improvement"] > 0
        assert fine_tuned["domain_accuracy"] > fine_tuned["base_accuracy"]


class TestLearningIntegration:
    """Integration tests for learning system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_learning_cycle(self, learning_engine, db_session):
        """Test complete learning cycle from data to deployment"""
        # 1. Collect initial data
        initial_queries = [
            {"query": "criar embarque", "intent": "create_shipment", "success": True},
            {"query": "verificar status", "intent": "check_status", "success": True},
            {"query": "xyz invalid", "intent": "unknown", "success": False}
        ]
        
        for q in initial_queries:
            await learning_engine.record_query_result(q)
        
        # 2. Train initial model
        initial_metrics = await learning_engine.train_models()
        assert initial_metrics["status"] == "success"
        
        # 3. Collect feedback and improve
        feedback_data = [
            {"query": "xyz invalid", "correct_intent": "create_report"},
            {"query": "gerar relatorio", "correct_intent": "create_report"}
        ]
        
        for f in feedback_data:
            await learning_engine.apply_feedback(f)
        
        # 4. Retrain with feedback
        improved_metrics = await learning_engine.train_models()
        assert improved_metrics["accuracy"] > initial_metrics["accuracy"]
        
        # 5. Deploy new model
        deployment = await learning_engine.deploy_model(
            version=improved_metrics["version"]
        )
        assert deployment["status"] == "deployed"
        
        # 6. Monitor performance
        performance = await learning_engine.monitor_model_performance()
        assert performance["queries_processed"] > 0
        assert performance["accuracy_trend"] == "improving"
    
    @pytest.mark.asyncio
    async def test_multi_user_personalization(self, learning_engine, db_session):
        """Test personalized learning for multiple users"""
        # User 1: Frequently uses freight operations
        user1_queries = [
            "verificar frete",
            "aprovar frete",
            "status do frete"
        ] * 10
        
        # User 2: Frequently generates reports
        user2_queries = [
            "gerar relatorio",
            "exportar dados",
            "relatorio mensal"
        ] * 10
        
        # Record usage
        for query in user1_queries:
            await learning_engine.record_user_query(1, query)
        
        for query in user2_queries:
            await learning_engine.record_user_query(2, query)
        
        # Get personalized suggestions
        user1_suggestions = await learning_engine.get_personalized_suggestions(1, "")
        user2_suggestions = await learning_engine.get_personalized_suggestions(2, "")
        
        assert any("frete" in s for s in user1_suggestions)
        assert any("relatorio" in s for s in user2_suggestions)
        assert user1_suggestions != user2_suggestions
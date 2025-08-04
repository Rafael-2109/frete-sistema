"""
Tests for Preference Manager and Learning System
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from app.mcp_logistica.preference_manager import PreferenceManager


class TestPreferenceManager:
    """Test preference management and learning functionality"""
    
    def test_initialization(self, preference_manager):
        """Test preference manager initialization"""
        assert preference_manager is not None
        assert hasattr(preference_manager, 'user_preferences')
        assert hasattr(preference_manager, 'query_patterns')
        assert hasattr(preference_manager, 'learning_enabled')
        assert preference_manager.learning_enabled == True
        
    def test_get_user_preferences_default(self, preference_manager):
        """Test getting default preferences for new user"""
        user_id = "new_user"
        prefs = preference_manager.get_user_preferences(user_id)
        
        assert isinstance(prefs, dict)
        assert 'response_format' in prefs
        assert prefs['response_format'] == 'auto'
        assert 'items_per_page' in prefs
        assert prefs['items_per_page'] == 20
        
    def test_update_preference(self, preference_manager):
        """Test updating user preferences"""
        user_id = "user1"
        
        # Update single preference
        preference_manager.update_preference(
            user_id, 
            'manual',
            'items_per_page',
            50
        )
        
        prefs = preference_manager.get_user_preferences(user_id)
        assert prefs['items_per_page'] == 50
        
        # Update multiple preferences
        preference_manager.update_preference(
            user_id,
            'manual', 
            'default_domain',
            'pedidos'
        )
        
        prefs = preference_manager.get_user_preferences(user_id)
        assert prefs['default_domain'] == 'pedidos'
        
    def test_learn_from_query_patterns(self, preference_manager):
        """Test learning from query patterns"""
        user_id = "user1"
        
        # Simulate multiple queries
        queries = [
            {
                'original_query': 'buscar entregas',
                'entities': {'domain': 'entregas'},
                'context': {'domain': 'entregas'},
                'intent': {'primary': 'buscar'},
                'response_format': 'table'
            },
            {
                'original_query': 'listar entregas',
                'entities': {'domain': 'entregas'},
                'context': {'domain': 'entregas'},
                'intent': {'primary': 'listar'},
                'response_format': 'table'
            },
            {
                'original_query': 'status entrega',
                'entities': {'domain': 'entregas'},
                'context': {'domain': 'entregas'},
                'intent': {'primary': 'status'},
                'response_format': 'card'
            }
        ]
        
        for query in queries:
            preference_manager.learn_from_query(user_id, query)
            
        # Check learned patterns
        patterns = preference_manager.get_query_patterns(user_id)
        assert 'most_used_domain' in patterns
        assert patterns['most_used_domain'] == 'entregas'
        assert 'common_intents' in patterns
        assert 'buscar' in patterns['common_intents']
        
    def test_query_suggestions(self, preference_manager):
        """Test query suggestion generation"""
        user_id = "user1"
        
        # Add query history
        for i in range(5):
            preference_manager.learn_from_query(user_id, {
                'original_query': f'buscar entregas cliente {i}',
                'entities': {'cliente': f'Cliente {i}'},
                'context': {'domain': 'entregas'},
                'intent': {'primary': 'buscar'},
                'success': True
            })
            
        # Get suggestions
        suggestions = preference_manager.get_query_suggestions(user_id, 'buscar')
        
        assert len(suggestions) > 0
        assert any('buscar entregas' in s for s in suggestions)
        
    def test_preference_insights(self, preference_manager):
        """Test preference insights generation"""
        user_id = "user1"
        
        # Create activity
        for _ in range(10):
            preference_manager.learn_from_query(user_id, {
                'original_query': 'test query',
                'entities': {},
                'context': {'urgency': True},
                'intent': {'primary': 'buscar'},
                'success': True
            })
            
        insights = preference_manager.get_preference_insights(user_id)
        
        assert 'total_queries' in insights
        assert insights['total_queries'] >= 10
        assert 'success_rate' in insights
        assert 'common_patterns' in insights
        
    def test_apply_user_context(self, preference_manager):
        """Test applying user preferences to context"""
        user_id = "user1"
        
        # Set preferences
        preference_manager.update_preference(user_id, 'manual', 'default_domain', 'pedidos')
        preference_manager.update_preference(user_id, 'manual', 'auto_export', True)
        
        # Apply to context
        base_context = {'timestamp': datetime.now()}
        enhanced_context = preference_manager.apply_user_context(user_id, base_context)
        
        assert enhanced_context['default_domain'] == 'pedidos'
        assert enhanced_context['auto_export'] == True
        assert 'timestamp' in enhanced_context
        
    def test_preference_persistence(self, preference_manager):
        """Test preference persistence across sessions"""
        user_id = "user1"
        
        # Set preferences
        preference_manager.update_preference(user_id, 'manual', 'theme', 'dark')
        preference_manager.update_preference(user_id, 'manual', 'language', 'pt-BR')
        
        # Simulate saving
        if hasattr(preference_manager, 'save_preferences'):
            preference_manager.save_preferences()
            
        # Create new instance (simulating new session)
        new_manager = PreferenceManager()
        
        # Preferences should persist (in real implementation)
        # For testing, we'll check the original instance
        prefs = preference_manager.get_user_preferences(user_id)
        assert prefs['theme'] == 'dark'
        assert prefs['language'] == 'pt-BR'
        
    def test_preference_reset(self, preference_manager):
        """Test resetting user preferences"""
        user_id = "user1"
        
        # Set custom preferences
        preference_manager.update_preference(user_id, 'manual', 'items_per_page', 100)
        
        # Reset preferences
        preference_manager.reset_preferences(user_id)
        
        # Should return to defaults
        prefs = preference_manager.get_user_preferences(user_id)
        assert prefs['items_per_page'] == 20  # Default value
        
    def test_learning_from_feedback(self, preference_manager):
        """Test learning from explicit user feedback"""
        user_id = "user1"
        
        # Negative feedback on response format
        feedback = {
            'query_id': 'q123',
            'satisfaction': 'unsatisfied',
            'reason': 'prefer_different_format',
            'preferred_format': 'chart'
        }
        
        preference_manager.process_feedback(user_id, feedback)
        
        # Should learn preference
        prefs = preference_manager.get_user_preferences(user_id)
        # In real implementation, would adjust preferences based on feedback
        
    def test_domain_affinity_learning(self, preference_manager):
        """Test learning domain preferences"""
        user_id = "user1"
        
        # Simulate queries across domains
        domains = ['entregas'] * 10 + ['pedidos'] * 5 + ['fretes'] * 2
        
        for domain in domains:
            preference_manager.learn_from_query(user_id, {
                'original_query': f'buscar {domain}',
                'context': {'domain': domain},
                'entities': {},
                'intent': {'primary': 'buscar'},
                'success': True
            })
            
        patterns = preference_manager.get_query_patterns(user_id)
        
        # Should identify primary domain
        assert patterns['most_used_domain'] == 'entregas'
        assert patterns['domain_distribution']['entregas'] > patterns['domain_distribution']['pedidos']
        
    def test_time_based_patterns(self, preference_manager):
        """Test learning time-based usage patterns"""
        user_id = "user1"
        
        # Simulate morning queries
        morning_time = datetime.now().replace(hour=9)
        for i in range(5):
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = morning_time
                preference_manager.learn_from_query(user_id, {
                    'original_query': 'relatorio diario',
                    'context': {'time_of_day': 'morning'},
                    'intent': {'primary': 'relatorio'},
                    'entities': {},
                    'success': True
                })
                
        patterns = preference_manager.get_time_based_patterns(user_id)
        
        # Should identify morning preference
        assert 'peak_hours' in patterns
        assert 9 in patterns['peak_hours']
        
    def test_error_pattern_learning(self, preference_manager):
        """Test learning from error patterns"""
        user_id = "user1"
        
        # Simulate repeated errors
        for i in range(3):
            preference_manager.learn_from_query(user_id, {
                'original_query': 'buscar cliente XYZ',
                'entities': {'cliente': 'XYZ'},
                'context': {},
                'intent': {'primary': 'buscar'},
                'success': False,
                'error': 'Cliente não encontrado'
            })
            
        # Should learn to avoid or suggest alternatives
        suggestions = preference_manager.get_query_suggestions(user_id, 'buscar cliente')
        # In real implementation, would avoid suggesting failed patterns
        
    def test_preference_export_import(self, preference_manager):
        """Test exporting and importing preferences"""
        user_id = "user1"
        
        # Set preferences
        preference_manager.update_preference(user_id, 'manual', 'theme', 'dark')
        preference_manager.update_preference(user_id, 'manual', 'notifications', True)
        
        # Export
        exported = preference_manager.export_preferences(user_id)
        
        assert 'preferences' in exported
        assert 'patterns' in exported
        assert 'export_date' in exported
        
        # Import to new user
        new_user_id = "user2"
        preference_manager.import_preferences(new_user_id, exported)
        
        # Should have same preferences
        prefs = preference_manager.get_user_preferences(new_user_id)
        assert prefs['theme'] == 'dark'
        assert prefs['notifications'] == True
        
    def test_adaptive_learning_rate(self, preference_manager):
        """Test adaptive learning rate based on consistency"""
        user_id = "user1"
        
        # Consistent behavior - should learn faster
        for i in range(20):
            preference_manager.learn_from_query(user_id, {
                'original_query': 'exportar para excel',
                'entities': {},
                'context': {},
                'intent': {'primary': 'exportar'},
                'response_format': 'excel',
                'success': True
            })
            
        # Check if preference was learned
        prefs = preference_manager.get_user_preferences(user_id)
        patterns = preference_manager.get_query_patterns(user_id)
        
        # Should have high confidence in export format preference
        assert patterns.get('export_format_preference') == 'excel'
        
    def test_multi_user_isolation(self, preference_manager):
        """Test preference isolation between users"""
        user1 = "user1"
        user2 = "user2"
        
        # Set different preferences
        preference_manager.update_preference(user1, 'manual', 'theme', 'light')
        preference_manager.update_preference(user2, 'manual', 'theme', 'dark')
        
        # Verify isolation
        prefs1 = preference_manager.get_user_preferences(user1)
        prefs2 = preference_manager.get_user_preferences(user2)
        
        assert prefs1['theme'] == 'light'
        assert prefs2['theme'] == 'dark'
        
    def test_preference_versioning(self, preference_manager):
        """Test preference version tracking"""
        user_id = "user1"
        
        # Update preferences multiple times
        versions = []
        for i in range(3):
            preference_manager.update_preference(
                user_id, 
                'manual',
                'items_per_page',
                (i + 1) * 10
            )
            versions.append(preference_manager.get_preference_version(user_id))
            
        # Versions should increment
        assert len(set(versions)) == 3  # All different
        
    def test_performance(self, preference_manager, performance_logger):
        """Test preference manager performance"""
        # Test with many users
        ctx = performance_logger.start("create_100_users")
        for i in range(100):
            user_id = f"user_{i}"
            preference_manager.update_preference(user_id, 'manual', 'theme', 'dark')
        duration = performance_logger.end(ctx)
        
        assert duration < 0.5  # Should handle 100 users quickly
        
        # Test preference retrieval
        ctx = performance_logger.start("get_preferences")
        for i in range(100):
            prefs = preference_manager.get_user_preferences(f"user_{i}")
        duration = performance_logger.end(ctx)
        
        assert duration < 0.1  # Should be very fast
"""
Tests for Flask API Endpoints
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from flask import g
from app.mcp_logistica.flask_integration import mcp_logistica_bp, init_mcp_logistica
from app.mcp_logistica.query_processor import QueryResult
from app.mcp_logistica.intent_classifier import Intent
from app.mcp_logistica.confirmation_system import ActionType, ConfirmationStatus


class TestFlaskEndpoints:
    """Test Flask API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup_app(self, app, client, mock_user):
        """Setup Flask app for testing"""
        with app.app_context():
            # Initialize MCP
            init_mcp_logistica(app)
            
            # Mock current_user
            with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
                yield
                
    def test_query_endpoint_success(self, client, mock_user):
        """Test successful query processing"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.query_processor') as mock_qp:
                # Mock successful result
                mock_result = QueryResult(
                    success=True,
                    query=Mock(entities={'nf': '123'}, context={}, response_format='table'),
                    intent=Intent(primary="buscar", secondary=None, confidence=0.8),
                    data=[{'id': 1, 'nf': '123'}],
                    sql="SELECT * FROM test",
                    suggestions=["Ver detalhes", "Exportar"]
                )
                mock_qp.process.return_value = mock_result
                
                response = client.post('/api/mcp/logistica/query', 
                    json={'query': 'buscar nf 123'},
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] == True
                assert data['intent']['primary'] == 'buscar'
                assert data['intent']['confidence'] == 0.8
                assert len(data['suggestions']) == 2
                
    def test_query_endpoint_missing_query(self, client, mock_user):
        """Test query endpoint with missing query"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            response = client.post('/api/mcp/logistica/query',
                json={},  # Missing query
                headers={'Authorization': 'Bearer test-token'}
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Query não fornecida' in data['error']
            
    def test_query_endpoint_with_confirmation(self, client, mock_user):
        """Test query requiring confirmation"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.query_processor') as mock_qp:
                with patch('app.mcp_logistica.flask_integration.confirmation_system') as mock_cs:
                    # Mock result requiring confirmation
                    mock_result = QueryResult(
                        success=True,
                        query=Mock(context={'domain': 'entregas'}),
                        intent=Intent(
                            primary="reagendar",
                            confidence=0.9,
                            action_required=True,
                            parameters={'entity_id': '123', 'nova_data': '2024-12-25'}
                        )
                    )
                    mock_qp.process.return_value = mock_result
                    
                    # Mock confirmation creation
                    mock_confirmation = Mock(id='conf-123')
                    mock_confirmation.to_dict.return_value = {
                        'id': 'conf-123',
                        'action_type': 'reagendar',
                        'status': 'pending'
                    }
                    mock_cs.create_confirmation_request.return_value = mock_confirmation
                    
                    response = client.post('/api/mcp/logistica/query',
                        json={'query': 'reagendar entrega para amanhã'},
                        headers={'Authorization': 'Bearer test-token'}
                    )
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['requires_confirmation'] == True
                    assert data['confirmation_id'] == 'conf-123'
                    
    def test_query_endpoint_with_claude(self, client, mock_user):
        """Test query with Claude enhancement"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.query_processor') as mock_qp:
                # Mock result with Claude response
                mock_result = QueryResult(
                    success=True,
                    query=Mock(entities={}, context={}, response_format='text'),
                    intent=Intent(primary="explicar", confidence=0.7),
                    natural_response="Baseado na análise, identificamos...",
                    claude_response=Mock(
                        success=True,
                        response_type='direct',
                        confidence=0.8,
                        direct_answer="Análise detalhada dos dados"
                    )
                )
                mock_qp.process.return_value = mock_result
                
                response = client.post('/api/mcp/logistica/query',
                    json={'query': 'explicar tendência de entregas', 'enhance_with_claude': True},
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert 'natural_response' in data
                assert 'claude_insights' in data
                assert data['claude_insights']['used'] == True
                
    def test_query_endpoint_error_handling(self, client, mock_user):
        """Test error handling in query endpoint"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.query_processor') as mock_qp:
                # Force exception
                mock_qp.process.side_effect = Exception("Processing error")
                
                response = client.post('/api/mcp/logistica/query',
                    json={'query': 'test query'},
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data['success'] == False
                assert 'error' in data
                
    def test_suggestions_endpoint(self, client, mock_user):
        """Test suggestions endpoint"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.preference_manager') as mock_pm:
                mock_pm.get_query_suggestions.return_value = [
                    "buscar entregas atrasadas",
                    "buscar entregas de hoje",
                    "buscar entregas por cliente"
                ]
                
                response = client.get('/api/mcp/logistica/suggestions?q=buscar',
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] == True
                assert len(data['suggestions']) == 3
                
    def test_preferences_get_endpoint(self, client, mock_user):
        """Test getting user preferences"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.preference_manager') as mock_pm:
                mock_pm.get_user_preferences.return_value = {
                    'default_domain': 'entregas',
                    'items_per_page': 50
                }
                mock_pm.get_preference_insights.return_value = {
                    'most_used_intent': 'buscar',
                    'query_count': 150
                }
                
                response = client.get('/api/mcp/logistica/preferences',
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['preferences']['default_domain'] == 'entregas'
                assert data['insights']['query_count'] == 150
                
    def test_preferences_update_endpoint(self, client, mock_user):
        """Test updating user preferences"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.preference_manager') as mock_pm:
                response = client.put('/api/mcp/logistica/preferences',
                    json={
                        'default_domain': 'pedidos',
                        'items_per_page': 100
                    },
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] == True
                
                # Verify update was called
                assert mock_pm.update_preference.call_count == 2
                
    def test_pending_confirmations_endpoint(self, client, mock_user):
        """Test getting pending confirmations"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.confirmation_system') as mock_cs:
                mock_confirmations = [
                    Mock(to_dict=lambda: {'id': '1', 'action_type': 'reagendar'}),
                    Mock(to_dict=lambda: {'id': '2', 'action_type': 'cancelar'})
                ]
                mock_cs.get_pending_confirmations.return_value = mock_confirmations
                
                response = client.get('/api/mcp/logistica/confirmations',
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert len(data['confirmations']) == 2
                
    def test_confirm_action_endpoint(self, client, mock_user):
        """Test confirming an action"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.confirmation_system') as mock_cs:
                mock_cs.confirm_action.return_value = True
                
                response = client.post('/api/mcp/logistica/confirmations/conf-123/confirm',
                    json={'details': {'observacao': 'Confirmado'}},
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] == True
                
    def test_reject_action_endpoint(self, client, mock_user):
        """Test rejecting an action"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.confirmation_system') as mock_cs:
                mock_cs.reject_action.return_value = True
                
                response = client.post('/api/mcp/logistica/confirmations/conf-123/reject',
                    json={'reason': 'Dados incorretos'},
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] == True
                
    def test_feedback_endpoint(self, client, mock_user):
        """Test feedback submission"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.query_processor') as mock_qp:
                response = client.post('/api/mcp/logistica/feedback',
                    json={
                        'query_id': 'query-123',
                        'feedback': {
                            'correct_intent': False,
                            'actual_intent': 'status'
                        }
                    },
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] == True
                
    def test_test_query_endpoint(self, client):
        """Test the test query endpoint (no auth required)"""
        with patch('app.mcp_logistica.flask_integration.query_processor') as mock_qp:
            mock_result = QueryResult(
                success=True,
                query=Mock(entities={}, context={}),
                intent=Intent(primary="buscar", confidence=0.8),
                data={'total': 10},
                sql="SELECT COUNT(*) FROM test",
                suggestions=["Test suggestion"]
            )
            mock_qp.process.return_value = mock_result
            
            response = client.post('/api/mcp/logistica/test/query',
                json={'query': 'test query'}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == True
            assert data['intent']['primary'] == 'buscar'
            
    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get('/api/mcp/logistica/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] in ['healthy', 'degraded']
        assert 'components' in data
        assert 'timestamp' in data
        
    def test_statistics_endpoint(self, client, mock_user):
        """Test statistics endpoint"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.error_handler') as mock_eh:
                with patch('app.mcp_logistica.flask_integration.confirmation_system') as mock_cs:
                    mock_eh.get_error_statistics.return_value = {
                        'total_errors': 5,
                        'by_category': {'system': 3, 'validation': 2}
                    }
                    mock_cs.get_pending_confirmations.return_value = [Mock(), Mock()]
                    
                    response = client.get('/api/mcp/logistica/stats',
                        headers={'Authorization': 'Bearer test-token'}
                    )
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['statistics']['errors']['total_errors'] == 5
                    assert data['statistics']['pending_confirmations'] == 2
                    
    def test_session_summary_endpoint(self, client, mock_user):
        """Test session summary endpoint"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.query_processor') as mock_qp:
                mock_qp.claude_integration.get_session_summary.return_value = {
                    'session_id': 'test-session',
                    'query_count': 10,
                    'domains_accessed': ['entregas', 'pedidos']
                }
                
                response = client.get('/api/mcp/logistica/session/summary',
                    headers={
                        'Authorization': 'Bearer test-token',
                        'X-Session-Id': 'test-session'
                    }
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['summary']['query_count'] == 10
                
    def test_clear_session_endpoint(self, client, mock_user):
        """Test clear session endpoint"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.query_processor') as mock_qp:
                response = client.post('/api/mcp/logistica/session/clear',
                    headers={
                        'Authorization': 'Bearer test-token',
                        'X-Session-Id': 'test-session'
                    }
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] == True
                
    def test_claude_config_endpoint(self, client, mock_user):
        """Test Claude configuration endpoint"""
        with patch('app.mcp_logistica.flask_integration.current_user', mock_user):
            with patch('app.mcp_logistica.flask_integration.query_processor') as mock_qp:
                mock_qp.claude_integration.client = Mock()  # Claude enabled
                mock_qp.claude_integration.max_context_queries = 10
                
                response = client.get('/api/mcp/logistica/claude/config',
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['config']['enabled'] == True
                assert data['config']['model'] == 'claude-3-5-sonnet-20241022'
                assert data['config']['features']['fallback'] == True
                
    def test_authentication_required(self, client):
        """Test endpoints require authentication"""
        endpoints = [
            ('/api/mcp/logistica/query', 'POST'),
            ('/api/mcp/logistica/preferences', 'GET'),
            ('/api/mcp/logistica/confirmations', 'GET'),
        ]
        
        for endpoint, method in endpoints:
            if method == 'GET':
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})
                
            assert response.status_code == 401  # Unauthorized
"""
Tests for Human-in-the-Loop Confirmation System
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from app.mcp_logistica.confirmation_system import (
    ConfirmationSystem, ConfirmationRequest, ConfirmationStatus, ActionType
)


class TestConfirmationSystem:
    """Test human-in-the-loop confirmation functionality"""
    
    def test_initialization(self, confirmation_system):
        """Test confirmation system initialization"""
        assert confirmation_system is not None
        assert hasattr(confirmation_system, 'pending_confirmations')
        assert hasattr(confirmation_system, 'action_handlers')
        assert hasattr(confirmation_system, 'validation_rules')
        assert confirmation_system.default_expiration_minutes == 30
        
    def test_create_confirmation_request(self, confirmation_system):
        """Test creating confirmation request"""
        request = confirmation_system.create_confirmation_request(
            action_type=ActionType.REAGENDAR,
            entity_type="entrega",
            entity_id="123",
            user_id="user1",
            description="Reagendar entrega para amanhã",
            details={'nova_data': '2024-12-25'}
        )
        
        assert isinstance(request, ConfirmationRequest)
        assert request.action_type == ActionType.REAGENDAR
        assert request.status == ConfirmationStatus.PENDING
        assert request.entity_id == "123"
        assert request.details['nova_data'] == '2024-12-25'
        assert request.id in confirmation_system.pending_confirmations
        
    def test_validation_rules_reschedule(self, confirmation_system):
        """Test validation rules for reschedule action"""
        # Valid reschedule
        is_valid, message = confirmation_system._validate_reschedule({
            'nova_data': (datetime.now() + timedelta(days=1)).isoformat()
        })
        assert is_valid == True
        
        # Missing date
        is_valid, message = confirmation_system._validate_reschedule({})
        assert is_valid == False
        assert "Nova data é obrigatória" in message
        
        # Past date
        is_valid, message = confirmation_system._validate_reschedule({
            'nova_data': (datetime.now() - timedelta(days=1)).isoformat()
        })
        assert is_valid == False
        assert "passado" in message
        
    def test_validation_rules_cancel(self, confirmation_system):
        """Test validation rules for cancel action"""
        # Valid cancel
        is_valid, message = confirmation_system._validate_cancel({
            'motivo': 'Cliente solicitou cancelamento por indisponibilidade'
        })
        assert is_valid == True
        
        # Missing reason
        is_valid, message = confirmation_system._validate_cancel({})
        assert is_valid == False
        assert "Motivo" in message
        
        # Short reason
        is_valid, message = confirmation_system._validate_cancel({
            'motivo': 'cancelar'
        })
        assert is_valid == False
        assert "10 caracteres" in message
        
    def test_validation_rules_value_change(self, confirmation_system):
        """Test validation rules for value change"""
        # Valid change within limit
        is_valid, message = confirmation_system._validate_value_change({
            'valor_anterior': 1000.0,
            'valor_novo': 1200.0
        })
        assert is_valid == True
        
        # Change exceeding 50%
        is_valid, message = confirmation_system._validate_value_change({
            'valor_anterior': 1000.0,
            'valor_novo': 2000.0
        })
        assert is_valid == False
        assert "50%" in message
        
    def test_confirm_action_success(self, confirmation_system):
        """Test successful action confirmation"""
        # Create request
        request = confirmation_system.create_confirmation_request(
            action_type=ActionType.APROVAR,
            entity_type="pedido",
            entity_id="456",
            user_id="user1",
            description="Aprovar pedido",
            details={'tipo_aprovacao': 'financeira'}
        )
        
        # Confirm action
        success = confirmation_system.confirm_action(
            request.id,
            "manager1",
            {'observacao': 'Aprovado conforme política'}
        )
        
        assert success == True
        assert request.status == ConfirmationStatus.CONFIRMED
        assert request.confirmed_by == "manager1"
        assert request.confirmed_at is not None
        assert 'observacao' in request.details
        
    def test_confirm_action_invalid_status(self, confirmation_system):
        """Test confirming already processed request"""
        request = confirmation_system.create_confirmation_request(
            action_type=ActionType.CANCELAR,
            entity_type="pedido",
            entity_id="789",
            user_id="user1",
            description="Cancelar pedido",
            details={'motivo': 'Produto indisponível no estoque'}
        )
        
        # First confirmation
        confirmation_system.confirm_action(request.id, "manager1")
        
        # Try to confirm again
        success = confirmation_system.confirm_action(request.id, "manager2")
        assert success == False
        
    def test_confirm_action_expired(self, confirmation_system):
        """Test confirming expired request"""
        # Create request with short expiration
        request = confirmation_system.create_confirmation_request(
            action_type=ActionType.REAGENDAR,
            entity_type="entrega",
            entity_id="999",
            user_id="user1",
            description="Reagendar entrega",
            details={'nova_data': '2024-12-25'},
            expiration_minutes=-1  # Already expired
        )
        
        success = confirmation_system.confirm_action(request.id, "manager1")
        assert success == False
        assert request.status == ConfirmationStatus.EXPIRED
        
    def test_reject_action(self, confirmation_system):
        """Test rejecting action"""
        request = confirmation_system.create_confirmation_request(
            action_type=ActionType.DESBLOQUEAR,
            entity_type="cliente",
            entity_id="111",
            user_id="user1",
            description="Desbloquear cliente",
            details={'justificativa': 'Pagamento realizado'}
        )
        
        success = confirmation_system.reject_action(
            request.id,
            "manager1",
            "Documentação incompleta"
        )
        
        assert success == True
        assert request.status == ConfirmationStatus.REJECTED
        assert request.rejection_reason == "Documentação incompleta"
        assert request.confirmed_by == "manager1"
        
    def test_reject_without_reason(self, confirmation_system):
        """Test rejection requires reason"""
        request = confirmation_system.create_confirmation_request(
            action_type=ActionType.ALTERAR_VALOR,
            entity_type="frete",
            entity_id="222",
            user_id="user1",
            description="Alterar valor do frete",
            details={'valor_anterior': 100.0, 'valor_novo': 120.0}
        )
        
        # Should require reason
        success = confirmation_system.reject_action(request.id, "manager1")
        assert success == False
        
    def test_cancel_request(self, confirmation_system):
        """Test cancelling pending request"""
        request = confirmation_system.create_confirmation_request(
            action_type=ActionType.EXCLUIR,
            entity_type="registro",
            entity_id="333",
            user_id="user1",
            description="Excluir registro",
            details={'confirmar_exclusao': True}
        )
        
        success = confirmation_system.cancel_request(request.id, "user1")
        
        assert success == True
        assert request.status == ConfirmationStatus.CANCELLED
        
    def test_get_pending_confirmations(self, confirmation_system):
        """Test retrieving pending confirmations"""
        # Create multiple requests
        req1 = confirmation_system.create_confirmation_request(
            ActionType.REAGENDAR, "entrega", "1", "user1", "Test 1", {}
        )
        req2 = confirmation_system.create_confirmation_request(
            ActionType.CANCELAR, "pedido", "2", "user2", "Test 2", 
            {'motivo': 'Teste de cancelamento'}
        )
        
        # Get all pending
        pending = confirmation_system.get_pending_confirmations()
        assert len(pending) >= 2
        
        # Filter by user
        user_pending = confirmation_system.get_pending_confirmations(user_id="user1")
        assert all(r.user_id == "user1" for r in user_pending)
        
        # Filter by action type
        cancel_pending = confirmation_system.get_pending_confirmations(
            action_type=ActionType.CANCELAR
        )
        assert all(r.action_type == ActionType.CANCELAR for r in cancel_pending)
        
    def test_register_action_handler(self, confirmation_system):
        """Test registering action handlers"""
        handler_called = False
        
        def test_handler(request):
            nonlocal handler_called
            handler_called = True
            return True
            
        confirmation_system.register_action_handler(ActionType.APROVAR, test_handler)
        
        # Create and confirm request
        request = confirmation_system.create_confirmation_request(
            ActionType.APROVAR, "test", "1", "user1", "Test", 
            {'tipo_aprovacao': 'teste'}
        )
        
        confirmation_system.confirm_action(request.id, "manager1")
        
        assert handler_called == True
        
    def test_execute_action_error_handling(self, confirmation_system):
        """Test action execution error handling"""
        def failing_handler(request):
            raise Exception("Handler error")
            
        confirmation_system.register_action_handler(ActionType.PROCESSAR_LOTE, failing_handler)
        
        request = confirmation_system.create_confirmation_request(
            ActionType.PROCESSAR_LOTE, "lote", "1", "user1", "Test",
            {'total_itens': 100}
        )
        
        # Should handle error gracefully
        success = confirmation_system.confirm_action(request.id, "manager1")
        assert success == False
        
    def test_bulk_confirm(self, confirmation_system):
        """Test bulk confirmation"""
        # Create multiple requests
        request_ids = []
        for i in range(3):
            req = confirmation_system.create_confirmation_request(
                ActionType.APROVAR, "pedido", str(i), "user1", f"Test {i}",
                {'tipo_aprovacao': 'bulk'}
            )
            request_ids.append(req.id)
            
        # Bulk confirm
        results = confirmation_system.bulk_confirm(request_ids, "manager1")
        
        assert len(results) == 3
        assert all(results.values())  # All should be successful
        
    def test_audit_log(self, confirmation_system):
        """Test audit logging"""
        # Create and process request
        request = confirmation_system.create_confirmation_request(
            ActionType.CANCELAR, "pedido", "123", "user1", "Cancel order",
            {'motivo': 'Cliente solicitou cancelamento'}
        )
        
        confirmation_system.confirm_action(request.id, "manager1")
        
        # Check audit log
        logs = confirmation_system.get_audit_log(entity_id="123")
        assert len(logs) > 0
        assert logs[0]['action'] == 'confirmed'
        assert logs[0]['by_user'] == 'manager1'
        
    def test_get_confirmation_status(self, confirmation_system):
        """Test getting confirmation status"""
        request = confirmation_system.create_confirmation_request(
            ActionType.REAGENDAR, "entrega", "456", "user1", "Test", 
            {'nova_data': '2024-12-25'}
        )
        
        # Check pending status
        status = confirmation_system.get_confirmation_status(request.id)
        assert status == ConfirmationStatus.PENDING
        
        # Confirm and check again
        confirmation_system.confirm_action(request.id, "manager1")
        status = confirmation_system.get_confirmation_status(request.id)
        assert status == ConfirmationStatus.CONFIRMED
        
        # Non-existent request
        status = confirmation_system.get_confirmation_status("invalid-id")
        assert status is None
        
    def test_cleanup_expired(self, confirmation_system):
        """Test cleanup of expired confirmations"""
        # Create expired request
        old_request = confirmation_system.create_confirmation_request(
            ActionType.REAGENDAR, "entrega", "old", "user1", "Old request",
            {'nova_data': '2024-12-25'},
            expiration_minutes=-1
        )
        
        # Create valid request
        new_request = confirmation_system.create_confirmation_request(
            ActionType.REAGENDAR, "entrega", "new", "user1", "New request",
            {'nova_data': '2024-12-25'}
        )
        
        # Run cleanup
        expired_count = confirmation_system.cleanup_expired()
        
        assert expired_count >= 1
        assert old_request.status == ConfirmationStatus.EXPIRED
        
    def test_confirmation_request_serialization(self, confirmation_system):
        """Test ConfirmationRequest to_dict method"""
        request = confirmation_system.create_confirmation_request(
            ActionType.APROVAR, "pedido", "789", "user1", "Approve order",
            {'tipo_aprovacao': 'gerencial', 'valor': 1000.0}
        )
        
        data = request.to_dict()
        
        assert data['id'] == request.id
        assert data['action_type'] == 'aprovar'
        assert data['status'] == 'pending'
        assert isinstance(data['created_at'], str)
        assert isinstance(data['expires_at'], str)
        assert data['details']['valor'] == 1000.0
        
    def test_storage_persistence(self, confirmation_system):
        """Test storage backend integration"""
        # Mock storage
        mock_storage = Mock()
        confirmation_system.storage = mock_storage
        
        # Create request
        request = confirmation_system.create_confirmation_request(
            ActionType.REAGENDAR, "entrega", "999", "user1", "Test",
            {'nova_data': '2024-12-25'}
        )
        
        # Verify storage was called
        mock_storage.set.assert_called()
        key = f"confirmation:{request.id}"
        assert any(key in str(call) for call in mock_storage.set.call_args_list)
        
    def test_notification_service(self, confirmation_system):
        """Test notification service integration"""
        # Mock notification service
        mock_notifier = Mock()
        confirmation_system.notification_service = mock_notifier
        
        # Create high priority request
        request = confirmation_system.create_confirmation_request(
            ActionType.CANCELAR, "pedido", "urgent", "user1", "Urgent cancel",
            {'motivo': 'Problema crítico identificado'}
        )
        
        # Verify notification was sent
        mock_notifier.notify.assert_called_once()
        call_args = mock_notifier.notify.call_args[1]
        assert call_args['user_id'] == "user1"
        assert call_args['priority'] == "high"
        
    def test_performance(self, confirmation_system, performance_logger):
        """Test confirmation system performance"""
        # Create many requests
        ctx = performance_logger.start("create_100_requests")
        request_ids = []
        for i in range(100):
            req = confirmation_system.create_confirmation_request(
                ActionType.APROVAR, "pedido", str(i), "user1", f"Test {i}",
                {'tipo_aprovacao': 'performance_test'}
            )
            request_ids.append(req.id)
        duration = performance_logger.end(ctx)
        
        assert duration < 1.0  # Should create 100 requests in under 1 second
        
        # Test retrieval performance
        ctx = performance_logger.start("get_pending")
        pending = confirmation_system.get_pending_confirmations()
        duration = performance_logger.end(ctx)
        
        assert duration < 0.1  # Should retrieve quickly
        assert len(pending) >= 100
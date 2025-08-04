"""
Sistema de confirmação human-in-the-loop para ações críticas
"""

import uuid
import logging
from typing import Dict, Optional, List, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Tipos de ações que requerem confirmação"""
    REAGENDAR = "reagendar"
    CANCELAR = "cancelar"
    APROVAR = "aprovar"
    DESBLOQUEAR = "desbloquear"
    ALTERAR_VALOR = "alterar_valor"
    EXCLUIR = "excluir"
    PROCESSAR_LOTE = "processar_lote"

class ConfirmationStatus(Enum):
    """Status de uma confirmação"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

@dataclass
class ConfirmationRequest:
    """Requisição de confirmação"""
    id: str
    action_type: ActionType
    entity_type: str
    entity_id: str
    user_id: str
    description: str
    details: Dict
    created_at: datetime
    expires_at: datetime
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    callback_data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        data = asdict(self)
        data['action_type'] = self.action_type.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        if self.confirmed_at:
            data['confirmed_at'] = self.confirmed_at.isoformat()
        return data

class ConfirmationSystem:
    """Sistema de confirmação human-in-the-loop"""
    
    def __init__(self, storage_backend=None, notification_service=None):
        self.storage = storage_backend
        self.notification_service = notification_service
        self.pending_confirmations = {}
        self.action_handlers = {}
        self.validation_rules = {}
        self.audit_log = []
        
        # Configurações padrão
        self.default_expiration_minutes = 30
        self.require_reason_for_rejection = True
        self.allow_bulk_confirmations = True
        
        # Inicializa regras de validação padrão
        self._initialize_validation_rules()
        
    def _initialize_validation_rules(self):
        """Inicializa regras de validação para cada tipo de ação"""
        self.validation_rules = {
            ActionType.REAGENDAR: self._validate_reschedule,
            ActionType.CANCELAR: self._validate_cancel,
            ActionType.APROVAR: self._validate_approve,
            ActionType.DESBLOQUEAR: self._validate_unblock,
            ActionType.ALTERAR_VALOR: self._validate_value_change,
            ActionType.EXCLUIR: self._validate_delete,
            ActionType.PROCESSAR_LOTE: self._validate_batch_process
        }
        
    def create_confirmation_request(
        self,
        action_type: ActionType,
        entity_type: str,
        entity_id: str,
        user_id: str,
        description: str,
        details: Dict,
        expiration_minutes: Optional[int] = None,
        callback_data: Optional[Dict] = None
    ) -> ConfirmationRequest:
        """Cria uma nova requisição de confirmação"""
        
        # Valida a ação
        is_valid, validation_message = self._validate_action(action_type, details)
        if not is_valid:
            raise ValueError(f"Ação inválida: {validation_message}")
        
        # Gera ID único
        request_id = str(uuid.uuid4())
        
        # Define expiração
        expiration = expiration_minutes or self.default_expiration_minutes
        expires_at = datetime.now() + timedelta(minutes=expiration)
        
        # Cria requisição
        request = ConfirmationRequest(
            id=request_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            description=description,
            details=details,
            created_at=datetime.now(),
            expires_at=expires_at,
            callback_data=callback_data
        )
        
        # Armazena
        self.pending_confirmations[request_id] = request
        
        # Persiste se possível
        if self.storage:
            self._persist_request(request)
            
        # Notifica usuário se serviço disponível
        if self.notification_service:
            self._send_notification(request)
            
        # Log
        logger.info(f"Confirmação criada: {request_id} - {action_type.value} para {entity_type} {entity_id}")
        
        return request
        
    def _validate_action(self, action_type: ActionType, details: Dict) -> tuple[bool, str]:
        """Valida se a ação pode ser executada"""
        validator = self.validation_rules.get(action_type)
        
        if validator:
            return validator(details)
        
        return True, "OK"
        
    def _validate_reschedule(self, details: Dict) -> tuple[bool, str]:
        """Valida reagendamento"""
        if 'nova_data' not in details:
            return False, "Nova data é obrigatória"
            
        try:
            nova_data = datetime.fromisoformat(details['nova_data'])
            if nova_data < datetime.now():
                return False, "Nova data não pode ser no passado"
        except:
            return False, "Data inválida"
            
        return True, "OK"
        
    def _validate_cancel(self, details: Dict) -> tuple[bool, str]:
        """Valida cancelamento"""
        if 'motivo' not in details:
            return False, "Motivo do cancelamento é obrigatório"
            
        if len(details['motivo']) < 10:
            return False, "Motivo deve ter pelo menos 10 caracteres"
            
        return True, "OK"
        
    def _validate_approve(self, details: Dict) -> tuple[bool, str]:
        """Valida aprovação"""
        if 'tipo_aprovacao' not in details:
            return False, "Tipo de aprovação é obrigatório"
            
        return True, "OK"
        
    def _validate_unblock(self, details: Dict) -> tuple[bool, str]:
        """Valida desbloqueio"""
        if 'justificativa' not in details:
            return False, "Justificativa é obrigatória"
            
        return True, "OK"
        
    def _validate_value_change(self, details: Dict) -> tuple[bool, str]:
        """Valida alteração de valor"""
        if 'valor_anterior' not in details or 'valor_novo' not in details:
            return False, "Valores anterior e novo são obrigatórios"
            
        try:
            anterior = float(details['valor_anterior'])
            novo = float(details['valor_novo'])
            
            # Valida diferença máxima (exemplo: 50%)
            if abs(novo - anterior) / anterior > 0.5:
                return False, "Alteração excede 50% do valor original"
        except:
            return False, "Valores inválidos"
            
        return True, "OK"
        
    def _validate_delete(self, details: Dict) -> tuple[bool, str]:
        """Valida exclusão"""
        if 'confirmar_exclusao' not in details or not details['confirmar_exclusao']:
            return False, "Confirmação de exclusão é obrigatória"
            
        return True, "OK"
        
    def _validate_batch_process(self, details: Dict) -> tuple[bool, str]:
        """Valida processamento em lote"""
        if 'total_itens' not in details:
            return False, "Total de itens é obrigatório"
            
        if details['total_itens'] > 1000:
            return False, "Lote excede limite de 1000 itens"
            
        return True, "OK"
        
    def confirm_action(
        self,
        request_id: str,
        confirmed_by: str,
        confirmation_details: Optional[Dict] = None
    ) -> bool:
        """Confirma uma ação pendente"""
        request = self.pending_confirmations.get(request_id)
        
        if not request:
            logger.error(f"Requisição não encontrada: {request_id}")
            return False
            
        if request.status != ConfirmationStatus.PENDING:
            logger.warning(f"Requisição {request_id} não está pendente: {request.status}")
            return False
            
        if datetime.now() > request.expires_at:
            request.status = ConfirmationStatus.EXPIRED
            logger.warning(f"Requisição {request_id} expirou")
            return False
            
        # Confirma
        request.status = ConfirmationStatus.CONFIRMED
        request.confirmed_by = confirmed_by
        request.confirmed_at = datetime.now()
        
        # Adiciona detalhes de confirmação se fornecidos
        if confirmation_details:
            request.details.update(confirmation_details)
            
        # Executa ação se handler registrado
        success = self._execute_action(request)
        
        # Persiste
        if self.storage:
            self._persist_request(request)
            
        # Audit log
        self._log_action(request, "confirmed", confirmed_by)
        
        logger.info(f"Ação confirmada: {request_id} por {confirmed_by}")
        
        return success
        
    def reject_action(
        self,
        request_id: str,
        rejected_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """Rejeita uma ação pendente"""
        request = self.pending_confirmations.get(request_id)
        
        if not request:
            logger.error(f"Requisição não encontrada: {request_id}")
            return False
            
        if request.status != ConfirmationStatus.PENDING:
            logger.warning(f"Requisição {request_id} não está pendente: {request.status}")
            return False
            
        if self.require_reason_for_rejection and not reason:
            logger.error("Motivo da rejeição é obrigatório")
            return False
            
        # Rejeita
        request.status = ConfirmationStatus.REJECTED
        request.confirmed_by = rejected_by
        request.confirmed_at = datetime.now()
        request.rejection_reason = reason
        
        # Persiste
        if self.storage:
            self._persist_request(request)
            
        # Audit log
        self._log_action(request, "rejected", rejected_by, reason)
        
        logger.info(f"Ação rejeitada: {request_id} por {rejected_by}")
        
        return True
        
    def cancel_request(self, request_id: str, cancelled_by: str) -> bool:
        """Cancela uma requisição pendente"""
        request = self.pending_confirmations.get(request_id)
        
        if not request:
            return False
            
        if request.status != ConfirmationStatus.PENDING:
            return False
            
        request.status = ConfirmationStatus.CANCELLED
        request.confirmed_by = cancelled_by
        request.confirmed_at = datetime.now()
        
        # Persiste
        if self.storage:
            self._persist_request(request)
            
        # Audit log
        self._log_action(request, "cancelled", cancelled_by)
        
        return True
        
    def get_pending_confirmations(
        self,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        action_type: Optional[ActionType] = None
    ) -> List[ConfirmationRequest]:
        """Obtém confirmações pendentes com filtros opcionais"""
        pending = []
        
        for request in self.pending_confirmations.values():
            if request.status != ConfirmationStatus.PENDING:
                continue
                
            if datetime.now() > request.expires_at:
                request.status = ConfirmationStatus.EXPIRED
                continue
                
            # Aplica filtros
            if user_id and request.user_id != user_id:
                continue
                
            if entity_type and request.entity_type != entity_type:
                continue
                
            if action_type and request.action_type != action_type:
                continue
                
            pending.append(request)
            
        return pending
        
    def register_action_handler(
        self,
        action_type: ActionType,
        handler: Callable[[ConfirmationRequest], bool]
    ):
        """Registra handler para executar ação após confirmação"""
        self.action_handlers[action_type] = handler
        
    def _execute_action(self, request: ConfirmationRequest) -> bool:
        """Executa a ação confirmada"""
        handler = self.action_handlers.get(request.action_type)
        
        if not handler:
            logger.warning(f"Sem handler para ação {request.action_type.value}")
            return True  # Considera sucesso se não há handler
            
        try:
            return handler(request)
        except Exception as e:
            logger.error(f"Erro ao executar ação {request.id}: {str(e)}")
            return False
            
    def get_confirmation_status(self, request_id: str) -> Optional[ConfirmationStatus]:
        """Obtém status de uma confirmação"""
        request = self.pending_confirmations.get(request_id)
        
        if not request:
            # Tenta carregar do storage
            if self.storage:
                request = self._load_request(request_id)
                
        if request:
            # Verifica expiração
            if request.status == ConfirmationStatus.PENDING and datetime.now() > request.expires_at:
                request.status = ConfirmationStatus.EXPIRED
                
            return request.status
            
        return None
        
    def bulk_confirm(
        self,
        request_ids: List[str],
        confirmed_by: str,
        confirmation_details: Optional[Dict] = None
    ) -> Dict[str, bool]:
        """Confirma múltiplas ações de uma vez"""
        if not self.allow_bulk_confirmations:
            raise ValueError("Confirmações em lote não permitidas")
            
        results = {}
        
        for request_id in request_ids:
            success = self.confirm_action(request_id, confirmed_by, confirmation_details)
            results[request_id] = success
            
        return results
        
    def get_audit_log(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action_type: Optional[ActionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Obtém log de auditoria com filtros"""
        filtered_log = []
        
        for entry in self.audit_log:
            # Aplica filtros
            if entity_type and entry.get('entity_type') != entity_type:
                continue
                
            if entity_id and entry.get('entity_id') != entity_id:
                continue
                
            if user_id and entry.get('user_id') != user_id:
                continue
                
            if action_type and entry.get('action_type') != action_type.value:
                continue
                
            if start_date and entry.get('timestamp') < start_date:
                continue
                
            if end_date and entry.get('timestamp') > end_date:
                continue
                
            filtered_log.append(entry)
            
        return filtered_log
        
    def _persist_request(self, request: ConfirmationRequest):
        """Persiste requisição no storage"""
        if self.storage:
            try:
                key = f"confirmation:{request.id}"
                self.storage.set(key, json.dumps(request.to_dict()))
            except Exception as e:
                logger.error(f"Erro ao persistir requisição: {e}")
                
    def _load_request(self, request_id: str) -> Optional[ConfirmationRequest]:
        """Carrega requisição do storage"""
        if self.storage:
            try:
                key = f"confirmation:{request_id}"
                data = self.storage.get(key)
                if data:
                    # Reconstruir objeto a partir do JSON
                    request_data = json.loads(data)
                    # Conversão simplificada - na prática seria mais robusta
                    return ConfirmationRequest(**request_data)
            except Exception as e:
                logger.error(f"Erro ao carregar requisição: {e}")
                
        return None
        
    def _send_notification(self, request: ConfirmationRequest):
        """Envia notificação sobre nova confirmação"""
        if self.notification_service:
            try:
                self.notification_service.notify(
                    user_id=request.user_id,
                    title=f"Confirmação necessária: {request.action_type.value}",
                    message=request.description,
                    action_url=f"/confirmations/{request.id}",
                    priority="high" if request.action_type in [ActionType.CANCELAR, ActionType.EXCLUIR] else "normal"
                )
            except Exception as e:
                logger.error(f"Erro ao enviar notificação: {e}")
                
    def _log_action(self, request: ConfirmationRequest, action: str, by_user: str, reason: Optional[str] = None):
        """Registra ação no log de auditoria"""
        log_entry = {
            'timestamp': datetime.now(),
            'request_id': request.id,
            'action_type': request.action_type.value,
            'entity_type': request.entity_type,
            'entity_id': request.entity_id,
            'user_id': request.user_id,
            'action': action,
            'by_user': by_user,
            'reason': reason,
            'details': request.details
        }
        
        self.audit_log.append(log_entry)
        
        # Persiste log se storage disponível
        if self.storage:
            try:
                log_key = f"audit_log:{datetime.now().strftime('%Y%m%d')}:{request.id}"
                self.storage.set(log_key, json.dumps(log_entry, default=str))
            except Exception as e:
                logger.error(f"Erro ao persistir log: {e}")
                
    def cleanup_expired(self) -> int:
        """Remove confirmações expiradas"""
        expired_count = 0
        
        for request_id in list(self.pending_confirmations.keys()):
            request = self.pending_confirmations[request_id]
            
            if request.status == ConfirmationStatus.PENDING and datetime.now() > request.expires_at:
                request.status = ConfirmationStatus.EXPIRED
                expired_count += 1
                
                # Remove da memória se muito antigo (> 24h)
                if datetime.now() > request.expires_at + timedelta(hours=24):
                    del self.pending_confirmations[request_id]
                    
        logger.info(f"Limpeza: {expired_count} confirmações expiradas")
        
        return expired_count
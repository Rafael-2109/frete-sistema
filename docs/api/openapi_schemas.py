"""
OpenAPI Schema Definitions for Frete Sistema API

This module contains comprehensive Pydantic models and OpenAPI schemas
for all API endpoints, ensuring type safety and auto-documentation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class StatusEmbarque(str, Enum):
    """Status possíveis para embarques"""
    ATIVO = "ativo"
    CANCELADO = "cancelado"
    FINALIZADO = "finalizado"
    EM_TRANSITO = "em_transito"


class StatusAprovacao(str, Enum):
    """Status de aprovação para fretes"""
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    REJEITADO = "rejeitado"
    EM_ANALISE = "em_analise"


class StatusEntrega(str, Enum):
    """Status de entrega no monitoramento"""
    EM_ANDAMENTO = "em_andamento"
    ENTREGUE = "entregue"
    DEVOLVIDO = "devolvido"
    EXTRAVIADO = "extraviado"
    AGUARDANDO_COLETA = "aguardando_coleta"


class TipoCarga(str, Enum):
    """Tipos de carga"""
    SECA = "seca"
    REFRIGERADA = "refrigerada"
    PERIGOSA = "perigosa"
    FRAGIL = "fragil"
    VIVA = "viva"


# ============================================================================
# BASE MODELS
# ============================================================================

class BaseResponse(BaseModel):
    """Base response model for all API endpoints"""
    success: bool = Field(..., description="Indicates if the operation was successful")
    message: Optional[str] = Field(None, description="Optional message about the operation")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (starts at 1)")
    limit: int = Field(10, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Optional error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# ============================================================================
# AUTHENTICATION SCHEMAS
# ============================================================================

class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr = Field(..., description="User email", example="user@example.com")
    password: str = Field(..., min_length=6, description="User password", example="senha123")


class TokenResponse(BaseResponse):
    """JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(3600, description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="Optional refresh token")


class UserInfo(BaseModel):
    """User information schema"""
    id: int = Field(..., description="User ID")
    nome: str = Field(..., description="User name")
    email: EmailStr = Field(..., description="User email")
    is_admin: bool = Field(False, description="Admin status")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# EMBARQUE (SHIPMENT) SCHEMAS
# ============================================================================

class TransportadoraInfo(BaseModel):
    """Basic transportadora information"""
    id: int
    razao_social: str
    cnpj: str
    ativa: bool = True
    
    model_config = ConfigDict(from_attributes=True)


class EmbarqueBase(BaseModel):
    """Base embarque schema"""
    numero: str = Field(..., description="Shipment number", example="EMB-2024-001")
    status: StatusEmbarque = Field(StatusEmbarque.ATIVO, description="Shipment status")
    data_embarque: datetime = Field(..., description="Shipment date")
    transportadora_id: int = Field(..., description="Carrier ID")
    observacoes: Optional[str] = Field(None, description="Optional observations")


class EmbarqueCreate(EmbarqueBase):
    """Schema for creating a new embarque"""
    fretes_ids: Optional[List[int]] = Field(None, description="List of freight IDs to include")


class EmbarqueUpdate(BaseModel):
    """Schema for updating an embarque"""
    status: Optional[StatusEmbarque] = None
    data_embarque: Optional[datetime] = None
    observacoes: Optional[str] = None


class EmbarqueResponse(EmbarqueBase):
    """Embarque response schema"""
    id: int
    transportadora: Optional[TransportadoraInfo] = None
    total_fretes: int = Field(0, description="Total number of freights")
    valor_total: float = Field(0.0, description="Total shipment value")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class EmbarqueListResponse(BaseResponse):
    """List of embarques response"""
    data: List[EmbarqueResponse]
    total: int = Field(..., description="Total number of records")
    page: int = Field(..., description="Current page")
    pages: int = Field(..., description="Total pages")


# ============================================================================
# FRETE (FREIGHT) SCHEMAS
# ============================================================================

class FreteBase(BaseModel):
    """Base frete schema"""
    embarque_id: int = Field(..., description="Associated shipment ID")
    transportadora_id: int = Field(..., description="Carrier ID")
    valor_cotado: float = Field(..., ge=0, description="Quoted freight value")
    valor_aprovado: Optional[float] = Field(None, ge=0, description="Approved value")
    status_aprovacao: StatusAprovacao = Field(StatusAprovacao.PENDENTE)
    numero_cte: Optional[str] = Field(None, description="CT-e number")


class FreteCreate(FreteBase):
    """Schema for creating a new frete"""
    pedido_id: Optional[int] = Field(None, description="Associated order ID")
    observacoes: Optional[str] = None


class FreteUpdate(BaseModel):
    """Schema for updating a frete"""
    valor_aprovado: Optional[float] = None
    status_aprovacao: Optional[StatusAprovacao] = None
    numero_cte: Optional[str] = None
    observacoes: Optional[str] = None


class FreteResponse(FreteBase):
    """Frete response schema"""
    id: int
    embarque_numero: Optional[str] = None
    transportadora: Optional[TransportadoraInfo] = None
    tem_cte: bool = Field(..., description="Indicates if CT-e exists")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class FreteListResponse(BaseResponse):
    """List of fretes response"""
    data: List[FreteResponse]
    total: int
    pending_approval: int = Field(..., description="Number of freights pending approval")
    total_value: float = Field(..., description="Total value of listed freights")


# ============================================================================
# MONITORAMENTO (MONITORING) SCHEMAS
# ============================================================================

class EntregaMonitoradaBase(BaseModel):
    """Base delivery monitoring schema"""
    numero_nf: str = Field(..., description="Invoice number", example="NF-123456")
    cliente: str = Field(..., description="Client name")
    municipio: str = Field(..., description="Delivery city")
    uf: str = Field(..., max_length=2, description="State code", example="SP")
    valor_nf: float = Field(..., ge=0, description="Invoice value")
    pendencia_financeira: bool = Field(False, description="Has financial pending")
    status_finalizacao: StatusEntrega = Field(StatusEntrega.EM_ANDAMENTO)


class EntregaMonitoradaCreate(EntregaMonitoradaBase):
    """Schema for creating monitored delivery"""
    transportadora_id: int
    data_entrega_prevista: Optional[datetime] = None
    observacoes: Optional[str] = None


class EntregaMonitoradaUpdate(BaseModel):
    """Schema for updating monitored delivery"""
    status_finalizacao: Optional[StatusEntrega] = None
    pendencia_financeira: Optional[bool] = None
    data_entrega_real: Optional[datetime] = None
    observacoes: Optional[str] = None


class EntregaMonitoradaResponse(EntregaMonitoradaBase):
    """Monitored delivery response"""
    id: int
    transportadora: Optional[str] = None
    data_faturamento: Optional[datetime] = None
    data_embarque: Optional[datetime] = None
    data_entrega_prevista: Optional[datetime] = None
    data_entrega_real: Optional[datetime] = None
    dias_em_transito: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class MonitoramentoListResponse(BaseResponse):
    """List of monitored deliveries"""
    data: List[EntregaMonitoradaResponse]
    total: int
    entregues: int
    pendencias: int
    em_transito: int


# ============================================================================
# CLIENTE (CLIENT) SCHEMAS
# ============================================================================

class PedidoInfo(BaseModel):
    """Order information"""
    numero: str
    data: str
    cliente: str
    destino: str
    valor: float
    status: str
    nf: Optional[str] = None


class FaturamentoInfo(BaseModel):
    """Billing information"""
    data_fatura: str
    valor_nf: float
    saldo_carteira: float
    status_faturamento: str


class ClienteDetalhado(BaseModel):
    """Detailed client information"""
    pedido: PedidoInfo
    faturamento: Optional[FaturamentoInfo] = None
    monitoramento: Optional[Dict[str, Any]] = None


class ClienteResumo(BaseModel):
    """Client summary"""
    total_pedidos: int
    valor_total: float
    pedidos_faturados: int
    percentual_faturado: float


class ClienteResponse(BaseResponse):
    """Client detailed response"""
    cliente: str
    uf: str
    resumo: ClienteResumo
    data: List[ClienteDetalhado]


# ============================================================================
# ESTATISTICAS (STATISTICS) SCHEMAS
# ============================================================================

class EstatisticasEmbarques(BaseModel):
    """Shipment statistics"""
    total: int
    ativos: int
    cancelados: int
    em_transito: int = 0


class EstatisticasFretes(BaseModel):
    """Freight statistics"""
    total: int
    pendentes_aprovacao: int
    aprovados: int
    rejeitados: int = 0
    percentual_aprovacao: float


class EstatisticasEntregas(BaseModel):
    """Delivery statistics"""
    total_monitoradas: int
    entregues: int
    pendencias_financeiras: int
    percentual_entrega: float
    tempo_medio_entrega: Optional[float] = None


class EstatisticasTransportadoras(BaseModel):
    """Carrier statistics"""
    total: int
    ativas: int
    inativas: int = 0
    melhor_desempenho: Optional[str] = None


class EstatisticasResponse(BaseResponse):
    """System statistics response"""
    periodo_analisado: str
    embarques: EstatisticasEmbarques
    fretes: EstatisticasFretes
    entregas: EstatisticasEntregas
    transportadoras: EstatisticasTransportadoras
    metricas_adicionais: Optional[Dict[str, Any]] = None


# ============================================================================
# MCP (MODEL CONTEXT PROTOCOL) SCHEMAS
# ============================================================================

class MCPAnalyzeRequest(BaseModel):
    """MCP analysis request"""
    query: str = Field(..., description="Natural language query", example="Show me pending shipments")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    include_suggestions: bool = Field(True, description="Include AI suggestions")


class MCPAnalyzeResponse(BaseResponse):
    """MCP analysis response"""
    interpretation: str
    suggested_actions: List[str]
    relevant_data: Dict[str, Any]
    confidence_score: float = Field(..., ge=0, le=1)


class MCPProcessRequest(BaseModel):
    """MCP process request"""
    command: str = Field(..., description="Command to process")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    auto_execute: bool = Field(False, description="Auto-execute if safe")


class MCPProcessResponse(BaseResponse):
    """MCP process response"""
    command_type: str
    executed: bool
    result: Optional[Any] = None
    requires_confirmation: bool = False
    safety_score: float = Field(..., ge=0, le=1)


# ============================================================================
# HEALTH CHECK SCHEMAS
# ============================================================================

class SystemHealth(BaseModel):
    """System health status"""
    database: bool
    cache: bool
    external_apis: bool
    disk_space: float
    memory_usage: float
    cpu_usage: float


class HealthCheckResponse(BaseResponse):
    """Health check response"""
    status: str = Field(..., description="Overall system status")
    environment: str
    version: str
    uptime_seconds: int
    system_health: SystemHealth
    services: Dict[str, bool]


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ValidationError(BaseModel):
    """Validation error detail"""
    field: str
    message: str
    type: str


class ValidationErrorResponse(ErrorResponse):
    """Validation error response"""
    errors: List[ValidationError]


class NotFoundResponse(ErrorResponse):
    """404 Not Found response"""
    error: str = "Resource not found"
    resource_type: Optional[str] = None
    resource_id: Optional[Any] = None


class UnauthorizedResponse(ErrorResponse):
    """401 Unauthorized response"""
    error: str = "Unauthorized"
    error_code: str = "AUTH_REQUIRED"


class ForbiddenResponse(ErrorResponse):
    """403 Forbidden response"""
    error: str = "Forbidden"
    error_code: str = "INSUFFICIENT_PERMISSIONS"
    required_permissions: Optional[List[str]] = None
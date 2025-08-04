"""
Modelos de banco de dados para o sistema MCP Logística
"""

from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

class UserPreference(db.Model):
    """Preferências de usuário para o sistema MCP"""
    __tablename__ = 'mcp_user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    preference_type = db.Column(db.String(50), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(JSON)
    confidence = db.Column(db.Float, default=0.5)
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índice único para evitar duplicatas
    __table_args__ = (
        db.UniqueConstraint('user_id', 'preference_type', 'key', name='uix_user_pref_key'),
    )
    
    # Relacionamento
    user = db.relationship('Usuario', backref='mcp_preferences')
    
    def __repr__(self):
        return f'<UserPreference {self.user_id}:{self.key}>'

class ConfirmationRequest(db.Model):
    """Requisições de confirmação human-in-the-loop"""
    __tablename__ = 'mcp_confirmation_requests'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    action_type = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    details = db.Column(JSON)
    status = db.Column(db.String(20), default='pending')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    confirmed_at = db.Column(db.DateTime)
    
    # Confirmação
    confirmed_by = db.Column(db.String(100))
    rejection_reason = db.Column(db.Text)
    callback_data = db.Column(JSON)
    
    # Índices
    __table_args__ = (
        db.Index('ix_mcp_conf_status', 'status'),
        db.Index('ix_mcp_conf_user', 'user_id', 'status'),
        db.Index('ix_mcp_conf_entity', 'entity_type', 'entity_id'),
    )
    
    # Relacionamento
    user = db.relationship('Usuario', backref='mcp_confirmations')
    
    def __repr__(self):
        return f'<ConfirmationRequest {self.id}:{self.action_type}>'

class QueryHistory(db.Model):
    """Histórico de consultas para análise e aprendizado"""
    __tablename__ = 'mcp_query_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    # Dados da consulta
    original_query = db.Column(db.Text, nullable=False)
    normalized_query = db.Column(db.Text)
    intent = db.Column(db.String(50))
    confidence = db.Column(db.Float)
    entities = db.Column(JSON)
    context = db.Column(JSON)
    
    # Resultado
    success = db.Column(db.Boolean, default=True)
    error_code = db.Column(db.String(50))
    error_message = db.Column(db.Text)
    result_count = db.Column(db.Integer)
    response_time_ms = db.Column(db.Integer)
    
    # SQL gerado (para debug)
    generated_sql = db.Column(db.Text)
    
    # Feedback
    user_feedback = db.Column(db.String(20))  # positive, negative, neutral
    feedback_comment = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Índices
    __table_args__ = (
        db.Index('ix_mcp_query_user_date', 'user_id', 'created_at'),
        db.Index('ix_mcp_query_intent', 'intent'),
    )
    
    # Relacionamento
    user = db.relationship('Usuario', backref='mcp_queries')
    
    def __repr__(self):
        return f'<QueryHistory {self.id}:{self.intent}>'

class EntityMapping(db.Model):
    """Mapeamento de entidades para resolução dinâmica"""
    __tablename__ = 'mcp_entity_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False)  # cliente, transportadora, etc
    
    # Identificadores
    reference = db.Column(db.String(255), nullable=False)  # Nome ou referência usada
    canonical_name = db.Column(db.String(255), nullable=False)  # Nome canônico/oficial
    entity_id = db.Column(db.String(50))  # ID da entidade no sistema
    
    # Dados adicionais
    cnpj_root = db.Column(db.String(8))  # Raiz do CNPJ para agrupamento
    variations = db.Column(JSON)  # Lista de variações conhecidas
    entity_metadata = db.Column(JSON)  # Metadados adicionais
    
    # Controle
    confidence = db.Column(db.Float, default=1.0)
    usage_count = db.Column(db.Integer, default=0)
    auto_detected = db.Column(db.Boolean, default=False)
    verified = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    
    # Índices
    __table_args__ = (
        db.Index('ix_mcp_entity_type_ref', 'entity_type', 'reference'),
        db.Index('ix_mcp_entity_cnpj', 'cnpj_root'),
        db.UniqueConstraint('entity_type', 'reference', name='uix_entity_reference'),
    )
    
    def __repr__(self):
        return f'<EntityMapping {self.entity_type}:{self.reference}>'

class LearningPattern(db.Model):
    """Padrões aprendidos pelo sistema"""
    __tablename__ = 'mcp_learning_patterns'
    
    id = db.Column(db.Integer, primary_key=True)
    pattern_type = db.Column(db.String(50), nullable=False)  # query, entity, intent, etc
    pattern_key = db.Column(db.String(255), nullable=False)
    pattern_value = db.Column(JSON, nullable=False)
    
    # Estatísticas
    occurrence_count = db.Column(db.Integer, default=1)
    success_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)
    confidence = db.Column(db.Float, default=0.5)
    
    # Controle
    active = db.Column(db.Boolean, default=True)
    auto_learned = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_occurred = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índices
    __table_args__ = (
        db.Index('ix_mcp_pattern_type_key', 'pattern_type', 'pattern_key'),
        db.Index('ix_mcp_pattern_confidence', 'confidence'),
    )
    
    def __repr__(self):
        return f'<LearningPattern {self.pattern_type}:{self.pattern_key}>'

class ErrorLog(db.Model):
    """Log de erros para análise e melhoria"""
    __tablename__ = 'mcp_error_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    error_code = db.Column(db.String(50), nullable=False)
    error_category = db.Column(db.String(50), nullable=False)
    error_severity = db.Column(db.String(20), nullable=False)
    error_message = db.Column(db.Text, nullable=False)
    
    # Contexto
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    query_id = db.Column(db.Integer, db.ForeignKey('mcp_query_history.id'))
    endpoint = db.Column(db.String(100))
    request_data = db.Column(JSON)
    
    # Detalhes técnicos
    stack_trace = db.Column(db.Text)
    recovery_suggestions = db.Column(JSON)
    
    # Resolution
    resolved = db.Column(db.Boolean, default=False)
    resolution_notes = db.Column(db.Text)
    resolved_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Índices
    __table_args__ = (
        db.Index('ix_mcp_error_code_date', 'error_code', 'created_at'),
        db.Index('ix_mcp_error_category', 'error_category'),
        db.Index('ix_mcp_error_severity', 'error_severity'),
    )
    
    # Relacionamentos
    user = db.relationship('Usuario', backref='mcp_errors')
    query = db.relationship('QueryHistory', backref='errors')
    
    def __repr__(self):
        return f'<ErrorLog {self.id}:{self.error_code}>'

# Função para criar as tabelas
def create_mcp_tables():
    """Cria as tabelas do MCP no banco de dados"""
    db.create_all()
    print("Tabelas MCP criadas com sucesso!")

# Função para popular dados iniciais
def seed_initial_data():
    """Popula dados iniciais para o MCP"""
    # Exemplo: adicionar mapeamentos de entidades comuns
    mappings = [
        {
            'entity_type': 'status',
            'reference': 'atrasado',
            'canonical_name': 'ATRASADO',
            'variations': ['atrasada', 'em atraso', 'vencido', 'vencida']
        },
        {
            'entity_type': 'status',
            'reference': 'entregue',
            'canonical_name': 'ENTREGUE',
            'variations': ['entregado', 'finalizado', 'concluído']
        },
        {
            'entity_type': 'status',
            'reference': 'pendente',
            'canonical_name': 'PENDENTE',
            'variations': ['aguardando', 'em espera', 'a fazer']
        }
    ]
    
    for mapping_data in mappings:
        mapping = EntityMapping.query.filter_by(
            entity_type=mapping_data['entity_type'],
            reference=mapping_data['reference']
        ).first()
        
        if not mapping:
            mapping = EntityMapping(**mapping_data)
            db.session.add(mapping)
            
    db.session.commit()
    print("Dados iniciais populados!")
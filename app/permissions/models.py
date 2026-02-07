"""
Sistema Unificado de Permissões
================================

Modelo único e otimizado para gerenciamento hierárquico de permissões.
Elimina toda duplicidade e unifica os dois sistemas existentes.

Hierarquia: Categoria → Módulo → Submódulo
Tipos: view / edit / delete / export
Herança e sobrescrita de permissões
"""

from app import db
from datetime import datetime
from app.utils.timezone import agora_utc_naive
from sqlalchemy import Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSON
import logging
import json

logger = logging.getLogger(__name__)

# ============================================================================
# 1. CATEGORIAS DE PERMISSÃO (Nível Superior)
# ============================================================================

class PermissionCategory(db.Model):
    """
    Categorias agrupam módulos relacionados
    Ex: Operacional, Financeiro, Administrativo
    """
    __tablename__ = 'permission_category'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    nome_exibicao = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    icone = db.Column(db.String(50), default='folder')
    cor = db.Column(db.String(7), default='#007bff')
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    modules = db.relationship('PermissionModule', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PermissionCategory {self.nome}>'

# ============================================================================
# 2. MÓDULOS DE PERMISSÃO (Nível Intermediário)
# ============================================================================

class PermissionModule(db.Model):
    """
    Módulos dentro de categorias
    Ex: Faturamento, Carteira, Embarques
    """
    __tablename__ = 'permission_module'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('permission_category.id'), nullable=False)
    nome = db.Column(db.String(50), nullable=False)
    nome_exibicao = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    icone = db.Column(db.String(50), default='file')
    cor = db.Column(db.String(7), default='#6c757d')
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    submodules = db.relationship('PermissionSubModule', backref='module', lazy='dynamic', cascade='all, delete-orphan')
    
    # Índices
    __table_args__ = (
        UniqueConstraint('category_id', 'nome', name='uq_module_category_name'),
        Index('idx_module_category', 'category_id', 'ativo'),
    )
    
    def __repr__(self):
        return f'<PermissionModule {self.category.nome}.{self.nome}>'

# ============================================================================
# 3. SUBMÓDULOS DE PERMISSÃO (Nível Detalhado)
# ============================================================================

class PermissionSubModule(db.Model):
    """
    Submódulos são as funções específicas
    Ex: Listar Faturas, Aprovar Pedido, Gerar Relatório
    """
    __tablename__ = 'permission_submodule'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('permission_module.id'), nullable=False)
    nome = db.Column(db.String(50), nullable=False)
    nome_exibicao = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    route_pattern = db.Column(db.String(200), nullable=True)  # Padrão de rota Flask
    critical_level = db.Column(db.String(10), default='NORMAL')  # LOW, NORMAL, HIGH, CRITICAL
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Índices
    __table_args__ = (
        UniqueConstraint('module_id', 'nome', name='uq_submodule_module_name'),
        Index('idx_submodule_module', 'module_id', 'ativo'),
        CheckConstraint("critical_level IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')", name='ck_critical_level')
    )
    
    def __repr__(self):
        return f'<PermissionSubModule {self.module.nome}.{self.nome}>'
    
    @property
    def full_path(self):
        """Retorna caminho completo: categoria.modulo.submodulo"""
        return f"{self.module.category.nome}.{self.module.nome}.{self.nome}"

# ============================================================================
# 4. PERMISSÕES DE USUÁRIO
# ============================================================================

class UserPermission(db.Model):
    """
    Permissões específicas de usuário com referências diretas
    Simplificado para ter apenas submódulo (nível mais específico)
    """
    __tablename__ = 'user_permission'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    submodule_id = db.Column(db.Integer, db.ForeignKey('permission_submodule.id'), nullable=False)
    
    # Permissões
    can_view = db.Column(db.Boolean, default=False, nullable=False)
    can_edit = db.Column(db.Boolean, default=False, nullable=False)
    
    # Controle
    granted_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relacionamentos
    user = db.relationship('Usuario', foreign_keys=[user_id], backref='permissions')
    submodule = db.relationship('PermissionSubModule', backref='user_permissions')
    granted_by_user = db.relationship('Usuario', foreign_keys=[granted_by])
    
    # Índices
    __table_args__ = (
        UniqueConstraint('user_id', 'submodule_id', name='uq_user_submodule_permission'),
        Index('idx_user_permission_active', 'user_id', 'ativo'),
        Index('idx_submodule_permission', 'submodule_id', 'ativo'),
    )
    
    def __repr__(self):
        return f'<UserPermission {self.user_id} -> {self.submodule_id}>'

# ============================================================================
# 5. VENDEDORES E EQUIPES
# ============================================================================

class Vendedor(db.Model):
    """
    Cadastro de vendedores - usuários podem estar vinculados a múltiplos
    """
    __tablename__ = 'vendedor'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    users = db.relationship('UserVendedor', backref='vendedor', lazy='dynamic')
    
    def __repr__(self):
        return f'<Vendedor {self.codigo} - {self.nome}>'

class EquipeVendas(db.Model):
    """
    Equipes de vendas - usuários podem pertencer a múltiplas
    """
    __tablename__ = 'equipe_vendas'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    gerente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    gerente = db.relationship('Usuario', foreign_keys=[gerente_id], backref='equipes_gerenciadas')
    users = db.relationship('UserEquipe', backref='equipe', lazy='dynamic')
    
    def __repr__(self):
        return f'<EquipeVendas {self.codigo} - {self.nome}>'

# ============================================================================
# 6. VÍNCULOS USUÁRIO-VENDEDOR E USUÁRIO-EQUIPE
# ============================================================================

class UserVendedor(db.Model):
    """
    Relacionamento N:N entre usuários e vendedores
    """
    __tablename__ = 'user_vendedor'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor.id'), nullable=False)
    tipo_acesso = db.Column(db.String(20), default='view')  # view, edit, full
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    adicionado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    adicionado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    observacoes = db.Column(db.String(255), nullable=True)
    
    # Relacionamentos
    user = db.relationship('Usuario', foreign_keys=[user_id], backref='vendedores')
    adicionado_por_user = db.relationship('Usuario', foreign_keys=[adicionado_por])
    
    # Índices
    __table_args__ = (
        UniqueConstraint('user_id', 'vendedor_id', name='uq_user_vendedor'),
        Index('idx_user_vendedor_active', 'user_id', 'ativo'),
    )

class UserEquipe(db.Model):
    """
    Relacionamento N:N entre usuários e equipes
    """
    __tablename__ = 'user_equipe'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    equipe_id = db.Column(db.Integer, db.ForeignKey('equipe_vendas.id'), nullable=False)
    cargo_equipe = db.Column(db.String(50), nullable=True)
    tipo_acesso = db.Column(db.String(20), default='member')  # member, supervisor, manager
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    adicionado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    adicionado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    observacoes = db.Column(db.String(255), nullable=True)
    
    # Relacionamentos
    user = db.relationship('Usuario', foreign_keys=[user_id], backref='equipes')
    adicionado_por_user = db.relationship('Usuario', foreign_keys=[adicionado_por])
    
    # Índices
    __table_args__ = (
        UniqueConstraint('user_id', 'equipe_id', name='uq_user_equipe'),
        Index('idx_user_equipe_active', 'user_id', 'ativo'),
    )

# ============================================================================
# 7. PERMISSÕES POR VENDEDOR/EQUIPE (Herança)
# ============================================================================

class VendedorPermission(db.Model):
    """
    Permissões padrão para todos os usuários de um vendedor
    """
    __tablename__ = 'vendedor_permission'
    
    id = db.Column(db.Integer, primary_key=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor.id'), nullable=False)
    submodule_id = db.Column(db.Integer, db.ForeignKey('permission_submodule.id'), nullable=False)
    can_view = db.Column(db.Boolean, default=False, nullable=False)
    can_edit = db.Column(db.Boolean, default=False, nullable=False)
    granted_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relacionamentos
    vendedor = db.relationship('Vendedor', backref='permissions')
    submodule = db.relationship('PermissionSubModule', backref='vendedor_permissions')
    
    # Índices
    __table_args__ = (
        UniqueConstraint('vendedor_id', 'submodule_id', name='uq_vendedor_submodule'),
        Index('idx_vendedor_permission', 'vendedor_id', 'ativo'),
    )

class EquipePermission(db.Model):
    """
    Permissões padrão para todos os membros de uma equipe
    """
    __tablename__ = 'equipe_permission'
    
    id = db.Column(db.Integer, primary_key=True)
    equipe_id = db.Column(db.Integer, db.ForeignKey('equipe_vendas.id'), nullable=False)
    submodule_id = db.Column(db.Integer, db.ForeignKey('permission_submodule.id'), nullable=False)
    can_view = db.Column(db.Boolean, default=False, nullable=False)
    can_edit = db.Column(db.Boolean, default=False, nullable=False)
    granted_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relacionamentos
    equipe = db.relationship('EquipeVendas', backref='permissions')
    submodule = db.relationship('PermissionSubModule', backref='equipe_permissions')
    
    # Índices
    __table_args__ = (
        UniqueConstraint('equipe_id', 'submodule_id', name='uq_equipe_submodule'),
        Index('idx_equipe_permission', 'equipe_id', 'ativo'),
    )

# ============================================================================
# 8. TEMPLATES DE PERMISSÃO
# ============================================================================

class PermissionTemplate(db.Model):
    """
    Templates reutilizáveis de permissões
    """
    __tablename__ = 'permission_template'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    categoria = db.Column(db.String(50), default='custom')  # roles, departments, custom
    template_data = db.Column(JSON, nullable=False)  # Estrutura de permissões
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=agora_utc_naive)
    
    def __repr__(self):
        return f'<PermissionTemplate {self.nome}>'
    
    def apply_to_user(self, user_id, applied_by=None):
        """Aplica este template a um usuário"""
        from app import db
        
        permissions_created = 0
        
        try:
            # Template data should contain submodule_ids directly
            # Format: {submodule_id: {can_view: bool, can_edit: bool}}
            for submodule_id, perms in self.template_data.items():
                # Busca ou cria permissão
                permission = UserPermission.query.filter_by(
                    user_id=user_id,
                    submodule_id=int(submodule_id)
                ).first()
                
                if not permission:
                    permission = UserPermission(
                        user_id=user_id,
                        submodule_id=int(submodule_id),
                        granted_by=applied_by,
                        granted_at=agora_utc_naive()
                    )
                    db.session.add(permission)
                
                # Aplica permissões
                permission.can_view = perms.get('can_view', False)
                permission.can_edit = perms.get('can_edit', False)
                permission.ativo = True
                
                permissions_created += 1
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao aplicar template: {e}")
            db.session.rollback()
            return False

# ============================================================================
# 9. PERFIS DE USUÁRIO
# ============================================================================

class PerfilUsuario(db.Model):
    """
    Perfis flexíveis de usuário
    """
    __tablename__ = 'perfil_usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    nome_exibicao = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    nivel_hierarquico = db.Column(db.Integer, default=0)  # 0=mais baixo, 10=mais alto
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    usuarios = db.relationship('Usuario', backref='perfil_detalhado', lazy='select')
    
    def __repr__(self):
        return f'<PerfilUsuario {self.nome}>'

# ============================================================================
# 10. AUDITORIA
# ============================================================================

class PermissionLog(db.Model):
    """
    Log completo de auditoria para todas as ações de permissão
    """
    __tablename__ = 'permission_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # GRANTED, REVOKED, USED, LOGIN, DENIED
    entity_type = db.Column(db.String(20), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(JSON, nullable=True)  # Detalhes em JSON
    result = db.Column(db.String(20), default='SUCCESS')  # SUCCESS, DENIED, ERROR
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=agora_utc_naive, nullable=False, index=True)
    
    # Relacionamentos
    user = db.relationship('Usuario', backref='permission_logs')
    
    # Índices
    __table_args__ = (
        Index('idx_log_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_log_action_timestamp', 'action', 'timestamp'),
        Index('idx_log_result', 'result', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<PermissionLog {self.action} - {self.user_id}>'
    
    @classmethod
    def log(cls, user_id, action, entity_type=None, entity_id=None, 
            details=None, result='SUCCESS', ip_address=None, 
            user_agent=None, session_id=None):
        """Método conveniente para criar logs"""
        try:
            log = cls(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                result=result,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            logger.error(f"Erro ao criar log: {e}")
            db.session.rollback()
            return None

# ============================================================================
# 11. OPERAÇÕES EM LOTE
# ============================================================================

class BatchOperation(db.Model):
    """
    Registro de operações em lote para auditoria e rollback
    """
    __tablename__ = 'batch_operation'
    
    id = db.Column(db.Integer, primary_key=True)
    operation_type = db.Column(db.String(20), nullable=False)  # GRANT, REVOKE, COPY, TEMPLATE, MIGRATION
    description = db.Column(db.String(255), nullable=True)
    executed_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    affected_users = db.Column(db.Integer, default=0)
    affected_permissions = db.Column(db.Integer, default=0)
    details = db.Column(JSON, nullable=True)
    error_details = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    executor = db.relationship('Usuario', backref='batch_operations')
    
    def __repr__(self):
        return f'<BatchOperation {self.operation_type} - {self.status}>'

# ============================================================================
# 12. CACHE DE PERMISSÕES
# ============================================================================

class PermissionCache(db.Model):
    """
    Cache de permissões para melhor performance
    """
    __tablename__ = 'permission_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    permission_data = db.Column(JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_cache_user', 'user_id'),
        Index('idx_cache_expires', 'expires_at'),
    )
    
    @classmethod
    def clean_expired(cls):
        """Remove entradas expiradas do cache"""
        try:
            cls.query.filter(cls.expires_at < agora_utc_naive()).delete()
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            db.session.rollback()
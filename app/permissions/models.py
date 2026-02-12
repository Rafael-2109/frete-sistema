"""
Sistema de Permissoes - Vendedores, Equipes e Vinculos
======================================================

Models ativos para gestao de vendedores e equipes.

Historico:
  - 2026-02-12: Removidos 10 models deprecated do sistema Permissions v2
    (PermissionCategory, PermissionModule, PermissionSubModule, UserPermission,
     VendedorPermission, EquipePermission, PermissionTemplate, PermissionLog,
     PermissionCache, BatchOperation). Tabelas dropadas via migration.
  - Mantidos: Vendedor, EquipeVendas, UserVendedor, UserEquipe, PerfilUsuario
"""

from app import db
from app.utils.timezone import agora_utc_naive
from sqlalchemy import Index, UniqueConstraint


# ============================================================================
# 1. VENDEDORES
# ============================================================================

class Vendedor(db.Model):
    """
    Cadastro de vendedores - usuarios podem estar vinculados a multiplos
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


# ============================================================================
# 2. EQUIPES DE VENDAS
# ============================================================================

class EquipeVendas(db.Model):
    """
    Equipes de vendas - usuarios podem pertencer a multiplas
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
# 3. VINCULOS USUARIO-VENDEDOR
# ============================================================================

class UserVendedor(db.Model):
    """
    Relacionamento N:N entre usuarios e vendedores
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

    # Indices
    __table_args__ = (
        UniqueConstraint('user_id', 'vendedor_id', name='uq_user_vendedor'),
        Index('idx_user_vendedor_active', 'user_id', 'ativo'),
    )


# ============================================================================
# 4. VINCULOS USUARIO-EQUIPE
# ============================================================================

class UserEquipe(db.Model):
    """
    Relacionamento N:N entre usuarios e equipes
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

    # Indices
    __table_args__ = (
        UniqueConstraint('user_id', 'equipe_id', name='uq_user_equipe'),
        Index('idx_user_equipe_active', 'user_id', 'ativo'),
    )


# ============================================================================
# 5. PERFIS DE USUARIO
# ============================================================================

class PerfilUsuario(db.Model):
    """
    Perfis flexiveis de usuario
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

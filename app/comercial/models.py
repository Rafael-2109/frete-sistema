"""
Modelos para o módulo comercial - Permissões e Logs
====================================================

Este módulo contém os modelos para controle de permissões de vendedores
e logs de auditoria das alterações de permissões.

Autor: Sistema de Fretes
Data: 2025-01-21
"""

from app import db
from datetime import datetime
from app.utils.timezone import agora_utc_naive


class PermissaoComercial(db.Model):
    """
    Modelo para armazenar permissões de vendedores a equipes e vendedores específicos.
    Um usuário pode ter N permissões (relação 1:N).
    """
    __tablename__ = 'permissao_comercial'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'equipe' ou 'vendedor'
    valor = db.Column(db.String(100), nullable=False)  # Nome da equipe ou vendedor

    # Timestamps
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)  # Email do admin que criou

    # Relacionamento
    usuario = db.relationship('Usuario', backref='permissoes_comercial')

    # Índice único para evitar duplicatas
    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'tipo', 'valor', name='_usuario_tipo_valor_uc'),
        db.Index('idx_usuario_tipo', 'usuario_id', 'tipo'),
    )

    def __repr__(self):
        return f'<PermissaoComercial {self.usuario_id} - {self.tipo}: {self.valor}>'


class LogPermissaoComercial(db.Model):
    """
    Modelo para armazenar logs de todas as alterações nas permissões comerciais.
    Mantém histórico completo de quem alterou, quando e o que foi alterado.
    """
    __tablename__ = 'log_permissao_comercial'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)  # Usuário que foi alterado
    admin_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)  # Admin que fez a alteração
    acao = db.Column(db.String(20), nullable=False)  # 'adicionar', 'remover', 'limpar_todas'
    tipo = db.Column(db.String(20), nullable=True)  # 'equipe' ou 'vendedor' (null se for limpar_todas)
    valor = db.Column(db.String(100), nullable=True)  # Nome da equipe ou vendedor (null se for limpar_todas)
    data_hora = db.Column(db.DateTime, default=agora_utc_naive, nullable=False, index=True)

    # Informações adicionais
    ip_address = db.Column(db.String(45), nullable=True)  # IP do admin
    user_agent = db.Column(db.String(500), nullable=True)  # Browser do admin
    observacao = db.Column(db.Text, nullable=True)  # Observações opcionais

    # Relacionamentos
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref='logs_permissao_como_usuario')
    admin = db.relationship('Usuario', foreign_keys=[admin_id], backref='logs_permissao_como_admin')

    # Índices para consultas frequentes
    __table_args__ = (
        db.Index('idx_usuario_data', 'usuario_id', 'data_hora'),
        db.Index('idx_admin_data', 'admin_id', 'data_hora'),
    )

    def __repr__(self):
        return f'<LogPermissaoComercial {self.acao} {self.tipo}:{self.valor} por admin:{self.admin_id}>'

    @property
    def descricao_acao(self):
        """Retorna uma descrição amigável da ação"""
        if self.acao == 'adicionar':
            return f"Adicionou permissão para {self.tipo} '{self.valor}'"
        elif self.acao == 'remover':
            return f"Removeu permissão para {self.tipo} '{self.valor}'"
        elif self.acao == 'limpar_todas':
            return "Limpou todas as permissões"
        return self.acao
"""Permissoes granulares por usuario x modulo do HORA.

Modelo: 1 linha por (usuario, modulo) com 4 flags Ver/Criar/Editar/Apagar.

Default = TUDO BLOQUEADO para usuarios nao-admin sem entry. Admin
(perfil='administrador') passa em qualquer checagem.

NAO usa FK para `usuarios` para manter app/hora independente de app/auth
(mesma decisao usada em Usuario.loja_hora_id em app/auth/models.py).
"""
from __future__ import annotations

from app import db
from app.utils.timezone import agora_utc_naive


# Lista canonica dos modulos com permissoes granulares no HORA.
# Espelha os blueprints/secoes do menu (app/templates/hora/base.html).
# Mantida aqui para que UI e service usem a MESMA fonte de verdade.
MODULOS_HORA: list[tuple[str, str]] = [
    ('usuarios', 'Usuarios'),
    ('dashboard', 'Dashboard'),
    ('lojas', 'Lojas'),
    ('modelos', 'Modelos'),
    ('pedidos', 'Pedidos'),
    ('nfs', 'NFs de Entrada'),
    ('recebimentos', 'Recebimentos'),
    ('estoque', 'Estoque'),
    ('devolucoes', 'Devolucoes'),
    ('pecas', 'Pecas faltando'),
]

ACOES_HORA: list[tuple[str, str]] = [
    ('ver', 'Ver'),
    ('criar', 'Criar'),
    ('editar', 'Editar'),
    ('apagar', 'Apagar'),
    ('aprovar', 'Aprovar'),
]


class HoraUserPermissao(db.Model):
    """Permissao granular por usuario x modulo HORA."""
    __tablename__ = 'hora_user_permissao'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    modulo = db.Column(db.String(40), nullable=False)

    pode_ver = db.Column(db.Boolean, nullable=False, default=False)
    pode_criar = db.Column(db.Boolean, nullable=False, default=False)
    pode_editar = db.Column(db.Boolean, nullable=False, default=False)
    pode_apagar = db.Column(db.Boolean, nullable=False, default=False)
    pode_aprovar = db.Column(db.Boolean, nullable=False, default=False)

    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive,
    )
    atualizado_por_id = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'modulo', name='uq_hora_user_perm_user_mod'),
        db.Index('idx_hora_user_perm_lookup', 'user_id', 'modulo'),
    )

    def __repr__(self) -> str:
        flags = ''.join([
            'V' if self.pode_ver else '-',
            'C' if self.pode_criar else '-',
            'E' if self.pode_editar else '-',
            'A' if self.pode_apagar else '-',
            'P' if self.pode_aprovar else '-',
        ])
        return f'<HoraUserPermissao user={self.user_id} mod={self.modulo} {flags}>'

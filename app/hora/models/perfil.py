"""Perfis de permissao das Lojas HORA.

Um **perfil HORA** e um template de permissoes reutilizavel. Tem duas funcoes:

1. **Identidade**: seu `slug` e gravado em `Usuario.perfil` (campo global, compartilhado
   com os perfis do restante do sistema). O slug carrega prefixo `hora_` e nunca colide
   com os 6 slugs reservados (`PERFIS_SISTEMA_RESERVADOS`) — assim um usuario HORA-only
   nao ganha acesso Nacom por acidente (todas as checagens `perfil in [...]` /
   `perfil == 'administrador'` retornam False para slug desconhecido).

2. **Esqueleto**: `HoraPerfilPermissao` guarda a matriz (modulo x acao) que PRE-PREENCHE
   as permissoes granulares de um usuario ao atribuir/redefinir o perfil. E apenas um
   TEMPLATE — a permissao efetiva continua em `hora_user_permissao` (ver
   `permissao_service.tem_perm`); o perfil NAO e consultado em runtime.

Sem FK para `usuarios` (mantem app/hora independente de app/auth — mesma decisao de
`HoraUserPermissao`). Migration: `scripts/migrations/hora_55_perfis.{py,sql}`.
"""
from __future__ import annotations

from app import db
from app.utils.timezone import agora_utc_naive


# Slugs reservados do restante do sistema (campo Usuario.perfil em app/auth).
# Um perfil HORA NUNCA pode usar um destes (garantido tambem pelo prefixo 'hora_').
# Espelha as choices de app/auth/forms.py + perfil_nome em app/auth/models.py.
PERFIS_SISTEMA_RESERVADOS: frozenset[str] = frozenset({
    'administrador',
    'vendedor',
    'gerente_comercial',
    'financeiro',
    'logistica',
    'portaria',
})

# Prefixo do slug de todo perfil HORA. Garante namespace isolado dos reservados
# e permite identificar visualmente um slug de perfil HORA. VARCHAR(30) em
# Usuario.perfil e hora_perfil.slug acomoda prefixo (5) + 25 chars de nome.
PERFIL_HORA_SLUG_PREFIXO = 'hora_'


class HoraPerfil(db.Model):
    """Definicao de um perfil de permissao HORA (template reutilizavel)."""
    __tablename__ = 'hora_perfil'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(30), nullable=False, unique=True)
    nome = db.Column(db.String(80), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive,
    )
    criado_por_id = db.Column(db.Integer, nullable=True)

    permissoes = db.relationship(
        'HoraPerfilPermissao',
        backref='perfil',
        cascade='all, delete-orphan',
        passive_deletes=True,
        lazy='selectin',
    )

    __table_args__ = (
        db.UniqueConstraint('slug', name='uq_hora_perfil_slug'),
    )

    def __repr__(self) -> str:
        return f'<HoraPerfil {self.slug} ativo={self.ativo}>'


class HoraPerfilPermissao(db.Model):
    """Linha do esqueleto: flags de 1 modulo dentro de 1 perfil HORA."""
    __tablename__ = 'hora_perfil_permissao'

    id = db.Column(db.Integer, primary_key=True)
    perfil_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_perfil.id', ondelete='CASCADE'),
        nullable=False,
    )
    modulo = db.Column(db.String(40), nullable=False)

    pode_ver = db.Column(db.Boolean, nullable=False, default=False)
    pode_criar = db.Column(db.Boolean, nullable=False, default=False)
    pode_editar = db.Column(db.Boolean, nullable=False, default=False)
    pode_apagar = db.Column(db.Boolean, nullable=False, default=False)
    pode_aprovar = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint('perfil_id', 'modulo', name='uq_hora_perfil_perm_perfil_mod'),
        db.Index('idx_hora_perfil_perm_perfil', 'perfil_id'),
    )

    def __repr__(self) -> str:
        flags = ''.join([
            'V' if self.pode_ver else '-',
            'C' if self.pode_criar else '-',
            'E' if self.pode_editar else '-',
            'A' if self.pode_apagar else '-',
            'P' if self.pode_aprovar else '-',
        ])
        return f'<HoraPerfilPermissao perfil={self.perfil_id} mod={self.modulo} {flags}>'

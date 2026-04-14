"""Modelo de Aprovacao de CarviaFrete.

Tabela satelite de carvia_fretes que registra o historico de tratativas
de aprovacao quando a divergencia entre valor_considerado/valor_pago e o
valor_cotado ultrapassa a tolerancia (R$ 5,00 — TOLERANCIA_APROVACAO em
AprovacaoFreteService).

Paridade app/fretes/models.py:AprovacaoFrete (Nacom), com as seguintes
diferencas:
- Snapshot dos 3 valores no momento da solicitacao (auditoria forte)
- 1:N (e nao 1:0..1) — frete pode ter multiplas aprovacoes ao longo do tempo
  (ex: PENDENTE -> REJEITADO -> nova solicitacao apos correcao do valor_pago)
- Status do frete.status_conferencia permanece PENDENTE durante a tratativa
  (e definido APROVADO ou DIVERGENTE so apos o aprovador decidir)

Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
"""

from app import db
from app.utils.timezone import agora_utc_naive


STATUS_APROVACAO = ('PENDENTE', 'APROVADO', 'REJEITADO')


class CarviaAprovacaoFrete(db.Model):
    """Tratativa de aprovacao de divergencia em CarviaFrete."""

    __tablename__ = 'carvia_aprovacoes_frete'

    id = db.Column(db.Integer, primary_key=True)
    frete_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_fretes.id'),
        nullable=False,
        index=True,
    )

    # PENDENTE | APROVADO | REJEITADO
    status = db.Column(db.String(20), nullable=False, default='PENDENTE', index=True)

    # Solicitacao
    solicitado_por = db.Column(db.String(100), nullable=False)
    solicitado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    motivo_solicitacao = db.Column(db.Text, nullable=True)

    # Snapshot dos valores no momento da solicitacao (auditoria)
    valor_cotado_snap = db.Column(db.Numeric(15, 2), nullable=True)
    valor_considerado_snap = db.Column(db.Numeric(15, 2), nullable=True)
    valor_pago_snap = db.Column(db.Numeric(15, 2), nullable=True)
    diferenca_snap = db.Column(db.Numeric(15, 2), nullable=True)

    # Decisao do aprovador
    aprovador = db.Column(db.String(100), nullable=True)
    aprovado_em = db.Column(db.DateTime, nullable=True)
    observacoes_aprovacao = db.Column(db.Text, nullable=True)
    lancar_diferenca = db.Column(db.Boolean, nullable=True, default=False)

    # Auditoria
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    @property
    def pendente(self):
        return self.status == 'PENDENTE'

    @property
    def finalizada(self):
        return self.status in ('APROVADO', 'REJEITADO')

    def __repr__(self):
        return (
            f'<CarviaAprovacaoFrete {self.id} '
            f'frete={self.frete_id} status={self.status}>'
        )

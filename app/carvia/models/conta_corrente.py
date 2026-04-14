"""Modelo de Conta Corrente Transportadoras CarVia.

Registra movimentacoes de DEBITO/CREDITO entre CarVia e cada transportadora
subcontratada, formando saldo acumulado por transportadora.

Cada movimentacao surge da diferenca entre `valor_considerado` (o que CarVia
acordou pagar) e `valor_pago` (o que CarVia efetivamente pagou) de um
CarviaSubcontrato. A movimentacao so e criada quando aprovada via
CarviaAprovacaoSubcontrato (com `lancar_diferenca=True`) ou quando a
diferenca esta dentro da tolerancia automatica (regra R$ 5).

Inspirado em app/fretes/models.py:ContaCorrenteTransportadora (Nacom), com
as seguintes diferencas:
- FK direta para `frete_id` (paridade Nacom — subcontrato_id foi removido em 2026-04-14)
- FK adicional `fatura_transportadora_id` para lookup direto sem JOIN
- Logica centralizada em ContaCorrenteService (no Nacom esta inline em routes)

Sinal canonico (espelha Nacom):
- valor_pago > valor_considerado -> CREDITO (CarVia pagou MAIS, transp. nos deve)
- valor_pago < valor_considerado -> DEBITO  (CarVia pagou MENOS, devemos a transp.)
- Saldo = SUM(valor_debito) - SUM(valor_credito)
- Saldo positivo = transportadora deve para CarVia

Ref: .claude/plans/wobbly-tumbling-treasure.md
"""

from app import db
from app.utils.timezone import agora_utc_naive


TIPOS_MOVIMENTACAO_CC = ('DEBITO', 'CREDITO', 'COMPENSACAO')
STATUS_CC = ('ATIVO', 'COMPENSADO', 'DESCONSIDERADO')


class CarviaContaCorrenteTransportadora(db.Model):
    """Movimentacao de conta corrente de uma transportadora subcontratada."""

    __tablename__ = 'carvia_conta_corrente_transportadoras'

    id = db.Column(db.Integer, primary_key=True)
    transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('transportadoras.id'),
        nullable=False,
        index=True,
    )
    frete_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_fretes.id'),
        nullable=True,
        index=True,
    )

    fatura_transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_transportadora.id'),
        nullable=True,
        index=True,
    )

    # DEBITO | CREDITO | COMPENSACAO
    tipo_movimentacao = db.Column(db.String(20), nullable=False)
    valor_diferenca = db.Column(db.Numeric(15, 2), nullable=False)  # absoluto
    valor_debito = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    valor_credito = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    descricao = db.Column(db.String(255), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)

    # ATIVO | COMPENSADO | DESCONSIDERADO
    status = db.Column(db.String(20), nullable=False, default='ATIVO', index=True)

    # Compensacao (ainda nao implementado, mas estrutura espelha Nacom)
    compensado_em = db.Column(db.DateTime, nullable=True)
    compensado_por = db.Column(db.String(100), nullable=True)
    # Auditoria
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive, index=True)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relacionamentos
    transportadora = db.relationship('Transportadora', lazy='joined')
    frete = db.relationship('CarviaFrete', foreign_keys=[frete_id])
    fatura_transportadora = db.relationship(
        'CarviaFaturaTransportadora',
        foreign_keys=[fatura_transportadora_id],
    )

    @property
    def ativa(self):
        return self.status == 'ATIVO'

    def __repr__(self):
        return (
            f'<CarviaContaCorrenteTransportadora {self.id} '
            f'transp={self.transportadora_id} frete={self.frete_id} '
            f'tipo={self.tipo_movimentacao} valor={self.valor_diferenca}>'
        )

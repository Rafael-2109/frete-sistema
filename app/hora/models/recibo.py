"""Recibo Simples (documento NAO-fiscal) de pecas/oficina — roadmap #1b.

Gerado a partir de uma HoraVenda que tem itens de peca. Cobre APENAS pecas/
servicos (motos sempre saem com NFe). Numeracao sequencial GLOBAL via sequence
`hora_recibo_numero_seq` (migration hora_47). PDF persistido no S3.

Coexiste com a NFe da venda (independentes — decisao do dono 2026-06-06):
uma venda pode ter NFe das motos E recibo das pecas.
"""
from app import db
from app.utils.timezone import agora_utc_naive


# Status do recibo.
RECIBO_STATUS_EMITIDO = 'EMITIDO'
RECIBO_STATUS_CANCELADO = 'CANCELADO'
RECIBO_STATUS_VALIDOS = (RECIBO_STATUS_EMITIDO, RECIBO_STATUS_CANCELADO)


class HoraRecibo(db.Model):
    """Recibo Simples de pecas/oficina de uma venda (nao-fiscal)."""
    __tablename__ = 'hora_recibo'

    id = db.Column(db.Integer, primary_key=True)

    # Numero sequencial GLOBAL (preenchido pelo service via nextval da sequence
    # hora_recibo_numero_seq). Exibido como "REC-000123" (helper numero_display).
    numero = db.Column(db.Integer, nullable=False, unique=True, index=True)

    venda_id = db.Column(
        db.Integer, db.ForeignKey('hora_venda.id'), nullable=False, index=True,
    )

    # Soma dos preco_final das pecas incluidas no recibo (snapshot no momento).
    valor_total = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    pdf_s3_key = db.Column(db.String(500), nullable=True)

    status = db.Column(
        db.String(20), nullable=False, default=RECIBO_STATUS_EMITIDO, index=True,
    )

    emitido_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    emitido_por = db.Column(db.String(100), nullable=True)
    cancelado_em = db.Column(db.DateTime, nullable=True)
    cancelado_por = db.Column(db.String(100), nullable=True)
    cancelamento_motivo = db.Column(db.String(500), nullable=True)

    venda = db.relationship('HoraVenda', backref='recibos')

    @property
    def numero_display(self) -> str:
        return f'REC-{self.numero:06d}'

    def __repr__(self):
        return f'<HoraRecibo {self.numero_display} venda={self.venda_id} {self.status}>'

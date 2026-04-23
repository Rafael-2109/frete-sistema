"""Models de transferencia entre filiais HORA.

Padrao header + item + auditoria (append-only), espelhando
hora_recebimento + hora_recebimento_conferencia + hora_conferencia_auditoria.

Fluxo (2 eventos em hora_moto_evento):
  1. Loja origem emite → EM_TRANSITO (loja_id=destino)
  2. Loja destino confirma → TRANSFERIDA (loja_id=destino)
Cancelamento (origem enquanto EM_TRANSITO) → CANCELADA (loja_id=origem).
"""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraTransferencia(db.Model):
    __tablename__ = 'hora_transferencia'

    id = db.Column(db.BigInteger, primary_key=True)
    loja_origem_id = db.Column(
        db.Integer, db.ForeignKey('hora_loja.id'),
        nullable=False, index=True,
    )
    loja_destino_id = db.Column(
        db.Integer, db.ForeignKey('hora_loja.id'),
        nullable=False, index=True,
    )
    status = db.Column(db.String(30), nullable=False, index=True)
    emitida_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    emitida_por = db.Column(db.String(100), nullable=False)
    confirmada_em = db.Column(db.DateTime, nullable=True)
    confirmada_por = db.Column(db.String(100), nullable=True)
    cancelada_em = db.Column(db.DateTime, nullable=True)
    cancelada_por = db.Column(db.String(100), nullable=True)
    motivo_cancelamento = db.Column(db.String(255), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive,
    )

    loja_origem = db.relationship('HoraLoja', foreign_keys=[loja_origem_id])
    loja_destino = db.relationship('HoraLoja', foreign_keys=[loja_destino_id])
    itens = db.relationship(
        'HoraTransferenciaItem',
        backref='transferencia',
        cascade='all, delete-orphan',
        lazy='selectin',
    )
    auditoria = db.relationship(
        'HoraTransferenciaAuditoria',
        backref='transferencia',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='HoraTransferenciaAuditoria.criado_em.desc()',
    )


class HoraTransferenciaItem(db.Model):
    __tablename__ = 'hora_transferencia_item'

    id = db.Column(db.BigInteger, primary_key=True)
    transferencia_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_transferencia.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    numero_chassi = db.Column(
        db.String(30), db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False, index=True,
    )
    conferido_destino_em = db.Column(db.DateTime, nullable=True)
    conferido_destino_por = db.Column(db.String(100), nullable=True)
    qr_code_lido = db.Column(db.Boolean, nullable=False, default=False)
    foto_s3_key = db.Column(db.String(500), nullable=True)
    observacao_item = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            'transferencia_id', 'numero_chassi',
            name='uq_hora_transferencia_item_chassi',
        ),
    )

    @property
    def esta_confirmado(self) -> bool:
        return self.conferido_destino_em is not None


class HoraTransferenciaAuditoria(db.Model):
    __tablename__ = 'hora_transferencia_auditoria'

    id = db.Column(db.BigInteger, primary_key=True)
    transferencia_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_transferencia.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    item_id = db.Column(
        db.Integer, db.ForeignKey('hora_transferencia_item.id'),
        nullable=True, index=True,
    )
    usuario = db.Column(db.String(100), nullable=False)
    acao = db.Column(db.String(40), nullable=False, index=True)
    campo_alterado = db.Column(db.String(60), nullable=True)
    valor_antes = db.Column(db.Text, nullable=True)
    valor_depois = db.Column(db.Text, nullable=True)
    detalhe = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

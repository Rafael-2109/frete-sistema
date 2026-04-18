"""Ato de receber uma NF em uma loja + conferência unitária por chassi."""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraRecebimento(db.Model):
    """Uma NF chegou fisicamente em uma loja. Header da conferência."""
    __tablename__ = 'hora_recebimento'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_nf_entrada.id'),
        nullable=False,
        index=True,
    )
    loja_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_loja.id'),
        nullable=False,
        index=True,
    )
    data_recebimento = db.Column(db.Date, nullable=False, default=agora_utc_naive)
    operador = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='EM_CONFERENCIA', index=True)
    # Valores: EM_CONFERENCIA, CONCLUIDO, COM_DIVERGENCIA

    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    nf = db.relationship('HoraNfEntrada', backref='recebimentos')
    loja = db.relationship('HoraLoja', backref='recebimentos')
    conferencias = db.relationship(
        'HoraRecebimentoConferencia',
        backref='recebimento',
        cascade='all, delete-orphan',
    )

    __table_args__ = (
        db.UniqueConstraint('nf_id', 'loja_id', name='uq_hora_recebimento_nf_loja'),
    )

    def __repr__(self):
        return f'<HoraRecebimento nf={self.nf_id} loja={self.loja_id}>'


class HoraRecebimentoConferencia(db.Model):
    """Conferência unitária de um chassi durante o recebimento.

    Cada registro captura: QR code lido, foto S3, e se houve divergência
    (modelo/cor diferente, moto faltando, chassi extra).
    """
    __tablename__ = 'hora_recebimento_conferencia'

    id = db.Column(db.Integer, primary_key=True)
    recebimento_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_recebimento.id'),
        nullable=False,
        index=True,
    )
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False,
        index=True,
    )
    conferido_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    qr_code_lido = db.Column(db.Boolean, nullable=False, default=False)
    foto_s3_key = db.Column(db.String(500), nullable=True)

    tipo_divergencia = db.Column(db.String(30), nullable=True, index=True)
    # Valores: NULL (sem divergência), MODELO_DIFERENTE, COR_DIFERENTE,
    #          MOTO_FALTANDO, CHASSI_EXTRA, MOTOR_DIFERENTE, AVARIA_FISICA
    detalhe_divergencia = db.Column(db.Text, nullable=True)

    operador = db.Column(db.String(100), nullable=True)

    moto = db.relationship('HoraMoto', backref='conferencias_recebimento')

    __table_args__ = (
        db.UniqueConstraint(
            'recebimento_id',
            'numero_chassi',
            name='uq_hora_recebimento_conferencia_chassi',
        ),
    )

    def __repr__(self):
        return (
            f'<HoraRecebimentoConferencia recebimento={self.recebimento_id} '
            f'chassi={self.numero_chassi} div={self.tipo_divergencia or "OK"}>'
        )

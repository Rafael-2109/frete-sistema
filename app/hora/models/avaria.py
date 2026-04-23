"""Models de avaria em moto do estoque HORA.

Padrao header + N fotos, espelhando hora_peca_faltando + hora_peca_faltando_foto.

Regra de negocio: avaria NAO bloqueia venda — apenas registra + emite
evento AVARIADA em hora_moto_evento. Moto permanece em estoque vendavel.
"""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraAvaria(db.Model):
    __tablename__ = 'hora_avaria'

    id = db.Column(db.BigInteger, primary_key=True)
    numero_chassi = db.Column(
        db.String(30), db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False, index=True,
    )
    loja_id = db.Column(
        db.Integer, db.ForeignKey('hora_loja.id'),
        nullable=False, index=True,
    )
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='ABERTA', index=True)
    criado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, index=True,
    )
    criado_por = db.Column(db.String(100), nullable=False)
    resolvido_em = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    resolucao_observacao = db.Column(db.Text, nullable=True)

    loja = db.relationship('HoraLoja')
    fotos = db.relationship(
        'HoraAvariaFoto',
        backref='avaria',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='HoraAvariaFoto.criado_em',
    )

    @property
    def esta_aberta(self) -> bool:
        return self.status == 'ABERTA'


class HoraAvariaFoto(db.Model):
    __tablename__ = 'hora_avaria_foto'

    id = db.Column(db.BigInteger, primary_key=True)
    avaria_id = db.Column(
        db.Integer, db.ForeignKey('hora_avaria.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    foto_s3_key = db.Column(db.String(500), nullable=False)
    legenda = db.Column(db.String(255), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

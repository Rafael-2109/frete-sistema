from app import db
from app.utils.timezone import agora_brasil_naive


COMPRA_STATUS_ABERTA = 'ABERTA'
COMPRA_STATUS_RECEBIMENTO_PARCIAL = 'RECEBIMENTO_PARCIAL'
COMPRA_STATUS_FECHADA = 'FECHADA'
COMPRA_STATUS_CANCELADA = 'CANCELADA'
COMPRA_STATUS_VALIDOS = {
    COMPRA_STATUS_ABERTA, COMPRA_STATUS_RECEBIMENTO_PARCIAL,
    COMPRA_STATUS_FECHADA, COMPRA_STATUS_CANCELADA,
}


class AssaiCompraMotochefe(db.Model):
    __tablename__ = 'assai_compra_motochefe'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False)
    data_emissao = db.Column(db.Date)
    motochefe_cnpj = db.Column(db.String(18))
    status = db.Column(db.String(30), default=COMPRA_STATUS_ABERTA, nullable=False)
    criada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    criada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    pedido_links = db.relationship('AssaiCompraMotochefePedido', backref='compra',
                                   cascade='all, delete-orphan', lazy='selectin')
    recibos = db.relationship('AssaiReciboMotochefe', backref='compra',
                              cascade='all, delete-orphan', lazy='selectin')
    criada_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiCompraMotochefe {self.numero} {self.status}>'


class AssaiCompraMotochefePedido(db.Model):
    __tablename__ = 'assai_compra_motochefe_pedido'

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('assai_compra_motochefe.id', ondelete='CASCADE'), nullable=False)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('compra_id', 'pedido_id', name='uq_assai_compra_pedido'),
    )

    pedido = db.relationship('AssaiPedidoVenda', lazy='joined')

    def __repr__(self):
        return f'<AssaiCompraMotochefePedido compra={self.compra_id} pedido={self.pedido_id}>'

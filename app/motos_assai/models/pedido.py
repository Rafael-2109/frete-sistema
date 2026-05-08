from app import db
from app.utils.timezone import agora_brasil_naive


PEDIDO_STATUS_ABERTO = 'ABERTO'
PEDIDO_STATUS_EM_PRODUCAO = 'EM_PRODUCAO'
PEDIDO_STATUS_SEPARANDO = 'SEPARANDO'
PEDIDO_STATUS_FATURADO_PARCIAL = 'FATURADO_PARCIAL'
PEDIDO_STATUS_FATURADO = 'FATURADO'
PEDIDO_STATUS_CANCELADO = 'CANCELADO'

PEDIDO_STATUS_VALIDOS = {
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO, PEDIDO_STATUS_SEPARANDO,
    PEDIDO_STATUS_FATURADO_PARCIAL, PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
}


class AssaiPedidoVenda(db.Model):
    __tablename__ = 'assai_pedido_venda'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(40), unique=True, nullable=False)
    data_emissao = db.Column(db.Date)
    previsao_entrega = db.Column(db.Date)
    fornecedor_cnpj = db.Column(db.String(18))
    pdf_s3_key = db.Column(db.String(500))
    parser_usado = db.Column(db.String(30))
    parsing_confianca = db.Column(db.Numeric(3, 2))
    status = db.Column(db.String(30), default=PEDIDO_STATUS_ABERTO, nullable=False)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    itens = db.relationship('AssaiPedidoVendaItem', backref='pedido',
                            cascade='all, delete-orphan', lazy='selectin')
    criado_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiPedidoVenda {self.numero} {self.status}>'


class AssaiPedidoVendaItem(db.Model):
    __tablename__ = 'assai_pedido_venda_item'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id', ondelete='CASCADE'), nullable=False)
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'), nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False, index=True)
    qtd_pedida = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    valor_total = db.Column(db.Numeric(14, 2), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('pedido_id', 'loja_id', 'modelo_id',
                            name='uq_assai_pedido_item_pedido_loja_modelo'),
    )

    loja = db.relationship('AssaiLoja', lazy='joined')
    modelo = db.relationship('AssaiModelo', lazy='joined')

    def __repr__(self):
        return f'<AssaiPedidoVendaItem pedido={self.pedido_id} loja={self.loja_id} modelo={self.modelo_id} qtd={self.qtd_pedida}>'

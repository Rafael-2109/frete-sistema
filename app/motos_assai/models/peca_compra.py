"""AssaiPecaCompra (cabecalho) + AssaiPecaCompraItem (Spec 1 §4.5/§4.6).

Molde AssaiCompraMotochefe: numero 'PC-AAAA-NNNN', tipo no cabecalho (O3),
status default ABERTA, relationship itens cascade all,delete-orphan selectin.
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


COMPRA_PECA_TIPO_GARANTIA = 'GARANTIA'
COMPRA_PECA_TIPO_COMPRA = 'COMPRA'
COMPRA_PECA_TIPOS_VALIDOS = {COMPRA_PECA_TIPO_GARANTIA, COMPRA_PECA_TIPO_COMPRA}

COMPRA_PECA_STATUS_ABERTA = 'ABERTA'
COMPRA_PECA_STATUS_PARCIAL = 'PARCIAL'
COMPRA_PECA_STATUS_RECEBIDA = 'RECEBIDA'
COMPRA_PECA_STATUS_CANCELADA = 'CANCELADA'
COMPRA_PECA_STATUS_VALIDOS = {
    COMPRA_PECA_STATUS_ABERTA,
    COMPRA_PECA_STATUS_PARCIAL,
    COMPRA_PECA_STATUS_RECEBIDA,
    COMPRA_PECA_STATUS_CANCELADA,
}


class AssaiPecaCompra(db.Model):
    __tablename__ = 'assai_peca_compra'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), nullable=False, default=COMPRA_PECA_STATUS_ABERTA)
    fornecedor = db.Column(db.String(120), nullable=False, default='MOTOCHEFE')
    criada_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    criada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    observacao = db.Column(db.Text)
    dados_extras = db.Column(JSONB, default=dict)

    itens = db.relationship('AssaiPecaCompraItem', backref='compra',
                            cascade='all, delete-orphan', lazy='selectin')

    def __repr__(self):
        return f'<AssaiPecaCompra {self.numero} {self.tipo} {self.status}>'


class AssaiPecaCompraItem(db.Model):
    __tablename__ = 'assai_peca_compra_item'

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('assai_peca_compra.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    peca_id = db.Column(db.Integer, db.ForeignKey('assai_peca.id', ondelete='RESTRICT'), nullable=False)
    quantidade = db.Column(db.Numeric(15, 3), nullable=False)
    quantidade_recebida = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    custo_estimado = db.Column(db.Numeric(15, 4))
    pendencia_id = db.Column(db.Integer, db.ForeignKey('assai_pendencia.id', ondelete='SET NULL'))
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)

    peca = db.relationship('AssaiPeca', lazy='joined')

    def __repr__(self):
        return f'<AssaiPecaCompraItem #{self.id} compra={self.compra_id} peca={self.peca_id}>'

from app import db
from app.utils.timezone import agora_brasil_naive


SEPARACAO_STATUS_EM_SEPARACAO = 'EM_SEPARACAO'
SEPARACAO_STATUS_FECHADA = 'FECHADA'
SEPARACAO_STATUS_FATURADA = 'FATURADA'
SEPARACAO_STATUS_CANCELADA = 'CANCELADA'
SEPARACAO_STATUS_VALIDOS = {
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_CANCELADA,
}


class AssaiSeparacao(db.Model):
    __tablename__ = 'assai_separacao'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id'), nullable=False, index=True)
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default=SEPARACAO_STATUS_EM_SEPARACAO, nullable=False)
    iniciada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    fechada_em = db.Column(db.DateTime)
    fechada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    solicitacao_excel_s3_key = db.Column(db.String(500))
    motivo_cancelamento = db.Column(db.Text)

    itens = db.relationship('AssaiSeparacaoItem', backref='separacao',
                            cascade='all, delete-orphan', lazy='selectin')
    pedido = db.relationship('AssaiPedidoVenda', lazy='joined')
    loja = db.relationship('AssaiLoja', lazy='joined')
    fechada_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiSeparacao pedido={self.pedido_id} loja={self.loja_id} {self.status}>'


class AssaiSeparacaoItem(db.Model):
    __tablename__ = 'assai_separacao_item'

    id = db.Column(db.Integer, primary_key=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id', ondelete='CASCADE'), nullable=False, index=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False)
    valor_unitario_qpa = db.Column(db.Numeric(12, 2), nullable=False)
    registrada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    registrada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))

    modelo = db.relationship('AssaiModelo', lazy='joined')
    registrada_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiSeparacaoItem separacao={self.separacao_id} chassi={self.chassi}>'

"""AssaiCarregamento - entidade entre Sep e NF (carga real).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md S2.1
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase1-fundacao.md Task 9
"""
from app import db
from app.utils.timezone import agora_brasil_naive


CARREGAMENTO_STATUS_EM_CARREGAMENTO = 'EM_CARREGAMENTO'
CARREGAMENTO_STATUS_FINALIZADO = 'FINALIZADO'
CARREGAMENTO_STATUS_CANCELADO = 'CANCELADO'

CARREGAMENTO_STATUS_VALIDOS = {
    CARREGAMENTO_STATUS_EM_CARREGAMENTO,
    CARREGAMENTO_STATUS_FINALIZADO,
    CARREGAMENTO_STATUS_CANCELADO,
}


class AssaiCarregamento(db.Model):
    __tablename__ = 'assai_carregamento'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id'), nullable=False, index=True)
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'), nullable=False, index=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id'), index=True)
    status = db.Column(db.String(20), nullable=False, default=CARREGAMENTO_STATUS_EM_CARREGAMENTO, index=True)
    iniciado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    iniciado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    finalizado_em = db.Column(db.DateTime)
    finalizado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    cancelado_em = db.Column(db.DateTime)
    cancelado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    motivo_cancelamento = db.Column(db.Text)

    pedido = db.relationship('AssaiPedidoVenda', backref='carregamentos')
    loja = db.relationship('AssaiLoja')
    separacao = db.relationship('AssaiSeparacao', backref='carregamento_finalizado', uselist=False)
    itens = db.relationship('AssaiCarregamentoItem', backref='carregamento', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AssaiCarregamento #{self.id} pedido={self.pedido_id} loja={self.loja_id} status={self.status}>'


class AssaiCarregamentoItem(db.Model):
    __tablename__ = 'assai_carregamento_item'

    id = db.Column(db.Integer, primary_key=True)
    carregamento_id = db.Column(db.Integer, db.ForeignKey('assai_carregamento.id', ondelete='CASCADE'),
                                nullable=False, index=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False)
    escaneado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    escaneado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))

    modelo = db.relationship('AssaiModelo')

    def __repr__(self):
        return f'<AssaiCarregamentoItem #{self.id} chassi={self.chassi}>'

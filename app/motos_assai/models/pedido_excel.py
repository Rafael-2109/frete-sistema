"""AssaiPedidoExcel - historico versionado de Excel Q.P.A. por sep.

Spec: S2.1, S12
Plano: Task 11
"""
from app import db
from app.utils.timezone import agora_brasil_naive


class AssaiPedidoExcel(db.Model):
    __tablename__ = 'assai_pedido_excel'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id'), nullable=False, index=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id'), nullable=False, index=True)
    s3_key = db.Column(db.String(500), nullable=False)
    versao = db.Column(db.Integer, nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    gerado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    gerado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    motivo_regeneracao = db.Column(db.Text)

    pedido = db.relationship('AssaiPedidoVenda', backref='excels_historico')
    separacao = db.relationship('AssaiSeparacao')

    def __repr__(self):
        flag = '*' if self.ativo else ' '
        return f'<AssaiPedidoExcel #{self.id} sep={self.separacao_id} v{self.versao}{flag}>'

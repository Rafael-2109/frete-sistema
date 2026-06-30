"""AssaiEstoqueMovimento — ledger append-only de pecas (Spec 1 §4.4/§5).

Saldo = SUM(delta_almoxarifado) por peca_id. Correcao = nova linha AJUSTE
(nunca UPDATE/DELETE). Custo congelado na linha (custo_unitario/custo_total).
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


MOVIMENTO_ENTRADA = 'ENTRADA'
MOVIMENTO_CONSUMO = 'CONSUMO'
MOVIMENTO_CANIBALIZACAO = 'CANIBALIZACAO'
MOVIMENTO_DESCARTE = 'DESCARTE'
MOVIMENTO_AJUSTE = 'AJUSTE'
MOVIMENTO_TIPOS_VALIDOS = {
    MOVIMENTO_ENTRADA,
    MOVIMENTO_CONSUMO,
    MOVIMENTO_CANIBALIZACAO,
    MOVIMENTO_DESCARTE,
    MOVIMENTO_AJUSTE,
}


class AssaiEstoqueMovimento(db.Model):
    __tablename__ = 'assai_estoque_movimento'

    id = db.Column(db.BigInteger, primary_key=True)
    peca_id = db.Column(db.Integer, db.ForeignKey('assai_peca.id', ondelete='RESTRICT'),
                        nullable=False, index=True)
    tipo = db.Column(db.String(40), nullable=False)
    quantidade = db.Column(db.Numeric(15, 3), nullable=False)
    delta_almoxarifado = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    chassi_origem = db.Column(db.String(50), index=True)
    chassi_destino = db.Column(db.String(50), index=True)
    pendencia_id = db.Column(db.Integer, db.ForeignKey('assai_pendencia.id', ondelete='SET NULL'), index=True)
    # FK real no banco (Task 1); ORM FK adicionado quando Task 5 definir AssaiPecaCompraItem
    compra_item_id = db.Column(db.Integer)
    custo_unitario = db.Column(db.Numeric(15, 4))
    custo_total = db.Column(db.Numeric(15, 2))
    receita_unitaria = db.Column(db.Numeric(15, 4))
    receita_total = db.Column(db.Numeric(15, 2))
    operador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    ocorrido_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    observacao = db.Column(db.Text)
    dados_extras = db.Column(JSONB, default=dict)

    peca = db.relationship('AssaiPeca', lazy='joined')

    def __repr__(self):
        return f'<AssaiEstoqueMovimento #{self.id} {self.tipo} peca={self.peca_id} delta={self.delta_almoxarifado}>'

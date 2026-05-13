from app import db
from app.utils.timezone import agora_brasil_naive


# 4 status simplificados (Fase 1 — D2 + R4.2 + Q18)
# Status legados (EM_PRODUCAO, SEPARANDO, FATURADO_PARCIAL) REMOVIDOS — Big Bang Task 19.
PEDIDO_STATUS_ABERTO = 'ABERTO'
PEDIDO_STATUS_PARCIALMENTE_FATURADO = 'PARCIALMENTE_FATURADO'  # renomeado de FATURADO_PARCIAL
PEDIDO_STATUS_FATURADO = 'FATURADO'
PEDIDO_STATUS_CANCELADO = 'CANCELADO'  # roadmap futuro (R4.1) — manual via cancelar_pedido_assai

PEDIDO_STATUS_VALIDOS = {
    PEDIDO_STATUS_ABERTO,
    PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    PEDIDO_STATUS_FATURADO,
    PEDIDO_STATUS_CANCELADO,
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
    lojas = db.relationship('AssaiPedidoVendaLoja', backref='pedido',
                            cascade='all, delete-orphan', lazy='selectin')
    criado_por = db.relationship('Usuario', lazy='joined')

    @property
    def numero_pedido(self):
        """Alias retrocompativel para self.numero — codigo legado em mirror_service usa numero_pedido."""
        return self.numero

    def __repr__(self):
        return f'<AssaiPedidoVenda {self.numero} {self.status}>'


class AssaiPedidoVendaLoja(db.Model):
    """Cabecalho por (pedido, loja). Contem os 4 campos de agendamento que
    propagam-se para todos os itens (loja x modelo) da mesma loja no pedido.

    Migration 10 (2026-05-12).
    """
    __tablename__ = 'assai_pedido_venda_loja'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'),
                        nullable=False, index=True)
    expedicao = db.Column(db.Date)
    agendamento = db.Column(db.Date)
    protocolo = db.Column(db.String(50))
    # server_default: garante DEFAULT no DB quando tabela criada via
    # db.create_all() (sem migration). Previne incidente PYTHON-FLASK-RT.
    agendamento_confirmado = db.Column(
        db.Boolean, default=False, server_default='false', nullable=False,
    )
    criado_em = db.Column(
        db.DateTime, default=agora_brasil_naive,
        server_default=db.text("(NOW() AT TIME ZONE 'America/Sao_Paulo')"),
        nullable=False,
    )
    atualizado_em = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint('pedido_id', 'loja_id',
                            name='uq_assai_pedido_venda_loja_pedido_loja'),
    )

    loja = db.relationship('AssaiLoja', lazy='joined')
    # passive_deletes=True (H7): confia no ON DELETE CASCADE do SQL. Sem isso,
    # SQLAlchemy emite UPDATE SET pedido_loja_id=NULL antes do cascade DB
    # disparar — viola NOT NULL constraint.
    itens = db.relationship('AssaiPedidoVendaItem', backref='pedido_loja',
                            lazy='selectin', passive_deletes=True,
                            primaryjoin='AssaiPedidoVendaLoja.id == AssaiPedidoVendaItem.pedido_loja_id')

    def __repr__(self):
        return f'<AssaiPedidoVendaLoja pedido={self.pedido_id} loja={self.loja_id}>'


class AssaiPedidoVendaItem(db.Model):
    __tablename__ = 'assai_pedido_venda_item'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id', ondelete='CASCADE'), nullable=False)
    pedido_loja_id = db.Column(db.Integer,
                               db.ForeignKey('assai_pedido_venda_loja.id', ondelete='CASCADE'),
                               nullable=False, index=True)
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

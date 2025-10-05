"""
Modelos de Logística - Sistema MotoCHEFE
EmbarqueMoto: Agrupamento de pedidos para entrega
EmbarquePedido: Relação N:N entre Embarque e Pedido (com rateio de frete)
"""
from app import db
from datetime import datetime, date


class EmbarqueMoto(db.Model):
    """
    Embarque de entregas
    1 Embarque = N Pedidos (rateio de frete)
    """
    __tablename__ = 'embarque_moto'

    # PK
    id = db.Column(db.Integer, primary_key=True)
    numero_embarque = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Transportadora
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadora_moto.id'), nullable=False)

    # Datas
    data_embarque = db.Column(db.Date, nullable=False, default=date.today)
    data_entrega_prevista = db.Column(db.Date, nullable=True)
    data_entrega_real = db.Column(db.Date, nullable=True)

    # Frete à transportadora
    valor_frete_contratado = db.Column(db.Numeric(15, 2), nullable=False)  # Valor acordado
    valor_frete_pago = db.Column(db.Numeric(15, 2), nullable=True)         # Valor efetivamente pago
    data_pagamento_frete = db.Column(db.Date, nullable=True)               # Data do pagamento
    status_pagamento_frete = db.Column(db.String(20), default='PENDENTE', nullable=False)  # PENDENTE, PAGO, ATRASADO
    tipo_veiculo = db.Column(db.String(50), nullable=True)

    # Status
    status = db.Column(db.String(20), default='PLANEJADO', nullable=False, index=True)
    # Valores: PLANEJADO, EM_TRANSITO, ENTREGUE, CANCELADO

    # Observações
    observacoes = db.Column(db.Text, nullable=True)

    # Relacionamentos
    transportadora = db.relationship('TransportadoraMoto', backref='embarques')
    pedidos_rel = db.relationship('EmbarquePedido', backref='embarque', lazy='dynamic', cascade='all, delete-orphan')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<EmbarqueMoto {self.numero_embarque} - {self.status}>'

    @property
    def total_motos(self):
        """Retorna total de motos no embarque"""
        return db.session.query(
            db.func.sum(EmbarquePedido.qtd_motos_pedido)
        ).filter_by(embarque_id=self.id).scalar() or 0

    @property
    def total_pedidos(self):
        """Retorna quantidade de pedidos no embarque"""
        return self.pedidos_rel.count()


class EmbarquePedido(db.Model):
    """
    Tabela de relacionamento N:N entre Embarque e Pedido
    Armazena rateio de frete por pedido
    """
    __tablename__ = 'embarque_pedido'
    __table_args__ = (
        db.UniqueConstraint('embarque_id', 'pedido_id', name='uk_embarque_pedido'),
    )

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # FK
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarque_moto.id'), nullable=False, index=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_venda_moto.id'), nullable=False, index=True)

    # Rateio de frete (calculado automaticamente)
    qtd_motos_pedido = db.Column(db.Integer, nullable=False)
    valor_frete_rateado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    # Fórmula: (valor_frete_pago_embarque / total_motos_embarque) * qtd_motos_pedido

    # Status de envio (trigger para rateio e atualização do pedido)
    enviado = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # Relacionamentos
    pedido = db.relationship('PedidoVendaMoto', backref='embarques')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<EmbarquePedido Embarque:{self.embarque_id} Pedido:{self.pedido_id}>'

    def calcular_rateio(self):
        """
        Calcula valor de frete rateado para este pedido
        Baseado no total de motos do embarque
        """
        embarque = self.embarque
        total_motos_embarque = embarque.total_motos

        if total_motos_embarque == 0:
            self.valor_frete_rateado = 0
            return

        # Rateio proporcional (usa valor contratado)
        self.valor_frete_rateado = (
            embarque.valor_frete_contratado / total_motos_embarque
        ) * self.qtd_motos_pedido

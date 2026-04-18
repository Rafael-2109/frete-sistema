"""Fluxo de entrada: pedido HORA→Motochefe e NF Motochefe→HORA."""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraPedido(db.Model):
    """Pedido de compra emitido pela HORA para a Motochefe (fabricante).

    Today: origem Excel via WhatsApp. Aqui persistido como entidade first-class
    para confronto estrutural com NF recebida.
    """
    __tablename__ = 'hora_pedido'

    id = db.Column(db.Integer, primary_key=True)
    numero_pedido = db.Column(db.String(50), nullable=False, unique=True, index=True)
    cnpj_destino = db.Column(db.String(20), nullable=False, index=True)
    # CNPJ para o qual a Motochefe deve faturar (uma das lojas HORA).
    data_pedido = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='ABERTO', index=True)
    # Valores: ABERTO, PARCIALMENTE_FATURADO, FATURADO, CANCELADO

    arquivo_origem_s3_key = db.Column(db.String(500), nullable=True)
    # Excel original (quando importado do WhatsApp).
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    itens = db.relationship(
        'HoraPedidoItem',
        backref='pedido',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<HoraPedido {self.numero_pedido} ({self.status})>'


class HoraPedidoItem(db.Model):
    """Linha de pedido: uma moto solicitada/esperada, com chassi opcional.

    `numero_chassi` é nullable para suportar pedido pré-NF (cliente solicita
    motos antes da Motochefe atribuir chassis). Única exceção ao invariante 2.
    Quando a NF chega, update-se com o chassi atribuído.

    UNIQUE parcial: UNIQUE(pedido_id, numero_chassi) WHERE numero_chassi IS NOT NULL.
    Criada via index em migration hora_02.
    """
    __tablename__ = 'hora_pedido_item'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_pedido.id'),
        nullable=False,
        index=True,
    )
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=True,
        index=True,
    )
    modelo_id = db.Column(db.Integer, db.ForeignKey('hora_modelo.id'), nullable=True)
    cor = db.Column(db.String(50), nullable=True)
    preco_compra_esperado = db.Column(db.Numeric(15, 2), nullable=False)

    moto = db.relationship('HoraMoto', backref='pedidos_itens')
    modelo = db.relationship('HoraModelo')

    def __repr__(self):
        chassi = self.numero_chassi or 'PENDENTE'
        return f'<HoraPedidoItem pedido={self.pedido_id} chassi={chassi}>'


class HoraNfEntrada(db.Model):
    """NF fiscal recebida da Motochefe (B2B / Laiouns / Q.P.A).

    Pode vir vinculada a pedido (fluxo normal) ou órfã (Motochefe emitiu sem pedido
    prévio — confronto registra divergência).
    """
    __tablename__ = 'hora_nf_entrada'

    id = db.Column(db.Integer, primary_key=True)
    chave_44 = db.Column(db.String(44), nullable=False, unique=True, index=True)
    numero_nf = db.Column(db.String(20), nullable=False)
    serie_nf = db.Column(db.String(10), nullable=True)
    cnpj_emitente = db.Column(db.String(20), nullable=False, index=True)
    # Vira derivável: B2B / LAIOUNS / QPA por CNPJ.
    nome_emitente = db.Column(db.String(200), nullable=True)
    cnpj_destinatario = db.Column(db.String(20), nullable=False, index=True)
    # CNPJ da loja HORA que recebe a NF.
    data_emissao = db.Column(db.Date, nullable=False)
    valor_total = db.Column(db.Numeric(15, 2), nullable=False)

    arquivo_pdf_s3_key = db.Column(db.String(500), nullable=True)
    arquivo_xml_s3_key = db.Column(db.String(500), nullable=True)

    pedido_id = db.Column(db.Integer, db.ForeignKey('hora_pedido.id'), nullable=True, index=True)
    # NULL se NF chegou sem pedido prévio (divergência estrutural).

    parseada_em = db.Column(db.DateTime, nullable=True)
    parser_usado = db.Column(db.String(50), nullable=True)
    # Ex.: 'danfe_pdf_parser_v1' — referência ao parser CarVia reusado.

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    pedido = db.relationship('HoraPedido', backref='nfs_entrada')
    itens = db.relationship(
        'HoraNfEntradaItem',
        backref='nf',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<HoraNfEntrada {self.numero_nf} emit={self.cnpj_emitente}>'


class HoraNfEntradaItem(db.Model):
    """Linha fiscal: um chassi efetivamente faturado a um preço real."""
    __tablename__ = 'hora_nf_entrada_item'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_nf_entrada.id'),
        nullable=False,
        index=True,
    )
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False,
        index=True,
    )
    preco_real = db.Column(db.Numeric(15, 2), nullable=False)

    # Texto original como apareceu na NF (antes de normalização via regex/LLM).
    # Permite auditar decisão do parser ex-post.
    modelo_texto_original = db.Column(db.String(255), nullable=True)
    cor_texto_original = db.Column(db.String(100), nullable=True)
    numero_motor_texto_original = db.Column(db.String(100), nullable=True)

    moto = db.relationship('HoraMoto', backref='nfs_entrada_itens')

    __table_args__ = (
        db.UniqueConstraint('nf_id', 'numero_chassi', name='uq_hora_nf_entrada_item_chassi'),
    )

    def __repr__(self):
        return f'<HoraNfEntradaItem nf={self.nf_id} chassi={self.numero_chassi}>'

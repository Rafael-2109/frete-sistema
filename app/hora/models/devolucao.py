"""Devolucao de motos ao fornecedor (Motochefe).

HoraMoto e insert-once; devolucao nao altera a linha da moto — registra
evento DEVOLVIDA em hora_moto_evento apontando para o item desta devolucao.
Chassi em devolucao sai do estoque por filtro do ultimo evento.
"""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraDevolucaoFornecedor(db.Model):
    """Header de devolucao: loja que esta devolvendo, motivo e status."""
    __tablename__ = 'hora_devolucao_fornecedor'

    id = db.Column(db.Integer, primary_key=True)
    loja_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_loja.id'),
        nullable=False,
        index=True,
    )
    # NF de entrada de referencia (opcional — se a devolucao e por erro de faturamento).
    nf_entrada_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_nf_entrada.id'),
        nullable=True,
        index=True,
    )
    motivo = db.Column(db.String(50), nullable=False)
    # Valores: CHASSI_EXTRA, MODELO_DIFERENTE, COR_DIFERENTE, MOTOR_DIFERENTE,
    #          AVARIA_FISICA, OUTROS
    observacoes = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default='ABERTA', index=True)
    # Valores: ABERTA, ENVIADA, CONFIRMADA, CANCELADA

    data_devolucao = db.Column(db.Date, nullable=False, default=agora_utc_naive)
    data_envio = db.Column(db.Date, nullable=True)
    data_confirmacao = db.Column(db.Date, nullable=True)

    # NF de saida emitida pela HORA para documentar a devolucao
    nf_saida_numero = db.Column(db.String(20), nullable=True)
    nf_saida_chave_44 = db.Column(db.String(44), nullable=True, unique=True)

    criado_por = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    loja = db.relationship('HoraLoja', backref='devolucoes_fornecedor')
    nf_entrada = db.relationship('HoraNfEntrada', backref='devolucoes')
    itens = db.relationship(
        'HoraDevolucaoFornecedorItem',
        backref='devolucao',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<HoraDevolucaoFornecedor #{self.id} loja={self.loja_id} {self.status}>'


class HoraDevolucaoFornecedorItem(db.Model):
    """Chassi incluido em uma devolucao. Unico por devolucao."""
    __tablename__ = 'hora_devolucao_fornecedor_item'

    id = db.Column(db.Integer, primary_key=True)
    devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_devolucao_fornecedor.id'),
        nullable=False,
        index=True,
    )
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False,
        index=True,
    )
    motivo_especifico = db.Column(db.String(255), nullable=True)
    # Ref opcional para conferencia que originou a devolucao (CHASSI_EXTRA etc.)
    recebimento_conferencia_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_recebimento_conferencia.id'),
        nullable=True,
    )

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    moto = db.relationship('HoraMoto', backref='devolucoes_fornecedor_itens')
    conferencia = db.relationship('HoraRecebimentoConferencia')

    __table_args__ = (
        db.UniqueConstraint(
            'devolucao_id',
            'numero_chassi',
            name='uq_hora_devolucao_fornecedor_item_chassi',
        ),
    )

    def __repr__(self):
        return (
            f'<HoraDevolucaoFornecedorItem dev={self.devolucao_id} '
            f'chassi={self.numero_chassi}>'
        )

"""Devolucao de Venda (cliente final -> HORA).

NAO confundir com `HoraDevolucaoFornecedor` (HORA -> Motochefe), que cobre
"recebi produto errado da Motochefe e estou devolvendo". Esta entidade cobre
o caso "cliente comprou e voltou para devolver a moto".

HoraMoto e insert-once (invariante 3); devolucao registra evento DEVOLVIDA
em hora_moto_evento e, quando resolvida, emite evento adicional conforme a
acao escolhida (CONFERIDA, AVARIADA ou FALTANDO_PECA).

Header.status:
    PENDENTE  (default ao criar) -> ainda ha itens nao resolvidos
    RESOLVIDA                    -> todos os itens estao RESOLVIDA
    CANCELADA                    -> devolucao foi revertida (motos voltaram via CONFERIDA)

Item.status_item:
    PENDENTE   -> aguardando resolucao
    RESOLVIDA  -> resolucao_acao + resolvida_em preenchidos
"""
from app import db
from app.utils.timezone import agora_utc_naive


# ----------------------------------------------------------------------------
# Constantes (manter sincronizadas com hora_39_devolucao_venda.{py,sql})
# ----------------------------------------------------------------------------
DEV_VENDA_STATUS_PENDENTE = 'PENDENTE'
DEV_VENDA_STATUS_RESOLVIDA = 'RESOLVIDA'
DEV_VENDA_STATUS_CANCELADA = 'CANCELADA'

DEV_VENDA_STATUS_VALIDOS = (
    DEV_VENDA_STATUS_PENDENTE,
    DEV_VENDA_STATUS_RESOLVIDA,
    DEV_VENDA_STATUS_CANCELADA,
)

DEV_VENDA_ITEM_STATUS_PENDENTE = 'PENDENTE'
DEV_VENDA_ITEM_STATUS_RESOLVIDA = 'RESOLVIDA'

DEV_VENDA_ITEM_STATUS_VALIDOS = (
    DEV_VENDA_ITEM_STATUS_PENDENTE,
    DEV_VENDA_ITEM_STATUS_RESOLVIDA,
)

# Acoes possiveis na resolucao do item.
DEV_VENDA_ACAO_DISPONIVEL = 'DISPONIVEL'      # volta ao estoque (CONFERIDA)
DEV_VENDA_ACAO_AVARIA = 'AVARIA'              # cria HoraAvaria + AVARIADA
DEV_VENDA_ACAO_PECA_FALTANDO = 'PECA_FALTANDO'  # cria HoraPecaFaltando + FALTANDO_PECA

DEV_VENDA_ACOES_VALIDAS = (
    DEV_VENDA_ACAO_DISPONIVEL,
    DEV_VENDA_ACAO_AVARIA,
    DEV_VENDA_ACAO_PECA_FALTANDO,
)


class HoraDevolucaoVenda(db.Model):
    """Header de devolucao de venda: NF de venda origem, motivo e status."""
    __tablename__ = 'hora_devolucao_venda'

    id = db.Column(db.Integer, primary_key=True)

    # NF de saida (HoraVenda). Obrigatoria — toda devolucao de venda parte de
    # uma venda existente que o operador localizou na pesquisa.
    venda_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_venda.id'),
        nullable=False,
        index=True,
    )
    # Snapshot da loja onde a devolucao foi registrada (normalmente a loja
    # da venda; pode divergir em cenarios multi-loja). Usado para escopo.
    loja_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_loja.id'),
        nullable=False,
        index=True,
    )

    # Detalhamento OBRIGATORIO do motivo da devolucao (texto livre).
    motivo = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.String(20), nullable=False,
        default=DEV_VENDA_STATUS_PENDENTE, index=True,
    )

    data_devolucao = db.Column(
        db.Date, nullable=False, default=lambda: agora_utc_naive().date(),
    )
    data_resolucao = db.Column(db.Date, nullable=True)

    cancelamento_motivo = db.Column(db.String(500), nullable=True)

    criado_por = db.Column(db.String(100), nullable=True)
    resolvida_por = db.Column(db.String(100), nullable=True)
    cancelada_por = db.Column(db.String(100), nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(
        db.DateTime, nullable=True, onupdate=agora_utc_naive,
    )

    venda = db.relationship('HoraVenda', backref='devolucoes_de_venda')
    loja = db.relationship('HoraLoja', backref='devolucoes_de_venda')
    itens = db.relationship(
        'HoraDevolucaoVendaItem',
        backref='devolucao',
        cascade='all, delete-orphan',
        order_by='HoraDevolucaoVendaItem.id',
    )

    @property
    def total_itens(self) -> int:
        return len(self.itens)

    @property
    def total_pendentes(self) -> int:
        return sum(
            1 for i in self.itens
            if i.status_item == DEV_VENDA_ITEM_STATUS_PENDENTE
        )

    @property
    def total_resolvidos(self) -> int:
        return sum(
            1 for i in self.itens
            if i.status_item == DEV_VENDA_ITEM_STATUS_RESOLVIDA
        )

    def __repr__(self) -> str:
        return (
            f'<HoraDevolucaoVenda #{self.id} venda={self.venda_id} '
            f'{self.status} ({self.total_resolvidos}/{self.total_itens})>'
        )


class HoraDevolucaoVendaItem(db.Model):
    """Chassi devolvido em uma devolucao de venda. Uma resolucao por item."""
    __tablename__ = 'hora_devolucao_venda_item'

    id = db.Column(db.Integer, primary_key=True)
    devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_devolucao_venda.id'),
        nullable=False,
        index=True,
    )
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False,
        index=True,
    )
    # Ref ao item original da venda (opcional — None quando chassi nao bateu
    # com nenhum HoraVendaItem ativo, ex.: dado historico).
    venda_item_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_venda_item.id'),
        nullable=True,
    )
    motivo_especifico = db.Column(db.Text, nullable=True)

    # Resolucao individual por chassi.
    status_item = db.Column(
        db.String(20), nullable=False,
        default=DEV_VENDA_ITEM_STATUS_PENDENTE, index=True,
    )
    resolucao_acao = db.Column(db.String(30), nullable=True)
    resolucao_observacoes = db.Column(db.Text, nullable=True)
    resolvida_em = db.Column(db.DateTime, nullable=True)
    resolvida_por = db.Column(db.String(100), nullable=True)

    # Auditoria: refs ao registro criado pela resolucao.
    avaria_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_avaria.id'),
        nullable=True,
    )
    peca_faltando_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_peca_faltando.id'),
        nullable=True,
    )

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    moto = db.relationship('HoraMoto', backref='devolucoes_venda_itens')
    venda_item = db.relationship('HoraVendaItem')
    avaria = db.relationship('HoraAvaria')
    peca_faltando = db.relationship('HoraPecaFaltando')

    __table_args__ = (
        db.UniqueConstraint(
            'devolucao_id', 'numero_chassi',
            name='uq_hora_dev_venda_item_chassi',
        ),
    )

    @property
    def pendente(self) -> bool:
        return self.status_item == DEV_VENDA_ITEM_STATUS_PENDENTE

    def __repr__(self) -> str:
        return (
            f'<HoraDevolucaoVendaItem dev={self.devolucao_id} '
            f'chassi={self.numero_chassi} {self.status_item}>'
        )

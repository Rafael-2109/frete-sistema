"""Cadastro de pecas (produtos fungiveis sem chassi) + estoque + itens.

Este modulo cobre o ciclo COMPLETO de pecas:
- HoraPeca               cadastro principal
- HoraTagPlusPecaMap     mapeamento opcional para emissao NFe TagPlus
- HoraPecaMovimento      log de entradas/saidas (saldo derivado por SUM)
- HoraNfEntradaItemPeca  linha de peca em NF de entrada (com conferencia 1:1)
- HoraVendaItemPeca      linha de peca em pedido de venda

NAO confundir com HoraPecaFaltando (peca FALTANDO em moto - vide peca_faltando.py).
"""
from app import db
from app.utils.timezone import agora_utc_naive


# ============================================================
# Constantes
# ============================================================

PECA_MOV_TIPO_ENTRADA_NF = 'ENTRADA_NF'
PECA_MOV_TIPO_SAIDA_VENDA = 'SAIDA_VENDA'
PECA_MOV_TIPO_TRANSF_OUT = 'TRANSFERENCIA_OUT'
PECA_MOV_TIPO_TRANSF_IN = 'TRANSFERENCIA_IN'
PECA_MOV_TIPO_AJUSTE_POS = 'AJUSTE_POS'
PECA_MOV_TIPO_AJUSTE_NEG = 'AJUSTE_NEG'
PECA_MOV_TIPO_DEVOLUCAO_VENDA = 'DEVOLUCAO_VENDA'
PECA_MOV_TIPO_DEVOLUCAO_FORN = 'DEVOLUCAO_FORNECEDOR'

PECA_MOV_TIPOS_VALIDOS = (
    PECA_MOV_TIPO_ENTRADA_NF, PECA_MOV_TIPO_SAIDA_VENDA,
    PECA_MOV_TIPO_TRANSF_OUT, PECA_MOV_TIPO_TRANSF_IN,
    PECA_MOV_TIPO_AJUSTE_POS, PECA_MOV_TIPO_AJUSTE_NEG,
    PECA_MOV_TIPO_DEVOLUCAO_VENDA, PECA_MOV_TIPO_DEVOLUCAO_FORN,
)

PECA_DIVERGENCIA_OK = 'OK'
PECA_DIVERGENCIA_FALTA = 'FALTA'
PECA_DIVERGENCIA_SOBRA = 'SOBRA'
PECA_DIVERGENCIA_AVARIA = 'AVARIA'

PECA_DIVERGENCIA_VALIDAS = (
    PECA_DIVERGENCIA_OK, PECA_DIVERGENCIA_FALTA,
    PECA_DIVERGENCIA_SOBRA, PECA_DIVERGENCIA_AVARIA,
)


# ============================================================
# HoraPeca
# ============================================================

class HoraPeca(db.Model):
    """Catalogo de pecas (capacete, retrovisor, bateria, ...)."""
    __tablename__ = 'hora_peca'

    id = db.Column(db.Integer, primary_key=True)
    codigo_interno = db.Column(db.String(50), nullable=False, unique=True, index=True)
    descricao = db.Column(db.String(255), nullable=False)
    ncm = db.Column(db.String(10), nullable=True)
    cfop_default = db.Column(db.String(5), nullable=False, default='5.102')
    unidade = db.Column(db.String(5), nullable=False, default='UN')
    preco_venda_padrao = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    # Custo de aquisicao padrao da peca (migration hora_59). Base da margem no
    # preview da NF: brindes e pecas vendidas usam ESTE valor como custo, nao
    # mais o preco_venda_padrao.
    custo = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    # Comissao por unidade vendida desta peca (roadmap #28; migration hora_49).
    valor_comissao = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    foto_s3_key = db.Column(db.String(500), nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    def __repr__(self):
        return f'<HoraPeca {self.codigo_interno} {self.descricao!r}>'


# ============================================================
# HoraTagPlusPecaMap
# ============================================================

class HoraTagPlusPecaMap(db.Model):
    """Mapeamento opcional de peca para integracao TagPlus.

    Peca pode existir sem mapeamento (somente uso interno). Para emitir
    NFe via TagPlus, exige tagplus_produto_id preenchido.
    """
    __tablename__ = 'hora_tagplus_peca_map'

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(
        db.Integer, db.ForeignKey('hora_peca.id'),
        nullable=False, unique=True, index=True,
    )
    tagplus_produto_id = db.Column(db.String(50), nullable=False)
    tagplus_codigo = db.Column(db.String(50), nullable=True, index=True)
    cfop_default = db.Column(db.String(5), nullable=True)
    # Se preenchido, sobrescreve hora_peca.cfop_default na emissao NFe.

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    peca = db.relationship('HoraPeca', backref=db.backref('tagplus_map', uselist=False))

    def __repr__(self):
        return f'<HoraTagPlusPecaMap peca={self.peca_id} tagplus={self.tagplus_produto_id}>'


# ============================================================
# HoraPecaMovimento - saldo derivado por SUM
# ============================================================

class HoraPecaMovimento(db.Model):
    """Movimento de peca (signed: + entrada, - saida).

    Saldo de uma combinacao (peca_id, loja_id) = SUM(qtd) deste log.
    Sem tabela de saldo materializado (mesmo padrao moto: estoque deriva
    de eventos).
    """
    __tablename__ = 'hora_peca_movimento'

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(
        db.Integer, db.ForeignKey('hora_peca.id'),
        nullable=False, index=True,
    )
    loja_id = db.Column(
        db.Integer, db.ForeignKey('hora_loja.id'),
        nullable=False, index=True,
    )
    tipo = db.Column(db.String(25), nullable=False)
    qtd = db.Column(db.Numeric(15, 3), nullable=False)
    ref_tabela = db.Column(db.String(50), nullable=True)
    ref_id = db.Column(db.Integer, nullable=True)
    motivo = db.Column(db.String(500), nullable=True)
    operador = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    peca = db.relationship('HoraPeca', backref='movimentos')
    loja = db.relationship('HoraLoja')

    __table_args__ = (
        db.Index('ix_hora_peca_mov_saldo_idx', 'peca_id', 'loja_id', 'criado_em'),
        db.Index('ix_hora_peca_mov_ref_idx', 'ref_tabela', 'ref_id'),
    )

    def __repr__(self):
        return (
            f'<HoraPecaMovimento peca={self.peca_id} loja={self.loja_id} '
            f'{self.tipo} {self.qtd}>'
        )


# ============================================================
# HoraNfEntradaItemPeca - peca em NF de entrada (com conferencia 1:1)
# ============================================================

class HoraNfEntradaItemPeca(db.Model):
    """Linha de peca em NF de entrada com conferencia embutida.

    Conferencia e 1:1 (uma linha de NF = uma conferencia, qtd_nf vs
    qtd_conferida). Por isso campos de conferencia moram aqui em vez
    de tabela paralela.
    """
    __tablename__ = 'hora_nf_entrada_item_peca'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(
        db.Integer, db.ForeignKey('hora_nf_entrada.id'),
        nullable=False, index=True,
    )
    peca_id = db.Column(
        db.Integer, db.ForeignKey('hora_peca.id'),
        nullable=False, index=True,
    )
    qtd_nf = db.Column(db.Numeric(15, 3), nullable=False)
    preco_real = db.Column(db.Numeric(15, 2), nullable=False)
    modelo_texto_original = db.Column(db.String(255), nullable=True)

    # Conferencia embutida (1:1).
    qtd_conferida = db.Column(db.Numeric(15, 3), nullable=True)
    divergencia_qtd = db.Column(db.String(20), nullable=True)
    foto_conferencia_s3_key = db.Column(db.String(500), nullable=True)
    conferida_em = db.Column(db.DateTime, nullable=True)
    conferida_por = db.Column(db.String(100), nullable=True)

    nf = db.relationship('HoraNfEntrada', backref='itens_peca')
    peca = db.relationship('HoraPeca')

    @property
    def conferida(self) -> bool:
        return self.qtd_conferida is not None

    def __repr__(self):
        return f'<HoraNfEntradaItemPeca nf={self.nf_id} peca={self.peca_id} qtd={self.qtd_nf}>'


# ============================================================
# HoraVendaItemPeca - peca em pedido de venda
# ============================================================

class HoraVendaItemPeca(db.Model):
    """Linha de peca em pedido de venda.

    `preco_unitario_referencia` e snapshot de hora_peca.preco_venda_padrao
    no momento da venda (auditoria). `preco_final` = qtd * (referencia - desconto).
    `custo_unitario` e snapshot de hora_peca.custo no momento da venda — base da
    margem no preview da NF.
    """
    __tablename__ = 'hora_venda_item_peca'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer, db.ForeignKey('hora_venda.id'),
        nullable=False, index=True,
    )
    peca_id = db.Column(
        db.Integer, db.ForeignKey('hora_peca.id'),
        nullable=False, index=True,
    )
    qtd = db.Column(db.Numeric(15, 3), nullable=False)
    preco_unitario_referencia = db.Column(db.Numeric(15, 2), nullable=False)
    desconto_aplicado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    preco_final = db.Column(db.Numeric(15, 2), nullable=False)
    # Snapshot de hora_peca.custo no momento da venda (migration hora_59).
    # Usado pelo preview da NF para a margem (custo real, nao preco de venda).
    custo_unitario = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    venda = db.relationship('HoraVenda', backref='itens_peca')
    peca = db.relationship('HoraPeca')

    def __repr__(self):
        return (
            f'<HoraVendaItemPeca venda={self.venda_id} peca={self.peca_id} '
            f'qtd={self.qtd} R${self.preco_final}>'
        )

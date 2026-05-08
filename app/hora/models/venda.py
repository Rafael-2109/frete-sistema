"""Fluxo de saída: pedido de venda ao consumidor final (pessoa física).

Maquina de estado (status):
  COTACAO    -> CONFIRMADO  (confirmar_venda; criada por criar_venda_manual)
  CONFIRMADO -> FATURADO    (webhook nfe_aprovada do TagPlus)
  *          -> CANCELADO   (cancelar_venda; FATURADO so apos cancelar NFe ate 24h)
  upload DANFE legado -> FATURADO direto (importar_nf_saida_pdf).

Estoque:
  - Status ativos (COTACAO, CONFIRMADO, FATURADO) reservam o chassi (saem
    de EVENTOS_EM_ESTOQUE via evento RESERVADA / VENDIDA / NF_EMITIDA).
  - CANCELADO devolve ao estoque via evento DEVOLVIDA.
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_utc_naive


# --------------------------------------------------------------------------
# Status validos (manter sincronizado com hora_20_pedido_workflow.sql).
# --------------------------------------------------------------------------
# INCOMPLETO: pedido salvo com dados parciais (formas de pagamento ausentes,
#   soma das formas != valor_total, ou AUT/ID faltando em forma que exige).
#   Reserva o chassi mas NAO permite confirmar/emitir NFe. Vendedor pode
#   editar e completar para promover a COTACAO.
VENDA_STATUS_INCOMPLETO = 'INCOMPLETO'
VENDA_STATUS_COTACAO = 'COTACAO'
VENDA_STATUS_CONFIRMADO = 'CONFIRMADO'
VENDA_STATUS_FATURADO = 'FATURADO'
VENDA_STATUS_CANCELADO = 'CANCELADO'

VENDA_STATUS_VALIDOS = (
    VENDA_STATUS_INCOMPLETO,
    VENDA_STATUS_COTACAO, VENDA_STATUS_CONFIRMADO,
    VENDA_STATUS_FATURADO, VENDA_STATUS_CANCELADO,
)
# Status que reservam chassi (saem do estoque disponivel).
VENDA_STATUS_RESERVA_CHASSI = (
    VENDA_STATUS_INCOMPLETO,
    VENDA_STATUS_COTACAO, VENDA_STATUS_CONFIRMADO, VENDA_STATUS_FATURADO,
)


class HoraVenda(db.Model):
    """Pedido de venda ao consumidor final. Header permite multi-item.

    Pode ser criada via:
      - Pedido manual (criar_venda_manual) -> nasce em COTACAO.
      - Upload de DANFE legado (importar_nf_saida_pdf) -> nasce em FATURADO.
    """
    __tablename__ = 'hora_venda'

    id = db.Column(db.Integer, primary_key=True)
    loja_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_loja.id'),
        nullable=True,  # NULL quando CNPJ emitente nao bate com HoraLoja cadastrada.
        index=True,
    )

    # Documento do destinatario: CPF (PF) ou CNPJ (PJ). Coluna String(14) comporta
    # ambos. Comentario "sempre pessoa física" antigo nao reflete mais a realidade
    # — desde NF #727 (2026-04-28) PJ tambem e aceito. Tipo se infere via
    # `app/hora/services/tagplus/_documento.normalizar_documento`.
    cpf_cliente = db.Column(db.String(14), nullable=False, index=True)
    nome_cliente = db.Column(db.String(200), nullable=False)
    telefone_cliente = db.Column(db.String(20), nullable=True)
    email_cliente = db.Column(db.String(120), nullable=True)

    # Indica se o destinatario eh consumidor final (B2C) ou nao (B2B / revenda).
    # Migration hora_36 (2026-05-07).
    #   NULL  -> nao informado; payload_builder infere via CPF/CNPJ
    #            (CPF=True, CNPJ=False).
    #   TRUE  -> consumidor final explicito (PF tipico ou PJ-uso-proprio).
    #   FALSE -> nao-consumidor (PJ-revenda; SEFAZ exige IE / outros campos).
    # UI no formulario `/tagplus/pedido-venda/novo` define o default client-side
    # via tipo do documento e operador pode sobrescrever.
    consumidor_final = db.Column(db.Boolean, nullable=True)

    data_venda = db.Column(db.Date, nullable=False, default=agora_utc_naive, index=True)
    forma_pagamento = db.Column(
        db.String(20), nullable=False, default='NAO_INFORMADO',
    )
    # Valores: PIX, CARTAO_CREDITO, DINHEIRO, MISTO, NAO_INFORMADO.
    # Default cobre import via DANFE (parser nao extrai <pag><detPag>); operador
    # edita manualmente pos-import na tela de detalhe.

    # ---- Frete e parcelamento (TagPlus POST /nfes) ----
    modalidade_frete = db.Column(
        db.String(1), nullable=False, default='9', server_default='9',
    )
    # TagPlus enum: '0' Contratacao Remetente (CIF), '1' Destinatario (FOB),
    # '2' Terceiros, '3' Proprio Remetente, '4' Proprio Destinatario, '9' Sem
    # Ocorrencia. Default '9' preserva comportamento anterior hardcoded.
    numero_parcelas = db.Column(
        db.Integer, nullable=False, default=1, server_default='1',
    )
    # 1..60. NF #738 emitida com 18 parcelas. PayloadBuilder gera N parcelas
    # com vencimentos espacados por intervalo_parcelas_dias.
    intervalo_parcelas_dias = db.Column(
        db.Integer, nullable=False, default=30, server_default='30',
    )
    # 1..90. Mensal=30, semanal=7, diario=1. NF #738 usou intervalo=1.

    # ---- Frete CIF (migration hora_38) ----
    # valor_frete: valor monetario do frete (R$). Aplicavel quando
    #   modalidade_frete == '0' (CIF). NULL para FOB / sem ocorrencia /
    #   pedidos legados.
    # tipo_frete_calc: como o valor da moto se relaciona com o frete:
    #   'INCLUSO'   -> valor da moto JA inclui o frete (UI compara
    #                  preco - frete vs tabela).
    #   'ADICIONAR' -> frete e somado ao valor da moto (UI rateia o frete
    #                  entre os itens do pedido).
    #   NULL        -> nao aplicavel ou nao informado.
    # Validacao da combinacao (tipo_frete_calc != NULL exige modalidade='0',
    # valor_frete >= 0) ocorre em venda_service.
    valor_frete = db.Column(db.Numeric(15, 2), nullable=True)
    tipo_frete_calc = db.Column(db.String(10), nullable=True)

    valor_total = db.Column(db.Numeric(15, 2), nullable=False)
    # Soma de hora_venda_item.preco_final (validado em serviço).

    nf_saida_numero = db.Column(db.String(20), nullable=True, index=True)
    nf_saida_chave_44 = db.Column(db.String(44), nullable=True, unique=True)
    nf_saida_emitida_em = db.Column(db.DateTime, nullable=True)

    # Auditoria do import (paralela a HoraNfEntrada).
    arquivo_pdf_s3_key = db.Column(db.String(500), nullable=True)
    parser_usado = db.Column(db.String(50), nullable=True)
    # Ex.: 'danfe_pdf_parser_v1'.
    parseada_em = db.Column(db.DateTime, nullable=True)

    cnpj_emitente = db.Column(db.String(20), nullable=True, index=True)
    # CNPJ impresso na NF (para corrigir loja_id quando o import falha em casar).

    status = db.Column(db.String(20), nullable=False, default=VENDA_STATUS_COTACAO, index=True)
    # Valores: COTACAO (default), CONFIRMADO, FATURADO, CANCELADO.
    # Migration hora_20_pedido_workflow.sql converteu legados:
    #   CONCLUIDA + nf_saida_chave_44 -> FATURADO
    #   CONCLUIDA sem chave           -> CONFIRMADO
    #   DEVOLVIDA                     -> CANCELADO

    # ---- Marcos de transicao (timestamp + autor) ----
    confirmado_em = db.Column(db.DateTime, nullable=True)
    confirmado_por = db.Column(db.String(100), nullable=True)
    faturado_em = db.Column(db.DateTime, nullable=True)
    cancelado_em = db.Column(db.DateTime, nullable=True)
    cancelado_por = db.Column(db.String(100), nullable=True)
    cancelamento_motivo = db.Column(db.String(500), nullable=True)

    vendedor = db.Column(db.String(100), nullable=True)
    # Preenchido manualmente na tela de detalhe pos-import OU via backfill
    # de pedido TagPlus (vendedor.nome em GET /pedidos/{id}).
    observacoes = db.Column(db.Text, nullable=True)

    # ----- Enriquecimento via GET /pedidos/{id} TagPlus -----
    tagplus_pedido_id = db.Column(db.Integer, nullable=True, index=True)
    # ID do pedido auto-criado pelo TagPlus quando NFe e confirmada.
    # Redundancia controlada com hora_tagplus_nfe_emissao.tagplus_pedido_id
    # para queries diretas em hora_venda sem JOIN.
    tagplus_pedido_payload = db.Column(JSONB, nullable=True)
    # JSON bruto do GET /pedidos/{id} para auditoria + reprocessamento.
    # Sanitizar com sanitize_for_json antes de atribuir.
    tagplus_departamento = db.Column(db.String(100), nullable=True, index=True)
    # departamento.descricao raw vinda do pedido TagPlus (ex.: "Praia Grande").
    # Base para de-para hora_tagplus_departamento_map.departamento_norm ->
    # loja_id real (REGRA FISCAL: cnpj_emitente sempre matriz, loja fisica
    # vem do departamento).

    # --------------------------------------------------------------
    # Endereco do destinatario (cliente)
    # --------------------------------------------------------------
    # Preenchido no fluxo manual (tela "Novo Pedido de Venda" no menu
    # Faturamento). NULL para vendas legacy importadas via DANFE — o parser
    # CarVia nao extrai endereco do destinatario do PDF. Quando preenchidos,
    # o PayloadBuilder usa estes campos para criar o cliente no TagPlus
    # (POST /clientes com enderecos[]).
    cep = db.Column(db.String(9), nullable=True)
    endereco_logradouro = db.Column(db.String(255), nullable=True)
    endereco_numero = db.Column(db.String(20), nullable=True)
    endereco_complemento = db.Column(db.String(100), nullable=True)
    endereco_bairro = db.Column(db.String(100), nullable=True)
    endereco_cidade = db.Column(db.String(100), nullable=True)
    endereco_uf = db.Column(db.String(2), nullable=True)

    # Discriminador da fonte: 'DANFE' (import legacy) | 'MANUAL' (novo fluxo).
    origem_criacao = db.Column(db.String(20), nullable=True, default='DANFE', index=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    loja = db.relationship('HoraLoja', backref='vendas')
    itens = db.relationship(
        'HoraVendaItem',
        backref='venda',
        cascade='all, delete-orphan',
    )
    divergencias = db.relationship(
        'HoraVendaDivergencia',
        backref='venda',
        cascade='all, delete-orphan',
        order_by='HoraVendaDivergencia.criado_em.desc()',
    )

    @property
    def divergencias_abertas(self):
        return [d for d in self.divergencias if d.resolvida_em is None]

    @property
    def tem_divergencia_aberta(self) -> bool:
        return any(d.resolvida_em is None for d in self.divergencias)

    def __repr__(self):
        return f'<HoraVenda {self.id} loja={self.loja_id} R${self.valor_total}>'


class HoraVendaItem(db.Model):
    """Linha de venda: um chassi vendido.

    Preserva a trilha de preço: preco_tabela_referencia (vigente) ← desconto_aplicado
    ← preco_final. Permite auditoria "por que vendeu R$X abaixo da tabela?".
    """
    __tablename__ = 'hora_venda_item'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_venda.id'),
        nullable=False,
        index=True,
    )
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False,
        index=True,
    )
    # NAO ha UNIQUE em numero_chassi: pedido cancelado devolve o chassi ao
    # estoque, permitindo nova venda. Defesa contra double-sell:
    #   1) SELECT FOR UPDATE no hora_moto em criar_venda_manual /
    #      adicionar_item_pedido / editar_item_pedido (venda_service.py).
    #   2) Validacao de ultimo evento em EVENTOS_EM_ESTOQUE (estoque_service.py).

    tabela_preco_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_tabela_preco.id'),
        nullable=True,
    )
    # Referência à linha de preço vigente usada (auditoria).

    preco_tabela_referencia = db.Column(db.Numeric(15, 2), nullable=False)
    desconto_aplicado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    desconto_percentual = db.Column(
        db.Numeric(5, 2), nullable=False, default=0, server_default='0',
    )
    # Migration hora_33: percentual de desconto sobre o preço de tabela.
    # Sempre coerente com `desconto_aplicado` (R$): pct = desconto_aplicado / preco_tabela_referencia * 100.
    # Operador pode preencher % OU R$ no formulario; o JS sincroniza ambos
    # antes do submit, e o backend grava os 2 valores ja consistentes.

    preco_final = db.Column(db.Numeric(15, 2), nullable=False)
    # Invariante: preco_final = preco_tabela_referencia - desconto_aplicado.

    moto = db.relationship('HoraMoto', backref='venda_item')
    tabela_preco = db.relationship('HoraTabelaPreco')

    def __repr__(self):
        return (
            f'<HoraVendaItem venda={self.venda_id} chassi={self.numero_chassi} '
            f'final=R${self.preco_final}>'
        )


class HoraVendaDivergencia(db.Model):
    """Divergencia derivada no import da NF de saida.

    Fluxo permissivo: o import NAO rejeita problemas; registra divergencia aqui
    e segue. Operador revisa na tela de detalhe e marca como resolvida apos
    tomar acao (ex.: corrigir loja, cancelar venda, aceitar como esta).

    Tipos:
      CHASSI_NAO_CADASTRADO  — chassi da NF nunca entrou na HORA (get_or_create_moto criou)
      CHASSI_INDISPONIVEL    — ultimo evento do chassi NAO em EVENTOS_EM_ESTOQUE
      LOJA_DIVERGENTE        — chassi esta em loja diferente da emitente da NF
      CNPJ_DESCONHECIDO      — emitente nao bate com HoraLoja ativa (venda com loja_id=NULL)
      TABELA_PRECO_AUSENTE   — sem HoraTabelaPreco vigente na data; preco_tabela_ref = preco_final
    """
    __tablename__ = 'hora_venda_divergencia'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_venda.id'),
        nullable=False,
        index=True,
    )
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=True,  # NULL para CNPJ_DESCONHECIDO (nao tem chassi).
        index=True,
    )
    tipo = db.Column(db.String(30), nullable=False, index=True)
    detalhe = db.Column(db.Text, nullable=True)
    valor_esperado = db.Column(db.String(200), nullable=True)
    valor_conferido = db.Column(db.String(200), nullable=True)

    resolvida_em = db.Column(db.DateTime, nullable=True)
    resolvida_por = db.Column(db.String(100), nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    moto = db.relationship('HoraMoto', backref='venda_divergencias')

    __table_args__ = (
        db.UniqueConstraint(
            'venda_id', 'tipo', 'numero_chassi',
            name='uq_hora_venda_divergencia_tipo_chassi',
        ),
    )

    @property
    def aberta(self) -> bool:
        return self.resolvida_em is None

    def __repr__(self):
        estado = 'aberta' if self.aberta else 'resolvida'
        return (
            f'<HoraVendaDivergencia venda={self.venda_id} tipo={self.tipo} '
            f'chassi={self.numero_chassi} {estado}>'
        )


class HoraVendaAuditoria(db.Model):
    """Auditoria append-only de transicoes e edicoes em HoraVenda.

    Padrao identico a hora_transferencia_auditoria e hora_recebimento_auditoria.
    Acoes registradas: ver `app/hora/services/venda_audit.py`.
    """
    __tablename__ = 'hora_venda_auditoria'

    id = db.Column(db.BigInteger, primary_key=True)
    venda_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_venda.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    item_id = db.Column(
        db.Integer, db.ForeignKey('hora_venda_item.id'),
        nullable=True, index=True,
    )
    usuario = db.Column(db.String(100), nullable=False)
    acao = db.Column(db.String(40), nullable=False, index=True)
    campo_alterado = db.Column(db.String(60), nullable=True)
    valor_antes = db.Column(db.Text, nullable=True)
    valor_depois = db.Column(db.Text, nullable=True)
    detalhe = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    venda = db.relationship(
        'HoraVenda',
        backref=db.backref(
            'auditoria',
            cascade='all, delete-orphan',
            lazy='selectin',
            order_by='HoraVendaAuditoria.criado_em.desc()',
        ),
    )

    def __repr__(self):
        return (
            f'<HoraVendaAuditoria venda={self.venda_id} acao={self.acao} '
            f'usuario={self.usuario}>'
        )


class HoraVendaPagamento(db.Model):
    """Pagamento parcial de uma venda (1:N com HoraVenda).

    Migration hora_34 (2026-05-07): permite registrar N formas de pagamento
    em 1 pedido. Soma dos valores deve igualar `HoraVenda.valor_total` para
    o pedido sair de status INCOMPLETO. Cada forma pode ter parcelas proprias
    e, quando exige_aut_id=True na forma, requer `aut_id` preenchido.

    Exemplo (pedido R$10.000):
      - DINHEIRO R$3.000 (1x)
      - PIX_AVISTA R$2.500 (1x)
      - CARTAO_CREDITO R$4.500 (12x, aut_id='123456')
    """
    __tablename__ = 'hora_venda_pagamento'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_venda.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    forma_pagamento_hora = db.Column(db.String(20), nullable=False)
    # Sem FK formal para hora_tagplus_forma_pagamento_map para preservar
    # historicidade — se a forma for renomeada/removida, o pagamento mantem
    # o nome usado no momento do pedido.

    valor = db.Column(db.Numeric(15, 2), nullable=False)
    numero_parcelas = db.Column(db.Integer, nullable=False, default=1)
    aut_id = db.Column(db.String(50), nullable=True)
    # Numero de autorizacao / comprovante. Obrigatorio quando a forma de
    # pagamento esta marcada com `exige_aut_id=True` em
    # HoraTagPlusFormaPagamentoMap.

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    venda = db.relationship(
        'HoraVenda',
        backref=db.backref(
            'pagamentos',
            cascade='all, delete-orphan',
            lazy='selectin',
            order_by='HoraVendaPagamento.id',
        ),
    )

    @property
    def forma_map(self):
        """Lookup tardio do mapeamento TagPlus (tipo + exige_aut_id).

        Pode retornar None se a forma foi removida do cadastro depois.
        """
        from app.hora.models.tagplus import HoraTagPlusFormaPagamentoMap
        return (
            HoraTagPlusFormaPagamentoMap.query
            .filter_by(forma_pagamento_hora=self.forma_pagamento_hora)
            .first()
        )

    def __repr__(self):
        return (
            f'<HoraVendaPagamento venda={self.venda_id} '
            f'{self.forma_pagamento_hora}={self.valor} '
            f'({self.numero_parcelas}x)>'
        )

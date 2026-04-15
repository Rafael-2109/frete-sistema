"""
Modelos CTe Complementar e Custos de Entrega CarVia
"""

from sqlalchemy import func

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaCteComplementar(db.Model):
    """CTe Complementar — emitido ao cliente para cobrar custos extras de entrega"""
    __tablename__ = 'carvia_cte_complementares'

    id = db.Column(db.Integer, primary_key=True)
    numero_comp = db.Column(db.String(20), nullable=False, index=True)

    # Vinculo com CTe pai (obrigatorio)
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=False,
        index=True
    )

    # Vinculo com Fatura CarVia (mesma logica de CarviaOperacao.fatura_cliente_id)
    fatura_cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_cliente.id'),
        nullable=True,
        index=True
    )

    # Vinculo com Frete CarVia (equivalente a DespesaExtra.frete_id na Nacom)
    frete_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_fretes.id'),
        nullable=True,
        index=True
    )

    # CTe dados
    cte_numero = db.Column(db.String(20), index=True)
    cte_chave_acesso = db.Column(db.String(44), unique=True, nullable=True)
    ctrc_numero = db.Column(db.String(30), index=True)  # CTRC SSW/SEFAZ: CAR-{nCT}-{cDV}
    cte_valor = db.Column(db.Numeric(15, 2), nullable=False)
    cte_xml_path = db.Column(db.String(500))
    cte_xml_nome_arquivo = db.Column(db.String(255))
    cte_data_emissao = db.Column(db.Date)

    # Cliente (herdado da operacao, pode sobrescrever)
    cnpj_cliente = db.Column(db.String(20), index=True)
    nome_cliente = db.Column(db.String(255))

    # Status: RASCUNHO | EMITIDO | FATURADO | CANCELADO
    status = db.Column(db.String(20), nullable=False, default='RASCUNHO', index=True)

    # Auditoria
    observacoes = db.Column(db.Text)
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    operacao = db.relationship(
        'CarviaOperacao',
        backref=db.backref('ctes_complementares', lazy='dynamic')
    )
    fatura_cliente = db.relationship(
        'CarviaFaturaCliente',
        backref=db.backref('ctes_complementares', lazy='dynamic'),
        foreign_keys=[fatura_cliente_id]
    )
    custos_entrega = db.relationship(
        'CarviaCustoEntrega',
        backref='cte_complementar',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    @staticmethod
    def gerar_numero_comp():
        """Gera proximo numero sequencial COMP-###."""
        max_num = db.session.query(
            func.max(CarviaCteComplementar.numero_comp)
        ).filter(
            CarviaCteComplementar.numero_comp.ilike('COMP-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('COMP-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'COMP-{next_num:03d}'

    def __repr__(self):
        return f'<CarviaCteComplementar {self.numero_comp} ({self.status})>'


class CarviaCustoEntrega(db.Model):
    """Custos de entrega que CarVia pagou/incorreu — repassaveis ao cliente via CTe Complementar.

    Padrao espelhado de DespesaExtra (Nacom):
    - frete_id FK (equivalente a DespesaExtra.frete_id)
    - fatura_transportadora_id FK nullable (equivalente a DespesaExtra.fatura_frete_id)
    - Fluxo: criar sem fatura -> vincular fatura manualmente depois -> propagacao PAGO via FT

    STATUS:
    - PENDENTE: criado, sem fatura vinculada
    - VINCULADO_FT: vinculado a CarviaFaturaTransportadora, sera pago junto
    - PAGO: pago (via propagacao automatica da FT ou conciliacao direta)
    - CANCELADO: cancelado
    """
    __tablename__ = 'carvia_custos_entrega'

    TIPOS_CUSTO = [
        'DIARIA', 'REENTREGA', 'ARMAZENAGEM', 'DEVOLUCAO', 'AVARIA',
        'PEDAGIO_EXTRA', 'TAXA_DESCARGA', 'OUTROS'
    ]

    STATUS_CHOICES = ['PENDENTE', 'VINCULADO_FT', 'PAGO', 'CANCELADO']

    id = db.Column(db.Integer, primary_key=True)
    numero_custo = db.Column(db.String(20), nullable=False, index=True)

    # Vinculos
    # operacao_id NULLABLE:
    # - Preenchido automaticamente a partir de CarviaFrete.operacao_id quando o
    #   frete tem CTe CarVia vinculado (fluxo venda → elegivel para CTe Compl. SSW 222).
    # - None quando o frete nao tem CTe CarVia (fluxo compra puro).
    # Exigido pelo helper _executar_gerar_cte_complementar em custo_entrega_routes.py.
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=True,
        index=True
    )
    cte_complementar_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_cte_complementares.id'),
        nullable=True,
        index=True
    )

    # Tipo de custo
    tipo_custo = db.Column(db.String(50), nullable=False, index=True)
    descricao = db.Column(db.String(500))
    valor = db.Column(db.Numeric(15, 2), nullable=False)
    data_custo = db.Column(db.Date, nullable=False)
    data_vencimento = db.Column(db.Date)

    # Terceiro responsavel (quem CarVia pagou - opcional)
    fornecedor_nome = db.Column(db.String(255))
    fornecedor_cnpj = db.Column(db.String(20))

    # ================================================
    # DOCUMENTO DA DESPESA (xerox DespesaExtra Nacom)
    # ================================================
    # Sentinel 'PENDENTE_DOCUMENTO' / 'PENDENTE_FATURA' enquanto nao vinculado a FT
    tipo_documento = db.Column(db.String(20), nullable=True, default='PENDENTE_DOCUMENTO')
    numero_documento = db.Column(db.String(50), nullable=True, default='PENDENTE_FATURA')

    # ================================================
    # TRANSPORTADORA DO PAGAMENTO (override opcional — xerox DespesaExtra)
    # ================================================
    # Se NULL → usar transportadora do frete (comportamento padrao)
    # Se preenchido → usar esta transportadora (ex: devolucao coletada por outro)
    transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('transportadoras.id'),
        nullable=True,
        index=True
    )

    # Status: PENDENTE | PAGO | CANCELADO
    status = db.Column(db.String(20), nullable=False, default='PENDENTE', index=True)
    pago_por = db.Column(db.String(100))
    pago_em = db.Column(db.DateTime)

    # Vinculo com Frete CarVia (equivalente a DespesaExtra.frete_id na Nacom)
    frete_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_fretes.id'),
        nullable=True,
        index=True
    )

    # Vinculo com Subcontrato que cobra este custo (LEGADO — sera removido)
    # Substituido por fatura_transportadora_id direta (padrao DespesaExtra.fatura_frete_id)
    # Mantido ate migration destructive para preservar dados em rollout.
    subcontrato_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_subcontratos.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )

    # Vinculo com Fatura Transportadora (equivalente a DespesaExtra.fatura_frete_id na Nacom)
    # Nullable porque CE e criado sem fatura e vinculado manualmente depois.
    # ON DELETE SET NULL: se FT for hard-deleted, CE volta a PENDENTE para re-vinculacao.
    fatura_transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_transportadora.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )

    # Conciliacao bancaria
    total_conciliado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    conciliado = db.Column(db.Boolean, nullable=False, default=False)

    # Auditoria
    observacoes = db.Column(db.Text)
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    operacao = db.relationship(
        'CarviaOperacao',
        backref=db.backref('custos_entrega', lazy='dynamic')
    )
    anexos = db.relationship(
        'CarviaCustoEntregaAnexo',
        backref='custo_entrega',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    subcontrato = db.relationship(
        'CarviaSubcontrato',
        backref=db.backref('custos_entrega_cobertos', lazy='dynamic'),
        foreign_keys=[subcontrato_id]
    )
    fatura_transportadora = db.relationship(
        'CarviaFaturaTransportadora',
        backref=db.backref('custos_entrega', lazy='dynamic'),
        foreign_keys=[fatura_transportadora_id]
    )
    transportadora = db.relationship(
        'Transportadora',
        foreign_keys=[transportadora_id],
    )

    @property
    def pode_vincular_fatura(self):
        """Indica se este CE pode ser vinculado a uma CarviaFaturaTransportadora.

        Replica o padrao DespesaExtra.pode_lancar_odoo: um gate de transicao.
        CE deve estar PENDENTE e sem FT vinculada.
        """
        return self.status == 'PENDENTE' and self.fatura_transportadora_id is None

    @property
    def transportadora_efetiva(self):
        """Retorna a transportadora que deve receber pela despesa.

        Xerox de DespesaExtra.transportadora_efetiva: se transportadora_id
        estiver preenchido, usa essa; caso contrario, usa a transportadora
        do frete (comportamento padrao).
        """
        if self.transportadora_id:
            return self.transportadora
        if self.frete:
            return self.frete.transportadora
        return None

    @property
    def usa_transportadora_alternativa(self):
        """Indica se a despesa usa transportadora diferente do frete.

        Xerox de DespesaExtra.usa_transportadora_alternativa.
        """
        if not self.frete or self.transportadora_id is None:
            return False
        return self.transportadora_id != self.frete.transportadora_id

    @property
    def status_descricao(self):
        """Retorna descricao amigavel do status (xerox DespesaExtra)."""
        descricoes = {
            'PENDENTE': 'Pendente',
            'VINCULADO_FT': 'Vinculada a Fatura',
            'PAGO': 'Paga',
            'CANCELADO': 'Cancelada',
        }
        return descricoes.get(self.status, self.status)

    @staticmethod
    def gerar_numero_custo():
        """Gera proximo numero sequencial CE-###."""
        max_num = db.session.query(
            func.max(CarviaCustoEntrega.numero_custo)
        ).filter(
            CarviaCustoEntrega.numero_custo.ilike('CE-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('CE-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'CE-{next_num:03d}'

    def __repr__(self):
        return f'<CarviaCustoEntrega {self.numero_custo} {self.tipo_custo} ({self.status})>'


class CarviaCustoEntregaAnexo(db.Model):
    """Anexos comprovatorios de custo de entrega (fotos, PDFs, comprovantes via S3)"""
    __tablename__ = 'carvia_custo_entrega_anexos'

    id = db.Column(db.Integer, primary_key=True)
    custo_entrega_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_custos_entrega.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    nome_original = db.Column(db.String(255), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_s3 = db.Column(db.String(500), nullable=False)
    tamanho_bytes = db.Column(db.Integer, nullable=True)
    content_type = db.Column(db.String(100), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)

    # Metadados de email (nullable — populados apenas para .msg/.eml)
    email_remetente = db.Column(db.String(255), nullable=True)
    email_assunto = db.Column(db.String(500), nullable=True)
    email_data_envio = db.Column(db.DateTime, nullable=True)
    email_conteudo_preview = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f'<CarviaCustoEntregaAnexo {self.nome_original} ativo={self.ativo}>'


class CarviaEmissaoCteComplementar(db.Model):
    """Tracking de emissao automatica de CTe Complementar no SSW (opcao 222).

    Lifecycle: PENDENTE → EM_PROCESSAMENTO → SUCESSO | ERRO
    1 emissao por custo de entrega (1:1).
    """
    __tablename__ = 'carvia_emissao_cte_complementar'

    id = db.Column(db.Integer, primary_key=True)

    # Vinculos
    custo_entrega_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_custos_entrega.id'),
        nullable=False,
        index=True
    )
    cte_complementar_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_cte_complementares.id'),
        nullable=False,
        index=True
    )
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=False,
        index=True
    )

    # Dados para SSW opcao 222
    ctrc_pai = db.Column(db.String(30), nullable=False)  # CTRC do CTe original (ex: CAR-113-9)
    motivo_ssw = db.Column(db.String(5), nullable=False)  # C/D/E/R
    filial_ssw = db.Column(db.String(10), nullable=False, default='CAR')
    valor_calculado = db.Column(db.Numeric(15, 2), nullable=False)
    icms_aliquota_usada = db.Column(db.Numeric(5, 2))  # Snapshot do ICMS usado no calculo

    # Status: PENDENTE | EM_PROCESSAMENTO | SUCESSO | ERRO
    status = db.Column(db.String(20), nullable=False, default='PENDENTE', index=True)
    etapa = db.Column(db.String(30))  # PREENCHIMENTO | SEFAZ | CONSULTA_101
    job_id = db.Column(db.String(100))
    erro_ssw = db.Column(db.Text)
    resultado_json = db.Column(db.JSON)

    # Auditoria
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    custo_entrega = db.relationship(
        'CarviaCustoEntrega',
        backref=db.backref('emissao_cte_comp', uselist=False)
    )
    cte_complementar = db.relationship(
        'CarviaCteComplementar',
        backref=db.backref('emissao', uselist=False)
    )
    operacao = db.relationship('CarviaOperacao')

    def __repr__(self):
        return (
            f'<CarviaEmissaoCteComplementar {self.id} '
            f'custo={self.custo_entrega_id} ({self.status})>'
        )

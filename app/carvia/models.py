"""
Modelos do Modulo CarVia
========================

Gestao de frete subcontratado:
- NFs importadas (DANFE PDF / XML NF-e / Manual)
- Operacoes (1 CTe CarVia = N NFs do mesmo cliente/destino)
- Subcontratos (1 por transportadora por operacao)
- Faturas Cliente (CarVia -> cliente)
- Faturas Transportadora (subcontratado -> CarVia)
"""

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaNf(db.Model):
    """NFs importadas (mercadoria) — PDF DANFE, XML NF-e ou entrada manual"""
    __tablename__ = 'carvia_nfs'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    serie_nf = db.Column(db.String(5))
    chave_acesso_nf = db.Column(db.String(44), unique=True, nullable=True)
    data_emissao = db.Column(db.Date)

    # Emitente (remetente da carga)
    cnpj_emitente = db.Column(db.String(20), nullable=False, index=True)
    nome_emitente = db.Column(db.String(255))
    uf_emitente = db.Column(db.String(2))
    cidade_emitente = db.Column(db.String(100))

    # Destinatario
    cnpj_destinatario = db.Column(db.String(20), index=True)
    nome_destinatario = db.Column(db.String(255))
    uf_destinatario = db.Column(db.String(2))
    cidade_destinatario = db.Column(db.String(100))

    # Valores e pesos
    valor_total = db.Column(db.Numeric(15, 2))
    peso_bruto = db.Column(db.Numeric(15, 3))
    peso_liquido = db.Column(db.Numeric(15, 3))
    quantidade_volumes = db.Column(db.Integer)

    # Arquivos
    arquivo_pdf_path = db.Column(db.String(500))
    arquivo_xml_path = db.Column(db.String(500))
    arquivo_nome_original = db.Column(db.String(255))

    # Tipo de fonte: PDF_DANFE, XML_NFE, MANUAL
    tipo_fonte = db.Column(db.String(20), nullable=False)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relacionamentos
    operacoes = db.relationship(
        'CarviaOperacao',
        secondary='carvia_operacao_nfs',
        back_populates='nfs',
        lazy='dynamic'
    )

    def get_faturas_cliente(self):
        """Retorna faturas cliente que referenciam esta NF via itens."""
        return CarviaFaturaCliente.query.join(
            CarviaFaturaClienteItem,
            CarviaFaturaClienteItem.fatura_cliente_id == CarviaFaturaCliente.id
        ).filter(
            CarviaFaturaClienteItem.nf_id == self.id
        ).all()

    def get_faturas_transportadora(self):
        """Retorna faturas transportadora que referenciam esta NF via itens."""
        return CarviaFaturaTransportadora.query.join(
            CarviaFaturaTransportadoraItem,
            CarviaFaturaTransportadoraItem.fatura_transportadora_id == CarviaFaturaTransportadora.id
        ).filter(
            CarviaFaturaTransportadoraItem.nf_id == self.id
        ).all()

    def __repr__(self):
        return f'<CarviaNf {self.numero_nf} ({self.tipo_fonte})>'


class CarviaNfItem(db.Model):
    """Itens de produto da NF — extraidos do DANFE PDF ou XML NF-e"""
    __tablename__ = 'carvia_nf_itens'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_nfs.id'),
        nullable=False,
        index=True
    )

    # Produto
    codigo_produto = db.Column(db.String(60))
    descricao = db.Column(db.String(255))
    ncm = db.Column(db.String(10))
    cfop = db.Column(db.String(10))

    # Quantidades e valores
    unidade = db.Column(db.String(10))
    quantidade = db.Column(db.Numeric(15, 4))
    valor_unitario = db.Column(db.Numeric(15, 4))
    valor_total_item = db.Column(db.Numeric(15, 2))

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamento
    nf = db.relationship(
        'CarviaNf',
        backref=db.backref('itens', lazy='dynamic', cascade='all, delete-orphan')
    )

    def __repr__(self):
        return f'<CarviaNfItem {self.codigo_produto} qtd={self.quantidade}>'


class CarviaOperacao(db.Model):
    """Operacao principal — 1 CTe CarVia = N NFs do mesmo cliente/destino"""
    __tablename__ = 'carvia_operacoes'

    id = db.Column(db.Integer, primary_key=True)

    # CTe CarVia (pode ser NULL para entrada manual)
    cte_numero = db.Column(db.String(20), index=True)
    cte_chave_acesso = db.Column(db.String(44), unique=True, nullable=True)
    cte_valor = db.Column(db.Numeric(15, 2))
    cte_xml_path = db.Column(db.String(500))
    cte_xml_nome_arquivo = db.Column(db.String(255))
    cte_data_emissao = db.Column(db.Date)

    # Cliente (remetente da carga)
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255))

    # Rota
    uf_origem = db.Column(db.String(2))
    cidade_origem = db.Column(db.String(100))
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)

    # Pesos (nivel operacao, compartilhado entre subcontratos)
    peso_bruto = db.Column(db.Numeric(15, 3))
    peso_cubado = db.Column(db.Numeric(15, 3))
    peso_utilizado = db.Column(db.Numeric(15, 3))
    valor_mercadoria = db.Column(db.Numeric(15, 2))

    # Cubagem por dimensoes (opcional)
    cubagem_comprimento = db.Column(db.Numeric(10, 2))
    cubagem_largura = db.Column(db.Numeric(10, 2))
    cubagem_altura = db.Column(db.Numeric(10, 2))
    cubagem_fator = db.Column(db.Numeric(10, 2))
    cubagem_volumes = db.Column(db.Integer)

    # Tipo e status
    # IMPORTADO, MANUAL_SEM_CTE, MANUAL_FRETEIRO
    tipo_entrada = db.Column(db.String(30), nullable=False)
    # RASCUNHO, COTADO, CONFIRMADO, FATURADO, CANCELADO
    status = db.Column(db.String(20), nullable=False, default='RASCUNHO')

    # Fatura CarVia (ao cliente)
    fatura_cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_cliente.id'),
        nullable=True,
        index=True
    )

    # Auditoria
    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    nfs = db.relationship(
        'CarviaNf',
        secondary='carvia_operacao_nfs',
        back_populates='operacoes',
        lazy='dynamic'
    )
    subcontratos = db.relationship(
        'CarviaSubcontrato',
        backref='operacao',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    fatura_cliente = db.relationship(
        'CarviaFaturaCliente',
        backref='operacoes',
        foreign_keys=[fatura_cliente_id]
    )

    def calcular_peso_utilizado(self):
        """Calcula peso_utilizado = max(peso_bruto, peso_cubado)"""
        bruto = float(self.peso_bruto or 0)
        cubado = float(self.peso_cubado or 0)
        self.peso_utilizado = max(bruto, cubado)
        return self.peso_utilizado

    def calcular_cubagem(self):
        """Calcula peso cubado a partir das dimensoes"""
        if (self.cubagem_comprimento and self.cubagem_largura
                and self.cubagem_altura and self.cubagem_fator
                and self.cubagem_volumes):
            comp = float(self.cubagem_comprimento)
            larg = float(self.cubagem_largura)
            alt = float(self.cubagem_altura)
            fator = float(self.cubagem_fator)
            volumes = int(self.cubagem_volumes)
            if fator > 0:
                self.peso_cubado = (comp * larg * alt / fator) * volumes
                return float(self.peso_cubado)
        return None

    def __repr__(self):
        return f'<CarviaOperacao {self.id} CTe={self.cte_numero} ({self.status})>'


class CarviaOperacaoNf(db.Model):
    """Junction N:N — Operacao <-> NFs"""
    __tablename__ = 'carvia_operacao_nfs'

    id = db.Column(db.Integer, primary_key=True)
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=False,
        index=True
    )
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_nfs.id'),
        nullable=False,
        index=True
    )
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint('operacao_id', 'nf_id', name='uq_operacao_nf'),
    )


class CarviaSubcontrato(db.Model):
    """Subcontratacao — 1 por transportadora por operacao"""
    __tablename__ = 'carvia_subcontratos'

    id = db.Column(db.Integer, primary_key=True)
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=False,
        index=True
    )

    # Transportadora subcontratada
    transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('transportadoras.id'),
        nullable=False,
        index=True
    )

    # Numeracao sequencial por transportadora (auto-increment logico)
    numero_sequencial_transportadora = db.Column(db.Integer, nullable=True)

    # CTe do subcontratado (pode ser NULL para freteiro)
    cte_numero = db.Column(db.String(20), index=True)
    cte_chave_acesso = db.Column(db.String(44), unique=True, nullable=True)
    cte_valor = db.Column(db.Numeric(15, 2))
    cte_xml_path = db.Column(db.String(500))
    cte_xml_nome_arquivo = db.Column(db.String(255))
    cte_data_emissao = db.Column(db.Date)

    # Cotacao
    valor_cotado = db.Column(db.Numeric(15, 2))
    tabela_frete_id = db.Column(
        db.Integer,
        db.ForeignKey('tabelas_frete.id'),
        nullable=True
    )
    valor_acertado = db.Column(db.Numeric(15, 2))

    # Fatura do subcontratado
    fatura_transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_transportadora.id'),
        nullable=True,
        index=True
    )

    # PENDENTE, COTADO, CONFIRMADO, FATURADO, CONFERIDO, CANCELADO
    status = db.Column(db.String(20), nullable=False, default='PENDENTE')

    # Auditoria
    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    transportadora = db.relationship('Transportadora', lazy='joined')
    fatura_transportadora = db.relationship(
        'CarviaFaturaTransportadora',
        backref='subcontratos',
        foreign_keys=[fatura_transportadora_id]
    )

    @property
    def valor_final(self):
        """Retorna valor_acertado se existir, senao valor_cotado"""
        if self.valor_acertado is not None:
            return self.valor_acertado
        return self.valor_cotado

    def __repr__(self):
        return f'<CarviaSubcontrato {self.id} op={self.operacao_id} ({self.status})>'


class CarviaFaturaCliente(db.Model):
    """Faturas CarVia emitidas ao cliente — agrupa N CTes CarVia"""
    __tablename__ = 'carvia_faturas_cliente'

    id = db.Column(db.Integer, primary_key=True)
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255))
    numero_fatura = db.Column(db.String(50), nullable=False, index=True)
    data_emissao = db.Column(db.Date, nullable=False)
    valor_total = db.Column(db.Numeric(15, 2), nullable=False)
    vencimento = db.Column(db.Date)
    arquivo_pdf_path = db.Column(db.String(500))
    arquivo_nome_original = db.Column(db.String(255))

    # Campos adicionais extraidos do PDF SSW
    tipo_frete = db.Column(db.String(10))  # CIF ou FOB
    quantidade_documentos = db.Column(db.Integer)
    valor_mercadoria = db.Column(db.Numeric(15, 2))
    valor_icms = db.Column(db.Numeric(15, 2))
    aliquota_icms = db.Column(db.String(20))  # Ex: "12.00%"
    valor_pedagio = db.Column(db.Numeric(15, 2))
    vencimento_original = db.Column(db.Date)
    cancelada = db.Column(db.Boolean, default=False)

    # Dados do pagador (cliente que paga a fatura)
    pagador_endereco = db.Column(db.String(500))
    pagador_cep = db.Column(db.String(10))
    pagador_cidade = db.Column(db.String(100))
    pagador_uf = db.Column(db.String(2))
    pagador_ie = db.Column(db.String(20))
    pagador_telefone = db.Column(db.String(30))

    # PENDENTE, EMITIDA, PAGA, CANCELADA
    status = db.Column(db.String(20), default='PENDENTE')

    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relacionamentos
    itens = db.relationship(
        'CarviaFaturaClienteItem',
        backref='fatura_cliente',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<CarviaFaturaCliente {self.numero_fatura} ({self.status})>'


class CarviaFaturaClienteItem(db.Model):
    """Itens de detalhe por CTe de uma fatura cliente SSW"""
    __tablename__ = 'carvia_fatura_cliente_itens'

    id = db.Column(db.Integer, primary_key=True)
    fatura_cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_cliente.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # CTe referenciado
    cte_numero = db.Column(db.String(20))
    cte_data_emissao = db.Column(db.Date)

    # Contraparte: Remetente (FOB) ou Destinatario (CIF)
    contraparte_cnpj = db.Column(db.String(20))
    contraparte_nome = db.Column(db.String(255))

    # NF referenciada
    nf_numero = db.Column(db.String(20))

    # FKs para linking cross-documento
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=True,
        index=True
    )
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_nfs.id'),
        nullable=True,
        index=True
    )

    # Valores
    valor_mercadoria = db.Column(db.Numeric(15, 2))
    peso_kg = db.Column(db.Numeric(15, 3))
    base_calculo = db.Column(db.Numeric(15, 2))
    icms = db.Column(db.Numeric(15, 2))
    iss = db.Column(db.Numeric(15, 2))
    st = db.Column(db.Numeric(15, 2))
    frete = db.Column(db.Numeric(15, 2))

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamentos de linking
    operacao = db.relationship('CarviaOperacao', lazy='joined')
    nf = db.relationship('CarviaNf', lazy='joined')

    def __repr__(self):
        return f'<CarviaFaturaClienteItem cte={self.cte_numero} fatura={self.fatura_cliente_id}>'


class CarviaFaturaTransportadoraItem(db.Model):
    """Itens de detalhe por subcontrato de uma fatura transportadora"""
    __tablename__ = 'carvia_fatura_transportadora_itens'

    id = db.Column(db.Integer, primary_key=True)
    fatura_transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_transportadora.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # FKs para linking cross-documento
    subcontrato_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_subcontratos.id'),
        nullable=True,
        index=True
    )
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=True,
        index=True
    )
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_nfs.id'),
        nullable=True,
        index=True
    )

    # CTe referenciado (display)
    cte_numero = db.Column(db.String(20))
    cte_data_emissao = db.Column(db.Date)

    # Contraparte: cliente da operacao
    contraparte_cnpj = db.Column(db.String(20))
    contraparte_nome = db.Column(db.String(255))

    # NF referenciada (display)
    nf_numero = db.Column(db.String(20))

    # Valores
    valor_mercadoria = db.Column(db.Numeric(15, 2))
    peso_kg = db.Column(db.Numeric(15, 3))
    valor_frete = db.Column(db.Numeric(15, 2))
    valor_cotado = db.Column(db.Numeric(15, 2))
    valor_acertado = db.Column(db.Numeric(15, 2))

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamentos
    subcontrato = db.relationship('CarviaSubcontrato', lazy='joined')
    operacao = db.relationship('CarviaOperacao', lazy='joined')
    nf = db.relationship('CarviaNf', lazy='joined')

    def __repr__(self):
        return f'<CarviaFaturaTransportadoraItem sub={self.subcontrato_id} fatura={self.fatura_transportadora_id}>'


class CarviaDespesa(db.Model):
    """Despesas operacionais da empresa no modulo CarVia"""
    __tablename__ = 'carvia_despesas'

    id = db.Column(db.Integer, primary_key=True)
    tipo_despesa = db.Column(db.String(50), nullable=False, index=True)
    # CONTABILIDADE, GRIS, SEGURO, OUTROS
    descricao = db.Column(db.String(500))
    valor = db.Column(db.Numeric(15, 2), nullable=False)

    data_despesa = db.Column(db.Date, nullable=False)
    data_vencimento = db.Column(db.Date)
    status = db.Column(db.String(20), default='PENDENTE', index=True)
    # PENDENTE, PAGO, CANCELADO

    observacoes = db.Column(db.Text)
    criado_por = db.Column(db.String(150))
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    def __repr__(self):
        return f'<CarviaDespesa {self.id} {self.tipo_despesa} ({self.status})>'


class CarviaFaturaTransportadora(db.Model):
    """Faturas recebidas dos subcontratados — agrupa N CTes de 1 transportadora"""
    __tablename__ = 'carvia_faturas_transportadora'

    id = db.Column(db.Integer, primary_key=True)
    transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('transportadoras.id'),
        nullable=False
    )
    numero_fatura = db.Column(db.String(50), nullable=False, index=True)
    data_emissao = db.Column(db.Date, nullable=False)
    valor_total = db.Column(db.Numeric(15, 2), nullable=False)
    vencimento = db.Column(db.Date)
    arquivo_pdf_path = db.Column(db.String(500))
    arquivo_nome_original = db.Column(db.String(255))

    # PENDENTE, EM_CONFERENCIA, CONFERIDO, DIVERGENTE
    status_conferencia = db.Column(db.String(20), default='PENDENTE')
    conferido_por = db.Column(db.String(100))
    conferido_em = db.Column(db.DateTime)

    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relacionamentos
    transportadora = db.relationship('Transportadora', lazy='joined')
    itens = db.relationship(
        'CarviaFaturaTransportadoraItem',
        backref='fatura_transportadora',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<CarviaFaturaTransportadora {self.numero_fatura} ({self.status_conferencia})>'

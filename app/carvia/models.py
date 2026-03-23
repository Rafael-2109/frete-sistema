"""
Modelos do Modulo CarVia
========================

Gestao de frete subcontratado:
- NFs importadas (DANFE PDF / XML NF-e / Manual)
- Operacoes (1 CTe CarVia = N NFs do mesmo cliente/destino)
- Subcontratos (1 por transportadora por operacao)
- Faturas Cliente (CarVia -> cliente)
- Faturas Transportadora (subcontratado -> CarVia)

GAP-20 — DECISAO DE DESIGN: AUSENCIA INTENCIONAL DE DELETE
Nenhuma entidade CarVia possui endpoint de exclusao. Registros sao CANCELADOS
(status='CANCELADO') em vez de deletados. Motivos:
1. Rastreabilidade: historico completo de operacoes para auditoria fiscal
2. Integridade referencial: NFs, CTes, faturas e subcontratos interligados por FKs
3. Documentos fiscais (NF-e, CT-e) nao podem ser apagados por regulamentacao
Se exclusao for necessaria no futuro, implementar soft-delete com campo `excluido_em`.
"""

from sqlalchemy import func

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

    # Status: ATIVA, CANCELADA (soft-delete conforme GAP-20)
    status = db.Column(db.String(20), nullable=False, default='ATIVA', index=True)

    # Auditoria de cancelamento
    cancelado_em = db.Column(db.DateTime)
    cancelado_por = db.Column(db.String(100))
    motivo_cancelamento = db.Column(db.Text)

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
    cte_pdf_path = db.Column(db.String(500))
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

    # NFs referenciadas no CTe XML (persistido para re-linking retroativo)
    # Formato: [{"chave": "44dig", "numero_nf": "123", "cnpj_emitente": "14dig"}]
    nfs_referenciadas_json = db.Column(db.JSON)

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
    # GAP-07: cascade='all, delete-orphan' e INTENCIONAL. SQLAlchemy gerencia
    # o ciclo de vida dos subcontratos via ORM. O DB nao aciona cascade
    # (FK sem ON DELETE CASCADE) — a remocao e feita pelo session.delete() do ORM.
    # Na pratica, operacoes nunca sao deletadas (GAP-20: design sem DELETE).
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

    @staticmethod
    def gerar_numero_cte():
        """Gera proximo numero sequencial CTe-###."""
        max_num = db.session.query(
            func.max(CarviaOperacao.cte_numero)
        ).filter(
            CarviaOperacao.cte_numero.ilike('CTe-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('CTe-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'CTe-{next_num:03d}'

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
    # GAP-08: ondelete='CASCADE' — ao deletar NF, remove junctions automaticamente
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_nfs.id', ondelete='CASCADE'),
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
    cte_pdf_path = db.Column(db.String(500))
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

    # Conferencia individual (CTe vs TabelaFrete)
    valor_considerado = db.Column(db.Numeric(15, 2), nullable=True)
    status_conferencia = db.Column(db.String(20), nullable=False, default='PENDENTE')
    conferido_por = db.Column(db.String(100), nullable=True)
    conferido_em = db.Column(db.DateTime, nullable=True)
    detalhes_conferencia = db.Column(db.JSON, nullable=True)

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

    @staticmethod
    def gerar_numero_sub():
        """Gera proximo numero sequencial Sub-###."""
        max_num = db.session.query(
            func.max(CarviaSubcontrato.cte_numero)
        ).filter(
            CarviaSubcontrato.cte_numero.ilike('Sub-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('Sub-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'Sub-{next_num:03d}'

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

    __table_args__ = (
        db.UniqueConstraint('numero_fatura', 'cnpj_cliente', name='uq_fatura_cliente_num_cnpj'),
    )

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

    # PENDENTE, PAGA, CANCELADA (GAP-01: EMITIDA removido — status morto no fluxo)
    status = db.Column(db.String(20), default='PENDENTE')

    # Auditoria de pagamento
    pago_por = db.Column(db.String(100))
    pago_em = db.Column(db.DateTime)

    # Conciliacao bancaria
    total_conciliado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    conciliado = db.Column(db.Boolean, nullable=False, default=False)

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

    @staticmethod
    def gerar_numero_fatura():
        """Gera proximo numero sequencial FAT-###."""
        max_num = db.session.query(
            func.max(CarviaFaturaCliente.numero_fatura)
        ).filter(
            CarviaFaturaCliente.numero_fatura.ilike('FAT-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('FAT-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'FAT-{next_num:03d}'

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

    # Auditoria de pagamento
    pago_por = db.Column(db.String(100))
    pago_em = db.Column(db.DateTime)

    # Conciliacao bancaria
    total_conciliado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    conciliado = db.Column(db.Boolean, nullable=False, default=False)

    observacoes = db.Column(db.Text)
    criado_por = db.Column(db.String(150))
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    def __repr__(self):
        return f'<CarviaDespesa {self.id} {self.tipo_despesa} ({self.status})>'


class CarviaReceita(db.Model):
    """Receitas operacionais diversas da empresa no modulo CarVia (espelho de despesas)"""
    __tablename__ = 'carvia_receitas'

    id = db.Column(db.Integer, primary_key=True)
    tipo_receita = db.Column(db.String(50), nullable=False, index=True)
    # Campo texto livre (comissoes, reembolsos, bonificacoes, etc.)
    descricao = db.Column(db.String(500))
    valor = db.Column(db.Numeric(15, 2), nullable=False)

    data_receita = db.Column(db.Date, nullable=False)
    data_vencimento = db.Column(db.Date)
    status = db.Column(db.String(20), default='PENDENTE', index=True)
    # PENDENTE, RECEBIDO, CANCELADO

    # Auditoria de recebimento
    recebido_por = db.Column(db.String(100))
    recebido_em = db.Column(db.DateTime)

    # Conciliacao bancaria
    total_conciliado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    conciliado = db.Column(db.Boolean, nullable=False, default=False)

    observacoes = db.Column(db.Text)
    criado_por = db.Column(db.String(150))
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    def __repr__(self):
        return f'<CarviaReceita {self.id} {self.tipo_receita} ({self.status})>'


class CarviaFaturaTransportadora(db.Model):
    """Faturas recebidas dos subcontratados — agrupa N CTes de 1 transportadora"""
    __tablename__ = 'carvia_faturas_transportadora'

    __table_args__ = (
        db.UniqueConstraint('numero_fatura', 'transportadora_id', name='uq_fatura_transp_num_transp'),
    )

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

    # Status de pagamento (independente de status_conferencia)
    # PENDENTE, PAGO
    status_pagamento = db.Column(db.String(20), default='PENDENTE', index=True)
    pago_por = db.Column(db.String(100))
    pago_em = db.Column(db.DateTime)

    # Conciliacao bancaria
    total_conciliado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    conciliado = db.Column(db.Boolean, nullable=False, default=False)

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

    @staticmethod
    def gerar_numero_fatura():
        """Gera proximo numero sequencial FTRANSP-###."""
        max_num = db.session.query(
            func.max(CarviaFaturaTransportadora.numero_fatura)
        ).filter(
            CarviaFaturaTransportadora.numero_fatura.ilike('FTRANSP-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('FTRANSP-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'FTRANSP-{next_num:03d}'

    def __repr__(self):
        return f'<CarviaFaturaTransportadora {self.numero_fatura} ({self.status_conferencia})>'


# CarviaSessaoCotacao e CarviaSessaoDemanda: REMOVIDOS (feature obsoleta, 22/03/2026)
# Tabelas permanecem no banco para historico. Models deletados.
# Migration: scripts/migrations/dropar_sessao_cotacao_carvia.sql (quando conveniente)


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
    """Custos de entrega que CarVia pagou/incorreu — repassaveis ao cliente via CTe Complementar"""
    __tablename__ = 'carvia_custos_entrega'

    TIPOS_CUSTO = [
        'DIARIA', 'REENTREGA', 'ARMAZENAGEM', 'DEVOLUCAO', 'AVARIA',
        'PEDAGIO_EXTRA', 'TAXA_DESCARGA', 'OUTROS'
    ]

    id = db.Column(db.Integer, primary_key=True)
    numero_custo = db.Column(db.String(20), nullable=False, index=True)

    # Vinculos
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=False,
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

    def __repr__(self):
        return f'<CarviaCustoEntregaAnexo {self.nome_original} ativo={self.ativo}>'


class CarviaContaMovimentacao(db.Model):
    """Movimentacoes financeiras da conta CarVia — saldo calculado por SUM"""
    __tablename__ = 'carvia_conta_movimentacoes'

    id = db.Column(db.Integer, primary_key=True)
    tipo_doc = db.Column(db.String(30), nullable=False)
    # 'fatura_cliente' | 'fatura_transportadora' | 'despesa' | 'saldo_inicial' | 'ajuste'
    doc_id = db.Column(db.Integer, nullable=False)
    # FK conceitual (0 para saldo_inicial/ajuste)
    tipo_movimento = db.Column(db.String(10), nullable=False)
    # 'CREDITO' | 'DEBITO'
    valor = db.Column(db.Numeric(15, 2), nullable=False)
    # Sempre positivo
    descricao = db.Column(db.String(500))
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    # GAP-10: UNIQUE parcial — exclui 'ajuste' e 'saldo_inicial' para permitir multiplos
    # A constraint real e via partial unique index no banco (migration)
    __table_args__ = (
        db.Index(
            'uq_carvia_mov_tipo_doc_parcial',
            'tipo_doc', 'doc_id',
            unique=True,
            postgresql_where=db.text("tipo_doc NOT IN ('ajuste', 'saldo_inicial')"),
        ),
        db.CheckConstraint("tipo_movimento IN ('CREDITO', 'DEBITO')", name='ck_carvia_mov_tipo'),
        db.CheckConstraint('valor > 0', name='ck_carvia_mov_valor'),
        db.Index('ix_carvia_mov_criado_em', 'criado_em'),
    )

    def __repr__(self):
        return f'<CarviaContaMovimentacao {self.tipo_doc}:{self.doc_id} {self.tipo_movimento} {self.valor}>'


class CarviaExtratoLinha(db.Model):
    """Linhas importadas do extrato bancario OFX — base para conciliacao"""
    __tablename__ = 'carvia_extrato_linhas'

    id = db.Column(db.Integer, primary_key=True)
    fitid = db.Column(db.String(100), nullable=False, unique=True)
    data = db.Column(db.Date, nullable=False, index=True)
    valor = db.Column(db.Numeric(15, 2), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # CREDITO | DEBITO
    descricao = db.Column(db.String(500))
    memo = db.Column(db.String(500))
    checknum = db.Column(db.String(50))
    refnum = db.Column(db.String(50))
    trntype = db.Column(db.String(20))
    status_conciliacao = db.Column(
        db.String(20), nullable=False, default='PENDENTE', index=True
    )  # PENDENTE | CONCILIADO | PARCIAL
    total_conciliado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    arquivo_ofx = db.Column(db.String(255), nullable=False, index=True)
    conta_bancaria = db.Column(db.String(50))
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    # Enriquecimento via CSV bancario
    razao_social = db.Column(db.String(255))  # Contraparte (importado do CSV bancario)
    observacao = db.Column(db.Text)  # Notas livres do usuario

    # Relacionamentos
    conciliacoes = db.relationship(
        'CarviaConciliacao',
        backref='extrato_linha',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    @property
    def valor_absoluto(self):
        """Valor absoluto da linha (sem sinal)"""
        return abs(float(self.valor or 0))

    @property
    def saldo_a_conciliar(self):
        """Quanto falta conciliar nesta linha"""
        return self.valor_absoluto - float(self.total_conciliado or 0)

    def __repr__(self):
        return f'<CarviaExtratoLinha {self.fitid} {self.tipo} {self.valor}>'


class CarviaConciliacao(db.Model):
    """Junction N:N — vincula linha do extrato a documento financeiro"""
    __tablename__ = 'carvia_conciliacoes'

    id = db.Column(db.Integer, primary_key=True)
    extrato_linha_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_extrato_linhas.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    tipo_documento = db.Column(db.String(30), nullable=False)
    # fatura_cliente | fatura_transportadora | despesa
    documento_id = db.Column(db.Integer, nullable=False)
    valor_alocado = db.Column(db.Numeric(15, 2), nullable=False)
    conciliado_por = db.Column(db.String(100), nullable=False)
    conciliado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint(
            'extrato_linha_id', 'tipo_documento', 'documento_id',
            name='uq_carvia_conc_linha_doc'
        ),
        db.CheckConstraint('valor_alocado > 0', name='ck_carvia_conc_valor'),
        db.Index('ix_carvia_conc_doc', 'tipo_documento', 'documento_id'),
    )

    @property
    def numero_documento(self):
        """Numero human-readable do documento conciliado."""
        _PREFIXOS = {
            'fatura_cliente': 'FAT',
            'fatura_transportadora': 'FTRANSP',
            'despesa': 'DESP',
            'custo_entrega': 'CE',
        }
        prefixo = _PREFIXOS.get(self.tipo_documento, 'DOC')
        fallback = f'{prefixo}-{self.documento_id}'

        if self.tipo_documento == 'fatura_cliente':
            from app.carvia.models import CarviaFaturaCliente
            doc = db.session.get(CarviaFaturaCliente, self.documento_id)
            return doc.numero_fatura if doc else fallback
        elif self.tipo_documento == 'fatura_transportadora':
            from app.carvia.models import CarviaFaturaTransportadora
            doc = db.session.get(CarviaFaturaTransportadora, self.documento_id)
            return doc.numero_fatura if doc else fallback
        elif self.tipo_documento == 'despesa':
            return f'DESP-{self.documento_id:03d}'
        elif self.tipo_documento == 'custo_entrega':
            from app.carvia.models import CarviaCustoEntrega
            doc = db.session.get(CarviaCustoEntrega, self.documento_id)
            return doc.numero_custo if doc else fallback
        return fallback

    @property
    def url_documento(self):
        """URL da pagina de detalhe do documento."""
        _URLS = {
            'fatura_cliente': '/carvia/faturas-cliente/{}',
            'fatura_transportadora': '/carvia/faturas-transportadora/{}',
            'despesa': '/carvia/despesas/{}',
            'custo_entrega': '/carvia/custos-entrega/{}',
        }
        template = _URLS.get(self.tipo_documento)
        if template:
            return template.format(self.documento_id)
        return None

    def __repr__(self):
        return (
            f'<CarviaConciliacao linha={self.extrato_linha_id} '
            f'{self.tipo_documento}:{self.documento_id} {self.valor_alocado}>'
        )


class CarviaCategoriaMoto(db.Model):
    """Categorias/tipos de moto para precificacao por unidade (ex: Leve, Pesada, Scooter)"""
    __tablename__ = 'carvia_categorias_moto'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relationships
    modelos = db.relationship('CarviaModeloMoto', backref='categoria', lazy='dynamic')
    precos = db.relationship('CarviaPrecoCategoriaMoto', backref='categoria', lazy='dynamic')

    def __repr__(self):
        return f'<CarviaCategoriaMoto {self.nome} ordem={self.ordem}>'


class CarviaModeloMoto(db.Model):
    """Modelos de moto para calculo automatico de peso cubado"""
    __tablename__ = 'carvia_modelos_moto'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    regex_pattern = db.Column(db.String(200), nullable=True)
    comprimento = db.Column(db.Numeric(10, 4), nullable=False)
    largura = db.Column(db.Numeric(10, 4), nullable=False)
    altura = db.Column(db.Numeric(10, 4), nullable=False)
    peso_medio = db.Column(db.Numeric(10, 3), nullable=True)
    cubagem_minima = db.Column(db.Numeric(10, 2), nullable=False, default=300)
    categoria_moto_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_categorias_moto.id'),
        nullable=True,
        index=True,
    )
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<CarviaModeloMoto {self.nome} ({self.comprimento}x{self.largura}x{self.altura})>'


class CarviaEmpresaCubagem(db.Model):
    """Empresas que utilizam cubagem para calculo de peso"""
    __tablename__ = 'carvia_empresas_cubagem'

    id = db.Column(db.Integer, primary_key=True)
    cnpj_empresa = db.Column(db.String(20), nullable=False, unique=True)
    nome_empresa = db.Column(db.String(255), nullable=False)
    considerar_cubagem = db.Column(db.Boolean, nullable=False, default=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<CarviaEmpresaCubagem {self.cnpj_empresa} cubagem={self.considerar_cubagem}>'


class CarviaPrecoCategoriaMoto(db.Model):
    """Preco fixo por unidade para combinacao tabela_frete × categoria_moto"""
    __tablename__ = 'carvia_precos_categoria_moto'

    id = db.Column(db.Integer, primary_key=True)
    tabela_frete_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_tabelas_frete.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    categoria_moto_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_categorias_moto.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    valor_unitario = db.Column(db.Numeric(15, 2), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'tabela_frete_id', 'categoria_moto_id',
            name='uq_carvia_preco_cat_moto'
        ),
    )

    # Relationships
    tabela_frete = db.relationship('CarviaTabelaFrete', backref='precos_categoria_moto')

    def __repr__(self):
        return (
            f'<CarviaPrecoCategoriaMoto tabela={self.tabela_frete_id} '
            f'cat={self.categoria_moto_id} R${self.valor_unitario}>'
        )


# =====================================================================
# Config — Parametros globais do modulo CarVia (chave-valor)
# =====================================================================

class CarviaConfig(db.Model):
    """Parametros globais do modulo CarVia (chave-valor)"""
    __tablename__ = 'carvia_config'

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), nullable=False, unique=True)
    valor = db.Column(db.Text, nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive
    )
    atualizado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<CarviaConfig {self.chave}={self.valor}>'


# =====================================================================
# Clientes CarVia — Cadastro + Enderecos (Receita + Fisico)
# =====================================================================

class CarviaCliente(db.Model):
    """Cliente CarVia — pessoa juridica que contrata frete"""
    __tablename__ = 'carvia_clientes'

    id = db.Column(db.Integer, primary_key=True)
    nome_comercial = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive
    )

    # Relacionamentos
    enderecos = db.relationship(
        'CarviaClienteEndereco',
        backref='cliente',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='CarviaClienteEndereco.tipo, CarviaClienteEndereco.principal.desc()'
    )

    def __repr__(self):
        return f'<CarviaCliente {self.nome_comercial} ativo={self.ativo}>'


class CarviaClienteEndereco(db.Model):
    """Endereco de cliente CarVia — dados da Receita (readonly) + fisico (editavel)"""
    __tablename__ = 'carvia_cliente_enderecos'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_clientes.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    cnpj = db.Column(db.String(20), nullable=False, index=True)
    razao_social = db.Column(db.String(255), nullable=True)

    # Dados da Receita Federal (readonly — preenchidos via API)
    receita_uf = db.Column(db.String(2))
    receita_cidade = db.Column(db.String(100))
    receita_logradouro = db.Column(db.String(255))
    receita_numero = db.Column(db.String(20))
    receita_bairro = db.Column(db.String(100))
    receita_cep = db.Column(db.String(10))
    receita_complemento = db.Column(db.String(255))

    # Endereco fisico (editavel — pre-preenchido da Receita, persistido)
    fisico_uf = db.Column(db.String(2))
    fisico_cidade = db.Column(db.String(100))
    fisico_logradouro = db.Column(db.String(255))
    fisico_numero = db.Column(db.String(20))
    fisico_bairro = db.Column(db.String(100))
    fisico_cep = db.Column(db.String(10))
    fisico_complemento = db.Column(db.String(255))

    # Tipo: ORIGEM ou DESTINO
    tipo = db.Column(db.String(20), nullable=False)
    principal = db.Column(db.Boolean, nullable=False, default=False)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('cliente_id', 'cnpj', 'tipo', name='uq_carvia_cliente_endereco'),
        db.CheckConstraint("tipo IN ('ORIGEM', 'DESTINO')", name='ck_carvia_endereco_tipo'),
        db.Index('ix_carvia_endereco_tipo', 'tipo'),
    )

    def __repr__(self):
        return f'<CarviaClienteEndereco {self.cnpj} {self.tipo} cliente={self.cliente_id}>'


# =====================================================================
# Cotacao Comercial — Fluxo proativo de cotacao para clientes
# =====================================================================

class CarviaCotacao(db.Model):
    """Cotacao comercial CarVia — fluxo proativo de frete"""
    __tablename__ = 'carvia_cotacoes'

    STATUSES = [
        'RASCUNHO', 'PENDENTE_ADMIN', 'ENVIADO',
        'APROVADO', 'RECUSADO', 'CANCELADO'
    ]

    id = db.Column(db.Integer, primary_key=True)
    numero_cotacao = db.Column(db.String(20), nullable=False, index=True)

    # Cliente e enderecos
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_clientes.id'),
        nullable=False,
        index=True
    )
    endereco_origem_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_cliente_enderecos.id'),
        nullable=False
    )
    endereco_destino_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_cliente_enderecos.id'),
        nullable=False
    )

    # Tipo de material
    tipo_material = db.Column(db.String(20), nullable=False)  # CARGA_GERAL | MOTO

    # Dados carga geral
    peso = db.Column(db.Numeric(15, 3), nullable=True)
    valor_mercadoria = db.Column(db.Numeric(15, 2), nullable=True)
    dimensao_c = db.Column(db.Numeric(10, 4), nullable=True)  # comprimento
    dimensao_l = db.Column(db.Numeric(10, 4), nullable=True)  # largura
    dimensao_a = db.Column(db.Numeric(10, 4), nullable=True)  # altura
    peso_cubado = db.Column(db.Numeric(15, 3), nullable=True)
    volumes = db.Column(db.Integer, nullable=True)

    # Pricing
    valor_tabela = db.Column(db.Numeric(15, 2), nullable=True)
    percentual_desconto = db.Column(db.Numeric(5, 2), nullable=True, default=0)
    valor_descontado = db.Column(db.Numeric(15, 2), nullable=True)
    valor_final_aprovado = db.Column(db.Numeric(15, 2), nullable=True)

    # Tabela usada para calculo
    tabela_carvia_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_tabelas_frete.id'),
        nullable=True
    )
    dentro_tabela = db.Column(db.Boolean, nullable=True)
    detalhes_calculo = db.Column(db.JSON, nullable=True)

    # Datas
    data_cotacao = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    data_expedicao = db.Column(db.Date, nullable=True)
    data_agenda = db.Column(db.Date, nullable=True)

    # Status flow
    status = db.Column(db.String(20), nullable=False, default='RASCUNHO', index=True)
    aprovado_por = db.Column(db.String(100), nullable=True)
    aprovado_em = db.Column(db.DateTime, nullable=True)

    # Observacoes
    observacoes = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive
    )

    # Relacionamentos
    cliente = db.relationship('CarviaCliente', backref='cotacoes', lazy='joined')
    endereco_origem = db.relationship(
        'CarviaClienteEndereco',
        foreign_keys=[endereco_origem_id],
        lazy='joined'
    )
    endereco_destino = db.relationship(
        'CarviaClienteEndereco',
        foreign_keys=[endereco_destino_id],
        lazy='joined'
    )
    tabela_carvia = db.relationship('CarviaTabelaFrete', lazy='joined')
    motos = db.relationship(
        'CarviaCotacaoMoto',
        backref='cotacao',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    pedidos = db.relationship(
        'CarviaPedido',
        backref='cotacao',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('RASCUNHO','PENDENTE_ADMIN','ENVIADO','APROVADO','RECUSADO','CANCELADO')",
            name='ck_carvia_cotacao_status'
        ),
        db.CheckConstraint(
            "tipo_material IN ('CARGA_GERAL', 'MOTO')",
            name='ck_carvia_cotacao_tipo_material'
        ),
    )

    @staticmethod
    def gerar_numero_cotacao():
        """Gera proximo numero sequencial COT-###."""
        max_num = db.session.query(
            func.max(CarviaCotacao.numero_cotacao)
        ).filter(
            CarviaCotacao.numero_cotacao.ilike('COT-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('COT-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'COT-{next_num:03d}'

    @property
    def peso_total_motos(self):
        """Soma de peso cubado de todas as motos da cotacao."""
        total = db.session.query(
            func.coalesce(func.sum(CarviaCotacaoMoto.peso_cubado_total), 0)
        ).filter(
            CarviaCotacaoMoto.cotacao_id == self.id
        ).scalar()
        return float(total)

    @property
    def qtd_total_motos(self):
        """Soma de quantidade de todas as motos da cotacao."""
        total = db.session.query(
            func.coalesce(func.sum(CarviaCotacaoMoto.quantidade), 0)
        ).filter(
            CarviaCotacaoMoto.cotacao_id == self.id
        ).scalar()
        return int(total)

    def __repr__(self):
        return f'<CarviaCotacao {self.numero_cotacao} ({self.status}) cliente={self.cliente_id}>'


class CarviaCotacaoMoto(db.Model):
    """Itens de moto em uma cotacao — modelo + quantidade + peso cubado"""
    __tablename__ = 'carvia_cotacao_motos'

    id = db.Column(db.Integer, primary_key=True)
    cotacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_cotacoes.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    modelo_moto_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_modelos_moto.id'),
        nullable=False
    )
    categoria_moto_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_categorias_moto.id'),
        nullable=False
    )
    quantidade = db.Column(db.Integer, nullable=False)
    peso_cubado_unitario = db.Column(db.Numeric(10, 3), nullable=True)
    peso_cubado_total = db.Column(db.Numeric(15, 3), nullable=True)

    # Valor do produto (declaracao/seguro — NAO e o frete)
    valor_unitario = db.Column(db.Numeric(15, 2), nullable=True)
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)

    # Relacionamentos
    modelo_moto = db.relationship('CarviaModeloMoto', lazy='joined')
    categoria_moto = db.relationship('CarviaCategoriaMoto', lazy='joined')

    def __repr__(self):
        return f'<CarviaCotacaoMoto cotacao={self.cotacao_id} modelo={self.modelo_moto_id} qtd={self.quantidade}>'


# =====================================================================
# Pedidos CarVia — Pedidos de moto SP/RJ vinculados a cotacao
# =====================================================================

class CarviaPedido(db.Model):
    """Pedido CarVia — vinculado a cotacao, split por filial SP/RJ"""
    __tablename__ = 'carvia_pedidos'

    STATUSES = ['PENDENTE', 'FATURADO', 'EMBARCADO', 'CANCELADO']

    id = db.Column(db.Integer, primary_key=True)
    numero_pedido = db.Column(db.String(20), nullable=False, index=True)
    cotacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_cotacoes.id'),
        nullable=False,
        index=True
    )
    filial = db.Column(db.String(5), nullable=False)  # SP | RJ
    tipo_separacao = db.Column(db.String(20), nullable=False)  # ESTOQUE | CROSSDOCK
    status = db.Column(db.String(20), nullable=False, default='PENDENTE', index=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive
    )

    # Relacionamentos
    itens = db.relationship(
        'CarviaPedidoItem',
        backref='pedido',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('PENDENTE','FATURADO','EMBARCADO','CANCELADO')",
            name='ck_carvia_pedido_status'
        ),
        db.CheckConstraint("filial IN ('SP', 'RJ')", name='ck_carvia_pedido_filial'),
        db.CheckConstraint(
            "tipo_separacao IN ('ESTOQUE', 'CROSSDOCK')",
            name='ck_carvia_pedido_tipo_sep'
        ),
    )

    @staticmethod
    def gerar_numero_pedido():
        """Gera proximo numero sequencial PED-CV-###."""
        max_num = db.session.query(
            func.max(CarviaPedido.numero_pedido)
        ).filter(
            CarviaPedido.numero_pedido.ilike('PED-CV-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('PED-CV-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'PED-CV-{next_num:03d}'

    @property
    def status_calculado(self):
        """Status derivado do estado real, sem dependencia de atualizacao manual.

        PENDENTE: itens sem NF (ou sem itens)
        FATURADO: TODOS itens com NF preenchida
        EMBARCADO: FATURADO + portaria registrou saida (embarque.data_embarque)
        CANCELADO: cancelamento explicito (coluna status)
        """
        if self.status == 'CANCELADO':
            return 'CANCELADO'

        # Buscar itens (lazy='dynamic', precisa .all())
        itens_lista = self.itens.all()
        if not itens_lista:
            return 'PENDENTE'

        todos_com_nf = all(i.numero_nf for i in itens_lista)
        if not todos_com_nf:
            return 'PENDENTE'

        # Todos itens com NF — verificar se esta em embarque embarcado
        from app.embarques.models import EmbarqueItem, Embarque
        em_embarque = EmbarqueItem.query.filter(
            EmbarqueItem.separacao_lote_id == f'CARVIA-PED-{self.id}',
            EmbarqueItem.status == 'ativo',
        ).first()

        if em_embarque:
            embarque = db.session.get(Embarque, em_embarque.embarque_id)
            if embarque and embarque.data_embarque:
                return 'EMBARCADO'

        return 'FATURADO'

    def __repr__(self):
        return f'<CarviaPedido {self.numero_pedido} ({self.status}) filial={self.filial}>'


class CarviaPedidoItem(db.Model):
    """Item de pedido CarVia — modelo/descricao + cor + qtd + valor"""
    __tablename__ = 'carvia_pedido_itens'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_pedidos.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    modelo_moto_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_modelos_moto.id'),
        nullable=True
    )
    descricao = db.Column(db.String(255), nullable=True)
    cor = db.Column(db.String(50), nullable=True)
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Numeric(15, 2), nullable=True)
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)
    numero_nf = db.Column(db.String(20), nullable=True)  # Preenchido apos faturamento

    # Relacionamentos
    modelo_moto = db.relationship('CarviaModeloMoto', lazy='joined')

    def __repr__(self):
        return f'<CarviaPedidoItem pedido={self.pedido_id} qtd={self.quantidade}>'


# =====================================================================
# Cotacao v2 — Tabelas CarVia (preco de venda) + Grupos de Cliente
# =====================================================================

class CarviaGrupoCliente(db.Model):
    """Grupo de clientes para tabelas de preco diferenciadas"""
    __tablename__ = 'carvia_grupos_cliente'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False, unique=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relacionamentos
    membros = db.relationship(
        'CarviaGrupoClienteMembro',
        backref='grupo',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    tabelas = db.relationship(
        'CarviaTabelaFrete',
        backref='grupo_cliente',
        lazy='dynamic',
    )

    def __repr__(self):
        return f'<CarviaGrupoCliente {self.nome} ativo={self.ativo}>'


class CarviaGrupoClienteMembro(db.Model):
    """Membro (CNPJ) de um grupo de clientes"""
    __tablename__ = 'carvia_grupo_cliente_membros'

    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_grupos_cliente.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    cnpj = db.Column(db.String(20), nullable=False, index=True)
    nome_empresa = db.Column(db.String(255), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('grupo_id', 'cnpj', name='uq_carvia_grupo_membro'),
    )

    def __repr__(self):
        return f'<CarviaGrupoClienteMembro {self.cnpj} grupo={self.grupo_id}>'


class CarviaTabelaFrete(db.Model):
    """Tabela de frete CarVia (preco de VENDA) — sem transportadora"""
    __tablename__ = 'carvia_tabelas_frete'

    id = db.Column(db.Integer, primary_key=True)
    uf_origem = db.Column(db.String(2), nullable=False)
    uf_destino = db.Column(db.String(2), nullable=False)
    nome_tabela = db.Column(db.String(50), nullable=False)
    tipo_carga = db.Column(db.String(20), nullable=False)  # DIRETA / FRACIONADA
    modalidade = db.Column(db.String(50), nullable=False)

    # Grupo de cliente (NULL = standard)
    grupo_cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_grupos_cliente.id'),
        nullable=True,
        index=True
    )

    # Campos de preco — identicos a TabelaFrete para compatibilidade
    # com TabelaFreteManager.preparar_dados_tabela()
    valor_kg = db.Column(db.Float, nullable=True)
    frete_minimo_peso = db.Column(db.Float, nullable=True)
    percentual_valor = db.Column(db.Float, nullable=True)
    frete_minimo_valor = db.Column(db.Float, nullable=True)
    percentual_gris = db.Column(db.Float, nullable=True)
    percentual_adv = db.Column(db.Float, nullable=True)
    percentual_rca = db.Column(db.Float, nullable=True)
    pedagio_por_100kg = db.Column(db.Float, nullable=True)
    valor_despacho = db.Column(db.Float, nullable=True)
    valor_cte = db.Column(db.Float, nullable=True)
    valor_tas = db.Column(db.Float, nullable=True)
    icms_incluso = db.Column(db.Boolean, nullable=False, default=False)
    gris_minimo = db.Column(db.Float, nullable=True, default=0)
    adv_minimo = db.Column(db.Float, nullable=True, default=0)
    icms_proprio = db.Column(db.Float, nullable=True)

    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.Index('ix_carvia_tf_uf', 'uf_origem', 'uf_destino'),
        db.Index('ix_carvia_tf_tipo_carga', 'tipo_carga'),
        db.CheckConstraint(
            "tipo_carga IN ('DIRETA', 'FRACIONADA')",
            name='ck_carvia_tf_tipo_carga'
        ),
    )

    def __repr__(self):
        return (
            f'<CarviaTabelaFrete {self.nome_tabela} '
            f'{self.uf_origem}->{self.uf_destino} {self.tipo_carga}>'
        )


class CarviaCidadeAtendida(db.Model):
    """Cidades atendidas pelo frete CarVia — vincula a CarviaTabelaFrete via nome_tabela"""
    __tablename__ = 'carvia_cidades_atendidas'

    id = db.Column(db.Integer, primary_key=True)
    codigo_ibge = db.Column(db.String(10), nullable=False)
    nome_cidade = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    nome_tabela = db.Column(db.String(50), nullable=False)
    lead_time = db.Column(db.Integer, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('codigo_ibge', 'nome_tabela', name='uq_carvia_cidade_tabela'),
        db.Index('ix_carvia_cidade_ibge', 'codigo_ibge'),
        db.Index('ix_carvia_cidade_uf', 'uf'),
    )

    def __repr__(self):
        return f'<CarviaCidadeAtendida {self.nome_cidade}/{self.uf} tab={self.nome_tabela}>'


class CarviaAdminAudit(db.Model):
    """Auditoria de acoes administrativas (hard delete, type change, re-link, field edit)"""
    __tablename__ = 'carvia_admin_audit'

    id = db.Column(db.Integer, primary_key=True)
    acao = db.Column(db.String(30), nullable=False)
    # HARD_DELETE | TYPE_CHANGE | RELINK | FIELD_EDIT | IMPORT_EDIT
    entidade_tipo = db.Column(db.String(50), nullable=False)
    entidade_id = db.Column(db.Integer, nullable=False)
    dados_snapshot = db.Column(db.JSON, nullable=False)
    dados_relacionados = db.Column(db.JSON)
    motivo = db.Column(db.Text, nullable=False)
    executado_por = db.Column(db.String(100), nullable=False)
    executado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    detalhes = db.Column(db.JSON)

    __table_args__ = (
        db.CheckConstraint(
            "acao IN ('HARD_DELETE', 'TYPE_CHANGE', 'RELINK', 'FIELD_EDIT', 'IMPORT_EDIT')",
            name='ck_carvia_audit_acao',
        ),
        db.Index('ix_carvia_audit_acao', 'acao'),
        db.Index('ix_carvia_audit_entidade', 'entidade_tipo', 'entidade_id'),
        db.Index('ix_carvia_audit_executado_em', 'executado_em'),
        db.Index('ix_carvia_audit_executado_por', 'executado_por'),
    )

    def __repr__(self):
        return (
            f'<CarviaAdminAudit {self.acao} {self.entidade_tipo}:{self.entidade_id} '
            f'por {self.executado_por}>'
        )


# =====================================================================
# Frete CarVia — Registro de frete por grupo CNPJ (emitente+destino)
# =====================================================================

class CarviaFrete(db.Model):
    """Frete CarVia — 1 frete = 1 par (cnpj_emitente, cnpj_destino) + 1 Embarque.

    Equivalente ao Frete Nacom (app/fretes/models.py) mas:
    - Agregacao por CNPJ emitente + destino (nao so destino)
    - 2 lados: CUSTO (subcontrato) + VENDA (operacao CarVia)
    - Sem integracao Odoo
    - Sem aprovacao multi-nivel

    Ref: app/carvia/INTEGRACAO_EMBARQUE.md secao P2.4
    """
    __tablename__ = 'carvia_fretes'

    id = db.Column(db.Integer, primary_key=True)

    # --- Chaves ---
    embarque_id = db.Column(
        db.Integer, db.ForeignKey('embarques.id'),
        nullable=False, index=True
    )
    transportadora_id = db.Column(
        db.Integer, db.ForeignKey('transportadoras.id'),
        nullable=False
    )

    # --- Agregacao CNPJ emitente + destino ---
    cnpj_emitente = db.Column(db.String(20), nullable=False, index=True)
    nome_emitente = db.Column(db.String(255))
    cnpj_destino = db.Column(db.String(20), nullable=False, index=True)
    nome_destino = db.Column(db.String(255))

    # --- Rota ---
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)
    tipo_carga = db.Column(db.String(20), nullable=False)  # DIRETA | FRACIONADA

    # --- Totais NFs do grupo ---
    peso_total = db.Column(db.Float, nullable=False, default=0)
    valor_total_nfs = db.Column(db.Float, nullable=False, default=0)
    quantidade_nfs = db.Column(db.Integer, nullable=False, default=0)
    numeros_nfs = db.Column(db.Text)  # CSV

    # --- Snapshot tabela frete (custo — tabela Nacom) ---
    tabela_nome_tabela = db.Column(db.String(100))
    tabela_valor_kg = db.Column(db.Float)
    tabela_percentual_valor = db.Column(db.Float)
    tabela_frete_minimo_valor = db.Column(db.Float)
    tabela_frete_minimo_peso = db.Column(db.Float)
    tabela_icms = db.Column(db.Float)
    tabela_percentual_gris = db.Column(db.Float)
    tabela_pedagio_por_100kg = db.Column(db.Float)
    tabela_valor_tas = db.Column(db.Float)
    tabela_percentual_adv = db.Column(db.Float)
    tabela_percentual_rca = db.Column(db.Float)
    tabela_valor_despacho = db.Column(db.Float)
    tabela_valor_cte = db.Column(db.Float)
    tabela_icms_incluso = db.Column(db.Boolean, default=False)
    tabela_icms_destino = db.Column(db.Float)
    tabela_gris_minimo = db.Column(db.Float, default=0)
    tabela_adv_minimo = db.Column(db.Float, default=0)
    tabela_icms_proprio = db.Column(db.Float)

    # --- 4 valores CUSTO (subcontrato = tabela Nacom) ---
    valor_cotado = db.Column(db.Float, nullable=False, default=0)
    valor_cte = db.Column(db.Float)
    valor_considerado = db.Column(db.Float)
    valor_pago = db.Column(db.Float)

    # --- Valor VENDA (tabela CarVia) ---
    valor_venda = db.Column(db.Float)

    # --- Vinculacao CUSTO ---
    subcontrato_id = db.Column(
        db.Integer, db.ForeignKey('carvia_subcontratos.id'),
        nullable=True, index=True
    )
    fatura_transportadora_id = db.Column(
        db.Integer, db.ForeignKey('carvia_faturas_transportadora.id'),
        nullable=True
    )

    # --- Vinculacao VENDA ---
    operacao_id = db.Column(
        db.Integer, db.ForeignKey('carvia_operacoes.id'),
        nullable=True, index=True
    )
    fatura_cliente_id = db.Column(
        db.Integer, db.ForeignKey('carvia_faturas_cliente.id'),
        nullable=True
    )

    # --- Status: PENDENTE → CONFERIDO → FATURADO ---
    status = db.Column(db.String(20), default='PENDENTE', index=True)

    # --- Auditoria ---
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    observacoes = db.Column(db.Text)

    # --- Relationships ---
    embarque = db.relationship('Embarque')
    transportadora = db.relationship('Transportadora')
    subcontrato = db.relationship('CarviaSubcontrato', foreign_keys=[subcontrato_id])
    operacao = db.relationship('CarviaOperacao', foreign_keys=[operacao_id])
    fatura_transportadora_rel = db.relationship(
        'CarviaFaturaTransportadora', foreign_keys=[fatura_transportadora_id]
    )
    fatura_cliente_rel = db.relationship(
        'CarviaFaturaCliente', foreign_keys=[fatura_cliente_id]
    )
    custos_entrega = db.relationship(
        'CarviaCustoEntrega',
        backref='frete',
        foreign_keys='CarviaCustoEntrega.frete_id',
        lazy='dynamic',
    )
    ctes_complementares = db.relationship(
        'CarviaCteComplementar',
        backref='frete',
        foreign_keys='CarviaCteComplementar.frete_id',
        lazy='dynamic',
    )

    __table_args__ = (
        db.UniqueConstraint(
            'embarque_id', 'cnpj_emitente', 'cnpj_destino',
            name='uq_carvia_frete_embarque_cnpj'
        ),
    )

    @property
    def margem(self):
        """Margem = venda - custo (valor_cotado como referencia de custo)."""
        if self.valor_venda is not None and self.valor_cotado:
            return self.valor_venda - self.valor_cotado
        return None

    @property
    def margem_percentual(self):
        """Margem percentual = (margem / venda) * 100."""
        if self.valor_venda and self.valor_venda > 0 and self.margem is not None:
            return (self.margem / self.valor_venda) * 100
        return None

    def __repr__(self):
        return (
            f'<CarviaFrete {self.id} emb={self.embarque_id} '
            f'{self.cnpj_emitente}→{self.cnpj_destino} ({self.status})>'
        )

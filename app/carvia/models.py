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


class CarviaSessaoCotacao(db.Model):
    """Sessao de cotacao — agrupa N demandas de rota para cotar frete"""
    __tablename__ = 'carvia_sessoes_cotacao'

    id = db.Column(db.Integer, primary_key=True)
    numero_sessao = db.Column(db.String(20), nullable=False, index=True)
    nome_sessao = db.Column(db.String(255), nullable=False)

    # RASCUNHO, ENVIADO, APROVADO, CONTRA_PROPOSTA, CANCELADO
    status = db.Column(db.String(20), nullable=False, default='RASCUNHO')

    # Resposta do cliente
    valor_contra_proposta = db.Column(db.Numeric(15, 2), nullable=True)
    resposta_cliente_obs = db.Column(db.Text, nullable=True)
    respondido_em = db.Column(db.DateTime, nullable=True)
    respondido_por = db.Column(db.String(100), nullable=True)

    # Envio
    enviado_em = db.Column(db.DateTime, nullable=True)
    enviado_por = db.Column(db.String(100), nullable=True)

    # Dados do cliente (opcionais)
    cliente_nome = db.Column(db.String(255), nullable=True)
    cliente_email = db.Column(db.String(255), nullable=True)
    cliente_telefone = db.Column(db.String(50), nullable=True)
    cliente_responsavel = db.Column(db.String(255), nullable=True)

    # Geral
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive
    )

    # Relacionamentos
    demandas = db.relationship(
        'CarviaSessaoDemanda',
        backref='sessao',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='CarviaSessaoDemanda.ordem'
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('RASCUNHO','ENVIADO','APROVADO','CONTRA_PROPOSTA','CANCELADO')",
            name='ck_carvia_sessao_status'
        ),
    )

    @staticmethod
    def gerar_numero_sessao():
        """Gera proximo numero sequencial COTACAO-### para sessoes de cotacao.

        Busca max de AMBOS prefixos (SC-% e COTACAO-%) para garantir
        continuidade apos backfill do prefixo.
        """
        from sqlalchemy import cast, Integer

        # Extrair o numero de ambos prefixos e pegar o maior
        max_num_cotacao = db.session.query(
            db.func.max(
                cast(
                    db.func.replace(CarviaSessaoCotacao.numero_sessao, 'COTACAO-', ''),
                    Integer
                )
            )
        ).filter(
            CarviaSessaoCotacao.numero_sessao.ilike('COTACAO-%'),
        ).scalar() or 0

        max_num_sc = db.session.query(
            db.func.max(
                cast(
                    db.func.replace(CarviaSessaoCotacao.numero_sessao, 'SC-', ''),
                    Integer
                )
            )
        ).filter(
            CarviaSessaoCotacao.numero_sessao.ilike('SC-%'),
        ).scalar() or 0

        next_num = max(max_num_cotacao, max_num_sc) + 1
        return f'COTACAO-{next_num:03d}'

    @property
    def valor_total_frete(self):
        """Soma dos fretes selecionados nas demandas"""
        total = db.session.query(
            func.coalesce(func.sum(CarviaSessaoDemanda.valor_frete_calculado), 0)
        ).filter(
            CarviaSessaoDemanda.sessao_id == self.id,
            CarviaSessaoDemanda.valor_frete_calculado.isnot(None)
        ).scalar()
        return float(total)

    @property
    def qtd_demandas(self):
        """Quantidade de demandas na sessao"""
        return db.session.query(
            func.count(CarviaSessaoDemanda.id)
        ).filter(
            CarviaSessaoDemanda.sessao_id == self.id
        ).scalar()

    @property
    def todas_demandas_com_frete(self):
        """Verifica se TODAS as demandas tem frete selecionado"""
        sem_frete = db.session.query(
            func.count(CarviaSessaoDemanda.id)
        ).filter(
            CarviaSessaoDemanda.sessao_id == self.id,
            CarviaSessaoDemanda.valor_frete_calculado.is_(None)
        ).scalar()
        return sem_frete == 0

    def __repr__(self):
        return f'<CarviaSessaoCotacao {self.numero_sessao} ({self.status})>'


class CarviaSessaoDemanda(db.Model):
    """Demanda de rota dentro de uma sessao de cotacao"""
    __tablename__ = 'carvia_sessao_demandas'

    id = db.Column(db.Integer, primary_key=True)
    sessao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_sessoes_cotacao.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    ordem = db.Column(db.Integer, nullable=False, default=1)

    # Origem
    origem_empresa = db.Column(db.String(255), nullable=False)
    origem_uf = db.Column(db.String(2), nullable=False)
    origem_cidade = db.Column(db.String(100), nullable=False)

    # Destino
    destino_empresa = db.Column(db.String(255), nullable=False)
    destino_uf = db.Column(db.String(2), nullable=False)
    destino_cidade = db.Column(db.String(100), nullable=False)

    # Carga
    tipo_carga = db.Column(db.String(100), nullable=True)
    peso = db.Column(db.Numeric(15, 3), nullable=False)
    valor_mercadoria = db.Column(db.Numeric(15, 2), nullable=False)
    volume = db.Column(db.Integer, nullable=True)

    # Datas
    data_coleta = db.Column(db.Date, nullable=True)
    data_entrega_prevista = db.Column(db.Date, nullable=True)
    data_agendamento = db.Column(db.Date, nullable=True)

    # Frete selecionado
    transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('transportadoras.id'),
        nullable=True
    )
    tabela_frete_id = db.Column(
        db.Integer,
        db.ForeignKey('tabelas_frete.id'),
        nullable=True
    )
    valor_frete_calculado = db.Column(db.Numeric(15, 2), nullable=True)
    detalhes_calculo = db.Column(db.JSON, nullable=True)

    # Valores por demanda (proposta comercial)
    valor_proposto = db.Column(db.Numeric(15, 2), nullable=True)
    valor_contra_proposta = db.Column(db.Numeric(15, 2), nullable=True)

    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    # Relacionamentos
    transportadora = db.relationship('Transportadora', lazy='joined')

    __table_args__ = (
        db.UniqueConstraint('sessao_id', 'ordem', name='uq_carvia_sessao_demanda_ordem'),
        db.Index('ix_carvia_sessao_demanda_destino_uf', 'destino_uf'),
    )

    def limpar_frete_selecionado(self):
        """Limpa frete quando demanda e editada (valores stale)"""
        self.transportadora_id = None
        self.tabela_frete_id = None
        self.valor_frete_calculado = None
        self.detalhes_calculo = None

    def __repr__(self):
        return f'<CarviaSessaoDemanda {self.id} sessao={self.sessao_id} #{self.ordem}>'


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

    def __repr__(self):
        return (
            f'<CarviaConciliacao linha={self.extrato_linha_id} '
            f'{self.tipo_documento}:{self.documento_id} {self.valor_alocado}>'
        )


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

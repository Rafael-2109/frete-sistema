"""
Modelos de Documentos CarVia — NFs, Operacoes, Subcontratos
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
        from app.carvia.models.faturas import CarviaFaturaCliente, CarviaFaturaClienteItem
        return CarviaFaturaCliente.query.join(
            CarviaFaturaClienteItem,
            CarviaFaturaClienteItem.fatura_cliente_id == CarviaFaturaCliente.id
        ).filter(
            CarviaFaturaClienteItem.nf_id == self.id
        ).all()

    def get_faturas_transportadora(self):
        """Retorna faturas transportadora que referenciam esta NF via itens."""
        from app.carvia.models.faturas import (
            CarviaFaturaTransportadora, CarviaFaturaTransportadoraItem,
        )
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


class CarviaNfVeiculo(db.Model):
    """Veiculo extraido da NF — 1 chassi por linha (motos)"""
    __tablename__ = 'carvia_nf_veiculos'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_nfs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    chassi = db.Column(db.String(30), nullable=False)
    modelo = db.Column(db.String(100))
    cor = db.Column(db.String(50))
    valor = db.Column(db.Numeric(15, 2))
    ano = db.Column(db.String(20))
    numero_motor = db.Column(db.String(30))
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamento
    nf = db.relationship(
        'CarviaNf',
        backref=db.backref('veiculos', lazy='dynamic', cascade='all, delete-orphan'),
    )

    __table_args__ = (
        db.UniqueConstraint('chassi', name='uq_carvia_nf_veiculo_chassi'),
    )

    def __repr__(self):
        return f'<CarviaNfVeiculo {self.chassi} {self.cor}>'


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

    # Condicao de pagamento e responsavel do frete (propagado da cotacao)
    condicao_pagamento = db.Column(db.String(20), nullable=True)   # A_VISTA | PRAZO
    prazo_dias = db.Column(db.Integer, nullable=True)              # 1-30 se PRAZO
    responsavel_frete = db.Column(db.String(30), nullable=True)    # 100_REMETENTE | 100_DESTINATARIO | 50_50 | PERSONALIZADO
    percentual_remetente = db.Column(db.Numeric(5, 2), nullable=True)
    percentual_destinatario = db.Column(db.Numeric(5, 2), nullable=True)

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
    """Subcontratacao — 1 por transportadora por CarviaFrete.

    operacao_id e nullable: CarviaSubcontrato pode ser criado independente
    de CarviaOperacao. CarviaFrete e o eixo central.
    """
    __tablename__ = 'carvia_subcontratos'

    id = db.Column(db.Integer, primary_key=True)
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=True,
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

    # FK para CarviaFrete (N:1 — um frete pode ter N subcontratos multi-leg)
    frete_id = db.Column(
        db.Integer, db.ForeignKey('carvia_fretes.id'),
        nullable=True, index=True
    )

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
    # N:1 com CarviaFrete via frete_id (back_populates com CarviaFrete.subcontratos)
    frete = db.relationship(
        'CarviaFrete',
        foreign_keys=[frete_id],
        back_populates='subcontratos',
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

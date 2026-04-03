"""
Modelos de Frete CarVia — Registro de frete + Emissao CTe
"""

from app import db
from app.utils.timezone import agora_utc_naive


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
        nullable=True, index=True  # nullable para backfill (sem embarque)
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
    # DEPRECATED: usar relationship subcontratos (1:N via CarviaSubcontrato.frete_id)
    # Mantido temporariamente para backward compat durante transicao.
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

    # --- Status: PENDENTE -> CONFERIDO -> FATURADO ---
    status = db.Column(db.String(20), default='PENDENTE', index=True)

    # --- Auditoria ---
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    observacoes = db.Column(db.Text)

    # --- Condicao de pagamento e responsavel do frete (propagado da cotacao) ---
    condicao_pagamento = db.Column(db.String(20), nullable=True)   # A_VISTA | PRAZO
    prazo_dias = db.Column(db.Integer, nullable=True)              # 1-30 se PRAZO
    responsavel_frete = db.Column(db.String(30), nullable=True)    # 100_REMETENTE | 100_DESTINATARIO | 50_50 | PERSONALIZADO
    percentual_remetente = db.Column(db.Numeric(5, 2), nullable=True)
    percentual_destinatario = db.Column(db.Numeric(5, 2), nullable=True)

    # --- Relationships ---
    embarque = db.relationship('Embarque')
    transportadora = db.relationship('Transportadora')
    # DEPRECATED: 1:1 via subcontrato_id — usar subcontratos (1:N) para multi-leg
    subcontrato = db.relationship('CarviaSubcontrato', foreign_keys=[subcontrato_id])
    # 1:N via CarviaSubcontrato.frete_id — suporta multi-leg transport
    subcontratos = db.relationship(
        'CarviaSubcontrato',
        foreign_keys='CarviaSubcontrato.frete_id',
        back_populates='frete',
        lazy='dynamic',
    )
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
        # Partial unique index: dedup apenas para fretes COM embarque.
        # Fretes backfill (embarque_id=NULL) nao tem essa restricao.
        # Gerenciado pela migration tornar_embarque_id_nullable_carvia_fretes.
        db.Index(
            'uq_carvia_frete_embarque_cnpj_notnull',
            'embarque_id', 'cnpj_emitente', 'cnpj_destino',
            unique=True,
            postgresql_where=db.text('embarque_id IS NOT NULL'),
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
            f'{self.cnpj_emitente}->{self.cnpj_destino} ({self.status})>'
        )


class CarviaEmissaoCte(db.Model):
    """Controle de emissoes automaticas de CTe no SSW via Playwright.

    Funcoes:
    - Mutex: evita dupla emissao (verificar status PENDENTE/EM_PROCESSAMENTO)
    - Progresso: campo 'etapa' atualizado pelo job RQ para polling
    - Auditoria: historico completo de tentativas por NF
    """
    __tablename__ = 'carvia_emissao_cte'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(db.Integer, db.ForeignKey('carvia_nfs.id'), nullable=False)
    operacao_id = db.Column(db.Integer, db.ForeignKey('carvia_operacoes.id'))
    status = db.Column(db.String(20), nullable=False, default='PENDENTE')
    etapa = db.Column(db.String(30))
    job_id = db.Column(db.String(100))
    ctrc_numero = db.Column(db.String(20))
    placa = db.Column(db.String(20), nullable=False, default='ARMAZEM')
    uf_origem = db.Column(db.String(2))
    filial_ssw = db.Column(db.String(10))
    cnpj_tomador = db.Column(db.String(20))
    frete_valor = db.Column(db.Numeric(15, 2))
    data_vencimento = db.Column(db.Date)
    medidas_json = db.Column(db.JSON)
    erro_ssw = db.Column(db.Text)
    resultado_json = db.Column(db.JSON)
    fatura_numero = db.Column(db.String(20))
    fatura_pdf_path = db.Column(db.String(500))
    xml_path = db.Column(db.String(500))
    dacte_path = db.Column(db.String(500))
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive,
                              onupdate=agora_utc_naive)

    # Relationships
    nf = db.relationship('CarviaNf', foreign_keys=[nf_id])
    operacao = db.relationship('CarviaOperacao', foreign_keys=[operacao_id])

    STATUSES = ('PENDENTE', 'EM_PROCESSAMENTO', 'SUCESSO', 'ERRO', 'CANCELADO')
    ETAPAS = ('LOGIN', 'PREENCHIMENTO', 'SEFAZ', 'CONSULTA_101',
              'IMPORTACAO_CTE', 'FATURA_437', 'IMPORTACAO_FAT')

    @property
    def em_andamento(self):
        """True se emissao esta pendente ou em processamento."""
        return self.status in ('PENDENTE', 'EM_PROCESSAMENTO')

    @property
    def finalizado(self):
        """True se emissao terminou (sucesso ou erro)."""
        return self.status in ('SUCESSO', 'ERRO', 'CANCELADO')

    def __repr__(self):
        return (
            f'<CarviaEmissaoCte {self.id} nf={self.nf_id} '
            f'status={self.status} ctrc={self.ctrc_numero}>'
        )

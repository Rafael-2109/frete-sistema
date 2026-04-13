"""
Modelos de Faturas CarVia — Faturas Cliente e Transportadora
"""

from sqlalchemy import func

from app import db
from app.utils.timezone import agora_utc_naive


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

    # Conferencia gerencial (Refator 2.1 — manual puro, independente de pagamento)
    # PENDENTE → CONFERIDO (binario, gate manual sem validacao automatica)
    # Ref: scripts/migrations/carvia_fatura_cliente_auditoria.py
    status_conferencia = db.Column(
        db.String(20), nullable=False, default='PENDENTE', index=True
    )
    conferido_por = db.Column(db.String(100))
    conferido_em = db.Column(db.DateTime)
    observacoes_conferencia = db.Column(db.Text)

    # Conciliacao bancaria
    total_conciliado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    conciliado = db.Column(db.Boolean, nullable=False, default=False)

    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Valores validos de status_conferencia (manual binario)
    STATUSES_CONFERENCIA = ('PENDENTE', 'CONFERIDO')

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

    # ------------------------------------------------------------------ #
    #  Validacoes de Bloqueio (Sprint 0 — Fundacao + Refator 2.1)
    #
    #  Fatura e entidade independente — valor_total NAO recalcula
    #  automaticamente. CTes podem ser desanexados antes de PAGA.
    #
    #  Refator 2.1: status_conferencia=CONFERIDO tambem bloqueia edicao,
    #  espelhando CarviaFaturaTransportadora.pode_editar().
    #  Conferencia e gerencial e precede pagamento — uma vez aprovada,
    #  a fatura fica travada ate ser reaberta explicitamente.
    # ------------------------------------------------------------------ #

    def pode_editar(self):
        """Verifica se a fatura pode ser editada.

        Bloqueios (ordem de verificacao):
        - status_conferencia == CONFERIDO (Refator 2.1)
        - Status PAGA ou CANCELADA
        - Conciliacao ativa (total_conciliado > 0)

        Returns:
            tuple[bool, str]: (pode_editar, razao_se_nao)
        """
        if self.status_conferencia == 'CONFERIDO':
            return (
                False,
                "Fatura ja conferida. Reabra a conferencia antes de editar."
            )
        if self.status == 'PAGA':
            return (
                False,
                "Fatura PAGA. Desconcilie via Extrato Bancario antes de editar."
            )
        if self.status == 'CANCELADA':
            return False, "Fatura cancelada nao pode ser editada."
        if self.total_conciliado and float(self.total_conciliado) > 0:
            return (
                False,
                "Fatura tem conciliacao ativa. Desconcilie antes de editar."
            )
        return True, ""

    def pode_desanexar_operacao(self):
        """Verifica se operacoes podem ser desanexadas da fatura.

        Mesma regra de pode_editar() — bloquear se conferida/paga/conciliada.

        Returns:
            tuple[bool, str]: (pode_desanexar, razao_se_nao)
        """
        return self.pode_editar()

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

    # ------------------------------------------------------------------ #
    #  Validacoes de Bloqueio (Sprint 0 — Fundacao)
    #
    #  Fatura Transportadora tem dois status independentes:
    #  - status_conferencia: PENDENTE → EM_CONFERENCIA → CONFERIDO | DIVERGENTE
    #  - status_pagamento:   PENDENTE → PAGO
    #
    #  CONFERIDO = trava para edicao/desanexar (espelhando FaturaFrete)
    #  PAGO = trava financeira
    # ------------------------------------------------------------------ #

    def pode_editar(self):
        """Verifica se a fatura pode ser editada.

        Bloqueios:
        - status_conferencia == CONFERIDO
        - status_pagamento == PAGO
        - Conciliacao ativa

        Returns:
            tuple[bool, str]: (pode_editar, razao_se_nao)
        """
        if self.status_conferencia == 'CONFERIDO':
            return (
                False,
                "Fatura ja conferida. Reabra a conferencia antes de editar."
            )
        if self.status_pagamento == 'PAGO':
            return (
                False,
                "Fatura ja paga. Desconcilie via Extrato Bancario antes de editar."
            )
        if self.total_conciliado and float(self.total_conciliado) > 0:
            return (
                False,
                "Fatura tem conciliacao ativa. Desconcilie antes de editar."
            )
        return True, ""

    def pode_desanexar_subcontrato(self):
        """Verifica se subcontratos podem ser desanexados da fatura.

        Mesma regra de pode_editar() — CONFERIDO ou PAGO bloqueia.

        Returns:
            tuple[bool, str]: (pode_desanexar, razao_se_nao)
        """
        return self.pode_editar()

    def pode_editar_sub_valor(self):
        """Verifica se valor_acertado de subcontratos vinculados pode ser editado.

        Bloqueios:
        - status_conferencia == CONFERIDO
        - status_pagamento == PAGO

        Nota: nao bloqueia por conciliacao parcial — valor pode ser ajustado
        ate a conferencia final. Apenas CONFERIDO trava definitivamente.

        Returns:
            tuple[bool, str]: (pode_editar, razao_se_nao)
        """
        if self.status_conferencia == 'CONFERIDO':
            return (
                False,
                "Fatura conferida. Reabra a conferencia para editar valores de subcontratos."
            )
        if self.status_pagamento == 'PAGO':
            return (
                False,
                "Fatura paga. Desconcilie antes de editar valores."
            )
        return True, ""

    def __repr__(self):
        return f'<CarviaFaturaTransportadora {self.numero_fatura} ({self.status_conferencia})>'

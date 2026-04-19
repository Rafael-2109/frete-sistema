"""
Modelos Financeiros CarVia — Despesas, Receitas, Movimentacoes, Extrato, Conciliacao
"""

from app import db
from app.utils.timezone import agora_utc_naive


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

    # D2 (2026-04-19): FKs opcionais para CTe / CarviaFrete — permite
    # vincular despesa (ex: seguro) a operacao especifica, habilita
    # calculo de margem real por frete. Ambas nullable (CarviaDespesa
    # generica continua funcionando sem vinculo).
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=True,
        index=True,
    )
    frete_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_fretes.id'),
        nullable=True,
        index=True,
    )

    @property
    def numero_despesa(self):
        """Codigo exibivel no formato DESP-### (mesmo usado no extrato/conciliacao)"""
        return f'DESP-{self.id:03d}'

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


class CarviaContaMovimentacao(db.Model):
    """Movimentacoes financeiras da conta CarVia — saldo calculado por SUM"""
    __tablename__ = 'carvia_conta_movimentacoes'

    id = db.Column(db.Integer, primary_key=True)
    tipo_doc = db.Column(db.String(30), nullable=False)
    # 'fatura_cliente' | 'fatura_transportadora' | 'despesa' | 'custo_entrega' | 'receita' | 'saldo_inicial' | 'ajuste'
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
    """Linhas do extrato bancario CarVia — base para conciliacao.

    W10 Nivel 2 (Sprint 4): campo `origem` distingue a fonte da linha:
      - OFX    -> importada de arquivo OFX (imutavel)
      - CSV    -> importada de CSV bancario (imutavel)
      - MANUAL -> lancamento manual fora do extrato bancario CarVia.
                  Exige `conta_origem` preenchido. Permite edicao/delecao
                  enquanto nao conciliada. Usada quando o pagamento e feito
                  por outra conta (pessoal, empresa parceira, dinheiro, etc.)

    Linhas MANUAL permitem que TODOS os pagamentos passem pelo Conciliacao
    como SOT — elimina dual-path com CarviaContaMovimentacao (que permanece
    apenas para saldo_inicial).

    Imutabilidade:
      - OFX/CSV: nunca editaveis/deletaveis (sao import bancario)
      - MANUAL: editaveis e deletaveis enquanto nao conciliadas
    """
    __tablename__ = 'carvia_extrato_linhas'

    # Enforcement DB: toda linha MANUAL exige conta_origem preenchido.
    # A constraint e criada pela migration `renomear_fc_virtual_para_manual`
    # (step 7, `ck_carvia_extrato_manual_conta`). Declaracao aqui e
    # documental — garante que novas criacoes de schema via create_all
    # refletem a regra.
    __table_args__ = (
        db.CheckConstraint(
            "origem != 'MANUAL' OR conta_origem IS NOT NULL",
            name='ck_carvia_extrato_manual_conta',
        ),
    )

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

    # W10 Nivel 2: origem da linha (OFX | CSV | MANUAL)
    origem = db.Column(
        db.String(20), nullable=False, default='OFX', index=True
    )
    # W10 Nivel 2 refactor: conta de origem para linhas MANUAL
    # (texto livre — ex: "Conta Pessoal Rafael", "Empresa Nacom Goya",
    #  "Dinheiro/Caixa"). Obrigatorio para origem='MANUAL', NULL para OFX/CSV.
    conta_origem = db.Column(db.String(100), nullable=True)

    # E2 (2026-04-19): par de estorno — quando OFX contem um ESTORNO
    # (reversal) de uma linha anterior, `linha_original_id` aponta para a
    # linha revertida. Detectado via refnum/checknum no import OFX OU
    # marcado manualmente pelo operador.
    linha_original_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_extrato_linhas.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )

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

    def pode_editar(self):
        """Valida se a linha pode ser editada.

        OFX/CSV: imutaveis (sao import bancario).
        MANUAL: editavel apenas se nao conciliada (editar valor
                alteraria o ja conciliado).

        Returns:
            (bool, str): (permitido, razao_caso_nao)
        """
        if self.origem in ('OFX', 'CSV'):
            return False, (
                f"Linha de origem '{self.origem}' e imutavel "
                f"(importada do extrato bancario)."
            )
        if self.status_conciliacao != 'PENDENTE':
            return False, (
                "Linha ja esta conciliada — desconcilie antes de editar."
            )
        return True, None

    def pode_deletar(self):
        """Valida se a linha pode ser deletada.

        OFX/CSV: imutaveis.
        MANUAL: deletavel apenas se nao conciliada.

        Returns:
            (bool, str): (permitido, razao_caso_nao)
        """
        if self.origem in ('OFX', 'CSV'):
            return False, (
                f"Linha de origem '{self.origem}' e imutavel "
                f"(importada do extrato bancario)."
            )
        if self.status_conciliacao != 'PENDENTE':
            return False, (
                "Linha ja esta conciliada — desconcilie antes de deletar."
            )
        return True, None

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
    # fatura_cliente | fatura_transportadora | despesa | custo_entrega | receita
    documento_id = db.Column(db.Integer, nullable=False)
    valor_alocado = db.Column(db.Numeric(15, 2), nullable=False)
    # E3 (2026-04-19): juros/multa (acrescimo) e desconto em conciliacao.
    # Quando pagamento chega com valor != fatura, nao precisa criar
    # Receita/Despesa avulsa — basta indicar no vinculo. Status 100%
    # considera: valor_alocado + valor_acrescimo - valor_desconto.
    valor_acrescimo = db.Column(db.Numeric(15, 2), nullable=True)
    valor_desconto = db.Column(db.Numeric(15, 2), nullable=True)
    # F1 (2026-04-19): marca conciliacao como compensacao cross-tipo
    # (linha DEBITO conciliada contra fatura_cliente CREDITO, ou vice-versa).
    # Usado apenas em encontro de contas / chargeback. NULL = conciliacao
    # normal da mesma direcao.
    eh_compensacao = db.Column(db.Boolean, nullable=False, default=False)
    compensacao_motivo = db.Column(db.String(255), nullable=True)
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
            'receita': 'REC',
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
        elif self.tipo_documento == 'receita':
            return f'REC-{self.documento_id:03d}'
        return fallback

    @property
    def url_documento(self):
        """URL da pagina de detalhe do documento."""
        _URLS = {
            'fatura_cliente': '/carvia/faturas-cliente/{}',
            'fatura_transportadora': '/carvia/faturas-transportadora/{}',
            'despesa': '/carvia/despesas/{}',
            'custo_entrega': '/carvia/custos-entrega/{}',
            'receita': '/carvia/receitas/{}',
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


class CarviaPreVinculoExtratoCotacao(db.Model):
    """Pre-vinculo soft entre linha de extrato e cotacao aprovada.

    Usado para frete pre-pago: cliente paga antes da fatura ser emitida.
    A linha do extrato entra no banco como 'orfa' (PENDENTE sem documento
    para conciliar contra). O usuario abre a cotacao APROVADA e cria um
    pre-vinculo com uma linha candidata — a linha permanece PENDENTE.

    Quando a CarviaFaturaCliente e criada cobrindo operacoes cuja cadeia
    FaturaItem.nf_id -> NF.numero_nf -> PedidoItem.numero_nf ->
    Pedido.cotacao_id aponta para a cotacao vinculada, o trigger automatico
    em fatura_routes.py cria CarviaConciliacao real (tipo_documento=
    'fatura_cliente') e marca este pre-vinculo como RESOLVIDO.

    Diferenca crucial vs CarviaConciliacao: pre-vinculo e INTENCAO, nao
    concilicao financeira final. Linha continua PENDENTE ate a fatura
    existir. Ponteiro `conciliacao_id` preserva audit trail apos resolver.

    Fluxo:
      ATIVO -> RESOLVIDO (quando fatura chega)
      ATIVO -> CANCELADO (usuario desfaz manualmente)
    """
    __tablename__ = 'carvia_previnculos_extrato_cotacao'

    id = db.Column(db.Integer, primary_key=True)

    extrato_linha_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_extrato_linhas.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    cotacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_cotacoes.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    valor_alocado = db.Column(db.Numeric(15, 2), nullable=False)

    # Estado do pre-vinculo
    status = db.Column(
        db.String(20), nullable=False, default='ATIVO', index=True,
    )  # ATIVO | RESOLVIDO | CANCELADO

    # Resolucao automatica — preenchidos quando fatura chega
    conciliacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_conciliacoes.id', ondelete='SET NULL'),
        nullable=True,
    )
    fatura_cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_cliente.id', ondelete='SET NULL'),
        nullable=True,
    )
    resolvido_em = db.Column(db.DateTime, nullable=True)
    resolvido_automatico = db.Column(db.Boolean, nullable=False, default=False)

    # Cancelamento
    cancelado_em = db.Column(db.DateTime, nullable=True)
    cancelado_por = db.Column(db.String(100), nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)

    # Auditoria
    observacao = db.Column(db.Text, nullable=True)
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    # Relacionamentos
    extrato_linha = db.relationship(
        'CarviaExtratoLinha',
        backref=db.backref('previnculos_cotacao', lazy='dynamic'),
    )
    cotacao = db.relationship(
        'CarviaCotacao',
        backref=db.backref('previnculos_extrato', lazy='dynamic'),
    )
    conciliacao = db.relationship(
        'CarviaConciliacao', foreign_keys=[conciliacao_id]
    )
    fatura_cliente = db.relationship(
        'CarviaFaturaCliente', foreign_keys=[fatura_cliente_id]
    )

    __table_args__ = (
        # UNIQUE PARCIAL: apenas 1 pre-vinculo ATIVO por (linha, cotacao).
        # Permite recriar apos CANCELADO, e coexistir com RESOLVIDO historico.
        db.Index(
            'uq_previnculo_linha_cotacao_ativo',
            'extrato_linha_id', 'cotacao_id',
            unique=True,
            postgresql_where=db.text("status = 'ATIVO'"),
        ),
        db.CheckConstraint(
            'valor_alocado > 0', name='ck_previnculo_valor_positivo'
        ),
        db.CheckConstraint(
            "status IN ('ATIVO', 'RESOLVIDO', 'CANCELADO')",
            name='ck_previnculo_status',
        ),
        db.Index('ix_previnculo_ativo', 'cotacao_id', 'status'),
        db.Index('ix_previnculo_resolvido', 'status', 'resolvido_em'),
    )

    def __repr__(self):
        return (
            f'<CarviaPreVinculoExtratoCotacao linha={self.extrato_linha_id} '
            f'cotacao={self.cotacao_id} {self.status} R${self.valor_alocado}>'
        )


class CarviaHistoricoMatchExtrato(db.Model):
    """Log append-only de eventos de match aprendidos (descricao+CNPJ pagador).

    R17: A cada CarviaConciliacao criada para fatura_cliente, o hook em
    CarviaConciliacaoService.conciliar() grava UMA linha com os tokens
    normalizados da descricao da linha de cima do extrato + CNPJ do pagador
    da fatura. Sem UPSERT — cada conciliacao vira um evento novo.

    1 descricao pode fazer match com N CNPJs legitimamente (ex: "PIX RECEBIDO"
    pode vir de varios pagadores). Nao ha UNIQUE constraint. Contagem de
    ocorrencias via COUNT(*) GROUP BY cnpj_pagador na consulta.

    Usada por pontuar_documentos() em carvia_sugestao_service.py para aplicar
    boost multiplicativo 1.4x no score quando o doc sugerido tem o mesmo
    cnpj_cliente de um padrao aprendido.

    Escopo atual: fatura_cliente apenas (CREDITO/recebimento). Campo
    `tipo_documento` preparado para extensao futura (fatura_transportadora,
    despesa, custo_entrega, receita).
    """
    __tablename__ = 'carvia_historico_match_extrato'

    id = db.Column(db.Integer, primary_key=True)

    # Snapshot raw da descricao da linha de cima (auditoria)
    descricao_linha_raw = db.Column(db.String(500), nullable=False)

    # Tokens normalizados ordenados — chave de match exato
    descricao_tokens = db.Column(db.String(500), nullable=False, index=True)

    # CNPJ do pagador (CarviaFaturaCliente.cnpj_cliente no escopo atual)
    cnpj_pagador = db.Column(db.String(20), nullable=False, index=True)

    # Preparado para extensao futura (transportadora, despesa, etc.)
    tipo_documento = db.Column(
        db.String(30), nullable=False, default='fatura_cliente',
    )

    # Ponteiro solto para auditoria (nao e FK formal — padrao de CarviaConciliacao)
    conciliacao_id = db.Column(db.Integer, nullable=True)

    registrado_em = db.Column(
        db.DateTime, nullable=False, default=agora_utc_naive,
    )

    __table_args__ = (
        # SEM UniqueConstraint: append-only, 1 descricao pode ter N CNPJs
        # Indice composto para consulta principal (WHERE tokens=X AND tipo=Y
        # GROUP BY cnpj_pagador). Cobre tambem queries so por tokens via
        # prefix rule do PostgreSQL (FIX M4: standalone removido).
        db.Index(
            'ix_carvia_histmatch_tokens_tipo',
            'descricao_tokens', 'tipo_documento',
        ),
        # FIX m5: sync com o DDL da migration — mantem db.create_all()
        # funcional em ambientes novos (ex: testes, dev setup sem migration).
        db.Index(
            'ix_carvia_histmatch_cnpj',
            'cnpj_pagador',
        ),
        db.Index(
            'ix_carvia_histmatch_conciliacao_id',
            'conciliacao_id',
            postgresql_where=db.text('conciliacao_id IS NOT NULL'),
        ),
    )

    def __repr__(self):
        return (
            f'<CarviaHistoricoMatchExtrato tokens={self.descricao_tokens[:30]!r} '
            f'cnpj={self.cnpj_pagador} tipo={self.tipo_documento}>'
        )

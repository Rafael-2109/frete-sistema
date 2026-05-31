"""
Modelos de Cotacao Comercial CarVia — Cotacao, Motos, Pedidos
"""

from sqlalchemy import func

from app import db
from app.utils.timezone import agora_utc_naive


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

    # Endereco de entrega (override por cotacao — independente do destino cadastrado)
    entrega_uf = db.Column(db.String(2), nullable=True)
    entrega_cidade = db.Column(db.String(100), nullable=True)
    entrega_logradouro = db.Column(db.String(255), nullable=True)
    entrega_numero = db.Column(db.String(20), nullable=True)
    entrega_bairro = db.Column(db.String(100), nullable=True)
    entrega_cep = db.Column(db.String(10), nullable=True)
    entrega_complemento = db.Column(db.String(255), nullable=True)

    # Tipo de material e carga
    tipo_material = db.Column(db.String(20), nullable=False)  # CARGA_GERAL | MOTO
    tipo_carga = db.Column(db.String(20), nullable=True)  # DIRETA | FRACIONADA

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

    # Cotacao manual (sem lookup de tabela — requer aprovacao admin)
    cotacao_manual = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    valor_manual = db.Column(db.Numeric(15, 2), nullable=True)

    # Veiculo selecionado (DIRETA only — FK veiculos.id)
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculos.id'), nullable=True, index=True)

    # Datas
    data_cotacao = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    data_expedicao = db.Column(db.Date, nullable=True)
    data_agenda = db.Column(db.Date, nullable=True)
    horario_agenda = db.Column(db.Time, nullable=True)  # Horario do agendamento (HH:MM) — exclusivo CarVia (Nacom nao usa)

    # Status flow
    status = db.Column(db.String(20), nullable=False, default='RASCUNHO', index=True)
    aprovado_por = db.Column(db.String(100), nullable=True)
    aprovado_em = db.Column(db.DateTime, nullable=True)

    # Agendamento
    agendamento_confirmado = db.Column(db.Boolean, nullable=False, default=False, server_default='false')

    # Observacoes
    observacoes = db.Column(db.Text, nullable=True)

    # Condicao de pagamento e responsavel do frete (controle financeiro)
    condicao_pagamento = db.Column(db.String(20), nullable=True)   # A_VISTA | PRAZO
    prazo_dias = db.Column(db.Integer, nullable=True)              # 1-30 se PRAZO
    responsavel_frete = db.Column(db.String(30), nullable=True)    # 100_REMETENTE | 100_DESTINATARIO | 50_50 | PERSONALIZADO
    percentual_remetente = db.Column(db.Numeric(5, 2), nullable=True)
    percentual_destinatario = db.Column(db.Numeric(5, 2), nullable=True)

    # Criacao tardia: cotacao criada a partir de NF que ja possui CTe CarVia
    criacao_tardia = db.Column(db.Boolean, nullable=False, default=False, server_default='false')

    # Alerta: saida portaria sem NF
    alerta_saida_sem_nf = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    alerta_saida_sem_nf_em = db.Column(db.DateTime, nullable=True)
    alerta_saida_embarque_id = db.Column(db.Integer, nullable=True)

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
    veiculo = db.relationship('Veiculo', lazy='joined')
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
    def gerar_numero_cotacao(cotacao_id=None):
        """Gera numero da cotacao no formato COT-{id}.

        Se cotacao_id fornecido (apos flush): COT-{id}.
        Se nao: fallback COT-{max+1} (pre-flush).
        """
        if cotacao_id:
            return f'COT-{cotacao_id}'

        max_num = db.session.query(
            func.max(CarviaCotacao.numero_cotacao)
        ).filter(
            CarviaCotacao.numero_cotacao.ilike('COT-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                num_str = max_num.replace('COT-', '')
                next_num = int(num_str) + 1
            except (ValueError, TypeError):
                pass
        return f'COT-{next_num}'

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

    @property
    def peso_para_cotacao(self):
        """Peso usado na precificacao do frete — acessor canonico.

        Convencao do sistema: para MOTO a fonte de verdade e a property
        `peso_total_motos` (SUM de CarviaCotacaoMoto.peso_cubado_total); o campo
        `peso_cubado` fica NULL por design em MOTO e NAO deve ser lido. Para
        CARGA_GERAL usa o peso cubado declarado, com fallback no peso bruto.

        Consolida a regra que estava duplicada em CotacaoV2Service.calcular_preco
        e MargemService._melhor_custo_subcontrato.
        """
        if self.tipo_material == 'MOTO':
            return float(self.peso_total_motos)
        return float(self.peso_cubado or self.peso or 0)

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
    # FIX PYTHON-FLASK-AY: nullable=True — modelos podem nao ter categoria vinculada ainda.
    # Precificacao por categoria so funciona quando categoria esta definida.
    categoria_moto_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_categorias_moto.id'),
        nullable=True
    )
    quantidade = db.Column(db.Integer, nullable=False)
    peso_cubado_unitario = db.Column(db.Numeric(10, 3), nullable=True)
    peso_cubado_total = db.Column(db.Numeric(15, 3), nullable=True)

    # Valor do produto (declaracao/seguro — NAO e o frete)
    valor_unitario = db.Column(db.Numeric(15, 2), nullable=True)
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)

    # Placeholder: registro criado via backfill de NF com modelo desconhecido na cotacao.
    # Quando TRUE, o peso/dimensoes ainda precisam ser completados pelo usuario.
    # A UI mostra badge amarelo "peso pendente" e o frete usa peso=0 ate ser corrigido.
    placeholder = db.Column(db.Boolean, nullable=False, default=False, server_default='false')

    # Relacionamentos
    modelo_moto = db.relationship('CarviaModeloMoto', lazy='joined')
    categoria_moto = db.relationship('CarviaCategoriaMoto', lazy='joined')

    def __repr__(self):
        return f'<CarviaCotacaoMoto cotacao={self.cotacao_id} modelo={self.modelo_moto_id} qtd={self.quantidade}>'


class CarviaPedido(db.Model):
    """Pedido CarVia — vinculado a cotacao, split por filial SP/RJ"""
    __tablename__ = 'carvia_pedidos'

    STATUSES = ['ABERTO', 'COTADO', 'FATURADO', 'CANCELADO']
    # EMBARCADO deixou de ser status (P12, 2026-04-24). O fato fisico do
    # embarque e exposto pela property `Pedido.badge_embarcado` (ortogonal).

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
    status = db.Column(db.String(20), nullable=False, default='ABERTO', index=True)
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
            "status IN ('ABERTO','COTADO','FATURADO','CANCELADO')",
            name='ck_carvia_pedido_status'
        ),
        db.CheckConstraint("filial IN ('SP', 'RJ')", name='ck_carvia_pedido_filial'),
        db.CheckConstraint(
            "tipo_separacao IN ('ESTOQUE', 'CROSSDOCK')",
            name='ck_carvia_pedido_tipo_sep'
        ),
    )

    @staticmethod
    def gerar_numero_pedido(cotacao_id=None):
        """Gera numero do pedido no formato PED-{cotacao_id}-{seq}.

        Se cotacao_id fornecido: PED-{cotacao_id}-{seq} (seq = proximo por cotacao).
        Se nao: fallback PED-CV-{max+1} (compatibilidade).
        """
        if cotacao_id:
            count = CarviaPedido.query.filter_by(cotacao_id=cotacao_id).count()
            return f'PED-{cotacao_id}-{count + 1}'

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
        """Status derivado do estado real, sem dependencia de coluna `status`.

        Fonte de verdade (2026-04-29 — refator robustez):
            - CANCELADO: coluna `status='CANCELADO'`.
            - FATURADO: TODOS itens com `numero_nf` E TODAS NFs em
              `CarviaNf` com `status='ATIVA'`. Decide independente de
              EmbarqueItem ou coluna `status`. Cobre casos de NF anexada
              antes/depois do embarque (recibo de impressao, importacao
              tardia, anexar manual).
            - COTADO: pedido em embarque ativo (`CARVIA-NF-{nf_id}`,
              `CARVIA-PED-{id}` legado, ou provisorio `CARVIA-COT-{cot}`).
            - ABERTO: nenhum dos anteriores.

        A coluna `status` continua sendo gravada para auditoria por
        `atualizar_status_pedido_carvia_pelo_faturamento` e por hooks
        de embarque, mas a UI sempre exibe esta property.
        """
        if self.status == 'CANCELADO':
            return 'CANCELADO'

        from app.embarques.models import EmbarqueItem
        from app.carvia.models.documentos import CarviaNf

        itens_lista = self.itens.all()

        # Sem itens -> coluna status manda (fallback para pedidos zumbis)
        if not itens_lista:
            return self.status if self.status in ('ABERTO', 'COTADO', 'FATURADO') else 'ABERTO'

        nf_nums = {i.numero_nf for i in itens_lista if i.numero_nf}

        # === Passo 1: FATURADO se TODOS itens tem NF e todas estao ATIVAS ===
        todos_com_nf = all(i.numero_nf and str(i.numero_nf).strip() for i in itens_lista)
        if todos_com_nf and nf_nums:
            nfs_ativas = CarviaNf.query.filter(
                CarviaNf.numero_nf.in_([str(n) for n in nf_nums]),
                CarviaNf.status == 'ATIVA',
            ).all()
            numeros_ativos = {str(nf.numero_nf) for nf in nfs_ativas}
            if all(str(n) in numeros_ativos for n in nf_nums):
                return 'FATURADO'

        # === Passo 2: COTADO se ha EmbarqueItem ativo (qualquer padrao) ===
        # 2a. Pedido com NF -> CARVIA-NF-{nf_id}
        if nf_nums:
            nfs_objs = CarviaNf.query.filter(
                CarviaNf.numero_nf.in_([str(n) for n in nf_nums])
            ).all()
            nf_ids = [nf.id for nf in nfs_objs]
            if nf_ids:
                lotes_nf = [f'CARVIA-NF-{nid}' for nid in nf_ids]
                ei_nf = EmbarqueItem.query.filter(
                    EmbarqueItem.separacao_lote_id.in_(lotes_nf),
                    EmbarqueItem.status == 'ativo',
                ).first()
                if ei_nf:
                    return 'COTADO'

        # 2b. Padrao legado CARVIA-PED-{id}
        em_legado = EmbarqueItem.query.filter_by(
            separacao_lote_id=f'CARVIA-PED-{self.id}',
            status='ativo',
        ).first()
        if em_legado:
            return 'COTADO'

        # 2c. Provisorio ativo na cotacao (CARVIA-COT-{id} ou via FK)
        ei_prov = EmbarqueItem.query.filter(
            EmbarqueItem.carvia_cotacao_id == self.cotacao_id,
            EmbarqueItem.provisorio == True,  # noqa: E712
            EmbarqueItem.status == 'ativo',
            db.or_(
                EmbarqueItem.volumes > 0,
                EmbarqueItem.peso > 0,
            ),
        ).first()
        if ei_prov:
            return 'COTADO'

        # === Passo 3: nada -> ABERTO ===
        return 'ABERTO'

    @property
    def embarque_ativo(self):
        """Retorna o objeto Embarque ativo associado a este pedido, ou None.

        Cobre 3 padroes de lote (na ordem de prioridade):
        1. CARVIA-NF-{nf_id} -> NFs do pedido (item real ja expandido)
        2. CARVIA-PED-{id} -> legado (compat backward)
        3. provisorio ativo via FK `carvia_cotacao_id` + `provisorio=True`

        Retorna o primeiro Embarque encontrado (consistencia com o
        fluxo: 1 cotacao -> 1 embarque por vez).
        """
        from app.embarques.models import EmbarqueItem, Embarque
        from app.carvia.models.documentos import CarviaNf

        itens_lista = self.itens.all()
        nf_nums = {i.numero_nf for i in itens_lista if i.numero_nf}

        # 1. Via NFs do pedido (CARVIA-NF-*)
        if nf_nums:
            nfs_objs = CarviaNf.query.filter(
                CarviaNf.numero_nf.in_([str(n) for n in nf_nums])
            ).all()
            if nfs_objs:
                lotes_nf = [f'CARVIA-NF-{nf.id}' for nf in nfs_objs]
                ei = EmbarqueItem.query.filter(
                    EmbarqueItem.separacao_lote_id.in_(lotes_nf),
                    EmbarqueItem.status == 'ativo',
                ).first()
                if ei:
                    return db.session.get(Embarque, ei.embarque_id)

        # 2. Legado CARVIA-PED-{id}
        ei_legado = EmbarqueItem.query.filter_by(
            separacao_lote_id=f'CARVIA-PED-{self.id}',
            status='ativo',
        ).first()
        if ei_legado:
            return db.session.get(Embarque, ei_legado.embarque_id)

        # 3. Provisorio via FK
        ei_prov = EmbarqueItem.query.filter(
            EmbarqueItem.carvia_cotacao_id == self.cotacao_id,
            EmbarqueItem.provisorio == True,  # noqa: E712
            EmbarqueItem.status == 'ativo',
        ).first()
        if ei_prov:
            return db.session.get(Embarque, ei_prov.embarque_id)

        return None

    @property
    def operacoes_ctes(self):
        """Lista de CarviaOperacao (CTes) vinculadas via NFs deste pedido.

        Retorna [] se nao ha NFs ou nenhuma NF tem CTe (operacao) ativa.
        """
        from app.carvia.models.documentos import (
            CarviaNf, CarviaOperacao, CarviaOperacaoNf,
        )

        itens_lista = self.itens.all()
        nf_nums = {i.numero_nf for i in itens_lista if i.numero_nf}
        if not nf_nums:
            return []

        operacoes = (
            db.session.query(CarviaOperacao)
            .join(CarviaOperacaoNf, CarviaOperacaoNf.operacao_id == CarviaOperacao.id)
            .join(CarviaNf, CarviaOperacaoNf.nf_id == CarviaNf.id)
            .filter(
                CarviaNf.numero_nf.in_([str(n) for n in nf_nums]),
                CarviaOperacao.status != 'CANCELADO',
            )
            .distinct()
            .all()
        )
        return operacoes

    @property
    def faturas_cliente(self):
        """Lista de CarviaFaturaCliente vinculadas via CTes deste pedido."""
        ops = self.operacoes_ctes
        if not ops:
            return []
        fat_ids = {op.fatura_cliente_id for op in ops if op.fatura_cliente_id}
        if not fat_ids:
            return []
        from app.carvia.models.faturas import CarviaFaturaCliente
        return (
            CarviaFaturaCliente.query
            .filter(CarviaFaturaCliente.id.in_(fat_ids))
            .all()
        )

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

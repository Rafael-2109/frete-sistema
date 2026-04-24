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
        """Status derivado do estado real, sem dependencia de atualizacao manual.

        Fluxo (P12 revisado, 2026-04-24):
            ABERTO -> COTADO -> FATURADO
            (EMBARCADO deixou de ser status. Saida da portaria e ortogonal
            — exposta via `Pedido.badge_embarcado`.)

        Regras:
          - FATURADO (nova semantica): pedido com coluna `status='FATURADO'`
            persistido (via `_marcar_pedidos_embarcado` ou
            `atualizar_status_pedido_carvia_pelo_faturamento`).
          - COTADO: pedido esta em embarque ativo (com ou sem data_embarque).
          - ABERTO: pedido sem embarque ativo.
          - CANCELADO: coluna status=CANCELADO.
        """
        if self.status == 'CANCELADO':
            return 'CANCELADO'
        if self.status == 'FATURADO':
            return 'FATURADO'

        from app.embarques.models import EmbarqueItem
        from app.carvia.models.documentos import CarviaNf

        itens_lista = self.itens.all()
        nf_nums = {i.numero_nf for i in itens_lista if i.numero_nf}

        # Passo 1: pedido COM NF propria — decide exclusivamente via CARVIA-NF-{nf_id}
        if nf_nums:
            for nf_num in nf_nums:
                nf_obj = CarviaNf.query.filter_by(numero_nf=str(nf_num)).first()
                if nf_obj:
                    ei = EmbarqueItem.query.filter_by(
                        separacao_lote_id=f'CARVIA-NF-{nf_obj.id}',
                        status='ativo',
                    ).first()
                    if ei:
                        return 'COTADO'
            # Pedido tem NF mas NENHUM EmbarqueItem CARVIA-NF-* ativo → ABERTO
            return 'ABERTO'

        # Passo 2: pedido SEM NF — padrao legado CARVIA-PED-{id}
        em_legado = EmbarqueItem.query.filter_by(
            separacao_lote_id=f'CARVIA-PED-{self.id}',
            status='ativo',
        ).first()
        if em_legado:
            return 'COTADO'

        # Passo 3: pedido SEM NF — provisorio ativo na cotacao
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

        return 'ABERTO'

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

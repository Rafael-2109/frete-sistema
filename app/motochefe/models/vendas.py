"""
Modelos de Vendas - Sistema MotoCHEFE
PedidoVendaMoto: Pedido que vira Venda quando faturado
PedidoVendaMotoItem: Itens do pedido (chassi alocado via FIFO)
PedidoVendaAuditoria: Auditoria de ações sobre pedidos (inserção e cancelamento)
"""
from app import db
from datetime import datetime, date
from app.utils.timezone import agora_utc_naive


class PedidoVendaMoto(db.Model):
    """
    Pedido de venda que evolui para Venda quando faturado
    1 Pedido = 1 NF (sem faturamento parcial)
    """
    __tablename__ = 'pedido_venda_moto'

    # PK
    id = db.Column(db.Integer, primary_key=True)
    numero_pedido = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Cliente
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente_moto.id'), nullable=False)

    # Vendedor e Equipe
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor_moto.id'), nullable=False)
    equipe_vendas_id = db.Column(db.Integer, db.ForeignKey('equipe_vendas_moto.id'), nullable=True)

    # Datas
    data_pedido = db.Column(db.Date, nullable=False, default=date.today)
    data_expedicao = db.Column(db.Date, nullable=True)

    # Status do fluxo (Pedido → Faturado → Enviado)
    faturado = db.Column(db.Boolean, default=False, nullable=False, index=True)
    enviado = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # 🆕 Status de aprovação do pedido
    status = db.Column(db.String(20), default='APROVADO', nullable=False, index=True)
    # Valores: 'PENDENTE', 'APROVADO', 'REJEITADO', 'CANCELADO'

    # Nota Fiscal (preenche quando faturado=True)
    numero_nf = db.Column(db.String(20), unique=True, nullable=True, index=True)
    numero_nf_importada = db.Column(db.String(20), nullable=True, index=True)  # NF importada (sem vínculo)
    data_nf = db.Column(db.Date, nullable=True)
    tipo_nf = db.Column(db.String(50), nullable=True)  # 'VENDA', 'REMESSA'

    # Valores
    valor_total_pedido = db.Column(db.Numeric(15, 2), nullable=False)
    valor_frete_cliente = db.Column(db.Numeric(15, 2), default=0)  # Cobrado do cliente

    # Pagamento
    forma_pagamento = db.Column(db.String(50), nullable=True)
    condicao_pagamento = db.Column(db.String(100), nullable=True)  # '10x sem juros'
    prazo_dias = db.Column(db.Integer, default=0, nullable=False)  # Prazo em dias para cálculo de vencimento
    numero_parcelas = db.Column(db.Integer, default=1, nullable=False)  # Número de parcelas do pedido

    # Logística
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadora_moto.id'), nullable=True)
    tipo_frete = db.Column(db.String(20), nullable=True)  # 'CIF', 'FOB'

    # Empresa emissora da NF (faturamento)
    empresa_venda_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True)

    # Observações
    observacoes = db.Column(db.Text, nullable=True)

    # Controle de impressão
    impresso = db.Column(db.Boolean, default=False, nullable=False, index=True)
    impresso_por = db.Column(db.String(100), nullable=True)
    impresso_em = db.Column(db.DateTime, nullable=True)

    # Relacionamentos
    cliente = db.relationship('ClienteMoto', backref='pedidos')
    vendedor = db.relationship('VendedorMoto', backref='pedidos')
    equipe = db.relationship('EquipeVendasMoto', backref='pedidos')
    transportadora = db.relationship('TransportadoraMoto', backref='pedidos')
    empresa_venda = db.relationship('EmpresaVendaMoto', backref='pedidos')
    itens = db.relationship('PedidoVendaMotoItem', backref='pedido', lazy='dynamic', cascade='all, delete-orphan')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=agora_utc_naive, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<PedidoVendaMoto {self.numero_pedido} - Faturado: {self.faturado}>'

    @property
    def quantidade_motos(self):
        """Retorna quantidade de motos no pedido"""
        return self.itens.count()

    @property
    def valor_total_com_frete(self):
        """Retorna valor total + frete"""
        return self.valor_total_pedido + (self.valor_frete_cliente or 0)

    @property
    def saldo_a_receber(self):
        """Retorna saldo total a receber somando todos os títulos do pedido"""
        from sqlalchemy import func
        from app.motochefe.models.financeiro import TituloFinanceiro

        saldo = db.session.query(func.sum(TituloFinanceiro.valor_saldo))\
            .filter(TituloFinanceiro.pedido_id == self.id)\
            .filter(TituloFinanceiro.status != 'CANCELADO')\
            .scalar()

        return saldo or 0

    @property
    def tem_nf(self):
        """Verifica se pedido tem NF (normal ou importada)"""
        return bool(self.numero_nf or self.numero_nf_importada)


class PedidoVendaMotoItem(db.Model):
    """
    Itens do pedido de venda
    Chassi é alocado via FIFO na criação do pedido
    """
    __tablename__ = 'pedido_venda_moto_item'

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # FK
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_venda_moto.id'), nullable=False, index=True)
    numero_chassi = db.Column(db.String(30), db.ForeignKey('moto.numero_chassi'), nullable=False, index=True)

    # Valores
    preco_venda = db.Column(db.Numeric(15, 2), nullable=False)

    # Montagem (opcional)
    montagem_contratada = db.Column(db.Boolean, default=False, nullable=False)
    valor_montagem = db.Column(db.Numeric(15, 2), default=0)
    fornecedor_montagem = db.Column(db.String(100), nullable=True)  # Equipe terceirizada

    # Controle de pagamento da montagem
    montagem_paga = db.Column(db.Boolean, default=False, nullable=False)
    data_pagamento_montagem = db.Column(db.Date, nullable=True)

    # 🆕 CONTROLE DE PAGAMENTO DE MONTAGEM EM LOTE
    empresa_pagadora_montagem_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True, index=True)
    # Empresa que pagou a montagem
    lote_pagamento_montagem_id = db.Column(db.Integer, nullable=True, index=True)
    # ID da MovimentacaoFinanceira PAI que agrupa este pagamento em lote

    # Relacionamentos
    moto = db.relationship('Moto', backref='vendas')
    empresa_pagadora_montagem = db.relationship('EmpresaVendaMoto', foreign_keys=[empresa_pagadora_montagem_id], backref='montagens_pagas')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<PedidoVendaMotoItem Pedido:{self.pedido_id} Chassi:{self.numero_chassi}>'

    @property
    def valor_total_item(self):
        """Retorna valor venda + montagem"""
        return self.preco_venda + (self.valor_montagem or 0)

    @property
    def excedente_tabela(self):
        """Calcula valor vendido acima da tabela (para comissão)"""
        if not self.moto or not self.moto.modelo:
            return 0

        preco_tabela = self.moto.modelo.preco_tabela
        excedente = self.preco_venda - preco_tabela
        return excedente if excedente > 0 else 0

    @property
    def montagem_paga_calculado(self):
        """
        ✅ FONTE DA VERDADE: TituloAPagar
        Verifica se montagem está paga baseado em TituloAPagar.status

        Returns:
            bool: True se título está PAGO, False caso contrário
        """
        from app.motochefe.models.financeiro import TituloAPagar

        if not self.montagem_contratada:
            return False

        # Buscar TituloAPagar MONTAGEM deste item
        titulo = TituloAPagar.query.filter_by(
            pedido_id=self.pedido_id,
            numero_chassi=self.numero_chassi,
            tipo='MONTAGEM'
        ).first()

        if not titulo:
            return False  # Título não criado ainda

        return titulo.status == 'PAGO'


class PedidoVendaAuditoria(db.Model):
    """
    Auditoria de ações sobre pedidos (inserção e cancelamento)
    Registra solicitações e confirmações/rejeições de mudanças

    Fluxos:
    1. INSERÇÃO: Novo pedido criado com ativo=False, status='PENDENTE'
       - Aprovação: ativo=True, status='APROVADO'
       - Rejeição: mantém ativo=False, status='REJEITADO'

    2. CANCELAMENTO: Pedido existente alterado para ativo=False, status='CANCELADO'
       - Aprovação: mantém ativo=False, status='CANCELADO'
       - Rejeição: REVERTE para ativo=True, status='APROVADO'
    """
    __tablename__ = 'pedido_venda_auditoria'

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # FK
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_venda_moto.id'), nullable=False, index=True)

    # Ação
    acao = db.Column(db.String(20), nullable=False, index=True)
    # Valores: 'INSERCAO', 'CANCELAMENTO'

    # Solicitação
    observacao = db.Column(db.Text, nullable=True)  # Motivo/justificativa
    solicitado_por = db.Column(db.String(100), nullable=False)
    solicitado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)

    # Confirmação/Rejeição (mutuamente exclusivas)
    confirmado = db.Column(db.Boolean, default=False, nullable=False, index=True)
    rejeitado = db.Column(db.Boolean, default=False, nullable=False, index=True)

    motivo_rejeicao = db.Column(db.Text, nullable=True)  # Obrigatório se rejeitado=True

    confirmado_por = db.Column(db.String(100), nullable=True)
    confirmado_em = db.Column(db.DateTime, nullable=True)

    # Relacionamento
    pedido = db.relationship('PedidoVendaMoto', backref='auditorias')

    # Índices compostos para queries eficientes
    __table_args__ = (
        db.Index('idx_auditoria_pendente', 'confirmado', 'rejeitado'),
        db.Index('idx_auditoria_acao_status', 'acao', 'confirmado', 'rejeitado'),
    )

    def __repr__(self):
        return f'<PedidoVendaAuditoria Pedido:{self.pedido_id} Acao:{self.acao} Confirmado:{self.confirmado}>'

    @property
    def status_atual(self):
        """Retorna status da ação"""
        if self.confirmado:
            return 'APROVADO'
        elif self.rejeitado:
            return 'REJEITADO'
        else:
            return 'PENDENTE'

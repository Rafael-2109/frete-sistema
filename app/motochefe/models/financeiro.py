"""
Modelos Financeiros - Sistema MotoCHEFE
TituloFinanceiro: Parcelas a receber
ComissaoVendedor: Comissões calculadas por venda
"""
from app import db
from datetime import datetime, date
from app.utils.timezone import agora_utc_naive


class TituloFinanceiro(db.Model):
    """
    Títulos a receber - REFATORADO
    Agora por MOTO + TIPO DE SERVIÇO
    Com suporte a parcelas dinâmicas e pagamentos parciais
    """
    __tablename__ = 'titulo_financeiro'

    # ====================
    # IDENTIFICAÇÃO
    # ====================
    id = db.Column(db.Integer, primary_key=True)

    # 🔴 FK para PEDIDO + MOTO
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_venda_moto.id'), nullable=False, index=True)
    numero_chassi = db.Column(db.String(30), db.ForeignKey('moto.numero_chassi'), nullable=False, index=True)

    # ====================
    # TIPO E ORDEM
    # ====================
    tipo_titulo = db.Column(db.String(20), nullable=False, index=True)
    # Valores: 'MOVIMENTACAO', 'MONTAGEM', 'FRETE', 'VENDA'

    ordem_pagamento = db.Column(db.Integer, nullable=False)
    # 1=Movimentação, 2=Montagem, 3=Frete, 4=Venda

    # ====================
    # PARCELA
    # ====================
    numero_parcela = db.Column(db.Integer, nullable=False, index=True)
    # Dinâmico: pode ser 1, 2, 3... N

    total_parcelas = db.Column(db.Integer, nullable=False, default=1, index=True)
    # Total de parcelas do título (ex: 3 se título dividido em 3x)

    valor_parcela = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    # Valor total da parcela (referência do parcelas_config)
    # 0 quando não há parcelamento (parcela única)

    # ====================
    # VALORES
    # ====================
    valor_original = db.Column(db.Numeric(15, 2), nullable=False)
    # Valor inicial do título (nunca muda)

    valor_saldo = db.Column(db.Numeric(15, 2), nullable=False)
    # Saldo devedor atual

    valor_pago_total = db.Column(db.Numeric(15, 2), default=0)
    # Total pago até agora

    # ====================
    # EMPRESA RECEBEDORA
    # ====================
    empresa_recebedora_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True, index=True)
    # Definido no momento do pagamento

    # ====================
    # DATAS
    # ====================
    data_emissao = db.Column(db.Date, nullable=False, default=date.today)
    prazo_dias = db.Column(db.Integer, nullable=True)
    data_vencimento = db.Column(db.Date, nullable=True)
    data_ultimo_pagamento = db.Column(db.Date, nullable=True)

    # ====================
    # STATUS
    # ====================
    status = db.Column(db.String(20), default='ABERTO', nullable=False, index=True)
    # RASCUNHO: Pedido não faturado
    # ABERTO: Pedido faturado, aguardando pagamento
    # PAGO: Totalmente quitado
    # CANCELADO: Cancelado

    # ====================
    # CONTROLE DE DIVISÃO
    # ====================
    titulo_pai_id = db.Column(db.Integer, db.ForeignKey('titulo_financeiro.id'), nullable=True)
    eh_titulo_dividido = db.Column(db.Boolean, default=False)
    historico_divisao = db.Column(db.Text, nullable=True)
    # JSON com histórico

    # ====================
    # AUDITORIA
    # ====================
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=agora_utc_naive, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # ====================
    # RELACIONAMENTOS
    # ====================
    pedido = db.relationship('PedidoVendaMoto', backref='titulos')
    moto = db.relationship('Moto', backref='titulos')
    empresa_recebedora = db.relationship('EmpresaVendaMoto', backref='titulos_receber')

    # Relacionamento recursivo
    titulos_filhos = db.relationship('TituloFinanceiro',
                                     foreign_keys=[titulo_pai_id],
                                     backref=db.backref('titulo_pai', remote_side=[id]))

    def __repr__(self):
        return f'<TituloFinanceiro {self.tipo_titulo} Moto:{self.numero_chassi} Parcela:{self.numero_parcela}>'

    @property
    def atrasado(self):
        """Verifica se título está vencido"""
        if self.status == 'PAGO':
            return False
        if not self.data_vencimento:
            return False
        return self.data_vencimento < date.today()

    @property
    def saldo_aberto(self):
        """Retorna saldo ainda não recebido (compatibilidade)"""
        return self.valor_saldo

    @property
    def percentual_pago(self):
        """Retorna percentual pago"""
        if self.valor_original == 0:
            return 0
        return (self.valor_pago_total / self.valor_original) * 100


class ComissaoVendedor(db.Model):
    """
    Comissões calculadas por venda - REFATORADO
    Agora POR MOTO (não mais por pedido)
    Valor Fixo + Excedente (acima da tabela)
    Rateada entre vendedores da mesma equipe
    """
    __tablename__ = 'comissao_vendedor'

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # FK
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_venda_moto.id'), nullable=False, index=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor_moto.id'), nullable=False, index=True)

    # 🆕 COMISSÃO POR MOTO
    numero_chassi = db.Column(db.String(30), db.ForeignKey('moto.numero_chassi'), nullable=False, index=True)

    # Cálculo da comissão
    valor_comissao_fixa = db.Column(db.Numeric(15, 2), nullable=False)
    valor_excedente = db.Column(db.Numeric(15, 2), default=0)  # Valor acima da tabela
    valor_total_comissao = db.Column(db.Numeric(15, 2), nullable=False)
    # valor_total = fixa + excedente

    # Rateio (se equipe tem N vendedores)
    qtd_vendedores_equipe = db.Column(db.Integer, default=1, nullable=False)
    valor_rateado = db.Column(db.Numeric(15, 2), nullable=False)
    # valor_rateado = valor_total / qtd_vendedores

    # Pagamento
    data_vencimento = db.Column(db.Date, nullable=True)
    data_pagamento = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)
    # Valores: PENDENTE, PAGO, CANCELADO

    # 🆕 CONTROLE DE PAGAMENTO EM LOTE
    empresa_pagadora_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True, index=True)
    # Empresa que pagou a comissão
    lote_pagamento_id = db.Column(db.Integer, nullable=True, index=True)
    # ID da MovimentacaoFinanceira PAI que agrupa este pagamento em lote

    # Relacionamentos
    pedido = db.relationship('PedidoVendaMoto', backref='comissoes')
    vendedor = db.relationship('VendedorMoto', backref='comissoes')
    moto = db.relationship('Moto', backref='comissoes')
    empresa_pagadora = db.relationship('EmpresaVendaMoto', foreign_keys=[empresa_pagadora_id], backref='comissoes_pagas')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    atualizado_em = db.Column(db.DateTime, onupdate=agora_utc_naive, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<ComissaoVendedor Vendedor:{self.vendedor_id} Pedido:{self.pedido_id} R${self.valor_rateado}>'

    @property
    def percentual_excedente(self):
        """Calcula percentual do excedente sobre o total"""
        if self.valor_total_comissao == 0:
            return 0
        return (self.valor_excedente / self.valor_total_comissao) * 100


class MovimentacaoFinanceira(db.Model):
    """
    Registro único de TODAS as movimentações financeiras
    Rastreabilidade completa de origem e destino
    Alimenta extrato financeiro e controla saldo das empresas
    """
    __tablename__ = 'movimentacao_financeira'

    # ====================
    # IDENTIFICAÇÃO
    # ====================
    id = db.Column(db.Integer, primary_key=True)

    tipo = db.Column(db.String(20), nullable=False, index=True)
    # Valores: 'RECEBIMENTO', 'PAGAMENTO'

    categoria = db.Column(db.String(50), nullable=False, index=True)
    # RECEBIMENTOS: 'Título Venda', 'Título Montagem', 'Título Frete', 'Título Movimentação'
    # PAGAMENTOS: 'Custo Moto', 'Montagem', 'Comissão', 'Frete', 'Despesa', 'Movimentação'

    # ====================
    # VALORES E DATA
    # ====================
    valor = db.Column(db.Numeric(15, 2), nullable=False)
    # Valor SEMPRE POSITIVO (tipo define se soma ou subtrai)

    data_movimentacao = db.Column(db.Date, nullable=False, index=True)

    # ====================
    # ORIGEM (Quem paga)
    # ====================
    empresa_origem_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True, index=True)
    # NULL para RECEBIMENTOS (origem é cliente)
    # PREENCHIDO para PAGAMENTOS (qual conta pagou)

    origem_tipo = db.Column(db.String(50), nullable=True)
    # Quando empresa_origem_id = NULL
    # Valores: 'Cliente', 'Outro'

    origem_identificacao = db.Column(db.String(255), nullable=True)
    # Nome/identificação textual da origem

    # ====================
    # DESTINO (Quem recebe)
    # ====================
    empresa_destino_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True, index=True)
    # PREENCHIDO para RECEBIMENTOS (qual conta recebeu)
    # NULL para PAGAMENTOS externos

    destino_tipo = db.Column(db.String(50), nullable=True)
    # Quando empresa_destino_id = NULL
    # Valores: 'Fornecedor', 'Vendedor', 'Transportadora', 'Despesa', 'Equipe Montagem'

    destino_identificacao = db.Column(db.String(255), nullable=True)
    # Nome/identificação textual do destino

    # ====================
    # RELACIONAMENTOS COM ENTIDADES
    # ====================
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_venda_moto.id'), nullable=True, index=True)
    numero_chassi = db.Column(db.String(30), db.ForeignKey('moto.numero_chassi'), nullable=True, index=True)
    titulo_financeiro_id = db.Column(db.Integer, db.ForeignKey('titulo_financeiro.id'), nullable=True, index=True)
    comissao_vendedor_id = db.Column(db.Integer, db.ForeignKey('comissao_vendedor.id'), nullable=True)
    embarque_moto_id = db.Column(db.Integer, db.ForeignKey('embarque_moto.id'), nullable=True)
    despesa_mensal_id = db.Column(db.Integer, db.ForeignKey('despesa_mensal.id'), nullable=True)

    # ====================
    # INFORMAÇÕES COMPLEMENTARES
    # ====================
    descricao = db.Column(db.Text, nullable=True)
    numero_nf = db.Column(db.String(20), nullable=True)
    numero_documento = db.Column(db.String(50), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    # ====================
    # CONTROLE DE BAIXA AUTOMÁTICA
    # ====================
    eh_baixa_automatica = db.Column(db.Boolean, default=False)
    movimentacao_origem_id = db.Column(db.Integer, db.ForeignKey('movimentacao_financeira.id'), nullable=True)

    # ====================
    # AUDITORIA
    # ====================
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)

    # ====================
    # RELACIONAMENTOS
    # ====================
    empresa_origem = db.relationship('EmpresaVendaMoto',
                                     foreign_keys=[empresa_origem_id],
                                     backref='movimentacoes_origem')
    empresa_destino = db.relationship('EmpresaVendaMoto',
                                      foreign_keys=[empresa_destino_id],
                                      backref='movimentacoes_destino')
    pedido = db.relationship('PedidoVendaMoto', backref='movimentacoes')
    moto = db.relationship('Moto', backref='movimentacoes')
    titulo = db.relationship('TituloFinanceiro', backref='movimentacoes')

    def __repr__(self):
        return f'<MovimentacaoFinanceira {self.tipo} {self.categoria} R$ {self.valor}>'


class TituloAPagar(db.Model):
    """
    Títulos a pagar gerados automaticamente
    Criados na EMISSÃO do pedido (status PENDENTE)
    Liberados quando cliente pagar título origem totalmente (status ABERTO)
    Usado para: Movimentação e Montagem
    """
    __tablename__ = 'titulo_a_pagar'

    # ====================
    # IDENTIFICAÇÃO
    # ====================
    id = db.Column(db.Integer, primary_key=True)

    tipo = db.Column(db.String(20), nullable=False, index=True)
    # Valores: 'MOVIMENTACAO', 'MONTAGEM'

    # ====================
    # ORIGEM (Título que gerou este)
    # ====================
    titulo_financeiro_id = db.Column(db.Integer, db.ForeignKey('titulo_financeiro.id'), nullable=False, index=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_venda_moto.id'), nullable=False, index=True)
    numero_chassi = db.Column(db.String(30), db.ForeignKey('moto.numero_chassi'), nullable=False, index=True)

    # ====================
    # BENEFICIÁRIO
    # ====================
    # Para MOVIMENTACAO:
    empresa_destino_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True)

    # Para MONTAGEM:
    fornecedor_montagem = db.Column(db.String(100), nullable=True)

    # ====================
    # VALORES
    # ====================
    valor_original = db.Column(db.Numeric(15, 2), nullable=False)
    # MOVIMENTACAO: Mesmo valor do título origem
    # MONTAGEM: Custo real (CustosOperacionais.custo_montagem)

    valor_pago = db.Column(db.Numeric(15, 2), default=0)
    valor_saldo = db.Column(db.Numeric(15, 2), nullable=False)

    # ====================
    # DATAS
    # ====================
    data_criacao = db.Column(db.Date, nullable=False, default=date.today)
    data_liberacao = db.Column(db.Date, nullable=True)
    data_vencimento = db.Column(db.Date, nullable=True)
    data_pagamento = db.Column(db.Date, nullable=True)

    # ====================
    # STATUS
    # ====================
    status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)
    # PENDENTE: Aguardando recebimento total do cliente
    # ABERTO: Liberado para pagamento
    # PAGO: Totalmente quitado
    # PARCIAL: Pagamento parcial
    # CANCELADO: Cancelado

    # ====================
    # CONTROLE
    # ====================
    observacoes = db.Column(db.Text, nullable=True)

    # ====================
    # AUDITORIA
    # ====================
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.String(100), default='SISTEMA', nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=agora_utc_naive, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # ====================
    # RELACIONAMENTOS
    # ====================
    titulo_origem = db.relationship('TituloFinanceiro', backref='titulo_a_pagar')
    pedido = db.relationship('PedidoVendaMoto', backref='titulos_a_pagar')
    moto = db.relationship('Moto', backref='titulos_a_pagar_moto')
    empresa_destino = db.relationship('EmpresaVendaMoto', backref='titulos_receber_internos')

    def __repr__(self):
        return f'<TituloAPagar {self.tipo} {self.status} R$ {self.valor_saldo}>'

    @property
    def beneficiario(self):
        """Retorna nome do beneficiário"""
        if self.tipo == 'MOVIMENTACAO':
            return self.empresa_destino.empresa if self.empresa_destino else 'MargemSogima'
        elif self.tipo == 'MONTAGEM':
            return self.fornecedor_montagem or 'Equipe Montagem'
        return 'Desconhecido'

    @property
    def fornecedor_nome(self):
        """
        Alias para beneficiario - compatibilidade com template
        Retorna nome do fornecedor/beneficiário dinamicamente
        """
        return self.beneficiario

    @property
    def pode_pagar(self):
        """Verifica se título está liberado para pagamento"""
        return self.status in ['ABERTO', 'PARCIAL']

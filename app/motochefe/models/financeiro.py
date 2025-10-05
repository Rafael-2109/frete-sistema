"""
Modelos Financeiros - Sistema MotoCHEFE
TituloFinanceiro: Parcelas a receber
ComissaoVendedor: Comissões calculadas por venda
"""
from app import db
from datetime import datetime, date


class TituloFinanceiro(db.Model):
    """
    Títulos a receber (parcelas de vendas parceladas)
    1 Venda = N Títulos (se parcelado)
    """
    __tablename__ = 'titulo_financeiro'

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # FK
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_venda_moto.id'), nullable=False, index=True)

    # Identificação da parcela
    numero_parcela = db.Column(db.Integer, nullable=False)  # 1, 2, 3...
    total_parcelas = db.Column(db.Integer, nullable=False)  # Ex: 10 (de 10x)

    # Valores
    valor_parcela = db.Column(db.Numeric(15, 2), nullable=False)
    prazo_dias = db.Column(db.Integer, nullable=True)  # Prazo em dias (ex: 30, 60, 90)
    data_vencimento = db.Column(db.Date, nullable=True)  # Calculado no faturamento

    # Recebimento
    data_recebimento = db.Column(db.Date, nullable=True)
    valor_recebido = db.Column(db.Numeric(15, 2), default=0)

    # Status
    status = db.Column(db.String(20), default='ABERTO', nullable=False, index=True)
    # Valores: ABERTO, PAGO, ATRASADO, CANCELADO

    # Relacionamentos
    pedido = db.relationship('PedidoVendaMoto', backref='titulos')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<TituloFinanceiro Pedido:{self.pedido_id} Parcela:{self.numero_parcela}/{self.total_parcelas}>'

    @property
    def atrasado(self):
        """Verifica se título está vencido"""
        if self.status == 'PAGO':
            return False
        return self.data_vencimento < date.today()

    @property
    def saldo_aberto(self):
        """Retorna saldo ainda não recebido"""
        return self.valor_parcela - (self.valor_recebido or 0)


class ComissaoVendedor(db.Model):
    """
    Comissões calculadas por venda
    Valor Fixo + Excedente (acima da tabela)
    Rateada entre vendedores da mesma equipe
    """
    __tablename__ = 'comissao_vendedor'

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # FK
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_venda_moto.id'), nullable=False, index=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor_moto.id'), nullable=False, index=True)

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

    # Relacionamentos
    pedido = db.relationship('PedidoVendaMoto', backref='comissoes')
    vendedor = db.relationship('VendedorMoto', backref='comissoes')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<ComissaoVendedor Vendedor:{self.vendedor_id} Pedido:{self.pedido_id} R${self.valor_rateado}>'

    @property
    def percentual_excedente(self):
        """Calcula percentual do excedente sobre o total"""
        if self.valor_total_comissao == 0:
            return 0
        return (self.valor_excedente / self.valor_total_comissao) * 100

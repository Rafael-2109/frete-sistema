"""
Modelos de Cadastro - Sistema MotoCHEFE
Mantidos dos models antigos, com auditoria padronizada
"""
from app import db
from datetime import datetime
from decimal import Decimal


class VendedorMoto(db.Model):
    """Cadastro de vendedores"""
    __tablename__ = 'vendedor_moto'

    id = db.Column(db.Integer, primary_key=True)
    vendedor = db.Column(db.String(100), nullable=False)
    equipe_vendas_id = db.Column(db.Integer, db.ForeignKey('equipe_vendas_moto.id'), nullable=False, index=True)
    # OBRIGATÓRIO: Todo vendedor DEVE estar em uma equipe

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<VendedorMoto {self.vendedor}>'


class EquipeVendasMoto(db.Model):
    """Cadastro de equipes de vendas"""
    __tablename__ = 'equipe_vendas_moto'

    id = db.Column(db.Integer, primary_key=True)
    equipe_vendas = db.Column(db.String(100), nullable=False, unique=True)

    # Configuração de Movimentação
    responsavel_movimentacao = db.Column(db.String(20), nullable=True)
    # Valores: 'NACOM'

    custo_movimentacao = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    # Custo específico de movimentação desta equipe (substitui custo_movimentacao_rj/nacom)

    incluir_custo_movimentacao = db.Column(db.Boolean, default=False, nullable=False)
    # TRUE: Adiciona custo_movimentacao ao preço final
    # FALSE: Custo já está incluído na tabela de preços

    # Configuração de Precificação
    tipo_precificacao = db.Column(db.String(20), default='TABELA', nullable=False)
    # Valores: 'TABELA' (usa TabelaPrecoEquipe) ou 'CUSTO_MARKUP' (custo_aquisicao + markup)

    markup = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    # Valor fixo adicionado ao custo quando tipo_precificacao='CUSTO_MARKUP'
    # Ex: R$ 500,00

    # Configuração de Comissão
    tipo_comissao = db.Column(db.String(20), default='FIXA_EXCEDENTE', nullable=False)
    # Valores: 'FIXA_EXCEDENTE' ou 'PERCENTUAL'

    # Para tipo FIXA_EXCEDENTE
    valor_comissao_fixa = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    # Excedente calculado automaticamente: (preco_venda - preco_tabela)

    # Para tipo PERCENTUAL
    percentual_comissao = db.Column(db.Numeric(5, 2), default=0, nullable=False)
    # Ex: 5.00 = 5%

    # Controle de Rateio
    comissao_rateada = db.Column(db.Boolean, default=True, nullable=False)
    # TRUE: Divide entre todos vendedores da equipe
    # FALSE: Apenas vendedor do pedido recebe

    # Controle de Montagem
    permitir_montagem = db.Column(db.Boolean, default=True, nullable=False)
    # TRUE: Exibe campos de montagem no formulário de pedidos
    # FALSE: Oculta e força montagem_contratada=False

    # 🆕 Controle de Prazo e Parcelamento
    permitir_prazo = db.Column(db.Boolean, default=False, nullable=False)
    # TRUE: Permite definir prazo de pagamento (dias)
    # FALSE: Vencimento = data_expedicao

    permitir_parcelamento = db.Column(db.Boolean, default=False, nullable=False)
    # TRUE: Permite múltiplas parcelas (grid de parcelas visível)
    # FALSE: Apenas 1 parcela

    # Relacionamentos
    vendedores = db.relationship('VendedorMoto', backref='equipe', lazy='dynamic')
    tabela_precos = db.relationship('TabelaPrecoEquipe', backref='equipe', lazy='dynamic', cascade='all, delete-orphan')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<EquipeVendasMoto {self.equipe_vendas}>'

    def obter_preco_modelo(self, modelo_id):
        """
        Retorna preço de venda para um modelo nesta equipe
        Fallback para preco_tabela do ModeloMoto se não houver registro específico
        """
        from .produto import ModeloMoto

        # Buscar preço específico da equipe
        tabela = TabelaPrecoEquipe.query.filter_by(
            equipe_vendas_id=self.id,
            modelo_id=modelo_id,
            ativo=True
        ).first()

        if tabela:
            return tabela.preco_venda

        # Fallback: usar preco_tabela do modelo
        modelo = ModeloMoto.query.get(modelo_id)
        return modelo.preco_tabela if modelo else Decimal('0')


class TabelaPrecoEquipe(db.Model):
    """
    Tabela de preços por Equipe x Modelo
    Usada quando equipe.tipo_precificacao = 'TABELA'
    """
    __tablename__ = 'tabela_preco_equipe'
    __table_args__ = (
        db.UniqueConstraint('equipe_vendas_id', 'modelo_id', name='uk_equipe_modelo_preco'),
    )

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # FK
    equipe_vendas_id = db.Column(db.Integer, db.ForeignKey('equipe_vendas_moto.id'), nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('modelo_moto.id'), nullable=False, index=True)

    # Preço
    preco_venda = db.Column(db.Numeric(15, 2), nullable=False)

    # Relacionamentos
    modelo = db.relationship('ModeloMoto', backref='precos_equipes')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<TabelaPrecoEquipe Equipe:{self.equipe_vendas_id} Modelo:{self.modelo_id} R${self.preco_venda}>'


class TransportadoraMoto(db.Model):
    """Cadastro de transportadoras"""
    __tablename__ = 'transportadora_moto'

    id = db.Column(db.Integer, primary_key=True)
    transportadora = db.Column(db.String(100), nullable=False, unique=True)
    cnpj = db.Column(db.String(20), nullable=True)
    telefone = db.Column(db.String(50), nullable=True)

    # Dados bancários
    chave_pix = db.Column(db.String(100), nullable=True)
    agencia = db.Column(db.String(20), nullable=True)
    conta = db.Column(db.String(20), nullable=True)
    banco = db.Column(db.String(100), nullable=True)
    cod_banco = db.Column(db.String(10), nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<TransportadoraMoto {self.transportadora}>'


class ClienteMoto(db.Model):
    """Cadastro de clientes"""
    __tablename__ = 'cliente_moto'

    id = db.Column(db.Integer, primary_key=True)
    cnpj_cliente = db.Column(db.String(20), unique=True, nullable=False)
    cliente = db.Column(db.String(100), nullable=False)

    # Relacionamento com vendedor (cascata: equipe → vendedor → cliente)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor_moto.id'), nullable=False, index=True)

    # CrossDocking
    crossdocking = db.Column(db.Boolean, default=False, nullable=False)
    # TRUE: Usa regras de CrossDocking genérico (único registro)
    # FALSE: Usa regras da EquipeVendasMoto do vendedor
    #
    # ⚠️ crossdocking_id REMOVIDO: Existe apenas 1 CrossDocking genérico compartilhado
    # ⚠️ O service busca automaticamente com CrossDocking.query.first()

    # Campos de endereço
    endereco_cliente = db.Column(db.String(100), nullable=True)
    numero_cliente = db.Column(db.String(20), nullable=True)
    complemento_cliente = db.Column(db.String(100), nullable=True)
    bairro_cliente = db.Column(db.String(100), nullable=True)
    cidade_cliente = db.Column(db.String(100), nullable=True)
    estado_cliente = db.Column(db.String(2), nullable=True)
    cep_cliente = db.Column(db.String(15), nullable=True)  # Aumentado de 10 para 15 (suporta formatos diversos)

    # Contato
    telefone_cliente = db.Column(db.String(100), nullable=True)  # Aumentado de 20 para 100 (múltiplos telefones)
    email_cliente = db.Column(db.String(100), nullable=True)

    # Relacionamentos
    vendedor = db.relationship('VendedorMoto', backref='clientes')
    # ⚠️ crossdocking_obj REMOVIDO: Não há mais FK para CrossDocking

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<ClienteMoto {self.cliente} - {self.cnpj_cliente}>'


class EmpresaVendaMoto(db.Model):
    """
    Cadastro de empresas - REFATORADO
    Agora funciona como conta bancária com saldo e controle financeiro
    """
    __tablename__ = 'empresa_venda_moto'

    id = db.Column(db.Integer, primary_key=True)
    cnpj_empresa = db.Column(db.String(20), unique=True, nullable=True)
    empresa = db.Column(db.String(255), nullable=False)

    # Dados bancários
    chave_pix = db.Column(db.String(100), nullable=True)
    banco = db.Column(db.String(100), nullable=True)
    cod_banco = db.Column(db.String(10), nullable=True)
    agencia = db.Column(db.String(20), nullable=True)
    conta = db.Column(db.String(20), nullable=True)

    # 🆕 CONTROLE FINANCEIRO
    baixa_compra_auto = db.Column(db.Boolean, default=False, nullable=False)
    # TRUE: Ao receber, paga motos automaticamente (FIFO)
    # FALSE: Apenas acumula saldo

    saldo = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    # Saldo atual da conta (calculado via MovimentacaoFinanceira)

    tipo_conta = db.Column(db.String(20), nullable=True)
    # Valores: 'FABRICANTE', 'OPERACIONAL', 'MARGEM_SOGIMA'

    # Auditoria
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<EmpresaVendaMoto {self.empresa} - Saldo: R$ {self.saldo}>'

    @property
    def saldo_calculado(self):
        """Calcula saldo baseado em MovimentacaoFinanceira (validação)"""
        from app.motochefe.models.financeiro import MovimentacaoFinanceira
        from sqlalchemy import func

        recebimentos = db.session.query(
            func.coalesce(func.sum(MovimentacaoFinanceira.valor), 0)
        ).filter_by(
            empresa_destino_id=self.id,
            tipo='RECEBIMENTO'
        ).scalar() or Decimal('0')

        pagamentos = db.session.query(
            func.coalesce(func.sum(MovimentacaoFinanceira.valor), 0)
        ).filter_by(
            empresa_origem_id=self.id,
            tipo='PAGAMENTO'
        ).scalar() or Decimal('0')

        return recebimentos - pagamentos


class CrossDocking(db.Model):
    """
    Regras de CrossDocking - Estrutura paralela a EquipeVendasMoto
    Quando cliente.crossdocking=True, usa estas regras ao invés de EquipeVendasMoto
    """
    __tablename__ = 'cross_docking'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)  # Identificação do CrossDocking
    descricao = db.Column(db.Text, nullable=True)

    # Configuração de Movimentação
    responsavel_movimentacao = db.Column(db.String(20), nullable=True)
    # Valores: 'RJ' ou 'NACOM'

    custo_movimentacao = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    # Custo específico de movimentação

    incluir_custo_movimentacao = db.Column(db.Boolean, default=False, nullable=False)
    # TRUE: Adiciona custo_movimentacao ao preço final
    # FALSE: Custo já está incluído na tabela de preços

    # Configuração de Precificação
    tipo_precificacao = db.Column(db.String(20), default='TABELA', nullable=False)
    # Valores: 'TABELA' (usa TabelaPrecoCrossDocking) ou 'CUSTO_MARKUP' (custo_aquisicao + markup)

    markup = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    # Valor fixo adicionado ao custo quando tipo_precificacao='CUSTO_MARKUP'

    # Configuração de Comissão
    tipo_comissao = db.Column(db.String(20), default='FIXA_EXCEDENTE', nullable=False)
    # Valores: 'FIXA_EXCEDENTE' ou 'PERCENTUAL'

    # Para tipo FIXA_EXCEDENTE
    valor_comissao_fixa = db.Column(db.Numeric(15, 2), default=0, nullable=False)

    # Para tipo PERCENTUAL
    percentual_comissao = db.Column(db.Numeric(5, 2), default=0, nullable=False)
    # Ex: 5.00 = 5%

    # Controle de Rateio
    comissao_rateada = db.Column(db.Boolean, default=True, nullable=False)
    # TRUE: Divide entre todos vendedores da equipe
    # FALSE: Apenas vendedor do pedido recebe

    # Controle de Montagem
    permitir_montagem = db.Column(db.Boolean, default=True, nullable=False)
    # TRUE: Exibe campos de montagem no formulário de pedidos
    # FALSE: Oculta e força montagem_contratada=False

    # Relacionamentos
    tabela_precos = db.relationship('TabelaPrecoCrossDocking', backref='crossdocking', lazy='dynamic', cascade='all, delete-orphan')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<CrossDocking {self.nome}>'

    def obter_preco_modelo(self, modelo_id):
        """
        Retorna preço de venda para um modelo neste CrossDocking
        Fallback para preco_tabela do ModeloMoto se não houver registro específico
        """
        from .produto import ModeloMoto

        # Buscar preço específico do CrossDocking
        tabela = TabelaPrecoCrossDocking.query.filter_by(
            crossdocking_id=self.id,
            modelo_id=modelo_id,
            ativo=True
        ).first()

        if tabela:
            return tabela.preco_venda

        # Fallback: usar preco_tabela do modelo
        modelo = ModeloMoto.query.get(modelo_id)
        return modelo.preco_tabela if modelo else Decimal('0')


class TabelaPrecoCrossDocking(db.Model):
    """
    Tabela de preços por CrossDocking x Modelo
    Usada quando crossdocking.tipo_precificacao = 'TABELA'
    """
    __tablename__ = 'tabela_preco_crossdocking'
    __table_args__ = (
        db.UniqueConstraint('crossdocking_id', 'modelo_id', name='uk_crossdocking_modelo_preco'),
    )

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # FK
    crossdocking_id = db.Column(db.Integer, db.ForeignKey('cross_docking.id'), nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('modelo_moto.id'), nullable=False, index=True)

    # Preço
    preco_venda = db.Column(db.Numeric(15, 2), nullable=False)

    # Relacionamentos
    modelo = db.relationship('ModeloMoto', backref='precos_crossdocking')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<TabelaPrecoCrossDocking CrossDocking:{self.crossdocking_id} Modelo:{self.modelo_id} R${self.preco_venda}>'

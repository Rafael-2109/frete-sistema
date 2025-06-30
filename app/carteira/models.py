# Modelos do módulo carteira
# FaturamentoPorProduto foi movido para app/faturamento/models.py

# TODO: Implementar modelos específicos do módulo carteira conforme necessário 

from app import db
from datetime import datetime, timedelta
from app.utils.timezone import agora_brasil
from sqlalchemy import func, and_, or_, Index
import logging

logger = logging.getLogger(__name__)

class CarteiraPrincipal(db.Model):
    """
    Modelo principal da carteira de pedidos - Baseado no arquivo 1
    Contém todos os 91 campos identificados + projeção D0-D28
    """
    __tablename__ = 'carteira_principal'

    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 CHAVES PRIMÁRIAS DE NEGÓCIO
    num_pedido = db.Column(db.String(50), nullable=False, index=True)  # Chave principal
    cod_produto = db.Column(db.String(50), nullable=False, index=True)  # Chave produto
    
    # 📋 DADOS DO PEDIDO
    pedido_cliente = db.Column(db.String(100), nullable=True)  # Pedido de Compra do Cliente
    data_pedido = db.Column(db.Date, nullable=True, index=True)  # Data de criação
    data_atual_pedido = db.Column(db.Date, nullable=True)  # Data da última alteração
    status_pedido = db.Column(db.String(50), nullable=True, index=True)  # Cancelado, Pedido de venda, Cotação
    
    # 👥 DADOS DO CLIENTE
    cnpj_cpf = db.Column(db.String(20), nullable=False, index=True)  # CNPJ do cliente
    raz_social = db.Column(db.String(255), nullable=True)  # Razão Social
    raz_social_red = db.Column(db.String(100), nullable=True)  # Nome reduzido
    municipio = db.Column(db.String(100), nullable=True)  # Cidade do cliente
    estado = db.Column(db.String(2), nullable=True)  # UF do cliente
    vendedor = db.Column(db.String(100), nullable=True, index=True)  # Vendedor responsável
    equipe_vendas = db.Column(db.String(100), nullable=True)  # Equipe de vendas
    
    # 📦 DADOS DO PRODUTO
    nome_produto = db.Column(db.String(255), nullable=False)  # Descrição do produto
    unid_medida_produto = db.Column(db.String(20), nullable=True)  # Unidade de medida
    embalagem_produto = db.Column(db.String(100), nullable=True)  # Categoria
    materia_prima_produto = db.Column(db.String(100), nullable=True)  # Sub categoria  
    categoria_produto = db.Column(db.String(100), nullable=True)  # Sub sub categoria
    
    # 📊 QUANTIDADES E VALORES
    qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)  # Quantidade original
    qtd_saldo_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)  # Saldo a faturar
    qtd_cancelada_produto_pedido = db.Column(db.Numeric(15, 3), default=0)  # Quantidade cancelada
    preco_produto_pedido = db.Column(db.Numeric(15, 2), nullable=True)  # Preço unitário
    
    # 💳 CONDIÇÕES COMERCIAIS
    cond_pgto_pedido = db.Column(db.String(100), nullable=True)  # Condições de pagamento
    forma_pgto_pedido = db.Column(db.String(100), nullable=True)  # Forma de pagamento
    incoterm = db.Column(db.String(20), nullable=True)  # Incoterm
    metodo_entrega_pedido = db.Column(db.String(50), nullable=True)  # Método de entrega
    data_entrega_pedido = db.Column(db.Date, nullable=True)  # Data de entrega
    cliente_nec_agendamento = db.Column(db.String(10), nullable=True)  # Sim/Não
    observ_ped_1 = db.Column(db.Text, nullable=True)  # Observações
    
    # 🏠 ENDEREÇO DE ENTREGA COMPLETO
    cnpj_endereco_ent = db.Column(db.String(20), nullable=True)  # CNPJ entrega
    empresa_endereco_ent = db.Column(db.String(255), nullable=True)  # Nome local entrega
    cep_endereco_ent = db.Column(db.String(10), nullable=True)  # CEP
    nome_cidade = db.Column(db.String(100), nullable=True)  # Cidade extraída
    cod_uf = db.Column(db.String(2), nullable=True)  # UF extraída  
    bairro_endereco_ent = db.Column(db.String(100), nullable=True)  # Bairro
    rua_endereco_ent = db.Column(db.String(255), nullable=True)  # Rua
    endereco_ent = db.Column(db.String(20), nullable=True)  # Número
    telefone_endereco_ent = db.Column(db.String(20), nullable=True)  # Telefone
    
    # 📅 DADOS OPERACIONAIS (PRESERVADOS na atualização)
    expedicao = db.Column(db.Date, nullable=True)  # Data prevista expedição  
    data_entrega = db.Column(db.Date, nullable=True)  # Data prevista entrega
    agendamento = db.Column(db.Date, nullable=True)  # Data agendamento
    protocolo = db.Column(db.String(50), nullable=True)  # Protocolo agendamento
    roteirizacao = db.Column(db.String(100), nullable=True)  # Transportadora sugerida
    
    # 📊 ANÁLISE DE ESTOQUE (CALCULADOS)
    menor_estoque_produto_d7 = db.Column(db.Numeric(15, 3), nullable=True)  # Previsão ruptura 7 dias
    saldo_estoque_pedido = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque na data expedição
    saldo_estoque_pedido_forcado = db.Column(db.Numeric(15, 3), nullable=True)  # Just-in-time
    
    # 🚛 DADOS DE CARGA/LOTE (PRESERVADOS)
    lote_separacao_id = db.Column(db.Integer, nullable=True, index=True)  # Vínculo separação
    qtd_saldo = db.Column(db.Numeric(15, 3), nullable=True)  # Qtd no lote
    valor_saldo = db.Column(db.Numeric(15, 2), nullable=True)  # Valor no lote
    pallet = db.Column(db.Numeric(15, 3), nullable=True)  # Pallets no lote
    peso = db.Column(db.Numeric(15, 3), nullable=True)  # Peso no lote
    
    # 📈 TOTALIZADORES POR CLIENTE (CALCULADOS)
    valor_saldo_total = db.Column(db.Numeric(15, 2), nullable=True)  # Valor total programado CNPJ
    pallet_total = db.Column(db.Numeric(15, 3), nullable=True)  # Pallet total programado CNPJ  
    peso_total = db.Column(db.Numeric(15, 3), nullable=True)  # Peso total programado CNPJ
    valor_cliente_pedido = db.Column(db.Numeric(15, 2), nullable=True)  # Valor total carteira CNPJ
    pallet_cliente_pedido = db.Column(db.Numeric(15, 3), nullable=True)  # Pallet total carteira CNPJ
    peso_cliente_pedido = db.Column(db.Numeric(15, 3), nullable=True)  # Peso total carteira CNPJ
    
    # 📊 TOTALIZADORES POR PRODUTO (CALCULADOS)
    qtd_total_produto_carteira = db.Column(db.Numeric(15, 3), nullable=True)  # Qtd total produto na carteira
    estoque = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque inicial/atual D0
    
    # 📈 PROJEÇÃO D0-D28 (28 CAMPOS DE ESTOQUE FUTURO)
    estoque_d0 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D0
    estoque_d1 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D1
    estoque_d2 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D2
    estoque_d3 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D3
    estoque_d4 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D4
    estoque_d5 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D5
    estoque_d6 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D6
    estoque_d7 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D7
    estoque_d8 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D8
    estoque_d9 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D9
    estoque_d10 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D10
    estoque_d11 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D11
    estoque_d12 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D12
    estoque_d13 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D13
    estoque_d14 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D14
    estoque_d15 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D15
    estoque_d16 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D16
    estoque_d17 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D17
    estoque_d18 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D18
    estoque_d19 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D19
    estoque_d20 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D20
    estoque_d21 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D21
    estoque_d22 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D22
    estoque_d23 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D23
    estoque_d24 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D24
    estoque_d25 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D25
    estoque_d26 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D26
    estoque_d27 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D27
    estoque_d28 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D28
    
    # 🛡️ AUDITORIA
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
    
    # 📊 ÍNDICES COMPOSTOS PARA PERFORMANCE
    __table_args__ = (
        # Chave única de negócio
        db.UniqueConstraint('num_pedido', 'cod_produto', name='uq_carteira_pedido_produto'),
        # Índices de consulta
        Index('idx_carteira_cliente_vendedor', 'cnpj_cpf', 'vendedor'),
        Index('idx_carteira_status_expedicao', 'status_pedido', 'expedicao'),
        Index('idx_carteira_produto_saldo', 'cod_produto', 'qtd_saldo_produto_pedido'),
        Index('idx_carteira_lote_separacao', 'lote_separacao_id'),
    )

    def __repr__(self):
        return f'<CarteiraPrincipal {self.num_pedido} - {self.cod_produto} - Saldo: {self.qtd_saldo_produto_pedido}>'

    def to_dict(self):
        """Converte para dicionário para APIs e exportações"""
        return {
            'id': self.id,
            'num_pedido': self.num_pedido,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'qtd_produto_pedido': float(self.qtd_produto_pedido) if self.qtd_produto_pedido else 0,
            'qtd_saldo_produto_pedido': float(self.qtd_saldo_produto_pedido) if self.qtd_saldo_produto_pedido else 0,
            'preco_produto_pedido': float(self.preco_produto_pedido) if self.preco_produto_pedido else 0,
            'cnpj_cpf': self.cnpj_cpf,
            'raz_social_red': self.raz_social_red,
            'vendedor': self.vendedor,
            'status_pedido': self.status_pedido,
            'expedicao': self.expedicao.strftime('%d/%m/%Y') if self.expedicao else None,
            'agendamento': self.agendamento.strftime('%d/%m/%Y') if self.agendamento else None,
            'protocolo': self.protocolo
        }

class CarteiraCopia(db.Model):
    """
    Modelo da carteira cópia - Baseado no arquivo 2
    Controle específico de baixas por faturamento
    """
    __tablename__ = 'carteira_copia'

    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 CHAVES PRIMÁRIAS DE NEGÓCIO (iguais à principal)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    
    # 📋 DADOS MESTRES (sincronizados com principal)
    pedido_cliente = db.Column(db.String(100), nullable=True)
    data_pedido = db.Column(db.Date, nullable=True)
    cnpj_cpf = db.Column(db.String(20), nullable=False, index=True)
    raz_social = db.Column(db.String(255), nullable=True)
    raz_social_red = db.Column(db.String(100), nullable=True)
    municipio = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    vendedor = db.Column(db.String(100), nullable=True)
    equipe_vendas = db.Column(db.String(100), nullable=True)
    
    # 📦 DADOS DO PRODUTO (sincronizados)
    nome_produto = db.Column(db.String(255), nullable=False)
    embalagem_produto = db.Column(db.String(100), nullable=True)
    materia_prima_produto = db.Column(db.String(100), nullable=True)
    categoria_produto = db.Column(db.String(100), nullable=True)
    
    # 📊 QUANTIDADES E VALORES (sincronizados com principal)
    qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_saldo_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_cancelada_produto_pedido = db.Column(db.Numeric(15, 3), default=0)
    preco_produto_pedido = db.Column(db.Numeric(15, 2), nullable=True)
    
    # 💳 CONDIÇÕES COMERCIAIS (sincronizadas)
    cond_pgto_pedido = db.Column(db.String(100), nullable=True)
    forma_pgto_pedido = db.Column(db.String(100), nullable=True)
    incoterm = db.Column(db.String(20), nullable=True)
    metodo_entrega_pedido = db.Column(db.String(50), nullable=True)
    data_entrega_pedido = db.Column(db.Date, nullable=True)
    cliente_nec_agendamento = db.Column(db.String(10), nullable=True)
    observ_ped_1 = db.Column(db.Text, nullable=True)
    status_pedido = db.Column(db.String(50), nullable=True)
    
    # 🏠 ENDEREÇO DE ENTREGA (sincronizado)
    cnpj_endereco_ent = db.Column(db.String(20), nullable=True)
    empresa_endereco_ent = db.Column(db.String(255), nullable=True)
    cep_endereco_ent = db.Column(db.String(10), nullable=True)
    nome_cidade = db.Column(db.String(100), nullable=True)
    cod_uf = db.Column(db.String(2), nullable=True)
    bairro_endereco_ent = db.Column(db.String(100), nullable=True)
    rua_endereco_ent = db.Column(db.String(255), nullable=True)
    endereco_ent = db.Column(db.String(20), nullable=True)
    telefone_endereco_ent = db.Column(db.String(20), nullable=True)
    
    # 💰 CONTROLE DE FATURAMENTO (ESPECÍFICO DA CÓPIA)
    baixa_produto_pedido = db.Column(db.Numeric(15, 3), default=0, nullable=False)  # ⭐ CAMPO CHAVE
    qtd_saldo_produto_calculado = db.Column(db.Numeric(15, 3), nullable=False)  # Calculado: qtd - cancelado - baixa
    
    # 🛡️ AUDITORIA
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
    
    # 📊 ÍNDICES COMPOSTOS
    __table_args__ = (
        db.UniqueConstraint('num_pedido', 'cod_produto', name='uq_carteira_copia_pedido_produto'),
        Index('idx_copia_cliente_baixa', 'cnpj_cpf', 'baixa_produto_pedido'),
        Index('idx_copia_saldo_calculado', 'qtd_saldo_produto_calculado'),
    )

    def __repr__(self):
        return f'<CarteiraCopia {self.num_pedido} - {self.cod_produto} - Baixa: {self.baixa_produto_pedido}>'

    def recalcular_saldo(self):
        """Recalcula saldo baseado nas quantidades atuais"""
        self.qtd_saldo_produto_calculado = (
            self.qtd_produto_pedido - 
            self.qtd_cancelada_produto_pedido - 
            self.baixa_produto_pedido
        )

class ControleCruzadoSeparacao(db.Model):
    """
    Controle cruzado entre separação baixada em Pedidos vs Carteira Cópia
    Detecta diferenças por ruptura de estoque ou inconsistências
    """
    __tablename__ = 'controle_cruzado_separacao'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO
    lote_separacao_id = db.Column(db.Integer, nullable=False, index=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    
    # 📊 QUANTIDADES
    qtd_separada_original = db.Column(db.Numeric(15,3), nullable=False)  # Quando gerou separação
    qtd_baixada_pedidos = db.Column(db.Numeric(15,3), nullable=True)     # Quando faturou em Pedidos
    qtd_baixada_carteira = db.Column(db.Numeric(15,3), nullable=True)    # Quando faturou na Carteira Cópia
    
    # 🎯 STATUS E DIFERENÇAS
    diferenca_detectada = db.Column(db.Numeric(15,3), nullable=True)  # qtd_baixada_pedidos - qtd_baixada_carteira
    status_controle = db.Column(db.String(20), default='AGUARDANDO', index=True)  # AGUARDANDO, CONFERIDO, DIFERENCA
    
    # 🔧 RESOLUÇÃO
    motivo_diferenca = db.Column(db.String(100), nullable=True)  # RUPTURA_ESTOQUE, CANCELAMENTO, etc
    resolvida = db.Column(db.Boolean, default=False, index=True)
    resolvida_por = db.Column(db.String(100), nullable=True)
    observacao_resolucao = db.Column(db.Text, nullable=True)
    
    # 🛡️ AUDITORIA
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    conferido_em = db.Column(db.DateTime, nullable=True)
    
    # 📊 ÍNDICES
    __table_args__ = (
        Index('idx_controle_lote_pedido', 'lote_separacao_id', 'num_pedido'),
        Index('idx_controle_status_diferenca', 'status_controle', 'diferenca_detectada'),
    )

    def __repr__(self):
        return f'<ControleCruzado Lote:{self.lote_separacao_id} {self.num_pedido}-{self.cod_produto} Dif:{self.diferenca_detectada}>'

class InconsistenciaFaturamento(db.Model):
    """
    Gestão de inconsistências entre faturamento e carteira
    Para detectar e resolver NFs problemáticas
    """
    __tablename__ = 'inconsistencia_faturamento'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False, index=True)  # FATURAMENTO_EXCEDE_SALDO, FATURAMENTO_SEM_PEDIDO
    
    # 📋 DADOS DA INCONSISTÊNCIA
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    num_pedido = db.Column(db.String(50), nullable=True)
    cod_produto = db.Column(db.String(50), nullable=False)
    
    # 📊 QUANTIDADES
    qtd_faturada = db.Column(db.Numeric(15,3), nullable=False)
    saldo_disponivel = db.Column(db.Numeric(15,3), nullable=True)
    qtd_excesso = db.Column(db.Numeric(15,3), nullable=True)
    
    # 🎯 STATUS E RESOLUÇÃO
    resolvida = db.Column(db.Boolean, default=False, index=True)
    acao_tomada = db.Column(db.String(50), nullable=True)  # CANCELAR_NF, AJUSTE_MANUAL, etc
    observacao_resolucao = db.Column(db.Text, nullable=True)
    
    # 🛡️ AUDITORIA
    detectada_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    resolvida_em = db.Column(db.DateTime, nullable=True)
    resolvida_por = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<Inconsistencia {self.tipo} NF:{self.numero_nf} Produto:{self.cod_produto}>'

class HistoricoFaturamento(db.Model):
    """
    Histórico detalhado de todas as baixas de faturamento na carteira
    Para auditoria e controle de reversões
    """
    __tablename__ = 'historico_faturamento'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    
    # 📊 DADOS DA BAIXA
    qtd_baixada = db.Column(db.Numeric(15,3), nullable=False)
    data_faturamento = db.Column(db.Date, nullable=False)
    
    # 🎯 STATUS
    cancelado = db.Column(db.Boolean, default=False, index=True)
    cancelado_em = db.Column(db.DateTime, nullable=True)
    cancelado_por = db.Column(db.String(100), nullable=True)
    motivo_cancelamento = db.Column(db.Text, nullable=True)
    
    # 🛡️ AUDITORIA
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    
    # 📊 ÍNDICES
    __table_args__ = (
        Index('idx_historico_nf_pedido', 'numero_nf', 'num_pedido'),
        Index('idx_historico_data_cancelado', 'data_faturamento', 'cancelado'),
    )

    def __repr__(self):
        return f'<HistoricoFaturamento NF:{self.numero_nf} {self.num_pedido}-{self.cod_produto} Qtd:{self.qtd_baixada}>'

class LogAtualizacaoCarteira(db.Model):
    """
    Log de auditoria para atualizações da carteira
    Rastreia todas as alterações em importações
    """
    __tablename__ = 'log_atualizacao_carteira'
    
    id = db.Column(db.Integer, primary_key=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    
    tipo_operacao = db.Column(db.String(20), nullable=False, index=True)  # CRIACAO, ATUALIZACAO
    campos_alterados = db.Column(db.JSON, nullable=True)  # Lista dos campos que mudaram
    
    valores_anteriores = db.Column(db.JSON, nullable=True)  # Backup dos valores antigos
    valores_novos = db.Column(db.JSON, nullable=True)  # Novos valores aplicados
    
    executado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    executado_por = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f'<LogAtualizacao {self.tipo_operacao} {self.num_pedido}-{self.cod_produto} por {self.executado_por}>' 
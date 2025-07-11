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

class VinculacaoCarteiraSeparacao(db.Model):
    """
    🔗 VINCULAÇÃO MULTI-DIMENSIONAL CARTEIRA ↔ SEPARAÇÃO
    
    PROBLEMA RESOLVIDO:
    - 1 pedido pode ter múltiplas cargas
    - 1 produto pode ser dividido em várias separações
    - Necessário vincular pela tríade: protocolo + agendamento + expedição
    
    CHAVE DE VINCULAÇÃO:
    num_pedido + cod_produto + protocolo + agendamento + expedição
    """
    __tablename__ = 'vinculacao_carteira_separacao'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 CHAVES DE VINCULAÇÃO MULTI-DIMENSIONAL
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    protocolo_agendamento = db.Column(db.String(50), nullable=False, index=True)
    data_agendamento = db.Column(db.Date, nullable=False, index=True)
    data_expedicao = db.Column(db.Date, nullable=False, index=True)
    
    # 🔗 IDs DE VINCULAÇÃO
    carteira_item_id = db.Column(db.Integer, nullable=False, index=True)  # FK para CarteiraPrincipal
    separacao_lote_id = db.Column(db.String(50), nullable=False, index=True)  # Lote da separação
    
    # 📊 QUANTIDADES CONTROLADAS
    qtd_carteira_original = db.Column(db.Numeric(15,3), nullable=False)  # Qtd quando criou vinculação
    qtd_separacao_original = db.Column(db.Numeric(15,3), nullable=False)  # Qtd na separação
    qtd_vinculada = db.Column(db.Numeric(15,3), nullable=False)  # Qtd efetivamente vinculada
    
    # 🎯 STATUS DA VINCULAÇÃO
    status_vinculacao = db.Column(db.String(20), default='ATIVA', index=True)  
    # ATIVA, DIVERGENTE, CANCELADA, FATURADA
    
    # 🔄 CONTROLE DE SINCRONIZAÇÃO
    ultima_sincronizacao = db.Column(db.DateTime, nullable=True)
    divergencia_detectada = db.Column(db.Boolean, default=False, index=True)
    tipo_divergencia = db.Column(db.String(50), nullable=True)  
    # QTD_ALTERADA, ITEM_CANCELADO, ITEM_FATURADO, PROTOCOLO_ALTERADO
    
    # 🛡️ AUDITORIA
    criada_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criada_por = db.Column(db.String(100), nullable=False)
    atualizada_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    
    # 📊 ÍNDICES COMPOSTOS CRÍTICOS
    __table_args__ = (
        # Chave única de vinculação multi-dimensional
        db.UniqueConstraint(
            'num_pedido', 'cod_produto', 'protocolo_agendamento', 
            'data_agendamento', 'data_expedicao',
            name='uq_vinculacao_multi_dimensional'
        ),
        # Índices de performance
        Index('idx_vinculacao_status_divergencia', 'status_vinculacao', 'divergencia_detectada'),
        Index('idx_vinculacao_carteira_separacao', 'carteira_item_id', 'separacao_lote_id'),
        Index('idx_vinculacao_protocolo_data', 'protocolo_agendamento', 'data_agendamento'),
    )

    def __repr__(self):
        return f'<VinculacaoCarteiraSeparacao {self.num_pedido}-{self.cod_produto} Protocolo:{self.protocolo_agendamento}>' 

class EventoCarteira(db.Model):
    """
    🎯 RASTREAMENTO DE EVENTOS DA CARTEIRA
    
    PROBLEMA RESOLVIDO:
    - Saber se item sumiu por FATURAMENTO ou CANCELAMENTO
    - Auditoria completa de todas as mudanças
    - Reconciliação automática entre sistemas
    """
    __tablename__ = 'evento_carteira'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    carteira_item_id = db.Column(db.Integer, nullable=False, index=True)
    
    # 🎯 TIPO DE EVENTO
    tipo_evento = db.Column(db.String(30), nullable=False, index=True)
    # FATURAMENTO, CANCELAMENTO, ALTERACAO_QTD, ALTERACAO_PROTOCOLO, 
    # ALTERACAO_AGENDAMENTO, ALTERACAO_EXPEDICAO
    
    # 📊 DADOS DO EVENTO
    qtd_anterior = db.Column(db.Numeric(15,3), nullable=True)
    qtd_nova = db.Column(db.Numeric(15,3), nullable=True)
    qtd_impactada = db.Column(db.Numeric(15,3), nullable=False)  # Diferença
    
    # 📋 DETALHES ESPECÍFICOS
    numero_nf = db.Column(db.String(20), nullable=True)  # Para FATURAMENTO
    motivo_cancelamento = db.Column(db.String(100), nullable=True)  # Para CANCELAMENTO
    campo_alterado = db.Column(db.String(50), nullable=True)  # Para ALTERACAO_*
    valor_anterior = db.Column(db.String(255), nullable=True)  # Valor anterior do campo
    valor_novo = db.Column(db.String(255), nullable=True)  # Novo valor do campo
    
    # 🔄 IMPACTO NA SEPARAÇÃO
    afeta_separacao = db.Column(db.Boolean, default=False, index=True)
    separacao_notificada = db.Column(db.Boolean, default=False, index=True)
    cotacao_afetada = db.Column(db.Boolean, default=False, index=True)
    responsavel_cotacao = db.Column(db.String(100), nullable=True)
    
    # 🎯 STATUS DO EVENTO
    status_processamento = db.Column(db.String(20), default='PENDENTE', index=True)
    # PENDENTE, PROCESSADO, REJEITADO, AGUARDA_APROVACAO
    
    # 🛡️ AUDITORIA
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    processado_em = db.Column(db.DateTime, nullable=True)
    processado_por = db.Column(db.String(100), nullable=True)
    
    # 📊 ÍNDICES
    __table_args__ = (
        Index('idx_evento_tipo_status', 'tipo_evento', 'status_processamento'),
        Index('idx_evento_cotacao_afetada', 'cotacao_afetada', 'responsavel_cotacao'),
        Index('idx_evento_separacao_notificada', 'afeta_separacao', 'separacao_notificada'),
        Index('idx_evento_pedido_produto', 'num_pedido', 'cod_produto'),
    )

    def __repr__(self):
        return f'<EventoCarteira {self.tipo_evento} {self.num_pedido}-{self.cod_produto} Qtd:{self.qtd_impactada}>' 

class AprovacaoMudancaCarteira(db.Model):
    """
    ✅ SISTEMA DE APROVAÇÃO PARA MUDANÇAS EM PEDIDOS COTADOS
    
    PROBLEMA RESOLVIDO:
    - Mudanças em pedidos cotados precisam de aprovação
    - Área específica para quem cotou visualizar mudanças
    - Workflow de aprovação sem passar batido
    """
    __tablename__ = 'aprovacao_mudanca_carteira'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO
    evento_carteira_id = db.Column(db.Integer, nullable=False, index=True)  # FK para EventoCarteira
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    
    # 🎯 DADOS DA COTAÇÃO AFETADA
    cotacao_id = db.Column(db.Integer, nullable=True, index=True)  # FK para CotacaoFrete (se existir)
    responsavel_cotacao = db.Column(db.String(100), nullable=False, index=True)
    valor_frete_cotado = db.Column(db.Numeric(15,2), nullable=True)
    transportadora_cotada = db.Column(db.String(100), nullable=True)
    
    # 📋 DETALHES DA MUDANÇA
    tipo_mudanca = db.Column(db.String(30), nullable=False)
    # ALTERACAO_QTD, CANCELAMENTO_ITEM, ALTERACAO_PROTOCOLO, ALTERACAO_DATA
    descricao_mudanca = db.Column(db.Text, nullable=False)
    impacto_estimado = db.Column(db.String(20), nullable=False)  # BAIXO, MEDIO, ALTO, CRITICO
    
    # 🎯 STATUS DA APROVAÇÃO
    status_aprovacao = db.Column(db.String(20), default='AGUARDA_VISUALIZACAO', index=True)
    # AGUARDA_VISUALIZACAO, VISUALIZADA, APROVADA, REJEITADA, EXPIRADA
    
    # ⏰ CONTROLE DE TEMPO
    prazo_resposta = db.Column(db.DateTime, nullable=False)  # 24h para visualizar, 48h para aprovar
    notificacoes_enviadas = db.Column(db.Integer, default=0)
    ultima_notificacao = db.Column(db.DateTime, nullable=True)
    
    # ✅ RESPOSTA DO RESPONSÁVEL
    visualizada_em = db.Column(db.DateTime, nullable=True)
    respondida_em = db.Column(db.DateTime, nullable=True)
    observacao_resposta = db.Column(db.Text, nullable=True)
    acao_tomada = db.Column(db.String(50), nullable=True)
    # ACEITAR_MUDANCA, REJEITAR_MUDANCA, REQUOTAR_FRETE, CANCELAR_COTACAO
    
    # 🔄 AÇÕES AUTOMÁTICAS
    acao_automatica_aplicada = db.Column(db.Boolean, default=False)
    motivo_acao_automatica = db.Column(db.String(100), nullable=True)
    
    # 🛡️ AUDITORIA
    criada_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criada_por = db.Column(db.String(100), nullable=False)
    
    # 📊 ÍNDICES
    __table_args__ = (
        Index('idx_aprovacao_responsavel_status', 'responsavel_cotacao', 'status_aprovacao'),
        Index('idx_aprovacao_prazo_status', 'prazo_resposta', 'status_aprovacao'),
        Index('idx_aprovacao_impacto_status', 'impacto_estimado', 'status_aprovacao'),
        Index('idx_aprovacao_pedido_produto', 'num_pedido', 'cod_produto'),
    )

    def __repr__(self):
        return f'<AprovacaoMudanca {self.num_pedido}-{self.cod_produto} Por:{self.responsavel_cotacao} Status:{self.status_aprovacao}>'
    
    def esta_vencida(self):
        """Verifica se a aprovação está vencida"""
        return agora_brasil() > self.prazo_resposta and self.status_aprovacao in ['AGUARDA_VISUALIZACAO', 'VISUALIZADA']
    
    def precisa_notificacao(self):
        """Verifica se precisa enviar notificação"""
        if self.status_aprovacao not in ['AGUARDA_VISUALIZACAO', 'VISUALIZADA']:
            return False
        
        # Primeira notificação imediata
        if self.notificacoes_enviadas == 0:
            return True
            
        # Notificações subsequentes a cada 4 horas
        if self.ultima_notificacao:
            tempo_desde_ultima = agora_brasil() - self.ultima_notificacao
            return tempo_desde_ultima.total_seconds() > 14400  # 4 horas
            
        return False 

class TipoCarga(db.Model):
    """
    🎯 CONTROLE DE TIPO DE CARGA - SOLUÇÃO PARA CONFLITO DE REGRAS
    
    PROBLEMA RESOLVIDO:
    - Separação parcial vs preservar dados operacionais
    - Alterações podem tornar carga inviável (peso limite)
    - Necessidade de controle inteligente de capacidade
    """
    __tablename__ = 'tipo_carga'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO DA CARGA
    separacao_lote_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    
    # 🎯 TIPO DE ENVIO (SOLUÇÃO PRINCIPAL)
    tipo_envio = db.Column(db.String(20), nullable=False, default='TOTAL', index=True)
    # TOTAL: Carga completa - aceita alterações até o limite
    # PARCIAL: Carga parcial planejada - alterações vão para nova carga  
    # COMPLEMENTAR: Carga para completar PARCIAL anterior
    # STANDBY: Aguardando definição comercial
    
    # 📊 CAPACIDADES E LIMITES
    capacidade_maxima_peso = db.Column(db.Numeric(15,3), nullable=True)     # Peso máximo suportado
    capacidade_maxima_pallets = db.Column(db.Numeric(15,3), nullable=True)  # Pallets máximos
    capacidade_maxima_valor = db.Column(db.Numeric(15,2), nullable=True)    # Valor máximo (seguro)
    
    # 📈 UTILIZAÇÃO ATUAL  
    peso_atual = db.Column(db.Numeric(15,3), default=0, nullable=False)
    pallets_atual = db.Column(db.Numeric(15,3), default=0, nullable=False)
    valor_atual = db.Column(db.Numeric(15,2), default=0, nullable=False)
    
    # 🔄 COMPORTAMENTO PARA ALTERAÇÕES
    aceita_incremento = db.Column(db.Boolean, default=True, nullable=False)
    # True: Alterações são adicionadas à carga existente
    # False: Alterações vão para nova carga (em branco)
    
    # 📋 JUSTIFICATIVA E CONTROLE
    motivo_tipo = db.Column(db.String(200), nullable=True)
    # "Carga completa planejada", "Separação parcial por peso", etc.
    
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    
    # 🔗 RELACIONAMENTO COM COMPLEMENTARES
    carga_principal_id = db.Column(db.Integer, db.ForeignKey('tipo_carga.id'), nullable=True)
    # Para cargas COMPLEMENTAR, aponta para a PARCIAL original
    
    def __repr__(self):
        return f'<FlexibilidadeCarga {self.separacao_lote_id} - {self.tipo_envio}>'
    
    @property
    def pode_aceitar_alteracao(self):
        """Verifica se a carga pode aceitar mais itens"""
        if not self.aceita_incremento:
            return False
            
        # Verifica limites de capacidade
        if self.capacidade_maxima_peso and self.peso_atual >= self.capacidade_maxima_peso:
            return False
            
        return True
    
    @property
    def percentual_utilizacao_peso(self):
        """Percentual de utilização do peso"""
        if not self.capacidade_maxima_peso:
            return 0
        return (float(self.peso_atual) / float(self.capacidade_maxima_peso)) * 100


class FaturamentoParcialJustificativa(db.Model):
    """
    📋 JUSTIFICATIVAS PARA FATURAMENTO PARCIAL
    
    PROBLEMA RESOLVIDO:
    - Separou 100, faturou 60 → Por que 40 não foram?
    - Tratamento inteligente do saldo restante
    - Decisão comercial sobre destino do saldo
    """
    __tablename__ = 'faturamento_parcial_justificativa'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO
    separacao_lote_id = db.Column(db.String(50), nullable=False, index=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    
    # 📊 QUANTIDADES
    qtd_separada = db.Column(db.Numeric(15,3), nullable=False)     # Quantidade na separação
    qtd_faturada = db.Column(db.Numeric(15,3), nullable=False)     # Quantidade faturada
    qtd_saldo = db.Column(db.Numeric(15,3), nullable=False)        # Saldo não faturado
    
    # 🔍 MOTIVO DO FATURAMENTO PARCIAL
    motivo_nao_faturamento = db.Column(db.String(20), nullable=False, index=True)
    # RUPTURA_ESTOQUE: Produto em falta
    # AVARIA_PRODUTO: Produto com defeito
    # ERRO_SEPARACAO: Separaram quantidade errada
    # ALTERACAO_PEDIDO: Cliente alterou pedido
    # CANCELAMENTO_PARCIAL: Cliente cancelou parte
    # RESTRICAO_TRANSPORTE: Não coube no veículo
    # OUTROS: Outros motivos
    
    # 📝 DETALHAMENTO
    descricao_detalhada = db.Column(db.Text, nullable=True)
    evidencias_anexas = db.Column(db.String(500), nullable=True)  # URLs de arquivos
    
    # 🎯 CLASSIFICAÇÃO DO SALDO
    classificacao_saldo = db.Column(db.String(20), nullable=False, index=True)
    # SALDO: Pode ser reaproveitado ou descartado
    # NECESSITA_COMPLEMENTO: Aguarda reposição/novo pedido
    # RETORNA_CARTEIRA: Volta à carteira com dados limpos
    # EXCLUIR_DEFINITIVO: Remove da carteira definitivamente
    
    # 📋 AÇÃO COMERCIAL TOMADA
    acao_comercial = db.Column(db.String(20), nullable=True, index=True)
    # AGUARDA_DECISAO: Pendente de análise comercial
    # RETORNOU_CARTEIRA: Voltou à carteira sem dados operacionais
    # NOVA_SEPARACAO: Criou nova separação
    # AGUARDA_REPOSICAO: Em standby para reposição
    # DESCARTADO: Removido definitivamente
    
    data_acao = db.Column(db.DateTime, nullable=True)
    executado_por = db.Column(db.String(100), nullable=True)
    observacoes_acao = db.Column(db.Text, nullable=True)
    
    # 🛡️ AUDITORIA
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    
    # 📊 ÍNDICES
    __table_args__ = (
        Index('idx_justificativa_separacao_pedido', 'separacao_lote_id', 'num_pedido'),
        Index('idx_justificativa_motivo_classificacao', 'motivo_nao_faturamento', 'classificacao_saldo'),
        Index('idx_justificativa_acao', 'acao_comercial', 'data_acao'),
    )

    def __repr__(self):
        return f'<FaturamentoParcial {self.separacao_lote_id} {self.num_pedido} - {self.motivo_nao_faturamento}>'


class ControleAlteracaoCarga(db.Model):
    """
    ⚖️ CONTROLE INTELIGENTE DE ALTERAÇÕES NA CARGA
    
    PROBLEMA RESOLVIDO:
    - Pedido tinha 100, separou 60, carteira importada com 120
    - Decidir se adiciona +20 na carga ou cria nova carga
    - Validar se carga suporta alteração (peso, dimensões)
    """
    __tablename__ = 'controle_alteracao_carga'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO
    carteira_item_id = db.Column(db.Integer, nullable=False, index=True)
    separacao_lote_id = db.Column(db.String(50), nullable=False, index=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    
    # 📊 ALTERAÇÃO DETECTADA
    qtd_anterior = db.Column(db.Numeric(15,3), nullable=False)      # Quantidade antes da alteração
    qtd_nova = db.Column(db.Numeric(15,3), nullable=False)          # Quantidade após alteração
    qtd_diferenca = db.Column(db.Numeric(15,3), nullable=False)     # Diferença (+/-)
    
    peso_anterior = db.Column(db.Numeric(15,3), nullable=True)
    peso_novo = db.Column(db.Numeric(15,3), nullable=True)
    peso_diferenca = db.Column(db.Numeric(15,3), nullable=True)
    
    # 🎯 DECISÃO TOMADA
    decisao_sistema = db.Column(db.String(20), nullable=False, index=True)
    # ADICIONAR_CARGA_ATUAL: Adicionou à carga existente
    # CRIAR_NOVA_CARGA: Criou nova carga para a diferença
    # REJEITAR_ALTERACAO: Manteve dados originais
    # AGUARDA_APROVACAO: Pendente de decisão manual
    
    # 🔍 MOTIVO DA DECISÃO
    motivo_decisao = db.Column(db.String(200), nullable=True)
    # "Carga suporta +20kg", "Peso excederia limite", etc.
    
    # 📋 VALIDAÇÕES DE CAPACIDADE
    capacidade_peso_ok = db.Column(db.Boolean, nullable=True)
    capacidade_pallets_ok = db.Column(db.Boolean, nullable=True)
    capacidade_valor_ok = db.Column(db.Boolean, nullable=True)
    
    # 🔄 AÇÃO EXECUTADA
    acao_executada = db.Column(db.String(20), nullable=True, index=True)
    # EXECUTADA: Ação foi aplicada
    # PENDENTE: Aguarda execução
    # CANCELADA: Decisão cancelada
    
    nova_carga_criada_id = db.Column(db.String(50), nullable=True)  # Se criou nova carga
    
    # 🛡️ AUDITORIA
    detectado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    processado_em = db.Column(db.DateTime, nullable=True)
    processado_por = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<ControleAlteracao {self.num_pedido} {self.decisao_sistema}: {self.qtd_diferenca}>'


class SaldoStandby(db.Model):
    """
    ⏸️ SALDOS EM STANDBY - AGUARDANDO DECISÃO COMERCIAL
    
    PROBLEMA RESOLVIDO:
    - "NECESSITA COMPLEMENTO" → Aguarda novo pedido do CNPJ
    - Controle temporal de saldos parados
    - Decisão comercial sobre destino final
    """
    __tablename__ = 'saldo_standby'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO
    origem_separacao_lote_id = db.Column(db.String(50), nullable=False, index=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255), nullable=False)
    
    # 📊 DADOS DO SALDO
    qtd_saldo = db.Column(db.Numeric(15,3), nullable=False)
    valor_saldo = db.Column(db.Numeric(15,2), nullable=False)
    peso_saldo = db.Column(db.Numeric(15,3), nullable=True)
    pallet_saldo = db.Column(db.Numeric(15,3), nullable=True)
    
    # 🎯 TIPO DE STANDBY
    tipo_standby = db.Column(db.String(20), nullable=False, index=True)
    # AGUARDA_COMPLEMENTO: Aguarda novo pedido mesmo CNPJ
    # AGUARDA_DECISAO: Aguarda decisão comercial
    # AGUARDA_REPOSICAO: Aguarda reposição de estoque
    
    # 📅 CONTROLE TEMPORAL
    data_limite_standby = db.Column(db.Date, nullable=True)  # Prazo máximo em standby
    dias_em_standby = db.Column(db.Integer, default=0)       # Contador automático
    
    # 🔔 ALERTAS E NOTIFICAÇÕES
    alertas_enviados = db.Column(db.Integer, default=0)
    proximo_alerta = db.Column(db.Date, nullable=True)
    
    # 🎯 RESOLUÇÃO
    status_standby = db.Column(db.String(20), default='ATIVO', index=True)
    # ATIVO: Em standby aguardando
    # RESOLVIDO: Problema resolvido
    # DESCARTADO: Removido definitivamente
    # TRANSFERIDO: Transferido para nova carga
    
    resolucao_final = db.Column(db.String(20), nullable=True)
    data_resolucao = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    observacoes_resolucao = db.Column(db.Text, nullable=True)
    
    # 🛡️ AUDITORIA
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f'<SaldoStandby {self.num_pedido} {self.cod_produto} - {self.qtd_saldo} - {self.tipo_standby}>'
    
    @property
    def dias_em_standby_calculado(self):
        """Calcula dias em standby automaticamente"""
        if self.status_standby != 'ATIVO':
            return self.dias_em_standby
            
        delta = datetime.now().date() - self.criado_em.date()
        return delta.days
    
    @property
    def precisa_alerta(self):
        """Verifica se precisa enviar alerta"""
        if self.status_standby != 'ATIVO':
            return False
            
        hoje = datetime.now().date()
        return not self.proximo_alerta or hoje >= self.proximo_alerta 

class ControleDescasamentoNF(db.Model):
    """
    🚨 CONTROLE CRÍTICO DE DESCASAMENTO - SOLUÇÃO PARA PROBLEMA IDENTIFICADO
    
    PROBLEMA RESOLVIDO:
    - NF preenchida em Embarques ≠ NF importada na carteira
    - Impacto direto em separações e justificativas parciais
    - Sincronização automática entre todos os sistemas
    """
    __tablename__ = 'controle_descasamento_nf'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO DA NF
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    
    # 📊 QUANTIDADES DOS 3 SISTEMAS
    qtd_embarques = db.Column(db.Numeric(15,3), nullable=True)        # Preenchido em Embarques
    qtd_importacao = db.Column(db.Numeric(15,3), nullable=True)       # Importação carteira
    qtd_separacao = db.Column(db.Numeric(15,3), nullable=True)        # Separação original
    
    # ⚠️ DETECÇÃO AUTOMÁTICA DE PROBLEMAS
    descasamento_detectado = db.Column(db.Boolean, default=False, index=True)
    tipo_descasamento = db.Column(db.String(50), nullable=True)
    # EMBARQUE_MAIOR_IMPORTACAO: Embarque faturou mais que carteira importou
    # IMPORTACAO_MAIOR_EMBARQUE: Carteira importou mais que embarque faturou
    # EXCEDE_SEPARACAO: Qualquer faturamento > separação original
    # DADOS_FALTANTES: Um dos sistemas sem dados
    
    diferenca_critica = db.Column(db.Numeric(15,3), nullable=True)    # Magnitude da diferença
    
    # 🎯 IMPACTOS IDENTIFICADOS
    impacta_separacao = db.Column(db.Boolean, default=False)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)
    justificativa_invalida = db.Column(db.Boolean, default=False)
    justificativa_id = db.Column(db.Integer, nullable=True)  # FK para FaturamentoParcialJustificativa
    
    # 🔧 RESOLUÇÃO AUTOMÁTICA
    acao_automatica = db.Column(db.String(50), nullable=True)
    # SINCRONIZAR_EMBARQUE: Usar dados da importação no embarque
    # SINCRONIZAR_CARTEIRA: Usar dados do embarque na carteira
    # CORRIGIR_SEPARACAO: Ajustar separação conforme realidade
    # RECRIAR_JUSTIFICATIVA: Refazer justificativa com dados corretos
    # AGUARDA_MANUAL: Precisa intervenção humana
    
    acao_executada = db.Column(db.Boolean, default=False)
    executada_em = db.Column(db.DateTime, nullable=True)
    
    # 📋 DADOS PARA RECONCILIAÇÃO
    fonte_correta = db.Column(db.String(20), nullable=True)  # EMBARQUES, IMPORTACAO, MEDIA
    qtd_reconciliada = db.Column(db.Numeric(15,3), nullable=True)    # Quantidade final acordada
    motivo_escolha = db.Column(db.String(200), nullable=True)
    
    # 🛡️ AUDITORIA
    detectado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    resolvido_em = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    
    # 📊 ÍNDICES PARA PERFORMANCE
    __table_args__ = (
        Index('idx_descasamento_nf_pedido', 'numero_nf', 'num_pedido'),
        Index('idx_descasamento_detectado_impacto', 'descasamento_detectado', 'impacta_separacao'),
        Index('idx_descasamento_acao', 'acao_automatica', 'acao_executada'),
        Index('idx_descasamento_separacao', 'separacao_lote_id', 'justificativa_invalida'),
    )

    def __repr__(self):
        return f'<ControleDescasamento NF:{self.numero_nf} {self.tipo_descasamento} - Diff:{self.diferenca_critica}>'
    
    @property
    def percentual_diferenca(self):
        """Calcula percentual da diferença em relação à separação"""
        if not self.qtd_separacao or self.qtd_separacao == 0:
            return 0
        return abs(float(self.diferenca_critica) / float(self.qtd_separacao)) * 100
    
    @property 
    def criticidade(self):
        """Classifica criticidade do descasamento"""
        perc = self.percentual_diferenca
        if perc == 0:
            return 'NENHUMA'
        elif perc <= 5:
            return 'BAIXA'
        elif perc <= 15:
            return 'MEDIA'
        elif perc <= 30:
            return 'ALTA'
        else:
            return 'CRITICA'
            
    def detectar_descasamento(self):
        """Algoritmo inteligente para detectar descasamento"""
        if not self.qtd_embarques or not self.qtd_importacao:
            self.tipo_descasamento = 'DADOS_FALTANTES'
            self.descasamento_detectado = True
            return
            
        # Comparação principal
        diff = abs(float(self.qtd_embarques) - float(self.qtd_importacao))
        
        if diff == 0:
            self.descasamento_detectado = False
            return
        
        self.diferenca_critica = diff
        self.descasamento_detectado = True
        
        # Classificação do tipo
        if self.qtd_embarques > self.qtd_importacao:
            self.tipo_descasamento = 'EMBARQUE_MAIOR_IMPORTACAO'
        else:
            self.tipo_descasamento = 'IMPORTACAO_MAIOR_EMBARQUE'
            
        # Verificação crítica vs separação
        if self.qtd_separacao:
            if max(self.qtd_embarques, self.qtd_importacao) > self.qtd_separacao:
                self.tipo_descasamento = 'EXCEDE_SEPARACAO'
                self.impacta_separacao = True
                
    def sugerir_acao_automatica(self):
        """Sugere ação automática baseada na análise"""
        if not self.descasamento_detectado:
            return
            
        if self.tipo_descasamento == 'DADOS_FALTANTES':
            self.acao_automatica = 'AGUARDA_MANUAL'
        elif self.tipo_descasamento == 'EXCEDE_SEPARACAO':
            self.acao_automatica = 'CORRIGIR_SEPARACAO'
        elif self.percentual_diferenca <= 5:  # Diferença pequena
            # Usar fonte com maior credibilidade (importação é mais recente)
            self.acao_automatica = 'SINCRONIZAR_EMBARQUE'
            self.fonte_correta = 'IMPORTACAO'
        else:
            self.acao_automatica = 'AGUARDA_MANUAL' 

class SnapshotCarteira(db.Model):
    """
    📸 SNAPSHOT NA IMPORTAÇÃO DA CARTEIRA - SOLUÇÃO CORRIGIDA
    
    MOMENTO CORRETO:
    - Snapshot criado na IMPORTAÇÃO da carteira
    - Separação pode ser alterada após snapshot
    - Faturamento sempre validado contra snapshot original
    """
    __tablename__ = 'snapshot_carteira'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO
    data_importacao = db.Column(db.DateTime, default=agora_brasil, nullable=False, index=True)
    versao_carteira = db.Column(db.String(50), nullable=False, index=True)  # Ex: "2025-06-30-18h30"
    
    # 📋 DADOS DO PEDIDO (PRESERVADOS NO MOMENTO DA IMPORTAÇÃO)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255), nullable=False)
    qtd_produto_pedido = db.Column(db.Float, nullable=False)
    preco_produto = db.Column(db.Float, nullable=False)
    valor_produto_pedido = db.Column(db.Float, nullable=False)
    
    # 🔗 CHAVE ÚNICA
    __table_args__ = (
        db.UniqueConstraint('num_pedido', 'cod_produto', 'versao_carteira'),
    )

class ValidacaoNFSimples(db.Model):
    """
    🎯 VALIDAÇÃO SIMPLIFICADA - APENAS PEDIDO + CNPJ
    
    PROBLEMA RESOLVIDO:
    - Não mais score de confiabilidade complexo
    - Validação simples: NF pertence ao pedido? CNPJ confere?
    - SIM = Executa tudo / NÃO = Bloqueia com motivo
    """
    __tablename__ = 'validacao_nf_simples'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO DA NF
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    data_validacao = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    
    # 🎯 VALIDAÇÃO SIMPLES
    num_pedido_nf = db.Column(db.String(50), nullable=False, index=True)
    cnpj_nf = db.Column(db.String(20), nullable=False, index=True)
    
    # ✅ RESULTADO DA VALIDAÇÃO
    pedido_encontrado = db.Column(db.Boolean, default=False, nullable=False)
    cnpj_confere = db.Column(db.Boolean, default=False, nullable=False)
    
    # 🎯 DECISÃO FINAL (SIMPLES)
    validacao_aprovada = db.Column(db.Boolean, default=False, nullable=False, index=True)
    # True = Executa frete + monitoramento
    # False = Bloqueia com motivo
    
    # 📝 DETALHES
    cnpj_esperado = db.Column(db.String(20), nullable=True)  # CNPJ do pedido
    cnpj_recebido = db.Column(db.String(20), nullable=True)  # CNPJ da NF
    motivo_bloqueio = db.Column(db.Text, nullable=True)
    
    # 🛠️ DADOS DA AÇÃO
    frete_gerado = db.Column(db.Boolean, default=False)
    monitoramento_registrado = db.Column(db.Boolean, default=False)
    data_execucao = db.Column(db.DateTime, nullable=True)
    
    def validar_nf_simples(self):
        """
        🎯 VALIDAÇÃO ULTRA SIMPLES
        
        REGRA:
        1. Pedido existe no snapshot? ✅/❌
        2. CNPJ da NF = CNPJ do pedido? ✅/❌
        3. Ambos OK = EXECUTA / Um falha = BLOQUEIA
        """
        
        # 1️⃣ BUSCAR PEDIDO NO SNAPSHOT
        snapshot = SnapshotCarteira.query.filter_by(
            num_pedido=self.num_pedido_nf
        ).first()
        
        if not snapshot:
            self.pedido_encontrado = False
            self.motivo_bloqueio = f"Pedido {self.num_pedido_nf} não encontrado na carteira"
            self.validacao_aprovada = False
            return False
        
        self.pedido_encontrado = True
        self.cnpj_esperado = snapshot.cnpj_cliente
        
        # 2️⃣ COMPARAR CNPJ
        if self.cnpj_nf.replace('.', '').replace('/', '').replace('-', '') == \
           self.cnpj_esperado.replace('.', '').replace('/', '').replace('-', ''):
            self.cnpj_confere = True
            self.validacao_aprovada = True
            return True
        else:
            self.cnpj_confere = False
            self.cnpj_recebido = self.cnpj_nf
            self.motivo_bloqueio = f"CNPJ não confere. Esperado: {self.cnpj_esperado}, Recebido: {self.cnpj_nf}"
            self.validacao_aprovada = False
            return False

class TipoEnvio(db.Model):
    """
    🎯 TIPO DE ENVIO SIMPLIFICADO - PARCIAL/TOTAL
    """
    __tablename__ = 'tipo_envio'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO DA CARGA
    separacao_lote_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    
    # 🎯 TIPO DE ENVIO
    tipo_envio = db.Column(db.String(20), nullable=False, default='TOTAL', index=True)
    # TOTAL: Carga completa - aceita alterações até o limite
    # PARCIAL: Carga parcial planejada - alterações vão para nova carga
    
    # 📊 CONTROLE DE CAPACIDADE
    capacidade_peso_kg = db.Column(db.Float, nullable=True, default=0)
    capacidade_volume_m3 = db.Column(db.Float, nullable=True, default=0)
    peso_atual_kg = db.Column(db.Float, nullable=False, default=0)
    volume_atual_m3 = db.Column(db.Float, nullable=False, default=0)
    
    # 📅 AUDITORIA
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    
    @property
    def capacidade_disponivel_peso(self):
        """Peso disponível em kg"""
        if self.capacidade_peso_kg and self.capacidade_peso_kg > 0:
            return max(0, self.capacidade_peso_kg - self.peso_atual_kg)
        return float('inf')  # Sem limite
    
    @property  
    def capacidade_disponivel_volume(self):
        """Volume disponível em m³"""
        if self.capacidade_volume_m3 and self.capacidade_volume_m3 > 0:
            return max(0, self.capacidade_volume_m3 - self.volume_atual_m3)
        return float('inf')  # Sem limite
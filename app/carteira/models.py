# Modelos do módulo carteira
# FaturamentoPorProduto foi movido para app/faturamento/models.py

# TODO: Implementar modelos específicos do módulo carteira conforme necessário 

from app import db
from datetime import datetime, timezone
from app.utils.timezone import agora_brasil
from sqlalchemy import and_, Index, func
import logging
import hashlib
from decimal import Decimal

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
    metodo_entrega_pedido = db.Column(db.String(100), nullable=True)  # Método de entrega - aumentado de 50 para 100
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
    telefone_endereco_ent = db.Column(db.String(50), nullable=True)  # Telefone - aumentado de 20 para 50
    
    # 📅 DADOS OPERACIONAIS (PRESERVADOS na atualização)
    expedicao = db.Column(db.Date, nullable=True)  # Data prevista expedição  
    data_entrega = db.Column(db.Date, nullable=True)  # Data prevista entrega
    agendamento = db.Column(db.Date, nullable=True)  # Data agendamento
    hora_agendamento = db.Column(db.Time, nullable=True)  # Hora agendamento
    protocolo = db.Column(db.String(50), nullable=True)  # Protocolo agendamento
    agendamento_confirmado = db.Column(db.Boolean, nullable=True, default=False)  # Agendamento confirmado
    roteirizacao = db.Column(db.String(100), nullable=True)  # Transportadora sugerida
    
    # 📊 ANÁLISE DE ESTOQUE (CALCULADOS)
    menor_estoque_produto_d7 = db.Column(db.Numeric(15, 3), nullable=True)  # Previsão ruptura 7 dias
    saldo_estoque_pedido = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque na data expedição
    saldo_estoque_pedido_forcado = db.Column(db.Numeric(15, 3), nullable=True)  # Just-in-time
    
    # 🚛 DADOS DE CARGA/LOTE (PRESERVADOS)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # Vínculo separação
    qtd_saldo = db.Column(db.Numeric(15, 3), nullable=True)  # Qtd no lote
    valor_saldo = db.Column(db.Numeric(15, 2), nullable=True)  # Valor no lote
    pallet = db.Column(db.Numeric(15, 3), nullable=True)  # Pallets no lote
    peso = db.Column(db.Numeric(15, 3), nullable=True)  # Peso no lote
    
    # 🛣️ DADOS DE ROTA E SUB-ROTA (ADICIONADOS)
    rota = db.Column(db.String(50), nullable=True)  # Rota principal baseada em cod_uf
    sub_rota = db.Column(db.String(50), nullable=True)  # Sub-rota baseada em cod_uf + nome_cidade
    
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
        Index('idx_carteira_separacao_lote', 'separacao_lote_id'),
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
    num_pedido = db.Column(db.String(50), nullable=False, index=True) #Campo "NUMERO DO PEDIDO DO REPRESENTANTE"
    cod_produto = db.Column(db.String(50), nullable=False, index=True) #Campo "CÓDIGO" ou "Codigo"
    
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
    metodo_entrega_pedido = db.Column(db.String(100), nullable=True)
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
    telefone_endereco_ent = db.Column(db.String(50), nullable=True)
    
    # 💰 CONTROLE DE FATURAMENTO (ESPECÍFICO DA CÓPIA)
    _baixa_produto_pedido_old = db.Column('baixa_produto_pedido', db.Numeric(15, 3), default=0, nullable=False)  # Campo legado
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

    @property
    def baixa_produto_pedido(self):
        """
        Calcula dinamicamente a baixa do produto baseada em FaturamentoProduto
        Soma todas as quantidades faturadas onde:
        - origem = num_pedido
        - cod_produto = cod_produto
        """
        from app.faturamento.models import FaturamentoProduto
        
        total_baixa = db.session.query(
            func.sum(FaturamentoProduto.qtd_produto_faturado)
        ).filter(
            FaturamentoProduto.origem == self.num_pedido,
            FaturamentoProduto.cod_produto == self.cod_produto
        ).scalar()
        
        return float(total_baixa or 0)

    def __repr__(self):
        return f'<CarteiraCopia {self.num_pedido} - {self.cod_produto} - Baixa: {self.baixa_produto_pedido}>'

    def recalcular_saldo(self):
        """Recalcula saldo baseado nas quantidades atuais"""
        # Agora usa a property calculada dinamicamente
        self.qtd_saldo_produto_calculado = float(
            self.qtd_produto_pedido - 
            self.qtd_cancelada_produto_pedido - 
            self.baixa_produto_pedido  # Usa property calculada dinamicamente
        )
    
    def sincronizar_com_principal(self):
        """
        Sincroniza qtd_saldo_produto_pedido da CarteiraPrincipal
        para pedidos que NÃO começam com VCD, VFB ou VSC
        """
        # Verifica se é um pedido que deve ser sincronizado
        prefixos_excluidos = ('VCD', 'VFB', 'VSC')
        if self.num_pedido.startswith(prefixos_excluidos):
            return  # Não sincroniza estes tipos
        
        # Busca CarteiraPrincipal correspondente
        carteira_principal = CarteiraPrincipal.query.filter_by(
            num_pedido=self.num_pedido,
            cod_produto=self.cod_produto
        ).first()
        
        if carteira_principal:
            # Sincroniza o saldo calculado
            carteira_principal.qtd_saldo_produto_pedido = self.qtd_saldo_produto_calculado
            logger.info(f"Sincronizado CarteiraPrincipal {self.num_pedido}/{self.cod_produto}: saldo={self.qtd_saldo_produto_calculado}")

class ControleCruzadoSeparacao(db.Model):
    """
    Controle cruzado entre separação baixada em Pedidos vs Carteira Cópia
    Detecta diferenças por ruptura de estoque ou inconsistências
    """
    __tablename__ = 'controle_cruzado_separacao'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 IDENTIFICAÇÃO
    separacao_lote_id = db.Column(db.String(50), nullable=False, index=True)
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
        Index('idx_controle_separacao_lote_pedido', 'separacao_lote_id', 'num_pedido'),
        Index('idx_controle_status_diferenca', 'status_controle', 'diferenca_detectada'),
    )

    def __repr__(self):
        return f'<ControleCruzado Lote:{self.separacao_lote_id} {self.num_pedido}-{self.cod_produto} Dif:{self.diferenca_detectada}>'

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

# ControleAlteracaoCarga - CLASSE REMOVIDA (obsoleta)
# Funcionalidade não utilizada no sistema atual

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



class PreSeparacaoItem(db.Model):
    """
    Modelo para sistema de pré-separação que SOBREVIVE à reimportação do Odoo
    
    FUNCIONALIDADE CRÍTICA: Quando Odoo reimporta e SUBSTITUI a carteira_principal,
    este modelo preserva as decisões dos usuários e permite "recompor" as divisões.
    
    FLUXO DE RECOMPOSIÇÃO:
    1. Usuário faz pré-separação (divisão parcial)
    2. Sistema salva dados com chave de negócio estável  
    3. Odoo reimporta → carteira_principal é substituída
    4. Sistema detecta pré-separações não recompostas
    5. Aplica novamente as divisões na nova carteira
    6. Preserva dados editáveis (datas, protocolos, etc.)
    """
    
    __tablename__ = 'pre_separacao_item'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de pré-separação
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True) 
    cnpj_cliente = db.Column(db.String(20), index=True)
    
    #  DADOS ORIGINAIS (momento da pré-separação)
    nome_produto = db.Column(db.String(255), nullable=True)
    qtd_original_carteira = db.Column(db.Numeric(15, 3), nullable=False)  # Qtd total no momento
    qtd_selecionada_usuario = db.Column(db.Numeric(15, 3), nullable=False)  # Qtd escolhida
    qtd_restante_calculada = db.Column(db.Numeric(15, 3), nullable=False)  # Saldo restante
    
    # Dados originais preservados (sobrevivência à reimportação)
    valor_original_item = db.Column(db.Numeric(15,2))
    peso_original_item = db.Column(db.Numeric(15,3))
    hash_item_original = db.Column(db.String(128))
    
    # Trabalho do usuário preservado
    data_expedicao_editada = db.Column(db.Date, nullable=False)  # ✅ OBRIGATÓRIO para constraint única
    data_agendamento_editada = db.Column(db.Date)
    protocolo_editado = db.Column(db.String(50))
    observacoes_usuario = db.Column(db.Text)
    
    # Controle de recomposição (sobrevivência ao Odoo)
    recomposto = db.Column(db.Boolean, default=False, index=True)
    data_recomposicao = db.Column(db.DateTime)
    recomposto_por = db.Column(db.String(100))
    versao_carteira_original = db.Column(db.String(50))
    versao_carteira_recomposta = db.Column(db.String(50))
    
    # Status e tipo
    status = db.Column(db.String(20), default='CRIADO', index=True)  # CRIADO, RECOMPOSTO, ENVIADO_SEPARACAO
    tipo_envio = db.Column(db.String(10), default='total')  # total, parcial
    
    # Auditoria
    data_criacao = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    criado_por = db.Column(db.String(100))
    
    # ✅ CONSTRAINT ÚNICA COMPOSTA - Sistema de contexto único
    # Permite múltiplas pré-separações POR CONTEXTO diferente (data + agendamento + protocolo)
    __table_args__ = (
        # Constraint única: mesmo pedido/produto pode ter múltiplas pré-separações com contextos diferentes
        # NOTA: func.coalesce será aplicado via trigger/constraint de BD para campos NULL
        db.UniqueConstraint(
            'num_pedido', 
            'cod_produto', 
            'data_expedicao_editada',
            'data_agendamento_editada',
            'protocolo_editado',
            name='uq_pre_separacao_contexto_unico'
        ),
        # Índices de performance
        db.Index('idx_pre_sep_data_expedicao', 'cod_produto', 'data_expedicao_editada', 'status'),
        db.Index('idx_pre_sep_dashboard', 'num_pedido', 'status', 'data_criacao'),
        db.Index('idx_pre_sep_recomposicao', 'recomposto', 'hash_item_original'),
    )
    
    def __repr__(self):
        return f'<PreSeparacaoItem {self.num_pedido}-{self.cod_produto}: {self.qtd_selecionada_usuario}/{self.qtd_original_carteira}>'
    
    # ===== PROPERTIES CALCULADAS =====
    
    @property
    def valor_selecionado(self):
        """Valor da quantidade selecionada"""
        if self.valor_original_item and self.qtd_original_carteira:
            return (float(self.qtd_selecionada_usuario) / float(self.qtd_original_carteira)) * float(self.valor_original_item)
        return 0
    
    @property 
    def valor_restante(self):
        """Valor da quantidade restante"""
        if self.valor_original_item and self.qtd_original_carteira:
            return (float(self.qtd_restante_calculada) / float(self.qtd_original_carteira)) * float(self.valor_original_item)
        return 0
        
    @property
    def peso_selecionado(self):
        """Peso da quantidade selecionada"""
        if self.peso_original_item and self.qtd_original_carteira:
            return (float(self.qtd_selecionada_usuario) / float(self.qtd_original_carteira)) * float(self.peso_original_item)
        return 0
        
    @property
    def percentual_selecionado(self):
        """Percentual selecionado do total"""
        if self.qtd_original_carteira:
            return (float(self.qtd_selecionada_usuario) / float(self.qtd_original_carteira)) * 100
        return 0
    
    # ===== MÉTODOS DE NEGÓCIO =====
    
    def gerar_hash_item(self, carteira_item):
        """Gera hash do item para detectar mudanças"""
        dados = f"{carteira_item.num_pedido}|{carteira_item.cod_produto}|{carteira_item.qtd_saldo_produto_pedido}|{carteira_item.preco_produto_pedido}"
        return hashlib.md5(dados.encode()).hexdigest()
    
    def validar_quantidades(self):
        """Valida se quantidades são consistentes"""
        if float(self.qtd_selecionada_usuario) > float(self.qtd_original_carteira):
            raise ValueError("Quantidade selecionada não pode ser maior que a original")
        
        if float(self.qtd_restante_calculada) != (float(self.qtd_original_carteira) - float(self.qtd_selecionada_usuario)):
            self.qtd_restante_calculada = float(self.qtd_original_carteira) - float(self.qtd_selecionada_usuario)
    
    def marcar_como_recomposto(self, usuario):
        """Marca item como recomposto após sincronização Odoo"""
        self.recomposto = True
        self.data_recomposicao = datetime.now(timezone.utc)
        self.recomposto_por = usuario
        self.status = 'RECOMPOSTO'
    
    def recompor_na_carteira(self, carteira_item, usuario):
        """Recompõe divisão na carteira após reimportação Odoo"""
        try:
            # Verificar se hash mudou (item foi alterado)
            novo_hash = self.gerar_hash_item(carteira_item)
            
            if self.hash_item_original != novo_hash:
                logger.warning(f"Item {self.num_pedido}-{self.cod_produto} foi alterado no Odoo")
            
            # NÃO criar linha de saldo - manter apenas uma linha por pedido/produto
            # O saldo disponível será calculado dinamicamente:
            # saldo_disponivel = qtd_carteira - soma(pre_separacoes) - soma(separacoes)
            
            # Aplicar dados editáveis preservados na pré-separação
            if self.data_expedicao_editada:
                # Dados ficam na pré-separação, não na carteira
                logger.info(f"Data expedição preservada na pré-separação: {self.data_expedicao_editada}")
            if self.data_agendamento_editada:
                logger.info(f"Data agendamento preservada na pré-separação: {self.data_agendamento_editada}")
            if self.protocolo_editado:
                logger.info(f"Protocolo preservado na pré-separação: {self.protocolo_editado}")
                    
            # Marcar como recomposto
            self.marcar_como_recomposto(usuario)
            
            logger.info(f"✅ Item {self.num_pedido}-{self.cod_produto} recomposto com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao recompor item {self.num_pedido}-{self.cod_produto}: {e}")
            return False
    
    # ===== MÉTODOS DE CLASSE (QUERIES) =====
    
    @classmethod
    def criar_pre_separacao(cls, carteira_item, qtd_selecionada, dados_editaveis, usuario, tipo_envio='total'):
        """Cria nova pré-separação"""
        
        # Calcular quantidades
        qtd_original = float(carteira_item.qtd_saldo_produto_pedido)
        qtd_selecionada = float(qtd_selecionada)
        qtd_restante = qtd_original - qtd_selecionada
        
        # Criar instância
        pre_separacao = cls(
            num_pedido=carteira_item.num_pedido,
            cod_produto=carteira_item.cod_produto,
            cnpj_cliente=carteira_item.cnpj_cliente,
            qtd_original_carteira=qtd_original,
            qtd_selecionada_usuario=qtd_selecionada,
            qtd_restante_calculada=qtd_restante,
            valor_original_item=carteira_item.preco_produto_pedido * qtd_original,
            peso_original_item=getattr(carteira_item, 'peso_total', 0),
            hash_item_original=cls().gerar_hash_item(carteira_item),
            data_expedicao_editada=dados_editaveis.get('data_expedicao'),
            data_agendamento_editada=dados_editaveis.get('data_agendamento'),
            protocolo_editado=dados_editaveis.get('protocolo'),
            observacoes_usuario=dados_editaveis.get('observacoes'),
            tipo_envio=tipo_envio,
            criado_por=usuario,
            status='CRIADO'
        )
        
        # Validar e salvar
        pre_separacao.validar_quantidades()
        db.session.add(pre_separacao)
        
        return pre_separacao
    
    @classmethod
    def buscar_nao_recompostas(cls):
        """Busca pré-separações que precisam ser recompostas após Odoo"""
        return cls.query.filter(cls.recomposto.is_(False)).all()
    
    @classmethod  
    def buscar_por_pedido(cls, num_pedido):
        """Busca pré-separações de um pedido específico"""
        return cls.query.filter(cls.num_pedido == num_pedido).all()
    
    @classmethod
    def recompor_todas_pendentes(cls, usuario):
        """Recompõe todas as pré-separações pendentes após reimportação Odoo"""
        from .models import CarteiraPrincipal
        
        pendentes = cls.buscar_nao_recompostas()
        sucesso = 0
        erro = 0
        
        for pre_sep in pendentes:
            # Buscar item na carteira atual
            carteira_item = CarteiraPrincipal.query.filter(
                and_(
                    CarteiraPrincipal.num_pedido == pre_sep.num_pedido,
                    CarteiraPrincipal.cod_produto == pre_sep.cod_produto,
                    CarteiraPrincipal.cnpj_cpf == pre_sep.cnpj_cliente  # Corrigido: cnpj_cpf ao invés de cnpj_cliente
                )
            ).first()
            
            if carteira_item:
                if pre_sep.recompor_na_carteira(carteira_item, usuario):
                    sucesso += 1
                else:
                    erro += 1
            else:
                logger.warning(f"Item {pre_sep.num_pedido}-{pre_sep.cod_produto} não encontrado na carteira atual")
                erro += 1
        
        db.session.commit()
        
        logger.info(f"✅ Recomposição concluída: {sucesso} sucessos, {erro} erros")
        return {'sucesso': sucesso, 'erro': erro, 'total': len(pendentes)}

    # ===== SISTEMA REAL DE PRÉ-SEPARAÇÃO (TABELA PRÓPRIA) =====
    
    @classmethod
    def criar_e_salvar(cls, carteira_item, qtd_selecionada, dados_editaveis, usuario, tipo_envio='total', config_parcial=None):
        """
        Cria e salva pré-separação na tabela real (pós-migração UTF-8)
        """
        try:
            # Calcular quantidades
            qtd_original = float(carteira_item.qtd_saldo_produto_pedido or 0)
            qtd_selecionada = float(qtd_selecionada)
            qtd_restante = qtd_original - qtd_selecionada
            
            # Criar instância
            pre_separacao = cls()
            pre_separacao.num_pedido = carteira_item.num_pedido
            pre_separacao.cod_produto = carteira_item.cod_produto
            pre_separacao.cnpj_cliente = carteira_item.cnpj_cpf
            pre_separacao.nome_produto = carteira_item.nome_produto
            pre_separacao.qtd_original_carteira = qtd_original
            pre_separacao.qtd_selecionada_usuario = qtd_selecionada
            pre_separacao.qtd_restante_calculada = qtd_restante
            pre_separacao.valor_original_item = float(carteira_item.preco_produto_pedido or 0) * qtd_original
            pre_separacao.peso_original_item = float(getattr(carteira_item, 'peso', 0) or 0)
            pre_separacao.hash_item_original = cls._gerar_hash_item(carteira_item)
            pre_separacao.data_expedicao_editada = dados_editaveis.get('expedicao')
            pre_separacao.data_agendamento_editada = dados_editaveis.get('agendamento')
            pre_separacao.protocolo_editado = dados_editaveis.get('protocolo')
            pre_separacao.observacoes_usuario = dados_editaveis.get('observacoes')
            pre_separacao.tipo_envio = tipo_envio
            pre_separacao.criado_por = usuario
            pre_separacao.status = 'CRIADO'
            
            # Adicionar configuração de envio parcial se necessário
            if tipo_envio == 'parcial' and config_parcial:
                observacoes_parcial = f"ENVIO PARCIAL - Motivo: {config_parcial.get('motivo', 'N/A')} | " \
                                     f"Justificativa: {config_parcial.get('justificativa', 'N/A')} | " \
                                     f"Previsão Complemento: {config_parcial.get('previsao_complemento', 'N/A')} | " \
                                     f"Responsável: {config_parcial.get('responsavel_aprovacao', 'N/A')}"
                
                if pre_separacao.observacoes_usuario:
                    pre_separacao.observacoes_usuario += f"\n{observacoes_parcial}"
                else:
                    pre_separacao.observacoes_usuario = observacoes_parcial
            
            # Validar e salvar
            pre_separacao.validar_quantidades()
            db.session.add(pre_separacao)
            db.session.commit()
            
            logger.info(f"✅ Pré-separação criada com sucesso: {pre_separacao.num_pedido}-{pre_separacao.cod_produto}")
            return pre_separacao
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar pré-separação: {e}")
            db.session.rollback()
            raise
    
    @classmethod
    def _gerar_hash_item(cls, carteira_item):
        """Gera hash do item para detectar mudanças"""
        dados = f"{carteira_item.num_pedido}|{carteira_item.cod_produto}|{carteira_item.qtd_saldo_produto_pedido}|{carteira_item.preco_produto_pedido}"
        return hashlib.md5(dados.encode()).hexdigest()
    
    @classmethod
    def buscar_por_pedido_produto(cls, num_pedido, cod_produto=None):
        """Busca pré-separações de um pedido específico"""
        query = cls.query.filter(cls.num_pedido == num_pedido)
        if cod_produto:
            query = query.filter(cls.cod_produto == cod_produto)
        return query.all()
    

    # ===== SISTEMA PÓS-SINCRONIZAÇÃO ODOO =====
    
    @classmethod
    def aplicar_reducao_quantidade(cls, num_pedido, cod_produto, qtd_reduzida, motivo="SYNC_ODOO"):
        """
        Aplica redução de quantidade seguindo hierarquia de impacto
        1º SALDO LIVRE → 2º PRÉ-SEPARAÇÃO → 3º SEPARAÇÃO ABERTO → 4º SEPARAÇÃO COTADO
        """
        try:
            qtd_restante = float(qtd_reduzida)
            log_operacoes = []
            
            # 1º Consumir do saldo livre primeiro (CarteiraPrincipal sem separação)
            carteira_item = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.separacao_lote_id.is_(None)
            ).first()
            
            if carteira_item and carteira_item.qtd_saldo_produto_pedido and qtd_restante > 0:
                qtd_consumida_saldo = min(float(carteira_item.qtd_saldo_produto_pedido), qtd_restante)
                # Converter para Decimal antes de subtrair para evitar erro de tipo
                carteira_item.qtd_saldo_produto_pedido = Decimal(str(float(carteira_item.qtd_saldo_produto_pedido) - qtd_consumida_saldo))
                qtd_restante -= qtd_consumida_saldo
                log_operacoes.append(f"Saldo livre reduzido em {qtd_consumida_saldo}")
            
            # 2º Consumir de pré-separações (mais recentes primeiro)
            if qtd_restante > 0:
                pre_separacoes = cls.query.filter(
                    cls.num_pedido == num_pedido,
                    cls.cod_produto == cod_produto,
                    cls.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).order_by(cls.data_criacao.desc()).all()
                
                for pre_sep in pre_separacoes:
                    if qtd_restante <= 0:
                        break
                    
                    qtd_consumida_pre = min(float(pre_sep.qtd_selecionada_usuario), qtd_restante)
                    # Converter para Decimal antes de subtrair
                    pre_sep.qtd_selecionada_usuario = Decimal(str(float(pre_sep.qtd_selecionada_usuario) - qtd_consumida_pre))
                    qtd_restante -= qtd_consumida_pre
                    log_operacoes.append(f"Pré-separação ID:{pre_sep.id} reduzida em {qtd_consumida_pre}")
                    
                    # Marcar para exclusão se zerou
                    if pre_sep.qtd_selecionada_usuario <= 0:
                        db.session.delete(pre_sep)
                        log_operacoes.append(f"Pré-separação ID:{pre_sep.id} removida (zerada)")
            
            # 3º Consumir de separações ABERTO
            if qtd_restante > 0:
                try:
                    from app.separacao.models import Separacao
                    from app.pedidos.models import Pedido
                    # CORRIGIDO: Separacao não tem campo 'status', usar Pedido.status via JOIN
                    separacoes_aberto = db.session.query(Separacao).join(
                        Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                    ).filter(
                        Separacao.num_pedido == num_pedido,
                        Separacao.cod_produto == cod_produto,
                        Pedido.status == 'ABERTO'
                    ).all()
                    
                    for separacao in separacoes_aberto:
                        if qtd_restante <= 0:
                            break
                        
                        qtd_consumida_sep = min(float(separacao.qtd_saldo or 0), qtd_restante)
                        # Converter para Decimal antes de subtrair
                        separacao.qtd_saldo = Decimal(str(float(separacao.qtd_saldo or 0) - qtd_consumida_sep))
                        qtd_restante -= qtd_consumida_sep
                        log_operacoes.append(f"Separação ABERTO {separacao.separacao_lote_id} reduzida em {qtd_consumida_sep}")
                        
                except ImportError:
                    log_operacoes.append("AVISO: Módulo separação não disponível")
            
            # 4º ÚLTIMO RECURSO: Separações COTADO (gerar alerta crítico)
            if qtd_restante > 0:
                try:
                    from app.separacao.models import Separacao
                    from app.pedidos.models import Pedido
                    # CORRIGIDO: Separacao não tem campo 'status', usar Pedido.status via JOIN
                    separacoes_cotado = db.session.query(Separacao).join(
                        Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                    ).filter(
                        Separacao.num_pedido == num_pedido,
                        Separacao.cod_produto == cod_produto,
                        Pedido.status == 'COTADO'
                    ).all()
                    
                    if separacoes_cotado:
                        # GERAR ALERTA CRÍTICO
                        cls._gerar_alerta_separacao_cotada_afetada(
                            num_pedido, cod_produto, qtd_restante, separacoes_cotado, motivo
                        )
                        
                        # Aplicar redução mesmo com alerta
                        for separacao in separacoes_cotado:
                            if qtd_restante <= 0:
                                break
                            
                            qtd_consumida_cotado = min(float(separacao.qtd_saldo or 0), qtd_restante)
                            # Converter para Decimal antes de subtrair
                            separacao.qtd_saldo = Decimal(str(float(separacao.qtd_saldo or 0) - qtd_consumida_cotado))
                            qtd_restante -= qtd_consumida_cotado
                            log_operacoes.append(f"🚨 CRÍTICO: Separação COTADA {separacao.separacao_lote_id} reduzida em {qtd_consumida_cotado}")
                            
                except ImportError:
                    log_operacoes.append("ERRO: Não foi possível acessar separações COTADO")
            
            db.session.commit()
            
            resultado = {
                'sucesso': True,
                'qtd_reduzida_total': float(qtd_reduzida) - qtd_restante,
                'qtd_nao_aplicada': qtd_restante,
                'operacoes': log_operacoes
            }
            
            logger.info(f"✅ Redução aplicada: {num_pedido}-{cod_produto} | {resultado}")
            return resultado
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao aplicar redução: {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    @classmethod
    def aplicar_aumento_quantidade(cls, num_pedido, cod_produto, qtd_aumentada, motivo="SYNC_ODOO"):
        """
        Aplica aumento de quantidade seguindo lógica de tipo_envio
        TOTAL = atualiza registro único | PARCIAL = cria saldo livre
        """
        try:
            # 1º Detectar tipo atual do pedido
            tipo_envio_atual = cls.detectar_tipo_envio_automatico(num_pedido, cod_produto)
            
            if tipo_envio_atual == 'total':
                # PEDIDO TOTAL: Atualizar registro único
                pre_sep_unica = cls.query.filter(
                    cls.num_pedido == num_pedido,
                    cls.cod_produto == cod_produto,
                    cls.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).first()
                
                if pre_sep_unica:
                    # ATUALIZAR pré-separação única
                    # Converter para Decimal antes de somar
                    pre_sep_unica.qtd_selecionada_usuario = Decimal(str(float(pre_sep_unica.qtd_selecionada_usuario) + float(qtd_aumentada)))
                    db.session.commit()
                    
                    logger.info(f"✅ Pré-separação TOTAL atualizada: {pre_sep_unica.id} +{qtd_aumentada}")
                    return {
                        'acao': 'ATUALIZACAO_PRE_SEPARACAO_TOTAL',
                        'pre_separacao_id': pre_sep_unica.id,
                        'nova_qtd': float(pre_sep_unica.qtd_selecionada_usuario)
                    }
                
                # Verificar separação única
                try:
                    from app.separacao.models import Separacao
                    separacao_unica = Separacao.query.filter(
                        Separacao.num_pedido == num_pedido,
                        Separacao.cod_produto == cod_produto
                    ).first()
                    
                    if separacao_unica:
                        # ATUALIZAR separação única
                        separacao_unica.qtd_saldo += float(qtd_aumentada)
                        db.session.commit()
                        
                        logger.info(f"✅ Separação TOTAL atualizada: {separacao_unica.separacao_lote_id} +{qtd_aumentada}")
                        return {
                            'acao': 'ATUALIZACAO_SEPARACAO_TOTAL',
                            'separacao_lote_id': separacao_unica.separacao_lote_id,
                            'nova_qtd': float(separacao_unica.qtd_saldo)
                        }
                except ImportError:
                    pass
            
            # PARCIAL ou SEM PROGRAMAÇÃO: Criar saldo livre na carteira
            carteira_item = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.cod_produto == cod_produto
            ).first()
            
            if carteira_item:
                # Converter para Decimal antes de somar
                carteira_item.qtd_saldo_produto_pedido = Decimal(str(float(carteira_item.qtd_saldo_produto_pedido) + float(qtd_aumentada)))
                db.session.commit()
                
                logger.info(f"✅ Saldo livre criado: {num_pedido}-{cod_produto} +{qtd_aumentada}")
                return {
                    'acao': 'SALDO_LIVRE_CRIADO',
                    'qtd_disponivel': float(qtd_aumentada),
                    'motivo': f'Pedido tipo {tipo_envio_atual or "sem programação"} - quantidade fica disponível'
                }
            
            logger.warning(f"⚠️ Item não encontrado na carteira: {num_pedido}-{cod_produto}")
            return {'acao': 'ITEM_NAO_ENCONTRADO', 'qtd_perdida': float(qtd_aumentada)}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao aplicar aumento: {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    @classmethod
    def detectar_tipo_envio_automatico(cls, num_pedido, cod_produto=None):
        """
        Detecta automaticamente se envio é total ou parcial
        TOTAL = 1 registro único | PARCIAL = múltiplos registros
        """
        try:
            # Verificar pré-separações do pedido/produto
            query_pre = cls.query.filter(
                cls.num_pedido == num_pedido,
                cls.status.in_(['CRIADO', 'RECOMPOSTO'])
            )
            if cod_produto:
                query_pre = query_pre.filter(cls.cod_produto == cod_produto)
            
            total_pre_separacoes = query_pre.count()
            
            # Verificar separações do pedido/produto
            total_separacoes = 0
            try:
                from app.separacao.models import Separacao
                query_sep = Separacao.query.filter(
                    Separacao.num_pedido == num_pedido
                )
                if cod_produto:
                    query_sep = query_sep.filter(Separacao.cod_produto == cod_produto)
                
                total_separacoes = query_sep.count()
            except ImportError:
                pass
            
            # REGRA: TOTAL = 1 único registro | PARCIAL = múltiplos registros
            if (total_pre_separacoes == 1 and total_separacoes == 0) or \
               (total_pre_separacoes == 0 and total_separacoes == 1):
                return 'total'
            elif (total_pre_separacoes > 1) or (total_separacoes > 1) or \
                 (total_pre_separacoes >= 1 and total_separacoes >= 1):
                return 'parcial'
            else:
                return None  # Sem programação
                
        except Exception as e:
            logger.error(f"❌ Erro ao detectar tipo envio: {e}")
            return None
    
    @classmethod
    def _gerar_alerta_separacao_cotada_afetada(cls, num_pedido, cod_produto, qtd_afetada, separacoes, motivo):
        """Gera alerta crítico quando separação COTADA é afetada"""
        try:
            alerta = {
                'nivel': 'CRITICO',
                'tipo': 'SEPARACAO_COTADA_ALTERADA',
                'pedido': num_pedido,
                'produto': cod_produto,
                'quantidade_afetada': qtd_afetada,
                'motivo': motivo,
                'separacoes_afetadas': [s.separacao_lote_id for s in separacoes],
                'timestamp': datetime.now(timezone.utc),
                'mensagem': f'🚨 URGENTE: {len(separacoes)} separação(ões) COTADA(s) afetada(s) por {motivo}',
                'acao_requerida': 'Verificar impacto no processo físico imediatamente'
            }
            
            logger.critical(f"🚨 ALERTA CRÍTICO: {alerta}")
            
            # TODO: Implementar sistema de notificações (email, webhook, etc.)
            # TODO: Salvar alerta em tabela de auditoria
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar alerta: {e}")


class CadastroCliente(db.Model):
    """
    Modelo para cadastro de clientes não-Odoo
    Utilizado para complementar informações na importação de pedidos não-Odoo
    """
    __tablename__ = 'cadastro_cliente'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Chave principal - CNPJ/CPF
    cnpj_cpf = db.Column(db.String(20), nullable=False, unique=True, index=True)
    
    # Dados básicos do cliente
    raz_social = db.Column(db.String(255), nullable=False)  # Razão social
    raz_social_red = db.Column(db.String(100), nullable=True)  # Nome fantasia
    
    # Localização
    municipio = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    
    # Dados comerciais
    vendedor = db.Column(db.String(100), nullable=True)
    equipe_vendas = db.Column(db.String(100), nullable=True)
    
    # Endereço de entrega padrão
    cnpj_endereco_ent = db.Column(db.String(20), nullable=True)
    empresa_endereco_ent = db.Column(db.String(255), nullable=True)  # Nome fantasia do endereço
    cep_endereco_ent = db.Column(db.String(10), nullable=True)
    nome_cidade = db.Column(db.String(100), nullable=True)
    cod_uf = db.Column(db.String(2), nullable=True)
    bairro_endereco_ent = db.Column(db.String(100), nullable=True)
    rua_endereco_ent = db.Column(db.String(255), nullable=True)
    endereco_ent = db.Column(db.String(20), nullable=True)  # Número
    telefone_endereco_ent = db.Column(db.String(50), nullable=True)
    
    # Flags de controle
    endereco_mesmo_cliente = db.Column(db.Boolean, default=True)  # Se endereço de entrega é o mesmo do cliente
    cliente_ativo = db.Column(db.Boolean, default=True)
    
    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    atualizado_por = db.Column(db.String(100), nullable=True)
    
    # Índices
    __table_args__ = (
        Index('idx_cadastro_cliente_vendedor', 'vendedor'),
        Index('idx_cadastro_cliente_equipe', 'equipe_vendas'),
        Index('idx_cadastro_cliente_municipio', 'municipio', 'estado'),
    )
    
    def __repr__(self):
        return f'<CadastroCliente {self.cnpj_cpf} - {self.raz_social_red or self.raz_social}>'
    
    def to_dict(self):
        """Converte para dicionário para APIs"""
        return {
            'id': self.id,
            'cnpj_cpf': self.cnpj_cpf,
            'raz_social': self.raz_social,
            'raz_social_red': self.raz_social_red,
            'municipio': self.municipio,
            'estado': self.estado,
            'vendedor': self.vendedor,
            'equipe_vendas': self.equipe_vendas,
            'cnpj_endereco_ent': self.cnpj_endereco_ent,
            'empresa_endereco_ent': self.empresa_endereco_ent,
            'cep_endereco_ent': self.cep_endereco_ent,
            'nome_cidade': self.nome_cidade,
            'cod_uf': self.cod_uf,
            'bairro_endereco_ent': self.bairro_endereco_ent,
            'rua_endereco_ent': self.rua_endereco_ent,
            'endereco_ent': self.endereco_ent,
            'telefone_endereco_ent': self.telefone_endereco_ent,
            'endereco_mesmo_cliente': self.endereco_mesmo_cliente,
            'cliente_ativo': self.cliente_ativo
        }
    
    @staticmethod
    def limpar_cnpj(cnpj):
        """Remove formatação do CNPJ/CPF"""
        if not cnpj:
            return None
        return ''.join(filter(str.isdigit, str(cnpj)))
    
    @staticmethod
    def formatar_cnpj(cnpj):
        """Formata CNPJ/CPF com máscara"""
        cnpj = CadastroCliente.limpar_cnpj(cnpj)
        if not cnpj:
            return None
            
        # CNPJ: 14 dígitos
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        # CPF: 11 dígitos
        elif len(cnpj) == 11:
            return f"{cnpj[:3]}.{cnpj[3:6]}.{cnpj[6:9]}-{cnpj[9:]}"
        else:
            return cnpj
    
    def aplicar_endereco_cliente(self):
        """Aplica endereço do cliente como endereço de entrega"""
        self.cnpj_endereco_ent = self.cnpj_cpf
        self.empresa_endereco_ent = self.raz_social_red or self.raz_social
        self.nome_cidade = self.municipio
        self.cod_uf = self.estado
        self.endereco_mesmo_cliente = True
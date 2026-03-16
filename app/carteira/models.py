
from app import db
from app.utils.timezone import agora_utc_naive
from sqlalchemy import Index, func
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

    # 💰 IMPOSTOS DA LINHA (Odoo sale.order.line)
    icms_valor = db.Column(db.Numeric(15, 2), nullable=True)  # l10n_br_icms_valor
    icmsst_valor = db.Column(db.Numeric(15, 2), nullable=True)  # l10n_br_icmsst_valor
    pis_valor = db.Column(db.Numeric(15, 2), nullable=True)  # l10n_br_pis_valor
    cofins_valor = db.Column(db.Numeric(15, 2), nullable=True)  # l10n_br_cofins_valor

    # 🏷️ DESCONTO CONTRATUAL (Odoo res.partner)
    desconto_contratual = db.Column(db.Boolean, default=False, nullable=True)  # x_studio_desconto_contratual
    desconto_percentual = db.Column(db.Numeric(5, 2), nullable=True)  # x_studio_desconto (%)

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
    
    # 📅 DADOS OPERACIONAIS
    # NOTA: Campos de agendamento/expedição/carga estão em Separacao (fonte única da verdade)
    # CarteiraPrincipal contém apenas dados do pedido original do Odoo
    forma_agendamento = db.Column(db.String(50), nullable=True)  # Portal, Telefone, E-mail, WhatsApp, ODOO, SEM AGENDAMENTO

    # 🔄 SINCRONIZAÇÃO INCREMENTAL
    odoo_write_date = db.Column(db.DateTime, nullable=True, index=True)  # write_date do Odoo
    ultima_sync = db.Column(db.DateTime, nullable=True)  # momento da última sincronização

    # 🗑️ CONTROLE DE EXCLUSÃO
    motivo_exclusao = db.Column(db.Text, nullable=True)  # Motivo do cancelamento/exclusão da separação

    # ⭐ MARCADOR DE IMPORTÂNCIA
    importante = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Marcador de pedido importante

    # 🏷️ TAGS DO PEDIDO (ODOO)
    tags_pedido = db.Column(db.Text, nullable=True)  # JSON com tags do pedido: [{"name": "VIP", "color": 5}]

    # 💰 SNAPSHOT DE CUSTO (gravado na importacao do Odoo)
    # Preserva o custo considerado no momento da criacao do item
    custo_unitario_snapshot = db.Column(db.Numeric(15, 6), nullable=True)
    custo_tipo_snapshot = db.Column(db.String(20), nullable=True)  # MEDIO_MES, ULTIMO_CUSTO, MEDIO_ESTOQUE, BOM
    custo_vigencia_snapshot = db.Column(db.DateTime, nullable=True)  # Data do custo usado
    custo_producao_snapshot = db.Column(db.Numeric(15, 6), nullable=True)  # Custo adicional de producao

    # 📊 MARGENS CALCULADAS
    margem_bruta = db.Column(db.Numeric(15, 2), nullable=True)
    margem_bruta_percentual = db.Column(db.Numeric(7, 2), nullable=True)  # Suporta até ±99999.99%
    margem_liquida = db.Column(db.Numeric(15, 2), nullable=True)
    margem_liquida_percentual = db.Column(db.Numeric(7, 2), nullable=True)  # Suporta até ±99999.99%
    comissao_percentual = db.Column(db.Numeric(5, 2), nullable=True, default=0)  # Soma das regras de comissao

    # 📸 SNAPSHOT DE PARAMETROS (rastreabilidade do calculo de margem)
    frete_percentual_snapshot = db.Column(db.Numeric(5, 2), nullable=True)  # % Frete usado
    custo_financeiro_pct_snapshot = db.Column(db.Numeric(5, 2), nullable=True)  # % Custo financeiro
    custo_operacao_pct_snapshot = db.Column(db.Numeric(5, 2), nullable=True)  # % Custo operacao
    percentual_perda_snapshot = db.Column(db.Numeric(5, 2), nullable=True)  # % Perda

    # 🛡️ AUDITORIA
    created_at = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
    
    # 📊 ÍNDICES COMPOSTOS PARA PERFORMANCE
    __table_args__ = (
        # Chave única de negócio
        db.UniqueConstraint('num_pedido', 'cod_produto', name='uq_carteira_pedido_produto'),
        # Índices de consulta
        Index('idx_carteira_cliente_vendedor', 'cnpj_cpf', 'vendedor'),
        Index('idx_carteira_status_data', 'status_pedido', 'data_pedido'),
        Index('idx_carteira_produto_saldo', 'cod_produto', 'qtd_saldo_produto_pedido'),
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
            'data_pedido': self.data_pedido.strftime('%d/%m/%Y') if self.data_pedido else None,
            'forma_agendamento': self.forma_agendamento
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
    # IMPORTANTE: Campo físico no banco, NÃO deve ser atualizado manualmente
    # Use a property baixa_produto_pedido (calculada dinamicamente do FaturamentoProduto)
    _baixa_produto_pedido_old = db.Column('baixa_produto_pedido', db.Numeric(15, 3), default=0, nullable=False)
    qtd_saldo_produto_calculado = db.Column(db.Numeric(15, 3), nullable=False)  # Calculado: qtd - cancelado - baixa
    
    # 🛡️ AUDITORIA
    created_at = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive, nullable=False)
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
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    conferido_em = db.Column(db.DateTime, nullable=True)
    
    # 📊 ÍNDICES
    __table_args__ = (
        Index('idx_controle_separacao_lote_pedido', 'separacao_lote_id', 'num_pedido'),
        Index('idx_controle_status_diferenca', 'status_controle', 'diferenca_detectada'),
    )

    def __repr__(self):
        return f'<ControleCruzado Lote:{self.separacao_lote_id} {self.num_pedido}-{self.cod_produto} Dif:{self.diferenca_detectada}>'

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
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    
    # 🔗 RELACIONAMENTO COM COMPLEMENTARES
    carga_principal_id = db.Column(db.Integer, db.ForeignKey('tipo_carga.id'), nullable=True)
    # Para cargas COMPLEMENTAR, aponta para a PARCIAL original
    
    def __repr__(self):
        return f'<FlexibilidadeCarga {self.separacao_lote_id} - {self.tipo_envio}>'
    
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
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
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
    data_pedido = db.Column(db.Date, nullable=True)
    
    # 🎯 TIPO DE STANDBY
    tipo_standby = db.Column(db.String(50), nullable=False, index=True)
    # Saldo: Aguarda complemento de saldo
    # Aguardar Comercial: Aguarda decisão comercial
    # Aguardar PCP: Aguarda planejamento e controle de produção
    
    # 📅 CONTROLE TEMPORAL
    data_limite_standby = db.Column(db.Date, nullable=True)  # Prazo máximo em standby
    dias_em_standby = db.Column(db.Integer, default=0)       # Contador automático
    
    # 🔔 ALERTAS E NOTIFICAÇÕES
    alertas_enviados = db.Column(db.Integer, default=0)
    proximo_alerta = db.Column(db.Date, nullable=True)
    
    # 🎯 RESOLUÇÃO
    status_standby = db.Column(db.String(20), default='ATIVO', index=True)
    # ATIVO: Em standby aguardando
    # BLOQ. COML.: Bloqueado pelo comercial
    # SALDO: Aguardando saldo
    # CONFIRMADO: Confirmado pelo comercial, retorna para carteira
    
    resolucao_final = db.Column(db.String(20), nullable=True)
    data_resolucao = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    observacoes_resolucao = db.Column(db.Text, nullable=True)
    
    # 📝 OBSERVAÇÕES CUMULATIVAS
    observacoes = db.Column(db.Text, nullable=True)  # JSON com histórico de observações
    
    # 🛡️ AUDITORIA
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f'<SaldoStandby {self.num_pedido} {self.cod_produto} - {self.qtd_saldo} - {self.tipo_standby}>'
    
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
    agendamento_confirmado = db.Column(db.Boolean, default=False)  # Flag para confirmação de agendamento
    protocolo_editado = db.Column(db.String(50))
    observacoes_usuario = db.Column(db.Text)
    
    # Controle de recomposição (sobrevivência ao Odoo)
    # ATENÇÃO: Campo praticamente INÚTIL! (Análise completa em 08/08/2025)
    # - Durante sincronização: Reseta para False → verifica hash → marca como True
    # - NÃO afeta ajustes de quantidade (feitos por aplicar_reducao/aumento_quantidade)
    # - NÃO modifica carteira, NÃO reaplica divisões, NÃO age sobre mudanças detectadas
    # - É apenas um ciclo decorativo: detecta mudanças via hash mas só gera logs
    # - Para movimentações previstas: IGNORAR completamente este campo
    # - Ver: FLUXO_COMPLETO_SINCRONIZACAO.md para análise detalhada
    recomposto = db.Column(db.Boolean, default=False, index=True)
    data_recomposicao = db.Column(db.DateTime)
    recomposto_por = db.Column(db.String(100))
    versao_carteira_original = db.Column(db.String(50))
    versao_carteira_recomposta = db.Column(db.String(50))
    
    # Status e tipo
    status = db.Column(db.String(20), default='CRIADO', index=True)  # CRIADO, RECOMPOSTO, ENVIADO_SEPARACAO
    tipo_envio = db.Column(db.String(10), default='total')  # total, parcial
    
    # Auditoria
    data_criacao = db.Column(db.DateTime, default=agora_utc_naive)
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
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive, nullable=False)
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


# ============================================================================
# ATIVAÇÃO DO ADAPTER PreSeparacaoItem → Separacao
# Data: 2025-01-29
# 
# IMPORTANTE: Este adapter faz PreSeparacaoItem funcionar usando Separacao
# com status='PREVISAO'. Isso permite migração gradual sem quebrar o código.
#
# Para DESATIVAR: Remova este bloco de código
# ============================================================================

try:
    from app.carteira.models_adapter_presep import PreSeparacaoItemAdapter
    
    # Substituir a classe PreSeparacaoItem pelo adapter
    PreSeparacaoItem = PreSeparacaoItemAdapter
    PreSeparacaoItem.query = PreSeparacaoItemAdapter.query_adapter()
    
    print("⚠️ ADAPTER ATIVO: PreSeparacaoItem está usando Separacao com status='PREVISAO'")
except ImportError as e:
    print(f"⚠️ Adapter não pôde ser carregado: {e}")
    # Mantém a classe original se o adapter não estiver disponível
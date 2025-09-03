from app import db  # ou de onde você estiver importando seu `db`
from datetime import datetime

# models.py
class Separacao(db.Model):
    __tablename__ = 'separacao'

    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação
    num_pedido = db.Column(db.String(50), nullable=True)
    data_pedido = db.Column(db.Date, nullable=True)  # agora pode ser nulo
    cnpj_cpf = db.Column(db.String(20), nullable=True)
    raz_social_red = db.Column(db.String(255), nullable=True)
    nome_cidade = db.Column(db.String(100), nullable=True)
    cod_uf = db.Column(db.String(2), nullable=False)
    cod_produto = db.Column(db.String(50), nullable=True)
    nome_produto = db.Column(db.String(255), nullable=True)

    qtd_saldo = db.Column(db.Float, nullable=True)  # agora pode ser nulo
    valor_saldo = db.Column(db.Float, nullable=True)
    pallet = db.Column(db.Float, nullable=True)
    peso = db.Column(db.Float, nullable=True)

    rota = db.Column(db.String(50), nullable=True)
    sub_rota = db.Column(db.String(50), nullable=True)
    observ_ped_1 = db.Column(db.String(700), nullable=True)
    roteirizacao = db.Column(db.String(255), nullable=True)
    expedicao = db.Column(db.Date, nullable=True)
    agendamento = db.Column(db.Date, nullable=True)
    agendamento_confirmado = db.Column(db.Boolean, default=False)  # Flag para confirmação de agendamento
    protocolo = db.Column(db.String(50), nullable=True)
    pedido_cliente = db.Column(db.String(100), nullable=True)  # 🆕 Pedido de Compra do Cliente
    
    # 🎯 ETAPA 2: CAMPO TIPO DE ENVIO (ADICIONADO NA MIGRAÇÃO)
    tipo_envio = db.Column(db.String(10), default='total', nullable=True)  # total, parcial
    
    # 🔄 CAMPOS DE CONTROLE DE SINCRONIZAÇÃO (FASE 3)
    sincronizado_nf = db.Column(db.Boolean, default=False, nullable=True)  # Indica se foi sincronizado com NF, gatilho principal para projetar saidas de estoque
    numero_nf = db.Column(db.String(20), nullable=True)  # NF associada quando sincronizada
    data_sincronizacao = db.Column(db.DateTime, nullable=True)  # Data/hora da sincronização
    zerado_por_sync = db.Column(db.Boolean, default=False, nullable=True)  # Indica se foi zerado por sincronização
    data_zeragem = db.Column(db.DateTime, nullable=True)  # Data/hora quando foi zerado
    
    # 🆕 NOVOS CAMPOS PARA SUBSTITUIR PEDIDO E PRESEPARACAOITEM
    status = db.Column(db.String(20), default='ABERTO', nullable=False, index=True)  # PREVISAO, ABERTO, FATURADO
    nf_cd = db.Column(db.Boolean, default=False, nullable=False)  # NF voltou para o CD
    data_embarque = db.Column(db.Date, nullable=True)  # Data de embarque
    
    # Campos de normalização (para cotação e agrupamento)
    cidade_normalizada = db.Column(db.String(120), nullable=True)
    uf_normalizada = db.Column(db.String(2), nullable=True)
    codigo_ibge = db.Column(db.String(10), nullable=True)
    
    # Controle de impressão
    separacao_impressa = db.Column(db.Boolean, default=False, nullable=False)
    separacao_impressa_em = db.Column(db.DateTime, nullable=True)
    separacao_impressa_por = db.Column(db.String(100), nullable=True)
    
    # Relacionamento com cotação (para manter compatibilidade com Pedido)
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'), nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índices compostos para performance (ordem correta: mais seletivo primeiro)
    __table_args__ = (
        # Índices principais
        db.Index('idx_sep_lote_sync', 'separacao_lote_id', 'sincronizado_nf'),
        db.Index('idx_sep_lote_status', 'separacao_lote_id', 'status'),
        db.Index('idx_sep_num_pedido', 'num_pedido'),
        db.Index('idx_sep_pedido_sync', 'num_pedido', 'sincronizado_nf'),
        
        # NOVOS ÍNDICES OTIMIZADOS para workspace_api.py
        db.Index('idx_sep_pedido_produto_sync', 'num_pedido', 'cod_produto', 'sincronizado_nf'),
        db.Index('idx_sep_produto_qtd_sync', 'cod_produto', 'qtd_saldo'),
        
        # Índices para estoque projetado
        db.Index('idx_sep_estoque_projetado', 'cod_produto', 'expedicao'),
        db.Index('idx_sep_expedicao_produto', 'expedicao', 'cod_produto'),
        
        # Índices simples
        db.Index('idx_sep_status', 'status'),
        db.Index('idx_sep_nf', 'numero_nf', 'sincronizado_nf'),
        db.Index('idx_sep_cnpj', 'cnpj_cpf', 'sincronizado_nf'),
        db.Index('idx_sep_expedicao', 'expedicao', 'sincronizado_nf'),
        db.Index('idx_sep_cotacao', 'cotacao_id'),
    )

    def __repr__(self):
        return f'<Separacao #{self.id} - {self.num_pedido} - Lote: {self.separacao_lote_id} - Tipo: {self.tipo_envio}>'

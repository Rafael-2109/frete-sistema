from app import db
from app.utils.timezone import agora_utc_naive

class Cotacao(db.Model):
    """
    Modelo para armazenar as cotações de frete
    """
    __tablename__ = 'cotacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Em Aberto')
    data_criacao = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    data_fechamento = db.Column(db.DateTime)
    tipo_carga = db.Column(db.String(20), nullable=False)  # DIRETA ou FRACIONADA
    valor_total = db.Column(db.Float, nullable=False)
    peso_total = db.Column(db.Float, nullable=False)
    
    # Parâmetros da tabela de frete (apenas para carga DIRETA)
    modalidade = db.Column(db.String(50))  # VALOR, PESO, VAN, etc.
    nome_tabela = db.Column(db.String(100))
    valor_kg = db.Column(db.Float)
    percentual_valor = db.Column(db.Float)
    frete_minimo_valor = db.Column(db.Float)
    frete_minimo_peso = db.Column(db.Float)
    icms = db.Column(db.Float)
    percentual_gris = db.Column(db.Float)
    pedagio_por_100kg = db.Column(db.Float)
    valor_tas = db.Column(db.Float)
    percentual_adv = db.Column(db.Float)
    percentual_rca = db.Column(db.Float)
    valor_despacho = db.Column(db.Float)
    valor_cte = db.Column(db.Float)
    icms_incluso = db.Column(db.Boolean, default=False)
    icms_destino = db.Column(db.Float)  # ICMS da cidade de destino
    
    # ===== NOVOS CAMPOS DE VALORES MÍNIMOS E ICMS =====
    gris_minimo = db.Column(db.Float, default=0)    # Valor mínimo de GRIS
    adv_minimo = db.Column(db.Float, default=0)     # Valor mínimo de ADV
    icms_proprio = db.Column(db.Float, nullable=True)  # ICMS próprio da tabela
    
    # Relacionamentos
    usuario = db.relationship('Usuario', backref='cotacoes')
    transportadora = db.relationship('Transportadora', backref='cotacoes')
    itens = db.relationship('CotacaoItem', backref='cotacao', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Cotacao {self.id}>'

class CotacaoItem(db.Model):
    """
    Modelo para armazenar os itens de uma cotação.
    Para cargas FRACIONADAS, cada item representa um pedido.
    """
    __tablename__ = 'cotacao_itens'

    id = db.Column(db.Integer, primary_key=True)
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'), nullable=False)
    
    # Migrado para usar separacao_lote_id ao invés de pedido_id
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # Novo campo principal
    pedido_id_old = db.Column(db.Integer, nullable=True)  # Antigo pedido_id mantido como backup
    
    cnpj_cliente = db.Column(db.String(20), nullable=False)
    cliente = db.Column(db.String(100), nullable=False)
    peso = db.Column(db.Float, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    

    # Parâmetros da tabela de frete
    modalidade = db.Column(db.String(20))
    nome_tabela = db.Column(db.String(100))
    valor_kg = db.Column(db.Float)
    percentual_valor = db.Column(db.Float)
    frete_minimo_valor = db.Column(db.Float)
    frete_minimo_peso = db.Column(db.Float)
    icms = db.Column(db.Float)
    percentual_gris = db.Column(db.Float)
    pedagio_por_100kg = db.Column(db.Float)
    valor_tas = db.Column(db.Float)
    percentual_adv = db.Column(db.Float)
    percentual_rca = db.Column(db.Float)
    valor_despacho = db.Column(db.Float)
    valor_cte = db.Column(db.Float)
    icms_incluso = db.Column(db.Boolean, default=False)
    icms_destino = db.Column(db.Float)
    
    # ===== NOVOS CAMPOS DE VALORES MÍNIMOS E ICMS =====
    gris_minimo = db.Column(db.Float, default=0)    # Valor mínimo de GRIS
    adv_minimo = db.Column(db.Float, default=0)     # Valor mínimo de ADV
    icms_proprio = db.Column(db.Float, nullable=True)  # ICMS próprio da tabela

    # Relacionamentos
    # Removido: relacionamento com Pedido (agora é VIEW, não tem FK)
    # pedido = db.relationship('Pedido', backref=db.backref('cotacao_item', lazy=True))
    
    @property
    def separacoes(self):
        """Retorna todas as separações deste lote"""
        from app.separacao.models import Separacao
        if self.separacao_lote_id:
            return Separacao.query.filter_by(separacao_lote_id=self.separacao_lote_id).all()
        return []
    
    @property
    def pedido(self):
        """Compatibilidade: retorna dados agregados do pedido (VIEW)"""
        from app.pedidos.models import Pedido
        if self.separacao_lote_id:
            return Pedido.query.filter_by(separacao_lote_id=self.separacao_lote_id).first()
        return None

    def __repr__(self):
        return f'<CotacaoItem {self.id} - Lote {self.separacao_lote_id}>'

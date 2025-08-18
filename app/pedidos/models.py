from app import db
from datetime import datetime
from sqlalchemy import UniqueConstraint, event

class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação
    num_pedido = db.Column(db.String(30), index=True)
    data_pedido = db.Column(db.Date)
    cnpj_cpf = db.Column(db.String(20))
    raz_social_red = db.Column(db.String(255))
    nome_cidade = db.Column(db.String(120))
    cod_uf = db.Column(db.String(2))
    cidade_normalizada = db.Column(db.String(120))
    uf_normalizada = db.Column(db.String(2))
    codigo_ibge = db.Column(db.String(10))  # Código IBGE da cidade (único por cidade)
    valor_saldo_total = db.Column(db.Float)
    pallet_total = db.Column(db.Float)
    peso_total = db.Column(db.Float)
    rota = db.Column(db.String(50))
    sub_rota = db.Column(db.String(50))
    observ_ped_1 = db.Column(db.Text)
    roteirizacao = db.Column(db.String(100))
    expedicao = db.Column(db.Date)
    agendamento = db.Column(db.Date)
    protocolo = db.Column(db.String(50))
    agendamento_confirmado = db.Column(db.Boolean, default=False)  # Novo campo sincronizado com Separacao

    transportadora = db.Column(db.String(100))
    valor_frete = db.Column(db.Float)
    valor_por_kg = db.Column(db.Float)
    nome_tabela = db.Column(db.String(100))
    modalidade = db.Column(db.String(50))
    melhor_opcao = db.Column(db.String(100))
    valor_melhor_opcao = db.Column(db.Float)
    lead_time = db.Column(db.Integer)

    data_embarque = db.Column(db.Date)
    nf = db.Column(db.String(20))
    status = db.Column(db.String(50), default='ABERTO')
    nf_cd = db.Column(db.Boolean, default=False)  # ✅ NOVO: Flag para NF no CD
    
    # Controle de impressão da separação
    separacao_impressa = db.Column(db.Boolean, default=False, nullable=False)
    separacao_impressa_em = db.Column(db.DateTime, nullable=True)
    separacao_impressa_por = db.Column(db.String(100), nullable=True)
    
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id', name='fk_pedido_cotacao'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', name='fk_pedido_usuario'))

    __table_args__ = (
        UniqueConstraint(
            'num_pedido', 'expedicao', 'agendamento', 'protocolo',
            name='uix_num_pedido_exped_agend_prot'
        ),
    )

    # Relacionamentos
    usuario = db.relationship('Usuario', backref='pedidos', foreign_keys=[usuario_id])

    def __repr__(self):
        return f'<Pedido {self.num_pedido} - Lote: {self.separacao_lote_id}>'
    
    @property
    def status_calculado(self):
        """
        Calcula o status do pedido baseado no estado atual:
        - NF no CD: Flag nf_cd é True (NF voltou para o CD)
        - FATURADO: Tem NF preenchida e não está no CD
        - EMBARCADO: Tem data de embarque mas não tem NF
        - COTADO: Tem cotação_id mas não está embarcado
        - ABERTO: Não tem cotação
        """
        # ✅ NOVO: Primeiro verifica se a NF está no CD
        if getattr(self, 'nf_cd', False):
            return 'NF no CD'
        elif self.nf and self.nf.strip():
            return 'FATURADO'
        elif self.data_embarque:
            return 'EMBARCADO'
        elif self.cotacao_id:
            return 'COTADO'
        else:
            return 'ABERTO'
    
    @property
    def status_badge_class(self):
        """Retorna a classe CSS para o badge do status"""
        status_classes = {
            'NF no CD': 'badge bg-danger',  # ✅ NOVO: Vermelho para indicar problema
            'FATURADO': 'badge bg-success',
            'EMBARCADO': 'badge bg-primary', 
            'COTADO': 'badge bg-warning text-dark',
            'ABERTO': 'badge bg-secondary'
        }
        return status_classes.get(self.status_calculado, 'badge bg-light text-dark')
    
    @property
    def pendente_cotacao(self):
        """Verifica se o pedido está pendente de cotação"""
        return self.status_calculado == 'ABERTO'


# ==============================
# 🔄 TRIGGER AUTOMÁTICO DE NORMALIZAÇÃO
# ==============================

@event.listens_for(Pedido, 'before_insert')
@event.listens_for(Pedido, 'before_update')
def auto_normalizar_localizacao_pedido(mapper, connection, target):
    """
    Trigger automático que normaliza os dados de localização 
    sempre que um pedido é inserido ou atualizado.
    
    Isso garante que todos os pedidos tenham dados normalizados
    e código IBGE preenchido automaticamente.
    """
    try:
        # Só importa quando necessário para evitar import circular
        from app.utils.localizacao import LocalizacaoService
        
        # Normaliza os dados do pedido
        LocalizacaoService.normalizar_dados_pedido(target)
        
    except Exception as e:
        # Em caso de erro, não quebra a operação, apenas loga
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Erro ao normalizar dados do pedido {getattr(target, 'num_pedido', 'N/A')}: {str(e)}")
        
        # Aplica normalização básica como fallback
        if hasattr(target, 'nome_cidade') and target.nome_cidade:
            target.cidade_normalizada = target.nome_cidade.strip().upper()
        if hasattr(target, 'cod_uf') and target.cod_uf:
            target.uf_normalizada = target.cod_uf.strip().upper()

@event.listens_for(Pedido, 'before_insert')
@event.listens_for(Pedido, 'before_update')
def auto_atualizar_status_pedido(mapper, connection, target):
    """
    Trigger automático que atualiza o status do pedido baseado
    no status_calculado sempre que for inserido ou atualizado.
    
    Isso garante que o campo status no banco esteja sempre sincronizado
    com a lógica de negócio do status_calculado.
    """
    try:
        # Atualiza o status baseado na lógica calculada
        target.status = target.status_calculado
        
    except Exception as e:
        # Em caso de erro, não quebra a operação, apenas loga
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Erro ao atualizar status do pedido {getattr(target, 'num_pedido', 'N/A')}: {str(e)}")
        
        # Como fallback, mantém o status atual ou define como ABERTO
        if not hasattr(target, 'status') or not target.status:
            target.status = 'ABERTO'

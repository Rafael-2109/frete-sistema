from app import db  # ou de onde você estiver importando seu `db`
from datetime import datetime
from sqlalchemy import text, event
from sqlalchemy.ext.hybrid import hybrid_property

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

    @property
    def status_calculado(self):
        """
        Calcula o status do item de separação baseado no estado atual:
        - NF no CD: Flag nf_cd é True (NF voltou para o CD)
        - FATURADO: Tem NF preenchida (sincronizado_nf=True) e não está no CD
        - EMBARCADO: Tem data de embarque mas não tem NF
        - COTADO: Tem cotação_id mas não está embarcado
        - ABERTO: Não tem cotação
        - PREVISAO: Status é PREVISAO (pré-separação)
        """
        # Primeiro verifica se é uma pré-separação
        if self.status == 'PREVISAO':
            return 'PREVISAO'
        # Depois verifica se a NF está no CD
        elif getattr(self, 'nf_cd', False):
            return 'NF no CD'
        # Verifica se foi sincronizado com NF (faturado)
        elif self.sincronizado_nf or (self.numero_nf and str(self.numero_nf).strip()):
            return 'FATURADO'
        elif self.data_embarque:
            return 'EMBARCADO'
        elif self.cotacao_id:
            return 'COTADO'
        else:
            return 'ABERTO'
    
    @classmethod
    def atualizar_status(cls, separacao_lote_id, num_pedido=None, novo_status='ABERTO'):
        """
        Método helper para atualizar status de itens de separação
        Se num_pedido for fornecido, atualiza apenas esse pedido
        Caso contrário, atualiza todo o lote
        """
        if num_pedido:
            sql = text("""
                UPDATE separacao 
                SET status = :status
                WHERE separacao_lote_id = :lote_id
                AND num_pedido = :num_pedido
            """)
            
            db.session.execute(sql, {
                'status': novo_status,
                'lote_id': separacao_lote_id,
                'num_pedido': num_pedido
            })
        else:
            sql = text("""
                UPDATE separacao 
                SET status = :status
                WHERE separacao_lote_id = :lote_id
            """)
            
            db.session.execute(sql, {
                'status': novo_status,
                'lote_id': separacao_lote_id
            })
        
        db.session.commit()
    
    @classmethod
    def atualizar_nf_cd(cls, separacao_lote_id, num_pedido=None, nf_cd=False):
        """
        Método helper para atualizar flag nf_cd de itens de separação
        Se num_pedido for fornecido, atualiza apenas esse pedido
        Caso contrário, atualiza todo o lote
        """
        if num_pedido:
            sql = text("""
                UPDATE separacao 
                SET nf_cd = :nf_cd
                WHERE separacao_lote_id = :lote_id
                AND num_pedido = :num_pedido
            """)
            
            db.session.execute(sql, {
                'nf_cd': nf_cd,
                'lote_id': separacao_lote_id,
                'num_pedido': num_pedido
            })
        else:
            sql = text("""
                UPDATE separacao 
                SET nf_cd = :nf_cd
                WHERE separacao_lote_id = :lote_id
            """)
            
            db.session.execute(sql, {
                'nf_cd': nf_cd,
                'lote_id': separacao_lote_id
            })
        
        db.session.commit()
    
    def save(self):
        """
        Método helper para salvar alterações no item de separação
        """
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f'<Separacao #{self.id} - {self.num_pedido} - Lote: {self.separacao_lote_id} - Tipo: {self.tipo_envio}>'


# ============================================================================
# EVENT LISTENERS PARA SINCRONIZAÇÃO AUTOMÁTICA DE STATUS
# ============================================================================

@event.listens_for(Separacao, 'before_insert')
@event.listens_for(Separacao, 'before_update')
def atualizar_status_automatico(mapper, connection, target):
    """
    Atualiza automaticamente o campo status baseado nos outros campos
    antes de salvar no banco de dados.
    
    REGRAS DE PRIORIDADE (ordem importa):
    1. PREVISAO - Status manual, não sobrescrever
    2. NF no CD - Flag nf_cd é True
    3. FATURADO - Tem NF (sincronizado_nf=True ou numero_nf preenchido)
    4. EMBARCADO - Tem data_embarque
    5. COTADO - Tem cotacao_id
    6. ABERTO - Estado padrão
    
    REVERSÕES AUTOMÁTICAS:
    - Se data_embarque for removida: volta de EMBARCADO para COTADO ou ABERTO
    - Se cotacao_id for removida: volta de COTADO para ABERTO
    - Se sincronizado_nf for False e numero_nf vazia: volta de FATURADO
    """
    
    # REGRA 1: Nunca sobrescrever status PREVISAO (é manual)
    if target.status == 'PREVISAO':
        return
    
    # Calcular o status correto baseado nos campos
    status_anterior = target.status if hasattr(target, '_sa_instance_state') and target._sa_instance_state.key else None
    
    # REGRA 2: NF no CD tem prioridade máxima
    if getattr(target, 'nf_cd', False):
        target.status = 'NF no CD'
    
    # REGRA 3: FATURADO - tem NF
    elif target.sincronizado_nf or (target.numero_nf and str(target.numero_nf).strip()):
        target.status = 'FATURADO'
    
    # REGRA 4: EMBARCADO - tem data de embarque
    elif target.data_embarque:
        target.status = 'EMBARCADO'
    
    # REGRA 5: COTADO - tem cotação
    elif target.cotacao_id:
        target.status = 'COTADO'
    
    # REGRA 6: ABERTO - estado padrão
    else:
        target.status = 'ABERTO'
    
    # Log de mudança (apenas em desenvolvimento)
    if status_anterior and status_anterior != target.status:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"[STATUS_SYNC] Separação {target.id}: {status_anterior} → {target.status}")


@event.listens_for(Separacao, 'after_update')
def log_reversao_status(mapper, connection, target):
    """
    Registra reversões de status para auditoria e debugging.
    Útil para identificar quando pedidos voltam de um status para outro.
    """
    # Verificar se houve mudança de status
    if not hasattr(target, '_sa_instance_state'):
        return
    
    history = db.inspect(target).attrs.status.history
    if history.has_changes():
        status_anterior = history.deleted[0] if history.deleted else None
        status_novo = target.status
        
        # Detectar reversões importantes
        reversoes = {
            ('EMBARCADO', 'COTADO'): "Removido do embarque",
            ('EMBARCADO', 'ABERTO'): "Removido do embarque (sem cotação)",
            ('COTADO', 'ABERTO'): "Cotação removida",
            ('FATURADO', 'EMBARCADO'): "NF cancelada (mantém embarque)",
            ('FATURADO', 'COTADO'): "NF cancelada (mantém cotação)",
            ('FATURADO', 'ABERTO'): "NF cancelada (sem vínculos)",
            ('NF no CD', 'FATURADO'): "NF saiu do CD"
        }
        
        if (status_anterior, status_novo) in reversoes:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[REVERSÃO] Separação {target.id}: {reversoes[(status_anterior, status_novo)]}")


# ============================================================================
# MÉTODOS AUXILIARES PARA REVERSÃO MANUAL
# ============================================================================

def remover_do_embarque(separacao_lote_id, num_pedido=None):
    """
    Remove separação do embarque, zerando data_embarque.
    O status será recalculado automaticamente pelo event listener.
    """
    from sqlalchemy import text
    
    if num_pedido:
        sql = text("""
            UPDATE separacao 
            SET data_embarque = NULL
            WHERE separacao_lote_id = :lote_id
            AND num_pedido = :num_pedido
        """)
        db.session.execute(sql, {
            'lote_id': separacao_lote_id,
            'num_pedido': num_pedido
        })
    else:
        sql = text("""
            UPDATE separacao 
            SET data_embarque = NULL
            WHERE separacao_lote_id = :lote_id
        """)
        db.session.execute(sql, {
            'lote_id': separacao_lote_id
        })
    
    db.session.commit()


def remover_cotacao(separacao_lote_id, num_pedido=None):
    """
    Remove cotação da separação, zerando cotacao_id.
    O status será recalculado automaticamente pelo event listener.
    """
    from sqlalchemy import text
    
    if num_pedido:
        sql = text("""
            UPDATE separacao 
            SET cotacao_id = NULL
            WHERE separacao_lote_id = :lote_id
            AND num_pedido = :num_pedido
        """)
        db.session.execute(sql, {
            'lote_id': separacao_lote_id,
            'num_pedido': num_pedido
        })
    else:
        sql = text("""
            UPDATE separacao 
            SET cotacao_id = NULL
            WHERE separacao_lote_id = :lote_id
        """)
        db.session.execute(sql, {
            'lote_id': separacao_lote_id
        })
    
    db.session.commit()


def cancelar_faturamento(separacao_lote_id, num_pedido=None):
    """
    Cancela o faturamento da separação, limpando campos de NF.
    O status será recalculado automaticamente pelo event listener.
    """
    from sqlalchemy import text
    
    if num_pedido:
        sql = text("""
            UPDATE separacao 
            SET sincronizado_nf = FALSE,
                numero_nf = NULL,
                data_sincronizacao = NULL
            WHERE separacao_lote_id = :lote_id
            AND num_pedido = :num_pedido
        """)
        db.session.execute(sql, {
            'lote_id': separacao_lote_id,
            'num_pedido': num_pedido
        })
    else:
        sql = text("""
            UPDATE separacao 
            SET sincronizado_nf = FALSE,
                numero_nf = NULL,
                data_sincronizacao = NULL
            WHERE separacao_lote_id = :lote_id
        """)
        db.session.execute(sql, {
            'lote_id': separacao_lote_id
        })
    
    db.session.commit()

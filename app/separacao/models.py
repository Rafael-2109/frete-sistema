from app import db  # ou de onde você estiver importando seu `db`
from datetime import datetime
from app.utils.timezone import agora_utc_naive
from sqlalchemy import text, event
from sqlalchemy.ext.hybrid import hybrid_property

# models.py
class Separacao(db.Model):
    __tablename__ = 'separacao'

    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # VARCHAR ex: LOTE_20251004_032844_195 (NAO e integer)
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
    observ_ped_1 = db.Column(db.String(700), nullable=True)  # Truncado automaticamente antes de salvar
    roteirizacao = db.Column(db.String(255), nullable=True)
    expedicao = db.Column(db.Date, nullable=True)
    agendamento = db.Column(db.Date, nullable=True)
    agendamento_confirmado = db.Column(db.Boolean, default=False)  # Flag para confirmação de agendamento
    protocolo = db.Column(db.String(50), nullable=True)
    pedido_cliente = db.Column(db.String(100), nullable=True)  # 🆕 Pedido de Compra do Cliente

    # 🏷️ TAGS DO PEDIDO (ODOO) — sincronizado de CarteiraPrincipal
    tags_pedido = db.Column(db.Text, nullable=True)  # JSON: [{"name": "VIP", "color": 5}]

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

    # 📝 CAMPOS DE CONTROLE DE SEPARAÇÃO (NOVOS)
    obs_separacao = db.Column(db.Text, nullable=True)  # Observações sobre a separação
    falta_item = db.Column(db.Boolean, default=False, nullable=False)  # Indica se falta item no estoque
    falta_pagamento = db.Column(db.Boolean, default=False, nullable=False)  # Indica se pagamento está pendente

    # Relacionamento com cotação (para manter compatibilidade com Pedido)
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'), nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)  # Usuario que criou a separacao
    
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

        # Índices para lista_pedidos - contadores de falta_item/falta_pagamento
        db.Index('idx_sep_falta_item_sync', 'falta_item', 'sincronizado_nf', postgresql_where=db.text('falta_item = true')),
        db.Index('idx_sep_falta_pgto_sync', 'falta_pagamento', 'sincronizado_nf', postgresql_where=db.text('falta_pagamento = true')),
        db.Index('idx_sep_nf_cd', 'nf_cd', postgresql_where=db.text('nf_cd = true')),
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

        IMPORTANTE: Usa ORM para garantir que event listeners sejam disparados
        """
        # Buscar itens usando ORM para disparar event listeners
        query = cls.query.filter_by(separacao_lote_id=separacao_lote_id)

        if num_pedido:
            query = query.filter_by(num_pedido=num_pedido)

        # Atualizar cada item via ORM (dispara event listeners)
        items = query.all()
        for item in items:
            item.status = novo_status

        db.session.commit()
    
    @classmethod
    def atualizar_nf_cd(cls, separacao_lote_id, num_pedido=None, nf_cd=False):
        """
        Método helper para atualizar flag nf_cd de itens de separação
        Se num_pedido for fornecido, atualiza apenas esse pedido
        Caso contrário, atualiza todo o lote

        IMPORTANTE: Usa ORM para garantir que event listeners sejam disparados
        """
        # Buscar itens usando ORM para disparar event listeners
        query = cls.query.filter_by(separacao_lote_id=separacao_lote_id)

        if num_pedido:
            query = query.filter_by(num_pedido=num_pedido)

        # Atualizar cada item via ORM (dispara event listeners)
        items = query.all()
        for item in items:
            item.nf_cd = nf_cd

        db.session.commit()

    @classmethod
    def atualizar_cotacao(cls, separacao_lote_id, cotacao_id, nf_cd=False):
        """
        Método helper para atualizar cotacao_id de itens de separação
        IMPORTANTE: Usa ORM para garantir que event listeners sejam disparados
        e o status seja atualizado automaticamente para COTADO
        """
        # Buscar itens usando ORM para disparar event listeners
        items = cls.query.filter_by(separacao_lote_id=separacao_lote_id).all()

        for item in items:
            item.cotacao_id = cotacao_id
            item.nf_cd = nf_cd
            # O event listener vai atualizar o status automaticamente

        db.session.commit()
        return len(items)  # Retorna quantidade de itens atualizados
    
    def save(self):
        """
        Método helper para salvar alterações no item de separação
        """
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f'<Separacao #{self.id} - {self.num_pedido} - Lote: {self.separacao_lote_id} - Tipo: {self.tipo_envio}>'


# ============================================================================
# EVENT LISTENERS PARA SINCRONIZAÇÃO AUTOMÁTICA DE STATUS E FALTA_PAGAMENTO
# ============================================================================

@event.listens_for(Separacao, 'before_insert')
def setar_falta_pagamento_inicial(mapper, connection, target):
    """
    Define falta_pagamento=True automaticamente APENAS na criação (INSERT)
    se o pedido tem condição de pagamento ANTECIPADO.

    Após a criação, o valor só pode ser alterado manualmente pelo usuário via botão.
    Este listener NÃO roda em UPDATEs para preservar a escolha manual do usuário.

    ✅ Executado: APENAS no INSERT (criação)
    ❌ NÃO executado: Em UPDATEs (preserva valor manual)
    """
    if target.num_pedido:
        from app.carteira.models import CarteiraPrincipal
        from sqlalchemy import select

        try:
            # Buscar condição de pagamento na CarteiraPrincipal
            stmt = select(CarteiraPrincipal.cond_pgto_pedido).where(
                CarteiraPrincipal.num_pedido == target.num_pedido
            ).limit(1)

            result = connection.execute(stmt).scalar()

            # Se encontrou e tem ANTECIPADO, marca falta_pagamento=True
            if result and 'ANTECIPADO' in result.upper():
                target.falta_pagamento = True

        except Exception as e:
            # Em caso de erro, mantém o valor padrão (False)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[FALTA_PAGAMENTO] Erro ao verificar pedido {target.num_pedido}: {e}")


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


@event.listens_for(Separacao, 'after_update')
@event.listens_for(Separacao, 'after_delete')
def recalcular_totais_embarque(mapper, connection, target):
    """
    ✅ CORREÇÃO: Recalcula automaticamente os totais do Embarque e EmbarqueItem
    quando peso, valor ou pallet de uma Separacao são alterados.

    Este listener dispara APÓS o commit, então pode fazer queries normalmente.

    IMPORTANTE:
    - Recalcula APENAS se a Separacao está vinculada a um EmbarqueItem
    - Atualiza EmbarqueItem.peso, .valor, .pallets
    - Atualiza Embarque.peso_total, .valor_total, .pallet_total
    """
    import logging
    logger = logging.getLogger(__name__)

    # Só recalcular se tem separacao_lote_id
    if not target.separacao_lote_id:
        return

    try:
        # Buscar EmbarqueItem vinculado a este lote
        from app.embarques.models import EmbarqueItem, Embarque
        from sqlalchemy import select, func

        # Buscar EmbarqueItem pelo separacao_lote_id
        stmt = select(EmbarqueItem).where(
            EmbarqueItem.separacao_lote_id == target.separacao_lote_id,
            EmbarqueItem.status == 'ativo'
        )
        resultado = connection.execute(stmt).first()

        if not resultado:
            # Não está em nenhum embarque ativo
            return

        embarque_item_id = resultado[0]  # ID do EmbarqueItem
        embarque_id = resultado[1]  # ID do Embarque (segunda coluna)

        # ✅ RECALCULAR TOTAIS DO LOTE (somando TODAS as Separacoes do lote)
        stmt_totais = select(
            func.sum(Separacao.peso).label('peso_total'),
            func.sum(Separacao.valor_saldo).label('valor_total'),
            func.sum(Separacao.pallet).label('pallet_total')
        ).where(
            Separacao.separacao_lote_id == target.separacao_lote_id,
            Separacao.sincronizado_nf == False
        )

        totais = connection.execute(stmt_totais).first()

        if totais:
            peso_total_lote = float(totais[0] or 0)
            valor_total_lote = float(totais[1] or 0)
            pallet_total_lote = float(totais[2] or 0)

            # ✅ ATUALIZAR EmbarqueItem
            connection.execute(
                text("""
                    UPDATE embarque_itens
                    SET peso = :peso, valor = :valor, pallets = :pallets
                    WHERE id = :item_id
                """),
                {
                    'peso': peso_total_lote,
                    'valor': valor_total_lote,
                    'pallets': pallet_total_lote,
                    'item_id': embarque_item_id
                }
            )

            # ✅ RECALCULAR TOTAIS DO EMBARQUE (somando TODOS os EmbarqueItems ativos)
            stmt_embarque = select(
                func.sum(EmbarqueItem.peso).label('peso_total'),
                func.sum(EmbarqueItem.valor).label('valor_total'),
                func.sum(EmbarqueItem.pallets).label('pallet_total')
            ).where(
                EmbarqueItem.embarque_id == embarque_id,
                EmbarqueItem.status == 'ativo'
            )

            totais_embarque = connection.execute(stmt_embarque).first()

            if totais_embarque:
                peso_total_embarque = float(totais_embarque[0] or 0)
                valor_total_embarque = float(totais_embarque[1] or 0)
                pallet_total_embarque = float(totais_embarque[2] or 0)

                # ✅ ATUALIZAR Embarque
                connection.execute(
                    text("""
                        UPDATE embarques
                        SET peso_total = :peso, valor_total = :valor, pallet_total = :pallet
                        WHERE id = :embarque_id
                    """),
                    {
                        'peso': peso_total_embarque,
                        'valor': valor_total_embarque,
                        'pallet': pallet_total_embarque,
                        'embarque_id': embarque_id
                    }
                )

                logger.info(f"✅ [RECALC] Embarque #{embarque_id} atualizado: "
                           f"Peso={peso_total_embarque:.2f}, Valor={valor_total_embarque:.2f}, "
                           f"Pallets={pallet_total_embarque:.2f}")

    except Exception as e:
        logger.error(f"❌ Erro ao recalcular totais do embarque: {e}", exc_info=True)
        # ✅ CORREÇÃO: Re-levantar exceção para evitar transações parcialmente corrompidas
        # Conforme .claude/ralph-loop/IMPLEMENTATION_PLAN.md - Item 3.1: Event Listener SEM Re-raise
        raise


# ============================================================================
# MÉTODOS AUXILIARES PARA REVERSÃO MANUAL
# ============================================================================

def remover_do_embarque(separacao_lote_id, num_pedido=None):
    """
    Remove separação do embarque, zerando data_embarque.
    O status será recalculado automaticamente pelo event listener.

    IMPORTANTE: Usa ORM para garantir que event listeners sejam disparados
    """
    # Buscar itens usando ORM para disparar event listeners
    query = Separacao.query.filter_by(separacao_lote_id=separacao_lote_id)

    if num_pedido:
        query = query.filter_by(num_pedido=num_pedido)

    # Atualizar cada item via ORM (dispara event listeners)
    items = query.all()
    for item in items:
        item.data_embarque = None

    db.session.commit()


def remover_cotacao(separacao_lote_id, num_pedido=None):
    """
    Remove cotação da separação, zerando cotacao_id.
    O status será recalculado automaticamente pelo event listener.

    IMPORTANTE: Usa ORM para garantir que event listeners sejam disparados
    """
    # Buscar itens usando ORM para disparar event listeners
    query = Separacao.query.filter_by(separacao_lote_id=separacao_lote_id)

    if num_pedido:
        query = query.filter_by(num_pedido=num_pedido)

    # Atualizar cada item via ORM (dispara event listeners)
    items = query.all()
    for item in items:
        item.cotacao_id = None

    db.session.commit()


def cancelar_faturamento(separacao_lote_id, num_pedido=None):
    """
    Cancela o faturamento da separação, limpando campos de NF.
    O status será recalculado automaticamente pelo event listener.

    IMPORTANTE: Usa ORM para garantir que event listeners sejam disparados
    """
    # Buscar itens usando ORM para disparar event listeners
    query = Separacao.query.filter_by(separacao_lote_id=separacao_lote_id)

    if num_pedido:
        query = query.filter_by(num_pedido=num_pedido)

    # Atualizar cada item via ORM (dispara event listeners)
    items = query.all()
    for item in items:
        item.sincronizado_nf = False
        item.numero_nf = None
        item.data_sincronizacao = None

    db.session.commit()

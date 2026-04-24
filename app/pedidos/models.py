"""
Adapter para o modelo Pedido funcionando como VIEW
Data: 2025-01-29

Este arquivo substitui models.py quando Pedido se torna uma VIEW
"""

from app import db
from datetime import datetime
from sqlalchemy import text
from app.utils.timezone import agora_utc_naive
from sqlalchemy.ext.hybrid import hybrid_property

class Pedido(db.Model):
    """
    Modelo Pedido que agora é uma VIEW agregando dados de Separacao
    """
    __tablename__ = 'pedidos'
    __table_args__ = {'info': {'is_view': True}}  # VIEW (sempre fresco — dados de separacao em tempo real)
    
    # Campos mapeados da VIEW
    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) #Vem de Separacao.separacao_lote_id
    num_pedido = db.Column(db.String(30), index=True) #Vem de Separacao.num_pedido
    data_pedido = db.Column(db.Date) #Vem de Separacao.data_pedido
    cnpj_cpf = db.Column(db.String(20)) #Vem de Separacao.cnpj_cpf
    raz_social_red = db.Column(db.String(255)) #Vem de Separacao.raz_social_red
    nome_cidade = db.Column(db.String(120)) #Vem de Separacao.nome_cidade
    cod_uf = db.Column(db.String(2)) #Vem de Separacao.cod_uf
    cidade_normalizada = db.Column(db.String(120)) 
    uf_normalizada = db.Column(db.String(2)) 
    codigo_ibge = db.Column(db.String(10))
    valor_saldo_total = db.Column(db.Float) #soma de Separacao.valor_saldo
    pallet_total = db.Column(db.Float) #soma de Separacao.pallet
    peso_total = db.Column(db.Float) #soma de Separacao.peso
    rota = db.Column(db.String(50)) #Vem de Separacao.rota
    sub_rota = db.Column(db.String(50)) #Vem de Separacao.sub_rota
    observ_ped_1 = db.Column(db.Text) #Vem de Separacao.observ_ped_1
    roteirizacao = db.Column(db.String(100)) #Vem de Separacao.roteirizacao
    expedicao = db.Column(db.Date) #Vem de Separacao.expedicao
    agendamento = db.Column(db.Date) #Vem de Separacao.agendamento
    protocolo = db.Column(db.String(50)) #Vem de Separacao.protocolo
    agendamento_confirmado = db.Column(db.Boolean, default=False) #Vem de Separacao.agendamento_confirmado

    # Campo de equipe de vendas (via JOIN com CarteiraPrincipal na VIEW)
    equipe_vendas = db.Column(db.String(100), nullable=True) #Vem de CarteiraPrincipal.equipe_vendas

    # 🏷️ Tags do pedido (de Separacao, via VIEW)
    tags_pedido = db.Column(db.Text, nullable=True)  # JSON: [{"name": "VIP", "color": 5}]

    # Campos de transporte (virão NULL da VIEW, precisam JOIN com cotacao)
    transportadora = db.Column(db.String(100))
    valor_frete = db.Column(db.Float)
    valor_por_kg = db.Column(db.Float)
    nome_tabela = db.Column(db.String(100))
    modalidade = db.Column(db.String(50))
    melhor_opcao = db.Column(db.String(100))
    valor_melhor_opcao = db.Column(db.Float)
    lead_time = db.Column(db.Integer)
    
    # Campos de status e NF
    data_embarque = db.Column(db.Date)
    nf = db.Column(db.String(20))
    status = db.Column(db.String(50), default='ABERTO')
    nf_cd = db.Column(db.Boolean, default=False)
    pedido_cliente = db.Column(db.String(100), nullable=True)
    
    # Controle de impressão
    separacao_impressa = db.Column(db.Boolean, default=False, nullable=False)
    separacao_impressa_em = db.Column(db.DateTime, nullable=True)
    separacao_impressa_por = db.Column(db.String(100), nullable=True)
    
    # Relacionamentos (via JOIN quando necessário)
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Timestamps
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    
    @property
    def eh_carvia(self):
        """Detecta item CarVia pelo prefixo do separacao_lote_id (CARVIA- ou CARVIA-PED-)."""
        lote = getattr(self, 'separacao_lote_id', None) or ''
        return lote.startswith('CARVIA-')

    @property
    def status_calculado(self):
        """
        Calcula o status do pedido baseado no estado atual.

        Fluxo unificado Nacom + CarVia (P12, 2026-04-24):
            ABERTO -> COTADO -> FATURADO
            (+ NF no CD como estado especial para Nacom)

        EMBARCADO deixou de ser status — virou badge visual independente via
        `badge_embarcado` (data_embarque preenchida E NF nao voltou ao CD).
        Isso reflete que EMBARCADO e um evento fisico ortogonal ao ciclo
        fiscal do pedido (FATURADO = NF ativa; EMBARCADO = saiu da portaria).

        Status retornados:
        - NF no CD: Nacom com flag nf_cd=True
        - FATURADO: NF preenchida e ativa
        - COTADO: em embarque ativo (sem NF ainda)
        - CANCELADO: explicitamente cancelado
        - CARVIA_COTADO / CARVIA: fallbacks CarVia sem embarque/sem NF
        - ABERTO: sem cotacao
        """
        # CarVia: detectado pelo prefixo CARVIA- no separacao_lote_id
        if self.eh_carvia:
            status_view = getattr(self, 'status', '') or ''
            if status_view in ('FATURADO',):
                return 'FATURADO'
            if status_view in ('CANCELADO',):
                return 'CANCELADO'
            # CarVia em embarque ativo — atributo injetado por
            # ListaPedidosService.enriquecer_pedidos (lista_service.py:691).
            # EMBARCADO deixou de ser status: pedido com data_embarque ganha
            # badge separado via `badge_embarcado`. Aqui so distingue "em
            # embarque" (CARVIA_COTADO) de "sem embarque" (CARVIA).
            ultimo_embarque = getattr(self, 'ultimo_embarque', None)
            if ultimo_embarque is not None:
                return 'CARVIA_COTADO'
            return 'CARVIA'

        # Nacom: flags concretas têm prioridade (NF existe de fato)
        if getattr(self, 'nf_cd', False):
            return 'NF no CD'
        elif self.nf and self.nf.strip():
            return 'FATURADO'
        # Status real persistido (ex: COTADO via embarque) tem prioridade sobre derivação.
        # EMBARCADO (se persistido em separacao.status) e convertido para COTADO
        # — a informacao fisica do embarque vai para o badge_embarcado.
        status_real = getattr(self, 'status', '') or ''
        if status_real == 'EMBARCADO':
            return 'COTADO' if self.cotacao_id else 'ABERTO'
        if status_real not in ('', 'ABERTO'):
            return status_real
        # Fallback derivado
        elif self.cotacao_id:
            return 'COTADO'
        else:
            return 'ABERTO'

    @property
    def badge_embarcado(self):
        """Retorna data/hora do embarque quando o pedido esta embarcado.

        Badge visual ORTOGONAL ao status_calculado (P12, 2026-04-24):
        - Aparece quando `data_embarque` preenchida E `nf_cd=False`.
        - Mascara: "Emb.{DD/MM} - {HH:MM}" (hora via ControlePortaria).

        Fontes:
        - Nacom: `Pedido.data_embarque` (VIEW via Separacao).
        - CarVia: `data_embarque` NULL na VIEW; usa `ultimo_embarque`
          (injetado por `enriquecer_pedidos`).
        - Hora: `_hora_saida_portaria` injetado por `enriquecer_pedidos`
          (batch-load de ControlePortaria). Fallback: None.

        Returns:
            dict | None: {'data': date, 'hora': time|None, 'texto': str}
        """
        if getattr(self, 'nf_cd', False):
            return None

        data_emb = getattr(self, 'data_embarque', None)
        if not data_emb:
            ult = getattr(self, 'ultimo_embarque', None)
            if ult is not None:
                data_emb = getattr(ult, 'data_embarque', None)

        if not data_emb:
            return None

        # Hora injetada por enriquecer_pedidos (batch-load ControlePortaria)
        hora = getattr(self, '_hora_saida_portaria', None)

        texto = f"Emb.{data_emb.strftime('%d/%m')}"
        if hora:
            texto += f" - {hora.strftime('%H:%M')}"
        return {'data': data_emb, 'hora': hora, 'texto': texto}
    
    def __repr__(self):
        return f'<Pedido {self.num_pedido} - Lote: {self.separacao_lote_id}>'
    
    @classmethod
    def atualizar_status(cls, separacao_lote_id, num_pedido, novo_status):
        """
        Método helper para atualizar status via UPDATE em Separacao
        """
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
        db.session.commit()
    
    @classmethod
    def atualizar_nf_cd(cls, separacao_lote_id, num_pedido, nf_cd):
        """
        Método helper para atualizar flag nf_cd via UPDATE em Separacao
        """
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
        db.session.commit()
    
    def save(self):
        """
        Override save para atualizar Separacao em vez de Pedido
        """
        # Atualiza campos em Separacao
        sql = text("""
            UPDATE separacao 
            SET 
                status = :status,
                nf_cd = :nf_cd,
                data_embarque = :data_embarque,
                agendamento = :agendamento,
                protocolo = :protocolo,
                agendamento_confirmado = :agendamento_confirmado,
                separacao_impressa = :separacao_impressa,
                separacao_impressa_em = :separacao_impressa_em,
                separacao_impressa_por = :separacao_impressa_por
            WHERE separacao_lote_id = :lote_id
            AND num_pedido = :num_pedido
        """)
        
        db.session.execute(sql, {
            'status': self.status,
            'nf_cd': self.nf_cd,
            'data_embarque': self.data_embarque,
            'agendamento': self.agendamento,
            'protocolo': self.protocolo,
            'agendamento_confirmado': self.agendamento_confirmado,
            'separacao_impressa': self.separacao_impressa,
            'separacao_impressa_em': self.separacao_impressa_em,
            'separacao_impressa_por': self.separacao_impressa_por,
            'lote_id': self.separacao_lote_id,
            'num_pedido': self.num_pedido
        })
        db.session.commit()


class PedidoMV(db.Model):
    """
    Materialized View mv_pedidos — snapshot pre-computado da VIEW pedidos.
    Usar APENAS para queries de contadores e agregacao (tolera staleness ~30min).
    Para dados frescos (edicao, lista paginada), usar Pedido (VIEW).
    Criada via migration (scripts/migrations/criar_mv_pedidos.sql), NAO por db.create_all().
    """
    __tablename__ = 'mv_pedidos'
    __table_args__ = {
        'info': {'is_view': True, 'skip_autogenerate': True},
        'keep_existing': True,  # nao tentar recriar se ja existe
    }

    # Campos usados pelos contadores e filtros
    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50))
    num_pedido = db.Column(db.String(30))
    cnpj_cpf = db.Column(db.String(20))
    cod_uf = db.Column(db.String(2))
    rota = db.Column(db.String(50))
    sub_rota = db.Column(db.String(50))
    expedicao = db.Column(db.Date)
    agendamento = db.Column(db.Date)
    data_embarque = db.Column(db.Date)
    nf = db.Column(db.String(20))
    status = db.Column(db.String(50))
    nf_cd = db.Column(db.Boolean)
    cotacao_id = db.Column(db.Integer)

    def __repr__(self):
        return f'<PedidoMV {self.separacao_lote_id}>'
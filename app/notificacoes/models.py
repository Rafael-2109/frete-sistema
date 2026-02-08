#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODELOS DE NOTIFICACAO
Modelos SQLAlchemy para persistencia de alertas e notificacoes
"""

from datetime import datetime
from app import db
from app.utils.timezone import agora_utc_naive
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Index


class AlertaNotificacao(db.Model):
    """
    Modelo para persistir alertas e notificacoes do sistema.

    Suporta multiplos canais de entrega:
    - in_app: notificacao interna (exibida na UI)
    - email: enviado por SMTP
    - webhook: HTTP POST para URL externa

    CAMPOS PRINCIPAIS:
    - tipo: tipo do alerta (ex: SEPARACAO_COTADA_ALTERADA, QUANTIDADE_INSUFICIENTE)
    - nivel: CRITICO, ATENCAO, INFO
    - mensagem: texto principal do alerta
    - dados: JSON com contexto adicional (pedido, produto, etc)
    - status_envio: pendente, enviado, falhou, lido
    - canais: lista de canais ['in_app', 'email', 'webhook']
    """
    __tablename__ = 'alerta_notificacoes'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao do alerta
    tipo = db.Column(db.String(100), nullable=False, index=True)  # Ex: SEPARACAO_COTADA_ALTERADA
    nivel = db.Column(db.String(20), nullable=False, default='INFO')  # CRITICO, ATENCAO, INFO

    # Conteudo
    titulo = db.Column(db.String(255), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    dados = db.Column(JSONB, nullable=True)  # JSON com contexto adicional

    # Destinatario (opcional - se None, e alerta de sistema)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)

    # Canais de entrega
    canais = db.Column(JSONB, nullable=False, default=['in_app'])  # ['in_app', 'email', 'webhook']

    # Status de envio por canal
    status_envio = db.Column(db.String(20), nullable=False, default='pendente')  # pendente, enviado, falhou, lido
    status_email = db.Column(db.String(20), nullable=True)  # pendente, enviado, falhou
    status_webhook = db.Column(db.String(20), nullable=True)  # pendente, enviado, falhou

    # Detalhes de entrega
    email_destinatario = db.Column(db.String(255), nullable=True)
    webhook_url = db.Column(db.String(500), nullable=True)
    webhook_response = db.Column(JSONB, nullable=True)  # Resposta do webhook

    # Metadados
    criado_em = db.Column(db.DateTime(timezone=True), default=agora_utc_naive, nullable=False)
    enviado_em = db.Column(db.DateTime(timezone=True), nullable=True)
    lido_em = db.Column(db.DateTime(timezone=True), nullable=True)

    # Auditoria
    origem = db.Column(db.String(100), nullable=True)  # Ex: sincronizacao_odoo, alert_system
    referencia_id = db.Column(db.String(100), nullable=True)  # ID do objeto relacionado (pedido, separacao, etc)
    referencia_tipo = db.Column(db.String(50), nullable=True)  # Tipo do objeto relacionado

    # Tentativas de reenvio
    tentativas_envio = db.Column(db.Integer, default=0)
    ultimo_erro = db.Column(db.Text, nullable=True)

    # Relacionamento com Usuario
    user = db.relationship(
        'Usuario',
        backref=db.backref('notificacoes', lazy='dynamic', cascade='all, delete-orphan')
    )

    # Indices para consultas frequentes
    __table_args__ = (
        Index('idx_notif_tipo_nivel', 'tipo', 'nivel'),
        Index('idx_notif_status_criado', 'status_envio', 'criado_em'),
        Index('idx_notif_user_status', 'user_id', 'status_envio'),
    )

    def __repr__(self):
        return f'<AlertaNotificacao {self.id} [{self.nivel}] {self.tipo}>'

    def to_dict(self):
        """Converte para dicionario (para API/JSON)"""
        return {
            'id': self.id,
            'tipo': self.tipo,
            'nivel': self.nivel,
            'titulo': self.titulo,
            'mensagem': self.mensagem,
            'dados': self.dados,
            'canais': self.canais,
            'status_envio': self.status_envio,
            'status_email': self.status_email,
            'status_webhook': self.status_webhook,
            'criado_em': self.criado_em.strftime('%d/%m/%Y %H:%M:%S') if self.criado_em else None,
            'enviado_em': self.enviado_em.strftime('%d/%m/%Y %H:%M:%S') if self.enviado_em else None,
            'lido_em': self.lido_em.strftime('%d/%m/%Y %H:%M:%S') if self.lido_em else None,
            'origem': self.origem,
            'referencia_id': self.referencia_id,
            'referencia_tipo': self.referencia_tipo,
        }

    def marcar_como_lido(self):
        """Marca notificacao como lida"""
        self.status_envio = 'lido'
        self.lido_em = agora_utc_naive()
        db.session.commit()

    def marcar_como_enviado(self, canal=None):
        """Marca notificacao como enviada (geral ou por canal)"""
        if canal == 'email':
            self.status_email = 'enviado'
        elif canal == 'webhook':
            self.status_webhook = 'enviado'
        else:
            self.status_envio = 'enviado'
        self.enviado_em = agora_utc_naive()
        db.session.commit()

    def marcar_como_falhou(self, erro, canal=None):
        """Marca notificacao como falhou (geral ou por canal)"""
        self.tentativas_envio += 1
        self.ultimo_erro = str(erro)[:1000]  # Limita tamanho do erro

        if canal == 'email':
            self.status_email = 'falhou'
        elif canal == 'webhook':
            self.status_webhook = 'falhou'
        else:
            self.status_envio = 'falhou'
        db.session.commit()

    @classmethod
    def criar_alerta(cls, tipo, nivel, titulo, mensagem, dados=None, user_id=None,
                     canais=None, origem=None, referencia_id=None, referencia_tipo=None,
                     email_destinatario=None, webhook_url=None):
        """
        Factory method para criar alertas de forma padronizada.

        Args:
            tipo: Tipo do alerta (ex: SEPARACAO_COTADA_ALTERADA)
            nivel: Nivel de severidade (CRITICO, ATENCAO, INFO)
            titulo: Titulo curto do alerta
            mensagem: Mensagem detalhada
            dados: Dicionario com contexto adicional
            user_id: ID do usuario destinatario (opcional)
            canais: Lista de canais ['in_app', 'email', 'webhook']
            origem: Modulo de origem (ex: sincronizacao_odoo)
            referencia_id: ID do objeto relacionado
            referencia_tipo: Tipo do objeto (ex: pedido, separacao)
            email_destinatario: Email para envio (se canal email)
            webhook_url: URL para webhook (se canal webhook)

        Returns:
            AlertaNotificacao: Instancia criada e salva no banco
        """
        if canais is None:
            canais = ['in_app']

        alerta = cls(
            tipo=tipo,
            nivel=nivel,
            titulo=titulo,
            mensagem=mensagem,
            dados=dados or {},
            user_id=user_id,
            canais=canais,
            origem=origem,
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
            email_destinatario=email_destinatario,
            webhook_url=webhook_url,
            status_envio='pendente',
            status_email='pendente' if 'email' in canais else None,
            status_webhook='pendente' if 'webhook' in canais else None,
        )

        db.session.add(alerta)
        db.session.commit()

        return alerta

    @classmethod
    def buscar_pendentes(cls, limite=100):
        """Busca alertas pendentes de envio"""
        return cls.query.filter(
            cls.status_envio == 'pendente'
        ).order_by(
            cls.criado_em.asc()
        ).limit(limite).all()

    @classmethod
    def buscar_nao_lidos_usuario(cls, user_id, limite=50):
        """Busca alertas nao lidos para um usuario"""
        return cls.query.filter(
            cls.user_id == user_id,
            cls.status_envio != 'lido',
            cls.canais.contains(['in_app'])  # Apenas alertas in_app
        ).order_by(
            cls.criado_em.desc()
        ).limit(limite).all()

    @classmethod
    def contar_nao_lidos_usuario(cls, user_id):
        """Conta alertas nao lidos para um usuario"""
        return cls.query.filter(
            cls.user_id == user_id,
            cls.status_envio != 'lido',
            cls.canais.contains(['in_app'])
        ).count()

    @classmethod
    def buscar_por_tipo(cls, tipo, limite=100, dias=7):
        """Busca alertas por tipo nos ultimos N dias"""
        from datetime import timedelta
        data_limite = agora_utc_naive() - timedelta(days=dias)

        return cls.query.filter(
            cls.tipo == tipo,
            cls.criado_em >= data_limite
        ).order_by(
            cls.criado_em.desc()
        ).limit(limite).all()


class WebhookConfig(db.Model):
    """
    Configuracao de webhooks para notificacoes.
    Permite cadastrar multiplos endpoints externos.
    """
    __tablename__ = 'webhook_configs'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)

    # Configuracao do endpoint
    url = db.Column(db.String(500), nullable=False)
    metodo = db.Column(db.String(10), default='POST')  # POST, PUT
    headers = db.Column(JSONB, nullable=True)  # Headers customizados

    # Autenticacao (opcional)
    auth_type = db.Column(db.String(20), nullable=True)  # bearer, basic, api_key
    auth_token = db.Column(db.String(500), nullable=True)  # Token ou API key

    # Filtros - quais tipos de alerta enviar para este webhook
    tipos_alerta = db.Column(JSONB, nullable=True)  # Lista de tipos ou None para todos
    niveis_alerta = db.Column(JSONB, nullable=True)  # Lista de niveis ou None para todos

    # Status
    ativo = db.Column(db.Boolean, default=True)

    # Metadados
    criado_em = db.Column(db.DateTime(timezone=True), default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime(timezone=True), onupdate=agora_utc_naive)

    # Estatisticas
    total_envios = db.Column(db.Integer, default=0)
    total_falhas = db.Column(db.Integer, default=0)
    ultimo_envio = db.Column(db.DateTime(timezone=True), nullable=True)
    ultimo_erro = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<WebhookConfig {self.id} {self.nome}>'

    def to_dict(self):
        """Converte para dicionario (sem dados sensiveis)"""
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'url': self.url,
            'metodo': self.metodo,
            'auth_type': self.auth_type,
            'tipos_alerta': self.tipos_alerta,
            'niveis_alerta': self.niveis_alerta,
            'ativo': self.ativo,
            'total_envios': self.total_envios,
            'total_falhas': self.total_falhas,
            'ultimo_envio': self.ultimo_envio.strftime('%d/%m/%Y %H:%M:%S') if self.ultimo_envio else None,
        }

    def deve_processar_alerta(self, tipo, nivel):
        """Verifica se este webhook deve processar o alerta dado"""
        if not self.ativo:
            return False

        # Se nao tem filtro de tipo, aceita todos
        if self.tipos_alerta and tipo not in self.tipos_alerta:
            return False

        # Se nao tem filtro de nivel, aceita todos
        if self.niveis_alerta and nivel not in self.niveis_alerta:
            return False

        return True

    def registrar_envio(self, sucesso=True, erro=None):
        """Registra resultado de envio"""
        if sucesso:
            self.total_envios += 1
            self.ultimo_envio = agora_utc_naive()
            self.ultimo_erro = None
        else:
            self.total_falhas += 1
            self.ultimo_erro = str(erro)[:1000] if erro else 'Erro desconhecido'

        db.session.commit()

"""
🚚 MODELOS DE RASTREAMENTO GPS DE ENTREGAS
Autor: Sistema de Rastreamento Nacom
Data: 2025-10-01

CONFORMIDADE LGPD:
- Coleta de localização GPS mediante consentimento explícito
- Retenção de dados: 90 dias
- Finalidade: Rastreamento de entregas e comprovação
- Base legal: Execução de contrato (Art. 7º, V da LGPD)
"""

from app import db
from datetime import datetime, timedelta
import secrets


class RastreamentoEmbarque(db.Model):
    """
    Registro principal de rastreamento de um embarque
    Controla o ciclo de vida do rastreamento GPS
    """
    __tablename__ = 'rastreamento_embarques'

    id = db.Column(db.Integer, primary_key=True)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False, unique=True, index=True)

    # Token único para acesso via QR Code
    token_acesso = db.Column(db.String(64), unique=True, nullable=False, index=True)
    token_expiracao = db.Column(db.DateTime, nullable=True)  # NULL = sem expiração

    # Status do rastreamento
    status = db.Column(db.String(20), default='AGUARDANDO_ACEITE', nullable=False)
    # Valores: AGUARDANDO_ACEITE, ATIVO, CHEGOU_DESTINO, ENTREGUE, CANCELADO, EXPIRADO

    # Dados de aceite LGPD
    aceite_lgpd = db.Column(db.Boolean, default=False, nullable=False)
    aceite_lgpd_em = db.Column(db.DateTime, nullable=True)
    aceite_lgpd_ip = db.Column(db.String(45), nullable=True)  # Suporta IPv6
    aceite_lgpd_user_agent = db.Column(db.String(500), nullable=True)

    # Controle de rastreamento ativo
    rastreamento_iniciado_em = db.Column(db.DateTime, nullable=True)
    rastreamento_finalizado_em = db.Column(db.DateTime, nullable=True)
    ultimo_ping_em = db.Column(db.DateTime, nullable=True)

    # Detecção de chegada ao destino
    chegou_destino_em = db.Column(db.DateTime, nullable=True)
    distancia_minima_atingida = db.Column(db.Float, nullable=True)  # Em metros

    # Comprovante de entrega
    canhoto_arquivo = db.Column(db.String(500), nullable=True)  # Caminho S3/local
    canhoto_enviado_em = db.Column(db.DateTime, nullable=True)
    canhoto_latitude = db.Column(db.Float, nullable=True)
    canhoto_longitude = db.Column(db.Float, nullable=True)

    # Auditoria e LGPD
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False, default='Sistema')
    data_expurgo_lgpd = db.Column(db.DateTime, nullable=True)  # Automaticamente 90 dias após criação

    # Relacionamentos
    embarque = db.relationship('Embarque', backref=db.backref('rastreamento', uselist=False))
    pings = db.relationship('PingGPS', backref='rastreamento', lazy='dynamic', cascade='all, delete-orphan', order_by='PingGPS.criado_em.desc()')
    logs = db.relationship('LogRastreamento', backref='rastreamento', lazy='dynamic', cascade='all, delete-orphan', order_by='LogRastreamento.criado_em.desc()')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Gera token único na criação
        if not self.token_acesso:
            self.token_acesso = secrets.token_urlsafe(48)  # 64 caracteres
        # Define data de expurgo LGPD (90 dias)
        if not self.data_expurgo_lgpd:
            self.data_expurgo_lgpd = datetime.utcnow() + timedelta(days=90)

    @property
    def url_rastreamento(self):
        """
        Retorna a URL completa para acesso via QR Code

        IMPORTANTE:
        - Em PRODUÇÃO: Usa SERVER_NAME do Flask (ex: seudominio.com)
        - Em DESENVOLVIMENTO: Usa IP da rede local (ex: 192.168.1.100:5000)

        Configure SERVER_NAME no .env ou config.py:
        - Produção: SERVER_NAME=seudominio.com
        - Local: SERVER_NAME=192.168.1.100:5000
        """
        from flask import url_for, current_app
        import os

        # Tentar obter URL base customizada do ambiente
        base_url_custom = os.getenv('RASTREAMENTO_BASE_URL')

        if base_url_custom:
            # URL customizada definida (ex: https://seudominio.com ou http://192.168.1.100:5000)
            return f"{base_url_custom.rstrip('/')}/rastreamento/aceite/{self.token_acesso}"
        else:
            # Usar url_for padrão do Flask
            return url_for('rastreamento.aceite_lgpd', token=self.token_acesso, _external=True)

    @property
    def esta_ativo(self):
        """Verifica se o rastreamento está ativo"""
        return self.status == 'ATIVO' and self.aceite_lgpd

    @property
    def chegou_proximo_destino(self):
        """Verifica se chegou próximo ao destino (200m)"""
        return self.status == 'CHEGOU_DESTINO' or (
            self.distancia_minima_atingida and self.distancia_minima_atingida <= 200
        )

    @property
    def tempo_sem_ping(self):
        """Retorna tempo em segundos desde o último ping"""
        if not self.ultimo_ping_em:
            return None
        return (datetime.utcnow() - self.ultimo_ping_em).total_seconds()

    @property
    def dias_para_expurgo(self):
        """Retorna quantos dias faltam para expurgo LGPD"""
        if not self.data_expurgo_lgpd:
            return None
        delta = self.data_expurgo_lgpd - datetime.utcnow()
        return max(0, delta.days)

    def registrar_log(self, evento, detalhes=None):
        """Registra evento no log de rastreamento"""
        log = LogRastreamento(
            rastreamento_id=self.id,
            evento=evento,
            detalhes=detalhes
        )
        db.session.add(log)
        return log

    def __repr__(self):
        return f'<RastreamentoEmbarque Embarque #{self.embarque_id} - Status: {self.status}>'


class PingGPS(db.Model):
    """
    Registro individual de cada ping GPS enviado pelo transportador
    Frequência: A cada 2 minutos
    """
    __tablename__ = 'pings_gps'

    id = db.Column(db.Integer, primary_key=True)
    rastreamento_id = db.Column(db.Integer, db.ForeignKey('rastreamento_embarques.id'), nullable=False, index=True)

    # Dados GPS
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    precisao = db.Column(db.Float, nullable=True)  # Precisão em metros
    altitude = db.Column(db.Float, nullable=True)
    velocidade = db.Column(db.Float, nullable=True)  # km/h
    direcao = db.Column(db.Float, nullable=True)  # Graus (0-360)

    # Distância calculada até o destino
    distancia_destino = db.Column(db.Float, nullable=True)  # Em metros

    # Dados do dispositivo
    bateria_nivel = db.Column(db.Integer, nullable=True)  # 0-100%
    bateria_carregando = db.Column(db.Boolean, default=False)

    # Timestamp
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    timestamp_dispositivo = db.Column(db.DateTime, nullable=True)  # Horário do dispositivo

    def __repr__(self):
        return f'<PingGPS Rastreamento #{self.rastreamento_id} - {self.latitude}, {self.longitude}>'

    @property
    def coordenadas(self):
        """Retorna tupla (latitude, longitude) para cálculos"""
        return (self.latitude, self.longitude)


class LogRastreamento(db.Model):
    """
    Log de eventos do rastreamento para auditoria
    """
    __tablename__ = 'logs_rastreamento'

    id = db.Column(db.Integer, primary_key=True)
    rastreamento_id = db.Column(db.Integer, db.ForeignKey('rastreamento_embarques.id'), nullable=False, index=True)

    # Dados do evento
    evento = db.Column(db.String(50), nullable=False)  # Ex: ACEITE_LGPD, INICIO_RASTREAMENTO, CHEGADA_DESTINO
    detalhes = db.Column(db.Text, nullable=True)  # JSON ou texto livre

    # Timestamp
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f'<LogRastreamento {self.evento} - {self.criado_em}>'


class ConfiguracaoRastreamento(db.Model):
    """
    Configurações globais do sistema de rastreamento
    Singleton pattern - apenas 1 registro
    """
    __tablename__ = 'configuracao_rastreamento'

    id = db.Column(db.Integer, primary_key=True)

    # Configurações de ping
    intervalo_ping_segundos = db.Column(db.Integer, default=120, nullable=False)  # 2 minutos
    intervalo_ping_parado_segundos = db.Column(db.Integer, default=300, nullable=False)  # 5 minutos quando parado
    velocidade_considerada_parado = db.Column(db.Float, default=5.0, nullable=False)  # km/h

    # Configurações de proximidade
    distancia_chegada_metros = db.Column(db.Float, default=200.0, nullable=False)  # 200 metros

    # Configurações LGPD
    dias_retencao_dados = db.Column(db.Integer, default=90, nullable=False)  # 90 dias
    versao_termo_lgpd = db.Column(db.String(20), default='1.0', nullable=False)

    # Configurações de notificação
    notificar_chegada_destino = db.Column(db.Boolean, default=True, nullable=False)
    notificar_inatividade_minutos = db.Column(db.Integer, default=30, nullable=True)  # NULL = desabilitado

    # Controle
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    atualizado_por = db.Column(db.String(100), nullable=True)

    @staticmethod
    def get_config():
        """Retorna a configuração única (singleton)"""
        config = ConfiguracaoRastreamento.query.first()
        if not config:
            # Cria configuração padrão
            config = ConfiguracaoRastreamento()
            db.session.add(config)
            db.session.commit()
        return config

    def __repr__(self):
        return f'<ConfiguracaoRastreamento Ping: {self.intervalo_ping_segundos}s | Proximidade: {self.distancia_chegada_metros}m>'

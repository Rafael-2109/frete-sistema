"""
Modelos do modulo de Seguranca
==============================

4 tabelas:
- seguranca_varreduras: Historico de scans
- seguranca_vulnerabilidades: Achados individuais por colaborador
- seguranca_scores: Historico de scores para trends
- seguranca_config: Configuracao key/value
"""

from app import db
from app.utils.timezone import agora_utc_naive


class SegurancaVarredura(db.Model):
    """Historico de varreduras/scans de seguranca"""
    __tablename__ = 'seguranca_varreduras'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(
        db.String(30), nullable=False
    )  # EMAIL_BREACH, PASSWORD_HEALTH, DOMAIN_EXPOSURE, FULL_SCAN
    status = db.Column(
        db.String(20), nullable=False, default='EM_EXECUCAO'
    )  # EM_EXECUCAO, CONCLUIDA, FALHOU
    iniciado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    concluido_em = db.Column(db.DateTime, nullable=True)
    total_verificados = db.Column(db.Integer, default=0)
    total_vulnerabilidades = db.Column(db.Integer, default=0)
    detalhes = db.Column(db.JSON, nullable=True)  # JSONB com detalhes extras
    disparado_por = db.Column(db.String(120), nullable=True)  # email do admin

    # Relacionamento
    vulnerabilidades = db.relationship(
        'SegurancaVulnerabilidade',
        backref='varredura',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<SegurancaVarredura {self.id} tipo={self.tipo} status={self.status}>'


class SegurancaVulnerabilidade(db.Model):
    """Achados individuais de vulnerabilidade por colaborador"""
    __tablename__ = 'seguranca_vulnerabilidades'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    varredura_id = db.Column(
        db.Integer, db.ForeignKey('seguranca_varreduras.id'), nullable=True
    )
    categoria = db.Column(
        db.String(30), nullable=False
    )  # EMAIL_BREACH, SENHA_FRACA, SENHA_VAZADA, DOMINIO_SPF, DOMINIO_DMARC, DOMINIO_DNSSEC
    severidade = db.Column(
        db.String(10), nullable=False
    )  # CRITICA, ALTA, MEDIA, BAIXA, INFO
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    dados = db.Column(db.JSON, nullable=True)  # JSONB com dados especificos do achado
    status = db.Column(
        db.String(20), nullable=False, default='ABERTA'
    )  # ABERTA, EM_ANDAMENTO, RESOLVIDA, ACEITA, FALSO_POSITIVO
    notificado = db.Column(db.Boolean, default=False)
    notificado_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=agora_utc_naive, onupdate=agora_utc_naive
    )

    # Relacionamento
    usuario = db.relationship('Usuario', backref='vulnerabilidades_seguranca')

    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'categoria', 'titulo',
            name='uq_seguranca_vuln_user_cat_titulo'
        ),
        db.Index('ix_seguranca_vuln_user_status', 'user_id', 'status'),
        db.Index('ix_seguranca_vuln_cat_sev', 'categoria', 'severidade'),
    )

    def __repr__(self):
        return (
            f'<SegurancaVulnerabilidade {self.id} '
            f'cat={self.categoria} sev={self.severidade}>'
        )

    @property
    def severidade_ordem(self):
        """Retorna ordem numerica para sorting (menor = mais critico)"""
        ordem = {
            'CRITICA': 0,
            'ALTA': 1,
            'MEDIA': 2,
            'BAIXA': 3,
            'INFO': 4,
        }
        return ordem.get(self.severidade, 99)


class SegurancaScore(db.Model):
    """Historico de scores de seguranca para trends"""
    __tablename__ = 'seguranca_scores'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id'), nullable=True
    )  # NULL = score da empresa
    score = db.Column(db.Integer, nullable=False)  # 0-100 (100=melhor)
    componentes = db.Column(db.JSON, nullable=True)  # JSONB breakdown do score
    vulnerabilidades_abertas = db.Column(db.Integer, default=0)
    vulnerabilidades_criticas = db.Column(db.Integer, default=0)
    calculado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    # Relacionamento
    usuario = db.relationship('Usuario', backref='scores_seguranca')

    __table_args__ = (
        db.Index('ix_seguranca_score_user_calc', 'user_id', 'calculado_em'),
    )

    def __repr__(self):
        return f'<SegurancaScore {self.id} user={self.user_id} score={self.score}>'


class SegurancaConfig(db.Model):
    """Configuracao key/value do modulo de seguranca"""
    __tablename__ = 'seguranca_config'

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text, nullable=True)
    descricao = db.Column(db.String(300), nullable=True)
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=agora_utc_naive, onupdate=agora_utc_naive
    )
    atualizado_por = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f'<SegurancaConfig {self.chave}={self.valor}>'

    # Defaults que serao inseridos na migration/seed
    DEFAULTS = {
        'hibp_api_key': {
            'valor': '',
            'descricao': 'API Key do HaveIBeenPwned (opcional, email breaches)'
        },
        'scan_interval_hours': {
            'valor': '24',
            'descricao': 'Intervalo entre varreduras automaticas (horas)'
        },
        'password_min_entropy': {
            'valor': '3',
            'descricao': 'Score minimo de senha (0-4, zxcvbn)'
        },
        'domains_to_monitor': {
            'valor': '',
            'descricao': 'Dominios adicionais para monitorar (separados por virgula)'
        },
        'auto_scan_enabled': {
            'valor': 'true',
            'descricao': 'Habilitar varredura automatica'
        },
    }

    @classmethod
    def get_valor(cls, chave, default=None):
        """Busca valor de config pela chave"""
        config = cls.query.filter_by(chave=chave).first()
        if config and config.valor:
            return config.valor
        return default

    @classmethod
    def set_valor(cls, chave, valor, atualizado_por=None):
        """Define valor de config pela chave"""
        config = cls.query.filter_by(chave=chave).first()
        if config:
            config.valor = valor
            if atualizado_por:
                config.atualizado_por = atualizado_por
        else:
            config = cls(chave=chave, valor=valor, atualizado_por=atualizado_por)
            db.session.add(config)
        db.session.flush()
        return config

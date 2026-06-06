"""
Modelos para integração TagPlus
"""

from datetime import datetime
from app import db
from app.utils.timezone import agora_utc_naive


class NFPendenteTagPlus(db.Model):
    """
    Tabela para armazenar itens de NFs do TagPlus pendentes de importação
    por falta de número de pedido (campo origem)
    """
    __tablename__ = 'nf_pendente_tagplus'

    id = db.Column(db.Integer, primary_key=True)

    # Dados da NF - espelhando FaturamentoProduto
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255), nullable=False)
    nome_cidade = db.Column(db.String(120), nullable=True)
    cod_uf = db.Column(db.String(5), nullable=True)
    data_fatura = db.Column(db.Date, nullable=False)

    # Dados do Produto
    cod_produto = db.Column(db.String(50), nullable=False)
    nome_produto = db.Column(db.String(200), nullable=False)
    qtd_produto_faturado = db.Column(db.Numeric(15, 3), nullable=False)
    preco_produto_faturado = db.Column(db.Numeric(15, 4), nullable=False)
    valor_produto_faturado = db.Column(db.Numeric(15, 2), nullable=False)

    # Campos de peso (calculados via CadastroPalletizacao)
    peso_unitario_produto = db.Column(db.Numeric(15, 3), nullable=True, default=0)  # Peso bruto unitário
    peso_total = db.Column(db.Numeric(15, 3), nullable=True, default=0)  # qtd_produto_faturado * peso_unitario_produto

    # Campo a ser preenchido pelo usuário
    origem = db.Column(db.String(50), nullable=True, index=True)  # Número do pedido

    # Status do fluxo
    resolvido = db.Column(db.Boolean, default=False, index=True)
    importado = db.Column(db.Boolean, default=False, index=True)

    # Auditoria básica
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    pedido_preenchido_em = db.Column(db.DateTime, nullable=True)
    pedido_preenchido_por = db.Column(db.String(100), nullable=True)
    resolvido_em = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    importado_em = db.Column(db.DateTime, nullable=True)

    # Índice composto para evitar duplicação
    __table_args__ = (
        db.UniqueConstraint('numero_nf', 'cod_produto', name='uq_nf_produto'),
        db.Index('idx_nf_pendente_resolvido', 'resolvido', 'importado'),
    )

    def __repr__(self):
        return f'<NFPendenteTagPlus {self.numero_nf}/{self.cod_produto}>'


class TagPlusOAuthToken(db.Model):
    """
    Armazena tokens OAuth2 do TagPlus no BANCO DE DADOS (não em session)

    ⚠️ IMPORTANTE: Resolve problema de perda de tokens após deploy

    Cada api_type (clientes, notas) tem seu próprio token.
    O refresh_token permite renovação automática por 30-90 dias.
    """
    __tablename__ = 'tagplus_oauth_token'

    id = db.Column(db.Integer, primary_key=True)

    # Tipo de API (único por tipo)
    api_type = db.Column(db.String(50), nullable=False, unique=True, index=True)
    # Exemplos: 'clientes', 'notas', 'produtos'

    # ✅ Tokens OAuth2
    access_token = db.Column(db.Text, nullable=False)  # Expira em 24h
    refresh_token = db.Column(db.Text, nullable=True)  # Dura 30-90 dias

    # ⏰ Controle de expiração
    expires_at = db.Column(db.DateTime, nullable=True)  # Quando access_token expira

    # 📝 Metadados OAuth
    token_type = db.Column(db.String(20), default='Bearer')
    scope = db.Column(db.String(255), nullable=True)

    # 📊 Auditoria e estatísticas
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive, nullable=False)
    ultimo_refresh = db.Column(db.DateTime, nullable=True)  # Última renovação
    total_refreshes = db.Column(db.Integer, default=0)  # Contador de renovações
    ultima_requisicao = db.Column(db.DateTime, nullable=True)  # Último uso

    # ✅ Status
    ativo = db.Column(db.Boolean, default=True, index=True)

    def __repr__(self):
        status = "VÁLIDO" if not self.esta_expirado else "EXPIRADO"
        return f'<TagPlusOAuthToken {self.api_type} {status}>'

    @property
    def esta_expirado(self):
        """
        Verifica se access_token está expirado
        Margem de segurança: 5 minutos antes da expiração real
        """
        if not self.expires_at:
            return True

        from datetime import timedelta
        margem = timedelta(minutes=5)
        return agora_utc_naive() >= (self.expires_at - margem)

    @property
    def tem_refresh_token(self):
        """Verifica se tem refresh_token disponível para renovação"""
        return bool(self.refresh_token and self.refresh_token.strip())

    @property
    def tempo_ate_expiracao(self):
        """Retorna timedelta até expiração (None se já expirado)"""
        if not self.expires_at or self.esta_expirado:
            return None
        return self.expires_at - agora_utc_naive()

    def to_dict(self):
        """Converte para dicionário (não expõe tokens completos)"""
        return {
            'id': self.id,
            'api_type': self.api_type,
            'access_token_preview': self.access_token[:20] + '...' if self.access_token else None,
            'tem_refresh_token': self.tem_refresh_token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'esta_expirado': self.esta_expirado,
            'tempo_restante_minutos': int(self.tempo_ate_expiracao.total_seconds() / 60) if self.tempo_ate_expiracao else 0,
            'ultimo_refresh': self.ultimo_refresh.isoformat() if self.ultimo_refresh else None,
            'total_refreshes': self.total_refreshes,
            'ultima_requisicao': self.ultima_requisicao.isoformat() if self.ultima_requisicao else None,
            'ativo': self.ativo
        }

    @staticmethod
    def buscar_ou_criar(api_type):
        """
        Busca token existente ou cria novo registro

        Args:
            api_type: Tipo da API ('clientes', 'notas', etc)

        Returns:
            Instância de TagPlusOAuthToken
        """
        token = TagPlusOAuthToken.query.filter_by(api_type=api_type, ativo=True).first()

        if not token:
            token = TagPlusOAuthToken(api_type=api_type)
            db.session.add(token)

        return token


class TagPlusNotificacaoWhatsapp(db.Model):
    """Registro/dedupe/auditoria das notificações WhatsApp de pedido/NF do TagPlus.

    UNIQUE (tipo, tagplus_id, event_type) garante idempotência contra reenvio
    do webhook pelo TagPlus. Flags `enviado_grupo`/`enviado_vendedor` permitem
    reenvio só do destino pendente.
    """
    __tablename__ = 'tagplus_notificacao_whatsapp'

    id = db.Column(db.Integer, primary_key=True)

    tipo = db.Column(db.String(10), nullable=False)         # PEDIDO | NFE
    event_type = db.Column(db.String(30), nullable=False)   # pedido_criado | nfe_criada
    tagplus_id = db.Column(db.String(30), nullable=False)   # id do registro no TagPlus (string)

    numero = db.Column(db.String(30), nullable=True)
    cliente_nome = db.Column(db.String(255), nullable=True)
    valor = db.Column(db.Numeric(15, 2), nullable=True)

    vendedor_nome = db.Column(db.String(120), nullable=True)
    vendedor_user_id = db.Column(db.Integer, nullable=True)  # usuarios.id (sem FK, padrão do projeto)

    enviado_grupo = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    enviado_vendedor = db.Column(db.Boolean, nullable=True)  # NULL = não havia vendedor a notificar

    status = db.Column(db.String(15), nullable=False, default='PENDENTE')  # PENDENTE/PROCESSANDO/ENVIADO/PARCIAL/ERRO/IGNORADO
    erro = db.Column(db.Text, nullable=True)
    tentativas = db.Column(db.Integer, nullable=False, default=0)
    anexou_pdf = db.Column(db.Boolean, nullable=False, default=False, server_default='false')

    enviado_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('tipo', 'tagplus_id', 'event_type', name='uq_tagplus_notif_tipo_id_event'),
        db.Index('idx_tagplus_notif_status', 'status'),
    )

    def __repr__(self):
        return f'<TagPlusNotificacaoWhatsapp {self.tipo} {self.tagplus_id} {self.status}>'

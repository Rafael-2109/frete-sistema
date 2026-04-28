"""Integracao TagPlus para emissao de NFe de venda (Lojas HORA).

5 tabelas novas (prefixo `hora_tagplus_`):
  HoraTagPlusConta              singleton; credenciais OAuth e webhook secret
  HoraTagPlusToken              tokens OAuth2 (encriptados, persistidos no DB)
  HoraTagPlusProdutoMap         de-para HoraModelo -> produto TagPlus
  HoraTagPlusFormaPagamentoMap  de-para HoraVenda.forma_pagamento -> forma TagPlus
  HoraTagPlusNfeEmissao         fila + historico de emissao (fonte de verdade)

Detalhes: app/hora/EMISSAO_NFE_ENGENHARIA.md secoes 3, 6, 7.
"""
from __future__ import annotations

from app import db
from app.utils.timezone import agora_utc_naive


class HoraTagPlusConta(db.Model):
    """Conta TagPlus (singleton). Todas as lojas HORA faturam pelo mesmo CNPJ.

    Constraint de unicidade parcial via SQL: `WHERE ativo = TRUE`. Permite
    rotacionar credenciais sem violar UNIQUE — desativar antiga + criar nova.
    """
    __tablename__ = 'hora_tagplus_conta'

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(db.String(64), nullable=False)
    client_secret_encrypted = db.Column(db.Text, nullable=False)
    # Encriptado com Fernet (chave em env HORA_TAGPLUS_ENC_KEY).

    webhook_secret = db.Column(db.String(64), nullable=False)
    # Token compartilhado com TagPlus em X-Hub-Secret. Gerado com
    # secrets.token_urlsafe(32) no cadastro.

    oauth_state_last = db.Column(db.String(64), nullable=True)
    # Anti-CSRF: persistido entre /oauth e /callback.

    scope_contratado = db.Column(
        db.String(255), nullable=False,
        default='write:nfes read:clientes write:clientes read:produtos',
    )

    ativo = db.Column(db.Boolean, nullable=False, default=True)
    # UNIQUE INDEX parcial em SQL: so 1 ativa.

    ambiente = db.Column(db.String(15), nullable=False, default='producao')
    # producao|homologacao. TagPlus nao tem ambiente de homologacao real;
    # 'homologacao' apenas bloqueia POST /nfes em ambiente dev.

    redirect_uri = db.Column(db.String(500), nullable=True)
    # Configurado no portal TagPlus; armazenado para conferencia no checklist.

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    @classmethod
    def ativa(cls) -> 'HoraTagPlusConta':
        """Retorna a unica conta ativa. Levanta RuntimeError se nenhuma."""
        conta = cls.query.filter_by(ativo=True).first()
        if not conta:
            raise RuntimeError(
                'Nenhuma conta TagPlus HORA ativa — configurar em /hora/tagplus/conta'
            )
        return conta

    def __repr__(self) -> str:
        return (
            f'<HoraTagPlusConta {self.id} ambiente={self.ambiente} '
            f'ativo={self.ativo}>'
        )


class HoraTagPlusToken(db.Model):
    """Tokens OAuth2 da conta. 1 linha por conta (UNIQUE)."""
    __tablename__ = 'hora_tagplus_token'

    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_tagplus_conta.id', ondelete='CASCADE'),
        nullable=False, unique=True, index=True,
    )

    access_token_encrypted = db.Column(db.Text, nullable=False)
    refresh_token_encrypted = db.Column(db.Text, nullable=False)
    token_type = db.Column(db.String(20), nullable=False, default='bearer')

    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    # Timestamp absoluto (TagPlus retorna expires_in=86400, ou seja, 24h).

    obtido_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    refreshed_em = db.Column(db.DateTime, nullable=True)

    conta = db.relationship(
        'HoraTagPlusConta',
        backref=db.backref('token', uselist=False, cascade='all, delete-orphan'),
    )

    def __repr__(self) -> str:
        return f'<HoraTagPlusToken conta={self.conta_id} expires_at={self.expires_at}>'


class HoraTagPlusProdutoMap(db.Model):
    """De-para HoraModelo -> produto cadastrado no TagPlus."""
    __tablename__ = 'hora_tagplus_produto_map'

    id = db.Column(db.Integer, primary_key=True)
    modelo_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_modelo.id'),
        nullable=False, unique=True, index=True,
    )
    tagplus_produto_id = db.Column(db.String(50), nullable=False)
    # POST /nfes aceita string no campo `produto` (codigo do produto no TagPlus).
    # Doc mostra exemplo `"produto": 1` (linha 638), mas o ERP aceita codigo string.

    tagplus_codigo = db.Column(db.String(50), nullable=True)
    # Opcional, exibicao/debug.

    cfop_default = db.Column(db.String(5), nullable=False, default='5.403')
    # 5.403 intra / 6.403 inter (venda de mercadoria com ST — contribuinte substituido).
    # PayloadBuilder ajusta por UF do cliente.

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    modelo = db.relationship('HoraModelo', backref=db.backref('tagplus_map', uselist=False))

    def __repr__(self) -> str:
        return (
            f'<HoraTagPlusProdutoMap modelo={self.modelo_id} '
            f'tagplus={self.tagplus_produto_id}>'
        )


class HoraTagPlusFormaPagamentoMap(db.Model):
    """De-para forma_pagamento HORA -> ID inteiro de forma no TagPlus."""
    __tablename__ = 'hora_tagplus_forma_pagamento_map'

    id = db.Column(db.Integer, primary_key=True)
    forma_pagamento_hora = db.Column(db.String(20), nullable=False, unique=True)
    # PIX / CARTAO_CREDITO / DINHEIRO.

    tagplus_forma_id = db.Column(db.Integer, nullable=False)
    # ID inteiro no TagPlus. Resolvido via GET /formas_pagamento (doc:672-687).

    descricao = db.Column(db.String(80), nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    def __repr__(self) -> str:
        return (
            f'<HoraTagPlusFormaPagamentoMap {self.forma_pagamento_hora} '
            f'-> {self.tagplus_forma_id}>'
        )


# Estados validos da maquina de emissao (manter sincronizado com EMISSAO_NFE_ENGENHARIA.md secao 2.2).
NFE_STATUS_PENDENTE = 'PENDENTE'
NFE_STATUS_EM_ENVIO = 'EM_ENVIO'
NFE_STATUS_ENVIADA_SEFAZ = 'ENVIADA_SEFAZ'
NFE_STATUS_APROVADA = 'APROVADA'
NFE_STATUS_REJEITADA_LOCAL = 'REJEITADA_LOCAL'
NFE_STATUS_REJEITADA_SEFAZ = 'REJEITADA_SEFAZ'
NFE_STATUS_ERRO_INFRA = 'ERRO_INFRA'
NFE_STATUS_CANCELAMENTO_SOLICITADO = 'CANCELAMENTO_SOLICITADO'
NFE_STATUS_CANCELADA = 'CANCELADA'

NFE_STATUS_VALIDOS = (
    NFE_STATUS_PENDENTE, NFE_STATUS_EM_ENVIO, NFE_STATUS_ENVIADA_SEFAZ,
    NFE_STATUS_APROVADA, NFE_STATUS_REJEITADA_LOCAL, NFE_STATUS_REJEITADA_SEFAZ,
    NFE_STATUS_ERRO_INFRA, NFE_STATUS_CANCELAMENTO_SOLICITADO, NFE_STATUS_CANCELADA,
)


class HoraTagPlusNfeEmissao(db.Model):
    """Fila + historico de emissoes. Fonte de verdade do status de emissao.

    Idempotencia: UNIQUE em venda_id. Re-emissao apos rejeicao reutiliza a
    mesma linha (nao cria nova).
    """
    __tablename__ = 'hora_tagplus_nfe_emissao'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_venda.id'),
        nullable=False, unique=True, index=True,
    )
    conta_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_tagplus_conta.id'),
        nullable=False, index=True,
    )

    status = db.Column(
        db.String(30), nullable=False,
        default=NFE_STATUS_PENDENTE, index=True,
    )

    tagplus_nfe_id = db.Column(db.Integer, nullable=True, index=True)
    numero_nfe = db.Column(db.String(20), nullable=True)
    serie_nfe = db.Column(db.String(5), nullable=True)
    chave_44 = db.Column(db.String(44), nullable=True, unique=True)
    protocolo_aprovacao = db.Column(db.String(30), nullable=True)

    # Auditoria (sanitizar com sanitize_for_json antes de atribuir).
    payload_enviado = db.Column(db.JSON, nullable=True)
    response_inicial = db.Column(db.JSON, nullable=True)
    response_webhook = db.Column(db.JSON, nullable=True)

    error_code = db.Column(db.String(60), nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    tentativas = db.Column(db.Integer, nullable=False, default=0)

    enviado_em = db.Column(db.DateTime, nullable=True)
    aprovado_em = db.Column(db.DateTime, nullable=True)

    # Cancelamento.
    cancelamento_justificativa = db.Column(db.Text, nullable=True)
    cancelamento_solicitado_por = db.Column(db.String(100), nullable=True)
    cancelamento_solicitado_em = db.Column(db.DateTime, nullable=True)
    cancelado_em = db.Column(db.DateTime, nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    venda = db.relationship('HoraVenda', backref=db.backref('emissao_nfe', uselist=False))
    conta = db.relationship('HoraTagPlusConta')

    def __repr__(self) -> str:
        return (
            f'<HoraTagPlusNfeEmissao venda={self.venda_id} status={self.status} '
            f'nfe={self.numero_nfe}>'
        )

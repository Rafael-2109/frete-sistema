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

    scope_efetivo = db.Column(db.String(255), nullable=True)
    # Scope retornado pelo TagPlus no token response. Pode divergir de
    # HoraTagPlusConta.scope_contratado quando admin atualiza contratado mas
    # ainda nao reautorizou (refresh_token nao re-emite scope, conforme RFC OAuth2).

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
    # Codigo curto exibido na coluna CODIGO da DANFE PDF emitida pelo TagPlus
    # (ex: 'MT-JETMAX', 'MT-X12', 'BK-VTB4').
    #
    # Papel duplo:
    # 1. Exibicao/debug na tela de mapeamento.
    # 2. CHAVE DE BACKFILL: parser DANFE (`danfe_pdf_parser._extrair_veiculos_llm`)
    #    extrai esse codigo da NF emitida e o backfill resolve `modelo_id` via
    #    SELECT ... WHERE tagplus_codigo = :codigo. Caminho deterministico que
    #    nao depende de LLM adivinhar o nome do modelo.

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


# Tipos de pagamento para HoraTagPlusFormaPagamentoMap (migration hora_33).
# Determinam qual preço do modelo (preco_a_vista vs preco_a_prazo) sera
# usado quando esta forma de pagamento for selecionada no pedido de venda.
TIPO_PAGAMENTO_A_VISTA = 'A_VISTA'
TIPO_PAGAMENTO_A_PRAZO = 'A_PRAZO'
TIPOS_PAGAMENTO_VALIDOS = (TIPO_PAGAMENTO_A_VISTA, TIPO_PAGAMENTO_A_PRAZO)


class HoraTagPlusFormaPagamentoMap(db.Model):
    """De-para forma_pagamento HORA -> ID inteiro de forma no TagPlus."""
    __tablename__ = 'hora_tagplus_forma_pagamento_map'

    id = db.Column(db.Integer, primary_key=True)
    forma_pagamento_hora = db.Column(db.String(20), nullable=False, unique=True)
    # PIX / CARTAO_CREDITO / DINHEIRO.

    tagplus_forma_id = db.Column(db.Integer, nullable=False)
    # ID inteiro no TagPlus. Resolvido via GET /formas_pagamento (doc:672-687).

    descricao = db.Column(db.String(80), nullable=True)

    tipo_pagamento = db.Column(db.String(10), nullable=True)
    # 'A_VISTA' | 'A_PRAZO' | NULL (nao classificada). CHECK constraint no DB
    # garante apenas esses valores. Usado pelo pedido de venda manual para
    # decidir qual preço do modelo trazer (preco_a_vista vs preco_a_prazo).

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    def __repr__(self) -> str:
        return (
            f'<HoraTagPlusFormaPagamentoMap {self.forma_pagamento_hora} '
            f'-> {self.tagplus_forma_id} ({self.tipo_pagamento or "—"})>'
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

    tagplus_pedido_id = db.Column(db.Integer, nullable=True, index=True)
    # ID do pedido auto-criado pelo TagPlus quando NFe e confirmada
    # (pedido_os_vinculada.id no GET /nfes/{id}). Chave para GET /pedidos/{id}.

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


# Status do job de backfill — mantidos como constantes para reuso em workers,
# rotas e templates.
BACKFILL_JOB_STATUS_PENDENTE = 'PENDENTE'
BACKFILL_JOB_STATUS_EM_PROGRESSO = 'EM_PROGRESSO'
BACKFILL_JOB_STATUS_CONCLUIDO = 'CONCLUIDO'
BACKFILL_JOB_STATUS_ERRO = 'ERRO'
BACKFILL_JOB_STATUS_CANCELADO = 'CANCELADO'

BACKFILL_JOB_STATUS_FINAIS = (
    BACKFILL_JOB_STATUS_CONCLUIDO,
    BACKFILL_JOB_STATUS_ERRO,
    BACKFILL_JOB_STATUS_CANCELADO,
)

# Tipo de backfill — discriminador para reuso da mesma tabela.
BACKFILL_JOB_TIPO_NF = 'NF'
# Backfill original: lista NFs no TagPlus e cria/atualiza HoraVenda
# (importar_nfe_da_api).
BACKFILL_JOB_TIPO_PEDIDO_ENRIQ = 'PEDIDO_ENRIQUECIMENTO'
# Backfill: itera HoraTagPlusNfeEmissao APROVADA, puxa
# pedido_os_vinculada via GET /nfes/{id} e enriquece HoraVenda com dados
# do GET /pedidos/{id} (vendedor, departamento, forma_pagamento detalhada).
BACKFILL_JOB_TIPO_PEDIDO_VENDAS_LEGADAS = 'PEDIDO_VENDAS_LEGADAS'
# Backfill: itera HoraVenda FATURADO sem `tagplus_pedido_id`, incluindo
# vendas legadas DANFE PDF (origem='DANFE') ou MANUAL sem entrada em
# HoraTagPlusNfeEmissao. Usa GET /nfes em janela de datas para descobrir
# o tagplus_nfe_id e dai segue mesmo fluxo de enriquecimento.

BACKFILL_JOB_TIPOS_VALIDOS = (
    BACKFILL_JOB_TIPO_NF,
    BACKFILL_JOB_TIPO_PEDIDO_ENRIQ,
    BACKFILL_JOB_TIPO_PEDIDO_VENDAS_LEGADAS,
)


class HoraTagPlusBackfillJob(db.Model):
    """Job de backfill TagPlus enfileirado em RQ (queue `hora_backfill`).

    Cada execucao do backfill cria 1 linha. O worker atualiza a linha
    incrementalmente para que a tela de detalhe mostre progresso em tempo
    real (auto-refresh AJAX).

    Estados:
      PENDENTE      — enfileirado, ainda nao pegou no worker.
      EM_PROGRESSO  — worker ativo, processando NFs.
      CONCLUIDO     — terminou OK (mesmo com erros parciais — ver `n_erro`).
      ERRO          — falha terminal (ex.: API TagPlus offline, exception
                       fora do try-per-NF).
      CANCELADO     — operador cancelou (futuro; por enquanto so PENDENTE).

    `relatorio` (JSON): snapshot final igual ao retornado por
    `executar_backfill` quando rodava sincrono.
    """
    __tablename__ = 'hora_tagplus_backfill_job'

    id = db.Column(db.Integer, primary_key=True)

    tipo = db.Column(
        db.String(30), nullable=False,
        default=BACKFILL_JOB_TIPO_NF, server_default=BACKFILL_JOB_TIPO_NF,
        index=True,
    )
    # NF: backfill original (importar_nfe_da_api).
    # PEDIDO_ENRIQUECIMENTO: enriquecimento via GET /pedidos/{id}.

    status = db.Column(
        db.String(20), nullable=False,
        default=BACKFILL_JOB_STATUS_PENDENTE, index=True,
    )

    # Filtros aplicados (echoa o input do operador).
    since = db.Column(db.Date, nullable=True)
    until = db.Column(db.Date, nullable=True)
    limite = db.Column(db.Integer, nullable=True)

    operador = db.Column(db.String(100), nullable=True)
    rq_job_id = db.Column(db.String(80), nullable=True, index=True)

    iniciado_em = db.Column(db.DateTime, nullable=True)
    finalizado_em = db.Column(db.DateTime, nullable=True)

    # Progresso (atualizado em batches pelo worker, sessao separada).
    total_listadas = db.Column(db.Integer, nullable=False, default=0)
    processadas = db.Column(db.Integer, nullable=False, default=0)

    # Contadores por status do importar_nfe_da_api.
    n_criado = db.Column(db.Integer, nullable=False, default=0)
    n_atualizado = db.Column(db.Integer, nullable=False, default=0)
    n_inalterado = db.Column(db.Integer, nullable=False, default=0)
    n_cancelado = db.Column(db.Integer, nullable=False, default=0)
    n_pulada_cancelada = db.Column(db.Integer, nullable=False, default=0)
    n_pulada_invalida = db.Column(db.Integer, nullable=False, default=0)
    n_dup = db.Column(db.Integer, nullable=False, default=0)
    n_erro = db.Column(db.Integer, nullable=False, default=0)
    n_divergencias = db.Column(db.Integer, nullable=False, default=0)

    ultimo_erro = db.Column(db.Text, nullable=True)

    # Relatorio final (mesmo dict retornado por executar_backfill sincrono).
    # Sanitizar com sanitize_for_json antes de atribuir.
    relatorio = db.Column(db.JSON, nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive, index=True)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    @property
    def percentual(self) -> int:
        """0..100. Quando total nao conhecido ainda, retorna 0."""
        if not self.total_listadas:
            return 0
        return min(100, int((self.processadas / self.total_listadas) * 100))

    @property
    def em_estado_final(self) -> bool:
        return self.status in BACKFILL_JOB_STATUS_FINAIS

    def __repr__(self) -> str:
        return (
            f'<HoraTagPlusBackfillJob id={self.id} status={self.status} '
            f'{self.processadas}/{self.total_listadas}>'
        )


class HoraTagPlusDepartamentoMap(db.Model):
    """De-para departamento.descricao TagPlus -> HoraLoja (loja fisica).

    REGRA FISCAL HORA: emitente das NFes e SEMPRE matriz (loja_id=1). O
    `departamento` no pedido TagPlus identifica a loja FISICA real onde a
    venda ocorreu (Praia Grande, Bragança, Tatuape...). Esse mapa permite
    UPDATE em massa em hora_venda.loja_id apos revisao humana.

    Workflow:
      1. Backfill coleta departamentos distintos (loja_id=NULL).
      2. UI /hora/tagplus/departamento-map: operador atribui loja para cada.
      3. UPDATE em massa: hora_venda.loja_id = mapa.loja_id WHERE
         hora_venda.tagplus_departamento = mapa.departamento_norm.
      4. Sem match: loja_id permanece como matriz (1) ate revisao posterior.
    """
    __tablename__ = 'hora_tagplus_departamento_map'

    id = db.Column(db.Integer, primary_key=True)
    departamento_norm = db.Column(db.String(200), nullable=False, unique=True)
    # Chave normalizada: lowercase + sem acentos + strip. Ex.: "praia grande".
    departamento_raw = db.Column(db.String(200), nullable=False)
    # Ultima forma vista em producao (TagPlus pode ter variacoes de digitacao).

    loja_id = db.Column(
        db.Integer, db.ForeignKey('hora_loja.id'),
        nullable=True, index=True,
    )
    # NULL = pendente de revisao. UPDATE so acontece quando preenchido.

    qtd_vendas_observadas = db.Column(db.Integer, nullable=False, default=0)
    # Atualizado pelo backfill a cada execucao (suporta novas vendas).

    revisado_por = db.Column(db.String(100), nullable=True)
    revisado_em = db.Column(db.DateTime, nullable=True)
    aplicado_em = db.Column(db.DateTime, nullable=True)
    # Marca timestamp do UPDATE em massa em hora_venda.loja_id.

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    loja = db.relationship('HoraLoja')

    def __repr__(self) -> str:
        return (
            f'<HoraTagPlusDepartamentoMap {self.departamento_norm!r} '
            f'-> loja={self.loja_id}>'
        )


class HoraDanfeParserAppend(db.Model):
    """Append-prompt versionado para o parser de DANFE/extrator de chassi/motor.

    Mecanismo de aprendizado por feedback: quando o parser erra a extracao
    de uma NF, o operador insere o valor correto e o sistema (Sonnet)
    recomenda uma instrucao curta a ser anexada ao prompt do LLM. Apos
    teste e aprovacao, a nova versao vira a `ativa`.

    Apenas UMA versao fica ativa por vez (`ativo=True`). Versoes antigas
    permanecem como historico — permitem rollback.

    Aplicado em:
      - `app/hora/services/tagplus/backfill_service._extrair_chassi_motor`
        (fallback LLM quando regex falha).
      - `app/hora/services/parsers/hora_danfe_parser.HoraDanfePDFParser`
        (subclasse do parser CarVia que prefixa o `texto_secao` com o
        append antes de delegar).
    """
    __tablename__ = 'hora_danfe_parser_append'

    id = db.Column(db.Integer, primary_key=True)
    versao = db.Column(db.Integer, nullable=False, unique=True)
    # Texto completo do append (acumulado — operador edita texto inteiro
    # ao gravar nova versao). Pode ter ate ~10k chars (Text).
    texto_append = db.Column(db.Text, nullable=False)
    # Trecho ACRESCENTADO em relacao a versao anterior (para auditoria).
    acrescimo_aplicado = db.Column(db.Text, nullable=True)
    # Motivo / contexto (ex: "NFe 538 — chassi vinha apos MOTOR sem prefixo Nº").
    motivo = db.Column(db.String(500), nullable=True)
    criado_por = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(
        db.DateTime, nullable=False, default=agora_utc_naive, index=True,
    )
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)

    def __repr__(self) -> str:
        return (
            f'<HoraDanfeParserAppend v{self.versao} '
            f'ativo={self.ativo} criado_em={self.criado_em}>'
        )

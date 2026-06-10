"""
Feature flags para o Agent SDK.
Todas iniciam False — ativar progressivamente apos testes.

Uso: definir variaveis de ambiente antes de iniciar o servidor.
Exemplo: AGENT_BUDGET_CONTROL=true flask run --debug
"""
import os

# ====================================================================
# Quick Wins
# ====================================================================

# Extended context window (1M tokens)
# Opus 4.8/4.7/4.6 e Sonnet 4.6: 1M tokens NATIVO (sem beta header necessário)
# Opus 4.8/4.7: 1M ao preço padrão $5/$25 per MTok, sem long-context premium
# Sonnet 4.5/4.0: precisam de beta header "context-1m-2025-08-07"
# Flag mantida apenas para documentação — modelos atuais usam 1M automaticamente
USE_EXTENDED_CONTEXT = os.getenv("AGENT_EXTENDED_CONTEXT", "false").lower() == "true"

# Controle de budget por request (disponivel desde SDK v0.1.6)
USE_BUDGET_CONTROL = os.getenv("AGENT_BUDGET_CONTROL", "true").lower() == "true"
MAX_BUDGET_USD = float(os.getenv("AGENT_MAX_BUDGET_USD", "5.0"))

# Context Clearing automatico — remove thinking/tool_uses antigos
# ATIVO por default: a Anthropic recomenda habilitar para conversas longas.
# O hook PreCompact (client.py) contém instruções explícitas de compactação.
# NOTA (2026-02): clear-thinking e clear-tool-uses foram promovidos a GA.
#   Beta headers removidos — flag controla apenas log/documentação.
# Para desativar: AGENT_CONTEXT_CLEARING=false
USE_CONTEXT_CLEARING = os.getenv("AGENT_CONTEXT_CLEARING", "true").lower() == "true"

# Prompt Caching — economia de 50-90% tokens input
# O system_prompt.md do agente e extenso (~8K tokens)
# NOTA (2026-02): prompt-caching foi promovido a GA.
#   Beta header removido — flag controla apenas log/documentação.
USE_PROMPT_CACHING = os.getenv("AGENT_PROMPT_CACHING", "true").lower() == "true"

# ====================================================================
# Architecture + Seguranca
# ====================================================================

# Self-correction — reescrito para Sonnet 4.6 (prompt específico para tabelas numéricas)
# Histórico: Haiku gerava falsos positivos com escopo amplo. Prompt agora valida APENAS
# inconsistências aritméticas em respostas com tabelas numéricas (threshold 500 chars).
# DESATIVADO: gerava observacoes que confundiam usuarios sem beneficio claro.
# Para reativar: AGENT_SELF_CORRECTION=true
USE_SELF_CORRECTION = os.getenv("AGENT_SELF_CORRECTION", "false").lower() == "true"

# Prompt Cache Optimization — extrai variáveis dinâmicas do system prompt
# ({data_atual}, {usuario_nome}, {user_id}) para injeção via UserPromptSubmit hook.
# System prompt fica estático entre usuários e turnos → prompt caching hits no CLI.
# Depende de USE_CUSTOM_SYSTEM_PROMPT=true para ter efeito.
# Rollback: AGENT_PROMPT_CACHE_OPTIMIZATION=false
USE_PROMPT_CACHE_OPTIMIZATION = os.getenv("AGENT_PROMPT_CACHE_OPTIMIZATION", "true").lower() == "true"

# ====================================================================
# Melhorias de Contexto e Memoria (P0)
# ====================================================================

# Structured Pre-Compaction — salva contexto logistico detalhado antes de compactacao
# Instrui modelo a salvar pedidos, decisoes, tarefas em formato XML estruturado
# ATIVO por default: melhoria direta sem risco, substitui instrucao generica por estruturada
USE_STRUCTURED_COMPACTION = os.getenv("AGENT_STRUCTURED_COMPACTION", "true").lower() == "true"

# Session Summary — gera resumo estruturado ao final de cada interacao
# Usa Sonnet para extrair pedidos, decisoes, tarefas e alertas da conversa
# Custo: ~$0.003 por resumo (Sonnet: $3/1M input + $15/1M output)
# ATIVO por default: migration ja aplicada, implementacao estavel
USE_SESSION_SUMMARY = os.getenv("AGENT_SESSION_SUMMARY", "true").lower() == "true"

# Threshold de mensagens para trigger de sumarizacao
# Sumariza quando message_count >= threshold e summary esta stale (delta >= threshold)
# Reduzido de 5→3 em 2026-04-12 (v2.2): auditoria mostrou que 57% das sessoes
# em 30d tinham <5 msgs (especialmente Teams curto), perdendo rolling window.
# Custo marginal: ~$0.36/mes. Sessoes 1-2 msgs continuam sem summary (trivial).
SESSION_SUMMARY_THRESHOLD = int(os.getenv("AGENT_SESSION_SUMMARY_THRESHOLD", "3"))

# ====================================================================
# Melhorias de UX (P1)
# ====================================================================

# Prompt Suggestions — gera 2-3 sugestoes contextuais apos cada resposta
# Usa Sonnet para sugestoes relevantes ao dominio logistico
# Custo: ~$0.003 por chamada (~500 tokens input, ~200 output)
# ATIVO por default: roda em background, nao bloqueia resposta.
# Para desativar: AGENT_PROMPT_SUGGESTIONS=false
USE_PROMPT_SUGGESTIONS = os.getenv("AGENT_PROMPT_SUGGESTIONS", "true").lower() == "true"

# Sentiment Detection — detecta frustração do operador e ajusta tom da resposta
# Heuristicas locais (sem chamada API): mensagens curtas, repetidas, marcadores explicitos
# Custo: zero (deteccao local por regex/heuristica)
# Default false: ativar apos validar que os sinais de frustracao sao precisos
USE_SENTIMENT_DETECTION = os.getenv("AGENT_SENTIMENT_DETECTION", "true").lower() == "true"

# Pattern Learning — analisa sessoes historicas e identifica padroes recorrentes
# Usa Sonnet para detectar: clientes frequentes, queries repetidas, preferencias
# Salva padroes em /memories/learned/patterns.xml para uso proativo
# Custo: ~$0.006 por analise (~4K tokens input, ~800 output Sonnet)
# Trigger: a cada N sessoes do usuario (default 10)
# Default false: requer historico suficiente de sessoes para ser util
USE_PATTERN_LEARNING = os.getenv("AGENT_PATTERN_LEARNING", "true").lower() == "true"

# Numero de sessoes entre analises de padrao
# Analisa quando total_sessions % threshold == 0
PATTERN_LEARNING_THRESHOLD = int(os.getenv("AGENT_PATTERN_LEARNING_THRESHOLD", "10"))

# Behavioral Profile — gera user.xml (Tier 1) com perfil comportamental
# Reutiliza mesma chamada Sonnet do patterns (zero custo adicional quando coincidem)
# Threshold menor que patterns (3 vs 10) para perfil mais rapido.
# Reduzido de 5→3 em 2026-04-12 (v2.2): auditoria mostrou que users low-freq
# (Jessica, Thamires, Marcus Souza, Nicoly) tinham 2-4 sessoes desde ultimo
# update mas nunca atingiam 5 — user.xml stale indefinidamente.
USE_BEHAVIORAL_PROFILE = os.getenv("AGENT_BEHAVIORAL_PROFILE", "true").lower() == "true"
BEHAVIORAL_PROFILE_THRESHOLD = int(os.getenv("AGENT_BEHAVIORAL_PROFILE_THRESHOLD", "3"))

# Thresholds adaptativos para profile — disparam atualizacao mesmo com poucas sessoes
# Sessao longa (>= N msgs) desde ultimo update de user.xml → trigger imediato
# Sessao cara (>= $X) desde ultimo update → trigger imediato
# Resolve: usuarios low-frequency com sessoes densas ficavam com profile stale
PROFILE_LONG_SESSION_THRESHOLD = int(os.getenv("AGENT_PROFILE_LONG_SESSION_THRESHOLD", "20"))
PROFILE_COST_THRESHOLD = float(os.getenv("AGENT_PROFILE_COST_THRESHOLD", "5.0"))

# Extracao pos-sessao de conhecimento organizacional (PRD v2.1)
# Analisa TODAS as mensagens via Sonnet para extrair: definicoes de termos,
# cargos, regras de negocio, correcoes factuais. Salva como memorias empresa (user_id=0).
# Custo: ~$0.003 por execucao (Sonnet, contexto completo). Volume baixo (~4 sessoes/dia).
# Trigger: a cada exchange (min 3 msgs OU cost >= $0.10), roda em daemon thread (background).
# A ultima execucao de cada sessao contem toda a conversa (= extracao de fim de sessao).
USE_POST_SESSION_EXTRACTION = os.getenv("AGENT_POST_SESSION_EXTRACTION", "true").lower() == "true"

# Minimo de mensagens para iniciar extracao (evita rodar em sessoes triviais)
POST_SESSION_EXTRACTION_MIN_MESSAGES = int(os.getenv("AGENT_POST_SESSION_EXTRACTION_MIN_MESSAGES", "3"))

# Threshold de custo: sessoes com custo >= este valor disparam extracao
# MESMO se message_count < threshold. Resolve sessoes curtas mas substantivas
# (ex: 2 msgs + 40 tool calls = $0.54, message_count=2 mas conteudo rico).
POST_SESSION_COST_THRESHOLD = float(os.getenv("AGENT_POST_SESSION_COST_THRESHOLD", "0.10"))

# Extracao pos-sessao de insights PESSOAIS (complementar a empresa)
# Analisa mensagens via Sonnet para extrair: correcoes, preferencias, expertise do usuario.
# Salva como memorias PESSOAIS (user_id do usuario, NAO user_id=0).
# Resolve: R0 auto-save depende do modelo, que frequentemente nao chama save_memory.
# Custo: ~$0.003 por execucao (Sonnet). Volume baixo (~4 sessoes/dia).
# Threshold maior que empresa (10 vs 3): insights pessoais precisam de mais contexto
# e rodar a cada turno desperdicaria tokens em sessoes curtas.
USE_POST_SESSION_PERSONAL_EXTRACTION = os.getenv("AGENT_POST_SESSION_PERSONAL_EXTRACTION", "true").lower() == "true"
POST_SESSION_PERSONAL_EXTRACTION_MIN_MESSAGES = int(os.getenv("AGENT_POST_SESSION_PERSONAL_MIN_MESSAGES", "10"))

# ====================================================================
# Dashboard e Analytics (P2)
# ====================================================================

# Agent Insights Dashboard — pagina admin com analytics de uso do agente
# Mostra: top queries, custos por usuario, tools mais usadas, erros, duracao
# Acesso: apenas usuarios com perfil 'administrador'
# ATIVO por default: dashboard estavel, acesso restrito a admin
USE_AGENT_INSIGHTS = os.getenv("AGENT_INSIGHTS", "true").lower() == "true"

# Reversibility Check — classifica acoes por reversibilidade e pede confirmacao extra
# Intercepta Skills e Bash que podem executar acoes destrutivas (criar separacao, modificar dados)
# Emite evento SSE 'destructive_action_warning' para dialog de confirmacao no frontend
# Default false: ativar apos validar que a classificacao nao gera falsos positivos
USE_REVERSIBILITY_CHECK = os.getenv("AGENT_REVERSIBILITY_CHECK", "true").lower() == "true"

# Friction Analysis — analisa sessoes e identifica pontos de friccao
# Detecta: queries repetidas (operador nao obteve resposta), mensagens curtas apos erro,
# sessoes abandonadas, uso excessivo de tools sem resultado
# Integrado ao Dashboard de Insights (P2-2)
# ATIVO por default: historico suficiente acumulado, integrado ao Insights
USE_FRICTION_ANALYSIS = os.getenv("AGENT_FRICTION_ANALYSIS", "true").lower() == "true"

# ====================================================================
# Memoria Persistente (P0)
# ====================================================================

# Auto-inject de memorias do usuario via UserPromptSubmit hook
# Carrega memorias do banco e injeta como additionalContext no inicio de cada turno
# Garante que o modelo SEMPRE tem contexto de memorias, mesmo se nao chamar tools
# ATIVO por default: feature core do agente, kill switch para rollback
# Para desativar: AGENT_AUTO_MEMORY_INJECTION=false
USE_AUTO_MEMORY_INJECTION = os.getenv("AGENT_AUTO_MEMORY_INJECTION", "true").lower() == "true"

# Threshold minimo de similaridade para injecao de memorias semanticas
# Memorias com score abaixo deste valor NAO sao injetadas (Tier 2)
# Memorias protegidas (user.xml, preferences.xml) sao SEMPRE injetadas (Tier 1)
# Ajustar em producao sem deploy: env AGENT_MEMORY_MIN_SIMILARITY
# CALIBRADO POR MEDICAO (2026-06-10, voyage-4-large): 0.40 = cobertura 18/20
# turnos com precision@4 0.673. ESCALA NAO TRANSFERE entre modelos de
# embedding — recalibrar com o harness do relatorio
# precision_at_k_baseline_2026-06-10.md ao trocar VOYAGE_MEMORY_MODEL
# (o 0.55 herdado matou o retrieval por semanas; nao repetir).
MEMORY_INJECTION_MIN_SIMILARITY = float(os.getenv("AGENT_MEMORY_MIN_SIMILARITY", "0.40"))

# User.xml Pointer (v2.2, 2026-04-12) — Camada 2 da Mudanca 4
# Quando user.xml > THRESHOLD e modelo tem budget finito (Sonnet/Haiku),
# injetar apenas <resumo> + <contextualizacao> + ponteiro instruindo o
# agente a chamar view_memories para detalhes operacionais.
# Evidencia: 5/12 users excedem 67% do budget Sonnet (6000) apenas com
# Tier 1 (user.xml + preferences.xml) — Gabriella e Marcus excedem 100%
# e Tier 2 fica zerado sistematicamente.
# Default false: ativar apos validar que agente chama view_memories
# corretamente (verificar via logs [MEMORY_INJECT] e amostras reais).
# Camada 1 (guidance no prompt gerador, em pattern_analyzer.py) e a
# solucao de causa raiz — este ponteiro cobre periodo de transicao.
USE_USER_XML_POINTER = os.getenv("AGENT_USER_XML_POINTER", "false").lower() == "true"
USER_XML_POINTER_THRESHOLD = int(os.getenv("AGENT_USER_XML_POINTER_THRESHOLD", "3000"))

# F6 PAD-CTX (2026-06-10): cap de blocos FIXOS do hook (tier1 + user_rules).
# Evidencia tripla PROD (users 1/18/82): user_rules 6.2K + tier1 7.6-9.1K
# estouravam sozinhos o teto de 15K e a politica de overflow F4 cortava TODO
# o adaptativo (tier2/directives organicas/routing) — os usuarios mais ativos
# eram os que nada recebiam do retrieval semantico. Solucao: destilar/ponteirar
# (como o Tier 2 faz com 300c), NUNCA cortar — intocaveis preservados.
# Caps em memory_injection.py (TIER1_PATH_CAPS, USER_RULE_CHAR_CAP), calibrados
# em dados PROD 2026-06-10. Kill-switch: AGENT_FIXED_BLOCKS_CAP=false restaura
# os blocos fixos INTEGRAIS (sem destilado/ponteiro). NOTA (review F6): a
# exclusao dos paths Tier 1 do canal <user_rules> (fix da dupla injecao) e
# INCONDICIONAL — nao volta com a flag off; o conteudo segue integro no Tier 1.
AGENT_FIXED_BLOCKS_CAP = os.getenv("AGENT_FIXED_BLOCKS_CAP", "true").lower() == "true"

# Operational Directives (v2.2, 2026-04-12) — Mudanca 1
# Promove heuristicas empresa nivel 5 (importance >= 0.7) de contexto
# passivo (<user_memories>) para diretriz operacional obrigatoria
# (<operational_directives>). O system_prompt.md instrui o agente a
# tratar este bloco como regra, nao como referencia.
# Evidencia: meta-heuristica id=300 "Memorias de usuario devem funcionar
# como protocolo ativo" tem 12% efetividade. O proprio sistema documenta
# que memorias sao lidas mas nao obedecidas. Causa e estrutural: onde
# a memoria aparece no prompt. Solucao deterministica (zero LLM).
# Inspirado na arquitetura CLAUDE.md do Claude Code (setting_sources).
# Default false: ativar apos revisao manual das candidatas filtradas.
USE_OPERATIONAL_DIRECTIVES = os.getenv("AGENT_OPERATIONAL_DIRECTIVES", "false").lower() == "true"
MANDATORY_IMPORTANCE_THRESHOLD = float(os.getenv("AGENT_MANDATORY_IMPORTANCE_THRESHOLD", "0.7"))
MANDATORY_MAX_COUNT = int(os.getenv("AGENT_MANDATORY_MAX_COUNT", "5"))

# Consolidacao periodica de memorias via Sonnet
# Quando usuario excede thresholds, consolida memorias redundantes em resumos compactos
# Custo: ~$0.006 por consolidacao (~4K input + ~800 output Sonnet)
# Frequencia: ~1x por semana por usuario ativo
# ATIVO por default: mantem memorias compactas sem intervencao manual
USE_MEMORY_CONSOLIDATION = os.getenv("AGENT_MEMORY_CONSOLIDATION", "true").lower() == "true"

# Thresholds para trigger de consolidacao
# Consolida quando: total_arquivos > FILES OU total_chars > CHARS
MEMORY_CONSOLIDATION_THRESHOLD_FILES = int(os.getenv("AGENT_MEMORY_CONSOLIDATION_FILES", "15"))
MEMORY_CONSOLIDATION_THRESHOLD_CHARS = int(os.getenv("AGENT_MEMORY_CONSOLIDATION_CHARS", "6000"))

# Minimo de arquivos em um diretorio para ser candidato a consolidacao
MEMORY_CONSOLIDATION_MIN_GROUP = int(os.getenv("AGENT_MEMORY_CONSOLIDATION_MIN_GROUP", "3"))

# Cold tier — sanitizacao automatica de memorias ineficazes
# Move para cold (nao injetadas, mas buscaveis) memorias com eficacia abaixo do threshold
# Eficacia = effective_count / usage_count (0.10 = 10%)
# Criterio: usage >= MIN_USAGE E eficacia < MAX_EFFICACY
# Rollback: AGENT_COLD_MOVE=false ou ajustar thresholds sem deploy
USE_COLD_MOVE = os.getenv("AGENT_COLD_MOVE", "true").lower() == "true"
COLD_MOVE_MIN_USAGE = int(os.getenv("AGENT_COLD_MOVE_MIN_USAGE", "20"))
COLD_MOVE_MAX_EFFICACY = float(os.getenv("AGENT_COLD_MOVE_MAX_EFFICACY", "0.10"))

# Sanitizar memorias empresa (user_id=0) com mesmos criterios
# Desativar se empresa mover memorias demais: AGENT_COLD_MOVE_EMPRESA=false
USE_COLD_MOVE_EMPRESA = os.getenv("AGENT_COLD_MOVE_EMPRESA", "true").lower() == "true"

# Garbage collection de memorias cold > 90 dias (MEMORY_PROTOCOL.md)
# Remove permanentemente memorias ja classificadas como cold sem atividade por 90+ dias
# Independente de USE_COLD_MOVE — pausar classificacao nao impede limpeza de memorias ja frias
# Rollback: AGENT_COLD_GC=false
USE_COLD_GC = os.getenv("AGENT_COLD_GC", "true").lower() == "true"
COLD_GC_MAX_AGE_DAYS = int(os.getenv("AGENT_COLD_GC_MAX_AGE_DAYS", "90"))

# Merge inteligente de memorias empresa via Sonnet (substitui append cego)
# Quando true: _try_enrich_existing() usa Sonnet para fundir old+new em versao unica
# Quando false: fallback para append legado (old + "<!-- Enriquecido em -->" + new)
# Custo: ~$0.002 por merge. Frequencia: ~1-3x/semana (so quando enrichment dispara)
# Rollback instantaneo: AGENT_MERGE_ENRICHMENT=false
USE_MERGE_ENRICHMENT = os.getenv("AGENT_MERGE_ENRICHMENT", "true").lower() == "true"

# Briefing Inter-Sessão — injeta eventos entre sessões (erros Odoo, imports, alertas de memória)
# Queries SQL leves, zero custo LLM. Injetado como Tier 0b no início da sessão.
# Default true (env AGENT_INTERSESSION_BRIEFING)
USE_INTERSESSION_BRIEFING = os.getenv("AGENT_INTERSESSION_BRIEFING", "true").lower() == "true"

# ====================================================================
# RAG Semantico (Fase 4)
# ====================================================================

# Embedding inline de turns de sessão: gera embedding em tempo real ao salvar cada turn
# Quando true: routes.py chama _embed_session_turn_best_effort() on-save
# Quando false: embedding só via batch indexer manual (session_turn_indexer.py)
# ATIVO por default (QW-3): batch indexer complementa, mas inline garante cobertura real-time
#
# NOTA: Esta flag controla ESCRITA de embeddings. A LEITURA é controlada por:
#   app/embeddings/config.py:SESSION_SEMANTIC_SEARCH (env: SESSION_SEMANTIC_SEARCH, default true)
# Ambas devem estar true para busca semântica de sessões funcionar end-to-end.
# UNIFICADO (GAP 5): Usa mesma env var que config.py (SESSION_SEMANTIC_SEARCH) para evitar
# dessincronização entre write e read path ao setar apenas uma env var.
USE_SESSION_TURN_EMBEDDING = os.getenv("SESSION_SEMANTIC_SEARCH", "true").lower() == "true"

# Alias legado (compatibilidade com código existente que importa USE_SESSION_SEMANTIC_SEARCH)
USE_SESSION_SEMANTIC_SEARCH = USE_SESSION_TURN_EMBEDDING

# REMOVIDO: USE_MEMORY_SEMANTIC_SEARCH — unificado em app.embeddings.config.MEMORY_SEMANTIC_SEARCH
# Env var: MEMORY_SEMANTIC_SEARCH (default true)
# Ver: app/embeddings/config.py linha 106

# ====================================================================
# File Attachments (Fase B — 2026-04-14)
# ====================================================================

# PDF strategy: native | extract | hybrid
# - native (default): PDF vira document block nativo do Claude (SDK 0.1.55+).
#   OCR, tabelas e layout sao preservados. Maior custo de tokens por pagina.
# - extract: PDF e extraido localmente via pdfplumber → texto plano injetado
#   no prompt. Menor custo, sem OCR, perde layout complexo.
# - hybrid: native para PDFs pequenos (<= 4MB), extract para grandes (> 4MB).
#   Otimiza custo sem perder qualidade nos documentos mais comuns.
# Rollback instantaneo via env var — nao precisa redeploy.
# Env var: AGENT_PDF_STRATEGY (segue convencao AGENT_* do resto do arquivo).
_VALID_PDF_STRATEGIES = {'native', 'extract', 'hybrid'}
AGENTE_PDF_STRATEGY = os.getenv("AGENT_PDF_STRATEGY", "native").lower()
if AGENTE_PDF_STRATEGY not in _VALID_PDF_STRATEGIES:
    import logging as _feature_flags_logging
    _feature_flags_logging.getLogger('sistema_fretes').warning(
        f"[FEATURE_FLAGS] AGENT_PDF_STRATEGY invalido: "
        f"{AGENTE_PDF_STRATEGY!r}. Usando 'native'. "
        f"Validos: {sorted(_VALID_PDF_STRATEGIES)}"
    )
    AGENTE_PDF_STRATEGY = 'native'


# ====================================================================
# Teams Bot
# ====================================================================

# Modelo padrao para o bot do Teams.
# Opus 4.8 (28/05/2026): mesma superficie de API que 4.7 (sem breaking change),
#   mesmo preco $5/$25 per 1M tokens, narrativa mais detalhada, mais deliberado.
# Opus 4.7 (16/04/2026): novo tokenizer (0-35% mais tokens por texto), stricter
#   effort calibration, comportamento mais literal.
# Opus 4.6 (legado): ~91s por resposta com tools.
# Sonnet 4.6: ~15-25s por resposta com tools, custo $3/$15 per 1M tokens.
# Rollback instantaneo: TEAMS_DEFAULT_MODEL=claude-opus-4-7 (ou =claude-opus-4-6)
TEAMS_DEFAULT_MODEL = os.getenv("TEAMS_DEFAULT_MODEL", "claude-opus-4-8")

# Modo assincrono para o bot do Teams
# Quando true: retorna task_id imediatamente, processa em daemon thread, Azure Function faz polling
# Quando false: fluxo sincrono legado (resposta direta na mesma request)
TEAMS_ASYNC_MODE = os.getenv("TEAMS_ASYNC_MODE", "true").lower() == "true"

# Timeout para AskUserQuestion no Teams (segundos)
# O usuario tem este tempo para responder o Adaptive Card antes de timeout.
# Default 180s (3 min) — humano precisa ler o card + render/poll do Teams; 120s
# estourava em perguntas multi-parte (2026-06-06). Alinhado ao web (AGENT_ASK_USER_TIMEOUT_WEB).
TEAMS_ASK_USER_TIMEOUT = int(os.getenv("TEAMS_ASK_USER_TIMEOUT", "180"))

# Progressive streaming: flush texto parcial ao DB durante processamento
# Quando true: polling retorna resposta_parcial enquanto status='processing'
# Quando false: comportamento atual (resposta so no final)
TEAMS_PROGRESSIVE_STREAMING = os.getenv("TEAMS_PROGRESSIVE_STREAMING", "true").lower() == "true"

# Intervalo em segundos entre flushes de texto parcial ao DB
TEAMS_STREAM_FLUSH_INTERVAL = float(os.getenv("TEAMS_STREAM_FLUSH_INTERVAL", "4.0"))

# Smart model routing: mensagens simples usam Sonnet (15-25s), complexas Opus (60-90s)
# Desativar para voltar ao comportamento anterior (tudo Opus)
TEAMS_SMART_MODEL_ROUTING = os.getenv("TEAMS_SMART_MODEL_ROUTING", "true").lower() == "true"

# Modelo rápido para mensagens simples (usado quando SMART_MODEL_ROUTING=true)
TEAMS_FAST_MODEL = os.getenv("TEAMS_FAST_MODEL", "claude-sonnet-4-6")

# Fase 1 (2026-04-21): routing programatico tambem no canal Web.
# Patterns compartilhados via app/agente/sdk/model_router.py.
# Motivacao: 21 sessoes > $10 USD tinham padrao estruturado que podia ir pra Sonnet.
# Desabilitar via env var: AGENT_WEB_SMART_MODEL_ROUTING=false
USE_WEB_SMART_MODEL_ROUTING = os.getenv(
    "AGENT_WEB_SMART_MODEL_ROUTING", "true"
).lower() == "true"

# Modelo rapido para Web quando router decide rebaixar.
# Default Sonnet 4.6 (mesmo do Teams). Rollback: deixar Opus setando igual.
WEB_FAST_MODEL = os.getenv("AGENT_WEB_FAST_MODEL", "claude-sonnet-4-6")

# FASE 1 (plano 2026-06-06-reducao-custo-agente-fast-path): fast-path
# DETERMINISTICO do baseline de conciliacao (Marcus). Quando "atualizar baseline"
# e' trivial (curto, sem data/variacao), roda o script gerar_baseline.py SEM LLM
# (nem Opus nem Sonnet) e responde com link + tabelas. Qualquer variacao ou falha
# cai no fluxo normal do agente (R-EXEC-6 fallback). Implementacao:
# app/agente/sdk/baseline_fastpath.py (Teams: services.py; Web: routes/chat.py).
# Rollback total: AGENT_BASELINE_FASTPATH=false.
AGENT_BASELINE_FASTPATH = os.getenv(
    "AGENT_BASELINE_FASTPATH", "true"
).lower() == "true"

# FASE 3 do mesmo plano (2026-06-08): "vincular/desvincular pedido X na nota Y"
# (Gabriella, Teams) resolvido por roteamento DETERMINISTICO (regex N0 + Haiku N1)
# reusando validar_dfe/consolidar_pos/reverter_consolidacao — SEM o subagente
# gestor-recebimento (Opus xhigh). Anomalia (status!=aprovado, PO diverge, NF
# ambigua) ou falha cai no fluxo LLM normal (N2). Impl: app/agente/sdk/
# vinculacao_fastpath.py + app/recebimento/services/vinculacao_rapida_service.py.
# Rollback total: AGENT_VINCULACAO_FASTPATH=false.
AGENT_VINCULACAO_FASTPATH = os.getenv(
    "AGENT_VINCULACAO_FASTPATH", "true"
).lower() == "true"

# ====================================================================
# Session Lifecycle (Fase 2, 2026-04-21)
# ====================================================================
# TTL idle para sessoes do Teams. Antes hardcoded 4h em app/teams/services.py.
# Extraido para env var com default 2h — evita acumular cache creation em
# sessoes de 9 dias (caso Marcus, $151.80) ou 7h (caso Gabriella, $27.88).
# Usuario idle por > TTL: retomar cria nova session_id (cache reinicia limpo).
# Rollback para comportamento anterior: TEAMS_SESSION_TTL_HOURS=4
TEAMS_SESSION_TTL_HOURS = int(os.getenv("TEAMS_SESSION_TTL_HOURS", "2"))

# Idle threshold para sessoes Web. Novo na Fase 2.
# Diferente do Teams: Web nao rotaciona automaticamente — apenas emite SSE
# 'session_rotated' com novo session_id; frontend troca no localStorage.
# Disabled (valor 0): comportamento legado (sessao persiste indefinidamente).
WEB_SESSION_IDLE_HOURS = int(os.getenv("AGENT_WEB_SESSION_IDLE_HOURS", "2"))

# Feedback visual de tool calls: mostra "Consultando dados..." durante execução de tools
# Desativar se causar flickering ou problemas visuais no Teams
TEAMS_TOOL_STATUS_FEEDBACK = os.getenv("TEAMS_TOOL_STATUS_FEEDBACK", "true").lower() == "true"

# ====================================================================
# Hooks Expandidos (P3)
# ====================================================================

# Expanded Hooks — adiciona hooks Stop e UserPromptSubmit alem dos 3 existentes
# Stop: loga metricas finais da sessao (tokens, custo, duracao, tools usadas)
# UserPromptSubmit: pode enriquecer o prompt do usuario antes de processar
# ATIVO por default: overhead minimo (apenas logging).
# Para desativar: AGENT_EXPANDED_HOOKS=false
USE_EXPANDED_HOOKS = os.getenv("AGENT_EXPANDED_HOOKS", "true").lower() == "true"

# ====================================================================
# Stderr Callback (SDK Debug Output)
# ====================================================================
# Quando true: registra stderr callback no ClaudeAgentOptions para capturar
# debug output do CLI subprocess em real-time. Emite como SSE event 'stderr'
# para o debug panel no frontend (admin-only, requer debug_mode=true).
# Quando false: stderr capturado apenas em ProcessError (comportamento original).
# Desativar se causar overhead perceptível no streaming.
USE_STDERR_CALLBACK = os.getenv("AGENT_STDERR_CALLBACK", "true").lower() == "true"

# ====================================================================
# Async Streaming (migração incremental)
# ====================================================================
# Quando true: usa implementação async nativa para streaming SSE
# Quando false: usa bridge Thread+Queue+asyncio.run (legado)
USE_ASYNC_STREAMING = os.getenv("ASYNC_STREAMING", "true").lower() == "true"
# ====================================================================
# Persistent SDK Client (migração query() → ClaudeSDKClient)
# ====================================================================
# Quando true: usa ClaudeSDKClient persistente (subprocess vivo entre turnos)
#   - Pool por sessão no daemon thread com event loop persistente
#   - ~2x menor latência (sem overhead spawn/destroy CLI por turno)
#   - Habilita interrupt, model switch, MCP server recovery
# Quando false: usa query() standalone (status quo — spawn + destroy por turno)
# Rollback instantâneo: AGENT_PERSISTENT_SDK_CLIENT=false + restart
# Ref: .claude/references/ROADMAP_SDK_CLIENT.md
USE_PERSISTENT_SDK_CLIENT = os.getenv("AGENT_PERSISTENT_SDK_CLIENT", "true").lower() == "true"

# Timeout em segundos para idle clients no pool (disconnect automático)
# Libera recursos de clients sem atividade por este período
PERSISTENT_CLIENT_IDLE_TIMEOUT = int(os.getenv("AGENT_CLIENT_IDLE_TIMEOUT", "900"))  # 15 min

# Intervalo em segundos entre limpezas de clients idle
PERSISTENT_CLIENT_CLEANUP_INTERVAL = int(os.getenv("AGENT_CLIENT_CLEANUP_INTERVAL", "60"))  # 1 min

# ====================================================================
# AskUserQuestion cross-worker (Redis-backed)
# ====================================================================
# Habilita backing Redis para pending_questions (registry + pub/sub wakeup).
# Resolve bug R-MULTIWORKER (2026-05-12): com 4 workers gunicorn, POST
# /api/user-answer pode cair em worker diferente do que registrou a pergunta.
# Sem Redis, ~75% das respostas viravam 404 e o agente esperava ate timeout.
# Quando true: usa Redis SETEX + PUBLISH/SUBSCRIBE para sincronizar workers.
# Quando false: comportamento legacy (memory-only, falha cross-worker).
# Rollback instantaneo: AGENT_REDIS_PENDING_QUESTIONS=false + restart.
USE_REDIS_PENDING_QUESTIONS = os.getenv(
    "AGENT_REDIS_PENDING_QUESTIONS", "true"
).lower() == "true"

# ====================================================================
# Custom System Prompt (Prompt Architecture v2)
# ====================================================================

# Substitui preset claude_code por preset_operacional.md + system_prompt.md
# Quando true: system_prompt = preset_operacional.md + system_prompt.md (string pura)
# Quando false: system_prompt = {preset: claude_code, append: system_prompt.md} (original)
# ATIVO: preset_operacional.md substitui claude_code preset
# Rollback instantaneo: AGENT_CUSTOM_SYSTEM_PROMPT=false
USE_CUSTOM_SYSTEM_PROMPT = os.getenv("AGENT_CUSTOM_SYSTEM_PROMPT", "true").lower() == "true"

# ====================================================================
# Debug Mode (Admin)
# ====================================================================

# Debug Mode — permite admin desbloquear tabelas internas e memorias cross-user
# Controlado por toggle na UI, validado server-side (perfil=administrador)
# Default true: feature disponivel, mas requer ativacao explicita pelo admin
USE_DEBUG_MODE = os.getenv("AGENT_DEBUG_MODE", "true").lower() == "true"

# ====================================================================
# Improvement Dialogue (Loop Agent SDK <-> Claude Code)
# ====================================================================

# Habilita dialogo versionado de melhoria continua.
# Agent SDK gera sugestoes pos-sessao via Sonnet (~$0.005/sessao).
# Claude Code (D8 cron diario) avalia, implementa e responde.
# Agent SDK verifica respostas via intersession briefing.
# Default false: ativacao gradual apos testes.
USE_IMPROVEMENT_DIALOGUE = os.getenv("AGENT_IMPROVEMENT_DIALOGUE", "false").lower() == "true"

# F4.1 PAD-CTX (2026-06-09): controle SEPARADO para a INJECAO de
# improvement_responses no briefing de boot (AGENT_IMPROVEMENT_DIALOGUE segue
# governando apenas o DIALOGO D8). Default OFF — responses chegam ao agente
# via excecao condicional por skill (F4.5, PreToolUse Skill) ou tela admin.
# Lida via os.getenv no intersession_briefing (runtime, testavel via setenv).
AGENT_IMPROVEMENT_INJECT_BOOT = os.getenv("AGENT_IMPROVEMENT_INJECT_BOOT", "false").lower() == "true"

# Minimo de mensagens na sessao para gerar sugestoes de melhoria
IMPROVEMENT_DIALOGUE_MIN_MESSAGES = int(os.getenv("AGENT_IMPROVEMENT_MIN_MESSAGES", "3"))

# ====================================================================
# User Rules Channel (Memory v3 — 3 canais de memoria)
# ====================================================================

# Novo canal L1: Injecao obrigatoria de regras do usuario (priority=mandatory)
# Quando true: _build_user_rules() e chamado no inicio da injecao de memoria
# Injeta <user_rules priority="mandatory"> como PRIMEIRO bloco em tier0_parts
# Sempre injetado sem consumir budget — priority maxima no prompt.
# Default ON (2026-06-02): canal aditivo e quase inocuo ate a promocao (Fase 2 do
# loop corretivo) encher o canal — quem promove a 'mandatory' passa pelo gate R9+A3.
# Manter ON evita a feature virar zumbi (construida, desligada e esquecida).
USE_USER_RULES_CHANNEL = os.getenv("AGENT_USER_RULES_CHANNEL", "true").lower() == "true"

# Cap de regras no canal duro <user_rules>, ordenado por correction_count DESC.
# Adesao a instrucoes despenca >100-150 regras (IFScale arXiv:2507.11538) — o canal
# duro deve ser pequeno e curado. Ver eixos/G-memoria-pessoal.md + plano loop corretivo.
MANDATORY_RULES_MAX_COUNT = int(os.getenv("AGENT_MANDATORY_RULES_MAX_COUNT", "12"))

# Fase 2 do loop corretivo — promocao de correcao PESSOAL recorrente a 'mandatory'.
# Roda no batch DIARIO (modulo 32 directive_promotion), nao em script one-shot — assim a
# licao do usuario e promovida automaticamente e nao fica esquecida. Correcao vem do usuario
# (feedback humano confiavel); o filtro e a REINCIDENCIA (correction_count >= threshold),
# nao o gate Odoo. Default ON (evita feature zumbi) — seguro: idempotente + cap na injecao.
AGENT_CORRECTION_PROMOTION = os.getenv("AGENT_CORRECTION_PROMOTION", "true").lower() == "true"
AGENT_CORRECTION_PROMOTION_THRESHOLD = int(os.getenv("AGENT_CORRECTION_PROMOTION_THRESHOLD", "2"))

# Fase 3.4A do loop corretivo — posiciona <user_rules> no TOPO ABSOLUTO do contexto
# injetado (antes de <user_memories>), nao mais na cauda (apos o footer). A Fase 0
# (AgingBench) provou que a regra no topo rende muito mais (P3=89% vs P1=0%). Default ON:
# e o coracao da cura de RETRIEVAL; aditivo (so reordena, nao adiciona/remove conteudo) e
# reversivel por flag. OFF reproduz o comportamento legado (regras na cauda).
USE_USER_RULES_TOP = os.getenv("AGENT_USER_RULES_TOP", "true").lower() == "true"

# Fase 3.4B do loop corretivo — soma um eixo de RECORRENCIA (correction_count) ao composite
# score de ranking das memorias contextuais. Default OFF: hoje correction_count e ~0 em
# quase todas as memorias (so o loop o popula com o tempo); ligar antes disso apenas
# redistribuiria os pesos de decay/importance (regressao silenciosa). Ligar so depois que o
# contador estiver populado. OFF = formula historica EXATA preservada.
USE_RECURRENCE_SCORE = os.getenv("AGENT_RECURRENCE_SCORE", "false").lower() == "true"

# Fase 3.3 do loop corretivo — medicao POR OUTCOME (harmful/helpful), desacoplada do eco
# textual (effective_count). harmful++ = regra 'mandatory' estava ativa e o MESMO erro
# reincidiu (a regra dura falhou em prevenir); helpful++ = regra 'mandatory' ativa e SEM
# reincidencia por K injecoes. Default ON: so escreve em colunas NOVAS (harmful_count/
# helpful_count) — aditivo e seguro; alimenta o demote (3.6) e o painel de adesao (3.7).
AGENT_OUTCOME_TRACKING = os.getenv("AGENT_OUTCOME_TRACKING", "true").lower() == "true"
# Nº de injecoes da regra dura SEM reincidencia (harmful_count==0) para creditar helpful_count
# (1 credito a cada K injecoes limpas — bounded). Conservador por padrao.
AGENT_OUTCOME_HELPFUL_K_SESSIONS = int(os.getenv("AGENT_OUTCOME_HELPFUL_K_SESSIONS", "3"))

# Fase 3.6 do loop corretivo — DEMOTE de regra dura que reincidiu repetidas vezes mesmo
# sendo 'mandatory' (harmful_count >= threshold). Rebaixa priority->'contextual' + is_cold=True
# (puxa de circulacao pendente de reescrita humana). Flap-free: a promocao filtra is_cold==False.
# Default OFF (DESVIO consciente da regra "flags ON"): demote REMOVE uma regra explicita do
# usuario do canal duro — efeito potencialmente surpreendente; validar o criterio antes de ligar.
AGENT_CORRECTION_DEMOTION = os.getenv("AGENT_CORRECTION_DEMOTION", "false").lower() == "true"
AGENT_OUTCOME_HARMFUL_THRESHOLD = int(os.getenv("AGENT_OUTCOME_HARMFUL_THRESHOLD", "2"))

# Fase 3.5 do loop corretivo — HARD enforcement (PreToolUse) de invariantes DUROS FORMALIZADOS.
# So bloqueia tool call cujo input contenha um token proibido declarado EXPLICITAMENTE por uma
# regra dura via 'ENFORCE_DENY_SUBSTR: <token>' (curadoria humana). NUNCA bloqueia por texto
# livre; o error_signature (slug de metrica) NAO e usado p/ matching. Fail-open (erro -> permite).
# Default OFF (DESVIO consciente da regra "flags ON"): enforcement DURO pode bloquear uma operacao
# legitima por falso-positivo — so ligar com invariantes bem curados (nome de campo, op destrutiva).
USE_MANDATORY_HARD_ENFORCE = os.getenv("AGENT_MANDATORY_HARD_ENFORCE", "false").lower() == "true"

# ====================================================================
# Features SDK 0.1.60 — Subagent Transparency (2026-04-16)
# ====================================================================
# 5 flags booleanas + 2 valores (threshold/admin-override) default=true.
# Rollback: setar AGENT_SUBAGENT_*=false + restart (sem redeploy).

# #1 Endpoint admin debug forense — drill-down em subagentes de qualquer sessao
USE_SUBAGENT_DEBUG_ENDPOINT = os.getenv(
    "AGENT_SUBAGENT_DEBUG_ENDPOINT", "true"
).lower() == "true"

# #3 Cost tracking granular por subagente — persiste em AgentSession.data JSONB
USE_SUBAGENT_COST_GRANULAR = os.getenv(
    "AGENT_SUBAGENT_COST_GRANULAR", "true"
).lower() == "true"

# #5 Memory mining cross-subagent — pattern_analyzer inclui findings dos especialistas
USE_SUBAGENT_MEMORY_MINING = os.getenv(
    "AGENT_SUBAGENT_MEMORY_MINING", "true"
).lower() == "true"

# #6 UI linha inline expansivel no chat
USE_SUBAGENT_UI = os.getenv("AGENT_SUBAGENT_UI", "true").lower() == "true"

# #4 Validacao anti-alucinacao async (Haiku 4.5 score 0-100)
USE_SUBAGENT_VALIDATION = os.getenv(
    "AGENT_SUBAGENT_VALIDATION", "true"
).lower() == "true"

# #4 Threshold de flag (score abaixo do qual dispara warning)
SUBAGENT_VALIDATION_THRESHOLD = int(
    os.getenv("AGENT_SUBAGENT_VALIDATION_THRESHOLD", "70")
)

# #6 Admin override — permite admin ver PII raw em UI
SUBAGENT_UI_RAW_FOR_ADMIN = os.getenv(
    "AGENT_SUBAGENT_UI_RAW_FOR_ADMIN", "true"
).lower() == "true"

# ====================================================================
# Subagent UI Enrichment (2026-05-14)
# ====================================================================
# Big-bang em prod: todos default true. Manter como circuit breakers.
# Rollback emergencial via env var no Render (sem redeploy).

# P0.1 Modal de transcript (prompt + timeline + findings)
USE_SUBAGENT_MODAL = os.getenv("USE_SUBAGENT_MODAL", "true").lower() == "true"

# P0.2 Estados visuais ricos (failed/stopped/validation_warning) +
# P1.1 Correlacao parent_tool_use_id
USE_SUBAGENT_RICH_STATES = os.getenv("USE_SUBAGENT_RICH_STATES", "true").lower() == "true"

# P0.3 Progresso ao vivo: tokens/duracao/last_tool no meta da linha
USE_SUBAGENT_LIVE_PROGRESS = os.getenv("USE_SUBAGENT_LIVE_PROGRESS", "true").lower() == "true"

# P1.2 Rename/tag de subagent (Fase 2)
USE_SUBAGENT_RENAME_TAG = os.getenv("USE_SUBAGENT_RENAME_TAG", "true").lower() == "true"

# P1.3 Download output_file JSONL (Fase 2)
USE_SUBAGENT_OUTPUT_DOWNLOAD = os.getenv("USE_SUBAGENT_OUTPUT_DOWNLOAD", "true").lower() == "true"

# ====================================================================
# SDK 0.1.64 — SessionStore (Fase B cutover: flag ON default)
# ====================================================================
#
# Substitui session_persistence.py (reduzido a helpers de path) pelo SessionStore
# protocol nativo do SDK 0.1.64. Tabela claude_session_store e source-of-truth
# para persistencia e resume de sessoes SDK.
#
# Historico:
# - Fase A (dual-run, 2026-04-21 15:00-16:30): flag OFF default, dual path
# - Fase B (cutover, 2026-04-21 ~17:00): flag ON default, 6 callsites legados
#   removidos, migration batch script populou store com sessions pre-existentes
#
# Fallback defense in depth (se store falhar):
# - SDK materialize_resume_session retorna None se store.load falhar
# - Subprocess spawna sem --resume
# - UserPromptSubmit hook (chat.py ~320+) reinjeta XML com ultimas 10 msgs
#   a partir de AgentSession.data['messages'] (JSONB preservado)
#
# Rollback: AGENT_SDK_SESSION_STORE_ENABLED=false + redeploy (0 downtime).
# Sessions ativas perdem resume automatico ate proximo deploy, mas fallback XML
# injeta contexto das ultimas 10 msgs via hook.
#
# Ref: /tmp/subagent-findings/20260421-sessionstore-60ddbe70/phase3/plan-v2-final.md
AGENT_SDK_SESSION_STORE_ENABLED = os.getenv(
    "AGENT_SDK_SESSION_STORE_ENABLED", "true"
).lower() == "true"

# Timeout em ms para store.load() / list_subkeys() durante materialize_resume_session.
# Default SDK = 60000ms. Nosso p99 de query indexed < 100ms; 30000ms e folgado.
# Se store ficar lento > 30s, resume falha — cai no fallback XML.
AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS = int(
    os.getenv("AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS", "30000")
)

# ====================================================================
# Session Store Flush Mode (claude-agent-sdk 0.1.73+)
# ====================================================================
# Controla quando o TranscriptMirrorBatcher entrega frames ao SessionStore.append().
#
#   "batched" (default — comportamento atual e seguro):
#     Buffera frames durante o turn, flush UMA vez no end-of-turn.
#     Custo Postgres: 1 INSERT por turn. Latencia: imperceptivel ao usuario.
#     Risco: se worker gunicorn crasha mid-turn, transcript do turn EM ANDAMENTO
#     se perde (sessao retoma do ultimo turn completo).
#
#   "eager" (NOVO 0.1.73 — opt-in):
#     Flush near-real-time, frame-by-frame. Habilita: live-tailing UIs, cross-process
#     resume mid-turn, crash durability frame-level.
#     Custo Postgres: dezenas a centenas de INSERTs por turn — pode saturar pool
#     asyncpg LAZY per-worker (max=3). Latencia: +5-20ms por chunk SSE.
#     ATIVAR APENAS apos profiling: medir frames/turn medio + impacto em pool DB.
#
# Rollback: AGENT_SDK_SESSION_STORE_FLUSH=batched + redeploy.
#
# Ref: claude-agent-sdk CHANGELOG 0.1.73, ClaudeAgentOptions.session_store_flush
AGENT_SDK_SESSION_STORE_FLUSH = os.getenv(
    "AGENT_SDK_SESSION_STORE_FLUSH", "batched"
).lower()
if AGENT_SDK_SESSION_STORE_FLUSH not in ("batched", "eager"):
    AGENT_SDK_SESSION_STORE_FLUSH = "batched"

# ====================================================================
# Sticky Session via Redis (2026-05-27)
# ====================================================================
# Mitiga Anthropic Issue #61862 (Vj3 over-fires interrupted_turn).
# Workers Gunicorn (workers=4) sem session affinity fazem requests da
# mesma sessao caírem em workers diferentes → cada worker novo recria
# subprocess CLI → materialize_resume_session → Vj3 dispara "Continue
# from where you left off" → chain parentUuid quebra → modelo perde
# turnos intermediários.
#
# Quando ON: workers registram ownership em Redis. Request num worker
# nao-dono retorna 409. Frontend JS retry com backoff até cair no dono.
#
# Rollback: AGENT_STICKY_SESSION_ENABLED=false. Fail-open se Redis off.
#
# Ref: https://github.com/anthropics/claude-code/issues/61862
AGENT_STICKY_SESSION_ENABLED = os.getenv(
    "AGENT_STICKY_SESSION_ENABLED", "false"
).lower() == "true"

# TTL do ownership (segundos). Default 30min = mais que session idle típica.
STICKY_SESSION_TTL_SEC = int(os.getenv("STICKY_SESSION_TTL_SEC", "1800"))

# ====================================================================
# POST_SESSION jobs via RQ (2026-05-27)
# ====================================================================
# Move jobs POST_SESSION (summarize, patterns, profile, extract_knowledge,
# extract_personal) do thread/sync inline no worker do chat → fila RQ
# `agent_background` (worker separado).
#
# Motivo: jobs chamam Sonnet API por 5-30s cada. Quando rodam inline,
# saturam o worker dono da sessao. Gunicorn roteia novas requests para
# outros workers que vem ownership Sticky e retornam 409. Mesmo o JS
# fazendo retry, pode demorar muitos segundos ate o worker dono liberar
# e aceitar a proxima request.
#
# Quando ON: jobs enfileirados em ~10ms, worker do chat libera imediato.
# Quando OFF (default): comportamento atual (thread/sync inline).
# Fallback: se RQ/Redis off, cai automaticamente em thread/sync.
#
# Rollback: AGENT_POST_SESSION_VIA_RQ=false. Sem deploy de codigo.
AGENT_POST_SESSION_VIA_RQ = os.getenv(
    "AGENT_POST_SESSION_VIA_RQ", "false"
).lower() == "true"

# ====================================================================
# Thinking Display (SDK 0.1.65+)
# ====================================================================
# Controla o campo `display` do ThinkingConfig (forwarded como --thinking-display CLI).
#
# MECANICA REAL (correcao ao framing anterior):
#   - `summarized`: modelo gera texto sumarizado do raciocinio (tokens extras de
#     output + latencia extra para essa geracao). Util para debug panel / UX.
#   - `omitted`: modelo pula a geracao do resumo. Thinking tokens internos iguais,
#     resposta final identica. Mais rapido e mais barato.
#
# ESTRATEGIA: default `omitted` (velocidade + custo). User pode habilitar via
# toggle na UI (persistido em Usuario.preferences['agent_thinking_display']).
# Esta flag atua como FALLBACK quando o user nao tem preferencia setada.
#
# Valores: "omitted" (default global, velocidade prioritaria), "summarized" (UX
# com raciocinio visivel, custo extra), "off" (NAO passa o campo — SDK/CLI
# decidem default; usar para rollback 0.1.65).
#
# Rollback: AGENT_THINKING_DISPLAY=off restaura comportamento pre-patch.
#
# Ref: https://github.com/anthropics/claude-agent-sdk-python (release 0.1.65, #830)
AGENT_THINKING_DISPLAY = os.getenv("AGENT_THINKING_DISPLAY", "omitted").lower()

# ====================================================================
# Strict MCP config (SDK 0.1.74+)
# ====================================================================
# Quando True, o CLI usa APENAS os mcp_servers passados em ClaudeAgentOptions —
# ignora project/user/global config (.mcp.json, plugins). Util para garantir
# determinismo DEV vs PROD: em DEV local, evita que MCP servers pessoais do
# desenvolvedor (pyright-lsp, context7, etc.) vazem para a sessao do agente.
#
# Em PROD (Render com HOME=/tmp), nao muda comportamento (sem .mcp.json).
# Em DEV, recomendado True para reproduzir ambiente PROD.
#
# Default false (rollback seguro). Ativacao: AGENT_STRICT_MCP_CONFIG=true.
# Forward-compat via introspection em client.py — SDK < 0.1.74 ignora.
#
# Ref: claude-agent-sdk CHANGELOG 0.1.74, ClaudeAgentOptions.strict_mcp_config
USE_STRICT_MCP_CONFIG = os.getenv("AGENT_STRICT_MCP_CONFIG", "false").lower() == "true"

# ====================================================================
# F1 — Cache hit alert (Sentry)
# ====================================================================
# Quando True, captura no Sentry quando uma request consome muitos tokens
# de input mas cache_read_input_tokens=0 — sinal de silent invalidator
# (datetime.now() em system prompt, tools mudando, model swap mid-session, etc).
#
# Threshold: input_tokens > MIN_CACHE_PREFIX (4096 Opus / 2048 Sonnet) AND
# cache_read_tokens == 0 AND cache_creation_tokens == 0 (excluiu primeiro write).
#
# Cooldown 5min por (user_id, model) para evitar spam — capturas adicionais
# logam DEBUG mas nao vao para Sentry.
#
# Default true (observabilidade barata). Desativar: AGENT_CACHE_MISS_ALERT_ENABLED=false.
USE_CACHE_MISS_ALERT = os.getenv("AGENT_CACHE_MISS_ALERT_ENABLED", "true").lower() == "true"

# ====================================================================
# F7 — Browser (Playwright) lazy registration
# ====================================================================
# Quando False (default), playwright_mcp_tool NAO eh registrado no MCP server
# do agente — reduz cold start (~1720 LOC nao carregadas) e RAM (server idle).
# Subagentes que precisam de browser (gestor-ssw, operando-portal-atacadao via
# skills) carregam playwright sob demanda via skill activation.
#
# Quando True, comportamento legado — playwright registrado no startup.
#
# Default false. Ativacao: AGENT_BROWSER_ENABLED=true.
USE_BROWSER_TOOL = os.getenv("AGENT_BROWSER_ENABLED", "false").lower() == "true"

# ====================================================================
# F8 — cost_tracker persistente em DB
# ====================================================================
# Quando True, cost_tracker.record_cost() faz write-through na tabela
# agent_session_costs (persiste cross-deploy). Quando False (default),
# mantem comportamento runtime-only em memoria — perde dados ao redeploy.
#
# Persistencia eh best-effort: falha de DB nao quebra stream do agente.
# Routes/insights le da tabela quando flag ON, fallback para in-memory quando OFF.
#
# Default true (ativado em 2026-05-16). Desativar: AGENT_COST_TRACKER_PERSIST=false.
USE_COST_TRACKER_PERSIST = os.getenv("AGENT_COST_TRACKER_PERSIST", "true").lower() == "true"


# A1 (2026-05-16) — Telemetria per-invocacao de subagent
# ---------------------------------------------------------------------------
# Quando ON: hook SubagentStop persiste UMA linha por spawn->stop em
# `agent_invocation_metrics`. Distinta de USE_COST_TRACKER_PERSIST (per-message).
#
# Granularidade nova: tokens, duracao, num_turns, stop_reason, cost por
# invocacao. Permite analise de regressao cross-deploy + per-agent dashboard
# (roadmap Fase A — Instrumentacao).
#
# Persistencia via AgentInvocationMetric.insert_metric (SAVEPOINT pattern).
# Falha de DB nao quebra stream do agente (best-effort).
#
# Default true (ativado em 2026-05-16). Desativar: AGENT_INVOCATION_METRICS_PERSIST=false.
USE_INVOCATION_METRICS_PERSIST = os.getenv(
    "AGENT_INVOCATION_METRICS_PERSIST", "true"
).lower() == "true"


# ====================================================================
# Restricao Estoque (2026-05-26) — gating de skills WRITE de ajuste/Indisponivel
# ====================================================================
# Bloqueia, via can_use_tool, skills WRITE de ajuste de estoque para users
# que NAO estao na whitelist:
#   - ajustando-quant-odoo            (TODOS modos = ajuste +/-)
#   - transferindo-interno-odoo       (SO se args mencionam Indisponivel)
#   - planejando-pre-etapa-odoo       (SO modo executar-onda)
#
# Movimentacoes legitimas (criar PO, faturar, transferencia entre lotes/locs
# sem Indisponivel, cancelar picking, operar reservas, etc.) NAO sao afetadas
# — o agente continua util para a equipe.
#
# Kill-switch: AGENT_ESTOQUE_RESTRICAO_ENFORCEMENT=false desliga completamente.
# Whitelist: AGENT_ESTOQUE_RESTRICAO_ALLOWED_USER_IDS=1,55 (CSV de user_ids).
# Default "1,55" cobre Rafael (web + Teams). Ajustar via env var sem deploy.
USE_ESTOQUE_RESTRICAO_ENFORCEMENT = os.getenv(
    "AGENT_ESTOQUE_RESTRICAO_ENFORCEMENT", "true"
).lower() == "true"


# =============================================================================
# R11.1 — GATE action_update_taxes (FASE 2 / T2.1, 2026-06-05)
# =============================================================================
# Bloqueia (deny UNIVERSAL — sem allowlist), via can_use_tool, qualquer tentativa
# de EXECUTAR `action_update_taxes` em sale.order via Bash/Write/Edit. Esse metodo
# zera tax_id quando a fiscal_position mapeia impostos para vazio (ex.: posicao 49
# "SAIDA - TRANSFERENCIA ENTRE FILIAIS") — anti-padrao real 4722693c (impostos de
# 30 linhas de SO ja' faturado zerados). O metodo correto e'
# `onchange_l10n_br_calcular_imposto` (mesmo do worker da fila `impostos`).
#
# Bloqueio universal (nem o admin executa pelo agente): nao ha uso legitimo desse
# metodo pelo Agente Web/Teams. Detalhe + alternativa: GOTCHAS.md secao "Recalcular
# Impostos em sale.order". Defesa best-effort (evasivel por string dinamica) — par
# DETERMINISTICO do principio R11.1 que permanece no system_prompt (FASE 2: a defesa
# vira codigo ANTES de o detalhe sair do prompt).
#
# Kill-switch: AGENT_ODOO_TAX_GATE=false desliga (rollback sem deploy).
USE_ODOO_TAX_GATE = os.getenv("AGENT_ODOO_TAX_GATE", "true").lower() == "true"


def _parse_allowed_user_ids_csv(raw: str) -> set[int]:
    """Parseia CSV de user_ids autorizados ('1,55' -> {1, 55}).

    Ignora valores invalidos com warning (defesa contra typo em env var).
    """
    import logging as _ff_logging
    _ff_logger = _ff_logging.getLogger('sistema_fretes')
    result: set[int] = set()
    for piece in (raw or '').split(','):
        piece = piece.strip()
        if not piece:
            continue
        try:
            result.add(int(piece))
        except ValueError:
            _ff_logger.warning(
                f"[FEATURE_FLAGS] AGENT_ESTOQUE_RESTRICAO_ALLOWED_USER_IDS: "
                f"ignorando valor invalido {piece!r}"
            )
    return result


ESTOQUE_RESTRICAO_ALLOWED_USER_IDS: set[int] = _parse_allowed_user_ids_csv(
    os.getenv("AGENT_ESTOQUE_RESTRICAO_ALLOWED_USER_IDS", "1,55")
)


# =============================================================================
# Fable 5 — modelo opt-in por usuario (2026-06-10)
# =============================================================================
# `claude-fable-5` e' o modelo mais capaz da Anthropic, porem o mais CARO (pricing
# acima do Opus-tier + tokenizer ~30% mais tokens). Por isso a opcao so' e' exposta
# na UI (e aceita no backend) para user_ids autorizados — espelha o padrao de
# ESTOQUE_RESTRICAO_ALLOWED_USER_IDS. Pre-req: CLI bundled >= 2.1.170 (SDK 0.2.95),
# que reconhece o model id `claude-fable-5`.
#
# Whitelist: AGENT_FABLE5_ALLOWED_USER_IDS=1,55 (CSV de user_ids). Default "1"
# (so Rafael). Ajustar via env var no Render SEM deploy.
FABLE5_MODEL_ID = "claude-fable-5"
FABLE5_ALLOWED_USER_IDS: set[int] = _parse_allowed_user_ids_csv(
    os.getenv("AGENT_FABLE5_ALLOWED_USER_IDS", "1")
)


def is_fable5_allowed(user_id) -> bool:
    """True se o user_id pode usar o modelo Fable 5 (gate por allowlist CSV).

    Aceita int | None | str-numerica. None/invalido -> False (fail-closed:
    Fable 5 e' caro, nao liberar por engano).
    """
    if user_id is None:
        return False
    try:
        return int(user_id) in FABLE5_ALLOWED_USER_IDS
    except (TypeError, ValueError):
        return False


# ====================================================================
# Audit Hook deterministico Odoo (2026-05-28)
# ====================================================================
# Quando ativo, OdooConnection.execute_kw registra TODA chamada XML-RPC
# write na tabela operacao_odoo_auditoria, correlacionando com session_id
# do agente web via ENV vars propagadas pelo PreToolUse hook.
#
# Whitelist de metodos: app/utils/odoo_audit_helpers.py METODOS_WRITE_AUDITADOS
# Schema: scripts/migrations/2026_05_28_operacao_odoo_auditoria_session.{py,sql}
# Ver app/odoo/CLAUDE.md secao P8.
USE_ODOO_AUDIT_HOOK = os.getenv("AGENT_ODOO_AUDIT_HOOK", "false").lower() == "true"


# ====================================================================
# Capability Registry (Onda 0 — S0c)
# ====================================================================
# Grafo descritivo read-only skill↔agente. Fundacao para ondas futuras
# (planejador/skill-RAG). Nenhum runtime consome o registry ainda.
# Ativar quando houver consumidor: AGENT_CAPABILITY_REGISTRY=true.
# Default false — flag marca a fundacao como inerte ate onda futura.
USE_CAPABILITY_REGISTRY = os.getenv("AGENT_CAPABILITY_REGISTRY", "false").lower() == "true"

# ====================================================================
# Onda 1 — Quality Spine + Ontologia (todas OFF por default; ativam em deploy)
# ====================================================================
USE_AGENT_QUALITY_SPINE = os.getenv("AGENT_QUALITY_SPINE", "false").lower() == "true"
USE_AGENT_STEP_JUDGE = os.getenv("AGENT_STEP_JUDGE", "false").lower() == "true"
USE_AGENT_ONTOLOGY = os.getenv("AGENT_ONTOLOGY", "false").lower() == "true"

# ====================================================================
# Onda 2 — Planejador + Verify (OFF por default; ativar em deploy gradual)
# ====================================================================

# B1: PlanState durável — captura TaskCreate/TaskUpdate e persiste em
# AgentSession.data['plan'] (JSONB). Fundação do super-loop planejador.
# Com flag OFF (default PROD): nenhum write em data['plan'] — comportamento
# idêntico ao atual. Ativar com AGENT_PLANNER=true para habilitar.
USE_AGENT_PLANNER = os.getenv("AGENT_PLANNER", "false").lower() == "true"

# B2: Verify step — juiz pós-turno que avalia se o plano foi executado.
# Depende de USE_AGENT_PLANNER. Planejado para Onda 2 fase posterior.
# Rollback: AGENT_VERIFY=false.
USE_AGENT_VERIFY = os.getenv("AGENT_VERIFY", "false").lower() == "true"

# ====================================================================
# Onda 3 — A3: Eval Gate (golden datasets, report-only, D8 cron)
# ====================================================================
# Quando ON: D8 (modulo 28) roda run_evals() contra os 4 golden datasets
# de subagentes e loga resultado (report-only — NUNCA bloqueia o cron).
# invoke_fn e' o seam injetavel; em shadow (flag ON) usa default que raise
# NotImplementedError e reporta todos os casos como 'error' (safe).
# Wiring real do agente sera' feito na ativacao futura.
#
# Default false (flag-OFF, D8 no-op). Ativar: AGENT_EVAL_GATE=true.
# Rollback instantaneo: AGENT_EVAL_GATE=false.
AGENT_EVAL_GATE = os.getenv("AGENT_EVAL_GATE", "false").lower() == "true"

# ====================================================================
# Onda 3 — A3-R3: Calibracao do judge de eval (spot-check humano)
# ====================================================================
# Quando ON: run_eval_regression_gate persiste 1 linha POR CASO em
# agent_eval_case (via persist_eval_cases em eval_runner), guardando o veredito
# granular do judge (case_score = mediana de N runs). Isso habilita:
#   - spot-check humano de 5-10% (AgentEvalCase.sample_unreviewed);
#   - metrica de concordancia judge-vs-humano (AgentEvalCase.concordance_rate).
# Spec eixos/A-flywheel.md:165 ("Calibracao obrigatoria: spot-check humano de
# 5-10% das notas do judge"). Sem calibracao, trocamos um proxy cego (eco) por
# outro (judge nao-auditado) — A-flywheel.md:318.
#
# Quando OFF (default): run_eval_regression_gate persiste APENAS o score
# agregado (comportamento atual, A3-R2) — NAO grava os casos. Zero overhead.
# Ativar: AGENT_EVAL_CALIBRATION=true. Rollback: AGENT_EVAL_CALIBRATION=false.
#
# ESCOPO (code-review M3): a calibracao por-caso (agent_eval_case) e' gravada
# SOMENTE no caminho do GATE DE REGRESSAO (run_eval_regression_gate, A3-R4 no D8),
# NAO no eval periodico do cron (run_eval_batch / modulo 28). E' intencional: o
# spot-check humano calibra o judge no ponto onde ele de fato decide regressao
# (commit do D8), nao no sanity-check periodico. Ligar esta flag NAO faz o batch
# do cron gravar casos.
USE_AGENT_EVAL_CALIBRATION = os.getenv("AGENT_EVAL_CALIBRATION", "false").lower() == "true"

# ====================================================================
# GATE-1 / E3 — Calibration Sampler do ONLINE judge (flag DEDICADA, T4.5)
# ====================================================================
# Gateia o calibration_sampler (workers/calibration_sampler.py) + o módulo 33
# do D8 (sincronizacao_incremental_definitiva.py), que populam agent_eval_case a
# partir dos vereditos do ONLINE judge (agent_step.outcome_signal['judge']) para
# spot-check humano + concordance_rate.
#
# DESACOPLADA de AGENT_EVAL_CALIBRATION DE PROPÓSITO (T4.5, pedido Rafael 2026-06-03):
# aquela flag gateia o eval_runner/A3 (persist_eval_cases), que dispara eval LLM
# CARO — APOSENTADO e VETADO. Esta flag NÃO compartilha gate com o A3, então ligar
# a calibração do online judge JAMAIS pode acionar um eval LLM caro, nem num cenário
# hipotético de A3 religado. O sinal aqui é 100% DB (copiar o veredito do judge já
# gravado por step_judge) + rotulagem humana barata — zero LLM.
#
# Default false. Ativar (GATE-1): AGENT_CALIBRATION_SAMPLER=true. Rollback: =false.
USE_AGENT_CALIBRATION_SAMPLER = os.getenv("AGENT_CALIBRATION_SAMPLER", "false").lower() == "true"

# ====================================================================
# Onda 4 — F4/F5: Skill Hints Advisory (flag-OFF por default)
# ====================================================================
# Quando ON: hook UserPromptSubmit adiciona bloco <skill_hints priority="advisory">
# com as N skills mais relevantes para o turno (keyword matching zero-LLM).
#
# LIMITAÇÃO ARQUITETURAL (documentada em context_enrichment.py):
#   O SDK fixa `skills=` no connect() — não há set_skills() por turno.
#   Este bloco é ADVISORY: informa o agente, não altera o listing real.
#
# Quando OFF (default): nenhum bloco adicionado — comportamento idêntico.
# Ativar: AGENT_SKILL_RAG=true
USE_AGENT_SKILL_RAG = os.getenv("AGENT_SKILL_RAG", "false").lower() == "true"

# ====================================================================
# Onda 4 — D5: World Model Injection via ontologia (flag-OFF por default)
# ====================================================================
# Quando ON: hook UserPromptSubmit adiciona bloco <world_model priority="advisory">
# com entidades canônicas da ontologia (D4 query_ontology_entities).
#
# D5 é ADITIVO: _DOMAIN_KEYWORDS em memory_injection.py permanece como
# fallback cold-start. Não remove nem substitui routing_context existente.
# Se ontologia vazia → None (fallback ativo) — nunca duplica contexto.
#
# Quando OFF (default): nenhum bloco adicionado — comportamento idêntico.
# Ativar: AGENT_WORLD_MODEL_INJECT=true
USE_AGENT_WORLD_MODEL_INJECT = os.getenv("AGENT_WORLD_MODEL_INJECT", "false").lower() == "true"

# ====================================================================
# Onda 3 — A4: Promoção Automática de Diretriz (V1 offline, flag-OFF)
# ====================================================================
# Fecha o flywheel "Distill→Deploy". A4-batch CONSTRUÍDA (2026-06-01):
# coluna directive_status (migration 2026_06_01), _persist_directive REAL
# (escreve directive_status='shadow'), e o caller = run_directive_promotion_batch
# (D8 módulo 32 em sincronizacao_incremental_definitiva.py).
#
# Quando ON: módulo 32 varre PlanStates concluídos → candidata → anti-gaming R9
# DOMINA (_tem_falha_odoo, conservador) → gate A3 vs floor → PERSISTE como
# directive_status='shadow'. Diretriz 'shadow' NUNCA é injetada (o builder
# _build_operational_directives injeta só NULL/'ativa'; e ele é gated por
# AGENT_OPERATIONAL_DIRECTIVES, OFF). Dupla segurança.
#
# ATIVAÇÃO (gate humano, fora do V1):
#   shadow→ativa = revisão manual das candidatas + flip de AGENT_OPERATIONAL_DIRECTIVES.
# Pré-reqs para ON ter efeito útil: USE_AGENT_PLANNER gerando PlanState em PROD +
# judge signal (AGENT_STEP_JUDGE) acumulando (senão o batch ABSTÉM, no-op seguro).
# ⚠️ PRÉ-REQ DE DEPLOY: a coluna directive_status DEVE existir antes de ligar
# AGENT_OPERATIONAL_DIRECTIVES (senão UndefinedColumn no builder desliga TODAS as
# diretrizes silenciosamente). Rodar a migration / wirar no build.sh ao mergear na main.
#
# Default false. Ativar: AGENT_DIRECTIVE_PROMOTION=true. Rollback: =false.
AGENT_DIRECTIVE_PROMOTION = os.getenv("AGENT_DIRECTIVE_PROMOTION", "false").lower() == "true"

# A4-batch: parâmetros do varredor (módulo D8 32). Só atuam com AGENT_DIRECTIVE_PROMOTION=ON.
AGENT_DIRECTIVE_LOOKBACK_HOURS = int(os.getenv("AGENT_DIRECTIVE_LOOKBACK_HOURS", "24"))
AGENT_DIRECTIVE_BATCH_LIMIT = int(os.getenv("AGENT_DIRECTIVE_BATCH_LIMIT", "50"))
# floor de qualidade da sessão de origem (baseline do gate; não há golden do agente principal).
AGENT_DIRECTIVE_MIN_QUALITY = float(os.getenv("AGENT_DIRECTIVE_MIN_QUALITY", "0.7"))

# =====================================================================
# SQL-FIRST CANARY (Fix B, sessao #787) — tool consultar_sql
# =====================================================================
# Inverte a premissa da tool: o chamador real e' o Agente (Opus), que ja' sabe
# SQL. Quando ele envia SQL pronto, executar LITERAL (skip Generator Haiku que
# adivinha/trunca/reescreve); o validador deterministico vira guard-rail.
#
# Flag UNICA multivalor. S3 decisao #5 (pos-S1): default do CODIGO = 'on' (SQL-first
# e' o padrao). A env var em PROD tem precedencia (nao foi alterada por esta mudanca).
# Estagios:
#   'off'    -> comportamento legado (Generator NL->SQL para todos) — KILL-SWITCH
#   'shadow' -> TODOS observam (log + etapa would_block), sem mudar comportamento
#   'admin'  -> admins (USUARIOS_SQL_ADMIN) recebem SQL-first real; demais ficam
#               em 'shadow' (continuam observando, sem mudanca de comportamento)
#   'on'     -> SQL-first real para TODOS (DEFAULT pos-S1)
#
# Lido FRESH em resolve_sql_first_mode() (nao constante de import) para o canary
# poder avancar via env var sem rebuild. O escopo por admin e' resolvido aqui (no
# chamador/tool); o pipeline (text_to_sql.run) so' recebe o modo efetivo.
_SQL_FIRST_VALID = {"off", "shadow", "admin", "on"}


# ====================================================================
# Aprendizado por efetividade de skill (Fase 1)
# ====================================================================
# Liga o gatilho + job de avaliacao pos-sessao. Default OFF (1 ciclo de smoke antes).
AGENT_SKILL_EVAL = os.getenv("AGENT_SKILL_EVAL", "false").lower() == "true"
# Permite escalonar ao Sonnet (estagio 2). Se OFF, para no Haiku (modo observacao).
AGENT_SKILL_EVAL_SONNET = os.getenv("AGENT_SKILL_EVAL_SONNET", "true").lower() == "true"
# Ramo lembrete_usuario aplica auto. Se OFF, vira shadow (vai p/ inbox tambem).
AGENT_SKILL_EVAL_APPLY_USER = os.getenv("AGENT_SKILL_EVAL_APPLY_USER", "true").lower() == "true"
# Limiar de confidence (0-1) do Sonnet p/ auto-aplicar lembrete_usuario.
AGENT_SKILL_EVAL_CONF_MIN = float(os.getenv("AGENT_SKILL_EVAL_CONF_MIN", "0.7"))
# Cap de escalonamentos a Sonnet por sessao (anti-explosao de custo).
AGENT_SKILL_EVAL_MAX_SONNET = int(os.getenv("AGENT_SKILL_EVAL_MAX_SONNET", "3"))


def resolve_sql_first_mode(is_admin: bool) -> str:
    """Resolve o modo SQL-first EFETIVO para este request (Fix B canary).

    Le SQL_AGENT_SQL_FIRST do ambiente e aplica o escopo por admin, retornando
    um dos modos que o pipeline entende: "off" | "shadow" | "on".

    Args:
        is_admin: True se o usuario esta em USUARIOS_SQL_ADMIN.

    Returns:
        "off"    -> pipeline mantem comportamento atual (Generator)
        "shadow" -> pipeline observa/loga, sem mudar comportamento
        "on"     -> pipeline executa SQL literal (SQL-first ativo)
    """
    # S3 decisao #5 (pos-S1): default do codigo = "on" (SQL-first e' o padrao).
    # Kill-switch: SQL_AGENT_SQL_FIRST=off restaura o legado (Generator).
    raw = os.getenv("SQL_AGENT_SQL_FIRST", "on").strip().lower()
    if raw not in _SQL_FIRST_VALID:
        return "off"
    if raw == "admin":
        return "on" if is_admin else "shadow"
    return raw  # off | shadow | on

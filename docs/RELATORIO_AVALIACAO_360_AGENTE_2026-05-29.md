<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Relatório Final Integrado — Avaliação 360° do Agente Nacom Goya

> **Papel:** Relatório Final Integrado — Avaliação 360° do Agente Nacom Goya.

## Indice

- [1. Sumário executivo](#1-sumário-executivo)
- [2. Bugs ativos P0/P1/P2 (CONFIRMADOS) + status dos refutados](#2-bugs-ativos-p0p1p2-confirmados-status-dos-refutados)
  - [BUG-1 [P1] — `registrar()` sem savepoint poisona a sessão do pipeline (cascata `PendingRollbackError`)](#bug-1-p1-registrar-sem-savepoint-poisona-a-sessão-do-pipeline-cascata-pendingrollbackerror)
  - [BUG-2 [P1] — Família "sessão DB poluída no Teams": `MEMORY_MCP` + endpoints sem rollback defensivo](#bug-2-p1-família-sessão-db-poluída-no-teams-memory_mcp-endpoints-sem-rollback-defensivo)
  - [BUG-3 [P1, segurança] — Gate de autorização WRITE-Odoo cobre só 3 skills; demais operações destrutivas abertas a qualquer usuário](#bug-3-p1-segurança-gate-de-autorização-write-odoo-cobre-só-3-skills-demais-operações-destrutivas-abertas-a-qualquer-usuário)
  - [BUG-4 [P2] — `max_budget_usd=5` é hard-stop SEM tratamento → pode cortar WRITE Odoo no meio](#bug-4-p2-max_budget_usd5-é-hard-stop-sem-tratamento-pode-cortar-write-odoo-no-meio)
  - [BUG-5 [P2] — `/bot/answer` retorna 200 "ok" FALSO quando resposta do usuário se perde (0 subscribers)](#bug-5-p2-botanswer-retorna-200-ok-falso-quando-resposta-do-usuário-se-perde-0-subscribers)
  - [BUG-6 [P2] — `debug_mode` (cross-user admin) provavelmente não propaga ao daemon thread do stream web](#bug-6-p2-debug_mode-cross-user-admin-provavelmente-não-propaga-ao-daemon-thread-do-stream-web)
  - [BUG-7 [P2, segurança] — `admin_mode` SQL sem backstop determinístico contra DDL](#bug-7-p2-segurança-admin_mode-sql-sem-backstop-determinístico-contra-ddl)
  - [Fora de escopo do agente (encaminhar aos donos dos módulos)](#fora-de-escopo-do-agente-encaminhar-aos-donos-dos-módulos)
- [3. Otimizações de custo & eficiência](#3-otimizações-de-custo-eficiência)
  - [OPT-2 [RESOLVIDO — NÃO É AÇÃO] — Prompt caching já ativo e instrumentado](#opt-2-resolvido-não-é-ação-prompt-caching-já-ativo-e-instrumentado)
  - [OPT-1 [GAP REAL, ROI por LATÊNCIA não por $] — Default Opus 4.8 + effort high pega TODA consulta read-only não-roteada](#opt-1-gap-real-roi-por-latência-não-por-default-opus-48-effort-high-pega-toda-consulta-read-only-não-roteada)
  - [OPT-4 [OTIMIZAÇÃO — latência] — Calibrar `effort: xhigh` por carga real do subagente](#opt-4-otimização-latência-calibrar-effort-xhigh-por-carga-real-do-subagente)
  - [OBS-1 [MELHORIA — desbloqueia decisões futuras] — Telemetria de custo do agente principal está cega](#obs-1-melhoria-desbloqueia-decisões-futuras-telemetria-de-custo-do-agente-principal-está-cega)
  - [OPT — descartados como over-tuning](#opt-descartados-como-over-tuning)
- [4. Melhorias de confiabilidade/qualidade](#4-melhorias-de-confiabilidadequalidade)
  - [CONF-1 [streaming web] — Persistência endurecida HOJE; monitorar, não reescrever](#conf-1-streaming-web-persistência-endurecida-hoje-monitorar-não-reescrever)
  - [CONF-2 [Teams — pool process-local em 4 workers] — alinhar com a doc oficial](#conf-2-teams-pool-process-local-em-4-workers-alinhar-com-a-doc-oficial)
  - [CONF-3 [Teams — commits diretos e recursão de fila] — higiene](#conf-3-teams-commits-diretos-e-recursão-de-fila-higiene)
  - [CONF-4 [system prompt] — CONF-4 do parcial FECHADO (dim 4)](#conf-4-system-prompt-conf-4-do-parcial-fechado-dim-4)
  - [CONF-5 [memória — qualidade] — Budget de injeção INFINITO em Opus](#conf-5-memória-qualidade-budget-de-injeção-infinito-em-opus)
  - [CONF-6 [memória — fix de doc] — `get_or_create` JÁ é atômico (doc errada)](#conf-6-memória-fix-de-doc-get_or_create-já-é-atômico-doc-errada)
- [5. Ampliação de recursos (sem over-engineering)](#5-ampliação-de-recursos-sem-over-engineering)
- [6. Adoção de features SDK/Anthropic 2026](#6-adoção-de-features-sdkanthropic-2026)
  - [Aplicabilidade ALTA (adotar)](#aplicabilidade-alta-adotar)
  - [Aplicabilidade MÉDIA (avaliar, não urgente)](#aplicabilidade-média-avaliar-não-urgente)
  - [Aplicabilidade BAIXA (ignorar — adotar seria redundante ou regressivo)](#aplicabilidade-baixa-ignorar-adotar-seria-redundante-ou-regressivo)
- [7. Over-engineering ATUAL (o que já existe demais)](#7-over-engineering-atual-o-que-já-existe-demais)
  - [OE-1 [CONFIRMADO] — 17 services de inteligência: o que MANTER / CONGELAR / APOSENTAR](#oe-1-confirmado-17-services-de-inteligência-o-que-manter-congelar-aposentar)
  - [OE-2 [parcial] — Pós-sessão sempre dispara cadeia completa](#oe-2-parcial-pós-sessão-sempre-dispara-cadeia-completa)
  - [OE-3 [aceitável, NÃO mexer] — Split Caddy + 2 gunicorn](#oe-3-aceitável-não-mexer-split-caddy-2-gunicorn)
- [8. Documentação desatualizada](#8-documentação-desatualizada)
- [9. Segurança (riscos reais)](#9-segurança-riscos-reais)
- [10. Roadmap priorizado (impacto × esforço)](#10-roadmap-priorizado-impacto-esforço)
  - [Quick wins (baixo esforço, alto/médio impacto) — fazer primeiro](#quick-wins-baixo-esforço-altomédio-impacto-fazer-primeiro)
  - [Médio prazo](#médio-prazo)
  - [Avaliar (não fazer sem gatilho)](#avaliar-não-fazer-sem-gatilho)
- [Anexo — Cobertura e honestidade](#anexo-cobertura-e-honestidade)
- [Contexto](#contexto)

> **Data**: 2026-05-29 · **Escopo**: Agente Web (SSE, `:5001`) + Teams bot (`:5002`) · **Perfil de uso real**: ~9 sessões/dia medidas (CONTEXTO declarava ~4; dado real de produção = 129 sessões/14d, 17 usuários), ~3 spawns de subagente/dia, indústria de alimentos R$16MM/mês, operadores logísticos + controller (Marcus) + Rafael (admin/dev).
>
> **Metodologia**: este relatório INTEGRA (a) o relatório parcial (`RELATORIO.md`) — que re-verificou A1-A5 quando os subagentes dimensionais ainda não tinham produzido output; (b) as **8 análises dimensionais** agora completas (`findings/01..08`); (c) as **3 pesquisas externas** (`pesquisa/01..03`). Todas as 11 fontes estavam presentes — **cobertura COMPLETA**, sem dimensão ausente. Spot-checks de evidência load-bearing foram re-confirmados pelo engenheiro líder (BUG-1 savepoint, Teams sanitize, budget hard-stop, `/bot/status` rollback). Cada item marca **[CONFIRMADO]** (evidência verificada em arquivo:linha / Sentry / dado Render) ou **[HIPÓTESE]** (plausível, não fechado em runtime).

---

> ⚠️ **ERRATA (2026-05-30, após revisão do Rafael)** — este relatório foi produzido sob LENTE ERRADA: o documento de contexto instruiu os agentes a julgar pelo volume (~9 sessões/dia) e marcar como over-engineering o que não "se aplicasse". **Volume dimensiona infraestrutura (workers/custo), não o VALOR de uma capacidade.** Consequências: (1) §7 **OE-1 (Knowledge Graph "aposentar") RETIRADO** — o "0.5 furando scoring" é design intencional (`knowledge_graph_service.py:830-834`); KG é embrião de ontologia a expandir. (2) **BUG-4 (max_budget_usd) falso positivo** — `client.py:1764` respeita `USE_BUDGET_CONTROL`, OFF em PROD. (3) **OBS-1 baixa prioridade**. Permanecem válidos: §2 bugs confirmados (BUG-1/2/3), §8 doc, achados de latência. **Falta a análise com lente de TETO (elevar capacidade), não de poda** — ver conversa 2026-05-30.

## 1. Sumário executivo

O agente está **operacionalmente saudável** para o volume real. O caminho de chat web (SSE, worker `:5001`) tem **0 erros em 14 dias no Sentry** (dim 6); o Teams tem **1 issue viva de baixa frequência** (BUG-2). O **prompt caching está ativo e funcionando perfeitamente** — cache hit **100%** medido nos subagentes (dim 7 / pesquisa 3), o que **REFUTA definitivamente** a hipótese OPT-2 do parcial. A arquitetura de deploy (Caddy split: agente em 1 worker isolado, sistema em 4 workers) é a **forma minimalista correta** de garantir afinidade de sessão exigida pelo SDK per-process (pesquisa 3 confirma contra a doc oficial de hosting — não é over-engineering).

**Pontos fortes confirmados:**
- **Caching maduro** — system prompt 100% estático + alerting de cache-miss (`_alert_cache_miss`), acima da média de implementações (dim 4, dim 7).
- **Segurança de SQL em camadas** — para usuário comum, `SET TRANSACTION READ ONLY` no Postgres é backstop real mesmo se o regex falhar (dim 5).
- **Permissões fail-closed** — exceção no callback → DENY; Write/Edit só em `/tmp` com anti-`../`; audit hook env-injection blindado com `shlex.quote()` (dim 8).
- **SSE acima da média** — timeouts em cascata, deadline renewal, heartbeat 10s, fallback persistência+poll (Fase 1/2 de hoje); reconnect via poll é tradeoff deliberado e correto (pesquisa 3).
- **Memória/prompt alinhados às best practices 2026** — compaction-awareness no prompt (duplo aviso), PreCompact hook estruturado, memória curada (níveis 3-5, dedup 0.80) — em alguns pontos **acima** do recomendado (pesquisa 2).

**Top 5 problemas (ordenados por prioridade real):**

| # | Problema | Sev | Onde |
|---|----------|-----|------|
| 1 | **[CONFIRMADO] `registrar()` sem savepoint** transforma 1 erro de campo em cascata de `PendingRollbackError` no pipeline WRITE SEFAZ (gatilho corrigido, padrão persiste) | P1 | BUG-1 (parcial + dim 8) |
| 2 | **[CONFIRMADO] Família de sessão DB poluída no Teams** — `MEMORY_MCP` + `/bot/status` e `/bot/answer` SEM rollback defensivo (só `/bot/message` tem); guard preventivo usa predicado errado | P1 | BUG-2 + T3/T4/MEM-1 (dim 2, 5, 6) |
| 3 | **[CONFIRMADO] Gate de autorização WRITE-Odoo cobre só 3 das ~10 famílias destrutivas** — cancelar MO, transmitir SEFAZ, escriturar etc. abertos a qualquer usuário do agente | P1 | SEC-1 (dim 8) |
| 4 | **[CONFIRMADO] `max_budget_usd=5` é hard-stop SEM tratamento** — pode cortar uma operação WRITE Odoo/SEFAZ no meio com erro genérico | P2 | OPT-3 (dim 7) |
| 5 | **[CONFIRMADO] Over-engineering: 17 services de inteligência** (10.5K LOC) para ~9 sessões/dia; custo $ irrelevante (~US$2-3/mês), mas superfície de manutenção desproporcional; Knowledge Graph é o candidato nº1 a aposentar | médio | OE-1 (dim 3) |

Itens menores de segurança defense-in-depth (input Teams não sanitizado, prompt-injection via tool results sem Layer-4, `admin_mode` SQL sem backstop determinístico de DDL) são reais mas de **blast radius pequeno** (3 admins confiáveis, usuários internos) — quick wins, não emergências.

---

## 2. Bugs ativos P0/P1/P2 (CONFIRMADOS) + status dos refutados

> **Refutados como ativos (descartados):** **A2** (DataError integer "F-E"/"F5d.5") = **JÁ CORRIGIDO E DEPLOYADO** (3 commits `7550fbca`/`32c43a32`/`c3204a06`; live `41d47ed6` contém os 3; zero callsites `etapa=<string>` remanescentes). **A3** (CLI message reader exit 1) e **A4** (porta 10000) = aged-out no Sentry (`is:unresolved` = 0). **Nuance dim 2/dim 6:** A3 ainda aparece como `ignored` (não `unresolved`) no path web (`PYTHON-FLASK-H`, 65 ev) — está **silenciado, residual, não crasheando turnos observavelmente**; não reabrir como P-ativo, mas não declarar "extinto".

### BUG-1 [P1] — `registrar()` sem savepoint poisona a sessão do pipeline (cascata `PendingRollbackError`)
- **[CONFIRMADO]** `OperacaoOdooAuditoria.registrar()` faz `db.session.add(rec); db.session.flush()` SEM savepoint (`app/odoo/models/operacao_odoo_auditoria.py:90-91`, re-verificado). Callers de pipeline (`faturamento_pipeline.py:257`, `escrituracao.py:110`, `pre_etapa_executor.py:174`) **não** envolvem em `begin_nested()`. Quando o `flush()` falha, a transação externa aborta e **toda** operação seguinte do pipeline estoura em cascata.
- **Contraste** [CONFIRMADO]: o hook `app/utils/odoo_audit_helpers.py:181` usa **corretamente** `with db.session.begin_nested():`. O padrão certo já existe no projeto — falta espelhar nas 3 callsites do orchestrator.
- **Evidência Sentry**: cluster `PYTHON-FLASK-WX/WT/WS/WR/WQ` (5× `PendingRollbackError`) disparado em cascata pela única `DataError` (`WY/WV`), todos no release pré-fix `6bd00a1a`.
- **Impacto real**: o gatilho específico (string→integer) está corrigido, mas **qualquer** falha futura de `flush()` dentro de `registrar()` (constraint, tipo, tamanho) volta a derrubar o lote inteiro de faturamento de inventário — operação WRITE crítica (SEFAZ). **Não afeta chat web/Teams.**
- **Fix**: envolver as 3 callsites em `with db.session.begin_nested():`, OU mover o savepoint para dentro de `registrar()` (preferível — auditoria nunca deve poder derrubar a transação que audita).
- **Esforço**: BAIXO (1-3 linhas/callsite + 1 teste). **Quick win.**

### BUG-2 [P1] — Família "sessão DB poluída no Teams": `MEMORY_MCP` + endpoints sem rollback defensivo
Este é **uma classe de bug, não um caso isolado** (refinado por dim 2, dim 5, dim 6). Três faces do mesmo root cause: uma exceção engolida a montante no turno Teams deixa a `db.session` (scoped por thread, e o pool roda no `sdk-pool-daemon`) abortada, e tudo a jusante herda.

- **2a — `list_memories` [CONFIRMADO]**: `[MEMORY_MCP] Erro ao listar memórias: Can't reconnect until invalid transaction is rolled back`. Sentry `PYTHON-FLASK-EG`, `culprit teams.bot_message`, `thread.name sdk-pool-daemon`, `sys.argv gunicorn_config_sistema.py`, **status `regressed`, 3 usuários, lastSeen 2026-05-28**. Degradação **silenciosa** (logado, não propagado) → o turno perde o contexto de memórias.
- **2b — guard preventivo NÃO pega [CONFIRMADO, dim 5]**: `_execute_with_context` (`memory_mcp_tool.py:421-454`) só faz rollback no ramo `ctx is None` **e** só se `db.session.is_active is False` (`:443`) — predicado insuficiente em SQLAlchemy 2.0 (sessão abortada frequentemente reporta `is_active=True`). Pior: o `except` de `list_memories` (`:2349-2352`) **só loga, não faz rollback** — assimetria com `save_memory` (`:2016`) que rola back. Paths read-only (list/view/search) deixam a poluição para a próxima tool. Mesma raiz já causou `register_improvement` (`HX`), `log_system_pitfall` (`HW`), `save_memory _test` (`JP`) — todos resolved, mesma família.
- **2c — endpoints Teams sem rollback defensivo [CONFIRMADO, dim 2]**: a correção histórica (`PYTHON-FLASK-J5` `InFailedSqlTransaction`) adicionou `db.session.rollback()` só em `cleanup_stale_teams_tasks()`, que **`/bot/message` chama** (`bot_routes.py:137`). Mas `/bot/status/<task_id>` (`bot_routes.py:276` `TeamsTask.query.get`) e `/bot/answer` (`bot_routes.py:341`) **NÃO têm rollback** — re-verificado. `/bot/status` é o **mais chamado** (polling do Azure Function), portanto o mais exposto a herdar sessão suja. Em gthread (`workers=4, threads=2`) as threads são reusadas entre requests → a poluição cruza requests.
- **Fix integrado**: (1) `db.session.rollback()` defensivo nos `except` read-only do `memory_mcp_tool`; (2) endurecer `_execute_with_context` para rollback preventivo incondicional best-effort (idempotente, barato) em vez de `is_active is False`; (3) cobrir TODOS os endpoints do blueprint Teams via `@teams_bp.before_request`/`teardown_request` (ou `db.session.remove()` no teardown) em vez de espalhar; (4) caçar o `except` upstream em `memory_injection.py:953,1004` (busca semântica + grafo) que engole erro sem rollback (dim 2 T4).
- **Esforço**: BAIXO (o fix) + MÉDIO (rastrear o gatilho upstream). **Atinge usuários reais, regressed.**

### BUG-3 [P1, segurança] — Gate de autorização WRITE-Odoo cobre só 3 skills; demais operações destrutivas abertas a qualquer usuário
- **[CONFIRMADO, dim 8 SEC-1]**: `_classify_estoque_restricao` (`permissions.py:320-390`) + o gate de user_id (`:808-836`, whitelist `{1,55}`) só cobrem `ajustando-quant-odoo`, `transferindo-interno-odoo` (c/ Indisponível) e `planejando-pre-etapa-odoo executar-onda`.
- **O que fica aberto**: `operando-mo-odoo cancelar` (furo contábil), `operando-picking-odoo`, `operando-reservas-odoo`, **`faturando-odoo transmitir-sefaz` (transmissão IRREVERSÍVEL)**, `escriturando-odoo`, `conciliando-odoo-po`, `executando-odoo-financeiro` (cria pagamentos). Qualquer usuário logado (perfil `logistica`) pode invocá-las.
- **Mitigantes**: cada skill exige `--dry-run`+`--confirmar` intra-script; normalmente disparadas via subagente `gestor-estoque-odoo`; usuários internos conhecidos. Mas o gate **server-side** (única defesa que não depende do LLM cooperar) cobre só 3 de ~10 famílias. A própria feature (commit 1cd4cec7) nasceu porque "Alice usava o agente para fazer ajustes" — o mesmo risco vale para SEFAZ.
- **Fix**: estender o classificador (ou criar `_classify_odoo_write_restrito`) para cobrir as famílias WRITE críticas com a mesma whitelist, OU introduzir tiers (read-only / write-estoque / write-fiscal). Mudança localizada + env var. **Não é over-engineering — é fechar o gap da própria feature.**
- **Esforço**: BAIXO-MÉDIO. Classifico como **P1** (acima do P2 do parcial) por envolver transmissão SEFAZ irreversível em operação de R$16MM/mês.

### BUG-4 [P2] — `max_budget_usd=5` é hard-stop SEM tratamento → pode cortar WRITE Odoo no meio
- **[CONFIRMADO, dim 7 OPT-3]**: `client.py:1765` seta `options_dict["max_budget_usd"]=5.0`; semântica SDK 0.2.87 (`types.py:1659-1663`) = **hard stop** retornando `error_max_budget_usd`. **Re-verificado**: grep em `app/agente/` + `app/teams/` retorna **só a linha que SETA** — **nenhum handler** de `error_max_budget_usd`. O parser do `done` (`client.py:1346-1412`) só trata `interrupted/canceled` → o budget-exceeded cai no caminho genérico (texto parcial + `errors[]` cru, sem mensagem clara, sem retry).
- **Risco REAL**: spawn mais caro medido = **$8,17** (`gestor-estoque-odoo`). Uma operação de inventário/faturamento conduzida **diretamente** pelo agente principal (sem delegar) e que cruze $5 corta no meio de um WRITE SEFAZ/Odoo. Subagentes têm budget próprio (por isso o $8,17 não foi cortado).
- **Fix**: (1) tratar `subtype == 'error_max_budget_usd'` no parser → mensagem clara ("operação atingiu limite de custo, posso continuar de onde parei?"); (2) reavaliar $5 para WRITE Odoo — elevar para controller/admin OU desligar `max_budget_usd` no caminho principal e confiar no cap por-subagente. Cortar WRITE Odoo no meio é mais caro que o $ economizado.
- **Esforço**: BAIXO.

### BUG-5 [P2] — `/bot/answer` retorna 200 "ok" FALSO quando resposta do usuário se perde (0 subscribers)
- **[CONFIRMADO, dim 2 T5]**: `submit_answer` (`pending_questions.py:457-526`) retorna `False` quando `n_subs==0` (worker dono reciclado, TTL Redis 130s expirou, subscriber falhou). O handler `/bot/answer` (`bot_routes.py:380-395`) trata `success=False` como "race: já consumida, ok" e retorna `{"status":"ok"}` (200). **Mas a resposta NÃO foi entregue** — a thread bloqueada só destrava por timeout (`TEAMS_ASK_USER_TIMEOUT=120`), task acaba em `timeout`/`error`. O usuário vê "Resposta enviada", o agente nunca recebe. O próprio comentário (`pending_questions.py:504-509`) documenta que `n_subs=0` deveria ser 404 no web — o Teams mascara.
- **Fix**: `submit_answer` retornar `(handled, reason)`; no Teams responder erro recuperável quando `reason='no_subscribers'`.
- **Esforço**: BAIXO. Baixa frequência, mas é **perda silenciosa de turno** confirmada.

### BUG-6 [P2] — `debug_mode` (cross-user admin) provavelmente não propaga ao daemon thread do stream web
- **[HIPÓTESE — alta confiança, dim 8 SEC-4]**: `set_debug_mode(True)` é chamado na thread da request (`chat.py:537`), mas o stream roda em `Thread(target=run_async_stream, daemon=True)` (`chat.py:1290`) — **ContextVars não são herdados por `threading.Thread`**. Dentro do daemon, `set_perm_user_id` é re-chamado (`chat.py:740`) mas `set_debug_mode` **não** → `get_debug_mode()` no hook lê default `False`.
- **Impacto duplo**: (1) funcional — capacidade admin de investigar memórias/sessões de outro usuário via chat web provavelmente **não funciona**; (2) segurança — é **fail-SAFE** (default `False` = sem leak cross-user). Higiene: `cleanup_session_context` não reseta `_debug_mode` → resíduo teórico em threads reusadas.
- **Fix**: re-chamar `set_debug_mode(debug_mode)` dentro de `run_async_stream` + `set_debug_mode(False)` no finally. **Esforço**: BAIXO. Requer confirmação runtime (não executei o agente).

### BUG-7 [P2, segurança] — `admin_mode` SQL sem backstop determinístico contra DDL
- **[CONFIRMADO, dim 5 SEC-1]**: em `admin_mode=True` (users `{1,55,62}`), a ETAPA 3 faz bypass COMPLETO do `SQLSafetyValidator` (`text_to_sql.py:2029-2032`) — o único lugar com `FORBIDDEN_KEYWORDS` (DROP/ALTER/TRUNCATE) e `FORBIDDEN_FUNCTIONS`. O executor roda `read_write=True` (sem `SET TRANSACTION READ ONLY`). A descrição da tool **promete** "DROP/ALTER/TRUNCATE continuam bloqueados" (`text_to_sql.py:1160-1161`), mas isso só é aplicado pelo **prompt do Haiku Evaluator** — sem regex determinístico. Pior: `TEXT_TO_SQL_ADMIN_OVERRIDE` (default true) executa mesmo após Haiku rejeitar, se `deterministic_approved=True` (que não olha verbos).
- **Blast radius**: pequeno (3 admins confiáveis). Mas é furo de defense-in-depth: garantia documentada que depende 100% de LLM não-determinístico. Conteúdo malicioso colado por admin (arquivo/Odoo/portal) poderia via injeção induzir DDL.
- **Fix**: blocklist determinístico ANTES de `execute(read_write=True)` que vale TAMBÉM em admin_mode (bloquear sempre DROP/ALTER/TRUNCATE/GRANT/REVOKE/CREATE + `FORBIDDEN_FUNCTIONS`; permitir só SELECT/WITH/INSERT/UPDATE/DELETE). O override nunca deve pular ESTE guard.
- **Esforço**: BAIXO.

### Fora de escopo do agente (encaminhar aos donos dos módulos)
- **`inventario.movimentacoes_api`** [CONFIRMADO]: `AttributeError 'OdooConnection' has no attribute 'search_count'` (`PYTHON-FLASK-WB`, 12 ev) + `search() unexpected kwarg 'offset'` (`WD`, 5 ev). Rota de inventário, não agente/Teams. Fix: `execute_kw('model','search_count',...)` + `search_read(offset=,limit=)`.
- **Faults XML-RPC Odoo crônicos** (`P5`/`P6` 28/22 ev desde 23/04), `recebimento_views`, OCR tesseract path (`WA`), `executar_fluxo_l3_1_2_x` kwarg (`WC` — **ambiente `development`, máquina local NACOM052**, não produção). Todos fora do escopo 360.

---

## 3. Otimizações de custo & eficiência

> **Cobertura COMPLETA** (dim 7 + pesquisa 3 fecharam com dados reais de produção Render Postgres).

**Dados reais (14d):** 129 sessões (~9,2/dia), 42 spawns de subagente (~3,2/dia), **$87,62 em subagentes (~$6,3/dia)**, **cache hit 100%** nos subagentes (68,9M cache_read vs 3.274 input). Estimativa total **~$250-550/mês**. Para R$16MM/mês de operação, é **ruído** — confirma o veredito: **economia agressiva não paga; foco em LATÊNCIA e robustez.**

### OPT-2 [RESOLVIDO — NÃO É AÇÃO] — Prompt caching já ativo e instrumentado
- **[CONFIRMADO ATIVO]** (dim 4, dim 7, pesquisa 1, pesquisa 3): system prompt 100% estático (`client.py:497-535`), vars dinâmicas via hook `session_context`; flag `AGENT_PROMPT_CACHING` default true; cache hit/creation medidos (`client.py:1297-1328`) + `_alert_cache_miss` dispara Sentry em invalidação silenciosa (ativo desde 2026-04-15). Services Sonnet usam `cache_control: ephemeral` (grep confirma conformidade). **No path do CLI o caching é automático e não se adiciona por cima** (pesquisa 1). **Remover do roadmap como "quick win".**

### OPT-1 [GAP REAL, ROI por LATÊNCIA não por $] — Default Opus 4.8 + effort high pega TODA consulta read-only não-roteada
- **[CONFIRMADO, dim 7]**: default = `claude-opus-4-8`; web `effortLevel='auto'` → `resolveEffortLevel()` mapeia `opus → 'high'` (`chat.js:367-371`). O router (`model_router.py`) só rebaixa Opus→Sonnet em padrões explícitos (NF-PO, baseline, saudação, ≤2-3 palavras). **Consultas read-only de 4-15 palavras** ("tem pedido do Atacadão pra amanhã?", "quanto tem de palmito?") **não casam pattern** → caem em `default` (linha 192) = **Opus + high**. Read-only trivial servido pelo modelo mais caro e mais lento.
- **Por que importa**: o $ extra é pequeno; o que **dói é latência** (Opus+high adiciona thinking que o operador ocupado não precisa para um lookup). Proxy: subagentes Sonnet 23-67s vs Opus 150-210s.
- **Recomendação (cirúrgica)**: (a) ALTERNATIVA MAIS SIMPLES — mudar `resolveEffortLevel()` Opus default de `high`→`medium` em chat interativo (1 linha JS, reduz thinking sem trocar modelo); OU (b) adicionar verbos de consulta read-only ao `_FAST_MODEL_PATTERNS` (`tem (pedido|saldo|estoque)`, `quanto tem de`, `cadê`, `já (chegou|faturou)`). **NÃO** trocar o default global (WRITE Odoo + P1-P7 precisam de Opus). **Esforço**: BAIXO.

### OPT-4 [OTIMIZAÇÃO — latência] — Calibrar `effort: xhigh` por carga real do subagente
- **[CONFIRMADO, dim 7]**: a premissa "~13 subagentes Opus+xhigh" do parcial está **imprecisa** — são **8 Opus (7 xhigh) + 8 Sonnet** (metade da frota já é barata). `raio-x-pedido` e `analista-carteira` são predominantemente **read + síntese** ("coletar e organizar"), não raciocínio profundo — xhigh adiciona 191-207s de latência sem ganho relevante. `gestor-recebimento` é pipeline determinístico pós match NF-PO.
- **Recomendação**: rebaixar `raio-x-pedido`, `analista-carteira`, `gestor-recebimento` para `effort: high`; **MANTER xhigh** em auditor-financeiro, auditor-sped-ecd, especialista-odoo, desenvolvedor-integracao-odoo (raciocínio cross-area genuíno); **ADICIONAR** effort a `gestor-estoque-odoo` (WRITE crítico, hoje sem effort, mais caro = $29 total). **Esforço**: BAIXO (editar frontmatter). ROI: latência.

### OBS-1 [MELHORIA — desbloqueia decisões futuras] — Telemetria de custo do agente principal está cega
- **[CONFIRMADO, dim 7 + pesquisa 3]**: `agent_session_costs` (per-message do `CostTracker`) está **VAZIA** (0 linhas); `agent_sessions.data` não guarda `total_cost_usd` (0 de 129). A única telemetria persistida é `agent_invocation_metrics` (**só subagentes**). O custo do caminho principal (~277 sessões/mês, a maior fatia) é **invisível** — impossível medir custo/dia real ou detectar regressão pós-mudança de modelo/prompt.
- **Recomendação**: rastrear por que `CostTracker.record_cost` não persiste (provável: não invocado no path SSE/Teams, ou grava só em memória). **Ligar a persistência (1 callsite)** desbloqueia medição baseada em dado. **NÃO** construir dashboard novo (over-engineering para o volume). **Esforço**: BAIXO-MÉDIO.

### OPT — descartados como over-tuning
- **Haiku 4.5 para triviais** (pesquisa 3 P3-6): economia absoluta irrisória + risco de Haiku errar roteamento de follow-up que escala. **Low/over-tune — não fazer.**
- **Batch API, cache 1h TTL, cache diagnostics**: não aplicáveis a agente interativo / ~9 sessões/dia (pesquisa 1, pesquisa 3).

---

## 4. Melhorias de confiabilidade/qualidade

### CONF-1 [streaming web] — Persistência endurecida HOJE; monitorar, não reescrever
- Commits `d1345a66` (Fase 1) + `41d47ed6` (Fase 2) resolveram a race da sessão do Marcus (6 user / 0 assistant no banco). A camada SSE está **acima da média** (pesquisa 3): timeouts em cascata, deadline renewal, heartbeat 10s, fallback persistência+poll. Reconnect via `fetch()`+poll (não EventSource nativo) é **tradeoff deliberado correto** (permite body grande de anexos; a persistência cobre o gap). **Recomendação: monitorar 1 semana antes de qualquer mudança no generator SSE.**

### CONF-2 [Teams — pool process-local em 4 workers] — alinhar com a doc oficial
- **[CONFIRMADO, dim 2 T1/T2 + pesquisa 3 P3-1]**: o pool SDK (`client_pool.py`) é **process-local** e o Teams roda em 4 workers SEM afinidade de sessão. A doc oficial de hosting é explícita: "pin each session to one container/process using consistent hashing on sessionId". A 2ª mensagem da mesma conversa pode cair em outro worker → 2º subprocesso CLI (cenário DC-7). Agravado por **T2 [CONFIRMADO]**: o controle "max 1 task ativa por conversa" é SELECT-then-INSERT **sem UK nem `FOR UPDATE`** (`bot_routes.py:142-205`; `TeamsTask` sem UK em `(conversation_id, status)`) → duas mensagens concorrentes furam o limite.
- **orphan-kill NÃO cobre o caso** [CONFIRMADO, dim 2 T1]: `_cleanup_orphan_claude_processes` só roda nos `except` timeout/erro (`services.py:1329,1343`) e usa `pgrep -P os.getpid()` (só filhos do worker atual) — **não varre peer workers**. Respondendo à dúvida A1: **não, o orphan-kill não cobre cliente duplicado idle entre workers.**
- **Recomendação (pesquisa 3, a mais limpa)**: **rotear `/api/teams/*` → `:5001`** (1 worker do agente) no Caddyfile — elimina a classe DC-7 de vez (~3 linhas; Teams é async via Azure bridge, não precisa dos 4 workers). Complementar: **UK parcial** `UNIQUE (conversation_id) WHERE status IN ('pending','processing','awaiting_user_input','queued')` + tratar `IntegrityError` enfileirando.
- **Mitigado na prática** pelo baixo volume — **não é anti-pattern fatal**, mas é o caminho tecnicamente não recomendado.

### CONF-3 [Teams — commits diretos e recursão de fila] — higiene
- **T7 [CONFIRMADO]**: `process_teams_task_async:1411` usa `db.session.commit()` direto, violando R2 (`_commit_with_retry`); commits pós-stream (onde o SSL do Render pode ter caído após idle longo) também são diretos em pontos. Padronizar para `_commit_with_retry` + re-fetch nos commits pós-stream. **Esforço**: BAIXO. Sev baixa.
- **T6 [CONFIRMADO]**: a cadeia de fila é recursão aninhada (`_process_queued_task` chama `process_teams_task_async` na mesma thread, dentro do `try` do pai) → o `finally` do pai (cleanup ContextVars + `db.session.remove()`) só roda após o filho inteiro. Inofensivo no volume (fila max-1), mas frágil se T2 for furado. Transformar em LOOP iterativo. Sev baixa.

### CONF-4 [system prompt] — CONF-4 do parcial FECHADO (dim 4)
- **[CONFIRMADO]** o prompt é **maior do que a doc diz**: `system_prompt.md` real = **840 linhas / ~12,5K tok** (a doc `app/agente/CLAUDE.md` afirma ~2,1K tok e a quality review auditou ~407 linhas/2,7K — **STALE**, ~5x menor que o atual). Total estático (preset+system+briefing) ≈ **14,9K tok** lidos a CADA turno.
- **Cacheabilidade é ponto FORTE** (não mexer no prefixo estático). Mas há gordura removível SEM perder regra:
  - **R11/R12/R3.1 detalhados** (≈1.840 tok, ~15% do prompt) são checklists de operação WRITE Odoo com post-mortem inline (IDs de sessão de anti-padrão) — o agente principal **delega** essas operações. Mover para `.claude/references/` deixando só o gatilho de 1-2 linhas + ponteiro (mesmo padrão de P1-P7). Compliance não cai (a skill/subagente carrega a ref). **Ganho**: ~1.500-1.800 tok no prefixo cacheável de TODO turno.
  - **`<context_awareness>` duplicado** quase verbatim em `preset_operacional.md:84-92` + `system_prompt.md:355-360` (~100 tok); + parallel tools, comunicação/concisão, prompt-injection duplicados (~250-300 tok total no par preset/system).
  - **`prompt_inventario.md` é LIXO MORTO** em `app/agente/prompts/` — grep retorna ZERO referências de injeção; é um prompt de brainstorming de sessão única. Mover para `docs/` e corrigir `CLAUDE.md:55`.
- **I7 (entrega atômica de artefatos) sem enforcement [CONFIRMADO]**: 100% confiado à prosa (~375 tok); NENHUM PostToolUse detecta o link/artefato — frágil exatamente para o comportamento que motivou 2 sessões de frustração (4cc8c1f6 com 3 "gerou?", ed2fa68c com 12 "gerou?"). As skills geradoras já retornam `url_completa` em JSON → um hook PostToolUse pode anexar o link ao output / bloquear o "done". **Mesmo padrão do R9 audit hook.** Aplicabilidade ALTA (Marcus gera baseline/Excel recorrente). **Esforço**: MÉDIO.

### CONF-5 [memória — qualidade] — Budget de injeção INFINITO em Opus
- **[CONFIRMADO, dim 3 + pesquisa 2 GAP-CTX-1]**: `memory_injection.py:1036-1049` → `if "opus" in _model: base_budget=None` (sem corte). Como o default é Opus 4.8, **em produção o budget de memória é None**: as ~25-30 blocos de memória por boot (Tier 0/1/1.5/1.6 + 10 semânticas + 5 KG) entram **inteiros**, e o `USER_XML_POINTER` que enxuga user.xml grande **só atua quando budget≠None** (nunca em Opus). O KG entra com `similarity=0.5` **fixo** (proxy, não medida real) furando o scoring.
- **Nuance que rebaixa a severidade** (pesquisa 2): a CONTAGEM não é ilimitada (Tier 2 `.limit(15)` + `scored[:10]`, conteúdo truncado a 400 chars) → pior caso ~4-6K chars, não explode. É mais **débito-técnico/clareza** + custo de input recorrente que **bug**.
- **Fix**: teto brando mesmo em Opus (ex.: 12-16K chars) + `USER_XML_POINTER` independente do modelo. **Esforço**: BAIXO. Sev **medium**.

### CONF-6 [memória — fix de doc] — `get_or_create` JÁ é atômico (doc errada)
- **[CONFIRMADO REFUTADO como bug, dim 3]**: a nota em `app/agente/CLAUDE.md` ("`get_or_create()` NÃO é atômico... sem SELECT FOR UPDATE") **contradiz o código atual** (`models.py:402-413` JÁ usa `with db.session.begin_nested()` + `except IntegrityError: rollback + re-fetch`, com `UniqueConstraint('session_id')`). Corrigir a doc para evitar dev "consertar" algo já correto. **Outros refutados** (dim 3): `flag_modified` em JSONB CORRETO; dedup não-atômico é best-effort BAIXO risco (1 worker + UK em `(user_id,path)`); KG é transaction-safe (usa `db.engine.begin()`, não `db.session`).

---

## 5. Ampliação de recursos (sem over-engineering)

> Critério: só o que operador/controller usaria de fato a ~9 sessões/dia.

- **AMP-1 [vale a pena]** — Evento `processing` no card do Teams para tasks longas (transcrição PDF ~25min, caso real Marcus). A Fase 1 já adicionou o evento no web; estender ao Teams (que hoje depende de polling do Azure) fecha o gap de "parece travado". **Esforço**: MÉDIO.
- **AMP-2 [avaliar]** — `metrics_dashboard_service` já existe sem UI acessível. Expor read-only **só se Rafael/Marcus forem olhar**; caso contrário é over-engineering latente.
- **NÃO recomendo** — filas dedicadas extras, sharding de sessão, multi-região, rate-limiting sofisticado, circuit breaker (pesquisa 3: sem volume para "storm"). O volume não justifica.

---

## 6. Adoção de features SDK/Anthropic 2026

> **Cobertura COMPLETA** (pesquisa 1 verificou os 45 campos de `ClaudeAgentOptions` 0.2.87 por introspecção; pesquisa 2 cruzou best practices de prompt/memória). **Veredito geral: o wrapper está na fronteira correta de adoção — mais maduro que o consumidor típico.**

### Aplicabilidade ALTA (adotar)
- **NENHUMA adoção nova de alto impacto.** As que importam **já estão feitas**: `output_format`, `skills`, `effort/xhigh`, `thinking.display`, `max_budget_usd`, `strict_mcp_config`, `fallback_model`, `agents` dict, `session_store` (PostgresSessionStore), PreCompact hook, MCP Enhanced (outputSchema). Smart routing → Sonnet ativo.
- **I7 → enforcement via PostToolUse hook** (dim 4): não é "feature SDK nova", mas usa o padrão de hooks determinísticos que o SDK já oferece. **ROI alto** (UX recorrente). Único item de adoção com impacto real.

### Aplicabilidade MÉDIA (avaliar, não urgente)
- **`task_budget` por subagente** (pesquisa 1 item 9): campo EXISTE em 0.2.87, **não usado**. Cap de tokens por subagent como salvaguarda contra runaway de um Opus xhigh em loop (`max_budget_usd` por request já é a rede maior). **Esforço**: BAIXO (1 campo no `agent_loader`). Hardening **opcional**.
- **SDK upgrade além de 0.2.87**: só com janela de teste — histórico mostra fragilidade por versão (SDK 0.1.60 subagent bugs). Não fazer sem necessidade concreta.

### Aplicabilidade BAIXA (ignorar — adotar seria redundante ou regressivo)
- **Prompt caching / context-editing / extended-context 1M**: já automáticos no CLI ou nativos do Opus 4.8 — flags log-only CORRETAS (pesquisa 1).
- **Memory tool server-side (`memory_20250818`) / CMA Memory / Managed Agents**: adotar seria **REGRESSÃO** (duplica/substitui a stack própria superior de agent_memories + Voyage + KG).
- **Cache diagnostics, OTEL nativo, Batch API, cache 1h TTL**: over-engineering para o volume.

---

## 7. Over-engineering ATUAL (o que já existe demais)

> dim 3 deu a análise concreta por-service que o OE-1 do parcial não detalhou. **Custo financeiro da cadeia inteira ≈ US$ 2-3/mês — IRRELEVANTE. O custo real é superfície de manutenção (~10,5K LOC, ~10 flags, migrations, cada service podendo poluir sessão/quebrar stream best-effort).**

### OE-1 [CONFIRMADO] — 17 services de inteligência: o que MANTER / CONGELAR / APOSENTAR

**MANTER** (valor real, custo idle ~zero):
- `intersession_briefing` (576 LOC, **zero LLM**, continuidade entre sessões — o que mais agrega a operador recorrente)
- `session_summarizer` (480, base do briefing, ~$0,16/mês)
- `memory_consolidator` (736, higiene, transaction-safe, raramente dispara)
- `pattern_analyzer` **somente extração empresa+pessoal** (a memória prescritiva é o núcleo de valor; disciplina prescritivo×descritivo é boa)
- `sentiment_detector` (214, **zero API**, heurística local — **correção ao parcial**: NÃO aposentar, não há ganho)
- `metrics_dashboard_service` + `artifact_service` (telemetria/produto, não "inteligência")

**CONGELAR** (não estender; reavaliar ao próximo erro/manutenção):
- **`knowledge_graph_service` (1082 LOC) — candidato nº1 a APOSENTAR de fato** [dim 3 seção B]: o grafo nunca atinge massa crítica a ~9 sessões/dia para o "hop 2" superar a busca semântica pura do Tier 2; injeta no boot com `similarity=0.5` fixo furando o scoring; em Opus (budget infinito) entra sem corte. Desligar `MEMORY_KNOWLEDGE_GRAPH=false` provavelmente não causa perda mensurável e remove 1082 LOC + 1 query Voyage/boot. (Ponto a favor: é transaction-safe, não polui sessão.)
- `friction_analyzer` (490) + `recommendations_engine` (279) + `insights_service` (1605) — **zero LLM**, mas só servem um dashboard admin que o perfil quase nunca abre. **Correção ao parcial**: não "aposentar com esforço" — só CONGELAR (custo idle zero).
- `pattern_analyzer` sub-funções profile+patterns (valor marginal a baixa frequência)
- `sql_evaluator_falses_service` (387, uso raro)

**AVALIAR DESLIGAR** (ROI questionável, custo recorrente):
- **`suggestion_generator` (223) — o ÚNICO com custo+latência POR TURNO web** (Sonnet pós-stream, ~$0,90-1,50/mês mas + latência no fim de CADA resposta para 2-3 sugestões que operador apressado ignora). **Teste A/B**: desligar `USE_PROMPT_SUGGESTIONS` 2 semanas; se ninguém reclamar, desligar de vez.
- `improvement_suggester` (602) — **JÁ OFF** (`USE_IMPROVEMENT_DIALOGUE=false`); manter OFF.

### OE-2 [parcial] — Pós-sessão sempre dispara cadeia completa
- Todo turno Teams concluído dispara `run_post_session_processing` (summary→extração→memórias→embedding) em thread. Tornar etapas mais caras (KG, embedding) condicionais (só sessões com N+ turnos ou batch 1x/dia). Baixa prioridade.

### OE-3 [aceitável, NÃO mexer] — Split Caddy + 2 gunicorn
- **CONFIRMADO justificado** (pesquisa 3 P3-8): resolve o per-process do SDK por afinidade minimalista (1 worker ⇒ sessão sempre no mesmo processo, sem consistent-hashing). **É a solução mínima correta, não over-engineering.**

---

## 8. Documentação desatualizada

- **DOC-1 [CONFIRMADO, P1 de doc]** — `teams/CLAUDE.md:110-113,151` diz "v2 efêmero ATIVO / v3 = Rollback (DC-7)", mas `feature_flags.py:422` default **true** + `services.py:1298-1299` comentário "v3 persistente, v2 desligado em 2026-03-27". **Risco real**: dev futuro "consertar" para o lado errado (exatamente A1). Atualizar para refletir v3 (pool persistente) ATIVO + documentar process-local em 4 workers.
- **DOC-2 [CONFIRMADO, P1 de doc, dim 4]** — `app/agente/CLAUDE.md` "Arquitetura de Prompts" afirma `system_prompt.md ~2,1K tok` / total ~2,7K. **REAL: ~12,5K / ~14,9K tok** (não conta `empresa_briefing.md`). Rotula "R0-R10"/"v4.2.0" mas o arquivo é R0-R12 + I2-I7 + L1-L4, version 4.3.3. A quality review (`STUDY_..._QUALITY_REVIEW.md:8`) auditou um prompt **~5x menor** — STALE. Corrigir evita que a próxima sessão adicione regras achando que o prompt tem 2,7K tok.
- **DOC-3 [CONFIRMADO, dim 3]** — `app/agente/CLAUDE.md` Gotchas: "`get_or_create()` NÃO é atômico" contradiz o código (já usa `begin_nested`). Corrigir.
- **DOC-4 [CONFIRMADO, dim 4]** — `prompt_inventario.md` em `app/agente/prompts/` é artefato de sessão (não injetado); `CLAUDE.md:55` o descreve como "prompt operacional" — enganoso. Mover para `docs/`.
- **DOC-5 [CONFIRMADO, baixo]** — `anthropic` local `0.84.0` vs prod `0.98.1` (afeta só testes locais de services que usam Messages API direto — features `stop_details`/`APIStatusError.type` exigem 0.87+). `pip install -U anthropic==0.98.1` no venv.
- **DOC-6 [baixo, dim 2 T5]** — `teams/CLAUDE.md` não menciona que cross-worker AskUserQuestion é resolvido por Redis pub/sub (`AGENT_REDIS_PENDING_QUESTIONS` default true) — doc fala só de Event local.
- **DOC-7 [higiene, fora do agente]** — `MEMORY.md` 27,9KB > limite 24,4KB (só parte carregada). Entradas de índice longas.

---

## 9. Segurança (riscos reais)

> dim 8 + dim 5. **Postura geral: defesas centrais sólidas (fail-closed, SQL read-only no Postgres, audit hook blindado, cross-user memory bem protegido). Os gaps são de defense-in-depth, blast radius pequeno (usuários internos, 3 admins confiáveis).**

| ID | Risco | Sev | Status |
|----|-------|-----|--------|
| **SEC-1 / BUG-3** | Gate WRITE-Odoo cobre só 3 de ~10 famílias destrutivas (SEFAZ irreversível aberto) | **HIGH** | §2 BUG-3 — estender classificador + whitelist |
| **SEC-2** | Input Teams NÃO passa por `sanitize_user_input` (web passa; Teams = **0 callsites**, re-verificado) — assimetria Layer-1 | MEDIUM | Quick win: 1 import + 1 linha em `processar_mensagem_bot` |
| **SEC-3** | Prompt-injection via TOOL RESULTS (Odoo/web/SQL) sem Layer-4 PostToolUse nem `<meta_instruction_alert>` (grep = 0 matches no system_prompt) — input usuário e memórias JÁ protegidos | MEDIUM | Adicionar `<meta_instruction_alert>` + `<security_invariants>` (pronto no doc §5.1/5.2, ~5 linhas, custo zero) — maior ROI; PostToolUse escapando `<system>`/`<instructions>` é opcional/médio |
| **BUG-7 / SEC(SQL)-1** | `admin_mode` SQL bypassa validator → DDL só barrado por prompt do Haiku (não código) | MEDIUM | §2 BUG-7 — blocklist determinístico que vale em admin |
| **SEC(SQL)-2** | Fallback `user_id==0` adota admin se houver exatamente 1 sessão admin ativa (fail-OPEN) | LOW | Trocar por fail-closed (ContextVar=0 ⇒ usuário comum, nunca admin por inferência) |
| **BUG-6 / SEC-4** | `debug_mode` não propaga ao daemon thread (fail-SAFE: feature quebra, sem leak) + sem reset de ContextVar | LOW-MED | §2 BUG-6 |
| **MCP-1** | Playwright (13 tools) fora do enhanced wrapper → sem `additionalProperties:false` (param alucinado ignorado) | LOW | Migrar para `enhanced_tool` |

**Confirmações de saúde (sem ação)**: `is:unresolved PermissionError` = 0; fail-closed permission = 0; cross-user memory exige `get_debug_mode()` server-side (não controlável pelo LLM) + log WARNING; audit hook usa `shlex.quote()` + `updatedInput` isolado (race-free). `subagent_validator` é real mas **advisory** (Haiku score, só sinaliza ícone ⚠, não bloqueia) — aceitável no volume. Camada Postgres READ ONLY para usuário comum é **ponto forte**. **NÃO recomendo Layer-5 leak-detection** (over-engineering).

---

## 10. Roadmap priorizado (impacto × esforço)

### Quick wins (baixo esforço, alto/médio impacto) — fazer primeiro
| # | Item | Tipo | Esforço | Impacto | Evidência |
|---|------|------|---------|---------|-----------|
| 1 | **BUG-1**: `registrar()` do pipeline em `begin_nested()` (3 callsites) ou dentro do método | bug/hardening | BAIXO | ALTO (evita cascata em WRITE SEFAZ) | `operacao_odoo_auditoria.py:90-91` vs hook `:181` |
| 2 | **BUG-2**: rollback defensivo nos `except` read-only do `memory_mcp_tool` + `_execute_with_context` incondicional + `before_request` no blueprint Teams | bug | BAIXO-MÉD | ALTO (3 users, regressed) | Sentry `EG`; `bot_routes.py:276,341` |
| 3 | **BUG-3/SEC-1**: estender gate WRITE-Odoo às famílias críticas (SEFAZ/MO/picking/financeiro) | segurança | BAIXO-MÉD | ALTO (SEFAZ irreversível) | `permissions.py:320-390,808-836` |
| 4 | **DOC-1+DOC-2**: corrigir `teams/CLAUDE.md` (v3 ATIVO) e tamanho do prompt no `agente/CLAUDE.md` | doc | BAIXO | ALTO (evita decisão errada de dev) | `feature_flags.py:422`; prompt 12,5K real |
| 5 | **BUG-4/OPT-3**: tratar `error_max_budget_usd` + reavaliar $5 em WRITE Odoo | bug | BAIXO | MÉD-ALTO (robustez WRITE) | `client.py:1765`, **sem handler** (verificado) |
| 6 | **SEC-2**: `sanitize_user_input` no Teams | segurança | BAIXO | MÉDIO | `teams/services.py` (0 callsites) |
| 7 | **SEC-3**: `<meta_instruction_alert>` no system_prompt (pronto no doc) | segurança | BAIXO | MÉDIO | `PROMPT_INJECTION_HARDENING.md §5` |
| 8 | **OPT-1**: `resolveEffortLevel()` Opus → `medium` (1 linha JS) | otimização | TRIVIAL | MÉDIO (latência) | `chat.js:367-371` |
| 9 | **OPT-4**: rebaixar xhigh→high em raio-x/analista-carteira/recebimento; +effort em gestor-estoque-odoo | otimização | BAIXO | MÉDIO (latência) | `.claude/agents/*.md` |
| 10 | **CONF-5/CONF-6**: teto brando de memória em Opus + corrigir doc `get_or_create` | otimização/doc | BAIXO | MÉDIO | `memory_injection.py:1036-1049` |

### Médio prazo
| # | Item | Tipo | Esforço | Impacto |
|---|------|------|---------|---------|
| 11 | **CONF-2**: rotear `/api/teams/*` → `:5001` + UK parcial em `TeamsTask` (elimina DC-7) | confiabilidade | MÉDIO | MÉDIO |
| 12 | **CONF-4**: mover R11/R12/R3.1 para reference (ganho ~1.500-1.800 tok/turno cacheável) + dedup `<context_awareness>` + remover `prompt_inventario.md` | otimização | MÉDIO | MÉDIO |
| 13 | **CONF-4/I7**: PostToolUse hook de entrega de artefato (link determinístico) | confiabilidade | MÉDIO | MÉDIO (UX Marcus) |
| 14 | **AMP-1**: evento `processing` no card Teams para tasks longas | ampliação | MÉDIO | MÉDIO (UX Marcus) |
| 15 | **OBS-1**: ligar persistência de `agent_session_costs` (1 callsite) | observabilidade | BAIXO-MÉD | MÉDIO (desbloqueia medição) |
| 16 | **BUG-5**: `/bot/answer` distinguir "no_subscribers" de "já respondida" | bug | BAIXO | MÉDIO (perda silenciosa) |
| 17 | **BUG-7**: blocklist determinístico de DDL em admin SQL | segurança | BAIXO | MÉDIO |
| 18 | **CONF-3/T7+T6**: padronizar `_commit_with_retry` pós-stream Teams + fila iterativa | débito | BAIXO-MÉD | BAIXO-MÉD |
| 19 | **BUG-3-inv** (fora do agente): `inventario.movimentacoes_api` (search_count/offset) — **encaminhar** | bug | BAIXO | MÉDIO |

### Avaliar (não fazer sem gatilho)
| # | Item | Nota |
|---|------|------|
| 20 | **OE-1**: desligar `MEMORY_KNOWLEDGE_GRAPH=false` (KG é o candidato nº1) + teste A/B `suggestion_generator` | KG/suggestions têm ROI questionável; demais services só CONGELAR (custo idle zero) — não deletar proativamente |
| 21 | **`task_budget`** por subagente (hardening opcional) | Só se aparecer runaway; `max_budget_usd` já é rede maior |
| 22 | **SDK upgrade** além de 0.2.87 | Só com janela de teste (histórico de fragilidade por versão) |
| 23 | **BUG-6/SEC-4**: propagar `set_debug_mode` ao daemon thread + reset | Confirmar runtime; fail-SAFE hoje |
| 24 | **AMP-2**: UI para metrics_dashboard / **MCP-1** Playwright enhanced | Só se forem usar de fato |
| 25 | **DESCARTAR**: Haiku para triviais, Batch API, circuit breaker, cache 1h, OTEL, Layer-5 leak-detection | over-engineering para ~9 sessões/dia |

---

## Anexo — Cobertura e honestidade

- **Cobertura COMPLETA**: todas as 8 dimensões + 3 pesquisas + parcial presentes e integradas. Nenhuma seção ficou com cobertura parcial (ao contrário do relatório parcial, que rodou antes dos subagentes). As hipóteses abertas do parcial foram FECHADAS: OPT-2 (caching) = ativo/100% hit; CONF-4 (prompt) = auditado (12,5K tok, gordura em R11/R12); custo = dado real Render ($87,62/14d subagentes).
- **Re-verificações de evidência load-bearing** confirmadas pelo líder: BUG-1 (`registrar` add+flush sem savepoint vs hook `begin_nested:181`), Teams sanitize (0 callsites), `error_max_budget_usd` (só setter, sem handler), `/bot/status:276` e `/bot/answer:341` sem rollback defensivo.
- **Não executei o agente** (sessão read-only). BUG-6/SEC-4 (propagação de ContextVar ao daemon) é [HIPÓTESE] de alta confiança, pendente de confirmação runtime.
- **Deploy**: live `41d47ed6` contém as correções A2 (confirmado no parcial via Render).
- **Marcações**: [CONFIRMADO] = evidência verificada · [HIPÓTESE] = plausível, não fechado · refutados explicitamente descartados (A2/A3/A4, `get_or_create`, `flag_modified`, path-traversal de memória que é Postgres não filesystem).

## Contexto

Relatorio integrado da avaliacao 360 do agente web (SSE :5001 + Teams :5002), de 2026-05-29 com errata em 2026-05-30. Os achados (ex.: BUG-1, CONF-2) geraram fixes diretos no codigo — ver `app/odoo/models/operacao_odoo_auditoria.py:90` e `app/teams/CLAUDE.md`. Documento de referencia historica da avaliacao.

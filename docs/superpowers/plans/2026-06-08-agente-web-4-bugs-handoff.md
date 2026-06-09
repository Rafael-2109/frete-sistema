<!-- doc:meta
tipo: how-to
camada: L3
sot_de: handoff dos 4 bugs do Agente Web diagnosticados na sessao 2026-06-08 (causas confirmadas) + resumo do redesenho de memoria entregue na mesma sessao
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-09
-->

# Agente Web — 4 Bugs (causas confirmadas) + Handoff do Redesenho de Memoria

> **Papel:** handoff entre sessoes. Origem: sessao 2026-06-08 (Rafael + Opus 4.8) que partiu de 5 problemas observados numa sessao do Agente Web. **1 dos 5 foi resolvido** (list_memories) junto do redesenho do formato canonico de memorias; **os 4 restantes ficam documentados aqui** com causa-raiz confirmada, fontes (`arquivo:linha`), fix proposto e esforco/risco — prontos para uma sessao dedicada. Princípio: nao atacar frontend SSE/JS sem validacao no browser.

> **STATUS 2026-06-09 (sessao Opus 4.8):** os **4 bugs foram RESOLVIDOS** (TDD).
> - **Onda 1 (#1 logs de boot, #3 `--json`)** — ✅ RESOLVIDA E VALIDADA (backend + smoke E2E; stdout 100% limpo). Sem pendencia.
> - **Onda 2 (#4 badge subagente, #5 transcript S3)** — ✅ CODIGO RESOLVIDO (59 testes verdes; `USE_S3=true` confirmado em PROD). **Pendente: validacao no browser pelo Rafael** (badge com nome real durante streaming; botao "Tentar restaurar" no modal pos-deploy).
> Detalhe do que cada fix tocou: ver os blocos de cada bug abaixo (atualizados com **RESOLVIDO**).

## Indice
- [Parte A — O que foi ENTREGUE nesta sessao (formato canonico de memorias)](#parte-a)
- [Parte B — Os 4 BUGS restantes (causas confirmadas)](#parte-b)
- [Parte C — Plano de ataque sugerido](#parte-c)

---

## Parte A — O que foi ENTREGUE (formato canonico de memorias) {#parte-a}

Redesenho do formato das memorias do Agente Web — **commitado na main** (`f67bee8da`), migration via build one-shot (`ad3c78027`, removido em `78bafade5` local nao-pushado).

**Memoria detalhada:** `memory/formato_canonico_memorias_agente.md` (Claude Code dev memory).

Resumo: campos discriminantes das memorias estruturadas (heuristica/armadilha/protocolo/correcao) agora vivem em coluna `agent_memories.meta` JSONB (fonte de verdade, indice GIN); `content` vira derivado em formato **sentinela** (`[kind:dominio] titulo\nWHEN:\nDO:\nMETA: nivel=N`). Serializador puro novo `app/agente/services/memory_format.py` (parse de 5+ formatos legados, 92,1% cobertura validada contra 535 memorias de PROD). `list_memories` virou INDICE navegavel (resolve o estouro de tokens = bug #2 original). Geradores gravam meta; consumidores preferem meta via `getattr`. 79 testes; revisado por 2 code-reviewers (4 fixes). **Deploy: migration roda no build do deploy `ad3c78027`** (coluna criada antes do start).

---

## Parte B — Os 4 BUGS restantes (causas confirmadas) {#parte-b}

> O bug **#2 (list_memories estourava tokens)** foi RESOLVIDO na Parte A.

### BUG #1 — Logs de boot poluindo o stdout das tools

> **✅ RESOLVIDO (2026-06-09)** — helper `app/utils/boot_log.py` (gated por `NACOM_QUIET_BOOT`, sempre stderr, `force=True` p/ erros) + ~14 prints de boot convertidos (import + `create_app`, incl. `[POOL]`/`Tabelas criadas` que faltavam nesta lista) + hook `hooks.py` prefixa `NACOM_QUIET_BOOT=1` em todo comando Bash. Smoke E2E: stdout 100% limpo. 13 testes. (Logs `logging.*` estruturados ficam fora do escopo — categoria distinta de `print`.)

- **Sintoma:** ao rodar scripts de skill via Bash, o stdout vem com `✅ Sentry inicializado`, `✅ Tipos PostgreSQL registrados`, `⚠️ ADAPTER ATIVO: PreSeparacaoItem`, etc.
- **Causa-raiz:** sao `print()` em **escopo de modulo** (executam no `import app`, antes de `create_app()`). A maioria vai pra `sys.stderr` (visivel porque o comando usava `2>&1`); **2 vao pra stdout REAL**.
- **Fontes:**
  - stdout real: `app/database/__init__.py:36,39`
  - stderr: `app/__init__.py:132,158,199,205` · `app/utils/pg_types_production.py:39` · `app/utils/pg_types_config.py:46` · `app/carteira/models.py:656` · `app/estoque/models.py:11`
  - `--quiet`/`silenciar_stdout()` (`app/odoo/estoque/_cli_utils.py:34`) NAO cobre: os prints ocorrem no import, antes do redirect.
- **Fix proposto:** (a) `app/database/__init__.py:36,39` -> `file=sys.stderr`; (b) helper `boot_log(msg)` gated por env `NACOM_QUIET_BOOT`, substituindo os ~8 prints de boot; scripts CLI setam a env ANTES do `import app`.
- **Esforco M · risco baixo-medio · NAO precisa browser** (testavel: rodar script e ver stdout limpo).

### BUG #3 — `--json` deduzido onde o script usa `--formato json`

> **✅ RESOLVIDO (2026-06-09)** — `--json` aceito como alias de `--formato json` em `consultar_quants.py` e `consultando_status_entrega.py` (via `build_parser()` + `_aplicar_alias_json()`, precedência sobre `--formato`); flag documentado no `SKILL.md`. 6 testes. Confirmado que `exportar.py` (`--formato {excel,csv,json,imagem}`) é semântica diferente — fora de escopo.

- **Sintoma:** agente rodou `consultar_quants.py ... --json` e falhou (`Expecting value`); o flag correto e `--formato {json,tabela}`.
- **Causa-raiz:** `consultar_quants.py:77` usa `--formato {json,tabela}` (default `tabela`) — **fora da convencao majoritaria** `--json` booleano (9+ scripts de `rastreando-odoo`/`gerindo-agente`). O `SKILL.md` de `consultando-quant-odoo` **nao documenta** o flag de saida -> o agente generalizou.
- **Fontes:** `.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py:77` · `.claude/skills/rastreando-odoo/SCRIPTS.md` (convencao `--json`) · `.claude/skills/consultando-quant-odoo/SKILL.md` (silente sobre o flag).
- **Fix proposto (ja aprovado pelo Rafael):** aceitar `--json` como alias de `--formato json` em `consultar_quants.py` (retrocompativel) + documentar o flag no `SKILL.md`. Verificar se ha OUTROS scripts com a mesma divergencia (`consultando_status_entrega.py` tambem usa `--formato`).
- **Esforco P · risco muito baixo · NAO precisa browser.**

### BUG #4 — Subagente exibido como "local agent" sem nome

> **✅ RESOLVIDO no codigo (2026-06-09) — validar no browser.** Correcao: imprecisao confirmada na investigacao — o Caminho 2 morria no **filtro `chat.js:1331`** (`task_type='subagent' !== 'local_agent'`), ANTES da idempotencia 1339. Corrigidos os dois: filtro rejeita só `local_bash`; idempotencia faz **upgrade** do badge (generico→nome real, nunca downgrade), persistindo em `dataset.summary`. `node --check` OK. **Pendente: ver renderizar no chat** (`$0.0000`/formato uniforme deixados p/ validacao visual — `cost_usd` é removido p/ não-admin em `chat.py:745`).

- **Sintoma:** durante a execucao a linha do subagente nasce como "local agent" (sem nome); ao concluir vira "subagente (qtd) tools - tempo - $0.0000". Desejado: nome do agente · comando · tools · tokens · tempo, durante E ao fim.
- **Causa-raiz:** o nome real (`agent_type`) existe no hook `SubagentStart` mas **NAO no `TaskStartedMessage` do SDK**. Ha **2 caminhos** de evento `task_started` com o mesmo `task_id`; o correto (pubsub com `agent_type`) e **descartado por idempotencia** no front.
- **Fontes:**
  - SDK sem `agent_type`: `.venv/.../claude_agent_sdk/types.py:1060-1073`
  - Caminho 1 (sem nome): `app/agente/sdk/client.py:958-977` -> `app/agente/routes/chat.py:1021-1026` -> `app/static/agente/js/chat.js:1337`
  - Caminho 2 (com nome, descartado): `app/agente/sdk/hooks.py:612-619` (pubsub) -> guard idempotencia `app/static/agente/js/chat.js:1339`
  - Card final + custo: `app/static/agente/js/chat.js:1396-1449`; `$0.0000` = `cost_usd` sanitizado p/ nao-admin em `app/agente/routes/chat.py:733-755`
- **Fix proposto:** permitir que o Caminho 2 (pubsub com `agent_type`) ATUALIZE o badge mesmo se a linha ja existe (em vez de descartar em `chat.js:1339`); formato uniforme nome·comando·tools·tokens·tempo em start/progress/summary.
- **Esforco M · risco medio · PRECISA browser** (validar streaming no chat web — Playwright/manual).

### BUG #5 — "Transcript nao encontrado / sessao arquivada" apos 5-10 min

> **✅ RESOLVIDO no codigo (2026-06-09) — validar no browser.** (a) `get_subagent_transcript` (`subagent_reader.py`) tenta `restore_session_from_s3()` + re-busca antes do 404 (espelha `list_session_subagents`); (b) botao "Tentar restaurar do arquivo" (`chat.js`) ativado como retry (reabre o modal → endpoint já tenta S3). `USE_S3=true` CONFIRMADO em PROD (58 sessões com `s3_archive`). 2 testes novos. **Pendente: validar no modal pós-deploy.**

- **Sintoma:** apos ~deploy, o modal do subagente mostra "Transcript nao encontrado. A sessao pode ter sido arquivada." + botao inerte "Tentar restaurar do arquivo".
- **Causa-raiz (CONFIRMADA por Rafael):** transcript de subagente vive em `/tmp/.claude/.../subagents/*.jsonl` e o **`/tmp` do Render e apagado entre deploys**. (Descartado: worker-recycle `gunicorn_config_agente.py:34` `max_requests=0`; multi-worker `workers=1`.)
- **Agravantes:** `get_subagent_transcript` **nao tenta S3 restore** (`app/agente/sdk/subagent_reader.py:659-708`) — so `list_session_subagents` tenta (`:120-143`); o botao "Tentar restaurar" e **stub `disabled`** sem handler (`app/static/agente/js/chat.js:1776`).
- **Fontes:** `app/static/agente/js/chat.js:1654,1776` · `app/agente/routes/subagents.py:181-185` · `app/agente/sdk/subagent_reader.py:659-708` (sem S3), `:120-143` (S3 so na lista) · `app/agente/sdk/session_archive.py:5` (doc /tmp efemero) · `.env:16` (`USE_S3=false` local).
- **Fix proposto:** (a) `get_subagent_transcript` tenta `restore_session_from_s3()` antes do 404; (b) ativar o botao com handler que chama o endpoint de restore. **Depende de `USE_S3=true` em PROD** (confirmar).
- **Esforco M · risco baixo-medio · PRECISA browser + confirmar USE_S3.**

---

## Parte C — Plano de ataque (EXECUTADO 2026-06-09) {#parte-c}

| Onda | Bugs | Natureza | Status |
|---|---|---|---|
| 1 (rapida) | #3, #1 | backend/CLI, testavel sem browser | ✅ **CONCLUIDA E VALIDADA** (smoke E2E: stdout limpo) |
| 2 (frontend) | #4, #5 | SSE/JS + S3 | ✅ **CODIGO CONCLUIDO** (59 testes; `USE_S3=true` PROD OK) · ⏳ **falta validacao browser (Rafael)** |

Ambas as ondas implementadas com TDD numa sessao (Opus 4.8). **Validacao no browser pendente** para #4 (badge com nome real durante streaming) e #5b (botao "Tentar restaurar" no modal pos-deploy) — conforme o principio "NAO mexer no streaming/modal sem ver renderizar". Commits: Onda 1 e Onda 2 separados.

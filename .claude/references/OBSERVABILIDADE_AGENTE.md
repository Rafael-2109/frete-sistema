<!-- doc:meta
tipo: reference
camada: L2
sot_de: observabilidade-agente
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-19
-->
# Observabilidade do Agente Web — onde mora cada coisa

> **Papel:** mapa unico de FONTES de verdade da observabilidade do Agente Web/Teams — custo, tokens, transcript, métricas e contagem de subagentes. **Abra quando:** precisar responder "qual o custo / o que rodou / quantos agentes / o transcript de uma sessão" sem caçar pela base.

## Índice
- [Regra de ouro](#regra-de-ouro)
- [Mapa: onde mora cada coisa](#mapa-onde-mora-cada-coisa)
- [Convenções que evitam erro](#convencoes-que-evitam-erro)
- [Como cruzar (queries)](#como-cruzar-queries)
- [Gotchas conhecidos](#gotchas-conhecidos)

## Regra de ouro

**O custo de UMA sessão = principal + subagentes, e eles vivem em tabelas DIFERENTES.**

- Principal → `agent_session_costs` / `agent_sessions.total_cost_usd`.
- Subagentes → `agent_invocation_metrics` (conta separada; NÃO está no `total_cost_usd` da sessão).

Somar só uma fonte subestima o custo real. Exemplo medido (sessão `17b68633`, 2026-06-19): principal **$31,92** + subagentes **$17,77** = **~$49,69** real — quem olhasse só `total_cost_usd` veria $31,92 (−36%).

## Mapa: onde mora cada coisa

| Quero ver… | Fonte | Campos-chave | Cuidado |
|---|---|---|---|
| **Custo por turno (principal)** | tabela `agent_session_costs` | `cost_usd`, `input/output/cache_*_tokens`, `message_id`, `session_id`, `user_id`, `recorded_at` | 1 linha/turno; só principal (`tool_name` null); existe desde **2026-06-05** (flag `USE_COST_TRACKER_PERSIST`). `cost_usd` = custo do turno (delta) após fix 2026-06-19 |
| **Custo total da sessão (principal)** | `agent_sessions.total_cost_usd` | — | = soma dos deltas do principal. NÃO inclui subagentes |
| **Custo / turnos / tokens de SUBAGENTE** | tabela `agent_invocation_metrics` | `cost_usd`, `num_turns`, `*_tokens`, `agent_type`, `agent_id`, `session_id`, `user_id`, `recorded_at`, `started_at` | 1 linha/invocação (spawn→stop). Flag `USE_INVOCATION_METRICS_PERSIST`. `cost_usd` = total da invocação (correto, não inflado). **`started_at`** corrigido p/ Brasil-naive em 2026-06-19 |
| **Quantos / quais subagentes numa sessão** | `agent_invocation_metrics` WHERE `session_id=` | `agent_type`, COUNT | invoc > sessões = mesmo especialista re-chamado |
| **Transcript real / completo (principal)** | tabela `claude_session_store` | `session_id`, `seq`, `entry` (JSONL) | TUDO que entra no contexto: system prompt, tool_use/tool_result, thinking. É daqui que vem o cache_read. NÃO confundir com `data->messages` |
| **Texto user + resposta final + tokens/turno** | `agent_sessions.data->messages` | `role`, `content`, `tokens`, `tools_used` | só o texto final (pequeno); **não** tem tool_results nem thinking |
| **Steps por turno** | tabela `agent_steps` | `step_uid`, `tools_used`, `*_tokens`, `model` | 1 linha/turno (`step_uid = {session_id}:{turn_seq}`) |
| **Transcript de subagente** | disco `/tmp/.claude/projects/*/{session}/subagents/agent-*.jsonl` + S3 archive + `/tmp/subagent-findings/` | — | efêmero (Render `/tmp`); arquivado em S3 ao expirar |
| **Dashboard de custo** | rota `/agente/insights` | lê `agent_session_costs` | — |
| **Dashboard de subagentes** | rota `/agente/admin/metrics` | `services/metrics_dashboard_service.py` → `agent_invocation_metrics` | admin |

## Convenções que evitam erro

- **Timezone:** todos os timestamps de observabilidade são **Brasil-naive** (`REGRAS_TIMEZONE.md`). `recorded_at` usa `agora_*_naive`; `agent_invocation_metrics.started_at` vem do JSONL e é convertido UTC→Brasil em `subagent_reader._parse_iso_timestamp`. O JSONL do CLI grava em **UTC** (sufixo `Z`).
- **`cost_usd` é por-turno (delta), não acumulado.** O SDK reporta `ResultMessage.total_cost_usd` ACUMULADO; a gravação converte em delta (`pricing.turn_cost_from_cumulative`). Ver [Gotchas](#gotchas-conhecidos).
- **`session_id`:** UUID (web) ou prefixo `teams_*` (Teams). Em `agent_invocation_metrics` e `claude_session_store` é o MESMO `sdk_session_id` da sessão.

## Como cruzar (queries)

Custo TOTAL real de uma sessão (principal + subagentes):
```sql
SELECT
  (SELECT COALESCE(SUM(cost_usd),0) FROM agent_session_costs   WHERE session_id = :sid) AS principal,
  (SELECT COALESCE(SUM(cost_usd),0) FROM agent_invocation_metrics WHERE session_id = :sid) AS subagentes;
```

Subagentes de uma sessão (quantos, quais, custo):
```sql
SELECT agent_type, COUNT(*) AS invocacoes, SUM(num_turns) AS turnos, ROUND(SUM(cost_usd),2) AS custo
FROM agent_invocation_metrics WHERE session_id = :sid GROUP BY agent_type ORDER BY custo DESC;
```

> **Não filtre subagente por `user_id`+`started_at` sem ter o fix de fuso aplicado** (era a armadilha do bug 2026-06-19): use `session_id` e `recorded_at`.

## Gotchas conhecidos

- **Double-count de custo (corrigido 2026-06-19, commit `0e9403082`):** `total_cost_usd` do SDK é acumulado; era somado por-turno → inflava ~Nx. Fix + backfill aplicados. Detalhe no gotcha de custo em `app/agente/CLAUDE.md` (§Gotchas).
- **`started_at` de subagente +3h (corrigido 2026-06-19):** `_parse_iso_timestamp` gravava UTC-naive em vez de Brasil-naive; 206/206 linhas com `started_at > recorded_at`. Fix no parser + backfill `scripts/migrations/2026_06_19_fix_invocation_metrics_started_at_tz.py`. `duration_ms` NÃO foi afetado (offset se cancela no delta).
- **Telemetria de subagente depende do `transcript_path` do hook `SubagentStop`** (`sdk/hooks.py:789`): SDK 0.1.60+ não emite `type:result` no JSONL do subagente → o "bridge" (`subagent_reader._compute_subagent_metadata_from_jsonl`) recompõe custo/tokens. Se o `transcript_path` vier vazio, a linha grava sem custo (raro: 3/206).
- **`claude_session_store` inclui os subagentes (`isSidechain=true`, com `agentId`), não só o principal.** Ao analisar transcript/tool_calls de uma sessão, SEPARE por `entry->>'isSidechain'` / `agentId` — senão você atribui ao principal o trabalho dos subagentes (erro cometido nesta análise). Os mesmos arquivos-base (`CLAUDE.md` do módulo, models, services) aparecem lidos por **subagentes DISTINTOS** (ex.: 1 arquivo por 4 agentes): é esperado em subagente **one-shot** — cada invocação se situa do zero, não é redundância. Mitigar = reuso de subagente (sessão resumível), não cache de Read.

## Fontes

- Persistência de custo principal: `app/agente/routes/chat.py` (`_save_messages_to_db`, `_persist_session_cost`); modelos `app/agente/models.py` (`AgentSessionCost`, `AgentSession`).
- Pricing / delta: `app/agente/sdk/pricing.py` (`turn_cost_from_cumulative`).
- Telemetria de subagente: `app/agente/sdk/hooks.py:789` (`_subagent_stop_hook`, bloco A1 ~1187) + `app/agente/sdk/subagent_reader.py` (`_parse_iso_timestamp`, `_compute_subagent_metadata_from_jsonl`); modelo `AgentInvocationMetric`.
- Dashboards: `app/agente/services/metrics_dashboard_service.py`, `app/agente/routes/admin_metrics.py`, `app/agente/routes/insights.py`.
- Tabelas verificadas em PROD (Render `dpg-d13m38vfte5s738t6p50-a`) em 2026-06-19.

> Guia dev do módulo: [`app/agente/CLAUDE.md`](../../app/agente/CLAUDE.md). Convenção de fuso: [`REGRAS_TIMEZONE.md`](REGRAS_TIMEZONE.md).

<!-- doc:meta
tipo: scratch
camada: L3
sot_de: prompt de continuacao (sessao limpa) — captura universal de error_signature (loop corretivo)
hub: docs/blueprint-agente/INDEX.md
superseded_by: —
atualizado: 2026-06-04
-->

# PROMPT — Próxima sessão: CAPTURA UNIVERSAL de `error_signature`

> **Papel:** prompt rigoroso para iniciar uma sessão LIMPA e atacar o GARGALO REAL do loop
> corretivo pessoal: a captura de `error_signature` só funciona por backfill manual, não
> organicamente. Cole como mensagem inicial (ou: "leia este arquivo e execute").
> **Regra inviolável:** VERIFICAR o estado real (PROD via MCP Render `dpg-d13m38vfte5s738t6p50-a`)
> ANTES de codar. NÃO assumir. Fonte de dados = Render, nunca local (local = teste).

## A dor (do Rafael, palavra dele)

"Expliquei pro agente e fez certo; na sessão seguinte errou tudo de novo." E, meta-dor:
"patino, over-engineering, não vejo evolução." O objetivo NÃO é zerar reincidência (o
mecanismo é probabilístico) — é **reduzir + iluminar**, com o Rafael intervindo nos residuais.

## Estado atual (o que JÁ está em PROD — não refazer)

Sessão 2026-06-04 consertou o elo **MEDIÇÃO** (o instrumento estava cego). Em PROD,
main `70da54827`, deploy `dep-d8h0onu7r5hc73d0tu1g`, flag existente `AGENT_OUTCOME_TRACKING` ON:

1. `pattern_analyzer._track_signature_recurrence` — `harmful_count++` na regra dura viva de
   MESMA `error_signature` (índice `ix_agent_memories_user_errsig`), desacoplado do
   dedup-de-conteúdo. Guard anti-dupla `not signature_tracked`.
2. `insights_service.get_rule_adhesion_panel['contencao']` — leitura RETROATIVA por
   `created_at`+signature (contidas vs reincidindo) + card no dashboard `insights.html`.
3. `insights_service._enrich_calibration_cases` — tela do judge mostra usuário + pergunta +
   resposta completas (linha expansível `toggleJudgeDetail`).

28 pytest verdes. **Esse é o MEDIDOR — use-o para validar a captura (abaixo).**

## A descoberta que define esta sessão (NÃO repetir o erro de assumir)

- O Marcus (user 18) só tem `error_signature` por **BACKFILL MANUAL one-shot**:
  `scripts/backfill_loop_corretivo_marcus.py` — as signatures estão **HARDCODED** por cluster
  (`CLUSTERS_CORE`, linha ~35). Ele fundiu as 36 correções dele à mão.
- A captura **orgânica** de signature está **QUEBRADA p/ todos**: user 1 (Rafael) 36 correções
  → 2 sig; demais usuários → 0 sig. O comentário do backfill "daqui pra frente é automático"
  é ASSUNÇÃO que os dados de PROD DESMENTEM.
- **ADESÃO NÃO é o gargalo — NÃO ATACAR.** O AgingBench (Fase 0, ver
  `PROMPT_PROXIMA_SESSAO_LOOP_CORRETIVO.md`) provou que quando a regra chega no topo o agente
  OBEDECE (Acc P1=0% → P3=89%). O `effective_count=0` é artefato do eco textual, não
  não-obediência. O gargalo é CAPTURA → RETRIEVAL.

## A frente: CAPTURA UNIVERSAL de `error_signature`

### Fase 0 — Investigar (OBRIGATÓRIA antes de codar; é o erro que já cometemos)

Descobrir **por que o fluxo orgânico não gera signature**. Três hipóteses, cada uma com como verificar:

| # | Hipótese | Como verificar |
|---|---|---|
| H1 | O extrator Sonnet (`extrair_insights_pessoais_sessao`) **omite** o campo `error_signature` apesar do prompt pedir (`pattern_analyzer.py:1884`). | Logs de PROD do extrator (Render) + rodar o extrator sobre sessões reais e ver o JSON; checar se o prompt força melhor o campo. |
| H2 | As correções dos outros usuários vêm de `save_memory` **direto** (caminho A, sem signature), não da extração pós-sessão. | Em PROD, cross-ref `/memories/corrections/%` sem signature × quem criou (`created_by`, `agente`) + logs `[PERSONAL_EXTRACTION]` vs `save_memory`. |
| H3 | O extrator pessoal **raramente classifica** turnos como `tipo=correcao` (threshold de 3 msgs, custo, ou o Sonnet não detecta a correção). | Contar em PROD correções criadas pós-sessão por usuário/período; ver se bate com volume real de correções. |

Provável: combinação de H1+H2. **Confirmar com dados, não deduzir.**

### Fase 1 — Conserto (forma depende do achado da Fase 0)

Candidatos (escolher pelo diagnóstico, mínimo cirúrgico, TDD):
- **Backfill universal contínuo:** generalizar `backfill_loop_corretivo_marcus.py` (hoje user-18-hardcoded)
  para um job que varre `/memories/corrections/` SEM `error_signature` de QUALQUER usuário e gera a
  assinatura via Sonnet (mesma instrução do extrator) — idempotente, dry-run-first. Poderia virar
  módulo do batch D8.
- **Conserto do orgânico:** se H1, reforçar o prompt/parse para SEMPRE emitir signature em
  `tipo=correcao`; se H2, fazer o caminho `save_memory` de correção também gerar signature.

### Como medir sucesso (usar o MEDIDOR consertado hoje)

- Antes/depois: nº de `/corrections/` COM `error_signature` por usuário (deve subir de ~0 para a
  maioria). Query PROD pronta no histórico desta sessão.
- A médio prazo: `get_rule_adhesion_panel['contencao']` deve passar a ter `promovidas > 6`
  (hoje só 6, quase todas do Marcus) e a taxa de contenção fica observável para TODOS os usuários.

## Onde está tudo (arquivos-chave)

- Captura orgânica: `app/agente/services/pattern_analyzer.py` — `extrair_insights_pessoais_sessao()`
  (prompt do extrator ~1840-1890, campo signature linha 1884) + `_save_personal_insight()` (~1910).
- Backfill manual (modelo a generalizar): `scripts/backfill_loop_corretivo_marcus.py`.
- Migration da coluna: `scripts/migrations/2026_06_02_agent_memories_error_signature.{py,sql}`.
- Medidor (desta sessão): `app/agente/services/insights_service.py`
  (`get_rule_adhesion_panel`, `_enrich_calibration_cases`) + `app/agente/templates/agente/insights.html`.
- Dedup (casa por conteúdo, NÃO signature — entender, não confundir):
  `app/agente/tools/memory_mcp_tool.py:1097` `_check_memory_duplicate`.
- Flags: `app/agente/config/feature_flags.py` (`AGENT_CORRECTION_PROMOTION` ON,
  `AGENT_OUTCOME_TRACKING` ON, `AGENT_DIRECTIVE_PROMOTION` OFF, `AGENT_CORRECTION_DEMOTION` OFF).

## Decisões já tomadas (NÃO reabrir)

1. **NÃO religar o flywheel** (judge/verify/eval-gate A3/directive_promotion A4/PlanState) —
   é o over-engineering parqueado; investir nele antes da captura amplifica ruído.
2. **NÃO atacar adesão** — AgingBench já provou que funciona (89% no topo).
3. **Medição já consertada** — não refazer; usar como instrumento de validação.
4. Padrão de trabalho: worktree isolado a partir de `origin/main`, TDD (pytest determinístico,
   sem eval LLM — Rafael veta evals.json por custo), `.venv` da raiz, `.env` copiado (DATABASE_URL
   = localhost = teste seguro), push só com OK explícito do Rafael (auto-deploy PROD).

## Gotchas

- Dados reais = MCP Render `dpg-d13m38vfte5s738t6p50-a`; local = teste. Testes que escrevem
  AgentMemory rodam contra o DB local (seguro) — NUNCA apontar para PROD.
- `error_signature` é `varchar(64)` — truncar `[:64]`.
- Backfill é WRITE: `--dry-run` default, `--confirmar` efetiva, idempotente. Rodar em PROD só
  no Render Shell APÓS GO do Rafael.
- Worktree: pre-commit UI lint usa `python` (ativar `.venv` antes do commit).

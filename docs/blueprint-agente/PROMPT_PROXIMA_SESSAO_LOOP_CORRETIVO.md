<!-- doc:meta
tipo: how-to
camada: L3
sot_de: prompt de continuacao (sessao limpa) do loop corretivo pessoal — backfill do passivo + Fase 3
hub: docs/blueprint-agente/RECONCILIACAO_MEMORIA.md
superseded_by: —
atualizado: 2026-06-02
-->

# PROMPT — Próxima sessão: Loop Corretivo Pessoal (backfill + Fase 3)

> **Papel:** prompt rigoroso para iniciar uma sessão LIMPA e dar sequência ao loop corretivo
> pessoal sem drift. Cole como mensagem inicial (ou: "leia este arquivo e execute").
> **Regra inviolável:** VERIFICAR o estado real (PROD via Render / worktree / testes) — NÃO assumir.

## Indice
- Contexto e estado
- Onde está tudo
- Tarefa 1 — Backfill do passivo (dry-run + OK)
- Tarefa 2 — Fase 3 (medição + posição + frame)
- Regras e gotchas (anti-drift)
- Decisões já tomadas (NÃO reabrir)

## Contexto e estado

Avaliação do sistema de memória do Agente Web/Teams (02/06/2026). Sintoma-raiz (Marcus, Controller Financeiro): *"expliquei pro agente e fez certo, mas na outra sessão fez tudo errado de novo"* = o **loop de aprendizado não fecha**. Fase 0 (AgingBench P1/P2/P3) **provou**: a falha é de **RETRIEVAL** (a correção não chega ao contexto; quando presente no topo, o agente obedece — Acc P1=0% → P3=89%). Fases 1 e 2 implementadas, testadas (**71 verdes**) e commitadas no worktree, **não pushadas**.

| Fase | Estado | Commit |
|---|---|---|
| Fase 1 (canal duro: `USE_USER_RULES_CHANNEL` ON + cap + order_by correction_count) | ✅ | `73346206b` |
| Fase 2 (write-path UPDATE: reincidência→`correction_count++`; promoção recorrente cc≥2→`mandatory` no batch diário módulo 32) | ✅ | `f810e7598` |
| **Backfill do passivo** do Marcus | ⬜ | esta sessão (Tarefa 1) |
| **Fase 3** (outcome + posição + frame) | ⬜ | esta sessão (Tarefa 2) |

Loop (já fechado para o futuro): reincidir → `correction_count++` → batch diário promove a `mandatory` → canal duro injeta ordenado por reincidência + cap.

## Onde está tudo

- **Worktree:** `/home/rafaelnascimento/projetos/frete_sistema_memoria` (branch `feat/blueprint-eixo-c-memoria`, base `origin/main`). 4 commits (base / docs `d784edbdc` / Fase1 `73346206b` / Fase2 `f810e7598`). **FALTA PUSH (Rafael).**
- **Rastreador:** `docs/blueprint-agente/EXECUCAO.md` seção "EIXOS C + G" (item G-F1 com Fases 0/1/2).
- **Plano:** `docs/superpowers/plans/2026-06-02-loop-corretivo-pessoal.md` (3 fases, DoD).
- **Eixos:** `eixos/C-vigilancia.md` + `eixos/G-memoria-pessoal.md`. **Reconciliação:** `RECONCILIACAO_MEMORIA.md`.
- **Relatórios de diagnóstico (efêmeros):** `/tmp/avaliacao-memoria-agente/01..07`.
- **Memória persistente Claude Code:** `memory/avaliacao_memoria_agente_2026_06.md` (estado completo).
- **Dados PROD:** Render `postgresId=dpg-d13m38vfte5s738t6p50-a`, workspace `tea-d01amimuk2gs73dhlup0`. IDs: Marcus web=**18**, teams=**56**; Martha=**82**; empresa=**0**.

## Tarefa 1 — Backfill do passivo do Marcus (dry-run + OK)

**Por que existe:** as ~9 correções antigas do Marcus sobre o mesmo erro têm `correction_count=0` (o sistema antigo nunca incrementava) → não são promovidas pelo batch (0 < threshold 2). É um passivo histórico one-shot; daqui pra frente é automático.

**Fazer:**
1. Consultar PROD (Render) as correções do Marcus (user 18) em `/memories/corrections/`; agrupar por tema (ex: ~9 "troca de escopo/cluster"; "JUROS (outros)"; "Tenda↔Sicoob"; formato baseline/datas).
2. Por grupo redundante: escolher/criar a **canônica**, setar `correction_count = nº de cópias` (ou ≥ threshold) e deixar o batch promover (ou setar `priority='mandatory'` direto); arquivar as demais (consolidação — preservar a prescrição).
3. **DRY-RUN primeiro** (listar o que seria feito) → **confirmar com o Rafael** → executar (write PROD). Idempotente.

## Tarefa 2 — Fase 3 (medição por outcome + posição + frame imperativo)

Detalhe no plano (Fase 3). Resumo + ênfases desta avaliação:
1. **Migration dupla** (`scripts/migrations/NOME.{py,sql}`, idempotente): coluna `error_signature` (hash de intenção) em `agent_memories`.
2. **`pattern_analyzer`**: emitir `error_signature` + reescrever a prescrição em **SEMPRE/NUNCA + WHEN/DO** na promoção (frame imperativo) — Compiled Memory.
3. **`routes/_helpers._track_memory_effectiveness`**: medir por **OUTCOME** (regra injetada + reincidência casada → `harmful++`; injetada + sem reincidência por K sessões → `helpful++`). DESACOPLAR do eco textual (manter eco só p/ dashboard).
4. **`memory_injection.py`**: **TUNING DE POSIÇÃO** — mover `<user_rules>` para o **TOPO** do contexto injetado (hoje vai em `tier0`, anexado APÓS as estáveis, ~linha 1214; a Fase 0 mostrou que o topo rende mais). + somar **recorrência** ao composite score (~linha 945).
5. **`sdk/hooks.py`** (base R9 PreToolUse): HARD enforcement só p/ invariantes formalizáveis promovidas.
6. **`directive_promotion_service`**: `demote_stale_rules` (harmful pós-promoção → reescrita; K limpas → demote, libera o cap).
7. **`insights_service`**: painel "adesão de regras" (reincidência por assinatura antes/depois).
8. Correções **tipo-A** (que competem com o pedido literal do usuário — caso A da Fase 0): precisam do frame imperativo no topo (lá P3 foi de 0%→67%).

**Métrica primária (DoD):** reincidência por `error_signature` ANTES vs DEPOIS da promoção estagna. Alvo: erro recorrente do Marcus de ~9 → ≤2.

## Regras e gotchas (anti-drift)

- **Flags default ON** (decisão Rafael 02/06: evitar feature virar zumbi "construída-e-desligada"). Mas ON deve ser **seguro por construção** (aditivo/gated/cap), e o estado das flags deve ficar registrado no `EXECUCAO.md`.
- **Pytest no worktree** (sem `.venv` próprio): `source <raiz>/.venv/bin/activate; set -a; source <raiz>/.env; set +a; cd <worktree>; python -m pytest <alvo> -q`. Conftest usa o PostgreSQL local via `DATABASE_URL` do ambiente.
- **Gotchas de teste:** `priority` válidos = `contextual`/`advisory`/`mandatory` (NÃO `structural` — isso é `category`). `create_file` exige **commit entre memórias no mesmo diretório** (senão IntegrityError no diretório-pai via autoflush). Filtrar por `user_id` em funções globais nos testes (evita poluir dados locais).
- **Commit no worktree:** `git commit --no-verify` (defere C1 legado de `EXECUCAO.md`/`app/agente/CLAUDE.md` — header `doc:meta` ausente, backlog **Onda 4 PAD-A ~645 docs**; NÃO retrofitar pontual). Docs novos: header `doc:meta` + Papel/Contexto/Indice (passa `doc_audit --enforce-touched`).
- **Push é do Rafael.** NÃO pushar.
- **Subagente Explore sempre `model: sonnet`.** Dados PROD via Render MCP (selecionar workspace `tea-d01amimuk2gs73dhlup0` sem perguntar). Dados locais = teste.

## Decisões já tomadas (NÃO reabrir)

- Falha = **RETRIEVAL** (Fase 0 provou) → o canal duro garantido é a cura principal; frame/medição (Fase 3) são complemento.
- Promoção é **RECORRENTE** (3ª fonte do batch diário módulo 32 `directive_promotion`), não script one-shot.
- **NÃO duplicar o blueprint:** F5=eixo D (KG), F8=eixo E (qualidade), F3=A4 (já LIVE em PROD). Memória pessoal/recuperação = eixo **G**; vigilância proativa = eixo **C** (novos).
- `user_id` fragmentado Web/Teams (P1) = problema **separado**, não é o loop.
- Constantes: `AGENT_CORRECTION_PROMOTION_THRESHOLD=2`, `MANDATORY_RULES_MAX_COUNT=12`.
- Sequência (regra de ouro): **medir antes de atuar**; backfill antes de validar adesão.

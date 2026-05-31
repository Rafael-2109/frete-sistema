# Onda 3 — Fechar o Flywheel + Ontologia Consultável Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps usam checkbox.
> **Branch**: `feat/agente-evolucao` (worktree). NÃO push. Tudo flag-OFF.
> **Spec**: `docs/blueprint-agente/EXECUCAO.md` Onda 3 + `eixos/A-flywheel.md`/`D-ontologia.md`.

**Goal:** Bootstrap da ontologia canônica (D2) + read path consultável (D4) + fatos bi-temporais (D3) + eval gate (A3) + promoção de diretriz (A4) — fechar o ciclo de aprendizado. Tudo flag-OFF / shadow.

**Tech Stack:** Flask, SQLAlchemy, Voyage embeddings (batching), RQ, feature flags, MCP tool.

---

## AUDITORIA D2 (2026-05-31 — recon `/tmp/subagent-findings/d2-recon.md`)
- **entity_indexer ERRADO**: `app/embeddings/indexers/entity_indexer.py` popula `financial_entity_embeddings` (contas_a_pagar/receber, resolução de favorecidos) — NÃO o KG. Não reusar para o grafo.
- **Tabelas-mestre + chaves canônicas**:
  | Entidade | Tabela | entity_key | entity_name | Indexer existente |
  |----------|--------|-----------|-------------|-------------------|
  | `produto` | `cadastro_palletizacao` (ativo+vendido) | `cod_produto` | `nome_produto` | `product_indexer.py` |
  | `transportadora` | `transportadoras` | `cnpj` (ou id) | `razao_social` | `carrier_indexer.py` |
  | `cliente` | `carteira_principal`/`contas_a_receber` | `cnpj_cpf` raiz 8d | `raz_social` | — (sem tabela dedicada) |
- `_VALID_ENTITY_TYPES` (`knowledge_graph_service.py:60-64`) já aceita `cliente`/`produto`/`transportadora`/`fornecedor`.
- `_upsert_entity(conn, user_id=0, entity_type, entity_name, entity_key)` idempotente (ON CONFLICT `uq_user_entity`); `entity_name` normalizado (upper, sem acento). Read user_id=0 já existe (D0.5 `query_graph_memories:797`).
- Voyage: <10K entidades, <$0.01. Batching 128 + sleep 0.5s já nos indexers (reusar). **Confirmar `COUNT(DISTINCT cnpj_raiz)` em PROD antes de rodar o bootstrap** (deploy-time; local = dados teste).

## GAP CRÍTICO (não no blueprint — RESOLVIDO por design)
Nós canônicos bootstrapados SEM link de memória NÃO são achados pelo HOP-1 de `query_graph_memories` (busca via `agent_memory_entity_links`). **Resolução**: o consumidor da ontologia é a tool **`query_ontology` (D4)** — read path DIRETO por entity_name/type/key — não o HOP-1. Logo D2 bootstrapa o substrato; D4 provê o read path. D2 fica inerte (flag `AGENT_ONTOLOGY` OFF) até D4 + deploy. NÃO forçar link a "memória âncora" (poluiria retrieval de memória).

---

## Task 1 — D2: bootstrap de ontologia das tabelas-mestre (flag AGENT_ONTOLOGY, CLI/job)

**Files:**
- Create: `app/agente/services/ontology_bootstrap.py` (lê tabelas-mestre → `_upsert_entity` user_id=0, batched, idempotente)
- Create: `scripts/agente/bootstrap_ontologia.py` (CLI: `--dry-run` / `--entity-type` / `--limit`) — NÃO auto-run
- Test: `tests/agente/services/test_ontology_bootstrap.py`

- [ ] **Step 1: Ler** `product_indexer.py`/`carrier_indexer.py` (padrão de leitura de tabela-mestre + batching Voyage), `_upsert_entity` + `_VALID_ENTITY_TYPES` (knowledge_graph_service.py), e os schemas `cadastro_palletizacao.json`/`transportadoras.json`/`carteira_principal.json`.

- [ ] **Step 2: Teste que falha** — `bootstrap_entities(entity_type, rows)` cria nós canônicos via `_upsert_entity(user_id=0)`, idempotente:
```python
def test_bootstrap_produto_cria_no_canonico(app_ctx, monkeypatch):
    from app.agente.services.ontology_bootstrap import bootstrap_entities
    # mock _upsert_entity para capturar chamadas (sem DB real do KG)
    chamadas = []
    monkeypatch.setattr('app.agente.services.ontology_bootstrap._upsert_entity',
                        lambda conn, user_id, et, en, ek: chamadas.append((user_id, et, en, ek)) or 1)
    rows = [{'cod_produto': '4729098', 'nome_produto': 'AZEITE X'}]
    n = bootstrap_entities('produto', rows, conn=object())
    assert n == 1
    assert chamadas[0][0] == 0          # user_id=0 (empresa)
    assert chamadas[0][1] == 'produto'  # entity_type
    assert chamadas[0][3] == '4729098'  # entity_key = cod_produto
```

- [ ] **Step 3: Implementar `ontology_bootstrap.py`**:
  - `bootstrap_entities(entity_type, rows, conn) -> int`: para cada row, mapeia (entity_key, entity_name) conforme a tabela do `entity_type` (mapeamento explícito por tipo), chama `_upsert_entity(conn, 0, entity_type, entity_name, entity_key)`. Pula rows sem nome/chave. Retorna nº criados/atualizados.
  - `bootstrap_all(conn, limit=None) -> dict`: lê as 3 tabelas-mestre (produto/transportadora/cliente; cliente = DISTINCT por cnpj raiz 8d) e chama `bootstrap_entities` por tipo. SOMENTE sob flag (o CLI checa `USE_AGENT_ONTOLOGY` ou exige `--force`).
  - Mapeamento por tipo (entity_key/entity_name) num dict `_ENTITY_SOURCE_MAP`.
- [ ] **Step 4: CLI `scripts/agente/bootstrap_ontologia.py`** com `--dry-run` (conta, não escreve), `--entity-type`, `--limit`. `sys.path.insert` + `create_app()`. Documenta: rodar no deploy após confirmar COUNT em PROD; idempotente.
- [ ] **Step 5: Testes** (mock `_upsert_entity` + mock queries de tabela-mestre) + `pytest tests/agente/ -q` baseline.
- [ ] **Step 6: Commit** — `feat(agente-onda3): D2 bootstrap ontologia tabelas-mestre (flag AGENT_ONTOLOGY, CLI dry-run)`

---

## Task 2 — D4: tool MCP `query_ontology` (read path da ontologia)

**Files:**
- Create/Modify: tool MCP `query_ontology` (em `app/agente/tools/` — seguir padrão das tools MCP existentes)
- Test: `tests/agente/tools/test_query_ontology.py`

- [ ] **Step 1: Ler** uma tool MCP existente (ex.: `memory_mcp_tool.py`) p/ o padrão de registro + `_upsert_entity`/leitura de `agent_memory_entities` por (user_id IN [uid,0], entity_type, entity_name like).
- [ ] **Step 2: Teste que falha** — `query_ontology(entity_type=?, name_like=?)` retorna nós canônicos (user_id=0) por busca DIRETA (não HOP-1).
- [ ] **Step 3: Implementar** `query_ontology` (read-only): busca direta em `agent_memory_entities` por tipo/nome/chave, une user_id do chamador + 0. Registrar a tool sob flag `AGENT_ONTOLOGY` (só aparece p/ o agente quando ON).
- [ ] **Step 4: Testes** + baseline.
- [ ] **Step 5: Commit** — `feat(agente-onda3): D4 tool query_ontology (read path ontologia, flag OFF)`

> Com D2+D4: a ontologia bootstrapada vira consultável. Isso DESTRAVA **B-TRIAGE** (decompõe meta sobre entidades) e **B2-domain** (valida contra ontologia) — voltar ao plano da Onda 2 e implementá-los.

---

## Task 3 — D3: fatos bi-temporais + episode subgraph (proveniência)
- [ ] Reusa `session_turn_indexer.py`. Adiciona `valid_from`/`valid_to` (tempo do fato) + `observed_at` aos nós/relações; episode subgraph liga fatos à sessão/turno de origem. Flag `AGENT_ONTOLOGY`. Plano detalhado quando a Task chegar (recon `session_turn_indexer` primeiro).

## Task 4 — A3: eval runner + gate no D8 (golden datasets)
- [ ] Processo EXTERNO ao agente: runner que roda `evals/` (golden datasets) contra a versão candidata, report-only → enforce. Integra no cron D8. Flag `AGENT_EVAL_GATE`. Reusa `.claude/evals/`. Plano detalhado quando chegar (recon `evals/` + D8 cron).

## Task 5 — A4: promoção automática de diretriz
- [ ] Liga `USE_OPERATIONAL_DIRECTIVES` com segurança: candidata→shadow/A-B→regression-gate(A3)→promove→monitora-drift→auto-despromove. Reusa `_build_operational_directives` (`memory_injection.py:420`). Flags `USE_OPERATIONAL_DIRECTIVES`+`AGENT_DIRECTIVE_PROMOTION`. **Reward-hacking guard**: componente ambiental (audit Odoo R9) DOMINA; held-out + spot-check. Plano detalhado quando chegar.

---

## Self-Review
- D2 gap (read path) resolvido por D4; não forçar âncora de memória. ✓
- Custo Voyage = deploy-time (flag OFF + CLI dry-run + confirmar COUNT PROD). ✓
- D2/D4 destravam B-TRIAGE/B2-domain (voltar à Onda 2). ✓
- A3/A4 mudam comportamento ativo → só shadow aqui; gate real exige deploy. ✓

## GATE-3
Flywheel fechado em shadow (promoção SUGERE, não aplica) ≥2 semanas com held-out anti-gaming OK; ontologia consultável validada. Requer deploy + flags shadow.

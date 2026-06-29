<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-28
-->
# Convergência Agente Lojas ↔ Agente Web — Implementation Plan

> **Papel:** plano de implementação bite-sized (TDD, commits frequentes) da
> convergência do `app/agente_lojas/` (fork `AgentLojasClient`) para reusar a
> infra do `app/agente/` via módulos compartilhados + gate por identidade de
> agente (`AGENTE_ID`), fail-closed. Resolve o drift O(N) do fork e prepara o
> sistema para N perfis de agente. Derivado da avaliação A vs B de 2026-06-28
> (veredito: **híbrido sequenciado**).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Indice

- [Contexto](#contexto)
- [Decisões Travadas](#decisões-travadas)
- [Global Constraints](#global-constraints)
- [File Structure](#file-structure)
- [FASE 0 — env dict (URGENTE, risco de produção)](#fase-0--env-dict-urgente-risco-de-produção)
- [FASE 1 — Fechar gaps genéricos via extração compartilhada](#fase-1--fechar-gaps-genéricos-via-extração-compartilhada)
- [FASE 2 (M3) — Isolamento de memória por agente, fail-closed](#fase-2-m3--isolamento-de-memória-por-agente-fail-closed)
- [FASE 3 — Parametrização do AgentClient por perfil (gated)](#fase-3--parametrização-do-agentclient-por-perfil-gated)
- [Apêndice A — Os 28 vetores de M3](#apêndice-a--os-28-vetores-de-m3)
- [Self-Review](#self-review)

---

## Contexto

**Goal:** Eliminar o drift estrutural entre `app/agente_lojas/` e `app/agente/`
convergindo a infra genérica para módulos compartilhados, com isolamento de
dados garantido por gate fail-closed na identidade do agente.

**Arquitetura:** O `AgentLojasClient` é um fork (779 LOC em 3 arquivos SDK) que
**não herda** o `AgentClient` web (~5.534 LOC equivalentes) e reusa o web só por
4 imports pontuais (`session_store_adapter`, `pricing`, `pending_questions`,
`subagent_reader`). O fork acumulou **7 gaps** vs o web — todos de infra genérica
sem razão de domínio (≥4 são fixes que pousaram no web e nunca foram replicados).
O destino correto é um `AgentClient` parametrizável por perfil, mas o caminho de
menor risco **não** é copiar (A, drift O(N)) nem big-bang reuse do client (B,
fail-open antes do isolamento de memória). É um híbrido sequenciado que **estende
o padrão de import compartilhado que já funciona**, com o isolamento de memória
(M3) como pré-requisito **duro** de qualquer reuso de contexto.

**Tech Stack:** Python 3.12 · Flask 3.1 · SQLAlchemy 2.0 · Claude Agent SDK
0.2.x · pytest · PostgreSQL local p/ testes (JSONB — **não** SQLite) · pgvector
(embeddings) · migrations par `.sql`+`.py` em `scripts/migrations/`.

**Por que híbrido (resumo da avaliação A vs B):**

| | Opção A (duplicar) | Opção B literal (gate por flag do Usuario) | Híbrido (este plano) |
|---|---|---|---|
| Drift | O(N), **já materializado** (7 gaps) | elimina na fonte | corrige já (F0/F1) + elimina (F3) |
| Isolamento | air gap real (fork não importa memória) | **fail-open** se antes de M3 | fail-closed por `AGENTE_ID` (F2) |
| Escala p/ N perfis | não | sim | sim |
| Blast radius | mínimo | alto (singleton de 3 consumidores) | faseado, contido por fase |
| Chave do gate | — | flag autoriza, **não roteia** (admin tem ambas) | identidade de agente (já persistida) |

---

## Decisões Travadas

> Confirmadas com o dono do sistema em 2026-06-28. Toda task implicitamente as respeita.

- **D1 — Corpus de memória `user_id=0` é POR-AGENTE, fail-closed.** Cada agente só
  enxerga `agente='<seu>'`. O que for compartilhado entra por **allow-list
  explícita**, nunca por default. Memórias-empresa hoje (todas `'web'` por DDL)
  ficam **invisíveis** ao lojas — comportamento correto.
- **D2 — A chave do gate é a IDENTIDADE DO AGENTE (`AGENTE_ID`)**, já persistida em
  `agent_sessions.agente` / `agent_memories.agente`. As flags do `Usuario`
  (`pode_acessar_lojas`, `_tem_acesso_nacom`) permanecem na camada de
  decorator/URL fazendo **só autorização de endpoint** — nunca definem o que é
  injetado. Admin (acessa ambos) é resolvido por endpoint, não por inferência de flag.
- **D3 — fail-closed sem fallback implícito.** O `DEFAULT 'web'` da coluna é só
  para retrocompat de dados legados; o código de retrieval **exige** `agente_id`
  explícito e nunca cai num default silencioso quando o parâmetro falta.
- **D4 — Extrair, não copiar.** Fechar gaps genéricos (F1) é via módulo
  compartilhado consumido por ambos, estendendo o padrão dos 4 imports já provados
  — copy-paste reintroduz o drift que estamos matando.

---

## Global Constraints

- **Ambiente:** `source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate` antes de qualquer `pytest`/script Python.
- **TDD obrigatório:** teste RED → implementação mínima → GREEN → commit. Um passo = uma ação.
- **Contrato de isolamento HORA** (`app/hora/CLAUDE.md`): o fork **NUNCA** importa `app/motochefe/`, `app/carvia/` direto, nem `app/agente/sdk/memory_injection.py` ou `app/agente/sdk/hooks.py` (têm domínio Nacom). Reuso é por **import de submódulo** (`from app.agente.sdk.<submodulo> import <simbolo>`), **NUNCA** `from app.agente.sdk import <simbolo>` (o `__init__.py:12-26` puxa `AgentClient` inteiro + pool → acoplamento pesado e thread global).
- **Migrations:** todo schema change = **par** `scripts/migrations/<nome>.sql` (DDL) + `<nome>.py` (Flask-Migrate/execução) — regra CLAUDE.md.
- **Timezone:** datas/timestamps seguem `.claude/references/REGRAS_TIMEZONE.md` (Brasil naive).
- **Teste = PostgreSQL local** (fixtures `app`/`db` de `tests/conftest.py:37-98`); SQLite quebra (JSONB).
- **Fail-closed por padrão:** na dúvida entre vazar e ocultar, ocultar. Toda query de retrieval de memória/sessão filtra por `agente_id` **explícito**.
- **Comando de teste do módulo:** `source .venv/bin/activate && cd /home/rafaelnascimento/projetos/frete_sistema && pytest tests/agente_lojas/ -v`

---

## File Structure

**Criar:**
- `app/agente/sdk/sdk_runtime.py` — infra de subprocesso genérica: `build_subprocess_env() -> dict` (env dict). Função pura, zero domínio.
- `app/agente/sdk/sdk_compat.py` — `check_skills_option()` + `SDK_HAS_SKILLS_OPTION` (hoje duplicados nos dois módulos). Função pura.
- `scripts/migrations/2026_06_28_add_agente_embeddings.{sql,py}` — coluna `agente` em `agent_memory_embeddings` + index + backfill `'web'`.
- `scripts/migrations/2026_06_28_add_agente_kg_entities.{sql,py}` — coluna `agente` em `agent_memory_entities` + index + backfill `'web'`.
- `tests/agente_lojas/conftest.py` — fixtures `app`/`db` (reusa raiz) + `mem_factory` (cria `AgentMemory` com `agente=`).
- `tests/agente_lojas/test_build_options_env.py` — F0.
- `tests/agente_lojas/test_sdk_error_handling.py`, `test_nacom_quiet_boot.py` — F1.
- `tests/agente/sdk/test_memory_isolation_por_agente.py` — **F2, o teste-contrato** (zero vazamento).

**Modificar (resumo — file:line por task abaixo):**
- `app/agente_lojas/sdk/client.py` (F0 env :221; F1 erro :457-482, imports :33; session_id turno1 :261-282; agents= :221-252)
- `app/agente_lojas/sdk/hooks.py:58-70` (F1 NACOM_QUIET_BOOT)
- `app/agente_lojas/config/settings.py:29` (F1 `empresa_briefing_path` morto)
- `app/agente/sdk/memory_injection.py` (F2: 13 vetores + `_DOMAIN_KEYWORDS`)
- `app/agente/sdk/memory_injection_rules.py:41-54` (F2)
- `app/agente/services/knowledge_graph_service.py:876-964` (F2)
- `app/embeddings/service.py:838-908` (F2)
- `app/agente/services/intersession_briefing.py:129-309` (F2)
- `app/agente/models.py:654-679` (F2 `get_by_path`/`get_directory`)
- `app/agente/sdk/hooks.py:1558-1578`, `app/agente/config/agent_loader.py:321-500`, `app/agente/sdk/context_enrichment.py` (F2 vetores não-memória)
- `app/agente/config/settings.py:162-170`, `app/agente/sdk/client.py:365,523,757,1718,3008` (F3, gated)

---

## FASE 0 — env dict (URGENTE, risco de produção)

**Blast radius:** só o fork. Independe de A/B. **Corrige risco de crash no Render**
(`HOME=/opt/render` read-only → CLI falha ao salvar `.claude.json`) e timeout de
hook/MCP em **60s vs 240s** (mata skill pesada / `orientador-loja`).

### Task 0.1: Adicionar `env` dict ao `build_options` do fork

**Files:**
- Modify: `app/agente_lojas/sdk/client.py:221` (dict `options_kwargs` em `build_options()`)
- Test: `tests/agente_lojas/test_build_options_env.py` (criar)
- Modelo de teste: `tests/agente_lojas/test_resume_build_options.py:1-47` (mesma API de chamada de `build_options`)

**Interfaces:**
- Produz: opções do SDK do fork passam a conter `env={'CLAUDE_CODE_STREAM_CLOSE_TIMEOUT': '240000', 'HOME': '/tmp'}`. Espelha web `app/agente/sdk/client.py:1629-1634`.

- [ ] **Step 1: Escrever o teste que falha** — espelhar o setup de chamada de `build_options` de `test_resume_build_options.py` e asseverar o `env`:

```python
# tests/agente_lojas/test_build_options_env.py
def test_build_options_seta_env_para_render_e_timeout():
    from app.agente_lojas.sdk.client import get_lojas_client
    client = get_lojas_client()
    options = client.build_options(  # mesma assinatura usada em test_resume_build_options.py
        sdk_session_id=None, our_session_id="11111111-1111-1111-1111-111111111111",
        user_id=1, user_name="Teste",
    )
    assert options.env.get("HOME") == "/tmp"
    assert options.env.get("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT") == "240000"
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `source .venv/bin/activate && pytest tests/agente_lojas/test_build_options_env.py -v`
Expected: FAIL (`env` é None ou não tem as chaves).

- [ ] **Step 3: Implementar** — em `app/agente_lojas/sdk/client.py`, no dict `options_kwargs` de `build_options()` (junto aos demais campos, ~:235-252):

```python
"env": {
    "CLAUDE_CODE_STREAM_CLOSE_TIMEOUT": "240000",  # 240s p/ hooks/MCP (default SDK = 60s)
    "HOME": "/tmp",                                  # Render: /opt/render é read-only
},
```

- [ ] **Step 4: Rodar e verificar que passa** — `pytest tests/agente_lojas/test_build_options_env.py -v` → PASS. Rodar a suíte: `pytest tests/agente_lojas/ -v` (sem regressão).

- [ ] **Step 5: Commit**

```bash
git add app/agente_lojas/sdk/client.py tests/agente_lojas/test_build_options_env.py
git commit -m "fix(agente-lojas): env dict (HOME=/tmp + STREAM_CLOSE_TIMEOUT) — risco de crash no Render"
```

---

## FASE 1 — Fechar gaps genéricos via extração compartilhada

**Pré-req:** Fase 0. **Blast radius:** fork + dois módulos novos puros (sem
domínio). **Princípio (D4):** extrair para módulo consumido por ambos, não copiar.
Cobre os gaps G2–G6 do fork (G7 já está alinhado — verificado).

### Task 1.1: Extrair `sdk_runtime.build_subprocess_env()` e consumir nos dois clients

**Files:**
- Create: `app/agente/sdk/sdk_runtime.py`
- Modify: `app/agente/sdk/client.py:1629-1634` (passar a chamar o helper), `app/agente_lojas/sdk/client.py:221` (idem — substitui o literal da F0)
- Test: `tests/agente/sdk/test_sdk_runtime.py` (criar)

**Interfaces:**
- Produz: `build_subprocess_env() -> dict[str, str]` retornando `{'CLAUDE_CODE_STREAM_CLOSE_TIMEOUT': '240000', 'HOME': '/tmp'}`. Consumida por web e fork.

- [ ] **Step 1: Teste RED** — `test_build_subprocess_env_retorna_chaves_canonicas` asserta as 2 chaves.
- [ ] **Step 2: Rodar, falha** (módulo não existe).
- [ ] **Step 3: Implementar** `app/agente/sdk/sdk_runtime.py`:

```python
"""Infra de subprocesso do SDK — pura, sem domínio. Consumida por web e agente_lojas."""

def build_subprocess_env() -> dict[str, str]:
    return {
        "CLAUDE_CODE_STREAM_CLOSE_TIMEOUT": "240000",  # 240s (default SDK = 60s)
        "HOME": "/tmp",                                  # Render: /opt/render read-only
    }
```

- [ ] **Step 4:** Trocar o literal da F0 no fork por `from app.agente.sdk.sdk_runtime import build_subprocess_env` (import de submódulo — Global Constraints) e `"env": build_subprocess_env()`. Trocar o inline web (`client.py:1629-1634`) pela mesma chamada. Rodar `pytest tests/agente/ tests/agente_lojas/ -v` → PASS.
- [ ] **Step 5: Commit** `refactor(agente-sdk): extrai build_subprocess_env compartilhado (web + lojas)`

### Task 1.2: Extrair `sdk_compat.check_skills_option()` (dedup web/fork)

**Files:**
- Create: `app/agente/sdk/sdk_compat.py` (move de `app/agente/sdk/client.py:70-78`)
- Modify: `app/agente/sdk/client.py:70-78`, `app/agente_lojas/sdk/client.py:98-117` (passam a importar)
- Test: `tests/agente/sdk/test_sdk_compat.py`

- [ ] **Step 1: Teste RED** — `test_check_skills_option_booleano` asserta que retorna `bool`.
- [ ] **Step 2:** Rodar, falha.
- [ ] **Step 3:** Mover `_check_skills_option()` + `_SDK_HAS_SKILLS_OPTION` para `sdk_compat.py` como `check_skills_option()` / `SDK_HAS_SKILLS_OPTION`.
- [ ] **Step 4:** Ambos os clients importam de `app.agente.sdk.sdk_compat`. Remover as duplicatas. Rodar suítes → PASS.
- [ ] **Step 5: Commit** `refactor(agente-sdk): extrai sdk_compat (mata duplicata web/lojas)`

### Task 1.3: Handlers de erro SDK especializados no fork (mínimo, sem pool)

**Files:**
- Modify: `app/agente_lojas/sdk/client.py:33` (imports SDK) e `:457-482` (try/except de `stream_response`, **antes** do `except Exception` genérico em :476)
- Test: `tests/agente_lojas/test_sdk_error_handling.py`

> **Nota (verificada):** NÃO extrair `handle_sdk_error()` compartilhado agora — o
> web acopla a lógica ao estado do pool (`dead-client eviction`, `state.done_emitted`),
> o fork usa client efêmero. Abstrair seria MCD prematuro. Fica para F3 (quando o
> fork adotar pool).

- [ ] **Step 1: Teste RED** — simular `ProcessError` no stream e asseverar que o fork emite `{'type':'error',...}` seguido de `{'type':'done', 'error_recovery': True}` (mock do SDK via padrão `tests/agente/sdk/conftest.py:190-213`).
- [ ] **Step 2:** Rodar, falha (hoje vira traceback bruto via `except Exception`).
- [ ] **Step 3:** Importar `CLINotFoundError, ProcessError, CLIConnectionError, CLIJSONDecodeError` (linha 33) e inserir 4 `except` especializados antes do genérico: log diagnóstico + drenar `stderr_queue` (parâmetro já existe) + emitir `done` com `error_recovery=True`.
- [ ] **Step 4:** Rodar `pytest tests/agente_lojas/test_sdk_error_handling.py -v` → PASS.
- [ ] **Step 5: Commit** `fix(agente-lojas): handlers de erro SDK (ProcessError/CLINotFound) + done error_recovery`

### Task 1.4: `NACOM_QUIET_BOOT` no PreToolUse do fork

**Files:**
- Modify: `app/agente_lojas/sdk/hooks.py:58-70` (`_keep_stream_open`)
- Test: `tests/agente_lojas/test_nacom_quiet_boot.py`

- [ ] **Step 1: Teste RED** — input `tool_name='Bash', command='python x.py'` → output deve prefixar `export NACOM_QUIET_BOOT=1; ` via `hookSpecificOutput.updatedInput` (SDK 0.1.29+, race-free).
- [ ] **Step 2:** Rodar, falha (hoje só retorna `{"continue_": True}`).
- [ ] **Step 3:** Em `_keep_stream_open`: se `input_data.get('tool_name') == 'Bash'`, prefixar `command`. **NÃO** incluir vars de auditoria Odoo (`AGENT_SESSION_ID` etc. — domínio Nacom, o fork não tem audit hook Odoo).
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5: Commit** `fix(agente-lojas): NACOM_QUIET_BOOT no Bash (stdout limpo p/ parse de skill)`

### Task 1.5: `session_id` nativo no turno 1 + `agents=` explícito + limpar `empresa_briefing_path` morto

**Files:**
- Modify: `app/agente_lojas/sdk/client.py:261-282` (bloco continuidade — setar `session_id` no turno 1), `:221-252` (passar `agents=` filtrado a `orientador-loja`), `app/agente_lojas/config/settings.py:29`
- Test: `tests/agente_lojas/test_resume_build_options.py` (estender)

- [ ] **Step 1: Teste RED** — turno 1 (`sdk_session_id=None`) com `our_session_id` UUID válido deve setar `options.session_id == our_session_id` (espelha web `client.py:1663-1678`). Hoje não seta (comentário "Nao setamos nada aqui") e depende de capturar via `SystemMessage` (frágil em race).
- [ ] **Step 2:** Rodar, falha.
- [ ] **Step 3:** (a) adicionar bloco que seta `options_kwargs['session_id'] = our_session_id` no turno 1; (b) setar `agents=` via `load_agent_definitions` filtrado a `SUBAGENTS_PERMITIDOS` (`{'orientador-loja'}`, `agente_lojas/config/skills_whitelist.py:34`) — defesa em profundidade vs auto-discovery implícita; (c) `settings.py:29`: setar `empresa_briefing_path = ''` + comentário "campo herdado, NÃO lido pelo fork — não apontar p/ briefing Nacom (contrato HORA)".
- [ ] **Step 4:** Rodar `pytest tests/agente_lojas/test_resume_build_options.py -v` → PASS.
- [ ] **Step 5: Commit** `fix(agente-lojas): session_id turno1 + agents= explícito (orientador-loja) + limpa briefing morto`

---

## FASE 2 (M3) — Isolamento de memória por agente, fail-closed

> **GATE DURO.** Bloqueia QUALQUER reuso de memória/contexto entre agentes, em A
> ou B. Hoje o fork está seguro por **air gap** (não importa `memory_injection`).
> Esta fase substitui o air gap por um gate de software fail-closed — e portanto
> **só pode ser considerada completa quando o teste-contrato (Task 2.2) provar
> ZERO vazamento em cada superfície**. Escopo medido: **28 vetores** (22 filtros
> `WHERE agente=`, 4 parâmetros de perfil/allow-list, **2 migrações de schema**).
> Ver [Apêndice A](#apêndice-a--os-28-vetores-de-m3).

### Task 2.0: Fechar o escopo (auditoria das lacunas conhecidas)

**Files (auditar, ainda não medidos):**
- `app/agente/tools/memory_mcp_tool.py` (13 operações save/update/list — o agente as chama via `view_memories`/`save_memory`; confirmar quais leem/gravam `AgentMemory` sem `agente`)
- `app/agente/services/intersession_briefing.py` (`_get_intelligence_report` → `AgentIntelligenceReport`: tem coluna `agente`?)
- `app/agente/services/{memory_consolidator,pattern_analyzer,directive_promotion_service,session_summarizer,insights_service,skill_effectiveness_service,approval_inbox_service}.py` (jobs de **escrita**/consolidação — particionam o corpus na origem? se um job 'web' consome sessão 'lojas', contamina)

- [ ] **Step 1:** Para cada arquivo acima, `grep -n "AgentMemory\|AgentSession\|agente"` e classificar: **P0** injeção-em-sessão (vaza em tempo real) / **P1** geração-consolidação (contamina corpus na escrita) / **P2** admin/UI (lista cross-agente). Anexar achados como linhas novas no Apêndice A.
- [ ] **Step 2:** Se a auditoria revelar **>10 vetores novos**, PARAR e re-dimensionar a fase com o dono antes de seguir (a 1ª estimativa de 8-10 já virou 28; o teto real precisa estar fechado antes de comprometer cronograma).
- [ ] **Step 3: Commit** (só doc) `docs(plano): fecha escopo M3 — auditoria memory_mcp_tool + jobs de consolidação`

### Task 2.1: Migrations — coluna `agente` em embeddings e KG

**Files:**
- Create: `scripts/migrations/2026_06_28_add_agente_embeddings.{sql,py}` — `ALTER TABLE agent_memory_embeddings ADD COLUMN agente VARCHAR(20) NOT NULL DEFAULT 'web'` + `CREATE INDEX ... (user_id, agente)` + backfill (default já cobre legado).
- Create: `scripts/migrations/2026_06_28_add_agente_kg_entities.{sql,py}` — idem em `agent_memory_entities` + index `(user_id, agente)`.
- Modify: model de embeddings e `AgentMemoryEntity` (adicionar o campo `agente`).

- [ ] **Step 1: Teste RED** — `test_embeddings_tem_coluna_agente` / `test_kg_entities_tem_coluna_agente` (inserir registro com `agente='lojas'` e ler de volta).
- [ ] **Step 2:** Rodar, falha (coluna não existe).
- [ ] **Step 3:** Escrever o par `.sql`+`.py` de cada migration + campo no model. Aplicar local.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5: Commit** `feat(agente-mem): migrations agente em agent_memory_embeddings + agent_memory_entities`

### Task 2.2: O teste-contrato de isolamento (RED que guia toda a fase)

**Files:**
- Create: `tests/agente_lojas/conftest.py` (fixtures `app`/`db` da raiz + `mem_factory`)
- Create: `tests/agente/sdk/test_memory_isolation_por_agente.py`

**Interfaces:**
- Consome: `_load_user_memories_for_context(user_id, ..., agente_id)` (assinatura ALVO da Task 2.3).
- Produz: o invariante "sessão `lojas` vê ZERO `agente='web'`" — critério de aceite da fase inteira.

- [ ] **Step 1:** `mem_factory` (padrão `tests/agente/test_migracao_namespaces.py:36-60` — `create_file` **não** aceita `agente=`, usar construtor direto):

```python
# tests/agente_lojas/conftest.py
import pytest

@pytest.fixture
def mem_factory(db):
    from app.agente.models import AgentMemory
    def _criar(user_id, path, content, agente='web'):
        mem = AgentMemory(user_id=user_id, path=path, content=content,
                          agente=agente, is_directory=False)
        db.session.add(mem); db.session.flush()
        return mem
    return _criar
```

- [ ] **Step 2: Teste-contrato (RED):** semear memória `agente='web'` (user e empresa `user_id=0`) e `agente='lojas'`; chamar o pipeline de injeção com `agente_id='lojas'`; asseverar que **nenhuma** string de conteúdo `'web'` aparece no contexto retornado e **toda** `'lojas'` semeada elegível aparece.

```python
def test_sessao_lojas_nao_ve_memoria_web(app, db, mem_factory):
    from app.agente.sdk.memory_injection import _load_user_memories_for_context
    mem_factory(1, "/memories/user/pref.xml", "SEGREDO_WEB", agente="web")
    mem_factory(0, "/memories/empresa/heuristicas/odoo.xml", "HEUR_NACOM", agente="web")
    mem_factory(1, "/memories/user/pref.xml", "DADO_LOJA", agente="lojas")
    ctx = _load_user_memories_for_context(user_id=1, agente_id="lojas")  # assinatura ALVO
    blob = str(ctx)
    assert "SEGREDO_WEB" not in blob
    assert "HEUR_NACOM" not in blob
    assert "DADO_LOJA" in blob
```

- [ ] **Step 3:** Rodar: `pytest tests/agente/sdk/test_memory_isolation_por_agente.py -v` → **FAIL** (hoje `_load_user_memories_for_context` nem aceita `agente_id`, e os filtros vazam). Este RED permanece até o fim da fase.
- [ ] **Step 4: Commit** `test(agente-mem): contrato de isolamento por agente (RED — guia M3)`

### Task 2.3: Propagar `agente_id` e filtrar — `memory_injection.py` + `_rules`

**Files:**
- Modify: `app/agente/sdk/memory_injection.py` (vetores **M01–M13** — ver Apêndice; assinatura de `_load_user_memories_for_context`, `_build_session_window`, `_build_operational_directives_parts`, etc. ganham `agente_id`)
- Modify: `app/agente/sdk/memory_injection_rules.py:41-54` (**R01**)

**Padrão de fix (idêntico nos 14 pontos `WHERE agente=`):** adicionar
`AgentMemory.agente == agente_id` (ou `AgentSession.agente == agente_id`) ao
filtro; propagar `agente_id` pela cadeia de chamada até o caller.

- [ ] **Step 1:** Adicionar `agente_id: str` (sem default — **D3**, fail-closed) à assinatura pública `_load_user_memories_for_context` e helpers internos M02–M13/R01. Aplicar o filtro em cada um (lista no Apêndice).
- [ ] **Step 2:** Para Tier 2 semântico (**M04**) e materializações (**M05/M06**): aplicar `AgentMemory.agente == agente_id` como defesa em profundidade (mesmo pré-fix de embeddings).
- [ ] **Step 3:** Rodar o teste-contrato (Task 2.2) — deve passar a parte de `AgentMemory`/`AgentSession` (KG/embeddings ainda podem vazar até Task 2.5).
- [ ] **Step 4: Commit** `feat(agente-mem): isola memory_injection por agente_id (M01-M13,R01)`

### Task 2.4: Métodos de model compartilhados — `get_by_path` / `get_directory`

**Files:**
- Modify: `app/agente/models.py:654-656` (**H01** `get_by_path`), `:675-679` (**H02** `get_directory`/equivalente), `:322-329` caller (**M09**)

> **Cuidado (verificado):** `get_by_path` é chamado em **outros** contextos. Não
> quebrar a assinatura: adicionar `agente: str = 'web'` **só** com backfill de
> todos os callers no mesmo commit, OU criar `get_by_path_for_agent(user_id, path, agente)`
> e migrar callers de injeção. Preferir a 2ª (não-disruptiva).

- [ ] **Step 1: Teste RED** — `get_by_path_for_agent(1, "/x", "lojas")` não retorna registro `agente='web'`.
- [ ] **Step 2:** Rodar, falha.
- [ ] **Step 3:** Implementar overload + migrar callers de `memory_injection`.
- [ ] **Step 4:** Rodar suíte de memória + o contrato → PASS.
- [ ] **Step 5: Commit** `feat(agente-mem): get_by_path_for_agent (H01/H02) + caller M09`

### Task 2.5: Knowledge Graph + Embeddings

**Files:**
- Modify: `app/agente/services/knowledge_graph_service.py:876-882` (**K01** query), `:891-964` (**K02** links — só se entidades não filtrarem), `_upsert_entity` (gravar `agente`)
- Modify: `app/embeddings/service.py:838-870` (**E01** `_search_memories_pgvector` — `AND m.agente = :agente_id` no JOIN com `agent_memories`), `:897-908` (**E02** fallback)
- Modify: `app/agente/sdk/context_enrichment.py` / `app/agente/tools/ontology_query_tool.py:148-174` (**N05**, depende de K01)

- [ ] **Step 1: Teste RED** — semear entidade KG / embedding `agente='web'`; `query_graph_memories(..., agente_id='lojas')` e `buscar_memorias_semantica(..., agente_id='lojas')` retornam vazio p/ os `web`.
- [ ] **Step 2:** Rodar, falha.
- [ ] **Step 3:** Aplicar `AND agente = :agente_id` (K01) / JOIN-filter (E01/E02); `_upsert_entity` grava `agente`; propagar `agente_id` aos callers.
- [ ] **Step 4:** Rodar o teste-contrato (Task 2.2) — agora **deve passar inteiro** (todas as superfícies de retrieval cobertas).
- [ ] **Step 5: Commit** `feat(agente-mem): isola KG + embeddings por agente (K01-K02,E01-E02,N05)`

### Task 2.6: Intersession briefing

**Files:**
- Modify: `app/agente/services/intersession_briefing.py:129-133,154-158` (**B01**), `:289-293` (**B02**), `:304-309` (**B03**)

- [ ] **Step 1: Teste RED** — `build_intersession_briefing(user_id, agente_id='lojas')` não cita conteúdo `agente='web'`.
- [ ] **Step 2-4:** Propagar `agente_id` + filtros. Rodar → PASS.
- [ ] **Step 5: Commit** `feat(agente-mem): isola intersession briefing por agente (B01-B03)`

### Task 2.7: Vetores não-memória (parâmetro de perfil / allow-list)

**Files:**
- Modify: `app/agente/sdk/memory_injection.py:660-697` (**N01** `_DOMAIN_KEYWORDS` → `DOMAIN_KEYWORDS_BY_AGENT`)
- Modify: `app/agente/sdk/hooks.py:1558-1578` (**N02** hint SQL admin — guarda `agente_id == 'web'`)
- Modify: `app/agente/config/agent_loader.py:321-500` (**N03** filtro de subagentes por `surface`/perfil)
- Modify: `app/agente/sdk/context_enrichment.py:55-155` (**N04** skill hints → allow-list por perfil via `capability_registry`)

> Estes são o "M3 não-de-memória": mesmo com WHERE agente, o PreToolUse injeta
> hints SQL Nacom, o routing sugere skills Nacom, e o loader exporia
> `analista-carteira`/`especialista-odoo` ao operador de loja.

- [ ] **Step 1: Teste RED** — sessão `lojas`: PreToolUse não injeta hint de `carteira_principal`; routing não sugere skills `expedicao/odoo/ssw`; `load_agent_definitions(agente_id='lojas')` só devolve `orientador-loja`.
- [ ] **Step 2-4:** Implementar os 4. `N03`: campo `surface`/`agente` no frontmatter dos agentes Nacom + filtro `if surface not in (None,'',agente_id): continue`. Rodar → PASS.
- [ ] **Step 5: Commit** `feat(agente-mem): isola vetores não-memória por perfil (N01-N04)`

### Task 2.8: Selar fail-closed + suíte verde

- [ ] **Step 1:** Garantir que nenhuma assinatura de retrieval tem `agente_id` com default silencioso que mascare caller esquecido (**D3**). `grep` por chamadas sem `agente_id`.
- [ ] **Step 2:** Rodar a **suíte inteira de memória + o contrato**: `pytest tests/agente/ tests/agente_lojas/ -v`. Todos verdes; o teste-contrato (2.2) PASS.
- [ ] **Step 3: Commit** `chore(agente-mem): sela M3 — fail-closed, contrato de isolamento verde`

---

## FASE 3 — Parametrização do AgentClient por perfil (gated)

> **GATE DE ENTRADA:** Fase 2 completa **e testada por vetor** (contrato verde).
> **Blast radius ALTO:** `get_client()` é consumido por **7 callsites** em 3
> produtos — chat web (`routes/chat.py:918,965,2305`), Teams
> (`services.py:1164,1540,2386`), WhatsApp (`services.py:216`). Regressão aqui
> atinge produção dos três. Por isso: **por subsistema, nunca big-bang**, ordem
> `lojas → Teams → WhatsApp`, validando isolamento a cada perfil.
>
> **Detalhamento TDD micro fica para quando o gate abrir** — depende das
> assinaturas finais que a Fase 2 deixou com `agente_id`. Abaixo o desenho e os
> file:line travados; não é placeholder, é sequência gated.

**Pontos a destravar (singletons P1-P6, verificados):**

| # | Local | Mudança |
|---|---|---|
| 1 | `config/settings.py:162-170` | `get_settings()` `@lru_cache(maxsize=1)` → aceitar `agente_id` como chave OU injeção. `AgentLojasSettings` **já** é o perfil pronto (`agente_lojas/config/settings.py:16-40`, `AGENTE_ID='lojas'`). |
| 2 | `sdk/client.py:365-368` | `AgentClient.__init__(self, settings=None)` — fallback `get_settings()`; permite `AgentClient(settings=get_lojas_settings())` sem tocar consumidores. |
| 3 | `sdk/client.py:3008-3022` | `get_client(agente_id='web')` com dict `_clients: dict[str, AgentClient]`. Callsites sem arg → `'web'` (zero regressão). |
| 4 | `sdk/client.py:523-561` | `_build_full_system_prompt`: label `'<empresa_briefing>...Nacom Goya...'` (linha 555-557) → atributo de perfil `empresa_briefing_label` em settings (lojas = vazio/HORA). |
| 5 | `sdk/client.py:82-120` | `_discover_skills_from_project(agente_id='web')` — remover `@lru_cache(maxsize=1)` global; `'web'`=deny-list `SKILLS_DELEGADAS_SUBAGENTE`, `'lojas'`=allow-list `SKILLS_PERMITIDAS`. |
| 6 | `sdk/client.py:1718-1733` | `_build_options(..., allowed_agents=None)` — filtrar `agent_definitions` por `SUBAGENTS_PERMITIDOS` (lojas só `orientador-loja`). |

**Sequência:**
1. Introduzir o objeto de perfil + destravar singletons 1-6 atrás de `agente_id='web'` (comportamento idêntico — provar com a suíte web verde).
2. Migrar `app/agente_lojas/` para `get_client('lojas')` + `AgentLojasSettings`; aposentar o fork `AgentLojasClient`. Validar contrato de isolamento (Fase 2) + suíte lojas.
3. Só então avaliar dobrar Teams/WhatsApp na mesma abstração (decisão aberta #5 — fora do escopo inicial).

---

## Apêndice A — Os 28 vetores de M3

> 22 filtros `WHERE agente=` · 4 parâmetro-de-perfil/allow-list · 2 migrações. Fix
> padrão (memória): `+ AgentMemory.agente == agente_id` no filtro + propagar `agente_id`.

| ID | Local | Tipo | Ação |
|----|-------|------|------|
| M01 | `memory_injection.py:1291-1295` | WHERE | Tier 1 protected — `+ agente==agente_id` |
| M02 | `memory_injection.py:1307-1323` | WHERE | Tier 1.5 empresa user_id=0 |
| M03 | `memory_injection.py:1344-1357` | WHERE | Tier 1.6 heurísticas |
| M04 | `memory_injection.py:1380-1383` → `embeddings/service.py:856` | WHERE+migr | Tier 2 semântico (ver E01) |
| M05 | `memory_injection.py:1401-1413` | WHERE | Tier 2 materialização (defesa profund.) |
| M06 | `memory_injection.py:1481-1485` | WHERE | Tier 2b KG materialização |
| M07 | `memory_injection.py:1513-1525` | WHERE | Fallback recência |
| M08 | `memory_injection.py:226-229` | WHERE | `_build_session_window` (AgentSession) |
| M09 | `memory_injection.py:322-329` → `models.py:654` | WHERE | `_load_resolved_pendencias` (ver H01) |
| M10 | `memory_injection.py:885-901` | WHERE | operational_directives |
| M11 | `memory_injection.py:1024-1046` | WHERE | (retrieval adicional) |
| M12 | `memory_injection.py:712-714` | WHERE | (AgentSession) |
| M13 | `memory_injection.py:1966-1973` | WHERE | (retrieval adicional) |
| R01 | `memory_injection_rules.py:41-54` | WHERE | `_build_user_rules` ganha `agente_id` |
| K01 | `knowledge_graph_service.py:876-882` | WHERE+migr | entidades — `agente` + `_upsert_entity` |
| K02 | `knowledge_graph_service.py:891-964` | WHERE | links (só se entidades não filtrarem) |
| E01 | `embeddings/service.py:838-870` | WHERE+migr | `_search_memories_pgvector` JOIN-filter |
| E02 | `embeddings/service.py:897-908` | WHERE | `_search_fallback_memories` |
| B01 | `intersession_briefing.py:129-158` | WHERE | `build_intersession_briefing(agente_id)` |
| B02 | `intersession_briefing.py:289-293` | WHERE | |
| B03 | `intersession_briefing.py:304-309` | WHERE | |
| H01 | `models.py:654-656` | WHERE | `get_by_path_for_agent` |
| H02 | `models.py:675-679` | WHERE | `get_directory`/equivalente |
| N01 | `memory_injection.py:660-697` | perfil | `DOMAIN_KEYWORDS_BY_AGENT` |
| N02 | `hooks.py:1558-1578` | perfil | hint SQL admin — guarda `agente=='web'` |
| N03 | `agent_loader.py:321-500` | perfil | filtro subagentes por `surface`/perfil |
| N04 | `context_enrichment.py:55-155` | perfil | skill hints allow-list por perfil |
| N05 | `context_enrichment.py:177-256` → `ontology_query_tool.py:148-174` | WHERE | world_model (depende K01) |

**Migrações (2):** `agent_memory_embeddings` (M04/E01), `agent_memory_entities` (K01/N05).

---

## Self-Review

- **Cobertura A vs B:** as duas opções do enunciado estão endereçadas — A (drift) é resolvida por F0/F1 sem duplicar; B (centralizar) é o destino (F3), corrigida a chave do gate (identidade, não flag — D2). ✔
- **Decisões do usuário:** D1 (corpus por-agente) está em M02/M03 + namespace; D2/D3 (gate por agente, fail-closed) são Global Constraints + Task 2.8. ✔
- **Sem placeholders:** cada vetor tem file:line + ação; o fix mecânico é mostrado uma vez (DRY) e tabelado; testes têm assert real ou apontam arquivo-modelo existente com file:line. Pontos genuinamente dependentes de gate (F3 micro) estão **marcados como gated**, não como TODO. ✔
- **Consistência de tipos:** `agente_id: str ('web'|'lojas')` é a assinatura única propagada; `get_by_path_for_agent`, `build_subprocess_env`, `check_skills_option` nomeados consistentemente entre tasks. ✔
- **Risco residual conhecido:** o teto de M3 só fecha após Task 2.0 (memory_mcp_tool + jobs de consolidação não medidos). Se >10 vetores novos → re-dimensionar antes de F2 (gate explícito na Task 2.0 Step 2). ✔

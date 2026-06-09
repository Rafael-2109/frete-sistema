# A1 — Pipeline de Montagem do Contexto de Boot do Agente Web

**Data**: 2026-06-09
**Missão**: Mapear EXATAMENTE como o contexto de boot do Agente Web é montado, em que ordem, e o que controla cada bloco.

---

## 1. `_build_full_system_prompt()` — Sistema Prompt Estático (3 arquivos concatenados)

**Arquivo**: `app/agente/sdk/client.py:505–543`

### Ordem de concatenação

```
1. preset_operacional.md   (app/agente/prompts/preset_operacional.md)
2. system_prompt.md        (lido para self.system_prompt pelo AgentClient.__init__)
3. empresa_briefing.md     (app/agente/config/empresa_briefing.md)
```

**Código exato** (`client.py:531–541`):
```python
base = f"{preset}\n\n{custom_instructions}"
return (
    f"{base}\n\n"
    f"<empresa_briefing>\n"
    f"Contexto institucional Nacom Goya...\n\n"
    f"{briefing}\n"
    f"</empresa_briefing>"
)
```

### Onde cada arquivo é carregado

| Arquivo | Método de carregamento | Linha |
|---------|----------------------|-------|
| `preset_operacional.md` | `_load_preset_operacional()` | `client.py:412–431` |
| `system_prompt.md` | `_format_system_prompt(user_name, user_id)` (lê `self.system_prompt`) | `client.py:739–787` |
| `empresa_briefing.md` | `_load_empresa_briefing()` | `client.py:434–457` |

**Caminhos** (definidos em `config/settings.py:112,117`):
- `operational_preset_path = "app/agente/prompts/preset_operacional.md"`
- `empresa_briefing_path = "app/agente/config/empresa_briefing.md"`

### Feature flag que controla o modo

**Flag**: `USE_CUSTOM_SYSTEM_PROMPT` (`feature_flags.py:477`)
- `true` (default): chama `_build_full_system_prompt()` → os 3 arquivos concatenados como string pura
- `false` (rollback): usa `{"type": "preset", "preset": "claude_code", "append": custom_instructions}`

**Código** (`client.py:1669–1683`):
```python
if USE_CUSTOM_SYSTEM_PROMPT:
    options_dict["system_prompt"] = self._build_full_system_prompt(custom_instructions)
else:
    options_dict["system_prompt"] = {"type": "preset", "preset": "claude_code", "append": custom_instructions}
```

### Tamanho atual (bloco auto-medido por `prompt_size_audit.py`)

| Componente | Linhas | Bytes | Tokens (est.) |
|------------|-------:|------:|--------------:|
| `preset_operacional.md` | 117 | 5.079 | ~1,5K |
| `system_prompt.md` | 784 | 48.134 | ~13,8K |
| `empresa_briefing.md` | 81 | 5.084 | ~1,5K |
| **TOTAL estático** | **982** | **58.297** | **~16,7K** |

---

## 2. `setting_sources` — Carga do CLAUDE.md Raiz

**Arquivo**: `app/agente/sdk/client.py:1580`

```python
"setting_sources": ["project"] if permission_mode == "acceptEdits" else ["user", "project"],
```

- Modo servidor (default): `["project"]` — SDK lê apenas `.claude/settings.json` do projeto e descobre `CLAUDE.md` raiz + skills (`.claude/skills/*/SKILL.md`) via `setting_sources=["project"]`
- O CLAUDE.md raiz **NÃO está dentro da string** de `system_prompt` — é carregado separadamente pelo SDK através do mecanismo de `setting_sources`
- Skills são descobertas pela opção `skills` (SDK 0.1.77+) via `_discover_skills_from_project()` ou via `"Skill"` em `allowed_tools` (SDK < 0.1.77). Ver `client.py:1617–1634`

---

## 3. `ClaudeAgentOptions` — Campos configurados

**Arquivo**: `app/agente/sdk/client.py:1556–2013` (método `_build_options`)

| Campo | Valor | Linha |
|-------|-------|-------|
| `model` | `self.settings.model` (default `claude-opus-4-8`) | ~1540 |
| `system_prompt` | string pura (3 arquivos) ou dict preset | 1669 |
| `cwd` | `project_cwd` (raiz do repo) | 1573 |
| `setting_sources` | `["project"]` (servidor) | 1580 |
| `allowed_tools` | `list(self.settings.tools_enabled)` + MCP globs | 1585 |
| `permission_mode` | `"default"` ou `"acceptEdits"` | 1588 |
| `fallback_model` | `"sonnet"` | 1591 |
| `disallowed_tools` | `["NotebookEdit"]` | 1594 |
| `max_buffer_size` | `10_000_000` (10MB) | 1566 |
| `skills` | `_discover_skills_from_project()` (SDK 0.1.77+) | 1625 |
| `hooks` | `build_hooks(...)` (8 hooks) | 1830 |
| `session_id` | nosso UUID (se UUID válido) | 1643 |
| `env` | `{"CLAUDE_CODE_STREAM_CLOSE_TIMEOUT": "240000", "HOME": "/tmp"}` | 1603 |
| `agents` | subagentes descobertos (`.claude/agents/*.md`) | ~1688 |
| `effort` | mapeado de `effort_level` | ~1710 |

---

## 4. Hook `UserPromptSubmit` — Injeção Dinâmica (Seção 5 do contexto)

**Arquivo**: `app/agente/sdk/hooks.py:1250–1494` (função `_user_prompt_submit_hook`)

O hook é registrado em `hooks.py:1528–1532`:
```python
"UserPromptSubmit": [HookMatcher(hooks=[_user_prompt_submit_hook], timeout=120.0)]
```

### Tabela completa: Bloco → Gerador → Flag → Fonte → Condição → Ordem

| # | Bloco no payload | Arquivo:linha gerador | Flag controladora | Fonte de dados | Condição de injeção | Ordem em `full_context` |
|---|---|---|---|---|---|---|
| 1 | `resume_fallback_context` (`<resume_fallback_notice>`) | `hooks.py:1422–1438` | nenhuma (defensivo) | `resume_state['fallback']` (XML JSONB do DB) | Apenas quando `resume_state['failed']=True` E há fallback XML; 1º turno após falha de resume; cleared após injetar | **1ª** |
| 2 | `session_context` (`<session_context>`) | `hooks.py:1388–1419` | `USE_PROMPT_CACHE_OPTIMIZATION` (`AGENT_PROMPT_CACHE_OPTIMIZATION`, default `true`) E `USE_CUSTOM_SYSTEM_PROMPT` | `agora_utc_naive()` + `user_name` + `user_id` + `app.pessoal.USUARIOS_PESSOAL/USUARIOS_SQL_ADMIN` | Todo turno (web + teams), quando ambas flags true E `user_id` presente | **2ª** |
| 3 | `additional_context` (`<user_rules>` + `<user_memories>` + tier0) | `hooks.py:1287–1303` → `memory_injection.py:803–1468` | `USE_AUTO_MEMORY_INJECTION` (`AGENT_AUTO_MEMORY_INJECTION`, default `true`) | Banco `agent_memories` (PostgreSQL) + pgvector Voyage AI | Todo turno, quando `user_id` presente | **3ª** |
| 4 | `correction_hint` (`<system_hint>`) | `hooks.py:1306–1326` | nenhuma (sempre ativo se prompt > 10 chars) | Regex sobre texto do prompt (`hooks.py:1309–1314`) | Quando o prompt contém padrões de correção ("não", "errado", "correto é") | **4ª** |
| 5 | `debug_context` (`<debug_mode_context>`) | `hooks.py:1331–1352` | `get_debug_mode()` (estado da sessão via `permissions.py`) | Estado de debug mode da sessão | Apenas para admin em modo debug ativo | **5ª** |
| 6 | `sql_admin_context` (`<sql_admin_context>`) | `hooks.py:1357–1381` | nenhuma (condição pelo `user_id`) | `app.pessoal.USUARIOS_SQL_ADMIN` (hardcoded: `{1, 55, 62}`) | Apenas para `user_id in {1, 55, 62}` | **6ª** |
| 7 | `skill_hints_context` (`<skill_hints>`) | `hooks.py:1443–1452` → `context_enrichment.py:122–157` | `USE_AGENT_SKILL_RAG` (`AGENT_SKILL_RAG`, default **`false`**) | `capability_registry.build_registry()` (zero LLM, keyword matching) | Quando flag ON E prompt não vazio | **7ª** |
| 8 | `world_model_context` (`<world_model>`) | `hooks.py:1459–1468` → `context_enrichment.py:177–256` | `USE_AGENT_WORLD_MODEL_INJECT` (`AGENT_WORLD_MODEL_INJECT`, default **`false`**) | `ontology_query_tool.query_ontology_entities()` (DB ontologia) | Quando flag ON E `user_id` E prompt presentes | **8ª** |

**Concatenação final** (`hooks.py:1471`):
```python
full_context = resume_fallback_context + session_context + (additional_context or "") + correction_hint + debug_context + sql_admin_context + skill_hints_context + world_model_context
```

**Retorno ao SDK** (`hooks.py:1484–1488`):
```python
return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": full_context}}
```

---

## 5. Detalhamento do `additional_context` — Pipeline de Memórias

**Arquivo**: `memory_injection.py:803–1468` (função `_load_user_memories_for_context`)

### Tiers de memória (dentro de `<user_memories>`)

| Tier | Nome | Arquivo:linha | Flag | Fonte | Condição | Montagem final |
|------|------|-------------|------|-------|----------|----------------|
| L1 (topo absoluto) | `<user_rules>` | `memory_injection.py:884–901` | `USE_USER_RULES_CHANNEL` (`AGENT_USER_RULES_CHANNEL`, default `true`) + `USE_USER_RULES_TOP` (`AGENT_USER_RULES_TOP`, default `true`) | `memory_injection_rules._build_user_rules(user_id)` (DB) | Sempre quando flag ON | **ANTES** do `<user_memories>` |
| Tier 0 | `<recent_sessions>` + `<pendencias_acumuladas>` | `memory_injection.py:903–906`, `_build_session_window:142–231` | nenhuma (sempre ativo) | `AgentSession.query` (últimas 5, com `summary`) | Sempre | APÓS `</user_memories>` (tier0_text) |
| Tier 0b | `<intersession_briefing>` | `memory_injection.py:908–918` | `USE_INTERSESSION_BRIEFING` (`AGENT_INTERSESSION_BRIEFING`, default `true`) | `intersession_briefing.build_intersession_briefing(user_id)` | Sempre quando flag ON | APÓS `</user_memories>` |
| Tier 0c | `<operational_directives>` + `<routing_context>` | `memory_injection.py:920–927`, `_build_routing_context:644–770` | `USE_OPERATIONAL_DIRECTIVES` (`AGENT_OPERATIONAL_DIRECTIVES`, default **`false`**) | `AgentMemory` (heuristicas/protocolos empresa nivel 5) + `AgentSession` | Sempre (routing); diretivas só se flag ON | APÓS `</user_memories>` |
| Tier 1 | user.xml, preferences.xml, user_expertise.xml | `memory_injection.py:933–943` | nenhuma (sempre injetado) | `AgentMemory` (paths fixos) | Sempre | DENTRO de `<user_memories>` |
| Tier 1.5 | Perfil empresa do usuário | `memory_injection.py:946–968` | nenhuma (sempre injetado) | `AgentMemory.path LIKE '/memories/empresa/usuarios/%'` (user_id=0) | Se perfil contém `user_id` do usuário | DENTRO de `<user_memories>` |
| Tier 1.6 | Heurísticas empresa nível 5 | `memory_injection.py:971–1007` | `USE_OPERATIONAL_DIRECTIVES` (se ON, skip — já em operational_directives) | `AgentMemory.path LIKE '/memories/empresa/heuristicas/%'` (user_id=0) | Quando `USE_OPERATIONAL_DIRECTIVES=false` | DENTRO de `<user_memories>` |
| Tier 2 | Memórias semânticas (top 10 por composite score) | `memory_injection.py:1009–1093` | `MEMORY_SEMANTIC_SEARCH` + `MEMORY_INJECTION_MIN_SIMILARITY` (default `0.45`) | `buscar_memorias_semantica(prompt, user_id)` → Voyage AI + pgvector | Quando embedding disponível E prompt presente | DENTRO de `<user_memories>` |
| Tier 2b | Memórias via Knowledge Graph | `memory_injection.py:1099–1146` | `MEMORY_KNOWLEDGE_GRAPH` | `knowledge_graph_service.query_graph_memories()` | Quando KG ativo E prompt presente | DENTRO de `<user_memories>` |
| Fallback | Memórias por recência | `memory_injection.py:1148–1164` | nenhuma (fallback se sem semântica) | `AgentMemory.query` (últimas 15 por updated_at) | Quando Tier 2 não retornou nada | DENTRO de `<user_memories>` |

### Montagem final do `<user_memories>` (`memory_injection.py:1341–1370`)

```
[user_rules]           ← TOPO ABSOLUTO (fora de <user_memories>)
<user_memories>
  [tier 1: user.xml, preferences.xml, user_expertise.xml]
  [tier 1.5: perfil empresa do usuário]
  [tier 1.6: heurísticas nível 5 — só se USE_OPERATIONAL_DIRECTIVES=false]
  [tier 2: semântica + composite score]
</user_memories>
[tier 0: recent_sessions + pendencias_acumuladas]
[tier 0b: intersession_briefing]
[tier 0c: operational_directives + routing_context]
```

---

## 6. `intersession_briefing` — Subcomponentes internos

**Arquivo**: `app/agente/services/intersession_briefing.py:27–101`

| Sub-bloco | Linha | Flag | Fonte |
|-----------|-------|------|-------|
| `<last_intent>` | :46 | nenhuma | `AgentSession.summary` (JSONB) |
| Erros Odoo sync | :51 | nenhuma | tabela `odoo_sync_errors` (últimas 6h) |
| Falhas import pedidos | :56 | nenhuma | tabela de pedidos |
| Conflitos de memória | :61 | nenhuma | `AgentMemory` com conflito |
| Commits recentes | :66 | `USE_COMMIT_BRIEFING` (env, default `true`) | `git log` (subprocess) |
| `<stale_empresa>` | :73 | nenhuma | `AgentMemory` empresa > 60 dias |
| Relatório D7 (intelligence report) | :78 | nenhuma | D7 cron semanal |
| `<improvement_responses>` | :83 | `AGENT_IMPROVEMENT_DIALOGUE` (env, default `false`) | `AgentImprovementDialogue` (respostas Claude Code) |

---

## 7. Controle de Orçamento (Budget) por Bloco

| Bloco | Limite configurado | Arquivo:linha |
|-------|-------------------|--------------|
| user.xml (pointer mode) | `USER_XML_POINTER_THRESHOLD` (default 3000 chars) → substitui por ponteiro | `feature_flags.py:202`, `memory_injection.py:1229–1244` |
| Budget total memórias (Sonnet) | 6000 chars (base) × fator ajuste prompt | `memory_injection.py:1190–1203` |
| Budget total memórias (Haiku) | 3000 chars | idem |
| Budget total memórias (Opus) | `None` (sem limite, 1M context) | idem |
| Tier 1.5 (perfil empresa) | truncado a 400 chars | `memory_injection.py:1261–1263` |
| `<directive>` titulo | 100 chars | `memory_injection.py:602` |
| `<directive>` when | 250 chars | `memory_injection.py:604` |
| `<directive>` do | 350 chars | `memory_injection.py:606` |
| `<active_traps>` título | 80 chars | `memory_injection.py:736` |
| `<active_traps>` prescricao | 200 chars | `memory_injection.py:741` |
| Hook timeout | 120 segundos | `hooks.py:1531` |

**A ordem dos blocos NÃO é configurável** — está hardcoded no `full_context` string concatenation em `hooks.py:1471`. Não existe parâmetro para reordenar.

**Cache de injeção por sessão** (`memory_injection.py:28–36`): TTL 30min, cap 500 sessões. Invalidado por mutações de memória (`save_memory`, `update_memory`, `delete_memory`).

---

## 8. Flags `skill_hints` e `world_model` — Nomes Exatos + Call Sites

### `skill_hints` / `USE_AGENT_SKILL_RAG`

**Definição** (`feature_flags.py:1017`):
```python
USE_AGENT_SKILL_RAG = os.getenv("AGENT_SKILL_RAG", "false").lower() == "true"
```

**Call sites (todos os arquivos onde é usada ou referenciada)**:
- `feature_flags.py:1017` — definição
- `hooks.py:1445` — `from ..config.feature_flags import USE_AGENT_SKILL_RAG` + verificação
- `context_enrichment.py:29` — documentação (comentário)

**Gerador**: `context_enrichment.py:122–157` (`build_skill_hints_block`)

### `world_model` / `USE_AGENT_WORLD_MODEL_INJECT`

**Definição** (`feature_flags.py:1031`):
```python
USE_AGENT_WORLD_MODEL_INJECT = os.getenv("AGENT_WORLD_MODEL_INJECT", "false").lower() == "true"
```

**Call sites**:
- `feature_flags.py:1031` — definição
- `hooks.py:1461` — `from ..config.feature_flags import USE_AGENT_WORLD_MODEL_INJECT` + verificação
- `context_enrichment.py:30` — documentação (comentário)

**Gerador**: `context_enrichment.py:177–256` (`build_world_model_block`)

**Nota**: Ambas as flags têm default `false` — os blocos já estão **desativados por padrão** em produção. Para remoção completa do código, os pontos a tocar são:
1. `feature_flags.py:1017` e `:1031` — remover definições das constantes
2. `hooks.py:1440–1468` — remover os dois blocos `try/except` com as chamadas
3. `hooks.py:1470` — remover `skill_hints_context` e `world_model_context` da concatenação
4. `hooks.py:1477–1480` — remover log de `skill_hints_chars` e `world_model_chars`
5. `context_enrichment.py` — remover arquivo inteiro (só serve as duas funções)
6. `app/agente/sdk/__init__.py` — verificar se `context_enrichment` é re-exportado

---

## 9. Condição de Injeção: Todo Turno vs Apenas 1º Turno

**IMPORTANTE**: O hook `UserPromptSubmit` dispara em **TODOS OS TURNOS** da conversa (toda vez que o usuário submete uma mensagem), não apenas no primeiro turno. Não existe separação por "turno 1 vs demais".

Exceção parcial: `resume_fallback_context` é injetado apenas quando `resume_state['failed']=True`, e após a injeção o estado é limpo (`resume_state['failed'] = False` em `hooks.py:1438`) — portanto efetivamente é injetado apenas UMA VEZ (no primeiro turno após falha de resume).

O cache de memórias (`_SESSION_INJECTION_CACHE` em `memory_injection.py:32`) mitiga o custo de SQL + embeddings em turnos repetidos (TTL 30min).

---

## 10. Diagrama da Ordem de Montagem Completa

```
CAMADA ESTÁTICA (montada no connect, antes do 1º turno):
─────────────────────────────────────────────────────
option system_prompt:
  1. preset_operacional.md     [117 linhas, ~1.5K tok]
  2. system_prompt.md          [784 linhas, ~13.8K tok]
  3. <empresa_briefing>        [81 linhas, ~1.5K tok]
  
setting_sources=["project"]:
  4. CLAUDE.md raiz            [carregado pelo SDK automaticamente]
  5. SKILL.md de cada skill    [28 skills descobertas]

CAMADA DINÂMICA (hook UserPromptSubmit, todo turno):
─────────────────────────────────────────────────────
additionalContext (concatenação em hooks.py:1471):
  1. resume_fallback_context   [só quando resume falhou — 1x]
  2. <session_context>         [data/hora + nome + user_id]    flag: AGENT_PROMPT_CACHE_OPTIMIZATION
  3. additional_context:
       [<user_rules>]          [topo absoluto]                 flag: AGENT_USER_RULES_CHANNEL
       <user_memories>
         [Tier 1: user.xml, prefs, expertise]
         [Tier 1.5: perfil empresa]
         [Tier 1.6: heurísticas nível 5]                       flag: não se AGENT_OPERATIONAL_DIRECTIVES=true
         [Tier 2: semântica top-10]
       </user_memories>
       [<recent_sessions> + <pendencias>]                       Tier 0
       [<intersession_briefing>]                               flag: AGENT_INTERSESSION_BRIEFING
       [<operational_directives> + <routing_context>]          flag: AGENT_OPERATIONAL_DIRECTIVES
  4. correction_hint           [<system_hint> se prompt corretivo]
  5. debug_context             [<debug_mode_context> se admin em debug]
  6. sql_admin_context         [<sql_admin_context> se user em {1,55,62}]
  7. skill_hints_context       [<skill_hints> — DESATIVADO default]     flag: AGENT_SKILL_RAG=false
  8. world_model_context       [<world_model> — DESATIVADO default]     flag: AGENT_WORLD_MODEL_INJECT=false
```

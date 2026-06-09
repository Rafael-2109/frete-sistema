# A2 — Mecanismo de Seleção e Injeção de Memórias
# Subagente: investigacao do pipeline de boot do Agente Web
# Data: 09/06/2026

## 1. COMO AS MEMÓRIAS SÃO SELECIONADAS PARA O BOOT

### Arquivo central: app/agente/sdk/memory_injection.py
Função principal: `_load_user_memories_for_context(user_id, prompt, model_name)`
(linhas 803–1468)

O pipeline é MULTI-TIER, não RAG puro nem top-k fixo:

---

### Tier 0 — SEMPRE injetado (fora do budget de memórias)
Fonte: código em linhas 874–927

- **L1 User Rules** (`memory_injection_rules.py:_build_user_rules`): memórias com
  `priority='mandatory'` do usuário E user_id=0. Ordenadas por `correction_count DESC`.
  Cap: `MANDATORY_RULES_MAX_COUNT` (default 12, env `AGENT_MANDATORY_RULES_MAX_COUNT`).
  Flag: `USE_USER_RULES_CHANNEL` (default true). Injetadas NO TOPO do contexto
  (antes do `<user_memories>`) quando `USE_USER_RULES_TOP=true` (default true).

- **Session window** (`_build_session_window`): últimas 5 sessões com summary JSONB.
  Query: `AgentSession.query.filter(...).order_by(updated_at.desc()).limit(5)`.
  Pendências com TTL=2 dias (`PENDENCIA_TTL_DAYS`), deduplicadas, max 5.

- **Briefing inter-sessão** (`intersession_briefing.build_intersession_briefing`):
  Flag `USE_INTERSESSION_BRIEFING` (default true).

- **Routing context** (`_build_routing_context`): domínio predominante (keyword match
  nas últimas 10 sessões), top 3 armadilhas ativas do domínio, skills sugeridas.
  Inclui `_build_operational_directives`: heurísticas empresa `nivel>=5` com
  `importance_score >= MANDATORY_IMPORTANCE_THRESHOLD` (default 0.7),
  max `MANDATORY_MAX_COUNT` (default 5) heurísticas orgânicas +
  diretivas constitucionais fixas (hardcoded em `_CONSTITUTIONAL_DIRECTIVES`).

---

### Tier 1 — Memórias protegidas (SEMPRE injetadas, dentro do `<user_memories>`)
Fonte: linhas 933–968

Paths fixos:
```python
PROTECTED_PATHS = [
    "/memories/user.xml",
    "/memories/preferences.xml",
    "/memories/user_expertise.xml",
]
```
Query: `AgentMemory.query.filter(user_id=user_id, path.in_(PROTECTED_PATHS))`

Nenhum budget limita Tier 1. Se `USE_USER_XML_POINTER=true` (default false) e
user.xml > `USER_XML_POINTER_THRESHOLD` (default 3000 chars), aplica compressão:
só `<resumo>` + `<contextualizacao>` + ponteiro para view_memories.

---

### Tier 1.5 — Perfis empresa do usuário (SEMPRE)
Fonte: linhas 949–969

Query: `AgentMemory.query.filter(user_id=0, path.like('/memories/empresa/usuarios/%'))`
Filtro: só injeta se o content do perfil contém `user_id` atual (string match em content_lower).
Trunca a 400 chars.

---

### Tier 1.6 — Heurísticas empresa nivel 5 (SEMPRE)
Fonte: linhas 971–1007

Só ativo quando `USE_OPERATIONAL_DIRECTIVES=false` (default false em feature_flags.py:215 —
**ATENÇÃO: o valor default é "false"**, então Tier 1.6 está ATIVO quando a flag está OFF).
Quando a flag está ON, Tier 0 já injetou as heurísticas como `<operational_directives>` e
Tier 1.6 é pulado (evita duplicação).

---

### Tier 2 — Busca semântica RAG (budget-limited)
Fonte: linhas 1009–1096

Parâmetros:
- `MEMORY_SEMANTIC_SEARCH` (app/embeddings/config.py:142, default true)
- Over-fetch: `limite=20` candidatos (hardcoded em memory_injection.py:1023)
- Reranking via Voyage rerank-2.5-lite se `MEMORY_RERANKING_ENABLED`
- Threshold mínimo: `MEMORY_INJECTION_MIN_SIMILARITY=0.45` (env `AGENT_MEMORY_MIN_SIMILARITY`)
  — sobrescreve o default global de `THRESHOLD_MEMORY=0.40` de embeddings/config.py
- Após filtrar protegidos: top 10 por **composite score** (ver fórmula abaixo)
- Filtro adicional: `is_cold=false` e `directive_status IN (NULL, 'ativa')`

**Fórmula composite score** (linhas 773–800, função `_composite_score`):
```
Com similarity: 0.3*decay + 0.3*importance + 0.4*similarity
Sem similarity: 0.3*decay + 0.7*importance
Com USE_RECURRENCE_SCORE=true: 0.25*decay + 0.25*importance + 0.35*similarity + 0.15*recurrence
```

**Category-aware decay** (linhas 263–277):
```python
'permanent': 1.0       # sem decay
'structural': 0.9995   # meia-vida ~58 dias
'operational': 0.999   # meia-vida ~29 dias
'contextual': 0.990    # meia-vida ~2.9 dias
```

---

### Tier 2b — Knowledge Graph (complementar)
Fonte: linhas 1099–1146

`query_graph_memories(user_id, prompt, exclude_memory_ids, limit=5)`.
Só ativo quando `MEMORY_KNOWLEDGE_GRAPH=true` (default true).
Composite score >= 0.3 para entrar.

---

### Fallback — Recência (quando semântica não retorna nada)
Fonte: linhas 1148–1164

`AgentMemory.query.filter(user_id.in_([user_id, 0])).order_by(updated_at.desc()).limit(15)`

---

### Budget adaptativo (linhas 1186–1203)
```python
Opus:   sem limite (budget=None, todos os candidatos entram)
Haiku:  3000 chars base
Sonnet: 6000 chars base (default)
Ajuste: budget *= max(0.5, 1.0 - len(prompt) / 10000)
```

### Cache de sessão (Fase 5, linhas 840–857)
TTL 30 minutos por session_id. Invalidado em save/update/delete via
`invalidate_injection_cache_for_user()`. Cap: 500 entradas.

---

## 2. DUPLICAÇÃO user_rules vs user_memories

### O que é observado no dump (contexto_boot.md linhas 1827–1840 e 1915–1924)

A memória `/memories/corrections/agente-afirmou-que-subagente-carrega-system-prompt-md-do-pai.xml`
aparece em DOIS lugares:

**Local A** — `<user_rules priority="mandatory">` (Tier 0 / L1, topo do contexto):
```xml
<rule path="/memories/corrections/agente-afirmou-que-subagente-carrega-system-prompt-md-do-pai.xml" scope="pessoal">
  [geral] NUNCA: Quando descrever arquitetura de subagentes...
</rule>
```

**Local B** — `<user_memories>` (dentro do bloco de memórias via Tier 2 semântico):
```xml
<memory path="/memories/corrections/agente-afirmou-que-subagente-carrega-system-prompt-md-do-pai.xml" kind="geral">
  [geral] NUNCA: Quando descrever arquitetura de subagentes...
</memory>
```

### Por que acontece: design com bug de filtragem

**Tier L1 (`_build_user_rules`)** filtra por `priority='mandatory'` (memory_injection_rules.py:33).
**Tier 2 (semântica)** filtra protegidos (PROTECTED_PATHS fixos — apenas user.xml, preferences.xml,
user_expertise.xml, linhas 933–936). NÃO exclui memórias que já estão em user_rules.

O código em `_load_user_memories_for_context` cria `protected_ids` apenas com os Tier 1 protegidos
(linha 944). As memórias do L1 (user_rules) NÃO são adicionadas a `protected_ids`.

Portanto, se uma memória com `priority='mandatory'` tem embedding que bate com o prompt atual,
ela entra via Tier 2 também. **Duplicação por omissão de filtragem — não é design intencional.**

A correção seria adicionar os IDs das `rules` ao `protected_ids` após `_build_user_rules()`:
```python
if rules_block_top:
    # IDs das mandatory rules precisam ser excluídos do Tier 2
    rule_ids = {r.id for r in rules}
    protected_ids.update(rule_ids)
```

---

## 3. PROVENIÊNCIA: session_id de origem da memória

### Tabela agent_memories (schema completo de .claude/skills/consultando-sql/schemas/tables/agent_memories.json)

Colunas presentes:
- `id`, `user_id`, `agente`, `path`, `content`, `is_directory`
- `importance_score`, `last_accessed_at`, `category`, `is_cold`
- `usage_count`, `effective_count`, `correction_count`, `has_potential_conflict`
- `escopo`, `directive_status`, `priority`, `error_signature`
- `harmful_count`, `helpful_count`, `created_by`, `reviewed_at`
- `created_at`, `updated_at`
- `meta` (JSONB — adicionado 2026-06-08, migration `2026_06_08_agent_memories_meta_jsonb`)

**NÃO existe coluna `source_session_id`** na tabela `agent_memories`.

### Onde session_id é capturado (parcialmente)

1. **Knowledge Graph (`AgentKnowledgeNode`)**: tem `source_session_ids: ARRAY(Text)` em models.py:1223.
   Populado quando `USE_AGENT_ONTOLOGY=true` (memory_mcp_tool.py:2099–2120).
   A flag `USE_AGENT_ONTOLOGY` está OFF por default (models.py:2100 — flag OFF -> `_kg_session_id = None`).

2. **AgentImprovementDialogue**: tem `source_session_ids: ARRAY(Text)` (models.py:1223).
   Populado no `register_improvement` tool (memory_mcp_tool.py:3468–3485).

3. **Na própria memória via campo `origem` do meta** (memory_format.py:35):
   Chave opcional `origem: str` no dict canônico. Texto livre, não FK para agent_sessions.
   Usado por pattern_analyzer quando gera memórias empresa (campo de "proveniência leve").

### O que falta para proveniência navegável

Para atender RP-2 do Rafael ("saber de qual sessão veio a memória e navegar para o raw"):

**O que falta:**
1. **Campo `source_session_id` (FK TEXT nullable)** na tabela `agent_memories` — uma coluna por linha
   (não array, pois cada memória tem uma sessão de origem primária).
2. **População no save_memory** (memory_mcp_tool.py:1930–2002): capturar
   `get_current_session_id()` e gravar no novo campo ao criar/atualizar.
3. **Tool de navegação**: search_sessions já existe (`session_search_tool.py`), mas não há
   tool que dada uma `memory_id` retorne o session_id + link para as mensagens.
4. **Exposição no contexto**: o `<memory>` tag injetado em memory_injection.py não inclui
   session_id (apenas path/kind/dominio/nivel). O agente não vê a proveniência na injeção.

---

## 4. FRESCOR E CONFIANÇA

### Na tabela agent_memories
- `last_accessed_at`: atualizado a cada injeção (UPDATE em memory_injection.py:1380–1393)
- `updated_at`: atualizado em save/update (via onupdate SQLAlchemy)
- `reviewed_at`: nullable, ciclo de revisão v5 (models.py:599) — populado manualmente
- **Sem `last_confirmed`** — campo inexistente no schema

### No user.xml (Tier 1 protegido)
O arquivo `/memories/user.xml` tem metadados INLINE no próprio XML:
```xml
<user_profile updated_at="08/06/2026" confidence="alta" sessions="25">
```
Estes atributos (`updated_at`, `confidence`, `sessions`) são ESCRITOS pelo pattern_analyzer
quando gera o perfil — são texto livre no content, não colunas do banco.
**Não há campo `confidence` na tabela agent_memories.**

### No campo meta (JSONB, 2026-06-08)
O dict canônico tem campo `nivel` (int 3–9), mas não tem `confidence` ou `last_confirmed`.
O campo `criterios` (lista de int) codifica QUAIS critérios a memória atende.

### Metadados de frescor existentes (resumo)
| Metadado | Onde vive | Atualizado quando |
|----------|-----------|-------------------|
| `last_accessed_at` | coluna DB | A cada injeção no boot |
| `updated_at` | coluna DB | A cada save/update |
| `usage_count` | coluna DB | A cada injeção |
| `effective_count` | coluna DB | Quando agent usa o conteúdo |
| `reviewed_at` | coluna DB nullable | Revisão manual |
| `importance_score` | coluna DB | Na criação/update |
| `category` | coluna DB | Na criação/update (decay rate) |
| confidence/updated_at | texto em user.xml | Gerado pelo pattern_analyzer |
| `nivel` | meta JSONB | Na criação/update |

**Falta**: `last_confirmed` (última vez que o conteúdo foi verificado como ainda válido),
`confidence` como campo queryável, e `freshness_score` derivado para o retrieval.

---

## 5. CONTROLE DE TAMANHO POR MEMÓRIA INJETADA

### Tier 1 (user.xml, preferences.xml, user_expertise.xml)
- **Sem truncamento por padrão**: Tier 1 é sempre incluído sem corte.
- Exceção: `USE_USER_XML_POINTER=false` (default) — quando `true`, user.xml > 3000 chars
  é comprimido para `<resumo>` + `<contextualizacao>` + ponteiro.
- **NÃO há sumarização automática no momento da injeção** para Tier 1.

### Tier 1.5 (perfis empresa)
- Truncamento HARD a 400 chars (memory_injection.py:1262):
  ```python
  if len(content) > 400:
      content = content[:400] + "..."
  ```

### Tier 2 (semântica)
- Seleção por budget (linhas 1325–1338): SKIP se não cabe, não trunca.
- Ordem: maior composite score primeiro, mas pode pular memórias que não cabem.
- **Sem truncamento individual**: a memória entra inteira ou não entra.

### Problema documentado (R-6 do Rafael)
A armadilha `ibge-float-em-planilha` tem ~27 linhas e entra com o mesmo peso
que uma linha de perfil. Isso ocorre porque:
1. Não há campo de "tamanho máximo por memória" no schema.
2. Budget total é controlado, mas não há limite por entrada individual.
3. O composite score pondera por importância/similaridade, mas não por tamanho.

**Ausência de sumarização na injeção**: não existe código que sumarize memórias longas
antes de injetá-las. A única compressão é o `USE_USER_XML_POINTER` para user.xml.

---

## 6. ESQUEMA COMPLETO DA TABELA agent_memories

Fonte: .claude/skills/consultando-sql/schemas/tables/agent_memories.json + models.py

| Coluna | Tipo | Nullable | Default | Notas |
|--------|------|----------|---------|-------|
| id | integer | N | — | PK |
| user_id | integer | N | — | FK → usuarios.id; 0=empresa |
| agente | varchar(20) | N | 'web' | 'web' ou 'lojas' |
| path | varchar(500) | N | — | Path virtual filesystem |
| content | text | Y | — | Content legível; derivado do meta para estruturadas |
| is_directory | boolean | N | false | Flag de diretório virtual |
| importance_score | float | N | 0.5 | Heurístico 0-1 |
| last_accessed_at | timestamp | N | now | Atualizado a cada injeção |
| category | varchar(20) | N | 'operational' | permanent/structural/operational/contextual |
| is_cold | boolean | N | false | Tier frio = não injetado automaticamente |
| usage_count | integer | N | 0 | Vezes injetada no contexto |
| effective_count | integer | N | 0 | Vezes que o agente usou o conteúdo |
| correction_count | integer | N | 0 | Vezes que usuário corrigiu após injeção |
| has_potential_conflict | boolean | N | false | Flag de contradição detectada |
| escopo | varchar(20) | N | 'pessoal' | 'pessoal' ou 'empresa' |
| directive_status | varchar(20) | Y | NULL | NULL/candidata/shadow/ativa/despromovida |
| priority | varchar(20) | N | 'contextual' | mandatory/advisory/contextual |
| error_signature | varchar(64) | Y | NULL | Hash de intenção do erro (loop corretivo) |
| harmful_count | integer | N | 0 | Regra ativa + reincidência do erro |
| helpful_count | integer | N | 0 | Regra ativa + sem reincidência |
| created_by | integer | Y | NULL | FK → usuarios.id (auditoria empresa) |
| reviewed_at | timestamp | Y | NULL | Última revisão manual |
| created_at | timestamp | Y | now | |
| updated_at | timestamp | Y | now | |
| meta | JSONB | Y | NULL | Formato canônico (2026-06-08): kind/dominio/nivel/titulo/when/do |

**Índices**: ix_agent_memories_agente, ix_agent_memories_category,
ix_agent_memories_user_errsig (user_id, error_signature), ix_agent_memories_user_id.
**Constraint única**: (user_id, path).

**Campo ausente para proveniência**: NÃO existe `source_session_id` em agent_memories.
O KG (AgentKnowledgeNode) tem `source_session_ids ARRAY(Text)` mas é entidade separada.

---

## 7. O QUE PRECISA MUDAR PARA INJEÇÃO POR INTENT + PROVENIÊNCIA NAVEGÁVEL

### 7.1 Para injeção por intent (RP-2 do Rafael)

O mecanismo atual é: semântica do prompt inteiro → similarity → composite score.
Isso aproxima do intent, mas não é explícito. Problemas:
- Para sessões sobre "contexto inicial do agente" (como a do Rafael), o prompt tem pouco
  conteúdo útil para embedding, então similaridade é baixa e memórias irrelevantes entram
  pelo fallback de recência ou Tier 0 obrigatório.

**O que falta:**
1. **Intent classifier leve (Haiku ou regex)**: classificar o prompt em domínios ANTES do
   RAG e filtrar Tier 2 por domínio (hoje existe `_compute_user_domain` baseado em sessões
   históricas, mas não no TURNO ATUAL).
2. **Filtro de Tier 0c por intent atual**: o routing_context usa domínio histórico, não o
   intent do turno. Resultado: armadilhas do domínio "admin" são injetadas mesmo quando o
   assunto é expedição.
3. **Exclusão de Tier 2 quando irrelevante**: a fatura 161-9 entrou porque foi salva com
   `priority='mandatory'` ou teve alta similarity com algum termo do prompt. O sistema
   não tem como distinguir "exemplo few-shot relevante" de "memória de contexto irrelevante".

### 7.2 Para proveniência navegável

**Mudanças de schema:**
1. Adicionar `source_session_id TEXT NULLABLE` à tabela `agent_memories`
   (migration necessária — não quebra constraint única).

**Mudanças de código:**
2. `memory_mcp_tool.py:save_memory` (linha ~1990–2000): capturar
   `get_current_session_id()` e gravar em `mem.source_session_id = session_id`.
3. `memory_mcp_tool.py:update_memory` (linha ~2200+): manter source_session_id original
   ou adicionar lógica de "last_modified_session_id".
4. `memory_injection.py:_memory_open_tag` (linha 279–295): adicionar atributo
   `session_id="{mem.source_session_id}"` quando disponível.

**Exposição ao agente:**
5. Tag injetada passaria a ser:
   ```xml
   <memory path="/memories/corrections/..." kind="correcao" session_id="abc123...">
   ```
   O agente pode então chamar `search_sessions(session_id="abc123...")` para ver o raw.

**Tool necessária** (opcional mas recomendada):
6. `get_memory_provenance(memory_path)`: retorna source_session_id + link para sessão.
   Evita que o agente precise saber que "session_id no atributo do XML = chave para search_sessions".

---

## RESUMO EXECUTIVO

| Pergunta | Resposta |
|----------|----------|
| Seleção por RAG/intent? | RAG semântico (Voyage) + composite score (0.4*sim + 0.3*decay + 0.3*importance). Intent do TURNO atual NÃO é usado explicitamente — domínio é histórico. |
| Top-k? | Over-fetch 20 candidatos → rerank → top 10 por composite → SKIP por budget (Sonnet: 6000 chars base) |
| Threshold de similarity | 0.45 (MEMORY_INJECTION_MIN_SIMILARITY) |
| Duplicação user_rules vs user_memories | BUG de omissão: protected_ids não inclui memórias do L1 (user_rules), permitindo que entrem também via Tier 2 semântico |
| source_session_id em agent_memories? | NÃO existe — campo ausente. Apenas AgentKnowledgeNode e AgentImprovementDialogue têm source_session_ids. |
| Confidence/last_confirmed? | Não existe como campo DB. `confidence` aparece apenas como atributo inline em user.xml (texto livre gerado pelo pattern_analyzer). |
| Controle de tamanho por memória? | Só Tier 1.5 trunca (400 chars). Tier 1 usa pointer opcional (flag OFF). Tier 2 entra inteira ou não entra. Sem sumarização na injeção. |
| Para injeção por intent | Falta: classifier do turno atual + filtro de tier por intent + exclusão de few-shots irrelevantes |
| Para proveniência navegável | Falta: coluna source_session_id em agent_memories + população no save + exposição na tag injetada |

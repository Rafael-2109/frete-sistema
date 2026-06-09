# C3 — Pesquisa: Padrões de Memória de Agentes
## Injeção, Proveniência, Frescor e Intent-Based Retrieval

**Subagente**: C3 (pesquisa externa)
**Data**: 09/06/2026
**Escopo**: Padrões externos (Anthropic Cookbook, Letta/MemGPT, Zep/Graphiti, LangMem, Manus) + mapeamento para o caso concreto Nacom Goya
**Endereça**: RP-2 (Rafael), A6 (agente), C5 (agente)

---

## 1. Estado da Arte — Padrões Identificados

### PD-1 — Hierarquia de Memória em 3 Tiers (Letta/MemGPT)

**Fonte**: Letta docs + MemGPT paper (2023-2025); confirmado em [Agent Memory post](https://www.letta.com/blog/agent-memory)

| Tier | Nome | Onde Vive | Acesso |
|------|------|-----------|--------|
| Core Memory | Blocos editáveis (RAM) | **Dentro** do context window | Sempre presente; read/write via tool call |
| Recall Memory | Histórico de conversas (cache) | **Fora** do context; disco/DB | Search on demand; nunca injetado em volume |
| Archival Memory | Conhecimento indexado (storage frio) | Vector DB / Graph DB | Query tool call; retorna top-k |

**Aplicação ao nosso caso**: O hook atual `UserPromptSubmit` mistura os três tiers — injeta indiscriminadamente (volume), quando o padrão canônico diz:
- Core = apenas `preferences.xml`, `user.xml`, `user_rules` (o que hoje está em Tier 1)
- Recall = `recent_sessions` (hoje injetado em volume = correto *se* filtrado por intent)
- Archival = armadilhas, heurísticas, protocolos de domínio = RAG por intent, **não injeção em bloco**

---

### PD-2 — Modelo Bi-Temporal com Proveniência (Zep/Graphiti)

**Fonte**: Paper arXiv:2501.13956, [Zep temporal KG docs](https://www.getzep.com/ai-agents/temporal-knowledge-graph/)

Cada fato/memória carrega **4 timestamps**:

```
t'_created  = quando o sistema ingeriu o fato (audit trail)
t'_expired  = quando o sistema invalidou o fato
t_valid     = quando o fato foi verdadeiro no mundo
t_invalid   = quando o fato deixou de ser verdadeiro
```

**Proveniência**: episodic edges (ℰₑ) ligam cada fato semântico ao episódio-fonte. "Semantic artifacts can be traced to their sources for citation or quotation."

**Invalidação por contradição**: quando chega fato novo que contradiz o existente, o sistema define `t_invalid = t_valid do novo fato`. Não deleta — invalida. Isso resolve o problema de "memória alta confiança que se torna poisoning" (citado no Wire blog: "Stored facts decay... Persistent memory without an explicit freshness model becomes a slow source of context poisoning").

**Aplicação ao nosso caso**:
- O campo `meta.updated_at` + `user.xml confidence="alta" sessions="25"` é um pré-cursor do modelo bi-temporal, mas **incompleto**: não há `t_valid`/`t_invalid`, não há link `memory → session_id → transcript`.
- A memória sobre "fatura 161-9" não tem o `episode_source` que permitiria ao agente navegar até a sessão-origem para contexto completo.

---

### PD-3 — Retrieval por Intent (multi-signal, não volume)

**Fonte**: mem0.ai State of AI Agent Memory 2026; MemRL framework (Jan 2026); AWS AgentCore episodic memory; neo4j agent memory modeling

O padrão de mercado 2025-2026 usa **3 passes paralelos**:
1. **Semantic similarity** (cosine / embedding vector): captura intent via embedding da query do turno
2. **BM25 full-text**: captura keywords exatas (nomes de campo, IDs, entidades)
3. **Entity matching**: resolve entidades canônicas (ATACADAO → CNPJ raiz)

Os 3 scores são fundidos (weighted fusion) antes do corte top-k.

**Retrieval por intent (MemRL, Jan 2026)**:
> "MemRL retrieves relevant past experiences in two stages — a semantic filter using dense embeddings to compute similarity between current intent and stored intents, keeping top-k candidates by semantic relevance, and a Q-value ranking phase that re-ranks filtered candidates by higher utility associated with successful outcomes."

**Aplicação ao nosso caso**:
- O sistema atual **tem** o embedding engine (Voyage AI + pgvector) para retrieval semântico em `agent_memory_embeddings`.
- O que **falta** é usar esse embedding para **filtrar o que é injetado no hook** com base no intent do turno atual. Hoje a injeção segue regras de path/kind/tier, não intent semântico do turno.
- O hook `UserPromptSubmit` recebe o texto do 1º turno (a mensagem do usuário). Esse texto **já poderia ser usado como query de embedding** para filtrar quais memórias de domínio injetar.

---

### PD-4 — Episódico como Few-Shot (Amazon AgentCore + neo4j)

**Fonte**: [AWS AgentCore episodic memory](https://aws.amazon.com/blogs/machine-learning/build-agents-to-learn-from-experiences-using-amazon-bedrock-agentcore-episodic-memory/); [neo4j modeling](https://neo4j.com/blog/developer/modeling-agent-memory/)

> "Episodes provide agents with concrete examples of how similar problems were solved before, enabling agents to follow proven strategies."

Pattern neo4j:
```
similarity_search(user_query, question_embeddings)
→ traversal to Cypher query nodes  
→ return top-k (question, answer) pairs as few-shot
```

**Aplicação ao nosso caso** (RP-2 — caso fatura 161-9):
- A sessão de 05/06 (exclusão fatura 161-9) está em `agent_sessions` + `recent_sessions` no hook.
- O que Rafael quer: quando o agente tratar **qualquer** fatura CarVia, injetar a sessão 05/06 como **few-shot** (como esse problema foi resolvido).
- Implementação: no hook, ao detectar intent "fatura" via embedding ou keyword, injetar 1-2 `recent_sessions` relevantes em vez de (ou antes das) 5 sessões mais recentes.
- Modelo: `search_sessions(query="fatura carvia", top_k=2)` → seção `<episodic_few_shots>` com os resumos anotados.

---

### PD-5 — Metadados Mínimos de Proveniência e Frescor

**Fonte**: Anthropic Cookbook (platform.claude.com/cookbook/tool-use-context-engineering), Wire Blog Anthropic Managed Agents, SSGM framework arXiv:2603.11768

Schema mínimo recomendado pela literatura para um memory entry:

```json
{
  "content": "...",
  "source_session_id": "uuid-da-sessao-origem",
  "t_created": "ISO8601 quando ingested",
  "t_last_confirmed": "ISO8601 ultima confirmacao pelo usuario",
  "confidence": "alta|media|baixa",
  "confidence_score": 0.92,
  "domain": "carvia|odoo|expedicao|financeiro|infra",
  "kind": "heuristica|protocolo|correcao|preferencia|armadilha",
  "nivel": 5,
  "decay_model": "static|half_life_168h|contradiction_invalidation"
}
```

O Wire Blog Anthropic (April 2026) enfatiza 4 decisões críticas de design:
1. **Scope** (quem pode acessar)
2. **Freshness** (como lidar com dado stale)
3. **Conflict resolution** (quando entradas se contradizem)
4. **Trust/provenance** (entender de onde veio cada entrada)

**Aplicação ao nosso caso**:
- Campo `source_session_id` está **ausente** do schema atual (`AgentMemory` — checar models.py).
- `confidence` aparece em `user.xml` mas **não em outras memórias**.
- `t_last_confirmed` está **ausente** de todas as memórias — o agente (achado A6) identificou corretamente.
- `kind` e `nivel` existem no `meta` JSONB — bem alinhados com a literatura.

---

### PD-6 — KV-Cache + Injeção Estável (Manus, Jul 2025)

**Fonte**: Medium/DEV Community — "Context Engineering for AI Agents: Key Lessons from Manus" por Yichao Ji (Jul 2025)

6 princípios Manus (com relevância para o nosso hook):

1. **KV-Cache hit rate como métrica primária**: tokens cached custam 10x menos. "Even a single-token change at the start of the system prompt can invalidate the cache." → A injeção dinâmica do hook (que muda a cada turno) invalida o cache. Memos voláteis (como `stale_empresa=33`) **pioram** o cache hit rate.

2. **Contexto append-only**: nunca modificar o que já foi injetado — preserva cache. O padrão atual de reinjetar o hook a cada turno é correto (append, não modify), mas o conteúdo variável ainda invalida.

3. **Tool masking vs remoção**: não remover tools (quebra cache), usar logits masking. → Para skills: não mudar a lista de skills a cada turno.

4. **todo.md recitation**: injetar objetivos ao final do contexto (perto da mensagem do usuário) para combater "lost in the middle". → As `pendencias` deveriam ficar **no final** do hook, coladas à mensagem do usuário (alinhado com D3 do agente).

5. **Preservar erros no contexto**: stack traces e falhas ajudam o agente a não repetir erros. → `improvement_responses` no hook pode ser valioso, mas o conteúdo delas (código de 200+ chars) invalida o cache constantemente. Alternativa: injetar só o ID + título (stable), detalhe via tool on-demand.

6. **Compressão recuperável**: "Web page content can be dropped if the URL is preserved." → Padrão aplicável ao hook: injetar path da memória em vez do conteúdo completo, com tool `view_memories(path)` para recuperar on-demand.

---

### PD-7 — Decay de Confiança e Invalidação (literatura 2025-2026)

**Fonte**: SSGM framework arXiv:2603.11768; mem0.ai State of Memory 2026; Wire Blog

Dois modelos principais:

**A — Decay por tempo (Weibull distribution — Huang et al. 2025)**:
```
score = confidence × decay_factor(age, half_life)
# Ex: half_life_168h = meia-vida de 1 semana para memorias operacionais
# Memórias abaixo de threshold → tier frio automático
```

**B — Invalidação por contradição (Graphiti/Zep)**:
```
if new_fact contradicts existing_fact:
    existing_fact.t_invalid = new_fact.t_valid
    # Não deleta, invalida — histórico preservado
```

**Problema identificado (Wire Blog)**: "A highly-retrieved memory about a user's employer is accurate until they change jobs, at which point it becomes confidently wrong." → **High-retrieval + wrong = context poisoning**. Decay trata low-relevance; **staleness em high-relevance permanece unsolved** na maioria dos frameworks.

**Aplicação ao nosso caso**:
- O `stale_empresa count="33"` (33 memórias sem revisão há 60+ dias) é um proxy de staleness, mas está sendo injetado como aviso em **todo** boot operacional — o que é exatamente o anti-pattern que Rafael identificou (R-6).
- A flag `is_cold` já existe no `AgentMemory` — é o tier frio. O que falta é o **decay automático para tier frio** baseado em `updated_at + last_confirmed` quando o agente não interage com a memória.

---

### PD-8 — Separação Episódica vs. Semântica vs. Procedimental

**Fonte**: Survey "Memory in the Age of AI Agents" (arXiv:2512.13564); AWS AgentCore

| Tipo | O que armazena | Recuperação | Uso no Agente |
|------|---------------|-------------|---------------|
| **Episódico** | Eventos específicos com contexto (quando, onde, quem, o que) | Por intent da query atual; top-k por similaridade | Few-shot de como resolver situações similares |
| **Semântico** | Fatos, relacionamentos, regras gerais | Busca vetorial + keyword; retorna entidades | Gotchas, heurísticas, configurações fixas |
| **Procedimental** | Workflows, passos, how-to | Por tipo de tarefa | Skills, subagente routing, confirmação de escrita |
| **Working Memory** | Estado do turno atual | Sempre presente (core) | Pendências, context atual, user_rules |

**Cinco propriedades de memória episódica (2025 position paper)**:
1. Long-term storage
2. Explicit reasoning
3. Single-shot learning (um episódio basta para aprender)
4. Instance-specific memories (não generalizadas)
5. Contextual memories (who, when, where, why)

**Aplicação ao nosso caso**: O sistema atual mistura os tipos:
- `user_rules` (procedimental/semântico) + `preferences` (semântico) estão em Tier 1 → correto
- `recent_sessions` (episódico) está injetado em volume → deveria ser RAG por intent
- `armadilhas` e `heuristicas` (semântico) estão injetadas por domínio → parcialmente correto, mas ainda em volume dentro do domínio

---

## 2. Diagnóstico do Sistema Atual (mapeamento evidence-based)

### D-1 — Injeção em Volume, não por Intent

**Evidência**: `contexto_boot.md:1903-1981` — 12 memórias de empresa injetadas no hook, incluindo:
- `ibge-float-em-planilha` (27 linhas, altamente específica para importação de tabela de frete)
- `tmpdir-divergente-entre-agente-e-web-server` (improvement dialogue determinístico)
- `tool-sql-reescreve-queries-complexas-com-ctes` (specific to SQL tool usage)

Na sessão capturada, Rafael perguntou sobre o **contexto de boot** (arquitetura do agente). Nenhuma das 3 memórias acima é relevante para essa intent. Isso é o C5 do agente: "injeta a maioria, não RAG por intent".

**Causa raiz** (`memory_injection.py:682-704`): armadilhas são filtradas por `domínio` do usuário (`_DOMAIN_PATH_SEGMENTS`) e ordenadas por `effective_count.desc()` — não pelo intent da mensagem atual. O domínio é calculado UMA vez por sessão (`_compute_user_domain`), não por turno.

### D-2 — Ausência de `source_session_id` na Memória

**Evidência**: `memory_mcp_tool.py` — a função `save_memory` salva `path`, `content`, `meta`, `kind`, `nivel`, mas **não há campo `source_session_id`** no schema. A proveniência até a sessão de origem não está registrada.

`models.py` — `AgentMemory` tem `user_id`, `path`, `content`, `meta` (JSONB), `created_at`, `updated_at`, `correction_count`, `priority`, `is_cold`, `category`, `escopo`, `effective_count`. Não há `source_session_id` como coluna dedicada.

O `meta` JSONB poderia conter `source_session_id`, mas o código de save não o popula automaticamente.

### D-3 — Sem `last_confirmed` nem `confidence` nas Memórias de Domínio

**Evidência**: O `user.xml` tem `confidence="alta" sessions="25" updated_at="08/06/2026"` — mas isso é atributo manual em XML. O modelo geral de memórias de domínio (armadilhas, heurísticas) não tem esses campos de forma sistemática. O meta JSONB tem `nivel` e `criterios`, mas não `confidence` nem `last_confirmed`.

### D-4 — improvement_responses e stale_empresa Invalidam Cache

**Evidência**: `contexto_boot.md:1996-1997`:
```xml
<stale_empresa count="33">Memorias empresa maduras sem revisao ha 60+ dias.</stale_empresa>
<improvement_responses count="2" note="...">
  <response key="IMP-2026-06-05-001" ...>Batch lançar comprovantes duplica payment...
  (200+ chars de código)
  </response>
</improvement_responses>
```

Ambos mudam a cada sessão (contagem muda, respostas mudam). Isso invalida o KV-cache do hook a cada turno, multiplicando o custo de tokens. O princípio Manus PD-6 é claro: conteúdo variável no início invalida tudo abaixo.

### D-5 — recent_sessions sem Filtragem por Intent

**Evidência**: `contexto_boot.md:1982-1993` — 5 sessões recentes injetadas em volume por data, não por relevância para o turno atual. A sessão de 05/06 (fatura 161-9) é episódica valiosa para turnos sobre fatura CarVia, mas **ruído** para um turno sobre arquitetura do agente.

### D-6 — Ordenação do Hook Não Segue "Recência de Atenção"

**Evidência**: `contexto_boot.md:1817-2083` — a ordem atual do hook é:
1. `session_context` (data/usuário) — correto
2. `user_rules` (mandatory) — correto (Tier 1)
3. `user_memories` (preferences, user_expertise, user.xml, memórias empresa) — Tier 1.x
4. `recent_sessions` — Tier 2
5. `pendencias_acumuladas` — deveria estar no final
6. `intersession_briefing` (stale_empresa + improvement_responses) — ruído, não operacional
7. `operational_directives` — importante, mas sepultado no meio
8. `routing_context` (advisory) — advisory
9. `debug_mode_context` + `sql_admin_context` — contextuais
10. `skill_hints` + `world_model` — advisory

O princípio Manus PD-6.4 (todo.md recitation) e o achado D3 do agente apontam que **`pendencias` deveria ser o último bloco antes da mensagem do usuário**, para máxima atenção. Hoje está sepultada no meio dos 34KB.

---

## 3. Padrões Recomendados para o Caso Nacom Goya

### PR-1 — Injeção por Intent do Turno (resposta ao RP-2)

**Mecanismo proposto**:
```python
# No hook UserPromptSubmit, antes de construir o contexto de memórias:
user_message_text = hook_input.get("user_message", "")

# Etapa 1: classificação de intent (zero-LLM, heurística de keywords)
intent = classify_intent(user_message_text)
# Categorias: "fatura|estoque|expedicao|odoo_escrita|consulta|arquitetura|financeiro|nenhum"

# Etapa 2: filtrar memórias de domínio por intent
# (em vez de injetar todas as armadilhas do domínio do usuário)
relevant_memories = semantic_search_memories(
    query=user_message_text,
    user_id=user_id,
    top_k=3,
    kinds=["armadilha", "protocolo", "heuristica"],
)

# Etapa 3: injetar few-shot episódico se intent específico detectado
if intent in ("fatura", "carvia"):
    few_shot_sessions = search_sessions(
        query="fatura carvia resolucao",
        user_id=user_id,
        top_k=2,
    )
```

**Custo**: O embedding da mensagem do usuário pode ser gerado em paralelo com a construção do hook (~100ms Voyage AI). O sistema já tem toda a infraestrutura (`agent_memory_embeddings`, `EmbeddingService`, `semantic_search_sessions`).

**Risco**: No 1º turno da sessão, o agente não sabe ainda o intent completo. Mitigação: classificação por keywords (zero-LLM) como Tier 0, embedding como Tier 1.

---

### PR-2 — Proveniência Navegável (resposta a RP-2)

**Schema proposto** (adição ao `meta` JSONB de `AgentMemory`):

```json
{
  "source_session_id": "uuid-da-sessao-de-origem",
  "source_session_date": "2026-06-05",
  "source_session_title": "Exclusão fatura CarVia 161-9",
  "t_last_confirmed": "2026-06-05T15:30:00",
  "confidence": "alta",
  "origin_type": "correction|learning|inference|user_explicit"
}
```

**Como navegar**: o agente já tem `mcp__sessions__search_sessions` e `mcp__sessions__list_recent_sessions`. Com `source_session_id` no meta, o agente pode:
```
1. Ver memória sobre "fatura carvia 161-9 — assume emitida pela CarVia"
2. Verificar meta.source_session_id = "abc-def-..."
3. Chamar search_sessions(session_id="abc-def-...") → transcript completo
4. Avaliar se a memória ainda é válida no contexto atual
```

**Implementação**: em `memory_mcp_tool.py`, na função `save_memory`, adicionar ao `meta`:
```python
# No contexto do agente, a session_id atual está em permissions.get_current_session_id()
from app.agente.config.permissions import get_current_session_id
meta["source_session_id"] = get_current_session_id()
```

**Custo**: zero (apenas armazenar o UUID da sessão atual no momento do save). Não quebra schema existente (JSONB é flexível).

---

### PR-3 — Metadados de Frescor e Confiança (resposta a A6)

**Schema mínimo** baseado na literatura:

```
Meta JSONB de AgentMemory (campos a adicionar):
├── last_confirmed: ISO8601 — quando usuario ou sistema confirmou explicitamente
├── confidence: "alta|media|baixa" — graduado pelo tipo de origem
├── origin_type: "user_correction|agent_learning|inference|bootstrap"
├── source_session_id: UUID da sessão onde foi criada/confirmada
└── invalidated_by: path ou session_id do fato que a contradisse (opcional)
```

**Regras de decay propostas**:
- `kind=correcao, origin_type=user_correction` → nunca decai automaticamente (PERMANENT)
- `kind=heuristica, nivel>=5` → decai para tier frio após 90 dias sem `last_confirmed`
- `kind=protocolo` → decai para tier frio após 60 dias
- `kind=armadilha` → nunca decai (armadilhas de sistema são permanentes até invalidação explícita)
- `kind=preferencia` → decai após 180 dias sem `last_confirmed`

**Invalidação por contradição**: quando o usuário corrige uma memória, o save_memory deve:
1. Criar a nova memória com `origin_type=user_correction`
2. Marcar a memória antiga com `meta.invalidated_by = nova_path` e `is_cold = True`

---

### PR-4 — Memória Episódica como Few-Shot por Tópico (resposta a RP-2 + A4)

**Pattern proposto** (baseado em neo4j modeling + AWS AgentCore):

```xml
<!-- Injetado condicionalmente no hook quando intent detectado -->
<episodic_few_shots>
  <!-- Sessão mais relevante para o tópico atual -->
  <episode session_id="abc-def" date="05/06/2026" intent="fatura_carvia">
    <resumo>Exclusão e substituição de fatura CarVia 161-9 (BIOMOTORS, R$1.250). 
    Sequência: hard-delete via AdminService contornando bug FK, CTes 235/237 
    desvinculados antes.</resumo>
    <outcome>RESOLVIDO — confirmado pelo usuário após hard-delete bem-sucedido.</outcome>
    <session_url>/agente/sessoes/abc-def</session_url>
  </episode>
</episodic_few_shots>
```

**Critério de injeção**: somente quando `semantic_similarity(turno_atual, episode_summary) > 0.75` — evitar ruído.

**Distinção de `recent_sessions`**: `recent_sessions` é cronológico (5 últimas). `episodic_few_shots` é semântico (top-k por relevância para o intent). Podem coexistir, com `recent_sessions` mais compacto (apenas título + data) quando `episodic_few_shots` já injeta o contexto rico.

---

### PR-5 — Ordenação do Hook para Máxima Atenção

**Baseado em**: princípio Manus (recitação ao final), achado D3 do agente, lost-in-the-middle literature

**Ordem proposta do hook** (do mais estável ao mais volátil + "aja-agora" no final):

```
1. session_context           ← identificação do turno (estável)
2. user_rules                ← mandatory (sempre-primeiro por prioridade)
3. user_memories             ← core memory: preferences, expertise, user.xml
4. [NOVO] episodic_few_shots ← few-shot condicional por intent (se relevante)
5. operational_directives    ← regras críticas de operação (sempre)
6. [CONDICIONAL] debug/sql   ← apenas se admin + debug_mode
7. routing_context           ← advisory (pode ser removido se eval confirmar)
8. recent_sessions           ← resumo compacto (últimas 3, não 5)
9. intersession_briefing     ← REFORMULADO: apenas pending confirmations (ver abaixo)
10. pendencias_acumuladas    ← "aja-agora" → ÚLTIMO bloco antes da msg do usuário
```

**Sobre o `intersession_briefing`**:
- `stale_empresa count=33` → remover do hook operacional; colocar em view do `gerindo-agente` (C3 do agente — free win)
- `improvement_responses` → injetar apenas o **título + chave** (2 linhas por item), não o corpo completo (que invalida cache). O agente pode chamar `view_memories(path)` se quiser o detalhe.

---

## 4. Gaps Detectados (o que a pesquisa NÃO encontrou)

1. **Nenhum framework externo** (Letta, LangMem, Zep) resolve explicitamente o caso de **intent classification no primeiro turno com memórias já prontas** — todos assumem que o RAG acontece durante a conversação, não no boot.

2. **Confiança em memórias long-tail** (uma única correção feita há meses, sem confirmação posterior) — a literatura identifica o problema (Wire Blog: "confidently wrong") mas não prescreve solução determinística além de TTL.

3. **Verificação não foi feita em prod**: todos os diagnósticos acima são baseados no dump estático `contexto_boot.md`. O comportamento real do `memory_injection.py` em prod (quais memórias são ou não injetadas, qual o cache hit rate efetivo) requer medição direta.

4. **MemOS** (novo framework 2026 com metadata-gated retrieval + `sensitivity_label` + `version_chain_pointers`) — citado na pesquisa mas não foi possível obter detalhes suficientes para avaliar aplicabilidade.

---

## 5. Resposta Direta ao RP-2

**RP-2 diz**: "Quando for tratar de fatura, o agente precisa entender as REGRAS (que podem vir das memórias) com alguns few-shots (a fatura 161-9 se aplicaria como few-shot). Importante: saber DE QUAL SESSÃO veio a memória."

**Resposta consolidada**:

### (a) Filtrar memórias por intent do turno

O sistema tem embedding engine (Voyage AI) e pgvector operacionais. O que falta é usar o **texto da mensagem atual** como query de embedding para filtrar quais memórias de domínio são injetadas. A implementação seria em `memory_injection.py`, na função principal de injeção, antes de construir o bloco de armadilhas/heurísticas. Custo: ~100ms de latência adicional por turno (já tolerado para o embedding de save). Alternativa zero-cost: classificação por keywords (regex sobre o texto) como Tier 0 antes do embedding.

### (b) Proveniência navegável (memória → session_id → transcript via tools)

Adicionar `source_session_id` ao `meta` JSONB no momento do `save_memory`. O campo deve ser populado automaticamente com `get_current_session_id()` (já disponível via `permissions.py`). O agente então pode chamar `search_sessions(session_id=...)` para ver o transcript completo — a ferramenta já existe (`session_search_tool.py`). Não é necessária nenhuma nova infraestrutura, apenas a adição do campo no save.

### (c) Memória episódica como few-shot por tópico (caso fatura 161-9)

Injetar um bloco `<episodic_few_shots>` no hook quando o intent do turno for semanticamente similar a episódios conhecidos (threshold sugerido: cosine similarity > 0.75). O few-shot contém o resumo da sessão + outcome + link navegável. Isso responde ao A4 do agente (few-shot nas tarefas de alta frequência) e ao RP-2 (161-9 como exemplo contextual, não memória plana).

### (d) Metadados mínimos recomendados (last_confirmed, confidence, origem)

```json
{
  "source_session_id": "uuid",       // ← proveniência navegável
  "t_last_confirmed": "ISO8601",     // ← quando foi confirmada última vez
  "confidence": "alta|media|baixa", // ← nível de confiança
  "origin_type": "user_correction|agent_learning|inference",
  "invalidated_by": null             // ← se contradita, path do substituto
}
```

`last_confirmed` deve ser atualizado quando: (1) usuário explicitamente confirma que a memória está correta; (2) o agente usa a memória com sucesso (implicit confirmation); (3) o agente registra nova memória que contradiz a anterior (→ invalida a antiga).

`confidence` deve ser: `alta` para correções explícitas do usuário (origin_type=user_correction), `media` para aprendizados do agente, `baixa` para inferências automáticas.

---

## 6. Fontes Consultadas

- Anthropic Cookbook — Context Engineering Tools: https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools
- Anthropic Managed Agents Memory (Wire Blog): https://usewire.io/blog/anthropic-managed-agents-memory-context-engineering/
- Deepwiki Anthropic Cookbook Memory Systems: https://deepwiki.com/anthropics/anthropic-cookbook/5.2-memory-systems-for-agents
- Letta Agent Memory: https://www.letta.com/blog/agent-memory
- MemGPT/Letta: https://vectorize.io/articles/mem0-vs-letta
- Zep Temporal Knowledge Graph paper: https://arxiv.org/html/2501.13956v1
- Zep Temporal KG docs: https://www.getzep.com/ai-agents/temporal-knowledge-graph/
- Graphiti on Neo4j: https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/
- Neo4j Agent Memory Modeling: https://neo4j.com/blog/developer/modeling-agent-memory/
- mem0.ai State of AI Agent Memory 2026: https://mem0.ai/blog/state-of-ai-agent-memory-2026
- Manus Context Engineering: https://medium.com/@contextspace/context-engineering-for-ai-agents-key-lessons-from-manus-319ab68e4370
- LangMem SDK: https://www.digitalocean.com/community/tutorials/langmem-sdk-agent-long-term-memory
- AWS AgentCore Episodic Memory: https://aws.amazon.com/blogs/machine-learning/build-agents-to-learn-from-experiences-using-amazon-bedrock-agentcore-episodic-memory/
- SSGM Framework (arXiv:2603.11768): https://arxiv.org/html/2603.11768v1
- AI Agent Memory Types (Atlan): https://atlan.com/know/types-of-ai-agent-memory/
- MemRL Self-Evolving Agents: https://effloow.com/articles/memrl-self-evolving-agents-episodic-memory-rl-guide-2026
- Memory in the Age of AI Agents (arXiv:2512.13564): https://arxiv.org/pdf/2512.13564
- Digital Applied AI Agent Memory 2026: https://www.digitalapplied.com/blog/ai-agent-memory-vector-graph-episodic-2026

---

*Fim do findings C3. Achados PD-1..PD-8 são padrões externos. PR-1..PR-5 são recomendações de aplicação. D-1..D-6 são diagnósticos com evidência exata do código.*

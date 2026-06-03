<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Sistema de Playbooks — Aprendizado Procedimental do Agente

> **Papel:** Sistema de Playbooks — Aprendizado Procedimental do Agente.

## Indice

- [1. Contexto e diagnóstico](#1-contexto-e-diagnóstico)
  - [O que temos hoje (memórias declarativas)](#o-que-temos-hoje-memórias-declarativas)
  - [O que falta (memória procedimental — playbooks)](#o-que-falta-memória-procedimental-playbooks)
- [2. Princípios de design](#2-princípios-de-design)
  - [P1 — Validação humana é o trigger primário, não decisão do modelo](#p1-validação-humana-é-o-trigger-primário-não-decisão-do-modelo)
  - [P2 — Capturar a sequência real, não a intenção declarada](#p2-capturar-a-sequência-real-não-a-intenção-declarada)
  - [P3 — Replicar passos, não conceitos](#p3-replicar-passos-não-conceitos)
  - [P4 — Safety acima de eficiência](#p4-safety-acima-de-eficiência)
  - [P5 — Aprendizado contínuo, não estático](#p5-aprendizado-contínuo-não-estático)
- [3. Estrutura do playbook](#3-estrutura-do-playbook)
  - [3.1 Path e identidade](#31-path-e-identidade)
  - [3.2 Conteúdo XML](#32-conteúdo-xml)
- [4. Decisão chave — nomenclatura (slug vs LLM-nomeado)](#4-decisão-chave-nomenclatura-slug-vs-llm-nomeado)
  - [Comparação](#comparação)
  - [Recomendação: Híbrido](#recomendação-híbrido)
  - [4.5 Domínio — propriedade derivada, não hardcoded no path](#45-domínio-propriedade-derivada-não-hardcoded-no-path)
- [5. Decisão chave — trigger pattern](#5-decisão-chave-trigger-pattern)
  - [Opções](#opções)
  - [Algoritmo combinado](#algoritmo-combinado)
- [5.5 Bootstrap retroativo via `claude_session_store`](#55-bootstrap-retroativo-via-claude_session_store)
  - [Correção da hipótese inicial (S3 archive)](#correção-da-hipótese-inicial-s3-archive)
  - [O que está disponível em `claude_session_store`](#o-que-está-disponível-em-claude_session_store)
  - [Universo viável para bootstrap](#universo-viável-para-bootstrap)
  - [Pipeline de bootstrap (one-time)](#pipeline-de-bootstrap-one-time)
  - [Custo estimado de bootstrap (revisado)](#custo-estimado-de-bootstrap-revisado)
  - [Justificativa estratégica (mantida)](#justificativa-estratégica-mantida)
  - [Gotcha — IDs de sessão](#gotcha-ids-de-sessão)
- [6. Fluxo de captura](#6-fluxo-de-captura)
  - [6.1 Triggers de detecção (Hook `Stop`)](#61-triggers-de-detecção-hook-stop)
  - [6.2 Pipeline pos-sessão](#62-pipeline-pos-sessão)
- [7. Fluxo de aplicação](#7-fluxo-de-aplicação)
  - [7.1 No `UserPromptSubmitHook`](#71-no-userpromptsubmithook)
  - [7.2 Frame de injeção no contexto](#72-frame-de-injeção-no-contexto)
  - [7.3 Decisão do modelo](#73-decisão-do-modelo)
- [8. Ciclo de vida do playbook](#8-ciclo-de-vida-do-playbook)
- [9. Métricas (dashboard admin)](#9-métricas-dashboard-admin)
- [10. Não-objetivos v1 (deixar para v2)](#10-não-objetivos-v1-deixar-para-v2)
- [11. Riscos e mitigações](#11-riscos-e-mitigações)
- [12. Plano de implementação faseado](#12-plano-de-implementação-faseado)
  - [Fase 1 — Foundation (3-4 dias)](#fase-1-foundation-3-4-dias)
  - [Fase 2 — Bootstrap retroativo via `claude_session_store` (1-2 dias)](#fase-2-bootstrap-retroativo-via-claude_session_store-1-2-dias)
  - [Fase 3 — Captura ao vivo (3-5 dias)](#fase-3-captura-ao-vivo-3-5-dias)
  - [Fase 4 — Aplicação (2-3 dias)](#fase-4-aplicação-2-3-dias)
  - [Fase 5 — Métricas + Deprecation (2 dias)](#fase-5-métricas-deprecation-2-dias)
  - [Fase 6 — Frontmatter migration (paralela, ongoing)](#fase-6-frontmatter-migration-paralela-ongoing)
  - [Fase 7 — Refinamento (continuo)](#fase-7-refinamento-continuo)
- [13. Decisões em aberto (para discussão pos-aprovação)](#13-decisões-em-aberto-para-discussão-pos-aprovação)
- [14. Referências](#14-referências)
- [Contexto](#contexto)

**Data**: 2026-05-11
**Status**: Spec — aguardando aprovação para implementação
**Autores**: Rafael (visão) + Claude Opus 4.7 (estruturação)
**Motivação primária**: aderência baixa do agente (< 10 usuários ativos) decorrente de usar o agente como "terceirizador" de tarefas já dominadas, sem que o sistema acumule conhecimento institucional de processos validados.

---

## 1. Contexto e diagnóstico

### O que temos hoje (memórias declarativas)

| Tipo | O que captura | Aplicação | Trigger de save |
|------|---------------|-----------|-----------------|
| `/heuristicas/` | "polling expira mas invoice confirma depois" | Aviso passivo | Modelo decide (R0) |
| `/armadilhas/` | "OAuth scope nova exige reautorização" | Aviso passivo | Modelo decide (R0) |
| `/termos/` | "VCD = pedido CD venda" | Vocabulário | Modelo decide (R0) |
| `/perfis/`, `/usuarios/` | "Gabriella é telegráfica" | Estilo | Modelo decide (R0) |
| `/learned/expertise_*` | "user conhece Render" | (Era órfão, fixado 2026-05-11) | Sonnet pos-sessão |
| `/corrections/` | "confirmar item antes de operar tabela" | Comportamento | Sonnet pos-sessão |
| `/preferences.xml` | "preferência por XLSX em vez de CSV" | Formato | Sonnet pos-sessão |

**Padrão comum**: tudo é **conhecimento declarativo** — fatos sobre o mundo, sobre o usuário, sobre armadilhas. O modelo precisa, a cada nova sessão, **interpretar** essas memórias e **decidir** como aplicá-las em um caso concreto.

### O que falta (memória procedimental — playbooks)

Citando o requisito do usuário:

> "O sistema de memórias deveria ser um atributo de aprendizagem real do agente, para que ele descubra e pegue nuances de processos que os usuarios falham e o sistema possa estruturá-lo e guardá-lo, mesmo que o usuario não tenha entendido o processo, mas tenha validado o resultado, possa ser repetido futuramente com a mesma consistencia."

**Tradução técnica**:

- **Trigger atual**: o modelo decide salvar (e frequentemente esquece — REC-2026-04-27-001)
- **Trigger desejado**: o **usuário valida o resultado** → o sistema extrai a **sequência exata** de tools/skills/parâmetros que produziu o resultado → salva como playbook reproduzível
- **Aplicação atual**: modelo lê memórias declarativas, decide caminho → variabilidade alta
- **Aplicação desejada**: prompt similar → playbook injetado → modelo replica passos validados → variabilidade baixa

**Diferença operacional para o usuário**: hoje o Marcus reconcilia transferências internas em 12 sessões caras de descoberta. Com playbooks, o próximo usuário consulta em 1 turno e o agente roda o playbook validado — capturando o que o Marcus aprendeu sem que ele precise documentar.

---

## 2. Princípios de design

### P1 — Validação humana é o trigger primário, não decisão do modelo

Playbook só é criado quando há sinal claro de validação positiva (humano confirmou resultado). Isso elimina a falha sistemática de R0 (modelo esquecendo de salvar) e garante que apenas processos com aprovação humana viram playbook.

### P2 — Capturar a sequência real, não a intenção declarada

Não pedir ao modelo "descreva o que fez". Capturar do log de execução: tools chamadas, parâmetros usados, outputs. Sonnet pos-sessão estrutura o XML, mas não inventa passos — só preserva o que aconteceu.

### P3 — Replicar passos, não conceitos

Quando o playbook é aplicado, o modelo recebe instrução explícita: "execute estes passos nesta ordem". Não "considere fazer X". Isso reduz variabilidade probabilística no caminho crítico.

### P4 — Safety acima de eficiência

Playbooks **respeitam R3** (confirmação obrigatória antes de operação irreversível). Um playbook de "criar separação" continua exigindo confirmação humana — o playbook acelera a **descoberta** dos parâmetros corretos, não bypassa o gate de segurança.

### P5 — Aprendizado contínuo, não estático

Cada execução de playbook incrementa `usage_count`. Cada falha (sinalizada via correção pós-execução) incrementa `failure_count`. Após threshold (`failure_count >= 3` ou `failure_rate > 30%`), playbook é marcado como `deprecated` e parado de injetar.

---

## 3. Estrutura do playbook

### 3.1 Path e identidade

```
/memories/empresa/playbooks/{slug}.xml
```

- `slug` = identificador determinístico do título (ver §4 sobre nomenclatura)
- **Sem segmento `{dominio}` no path** (decisão 2026-05-11 — ver §4.5 sobre domínios derivados em runtime, não hardcoded no path)

### 3.2 Conteúdo XML

```xml
<playbook id="financeiro_reconciliacao_transferencias_internas_marcus" status="active">
  <title>Reconciliação de transferências internas entre journals NACOM GOYA</title>

  <trigger>
    <keywords>reconcilia, transferencia, interna, NACOM GOYA, journal</keywords>
    <embedding_seed>conciliar transferencias internas entre journals NACOM GOYA / VORTX / AGIS</embedding_seed>
    <required_params>
      <param name="periodo" type="data_range" optional="false"/>
      <param name="journal_origem" type="enum" optional="true"/>
    </required_params>
  </trigger>

  <steps>
    <step n="1" tool="Skill:gerando-baseline-conciliacao">
      <args>{"data_inicio": "{periodo.inicio}", "data_fim": "{periodo.fim}"}</args>
      <expected>Excel com 4 abas (Pendentes Mes x Journal, Pendentes, Conciliacoes, Resumo)</expected>
    </step>
    <step n="2" tool="Skill:conciliando-transferencias-internas">
      <args>{"data_referencia": "{periodo.fim}"}</args>
      <expected>Lista de candidatos com is_internal_transfer ja flaggado</expected>
    </step>
    <step n="3" tool="ASK_USER" gate="R3">
      <prompt>Confirmar aplicar conciliacao para os N pares listados?</prompt>
    </step>
    <step n="4" tool="Skill:executando-odoo-financeiro" conditional="user_aprovou">
      <args>{"action": "reconcile_transfer", "pairs": "{step_2.output.pairs}"}</args>
      <expected>account.bank.statement.line.is_reconciled = True para todas as N linhas</expected>
    </step>
  </steps>

  <validations>
    <validation source="marcus_lima" date="2026-04-15" session_id="dc6af5f0..." outcome="success"/>
    <validation source="marcus_lima" date="2026-04-22" session_id="..." outcome="success"/>
  </validations>

  <metrics>
    <usage_count>2</usage_count>
    <success_count>2</success_count>
    <failure_count>0</failure_count>
    <avg_cost_usd>1.25</avg_cost_usd>
    <avg_duration_sec>45</avg_duration_sec>
  </metrics>

  <provenance>
    <captured_at>2026-04-15T14:32:00</captured_at>
    <captured_from_session>dc6af5f0-...</captured_from_session>
    <validation_signal>user_message_after: "perfeito, era exatamente isso"</validation_signal>
  </provenance>
</playbook>
```

---

## 4. Decisão chave — nomenclatura (slug vs LLM-nomeado)

A pergunta foi: *"esses 'slugs' e o 'trigger' são a melhor abordagem, ou o agente deveria também pensar sobre o nome?"*

### Comparação

| Abordagem | Custo | Latência | Qualidade nome | Idempotência | Risco |
|-----------|-------|----------|----------------|--------------|-------|
| **Slug puro determinístico** (do `descricao[:60]`) | $0 | 0ms | Baixa (truncado, sem contexto) | Alta | Colisões em sinônimos ("reconciliação" vs "conciliação") |
| **LLM puro** (Sonnet escolhe nome) | ~$0.0005 | ~200ms | Alta | Baixa (varia por chamada) | Nome diferente para mesmo processo |
| **Híbrido** (LLM gera title + slug determinístico do title) | ~$0.0005 | ~200ms | Alta | Alta | Mitigado |

### Recomendação: Híbrido

1. **Sonnet pos-sessão** propõe `title` legível (ex: "Reconciliação de transferências internas entre journals NACOM GOYA")
2. **Slugify determinístico** gera path: `reconciliacao-de-transferencias-internas-entre-journals-nacom-goya`
3. **Dedup pre-save** via busca semântica sobre `embedding_seed` (threshold 0.85) — se já existe playbook com seed similar, **não cria novo** — incrementa `validations` do existente
4. **Title é editável** sem renomear path (preserva idempotência) — operador pode melhorar título depois sem quebrar referências

**Por que isso resolve a dúvida**:
- Slug determinístico → garante que mesma sequência sempre vai pro mesmo path (idempotente)
- LLM gera title → nome legível e contextual
- Dedup semântico → evita variações ("reconciliar" vs "conciliar") criando playbooks duplicados

---

### 4.5 Domínio — propriedade derivada, não hardcoded no path

A pergunta original do usuário: *"essas listas hardcoded de dominio são problema pra manter atualizada, o agente não é capaz de deterministicamente categoriza-las e garantir que não haja ambiguidade através de um 'criterizador' que torne o dominio o mais deterministico possivel sem hardcoded?"*

**Diagnóstico**: `tool_skill_mapper.py` (~338 linhas) hoje tem 3 dicts hardcoded (`TOOL_TO_CATEGORY`, `SKILL_TO_CATEGORY`, `CATEGORY_TO_DOMAIN`). Toda nova skill exige editar 3 lugares, e gera inconsistências (ex.: `gerando-baseline-conciliacao` cai em domínio `Financeiro` enquanto outras skills Odoo caem em `Odoo`).

**Substituir hardcoded por derivação determinística em 3 camadas (fallback chain)**:

#### Camada 1 — Mapper canônico de tools (mantido, mas elas mudam menos que playbooks)

`tool_skill_mapper.py` continua sendo source of truth, mas só pra **mapping tool → domínio**. Playbooks NÃO repetem essa info — derivam.

```python
playbook.domain_inferred = mode([
    map_tool_to_domain(t) for t in playbook.tools_used
])
```

Vantagem: mover uma skill de `Logistica → Financeiro` no mapper atualiza automaticamente todos os playbooks que a usam. Sem rewrite manual.

#### Camada 2 — Frontmatter da skill (declarativo na fonte)

Padrão novo proposto: cada `.claude/skills/{nome}/SKILL.md` declara seu domínio no frontmatter:

```yaml
---
name: conciliando-transferencias-internas
description: ...
domain: financeiro          # << NOVO — fonte da verdade do domínio da skill
tags: [odoo, reconciliacao] # << opcional — facets adicionais
---
```

`tool_skill_mapper.py` (ou novo `domain_resolver.py`) lê os frontmatters e popula o cache. Adicionar skill nova: editar APENAS o frontmatter — zero edição de mapper.

#### Camada 3 — Auto-clusterização emergente (para tools sem mapping nem frontmatter)

Quando uma tool/skill aparece num playbook **sem** mapping nem frontmatter (caso edge: tool externa, skill experimental):

1. Playbook fica com `domain_inferred = "indefinido"`
2. Dashboard admin mostra: *"N playbooks com tools `[X, Y, Z]` estão em 'indefinido'. Estes parecem formar cluster semântico (embedding similarity > 0.75). Nomear como domínio novo?"*
3. Admin responde 1 vez → mapper aprende → re-clusteriza retroativamente

#### O "criterizador" determinístico

A combinação acima É o criterizador: 100% determinística sem chamar LLM, exceto na sugestão de clusters emergentes (que é proposta, não decisão). Ambiguidade controlada via:

- **Tie-breaker** quando `mode()` tem empate: usar a tool com maior `usage_count` no playbook (peso por importância)
- **Override manual**: admin pode marcar `domain_override` no playbook (raro, mas disponível)

#### Migração do código atual

`tool_skill_mapper.py` atual permanece como fallback (não é removido em v1). Ao longo do tempo:
- Skills ganham `domain:` no frontmatter (uma onda de PRs)
- Mapper fica sendo apenas para **MCP tools built-in** (`Bash`, `Read`, `Glob`, etc.) que não têm SKILL.md
- Drift entre mapper e frontmatter é detectado por test automatizado (CI)

---

## 5. Decisão chave — trigger pattern

A pergunta implícita: "como o sistema sabe que um prompt novo bate com um playbook existente?"

### Opções

| Abordagem | Precisão | Recall | Custo |
|-----------|----------|--------|-------|
| Só keywords (regex) | Alta | Baixa (frase reformulada falha) | 0 |
| Só embedding (semantic match) | Média | Alta (pega sinônimos) | ~50ms + $0.0001 |
| Só required_params (estrutural) | Alta | Baixa (exige menção explícita) | 0 |
| **Combinado (recomendado)** | Alta | Alta | ~50ms + $0.0001 |

### Algoritmo combinado

```
match_score = (
    0.40 * keyword_overlap(prompt, trigger.keywords) +
    0.45 * cosine_similarity(embed(prompt), trigger.embedding_seed) +
    0.15 * params_extractable(prompt, trigger.required_params)
)

if match_score >= 0.70: inject playbook
elif match_score >= 0.50: suggest playbook (ask user)
else: ignore
```

**Por que combinado é melhor**:
- Keywords filtram cedo (fast) e evitam falsos positivos semânticos genéricos
- Embedding cobre reformulações ("conciliar" ≈ "reconciliar" ≈ "fazer match")
- Params estruturais valida que prompt tem ao menos o input mínimo ("data" para um playbook que precisa de período)

---

## 5.5 Bootstrap retroativo via `claude_session_store`

**Descoberta crítica (2026-05-11)**: a fonte real do transcript SDK completo de TODAS as sessões está em `claude_session_store` (PostgresSessionStore — Fase B cutover documentada em `app/agente/CLAUDE.md`).

### Correção da hipótese inicial (S3 archive)

A hipótese original deste spec era usar `agent-archive/{YYYY-MM}/{session_id}.tar.gz` (S3) como fonte. **Análise empírica em 2026-05-11 mostrou**:

- Apenas **8 de 541 sessões** (1.48%) têm `s3_archive` registrado em `AgentSession.data`
- Motivo: `session_archive.py:137` arquiva **só** quando há `subagents/*.jsonl` em `/tmp/.claude/projects/*/session/subagents/` — ou seja, **só sessões que invocaram a Task tool com subagente**
- Sessões diretas (a maioria) não passam pelo archive

S3 archive permanece útil para forensics de subagentes, mas **não cobre o caso geral de playbooks**.

### O que está disponível em `claude_session_store`

Schema:
```
project_key TEXT     -- '-opt-render-project-src' no Render
session_id  TEXT     -- bate com agent_sessions.session_id (SDK ID)
subpath     TEXT
seq         BIGINT   -- ordem cronológica dentro da sessão
entry       JSONB    -- payload SDK (type, content, message, tool_uses, etc.)
mtime       BIGINT   -- timestamp ms
```

Volume confirmado (2026-05-11):
- **36.321 linhas total** (média ~67 entries/sessão × 541 sessões)
- **14.591 entries tipo `assistant`** (incluem tool_use blocks com tools + params)
- **11.018 entries tipo `user`** (prompts originais + tool_result com outputs)
- **506 entries tipo `system`** (system prompts cacheados — descartar)
- + attachments, progress, agent_metadata

### Universo viável para bootstrap

Filtros para identificar candidatos de qualidade:

```sql
SELECT s.session_id
FROM agent_sessions s
WHERE s.total_cost_usd < 2.0       -- sessão resolvida (não outlier caro)
  AND s.message_count BETWEEN 3 AND 20  -- nem muito curta nem ruminação
  AND s.summary IS NOT NULL         -- Sonnet já gerou resumo pos-sessão (proxy de outcome)
  AND s.created_at > NOW() - INTERVAL '90 days'
ORDER BY s.created_at DESC
```

Volume real: **219 sessões resolved + 282 com summary** = corpus rico.

### Pipeline de bootstrap (one-time)

```
1. Query candidates (filtro acima) → lista de session_ids

2. Para cada candidate:
   a. SELECT seq, entry FROM claude_session_store
      WHERE session_id = ?
      ORDER BY seq

   b. Extrair sequência estruturada:
      - User prompt original (primeira entry type='user' com message.role='user')
      - Tool calls do assistant: iterar entries type='assistant',
        pegar message.content[*] onde type='tool_use' → (tool_name, input)
      - Tool results: iterar entries type='user',
        pegar message.content[*] onde type='tool_result' → output
      - Resposta final (última entry assistant com texto)

   c. Cruzar com agent_sessions.summary para extrair:
      - Outcome detectado (success/inconclusive/failure)
      - Title sugerido pela Sonnet pos-sessão

   d. Detectar validation signal:
      - Último user message: regex de "perfeito|exatamente|obrigado"
      - Ausência de correção nos últimos 3 turnos
      - Card action approved (se aplicável)

   e. Se signal positivo: playbook_extractor (Sonnet) com:
      - Sequência estruturada como input
      - Title do summary como hint
      - Output: XML do playbook (§3.2)

   f. Dedup semântico via embedding_seed (threshold 0.85)
      contra playbooks já criados nesta corrida

   g. Save com status='pending'
```

### Custo estimado de bootstrap (revisado)

- **219 sessões** candidatas (corpus real, não 500 hipotético)
- Sonnet @ ~$0.005-0.008 por extração (input ~3K tokens estruturados + output XML)
- **Total: ~$1.10-1.75 one-time** (menor que estimativa original)
- Tempo de processamento: ~1-2h em worker dedicado

### Justificativa estratégica (mantida)

Sem bootstrap, o sistema parte do zero — leva semanas para acumular massa crítica. Com bootstrap retroativo via `claude_session_store`, **dia 1 do sistema ativo já tem 30-80 playbooks distintos** cobrindo os processos mais comuns dos últimos 90 dias. Acelera o ROI em ~6-8 semanas, e cobre **toda a base de sessões** (não apenas as 1.48% com subagentes).

### Gotcha — IDs de sessão

`claude_session_store.session_id` é o **SDK ID** (ephemeral), gravado em `agent_sessions.data['sdk_session_id']`. Nossa coluna `agent_sessions.session_id` é o **UUID persistente**. Resolver via `_resolve_our_session_uuid()` (existe em `session_archive.py:89`) antes de cruzar.

---

## 6. Fluxo de captura

### 6.1 Triggers de detecção (Hook `Stop`)

Sinais positivos de validação a serem detectados no último user message ou no estado da sessão:

| Sinal | Peso | Exemplo |
|-------|------|---------|
| Palavras de confirmação | Alto | "perfeito", "exatamente", "isso mesmo", "obrigado" (quando NÃO é só polidez de fechamento) |
| Aprovação de Adaptive Card | Muito alto | `criar_separacao_preview` → click em "confirmar_separacao" |
| Ausência de correção em N turnos | Médio | Última correção há ≥ 5 turnos, sessão prosseguiu sem mudança de direção |
| Comportamento downstream | Alto | Usuário pediu "agora faça o mesmo para data X" — sinal claro de reprodução desejada |

### 6.2 Pipeline pos-sessão

```
1. session_summarizer já roda (existente) → estrutura summary
2. NOVO: playbook_extractor (Sonnet)
   - Input: summary + log de tools/skills usadas + parâmetros + validation signal
   - Output: playbook XML candidato OU "no_playbook" (se sequência não foi validada)
3. Dedup semântico:
   - Embeddar trigger.embedding_seed
   - Buscar playbooks existentes com similaridade >= 0.85
   - Se achar: incrementar validations + metrics do existente
   - Se não: salvar novo com status='pending'
4. pending → active: após 2ª validação independente (outro usuário OU outra sessão do mesmo)
```

Custo estimado por captura: **~$0.008** (Sonnet com cache) — só roda quando sinal de validação é detectado, não em toda sessão.

---

## 7. Fluxo de aplicação

### 7.1 No `UserPromptSubmitHook`

```
1. Calcular match_score contra TODOS os playbooks ativos do domínio inferido
2. Se max_score >= 0.70: injetar playbook como <validated_playbook> no contexto
3. Se 0.50 <= max_score < 0.70: injetar como <playbook_sugerido> + perguntar ao usuário
4. Se max_score < 0.50: não injetar
```

### 7.2 Frame de injeção no contexto

```xml
<validated_playbook priority="high">
  <!-- Este processo foi validado N vezes (última validação: data). -->
  <!-- Os passos abaixo devem ser executados na ordem, com confirmação humana em gates R3. -->
  <!-- Se algum passo falhar, sinalizar e PARAR — não tentar caminhos alternativos. -->

  {playbook XML aqui}
</validated_playbook>
```

### 7.3 Decisão do modelo

O modelo continua decidindo CASO aplicar (R3, safety), mas a sequência de tools/parâmetros está pré-determinada. O modelo essencialmente "lê o script" em vez de improvisar.

---

## 8. Ciclo de vida do playbook

```
[captured] → pending → active → ↻ deprecated
              ↓
           rejected (humano clicou "não é playbook")
```

| Estado | Critério de entrada | Comportamento |
|--------|---------------------|---------------|
| `pending` | Capturado em 1 sessão | NÃO é injetado ainda — espera validação independente |
| `active` | ≥ 2 validações independentes OU aprovação manual | Injetado quando match_score >= 0.70 |
| `deprecated` | `failure_count ≥ 3` OU `failure_rate > 30%` | NÃO é injetado mais; permanece no DB para histórico |
| `rejected` | Operador marcou explicitamente | NÃO é injetado |

---

## 9. Métricas (dashboard admin)

| Métrica | Como medir | Meta |
|---------|------------|------|
| `playbook_count_active` | COUNT(playbooks status='active') | Crescente |
| `playbook_hit_rate` | sessoes com playbook injetado / sessoes totais | > 30% em 3 meses |
| `playbook_success_rate` | success_count / (success + failure) | > 80% |
| `cost_reduction_per_playbook` | avg_cost (sessoes pre-playbook) - avg_cost (sessoes com playbook) | > $1.00 |
| `time_to_first_success` | tempo desde captura ate 1a validacao independente | < 7 dias |

---

## 10. Não-objetivos v1 (deixar para v2)

- **Branching/decisões dentro do playbook** — v1 só linear
- **Playbooks com loop** ("para cada cliente: ...")
- **Edição manual via UI** — v1 só via banco direto / SQL
- **Versionamento de playbook** — v1 sobrescreve o ativo
- **Compartilhamento cross-empresa** — v1 só user_id=0
- **Captura automática de playbook em conversas Teams** — v1 só Web (Teams na v1.1)

---

## 11. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Capturar processo errado e replicar | Média | Alto | Exigir 2 validações independentes antes de `active` |
| Match score injeta playbook em prompt mal-classificado | Média | Médio | Threshold conservador (0.70) + R3 ainda exige confirmação |
| Custo de captura escalar | Baixa | Baixo | Só roda em sessões com validation signal detectado (filtro pre-LLM) |
| Conflito com R3 (confirmação) | Baixa | Crítico | Spec explícita: playbook NÃO bypassa gates de safety |
| Playbook desatualiza (skill mudou parâmetro) | Alta | Médio | Worker detecta `failure_count >= 3` e marca deprecated automático |

---

## 12. Plano de implementação faseado

### Fase 1 — Foundation (3-4 dias)
- Schema novo: tabela `agent_playbooks` (separada de `agent_memories` — estrutura diferente o suficiente)
- Migration `agent_playbooks.sql` com índices (status, embedding via pgvector). **SEM coluna `domain` fixa** — armazenar `tools_used` (JSONB) e calcular domain em runtime via `_resolve_domain()`
- Models SQLAlchemy + repository
- `domain_resolver.py`: implementar derivação 3-camadas (mapper → frontmatter → cluster emergente)

### Fase 2 — Bootstrap retroativo via `claude_session_store` (1-2 dias)
- Worker `playbook_bootstrap_from_session_store.py` (one-time job, queueable)
- Query candidatos: 219 sessões resolved + 282 com summary (filtros §5.5)
- Loop: query session_store por session_id → estruturar sequência tools/params/outputs → detect validation signal → Sonnet extract → dedup → save
- Resolver SDK ID ↔ UUID via helper existente (`_resolve_our_session_uuid`)
- Validação manual no dashboard: revisar primeiros ~20 playbooks gerados antes de promover a active
- **Esta fase entra ANTES de captura ao vivo** — bootstrap inicial cria base
- **NÃO usar S3 archive como fonte** — só cobre 1.48% das sessões

### Fase 3 — Captura ao vivo (3-5 dias)
- `playbook_extractor.py` — Sonnet pos-sessão extrai candidato
- Hook `Stop` detecta validation signal (reusa lógica do bootstrap)
- Dedup semântico pre-save (reaproveita pipeline da fase 2)
- Dashboard admin: listar pending para revisão manual

### Fase 4 — Aplicação (2-3 dias)
- Tier de match no `_user_prompt_submit_hook`
- Injection de `<validated_playbook>`
- Integração com R3 (gate respeitado)

### Fase 5 — Métricas + Deprecation (2 dias)
- Worker que detecta `failure_count >= 3` e marca deprecated
- Dashboard com métricas (§9)
- Alertas em playbook com falha emergente

### Fase 6 — Frontmatter migration (paralela, ongoing)
- PR onda 1: adicionar `domain:` no frontmatter das ~30 skills existentes
- Teste CI que valida coerência mapper ↔ frontmatter (alerta de drift)
- Mapper hardcoded vira fallback para tools built-in (Bash, Read, etc.) apenas

### Fase 7 — Refinamento (continuo)
- Ajustar thresholds (match_score, deprecation)
- Adicionar branching (v2)
- UI de edição manual (v2)
- Auto-clusterização emergente para tools sem mapping (§4.5 camada 3)

**Esforço total v1**: ~12-17 dias úteis. Fase 2 (bootstrap) entrega valor imediato — playbooks ativos no dia 1 da app, sem esperar semanas de captura ao vivo.

---

## 13. Decisões em aberto (para discussão pos-aprovação)

1. **Tabela nova vs reuso de `agent_memories`?**
   - Nova: estrutura específica, queries mais limpas, evita poluir tabela de memórias
   - Reuso: aproveita pipeline existente (embeddings, cold tier, etc.)
   - **Recomendação preliminar**: nova tabela. Playbooks têm ciclo de vida (active/deprecated), métricas próprias, validations multi-source — distintos o suficiente para merecer schema próprio.

2. **Captura também em Teams desde v1?**
   - Teams tem AdaptiveCards que sinalizam validação claramente (`confirmar_separacao` click)
   - Mas complexidade dobra (race conditions, timeout, etc.)
   - **Recomendação**: v1 web only. v1.1 = adicionar Teams.

3. **Playbook é per-empresa ou per-user?**
   - Per-empresa: Marcus descobre, Gabriella usa
   - Per-user: cada um tem seu playbook (perde o ganho institucional)
   - **Recomendação**: per-empresa (user_id=0), mas registrar `provenance.captured_from_user` para auditoria

4. **Como tratar playbook que falha 1x mas é caso edge?**
   - Marcar deprecated direto pode jogar fora playbook bom
   - **Recomendação**: threshold de deprecation = `failure_count >= 3` AND `failure_rate > 30%` (precisa ambos)

---

## 14. Referências

- **Visão original**: conversa Rafael ↔ Claude 2026-05-11 (sessão de memory review)
- **Trigger detection**: análise R0 ignorado pelo modelo (REC-2026-04-27-001)
- **Cluster expertise_* fix**: este mesmo dia, `pattern_analyzer.py` e `memory_injection.py` modificados
- **`tool_skill_mapper.py`**: hoje source of truth de domínios hardcoded — será gradualmente substituído (§4.5 + Fase 6)
- **Memory injection tiers**: `app/agente/sdk/memory_injection.py` linhas 798-870 (referência arquitetural)
- **AdaptiveCards Teams**: `app/agente/tools/teams_card_tool.py` (mecanismo de validação explícita)
- **`claude_session_store`**: tabela source-of-truth do transcript SDK (Fase B cutover, ver `app/agente/CLAUDE.md`) — **fonte real do bootstrap §5.5**
- **`session_archive.py`** (S3): só arquiva subagentes (1.48% das sessões) — útil para forensics, NÃO para playbooks
- **S3 storage geral**: `.claude/references/S3_STORAGE.md` (mapa completo de uso atual)
- **Helper para IDs**: `_resolve_our_session_uuid()` em `session_archive.py:89` — necessário para cruzar SDK ID ↔ UUID

## Contexto

_A completar (PAD-A Onda 4)._

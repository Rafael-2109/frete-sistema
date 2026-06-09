# C4 — Macro-Estruturas de Contexto em Camadas: Critérios de Admissão por Camada
## Pesquisa externa + análise do contexto real do Agente Nacom Goya
## Subagente: C4 | Data: 09/06/2026

---

## SUMÁRIO EXECUTIVO

Esta pesquisa sintetiza evidências externas de 8+ fontes autorizadas sobre como times
maduros organizam contexto de agentes em camadas. O objetivo é responder RP-1 do Rafael:
*"Antes de definir PARA ONDE vai, precisamos saber O QUE tem que estar AONDE"*.

A resposta central: **cada camada tem um critério dominante de admissão** — estabilidade,
altitude, modalidade de acesso, e temporalidade. O problema diagnosticado no boot atual
(RP-1: "peso igual por linha") é consequência direta da ausência desses critérios.

---

## PARTE 1 — FUNDAMENTO TÉCNICO: PROMPT CACHING E ESTABILIDADE

### 1.1 A Mecânica do Prefix Caching (Anthropic Docs)

**Fonte**: Anthropic Prompt Caching Docs — platform.claude.com/docs/en/build-with-claude/prompt-caching

A cache do Claude exige que o prefixo seja **100% idêntico** entre requisições:
- Qualquer mudança num bloco invalida aquele bloco e TODOS os subsequentes
- Ordem obrigatória de avaliação: `tools → system → messages`
- TTL padrão: 5 minutos; TTL estendido (1h) disponível

**Implicação direta para arquitetura de camadas:**

```
Se você muda tools → invalida system + messages (100% miss)
Se você muda system → invalida messages (miss parcial)  
Se você muda messages → só messages é invalidado (hit parcial)
```

O Anthropic recomenda explicitamente separar o system prompt em **múltiplos blocos**
com `cache_control` em posições de estabilidade diferente:

```python
# Layer 1: Core invariant instructions (muda semanalmente no máximo)
{"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}  # <- breakpoint aqui

# Layer 2: Session-level context (muda diariamente)
{"type": "text", "text": "..."}  # dynamic, sem cache_control
```

**Critério de admissão derivado:**
> **Camada system prompt "cacheável"** = apenas conteúdo que é IDÊNTICO em 95%+
> das sessões do mesmo usuário, no mesmo dia. Qualquer coisa que varia por turno,
> por sessão, por semana, ou por usuário pertence a camadas posteriores.

### 1.2 Hierarquia de Estabilidade Temporal

A pesquisa revelou uma taxonomia clara de estabilidade (fonte: AgentMarketCap 2026,
ZBrain, Anthropic Engineering):

| Frequência de mudança | Onde deve morar |
|-----------------------|-----------------|
| Invariante (muda raramente ou nunca) | System prompt — bloco cacheável |
| Semanal/mensal | System prompt — bloco cacheável (com TTL 1h) |
| Diário / por usuário autenticado | System prompt dinâmico OU início do hook |
| Por sessão | Hook inicial (UserPromptSubmit) |
| Por turno | Hook reinjectado por turno |
| Sob demanda (intent-driven) | Skill (carregada JIT) ou ferramenta/RAG |

---

## PARTE 2 — TAXONOMIA DE CONTEÚDO POR CAMADA (fontes consolidadas)

### Fonte primária: Anthropic Engineering Blog — "Effective Context Engineering for AI Agents"

O artigo identifica **5 tipos de informação** que requerem tratamento diferente:

| Tipo | Tratamento correto | Exemplo |
|------|-------------------|---------|
| **Behavior Guidance** | System prompt; mínimo e claro | Instruções de comportamento, hierarquia |
| **Structural Knowledge** | Examples / few-shot | Casos canônicos de operação |
| **Operational State** | Memory / notas externas | Progresso de tarefas, milestones |
| **Environmental Data** | Tools + JIT retrieval | BD, Odoo, filesystem |
| **Redundant Outputs** | Poda agressiva (compaction) | Resultados de tool calls pós-execução |
| **Metadata/Signals** | Referências leves | Timestamps, hierarquia de pastas |

**Princípio central**: "Find the smallest possible set of high-signal tokens that maximize
the likelihood of some desired outcome." O contexto é recurso escasso com retorno
marginal decrescente ("context rot").

### Fonte: ZBrain — "Context Engineering for Agentic AI"

Identifica 4 camadas funcionais:

```
┌────────────────────────────────────────────────────────────────────────┐
│ CAMADA POLÍTICA/GOVERNANÇA                                              │
│ • Instruções de sistema com definição de papel                         │
│ • Restrições de compliance e regulamentação                            │
│ • Controles de acesso baseados em papel                                │
│ • Regras de escalamento e aprovação                                    │
│ Critério: "Compliance is enforced by embedding policy rules in system  │
│ instructions" — NÃO inclui detalhes operacionais, definições de tool   │
├────────────────────────────────────────────────────────────────────────┤
│ CAMADA DE CONHECIMENTO/PERCEPÇÃO                                       │
│ • Conhecimento recuperado via RAG                                      │
│ • Documentos, chunks semânticos                                        │
│ • Dados em tempo real de APIs/BDs                                      │
│ Critério: relevância para a tarefa ATUAL; filtrado por ranking         │
│ NÃO inclui: políticas obsoletas, info irrelevante ao workflow ativo    │
├────────────────────────────────────────────────────────────────────────┤
│ CAMADA DE ESTADO/MEMÓRIA                                               │
│ • Histórico de sessão/conversa (curto prazo)                          │
│ • Variáveis de trabalho rastreando progresso de tarefa                 │
│ • Memória persistente de longo prazo                                   │
│ Critério: necessário para CONTINUIDADE entre ciclos de raciocínio      │
│ NÃO inclui: bate-papo trivial, estados intermediários obsoletos        │
├────────────────────────────────────────────────────────────────────────┤
│ CAMADA DE TOOLS/AÇÕES                                                  │
│ • Definições estruturadas de ferramentas com parâmetros                │
│ • Schemas de API e limites de acesso                                   │
│ Critério: "formalized capabilities" com I/O explícito                  │
│ NÃO inclui: tools não validadas ou não autorizadas                     │
└────────────────────────────────────────────────────────────────────────┘
```

### Fonte: 12-Factor Agents (HumanLayer) — Fatores 2, 3, 5, 9

**Factor 2 — Own Your Prompts:**
"Prompts are the primary interface between your application logic and the LLM."
O system prompt deve encapsular: identidade do agente, restrições operacionais, frameworks
de decisão. Definições de tools e structured outputs pertencem a camadas separadas
(Factor 4 — não lido, mas mencionado como separação explícita no Factor 2).

**Factor 3 — Own Your Context Window:**
Cinco camadas de informação em qualquer ponto de execução de agente:
1. Prompts & Instructions (system)
2. External Data (RAG)
3. Historical Information (tool calls, resultados passados)
4. Memory (conversas relacionadas)
5. Output Specifications (formato de saída estruturado)

"Fill your context window past 40% and you enter the 'dumb zone' where signal-to-noise
degrades, attention fragments, and agents start making mistakes."

**Factor 5 — Unify Execution State and Business State:**
Use um único event log (Thread) como fonte da verdade para estado — consolida o que
o agente está fazendo + os dados que coletou. NÃO fragmentar estado entre contextos
diferentes.

**Factor 9 — Compact Errors:**
Erros devem entrar no contexto de forma compacta — não como dumps longos. O LLM
precisa do erro para auto-corrigir, mas dumps extensos fragmentam atenção.

### Fonte: Claude Code Architecture (arxiv 2604.14228 + Piebald-AI/claude-code-system-prompts)

O próprio Claude Code implementa separação em 3 tiers + compaction pipeline:

```
Tier 1 — System context (getSystemContext):
  → Git status + project metadata
  → Cacheado + appendado ao system prompt
  → Critério: metadata estável do projeto

Tier 2 — User context (getUserContext):
  → CLAUDE.md hierarquia + data atual
  → Adicionado como USER MESSAGE (não no system prompt!)
  → Critério: configuração visível, version-controllable

Tier 3 — Conversation history:
  → getMessagesAfterCompactBoundary()
  → Critério: o que o usuário realmente disse + resultados de tools
```

**Insight crítico**: O CLAUDE.md opera como mensagem de usuário, NÃO como system prompt.
Isso mantém o system prompt base estável (cacheável) e o CLAUDE.md adaptável por projeto.

O Claude Code também implementa lazy loading de CLAUDE.md: "additional nested-directory
instruction files and conditional rules are loaded only when the agent reads files in
those directories, preventing unused instructions from consuming context."

### Fonte: Anthropic Engineering — "Equipping Agents with Agent Skills"

**Arquitetura de skills com 3 níveis de disclosure:**

```
Nível 1 — Boot: apenas nome + description da skill (poucas linhas)
Nível 2 — Demanda: SKILL.md completo carregado quando tarefa bate com a skill
Nível 3 — JIT: arquivos referenciados dentro da skill (forms.md, reference.md, scripts)
```

"The name and description attributes are read at model start and loaded into the system
prompt. The body of the skill file is loaded only when Claude decides that a skill
is relevant."

**Admissão Critério:** Uma skill deve conter conhecimento PROCEDIMENTAL (step-by-step),
não conhecimento DECLARATIVO (o que existe, definições). Declarativo fica em references
(JIT via tool), procedimental fica na skill.

**"The amount of context that can be bundled into a skill is effectively unbounded"**
porque o agente carrega seletivamente via acesso ao filesystem.

### Fonte: OpenAI Model Spec — Hierarquia de Instrução

A hierarquia OpenAI formaliza prioridade de fonte:
1. **Root** — Model Spec (nunca sobrescrito, treinado no modelo)
2. **System** — Regras do operador/plataforma (sobrescreve usuário)
3. **Developer** — Configuração do aplicativo (pode ser sobrescrito por usuário explicitamente)
4. **User** — Instruções da conversa (guideline-level, sobrescrito por contexto)

**Insight**: instrução de "sistema" não significa "tudo que está no system prompt" —
significa instrução com **autoridade de operador**. A hierarquia é sobre FONTE DE
AUTORIDADE, não sobre posição no contexto.

---

## PARTE 3 — CRITÉRIOS DE ADMISSÃO CONSOLIDADOS POR CAMADA

### Camada 0: Tools (Definições)

**O que é:** Lista de tools disponíveis (MCP, builtins)
**Critério de admissão:** Apenas tools que o agente PODE precisar nesta sessão
**Critério de exclusão:** Tools dev-only sem uso pelo agente web (ex: diagnosticando-banco, padronizando-docs)
**Por que aqui:** Muda raramente; invalida TUDO abaixo se mudar (hierarquia caching)
**Frequência de mudança:** Mensal (ao adicionar/remover capabilities)
**Altitude:** Alta — capacidades, não comportamentos específicos

### Camada 1: System Prompt Cacheável (preset + policy core)

**O que é:** Identidade do agente, hierarquia constitucional, regras invariantes, segurança
**Critério de admissão:**
- ✅ Comportamento invariante entre 100% das sessões do mesmo contexto
- ✅ Regras de segurança invioláveis (L1/L2 da hierarquia constitucional)
- ✅ Instruções que definem COMO o agente deve agir (não O QUE ele sabe)
- ✅ Hierarquia de prioridade para resolver conflitos de regras
- ✅ Protocolo de memória + ferramentas persistentes (R0)

**Critério de exclusão:**
- ❌ Conteúdo que muda por sessão, por usuário, ou por turno
- ❌ Conhecimento de domínio (gotchas Odoo, paths, etc.) — pertence a references/skills JIT
- ❌ Listas de subagentes com descrições longas — pertence ao CLAUDE.md
- ❌ Estado de debug/SQL admin — pertence ao hook condicional
- ❌ Exemplos de skills (few-shots procedurais) — pertencem às skills

**Por que aqui:** Prompt caching: deve ser idêntico em todas as sessões para maximizar cache hits.
O preset_operacional.md e o core do system_prompt.md são exatamente isto.

**Altitude:** "Alta altitude" — princípios que guiam COMO agir, não O QUE fazer

**Exemplo de conteúdo correto:**
> "L1 — SEGURANÇA (inviolável): Não fabricar dados, IDs, campos ou valores."
> "constitutional_hierarchy + exemplo trabalhado"
> "R0 Memory Protocol — quando salvar, como salvar"

### Camada 2: CLAUDE.md (Mapa do Território)

**O que é:** Referência técnica do projeto, mapa de paths, índice de documentação
**Critério de admissão:**
- ✅ Mapa do sistema: onde está cada módulo, o que existe
- ✅ Índice de referências (ponteiros, não o conteúdo)
- ✅ Regras que são ESPECÍFICAS do projeto mas ainda genéricas o suficiente
- ✅ Tech stack e versões (lookup rápido)

**Critério de exclusão:**
- ❌ Conteúdo DEV-ONLY: CSS architecture, migrations, CRUD scripts, pre-commit hooks
- ❌ Design system UI — sem relevância para agente web
- ❌ Conteúdo duplicado do system_prompt (subagentes, routing)
- ❌ Gotchas operacionais profundos (devem estar em references JIT)

**Por que aqui:** O CLAUDE.md é o "mapa do território" — diz onde as coisas estão,
não como usá-las. É como uma TOC. No Claude Code, CLAUDE.md é injetado como USER MESSAGE,
não no system prompt — o que significa que PODE variar sem invalidar o cache do sistema.

**Altitude:** Médio-alta — conhecimento estrutural, não operacional

**Tensão real identificada (R-5):** O CLAUDE.md atual serve DOIS contexts (dev + agente web)
sem distinguir. Deve haver critério explícito de "para quem" cada seção existe.

### Camada 3: Skills (Procedimento Sob Demanda)

**O que é:** Pacotes de conhecimento procedimental carregados JIT
**Critério de admissão:**
- ✅ Conhecimento procedimental step-by-step (como fazer X)
- ✅ Scripts determinísticos + documentação de uso
- ✅ Gotchas específicos de uma operação (dentro do SKILL.md da skill relevante)
- ✅ Conteúdo de alta variância de uso (só ~25-30% das sessões o necessitam)

**Critério de exclusão:**
- ❌ Regras comportamentais gerais (pertencem ao system prompt)
- ❌ Skills que o agente web NUNCA usa (consultando-sentry, diagnosticando-banco → R-3)
- ❌ Skills duplicadas entre si (lendo-arquivos vs lendo-documentos → R-4)
- ❌ "WHEN TO USE" genérico repetido que já está no routing_strategy (redundância C1)

**Nível de disclosure correto:**
- Boot: só nome + description (< 50 tokens)
- On-demand: SKILL.md completo
- JIT: arquivos adicionais referenciados dentro da skill

**Altitude:** Baixa — conhecimento operacional específico e detalhado

### Camada 4: Hook Dinâmico (Estado do Turno/Sessão)

**O que é:** Injeção dinâmica a cada turno com contexto de sessão específico
**Critério de admissão:**
- ✅ session_context: data, user_id, permissões especiais (pessoal_access)
- ✅ user_rules: regras mandatórias salvas pelo usuário (correto, conteúdo load-bearing)
- ✅ user_memories (RAG por intent): apenas memórias relevantes ao turno atual
- ✅ recent_sessions: últimas 5 sessões (continuidade inter-sessão)
- ✅ pendencias_acumuladas: tarefas pendentes entre sessões
- ✅ operational_directives: diretivas críticas de operação (WHEN/DO)
- ✅ debug_mode_context + sql_admin_context: CONDICIONAIS (só quando ativo)

**Critério de exclusão:**
- ❌ stale_empresa + improvement_responses → pertencem à skill gerindo-agente (C3 da auto-avaliação)
- ❌ skill_hints priority="advisory" → valor não confirmado (C4 da auto-avaliação)
- ❌ world_model priority="advisory" → valor não confirmado (C4 da auto-avaliação)
- ❌ routing_context.preferred_skills com skills dev-only → R-7
- ❌ Memórias empresa injetadas em volume sem filtro por intent (C5 da auto-avaliação)
- ❌ improvement_dialogue determinístico → pertence ao gerindo-agente, não ao boot operacional

**Por que aqui:** O hook é o único lugar que DEVE mudar a cada turno — contém o estado
vivo da sessão. Tudo que tem "priority advisory" e cujo efeito não foi medido é candidato
a remoção (princípio A/B da auto-avaliação do agente).

**Altitude:** Muito baixa — estado efêmero e específico ao turno

### Camada 5: References (Conhecimento Profundo JIT)

**O que é:** Arquivos de referência carregados via tool (Read, Glob, Grep) quando necessário
**Critério de admissão:**
- ✅ Gotchas profundos de sistemas específicos (Odoo, SSW)
- ✅ Regras de negócio detalhadas com exceções
- ✅ Schemas de tabelas
- ✅ Documentação que é relevante para ~5-15% das sessões

**Por que aqui:** "Context as scarce resource" — conhecimento que não é usado em 85%+
das sessões NÃO deve estar no boot. Carrega JIT via tool call.

---

## PARTE 4 — CRITÉRIO UNIFICADOR: ALTITUDE DE INSTRUÇÃO

### O Conceito de "Instruction Altitude"

Fontes: Anthropic Engineering ("Goldilocks zone"), arxiv 2603.05344, papers de agent design

"System prompts should present ideas at the right altitude for the agent — the Goldilocks
zone between two common failure modes: (1) hardcode complex, brittle logic (too low), or
(2) provide vague guidance that fails to give concrete signals (too high)."

**Tabela de altitude por camada:**

```
ALTITUDE ALTA (princípios invariantes, policy)
┌─────────────────────────────────────────────┐
│ preset_operacional + system_prompt core     │ → "NUNCA fabricar dados (L1)"
│ Regras constitucionais, segurança, ética    │ → "Confirmar antes de escrita irreversível"
└─────────────────────────────────────────────┘
         ↓ mais específico
┌─────────────────────────────────────────────┐
│ CLAUDE.md (mapa do território)              │ → "paths do módulo carteira"
│ Estrutura do sistema, índice de referências │ → "índice de skills disponíveis"
└─────────────────────────────────────────────┘
         ↓ mais específico
┌─────────────────────────────────────────────┐
│ Skills (procedimentos)                      │ → "como criar separação: passo 1, 2, 3"
│ Conhecimento operacional step-by-step       │ → "gotcha X da skill Y"
└─────────────────────────────────────────────┘
         ↓ mais específico
┌─────────────────────────────────────────────┐
│ Hook dinâmico (estado da sessão)            │ → "user_id=1, permissão pessoal=sim"
│ Memórias do usuário, sessões anteriores     │ → "usuário prefere Excel automático"
└─────────────────────────────────────────────┘
ALTITUDE BAIXA (estado efêmero, ultra-específico)
```

**Regra de consistência:**
> Conteúdo de altitude baixa numa camada alta = noise
> Conteúdo de altitude alta numa camada baixa = redundância

---

## PARTE 5 — APLICAÇÃO AO CONTEXTO ATUAL DO AGENTE NACOM

### Violações Observadas no Boot Atual

Baseado na leitura das 5 camadas do contexto (contexto_boot.md):

**1. Conteúdo DEV-ONLY no CLAUDE.md (violação R-5):**
- Design System (UI/CSS) — seção inteira irrelevante para agente web
- "ANTES de criar/editar doc ou script: LER ARQUITETURA_DE_ARTEFATOS.md" → dev-only
- "FONTE DE DADOS: LER .claude/references/INFRAESTRUTURA.md" → regra de dev; agente web
  tem suas próprias tools para dados, não lê esse arquivo
- Critério de admissão violado: conteúdo que não passa no teste "o agente web usa isto?"

**2. Conhecimento procedimental profundo no system_prompt (violação de altitude):**
- Descrição longa de subagente `gestor-estoque-odoo` (~200 tokens com status de skills,
  G021/G022, ROADMAP_SKILLS.md) é conteúdo de baixa altitude num local de alta altitude
- Deveria ser: "gestor-estoque-odoo | operações de escrita de estoque + consulta ao vivo"
  e o detalhe vive em `app/odoo/estoque/CLAUDE.md` (já existe, já é referenciado)

**3. Estado efêmero no system_prompt (violação C3 da auto-avaliação):**
- `stale_empresa count="33"` e `improvement_responses` no boot operacional
  → conteúdo de governança do agente, não operacional; pertence ao gerindo-agente

**4. Skills dev-only expostas ao agente web (violação R-3):**
- `diagnosticando-banco` — ferramenta de DBA, não de operador logístico
- `consultando-sentry` — ferramenta de monitoramento, não de operação
- `padronizando-docs` — ferramenta de documentação, não de operação
- Critério: skill deve ser usada em pelo menos 1% das sessões do contexto de destino

**5. Memórias injetadas sem filtro de intent (violação C5):**
- `memories/empresa/armadilhas/integracao/tmpdir-divergente...` injetada numa sessão
  sobre contexto de boot — não tem relação com o turno
- Critério: memória só deve ser injetada se tem probabilidade > threshold de ser usada
  no turno atual

**6. Advisory blocks sem evidência de efeito (candidatos a ablação C4):**
- `skill_hints priority="advisory"` — lista de 8 skills para uma consulta sobre contexto
  de boot → zero correspondência com o intent real
- `world_model priority="advisory"` — entidades "ELAINE", "ASSAI" etc. numa sessão técnica
- `routing_context.preferred_skills` contém skills dev-only (gerindo-agente, diagnosticando-banco)

**7. Conteúdo duplicado entre camadas (violação C1):**
- Subagentes listados em system_prompt E em CLAUDE.md (com listas diferentes — R-9)
- Routing instructions em: R7 (system_prompt) + ROUTING_SKILLS.md (reference) + 28 skills
  (each with WHEN TO USE) → 3 lugares para o mesmo assunto
- qtd_saldo gotcha: aparece em system_prompt (`critical_fields`), em múltiplas skills,
  e nas memórias

---

## PARTE 6 — PROPOSTA: CRITÉRIOS DE ADMISSÃO FORMALIZADOS

### Filtro de Camada (perguntas diagnósticas)

**Camada system prompt cacheável:**
1. Este conteúdo seria IDÊNTICO para 95%+ das sessões do agente web?
2. É uma regra de COMPORTAMENTO (como agir) ou de CONHECIMENTO (o que saber)?
3. Se este conteúdo não estivesse aqui, o agente tomaria decisões erradas mesmo com todas
   as tools e skills disponíveis?
→ Se SIM às 3: pertence ao system prompt. Se NÃO a qualquer uma: pertence em outra camada.

**Camada CLAUDE.md:**
1. Este conteúdo é relevante para o agente WEB (não para dev)?
2. É um mapa/índice (ponteiro) ou é o conteúdo em si?
3. Mudaria se o projeto mudasse de tamanho/escopo, mas não se o comportamento mudasse?
→ Se SIM às 3: pertence ao CLAUDE.md. Se é conteúdo detalhado: pertence a references/skills.

**Camada skills:**
1. Este conhecimento é procedimental (passo a passo) ou declarativo (o que existe)?
2. O agente web realmente usa esta skill (histórico confirma)?
3. A skill é suficientemente distinta das outras (< 50% overlap)?
→ Procedimental + usado + distinto = skill. Declarativo = reference JIT.

**Camada hook dinâmico:**
1. Este conteúdo MUDA a cada sessão/turno?
2. É essencial para o turno ESPECÍFICO que está acontecendo (não genérico)?
3. Tem priority="mandatory" ou é evidentemente critical para o agente?
→ SIM + priority mandatory/critical = hook. Advisory sem evidência = candidato a ablação.

**Camada references (JIT):**
1. Este conteúdo é necessário em menos de 20% das sessões?
2. O agente consegue acessá-lo via tool quando precisar?
3. É conhecimento profundo/especializado que seria noise na maioria dos contextos?
→ Se SIM às 3: pertence a references, não ao boot.

---

## PARTE 7 — SÍNTESE: TAXONOMIA FINAL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CAMADA          │ CRITÉRIO DOMINANTE    │ FREQUÊNCIA MUDANÇA │ CACHEÁVEL?  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tools            │ Capacidade do agente  │ Mensal             │ SIM         │
│ System prompt    │ Política invariante   │ Semanal/nunca      │ SIM (alto)  │
│ CLAUDE.md        │ Mapa do território    │ Semanal            │ SIM (médio) │
│ Skills (boot)    │ Mapa de capacidades   │ Mensal             │ SIM         │
│ Skills (JIT)     │ Procedimento on-dem.  │ Nunca (versioned)  │ N/A         │
│ Hook (sessão)    │ Estado autenticado    │ Por sessão         │ NÃO         │
│ Hook (turno)     │ Estado efêmero        │ Por turno          │ NÃO         │
│ References (JIT) │ Conhecimento profundo │ Nunca / raro       │ N/A         │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Regra mnemônica (para uso nas próximas sessões):**
- **System prompt** = "Como eu ajo" (política)
- **CLAUDE.md** = "O que existe e onde está" (mapa)
- **Skill** = "Como eu faço X especificamente" (procedimento)
- **Hook** = "Quem sou nesta sessão, o que ficou pendente" (estado)
- **Reference** = "O que eu consulto quando precisar aprofundar" (biblioteca)

---

## FONTES

1. Anthropic Prompt Caching Docs — https://platform.claude.com/docs/en/build-with-claude/prompt-caching
2. Anthropic Engineering — "Effective Context Engineering for AI Agents" — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
3. Anthropic Engineering — "Equipping Agents for the Real World with Agent Skills" — https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
4. HumanLayer — 12-Factor Agents (Factors 2, 3, 5, 9) — https://github.com/humanlayer/12-factor-agents
5. ZBrain — "Context Engineering for Agentic AI" — https://zbrain.ai/context-engineering-for-agentic-ai/
6. OpenAI Model Spec — https://model-spec.openai.com/2025-10-27.html
7. arxiv 2604.14228 — "Dive into Claude Code" — https://arxiv.org/html/2604.14228v1
8. Piebald-AI — Claude Code System Prompts — https://github.com/Piebald-AI/claude-code-system-prompts
9. SOTAAZ — "CLAUDE.md, .cursorrules, AGENTS.md Guide" — https://www.sotaaz.com/post/ai-coding-rules-guide-en
10. CometML — "Context Engineering" — https://www.comet.com/site/blog/context-engineering/
11. AgentMarketCap — Prompt Cache Hit Rate Engineering 2026 — https://agentmarketcap.ai/blog/2026/04/11/prompt-cache-hit-rate-engineering-2026
12. Contexto de boot real — /tmp/estudo-contexto-boot/contexto_boot.md (2084 linhas)
13. Auto-avaliação do agente — /tmp/estudo-contexto-boot/avaliacao_agente.md
14. Avaliação do Rafael — /tmp/estudo-contexto-boot/avaliacao_rafael.md

---

*Gerado por subagente C4. Para implementação, ver C5 (análise estrutura-por-estrutura)
e C6 (plano + roadmap). Este documento responde RP-1: define O QUE pertence AONDE antes
de discutir mudanças específicas.*

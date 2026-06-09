# C2 — Pesquisa: Docs Canônicas do Claude Agent SDK — O-que-mora-onde

**Subagente:** C2 (pesquisa externa)
**Data:** 09/06/2026
**Fontes primárias:**
- `https://code.claude.com/docs/en/agent-sdk/overview` (oficial Anthropic, verificado)
- `https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts` (oficial)
- `https://code.claude.com/docs/en/agent-sdk/subagents` (oficial)
- `https://code.claude.com/docs/en/agent-sdk/skills` (oficial)
- `https://code.claude.com/docs/en/hooks` (oficial)
- `https://code.claude.com/docs/en/memory` (oficial CLAUDE.md)
- `https://code.claude.com/docs/en/skills` (oficial skills completo)
- Context7 `/nothflare/claude-agent-sdk-docs` (Benchmark 85.9, fonte: github.com/nothflare/claude-agent-sdk-docs)
- Context7 `/anthropics/claude-agent-sdk-python` (Benchmark 86.5, fonte: github.com/anthropics/claude-agent-sdk-python)

---

## RESUMO EXECUTIVO

O SDK oferece **cinco mecanismos independentes** para carregar contexto no agente. Cada um tem papel, momento de carga e semântica distintos — e a Anthropic é **explícita** sobre o que pertence a cada um. O sistema Nacom usa todos os cinco, porém com sobreposições e conteúdo no lugar errado que a documentação canônica contradiz diretamente.

---

## MECANISMO 1 — system_prompt (Opções: preset / preset+append / custom string / file)

### O que a Anthropic recomenda

**Fonte:** `https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts`

> "System prompts define Claude's behavior, capabilities, and response style. Start from the `claude_code` preset for CLI or IDE-like coding tools where a human watches and steers the work. Write your own prompt for agents with a different surface, identity, or permission model."

#### Três pontos de partida canônicos:

| Opção | Quando usar | O que carrega |
|---|---|---|
| `type: "preset", preset: "claude_code"` | Agente tipo Claude Code (coding tool, humano supervisionando) | Full Claude Code prompt: tool guidance, code style, safety, response tone, env context |
| `type: "preset", ..., append: "..."` | Mesmo caso + regras adicionais de produto | Tudo do preset + texto appended ao final |
| String customizada | Agente com surface, identidade ou permission model DIFERENTE do Claude Code | Apenas o que você escreve; você assume responsabilidade por tool guidance e safety |
| `None`/vazio | Loop de tool-calling puro sem persona | Prompt mínimo: suporte a tool-calling e nada mais |

#### A decisão fundamental:

> "The deciding factor is how closely your agent resembles Claude Code: a coding agent operating in a repository, with a human watching streaming output and steering the work. The further your product is from that, the more you'll want to write your own prompt."

**"Different from Claude Code" inclui:**
- **Different surface**: output não é lido em terminal por quem disparou. Chat UIs, structured-output consumers.
- **Different identity**: agent não deve se apresentar como Claude Code.
- **Different permission model**: roda autonomamente sem humano aprovando cada passo, ou em conjunto restrito de recursos.
- **Non-coding tasks**: guias de código do preset competem com instruções que você realmente precisa.

#### O que o system_prompt NÃO deve conter (canonicamente):

A doc é implícita: o preset já cobre tool guidance, safety, response style, env context. Se usar custom string, você **perde tudo isso** e precisa reimplementar o que ainda precisar. O padrão recomendado para sistemas como o Nacom (agente com identidade própria, domínio não-coding) é **custom string** — não preset.

#### Otimização de cache de prompt:

> "By default, two sessions that use the same `claude_code` preset and `append` text still cannot share a prompt cache entry if they run from different working directories."

> `excludeDynamicSections: true` move per-session context (working dir, git flag, platform, shell, OS, auto-memory paths) para o **primeiro user message**, deixando apenas o preset estático na system prompt para compartilhar cache entre sessões.

**Implicação para Nacom:** O sistema usa custom system_prompt (correto para um agente logístico), mas carrega CLAUDE.md via `setting_sources` separadamente (correto). O problema não é o mecanismo, é o conteúdo.

---

## MECANISMO 2 — setting_sources / CLAUDE.md

### O que a Anthropic recomenda

**Fonte:** `https://code.claude.com/docs/en/memory` + `https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts`

#### Como CLAUDE.md é injetado:

> "CLAUDE.md is delivered as a **user message after the system prompt**, not as part of the system prompt itself."
> "CLAUDE.md takes a different path: the SDK reads it and injects its content into the conversation as **project context, not into the system prompt**, so it shapes behavior alongside whichever system prompt you choose."

**Isso é crítico:** CLAUDE.md NÃO tem o peso do system prompt. É mensagem de usuário. Claude lê e tenta seguir, mas **não há garantia de strict compliance**, especialmente para instruções vagas ou conflitantes.

#### Quando usar CLAUDE.md:

> "Use CLAUDE.md for instructions that should apply to every session in a project, regardless of which system prompt the session uses: coding standards, common commands, architecture context, and team conventions."

> "Treat CLAUDE.md as the place you write down what you'd otherwise re-explain. Add to it when: Claude makes the same mistake a second time; A code review catches something Claude should have known; You type the same correction or clarification into chat that you typed last session; A new teammate would need the same context to be productive."

> "Keep it to facts Claude should hold in every session: build commands, conventions, project layout, 'always do X' rules."

#### O que NÃO pertence ao CLAUDE.md:

> "If an entry is a multi-step procedure or only matters for one part of the codebase, move it to a **skill** or a **path-scoped rule** instead."

> "Unlike CLAUDE.md content, **a skill's body loads only when it's used**, so long reference material costs almost nothing until you need it."

#### Limite de tamanho (canônico):

> "**Size: target under 200 lines per CLAUDE.md file.** Longer files consume more context and reduce adherence. If your instructions are growing large, use path-scoped rules so instructions load only when Claude works with matching files."

> "The first 200 lines of `MEMORY.md`, or the first 25KB" — esse limite é do auto-memory, não do CLAUDE.md. **CLAUDE.md é carregado INTEIRO** independente do tamanho, mas aderência cai com arquivos longos.

#### setting_sources — o que cada source carrega:

| Source | O que carrega |
|---|---|
| `"project"` | `CLAUDE.md` ou `.claude/CLAUDE.md` do working directory + skills do projeto |
| `"user"` | `~/.claude/CLAUDE.md` + skills do usuário |
| `"local"` | `.claude/settings.local.json` |
| `None` (default) | Todas as fontes (match CLI defaults) |
| `[]` (lista vazia) | Nenhuma (SDK isolation mode) |

> "Must include `'project'` to load CLAUDE.md files."
> "The `claude_code` preset alone does NOT load CLAUDE.md files — you must also specify setting sources."

**Implicação para Nacom:** O CLAUDE.md raiz atual tem ~16KB e serve TANTO Claude Code (dev) QUANTO o Agente Web. A doc é explícita: CLAUDE.md é para "facts that should hold in every session". Conteúdo dev-only (TECH STACK, links a .claude/references, PAD-A) não pertence ao CLAUDE.md compartilhado que o agente web lê.

---

## MECANISMO 3 — Skills (SKILL.md frontmatter + body)

### O que a Anthropic recomenda

**Fonte:** `https://code.claude.com/docs/en/skills` (verificado direto)

#### Modelo de 3 níveis (confirmado canonicamente):

> "In a regular session, skill descriptions are loaded into context so Claude knows what's available, but **full skill content only loads when invoked**."

Tabela canônica:

| Frontmatter | Quem invoca | Quando carrega no contexto |
|---|---|---|
| (default) | Você E Claude | Description sempre em contexto; full skill carrega quando invocada |
| `disable-model-invocation: true` | Só você | Description NÃO em contexto; full skill carrega quando você invoca |
| `user-invocable: false` | Só Claude | Description sempre em contexto; full skill carrega quando invocada |

**Subagentes com skills preloaded são exceção:**
> "Subagents with preloaded skills work differently: the full skill content is injected at startup."

#### Limite canônico de description (CONFIRMADO):

> "Put the key use case first: **the combined `description` and `when_to_use` text is truncated at 1,536 characters** in the skill listing to reduce context usage."

**[NAO ENCONTRADO em docs oficiais: o "budget de 16K" mencionado em memórias internas.]** O limite documentado é **1.536 caracteres** por skill (description + when_to_use combinados). Budget total de skills não é documentado explicitamente nas fontes verificadas.

**Nota sobre a memória do sistema:** A memória `skills_budget_truncamento.md` menciona "CLI trunca a 16K" e "B feito (46→25)" como contagem de skills. O limite de 1.536 chars por description é o documentado oficialmente — o "16K" pode se referir ao budget total do listing de skills no contexto, [HIPÓTESE] não confirmada nas fontes atuais.

#### O que pertence na description vs body:

> "Claude uses this [description] to decide when to apply the skill."
> "The body loads only when invoked."
> "Keep the body itself concise. Once a skill loads, its content stays in context across turns, so every line is a recurring token cost."
> "State what to do rather than narrating how or why."
> "`SKILL.md` under 500 lines" (tip para manter conciso)

#### Lifecycle pós-invoke:

> "When you or Claude invoke a skill, the rendered SKILL.md content enters the conversation as a single message and stays there for the rest of the session."
> "Auto-compaction carries invoked skills forward within a token budget... keeping the first 5,000 tokens of each. Re-attached skills share a combined budget of **25,000 tokens**."

#### O que NÃO deve ficar em skills:

[NAO DOCUMENTADO explicitamente] — mas implícito: informações que devem estar em TODA sessão vão no CLAUDE.md; informações que só importam quando a skill é invocada vão no body.

---

## MECANISMO 4 — Hooks (UserPromptSubmit additionalContext)

### O que a Anthropic recomenda

**Fonte:** `https://code.claude.com/docs/en/hooks` (verificado direto)

#### UserPromptSubmit — detalhes canônicos:

> "When: User submits prompt, before Claude processes it"
> "Use case: Validate prompts, add context, block certain prompts"
> "**Default timeout: 30 seconds** (vs 600s on other events)"

#### O campo additionalContext:

> "Fields within the `hookSpecificOutput` object... For **PostToolUse, UserPromptSubmit, SessionStart, and SubagentStart**, the `additionalContext` (string) field can inject extra information into the conversation."

> "Where It Appears — UserPromptSubmit/UserPromptExpansion: **Alongside submitted prompt**"

#### Limite de tamanho (canônico):

> "**Output strings cap: 10,000 characters**"
> "Includes: additionalContext, systemMessage, plain stdout"
> "Exceeds limit: Saved to file, replaced with preview and file path"

**Nota importante:** O hook do Nacom injeta ~34KB/turno. Isso está **acima do limite de 10.000 chars** da saída de hooks individuais. [HIPÓTESE: o hook atual pode ser uma composição de múltiplos hooks ou usar um mecanismo diferente de injeção direta — a implementação real precisaria ser verificada em `app/agente/hooks/`.]

#### O que a Anthropic recomenda colocar no hook additionalContext:

> "Write as **factual statements** rather than imperative commands"
> ✅ "The deployment target is production"
> ✅ "This repo uses `bun test`"
> ❌ "You must always use npm" (triggers prompt injection defenses)

Casos de uso canônicos:
- Environment state (current branch, deployment target, feature flags)
- Conditional project rules (which test applies to edited file)
- External data (open issues, CI results, internal service data)

> "For static context, use CLAUDE.md instead (loads without script overhead)."

**Implicação para Nacom:** A doc é explícita: hooks são para **contexto dinâmico e condicional**. Conteúdo estático (memórias de empresa maduras, improvement_responses de sessões passadas, `stale_empresa=33`) não pertence no hook — pertence no CLAUDE.md ou, melhor, em skills específicas carregadas por demanda.

#### SessionStart hook:

> "When: New session or resume"
> "Use case: Load development context, set environment variables"
> "Supports: `type: 'command'` and `type: 'mcp_tool'` only"

---

## MECANISMO 5 — Subagents (AgentDefinition)

### O que a Anthropic recomenda

**Fonte:** `https://code.claude.com/docs/en/agent-sdk/subagents` (verificado direto)

#### CONFIRMADO: Subagentes NÃO herdam system prompt do pai

Tabela canônica do SDK:

| O subagente RECEBE | O subagente NÃO recebe |
|---|---|
| Seu próprio system prompt (`AgentDefinition.prompt`) + o prompt do Agent tool | Histórico de conversa do pai ou tool results |
| Project CLAUDE.md (carregado via `settingSources`) | Skill content preloaded, a menos que listado em `AgentDefinition.skills` |
| Tool definitions (herdadas do pai, ou o subset em `tools`) | **O system prompt do pai** |

> "The only channel from parent to subagent is the Agent tool's prompt string, so include any file paths, error messages, or decisions the subagent needs directly in that prompt."

**Memória confirmada:** A correção registrada nas memórias do sistema ("Subagentes NUNCA herdam system prompt do pai — corrigido 2x") está **totalmente alinhada com a documentação oficial**.

#### Campos canônicos do AgentDefinition:

| Campo | Required | Descrição |
|---|---|---|
| `description` | Yes | Natural language de QUANDO usar este agente |
| `prompt` | Yes | O system prompt do subagente — define role e comportamento |
| `tools` | No | Array de tools permitidas; se omitido, **herda todas as tools** |
| `disallowedTools` | No | Tools a remover do pool do agente |
| `model` | No | Override de modelo (alias: `sonnet`, `opus`, `haiku`, `inherit`) |
| `skills` | No | Nomes de skills para **preload** no contexto de startup do subagente |
| `memory` | No | Fonte de memória (`user`, `project`, `local`) |
| `maxTurns` | No | Máximo de turns agentic antes de parar |

#### Importante — subagentes NÃO podem spawnar sub-subagentes:

> "Subagents cannot spawn their own subagents. Don't include `Agent` in a subagent's `tools` array."

#### Filesystem-based agents (.claude/agents/):

A doc também documenta agentes definidos como markdown em `.claude/agents/`. Agentes programáticos têm precedência sobre filesystem-based com o mesmo nome.

---

## MAPA CONSOLIDADO — O-que-mora-onde (SDK canônico)

| Mecanismo | O que colocar | O que NÃO colocar | Momento de carga |
|---|---|---|---|
| **system_prompt** (custom string) | Persona, identidade, role, hierarquia de regras invioláveis (safety/ética), regras de comportamento de alta prioridade, poucos exemplos de conflito resolvido | Informações dinâmicas (data, usuário), gotchas de negócio voláteis, listas longas de regras | Uma vez, no início da sessão; estático → bom para cache |
| **system_prompt.append** | Instruções de produto sobre o preset claude_code; domain-specific additions | Persona completa, regras de safety (já cobertas pelo preset) | Estático, concatenado ao preset |
| **CLAUDE.md** (project) | Fatos persistentes do projeto: convenções, stack, paths, "always do X", gotchas de campo que todo contexto precisa, subagentes disponíveis (lista curta) | Conteúdo dev-only, procedimentos multi-passo (→ skills), contexto dinâmico (→ hooks), conteúdo que só importa para parte do codebase | User message após system prompt; carregado inteiro; aderência cai >200 linhas |
| **Skills (description/frontmatter)** | Trigger phrase, caso de uso primário, quando invocar/não invocar, sinais de escolha | Procedimento completo, exemplos longos, scripts | Listing sempre em contexto (truncado a 1.536 chars); body só quando invocada |
| **Skills (body/SKILL.md)** | Procedimento passo-a-passo, scripts, referências, exemplos, gotchas específicos da tarefa | Regras que devem valer em toda sessão (→ CLAUDE.md), instruções brevíssimas (→ description) | Carregado quando invocada; fica em contexto até fim da sessão |
| **Hook additionalContext** | Contexto dinâmico/condicional: data atual, usuário, pendências, memorias RAG relevantes ao turno, estado de sistemas externos, flags de debug | Conteúdo estático (→ CLAUDE.md), manutenção/governança do agente (→ gerindo-agente skill), memórias de empresa maduras sem relação com o turno | Por turno (UserPromptSubmit); limite 10.000 chars por hook |
| **AgentDefinition.prompt** | System prompt completo do subagente: persona, ferramentas disponíveis, objetivo, restrições | Histórico do pai (inacessível), sistema de memória do pai (separado) | Quando o subagente é spawned |

---

## ACHADOS ESPECÍFICOS COM EVIDÊNCIA

### A1 — CLAUDE.md NÃO é system prompt

**Fonte:** `https://code.claude.com/docs/en/memory`
> "CLAUDE.md content is delivered as a **user message after the system prompt**, not as part of the system prompt itself. Claude reads it and tries to follow it, but there's no guarantee of strict compliance."

**Implicação:** Regras invioláveis (security invariants, hierarquia constitucional L1/L2) pertencem ao **system_prompt**, não ao CLAUDE.md. O CLAUDE.md da Nacom contém tanto regras invioláveis (correto: no system_prompt.md) quanto conteúdo de referência de dev (incorreto: deveria ir em CLAUDE.md dev-only ou skills).

### A2 — Limite de description de skills: 1.536 chars (não 16K)

**Fonte:** `https://code.claude.com/docs/en/skills`
> "the combined `description` and `when_to_use` text is **truncated at 1,536 characters** in the skill listing"

O "budget de 16K" mencionado em memórias internas [HIPÓTESE: pode ser o budget total do listing completo de skills no contexto (1.536 × N skills), não por skill individual].

### A3 — Skill body: 5.000 tokens após compaction, budget total 25.000

**Fonte:** `https://code.claude.com/docs/en/skills`
> "keeping the first **5,000 tokens** of each [skill]. Re-attached skills share a combined budget of **25,000 tokens**."

Skill bodies longas são truncadas na compactação.

### A4 — Subagentes herdam CLAUDE.md do projeto (mas NÃO o system prompt)

**Fonte:** `https://code.claude.com/docs/en/agent-sdk/subagents`
> "Project CLAUDE.md (loaded via settingSources)" ← subagente RECEBE
> "The parent's system prompt" ← subagente NÃO RECEBE

Isso significa: gotchas críticos que subagentes precisam devem estar no **CLAUDE.md do projeto** (que subagentes leem) ou no **prompt do AgentDefinition** (passado explicitamente).

### A5 — Hooks: 10.000 chars de limite, contexto estático deve ir no CLAUDE.md

**Fonte:** `https://code.claude.com/docs/en/hooks`
> "Output strings cap: **10,000 characters**"
> "For static context, use CLAUDE.md instead (loads without script overhead)."

O hook atual do Nacom injeta ~34KB/turno. [HIPÓTESE: usa mecanismo além do `additionalContext` padrão, possivelmente injeção direta de user message ou múltiplos hooks compostos.]

### A6 — CLAUDE.md: aderência cai acima de 200 linhas

**Fonte:** `https://code.claude.com/docs/en/memory`
> "**target under 200 lines per CLAUDE.md file.** Longer files consume more context and reduce adherence."

O CLAUDE.md raiz da Nacom tem ~16KB. [NAO FOI CONTADO em linhas, mas é substancialmente maior que 200 linhas]. Impacto direto em aderência.

### A7 — system_prompt e setting_sources são independentes

**Fonte:** Context7 `/anthropics/claude-agent-sdk-python/src/claude_agent_sdk/_internal/transport/subprocess_cli.py`
```python
# system_prompt handling (lines 227-238) doesn't affect setting_sources
# The setting_sources flag is applied regardless of what system_prompt is set to
```

Setting sources e system_prompt são opções independentes. Podem ser combinados livremente.

### A8 — CLAUDE.md não afeta cache do system prompt

**Fonte:** `https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts`
> "CLAUDE.md content doesn't affect the system prompt cache because the SDK injects it into the conversation, not the system prompt."

CLAUDE.md nunca quebra o cache do system_prompt — é seguro ter conteúdo dinâmico nele sem penalidade de cache.

### A9 — Ordem de carga: broadest → most specific

**Fonte:** `https://code.claude.com/docs/en/memory`
> "Across the directory tree, content is ordered from the filesystem root down to your working directory... instructions closer to where you launched Claude are read last."

Managed policy → user (`~/.claude/CLAUDE.md`) → project (`CLAUDE.md`) → local (`CLAUDE.local.md`). Mais específico tem precedência por ser lido por último.

### A10 — O que subagentes preloaded de skills recebem (modo diferente)

**Fonte:** `https://code.claude.com/docs/en/skills`
> "Subagents with preloaded skills work differently: **the full skill content is injected at startup**."

Skill no campo `AgentDefinition.skills` = body completo no contexto de startup do subagente (não apenas description).

---

## GAPS — O QUE NÃO FOI ENCONTRADO / NÃO DOCUMENTADO

1. **Budget total do listing de skills no contexto**: documentado apenas por skill (1.536 chars description). Budget total [NAO DOCUMENTADO] nas fontes verificadas.

2. **Número máximo de skills**: [NAO DOCUMENTADO] nas fontes verificadas.

3. **Como o hook do Nacom injeta 34KB quando o limite documentado é 10.000 chars**: a implementação em `app/agente/hooks/` não foi lida nesta pesquisa. [HIPÓTESE: usa injeção de user message direta via SDK, não apenas `additionalContext` do hook JSON standard.]

4. **Recomendações explícitas sobre o que colocar no body do hook vs session_context**: a doc descreve additionalContext como para "dynamic facts" mas não lista exemplos de conteúdo a evitar (além de "static context → use CLAUDE.md").

5. **Comportamento de auto-memory em agentes SDK**: a doc menciona `AgentDefinition.memory` mas não detalha como auto-memory interage com o system_prompt customizado vs preset.

6. **Hosting Pattern 2 (per-process sticky session)**: a doc de hosting não foi encontrada com URL direta. A memória do sistema (`agent_sdk_config.md`) cita "Pattern 2 doc oficial /hosting" — não verificado nesta pesquisa.

7. **Tamanho máximo total do contexto de boot**: [NAO DOCUMENTADO] explicitamente. Limite implícito = context window do modelo menos o que a conversa consome.

---

## CONCLUSÕES PARA O SISTEMA NACOM

Com base na documentação oficial, os principais desvios do sistema atual em relação ao canônico são:

1. **CLAUDE.md compartilhado (raiz) serve dois mestres**: O SDK diz que CLAUDE.md é para "facts in every session" e deve ter "<200 linhas". O CLAUDE.md raiz da Nacom tem conteúdo dev-only (TECH STACK, CSS architecture, PAD-A, migrations) que o agente web não precisa — inflando o contexto e reduzindo aderência.

2. **Hook injetando conteúdo estático**: `stale_empresa`, `improvement_responses`, memórias de empresa sem relação com o turno são conteúdo estático/de-manutenção que a doc diz deve ir no CLAUDE.md (ou skill) — não em hooks (que são para contexto dinâmico/condicional).

3. **Inflação de prioridade vs hierarquia constitucional**: A doc recomenda system_prompt para regras invioláveis. O sistema Nacom faz isso corretamente (L1/L2 no system_prompt.md). O problema identificado pelo agente (C2 — 6 rótulos de "máximo") é de **design interno do system_prompt**, não de mecanismo errado.

4. **Skills dev-only expostas ao agente web**: A doc diz que `skills` é um "context filter, not a sandbox" — mas o filtro existe e deve ser usado. `consultando-sentry`, `diagnosticando-banco`, `gerindo-agente`, `padronizando-docs` não devem aparecer no listing do agente web.

5. **Subagentes**: O campo `agents` aceita tanto definição programática quanto filesystem-based (`.claude/agents/`). A lista de subagentes duplicada no system_prompt + CLAUDE.md é um problema de redundância, não de mecanismo. A fonte canônica para "quando usar qual subagente" deveria ser uma **skill** (description sempre em contexto, body com detalhes carregado quando preciso) — não embutido em system_prompt.

6. **Tamanho do hook (~34KB)**: Se usa `additionalContext` padrão, está 3.4× acima do limite documentado (10K chars). Precisa verificar implementação real.

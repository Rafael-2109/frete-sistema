# C1 — Pesquisa: Best Practices Anthropic de Context Engineering
# Subagente: C1 (pesquisa)
# Data: 09/06/2026

---

## FONTES PRIMÁRIAS CONSULTADAS

1. Anthropic Engineering: "Effective context engineering for AI agents"
   URL: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

2. Anthropic Engineering: "Writing effective tools for AI agents"
   URL: https://www.anthropic.com/engineering/writing-tools-for-agents

3. Anthropic Engineering: "Effective harnesses for long-running agents"
   URL: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

4. Anthropic Engineering: "Equipping agents for the real world with Agent Skills"
   URL: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

5. Anthropic Engineering: "Building Effective AI Agents"
   URL: https://www.anthropic.com/research/building-effective-agents

6. Anthropic Docs: "Prompting best practices / Long context tips"
   URL: https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/long-context-tips

7. Anthropic Docs: "Prompt caching"
   URL: https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching

8. Claude Code Docs: "Best practices for Claude Code"
   URL: https://code.claude.com/docs/en/best-practices

9. Literatura científica: Liu et al. (2023) "Lost in the Middle: How Language Models Use Long Contexts"
   Sumário via: https://dev.to/thousand_miles_ai/the-lost-in-the-middle-problem-why-llms-ignore-the-middle-of-your-context-window-3al2

---

## PRINCÍPIOS NUMERADOS (P-1..P-20)

---

### P-1 — CONTEXTO É RECURSO FINITO, NÃO LOUSA EM BRANCO

**Fonte:** "Effective context engineering for AI agents" (anthropic.com/engineering)

**Citação direta:**
> "LLMs have an 'attention budget' that they draw on when parsing large volumes of context."
> "Context is a precious, finite resource requiring thoughtful curation at each inference step."
> "Find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome."

**Mecanismo subjacente:**
A atenção em transformers tem custo n² — quanto mais tokens, mais pares de atenção competem. Isso cria retornos decrescentes e "context rot": conforme tokens aumentam, a capacidade de recall degrada em todos os modelos (alguns com degradação mais suave, mas nenhum imune).

**Aplicação ao nosso boot de 5 camadas:**
- O hook dinâmico (~34KB / turno) é o componente mais volátil e mais denso. A pergunta operacional correta não é "o que posso adicionar?" mas "o que não está ganhando sua fatia de atenção?"
- A acreção documentada (407→862 linhas em 6 semanas no system_prompt) é sintoma direto de violação deste princípio.
- Cada bloco `<world_model>`, `<skill_hints>` e `<stale_empresa>` que Rafael marcou como ruído ocupa atenção que poderia ir para `<constitutional_hierarchy>` e `operational_directives`.

---

### P-2 — MÍNIMO SUFICIENTE: PROMPT COMEÇA PEQUENO E CRESCE POR FALHAS OBSERVADAS

**Fonte:** "Effective context engineering for AI agents"

**Citação direta:**
> "Aim for 'the minimal set of information that fully outlines your expected behavior.' Start with minimal prompts on capable models, then iteratively add instructions based on failure modes."

**Aplicação ao nosso boot:**
- O oposto está acontecendo: crescimento por acreção de regras preventivas, não por falhas medidas. O achado M2 do agente ("cada regra tem uma cicatriz") é verdade para regras OLD — mas novas regras devem ser gated por evidência de falha (eval, judge, friction), não por precaução.
- O `stale_empresa` (33 memórias sem revisão há 60+ dias) e o `improvement_responses` injetados no boot são exemplos de adição que nunca foi retirada após servir seu propósito.
- Governança proposta: qualquer adição ao boot passa por "que falha específica isso resolve?" e ganha sunset automático se não houver incidente em N sessões.

---

### P-3 — ALTITUDE CERTA: NEM RÍGIDO NEM VAGO

**Fonte:** "Effective context engineering for AI agents"

**Citação direta:**
> "Avoid two extremes: hardcoded brittle logic or vague, high-level guidance. The optimal prompt should be 'specific enough to guide behavior effectively, yet flexible enough to provide the model with strong heuristics.'"

**Aplicação ao nosso boot:**
- `<constitutional_hierarchy>` está na altitude certa: princípio + exemplo trabalhado + hierarquia (L1-L4). Proteger.
- `<operational_directives>` está na altitude certa: WHEN/DO com contexto específico. Proteger.
- `<world_model>` está na altitude errada (baixa demais / trivial): lista de entidades genéricas ([cliente] ELAINE, [produto] ODOO) sem contexto de quando usar. É baixa altitude sem valor heurístico — ruído (confirma R-1 de Rafael).
- `<skill_hints>` está na altitude errada (prescrição sem heurística): lista pré-computada de skills sem explicar por que são relevantes para a query atual. Não ensina o modelo a raciocinar sobre roteamento.

---

### P-4 — JUST-IN-TIME CONTEXT: LEVE IDENTIFICADORES, NÃO DADOS COMPLETOS

**Fonte:** "Effective context engineering for AI agents"

**Citação direta:**
> "Instead of pre-loading all relevant data, agents maintain 'lightweight identifiers (file paths, stored queries, web links, etc.)' and dynamically load data at runtime."
> "This approach mirrors human cognition and enables 'progressive disclosure—in other words, allows agents to incrementally discover relevant context through exploration.'"

**Trade-off registrado pela própria Anthropic:**
> "Runtime exploration is slower than pre-computed retrieval and requires thoughtful tool design and heuristics."

**Aplicação ao nosso boot:**
- O CLAUDE.md (~16KB) carregado inteiramente como Seção 4 viola este princípio: a maioria das seções (Design System/CSS, TECH STACK, MIGRATIONS, Quick Start, Worker RQ) é dev-only e nunca será usada pelo agente web. Deveria ser injetado apenas o ponteiro + as seções relevantes.
- As `<session_summaries>` (5 sessões completas) podem ser compactadas mais agressivamente — o agente precisa do contexto das pendências, não de um relato detalhado de cada sessão. Ponteiros + pendências = suficiente.
- `<skill_hints>` deveria ser substituído por heurística de roteamento just-in-time (o agente lê o SKILL.md sob demanda via progressive disclosure).

---

### P-5 — PROGRESSIVE DISCLOSURE EM SKILLS: 3 NÍVEIS HIERÁRQUICOS

**Fonte:** "Equipping agents for the real world with Agent Skills" (anthropic.com/engineering)

**Citação direta:**
> "Level 1 (Metadata): The YAML frontmatter in SKILL.md contains name and description, which are 'loaded into its system prompt at startup.' This provides 'just enough information for Claude to know when each skill should be used.'"
> "Level 2 (Core Content): The main body of SKILL.md loads fully into context 'if Claude thinks the skill is relevant to the current task.'"
> "Level 3+ (Linked Files): Additional bundled files referenced from SKILL.md are 'navigated and discovered only as needed,' allowing context to be 'effectively unbounded' without consuming tokens unnecessarily."

**Gatilho da skill:**
> "Skills activate when Claude 'invokes a Bash tool to read the contents' of the skill's SKILL.md file."

**Aplicação ao nosso boot:**
- O frontmatter atual (28 skills × ~1-3 linhas de description) é Level 1 correto — manter.
- O problema identificado por Rafael (R-2): redundância entre o R7 do system_prompt (WHEN TO USE dentro de rules), o ROUTING_SKILLS.md referenciado, e o frontmatter das skills. Esses 3 lugares descrevem a mesma coisa em altitude diferente. A solução: Level 1 = frontmatter conciso (trigger + escopo), Level 2 = SKILL.md com WHEN/DO/examples, Level 3 = scripts + referências. O R7 do system_prompt deve ter apenas o critério de decisão de roteamento, não exemplos específicos de skills.
- Skills dev-only (R-3: consultando-sentry, diagnosticando-banco, gerindo-agente, padronizando-docs) não devem aparecer no Level 1 do agente web — suas descriptions ocupam tokens de atenção em toda sessão.
- Descrições longas/near-duplicate entre skills devem ser comprimidas (C-6 do agente).

---

### P-6 — DESCRIÇÕES DE TOOLS: INVESTIR NO MESMO NÍVEL QUE NO PROMPT

**Fonte:** "Writing effective tools for AI agents" + "Building Effective Agents"

**Citações diretas:**
> "Even small refinements to tool descriptions can yield dramatic improvements."
> "Describe the tool as you would to a new team member, making implicit context explicit."
> "A good tool definition often includes example usage, edge cases, input format requirements, and clear boundaries from other tools."
> "If engineers can't definitively select between tools, agents won't either."

**Aplicação ao nosso boot:**
- As 12 tools always-loaded não foram auditadas neste estudo, mas o princípio se aplica: cada tool deve ter description que torna óbvio QUANDO usá-la e QUANDO NÃO usá-la.
- A sobreposição entre `lendo-arquivos` e `lendo-documentos` (R-4 de Rafael) é um caso clássico deste princípio violado: se o humano não consegue distinguir, o agente também não conseguirá.
- Tools com nomes ambíguos ou escopo superposto aumentam latência (hesitação) e taxa de erro de roteamento.

---

### P-7 — FERRAMENTAS CONSOLIDADAS > FERRAMENTAS GRANULARES

**Fonte:** "Writing effective tools for AI agents"

**Citação direta:**
> "Tools should handle multiple discrete operations. Examples include implementing a schedule_event tool instead of separate list_users, list_events, and create_event tools."
> "More tools don't always lead to better outcomes. Focus on 'a few thoughtful tools targeting specific high-impact workflows.'"

**Aplicação ao nosso boot:**
- Isso confirma a sugestão de Rafael (R-4): unificar `lendo-arquivos` + `lendo-documentos` em uma skill única com parâmetros para tipo de conteúdo.
- Mais amplamente: o conjunto de 28 skills expostas deve ser revisado periodicamente. Skills raramente usadas devem ser removidas do conjunto always-available ou movidas para deferred.

---

### P-8 — FEW-SHOT BEATS "LISTA DE CASOS DE BORDA"

**Fonte:** "Effective context engineering for AI agents" + Anthropic docs gerais

**Citação direta:**
> "Rather than 'a laundry list of edge cases into a prompt,' curate 'diverse, canonical examples that effectively portray the expected behavior.'"
> "For LLMs, 'examples are the pictures worth a thousand words.'"
> "Include 3–5 examples for best results."

**Aplicação ao nosso boot:**
- O achado A4 do agente ("sem few-shot nas tarefas de alta frequência") tem suporte sólido nesta literatura. Adicionar 1 par bom/ruim para as 2 tarefas top-frequência (separação + frete) vai além de uma regra nova — é mostrar ao modelo o padrão de output esperado.
- Importante: few-shots devem ser colocados no nível correto da hierarquia. Para tarefas recorrentes com padrão estável, o SKILL.md Level 2 é o lugar certo, não o system_prompt. Isso respeita o princípio de just-in-time context.
- Os `<why>` blocos no system_prompt (M1 do agente) funcionam como "explicação narrativa" que se aproxima de few-shot — manter a lógica motivacional, não apenas a regra.

---

### P-9 — POSIÇÃO IMPORTA: PRIMAZIA E RECÊNCIA (LOST IN THE MIDDLE)

**Fonte:** Liu et al. (2023) "Lost in the Middle: How Language Models Use Long Contexts"
Sumário: https://dev.to/thousand_miles_ai/the-lost-in-the-middle-problem

**Citação direta (sumário):**
> "Language models pay the most attention to the beginning and end of their context, and systematically under-attend to the middle."
> "Performance is highest when the answer is at the very beginning or very end of the context, and it drops when the answer sits in the middle."
> "LLMs exhibit a U-shaped performance curve: greater attention to beginning and end, a dead zone in the middle."

**Mecanismo:**
- Causal attention masking: tokens iniciais acumulam mais peso de atenção.
- RoPE positional encoding decay: tokens distantes de ambas as extremidades têm sinal reduzido.
- Ainda válido em 2026: nenhum modelo eliminou esse bias estrutural completamente.

**Aplicação ao nosso boot de 5 camadas:**
- O hook dinâmico (~34KB) é a última camada, mas dentro do hook, a ordem interna importa muito. O agente identificou (D3): `<pendencias>` e `<user_rules>` no meio de 34KB perdem atenção. Eles devem estar no INÍCIO ou no FIM do hook — preferencialmente logo antes (ou depois) da mensagem do usuário.
- `<operational_directives>` (regras críticas de operação) está no final do hook (linhas 1999+) — boa posição (recência). Confirma que essa parte do design está alinhada ao princípio.
- `<world_model>` e `<skill_hints>` estão no final do hook (~2065-2085) — ruído no slot de recência. Confirmando R-1 de Rafael: devem ser removidos, pois ocupam o slot de maior atenção com conteúdo de menor valor.
- Dentro do system_prompt: as regras mais críticas (L1 hierarquia, R0 memory, R3 confirmação) devem estar no início — verificar se estão.
- Documentação longa (CLAUDE.md ~16KB, Seção 4) sendo injetada entre o system_prompt e o hook é um risco de "zona morta" de atenção para o conteúdo mais crítico do hook.

---

### P-10 — CONTEÚDO ESTÁTICO PRIMEIRO: ORDEM tools → system → messages PARA CACHE

**Fonte:** "Prompt caching" (platform.claude.com/docs)

**Citação direta:**
> "Cache prefixes are created in the following order: tools, system, then messages."
> "Place static content (tool definitions, system instructions, background information, large contexts, or frequent tool definitions) at the beginning of your prompt."
> "Place the breakpoint on the last block that stays identical across requests."

**Regra crítica:**
> "Cache writes happen only at your breakpoint. If that block changes (timestamps, per-request context, the incoming message), the prefix hash never matches."

**Aplicação ao nosso boot:**
- A arquitetura atual (1a preset + 1b system_prompt + 1c empresa_briefing = estáticos; depois skills + tools; depois CLAUDE.md; depois hook dinâmico) é conceitualmente correta: o system prompt estático fica antes.
- PROBLEMA: o CLAUDE.md (Seção 4) é injetado via `setting_sources` e pode ter conteúdo variável (ex: se for editado com frequência). Se mudar entre sessões, invalida o cache de tudo que vem depois.
- O hook (Seção 5) é 100% dinâmico por design — correto colocá-lo no final.
- `<stale_empresa count="33">` no hook introuz dados que mudam turno a turno. Se isso quebra o cache do hook, não há problema (hook é sempre dinâmico). Mas se por algum motivo partes do hook fossem candidatas ao cache (ex: `<operational_directives>` que raramente mudam), seria necessário separar conteúdo estável de volátil dentro do hook.
- Recomendação: auditar quais partes do hook são estáveis o suficiente para cacheamento separado (directives, user_profile) vs. voláteis (sessions, pendências, world_model).

---

### P-11 — COMPACTAÇÃO: SUMARIZE ANTES DE LOTAR; PRESERVE DECISÕES ARQUITETURAIS

**Fonte:** "Effective context engineering for AI agents" + "Effective harnesses for long-running agents"

**Citação direta:**
> "Summarize and compress message history before context window limits, preserving 'architectural decisions, unresolved bugs, and implementation details' while discarding redundant outputs."
> "Start by maximizing recall, then improve precision."
> "Tool result clearing is identified as 'one of the safest lightest touch forms of compaction.'"

**Aplicação ao nosso boot:**
- As 5 sessões recentes no hook são um caso de compactação: cada resumo tem ~3-4 linhas que capturam essência da sessão. Isso está correto.
- Mas o hook também injeta memórias empresa completas (algumas muito longas — ex: a armadilha "IBGE float" com 27 linhas de XML aninhado). O princípio de compactação aplicado às memórias: comprimir narrativa, preservar WHEN/DO, eliminar contexto de descuberta que já não agrega.
- As `<improvement_responses>` no hook (stale_empresa + 2 respostas do Claude Code) são claro candidato a compactação: são estado de manutenção, não operação. Se o conteúdo for relevante, condensar em uma linha.

---

### P-12 — NOTA ESTRUTURADA COMO MEMÓRIA EXTERNA PERSISTENTE

**Fonte:** "Effective context engineering for AI agents"

**Citação direta:**
> "Agents maintain persistent external memory (files, notes) pulled back into context later."
> "This enables tracking across complex tasks without exhausting the context window."

**Aplicação ao nosso boot:**
- O sistema de memórias persistentes (MCP tools, banco PostgreSQL) é exatamente este padrão. Correto.
- PROBLEMA identificado por Rafael (RP-2, R-6): a injeção de memórias não é contextual — "o que a forma de excluir a fatura 161-9 tem a ver com solicitar o contexto inicial?". O princípio não é "injete todas as memórias", é "injete a nota que resolve a tarefa atual".
- Proposta derivada do princípio: filtrar memórias por intenção do turno (C5 do agente). A sessão que pediu o contexto de boot deveria receber memórias sobre arquitetura/tokens, não sobre fatura CarVia.
- Adicionar proveniência nas memórias (RP-2): saber DE QUAL SESSÃO veio a memória permite ao agente acessar contexto raw quando a memória for incompleta — isso é o padrão "ponteiro para fonte autoritativa".

---

### P-13 — SUBAGENTES: CONTEXTO LIMPO PARA TAREFA FOCADA

**Fonte:** "Effective context engineering for AI agents" + "Claude Code best practices"

**Citação direta:**
> "Specialized sub-agents handle focused tasks with clean context windows while returning condensed summaries (1,000-2,000 tokens)."
> "Since context is your fundamental constraint, subagents are one of the most powerful tools available. When Claude researches a codebase it reads lots of files, all of which consume your context. Subagents run in separate context windows and report back summaries."
> "Achieve 'clear separation of concerns' for complex research and analysis."

**Aplicação ao nosso boot:**
- Isso valida a arquitetura de subagentes do sistema (analista-carteira, gestor-carvia, etc.) — cada um tem contexto limpo + tarefa focada.
- CRÍTICO: o achado do agente (rule de user_rules): "subagentes NUNCA herdam system_prompt do pai". Isso é um fato arquitetural do Agent SDK que o agente já aprendeu. Está correto.
- Para o bootstrap: o system_prompt não precisa incluir toda a documentação dos subagentes (R-9 Rafael: lista incompleta e duplicada no system_prompt + CLAUDE.md). A lista canônica deve estar em um ÚNICO lugar (CLAUDE.md ou uma reference file) com ponteiro no system_prompt.

---

### P-14 — CLAUDE.md: CURTO, APENAS O QUE CLAUDE NÃO INFERE DO CÓDIGO

**Fonte:** "Claude Code best practices" (code.claude.com/docs)

**Citações diretas:**
> "Keep it short and human-readable."
> "Only include things that apply broadly. For domain knowledge or workflows that are only relevant sometimes, use skills instead."
> "For each line, ask: 'Would removing this cause Claude to make mistakes?' If not, cut it."
> "Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"
> "If Claude keeps doing something you don't want despite having a rule against it, the file is probably too long and the rule is getting lost."

**Tabela do que incluir vs. excluir:**
| Incluir | Excluir |
|---------|---------|
| Bash commands que Claude não pode adivinhar | O que Claude infere lendo o código |
| Regras de estilo que diferem do default | Convenções de linguagem já conhecidas |
| Instruções de teste | Documentação detalhada de API (link em vez) |
| Decisões arquiteturais específicas do projeto | Informações que mudam frequentemente |
| Gotchas não-óbvios do ambiente | Explicações longas ou tutoriais |
| | Descrições arquivo-por-arquivo do codebase |
| | Práticas auto-evidentes ("escreva código limpo") |

**Aplicação ao nosso boot:**
- O CLAUDE.md raiz atual (~16KB) viola múltiplas exclusões da tabela:
  - TECH STACK (dev): list de versões que Claude não precisa em runtime
  - Design System / CSS (dev-only): regras CSS de modulo que o agente web não usa
  - MIGRATIONS (dev-only): instruções para Claude Code dev, não para agente web
  - Quick Start (dev): comandos locais
  - SUBAGENTES: duplicado do system_prompt (R-9 Rafael)
- O que DEVE ficar no CLAUDE.md para o agente web: ÍNDICE DE REFERÊNCIAS (R-5 Rafael marcou como "muito bom"), CAMINHOS DO SISTEMA, GOTCHAS de campos críticos (qtd_saldo, company_id), REGRAS UNIVERSAIS de timezone e fontes de dados.
- Solução: dividir CLAUDE.md em 2 versões ou usar CLAUDE.md hierárquico (Claude Code lê ambos, agente web lê apenas a versão web-friendly).

---

### P-15 — INFLAÇÃO DE PRIORIDADE: 3 NÍVEIS REAIS, NÃO 6 RÓTULOS

**Fonte:** Insights de "Effective context engineering" + achado C2 do agente (confirmado pela doc)

**Princípio Anthropic (via Claude Code docs):**
> "You can tune instructions by adding emphasis (e.g., 'IMPORTANT' or 'YOU MUST') to improve adherence."

**Mas o complemento crítico (via effective context engineering):**
> "Aim for the minimal set of information that fully outlines your expected behavior."

**Evidência no nosso boot:**
- Achado C2 (agente, alta confiança): 6 rótulos de "máximo" coexistindo: `inviolable`, `critical`, `mandatory`, `L1`, `L2`, `OBRIGATÓRIO`
- Quando tudo é crítico, nada é crítico. A atenção do modelo (budget finito) trata todos iguais.

**Proposta derivada:**
- Colapsar para 3 níveis: INVIOLÁVEL (L1/L2: segurança + ética), OBRIGATÓRIO (L3: regras de negócio confirmadas), ORIENTAÇÃO (L4: utilidade, formato, preferências)
- Qualquer regra nova que queira entrar em INVIOLÁVEL precisa de evidência de incidente irreversível.

---

### P-16 — CONTEXTO VIVO: ESTADO DO SISTEMA NO BOOT (HEALTH CHECK)

**Fonte:** Achado A2 do agente + padrões de harness (effective-harnesses-for-long-running-agents)

**Citação direta (harnesses):**
> "Agents must work in discrete sessions, and each new session begins with no memory of what came before."
> Three preservation mechanisms: progress documentation, feature tracking, version control.

**Princípio derivado:**
Um agente que começa uma sessão sem saber o estado dos sistemas dependentes (Odoo online/offline? Redis saturado? Sentry errors?) vai descobrir falhas apenas ao falhar — latência de percepção de problemas.

**Aplicação ao nosso boot:**
- A2 do agente: "sem flag de saúde no boot — descubro que o Odoo caiu falhando uma chamada"
- Solução: expor estado do Circuit Breaker como metadado no hook. Não precisa ser uma query nova — se o harness já tem circuit breaker, o estado já existe. Custo: S (pequena adição ao hook).
- Diferente de A1 (painel de contagens operacionais opt-in): saúde dos sistemas é invariante útil que raramente muda e custa pouca atenção (uma linha por sistema).

---

### P-17 — REDUNDÂNCIA CONTROLADA: 1 FONTE CANÔNICA + PONTEIROS

**Fonte:** Princípio derivado de múltiplas fontes Anthropic sobre tool design + CLAUDE.md design

**Princípio:**
Redundância intencional para gotchas críticos (2-3 lugares) é defensável e até recomendada para garantir que a regra "não se perca". Mas redundância não intencional (a mesma regra aparece em 3 lugares porque 3 sessões de dev a adicionaram) dilui atenção sem benefício.

**Evidência no nosso boot:**
- C1 (agente, alta confiança): fronteira PRE/POS repetida em cada description de skill (desnecessário — o body do SKILL.md já tem essa lógica)
- R-2 (Rafael): 3 lugares descrevendo roteamento de skills (R7 system_prompt, ROUTING_SKILLS.md referenciado, frontmatter das 28 skills)
- R-5 (Rafael): SUBAGENTES no system_prompt E no CLAUDE.md

**Aplicação:**
- Identificar o nível correto para cada informação na hierarquia (system_prompt / SKILL.md / reference file)
- Uma vez identificado, remover das outras instâncias e substituir por ponteiro: "ver [arquivo/seção]"

---

### P-18 — SEPARAÇÃO DE OPERAÇÃO vs. MANUTENÇÃO/GOVERNANÇA

**Fonte:** Achado C3 do agente (confiança alta) + princípio de "separation of concerns"

**Princípio:**
O contexto de boot operacional deve conter apenas o que é necessário para responder ao próximo pedido operacional. Conteúdo de governança do agente (dashboards de melhoria, stale counts, improvement_responses) é metadado do sistema, não instrução operacional.

**Evidência no nosso boot:**
- `<stale_empresa count="33">`: é sinal para o Claude Code dev, não para o agente web operacional
- `<improvement_responses count="2">`: são feeds de auditoria de bugs, não instruções de operação
- Ambos estão no hook principal, injetados em TODO boot operacional

**Aplicação:**
- C3 do agente: mover stale_empresa + improvement_responses para a view do gerindo-agente
- Zero regressão operacional esperada (o agente confirmou isso com alta confiança: "o pedido é 'tem pedido do Atacadão?', eles são peso morto")

---

### P-19 — MEMÓRIAS: FILTRAR POR INTENÇÃO, ADICIONAR PROVENIÊNCIA

**Fonte:** RP-2 de Rafael + princípio de just-in-time context (P-4) + princípio de minimal information (P-2)

**Princípio:**
A memória útil é a que muda o comportamento para a tarefa atual. Uma memória de "fatura 161-9" injetada durante uma sessão de análise de contexto de boot é ruído — não porque seja errada, mas porque não é relevante para a tarefa.

**Evidência no nosso boot:**
- Hook injeta 8+ memórias de empresa de domínios variados (comercial, expedição, integração, logística, financeiro) sem filtragem por intenção do turno
- Rafael explicou (RP-2): quando for tratar de fatura, o few-shot se aplica — mas trazer o few-shot da fatura 161-9 para uma sessão de análise arquitetural é ruído

**Aplicação:**
- C5 do agente: filtrar memórias por intent do turno — classificar a intenção antes de decidir quais memórias injetar
- RP-2 de Rafael: adicionar proveniência nas memórias (session_id de origem) para que o agente possa acessar contexto raw quando a memória for incompleta ou incerta
- A6 do agente: adicionar metadado last_confirmed/confidence — memórias antigas sem confirmação devem ser tratadas com peso menor que correções recentes

---

### P-20 — DADOS LONGOS NO TOPO DO CONTEXTO; QUERY/INSTRUÇÃO NO FINAL

**Fonte:** "Prompting best practices / Long context tips" (platform.claude.com)

**Citação direta:**
> "Put longform data at the top: Place your long documents and inputs near the top of your prompt, above your query, instructions, and examples."
> "Queries at the end can improve response quality by up to 30% in tests, especially with complex, multi-document inputs."

**Combinação com P-9 (Lost in the Middle):**
- Dados longos no TOPO: aproveitam o efeito de primazia (melhor recall)
- Instrução/query no FINAL: aproveitam o efeito de recência (maior atenção no último slot antes de gerar)
- Este é o padrão inverso do que a intuição sugere (colocar instrução antes dos dados)

**Aplicação ao nosso boot:**
- O system prompt tem o role + hierarchia no início (positivo: primazia para o que define o comportamento base)
- O hook dinâmico tem `<session_context>` (data, usuário) no início — correto (dado contextual breve)
- O hook tem `<operational_directives>` no final — correto (recência para regras críticas de operação)
- PROBLEMA: `<skill_hints>` e `<world_model>` estão APÓS `<operational_directives>` no final do hook (linhas 2065-2085). Isso coloca lixo/ruído no slot de recência, deslocando as diretivas críticas para a "zona morta" relativa. Isso agrava o problema já identificado por Rafael (R-1) e pelo agente (D3).

---

## SÍNTESE: MAPA DE APLICAÇÃO AO BOOT DE 5 CAMADAS

### Camada 1 — System Prompt (3 arquivos estáticos)

| Bloco | Situação atual | Princípio violado | Ação |
|-------|---------------|-------------------|------|
| `<constitutional_hierarchy>` L1-L4 | Bom: altitude certa, exemplo trabalhado | — | MANTER (M2 do agente) |
| Regras R0-R12 | Bom: cada uma com `<why>` | — | MANTER (M1 do agente) |
| `<scope>` can/cannot | Adequado | — | MANTER |
| `<language_policy>` | Adequado | — | MANTER |
| Inflação de rótulos de prioridade | Problemático | P-15 | COLAPSAR para 3 níveis |
| Lista de subagentes | Duplicada em CLAUDE.md | P-17 | 1 fonte canônica |

### Camada 2 — Skills (28 expostas no frontmatter)

| Bloco | Situação atual | Princípio violado | Ação |
|-------|---------------|-------------------|------|
| Frontmatter description (Level 1) | Adequado conceitualmente | P-5 | MANTER estrutura, COMPRIMIR conteúdo redundante |
| Skills dev-only expostas ao agente web | Ruído de atenção | P-5 (nível errado) | REMOVER do conjunto agente-web (R-3) |
| Redundância PRE/POS em descriptions | Desnecessária | P-17 | REMOVER das descriptions; fica no body SKILL.md |
| `lendo-arquivos` vs `lendo-documentos` | Overlap ambíguo | P-6, P-7 | UNIFICAR (R-4) |

### Camada 3 — Tools (12 always-loaded + 47 deferred)

| Bloco | Situação atual | Princípio violado | Ação |
|-------|---------------|-------------------|------|
| Always-loaded tools | Não auditadas em profundidade | P-6 | Auditar descriptions |
| Deferred tools | Padrão correto (ToolSearch) | P-4 | MANTER (just-in-time) |

### Camada 4 — CLAUDE.md (~16KB)

| Bloco | Situação atual | Princípio violado | Ação |
|-------|---------------|-------------------|------|
| TECH STACK, CSS, MIGRATIONS, Quick Start | Dev-only | P-14 | REMOVER do contexto agente-web |
| ÍNDICE DE REFERÊNCIAS | Valioso para ambos | — | MANTER |
| CAMINHOS DO SISTEMA | Valioso para agente web | — | MANTER |
| SUBAGENTES (lista) | Duplicada no system_prompt | P-17 | 1 fonte canônica |
| DADOS e REGRAS UNIVERSAIS | Alguns aplicáveis ao agente | P-3, P-14 | FILTRAR: manter só o que o agente usa |

### Camada 5 — Hook Dinâmico (~34KB / turno)

| Bloco | Situação atual | Princípio violado | Ação |
|-------|---------------|-------------------|------|
| `<session_context>` (data, usuário) | Bom — início do hook | P-20 | MANTER |
| `<user_rules>` | Bom conteúdo, posição problemática (meio) | P-9 | MOVER para final do hook, logo antes do `</session_context>` |
| `<user_memories>` (6+ blocos) | Volume sem filtro de intent | P-4, P-12, P-19 | FILTRAR por intenção do turno; adicionar proveniência |
| `<recent_sessions>` (5 sessões) | Adequado como compactação | P-11 | MANTER estrutura; vigilar tamanho individual |
| `<pendencias_acumuladas>` | Crítico para continuidade; posição correta (após sessões) | P-9 | MANTER; verificar posicionamento próximo ao final |
| `<stale_empresa>` | Governança, não operação | P-18 | REMOVER do boot operacional → view gerindo-agente |
| `<improvement_responses>` | Governança, não operação | P-18 | REMOVER do boot operacional → view gerindo-agente |
| `<operational_directives>` | Bom: final do hook = recência | P-9, P-20 | MANTER posição |
| `<routing_context advisory>` com `<preferred_skills>` | Questionável (R-7) | P-3 (altitude errada) | VERIFICAR uso real; se baixo → REMOVER |
| `<active_traps>` dentro de routing_context | Bom conteúdo, altitude correta | — | MANTER mas auditar se sobreposição com operational_directives |
| `<debug_mode_context>` + `<sql_admin_context>` | Gera ruído para não-admins | P-2, R-8 | Condicional: injetar SOMENTE se usuário é admin |
| `<skill_hints priority="advisory">` | Ruído no slot de recência | P-1, P-3, P-9, R-1 | REMOVER (confirmado por Rafael) |
| `<world_model priority="advisory">` | Ruído no slot de recência | P-1, P-3, P-9, R-1 | REMOVER (confirmado por Rafael) |

---

## LACUNAS (NÃO ENCONTREI / NÃO VERIFICADO)

1. **Tamanho exato de cada bloco do hook em tokens** — apenas KB aproximado disponível; auditoria por tokens recomendada
2. **Taxa de cache hit atual** — não verificado qual breakpoint está sendo usado e qual a eficiência do caching
3. **Análise de uso real das skills dev-only** (R-7 de Rafael) — requer dados de produção de routing
4. **Conteúdo dos 47 tools deferred** — verificação de overlaps entre tools não foi possível neste estudo
5. **Impacto quantitativo de cada bloco no judge score** — requer ablação experimental (A/B)
6. **Posição exata de `<user_rules>` vs `<operational_directives>` dentro do hook** — lido nas linhas 1827-1840 vs 1999-2031 — confirmado que user_rules fica no início do hook (antes das memórias), não no meio nem no final. Isso é subótimo segundo P-9 (deveria estar no final).

---

## FONTES COMPLETAS (PARA REFERÊNCIA)

- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://www.anthropic.com/engineering/writing-tools-for-agents
- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://www.anthropic.com/research/building-effective-agents
- https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/long-context-tips
- https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching
- https://code.claude.com/docs/en/best-practices
- https://dev.to/thousand_miles_ai/the-lost-in-the-middle-problem-why-llms-ignore-the-middle-of-your-context-window-3al2

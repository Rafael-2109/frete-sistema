# Separação Estrutural de Tools, Skills e Prompts no Claude Agent SDK

**A mudança que você descreve mapeia para uma atualização específica da v0.1.49 no `AgentDefinition`** — não uma migração para fora do system prompt, mas uma expansão do escopo de capacidades por subagente. Na v0.1.49 (20 de março de 2026), o Claude Agent SDK adicionou os campos `skills`, `memory` e `mcpServers` ao dataclass `AgentDefinition` (PR #684), permitindo que subagentes carreguem suas próprias configurações de ferramentas e conhecimento. Isso reflete uma filosofia de design mais ampla da Anthropic: **capacidades são dados estruturados gerenciados pelo runtime, não texto livre embutido em prompts**. A distinção importa porque habilita progressive disclosure, prompt caching, tool search dinâmico e roteamento de permissões — nada disso funciona se as ferramentas forem apenas texto no prompt.

## O que de fato mudou na v0.1.49

O pacote oficial é **`claude-agent-sdk`** no PyPI (repositório: `anthropics/claude-agent-sdk-python`). A superfície de configuração principal é `ClaudeAgentOptions`, e subagentes são definidos via `AgentDefinition`.

Antes da v0.1.49, `AgentDefinition` tinha quatro campos: `description`, `prompt`, `tools` e `model`. A v0.1.49 expandiu para incluir **`skills`**, **`memory`** e **`mcpServers`**, alinhando definições programáticas de subagentes com o conjunto completo de opções já disponíveis no frontmatter de arquivos de subagente. O parâmetro `mcp_servers` no `ClaudeAgentOptions` em si já existia desde a v0.0.22, quando servidores MCP in-process customizados foram introduzidos. Skills sempre foram artefatos de filesystem (arquivos `.claude/skills/SKILL.md`) desde sua criação — nunca foram parâmetros de construtor na classe de opções de nível superior. O que a v0.1.49 fez foi permitir que subagentes **referenciem** skills e carreguem suas próprias configurações de MCP server, criando escopo de capacidade verdadeiramente por agente.

A versão 0.1.50, lançada no mesmo dia, foi um follow-up menor adicionando `tag` e `created_at` ao `SDKSessionInfo` e atualizando a CLI bundled para v2.1.81.

## Progressive disclosure mantém a context window enxuta

A justificativa mais explicitamente documentada para essa arquitetura vem do blog de engenharia da Anthropic de outubro de 2025 sobre Agent Skills. O design usa **progressive disclosure em três níveis**: na inicialização, apenas nomes de skills e descrições de uma linha (frontmatter YAML) são injetados no system prompt. Quando Claude determina que uma skill é relevante durante a execução, ele lê o conteúdo completo do `SKILL.md` para o contexto. Arquivos referenciados adicionais — scripts, templates, dados — carregam somente quando as instruções da skill os invocam.

Essa arquitetura significa que a quantidade de conhecimento empacotada numa skill é **efetivamente ilimitada**, já que reside no filesystem e não no prompt. Um agente pode ter centenas de skills instaladas mas carregar apenas uma ou duas por tarefa. A adição de `skills` ao `AgentDefinition` na v0.1.49 estende esse padrão para subagentes: um subagente de code review pode carregar suas próprias skills enquanto um subagente de deployment carrega skills completamente diferentes, cada um carregando apenas o necessário em sua context window isolada.

## Prompt caching exige separação estrutural

O prompt caching da Anthropic processa componentes da requisição API numa ordem fixa: **tools → system message → message history**. Cache hits custam apenas **10% do preço base de input tokens**, tornando a estabilidade do cache extremamente valiosa. Essa ordenação cria um incentivo arquitetural direto para manter definições de ferramentas separadas dos system prompts.

Quando definições de ferramentas são parâmetros de dados estruturados, o SDK pode garantir que apareçam como prefixos estáveis e cacheáveis. Se ferramentas fossem embutidas como texto livre dentro do system prompt, qualquer mudança de ferramenta invalidaria o cache do system prompt inteiro. Mantendo a separação, o SDK alcança lifetimes de cache independentes: definições de ferramentas permanecem em cache mesmo quando o system prompt muda, e o system prompt permanece em cache mesmo quando a conversa cresce. O blog de engenharia da Anthropic sobre advanced tool use confirma isso explicitamente: ferramentas deferidas (via Tool Search) não quebram o prompt caching porque são excluídas do prompt inicial — assim as definições de system prompt e core tools permanecem cacheáveis.

## Tool loading dinâmico resolve o problema de context bloat

A Anthropic observou definições de ferramentas consumindo **134K tokens** antes de otimização em deployments reais. O SDK endereça isso através do Tool Search Tool, que se auto-ativa quando descrições de MCP tools excedem **10% da context window**. MCP tools são marcadas com `defer_loading: true`, e Claude as descobre via interface de busca somente quando necessário.

Esse mecanismo requer fundamentalmente que ferramentas sejam dados estruturados legíveis por máquina, não texto de prompt. O runtime precisa rastrear programaticamente estados de ferramentas (loaded, deferred, discovered), parsear e indexar definições de ferramentas para busca, e injetar seletivamente definições no contexto no momento certo. O parâmetro `mcp_servers` dá ao SDK essa superfície de controle. Com o `mcpServers` por subagente da v0.1.49, isso se estende ainda mais: um subagente lidando com queries de banco de dados pode ter MCP tools de banco carregadas enquanto o agente pai nunca as vê, prevenindo context bloat no thread principal. Uma issue no GitHub do Claude Code (#14722) destacou exatamente esse pain point: habilitar um MCP de Linear causava bloat de contexto no thread principal mesmo quando Linear não estava sendo usado.

## Roteamento estruturado habilita controle granular de permissões

MCP tools seguem uma convenção de nomenclatura estrita: `mcp__<server_name>__<tool_name>`. Esse padrão estruturado habilita capacidades que seriam impossíveis com declarações de ferramentas em texto livre:

- **Permissões wildcard**: `"mcp__github__*"` aprova todas as ferramentas do GitHub
- **Controle granular**: `"mcp__db__query"` aprova somente a ferramenta de query de leitura
- **Gerenciamento por servidor**: Servidores MCP inteiros podem ser adicionados ou removidos em runtime via `add_mcp_server()` e `remove_mcp_server()` (adicionados na v0.1.46)
- **Escopo por subagente**: Cada `AgentDefinition` pode especificar seu próprio allowlist de `tools` e configuração de `mcpServers`

O parâmetro `allowed_tools` no `ClaudeAgentOptions` é notavelmente um **allowlist de permissões**, não uma lista de registro de ferramentas. Todas as ferramentas built-in (Read, Write, Bash, Grep, WebSearch, etc.) estão sempre disponíveis para Claude; `allowed_tools` controla quais executam sem prompt de permissão. Isso significa que capacidade é separada de autorização — mais uma dimensão da arquitetura de separação de responsabilidades.

## Cinco camadas substituem um prompt monolítico

A arquitetura do SDK decompõe o que tradicionalmente seria um único system prompt em cinco camadas distintas e independentemente gerenciáveis:

1. **Camada de system prompt** (`system_prompt`): define personalidade e instruções comportamentais do agente — permanece estática e cacheável.
2. **Camada de tools**: ferramentas built-in mais MCP servers configurados via `mcp_servers`, definindo quais ações o agente pode executar.
3. **Camada de skills**: arquivos `SKILL.md` no filesystem descobertos através de `setting_sources`, fornecendo conhecimento de domínio que carrega lazily.
4. **Camada de subagentes** (parâmetro `agents` com objetos `AgentDefinition`): define alvos de delegação, cada um com seu próprio prompt, tools, skills e MCP servers a partir da v0.1.49.
5. **Camada de controle**: enforcement de permissões via hooks (`PreToolUse`, `PostToolUse`), `allowed_tools` e `disallowed_tools`.

Essa decomposição em cinco camadas significa que cada responsabilidade tem sua própria estratégia de carregamento, comportamento de cache e lifecycle. O paper de pesquisa da Anthropic de dezembro de 2024 "Building Effective Agents" articula a filosofia subjacente: agentes tipicamente são apenas LLMs usando ferramentas baseadas em feedback ambiental em loop — portanto é crucial projetar toolsets e sua documentação de forma clara e deliberada. O SDK vai além — o toolset não é apenas bem documentado, ele é **estruturalmente isolado** do prompt comportamental.

## Implicações diretas para o seu sistema

Considerando a arquitetura do `frete_sistema` com ~35 MCP tools declaradas inline no prompt de ~12-15K tokens, essa separação estrutural endereça diretamente os problemas identificados na sua auditoria:

- **O custo de ~2.500-3.000 tokens/turno do protocolo R0** se beneficia da mesma lógica de extração: memória como dado estruturado, não texto de prompt
- **As ~35 MCP tools inline** são exatamente o caso de uso do Tool Search — declarar via `mcp_servers` como parâmetro e deixar o SDK deferir automaticamente as que excedem 10% da context window
- **Prompt caching** torna-se viável quando o system prompt estabiliza: ferramentas como dados estruturados = prefixo cacheável, system prompt comportamental = segundo bloco cacheável
- **Subagentes Nacom vs. CarVia** podem agora carregar cada um seus próprios MCP servers e skills via `AgentDefinition`, sem poluir o contexto um do outro

## Conclusão

A mudança da v0.1.49 não foi uma migração de skills e MCP servers para fora de system prompts — essas capacidades nunca foram texto de prompt. Foi a **completude de um modelo de capacidade por subagente**, dando a cada `AgentDefinition` seus próprios campos `skills`, `mcpServers` e `memory`. A história arquitetural mais profunda é que a Anthropic projetou o SDK inteiro em torno de separação estrutural desde o início, dirigida por restrições concretas de performance: prompt caching exige prefixos estáveis, context windows exigem lazy loading, e roteamento de permissões exige identificadores de ferramentas legíveis por máquina. O resultado é uma arquitetura onde o system prompt faz apenas um trabalho — definir comportamento — enquanto capacidades, conhecimento, delegação e autorização ocupam cada um seu próprio espaço de parâmetros com caminhos de otimização independentes.
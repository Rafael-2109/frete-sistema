Abaixo segue um guia criado pelo Claude Desktop através de pesquisas dele:


# Guia completo da Anthropic para engenharia de system prompts em agentes de produção

**A Anthropic evoluiu sua orientação de "engenharia de prompts" para "engenharia de contexto"** — a arte de curar o menor conjunto de tokens de alto sinal que maximiza a probabilidade de resultados desejados dentro de uma janela de contexto finita. Este relatório compila todas as recomendações oficiais, benchmarks quantitativos e padrões endossados da documentação, blog de engenharia e referência de API da Anthropic até março de 2026. Está organizado como um framework de avaliação que você pode aplicar diretamente à arquitetura do system prompt v3.7.0 do agente logístico Nacom Goya.

A filosofia central é a simplicidade radical: as implementações de agentes mais bem-sucedidas da Anthropic usam **padrões simples e composáveis em vez de frameworks complexos**. Comece minimalista, teste com o melhor modelo disponível, depois adicione instruções apenas para resolver modos de falha específicos encontrados durante os testes. A orientação abaixo cobre estrutura, ferramentas, delegação multi-agente, memória, caching e gerenciamento de contexto — as dimensões exatas relevantes para um agente de produção com ~50 tools MCP, 3 subagentes, 18 regras e injeção de contexto dinâmico.

---

## Estrutura do system prompt: tags XML, ordenação e a "altitude certa"

A recomendação estrutural fundamental da Anthropic é organizar system prompts em **seções distintas e hierarquicamente aninhadas usando tags XML**. Tags como `<instructions>`, `<context>`, `<behavior_instructions>` e `<output_format>` criam limites inequívocos que previnem "vazamento de instruções" entre seções. Os nomes das tags devem ser descritivos e consistentes ao longo do prompt — não existem tags "melhores" canônicas, mas os nomes devem fazer sentido com o conteúdo que envolvem. Aninhe tags para conteúdo hierárquico (`<outer><inner></inner></outer>`), e combine tags XML com técnicas como prompting multishot (`<examples>`) ou cadeia de pensamento (`<thinking>`, `<answer>`) para prompts de alta performance.

A **ordenação recomendada** dentro de um system prompt é crítica e segue a hierarquia de cache de prompts:

1. **Dados estáticos longos e documentos** (20K+ tokens) no topo absoluto
2. **Identidade e definição de papel** — quem o agente é, seu domínio, a data atual
3. **Regras comportamentais centrais** — defaults de ação, estilo de resposta, políticas de execução paralela
4. **Contexto e restrições de domínio** — informações específicas do projeto, limites
5. **Protocolo de memória** — instruções para verificar/escrever estado persistente
6. **Exemplos** (3–5 exemplos diversos, ou 20+ com prompt caching habilitado)
7. **Contexto dinâmico** — dados operacionais, sessões recentes, preferências do usuário
8. **Query/instruções no final** — posicionar queries no final melhora a qualidade da resposta em **até 30%** nos testes da Anthropic

A Anthropic chama o nível ideal de especificidade de **"altitude certa"** — uma zona Goldilocks entre dois modos de falha. Específico demais significa hardcodar lógica if-else frágil ("Se o usuário disser X, responda com Y") que cria pesadelos de manutenção. Vago demais significa fornecer orientação de alto nível ("Seja útil") que assume falsamente contexto compartilhado. O prompt ótimo fornece **heurísticas específicas o suficiente** que guiam o comportamento de forma flexível em cenários diversos.

Para as **18 regras** do agente Nacom Goya, a Anthropic alerta explicitamente contra enfiar uma lista enorme de edge cases em um prompt. Em vez disso, recomendam curar **exemplos diversos e canônicos** que retratam efetivamente o comportamento esperado. Para um LLM, exemplos são as "imagens" que valem mil palavras. Se regras são genuinamente necessárias, diga ao Claude o que **fazer** em vez do que não fazer — instruções positivas consistentemente superam as negativas. Além disso, explique **por que** cada regra existe; fornecer motivação por trás das instruções melhora significativamente a conformidade do Claude 4.x.

---

## Gerenciando 50 tools: tool search, lazy-loading e design token-eficiente

A orientação mais crítica para um agente com ~50 tools MCP é o recurso **Tool Search** da Anthropic — sua solução oficial para o problema de muitas ferramentas. O caso quantitativo é severo: uma configuração típica multi-servidor-MCP consome **55K–77K tokens** em definições de ferramentas antes de qualquer trabalho começar. O servidor MCP do GitHub sozinho consome ~25% da janela de contexto do Claude Sonnet. A precisão na seleção de ferramentas **degrada significativamente acima de 30–50 tools**.

O Tool Search funciona marcando tools com `defer_loading: true`, excluindo-as do prompt inicial completamente. O Claude vê apenas uma ferramenta de busca mais um pequeno conjunto de tools core não diferidas. Quando o Claude precisa de uma capacidade específica, ele busca no catálogo de ferramentas, e a API retorna **3–5 definições de ferramentas relevantes** como blocos `tool_reference` que são auto-expandidos em definições completas. Os benchmarks são dramáticos:

- Uso de tokens reduzido em **85%** (de ~77K para ~12K consumidos inicialmente)
- Precisão de tools do Opus 4.0: 49% → **74%** com tool search
- Precisão de tools do Opus 4.5: 79,5% → **88,1%** com tool search
- Contexto disponível recuperado: de 122,8K para **191,3K tokens**

A configuração recomendada é manter **3–5 tools mais frequentemente usadas como não diferidas** (sempre carregadas), com todas as outras diferidas. O Claude Code auto-ativa tool search quando descrições de tools MCP excedem **10% da janela de contexto**, configurável via `ENABLE_TOOL_SEARCH=auto:5` para um threshold de 5%.

Além do lazy-loading, a orientação de design de tools da Anthropic enfatiza vários princípios diretamente aplicáveis a um agente logístico com 50 tools. **Não simplesmente encapsule endpoints de API existentes** — construa menos ferramentas, mais pensadas, mirando workflows de alto impacto. Consolide operações multi-etapa em ferramentas únicas (ex.: `schedule_shipment` em vez de `list_carriers` + `list_routes` + `create_booking`). Nomeie tools claramente agrupando por serviço e recurso (ex.: `logistics_orders_search`, `logistics_inventory_check`). Descrições de tools devem ser escritas como você explicaria para um novo funcionário — tornando contexto implícito explícito, incluindo exemplos de uso, edge cases, requisitos de formato de input e limites claros sobre quando usar cada tool.

Para respostas de tools, a Anthropic recomenda implementar um enum `response_format` (conciso/detalhado) para controlar verbosidade — respostas concisas usam aproximadamente **⅓ dos tokens** de respostas detalhadas. Mantenha respostas abaixo de **25.000 tokens** (limite padrão do Claude Code). Retorne nomes/identificadores em linguagem natural em vez de UUIDs, o que reduz significativamente alucinações. Implemente paginação, seleção de range, filtragem e truncamento com defaults sensatos. Faça respostas de erro específicas e acionáveis em vez de retornar códigos de erro opacos.

Para validação de schema em produção, use `strict: true` nas definições de tools. Isso garante que as chamadas de tools do Claude sempre correspondam exatamente ao seu schema, eliminando incompatibilidades de tipo ou campos obrigatórios ausentes — essencial para um sistema logístico de produção onde parâmetros inválidos podem causar falhas no mundo real.

---

## Orquestração multi-agente: como a Anthropic constrói sistemas de subagentes

A arquitetura multi-agente de produção da Anthropic segue o **padrão orquestrador-trabalhador** — um agente líder coordena subagentes especializados operando em paralelo. Seu sistema de pesquisa interno usando esse padrão com Claude Opus 4 como líder e subagentes Claude Sonnet 4 **superou o Claude Opus 4 single-agent em 90,2%** na avaliação interna de pesquisa.

Para os 3 subagentes do agente Nacom Goya, a orientação da Anthropic é específica. Cada subagente precisa de quatro elementos em seu prompt de delegação: um **objetivo**, um **formato de saída**, **orientação sobre tools/fontes**, e **limites claros de tarefa**. Sem descrições detalhadas de tarefas, agentes duplicam trabalho ou deixam lacunas. Cada subagente roda em sua própria janela de contexto nova — chamadas de tools intermediárias e resultados ficam dentro do subagente, e apenas sua mensagem final retorna ao pai. Isso é crítico para gerenciamento de contexto: o pai recebe um resumo conciso, não cada chamada de tool que o subagente fez.

As regras de escala que a Anthropic incorpora em seus próprios prompts de orquestrador são instrutivas:

- Busca de fatos simples: 1 agente, 3–10 chamadas de tools
- Comparações diretas: 2–4 subagentes, 10–15 chamadas cada
- Pesquisa complexa: 10+ subagentes com responsabilidades claramente divididas

Subagentes podem usar modelos diferentes para otimização de custo — rotear tarefas simples para o **Haiku** (mais barato, mais rápido) e tarefas de raciocínio complexo para **Sonnet ou Opus**. Escopo de tools por subagente é recomendado: limitar quais tools cada subagente pode acessar para prevenir expansão de escopo e reduzir overhead de tokens de definições desnecessárias.

Restrições arquiteturais chave: subagentes **não podem criar outros subagentes** (prevenindo aninhamento infinito). Para paralelismo sustentado excedendo janelas de contexto, use **equipes de agentes** que coordenam entre sessões separadas. Quando subagentes retornam resultados detalhados, podem consumir contexto significativo do pai — considere fazer subagentes escreverem outputs em armazenamento externo (filesystem, banco de dados) e passar referências leves de volta ao coordenador em vez de payloads completos.

Os arquétipos de subagentes built-in no Claude Code fornecem um template útil: **Explore** (pesquisa/coleta de contexto somente leitura), **Plan** (pesquisa especificamente para planejamento sem modificações), e **General-purpose** (tarefas multi-etapa complexas requerendo exploração e ação). Para o agente logístico, isso mapeia naturalmente para subagentes especializados em diferentes domínios operacionais.

---

## Prompt caching: projetando para 90% de redução de custo

Prompt caching pode reduzir custos em **até 90%** e latência em **até 85%** para prompts longos. A hierarquia de cache é `tools → system → messages`, significando que mudanças em níveis superiores invalidam tudo abaixo. Para um agente logístico com um system prompt grande e majoritariamente estático, essa arquitetura tem implicações diretas de design.

O system prompt deve ser estruturado para que **todo conteúdo estático venha primeiro** — definições de tools, instruções do sistema, contexto de fundo, exemplos. Conteúdo dinâmico (contexto operacional, sessões recentes, memórias do usuário) deve vir **depois** das seções estáticas cacheadas. Breakpoints de cache (até 4 por request) marcam onde conteúdo estável termina e conteúdo dinâmico começa. O comprimento mínimo cacheável é **1.024 tokens** para modelos Sonnet/Opus.

O cache tem um **TTL de 5 minutos** por padrão (renovado a cada hit) com opção de 1 hora com custo de escrita maior. Leituras cacheadas custam apenas **10% do preço padrão de input**, significando que um único cache hit já se paga. Para o agente Nacom Goya, isso significa que o system prompt de ~10K+ tokens custaria efetivamente nada em requests repetidos se estruturado adequadamente para caching.

Regras críticas de invalidação para projetar ao redor: mudar definições de tools invalida **todos** os caches (tools, system, messages). Mudar `tool_choice` invalida caches de system e messages. Mudar parâmetros de thinking invalida apenas caches de messages — caches de tools e system sobrevivem. Isso significa que a seção de definições de tools deve ser particularmente estável; evite injetar dados dinâmicos em descrições de tools.

Com prompt caching habilitado, a Anthropic recomenda incluir **20+ exemplos diversos** de outputs de alta qualidade em vez dos usuais 3–5. O custo marginal de exemplos cacheados adicionais é negligível, e mais exemplos melhoram dramaticamente a qualidade de output para tarefas estruturadas.

---

## Injeção de contexto dinâmico e hooks operacionais

A Anthropic enquadra contexto dinâmico como um problema de **recuperação just-in-time (JIT)**. O padrão recomendado é manter **identificadores leves** (caminhos de arquivo, queries armazenadas, chaves de banco de dados, endpoints de API) no system prompt, depois usar tools para carregar dados reais dinamicamente em runtime. Isso mantém o prompt base enxuto e cacheável enquanto dá ao agente acesso ao estado operacional atual.

Para a injeção de contexto operacional do agente Nacom Goya (sessões recentes, status da frota, níveis de inventário), a arquitetura recomendada é uma **estratégia híbrida**: inserir contexto essencial de mudança lenta upfront (configuração do sistema, preferências do usuário, metadados da base de conhecimento) e usar chamadas de tools para dados de mudança rápida (status atual de pedidos, inventário em tempo real, embarques ativos). Isso previne o system prompt de inchar com dados operacionais obsoletos a cada turno.

O Claude Code implementa injeção de contexto dinâmico através de **Skills** — arquivos markdown com comandos shell embutidos usando sintaxe `!`command`` que executam antes do Claude processar o prompt:

```markdown
## Status Atual da Frota
!`python get_fleet_status.py --format=summary`
## Alertas Recentes
!`curl -s https://api.nacom-goya.com/alerts/recent | jq '.[:5]'`
```

Esse padrão injeta dados ao vivo automaticamente sem inchar o system prompt persistente. Para o agente logístico, hooks operacionais poderiam seguir esse padrão — injetando posições resumidas da frota, pedidos pendentes e estados de alertas no início da conversa em vez de embutir datasets completos.

**Compactação** é a estratégia da Anthropic para gerenciar contexto que cresce além dos limites durante conversas longas. O sistema resume o histórico da conversa, preservando decisões arquiteturais e issues não resolvidas enquanto descarta outputs de tools redundantes. Importante: o system prompt estático (incluindo configuração estilo CLAUDE.md) **sobrevive completamente à compactação** — é relido do armazenamento e reinjetado fresco. A compactação leve mais segura é **limpeza de resultados de tools** — remover resultados brutos de tools profundos no histórico da conversa que não são mais necessários.

---

## Sistemas de memória: três níveis de estado persistente

A Anthropic documenta três abordagens complementares de memória, todas relevantes para um agente logístico de produção gerenciando preferências de usuário e histórico operacional.

**Nível 1: Memória no system prompt** — Preferências estáticas e configurações embutidas no system prompt. Para seções de memória de usuário, a Anthropic alerta que arquivos excedendo **200 linhas reduzem aderência**. Seções de memória devem ser curadas, modulares e concisas. O problema de "memória esmaecida" é real: conforme blocos de memória crescem monolíticos, a capacidade do Claude de localizar informações relevantes diminui devido à diluição de atenção, não ao esquecimento verdadeiro. Divida blocos grandes de memória em seções menores e específicas por tópico com cabeçalhos claros.

**Nível 2: Memória persistente baseada em arquivo** — A Memory Tool da Anthropic (beta, header `context-management-2025-06-27`) fornece um diretório `/memory` que persiste entre sessões. O padrão recomendado de system prompt para agentes com memória habilitada é explícito:

```
IMPORTANTE: SEMPRE VISUALIZE SEU DIRETÓRIO DE MEMÓRIA ANTES DE FAZER QUALQUER OUTRA COISA.
Registre status/progresso/pensamentos em sua memória enquanto trabalha.
ASSUMA INTERRUPÇÃO: Sua janela de contexto pode ser resetada a qualquer momento,
então você arrisca perder qualquer progresso que não esteja registrado na memória.
```

Armazene preferências estruturadas e acionáveis — não histórico bruto de conversas. Use JSON para dados de estado (rastreamento de pedidos, snapshots de inventário), markdown não-estruturado para notas de progresso e insights operacionais, e git para rastreamento de estado entre sessões.

**Nível 3: Memória distribuída por subagentes** — Em sistemas multi-agente, o agente líder salva seu plano de pesquisa ou estado operacional na memória antes do truncamento de contexto em 200K tokens. Subagentes armazenam trabalho em sistemas externos via tools e passam referências leves de volta ao coordenador. Isso previne perda de informação durante processamento multi-etapa e reduz overhead de tokens.

Para o gerenciamento de memória/preferências de usuário do agente Nacom Goya, o padrão recomendado é um sistema hierárquico similar ao CLAUDE.md: políticas de nível organizacional (segurança, regras de compliance que não podem ser substituídas), configuração de nível de projeto (layouts de armazém, preferências de transportadora, regras de roteamento) e preferências de nível de usuário (formatos de exibição, preferências de notificação, relatórios favoritos). Carregue o nível relevante no início da sessão usando padrões `@import` para modularidade.

---

## Referências de base de conhecimento e triggers de recuperação

A Anthropic favorece fortemente **busca agêntica sobre RAG estático** para agentes de produção. Em vez de pré-computar embeddings e recuperar chunks fixos, o agente deve usar tools para navegar informações dinamicamente — tratando hierarquias de pastas, convenções de nomenclatura e schemas de banco de dados como metadados navegáveis.

O padrão recomendado é um **sistema de conhecimento de três níveis**:

1. **Sempre carregado**: Descrições breves de tools/recursos (suficiente para saber *se* um recurso é relevante) — fica permanentemente no system prompt
2. **Sob demanda**: Documentação completa e arquivos de instrução, puxados quando o agente determina relevância — carregados via chamadas de tools
3. **Just-in-time**: Dados ao vivo buscados via chamadas de API, queries de banco de dados ou comandos shell — carregados apenas para o request específico

Para as referências de base de conhecimento do agente logístico, isso significa que o system prompt deve conter ponteiros breves para domínios de conhecimento ("Tabelas de tarifa de transportadora estão disponíveis via a tool `kb_search`; SOPs de armazém estão na base de conhecimento de operações") em vez de embutir documentos de referência completos. Deixe o Claude decidir quando recuperar baseado na relevância da query.

A descoberta quantitativa da Anthropic de que **o uso de tokens explica 80% da variância de performance** em tarefas complexas significa que o agente deve ser generoso com tokens quando a tarefa exige. Embutir triggers de recuperação no system prompt — heurísticas explícitas como "Quando perguntado sobre tarifas de transportadora, sempre consulte a tool de tabela de tarifas antes de responder" — ajuda a garantir que o Claude use fontes autoritativas em vez de confiar em dados de treinamento potencialmente desatualizados.

---

## Regras, limites e controle comportamental no Claude 4.x

Modelos Claude 4.x seguem instruções mais literalmente que predecessores, o que tem implicações diretas para como as 18 regras do agente Nacom Goya devem ser estruturadas. Orientação específica para Claude 4.x:

**Reduza linguagem agressiva.** Onde modelos anteriores precisavam de prompting forçado como "CRÍTICO: Você DEVE usar esta tool quando...", o Claude 4.x (especialmente Opus 4.5+) dispara em excesso com tal linguagem. Use fraseamento normal: "Use esta tool quando..." A Anthropic nota especificamente que o Opus 4.5 é **mais responsivo ao system prompt que modelos anteriores**, então ênfase agressiva é contraproducente.

**Ação proativa vs. conservadora** deve ser explicitamente configurada. Para um agente logístico que deve tomar ação (criar embarques, atualizar pedidos), use o padrão proativo:

```xml
<default_to_action>
Por padrão, implemente mudanças em vez de apenas sugeri-las.
Se a intenção do usuário não é clara, infira a ação mais útil provável
e prossiga, usando tools para descobrir detalhes faltantes.
</default_to_action>
```

Para operações onde cautela importa (transações financeiras, mudanças irreversíveis), use o padrão conservador com limites explícitos sobre o que requer confirmação.

**Chamadas de tools paralelas** devem ser explicitamente habilitadas para um agente logístico que frequentemente precisa verificar múltiplos sistemas simultaneamente:

```xml
<use_parallel_tool_calls>
Ao chamar múltiplas tools sem dependências entre chamadas,
faça todas as chamadas independentes em paralelo. Por exemplo, ao verificar
inventário em 3 armazéns, rode todas as 3 queries simultaneamente.
</use_parallel_tool_calls>
```

**Evite super-engenharia de regras.** A orientação explícita da Anthropic: "Só faça mudanças que são diretamente solicitadas ou claramente necessárias. Não adicione error handling, fallbacks ou validação para cenários que não podem acontecer. Confie no código interno e garantias do framework. Valide apenas nos limites do sistema. A quantidade certa de complexidade é o mínimo necessário para a tarefa atual." Esse princípio se aplica a regras também — cada regra deve abordar um modo de falha demonstrado, não um hipotético.

Para o recurso de **extended thinking**, note que quando desabilitado, o Claude Opus 4.5 é particularmente sensível à palavra "think" e suas variantes. Substitua "think" por "considere", "acredite" ou "avalie" em regras e instruções. Quando extended thinking está habilitado, use `type: "adaptive"` para modelos mais novos, e adicione pensamento intercalado (header beta `interleaved-thinking-2025-05-14`) para habilitar raciocínio entre chamadas de tools — isso melhora dramaticamente avaliação, identificação de lacunas e refinamento de queries em workflows agênticos.

---

## Framework de avaliação para o agente Nacom Goya

Baseado no conjunto completo de recomendações da Anthropic, aqui está um checklist para avaliar a arquitetura do system prompt v3.7.0:

**Estrutura e ordenação.** O conteúdo estático de longa forma está no topo? Tags XML são usadas consistentemente com nomes descritivos? O posicionamento de query/instrução está no final? O prompt segue a hierarquia amigável ao cache (conteúdo estável primeiro, conteúdo dinâmico por último)?

**Gerenciamento de tools.** Com ~50 tools MCP, o Tool Search está habilitado com `defer_loading: true` em tools usadas infrequentemente? As 3–5 tools mais críticas são mantidas não diferidas? As descrições de tools são escritas como explicações para um novo funcionário — com exemplos de uso, edge cases e limites claros? O `strict: true` está habilitado para validação de schema em produção? As respostas de tools são projetadas com paginação e defaults token-eficientes?

**Arquitetura de subagentes.** Cada um dos 3 subagentes tem objetivos claros, formatos de saída, orientação de tools/fontes e limites de tarefas em seus prompts de delegação? Os subagentes são escopados para subconjuntos específicos de tools? O modelo mais barato (Haiku) é usado onde apropriado? Os subagentes retornam resumos concisos em vez de outputs brutos de tools?

**Contexto dinâmico.** O contexto operacional é injetado via recuperação JIT (chamadas de tools em runtime) em vez de embutido no prompt estático? O system prompt é estruturado para que seções estáticas sejam cacheáveis e seções dinâmicas venham após breakpoints de cache? Os hooks operacionais usam dados resumidos em vez de datasets completos?

**Memória e regras.** As memórias de usuário estão abaixo de 200 linhas por arquivo? As 18 regras são expressas como instruções positivas com motivação? A linguagem agressiva/enfática ("DEVE", "CRÍTICO", "SEMPRE") é minimizada para modelos Claude 4.x? As regras são apoiadas por exemplos diversos em vez de enumeração de edge cases?

**Otimização de performance.** Breakpoints de prompt caching estão configurados nos limites entre conteúdo estático e dinâmico? O uso de contexto é monitorado para que definições de tools não excedam 10% da janela? A compactação está configurada para conversas longas? Os resultados de tools são limpos do histórico profundo durante compactação?

A otimização de maior alavancagem para essa arquitetura específica é quase certamente **habilitar Tool Search** para as ~50 tools MCP, o que sozinho poderia recuperar **60–80% do contexto atualmente consumido**, melhorando dramaticamente tanto a precisão quanto a memória de trabalho disponível para as tarefas de raciocínio logístico do agente.
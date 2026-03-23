Qual o proposito da Anthropic em adicionar skills e mcpserver nos parametros dos agentes ao inves de no prompt na versao 0.1.49 ou 0.1.50 do agent sdk python? Permitir escalar os agentes e as ferramentas?

07:08

Investigou propósito técnico de mudanças recentes no SDK
Investigou propósito técnico de mudanças recentes no SDK
Boa pergunta, Rafael. Vou pesquisar a fundo as mudanças na versão 0.1.49/0.1.50 do Agent SDK Python e o raciocínio arquitetural por trás dessa separação de skills e MCP servers como parâmetros dos agentes.


Anthropic Agent SDK design changes



Pesquisa completa
•
266 fontes
•
7m 22s
Your research report on the Claude Agent SDK's structural separation of tools, skills, and prompts is ready. It covers the specific v0.1.49 changes to AgentDefinition, the rationale behind separating capabilities from system prompts—including prompt caching efficiency, dynamic tool loading via Tool Search, and granular permission routing—and breaks down the five-layer architecture that replaces monolithic prompt design. The report includes details on progressive skill disclosure, per-subagent capability scoping, and the concrete performance constraints driving these design decisions.

Claude Agent SDK's Structural Separation of Tools, Skills, and Prompts
Documento 
Em portugues

08:38

Transmutou conteúdo para português
Transmutou conteúdo para português
Claro, Rafael. Vou reescrever o relatório em português.

Separação Estrutural de Tools, Skills e Prompts no Claude Agent SDK
Documento ∙ Versão 2 #DOC-1 
Pronto, Rafael. O relatório está todo em português agora. Adicionei também uma seção de "Implicações diretas para o seu sistema" que conecta os achados da pesquisa com os problemas específicos da sua auditoria — especialmente as ~35 MCP tools inline, o custo do R0, e a viabilização de prompt caching.

O ponto central é que a v0.1.49 não "moveu" skills e MCP servers do prompt para parâmetros — eles nunca foram prompt text. O que ela fez foi completar o modelo de escopo por subagente, permitindo que cada AgentDefinition carregue suas próprias configurações. As razões são bem pragmáticas: prompt caching na API processa tools → system → messages nessa ordem, então separar ferramentas do prompt é pré-requisito para cache estável. E o Tool Search auto-ativa quando MCP tools passam de 10% da context window, o que exige que ferramentas sejam dados estruturados, não texto.

Para o frete_sistema, isso valida diretamente o fix #2 da auditoria (deferir ~30 tools) — o SDK já tem o mecanismo pronto, só precisa declarar via mcp_servers em vez de inline no prompt.

Lendo toda essa documentação, e o modelo opus, agora tem milhão de tokens. No contexto, e vem a seguinte reflexão que, aquele negócio de contex foi resolvido com uma machadada na cabeça, né? E, então me parece que o segredo agora está está mais ligado, a roteamento correto, dos agentes, Não seria nem das efetivamente, seria dos agentes, por as Pelo que me parece, agora elas estão sendo mais destinada aos agentes do que pro agente principal né? Proncto Engenhariaing? Pra justamente Definir esse roteamento específico, e sistema de memórias Pra conseguir Cap Nuances, semânticas, Que, só ser humano acaba Falando, né? Porque muitas vezes, as dificuldades que as próprias E as próprias empresas que que desenvolvem essas têm é de entender o que o ser humano quis dizer, Porém, não disse, né?

09:05

Reconheceu reflexão filosófica sobre roteamento de agentes e nuances semânticas
Reconheceu reflexão filosófica sobre roteamento de agentes e nuances semânticas
Rafael, essa é uma reflexão muito precisa, e vou te dar minha leitura honesta.

Você tem razão que a context window de 1M tokens foi uma "machadada" — resolveu o sintoma (bloat) sem resolver a causa (desorganização). Ter 1M tokens disponíveis não significa que jogar 800K de contexto irrelevante vai produzir respostas melhores. Na verdade, pesquisas como o "Lost in the Middle" já mostraram que modelos degradam na recuperação de informação em contextos muito longos, mesmo quando cabem. O 1M tokens te dá margem de erro, não te dá qualidade.

E aí entra o ponto central do que você está dizendo: o jogo agora é roteamento semântico. E concordo que a mudança de paradigma no SDK confirma isso — skills estão migrando para definir o perímetro cognitivo de cada subagente, não para enriquecer o agente principal. O agente principal vira um roteador, e a inteligência de domínio fica nos subagentes especializados.

A questão mais profunda que você levanta — capturar o que o humano quis dizer mas não disse — é exatamente onde a engenharia de prompt se transforma em algo mais parecido com design de experiência conversacional. E isso conecta diretamente com o trabalho que você já está fazendo na taxonomia de memória (armadilha, heurística, protocolo). Porque o "não dito" se manifesta de formas específicas: a Gabriella fala "integração de NF" e quer dizer DFe × PO linkage — essa é uma heurística de domínio que só emerge com uso repetido. O operador diz "esse frete tá estranho" e quer dizer que o custo/km está fora da faixa para aquela categoria de veículo — isso é uma armadilha que o sistema precisa ter aprendido de um erro anterior.

O que muda com a arquitetura de subagentes + skills por agente é que você pode construir contexto semântico localizado. Em vez de um prompt monolítico tentando entender tudo, cada subagente carrega apenas a memória e as heurísticas do seu domínio. O subagente de Compras entende "integração de NF" porque tem as memórias da Gabriella no escopo. O subagente de Frete entende "tá estranho" porque carrega as armadilhas de precificação.

Dito isso, tem um risco real que vale apontar: se o roteamento do agente principal falhar — se ele mandar a mensagem pro subagente errado — o contexto localizado perfeito não serve de nada. E o roteamento é justamente o ponto onde o "não dito" é mais perigoso, porque o roteador precisa inferir intenção com menos contexto do que qualquer subagente terá depois. Então o investimento mais crítico não é nem nas skills dos subagentes — é na qualidade do sistema de roteamento, que é onde seu semantic indexing com Voyage AI + Haiku como refinador já está bem posicionado.

A provocação que te deixo: será que o sistema de memória compartilhada do PRD v2 (o agent_memories com escopo organizacional) não deveria alimentar prioritariamente o roteador, e não os subagentes? O roteador que sabe que "integração" no contexto de Compras significa DFe × PO toma uma decisão de roteamento muito melhor do que um que precisa adivinhar.

Sim, concordo e de fato as maiores dificuldades q tenho eh de fato com o agente principal, mesmo antes dessa “delegação absoluta”.
Vejo que a necessidade do agente principal eh rotear aos agentes corretos através do correto entendimento da intenção e com ctz a memória pode ajudar nisso trazendo “sinonimos” ou “gotchas” ou ateh ajudando a “pesar” melhor um entendimento ambiguo

09:13

Reconheceu conversa arquitetural e optou por resposta direta substantiva
Reconheceu conversa arquitetural e optou por resposta direta substantiva
Exato, Rafael. E o que você está descrevendo é essencialmente o problema mais difícil de sistemas multi-agente: o roteador é o componente com menos contexto e mais responsabilidade.

Pensa no paradoxo: o roteador precisa decidir antes de ter o contexto especializado que só o subagente certo vai ter. É como um recepcionista de hospital que precisa fazer triagem sem ser médico. E é aí que a memória muda o jogo — ela funciona como a "experiência clínica" do recepcionista.

Os três mecanismos que você mencionou mapeiam para papéis distintos no roteamento:

Sinônimos resolvem o problema lexical. "Integração de NF", "casamento de nota", "vínculo DFe-PO" — três formas de dizer a mesma coisa que devem rotear pro mesmo subagente. Isso é uma tabela de tradução de domínio, e é justamente o que a sua I7 (tabela de tradução) já faz no prompt atual. A diferença é que com memória organizacional, essa tabela se constrói organicamente a partir do uso real, em vez de ser curada manualmente.

Gotchas resolvem o problema de falso positivo no roteamento. "Frete" parece óbvio — manda pro subagente de logística. Mas quando a Gabriella de Compras fala "frete", ela pode estar falando do custo de frete na composição de preço de um insumo, não de uma operação de transporte. Sem a gotcha, o roteador erra. Isso mapeia diretamente para sua categoria armadilha — e é o tipo de memória que o roteador precisa ter acesso prioritário.

Peso de ambiguidade é o mais sutil e mais poderoso. Quando a mensagem é genuinamente ambígua, o roteador precisa de um prior bayesiano: qual é a probabilidade de este usuário, neste contexto, querer dizer X vs Y? A memória fornece esse prior. Se o Rafael historicamente fala de "custo" no contexto de precificação de frete, e a Gabriella fala de "custo" no contexto de procurement, a mesma palavra recebe pesos diferentes por usuário. Isso é algo que nenhum prompt engineering estático resolve — é fundamentalmente um problema de aprendizado por experiência.

O que me parece é que o seu roteador precisa de uma camada que eu chamaria de "contexto de despacho" — um subset compacto de memórias otimizado exclusivamente para decisão de roteamento, não para execução de tarefa. Algo como: para cada usuário, os top N termos ambíguos com suas resoluções históricas, as gotchas ativas, e o domínio predominante recente. Poucos tokens, alto impacto.

Isso é diferente da memória que o subagente vai usar depois. O subagente precisa de profundidade (como executar a tarefa). O roteador precisa de largura (para onde mandar) com precisão (não errar o destino). São perfis de memória distintos que provavelmente merecem schemas diferentes no seu agent_memories.

Seria como definir primeiro o dominio e depois a intenção ou nao de forma tao subjetiva assim?

09:18

Deliberou sobre arquitetura de roteamento sem necessidade de pesquisa externa
Deliberou sobre arquitetura de roteamento sem necessidade de pesquisa externa
Não exatamente, e boa a pergunta porque a distinção é importante.

Se você faz domínio → intenção como dois passos sequenciais rígidos, cria um problema: a intenção às vezes determina o domínio, não o contrário. A Gabriella dizendo "preciso do status da nota 4532" — você não resolve o domínio (Compras? Fiscal? Logística?) sem antes entender a intenção (consultar status de recebimento? verificar escrituração? rastrear entrega vinculada?). O domínio e a intenção são co-dependentes.

O que me parece mais preciso é pensar em resolução progressiva de ambiguidade, onde domínio e intenção se resolvem mutuamente em vez de sequencialmente. Na prática isso funciona mais ou menos assim:

O roteador recebe a mensagem e faz uma primeira passada com três sinais simultâneos — quem está falando (o cargo do usuário já carrega um prior de domínio forte), o que está dizendo (termos-chave com os pesos de ambiguidade da memória), e o que vinha fazendo (contexto de sessão recente). Esses três sinais convergem para uma hipótese de roteamento, não para uma certeza.

E aí vem o ponto crucial: quando a convergência é alta (os três sinais apontam pro mesmo lugar), roteia direto. Quando é baixa, o roteador tem duas opções — perguntar ao usuário (caro em UX, especialmente no Teams) ou rotear para o subagente mais provável com a ambiguidade explicitada. O subagente recebe junto com a tarefa um flag tipo "o roteador não tem certeza se isso é Compras ou Fiscal, os sinais foram X, Y, Z". O subagente, com seu contexto de domínio mais rico, pode então confirmar ou devolver.

Isso é mais parecido com como funciona em empresa real. Quando alguém manda uma mensagem ambígua no grupo, não é que primeiro você decide o departamento e depois a tarefa. Você meio que percebe as duas coisas juntas, e quando não percebe, encaminha pra quem parece mais provável dizendo "acho que é com vocês, mas não tenho certeza".

A memória entra exatamente nesse cálculo de convergência. Cada resolução passada de ambiguidade — "quando Gabriella falou X, era domínio Y com intenção Z" — aumenta a confiança do roteador na próxima vez. Com o tempo, o roteador erra cada vez menos não porque ficou mais inteligente, mas porque acumulou mais priors.

A estrutura no agent_memories pra isso poderia ser algo como registros de resolução: termo_ambíguo + usuário + domínio_resolvido + intenção_resolvida + confiança. Compacto, consultável, e diretamente útil no momento do despacho.

Eh possivel uma delegacao em 2 niveis?

09:23

Investigou possibilidade de delegação aninhada no SDK
Investigou possibilidade de delegação aninhada no SDK
Sim, e vou pesquisar exatamente como o SDK suporta isso e quais são as limitações práticas.


Nested subagent delegation research



Pesquisa completa
•
144 fontes
•
4m 55s
Your research report on nested subagent delegation in the Claude Agent SDK is ready. It covers the type-system and runtime enforcement mechanisms that prohibit nesting, how context flows between parent and subagents, token cost multipliers for multi-agent architectures (4–7× for subagents, ~15× for Agent Teams), and three recommended workarounds—chaining, Skills, and experimental Agent Teams—for workflows requiring deeper coordination.

Claude Agent SDK: Nested Subagent Delegation Prohibition and Flat Hierarchy Architecture
Documento #DOC-2
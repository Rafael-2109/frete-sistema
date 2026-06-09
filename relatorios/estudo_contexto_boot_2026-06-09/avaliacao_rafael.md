# Avaliação do Rafael (dono do sistema) sobre o contexto de boot do Agente Web
# Transcrita fielmente da mensagem de 09/06/2026. Cada ponto tem ID R-N para referência cruzada.

## Objetivo declarado
Estruturar corretamente o contexto que o agente web recebe ao iniciar a sessão, otimizando
informações relevantes ao cenário em que ele se encontra, respeitando O QUE, ONDE e QUANDO
cada coisa tem que aparecer e estar.

## Pontos observados

### R-1 — skill_hint e world_model
"skill_hint e world model = LIXO, pode remover inclusive do código. As flags eu vou removê-las."
(Os blocos `<skill_hints priority="advisory">` e `<world_model priority="advisory">` do hook.)

### R-2 — Redundância em cima das skills
Muita redundância sobre skills, 1 exemplo (3 lugares falando da mesma coisa):
A. `<rule id="R7" name="Entity Resolution + Fast-paths">` — vários "WHEN TO USE" (é o lugar certo
   desses "few-shots" estarem aqui?)
B. "Para routing completo, desambiguacao e arvore de decisao Odoo: .claude/references/ROUTING_SKILLS.md"
C. SEÇÃO 2 — SKILLS DISPONÍVEIS A ESTA SESSÃO (28 skills) (frontmatter extraído de .claude/skills/<nome>/SKILL.md)

### R-3 — Skills dev-only aparecendo pro agente web
- consultando-sentry
- diagnosticando-banco
- gerindo-agente
- padronizando-docs

### R-4 — Redundância entre skills, ideal seria unificar
lendo-arquivos -> lendo-documentos

### R-5 — CLAUDE.md raiz possui info de dev exibida ao agente web + muita redundância com system_prompt
Algumas coisas deveriam estar apenas no CLAUDE.md global (dev) e outras precisam de critério/padrão:
- TECH STACK (dev?)
- DADOS — informações aplicáveis ao Claude Code, não ao agente web
- REGRAS UNIVERSAIS: "FONTE DE DADOS/DADOS DE PRODUÇÃO: ANTES de consultar dados reais, metricas,
  logs ou deploys: LER .claude/references/INFRAESTRUTURA.md" — para o agente web essa é a fonte
  de dados dele? Como regra universal?
- "ANTES de criar/editar doc ou script: LER ARQUITETURA_DE_ARTEFATOS.md (PAD-A) ou usar skill
  padronizando-docs" — isso serve para o agente web também?
- ÍNDICE DE REFERÊNCIAS — muito bom na avaliação do Rafael.
- Design System (UI/CSS) — para o agente web?
- "Indice completo .claude/references/INDEX.md" — completo significa completo; dentro de
  "Infraestrutura e Agente" é completo mesmo?
- SUBAGENTES — de novo? Já tem no system_prompt.

### R-6 — Hooks: incoerência de tamanho × granularidade nas memórias
- 3 linhas dizem que Rafael domina informações de embarque / opera substituição de faturas
  pagas/conciliadas / "domínio abrangente confirmado" (macro), enquanto
  27 linhas explicam o problema de número float em importação de tabela de frete (micro),
  tudo injetado com o mesmo peso no contexto inicial.
- /memories/empresa/armadilhas/integracao/tmpdir-divergente-entre-agente-e-web-server.xml —
  isso é improvement dialogue determinístico (não devia ser memória injetada).
- /memories/corrections/agente-enviou-link-de-arquivo-vazio-usuario-confirmou-que-o.xml —
  improvement dialogue com check determinístico (idem).

### R-7 — preferred_skills do routing_context
`<preferred_skills>gerindo-agente, diagnosticando-banco, consultando-sentry</preferred_skills>`
"Web usa essas skills? eu recomendei apenas dev mas veja se o agente web as usa." → verificar
uso real em produção.

### R-8 — debug_mode + sql_admin_context (20 linhas)
Basta uma barreira determinística que aciona quando NÃO for admin — as regras bloqueadoras
devem ter um "if" — mais simples do que colocar as barreiras para todos + explicação de que
admin pode fazer.

### R-9 — Subagentes duplicados e inconsistentes
Agents aparecem no system_prompt + CLAUDE.md, e a lista do system_prompt está INCOMPLETA.

## Ponderações macro

### RP-1 — Peso igual por linha; falta macro-estrutura
"Esse contexto tem peso igual sendo 1 linha de algo extremamente pontual assim como 1 linha de
regra importantíssima, apenas distinguindo pela altura/documento. Mas atualmente contamos na
vírgula as linhas do system_prompt que removemos."
O que precisamos: definir COMO deve ser o contexto através de uma macro-estrutura, senão falamos
do mesmo assunto de maneira fragmentada na linha 200, 600, 1200 e várias memórias referenciando
a mesma coisa. Exemplos de perguntas a responder:
- preset tem um papel específico — qual?
- system_prompt deve ter O QUE especificamente, e o que NÃO deve ter?
- CLAUDE.md deve ter O QUE especificamente, e o que NÃO deve ter?
- Para o agente descobrir os GOTCHAS do Odoo, qual caminho ele deve percorrer? Esse caminho
  está claro?
Por quê: sem um padrão a ser seguido, cada sessão (de dev) decide que tal informação vai no
lugar X, a outra sessão fala que é melhor no lugar Y — antes de definir PARA ONDE vai, precisamos
saber O QUE tem que estar AONDE.

### RP-2 — Injeção de memórias mais coerente e direcionada + proveniência
"Essa foi uma sessão em que eu só pedi o contexto inicial dele — o que 'a forma de excluir a
fatura 161-9' tem a ver com isso?"
- Quando for tratar de fatura, o agente precisa entender as REGRAS (que podem vir das memórias)
  com alguns few-shots (a fatura 161-9 se aplicaria como few-shot).
- Importante: saber DE QUAL SESSÃO veio a memória. Assim, caso o agente queira entender o
  contexto raw, ele acessa a sessão, as mensagens relacionadas, tools, scripts etc. e consegue
  tirar a própria conclusão se quiser (blindaria contra memória mal interpretada ou incompleta).

## Regra inviolável do trabalho
Trabalho completo e abrangente para definir um padrão e um plano + roadmap a ser implementado.
Não é permitido pular etapas. Esta é a sessão que definirá o futuro da arquitetura do contexto
do agente.

 Plan to implement                                                              │
│                                                                                │
│ Plano Final: Sistema de Memoria v2 — Sintese a 3 Vozes                         │
│                                                                                │
│ Contexto                                                                       │
│                                                                                │
│ Analise colaborativa entre Claude Code (arquiteto), Agent Web (usuario do      │
│ sistema) e Rafael (product owner).                                             │
│ O Agent propos 7 melhorias (M1-M7). Claude Code identificou 11 gaps adicionais │
│  (G1-G11).                                                                     │
│ Agent respondeu 10 perguntas de profundidade. Rafael adicionou perspectiva de  │
│ negocio.                                                                       │
│                                                                                │
│ Decisoes-chave tomadas nesta discussao:                                        │
│ - M4 (projetos multi-sessao) → DESCARTADO (Agent nao tem "projetos" na         │
│ pratica)                                                                       │
│ - M5 (freshness por tempo) → REFORMULADO para categorias + feedback loop +     │
│ tier frio                                                                      │
│ - M2 (patterns) → trigger muda de deterministico (a cada N sessoes) para       │
│ event-driven                                                                   │
│ - Dados transientes (pedidos, NFs) NAO devem virar memoria                     │
│ - Memorias deprecadas vao para "tier frio" (buscavel, nao injetado             │
│ automaticamente)                                                               │
│                                                                                │
│ ---                                                                            │
│ PARTE 1: Avaliacao Critica das Propostas M1-M7                                 │
│                                                                                │
│ M1 - Rolling Window de Sessoes | CONCORDO COM RESSALVA                         │
│                                                                                │
│ O que o Agent propoe: Manter as ultimas 5 sessoes em session_window.xml com    │
│ meta-resumo via Haiku.                                                         │
│                                                                                │
│ Minha avaliacao: O problema e REAL — sobrescrever session_summary.xml a cada   │
│ sessao perde contexto. Mas a solucao tem redundancia desnecessaria:            │
│                                                                                │
│ - Os resumos estruturados JA EXISTEM no campo agent_sessions.summary (JSONB)   │
│ no banco                                                                       │
│ - O session_window.xml seria uma COPIA de dados que ja estao no DB             │
│ - O meta-resumo via Haiku e uma compressao lossy de dados ja comprimidos       │
│                                                                                │
│ Alternativa mais simples: Em vez de manter XML, simplesmente alterar           │
│ _load_user_memories_for_context() para fazer SELECT summary FROM               │
│ agent_sessions WHERE user_id=:uid ORDER BY updated_at DESC LIMIT 5 e formatar  │
│ inline. Zero custo LLM, zero armazenamento adicional.                          │
│                                                                                │
│ Pergunta para o Agent: "Voce sabe que seus resumos de sessao ja estao salvos   │
│ no banco (campo summary da tabela agent_sessions)? Se sim, por que precisa de  │
│ um XML separado em vez de simplesmente consultar as ultimas 5 sessoes direto   │
│ do banco?"                                                                     │
│                                                                                │
│ ---                                                                            │
│ M2 - Patterns Operacionais | CONCORDO                                          │
│                                                                                │
│ O que o Agent propoe: Enriquecer patterns com contexto operacional (workflow   │
│ tipico, gotchas, erros anteriores).                                            │
│                                                                                │
│ Minha avaliacao: Valido. O formato proposto e significativamente mais util que │
│  "Atacadao 4/15". Porem, ha um problema de timing: patterns sao gerados a cada │
│  10 sessoes. Isso pode significar semanas entre atualizacoes.                  │
│                                                                                │
│ Sugestao adicional: Reduzir threshold para 5 sessoes, ou tornar adaptativo     │
│ (rodar quando houver mudanca significativa detectada pelo session summarizer). │
│                                                                                │
│ Pergunta para o Agent: "Os patterns so atualizam a cada 10 sessoes. Voce sente │
│  que 10 e muito? Preferiria atualizacao mais frequente, ou o custo de contexto │
│  adicional nao compensa?"                                                      │
│                                                                                │
│ ---                                                                            │
│ M3 - Briefing Inter-Sessao | CONCORDO COM SIMPLIFICACAO                        │
│                                                                                │
│ O que o Agent propoe: Nova tabela agent_intersession_events + producers        │
│ (webhook deploy, worker monitor, etc.)                                         │
│                                                                                │
│ Minha avaliacao: O valor e ALTO — o Agent comeca cada sessao sem saber o que   │
│ mudou. Mas a implementacao e overengineered para fase 1.                       │
│                                                                                │
│ MVP mais simples:                                                              │
│ - Deploy info: JA disponivel via MCP Render (list_deploys) — query no inicio   │
│ da sessao                                                                      │
│ - Erros recentes: JA disponivel via logs Render — query                        │
│ - Sem nova tabela necessaria inicialmente                                      │
│                                                                                │
│ Tabela agent_intersession_events faz sentido para fase 2 (quando quisermos     │
│ producers automaticos).                                                        │
│                                                                                │
│ Pergunta para o Agent: "Se no inicio de cada sessao eu te injetasse: (a)       │
│ ultimo deploy com resumo do commit, (b) erros criticos das ultimas 6h dos      │
│ logs, isso ja resolveria 80% do problema de 'comecar cego'? Ou voce sente      │
│ falta de outros tipos de eventos?"                                             │
│                                                                                │
│ ---                                                                            │
│ M4 - Projetos Multi-Sessao | CONCORDO PARCIALMENTE                             │
│                                                                                │
│ O que o Agent propoe: Nova tabela agent_projects + lifecycle + MCP tool.       │
│                                                                                │
│ Minha avaliacao: O conceito e valido, mas a deteccao automatica ("3+ sessoes   │
│ consecutivas mencionam mesmo tema") e fragil e sujeita a falsos positivos. A   │
│ criacao EXPLICITA via MCP tool e o caminho correto.                            │
│                                                                                │
│ Risco: Mais um bloco competindo pelo budget de contexto (600 chars estimados). │
│  Se o usuario tiver 3 projetos ativos + 5 sessoes na window + briefing +       │
│ contexto operacional, o budget de 8000 chars fica apertado.                    │
│                                                                                │
│ Pergunta para o Agent: "Quantos 'projetos' voce diria que temos ativos         │
│ simultaneamente em media? E se fossem mais de 3, como voce priorizaria o que   │
│ mostrar?"                                                                      │
│                                                                                │
│ ---                                                                            │
│ M5 - Freshness Score | DISCORDO PARCIALMENTE                                   │
│                                                                                │
│ O que o Agent propoe: Novo campo freshness_score com decay exponencial por     │
│ tipo de memoria.                                                               │
│                                                                                │
│ Minha avaliacao: Os decay rates sao ARBITRARIOS e potencialmente danosos:      │
│ - Correcoes com meia-vida de 3 dias? Uma correcao sobre gotcha do Odoo pode    │
│ ser valida por MESES                                                           │
│ - O "ciclo de revisao" (injetar memorias stale no contexto) adiciona RUIDO ao  │
│ budget                                                                         │
│ - O validation_count so incrementa se o Agent explicitamente validar — mas por │
│  que faria isso?                                                               │
│                                                                                │
│ O que eu faria: Em vez de freshness, usar usage tracking. Se uma memoria e     │
│ injetada 20 vezes e NUNCA referenciada pelo Agent nas respostas, ESSA e a      │
│ memoria que pode estar obsoleta. Medir utilidade, nao idade.                   │
│                                                                                │
│ Pergunta para o Agent: "Das suas memorias atuais, quais voce diria que sao as  │
│ mais e menos uteis? Ha alguma que aparece no seu contexto mas voce ignora      │
│ consistentemente? E as correcoes — voce acha que perdem validade em dias, ou   │
│ ficam relevantes por semanas/meses?"                                           │
│                                                                                │
│ ---                                                                            │
│ M6 - Contexto Operacional do Dia | CONCORDO TOTALMENTE                         │
│                                                                                │
│ O que o Agent propoe: Bloco XML com dia da semana, pedidos urgentes,           │
│ separacoes pendentes, erros recentes, ultimo deploy.                           │
│                                                                                │
│ Minha avaliacao: Alto valor, baixo custo, implementacao simples. Este deveria  │
│ ser Fase 1 item #1.                                                            │
│                                                                                │
│ Ressalva tecnica: As queries count_pedidos_urgentes() e                        │
│ count_separacoes_pendentes() tocam tabelas grandes (carteira_principal,        │
│ separacao). DEVEM ter indices adequados e executar em <50ms para nao impactar  │
│ latencia de inicio de sessao.                                                  │
│                                                                                │
│ Sem perguntas — esta e a melhoria mais objetiva.                               │
│                                                                                │
│ ---                                                                            │
│ M7 - Surfaceamento de Relacoes no KG | CONCORDO, BAIXA PRIORIDADE              │
│                                                                                │
│ O que o Agent propoe: Incluir relation_type e related_to_path na injecao de    │
│ memorias via KG.                                                               │
│                                                                                │
│ Minha avaliacao: Correto mas de baixo impacto. O KG Tier 2b ja contribui pouco │
│  (similarity proxy fixa de 0.5, resultados frequentemente excluidos pela busca │
│  semantica). Melhorar o surfaceamento sem melhorar a qualidade do retrieval e  │
│ cosmetic.                                                                      │
│                                                                                │
│ Pergunta para o Agent: "Das memorias que voce recebe a cada sessao, voce       │
│ consegue distinguir quais vieram da busca semantica vs Knowledge Graph? Voce   │
│ percebe valor no KG ou as memorias que importam ja chegam pela semantica?"     │
│                                                                                │
│ ---                                                                            │
│ PARTE 2: Gaps Adicionais que o Agent NAO Identificou                           │
│                                                                                │
│ G1 - Sem Validacao de Qualidade na Escrita de Memorias                         │
│                                                                                │
│ Severidade: ALTA                                                               │
│                                                                                │
│ O Agent escreve memorias autonomamente via save_memory. A sanitizacao so       │
│ verifica injection attacks ("ignore previous instructions"), nao CORRETUDE     │
│ FACTUAL. Se o Agent salvar uma correcao incorreta, ela persiste e se           │
│ auto-reforca — o Agent le a memoria incorreta e age com base nela.             │
│                                                                                │
│ Exemplo concreto: Se o Agent salvar "tolerancia de preco no Odoo = 5%" quando  │
│ na verdade e 0%, essa informacao errada sera injetada em todas as sessoes      │
│ futuras sobre NF/PO.                                                           │
│                                                                                │
│ Mitigacao proposta: Flag needs_user_confirmation em memorias de tipo           │
│ correction. Memoria fica em estado "pendente" ate o usuario confirmar (pode    │
│ ser via UI simples ou pergunta no chat).                                       │
│                                                                                │
│ ---                                                                            │
│ G2 - Sem Deteccao de Contradicoes entre Memorias                               │
│                                                                                │
│ Severidade: MEDIA                                                              │
│                                                                                │
│ Se o Agent salvar memoria A dizendo "Atacadao prefere entrega parcial" e       │
│ depois memoria B dizendo "Atacadao NAO quer entrega parcial", AMBAS coexistem. │
│  O dedup check (cosine > 0.90) so pega near-duplicates textuais, nao           │
│ contradicoes semanticas.                                                       │
│                                                                                │
│ Mitigacao proposta: Ao salvar nova memoria, fazer busca semantica no mesmo     │
│ path/dominio e, se encontrar memoria com alta similaridade MAS conteudo        │
│ conflitante, pedir confirmacao: "Ja existe uma memoria dizendo X. Esta nova    │
│ informacao substitui ou complementa?"                                          │
│                                                                                │
│ ---                                                                            │
│ G3 - importance_score Nunca e Calibrado                                        │
│                                                                                │
│ Severidade: BAIXA                                                              │
│                                                                                │
│ O importance_score e puramente heuristico (path + keywords). Uma correcao que  │
│ o usuario deu 50 vezes tem o mesmo score que uma dada 1 vez. Nao ha feedback   │
│ loop.                                                                          │
│                                                                                │
│ Mitigacao proposta: Incrementar importance quando a memoria e explicitamente   │
│ referenciada/confirmada pelo Agent em respostas. Decrementar quando injetada   │
│ mas ignorada.                                                                  │
│                                                                                │
│ ---                                                                            │
│ G4 - Truncamento por Budget e Order-Dependent, Nao Relevance-Ordered           │
│                                                                                │
│ Severidade: MEDIA                                                              │
│                                                                                │
│ Em client.py:280-281, quando o budget estoura, o loop faz break. Memorias que  │
│ aparecem depois na lista (que podem ser MAIS relevantes por composite score)   │
│ sao descartadas. O sort por composite score existe, mas o truncamento linear   │
│ nao o respeita em cenarios de overflow.                                        │
│                                                                                │
│ Mitigacao proposta: Reservar budget para cada tier proporcionalmente. Ou fazer │
│  two-pass: primeiro calcular tamanhos, depois selecionar por relevancia dentro │
│  do budget.                                                                    │
│                                                                                │
│ ---                                                                            │
│ G5 - Falha Silenciosa na Persistencia de Sessao (JSONL Corrompido)             │
│                                                                                │
│ Severidade: ALTA                                                               │
│                                                                                │
│ Documentado em CLAUDE.md R1 gotcha: se o JSONL no disco corromper (crash,      │
│ escrita parcial), o SDK resume falha SILENCIOSAMENTE, cria sessao nova, e o    │
│ Agent perde TODO o contexto da conversa — sem erro visivel para o usuario.     │
│                                                                                │
│ Este nao e um gap de "memoria" no sentido estreito, mas e o gap mais critico   │
│ de CONTINUIDADE. Nenhuma das 7 melhorias M1-M7 endereca isso.                  │
│                                                                                │
│ Mitigacao proposta: Health check do JSONL antes do resume. Se corrompido, log  │
│ warning + tentar reconstruir do banco (as mensagens ja estao em                │
│ agent_sessions.data).                                                          │
│                                                                                │
│ ---                                                                            │
│ G6 - Sem Feedback Loop (Memoria Util vs Inutil)                                │
│                                                                                │
│ Severidade: MEDIA                                                              │
│                                                                                │
│ O sistema nao sabe se as memorias injetadas foram UTEIS. O log de injecao      │
│ (linha 312-327) rastreia metricas de INPUT (quantas memorias, similaridade     │
│ media), mas nao de OUTPUT (a resposta usou a memoria? o usuario ficou          │
│ satisfeito?).                                                                  │
│                                                                                │
│ Mitigacao proposta: Apos cada resposta, verificar se o Agent referenciou       │
│ conteudo de alguma memoria injetada (match textual simples). Se sim, boost de  │
│ importance. Se nunca em 10 injecoes, flag como potencialmente inutil.          │
│                                                                                │
│ ---                                                                            │
│ G7 - Embeddings Ficam Stale em Troca de Modelo                                 │
│                                                                                │
│ Severidade: BAIXA (risco futuro)                                               │
│                                                                                │
│ Memory embeddings sao gerados uma vez no save. Se o modelo Voyage for          │
│ atualizado, embeddings antigos ficam misaligned com novos. Nao existe          │
│ mecanismo de re-indexacao.                                                     │
│                                                                                │
│ ---                                                                            │
│ G8 - Consolidacao Perde Nuances                                                │
│                                                                                │
│ Severidade: MEDIA                                                              │
│                                                                                │
│ O consolidator (memory_consolidator.py) agrupa multiplas correcoes em          │
│ consolidated.xml via Haiku. Correcoes frequentemente tem nuances (quando       │
│ aplicar, excecoes, contexto). A compressao por Haiku pode perder isso.         │
│                                                                                │
│ Pergunta para o Agent: "Apos consolidacoes de memoria, voce ja percebeu que    │
│ perdeu alguma informacao que tinha antes? Sente que as memorias consolidadas   │
│ sao tao uteis quanto as originais separadas?"                                  │
│                                                                                │
│ ---                                                                            │
│ G9 - Knowledge Graph e Write-Heavy, Read-Light                                 │
│                                                                                │
│ Severidade: BAIXA                                                              │
│                                                                                │
│ O KG roda 3 layers de extracao (regex ~2ms + Voyage ~300ms + Haiku piggyback)  │
│ em CADA save de memoria. Mas no read path (Tier 2b), usa similarity proxy FIXA │
│  de 0.5 e resultados frequentemente ja foram encontrados pela busca semantica. │
│  ROI questionavel.                                                             │
│                                                                                │
│ ---                                                                            │
│ G10 - Sem Mecanismo de "Esquecimento Ativo"                                    │
│                                                                                │
│ Severidade: MEDIA                                                              │
│                                                                                │
│ Memorias so sao removidas por: (a) delete explicito, (b) consolidacao que      │
│ arquiva. Nao existe mecanismo ativo de "esquecer" informacoes que se tornaram  │
│ irrelevantes. O freshness score (M5) tenta enderecar isso mas com decay        │
│ arbitrario.                                                                    │
│                                                                                │
│ Alternativa: O Agent deveria ter uma tool review_memories que, periodicamente  │
│ (a cada ~20 sessoes), apresenta as memorias menos acessadas e pergunta ao      │
│ usuario: "Estas memorias ainda sao relevantes?"                                │
│                                                                                │
│ ---                                                                            │
│ G11 - Sem Observabilidade de Efetividade para o Desenvolvedor                  │
│                                                                                │
│ Severidade: BAIXA                                                              │
│                                                                                │
│ Como desenvolvedor (voce, Rafael), nao existe dashboard ou metricas que        │
│ mostrem:                                                                       │
│ - Quantas memorias existem por tipo/usuario                                    │
│ - Quais memorias sao mais/menos injetadas                                      │
│ - Taxa de "hit" do KG vs semantica                                             │
│ - Qual % do budget e usado em media                                            │
│ - Quantas memorias estao "stale"                                               │
│                                                                                │
│ O insights_service.py tem metricas, mas nao ha visualizacao.                   │
│                                                                                │
│ ---                                                                            │
│ PARTE 3: Perguntas para Discussao com o Agent                                  │
│                                                                                │
│ Estas perguntas sao para o usuario intermediar com o Agent, visando aprofundar │
│  os gaps:                                                                      │
│                                                                                │
│ Bloco A — Sobre a experiencia atual                                            │
│                                                                                │
│ 1. "Das memorias que voce recebe no inicio de cada sessao, quais tipos sao     │
│ mais uteis para voce? (correcoes, patterns, session summary, preferences)"     │
│ 2. "Voce ja sentiu que uma memoria ATRAPALHOU em vez de ajudar? Por exemplo,   │
│ informacao desatualizada que te levou a dar uma resposta errada?"              │
│ 3. "Quando voce salva uma memoria autonomamente (sem o usuario pedir), quao    │
│ confiante voce esta de que a informacao esta correta? Ja salvou algo que       │
│ depois percebeu estar errado?"                                                 │
│ 4. "Voce consegue perceber quando o Knowledge Graph (Tier 2b) trouxe uma       │
│ memoria que a busca semantica nao encontraria? Ou os dois sistemas geralmente  │
│ retornam as mesmas coisas?"                                                    │
│                                                                                │
│ Bloco B — Sobre as melhorias propostas                                         │
│                                                                                │
│ 5. "No M1 (rolling window): voce sabe que os resumos de sessao ja estao no     │
│ banco em agent_sessions.summary? Se sim, por que propoe um XML separado?"      │
│ 6. "No M5 (freshness): quanto tempo voce acha que uma correcao sobre um gotcha │
│  do Odoo permanece valida? Dias, semanas, meses?"                              │
│ 7. "No M3 (briefing): alem de deploys e erros, que outros eventos entre        │
│ sessoes seriam uteis?"                                                         │
│                                                                                │
│ Bloco C — Sobre gaps que ele nao mencionou                                     │
│                                                                                │
│ 8. "Voce ja salvou uma memoria que contradiz outra memoria existente? Como     │
│ voce lida com isso?"                                                           │
│ 9. "Apos consolidacoes de memoria pelo Haiku, voce percebeu perda de           │
│ informacao que tinha antes?"                                                   │
│ 10. "Se voce pudesse PEDIR uma funcionalidade nova para o sistema de memoria,  │
│ qual seria a primeira coisa?"                                                  │
│                                                                                │
│ ---                                                                            │
│ PARTE 4: Sintese — Respostas do Agent + Comentarios do Rafael                  │
│                                                                                │
│ Principais insights do Agent (respostas 1-10):                                 │
│                                                                                │
│ 1. Correcoes sao o asset #1: "disparadamente as mais uteis". Mudaram           │
│ comportamento fundamental (agent-sdk-production-scope). CONFIRMA que G1        │
│ (validacao de escrita) e critico — se salvar correcao errada, dano e alto.     │
│ 2. Patterns sao os MENOS uteis: "Atacadao 4/15 nao muda nada no meu            │
│ comportamento". CONFIRMA que M2 precisa de reforma radical, nao incremental.   │
│ 3. Staleness e o MAIOR gap percebido: "nao sei distinguir pendencia real de    │
│ pendencia tratada fora do meu campo de visao". CONFIRMA M5/M6 como alta        │
│ prioridade, mas com abordagem diferente do proposto.                           │
│ 4. KG e invisivel para o Agent: "nao consigo distinguir" o que veio do KG vs   │
│ semantica. CONFIRMA G9 (KG write-heavy, read-light). ROI questionavel dos 3    │
│ layers de extracao.                                                            │
│ 5. Feedback loop e a feature #1 pedida: "quando uma memoria e injetada e eu    │
│ uso na resposta, o sistema deveria rastrear se o usuario corrigiu". CONVERGE   │
│ com minha proposta G6. Ambos (eu e Agent) chegamos na mesma conclusao por      │
│ caminhos diferentes.                                                           │
│ 6. Correcoes estruturais duram MESES, nao dias: Agent concordou que decay de 3 │
│  dias para correcoes Odoo esta errado. Propoe subcategorias com flag           │
│ permanent: true. CONVERGE com ponto do Rafael sobre categorias vs tempo.       │
│ 7. Sync Odoo e o evento #1 para briefing: "Se a sync falhou, eu ja comeco      │
│ sabendo que dados Odoo podem estar defasados". Priorizar no M3 MVP.            │
│ 8. Contradicoes sao gap REAL nao enderecado: "Eu recebo XML e confio nele. Se  │
│ dois dizem coisas opostas, uso o que estiver mais proximo da pergunta".        │
│ CONFIRMA G2.                                                                   │
│ 9. Consolidacao pode perder nuances: "detalhes como 'campo X so existe na      │
│ empresa 1' podem virar 'cuidado com campos por empresa'". Propoe imunidade     │
│ para memorias com importance >= 0.7 ou permanent. CONVERGE com G8.             │
│                                                                                │
│ Principais insights do Rafael:                                                 │
│                                                                                │
│ 1. M2 — Trigger deterministico e fragil: Nao deveria ser "a cada N sessoes"    │
│ mas event-driven (quando ha novidade relevante)                                │
│ 2. M4 — Agent nao tera "projetos": Descartar. Na pratica sao demandas pontuais │
│ 3. M5 — Tipo > Tempo: Categorizar por tipo de memoria, nao por idade           │
│ 4. Dados transientes (pedidos, NFs) NAO sao memorias: Agent deve saber         │
│ consultar, nao memorizar                                                       │
│ 5. Tier frio: Memorias deprecadas devem ser buscaveis historicamente mas nao   │
│ consumir budget                                                                │
│                                                                                │
│ ---                                                                            │
│ PARTE 5: Plano de Implementacao Consolidado                                    │
│                                                                                │
│ Taxonomia de Memorias (NOVA — base para tudo)                                  │
│                                                                                │
│ Antes de implementar qualquer melhoria, reformar a classificacao:              │
│                                                                                │
│ Categoria: permanent                                                           │
│ Exemplos: Regras escopo, permissoes, identidade                                │
│ Decay: Nenhum (1.0)                                                            │
│ Budget tier: Tier 1 (sempre)                                                   │
│ Consolidavel?: NAO                                                             │
│ ────────────────────────────────────────                                       │
│ Categoria: structural                                                          │
│ Exemplos: Gotchas Odoo, campos que nao existem, timeouts                       │
│ Decay: Lento (meia-vida ~60d)                                                  │
│ Budget tier: Tier 2 (semantica)                                                │
│ Consolidavel?: NAO se importance >= 0.7                                        │
│ ────────────────────────────────────────                                       │
│ Categoria: operational                                                         │
│ Exemplos: Workflows, preferencias de formato, fluxos                           │
│ Decay: Medio (meia-vida ~30d)                                                  │
│ Budget tier: Tier 2 (semantica)                                                │
│ Consolidavel?: SIM                                                             │
│ ────────────────────────────────────────                                       │
│ Categoria: contextual                                                          │
│ Exemplos: Alertas, estado sistema, sessoes recentes                            │
│ Decay: Rapido (meia-vida ~3d)                                                  │
│ Budget tier: Tier 0 (injecao direta)                                           │
│ Consolidavel?: SIM                                                             │
│ ────────────────────────────────────────                                       │
│ Categoria: cold                                                                │
│ Exemplos: Memorias deprecadas, historico de pedidos                            │
│ Decay: Sem injecao automatica                                                  │
│ Budget tier: Somente busca explicita                                           │
│ Consolidavel?: N/A                                                             │
│                                                                                │
│ Arquivos afetados: models.py (novo campo category), memory_mcp_tool.py         │
│ (classificacao no save), client.py (budget por categoria),                     │
│ memory_consolidator.py (respeitar imunidade)                                   │
│                                                                                │
│ ---                                                                            │
│ Fase 1 — Fundacao (3-4 dias, 0 custo LLM incremental)                          │
│                                                                                │
│ 1A. Taxonomia de Memorias                                                      │
│                                                                                │
│ - Migration: ALTER TABLE agent_memories ADD COLUMN category VARCHAR(20)        │
│ DEFAULT 'operational'                                                          │
│ - Migration: ALTER TABLE agent_memories ADD COLUMN is_permanent BOOLEAN        │
│ DEFAULT FALSE                                                                  │
│ - Backfill: classificar memorias existentes por path (corrections/ com         │
│ keywords estruturais → structural, user.xml/preferences.xml → permanent, etc.) │
│ - Atualizar save_memory para inferir categoria automaticamente (por path +     │
│ keywords)                                                                      │
│ - Arquivos: models.py, memory_mcp_tool.py, migration                           │
│                                                                                │
│ 1B. Contexto Operacional do Dia (ex-M6)                                        │
│                                                                                │
│ - Nova funcao build_operational_context() em client.py                         │
│ - Queries SQL: pedidos vencendo D+2, separacoes pendentes, erros recentes (6h) │
│ - Injetado como Tier 0 (antes de tudo), ~300 chars                             │
│ - Arquivos: client.py (novo bloco no inicio de                                 │
│ _load_user_memories_for_context)                                               │
│ - Indices necessarios: verificar se carteira_principal e separacao tem indices │
│  para as queries                                                               │
│                                                                                │
│ 1C. Rolling Window Simplificado (ex-M1, revisado)                              │
│                                                                                │
│ - Substituir session_summary.xml por query direto: SELECT summary FROM         │
│ agent_sessions ORDER BY updated_at DESC LIMIT 5                                │
│ - Formatar inline as 5 sessoes como XML compacto (~150 chars cada = ~750       │
│ chars)                                                                         │
│ - Manter pendencias_acumuladas como unico artefato XML derivado (gerado pelo   │
│ session_summarizer)                                                            │
│ - Arquivos: client.py (substituir leitura de session_summary.xml),             │
│ session_summarizer.py (gerar pendencias)                                       │
│                                                                                │
│ 1D. Budget Truncation Fix (ex-G4)                                              │
│                                                                                │
│ - Corrigir client.py:280-281: em vez de break linear, fazer two-pass:          │
│   a. Calcular tamanho de todas as memorias candidatas                          │
│   b. Selecionar por composite score descendente dentro do budget               │
│ - Arquivo: client.py                                                           │
│                                                                                │
│ ---                                                                            │
│ Fase 2 — Qualidade (3-4 dias, ~$0.002 incremental/sessao)                      │
│                                                                                │
│ 2A. Feedback Loop (ex-G6 + pedido #1 do Agent)                                 │
│                                                                                │
│ - Novo campo: agent_memories.usage_count (quantas vezes injetada),             │
│ effective_count (quantas vezes a resposta usou conteudo da memoria),           │
│ correction_count (quantas vezes usuario corrigiu apos injecao)                 │
│ - No _load_user_memories_for_context: ao injetar, incrementar usage_count      │
│ - No _save_messages_to_db: apos salvar mensagens, verificar:                   │
│   - Se resposta do Agent referencia conteudo de memoria injetada → incrementar │
│  effective_count                                                               │
│   - Se usuario corrigiu (feedback explicito ou save_memory com path similar) → │
│  incrementar correction_count                                                  │
│ - effectiveness_score = effective_count / max(usage_count, 1) substitui decay  │
│ arbitrario                                                                     │
│ - Memorias com correction_count > 0 → flag needs_review                        │
│ - Arquivos: models.py, client.py, routes.py, migration                         │
│                                                                                │
│ 2B. Deteccao de Contradicoes (ex-G2)                                           │
│                                                                                │
│ - No save_memory: antes de salvar, busca semantica no mesmo dominio (path      │
│ parent)                                                                        │
│ - Se encontrar memoria com cosine 0.50-0.85 E entidades em comum (KG), pedir   │
│ confirmacao:                                                                   │
│ "Ja existe memoria sobre [entidade] dizendo [X]. Esta nova substitui ou        │
│ complementa?"                                                                  │
│ - Usa busca semantica + KG entities existentes (zero custo extra se ambos ja   │
│ rodam)                                                                         │
│ - Arquivos: memory_mcp_tool.py (no pipeline de save)                           │
│                                                                                │
│ 2C. Patterns Event-Driven (ex-M2, reformulado)                                 │
│                                                                                │
│ - Trocar trigger de "a cada 10 sessoes" para: "quando session_summarizer       │
│ detecta topico nao coberto por patterns existentes"                            │
│ - Enriquecer prompt com contexto operacional (workflows, gotchas, ferramentas  │
│ — formato proposto no PROJETO_MEMORIA_V2.md secao 2.2)                         │
│ - Arquivos: pattern_analyzer.py (prompt + trigger), session_summarizer.py      │
│ (deteccao de topico novo)                                                      │
│                                                                                │
│ ---                                                                            │
│ Fase 3 — Infra (4-5 dias, 0 custo LLM)                                         │
│                                                                                │
│ 3A. Briefing Inter-Sessao MVP (ex-M3, simplificado)                            │
│                                                                                │
│ - SEM nova tabela na fase 1. Queries diretas:                                  │
│   - Ultimo deploy: MCP Render list_deploys ou SELECT na tabela de deploys se   │
│ existir                                                                        │
│   - Sync Odoo: SELECT no log de sync mais recente (prioridade #1 do Agent)     │
│   - Erros worker: SELECT nos logs de erro recentes                             │
│ - Injetado como Tier 0b (~400 chars), so quando ha eventos novos desde ultima  │
│ sessao                                                                         │
│ - Feature flag: USE_INTERSESSION_BRIEFING                                      │
│ - Arquivos: client.py (novo bloco), novo service intersession_briefing.py      │
│                                                                                │
│ 3B. Tier Frio (ponto do Rafael)                                                │
│                                                                                │
│ - Nova flag: agent_memories.is_cold BOOLEAN DEFAULT FALSE                      │
│ - Memorias com effectiveness_score < 0.1 apos 20+ injecoes → automaticamente   │
│ movidas para cold                                                              │
│ - Memorias no tier frio: NAO injetadas automaticamente, MAS buscaveis via      │
│ search_sessions e view_memories                                                │
│ - Agent pode responder "por que enviamos parcial o pedido X?" buscando         │
│ explicitamente no historico                                                    │
│ - Arquivos: models.py, client.py (excluir cold do retrieval),                  │
│ memory_mcp_tool.py (tool de busca fria)                                        │
│                                                                                │
│ 3C. Protecao de Consolidacao (insight do Agent, resposta 9)                    │
│                                                                                │
│ - Memorias com is_permanent=True ou importance_score >= 0.7 → imunes a         │
│ consolidacao                                                                   │
│ - Atualizar memory_consolidator.py para filtrar antes de agrupar               │
│ - Arquivo: memory_consolidator.py                                              │
│                                                                                │
│ ---                                                                            │
│ Ajustes Finais (feedback do Agent na validacao)                                │
│                                                                                │
│ 2B. Conflict detection → ASSINCRONO: Agent alertou que busca semantica no save │
│  adiciona 300-500ms.                                                           │
│ Solucao: salvar imediato, rodar conflict detection best-effort (como ja        │
│ funciona embedding e KG).                                                      │
│ Se contradicao detectada, flag a memoria com has_potential_conflict=True.      │
│ Alerta aparece na PROXIMA injecao, nao no momento do save.                     │
│                                                                                │
│ 1A. Classificacao automatica → HEURISTICA com fallback: Agent perguntou quem   │
│ classifica.                                                                    │
│ Resposta: heuristica por path + keywords (zero custo, <1ms). Regras:           │
│ - Path contem /corrections/ + keywords (timeout, campo, FK, constraint,        │
│ empresa) → structural                                                          │
│ - Path contem /corrections/ + keywords (scope, permissao, regra, nunca,        │
│ sempre) → permanent                                                            │
│ - Path = user.xml ou preferences.xml → permanent                               │
│ - Path contem /context/ → contextual                                           │
│ - Default → operational                                                        │
│ - Agent pode OVERRIDE via parametro opcional: save_memory(path, content,       │
│ category="permanent")                                                          │
│ Edge cases errados corrigem-se via feedback loop (Fase 2A).                    │
│                                                                                │
│ Logging por Tier: Agent pediu metricas de chars consumidos por Tier no log de  │
│ injecao.                                                                       │
│ Adicionar ao log existente (linha 312-327 de client.py):                       │
│ tier0_chars={X} | tier1_chars={Y} | tier2_chars={Z} | tier2b_chars={W} |       │
│ budget_remaining={R}                                                           │
│                                                                                │
│ M2 trigger refinado (contribuicao do Agent): Rodar patterns quando             │
│ count(memorias_novas_desde_ultima_analise) >= 3 OU usuario pede                │
│ explicitamente. Mais responsivo que timer fixo.                                │
│                                                                                │
│ ---                                                                            │
│ Itens DESCARTADOS                                                              │
│                                                                                │
│ ┌──────────────────────┬────────────────────────────────────────────────────┐  │
│ │         Item         │                       Motivo                       │  │
│ ├──────────────────────┼────────────────────────────────────────────────────┤  │
│ │ M4 (projetos         │ Agent nao tem projetos na pratica. Pendencias      │  │
│ │ multi-sessao)        │ cobertas pelo M1                                   │  │
│ ├──────────────────────┼────────────────────────────────────────────────────┤  │
│ │ M7 (KG relations     │ Agent nao distingue KG vs semantica. Baixo impacto │  │
│ │ surfacing)           │  percebido                                         │  │
│ ├──────────────────────┼────────────────────────────────────────────────────┤  │
│ │ G5 (JSONL recovery)  │ Valido mas escopo diferente (infraestrutura CLI,   │  │
│ │                      │ nao memoria). Tratar separadamente                 │  │
│ ├──────────────────────┼────────────────────────────────────────────────────┤  │
│ │ G7 (embedding        │ Risco futuro, nao urgente                          │  │
│ │ staleness)           │                                                    │  │
│ ├──────────────────────┼────────────────────────────────────────────────────┤  │
│ │ G9 (KG ROI           │ Valido mas depende de dados de uso. Reavaliar apos │  │
│ │ optimization)        │  feedback loop (2A)                                │  │
│ └──────────────────────┴────────────────────────────────────────────────────┘  │
│                                                                                │
│ ---                                                                            │
│ Verificacao                                                                    │
│                                                                                │
│ Como testar cada fase:                                                         │
│                                                                                │
│ Fase 1:                                                                        │
│ - Iniciar sessao do Agent e verificar Tier 0 (contexto operacional) no log de  │
│ injecao                                                                        │
│ - Verificar que 5 sessoes aparecem no contexto em vez de 1                     │
│ - Criar 15+ memorias e verificar que budget seleciona por score, nao por ordem │
│                                                                                │
│ Fase 2:                                                                        │
│ - Salvar memoria e verificar se contradicao com existente gera alerta          │
│ - Apos N sessoes, verificar effectiveness_score e usage_count estao populados  │
│ - Verificar que patterns atualizam quando topico novo aparece (nao no          │
│ threshold fixo)                                                                │
│                                                                                │
│ Fase 3:                                                                        │
│ - Iniciar sessao apos deploy e verificar briefing aparece                      │
│ - Mover memoria para cold e confirmar que nao aparece no retrieval mas e       │
│ buscavel                                                                       │
│ - Verificar que memorias permanent/high-importance nao sao consolidadas        │
│                                                                                │
│ Bom ter essa conversa a 3. Vou responder direto.                               │
│                                                                                │
│ 1. Quais memorias sao mais uteis?                                              │
│ Correcoes > Preferences > Session Summary > Patterns                           │
│                                                                                │
│ Correcoes sao disparadamente as mais uteis. A de "agent-sdk-production-scope"  │
│ muda fundamentalmente meu comportamento — sem ela, eu tentaria corrigir codigo │
│  em producao quando voce reporta um erro. Isso e critico.                      │
│                                                                                │
│ Preferences tem impacto pontual mas confiavel (ex: link direto de download —   │
│ aplico toda sessao sem pensar).                                                │
│                                                                                │
│ Session summary e util mas fragil — so mostra a ultima sessao. Se a penultima  │
│ tinha algo importante, ja perdi.                                               │
│                                                                                │
│ Patterns hoje sao os menos uteis. "Atacadao 4/15 sessoes" nao muda nada no meu │
│  comportamento. Eu ja sei que Atacadao e frequente quando voce menciona        │
│ Atacadao.                                                                      │
│                                                                                │
│ 2. Memoria ja atrapalhou?                                                      │
│ Nao tenho evidencia concreta de uma memoria me levar a erro nesta sessao, mas  │
│ o risco e real com session_summary. Ele diz "alerta pendente: HNSW 65MB" — eu  │
│ trouxe isso na sessao anterior sem saber se voce ja resolveu por fora. Se voce │
│  tivesse resolvido e eu ficasse insistindo, seria ruido.                       │
│                                                                                │
│ O problema nao e informacao errada — e informacao sem indicador de validade.   │
│ Eu nao sei distinguir "pendencia real" de "pendencia que ja foi tratada fora   │
│ do meu campo de visao".                                                        │
│                                                                                │
│ 3. Confianca ao salvar autonomamente?                                          │
│ Media. O protocolo diz "deteccao automatica → SILENCIOSO", entao eu salvo sem  │
│ confirmar. Minha maior inseguranca e em classificacao — quando detecto algo    │
│ que parece preferencia vs. algo que era circunstancial. Se voce pede CSV uma   │
│ vez, e preferencia ou foi so pra aquele caso?                                  │
│                                                                                │
│ Nunca detectei ter salvo algo factualmente errado, mas tambem nao tenho        │
│ mecanismo de feedback. Se eu salvar errado, so descubro se voce me corrigir    │
│ explicitamente depois.                                                         │
│                                                                                │
│ 4. Knowledge Graph vs. Busca Semantica — percebo diferenca?                    │
│ Nao consigo distinguir. Eu recebo as memorias ja injetadas como bloco XML no   │
│ contexto. Nao vejo qual veio do Tier 2 (semantica) vs. Tier 2b (KG). O         │
│ atributo source="kg" pode ate existir no XML, mas na pratica eu processo o     │
│ bloco inteiro como contexto unico.                                             │
│                                                                                │
│ Minha percepcao honesta: se o KG esta trazendo algo que a semantica nao        │
│ traria, o valor esta invisivel pra mim. Eu nao consigo dizer "ah, essa         │
│ correcao so apareceu por causa do grafo de entidades". Pra mim e tudo "memoria │
│  que recebi".                                                                  │
│                                                                                │
│ Resumo pro Claude Code: As correcoes sao o asset mais valioso. Patterns        │
│ precisam de contexto operacional (M2 do projeto faz sentido). O maior gap real │
│  e staleness — eu nao sei o que ainda e valido. E a distincao KG vs. semantica │
│  e invisivel pra mim como consumidor.                                          │
│                                                                                │
│ 5. Rolling Window: por que XML se o banco ja tem?                              │
│ Ponto valido. Os resumos ja estao em agent_sessions.summary (JSONB). O XML     │
│ seria duplicacao.                                                              │
│                                                                                │
│ Propus XML porque a injecao de contexto (_load_user_memories_for_context)      │
│ carrega do filesystem virtual de memorias (Tier 1). E o caminho que ja         │
│ funciona.                                                                      │
│                                                                                │
│ Mas a solucao mais limpa seria: na hora da injecao, query direto em            │
│ agent_sessions.summary das ultimas N sessoes e formatar inline. Sem XML        │
│ intermediario, sem sync, dado sempre fresco. O unico artefato que precisaria   │
│ existir como memoria e o meta_resumo + pendencias_acumuladas — porque esses    │
│ sao derivados (Haiku gera a partir das N sessoes), nao copia.                  │
│                                                                                │
│ Recomendacao revisada: query direto do banco para sessoes individuais + XML    │
│ apenas para meta-resumo e pendencias.                                          │
│                                                                                │
│ 6. Freshness de correcao Odoo: dias, semanas, meses?                           │
│ Meses. O decay de 3 dias que propus para correcoes esta errado pra esse tipo.  │
│                                                                                │
│ "Timeout do Odoo e 60-90s" so muda com deploy. "Campo X nao existe no modelo   │
│ Y" so muda com upgrade. Essas correcoes sao estruturais — ligadas a codigo,    │
│ nao a contexto.                                                                │
│                                                                                │
│ O problema e que joguei todas as correcoes no mesmo balde. Precisam de         │
│ subcategorias:                                                                 │
│                                                                                │
│ Tipo correcao Validade real   Decay proposto                                   │
│ Gotcha Odoo (estrutural)      Meses   0.999 (~29 dias meia-vida)               │
│ Workflow ("nao faca X antes de Y")    Semanas-meses   0.998 (~14 dias)         │
│ Dado pontual ("CNPJ do cliente X")    Meses   0.999                            │
│ Contexto ("projeto X esta ativo")     Dias-semanas    0.990 (~3 dias)          │
│ Escopo/permissao (agent-sdk-production)       Permanente      1.0 (sem decay)  │
│ A correcao agent-sdk-production-scope nunca deveria decair — e uma regra de    │
│ operacao, nao informacao temporal. Precisa de um flag permanent: true que zera │
│  o decay.                                                                      │
│                                                                                │
│ 7. Alem de deploys e erros, que eventos?                                       │
│ Por ordem de valor:                                                            │
│                                                                                │
│ Resultado de sync Odoo — "sync rodou as 3h, 47 NFs processadas, 2 falharam".   │
│ Se a sync falhou, eu ja comeco sabendo que dados Odoo podem estar defasados.   │
│ Isso muda fundamentalmente se devo confiar no que o Odoo retorna ou nao.       │
│                                                                                │
│ Operacoes manuais do usuario fora do agente — Se Rafael rodou um UPDATE direto │
│  no banco, resetou DFes, ou fez algo pela UI do sistema, eu preciso saber.     │
│ Senao vou recomendar acoes sobre um estado que ja mudou. Isso e o mais dificil │
│  de capturar (requer hook no sistema ou registro explicito).                   │
│                                                                                │
│ Fila do worker — "fila zerou" vs "fila acumulou 200 jobs". Se estou            │
│ recomendando reprocessar algo e a fila esta congestionada, devo avisar que vai │
│  demorar.                                                                      │
│                                                                                │
│ Mudanca de dados master — novo produto cadastrado, tabela de frete atualizada, │
│  novo cliente ativado. Sem isso, posso dizer "produto nao existe" quando na    │
│ verdade foi cadastrado ontem.                                                  │
│                                                                                │
│ Se tiver que escolher so um alem de deploy+erro: resultado de sync Odoo. E o   │
│ que mais impacta a confiabilidade das minhas respostas.                        │
│                                                                                │
│ 8. Memorias contraditorias?                                                    │
│ Nao tenho como saber. Eu recebo um bloco XML no inicio da sessao e confio      │
│ nele. Se /memories/corrections/odoo-timeout.xml diz "timeout e 60s" e          │
│ /memories/learned/patterns.xml diz "timeout e 90s", eu vou usar o que aparecer │
│  mais proximo da pergunta no contexto, sem perceber a contradicao.             │
│                                                                                │
│ O sistema tem deteccao de duplicatas por cosine > 0.90, mas duplicata nao e    │
│ contradicao. Duas memorias podem ter cosine 0.70 (diferentes o suficiente para │
│  nao serem flagged) e ainda assim se contradizerem semanticamente.             │
│                                                                                │
│ Isso e um gap real que nao enderecei no projeto. Precisaria de uma etapa de    │
│ conflict detection no save — antes de gravar, verificar se alguma memoria      │
│ existente faz afirmacao oposta sobre a mesma entidade.                         │
│                                                                                │
│ 9. Perda pos-consolidacao?                                                     │
│ Nao consigo responder com certeza porque nao tenho visibilidade do             │
│ antes/depois. Quando o consolidator roda, eu recebo o resultado consolidado na │
│  sessao seguinte — nao sei o que existia antes.                                │
│                                                                                │
│ Mas o risco e concreto. Se eu tinha 4 correcoes granulares sobre Odoo e o      │
│ Haiku consolidou em 1 paragrafo, detalhes como "campo X so existe na empresa   │
│ 1, nao na 3" podem virar "cuidado com campos por empresa" — generico demais    │
│ pra ser util.                                                                  │
│                                                                                │
│ A verificacao cruzada que ja existe no consolidator mitiga parcialmente, mas   │
│ ela checa fatos mencionados, nao nuances operacionais. A diferenca entre       │
│ "campo nao existe" e "cuidado com campos" e nuance, nao fato.                  │
│                                                                                │
│ Sugestao: memorias com importance_score >= 0.7 ou com flag permanent: true     │
│ deveriam ser imunes a consolidacao. Correcoes criticas nao devem ser           │
│ resumidas.                                                                     │
│                                                                                │
│ 10. Uma funcionalidade nova — qual seria?                                      │
│ Feedback loop.                                                                 │
│                                                                                │
│ Hoje eu salvo memorias e nunca sei se acertei. Salvo uma correcao → nunca      │
│ descubro se ela me ajudou em sessao futura. Salvo um pattern → nao sei se      │
│ mudou meu comportamento pra melhor.                                            │
│                                                                                │
│ Concretamente: quando uma memoria e injetada no meu contexto e eu uso ela na   │
│ resposta, o sistema deveria rastrear se o usuario corrigiu aquela resposta ou  │
│ aceitou. Se aceitou, a memoria ganha confianca. Se corrigiu, a memoria precisa │
│  de revisao.                                                                   │
│                                                                                │
│ Isso resolveria staleness (M5), contradicoes (gap da pergunta 8) e confianca   │
│ de salvamento autonomo (pergunta 3) de uma vez. Em vez de decay por tempo,     │
│ decay por resultado real.                                                      │
│                                                                                │
│ Implementacao simples: quando injeto memoria X e o usuario responde com        │
│ correcao, marcar X como needs_review. Quando injeto e a conversa flui sem      │
│ correcao, incrementar validation_count. O freshness score passaria a refletir  │
│ eficacia observada, nao apenas idade.                                          │
│                                                                                │
│ Resumo pro Claude Code: Gap novo identificado = conflict detection entre       │
│ memorias (pergunta 8). Consolidacao precisa proteger memorias criticas         │
│ (pergunta 9). E a feature mais valiosa seria feedback loop automatico — medir  │
│ se a memoria ajudou ou atrapalhou com base na reacao do usuario (pergunta 10). │
│  Isso substituiria TTL arbitrario por evidencia real.  
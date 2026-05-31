# CRÍTICA ARQUITETURAL — Eixo D (Ontologia / Modelo de Mundo)

> Revisor: arquiteto senior cético, na LENTE DE TETO (volume nunca julga valor).
> Foco: coerência com as 5 camadas + invariantes, reaproveitamento real, realizabilidade
> com rollback, lacunas, ambição. Evidência arquivo:linha verificada diretamente no código.

**VEREDITO: SÓLIDO COM AJUSTES.** O diagnóstico (Parte 1) é o mais forte dos eixos que vi —
verifiquei os números, o leak `:E/:A`, o proxy 0.5, o catch-all `conceito` e a ontologia
hardcoded: tudo confere. A tese central (KG = índice de recall → ontologia logística consultável
e bi-temporal) é o teto certo e encaixa nas 5 camadas. MAS três pontos do CAMINHO contêm erros
factuais de código que, se executados como escritos, fazem a Fase D0 e a Fase D2 falharem ou
entregarem menos do que prometem. E a AMBIÇÃO parou um degrau abaixo do SOTA real que o próprio
blueprint cita. Detalho abaixo.

---

## 1. COERÊNCIA — encaixe nas 5 camadas e invariantes

**Encaixe nas camadas: correto.** A `query_ontology` como Enhanced MCP tool (Camada 2) e a
injeção `<world_model>` no boot (Camada 4) são os dois pontos de entrada certos e ambos reusam
infra real: `_mcp_enhanced.py` existe e já serve Memory/Sessions com `outputSchema`
(`CLAUDE.md` R6), e `_build_routing_context` (`memory_injection.py:561`) é de fato onde o
`_DOMAIN_KEYWORDS` hardcoded é consumido (verifiquei o bloco em `memory_injection.py:338-372`).

**Invariantes respeitadas — com uma exceção a destacar:**

- *Best-effort dos services* (services/CLAUDE.md R1): o WRITE do grafo já roda em
  `db.engine.begin()` isolado (`knowledge_graph_service.py:619`) e é chamado best-effort por
  `memory_mcp_tool.py`. As fases D2/D3 (jobs de bootstrap/fatos) DEVEM herdar o mesmo contrato —
  o blueprint diz "best-effort/flag-gated (R1-R2)" mas NÃO especifica que o **job de bootstrap
  estrutural não pode rodar no path SSE** nem inline no save de memória. É um job RQ/APScheduler,
  não um hook. O blueprint deixa isso implícito; precisa virar requisito explícito ou a primeira
  execução de D2 (criar nó para todo cliente/SKU) trava o boot.

- *Thread-safety ContextVar* (CLAUDE.md R2): a `query_ontology` herda `_current_user_id` do
  ContextVar próprio da tool (CLAUDE.md "Prerequisitos de execução" #1 — cada tool tem o SEU
  ContextVar). O blueprint não menciona; é um gotcha real que vai morder na D4 se a tool de
  ontologia esquecer `set_current_user_id`. Anotar.

- *Constituição "1 skill = 1 objeto"*: essa invariante é do orquestrador de ESTOQUE Odoo, NÃO do
  agente web. O blueprint não a viola porque nem toca skills. Citação no enunciado da crítica é
  um falso-alarme — não há conflito.

- *Separação Web/Teams* (CLAUDE.md "Export crítico: Teams"): a injeção `<world_model>` no boot
  passa por `memory_injection.py`, que é compartilhado entre Web e Teams. O blueprint NÃO sinaliza
  que mexer em `_build_routing_context` afeta o Teams bot. É a invariante mais perigosa não-mapeada
  da Parte 3 (ver Lacunas).

**Coerência interna do ALVO:** a "5ª moeda" (força-de-aresta + recência) é honesta — o blueprint
admite que o 0.5 é proxy de design, não bug (1.2b), e propõe trocar a moeda em vez de tunar o
número. Isso é raciocínio arquitetural correto, não faxina.

---

## 2. REAPROVEITAMENTO — onde reusa de verdade e onde erra a peça

Aqui estão os **dois erros factuais** que mais comprometem o caminho. Ambos são de código que o
blueprint afirmou sem verificar a direção do dado.

### ERRO 2.1 — "Fase D0: backfill de entity_key é trivial, a Layer 2 já tem a chave em mãos e só não persiste" (l.190-191) está ERRADO na causa-raiz.

O blueprint diz que `l.299-336` "têm cnpj/cod em mãos, só não persistem em `entity_key`". Verifiquei
o WRITE path inteiro:

- `_extract_entities_voyage` JÁ RETORNA a chave: `('transportadora', name, cnpj)`
  (`knowledge_graph_service.py:302`), `('cliente', name, cnpj_raiz)` (l.320),
  `('produto', name, cod_produto)` (l.336).
- `_upsert_entity` JÁ PERSISTE a chave: `entity_key = COALESCE(EXCLUDED.entity_key, ...)`
  (`knowledge_graph_service.py:468`).

Ou seja, **a Layer 2 NÃO descarta a chave — o upsert já a grava.** Então por que `with_key=0`
para produto/cliente/transportadora em PROD? A causa real é outra, e está no pipeline de merge
(`extract_and_link_entities`, l.589-611):

1. **A fonte dominante de entidades nomeadas é o LLM (Layer 3), que injeta `key=None` por
   construção**: `haiku_converted.append((validated_type, ename, None))`
   (`knowledge_graph_service.py:597`).
2. **O dedup em l.605-611 usa `(etype, norm_name)`** processando regex→voyage→haiku NESSA ordem.
   O nome que a Voyage normaliza (descrição de produto / razão social do indexer) quase nunca é
   idêntico ao nome que o LLM cospe na conversa ("Atacadão"). Logo NÃO fazem merge: ficam duas
   entidades, e a que vence a corrida de menção é a do LLM, keyless.
3. **O fallback `conceito` (l.652, l.657) cria entidades keyless em massa** quando o nó da relação
   não existe no `entity_id_map`.

**Consequência para o caminho:** D0 não é "persistir a chave que já está em mãos" (P, risco baixo).
O conserto verdadeiro é **forçar a resolução-ao-nó-canônico antes do dedup** — quando a conversa
cita "Atacadão", buscar via Layer 2 e LINKAR ao nó com chave, em vez de criar string nova
(o blueprint até descreve isso corretamente na 2.3 "resolução de entidade", mas então CONTRADIZ a
si mesmo ao chamar D0 de backfill trivial). Backfill de `entity_key` para os 2.025 nós legados
não resolve o problema estrutural — só limpa o passado, e mesmo assim só consegue chave para os
nós cujo `entity_name` ainda casa por embedding. **Reclassificar D0 como M (não P)** e reescrever
o objetivo: "interceptar o merge para resolver-ao-nó, e backfillar o que for re-resolvível".

### ERRO 2.2 — "Fase D2: promover entity_indexer a fonte de nós Cliente canônicos" (l.152-153, l.202-203) reusa a PEÇA ERRADA.

Verifiquei `entity_indexer.py`: o `_collect_customers_impl`/`_collect_suppliers_impl` leem de
**`contas_a_pagar`** (`entity_indexer.py:81` — `FROM contas_a_pagar`), agrupando por **raiz de CNPJ
de 8 dígitos** (`entity_indexer.py:78`). Isto é um cadastro de PAGADORES/FORNECEDORES financeiros,
não o mestre de clientes de venda. Usá-lo para criar os nós `Cliente` da ontologia LOGÍSTICA gera:
(a) clientes ausentes (quem só compra, nunca recebe pagamento, não aparece); (b) granularidade de
raiz-CNPJ, que colapsa filiais com agendas/rotas distintas — exatamente a distinção que a ontologia
precisa preservar.

**A peça certa NÃO foi citada:** `carteira_principal` (verifiquei: 69 colunas) tem `cnpj_cpf`,
`raz_social`, `incoterm`, `cliente_nec_agendamento`, `forma_agendamento`, `cnpj_endereco_ent`,
`cod_produto`. É a fonte canônica de Cliente+Pedido+SKU para o domínio de expedição. E
`transportadoras.json` (27 cols, `cnpj`, `razao_social`) é o mestre de Transportadora real — não o
`carrier_indexer` (que é busca semântica, não cadastro). O blueprint reusou os **indexers de
SEARCH** como se fossem **fontes de cadastro**; são coisas diferentes. D2 deve produzir nós a partir
das TABELAS-mestre (`carteira_principal`, `transportadoras`, produto), opcionalmente reusando os
indexers só para gerar o embedding de cada nó (aí sim o reuso é legítimo).

### ERRO 2.3 — `key_source="cadastro_cliente.cnpj_cpf"` (l.118) aponta para tabela inexistente.

Não há `cadastro_cliente.json` nos 298 schemas. O Cliente real mora em `carteira_principal.cnpj_cpf`
(que o próprio blueprint cita corretamente para Pedido/SKU em l.119/l.121 — incoerência interna).
A AgendaEntrega tem fonte real e o blueprint não a citou: `agendamentos_entrega`
(`protocolo_agendamento`, `data_agendada`, `forma_agendamento` — verifiquei) + `contatos_agendamento`.

### Reaproveitamentos CORRETOS (creditados):
- `relationships.json` (420 FKs, v2.0.0 — verifiquei o header) como bootstrap de arestas
  determinísticas: **válido e excelente**. É o esqueleto relacional pronto.
- Composite scoring + budget two-pass (`memory_injection.py:877-1171`) como base da 5ª dimensão:
  **válido**.
- `_upsert_relation` com `weight += ` (`knowledge_graph_service.py:529`) como o ponto exato a
  evoluir para invalidação temporal: **diagnóstico correto** (verifiquei: só soma, sem valid_to).

---

## 3. REALIZABILIDADE — valor + rollback por fase, e um acoplamento perigoso

- **D0–D1 (higiene + schema declarativo):** rollback trivial (flag + tabela aditiva). OK, contanto
  que D0 seja reescopado (ver 2.1). O leak `:E/:A` (`knowledge_graph_service.py:403`) é um one-liner
  reversível — concordo.
- **D2 (bootstrap estrutural):** ATENÇÃO. Criar nó canônico para "todo cliente/SKU/transportadora"
  num grafo cujo escopo é **por user_id** (UniqueConstraint `uq_user_entity` inclui `user_id` —
  `models.py:920`) força uma decisão que o blueprint NÃO tomou: **os nós canônicos da base são
  `user_id=0` (empresa)?** Se sim, é coerente com o padrão de memória-empresa
  (CLAUDE.md "Memória Compartilhada" — paths `/empresa/*` salvam user_id=0, e
  `query_graph_memories` já faz `user_id = ANY([user_id, 0])`). Se o blueprint não fixar isso, D2
  ou duplica o cadastro inteiro por usuário (explosão), ou quebra a UniqueConstraint. **Rollback de
  D2:** truncar nós com `entity_key NOT NULL AND user_id=0` — possível, mas só se a decisão de
  escopo for tomada ANTES. Esta é a lacuna de realizabilidade mais concreta.
- **D3 (bi-temporal):** o blueprint propõe adicionar `valid_from/valid_to` a `_upsert_relation`.
  Risco real não mapeado: a UniqueConstraint atual `uq_entity_relation` é por
  (source, target, type). Com bi-temporalidade, o MESMO par pode ter várias versões temporais —
  a constraint PRECISA mudar (ou a invalidação vira UPDATE de `valid_to` da linha vigente + INSERT
  da nova). É uma migration de constraint, não só colunas aditivas. **Rollback fica caro** se não
  for desenhado como tabela-de-fatos separada (ver Ambição). Marcar D3 como G (não foi subestimado,
  mas o blueprint não viu a mudança de constraint).
- **D4–D5:** reversíveis por flag. OK.

**Acoplamento perigoso introduzido:** D5 substitui `_DOMAIN_KEYWORDS` por leitura do subgrafo em
`_build_routing_context`. Como esse caminho é compartilhado Web+Teams (CLAUDE.md), e o routing por
domínio alimenta `_DOMAIN_SKILLS`/`_DOMAIN_PATH_SEGMENTS` (`memory_injection.py:352-372`), se o
grafo retornar vazio para um prompt (cold start, usuário novo) o roteamento por domínio degrada
para nada. **D5 precisa manter `_DOMAIN_KEYWORDS` como FALLBACK**, não substituir — o blueprint diz
"deixa de ler hardcoded e passa a ler o subgrafo" (l.171-172), o que remove a rede de segurança.
Defense-in-depth: grafo primário, keywords fallback.

---

## 4. LACUNAS (a mais importante primeiro)

**LACUNA #1 (a mais importante) — escopo `user_id` da ontologia canônica não foi decidido, e isso
é pré-requisito de TUDO.** A tabela `agent_memory_entities` é multi-tenant por `user_id`
(`models.py:920`, `uq_user_entity`). Uma ontologia de NEGÓCIO (clientes, SKUs da Nacom) é fato da
EMPRESA, não de um usuário. Sem decidir `user_id=0` para os nós canônicos + ajustar a leitura
(`query_graph_memories` já suporta `ANY([user_id,0])` — `knowledge_graph_service.py` confirma),
D2 é irrealizável sem explosão ou colisão. Esta decisão deveria ser a Fase D0.5, antes do schema.

**LACUNA #2 — dependência cross-eixo com F (governança) omitida.** A `query_ontology` é uma nova
tool MCP. O eixo F documenta que a description budget da meta-tool `Skill`/tools já estourou
(CLAUDE.md "Solução B 2026-05-29": budget 16.000 chars, 46 skills truncadas). Adicionar tools sem
um modelo de namespacing/lifecycle (o sintoma que F levanta) reincide no mesmo problema. D4 DEPENDE
de F, não só "habilita B". Não está no mapa de dependências.

**LACUNA #3 — entity resolution sem mecanismo de invalidação de DEDUPLICAÇÃO ERRADA.** O blueprint
trata bi-temporalidade de FATOS (D3) mas não de IDENTIDADE. Se a Layer 2 resolver "Atacadão"
errado para o nó errado (embedding @ 0.70 — `knowledge_graph_service.py:296`), não há como
desfazer o merge. Graphiti/Zep tratam isso com episode subgraph que preserva a menção original.
O blueprint colapsou os três subgrafos do Zep (episode/semantic/community) em um só. Ver Ambição.

**LACUNA #4 — sinal de validação do próprio grounding.** O blueprint diz "DEPENDE de E só
indiretamente". Discordo: sem o sinal de qualidade do Eixo E, não há como saber se a ontologia
melhora ou piora as respostas (um grafo errado é PIOR que keyword hardcoded). A dependência de E
é DIRETA e bloqueante para promover D5 de experimento a default. Subestimada.

---

## 5. AMBIÇÃO — o alvo ficou UM DEGRAU abaixo do SOTA que ele mesmo cita

O blueprint ancora em Graphiti/Zep mas **achatou o modelo deles**. Verifiquei o paper (Zep,
arXiv 2501.13956): Graphiti tem (a) **quádruplo timestamp** — `t_created/t_expired` (system time)
E `t_valid/t_invalid` (event time), não o par único `valid_from/valid_to` que o blueprint propõe;
e (b) **três subgrafos**: episode (menção bruta), semantic entity (a ontologia), e **community**
(clusters hierárquicos via Leiden, à la GraphRAG). O blueprint só desenha o subgrafo semântico.

**Elevação concreta de ambição (puxando para o teto real):**

> **Adicionar o EPISODE SUBGRAPH como camada de proveniência imutável.** Hoje, quando o agente
> diz "Rodonaves atrasa para AM", a menção bruta da conversa se perde — vira aresta `atrasa_para`
> com weight. No teto Zep, cada FATO aponta para o EPISÓDIO que o originou (o turno de conversa +
> a query SQL/Odoo que o confirmou). Isso resolve a Lacuna #3 (dedup errado é reversível porque a
> menção original sobrevive) E dá ao Eixo A o sinal de qualidade definitivo: *um fato invalidado
> cujo episódio era uma resposta do agente = a recomendação anterior estava errada, com a trilha
> de auditoria de ONDE veio*. O agente passa a poder responder "por que você acha que Rodonaves
> atrasa?" com a proveniência — não com um weight opaco. A peça para construir isso JÁ EXISTE:
> `session_turn_indexer.py` (verifiquei que está em `app/embeddings/indexers/`) já indexa turnos
> de sessão; o episódio é o turno + o `AgentInvocationMetric`/tool-call que produziu o fato.

Segundo eixo de ambição: o blueprint para em "agente consulta o grafo". O teto real é o grafo
**alimentar a vigilância proativa (Eixo C) por construção bi-temporal**: um job que detecta
`valid_to` recém-setado em fatos de alta importância (ruptura nova, atraso novo) é um gatilho de
push natural — o blueprint cita isso de passagem (l.212-213) mas não o promove a parte do ALVO.
Com episode+community, "qual a temática dominante de problemas da rede Assaí esta semana" vira uma
query de comunidade, não um scan linear.

---

## RESUMO EXECUTIVO

- **Veredito: SÓLIDO COM AJUSTES.** Diagnóstico impecável e verificado; o ALVO é o teto certo e
  encaixa nas 5 camadas. Os ajustes são no CAMINHO, não na visão.
- **Ajustes obrigatórios:** (1) reescopar D0 — `entity_key` JÁ é persistido (`l.468`); o problema
  é o merge LLM-keyless + dedup por nome + fallback `conceito`, não falta de persistência [M, não P];
  (2) D2 reusa a peça errada — `entity_indexer` lê `contas_a_pagar` raiz-CNPJ, NÃO o mestre de
  clientes; usar `carteira_principal`/`transportadoras`; (3) corrigir `cadastro_cliente`→
  `carteira_principal` (l.118); (4) D5 manter `_DOMAIN_KEYWORDS` como fallback, não substituir.
- **Lacuna mais importante:** **o escopo `user_id` da ontologia canônica não foi decidido** — a
  tabela é multi-tenant (`uq_user_entity`, `models.py:920`); fatos da EMPRESA exigem `user_id=0`
  (padrão de memória-empresa já existente). Sem essa decisão como Fase D0.5, D2 é irrealizável
  (explosão por usuário ou colisão de constraint).
- **Elevação de ambição:** adicionar o **episode subgraph de proveniência** (Zep, 3 subgrafos) —
  reusa `session_turn_indexer.py` que já existe; torna a entity-resolution reversível (Lacuna #3),
  dá ao flywheel (Eixo A) o sinal de qualidade auditável, e habilita queries de comunidade para a
  vigilância proativa (Eixo C). O blueprint colapsou os 3 subgrafos do Zep em 1 — esse é o degrau
  que falta para chegar no teto real que ele mesmo citou.

### Fontes externas consultadas
- [Zep: A Temporal Knowledge Graph Architecture for Agent Memory (arXiv 2501.13956)](https://arxiv.org/html/2501.13956v1) — quádruplo timestamp (t_created/t_expired + t_valid/t_invalid), 3 subgrafos (episode/semantic/community), entity resolution por embedding
- [Graphiti — Neo4j](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/) — invalidação vs descarte, retrieval híbrido
- [GraphRAG community detection (Microsoft, Leiden)](https://www.mintlify.com/microsoft/graphrag/concepts/community-detection) — clusters hierárquicos para reasoning global (base da ambição de "query de comunidade")

# EIXO D — ONTOLOGIA / MODELO DE MUNDO

> De "recuperar fragmentos de conversa" para "raciocinar sobre o negócio da Nacom".
> Blueprint de arquitetura. READ-ONLY. Evidência arquivo:linha em tudo.

---

## PARTE 1 — ESTADO REAL (com evidência)

### 1.1 O que existe e como flui

O Knowledge Graph (KG) é um **embrião funcional e POVOADO** — não está desligado nem vazio.
Flag `MEMORY_KNOWLEDGE_GRAPH` default `true` (`app/embeddings/config.py:157`). Em PROD hoje
(query direta `dpg-d13m38vfte5s738t6p50-a`):

| Tabela | Linhas |
|---|---|
| `agent_memory_entities` | **2.025** |
| `agent_memory_entity_links` | 2.237 |
| `agent_memory_entity_relations` | **7.215** |
| `agent_memories` (não-dir) | 485 |

Três camadas de extração (`knowledge_graph_service.py:4-7`):
- **Layer 1 — regex** (`_extract_entities_regex`, l.214): UF, pedido `VC[DB]\d{5}`, CNPJ raiz, valor R$. ~2ms, zero custo.
- **Layer 2 — Voyage/pgvector** (`_extract_entities_voyage`, l.271): resolve transportadora/cliente/fornecedor/produto reusando `app.embeddings` (`service.search_carriers`, `entity_search.buscar_entidade_semantica`, `product_search.buscar_produtos_hibrido`), threshold 0.70.
- **Layer 3 — Sonnet piggyback** (`parse_contextual_response`, l.347): relações semânticas extraídas de graça junto do contextual-retrieval.

**WRITE** (`extract_and_link_entities`, l.541): roda **só** quando uma `agent_memory` é salva
(chamado por `memory_mcp_tool.py`). Faz upsert de entidades (l.439), links entidade→memória
(l.482), relações LLM (l.632) e **co-ocorrência** par-a-par cap 10 entidades (l.666-680, weight 0.5).

**READ** (`query_graph_memories`, l.736): no boot, dentro de `_load_user_memories_for_context`
como **Tier 2b** (`memory_injection.py:958-1002`). Extrai entidades do *prompt* (l.775-782),
busca entity_ids (l.799), HOP-1 via links (l.813), HOP-2 via relações (l.846-930), devolve
`[{memory_id, similarity, source:'graph'}]`.

### 1.2 ONDE o circuito quebra (o teto do design atual)

**(a) O grafo é um booster de RECALL, não um modelo de mundo consultável.**
`query_graph_memories` devolve **apenas IDs de `agent_memories`** que voltam para a MESMA lista
plana de blobs de texto (`memory_injection.py:976-1001`). As entidades e relações (os 7.215 edges)
**nunca são mostradas ao agente** como material de raciocínio. O agente nunca "vê" o grafo —
ele só ganha um atalho para lembrar fragmentos de conversa. Não existe tool de consulta à
ontologia, nem traversal exposto ao planejador. **Esse é o teto estrutural.**

**(b) Composite scoring com proxy 0.5 — é DESIGN, não bug, mas revela a limitação.**
`composite = 0.3*decay + 0.3*importance + 0.4*similarity` com `similarity=0.5` fixo para graph
(`memory_injection.py:997`, justificado em `knowledge_graph_service.py:830-834`). É um proxy
neutro honesto **porque link-match não tem cosine**. O problema não é o número — é que o grafo
é forçado a competir na mesma moeda (similaridade vetorial) de um sistema que deveria operar em
moeda DIFERENTE: força de relação, recência temporal do fato, validade. O 0.5 é o sintoma de que
o grafo foi encaixado num pipeline RAG, não tratado como base de conhecimento estruturada.

**(c) Entidades são genéricas e DESCONECTADAS do negócio real.** Distribuição em PROD:
- **1.256/2.025 (62%) são `conceito`** — catch-all indiferenciado. `processo` (203) e `campo`
  (157) idem. ~80% do grafo é vocabulário de dev/ops, não o mundo logístico.
- **`entity_key` (o ID canônico que permitiria JOIN com a base) é NULL em quase tudo**: só UF (28),
  pedido (23), cnpj (4) têm chave. **produto, cliente, transportadora, fornecedor: `with_key=0`** —
  são strings órfãs sem ponte para `carteira_principal`, `cadastro_cliente` ou Odoo.
- **Tipos contaminados**: `entity_type='produto'` contém `FATURAMENTO_PRODUTO`, `ODOO`,
  `CARTEIRA_PRINCIPAL`, `PEDIDO-DE-VENDA`, `SEPARACAO`, `STOCK.QUANT` (nomes de TABELA/conceito de
  código, não produtos). `cliente` contém `ELAINE`, `DENISE`, `GABRIELLA` (pessoas, não clientes).
- **Bug de parsing leaking flag**: `SP:A`, `ATACADAO:E`, `CARVIA:E`, `SENDAS:E` — o sufixo de
  relevância `:E`/`:A` de `parse_contextual_response` (l.398-405) **entra no nome da entidade** e
  cria duplicatas que nunca casam com a forma limpa. Furo de qualidade real, hoje em PROD.

**(d) Relações são 89,5% ruído de co-ocorrência.** **6.462/7.215 edges são `co_occurs`**
(weight 0.5). As relações semânticas de verdade (`requer` 109, `complementa` 108, `bloqueia` 87,
`depende_de` 51, `precede` 50…) somam ~750 e ligam majoritariamente nós `conceito`/`processo`.
Praticamente NENHUMA relação codifica a física do negócio (cliente→agenda, SKU→ruptura,
incoterm→responsável pelo frete).

**(e) Sem dimensão temporal.** Entidade tem `first_seen_at`/`last_seen_at`
(`models.py:916-917`); relação só `created_at` + weight acumulado (`models.py:1014`). Não há
`valid_from`/`valid_to`. Um fato hoje verdadeiro ("Rodonaves atrasa para AM") nunca expira nem é
invalidado por um fato novo — só acumula weight. Não há como reconstruir o estado do mundo numa data.

**(f) Existe uma ontologia escondida, hardcoded, FORA do grafo.** `memory_injection.py:338`
(`_DOMAIN_KEYWORDS`), `:352` (`_DOMAIN_SKILLS`), `:363` (`_DOMAIN_PATH_SEGMENTS`) são um
mini-modelo de domínio escrito à mão (expedicao/odoo_compras/frete/ssw…) usado em `_build_routing_context`
(l.561). É a prova de que o sistema JÁ precisa de uma ontologia — só que ela está dispersa em
constantes Python, sem ligação com o grafo nem com a base.

### 1.3 Ativos de reaproveitamento já existentes (não jogar fora)

- **`app/embeddings/indexers/`**: já indexam FONTES ESTRUTURADAS — `product_indexer`,
  `carrier_indexer`, `entity_indexer` (clientes/fornecedores financeiros), `route_template_indexer`,
  `devolucao_reason_indexer`, `payment_category_indexer`. Esses são exatamente as pontes
  estrutura→semântica que faltam ao grafo (que só usa os de SEARCH, nunca os indexers como fonte de nós).
- **`.claude/skills/consultando-sql/schemas/`**: 298 schemas de tabela + `relationships.json` (catálogo
  de FKs) + `catalog.json`. É o esqueleto relacional pronto para virar o esquema da ontologia.
- **Composite scoring + budget two-pass** (`memory_injection.py:877-1171`): a maquinaria de seleção
  por orçamento já existe e é boa — basta uma 5ª moeda (força de grafo / validade temporal).
- **Pipeline best-effort/flag-gated** (services/CLAUDE.md R1-R2): contrato de não-quebra já estabelecido.

---

## PARTE 2 — ALVO ARQUITETURAL (o teto)

**Tese:** o KG deixa de ser um índice de recall sobre conversas e passa a ser a **Ontologia
Logística da Nacom** — um modelo de mundo *bi-temporal, tipado e consultável* cujos nós são as
ENTIDADES REAIS do negócio (clientes, SKUs, transportadoras, pedidos, MPs, lotes, plantas) com
`entity_key` apontando para a fonte canônica (carteira/Odoo), e cujas arestas codificam a física
do negócio. O agente passa a **raciocinar sobre o grafo**, não apenas a recuperar fragmentos por causa dele.

Ancoragem em padrões 2026: este é o modelo **Graphiti/Zep** (ontologia tipada via Pydantic +
bi-temporal `t_valid/t_invalid` + retrieval híbrido semântico+BM25+traversal, P95 ~300ms — Neo4j/Zep)
e a abordagem **ontology-first / semantic layer** (mapear o schema relacional para conceitos tipados;
"ontologies provide the missing layer of meaning"). Fontes no fim.

### 2.1 Esquema de domínio (a ontologia tipada)

Um registro declarativo de **entity types** e **edge types** Nacom — Pydantic models versionados,
não strings livres. Substitui o vocabulário controlado plano de `knowledge_graph_service.py:60-73`
(que mistura `conceito`/`campo`/`termo` genéricos com `cliente`/`produto`).

```
EntityType(name="Cliente",     key_source="cadastro_cliente.cnpj_cpf",  attrs=[razao_social, uf, rede])
EntityType(name="SKU",         key_source="carteira_principal.cod_produto", attrs=[descricao, peso, giro_classe])
EntityType(name="Transportadora", key_source="transportadora.id")
EntityType(name="Pedido",      key_source="carteira_principal.num_pedido", attrs=[incoterm, valor, expedicao])
EntityType(name="MateriaPrima")  EntityType(name="Planta")  EntityType(name="Lote")  EntityType(name="UF")
```
Edge types **com semântica de negócio** (não `co_occurs`):
```
Cliente   --tem_agenda-->         AgendaEntrega(dia_semana, janela, exige_protocolo)
Cliente   --pertence_a_rede-->    Rede(Assaí, Atacadão…)
Pedido    --tem_incoterm-->       Incoterm(FOB|CIF)  --define_responsavel_frete--> {Cliente|Nacom}
SKU       --consome-->            MateriaPrima       --produzido_em--> Planta(capacidade)
SKU       --em_ruptura_para-->    Cliente@<t_valid>  (fato temporal)
SKU       --classe_giro-->        {A|B|C}
Pedido    --prioridade-->         P1..P7   (a regra P1-P7 vira ESTRUTURA, não prosa)
Transportadora --atende-->        UF(lead_time, custo)  --atrasa_para--> UF@<t_valid>
```

### 2.2 Bi-temporalidade (Graphiti)

Toda aresta de FATO ganha `valid_from`/`valid_to` + `recorded_at`. Fato novo que contradiz um
antigo **invalida** (set `valid_to`) em vez de descartar (preserva histórico — "Rodonaves atrasava
para AM em mar/abr; deixou de atrasar em mai"). Permite query "como era o mundo em DATA X" e dá ao
flywheel (Eixo A) um sinal de qualidade temporal. Substitui o weight monotônico-crescente atual
(`_upsert_relation` l.529, que só soma).

### 2.3 Povoamento a partir das FONTES ESTRUTURADAS (a virada central)

Hoje 100% dos nós vêm de conversa. No alvo, a **espinha dorsal** vem da base — conversa só
**enriquece** (sentimentos, exceções, heurísticas tácitas):

- **Bootstrap relacional**: `relationships.json` + schemas → arestas estruturais determinísticas
  (Pedido→Cliente, SKU→Pedido) sem LLM, com `entity_key` real.
- **Ingestores como FONTE de nós** (não só search): os `indexers/` existentes viram produtores de
  entidades canônicas (todo cliente de `cadastro_cliente`, todo SKU, toda transportadora) — `entity_key`
  preenchido por construção, matando o problema `with_key=0`.
- **Fatos derivados do operacional** (jobs incrementais): ruptura (estoque×carteira),
  agenda-de-entrega (padrão histórico de `Separacao.agendamento`/`protocolo`), giro (faturamento),
  incoterm (campo do pedido). São FATOS bi-temporais alimentados de carteira/estoque/produção/Odoo —
  exatamente as fontes que o CONTEXTO pede.
- **Resolução de entidade** (LLM+símbolo, padrão 2026): quando a conversa cita "Atacadão",
  resolve-se ao NÓ canônico via embedding+regra (Layer 2 já faz a busca — falta *linkar ao nó*,
  não criar string nova). Mata `ATACADAO`, `ATACADAO:E`, `ASSAI` duplicados.

### 2.4 Consulta: a ontologia vira CAPACIDADE do agente (onde encaixa nas 5 camadas)

Duas portas, ambas reusando infra:

1. **Tool MCP `query_ontology`** (Camada 2 — Tools). Enhanced tool (`_mcp_enhanced.py`) com
   `outputSchema`, retrieval HÍBRIDO (semântico Voyage + traversal de grafo + filtro temporal),
   devolvendo **FATOS e SUBGRAFO tipado** ("clientes da rede Assaí com agenda 3ªf que exigem
   protocolo; SKUs em ruptura para eles"), não memory-IDs. É a primeira vez que o agente *consulta
   o modelo de mundo*.
2. **Injeção estrutural no boot** (Camada 4 — dynamic injection). `_build_routing_context`
   (`memory_injection.py:561`) deixa de ler `_DOMAIN_KEYWORDS` hardcoded e passa a ler o subgrafo
   das entidades do prompt — bloco `<world_model>` tipado com fatos vigentes (`valid_to IS NULL`),
   não blobs de memória. O composite scoring ganha a 5ª dimensão: força-de-aresta + recência-do-fato.

### 2.5 Alimenta o planejador (dependência com Eixo B)

O planejador (Eixo B) deixa de rotear por keyword/prosa do system_prompt e passa a **planejar sobre
o grafo**: "pedido X é CIF → frete é responsabilidade Nacom → cotar; cliente tem agenda 3ªf+protocolo
→ checar portal; SKU em ruptura → P-rule rebaixa prioridade". A ontologia é o substrato compartilhado
que torna o planejamento *grounded* em vez de heurístico. P1-P7 viram traversal, não texto a interpretar.

---

## PARTE 3 — CAMINHO INCREMENTAL (reaproveitando o existente)

**Fase D0 — Higiene + chave canônica (P, risco baixo).** Corrigir o leak `:E/:A` em
`parse_contextual_response` (l.398-405) e reclassificar os `produto` que são tabelas/conceito.
Backfill de `entity_key` para os nós já resolvíveis (cliente/transportadora/produto via os mesmos
`buscar_*` da Layer 2 que HOJE descartam a chave — l.299-336 já têm cnpj/cod em mãos, só não persistem
em `entity_key`). **Destrava**: parar de poluir o grafo; pré-condição para qualquer JOIN com a base.
*Risco*: dados legados duplicados — dedup por `entity_key`. *Dep*: nenhuma.

**Fase D1 — Esquema de domínio declarativo (M).** Criar o registro tipado (entity/edge types Pydantic)
substituindo o vocabulário plano de `knowledge_graph_service.py:60-73` e absorvendo o
`_DOMAIN_KEYWORDS` hardcoded. Reusa `relationships.json` + 298 schemas como ponto de partida.
**Destrava**: ontologia versionável; fim do catch-all `conceito`. *Risco*: migração do vocabulário —
manter compat backward (l.356). *Dep*: D0.

**Fase D2 — Bootstrap estrutural a partir da base (M/G).** Promover `indexers/` a FONTE de nós:
job incremental que cria nós canônicos (todo cliente/SKU/transportadora) + arestas determinísticas
de `relationships.json`. **Destrava**: espinha dorsal do grafo vem do negócio, não de conversa;
`with_key` deixa de ser 0%. Reusa: `entity_indexer`, `product_indexer`, `carrier_indexer`,
sync incremental existente. *Risco*: volume (rate-limit Voyage — dimensiona INFRA, não valor).
*Dep*: D1.

**Fase D3 — Fatos bi-temporais do operacional (G).** Adicionar `valid_from/valid_to/recorded_at`
às arestas (`_upsert_relation` passa a invalidar, não só somar). Jobs que derivam fatos de
carteira/estoque/produção/Odoo: ruptura, agenda-entrega, giro, incoterm→responsável-frete.
**Destrava**: o modelo de mundo vivo do CONTEXTO (cliente→agenda→MP→capacidade; pedido→incoterm→frete;
SKU→giro→ruptura). *Risco*: complexidade de derivação — começar por 2 fatos (agenda + ruptura).
*Dep*: D2. **Habilita Eixo A** (sinal de qualidade temporal) e **Eixo C** (vigilância: "ruptura nova
para cliente com agenda amanhã" é um gatilho proativo natural).

**Fase D4 — Tool `query_ontology` + retrieval híbrido (M).** Enhanced MCP tool devolvendo subgrafo
tipado; `query_graph_memories` evolui de "devolve IDs" para "devolve fatos+traversal". **Destrava**:
o agente RACIOCINA sobre o negócio; primeira capacidade consultável de ontologia. Reusa: `_mcp_enhanced`,
Voyage, maquinaria de query atual. *Risco*: latência traversal (cap de hop, P95 alvo ~300ms à la Graphiti).
*Dep*: D2 (D3 enriquece).

**Fase D5 — Injeção estrutural `<world_model>` + 5ª dimensão de score (M).** `_build_routing_context`
lê o subgrafo em vez de `_DOMAIN_KEYWORDS`; composite ganha força-de-aresta + recência-de-fato.
**Destrava**: boot grounded no mundo real. *Dep*: D4. **Habilita Eixo B** (planejador sobre grafo).

---

### Dependências cross-eixo
- **HABILITA B (planejador)**: substrato consultável para planejar sobre o negócio (P1-P7 vira traversal).
- **HABILITA A (flywheel)**: bi-temporalidade dá sinal de qualidade ("fato foi invalidado = a recomendação anterior estava certa/errada").
- **HABILITA C (proatividade)**: fatos temporais novos (ruptura, atraso) são gatilhos de vigilância.
- **DEPENDE de E (qualidade)** só indiretamente: medir se o grounding de ontologia melhora respostas exige o sinal de qualidade do Eixo E.

### O que NÃO consegui verificar
- Se `cadastro_cliente`/`transportadora` têm os campos exatos (incoterm, rede, agenda) — assumi a partir do CONTEXTO e dos nomes de schema; D1 deve validar contra os 298 JSONs.
- Volume/custo Voyage no bootstrap D2 (questão de INFRA, não de valor — fora do escopo desta lente).

### Fontes externas
- [Graphiti: Knowledge Graph Memory for an Agentic World — Neo4j](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/) (ontologia Pydantic, bi-temporal t_valid/t_invalid, retrieval híbrido P95 300ms, invalidação vs descarte)
- [Graphiti: Temporal KGs for Agent Memory — Should the Flywheel Use It? — Codex](https://codex.danielvaughan.com/2026/03/30/graphiti-agent-memory-store/)
- [Ontologies, Context Graphs, and Semantic Layers: What AI Actually Needs in 2026 — Metadata Weekly](https://metadataweekly.substack.com/p/ontologies-context-graphs-and-semantic)
- [LLM-Driven Ontology Construction for Enterprise Knowledge Graphs (arXiv 2602.01276)](https://www.arxiv.org/pdf/2602.01276)
- [A Multi-Agent System for Semantic Mapping of Relational Data to Knowledge Graphs (arXiv 2511.06455)](https://arxiv.org/pdf/2511.06455)
- [Graph-based Agent Memory: Taxonomy, Techniques, Applications (arXiv 2602.05665)](https://arxiv.org/html/2602.05665v1)

<!-- doc:meta
tipo: explanation
camada: L3
sot_de: eixo C do blueprint — vigilancia proativa e memoria temporal
hub: docs/blueprint-agente/eixos/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# EIXO C — Vigilância Proativa / Memória Temporal

> **Papel:** eixo de design — vigilância proativa e memória temporal (preenche o "Eixo C" referenciado por `critica/D-ontologia.md:213,237`).
>
> Lente: TETO. O agente hoje só reage a um save; o alvo é um agente que VARRE a
> própria memória em busca de contradição e obsolescência, INVALIDA fatos com
> proveniência e EMPURRA o que mudou. Não pode podar o que o sistema já capta —
> precisa elevar memória estática a memória temporal viva.
>
> Tese: o agente trata toda memória como verdade atemporal. Quanto mais
> "permanente" a memória, pior — porque ela nunca é re-questionada contra o tempo
> nem contra fatos novos. A consolidação existe, mas é REATIVA (dispara no save).
> Falta um relógio: bi-temporalidade no substrato + um job offline que detecta o
> que envelheceu, o que se contradiz, e o que precisa de push.

---

## Indice

- Contexto
- Parte 1 — Estado real (com evidência arquivo:linha)
- Parte 2 — Alvo arquitetural (o teto)
- Parte 3 — Caminho incremental (Fases C0–C3)
- Fontes externas
- O que NÃO está verificado

## Contexto

Preenche a lacuna "Eixo C", referenciada por `critica/D-ontologia.md:213,237` e nunca escrita. Mapeamento das frentes da avaliação de memória ↔ eixos: `RECONCILIACAO_MEMORIA.md`.

## PARTE 1 — ESTADO REAL (com evidência arquivo:linha)

### 1.1 Toda manutenção de memória é REATIVA, disparada por um save

O agente só toca a própria memória quando ACABOU de salvar uma. Não há varredura
periódica que olhe o acervo inteiro procurando incoerência. O gatilho é o save:

| Operação | Quando dispara | Evidência |
|---|---|---|
| `maybe_consolidate` (Sonnet, dedup) | logo após `save_memory` (best-effort, daemon) | `memory_mcp_tool.py:1925-1933` |
| `maybe_move_to_cold` / `maybe_gc_cold_memories` | mesmo callsite pós-save | `memory_mcp_tool.py:1931-1932` |
| `maybe_cleanup_low_value` (empresa) | mesmo callsite pós-save | `memory_mcp_tool.py:1941-1942` |
| `_detect_conflicts_async` (contradição) | após o save, sobre a memória RECÉM-CRIADA | `memory_mcp_tool.py:1397-1462` |

`_detect_conflicts_async` é a peça que mais se aproxima de vigilância — e revela a
limitação por construção. Ela busca memórias similares (cosine 0.50–0.85) no mesmo
domínio e, se acha conflito, marca **apenas a memória nova** com
`has_potential_conflict=True` [CONFIRMADO `memory_mcp_tool.py:1443-1459`]. Nunca
re-examina pares de memórias ANTIGAS entre si. Se dois fatos contraditórios já
existiam no acervo antes da feature, ou se um fato fica obsoleto sem nenhum save
novo no domínio, **nada dispara**. O docstring é honesto: *"O alerta aparece na
PRÓXIMA injeção (não bloqueia o save atual)"* [CONFIRMADO `memory_mcp_tool.py:1410`].

Diferença com o estado-da-arte (Zep, arXiv:2501.13956; Generative Agents,
arXiv:2304.03442): lá a reflexão/invalidação é um processo AGENDADO que varre o
grafo inteiro, não um efeito colateral de uma escrita pontual.

### 1.2 Bi-temporalidade: o schema tem a coluna, o dado nunca foi preenchido

O KG declara `valid_from`/`valid_to` na tabela de relações
(`agent_memory_entity_relations`), mas só uma das duas é escrita — e a outra é
explicitamente adiada:

```
knowledge_graph_service.py:539  valid_from: Optional[datetime] = None,
knowledge_graph_service.py:551  valid_to fica NULL (fato vigente) — invalidação é fase posterior.
knowledge_graph_service.py:560-582  INSERT ... valid_from ... ON CONFLICT ... DO UPDATE SET valid_from = COALESCE(...)
```

`valid_from` é opcional e, na prática, chega `None` (o caller MVP não passa
timestamp de evento) [CONFIRMADO `knowledge_graph_service.py:539,546`]. `valid_to`
**nunca** é setado — a invalidação foi declarada "fase posterior"
[CONFIRMADO `knowledge_graph_service.py:551`]. Resultado: das relações do grafo,
**nenhuma tem o par bi-temporal preenchido**; todo fato é tratado como vigente para
sempre. (O blueprint cita "0/7204 relações"; não reconfirmei o número contra o
banco PROD — ver "O que NÃO está verificado".)

Pior no nível da memória de texto: `AgentMemory` **não tem campo temporal de
evento algum**. Suas únicas datas são de sistema —
`last_accessed_at` (`models.py:525`), `created_at`/`updated_at`
(`models.py:578-579`) — e nada que diga *de quando é o fato* nem *até quando ele
vale* [CONFIRMADO `models.py:502-579`: colunas são `importance_score`,
`category`, `is_cold`, `usage_count`, `effective_count`, `correction_count`,
`has_potential_conflict`, `priority`, `directive_status` — zero `valid_from`/`valid_to`].

**Consequência operacional — staleness silencioso.** Dados operacionais
congelados são injetados como verdade atual. Exemplo do próprio acervo: a memória
de baseline de troca de NF carrega `ultimo_total=881` com `updated_at` travado em
07/05 (ver topic file `troca_nf_atacadao881`), e há memórias datadas "set/2025"
sem nenhum marcador de validade. Sem `valid_to`, o agente não tem como saber que
"881" era o total *naquele dia* — ele lê como se fosse hoje. **Quanto mais
"permanente" a classificação da memória, pior**: `category='permanent'` e
`importance >= 0.7` são IMUNES à consolidação [CONFIRMADO `services/CLAUDE.md`
→ "memory_consolidator: arquivos protegidos"; `memory_consolidator.py:49-52`], ou
seja, exatamente as memórias mais "confiáveis" são as que menos são re-questionadas
contra o tempo.

### 1.3 O sinal de "memória útil" é eco textual, não desfecho

`effective_count` parece um sinal de qualidade temporal ("esta memória ainda
serve?"). Não é. Ele é incrementado quando o conteúdo da memória aparece
textualmente na resposta do agente:

```
_helpers.py:605  def _check_effectiveness_heuristic(memory_contents, assistant_message)
_helpers.py:638-648  overlap de palavras >= threshold  → effective_ids.append(mem_id)
_helpers.py:651-655  entity overlap >= 1 (CNPJ/UF/ID)  → effective_ids.append(mem_id)
_helpers.py:506-511  SET effective_count = effective_count + 1
```

É **eco textual** [CONFIRMADO `_helpers.py:605-659`]: se a memória foi "ecoada" na
resposta, conta como efetiva — independentemente de a resposta ter resolvido a
pergunta. Não há gatilho de reflexão por DESFECHO (o usuário aceitou? corrigiu?
o fato ainda era verdade?). É o mesmo buraco do Eixo E visto de outro ângulo: sem
sinal de qualidade por turno, o agente não tem como saber que uma memória
"efetiva" (ecoada) na verdade estava obsoleta.

### 1.4 Os pré-requisitos da vigilância JÁ EXISTEM — falta o vigia

O eixo não exige construir do zero. As três peças de infraestrutura estão prontas:

| Pré-requisito | Onde já existe | Evidência |
|---|---|---|
| Scheduler com step "1x/dia gated" | KG cleanup roda em hora/dia fixos, idempotente via `_ultimo_kg_cleanup.date() < hoje` | `sincronizacao_incremental_definitiva.py:1752-1788` (chama `cleanup_orphan_entities`, registrado como step 22 em `:2358`) |
| Maquinaria de consolidação reutilizável | `maybe_consolidate`, `maybe_move_to_cold`, `maybe_gc_cold_memories` | `memory_consolidator.py:86,194,291` |
| Schema KG temporal (parcial) | colunas `valid_from`/`valid_to` na tabela de relações | `knowledge_graph_service.py:539,551,560-582` |

O step de KG cleanup (`sincronizacao_incremental_definitiva.py:1752-1788`) é o
molde exato do que falta: um job offline, gated 1x/período, que varre o acervo e
toma uma ação de manutenção (lá, remover entidades órfãs). Falta o IRMÃO dele que
varra COERÊNCIA e OBSOLESCÊNCIA em vez de orfandade.

### 1.5 Diagnóstico em uma frase

O agente tem relógio no substrato mas nunca o lê: a manutenção de memória é
reativa a saves, a bi-temporalidade é schema-sem-dado, o sinal de utilidade é eco
textual — então fatos obsoletos são injetados como verdade atual e contradições
antigas dormem no acervo sem ninguém varrer.

---

## PARTE 2 — ALVO ARQUITETURAL (o teto)

### 2.1 Princípio: a memória tem um relógio, e há um vigia que o lê

O estado-final tem três propriedades que o estado atual não tem:

1. **Bi-temporalidade de PRIMEIRA CLASSE** (Zep, arXiv:2501.13956). Todo fato
   carrega tempo de evento (`valid_from`/`valid_to`) além do tempo de sistema
   (`created_at`). Um fato novo que contradiz um antigo **invalida** o antigo
   (seta `valid_to`) — não o apaga — preservando a proveniência do episódio que
   originou a mudança. O agente passa a poder responder "isso valia até X, mudou
   por causa de Y".
2. **Reflexão AGENDADA** (Generative Agents, arXiv:2304.03442). Um processo offline
   dispara quando a soma de importance dos fatos recentes ultrapassa um threshold,
   gera um insight de nível superior e — crucialmente — **cita os ids das
   memórias-fonte**. Reflexão sem proveniência é alucinação reciclada.
3. **Detecção PROATIVA de contradição + staleness/TTL.** Um vigia varre o acervo
   inteiro (não só a memória recém-salva) procurando pares incoerentes e fatos que
   envelheceram (FadeMem, arXiv:2601.18642 — decaimento/TTL como cidadão de
   primeira classe da memória de agente). O que envelheceu é rebaixado ou expira;
   o que mudou e é importante vira gatilho de PUSH.

A vigilância proativa "ruptura nova / atraso novo" que `critica/D-ontologia.md:213`
descreve "de passagem" vira aqui ALVO explícito: um `valid_to` recém-setado em um
fato de alta importância É o evento que dispara o push (`critica/D-ontologia.md:237`
promove isso a parte do teto via episode+community subgraph do Zep).

### 2.2 Modelo de dados-alvo

**(a) Promover bi-temporalidade no substrato (não só nas relações):**

| Onde | Mudança-alvo |
|---|---|
| `agent_memory_entity_relations` | `valid_to` passa a ser ESCRITO no ingest (invalidação), não NULL eterno (`knowledge_graph_service.py:551`); `valid_from` recebe timestamp real do episódio |
| `AgentMemory` | ganha `valid_from`/`valid_to` (migration dupla .py+.sql) — primeira vez que a memória de texto tem tempo de evento (`models.py:502-579` não tem) |
| episódio/proveniência | cada `valid_to` aponta para o episódio que o invalidou (turno + tool-call); reusa `session_turn_indexer` apontado em `critica/D-ontologia.md:208-210` |

**Risco estrutural (ver D§3):** com bi-temporalidade real, a constraint
`uq_entity_relation` (que hoje faz `ON CONFLICT DO UPDATE` somando weight,
`knowledge_graph_service.py:567-582`) deixa de fazer sentido — uma relação
invalidada e uma nova relação vigente entre as MESMAS entidades coexistem. A tabela
de relações vira uma **tabela-de-fatos versionada** (1 linha por versão de fato),
não 1 linha por par. Isso é uma migration cara e é o principal acoplamento com o
Eixo D — a decisão NÃO é local deste eixo.

**(b) Tabela de eventos de vigilância (`memory_vigilance_event`)**, append-only,
1 linha por achado do job offline: `kind ∈ {contradiction, staleness, reflection}`,
`memory_ids` (JSONB, as fontes citadas), `severity`, `detected_at`,
`action_taken ∈ {none, flagged, demoted, expired, pushed}`. Resolve o gap de o
achado de contradição hoje morrer num boolean (`has_potential_conflict`) sem
histórico nem proveniência.

### 2.3 Como encaixa nas 5 camadas do SDK

| Camada SDK | Componente do alvo |
|---|---|
| **5. Control (hooks/scheduler)** | job offline `vigilancia_coerencia` registrado no scheduler como step gated 1x/dia — espelha o KG cleanup (`sincronizacao_incremental_definitiva.py:1752-1788`). NUNCA no path SSE. |
| **2. Tools** | nova capacidade do `ontology_query_tool` / memory tools: consultar "fatos invalidados", "o que mudou desde X", responder com proveniência temporal |
| **4. Subagents** | a reflexão agendada (gerar insight de nível superior citando fontes) é tarefa natural de um subagent read-only barato (Haiku), espelhando o padrão `subagent_validator` |
| **3. Skills** | `gerindo-agente` ganha visão de saúde temporal (fatos obsoletos, contradições abertas) — hoje só vê memórias não-efetivas/conflito-boolean |
| **1. System prompt** | o resultado da vigilância não vai cru pro prompt; um achado confiável de "fato X foi invalidado" pode virar *operational directive* (Eixo A) ou um item de push (vigilância proativa) |

---

## PARTE 3 — CAMINHO INCREMENTAL (reaproveitando o existente)

> Ordenado por alavancagem e risco. Cada fase: [LIGAR]/[AJUSTAR]/[CONSTRUIR],
> dependência cross-eixo, flag, e o que destrava. Regra inviolável do eixo:
> **o job NUNCA roda no path SSE** — sempre RQ/APScheduler offline.

### Fase C0 — Job offline de coerência, REPORT-ONLY (detecta, não escreve)
**[CONSTRUIR] · Esforço M · Risco baixo (não muta acervo).**
- Novo step no scheduler, gated 1x/dia, espelhando o KG cleanup
  (`sincronizacao_incremental_definitiva.py:1752-1788` + registro de step `:2358`).
  Flag `USE_MEMORY_VIGILANCE` + `MEMORY_VIGILANCE_HOUR`/`_WEEKDAY` (mesmo padrão de
  `KG_CLEANUP_HOUR`/`_WEEKDAY`).
- O job varre o acervo INTEIRO procurando: (a) **pares contraditórios** —
  generaliza `_detect_conflicts_async` (`memory_mcp_tool.py:1397-1462`) de
  "memória nova vs acervo" para "acervo vs acervo", reusando a mesma faixa cosine
  0.50–0.85 + mesmo-domínio; (b) **staleness** — memórias com `updated_at` antigo
  + ausência de `valid_to` + entidade operacional volátil (total, saldo, baseline).
- Escreve SÓ em `memory_vigilance_event` (report-only). Nenhuma mutação de
  `AgentMemory`/relações ainda. Sai no dashboard `gerindo-agente`.
- **Destrava**: primeira visão de "o que está incoerente/obsoleto" sem risco; mede
  o volume antes de agir (decide thresholds de C2/C3 empiricamente).
- **Dependência**: nenhuma para detectar; consome melhor com Eixo E (sinal de
  qualidade) e Eixo D (substrato/ontologia). É a fundação do eixo.

### Fase C1 — Bi-temporalidade em AgentMemory + invalidação no ingest
**[CONSTRUIR] · Esforço G · Risco médio-alto (migration de constraint, ver D§3).**
- Migration dupla (.py+.sql, regra do projeto) adicionando `valid_from`/`valid_to`
  a `AgentMemory` (`models.py:502-579` hoje não tem) e fazendo `valid_to` da tabela
  de relações ser ESCRITO (`knowledge_graph_service.py:551` deixa de ser NULL eterno).
- No ingest, quando um fato novo contradiz um vigente (sinal vem do C0 ou do
  `_detect_conflicts_async`), **invalidar** o antigo (`valid_to = now`) com
  proveniência do episódio — não apagar (Zep arXiv:2501.13956: invalidação >
  descarte).
- **Risco codificado**: `uq_entity_relation` (`knowledge_graph_service.py:567`)
  precisa virar tabela-de-fatos versionada — migration cara, ACOPLADA ao Eixo D.
  Fazer atrás de flag e com backfill validado em staging antes de PROD.
- **Destrava**: o agente passa a saber "isso valia até X"; staleness deixa de ser
  silencioso. Habilita o push do C2.
- **Dependência**: C0 (sinal de contradição) + **Eixo D** (decisão de schema da
  ontologia — `uq_entity_relation` e episode subgraph; ver `critica/D-ontologia.md:234-237`).

### Fase C2 — Reflexão agendada citando evidência
**[CONSTRUIR] · Esforço M · Risco médio (custo LLM, controlado por threshold).**
- No mesmo job offline (C0), disparar reflexão quando a soma de `importance_score`
  dos fatos recentes de um domínio ultrapassar um threshold (Generative Agents
  arXiv:2304.03442). Gera insight de nível superior via Haiku/Sonnet read-only
  (subagent, padrão `subagent_validator`).
- **Inviolável**: o insight CITA os `memory_ids` das fontes (gravados em
  `memory_vigilance_event.memory_ids`). Reflexão sem proveniência é rejeitada.
- Um `valid_to` recém-setado (C1) em fato de alta importance vira **gatilho de
  push** — a vigilância proativa "ruptura nova/atraso novo" de
  `critica/D-ontologia.md:213,237`. O push em si é entregue por RQ/APScheduler,
  jamais no SSE.
- **Destrava**: insights de nível superior auditáveis + push proativo do que mudou.
- **Dependência**: C0 (job), C1 (`valid_to` como gatilho), **Eixo E** (só reflete
  sobre o que tem sinal de qualidade — senão recicla ruído), **Eixo A** (insight
  confiável pode virar directive).

### Fase C3 — Staleness → demote/TTL (agir sobre o que envelheceu)
**[AJUSTAR] · Esforço M · Risco médio (mexe no que é injetado).**
- Promover o achado de staleness do C0 de report-only para AÇÃO: memória obsoleta
  é rebaixada (demote: `priority`/`importance_score` para baixo) ou expira (TTL via
  `valid_to`). FadeMem (arXiv:2601.18642): decaimento como cidadão de primeira classe.
- **Reusar** a maquinaria existente: `maybe_move_to_cold` (`memory_consolidator.py:86`)
  já move memória de baixa eficácia para tier frio — estender o gatilho de "baixo
  `effective_count`" para incluir "stale + sem `valid_to` vigente".
- **Respeitar** a imunidade existente com cuidado: `category='permanent'` /
  `importance >= 0.7` são imunes à consolidação (`memory_consolidator.py:49-52`) —
  mas são EXATAMENTE as mais perigosas se obsoletas. A regra-alvo: imune a
  consolidação ≠ imune a invalidação temporal (um fato "permanente" pode ter
  `valid_to` setado por contradição factual).
- **Destrava**: fecha o loop — staleness para de ser injetada como verdade atual.
- **Dependência**: C0 (detector), C1 (`valid_to`/TTL), **Eixo E** (não rebaixar
  memória que ainda dá bom desfecho só por ser antiga — staleness ≠ idade pura).

---

## Fontes externas (ancoragem do alvo)

- **Zep — A Temporal Knowledge Graph Architecture for Agent Memory**
  (arXiv:2501.13956): bi-temporalidade (`t_created`/`t_valid`/`t_invalid`), fato
  novo invalida o antigo COM proveniência do episódio, invalidação > descarte.
  https://arxiv.org/abs/2501.13956
- **Generative Agents — Interactive Simulacra of Human Behavior**
  (arXiv:2304.03442): reflexão dispara quando soma de importance > threshold; o
  insight de nível superior CITA as memórias-fonte. https://arxiv.org/abs/2304.03442
- **FadeMem** (arXiv:2601.18642): decaimento/TTL e esquecimento gradual como
  primitiva de primeira classe da memória de agente.
- **CoALA — Cognitive Architectures for Language Agents** (arXiv:2309.02427):
  separação memória de trabalho / episódica / semântica e processos de decisão
  sobre memória (incl. consolidação/esquecimento agendados).
  https://arxiv.org/abs/2309.02427
- `critica/D-ontologia.md:213,237` — promove a vigilância proativa (ruptura/atraso
  novo via `valid_to` recém-setado) de "citação de passagem" a parte do ALVO; o
  episode subgraph do Zep como substrato de proveniência da reflexão.

---

### O que NÃO está verificado

- **"0/7204 relações com bi-temporal preenchida"**: não consultei o banco PROD. O
  CÓDIGO confirma que `valid_to` nunca é escrito (`knowledge_graph_service.py:551`)
  e `valid_from` chega `None` no MVP (`:539,546`), o que torna o número plausível —
  mas a contagem exata (7204) não foi reconfirmada contra PROD.
- **Volume real de contradições/staleness no acervo atual**: o C0 existe
  justamente para medir isso antes de agir; não há baseline hoje.
- **Custo agregado da reflexão agendada (C2)** em volume real: dimensiona o
  threshold de importance e o nº de domínios por execução; não muda o desenho.
- **Se `session_turn_indexer` (citado em `critica/D-ontologia.md:208-210`) cobre
  todos os paths (web vs Teams vs persistente)** como fonte de episódio para a
  proveniência do `valid_to` — precisa ser verificado antes do C1.
- **Decisão de escopo `user_id` da ontologia/fatos** (memória-empresa `user_id=0`
  vs pessoal): apontada como pendência em `critica/D-ontologia.md:230-233`; afeta
  diretamente como o C0 agrupa pares contraditórios. É decisão do Eixo D.

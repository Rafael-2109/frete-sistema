<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/blueprint-agente/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# BLUEPRINT MESTRE — A Evolução do Agente Logístico Nacom

> **Papel:** BLUEPRINT MESTRE — A Evolução do Agente Logístico Nacom.

## Indice

- [1. VISÃO ARQUITETURAL](#1-visão-arquitetural)
- [2. GRAFO DE DEPENDÊNCIAS ENTRE EIXOS](#2-grafo-de-dependências-entre-eixos)
- [3. SEQUÊNCIA DE EVOLUÇÃO EM ONDAS (ordenada por DEPENDÊNCIA ARQUITETURAL)](#3-sequência-de-evolução-em-ondas-ordenada-por-dependência-arquitetural)
  - [ONDA 0 — A FUNDAÇÃO FÍSICA: entidade de passo/turno + registry descritivo](#onda-0-a-fundação-física-entidade-de-passoturno-registry-descritivo)
  - [ONDA 1 — A FUNDAÇÃO SEMÂNTICA: sinal de qualidade step-level + higiene da ontologia](#onda-1-a-fundação-semântica-sinal-de-qualidade-step-level-higiene-da-ontologia)
  - [ONDA 2 — O ATUADOR DE PLANEJAMENTO: super-loop com verifier de domínio](#onda-2-o-atuador-de-planejamento-super-loop-com-verifier-de-domínio)
  - [ONDA 3 — FECHAR O FLYWHEEL: promoção automática gated + ontologia consultável](#onda-3-fechar-o-flywheel-promoção-automática-gated-ontologia-consultável)
  - [ONDA 4 — O TETO DE ESCALA: registry executável + Skill-RAG + injeção `<world_model>`](#onda-4-o-teto-de-escala-registry-executável-skill-rag-injeção-world_model)
- [4. POR EIXO — ESTADO → ALVO → PRIMEIRA ALAVANCA (incorporando a crítica)](#4-por-eixo-estado-alvo-primeira-alavanca-incorporando-a-crítica)
- [5. INVARIANTES A PRESERVAR E RISCOS ARQUITETURAIS](#5-invariantes-a-preservar-e-riscos-arquiteturais)
  - [O que NÃO está verificado (honestidade arquitetural)](#o-que-não-está-verificado-honestidade-arquitetural)
- [Contexto](#contexto)

> Síntese dos 5 eixos (A flywheel · D ontologia · B planejador · E qualidade · F governança),
> integrando blueprint + crítica de cada um, num desenho **coerente, ambicioso e realizável**.
> Lente de TETO: volume dimensiona INFRAESTRUTURA, nunca o valor de uma capacidade.
> Convenção: **[CONFIRMADO `arquivo:linha`]** = verificado no código · **[PROPOSTA]** = design novo.

---

## 1. VISÃO ARQUITETURAL

Hoje o agente é um **roteador reativo single-shot** de classe alta: 5 camadas SDK bem construídas (system_prompt v4.3.3, 12 MCP tools, ~50 skills, 16 subagentes, 8 hooks), uma camada de inteligência rica em 17 services, um Knowledge Graph **povoado e ativo** (2.025 entidades, 7.215 relações em PROD — [CONFIRMADO `embeddings/config.py:157`]), memória multi-tier com embeddings Voyage+pgvector, e um diálogo de auto-melhoria (D8) que efetivamente commita código em `main`. Mas é um corpo com sensores ricos e **atuadores desligados**: o sinal de "qualidade" mede eco semântico e atividade, não acerto ([CONFIRMADO `_helpers.py:497`, `insights_service.py:229`]); o atuador mais potente está OFF ([CONFIRMADO `USE_OPERATIONAL_DIRECTIVES=false`, `feature_flags.py:215`]); a orquestração vive como **prosa no prompt** que o modelo pode ignorar ([CONFIRMADO `system_prompt.md:664-838`]); o grafo é um booster de recall que o agente nunca *vê* como modelo de mundo ([CONFIRMADO `query_graph_memories` devolve só memory-IDs, `memory_injection.py:976-1001`]); e as capacidades cresceram organicamente sem registro único de escopo/lifecycle ([CONFIRMADO escopo disperso em `skills_whitelist.py` + `settings.py:40` + 16 frontmatters]).

O agente VIRA um **copiloto logístico que ENTENDE o negócio, PLANEJA, e APRENDE sobre si — medido por qualidade real, sobre uma base governada**. Concretamente: (D) o KG deixa de recuperar fragmentos de conversa e passa a ser a **Ontologia Logística da Nacom** — entidades reais (cliente/SKU/transportadora/pedido/lote) com chave canônica para a base, arestas que codificam a física do negócio (incoterm→responsável-frete, SKU→ruptura, cliente→agenda), **bi-temporal** (fato novo invalida o antigo, com proveniência do episódio que o originou). (B) sobre esse substrato, um **modo planejador** — super-loop determinístico plan→execute→**verify(gate real)**→replan→escalate — promove os primitivos hoje cosméticos (Task*, `plan_mode`, os dois validadores) a mecanismo, com o **plano tipado pela ontologia** e verificado contra os guards de domínio já codificados (G021/G031/G-MO-01/direção-MIGRAÇÃO). (E) toda ação de risco ganha uma nota: o **Quality Spine step-level** funde sinal humano + outcome ambiental + judge-de-raciocínio, ancorado no **audit hook Odoo determinístico que já existe** ([CONFIRMADO `operacao_odoo_auditoria` correlaciona cada `execute_kw` a sessão+tool_use_id, `CLAUDE.md:291-293`, `hooks.py:114,131`]). (A) esse sinal vira a **moeda do flywheel**: re-calibra importância de memória por desfecho (com **atribuição causal de culpa** por passo, não correlação grosseira), e promove heurística→diretriz **automaticamente, gated por eval, em shadow/A-B, com auto-rollback por drift**. (F) tudo isso repousa num **Capability Registry** — tools+skills+subagentes como nós de um grafo de escopo com pré/pós-condições, fonte única que deriva deny-lists, catálogos e routing, e que **é o próprio espaço de estados do planejador**. O fio condutor: o sistema deixa de aprender a ser *consistente consigo mesmo* e passa a aprender a ser *correto sobre o mundo logístico da Nacom*, com cada elo do circuito ancorado em código que já existe e foi conscientemente estacionado esperando exatamente este sinal.

---

## 2. GRAFO DE DEPENDÊNCIAS ENTRE EIXOS

Os blueprints partiram de uma hipótese de fundação (E habilita A; D habilita B; F sustenta tudo). As **críticas refinaram-na em três pontos decisivos**, que mudam o grafo:

1. **A fundação real, comum a A, E e B, é uma entidade de schema que não existe: o "turn"/"step".** A§C2 e E§4.1 provaram que o sistema só tem `AgentSession` (blob), `AgentSessionCost` (por-mensagem) e `AgentInvocationMetric` (por-spawn de subagent) — [CONFIRMADO `models.py:22,1394,1597`]; **não há tabela de turn nem turn_id estável**. Sem ela, A (re-calibração), E (spine) e B (PlanState verificável) escrevem em granularidades que não se joinam. **Esta é a fase-zero de TODO o grafo.**
2. **A "qualidade" e a "ontologia" são co-dependentes, não sequenciais.** D§Lacuna#4: sem o sinal de E não há como saber se a ontologia melhora ou piora respostas (grafo errado é PIOR que keyword hardcoded). A§4.4: o sinal ambiental de maior valor (operação Odoo revertida) exige a ontologia de D para mapear turn→entidade→desfecho. Logo **E↔D é um ciclo de mútua validação**, não uma seta.
3. **O sinal não-gameável que ancora tudo já existe e é determinístico: o audit Odoo (R9).** E§5 e A§5 convergem: o ground-truth de passo (sucesso/rollback/guard disparado) está em `operacao_odoo_auditoria` [CONFIRMADO]. É a raiz que torna o judge-LLM honesto (componente ambiental dominante anti-reward-hacking, C1 da crítica A).

```
                      ┌──────────────────────────────────────────────┐
   FUNDAÇÃO 0 ───────►│  S0: entidade STEP/TURN  (tabela 1ª classe)  │  habilita A,E,B
   (schema)           │  chave = AgentSessionCost.message_id          │
                      │  [CONFIRMADO joinável, models.py:1413 UNIQUE] │
                      └──────────────────────────────────────────────┘
                               │              │              │
                ┌──────────────┘              │              └──────────────┐
                ▼                             ▼                             ▼
   ┌────────────────────┐      ┌──────────────────────────┐   ┌────────────────────┐
   │ E  QUALIDADE        │◄────►│ D  ONTOLOGIA             │   │ F  GOVERNANÇA       │
   │ Quality Spine       │ ciclo│ Modelo de mundo Nacom    │   │ Capability Registry │
   │ step-level (PRM)     │ valid.│ bi-temporal + proveniência│   │ (tools+skills+sub)  │
   │ âncora: R9 Odoo     │      │ âncora: carteira/Odoo    │   │ grafo de escopo     │
   └─────────┬───────────┘      └────────────┬─────────────┘   └─────────┬──────────┘
             │ sinal de recompensa            │ substrato de mundo        │ mapa verdadeiro
             │ (causal, por passo)            │ (entidades + invariantes) │ de capacidades
             ▼                                ▼                           │
   ┌─────────────────────┐      ┌──────────────────────────┐             │
   │ A  FLYWHEEL          │◄─────│ B  PLANEJADOR            │◄────────────┘
   │ recalibra + promove  │ plano│ plan→exec→VERIFY→replan  │  registry = espaço de
   │ gated por eval+drift │ tipado│ verifier DOMAIN (guards) │  estados do planner (F§5)
   │ attribution causal   │─────►│ template de plano (A↔B)  │
   └─────────────────────┘      └──────────────────────────┘
```

**Leitura do grafo (o que habilita o quê):**
- **S0 (entidade step/turn) é a fundação de tudo.** Não é um eixo; é o pré-requisito de A, E e B. Reusa uma chave que **já existe e é joinável**: `AgentSessionCost.message_id` (UNIQUE) [CONFIRMADO `models.py:1413`] — resolve a colisão de IDs que E§4.1 apontou (o SDK session_id efêmero NÃO serve; o nosso UUID+message_id, sim).
- **E habilita A** (a tese original): sem sinal de qualidade o flywheel gira no vácuo. Confirmado e central.
- **D habilita B** (a tese original): plano *grounded* exige modelo de mundo, não regex de domínio. Confirmado — e B§1.b prova que o TRIAGE NÃO pode reusar `model_router` (que é o *inverso*, um rebaixador de prompts simples, [CONFIRMADO `model_router.py:147-151`]).
- **F sustenta A e B** (a tese original) — e a crítica F§5 eleva: F não só *sustenta*, **F É o espaço de estados de B** quando o registry codifica pré/pós-condições. O mapa não é lido pelo planejador; o mapa É o planejador.
- **E↔D em ciclo** (refino da crítica): mútua validação. Desenhar juntos.
- **A e E compartilham o substrato causal** (attribution_judge de A§5 = step_quality de E§5): **é a mesma chamada de LLM** lendo a trajetória; A pede o *laudo de culpa*, E pede a *nota por passo*. Unificar num só componente.

**Fundação(ões) identificada(s):** (i) **S0 schema de step** — fundação física; (ii) **o par E↔D** — fundação semântica (sinal + mundo); (iii) **F registry** — fundação estrutural que mantém o mapa verdadeiro. A ordem de evolução abaixo decorre disto, NÃO de esforço.

---

## 3. SEQUÊNCIA DE EVOLUÇÃO EM ONDAS (ordenada por DEPENDÊNCIA ARQUITETURAL)

> Critério único: **o que DESTRAVA o resto vem primeiro**. Nunca volume, nunca esforço.
> Cada onda nasce atrás de flag OFF (padrão do repo: cold-move, `ui_policy_lint` report→enforce).

### ONDA 0 — A FUNDAÇÃO FÍSICA: entidade de passo/turno + registry descritivo
*O que entra:*
- **S0a — Tabela `agent_step` (ou `agent_turn`) de 1ª classe** [PROPOSTA], keyed por `(session_uuid, message_id)` reusando `AgentSessionCost.message_id` UNIQUE [CONFIRMADO `models.py:1413`] como a chave joinável que A e E disputavam. Populada **no fim da thread PRIMARY** (onde nosso UUID + msg_id coexistem, R10), NÃO no `_stop_hook` (que só vê o SDK session_id efêmero — erro de fundação que E§4.1 e A§C2 pegaram). O `_stop_hook` vira apenas gatilho assíncrono.
- **S0b — Consolidar a deny-list dispersa** (F-Fase0): mover `SPED_SKILLS_RESERVED` de `settings.py:40` [CONFIRMADO] para `skills_whitelist.py` num 4º grupo; `client.py:114` passa a ler UMA fonte.
- **S0c — Capability Registry DESCRITIVO** (F-Fase1, corrigido): `SkillEntry` (propriedades intrínsecas) + **`SkillBinding` (aresta N:M skill↔agente)** — porque `exposure` NÃO é escalar (`consultando-sql` é declarada por 9 dos 16 agentes E pelo principal, F§1.2). Populado por `agent_loader._parse_skills` [CONFIRMADO `agent_loader.py:239-272`] + parse das 5 tabelas-catálogo do estoque (já são um registry em Markdown, F§2). Flag OFF: só descreve, não muda comportamento.

*O que destrava:* a chave de junção sem a qual A, E e B escrevem lixo não-joinável (a lacuna nº 1 de duas críticas); a fonte única de capacidades que B e A precisam confiar; fim do drift doc↔código.
*O que reaproveita:* `AgentSessionCost.message_id` UNIQUE [CONFIRMADO `models.py:1413`]; padrão `insert_metric` SAVEPOINT [CONFIRMADO `models.py:1664-1719`]; `agent_loader._parse_skills` [CONFIRMADO `agent_loader.py:239-272`]; catálogos do estoque [CONFIRMADO `estoque/CLAUDE.md:120-168`].
*Risco:* baixo — schema aditivo + registry read-only. **Acoplamento a evitar:** NÃO escrever a entidade de passo no `_stop_hook` (corrida R10).

### ONDA 1 — A FUNDAÇÃO SEMÂNTICA: sinal de qualidade step-level + higiene da ontologia
*O que entra (E e D em paralelo, pois se validam mutuamente):*
- **E1 — Sinais humanos/implícitos para a entidade de passo (grátis):** capturar o `score` que `detect_frustration` JÁ calcula e é descartado no callsite ([CONFIRMADO `chat.py:560` pega só o prompt enriquecido, `sentiment_detector.py:167`]); **promover** os 👍👎 de `data['feedbacks']` (já persistidos — a crítica A§4.1 corrigiu o blueprint: NÃO estão inertes, estão mal-domiciliados em JSONB não-joinável) para a entidade de passo. **Ressuscitar `_adjust_importance_for_corrections`** deletado em v2.2 "porque nenhum sinal o alimentava" [CONFIRMADO comentário `memory_injection.py:332-335`] — agora alimentado.
- **E2/A1 — O componente UNIFICADO `attribution_judge` (= step_quality):** judge batch (clona `subagent_validator` [CONFIRMADO esqueleto pronto `subagent_validator.py:28-42,84-97`]) que, ancorado no **resultado determinístico do audit Odoo R9** ([CONFIRMADO `operacao_odoo_auditoria`]), produz por passo de risco um **laudo causal** `{score, label, componente_culpado: skill|tool|subagent|memória|diretiva, evidência}` — o teto 2026 (Process Reward Model, A§5/E§5). Mesma chamada de LLM; output rico em vez de nota escalar. O componente **ambiental (R9 + os 4 detectores de `friction_analyzer` já prontos** [CONFIRMADO `friction_analyzer.py:186,274,319,376`]) domina o judge na decisão de promoção (defesa anti-reward-hacking, C1).
- **D0 — Higiene + resolução-ao-nó (reescopada de P para M, D§2.1):** corrigir o leak `:E/:A` [CONFIRMADO `knowledge_graph_service.py:403`]; **interceptar o merge** para resolver menções ao nó canônico ANTES do dedup (a causa real de `with_key=0` é o LLM-keyless vencer a corrida, NÃO falta de persistência — `_upsert_entity` JÁ grava a chave [CONFIRMADO `knowledge_graph_service.py:468`]).
- **D0.5 — DECISÃO DE ESCOPO `user_id=0`** (D§Lacuna#1, pré-requisito irreversível): nós canônicos de negócio são da EMPRESA (`user_id=0`), reusando o padrão de memória-empresa e o `query_graph_memories` que já faz `ANY([user_id,0])` [CONFIRMADO]. Sem isto, D2 explode por usuário.

*O que destrava:* a moeda do flywheel (sinal causal de acerto, não eco) E a primeira validação de se a ontologia ajuda. O par E↔D.
*O que reaproveita:* `subagent_validator` inteiro [CONFIRMADO]; `friction_analyzer` (4 detectores) [CONFIRMADO]; `operacao_odoo_auditoria` (R9) [CONFIRMADO]; `_adjust_importance_for_corrections` (código estacionado) [CONFIRMADO]; `sql_evaluator_falses_service` como motor de calibração [CONFIRMADO `:1-21,35`].
*Risco:* médio — judge mal-calibrado (mitigado: ambiental domina + spot-check humano + held-out anti-gaming). **NÃO redefinir `effective_count` in-place** (3 consumidores acoplados, A§2/§3) — usar coluna nova `outcome_effective_count`.

### ONDA 2 — O ATUADOR DE PLANEJAMENTO: super-loop com verifier de domínio
*O que entra (B, agora com substrato de D e sinal de E):*
- **B1 — PlanState durável + Plan tools** (promoção dos Task* cosméticos [CONFIRMADO `client.py:696-739` só pinta UI]) em `AgentSession.data['plan']`, reusando `flag_modified` [CONFIRMADO já usado por `subagent_validator.py:183`] e `output_format` nativo [CONFIRMADO threaded `routes/chat.py:169-174`].
- **B-TRIAGE — classificador NOVO semântico** (B§1.b corrigiu: NÃO reusar `model_router`, que é o inverso): decompõe meta em steps sobre **entidades do KG de D**, não contagem de palavras.
- **B2 — VERIFY como gate real**, com TRÊS verifiers: `arithmetic` (promove `_self_correct_response` de caveat a retry [CONFIRMADO advisory+OFF `client.py:1378-1383`, `feature_flags.py:48`]); `adversarial` (promove `subagent_validator` de badge a veredito **lido pelo loop** — a ponte `get_subagent_summary` JÁ é exercitada [CONFIRMADO `subagent_validator.py:126`]); e **`domain`** — o que B§4.c/§5 elevaram: valida o artefato contra a **ontologia (D)** e os **guards já codificados** (G021/G031/G-MO-01/direção-MIGRAÇÃO vivem em código). Primeiro passo de menor risco (B§correção): rodar o validator em **SOMBRA** antes de virar gate.
- **B3 — REPLAN com budget + escalate:** finalmente escreve `escalated_to_human` (campo morto da "Fase D" [CONFIRMADO `models.py:1647`]).

*O que destrava:* falha vira recuperação; verificação vira passo; o **plano tipado** que A precisa para promover. O audit trail que operações irreversíveis (SEFAZ, estoque) exigem.
*O que reaproveita:* `_self_correct_response` [CONFIRMADO `client.py:792`]; `subagent_validator` [CONFIRMADO]; guards das skills de estoque (em código); `pending_questions.py` (R-MULTIWORKER) para aprovação Web.
*Risco:* médio-alto. **Lacuna a fechar antes de B4 (B§4.a):** verificar se subagentes JÁ recursam via Task ([CONFIRMADO instrução contraditória `gestor-estoque-odoo.md:73` "use Task tool" vs frontmatter restrito]) — se sim, scatter-gather é **domar recursão solta**, não criar capacidade. **Aprovação de plano = Web-only na largada** (Teams é turn-based, B§4.b).

### ONDA 3 — FECHAR O FLYWHEEL: promoção automática gated + ontologia consultável
*O que entra:*
- **A3 — Eval runner automatizado + gate no D8** ([CONFIRMADO golden datasets manuais `evals/README.md:79`; D8 commita direto em main `dominio-8.md:13`]): processo **EXTERNO** ao agente avaliado (A§3 — não o réu presidindo o júri), modo report-only→enforce.
- **A4 — Promoção automática de diretriz** (liga `USE_OPERATIONAL_DIRECTIVES` com segurança): candidata→shadow/A-B→regression-gate→promove→monitora-drift→auto-despromove. O **plano tipado que funcionou (zero replan, invariantes OK) é o artefato promovível** (B§5↔A). Reusa `_build_operational_directives` inteiro [CONFIRMADO pronto `memory_injection.py:420`] + `model_router` A/B per-request.
- **D2/D3/D4 — Ontologia consultável e viva:** bootstrap estrutural das TABELAS-mestre corretas (`carteira_principal`/`transportadoras`, NÃO `entity_indexer` que lê `contas_a_pagar` — D§2.2) [CONFIRMADO erro de peça]; fatos bi-temporais + **episode subgraph de proveniência** (D§5, reusa `session_turn_indexer.py`); tool MCP `query_ontology`.

*O que destrava:* o circuito fecha sobre acerto; o agente raciocina sobre o negócio; promoção autônoma segura.
*Risco:* alto (muda comportamento ativo) — por isso vem por último, sobre fundações confiáveis.

### ONDA 4 — O TETO DE ESCALA: registry executável + Skill-RAG + injeção `<world_model>`
- **F4/F5 — Routing gerado + Skill-RAG por domínio** (resolve o budget estruturalmente, não por tampão de deny-list); separar catálogo-gerável de **boundaries comportamentais críticas** que ficam no prompt (F§3 — senão a geração apaga regra de negócio Web/Teams).
- **F§5 + D5 — O registry como espaço de estados do planejador:** pré/pós-condições dos contratos de estoque viram operadores; fluxos L3 viram planos cacheados; `<world_model>` substitui `_DOMAIN_KEYWORDS` **mantendo-o como fallback** (D§3 — defense-in-depth para cold start).

---

## 4. POR EIXO — ESTADO → ALVO → PRIMEIRA ALAVANCA (incorporando a crítica)

**A — FLYWHEEL.** Estado: circuito conectado de ponta a ponta mas girando sobre **eco/atividade**, não acerto — `effective_count` = similaridade cosseno memória↔resposta [CONFIRMADO `_helpers.py:497`], `verified` = opinião de Sonnet sem baseline [CONFIRMADO `improvement_suggester.py:415`], atuador `USE_OPERATIONAL_DIRECTIVES` OFF [CONFIRMADO `feature_flags.py:215`]. Alvo: flywheel **eval-driven com credit assignment causal** — não "este turno foi bom?" mas "QUAL passo/memória/diretriz estragou o turno?" (Process Reward Model, A§5). A re-calibração de importância vira cirúrgica (penaliza só o componente culpado, não toda memória presente). Primeira alavanca: **a entidade de passo (S0) + ressuscitar `_adjust_importance_for_corrections`** [CONFIRMADO estacionado `memory_injection.py:332`] alimentado pelo sinal humano que já existe mas está mal-domiciliado em `data['feedbacks']` (A§4.1 corrigiu: não inerte, não-joinável).

**D — ONTOLOGIA.** Estado: KG **povoado mas é booster de recall** — devolve memory-IDs, nunca o subgrafo [CONFIRMADO `memory_injection.py:976-1001`]; 62% das entidades são `conceito` catch-all, `with_key=0` para produto/cliente/transportadora [CONFIRMADO PROD], relações 89,5% co-ocorrência. Alvo: **Ontologia Logística bi-temporal, tipada e consultável** com `entity_key` para a fonte canônica e o **episode subgraph de proveniência** (Zep 3-subgrafos, D§5) que torna a entity-resolution reversível e dá ao flywheel o sinal auditável. Primeira alavanca: **DECISÃO `user_id=0`** (D§Lacuna#1, pré-requisito de tudo) + interceptar o merge para resolver-ao-nó (a causa real de `with_key=0`, não backfill trivial — D§2.1).

**B — PLANEJADOR.** Estado: **single-shot ReAct**, orquestração é prosa que o modelo pode ignorar [CONFIRMADO `system_prompt.md:664-838`]; Task* só pintam UI [CONFIRMADO `client.py:696`]; verificação advisory e OFF [CONFIRMADO `client.py:792`, `feature_flags.py:48`]; subagentes são folhas. Alvo: **super-loop plan→execute→verify→replan** com o **plano e o verifier TIPADOS PELA ONTOLOGIA** (B§5) — `domain_object` + `invariants_to_check` reusando guards já codificados, transformando o gate de "linter de forma" em "verificador com modelo de mundo Nacom". Primeira alavanca: **promover `subagent_validator` de badge a veredito-lido em SOMBRA** (B§correção — menor raio, zero risco no caminho quente, calibra o threshold antes do gate).

**E — QUALIDADE.** Estado: telemetria mede tudo **menos qualidade** (custo/latência/tokens); `escalated_to_human`/`user_correction_received` são **colunas fantasma nunca escritas** [CONFIRMADO `models.py:1647`, grep = 0 writes]; `resolution_rate` = teve-tool+≥4-msgs [CONFIRMADO `insights_service.py:229`]. Alvo: **Quality Spine STEP-level (PRM)** ancorado no **audit hook Odoo determinístico que já existe** (E§5) — mede "essa transferência de 320k unidades foi a certa?", não "essa conversa foi boa?". Primeira alavanca: **a entidade de passo (S0) com a chave correta** — `AgentSessionCost.message_id` [CONFIRMADO `models.py:1413`], NÃO o SDK session_id efêmero (E§4.1, o bloqueio nº 1).

**F — GOVERNANÇA.** Estado: **duas culturas coexistindo** — madura e formal (estoque: contrato+lifecycle+antipadrões) vs orgânica (resto); escopo disperso em 4 lugares; o estouro de budget da meta-tool `Skill` é o sintoma [CONFIRMADO `skills_whitelist.py:5-11`]. Alvo: **Capability Registry** (tools+skills+subagentes no mesmo grafo de escopo — F§4.1 elevou de SKILL para CAPABILITY) como **grafo executável com pré/pós-condições = espaço de estados do planejador** (F§5). Primeira alavanca: **registry descritivo com `SkillBinding` (aresta N:M), NÃO `exposure` escalar** (F§1.2 — senão nasce com drift no dia 1), reusando os 16 frontmatters e as 5 tabelas-catálogo do estoque.

---

## 5. INVARIANTES A PRESERVAR E RISCOS ARQUITETURAIS

**Invariantes que NÃO podem quebrar ao evoluir:**
1. **R10 — thread PRIMARY vs DEFESA generator.** A entidade de passo (S0) e o spine devem ser escritos **no fim da thread PRIMARY** (onde nosso UUID + msg_id coexistem), NÃO no `_stop_hook` — que só conhece o SDK session_id efêmero. Introduzir uma terceira escrita correlacionada via hook adiciona um participante exatamente na corrida que R10 doma (E§1.2, a invariante mais relevante e omitida pelo blueprint E).
2. **Chave de identidade: nosso UUID + `message_id`, nunca o SDK session_id.** Confundi-los "causa sessão perdida" (R1). `AgentSessionCost.message_id` UNIQUE [CONFIRMADO `models.py:1413`] é a chave joinável correta.
3. **Separação de canais Web/Teams.** Aprovação de plano (B), feedback explícito (`feedback.py` é só-Web, E§1.2), e injeção `<world_model>` em `_build_routing_context` (compartilhado Web+Teams, D§3) — todos cruzam essa fronteira. Modo planejador com aprovação = Web-only na largada; sinal explícito do Teams (Adaptive Card, R4) precisa de caminho próprio.
4. **Constituição do estoque "1 skill = 1 objeto" / `--dry-run` first / fluxos>>skills** [CONFIRMADO `estoque/CLAUDE.md:28-40,109-115`]. O verifier `domain` (B) e o registry (F) **generalizam** esta constituição — não a violam. O dry-run-first é o par natural "previsto vs executado" para o credit assignment (E§5).
5. **Guards de domínio codificados** (G021/G031/G-MO-01, direção-MIGRAÇÃO por `diff_qtd`, guard CICLAMATO, GTIN/SEFAZ G035): são a verdade logística que o verifier `domain` deve checar. Errar a direção de uma transferência custou estoque fantasma de 6 dígitos (MEMORY.md: azeite↔soja, ajustes-Maria-LF, quant-negativo).
6. **Best-effort / flag-gated dos services (R1-R2) + thread-safety ContextVar.** Jobs de bootstrap da ontologia (D2) e o judge batch (E/A) rodam em RQ/APScheduler, **nunca no path SSE** (D§1) nem inline no save de memória.
7. **Caching da Camada 1.** `<operational_directives>` e `<world_model>` continuam injetados via hook (dinâmico, fora do cache do system_prompt estático).

**Riscos arquiteturais (e mitigação):**
- **Reward-hacking** (A§C1): fechar A1→A4 com judge cego ensinaria o agente a agradar o judge. Mitigação: o judge é *reasoning* (laudo causal justificado), e o **componente ambiental não-gameável (R9 Odoo) domina** na decisão de promoção; held-out anti-gaming + spot-check humano 5-10%.
- **Recursão de subagente solta** (B§4.a): se subagentes já recursam via Task [CONFIRMADO instrução contraditória `gestor-estoque-odoo.md:73`], B4 é *domar*, não criar — risco sobe de médio para alto. Verificar a propagação SDK 0.2.87 antes.
- **Gate travando o único atuador autônomo** (A§3): o eval no D8 deve ser processo EXTERNO + report-only→enforce, senão um eval flaky trava o commit autônomo em main.
- **Registry invertendo a cultura demand-driven** (F§3): CI guard precisa de **auto-seed `incubating`** para skill nova (warning, não erro) — senão vira atrito contra o fluxo do Rafael.
- **Geração apagando regra de negócio** (F§3): separar catálogo-gerável de boundaries comportamentais críticas (`<boundary critical="true">` faturamento/baseline) que ficam escritas à mão no prompt.
- **Mudança de constraint bi-temporal** (D§3): `uq_entity_relation` precisa virar tabela-de-fatos ou UPDATE-de-valid_to + INSERT — migration de constraint, não só colunas aditivas; rollback caro se não desenhado como tabela separada.
- **Semântica de `effective_count`** (A§3): coluna NOVA `outcome_effective_count`, nunca redefinir in-place (cold-move + dashboard + builder de diretrizes acoplados).

---

### O que NÃO está verificado (honestidade arquitetural)
- Propagação de `Task` para subprocesso de subagente no SDK 0.2.87 (decide o risco de B4).
- Volume/custo de Voyage no bootstrap D2 e do judge online em turnos longos de Odoo (dimensiona INFRA — nº de workers, sampling — NÃO o valor da capacidade).
- Conteúdo de `tool_skill_mapper` (service L5) — possível reuso para Skill-RAG (F§2), a auditar antes da Onda 4.
- Campos exatos de agenda/incoterm em `carteira_principal`/`agendamentos_entrega` (D1 valida contra os 298 schemas).

## Contexto

Documento — evolucao do agente logistico. Tema: BLUEPRINT MESTRE — A Evolução do Agente Logístico Nacom

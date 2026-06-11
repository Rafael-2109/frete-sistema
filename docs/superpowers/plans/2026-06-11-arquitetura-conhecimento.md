<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de implementacao da arquitetura de conhecimento (memorias + agents + skills + camada estatica)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-11
-->
# Arquitetura de Conhecimento — Plano de Implementacao (Jeito X)

> **Papel:** plano executavel derivado do estudo macro-arquitetural 2026-06-11 (12 agentes:
> 5 mapas por camada + 2 cruzamentos + 3 propostas + 2 juizes — evidencia completa em
> `relatorios/arquitetura_x_2026-06-11/`, local nao-versionado). Reorganiza memorias (dev e web),
> agents, skills e camada estatica como ESTAGIOS de um ciclo de vida com trilhos de promocao
> e enforcement, sem re-arquitetura de substratos. **Abra quando:** for executar/retomar
> qualquer fase (Item 0, F0, F1, F2) ou decidir se uma mudanca de conhecimento respeita o
> papel canonico por camada.

> 🔵 **PROXIMA SESSAO — RETOMAR AQUI:** plano aprovado em conversa com Rafael 2026-06-11
> (4 decisoes registradas na secao Decisoes). Nada executado ainda. Comecar pelo Item 0
> (minutos) e F0 (T0.1 → T0.4). Worktree: `feat/arquitetura-conhecimento`.
> Cada fase ganha detalhamento TDD bite-sized na propria sessao de execucao
> (padrao text-to-sql S1-S3); este doc e o programa.

## Indice

- [Origem e evidencia](#origem-e-evidencia)
- [Decisoes registradas (Rafael, 2026-06-11)](#decisoes-registradas-rafael-2026-06-11)
- [Diagnostico em 5 fatos](#diagnostico-em-5-fatos)
- [Arquitetura-alvo: papel canonico por camada](#arquitetura-alvo-papel-canonico-por-camada)
- [Ontologia de captura T1-T6 (tabela de decisao, nao schema)](#ontologia-de-captura-t1-t6-tabela-de-decisao-nao-schema)
- [Metricas de sucesso (contrato hoje → alvo)](#metricas-de-sucesso-contrato-hoje--alvo)
- [ITEM 0 — Verificacoes antes de tudo (minutos)](#item-0--verificacoes-antes-de-tudo-minutos)
- [FASE F0 — Dor ativa, so certeza (~1 semana)](#fase-f0--dor-ativa-so-certeza-1-semana)
- [FASE F1 — Estancar a fonte do drift (2-3 semanas)](#fase-f1--estancar-a-fonte-do-drift-2-3-semanas)
- [FASE F2 — Decisoes por medida (condicionada a gates)](#fase-f2--decisoes-por-medida-condicionada-a-gates)
- [Lista NAO-FAZER (governanca permanente)](#lista-nao-fazer-governanca-permanente)
- [Riscos](#riscos)
- [Rastreamento](#rastreamento)
- [Fontes](#fontes)

## Origem e evidencia

Estudo 2026-06-11 com queries read-only em PROD (`sistema-fretes-db`) + leitura integral de
codigo/docs. Relatorios em `relatorios/arquitetura_x_2026-06-11/` (12 arquivos: 01-05 mapas,
06 cross-layer, 07 avaliacao adversarial da proposta KG, 08-* tres propostas, 09-* dois juizes).
Motivacao original: conversa do Rafael com outro assistente sobre duplicacao de memorias
(`app/agente/conversa.md`) — diagnostico "classificacao != identidade" absorvido; prescricao
"KG como autoridade de identidade" rejeitada com dados (07 §2: KG retorna 0 memorias em toda
injecao PROD; 700 nomes poluidos `:E`/`:A`; 3,6% das entidades canonicas linkadas; o componente
`aspecto` fragmenta como os paths — 18+ variantes de "conciliacao").

Fatos load-bearing re-verificados em 2026-06-11 nesta branch (e58a11d54):
`pattern_analyzer.py` com 0 ocorrencias de `save_version`; `pattern_analyzer.py:962` dominio
texto livre; `ROUTING_SKILLS.md:19` "54 invocaveis" (reais: 53); `tool_skill_mapper.py:109`
cita skill extinta `lendo-documentos`; docstring L1 de
`app/odoo/estoque/orchestrators/inventario_pipeline.py` com nome antigo; CLAUDE.md raiz lista
14/16 subagentes; anti-gatilho para skill inexistente `transferencia-saldo-codigo` em 2
SKILL.md; frontmatter de `orientador-loja.md` sem `consultando-venda-loja`.

## Decisoes registradas (Rafael, 2026-06-11)

1. **Arquitetura aprovada** condicionada a confirmacao de que e a melhor mesmo sem limite de
   abrangencia — confirmada: o alvo (papel por camada + trilhos + enforcement) e o que se
   desenharia do zero dado que os substratos sao impostos pelas ferramentas (Claude Code:
   SKILL.md/agents .md/CLAUDE.md/memoria filesystem; Agent SDK: Postgres/hook). Itens em que
   um greenfield divergiria (KG, modelo 2-andares de evidencias) estao atras de gates cuja
   adocao futura e ADITIVA, nao retrabalho.
2. **Cadencia do trilho memoria→reference: QUINZENAL** (checklist 30min, fila gerada por
   query); degradar para trimestral se 2 ciclos seguidos vierem vazios — decidir por uso.
3. **KG: replay-gate** (1 dia) antes de escolher higiene X3-lite vs flag-off. Excecao
   consciente a preferencia "flags ligadas": aqui o custo e de ESCRITA continua com retorno
   zero de leitura.
4. **Escopo: F0+F1 ≈ 1 mes; F2 explicitamente atras de gates.**

## Diagnostico em 5 fatos

1. **O conhecimento mora onde NASCE, nao onde e LIDO.** 4 motores de captura (pipeline
   pos-sessao web, memoria dev manual, `.remember/`, docs de sessao); 0 desaguam em
   `references/` — a unica camada lida por CC dev, agente web, Teams e subagentes (06 §B).
   Unico trilho formalizado: memoria→codigo (2 promocoes ate hoje).
2. **Drift = f(1/enforcement), nao de disciplina.** As unicas duplicacoes sem drift do sistema
   inteiro sao as 2 lintadas/autorizadas (qtd_saldo, critical_ids) + projecao ×3 de subagentes;
   todas as demais classes driftam em dias-semanas (06 §Q5). Mesmo conhecimento em 4-7 camadas;
   pior caso G021 em 33 arquivos.
3. **Memoria sem aposentadoria.** Fluxo observado: nasce memoria → codificado em
   skill/CLAUDE.md → memoria orfa permanece (06 §Q2). MEMORY.md dev estourado (>24,4KB,
   truncagem ativa); 33-39% das 167 memorias dev duplicam a camada estatica (02 §3).
4. **Memoria web: o gargalo e o read path e o feedback, nao a duplicacao.** Duplicacao
   verdadeira ~3-8% do corpus empresa ativo; KG write-only (custo por save, leitura 0);
   4 contadores sobrepostos com cold-move governado por sinal declarado "so dashboard";
   merge Sonnet destrutivo sem versionamento (07 §3, §6).
5. **Agent = particionamento de action-space + isolamento de contexto** (criterio real,
   comprovado pela historia: Solucao B, routing nominal, skills exclusivas), nao
   "orquestracao". Anti-gatilhos espelhados agent↔skill sao o custo de defender fronteira
   em 4-5 registros manuais sem verificador (06 §Q3).

## Arquitetura-alvo: papel canonico por camada

| Camada | MORA aqui | Escreve | Le | Promocao (sai para) | Expiracao |
|---|---|---|---|---|---|
| Codigo (guards) | Tudo deterministico (doutrina `app/odoo/estoque/CLAUDE.md` §8 generalizada) | dev | runtime de todas as superficies | — (destino final) | refactor |
| Skills | Procedimento DA operacao + gotchas DA operacao + few-shot; description = SO selecao (≤600c) | dev | principal + subagentes | dominio citado por 2+ skills → reference | versionamento |
| Agents | Disciplina de execucao + particao de action-space, ponteiro-first; ZERO dominio inline | dev | loader web + Task dev | dominio inline → reference/CLAUDE.md modulo | aposentar por medicao |
| References + CLAUDE.md | **Residencia permanente** do estavel nao-deterministico; unica camada lida por TODAS as superficies | dev (PAD-A) + PROMOCOES | todas as superficies | check binario → codigo | superseded_by/_deprecated |
| Memoria web | Episodico, perfil/preferencias, aprendizado AINDA-nao-estavel (incubadora) | save_memory + pipelines | hook de injecao | →codigo (existe) e →reference (NOVO, T1.4) | cold/GC + aposentadoria pos-promocao |
| Memoria dev | feedback_* do Rafael, handoffs VIVOS, gotchas ainda nao codificados | dev manual | boot CC dev | codificado → APOSENTAR na mesma sessao (regra nova) | aposentadoria obrigatoria |
| .remember/ | Episodico automatico dev | plugin | boot CC dev | Identity Candidates → trilho T1.4 | rollup proprio |

Fronteiras de INFRA dev↔web preservadas (corretas); o que muda: ambas ganham trilho de saida
para `references/`.

## Ontologia de captura T1-T6 (tabela de decisao, nao schema)

Usar na hora de capturar conhecimento ("que tipo e isto?") e no checklist da cadencia.
NAO e declaracao obrigatoria por entrada (disciplina sem lint drifta — fato 2).

| Tipo | Natureza | Substrato-dono |
|---|---|---|
| T1 fato declarativo sobre entidade | campos, IDs, mapeamentos | schemas JSON + reference dona |
| T2 invariante/gotcha operacional | "se X sem Y, quebra" | guard codigo > corpo de skill > GOTCHAS por dominio |
| T3 procedimento componivel | passos 1..n | SKILL.md body / how-to / runbook |
| T4 preferencia/correcao comportamental | "comigo, aja assim" | memoria (residencia natural: user_rules web; feedback_* dev) |
| T5 heuristica/armadilha empresarial | padrao observado em PROD | memoria web empresa = INCUBADORA com trilho de saida |
| T6 estado de trabalho efemero | handoff, pendencia | .remember/ + PAD-A `state` (incidente = tag em adr/state) |

## Metricas de sucesso (contrato hoje → alvo)

Declarar alvo ANTES de cada fase; medir depois. Valores "hoje" medidos no estudo.

| Metrica | Hoje (2026-06-11) | Alvo pos-F2 |
|---|---|---|
| MEMORY.md dev | 25,2KB, truncagem ativa | <22KB, zero truncagem |
| Violacoes regra 3 (dup com estatica) | ~55-65 de 167 (33-39%) | <10 |
| Duplicacao verdadeira corpus empresa web | ~3-8% | <2%; 0 colisoes de slug novas/mes |
| Merges nao-versionados no pipeline empresa | 100% dos merges | 0 |
| Budget descriptions por superficie (limite 8K confirmado I0.3) | principal ~9,2K (115%); gestor-estoque-odoo ~15-16K (~200%) — truncamento ATIVO em ambos | todas as superficies <8K com lint |
| Anti-gatilhos mortos / contagens divergentes | 1 skill inexistente + 3+ contagens | 0 (lint) |
| Conhecimento "INVIOLAVEL" so em memoria | ≥1 caso provado (diff_qtd) | 0 |
| KG no read path | 0 memorias em toda injecao | >0 com higiene OU escrita OFF (decisao T2.2) |
| Promocoes memoria→reference | 0 (trilho inexistente) | ≥2/mes nos 3 primeiros meses |
| Registros manuais por skill nova | ate 8 | ≤3 manuais + projecoes lintadas |

## ITEM 0 — Verificacoes antes de tudo (minutos)

> EXECUTADO 2026-06-11 (mesma sessao do plano). Resultados abaixo de cada item.

- [x] **I0.1** Flags efetivas em PROD — verificadas por COMPORTAMENTO no banco (get_service
  nao expoe env vars): KG **ATIVO** (1.764 entidades com last_seen_at em 7d; ultima relacao
  criada 2026-06-11 15:29Z); enriquecimento/merge **ATIVO em volume** (230 memorias empresa
  com updated_at > created_at+1h em 14d, contra apenas 59 versoes em 14d — o gap X5 de
  merges nao-versionados esta acontecendo AGORA em PROD, refortalece T0.1);
  directives intent-only deployado 2026-06-10 (PAD-CTX, nao re-verificado).
- [x] **I0.2** Invocacoes por subagente em PROD, 90d (`agent_invocation_metrics.agent_type`):
  gestor-estoque-odoo 37 · especialista-odoo 31 · gestor-recebimento 26 ·
  auditor-financeiro 7 · raio-x-pedido 4 · gestor-motos-assai 3 · analista-carteira 2 ·
  gestor-estoque-producao 2 · analista-performance-logistica 1 · gestor-carvia 1 ·
  auditor-sped-ecd 1. **ZERO invocacoes**: controlador-custo-frete, gestor-devolucoes,
  gestor-ssw, desenvolvedor-integracao-odoo (+ orientador-loja, que opera na superficie
  isolada do Agente Lojas). Caveat T2.1: a tabela registra a superficie WEB; uso via Task
  no CC dev nao aparece aqui — mover do loader web NAO remove disponibilidade no dev.
- [x] **I0.3** Budget REAL do listing: **8.000 chars CONFIRMADO** no binario bundled 2.1.170
  (`claude_agent_sdk/_bundled/claude`, o mesmo de PROD): constantes `V85=200000` (ctx) ×
  `ML7=4` (bytes/token) × `T85=0.01` (fraction default de `skillListingBudgetFraction`) =
  8.000; override por env `SLASH_COMMAND_TOOL_CHAR_BUDGET` existe (alavanca de emergencia;
  padrao do PAD-CTX permanece "caber no default, nao subir o teto"). O mapa 03 (16K) estava
  ERRADO. Consequencia: **truncamento ATIVO confirmado nas DUAS superficies** — principal
  ~9,2K/8K (115%) e gestor-estoque-odoo ~15-16K/8K (~200%, perde metade das clausulas das
  skills WRITE). Eleva a urgencia de T1.2; lint T1.1 calibra em 8K por superficie.

## FASE F0 — Dor ativa, so certeza (~1 semana)

Rollback por item; nada muda comportamento sem flag. Detalhar TDD na sessao de execucao.

- [ ] **T0.1 — X5: versionar + verificar o merge do pipeline empresa.**
  Sintoma: `_try_enrich_existing` (`app/agente/services/pattern_analyzer.py:1569-1669`) faz
  merge Sonnet destrutivo SEM `save_version` (0 ocorrencias no arquivo) e SEM verificacao
  TODOS_PRESERVADOS (existe so em `memory_consolidator.py:564-571`). Cura: chamar
  `save_version` antes do merge (padrao de `memory_mcp_tool.py:2074`) + portar a verificacao
  com retry do consolidator. Teste: pytest novo cobrindo merge com e sem perda de fatos.
  Rollback: e adicao de salvaguarda.
- [ ] **T0.2 — Lista fechada de consertos de drift (horas).** Todos re-verificados 2026-06-11:
  (a) `ROUTING_SKILLS.md:19` "54"→53 + secao Utilitarios com contagem divergente;
  (b) `tool_skill_mapper.py:109` remover `lendo-documentos`, avaliar adicionar `padronizando-docs`;
  (c) docstring L1 de `inventario_pipeline.py`;
  (d) CLAUDE.md raiz SUBAGENTES: incluir `auditor-sped-ecd` e `orientador-loja` (14→16);
  (e) anti-gatilho `transferencia-saldo-codigo` (inexistente) em
  `ajustando-quant-odoo/SKILL.md` e `transferindo-interno-odoo/SKILL.md` — remover ou marcar
  "(planejada)";
  (f) contagens do `especialista-odoo` "9 vs 8 vs 8" (mapa 04);
  (g) espelho CAMINHOS de `~/.claude/CLAUDE.md` sem a linha SPED (mapa 05);
  (h) frontmatter `orientador-loja.md` sem `consultando-venda-loja` — CONFIRMAR INTENCAO antes.
- [ ] **T0.3 — Triagem unica da memoria dev + regra de aposentadoria.**
  Backup `tar.gz` ANTES (diretorio fora de git). Aposentar ~55-65 memorias provadamente
  duplicadas/vencidas (clusters no mapa 02 §3: ~22 do cluster Odoo-estoque ja codificadas em
  `app/odoo/estoque/CLAUDE.md:131,144,161`; worker_render_filas verbatim em ~/.claude/CLAUDE.md;
  memorias-ponteiro para references existentes; ~25-30 estados vencidos). Conteudo exclusivo
  (genealogia, gaps) move para `ROADMAP_SKILLS.md`/adr antes de apagar. Corrigir staleness que
  induz erro: `memory/skill8_pipeline_completo_v17.md:15,38` cita `faturamento_pipeline.py`
  (renomeado). Adicionar ao guideline do MEMORY.md: *"memoria cujo conteudo foi codificado em
  skill/CLAUDE.md/reference DEVE ser aposentada na mesma sessao (ponteiro de 1 linha ou
  delecao)"*. Meta: MEMORY.md <22KB.
- [ ] **T0.4 — X1+X2: determinizar o path da memoria empresa (flag-gated).**
  (a) Fechar `dominio` em enum ~12 valores no prompt do extrator (`pattern_analyzer.py:962`)
  + validacao em `_build_knowledge_path` (`:1100-1141`) com fallback `geral`;
  (b) dedup de slug por embedding de TITULO (nao da descricao) contra slugs existentes do
  mesmo kind ANTES de criar path novo — match vira enriquecimento do slot existente (ja
  versionado por T0.1);
  (c) migracao UNICA dos namespaces legados fora do protocolo (`regras/` 20, `termos/` 7,
  `usuarios/` 6, `procedimentos/`, `pendencias/`, `pitfalls/`) para
  protocolos/armadilhas/heuristicas — dry-run + relatorio antes de aplicar.
  Path-alvo: `/memories/empresa/{kind-enum}/{dominio-enum}/{slug-dedupado}` — equivalente
  funcional da chave (kind, entidade, aspecto) para o sub-corpus operativo, mantendo
  UNIQUE(user_id, path), injecao, `list_memories` e a tela `/agente/memorias` intactos.
  Rollback: flag no pipeline; migracao reversivel via versions + relatorio.

## FASE F1 — Estancar a fonte do drift (2-3 semanas)

- [ ] **T1.1 — Lint de consistencia de roteamento (report-only → enforce).**
  Estender `prompt_size_audit.py --check-consistency`/`skills_listing_audit.py`:
  (a) toda skill citada em anti-gatilho de description, ROUTING_SKILLS.md, tool_skill_mapper
  e frontmatter de agents EXISTE em `.claude/skills/`;
  (b) contagens declaradas no ROUTING = contagem real;
  (c) **budget por subagente**: soma das descriptions das skills declaradas no frontmatter de
  cada `.claude/agents/*.md` ≤ limite confirmado no I0.3.
  Padrao de rollout: `ui_policy_lint` (report-only primeiro, enforce no pre-commit depois).
- [ ] **T1.2 — Solucao A nas descriptions (truncamento ATIVO nas 2 superficies — I0.3).**
  Descriptions ≤600c (1 frase proposito + gatilhos + 1 anti-gatilho critico); matriz
  USAR/NAO-USAR completa move para o CORPO da SKILL.md. Cobre as DUAS superficies acima do
  limite de 8K: o listing do PRINCIPAL (~9,2K, afeta todo turno do agente web) e as 10 de
  estoque dentro do `gestor-estoque-odoo` (~15-16K, perde anti-gatilhos das skills WRITE).
  Piloto: 2 skills com a suite pytest do dominio verde antes/depois; ordem das superficies
  a decidir na execucao; depois os 16 frontmatters >1024c. Alavanca de emergencia documentada
  (env `SLASH_COMMAND_TOOL_CHAR_BUDGET`) — usar SO se algo critico for perdido antes da
  Solucao A concluir.
- [ ] **T1.3 — Registro G0xx minimalista (resolver colisao de IDs).**
  Colisoes provadas: G002/G021 com significados diferentes em
  `docs/inventario-2026-05/02-gotchas/` vs dominio estoque; DOIS arquivos `G030-*.md` no mesmo
  diretorio. Cura: `app/odoo/estoque/CLAUDE.md` continua dono da serie G0xx (de facto);
  docs/inventario renomeia sua serie para prefixo proprio (ex.: `INV-xxx`); GOTCHAS.md ganha
  tabela-indice apontando donos; portar ao catalogo geral `odoo/GOTCHAS.md` os 2 gotchas
  gerais ausentes: G002 (stock.lot.name busca via `in`/`=like`) e G021 (lote exige
  company_id) — quem opera Odoo fora do estoque hoje nao os encontra.
- [ ] **T1.4 — Trilho memoria→reference + primeira leva (4 silos provados).**
  (a) Secao nova no PAD-CTX (§Memorias) simetrica a promocao→codigo: criterios (estavel,
  nao-deterministico, relevante a 2+ superficies), fluxo (fila → revisao → reference →
  aposentar origem com `is_cold` + `meta.promovida_para`);
  (b) fila de candidatas GERADA POR QUERY (2+ evidencias OU correction_count≥2, idade≥30d,
  sem promovida_para) exposta via `gerindo-agente`;
  (c) cadencia QUINZENAL 30min com checklist (decisao 2); degradar para trimestral se 2
  ciclos vazios;
  (d) PRIMEIRA LEVA (mesmo trabalho, ja aprovada): regra MIGRACAO `diff_qtd`
  (memoria `regra_direcao_migracao_diff_qtd` rotulada SOT/INVIOLAVEL) →
  `app/odoo/estoque/CLAUDE.md` + fluxos; 2 semanticas de "anexar" → `app/carvia/CLAUDE.md`;
  nuance "CD=34 financeiro NAO e company_id" → `odoo/IDS_FIXOS.md`; heuristica
  `duplicacao-de-pedido-atacadao-por-reinsercao` (web) → reference de negocio. Aposentar as
  memorias de origem no mesmo commit.
- [ ] **T1.5 — Guard "cannot marshal None" (o gotcha mais replicado: ~20 arquivos, 0 guard).**
  Wrapper unico no ponto de conexao XML-RPC Odoo (verificar arquivo exato na execucao —
  mapa 06 §E4 sugere `connection.py`) interpretando o Fault como sucesso-com-aviso conforme
  semantica ja documentada em `odoo/GOTCHAS.md`. Reduzir os ecos textuais a ponteiro de
  1 linha. E o piloto do modelo "constituicao generalizada" (T2 da ontologia).
- [ ] **T1.6 — Versionar o conteudo dev-only de `~/.claude/CLAUDE.md` (17,3KB fora de git).**
  Criar doc versionado no repo (zona PAD-A) com o conteudo critico (worker RQ, Caddy split,
  migrations, JSON sanitization...); `~/.claude/CLAUDE.md` vira ponteiro fino. Mata a CLASSE
  do drift do espelho, nao so a instancia (0,5 dia).

## FASE F2 — Decisoes por medida (condicionada a gates)

- [ ] **T2.1 — Agents: aposentadoria por medicao + filtro de superficie.**
  Gate: dados do I0.2 (JA COLETADOS — candidatos com 0 invocacoes web/90d:
  controlador-custo-frete, gestor-devolucoes, gestor-ssw, desenvolvedor-integracao-odoo;
  ponderar uso na superficie dev antes de decidir). Agents com ~0 invocacoes → mover para
  fora do loader (NAO deletar).
  Independente da medicao: frontmatter `surface: dev` + filtro de ~3 linhas em
  `app/agente/config/agent_loader.py` para `desenvolvedor-integracao-odoo` (dev-only de jure,
  carregado em PROD de facto — risco em si). `gestor-recebimento` MANTER (routing nominal
  comprovado). NAO converter roteadores finos (NAO-FAZER N4).
- [ ] **T2.2 — KG: replay-gate → higiene X3-lite OU flag-off (decisao 3).**
  Replay controlado de 1 dia reproduzindo `query_graph_memories`
  (`knowledge_graph_service.py:877-882`) com prompts reais para CONFIRMAR a causa do graph=0
  (hipotese: vocabularios disjuntos prompt-side canonico vs memory-side ruidoso).
  Se confirmada e a higiene couber em ≤1 semana (limpar 700 nomes `:E`/`:A`, rebaixar fallback
  `conceito`, ligar por entity_key): executar X3-lite e medir retorno no read path.
  SENAO: `MEMORY_KNOWLEDGE_GRAPH=false` preservando tabelas. So DEPOIS de read path saudavel
  reabrir a discussao "KG como identidade" (e o modelo 2-andares de evidencias — aditivo).
- [ ] **T2.3 — Consolidar os 4 contadores de feedback (com sombra).**
  `helpful/harmful` (outcome real) vira sinal canonico com PERIODO DE SOMBRA: cold-move
  continua no `effective_count` ate `helpful+harmful` atingir volume minimo (gatilho objetivo
  a definir na execucao); registrar a divergencia entre sinais durante a sombra. Corrige
  cold-move governado por sinal declarado "so dashboard" (`models.py:592`).

## Lista NAO-FAZER (governanca permanente)

Anexo permanente do desenho-alvo (anti-overengineering). Revisitar item so com gate atingido.

- **N1** Re-arquitetura KG-identidade — duplicacao ~3-8% e T0.4 ataca por caminho de horas.
- **N2** Store unico dev+web — fronteira de infra correta; silo e de CONTEUDO (T1.4 resolve).
- **N3** Router central/classifier de intencao — sem telemetria de mis-routing que dimensione.
- **N4** Converter roteadores finos em skills agora — quebraria routing nominal; medir antes (I0.2).
- **N5** Re-taxonomia/renomeacao geral de skills — rename de 1 arquivo gerou 25+ citacoes stale.
- **N6** Retrofit L0-L4 forcado em todos os dominios — adotar so em dominio novo/reaberto.
- **N7** Tipo PAD-A "incidente" com pipeline proprio — tag em adr/state resolve; upgrade so se >10 incidentes ativos simultaneos.
- **N8** TTL/decay automatico na memoria dev — triagem unica + regra de aposentadoria + cadencia bastam.
- **N9** Sandbox tecnico por agent — protecao real ja esta nas skills WRITE (dry-run/--confirmar).
- **N10** Evals LLM para routing — vetado por custo (Rafael); cobertura = pytest deterministico.

## Riscos

1. Triagem T0.3 apagar conteudo exclusivo → mitigado: backup tar + mover genealogia/gaps antes.
2. Dedup de slug (T0.4b) fundir vizinhos legitimos → mitigado: match vira ENRIQUECIMENTO
   versionado (T0.1), nunca overwrite; threshold conservador; fila de revisao na tela existente.
3. Lint T1.1 com falso-positivo travando commit → mitigado: report-only primeiro.
4. Cadencia quinzenal nao acontecer → mitigado: fila gerada por query (humano so julga);
   degradacao para trimestral e decisao prevista, nao falha.
5. Budget real (I0.3) divergir das metas → metas de T1.2/T1.1 recalibram ANTES de executar.
6. Plano de cauda longa com 1 dev → F2 inteira atras de gates; F0+F1 fecham valor sozinhas.

## Rastreamento

> Atualizar a cada sessao de execucao (data + o que fechou + evidencia).

- 2026-06-11 — Plano criado e aprovado em conversa (4 decisoes registradas).
- 2026-06-11 — **ITEM 0 EXECUTADO** (read-only): budget 8K confirmado no binario 2.1.170
  (truncamento ATIVO no principal 115% e no gestor-estoque-odoo ~200% — urgencia de T1.2);
  invocacoes/90d coletadas (4 agents com zero na superficie web); flags KG+enrichment ativas
  por comportamento (230 enriquecidas vs 59 versoes em 14d = X5 sangrando agora).
  Modo de execucao decidido: N sessoes (1 por fase), subagent-driven nas tasks mecanicas/TDD,
  inline nas de julgamento (T0.3, gates, decisoes). Proximo: F0 (T0.1 → T0.4) em sessao nova.

## Fontes

- FONTE: estudo macro-arquitetural 2026-06-11 — `relatorios/arquitetura_x_2026-06-11/`
  (01-05 mapas por camada, 06 cross-layer, 07 avaliacao adversarial KG, 08-* propostas
  episteme/refinaria/x-enxuto, 09-* juizes escalabilidade/risco-retorno). Diretorio
  nao-versionado (gitignore `relatorios/`).
- FONTE: conversa motivadora — `app/agente/conversa.md` (nao-versionada; raiz do repo principal).
- FONTE: padroes que este plano generaliza — `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md`
  (PAD-CTX: dono + redundancia autorizada + lint; promocao memoria→codigo),
  `.claude/references/ARQUITETURA_DE_ARTEFATOS.md` (PAD-A), `app/odoo/estoque/CLAUDE.md`
  (constituicao: gotcha = invariante codificado), `.claude/references/MEMORY_PROTOCOL.md`.
- FONTE: verificacoes diretas 2026-06-11 listadas em "Origem e evidencia".

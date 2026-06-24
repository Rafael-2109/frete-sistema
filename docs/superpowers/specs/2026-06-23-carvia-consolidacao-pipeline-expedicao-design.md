<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-23
-->
# Spec — Consolidação do pipeline de expedição CarVia/Nacom (reconciliador central + fonte canônica)

> **Papel:** especificação de design (diagnóstico + arquitetura-alvo + plano faseado) para eliminar a inconsistência recorrente dos fatos derivados do Embarque CarVia (`local_cd`, totais/valor, frete, vínculo NF↔Embarque). **Abra quando:** for revisar (4-mãos) ou implementar a refatoração de consistência CarVia/Embarque. **Status:** IMPLEMENTADO (2026-06-23) no branch `feat/carvia-consolidacao-pipeline` (worktree `frete_sistema_carvia`, SEM push — aguarda revisão + deploy). Commits F0→F5+docs: `00cb3ba84`, `b07d4688b`, `29d217a1e`, `8f6a9bbe7`, `70175c0dc`, `bf76f4099`, `93ab55512`. **Desvio da spec:** F6 (remover skip do `sync_totais`) NÃO foi feito — verificou-se que o skip é correto (o recompute do header já inclui CarVia; removê-lo zeraria valores); em vez disso o skip foi blindado com comentário. CHECK constraint do F5 descartado (inócuo: VM/TM ambos válidos); a tranca é factory + guard test.

## Indice

- [Contexto](#contexto)
- [Os 4 sintomas relatados](#os-4-sintomas-relatados)
- [Diagnóstico estrutural: 1 doença, não 4 bugs](#diagnóstico-estrutural-1-doença-não-4-bugs)
- [Achados verificados no código](#achados-verificados-no-código)
- [Antipadrões recorrentes (assinatura do Frankenstein)](#antipadrões-recorrentes-assinatura-do-frankenstein)
- [Mapa de consistência](#mapa-de-consistência)
- [Requisitos da solução (critério de aceite)](#requisitos-da-solução-critério-de-aceite)
- [As 3 arquiteturas avaliadas](#as-3-arquiteturas-avaliadas)
- [Recomendação: híbrido P1 → P2](#recomendação-híbrido-p1--p2)
- [Arquitetura-alvo](#arquitetura-alvo)
- [Centralização por fato](#centralização-por-fato)
- [Tratamento do fork Nacom vs CarVia](#tratamento-do-fork-nacom-vs-carvia)
- [Plano faseado](#plano-faseado)
- [Invariantes impostas](#invariantes-impostas)
- [Riscos residuais](#riscos-residuais)
- [Fora de escopo (YAGNI)](#fora-de-escopo-yagni)
- [Decisões em aberto para a revisão](#decisões-em-aberto-para-a-revisão)
- [Documentação a atualizar no fechamento](#documentação-a-atualizar-no-fechamento)
- [Fontes e arquivos-chave](#fontes-e-arquivos-chave)

## Contexto

Origem: com os pedidos CarVia e a ampliação para 2 CDs (Victorio Marchezine / Tenente Marques), surgiram inconsistências recorrentes nos gatilhos que atualizam fatos do sistema. A sensação relatada pelo usuário é a de um "Frankenstein" impossível de conciliar — cada bug foi corrigido com um point-fix em 1-2 pontos, mas a correção apenas adicionou o gatilho numa porta a mais, sem fechar a vulnerabilidade. O usuário também aponta que o sistema "trabalha de um jeito X para a Nacom e Y para a CarVia", quando na verdade é a **mesma operação** com **2 diferenças reais**: (a) CarVia **não lança no Odoo**; (b) CarVia **cobra pelo frete** (receita), enquanto a Nacom **absorve o custo** (mercadoria própria).

Esta spec é o resultado de uma investigação paralela do código real (não dos docs, que driftam para trás), validada linha a linha. O objetivo é **garantir consistência, wiring e clareza** — com autorização explícita para mudanças grandes, mas **sem over-engineering** e sem tocar no que funciona no Nacom.

## Os 4 sintomas relatados

1. Pedido CarVia com CD **TM**, ao gerar embarque gravava **VM**.
2. **Valor da CarVia** no Embarque ficava **stale** mesmo após adição de novos pedidos CarVia.
3. **Frete CarVia** de apenas **alguns** pedidos não sendo gerado.
4. **Badge "Embarque"** aparecendo em apenas alguns casos na tela de NFs CarVia.

Todos foram corrigidos por point-fixes recentes; a recorrência é o problema a resolver.

## Diagnóstico estrutural: 1 doença, não 4 bugs

> **CarVia reutilizou as 4 entidades físicas do Nacom (`EmbarqueItem`, `Embarque`, `ControlePortaria`, `EntregaMonitorada`) sem herdar o mecanismo que as mantém consistentes no Nacom: a entidade-raiz `Separacao` e seus event listeners SQLAlchemy.**

No Nacom, quando peso/valor/pallet mudam, o listener `recalcular_totais_embarque` (`app/separacao/models.py:343`, `after_update`/`after_delete`) reescreve os totais **automaticamente**. Mas **CarVia não tem linha `Separacao`** — vive só como `EmbarqueItem` com lote `CARVIA-*`. Logo toda derivação que no Nacom é automática-on-change virou, em CarVia, um **contrato informal**: "lembre-se de chamar o helper X em cada porta nova". Cada porta nova esquece um helper → bug → point-fix + backfill → recorrência.

**O defeito de fundo é a AUSÊNCIA DE UM RECONCILIADOR ÚNICO acionado por mudança de estado do `EmbarqueItem` CarVia.** As 2 diferenças de negócio reais (não-Odoo, frete=receita) justificam pipelines de **dados** diferentes; **não** justificam 6+ call-sites desacoplados para disparar o mesmo fato derivado. Esse é o **fork acidental** que causa a recorrência.

**Prova de recorrência sistemática (não azar):** 5 backfills em ~5 dias (18→23/06):

| Data | Backfill | Volume |
|------|----------|--------|
| 2026-06-18 | `local_cd` embarque+entrega | 34 + 15 |
| 2026-06-22 | `carvia_frete.operacao_id` | 110/114 fretes |
| 2026-06-23 | `volumes` (qtd motos) | 146 itens com 0 |
| 2026-06-23 | `peso_cubado` dos fretes | 71 fretes |
| 2026-05-05 | `valor_cotado` | 19/21 |

## Achados verificados no código

Todas as âncoras abaixo foram lidas no código real (não nos docs):

| Alegação | Verificado em | Veredito |
|---|---|---|
| Skip CarVia no sync de totais | `app/embarques/services/sync_totais_service.py:148-156` (`if lote.startswith('CARVIA-') or item.carvia_cotacao_id: return {...'fonte':'CarVia (skip)'}`) | **CONFIRMADO** |
| `receita_carvia()` computed-on-read, lazy import, separado de `valor_total` | `app/embarques/models.py:148-169` (lazy import `viabilidade_service`) | **CONFIRMADO** |
| Listener Nacom só dispara por `Separacao` | `app/separacao/models.py:343-413` (`after_update`/`after_delete`; busca `EmbarqueItem` por `separacao_lote_id`) | **CONFIRMADO** — nunca casa item CARVIA- (não há Separacao) |
| 8 construtores `EmbarqueItem(` em cotacao sem `local_cd=` | `app/cotacao/routes.py:1754,1850,1896,2257,2333,2375,4123,4200` — `grep local_cd` retorna **VAZIO** | **CONFIRMADO** (3 são CarVia: 1754/2257/4123) |
| Herança correta de local_cd já existe (padrão a generalizar) | `app/carvia/services/documentos/embarque_carvia_service.py:283` | **CONFIRMADO** |
| `_recalcular_totais` NÃO toca pallet e soma TODOS os itens ativos | `embarque_carvia_service.py:911-933` | **CONFIRMADO** |
| 5 early-returns mudos em `_processar` | `carvia_frete_service.py:51-77` (InFailedSqlTransaction→[]), `:98-100` (sem transportadora), `:108-115` (gate 2-CD), `:127` (sem item elegível), + frete-existente | **CONFIRMADO** — todos `logger.info/warning` + `return []` |
| `cancelar_fretes_orfaos_embarque` é state-driven (espelho do "regenerar" que falta) | `embarque_carvia_service.py:2108` | **CONFIRMADO** |
| Readers de vínculo NF fazem UNION de 2 vias replicado; `detalhe_nf` diverge | `nf_routes.py:25-55`, `:127-159`, detalhe usa só 1 via | **CONFIRMADO** |

### Achado próprio — o furo do safety-net `propagar_local_cd_carvia`

`app/utils/propagacao_local_cd.py:37-46` filtra o `EmbarqueItem` por `nota_fiscal == numero_nf` **e** `local_cd.isnot(None)`. Consequência:

- Um item **provisório** (`CARVIA-PED-*`) criado **antes** de a NF chegar **nunca casa** (filtro por `nota_fiscal`) → carrega o **default VM** até a NF ser anexada. Esse é exatamente o 3º vetor (COL-004).
- (Nuance corretiva: como a coluna `embarque_itens.local_cd` é `NOT NULL default VM`, o filtro `isnot(None)` quase não morde — o furo **real e load-bearing** é o match por NF.)

**Implicação para a arquitetura:** qualquer solução que dependa só de propagação pós-evento **herda esse furo**. O fix de **herança-na-criação** (passar `local_cd` ao instanciar o `EmbarqueItem` CarVia em `cotacao/routes.py`) **não é opcional** — é o único que fecha a janela na origem, porque o item nasce correto independentemente de a NF já estar anexada.

## Antipadrões recorrentes (assinatura do Frankenstein)

| Antipadrão | Descrição | Evidência |
|---|---|---|
| **Chokepoint só no comentário** | "ponto único" é convenção; nada técnico impede furar | `coleta_service.py:130` diz "ÚNICO ponto"; 3 criadores em `cotacao/routes.py` furam |
| **Default silencioso mascara input ausente** | criar `EmbarqueItem` sem `local_cd` grava VM sem erro | `embarques/models.py` default VM; `cotacao/routes.py` 1754/2257/4123 |
| **Mesmo fato em 2 fontes c/ semânticas tratadas como iguais** | custo (`valor_total`) vs receita (`receita_carvia`); vínculo via EI vs via Frete | `models.py:148-169`; `nf_routes.py` UNION vs `detalhe_nf` só-Frete |
| **Derivação por evento sem reconciliação por estado** | nenhum evento isolado captura todos os casos; cada caso novo = hook novo | frete 4 hooks + 5 early-returns; `_recalcular_totais` em 4 pontos |
| **Falha silenciosa sem feedback** | early-return loga INFO/warning e retorna `[]`; operador não sabe | `carvia_frete_service.py:57-83` |
| **Point-fix + backfill como ciclo de manutenção** | corrige a porta esquecida sem remover a vulnerabilidade | 5 backfills em 5 dias |
| **Reuso de entidade física sem reusar seu mecanismo de consistência** | *(meta-antipadrão)* CarVia reusa `EmbarqueItem` mas não `Separacao`+listeners | `separacao/models.py:343`; `sync_totais_service.py:148` |

## Mapa de consistência

| Fato derivado | Writers | Cópias/Fontes | Chokepoint segura? | Nacom (automático) | CarVia (manual) | Vetor de recorrência |
|---|---|---|---|---|---|---|
| **local_cd** (CD VM/TM) | 8 (3 criadores não setam) | 7+ tabelas | NÃO (casa por NF; provisório sem NF) | herda de `Separacao.local_cd` | `propagar_local_cd_carvia` em ~4 gatilhos | novo criador de EmbarqueItem sem `local_cd=` |
| **valor/peso/pallet total** | 4 mecanismos | `valor_total` + `receita_carvia` + mapa | NÃO (sync PULA CarVia, `:148`) | listener `recalcular_totais` | `_recalcular_totais` em 4 call-sites (sem pallet) | rota nova muta itens sem chamar recalc |
| **CarviaFrete** (geração) | 4 portas | `carvia_fretes` (operacao_id NULL) | PARCIAL (1 criador, 5 early-returns mudos) | `processar_lancamento_automatico_fretes` | `_processar` via 4 hooks | sequência fora do caminho feliz |
| **Vínculo NF↔Embarque** | 2 materializações | `nota_fiscal` + `numeros_nfs` CSV (sem FK) | NÃO (cada via é cega à outra) | `Pedido.nf`→EmbarqueItem (1 query) | UNION 2 vias replicado por reader | nova tela sem UNION |
| **Status pedido CarVia** | 1 (portaria) | `CarviaPedido.status` | NÃO (sem máquina de estados) | 4 listeners `before_insert/update` | `_marcar_pedidos_embarcado` manual | transição intermediária sem derivador |
| **volumes/peso_cubado** | 5+ criadores | `EmbarqueItem.volumes`, `CarviaFrete.peso_total` | NÃO (fonte por call-site até fix) | n/a (volume físico) | `qtd_motos_carvia` canônico (pós-fix) | novo call-site grava 0/None |

## Requisitos da solução (critério de aceite)

| ID | Requisito | Critério |
|----|-----------|----------|
| **R1** | Reconciliador único acionado por estado | UM ponto recomputa TODOS os fatos derivados de forma idempotente; nova porta chama 1 função, não N |
| **R2** | Herança de `local_cd` na CRIAÇÃO do EmbarqueItem CarVia | Os 3 criadores em `cotacao/routes.py` passam `local_cd=(cotacao.local_cd or DEFAULT)`; reconciliação vira safety-net |
| **R3** | Cobertura de TODAS as portas de frete | Todas as portas passam por orquestrador comum + função de regeneração de fretes faltantes (espelho de `cancelar_fretes_orfaos`) |
| **R4** | Vínculo NF↔Embarque com fonte única de leitura | Helper único `resolve_embarque_por_nf_ids()` usado por TODOS os readers; zero UNION replicado |
| **R5** | Falha de derivação VISÍVEL | early-returns/skips emitem sinal observável (flash/registro), não só log INFO |
| **R6** | Default de coluna não mascara ausência de input p/ CarVia | constraint/validação/CI-guard detecta EmbarqueItem CARVIA- criado sem `local_cd` explícito |
| **R7** | Semânticas distintas não confundidas | custo (`valor_total`) e receita (`receita_carvia`) ficam nomeados e separados |
| **R8** | NÃO tocar o que funciona no Nacom | preserva o listener `Separacao` e as 2 diferenças de negócio; unifica só o fork ACIDENTAL |
| **R9** | Eliminar o ciclo point-fix+backfill | porta nova herda os hooks; risco vira gate de review, não bug silencioso |

## As 3 arquiteturas avaliadas

Três lentes independentes foram projetadas e julgadas (consistência / manutenibilidade / risco de migração / esforço-ROI / anti-over-engineering):

- **P1 — EmbarqueReconciler (recompute-on-change).** Um único `EmbarqueReconciler.reconcile(embarque_id)` que delega aos reconciliadores **já existentes** numa ordem única. Não cria schema, não cria tabela. **Melhor caminho de entrada** (ROI imediato, risco quase-zero). Fraqueza: é orquestrador-chamado-pela-porta, não trigger — reduz drasticamente o "esqueci de chamar" mas não o elimina (R6/R9 ficam como teste/gate).
- **P2 — Fonte canônica + invariante no DB.** Para cada fato, eleger UMA fonte e fazer o resto derivar; onde a cópia é inevitável, impor `CHECK`/factory único/CI-guard. **Melhor lente estrutural** — torna "esquecer o campo" um erro **alto**, fechando o ciclo point-fix (R9). Riscos: `CHECK` com `VALIDATE` exige backfill 100%; remover o skip muda totais visíveis na tela.
- **P3 — Pipeline unificado + Policy/Strategy por tipo de carga.** Discriminador `tipo_carga_origem` (coluna nova) + `ExpedicaoPolicy` (NACOM/CARVIA/ASSAI). **Tese diagnóstica mais correta**, mas **execução mais arriscada**: exige coluna nova + backfill **e** converter o listener `Separacao` do Nacom (mexe no coração estável). A abstração Policy/Strategy para 2 diferenças hardcoded é a tentação de "framework" que o usuário pediu para evitar.

### Pontuação (1-5; risco/esforço: menor é melhor)

| Critério | P1 | P2 | P3 |
|---|---|---|---|
| Consistência (mata recorrência?) | 4 | **5** | 4 |
| Manutenibilidade | 4 | 4 | 3 |
| Risco de migração (prod 2-CD) | **5** | 3 | 2 |
| Esforço/ROI | **5** | 4 | 2 |
| Anti over-engineering | **5** | 4 | 2 |

## Recomendação: híbrido P1 → P2

A síntese **não é escolher uma** — é **sequenciar**:

- **P1 primeiro** (dispatch): ROI imediato, risco quase-zero, reusa 100% dos helpers.
- **P2 depois** (fonte canônica + invariante no DB): fecha a recorrência **na origem**.
- **P3 descartado por ora**: retém-se **apenas** o discriminador `tipo_carga_origem` como **hardening opcional** pós-estabilização. A conversão do listener Nacom e a Policy/Strategy são risco em R8 sem ganho sobre o híbrido.

> **Princípio condutor:** primeiro um ponto-único de **dispatch** (P1) que estanca a sangria com risco baixo; depois, por fato e da origem para o DB, tornar a cópia divergente **impossível de nascer** (P2). O fork **justificado** (Nacom listener-driven via Separacao; CarVia=receita, não-Odoo) fica **intocado** — só o fork **acidental** (dispatch desacoplado) é unificado.

## Arquitetura-alvo

1. **`EmbarqueReconciler.reconcile(embarque_id, *, gatilhos)`** — `app/embarques/services/embarque_reconciler.py` (novo). Pipeline ordenado idempotente, **sem commit próprio** (caller commita; `commit=True` só standalone), que delega aos helpers existentes na ordem: `local_cd → totais → entregas → frete`. **Frete é o último passo** (por causa do rollback `InFailedSqlTransaction` em `carvia_frete_service.py:51`). Roteia itens por prefixo (`CARVIA-`/`ASSAI-`/Nacom). Retorna `RelatorioReconciliacao` (o que mudou, o que não pôde ser gerado e por quê) para feedback (R5). É a ÚNICA porta que rotas mutantes chamam.
2. **`criar_embarque_item_carvia(...)`** — `embarque_carvia_service.py` (novo factory). Único lugar autorizado a instanciar `EmbarqueItem` lote CARVIA-. Generaliza a herança da linha 283 (`local_cd`, `volumes` via `qtd_motos_carvia`, `peso_cubado` via `MotoRecognitionService`). Fecha a janela **na origem**.
3. **`resolve_embarque_por_nf_ids(nf_ids)`** — `app/utils/` (novo, R1-safe). Único helper do UNION das 2 vias (EI por `nota_fiscal` + `CarviaOperacaoNf→CarviaFrete→Embarque`, com a regra "EI cancelado = saiu"). Todos os readers consomem. **Sem tabela canônica nova** (tabela nova = mais um writer a sincronizar).
4. **`regenerar_fretes_faltantes_carvia(embarque_id)`** — `carvia_frete_service.py` (novo). Espelho do já-existente `cancelar_fretes_orfaos_embarque` (`:2108`). State-driven, idempotente.
5. **`CHECK` constraint + CI grep-guard** — só na fase final, como tranca: item CARVIA- com NF preenchida só aceita `local_cd IN (VM,TM)`; build falha se `EmbarqueItem` CARVIA- for instanciado fora do factory.
6. **`tipo_carga_origem`** — NÃO adotado agora; hardening opcional pós-estabilização.

### O que NÃO muda (anti over-engineering)

- NÃO cria `Separacao` para CarVia (seria o big-bang oposto).
- NÃO toca o listener `recalcular_totais_embarque`/`atualizar_status_automatico` de `Separacao` (fork justificado).
- NÃO unifica `carvia_frete_service` com o frete Nacom/Odoo (R1 CarVia: módulo isolado).
- NÃO funde `valor_total` (custo) com `receita_carvia` (receita).
- NÃO cria tabela canônica de vínculo NF↔Embarque (só helper de leitura).
- NÃO adiciona listener SQLAlchemy em `EmbarqueItem` (orquestrador chamado pela porta, não trigger automático — evolução P2 futura se o "esqueci" reincidir).
- NÃO mexe no gate 2-CD (`cds_pendentes_de_saida`) nem no carimbo por-CD da portaria.
- NÃO entra no status de `CarviaPedido` (não causou backfill).

## Centralização por fato

| Fato | Hoje (verificado) | Alvo híbrido | Fase que fecha |
|---|---|---|---|
| **local_cd** | 8 writers; 3 criadores cotacao sem `local_cd`; safety-net com furo do match por NF | Herança na criação (factory) + reconcile como safety-net | **F2 (origem) + F5 (CHECK)** |
| **valor/peso totais** | 4 mecanismos; sync PULA CarVia; `_recalcular_totais` já soma ambos sem pallet | 1 passo no reconciler; skip vira delegação | **F1 + F6** |
| **receita_carvia** | computed-on-read, semântica RECEITA ≠ valor_total CUSTO | **Mantido computed e nomeado** (não fundir) | preservado (R7) |
| **frete CarVia** | 4 portas; 5 early-returns mudos | `lancar_frete_carvia` + `regenerar` no reconcile; early-returns retornam motivo | **F3 + F4** |
| **vínculo NF↔Embarque** | UNION replicado; `detalhe_nf` diverge | helper único `resolve_embarque_por_nf_ids` | **F0** |
| **pallet** | `_recalcular_totais` não toca (by design) | mantido | preservado |
| **status CarviaPedido** | 1 ponto manual (portaria) | **fora de escopo** | adiar (não dourar) |

## Tratamento do fork Nacom vs CarVia

As 2 diferenças reais viram **branches explícitos e nomeados** no passo de frete do reconciler — **sem** Policy/Strategy:

- **Odoo**: itens Nacom → `processar_lancamento_automatico_fretes` (lança Odoo); itens CarVia → `lancar_frete_carvia` (não toca Odoo). A ausência de Odoo no CarVia deixa de ser implícita-espalhada e vira 1 branch.
- **Receita vs Custo**: `valor_total` (custo da mercadoria; Nacom absorve; vale p/ ambos) e `receita_carvia()` (receita cobrada; só CarVia; computed-on-read) permanecem **2 fatos nomeados**. O reconciler só garante que ambos refletem os **mesmos itens** — não os funde (R7, R8).
- **Listener `Separacao`**: INTOCADO. O passo de totais do reconciler **só re-soma `EmbarqueItem` já materializados** no header — não recalcula item Nacom a partir de `Separacao` (evita dupla-escrita em embarque misto).

## Plano faseado

> Sistema em PRODUÇÃO (2 CDs ativos). Zero big-bang. Cada fase deployável, testável e reversível isoladamente.

| Fase | O quê | Bug que resolve | Esforço | Risco | Reversível |
|---|---|---|---|---|---|
| **0** | `resolve_embarque_por_nf_ids` em `app/utils/`; apontar `nf_routes.py:25-55`, `:127-159` e `detalhe_nf`. Read-only, sem migration | **Badge cego / detalhe_nf diverge** | P | **Mínimo** | Sim |
| **1** | Criar `embarque_reconciler.py` delegando aos helpers existentes. **Não wired.** Testes de idempotência (2x==1x) + embarque MISTO | base p/ tudo | M | **Zero** (não em prod) | Sim |
| **2** | 3 criadores CarVia `cotacao/routes.py:1754/2257/4123` passam `local_cd=(cotacao.local_cd or LOCAL_CD_DEFAULT)` | **local_cd VM-errado na ORIGEM** (vetor #1) | P | Baixo | Sim |
| **3** | Rewire 1 porta/vez para `reconcile()`, da menos crítica à mais (coleta → expandir_provisorio → save embarque → **portaria por último**). Canary por porta + `regenerar_fretes_faltantes_carvia` | **Frete não-gerado** | M | Médio | Por porta |
| **4** | Early-returns de `_processar` retornam motivo estruturado; reconciler propaga → flash. Classificar ESPERADO (gate 2-CD) vs PROBLEMA | **Falha silenciosa** (R5) | P | Baixo | Sim |
| **5** | `criar_embarque_item_carvia()` factory; migrar 8 call-sites (1 ramo/vez); `CHECK` NOT VALID → auditar prod → VALIDATE; CI grep-guard | **Trancar** ciclo point-fix (R6/R9) | M | Médio | NOT VALID sim; VALIDATE não |
| **6** | Substituir o skip `sync_totais_service.py:148-156` por delegação ao reconciler (gatilhos={TOTAIS} no GET) | **Totais stale** | P | Médio | Sim |

**Mapa fase→bug:** Badge cego→F0; local_cd→F2(origem)+F5(tranca); frete não-gerado→F3+F4; totais stale→F6; ciclo point-fix→F5.

**Ganho imediato sem risco:** Fases **0, 1, 2** podem ir já — F0 corrige o badge na hora, F1 não toca prod, F2 fecha o vetor #1 na origem.

## Invariantes impostas

- **I1 (teste):** `reconcile(embarque_id)` 2x consecutivas == 1x — `tests/embarques/test_reconciler_idempotente.py` compara snapshot de embarque+itens+fretes.
- **I2 (teste/CI-guard):** nenhum `EmbarqueItem` CARVIA- criado sem `local_cd` explícito — falha alto, não mascarado pelo default VM.
- **I3 (teste):** todo embarque com `data_embarque` + item CarVia c/ NF + sem CDs pendentes tem `CarviaFrete` OU motivo registrado — sem frete silenciosamente ausente.
- **I4 (estrutural):** UM único helper `resolve_embarque_por_nf_ids`; grep garante zero UNION replicado fora dele.
- **I5 (contrato de código):** toda porta que muta itens de embarque chama `reconcile()` — sem call-site chamando `propagar_local_cd_carvia`/`_recalcular_totais`/`lancar_frete_carvia` direto fora do reconciler.
- **I6 (teste):** `valor_total` (custo) e `receita_carvia` (receita) refletem o MESMO conjunto de itens ativos após reconcile.
- **I7 (DB, F5):** `CHECK` rejeita item CARVIA- com NF preenchida e `local_cd NOT IN (VM,TM)` — divergência de CD vira erro de INSERT/UPDATE.

## Riscos residuais

1. **Embarque MISTO (Nacom+CarVia):** `_recalcular_totais` (`:911`) já soma TODOS os itens e sobrescreve o header — coexiste com o listener `Separacao`. **Mitigação obrigatória:** o passo de totais do reconciler só re-soma `EmbarqueItem` já materializados (não recalcula item Nacom a partir de `Separacao`); **teste de embarque misto na F1**.
2. **Reentrância/atomicidade no save:** `reconcile()` dentro de rota que já commita 1x não pode commitar no meio (`commit=False` em pipeline). Auditar rollback interno de `lancar_frete_carvia` (`:51`) antes de F3.
3. **`CHECK` VALIDATE (F5) falha com 1 item histórico violando:** NOT VALID primeiro → auditar prod via Render MCP (`query_render_postgres`) → VALIDATE.
4. **Custo do GET:** `reconcile` no GET de `visualizar_embarque` (que commita) pode aumentar latência. Mitigação: gatilhos={TOTAIS} no GET; frete/regeneração só em rotas mutantes.
5. **Furo do safety-net persiste se F2 não for feito:** `propagar_local_cd_carvia` não alcança item sem NF (verificado `:37-46`). A herança-na-criação (F2/F5) é a única que fecha a janela.
6. **Status CarviaPedido fora de escopo:** `_marcar_pedidos_embarcado` continua manual. Se transições provisório→real divergirem, vira fase 7 — adicioná-la agora seria dourar.
7. **3º CD futuro:** `CHECK local_cd IN (VM,TM)` exige migration se surgir 3º CD (aceitável).

## Fora de escopo (YAGNI)

- Criar `Separacao` para CarVia.
- Unificar os modelos de dados Nacom/CarVia (CarviaOperacao/Subcontrato/Frete vs Frete Nacom).
- Policy/Strategy framework + coluna `tipo_carga_origem` (retido só como hardening opcional).
- Tabela canônica `carvia_nf_embarque_vinculo`.
- Transformar `valor_total` em computed (performance: ~50 readers do Embarque).
- Reconciliar status de `CarviaPedido`.
- Unificar pallet teórico/físico.

## Decisões em aberto para a revisão

1. **Escopo do primeiro lote:** começar por F0-F2 (ROI imediato) e parar para nova revisão antes de F3 (rewire de portas)? Ou autorizar até F4 de uma vez?
2. **F5 — `CHECK` constraint vs só CI-guard:** o `CHECK` no DB é a tranca mais forte (R6), mas exige `VALIDATE` em prod. Aceitável agora ou adiar a tranca-DB e ficar só com factory+CI-guard inicialmente?
3. **Feedback de falha (R5):** flash ao operador na hora vs registro auditável consultável depois — qual canal preferido para "frete não gerado por motivo X"?
4. **`tipo_carga_origem`:** descartar de vez ou manter como item de roadmap pós-estabilização?

## Documentação a atualizar no fechamento

- `app/carvia/CLAUDE.md` — R1/R23: "ponto único" deixa de ser comentário informal e passa a ser o reconciler; registrar que toda porta nova chama `reconcile()`.
- `app/embarques/CLAUDE.md` — R2: documentar o `EmbarqueReconciler` e a delegação do `sync_totais`.
- `.claude/references/modelos/CD_EXPEDICAO_LOCAL_CD.md` — atualizar "Fonte e propagação" (herança-na-criação como mecanismo primário; reconcile como safety-net).
- `app/separacao/CLAUDE.md` — nota de que o listener Nacom permanece, mas o reconciler é a autoridade do lado CarVia.
- Plano de implementação correspondente em `docs/superpowers/plans/` quando autorizado.

## Fontes e arquivos-chave

- `app/embarques/services/embarque_reconciler.py` (a criar)
- `app/embarques/services/sync_totais_service.py:148-156` (skip CarVia)
- `app/cotacao/routes.py:1754/2257/4123` (criadores sem `local_cd`)
- `app/carvia/services/documentos/embarque_carvia_service.py:283` (herança correta), `:911` (`_recalcular_totais`), `:2108` (`cancelar_fretes_orfaos`)
- `app/carvia/services/documentos/carvia_frete_service.py:36-128` (`lancar_frete_carvia` + early-returns)
- `app/utils/propagacao_local_cd.py:37-46` (furo do safety-net)
- `app/carvia/routes/nf_routes.py:25-55/127-159` (UNION replicado)
- `app/separacao/models.py:343-413` (listener Nacom)
- `app/portaria/routes.py:331/955`, `app/embarques/routes.py:474` (portas de frete)
- `.claude/references/modelos/CD_EXPEDICAO_LOCAL_CD.md` (SOT do local_cd)
- Workflow de diagnóstico: `wf_c8abf3ad-2f7` (6 investigadores + síntese + 3 propostas + julgamento)

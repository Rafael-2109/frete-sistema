<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-30
-->
# Motos Assaí — Estoque de Peças + Pendência (Spec 1 back-end): HANDOFF para o Spec 2

> **Papel:** estado vivo do trabalho "Pendências + Estoque de Peças" no módulo Motos Assaí. O **Spec 1 (back-end) está implementado, testado e pronto para merge, mas NÃO foi pushado**. Este doc é o ponto de retomada para uma nova sessão construir o **Spec 2 (UI)** + os follow-ups. Contém o **prompt de continuação** no fim.

## Indice

- [Contexto](#contexto)
- [Estado atual (o que existe)](#estado-atual-o-que-existe)
- [O que foi construído (Spec 1)](#o-que-foi-construído-spec-1)
- [Como foi validado](#como-foi-validado)
- [Follow-ups conhecidos (para o Spec 2)](#follow-ups-conhecidos-para-o-spec-2)
- [Spec 2 (UI) — escopo](#spec-2-ui-escopo)
- [Deploy — sequência obrigatória](#deploy-sequência-obrigatória)
- [Decisões em aberto](#decisões-em-aberto)
- [Referências](#referências)
- [Prompt de continuação (colar em nova sessão)](#prompt-de-continuação-colar-em-nova-sessão)

## Contexto

O dono pediu para ampliar o "meio" do processo de pendência do módulo `motos_assai` (categoria + origem + tratativa) e criar uma entidade de **Estoque de Peças** com movimentação rastreável. Decidiu-se dividir em **Spec 1 = back-end** (modelo de dados + serviços) e **Spec 2 = UI** (telas + fios). O Spec 1 foi desenhado, planejado e **implementado nesta sessão** (2026-06-30) via subagent-driven-development (12 tarefas TDD + 1 fix).

## Estado atual (o que existe)

- **Branch:** `main` local. **13 commits**: `125224c01` (migration 34) .. `751178d50` (schema+docs). **NÃO pushado** (push = auto-deploy Render).
- **Testes:** suíte completa do módulo **372 passed / 34 skipped / 0 failed**.
- **Review final whole-branch (opus):** PRONTO PARA MERGE — 0 Critical / 0 Important; todos os requisitos travados (§2/§14 do spec) cobertos e testados; 5 focos de integração verificados.
- **Ledger de execução (scratch, gitignored):** `.superpowers/sdd/progress.md` (12 tarefas + estado). Pode ser apagado por `git clean`; este handoff é o registro durável.

## O que foi construído (Spec 1)

**Princípio:** evento da moto = estado físico (1 PENDENTE/chassi, intocado) · ficha `assai_pendencia` = tratamento (N/chassi) · ledger `assai_estoque_movimento` = peça (elo). **Zero novo tipo de evento de moto.**

**6 tabelas novas** (migration 34): `assai_peca`, `assai_peca_modelo`, `assai_pendencia`, `assai_estoque_movimento`, `assai_peca_compra`, `assai_peca_compra_item`.

**Serviços** (`app/motos_assai/services/`):
- `peca_service` — catálogo + compatibilidade por modelo.
- `movimento_service` — ledger: `registrar_entrada`/`saldo`/`custo_medio` (média móvel + guarda div-zero)/`descartar`/`ajustar`/`consumir`/`canibalizar` (custo 0 + abre FALTA no doador, import lazy).
- `pendencia_service` — `abrir_pendencia`/`resolver_pendencia`/`cancelar_pendencia` sob `pg_advisory_xact_lock` (idempotência double-checked pós-lock), `solicitar_compra` (AGUARDANDO_PECA), `count_fisicas_abertas`, `afeta_estado_moto`, + 5 leituras migradas para a tabela.
- `compra_peca_service` — pedido GARANTIA/COMPRA (`PC-AAAA-NNNN`), `receber_item` → ENTRADA no ledger + recompute status.

**Integração** (Task 10): `montagem_service.registrar_montagem`/`enviar_para_pendencia` e `devolucao_service.criar_devolucao` agora **também abrem ficha** (passando `evento_pendente_id` explícito → sem 2º PENDENTE). `montagem_service.resolver_pendencia` virou **shim** retrocompatível (resolve a única física aberta por chassi, commita). Rota `POST /pendencias/resolver` e `services/__init__.py` intactos.

**Backfill:** `scripts/migrations/motos_assai_35_backfill_pendencias.py` (`--confirmar`/`--check`).

**Docs:** schema JSON das 6 tabelas + `TABLE_DESCRIPTIONS` + `app/motos_assai/CLAUDE.md` (35 tabelas, seção nova, `assai_avaria` removido do roadmap).

## Como foi validado

- Cada tarefa: implementer + reviewer (spec compliance + qualidade), TDD.
- Tarefas de concorrência (núcleo da pendência, resolver/gate, tratativas), integração e o review final: revisadas com **opus**.
- **1 Important achado e corrigido em execução:** TOCTOU de idempotência no resolver/cancelar (guard de idempotência rodava fora do advisory lock). Fix `08734cf0f` = double-checked locking (`db.session.refresh(ficha)` + re-check pós-lock).

## Follow-ups conhecidos (para o Spec 2)

Todos triados como **follow-up** no review final (nenhum bloqueia o merge):

1. **`_gerar_numero` → `CREATE SEQUENCE`** (item 1, fazer ANTES do deploy em prod). Hoje usa `COUNT()`+retry-SAVEPOINT — seguro (UNIQUE+retry), mas desvia da constraint §13.4 "NUNCA COUNT()". Trocar por `CREATE SEQUENCE IF NOT EXISTS assai_peca_compra_numero_seq` na **migration 34** (ainda não deployada) + `nextval()` em `_gerar_numero`.
2. **Guards de canibalização** (`movimento_service.canibalizar`): anti-cascata A→B→A (bloquear canibalizar peça já em FALTA aberta no doador — pré-mortem §13.2), `_exigir_peca` em `consumir`/`canibalizar` (hoje `peca_id` inválido vira IntegrityError cru), validar existência/estado do doador. Legítimo Spec 2: hoje `canibalizar`/`consumir`/`solicitar_compra` **não têm caller de produção** (a UI que os invoca é o Spec 2).
3. Polish: `.query.get()`→`db.session.get()` (recorrente, SA2.0); `lazy='joined'` nas 3 relations Usuario de `pendencia.py` → `select` + joinedload explícito nas leituras; `dados_extras` via `sanitize_for_json` em `consumir`/`canibalizar`; imports mortos (`EVENTO_PENDENCIA_RESOLVIDA` em `montagem_service`, `AssaiModelo` em `devolucao_service`, `pytest`/unused em testes); refinar a hint do `assai_pendencia.json` (`afeta_estado_moto` está abreviada — só cita pós-venda, omite `retorno_fisico`/origem física).
4. Test hygiene: alguns testes não limpam `AssaiMoto`/`AssaiMotoEvento` (deixam chassis `TST_` residuais — o `--check` local acha esses como lixo de teste, não afeta prod).

## Spec 2 (UI) — escopo

Da §15 do spec: cadastro de peça + compatibilidade; tela de estoque/saldo por peça; recebimento manual de peças (entrada sem NF, lote via `recebimento_ref`); tela de pendência categorizada com os ramos de tratativa (árvore da AVARIA) + provisão; **botão "gerar pendência" na área de pós-venda** (origem POS_VENDA_LOJA/CLIENTE); telas de pedido de compra (criar, receber itens); **reescrita da rota `POST /pendencias/resolver` para `pendencia_id` + `tratativa`** (Spec 1 deixou o shim por chassi); refactor de `pendencias/{abertas,historico}` para mostrar categoria/origem/tratativa; **ação de reclassificar pendências `INDETERMINADA`** (decisão R2); itens de menu; onboarding tours.

## Deploy — sequência obrigatória

A migration 34 e o backfill 35 são **manuais** (padrão 30/32/33, fora do `build.sh`). Ordem: **migration 34 → deploy do código → `python scripts/migrations/motos_assai_35_backfill_pendencias.py --confirmar` → `--check`**. Até o backfill 35 rodar, pendências já abertas em prod **não resolvem pela UI** (o shim falha alto — sem corromper nada). Por isso recomenda-se **bundlar o deploy do Spec 1 com o Spec 2** (evita um deploy intermediário que muda internos sem feature visível).

## Decisões em aberto

- **Push/deploy:** segurado (recomendação: bundlar com o Spec 2). Alternativa: push agora conduzindo a sequência de deploy acima.
- **`_gerar_numero`:** decidido — trocar por `SEQUENCE` no início do Spec 2 (a migration 34 ainda não foi para prod → emenda limpa).

## Referências

- Spec (design): `docs/superpowers/specs/2026-06-30-motos-assai-estoque-pecas-pendencia-design.md`
- Plano (12 tarefas TDD): `docs/superpowers/plans/2026-06-30-motos-assai-estoque-pecas-pendencia.md`
- Doc do módulo (atualizado): `app/motos_assai/CLAUDE.md` (seção "Estoque de Peças + Pendência categorizada (Spec 1)")
- Ledger de execução (scratch): `.superpowers/sdd/progress.md`

## Prompt de continuação (colar em nova sessão)

```
Dar continuidade ao trabalho "Estoque de Peças + Pendência categorizada" do módulo motos_assai.

ESTADO: o Spec 1 (back-end) está IMPLEMENTADO, testado (372 testes do módulo verdes) e pronto para merge, em 13 commits LOCAIS na main (125224c01..751178d50), NÃO pushados. Leia primeiro, nesta ordem:
1. docs/superpowers/plans/2026-06-30-motos-assai-estoque-pendencia-spec1-handoff.md (estado completo + follow-ups + escopo Spec 2)
2. docs/superpowers/specs/2026-06-30-motos-assai-estoque-pecas-pendencia-design.md (design; §2/§14 = decisões do dono; §15 = escopo do Spec 2)
3. app/motos_assai/CLAUDE.md (seção "Estoque de Peças + Pendência categorizada (Spec 1)")

PRÓXIMOS PASSOS:
1. Antes de tudo: trocar _gerar_numero (compra_peca_service.py) por CREATE SEQUENCE — emendar a migration 34 (ainda não deployada) com CREATE SEQUENCE IF NOT EXISTS assai_peca_compra_numero_seq + nextval(); aplicar local + teste.
2. Brainstorm + spec do Spec 2 (UI) seguindo a §15, dobrando nele os follow-ups do handoff (guards de canibalização anti-cascata/_exigir_peca/doador-vendido; polish .query.get()/lazy='joined'/sanitize/imports mortos; reescrita da rota resolver para pendencia_id; reclassificar INDETERMINADA).
3. Deploy quando o Spec 2 fechar: migration 34 → código → backfill 35 --confirmar → --check (bundlar Spec 1 + Spec 2).

Use o fluxo de sempre: brainstorming → writing-plans → subagent-driven-development. NÃO pushar sem meu aval.
```

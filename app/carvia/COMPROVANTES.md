<!-- doc:meta
tipo: explanation
camada: L2
sot_de: comprovantes-pagamento
hub: app/carvia/CLAUDE.md
superseded_by: —
atualizado: 2026-06-16
-->
# Comprovantes de Pagamento CarVia

> **Papel:** explica o design da feature de Comprovantes de Pagamento (anexo de
> PIX/boleto/TED na cadeia de frete, com propagacao e uso na conciliacao).
> **Abra quando:** for mexer em comprovantes, na flag "Cotacao Paga" ou na
> "Conciliacao p/ Comprovante".

## Indice

- [Contexto](#contexto)
- [Modelo de dados (N:N)](#modelo-de-dados-nn)
- [Propagacao pela cadeia](#propagacao-pela-cadeia)
- [Rotas e UI](#rotas-e-ui)
- [Flag "Cotacao Paga"](#flag-cotacao-paga)
- [Conciliacao p/ Comprovante (invertida)](#conciliacao-p-comprovante-invertida)
- [Estado de implementacao](#estado-de-implementacao)

## Contexto

**Finalidade:** destravar a conciliacao bancaria de pagamentos de frete
**despadronizados**. O cliente paga de formas que a fatura sozinha nao explica —
**antecipado** (antes de a NF/CTe/fatura existirem), com **CNPJ diferente** do
da fatura, ou **um pagamento para varios fretes** de uma vez. Nesse cenario, o
fluxo normal (selecionar a linha do extrato → caçar a fatura) fica dificil ou
ambiguo.

O comprovante (PIX/boleto/TED) carrega os dados **reais** do pagamento — quem
pagou (`cnpj_pagador`), quanto (`valor`), quando (`data_pagamento`). Anexado na
**cotacao** (onde o pagamento antecipado nasce) e **propagado** por toda a cadeia
(NF → CTe → Fatura Cliente), ele fica sempre a mao e **enriquece a fatura** o
bastante para **inverter a busca**: partir das faturas-com-comprovante e ir atras
da linha do extrato (modo "Conciliacao p/ Comprovante"). **Esse e o ganho
central** — propagacao, flag "Cotacao Paga" e emoji nas listagens sao **meios**
para ter o comprovante acessivel e visivel onde a conciliacao acontece.

Escopo (decisao Rafael, 2026-06-16): propaga **so para Fatura Cliente**
(pagamento e do cliente = receita), nao para Fatura Transportadora.

## Modelo de dados (N:N)

Diferente de `CarviaAnexo` (1 anexo → 1 entidade), o comprovante e **N:N**: um
comprovante pode cobrir varios documentos (paga 2 fretes) e um documento pode
ter varios comprovantes. O arquivo vive **uma vez** no S3.

- **`CarviaComprovantePagamento`** (`carvia_comprovantes_pagamento`): arquivo S3
  (`caminho_s3`, `nome_original`...) + metadados de conciliacao opcionais
  (`valor`, `data_pagamento`, `cnpj_pagador`, `descricao`), `ativo` (soft-delete).
- **`CarviaComprovanteVinculo`** (`carvia_comprovante_vinculos`): vinculo
  polimorfico — `comprovante_id` FK + (`entidade_tipo` ∈ `cotacao|nf|operacao|
  fatura_cliente`, `entidade_id`) + `origem` (`MANUAL` upload direto |
  `PROPAGADO` herdado). UNIQUE (`comprovante_id`, `entidade_tipo`, `entidade_id`).

Models em `models/comprovante.py`; campos exatos nos schemas JSON
`carvia_comprovantes_pagamento.json` / `carvia_comprovante_vinculos.json`.

## Propagacao pela cadeia

**Por que propagar:** o comprovante nasce na cotacao (pagamento antecipado), mas
a conciliacao acontece na **fatura**. Propagar garante que o mesmo comprovante
esteja vinculado a fatura — e a NF/CTe — sem o operador reanexar documento a
documento.

`CarviaComprovanteService.sincronizar_cadeia(entidade_tipo, entidade_id)` e a
operacao central, **idempotente**: garante que todo comprovante ATIVO de
qualquer entidade do fecho da cadeia esteja vinculado a TODAS as entidades do
fecho.

O fecho e calculado por `_entidades_relacionadas`, com **NFs como eixo**:
- `operacao → NFs` via `CarviaOperacaoNf` (FK real)
- `operacao → fatura_cliente` via `CarviaOperacao.fatura_cliente_id` (FK real)
- `cotacao ↔ NF` via `numero_nf` (string match, mesmo elo textual do resto do
  modulo — Refator 2.5 ainda nao FK)

Chamada no **upload** (propaga retroativo para o que ja existe). Para heranca
**futura** (documento criado depois do comprovante), o hook
`sincronizar_cadeia('fatura_cliente', id)` deve ser plugado nos pontos de
criacao de fatura cliente (pendente — ver Estado).

## Rotas e UI

Rotas (AJAX, lazy imports R2) em `routes/comprovante_routes.py`:
- `POST /carvia/api/comprovante/<tipo>/<id>/upload` — upload + propagacao
- `POST /carvia/api/comprovante/<id>/excluir` — soft-delete
- `GET  /carvia/api/comprovante/<id>/download` — redirect presigned S3
- `POST /carvia/api/cotacao/<id>/marcar-pago` — toggle flag "Cotacao Paga"
- `GET  /carvia/conciliacao/por-comprovante` — pagina da conciliacao invertida
  (em `routes/conciliacao_routes.py`)

UI: widget `templates/carvia/_comprovantes_card.html` (macro `comprovantes_card`,
recebe pares `(comprovante, vinculo)` de `CarviaComprovanteService.listar`) +
`static/carvia/js/comprovantes_widget.js`. Upload coleta valor/data/cnpj_pagador.
Badge de origem `MANUAL`/`PROPAGADO`. O card e renderizado nas **4 telas de
detalhe** (cotacao, NF, CTe/operacao, fatura cliente); o toggle "Cotacao Paga"
fica na cotacao. As **4 listagens** exibem o emoji 💳 (via `tem_comprovante_batch`).

## Flag "Cotacao Paga"

Sinal manual **redundante** ao comprovante (a pedido do Rafael, ajuda visao
rapida). Campos `pago` / `pago_em` / `pago_por` em `carvia_cotacoes`; toggle via
`marcar_pago_cotacao`. Independente de ter comprovante anexado.

## Conciliacao p/ Comprovante (invertida)

**Este e o destino da feature** — o resto (modelo, propagacao, flags) e
infraestrutura para chegar aqui. 2o modo, em **pagina dedicada**
`GET /carvia/conciliacao/por-comprovante` (linkada no header da conciliacao por
extrato), que **inverte o fluxo atual**: em vez de selecionar linha do extrato →
buscar fatura, lista **faturas cliente com comprovante e nao 100% conciliadas**
(`CarviaComprovanteService.faturas_cliente_com_comprovante`) → exibe o
comprovante (valor/data/cnpj_pagador) → sugere linhas de extrato candidatas
(reusa `api_matches_por_documento`) → concilia reusando `api_conciliar`
(`CarviaConciliacao`). Complementa o pre-vinculo extrato↔cotacao (R16).

**Scoring guiado pelo `cnpj_pagador`** (o que resolve "pagou com CNPJ ≠
fatura"): em `api_matches_por_documento`, para `fatura_cliente`, le os
`cnpj_pagador` dos comprovantes da fatura (`cnpjs_pagadores`) e da boost
**deterministico** a linha do extrato cuja descricao traz esse CNPJ (score 0.95)
ou a raiz de 8 digitos (0.82) — flag `score_comprovante` na resposta/UI. Reusa
`extrair_cnpjs_da_descricao` / `extrair_raizes_cnpj_da_descricao` do
`carvia_sugestao_service`.

## Estado de implementacao

> Estado vivo e proximos passos: `.remember/remember.md` + memoria
> `carvia-comprovantes-pagamento-wip`.

- **PRONTO + TESTADO** (13 testes em `tests/carvia/test_comprovante_*.py` —
  models, propagacao, conciliacao invertida):
  - models (N:N) + flag "Cotacao Paga";
  - service: `sincronizar_cadeia` (propagacao), `tem_comprovante_batch`,
    `cnpjs_pagadores`, `faturas_cliente_com_comprovante`;
  - rotas AJAX (upload / excluir / download / marcar-pago);
  - widget + JS; **card nas 4 telas de detalhe** + toggle na cotacao;
  - **emoji 💳 nas 4 listagens**;
  - **hook de heranca** `sincronizar_cadeia('fatura_cliente', id)` na criacao da
    fatura (`fatura_routes.py`, isolado por SAVEPOINT — espelha o pre-vinculo);
  - **conciliacao invertida** (pagina + boost por `cnpj_pagador` em
    `api_matches_por_documento`);
  - migration `scripts/migrations/carvia_comprovante_pagamento.{sql,py}`
    (rodada **LOCAL**).
- **PENDENTE (PROD/Rafael)**: rodar `carvia_comprovante_pagamento.py` em PROD;
  commit do working tree (F3 ainda nao commitada — separar das mudancas de
  outras sessoes, como nas Frentes 1+2 `eaf1183ef`).

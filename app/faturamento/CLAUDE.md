<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->
# Faturamento — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo Faturamento — ingestao das NFs (via sync Odoo) e o **match NF → Embarque/Separacao**. O `ProcessadorFaturamento` vincula a NF a um `EmbarqueItem` existente, marca a Separacao FATURADO, cria a movimentacao de estoque e encadeia a sincronizacao de entregas e o lancamento de frete.

## Indice

- [Contexto](#contexto)
- [Estrutura](#estrutura)
- [Blueprints e Rotas](#blueprints-e-rotas)
- [Regras Criticas](#regras-criticas)
  - [R1: Dois models distintos — cabecalho vs item](#r1-dois-models-distintos-cabecalho-vs-item)
  - [R2: NF NAO cria EmbarqueItem — vincula por origem(pedido)+lote](#r2-nf-nao-cria-embarqueitem-vincula-por-origempedidolote)
  - [R3: Envio parcial — escolha de lote por SCORING (fallback silencioso)](#r3-envio-parcial-escolha-de-lote-por-scoring-fallback-silencioso)
  - [R4: status_nf significa coisas diferentes em tabelas diferentes](#r4-status_nf-significa-coisas-diferentes-em-tabelas-diferentes)
  - [R5: Inativar != Cancelar != Excluir](#r5-inativar-cancelar-excluir)
  - [R6: Commit unico; FATURADO so apos commit OK](#r6-commit-unico-faturado-so-apos-commit-ok)
  - [R7: Sync de entregas e SINCRONO de proposito (rollback O4)](#r7-sync-de-entregas-e-sincrono-de-proposito-rollback-o4)
- [Models](#models)
- [Fluxo (Odoo → 4 sincronizacoes)](#fluxo-odoo-4-sincronizacoes)
- [Gotchas](#gotchas)
- [Interdependencias](#interdependencias)
- [Referencias](#referencias)

## Contexto

15 arquivos Python (~5.1K LOC — `routes.py` 1.494, `models.py` 118, 6 services, 2 jobs RQ, 1 API). A NF entra **exclusivamente via sincronizacao Odoo** (a importacao por upload foi removida). O coracao e `services/processar_faturamento.py` (`ProcessadorFaturamento`): casa cada NF contra o `EmbarqueItem` ativo do pedido e marca a Separacao FATURADO.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{relatorio_faturamento_importado,faturamento_produto}.json`
> Separacao (recebe FATURADO/sincronizado_nf): `app/separacao/CLAUDE.md`
> Embarque (recebe a NF no item): `app/embarques/CLAUDE.md`
> Frete (disparado por CNPJ): `app/fretes/CLAUDE.md`

---

## Estrutura

```
app/faturamento/
  ├── models.py    # 118 LOC — RelatorioFaturamentoImportado (cabecalho) + FaturamentoProduto (item)
  ├── routes.py    # 1.494 LOC — faturamento_bp (listar/dashboard/reconciliacao/inativar/cancelar/sync Odoo)
  ├── api/atualizar_nf_api.py  # 2o blueprint atualizar_nf_bp (preenche NF de EmbarqueItem com erro)
  ├── services/
  │   ├── processar_faturamento.py        # CORE — match NF↔Embarque, scoring, FATURADO, MovimentacaoEstoque
  │   ├── reconciliacao_separacao_nf.py    # reconcilia NF×Separacao em lote (CLI); SOBRESCREVE qtd/valor/peso
  │   ├── reconciliacao_service.py         # busca NFs sem vinculacao
  │   ├── recuperar_separacoes_perdidas.py # reconstroi Separacao ausente (engenharia reversa)
  │   ├── atualizar_nf_embarque.py         # recuperacao manual: seta nota_fiscal por parsing de observacao
  │   └── atualizar_peso_service.py        # recalcula peso/pallet por NF (cascata ate Frete)
  └── jobs/        # retry_nf_sync_job (fila 'faturamento'), sincronizar_entregas_job (ROLLBACKED — ver R7)
```

---

## Blueprints e Rotas

Dois blueprints, ambos `/faturamento`: `faturamento_bp` (`__init__.py:918`+`:982`) e `atualizar_nf_bp` (`__init__.py:919`). Rotas-chave: `api/sincronizar-odoo` (origem real dos dados), `listar`/`produtos`/`dashboard`, `dashboard-reconciliacao`/`conciliacao-manual`, `inativar-nfs`, `cancelar-nf-devolvida` (admin), `api/excluir-nf/<nf>` (DELETE hard), `api/atualizar-nf-embarques`.

---

## Regras Criticas

### R1: Dois models distintos — cabecalho vs item
`RelatorioFaturamentoImportado` = **cabecalho** da NF (1 linha/NF, `numero_nf` UNIQUE, soft-delete via `ativo`). `FaturamentoProduto` = **item** (N linhas/NF, `numero_nf` NAO-unique, 1 por `cod_produto`). Para somar por produto/pedido use `FaturamentoProduto`; para 1 NF use o `Relatorio`. Ambos tem campo `origem`, mas em `FaturamentoProduto` `origem` = **num_pedido** (chave do match). Nao ha event listener neste modulo — efeitos sao explicitos nos services. `nf_cd` NAO existe aqui (a logica 2-CD vive em `app/utils/local_cd.py`).

### R2: NF NAO cria EmbarqueItem — vincula por origem(pedido)+lote
O match busca `EmbarqueItem` ativo por `pedido == nf.origem` + `status=='ativo'` + Embarque ativo, e so preenche `nota_fiscal` num item existente sem NF. A chave de juncao e o **LOTE** (`separacao_lote_id`) + pedido. Se nao existe item, a NF fica "Sem Separacao" (`MovimentacaoEstoque` com `separacao_lote_id=None`, reprocessavel). Pedido divergente: grava `erro_validacao='NF_DIVERGENTE:...'` no item mas AINDA cria a movimentacao sem lote (nao bloqueia).

### R3: Envio parcial — escolha de lote por SCORING (fallback silencioso)
Quando ha multiplos `EmbarqueItem` ativos para o mesmo pedido (envio parcial), o lote NAO e o primeiro: calcula um score por produto (`min/max` de qtd NF×Separacao, cobertura, penalidade por produtos extras) e escolhe o maior. **Fallback perigoso**: se nenhum score > 0, usa `lotes_candidatos[0]` com so um `warning` → pode vincular a NF ao lote errado. Score < 0.99 cria `FaturamentoParcialJustificativa` (motivo/classificacao vazios p/ preencher depois).

### R4: status_nf significa coisas diferentes em tabelas diferentes
`FaturamentoProduto.status_nf`: `Provisório` (default) → `SEM_LOTE` (mov criada sem lote) → `Lançado` (lote vinculado), ou `Cancelado`. `MovimentacaoEstoque.status_nf`: `FATURADO` / `SEM_LOTE` / `CANCELADO` (MAIUSCULO). NAO assumir o mesmo vocabulario ao cruzar as tabelas. Idempotencia ancorada em `MovimentacaoEstoque.separacao_lote_id` (mov com lote + FATURADO = completa; mov sem lote = reprocessar).

### R5: Inativar != Cancelar != Excluir
Tres operacoes distintas: `inativar-nfs` seta `RelatorioFaturamentoImportado.ativo=False` E **DELETA** a `EntregaMonitorada`. `cancelar-nf-devolvida` (admin) cascateia: `FaturamentoProduto` → `Cancelado`, `MovimentacaoEstoque` → `ativo=False` (reverte estoque), `Relatorio` → `ativo=False`. `api/excluir-nf` e DELETE fisico. Uma NF toda cancelada (`all(p.status_nf=='Cancelado')`) NAO cria movimentacao.

### R6: Commit unico; FATURADO so apos commit OK
`ProcessadorFaturamento.processar_nfs_importadas` faz 1 commit no fim do batch (try/except + rollback isolado por NF) e **SO ENTAO** chama `_atualizar_status_separacoes_faturadas` (que faz commit proprio). Ordem critica: se o commit falha, o batch inteiro vai para retry (nenhuma Separacao fica FATURADO orfa). NF falhada → retry RQ (fila `faturamento`, backoff 60·2^n, max 3, depois audit jsonl).

### R7: Sync de entregas e SINCRONO de proposito (rollback O4)
Existe um job RQ `sincronizar_entregas_batch`, mas ele foi **ROLLBACKED**: a versao async duplicava `EntregaMonitorada` (2 workers paralelos na fila `default`, sem UNIQUE em `numero_nf`). O codigo VIVO usa loop sincrono em `odoo/services/faturamento_service.py`. **NAO reativar o job sem aplicar UNIQUE + ON CONFLICT em `numero_nf`.**

---

## Models

> Campos completos: `.claude/skills/consultando-sql/schemas/tables/{relatorio_faturamento_importado,faturamento_produto}.json`

| Model | Tabela | Gotcha principal |
|-------|--------|------------------|
| `RelatorioFaturamentoImportado` | `relatorio_faturamento_importado` | CABECALHO (1/NF). `numero_nf` UNIQUE. Soft-delete `ativo`+`inativado_em/por`. NAO tem produtos |
| `FaturamentoProduto` | `faturamento_produto` | ITEM (N/NF). `numero_nf` NAO unique. `origem`=num_pedido (chave do match). `status_nf` = maquina (R4). Campos de reversao: `revertida`, `nota_credito_id` |

> Modelos tocados (de outros modulos): `EmbarqueItem` (`nota_fiscal`/`erro_validacao`), `Separacao` (`sincronizado_nf`/`numero_nf`/FATURADO), `MovimentacaoEstoque` (baixa `-qtd`), `EntregaMonitorada` (sem UNIQUE em `numero_nf` — causa do O4). Produto **PALLET (208000012) e pulado** (gerido por `PalletSyncService` — esquecer causa dupla baixa).

---

## Fluxo (Odoo → 4 sincronizacoes)

`api/sincronizar-odoo` → `importar_faturamento_odoo` (`app/odoo/services/faturamento_service.py`) persiste cabecalho + itens e, na MESMA sync, dispara em ordem: **(1)** `sincronizar_entrega_por_nf` (monitoramento, sincrono — R7); **(2)** `revalidar_embarques_pendentes` (re-roda `validar_cnpj_embarque_faturamento` para itens com `NF_PENDENTE_FATURAMENTO`); **(3)** NFs pendentes em embarques; **(4)** frete via `processar_lancamento_automatico_fretes(cnpj_cliente=...)` **por CNPJ** (nao por NF/embarque; conta como lancado so se o resultado contem `'lancado(s) automaticamente'`). O match NF↔Embarque (R2/R3) acontece dentro do `ProcessadorFaturamento`.

---

## Gotchas

- **G1 — `nf.origem` E o num_pedido** (campo enganoso — nao e UF/local).
- **G2 — reconciliacao SOBRESCREVE a Separacao**: `reconciliacao_separacao_nf` faz `sep.qtd_saldo=qtd_nf`, `valor_saldo`, `peso` e recalcula pallet quando diverge > 0.01 — efeito destrutivo no snapshot original.
- **G3 — `atualizar_nf_embarque` faz parsing de observacao** (regex `lote separacao {id}` + `NF (\d+)` em `MovimentacaoEstoque.observacao`): recuperacao manual fragil; **NAO marca Separacao FATURADO** (so seta `nota_fiscal`+limpa erro).
- **G4 — cache de separacoes do batch fica stale**: chaveado por `{lote}_{origem}` com `sincronizado_nf=False`; apos uma NF marcar `sincronizado_nf=True`, a NF seguinte do mesmo lote pode ler do cache desatualizado.
- **G5 — `recuperar_separacoes_perdidas`** (nome enganoso) reconstroi Separacao ausente para pedidos com lote+NF mas sem registro fisico (tem `modo_simulacao`).

---

## Interdependencias

| Importa de | O que | Pattern |
|-----------|-------|---------|
| `app.odoo.services.faturamento_service` | `importar_faturamento_odoo` (origem REAL das NFs) | lazy |
| `app.embarques.models` | `Embarque`, `EmbarqueItem` (match por lote+pedido) | top-level |
| `app.separacao.models` | `Separacao` (marca FATURADO/sincronizado_nf) | top-level |
| `app.estoque.models` | `MovimentacaoEstoque` (baixa de venda) | top-level |
| `app.fretes.routes` | `validar_cnpj_embarque_faturamento` (top-level), `processar_lancamento_automatico_fretes` (SYNC 4) | top-level / via Odoo service |
| `app.monitoramento.models` / `app.utils.sincronizar_entregas` | `EntregaMonitorada`, `sincronizar_entrega_por_nf` | top-level |

> **Exporta** os 2 models (+ `ProcessadorFaturamento`) para ~15 modulos (monitoramento, devolucao, comercial, embarques [totais], fretes [analise real], integracoes/tagplus, carteira, portal, BI).

---

## Referencias

| Preciso de... | Documento |
|---------------|-----------|
| Separacao (FATURADO / sincronizado_nf / maquina de estados) | `app/separacao/CLAUDE.md` |
| Embarque (recebe a NF no EmbarqueItem) | `app/embarques/CLAUDE.md` |
| Portaria (data_embarque antes do faturamento) | `app/portaria/CLAUDE.md` |
| Frete real (disparado por CNPJ) | `app/fretes/CLAUDE.md` |
| Reconciliacao financeira Local×Odoo | `app/financeiro/FLUXOS_RECONCILIACAO.md` |
| Campos de qualquer tabela | `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |

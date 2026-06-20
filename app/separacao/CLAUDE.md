<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->
# Separacao — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo Separacao — **tabela-fato central** do sistema pos-Carteira. O ativo do modulo NAO sao as rotas (legadas), e o MODEL `Separacao` + seus event listeners, que sao a **maquina de estados** de todo o fluxo logistico e ressincronizam os totais do Embarque. Importado por ~40 modulos.

## Indice

- [Contexto](#contexto)
- [Estrutura](#estrutura)
- [Regras Criticas](#regras-criticas)
  - [R1: Tabela-fato — 1 linha = 1 ITEM; Pedido e VIEW](#r1-tabela-fato-1-linha-1-item-pedido-e-view)
  - [R2: status e DERIVADO por listener — nunca setar a mao (exceto PREVISAO)](#r2-status-e-derivado-por-listener-nunca-setar-a-mao-exceto-previsao)
  - [R3: Sempre ORM (.all() + loop), nunca bulk UPDATE](#r3-sempre-orm-all-loop-nunca-bulk-update)
  - [R4: O listener remoto recalcula o Embarque e RE-LEVANTA erro](#r4-o-listener-remoto-recalcula-o-embarque-e-re-levanta-erro)
  - [R5: A criacao REAL de Separacao vive em app/carteira](#r5-a-criacao-real-de-separacao-vive-em-appcarteira)
  - [R6: status_calculado (leitura) diverge da coluna persistida](#r6-status_calculado-leitura-diverge-da-coluna-persistida)
- [Maquina de Estados](#maquina-de-estados)
- [Model e Event Listeners](#model-e-event-listeners)
- [Rotas (legado)](#rotas-legado)
- [Gotchas](#gotchas)
- [Interdependencias](#interdependencias)
- [Referencias](#referencias)

## Contexto

4 arquivos Python (~930 LOC). O peso esta em `models.py` (524 LOC): o model `Separacao`, 4 event listeners e 3 funcoes de reversao. `routes.py` e superficie **legada** (import Excel + CRUD de exclusao). `Separacao` e a tabela onde vivem expedicao/agendamento/cotacao/NF de cada item — `Pedido` e apenas uma VIEW agregada sobre ela.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/separacao.json`
> Como a Separacao NASCE (fluxo vivo): `app/carteira/CLAUDE.md` (`routes/separacao_api.py`, `utils/separacao_utils.py`)
> Quem consome o status: `app/cotacao/CLAUDE.md`, `app/embarques/CLAUDE.md`, `app/portaria/CLAUDE.md`, `app/faturamento/CLAUDE.md`
> CD de expedicao (2-CD): `app/utils/local_cd.py`

---

## Estrutura

```
app/separacao/
  ├── __init__.py   # VAZIO
  ├── models.py     # 524 LOC — O ATIVO: model Separacao + 4 listeners + 3 funcoes de reversao
  ├── forms.py      #   7 LOC — ImportarExcelForm (File+Submit)
  └── routes.py     # ~400 LOC — LEGADO: separacao_bp (importar Excel, listar, excluir, excluir_lote)
```

---

## Regras Criticas

### R1: Tabela-fato — 1 linha = 1 ITEM; Pedido e VIEW
Cada linha de `separacao` e **um item (produto) de um lote**, NAO uma separacao inteira. Chave logica = `separacao_lote_id` (VARCHAR, ex `LOTE_20251004_032844_195`, NAO integer) + `num_pedido` + `cod_produto`. `Pedido` e uma VIEW agregada sobre esta tabela (somente leitura — escrever vai sempre na `Separacao`). Campo de quantidade = `qtd_saldo` (NAO `qtd_saldo_produto_pedido`, que e da `CarteiraPrincipal`). `expedicao`/`agendamento`/`protocolo` existem aqui e NAO na Carteira.

### R2: status e DERIVADO por listener — nunca setar a mao (exceto PREVISAO)
`status` e coluna persistida mas e **REESCRITA** pelo listener `atualizar_status_automatico` (before_insert **e** before_update) a cada gravacao, com ordem de prioridade FIXA:
`PREVISAO` (early-return, unico manual) → `NF no CD` (`nf_cd`) → `FATURADO` (`sincronizado_nf` OU `numero_nf`) → `COTADO` (`cotacao_id`) → `ABERTO`. Para mudar o status, mude as **flags-fonte** (`cotacao_id`/`sincronizado_nf`/`nf_cd`) — atribuir `status='COTADO'` e inutil (sera sobrescrito). `data_embarque` NAO participa da derivacao.

### R3: Sempre ORM (.all() + loop), nunca bulk UPDATE
Todos os helpers (`atualizar_status`, `atualizar_nf_cd`, `atualizar_cotacao`) e as funcoes de reversao (`remover_do_embarque`, `remover_cotacao`, `cancelar_faturamento`) carregam via `query.all()` e iteram setando atributos — DE PROPOSITO, para disparar os event listeners. Um `query().update()` em massa **PULA os listeners**: o status nao recalcula e os totais do embarque nao reagregam. (Paths que escrevem `status` direto via bulk — faturamento backfill, cancelamento de embarque — fazem isso conscientemente.) Esses helpers tambem dao `commit()` interno (cuidado dentro de transacao maior).

### R4: O listener remoto recalcula o Embarque e RE-LEVANTA erro
`recalcular_totais_embarque` (after_update **e** after_delete) reescreve, via SQL cru (`connection`, nao session), `EmbarqueItem` e `Embarque` do lote. Soma apenas Separacoes com `sincronizado_nf == False` (linhas faturadas saem do total). **Mapeamento que engana**: `EmbarqueItem.valor` ← `sum(Separacao.valor_saldo)`, `EmbarqueItem.pallets` ← `sum(Separacao.pallet)`. Em erro ele faz `raise` (deliberado) → **derruba o UPDATE/DELETE da Separacao**. Mexer numa Separacao dentro de transacao grande: um erro no recalc do embarque aborta tudo.

### R5: A criacao REAL de Separacao vive em app/carteira
As rotas deste modulo so criam Separacao por **import de Excel** (legado). O fluxo de negocio Carteira→Separacao esta em `app/carteira/routes/separacao_api.py`, `carteira_simples/separacao_api.py` e `utils/separacao_utils.py` (`gerar_separacao_workspace_interno`). Ao investigar "como nasce uma Separacao", olhar a carteira, NAO `app/separacao/routes.py`.

### R6: status_calculado (leitura) diverge da coluna persistida
A property `status_calculado` (usada em telas) AINDA tem um branch `EMBARCADO` (data_embarque preenchida sem NF) que a **coluna persistida nunca produz** (o listener nao deriva EMBARCADO). Os dois podem divergir. Para filtros SQL use a **coluna** `status`; `status_calculado` so existe no objeto Python carregado. `EMBARCADO` deixou de ser status persistido — virou badge visual.

---

## Maquina de Estados

| De | Para | Gatilho | Onde |
|----|------|---------|------|
| ABERTO | COTADO | `cotacao_id` setado | `cotacao` fechar_frete → `atualizar_cotacao()` (ORM) |
| COTADO | (data_embarque) | saida da portaria carimba `data_embarque` | `portaria` — **NAO muda status** (so badge) |
| COTADO/* | FATURADO | `sincronizado_nf=True`+`numero_nf` | `faturamento` (path flag) ou status direto (backfill) |
| FATURADO | NF no CD | `nf_cd=True` (NF faturada voltou ao CD) | cancelamento de embarque OU evento manual no monitoramento |

> `nf_cd=True` tem prioridade MAXIMA: uma NF que voltou ao CD aparece como `NF no CD` mesmo com `numero_nf` preenchido. Detalhe da maquina: cada modulo da cadeia mexe nas FLAGS, nunca no `status` direto (no fluxo normal).

---

## Model e Event Listeners

> Campos completos: `.claude/skills/consultando-sql/schemas/tables/separacao.json`

**Campos-chave / gotchas**: `sincronizado_nf` (gatilho principal de projecao de estoque E de FATURADO; o listener de totais so soma `sincronizado_nf==False`), `nf_cd`, `local_cd` (NOT NULL default `VICTORIO_MARCHEZINE`), `chassi_assai` (preenchido so em lotes `ASSAI-SEP-%`; NULL para Nacom/CarVia), `tags_pedido`/`equipe_vendas` (desnormalizados de `CarteiraPrincipal`), `tipo_envio` (total/parcial), `roteirizacao` (DEPRECADO). `observ_ped_1` truncado em 700 chars.

| Listener | Evento | Efeito |
|----------|--------|--------|
| `atualizar_status_automatico` | before_insert + before_update | **O coracao** — rederiva `status` (R2) |
| `recalcular_totais_embarque` | after_update + after_delete | Reescreve totais do Embarque via SQL cru; **re-raise** (R4) |
| `setar_falta_pagamento_inicial` | before_insert | Le `CarteiraPrincipal.cond_pgto_pedido`; se `ANTECIPADO` → `falta_pagamento=True`. SO no INSERT (preserva escolha manual) |
| `log_reversao_status` | after_update | Apenas LOG de reversoes (o dict ainda cita pares `EMBARCADO` — codigo morto) |

Helpers de classe (ORM + commit interno): `atualizar_status`, `atualizar_nf_cd`, `atualizar_cotacao` (retorna count). Funcoes module-level de reversao: `remover_do_embarque`, `remover_cotacao`, `cancelar_faturamento`.

---

## Rotas (legado)

Blueprint `separacao` (`/separacao`), registrado em `app/__init__.py:936`+`:1001`. Rotas: `importar` (Excel → 1 lote por `num_pedido`+`expedicao`), `listar` (paginado 200/pag — **SEM `@login_required`**), `excluir`/`excluir_lote` (gate: bloqueia se o Pedido estiver FATURADO/COTADO/EMBARCADO). Erro por linha no import faz `rollback()` de TODA a sessao.

---

## Gotchas

- **G1 — `status_calculado` ≠ coluna `status`** (R6): EMBARCADO so existe na property de leitura.
- **G2 — listeners usam `connection` (Core), nao `db.session`**: por isso `select()`/`text()` cru; as mudancas ficam na MESMA transacao do flush.
- **G3 — `recalcular_totais_embarque` exclui linhas faturadas** (`sincronizado_nf==False`): apos faturar, o item sai do total do embarque.
- **G4 — `separacao_lote_id` e VARCHAR** apesar do sufixo `_id`; prefixo `CARVIA-`/`ASSAI-` roteia o dominio em toda a cadeia.

---

## Interdependencias

| Importa de | O que | Pattern |
|-----------|-------|---------|
| `app.carteira.models` | `CarteiraPrincipal` (no listener de falta_pagamento) | lazy (dentro do listener) |
| `app.embarques.models` | `Embarque`, `EmbarqueItem` (no listener de totais) | lazy |
| `app.utils.timezone` / `app.utils.lote_utils` | `agora_utc_naive`, `gerar_lote_id` | top-level |

> **Exporta** o model `Separacao` para ~40 modulos (carteira, embarques, portaria, faturamento, monitoramento, cotacao, comercial, producao, estoque, integracoes, workers). As rotas (`routes.py`) so sao consumidas pelo registro do blueprint.

---

## Referencias

| Preciso de... | Documento |
|---------------|-----------|
| Como a Separacao nasce (carteira→separacao) | `app/carteira/CLAUDE.md` |
| Cotacao (seta cotacao_id → COTADO) | `app/cotacao/CLAUDE.md` |
| Embarque (recebe os totais via listener) | `app/embarques/CLAUDE.md` |
| Portaria (carimba data_embarque) | `app/portaria/CLAUDE.md` |
| Faturamento (seta sincronizado_nf → FATURADO) | `app/faturamento/CLAUDE.md` |
| Regras CarteiraPrincipal / Separacao | `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md` |
| Campos de qualquer tabela | `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |

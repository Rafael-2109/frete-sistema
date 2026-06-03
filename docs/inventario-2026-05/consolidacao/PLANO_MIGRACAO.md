<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/inventario-2026-05/consolidacao/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# PLANO DE MIGRAÇÃO — `app/odoo/estoque/` (gold-utils · gold-scripts · gold-orchestrators)

> **Papel:** PLANO DE MIGRAÇÃO — `app/odoo/estoque/` (gold-utils · gold-scripts · gold-orchestrators).

## Indice

- [1. Estrutura-alvo](#1-estrutura-alvo)
- [2. Gatilhos de substituição (por SITUAÇÃO do arquivo)](#2-gatilhos-de-substituição-por-situação-do-arquivo)
- [3. gold-utils](#3-gold-utils)
- [4. gold-scripts (mover `app/odoo/services/` → `app/odoo/estoque/scripts/`)](#4-gold-scripts-mover-appodooservices-appodooestoquescripts)
- [5. gold-orchestrators](#5-gold-orchestrators)
- [6. scripts/inventario_2026_05/ (~90) — destino por categoria](#6-scriptsinventario_2026_05-90-destino-por-categoria)
- [7. Estratégia de shims (preservar operação ativa)](#7-estratégia-de-shims-preservar-operação-ativa)
- [8. Ordem de execução (bottom-up — não inverter)](#8-ordem-de-execução-bottom-up-não-inverter)

> **NOTA (Onda 2 PAD-A):** "gold-utils/gold-scripts/gold-orchestrators" é vocabulário APOSENTADO — a nomenclatura vigente é services/primitivas (C1/C2) · orchestrators (C3), definida em `app/odoo/estoque/CLAUDE.md`. Este doc é mineração transitória válida; a consolidação real dos scripts é a Onda 3.

**Criado:** 2026-05-20 | **Decisão:** pacote dedicado `app/odoo/estoque/` com shims de compatibilidade (blast radius contido: só inventário + testes importam).
**Companheiros:** [`MAPA_ASSUNTOS.md`](MAPA_ASSUNTOS.md) (o "o quê existe") · [`MAPA_SCRIPTS.md`](MAPA_SCRIPTS.md) (mineração: cada um dos ~100 scripts → gold destino). Este doc é o **"o quê e como migrar"**.

> ⚠️ **Operação viva:** o nº de scripts cresce (90→100 só nesta sessão). **Antes de cada onda, reconciliar com `find scripts/inventario_2026_05 -name '*.py'`** e atualizar o `MAPA_SCRIPTS`. Ex.: `transferir_lote.py` já é o genérico de transferência net-zero — **promover, não recriar**.

> **"Quando substituir" = por SITUAÇÃO do arquivo, não por momento no tempo** (ver §2).
> Este é um PLANO — nenhum código foi movido ainda.

---

## 1. Estrutura-alvo

```
app/odoo/
  constants/                         # gold-utils (DADOS) — permanece, EXPANDE
    locations.py                     #   + LOCAIS_INDISPONIVEL, + SC, + LOTES_MIGRACAO_POR_COMPANY
    operacoes_fiscais.py             #   + SC em CODIGO_PARA_COMPANY_ID/COMPANY_PARTNER_ID
    picking_types.py   (novo)        #   PICKING_TYPE_POR_DIRECAO (hoje hardcoded no pipeline)
  utils/                             # gold-utils (INFRA) — permanece (connection, etc.)
  estoque/                           # ← NOVO PACOTE
    __init__.py                      #   fachada: re-exporta gold-scripts p/ uso ergonômico
    _utils.py                        # gold-utils (FUNÇÕES de estoque): buscar_quant unificado,
                                     #   _registrar_op (audit), norm_lote/is_migracao, leitura RO
    scripts/                         # GOLD-SCRIPTS (operações versáteis)
      lot.py                         #   StockLotService
      quant.py                       #   StockQuantAdjustmentService
      transfer.py                    #   StockInternalTransferService
      picking.py                     #   StockPickingService
      indisponibilizacao.py          #   IndisponibilizacaoEstoqueService
      pre_etapa.py                   #   PreEtapaEstoqueService (planner)
      cancelar_mo.py                 #   GAP — criar
      cancelar_reserva.py            #   GAP — criar
    orchestrators/                   # GOLD-ORCHESTRATORS (fluxos compostos)
      inventario_pipeline.py         #   InventarioPipelineService (faturamento IC macro)
      pre_etapa_executor.py          #   (extrair de 09b)

# COMPATIBILIDADE (não quebrar 27 scripts + 7 testes ativos):
app/odoo/services/<nome>_service.py  # vira SHIM: `from app.odoo.estoque.scripts.X import *`

# DOCUMENTAÇÃO:
docs/inventario-2026-05/consolidacao/
  MAPA_ASSUNTOS.md       # o quê existe (camadas)
  PLANO_MIGRACAO.md      # este arquivo (como migrar)
  GUIA_CRIAR_ORQUESTRADOR.md   # como compor gold-scripts (a criar)
  manuais/<gold-script>.md     # 1 manual por gold-script

# scripts/inventario_2026_05/ → reorganiza (ver §6)
```

> `RecebimentoLfOdooService` fica em `app/recebimento/` (não move — é do domínio recebimento; o pipeline o chama).
> Transmissão SEFAZ idem (`app/recebimento/services/playwright_nfe_transmissao`).

---

## 2. Gatilhos de substituição (por SITUAÇÃO do arquivo)

| Estado | Condição (situação) | Ação |
|--------|---------------------|------|
| **AGORA-MOVER** | gold-script/util **maduro e testado**, sem dependência de fluxo em execução | mover p/ `estoque/` + criar shim no caminho antigo |
| **AGORA-EXPANDIR** | constante central que só precisa **ganhar entradas** (não move) | editar in-place (`constants/`) |
| **AO-CAPINAR** | assunto ainda não consolidado (gap ou lógica própria) | criar/refatorar o gold-script **quando aquele assunto entrar no roadmap** |
| **QUANDO-SUPERADO** | existe gold-script/orquestrador novo que **comprovadamente cobre** o script antigo (checklist §7) | arquivar o antigo em `_historico/` |
| **QUANDO-OP-FECHAR** | script ad-hoc **ainda executável** na operação ativa (inventário 2026-05 aberto) | manter intacto; arquivar quando P1-P13 fecharem |
| **JÁ-MORTO** | discovery/investigação **concluída**, sem reuso | arquivar agora em `_historico/` |

---

## 3. gold-utils

| Recurso atual | Destino | Ação | Gatilho |
|---------------|---------|------|---------|
| `constants/locations.py` (COMPANY_LOCATIONS) | mesmo | ✅ **FEITO (Onda 1)**: `LOCAIS_INDISPONIVEL` + `LOTES_MIGRACAO_POR_COMPANY` (30482/30856) + helpers + testes. SC=22 **NÃO** adicionado (decisão 2026-05-20) | — |
| `constants/operacoes_fiscais.py` | mesmo | SC **NÃO** adicionado a `CODIGO_PARA_COMPANY_ID`/`COMPANY_PARTNER_ID` (decisão 2026-05-20) | adiar até SC entrar em escopo |
| `PICKING_TYPE_POR_DIRECAO` (em `inventario_pipeline_service.py:59`) | `constants/picking_types.py` (novo) | extrair | AO-CAPINAR (faturamento) |
| `buscar_quant` (duplicado em quant + transfer) | `estoque/_utils.py` | unificar 1 cópia; quant/transfer passam a usar | AGORA-MOVER (junto com quant/transfer) |
| `_registrar_op` (audit; repetido em indispon + pipeline) | `estoque/_utils.py` | unificar | AO-CAPINAR (indispon/pipeline) |
| `monitor/_comum.py` (norm_lote, is_migracao, m2o_id, leitura RO) | `estoque/_utils.py` | mover funções; `monitor/` passa a importar | QUANDO-SUPERADO (após consolidar leitura R1-R3) |
| `app/odoo/utils/connection.py` | mesmo | não move | — |

---

## 4. gold-scripts (mover `app/odoo/services/` → `app/odoo/estoque/scripts/`)

| Atual | Destino | Camada | Ação | Gatilho |
|-------|---------|--------|------|---------|
| `stock_lot_service.py` | `scripts/lot.py` | C1 atômico | mover + shim | AGORA-MOVER |
| `stock_quant_adjustment_service.py` | `scripts/quant.py` | C1 atômico | mover + shim | AGORA-MOVER |
| `stock_internal_transfer_service.py` | `scripts/transfer.py` | C2 composto | mover + shim | AGORA-MOVER |
| `stock_picking_service.py` | `scripts/picking.py` | C2 composto | mover + shim | AGORA-MOVER (cuidado: acoplado robô CIEL IT) |
| `indisponibilizacao_estoque_service.py` | `scripts/indisponibilizacao.py` | C2 composto | mover + shim | AGORA-MOVER |
| `pre_etapa_estoque_service.py` | `scripts/pre_etapa.py` | C2 (planner) | mover + shim | AGORA-MOVER |
| — (gap A8) | `scripts/cancelar_mo.py` | C2 | CRIAR (extrair de `cancelar_mos.py`) | AO-CAPINAR (A8) |
| — (gap A9) | `scripts/cancelar_reserva.py` | C2 | CRIAR (extrair de `remover_reservas_saida.py`) | AO-CAPINAR (A9) |

Cada `mover + shim` acompanha: mover testes (`tests/odoo/services/` → manter ou `tests/odoo/estoque/`), criar manual em `manuais/`, atualizar imports internos.

---

## 5. gold-orchestrators

| Atual | Destino | Ação | Gatilho |
|-------|---------|------|---------|
| `inventario_pipeline_service.py` | `orchestrators/inventario_pipeline.py` | mover + shim | AGORA-MOVER (macro; ~20 gotchas — mover com testes) |
| `09b_executar_pre_etapa.py` (executor) | `orchestrators/pre_etapa_executor.py` | extrair lógica reusável | AO-CAPINAR (pré-etapa) |
| `RecebimentoLfOdooService` | fica em `app/recebimento/` | não move (outro domínio) | — |
| Scripts `09`, `fat_lf_04/05`, `teste_210030325` | exemplos no GUIA / orquestradores finos | refatorar sobre gold-scripts OU virar exemplo | AO-CAPINAR (faturamento) |

---

## 6. scripts/inventario_2026_05/ (~90) — destino por categoria

| Categoria | Exemplos | Ação | Gatilho |
|-----------|----------|------|---------|
| Família A clássicos | 11, 12, 13, 14_v2, criar_saldo | já cobertos por `ajuste_inventario.py` → arquivar | QUANDO-SUPERADO (confirmar cobertura) ou QUANDO-OP-FECHAR |
| Família B (lógica própria) | pasta17, zerar_negativos, limpar_quants, corrigir_reserved | refatorar como orquestradores finos sobre `quant.py` | AO-CAPINAR (cada) |
| Transferência ad-hoc | 10, 13_transf, 15, 15r, substituir_lote, padronizar | virar chamadas a `transfer.py`/`lot.py` (orquestrador ou ad-hoc via guia) | AO-CAPINAR (A2) |
| MIGRAÇÃO↔Indisponível | mover_migracao, ajuste_fb_cd_indisponivel, transferir_indisp | orquestrador sobre `quant.py` | AO-CAPINAR |
| Faturamento (G1) | 09, 09c, fat_lf_*, entrada_fb_piloto | sobre `orchestrators/inventario_pipeline` | AO-CAPINAR (faturamento) |
| Pré-etapa (G2) | 03b, 04b, 09b | sobre `pre_etapa` + executor | AO-CAPINAR |
| Cancelamentos | 14_cancelar_mos, cancelar_mos, cancelar_reservas_*, remover_reservas, 16_cancelar_pickings | sobre `cancelar_mo`/`cancelar_reserva` | AO-CAPINAR (A8/A9) |
| Leitura/diff/SOT | 01, 08, extrair_*, comparar_sot_*, diff_*, confronto_*, monitor/* | consolidar em gold-script(s) de leitura | AO-CAPINAR (R1-R3) |
| Investigação F0 | 00-00e, auditoria/investiga_*, dados_pickings_* | arquivar | JÁ-MORTO |
| Logs `auditoria/log_*.json` | — | manter (registro de execução) | — |

Pasta-alvo: `scripts/inventario_2026_05/{orquestradores/, _ad-hoc/, _historico/}` + os logs.

---

## 7. Estratégia de shims (preservar operação ativa)

Ao mover `app/odoo/services/stock_X_service.py` → `app/odoo/estoque/scripts/X.py`, o caminho antigo vira:

```python
# app/odoo/services/stock_X_service.py  (SHIM de compatibilidade)
"""Movido para app/odoo/estoque/scripts/X.py. Mantido para os scripts ativos do inventário."""
from app.odoo.estoque.scripts.X import *          # noqa: F401,F403
from app.odoo.estoque.scripts.X import StockXService  # re-export explícito
```

- Os 27 scripts + 7 testes continuam funcionando sem alteração.
- **Checklist QUANDO-SUPERADO** (para remover um shim ou arquivar um script antigo): (1) `grep` confirma 0 imports do caminho antigo fora do shim; (2) testes do gold-script passam; (3) se substitui um script da operação, dry-run do novo reproduz o resultado do antigo. Só então remover.

---

## 8. Ordem de execução (bottom-up — não inverter)

| # | Onda | Conteúdo | Pré-requisito |
|---|------|----------|---------------|
| 1 | **gold-utils dados** | expandir `constants/` (LOCAIS_INDISPONIVEL, SC, lotes, picking_types) | — |
| 2 | **esqueleto do pacote** | criar `app/odoo/estoque/{__init__,_utils}.py` + pastas | onda 1 |
| 3 | **mover gold-scripts atômicos** | lot, quant (+ shims + manuais) | onda 2 |
| 4 | **mover gold-scripts compostos** | transfer, picking, indispon, pre_etapa (+ shims + manuais + unificar buscar_quant) | onda 3 |
| 5 | **gaps** | criar cancelar_mo, cancelar_reserva | onda 4 |
| 6 | **gold-orchestrators** | mover pipeline, extrair pré-etapa executor | onda 4 |
| 7 | **GUIA + orquestradores finos** | `GUIA_CRIAR_ORQUESTRADOR.md`; refatorar scripts inventário | ondas 3-6 |
| 8 | **reorganizar scripts/** | mover ad-hoc/histórico; arquivar F0 e Família A superada | ondas 5-7 |

Cada onda: rodar `pytest tests/odoo/...` + spot-check de imports antes de avançar.

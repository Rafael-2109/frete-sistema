<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/08-execucoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# EXECUCAO — Cancelar 149 MOs antigas + transferir Pre-Prod -> FB/Estoque (2026-05-18 23:21-23:32)

**Origem do pedido**: Rafael — "Zere as qtds desses pickings nao 'done' e
transfira para Estoque os saldos" (2026-05-18 23:00).

**Decisao**: cancelar APENAS MOs `confirmed` antigas (>6 meses), preservando
`progress`/`to_close` e `confirmed` recentes (pos 2025-11-19).

## Contexto

Apos transferencia MIGRACAO -> lotes canonicos (script 13, 170/446 OK),
investigamos os 260 que falharam. Descoberta: nao sao pickings zumbis, sao
**reservas de Manufacturing Orders ativas** em sub-locations Pre-Producao
(Linha Balde/Vidro/Manual/Salmoura).

Total: **219 MOs ativas**, 284 stock.move.line reservando MIGRACAO em
Pre-Prod, 453.980 un reservadas.

## FASE A — Cancelar 149 MOs antigas

**Script**: `scripts/inventario_2026_05/14_cancelar_mos_antigas_fb.py`
**Log JSON**: `auditoria/log_14_cancelar_mos_20260518_232836.json`
**Execucao**: 2026-05-18 23:21-23:28 (~7 min)

| Metrica | Valor |
|---|---|
| MOs ativas no escopo | 219 |
| **MOs canceladas** | **149** (state=confirmed AND create<=2025-11-19) |
| MOs preservadas | 70 (63 confirmed recentes + 4 progress + 3 to_close) |
| Status `CANCELADA` | **149/149 (100%)** |
| Falhas | 0 |
| Move_lines liberadas | 199 |
| Tempo total | ~7 min (~3s por MO) |

Distribuicao por mes de criacao:
- 2024-10: 1 (mais antiga: `FB/OP/BALDE/00887`, 19 meses)
- 2024-11: 3
- 2025-03 a 2025-11: 145

Distribuicao por tipo:
- BALDE: 86, VIDRO: 35, MANUAL: 24, SALMOURA: 4

**Reservas liberadas:**
- Pre-Prod ANTES: 453.980 un reservadas
- Pre-Prod APOS: 147.788 un reservadas (-306.193 un liberadas)

## FASE B — Transferir saldo livre Pre-Prod -> FB/Estoque

**Script**: `scripts/inventario_2026_05/15_transferir_preprod_para_estoque_fb.py`
**Log JSON**: `auditoria/log_15_preprod_estoque_20260518_233231.json`
**Execucao**: 2026-05-18 23:30-23:32 (~2 min)

| Metrica | Valor |
|---|---|
| Quants Pre-Prod com livre>0 | 75 (8 ficaram 100% reservados pelas 70 MOs preservadas) |
| `EXECUTADO` | **74/75 (98.7%)** |
| `FALHA` | 1 |
| Quants destino criados em loc=8 | 45 |
| Quants destino atualizados em loc=8 | 30 (-1 falha) |
| **Soma transferida** | **424.053 un** |
| Tempo | ~2 min |

### Falha unica (quant 121581)

`[102030303] AZEITONA VERDE INTEIRA 20/24` em FB/Pre-Producao/Linha Vidro:
- `quantity = 735.913`
- `reserved_quantity = -4326.0` (**NEGATIVA — dados corrompidos**)
- `livre calculado = 5061.913`
- Odoo rejeitou: "stock negativo nao permitido"

**Acao manual sugerida**: Tratar essa anomalia no Odoo UI (corrigir reserva
negativa via inventory adjustment manual antes de re-tentar).

## Padrao de execucao (FASE B)

Para cada quant em Pre-Prod com livre>0:
1. **Reduzir origem**: `stock.quant.write({inventory_quantity: qty - livre})`
   + `action_apply_inventory` (gera stock.move Pre-Prod -> Virtual/Ajuste)
2. **Aumentar/criar destino**: `write/create` em loc=8 com mesmo
   `(product_id, lot_id, company_id)` + `action_apply_inventory`
   (gera stock.move Virtual/Ajuste -> FB/Estoque)

Lote `MIGRACAO` preservado em ambos. Gera **2 stock.moves por quant**
auditavel em Inventory > Reporting > Stock Moves filtrando location_id=8
+ data 2026-05-18 (origem `Physical Inventory`).

## Resultado consolidado

Saldo MIGRACAO em FB/Estoque (loc=8) **APOS** as duas fases deve estar
acrescido em ~424.053 un. Re-rodar script 13 (`13_transferencia_migracao_fb.py
--dry-run`) agora vai mostrar mais linhas passando — saldo agora disponivel
em loc=8 para transferir para os lotes canonicos da planilha original.

## Reversao

**FASE A** — MOs canceladas:
- Lista completa em `log_14_cancelar_mos_20260518_232836.json`
- Recriar via UI Odoo (botao "Duplicar" em cada MO) ou nova MO com mesmo BoM

**FASE B** — transferencias inventory adjustment:
- 74 `quant_origem_id` / `quant_destino_id` no log
- Reverter via nova inventory adjustment com sinal oposto

## Nao tocou

- `ajuste_estoque_inventario` local (regra emergenciais FB)
- 70 MOs preservadas (4 progress + 3 to_close + 63 confirmed recentes)
- 147k un ainda reservadas pelas MOs preservadas
- 1 quant corrompido (121581) — necessita tratamento manual

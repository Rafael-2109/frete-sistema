# T-L1 — Repoint das categorias da LF (Design A) ✅ APLICADO em PROD

**Data:** 2026-05-30 · **Script:** `scripts/e2e_l1_repoint_lf.py --execute` · **Reversão:** `--revert` (lê `scripts/e2e_l1_snapshot_baseline.json` — versionado no repo).

## O que foi feito
Repoint de **14 categorias** no contexto **LF (cmp 5)** — **Design A** (valoração→terceiros; input/output→transitórias físico-fiscais, p/ a NF de entrada fechar a transitória):

| Campo | Alvo aplicado (id / code) |
|---|---|
| `property_stock_valuation_account_id` | 26140 / **1150200001** MATERIAL EM TERCEIROS |
| `property_stock_account_input_categ_id` | 26845 / **1150100011** RECEB FÍSICO FISCAL |
| `property_stock_account_output_categ_id` | 26855 / **1150100012** FATUR FÍSICO FISCAL |

**Confirmado em PROD (2026-05-30)**: as 14 com val=1150200001 / in=1150100011 / out=1150100012.

## As 14 categorias (escopo / blast radius)
`57` AROMAS · `64` FRASCO · `69` TAMPA · `73` CAIXA · `75` ROTULO · `76` ETIQ · `77` FILME · `78` FITA · `90` CORANTE · `193` PA PET 1,01LT · `387` AÇÚCARES · `388` SAIS E CONSERVANTES · `393` SHOYU · `395` BATELADAS.

> Valores ORIGINAIS (antes) de cada categoria: `scripts/e2e_l1_snapshot_baseline.json` (val própria LF MP/EMB/PA/SEMI + in/out misturado entre `3201000002/003` resultado e `1150100011/012` transitória).

## ⚠️ Status de validação
- **Design A está APLICADO** mas **NÃO validado no fluxo de entrada-com-NF** ainda. O `T-PASSO0-TESTE` validou o mecanismo com **Design B** (input/output→1150200002) num **ajuste simples** (sem NF) — design diferente.
- **A validar no piloto (Etapa 2)**: após o par NF-entrada (ENTIN) + SVL do recebimento do 4870112, o **Δ de `1150100011` (LF) atribuível ao recebimento = 0** (Design A fecha a transitória). Se não fechar → reavaliar A vs B.

## Reversão
```
python docs/industrializacao-fb-lf/scripts/e2e_l1_repoint_lf.py --revert
```
(usa o baseline versionado; restaura as 14 categorias ao estado original).

## Impacto
Config **GLOBAL** das 14 categorias na LF — afeta TODO movimento LF dessas categorias enquanto aplicado (não só o piloto). Reversível.

# T-AJUSTE-ESTOQUE — Inventory adjustments para piloto 4870112 (10 cx)

**Status final**: ✅ done
**Executado em**: 2026-05-29
**Executor**: Claude via skill `ajustando-quant-odoo` com autorização Rafael (D19)
**Modo**: dry-run → execute (3 quants em paralelo)

## Objetivo

Liberar saldo em FB/Estoque dos 3 componentes que estavam 100% reservados, para permitir que o PO piloto FB→LF de 10 cx do 4870112 (D08 + D19) reserve sem furo.

## Antes

Conforme `testes/T13-prep-cadastros.md` CHK4, 3 componentes tinham todo o saldo de FB/Estoque reservado:

| Componente | Demanda (10 cx) | FB/Estoque LIVRE antes |
|---|---:|---:|
| 210030110 TAMPA PLASTICA | 120 un | **0** |
| 105000023 ANTIESPUMANTE AFE 1520 | 0.0256 kg | **0** |
| 105000039 AROMA SHOYU ST 2175 | 0.5845 kg | **0** |

## Comandos executados

```bash
# 3 ajustes em paralelo via skill ajustando-quant-odoo (cmd minimo)
python .claude/skills/ajustando-quant-odoo/scripts/ajustar_quant.py --quant-id 265491 --delta 120     --confirmar  # TAMPA
python .claude/skills/ajustando-quant-odoo/scripts/ajustar_quant.py --quant-id 265559 --delta 0.0256  --confirmar  # ANTIESPUMANTE
python .claude/skills/ajustando-quant-odoo/scripts/ajustar_quant.py --quant-id 264324 --delta 0.5845  --confirmar  # AROMA
```

## Resultado

| Componente | quant_id | lote | qty antes | delta | qty após | reservada | LIVRE após |
|---|---:|---:|---:|---:|---:|---:|---:|
| 210030110 TAMPA | 265491 | 13258 | 2016.0000 | +120 | **2136.0000** | 2016.0000 | **120.0000** ✅ |
| 105000023 ANTIESPUMANTE | 265559 | 13256 | 0.5989 | +0.0256 | **0.6245** | 0.5989 | **0.0256** ✅ |
| 105000039 AROMA | 264324 | 13240 | 27.8807 | +0.5845 | **28.4652** | 27.8807 | **0.5845** ✅ |

Todos os 3 com `status: EXECUTADO`, ajuste aplicado conforme planejado.

## Validação pós-execução

```
quant_id=265491 prod=210030110 lot=   13258 qty=  2136.0000 reserved=  2016.0000 livre=   120.0000
quant_id=265559 prod=105000023 lot=   13256 qty=     0.6245 reserved=     0.5989 livre=     0.0256
quant_id=264324 prod=105000039 lot=   13240 qty=    28.4652 reserved=    27.8807 livre=     0.5845
```

Livre = qty_apos - reserved_antes = exatamente o delta solicitado. `reserved_quantity` permaneceu inalterado.

## Por que ajuste positivo (não transferência de FB/Indisponivel)

- Volumes ínfimos (120 un, 26 g, 585 g) — overhead operacional de transferência não compensa
- Lote MIGRAÇÃO em FB/Indisponivel é estoque fantasma a baixar separadamente (memória local `estoque-fantasma-migracao-indisponivel.md` do projeto inventário 2026-05). Movê-lo para Estoque artificialmente desinfantasmaria registros que devem ser desindisponibilizados via plano D007 separado.
- Reusa lotes ativos (13258, 13256, 13240) — rastreabilidade preservada na NF de remessa T22 (FB→LF CFOP 5901).

## Pegada contábil

3 inventory adjustments positivos. Auditoria via `stock.move` automático criado pelo Odoo (categoria "Physical Inventory" — ver model `stock.move` com `inventory_id` populado). Volume total inserido:

| Produto | Delta | Valor estimado (unit. de R$ stub) |
|---|---:|---:|
| TAMPA PLASTICA | 120 un | trivial |
| ANTIESPUMANTE | 0.0256 kg | trivial |
| AROMA SHOYU | 0.5845 kg | trivial |

Para escopo "piloto" não exige aprovação financeira/contábil específica.

## Rollback

```bash
python .claude/skills/ajustando-quant-odoo/scripts/ajustar_quant.py --quant-id 265491 --delta -120     --confirmar
python .claude/skills/ajustando-quant-odoo/scripts/ajustar_quant.py --quant-id 265559 --delta -0.0256  --confirmar
python .claude/skills/ajustando-quant-odoo/scripts/ajustar_quant.py --quant-id 264324 --delta -0.5845  --confirmar
```

Reverte os 3 saldos ao estado original. Idempotente (cada um é write atômico). Não há reserva sobre os 120 un / 0.0256 kg / 0.5845 kg adicionados (`livre>0`), então o rollback não bate em movimento já feito.

## Destrava

T13/T21 (D19 fundidas) — Rafael pode agora abrir PO FB→LF para o partner LF (35), produto 4870112, qty=10 cx, sem furo de reserva.

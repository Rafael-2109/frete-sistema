# EXECUCAO — Ajuste FB + Transf CD → Indisponível (2026-05-20 02:52–03:51)

**Script**: `scripts/inventario_2026_05/ajuste_fb_cd_indisponivel.py`
**Decisão**: [D013](../00-decisoes/D013-ajuste-fb-cd-indisponivel-via-planilha-de-para.md)
**Planilhas**: `Downloads/AJUSTE FB.xlsx` (2259) + `Downloads/TRANSF CD.xlsx` (101) — enviadas pelo Rafael
**Logs JSON**: `scripts/inventario_2026_05/auditoria/log_ajuste_fb_cd_{CD,FB}_real_*.json`
**Exceções**: `Downloads/EXCECOES_AJUSTE_FB_CD_2026_05_20.xlsx` (108 linhas) + [PENDENCIAS P13](../PENDENCIAS.md)
**Confirmado**: Rafael (autonomia explícita — "siga até o final")

## Resumo

| Métrica | CD | FB |
|---|---|---|
| Linhas | 101 | 2259 |
| `EXECUTADO` | **98** (97,0%) | **2154** (95,4%) |
| Falhas | 0 | 0 |
| SAÍDA →Indisponivel | 68/71 | 2046/2146 |
| RETORNO →Estoque | 30/30 | 108/113 |
| Soma movida | 236.642,63 un | 29.090.563,44 un |
| Tempo | ~7 min | 56 min (3351 s) |

FB/Indisponivel (loc 31088) após execução: ~**158,4M un** (validado no Odoo; `free_qty == qty_available`).

## Como executou (inventory adjustment 2 passos)

1. `default_code` → `product.product.id` (active).
2. Resolve loc destino (fixa) e loc origem (fixa OU **wildcard** p/ `FB/Estoque`/`CD/Estoque`/`CD/*`).
3. Resolve lote origem: `MIGRAÇÃO`→variante com saldo na loc; vazio→`P-15/05`; literal→`buscar_por_nome` (`in`+`=like`).
4. Busca quant(s) origem; valida saldo livre (clamp se ≤ 0,001; parcial se maior; pula reservado).
5. Reduz origem (`inventory_quantity`) + `action_apply_inventory` por quant.
6. Resolve/cria lote destino (consolida `MIGRAÇÃO` onde já há saldo) e aumenta/cria o quant destino.

Lê **saldo fresco por linha** (sem snapshot global) → seguro contra consumo acumulado e concorrência.

## Validação

- **Dry-run** prévio (ambos arquivos): CD 98 OK / FB 2208 OK. Revisado antes de `--confirmar`.
- **Pós-exec Odoo** (amostra 6 CD + 6 FB): origens reduziram exatamente o esperado (12/12 OK);
  destinos `MIGRAÇÃO` em Indisponivel acumulam (vários produtos compartilham o lote — soma líquida correta).
- **Conservação**: FB/Indisponivel cresceu ~28,1M un ≈ soma SAÍDA FB executada (28,6M − retornos).

## Exceções (108 = 105 FB + 3 CD)

| Motivo | N | Tratamento |
|---|---|---|
| Saldo consumido por **industrialização concorrente** (rótulos P-15/05 → LA FAMIGLIA durante a execução) | 53 | Não movido p/ Indisponivel — saldo migrou p/ industrialização. Revisar com Rafael. |
| Linha sem lote sem `P-15/05` p/ o produto | 29 | PENDENTE — não adivinhar lote datado. |
| Lote apontado existe mas com **saldo zero** | 17 | Saldo do produto está em outro lote. |
| Código **não cadastrado** no Odoo (`103` PEPINO, `25` GLP, `45121452`) | 8 | Sem ação possível. |
| Duplicata na planilha (mesma origem já movida) | 1 | Correto não mover 2×. |

Nenhuma é falha de execução — o script foi defensivo (saldo fresco + clamp).

## Caso notável — cod 109000100 OLEO MISTO

Planilha pedia mover 40.397.270 kg (= **valor do monitor**, não saldo físico). Odoo:
`qty_available = 6.340.297 kg`, `reserved_quantity = 0` em todas companies, `lot_id=False` zerado,
6,28M já em FB/Indisponivel/MIGRAÇÃO. **Nada reservado**; `outgoing_qty = 2,2M` (industrialização em
trânsito). Sobram só 7.728 kg movíveis (lote 13194). Divergência **monitor × Odoo** registrada.

## Reversão

Cada `action_apply_inventory` é reversível por inventory adjustment de sinal oposto.
`quant_id` afetados nos logs JSON (`resultados[].reducoes_origem[].quant_id` e `quant_destino_id`).

## Não toca

- `ajuste_estoque_inventario` local (acerto direto no Odoo).
- Pickings ativos (saldo reservado é PULADO, nunca cancelado).

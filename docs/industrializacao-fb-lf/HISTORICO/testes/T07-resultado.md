# T07 — Criar picking_type LF/SAI/IND/RET

**Status final**: ✅ done (2026-05-29)
**Executor**: Claude (`setup_s0.py --task T07 --execute`) com autorização Rafael
**Modo**: dry-run → execute

## Comando

```bash
python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T07 --execute
```

## Output execute

```
[EXEC] T07 — Criar picking_type LF/SAI/IND/RET
[EXEC] create stock.picking.type: {
  'name': 'Retorno Industrialização (LF)',
  'sequence_code': 'LF/SAI/IND/RET',
  'code': 'outgoing',
  'company_id': 5,
  'warehouse_id': 4,
  'default_location_src_id': 31093,
  'default_location_dest_id': 26489,
  'return_picking_type_id': 64,
  'show_operations': True,
  'show_reserved': True,
  'use_create_lots': False,
  'use_existing_lots': True
}
[EXEC]   resultado: picking_type id=98
✅ Task T07 OK (result=98)
```

## Validação

| Campo | Valor |
|---|---|
| `id` | **98** |
| `name` | Retorno Industrialização (LF) |
| `sequence_code` | LF/SAI/IND/RET |
| `code` | outgoing |
| `company_id` | 5 (LA FAMIGLIA - LF) |
| `warehouse_id` | 4 (WH LF) |
| `default_location_src_id` | 31093 (LF/PA de Terceiros) |
| `default_location_dest_id` | 26489 (Estoque Virtual/Em Trânsito Industrialização) |
| `return_picking_type_id` | 64 (LF/RECEB/IND — reverso) |

## Significado operacional

Este picking_type será usado pelo CIEL IT quando a LF emitir a NF de retorno (CFOPs 5124+5902+5903) — T25.

Fluxo esperado:
- MO LF 20154 produz 10 cx do PA em **LF/PA de Terceiros (31093)** (location_dest_id forçado na MO).
- Quando NF retorno é emitida via CIEL IT, picking pt=98 LF/SAI/IND/RET é gerado automaticamente:
  - src = LF/PA de Terceiros (31093) — onde PA está fisicamente
  - dst = Em Trânsito Industrialização (26489)
- Após picking validado, DFe vai para FB.
- FB recebe DFe via pt=52 RECEB/FB/IND:
  - src = Em Trânsito Industrialização (26489)
  - dst = FB/Estoque (8)

O ciclo Em Trânsito Industrialização fecha entre pt=53 (saída FB), pt=64 (entrada LF), pt=98 (saída LF retorno) e pt=52 (entrada FB retorno).

## Mudança de plano A05 (relevante)

T07 originalmente esperava decisão A05 (PA → LF/Estoque ou LF/PA de Terceiros). A spec original (D11/T03) sempre intencionou LF/PA de Terceiros. D20 fechou A05 com LF/Estoque, mas Rafael relembrou a spec e a sessão re-corrigiu para **LF/PA de Terceiros (31093)**. T07 usa esse local como src.

## Constante para o projeto

```
PT_LF_SAI_IND_RET = 98
```

Adicionar em CONTEXTO.md (tabela "Picking Types").

## Idempotência

Re-executar com `--execute`: `picking_type 'LF/SAI/IND/RET' já existe (skip)`.

## Próximas dependências

- T25 — emitir NF retorno LF→FB via CIEL IT, deve usar pt=98 como saída.
- A NF retorno deve ter 3 CFOPs (5124 PA + 5902 componentes consumidos + 5903 sobras).

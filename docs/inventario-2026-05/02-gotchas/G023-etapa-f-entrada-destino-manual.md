<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G023 — ETAPA F: entrada manual destino para NFs FB→{LF,CD}

> **Papel:** G023 — ETAPA F: entrada manual destino para NFs FB→{LF,CD}.

## Indice

- [Problema](#problema)
- [Padrão validado (pre-existente, manual)](#padrão-validado-pre-existente-manual)
- [Implementação ETAPA F](#implementação-etapa-f)
- [Fluxo](#fluxo)
- [Execução validada (2026-05-18 13:58)](#execução-validada-2026-05-18-1358)
- [Gotcha de naming convention](#gotcha-de-naming-convention)
- [Gotcha de length (DB local)](#gotcha-de-length-db-local)
- [Ref](#ref)

**Status**: ✅ IMPLEMENTADO (sessão 3 tarde, 2026-05-18)
**Severidade**: HIGH (sem essa etapa, mercadoria fica "Em Trânsito" indefinidamente)
**Padrão derivado de**: pickings 317306 (NF 608629) e 317316 (NF 627348)

## Problema

NFs emitidas pela FB com sentido FB→{LF,CD} (industrialização, dev,
transferência) saem da FB/Estoque, atravessam location virtual
"Em Trânsito Industrialização" (26489), mas **nunca chegam ao destino
automaticamente**. Robô CIEL IT NÃO cria entrada destino — não há DFe
no sentido reverso para operações inter-company internas.

Sintoma: após F5e_SEFAZ_OK, mercadoria fica parada em `Em Trânsito
Industrialização` (26489). LF/Estoque (42) não recebe.

## Padrão validado (pre-existente, manual)

Picking 317306 (NF 608629 ALHO GRANULADO) e 317316 (NF 627348 PEPINO).
Ambos criados manualmente nas sessões 1 e 2 com:

- `picking_type_id` = 19 (LF: Recebimento)
- `location_id` = 26489 (Em Trânsito Industrialização)
- `location_dest_id` = 42 (LF/Estoque)
- `company_id` = 5 (LF)
- `origin` = `INV-INVENTARIO_2026_05-ENTRADA-LF-NF{invoice_id}`
- Move com `company_id=5` forçado via `odoo.write('stock.move',...)`
  (G006: XML-RPC não herda company_id do picking)
- `lot_name` = `INV-{cod_produto}-{YYYYMMDD}` se ajuste tem
  `lote_destino` vazio ou `MIGRAÇÃO`

## Implementação ETAPA F

`scripts/inventario_2026_05/09_executar_onda1_bulk.py`:

- `etapa_f_entrada_destino_manual()` — orquestra
- `_f_criar_entrada_destino_para_invoice()` — cria 1 picking por invoice
- Idempotência: `search_read stock.picking` por `origin`. Se done, skip
  e promove `fase_pipeline = 'F5f_ENTRADA_OK'`. Se outro state, mantém
  para investigação manual.
- Suporta apenas `INDUSTRIALIZACAO_FB_LF` (validado).
  `DEV_FB_LF` e `TRANSFERIR_FB_CD` precisam:
  - Adicionar à `ACOES_ENTRADA_DESTINO_MANUAL`
  - Completar `PICKING_TYPE_ENTRADA_DESTINO_MANUAL` para company=4 (CD)
  - Validar mapeamento `location_origem` se for diferente de 26489

## Fluxo

```
F5e_SEFAZ_OK (NF emitida + autorizada)
        |
        v
ETAPA F (--apenas-etapa=F)
        |
        +-- ja existe picking done com origin? --> SKIP + F5f_ENTRADA_OK
        |
        +-- nao existe:
              1. resolver product_id de cada cod
              2. agg(pid, lote_dest) -> qty (lote_dest = INV-{cod}-YYYYMMDD se vazio)
              3. odoo.create('stock.picking', ...)
              4. odoo.write('stock.move', [moves], {'company_id': dest})  # G006
              5. action_confirm + action_assign
              6. write quantity + lot_name nos move_lines (G011)
              7. button_validate
              8. assert state == 'done' (G019/G020 pattern)
              9. fase_pipeline = 'F5f_ENTRADA_OK' nos ajustes
```

## Execução validada (2026-05-18 13:58)

```
ETAPA F: OK=1 SKIP=2 FALHA=0

invoice 627348: picking 317316 LF/IN/01734 ja done (skip)
invoice 608629: picking 317306 LF/IN/01733 ja done (skip)
invoice 628907: picking 317410 LF/IN/01735 criado state=done
```

Picking 317410 criado para invoice 628907 (NF 94471 RPI/2026/00203):
- 5 produtos: GOMA GUAR, CORANTE VERMELHO, AÇÚCAR MASCAVO, ÁCIDO
  FOSFÓRICO, AROMA ERVAS FINAS
- Total: ~106 kg/un transferidos de Em Trânsito Industr → LF/Estoque

## Gotcha de naming convention

Origin usa `invoice_id` (account.move.id), NÃO `l10n_br_numero_nf`:
- Pickings antigos: `INV-INVENTARIO_2026_05-ENTRADA-LF-NF608629`
  (608629 = invoice_id, NOT numero_nf=94469)
- Razão: `invoice_id` é globalmente único; `numero_nf` pode colidir
  entre companies (FB e LF podem ter mesmas séries/números).

## Gotcha de length (DB local)

Coluna `ajuste_estoque_inventario.fase_pipeline` é `character varying(20)`.
Nome inicial proposto `F5f_ENTRADA_DESTINO_OK` (22 chars) falhou. Usado
`F5f_ENTRADA_OK` (14 chars).

Se adicionar fases futuras, manter <=20 chars OU migrar coluna.

## Ref

- `scripts/inventario_2026_05/09_executar_onda1_bulk.py`:
  - `ACOES_ENTRADA_DESTINO_MANUAL` (linha ~115)
  - `etapa_f_entrada_destino_manual` (linha ~1282)
  - `_f_criar_entrada_destino_para_invoice` (linha ~1372)
- `docs/inventario-2026-05/EXECUCAO_ENTRADA_LF_NF627348_2026_05_18.md`
  (padrão manual de referência)
- `docs/inventario-2026-05/02-gotchas/G006-picking-inter-company-location-virtual.md`
  (gotcha company_id no move)

# G041 — `picking_type.reservation_method='manual'` faz `action_assign` reservar ZERO → faturamento multi-lote falha não-deterministicamente

**Severidade**: HIGH (bloqueia `button_validate` da SAÍDA inter-company → trava faturamento SEFAZ de produto com 2+ lotes na origem)
**Status**: 🟡 WORKAROUND validado em PROD (cirurgia: criar `stock.move.line` com `lot_id`). **Fix de código PENDENTE — needs-canary** (não implementar "no escuro" no caminho SEFAZ).
**Escopo**: orchestrator de faturamento (`faturamento_pipeline` ETAPA B) + Skill 5 `validar_picking_inter_company`/`preencher_qty_done`/`consolidar_move_lines`. Afeta `picking_type` com `reservation_method='manual'` — confirmado no **pt 97 (LF Expedição Industrialização Retorno)**.

## Sintoma

Faturamento LF→FB (`DEV_LF_FB`) de um produto que tem **2+ lotes com saldo** na `LF/Estoque`: a ETAPA B falha em `button_validate` (F5b) com:

```
<Fault 2: 'Nao e possivel validar uma transferencia se nao houver
quantidades reservadas. Para forcar a transferencia, codifique as
quantidades.'>
```

A `stock.move.line` fica corrompida: `lot_id=<lote ERRADO>` + `lot_name="<lote esperado>"` (conflito) + `quantity=0.0`.

**Não-determinístico entre produtos do mesmo lote de faturamento**: no inventário 2026-05, o BALDE `210030507` (lote 10426) passou direto pelo pipeline, enquanto a TAMPA `210030607` (lote 291025) falhou — diferença apenas em qual lote o removal strategy tocou primeiro vs o `lote_origem` do ajuste.

Incidente real: 2026-05-29, baldes `210030607`/`210030507` do Bloco C. A TAMPA não faturava pelo pipeline; o BALDE sim.

## Causa raiz

O `picking_type 97` (LF Exp Ind Retorno) tem **`reservation_method='manual'`**. Com reserva manual, `action_assign` **NÃO auto-reserva** — não cria `move_line` reservada (ou cria com `quantity=0`). Verificado AO VIVO: após deletar a ML e rodar `action_assign` limpo, **o Odoo reservou ZERO, nenhuma ML criada, move continua `confirmed` qty=0**.

O fluxo legacy `validar_picking_inter_company` depende de `action_assign` ter reservado:
1. `confirmar_e_reservar` → `action_assign` (manual = reserva 0).
2. `preencher_qty_done` → seta `lot_name` + `qty_done` na ML que houver (mas a ML está no lote errado e com `quantity=0`).
3. `consolidar_move_lines` (G023) → tenta corrigir, mas opera sobre MLs existentes.
4. `button_validate` → falha: sem `quantity` reservada real no quant.

Por que o BALDE passou: o removal strategy do `action_assign(manual)` tocou o lote `10426` (= `lote_origem`), a ML ficou consistente e o `preencher_qty_done` + `validate` funcionaram. Para a TAMPA, tocou `C/DEFIEITO` (≠ `291025`) → ML em conflito → falha.

## Workaround VALIDADO em PROD (cirurgia)

Criar a `stock.move.line` **explicitamente** com `lot_id` correto (não depender do `action_assign`):

```python
# picking limpo (confirmed, sem ML adequada):
odoo.create('stock.move.line', {
    'move_id': <move do produto no picking>,
    'picking_id': <picking_id>,
    'product_id': <pid>,
    'lot_id': <id do lote CORRETO>,        # ex.: 58700 = 291025 (NAO C/DEFIEITO)
    'location_id': 42,                     # LF/Estoque
    'location_dest_id': 5,                 # transito inter-company
    'qty_done': <qty>,                     # ex.: 4824
    'product_uom_id': <uom>,
})
# -> ML fica state=assigned, quantity=<qty>, lote correto. button_validate OK.
```

**CRIAR a ML (com `lot_id`) reserva**; **ATUALIZAR uma ML existente (setar `quantity` via write) NÃO reserva** em `reservation_method='manual'`. Essa é a distinção crucial. Confirmado: picking 322269, ML manual com `lot_id=58700` → faturou (NF 726719 SARET/2026/00013 cstat=100, lote 291025).

## Tentativa de fix DESCARTADA (revertida)

Houve uma tentativa (commit `0770707d`, **REVERTIDO**) de fazer `consolidar_move_lines` (G023) **redirecionar** a ML órfã de maior qty para o lote esperado. **Não resolve este caso** porque:
- Assume que `action_assign` reservou no lote errado **com `quantity>0`** (cenário `reservation_method='auto'`). Com manual, `quantity=0` → não há reserva para redirecionar.
- Redirecionar = ATUALIZAR ML existente → **não cria reserva real** no quant. `button_validate` continua falhando.

Lição: o fix correto é **CRIAR** a ML, não redirecionar uma existente. E não se deve commitar fix no caminho SEFAZ sem canary em PROD (o redirect passava no pytest mock mas não na realidade do Odoo).

## Fix de código recomendado (needs-canary)

`validar_picking_inter_company` deve detectar `reservation_method='manual'` (ler do `picking_type`) e, quando faltar ML reservada no lote esperado, **criar a ML explicitamente** com `lot_id` resolvido (mecânica da cirurgia acima), em vez de depender do `action_assign`. Alternativa: migrar o caminho legacy para usar `preencher_lotes_picking` (Skill 5 v19+, que cria MLs) — porém esse átomo hoje exige ≥1 ML existente para referenciar `move_id`; precisaria estender para o caso "sem ML".

Implementação deve ser **gated por `reservation_method='manual'`** (não alterar o caminho `auto`, que é a maioria) e validada com **canary REAL em PROD** antes de confiar (1 faturamento multi-lote manual).

## Evidência

- Baldes 2026-05-29: `210030607` via cirurgia (picking 322269); `210030507` via pipeline direto (picking 322273). Ambos cstat=100 nos lotes corretos, FB líquido zero.
- Relatório: `/tmp/subagent-findings/gestor-estoque-baldes-2026-05-29.md`.

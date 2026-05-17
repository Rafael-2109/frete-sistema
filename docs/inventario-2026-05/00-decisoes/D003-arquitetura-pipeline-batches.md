# D003 — Arquitetura pipeline em batches (G004)

**Data:** 2026-05-17
**Resolve:** G004 (padrao NACOM eh picking + robo CIEL IT + Playwright)
**Decisao do usuario:** "Reescrever spec/plano para pipeline ja, sem medir robo antes"

## Decisão

Substituir o desenho original (1 NF por chamada via `account_move_intercompany_service.executar()`) por **pipeline em batches** processando coleções de ajustes em 5 etapas paralelas/serializadas conforme a natureza de cada etapa.

## Service renomeado/redesenhado

`account_move_intercompany_service` → `inventario_pipeline_service` (ou nome a definir)

5 métodos batch, cada um opera sobre **lista de ajustes/pickings/invoices**:

| Método | Paralelizavel? | Tempo estimado N=50 |
|---|---|---|
| `f5a_criar_pickings(ajustes)` | ✅ sim (semaphore 5-10) | ~5 min |
| `f5b_validar_pickings(picking_ids)` | ✅ sim | ~10 min |
| `f5c_liberar_faturamento(picking_ids)` | ✅ sim | ~1 min |
| `f5d_aguardar_invoices(picking_ids, timeout)` | ⚠️ depende robô | 30 min - 25h |
| `f5e_transmitir_sefaz(invoice_ids)` | ❌ serial (Playwright) | ~50 min |

## Mudancas no spec/plano

### Spec §6.2 — serviços

Substituir entrada `account_move_intercompany_service.py` por:

```
inventario_pipeline_service.py
    # Orquestrador pipeline-batch para inventario (e operacoes futuras).
    # 5 metodos batch, paralelismo controlado por semaphore.
    # Usa stock_picking_service + Playwright + constants.
```

`stock_picking_service.py` ganha 2 metodos novos:
- `liberar_faturamento(picking_id)` → `action_liberar_faturamento` no Odoo
- `aguardar_invoice_do_robo(picking_id, timeout=1800)` → fire-and-poll em `account.move` com `ref=picking_name`

`indisponibilizacao_estoque_service.py` — mantem
`stock_lot_service.py` — mantem

### Spec §7 — modelo de dados

Adicionar 1 campo em `ajuste_estoque_inventario`:

```
fase_pipeline VARCHAR(20) NULL
  -- Valores: F5a_PICKING_CRIADO, F5b_VALIDADO, F5c_LIBERADO,
  --          F5d_INVOICE_GERADA, F5e_SEFAZ_OK, FINALIZADO
```

Tambem em `operacao_odoo_auditoria`, adicionar `pipeline_etapa` (varchar) para rastreabilidade.

### Spec §8 — pipeline operacional

§8.1 — fases:
- F0..F4 — mantem
- F5 — reescrita em 5 etapas batch:
  - **F5a** Criar pickings em batch (XML-RPC paralelo, semaphore=5)
  - **F5b** Validar pickings (action_confirm + assign + lotes + button_validate, paralelo)
  - **F5c** Liberar faturamento em batch (action_liberar_faturamento, paralelo)
  - **F5d** Aguardar robô CIEL IT criar invoices (1 polling longo sobre todos)
  - **F5e** Transmitir SEFAZ via Playwright (serial, 1 browser)
- F6 — reconciliacao (mantem)

§8.2 — ondas: cada onda (O1, O2, O3, O4) agrupa por tipo, e DENTRO da onda usa pipeline F5a-F5e.

### Plano — Fase 4 reescrita

Em vez de 3 sub-tasks de `AccountMoveIntercompanyService.preview/executar/cancelar`, ficam **5 sub-tasks** de `InventarioPipelineService.f5a..f5e`. Detalhamento de cada metodo + paralelismo + idempotencia.

### Plano — Fase 3 estendida

`StockPickingService` ganha 2 sub-tasks novas:
- Task 3.3 — `liberar_faturamento` (action_liberar_faturamento)
- Task 3.4 — `aguardar_invoice_do_robo` (fire-and-poll batch-friendly)

## Riscos pendentes

- F5d (robô CIEL IT) pode ser serial → 25h para 50 NFs. Mitigacao:
  - Reduzir N por onda (batch de 10-20)
  - Implementar reentrancia (retomar de onde parou se cair)
  - Ou aceitar tempo longo para uma onda crítica

- Playwright SEFAZ em paralelo (multi-browser) — não previsto agora, mas factível se necessário (multi-worker RQ com queue própria)

## Itens em aberto (G005, G006 a investigar)

- [ ] G005: `action_liberar_faturamento` existe em outros picking types ou apenas em "Expedicao Entre Filiais"?
- [ ] G006: como o robô CIEL IT decide vincular invoice a picking (campo `ref` ou outro)?

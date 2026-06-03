# CHECKPOINT — Fim Sessao 3 LF (2026-05-18 tarde+noite)

**Sessao Claude Code 3**: 2026-05-18 ~13:00 → 17:30 UTC
**Foco**: bulk LF (batches 50/30/15 prods) + fixes over-reservation
**Status global**: 4 pickings PERDA + 1 INDUSTR processados completos
(SEFAZ + entrada FB). 5 gotchas adicionais documentados (G021-G023 da
manha + G028-G030 da tarde).

> Substitui `CHECKPOINT_2026_05_18_LF_FIM_SESSAO2.md`. Proxima sessao:
> continuar LF restante com fixes G023/G028 ativos.

---

## 1. Resumo executivo

### Conquistas pos-sessao 2

| Antes (sessao 2 fim) | Fim hoje (sessao 3) | Δ |
|----------------------|---------------------|---|
| 34 EXECUTADO | **114 EXECUTADO** | **+80** ✅ |
| 6 PERDA F5e_SEFAZ_OK | **81 PERDA F5e_SEFAZ_OK** | +75 |
| 0 F5f_ENTRADA_OK | **9 INDUSTR F5f_ENTRADA_OK** | +9 |

### Pickings processados nesta sessao

| Picking | NF | Tipo | Invoice LF | Invoice FB | RecLf |
|---------|-----|------|------------|-----------|-------|
| 317407 FB/SAI/IND/01560 | RPI/2026/00203 | INDUSTR | 628907 (auto) | n/a (entrada manual via F) | n/a |
| 317420 LF/LF/SAI/RNA/00021 | RETNA/2026/00032 | PERDA | 629055 | 629191 | 11 ✅ |
| 317460 LF/LF/SAI/RNA/00035 | RETNA/2026/00036 | PERDA | 629364 | 629567 (manual post) | 14 ✅ |
| 317461 LF/LF/SAI/RNA/00036 | RETNA/2026/00037 | PERDA | 629376 | 629703 | 16 ✅ |
| 317416 LF/LF/SAI/RNA/00017 | RETNA/2026/00038 | PERDA | 629363 | 629726 | 17 ✅ |
| 317410 LF/IN/01735 | n/a | ENTRADA LF (do 317407) | n/a | n/a | n/a |

---

## 2. Gotchas descobertos nesta sessao

| # | Severidade | Tema | Status |
|---|------------|------|--------|
| G021 | HIGH | ETAPA A reporta resultado prematuro (race A↔B) | 🔴 ABERTO (mitigado via sleep 90s) |
| G022 | MEDIUM | ETAPA B sem re-validar saldo (mitigado por G028) | 🟡 ABERTO |
| G023 | HIGH | ETAPA F: entrada manual destino FB→LF | ✅ IMPLEMENTADO |
| **G028** | **CRITICAL** | **Over-reservation pos-renomeacao lote** | ✅ **IMPLEMENTADO** |
| G029 | HIGH | payment_provider em recovery manual | 🟡 WORKAROUND |
| G030 | MEDIUM | Pipeline RecLf trava em Fase 4 (raro) | 📝 DOCUMENTADO |

### G028 — fix principal da sessao

**Causa**: `action_apply_inventory` da ETAPA A renomeia lotes mas DEIXA
reservas órfãs no lote velho. `action_assign` da ETAPA B reserva em
AMBOS (velho + novo) — over-reservation 2x até 459x.

**Fix**: `StockPickingService.consolidar_move_lines(picking_id, linhas_esperadas)`
chamado em `validar()` ANTES de `button_validate`. Usa lote/qty EXATOS
dos `AjusteEstoqueInventario.lote_origem`+`qtd_ajuste` para zerar
move_lines em lotes não esperados.

**Resultado**: taxa de sucesso PERDA passou de 17% → 67% (3.9x).

### G023 ETAPA F — entrada destino auto

Padrão herdado de pickings manuais 317306/317316. Detecta NFs sentido
FB→{LF,CD} SEFAZ-OK e cria picking interno Em Trânsito (26489) →
LF/Estoque (42) automaticamente. Idempotente via origin
`INV-INVENTARIO_2026_05-ENTRADA-LF-NF<invoice_id>`.

---

## 3. Modificacoes de codigo

### `app/odoo/services/stock_picking_service.py`
- **+ `consolidar_move_lines(picking_id, linhas_esperadas)`** (linha 142-265)
- **`validar(picking_id, linhas_esperadas)`** — assinatura ampliada, chama
  consolidar antes de button_validate (linha 425-451)

### `app/odoo/services/inventario_pipeline_service.py`
- `f5b_validar_pickings` — passa `linhas_esperadas=linhas` para
  `validar()` (linha 727)

### `scripts/inventario_2026_05/09_executar_onda1_bulk.py`
- **+ `_commit_resilient()`** helper (linha 158-218) — SSL retry + dispose
- **+ ETAPA F** `etapa_f_entrada_destino_manual()` + `_f_criar_entrada_destino_para_invoice()`
- **Sleep 5s** entre pickings em `etapa_b_pickings` (linha 1019-1024)
- **`db.engine.dispose()`** antes/depois ETAPAS C e D (linha 1716+)
- **G023 refactor**: geração de `linhas` baseada em `aj.lote_origem` +
  `aj.qtd_ajuste` (1:1 ajuste→linha) com fallback FIFO para ajustes sem
  `lote_origem` (linha 919-985)
- **ETAPAS_VALIDAS** = `('A', 'B', 'C', 'D', 'E', 'F')`

---

## 4. Estado LF apos sessao 3

```
EXECUTADO 114 ajustes:
  - 81 PERDA_LF_FB F5e_SEFAZ_OK (4 antigos + 7 do 317420 + 33 do 317460 + 26 do 317461 + 11 do 317416)
  - 9 INDUSTRIALIZACAO_FB_LF F5f_ENTRADA_OK
  - 24 RENOMEAR_LOTE TRANSF_OK

PROPOSTO 1617 ajustes:
  - 703 PERDA_LF_FB (sem fase)
  - 148 DEV_LF_FB (sem fase, nao testado)
  - 126 INDUSTRIALIZACAO_FB_LF (sem fase)
  - 382 RENOMEAR_LOTE (sem fase)
  - 175 RENOMEAR_LOTE TRANSF_FALHA (drift Cat 2)
  - 49 RENOMEAR_LOTE TRANSF_OK (nao promovidos)
  - 21 INDUSTRIALIZACAO_FB_LF F5c_LIBERADO (do 317346 pendente robo CIEL IT)
  - 13 INDISPONIBILIZAR_LOTE (onda 3, fora escopo)
```

## 5. Bloqueio residual

- **317346 FB/SAI/IND/01559** done desde 14:19 (sessao 2 manha) sem
  invoice criada pelo robô CIEL IT. **>24h sem invoice** — operacional
  precisa decidir se cancela ou aguarda mais.

---

## 6. Roadmap proxima sessao

### Priority 0 — Decidir 317346
- Aguardar mais OU cancelar via `stock.return.picking` + reset ajustes
  (replicar padrao 317402-406 cancelados em sessao 3)

### Priority 1 — Continuar LF PERDA restante
- 703 PERDA_LF_FB sem fase
- 148 DEV_LF_FB sem fase
- 126 INDUSTRIALIZACAO_FB_LF sem fase

**Estrategia recomendada** (com fixes ativos):
- Batches de 15-30 prods, max-picking=5
- Pausa 90s entre A e B (G021 mitigation)
- Sleep 5s entre pickings B (codigo)
- G028 fix vai consolidar move_lines automaticamente

### Priority 2 — Drift Cat 2 (RENOMEAR_LOTE TRANSF_FALHA)
- 175 ajustes
- Causas conhecidas: reservas concorrentes, lotes vencidos sem saldo
- Estrategia: aguardar separações fluirem OU aceitar como rabo permanente

### Priority 3 — Fix G029 code-level
- Adicionar `_garantir_payment_provider` no início de `f5e_transmitir_sefaz`
  (idempotente, ~50ms extra) para resolver recovery manual

### Priority 4 — Onda 2 (TRANSFERIR_CD_FB / TRANSFERIR_FB_CD)
- Rafael ja iniciou batch 09c em paralelo na sessao 3 (FB/CD)
- Acompanhar resultado

---

## 7. Comando rapido para retomar

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# Validar baseline (134 tests passing)
pytest tests/odoo/ -p no:randomly -q

# Verificar estado atual LF
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT status, fase_pipeline, acao_decidida, COUNT(*) AS qtd
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=5
GROUP BY status, fase_pipeline, acao_decidida
ORDER BY status, fase_pipeline NULLS FIRST, acao_decidida;
"

# Verificar 317346 (invoice apareceu?)
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    p = odoo.read('stock.picking', [317346], ['name', 'state', 'date_done'])
    print(p)
    invs = odoo.search_read('account.move',
        [['ref', 'ilike', 'FB/SAI/IND/01559'], ['move_type', '=', 'out_invoice']],
        ['id', 'name', 'state', 'l10n_br_situacao_nf'])
    print(f'Invoices: {invs}')
"

# Continuar LF (batches com fixes ativos)
CODS=<gerar 15 prods novos sem 317346>
# PASSO 1: ETAPA A só
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --max-produtos-picking=5 \
    --filtro-cod-produto="$CODS" --ate-etapa=A \
    --confirmar --usuario=rafael
sleep 90  # G021 mitigation
# PASSO 2: B-F (G028 fix ativo)
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --max-produtos-picking=5 \
    --filtro-cod-produto="$CODS" \
    --confirmar --confirmar-sefaz --usuario=rafael \
    --validacao-fiscal=strict --auto-fix-weight=0.001
```

---

## 8. Referencias

- `02-gotchas/G021-etapa-a-reporta-prematuro.md`
- `02-gotchas/G022-etapa-b-sem-revalidar-saldo.md`
- `02-gotchas/G023-etapa-f-entrada-destino-manual.md`
- **`02-gotchas/G028-over-reservation-action-assign-pos-renomeacao.md`** ← fix principal
- `02-gotchas/G029-payment-provider-recovery-manual.md`
- `02-gotchas/G030-pipeline-reclf-trava-em-fase-4.md`
- `99-historia/CHECKPOINT_2026_05_18_LF_FIM_SESSAO2.md` (anterior)

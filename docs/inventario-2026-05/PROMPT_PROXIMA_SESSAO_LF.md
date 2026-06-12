<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Prompt — Próxima sessão LF (continuação inventário 2026-05)

**Foco exclusivo**: continuar ajuste de estoque da LF (company_id=5).
Demais empresas (FB, CD, SC) fora de escopo desta sessão.

**Pre-leitura obrigatória** (nesta ordem):
1. `docs/inventario-2026-05/99-historia/CHECKPOINT_2026_05_18_LF_FIM_SESSAO3.md` (estado mais recente)
2. `docs/inventario-2026-05/PICKINGS_PENDENTES_INVOICE.md` (317346 ainda pendente)
3. `docs/inventario-2026-05/02-gotchas/G028-over-reservation-action-assign-pos-renomeacao.md` (fix principal)
4. `docs/inventario-2026-05/02-gotchas/G023-etapa-f-entrada-destino-manual.md`
5. `docs/inventario-2026-05/02-gotchas/G029-payment-provider-recovery-manual.md`

---

## Validar baseline

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
pytest tests/odoo/ -p no:randomly -q
# Esperado: 134 passing
```

## Estado atual LF (fim sessao 3, 2026-05-18 noite)

- **114 ajustes EXECUTADO** (+80 vs sessao 2)
  - 81 PERDA_LF_FB F5e_SEFAZ_OK
  - 9 INDUSTRIALIZACAO_FB_LF F5f_ENTRADA_OK
  - 24 RENOMEAR_LOTE TRANSF_OK
- **1617 ajustes PROPOSTO** (LF restante)
  - 703 PERDA_LF_FB sem fase
  - 148 DEV_LF_FB sem fase (não testado)
  - 126 INDUSTRIALIZACAO_FB_LF sem fase
  - 382 RENOMEAR_LOTE sem fase
  - 175 RENOMEAR_LOTE TRANSF_FALHA (drift Cat 2)
  - 49 RENOMEAR_LOTE TRANSF_OK (não promovidos)
  - 21 INDUSTRIALIZACAO_FB_LF F5c_LIBERADO (do 317346)
  - 13 INDISPONIBILIZAR_LOTE (onda 3, fora escopo)
- **1 picking pendente invoice**: 317346 INDUSTR (>24h sem invoice CIEL IT)

## Tarefa 1 — Decidir sobre 317346 INDUSTR

Robô CIEL IT está há >24h sem criar invoice fiscal para o picking
317346 FB/SAI/IND/01559. Operacional precisa decidir:

### Opção A — Aguardar mais
Verificar de hora em hora se invoice apareceu:
```python
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    invs = odoo.search_read('account.move',
        [['ref', 'ilike', 'FB/SAI/IND/01559'],
         ['move_type', '=', 'out_invoice']],
        ['id', 'name', 'state', 'l10n_br_situacao_nf'])
    print(f'Invoices: {invs}')
```

### Opção B — Cancelar e refazer
1. Criar picking devolução (`stock.return.picking` wizard)
2. Reset 21 ajustes para PROPOSTO sem fase/picking_id
3. Re-rodar batch incluindo esses produtos

## Tarefa 2 — Continuar bulk LF restante

**Fixes ativos** (validados em sessao 3):
- **G028 `consolidar_move_lines`**: ANTES de button_validate, força
  lote/qty exatos baseado em `aj.lote_origem` + `aj.qtd_ajuste`
- **G023 ETAPA F**: entrada destino automática (FB→LF SEFAZ-OK)
- **Sleep 5s** entre pickings em ETAPA B
- **SSL protection** (`_commit_resilient` + `db.engine.dispose()`)
- **Resolver lote sem origem** automaticamente via FIFO de quants

**Estratégia recomendada para esta sessão**:

```bash
# 1. Gerar lista de 15-30 prods novos (excluindo 317346 e EXECUTADO)
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -tA -c "
WITH onda1 AS (
  SELECT DISTINCT cod_produto FROM ajuste_estoque_inventario
  WHERE ciclo='INVENTARIO_2026_05' AND company_id=5
    AND status IN ('PROPOSTO', 'APROVADO')
    AND acao_decidida IN ('PERDA_LF_FB','INDUSTRIALIZACAO_FB_LF',
                          'DEV_LF_FB','DEV_FB_LF','DEV_CD_LF','DEV_LF_CD',
                          'RENOMEAR_LOTE','TRANSFERIR_LOTE')
), excluir AS (
  SELECT DISTINCT cod_produto FROM ajuste_estoque_inventario
  WHERE picking_id_odoo=317346
     OR fase_pipeline IN ('F5f_ENTRADA_OK','F5e_SEFAZ_OK')
)
SELECT STRING_AGG(cod_produto, ',') FROM (
  SELECT o.cod_produto FROM onda1 o
  LEFT JOIN excluir e ON e.cod_produto=o.cod_produto
  WHERE e.cod_produto IS NULL
  ORDER BY o.cod_produto LIMIT 30
) sub;
" > /tmp/bulk_lf_batch_codes.txt

CODS=$(cat /tmp/bulk_lf_batch_codes.txt)

# 2. PASSO 1: ETAPA A só (mitiga INV-021)
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --max-produtos-picking=5 \
    --filtro-cod-produto="$CODS" \
    --ate-etapa=A --confirmar --usuario=rafael

# 3. SLEEP 90s (INV-021 mitigation)
sleep 90

# 4. PASSO 2: B-F (G028 fix ativo)
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --max-produtos-picking=5 \
    --filtro-cod-produto="$CODS" \
    --confirmar --confirmar-sefaz --usuario=rafael \
    --validacao-fiscal=strict --auto-fix-weight=0.001
```

**Taxa de sucesso esperada** (com G028 ativo): **65-100%** dos pickings PERDA
(vs 17% antes do fix).

## Tarefa 3 — Implementar fix G029 (opcional)

Adicionar `_garantir_payment_provider` no início de
`f5e_transmitir_sefaz` para evitar recovery manual em SSL crash.

```python
def f5e_transmitir_sefaz(self, ajustes, executado_por='sistema'):
    invoices_distintas = sorted({a.invoice_id_odoo for a in ajustes if a.invoice_id_odoo})
    for inv_id in invoices_distintas:
        # G029: garantir payment_provider antes de SEFAZ (idempotente)
        try:
            primeiro_ajuste = next(a for a in ajustes if a.invoice_id_odoo == inv_id)
            self._garantir_payment_provider(inv_id, primeiro_ajuste, executado_por)
        except Exception as e:
            logger.warning(f'G029 payment_provider write falhou: {e}')
        # ... rest of SEFAZ transmission
```

## Tarefa 4 — Drift Cat 2 (175 RENOMEAR_LOTE TRANSF_FALHA)

Sem urgência. Estrategias:
- Aguardar separações concluírem + re-rodar `09_executar_onda1_bulk` com filtro
- Cancelar reservas no Odoo UI
- Aceitar como rabo permanente

## Pre-requisitos não atendidos / decisões em aberto

- ⏳ **317346 robô CIEL IT** — aguardando >24h sem invoice fiscal
- ⏳ **DEV_LF_FB** — 148 ajustes nunca testados em pipeline
- ⏳ **Fix G029 code-level** (opcional, evita recovery manual)

## Resumo dos gotchas relevantes (G016-G029 + INV-030)

| # | Status | Impacto |
|---|--------|---------|
| G005 | ⚠️ ABERTO | Robô CIEL IT lento (revelado >24h sem invoice 317346) |
| G016 | ✅ FIXADO | SSL resilience F5e+F5d + bulk script |
| G017 | ✅ FIXADO | NCM strict validation |
| G018 v2 | ✅ FIXADO | Weight=0 fallback no picking |
| G019 | ✅ FIXADO | F5b validar checa state=done |
| G020 | ✅ FIXADO | F5c pre-cond state=done |
| INV-021 | 🔴 ABERTO | Race A↔B (mitigado via sleep) |
| G022 | 🟡 ABERTO | Mitigado por G028 |
| G023 | ✅ FIXADO | ETAPA F entrada destino auto |
| **G028** | ✅ **FIXADO** | **Over-reservation pos-renomeacao (FIX PRINCIPAL)** |
| G029 | 🟡 WORKAROUND | payment_provider em recovery manual |
| INV-030 | 📝 DOCUMENTADO | Pipeline RecLf trava em Fase 4 (raro) |

## Comandos auxiliares

### Ver estado LF
```bash
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT status, fase_pipeline, acao_decidida, COUNT(*) AS qtd
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=5
GROUP BY status, fase_pipeline, acao_decidida
ORDER BY status, fase_pipeline NULLS FIRST, acao_decidida;
"
```

### Identificar pickings pela metade
```bash
# A) Assigned (potencial F5c_FALHA)
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    p = odoo.search_read('stock.picking',
        [['state', '=', 'assigned'],
         ['origin', 'ilike', 'INV-INVENTARIO_2026_05']],
        ['id', 'name', 'origin'])
    print(f'Assigned: {len(p)}')
    for x in p: print(f'  {x}')
"

# B) Done sem invoice fiscal (via Odoo)
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    p = odoo.search_read('stock.picking',
        [['state', '=', 'done'],
         ['origin', 'ilike', 'INV-INVENTARIO_2026_05']],
        ['id', 'name', 'date_done', 'origin'])
    for x in p:
        invs = odoo.search_read('account.move',
            [['ref', 'ilike', x['name']], ['move_type', '=', 'out_invoice']],
            ['id', 'name'])
        if not invs:
            print(f'  SEM INVOICE: {x[\"id\"]} {x[\"name\"]} done={x[\"date_done\"]}')
"
```

### Promover RENOMEAR TRANSF_OK → EXECUTADO (após cada batch)
```bash
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
UPDATE ajuste_estoque_inventario
SET status='EXECUTADO'
WHERE ciclo='INVENTARIO_2026_05' AND company_id=5
  AND acao_decidida='RENOMEAR_LOTE'
  AND fase_pipeline='TRANSF_OK'
  AND status='PROPOSTO'
RETURNING id;
"
```

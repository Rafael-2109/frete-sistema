# PROMPT — Próxima sessão (2026-05-18 continuação)

> Cole este texto inteiro como primeira mensagem da próxima sessão Claude Code.

---

```
Retomando inventario 2026-05 apos sessao de root cause da NF 626032.

ESTADO ATUAL (verificado em 2026-05-18 07:20):
- Sub-piloto bulk 10 produtos executado end-to-end ate F5e_SEFAZ_OK
- 13 ajustes em F5e_SEFAZ_OK (10 da NF 626032 + 3 da NF 627348)
- ROOT CAUSE da NF 626032 falhar: produto 103000020 ALHO EM PO com
  l10n_br_ncm_id=False no Odoo -> XML gerado com <NCM>False</NCM> ->
  SEFAZ cstat=225 "Falha no Schema XML do lote de NFe" (G017)
- XML preview da NF 626032 baixado via Playwright e inserido em
  l10n_br_xml_aut_nfe (13412 chars b64) — Odoo agora consegue cancelar
- Picking 317311 (LF perda) ja DEVOLVIDO via picking 317315 (state=done).
  Estoque LF restaurado.

PRE-REQUISITOS ANTES DE EU CONTINUAR (usuario fara manualmente):
1. CANCELAR NF 626032 pela UI Odoo:
   URL: https://odoo.nacomgoya.com.br/web#id=626032&cids=5&model=account.move&view_type=form
   Justificativa (84 chars):
   "Inventario 2026-05 LF: NFe com Schema XML invalido (cstat 225) - re-emissao corrigida"

2. CADASTRAR NCM no produto 103000020 ALHO EM PO (provavel NCM 09109100):
   Via UI Odoo: produto -> aba Faturamento -> NCM
   OU via XML-RPC:
   odoo.write('product.product', [PID_ALHO],
       {'l10n_br_ncm_id': NCM_ID})

LER PRIMEIRO (ordem):
1. docs/inventario-2026-05/CHECKPOINT_2026_05_18_NCM_PENDENTE.md (estado completo)
2. docs/inventario-2026-05/02-gotchas/G017-ncm-false-bloqueia-sefaz.md (root cause)
3. docs/inventario-2026-05/02-gotchas/G016-ssl-crash-no-loop-f5e-perde-commits.md (bug PENDENTE para LF completo)
4. docs/inventario-2026-05/00-decisoes/D006-...md secao L24-L25 (resumo)

OBJETIVO desta sessao:
1. Validar que as 2 acoes manuais foram concluidas (NF cancelada + NCM cadastrado)
2. Resetar 10 ajustes do 626032 para PROPOSTO sem picking_id/fase
3. (RECOMENDADO) Implementar G017: validar l10n_br_ncm_id != False em
   etapa_b_pickings antes de criar pickings (script 09_executar_onda1_bulk.py)
4. Re-rodar etapa B+C+D+E do sub-piloto (vai gerar NF nova LF perda)
5. Validar que end-to-end funciona com NCM cadastrado

VALIDAR pre-requisitos:

```python
# 1. NF 626032 cancelada SEFAZ?
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    inv = odoo.read('account.move', [626032],
        ['name', 'state', 'l10n_br_situacao_nf', 'l10n_br_protocolo_cancelamento'])
    print(inv[0])
"
# Esperado: state=cancel + situacao_nf='cancelado' + protocolo populado

# 2. NCM cadastrado em ALHO EM PO?
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    p = odoo.search_read('product.product',
        [['default_code', '=', '103000020']],
        ['default_code', 'name', 'l10n_br_ncm_id'])
    print(p)
"
# Esperado: l10n_br_ncm_id = [N, '09109100 - ...']
```

SE 2 pre-requisitos OK, prosseguir com:

```bash
# 3. Reset DB 10 ajustes (status PROPOSTO, sem picking_id/fase):
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
UPDATE ajuste_estoque_inventario
SET status='PROPOSTO', fase_pipeline=NULL, picking_id_odoo=NULL,
    invoice_id_odoo=NULL, chave_nfe=NULL, erro_msg=NULL
WHERE invoice_id_odoo=626032
RETURNING id, cod_produto;
"
# Esperado: 10 rows.

# 4. Re-rodar etapa B+C+D+E:
source .venv/bin/activate
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
    --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 \\
    --confirmar --confirmar-sefaz --usuario=rafael
```

Apos sub-piloto end-to-end OK (todas as 13 ajustes em F5e_SEFAZ_OK + entrada FB OK):

OBJETIVO MAIOR: LF completo (660 produtos)

PRE-REQUISITOS bloqueante para LF completo:
- Implementar G016 (resiliencia SSL no f5e_transmitir_sefaz)
- Implementar G017 (validar NCM antes pickings + audit em massa)

Audit pre-bulk LF:
```bash
# Listar produtos sem NCM no ciclo LF
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app, db
from sqlalchemy import text
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    cods = db.session.execute(text(\"\"\"
        SELECT DISTINCT cod_produto FROM ajuste_estoque_inventario
        WHERE ciclo='INVENTARIO_2026_05' AND company_id=5 AND status='PROPOSTO'
        ORDER BY cod_produto
    \"\"\")).fetchall()
    odoo = get_odoo_connection()
    cods_list = [r[0] for r in cods]
    # batches de 50
    sem_ncm = []
    for i in range(0, len(cods_list), 50):
        batch = cods_list[i:i+50]
        prods = odoo.search_read('product.product',
            [['default_code', 'in', batch]],
            ['default_code', 'l10n_br_ncm_id'])
        sem_ncm.extend([p['default_code'] for p in prods if not p.get('l10n_br_ncm_id')])
    print(f'Total produtos onda 1 LF: {len(cods_list)}')
    print(f'Produtos SEM NCM: {len(sem_ncm)}')
    if sem_ncm:
        print('Cods:', sem_ncm[:30])
"
```

Quando estiver TUDO OK, rodar LF completo:
```bash
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
    --company-id=5 --onda=1 --max-produtos-picking=30 \\
    --confirmar --confirmar-sefaz --usuario=rafael
```
```

---

## Resumo executivo

| Item | Status |
|---|---|
| 23 bugs L1-L23 fixados | ✅ |
| L24/G016 SSL crash | ⚠️ PROPOSTO (precisa antes LF completo) |
| L25/G017 NCM=False | ⚠️ PROPOSTO (precisa antes LF completo) |
| NF 626032 cancel | ⚠️ MANUAL (usuario faz pela UI Odoo) |
| NCM ALHO 103000020 | ⚠️ MANUAL (usuario cadastra) |
| Picking 317311 devolvido | ✅ (via 317315 done) |
| Tests baseline | ✅ 130 passing |

## Arquivos referencia

- Checkpoint: `docs/inventario-2026-05/CHECKPOINT_2026_05_18_NCM_PENDENTE.md`
- Decisao D006: `docs/inventario-2026-05/00-decisoes/D006-...md` (L24-L25)
- Gotchas: G010 a G017 em `docs/inventario-2026-05/02-gotchas/`
- Script bulk: `scripts/inventario_2026_05/09_executar_onda1_bulk.py`
- Script XML preview: `scripts/inventario_2026_05/baixar_xml_preview_626032.py`
- Pipeline service: `app/odoo/services/inventario_pipeline_service.py`

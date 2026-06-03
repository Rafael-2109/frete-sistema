<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/08-execucoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Execução: Cadastro NCM + Weight em 3 produtos LF

**Data**: 2026-05-18 08:19 UTC
**Executado por**: Claude Code sessao 2 manha + autorizacao explicita Rafael
**Contexto**: pre-requisitos manuais do sub-piloto inventario 2026-05 LF
(NF 626032 root cause = G017 NCM=False)
**Snapshot auditoria**: `/tmp/auditoria_ncm_weight_2026_05_18.json`

---

## 1. Resultado final

| Produto | weight antes → depois | NCM antes → depois |
|---|---|---|
| 103000020 ALHO EM PÓ (pid=31416) | 1.0 → 1.0 (sem mudanca) | **None → 07129010** |
| 104000046 CORANTE VERMELHO (pid=34907) | 0.0 → **1.0** | **None → 32041100** |
| 109000101 OLEO MISTO (pid=34914) | 0.0 → **0.93** | **None → 15179090** |

5 campos modificados (2 weights + 3 NCMs). Verificacao pos-write OK em
todos os 3 produtos.

---

## 2. Modelo CIEL IT customizado (descoberta)

CIEL IT NAO usa `l10n_br_fiscal.ncm` (modelo padrao OCA). Usa modelo
**proprio**:

```
l10n_br_ciel_it_account.ncm
```

Campos relevantes (descobertos via `fields_get`):

| Campo | Tipo | Uso |
|---|---|---|
| `id` | int | PK |
| `codigo_ncm` | char | Codigo NCM em formato `'XXXXXXXX'` (sem mascara) |
| `name` | char | Descricao tipo `'ALHO EM PO'` ou `'CORANTES DISPERSOS...'` |
| `codigo_cest` | char | CEST quando aplicavel |
| `display_name` | char | Computed |

Buscas que **NAO funcionam**:
- `[['code', '=', '...']]` -> Invalid field
- `[['code_unmasked', '=', '...']]` -> Invalid field
- `[['cod_ncm', '=', '...']]` -> Invalid field

Busca que **funciona**:
```python
odoo.search_read('l10n_br_ciel_it_account.ncm',
    [['codigo_ncm', '=', '07129010']],  # sem mascara, 8 digitos
    ['id', 'codigo_ncm', 'name'], limit=1)
```

**Lição para skill `descobrindo-odoo-estrutura`**: sempre fazer
`fields_get` antes de assumir nome do modelo many2one.

---

## 3. Decisões fiscais (NCMs aplicados)

### 3.1. ALHO EM PÓ (103000020) → NCM 07129010

**Justificativa**: produto similar `104000077 AMOSTRA - ALHO EM PO` ja
tinha o mesmo NCM cadastrado. Descricao do NCM em `name` = "ALHO EM PO"
(match literal).

**Rejeitado**: NCM 09109100 (sugestao inicial Rafael) — pertence ao
Cap. 09 (cafe/cha/mate/especiarias). Alho seco/em po e' classificado
no Cap. 07 (hortícolas).

**Alternativas avaliadas**:
- 07129020 "Alho em po" (usado em 105000094 ALHO EM PO CHINES,
  105000095 ALHO EM PO INDIANO) — variante de origem importada
- 07129090 "OUTROS PRODUTOS HORTICOLAS" (usado em 103000037 ALHO GRANULADO,
  103000121 ALHO PORO DESIDRATADO POLICO)

Decisao por **07129010** pelo match literal de descricao no NCM (cadastro
proprio do nome). Se contadora preferir 07129020, basta novo write.

### 3.2. CORANTE VERMELHO (104000046) → NCM 32041100

**Justificativa**: 3 produtos similares no Odoo usam o mesmo NCM:
- `104000020 CORANTE - VERMELHO` (mesmo nome)
- `104000048 CORANTE - VITAMASSA U/102 (cópia)`
- `104000151 AMOSTRA – CORANTE ARTIFICIAL VERMEL`

NCM 32041100 = "CORANTES DISPERSOS E PREPARAÇÕES À BASE DESSES CORANTES".

### 3.3. OLEO MISTO (109000101) → NCM 15179090

**Justificativa**: produto similar `109000100 OLEO MISTO SOJA/AZEITE`
(mesma familia 109xxx + mesmo nome) ja tem este NCM.

NCM 15179090 = "MISTURA DE OLEOS VEGETAIS" (match literal de descricao).

---

## 4. IDs Odoo (auditoria)

```json
{
  "ncms_aplicados": {
    "103000020": {"ncm_code": "07129010", "ncm_id": 29005, "ncm_name": "ALHO EM PO"},
    "104000046": {"ncm_code": "32041100", "ncm_id": 27676,
                  "ncm_name": "CORANTES DISPERSOS E PREPARAÇÕES À BASE DESSES COR"},
    "109000101": {"ncm_code": "15179090", "ncm_id": 28485,
                  "ncm_name": "MISTURA DE OLEOS VEGETAIS"}
  }
}
```

---

## 5. Validação pos-aplicacao

```bash
source .venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    p = odoo.read('product.product', [31416, 34907, 34914],
        ['default_code', 'name', 'l10n_br_ncm_id', 'weight'])
    for r in p:
        ncm = r['l10n_br_ncm_id'][1] if r['l10n_br_ncm_id'] else None
        print(f'{r[\"default_code\"]} weight={r[\"weight\"]} ncm={ncm}')
"
```

Output esperado:
```
103000020 weight=1.0 ncm=07129010 - ALHO EM PO
104000046 weight=1.0 ncm=32041100 - CORANTES DISPERSOS...
109000101 weight=0.93 ncm=15179090 - MISTURA DE OLEOS VEGETAIS
```

Re-rodar audit fiscal LF para confirmar que os 3 produtos sairam da
lista "sem NCM":

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
sys.path.insert(0, 'scripts/inventario_2026_05')
import importlib.util
spec = importlib.util.spec_from_file_location(
    'bulk', 'scripts/inventario_2026_05/09_executar_onda1_bulk.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    pids = {'103000020': 31416, '104000046': 34907, '109000101': 34914}
    res = mod.validar_cadastro_fiscal(odoo, pids, modo='strict')
    print(f'OK: sem_ncm={len(res[\"sem_ncm\"])} sem_weight={len(res[\"sem_weight\"])}')
"
```

Output esperado:
```
OK: sem_ncm=0 sem_weight=0
```

---

## 6. Status pre-requisitos pos-execucao

| # | Item | Status |
|---|---|---|
| 3.1 | Cancelar NF 626032 SEFAZ | ⚠️ PENDENTE — Rafael fara depois |
| 3.2 | Cadastrar NCM em 3 produtos | ✅ CONCLUIDO (2026-05-18 08:19 UTC) |
| 3.3 | Cadastrar weight em 2 produtos | ✅ CONCLUIDO (2026-05-18 08:14 UTC) |

Apos 3.1 (cancel NF 626032), pode-se proceder com reset DB + re-execucao
sub-piloto.

---

## 7. Impacto LF completo (455 produtos)

Audit fiscal pos-aplicacao (esperado):
- **Sem NCM: 0** (era 3, todos resolvidos)
- **Sem weight em acao de picking: 107** (era 109, -2 — CORANTE + OLEO MISTO resolvidos)

Os 107 restantes ainda sao bloqueio para LF completo (G018 PROPOSTO).
Decisao A/B/C ainda pendente para esses 107.

---

## Ref

- `docs/inventario-2026-05/02-gotchas/G017-ncm-false-bloqueia-sefaz.md`
- `docs/inventario-2026-05/07-relatorios/audit_fiscal_LF.md`
- `docs/inventario-2026-05/CHECKPOINT_2026_05_18_NCM_PENDENTE.md`
- `/tmp/auditoria_ncm_weight_2026_05_18.json` (snapshot completo)

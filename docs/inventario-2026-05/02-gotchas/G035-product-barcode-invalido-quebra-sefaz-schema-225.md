# G035 — `product.barcode` invalido como GTIN quebra SEFAZ Schema 225

**Severidade**: CRITICAL
**Status**: ✅ IDENTIFICADO + FIX APLICADO (2026-05-19)
**Descoberto em**: Sessao LF→FB MIGRAÇÃO PERDA_LF_FB (Excel 317 cods)

## Sintoma

NF-e emitida via robo CIEL IT retorna SEFAZ:
```
cstat=225, xmotivo="Rejeição: Falha no Schema XML do lote de NFe"
```

A UI Odoo CIEL IT mostra apenas a mensagem generica acima — nao indica XPath
do elemento invalido. Tentativas (max 15) repetem o mesmo erro.

**Pattern correlacional observado**:
- 8/9 NFs OK: TODOS produtos com `product.barcode` = `False`/`None`
- 1/9 NFs OK: 1 produto com barcode `7908152302344` (**GTIN-13 valido**)
- 7/7 NFs FAIL: 1+ produtos com `product.barcode` = `default_code` (9 digitos, NAO eh GTIN)

## Causa raiz

Schema NF-e v4.00 do elemento `<cEAN>` (codigo EAN/GTIN do produto):

- Aceita: `"SEM GTIN"` (texto literal) quando produto sem codigo de barras
- Aceita: GTIN-8 (8 digitos), GTIN-12 (12 dig UPC-A), GTIN-13 (13 dig EAN-13),
  GTIN-14 (14 dig) — todos com check digit valido conforme algoritmo Modulo 10
- **REJEITA**: qualquer outro valor (incluindo numeros com 9 digitos, valores
  alfanumericos, ou GTIN-8/12/13/14 com check digit invalido)

Quando `product.barcode` esta preenchido com valor inválido (ex: `210010347`
— 9 digitos, sem check digit), o XML gerado pelo CIEL IT inclui:
```xml
<cEAN>210010347</cEAN>
```

SEFAZ valida formato/check-digit do `cEAN` no schema XSD e rejeita o lote
INTEIRO com cstat=225 (schema fail), sem indicar qual produto causou.

## Casos concretos identificados

Produtos no escopo do INVENTARIO_2026_05 com barcode invalido:

```
105000040, 207030426, 207032627, 207032727, 207120233, 207120309,
207120433, 209000110, 210010322, 210010339, 210010347, 301100029,
3800000, 3800002, 3800004, 3800005, 3800007, 3800009, 3800011, 3800012,
3800016, 3800018, 3800019, 4820151, 4820153, 4829012, 4829051, 4829052,
4829053, 4849076, 4869012, 4879012, 4889003, 4899024, 4899027, 4899028
```

Total no escopo: **36 produtos** afetados.

## Fix aplicado

UPDATE em `product.product` setando `barcode = False` para esses 36 cods:

```python
def is_valid_gtin(s):
    """Valida GTIN-8/12/13/14 com check digit Modulo 10."""
    if not s or not str(s).isdigit():
        return False
    s = str(s)
    if len(s) not in (8, 12, 13, 14):
        return False
    digits = [int(d) for d in s]
    check = digits[-1]
    body = digits[:-1][::-1]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(body))
    expected = (10 - total % 10) % 10
    return expected == check

# Buscar produtos com barcode invalido
prods = odoo.search_read('product.product', [['barcode','!=',False]], ['id','barcode'])
to_clear = [p['id'] for p in prods if not is_valid_gtin(p['barcode'])]
odoo.write('product.product', to_clear, {'barcode': False})
```

Script reutilizavel: `/tmp/limpar_barcode_invalido.py` (ver historia desta
sessao).

## Validacao pos-fix

Apos limpeza, **5 batches de PERDA_LF_FB** (146 cods) foram processados
sequencialmente:
- Batch 1 (30 cods): 4/4 NFs SEFAZ OK
- Batch 2 (30 cods): 4/4 OK
- Batch 3 (30 cods): 5/5 OK (incluindo 1 reprocessada antiga)
- Batch 4 (30 cods): 3/3 OK
- Batch 5 (26 cods): 3/3 OK

**Zero rejeicoes Schema 225 pos-fix**.

## Como aplicar profilaticamente

ANTES de qualquer emissao SEFAZ via CIEL IT em lote, executar validador de
GTIN em todos os produtos do escopo:

```python
# Adicionar em scripts/inventario_2026_05/ ou pre-flight check generico:
from app.odoo.utils.connection import get_odoo_connection
odoo = get_odoo_connection()
prods = odoo.search_read('product.product',
    [['barcode','!=',False],['default_code','in',cods_do_lote]],
    ['id','default_code','barcode'])
invalidos = [p for p in prods if not is_valid_gtin(p['barcode'])]
if invalidos:
    raise RuntimeError(
        f'{len(invalidos)} produtos com barcode invalido como GTIN. '
        f'Limpar antes de emitir NF-e (G035). Cods: '
        f'{[p["default_code"] for p in invalidos[:10]]}'
    )
```

## Why

CIEL IT default eh popular `barcode` com `default_code` quando o produto eh
criado sem GTIN real (ex: matéria-prima, embalagem, batelada interna). Isso
gera XML `<cEAN>{default_code}</cEAN>` que SEFAZ rejeita silenciosamente
porque o schema XSD valida formato GTIN no `cEAN`.

A UI do Odoo nao alerta esse problema porque `barcode` aceita qualquer string
no DB — a validacao so acontece quando SEFAZ recebe o lote.

## How to apply

- Em qualquer operacao em lote NF-e: rodar pre-flight check de GTIN.
- Em cadastro novo de produto matéria-prima/embalagem/batelada: NAO popular
  `barcode` (deixar `False`). Se o usuario precisar do default_code visivel
  em scan, criar campo customizado.
- Em recuperacao de NF Schema 225: SEMPRE verificar `barcode` dos produtos
  da NF antes de outras hipoteses.

## Referencias

- Schema NF-e 4.00: <https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=33ol5hhSYZk=>
- Algoritmo check digit GTIN: <https://www.gs1.org/services/how-calculate-check-digit-manually>
- Logs da sessao: `/tmp/lf_fb_batch*.log` (2026-05-19)
- Comparacao OK vs FAIL: `/tmp/comparar_ok_vs_fail.py`
- Validador GTIN: `/tmp/limpar_barcode_invalido.py`

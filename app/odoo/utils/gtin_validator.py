"""GTIN validator for SEFAZ NF-e cEAN/cEANTrib fields.

G035 (2026-05-19): produtos com `barcode` invalido como GTIN geram
`<cEAN>` no XML que SEFAZ rejeita com cstat=225 "Falha no Schema XML do
lote de NFe". CIEL IT default popula `product.barcode` com `default_code`
em materia-prima/embalagem/batelada — esses valores NAO sao GTIN validos.

Schema NF-e v4.00 do elemento <cEAN>:
- Aceita "SEM GTIN" (texto literal)
- Aceita GTIN-8, GTIN-12, GTIN-13, GTIN-14 com check digit Modulo 10
- Rejeita qualquer outro valor

Uso:
    from app.odoo.utils.gtin_validator import is_valid_gtin, find_invalid_barcodes

    if not is_valid_gtin(product.barcode):
        # XML SEFAZ vai rejeitar — limpar antes de emitir
        ...

    # Pre-flight check em lote
    invalids = find_invalid_barcodes(odoo, cods_da_nf)
    if invalids:
        raise RuntimeError(f'G035: {len(invalids)} produtos com barcode invalido')

Ver `docs/inventario-2026-05/02-gotchas/G035-*.md` para detalhes.
"""
from typing import Dict, List, Optional


def is_valid_gtin(value) -> bool:
    """Valida GTIN-8/12/13/14 com check digit (algoritmo Modulo 10 GS1).

    Args:
        value: codigo a validar (string ou int)

    Returns:
        True se for GTIN-8, GTIN-12, GTIN-13 ou GTIN-14 valido.
        False para qualquer outro formato (incluindo None, '', non-digit,
        len != 8/12/13/14, ou check digit invalido).

    Examples:
        >>> is_valid_gtin('7908152302344')  # GTIN-13 valido
        True
        >>> is_valid_gtin('210010347')  # 9 digitos — NAO eh GTIN
        False
        >>> is_valid_gtin(None)
        False
        >>> is_valid_gtin('')
        False
        >>> is_valid_gtin('SEM GTIN')
        False  # texto literal — caller deve tratar como nao-GTIN
    """
    if value is None or value is False:
        return False
    s = str(value).strip()
    if not s.isdigit():
        return False
    if len(s) not in (8, 12, 13, 14):
        return False
    digits = [int(d) for d in s]
    check = digits[-1]
    body = digits[:-1][::-1]  # reverso, sem check digit
    # GTIN check digit: posicoes impares (0-indexed reversed) pesam 3, pares pesam 1
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(body))
    expected = (10 - total % 10) % 10
    return expected == check


def find_invalid_barcodes(
    odoo,
    cods_produto: Optional[List[str]] = None,
    product_ids: Optional[List[int]] = None,
) -> List[Dict]:
    """Busca produtos com barcode preenchido mas invalido como GTIN.

    Args:
        odoo: conexao Odoo (OdooConnection)
        cods_produto: lista de default_code a verificar (opcional)
        product_ids: lista de IDs Odoo a verificar (opcional, prioritario
                     sobre cods_produto se ambos fornecidos)

    Returns:
        Lista de dicts com `{id, default_code, barcode}` dos produtos com
        barcode invalido (que geram SEFAZ Schema 225 reject).

    Examples:
        >>> invalids = find_invalid_barcodes(odoo, cods_produto=['210010347'])
        >>> if invalids:
        ...     ids = [p['id'] for p in invalids]
        ...     odoo.write('product.product', ids, {'barcode': False})
    """
    if product_ids:
        domain = [['id', 'in', product_ids], ['barcode', '!=', False]]
    elif cods_produto:
        domain = [['default_code', 'in', cods_produto], ['barcode', '!=', False]]
    else:
        domain = [['barcode', '!=', False]]

    prods = odoo.search_read('product.product', domain,
                             ['id', 'default_code', 'barcode'])
    return [p for p in prods if not is_valid_gtin(p['barcode'])]


def clear_invalid_barcodes(odoo, cods_produto=None, product_ids=None) -> int:
    """Helper: encontra e limpa (set False) barcodes invalidos em lote.

    Returns:
        Numero de produtos atualizados.
    """
    invalids = find_invalid_barcodes(odoo, cods_produto=cods_produto,
                                     product_ids=product_ids)
    if not invalids:
        return 0
    ids = [p['id'] for p in invalids]
    odoo.write('product.product', ids, {'barcode': False})
    return len(ids)

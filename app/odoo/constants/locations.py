"""
COMPANY_LOCATIONS — location_id de estoque interno principal por company.

Validado em F0 audit (`scripts/inventario_2026_05/00_audit_odoo_realidade.py`):
- FB/Estoque = id 8
- CD/Estoque = id 32
- LF/Estoque = id 42

Cada company tem outras locations (sub-localizacoes, conferencia, etc).
Esta constante mantem apenas a location INTERNA PRINCIPAL — usar como
default para origem/destino de pickings de transferencia.

Atualizar quando uma company mudar ou for adicionada.
Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §5.1
"""
from typing import Dict


COMPANY_LOCATIONS: Dict[int, int] = {
    1: 8,    # FB — FB/Estoque
    4: 32,   # CD — CD/Estoque
    5: 42,   # LF — LF/Estoque
}


def get_location_id(company_id: int) -> int:
    """Retorna location_id interna principal da company.

    Raises:
        ValueError: se company_id nao mapeada.
    """
    loc = COMPANY_LOCATIONS.get(company_id)
    if loc is None:
        raise ValueError(f'COMPANY_LOCATIONS sem entrada para company_id={company_id}')
    return loc

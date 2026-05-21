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


# ---------------------------------------------------------------------------
# Locais "Indisponivel" por company (D011) — quants em ajuste de inventario
# ficam isolados aqui, invisiveis a stock.rule (child_of nao alcanca).
# Fonte: docs/inventario-2026-05/00-decisoes/D011-locais-indisponivel-por-empresa.md (tabela linhas 33-38, dict 43-47)
# NOTA: redefinido solto em varios scripts (auditar_migracao_fora_indisponivel,
# extrair_estoque_locais_emp, executar_fluxo_b_vivas, ...) — importar daqui.
# ---------------------------------------------------------------------------
LOCAIS_INDISPONIVEL: Dict[int, int] = {
    1: 31088,  # FB/Indisponivel
    3: 31089,  # SC/Indisponivel (local existe; SC fora do escopo operacional — D011:95)
    4: 31090,  # CD/Indisponivel
    5: 31091,  # LF/Indisponivel
}


def get_local_indisponivel(company_id: int) -> int:
    """Retorna location_id do {emp}/Indisponivel da company.

    Raises:
        ValueError: se company_id nao mapeada.
    """
    loc = LOCAIS_INDISPONIVEL.get(company_id)
    if loc is None:
        raise ValueError(f'LOCAIS_INDISPONIVEL sem entrada para company_id={company_id}')
    return loc


# ---------------------------------------------------------------------------
# Lote consolidador 'MIGRACAO' por company (stock.lot.id ja existente — D005/D011).
# So FB e CD usam MIGRACAO; LF (5) nao usa (apenas NF FB<->LF); SC (3) fora de escopo.
# Fonte: D011-...:104 ("id=30482 FB MIGRAÇÃO, id=30856 CD MIGRAÇÃO"), 121
# ---------------------------------------------------------------------------
LOTES_MIGRACAO_POR_COMPANY: Dict[int, int] = {
    1: 30482,  # FB — lote MIGRAÇÃO
    4: 30856,  # CD — lote MIGRAÇÃO
}

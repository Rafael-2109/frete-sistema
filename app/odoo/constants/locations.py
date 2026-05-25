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
# ⛔ DEPRECATED 2026-05-24 v4 (G031) — NAO USAR EM ESCRITA.
#
# `LOTES_MIGRACAO_POR_COMPANY` é HISTORICO/EXEMPLO. Cada valor é o `stock.lot.id`
# do lote MIGRAÇÃO de UM produto especifico (escolhido em D011 do inventario
# 2026-05). **stock.lot tem `product_id` no Odoo CIEL IT** — cada produto tem
# seu PROPRIO lote MIGRACAO (mesmo NOME, lot_ids DIFERENTES).
#
# Usar isso como FK universal em `stock.quant.create({lot_id: 30482, product_id: Y})`
# de produto diferente do "dono" do lote gera erro:
#   <Fault 2: 'O numero de lote/serie (MIGRACAO) esta vinculado a outro produto.'>
#
# Incidente real 2026-05-24 v4: 16/16 FALHA_AUMENTO em PROD; rollback 100% OK;
# fix via `lot_svc.criar_se_nao_existe`. Ver
# `docs/inventario-2026-05/02-gotchas/G031-lot-migracao-por-produto.md`.
#
# ✅ CAMINHO CORRETO — sempre resolver POR PRODUTO:
#   lot_svc.buscar_por_nome('MIGRAÇÃO', product_id, company_id)        # read
#   lot_svc.criar_se_nao_existe('MIGRAÇÃO', product_id, company_id)    # write
#
# Mantido apenas para read-only docs / referencias historicas. Future-proof:
# considerar remocao quando todas as skills migrarem (auditar via grep
# `LOTES_MIGRACAO_POR_COMPANY\[`).
# ---------------------------------------------------------------------------
LOTES_MIGRACAO_POR_COMPANY: Dict[int, int] = {
    1: 30482,  # FB — lote MIGRACAO de UM produto (NAO universal — G031)
    4: 30856,  # CD — lote MIGRACAO de UM produto (NAO universal — G031)
}


def _warn_lot_migracao_universal() -> None:
    """Avisa que LOTES_MIGRACAO_POR_COMPANY NAO eh FK universal (G031)."""
    import warnings
    warnings.warn(
        'LOTES_MIGRACAO_POR_COMPANY eh HISTORICO/EXEMPLO — stock.lot tem '
        'product_id no Odoo. Usar lot_svc.buscar_por_nome/criar_se_nao_existe '
        'POR PRODUTO em vez disso. Ver gotcha G031.',
        DeprecationWarning,
        stacklevel=3,
    )

# Nome canonico do lote consolidador por company (USAR este para resolver
# POR PRODUTO via lot_svc.buscar_por_nome / criar_se_nao_existe).
NOME_LOTE_MIGRACAO_POR_COMPANY: Dict[int, str] = {
    1: 'MIGRAÇÃO',  # FB (com cedilha — canonico)
    4: 'MIGRAÇÃO',  # CD
}


# ---------------------------------------------------------------------------
# Sub-locais de Pré-Produção por company (default canonico — scripts 15/17).
# Sao parametrizaveis nos scripts (--locs sobrescreve); este e o conjunto base.
# {company_id: {location_id: nome}}
# ---------------------------------------------------------------------------
LOCAIS_PRE_PRODUCAO: Dict[int, Dict[int, str]] = {
    1: {  # FB
        4066: 'FB/Pré-Produção/Linha Vidro',
        4067: 'FB/Pré-Produção/Linha Manual',
        4068: 'FB/Pré-Produção/Linha Balde',
        27458: 'FB/Pré-Produção/Linha Salmoura',
    },
    5: {  # LF
        53: 'LF/Pré-Produção',
        30710: 'LF/Pré-Produção/Intermediário',
    },
}

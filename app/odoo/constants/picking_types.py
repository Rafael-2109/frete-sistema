"""Picking types e locations virtuais de destino por direcao inter-company (NACOM).

Movido de `app/odoo/services/inventario_pipeline_service.py` (TODO G003 — SOT.md §3:
"mover este mapping para app/odoo/constants/picking_types.py se virar fonte de gotcha").
O service e os scripts passam a importar daqui (fonte unica).

Chave dos dicts: tupla (company_origem_id, tipo_operacao).
- company_origem_id: 1=FB, 4=CD, 5=LF (ver `operacoes_fiscais.CODIGO_PARA_COMPANY_ID`)
- tipo_operacao: chave de `operacoes_fiscais.MATRIZ_INTERCOMPANY`
  ('transf-filial', 'industrializacao', 'perda', 'dev-industrializacao')

Fonte dos valores: audit dos picking_types e default_location_dest_id (2026-05-18);
G034 (2026-05-18) criou PT 97/88 via XML-RPC para dev-industrializacao.
"""
from typing import Dict, Tuple


# stock.picking.type.id de SAIDA por (company_origem, tipo_operacao).
#   CD outgoing: 55 (entre filiais) | 96 (retrabalho)
#   LF outgoing: 66 (industrializacao) | 94 (n. aplicado)
PICKING_TYPE_POR_DIRECAO: Dict[Tuple[int, str], int] = {
    (1, 'transf-filial'):        51,  # FB: Expedicao Entre Filiais
    (4, 'transf-filial'):        55,  # CD: Expedicao Entre Filiais
    (1, 'industrializacao'):     53,  # FB: Expedicao Industrializacao
    (5, 'perda'):                94,  # LF: Expedicao N Aplicado
    (4, 'dev-industrializacao'): 96,  # CD: Retrabalho (CD/OUT/RET)
    # G034 (2026-05-18): PT 97 'LF: Expedição Industrialização Retorno (LF)'
    # criado via XML-RPC para ter l10n_br_tipo_pedido='dev-industrializacao'.
    # Substitui PT 66 (que tinha tipo='venda-industrializacao' → journal VND →
    # CFOP 5124 errado). PT 97 → journal SARET → CFOP 5949.
    # Sequence: ir.sequence id=188 (prefix LF/LF/SAI/RETIND/).
    (5, 'dev-industrializacao'): 97,  # LF: Saida Retrabalho (LF/SAI/RETIND)
    (1, 'dev-industrializacao'): 88,  # FB: Saida Retorno Industrializacao (FB/SAI/RETIND, espelho)
}


# Locations virtuais usadas como destino de pickings inter-company.
# Pickings outgoing exigem location_dest_id com company_id=False (shared).
# Descobertos em audit dos picking_types.default_location_dest_id (2026-05-18):
#   pt 53 FB Expedicao Industrializacao: dest=26489 (Em Transito Industrializacao)
#   pt 51 FB Expedicao Entre Filiais:    dest=6     (Em Transito Filiais)
#   pt 55 CD Expedicao Entre Filiais:    dest=6     (Em Transito Filiais)
#   pt 66 LF Expedicao Industrializacao: dest=5     (Parceiros/Clientes)
#   pt 94 LF Expedicao N Aplicado:       dest=5     (Parceiros/Clientes)
#   pt 96 CD Retrabalho:                 dest=26489 (Em Transito Industrializacao)
LOCATION_DESTINO_VIRTUAL_PARCEIROS = 5   # Parceiros/Clientes (perda LF→FB)
LOCATION_DESTINO_TRANSITO_FILIAIS = 6    # Em Transito (Filiais) — TRANSF_FILIAL
LOCATION_DESTINO_TRANSITO_INDUSTR = 26489  # Em Transito (Industrializacao)

# Mapeamento canonico por (company_origem, tipo_op) -> location virtual
# de destino. Validado contra default_location_dest_id de cada picking_type.
LOCATION_DESTINO_POR_DIRECAO: Dict[Tuple[int, str], int] = {
    (5, 'perda'):                5,      # LF→FB perda
    (1, 'industrializacao'):     26489,  # FB→LF industrializacao
    (5, 'industrializacao'):     5,      # LF retorno (pt 66 LF Exp Industr)
    (1, 'transf-filial'):        6,      # FB→CD
    (4, 'transf-filial'):        6,      # CD→FB
    (5, 'dev-industrializacao'): 5,      # LF retorna industr (pt 66)
    (4, 'dev-industrializacao'): 26489,  # CD retrabalho (pt 96)
    (1, 'dev-industrializacao'): 26489,  # FB dev industr (pt 53)
}


def get_picking_type(company_origem: int, tipo_operacao: str) -> int:
    """Retorna picking_type_id de saida para a direcao. Raises se nao mapeada."""
    pt = PICKING_TYPE_POR_DIRECAO.get((company_origem, tipo_operacao))
    if pt is None:
        raise ValueError(
            f'PICKING_TYPE_POR_DIRECAO sem entrada para '
            f'(company={company_origem}, tipo={tipo_operacao!r}). '
            f'Validas: {sorted(PICKING_TYPE_POR_DIRECAO.keys())}'
        )
    return pt

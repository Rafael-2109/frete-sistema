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
v15a (2026-05-25): centralizadas constants ETAPA F (entrada destino manual) que
estavam inline em `scripts/inventario_2026_05/09_executar_onda1_bulk.py:126-146`.
"""
from typing import Dict, FrozenSet, Tuple


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


# ============================================================================
# ETAPA F — Entrada Destino Manual (FB→{LF, CD})
# ============================================================================
# Padrao L17: NFs sentido FB→{LF, CD} de industrializacao interna precisam
# de picking de ENTRADA criado MANUALMENTE no destino. O robo CIEL IT nao
# cria entrada automatica (nao ha DFe no sentido reverso).
#
# Validado em PROD via pickings:
#   - 317306 LF/IN/01733 (NF 608629)
#   - 317316 LF/IN/01734 (NF 627348)
#
# Centralizado em v15a (2026-05-25) — antes inline em
# `scripts/inventario_2026_05/09_executar_onda1_bulk.py:126-146`.
# ============================================================================

# Acoes (do AjusteEstoqueInventario.acao_decidida) que requerem ETAPA F.
#
# v17.5 (2026-05-26): expandido para incluir DEV_FB_LF e TRANSFERIR_FB_CD
# (com flag --auto-confirma-direcao-nova default False; decisao Rafael Q1=C).
# - INDUSTRIALIZACAO_FB_LF: validado PROD (317306, 317316) — sempre habilitado
# - DEV_FB_LF: assumido fp 86 (sem precedente PROD) — canary fiscal v17.5
# - TRANSFERIR_FB_CD: PT 50 CD/IN/INTER src=6 dest=32 (audit Odoo 2026-05-26;
#   nunca rodou INVENTARIO_2026_05; ENTTR/2026/05 invoices observadas sao
#   DFe externos, nao desta skill — entrada manual eh necessaria)
ACOES_ENTRADA_DESTINO_MANUAL: FrozenSet[str] = frozenset({
    'INDUSTRIALIZACAO_FB_LF',   # FB→LF — validado PROD (317306, 317316)
    'DEV_FB_LF',                # FB→LF — canary v17.5 (fp 86 assumido)
    'TRANSFERIR_FB_CD',         # FB→CD — canary v17.5 (PT 50, src=6, dest=32)
})


# Acoes que requerem flag --auto-confirma-direcao-nova=True para executar
# em real-run (canary fiscal sem precedente PROD).
# INDUSTRIALIZACAO_FB_LF NAO esta aqui — ja validada (317306, 317316).
ACOES_ENTRADA_DESTINO_MANUAL_CANARY: FrozenSet[str] = frozenset({
    'DEV_FB_LF',                # fp 86 assumido — canary fiscal pendente
    'TRANSFERIR_FB_CD',         # PT 50 nunca rodou INVENTARIO_2026_05 — canary
})


# stock.picking.type.id de ENTRADA por company DESTINO.
# Origem do picking eh `LOCATION_ORIGEM_POR_DIRECAO[acao]` (varia por direcao
# em v17.5; antes era hardcode 26489); destino e o
# `COMPANY_LOCATIONS[company_destino]` (estoque interno principal do destino).
#
# Discovery audit Odoo 2026-05-26 v17.5:
#   - LF PT 19 LF/IN Recebimento  (validado 317306, 317316)
#   - LF PT 64 LF/RECEB/IND        (dedicado industr — usado por DFe externo,
#                                    NAO para inter-company nosso)
#   - CD PT 50 CD/IN/INTER         (src=6 Em Trans. Filiais, dest=32 CD/Estoque)
PICKING_TYPE_ENTRADA_DESTINO_MANUAL: Dict[int, int] = {
    5: 19,   # LF: Recebimento (validado 317306, 317316)
    4: 50,   # CD: Recebimentos Entre Filiais (NACOM/CD/IN/INTER) — v17.5
}


# Label da company para usar em `origin` de pickings ETAPA F.
# Convenção do CICLO atual: `INV-{CICLO}-ENTRADA-{LABEL}-NF{invoice_id}`.
# Inclui FB para casos futuros de espelhamento reverso (LF→FB entrada manual).
COMPANY_LABEL_ENTRADA: Dict[int, str] = {
    1: 'FB',
    4: 'CD',
    5: 'LF',
}


# location_id ORIGEM por direcao (v17.5).
# Antes da v17.5: hardcode 26489 (LOCATION_ORIGEM_ENTRADA_INDUSTR) em todas
# as direcoes ETAPA F. v17.5 separa por acao_decidida:
#   - INDUSTRIALIZACAO_FB_LF: 26489 Em Trans. Industr. (saida PT 53 dest)
#   - DEV_FB_LF: 26489 Em Trans. Industr. (assumido — saida via PT 88 dest)
#   - TRANSFERIR_FB_CD: 6 Em Trans. Filiais (saida PT 51 dest; entrada PT 50 src)
LOCATION_ORIGEM_POR_DIRECAO: Dict[str, int] = {
    'INDUSTRIALIZACAO_FB_LF': LOCATION_DESTINO_TRANSITO_INDUSTR,  # 26489
    'DEV_FB_LF':              LOCATION_DESTINO_TRANSITO_INDUSTR,  # 26489 (assumido)
    'TRANSFERIR_FB_CD':       LOCATION_DESTINO_TRANSITO_FILIAIS,  # 6
}


# Alias semantico: `LOCATION_DESTINO_TRANSITO_INDUSTR` da SAIDA (ETAPA B) eh
# a MESMA location que serve como ORIGEM da ENTRADA (ETAPA F). Manter os 2
# nomes — `LOCATION_DESTINO_TRANSITO_INDUSTR` vira de SAIDA; o alias deixa
# explicito quando usado em ENTRADA (centralizando o numero magico 26489).
#
# DEPRECATED v17.5: prefira `LOCATION_ORIGEM_POR_DIRECAO[acao]` que varia
# por direcao. Mantido para backward-compat (orchestrator legado).
LOCATION_ORIGEM_ENTRADA_INDUSTR = LOCATION_DESTINO_TRANSITO_INDUSTR  # 26489


def get_location_origem_entrada(acao: str) -> int:
    """Retorna location_id origem da ENTRADA ETAPA F para a `acao_decidida`.

    Raises:
        ValueError se acao nao mapeada em LOCATION_ORIGEM_POR_DIRECAO.

    Usado pelo orchestrator Skill 8 ETAPA F v17.5 em vez do hardcode
    LOCATION_ORIGEM_ENTRADA_INDUSTR (so funcionava para INDUSTRIALIZACAO_FB_LF).
    """
    loc = LOCATION_ORIGEM_POR_DIRECAO.get(acao)
    if loc is None:
        raise ValueError(
            f'LOCATION_ORIGEM_POR_DIRECAO sem entrada para acao={acao!r}. '
            f'Validas: {sorted(LOCATION_ORIGEM_POR_DIRECAO.keys())}. '
            f'Adicionar nova direcao requer audit Odoo (PT entrada destino, '
            f'src location, fiscal_position).'
        )
    return loc

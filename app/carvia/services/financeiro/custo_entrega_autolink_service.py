# -*- coding: utf-8 -*-
"""
Service Auto-link CarviaCustoEntrega <-> CarviaFrete
=====================================================

Heuristica best-effort para popular `CarviaCustoEntrega.frete_id` quando o
CE foi criado sem frete (ex: criado por CTe direto, conciliacao bancaria,
gap operacional onde a portaria nao gerou CarviaFrete).

NUNCA bloqueia a operacao chamadora — apenas log e returns silently se
nao encontrar match.

Niveis de match (ordem de preferencia):
1. Por `operacao_id` -> `CarviaFrete.operacao_id` (1:1 esperado)
2. Por NFs da operacao -> `CarviaFrete.numeros_nfs` (CSV match)
3. Por `(transportadora, cnpj_destino)` -> CarviaFrete recente (fallback fraco)
"""

import logging
from typing import Optional

from app import db

logger = logging.getLogger(__name__)


def tentar_vincular_frete(custo, *, atualizar_operacao_id: bool = True) -> Optional[int]:
    """Tenta popular `custo.frete_id` via heuristica 3-niveis.

    Args:
        custo: instancia de `CarviaCustoEntrega` (ja na sessao, nao commitado).
        atualizar_operacao_id: se True e o frete encontrado tiver
            `operacao_id`, popula `custo.operacao_id` tambem (caso esteja vazio).

    Returns:
        frete_id (int) se vinculou, None caso contrario. NAO commita.
    """
    if not custo:
        return None

    if custo.frete_id:
        return custo.frete_id

    from app.carvia.models import CarviaFrete

    frete = None
    nivel = None

    # Nivel 1: por operacao_id
    if custo.operacao_id:
        frete = (
            CarviaFrete.query
            .filter_by(operacao_id=custo.operacao_id)
            .order_by(CarviaFrete.criado_em.desc())
            .first()
        )
        if frete:
            nivel = 'operacao_id'

    # Nivel 2: por NFs da operacao -> CarviaFrete.numeros_nfs (CSV)
    if not frete and custo.operacao_id:
        from app.carvia.models import CarviaNf, CarviaOperacaoNf

        nf_numeros = (
            db.session.query(CarviaNf.numero_nf)
            .join(CarviaOperacaoNf, CarviaOperacaoNf.nf_id == CarviaNf.id)
            .filter(CarviaOperacaoNf.operacao_id == custo.operacao_id)
            .all()
        )
        for (numero_nf,) in nf_numeros:
            if not numero_nf:
                continue
            f = (
                CarviaFrete.query
                .filter(
                    db.or_(
                        CarviaFrete.numeros_nfs == numero_nf,
                        CarviaFrete.numeros_nfs.like(f"{numero_nf},%"),
                        CarviaFrete.numeros_nfs.like(f"%,{numero_nf},%"),
                        CarviaFrete.numeros_nfs.like(f"%,{numero_nf}"),
                    )
                )
                .order_by(CarviaFrete.criado_em.desc())
                .first()
            )
            if f:
                frete = f
                nivel = f'nf:{numero_nf}'
                break

    # Nivel 3: (transportadora, cnpj_destino) — fallback fraco
    # Usa transportadora_efetiva do CE; se vazio, nao da pra tentar.
    if not frete and custo.transportadora_id and custo.fornecedor_cnpj:
        frete = (
            CarviaFrete.query
            .filter(
                CarviaFrete.transportadora_id == custo.transportadora_id,
                CarviaFrete.cnpj_destino == custo.fornecedor_cnpj,
            )
            .order_by(CarviaFrete.criado_em.desc())
            .first()
        )
        if frete:
            nivel = 'transp+cnpj_dest'

    if not frete:
        logger.info(
            'autolink_frete: nenhum CarviaFrete encontrado para CE=%s '
            '(operacao=%s, transp=%s, cnpj_dest=%s)',
            getattr(custo, 'numero_custo', custo.id),
            custo.operacao_id, custo.transportadora_id, custo.fornecedor_cnpj,
        )
        return None

    custo.frete_id = frete.id
    if atualizar_operacao_id and not custo.operacao_id and frete.operacao_id:
        custo.operacao_id = frete.operacao_id

    logger.info(
        'autolink_frete: CE=%s vinculado a CarviaFrete #%d (nivel=%s)',
        getattr(custo, 'numero_custo', custo.id), frete.id, nivel,
    )
    return frete.id

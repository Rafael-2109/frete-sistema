"""Retroatividade ao resolver HoraModeloPendente.

Quando uma pendencia eh resolvida (vincular ou criar novo modelo), os
registros que ficaram com modelo_id=NULL OU sem HoraMoto criada precisam
ser corrigidos retroativamente:

  1. hora_pedido_item.modelo_id IS NULL com modelo_texto bate em
     pendencia.nome_observado -> preencher modelo_id.

  2. hora_nf_entrada_item.modelo_texto_original = nome_observado e
     numero_chassi NAO esta em hora_moto -> criar HoraMoto agora
     (modelo_id=canonico, cor=texto_original ou 'NAO_INFORMADA').

  3. hora_venda_divergencia tipo=MODELO_PENDENTE com chassi citado em
     detalhe -> resolver (status=resolvida).

Decisao do dono: SIM, retroatividade automatica ao resolver pendencia.
Operador nao precisa rodar nada manualmente — eh atomico junto da
resolucao.

Ver `app/hora/CLAUDE.md` secao "Unificacao de modelos -> retroatividade".
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func

from app import db
from app.hora.models import (
    HoraModelo,
    HoraMoto,
    HoraNfEntradaItem,
    HoraVendaDivergencia,
)

logger = logging.getLogger(__name__)


def propagar_resolucao(
    nome_observado: str,
    modelo_canonico_id: int,
    *,
    operador: Optional[str] = None,
) -> dict:
    """Aplica retroatividade. Idempotente — pode rodar 2x sem efeito.

    Returns dict com contadores:
        pedido_itens_atualizados, motos_criadas, divergencias_resolvidas.
    """
    canonico = HoraModelo.query.get(modelo_canonico_id)
    if not canonico:
        raise ValueError(f'Modelo canonico {modelo_canonico_id} nao encontrado')

    nome_upper = nome_observado.strip().upper()
    if not nome_upper:
        return {
            'pedido_itens_atualizados': 0,
            'motos_criadas': 0,
            'divergencias_resolvidas': 0,
        }

    contadores = {
        'pedido_itens_atualizados': 0,
        'motos_criadas': 0,
        'divergencias_resolvidas': 0,
    }

    # 1. hora_pedido_item: nao temos `modelo_texto_original` armazenado,
    # entao nao da pra correlacionar item-pendencia por SQL retroativo.
    # Decisao: nao corrige aqui — operador edita item manualmente via
    # /hora/pedidos/<id> apos resolver pendencia. Caso futuro queira
    # automatizar, adicionar coluna `modelo_texto_original` em
    # hora_pedido_item espelhando hora_nf_entrada_item.

    # 2. hora_nf_entrada_item: modelo_texto_original bate, chassi sem moto
    itens_nf = (
        HoraNfEntradaItem.query
        .filter(func.upper(HoraNfEntradaItem.modelo_texto_original) == nome_upper)
        .filter(HoraNfEntradaItem.numero_chassi.isnot(None))
        .all()
    )
    for nf_item in itens_nf:
        chassi = (nf_item.numero_chassi or '').strip().upper()
        if not chassi:
            continue
        existente = HoraMoto.query.get(chassi)
        if existente:
            # Moto ja existe — pulamos (nao alteramos identidade imutavel,
            # mesmo que aponte para outro modelo). O merge_service trata
            # casos de re-apontamento de modelo.
            continue
        cor_final = (
            (nf_item.cor_texto_original or '').strip().upper()
            or 'NAO_INFORMADA'
        )
        moto = HoraMoto(
            numero_chassi=chassi,
            modelo_id=modelo_canonico_id,
            cor=cor_final,
            numero_motor=(nf_item.numero_motor_texto_original or None),
            criado_por=operador,
        )
        db.session.add(moto)
        contadores['motos_criadas'] += 1
        logger.info(
            'Retroatividade: HoraMoto criada chassi=%s modelo_id=%s '
            '(via NF item %s)',
            chassi, modelo_canonico_id, nf_item.id,
        )

    # 3. hora_venda_divergencia: divergencias MODELO_PENDENTE de chassis que
    # agora tem HoraMoto criada (acabou de criar acima OU ja existia) sao
    # marcadas como resolvidas automaticamente.
    chassis_com_moto = (
        db.session.query(HoraNfEntradaItem.numero_chassi)
        .filter(func.upper(HoraNfEntradaItem.modelo_texto_original) == nome_upper)
        .filter(HoraNfEntradaItem.numero_chassi.isnot(None))
        .all()
    )
    chassis_set = {row.numero_chassi for row in chassis_com_moto if row.numero_chassi}
    if chassis_set:
        from app.utils.timezone import agora_utc_naive
        divergencias = (
            HoraVendaDivergencia.query
            .filter(HoraVendaDivergencia.tipo == 'MODELO_PENDENTE')
            .filter(HoraVendaDivergencia.numero_chassi.in_(chassis_set))
            .filter(HoraVendaDivergencia.resolvida_em.is_(None))
            .all()
        )
        for d in divergencias:
            d.resolvida_em = agora_utc_naive()
            d.resolvida_por = (operador or 'sistema')
            contadores['divergencias_resolvidas'] += 1
            logger.info(
                'Retroatividade: divergencia MODELO_PENDENTE resolvida '
                '(venda=%s chassi=%s)', d.venda_id, d.numero_chassi,
            )

    db.session.flush()
    return contadores

"""Disponibilizar: MONTADA → DISPONIVEL.
Reverter: DISPONIVEL → MONTADA via REVERTIDA_PARA_MONTADA (motivo obrigatório ≥3 chars).
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from sqlalchemy.orm import joinedload

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiMotoEvento,
    EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_REVERTIDA_PARA_MONTADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


class DisponibilizarValidationError(Exception):
    pass


def disponibilizar(chassi: str, operador_id: int) -> Dict[str, Any]:
    """Apenas se status efetivo é MONTADA ou REVERTIDA_PARA_MONTADA."""
    chassi_norm = chassi.strip().upper()
    if not chassi_norm:
        raise DisponibilizarValidationError('Chassi vazio')

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).first()
    if not moto:
        raise DisponibilizarValidationError(f'Chassi {chassi_norm} não cadastrado')

    status = status_efetivo(chassi_norm)
    if status not in (EVENTO_MONTADA, EVENTO_REVERTIDA_PARA_MONTADA):
        raise DisponibilizarValidationError(
            f'Chassi {chassi_norm} está em {status}, esperado MONTADA ou REVERTIDA_PARA_MONTADA. '
            'Resolva pendência se houver.'
        )

    ev = emitir_evento(chassi_norm, EVENTO_DISPONIVEL, operador_id=operador_id)
    db.session.commit()
    return {
        'evento_id': ev.id, 'chassi': chassi_norm, 'tipo': EVENTO_DISPONIVEL,
        'modelo_id': moto.modelo_id, 'cor': moto.cor,
    }


def reverter_para_montada(
    chassi: str, motivo: str, operador_id: int,
) -> Dict[str, Any]:
    """DISPONIVEL → MONTADA com motivo obrigatório.

    Emite REVERTIDA_PARA_MONTADA (status efetivo final = REVERTIDA_PARA_MONTADA,
    que NÃO está em EVENTOS_VALIDOS_PARA_DISPONIBILIZAR — então a moto precisa
    de NOVA disponibilização).

    NOTA do design: a sequência é Disponivel → REVERTIDA_PARA_MONTADA. Como
    REVERTIDA_PARA_MONTADA NÃO é MONTADA puro, mas semanticamente a moto está
    "montada de novo", o `disponibilizar()` aceita tanto MONTADA quanto
    REVERTIDA_PARA_MONTADA como pré-condição.
    """
    chassi_norm = chassi.strip().upper()
    if not motivo or len(motivo.strip()) < 3:
        raise DisponibilizarValidationError('Motivo obrigatório (≥3 chars)')

    status = status_efetivo(chassi_norm)
    if status != EVENTO_DISPONIVEL:
        raise DisponibilizarValidationError(
            f'Chassi {chassi_norm} está em {status}, esperado DISPONIVEL'
        )

    ultimo_disp = (
        AssaiMotoEvento.query
        .filter_by(chassi=chassi_norm, tipo=EVENTO_DISPONIVEL)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .first()
    )
    ev = emitir_evento(
        chassi_norm, EVENTO_REVERTIDA_PARA_MONTADA,
        operador_id=operador_id,
        observacao=motivo.strip(),
        dados_extras={
            'motivo': motivo.strip(),
            'evento_revertido_id': ultimo_disp.id if ultimo_disp else None,
        },
    )
    db.session.commit()
    return {
        'evento_id': ev.id, 'chassi': chassi_norm,
        'tipo': EVENTO_REVERTIDA_PARA_MONTADA,
    }


def historico_3_ultimas_disponibilizacoes() -> list:
    """3 últimos eventos DISPONIVEL globais com info do chassi/modelo/cor.

    Filtra apenas as que ainda são "DISPONIVEL ativo" (não foram revertidas)
    para que o botão Reverter faça sentido.
    """
    eventos = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter_by(tipo=EVENTO_DISPONIVEL)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .limit(20)  # pega 20, filtra os 3 ainda válidos
        .all()
    )

    enriched = []
    for ev in eventos:
        if status_efetivo(ev.chassi) != EVENTO_DISPONIVEL:
            continue  # já foi revertida ou separada
        moto = AssaiMoto.query.filter_by(chassi=ev.chassi).first()
        enriched.append({
            'evento_id': ev.id, 'chassi': ev.chassi,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'cor': moto.cor if moto else '-',
            'ocorrido_em': ev.ocorrido_em,
            'operador_nome': ev.operador.nome if ev.operador else '-',
        })
        if len(enriched) >= 3:
            break
    return enriched

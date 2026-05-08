"""Montagem da moto: ESTOQUE → MONTADA ou ESTOQUE → PENDENTE.

PENDENTE bloqueia transição para DISPONIVEL até evento PENDENCIA_RESOLVIDA.

Resolução de pendência: cria evento PENDENCIA_RESOLVIDA + (via service) MONTADA novo,
de modo que `status_efetivo` volte a MONTADA antes de poder DISPONIBILIZAR.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from app import db
from app.motos_assai.models import (
    AssaiMoto, EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
    EVENTO_PENDENCIA_RESOLVIDA,
)
from app.motos_assai.services.moto_evento_service import (
    emitir_evento, status_efetivo, ultimo_evento,
)


class MontagemValidationError(Exception):
    pass


def registrar_montagem(
    chassi: str,
    pendencia: bool,
    descricao_pendencia: Optional[str],
    chassi_doador: Optional[str],
    operador_id: int,
) -> Dict[str, Any]:
    """Registra montagem.

    - pendencia=False → emite MONTADA
    - pendencia=True  → emite PENDENTE com descrição obrigatória ≥3 chars
    """
    chassi_norm = chassi.strip().upper()
    if not chassi_norm:
        raise MontagemValidationError('Chassi vazio')

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).first()
    if not moto:
        raise MontagemValidationError(
            f'Chassi {chassi_norm} não está no estoque (faça recebimento primeiro)'
        )

    status = status_efetivo(chassi_norm)
    if status != EVENTO_ESTOQUE:
        raise MontagemValidationError(
            f'Chassi {chassi_norm} está em status {status}, esperado ESTOQUE'
        )

    if pendencia:
        if not descricao_pendencia or len(descricao_pendencia.strip()) < 3:
            raise MontagemValidationError(
                'Descrição de pendência obrigatória (≥3 caracteres)'
            )
        ev = emitir_evento(
            chassi_norm, EVENTO_PENDENTE,
            operador_id=operador_id,
            observacao=descricao_pendencia.strip(),
            dados_extras={
                'descricao': descricao_pendencia.strip(),
                'chassi_doador': (chassi_doador or '').strip().upper() or None,
            },
        )
    else:
        ev = emitir_evento(chassi_norm, EVENTO_MONTADA, operador_id=operador_id)

    db.session.commit()
    return {
        'evento_id': ev.id, 'chassi': chassi_norm, 'tipo': ev.tipo,
        'modelo_id': moto.modelo_id, 'cor': moto.cor,
    }


def resolver_pendencia(
    chassi: str, descricao_resolucao: str, operador_id: int,
) -> Dict[str, Any]:
    """PENDENTE → MONTADA via PENDENCIA_RESOLVIDA + MONTADA.

    Sequência de eventos: ... → PENDENTE → PENDENCIA_RESOLVIDA → MONTADA
    O `status_efetivo` final = MONTADA.
    """
    chassi_norm = chassi.strip().upper()
    status = status_efetivo(chassi_norm)
    if status != EVENTO_PENDENTE:
        raise MontagemValidationError(
            f'Chassi {chassi_norm} não está PENDENTE (está {status})'
        )

    if not descricao_resolucao or len(descricao_resolucao.strip()) < 3:
        raise MontagemValidationError('Descrição da resolução obrigatória (≥3 chars)')

    emitir_evento(
        chassi_norm, EVENTO_PENDENCIA_RESOLVIDA,
        operador_id=operador_id,
        observacao=descricao_resolucao.strip(),
    )
    ev_montada = emitir_evento(chassi_norm, EVENTO_MONTADA, operador_id=operador_id)

    db.session.commit()
    return {'evento_id': ev_montada.id, 'chassi': chassi_norm, 'tipo': EVENTO_MONTADA}


def historico_3_ultimas_montagens() -> list:
    """3 últimos eventos MONTADA globais (com info do chassi/modelo/cor)."""
    from sqlalchemy.orm import joinedload
    from app.motos_assai.models import AssaiMotoEvento

    eventos = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter_by(tipo=EVENTO_MONTADA)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .limit(3)
        .all()
    )

    enriched = []
    for ev in eventos:
        moto = AssaiMoto.query.filter_by(chassi=ev.chassi).first()
        enriched.append({
            'evento_id': ev.id,
            'chassi': ev.chassi,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'cor': moto.cor if moto else '-',
            'ocorrido_em': ev.ocorrido_em,
            'operador_nome': ev.operador.nome if ev.operador else '-',
        })
    return enriched

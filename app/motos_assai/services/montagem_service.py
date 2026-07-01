"""Montagem da moto: ESTOQUE → MONTADA ou ESTOQUE → PENDENTE.

PENDENTE bloqueia transição para DISPONIVEL até evento PENDENCIA_RESOLVIDA.

A resolução de pendência mora em `pendencia_service` (por ficha/pendencia_id):
o gate físico (última ficha física aberta → PENDENCIA_RESOLVIDA + MONTADA) é
responsabilidade de `pendencia_service.resolver_pendencia`, não deste módulo.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from app import db
from app.motos_assai.models import (
    AssaiMoto, EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
    EVENTO_DISPONIVEL, EVENTO_REVERTIDA_PARA_MONTADA,
    EVENTO_SEPARADA, EVENTO_CARREGADA, EVENTO_FATURADA,
)
from app.motos_assai.services.moto_evento_service import (
    emitir_evento, status_efetivo,
)


class MontagemValidationError(Exception):
    pass


# Alias publico (mantido para callers internos / docstrings de skill).
MontagemError = MontagemValidationError


def _msg_a6_por_status_montagem(chassi_norm: str, status: Optional[str], esperado: str) -> str:
    """A6: dispatch de mensagens especificas para registrar_montagem.

    Retorna orientacao especifica para DISPONIVEL/SEPARADA/CARREGADA/FATURADA;
    fallback generico para estados nao mapeados (ex: MONTADA, ESTOQUE quando
    esperado PENDENTE) preserva o motivo original.
    """
    msgs = {
        EVENTO_DISPONIVEL: f'Chassi {chassi_norm} ja esta DISPONIVEL.',
        EVENTO_SEPARADA: (
            f'Chassi {chassi_norm} esta SEPARADA. '
            'Para reverter, cancele a Sep ou desfaca o item.'
        ),
        EVENTO_CARREGADA: (
            f'Chassi {chassi_norm} esta CARREGADA. '
            'Para reverter, cancele o Carregamento ou substitua o chassi (cross-loja).'
        ),
        EVENTO_FATURADA: (
            f'Chassi {chassi_norm} esta FATURADA. '
            'Para reverter, cancele a NF (cancelar_nf_qpa).'
        ),
    }
    return msgs.get(
        status,
        f'Chassi {chassi_norm} está em status {status}, esperado {esperado}',
    )


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
        # A6: dispatch de mensagens especificas (CARREGADA/SEPARADA/FATURADA/DISPONIVEL)
        raise MontagemValidationError(
            _msg_a6_por_status_montagem(chassi_norm, status, esperado='ESTOQUE')
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
        # Spec 1: toda PENDENTE fisica nasce com uma ficha assai_pendencia.
        # Categoria INDETERMINADA (reclassificada na UI do Spec 2). Passa o
        # evento_pendente_id JA emitido -> abrir_pendencia nao emite 2o PENDENTE.
        from app.motos_assai.services import pendencia_service
        from app.motos_assai.models import (
            PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
        )
        doador_norm = (chassi_doador or '').strip().upper() or None
        pendencia_service.abrir_pendencia(
            chassi=chassi_norm,
            categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO,
            descricao=descricao_pendencia.strip(),
            evento_pendente_id=ev.id,
            operador_id=operador_id,
            detalhes={'chassi_doador': doador_norm} if doador_norm else None,
        )
    else:
        ev = emitir_evento(chassi_norm, EVENTO_MONTADA, operador_id=operador_id)

    db.session.commit()
    return {
        'evento_id': ev.id, 'chassi': chassi_norm, 'tipo': ev.tipo,
        'modelo_id': moto.modelo_id, 'cor': moto.cor,
    }


# Estados a partir dos quais o operador pode marcar uma moto como PENDENTE
# (defeito descoberto depois da montagem). ESTOQUE usa o fluxo normal de
# montagem (registrar_montagem(pendencia=True)); CARREGADA/FATURADA exigem
# reverter o carregamento/NF antes.
ESTADOS_PERMITEM_ENVIAR_PENDENCIA = {
    EVENTO_MONTADA, EVENTO_REVERTIDA_PARA_MONTADA,
    EVENTO_DISPONIVEL, EVENTO_SEPARADA,
}


def _msg_bloqueio_pendencia(chassi_norm: str, status) -> str:
    """Mensagem específica quando o chassi NÃO pode ir para PENDENTE."""
    msgs = {
        EVENTO_PENDENTE: f'Chassi {chassi_norm} já está PENDENTE.',
        EVENTO_ESTOQUE: (
            f'Chassi {chassi_norm} está em ESTOQUE. '
            'Use a tela de Montagem (marque "Pendência de peça") para registrar.'
        ),
        EVENTO_CARREGADA: (
            f'Chassi {chassi_norm} está CARREGADA. '
            'Cancele o Carregamento antes de enviar para pendência.'
        ),
        EVENTO_FATURADA: (
            f'Chassi {chassi_norm} está FATURADA. '
            'Cancele a NF (cancelar_nf_qpa) antes de enviar para pendência.'
        ),
    }
    return msgs.get(
        status,
        f'Chassi {chassi_norm} está em status {status or "sem eventos"} — '
        'não é possível enviar para pendência a partir daqui.',
    )


def enviar_para_pendencia(
    chassi: str,
    descricao_pendencia: Optional[str],
    chassi_doador: Optional[str],
    operador_id: int,
) -> Dict[str, Any]:
    """Marca uma moto já processada como PENDENTE (defeito descoberto depois).

    Aceita os estados MONTADA / REVERTIDA_PARA_MONTADA / DISPONIVEL / SEPARADA.
    Para SEPARADA: remove o item da separação (libera o saldo do pedido) ANTES
    de emitir PENDENTE — só se a separação estiver EM_SEPARACAO. Se a separação
    estiver FECHADA/CARREGADA, bloqueia orientando reabrir/cancelar primeiro
    (mesma regra de `desfazer_chassi`).

    Usado pelos botões "Enviar p/ Pendência" das telas Montagem, Disponibilizar
    e Separação. Descrição obrigatória (≥3 chars).
    """
    chassi_norm = (chassi or '').strip().upper()
    if not chassi_norm:
        raise MontagemValidationError('Chassi vazio')

    if not descricao_pendencia or len(descricao_pendencia.strip()) < 3:
        raise MontagemValidationError(
            'Descrição de pendência obrigatória (≥3 caracteres)'
        )

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).first()
    if not moto:
        raise MontagemValidationError(f'Chassi {chassi_norm} não cadastrado')

    status = status_efetivo(chassi_norm)
    if status not in ESTADOS_PERMITEM_ENVIAR_PENDENCIA:
        raise MontagemValidationError(_msg_bloqueio_pendencia(chassi_norm, status))

    # SEPARADA: liberar o chassi da separação (igual a desfazer_chassi, mas o
    # evento seguinte é PENDENTE em vez de DISPONIVEL).
    sep_liberada_id = None
    if status == EVENTO_SEPARADA:
        from app.motos_assai.models import (
            AssaiSeparacao, AssaiSeparacaoItem,
            SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_CANCELADA,
        )
        item = (
            AssaiSeparacaoItem.query
            .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
            .filter(
                AssaiSeparacaoItem.chassi == chassi_norm,
                AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
            )
            .first()
        )
        if item:
            sep = AssaiSeparacao.query.get(item.separacao_id)
            if sep and sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
                raise MontagemValidationError(
                    f'Chassi {chassi_norm} está na Separação #{sep.id} ({sep.status}). '
                    'Reabra (Alterar) ou cancele a separação antes de enviar '
                    'para pendência.'
                )
            sep_liberada_id = item.separacao_id
            db.session.delete(item)

    ev = emitir_evento(
        chassi_norm, EVENTO_PENDENTE,
        operador_id=operador_id,
        observacao=descricao_pendencia.strip(),
        dados_extras={
            'descricao': descricao_pendencia.strip(),
            'chassi_doador': (chassi_doador or '').strip().upper() or None,
            'origem_status': status,
            'separacao_liberada_id': sep_liberada_id,
        },
    )
    # Spec 1: abre a ficha INDETERMINADA/GALPAO reusando o PENDENTE ja emitido.
    from app.motos_assai.services import pendencia_service
    from app.motos_assai.models import (
        PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
    )
    doador_norm = (chassi_doador or '').strip().upper() or None
    pendencia_service.abrir_pendencia(
        chassi=chassi_norm,
        categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
        origem=PENDENCIA_ORIGEM_GALPAO,
        descricao=descricao_pendencia.strip(),
        evento_pendente_id=ev.id,
        operador_id=operador_id,
        detalhes={'chassi_doador': doador_norm, 'origem_status': status}
        if (doador_norm or status) else None,
    )
    db.session.commit()

    # Se removeu de separação, reprocessar NFs que mencionam o chassi (defensivo).
    if sep_liberada_id is not None:
        try:
            from app.motos_assai.services.separacao_service import (
                _hook_reprocessar_match_chassi,
            )
            _hook_reprocessar_match_chassi(
                chassi_norm, operador_id, motivo_hook='HOOK_ENVIADO_PENDENCIA',
            )
        except Exception:
            import logging as _log
            _log.getLogger(__name__).exception(
                'hook reprocessar_match (enviar_para_pendencia chassi=%s) falhou '
                '— operação principal já commitada', chassi_norm,
            )

    return {
        'evento_id': ev.id, 'chassi': chassi_norm, 'tipo': EVENTO_PENDENTE,
        'modelo_id': moto.modelo_id, 'cor': moto.cor,
        'origem_status': status, 'separacao_liberada_id': sep_liberada_id,
    }


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

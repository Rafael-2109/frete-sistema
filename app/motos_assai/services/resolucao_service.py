"""resolucao_service — orquestra a resolucao de pendencia com tratativa (Spec 2 §4.1).

Compoe os atomos do Spec 1: movimento (consumir/canibalizar) + resolver_pendencia.
add+flush SEM commit (a rota commita). NAO adiciona corrida — o gate fisico e o
advisory lock ja vivem em pendencia_service.resolver_pendencia.
"""
from app import db
from app.motos_assai.models import (
    AssaiPendencia,
    PENDENCIA_TRATATIVA_USAR_ESTOQUE, PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO,
    PENDENCIA_TRATATIVAS_VALIDAS, PENDENCIA_CATEGORIA_VENDA, EVENTO_MONTADA,
)
from app.motos_assai.services import movimento_service, pendencia_service
from app.motos_assai.services.moto_evento_service import status_efetivo

_MOVIMENTA = {PENDENCIA_TRATATIVA_USAR_ESTOQUE, PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO}


class ResolucaoError(Exception):
    """Erro de dominio da orquestracao de resolucao."""


def resolver_com_tratativa(
    *, pendencia_id, tratativa, resolucao_descricao, operador_id,
    peca_id=None, quantidade=None, chassi_doador=None, receita_unitaria=None,
) -> dict:
    if tratativa not in PENDENCIA_TRATATIVAS_VALIDAS:
        raise ResolucaoError(
            f'Tratativa invalida: {tratativa}. Validas: {sorted(PENDENCIA_TRATATIVAS_VALIDAS)}')
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        raise ResolucaoError(f'Pendencia {pendencia_id} nao encontrada.')

    # Guard de idempotencia ANTES de qualquer movimento de estoque: serializa por
    # chassi (o mesmo advisory lock reentrante de resolver_pendencia) e recusa
    # re-submit de ficha ja fechada. Sem isto, um double-submit/POST concorrente
    # grava um 2o CONSUMO/CANIBALIZACAO (o ledger e append-only) enquanto
    # resolver_pendencia vira no-op idempotente — baixando o saldo em duplicidade.
    db.session.execute(
        db.text('SELECT pg_advisory_xact_lock(hashtext(:c))'), {'c': ficha.chassi})
    db.session.refresh(ficha)
    if ficha.resolvida_em is not None or ficha.cancelada_em is not None:
        raise ResolucaoError(f'Pendencia {pendencia_id} ja esta fechada.')

    saldo_apos = None
    if tratativa in _MOVIMENTA:
        if not peca_id or quantidade is None:
            raise ResolucaoError('Tratativa exige peca_id e quantidade.')
        rec = receita_unitaria if ficha.categoria == PENDENCIA_CATEGORIA_VENDA else None
        if tratativa == PENDENCIA_TRATATIVA_USAR_ESTOQUE:
            movimento_service.consumir(
                peca_id=peca_id, quantidade=quantidade, pendencia_id=pendencia_id,
                chassi_destino=ficha.chassi, operador_id=operador_id, receita_unitaria=rec)
        else:  # USAR_OUTRA_MOTO
            if not chassi_doador:
                raise ResolucaoError('USAR_OUTRA_MOTO exige chassi_doador.')
            movimento_service.canibalizar(
                peca_id=peca_id, quantidade=quantidade, chassi_origem=chassi_doador,
                chassi_destino=ficha.chassi, pendencia_id=pendencia_id,
                operador_id=operador_id, receita_unitaria=rec)
        saldo_apos = movimento_service.saldo(peca_id)

    pendencia_service.resolver_pendencia(
        pendencia_id=pendencia_id, tratativa=tratativa,
        resolucao_descricao=resolucao_descricao, operador_id=operador_id)
    db.session.flush()

    return {
        'ok': True,
        'pendencia_id': pendencia_id,
        'tratativa': tratativa,
        'saldo_apos': saldo_apos,
        'montou': status_efetivo(ficha.chassi) == EVENTO_MONTADA,
    }

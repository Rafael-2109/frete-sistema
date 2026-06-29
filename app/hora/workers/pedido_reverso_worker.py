"""Cron da descoberta reversa HORA<->TagPlus (Fase 3, numero-walk +3).

Entry point para agendamento periodico (RQ scheduler / crontab Render, padrao
do `reconciliacao_worker.reconciliar_emissoes_job`). Descobre pedidos criados
direto no TagPlus e os replica como HoraVenda INCOMPLETO (origem TAGPLUS).

GATE: roda apenas com a flag HORA_TAGPLUS_REVERSO ligada (default OFF) — a
descoberta CRIA vendas, entao fica desligada ate o numero-walk ser validado em
PROD. Independente da flag de push/to_nfe (HORA_TAGPLUS_PUSH_PEDIDO).

Agendamento (acao de infra, nao automatica): registrar um cron (ex.: 30min)
que invoque `descobrir_e_replicar_job`, espelhando o cron de reconciliacao.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Lock anti-concorrencia: 2 execucoes do cron sobrepostas duplicariam HoraVenda
# (a checagem de idempotencia em replicar tem janela TOCTOU e tagplus_pedido_id
# NAO e' UNIQUE — PROD tem duplicatas legadas que impedem o constraint). O lock
# Redis serializa as execucoes. TTL = intervalo tipico do cron.
_LOCK_KEY = 'hora:tagplus:reverso:lock'
_LOCK_TTL = 1800  # 30min
_SEM_REDIS = object()  # sentinel: roda sem lock (assume execucao unica)


def _adquirir_lock():
    """Retorna o conn Redis se adquiriu o lock, None se ja' ha execucao ativa,
    ou _SEM_REDIS se nao ha Redis (roda sem lock)."""
    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        return _SEM_REDIS
    try:
        from redis import Redis
        conn = Redis.from_url(redis_url)
        return conn if conn.set(_LOCK_KEY, '1', nx=True, ex=_LOCK_TTL) else None
    except Exception as exc:
        logger.warning('lock reverso indisponivel (%s) — rodando sem lock.', exc)
        return _SEM_REDIS


def _liberar_lock(lock) -> None:
    if lock is _SEM_REDIS or lock is None:
        return
    try:
        lock.delete(_LOCK_KEY)
    except Exception:
        pass


def descobrir_e_replicar_job() -> dict:
    """1 ciclo da descoberta reversa. Wrapper create_app (cron / crontab).

    Retorna stats: {flag_off|lock_busy, replicados, numeros}.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.hora.services.tagplus import pedido_reverso_service as rev

        if not rev.reverso_habilitado():
            logger.info(
                'descobrir_e_replicar_job: flag HORA_TAGPLUS_REVERSO OFF — skip.'
            )
            return {'flag_off': True, 'replicados': 0, 'numeros': []}

        lock = _adquirir_lock()
        if lock is None:
            logger.warning(
                'descobrir_e_replicar_job: outra execucao em andamento (lock) — skip.'
            )
            return {'lock_busy': True, 'replicados': 0, 'numeros': []}

        try:
            from app.hora.models.tagplus import HoraTagPlusConta
            from app.hora.services.tagplus.api_client import ApiClient

            conta = HoraTagPlusConta.ativa()
            replicados = rev.descobrir_e_replicar(ApiClient(conta), conta)
            numeros = [v.tagplus_pedido_numero for v in replicados]
            logger.info('descobrir_e_replicar_job: %s replicado(s) %s', len(replicados), numeros)
            return {'flag_off': False, 'replicados': len(replicados), 'numeros': numeros}
        finally:
            _liberar_lock(lock)

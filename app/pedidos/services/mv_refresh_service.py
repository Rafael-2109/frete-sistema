"""Refresh sob demanda da materialized view `mv_pedidos`.

## Por que existe

A `lista_pedidos` (e os contadores) leem da MV `mv_pedidos` via `PedidoMV`
(`counter_service._get_model`). A MV e' refreshed a cada ciclo do scheduler
(`sincronizacao_incremental_definitiva.py` step 24.5, `SYNC_INTERVAL_MINUTES=30`).
Mudancas que precisam refletir RAPIDO na lista — caso concreto: o `local_cd` (CD
de expedicao VM/TM) propagado da Coleta CarVia para `carvia_pedidos`/`carvia_cotacoes`
(`coleta_service._propagar_local_cd_para_documentos`) — ficariam com lag de ate 1
ciclo (a edicao da coleta cai logo apos um refresh e so' aparece no proximo).

Este servico DISPARA um refresh fora do ciclo, mantendo a lista fresca.

## Design (e os porques)

- **Assincrono (RQ)**: `REFRESH MATERIALIZED VIEW CONCURRENTLY` adquire lock e
  serializa com o refresh do scheduler — NUNCA deve pendurar a request HTTP.
- **Enqueue IMEDIATO (sem `enqueue_in`)**: nenhum worker roda o RQ scheduler
  (`worker_atacadao` chama `work()` sem `with_scheduler`; `worker_render` usa
  `with_scheduler=False`), entao jobs agendados (`enqueue_in/at`) nao executam.
- **Debounce (Redis `SET NX EX`)**: uma rajada (ex.: `vincular_lote`/`marcar_coletada`
  de N NFs propaga N vezes) colapsa em 1 unico refresh. O TTL e' so' rede de
  seguranca: se o job morrer sem limpar a flag (worker down), ela expira e o
  proximo evento re-agenda.
- **Best-effort**: falha de Redis/RQ NUNCA propaga para o fluxo de negocio — o
  scheduler segue como fallback (no pior caso volta-se ao lag de ate 1 ciclo).
- **Corrida commit-vs-job**: a propagacao roda dentro da transacao do request
  (commit do route logo em seguida, em ms); o job faz `create_app()` (centenas de
  ms) antes do `REFRESH`, entao na pratica le o estado JA committado. Pior caso
  improvavel: degrada ao refresh do scheduler.
"""
import logging

logger = logging.getLogger(__name__)

# Flag de debounce no Redis (1 refresh por janela). TTL = safety se o job nao limpar.
_FLAG_DEBOUNCE = 'mv_pedidos:refresh_agendado'
_JANELA_DEBOUNCE_S = 120


def solicitar_refresh_mv_pedidos(janela_debounce_s=_JANELA_DEBOUNCE_S):
    """Agenda (assincrono + debounced + best-effort) um refresh de `mv_pedidos`.

    A 1a chamada da janela enfileira o job; as demais sao no-op (debounce).
    Retorna o Job enfileirado, ou None se ja havia um agendado / em caso de falha.
    NUNCA levanta excecao.
    """
    try:
        from app.portal.workers import get_redis_connection
        conn = get_redis_connection()
    except Exception as e:  # Redis indisponivel — scheduler segue como fallback
        logger.warning(f"refresh mv_pedidos: Redis indisponivel, pulando ({e})")
        return None

    try:
        # NX: so' a 1a propagacao da janela agenda. EX: TTL de seguranca.
        if not conn.set(_FLAG_DEBOUNCE, b'1', nx=True, ex=janela_debounce_s):
            return None  # ja ha um refresh agendado nesta janela
    except Exception as e:
        logger.warning(f"refresh mv_pedidos: debounce falhou, pulando ({e})")
        return None

    try:
        from app.portal.workers import enqueue_job
        return enqueue_job(refresh_mv_pedidos_job, queue_name='default', timeout='10m')
    except Exception as e:
        logger.warning(f"refresh mv_pedidos: enqueue falhou ({e})")
        # Libera a flag para a proxima propagacao poder re-agendar (nao espera o TTL).
        try:
            conn.delete(_FLAG_DEBOUNCE)
        except Exception:
            pass
        return None


def refresh_mv_pedidos_job():
    """Entrypoint do job RQ — roda no worker, com app context proprio.

    Padrao do projeto (ver `app/carvia/workers/ssw_cte_jobs.py`): o worker nao faz
    push de app context global, entao o job cria o seu.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        # Limpa a flag LOGO no inicio: propagacoes que cheguem durante o refresh
        # ja podem agendar a PROXIMA janela (nao perde atualizacoes tardias).
        try:
            from app.portal.workers import get_redis_connection
            get_redis_connection().delete(_FLAG_DEBOUNCE)
        except Exception:
            pass
        return refresh_mv_pedidos()


def refresh_mv_pedidos():
    """Executa `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pedidos`.

    Mesmo padrao do scheduler (step 24.5): isola a conexao antes do refresh.
    Pressupoe app context ativo. Retorna True em sucesso, False em falha.
    """
    from app import db
    from sqlalchemy import text
    try:
        db.session.remove()
        db.engine.dispose()
        db.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pedidos"))
        db.session.commit()
        logger.info("mv_pedidos refreshed OK (sob demanda)")
        return True
    except Exception as e:
        # Mesma severidade do scheduler: MV defasada serve lista desatualizada.
        logger.error(f"Refresh mv_pedidos (sob demanda) FALHOU: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return False

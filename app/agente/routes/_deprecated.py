"""
Scaffolding de validacao async migration (Fases 0-3).

Rotas de desenvolvimento/teste — sem uso em producao.
Candidatas a remocao em limpeza futura.
"""

import asyncio
import logging

from flask import jsonify, Response
from flask_login import login_required

from app.agente.routes import agente_bp
from app.agente.routes._helpers import _sse_event
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/api/async-health', methods=['GET'])
@login_required
async def async_health():
    """
    Fase 0: Valida que Flask executa async routes corretamente neste ambiente.

    Se retornar {"async": true}, Flask 3.1 + Gunicorn gthread aceita async views.
    Se falhar: async routes NÃO funcionam → Fase 3 inviável.
    """
    import asyncio as _asyncio
    await _asyncio.sleep(0.01)  # Confirma que await funciona
    return jsonify({
        'async': True,
        'event_loop': str(_asyncio.get_running_loop()),
        'timestamp': agora_utc_naive().isoformat(),
    })


@agente_bp.route('/api/contextvar-test', methods=['GET'])
@login_required
def contextvar_test():
    """
    Fase 0: Valida que ContextVar funciona no MESMO fluxo de threading/asyncio usado pelo SDK.

    Simula EXATAMENTE o padrão atual:
    1. Thread daemon + asyncio.run() (como _stream_chat_response faz)
    2. Seta ContextVar DENTRO do async (como set_current_session_id faz)
    3. Lê ContextVar de um callback async (como can_use_tool faz)
    4. Compara com threading.local para confirmar equivalência
    """
    import threading
    from contextvars import ContextVar
    from queue import Queue

    result_queue = Queue()
    test_cv: ContextVar[str] = ContextVar('_test_cv', default='NOT_SET')
    test_tl = threading.local()

    def run_in_daemon():
        async def async_test():
            # Simula set_current_session_id (como routes.py:442)
            test_cv.set('CV_VALUE_123')
            test_tl.value = 'TL_VALUE_123'

            # Simula can_use_tool sendo chamado como callback
            async def simulated_callback():
                cv_read = test_cv.get()
                tl_read = getattr(test_tl, 'value', 'NOT_SET')
                return cv_read, tl_read

            # Teste 1: await direto (como SDK provavelmente faz)
            cv1, tl1 = await simulated_callback()

            # Teste 2: via asyncio.create_task (se SDK criar task)
            task = asyncio.create_task(simulated_callback())
            cv2, tl2 = await task

            # Teste 3: via loop.run_in_executor (se SDK usar thread pool)
            loop = asyncio.get_running_loop()

            def sync_callback():
                cv_r = test_cv.get()
                tl_r = getattr(test_tl, 'value', 'NOT_SET')
                return cv_r, tl_r

            cv3, tl3 = await loop.run_in_executor(None, sync_callback)

            result_queue.put({
                'await_direct': {'contextvar': cv1, 'threading_local': tl1},
                'create_task': {'contextvar': cv2, 'threading_local': tl2},
                'run_in_executor': {'contextvar': cv3, 'threading_local': tl3},
                'thread_name': threading.current_thread().name,
                'thread_id': threading.get_ident(),
            })

        asyncio.run(async_test())

    thread = threading.Thread(target=run_in_daemon, daemon=True)
    thread.start()
    thread.join(timeout=5.0)

    if result_queue.empty():
        return jsonify({'error': 'Thread timeout — teste falhou'}), 500

    results = result_queue.get()

    # Análise
    # NOTA: run_in_executor usa OUTRA thread — ContextVar NÃO propaga para threads filhas
    # (comportamento documentado em PEP 567). O SDK NÃO usa run_in_executor para can_use_tool.
    # Os cenários relevantes são await_direct e create_task.
    cv_await = results['await_direct']['contextvar'] == 'CV_VALUE_123'
    cv_task = results['create_task']['contextvar'] == 'CV_VALUE_123'
    cv_executor = results['run_in_executor']['contextvar'] == 'CV_VALUE_123'

    all_cv_ok = cv_await and cv_task  # Cenários relevantes para o SDK
    all_tl_ok = all(
        results[k]['threading_local'] == 'TL_VALUE_123'
        for k in ['await_direct', 'create_task']
    )

    return jsonify({
        'contextvar_works_everywhere': all_cv_ok,
        'contextvar_executor_propagates': cv_executor,  # Informativo (não bloqueia)
        'threading_local_works_same_thread': all_tl_ok,
        'details': results,
        'conclusion': (
            'ContextVar é seguro para substituir threading.local'
            if all_cv_ok else
            'ATENÇÃO: ContextVar NÃO funciona em algum cenário — NÃO migrar'
        ),
        'nota': (
            'run_in_executor usa thread separada — ContextVar NÃO propaga '
            '(PEP 567). SDK usa await direto, não executor.'
        ),
    })


@agente_bp.route('/api/async-stream-test', methods=['GET'])
@login_required
async def async_stream_test():
    """
    Fase 3 (Protótipo): Testa async generator SSE com Flask 3.1 + Gunicorn gthread.

    Simula o padrão da Fase 3 completa com heartbeats + delay + eventos.
    NÃO modifica a rota /api/chat — endpoint isolado para validação.
    """
    from app.agente.config.feature_flags import USE_ASYNC_STREAMING
    if not USE_ASYNC_STREAMING:
        return jsonify({'error': 'ASYNC_STREAMING não habilitado'}), 400

    async def generate():
        import asyncio as _asyncio
        yield _sse_event('start', {'message': 'Protótipo async SSE'})

        for i in range(5):
            await _asyncio.sleep(2)  # Simula SDK event delay
            yield _sse_event('text', {'content': f'Evento {i+1}/5'})

            # Heartbeat inline
            yield _sse_event('heartbeat', {'timestamp': agora_utc_naive().isoformat()})

        yield _sse_event('done', {'message': 'Protótipo concluído'})

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )

"""
API de Workers para análise de ruptura - Camada adicional
Trabalha em conjunto com ruptura_api.py sem modificá-lo
"""

from flask import jsonify, request, Response
from app.carteira.main_routes import carteira_bp
from app import db
from redis import Redis
from rq import Queue
import json
import os
import uuid
import logging

logger = logging.getLogger(__name__)

# Conectar ao Redis
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = Redis.from_url(redis_url)

# Criar 2 filas para 2 workers
queue_worker1 = Queue('ruptura_worker1', connection=redis_conn)
queue_worker2 = Queue('ruptura_worker2', connection=redis_conn)

# TTL do cache = 15 segundos conforme solicitado
CACHE_TTL = 15

@carteira_bp.route('/api/ruptura/worker/iniciar-processamento', methods=['POST'])
def iniciar_processamento_workers():
    """
    Recebe lista de pedidos e distribui entre 2 workers
    """
    try:
        data = request.get_json()
        pedidos = data.get('pedidos', [])
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not pedidos:
            return jsonify({'success': False, 'error': 'Lista vazia'}), 400
        
        logger.info(f"📦 Iniciando processamento de {len(pedidos)} pedidos com 2 workers")
        
        # Dividir pedidos em lotes de 20
        tamanho_lote = 20
        lotes = [pedidos[i:i + tamanho_lote] for i in range(0, len(pedidos), tamanho_lote)]
        
        # Distribuir lotes entre os 2 workers
        jobs_info = []
        for i, lote in enumerate(lotes):
            # Alternar entre worker1 e worker2
            queue = queue_worker1 if i % 2 == 0 else queue_worker2
            worker_id = 1 if i % 2 == 0 else 2
            
            job = queue.enqueue(
                'app.portal.workers.ruptura_worker_novo.processar_lote_com_publicacao',
                args=(lote, session_id, worker_id, i),
                job_timeout='5m',
                result_ttl=300  # Resultado fica 5 min
            )
            
            jobs_info.append({
                'job_id': job.id,
                'worker': worker_id,
                'lote': i,
                'pedidos': len(lote)
            })
            
            logger.info(f"  Lote {i} com {len(lote)} pedidos -> Worker {worker_id}")
        
        # Salvar informação da sessão no Redis
        session_info = {
            'session_id': session_id,
            'total_pedidos': len(pedidos),
            'total_lotes': len(lotes),
            'jobs': jobs_info,
            'status': 'processando'
        }
        redis_conn.setex(
            f'ruptura:session:{session_id}:info',
            300,  # 5 minutos
            json.dumps(session_info)
        )
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'total_pedidos': len(pedidos),
            'lotes': len(lotes),
            'workers': 2,
            'jobs': jobs_info
        })
        
    except Exception as e:
        logger.error(f"Erro ao iniciar processamento: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@carteira_bp.route('/api/ruptura/worker/buscar-resultados/<session_id>', methods=['GET'])
def buscar_resultados_workers(session_id):
    """
    Busca resultados processados pelos workers
    Retorna apenas os novos desde a última busca
    """
    try:
        # Pegar o offset da query string (quantos já foram retornados)
        offset = request.args.get('offset', 0, type=int)
        
        # Buscar todos os resultados da sessão
        pattern = f'ruptura:resultado:{session_id}:*'
        keys = redis_conn.keys(pattern)
        
        resultados = []
        indices_processados = []
        
        for key in sorted(keys):  # Ordenar para manter ordem
            # Extrair índice do pedido da chave
            partes = key.decode('utf-8').split(':')
            if len(partes) >= 4:
                try:
                    indice = int(partes[3])
                    if indice >= offset:  # Só retornar novos
                        resultado_json = redis_conn.get(key)
                        if resultado_json:
                            resultado = json.loads(resultado_json)
                            resultados.append(resultado)
                            indices_processados.append(indice)
                except (ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"Erro ao processar chave {key}: {e}")
        
        # Verificar status da sessão
        session_info_key = f'ruptura:session:{session_id}:info'
        session_info_json = redis_conn.get(session_info_key)
        
        total_esperado = 0
        if session_info_json:
            session_info = json.loads(session_info_json)
            total_esperado = session_info.get('total_pedidos', 0)
        
        # Determinar se processamento está completo
        total_processados = len(keys)
        completo = total_processados >= total_esperado and total_esperado > 0
        
        # Se completo, marcar sessão
        if completo:
            redis_conn.setex(
                f'ruptura:session:{session_id}:completo',
                60,  # 1 minuto
                '1'
            )
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'resultados': resultados,
            'offset_anterior': offset,
            'offset_novo': offset + len(resultados),
            'novos_resultados': len(resultados),
            'total_processados': total_processados,
            'total_esperado': total_esperado,
            'completo': completo,
            'progresso': (total_processados / total_esperado * 100) if total_esperado > 0 else 0
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar resultados: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@carteira_bp.route('/api/ruptura/worker/status/<session_id>', methods=['GET'])
def status_processamento_workers(session_id):
    """
    Retorna status do processamento
    """
    try:
        # Buscar informação da sessão
        session_info_json = redis_conn.get(f'ruptura:session:{session_id}:info')
        if not session_info_json:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404
        
        session_info = json.loads(session_info_json)
        
        # Contar resultados processados
        pattern = f'ruptura:resultado:{session_id}:*'
        total_processados = len(redis_conn.keys(pattern))
        
        # Verificar se está completo
        completo = redis_conn.exists(f'ruptura:session:{session_id}:completo')
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'total_pedidos': session_info.get('total_pedidos', 0),
            'total_lotes': session_info.get('total_lotes', 0),
            'total_processados': total_processados,
            'completo': bool(completo),
            'progresso': (total_processados / session_info.get('total_pedidos', 1) * 100),
            'jobs': session_info.get('jobs', [])
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@carteira_bp.route('/api/ruptura/worker/limpar-cache', methods=['POST'])
def limpar_cache_workers():
    """
    Limpa cache de uma sessão específica ou todo o cache
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        if session_id:
            # Limpar sessão específica
            pattern = f'ruptura:*{session_id}*'
            keys = redis_conn.keys(pattern)
            if keys:
                redis_conn.delete(*keys)
                logger.info(f"Cache limpo para sessão {session_id}: {len(keys)} chaves")
        else:
            # Limpar todo cache de ruptura
            pattern = 'ruptura:*'
            keys = redis_conn.keys(pattern)
            if keys:
                redis_conn.delete(*keys)
                logger.info(f"Todo cache de ruptura limpo: {len(keys)} chaves")
        
        return jsonify({
            'success': True,
            'chaves_removidas': len(keys) if keys else 0
        })
        
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
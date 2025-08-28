"""
Rota para verificação em lote de protocolos no portal
"""

from flask import jsonify, request
from flask_login import login_required
from app.portal import portal_bp
from app import redis_client, db
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
import json
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@portal_bp.route('/api/verificar-agendas-lote', methods=['POST'])
@login_required
def verificar_agendas_lote():
    """
    Enfileira protocolos para verificação em lote no portal
    Processa até 50 protocolos por vez
    """
    try:
        data = request.json
        protocolos = data.get('protocolos', [])
        portal = data.get('portal', 'atacadao')
        
        if not protocolos:
            return jsonify({
                'success': False,
                'message': 'Nenhum protocolo fornecido'
            }), 400
        
        # Limitar a 50 protocolos
        protocolos_limitados = protocolos[:100]
        
        # Criar task ID única
        task_id = f"verificacao_lote_{uuid.uuid4().hex[:8]}"
        
        # Preparar dados para Redis
        task_data = {
            'task_id': task_id,
            'portal': portal,
            'protocolos': protocolos_limitados,
            'total': len(protocolos_limitados),
            'processados': 0,
            'atualizados': 0,
            'status': 'pending',
            'criado_em': datetime.now().isoformat(),
            'resultados': []
        }
        
        # Salvar no Redis com TTL de 1 hora
        redis_client.setex(
            f"task:{task_id}",
            3600,  # 1 hora
            json.dumps(task_data)
        )
        
        # Enfileirar cada protocolo individualmente para processamento
        for protocolo_info in protocolos_limitados:
            job_data = {
                'task_id': task_id,
                'protocolo': protocolo_info['protocolo'],
                'lote_id': protocolo_info.get('lote_id'),
                'num_pedido': protocolo_info.get('num_pedido'),
                'portal': portal
            }
            
            # Adicionar à fila de verificação
            redis_client.lpush('queue:verificacao_protocolo', json.dumps(job_data))
        
        logger.info(f"Enfileirado {len(protocolos_limitados)} protocolos para verificação. Task ID: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'total_enfileirados': len(protocolos_limitados),
            'message': f'{len(protocolos_limitados)} protocolos enfileirados para verificação'
        })
        
    except Exception as e:
        logger.error(f"Erro ao enfileirar protocolos: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao processar solicitação: {str(e)}'
        }), 500


@portal_bp.route('/api/status-verificacao/<task_id>', methods=['GET'])
@login_required
def status_verificacao(task_id):
    """
    Retorna o status de uma verificação em lote
    """
    try:
        # Buscar dados da task no Redis
        task_data = redis_client.get(f"task:{task_id}")
        
        if not task_data:
            return jsonify({
                'status': 'not_found',
                'message': 'Task não encontrada'
            }), 404
        
        task_info = json.loads(task_data)
        
        # Se todos foram processados, marcar como concluído
        if task_info['processados'] >= task_info['total']:
            task_info['status'] = 'completed'
        elif task_info['processados'] > 0:
            task_info['status'] = 'processing'
        
        return jsonify({
            'status': task_info['status'],
            'total': task_info['total'],
            'processados': task_info['processados'],
            'atualizados': task_info['atualizados'],
            'resultados': task_info.get('resultados', [])
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar status da task {task_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Rota removida - worker atualiza Redis diretamente sem precisar de endpoint HTTP
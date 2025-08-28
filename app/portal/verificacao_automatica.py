"""
Rota para verificação automática de protocolos pendentes
"""

from flask import jsonify, request
from flask_login import login_required
from app.portal import portal_bp
from app import db
from app.separacao.models import Separacao
import json
import uuid
import logging
from datetime import datetime
import redis
import os

logger = logging.getLogger(__name__)

# Configurar Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
try:
    if REDIS_URL.startswith('redis://'):
        redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    else:
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
    redis_client.ping()
    logger.info("✅ Redis conectado com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao conectar Redis: {e}")
    redis_client = None

@portal_bp.route('/api/buscar-protocolos-pendentes', methods=['GET'])
@login_required
def buscar_protocolos_pendentes():
    """
    Busca todos os protocolos pendentes de confirmação
    (protocolo != 'Vazio' e agendamento_confirmado = False)
    """
    try:
        # Buscar separações com protocolo válido e não confirmado
        query = db.session.query(Separacao).filter(
            Separacao.protocolo.isnot(None),
            Separacao.protocolo != '',
            Separacao.protocolo != 'Vazio',
            Separacao.protocolo != 'vazio',
            Separacao.agendamento_confirmado == False
        )
        
        # Adicionar filtro de portal se necessário (por enquanto só Atacadão)
        # Para futuro: adicionar campo portal na Separacao
        
        separacoes = query.all()
        
        # Agrupar por protocolo único
        protocolos_unicos = {}
        for sep in separacoes:
            if sep.protocolo not in protocolos_unicos:
                protocolos_unicos[sep.protocolo] = {
                    'protocolo': sep.protocolo,
                    'lote_id': sep.separacao_lote_id,
                    'num_pedido': sep.num_pedido,
                    'cliente': sep.raz_social_red,
                    'data_agendamento': sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None
                }
        
        protocolos_lista = list(protocolos_unicos.values())
        
        logger.info(f"📋 Encontrados {len(protocolos_lista)} protocolos pendentes únicos")
        
        return jsonify({
            'success': True,
            'total': len(protocolos_lista),
            'protocolos': protocolos_lista,
            'message': f'{len(protocolos_lista)} protocolos pendentes encontrados'
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar protocolos pendentes: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao buscar protocolos: {str(e)}'
        }), 500


@portal_bp.route('/api/verificar-todos-protocolos-pendentes', methods=['POST'])
@login_required
def verificar_todos_protocolos_pendentes():
    """
    Enfileira TODOS os protocolos pendentes para verificação
    """
    try:
        if not redis_client:
            return jsonify({
                'success': False,
                'message': 'Redis não está disponível'
            }), 503
        
        # Buscar todos os protocolos pendentes
        query = db.session.query(Separacao).filter(
            Separacao.protocolo.isnot(None),
            Separacao.protocolo != '',
            Separacao.protocolo != 'Vazio',
            Separacao.protocolo != 'vazio',
            Separacao.agendamento_confirmado == False
        ).distinct(Separacao.protocolo)
        
        separacoes = query.all()
        
        # Agrupar por protocolo único
        protocolos_unicos = {}
        for sep in separacoes:
            if sep.protocolo not in protocolos_unicos:
                protocolos_unicos[sep.protocolo] = {
                    'protocolo': sep.protocolo,
                    'lote_id': sep.separacao_lote_id,
                    'num_pedido': sep.num_pedido,
                    'cliente': sep.raz_social_red,
                    'data_agendamento_anterior': sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None
                }
        
        protocolos_lista = list(protocolos_unicos.values())
        
        if not protocolos_lista:
            return jsonify({
                'success': False,
                'message': 'Nenhum protocolo pendente encontrado'
            }), 404
        
        # Criar task ID única
        task_id = f"verificacao_todos_{uuid.uuid4().hex[:8]}"
        
        # Preparar dados para Redis
        task_data = {
            'task_id': task_id,
            'portal': 'atacadao',  # Por enquanto só Atacadão
            'protocolos': protocolos_lista,
            'total': len(protocolos_lista),
            'processados': 0,
            'atualizados': 0,
            'status': 'pending',
            'criado_em': datetime.now().isoformat(),
            'resultados': [],
            'alteracoes': []  # Lista detalhada de alterações
        }
        
        # Salvar no Redis com TTL de 2 horas
        redis_client.setex(
            f"task:{task_id}",
            7200,  # 2 horas
            json.dumps(task_data)
        )
        
        # Enfileirar cada protocolo para processamento
        for protocolo_info in protocolos_lista:
            job_data = {
                'task_id': task_id,
                'protocolo': protocolo_info['protocolo'],
                'lote_id': protocolo_info.get('lote_id'),
                'num_pedido': protocolo_info.get('num_pedido'),
                'portal': 'atacadao',
                'data_anterior': protocolo_info.get('data_agendamento_anterior'),
                'cliente': protocolo_info.get('cliente')
            }
            
            # Adicionar à fila de verificação
            redis_client.lpush('queue:verificacao_protocolo', json.dumps(job_data))
        
        logger.info(f"✅ Enfileirado {len(protocolos_lista)} protocolos pendentes. Task ID: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'total_enfileirados': len(protocolos_lista),
            'message': f'{len(protocolos_lista)} protocolos pendentes enfileirados para verificação'
        })
        
    except Exception as e:
        logger.error(f"Erro ao enfileirar protocolos pendentes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao processar solicitação: {str(e)}'
        }), 500


@portal_bp.route('/api/status-verificacao/<task_id>', methods=['GET'])
@portal_bp.route('/api/status-verificacao-detalhado/<task_id>', methods=['GET'])
@login_required
def status_verificacao_detalhado(task_id):
    """
    Retorna o status detalhado de uma verificação incluindo alterações
    """
    try:
        if not redis_client:
            return jsonify({
                'status': 'error',
                'message': 'Redis não está disponível'
            }), 503
        
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
        
        # Preparar lista de alterações para exibição
        alteracoes_formatadas = []
        for alteracao in task_info.get('alteracoes', []):
            alteracoes_formatadas.append({
                'protocolo': alteracao.get('protocolo'),
                'cliente': alteracao.get('cliente'),
                'tipo_mudanca': alteracao.get('tipo_mudanca'),
                'data_anterior': alteracao.get('data_anterior'),
                'data_nova': alteracao.get('data_nova'),
                'status_anterior': alteracao.get('status_anterior'),
                'status_novo': alteracao.get('status_novo'),
                'confirmado': alteracao.get('confirmado', False)
            })
        
        return jsonify({
            'status': task_info['status'],
            'total': task_info['total'],
            'processados': task_info['processados'],
            'atualizados': task_info['atualizados'],
            'alteracoes': alteracoes_formatadas,
            'resultados': task_info.get('resultados', [])
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar status detalhado da task {task_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@portal_bp.route('/api/verificar-agendas-lote', methods=['POST'])
@login_required
def verificar_agendas_lote():
    """
    Enfileira protocolos específicos para verificação em lote
    Recebe lista de protocolos via POST
    """
    try:
        if not redis_client:
            return jsonify({
                'success': False,
                'message': 'Redis não está disponível'
            }), 503
            
        data = request.json
        protocolos = data.get('protocolos', [])
        portal = data.get('portal', 'atacadao')
        
        if not protocolos:
            return jsonify({
                'success': False,
                'message': 'Nenhum protocolo fornecido'
            }), 400
        
        # Limitar a 100 protocolos
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
            'resultados': [],
            'alteracoes': []
        }
        
        # Salvar no Redis com TTL de 1 hora
        redis_client.setex(
            f"task:{task_id}",
            3600,
            json.dumps(task_data).encode('utf-8')
        )
        
        # Enfileirar cada protocolo para processamento
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
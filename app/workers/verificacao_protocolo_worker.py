"""
Worker para processar verificação de protocolos em lote
Processa a fila queue:verificacao_protocolo
"""

import json
import time
import logging
from datetime import datetime
from app import create_app, redis_client, db
from app.portal.atacadao.verificacao_protocolo import VerificadorProtocoloAtacadao
from app.separacao.models import Separacao
from app.pedidos.models import Pedido

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def processar_verificacao_protocolo():
    """
    Processa protocolos da fila de verificação
    """
    app = create_app()
    
    with app.app_context():
        logger.info("🚀 Worker de verificação de protocolos iniciado")
        
        while True:
            try:
                # Buscar próximo job da fila
                job_data = redis_client.brpop('queue:verificacao_protocolo', timeout=5)
                
                if not job_data:
                    continue
                
                # Decodificar dados do job
                job_info = json.loads(job_data[1])
                task_id = job_info.get('task_id')
                protocolo = job_info.get('protocolo')
                lote_id = job_info.get('lote_id')
                num_pedido = job_info.get('num_pedido')
                portal = job_info.get('portal', 'atacadao')
                
                logger.info(f"📋 Processando protocolo {protocolo} (Task: {task_id})")
                
                resultado = {
                    'atualizado': False,
                    'data_agendamento': None,
                    'confirmado': False,
                    'erro': None,
                    'data_anterior': job_info.get('data_anterior'),
                    'cliente': job_info.get('cliente')
                }
                
                try:
                    if portal == 'atacadao':
                        # Usar verificador direto (sem chamada HTTP)
                        logger.info(f"Verificando protocolo {protocolo} diretamente")
                        
                        verificador = VerificadorProtocoloAtacadao()
                        dados_protocolo = verificador.verificar_protocolo_completo(protocolo, lote_id)
                        
                        if dados_protocolo.get('success'):
                            # Verificar se houve atualização
                            if dados_protocolo.get('data_aprovada'):
                                resultado['atualizado'] = True
                                resultado['data_agendamento'] = dados_protocolo['data_aprovada']
                                resultado['confirmado'] = dados_protocolo.get('agendamento_confirmado', False)
                                
                                # Atualizar no banco se confirmado
                                if resultado['confirmado'] and lote_id:
                                    # Atualizar Separações diretamente (Pedido é VIEW, não atualizar)
                                    data_agend_obj = datetime.strptime(resultado['data_agendamento'], '%Y-%m-%d').date()

                                    Separacao.query.filter_by(separacao_lote_id=lote_id).update({
                                        'agendamento_confirmado': True,
                                        'agendamento': data_agend_obj
                                    })

                                    db.session.commit()
                                    logger.info(f"✅ Banco atualizado para lote {lote_id}")
                                
                                logger.info(f"✅ Protocolo {protocolo}: Data {resultado['data_agendamento']}, Confirmado: {resultado['confirmado']}")
                            else:
                                logger.info(f"ℹ️ Protocolo {protocolo} sem data aprovada")
                            
                            # Log do status encontrado
                            if dados_protocolo.get('status_text'):
                                logger.info(f"Status no portal: {dados_protocolo['status_text']}")
                        else:
                            logger.warning(f"⚠️ Erro ao verificar protocolo {protocolo}: {dados_protocolo.get('message')}")
                            resultado['erro'] = dados_protocolo.get('message', 'Erro ao verificar protocolo')
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao verificar protocolo {protocolo}: {e}")
                    resultado['erro'] = str(e)
                
                # Atualizar resultado da task no Redis diretamente
                try:
                    # Buscar task no Redis
                    task_data = redis_client.get(f"task:{task_id}")
                    if task_data:
                        task_info = json.loads(task_data)
                        
                        # Atualizar contador de processados
                        task_info['processados'] = task_info.get('processados', 0) + 1
                        
                        # Se houve atualização, incrementar contador
                        if resultado.get('atualizado'):
                            task_info['atualizados'] = task_info.get('atualizados', 0) + 1
                        
                        # Adicionar resultado à lista
                        task_info['resultados'].append({
                            'protocolo': protocolo,
                            'lote_id': lote_id,
                            'atualizado': resultado.get('atualizado', False),
                            'data_agendamento': resultado.get('data_agendamento'),
                            'confirmado': resultado.get('confirmado')
                        })
                        
                        # Se houve alteração, adicionar detalhes à lista de alterações
                        if resultado.get('atualizado'):
                            alteracao = {
                                'protocolo': protocolo,
                                'cliente': resultado.get('cliente'),
                                'tipo_mudanca': 'Data alterada' if resultado.get('data_agendamento') != resultado.get('data_anterior') else 'Status alterado',
                                'data_anterior': resultado.get('data_anterior'),
                                'data_nova': resultado.get('data_agendamento'),
                                'confirmado': resultado.get('confirmado', False)
                            }
                            
                            if 'alteracoes' not in task_info:
                                task_info['alteracoes'] = []
                            task_info['alteracoes'].append(alteracao)
                        
                        # Se todos foram processados, marcar como concluído
                        if task_info['processados'] >= task_info['total']:
                            task_info['status'] = 'completed'
                        else:
                            task_info['status'] = 'processing'
                        
                        # Salvar atualização no Redis
                        redis_client.setex(
                            f"task:{task_id}",
                            3600,  # Renovar TTL
                            json.dumps(task_info)
                        )
                        
                        logger.info(f"✅ Task {task_id} atualizada: {task_info['processados']}/{task_info['total']}")
                    else:
                        logger.warning(f"⚠️ Task {task_id} não encontrada no Redis")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao atualizar task no Redis: {e}")
                
                # Pequena pausa entre verificações para não sobrecarregar
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Erro no worker: {e}")
                time.sleep(5)  # Aguardar antes de tentar novamente

if __name__ == '__main__':
    processar_verificacao_protocolo()
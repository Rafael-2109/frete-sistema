"""
Job Scheduler para processar Fila de Agendamento Sendas
Executa a cada 20 minutos se houver itens na fila
"""

import logging
from app import create_app, db
from app.portal.models_fila_sendas import FilaAgendamentoSendas
from app.portal.models import PortalIntegracao
from app.portal.workers import enqueue_job
from app.portal.workers.sendas_jobs import processar_agendamento_sendas
from app.utils.lote_utils import gerar_lote_id

logger = logging.getLogger(__name__)

def processar_fila_sendas_scheduled():
    """
    Processa a fila de agendamento Sendas se houver itens pendentes
    Chamado pelo scheduler a cada 20 minutos
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar se há itens pendentes
            pendentes = FilaAgendamentoSendas.contar_pendentes()
            total_pendentes = sum(pendentes.values())
            
            if total_pendentes == 0:
                logger.info("✅ Fila Sendas vazia - nada para processar")
                return {
                    'success': True,
                    'message': 'Fila vazia',
                    'total_processado': 0
                }
            
            logger.info(f"📋 Fila Sendas com {total_pendentes} itens pendentes - iniciando processamento")
            
            # Obter grupos para processar
            grupos = FilaAgendamentoSendas.obter_para_processar()
            
            if not grupos:
                logger.warning("⚠️ Itens pendentes mas nenhum grupo formado")
                return {
                    'success': False,
                    'message': 'Erro ao formar grupos',
                    'total_processado': 0
                }
            
            # Agrupar CNPJs únicos COM OS ITENS
            cnpjs_para_processar = []
            cnpjs_processados = set()

            for chave, grupo in grupos.items():
                cnpj = grupo['cnpj']
                data_agendamento = grupo['data_agendamento']

                chave_unica = f"{cnpj}_{data_agendamento}"
                if chave_unica not in cnpjs_processados:
                    # Preparar itens do grupo
                    itens_grupo = []
                    for item in grupo['itens']:
                        itens_grupo.append({
                            'tipo_origem': 'separacao',  # Unificado para 'separacao'
                            'id': item.id,
                            'num_pedido': item.num_pedido,
                            'pedido_cliente': item.pedido_cliente,
                            'cod_produto': item.cod_produto,
                            'nome_produto': item.nome_produto,
                            'quantidade': float(item.quantidade),
                            'data_expedicao': item.data_expedicao.isoformat() if item.data_expedicao else None
                        })

                    # Calcular data_expedicao (pegar do primeiro item ou calcular)
                    data_expedicao = None
                    if grupo['itens'] and grupo['itens'][0].data_expedicao:
                        data_expedicao = grupo['itens'][0].data_expedicao

                    cnpjs_para_processar.append({
                        'cnpj': cnpj,
                        'data_agendamento': data_agendamento.isoformat() if hasattr(data_agendamento, 'isoformat') else str(data_agendamento),
                        'data_expedicao': data_expedicao.isoformat() if data_expedicao and hasattr(data_expedicao, 'isoformat') else str(data_expedicao) if data_expedicao else None,
                        'protocolo': grupo.get('protocolo'),  # Incluir protocolo
                        'itens': itens_grupo,  # INCLUIR OS ITENS!
                        'tipo_fluxo': 'programacao_lote'  # Identificar tipo de fluxo
                    })
                    cnpjs_processados.add(chave_unica)
            
            # Criar registro de integração
            lote_id = gerar_lote_id()
            
            # Preparar dados para JSONB
            lista_cnpjs_json = []
            for item in cnpjs_para_processar:
                lista_cnpjs_json.append({
                    'cnpj': item['cnpj'],
                    'data_agendamento': item['data_agendamento']
                })
            
            integracao = PortalIntegracao(
                portal='sendas',
                lote_id=lote_id,
                tipo_lote='fila_scheduled',  # Abreviado para caber no campo varchar(20)
                status='aguardando',
                dados_enviados={
                    'cnpjs': lista_cnpjs_json,
                    'total': len(lista_cnpjs_json),
                    'origem': 'fila_scheduled',
                    'usuario': 'Scheduler'
                }
            )
            db.session.add(integracao)
            db.session.commit()
            
            # Enfileirar job
            try:
                job = enqueue_job(
                    processar_agendamento_sendas,
                    integracao.id,
                    cnpjs_para_processar,
                    'Scheduler',
                    queue_name='sendas',
                    timeout='15m'
                )
                
                # Salvar job_id
                integracao.job_id = job.id
                db.session.commit()

                # ❌ REMOVIDO: NÃO marcar como processado aqui!
                # Quem deve marcar como processado é APENAS a exportação da planilha
                # O scheduler apenas cria o job de integração, mas os itens ficam pendentes
                # até que o usuário baixe a planilha via exportar_planilha()

                logger.info(f"✅ Fila processada via scheduler - Job {job.id} criado com {len(cnpjs_para_processar)} grupos (itens permanecem pendentes até exportação)")
                
                return {
                    'success': True,
                    'message': f'{len(cnpjs_para_processar)} grupos processados',
                    'job_id': job.id,
                    'total_processado': len(cnpjs_para_processar)
                }
                
            except Exception as queue_error:
                logger.error(f"❌ Erro ao enfileirar job: {queue_error}")
                integracao.status = 'erro'
                integracao.resposta_portal = {'erro': str(queue_error)}
                db.session.commit()
                
                return {
                    'success': False,
                    'message': f'Erro ao processar: {str(queue_error)}',
                    'total_processado': 0
                }
            
        except Exception as e:
            logger.error(f"❌ Erro no scheduler da fila Sendas: {e}")
            return {
                'success': False,
                'message': str(e),
                'total_processado': 0
            }

if __name__ == "__main__":
    # Para teste manual
    resultado = processar_fila_sendas_scheduled()
    print(f"Resultado: {resultado}")
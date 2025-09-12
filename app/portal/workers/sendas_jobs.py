"""
Jobs assíncronos para o portal Sendas
Executados em worker dedicado via Redis Queue
"""

import logging
from datetime import datetime
from app import create_app, db
from app.portal.models import PortalIntegracao, PortalLog
import json
import traceback

logger = logging.getLogger(__name__)

def processar_agendamento_sendas(integracao_id, lista_cnpjs_agendamento, usuario_nome=None):
    """
    Job assíncrono para processar agendamento no portal Sendas
    
    Args:
        integracao_id: ID da integração no banco
        lista_cnpjs_agendamento: Lista com dados dos CNPJs e agendamentos
        usuario_nome: Nome do usuário que iniciou o processo
    
    Returns:
        dict: Resultado do processamento
    """
    # Criar contexto da aplicação Flask (necessário para worker)
    app = create_app()
    
    with app.app_context():
        try:
            logger.info(f"[Worker Sendas] Iniciando processamento da integração {integracao_id}")
            logger.info(f"[Worker Sendas] Total de CNPJs: {len(lista_cnpjs_agendamento)}")
            logger.info(f"[Worker Sendas] Usuário: {usuario_nome}")
            
            # Buscar integração no banco
            integracao = PortalIntegracao.query.get(integracao_id)
            if not integracao:
                raise ValueError(f"Integração {integracao_id} não encontrada")
            
            # Atualizar status para processando
            integracao.status = 'processando'
            integracao.atualizado_em = datetime.utcnow()
            db.session.commit()
            
            # Log de início
            log_inicio = PortalLog(
                integracao_id=integracao_id,
                acao='processamento_inicio',
                sucesso=True,
                mensagem='Iniciando processamento assíncrono no worker Sendas',
                dados_contexto={
                    'worker': 'sendas',
                    'total_cnpjs': len(lista_cnpjs_agendamento),
                    'usuario': usuario_nome
                }
            )
            db.session.add(log_inicio)
            db.session.commit()
            
            # Importar classes necessárias (dentro do contexto para evitar imports circulares)
            from app.portal.sendas.consumir_agendas import ConsumirAgendasSendas
            from app.portal.sendas.preencher_planilha import PreencherPlanilhaSendas
            
            logger.info("[Worker Sendas] Inicializando classes...")
            
            # Criar instâncias
            consumidor = ConsumirAgendasSendas()
            preenchedor = PreencherPlanilhaSendas()
            
            # Callback para preencher a planilha
            def processar_planilha_callback(arquivo_baixado):
                """Callback para preencher a planilha com os dados selecionados"""
                logger.info(f"[Worker Sendas] Preenchendo planilha: {arquivo_baixado}")
                
                arquivo_processado = preenchedor.preencher_multiplos_cnpjs(
                    arquivo_origem=arquivo_baixado,
                    lista_cnpjs_agendamento=lista_cnpjs_agendamento
                )
                
                logger.info(f"[Worker Sendas] Planilha preenchida: {arquivo_processado}")
                return arquivo_processado
            
            # Executar fluxo completo com navegador persistente
            logger.info("[Worker Sendas] Iniciando fluxo unificado (navegador persistente)...")
            resultado = consumidor.executar_fluxo_completo_sync(
                processar_planilha_callback=processar_planilha_callback
            )
            
            # Processar resultado
            if resultado:
                logger.info("[Worker Sendas] ✅ Processamento concluído com sucesso")
                
                # Atualizar status da integração
                integracao.status = 'concluido'
                integracao.atualizado_em = datetime.utcnow()
                integracao.resultado = {
                    'sucesso': True,
                    'mensagem': 'Agendamentos processados com sucesso',
                    'timestamp': datetime.now().isoformat(),
                    'total_cnpjs': len(lista_cnpjs_agendamento)
                }
                db.session.commit()
                
                # Log de sucesso
                log_sucesso = PortalLog(
                    integracao_id=integracao_id,
                    acao='processamento_concluido',
                    sucesso=True,
                    mensagem=f'Processados {len(lista_cnpjs_agendamento)} CNPJs com sucesso',
                    dados_contexto={'resultado': resultado}
                )
                db.session.add(log_sucesso)
                db.session.commit()
                
                return {
                    'status': 'success',
                    'message': 'Agendamentos processados com sucesso no Sendas',
                    'integracao_id': integracao_id,
                    'total_cnpjs': len(lista_cnpjs_agendamento),
                    'resultado': resultado
                }
                
            else:
                raise Exception("Fluxo Sendas retornou sem sucesso")
                
        except Exception as e:
            logger.error(f"[Worker Sendas] ❌ Erro no processamento: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Atualizar status da integração para erro
            try:
                if integracao:
                    integracao.status = 'erro'
                    integracao.atualizado_em = datetime.utcnow()
                    integracao.resultado = {
                        'sucesso': False,
                        'erro': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    db.session.commit()
                    
                    # Log de erro
                    log_erro = PortalLog(
                        integracao_id=integracao_id,
                        acao='processamento_erro',
                        sucesso=False,
                        mensagem=f'Erro no processamento: {str(e)}',
                        dados_contexto={'traceback': traceback.format_exc()}
                    )
                    db.session.add(log_erro)
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"[Worker Sendas] Erro ao atualizar banco: {db_error}")
            
            return {
                'status': 'error',
                'message': str(e),
                'integracao_id': integracao_id,
                'traceback': traceback.format_exc()
            }
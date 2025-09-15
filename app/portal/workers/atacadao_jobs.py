"""
Jobs assíncronos para o portal Atacadão
Executados em worker dedicado via Redis Queue
"""

import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

def processar_agendamento_atacadao(integracao_id, dados_agendamento):
    """
    Job assíncrono para processar agendamento no portal Atacadão
    
    Args:
        integracao_id: ID da integração no banco
        dados_agendamento: Dicionário com dados do agendamento
            - lote_id: ID do lote de separação
            - pedido_cliente: Número do pedido do cliente
            - data_agendamento: Data do agendamento
            - hora_agendamento: Hora do agendamento (opcional)
            - peso_total: Peso total em kg
            - produtos: Lista de produtos com código e quantidade
            - transportadora: Nome da transportadora
            - tipo_veiculo: ID do tipo de veículo
    
    Returns:
        dict: Resultado do processamento
    """
    # Importações lazy dentro da função para evitar circular imports
    from app import create_app, db
    from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient
    from app.portal.models import PortalIntegracao, PortalLog
    from app.separacao.models import Separacao

    # Criar contexto da aplicação Flask (necessário para worker)
    app = create_app()
    
    with app.app_context():
        try:
            logger.info(f"[Worker] Iniciando processamento do agendamento {integracao_id}")
            
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
                integracao_id=integracao_id,  # Campo correto
                acao='processamento_inicio',  # Campo correto
                sucesso=True,
                mensagem='Iniciando processamento assíncrono no worker',
                dados_contexto={
                    'worker': 'atacadao',
                    'dados_recebidos': str(dados_agendamento)[:500]  # Limita tamanho
                }
            )
            db.session.add(log_inicio)
            db.session.commit()
            
            # Inicializar cliente Playwright com tratamento de erro
            logger.info("[Worker] Inicializando Playwright...")
            try:
                client = AtacadaoPlaywrightClient(headless=True)
                client.iniciar_sessao()
            except Exception as playwright_error:
                error_msg = str(playwright_error)
                if "Executable doesn't exist" in error_msg or "playwright install" in error_msg:
                    logger.error("[Worker] Playwright/Chromium não está instalado corretamente")
                    logger.error("[Worker] Execute: playwright install chromium")
                    raise Exception("Playwright não disponível. O navegador Chromium precisa ser instalado.")
                else:
                    raise
            
            # Verificar login
            if not client.verificar_login():
                logger.warning("[Worker] Sessão inválida, tentando login com CAPTCHA...")
                
                # Fazer login (com credenciais do .env)
                if not client.fazer_login_com_captcha():
                    raise Exception("Não foi possível fazer login no portal")
                
                # Reiniciar sessão após login
                client.fechar()
                client = AtacadaoPlaywrightClient(headless=True)
                client.iniciar_sessao()
            
            # Executar agendamento
            logger.info(f"[Worker] Criando agendamento para pedido {dados_agendamento.get('pedido_cliente')}...")
            resultado = client.criar_agendamento(dados_agendamento)
            
            # Fechar navegador
            client.fechar()
            
            # Processar resultado
            if resultado and resultado.get('success'):
                logger.info(f"[Worker] ✅ Agendamento criado com sucesso! Protocolo: {resultado.get('protocolo')}")
                
                # Atualizar integração
                integracao.status = 'aguardando_confirmacao'
                integracao.protocolo = resultado.get('protocolo')
                integracao.resposta_portal = resultado
                integracao.atualizado_em = datetime.utcnow()
                
                # Atualizar registros no banco de dados
                if resultado.get('protocolo'):
                    # Importar modelo Pedido
                    from app.pedidos.models import Pedido
                    
                    separacoes = Separacao.query.filter_by(
                        separacao_lote_id=dados_agendamento.get('lote_id')
                    ).all()
                    
                    # Converter data uma vez para usar em ambos os updates
                    data_agendamento_convertida = None
                    if dados_agendamento.get('data_agendamento'):
                        try:
                            if isinstance(dados_agendamento['data_agendamento'], str):
                                if '/' in dados_agendamento['data_agendamento']:
                                    # Formato DD/MM/AAAA
                                    partes = dados_agendamento['data_agendamento'].split('/')
                                    data_agendamento_convertida = datetime(
                                        int(partes[2]), 
                                        int(partes[1]), 
                                        int(partes[0])
                                    ).date()
                                else:
                                    # Formato ISO
                                    data_agendamento_convertida = datetime.fromisoformat(
                                        dados_agendamento['data_agendamento']
                                    ).date()
                            else:
                                data_agendamento_convertida = dados_agendamento['data_agendamento']
                        except Exception as e:
                            logger.error(f"Erro ao converter data: {e}")
                    
                    # Atualizar Separacao
                    for sep in separacoes:
                        sep.protocolo = resultado.get('protocolo')
                        sep.agendamento_confirmado = False  # Status aguardando confirmação
                        if data_agendamento_convertida:
                            sep.agendamento = data_agendamento_convertida
                    
                    # Atualizar Pedido correspondente
                    pedido = Pedido.query.filter_by(
                        separacao_lote_id=dados_agendamento.get('lote_id')
                    ).first()
                    
                    if pedido:
                        pedido.protocolo = resultado.get('protocolo')
                        if data_agendamento_convertida:
                            pedido.agendamento = data_agendamento_convertida
                        logger.info(f"[Worker] ✅ Atualizado Pedido {pedido.num_pedido} com protocolo {resultado.get('protocolo')}")
                    else:
                        logger.warning(f"[Worker] ⚠️ Pedido não encontrado para lote {dados_agendamento.get('lote_id')}")
                
                # Log de sucesso
                log_sucesso = PortalLog(
                    integracao_id=integracao_id,  # Campo correto
                    acao='agendamento_criado',  # Campo correto
                    sucesso=True,
                    mensagem=f'Agendamento criado com sucesso. Protocolo: {resultado.get("protocolo")}',
                    dados_contexto=resultado
                )
                db.session.add(log_sucesso)
                
            else:
                # Agendamento falhou
                logger.error(f"[Worker] ❌ Falha no agendamento: {resultado.get('message') if resultado else 'Erro desconhecido'}")
                
                integracao.status = 'erro'
                integracao.resposta_portal = resultado or {'message': 'Erro desconhecido'}
                integracao.atualizado_em = datetime.utcnow()
                
                # Log de erro
                log_erro = PortalLog(
                    integracao_id=integracao_id,  # Campo correto
                    acao='agendamento_erro',  # Campo correto
                    sucesso=False,
                    mensagem=f'Erro no agendamento: {resultado.get("message") if resultado else "Erro desconhecido"}',
                    dados_contexto=resultado if resultado else None
                )
                db.session.add(log_erro)
            
            # Commit final
            db.session.commit()
            
            logger.info(f"[Worker] Processamento concluído para integração {integracao_id}")
            return resultado
            
        except Exception as e:
            logger.error(f"[Worker] Erro fatal no processamento: {str(e)}")
            
            # Atualizar integração com erro
            try:
                integracao = PortalIntegracao.query.get(integracao_id)
                if integracao:
                    integracao.status = 'erro'
                    integracao.resposta_portal = {'error': str(e)}
                    integracao.atualizado_em = datetime.utcnow()
                    
                    # Log de erro fatal
                    log_erro_fatal = PortalLog(
                        integracao_id=integracao_id,  # Campo correto
                        acao='erro_fatal',  # Campo correto
                        sucesso=False,
                        mensagem=f'Erro fatal no worker: {str(e)}',
                        dados_contexto={
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    )
                    db.session.add(log_erro_fatal)
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"[Worker] Erro ao atualizar banco: {db_error}")
            
            # Re-raise para que o RQ marque o job como falho
            raise


def verificar_status_protocolo_atacadao(protocolo):
    """
    Job assíncrono para verificar status de um protocolo no Atacadão
    
    Args:
        protocolo: Número do protocolo
    
    Returns:
        dict: Status do protocolo
    """
    from app import create_app, db
    from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient

    app = create_app()
    
    with app.app_context():
        try:
            logger.info(f"[Worker] Verificando status do protocolo {protocolo}")
            
            # Inicializar cliente
            client = AtacadaoPlaywrightClient(headless=True)
            client.iniciar_sessao()
            
            # Verificar status
            status = client.verificar_status_agendamento(protocolo)
            
            # Fechar navegador
            client.fechar()
            
            logger.info(f"[Worker] Status do protocolo {protocolo}: {status}")
            
            return {
                'protocolo': protocolo,
                'status': status,
                'verificado_em': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"[Worker] Erro ao verificar protocolo: {e}")
            raise


def reprocessar_integracao_erro(integracao_id):
    """
    Job para reprocessar uma integração que falhou
    
    Args:
        integracao_id: ID da integração
    
    Returns:
        dict: Resultado do reprocessamento
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Buscar integração
            integracao = PortalIntegracao.query.get(integracao_id)
            if not integracao:
                raise ValueError(f"Integração {integracao_id} não encontrada")
            
            if integracao.status != 'erro':
                return {
                    'success': False,
                    'message': f'Integração não está em erro (status: {integracao.status})'
                }
            
            logger.info(f"[Worker] Reprocessando integração {integracao_id}")
            
            # Reconstruir dados de agendamento
            dados_agendamento = integracao.dados_enviados or {}
            
            # Chamar job principal
            return processar_agendamento_atacadao(integracao_id, dados_agendamento)
            
        except Exception as e:
            logger.error(f"[Worker] Erro no reprocessamento: {e}")
            raise
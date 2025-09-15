"""
Jobs assíncronos para o portal Sendas
Executados em worker dedicado via Redis Queue
"""

import logging
from datetime import datetime
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
    # Importações lazy dentro da função para evitar circular imports
    from app import create_app, db
    from app.portal.models import PortalIntegracao, PortalLog
    from app.portal.sendas.retorno_agendamento import processar_retorno_agendamento

    # Criar contexto da aplicação Flask (necessário para worker)
    app = create_app()
    
    with app.app_context():
        try:
            logger.info(f"[Worker Sendas] Iniciando processamento da integração {integracao_id}")
            logger.info(f"[Worker Sendas] Total de CNPJs: {len(lista_cnpjs_agendamento)}")
            logger.info(f"[Worker Sendas] Usuário: {usuario_nome}")
            
            # Converter datas de string para date objects se necessário
            # (os dados vêm do JSONB onde dates são armazenadas como strings)
            # MAS PRESERVAR TODA A ESTRUTURA DE DADOS!
            lista_cnpjs_processada = []
            for item in lista_cnpjs_agendamento:
                # Criar cópia profunda do item para não modificar o original
                item_processado = dict(item)

                # Converter data_agendamento se necessário
                data_agendamento = item_processado.get('data_agendamento')
                if isinstance(data_agendamento, str) and data_agendamento:
                    try:
                        item_processado['data_agendamento'] = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
                    except ValueError:
                        logger.warning(f"[Worker Sendas] Não foi possível converter data_agendamento: {data_agendamento}")

                # Converter data_expedicao se existir (campo documentado em TECHNICAL_SPEC_SENDAS.md)
                data_expedicao = item_processado.get('data_expedicao')
                if isinstance(data_expedicao, str) and data_expedicao:
                    try:
                        item_processado['data_expedicao'] = datetime.strptime(data_expedicao, '%Y-%m-%d').date()
                    except ValueError:
                        logger.warning(f"[Worker Sendas] Não foi possível converter data_expedicao: {data_expedicao}")

                # Se houver itens, converter datas dentro dos itens também
                if 'itens' in item_processado and item_processado['itens']:
                    for subitem in item_processado['itens']:
                        # Converter data_expedicao do item se necessário
                        if 'data_expedicao' in subitem and isinstance(subitem['data_expedicao'], str):
                            try:
                                subitem['data_expedicao'] = datetime.strptime(subitem['data_expedicao'], '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                pass

                # PRESERVAR TODA A ESTRUTURA!
                # Incluindo: cnpj, data_agendamento, data_expedicao, protocolo, itens, peso_total, etc.
                lista_cnpjs_processada.append(item_processado)

            # Usar a lista processada daqui em diante
            lista_cnpjs_agendamento = lista_cnpjs_processada

            # Log para debug - mostrar se preservamos a estrutura
            if lista_cnpjs_agendamento and isinstance(lista_cnpjs_agendamento[0], dict):
                campos_preservados = list(lista_cnpjs_agendamento[0].keys())
                logger.info(f"[Worker Sendas] Campos preservados: {campos_preservados}")
                if 'itens' in lista_cnpjs_agendamento[0]:
                    logger.info(f"[Worker Sendas] ✅ Estrutura completa preservada com {len(lista_cnpjs_agendamento[0].get('itens', []))} itens")
            
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
                
                # Detectar se temos dados completos fornecidos
                usar_dados_fornecidos = False
                if lista_cnpjs_agendamento and isinstance(lista_cnpjs_agendamento[0], dict):
                    usar_dados_fornecidos = 'itens' in lista_cnpjs_agendamento[0]

                arquivo_processado = preenchedor.preencher_multiplos_cnpjs(
                    arquivo_origem=arquivo_baixado,
                    lista_cnpjs_agendamento=lista_cnpjs_agendamento,
                    usar_dados_fornecidos=usar_dados_fornecidos
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

                # Processar retorno e salvar protocolos nos locais corretos
                # IMPORTANTE: Cada item da lista pode ter seu próprio protocolo!
                if lista_cnpjs_agendamento:
                    protocolos_processados = []

                    # Processar CADA item da lista com seu próprio protocolo
                    for idx, item_agendamento in enumerate(lista_cnpjs_agendamento):
                        if not isinstance(item_agendamento, dict):
                            continue

                        # Pegar protocolo deste item específico
                        protocolo = item_agendamento.get('protocolo')

                        # Fallback apenas se não tiver protocolo (não deveria acontecer)
                        if not protocolo:
                            protocolo_fallback = resultado.get('arquivo_upload', '').split('_')[-1].replace('.xlsx', '')
                            logger.warning(f"⚠️ Item {idx+1}: Protocolo não encontrado, usando fallback: {protocolo_fallback}")
                            protocolo = protocolo_fallback
                        else:
                            logger.info(f"✅ Item {idx+1}: Usando protocolo: {protocolo}")

                        # Determinar documento_origem (pode vir dos itens no Fluxo 3)
                        documento_origem = None
                        if item_agendamento.get('itens'):
                            # Se tem itens, verificar se algum tem documento_origem (Fluxos 2 e 3)
                            for item in item_agendamento['itens']:
                                if item.get('documento_origem'):
                                    documento_origem = item['documento_origem']
                                    break

                        # Determinar tipo_fluxo baseado na estrutura dos dados
                        tipo_fluxo = item_agendamento.get('tipo_fluxo')
                        if not tipo_fluxo:
                            tipo_fluxo = integracao.dados_enviados.get('tipo_fluxo') if integracao.dados_enviados else None
                        if not tipo_fluxo:
                            # Tentar identificar pela origem ou estrutura
                            if integracao.dados_enviados and integracao.dados_enviados.get('origem') == 'fila_agendamento':
                                # Veio da fila - pode ser Fluxo 2 ou 3
                                if documento_origem and documento_origem.isdigit():
                                    tipo_fluxo = 'listar_entregas'  # Fluxo 3 - NF
                                else:
                                    tipo_fluxo = 'carteira_agrupada'  # Fluxo 2 - Separação
                            else:
                                tipo_fluxo = 'programacao_lote'  # Fluxo 1

                        # Preparar dados para retorno universal
                        dados_retorno = {
                            'protocolo': protocolo,
                            'cnpj': item_agendamento.get('cnpj'),
                            'data_agendamento': item_agendamento.get('data_agendamento'),
                            'data_expedicao': item_agendamento.get('data_expedicao'),
                            'itens': item_agendamento.get('itens', []),
                            'tipo_fluxo': tipo_fluxo,
                            'documento_origem': documento_origem
                        }

                        # Processar retorno para este item
                        try:
                            retorno_sucesso = processar_retorno_agendamento(dados_retorno)
                            if retorno_sucesso:
                                protocolos_processados.append(protocolo)
                                logger.info(f"[Worker Sendas] ✅ Protocolo {protocolo} salvo com sucesso")
                        except Exception as e:
                            logger.error(f"[Worker Sendas] ❌ Erro ao processar protocolo {protocolo}: {e}")

                    if protocolos_processados:
                        logger.info(f"[Worker Sendas] ✅ Total de {len(protocolos_processados)} protocolos processados com sucesso")
                    else:
                        logger.warning("[Worker Sendas] ⚠️ Nenhum protocolo foi processado com sucesso")

                # Atualizar status da integração
                integracao.status = 'concluido'
                integracao.atualizado_em = datetime.utcnow()
                integracao.resposta_portal = {
                    'sucesso': True,
                    'mensagem': 'Agendamentos processados com sucesso',
                    'timestamp': datetime.now().isoformat(),
                    'total_cnpjs': len(lista_cnpjs_agendamento),
                    'protocolo': protocolo
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
                    integracao.resposta_portal = {
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
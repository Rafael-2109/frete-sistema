"""
Jobs assíncronos para o portal Atacadão - Versão Otimizada para Render
Evita importações circulares usando lazy loading
"""

import logging
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

def processar_agendamento_atacadao(integracao_id, lista_cnpjs_agendamento, usuario_nome=None):
    """
    Job assíncrono para processar agendamento no portal Atacadão
    Versão otimizada com importações lazy para evitar circular imports

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
    from app.portal.atacadao.retorno_agendamento import processar_retorno_agendamento

    # Criar contexto da aplicação Flask (necessário para worker)
    app = create_app()

    with app.app_context():
        try:
            logger.info(f"[Worker Atacadão] Iniciando processamento da integração {integracao_id}")
            logger.info(f"[Worker Atacadão] Total de CNPJs: {len(lista_cnpjs_agendamento)}")
            logger.info(f"[Worker Atacadão] Usuário: {usuario_nome}")

            # Converter datas de string para date objects se necessário
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
                        logger.warning(f"[Worker Atacadão] Não foi possível converter data_agendamento: {data_agendamento}")

                # Converter data_entrega se existir
                data_entrega = item_processado.get('data_entrega')
                if isinstance(data_entrega, str) and data_entrega:
                    try:
                        item_processado['data_entrega'] = datetime.strptime(data_entrega, '%Y-%m-%d').date()
                    except ValueError:
                        logger.warning(f"[Worker Atacadão] Não foi possível converter data_entrega: {data_entrega}")

                lista_cnpjs_processada.append(item_processado)

            # Buscar integração no banco
            integracao = PortalIntegracao.query.get(integracao_id)
            if not integracao:
                logger.error(f"[Worker Atacadão] Integração {integracao_id} não encontrada")
                return {
                    'success': False,
                    'message': f'Integração {integracao_id} não encontrada'
                }

            logger.info(f"[Worker Atacadão] Integração encontrada: {integracao.nome_portal}")

            # Atualizar status para processando
            integracao.status = 'processando'
            integracao.ultima_atualizacao = datetime.now()
            db.session.commit()

            # Processar agendamento usando a função do módulo atacadão
            resultado = processar_retorno_agendamento(
                integracao_id=integracao_id,
                lista_cnpjs_agendamento=lista_cnpjs_processada,
                usuario_nome=usuario_nome
            )

            logger.info(f"[Worker Atacadão] Processamento finalizado. Sucesso: {resultado.get('success', False)}")

            # Atualizar status baseado no resultado
            if resultado.get('success'):
                integracao.status = 'ativo'
            else:
                integracao.status = 'erro'
                integracao.erro_mensagem = resultado.get('message', 'Erro desconhecido')

            integracao.ultima_atualizacao = datetime.now()
            db.session.commit()

            # Registrar log
            PortalLog.registrar(
                portal='atacadao',
                tipo='agendamento_async',
                mensagem=f"Processamento assíncrono finalizado - Sucesso: {resultado.get('success')}",
                detalhes=resultado,
                usuario=usuario_nome
            )

            return resultado

        except Exception as e:
            logger.error(f"[Worker Atacadão] Erro ao processar agendamento: {str(e)}")
            logger.error(f"[Worker Atacadão] Traceback: {traceback.format_exc()}")

            # Atualizar status da integração para erro
            try:
                integracao = PortalIntegracao.query.get(integracao_id)
                if integracao:
                    integracao.status = 'erro'
                    integracao.erro_mensagem = str(e)
                    integracao.ultima_atualizacao = datetime.now()
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"[Worker Atacadão] Erro ao atualizar banco: {str(db_error)}")

            # Registrar log de erro
            try:
                PortalLog.registrar(
                    portal='atacadao',
                    tipo='erro_agendamento_async',
                    mensagem=f"Erro no processamento assíncrono: {str(e)}",
                    detalhes={'traceback': traceback.format_exc()},
                    usuario=usuario_nome
                )
            except Exception as log_error:
                logger.error(f"[Worker Atacadão] Erro ao registrar log: {str(log_error)}")

            return {
                'success': False,
                'message': f'Erro ao processar agendamento: {str(e)}',
                'traceback': traceback.format_exc()
            }
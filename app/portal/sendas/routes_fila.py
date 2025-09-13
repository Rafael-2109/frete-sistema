"""
Rotas para gerenciar a fila de agendamentos Sendas
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.portal.models_fila_sendas import FilaAgendamentoSendas
from app.separacao.models import Separacao
from app.monitoramento.models import EntregaMonitorada
from app.carteira.models import CarteiraPrincipal
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

fila_sendas_bp = Blueprint('fila_sendas', __name__, url_prefix='/portal/sendas/fila')

@fila_sendas_bp.route('/adicionar', methods=['POST'])
@login_required
def adicionar_na_fila():
    """
    Adiciona item na fila de agendamento Sendas
    
    Aceita origem de:
    - Separação (carteira agrupada)
    - NF (listar_entregas)
    """
    try:
        data = request.get_json()
        
        tipo_origem = data.get('tipo_origem')  # 'separacao' ou 'nf'
        documento_origem = data.get('documento_origem')  # lote_id ou numero_nf
        data_expedicao = data.get('data_expedicao')
        data_agendamento = data.get('data_agendamento')
        
        if not all([tipo_origem, documento_origem, data_agendamento]):
            return jsonify({
                'success': False,
                'message': 'Dados obrigatórios faltando'
            }), 400
        
        # Converter datas se vierem como string
        if isinstance(data_expedicao, str):
            data_expedicao = datetime.strptime(data_expedicao, '%Y-%m-%d').date()
        if isinstance(data_agendamento, str):
            data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
        
        itens_adicionados = []
        
        if tipo_origem == 'separacao':
            # Buscar itens da separação
            itens_sep = Separacao.query.filter_by(
                separacao_lote_id=documento_origem,
                sincronizado_nf=False
            ).all()
            
            if not itens_sep:
                return jsonify({
                    'success': False,
                    'message': 'Separação não encontrada ou já sincronizada'
                }), 404
            
            # Adicionar cada item na fila
            for item in itens_sep:
                # Buscar nome do produto se não existir no item
                nome_produto = None
                if item.cod_produto:
                    # Buscar na CarteiraPrincipal ou CadastroPalletizacao
                    carteira_item = CarteiraPrincipal.query.filter_by(
                        cod_produto=item.cod_produto
                    ).first()
                    if carteira_item:
                        nome_produto = carteira_item.nome_produto
                
                # Garantir data_expedicao (usar item.expedicao ou calcular D-1)
                data_exp_final = data_expedicao or item.expedicao
                if not data_exp_final and data_agendamento:
                    # Se não tem data de expedição, usar D-1 do agendamento
                    from datetime import timedelta
                    if isinstance(data_agendamento, str):
                        data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
                    data_exp_final = data_agendamento - timedelta(days=1)
                
                fila_item = FilaAgendamentoSendas.adicionar(
                    tipo_origem='separacao',
                    documento_origem=documento_origem,
                    cnpj=item.cnpj_cpf,
                    num_pedido=item.num_pedido,
                    cod_produto=item.cod_produto,
                    nome_produto=nome_produto,
                    quantidade=float(item.qtd_saldo or 0),
                    data_expedicao=data_exp_final,
                    data_agendamento=data_agendamento,
                    pedido_cliente=item.pedido_cliente
                )
                itens_adicionados.append(fila_item.id)
            
        elif tipo_origem == 'nf':
            # Buscar entrega monitorada
            entrega = EntregaMonitorada.query.filter_by(
                numero_nf=documento_origem
            ).first()
            
            if not entrega:
                return jsonify({
                    'success': False,
                    'message': 'NF não encontrada no monitoramento'
                }), 404
            
            # Buscar itens da NF na separação (para obter produtos)
            itens_nf = Separacao.query.filter_by(
                numero_nf=documento_origem
            ).all()
            
            if not itens_nf:
                # Se não tem na separação, buscar na carteira pelo pedido
                # (aqui simplificado - pode precisar ajustar lógica)
                return jsonify({
                    'success': False,
                    'message': 'Produtos da NF não encontrados'
                }), 404
            
            # Adicionar cada produto na fila
            for item in itens_nf:
                # Buscar pedido_cliente e nome_produto
                pedido_cliente = item.pedido_cliente
                nome_produto = None
                
                if item.num_pedido and item.cod_produto:
                    carteira_item = CarteiraPrincipal.query.filter_by(
                        num_pedido=item.num_pedido,
                        cod_produto=item.cod_produto
                    ).first()
                    if carteira_item:
                        if not pedido_cliente:
                            pedido_cliente = carteira_item.pedido_cliente
                        nome_produto = carteira_item.nome_produto
                
                # Garantir data_expedicao (usar item.expedicao ou calcular D-1)
                data_exp_final = data_expedicao or item.expedicao
                if not data_exp_final and data_agendamento:
                    # Se não tem data de expedição, usar D-1 do agendamento
                    from datetime import timedelta
                    if isinstance(data_agendamento, str):
                        data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
                    data_exp_final = data_agendamento - timedelta(days=1)
                
                fila_item = FilaAgendamentoSendas.adicionar(
                    tipo_origem='nf',
                    documento_origem=documento_origem,
                    cnpj=entrega.cnpj_cliente,
                    num_pedido=item.num_pedido,
                    cod_produto=item.cod_produto,
                    nome_produto=nome_produto,
                    quantidade=float(item.qtd_saldo or 0),
                    data_expedicao=data_exp_final,
                    data_agendamento=data_agendamento,
                    pedido_cliente=pedido_cliente
                )
                itens_adicionados.append(fila_item.id)
        
        else:
            return jsonify({
                'success': False,
                'message': 'Tipo de origem inválido'
            }), 400
        
        # Contar pendentes
        pendentes = FilaAgendamentoSendas.contar_pendentes()
        
        return jsonify({
            'success': True,
            'message': f'{len(itens_adicionados)} itens adicionados à fila',
            'itens_adicionados': len(itens_adicionados),
            'pendentes_total': sum(pendentes.values()),
            'pendentes_por_cnpj': pendentes
        })
        
    except Exception as e:
        logger.error(f"Erro ao adicionar na fila: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@fila_sendas_bp.route('/status', methods=['GET'])
@login_required
def status_fila():
    """
    Retorna status da fila de agendamentos
    """
    try:
        pendentes = FilaAgendamentoSendas.contar_pendentes()
        
        # Buscar detalhes se solicitado
        incluir_detalhes = request.args.get('detalhes', 'false').lower() == 'true'
        detalhes = []
        
        if incluir_detalhes:
            grupos = FilaAgendamentoSendas.obter_para_processar()
            for chave, grupo in grupos.items():
                detalhes.append({
                    'cnpj': grupo['cnpj'],
                    'data_agendamento': grupo['data_agendamento'].isoformat(),
                    'total_itens': len(grupo['itens']),
                    'protocolo': grupo['protocolo']
                })
        
        return jsonify({
            'success': True,
            'pendentes_total': sum(pendentes.values()),
            'pendentes_por_cnpj': pendentes,
            'detalhes': detalhes if incluir_detalhes else None
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@fila_sendas_bp.route('/processar', methods=['POST'])
@login_required  
def processar_fila():
    """
    Processa a fila enviando para o worker de agendamento em lote
    """
    try:
        from app.portal.workers import enqueue_job
        from app.portal.workers.sendas_jobs import processar_agendamento_sendas
        from app.portal.models import PortalIntegracao
        from app.utils.lote_utils import gerar_lote_id
        
        grupos = FilaAgendamentoSendas.obter_para_processar()
        
        if not grupos:
            return jsonify({
                'success': True,
                'message': 'Nenhum item na fila para processar',
                'total_processado': 0
            })
        
        # Agrupar todos os CNPJs únicos para processar
        cnpjs_para_processar = []
        cnpjs_processados = set()
        
        for chave, grupo in grupos.items():
            cnpj = grupo['cnpj']
            data_agendamento = grupo['data_agendamento']
            
            # Evitar duplicatas
            chave_unica = f"{cnpj}_{data_agendamento}"
            if chave_unica not in cnpjs_processados:
                cnpjs_para_processar.append({
                    'cnpj': cnpj,
                    'data_agendamento': data_agendamento.isoformat() if hasattr(data_agendamento, 'isoformat') else str(data_agendamento)
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
            tipo_lote='agendamento_fila',
            status='aguardando',
            dados_enviados={
                'cnpjs': lista_cnpjs_json,
                'total': len(lista_cnpjs_json),
                'origem': 'fila_agendamento',
                'usuario': current_user.nome if current_user else 'Sistema'
            }
        )
        db.session.add(integracao)
        db.session.commit()
        
        # Enfileirar job no Redis Queue
        try:
            job = enqueue_job(
                processar_agendamento_sendas,
                integracao.id,
                cnpjs_para_processar,
                current_user.nome if current_user else 'Sistema',
                queue_name='sendas',
                timeout='15m'
            )
            
            # Salvar job_id na integração
            integracao.job_id = job.id
            db.session.commit()
            
            # Marcar itens da fila como processados
            for chave, grupo in grupos.items():
                FilaAgendamentoSendas.marcar_processados(
                    grupo['cnpj'],
                    grupo['data_agendamento']
                )
            
            logger.info(f"✅ Fila processada - Job {job.id} criado com {len(cnpjs_para_processar)} grupos")
            
            return jsonify({
                'success': True,
                'message': f'{len(cnpjs_para_processar)} grupos enviados para processamento',
                'job_id': job.id,
                'total_processado': len(cnpjs_para_processar)
            })
            
        except Exception as queue_error:
            logger.error(f"❌ Erro ao enfileirar job: {queue_error}")
            integracao.status = 'erro'
            integracao.resposta_portal = {'erro': str(queue_error)}
            db.session.commit()
            
            return jsonify({
                'success': False,
                'message': f'Erro ao processar fila: {str(queue_error)}',
                'total_processado': 0
            }), 500
        
    except Exception as e:
        logger.error(f"Erro ao processar fila: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@fila_sendas_bp.route('/limpar', methods=['POST'])
@login_required
def limpar_fila():
    """
    Limpa itens processados antigos
    """
    try:
        dias = request.get_json().get('dias', 7)
        FilaAgendamentoSendas.limpar_processados(dias)
        
        return jsonify({
            'success': True,
            'message': f'Itens processados há mais de {dias} dias removidos'
        })
        
    except Exception as e:
        logger.error(f"Erro ao limpar fila: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
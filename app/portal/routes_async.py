"""
Rotas assíncronas do Portal - versão com Redis Queue
Substitui execução síncrona por jobs assíncronos
"""

from flask import jsonify, request
from flask_login import login_required, current_user
from app.portal import portal_bp
from app.portal.models import PortalIntegracao, PortalLog
from app.portal.workers import enqueue_job
from app.portal.workers.atacadao_jobs import processar_agendamento_atacadao
from app import db
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

@portal_bp.route('/api/solicitar-agendamento-nf-async', methods=['POST'])
@login_required
def solicitar_agendamento_nf_async():
    """
    API assíncrona para solicitar agendamento usando numero_nf
    Versão assíncrona do endpoint /api/solicitar-agendamento-nf
    """
    try:
        dados = request.json
        numero_nf = dados.get('numero_nf')
        data_agendamento = dados.get('data_agendamento')
        hora_agendamento = dados.get('hora_agendamento')
        
        if not numero_nf:
            return jsonify({
                'success': False,
                'message': 'Número da NF é obrigatório'
            }), 400
        
        if not data_agendamento:
            return jsonify({
                'success': False,
                'message': 'Data de agendamento é obrigatória'
            }), 400
        
        # Buscar dados da entrega via NF
        from app.monitoramento.models import EntregaMonitorada
        from app.faturamento.models import FaturamentoProduto
        from app.portal.utils.grupo_empresarial import GrupoEmpresarial
        from app.portal.atacadao.models import ProdutoDeParaAtacadao
        
        entrega = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
        
        if not entrega:
            logger.error(f"Entrega não encontrada para NF {numero_nf}")
            return jsonify({
                'success': False,
                'message': f'Entrega com NF {numero_nf} não encontrada'
            }), 404
        
        logger.info(f"Entrega encontrada para NF {numero_nf}: ID={entrega.id}, Cliente={entrega.cliente}")
        
        # Buscar produtos da NF - aceitar qualquer status exceto Cancelado
        produtos_faturamento = FaturamentoProduto.query.filter(
            FaturamentoProduto.numero_nf == numero_nf,
            FaturamentoProduto.status_nf != 'Cancelado'
        ).all()
        
        if not produtos_faturamento:
            # Tentar buscar sem filtro de status como fallback
            produtos_faturamento = FaturamentoProduto.query.filter_by(
                numero_nf=numero_nf
            ).all()
            
            if not produtos_faturamento:
                logger.error(f"Produtos não encontrados para NF {numero_nf} na tabela FaturamentoProduto")
                
                # Debug: verificar total de registros na tabela
                total_registros = FaturamentoProduto.query.count()
                logger.info(f"Total de registros em FaturamentoProduto: {total_registros}")
                
                # Debug: verificar últimas NFs cadastradas
                ultimas_nfs = db.session.query(FaturamentoProduto.numero_nf).distinct().limit(5).all()
                logger.info(f"Últimas NFs cadastradas: {[nf[0] for nf in ultimas_nfs]}")
                
                return jsonify({
                    'success': False,
                    'message': f'Produtos não encontrados para a NF {numero_nf}. Verifique se a NF foi importada corretamente no sistema de faturamento.'
                }), 404
            else:
                logger.warning(f"Produtos encontrados para NF {numero_nf}, mas todos com status Cancelado")
        
        logger.info(f"Encontrados {len(produtos_faturamento)} produtos para NF {numero_nf}")
        
        # Identificar portal
        portal = GrupoEmpresarial.identificar_portal(entrega.cnpj_cliente)
        
        if portal != 'atacadao':
            return jsonify({
                'success': False,
                'message': f'Portal {portal} ainda não suporta agendamento assíncrono'
            }), 400
        
        # Buscar pedido_cliente
        pedido_cliente = entrega.pedido_cliente
        if not pedido_cliente:
            return jsonify({
                'success': False,
                'message': 'Pedido do cliente não encontrado para esta NF'
            }), 400
        
        # Preparar produtos com DE-PARA
        produtos = []
        peso_total = 0
        
        for produto in produtos_faturamento:
            # Buscar DE-PARA - usando campos CORRETOS do modelo
            depara = ProdutoDeParaAtacadao.query.filter_by(
                codigo_nosso=produto.cod_produto,
                ativo=True
            ).first()
            
            codigo_portal = depara.codigo_atacadao if depara else produto.cod_produto
            
            produtos.append({
                'codigo': codigo_portal,
                'codigo_nosso': produto.cod_produto,  # Nosso código interno
                'nome': produto.nome_produto,
                'quantidade': int(produto.qtd_produto_faturado or 0),
                'peso': float(produto.peso_total or 0)
            })
            
            peso_total += float(produto.peso_total or 0)
        
        # Criar integração
        integracao = PortalIntegracao(
            lote_id=f'NF-{numero_nf}',
            portal=portal,
            tipo_lote='agendamento_nf',  # Campo correto: tipo_lote
            data_agendamento=data_agendamento,
            hora_agendamento=hora_agendamento,
            status='enfileirado',
            dados_enviados={
                'numero_nf': numero_nf,
                'pedido_cliente': pedido_cliente,
                'data_agendamento': data_agendamento,
                'hora_agendamento': hora_agendamento,
                'peso_total': peso_total,
                'produtos': produtos
            },
            usuario_solicitante=current_user.nome if current_user.is_authenticated else 'Sistema'
        )
        db.session.add(integracao)
        db.session.commit()
        
        # Enfileirar job
        job = enqueue_job(
            processar_agendamento_atacadao,
            integracao.id,
            integracao.dados_enviados,
            queue_name='atacadao',
            timeout='30m'
        )
        
        # Salvar job_id
        integracao.job_id = job.id
        db.session.commit()
        
        logger.info(f"✅ Job {job.id} enfileirado para NF {numero_nf}")
        
        return jsonify({
            'success': True,
            'message': 'Agendamento enfileirado para processamento',
            'integracao_id': integracao.id,
            'job_id': job.id,
            'numero_nf': numero_nf,
            'status_url': f'/portal/api/status-job/{job.id}'
        }), 202
        
    except Exception as e:
        logger.error(f"Erro no agendamento assíncrono NF: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@portal_bp.route('/api/solicitar-agendamento-async', methods=['POST'])
@login_required
def solicitar_agendamento_async():
    """
    API assíncrona para solicitar agendamento no portal
    Enfileira o job ao invés de executar diretamente
    """
    try:
        dados = request.json
        lote_id = dados.get('lote_id')
        data_agendamento = dados.get('data_agendamento')
        hora_agendamento = dados.get('hora_agendamento')
        transportadora = dados.get('transportadora')
        tipo_veiculo = dados.get('tipo_veiculo')
        
        # Validações básicas
        if not lote_id:
            return jsonify({
                'success': False,
                'message': 'ID do lote é obrigatório'
            }), 400
        
        if not data_agendamento:
            return jsonify({
                'success': False,
                'message': 'Data de agendamento é obrigatória'
            }), 400
        
        # Importar depois para evitar imports circulares
        from app.separacao.models import Separacao
        from app.portal.utils.grupo_empresarial import GrupoEmpresarial
        from app.portal.atacadao.models import ProdutoDeParaAtacadao
        
        # Buscar dados do lote
        lote_separacao = Separacao.query.filter_by(
            separacao_lote_id=lote_id
        ).all()
        
        if not lote_separacao:
            return jsonify({
                'success': False,
                'message': f'Lote {lote_id} não encontrado'
            }), 404
        
        # Identificar portal
        cnpj = lote_separacao[0].cnpj_cpf
        portal = GrupoEmpresarial.identificar_portal(cnpj)
        
        if portal != 'atacadao':
            return jsonify({
                'success': False,
                'message': f'Portal {portal} ainda não suporta agendamento assíncrono'
            }), 400
        
        # Buscar pedido_cliente
        pedido_cliente = None
        for item in lote_separacao:
            if item.pedido_cliente:
                pedido_cliente = item.pedido_cliente
                break
        
        if not pedido_cliente:
            # Tentar buscar em CarteiraPrincipal
            from app.carteira.models import CarteiraPrincipal
            carteira_item = CarteiraPrincipal.query.filter_by(
                separacao_lote_id=lote_id
            ).first()
            if carteira_item:
                pedido_cliente = carteira_item.pedido_cliente
        
        if not pedido_cliente:
            return jsonify({
                'success': False,
                'message': 'Pedido do cliente não encontrado para o lote'
            }), 400
        
        # Buscar produtos com DE-PARA
        produtos = []
        peso_total = 0
        
        for item in lote_separacao:
            # Buscar DE-PARA - usando campos CORRETOS do modelo
            depara = ProdutoDeParaAtacadao.query.filter_by(
                codigo_nosso=item.cod_produto,
                ativo=True
            ).first()
            
            if depara:
                codigo_portal = depara.codigo_atacadao
            else:
                logger.warning(f"Produto {item.cod_produto} sem DE-PARA, usando código original")
                codigo_portal = item.cod_produto
            
            produtos.append({
                'codigo': codigo_portal,
                'codigo_nosso': item.cod_produto,  # Nosso código interno
                'nome': getattr(item, 'nome_produto', ''),
                'quantidade': int(item.qtd_saldo or 0),
                'peso': float(item.peso or 0)
            })
            
            peso_total += float(item.peso or 0)
        
        # Preparar dados para o job
        dados_agendamento = {
            'lote_id': lote_id,
            'pedido_cliente': pedido_cliente,
            'data_agendamento': data_agendamento,
            'hora_agendamento': hora_agendamento,
            'peso_total': peso_total,
            'produtos': produtos,
            'transportadora': transportadora,
            'tipo_veiculo': tipo_veiculo
        }
        
        # Criar integração no banco (status: enfileirado)
        integracao = PortalIntegracao(
            lote_id=lote_id,
            portal=portal,
            tipo_lote='agendamento',  # Campo correto: tipo_lote
            data_agendamento=data_agendamento,
            hora_agendamento=hora_agendamento,
            status='enfileirado',  # Novo status
            dados_enviados=dados_agendamento,
            usuario_solicitante=current_user.nome if current_user.is_authenticated else 'Sistema'
        )
        db.session.add(integracao)
        db.session.commit()
        
        # Log de enfileiramento
        log_enfileirado = PortalLog(
            integracao_id=integracao.id,  # Campo correto: integracao_id
            acao='enfileiramento',  # Campo correto: acao
            sucesso=True,
            mensagem='Agendamento enfileirado para processamento assíncrono',
            dados_contexto={
                'pedido_cliente': pedido_cliente,
                'data_agendamento': data_agendamento,
                'produtos': len(produtos)
            }
        )
        db.session.add(log_enfileirado)
        db.session.commit()
        
        # ENFILEIRAR JOB NO REDIS QUEUE
        try:
            job = enqueue_job(
                processar_agendamento_atacadao,
                integracao.id,
                dados_agendamento,
                queue_name='atacadao',  # Fila dedicada
                timeout='30m'  # 30 minutos de timeout
            )
            
            # Salvar job_id na integração
            integracao.job_id = job.id
            db.session.commit()
            
            logger.info(f"✅ Job {job.id} enfileirado para integração {integracao.id}")
            
            return jsonify({
                'success': True,
                'message': 'Agendamento enfileirado para processamento',
                'integracao_id': integracao.id,
                'job_id': job.id,
                'status_url': f'/portal/api/status-job/{job.id}'
            }), 202  # 202 = Accepted (processamento assíncrono)
            
        except Exception as e:
            logger.error(f"Erro ao enfileirar job: {e}")
            
            # Atualizar integração com erro
            integracao.status = 'erro'
            integracao.resposta_portal = {'error': str(e)}
            db.session.commit()
            
            return jsonify({
                'success': False,
                'message': f'Erro ao enfileirar job: {str(e)}'
            }), 500
        
    except Exception as e:
        logger.error(f"Erro na API assíncrona: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@portal_bp.route('/api/status-job/<job_id>')
@login_required
def status_job(job_id):
    """
    Verifica o status de um job no Redis Queue
    """
    try:
        from rq.job import Job
        from app.portal.workers import get_redis_connection
        
        redis_conn = get_redis_connection()
        
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except Exception:
            return jsonify({
                'success': False,
                'message': 'Job não encontrado'
            }), 404
        
        # Buscar integração relacionada
        integracao = PortalIntegracao.query.filter_by(job_id=job_id).first()
        
        response = {
            'job_id': job.id,
            'status': job.get_status(),
            'criado_em': job.created_at.isoformat() if job.created_at else None,
            'iniciado_em': job.started_at.isoformat() if job.started_at else None,
            'finalizado_em': job.ended_at.isoformat() if job.ended_at else None,
            'resultado': job.result if job.is_finished else None
        }
        
        if integracao:
            response['integracao'] = {
                'id': integracao.id,
                'status': integracao.status,
                'protocolo': integracao.protocolo,
                'lote_id': integracao.lote_id,
                'portal': integracao.portal
            }
        
        # Adicionar informações baseadas no status
        if job.is_finished:
            response['message'] = 'Job concluído com sucesso'
        elif job.is_failed:
            response['message'] = 'Job falhou'
            response['error'] = str(job.exc_info) if job.exc_info else 'Erro desconhecido'
        elif job.is_started:
            response['message'] = 'Job em processamento...'
        elif job.is_queued:
            response['message'] = 'Job na fila aguardando processamento'
        elif job.is_deferred:
            response['message'] = 'Job adiado'
        else:
            response['message'] = f'Status desconhecido: {job.get_status()}'
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Erro ao verificar status do job: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@portal_bp.route('/api/reprocessar-integracao/<int:integracao_id>', methods=['POST'])
@login_required
def reprocessar_integracao(integracao_id):
    """
    Reprocessa uma integração que falhou
    """
    try:
        integracao = PortalIntegracao.query.get(integracao_id)
        
        if not integracao:
            return jsonify({
                'success': False,
                'message': 'Integração não encontrada'
            }), 404
        
        if integracao.status != 'erro':
            return jsonify({
                'success': False,
                'message': f'Integração não está em erro (status atual: {integracao.status})'
            }), 400
        
        # Enfileirar job de reprocessamento
        from app.portal.workers.atacadao_jobs import reprocessar_integracao_erro
        
        job = enqueue_job(
            reprocessar_integracao_erro,
            integracao_id,
            queue_name='high',  # Fila de alta prioridade
            timeout='30m'
        )
        
        # Atualizar integração
        integracao.status = 'enfileirado'
        integracao.job_id = job.id
        integracao.atualizado_em = datetime.utcnow()
        
        # Log
        log_reprocessamento = PortalLog(
            integracao_id=integracao_id,  # Campo correto: integracao_id
            acao='reprocessamento',  # Campo correto: acao
            sucesso=True,
            mensagem='Integração enfileirada para reprocessamento',
            dados_contexto={
                'job_id': job.id,
                'usuario': current_user.nome if current_user.is_authenticated else 'Sistema'
            }
        )
        db.session.add(log_reprocessamento)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Integração enfileirada para reprocessamento',
            'job_id': job.id,
            'status_url': f'/portal/api/status-job/{job.id}'
        })
        
    except Exception as e:
        logger.error(f"Erro ao reprocessar integração: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@portal_bp.route('/api/status-filas')
@login_required
def status_filas():
    """
    Mostra status das filas do Redis Queue
    """
    try:
        from rq import Queue
        from app.portal.workers import get_redis_connection
        
        redis_conn = get_redis_connection()
        
        queue_names = ['atacadao', 'high', 'default', 'low']
        status = {}
        
        for queue_name in queue_names:
            queue = Queue(queue_name, connection=redis_conn)
            
            status[queue_name] = {
                'pendentes': len(queue),
                'em_execucao': len(queue.started_job_registry),
                'concluidos': len(queue.finished_job_registry),
                'falhados': len(queue.failed_job_registry),
                'jobs': []
            }
            
            # Listar alguns jobs pendentes
            for job_id in queue.job_ids[:5]:
                try:
                    from rq.job import Job
                    job = Job.fetch(job_id, connection=redis_conn)
                    status[queue_name]['jobs'].append({
                        'id': job.id,
                        'funcao': job.func_name,
                        'criado_em': job.created_at.isoformat() if job.created_at else None
                    })
                except Exception:
                    pass
        
        return jsonify({
            'success': True,
            'filas': status
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar status das filas: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
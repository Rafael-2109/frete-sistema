"""
Rotas do módulo Portal de Agendamento
Integração com sistema de carteira e separação
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.portal import portal_bp
from app.portal.models import PortalIntegracao, PortalConfiguracao, PortalLog
from app.portal.atacadao.models import ProdutoDeParaAtacadao
from app.portal.utils.grupo_empresarial import GrupoEmpresarial
from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.separacao.models import Separacao
from app import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@portal_bp.route('/')
@login_required
def index():
    """Página principal do portal de agendamento"""
    # Buscar integrações recentes
    integracoes = PortalIntegracao.query.order_by(
        PortalIntegracao.criado_em.desc()
    ).limit(20).all()
    
    # Estatísticas
    stats = {
        'total': PortalIntegracao.query.count(),
        'aguardando': PortalIntegracao.query.filter_by(status='aguardando').count(),
        'confirmado': PortalIntegracao.query.filter_by(status='confirmado').count(),
        'erro': PortalIntegracao.query.filter_by(status='erro').count()
    }
    
    return render_template('portal/index.html', 
                         integracoes=integracoes,
                         stats=stats)

@portal_bp.route('/agendar/<lote_id>')
@login_required
def agendar_lote(lote_id):
    """Página para agendar um lote específico"""
    
    # Buscar dados do lote
    lote_separacao = Separacao.query.filter_by(
        separacao_lote_id=lote_id
    ).first()
    
    if not lote_separacao:
        # Tentar PreSeparacao
        lote_pre = PreSeparacaoItem.query.filter_by(
            separacao_lote_id=lote_id
        ).first()
        
        if not lote_pre:
            flash('Lote não encontrado', 'error')
            return redirect(url_for('portal.index'))
        
        # Dados do pré-separação
        cnpj = lote_pre.cnpj_cliente
        tipo_lote = 'pre_separacao'
    else:
        cnpj = lote_separacao.cnpj_cpf
        tipo_lote = 'separacao'
    
    # Identificar portal pelo CNPJ
    grupo = GrupoEmpresarial.identificar_grupo(cnpj)
    portal = GrupoEmpresarial.identificar_portal(cnpj)
    
    if not portal:
        flash('Cliente não possui portal de agendamento', 'warning')
        return redirect(request.referrer or url_for('portal.index'))
    
    # Buscar configuração do portal
    config = PortalConfiguracao.query.filter_by(
        portal=portal,
        ativo=True
    ).first()
    
    # Verificar se já existe integração
    integracao_existente = PortalIntegracao.query.filter_by(
        lote_id=lote_id,
        portal=portal
    ).first()
    
    return render_template('portal/agendar.html',
                         lote_id=lote_id,
                         tipo_lote=tipo_lote,
                         portal=portal,
                         grupo=grupo,
                         config=config,
                         integracao_existente=integracao_existente,
                         cnpj=cnpj)

@portal_bp.route('/api/solicitar-agendamento', methods=['POST'])
@login_required
def solicitar_agendamento():
    """API para solicitar agendamento no portal"""
    try:
        dados = request.json
        lote_id = dados.get('lote_id')
        data_agendamento = dados.get('data_agendamento')
        hora_agendamento = dados.get('hora_agendamento')
        transportadora = dados.get('transportadora')
        tipo_veiculo = dados.get('tipo_veiculo')
        
        # Buscar dados do lote
        itens = []
        tipo_lote = None
        portal = None
        cnpj = None
        pedido_cliente = None
        
        # Tentar Separacao primeiro
        lote_separacao = Separacao.query.filter_by(
            separacao_lote_id=lote_id
        ).all()
        
        if lote_separacao:
            tipo_lote = 'separacao'
            cnpj = lote_separacao[0].cnpj_cpf
            
            # Buscar pedido_cliente da CarteiraPrincipal
            for item in lote_separacao:
                carteira_item = CarteiraPrincipal.query.filter_by(
                    num_pedido=item.num_pedido
                ).first()
                
                if carteira_item and carteira_item.pedido_cliente:
                    pedido_cliente = carteira_item.pedido_cliente
                    break
                    
            itens = lote_separacao
        else:
            # Tentar PreSeparacao
            lote_pre = PreSeparacaoItem.query.filter_by(
                separacao_lote_id=lote_id
            ).all()
            
            if lote_pre:
                tipo_lote = 'pre_separacao'
                cnpj = lote_pre[0].cnpj_cliente
                
                # Buscar pedido_cliente
                for item in lote_pre:
                    carteira_item = CarteiraPrincipal.query.filter_by(
                        num_pedido=item.num_pedido
                    ).first()
                    
                    if carteira_item and carteira_item.pedido_cliente:
                        pedido_cliente = carteira_item.pedido_cliente
                        break
                        
                itens = lote_pre
        
        if not itens:
            return jsonify({
                'success': False,
                'message': 'Lote não encontrado'
            }), 404
        
        # Identificar portal
        portal = GrupoEmpresarial.identificar_portal(cnpj)
        
        if not portal:
            return jsonify({
                'success': False,
                'message': 'Cliente não possui portal de agendamento'
            }), 400
        
        if not pedido_cliente:
            return jsonify({
                'success': False,
                'message': 'Pedido do cliente não encontrado. Verifique o campo pedido_cliente na carteira.'
            }), 400
        
        # Criar ou atualizar integração
        integracao = PortalIntegracao.query.filter_by(
            lote_id=lote_id,
            portal=portal
        ).first()
        
        if not integracao:
            integracao = PortalIntegracao(
                portal=portal,
                lote_id=lote_id,
                tipo_lote=tipo_lote
            )
            db.session.add(integracao)
        
        # Atualizar dados
        integracao.status = 'processando'
        integracao.data_solicitacao = datetime.now()
        integracao.data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
        integracao.hora_agendamento = datetime.strptime(hora_agendamento, '%H:%M').time() if hora_agendamento else None
        integracao.usuario_solicitante = current_user.nome or 'Sistema'
        integracao.dados_enviados = {
            'pedido_cliente': pedido_cliente,
            'cnpj': cnpj,
            'transportadora': transportadora,
            'tipo_veiculo': tipo_veiculo,
            'data_agendamento': data_agendamento,
            'hora_agendamento': hora_agendamento
        }
        
        # Tentar commit com tratamento de erro
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar integração, fazendo rollback: {e}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': 'Erro ao salvar dados. Por favor, tente novamente.'
            }), 500
        
        # Executar agendamento (por enquanto síncrono, depois será Celery)
        resultado = executar_agendamento_portal(integracao.id)
        
        return jsonify({
            'success': resultado['success'],
            'message': resultado.get('message'),
            'protocolo': resultado.get('protocolo'),
            'integracao_id': integracao.id
        })
        
    except Exception as e:
        logger.error(f"Erro ao solicitar agendamento: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao processar solicitação: {str(e)}'
        }), 500

@portal_bp.route('/api/verificar-status/<int:integracao_id>')
@login_required
def verificar_status(integracao_id):
    """Verifica status de uma integração"""
    try:
        integracao = PortalIntegracao.query.get_or_404(integracao_id)
        
        # Se ainda não tem protocolo, não pode verificar
        if not integracao.protocolo:
            return jsonify({
                'success': False,
                'message': 'Integração não possui protocolo ainda'
            })
        
        # Verificação real no portal para Atacadão
        if integracao.portal == 'atacadao':
            from app.portal.atacadao.verificar_posicao import verificar_posicao_agendamento
            
            logger.info(f"Verificando posição do protocolo {integracao.protocolo}")
            resultado = verificar_posicao_agendamento(integracao.protocolo)
            
            if resultado['success']:
                # Atualizar banco com informações obtidas
                if resultado.get('status'):
                    # Mapear status do portal para nosso sistema
                    status_map = {
                        'aguardando': 'aguardando_confirmacao',
                        'confirmado': 'confirmado',
                        'cancelado': 'cancelado'
                    }
                    novo_status = status_map.get(resultado['status'], integracao.status)
                    
                    if novo_status != integracao.status:
                        integracao.status = novo_status
                        if novo_status == 'confirmado':
                            integracao.data_confirmacao = datetime.now()
                        
                        # Log da mudança
                        log = PortalLog(
                            integracao_id=integracao_id,
                            acao='status_atualizado',
                            sucesso=True,
                            mensagem=f"Status mudou para {novo_status}"
                        )
                        db.session.add(log)
                
                # Salvar dados adicionais
                integracao.resposta_portal = resultado
                
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
                
                return jsonify({
                    'success': True,
                    'status': integracao.status,
                    'protocolo': integracao.protocolo,
                    'posicao_fila': resultado.get('posicao_fila'),
                    'total_fila': resultado.get('total_fila'),
                    'data_prevista': resultado.get('data_prevista'),
                    'observacoes': resultado.get('observacoes'),
                    'message': resultado.get('message'),
                    'data_agendamento': integracao.data_agendamento.isoformat() if integracao.data_agendamento else None,
                    'data_confirmacao': integracao.data_confirmacao.isoformat() if integracao.data_confirmacao else None
                })
            else:
                return jsonify({
                    'success': False,
                    'message': resultado.get('message', 'Erro ao verificar status no portal')
                })
        
        # Para outros portais, retornar dados do banco
        return jsonify({
            'success': True,
            'status': integracao.status,
            'protocolo': integracao.protocolo,
            'data_agendamento': integracao.data_agendamento.isoformat() if integracao.data_agendamento else None,
            'data_confirmacao': integracao.data_confirmacao.isoformat() if integracao.data_confirmacao else None
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar status: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao verificar status: {str(e)}'
        }), 500

@portal_bp.route('/api/comparar-portal/<lote_id>')
@login_required
def comparar_portal(lote_id):
    """Compara dados da separação com o portal"""
    try:
        # Buscar dados da separação
        separacao_items = Separacao.query.filter_by(
            separacao_lote_id=lote_id
        ).all()
        
        if not separacao_items:
            # Tentar PreSeparacao
            separacao_items = PreSeparacaoItem.query.filter_by(
                separacao_lote_id=lote_id
            ).all()
            
            if not separacao_items:
                return jsonify({
                    'success': False,
                    'message': 'Lote não encontrado'
                }), 404
        
        # Identificar portal pelo CNPJ
        cnpj = separacao_items[0].cnpj_cpf if hasattr(separacao_items[0], 'cnpj_cpf') else separacao_items[0].cnpj_cliente
        portal = GrupoEmpresarial.identificar_portal(cnpj)
        
        # Buscar integração existente
        integracao = PortalIntegracao.query.filter_by(
            lote_id=lote_id,
            portal=portal
        ).first()
        
        # Preparar dados da separação
        produtos_separacao = []
        for item in separacao_items:
            produtos_separacao.append({
                'cod_produto': item.cod_produto,
                'nome_produto': getattr(item, 'nome_produto', '-'),
                'quantidade': float(item.qtd_saldo) if hasattr(item, 'qtd_saldo') else float(item.qtd_selecionada_usuario)
            })
        
        # Se há integração, buscar dados do portal
        portal_data = None
        divergencias = []
        
        if integracao and integracao.protocolo:
            # TODO: Implementar busca real no portal
            # Por enquanto, simular dados
            portal_data = {
                'protocolo': integracao.protocolo,
                'produtos': [
                    # Simular produtos do portal
                    {
                        'codigo': '35642',
                        'mercadoria': 'AZEITONA VERDE CAMPO BELO BALDE 2KG',
                        'quantidade': 8
                    },
                    {
                        'codigo': '46626',
                        'mercadoria': 'AZEITONA VERDE CAMPO BELO S/C POUCH 150G',
                        'quantidade': 24
                    }
                ]
            }
            
            # Verificar divergências
            # TODO: Implementar comparação real com DE-PARA
        
        return jsonify({
            'success': True,
            'separacao': {
                'lote_id': lote_id,
                'produtos': produtos_separacao
            },
            'portal': portal,
            'portal_data': portal_data,
            'divergencias': divergencias
        })
        
    except Exception as e:
        logger.error(f"Erro ao comparar com portal: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@portal_bp.route('/api/extrair-confirmacoes')
@login_required
def extrair_confirmacoes():
    """Extrai confirmações pendentes dos portais"""
    try:
        # Buscar integrações aguardando confirmação
        integracoes = PortalIntegracao.query.filter(
            PortalIntegracao.status.in_(['aguardando_confirmacao', 'processando']),
            PortalIntegracao.protocolo.isnot(None)
        ).all()
        
        resultados = []
        
        for integracao in integracoes:
            # TODO: Implementar extração real do portal
            # Por enquanto, simular confirmação
            
            if integracao.portal == 'atacadao':
                # Simular verificação no Atacadão
                integracao.status = 'confirmado'
                integracao.data_confirmacao = datetime.now()
                
                # Atualizar lote original
                if integracao.tipo_lote == 'separacao':
                    Separacao.query.filter_by(
                        separacao_lote_id=integracao.lote_id
                    ).update({
                        'agendamento_confirmado': True,
                        'protocolo': integracao.protocolo
                    })
                
                resultados.append({
                    'lote_id': integracao.lote_id,
                    'protocolo': integracao.protocolo,
                    'status': 'confirmado'
                })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'confirmacoes': len(resultados),
            'resultados': resultados
        })
        
    except Exception as e:
        logger.error(f"Erro ao extrair confirmações: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@portal_bp.route('/configuracao')
@login_required
def configuracao():
    """Página de configuração dos portais"""
    configs = PortalConfiguracao.query.all()
    return render_template('portal/configuracao.html', configs=configs)

@portal_bp.route('/depara')
@login_required
def depara():
    """Página de mapeamento DE-PARA de produtos"""
    # Por enquanto, só Atacadão
    mapeamentos = ProdutoDeParaAtacadao.query.filter_by(ativo=True).all()
    return render_template('portal/depara.html', mapeamentos=mapeamentos)

def executar_agendamento_portal(integracao_id):
    """
    Executa o agendamento no portal
    Por enquanto síncrono, depois será task Celery
    """
    try:
        # Buscar integração com nova sessão para evitar problemas de SSL
        try:
            integracao = PortalIntegracao.query.get(integracao_id)
        except Exception as e:
            logger.error(f"Erro ao buscar integração, tentando rollback: {e}")
            db.session.rollback()
            integracao = PortalIntegracao.query.get(integracao_id)
        
        if not integracao:
            return {'success': False, 'message': 'Integração não encontrada'}
        
        # Log início
        log = PortalLog(
            integracao_id=integracao_id,
            acao='inicio_agendamento',
            sucesso=True,
            mensagem='Iniciando processo de agendamento'
        )
        db.session.add(log)
        
        # Fazer commit parcial para garantir que o log seja salvo
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar log inicial, fazendo rollback: {e}")
            db.session.rollback()
        
        if integracao.portal == 'atacadao':
            # Usar cliente Atacadão com Playwright - LOCALIZADO CORRETAMENTE
            try:
                logger.info("🚀 Usando Playwright para automação")
                client = AtacadaoPlaywrightClient(headless=True)
                
                # Verificar se sessão existe
                import os
                if not os.path.exists("storage_state_atacadao.json"):
                    raise Exception("Sessão não configurada. Execute: python configurar_sessao_atacadao.py")
                
                client.iniciar_sessao()
                
                # Preparar dados
                dados = integracao.dados_enviados or {}
                
                # Executar agendamento com Playwright
                resultado = client.criar_agendamento(dados)
                
                # Fechar navegador
                client.fechar()
                
                if resultado.get('success'):
                    # Atualizar integração
                    integracao.protocolo = resultado.get('protocolo') 
                    integracao.status = 'aguardando_confirmacao'
                    integracao.resposta_portal = resultado
                    
                    # IMPORTANTE: Atualizar também o protocolo na tabela Separacao!
                    from app.separacao.models import Separacao
                    separacoes = Separacao.query.filter_by(
                        separacao_lote_id=integracao.lote_id
                    ).all()
                    for sep in separacoes:
                        sep.protocolo = resultado.get('protocolo')
                    
                    # Log sucesso
                    log = PortalLog(
                        integracao_id=integracao_id,
                        acao='agendamento_criado',
                        sucesso=True,
                        mensagem=f"Protocolo: {resultado.get('protocolo')}"
                    )
                    db.session.add(log)
                    
                    # Commit com tratamento de erro
                    try:
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Erro ao salvar resultado, fazendo rollback: {e}")
                        db.session.rollback()
                        # Tentar novamente
                        try:
                            db.session.merge(integracao)
                            db.session.merge(log)
                            for sep in separacoes:
                                db.session.merge(sep)
                            db.session.commit()
                        except Exception as e2:
                            logger.error(f"Erro na segunda tentativa: {e2}")
                            # Retornar sucesso parcial
                            return {
                                'success': True,
                                'protocolo': resultado.get('protocolo'),
                                'message': 'Agendamento realizado mas erro ao salvar no banco. Protocolo: ' + resultado.get('protocolo', 'N/A')
                            }
                    
                    return {
                        'success': True,
                        'protocolo': resultado.get('protocolo'),
                        'message': 'Agendamento solicitado com sucesso'
                    }
                else:
                    # Log erro
                    integracao.status = 'erro'
                    integracao.ultimo_erro = resultado.get('message')
                    
                    log = PortalLog(
                        integracao_id=integracao_id,
                        acao='erro_agendamento',
                        sucesso=False,
                        mensagem=resultado.get('message')
                    )
                    db.session.add(log)
                    db.session.commit()
                    
                    return {
                        'success': False,
                        'message': resultado.get('message', 'Erro ao agendar')
                    }
                    
            except Exception as e:
                logger.error(f"Erro ao executar agendamento Atacadão: {e}")
                
                # Fazer rollback e tentar novamente
                try:
                    db.session.rollback()
                    # Buscar integração novamente
                    integracao = PortalIntegracao.query.get(integracao_id)
                    if integracao:
                        integracao.status = 'erro'
                        integracao.ultimo_erro = str(e)
                        db.session.commit()
                except:
                    # Se ainda falhar, apenas fazer rollback
                    db.session.rollback()
                
                return {
                    'success': False,
                    'message': f'Erro ao conectar com portal: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Portal {integracao.portal} ainda não implementado'
            }
            
    except Exception as e:
        logger.error(f"Erro geral ao executar agendamento: {e}")
        return {
            'success': False,
            'message': f'Erro inesperado: {str(e)}'
        }
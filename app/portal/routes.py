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

@portal_bp.route('/central')
@login_required
def central_portais():
    """Central de Portais de Agendamento - Nova interface unificada"""
    return render_template('portal/central_portais.html')

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
            
            # 🆕 Buscar pedido_cliente DIRETO da Separacao
            for item in lote_separacao:
                if item.pedido_cliente:
                    pedido_cliente = item.pedido_cliente
                    break
            
            # Se não encontrar na Separacao, tentar CarteiraPrincipal (compatibilidade)
            if not pedido_cliente:
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
        
        # Calcular peso total dos itens
        peso_total = 0
        for item in itens:
            # Para Separacao
            if hasattr(item, 'peso'):
                peso_total += float(item.peso) if item.peso else 0
            # Para PreSeparacaoItem
            elif hasattr(item, 'peso_original_item'):
                peso_total += float(item.peso_original_item) if item.peso_original_item else 0
        
        logger.info(f"Peso total do lote: {peso_total:.2f} kg")
        
        # Atualizar dados
        integracao.status = 'processando'
        integracao.data_solicitacao = datetime.now()
        integracao.data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
        integracao.hora_agendamento = datetime.strptime(hora_agendamento, '%H:%M').time() if hora_agendamento else None
        integracao.usuario_solicitante = current_user.nome or 'Sistema'
        # Montar lista de produtos do lote com conversão DE-PARA
        from app.portal.atacadao.models import ProdutoDeParaAtacadao
        from app.faturamento.models import FaturamentoProduto
        from app.monitoramento.models import EntregaMonitorada
        
        produtos = []
        produtos_no_portal = set()  # Para rastrear quais produtos estão no portal
        numero_nf_usado = None  # Para rastreabilidade
        
        # 🆕 FLUXO CORRETO: EntregaMonitorada → FaturamentoProduto → Separacao
        # Buscar primeiro pedido da separação
        primeiro_pedido = itens[0].num_pedido if itens else None
        
        # Buscar EntregaMonitorada relacionada através do separacao_lote_id
        entrega_monitorada = None
        produtos_faturados = []
        
        if lote_id:
            # Buscar EntregaMonitorada pelo lote de separação
            entrega_monitorada = EntregaMonitorada.query.filter_by(
                separacao_lote_id=lote_id
            ).first()
            
            if entrega_monitorada:
                numero_nf_usado = entrega_monitorada.numero_nf
                logger.info(f"🔍 EntregaMonitorada encontrada: NF {numero_nf_usado}")
                
                # Buscar produtos faturados através da NF
                produtos_faturados = FaturamentoProduto.query.filter_by(
                    numero_nf=numero_nf_usado,
                    status_nf='Lançado'
                ).all()
                
                logger.info(f"📦 Encontrados {len(produtos_faturados)} produtos faturados na NF {numero_nf_usado}")
                
                # Validar que origem corresponde ao pedido
                if produtos_faturados and produtos_faturados[0].origem != primeiro_pedido:
                    logger.warning(f"⚠️ NF {numero_nf_usado} tem origem {produtos_faturados[0].origem}, esperado {primeiro_pedido}")
        
        # Se não encontrou por EntregaMonitorada, tentar buscar direto por origem
        if not produtos_faturados and primeiro_pedido:
            produtos_faturados = FaturamentoProduto.query.filter_by(
                origem=primeiro_pedido,
                status_nf='Lançado'
            ).all()
            
            if produtos_faturados:
                numero_nf_usado = produtos_faturados[0].numero_nf
                logger.info(f"📦 Encontrados {len(produtos_faturados)} produtos via origem {primeiro_pedido}, NF {numero_nf_usado}")
        
        # Decidir fonte de produtos: Faturamento ou Separacao
        if produtos_faturados:
            # 🆕 USAR PRODUTOS FATURADOS (fluxo principal)
            logger.info(f"✅ Usando produtos do FaturamentoProduto da NF {numero_nf_usado}")
            
            if portal == 'atacadao':
                # Buscar TODOS os produtos DE-PARA ativos
                todos_depara = ProdutoDeParaAtacadao.query.filter_by(ativo=True).all()
                depara_dict = {d.codigo_nosso: d.codigo_atacadao for d in todos_depara}
                
                for prod_fat in produtos_faturados:
                    codigo_nosso = prod_fat.cod_produto
                    quantidade = float(prod_fat.qtd_produto_faturado or 0)
                    
                    # Buscar conversão DE-PARA
                    codigo_portal = depara_dict.get(codigo_nosso)
                    
                    if codigo_portal:
                        produtos_no_portal.add(codigo_portal)
                        produtos.append({
                            'codigo': codigo_portal,  # Código convertido para o portal
                            'codigo_nosso': codigo_nosso,  # Nosso código original
                            'quantidade': quantidade,
                            'numero_nf': prod_fat.numero_nf  # 🆕 Rastreabilidade com NF
                        })
                        logger.info(f"  ✅ Produto {codigo_nosso} → {codigo_portal} (Qtd: {quantidade}, NF: {prod_fat.numero_nf})")
                    else:
                        logger.warning(f"  ⚠️ Produto {codigo_nosso} sem DE-PARA configurado")
            else:
                # Para outros portais, usar código direto
                for prod_fat in produtos_faturados:
                    produtos.append({
                        'codigo': prod_fat.cod_produto,
                        'quantidade': float(prod_fat.qtd_produto_faturado or 0),
                        'numero_nf': prod_fat.numero_nf
                    })
        else:
            # FALLBACK: Usar produtos da Separacao (quando não há NF faturada)
            logger.info("⚠️ Sem NF faturada, usando produtos da Separacao como fallback")
            
            if portal == 'atacadao':
                # Buscar TODOS os produtos DE-PARA ativos
                todos_depara = ProdutoDeParaAtacadao.query.filter_by(ativo=True).all()
                depara_dict = {d.codigo_nosso: d.codigo_atacadao for d in todos_depara}
                
                for item in itens:
                    # Obter código e quantidade conforme o tipo do item
                    if hasattr(item, 'cod_produto'):
                        codigo_nosso = item.cod_produto
                        quantidade = item.qtd_saldo if hasattr(item, 'qtd_saldo') else 0
                        
                        # Buscar conversão DE-PARA
                        codigo_portal = depara_dict.get(codigo_nosso)
                        
                        if codigo_portal:
                            produtos_no_portal.add(codigo_portal)
                            produtos.append({
                                'codigo': codigo_portal,  # Código convertido para o portal
                                'codigo_nosso': codigo_nosso,  # Nosso código original
                                'quantidade': float(quantidade) if quantidade else 0
                            })
            else:
                # Para outros portais, usar código direto
                for item in itens:
                    if hasattr(item, 'cod_produto'):
                        codigo = item.cod_produto
                        quantidade = item.qtd_saldo if hasattr(item, 'qtd_saldo') else 0
                        produtos.append({
                            'codigo': codigo,
                            'quantidade': float(quantidade) if quantidade else 0
                        })
        
        integracao.dados_enviados = {
            'pedido_cliente': pedido_cliente,
            'cnpj': cnpj,
            'transportadora': transportadora,
            'tipo_veiculo': tipo_veiculo,
            'peso_total': peso_total,  # Adicionar peso total
            'data_agendamento': data_agendamento,
            'hora_agendamento': hora_agendamento,
            'produtos': produtos  # Adicionar produtos para seleção no portal
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
        
        # Guardar o ID antes de executar (a sessão será removida)
        integracao_id = integracao.id
        
        # Executar agendamento (por enquanto síncrono, depois será Celery)
        resultado = executar_agendamento_portal(integracao_id)
        
        return jsonify({
            'success': resultado['success'],
            'message': resultado.get('message'),
            'protocolo': resultado.get('protocolo'),
            'integracao_id': integracao_id
        })
        
    except Exception as e:
        logger.error(f"Erro ao solicitar agendamento: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao processar solicitação: {str(e)}'
        }), 500

@portal_bp.route('/api/solicitar-agendamento-nf', methods=['POST'])
@login_required
def solicitar_agendamento_nf():
    """
    API para solicitar agendamento no portal usando numero_nf como índice
    Mantém EXATAMENTE a mesma estrutura de dados_enviados da função original
    """
    try:
        dados = request.json
        numero_nf = dados.get('numero_nf')
        data_agendamento = dados.get('data_agendamento')
        hora_agendamento = dados.get('hora_agendamento')
        transportadora = dados.get('transportadora')
        tipo_veiculo = dados.get('tipo_veiculo')
        
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
        
        # Importar modelos necessários
        from app.monitoramento.models import EntregaMonitorada
        from app.faturamento.models import FaturamentoProduto
        from app.separacao.models import Separacao
        
        # 1️⃣ BUSCAR EntregaMonitorada pela NF
        entrega_monitorada = EntregaMonitorada.query.filter_by(
            numero_nf=numero_nf
        ).first()
        
        if not entrega_monitorada:
            return jsonify({
                'success': False,
                'message': f'Entrega não encontrada para NF {numero_nf}'
            }), 404
        
        logger.info(f"📦 EntregaMonitorada encontrada - NF: {numero_nf}, Cliente: {entrega_monitorada.cliente}")
        
        # 2️⃣ BUSCAR PRODUTOS do FaturamentoProduto
        produtos_faturados = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            status_nf='Lançado'
        ).all()
        
        if not produtos_faturados:
            return jsonify({
                'success': False,
                'message': f'Nenhum produto faturado encontrado para NF {numero_nf}'
            }), 404
        
        logger.info(f"✅ {len(produtos_faturados)} produtos encontrados no FaturamentoProduto")
        
        # 3️⃣ IDENTIFICAR CNPJ e PORTAL
        cnpj = produtos_faturados[0].cnpj_cliente if produtos_faturados else None
        
        if not cnpj:
            return jsonify({
                'success': False,
                'message': 'CNPJ do cliente não encontrado nos produtos faturados'
            }), 400
        
        portal = GrupoEmpresarial.identificar_portal(cnpj)
        
        if not portal:
            return jsonify({
                'success': False,
                'message': f'Cliente {cnpj} não possui portal de agendamento'
            }), 400
        
        logger.info(f"🌐 Portal identificado: {portal}")
        
        # 4️⃣ BUSCAR pedido_cliente através do fluxo correto
        pedido_cliente = None
        origem_pedido = produtos_faturados[0].origem if produtos_faturados else None
        
        if origem_pedido:
            # Buscar na Separacao usando origem como num_pedido
            separacao_origem = Separacao.query.filter_by(
                num_pedido=origem_pedido
            ).first()
            
            if separacao_origem and separacao_origem.pedido_cliente:
                pedido_cliente = separacao_origem.pedido_cliente
                logger.info(f"✅ pedido_cliente encontrado: {pedido_cliente} (via FaturamentoProduto.origem: {origem_pedido})")
            else:
                logger.warning(f"⚠️ pedido_cliente não encontrado para origem: {origem_pedido}")
        
        if not pedido_cliente:
            return jsonify({
                'success': False,
                'message': 'Pedido do cliente não encontrado. Verifique o campo pedido_cliente na Separacao.'
            }), 400
        
        # 5️⃣ CONVERTER PRODUTOS com DE-PARA (mantendo estrutura idêntica)
        produtos = []
        produtos_no_portal = set()
        
        if portal == 'atacadao':
            # Buscar todos os DE-PARA ativos
            todos_depara = ProdutoDeParaAtacadao.query.filter_by(ativo=True).all()
            depara_dict = {d.codigo_nosso: d.codigo_atacadao for d in todos_depara}
            
            for prod_fat in produtos_faturados:
                codigo_nosso = prod_fat.cod_produto
                quantidade = float(prod_fat.qtd_produto_faturado or 0)
                
                # Buscar conversão DE-PARA
                codigo_portal = depara_dict.get(codigo_nosso)
                
                if codigo_portal:
                    produtos_no_portal.add(codigo_portal)
                    produtos.append({
                        'codigo': codigo_portal,  # Código convertido
                        'codigo_nosso': codigo_nosso,  # Nosso código
                        'quantidade': quantidade,
                        'numero_nf': prod_fat.numero_nf  # Rastreabilidade
                    })
                    logger.info(f"  ✅ {codigo_nosso} → {codigo_portal} | {prod_fat.nome_produto} | Qtd: {quantidade}")
                else:
                    logger.warning(f"  ⚠️ Produto {codigo_nosso} sem DE-PARA configurado")
        else:
            # Outros portais - usar código direto
            for prod_fat in produtos_faturados:
                produtos.append({
                    'codigo': prod_fat.cod_produto,
                    'quantidade': float(prod_fat.qtd_produto_faturado or 0),
                    'numero_nf': prod_fat.numero_nf
                })
        
        if not produtos:
            return jsonify({
                'success': False,
                'message': 'Nenhum produto válido para agendamento (verificar DE-PARA)'
            }), 400
        
        # 6️⃣ Calcular peso total
        peso_total = sum(float(p.peso_total or 0) for p in produtos_faturados)
        logger.info(f"Peso total calculado: {peso_total:.2f} kg")
        
        # 7️⃣ CRIAR/ATUALIZAR INTEGRAÇÃO (usando numero_nf ao invés de lote_id)
        integracao = PortalIntegracao.query.filter_by(
            numero_nf=numero_nf,
            portal=portal
        ).first()
        
        if not integracao:
            integracao = PortalIntegracao(
                portal=portal,
                numero_nf=numero_nf,
                tipo_lote='entrega_monitorada'
            )
            db.session.add(integracao)
        
        # 8️⃣ MONTAR dados_enviados COM EXATAMENTE A MESMA ESTRUTURA
        integracao.dados_enviados = {
            'pedido_cliente': pedido_cliente,
            'cnpj': cnpj,
            'transportadora': transportadora,
            'tipo_veiculo': tipo_veiculo,
            'peso_total': peso_total,
            'data_agendamento': data_agendamento,
            'hora_agendamento': hora_agendamento,
            'produtos': produtos
        }
        
        integracao.status = 'processando'
        integracao.data_solicitacao = datetime.now()
        integracao.data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
        integracao.hora_agendamento = datetime.strptime(hora_agendamento, '%H:%M').time() if hora_agendamento else None
        integracao.usuario_solicitante = current_user.nome or 'Sistema'
        
        # Salvar antes de executar
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar integração: {e}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': 'Erro ao salvar dados. Por favor, tente novamente.'
            }), 500
        
        # Guardar o ID
        integracao_id = integracao.id
        
        # 9️⃣ EXECUTAR AGENDAMENTO (usando a mesma função)
        resultado = executar_agendamento_portal(integracao_id)
        
        # 🔟 ATUALIZAR EntregaMonitorada e criar AgendamentoEntrega
        if resultado.get('success'):
            # Buscar novamente após execução
            entrega_monitorada = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
            integracao = PortalIntegracao.query.get(integracao_id)
            
            if entrega_monitorada and integracao:
                # Atualizar data_agenda em EntregaMonitorada
                if integracao.data_agendamento:
                    entrega_monitorada.data_agenda = integracao.data_agendamento
                
                # Criar registro em AgendamentoEntrega
                from app.monitoramento.models import AgendamentoEntrega
                agendamento = AgendamentoEntrega(
                    entrega_id=entrega_monitorada.id,
                    data_agendada=integracao.data_agendamento,
                    hora_agendada=integracao.hora_agendamento,
                    forma_agendamento='Portal',
                    contato_agendamento=f'Portal {portal.upper()}',
                    protocolo_agendamento=resultado.get('protocolo'),
                    motivo='Agendamento via Portal',
                    observacao=f'Agendamento automático via API - NF {numero_nf}',
                    autor=current_user.nome or 'Sistema',
                    status='confirmado' if resultado.get('agendamento_confirmado') else 'aguardando'
                )
                db.session.add(agendamento)
                
                try:
                    db.session.commit()
                    logger.info(f"✅ EntregaMonitorada e AgendamentoEntrega atualizados - Protocolo: {resultado.get('protocolo')}")
                except Exception as e:
                    logger.error(f"Erro ao atualizar registros: {e}")
                    db.session.rollback()
        
        return jsonify({
            'success': resultado['success'],
            'message': resultado.get('message'),
            'protocolo': resultado.get('protocolo'),
            'data_agendamento': str(integracao.data_agendamento) if integracao else None,
            'integracao_id': integracao_id
        })
        
    except Exception as e:
        logger.error(f"Erro ao solicitar agendamento via NF: {e}")
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
            from app.portal.atacadao.verificacao_protocolo import verificar_posicao_agendamento
            
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
                except Exception:
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
        # Buscar integração e extrair dados necessários ANTES de fechar a conexão
        try:
            integracao = PortalIntegracao.query.get(integracao_id)
            if not integracao:
                return {'success': False, 'message': 'Integração não encontrada'}
            
            # Extrair todos os dados necessários da integração
            portal = integracao.portal
            lote_id = integracao.lote_id
            dados_enviados = integracao.dados_enviados or {}
            
        except Exception as e:
            logger.error(f"Erro ao buscar integração: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Erro ao buscar dados: {str(e)}'}
        
        # Log início
        log = PortalLog(
            integracao_id=integracao_id,
            acao='inicio_agendamento',
            sucesso=True,
            mensagem='Iniciando processo de agendamento'
        )
        db.session.add(log)
        
        # Fazer commit e FECHAR sessão antes de iniciar Playwright
        try:
            db.session.commit()
            db.session.close()  # Fecha a conexão antes da automação
        except Exception as e:
            logger.error(f"Erro ao salvar log inicial: {e}")
            db.session.rollback()
            db.session.close()
        
        if portal == 'atacadao':
            # Usar cliente Atacadão com Playwright - LOCALIZADO CORRETAMENTE
            resultado = None
            try:
                logger.info("🚀 Usando Playwright para automação")
                client = AtacadaoPlaywrightClient(headless=True)
                
                # Garantir sessão válida (faz re-login automático se necessário)
                from app.portal.routes_sessao import garantir_sessao_valida
                
                # Obter CNPJ do lote para buscar credenciais específicas
                cnpj = dados_enviados.get('cnpj')
                
                if not garantir_sessao_valida('atacadao', cnpj):
                    # Se não conseguiu garantir sessão, verificar se existe arquivo manual
                    import os
                    if not os.path.exists("storage_state_atacadao.json"):
                        raise Exception("Sessão não configurada. Configure em: /portal/configurar-sessao ou execute: python configurar_sessao_atacadao.py")
                
                client.iniciar_sessao()
                
                # Executar agendamento com Playwright (usando dados já extraídos)
                resultado = client.criar_agendamento(dados_enviados)
                
                # Converter data para formato DD/MM/AAAA se necessário
                data_agendamento = dados_enviados.get('data_agendamento')
                if data_agendamento and '-' in str(data_agendamento):
                    # Converter de YYYY-MM-DD para DD/MM/AAAA
                    from datetime import datetime
                    try:
                        dt = datetime.strptime(str(data_agendamento), '%Y-%m-%d')
                        data_agendamento = dt.strftime('%d/%m/%Y')
                    except Exception:
                        pass  # Manter como está se falhar
                
                #resultado = client.criar_agendamento_completo(
                #    pedido_cliente=dados_enviados.get('pedido_cliente'),
                #    data_agendamento=data_agendamento,
                #    produtos=dados_enviados.get('produtos')
                #)
                
                # Fechar navegador
                client.fechar()
                
                # Após Playwright, atualizar dados no banco
                if resultado and resultado.get('success'):
                    # Import Separacao para atualizar protocolo
                    from app.separacao.models import Separacao
                    
                    # Buscar integração novamente (sessão foi removida mas não fechada)
                    integracao = PortalIntegracao.query.get(integracao_id)
                    if integracao:
                        # Atualizar integração
                        integracao.protocolo = resultado.get('protocolo') 
                        integracao.status = 'aguardando_confirmacao'
                        integracao.resposta_portal = resultado
                    
                    # IMPORTANTE: Atualizar também os campos na tabela Separacao!
                    separacoes = Separacao.query.filter_by(
                        separacao_lote_id=lote_id
                    ).all()
                    
                    # Buscar data de agendamento da integração
                    data_agend = integracao.data_agendamento if integracao else None
                    
                    for sep in separacoes:
                        sep.protocolo = resultado.get('protocolo')
                        sep.agendamento = data_agend  # Atualizar data de agendamento
                        sep.agendamento_confirmado = False  # False até ser confirmado pelo portal
                    
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
                    # Erro no agendamento - reabrir sessão para salvar erro
                    integracao = PortalIntegracao.query.get(integracao_id)
                    if integracao:
                        integracao.status = 'erro'
                        integracao.ultimo_erro = resultado.get('message') if resultado else 'Erro desconhecido'
                    
                    log = PortalLog(
                        integracao_id=integracao_id,
                        acao='erro_agendamento',
                        sucesso=False,
                        mensagem=resultado.get('message') if resultado else 'Erro desconhecido'
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
                except Exception:
                    # Se ainda falhar, apenas fazer rollback
                    db.session.rollback()
                
                return {
                    'success': False,
                    'message': f'Erro ao conectar com portal: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Portal {portal} ainda não implementado'
            }
            
    except Exception as e:
        logger.error(f"Erro geral ao executar agendamento: {e}")
        return {
            'success': False,
            'message': f'Erro inesperado: {str(e)}'
        }
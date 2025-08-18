"""
API Routes para análise de ruptura de estoque por pedido
"""

from flask import jsonify, request
from app import db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import ProgramacaoProducao
from app.carteira.main_routes import carteira_bp
from sqlalchemy import func, case
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/ruptura/analisar-pedido/<num_pedido>', methods=['GET'])
def analisar_ruptura_pedido(num_pedido):
    """
    Analisa ruptura de estoque para um pedido específico
    Retorna análise detalhada ou indica que pedido está OK
    """
    try:
        # Buscar todos os itens do pedido - SEM campos de estoque que não são usados
        itens = db.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido,
            CarteiraPrincipal.preco_produto_pedido
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()
        
        if not itens:
            return jsonify({
                'success': False,
                'message': 'Pedido não encontrado'
            }), 404
            
        # Importar o serviço que JÁ FUNCIONA no cardex
        from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
        
        # Análise dos itens
        itens_com_ruptura = []
        itens_disponiveis_lista = []  # Lista dos itens SEM ruptura
        valor_total_pedido = 0
        valor_com_ruptura = 0
        total_itens = len(itens)
        itens_disponiveis = 0  # Contador de itens SEM ruptura
        data_max_disponibilidade = None  # Data mais distante para ter todos disponíveis
        tem_item_sem_producao = False  # Flag para itens em ruptura sem produção
        datas_producao_ruptura = []  # Lista de datas de produção dos itens em ruptura
        
        for item in itens:
            valor_item = float(item.qtd_saldo_produto_pedido * (item.preco_produto_pedido or 0))
            valor_total_pedido += valor_item
            
            # Usar EXATAMENTE o mesmo método que o workspace usa (QUE FUNCIONA!)
            projecao = ServicoEstoqueTempoReal.get_projecao_completa(item.cod_produto, dias=7)
            
            # Se não tem projeção, usar 0
            if not projecao:
                estoque_d7 = 0
            else:
                # Usar o MESMO campo que o workspace usa: menor_estoque_d7
                estoque_d7 = float(projecao.get('menor_estoque_d7', 0))
                
                # Se menor_estoque_d7 não existe, tentar pegar do último dia da projeção
                if estoque_d7 == 0 and projecao.get('projecao') and len(projecao['projecao']) > 0:
                    estoque_d7 = float(projecao['projecao'][-1].get('estoque_final', 0))
            
            qtd_saldo = float(item.qtd_saldo_produto_pedido)
            
            if qtd_saldo > estoque_d7:
                ruptura = qtd_saldo - estoque_d7
                valor_com_ruptura += valor_item
                
                # Buscar produção programada para QUALQUER data futura (não apenas 7 dias)
                # Buscar TODAS as produções futuras para calcular quando terá estoque suficiente
                producoes_futuras = db.session.query(
                    ProgramacaoProducao.data_programacao,
                    func.sum(ProgramacaoProducao.qtd_programada).label('qtd_producao')
                ).filter(
                    ProgramacaoProducao.cod_produto == item.cod_produto,
                    ProgramacaoProducao.data_programacao >= datetime.now().date()
                ).group_by(
                    ProgramacaoProducao.data_programacao
                ).order_by(
                    ProgramacaoProducao.data_programacao
                ).all()
                
                # Calcular quando terá estoque suficiente
                data_disponivel = None
                qtd_acumulada = estoque_d7
                primeira_producao = None
                qtd_primeira_producao = 0
                
                if producoes_futuras:
                    primeira_producao = producoes_futuras[0]
                    qtd_primeira_producao = float(primeira_producao.qtd_producao)
                    
                    for prod in producoes_futuras:
                        qtd_acumulada += float(prod.qtd_producao)
                        if qtd_acumulada >= qtd_saldo:
                            data_disponivel = prod.data_programacao
                            break
                    
                    # Adicionar data de disponibilidade à lista para calcular máximo
                    if data_disponivel:
                        datas_producao_ruptura.append(data_disponivel)
                else:
                    # Item em ruptura SEM produção programada
                    tem_item_sem_producao = True
                
                itens_com_ruptura.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_saldo': int(qtd_saldo),
                    'estoque_min_d7': int(estoque_d7) if estoque_d7 > 0 else int(estoque_d7),
                    'ruptura_qtd': int(ruptura),
                    'data_producao': primeira_producao.data_programacao.isoformat() if primeira_producao else None,
                    'qtd_producao': int(qtd_primeira_producao),
                    'data_disponivel': data_disponivel.isoformat() if data_disponivel else None
                })
            else:
                # Item disponível (sem ruptura)
                itens_disponiveis += 1
                itens_disponiveis_lista.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_saldo': int(qtd_saldo),
                    'estoque_min_d7': int(estoque_d7),
                    'preco_unitario': float(item.preco_produto_pedido or 0),
                    'valor_total': valor_item
                })
        
        # Se não há ruptura, pedido está OK
        if not itens_com_ruptura:
            return jsonify({
                'success': True,
                'pedido_ok': True,
                'percentual_disponibilidade': 100,
                'data_disponibilidade_total': 'agora',
                'message': 'Pedido OK - Todos os itens disponíveis'
            })
            
        # Calcular percentual de ruptura por VALOR
        percentual_ruptura = (valor_com_ruptura / valor_total_pedido * 100) if valor_total_pedido > 0 else 0
        
        # Calcular percentual de DISPONIBILIDADE por VALOR (100% - % ruptura)
        valor_disponivel = valor_total_pedido - valor_com_ruptura
        percentual_disponibilidade = (valor_disponivel / valor_total_pedido * 100) if valor_total_pedido > 0 else 0
        
        # Determinar data de disponibilidade total
        if tem_item_sem_producao:
            # Se tem algum item sem produção programada
            data_disponibilidade_total = None  # "Total Não Disp."
        elif datas_producao_ruptura:
            # Pegar a data mais distante (quando TODOS estarão disponíveis)
            data_max_disponibilidade = max(datas_producao_ruptura)
            data_disponibilidade_total = data_max_disponibilidade.isoformat()
        else:
            # Não deveria chegar aqui, mas por segurança
            data_disponibilidade_total = None
        
        # Determinar criticidade baseado nos critérios fornecidos
        qtd_itens_ruptura = len(itens_com_ruptura)
        if qtd_itens_ruptura > 3 and percentual_ruptura > 10:
            criticidade = 'CRITICA'
        elif qtd_itens_ruptura <= 3 and percentual_ruptura <= 10:
            criticidade = 'ALTA'
        elif qtd_itens_ruptura <= 2 and percentual_ruptura <= 5:
            criticidade = 'MEDIA'
        else:
            criticidade = 'BAIXA'
            
        return jsonify({
            'success': True,
            'pedido_ok': False,
            'percentual_disponibilidade': round(percentual_disponibilidade, 0),  # Percentual por VALOR disponível
            'data_disponibilidade_total': data_disponibilidade_total,  # Data quando todos estarão disponíveis ou None
            'resumo': {
                'num_pedido': num_pedido,
                'percentual_ruptura': round(percentual_ruptura, 2),
                'percentual_disponibilidade': round(percentual_disponibilidade, 0),  # Por VALOR
                'percentual_itens_disponiveis': round((itens_disponiveis / total_itens * 100) if total_itens > 0 else 0, 0),  # Por QUANTIDADE
                'qtd_itens_ruptura': qtd_itens_ruptura,
                'qtd_itens_disponiveis': itens_disponiveis,
                'total_itens': total_itens,
                'criticidade': criticidade,
                'valor_total_pedido': valor_total_pedido,
                'valor_disponivel': valor_disponivel,
                'valor_com_ruptura': valor_com_ruptura,
                'data_disponibilidade_total': data_disponibilidade_total
            },
            'itens': itens_com_ruptura,
            'itens_disponiveis': itens_disponiveis_lista  # Nova lista com itens disponíveis
        })
        
    except Exception as e:
        logger.error(f"Erro ao analisar ruptura do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/ruptura/atualizar-visual-separacao', methods=['POST'])
def atualizar_visual_pos_separacao():
    """
    Atualiza visual do pedido após criar separação sem recarregar página
    """
    try:
        data = request.get_json()
        num_pedido = data.get('num_pedido')
        data_expedicao = data.get('data_expedicao')
        
        if not num_pedido:
            return jsonify({
                'success': False,
                'error': 'Número do pedido é obrigatório'
            }), 400
            
        # Buscar informações atualizadas do pedido
        pedido_info = db.session.query(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.expedicao,
            func.count(CarteiraPrincipal.separacao_lote_id).label('tem_separacao'),
            func.sum(
                case(
                    (CarteiraPrincipal.qtd_saldo > 0, 1),
                    else_=0
                )
            ).label('itens_separados')
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).group_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.expedicao
        ).first()
        
        if not pedido_info:
            return jsonify({
                'success': False,
                'message': 'Pedido não encontrado'
            }), 404
            
        # Determinar cor baseado no status
        tem_separacao = pedido_info.itens_separados > 0
        cor_linha = 'table-success' if tem_separacao else ''
        
        return jsonify({
            'success': True,
            'pedido': {
                'num_pedido': num_pedido,
                'data_expedicao': data_expedicao or (pedido_info.expedicao.isoformat() if pedido_info.expedicao else None),
                'tem_separacao': tem_separacao,
                'cor_linha': cor_linha,
                'classe_css': 'pedido-com-separacao' if tem_separacao else ''
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar visual pós-separação: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/detalhes-completo', methods=['GET'])
def obter_detalhes_pedido_completo(num_pedido):
    """
    Obtém detalhes completos do pedido incluindo todos os itens
    """
    try:
        # Buscar informações principais do pedido (primeira linha)
        pedido_info = db.session.query(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.municipio,
            CarteiraPrincipal.estado,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.data_pedido,
            CarteiraPrincipal.expedicao,
            CarteiraPrincipal.agendamento,
            CarteiraPrincipal.hora_agendamento,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento_confirmado,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.forma_agendamento,
            CarteiraPrincipal.rota,
            CarteiraPrincipal.sub_rota,
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.peso).label('peso_total'),
            func.sum(CarteiraPrincipal.pallet).label('pallet_total'),
            func.count(CarteiraPrincipal.id).label('total_itens')
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).group_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.municipio,
            CarteiraPrincipal.estado,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.data_pedido,
            CarteiraPrincipal.expedicao,
            CarteiraPrincipal.agendamento,
            CarteiraPrincipal.hora_agendamento,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento_confirmado,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.forma_agendamento,
            CarteiraPrincipal.rota,
            CarteiraPrincipal.sub_rota
        ).first()
        
        if not pedido_info:
            return jsonify({
                'success': False,
                'message': 'Pedido não encontrado'
            }), 404
        
        # Buscar todos os itens do pedido
        itens = db.session.query(
            CarteiraPrincipal.id,
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            CarteiraPrincipal.qtd_produto_pedido,
            CarteiraPrincipal.qtd_saldo_produto_pedido,
            CarteiraPrincipal.qtd_cancelada_produto_pedido,
            CarteiraPrincipal.preco_produto_pedido,
            CarteiraPrincipal.peso,
            CarteiraPrincipal.pallet,
            CarteiraPrincipal.estoque
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()
        
        # Buscar separações relacionadas
        from app.separacao.models import Separacao
        from app.pedidos.models import Pedido
        
        separacoes = db.session.query(
            Separacao.separacao_lote_id,
            Separacao.criado_em,
            Separacao.tipo_envio,
            func.sum(Separacao.valor_saldo).label('valor_saldo'),
            func.sum(Separacao.peso).label('peso'),
            func.sum(Separacao.pallet).label('pallet'),
            Pedido.status
        ).join(
            Pedido, 
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.num_pedido == num_pedido
        ).group_by(
            Separacao.separacao_lote_id,
            Separacao.criado_em,
            Separacao.tipo_envio,
            Pedido.status
        ).all()
        
        # Formatar dados do pedido
        pedido_dict = {
            'num_pedido': pedido_info.num_pedido,
            'cnpj_cpf': pedido_info.cnpj_cpf,
            'raz_social_red': pedido_info.raz_social_red,
            'nome_cidade': pedido_info.nome_cidade,
            'cod_uf': pedido_info.cod_uf,
            'municipio': pedido_info.municipio,
            'estado': pedido_info.estado,
            'vendedor': pedido_info.vendedor,
            'equipe_vendas': pedido_info.equipe_vendas,
            'data_pedido': pedido_info.data_pedido.isoformat() if pedido_info.data_pedido else None,
            'expedicao': pedido_info.expedicao.isoformat() if pedido_info.expedicao else None,
            'agendamento': pedido_info.agendamento.isoformat() if pedido_info.agendamento else None,
            'hora_agendamento': pedido_info.hora_agendamento.isoformat() if pedido_info.hora_agendamento else None,
            'protocolo': pedido_info.protocolo,
            'agendamento_confirmado': pedido_info.agendamento_confirmado,
            'observ_ped_1': pedido_info.observ_ped_1,
            'pedido_cliente': pedido_info.pedido_cliente,
            'incoterm': pedido_info.incoterm,
            'forma_agendamento': pedido_info.forma_agendamento,
            'rota': pedido_info.rota,
            'sub_rota': pedido_info.sub_rota,
            'valor_total': float(pedido_info.valor_total or 0),
            'peso_total': float(pedido_info.peso_total or 0),
            'pallet_total': float(pedido_info.pallet_total or 0),
            'total_itens': pedido_info.total_itens
        }
        
        # Formatar itens
        itens_list = []
        for item in itens:
            itens_list.append({
                'id': item.id,
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'qtd_produto_pedido': float(item.qtd_produto_pedido or 0),
                'qtd_saldo_produto_pedido': float(item.qtd_saldo_produto_pedido or 0),
                'qtd_cancelada_produto_pedido': float(item.qtd_cancelada_produto_pedido or 0),
                'preco_produto_pedido': float(item.preco_produto_pedido or 0),
                'peso': float(item.peso or 0),
                'pallet': float(item.pallet or 0),
                'estoque': float(item.estoque or 0) if item.estoque else 0
            })
        
        # Formatar separações com detalhes dos itens
        separacoes_list = []
        for sep in separacoes:
            # Buscar itens desta separação
            itens_sep = db.session.query(
                Separacao.cod_produto,
                Separacao.nome_produto,
                Separacao.qtd_saldo,
                Separacao.peso,
                Separacao.pallet,
                Separacao.expedicao,
                Separacao.agendamento,
                Separacao.protocolo
            ).filter(
                Separacao.separacao_lote_id == sep.separacao_lote_id,
                Separacao.num_pedido == num_pedido
            ).all()
            
            # Pegar dados de expedição/agendamento do primeiro item
            primeiro_item_sep = itens_sep[0] if itens_sep else None
            
            separacoes_list.append({
                'separacao_lote_id': sep.separacao_lote_id,
                'criado_em': sep.criado_em.isoformat() if sep.criado_em else None,
                'tipo_envio': sep.tipo_envio,
                'valor_saldo': float(sep.valor_saldo or 0),
                'peso': float(sep.peso or 0),
                'pallet': float(sep.pallet or 0),
                'status': sep.status,
                'expedicao': primeiro_item_sep.expedicao.isoformat() if primeiro_item_sep and primeiro_item_sep.expedicao else None,
                'agendamento': primeiro_item_sep.agendamento.isoformat() if primeiro_item_sep and primeiro_item_sep.agendamento else None,
                'protocolo': primeiro_item_sep.protocolo if primeiro_item_sep else None,
                'itens': [
                    {
                        'cod_produto': item.cod_produto,
                        'nome_produto': item.nome_produto,
                        'qtd': float(item.qtd_saldo or 0),
                        'peso': float(item.peso or 0),
                        'pallet': float(item.pallet or 0)
                    }
                    for item in itens_sep
                ]
            })
        
        # Se pedido for total, pegar dados de expedição da primeira separação
        if separacoes_list and separacoes_list[0]['tipo_envio'] == 'total':
            pedido_dict['expedicao_separacao'] = separacoes_list[0]['expedicao']
            pedido_dict['agendamento_separacao'] = separacoes_list[0]['agendamento']
            pedido_dict['protocolo_separacao'] = separacoes_list[0]['protocolo']
        
        return jsonify({
            'success': True,
            'pedido': pedido_dict,
            'itens': itens_list,
            'separacoes': separacoes_list
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/produto/<cod_produto>/cardex', methods=['GET'])
def obter_cardex_produto(cod_produto):
    """
    Obtém cardex completo do produto (D0-D28)
    """
    try:
        from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
        
        # Obter projeção completa de 28 dias
        projecao = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=28)
        
        if not projecao:
            return jsonify({
                'success': False,
                'message': 'Produto não encontrado ou sem dados de estoque'
            }), 404
        
        # Preparar dados do cardex
        cardex_list = []
        estoque_atual = float(projecao.get('estoque_atual', 0))
        maior_estoque = {'dia': 0, 'valor': estoque_atual}
        menor_estoque = {'dia': 0, 'valor': estoque_atual}
        total_producao = 0
        total_saidas = 0
        alertas = []
        
        # Processar cada dia da projeção
        for i, dia_proj in enumerate(projecao.get('projecao', [])):
            estoque_inicial = float(dia_proj.get('estoque_inicial', 0))
            saidas = float(dia_proj.get('saidas', 0))
            producao = float(dia_proj.get('producao', 0))
            estoque_final = float(dia_proj.get('estoque_final', 0))
            data = dia_proj.get('data')
            
            # Atualizar estatísticas
            if estoque_final > maior_estoque['valor']:
                maior_estoque = {'dia': i, 'valor': estoque_final}
            if estoque_final < menor_estoque['valor']:
                menor_estoque = {'dia': i, 'valor': estoque_final}
            
            total_producao += producao
            total_saidas += saidas
            
            # Adicionar alertas se necessário
            if estoque_final <= 0:
                alertas.append({
                    'tipo': 'danger',
                    'dia': i,
                    'titulo': 'Ruptura de Estoque',
                    'descricao': f'Estoque zerado em D+{i}',
                    'sugestao': 'Programar produção urgente'
                })
            elif estoque_final < 10:
                alertas.append({
                    'tipo': 'warning',
                    'dia': i,
                    'titulo': 'Estoque Crítico',
                    'descricao': f'Estoque muito baixo em D+{i}: {estoque_final} unidades',
                    'sugestao': 'Considerar produção adicional'
                })
            
            cardex_list.append({
                'dia': i,
                'data': data,
                'estoque_inicial': estoque_inicial,
                'saidas': saidas,
                'saldo': estoque_inicial - saidas,
                'producao': producao,
                'estoque_final': estoque_final
            })
        
        return jsonify({
            'success': True,
            'cod_produto': cod_produto,
            'estoque_atual': estoque_atual,
            'maior_estoque': maior_estoque,
            'menor_estoque': menor_estoque,
            'total_producao': total_producao,
            'total_saidas': total_saidas,
            'alertas': alertas[:5],  # Limitar a 5 alertas mais importantes
            'cardex': cardex_list
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter cardex do produto {cod_produto}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/produto/<cod_produto>/cardex-detalhado', methods=['GET'])
def obter_cardex_detalhado_produto(cod_produto):
    """
    Obtém cardex detalhado com detalhes de todas as saídas
    Usado pelo modal-cardex-expandido.js
    """
    try:
        from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
        from datetime import date, timedelta
        
        # Obter projeção completa de 28 dias
        projecao = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=28)
        
        if not projecao:
            return jsonify({
                'success': False,
                'message': 'Produto não encontrado ou sem dados de estoque'
            }), 404
        
        # Buscar todos os pedidos dos próximos 28 dias
        data_hoje = date.today()
        data_limite = data_hoje + timedelta(days=28)
        
        # Importar modelos necessários
        from app.separacao.models import Separacao
        from app.pedidos.models import Pedido
        from app.carteira.models import PreSeparacaoItem
        from sqlalchemy import and_
        
        # Buscar pedidos de Separacao (ABERTO ou COTADO)
        pedidos_separacao = db.session.query(
            Separacao.num_pedido,
            Separacao.expedicao,
            Separacao.qtd_saldo,
            Separacao.raz_social_red,
            Separacao.nome_cidade,
            Separacao.cod_uf,
            Separacao.separacao_lote_id
        ).join(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.cod_produto == cod_produto,
            Separacao.qtd_saldo > 0,
            Pedido.status.in_(['ABERTO', 'COTADO'])
        ).all()
        
        # Buscar pedidos de PreSeparacao (CRIADO ou RECOMPOSTO)
        pedidos_pre_separacao = db.session.query(
            PreSeparacaoItem.num_pedido,
            PreSeparacaoItem.data_expedicao_editada.label('expedicao'),
            PreSeparacaoItem.qtd_selecionada_usuario.label('qtd_saldo'),
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.cod_uf,
            PreSeparacaoItem.separacao_lote_id
        ).join(
            CarteiraPrincipal,
            and_(
                PreSeparacaoItem.num_pedido == CarteiraPrincipal.num_pedido,
                PreSeparacaoItem.cod_produto == CarteiraPrincipal.cod_produto
            )
        ).filter(
            PreSeparacaoItem.cod_produto == cod_produto,
            PreSeparacaoItem.qtd_selecionada_usuario > 0,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).all()
        
        # Combinar os resultados
        pedidos = list(pedidos_separacao) + list(pedidos_pre_separacao)
        
        
        # Agrupar pedidos por data
        pedidos_por_data = {}
        pedidos_sem_data = []
        
        # Log temporário para debug
        logger.info(f"DEBUG Cardex: Total pedidos encontrados: {len(pedidos)}")
        logger.info(f"DEBUG Cardex: Separacao: {len(pedidos_separacao)}, PreSeparacao: {len(pedidos_pre_separacao)}")
        
        for pedido in pedidos:
            if pedido.expedicao:
                data_key = pedido.expedicao.isoformat()
                if data_key not in pedidos_por_data:
                    pedidos_por_data[data_key] = []
                
                # Usar qtd_saldo que é o nome comum em ambas queries
                qtd = float(pedido.qtd_saldo) if hasattr(pedido, 'qtd_saldo') else 0
                
                pedidos_por_data[data_key].append({
                    'num_pedido': pedido.num_pedido,
                    'qtd': qtd,
                    'cliente': pedido.raz_social_red or 'Cliente não informado',
                    'cidade': pedido.nome_cidade or 'Cidade não informada',
                    'uf': pedido.cod_uf or 'UF',
                    'tem_separacao': bool(pedido.separacao_lote_id)
                })
            else:
                # Pedidos sem data de expedição
                qtd = float(pedido.qtd_saldo) if hasattr(pedido, 'qtd_saldo') else 0
                
                pedidos_sem_data.append({
                    'num_pedido': pedido.num_pedido,
                    'qtd': qtd,
                    'cliente': pedido.raz_social_red or 'Cliente não informado',
                    'cidade': pedido.nome_cidade or 'Cidade não informada',
                    'uf': pedido.cod_uf or 'UF',
                    'tem_separacao': bool(pedido.separacao_lote_id)
                })
        
        # Adicionar pedidos sem data em uma categoria especial
        if pedidos_sem_data:
            pedidos_por_data['sem_data'] = pedidos_sem_data
        
        # Log final para debug
        logger.info(f"DEBUG Cardex Final: Total datas agrupadas: {len(pedidos_por_data)}")
        logger.info(f"DEBUG Cardex Final: Datas: {list(pedidos_por_data.keys())[:5]}")  # Primeiras 5 datas
        
        return jsonify({
            'success': True,
            'cod_produto': cod_produto,
            'estoque_atual': float(projecao.get('estoque_atual', 0)),
            'projecao_resumo': projecao.get('projecao', []),
            'pedidos_por_data': pedidos_por_data
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter cardex detalhado do produto {cod_produto}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
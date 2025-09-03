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
from app.estoque.services.estoque_simples import ServicoEstoqueSimples

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
            
        
        # OTIMIZAÇÃO: Buscar TODAS as produções programadas de uma vez
        produtos_pedido = [item.cod_produto for item in itens]
        producoes_por_produto = {}
        
        if produtos_pedido:
            producoes_todas = db.session.query(
                ProgramacaoProducao.cod_produto,
                ProgramacaoProducao.data_programacao,
                func.sum(ProgramacaoProducao.qtd_programada).label('qtd_producao')
            ).filter(
                ProgramacaoProducao.cod_produto.in_(produtos_pedido),
                ProgramacaoProducao.data_programacao >= datetime.now().date()
            ).group_by(
                ProgramacaoProducao.cod_produto,
                ProgramacaoProducao.data_programacao
            ).order_by(
                ProgramacaoProducao.cod_produto,
                ProgramacaoProducao.data_programacao
            ).all()
            
            # Agrupar por produto para lookup O(1)
            for prod in producoes_todas:
                if prod.cod_produto not in producoes_por_produto:
                    producoes_por_produto[prod.cod_produto] = []
                producoes_por_produto[prod.cod_produto].append({
                    'data': prod.data_programacao,
                    'qtd': float(prod.qtd_producao)
                })
        
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
            projecao = ServicoEstoqueSimples.get_projecao_completa(item.cod_produto, dias=7)
            
            # DEBUG: Log do tipo retornado
            logger.debug(f"Produto {item.cod_produto}: projecao tipo={type(projecao)}, valor={projecao}")
            
            # Se não tem projeção ou não é um dicionário, usar 0
            if not projecao or not isinstance(projecao, dict):
                logger.warning(f"Produto {item.cod_produto} sem projeção válida. Usando estoque=0")
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
                
                # OTIMIZADO: Usar lookup O(1) ao invés de query
                producoes_futuras = producoes_por_produto.get(item.cod_produto, [])
                
                # Calcular quando terá estoque suficiente
                data_disponivel = None
                qtd_acumulada = estoque_d7
                primeira_producao = None
                qtd_primeira_producao = 0
                
                if producoes_futuras:
                    primeira_producao = producoes_futuras[0]
                    qtd_primeira_producao = primeira_producao['qtd']
                    
                    for prod in producoes_futuras:
                        qtd_acumulada += prod['qtd']
                        if qtd_acumulada >= qtd_saldo:
                            data_disponivel = prod['data']
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
                    'data_producao': primeira_producao['data'].isoformat() if primeira_producao else None,
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
        
        # MIGRADO: Buscar separações sem JOIN com Pedido
        from app.separacao.models import Separacao
        
        # OTIMIZADO: Buscar separações agrupadas com dados de agendamento
        separacoes = db.session.query(
            Separacao.separacao_lote_id,
            Separacao.criado_em,
            Separacao.tipo_envio,
            Separacao.status,  # MIGRADO: Usar status direto de Separacao
            func.sum(Separacao.valor_saldo).label('valor_saldo'),
            func.sum(Separacao.peso).label('peso'),
            func.sum(Separacao.pallet).label('pallet'),
            func.min(Separacao.expedicao).label('expedicao'),  # Dados de agendamento vêm de Separacao
            func.min(Separacao.agendamento).label('agendamento'),
            func.min(Separacao.protocolo).label('protocolo'),
            func.bool_or(Separacao.agendamento_confirmado).label('agendamento_confirmado')
        ).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.sincronizado_nf == False  # IMPORTANTE: Apenas não sincronizados
        ).group_by(
            Separacao.separacao_lote_id,
            Separacao.criado_em,
            Separacao.tipo_envio,
            Separacao.status
        ).all()
        
        # CORRIGIDO: Pegar dados de agendamento da primeira separação, não de CarteiraPrincipal
        primeira_sep = separacoes[0] if separacoes else None
        
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
            # MIGRADO: Dados de agendamento vêm de Separacao, não CarteiraPrincipal
            'expedicao': primeira_sep.expedicao.isoformat() if primeira_sep and primeira_sep.expedicao else None,
            'agendamento': primeira_sep.agendamento.isoformat() if primeira_sep and primeira_sep.agendamento else None,
            'hora_agendamento': pedido_info.hora_agendamento.isoformat() if pedido_info.hora_agendamento else None,
            'protocolo': primeira_sep.protocolo if primeira_sep else None,
            'agendamento_confirmado': primeira_sep.agendamento_confirmado if primeira_sep else False,
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
        
        # OTIMIZADO: Buscar TODOS os itens de separação de uma vez
        lotes_ids = [sep.separacao_lote_id for sep in separacoes]
        todos_itens_sep = {}
        
        if lotes_ids:
            itens_todas_sep = db.session.query(
                Separacao.separacao_lote_id,
                Separacao.cod_produto,
                Separacao.nome_produto,
                Separacao.qtd_saldo,
                Separacao.peso,
                Separacao.pallet
            ).filter(
                Separacao.separacao_lote_id.in_(lotes_ids),
                Separacao.num_pedido == num_pedido,
                Separacao.sincronizado_nf == False  # Consistente com filtro anterior
            ).all()
            
            # Agrupar por lote para lookup O(1)
            for item in itens_todas_sep:
                if item.separacao_lote_id not in todos_itens_sep:
                    todos_itens_sep[item.separacao_lote_id] = []
                todos_itens_sep[item.separacao_lote_id].append(item)
        
        # Formatar separações com detalhes dos itens
        separacoes_list = []
        for sep in separacoes:
            # OTIMIZADO: Usar lookup O(1) ao invés de query
            itens_sep = todos_itens_sep.get(sep.separacao_lote_id, [])
            
            separacoes_list.append({
                'separacao_lote_id': sep.separacao_lote_id,
                'criado_em': sep.criado_em.isoformat() if sep.criado_em else None,
                'tipo_envio': sep.tipo_envio,
                'valor_saldo': float(sep.valor_saldo or 0),
                'peso': float(sep.peso or 0),
                'pallet': float(sep.pallet or 0),
                'status': sep.status,
                # OTIMIZADO: Dados de agendamento já vieram na query principal
                'expedicao': sep.expedicao.isoformat() if sep.expedicao else None,
                'agendamento': sep.agendamento.isoformat() if sep.agendamento else None,
                'protocolo': sep.protocolo,
                'agendamento_confirmado': sep.agendamento_confirmado,
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


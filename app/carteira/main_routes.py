from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import login_required
from app import db
from app.carteira.models import (
    CarteiraPrincipal, ControleCruzadoSeparacao,
    SaldoStandby
)
from app.estoque.services.compatibility_layer import SaldoEstoque
from sqlalchemy import func, inspect
from datetime import datetime, date, timedelta
from app.utils.timezone import agora_brasil
import logging
from app.separacao.models import Separacao
from app.permissions.permissions import check_permission

logger = logging.getLogger(__name__)


def _calcular_estoque_data_especifica(projecao_29_dias, data_target):
    """
    Calcula estoque para uma data específica baseado na projeção
    """
    try:
        data_hoje = datetime.now().date()
        diff_dias = (data_target - data_hoje).days
        
        # Se data é passado ou muito futuro, usar fallbacks
        if diff_dias < 0:
            return 0  # Data no passado = sem estoque
        if diff_dias >= len(projecao_29_dias):
            return 0  # Além da projeção = sem estoque
        
        # Buscar estoque final do dia específico na projeção
        dia_especifico = projecao_29_dias[diff_dias]
        return dia_especifico.get('estoque_final', 0)
        
    except Exception as e:
        logger.warning(f"Erro ao calcular estoque para data {data_target}: {e}")
        return 0

def _encontrar_proxima_data_com_estoque(projecao_29_dias, qtd_necessaria):
    """
    Encontra a próxima data com estoque suficiente para atender a quantidade
    """
    try:
        data_hoje = datetime.now().date()
        qtd_necessaria = float(qtd_necessaria or 0)
        
        if qtd_necessaria <= 0:
            return data_hoje  # Se não precisa de nada, qualquer data serve
        
        # Procurar primeiro dia com estoque suficiente
        for i, dia in enumerate(projecao_29_dias):
            estoque_final = dia.get('estoque_final', 0)
            if estoque_final >= qtd_necessaria:
                data_disponivel = data_hoje + timedelta(days=i)
                return data_disponivel.strftime('%d/%m/%Y')

        # Se não encontrou em 29 dias, retornar informação
        return "Sem estoque em 29 dias"
    
    except Exception as e:
        logger.warning(f"Erro ao encontrar próxima data com estoque: {e}")
        return None

# 📦 Blueprint da carteira (seguindo padrão dos outros módulos)
carteira_bp = Blueprint('carteira', __name__, url_prefix='/carteira')


@carteira_bp.route('/')
@login_required
@check_permission('carteira')
def index():
    """Dashboard principal da carteira de pedidos com KPIs e visão geral"""
    try:
        # 📊 VERIFICAR SE TABELAS EXISTEM (FALLBACK PARA DEPLOY)
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            # 📊 SISTEMA NÃO INICIALIZADO
            estatisticas = {
                'total_pedidos': 0,
                'total_produtos': 0,
                'total_itens': 0,
                'valor_total': 0
            }
            
            return render_template('carteira/dashboard.html',
                                 estatisticas=estatisticas,
                                 status_breakdown=[],
                                 alertas_inconsistencias=0,
                                 alertas_vinculacao=0,
                                 alertas_pendentes_count=0,
                                 expedicoes_proximas=[],
                                 top_vendedores=[],
                                 standby_stats=[],
                                 total_standby_pedidos=0,
                                 total_standby_valor=0,
                                 sistema_inicializado=False)
        
        # 📊 ESTATÍSTICAS PRINCIPAIS
        # IMPORTANTE: Filtrar apenas itens com saldo > 0 para consistência com workspace
        total_pedidos = db.session.query(CarteiraPrincipal.num_pedido).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).distinct().count()

        total_produtos = db.session.query(CarteiraPrincipal.cod_produto).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).distinct().count()

        total_itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).count()
        
        # 💰 VALORES TOTAIS
        valor_total_carteira = db.session.query(func.sum(
            CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido
        )).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).scalar() or 0
        
        # 🎯 STATUS BREAKDOWN
        status_breakdown = db.session.query(
            CarteiraPrincipal.status_pedido,
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor')
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).group_by(CarteiraPrincipal.status_pedido).all()
        
        # 🔄 CONTROLES CRUZADOS PENDENTES (com fallback)
        controles_pendentes = 0
        inconsistencias_abertas = 0
        if inspector.has_table('controle_cruzado_separacao'):
            controles_pendentes = ControleCruzadoSeparacao.query.filter_by(resolvida=False).count()
        # 📈 PEDIDOS COM EXPEDIÇÃO PRÓXIMA (7 dias)
        # NOTA: Campo expedicao foi REMOVIDO de CarteiraPrincipal - usar data_pedido
        data_limite = date.today() + timedelta(days=7)
        expedicoes_proximas = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.data_pedido <= data_limite,
            CarteiraPrincipal.data_pedido >= date.today() - timedelta(days=30),  # Pedidos dos últimos 30 dias
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).count()
        
        # 👥 BREAKDOWN POR VENDEDOR (ordenado por valor total decrescente)
        vendedores_breakdown = db.session.query(
            CarteiraPrincipal.vendedor,
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor')
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).group_by(CarteiraPrincipal.vendedor).order_by(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).desc()
        ).limit(10).all()
        
        # 🔸 ESTATÍSTICAS DE STANDBY
        standby_stats = []
        total_standby_pedidos = 0
        total_standby_valor = 0
        
        if inspector.has_table('saldo_standby'):
            # Estatísticas por status
            standby_stats = db.session.query(
                SaldoStandby.status_standby,
                func.count(func.distinct(SaldoStandby.num_pedido)).label('qtd_pedidos'),
                func.sum(SaldoStandby.valor_saldo).label('valor_total')
            ).filter(
                SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
            ).group_by(
                SaldoStandby.status_standby
            ).all()
            
            # Total geral
            total_geral = db.session.query(
                func.count(func.distinct(SaldoStandby.num_pedido)).label('total_pedidos'),
                func.sum(SaldoStandby.valor_saldo).label('valor_total')
            ).filter(
                SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
            ).first()
            
            if total_geral:
                total_standby_pedidos = total_geral.total_pedidos or 0
                total_standby_valor = float(total_geral.valor_total) if total_geral.valor_total else 0
        
        # 📊 CONTAGEM DE ALERTAS PENDENTES
        try:
            from app.carteira.models_alertas import AlertaSeparacaoCotada
            alertas_pendentes_count = AlertaSeparacaoCotada.query.filter_by(reimpresso=False).count()
        except Exception as e:
            logger.error(f"Erro ao buscar alertas pendentes: {e}")
            alertas_pendentes_count = 0
        
        # 📊 ORGANIZAR DADOS PARA O TEMPLATE
        estatisticas = {
            'total_pedidos': total_pedidos,
            'total_produtos': total_produtos,
            'total_itens': total_itens,
            'valor_total': valor_total_carteira
        }
        
        return render_template('carteira/dashboard.html',
                             estatisticas=estatisticas,
                             status_breakdown=status_breakdown,
                             alertas_inconsistencias=inconsistencias_abertas,
                             alertas_vinculacao=controles_pendentes,
                             alertas_pendentes_count=alertas_pendentes_count,
                             expedicoes_proximas=[],  # Lista vazia por enquanto
                             top_vendedores=vendedores_breakdown[:5] if vendedores_breakdown else [],
                             standby_stats=standby_stats,
                             total_standby_pedidos=total_standby_pedidos,
                             total_standby_valor=total_standby_valor,
                             sistema_inicializado=True)
        
    except Exception as e:
        logger.error(f"Erro no dashboard da carteira: {str(e)}")
        flash('Erro ao carregar dashboard da carteira', 'error')
        
        # 📊 FALLBACK COM DADOS ZERO
        estatisticas = {
            'total_pedidos': 0,
            'total_produtos': 0,
            'total_itens': 0,
            'valor_total': 0
        }
        
        return render_template('carteira/dashboard.html',
                             estatisticas=estatisticas,
                             status_breakdown=[],
                             alertas_inconsistencias=0,
                             alertas_vinculacao=0,
                             alertas_pendentes_count=0,
                             expedicoes_proximas=[],
                             top_vendedores=[],
                             standby_stats=[],
                             total_standby_pedidos=0,
                             total_standby_valor=0,
                             sistema_inicializado=False)


@carteira_bp.route('/api/item/<int:id>')
@login_required
def api_item_detalhes(id):
    """API aprimorada para detalhes completos de um item da carteira"""
    try:
        item = CarteiraPrincipal.query.get_or_404(id)
        
        # 🔍 DEBUG: Log do saldo para investigar zeros
        qtd_saldo = float(item.qtd_saldo_produto_pedido or 0)
        logger.info(f"🔍 DEBUG CarteiraPrincipal ID {item.id}: cod={item.cod_produto}, qtd_saldo={qtd_saldo}, qtd_produto={item.qtd_produto_pedido}, qtd_cancelada={item.qtd_cancelada_produto_pedido}")
        
        # 📊 DADOS BÁSICOS DO ITEM
        dados = {
            'id': item.id,
            'num_pedido': item.num_pedido,
            'cod_produto': item.cod_produto,
            'nome_produto': item.nome_produto,
            'raz_social': item.raz_social,
            'raz_social_red': item.raz_social_red,
            'vendedor': item.vendedor,
            'status_pedido': item.status_pedido,
            'qtd_produto_pedido': float(item.qtd_produto_pedido or 0),
            'qtd_saldo_produto_pedido': float(item.qtd_saldo_produto_pedido or 0),
            'qtd_cancelada_produto_pedido': float(item.qtd_cancelada_produto_pedido or 0),
            'preco_produto_pedido': float(item.preco_produto_pedido or 0),
            'expedicao': item.expedicao.strftime('%d/%m/%Y') if item.expedicao else None,
            'agendamento': item.agendamento.strftime('%d/%m/%Y') if item.agendamento else None,
            'protocolo': item.protocolo,
            'peso': float(item.peso or 0),
            'pallet': float(item.pallet or 0),
            'cnpj_cpf': item.cnpj_cpf,
            'municipio': item.municipio,
            'estado': item.estado,
            'cliente_nec_agendamento': item.cliente_nec_agendamento,
            'valor_total': float((item.qtd_saldo_produto_pedido or 0) * (item.preco_produto_pedido or 0)),
            'separacao_lote_id': item.separacao_lote_id
        }
        
        # 📦 INFORMAÇÕES DE ESTOQUE
        try:
            from app.estoque.services.compatibility_layer import SaldoEstoque
            estoque_info = SaldoEstoque.obter_resumo_produto(item.cod_produto, item.nome_produto)
            if estoque_info:
                dados['estoque'] = {
                    'saldo_atual': estoque_info['estoque_inicial'],
                    'previsao_ruptura': estoque_info['previsao_ruptura'],
                    'status_ruptura': estoque_info['status_ruptura'],
                    'disponivel': estoque_info['estoque_inicial'] >= (item.qtd_saldo_produto_pedido or 0)
                }
            else:
                dados['estoque'] = {
                    'saldo_atual': 0,
                    'previsao_ruptura': 0,
                    'status_ruptura': 'SEM_DADOS',
                    'disponivel': False
                }
        except Exception as e:
            logger.warning(f"Erro ao buscar dados de estoque: {str(e)}")
            dados['estoque'] = {
                'saldo_atual': 0,
                'previsao_ruptura': 0,
                'status_ruptura': 'ERRO',
                'disponivel': False
            }
        
        # 📞 INFORMAÇÕES DE AGENDAMENTO DO CLIENTE
        try:
            from app.cadastros_agendamento.models import ContatoAgendamento
            contato_agendamento = ContatoAgendamento.query.filter_by(cnpj=item.cnpj_cpf).first()
            if contato_agendamento:
                dados['agendamento_info'] = {
                    'forma_agendamento': contato_agendamento.forma,
                    'contato': contato_agendamento.contato,
                    'observacao': contato_agendamento.observacao,
                    'precisa_agendamento': item.cliente_nec_agendamento == 'Sim'
                }
            else:
                dados['agendamento_info'] = {
                    'forma_agendamento': None,
                    'contato': None,
                    'observacao': 'Cliente não cadastrado',
                    'precisa_agendamento': item.cliente_nec_agendamento == 'Sim'
                }
        except Exception as e:
            logger.warning(f"Erro ao buscar dados de agendamento: {str(e)}")
            dados['agendamento_info'] = {
                'forma_agendamento': None,
                'contato': None,
                'observacao': 'Erro ao carregar',
                'precisa_agendamento': item.cliente_nec_agendamento == 'Sim'
            }
        
        # 📦 INFORMAÇÕES DE SEPARAÇÃO VINCULADA
        try:
            if item.separacao_lote_id:
                separacoes = Separacao.query.filter_by(
                    separacao_lote_id=item.separacao_lote_id,
                    num_pedido=item.num_pedido,
                    cod_produto=item.cod_produto
                ).all()
                
                if separacoes:
                    total_qtd_separada = sum(float(s.qtd_saldo or 0) for s in separacoes)
                    total_peso_separado = sum(float(s.peso or 0) for s in separacoes)
                    total_pallet_separado = sum(float(s.pallet or 0) for s in separacoes)
                    
                    dados['separacao_info'] = {
                        'tem_separacao': True,
                        'lote_id': item.separacao_lote_id,
                        'qtd_separada': total_qtd_separada,
                        'peso_separado': total_peso_separado,
                        'pallet_separado': total_pallet_separado,
                        'percentual_separado': (total_qtd_separada / (item.qtd_saldo_produto_pedido or 1)) * 100 if item.qtd_saldo_produto_pedido else 0,
                        'separacao_completa': total_qtd_separada >= (item.qtd_saldo_produto_pedido or 0)
                    }
                else:
                    dados['separacao_info'] = {
                        'tem_separacao': False,
                        'lote_id': item.separacao_lote_id,
                        'qtd_separada': 0,
                        'peso_separado': 0,
                        'pallet_separado': 0,
                        'percentual_separado': 0,
                        'separacao_completa': False
                    }
            else:
                dados['separacao_info'] = {
                    'tem_separacao': False,
                    'lote_id': None,
                    'qtd_separada': 0,
                    'peso_separado': 0,
                    'pallet_separado': 0,
                    'percentual_separado': 0,
                    'separacao_completa': False
                }
        except Exception as e:
            logger.warning(f"Erro ao buscar dados de separação: {str(e)}")
            dados['separacao_info'] = {
                'tem_separacao': False,
                'lote_id': None,
                'qtd_separada': 0,
                'peso_separado': 0,
                'pallet_separado': 0,
                'percentual_separado': 0,
                'separacao_completa': False
            }
        
        # 📊 INDICADORES CALCULADOS
        dados['indicadores'] = {
            'valor_total_item': dados['valor_total'],
            'necessita_agendamento': dados['agendamento_info']['precisa_agendamento'],
            'estoque_suficiente': dados['estoque']['disponivel'],
            'tem_separacao_vinculada': dados['separacao_info']['tem_separacao'],
            'separacao_completa': dados['separacao_info']['separacao_completa'],
            'status_geral': _calcular_status_geral_item(dados)
        }
        
        return jsonify(dados)
        
    except Exception as e:
        logger.error(f"Erro na API item {id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

def _calcular_status_geral_item(dados):
    """Calcula status geral do item baseado em todos os indicadores"""
    # Verificar problemas críticos
    if not dados['estoque']['disponivel']:
        return {'status': 'CRITICO', 'motivo': 'Estoque insuficiente'}
    
    if dados['agendamento_info']['precisa_agendamento'] and not dados['agendamento_info']['contato']:
        return {'status': 'ATENCAO', 'motivo': 'Cliente precisa agendamento mas não tem contato cadastrado'}
    
    if not dados['separacao_info']['tem_separacao']:
        return {'status': 'PENDENTE', 'motivo': 'Aguardando separação'}
    
    if dados['separacao_info']['tem_separacao'] and not dados['separacao_info']['separacao_completa']:
        return {'status': 'PARCIAL', 'motivo': 'Separação parcial'}
    
    # Se chegou até aqui, está ok
    return {'status': 'OK', 'motivo': 'Item pronto para expedição'}




"""
📋 DOCUMENTAÇÃO SISTEMA DE VINCULAÇÃO INTELIGENTE

FUNCIONALIDADES IMPLEMENTADAS:

1. VINCULAÇÃO PARCIAL INTELIGENTE:
   - Carteira 10 + Separação 5 = Vincula 5, deixa 5 livre
   - One-way: Carteira → Separação (nunca o contrário)
   - Preserva quantidade exata da separação existente

2. DADOS OPERACIONAIS PRESERVADOS:
   - expedicao: Data prevista de expedição (roteirização)
   - agendamento: Data de agendamento com cliente  
   - protocolo: Protocolo de agendamento
   - roteirizacao: Transportadora sugerida/contratada
   - separacao_lote_id: Vínculo com separação já gerada
   - qtd_saldo, valor_saldo, pallet, peso: Dados do lote

3. SISTEMA DE RESTRIÇÕES POR COTAÇÃO:
   - Sem cotação: Alteração livre
   - Com cotação: Restrição parcial com notificação
   - Workflow de aprovação para mudanças críticas
"""


@carteira_bp.route('/api/item/<item_id>/recalcular-estoques', methods=['POST'])
@login_required
def api_recalcular_estoques_item(item_id):
    """
    API para recalcular estoques D0/D7 baseado em nova data de expedição
    """
    try:
        data = request.get_json()
        data_d0_str = data.get('data_d0')
        
        if not data_d0_str:
            return jsonify({
                'success': False,
                'error': 'Data D0 é obrigatória'
            }), 400
        
        # Converter string para date
        try:
            data_d0 = datetime.strptime(data_d0_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Formato de data inválido. Use YYYY-MM-DD'
            }), 400
        
        # Buscar item da carteira
        item = db.session.get(CarteiraPrincipal,item_id) if item_id else None
        if not item:
            return jsonify({
                'success': False,
                'error': f'Item {item_id} não encontrado'
            }), 404
        
        # Recalcular estoques usando data de expedição dinâmica
        try:
            # Data de expedição específica do item (ou hoje+1 se não definida)
            data_expedicao = item.expedicao or (agora_brasil().date() + timedelta(days=1))
            
            # SISTEMA DINÂMICO: Usar projeção completa para data específica
            resumo_estoque = SaldoEstoque.obter_resumo_produto(item.cod_produto, item.nome_produto)
            
            if resumo_estoque and resumo_estoque['projecao_29_dias']:
                # 📅 ESTOQUE DA DATA DE EXPEDIÇÃO (dinâmico)
                estoque_expedicao = _calcular_estoque_data_especifica(
                    resumo_estoque['projecao_29_dias'], data_expedicao
                )
                estoque_d0 = f"{int(estoque_expedicao)}" if estoque_expedicao >= 0 else "RUPTURA"
                
                # 🏭 PRODUÇÃO DA DATA DE EXPEDIÇÃO (dinâmico)
                producao_expedicao = SaldoEstoque.calcular_producao_periodo(
                    item.cod_produto, data_expedicao, data_expedicao
                )
                producao_d0 = f"{int(producao_expedicao)}" if producao_expedicao > 0 else "0"
                
                # 📊 MENOR ESTOQUE D7 (mantém D0 até D7)
                menor_estoque_calc = resumo_estoque['previsao_ruptura']
                menor_estoque_d7 = f"{int(menor_estoque_calc)}" if menor_estoque_calc >= 0 else "RUPTURA"
                
                # 🎯 PRÓXIMA DATA COM ESTOQUE (sugestão inteligente)
                proxima_data_disponivel = _encontrar_proxima_data_com_estoque(
                    resumo_estoque['projecao_29_dias'], item.qtd_saldo_produto_pedido or 0
                )
            else:
                # Fallback simples se projeção não disponível
                estoque_inicial = SaldoEstoque.calcular_estoque_inicial(item.cod_produto)
                estoque_d0 = f"{int(estoque_inicial)}" if estoque_inicial >= 0 else "RUPTURA"
                menor_estoque_d7 = estoque_d0
                producao_d0 = "0"
                proxima_data_disponivel = None
            
            return jsonify({
                'success': True,
                'estoque_data_expedicao': estoque_d0,  # CORRIGIDO: nome mais claro
                'menor_estoque_d7': menor_estoque_d7,
                'producao_data_expedicao': producao_d0,  # CORRIGIDO: nome mais claro
                'proxima_data_com_estoque': proxima_data_disponivel,  # NOVO: sugestão inteligente
                'data_expedicao': data_d0_str
            })
            
        except Exception as e:
            logger.error(f"Erro ao calcular estoques para item {item_id} com data {data_d0}: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro ao calcular estoques: {str(e)}'
            }), 500
        
    except Exception as e:
        logger.error(f"Erro ao recalcular estoques do item {item_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

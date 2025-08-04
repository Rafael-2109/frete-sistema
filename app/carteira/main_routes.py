from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response
from flask_login import login_required
from typing import Union, Tuple
from app import db
from app.carteira.models import (
    CarteiraPrincipal, ControleCruzadoSeparacao,
    InconsistenciaFaturamento, SaldoStandby
)
from app.estoque.models import SaldoEstoque
from app.localidades.models import CadastroRota, CadastroSubRota
from app.utils.timezone import agora_brasil
from sqlalchemy import func, and_, or_, inspect
from datetime import datetime, date, timedelta
import logging
from app.carteira.utils.separacao_utils import calcular_peso_pallet_produto
from app.separacao.models import Separacao

logger = logging.getLogger(__name__)

# Função auxiliar para buscar rota baseada no cod_uf
def _buscar_rota_por_uf(cod_uf):
    """Busca rota principal baseada no cod_uf"""
    if not cod_uf:
        return None
    try:
        rota = CadastroRota.query.filter_by(cod_uf=cod_uf, ativa=True).first()
        return rota.rota if rota else None
    except Exception:
        return None

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

# Função auxiliar para buscar sub-rota baseada no cod_uf + nome_cidade
def _buscar_sub_rota_por_uf_cidade(cod_uf, nome_cidade):
    """
    Busca sub-rota baseada no cod_uf + nome_cidade
    ✅ CORREÇÃO: Usa ILIKE para busca com acentos
    """
    if not cod_uf or not nome_cidade:
        return None
    try:
        # ✅ CORREÇÃO: ILIKE para resolver problema de acentos
        sub_rota = CadastroSubRota.query.filter(
            CadastroSubRota.cod_uf == cod_uf,
            CadastroSubRota.nome_cidade.ilike(f'%{nome_cidade}%'),
            CadastroSubRota.ativa == True
        ).first()
        return sub_rota.sub_rota if sub_rota else None
    except Exception as e:
        logger.warning(f"Erro ao buscar sub-rota para {cod_uf}/{nome_cidade}: {e}")
        return None


# 📦 Blueprint da carteira (seguindo padrão dos outros módulos)
carteira_bp = Blueprint('carteira', __name__, url_prefix='/carteira')


@carteira_bp.route('/')
@login_required
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
                                 expedicoes_proximas=[],
                                 top_vendedores=[],
                                 standby_stats=[],
                                 total_standby_pedidos=0,
                                 total_standby_valor=0,
                                 sistema_inicializado=False)
        
        # 📊 ESTATÍSTICAS PRINCIPAIS
        total_pedidos = db.session.query(CarteiraPrincipal.num_pedido).distinct().count()
        total_produtos = db.session.query(CarteiraPrincipal.cod_produto).distinct().count()
        total_itens = CarteiraPrincipal.query.filter_by(ativo=True).count()
        
        # 💰 VALORES TOTAIS
        valor_total_carteira = db.session.query(func.sum(
            CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido
        )).scalar() or 0
        
        # 🎯 STATUS BREAKDOWN
        status_breakdown = db.session.query(
            CarteiraPrincipal.status_pedido,
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor')
        ).filter_by(ativo=True).group_by(CarteiraPrincipal.status_pedido).all()
        
        # 🔄 CONTROLES CRUZADOS PENDENTES (com fallback)
        controles_pendentes = 0
        inconsistencias_abertas = 0
        if inspector.has_table('controle_cruzado_separacao'):
            controles_pendentes = ControleCruzadoSeparacao.query.filter_by(resolvida=False).count()
        if inspector.has_table('inconsistencia_faturamento'):
            inconsistencias_abertas = InconsistenciaFaturamento.query.filter_by(resolvida=False).count()
        
        # 📈 PEDIDOS COM EXPEDIÇÃO PRÓXIMA (7 dias)
        data_limite = date.today() + timedelta(days=7)
        expedicoes_proximas = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.expedicao <= data_limite,
            CarteiraPrincipal.expedicao >= date.today(),
            CarteiraPrincipal.ativo == True
        ).count()
        
        # 👥 BREAKDOWN POR VENDEDOR (ordenado por valor total decrescente)
        vendedores_breakdown = db.session.query(
            CarteiraPrincipal.vendedor,
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor')
        ).filter_by(ativo=True).group_by(CarteiraPrincipal.vendedor).order_by(
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
                             expedicoes_proximas=[],
                             top_vendedores=[],
                             standby_stats=[],
                             total_standby_pedidos=0,
                             total_standby_valor=0,
                             sistema_inicializado=False)

@carteira_bp.route('/principal')
@login_required
def listar_principal():
    """Lista a carteira principal com filtros e paginação"""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            flash('Sistema de carteira ainda não foi inicializado', 'warning')
            return render_template('carteira/listar_principal.html', itens=None)
            
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # 🔍 FILTROS
        num_pedido = request.args.get('num_pedido', '').strip()
        cod_produto = request.args.get('cod_produto', '').strip()
        vendedor = request.args.get('vendedor', '').strip()
        status = request.args.get('status', '').strip()
        cliente = request.args.get('cliente', '').strip()
        
        # 📊 QUERY BASE + FILTRO AUTOMÁTICO (ocultar itens fracionados)
        query = CarteiraPrincipal.query.filter_by(ativo=True).filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )
        
        # 🔎 APLICAR FILTROS
        if num_pedido:
            query = query.filter(CarteiraPrincipal.num_pedido.ilike(f'%{num_pedido}%'))
        if cod_produto:
            query = query.filter(CarteiraPrincipal.cod_produto.ilike(f'%{cod_produto}%'))
        if vendedor:
            query = query.filter(CarteiraPrincipal.vendedor.ilike(f'%{vendedor}%'))
        if status:
            query = query.filter(CarteiraPrincipal.status_pedido.ilike(f'%{status}%'))
        if cliente:
            query = query.filter(or_(
                CarteiraPrincipal.raz_social.ilike(f'%{cliente}%'),
                CarteiraPrincipal.raz_social_red.ilike(f'%{cliente}%')
            ))
        
        # 📊 ORDENAÇÃO INTELIGENTE
        sort_field = request.args.get('sort', '')
        sort_order = request.args.get('order', 'asc')
        
        # Mapear campos para ordenação
        sort_mapping = {
            'vendedor': CarteiraPrincipal.vendedor,
            'num_pedido': CarteiraPrincipal.num_pedido,
            'data_pedido': CarteiraPrincipal.data_pedido,
            'raz_social': CarteiraPrincipal.raz_social,
            'cod_uf': CarteiraPrincipal.cod_uf,
            'rota': CarteiraPrincipal.rota,
            'cod_produto': CarteiraPrincipal.cod_produto,
            'qtd_saldo_produto_pedido': CarteiraPrincipal.qtd_saldo_produto_pedido,
            'preco_produto_pedido': CarteiraPrincipal.preco_produto_pedido,
            'expedicao': CarteiraPrincipal.expedicao,
            'agendamento': CarteiraPrincipal.agendamento
        }
        
        # Aplicar ordenação se especificada e válida
        if sort_field and sort_field in sort_mapping:
            sort_column = sort_mapping[sort_field]
            if sort_order.lower() == 'desc':
                query = query.order_by(sort_column.desc().nullslast())
            else:
                query = query.order_by(sort_column.asc().nullslast())
        else:
            # Ordenação padrão
            query = query.order_by(
                CarteiraPrincipal.expedicao.asc().nullslast(),
                CarteiraPrincipal.num_pedido.asc()
            )
        
        # 📈 PAGINAÇÃO
        itens = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 📞 BUSCAR CONTATOS DE AGENDAMENTO para exibir botão "Agendar"
        from app.cadastros_agendamento.models import ContatoAgendamento
        from app.producao.models import CadastroPalletizacao
        
        # Obter CNPJs únicos dos itens
        cnpjs_unicos = set()
        produtos_unicos = set()
        if itens.items:
            cnpjs_unicos = {item.cnpj_cpf for item in itens.items if item.cnpj_cpf}
            produtos_unicos = {item.cod_produto for item in itens.items if item.cod_produto}
        
        # Buscar contatos de agendamento
        contatos_agendamento = {}
        if cnpjs_unicos:
            contatos = ContatoAgendamento.query.filter(
                ContatoAgendamento.cnpj.in_(cnpjs_unicos)
            ).all()
            contatos_agendamento = {contato.cnpj: contato for contato in contatos}
        
        # 🏭 BUSCAR DADOS DE PALLETIZAÇÃO para calcular peso e pallet
        dados_palletizacao = {}
        if produtos_unicos:
            palletizacoes = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.cod_produto.in_(produtos_unicos),
                CadastroPalletizacao.ativo == True
            ).all()
            dados_palletizacao = {p.cod_produto: p for p in palletizacoes}
        
        # 📊 CALCULAR PESO E PALLET DINAMICAMENTE + ROTA/SUB-ROTA para cada item
        if itens.items:
            for item in itens.items:
                palletizacao = dados_palletizacao.get(item.cod_produto)
                if palletizacao and item.qtd_saldo_produto_pedido:
                    # Calcular peso: QTD x peso_bruto
                    item.peso_calculado = float(item.qtd_saldo_produto_pedido) * palletizacao.peso_bruto
                    # Calcular pallet: QTD / palletizacao
                    item.pallet_calculado = float(item.qtd_saldo_produto_pedido) / palletizacao.palletizacao
                else:
                    # Fallback para campos existentes no banco
                    item.peso_calculado = float(getattr(item, 'peso', 0) or 0)
                    item.pallet_calculado = float(getattr(item, 'pallet', 0) or 0)
                
                # 🛣️ BUSCAR ROTA E SUB-ROTA SE NÃO EXISTIREM NO BANCO
                if not item.rota and item.cod_uf:
                    item.rota = _buscar_rota_por_uf(item.cod_uf)
                if not item.sub_rota and item.cod_uf and item.nome_cidade:
                    item.sub_rota = _buscar_sub_rota_por_uf_cidade(item.cod_uf, item.nome_cidade)
        
        return render_template('carteira/listar_principal.html',
                             itens=itens,
                             num_pedido=num_pedido,
                             cod_produto=cod_produto,
                             vendedor=vendedor,
                             status=status,
                             cliente=cliente,
                             contatos_agendamento=contatos_agendamento)
        
    except Exception as e:
        import traceback
        logger.error(f"Erro ao listar carteira principal: {str(e)}")
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        flash(f'Erro ao carregar carteira principal: {str(e)}', 'error')
        return redirect(url_for('carteira.index'))

# ROTA REMOVIDA: /item/<int:item_id>/endereco - Usar /item/<num_pedido>/endereco

@carteira_bp.route('/item/<int:item_id>/agendamento', methods=['POST'])
@login_required
def agendamento_item(item_id: int) -> Union[Response, Tuple[Response, int]]:
    """API para salvar dados de agendamento de um item da carteira"""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            return jsonify({'error': 'Sistema não inicializado'}), 400
            
        item = CarteiraPrincipal.query.get_or_404(item_id)
        
        # POST apenas - GET foi removido pois não é utilizado
        if request.method == 'POST':
            # Salvar agendamento
            from datetime import datetime
            
            dados = request.get_json()
            
            # Se apenas confirmando agendamento existente
            if dados.get('agenda_confirmada') and not dados.get('data_agendamento'):
                if not item.agendamento:
                    return jsonify({'error': 'Não é possível confirmar agendamento que não existe'}), 400
                
                item.agendamento_confirmado = True
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Agendamento confirmado com sucesso'
                })
            
            # Validar data obrigatória para novos agendamentos
            if not dados.get('data_agendamento'):
                return jsonify({'error': 'Data do agendamento é obrigatória'}), 400
            
            # Atualizar campos
            try:
                data_agendamento = datetime.strptime(dados['data_agendamento'], '%Y-%m-%d').date()
                item.agendamento = data_agendamento
                
                # Data de entrega (novo campo)
                if dados.get('expedicao'):
                    expedicao_obj = datetime.strptime(dados['expedicao'], '%Y-%m-%d').date()
                    item.expedicao = expedicao_obj
                
                if dados.get('hora_agendamento'):
                    hora_agendamento = datetime.strptime(dados['hora_agendamento'], '%H:%M').time()
                    item.hora_agendamento = hora_agendamento
                
                if dados.get('protocolo'):
                    item.protocolo = dados['protocolo']
                
                # ✅ CORREÇÃO: Suporte a observações de agendamento
                if dados.get('observacoes'):
                    item.observ_ped_1 = dados['observacoes']
                
                # Processar confirmação do agendamento
                item.agendamento_confirmado = dados.get('agenda_confirmada', False)
                
                # Se checkbox "Aplicar a todos os itens do pedido" foi marcado
                if dados.get('aplicar_todos'):
                    # Buscar todos os itens do mesmo pedido
                    itens_mesmo_pedido = CarteiraPrincipal.query.filter_by(
                        num_pedido=item.num_pedido,
                        ativo=True
                    ).all()
                    
                    # Aplicar o agendamento a todos os itens
                    for item_pedido in itens_mesmo_pedido:
                        item_pedido.agendamento = data_agendamento
                        if dados.get('expedicao'):
                            item_pedido.expedicao = expedicao_obj
                        if dados.get('hora_agendamento'):
                            item_pedido.hora_agendamento = hora_agendamento
                        if dados.get('protocolo'):
                            item_pedido.protocolo = dados['protocolo']
                        # ✅ CORREÇÃO: Aplicar observações a todos os itens
                        if dados.get('observacoes'):
                            item_pedido.observ_ped_1 = dados['observacoes']
                        item_pedido.agendamento_confirmado = dados.get('agenda_confirmada', False)
                    
                    message = f'Agendamento aplicado a {len(itens_mesmo_pedido)} itens do pedido {item.num_pedido}'
                else:
                    message = 'Agendamento salvo com sucesso'
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': message
                })
                
            except ValueError as e:
                return jsonify({'error': f'Formato de data/hora inválido: {str(e)}'}), 400
        
        # Método não suportado
        return jsonify({'error': 'Método não suportado'}), 405
        
    except Exception as e:
        logger.error(f"Erro no agendamento do item {item_id}: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500



# ROTA REMOVIDA: /gerar-separacao - Será recriada de forma simplificada

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
            from app.estoque.models import SaldoEstoque
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
            from app.separacao.models import Separacao
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

def _gerar_novo_lote_id():
    """
    Gera novo ID único para lotes de separação (NÃO SEQUENCIAL)
    
    FORMATO: LOTE_YYYYMMDD_HHMMSS_XXX
    Exemplo: LOTE_20250702_143025_001
    """
    try:
        from datetime import datetime
        import random
        
        # Gerar ID baseado em timestamp + random
        agora = datetime.now()
        timestamp = agora.strftime("%Y%m%d_%H%M%S")
        
        # Adicionar componente aleatório para evitar colisões
        random_suffix = f"{random.randint(100, 999)}"
        
        lote_id = f"LOTE_{timestamp}_{random_suffix}"
        
        logger.info(f"🆔 Lote ID gerado: {lote_id}")
        return lote_id
            
    except Exception as e:
        logger.error(f"Erro ao gerar lote ID: {str(e)}")
        # Fallback ainda mais simples
        import time
        return f"LOTE_{int(time.time())}"

@carteira_bp.route('/api/pedido/<num_pedido>/itens')
@login_required
def api_itens_pedido(num_pedido):
    """
    API para carregar itens de um pedido específico via AJAX
    Implementação: Fase 2.2 - JavaScript Expandir/Colapsar
    """
    try:
        # Import necessário para join
        from app.producao.models import CadastroPalletizacao
        
        # 📊 BUSCAR ITENS DO PEDIDO com dados de palletização
        itens = db.session.query(
            CarteiraPrincipal.id,
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido,
            CarteiraPrincipal.preco_produto_pedido,
            CarteiraPrincipal.expedicao,
            CarteiraPrincipal.agendamento,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.separacao_lote_id,
            
            # Dados de palletização para cálculos
            CadastroPalletizacao.peso_bruto,
            CadastroPalletizacao.palletizacao
            
        ).outerjoin(
            CadastroPalletizacao,
            and_(
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto,
                CadastroPalletizacao.ativo == True
            )
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()
        
        # 📋 CONVERTER PARA JSON
        itens_json = []
        for item in itens:
            # Calcular peso e pallet
            peso_item = 0
            pallet_item = 0
            if item.peso_bruto and item.qtd_saldo_produto_pedido:
                peso_item = float(item.qtd_saldo_produto_pedido) * float(item.peso_bruto)
            if item.palletizacao and item.qtd_saldo_produto_pedido and item.palletizacao > 0:
                pallet_item = float(item.qtd_saldo_produto_pedido) / float(item.palletizacao)
            
            # Calcular valor
            valor_item = 0
            if item.preco_produto_pedido and item.qtd_saldo_produto_pedido:
                valor_item = float(item.qtd_saldo_produto_pedido) * float(item.preco_produto_pedido)
            
            item_data = {
                'id': item.id,
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'qtd_saldo': int(item.qtd_saldo_produto_pedido) if item.qtd_saldo_produto_pedido else 0,  # SEM casa decimal
                'preco': float(item.preco_produto_pedido) if item.preco_produto_pedido else 0,
                'valor_item': valor_item,
                'peso_item': int(peso_item),  # SEM casa decimal  
                'pallet_item': round(pallet_item, 1),  # 1 casa decimal
                'expedicao': item.expedicao.strftime('%Y-%m-%d') if item.expedicao else '',
                'agendamento': item.agendamento.strftime('%Y-%m-%d') if item.agendamento else '',
                'protocolo': item.protocolo or '',
                'separacao_lote_id': item.separacao_lote_id or '',
                'tem_separacao': bool(item.separacao_lote_id),
                # Formatação brasileira para frontend
                'valor_item_formatado': f"R$ {valor_item:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'peso_item_formatado': f"{int(peso_item):,} kg".replace(',', '.'),
                'pallet_item_formatado': f"{pallet_item:,.1f} pal".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'qtd_saldo_formatado': f"{int(item.qtd_saldo_produto_pedido) if item.qtd_saldo_produto_pedido else 0:,}".replace(',', '.')
            }
            itens_json.append(item_data)
        
        # 📊 ESTATÍSTICAS DO PEDIDO
        total_itens = len(itens_json)
        total_valor = sum(item['valor_item'] for item in itens_json)
        total_peso = sum(item['peso_item'] for item in itens_json)
        total_pallet = sum(item['pallet_item'] for item in itens_json)
        itens_separados = sum(1 for item in itens_json if item['tem_separacao'])
        
        return jsonify({
            'success': True,
            'num_pedido': num_pedido,
            'total_itens': total_itens,
            'itens_separados': itens_separados,
            'itens_pendentes': total_itens - itens_separados,
            'totais': {
                'valor': total_valor,
                'peso': total_peso,
                'pallet': total_pallet
            },
            'itens': itens_json
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar itens do pedido {num_pedido}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro ao carregar itens: {str(e)}'
        }), 500


# 🎯 ETAPA 3: FUNÇÕES AUXILIARES DO SISTEMA REAL (SEM WORKAROUND)






@carteira_bp.route('/api/pre-separacao/<int:pre_sep_id>')
@login_required
def api_pre_separacao_detalhes(pre_sep_id):
    """
    API para obter detalhes de uma pré-separação
    CRIADA: Rota estava faltando e sendo usada no JS linha 5687
    """
    try:
        from app.carteira.models import PreSeparacaoItem
        
        pre_sep = PreSeparacaoItem.query.get(pre_sep_id)
        if not pre_sep:
            return jsonify({
                'success': False,
                'error': f'Pré-separação {pre_sep_id} não encontrada'
            }), 404
            
        # Retornar dados da pré-separação
        dados = {
            'success': True,
            'id': pre_sep.id,
            'num_pedido': pre_sep.num_pedido,
            'cod_produto': pre_sep.cod_produto,
            'nome_produto': pre_sep.nome_produto,
            'qtd_original_carteira': float(pre_sep.qtd_original_carteira or 0),
            'qtd_selecionada_usuario': float(pre_sep.qtd_selecionada_usuario or 0),
            'qtd_restante_calculada': float(pre_sep.qtd_restante_calculada or 0),
            'data_expedicao_editada': pre_sep.data_expedicao_editada.strftime('%Y-%m-%d') if pre_sep.data_expedicao_editada else None,
            'data_agendamento_editada': pre_sep.data_agendamento_editada.strftime('%Y-%m-%d') if pre_sep.data_agendamento_editada else None,
            'protocolo_editado': pre_sep.protocolo_editado,
            'observacoes_usuario': pre_sep.observacoes_usuario,
            'status': pre_sep.status,
            'criado_em': pre_sep.criado_em.strftime('%d/%m/%Y %H:%M') if pre_sep.criado_em else None,
            'criado_por': pre_sep.criado_por
        }
        
        return jsonify(dados)
        
    except Exception as e:
        logger.error(f"Erro ao buscar pré-separação {pre_sep_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pre-separacao/<int:pre_sep_id>/enviar-separacao', methods=['POST'])
@login_required  
def api_enviar_pre_separacao_para_separacao(pre_sep_id):
    """
    API para converter PreSeparacaoItem em Separacao definitiva
    """
    try:
        from app.carteira.models import PreSeparacaoItem
        
        data = request.get_json()
        observacoes = data.get('observacoes', '')
        
        # Buscar pré-separação
        pre_sep = PreSeparacaoItem.query.get(pre_sep_id)
        if not pre_sep:
            return jsonify({
                'success': False,
                'error': f'Pré-separação {pre_sep_id} não encontrada'
            }), 404
        
        # Verificar se pode ser enviada
        if pre_sep.status in ['ENVIADO_SEPARACAO', 'CANCELADO']:
            return jsonify({
                'success': False,
                'error': f'Pré-separação já está {pre_sep.status.lower()}'
            }), 400
        
        # Validar se tem data de expedição
        if not pre_sep.data_expedicao_editada:
            return jsonify({
                'success': False,
                'error': 'Data de expedição é obrigatória para enviar para separação'
            }), 400
        
        # Gerar lote de separação usando função local
        lote_id = _gerar_novo_lote_id()
        
        # Criar separação baseada na pré-separação
        separacao = Separacao()
        separacao.separacao_lote_id = lote_id
        separacao.num_pedido = pre_sep.num_pedido
        separacao.cod_produto = pre_sep.cod_produto
        separacao.nome_produto = pre_sep.nome_produto
        separacao.qtd_saldo = pre_sep.qtd_selecionada_usuario
        separacao.valor_saldo = pre_sep.valor_selecionado if hasattr(pre_sep, 'valor_selecionado') else 0
        
        # ✅ CALCULAR PESO E PALLET CORRETAMENTE
        peso_calculado, pallet_calculado = calcular_peso_pallet_produto(pre_sep.cod_produto, pre_sep.qtd_selecionada_usuario)
        separacao.peso = peso_calculado
        separacao.pallet = pallet_calculado
        
        separacao.cnpj_cpf = pre_sep.cnpj_cliente
        separacao.expedicao = pre_sep.data_expedicao_editada
        separacao.agendamento = pre_sep.data_agendamento_editada
        separacao.protocolo = pre_sep.protocolo_editado
        separacao.observ_ped_1 = observacoes or f"Criado a partir de pré-separação #{pre_sep.id}"
        separacao.criado_em = datetime.utcnow()
        # ❌ REMOVIDO: status (campo não existe no modelo - status está em Pedido)
        
        db.session.add(separacao)
        
        # Atualizar status da pré-separação
        pre_sep.status = 'ENVIADO_SEPARACAO'
        pre_sep.observacoes_usuario = (pre_sep.observacoes_usuario or '') + f"\n[ENVIADO para separação {lote_id} em {datetime.now().strftime('%d/%m/%Y %H:%M')}]"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Pré-separação enviada para separação com sucesso',
            'lote_id': lote_id,
            'separacao_id': separacao.id
        })
        
    except Exception as e:
        logger.error(f"Erro ao enviar pré-separação {pre_sep_id} para separação: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/estoque-projetado-28-dias')
@login_required
def api_estoque_projetado_28_dias(num_pedido):
    """
    🎯 API para calcular estoque projetado de 28 dias para itens do pedido
    
    CÁLCULO:
    - Estoque atual
    - Entrada prevista (produção + compras)
    - Saída prevista (vendas + separações)
    - Projeção para 28 dias
    """
    try:
        from datetime import datetime, timedelta
        from app.estoque.models import SaldoEstoque
        from app.producao.models import CadastroPalletizacao
        
        # Buscar itens do pedido
        itens_pedido = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido, 
            ativo=True
        ).all()
        
        if not itens_pedido:
            return jsonify({
                'success': False,
                'error': f'Nenhum item encontrado para o pedido {num_pedido}'
            }), 404
        
        # Data limite para projeção (28 dias)
        data_limite = datetime.now() + timedelta(days=28)
        
        resultado = {
            'success': True,
            'num_pedido': num_pedido,
            'data_consulta': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'projecao_dias': 28,
            'data_limite': data_limite.strftime('%d/%m/%Y'),
            'itens': []
        }
        
        for item in itens_pedido:
            try:
                # 🎯 USAR CÁLCULO EXISTENTE DO MÓDULO ESTOQUE
                estoque_info = SaldoEstoque.obter_resumo_produto(item.cod_produto, item.nome_produto)
                
                if not estoque_info:
                    # Fallback se não houver dados de estoque
                    estoque_info = {
                        'estoque_inicial': 0,
                        'previsao_ruptura': 'Sem dados',
                        'dias_restantes': 0,
                        'estoque_projetado_28d': 0
                    }
                
                # 🎯 STATUS DA PROJEÇÃO
                qtd_pedido = float(item.qtd_saldo_produto_pedido or 0)
                estoque_projetado = float(estoque_info.get('estoque_projetado_28d', 0))
                
                status_estoque = 'SUFICIENTE'
                status_class = 'success'
                
                if estoque_projetado < qtd_pedido:
                    if estoque_projetado <= 0:
                        status_estoque = 'RUPTURA'
                        status_class = 'danger'
                    else:
                        status_estoque = 'INSUFICIENTE'
                        status_class = 'warning'
                
                # 🏭 DADOS DE PALLETIZAÇÃO
                peso_unitario = 0
                palletizacao_info = 0
                try:
                    palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=item.cod_produto).first()
                    if palletizacao:
                        peso_unitario = float(palletizacao.peso_bruto or 0)
                        palletizacao_info = float(palletizacao.palletizacao or 0)
                except Exception:
                    pass
                
                item_data = {
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto or f'Produto {item.cod_produto}',
                    'qtd_pedido': qtd_pedido,
                    'estoque_atual': float(estoque_info.get('estoque_inicial', 0)),
                    'estoque_projetado_28d': estoque_projetado,
                    'previsao_ruptura': estoque_info.get('previsao_ruptura', 'Sem dados'),
                    'dias_restantes': estoque_info.get('dias_restantes', 0),
                    'diferenca': estoque_projetado - qtd_pedido,
                    'status_estoque': status_estoque,
                    'status_class': status_class,
                    'peso_unitario': peso_unitario,
                    'palletizacao': palletizacao_info,
                    'valor_unitario': float(item.preco_produto_pedido or 0),
                    'valor_total_pedido': qtd_pedido * float(item.preco_produto_pedido or 0)
                }
                
                resultado['itens'].append(item_data)
                
            except Exception as e:
                logger.error(f"Erro ao calcular estoque projetado para produto {item.cod_produto}: {e}")
                continue
        
        # 📊 RESUMO GERAL
        total_itens = len(resultado['itens'])
        itens_suficientes = len([i for i in resultado['itens'] if i['status_estoque'] == 'SUFICIENTE'])
        itens_insuficientes = len([i for i in resultado['itens'] if i['status_estoque'] == 'INSUFICIENTE'])  
        itens_ruptura = len([i for i in resultado['itens'] if i['status_estoque'] == 'RUPTURA'])
        
        # Calcular totais para compatibilidade com o frontend
        total_valor = sum(item['valor_total_pedido'] for item in resultado['itens'])
        total_peso = sum(item['qtd_pedido'] * item['peso_unitario'] for item in resultado['itens'])
        total_pallet = sum(item['qtd_pedido'] * item['palletizacao'] for item in resultado['itens'])
        
        resultado['resumo'] = {
            'total_itens': total_itens,
            'itens_suficientes': itens_suficientes,
            'itens_insuficientes': itens_insuficientes,
            'itens_ruptura': itens_ruptura,
            'percentual_disponibilidade': round((itens_suficientes / total_itens * 100) if total_itens > 0 else 0, 1)
        }
        
        # Adicionar campo totais para compatibilidade com atualizarResumoModal()
        resultado['total_itens'] = total_itens
        resultado['totais'] = {
            'valor': total_valor,
            'peso': total_peso,
            'pallet': total_pallet
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro ao calcular estoque projetado 28 dias para pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/pre-separacoes-agrupadas')
@login_required
def api_pedido_pre_separacoes_agrupadas(num_pedido):
    """
    API para carregar PreSeparacaoItem agrupadas por (expedição, agendamento, protocolo)
    para exibir no modal "Gerar Separação"
    """
    try:
        from app.carteira.models import PreSeparacaoItem
        
        # Buscar pré-separações ativas do pedido
        pre_separacoes = PreSeparacaoItem.query.filter(
            and_(
                PreSeparacaoItem.num_pedido == num_pedido,
                PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])  # Apenas ativos
            )
        ).all()
        
        if not pre_separacoes:
            return jsonify({
                'success': True,
                'agrupamentos': [],
                'total_agrupamentos': 0,
                'num_pedido': num_pedido
            })
        
        # Agrupar por (expedição, agendamento, protocolo)
        agrupamentos = {}
        
        for pre_sep in pre_separacoes:
            # Criar chave de agrupamento
            chave_exp = pre_sep.data_expedicao_editada.strftime('%Y-%m-%d') if pre_sep.data_expedicao_editada else ''
            chave_agend = pre_sep.data_agendamento_editada.strftime('%Y-%m-%d') if pre_sep.data_agendamento_editada else ''
            chave_prot = pre_sep.protocolo_editado or ''
            
            chave_agrupamento = f"{chave_exp}|{chave_agend}|{chave_prot}"
            
            if chave_agrupamento not in agrupamentos:
                agrupamentos[chave_agrupamento] = {
                    'expedicao': chave_exp,
                    'agendamento': chave_agend,
                    'protocolo': chave_prot,
                    'pre_separacoes': [],
                    'total_quantidade': 0,
                    'total_valor': 0,
                    'total_peso': 0,
                    'total_pallet': 0,
                    'produtos': []
                }
            
            # 🔍 DEBUG: Log das quantidades para investigar zeros
            qtd_selecionada = float(pre_sep.qtd_selecionada_usuario or 0)
            logger.info(f"🔍 DEBUG PreSeparacao ID {pre_sep.id}: cod={pre_sep.cod_produto}, qtd_selecionada={qtd_selecionada}, qtd_original={getattr(pre_sep, 'qtd_original_carteira', 'N/A')}")
            
            # Adicionar à lista de pré-separações do agrupamento
            agrupamentos[chave_agrupamento]['pre_separacoes'].append({
                'id': pre_sep.id,
                'cod_produto': pre_sep.cod_produto,
                'nome_produto': pre_sep.nome_produto,
                'quantidade': qtd_selecionada,
                'valor': float(pre_sep.valor_selecionado if hasattr(pre_sep, 'valor_selecionado') else 0),
                'peso': float(pre_sep.peso_selecionado if hasattr(pre_sep, 'peso_selecionado') else 0),
                'status': pre_sep.status,
                'criado_em': pre_sep.data_criacao.strftime('%d/%m/%Y %H:%M') if hasattr(pre_sep, 'data_criacao') and pre_sep.data_criacao else ''
            })
            
            # Somar totais do agrupamento
            agrupamentos[chave_agrupamento]['total_quantidade'] += float(pre_sep.qtd_selecionada_usuario)
            agrupamentos[chave_agrupamento]['total_valor'] += float(pre_sep.valor_selecionado if hasattr(pre_sep, 'valor_selecionado') else 0)
            agrupamentos[chave_agrupamento]['total_peso'] += float(pre_sep.peso_selecionado if hasattr(pre_sep, 'peso_selecionado') else 0)
            
            # Calcular pallet proporcional
            try:
                from app.producao.models import CadastroPalletizacao
                palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=pre_sep.cod_produto).first()
                if palletizacao and palletizacao.palletizacao and palletizacao.palletizacao > 0:
                    pallet_item = float(pre_sep.qtd_selecionada_usuario) / float(palletizacao.palletizacao)
                    agrupamentos[chave_agrupamento]['total_pallet'] += pallet_item
            except ImportError:
                pass
            
            # Adicionar produto à lista (se não existir)
            produto_existe = any(p['cod_produto'] == pre_sep.cod_produto for p in agrupamentos[chave_agrupamento]['produtos'])
            if not produto_existe:
                agrupamentos[chave_agrupamento]['produtos'].append({
                    'cod_produto': pre_sep.cod_produto,
                    'nome_produto': pre_sep.nome_produto
                })
        
        # Converter agrupamentos para lista
        lista_agrupamentos = []
        for i, (chave, agrup) in enumerate(agrupamentos.items(), 1):
            # Formatar valores para exibição
            agrup['id_agrupamento'] = f"agrup_{i}"
            agrup['total_valor_formatado'] = f"R$ {agrup['total_valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            agrup['total_peso_formatado'] = f"{agrup['total_peso']:,.1f} kg".replace(',', 'X').replace('.', ',').replace('X', '.')
            agrup['total_pallet_formatado'] = f"{agrup['total_pallet']:,.1f} pal".replace(',', 'X').replace('.', ',').replace('X', '.')
            agrup['total_produtos'] = len(agrup['produtos'])
            agrup['total_pre_separacoes'] = len(agrup['pre_separacoes'])
            
            # Criar descrição do agrupamento
            descricao_partes = []
            if agrup['expedicao']:
                descricao_partes.append(f"Exp: {datetime.strptime(agrup['expedicao'], '%Y-%m-%d').strftime('%d/%m')}")
            if agrup['agendamento']:
                descricao_partes.append(f"Agend: {datetime.strptime(agrup['agendamento'], '%Y-%m-%d').strftime('%d/%m')}")
            if agrup['protocolo']:
                descricao_partes.append(f"Prot: {agrup['protocolo']}")
            
            agrup['descricao'] = ' | '.join(descricao_partes) if descricao_partes else 'Sem agrupamento'
            
            lista_agrupamentos.append(agrup)
        
        # Ordenar por data de expedição
        lista_agrupamentos.sort(key=lambda x: x['expedicao'] or '9999-12-31')
        
        return jsonify({
            'success': True,
            'agrupamentos': lista_agrupamentos,
            'total_agrupamentos': len(lista_agrupamentos),
            'num_pedido': num_pedido
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar pré-separações agrupadas do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/agrupamentos/enviar-separacao', methods=['POST'])
@login_required
def api_enviar_agrupamentos_para_separacao():
    """
    API para enviar agrupamentos de PreSeparacaoItem para separação
    Cria 1 Separação para cada agrupamento selecionado
    """
    try:
        from app.carteira.models import PreSeparacaoItem
        
        data = request.get_json()
        agrupamentos_selecionados = data.get('agrupamentos', [])
        observacoes_gerais = data.get('observacoes', '')
        
        if not agrupamentos_selecionados:
            return jsonify({
                'success': False,
                'error': 'Selecione pelo menos um agrupamento'
            }), 400
        
        separacoes_criadas = []
        
        for agrup_data in agrupamentos_selecionados:
            pre_separacao_ids = agrup_data.get('pre_separacao_ids', [])
            
            if not pre_separacao_ids:
                continue
            
            # Buscar pré-separações do agrupamento
            pre_separacoes = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.id.in_(pre_separacao_ids)
            ).all()
            
            if not pre_separacoes:
                continue
            
            # Gerar lote de separação para o agrupamento usando função local
            lote_id = _gerar_novo_lote_id()
            
            # Pegar dados do primeiro item para dados gerais
            primeira_pre_sep = pre_separacoes[0]
            
            # Criar separações individuais para cada pré-separação do agrupamento
            for pre_sep in pre_separacoes:
                # Verificar se pode ser enviada
                if pre_sep.status not in ['CRIADO', 'RECOMPOSTO']:
                    continue
                
                # Buscar item da carteira para dados completos
                carteira_item = CarteiraPrincipal.query.filter_by(
                    num_pedido=pre_sep.num_pedido,
                    cod_produto=pre_sep.cod_produto
                ).first()
                
                # ✅ CALCULAR PESO E PALLET CORRETAMENTE
                peso_calculado, pallet_calculado = calcular_peso_pallet_produto(pre_sep.cod_produto, pre_sep.qtd_selecionada_usuario)
                
                # ✅ BUSCAR ROTA POR UF (funções já definidas neste arquivo)
                cod_uf_item = carteira_item.cod_uf if carteira_item else 'SP'
                nome_cidade_item = carteira_item.nome_cidade if carteira_item else ''
                rota_calculada = _buscar_rota_por_uf(cod_uf_item)
                sub_rota_calculada = _buscar_sub_rota_por_uf_cidade(cod_uf_item, nome_cidade_item)
                
                # Criar separação com TODOS os campos obrigatórios
                separacao = Separacao(
                    separacao_lote_id=lote_id,
                    num_pedido=pre_sep.num_pedido,
                    data_pedido=carteira_item.data_pedido if carteira_item else None,
                    cnpj_cpf=pre_sep.cnpj_cliente,
                    raz_social_red=carteira_item.raz_social_red if carteira_item else '',
                    nome_cidade=carteira_item.nome_cidade if carteira_item else '',
                    cod_uf=cod_uf_item,  # ✅ OBRIGATÓRIO! 
                    cod_produto=pre_sep.cod_produto,
                    nome_produto=pre_sep.nome_produto,
                    qtd_saldo=pre_sep.qtd_selecionada_usuario,
                    valor_saldo=pre_sep.valor_selecionado if hasattr(pre_sep, 'valor_selecionado') else 0,
                    peso=peso_calculado,
                    pallet=pallet_calculado,
                    rota=rota_calculada,
                    sub_rota=sub_rota_calculada,
                    observ_ped_1=f"{observacoes_gerais}\n[Agrupamento: {agrup_data.get('descricao', 'N/A')}]",
                    roteirizacao=None,  # Para preenchimento futuro
                    expedicao=pre_sep.data_expedicao_editada,
                    agendamento=pre_sep.data_agendamento_editada,
                    protocolo=pre_sep.protocolo_editado,
                    tipo_envio='total',  # Valor padrão
                    criado_em=agora_brasil()
                )
                
                db.session.add(separacao)
                
                # Atualizar status da pré-separação
                pre_sep.status = 'ENVIADO_SEPARACAO'
                pre_sep.observacoes_usuario = (pre_sep.observacoes_usuario or '') + f"\n[ENVIADO para separação {lote_id} em {datetime.now().strftime('%d/%m/%Y %H:%M')}]"
            
            separacoes_criadas.append({
                'lote_id': lote_id,
                'total_itens': len(pre_separacoes),
                'descricao': agrup_data.get('descricao', 'N/A')
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(separacoes_criadas)} separação(ões) criada(s) com sucesso',
            'separacoes_criadas': separacoes_criadas
        })
        
    except Exception as e:
        logger.error(f"Erro ao enviar agrupamentos para separação: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


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
        item = CarteiraPrincipal.query.get(item_id)
        if not item:
            return jsonify({
                'success': False,
                'error': f'Item {item_id} não encontrado'
            }), 404
        
        # Recalcular estoques usando data de expedição dinâmica
        try:
            # Data de expedição específica do item (ou hoje+1 se não definida)
            data_expedicao = item.expedicao or (datetime.now().date() + timedelta(days=1))
            
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


@carteira_bp.route('/api/item/<item_id>/salvar-alteracao', methods=['POST'])
@login_required
def api_salvar_alteracao_item(item_id):
    """
    API para salvar alterações automáticas de um item
    """
    try:
        data = request.get_json()
        campo = data.get('campo')
        valor = data.get('valor')
        
        if not campo:
            return jsonify({
                'success': False,
                'error': 'Campo é obrigatório'
            }), 400
        
        # Buscar item da carteira
        item = CarteiraPrincipal.query.get(item_id)
        if not item:
            return jsonify({
                'success': False,
                'error': f'Item {item_id} não encontrado'
            }), 404
        
        # Atualizar campo conforme tipo
        if campo == 'expedicao':
            if valor:
                try:
                    item.expedicao = datetime.strptime(valor, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'success': False, 'error': 'Data de expedição inválida'}), 400
            else:
                item.expedicao = None
                
        elif campo == 'agendamento':
            if valor:
                try:
                    item.agendamento = datetime.strptime(valor, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'success': False, 'error': 'Data de agendamento inválida'}), 400
            else:
                item.agendamento = None
                
        elif campo == 'protocolo':
            item.protocolo = valor
            
        elif campo == 'quantidade':
            # Para quantidade, criar PreSeparacaoItem se necessário
            qtd_nova = float(valor) if valor else 0
            qtd_original = float(item.qtd_saldo_produto_pedido or 0)
            
            if qtd_nova < qtd_original:
                # Criar ou atualizar PreSeparacaoItem
                from app.carteira.models import PreSeparacaoItem
                
                pre_separacao = PreSeparacaoItem.query.filter_by(
                    num_pedido=item.num_pedido,
                    cod_produto=item.cod_produto
                ).first()
                
                if pre_separacao:
                    pre_separacao.qtd_selecionada_usuario = qtd_nova
                else:
                    pre_separacao = PreSeparacaoItem()
                    pre_separacao.num_pedido = item.num_pedido
                    pre_separacao.cod_produto = item.cod_produto
                    pre_separacao.qtd_selecionada_usuario = qtd_nova
                    pre_separacao.qtd_original_carteira = qtd_original
                    pre_separacao.qtd_restante_calculada = qtd_original - qtd_nova
                    pre_separacao.valor_original_item = float(item.preco_produto_pedido or 0) * qtd_original
                    pre_separacao.peso_original_item = 0  # TODO: Calcular peso correto
                    pre_separacao.cnpj_cliente = item.cnpj_cpf
                    pre_separacao.nome_produto = item.nome_produto
                    pre_separacao.data_expedicao_editada = item.expedicao
                    pre_separacao.data_agendamento_editada = item.agendamento
                    pre_separacao.protocolo_editado = item.protocolo
                    db.session.add(pre_separacao)
        
        # Salvar alterações
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Campo {campo} atualizado com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar alteração do item {item_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/item/<item_id>/dividir-linha', methods=['POST'])
@login_required
def api_dividir_linha_item(item_id):
    """
    🎯 FLUXO COMPLETO: Divisão com controle de restauração
    
    PROCESSO:
    1. Item original 500 unidades → fica OCULTO/FRACIONADO
    2. Cria pré-separação 100 unidades (com referência ao original)
    3. Cria linha saldo 400 unidades
    4. Se cancelar → restaura item original 500, deleta saldo
    """
    try:
        data = request.get_json()
        qtd_utilizada = float(data.get('qtd_utilizada', 0))
        
        if qtd_utilizada <= 0:
            return jsonify({
                'success': False,
                'error': 'Quantidade deve ser maior que zero'
            }), 400
        
        # Buscar item da carteira
        item = CarteiraPrincipal.query.get(item_id)
        if not item:
            return jsonify({
                'success': False,
                'error': f'Item {item_id} não encontrado'
            }), 404
        
        # Verificar se item já foi fracionado
        if hasattr(item, 'fracionado') and item.fracionado:
            return jsonify({
                'success': False,
                'error': 'Item já foi fracionado anteriormente'
            }), 400
        
        qtd_original = float(item.qtd_saldo_produto_pedido or 0)
        
        if qtd_utilizada >= qtd_original:
            return jsonify({
                'success': False,
                'error': 'Quantidade utilizada deve ser menor que a original'
            }), 400
        
        qtd_restante = qtd_original - qtd_utilizada
        
        # 🔧 STEP 1: MARCAR item original como fracionado (ocultar)
        # Adicionar campo temporário para controle
        if not hasattr(item, '_dados_backup'):
            item._dados_backup = {
                'qtd_original': qtd_original,
                'visivel': True
            }
        
        # 🔧 STEP 2: Criar PreSeparacaoItem com REFERÊNCIA ao item original
        from app.carteira.models import PreSeparacaoItem
        
        pre_separacao = PreSeparacaoItem()
        pre_separacao.num_pedido = item.num_pedido
        pre_separacao.cod_produto = item.cod_produto
        pre_separacao.qtd_selecionada_usuario = qtd_utilizada
        pre_separacao.qtd_original_carteira = qtd_original
        pre_separacao.qtd_restante_calculada = qtd_restante
        pre_separacao.valor_original_item = float(item.preco_produto_pedido or 0) * qtd_original
        pre_separacao.peso_original_item = 0  # TODO: Calcular peso correto
        pre_separacao.cnpj_cliente = item.cnpj_cpf
        pre_separacao.nome_produto = item.nome_produto
        pre_separacao.data_expedicao_editada = item.expedicao
        pre_separacao.data_agendamento_editada = item.agendamento
        pre_separacao.protocolo_editado = item.protocolo
        
        # Observação removida - cancelamento simples
        
        db.session.add(pre_separacao)
        db.session.flush()  # Para obter ID da pré-separação
        
        # 🔧 STEP 3: Criar linha saldo preservando dados originais
        novo_item = CarteiraPrincipal(
            num_pedido=item.num_pedido,
            cod_produto=item.cod_produto,
            qtd_saldo_produto_pedido=qtd_restante,
            nome_produto=f"[SALDO] {item.nome_produto}",
            preco_produto_pedido=item.preco_produto_pedido,
            # Copiar outros campos relevantes preservando dados originais
            cnpj_cpf=item.cnpj_cpf,
            raz_social_red=item.raz_social_red,
            data_pedido=item.data_pedido,
            status_pedido=item.status_pedido,
            vendedor=item.vendedor,
        )
        db.session.add(novo_item)
        
        # 🔧 ARQUITETURA CORRETA: CarteiraPrincipal não deve ser alterada
        # Separações e pré-separações são modelos operacionais
        # O saldo será calculado dinamicamente: carteira - pré_separações - separações_ativas
        
        # Salvar alterações
        db.session.commit()
        
        logger.info(f"✅ Item {item_id} fracionado: {qtd_utilizada}/{qtd_original}, pré-sep {pre_separacao.id}, saldo {novo_item.id}")
        
        return jsonify({
            'success': True,
            'message': f'Item fracionado com sucesso: {qtd_utilizada} de {qtd_original}',
            'pre_separacao_id': pre_separacao.id,
            'novo_item_id': novo_item.id,
            'item_original_id': item_id,
            'qtd_utilizada': qtd_utilizada,
            'qtd_restante': qtd_restante
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao dividir linha do item {item_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/criar-separacao', methods=['POST'])
@login_required
def api_criar_separacao_pedido(num_pedido):
    """
    API para criar separação a partir de itens selecionados (dropdown ou modal)
    """
    try:
        data = request.get_json()
        itens = data.get('itens', [])
        
        if not itens:
            return jsonify({
                'success': False,
                'error': 'Nenhum item fornecido para separação'
            }), 400
        
        # Validar se todos os itens têm data de expedição
        for item in itens:
            if not item.get('expedicao'):
                return jsonify({
                    'success': False,
                    'error': 'Todos os itens devem ter Data de Expedição preenchida'
                }), 400
        
        # Gerar ID único para o lote usando função centralizada
        separacao_lote_id = _gerar_novo_lote_id()
        
        # Criar separações para cada item
        separacoes_criadas = []
        
        for item in itens:
            item_id = item.get('item_id')
            qtd_separacao = float(item.get('qtd_separacao', 0))
            expedicao = item.get('expedicao')
            agendamento = item.get('agendamento')
            protocolo = item.get('protocolo')
            
            if qtd_separacao <= 0:
                continue
            
            # Buscar item da carteira
            carteira_item = CarteiraPrincipal.query.get(item_id)
            if not carteira_item:
                continue
            
            # Converter data de expedição
            try:
                expedicao_obj = datetime.strptime(expedicao, '%Y-%m-%d').date() if expedicao else None
            except ValueError:
                expedicao_obj = None
            
            try:
                data_agend_obj = datetime.strptime(agendamento, '%Y-%m-%d').date() if agendamento else None
            except ValueError:
                data_agend_obj = None
            
            # Calcular valores proporcionais
            preco_unitario = float(carteira_item.preco_produto_pedido or 0)
            valor_separacao = qtd_separacao * preco_unitario
            
            # ✅ CALCULAR PESO E PALLET CORRETAMENTE
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(carteira_item.cod_produto, qtd_separacao)
            
            # ✅ BUSCAR ROTA POR UF DO CLIENTE (funções já definidas neste arquivo)
            rota_calculada = _buscar_rota_por_uf(carteira_item.cod_uf or 'SP')
            
            # ✅ BUSCAR SUB-ROTA POR UF E CIDADE  
            sub_rota_calculada = _buscar_sub_rota_por_uf_cidade(
                carteira_item.cod_uf or '', 
                carteira_item.nome_cidade or ''
            )
            
            # Criar separação com TODOS os campos obrigatórios
            separacao = Separacao(
                separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                data_pedido=carteira_item.data_pedido,  # ✅ ADICIONADO
                cnpj_cpf=carteira_item.cnpj_cpf,
                raz_social_red=carteira_item.raz_social_red,  # ✅ ADICIONADO
                nome_cidade=carteira_item.nome_cidade,  # ✅ ADICIONADO
                cod_uf=carteira_item.cod_uf,  # ✅ OBRIGATÓRIO
                cod_produto=carteira_item.cod_produto,
                nome_produto=carteira_item.nome_produto,  # ✅ ADICIONADO
                qtd_saldo=qtd_separacao,
                valor_saldo=valor_separacao,
                peso=peso_calculado,
                pallet=pallet_calculado,
                rota=rota_calculada,  # ✅ ADICIONADO
                sub_rota=sub_rota_calculada,  # ✅ ADICIONADO
                observ_ped_1=carteira_item.observ_ped_1,  # ✅ ADICIONADO
                roteirizacao=None,  # ✅ ADICIONADO - será preenchido na roteirização
                expedicao=expedicao_obj,
                agendamento=data_agend_obj,
                protocolo=protocolo,
                tipo_envio='total',  # ✅ ADICIONADO - valor padrão
                criado_em=agora_brasil()
            )
            
            db.session.add(separacao)
            separacoes_criadas.append(separacao)
        
        if not separacoes_criadas:
            return jsonify({
                'success': False,
                'error': 'Nenhuma separação válida foi criada'
            }), 400
        
        # Salvar alterações
        db.session.commit()
        
        return jsonify({
            'success': True,
            'separacao_lote_id': separacao_lote_id,
            'total_separacoes': len(separacoes_criadas),
            'message': f'Separação criada com sucesso! Lote: {separacao_lote_id}'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar separação para pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@carteira_bp.route('/api/pedido/<num_pedido>/agendamento-existente')
@login_required
def api_pedido_agendamento_existente(num_pedido):
    """
    API para buscar agendamento existente de um pedido
    Chamada pelo JavaScript em listar_agrupados.html linha 2465
    """
    try:
        # Buscar primeiro item do pedido para obter dados de agendamento
        item = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).first()
        
        if not item:
            return jsonify({
                'success': False,
                'error': f'Pedido {num_pedido} não encontrado'
            }), 404
        
        # Buscar contato de agendamento do cliente
        from app.cadastros_agendamento.models import ContatoAgendamento
        contato = ContatoAgendamento.query.filter_by(cnpj=item.cnpj_cpf).first()
        
        # Preparar dados do agendamento existente
        agendamento_data = {
            'success': True,
            'agendamento': {
                'data_agendamento': item.agendamento.strftime('%Y-%m-%d') if item.agendamento else None,
                'hora_agendamento': item.hora_agendamento.strftime('%H:%M') if item.hora_agendamento else None,
                'expedicao': item.expedicao.strftime('%Y-%m-%d') if item.expedicao else None,
                'protocolo': item.protocolo or '',
                'observacoes': item.observ_ped_1 or '',
                'agenda_confirmada': item.agendamento_confirmado or False,
                'cliente_nec_agendamento': item.cliente_nec_agendamento == 'Sim',
                'contato_agendamento': {
                    'forma': contato.forma if contato else None,
                    'contato': contato.contato if contato else None,
                    'observacao': contato.observacao if contato else None
                } if contato else None
            }
        }
        
        return jsonify(agendamento_data)
        
    except Exception as e:
        logger.error(f"Erro ao buscar agendamento existente do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


# REMOVIDO: Rotas de Carteira Não-Odoo movidas para views_nao_odoo.py
# REMOVIDO: Registro de blueprints movido para __init__.py

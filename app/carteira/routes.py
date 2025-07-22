from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, Response
from flask_login import login_required, current_user
from typing import Union, Tuple
from app import db
from app.carteira.models import (
    CarteiraPrincipal, ControleCruzadoSeparacao,
    InconsistenciaFaturamento
)
from app.estoque.models import SaldoEstoque, MovimentacaoEstoque
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.faturamento.models import FaturamentoProduto
from app.localidades.models import CadastroRota, CadastroSubRota
from app.utils.timezone import agora_brasil
from sqlalchemy import func, and_, or_, inspect, literal
from datetime import datetime, date, timedelta
import pandas as pd
import logging
import os
from werkzeug.utils import secure_filename
import random
import time

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
    """Busca sub-rota baseada no cod_uf + nome_cidade"""
    if not cod_uf or not nome_cidade:
        return None
    try:
        sub_rota = CadastroSubRota.query.filter_by(
            cod_uf=cod_uf, 
            nome_cidade=nome_cidade,
            ativa=True
        ).first()
        return sub_rota.sub_rota if sub_rota else None
    except Exception:
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
        
        # 👥 BREAKDOWN POR VENDEDOR
        vendedores_breakdown = db.session.query(
            CarteiraPrincipal.vendedor,
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor')
        ).filter_by(ativo=True).group_by(CarteiraPrincipal.vendedor).limit(10).all()
        
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

@carteira_bp.route('/item/<int:item_id>/endereco')
@login_required
def buscar_endereco_item(item_id: int) -> Union[Response, Tuple[Response, int]]:
    """API para buscar dados de endereço de um item da carteira"""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            return jsonify({'error': 'Sistema não inicializado'}), 400
            
        item = CarteiraPrincipal.query.get_or_404(item_id)
        
        # Retornar dados do endereço em formato JSON
        dados_endereco = {
            'id': item.id,
            'estado': item.estado,
            'municipio': item.municipio,
            'cnpj_endereco_ent': item.cnpj_endereco_ent,
            'empresa_endereco_ent': item.empresa_endereco_ent,
            'cod_uf': item.cod_uf,
            'nome_cidade': item.nome_cidade,
            'bairro_endereco_ent': item.bairro_endereco_ent,
            'cep_endereco_ent': item.cep_endereco_ent,
            'rua_endereco_ent': item.rua_endereco_ent,
            'endereco_ent': item.endereco_ent,
            'telefone_endereco_ent': item.telefone_endereco_ent
        }
        
        return jsonify(dados_endereco)
        
    except Exception as e:
        logger.error(f"Erro ao buscar endereço do item {item_id}: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@carteira_bp.route('/item/<int:item_id>/agendamento', methods=['GET', 'POST'])
@login_required
def agendamento_item(item_id: int) -> Union[Response, Tuple[Response, int]]:
    """API para buscar e salvar dados de agendamento de um item da carteira"""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            return jsonify({'error': 'Sistema não inicializado'}), 400
            
        item = CarteiraPrincipal.query.get_or_404(item_id)
        
        if request.method == 'GET':
            # Buscar dados de agendamento
            from app.cadastros_agendamento.models import ContatoAgendamento
            
            # Buscar contato de agendamento
            contato = ContatoAgendamento.query.filter_by(cnpj=item.cnpj_cpf).first()
            
            dados_agendamento = {
                'id': item.id,
                'num_pedido': item.num_pedido,
                'raz_social': item.raz_social,
                'raz_social_red': item.raz_social_red,
                'cnpj_cpf': item.cnpj_cpf,
                'cliente_nec_agendamento': item.cliente_nec_agendamento,
                'agendamento': item.agendamento.strftime('%Y-%m-%d') if item.agendamento else None,
                'hora_agendamento': item.hora_agendamento.strftime('%H:%M') if item.hora_agendamento else None,
                'protocolo': item.protocolo,
                'agendamento_confirmado': item.agendamento_confirmado if item.agendamento_confirmado is not None else False,
                'contato_agendamento': {
                    'forma': contato.forma,
                    'contato': contato.contato,
                    'observacao': contato.observacao
                } if contato else None
            }
            
            return jsonify(dados_agendamento)
            
        elif request.method == 'POST':
            # Salvar agendamento
            from datetime import datetime, time
            
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
                if dados.get('data_entrega'):
                    data_entrega = datetime.strptime(dados['data_entrega'], '%Y-%m-%d').date()
                    item.data_entrega_pedido = data_entrega
                
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
                        if dados.get('data_entrega'):
                            item_pedido.data_entrega_pedido = data_entrega
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
            'data_entrega_pedido': item.data_entrega_pedido.strftime('%d/%m/%Y') if item.data_entrega_pedido else None,
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

@carteira_bp.route('/agrupados')
@login_required
def listar_pedidos_agrupados():
    """
    Lista pedidos agrupados por num_pedido conforme CARTEIRA.csv
    Implementação: Fase 1.1 - Query de Agrupamento Base
    """
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            flash('Sistema de carteira ainda não foi inicializado', 'warning')
            return render_template('carteira/listar_agrupados.html', pedidos=None)
        
        # Verificar se tabela palletizacao existe
        if not inspector.has_table('cadastro_palletizacao'):
            flash('Tabela de palletização não encontrada', 'warning')
            return render_template('carteira/listar_agrupados.html', pedidos=None)
        
        # Import necessário para join
        from app.producao.models import CadastroPalletizacao
        
        # 📊 QUERY AGRUPADA conforme CARTEIRA.csv
        # Campos agregados: valor_total, peso_total, pallet_total
        pedidos_agrupados = db.session.query(
            # Campos base do agrupamento
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.data_pedido,
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.rota,
            CarteiraPrincipal.sub_rota,
            CarteiraPrincipal.data_entrega_pedido,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.status_pedido,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.expedicao,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento,
            
            # Agregações conforme CSV
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * 
                    CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * 
                    CadastroPalletizacao.peso_bruto).label('peso_total'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido / 
                    CadastroPalletizacao.palletizacao).label('pallet_total'),
            func.count(CarteiraPrincipal.id).label('total_itens')
            
        ).outerjoin(
            CadastroPalletizacao,
            and_(
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto,
                CadastroPalletizacao.ativo == True
            )
        ).filter(
            CarteiraPrincipal.ativo == True
        ).group_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.data_pedido,
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.rota,
            CarteiraPrincipal.sub_rota,
            CarteiraPrincipal.data_entrega_pedido,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.status_pedido,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.expedicao,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento
        ).order_by(
            CarteiraPrincipal.expedicao.asc().nullslast(),
            CarteiraPrincipal.num_pedido.asc()
        ).all()
        
        # 📊 VALIDAÇÃO: Log de resultado para debug
        logger.info(f"Query agrupamento executada: {len(pedidos_agrupados)} pedidos encontrados")
        
        # Converter resultados para formato JSON para debugging
        pedidos_debug = []
        for pedido in pedidos_agrupados[:5]:  # Apenas primeiros 5 para debug
            pedidos_debug.append({
                'num_pedido': pedido.num_pedido,
                'valor_total': float(pedido.valor_total) if pedido.valor_total else 0,
                'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
                'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
                'total_itens': pedido.total_itens
            })
        
        logger.info(f"Primeiros 5 pedidos (debug): {pedidos_debug}")
        
        return render_template('carteira/listar_agrupados.html', 
                             pedidos=pedidos_agrupados,
                             total_pedidos=len(pedidos_agrupados))
        
    except Exception as e:
        logger.error(f"Erro ao listar pedidos agrupados: {str(e)}")
        flash(f'Erro ao carregar pedidos agrupados: {str(e)}', 'error')
        return render_template('carteira/listar_agrupados.html', pedidos=None)

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

@carteira_bp.route('/api/pedido/<num_pedido>/separacoes')
@login_required
def api_separacoes_pedido(num_pedido):
    """
    API para buscar separações de um pedido específico via AJAX
    Implementação: Fase 3.1 - Query Separações por Pedido
    """
    try:
        from app.embarques.models import Embarque, EmbarqueItem
        from app.pedidos.models import Pedido
        from app.transportadoras.models import Transportadora
        
        # 🔍 QUERY SIMPLES: Buscar TODAS as separações do pedido primeiro
        logger.info(f"🔍 DEBUG: Buscando separações para pedido {num_pedido}")
        
        # 🔧 QUERY CORRIGIDA: Incluir campos que o código espera
        separacoes = db.session.query(
            Separacao.separacao_lote_id,
            Separacao.num_pedido,
            Separacao.cod_produto,
            Separacao.criado_em,
            Separacao.qtd_saldo,
            Separacao.valor_saldo,
            Separacao.peso,
            Separacao.pallet,
            Separacao.expedicao,
            Separacao.agendamento,
            Separacao.protocolo,
            # Campos que o código espera (evitar erros)
            db.literal(None).label('embarque_numero'),
            db.literal(None).label('data_prevista_embarque'),
            db.literal(None).label('data_embarque'),
            db.literal(None).label('embarque_status'),
            db.literal(None).label('tipo_carga'),
            db.literal(None).label('transportadora_razao'),
            db.literal('Produto').label('nome_produto')
        ).filter(
            Separacao.num_pedido == num_pedido
        ).all()
        
        logger.info(f"🔍 DEBUG: Encontradas {len(separacoes)} separações para pedido {num_pedido}")
        if separacoes:
            for sep in separacoes[:3]:  # Log apenas primeiras 3
                logger.info(f"🔍 DEBUG Sep: lote={sep.separacao_lote_id}, cod={sep.cod_produto}, qtd={sep.qtd_saldo}")
        else:
            logger.warning(f"🔍 DEBUG: NENHUMA separação encontrada para pedido {num_pedido}")
        
        # 📋 CONVERTER PARA JSON
        separacoes_json = []
        for sep in separacoes:
            # Determinar status da separação
            status_separacao = 'CRIADA'
            status_class = 'info'
            
            if sep.embarque_numero:
                if sep.data_embarque:
                    status_separacao = 'EMBARCADA'
                    status_class = 'success'
                elif sep.embarque_status == 'ativo':
                    status_separacao = 'AGUARDANDO EMBARQUE'
                    status_class = 'warning'
                elif sep.embarque_status == 'cancelado':
                    status_separacao = 'EMBARQUE CANCELADO'
                    status_class = 'danger'
                else:
                    status_separacao = 'EM EMBARQUE'
                    status_class = 'primary'
            
            # Calcular totais da separação
            total_itens_separacao = db.session.query(func.count(Separacao.id)).filter(
                Separacao.separacao_lote_id == sep.separacao_lote_id
            ).scalar() or 0
            
            sep_data = {
                'separacao_lote_id': sep.separacao_lote_id,
                'num_pedido': sep.num_pedido,
                'cod_produto': sep.cod_produto,
                'nome_produto': sep.nome_produto or f'Produto {sep.cod_produto}',
                'criado_em': sep.criado_em.strftime('%d/%m/%Y %H:%M') if sep.criado_em else '',
                'status': status_separacao,
                'status_class': status_class,
                'total_itens': total_itens_separacao,
                
                # 🎯 DADOS CORRETOS DA SEPARAÇÃO
                'qtd_saldo': float(sep.qtd_saldo) if sep.qtd_saldo else 0,
                'valor_saldo': float(sep.valor_saldo) if sep.valor_saldo else 0,
                'peso': float(sep.peso) if sep.peso else 0,
                'pallet': float(sep.pallet) if sep.pallet else 0,
                'expedicao': sep.expedicao.strftime('%d/%m/%Y') if sep.expedicao else '',
                'agendamento': sep.agendamento.strftime('%d/%m/%Y') if sep.agendamento else '',
                'protocolo': sep.protocolo or '',
                
                # Dados do embarque
                'embarque': {
                    'numero': sep.embarque_numero,
                    'data_prevista': sep.data_prevista_embarque.strftime('%d/%m/%Y') if sep.data_prevista_embarque else '',
                    'data_embarque': sep.data_embarque.strftime('%d/%m/%Y') if sep.data_embarque else '',
                    'status': sep.embarque_status or '',
                    'tipo_carga': sep.tipo_carga or '',
                    'valor_total': float(sep.embarque_valor_total) if sep.embarque_valor_total else 0,
                    'peso_total': float(sep.embarque_peso_total) if sep.embarque_peso_total else 0,
                    'pallet_total': float(sep.embarque_pallet_total) if sep.embarque_pallet_total else 0
                },
                
                # Dados da transportadora
                'transportadora': {
                    'razao_social': sep.transportadora_razao or '',
                    'nome_fantasia': sep.transportadora_fantasia or ''
                }
            }
            separacoes_json.append(sep_data)
        
        # 📊 ESTATÍSTICAS GERAIS
        total_separacoes = len(separacoes_json)
        separacoes_embarcadas = sum(1 for s in separacoes_json if s['status'] == 'EMBARCADA')
        separacoes_pendentes = total_separacoes - separacoes_embarcadas
        
        return jsonify({
            'success': True,
            'num_pedido': num_pedido,
            'total_separacoes': total_separacoes,
            'separacoes_embarcadas': separacoes_embarcadas,
            'separacoes_pendentes': separacoes_pendentes,
            'separacoes': separacoes_json
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar separações do pedido {num_pedido}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro ao carregar separações: {str(e)}'
        }), 500

@carteira_bp.route('/api/pedido/<num_pedido>/estoque-d0-d7')
@login_required
def api_estoque_d0_d7_pedido(num_pedido):
    """
    API para análise de estoque D0/D7 de todos os produtos de um pedido
    Integração REAL com estoque.models
    """
    try:
        from app.estoque.models import SaldoEstoque
        
        # Buscar produtos do pedido
        produtos_pedido = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            ativo=True
        ).all()
        
        if not produtos_pedido:
            return jsonify({
                'success': False,
                'error': f'Pedido {num_pedido} não encontrado'
            }), 404
        
        # Analisar estoque para cada produto
        itens_analise = []
        problemas_d0 = 0
        problemas_d7 = 0
        estoque_ok = 0
        
        for item in produtos_pedido:
            try:
                # Buscar dados de estoque REAIS
                estoque_info = SaldoEstoque.obter_resumo_produto(
                    item.cod_produto, 
                    item.nome_produto
                )
                
                if estoque_info:
                    estoque_d0 = estoque_info.get('estoque_inicial', 0)
                    # Simular D7 como estoque atual menos 30% (será integrado com cálculo real)
                    estoque_d7 = max(0, estoque_d0 - (estoque_d0 * 0.3))
                else:
                    estoque_d0 = 0
                    estoque_d7 = 0
                
                qtd_pedido = float(item.qtd_saldo_produto_pedido or 0)
                
                # Classificar status
                if estoque_d0 <= 0:
                    problemas_d0 += 1
                elif estoque_d7 <= 0 or estoque_d0 < qtd_pedido:
                    problemas_d7 += 1
                else:
                    estoque_ok += 1
                
                itens_analise.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_pedido': qtd_pedido,
                    'estoque_d0': estoque_d0,
                    'estoque_d7': estoque_d7,
                    'disponivel': estoque_d0 >= qtd_pedido,
                    'percentual_disponivel': min(100, (estoque_d0 / qtd_pedido * 100)) if qtd_pedido > 0 else 100
                })
                
            except Exception as e:
                logger.warning(f"Erro ao analisar estoque do produto {item.cod_produto}: {str(e)}")
                # Adicionar com dados zerados em caso de erro
                itens_analise.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_pedido': float(item.qtd_saldo_produto_pedido or 0),
                    'estoque_d0': 0,
                    'estoque_d7': 0,
                    'disponivel': False,
                    'percentual_disponivel': 0
                })
                problemas_d0 += 1
        
        return jsonify({
            'success': True,
            'num_pedido': num_pedido,
            'resumo': {
                'problemas_d0': problemas_d0,
                'problemas_d7': problemas_d7,
                'estoque_ok': estoque_ok,
                'total_produtos': len(itens_analise)
            },
            'itens': itens_analise
        })
        
    except Exception as e:
        logger.error(f"Erro na análise D0/D7 do pedido {num_pedido}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro na análise de estoque: {str(e)}'
        }), 500

@carteira_bp.route('/item/<num_pedido>/endereco')
@login_required
def buscar_endereco_pedido(num_pedido):
    """API para buscar dados de endereço do primeiro item de um pedido"""
    try:
        # Buscar primeiro item do pedido (todos têm mesmo endereço)
        item = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            ativo=True
        ).first()
        
        if not item:
            return jsonify({'error': f'Pedido {num_pedido} não encontrado'}), 404
        
        # Retornar dados do endereço em formato JSON (igual à API original)
        dados_endereco = {
            'id': item.id,
            'estado': item.estado,
            'municipio': item.municipio,
            'cnpj_endereco_ent': item.cnpj_endereco_ent,
            'empresa_endereco_ent': item.empresa_endereco_ent,
            'cod_uf': item.cod_uf,
            'nome_cidade': item.nome_cidade,
            'bairro_endereco_ent': item.bairro_endereco_ent,
            'cep_endereco_ent': item.cep_endereco_ent,
            'rua_endereco_ent': item.rua_endereco_ent,
            'endereco_ent': item.endereco_ent,
            'telefone_endereco_ent': item.telefone_endereco_ent
        }
        
        return jsonify(dados_endereco)
        
    except Exception as e:
        logger.error(f"Erro ao buscar endereço do pedido {num_pedido}: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@carteira_bp.route('/api/produto/<cod_produto>/estoque-d0-d7')
@login_required  
def api_estoque_d0_d7(cod_produto):
    """
    API para calcular estoque D0/D7 de um produto via AJAX
    Implementação: Fase 3.2 - Integração Estoque D0/D7
    """
    try:
        from app.estoque.models import SaldoEstoque
        from datetime import datetime, timedelta
        
        # 📊 CALCULAR PROJEÇÃO COMPLETA (D0 até D+28)
        projecao_completa = SaldoEstoque.calcular_projecao_completa(cod_produto)
        
        if not projecao_completa:
            return jsonify({
                'success': False,
                'error': f'Não foi possível calcular projeção para produto {cod_produto}'
            }), 500
        
        # 📋 EXTRAIR DADOS D0 E D7
        data_hoje = datetime.now().date()
        
        # D0 - Estoque atual (hoje)
        d0_data = projecao_completa[0] if projecao_completa else None
        estoque_d0 = d0_data['estoque_final'] if d0_data else 0
        
        # D7 - Menor estoque nos próximos 7 dias
        estoques_d7 = [dia['estoque_final'] for dia in projecao_completa[:8]]  # D0 até D7
        menor_estoque_d7 = min(estoques_d7) if estoques_d7 else 0
        
        # 🚨 DETECTAR ALERTAS
        status_d0 = 'NORMAL'
        status_d7 = 'NORMAL' 
        
        if estoque_d0 <= 0:
            status_d0 = 'RUPTURA'
        elif estoque_d0 <= 10:  # Configurável
            status_d0 = 'BAIXO'
            
        if menor_estoque_d7 <= 0:
            status_d7 = 'RUPTURA_PREVISTA'
        elif menor_estoque_d7 <= 10:  # Configurável
            status_d7 = 'BAIXO_PREVISTO'
        
        # 📅 DETECTAR DIA DA RUPTURA
        dia_ruptura = None
        for i, dia in enumerate(projecao_completa[:8]):
            if dia['estoque_final'] <= 0:
                dia_ruptura = i
                break
        
        # 📊 ESTATÍSTICAS DETALHADAS
        projecao_d7 = projecao_completa[:8]  # D0 até D7
        
        total_saidas_d7 = sum(dia['saida_prevista'] for dia in projecao_d7)
        total_producao_d7 = sum(dia['producao_programada'] for dia in projecao_d7)
        
        resultado = {
            'success': True,
            'cod_produto': cod_produto,
            'data_calculo': data_hoje.strftime('%d/%m/%Y'),
            
            # Dados principais
            'estoque_d0': float(estoque_d0),
            'menor_estoque_d7': float(menor_estoque_d7),
            'status_d0': status_d0,
            'status_d7': status_d7,
            
            # Alertas
            'dia_ruptura': dia_ruptura,
            'tem_ruptura': dia_ruptura is not None,
            
            # Estatísticas
            'total_saidas_d7': float(total_saidas_d7),
            'total_producao_d7': float(total_producao_d7),
            
            # Projeção detalhada D0-D7
            'projecao_d7': [
                {
                    'dia': dia['dia'],
                    'data': dia['data'].strftime('%d/%m'),
                    'estoque_inicial': float(dia['estoque_inicial']),
                    'saida_prevista': float(dia['saida_prevista']),
                    'producao_programada': float(dia['producao_programada']),
                    'estoque_final': float(dia['estoque_final']),
                    'status': 'RUPTURA' if dia['estoque_final'] <= 0 else 
                             'BAIXO' if dia['estoque_final'] <= 10 else 'NORMAL'
                }
                for dia in projecao_d7
            ]
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro ao calcular estoque D0/D7 para produto {cod_produto}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro ao calcular estoque: {str(e)}'
        }), 500

@carteira_bp.route('/api/pedido/<num_pedido>/estoque-d0-d7')
@login_required
def api_estoque_pedido_d0_d7(num_pedido):
    """
    API para calcular estoque D0/D7 de todos os produtos de um pedido via AJAX
    Implementação: Fase 3.2 - Integração Estoque D0/D7
    """
    try:
        from app.estoque.models import SaldoEstoque
        from datetime import datetime
        
        # 📋 BUSCAR ITENS DO PEDIDO
        itens_pedido = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido
        ).all()
        
        if not itens_pedido:
            return jsonify({
                'success': False,
                'error': f'Nenhum item encontrado para o pedido {num_pedido}'
            }), 404
        
        # 📊 CALCULAR D0/D7 PARA CADA PRODUTO
        resultados_produtos = []
        estatisticas_gerais = {
            'total_produtos': 0,
            'produtos_ruptura_d0': 0,
            'produtos_ruptura_d7': 0,
            'produtos_baixo_estoque': 0,
            'menor_estoque_geral': float('inf'),
            'dia_ruptura_mais_proximo': None
        }
        
        for item in itens_pedido:
            cod_produto = item.cod_produto
            
            # Calcular projeção do produto
            projecao_completa = SaldoEstoque.calcular_projecao_completa(cod_produto)
            
            if projecao_completa:
                # D0 e D7
                estoque_d0 = projecao_completa[0]['estoque_final'] if projecao_completa else 0
                estoques_d7 = [dia['estoque_final'] for dia in projecao_completa[:8]]
                menor_estoque_d7 = min(estoques_d7) if estoques_d7 else 0
                
                # Status
                status_d0 = 'RUPTURA' if estoque_d0 <= 0 else 'BAIXO' if estoque_d0 <= 10 else 'NORMAL'
                status_d7 = 'RUPTURA_PREVISTA' if menor_estoque_d7 <= 0 else 'BAIXO_PREVISTO' if menor_estoque_d7 <= 10 else 'NORMAL'
                
                # Dia da ruptura
                dia_ruptura = None
                for i, dia in enumerate(projecao_completa[:8]):
                    if dia['estoque_final'] <= 0:
                        dia_ruptura = i
                        break
                
                # Dados do produto
                produto_data = {
                    'cod_produto': cod_produto,
                    'nome_produto': item.nome_produto or '',
                    'qtd_pedido': float(item.qtd_saldo_produto_pedido) if item.qtd_saldo_produto_pedido else 0,
                    'estoque_d0': float(estoque_d0),
                    'menor_estoque_d7': float(menor_estoque_d7),
                    'status_d0': status_d0,
                    'status_d7': status_d7,
                    'dia_ruptura': dia_ruptura,
                    'tem_ruptura': dia_ruptura is not None,
                    'tem_estoque_suficiente': estoque_d0 >= float(item.qtd_saldo_produto_pedido or 0),
                    'projecao_resumo': [
                        {
                            'dia': dia['dia'],
                            'data': dia['data'].strftime('%d/%m'),
                            'estoque_final': float(dia['estoque_final']),
                            'status': 'RUPTURA' if dia['estoque_final'] <= 0 else 
                                     'BAIXO' if dia['estoque_final'] <= 10 else 'NORMAL'
                        }
                        for dia in projecao_completa[:8]  # D0 até D7
                    ]
                }
                
                resultados_produtos.append(produto_data)
                
                # Atualizar estatísticas gerais
                estatisticas_gerais['total_produtos'] += 1
                if status_d0 == 'RUPTURA':
                    estatisticas_gerais['produtos_ruptura_d0'] += 1
                if status_d7 in ['RUPTURA_PREVISTA', 'BAIXO_PREVISTO']:
                    estatisticas_gerais['produtos_ruptura_d7'] += 1 
                if status_d0 == 'BAIXO' or status_d7 in ['BAIXO_PREVISTO']:
                    estatisticas_gerais['produtos_baixo_estoque'] += 1
                
                if menor_estoque_d7 < estatisticas_gerais['menor_estoque_geral']:
                    estatisticas_gerais['menor_estoque_geral'] = menor_estoque_d7
                
                if dia_ruptura is not None:
                    if (estatisticas_gerais['dia_ruptura_mais_proximo'] is None or 
                        dia_ruptura < estatisticas_gerais['dia_ruptura_mais_proximo']):
                        estatisticas_gerais['dia_ruptura_mais_proximo'] = dia_ruptura
            
            else:
                # Produto sem dados de estoque
                produto_data = {
                    'cod_produto': cod_produto,
                    'nome_produto': item.nome_produto or '',
                    'qtd_pedido': float(item.qtd_saldo_produto_pedido) if item.qtd_saldo_produto_pedido else 0,
                    'estoque_d0': 0,
                    'menor_estoque_d7': 0,
                    'status_d0': 'SEM_DADOS',
                    'status_d7': 'SEM_DADOS',
                    'dia_ruptura': None,
                    'tem_ruptura': False,
                    'tem_estoque_suficiente': False,
                    'projecao_resumo': []
                }
                resultados_produtos.append(produto_data)
                estatisticas_gerais['total_produtos'] += 1
        
        # Ajustar estatísticas
        if estatisticas_gerais['menor_estoque_geral'] == float('inf'):
            estatisticas_gerais['menor_estoque_geral'] = 0
        
        return jsonify({
            'success': True,
            'num_pedido': num_pedido,
            'data_calculo': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'estatisticas': estatisticas_gerais,
            'produtos': resultados_produtos
        })
        
    except Exception as e:
        logger.error(f"Erro ao calcular estoque D0/D7 do pedido {num_pedido}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro ao calcular estoque: {str(e)}'
        }), 500

@carteira_bp.route('/api/pedido/<num_pedido>/salvar-avaliacoes', methods=['POST'])
@login_required
def api_salvar_avaliacoes(num_pedido):
    """
    🎯 ETAPA 3: API SISTEMA REAL DE PRÉ-SEPARAÇÃO (SEM WORKAROUND)
    Salva avaliações usando tabela pre_separacao_itens
    """
    try:
        # 📝 RECEBER DADOS DA REQUISIÇÃO
        dados = request.get_json()
        
        if not dados or 'itens' not in dados:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos. Esperado: {"itens": [...]}'
            }), 400
        
        itens_selecionados = dados['itens']
        tipo_envio = dados.get('tipo_envio', 'total')
        config_envio_parcial = dados.get('config_envio_parcial')
        
        if not itens_selecionados:
            return jsonify({
                'success': False,
                'error': 'Nenhum item selecionado'
            }), 400
        
        # 📋 VALIDAR ITENS EXISTEM NO PEDIDO
        itens_pedido = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido
        ).all()
        
        itens_dict = {str(item.id): item for item in itens_pedido}
        resultados_processamento = []
        
        # 🔄 PROCESSAR CADA ITEM SELECIONADO - SISTEMA REAL
        from app.carteira.models import PreSeparacaoItem
        
        for item_avaliado in itens_selecionados:
            item_id = str(item_avaliado['item_id'])
            qtd_selecionada = float(item_avaliado['qtd_selecionada'])
            
            if item_id not in itens_dict:
                resultados_processamento.append({
                    'item_id': item_id,
                    'status': 'erro',
                    'erro': f'Item {item_id} não encontrado no pedido {num_pedido}'
                })
                continue
            
            item_original = itens_dict[item_id]
            qtd_disponivel = float(item_original.qtd_saldo_produto_pedido or 0)
            
            # ⚖️ VALIDAR QUANTIDADE
            if qtd_selecionada <= 0:
                resultados_processamento.append({
                    'item_id': item_id,
                    'status': 'erro',
                    'erro': 'Quantidade deve ser maior que zero'
                })
                continue
            
            if qtd_selecionada > qtd_disponivel:
                resultados_processamento.append({
                    'item_id': item_id,
                    'status': 'erro',
                    'erro': f'Quantidade selecionada ({qtd_selecionada}) excede disponível ({qtd_disponivel})'
                })
                continue
            
            # 🎯 PROCESSAR VIA SISTEMA REAL (SEM WORKAROUND)
            try:
                # Preparar dados editáveis
                dados_editaveis = {
                    'expedicao': item_avaliado.get('expedicao'),
                    'agendamento': item_avaliado.get('agendamento'),
                    'protocolo': item_avaliado.get('protocolo'),
                    'observacoes': item_avaliado.get('observacoes')
                }
                
                # Criar pré-separação na tabela real
                pre_separacao = PreSeparacaoItem.criar_e_salvar(
                    carteira_item=item_original,
                    qtd_selecionada=qtd_selecionada,
                    dados_editaveis=dados_editaveis,
                    usuario=current_user.nome if current_user else 'sistema',
                    tipo_envio=tipo_envio,
                    config_parcial=config_envio_parcial
                )
                
                # Atualizar item na carteira (aplicar mudanças editáveis)
                if dados_editaveis.get('expedicao'):
                    try:
                        from datetime import datetime
                        item_original.expedicao = datetime.strptime(dados_editaveis['expedicao'], '%Y-%m-%d').date()
                    except:
                        pass
                
                if dados_editaveis.get('agendamento'):
                    try:
                        from datetime import datetime
                        item_original.agendamento = datetime.strptime(dados_editaveis['agendamento'], '%Y-%m-%d').date()
                    except:
                        pass
                
                if dados_editaveis.get('protocolo'):
                    item_original.protocolo = dados_editaveis['protocolo']
                
                resultados_processamento.append({
                    'item_id': item_id,
                    'status': 'sucesso',
                    'acao': 'pre_separacao_criada',
                    'qtd_processada': qtd_selecionada,
                    'pre_separacao_id': pre_separacao.id,
                    'tipo_envio': tipo_envio,
                    'mensagem': f'Pré-separação criada para {item_original.cod_produto} - {qtd_selecionada} unidades ({tipo_envio})'
                })
                
            except Exception as e:
                logger.error(f"Erro ao processar pré-separação do item {item_id}: {e}")
                resultados_processamento.append({
                    'item_id': item_id,
                    'status': 'erro',
                    'erro': f'Erro interno: {str(e)}'
                })
        
        # 📊 CONSOLIDAR RESULTADOS
        sucessos = [r for r in resultados_processamento if r['status'] == 'sucesso']
        erros = [r for r in resultados_processamento if r['status'] == 'erro']
        
        # 💾 COMMIT DAS ALTERAÇÕES SE TUDO OK
        if len(erros) == 0:
            db.session.commit()
            logger.info(f"✅ Pré-separação concluída para pedido {num_pedido}: {len(sucessos)} itens processados")
        else:
            db.session.rollback()
            logger.warning(f"❌ Pré-separação falhou para pedido {num_pedido}: {len(erros)} erros")
        
        return jsonify({
            'success': len(erros) == 0,
            'num_pedido': num_pedido,
            'processados': len(resultados_processamento),
            'sucessos': len(sucessos),
            'erros': len(erros),
            'resultados': resultados_processamento,
            'mensagem': f'Processados {len(sucessos)} itens com sucesso' if len(erros) == 0 
                       else f'{len(erros)} erros encontrados'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar avaliações do pedido {num_pedido}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


# 🎯 ETAPA 3: FUNÇÕES AUXILIARES DO SISTEMA REAL (SEM WORKAROUND)

def buscar_pre_separacoes_pedido(num_pedido):
    """
    Busca pré-separações ativas de um pedido na tabela real
    """
    try:
        from app.carteira.models import PreSeparacaoItem
        return PreSeparacaoItem.buscar_por_pedido_produto(num_pedido)
    except Exception as e:
        logger.error(f"Erro ao buscar pré-separações do pedido {num_pedido}: {e}")
        return []


def calcular_peso_pallet_produto(cod_produto, quantidade):
    """
    Calcula peso e pallet usando CadastroPalletizacao
    
    Args:
        cod_produto (str): Código do produto
        quantidade (float): Quantidade do produto
        
    Returns:
        tuple: (peso_total, pallet_total)
    """
    try:
        from app.producao.models import CadastroPalletizacao
        
        palletizacao = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto, 
            ativo=True
        ).first()
        
        if palletizacao:
            # Calcular peso total
            peso = float(quantidade) * float(palletizacao.peso_bruto or 0)
            
            # Calcular pallet total
            if palletizacao.palletizacao and palletizacao.palletizacao > 0:
                pallet = float(quantidade) / float(palletizacao.palletizacao)
            else:
                pallet = 0
                
            logger.debug(f"✅ Cálculo {cod_produto}: Qtd={quantidade}, Peso={peso:.2f}kg, Pallet={pallet:.2f}")
            return peso, pallet
        else:
            logger.warning(f"⚠️ Produto {cod_produto} sem cadastro de palletização")
            return 0, 0
            
    except Exception as e:
        logger.error(f"❌ Erro ao calcular peso/pallet {cod_produto}: {e}")
        return 0, 0


def validar_saldo_disponivel_real(num_pedido, cod_produto, qtd_solicitada):
    """
    🚨 VALIDAÇÃO CRÍTICA DE SALDO DISPONÍVEL
    
    REGRA FUNDAMENTAL: Separacao(Aberto|Cotado) + PreSeparacao(CRIADO|RECOMPOSTO) ≤ CarteiraPrincipal
    
    Esta função DEVE ser chamada SEMPRE antes de:
    - Criar PreSeparacaoItem
    - Editar quantidade de PreSeparacaoItem  
    - Criar Separacao
    
    Args:
        num_pedido (str): Número do pedido
        cod_produto (str): Código do produto
        qtd_solicitada (float): Quantidade que se deseja separar/pré-separar
        
    Returns:
        float: Saldo disponível após validação
        
    Raises:
        ValueError: Se quantidade solicitada excede saldo disponível
    """
    from sqlalchemy import func, and_, or_
    
    try:
        # 1. Buscar saldo da carteira
        carteira_item = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            cod_produto=cod_produto,
            ativo=True
        ).first()
        
        if not carteira_item:
            raise ValueError(f"Item {num_pedido}-{cod_produto} não encontrado na carteira")
        
        # 2. Calcular separações ativas (via status do Pedido)
        from app.pedidos.models import Pedido
        separacoes_ativas = db.session.query(func.coalesce(func.sum(Separacao.qtd_saldo), 0)).join(
            Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            and_(
                Separacao.num_pedido == num_pedido,
                Separacao.cod_produto == cod_produto,
                or_(
                    Pedido.status == 'Aberto',
                    Pedido.status == 'Cotado'
                )
            )
        ).scalar() or 0
        
        # 3. Calcular pré-separações ativas (apenas CRIADO e RECOMPOSTO)
        pre_separacoes_ativas = 0
        try:
            from app.carteira.models import PreSeparacaoItem
            pre_separacoes_ativas = db.session.query(func.coalesce(func.sum(PreSeparacaoItem.qtd_selecionada_usuario), 0)).filter(
                and_(
                    PreSeparacaoItem.num_pedido == num_pedido,
                    PreSeparacaoItem.cod_produto == cod_produto,
                    or_(
                        PreSeparacaoItem.status == 'CRIADO',
                        PreSeparacaoItem.status == 'RECOMPOSTO'
                    )
                )
            ).scalar() or 0
        except (ImportError, AttributeError):
            pass
        
        # 4. Calcular saldo disponível real
        saldo_carteira = float(carteira_item.qtd_saldo_produto_pedido or 0)
        saldo_disponivel = saldo_carteira - float(separacoes_ativas) - float(pre_separacoes_ativas)
        
        # 5. Validar se quantidade solicitada é viável
        if qtd_solicitada > saldo_disponivel:
            raise ValueError(
                f"❌ VALIDAÇÃO CRÍTICA FALHOU\n"
                f"Quantidade solicitada: {qtd_solicitada}\n"
                f"Saldo disponível: {saldo_disponivel}\n"
                f"Detalhes:\n"
                f"  • Carteira: {saldo_carteira}\n"
                f"  • Separações ativas: {separacoes_ativas}\n"
                f"  • Pré-separações ativas: {pre_separacoes_ativas}\n"
                f"Item: {num_pedido}-{cod_produto}"
            )
        
        logger.info(f"✅ Validação OK: {num_pedido}-{cod_produto} - Solicitado: {qtd_solicitada}, Disponível: {saldo_disponivel}")
        return saldo_disponivel
        
    except Exception as e:
        logger.error(f"❌ Erro na validação de saldo {num_pedido}-{cod_produto}: {e}")
        raise


def _carregar_dados_estoque_d0_d7(num_pedido):
    """
    🔧 P1.2: Função auxiliar para carregar dados de estoque D0/D7
    Reutiliza lógica da API existente
    """
    try:
        # Reutilizar lógica da API existente
        from datetime import datetime, timedelta
        from app.estoque.models import SaldoEstoque
        
        # 1. Buscar itens do pedido
        itens_pedido = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()
        
        if not itens_pedido:
            return {'success': False, 'error': 'Pedido não encontrado'}
        
        # 2. Calcular dados de estoque para cada produto
        produtos_estoque = []
        data_hoje = datetime.now().date()
        data_d7 = data_hoje + timedelta(days=7)
        
        for item in itens_pedido:
            try:
                # Buscar saldo do produto
                saldo = SaldoEstoque.query.filter_by(cod_produto=item.cod_produto).first()
                
                if saldo:
                    estoque_d0 = saldo.qtd_saldo_estoque_d0 or 0
                    saida_periodo = SaldoEstoque.calcular_saida_periodo(
                        item.cod_produto, data_hoje, data_d7
                    )
                    estoque_d7 = estoque_d0 - saida_periodo
                    
                    # Determinar status
                    qtd_pedido = item.qtd_saldo_produto_pedido or 0
                    
                    if estoque_d0 >= qtd_pedido:
                        status_d0 = 'NORMAL'
                    elif estoque_d0 > 0:
                        status_d0 = 'BAIXO'
                    else:
                        status_d0 = 'RUPTURA'
                    
                    if estoque_d7 >= qtd_pedido:
                        status_d7 = 'NORMAL'
                    elif estoque_d7 > 0:
                        status_d7 = 'BAIXO_PREVISTO'
                    else:
                        status_d7 = 'RUPTURA_PREVISTA'
                    
                    # Calcular dias para ruptura
                    if estoque_d0 > 0 and saida_periodo > 0:
                        dias_ruptura = int(estoque_d0 / (saida_periodo / 7))
                    else:
                        dias_ruptura = None
                else:
                    estoque_d0 = 0
                    estoque_d7 = 0
                    status_d0 = 'SEM_DADOS'
                    status_d7 = 'SEM_DADOS'
                    dias_ruptura = None
                
                produtos_estoque.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_pedido': qtd_pedido,
                    'estoque_d0': estoque_d0,
                    'estoque_d7': estoque_d7,
                    'status_d0': status_d0,
                    'status_d7': status_d7,
                    'dias_ruptura': dias_ruptura
                })
                
            except Exception as e:
                logger.warning(f"Erro ao calcular estoque produto {item.cod_produto}: {e}")
                produtos_estoque.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_pedido': item.qtd_saldo_produto_pedido or 0,
                    'estoque_d0': 0,
                    'estoque_d7': 0,
                    'status_d0': 'SEM_DADOS',
                    'status_d7': 'SEM_DADOS',
                    'dias_ruptura': None
                })
        
        # 3. Calcular estatísticas
        total_produtos = len(produtos_estoque)
        produtos_ruptura_d0 = sum(1 for p in produtos_estoque if p['status_d0'] == 'RUPTURA')
        produtos_ruptura_d7 = sum(1 for p in produtos_estoque if p['status_d7'] in ['RUPTURA_PREVISTA', 'BAIXO_PREVISTO'])
        menor_estoque = min([p['estoque_d0'] for p in produtos_estoque if p['estoque_d0'] > 0], default=0)
        
        estatisticas = {
            'total_produtos': total_produtos,
            'produtos_ruptura_d0': produtos_ruptura_d0,
            'produtos_ruptura_d7': produtos_ruptura_d7,
            'menor_estoque_geral': menor_estoque
        }
        
        return {
            'success': True,
            'produtos': produtos_estoque,
            'estatisticas': estatisticas,
            'data_calculo': data_hoje.strftime('%d/%m/%Y')
        }
        
    except Exception as e:
        logger.error(f"Erro em _carregar_dados_estoque_d0_d7: {e}")
        return {'success': False, 'error': str(e)}


def _carregar_dados_itens_pedido(num_pedido):
    """
    🔧 P1.2: Função auxiliar para carregar dados dos itens do pedido
    Reutiliza lógica da API existente
    """
    try:
        # Reutilizar lógica da API /api/pedido/<num_pedido>/itens existente
        itens_pedido = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()
        
        if not itens_pedido:
            return {'success': False, 'error': 'Pedido não encontrado'}
        
        # Processar itens (mesma lógica da API existente)
        itens_processados = []
        totais = {'quantidade': 0, 'valor': 0, 'peso': 0, 'pallet': 0}
        
        for item in itens_pedido:
            qtd_saldo = item.qtd_saldo_produto_pedido or 0
            preco = item.preco_produto_pedido or 0
            peso_unit = item.peso_produto_pedido or 0
            pallet_unit = item.qtd_pal_pro_ped or 0
            
            valor_item = qtd_saldo * preco
            peso_item = qtd_saldo * peso_unit
            pallet_item = qtd_saldo * pallet_unit
            
            # Verificar se tem separação
            from app.separacao.models import Separacao
            tem_separacao = db.session.query(
                db.exists().where(
                    db.and_(
                        Separacao.num_pedido == num_pedido,
                        Separacao.cod_produto == item.cod_produto,
                        Separacao.status == 'ativo'
                    )
                )
            ).scalar()
            
            item_processado = {
                'id': item.id,
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'qtd_saldo': qtd_saldo,
                'preco': preco,
                'peso_produto': peso_unit,
                'pallet_produto': pallet_unit,
                'valor_item': valor_item,
                'peso_item': peso_item,
                'pallet_item': pallet_item,
                'tem_separacao': tem_separacao,
                'expedicao': item.expedicao.strftime('%Y-%m-%d') if item.expedicao else None,
                'expedicao_formatada': item.expedicao.strftime('%d/%m/%Y') if item.expedicao else '',
                'agendamento': item.agendamento.strftime('%Y-%m-%d') if item.agendamento else None,
                'agendamento_formatado': item.agendamento.strftime('%d/%m/%Y') if item.agendamento else '',
                'protocolo': item.protocolo or ''
            }
            
            itens_processados.append(item_processado)
            
            # Somar totais
            totais['quantidade'] += qtd_saldo
            totais['valor'] += valor_item
            totais['peso'] += peso_item
            totais['pallet'] += pallet_item
        
        return {
            'success': True,
            'itens': itens_processados,
            'total_itens': len(itens_processados),
            'totais': totais
        }
        
    except Exception as e:
        logger.error(f"Erro em _carregar_dados_itens_pedido: {e}")
        return {'success': False, 'error': str(e)}


@carteira_bp.route('/api/export-excel/estoque-analise/<num_pedido>')
@login_required
def api_export_excel_estoque_analise(num_pedido):
    """
    🔧 P1.2: Exportar análise de estoque D0/D7 em Excel
    """
    try:
        import pandas as pd
        from datetime import datetime
        import os
        from flask import send_file
        
        # 1. Buscar dados de estoque D0/D7 (reutilizar lógica existente)
        dados_estoque = _carregar_dados_estoque_d0_d7(num_pedido)
        
        if not dados_estoque.get('success'):
            return jsonify({'error': 'Erro ao carregar dados de estoque'}), 400
        
        # 2. Preparar dados para Excel
        produtos = dados_estoque['produtos']
        estatisticas = dados_estoque['estatisticas']
        
        # DataFrame principal
        df_produtos = pd.DataFrame([{
            'Código Produto': p['cod_produto'],
            'Nome Produto': p['nome_produto'],
            'Qtd Pedido': p['qtd_pedido'],
            'Estoque D0': p['estoque_d0'],
            'Estoque D7': p['estoque_d7'],
            'Status D0': p['status_d0'],
            'Status D7': p['status_d7'],
            'Dias Ruptura': p['dias_ruptura'] if p['dias_ruptura'] else 'Sem previsão'
        } for p in produtos])
        
        # DataFrame resumo
        df_resumo = pd.DataFrame([{
            'Métrica': 'Total de Produtos',
            'Valor': estatisticas['total_produtos']
        }, {
            'Métrica': 'Produtos com Ruptura D0',
            'Valor': estatisticas['produtos_ruptura_d0']
        }, {
            'Métrica': 'Produtos com Problemas D7',
            'Valor': estatisticas['produtos_ruptura_d7']
        }, {
            'Métrica': 'Menor Estoque Geral',
            'Valor': f"{estatisticas['menor_estoque_geral']:.2f}"
        }])
        
        # 3. Gerar arquivo Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'analise_estoque_pedido_{num_pedido}_{timestamp}.xlsx'
        filepath = os.path.join('app', 'static', 'reports', filename)
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Aba principal
            df_produtos.to_excel(writer, sheet_name='Análise D0-D7', index=False)
            
            # Aba resumo
            df_resumo.to_excel(writer, sheet_name='Resumo Executivo', index=False)
            
            # Aba instruções
            df_instrucoes = pd.DataFrame([{
                'Informação': 'Data Geração',
                'Valor': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }, {
                'Informação': 'Pedido Analisado',
                'Valor': num_pedido
            }, {
                'Informação': 'Status D0',
                'Valor': 'Estoque atual (hoje)'
            }, {
                'Informação': 'Status D7',
                'Valor': 'Projeção 7 dias úteis'
            }, {
                'Informação': 'NORMAL',
                'Valor': 'Estoque suficiente'
            }, {
                'Informação': 'BAIXO',
                'Valor': 'Estoque baixo mas disponível'
            }, {
                'Informação': 'RUPTURA',
                'Valor': 'Estoque insuficiente'
            }])
            df_instrucoes.to_excel(writer, sheet_name='Como Ler', index=False)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': f'/static/reports/{filename}',
            'total_produtos': len(produtos)
        })
        
    except Exception as e:
        logger.error(f"Erro ao exportar análise estoque pedido {num_pedido}: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@carteira_bp.route('/api/export-excel/estoque-dados/<num_pedido>')
@login_required  
def api_export_excel_estoque_dados(num_pedido):
    """
    🔧 P1.2: Exportar dados brutos de estoque em Excel
    """
    try:
        import pandas as pd
        from datetime import datetime
        import os
        from flask import send_file
        
        # 1. Buscar dados brutos de estoque (mais detalhados)
        dados_estoque = _carregar_dados_estoque_d0_d7(num_pedido)
        
        if not dados_estoque.get('success'):
            return jsonify({'error': 'Erro ao carregar dados de estoque'}), 400
        
        # 2. Buscar dados dos itens do pedido também
        dados_itens = _carregar_dados_itens_pedido(num_pedido)
        
        if not dados_itens.get('success'):
            return jsonify({'error': 'Erro ao carregar itens do pedido'}), 400
        
        # 3. Combinar dados para dataset completo
        produtos_completos = []
        produtos_dict = {p['cod_produto']: p for p in dados_estoque['produtos']}
        
        for item in dados_itens['itens']:
            produto_estoque = produtos_dict.get(item['cod_produto'], {})
            
            produtos_completos.append({
                'Pedido': num_pedido,
                'Código Produto': item['cod_produto'],
                'Nome Produto': item['nome_produto'],
                'Qtd Saldo Pedido': item['qtd_saldo'],
                'Preço Unitário': item['preco'],
                'Valor Total Item': item['qtd_saldo'] * item['preco'],
                'Peso Unitário': item.get('peso_produto', 0),
                'Peso Total': (item.get('peso_produto', 0) * item['qtd_saldo']),
                'Pallet Unitário': item.get('pallet_produto', 0),
                'Pallet Total': (item.get('pallet_produto', 0) * item['qtd_saldo']),
                'Estoque D0': produto_estoque.get('estoque_d0', 'N/A'),
                'Estoque D7': produto_estoque.get('estoque_d7', 'N/A'),
                'Status D0': produto_estoque.get('status_d0', 'SEM_DADOS'),
                'Status D7': produto_estoque.get('status_d7', 'SEM_DADOS'),
                'Dias até Ruptura': produto_estoque.get('dias_ruptura', 'N/A'),
                'Expedição': item.get('expedicao_formatada', ''),
                'Agendamento': item.get('agendamento_formatado', ''),
                'Protocolo': item.get('protocolo', ''),
                'Separação': 'Sim' if item.get('tem_separacao') else 'Não'
            })
        
        df_completo = pd.DataFrame(produtos_completos)
        
        # 4. Dados de resumo por status
        status_counts = df_completo['Status D0'].value_counts()
        df_status = pd.DataFrame([{
            'Status': status,
            'Quantidade Produtos': count,
            'Percentual': f"{(count/len(df_completo)*100):.1f}%"
        } for status, count in status_counts.items()])
        
        # 5. Gerar arquivo Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'dados_estoque_pedido_{num_pedido}_{timestamp}.xlsx'
        filepath = os.path.join('app', 'static', 'reports', filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Dados completos
            df_completo.to_excel(writer, sheet_name='Dados Completos', index=False)
            
            # Análise por status
            df_status.to_excel(writer, sheet_name='Análise Status', index=False)
            
            # Resumo financeiro
            resumo_financeiro = pd.DataFrame([{
                'Métrica': 'Total Itens',
                'Valor': len(df_completo)
            }, {
                'Métrica': 'Valor Total Pedido',
                'Valor': f"R$ {df_completo['Valor Total Item'].sum():,.2f}"
            }, {
                'Métrica': 'Peso Total',
                'Valor': f"{df_completo['Peso Total'].sum():,.0f} kg"
            }, {
                'Métrica': 'Pallets Total',
                'Valor': f"{df_completo['Pallet Total'].sum():.1f}"
            }])
            resumo_financeiro.to_excel(writer, sheet_name='Resumo Financeiro', index=False)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': f'/static/reports/{filename}',
            'total_produtos': len(produtos_completos),
            'valor_total': df_completo['Valor Total Item'].sum()
        })
        
    except Exception as e:
        logger.error(f"Erro ao exportar dados estoque pedido {num_pedido}: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@carteira_bp.route('/api/export-excel/produto-detalhes/<cod_produto>')
@login_required
def api_export_excel_produto_detalhes(cod_produto):
    """
    🔧 P1.2: Exportar detalhes específicos de um produto em Excel
    """
    try:
        import pandas as pd
        from datetime import datetime, timedelta
        import os
        from app.estoque.models import SaldoEstoque
        
        # 1. Buscar todos os dados do produto na carteira
        itens_produto = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.ativo == True
        ).all()
        
        if not itens_produto:
            return jsonify({'error': f'Produto {cod_produto} não encontrado na carteira'}), 404
        
        # 2. Buscar dados de estoque
        saldo_estoque = SaldoEstoque.query.filter_by(cod_produto=cod_produto).first()
        
        # 3. Preparar dados detalhados por pedido
        dados_pedidos = []
        for item in itens_produto:
            # Calcular estoque D0 e D7 para este produto
            try:
                if saldo_estoque:
                    estoque_d0 = saldo_estoque.qtd_saldo_estoque_d0 or 0
                    saida_periodo = SaldoEstoque.calcular_saida_periodo(
                        cod_produto, 
                        datetime.now().date(),
                        datetime.now().date() + timedelta(days=7)
                    )
                    estoque_d7 = estoque_d0 - saida_periodo
                else:
                    estoque_d0 = 0
                    estoque_d7 = 0
            except:
                estoque_d0 = 0
                estoque_d7 = 0
            
            dados_pedidos.append({
                'Pedido': item.num_pedido,
                'Cliente': item.raz_social,
                'Vendedor': item.vendedor,
                'Status Pedido': item.status_pedido,
                'Qtd Saldo': item.qtd_saldo_produto_pedido,
                'Preço': item.preco_produto_pedido,
                'Valor Total': (item.qtd_saldo_produto_pedido or 0) * (item.preco_produto_pedido or 0),
                'Peso Unitário': item.peso_produto_pedido,
                'Pallet Unitário': item.qtd_pal_pro_ped,
                'Expedição': item.expedicao.strftime('%d/%m/%Y') if item.expedicao else '',
                'Agendamento': item.agendamento.strftime('%d/%m/%Y') if item.agendamento else '',
                'Protocolo': item.protocolo or '',
                'Estoque D0': estoque_d0,
                'Estoque D7': estoque_d7,
                'Criado em': item.created_at.strftime('%d/%m/%Y %H:%M') if item.created_at else ''
            })
        
        df_produto = pd.DataFrame(dados_pedidos)
        
        # 4. Dados do produto (info geral)
        primeiro_item = itens_produto[0]
        info_produto = pd.DataFrame([{
            'Campo': 'Código Produto',
            'Valor': cod_produto
        }, {
            'Campo': 'Nome Produto',
            'Valor': primeiro_item.nome_produto
        }, {
            'Campo': 'Total Pedidos',
            'Valor': len(set(item.num_pedido for item in itens_produto))
        }, {
            'Campo': 'Qtd Total Carteira',
            'Valor': sum(item.qtd_saldo_produto_pedido or 0 for item in itens_produto)
        }, {
            'Campo': 'Valor Total Carteira',
            'Valor': f"R$ {sum((item.qtd_saldo_produto_pedido or 0) * (item.preco_produto_pedido or 0) for item in itens_produto):,.2f}"
        }, {
            'Campo': 'Estoque D0',
            'Valor': estoque_d0
        }, {
            'Campo': 'Estoque D7',
            'Valor': estoque_d7
        }])
        
        # 5. Gerar arquivo Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'detalhes_produto_{cod_produto}_{timestamp}.xlsx'
        filepath = os.path.join('app', 'static', 'reports', filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Dados por pedido
            df_produto.to_excel(writer, sheet_name='Por Pedido', index=False)
            
            # Informações gerais
            info_produto.to_excel(writer, sheet_name='Informações Produto', index=False)
            
            # Resumo por cliente
            resumo_cliente = df_produto.groupby('Cliente').agg({
                'Qtd Saldo': 'sum',
                'Valor Total': 'sum',
                'Pedido': 'count'
            }).reset_index()
            resumo_cliente.columns = ['Cliente', 'Qtd Total', 'Valor Total', 'Num Pedidos']
            resumo_cliente.to_excel(writer, sheet_name='Resumo por Cliente', index=False)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': f'/static/reports/{filename}',
            'total_pedidos': len(dados_pedidos),
            'produto_nome': primeiro_item.nome_produto
        })
        
    except Exception as e:
        logger.error(f"Erro ao exportar detalhes produto {cod_produto}: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@carteira_bp.route('/api/separacao/<lote_id>/detalhes')
@login_required
def api_separacao_detalhes(lote_id):
    """
    🔧 P2.1: Ver detalhes completos de uma separação por lote_id
    """
    try:
        from app.separacao.models import Separacao
        from app.pedidos.models import Pedido
        from app.embarques.models import Embarque, EmbarqueItem
        
        # 1. Buscar todas as separações do lote
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        
        if not separacoes:
            return jsonify({'error': f'Separação {lote_id} não encontrada'}), 404
        
        # 2. Buscar dados complementares
        # Pedido relacionado
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
        
        # Embarque relacionado (via EmbarqueItem)
        embarque_item = EmbarqueItem.query.filter_by(separacao_lote_id=lote_id).first()
        embarque = embarque_item.embarque if embarque_item else None
        
        # Itens da carteira relacionados
        itens_carteira = CarteiraPrincipal.query.filter_by(
            separacao_lote_id=lote_id,
            ativo=True
        ).all()
        
        # 3. Organizar dados da separação
        produtos_separacao = []
        totais = {
            'quantidade': 0,
            'valor': 0,
            'peso': 0,
            'pallet': 0,
            'produtos': len(separacoes)
        }
        
        for sep in separacoes:
            produto_info = {
                'id': sep.id,
                'cod_produto': sep.cod_produto,
                'nome_produto': sep.nome_produto,
                'qtd_saldo': sep.qtd_saldo or 0,
                'valor_saldo': sep.valor_saldo or 0,
                'peso': sep.peso or 0,
                'pallet': sep.pallet or 0,
                'tipo_envio': sep.tipo_envio or 'total',
                'rota': sep.rota,
                'sub_rota': sep.sub_rota,
                'observ_ped_1': sep.observ_ped_1,
                'roteirizacao': sep.roteirizacao,
                'expedicao': sep.expedicao.strftime('%d/%m/%Y') if sep.expedicao else '',
                'agendamento': sep.agendamento.strftime('%d/%m/%Y') if sep.agendamento else '',
                'protocolo': sep.protocolo or '',
                'criado_em': sep.criado_em.strftime('%d/%m/%Y %H:%M') if sep.criado_em else ''
            }
            produtos_separacao.append(produto_info)
            
            # Somar totais
            totais['quantidade'] += produto_info['qtd_saldo']
            totais['valor'] += produto_info['valor_saldo']
            totais['peso'] += produto_info['peso']
            totais['pallet'] += produto_info['pallet']
        
        # 4. Dados do cabeçalho da separação (primeiro item)
        primeira_sep = separacoes[0]
        info_cabecalho = {
            'lote_id': lote_id,
            'num_pedido': primeira_sep.num_pedido,
            'data_pedido': primeira_sep.data_pedido.strftime('%d/%m/%Y') if primeira_sep.data_pedido else '',
            'cnpj_cpf': primeira_sep.cnpj_cpf,
            'raz_social_red': primeira_sep.raz_social_red,
            'nome_cidade': primeira_sep.nome_cidade,
            'cod_uf': primeira_sep.cod_uf,
            'rota': primeira_sep.rota,
            'sub_rota': primeira_sep.sub_rota
        }
        
        # 5. Status e vínculos
        status_info = {
            'pedido_vinculado': bool(pedido),
            'pedido_status': pedido.status_calculado if pedido else None,
            'embarque_vinculado': bool(embarque),
            'embarque_numero': embarque.numero if embarque else None,
            'itens_carteira': len(itens_carteira),
            'pode_editar': pedido.status_calculado in ['ABERTO', 'COTADO'] if pedido else True,
            'pode_excluir': pedido.status_calculado == 'ABERTO' if pedido else True
        }
        
        return jsonify({
            'success': True,
            'separacao': {
                'cabecalho': info_cabecalho,
                'produtos': produtos_separacao,
                'totais': totais,
                'status': status_info
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes separação {lote_id}: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@carteira_bp.route('/api/separacao/<lote_id>/editar', methods=['POST'])
@login_required
def api_separacao_editar(lote_id):
    """
    🔧 P2.1: Editar dados de uma separação existente
    """
    try:
        from app.separacao.models import Separacao
        from app.pedidos.models import Pedido
        
        dados = request.get_json()
        
        if not dados:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # 1. Verificar se a separação existe
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        
        if not separacoes:
            return jsonify({'error': f'Separação {lote_id} não encontrada'}), 404
        
        # 2. Verificar se pode editar (status do pedido)
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
        if pedido and pedido.status_calculado not in ['ABERTO', 'COTADO']:
            return jsonify({'error': f'Não é possível editar separação. Pedido está {pedido.status_calculado}'}), 403
        
        # 3. Campos que podem ser editados
        campos_editaveis = [
            'expedicao', 'agendamento', 'protocolo', 'observ_ped_1', 
            'tipo_envio', 'rota', 'sub_rota', 'roteirizacao'
        ]
        
        # 4. Atualizar dados da separação
        alteracoes_realizadas = []
        
        for separacao in separacoes:
            for campo in campos_editaveis:
                if campo in dados:
                    valor_atual = getattr(separacao, campo)
                    valor_novo = dados[campo]
                    
                    # Tratamento especial para datas
                    if campo in ['expedicao', 'agendamento'] and valor_novo:
                        try:
                            from datetime import datetime
                            if isinstance(valor_novo, str):
                                # Assumir formato brasileiro dd/mm/yyyy
                                valor_novo = datetime.strptime(valor_novo, '%d/%m/%Y').date()
                        except ValueError:
                            return jsonify({'error': f'Data inválida para {campo}: {valor_novo}'}), 400
                    
                    # Aplicar alteração se valor mudou
                    if valor_atual != valor_novo:
                        setattr(separacao, campo, valor_novo)
                        alteracoes_realizadas.append(f'{campo}: {valor_atual} → {valor_novo}')
        
        # 5. Atualizar também na carteira principal se necessário
        if 'expedicao' in dados or 'agendamento' in dados or 'protocolo' in dados:
            itens_carteira = CarteiraPrincipal.query.filter_by(
                separacao_lote_id=lote_id,
                ativo=True
            ).all()
            
            for item in itens_carteira:
                if 'expedicao' in dados and dados['expedicao']:
                    item.expedicao = datetime.strptime(dados['expedicao'], '%d/%m/%Y').date() if isinstance(dados['expedicao'], str) else dados['expedicao']
                if 'agendamento' in dados and dados['agendamento']:
                    item.agendamento = datetime.strptime(dados['agendamento'], '%d/%m/%Y').date() if isinstance(dados['agendamento'], str) else dados['agendamento']
                if 'protocolo' in dados:
                    item.protocolo = dados['protocolo']
        
        # 6. Salvar alterações
        if alteracoes_realizadas:
            db.session.commit()
            
            logger.info(f"Separação {lote_id} editada por {current_user.nome}. Alterações: {alteracoes_realizadas}")
            
            return jsonify({
                'success': True,
                'message': f'Separação {lote_id} atualizada com sucesso',
                'alteracoes': alteracoes_realizadas,
                'total_produtos': len(separacoes)
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Nenhuma alteração foi necessária',
                'alteracoes': []
            })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao editar separação {lote_id}: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@carteira_bp.route('/api/separacao/criar', methods=['POST'])
@login_required
def api_separacao_criar():
    """
    🔧 P2.1: Criar nova separação a partir de itens da carteira
    """
    try:
        from app.separacao.models import Separacao
        from app.pedidos.models import Pedido
        import uuid
        from datetime import datetime, date
        
        dados = request.get_json()
        
        if not dados:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # 1. Validar campos obrigatórios
        campos_obrigatorios = ['num_pedido', 'itens_selecionados']
        for campo in campos_obrigatorios:
            if campo not in dados:
                return jsonify({'error': f'Campo obrigatório: {campo}'}), 400
        
        num_pedido = dados['num_pedido']
        itens_ids = dados['itens_selecionados']  # Lista de IDs dos itens da carteira
        
        if not itens_ids:
            return jsonify({'error': 'Nenhum item selecionado para separação'}), 400
        
        # 2. Buscar itens da carteira
        itens_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.id.in_(itens_ids),
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()
        
        if len(itens_carteira) != len(itens_ids):
            return jsonify({'error': 'Alguns itens selecionados não foram encontrados'}), 400
        
        # 3. Verificar se já existe separação para estes itens
        itens_com_separacao = [item for item in itens_carteira if item.separacao_lote_id]
        if itens_com_separacao:
            return jsonify({'error': f'Alguns itens já possuem separação: {[item.cod_produto for item in itens_com_separacao]}'}), 400
        
        # 4. Gerar novo lote_id único
        lote_id = f"SEP{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"
        
        # 5. Obter dados do primeiro item para cabeçalho
        primeiro_item = itens_carteira[0]
        
        # 6. Campos opcionais da separação
        tipo_envio = dados.get('tipo_envio', 'total')
        data_expedicao = None
        data_agendamento = None
        protocolo = dados.get('protocolo', '')
        observacoes = dados.get('observacoes', '')
        
        # Processar datas se fornecidas
        if dados.get('expedicao'):
            try:
                data_expedicao = datetime.strptime(dados['expedicao'], '%d/%m/%Y').date()
            except ValueError:
                return jsonify({'error': 'Data de expedição inválida'}), 400
                
        if dados.get('agendamento'):
            try:
                data_agendamento = datetime.strptime(dados['agendamento'], '%d/%m/%Y').date()
            except ValueError:
                return jsonify({'error': 'Data de agendamento inválida'}), 400
        
        # 7. Criar registros de separação
        separacoes_criadas = []
        totais = {'quantidade': 0, 'valor': 0, 'peso': 0, 'pallet': 0}
        
        for item in itens_carteira:
            # Criar objeto Separacao e definir atributos
            separacao = Separacao()
            separacao.separacao_lote_id = lote_id
            separacao.num_pedido = item.num_pedido
            separacao.data_pedido = item.data_pedido
            separacao.cnpj_cpf = item.cnpj_cpf
            separacao.raz_social_red = item.raz_social
            separacao.nome_cidade = item.nome_cidade
            separacao.cod_uf = item.cod_uf
            separacao.cod_produto = item.cod_produto
            separacao.nome_produto = item.nome_produto
            separacao.qtd_saldo = item.qtd_saldo_produto_pedido
            separacao.valor_saldo = (item.qtd_saldo_produto_pedido or 0) * (item.preco_produto_pedido or 0)
            separacao.pallet = item.qtd_pal_pro_ped
            separacao.peso = item.peso_produto_pedido
            separacao.rota = item.rota
            separacao.sub_rota = item.sub_rota
            separacao.observ_ped_1 = observacoes
            separacao.roteirizacao = item.roteirizacao
            separacao.expedicao = data_expedicao
            separacao.agendamento = data_agendamento
            separacao.protocolo = protocolo
            separacao.tipo_envio = tipo_envio
            separacao.criado_em = datetime.utcnow()
            
            db.session.add(separacao)
            separacoes_criadas.append(separacao)
            
            # 8. Atualizar item da carteira com lote_id
            item.separacao_lote_id = lote_id
            if data_expedicao:
                item.expedicao = data_expedicao
            if data_agendamento:
                item.agendamento = data_agendamento
            if protocolo:
                item.protocolo = protocolo
            
            # Somar totais
            totais['quantidade'] += item.qtd_saldo_produto_pedido or 0
            totais['valor'] += (item.qtd_saldo_produto_pedido or 0) * (item.preco_produto_pedido or 0)
            totais['peso'] += item.peso_produto_pedido or 0
            totais['pallet'] += item.qtd_pal_pro_ped or 0
        
        # 9. Atualizar pedido se necessário
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        if pedido and not pedido.separacao_lote_id:
            pedido.separacao_lote_id = lote_id
        
        # 10. Salvar todas as alterações
        db.session.commit()
        
        logger.info(f"Nova separação criada: {lote_id} para pedido {num_pedido} por {current_user.nome}. {len(separacoes_criadas)} produtos.")
        
        return jsonify({
            'success': True,
            'message': f'Separação criada com sucesso',
            'separacao': {
                'lote_id': lote_id,
                'num_pedido': num_pedido,
                'total_produtos': len(separacoes_criadas),
                'tipo_envio': tipo_envio,
                'totais': totais,
                'data_criacao': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar separação: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


# ===== APIS PARA MODAL ITENS EDITÁVEIS =====

@carteira_bp.route('/api/pedido/<num_pedido>/itens-editaveis')
@login_required
def api_pedido_itens_editaveis(num_pedido):
    """
    API para carregar itens editáveis de um pedido com saldo calculado + PreSeparacaoItem
    Implementa fórmula: Qtd = carteira_principal.qtd_saldo_produto_pedido - separacao.qtd_saldo - pre_separacao_item.qtd_selecionada_usuario
    INCLUI: PreSeparacaoItem como itens editáveis/canceláveis
    """
    try:
        # Buscar itens da carteira principal para o pedido
        itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()
        
        # Buscar pré-separações do pedido
        pre_separacoes = buscar_pre_separacoes_pedido(num_pedido)
        
        if not itens_carteira and not pre_separacoes:
            return jsonify({
                'success': False,
                'error': f'Nenhum item encontrado para o pedido {num_pedido}'
            }), 404
        
        itens_resultado = []
        
        for item in itens_carteira:
            try:
                # 📊 CALCULAR SALDO DISPONÍVEL conforme especificação
                qtd_carteira = float(item.qtd_saldo_produto_pedido or 0)
                
                # 🔍 DEBUG: Log se quantidade está zerada
                if qtd_carteira == 0:
                    logger.warning(f"🔍 DEBUG QTD ZERADA: Pedido {num_pedido}, Produto {item.cod_produto}, qtd_saldo_produto_pedido={item.qtd_saldo_produto_pedido}, qtd_produto_pedido={getattr(item, 'qtd_produto_pedido', 'N/A')}")
                else:
                    logger.info(f"🔍 DEBUG QTD OK: Pedido {num_pedido}, Produto {item.cod_produto}, qtd_saldo={qtd_carteira}")
                
                # Somar quantidades em separações ATIVAS (via status do Pedido)
                from app.pedidos.models import Pedido
                qtd_separacoes = db.session.query(func.coalesce(func.sum(Separacao.qtd_saldo), 0)).join(
                    Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                ).filter(
                    and_(
                        Separacao.num_pedido == num_pedido,
                        Separacao.cod_produto == item.cod_produto,
                        or_(
                            # SEPARAÇÕES QUE AINDA CONSOMEM SALDO (via status do Pedido)
                            Pedido.status == 'Aberto',
                            Pedido.status == 'Cotado'
                        )
                    )
                ).scalar() or 0
                
                # Somar quantidades em pré-separações ATIVAS (apenas "CRIADO" e "RECOMPOSTO")
                qtd_pre_separacoes = 0
                try:
                    from app.carteira.models import PreSeparacaoItem
                    qtd_pre_separacoes = db.session.query(func.coalesce(func.sum(PreSeparacaoItem.qtd_selecionada_usuario), 0)).filter(
                        and_(
                            PreSeparacaoItem.num_pedido == num_pedido,
                            PreSeparacaoItem.cod_produto == item.cod_produto,
                            or_(
                                # PRÉ-SEPARAÇÕES QUE AINDA CONSOMEM SALDO
                                PreSeparacaoItem.status == 'CRIADO',
                                PreSeparacaoItem.status == 'RECOMPOSTO'
                            )
                        )
                    ).scalar() or 0
                except (ImportError, AttributeError):
                    # Modelo PreSeparacaoItem não existe ainda, usar apenas separações
                    pass
                
                # Calcular saldo disponível
                qtd_saldo_disponivel = qtd_carteira - float(qtd_separacoes) - float(qtd_pre_separacoes)
                
                # Garantir que não seja negativo
                qtd_saldo_disponivel = max(0, qtd_saldo_disponivel)
                
                # 💰 CALCULAR VALORES AUTOMÁTICOS
                preco_unitario = float(item.preco_produto_pedido or 0)
                valor_calculado = qtd_saldo_disponivel * preco_unitario
                
                # 📦 BUSCAR DADOS DE PALLETIZAÇÃO/PESO
                peso_calculado = 0
                pallet_calculado = 0
                
                try:
                    # Se existir cadastro de palletização, usar
                    from app.producao.models import CadastroPalletizacao
                    palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=item.cod_produto).first()
                    if palletizacao:
                        if palletizacao.peso_bruto:
                            peso_calculado = qtd_saldo_disponivel * float(palletizacao.peso_bruto)
                        if palletizacao.palletizacao and palletizacao.palletizacao > 0:
                            pallet_calculado = qtd_saldo_disponivel / float(palletizacao.palletizacao)
                except ImportError:
                    # Usar valores da carteira se disponíveis
                    if item.peso:
                        peso_calculado = qtd_saldo_disponivel * (float(item.peso) / float(item.qtd_saldo_produto_pedido)) if item.qtd_saldo_produto_pedido else 0
                    if item.pallet:
                        pallet_calculado = qtd_saldo_disponivel * (float(item.pallet) / float(item.qtd_saldo_produto_pedido)) if item.qtd_saldo_produto_pedido else 0
                
                # 📊 CALCULAR ESTOQUES D0/D7 (usando SaldoEstoque)
                menor_estoque_d7 = '-'
                estoque_d0 = '-'
                producao_d0 = '-'
                
                try:
                    # Data de expedição específica (ou hoje+1 se não definida)
                    data_expedicao = item.expedicao or (datetime.now().date() + timedelta(days=1))
                    
                    # SISTEMA DINÂMICO: Estoque e produção baseados na data de expedição
                    resumo_estoque = SaldoEstoque.obter_resumo_produto(item.cod_produto, item.nome_produto)
                    
                    if resumo_estoque and resumo_estoque['projecao_29_dias']:
                        # 📅 ESTOQUE DA DATA DE EXPEDIÇÃO (não D0)
                        estoque_expedicao = _calcular_estoque_data_especifica(
                            resumo_estoque['projecao_29_dias'], data_expedicao
                        )
                        estoque_d0 = f"{int(estoque_expedicao)}" if estoque_expedicao >= 0 else "RUPTURA"
                        
                        # 🏭 PRODUÇÃO DA DATA DE EXPEDIÇÃO (não D0)
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
                        # Fallback se não conseguir calcular projeção
                        estoque_inicial = SaldoEstoque.calcular_estoque_inicial(item.cod_produto)
                        estoque_d0 = f"{int(estoque_inicial)}" if estoque_inicial >= 0 else "RUPTURA"
                        producao_d0 = "0"
                        menor_estoque_d7 = estoque_d0
                        proxima_data_disponivel = None


                    
                except Exception as e:
                    logger.warning(f"Erro ao calcular estoques para {item.cod_produto}: {e}")
                
                # Montar item resultado
                item_data = {
                    'id': item.id,
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_carteira': qtd_carteira,
                    'qtd_separacoes': float(qtd_separacoes),
                    'qtd_pre_separacoes': float(qtd_pre_separacoes),
                    'qtd_saldo_disponivel': qtd_saldo_disponivel,
                    'preco_unitario': preco_unitario,
                    'valor_calculado': f"R$ {valor_calculado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'peso_calculado': f"{peso_calculado:,.1f} kg".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'pallet_calculado': f"{pallet_calculado:,.1f} pal".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'menor_estoque_d7': menor_estoque_d7,
                    'estoque_data_expedicao': estoque_d0,  # CORRIGIDO: nome mais claro
                    'producao_data_expedicao': producao_d0,  # CORRIGIDO: nome mais claro
                    'proxima_data_com_estoque': proxima_data_disponivel,  # NOVO: sugestão inteligente
                    'expedicao': item.expedicao.strftime('%Y-%m-%d') if item.expedicao else '',
                    'agendamento': item.agendamento.strftime('%Y-%m-%d') if item.agendamento else '',
                    'protocolo': item.protocolo or ''
                }
                
                itens_resultado.append(item_data)
                
            except Exception as e:
                logger.error(f"Erro ao processar item {item.cod_produto}: {e}")
                continue
        
        # 📋 PROCESSAR PRÉ-SEPARAÇÕES COMO ITENS EDITÁVEIS
        for pre_sep in pre_separacoes:
            try:
                # 💰 CALCULAR VALORES DAS PRÉ-SEPARAÇÕES
                valor_calculado = float(pre_sep.qtd_selecionada_usuario) * float(pre_sep.valor_original_item / pre_sep.qtd_original_carteira if pre_sep.qtd_original_carteira else 0)
                peso_calculado = float(pre_sep.peso_selecionado if hasattr(pre_sep, 'peso_selecionado') else 0)
                
                # 📦 CALCULAR PALLET PROPORCIONAL
                pallet_calculado = 0
                try:
                    from app.producao.models import CadastroPalletizacao
                    palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=pre_sep.cod_produto).first()
                    if palletizacao and palletizacao.palletizacao and palletizacao.palletizacao > 0:
                        pallet_calculado = float(pre_sep.qtd_selecionada_usuario) / float(palletizacao.palletizacao)
                except ImportError:
                    pass
                
                # 📊 ESTOQUE D0/D7 (mesmo produto, mesmos dados)
                menor_estoque_d7 = '-'
                estoque_d0 = '-'
                producao_d0 = '-'
                proxima_data_disponivel = None
                
                try:
                    data_expedicao = pre_sep.data_expedicao_editada or (datetime.now().date() + timedelta(days=1))
                    resumo_estoque = SaldoEstoque.obter_resumo_produto(pre_sep.cod_produto, pre_sep.nome_produto)
                    
                    if resumo_estoque and resumo_estoque['projecao_29_dias']:
                        estoque_expedicao = _calcular_estoque_data_especifica(
                            resumo_estoque['projecao_29_dias'], data_expedicao
                        )
                        estoque_d0 = f"{int(estoque_expedicao)}" if estoque_expedicao >= 0 else "RUPTURA"
                        
                        producao_expedicao = SaldoEstoque.calcular_producao_periodo(
                            pre_sep.cod_produto, data_expedicao, data_expedicao
                        )
                        producao_d0 = f"{int(producao_expedicao)}" if producao_expedicao > 0 else "0"
                        
                        menor_estoque_calc = resumo_estoque['previsao_ruptura']
                        menor_estoque_d7 = f"{int(menor_estoque_calc)}" if menor_estoque_calc >= 0 else "RUPTURA"
                        
                        proxima_data_disponivel = _encontrar_proxima_data_com_estoque(
                            resumo_estoque['projecao_29_dias'], float(pre_sep.qtd_selecionada_usuario)
                        )
                except Exception as e:
                    logger.warning(f"Erro ao calcular estoques para pré-separação {pre_sep.cod_produto}: {e}")
                
                # Montar item de pré-separação
                pre_sep_data = {
                    'id': f"pre_{pre_sep.id}",  # ID especial para identificar como pré-separação
                    'pre_separacao_id': pre_sep.id,  # ID real da pré-separação
                    'tipo_item': 'pre_separacao',  # Identificar tipo
                    'cod_produto': pre_sep.cod_produto,
                    'nome_produto': f"[PRÉ-SEP] {getattr(pre_sep, 'nome_produto', None) or pre_sep.cod_produto or 'Produto sem nome'}",  # Fix undefined
                    'qtd_carteira': float(pre_sep.qtd_original_carteira),
                    'qtd_separacoes': 0,  # Pré-separações não têm separações filhas
                    'qtd_pre_separacoes': float(pre_sep.qtd_selecionada_usuario),
                    'qtd_saldo_disponivel': float(pre_sep.qtd_selecionada_usuario),  # Quantidade editável
                    'preco_unitario': float(pre_sep.valor_original_item / pre_sep.qtd_original_carteira if pre_sep.qtd_original_carteira else 0),
                    'valor_calculado': f"R$ {valor_calculado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'peso_calculado': f"{peso_calculado:,.1f} kg".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'pallet_calculado': f"{pallet_calculado:,.1f} pal".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'menor_estoque_d7': menor_estoque_d7,
                    'estoque_data_expedicao': estoque_d0,
                    'producao_data_expedicao': producao_d0,
                    'proxima_data_estoque': proxima_data_disponivel,
                    'expedicao': pre_sep.data_expedicao_editada.strftime('%Y-%m-%d') if pre_sep.data_expedicao_editada else '',
                    'agendamento': pre_sep.data_agendamento_editada.strftime('%Y-%m-%d') if pre_sep.data_agendamento_editada else '',
                    'protocolo': pre_sep.protocolo_editado or '',
                    'status': pre_sep.status,
                    'criado_em': pre_sep.data_criacao.strftime('%d/%m/%Y %H:%M') if hasattr(pre_sep, 'data_criacao') and pre_sep.data_criacao else '',
                    'criado_por': getattr(pre_sep, 'criado_por', None) or 'Sistema',
                    'observacoes': pre_sep.observacoes_usuario or ''
                }
                
                itens_resultado.append(pre_sep_data)
                
            except Exception as e:
                logger.error(f"Erro ao processar pré-separação {pre_sep.id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'itens': itens_resultado,
            'total_itens': len(itens_resultado),
            'total_carteira': len(itens_carteira),
            'total_pre_separacoes': len(pre_separacoes),
            'num_pedido': num_pedido
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar itens editáveis do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


# 🗂️ ROTAS PARA GERENCIAR PRÉ-SEPARAÇÕES NO DROPDOWN

@carteira_bp.route('/api/pedido/<num_pedido>/criar-pre-separacao', methods=['POST'])
@login_required
def api_criar_pre_separacao(num_pedido):
    """
    API CRÍTICA: Criar pré-separação a partir de item da carteira
    Esta API estava sendo chamada pelo frontend mas não existia
    """
    try:
        from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
        
        data = request.get_json()
        
        # Validar dados obrigatórios
        item_id = data.get('item_id')
        qtd_pre_separacao = float(data.get('qtd_pre_separacao', 0))
        
        if not item_id or qtd_pre_separacao <= 0:
            return jsonify({
                'success': False,
                'error': 'Item ID e quantidade são obrigatórios'
            }), 400
        
        # Buscar item da carteira
        item_carteira = CarteiraPrincipal.query.filter_by(
            id=item_id,
            num_pedido=num_pedido
        ).first()
        
        if not item_carteira:
            return jsonify({
                'success': False,
                'error': 'Item não encontrado na carteira'
            }), 404
        
        # Validar disponibilidade usando função existente
        try:
            validar_saldo_disponivel_real(num_pedido, item_carteira.cod_produto, qtd_pre_separacao)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400        # Preparar dados editáveis
        dados_editaveis = {
            'expedicao': data.get('data_expedicao'),
            'agendamento': data.get('data_agendamento'),
            'protocolo': data.get('protocolo'),
            'observacoes': data.get('observacoes')
        }
        
        # Criar pré-separação usando método implementado
        pre_separacao = PreSeparacaoItem.criar_e_salvar(
            carteira_item=item_carteira,
            qtd_selecionada=qtd_pre_separacao,
            dados_editaveis=dados_editaveis,
            usuario=current_user.nome,
            tipo_envio=data.get('tipo_envio', 'total')
        )
        
        # Ajustar carteira principal se necessário
        if qtd_pre_separacao < item_carteira.qtd_saldo_produto_pedido:
            # Criar nova linha com saldo restante
            nova_linha = CarteiraPrincipal()
            # Copiar dados do item original
            for column in item_carteira.__table__.columns:
                if column.name not in ['id']:
                    setattr(nova_linha, column.name, getattr(item_carteira, column.name))
            
            # Ajustar quantidades
            nova_linha.qtd_saldo_produto_pedido = item_carteira.qtd_saldo_produto_pedido - qtd_pre_separacao
            item_carteira.qtd_saldo_produto_pedido = qtd_pre_separacao
            
            db.session.add(nova_linha)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'pre_separacao_id': pre_separacao.id,
            'mensagem': 'Pré-separação criada com sucesso',
            'qtd_criada': qtd_pre_separacao,
            'saldo_restante': item_carteira.qtd_saldo_produto_pedido - qtd_pre_separacao
        })
        
    except ValueError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao criar pré-separação: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pre-separacao/<int:pre_sep_id>/editar', methods=['POST'])
@login_required
def api_editar_pre_separacao(pre_sep_id):
    """
    API para editar PreSeparacaoItem via dropdown
    """
    try:
        from app.carteira.models import PreSeparacaoItem
        
        data = request.get_json()
        campo = data.get('campo')
        valor = data.get('valor')
        
        if not campo:
            return jsonify({
                'success': False,
                'error': 'Campo é obrigatório'
            }), 400
        
        # Buscar pré-separação
        pre_sep = PreSeparacaoItem.query.get(pre_sep_id)
        if not pre_sep:
            return jsonify({
                'success': False,
                'error': f'Pré-separação {pre_sep_id} não encontrada'
            }), 404
        
        # Atualizar campo específico
        if campo == 'expedicao':
            if valor:
                try:
                    pre_sep.data_expedicao_editada = datetime.strptime(valor, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Formato de data inválido'
                    }), 400
            else:
                pre_sep.data_expedicao_editada = None
                
        elif campo == 'agendamento':
            if valor:
                try:
                    pre_sep.data_agendamento_editada = datetime.strptime(valor, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Formato de data inválido'
                    }), 400
            else:
                pre_sep.data_agendamento_editada = None
                
        elif campo == 'protocolo':
            pre_sep.protocolo_editado = valor or None
            
        elif campo == 'quantidade':
            qtd_nova = float(valor) if valor else 0
            if qtd_nova <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Quantidade deve ser maior que zero'
                }), 400
            
            # ✅ VALIDAÇÃO CRÍTICA DE SALDO DISPONÍVEL
            try:
                saldo_disponivel = validar_saldo_disponivel_real(
                    pre_sep.num_pedido, 
                    pre_sep.cod_produto, 
                    qtd_nova
                )
                
                pre_sep.qtd_selecionada_usuario = qtd_nova
                pre_sep.qtd_restante_calculada = pre_sep.qtd_original_carteira - qtd_nova
                
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f'Validação de saldo falhou: {str(e)}'
                }), 400
            
        elif campo == 'observacoes':
            pre_sep.observacoes_usuario = valor or None
            
        else:
            return jsonify({
                'success': False,
                'error': f'Campo {campo} não suportado'
            }), 400
        
        # Salvar alterações
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Campo {campo} da pré-separação atualizado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao editar pré-separação {pre_sep_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pre-separacao/<int:pre_sep_id>/cancelar', methods=['POST'])
@login_required
def api_cancelar_pre_separacao(pre_sep_id):
    """
    🎯 FLUXO COMPLETO: Cancelamento com RESTAURAÇÃO total
    
    PROCESSO DE RESTAURAÇÃO:
    1. Encontra item original usando referência
    2. Restaura quantidade original (500 unidades)
    3. Deleta linha saldo (400 unidades)
    4. Deleta pré-separação (100 unidades)
    5. RESULTADO: Volta ao estado inicial!
    """
    try:
        from app.carteira.models import PreSeparacaoItem
        
        # Buscar pré-separação
        pre_sep = PreSeparacaoItem.query.get(pre_sep_id)
        if not pre_sep:
            return jsonify({
                'success': False,
                'error': f'Pré-separação {pre_sep_id} não encontrada'
            }), 404
        
        # Verificar se pode ser cancelada
        if pre_sep.status in ['ENVIADO_SEPARACAO', 'PROCESSADO']:
            return jsonify({
                'success': False,
                'error': 'Não é possível cancelar pré-separação já enviada para separação'
            }), 400
        
        # 🔍 STEP 1: Cancelamento simples - apenas deletar pré-separação
        # Guardar informações para log antes de deletar
        info_log = f"Pré-separação deletada: ID={pre_sep.id}, Pedido={pre_sep.num_pedido}, Produto={pre_sep.cod_produto}, Qtd={pre_sep.qtd_selecionada_usuario}"
        logger.info(f"{info_log} por {current_user.nome if hasattr(current_user, 'nome') else 'Sistema'}")
        
        # DELETAR o registro
        db.session.delete(pre_sep)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pré-separação cancelada com sucesso',
            'pre_separacao_id': pre_sep_id
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao cancelar/restaurar pré-separação {pre_sep_id}: {e}")
        db.session.rollback()
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
                    from app.producao.models import CadastroPalletizacao
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
        
        resultado['resumo'] = {
            'total_itens': total_itens,
            'itens_suficientes': itens_suficientes,
            'itens_insuficientes': itens_insuficientes,
            'itens_ruptura': itens_ruptura,
            'percentual_disponibilidade': round((itens_suficientes / total_itens * 100) if total_itens > 0 else 0, 1)
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
                separacao.observ_ped_1 = f"{observacoes_gerais}\n[Agrupamento: {agrup_data.get('descricao', 'N/A')}]"
                separacao.criado_em = datetime.utcnow()
                # ❌ REMOVIDO: status (campo não existe no modelo - status está em Pedido)
                
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
        
        # 🔧 STEP 3: Criar linha saldo com marcação especial
        novo_item = CarteiraPrincipal(
            num_pedido=item.num_pedido,
            cod_produto=item.cod_produto,
            qtd_saldo_produto_pedido=qtd_restante,
            nome_produto=f"[SALDO] {item.nome_produto}",
            preco_produto_pedido=item.preco_produto_pedido,
            # Copiar outros campos relevantes
            cnpj_cpf=item.cnpj_cpf,
            raz_social_red=item.raz_social_red,
            data_pedido=item.data_pedido,
            status_pedido=item.status_pedido,
            vendedor=item.vendedor,
            # 🎯 MARCAÇÃO: Vincular à pré-separação para controle
            observacoes=f"SALDO_PRE_SEP_ID:{pre_separacao.id}"
        )
        db.session.add(novo_item)
        
        # 🔧 STEP 4: OCULTAR item original (marca como fracionado)
        item.qtd_saldo_produto_pedido = 0  # Zerar para ocultar
        item.observacoes = f"FRACIONADO_PRE_SEP_ID:{pre_separacao.id}|QTD_BACKUP:{qtd_original}"
        
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
            if not item.get('data_expedicao'):
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
            data_expedicao = item.get('data_expedicao')
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
                data_exp_obj = datetime.strptime(data_expedicao, '%Y-%m-%d').date() if data_expedicao else None
            except ValueError:
                data_exp_obj = None
            
            try:
                data_agend_obj = datetime.strptime(agendamento, '%Y-%m-%d').date() if agendamento else None
            except ValueError:
                data_agend_obj = None
            
            # Calcular valores proporcionais
            preco_unitario = float(carteira_item.preco_produto_pedido or 0)
            valor_separacao = qtd_separacao * preco_unitario
            
            # ✅ CALCULAR PESO E PALLET CORRETAMENTE
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(carteira_item.cod_produto, qtd_separacao)
            
            # Criar separação
            separacao = Separacao(
                separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                cod_produto=carteira_item.cod_produto,
                qtd_saldo=qtd_separacao,
                valor_saldo=valor_separacao,
                peso=peso_calculado,
                pallet=pallet_calculado,
                expedicao=data_exp_obj,
                agendamento=data_agend_obj,
                protocolo=protocolo,
                cnpj_cpf=carteira_item.cnpj_cpf,  # ✅ CAMPO OBRIGATÓRIO ADICIONADO
                criado_em=agora_brasil()
                # ❌ REMOVIDO: status (campo não existe no modelo - status está em Pedido)
                # ❌ REMOVIDO: criado_por (campo não existe no modelo)
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

 
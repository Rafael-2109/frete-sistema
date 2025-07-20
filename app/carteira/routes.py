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
        
        # 📊 QUERY BASE
        query = CarteiraPrincipal.query.filter_by(ativo=True)
        
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
                    item.peso_calculado = float(item.peso) if item.peso else 0
                    item.pallet_calculado = float(item.pallet) if item.pallet else 0
                
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
        logger.error(f"Erro ao listar carteira principal: {str(e)}")
        flash('Erro ao carregar carteira principal', 'error')
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
                'qtd_saldo': float(item.qtd_saldo_produto_pedido) if item.qtd_saldo_produto_pedido else 0,
                'preco': float(item.preco_produto_pedido) if item.preco_produto_pedido else 0,
                'valor_item': valor_item,
                'peso_item': peso_item,
                'pallet_item': pallet_item,
                'expedicao': item.expedicao.strftime('%Y-%m-%d') if item.expedicao else '',
                'agendamento': item.agendamento.strftime('%Y-%m-%d') if item.agendamento else '',
                'protocolo': item.protocolo or '',
                'separacao_lote_id': item.separacao_lote_id or '',
                'tem_separacao': bool(item.separacao_lote_id)
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
        from app.embarques.models import Embarque
        from app.pedidos.models import Pedido
        from app.transportadoras.models import Transportadora
        
        # 📊 QUERY COMPLEXA: Separacao + Embarque + Pedido + Transportadora
        separacoes = db.session.query(
            Separacao.separacao_lote_id,
            Separacao.num_pedido,
            Separacao.criado_em,
            Separacao.qtd_saldo,
            Separacao.valor_saldo,
            Separacao.peso,
            Separacao.pallet,
            Separacao.expedicao,
            Separacao.agendamento,
            Separacao.protocolo,
            
            # Dados do embarque
            Embarque.numero.label('embarque_numero'),
            Embarque.data_prevista_embarque,
            Embarque.data_embarque,
            Embarque.status.label('embarque_status'),
            Embarque.tipo_carga,
            Embarque.valor_total.label('embarque_valor_total'),
            Embarque.peso_total.label('embarque_peso_total'),
            Embarque.pallet_total.label('embarque_pallet_total'),
            
            # Dados da transportadora
            Transportadora.razao_social.label('transportadora_razao'),
            Transportadora.nome_fantasia.label('transportadora_fantasia'),
            
            # Dados do pedido
            Pedido.valor_saldo_total.label('pedido_valor_total'),
            Pedido.peso_total.label('pedido_peso_total'),
            Pedido.pallet_total.label('pedido_pallet_total')
            
        ).outerjoin(
            Embarque, 
            Separacao.separacao_lote_id == Embarque.separacao_lote_id
        ).outerjoin(
            Transportadora,
            Embarque.transportadora_id == Transportadora.id
        ).outerjoin(
            Pedido,
            and_(
                Separacao.num_pedido == Pedido.num_pedido,
                Separacao.separacao_lote_id == Pedido.separacao_lote_id
            )
        ).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.separacao_lote_id.isnot(None)  # Apenas separações válidas
        ).order_by(
            Separacao.criado_em.desc()
        ).all()
        
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
                'criado_em': sep.criado_em.strftime('%d/%m/%Y %H:%M') if sep.criado_em else '',
                'status': status_separacao,
                'status_class': status_class,
                'total_itens': total_itens_separacao,
                
                # Dados da separação
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


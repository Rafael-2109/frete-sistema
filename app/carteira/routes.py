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
            # 'rota': CarteiraPrincipal.rota,  # TODO: Aplicar migração das colunas rota/sub_rota
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
                
                # 🛣️ BUSCAR ROTA E SUB-ROTA TEMPORÁRIO (até aplicar migração)
                # TODO: Após aplicar migração, usar campos do banco
                item.rota = _buscar_rota_por_uf(item.cod_uf) if item.cod_uf else None
                item.sub_rota = _buscar_sub_rota_por_uf_cidade(item.cod_uf, item.nome_cidade) if item.cod_uf and item.nome_cidade else None
        
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


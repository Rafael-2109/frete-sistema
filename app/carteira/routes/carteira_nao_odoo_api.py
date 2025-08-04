"""
API para gerenciar a Carteira Não-Odoo
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.carteira.models import CarteiraCopia, CarteiraPrincipal
from app.producao.models import CadastroPalletizacao
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from sqlalchemy import and_, func
import logging

logger = logging.getLogger(__name__)

carteira_nao_odoo_api = Blueprint('carteira_nao_odoo_api', __name__)

@carteira_nao_odoo_api.route('/api/carteira-nao-odoo', methods=['GET'])
@login_required
def listar_carteira():
    """Lista todos os itens da carteira não-Odoo (CarteiraCopia)"""
    try:
        # Buscar todos os itens ativos da CarteiraCopia
        query = CarteiraCopia.query.filter_by(ativo=True)
        
        # Filtros opcionais via query string
        vendedor = request.args.get('vendedor')
        equipe = request.args.get('equipe_vendas')
        estado = request.args.get('estado')
        search = request.args.get('search')
        
        if vendedor:
            query = query.filter(CarteiraCopia.vendedor == vendedor)
        if equipe:
            query = query.filter(CarteiraCopia.equipe_vendas == equipe)
        if estado:
            query = query.filter(CarteiraCopia.estado == estado)
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                db.or_(
                    CarteiraCopia.num_pedido.ilike(search_pattern),
                    CarteiraCopia.cnpj_cpf.ilike(search_pattern),
                    CarteiraCopia.raz_social.ilike(search_pattern),
                    CarteiraCopia.raz_social_red.ilike(search_pattern),
                    CarteiraCopia.cod_produto.ilike(search_pattern)
                )
            )
        
        # Ordenar por pedido e produto
        items = query.order_by(
            CarteiraCopia.num_pedido,
            CarteiraCopia.cod_produto
        ).all()
        
        # Processar cada item
        resultado = []
        for item in items:
            # Buscar nome do produto no CadastroPalletizacao
            nome_produto = item.nome_produto
            try:
                palletizacao = CadastroPalletizacao.query.filter_by(
                    cod_produto=item.cod_produto
                ).first()
                if palletizacao and palletizacao.descricao:
                    nome_produto = palletizacao.descricao
            except Exception as e:
                logger.warning(f"Erro ao buscar produto {item.cod_produto}: {e}")
            
            # Buscar quantidade em embarque (separações cotadas)
            qtd_embarque = 0
            try:
                # Buscar separações do pedido/produto com status COTADO
                separacoes_cotadas = db.session.query(
                    func.sum(Separacao.qtd_saldo)
                ).join(
                    Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                ).filter(
                    and_(
                        Separacao.num_pedido == item.num_pedido,
                        Separacao.cod_produto == item.cod_produto,
                        Pedido.status == 'COTADO'
                    )
                ).scalar()
                
                qtd_embarque = float(separacoes_cotadas or 0)
            except Exception as e:
                logger.warning(f"Erro ao buscar embarques: {e}")
            
            # Recalcular saldo (qtd_pedido - qtd_cancelada - baixa)
            qtd_saldo = float(item.qtd_produto_pedido or 0) - \
                       float(item.qtd_cancelada_produto_pedido or 0) - \
                       float(item.baixa_produto_pedido or 0)
            
            # Calcular valor total (saldo * preço)
            valor_total = qtd_saldo * float(item.preco_produto_pedido or 0)
            
            # Montar objeto de resposta
            resultado.append({
                'id': item.id,
                'num_pedido': item.num_pedido,
                'cnpj_cpf': item.cnpj_cpf,
                'raz_social': item.raz_social,
                'raz_social_red': item.raz_social_red,
                'estado': item.estado,
                'municipio': item.municipio,
                'vendedor': item.vendedor,
                'equipe_vendas': item.equipe_vendas,
                'cod_produto': item.cod_produto,
                'nome_produto': nome_produto,
                'qtd_produto_pedido': float(item.qtd_produto_pedido or 0),
                'qtd_cancelada_produto_pedido': float(item.qtd_cancelada_produto_pedido or 0),
                'baixa_produto_pedido': float(item.baixa_produto_pedido or 0),
                'qtd_saldo_produto_pedido': qtd_saldo,
                'qtd_embarque': qtd_embarque,
                'preco_produto_pedido': float(item.preco_produto_pedido or 0),
                'valor_total': valor_total
            })
        
        return jsonify({
            'success': True,
            'items': resultado,
            'total': len(resultado)
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar carteira não-Odoo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@carteira_nao_odoo_api.route('/api/carteira-nao-odoo/<int:id>/cancelar', methods=['PUT'])
@login_required
def atualizar_qtd_cancelada(id):
    """Atualiza quantidade cancelada de um item"""
    try:
        # Buscar item da CarteiraCopia
        item_copia = CarteiraCopia.query.get_or_404(id)
        
        data = request.get_json()
        nova_qtd_cancelada = float(data.get('qtd_cancelada', 0))
        
        # Validações
        if nova_qtd_cancelada < 0:
            return jsonify({
                'success': False,
                'error': 'Quantidade cancelada não pode ser negativa'
            }), 400
        
        # Verificar se tem quantidade em embarque cotado
        qtd_embarque_cotado = 0
        try:
            separacoes_cotadas = db.session.query(
                func.sum(Separacao.qtd_saldo)
            ).join(
                Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
            ).filter(
                and_(
                    Separacao.num_pedido == item_copia.num_pedido,
                    Separacao.cod_produto == item_copia.cod_produto,
                    Pedido.status == 'COTADO'
                )
            ).scalar()
            
            qtd_embarque_cotado = float(separacoes_cotadas or 0)
        except Exception as e:
            logger.warning(f"Erro ao verificar embarques cotados: {e}")
        
        # Calcular máximo permitido
        max_cancelada = float(item_copia.qtd_produto_pedido or 0) - \
                       float(item_copia.baixa_produto_pedido or 0) - \
                       qtd_embarque_cotado
        
        if nova_qtd_cancelada > max_cancelada:
            return jsonify({
                'success': False,
                'error': f'Quantidade cancelada excede o máximo permitido ({max_cancelada:.3f})',
                'max_permitido': max_cancelada
            }), 400
        
        # Atualizar CarteiraCopia
        item_copia.qtd_cancelada_produto_pedido = nova_qtd_cancelada
        item_copia.qtd_saldo_produto_calculado = (
            float(item_copia.qtd_produto_pedido or 0) - 
            nova_qtd_cancelada - 
            float(item_copia.baixa_produto_pedido or 0)
        )
        item_copia.updated_by = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
        
        # Atualizar também na CarteiraPrincipal
        item_principal = CarteiraPrincipal.query.filter(
            and_(
                CarteiraPrincipal.num_pedido == item_copia.num_pedido,
                CarteiraPrincipal.cod_produto == item_copia.cod_produto
            )
        ).first()
        
        if item_principal:
            # Calcular diferença para aplicar na principal
            diferenca = nova_qtd_cancelada - float(item_principal.qtd_cancelada_produto_pedido or 0)
            
            item_principal.qtd_cancelada_produto_pedido = nova_qtd_cancelada
            item_principal.qtd_saldo_produto_pedido = float(item_principal.qtd_saldo_produto_pedido or 0) - diferenca
            item_principal.updated_by = item_copia.updated_by
            
            logger.info(f"Atualizado CarteiraPrincipal: {item_principal.num_pedido}/{item_principal.cod_produto}")
        
        # Commit das alterações
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Quantidade cancelada atualizada com sucesso',
            'qtd_cancelada': nova_qtd_cancelada,
            'qtd_saldo': float(item_copia.qtd_saldo_produto_calculado)
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar quantidade cancelada: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@carteira_nao_odoo_api.route('/api/carteira-nao-odoo/atualizar-faturamento', methods=['POST'])
@login_required
def atualizar_faturamento():
    """
    Atualiza baixa_produto_pedido baseado no faturamento
    Esta função será chamada após importação de faturamento
    """
    try:
        from app.faturamento.models import FaturamentoProduto
        
        # Buscar todos os faturamentos que têm origem (número do pedido)
        faturamentos = FaturamentoProduto.query.filter(
            FaturamentoProduto.origem.isnot(None),
            FaturamentoProduto.origem != ''
        ).all()
        
        atualizacoes = 0
        
        for fat in faturamentos:
            # Buscar item correspondente na CarteiraCopia
            item_copia = CarteiraCopia.query.filter(
                and_(
                    CarteiraCopia.num_pedido == fat.origem,
                    CarteiraCopia.cod_produto == fat.cod_produto
                )
            ).first()
            
            if item_copia:
                # Atualizar baixa (somar quantidade faturada)
                qtd_anterior = float(item_copia.baixa_produto_pedido or 0)
                qtd_faturada = float(fat.qtd_produto_faturado or 0)
                
                item_copia.baixa_produto_pedido = qtd_anterior + qtd_faturada
                item_copia.qtd_saldo_produto_calculado = (
                    float(item_copia.qtd_produto_pedido or 0) - 
                    float(item_copia.qtd_cancelada_produto_pedido or 0) - 
                    item_copia.baixa_produto_pedido
                )
                
                atualizacoes += 1
                
                # Atualizar também na CarteiraPrincipal
                item_principal = CarteiraPrincipal.query.filter(
                    and_(
                        CarteiraPrincipal.num_pedido == fat.origem,
                        CarteiraPrincipal.cod_produto == fat.cod_produto
                    )
                ).first()
                
                if item_principal:
                    item_principal.qtd_saldo_produto_pedido = float(item_principal.qtd_saldo_produto_pedido or 0) - qtd_faturada
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{atualizacoes} itens atualizados com faturamento'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar faturamento: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
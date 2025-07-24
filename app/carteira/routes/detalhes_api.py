"""
API para detalhes do pedido - usado no expandir da carteira agrupada
"""

from flask import jsonify
from flask_login import login_required
from app import db
from app.carteira.models import CarteiraPrincipal
from . import carteira_bp
import logging

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/detalhes')
@login_required
def detalhes_pedido(num_pedido):
    """
    API para obter detalhes de um pedido para exibir no dropdown expandido
    """
    try:
        # Buscar todos os itens do pedido
        itens = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).order_by(CarteiraPrincipal.cod_produto).all()
        
        if not itens:
            return jsonify({
                'success': False,
                'error': f'Nenhum item encontrado para o pedido {num_pedido}'
            }), 404
        
        # Montar dados dos itens
        itens_data = []
        total_valor = 0
        total_peso = 0
        total_itens = 0
        
        for item in itens:
            # Calcular valores
            valor_item = float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
            peso_item = float(item.qtd_saldo_produto_pedido or 0) * float(item.peso or 0)
            
            itens_data.append({
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'qtd_pedido': float(item.qtd_produto_pedido or 0),
                'qtd_saldo': float(item.qtd_saldo_produto_pedido or 0),
                'preco_unitario': float(item.preco_produto_pedido or 0),
                'valor_total': valor_item,
                'peso_unitario': float(item.peso or 0),
                'peso_total': peso_item,
                'estoque_hoje': float(item.estoque or 0),
                'data_disponibilidade': item.data_disponibilidade.isoformat() if item.data_disponibilidade else None,
                'separacao_lote_id': item.separacao_lote_id,
                'expedicao': item.expedicao.isoformat() if item.expedicao else None,
                'agendamento': item.agendamento.isoformat() if item.agendamento else None,
                'protocolo': item.protocolo
            })
            
            total_valor += valor_item
            total_peso += peso_item
            total_itens += 1
        
        # Dados do primeiro item para informações gerais
        primeiro_item = itens[0]
        
        return jsonify({
            'success': True,
            'num_pedido': num_pedido,
            'cliente': {
                'cnpj_cpf': primeiro_item.cnpj_cpf,
                'razao_social': primeiro_item.raz_social,
                'razao_social_red': primeiro_item.raz_social_red,
                'municipio': primeiro_item.municipio,
                'estado': primeiro_item.estado,
                'vendedor': primeiro_item.vendedor,
                'equipe_vendas': primeiro_item.equipe_vendas
            },
            'endereco_entrega': {
                'cnpj': primeiro_item.cnpj_endereco_ent,
                'empresa': primeiro_item.empresa_endereco_ent,
                'cep': primeiro_item.cep_endereco_ent,
                'cidade': primeiro_item.nome_cidade,
                'uf': primeiro_item.cod_uf,
                'bairro': primeiro_item.bairro_endereco_ent,
                'rua': primeiro_item.rua_endereco_ent,
                'numero': primeiro_item.endereco_ent,
                'telefone': primeiro_item.telefone_endereco_ent
            },
            'totais': {
                'itens': total_itens,
                'valor': total_valor,
                'peso': total_peso
            },
            'itens': itens_data,
            'observacoes': primeiro_item.observ_ped_1
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500
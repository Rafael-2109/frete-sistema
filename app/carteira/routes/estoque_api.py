"""
API para carregar dados de estoque de forma assíncrona
"""

from flask import jsonify
from flask_login import login_required
from app import db
from app.carteira.models import CarteiraPrincipal
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from sqlalchemy import and_
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/estoque', methods=['GET'])
@login_required
def obter_estoque_pedido(num_pedido):
    """
    Retorna dados de estoque para produtos de um pedido específico
    Usado para carregamento assíncrono após renderização inicial
    """
    try:
        # Buscar produtos do pedido com dados de estoque
        produtos = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido
        ).all()
        
        produtos_estoque = []
        
        for produto in produtos:
            # USAR ServicoEstoqueTempoReal IGUAL ao workspace_api.py
            projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(produto.cod_produto, dias=28)
            
            if projecao_completa:
                # Usar dados calculados pelo serviço (VALORES REAIS)
                produto_estoque = {
                    'cod_produto': produto.cod_produto,
                    'estoque': projecao_completa['estoque_atual'],
                    'estoque_d0': projecao_completa.get('estoque_d0', projecao_completa['estoque_atual']),
                    'menor_estoque_produto_d7': projecao_completa.get('menor_estoque_d7', 0),
                    'saldo_estoque_pedido': float(produto.saldo_estoque_pedido or 0),
                    'dia_ruptura': projecao_completa.get('dia_ruptura')
                }
                
                # Adicionar projeções D0-D28 calculadas
                for i, valor in enumerate(projecao_completa.get('projecao', [])):
                    if i < 29:
                        produto_estoque[f'estoque_d{i}'] = valor
                
                produtos_estoque.append(produto_estoque)
            else:
                # Fallback se o serviço falhar
                produtos_estoque.append({
                    'cod_produto': produto.cod_produto,
                    'estoque': float(produto.estoque or 0),
                    'estoque_d0': float(produto.estoque_d0 or 0),
                    'menor_estoque_produto_d7': float(produto.menor_estoque_produto_d7 or 0),
                    'saldo_estoque_pedido': float(produto.saldo_estoque_pedido or 0),
                    # Adicionar projeções D0-D28 se necessário
                    **{f'estoque_d{i}': float(getattr(produto, f'estoque_d{i}', 0) or 0) for i in range(29)}
                })
        
        return jsonify({
            'success': True,
            'produtos': produtos_estoque,
            'total': len(produtos_estoque)
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar estoque do pedido {num_pedido}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/workspace-estoque', methods=['GET'])
@login_required
def obter_workspace_estoque(num_pedido):
    """
    Retorna dados completos de estoque para o workspace
    Inclui projeções, produção programada e análise de ruptura
    """
    try:
        # Buscar produtos do pedido com todos os dados
        produtos = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido
        ).all()
        
        produtos_completos = []
        
        for produto in produtos:
            # USAR ServicoEstoqueTempoReal IGUAL ao workspace_api.py
            projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(produto.cod_produto, dias=28)
            
            if projecao_completa:
                # Usar dados calculados pelo serviço (VALORES REAIS)
                produto_data = {
                    'cod_produto': produto.cod_produto,
                    'nome_produto': produto.nome_produto,
                    'qtd_saldo_produto_pedido': float(produto.qtd_saldo_produto_pedido or 0),
                    'preco_produto_pedido': float(produto.preco_produto_pedido or 0),
                    
                    # Estoque calculado pelo serviço
                    'estoque': projecao_completa['estoque_atual'],
                    'estoque_d0': projecao_completa.get('estoque_d0', projecao_completa['estoque_atual']),
                    'saldo_estoque_pedido': float(produto.saldo_estoque_pedido or 0),
                    'menor_estoque_produto_d7': projecao_completa.get('menor_estoque_d7', 0),
                    'dia_ruptura': projecao_completa.get('dia_ruptura'),
                    
                    # Produção programada (se disponível)
                    'producao_hoje': 0,  # Seria calculado com base em outra tabela se existisse
                    
                    # Peso e palletização
                    'peso_unitario': float(produto.peso or 0) / float(produto.qtd_saldo_produto_pedido or 1) if produto.qtd_saldo_produto_pedido else 0,
                    'palletizacao': 1000,  # Valor padrão, ajustar conforme necessário
                }
                
                # Adicionar todas as projeções D0-D28 calculadas
                for i, valor in enumerate(projecao_completa.get('projecao', [])):
                    if i < 29:
                        produto_data[f'estoque_d{i}'] = valor
            else:
                # Fallback se o serviço falhar
                produto_data = {
                    'cod_produto': produto.cod_produto,
                    'nome_produto': produto.nome_produto,
                    'qtd_saldo_produto_pedido': float(produto.qtd_saldo_produto_pedido or 0),
                    'preco_produto_pedido': float(produto.preco_produto_pedido or 0),
                    
                    # Estoque atual e projeções
                    'estoque': float(produto.estoque or 0),
                    'estoque_d0': float(produto.estoque_d0 or 0),
                    'saldo_estoque_pedido': float(produto.saldo_estoque_pedido or 0),
                    'menor_estoque_produto_d7': float(produto.menor_estoque_produto_d7 or 0),
                    
                    # Produção programada (se disponível)
                    'producao_hoje': 0,  # Seria calculado com base em outra tabela se existisse
                    
                    # Peso e palletização
                    'peso_unitario': float(produto.peso or 0) / float(produto.qtd_saldo_produto_pedido or 1) if produto.qtd_saldo_produto_pedido else 0,
                    'palletizacao': 1000,  # Valor padrão, ajustar conforme necessário
                }
                
                # Adicionar todas as projeções D0-D28
                for i in range(29):
                    campo = f'estoque_d{i}'
                    if hasattr(produto, campo):
                        produto_data[campo] = float(getattr(produto, campo, 0) or 0)
            
            produtos_completos.append(produto_data)
        
        return jsonify({
            'success': True,
            'produtos': produtos_completos,
            'total': len(produtos_completos)
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar estoque completo do pedido {num_pedido}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
"""
Rotas para analise de margem de pedidos
Acesso restrito - vendedores nao podem acessar

Autor: Sistema de Fretes
Data: 27/12/2025
"""

from flask import render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps

from app.comercial import comercial_bp
from app.comercial.services.margem_service import MargemService
import logging

logger = logging.getLogger(__name__)


def nao_vendedor_required(f):
    """
    Decorator que bloqueia acesso de vendedores.
    Vendedores sao redirecionados para o dashboard comercial.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.perfil == 'vendedor':
            flash('Acesso negado. Vendedores nao podem acessar a Analise de Margem.', 'warning')
            return redirect(url_for('comercial.dashboard_diretoria'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# PAGINA PRINCIPAL
# =============================================================================

@comercial_bp.route('/analise-margem')
@nao_vendedor_required
def analise_margem():
    """Pagina principal de analise de margem"""
    return render_template('comercial/analise_margem.html')


# =============================================================================
# APIs
# =============================================================================

@comercial_bp.route('/api/margem/filtros')
@nao_vendedor_required
def api_margem_filtros():
    """Retorna filtros disponiveis para a tela"""
    try:
        filtros = MargemService.obter_filtros_disponiveis()
        return jsonify({
            'sucesso': True,
            'filtros': filtros
        })
    except Exception as e:
        logger.error(f"Erro ao obter filtros de margem: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@comercial_bp.route('/api/margem/dados')
@nao_vendedor_required
def api_margem_dados():
    """
    Retorna dados de margem com agrupamento dinamico

    Query params:
        - agrupamento: produto_pedido|pedido|data|tipo_produto|equipe|vendedor
        - data_inicio: YYYY-MM-DD
        - data_fim: YYYY-MM-DD
        - equipe: nome da equipe
        - vendedor: nome do vendedor
        - tipo_produto: valor do filtro
        - tipo_produto_campo: embalagem|materia_prima|categoria
        - page: pagina atual
        - per_page: itens por pagina
    """
    try:
        # Parametros de agrupamento
        agrupamento = request.args.get('agrupamento', 'produto_pedido')

        # Paginacao
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        # Limitar per_page para evitar sobrecarga
        per_page = min(per_page, 200)

        # Filtros
        filtros = {
            'data_inicio': request.args.get('data_inicio'),
            'data_fim': request.args.get('data_fim'),
            'equipe': request.args.get('equipe'),
            'vendedor': request.args.get('vendedor'),
            'tipo_produto': request.args.get('tipo_produto'),
            'tipo_produto_campo': request.args.get('tipo_produto_campo', 'embalagem')
        }

        # Remover filtros vazios
        filtros = {k: v for k, v in filtros.items() if v}

        # Buscar dados
        resultado = MargemService.obter_dados_margem(
            agrupamento=agrupamento,
            filtros=filtros,
            page=page,
            per_page=per_page
        )

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao obter dados de margem: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@comercial_bp.route('/api/margem/cliente/<cnpj>/historico')
@nao_vendedor_required
def api_margem_cliente_historico(cnpj):
    """
    Retorna historico de pedidos do cliente

    Args:
        cnpj: CNPJ/CPF do cliente

    Query params:
        - limite: numero maximo de pedidos (default: 4)
    """
    try:
        limite = request.args.get('limite', 4, type=int)
        limite = min(limite, 10)  # Maximo 10 pedidos

        resultado = MargemService.obter_historico_cliente(cnpj, limite)
        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao obter historico do cliente {cnpj}: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

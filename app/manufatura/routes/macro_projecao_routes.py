"""
Rotas para Macro Projeção de Componentes
========================================

Visualização consolidada de projeção de componentes (produto_comprado=True)
com índices de Ruptura e Saldo Mensal.

Autor: Sistema de Fretes
Data: 13/01/2026
"""

from flask import Blueprint, render_template, jsonify, make_response, request
from flask_login import login_required
from datetime import date

from app.manufatura.services.macro_projecao_componentes_service import MacroProjecaoComponentesService


# Blueprint para macro projeção
macro_projecao_bp = Blueprint(
    'macro_projecao',
    __name__,
    url_prefix='/manufatura/macro-projecao'
)


@macro_projecao_bp.route('/')
@login_required
def index():
    """
    Página principal de Macro Projeção de Componentes
    """
    return render_template('manufatura/macro_projecao_componentes.html')


@macro_projecao_bp.route('/api/dados')
@login_required
def api_dados():
    """
    API para buscar dados da projeção macro

    Query params:
        - categoria: filtrar por categoria_produto
        - tipo_materia_prima: filtrar por tipo_materia_prima
        - linha_producao: filtrar por linha_producao

    Returns:
        JSON com dados da projeção
    """
    try:
        # Parâmetros de filtro
        categoria = request.args.get('categoria', '').strip() or None
        tipo_materia_prima = request.args.get('tipo_materia_prima', '').strip() or None
        linha_producao = request.args.get('linha_producao', '').strip() or None

        service = MacroProjecaoComponentesService()
        dados = service.calcular_projecao_macro(
            categoria=categoria,
            tipo_materia_prima=tipo_materia_prima,
            linha_producao=linha_producao
        )

        return jsonify(dados)

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@macro_projecao_bp.route('/api/filtros')
@login_required
def api_filtros():
    """
    API para buscar opções de filtros (valores únicos)

    Returns:
        JSON com listas de categorias, tipos_materia_prima, linhas_producao
    """
    try:
        service = MacroProjecaoComponentesService()
        opcoes = service.get_opcoes_filtros()

        return jsonify({
            'sucesso': True,
            **opcoes
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@macro_projecao_bp.route('/exportar')
@login_required
def exportar_excel():
    """
    Exporta projeção macro para Excel

    Query params:
        - categoria: filtrar por categoria_produto
        - tipo_materia_prima: filtrar por tipo_materia_prima
        - linha_producao: filtrar por linha_producao

    Returns:
        Arquivo Excel para download
    """
    try:
        # Parâmetros de filtro
        categoria = request.args.get('categoria', '').strip() or None
        tipo_materia_prima = request.args.get('tipo_materia_prima', '').strip() or None
        linha_producao = request.args.get('linha_producao', '').strip() or None

        service = MacroProjecaoComponentesService()
        dados = service.calcular_projecao_macro(
            categoria=categoria,
            tipo_materia_prima=tipo_materia_prima,
            linha_producao=linha_producao
        )

        if not dados.get('sucesso'):
            return jsonify({
                'sucesso': False,
                'erro': dados.get('erro', 'Erro ao gerar dados')
            }), 500

        # Gerar Excel
        excel_bytes = service.exportar_para_excel(dados)

        # Criar resposta
        response = make_response(excel_bytes)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=macro_projecao_componentes_{date.today().strftime("%Y%m%d")}.xlsx'

        return response

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@macro_projecao_bp.route('/api/filtrar')
@login_required
def api_filtrar():
    """
    API para filtrar dados da projeção

    Query params:
        - search: texto para buscar no código ou nome
        - apenas_negativos: se 'true', mostra apenas saldos negativos
        - ordenar_por: campo para ordenação (ruptura_saldo, nome, codigo)
        - categoria: filtrar por categoria_produto
        - tipo_materia_prima: filtrar por tipo_materia_prima
        - linha_producao: filtrar por linha_producao

    Returns:
        JSON com dados filtrados
    """
    try:
        search = request.args.get('search', '').strip().lower()
        apenas_negativos = request.args.get('apenas_negativos', 'false').lower() == 'true'
        ordenar_por = request.args.get('ordenar_por', 'ruptura_saldo')

        # Filtros de dropdown
        categoria = request.args.get('categoria', '').strip() or None
        tipo_materia_prima = request.args.get('tipo_materia_prima', '').strip() or None
        linha_producao = request.args.get('linha_producao', '').strip() or None

        service = MacroProjecaoComponentesService()
        dados = service.calcular_projecao_macro(
            categoria=categoria,
            tipo_materia_prima=tipo_materia_prima,
            linha_producao=linha_producao
        )

        if not dados.get('sucesso'):
            return jsonify(dados), 500

        componentes = dados.get('componentes', [])

        # Filtrar por busca
        if search:
            componentes = [
                c for c in componentes
                if search in c.get('cod_produto', '').lower()
                or search in c.get('nome_produto', '').lower()
            ]

        # Filtrar apenas negativos
        if apenas_negativos:
            componentes = [
                c for c in componentes
                if c.get('ruptura', {}).get('saldo', 0) < 0
                or c.get('saldo_mes_atual', {}).get('saldo', 0) < 0
                or c.get('saldo_mes_proximo', {}).get('saldo', 0) < 0
            ]

        # Ordenar
        if ordenar_por == 'ruptura_saldo':
            componentes.sort(key=lambda x: x.get('ruptura', {}).get('saldo', 0))
        elif ordenar_por == 'nome':
            componentes.sort(key=lambda x: x.get('nome_produto', ''))
        elif ordenar_por == 'codigo':
            componentes.sort(key=lambda x: x.get('cod_produto', ''))

        dados['componentes'] = componentes
        dados['total_componentes'] = len(componentes)

        return jsonify(dados)

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

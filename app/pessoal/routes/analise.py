"""Rotas da tela de Analise de Categorias — busca, comparacao, grupos."""
from datetime import date

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.pessoal import pode_acessar_pessoal
from app.pessoal.services.analise_service import (
    buscar_categorias_fuzzy, serie_mensal_categorias, extrato_por_categorias,
    listar_grupos, criar_grupo, atualizar_grupo, excluir_grupo, obter_grupo,
)

analise_bp = Blueprint('pessoal_analise', __name__)


def _parse_mes(mes_str):
    try:
        partes = (mes_str or '').split('-')
        ano, mes = int(partes[0]), int(partes[1])
        date(ano, mes, 1)
        return ano, mes
    except (ValueError, IndexError, AttributeError, TypeError):
        hoje = date.today()
        return hoje.year, hoje.month


def _clamp_meses(n):
    if n is None or n < 2:
        return 2
    if n > 24:
        return 24
    return n


def _parse_ids(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        items = raw
    else:
        items = str(raw).split(',')
    out = []
    for v in items:
        v = str(v).strip()
        if not v:
            continue
        try:
            out.append(int(v))
        except ValueError:
            continue
    return out


# =============================================================================
# PAGINA
# =============================================================================
@analise_bp.route('/analise')
@login_required
def index():
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403
    return render_template('pessoal/analise.html')


# =============================================================================
# API — BUSCA FUZZY DE CATEGORIAS
# =============================================================================
@analise_bp.route('/api/analise/categorias/buscar')
@login_required
def api_buscar_categorias():
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    q = request.args.get('q', '')
    limit = request.args.get('limit', 50, type=int)
    limit = max(1, min(limit, 200))
    categorias = buscar_categorias_fuzzy(q, limit=limit)
    return jsonify({'sucesso': True, 'categorias': categorias})


# =============================================================================
# API — DADOS (valores + serie mensal)
# =============================================================================
@analise_bp.route('/api/analise/dados')
@login_required
def api_dados():
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    cat_ids = _parse_ids(request.args.get('categorias'))
    ano, mes = _parse_mes(request.args.get('mes'))
    n_meses = _clamp_meses(request.args.get('meses', 6, type=int))
    dados = serie_mensal_categorias(cat_ids, ano, mes, n_meses)
    return jsonify({'sucesso': True, **dados})


# =============================================================================
# API — EXTRATO (transacoes detalhadas)
# =============================================================================
@analise_bp.route('/api/analise/transacoes')
@login_required
def api_transacoes():
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    cat_ids = _parse_ids(request.args.get('categorias'))
    ano, mes = _parse_mes(request.args.get('mes'))
    n_meses = _clamp_meses(request.args.get('meses', 6, type=int))
    limit = request.args.get('limit', 200, type=int)
    offset = request.args.get('offset', 0, type=int)
    incluir_receitas = request.args.get('incluir_receitas', '1') != '0'

    resultado = extrato_por_categorias(
        cat_ids, ano, mes, n_meses,
        limit=limit, offset=offset, incluir_receitas=incluir_receitas,
    )
    return jsonify({'sucesso': True, **resultado})


# =============================================================================
# API — CRUD GRUPOS
# =============================================================================
@analise_bp.route('/api/analise/grupos', methods=['GET'])
@login_required
def api_listar_grupos():
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403
    return jsonify({'sucesso': True, 'grupos': listar_grupos()})


@analise_bp.route('/api/analise/grupos', methods=['POST'])
@login_required
def api_criar_grupo():
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    try:
        grupo = criar_grupo(
            nome=dados.get('nome', ''),
            categoria_ids=_parse_ids(dados.get('categoria_ids') or dados.get('categorias')),
            descricao=dados.get('descricao'),
            cor=dados.get('cor'),
        )
        return jsonify({'sucesso': True, 'grupo': grupo})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@analise_bp.route('/api/analise/grupos/<int:grupo_id>', methods=['GET'])
@login_required
def api_obter_grupo(grupo_id):
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403
    grupo = obter_grupo(grupo_id)
    if not grupo:
        return jsonify({'sucesso': False, 'mensagem': 'Grupo nao encontrado.'}), 404
    return jsonify({'sucesso': True, 'grupo': grupo})


@analise_bp.route('/api/analise/grupos/<int:grupo_id>', methods=['PUT'])
@login_required
def api_atualizar_grupo(grupo_id):
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    try:
        cats = dados.get('categoria_ids')
        if cats is None:
            cats = dados.get('categorias')
        grupo = atualizar_grupo(
            grupo_id,
            nome=dados.get('nome'),
            categoria_ids=_parse_ids(cats) if cats is not None else None,
            descricao=dados.get('descricao'),
            cor=dados.get('cor'),
        )
        return jsonify({'sucesso': True, 'grupo': grupo})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@analise_bp.route('/api/analise/grupos/<int:grupo_id>', methods=['DELETE'])
@login_required
def api_excluir_grupo(grupo_id):
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403
    try:
        excluir_grupo(grupo_id)
        return jsonify({'sucesso': True})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 404
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

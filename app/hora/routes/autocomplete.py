"""Rotas de autocomplete centralizadas para o modulo HORA.

Todas usam GET /hora/autocomplete/<entidade>?q=<texto>&limit=<N> e retornam JSON.
Filtragem por escopo de loja respeita lojas_permitidas_ids() do auth_helper.

Endpoints:
- /hora/autocomplete/chassi
- /hora/autocomplete/pedido
- /hora/autocomplete/nf-entrada
- /hora/autocomplete/venda
- /hora/autocomplete/cliente
- /hora/autocomplete/loja-externa
- /hora/autocomplete/modelo
- /hora/autocomplete/loja
"""
from __future__ import annotations

from flask import jsonify, request

from app.hora.decorators import require_hora_perm
from app.hora.routes import hora_bp
from app.hora.services import autocomplete_service
from app.hora.services.auth_helper import lojas_permitidas_ids


def _limit_arg(default: int = 20, maximum: int = 50) -> int:
    raw = (request.args.get('limit') or '').strip()
    try:
        n = int(raw) if raw else default
    except ValueError:
        n = default
    return max(1, min(n, maximum))


@hora_bp.route('/autocomplete/chassi')
@require_hora_perm('estoque', 'ver')
def autocomplete_chassi():
    return jsonify(autocomplete_service.chassis(
        q=request.args.get('q') or '',
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=_limit_arg(),
    ))


@hora_bp.route('/autocomplete/pedido')
@require_hora_perm('pedidos', 'ver')
def autocomplete_pedido():
    return jsonify(autocomplete_service.pedidos_compra(
        q=request.args.get('q') or '',
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=_limit_arg(),
    ))


@hora_bp.route('/autocomplete/nf-entrada')
@require_hora_perm('nfs', 'ver')
def autocomplete_nf_entrada():
    return jsonify(autocomplete_service.nfs_entrada(
        q=request.args.get('q') or '',
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=_limit_arg(),
    ))


@hora_bp.route('/autocomplete/venda')
@require_hora_perm('vendas', 'ver')
def autocomplete_venda():
    return jsonify(autocomplete_service.vendas(
        q=request.args.get('q') or '',
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=_limit_arg(),
    ))


@hora_bp.route('/autocomplete/cliente')
@require_hora_perm('vendas', 'ver')
def autocomplete_cliente():
    return jsonify(autocomplete_service.clientes_venda(
        q=request.args.get('q') or '',
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=_limit_arg(),
    ))


@hora_bp.route('/autocomplete/loja-externa')
@require_hora_perm('emprestimos', 'ver')
def autocomplete_loja_externa():
    return jsonify(autocomplete_service.lojas_externas(
        q=request.args.get('q') or '',
        limit=_limit_arg(),
    ))


@hora_bp.route('/autocomplete/modelo')
@require_hora_perm('modelos', 'ver')
def autocomplete_modelo():
    apenas_ativos = (request.args.get('ativos') or '1') == '1'
    return jsonify(autocomplete_service.modelos(
        q=request.args.get('q') or '',
        apenas_ativos=apenas_ativos,
        limit=_limit_arg(),
    ))


@hora_bp.route('/autocomplete/loja')
@require_hora_perm('lojas', 'ver')
def autocomplete_loja():
    apenas_ativas = (request.args.get('ativas') or '1') == '1'
    return jsonify(autocomplete_service.lojas(
        q=request.args.get('q') or '',
        lojas_permitidas_ids=lojas_permitidas_ids(),
        apenas_ativas=apenas_ativas,
        limit=_limit_arg(),
    ))

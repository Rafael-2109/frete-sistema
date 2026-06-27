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
- /hora/autocomplete/peca
"""
from __future__ import annotations

from flask import jsonify, request

from app.hora.decorators import require_hora_perm, require_hora_perm_any
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
    # Filtros opcionais (tela de Pedido de Venda — cascata + disponibilidade):
    # disponivel=1 restringe a chassis em estoque; modelo_id/cor filtram.
    # vazio_ok=1 (FU-1): permite q vazio retornar top-N (autocomplete "lista
    # ao clicar"); sem ele, q vazio mantem o corte por _MIN_CHARS ([]).
    disponivel = (request.args.get('disponivel') or '0').strip() == '1'
    try:
        modelo_id = int(request.args.get('modelo_id') or 0) or None
    except ValueError:
        modelo_id = None
    cor = (request.args.get('cor') or '').strip().upper() or None
    permitir_vazio = (request.args.get('vazio_ok') or '0').strip() == '1'
    return jsonify(autocomplete_service.chassis(
        q=request.args.get('q') or '',
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=_limit_arg(),
        disponivel=disponivel,
        modelo_id=modelo_id,
        cor=cor,
        permitir_vazio=permitir_vazio,
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
    # `sem_recebimento=1` (usado em /hora/recebimentos/novo): retorna apenas
    # NFs que ainda nao tem recebimento iniciado. Default `False` mantem
    # comportamento legado para outros callers (listagem de recebimentos etc.).
    sem_rec = (request.args.get('sem_recebimento') or '0').strip() == '1'
    return jsonify(autocomplete_service.nfs_entrada(
        q=request.args.get('q') or '',
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=_limit_arg(),
        sem_recebimento=sem_rec,
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


@hora_bp.route('/autocomplete/peca')
@require_hora_perm_any(('pecas_estoque', 'ver'), ('vendas', 'criar'), ('vendas', 'editar'))
def autocomplete_peca():
    """Catalogo global de pecas (sem filtro de loja).

    Usado em telas de pedido de compra e pedido de venda para selecionar
    a peca (item de venda OU brinde). O backend que recebe `peca_id` revalida
    saldo por loja antes de gravar item cobrado (ver
    `venda_service.adicionar_item_peca`); brinde nao abate estoque.

    Permissao via OR: `pecas_estoque/ver` (comprador/estoquista) OU
    `vendas/criar`/`vendas/editar` (vendedor montando pedido de venda). Antes
    exigia SO `pecas_estoque/ver` — o vendedor que so tinha `vendas/*` recebia
    302 e o autocomplete falhava em silencio, derrubando a selecao de peca
    de BRINDE na criacao do pedido (o `brinde_peca_id` ficava vazio e a rota
    descartava a linha). Causa-raiz do "brinde nao aparece" (2026-06-27).
    """
    apenas_ativas = (request.args.get('ativas') or '1') == '1'
    return jsonify(autocomplete_service.pecas(
        q=request.args.get('q') or '',
        apenas_ativas=apenas_ativas,
        limit=_limit_arg(),
    ))

"""
Rotas do modulo Ctrl+K.

Endpoints:
    GET  /api/cmdk/comandos         — catalogo navegavel filtrado por permissao
    GET  /api/cmdk/buscar?q&tipo    — busca multi-categoria (comando, pedido, nf)
    GET  /cmdk/pedido/<num_pedido>  — tela rica de raio-X de pedido

Convencoes:
    - Todos os endpoints exigem login (@login_required)
    - Resposta JSON: {success: bool, ...} para APIs
    - Erros nao quebram UI: retornam {success:False, error: ...} com status 200
      em casos de falha parcial (uma busca quebra mas outras funcionam)
"""
from __future__ import annotations

import logging
import re
import time

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.cmdk import cmdk_bp
from app.cmdk.services import (
    buscar_nfs,
    buscar_pedidos,
    comandos,
    historico_pedido,
    pedido_completo,
    projecao_pedido,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Limites e detectores
# =============================================================================

MAX_QUERY_LEN = 100
MIN_QUERY_LEN = 2
LIMIT_DEFAULT = 6
LIMIT_MAX = 20

# num_pedido pode ter letras (VCD/VFB), digitos, traco e underline. Max 50 chars
# (varchar(50) na carteira_principal). Validacao da rota tela_pedido.
NUM_PEDIDO_RE = re.compile(r'^[A-Za-z0-9_\-./]{1,50}$')

PEDIDO_PREFIX_RE = re.compile(r'^[VvKk][CcFf][DdLl]?\d+', re.IGNORECASE)
NF_PREFIX_RE = re.compile(r'^nf[:\s]+\S', re.IGNORECASE)
ONLY_DIGITS_RE = re.compile(r'^\d{4,}$')
COMANDO_PREFIX_RE = re.compile(r'^[>/]')


def _log_warn(categoria: str, err: Exception) -> None:
    """Log de erro nao-fatal em uma categoria de busca (nao quebra UI)."""
    try:
        current_app.logger.warning(
            f"[cmdk.routes.api_buscar] grupo={categoria} erro={err}"
        )
    except RuntimeError:
        pass


def _detectar_tipo(q: str) -> str:
    """Heuristica para priorizar a busca por prefixo."""
    if not q:
        return 'all'
    if COMANDO_PREFIX_RE.match(q):
        return 'comando'
    if PEDIDO_PREFIX_RE.match(q):
        return 'pedido'
    if NF_PREFIX_RE.match(q) or ONLY_DIGITS_RE.match(q):
        return 'nf'
    return 'all'


def _strip_prefix(q: str) -> str:
    """Remove prefixo > ou / quando filtrando comando."""
    return COMANDO_PREFIX_RE.sub('', q).strip()


# =============================================================================
# /api/cmdk/comandos
# =============================================================================

@cmdk_bp.route('/api/cmdk/comandos', methods=['GET'])
@login_required
def api_comandos():
    """Retorna catalogo de comandos visiveis para current_user."""
    started = time.time()
    items = comandos.listar_para_usuario()
    return jsonify({
        'success': True,
        'comandos': items,
        'count': len(items),
        'took_ms': round((time.time() - started) * 1000, 1),
    })


# =============================================================================
# /api/cmdk/buscar
# =============================================================================

@cmdk_bp.route('/api/cmdk/buscar', methods=['GET'])
@login_required
def api_buscar():
    """
    Busca multi-categoria.

    Query params:
        q     — query (string, 2-100 chars)
        tipo  — 'all'|'comando'|'pedido'|'nf' (default: detectado por prefixo)
        limit — 1-20 (default: 6)
    """
    started = time.time()

    q = (request.args.get('q') or '').strip()[:MAX_QUERY_LEN]
    tipo_param = (request.args.get('tipo') or 'auto').strip().lower()
    try:
        limit = int(request.args.get('limit') or LIMIT_DEFAULT)
    except (TypeError, ValueError):
        limit = LIMIT_DEFAULT
    limit = max(1, min(limit, LIMIT_MAX))

    if len(q) < MIN_QUERY_LEN:
        return jsonify({
            'success': True,
            'q': q,
            'groups': [],
            'tipo_detectado': tipo_param,
            'took_ms': 0.0,
        })

    tipo = tipo_param if tipo_param in ('all', 'comando', 'pedido', 'nf') else _detectar_tipo(q)

    groups = []

    # Comandos
    if tipo in ('all', 'comando'):
        try:
            cmds_user = comandos.listar_para_usuario()
            q_for_cmds = _strip_prefix(q) if tipo == 'comando' else q
            cmd_items = comandos.filtrar(cmds_user, q_for_cmds, limit=limit)
            if cmd_items:
                groups.append({
                    'tipo': 'comando',
                    'label': 'Comandos',
                    'icon': 'fas fa-bolt',
                    'items': cmd_items,
                })
        except Exception as e:
            _log_warn('comando', e)

    # Pedidos
    if tipo in ('all', 'pedido'):
        try:
            ped_items = buscar_pedidos.buscar(q, limit=limit)
            if ped_items:
                groups.append({
                    'tipo': 'pedido',
                    'label': 'Pedidos',
                    'icon': 'fas fa-shopping-cart',
                    'items': ped_items,
                })
        except Exception as e:
            _log_warn('pedido', e)

    # NFs
    if tipo in ('all', 'nf'):
        try:
            nf_items = buscar_nfs.buscar(q, limit=limit)
            if nf_items:
                groups.append({
                    'tipo': 'nf',
                    'label': 'NFs',
                    'icon': 'fas fa-receipt',
                    'items': nf_items,
                })
        except Exception as e:
            _log_warn('nf', e)

    return jsonify({
        'success': True,
        'q': q,
        'tipo_detectado': tipo,
        'groups': groups,
        'took_ms': round((time.time() - started) * 1000, 1),
    })


# =============================================================================
# /cmdk/pedido/<num_pedido> — tela rica (raio-X de pedido)
# =============================================================================

@cmdk_bp.route('/cmdk/pedido/<num_pedido>', methods=['GET'])
@login_required
def tela_pedido(num_pedido: str):
    """
    Tela rica de raio-X de pedido.

    Combina:
    - Detalhes (cliente, totais, itens) — pedido_completo.montar_contexto
    - Separacoes ativas (Separacao agrupada por separacao_lote_id)
    - NFs faturadas + status entrega (FaturamentoProduto + EntregaMonitorada)
    - Projecao de estoque (D0-D28) LAZY — /carteira/api/pedido/<num>/estoque
    - Projecao por linha LAZY — /carteira/api/produto/<cod>/projecao-linha
    - Acao: criar separacao via POST /carteira/api/pedido/<num>/gerar-separacao-completa

    Validacao: num_pedido deve casar NUM_PEDIDO_RE (alfanum + _-./ , 1-50 chars).
    Pedido nao encontrado: flash + redirect para carteira (NAO abort 404 — global
    handler re-raise faria pagina de erro generica).
    """
    num_pedido = (num_pedido or '').strip()

    if not num_pedido or not NUM_PEDIDO_RE.match(num_pedido):
        flash(f"Numero de pedido invalido: {num_pedido!r}", 'warning')
        return redirect(url_for('carteira.index'))

    try:
        contexto = pedido_completo.montar_contexto(num_pedido)
    except Exception as e:
        logger.exception(f"[cmdk.tela_pedido] erro montando contexto num_pedido={num_pedido}")
        flash(f"Erro ao carregar pedido {num_pedido}: {e}", 'danger')
        return redirect(url_for('carteira.index'))

    if contexto is None:
        flash(f"Pedido {num_pedido} nao encontrado.", 'warning')
        return redirect(url_for('carteira.index'))

    return render_template('cmdk/pedido_completo.html', pedido=contexto)


# =============================================================================
# /api/cmdk/pedido/<num>/projecao-estoque
# =============================================================================

@cmdk_bp.route('/api/cmdk/pedido/<num_pedido>/projecao-estoque', methods=['GET'])
@login_required
def api_projecao_estoque_pedido(num_pedido: str):
    """
    Projecao de estoque (D0-D14) dos produtos do pedido.

    Retorna formato compativel com modal-projecao-linha.js para reuso do modal.
    Aplica UnificacaoCodigos para de-duplicar codigos relacionados.
    """
    num_pedido = (num_pedido or '').strip()
    if not num_pedido or not NUM_PEDIDO_RE.match(num_pedido):
        return jsonify({'success': False, 'error': 'num_pedido invalido'}), 400

    try:
        data = projecao_pedido.montar_projecao_estoque_pedido(num_pedido)
    except Exception as e:
        logger.exception(
            f"[cmdk.api_projecao_estoque_pedido] erro num_pedido={num_pedido}"
        )
        return jsonify({'success': False, 'error': str(e)}), 500

    if data is None:
        return jsonify({'success': False, 'error': 'Pedido sem itens ativos'}), 404

    return jsonify(data)


# =============================================================================
# /api/cmdk/pedido/<num>/codigos-canonicos
# (usado pelo modal de projecao por linha para destacar produtos do pedido)
# =============================================================================

@cmdk_bp.route('/api/cmdk/pedido/<num_pedido>/codigos-canonicos', methods=['GET'])
@login_required
def api_codigos_canonicos_pedido(num_pedido: str):
    """Lista de codigos canonicos (apos UnificacaoCodigos) do pedido."""
    num_pedido = (num_pedido or '').strip()
    if not num_pedido or not NUM_PEDIDO_RE.match(num_pedido):
        return jsonify({'success': False, 'error': 'num_pedido invalido'}), 400

    try:
        cods = projecao_pedido.codigos_canonicos_do_pedido(num_pedido)
    except Exception as e:
        logger.exception(
            f"[cmdk.api_codigos_canonicos_pedido] erro num_pedido={num_pedido}"
        )
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'num_pedido': num_pedido, 'codigos': cods})


# =============================================================================
# /api/cmdk/pedido/<num>/historico
# (aba "Historico" da tela rica — le evento_supply_chain, append-only,
#  populada por trigger PostgreSQL audit_supply_chain_trigger())
# =============================================================================

@cmdk_bp.route('/api/cmdk/pedido/<num_pedido>/historico', methods=['GET'])
@login_required
def api_historico_pedido(num_pedido: str):
    """
    Historico de alteracoes do pedido (event sourcing).

    Retorna sumario + lista cronologica de "momentos" (eventos agregados
    por entidade+tipo+origem+usuario+minuto), com diff dos campos mais
    relevantes (status, expedicao, data_embarque, NF, etc).

    LAZY no client: chamada apenas ao abrir a aba "Historico" da tela rica.
    """
    num_pedido = (num_pedido or '').strip()
    if not num_pedido or not NUM_PEDIDO_RE.match(num_pedido):
        return jsonify({'success': False, 'error': 'num_pedido invalido'}), 400

    try:
        data = historico_pedido.montar_historico(num_pedido)
    except Exception as e:
        logger.exception(
            f"[cmdk.api_historico_pedido] erro num_pedido={num_pedido}"
        )
        return jsonify({'success': False, 'error': str(e)}), 500

    if data is None:
        return jsonify({
            'success': True,
            'num_pedido': num_pedido,
            'sumario': None,
            'momentos': [],
            'vazio': True,
        })

    return jsonify({
        'success': True,
        **data,
        'vazio': False,
    })

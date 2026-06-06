"""Rotas da tela admin de Transferência de Estoque (Odoo) — 3 modos.

Tela em /estoque/transferencia-estoque. Reusa os átomos maduros de
app/odoo/estoque/scripts/transfer.py (Modos 1/2) e transferir_v2 do
TransferenciaSaldoCodigoService (Modo 3). Síncrono + Simular(dry-run)/Confirmar.

Spec: docs/superpowers/specs/2026-06-06-transferencia-estoque-odoo-ui-design.md
"""
import logging
from functools import wraps

from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from app.estoque import estoque_bp
from app.utils.auth_decorators import require_admin
from app.odoo.constants.locations import LOCAIS_INDISPONIVEL
from app.odoo.estoque._utils import EMPRESAS, resolver_empresa
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.estoque.scripts.consulta_quant import StockQuantQueryService

logger = logging.getLogger(__name__)

_LOCAIS_INDISP = set(LOCAIS_INDISPONIVEL.values())


def require_admin_json(f):
    """Admin-only para endpoints JSON: 403 em vez de redirect."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.perfil != 'administrador':
            return jsonify({'success': False,
                            'message': 'Acesso restrito a administradores'}), 403
        return f(*args, **kwargs)
    return wrapper


@estoque_bp.route('/transferencia-estoque')
@login_required
@require_admin
def transferencia_estoque():
    """Tela unificada de transferência de estoque (3 modos)."""
    return render_template('estoque/transferir_estoque_odoo.html',
                           empresas=list(EMPRESAS))


@estoque_bp.route('/transferencia-estoque/api/dados-codigo')
@login_required
@require_admin_json
def api_te_dados_codigo():
    """A (por local) + B (reservada) + C (por lote) do código origem na empresa."""
    codigo = (request.args.get('codigo') or '').strip()
    empresa = (request.args.get('empresa') or '').strip().upper()
    if not codigo or not empresa:
        return jsonify({'success': False, 'message': 'Informe codigo e empresa'}), 200
    try:
        odoo = get_odoo_connection()
        res = StockQuantQueryService(odoo).listar_quants(cods=[codigo], empresas=[empresa])
        quants = res['quants']
        if not quants:
            return jsonify({'success': True, 'produto': None, 'por_local': [],
                            'por_lote': [], 'reservada_total': 0.0,
                            'message': 'Sem saldo para este codigo/empresa'})
        produto = {'cod': quants[0]['cod'], 'name': quants[0]['product_name'],
                   'tracking': quants[0]['tracking']}
        por_local, por_lote, reservada_total = {}, {}, 0.0
        for q in quants:
            reservada_total += q['reserved_quantity']
            lk = q['location_id']
            loc = por_local.setdefault(lk, {
                'location_id': lk, 'location_name': q['location_name'],
                'qty': 0.0, 'reservada': 0.0, 'disponivel': 0.0,
                'is_indisp': lk in _LOCAIS_INDISP})
            loc['qty'] += q['quantity']; loc['reservada'] += q['reserved_quantity']
            loc['disponivel'] += q['available']
            lote = q['lote'] or '(sem lote)'
            kk = (lote, q['lot_id'])
            lt = por_lote.setdefault(kk, {
                'lote': lote, 'lot_id': q['lot_id'], 'qty': 0.0,
                'reservada': 0.0, 'disponivel': 0.0,
                'is_migracao': 'MIGRA' in lote.upper()})
            lt['qty'] += q['quantity']; lt['reservada'] += q['reserved_quantity']
            lt['disponivel'] += q['available']
        ks = ('qty', 'reservada', 'disponivel')
        _round = lambda d: {**d, **{k: round(d[k], 6) for k in ks}}
        return jsonify({
            'success': True, 'produto': produto,
            'por_local': [_round(v) for v in por_local.values()],
            'por_lote': [_round(v) for v in por_lote.values()],
            'reservada_total': round(reservada_total, 6)})
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_dados_codigo erro: {e}')
        return jsonify({'success': False, 'message': f'Erro ao consultar Odoo: {e}'}), 200


@estoque_bp.route('/transferencia-estoque/api/autocomplete/produto')
@login_required
@require_admin_json
def api_te_ac_produto():
    """Autocomplete de produto por default_code OU name (ilike). Min 2 chars."""
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])
    try:
        odoo = get_odoo_connection()
        rows = odoo.search_read(
            'product.product',
            ['&', ['active', '=', True], '|',
             ['default_code', 'ilike', q], ['name', 'ilike', q]],
            ['id', 'default_code', 'name', 'tracking'], limit=20)
        out = [{'product_id': r['id'], 'cod': r['default_code'],
                'name': r['name'], 'tracking': r.get('tracking') or 'none',
                'label': f"{r['default_code']} — {r['name']}"}
               for r in rows if r.get('default_code')]
        return jsonify(out)
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_ac_produto erro: {e}')
        return jsonify([])


@estoque_bp.route('/transferencia-estoque/api/autocomplete/local')
@login_required
@require_admin_json
def api_te_ac_local():
    """Autocomplete de stock.location internas da empresa (ilike complete_name)."""
    q = (request.args.get('q') or '').strip()
    empresa = (request.args.get('empresa') or '').strip().upper()
    try:
        info = resolver_empresa(empresa)
    except ValueError:
        return jsonify([])
    try:
        odoo = get_odoo_connection()
        domain = [['company_id', '=', info['company_id']],
                  ['usage', '=', 'internal'], ['active', '=', True]]
        if q:
            domain.append(['complete_name', 'ilike', q])
        rows = odoo.search_read('stock.location', domain,
                                ['id', 'complete_name'], limit=30)
        return jsonify([{'location_id': r['id'], 'complete_name': r['complete_name'],
                         'label': r['complete_name']} for r in rows])
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_ac_local erro: {e}')
        return jsonify([])

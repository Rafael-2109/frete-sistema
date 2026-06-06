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
from app.odoo.estoque._utils import EMPRESAS, resolver_empresa, resolver_produto
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.estoque.scripts.consulta_quant import StockQuantQueryService
from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.estoque.scripts.transfer import StockInternalTransferService
from app.odoo.services.transferencia_saldo_codigo_service import (
    TransferenciaSaldoCodigoService,
)

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


# ---------------------------------------------------------------------------
# Simular / Executar — dispatcher dos 3 modos
# ---------------------------------------------------------------------------

def _fmt_origem(qa, qp, cod, lote):
    return {'label': f"{cod} / {lote or '(sem lote)'}", 'antes': qa, 'apos': qp}


def _fmt_destino(qa, qp, cod, lote, lote_criado=False):
    return {'label': f"{cod} / {lote or '(sem lote)'}", 'antes': qa, 'apos': qp,
            'lote_criado': lote_criado}


def _fmt_atomo12(r, cod, lote_o, lote_d, lote_criado=False):
    """Resultado de transferir_entre_locations/lotes_v2 → contrato de UI."""
    red = r.get('reducao_origem') or {}
    aum = r.get('aumento_destino') or {}
    ok = r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    return {
        'success': ok, 'status': r['status'], 'aviso_par': False,
        'preview': {
            'origem': _fmt_origem(red.get('qty_antes'), red.get('qty_apos'), cod, lote_o),
            'destino': _fmt_destino(aum.get('qty_antes'), aum.get('qty_apos'),
                                    cod, lote_d, lote_criado)},
        'message': r['status'] if ok else f"Falha: {r.get('erro') or r['status']}",
        'resultado': r}


def _fmt_v2(r):
    """Resultado de transferir_v2 (Modo 3) → contrato de UI."""
    ok = r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    return {
        'success': ok, 'status': r['status'], 'aviso_par': r.get('aviso_par', False),
        'preview': {
            'origem': _fmt_origem(r.get('origem_antes'), r.get('origem_apos'),
                                  r['cod_origem'], r.get('lote_nome_origem')),
            'destino': _fmt_destino(r.get('destino_antes'), r.get('destino_apos'),
                                    r['cod_destino'], r.get('lote_nome_destino'),
                                    r.get('lote_criado', False))},
        'message': r['status'] if ok else f"Falha: {r.get('erro') or r['status']}",
        'resultado': r}


def _despachar_transferencia(data, dry_run, usuario):
    """Dispatcher dos 3 modos. Levanta ValueError em erro de uso/dado."""
    modo = str(data.get('modo'))
    empresa = (data.get('empresa') or '').strip().upper()
    cod_origem = str(data.get('cod_origem') or '').strip()
    qty = float(data.get('qty') or 0)
    if qty <= 0:
        raise ValueError('Quantidade deve ser > 0')
    company_id = resolver_empresa(empresa)['company_id']
    odoo = get_odoo_connection()
    lot_svc = StockLotService(odoo=odoo)

    if modo == '1':  # local -> local (mesmo código, mesmo lote)
        prod = resolver_produto(odoo, cod_origem)
        if not prod:
            raise ValueError(f'Codigo {cod_origem} nao encontrado')
        lote = (data.get('lote_nome') or '').strip() or None
        lot_id = lot_svc.buscar_por_nome(lote, prod['pid'], company_id) if lote else None
        if lote and not lot_id:
            raise ValueError(f'Lote {lote} nao encontrado no produto/empresa')
        svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)
        r = svc.transferir_entre_locations(
            product_id=prod['pid'], company_id=company_id, lot_id=lot_id, qty=qty,
            location_id_origem=int(data['location_id_origem']),
            location_id_destino=int(data['location_id_destino']), dry_run=dry_run)
        return _fmt_atomo12(r, cod_origem, lote, lote)

    if modo == '2':  # lote -> lote (mesmo código, mesmo local)
        prod = resolver_produto(odoo, cod_origem)
        if not prod:
            raise ValueError(f'Codigo {cod_origem} nao encontrado')
        loc_id = int(data['location_id'])
        lote_o = (data.get('lote_nome_origem') or '').strip() or None
        lote_d = (data.get('lote_nome_destino') or '').strip()
        if not lote_d:
            raise ValueError('Lote destino obrigatorio')
        lot_o = lot_svc.buscar_por_nome(lote_o, prod['pid'], company_id) if lote_o else None
        if lote_o and not lot_o:
            raise ValueError(f'Lote origem {lote_o} nao encontrado')
        lot_d = lot_svc.buscar_por_nome(lote_d, prod['pid'], company_id)
        # dry-run com lote destino novo: preview manual (não cria lote)
        if dry_run and lot_d is None:
            from app.odoo.services.stock_quant_adjustment_service import (
                StockQuantAdjustmentService)
            adj = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)
            r_red = adj.ajustar_quant(
                product_id=prod['pid'], company_id=company_id, location_id=loc_id,
                lot_id=lot_o, delta=-qty, delta_esperado=-qty, tolerancia_delta=0.001,
                dry_run=True)
            return _fmt_atomo12({
                'status': r_red['status'] if r_red['status'] != 'DRY_RUN_OK' else 'DRY_RUN_OK',
                'reducao_origem': r_red,
                'aumento_destino': {'qty_antes': 0.0, 'qty_apos': qty}},
                cod_origem, lote_o, lote_d, lote_criado=True)
        lote_criado = False
        if lot_d is None:  # executar real → cria
            lot_d, lote_criado = lot_svc.criar_se_nao_existe(lote_d, prod['pid'], company_id)
        svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)
        r = svc.transferir_entre_lotes_v2(
            product_id=prod['pid'], company_id=company_id, location_id=loc_id, qty=qty,
            lot_id_origem=lot_o, lot_id_destino=lot_d, dry_run=dry_run)
        return _fmt_atomo12(r, cod_origem, lote_o, lote_d, lote_criado=lote_criado)

    if modo == '3':  # código -> código
        cod_destino = str(data.get('cod_destino') or '').strip()
        if not cod_destino:
            raise ValueError('Codigo destino obrigatorio')
        svc3 = TransferenciaSaldoCodigoService(odoo=odoo, lot_svc=lot_svc)
        r = svc3.transferir_v2(
            company_id=company_id, cod_origem=cod_origem,
            location_id_origem=int(data['location_id_origem']),
            lote_nome_origem=(data.get('lote_nome_origem') or '').strip() or None,
            cod_destino=cod_destino,
            location_id_destino=int(data['location_id_destino']),
            lote_nome_destino=(data.get('lote_nome_destino') or '').strip() or None,
            qty=qty, usuario=usuario, dry_run=dry_run)
        return _fmt_v2(r)

    raise ValueError(f'Modo invalido: {modo}')


@estoque_bp.route('/transferencia-estoque/api/simular', methods=['POST'])
@login_required
@require_admin_json
def api_te_simular():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(_despachar_transferencia(data, dry_run=True, usuario=current_user.nome))
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 200
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_simular erro: {e}')
        return jsonify({'success': False, 'message': f'Erro: {e}'}), 200


@estoque_bp.route('/transferencia-estoque/api/executar', methods=['POST'])
@login_required
@require_admin_json
def api_te_executar():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(_despachar_transferencia(data, dry_run=False, usuario=current_user.nome))
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 200
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_executar erro: {e}')
        return jsonify({'success': False, 'message': f'Erro: {e}'}), 200

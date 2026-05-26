"""Drill-down: movimentações Odoo paginadas em nova aba."""
import io
import xlsxwriter
from flask import render_template, request, jsonify, send_file
from flask_login import login_required
from app.inventario import inventario_bp
from app.inventario.services.movimentacoes_odoo_service import (
    MovimentacoesOdooService,
)
from app.utils.auth_decorators import require_admin
from app.utils.json_helpers import sanitize_for_json


def _build_filtros(args):
    return {
        'cod': args.get('cod'),
        'empresa': args.get('empresa'),
        'tipo': args.get('tipo'),
        'data_inicio': args.get('data_inicio'),
        'data_fim': args.get('data_fim'),
        'origem': args.get('origem'),
        'destino': args.get('destino'),
        'usuario': args.get('usuario'),
        'page': args.get('page', 1, type=int),
        'page_size': args.get('page_size', 100, type=int),
    }


@inventario_bp.route('/movimentacoes', endpoint='movimentacoes')
@login_required
@require_admin
def movimentacoes():
    filtros = _build_filtros(request.args)
    return render_template('inventario/movimentacoes.html', filtros=filtros)


@inventario_bp.route('/movimentacoes/api', endpoint='movimentacoes_api')
@login_required
@require_admin
def movimentacoes_api():
    filtros = _build_filtros(request.args)
    resultado = MovimentacoesOdooService.buscar_paginado(filtros)
    return jsonify(sanitize_for_json(resultado))


@inventario_bp.route('/movimentacoes/export.xlsx',
                      endpoint='movimentacoes_export')
@login_required
@require_admin
def movimentacoes_export():
    filtros = _build_filtros(request.args)
    filtros['page_size'] = 1000
    todas = []
    for p in range(1, 6):
        filtros['page'] = p
        r = MovimentacoesOdooService.buscar_paginado(filtros)
        todas.extend(r.get('rows', []))
        if len(r.get('rows', [])) < 1000:
            break

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {'in_memory': True})
    ws = wb.add_worksheet('Movimentacoes')
    headers = ['data', 'empresa', 'cod', 'produto', 'lote', 'qtd',
               'origem', 'destino', 'usuario']
    hfmt = wb.add_format({'bold': True, 'bg_color': '#E0E0E0', 'border': 1})
    for i, h in enumerate(headers):
        ws.write(0, i, h, hfmt)
    nfmt = wb.add_format({'num_format': '#,##0.000'})
    for r, row in enumerate(todas, start=1):
        ws.write(r, 0, row.get('data') or '')
        ws.write(r, 1, row.get('empresa') or '')
        ws.write(r, 2, row.get('cod') or '')
        ws.write(r, 3, row.get('produto') or '')
        ws.write(r, 4, row.get('lote') or '')
        ws.write_number(r, 5, float(row.get('qtd') or 0), nfmt)
        ws.write(r, 6, row.get('origem') or '')
        ws.write(r, 7, row.get('destino') or '')
        ws.write(r, 8, row.get('usuario') or '')
    wb.close()
    return send_file(
        io.BytesIO(buf.getvalue()),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='MOVIMENTACOES_ODOO.xlsx',
    )

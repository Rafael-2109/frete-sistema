"""Tela principal Relatório de Confronto + export XLSX."""
import io
from flask import render_template, jsonify, redirect, url_for, send_file
from flask_login import login_required
from app.inventario import inventario_bp
from app.inventario.models import CicloInventario, InventarioSnapshotOdoo
from app.inventario.services.confronto_service import ConfrontoService
from app.inventario.services.export_xlsx_service import ExportXlsxService
from app.utils.json_helpers import sanitize_for_json


@inventario_bp.route('/confronto', endpoint='confronto_index')
@login_required
def index():
    ultimo = (CicloInventario.query.filter_by(status='ATIVO')
              .order_by(CicloInventario.criado_em.desc()).first())
    if ultimo is None:
        return redirect(url_for('inventario.listar_ciclos'))
    return redirect(url_for('inventario.confronto_por_id', ciclo_id=ultimo.id))


@inventario_bp.route('/confronto/<int:ciclo_id>', endpoint='confronto_por_id')
@login_required
def por_id(ciclo_id):
    ciclo = CicloInventario.query.get_or_404(ciclo_id)
    snap_first = (InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo.id)
                  .order_by(InventarioSnapshotOdoo.refresh_em.desc()).first())
    last_refresh = snap_first.refresh_em if snap_first else None
    return render_template('inventario/confronto.html',
                            ciclo=ciclo, last_refresh=last_refresh)


@inventario_bp.route('/confronto/<int:ciclo_id>/api', endpoint='confronto_api')
@login_required
def api(ciclo_id):
    CicloInventario.query.get_or_404(ciclo_id)
    linhas = ConfrontoService.montar_linhas(ciclo_id)
    return jsonify(sanitize_for_json({'linhas': linhas, 'total': len(linhas)}))


@inventario_bp.route('/confronto/<int:ciclo_id>/export.xlsx',
                      endpoint='confronto_export')
@login_required
def export_xlsx(ciclo_id):
    ciclo = CicloInventario.query.get_or_404(ciclo_id)
    blob = ExportXlsxService.gerar(ciclo_id)
    return send_file(
        io.BytesIO(blob),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'CONFRONTO_INVENTARIO_{ciclo.codigo}.xlsx',
    )

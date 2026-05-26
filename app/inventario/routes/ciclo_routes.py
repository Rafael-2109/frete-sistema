"""CRUD CicloInventario + upload XLSX de inventário base."""
from datetime import datetime, date
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.inventario import inventario_bp
from app.inventario.models import CicloInventario
from app.inventario.services.inventario_loader import InventarioLoader
from app.utils.json_helpers import sanitize_for_json


def _user_nome():
    try:
        return getattr(current_user, 'nome', None) or getattr(current_user, 'email', 'unknown')
    except Exception:
        return 'unknown'


@inventario_bp.route('/ciclos', endpoint='listar_ciclos')
@login_required
def listar_ciclos():
    ciclos = CicloInventario.query.order_by(CicloInventario.criado_em.desc()).all()
    return render_template('inventario/ciclos.html', ciclos=ciclos)


@inventario_bp.route('/ciclos/novo', methods=['POST'], endpoint='criar_ciclo')
@login_required
def criar_ciclo():
    codigo = (request.form.get('codigo') or '').strip()
    data_str = (request.form.get('data_snapshot') or '').strip()
    descricao = (request.form.get('descricao') or '').strip() or None
    if not codigo or not data_str:
        return jsonify({'erro': 'codigo e data_snapshot obrigatórios'}), 400
    try:
        d = (datetime.fromisoformat(data_str).date() if 'T' in data_str
             else date.fromisoformat(data_str))
    except ValueError:
        return jsonify({'erro': 'data_snapshot inválida (ISO YYYY-MM-DD)'}), 400
    if CicloInventario.query.filter_by(codigo=codigo).first():
        return jsonify({'erro': f'codigo {codigo} já existe'}), 409
    c = CicloInventario(
        codigo=codigo, data_snapshot=d, descricao=descricao,
        status='ATIVO', criado_por=_user_nome(),
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(sanitize_for_json({'id': c.id, 'codigo': c.codigo})), 201


@inventario_bp.route('/ciclos/<int:ciclo_id>/upload', methods=['POST'],
                      endpoint='upload_xlsx')
@login_required
def upload_xlsx(ciclo_id):
    ciclo = CicloInventario.query.get_or_404(ciclo_id)
    if 'arquivo' not in request.files:
        return jsonify({'erro': 'arquivo ausente'}), 400
    f = request.files['arquivo']
    if not (f.filename or '').lower().endswith('.xlsx'):
        return jsonify({'erro': 'envie .xlsx'}), 400
    try:
        resultado = InventarioLoader.carregar(
            ciclo.id, f.stream, criado_por=_user_nome())
        db.session.commit()
        return jsonify(sanitize_for_json(resultado))
    except Exception as exc:
        db.session.rollback()
        return jsonify({'erro': str(exc)}), 500


@inventario_bp.route('/ciclos/<int:ciclo_id>/arquivar', methods=['POST'],
                      endpoint='arquivar_ciclo')
@login_required
def arquivar_ciclo(ciclo_id):
    c = CicloInventario.query.get_or_404(ciclo_id)
    c.status = 'ARQUIVADO'
    db.session.commit()
    return jsonify({'ok': True})

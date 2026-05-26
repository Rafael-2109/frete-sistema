"""CRUD AjusteManualInventario."""
from decimal import Decimal, InvalidOperation
from flask import request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.inventario import inventario_bp
from app.inventario.models import AjusteManualInventario, CicloInventario
from app.utils.json_helpers import sanitize_for_json


def _user_nome():
    try:
        return getattr(current_user, 'nome', None) or getattr(current_user, 'email', 'unknown')
    except Exception:
        return 'unknown'


@inventario_bp.route('/ajustes/<int:ciclo_id>', endpoint='listar_ajustes')
@login_required
def listar_ajustes(ciclo_id):
    CicloInventario.query.get_or_404(ciclo_id)
    rows = AjusteManualInventario.query.filter_by(ciclo_id=ciclo_id).order_by(
        AjusteManualInventario.criado_em.desc()).all()
    return render_template('inventario/ajustes_manuais.html',
                            ciclo_id=ciclo_id, ajustes=rows)


@inventario_bp.route('/ajustes/<int:ciclo_id>', methods=['POST'],
                      endpoint='criar_ajuste')
@login_required
def criar_ajuste(ciclo_id):
    CicloInventario.query.get_or_404(ciclo_id)
    cod = (request.form.get('cod_produto') or '').strip()
    qtd_str = (request.form.get('qtd') or '').strip()
    if not cod or not qtd_str:
        return jsonify({'erro': 'cod_produto e qtd obrigatórios'}), 400
    try:
        qtd = Decimal(qtd_str)
    except InvalidOperation:
        return jsonify({'erro': 'qtd inválida'}), 400
    a = AjusteManualInventario(
        ciclo_id=ciclo_id, cod_produto=cod,
        nome_produto=(request.form.get('nome_produto') or '').strip() or None,
        local=(request.form.get('local') or '').strip() or None,
        qtd=qtd,
        tipo_ajuste=(request.form.get('tipo_ajuste') or '').strip() or None,
        observacao=(request.form.get('observacao') or '').strip() or None,
        criado_por=_user_nome(),
    )
    db.session.add(a)
    db.session.commit()
    return jsonify(sanitize_for_json({'id': a.id})), 201


@inventario_bp.route('/ajustes/<int:ciclo_id>/<int:aj_id>', methods=['PUT'],
                      endpoint='editar_ajuste')
@login_required
def editar_ajuste(ciclo_id, aj_id):
    a = AjusteManualInventario.query.filter_by(id=aj_id, ciclo_id=ciclo_id).first_or_404()
    data = request.form
    if 'qtd' in data:
        try:
            a.qtd = Decimal(data['qtd'])
        except InvalidOperation:
            return jsonify({'erro': 'qtd inválida'}), 400
    for f in ('cod_produto', 'nome_produto', 'local', 'tipo_ajuste', 'observacao'):
        if f in data:
            setattr(a, f, (data[f] or '').strip() or None)
    db.session.commit()
    return jsonify({'ok': True})


@inventario_bp.route('/ajustes/<int:ciclo_id>/<int:aj_id>', methods=['DELETE'],
                      endpoint='deletar_ajuste')
@login_required
def deletar_ajuste(ciclo_id, aj_id):
    a = AjusteManualInventario.query.filter_by(id=aj_id, ciclo_id=ciclo_id).first_or_404()
    db.session.delete(a)
    db.session.commit()
    return jsonify({'ok': True})

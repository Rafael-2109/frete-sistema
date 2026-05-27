"""CRUD AjusteManualInventario."""
from decimal import Decimal, InvalidOperation
from flask import request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.inventario import inventario_bp
from app.inventario.models import AjusteManualInventario, CicloInventario
from app.utils.auth_decorators import require_admin
from app.utils.json_helpers import sanitize_for_json


def _user_nome():
    try:
        return getattr(current_user, 'nome', None) or getattr(current_user, 'email', 'unknown')
    except Exception:
        return 'unknown'


@inventario_bp.route('/ajustes/<int:ciclo_id>', endpoint='listar_ajustes')
@login_required
@require_admin
def listar_ajustes(ciclo_id):
    CicloInventario.query.get_or_404(ciclo_id)
    rows = AjusteManualInventario.query.filter_by(ciclo_id=ciclo_id).order_by(
        AjusteManualInventario.criado_em.desc()).all()
    return render_template('inventario/ajustes_manuais.html',
                            ciclo_id=ciclo_id, ajustes=rows)


@inventario_bp.route('/ajustes/<int:ciclo_id>', methods=['POST'],
                      endpoint='criar_ajuste')
@login_required
@require_admin
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
@require_admin
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
@require_admin
def deletar_ajuste(ciclo_id, aj_id):
    a = AjusteManualInventario.query.filter_by(id=aj_id, ciclo_id=ciclo_id).first_or_404()
    db.session.delete(a)
    db.session.commit()
    return jsonify({'ok': True})


@inventario_bp.route('/ajustes/<int:ciclo_id>/upsert', methods=['POST'],
                      endpoint='upsert_ajuste')
@login_required
@require_admin
def upsert_ajuste(ciclo_id):
    """Upsert inline de AJ.LOCAL/AJ.QTD por (ciclo_id, cod_produto).

    Comportamento:
      - qtd vazia ou == 0 -> DELETE TODOS os registros do (ciclo, cod) e retorna {'deleted': N}
      - existe registro -> UPDATE (local, qtd)
      - nao existe -> INSERT
    Recebe form: cod_produto (obrig), local (opcional), qtd (opcional p/ delete).
    """
    CicloInventario.query.get_or_404(ciclo_id)
    cod = (request.form.get('cod_produto') or '').strip()
    if not cod:
        return jsonify({'erro': 'cod_produto obrigatorio'}), 400

    qtd_str = (request.form.get('qtd') or '').strip()
    local = (request.form.get('local') or '').strip() or None
    nome_produto = (request.form.get('nome_produto') or '').strip() or None

    # with_for_update() serializa saves simultaneos para o mesmo (ciclo, cod):
    # 2 requests concorrentes nao criam mais 2 registros (CR HIGH 2026-05-27).
    # Sem UNIQUE constraint na tabela, o lock e' a unica defesa contra duplicacao.
    existentes = (AjusteManualInventario.query
                  .filter_by(ciclo_id=ciclo_id, cod_produto=cod)
                  .with_for_update()
                  .all())

    if not qtd_str:
        deleted = 0
        for a in existentes:
            db.session.delete(a)
            deleted += 1
        db.session.commit()
        return jsonify({'deleted': deleted, 'ok': True})

    try:
        qtd = Decimal(qtd_str)
    except InvalidOperation:
        return jsonify({'erro': 'qtd invalida'}), 400

    if qtd == 0:
        deleted = 0
        for a in existentes:
            db.session.delete(a)
            deleted += 1
        db.session.commit()
        return jsonify({'deleted': deleted, 'ok': True})

    if existentes:
        # Atualiza o mais recente, descarta duplicatas anteriores
        existentes.sort(key=lambda x: x.criado_em, reverse=True)
        a = existentes[0]
        a.local = local
        a.qtd = qtd
        if nome_produto and not a.nome_produto:
            a.nome_produto = nome_produto
        for extra in existentes[1:]:
            db.session.delete(extra)
        db.session.commit()
        return jsonify({'id': a.id, 'ok': True, 'mode': 'update'})

    a = AjusteManualInventario(
        ciclo_id=ciclo_id, cod_produto=cod, nome_produto=nome_produto,
        local=local, qtd=qtd, criado_por=_user_nome(),
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({'id': a.id, 'ok': True, 'mode': 'insert'}), 201

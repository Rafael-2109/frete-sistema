from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required
from app.utils.sincronizar_todas_entregas import sincronizar_todas_entregas

monitoramento_bp = Blueprint('monitoramento', __name__, url_prefix='/monitoramento')

@monitoramento_bp.route('/sincronizar-todas')
@login_required
def sincronizar_todas():
    sincronizar_todas_entregas()
    flash("Sincronização de entregas concluída com sucesso.", "success")
    return redirect(url_for('monitoramento.lista_entregas'))
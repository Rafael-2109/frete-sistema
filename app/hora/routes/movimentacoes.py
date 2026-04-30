"""Hub `/hora/movimentacoes` — agrupa transferencias, emprestimos e avarias.

Tela index com cards convidando a abrir cada operacao. Permissao de cada
card respeita o decorator `tem_perm_hora` correspondente.
"""
from flask import render_template
from flask_login import login_required

from app.hora.routes import hora_bp


@hora_bp.route('/movimentacoes')
@login_required
def movimentacoes_hub():
    return render_template('hora/movimentacoes_hub.html')

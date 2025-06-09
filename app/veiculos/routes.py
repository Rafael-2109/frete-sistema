from flask import Blueprint, render_template
from app.veiculos.models import Veiculo
from flask_login import login_required

veiculos_bp = Blueprint('veiculos', __name__, url_prefix='/veiculos')

@veiculos_bp.route('/consulta')
@login_required
def consulta_veiculos():
    veiculos = Veiculo.query.order_by(Veiculo.peso_maximo.asc()).all()
    return render_template('veiculos/consulta_veiculos.html', veiculos=veiculos)

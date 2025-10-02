from flask import Blueprint

rastreamento_bp = Blueprint('rastreamento', __name__, url_prefix='/rastreamento')

from app.rastreamento import routes

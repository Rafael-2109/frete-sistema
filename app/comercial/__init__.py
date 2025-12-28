from flask import Blueprint

comercial_bp = Blueprint('comercial', __name__, url_prefix='/comercial')

# Importar as rotas para registrar no blueprint
from app.comercial.routes import diretoria
from app.comercial.routes import margem
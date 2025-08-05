# Módulo estoque - blueprint definido em routes.py 
from flask import Blueprint

# IMPORTANTE: Registrar tipos PostgreSQL imediatamente
from app.estoque.pg_register import force_register_global
force_register_global()

estoque_bp = Blueprint('estoque', __name__, url_prefix='/estoque')

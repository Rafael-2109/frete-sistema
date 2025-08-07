# Módulo estoque - blueprint definido em routes.py 
from flask import Blueprint

estoque_bp = Blueprint('estoque', __name__, url_prefix='/estoque')

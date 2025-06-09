from flask import Blueprint

transportadoras_bp = Blueprint('transportadoras', __name__, url_prefix='/transportadoras')

from app.transportadoras import routes
from app.transportadoras import models, forms

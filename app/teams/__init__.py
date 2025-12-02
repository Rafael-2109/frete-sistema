from flask import Blueprint

teams_bp = Blueprint('teams', __name__, url_prefix='/api/teams')

from app.teams import routes

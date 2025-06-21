from flask import Blueprint

claude_ai_bp = Blueprint('claude_ai', __name__, url_prefix='/claude-ai')

# Import routes to register them with the blueprint
from . import routes 
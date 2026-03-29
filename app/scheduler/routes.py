"""
Routes: Scheduler Health Dashboard
===================================

Dashboard para monitorar saude do scheduler.
Acessivel apenas para administradores.
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required

scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/admin/scheduler')


@scheduler_bp.route('/health')
@login_required
def health_dashboard():
    """Dashboard de saude do scheduler."""
    from app.scheduler.health_service import obter_status_steps
    steps = obter_status_steps()
    return render_template('scheduler/health.html', steps=steps)


@scheduler_bp.route('/health/api')
@login_required
def health_api():
    """API JSON com status dos steps."""
    from app.scheduler.health_service import obter_status_steps
    return jsonify({'steps': obter_status_steps()})

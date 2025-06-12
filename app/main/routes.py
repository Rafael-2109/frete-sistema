from flask import Blueprint, render_template, redirect, url_for, send_from_directory, current_app
from flask_login import current_user, login_required
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
@main_bp.route('/main/dashboard')
@login_required
def dashboard():
    return render_template('main/dashboard.html', usuario=current_user)

@main_bp.route('/')
def home():
    return redirect(url_for('auth.login'))

@main_bp.route('/favicon.ico')
def favicon():
    """Rota para o favicon.ico para evitar erros 404"""
    try:
        # Tenta servir favicon.ico da pasta static se existir
        static_dir = os.path.join(current_app.root_path, 'static')
        if os.path.exists(os.path.join(static_dir, 'favicon.ico')):
            return send_from_directory(static_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except:
        pass
    
    # Se não encontrar, retorna resposta vazia
    from flask import Response
    return Response('', status=204, mimetype='image/vnd.microsoft.icon')

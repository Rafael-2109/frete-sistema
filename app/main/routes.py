from flask import Blueprint
from flask import render_template
from flask import redirect
from flask import url_for

from flask_login import current_user
from flask_login import login_required
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
@main_bp.route('/main/dashboard')
@login_required
def dashboard():
    return render_template('main/dashboard.html', usuario=current_user)

@main_bp.route('/')
def home():
    return redirect(url_for('auth.login'))

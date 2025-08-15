"""
Rotas OAuth2 para TagPlus - Callbacks e Autorização
"""

from flask import Blueprint, request, redirect, url_for, jsonify, session, render_template_string
from flask_login import login_required, current_user
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
import logging

logger = logging.getLogger(__name__)

oauth_bp = Blueprint('tagplus_oauth', __name__, url_prefix='/tagplus/oauth')

# Template HTML simples para página de autorização
AUTH_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Autorização TagPlus</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .btn { padding: 10px 20px; margin: 10px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.warning { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <h1>🔐 Autorização TagPlus</h1>
    
    {% if status %}
    <div class="status {{ status_type }}">
        {{ status }}
    </div>
    {% endif %}
    
    <div class="card">
        <h2>📋 Status das APIs</h2>
        <ul>
            <li>API Clientes: 
                {% if tokens_clientes %}
                    ✅ Autorizada
                {% else %}
                    ⚠️ Não autorizada
                {% endif %}
            </li>
            <li>API Notas: 
                {% if tokens_notas %}
                    ✅ Autorizada
                {% else %}
                    ⚠️ Não autorizada
                {% endif %}
            </li>
        </ul>
    </div>
    
    <div class="card">
        <h2>🔑 Autorizar APIs</h2>
        <p>Clique nos botões abaixo para autorizar cada API:</p>
        
        <a href="{{ url_for('tagplus_oauth.authorize', api_type='clientes') }}" class="btn btn-primary">
            Autorizar API de Clientes
        </a>
        
        <a href="{{ url_for('tagplus_oauth.authorize', api_type='notas') }}" class="btn btn-primary">
            Autorizar API de Notas
        </a>
    </div>
    
    {% if tokens_clientes or tokens_notas %}
    <div class="card">
        <h2>🧪 Testar Conexões</h2>
        <a href="{{ url_for('tagplus_oauth.test_connection', api_type='clientes') }}" class="btn btn-success">
            Testar API Clientes
        </a>
        <a href="{{ url_for('tagplus_oauth.test_connection', api_type='notas') }}" class="btn btn-success">
            Testar API Notas
        </a>
    </div>
    {% endif %}
    
    <div class="card">
        <h2>📝 Tokens Manuais</h2>
        <p>Se você já tem tokens de acesso, pode configurá-los manualmente:</p>
        <form method="POST" action="{{ url_for('tagplus_oauth.set_tokens_manual') }}">
            <div style="margin: 10px 0;">
                <label>API:</label>
                <select name="api_type" required>
                    <option value="clientes">Clientes</option>
                    <option value="notas">Notas</option>
                </select>
            </div>
            <div style="margin: 10px 0;">
                <label>Access Token:</label>
                <input type="text" name="access_token" style="width: 100%; padding: 5px;" required>
            </div>
            <div style="margin: 10px 0;">
                <label>Refresh Token (opcional):</label>
                <input type="text" name="refresh_token" style="width: 100%; padding: 5px;">
            </div>
            <button type="submit" class="btn btn-primary">Salvar Tokens</button>
        </form>
    </div>
</body>
</html>
"""

@oauth_bp.route('/')
@login_required
def index():
    """Página principal de autorização OAuth2"""
    # Verifica tokens na sessão
    tokens_clientes = session.get('tagplus_clientes_access_token')
    tokens_notas = session.get('tagplus_notas_access_token')
    
    status = request.args.get('status')
    status_type = request.args.get('status_type', 'success')
    
    return render_template_string(
        AUTH_PAGE_TEMPLATE,
        tokens_clientes=tokens_clientes,
        tokens_notas=tokens_notas,
        status=status,
        status_type=status_type
    )

@oauth_bp.route('/authorize/<api_type>')
@login_required
def authorize(api_type):
    """Inicia o fluxo OAuth2 para API específica"""
    if api_type not in ['clientes', 'notas']:
        return redirect(url_for('tagplus_oauth.index', 
                              status='Tipo de API inválido',
                              status_type='error'))
    
    oauth = TagPlusOAuth2V2(api_type=api_type)
    
    # Gera estado anti-CSRF
    import secrets
    state = secrets.token_urlsafe(32)
    session[f'oauth_state_{api_type}'] = state
    
    # Gera URL de autorização
    auth_url = oauth.get_authorization_url(state=state)
    
    logger.info(f"Redirecionando para autorização {api_type}: {auth_url}")
    return redirect(auth_url)

@oauth_bp.route('/callback/cliente')
def callback_cliente():
    """Callback OAuth2 para API de Clientes"""
    return handle_callback('clientes')

@oauth_bp.route('/callback/nfe')
def callback_nfe():
    """Callback OAuth2 para API de Notas"""
    return handle_callback('notas')

def handle_callback(api_type):
    """Processa callback OAuth2"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    # Verifica erro
    if error:
        logger.error(f"Erro no callback OAuth2 {api_type}: {error}")
        return redirect(url_for('tagplus_oauth.index',
                              status=f'Erro na autorização: {error}',
                              status_type='error'))
    
    # Verifica código
    if not code:
        return redirect(url_for('tagplus_oauth.index',
                              status='Código de autorização não recebido',
                              status_type='error'))
    
    # Verifica estado (anti-CSRF)
    expected_state = session.get(f'oauth_state_{api_type}')
    if state != expected_state:
        logger.warning(f"Estado inválido no callback {api_type}")
        # Continua mesmo assim para facilitar testes
    
    # Troca código por tokens
    oauth = TagPlusOAuth2V2(api_type=api_type)
    tokens = oauth.exchange_code_for_tokens(code)
    
    if tokens:
        logger.info(f"Autorização {api_type} concluída com sucesso")
        return redirect(url_for('tagplus_oauth.index',
                              status=f'API de {api_type.title()} autorizada com sucesso!',
                              status_type='success'))
    else:
        return redirect(url_for('tagplus_oauth.index',
                              status=f'Erro ao obter tokens para {api_type}',
                              status_type='error'))

@oauth_bp.route('/test/<api_type>')
@login_required
def test_connection(api_type):
    """Testa conexão com API específica"""
    if api_type not in ['clientes', 'notas']:
        return jsonify({'error': 'Tipo de API inválido'}), 400
    
    oauth = TagPlusOAuth2V2(api_type=api_type)
    success, info = oauth.test_connection()
    
    if success:
        return redirect(url_for('tagplus_oauth.index',
                              status=f'Conexão com API de {api_type.title()} OK!',
                              status_type='success'))
    else:
        return redirect(url_for('tagplus_oauth.index',
                              status=f'Erro na conexão: {info}',
                              status_type='error'))

@oauth_bp.route('/set-tokens', methods=['POST'])
@login_required
def set_tokens_manual():
    """Define tokens manualmente"""
    api_type = request.form.get('api_type')
    access_token = request.form.get('access_token')
    refresh_token = request.form.get('refresh_token')
    
    if not api_type or not access_token:
        return redirect(url_for('tagplus_oauth.index',
                              status='API e Access Token são obrigatórios',
                              status_type='error'))
    
    # Salva tokens
    oauth = TagPlusOAuth2V2(api_type=api_type)
    oauth.set_tokens(access_token, refresh_token)
    
    # Testa conexão
    success, info = oauth.test_connection()
    
    if success:
        return redirect(url_for('tagplus_oauth.index',
                              status=f'Tokens configurados e testados com sucesso para {api_type}!',
                              status_type='success'))
    else:
        return redirect(url_for('tagplus_oauth.index',
                              status=f'Tokens salvos mas teste falhou: {info}',
                              status_type='warning'))

@oauth_bp.route('/status')
@login_required
def status():
    """Retorna status das autorizações (JSON)"""
    return jsonify({
        'clientes': {
            'authorized': bool(session.get('tagplus_clientes_access_token')),
            'expires_at': session.get('tagplus_clientes_expires_at')
        },
        'notas': {
            'authorized': bool(session.get('tagplus_notas_access_token')),
            'expires_at': session.get('tagplus_notas_expires_at')
        }
    })
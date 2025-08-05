"""
Fluxo OAuth2 completo para TagPlus
"""

from flask import Blueprint, request, redirect, url_for, session, flash, render_template_string
import requests
import logging
from .config import TAGPLUS_CONFIG, get_config

logger = logging.getLogger(__name__)

tagplus_oauth_bp = Blueprint('tagplus_oauth', __name__, url_prefix='/tagplus/oauth')

# Template HTML simples para autorização
OAUTH_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Autorização TagPlus</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 600px; margin: 0 auto; }
        .success { color: green; }
        .error { color: red; }
        .info { background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
        code { background: #f5f5f5; padding: 2px 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Integração TagPlus OAuth2</h1>
        
        {% if access_token %}
            <div class="success">
                <h2>✅ Autorização Concluída!</h2>
                <div class="info">
                    <p><strong>Access Token:</strong> <code>{{ access_token[:20] }}...</code></p>
                    {% if refresh_token %}
                    <p><strong>Refresh Token:</strong> <code>{{ refresh_token[:20] }}...</code></p>
                    {% endif %}
                    <p><strong>Expira em:</strong> {{ expires_in }} segundos</p>
                </div>
                <p>Tokens salvos com sucesso! Você já pode usar a integração.</p>
            </div>
        {% elif error %}
            <div class="error">
                <h2>❌ Erro na Autorização</h2>
                <p>{{ error }}</p>
            </div>
        {% else %}
            <h2>Autorizar Aplicação</h2>
            <p>Para integrar com o TagPlus, você precisa autorizar nosso aplicativo.</p>
            
            <div class="info">
                <p><strong>Client ID:</strong> <code>{{ client_id }}</code></p>
                <p><strong>Redirect URI:</strong> <code>{{ redirect_uri }}</code></p>
            </div>
            
            <h3>Opção 1: Fluxo OAuth2 (Recomendado)</h3>
            <p>Clique no botão abaixo para ser redirecionado ao TagPlus:</p>
            <form action="{{ url_for('tagplus_oauth.authorize') }}" method="get">
                <button type="submit">Autorizar no TagPlus</button>
            </form>
            
            <h3>Opção 2: Código de Autorização Manual</h3>
            <p>Se você já tem um código de autorização, cole aqui:</p>
            <form action="{{ url_for('tagplus_oauth.callback') }}" method="get">
                <input type="text" name="code" placeholder="Código de autorização" size="40">
                <button type="submit">Trocar por Token</button>
            </form>
            
            <h3>Opção 3: Token Manual</h3>
            <p>Se você já tem um access token, cole aqui:</p>
            <form action="{{ url_for('tagplus_oauth.save_token') }}" method="post">
                <input type="text" name="access_token" placeholder="Access Token" size="40"><br><br>
                <input type="text" name="refresh_token" placeholder="Refresh Token (opcional)" size="40"><br><br>
                <button type="submit">Salvar Tokens</button>
            </form>
        {% endif %}
        
        <hr>
        <p><a href="{{ url_for('tagplus.importar') }}">Voltar para Importação</a></p>
    </div>
</body>
</html>
'''

@tagplus_oauth_bp.route('/')
def index():
    """Página inicial do fluxo OAuth"""
    return render_template_string(
        OAUTH_TEMPLATE,
        client_id=get_config('client_id'),
        redirect_uri=url_for('tagplus_oauth.callback', _external=True),
        access_token=session.get('tagplus_access_token'),
        refresh_token=session.get('tagplus_refresh_token'),
        expires_in=session.get('tagplus_expires_in')
    )

@tagplus_oauth_bp.route('/authorize')
def authorize():
    """Redireciona para página de autorização do TagPlus"""
    # URLs possíveis de autorização
    auth_urls = [
        "https://api.tagplus.com.br/oauth/authorize",
        "https://developers.tagplus.com.br/oauth/authorize",
        "https://app.tagplus.com.br/oauth/authorize"
    ]
    
    # Usar a primeira URL por padrão
    auth_url = auth_urls[0]
    
    # Parâmetros OAuth2
    params = {
        'client_id': get_config('client_id'),
        'redirect_uri': url_for('tagplus_oauth.callback', _external=True),
        'response_type': 'code',
        'scope': 'read:clientes write:clientes read:nfes read:produtos'
    }
    
    # Construir URL completa
    from urllib.parse import urlencode
    full_url = f"{auth_url}?{urlencode(params)}"
    
    logger.info(f"Redirecionando para: {full_url}")
    return redirect(full_url)

@tagplus_oauth_bp.route('/callback')
def callback():
    """Callback do OAuth2 - recebe o código e troca por token"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return render_template_string(
            OAUTH_TEMPLATE,
            error=f"Erro do TagPlus: {error}"
        )
    
    if not code:
        return render_template_string(
            OAUTH_TEMPLATE,
            error="Código de autorização não fornecido"
        )
    
    # Trocar código por token
    token_urls = [
        "https://api.tagplus.com.br/oauth/token",
        "https://developers.tagplus.com.br/oauth/token",
        "https://oauth2.tagplus.com.br/token"
    ]
    
    for token_url in token_urls:
        try:
            response = requests.post(
                token_url,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'client_id': get_config('client_id'),
                    'client_secret': get_config('client_secret'),
                    'redirect_uri': url_for('tagplus_oauth.callback', _external=True)
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            logger.info(f"Token response from {token_url}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Salvar tokens na sessão
                    session['tagplus_access_token'] = data.get('access_token')
                    session['tagplus_refresh_token'] = data.get('refresh_token')
                    session['tagplus_expires_in'] = data.get('expires_in', 3600)
                    
                    flash('Autorização concluída com sucesso!', 'success')
                    
                    return render_template_string(
                        OAUTH_TEMPLATE,
                        access_token=data.get('access_token'),
                        refresh_token=data.get('refresh_token'),
                        expires_in=data.get('expires_in', 3600)
                    )
                except:
                    logger.error(f"Resposta não é JSON: {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"Erro ao trocar código por token em {token_url}: {e}")
    
    return render_template_string(
        OAUTH_TEMPLATE,
        error="Não foi possível obter o access token. Verifique os logs."
    )

@tagplus_oauth_bp.route('/save_token', methods=['POST'])
def save_token():
    """Salva tokens fornecidos manualmente"""
    access_token = request.form.get('access_token')
    refresh_token = request.form.get('refresh_token')
    
    if not access_token:
        return render_template_string(
            OAUTH_TEMPLATE,
            error="Access token é obrigatório"
        )
    
    # Salvar na sessão
    session['tagplus_access_token'] = access_token
    session['tagplus_refresh_token'] = refresh_token
    session['tagplus_expires_in'] = 86400  # 24 horas padrão
    
    flash('Tokens salvos com sucesso!', 'success')
    
    return render_template_string(
        OAUTH_TEMPLATE,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=86400
    )
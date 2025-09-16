"""
Rotas para gerenciamento de sessão do Portal Sendas
"""

import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import requests
from functools import wraps
import logging

logger = logging.getLogger(__name__)
# Blueprint
sendas_bp = Blueprint('sendas', __name__, url_prefix='/portal/sendas')

# Diretório para salvar sessões
SESSION_DIR = os.path.join(os.path.dirname(__file__), 'sessions')
os.makedirs(SESSION_DIR, exist_ok=True)

# Arquivos de sessão
COOKIES_FILE = os.path.join(SESSION_DIR, 'sendas_cookies.json')
SESSION_FILE = os.path.join(SESSION_DIR, 'sendas_session.json')


def admin_required(f):
    """Decorator para requerer acesso admin"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Aqui você pode adicionar verificação de admin se necessário
        # Por enquanto, apenas login_required
        return f(*args, **kwargs)
    return decorated_function


@sendas_bp.route('/sessao')
@admin_required
def gerenciar_sessao():
    """Página para gerenciar sessão do Sendas"""
    
    # Verificar se existe sessão salva
    sessao_atual = None
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                sessao_atual = json.load(f)
        except Exception as e:
            sessao_atual = None
    
    return render_template('portal/sendas_sessao.html', sessao=sessao_atual)


@sendas_bp.route('/sessao/salvar', methods=['POST'])
@admin_required
def salvar_sessao():
    """Salva cookies e tokens do Sendas"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Dados não fornecidos'}), 400
        
        # Processar cookies
        cookies_raw = data.get('cookies', '')
        tokens = data.get('tokens', {})
        local_storage = data.get('localStorage', {})
        
        # Parse cookies se vier como string
        cookies = []
        if cookies_raw:
            if isinstance(cookies_raw, str):
                # Se for string de cookies do navegador (formato: "name=value; name2=value2")
                if '; ' in cookies_raw:
                    for cookie_str in cookies_raw.split('; '):
                        parts = cookie_str.split('=', 1)
                        if len(parts) == 2:
                            cookies.append({
                                'name': parts[0],
                                'value': parts[1],
                                'domain': '.trizy.com.br',
                                'path': '/',
                                'secure': True
                            })
                # Se for JSON string
                else:
                    try:
                        cookies = json.loads(cookies_raw)
                    except Exception as e:
                        logger.error(f"Erro ao carregar cookies: {e}")
                        pass
            elif isinstance(cookies_raw, list):
                cookies = cookies_raw
        
        # Salvar cookies
        if cookies:
            with open(COOKIES_FILE, 'w') as f:
                json.dump(cookies, f, indent=2)
        
        # Salvar sessão completa
        session_data = {
            'timestamp': datetime.now().isoformat(),
            'cookies': cookies,
            'tokens': tokens,
            'localStorage': local_storage,
            'saved_by': request.remote_addr
        }
        
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Sessão salva com sucesso! {len(cookies)} cookies capturados.',
            'cookies_count': len(cookies)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao salvar: {str(e)}'}), 500


@sendas_bp.route('/sessao/testar', methods=['POST'])
@admin_required
def testar_sessao():
    """Testa se a sessão salva funciona"""
    try:
        if not os.path.exists(COOKIES_FILE):
            return jsonify({'success': False, 'message': 'Nenhuma sessão salva encontrada'}), 404
        
        # Carregar cookies
        with open(COOKIES_FILE, 'r') as f:
            cookies_list = json.load(f)
        
        # Converter para dict e extrair token JWT
        cookies_dict = {}
        access_token = None
        
        for cookie in cookies_list:
            if isinstance(cookie, dict):
                cookie_name = cookie.get('name', '')
                cookie_value = cookie.get('value', '')
                cookies_dict[cookie_name] = cookie_value
                
                # Capturar o access token
                if cookie_name == 'trizy_access_token':
                    access_token = cookie_value
        
        # Fazer requisição de teste
        session = requests.Session()
        
        # Adicionar cookies com domínio correto
        for name, value in cookies_dict.items():
            session.cookies.set(name, value, domain='.trizy.com.br', path='/')
        
        # Headers mais completos para parecer navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://plataforma.trizy.com.br/#/terminal/painel'
        }
        
        # Se temos o token JWT, adicionar Authorization header
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        
        # Tentar acessar o painel do terminal (URL específica onde usuário trabalha)
        response = session.get(
            'https://plataforma.trizy.com.br/#/terminal/painel',
            headers=headers,
            allow_redirects=True,  # Permitir redirecionamento para ver onde vai
            timeout=10
        )
        
        # Verificar resposta
        final_url = response.url
        
        # Log para debug
        logger.info(f"Test response - Status: {response.status_code}, Final URL: {final_url}")
        logger.info(f"Has access_token: {bool(access_token)}")
        
        if response.status_code == 200:
            # Verificar se não foi redirecionado para login
            if 'login' not in final_url.lower() and 'auth' not in final_url.lower():
                # Verificar se está na plataforma ou área autenticada
                if 'plataforma' in final_url.lower() or 'trizy' in final_url.lower():
                    return jsonify({
                        'success': True,
                        'message': 'Sessão válida! Acesso autorizado à plataforma.',
                        'status_code': response.status_code,
                        'url': final_url
                    })
                else:
                    return jsonify({
                        'success': True,
                        'message': f'Sessão válida! Redirecionado para: {final_url}',
                        'status_code': response.status_code,
                        'url': final_url
                    })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Sessão inválida - redirecionado para login',
                    'status_code': response.status_code,
                    'url': final_url
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Status inesperado: {response.status_code}',
                'status_code': response.status_code,
                'url': final_url
            })
            
    except requests.Timeout:
        return jsonify({'success': False, 'message': 'Timeout ao testar sessão'}), 504
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao testar: {str(e)}'}), 500


@sendas_bp.route('/sessao/limpar', methods=['POST'])
@admin_required
def limpar_sessao():
    """Limpa a sessão salva"""
    try:
        # Remover arquivos
        for file in [COOKIES_FILE, SESSION_FILE]:
            if os.path.exists(file):
                os.remove(file)
        
        return jsonify({'success': True, 'message': 'Sessão limpa com sucesso'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao limpar: {str(e)}'}), 500


@sendas_bp.route('/sessao/status', methods=['GET'])
@admin_required
def status_sessao():
    """Retorna status da sessão atual"""
    try:
        if not os.path.exists(SESSION_FILE):
            return jsonify({
                'exists': False,
                'message': 'Nenhuma sessão salva'
            })
        
        with open(SESSION_FILE, 'r') as f:
            session_data = json.load(f)
        
        # Calcular idade da sessão
        timestamp = datetime.fromisoformat(session_data.get('timestamp', ''))
        age_minutes = (datetime.now() - timestamp).total_seconds() / 60
        
        return jsonify({
            'exists': True,
            'timestamp': session_data.get('timestamp'),
            'age_minutes': round(age_minutes, 1),
            'cookies_count': len(session_data.get('cookies', [])),
            'has_tokens': bool(session_data.get('tokens', {})),
            'has_localStorage': bool(session_data.get('localStorage', {}))
        })
        
    except Exception as e:
        return jsonify({
            'exists': False,
            'error': str(e)
        })
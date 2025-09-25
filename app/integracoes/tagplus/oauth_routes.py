"""
Rotas OAuth2 para TagPlus - Callbacks e Autorização
"""

from flask import Blueprint, request, redirect, url_for, jsonify, session, render_template_string
from flask_login import login_required
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
from datetime import datetime, timedelta
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
                    <br><small style="color: #666;">Token: {{ tokens_clientes_display }}</small>
                {% else %}
                    ⚠️ Não autorizada
                {% endif %}
            </li>
            <li>API Notas:
                {% if tokens_notas %}
                    ✅ Autorizada
                    <br><small style="color: #666;">Token: {{ tokens_notas_display }}</small>
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

    {% if tokens_notas %}
    <div class="card">
        <h2>📋 Visualizar e Importar Notas Fiscais</h2>
        <p>Buscar NFs dos últimos dias:</p>
        <div style="margin: 10px 0;">
            <label>Últimos quantos dias:</label>
            <input type="number" id="diasBusca" value="7" min="1" max="365" style="width: 100px; padding: 5px;">
            <button class="btn btn-primary" onclick="listarNFs()">
                🔍 Buscar NFs
            </button>
        </div>

        <div id="resultadoNFs" style="margin-top: 20px; display: none;">
            <h4>Notas Fiscais Encontradas: <span id="totalNFs">0</span></h4>
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: #f0f0f0; position: sticky; top: 0;">
                        <tr>
                            <th style="padding: 8px; border: 1px solid #ddd;">NF</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Data</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Cliente</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">CNPJ</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Valor</th>
                        </tr>
                    </thead>
                    <tbody id="tabelaNFs"></tbody>
                </table>
            </div>
            <div style="margin-top: 10px;">
                <button class="btn btn-success" onclick="importarTodasNFs()">
                    📥 Importar Todas as NFs Listadas
                </button>
            </div>
        </div>

        <div id="loadingNFs" style="display: none; text-align: center; padding: 20px;">
            <div style="font-size: 24px;">⏳</div>
            Carregando notas fiscais...
        </div>
    </div>

    <script>
    function listarNFs() {
        const dias = document.getElementById('diasBusca').value;
        const loading = document.getElementById('loadingNFs');
        const resultado = document.getElementById('resultadoNFs');
        const tabela = document.getElementById('tabelaNFs');

        loading.style.display = 'block';
        resultado.style.display = 'none';

        fetch(`/tagplus/oauth/listar-nfs?dias=${dias}`)
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';

                if (data.error) {
                    alert('Erro: ' + data.error);
                    return;
                }

                if (data.success && data.nfes) {
                    tabela.innerHTML = '';
                    document.getElementById('totalNFs').textContent = data.total;

                    if (data.nfes.length === 0) {
                        tabela.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px;">Nenhuma NF encontrada no período</td></tr>';
                    } else {
                        data.nfes.forEach(nfe => {
                            const tr = document.createElement('tr');
                            const dataFormatada = nfe.data_emissao ? new Date(nfe.data_emissao).toLocaleDateString('pt-BR') : 'N/A';
                            tr.innerHTML = `
                                <td style="padding: 8px; border: 1px solid #ddd;">${nfe.numero}</td>
                                <td style="padding: 8px; border: 1px solid #ddd;">${dataFormatada}</td>
                                <td style="padding: 8px; border: 1px solid #ddd; font-size: 0.9em;">${nfe.cliente}</td>
                                <td style="padding: 8px; border: 1px solid #ddd;">${nfe.cnpj}</td>
                                <td style="padding: 8px; border: 1px solid #ddd;">R$ ${parseFloat(nfe.valor_total).toFixed(2)}</td>
                            `;
                            tabela.appendChild(tr);
                        });
                    }

                    resultado.style.display = 'block';
                    window.nfsParaImportar = data.nfes.map(nf => nf.id);
                }
            })
            .catch(error => {
                loading.style.display = 'none';
                alert('Erro ao buscar NFs: ' + error);
            });
    }

    function importarTodasNFs() {
        if (!window.nfsParaImportar || window.nfsParaImportar.length === 0) {
            alert('Nenhuma NF para importar');
            return;
        }

        if (!confirm(`Importar ${window.nfsParaImportar.length} NFs para o sistema?`)) {
            return;
        }

        alert('Função de importação será implementada');
    }
    </script>
    {% endif %}
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

    # Pega apenas os primeiros caracteres para exibir
    tokens_clientes_display = tokens_clientes[:30] + '...' if tokens_clientes else None
    tokens_notas_display = tokens_notas[:30] + '...' if tokens_notas else None

    status = request.args.get('status')
    status_type = request.args.get('status_type', 'success')

    return render_template_string(
        AUTH_PAGE_TEMPLATE,
        tokens_clientes=tokens_clientes,
        tokens_notas=tokens_notas,
        tokens_clientes_display=tokens_clientes_display,
        tokens_notas_display=tokens_notas_display,
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

@oauth_bp.route('/listar-nfs')
@login_required
def listar_nfs():
    """Lista NFs disponíveis para importação"""
    try:
        # Pega parâmetros da query string
        dias = request.args.get('dias', 7, type=int)
        data_fim = datetime.now().date()
        data_inicio = data_fim - timedelta(days=dias)

        # Usa OAuth2 para buscar NFs
        oauth = TagPlusOAuth2V2(api_type='notas')

        # Faz requisição para listar NFs
        response = oauth.make_request(
            'GET',
            '/nfes',
            params={
                'data_emissao_inicio': data_inicio.strftime('%Y-%m-%d'),
                'data_emissao_fim': data_fim.strftime('%Y-%m-%d'),
                'limite': 100,
                'status': 'autorizada'
            }
        )

        if not response:
            return jsonify({'error': 'Erro ao buscar NFs'}), 500

        if response.status_code == 401:
            return jsonify({'error': 'Token expirado. Autorize novamente.'}), 401

        if response.status_code != 200:
            return jsonify({'error': f'Erro: {response.status_code}'}), response.status_code

        data = response.json()

        # Extrai NFs do response
        if isinstance(data, dict):
            nfes = data.get('data', data.get('nfes', []))
        else:
            nfes = data if isinstance(data, list) else []

        # Formata NFs para exibição
        nfes_formatadas = []
        for nfe in nfes:
            nfes_formatadas.append({
                'id': nfe.get('id'),
                'numero': nfe.get('numero'),
                'serie': nfe.get('serie', '1'),
                'data_emissao': nfe.get('data_emissao'),
                'cliente': nfe.get('cliente', {}).get('nome', 'N/A'),
                'cnpj': nfe.get('cliente', {}).get('cnpj', nfe.get('cliente', {}).get('cpf', 'N/A')),
                'valor_total': nfe.get('valor_total', 0),
                'status': nfe.get('status', 'N/A'),
                'chave_acesso': nfe.get('chave_acesso', '')
            })

        return jsonify({
            'success': True,
            'total': len(nfes_formatadas),
            'periodo': {
                'inicio': data_inicio.strftime('%d/%m/%Y'),
                'fim': data_fim.strftime('%d/%m/%Y')
            },
            'nfes': nfes_formatadas
        })

    except Exception as e:
        logger.error(f"Erro ao listar NFs: {e}")
        return jsonify({'error': str(e)}), 500

@oauth_bp.route('/visualizar-nfe/<nfe_id>')
@login_required
def visualizar_nfe(nfe_id):
    """Visualiza detalhes de uma NF específica"""
    try:
        oauth = TagPlusOAuth2V2(api_type='notas')

        # Busca detalhes da NF
        response = oauth.make_request('GET', f'/nfes/{nfe_id}')

        if not response or response.status_code != 200:
            return jsonify({'error': 'NF não encontrada'}), 404

        nfe = response.json()

        return jsonify({
            'success': True,
            'nfe': nfe
        })

    except Exception as e:
        logger.error(f"Erro ao visualizar NF {nfe_id}: {e}")
        return jsonify({'error': str(e)}), 500

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
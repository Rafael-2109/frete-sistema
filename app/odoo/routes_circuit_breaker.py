"""
Rotas para Monitoramento do Circuit Breaker
============================================

Endpoints administrativos para monitorar e gerenciar o Circuit Breaker
que protege as conexões com o Odoo.

Autor: Sistema de Fretes
Data: 2025-11-05
"""

from flask import Blueprint, jsonify, render_template_string
from flask_login import login_required, current_user
from functools import wraps
from .utils.connection import get_odoo_connection

# Blueprint
circuit_breaker_bp = Blueprint('circuit_breaker', __name__, url_prefix='/admin/circuit-breaker')


def admin_required(f):
    """Decorator para permitir apenas administradores"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Não autenticado'}), 401

        # ✅ CORREÇÃO: perfil correto é 'administrador' (não 'admin')
        if current_user.perfil != 'administrador':
            return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403

        return f(*args, **kwargs)
    return decorated_function


@circuit_breaker_bp.route('/status', methods=['GET'])
@login_required
def status():
    """
    Retorna status do Circuit Breaker
    Qualquer usuário autenticado pode visualizar (não modificar)
    """
    try:
        connection = get_odoo_connection()
        status_data = connection.get_circuit_breaker_status()

        return jsonify({
            'success': True,
            'circuit_breaker': status_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@circuit_breaker_bp.route('/reset', methods=['POST'])
@admin_required
def reset():
    """Reseta manualmente o Circuit Breaker"""
    try:
        connection = get_odoo_connection()
        connection.reset_circuit_breaker()

        return jsonify({
            'success': True,
            'message': 'Circuit Breaker resetado com sucesso'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@circuit_breaker_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    """Dashboard visual do Circuit Breaker"""
    html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Circuit Breaker - Monitoramento Odoo</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
            }

            h1 {
                color: #333;
                margin-bottom: 10px;
            }

            .subtitle {
                color: #666;
                margin-bottom: 30px;
            }

            .status-card {
                background: white;
                border-radius: 8px;
                padding: 30px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }

            .status-indicator {
                display: inline-flex;
                align-items: center;
                gap: 10px;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
            }

            .status-dot {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }

            .status-CLOSED {
                background: #4CAF50;
            }

            .status-OPEN {
                background: #f44336;
            }

            .status-HALF_OPEN {
                background: #ff9800;
            }

            @keyframes pulse {
                0%, 100% {
                    opacity: 1;
                }
                50% {
                    opacity: 0.5;
                }
            }

            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }

            .metric {
                background: #f9f9f9;
                padding: 20px;
                border-radius: 6px;
                border-left: 4px solid #2196F3;
            }

            .metric-label {
                color: #666;
                font-size: 14px;
                margin-bottom: 5px;
            }

            .metric-value {
                font-size: 32px;
                font-weight: bold;
                color: #333;
            }

            .metric-unit {
                font-size: 16px;
                color: #666;
            }

            .btn {
                background: #2196F3;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                transition: background 0.3s;
            }

            .btn:hover {
                background: #1976D2;
            }

            .btn-danger {
                background: #f44336;
            }

            .btn-danger:hover {
                background: #d32f2f;
            }

            .alert {
                padding: 15px;
                border-radius: 6px;
                margin-top: 20px;
            }

            .alert-success {
                background: #e8f5e9;
                border: 1px solid #4CAF50;
                color: #2e7d32;
            }

            .alert-error {
                background: #ffebee;
                border: 1px solid #f44336;
                color: #c62828;
            }

            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }

            .timestamp {
                color: #999;
                font-size: 14px;
                margin-top: 20px;
            }

            .config-info {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 6px;
                margin-top: 20px;
                border-left: 4px solid #2196F3;
            }

            .config-info h3 {
                margin-bottom: 10px;
                color: #1976D2;
            }

            .config-info ul {
                list-style: none;
                padding-left: 0;
            }

            .config-info li {
                padding: 5px 0;
                color: #555;
            }

            .actions {
                margin-top: 30px;
                display: flex;
                gap: 15px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 Circuit Breaker - Monitoramento Odoo</h1>
            <p class="subtitle">Proteção contra travamentos quando Odoo está offline</p>

            <div id="status-container" class="loading">
                Carregando status...
            </div>

            <div class="actions">
                <button class="btn" onclick="refreshStatus()">🔄 Atualizar Status</button>
                <button class="btn btn-danger" onclick="resetCircuitBreaker()">⚠️ Resetar Circuit Breaker</button>
            </div>

            <div id="alert-container"></div>
        </div>

        <script>
            let autoRefreshInterval;

            async function fetchStatus() {
                try {
                    const response = await fetch('/admin/circuit-breaker/status');
                    const data = await response.json();

                    if (data.success) {
                        renderStatus(data.circuit_breaker);
                    } else {
                        showAlert('Erro ao carregar status: ' + data.error, 'error');
                    }
                } catch (error) {
                    showAlert('Erro na requisição: ' + error.message, 'error');
                }
            }

            function renderStatus(status) {
                const container = document.getElementById('status-container');

                const stateLabels = {
                    'CLOSED': '🟢 FECHADO (Normal)',
                    'OPEN': '🔴 ABERTO (Bloqueado)',
                    'HALF_OPEN': '🟡 TESTANDO (Verificando Recuperação)'
                };

                const stateDescriptions = {
                    'CLOSED': 'Sistema funcionando normalmente. Todas as chamadas ao Odoo passam.',
                    'OPEN': 'Odoo indisponível. Chamadas bloqueadas para proteger o sistema.',
                    'HALF_OPEN': 'Testando se Odoo voltou. Próxima tentativa determinará o estado.'
                };

                let html = `
                    <div class="status-card">
                        <div class="status-indicator">
                            <span class="status-dot status-${status.state}"></span>
                            ${stateLabels[status.state] || status.state}
                        </div>
                        <p>${stateDescriptions[status.state] || ''}</p>

                        <div class="metrics-grid">
                            <div class="metric">
                                <div class="metric-label">Total de Chamadas</div>
                                <div class="metric-value">${status.total_calls}</div>
                            </div>

                            <div class="metric">
                                <div class="metric-label">Sucessos</div>
                                <div class="metric-value" style="color: #4CAF50;">${status.total_successes}</div>
                            </div>

                            <div class="metric">
                                <div class="metric-label">Falhas</div>
                                <div class="metric-value" style="color: #f44336;">${status.total_failures}</div>
                            </div>

                            <div class="metric">
                                <div class="metric-label">Vezes que Abriu</div>
                                <div class="metric-value">${status.times_opened}</div>
                            </div>

                            <div class="metric">
                                <div class="metric-label">Falhas Consecutivas</div>
                                <div class="metric-value">${status.failure_count} <span class="metric-unit">/ ${status.failure_threshold}</span></div>
                            </div>

                            ${status.time_until_retry !== null ? `
                            <div class="metric">
                                <div class="metric-label">Próxima Tentativa Em</div>
                                <div class="metric-value">${Math.ceil(status.time_until_retry)} <span class="metric-unit">seg</span></div>
                            </div>
                            ` : ''}
                        </div>

                        <div class="config-info">
                            <h3>⚙️ Configuração Conservadora</h3>
                            <ul>
                                <li>✅ <strong>5 falhas consecutivas</strong> para abrir (evita falsos positivos)</li>
                                <li>⏱️ <strong>8 segundos</strong> de timeout por chamada (generoso)</li>
                                <li>🔄 <strong>30 segundos</strong> entre tentativas de recuperação</li>
                                <li>✔️ <strong>1 sucesso</strong> fecha o circuit imediatamente</li>
                                <li>♻️ <strong>Auto-reset</strong> após 2 minutos sem erros</li>
                            </ul>
                        </div>

                        <p class="timestamp">
                            ${status.last_failure_time ? '⏰ Última falha: ' + new Date(status.last_failure_time).toLocaleString('pt-BR') : ''}
                            ${status.last_success_time ? '<br>✅ Último sucesso: ' + new Date(status.last_success_time).toLocaleString('pt-BR') : ''}
                        </p>
                    </div>
                `;

                container.innerHTML = html;
            }

            async function resetCircuitBreaker() {
                if (!confirm('Tem certeza que deseja resetar o Circuit Breaker?\\n\\nIsso forçará novas tentativas de conexão com o Odoo.')) {
                    return;
                }

                try {
                    const response = await fetch('/admin/circuit-breaker/reset', {
                        method: 'POST'
                    });
                    const data = await response.json();

                    if (data.success) {
                        showAlert('✅ Circuit Breaker resetado com sucesso!', 'success');
                        setTimeout(fetchStatus, 500);
                    } else {
                        showAlert('Erro ao resetar: ' + data.error, 'error');
                    }
                } catch (error) {
                    showAlert('Erro na requisição: ' + error.message, 'error');
                }
            }

            function showAlert(message, type) {
                const container = document.getElementById('alert-container');
                container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
                setTimeout(() => {
                    container.innerHTML = '';
                }, 5000);
            }

            function refreshStatus() {
                fetchStatus();
            }

            // Auto-refresh a cada 5 segundos
            autoRefreshInterval = setInterval(fetchStatus, 5000);

            // Carregar status inicial
            fetchStatus();
        </script>
    </body>
    </html>
    """

    return render_template_string(html)

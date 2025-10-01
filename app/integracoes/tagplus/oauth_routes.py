"""
Rotas OAuth2 para TagPlus - Callbacks e Autorização
"""

from flask import Blueprint, request, redirect, url_for, jsonify, session, render_template_string
from flask_login import login_required, current_user
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
from app.integracoes.tagplus.importador_v2 import ImportadorTagPlusV2
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
                    <br><input type="text" value="{{ tokens_clientes_display }}" readonly style="width: 100%; padding: 5px; margin-top: 5px; font-size: 11px; background: #f0f0f0;" onclick="this.select();">
                {% else %}
                    ⚠️ Não autorizada
                {% endif %}
            </li>
            <li>API Notas:
                {% if tokens_notas %}
                    ✅ Autorizada
                    <br><input type="text" value="{{ tokens_notas_display }}" readonly style="width: 100%; padding: 5px; margin-top: 5px; font-size: 11px; background: #f0f0f0;" onclick="this.select();">
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
        <p>Buscar NFs por período:</p>
        <div style="margin: 10px 0;">
            <label>Data Inicial:</label>
            <input type="date" id="dataInicio" value="{{ (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d') }}" style="padding: 5px; margin-right: 10px;">

            <label>Data Final:</label>
            <input type="date" id="dataFim" value="{{ datetime.now().strftime('%Y-%m-%d') }}" style="padding: 5px; margin-right: 10px;">

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
            <div style="margin-top: 10px;">
                <strong>Carregando notas fiscais...</strong><br>
                <small style="color: #666;">Buscando detalhes de cada NF. Isso pode demorar alguns minutos dependendo da quantidade.</small>
            </div>
        </div>
    </div>

    <script>
    function listarNFs() {
        const dataInicio = document.getElementById('dataInicio').value;
        const dataFim = document.getElementById('dataFim').value;
        const loading = document.getElementById('loadingNFs');
        const resultado = document.getElementById('resultadoNFs');
        const tabela = document.getElementById('tabelaNFs');

        loading.style.display = 'block';
        resultado.style.display = 'none';

        fetch(`/tagplus/oauth/listar-nfs?data_inicio=${dataInicio}&data_fim=${dataFim}`)
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';

                if (data.error) {
                    alert('❌ Erro: ' + data.error);
                    return;
                }

                if (data.success && data.nfes !== undefined) {
                    tabela.innerHTML = '';
                    document.getElementById('totalNFs').textContent = data.total;

                    if (data.nfes.length === 0) {
                        tabela.innerHTML = `
                            <tr>
                                <td colspan="4" style="text-align: center; padding: 30px;">
                                    <div style="font-size: 48px; margin-bottom: 10px;">📋</div>
                                    <strong>Nenhuma NF encontrada no período</strong><br>
                                    <small style="color: #666;">Período buscado: ${dataInicio} a ${dataFim}</small><br>
                                    <small style="color: #999;">Tente ampliar o período de busca ou verifique se há NFs emitidas nesses dias.</small>
                                </td>
                            </tr>
                        `;
                    } else {
                        data.nfes.forEach(nfe => {
                            const tr = document.createElement('tr');
                            // OTIMIZADO: Removida coluna de data (acelera listagem)
                            tr.innerHTML = `
                                <td style="padding: 8px; border: 1px solid #ddd;">${nfe.numero}</td>
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

        // Mostrar loading com informação de quantidade
        const loading = document.getElementById('loadingNFs');
        const totalNFs = window.nfsParaImportar.length;
        if (loading) {
            loading.innerHTML = `
                <div style="font-size: 24px;">⏳</div>
                <div style="margin-top: 10px;">
                    <strong>Importando ${totalNFs} NF(s)...</strong><br>
                    <small style="color: #666;">Isso pode levar alguns minutos. Aguarde...</small><br>
                    <div style="margin-top: 10px; padding: 10px; background: #f0f0f0; border-radius: 5px;">
                        <div style="font-size: 12px; color: #555;">
                            ⚙️ Processando: buscando detalhes, validando pedidos e criando registros...<br>
                            ⏱️ Tempo estimado: ~${Math.ceil(totalNFs * 0.5)} segundos
                        </div>
                    </div>
                </div>
            `;
            loading.style.display = 'block';
        }

        // Desabilitar botão para evitar cliques duplos
        const botao = event.target;
        botao.disabled = true;
        botao.textContent = `⏳ Importando ${totalNFs} NF(s)...`;

        // Fazer requisição para importar
        fetch('/tagplus/oauth/importar-nfs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': '{{ csrf_token() }}'
            },
            body: JSON.stringify({
                nf_ids: window.nfsParaImportar,
                data_inicio: document.getElementById('dataInicio').value,
                data_fim: document.getElementById('dataFim').value
            })
        })
        .then(response => response.json())
        .then(data => {
            if (loading) loading.style.display = 'none';

            if (data.success) {
                let mensagem = `✅ Importação concluída!\n\n`;

                // NFs com pedido (importadas completamente)
                if (data.nfs_importadas > 0) {
                    mensagem += `✅ ${data.nfs_importadas} NF(s) importada(s) com sucesso\n`;
                    mensagem += `   └─ ${data.itens_criados} itens criados\n`;
                }

                // NFs sem pedido (pendentes NOVAS)
                if (data.nfs_pendentes > 0) {
                    mensagem += `⚠️ ${data.nfs_pendentes} NF(s) sem pedido (gravadas em pendências)\n`;
                }

                // NFs que já estavam em pendências
                if (data.nfs_pendentes_existentes > 0) {
                    mensagem += `ℹ️ ${data.nfs_pendentes_existentes} NF(s) já estavam em pendências\n`;
                }

                // NFs já importadas antes
                if (data.nfs_ja_importadas > 0) {
                    mensagem += `✓ ${data.nfs_ja_importadas} NF(s) já importadas anteriormente (puladas)\n`;
                }

                // Processamento
                if (data.processamento && data.processamento.nfs_processadas > 0) {
                    mensagem += `\n📊 Processamento:\n`;
                    mensagem += `   └─ ${data.processamento.nfs_processadas} NF(s) processadas\n`;
                    if (data.processamento.movimentacoes_criadas) {
                        mensagem += `   └─ ${data.processamento.movimentacoes_criadas} movimentação(ões) de estoque\n`;
                    }
                }

                // Link para pendências se houver
                if (data.nfs_pendentes > 0 || data.nfs_pendentes_existentes > 0) {
                    mensagem += `\n💡 Use a tela "Correção de Pedidos" para preencher os pedidos das NFs pendentes.`;
                }

                alert(mensagem);

                // Recarregar página para mostrar status atualizado
                window.location.reload();
            } else {
                alert('❌ Erro na importação: ' + (data.error || 'Erro desconhecido'));
                botao.disabled = false;
                botao.textContent = '📥 Importar Todas as NFs Listadas';
            }
        })
        .catch(error => {
            if (loading) loading.style.display = 'none';
            alert('❌ Erro na requisição: ' + error);
            botao.disabled = false;
            botao.textContent = '📥 Importar Todas as NFs Listadas';
        });
    }
    </script>

    <div class="card">
        <h2>🎯 Importar NF Individual</h2>
        <p>Buscar e importar uma NF específica com validações completas:</p>
        <div style="margin: 10px 0;">
            <label>Número da NF:</label>
            <input type="text" id="numeroNFIndividual" placeholder="Ex: 3706" style="padding: 5px; margin-right: 10px; width: 150px;">

            <button class="btn btn-primary" onclick="buscarNFIndividual()">
                🔍 Buscar e Validar
            </button>
        </div>
        <div id="loadingNFIndividual" style="display: none; text-align: center; padding: 20px;">
            ⏳ Buscando NF...
        </div>
    </div>

    <div class="card">
        <h2>🔧 Correção de Pedidos (NFs Pendentes)</h2>
        <p>Visualizar e corrigir NFs que foram importadas sem número de pedido:</p>
        <button class="btn btn-primary" onclick="carregarNFsPendentes()">
            📋 Ver NFs Pendentes
        </button>
        <div id="nfsPendentesContainer" style="display: none; margin-top: 20px;">
            <div id="loadingPendentes" style="display: none; text-align: center; padding: 20px;">
                ⏳ Carregando NFs pendentes...
            </div>
            <div id="resultadoPendentes"></div>
        </div>
    </div>

    <script>
    // ========== IMPORTAÇÃO INDIVIDUAL DE NF ==========
    function buscarNFIndividual() {
        const numeroNF = document.getElementById('numeroNFIndividual').value.trim();
        if (!numeroNF) {
            alert('❌ Por favor, informe o número da NF');
            return;
        }
        const loading = document.getElementById('loadingNFIndividual');
        loading.style.display = 'block';
        fetch(`/tagplus/oauth/buscar-nf-individual/${numeroNF}`)
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';
                if (data.error) {
                    alert('❌ ' + data.error);
                    return;
                }
                if (data.success) {
                    mostrarModalNFIndividual(data);
                }
            })
            .catch(error => {
                loading.style.display = 'none';
                alert('❌ Erro ao buscar NF: ' + error);
            });
    }

    function mostrarModalNFIndividual(data) {
        const nf = data.nf;
        const validacoes = data.validacoes;
        const modalHTML = `
            <div id="modalNFIndividual" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center;">
                <div style="background: white; padding: 30px; border-radius: 10px; max-width: 700px; width: 90%; max-height: 90vh; overflow-y: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h2 style="margin-top: 0; border-bottom: 2px solid #007bff; padding-bottom: 10px;">📋 NF ${nf.numero}</h2>
                    <div style="margin: 20px 0;"><h3 style="margin-bottom: 10px;">📦 Dados da NF</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="background: #f8f9fa;"><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Cliente:</td><td style="padding: 8px; border: 1px solid #ddd;">${nf.cliente}</td></tr>
                            <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">CNPJ:</td><td style="padding: 8px; border: 1px solid #ddd;">${nf.cnpj}</td></tr>
                            <tr style="background: #f8f9fa;"><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Valor Total:</td><td style="padding: 8px; border: 1px solid #ddd;">R$ ${parseFloat(nf.valor_total).toFixed(2)}</td></tr>
                            <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Pedido TagPlus:</td><td style="padding: 8px; border: 1px solid #ddd;">${nf.numero_pedido ? '<strong style="color: green;">✅ ' + nf.numero_pedido + '</strong>' : '<span style="color: orange;">⚠️ Sem pedido</span>'}</td></tr>
                            <tr style="background: #f8f9fa;"><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Itens:</td><td style="padding: 8px; border: 1px solid #ddd;">${nf.qtd_itens} produto(s)</td></tr>
                        </table>
                    </div>
                    <div style="margin: 20px 0;"><h3 style="margin-bottom: 10px;">🔍 Status de Validações</h3>
                        <div style="padding: 10px; margin: 5px 0; border-radius: 5px; background: ${validacoes.faturamento_produto ? '#d4edda' : '#fff3cd'}; border-left: 4px solid ${validacoes.faturamento_produto ? '#28a745' : '#ffc107'};">
                            <strong>FaturamentoProduto:</strong> ${validacoes.faturamento_produto ? '✅ Já importada (' + validacoes.faturamento_produto_count + ' item/ns)' : '⚠️ Não importada'}
                        </div>
                        <div style="padding: 10px; margin: 5px 0; border-radius: 5px; background: ${validacoes.embarque_item ? '#d4edda' : '#f8f9fa'}; border-left: 4px solid ${validacoes.embarque_item ? '#28a745' : '#6c757d'};">
                            <strong>EmbarqueItem:</strong> ${validacoes.embarque_item ? '✅ Vinculada (Embarque #' + validacoes.embarque_numero + ')' : 'ℹ️ Não vinculada a embarque'}
                        </div>
                        <div style="padding: 10px; margin: 5px 0; border-radius: 5px; background: ${validacoes.movimentacao_estoque_com_lote ? '#d4edda' : '#f8f9fa'}; border-left: 4px solid ${validacoes.movimentacao_estoque_com_lote ? '#28a745' : '#6c757d'};">
                            <strong>MovimentacaoEstoque:</strong> ${validacoes.movimentacao_estoque_com_lote ? '✅ Com lote preenchido (' + validacoes.movimentacao_count + ' movimentação/ões)' : 'ℹ️ Sem movimentações com lote'}
                        </div>
                    </div>
                    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; display: flex; gap: 10px; justify-content: flex-end;">
                        <button onclick="fecharModalNFIndividual()" class="btn" style="background: #6c757d; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">Fechar</button>
                        ${validacoes.faturamento_produto ? '<button disabled class="btn" style="background: #ccc; color: #666; padding: 10px 20px; border: none; border-radius: 5px; cursor: not-allowed;">✅ Já Importada</button>' : '<button onclick="importarNFIndividual(\'' + nf.id + '\')" class="btn btn-success" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">📥 Importar NF</button>'}
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    function fecharModalNFIndividual() {
        const modal = document.getElementById('modalNFIndividual');
        if (modal) modal.remove();
    }

    function importarNFIndividual(nfId) {
        if (!confirm('Confirma a importação desta NF?\\n\\nSerão executadas todas as validações do processo normal de importação.')) return;
        event.target.disabled = true;
        event.target.textContent = '⏳ Importando...';
        fetch('/tagplus/oauth/importar-nf-individual', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token() }}'},
            body: JSON.stringify({ nf_id: nfId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('✅ Importação concluída!\\n\\nNFs importadas: ' + data.nfs_importadas + '\\nItens criados: ' + data.itens_criados + '\\n' + (data.nfs_pendentes > 0 ? '⚠️ NF sem pedido (em pendências): ' + data.nfs_pendentes + '\\n' : '') + (data.processamento ? 'Processadas: ' + data.processamento.nfs_processadas : ''));
                fecharModalNFIndividual();
                document.getElementById('numeroNFIndividual').value = '';
            } else {
                alert('❌ Erro na importação: ' + (data.error || 'Erro desconhecido'));
                event.target.disabled = false;
                event.target.textContent = '📥 Importar NF';
            }
        })
        .catch(error => {
            alert('❌ Erro na requisição: ' + error);
            event.target.disabled = false;
            event.target.textContent = '📥 Importar NF';
        });
    }
    // ========== FIM IMPORTAÇÃO INDIVIDUAL ==========

    function carregarNFsPendentes() {
        const container = document.getElementById('nfsPendentesContainer');
        const loading = document.getElementById('loadingPendentes');
        const resultado = document.getElementById('resultadoPendentes');

        container.style.display = 'block';
        loading.style.display = 'block';
        resultado.innerHTML = '';

        // Buscar estatísticas e NFs pendentes
        fetch('/integracoes/tagplus/api/v2/estatisticas-pendentes')
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';

                if (data.success && data.estatisticas) {
                    const stats = data.estatisticas;

                    if (stats.total_pendentes === 0) {
                        resultado.innerHTML = `
                            <div class="status success">
                                ✅ Nenhuma NF pendente! Todas as NFs importadas têm número de pedido.
                            </div>
                        `;
                        return;
                    }

                    resultado.innerHTML = `
                        <div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                            <strong>📊 Estatísticas:</strong><br>
                            • Total pendentes: ${stats.total_pendentes}<br>
                            • Resolvidas: ${stats.total_resolvido}<br>
                            • Importadas: ${stats.total_importado}
                        </div>
                        <div style="margin-top: 10px;">
                            <a href="/integracoes/tagplus/pendencias" target="_blank" class="btn btn-success">
                                📝 Abrir Tela de Correção
                            </a>
                        </div>
                    `;
                } else {
                    resultado.innerHTML = `
                        <div class="status error">
                            ❌ Erro ao carregar estatísticas
                        </div>
                    `;
                }
            })
            .catch(error => {
                loading.style.display = 'none';
                resultado.innerHTML = `
                    <div class="status error">
                        ❌ Erro: ${error}
                    </div>
                `;
            });
    }
    </script>
    {% endif %}
    {% endif %}

    <div class="card">
        <h2>📝 Tokens Manuais</h2>
        <p>Se você já tem tokens de acesso, pode configurá-los manualmente:</p>
        <form method="POST" action="{{ url_for('tagplus_oauth.set_tokens_manual') }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
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

    # Mostra o token completo (removido limite ridículo)
    tokens_clientes_display = tokens_clientes if tokens_clientes else None
    tokens_notas_display = tokens_notas if tokens_notas else None

    status = request.args.get('status')
    status_type = request.args.get('status_type', 'success')

    return render_template_string(
        AUTH_PAGE_TEMPLATE,
        tokens_clientes=tokens_clientes,
        tokens_notas=tokens_notas,
        tokens_clientes_display=tokens_clientes_display,
        tokens_notas_display=tokens_notas_display,
        status=status,
        status_type=status_type,
        datetime=datetime,
        timedelta=timedelta
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
    import time

    api_type = request.form.get('api_type')
    access_token = request.form.get('access_token', '').strip()
    refresh_token = request.form.get('refresh_token', '').strip()

    if not api_type or not access_token:
        return redirect(url_for('tagplus_oauth.index',
                              status='API e Access Token são obrigatórios',
                              status_type='error'))

    # IMPORTANTE: Salva tokens DIRETAMENTE na sessão Flask
    # Usa EXATAMENTE as mesmas chaves que são verificadas no index()
    session[f'tagplus_{api_type}_access_token'] = access_token
    if refresh_token:
        session[f'tagplus_{api_type}_refresh_token'] = refresh_token
    session[f'tagplus_{api_type}_expires_at'] = time.time() + 86400 - 300  # 24h menos 5 min

    # CRÍTICO: Força o Flask a salvar a sessão
    session.modified = True

    logger.info(f"Token manual salvo para {api_type}: {access_token[:20]}...")

    # Agora testa a conexão para validar o token
    oauth = TagPlusOAuth2V2(api_type=api_type)
    # OAuth vai carregar o token da sessão que acabamos de salvar

    # Testa conexão
    success, info = oauth.test_connection()

    if success:
        logger.info(f"Token manual validado com sucesso para {api_type}")
        return redirect(url_for('tagplus_oauth.index',
                              status=f'✅ Token configurado e validado com sucesso para {api_type}!',
                              status_type='success'))
    else:
        # Remove token inválido da sessão
        session.pop(f'tagplus_{api_type}_access_token', None)
        session.pop(f'tagplus_{api_type}_refresh_token', None)
        session.pop(f'tagplus_{api_type}_expires_at', None)
        session.modified = True

        logger.error(f"Token manual inválido para {api_type}: {info}")
        return redirect(url_for('tagplus_oauth.index',
                              status=f'❌ Token inválido: {info}',
                              status_type='error'))

@oauth_bp.route('/listar-nfs')
@login_required
def listar_nfs():
    """Lista NFs disponíveis para importação"""
    try:
        # Pega parâmetros da query string
        data_inicio_str = request.args.get('data_inicio')
        data_fim_str = request.args.get('data_fim')

        # Se não receber datas, usar últimos 7 dias como fallback
        if data_inicio_str:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        else:
            data_inicio = datetime.now().date() - timedelta(days=7)

        if data_fim_str:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        else:
            data_fim = datetime.now().date()

        # Usa OAuth2 para buscar NFs
        oauth = TagPlusOAuth2V2(api_type='notas')

        # Faz requisição para listar NFs
        # Primeiro tenta com filtros de data
        params = {
            'since': data_inicio.strftime('%Y-%m-%d'),
            'until': data_fim.strftime('%Y-%m-%d'),
            'per_page': 500  # Aumentado para 500 (timeout de 5min protege)
        }

        # Log para debug
        logger.info(f"Buscando NFs do TagPlus com params: {params}")

        response = oauth.make_request(
            'GET',
            '/nfes',
            params=params
        )

        # Log da resposta
        if response:
            logger.info(f"Resposta TagPlus - Status: {response.status_code}")
            if response.status_code == 200:
                try:
                    resp_data = response.json()
                    if isinstance(resp_data, list):
                        logger.info(f"TagPlus retornou lista com {len(resp_data)} NFs no período {data_inicio} a {data_fim}")
                        if resp_data and len(resp_data) > 0:
                            logger.info(f"Primeira NF: {resp_data[0].get('numero', 'sem numero')}")
                    else:
                        logger.info(f"TagPlus retornou tipo: {type(resp_data)}")
                except Exception as e:
                    logger.error(f"Erro ao processar resposta TagPlus: {e}")
                    pass

        if not response:
            return jsonify({'error': 'Erro ao buscar NFs'}), 500

        if response.status_code == 401:
            return jsonify({'error': 'Token expirado. Autorize novamente.'}), 401

        if response.status_code != 200:
            return jsonify({'error': f'Erro: {response.status_code}'}), response.status_code

        data = response.json()

        # Log para debug
        logger.info(f"Tipo de resposta: {type(data)}")

        # Extrai NFs do response - a API retorna uma lista direta
        if isinstance(data, list):
            nfes = data
        elif isinstance(data, dict):
            # Caso retorne em um envelope
            nfes = data.get('data', data.get('nfes', data.get('items', [])))
        else:
            nfes = []

        logger.info(f"Total de NFs do TagPlus processadas: {len(nfes)}")

        # Se não encontrou NFs no TagPlus, retornar erro claro
        if len(nfes) == 0:
            logger.warning("Nenhuma NF encontrada no TagPlus")
            return jsonify({
                'success': True,
                'total': 0,
                'periodo': {
                    'inicio': data_inicio.strftime('%d/%m/%Y'),
                    'fim': data_fim.strftime('%d/%m/%Y')
                },
                'nfes': [],
                'mensagem': 'Nenhuma NF encontrada no TagPlus para o período'
            })

        # Formata NFs para exibição (OTIMIZADO - sem buscar detalhes)
        nfes_formatadas = []
        for nfe in nfes:
            # A API retorna estrutura simplificada com destinatário
            destinatario = nfe.get('destinatario', {})

            # Extrai dados do destinatário
            if isinstance(destinatario, dict):
                nome_cliente = destinatario.get('razao_social') or destinatario.get('nome') or 'N/A'
                cnpj_cliente = destinatario.get('cnpj') or destinatario.get('cpf') or 'N/A'
            else:
                nome_cliente = 'N/A'
                cnpj_cliente = 'N/A'

            # OTIMIZAÇÃO: Não busca detalhes aqui (reduz de N+1 para 1 requisição)
            # Data será capturada apenas durante importação
            nfes_formatadas.append({
                'id': nfe.get('id'),
                'id_nota': nfe.get('id_nota'),
                'numero': nfe.get('numero'),
                'serie': nfe.get('serie', 1),
                'cliente': nome_cliente,
                'cnpj': cnpj_cliente,
                'valor_total': nfe.get('valor_nota', 0),
                'cfop': nfe.get('cfop', ''),
                'status': 'Autorizada'  # Lista simplificada só traz autorizadas
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

@oauth_bp.route('/importar-nfs', methods=['POST'])
@login_required
def importar_nfs():
    """Importa NFs selecionadas para o sistema"""
    try:
        from app.integracoes.tagplus.importador_v2 import ImportadorTagPlusV2
        from datetime import datetime, timedelta

        data = request.get_json()
        nf_ids = data.get('nf_ids', [])
        data_inicio_str = data.get('data_inicio')
        data_fim_str = data.get('data_fim')

        if not nf_ids:
            return jsonify({'error': 'Nenhuma NF selecionada'}), 400

        logger.info(f"Iniciando importação de {len(nf_ids)} NFs")

        # Criar importador
        importador = ImportadorTagPlusV2()

        # Definir período baseado nas datas recebidas
        if data_inicio_str:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        else:
            data_inicio = datetime.now().date() - timedelta(days=7)

        if data_fim_str:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        else:
            data_fim = datetime.now().date()

        # Importar NFs específicas selecionadas pelo usuário
        resultado = importador.importar_nfs(
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=None,  # Não usar limite quando temos IDs específicos
            verificar_cancelamentos=False,  # Não verificar outros cancelamentos quando importando específicos
            nf_ids=nf_ids  # PASSAR OS IDs ESPECÍFICOS DAS NFs SELECIONADAS
        )

        if resultado:
            logger.info(f"Importação concluída: {resultado}")
            return jsonify({
                'success': True,
                'nfs_importadas': resultado['nfs']['importadas'],
                'nfs_pendentes': resultado['nfs']['pendentes'],
                'nfs_pendentes_existentes': resultado['nfs']['pendentes_existentes'],
                'nfs_ja_importadas': resultado['nfs']['ja_importadas'],
                'itens_criados': resultado['nfs']['itens'],
                'processamento': resultado.get('processamento', {}),
                'erros': resultado['nfs'].get('erros', [])
            })
        else:
            return jsonify({
                'error': 'Erro ao importar NFs',
                'success': False
            }), 500

    except Exception as e:
        logger.error(f"Erro ao importar NFs: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@oauth_bp.route('/buscar-nf-individual/<numero_nf>')
@login_required
def buscar_nf_individual(numero_nf):
    """Busca uma NF individual e retorna seus dados com validações"""
    try:
        from app.faturamento.models import FaturamentoProduto
        from app.embarques.models import EmbarqueItem
        from app.estoque.models import MovimentacaoEstoque
        oauth = TagPlusOAuth2V2(api_type='notas')
        logger.info(f"Buscando NF individual: {numero_nf}")
        response = oauth.make_request('GET', '/nfes', params={'per_page': 500})
        if not response or response.status_code != 200:
            return jsonify({'error': 'Erro ao buscar NFs do TagPlus'}), 500
        nfes = response.json()
        nf_encontrada = None
        for nf in nfes:
            if str(nf.get('numero')) == str(numero_nf):
                nf_encontrada = nf
                break
        if not nf_encontrada:
            return jsonify({'error': f'NF {numero_nf} não encontrada no TagPlus'}), 404
        nf_id = nf_encontrada.get('id')
        response_detail = oauth.make_request('GET', f'/nfes/{nf_id}')
        if not response_detail or response_detail.status_code != 200:
            return jsonify({'error': 'Erro ao buscar detalhes da NF'}), 500
        nf_completa = response_detail.json()
        destinatario = nf_completa.get('destinatario', {})
        cliente_nome = destinatario.get('razao_social') or destinatario.get('nome') or 'N/A'
        cnpj_cliente = destinatario.get('cnpj') or destinatario.get('cpf') or 'N/A'
        numero_pedido = nf_completa.get('numero_pedido') or ''
        qtd_itens = len(nf_completa.get('itens', []))
        itens_faturamento = FaturamentoProduto.query.filter_by(numero_nf=str(numero_nf)).all()
        tem_faturamento = len(itens_faturamento) > 0
        embarque_item = EmbarqueItem.query.filter_by(nota_fiscal=str(numero_nf)).first()
        tem_embarque = embarque_item is not None
        embarque_numero = embarque_item.embarque_id if embarque_item else None
        movimentacoes = MovimentacaoEstoque.query.filter_by(numero_nf=str(numero_nf)).all()
        movimentacoes_com_lote = [m for m in movimentacoes if m.separacao_lote_id and m.separacao_lote_id.strip()]
        tem_movimentacao_com_lote = len(movimentacoes_com_lote) > 0
        return jsonify({
            'success': True,
            'nf': {
                'id': nf_id, 'numero': numero_nf, 'cliente': cliente_nome, 'cnpj': cnpj_cliente,
                'valor_total': nf_completa.get('valor_nota', 0), 'numero_pedido': numero_pedido, 'qtd_itens': qtd_itens
            },
            'validacoes': {
                'faturamento_produto': tem_faturamento, 'faturamento_produto_count': len(itens_faturamento),
                'embarque_item': tem_embarque, 'embarque_numero': embarque_numero,
                'movimentacao_estoque_com_lote': tem_movimentacao_com_lote, 'movimentacao_count': len(movimentacoes_com_lote)
            }
        })
    except Exception as e:
        logger.error(f"Erro ao buscar NF individual {numero_nf}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro ao buscar NF: {str(e)}', 'success': False}), 500

@oauth_bp.route('/importar-nf-individual', methods=['POST'])
@login_required
def importar_nf_individual():
    """Importa uma NF individual usando o ImportadorTagPlusV2"""
    try:
        dados = request.get_json()
        nf_id = dados.get('nf_id')
        if not nf_id:
            return jsonify({'error': 'ID da NF não informado'}), 400
        logger.info(f"Importando NF individual: {nf_id}")
        importador = ImportadorTagPlusV2()
        resultado = importador.importar_nfs(
            usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema',
            limpar_inconsistencias=False, verificar_cancelamentos=False, nf_ids=[nf_id]
        )
        if resultado:
            logger.info(f"Importação individual concluída: {resultado}")
            return jsonify({
                'success': True, 'nfs_importadas': resultado['nfs']['importadas'],
                'nfs_pendentes': resultado['nfs']['pendentes'],
                'nfs_pendentes_existentes': resultado['nfs']['pendentes_existentes'],
                'nfs_ja_importadas': resultado['nfs']['ja_importadas'],
                'itens_criados': resultado['nfs']['itens'],
                'processamento': resultado.get('processamento', {}),
                'erros': resultado['nfs'].get('erros', [])
            })
        else:
            return jsonify({'error': 'Erro ao importar NF', 'success': False}), 500
    except Exception as e:
        logger.error(f"Erro ao importar NF individual: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

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
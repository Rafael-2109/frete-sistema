/**
 * JavaScript para Modal de Histórico de Requisições
 * Compara versões e exibe alterações
 */

(function() {
    'use strict';

    // ========================================
    // Inicialização
    // ========================================
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[HISTORICO] Módulo carregado');

        // Verificar se estamos na página de detalhe
        if (!window.REQUISICAO_DATA) {
            return;
        }

        inicializarModal();
    });

    // ========================================
    // Inicializar Modal
    // ========================================
    function inicializarModal() {
        const btnVerHistorico = document.getElementById('btn-ver-historico-completo');

        if (!btnVerHistorico) {
            console.warn('[HISTORICO] Botão não encontrado');
            return;
        }

        btnVerHistorico.addEventListener('click', function() {
            abrirModalHistorico();
        });
    }

    // ========================================
    // Abrir Modal e Carregar Dados
    // ========================================
    function abrirModalHistorico() {
        const modal = new bootstrap.Modal(document.getElementById('modalHistoricoCompleto'));

        // Preencher dados da requisição
        document.getElementById('modal-num-requisicao').textContent = window.REQUISICAO_DATA.num_requisicao;
        document.getElementById('modal-cod-produto').textContent = window.REQUISICAO_DATA.cod_produto;
        document.getElementById('modal-nome-produto').textContent = window.REQUISICAO_DATA.nome_produto;

        // Mostrar loading
        mostrarLoading();

        // Abrir modal
        modal.show();

        // Carregar histórico
        carregarHistorico();
    }

    // ========================================
    // Carregar Histórico via API
    // ========================================
    function carregarHistorico() {
        const requisicaoId = window.REQUISICAO_DATA.id;
        const url = `/manufatura/api/requisicoes-compras/${requisicaoId}/historico`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.sucesso) {
                    if (data.versoes && data.versoes.length > 0) {
                        renderizarHistorico(data.versoes);
                    } else {
                        mostrarVazio();
                    }
                } else {
                    mostrarErro(data.erro || 'Erro ao carregar histórico');
                }
            })
            .catch(error => {
                console.error('[HISTORICO] Erro:', error);
                mostrarErro('Erro ao conectar com o servidor');
            });
    }

    // ========================================
    // Renderizar Histórico (Timeline)
    // ========================================
    function renderizarHistorico(versoes) {
        const conteudoDiv = document.getElementById('historico-conteudo');
        conteudoDiv.innerHTML = '';

        // Criar timeline
        const timeline = document.createElement('div');
        timeline.className = 'timeline-historico';

        versoes.forEach((versao, index) => {
            const itemTimeline = criarItemTimeline(versao, index);
            timeline.appendChild(itemTimeline);
        });

        conteudoDiv.appendChild(timeline);

        // Esconder loading e mostrar conteúdo
        document.getElementById('historico-loading').style.display = 'none';
        document.getElementById('historico-conteudo').style.display = 'block';
    }

    // ========================================
    // Criar Item da Timeline
    // ========================================
    function criarItemTimeline(versao, index) {
        const item = document.createElement('div');
        item.className = 'timeline-item mb-4';

        const badgeClass = versao.operacao === 'CRIAR' ? 'bg-success' : 'bg-info';
        const iconClass = versao.operacao === 'CRIAR' ? 'fa-plus-circle' : 'fa-edit';

        let alteracoesHTML = '';

        if (versao.alteracoes && versao.alteracoes.length > 0) {
            alteracoesHTML = `
                <div class="table-responsive mt-3">
                    <table class="table table-sm table-bordered">
                        <thead class="table-light">
                            <tr>
                                <th style="width: 30%;">Campo</th>
                                <th style="width: 35%;">Valor Anterior</th>
                                <th style="width: 35%;">Novo Valor</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${versao.alteracoes.map(alt => `
                                <tr>
                                    <td><strong>${alt.campo}</strong></td>
                                    <td class="text-danger">${alt.antes}</td>
                                    <td class="text-success"><strong>${alt.depois}</strong></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else if (versao.operacao === 'CRIAR') {
            alteracoesHTML = `
                <div class="alert alert-success mt-3">
                    <i class="fas fa-check-circle"></i> <strong>Requisição criada</strong>
                </div>
            `;
        } else {
            alteracoesHTML = `
                <div class="alert alert-secondary mt-3">
                    <i class="fas fa-info-circle"></i> Nenhuma alteração detectada
                </div>
            `;
        }

        item.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge ${badgeClass}">
                            <i class="fas ${iconClass}"></i> ${versao.operacao}
                        </span>
                        <span class="ms-2">
                            <i class="fas fa-clock text-muted"></i> ${versao.data_hora}
                        </span>
                        <span class="ms-2">
                            <i class="fas fa-user text-muted"></i> ${versao.usuario}
                        </span>
                    </div>
                    ${versao.alteracoes.length > 0 ? `<span class="badge bg-warning">${versao.alteracoes.length} alterações</span>` : ''}
                </div>
                <div class="card-body">
                    ${alteracoesHTML}
                </div>
            </div>
        `;

        return item;
    }

    // ========================================
    // Estados de UI
    // ========================================
    function mostrarLoading() {
        document.getElementById('historico-loading').style.display = 'block';
        document.getElementById('historico-conteudo').style.display = 'none';
        document.getElementById('historico-vazio').style.display = 'none';
    }

    function mostrarVazio() {
        document.getElementById('historico-loading').style.display = 'none';
        document.getElementById('historico-conteudo').style.display = 'none';
        document.getElementById('historico-vazio').style.display = 'block';
    }

    function mostrarErro(mensagem) {
        document.getElementById('historico-loading').style.display = 'none';
        document.getElementById('historico-conteudo').innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> ${mensagem}
            </div>
        `;
        document.getElementById('historico-conteudo').style.display = 'block';
    }

})();

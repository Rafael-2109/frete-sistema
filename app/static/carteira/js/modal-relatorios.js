/**
 * Gerenciador de Relatórios da Carteira
 * Controla o modal de exportação e filtros de data
 */

class RelatoriosManager {
    constructor() {
        this.filtroRelatorios = {
            data_inicio: null,
            data_fim: null
        };
        this.initializeModal();
    }

    initializeModal() {
        // Criar o HTML do modal dinamicamente
        const modalHTML = `
            <div class="modal fade" id="modalRelatorios" tabindex="-1" aria-labelledby="modalRelatoriosLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-info">
                            <h5 class="modal-title" id="modalRelatoriosLabel">
                                <i class="fas fa-file-excel"></i> Exportar Relatórios
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Filtros de Data -->
                            <div class="row mb-4">
                                <div class="col-12">
                                    <div class="card border-info">
                                        <div class="card-header bg-light">
                                            <h6 class="mb-0"><i class="fas fa-calendar"></i> Filtro por Período</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="row">
                                                <div class="col-md-5">
                                                    <label for="dataInicio" class="form-label">Data Inicial:</label>
                                                    <input type="date" class="form-control" id="dataInicio">
                                                </div>
                                                <div class="col-md-5">
                                                    <label for="dataFim" class="form-label">Data Final:</label>
                                                    <input type="date" class="form-control" id="dataFim">
                                                </div>
                                                <div class="col-md-2 d-flex align-items-end">
                                                    <div class="btn-group w-100" role="group">
                                                        <button type="button" class="btn btn-primary" id="btnAplicarFiltro">
                                                            <i class="fas fa-check"></i> Aplicar
                                                        </button>
                                                        <button type="button" class="btn btn-secondary" id="btnLimparFiltro">
                                                            <i class="fas fa-times"></i> Limpar
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="row mt-2">
                                                <div class="col-12">
                                                    <small id="periodoSelecionado" class="text-muted"></small>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Botões de Exportação -->
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <div class="card h-100 text-center border-success">
                                        <div class="card-body">
                                            <i class="fas fa-truck-loading fa-3x text-success mb-3"></i>
                                            <h5 class="card-title">Separações</h5>
                                            <p class="card-text text-muted">
                                                Exportar separações com status do pedido
                                            </p>
                                            <button class="btn btn-success btn-block" data-relatorio="separacoes">
                                                <i class="fas fa-download"></i> Exportar
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <div class="col-md-6 mb-3">
                                    <div class="card h-100 text-center border-warning">
                                        <div class="card-body">
                                            <i class="fas fa-clipboard-list fa-3x text-warning mb-3"></i>
                                            <h5 class="card-title">Carteira Simples</h5>
                                            <p class="card-text text-muted">
                                                Exportar carteira de pedidos em formato simples
                                            </p>
                                            <button class="btn btn-warning btn-block" data-relatorio="carteira_simples">
                                                <i class="fas fa-download"></i> Exportar
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <div class="col-md-6 mb-3">
                                    <div class="card h-100 text-center border-danger">
                                        <div class="card-body">
                                            <i class="fas fa-file-excel fa-3x text-danger mb-3"></i>
                                            <h5 class="card-title">Carteira Detalhada</h5>
                                            <p class="card-text text-muted">
                                                Relatório completo com pedidos, pré-separações e separações
                                            </p>
                                            <button class="btn btn-danger btn-block" data-relatorio="carteira_detalhada">
                                                <i class="fas fa-download"></i> Exportar
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <div class="col-md-6 mb-3">
                                    <div class="card h-100 text-center border-info">
                                        <div class="card-body">
                                            <i class="fas fa-industry fa-3x text-info mb-3"></i>
                                            <h5 class="card-title">Estoque e Produção</h5>
                                            <p class="card-text text-muted">
                                                Estoque atual e movimentações previstas (2 abas)<br>
                                                <small class="text-info"><i class="fas fa-info-circle"></i> Não usa filtro de data</small>
                                            </p>
                                            <button class="btn btn-info btn-block" data-relatorio="producao">
                                                <i class="fas fa-download"></i> Exportar
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Mensagem de Status -->
                            <div id="statusExportacao" class="alert d-none mt-3" role="alert"></div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times"></i> Fechar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Adicionar modal ao body se ainda não existir
        if (!document.getElementById('modalRelatorios')) {
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }

        // Vincular eventos
        this.bindEvents();
    }

    bindEvents() {
        // Evento de aplicar filtro
        document.getElementById('btnAplicarFiltro')?.addEventListener('click', () => {
            this.aplicarFiltro();
        });

        // Evento de limpar filtro
        document.getElementById('btnLimparFiltro')?.addEventListener('click', () => {
            this.limparFiltro();
        });

        // Eventos de exportação
        document.querySelectorAll('[data-relatorio]').forEach(button => {
            button.addEventListener('click', (e) => {
                const tipo = e.currentTarget.getAttribute('data-relatorio');
                this.exportarRelatorio(tipo);
            });
        });
    }

    aplicarFiltro() {
        const dataInicio = document.getElementById('dataInicio').value;
        const dataFim = document.getElementById('dataFim').value;

        if (!dataInicio || !dataFim) {
            this.mostrarStatus('Por favor, selecione as duas datas', 'warning');
            return;
        }

        if (dataInicio > dataFim) {
            this.mostrarStatus('A data inicial deve ser anterior à data final', 'warning');
            return;
        }

        this.filtroRelatorios.data_inicio = dataInicio;
        this.filtroRelatorios.data_fim = dataFim;

        // Mostrar período selecionado
        const periodoElem = document.getElementById('periodoSelecionado');
        const dataInicioFormatada = new Date(dataInicio + 'T00:00:00').toLocaleDateString('pt-BR');
        const dataFimFormatada = new Date(dataFim + 'T00:00:00').toLocaleDateString('pt-BR');
        periodoElem.innerHTML = `<i class="fas fa-check-circle text-success"></i> Período selecionado: ${dataInicioFormatada} até ${dataFimFormatada}`;

        this.mostrarStatus('Filtro aplicado com sucesso!', 'success');
    }

    limparFiltro() {
        this.filtroRelatorios.data_inicio = null;
        this.filtroRelatorios.data_fim = null;

        document.getElementById('dataInicio').value = '';
        document.getElementById('dataFim').value = '';
        document.getElementById('periodoSelecionado').innerHTML = '';

        this.mostrarStatus('Filtro removido', 'info');
    }

    mostrarStatus(mensagem, tipo) {
        const statusElem = document.getElementById('statusExportacao');
        statusElem.className = `alert alert-${tipo}`;
        statusElem.innerHTML = mensagem;
        statusElem.classList.remove('d-none');

        setTimeout(() => {
            statusElem.classList.add('d-none');
        }, 3000);
    }

    async exportarRelatorio(tipo) {
        this.mostrarStatus('Gerando relatório...', 'info');

        // Definir a URL baseada no tipo
        const urlMap = {
            'pre_separacoes': '/carteira/api/relatorios/pre_separacoes',
            'separacoes': '/carteira/api/relatorios/separacoes',
            'carteira_simples': '/carteira/api/relatorios/carteira_simples',
            'carteira_detalhada': '/carteira/api/relatorios/carteira_detalhada',
            'producao': '/producao/relatorios/exportar'
        };

        const url = urlMap[tipo];
        if (!url) {
            this.mostrarStatus('Tipo de relatório inválido', 'danger');
            return;
        }

        try {
            let response;

            // Relatório de produção usa GET, os outros usam POST
            if (tipo === 'producao') {
                console.log('Baixando relatório de produção:', url);
                response = await fetch(url, {
                    method: 'GET'
                });
            } else {
                // Preparar o body - sempre enviar um objeto, mesmo que vazio
                const bodyData = {
                    data_inicio: this.filtroRelatorios.data_inicio || null,
                    data_fim: this.filtroRelatorios.data_fim || null
                };

                console.log('Enviando requisição para:', url);
                console.log('Dados:', bodyData);

                response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(bodyData)
                });
            }

            if (!response.ok) {
                // Tentar obter mensagem de erro do servidor
                let errorMessage = 'Erro ao gerar relatório';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    // Se não for JSON, usar status text
                    errorMessage = response.statusText || errorMessage;
                }
                throw new Error(errorMessage);
            }

            const blob = await response.blob();

            // Criar link para download
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `relatorio_${tipo}_${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);

            this.mostrarStatus('Relatório exportado com sucesso!', 'success');
        } catch (error) {
            console.error('Erro:', error);
            // Mostrar a mensagem de erro real
            this.mostrarStatus(`Erro ao exportar relatório: ${error.message}`, 'danger');
        }
    }
}

// Inicializar quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.relatoriosManager = new RelatoriosManager();
});
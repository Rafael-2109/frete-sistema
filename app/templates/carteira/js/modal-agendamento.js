/**
 * 🗓️ MODAL DE AGENDAMENTO
 * Responsável pela exibição e gerenciamento do modal de agendamento
 */

class ModalAgendamento {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Modal Agendamento inicializado');
    }

    async abrirModalAgendamento(numPedido) {
        console.log(`🗓️ Abrindo modal de agendamento para pedido ${numPedido}`);
        
        // Criar modal se não existir
        this.criarModalSeNecessario();
        
        // Mostrar modal
        const modalElement = document.getElementById('modalAgendamento');
        if (!window._modalAgendamento) {
            window._modalAgendamento = new bootstrap.Modal(modalElement);
        }
        window._modalAgendamento.show();
        
        // Carregar dados
        await this.carregarDadosAgendamento(numPedido);
    }

    criarModalSeNecessario() {
        if (document.getElementById('modalAgendamento')) {
            return; // Modal já existe
        }

        const modal = document.createElement('div');
        modal.id = 'modalAgendamento';
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('role', 'dialog');
        modal.innerHTML = this.renderizarModalAgendamento();
        
        document.body.appendChild(modal);
    }

    renderizarModalAgendamento() {
        return `
            <div class="modal-dialog modal-lg" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-calendar-plus"></i> Solicitar Agendamento
                            <span id="modal-agendamento-pedido" class="badge bg-primary ms-2"></span>
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <!-- Loading state -->
                        <div id="modal-agendamento-loading" class="text-center p-4">
                            <i class="fas fa-spinner fa-spin fa-2x"></i>
                            <p class="mt-2">Carregando dados do pedido...</p>
                        </div>

                        <!-- Error state -->
                        <div id="modal-agendamento-error" class="alert alert-danger" style="display: none;">
                            <i class="fas fa-exclamation-triangle"></i>
                            <span id="modal-agendamento-error-message"></span>
                        </div>

                        <!-- Form content -->
                        <div id="modal-agendamento-content" style="display: none;">
                            <form id="form-agendamento">
                                <input type="hidden" id="agendamento-num-pedido" name="num_pedido">

                                <!-- Resumo do pedido -->
                                <div class="card mb-3">
                                    <div class="card-header bg-info text-white">
                                        <h6 class="mb-0">
                                            <i class="fas fa-box"></i> Resumo do Pedido
                                        </h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="row">
                                            <div class="col-md-6">
                                                <p><strong>Cliente:</strong> <span id="agendamento-cliente"></span></p>
                                                <p><strong>Cidade/UF:</strong> <span id="agendamento-cidade-uf"></span></p>
                                            </div>
                                            <div class="col-md-6">
                                                <p><strong>Valor Total:</strong> <span id="agendamento-valor-total"></span></p>
                                                <p><strong>Total de Itens:</strong> <span id="agendamento-total-itens"></span></p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Dados de expedição e agendamento -->
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label for="data-expedicao" class="form-label">Data de Expedição <span class="text-danger">*</span></label>
                                            <input type="date" class="form-control" id="data-expedicao" required>
                                            <div class="form-text">Data prevista para expedição do pedido</div>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label for="data-agendamento" class="form-label">Data do Agendamento</label>
                                            <input type="date" class="form-control" id="data-agendamento">
                                            <div class="form-text">Data agendada com cliente</div>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label for="hora-agendamento" class="form-label">Hora do Agendamento</label>
                                            <input type="time" class="form-control" id="hora-agendamento">
                                        </div>
                                    </div>
                                </div>

                                <div class="mb-3">
                                    <label for="protocolo-agendamento" class="form-label">Protocolo</label>
                                    <input type="text" class="form-control" id="protocolo-agendamento" placeholder="Protocolo do agendamento">
                                </div>

                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="agendamento-confirmado">
                                        <label class="form-check-label" for="agendamento-confirmado">
                                            Agendamento confirmado
                                        </label>
                                    </div>
                                </div>

                                <!-- Tabela de itens -->
                                <div class="card">
                                    <div class="card-header">
                                        <h6 class="mb-0">
                                            <i class="fas fa-list"></i> Itens do Pedido
                                        </h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive" style="max-height: 300px;">
                                            <table class="table table-sm table-striped">
                                                <thead>
                                                    <tr>
                                                        <th>Produto</th>
                                                        <th>Quantidade</th>
                                                        <th>Valor</th>
                                                        <th>Expedição</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="agendamento-tbody-itens">
                                                    <!-- Itens carregados dinamicamente -->
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-primary" onclick="modalAgendamento.salvarAgendamento()">
                            <i class="fas fa-save"></i> Salvar Agendamento
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    async carregarDadosAgendamento(numPedido) {
        const modalLoading = document.getElementById('modal-agendamento-loading');
        const modalError = document.getElementById('modal-agendamento-error');
        const modalContent = document.getElementById('modal-agendamento-content');

        // Reset states
        modalLoading.style.display = 'block';
        modalError.style.display = 'none';
        modalContent.style.display = 'none';

        // Atualizar título
        document.getElementById('modal-agendamento-pedido').textContent = numPedido;
        document.getElementById('agendamento-num-pedido').value = numPedido;

        try {
            // Carregar dados via AJAX (usando API existente ou adaptada)
            const response = await fetch(`/carteira/api/pedido/${numPedido}/agendamento-info`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar dados do pedido');
            }

            // Preencher dados do resumo
            document.getElementById('agendamento-cliente').textContent = data.cliente || '-';
            document.getElementById('agendamento-cidade-uf').textContent = `${data.cidade || '-'}/${data.uf || '-'}`;
            document.getElementById('agendamento-valor-total').textContent = this.formatarMoeda(data.valor_total || 0);
            document.getElementById('agendamento-total-itens').textContent = data.total_itens || '0';

            // Preencher campos de expedição e agendamento
            if (data.expedicao) {
                document.getElementById('data-expedicao').value = data.expedicao;
            }
            if (data.agendamento) {
                document.getElementById('data-agendamento').value = data.agendamento;
            }
            if (data.hora_agendamento) {
                document.getElementById('hora-agendamento').value = data.hora_agendamento;
            }
            if (data.protocolo) {
                document.getElementById('protocolo-agendamento').value = data.protocolo;
            }
            if (data.agendamento_confirmado) {
                document.getElementById('agendamento-confirmado').checked = data.agendamento_confirmado;
            }

            // Gerar tabela de itens
            this.gerarTabelaItens(data.itens || []);

            // Mostrar conteúdo
            modalLoading.style.display = 'none';
            modalContent.style.display = 'block';

        } catch (error) {
            console.error('Erro ao carregar agendamento:', error);
            document.getElementById('modal-agendamento-error-message').textContent = error.message;
            modalLoading.style.display = 'none';
            modalError.style.display = 'block';
        }
    }

    gerarTabelaItens(itens) {
        const tbody = document.getElementById('agendamento-tbody-itens');
        let html = '';

        itens.forEach(item => {
            html += `
                <tr>
                    <td>
                        <strong>${item.cod_produto}</strong>
                        <br><small class="text-muted">${item.nome_produto || ''}</small>
                    </td>
                    <td class="text-end">${this.formatarQuantidade(item.quantidade)}</td>
                    <td class="text-end">${this.formatarMoeda(item.valor_total)}</td>
                    <td class="text-center">
                        ${item.expedicao ? 
                            `<span class="badge bg-success">${this.formatarData(item.expedicao)}</span>` : 
                            '<span class="badge bg-secondary">Não definida</span>'}
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    async salvarAgendamento() {
        const numPedido = document.getElementById('agendamento-num-pedido').value;
        const dataExpedicao = document.getElementById('data-expedicao').value;
        const dataAgendamento = document.getElementById('data-agendamento').value;
        const horaAgendamento = document.getElementById('hora-agendamento').value;
        const protocolo = document.getElementById('protocolo-agendamento').value;
        const confirmado = document.getElementById('agendamento-confirmado').checked;

        if (!dataExpedicao) {
            alert('❌ Data de expedição é obrigatória!');
            return;
        }

        try {
            const payload = {
                data_expedicao: dataExpedicao,
                data_agendamento: dataAgendamento,
                hora_agendamento: horaAgendamento,
                protocolo: protocolo,
                confirmado: confirmado
            };

            const response = await fetch(`/carteira/api/pedido/${numPedido}/salvar-agendamento`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success) {
                alert(`✅ ${result.message || 'Agendamento salvo com sucesso!'}`);
                
                // Fechar modal
                window._modalAgendamento.hide();
                
                // Recarregar página ou atualizar dados se necessário
                if (typeof window.carteiraAgrupada !== 'undefined') {
                    // Recarregar dados da carteira se estiver na tela agrupada
                    location.reload();
                }
                
            } else {
                alert(`❌ Erro: ${result.error}`);
            }

        } catch (error) {
            console.error('Erro ao salvar agendamento:', error);
            alert('❌ Erro de comunicação com o servidor');
        }
    }

    // Utilitários
    formatarMoeda(valor) {
        if (!valor) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    formatarQuantidade(qtd) {
        if (!qtd) return '0';
        return parseFloat(qtd).toLocaleString('pt-BR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        });
    }

    formatarData(dataStr) {
        const data = new Date(dataStr);
        return data.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: '2-digit'
        });
    }
}

// Disponibilizar globalmente
window.ModalAgendamento = ModalAgendamento;
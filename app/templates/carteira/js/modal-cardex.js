/**
 * 📊 MODAL DE CARDEX D0-D28
 * Responsável pela exibição e formatação do cardex de produtos
 */

class ModalCardex {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Modal Cardex inicializado');
    }

    async abrirCardex(codProduto, dadosProdutos) {
        console.log(`🔍 Abrindo cardex para produto ${codProduto}`);

        try {
            // Buscar dados do cardex
            const response = await fetch(`/carteira/api/produto/${codProduto}/cardex`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar cardex');
            }

            // Criar ID único para esta instância
            const modalId = `modal-cardex-${codProduto}-${Date.now()}`;
            
            // Adicionar à navegação se existe
            if (window.modalNav) {
                window.modalNav.pushModal(modalId, `Cardex - ${codProduto}`, {
                    codProduto: codProduto,
                    dados: data,
                    modalId: modalId
                });
            }

            // Renderizar modal de cardex
            this.mostrarModalCardex(codProduto, data, dadosProdutos, modalId);

        } catch (error) {
            console.error(`❌ Erro ao carregar cardex:`, error);
            alert(`Erro ao carregar cardex: ${error.message}`);
        }
    }

    mostrarModalCardex(codProduto, data, dadosProdutos, modalId) {
        // Usar o modalId fornecido ou criar um novo
        if (!modalId) {
            modalId = `modal-cardex-${codProduto}-${Date.now()}`;
        }
        
        // Remover modal anterior do mesmo produto se houver
        const modaisExistentes = document.querySelectorAll(`[id^="modal-cardex-${codProduto}"]`);
        modaisExistentes.forEach(m => m.remove());

        // Criar modal
        const modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = this.renderizarModalCardex(codProduto, data, dadosProdutos);

        // Adicionar ao DOM
        document.body.appendChild(modal);

        // Mostrar modal usando Bootstrap
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // Remover modal quando fechar
        modal.addEventListener('hidden.bs.modal', () => {
            // Notificar navegação ANTES de remover (se não for navegação)
            if (window.modalNav && !modal._skipNavigation) {
                window.modalNav.popModal();
            }
            // Remover modal do DOM
            setTimeout(() => {
                if (modal.parentNode) {
                    modal.remove();
                }
            }, 100);
        });
    }

    renderizarModalCardex(codProduto, data, dadosProdutos) {
        // Garantir que dadosProdutos seja um Map
        if (!(dadosProdutos instanceof Map)) {
            dadosProdutos = new Map();
        }
        
        const produto = dadosProdutos.get(codProduto);
        const nomeProduto = produto ? produto.nome_produto : codProduto;

        return `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <!-- Header -->
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-chart-line me-2"></i>
                            Cardex - ${codProduto}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>

                    <!-- Body -->
                    <div class="modal-body">
                        <!-- Info do Produto -->
                        <div class="produto-cardex-header mb-4">
                            <div class="row">
                                <div class="col-md-8">
                                    <h6 class="text-primary">${nomeProduto}</h6>
                                    <p class="text-muted mb-0">Análise de estoque para os próximos 28 dias</p>
                                </div>
                                <div class="col-md-4 text-end">
                                    <div class="cardex-resumo">
                                        <small class="text-muted">Estoque Atual</small>
                                        <br><strong class="h4 text-success">${this.formatarQuantidade(data.estoque_atual)}</strong>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Gráfico Resumo -->
                        <div class="cardex-resumo-visual mb-4">
                            <div class="row text-center">
                                <div class="col-3">
                                    <div class="stat-card bg-success bg-opacity-10 p-3 rounded">
                                        <h5 class="text-success mb-1">${this.formatarQuantidade(data.maior_estoque.valor)}</h5>
                                        <small class="text-muted">Maior Pico</small>
                                        <br><small class="text-success">D+${data.maior_estoque.dia}</small>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="stat-card bg-warning bg-opacity-10 p-3 rounded">
                                        <h5 class="text-warning mb-1">${this.formatarQuantidade(data.menor_estoque.valor)}</h5>
                                        <small class="text-muted">Menor Estoque</small>
                                        <br><small class="text-warning">D+${data.menor_estoque.dia}</small>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="stat-card bg-info bg-opacity-10 p-3 rounded">
                                        <h5 class="text-info mb-1">${this.formatarQuantidade(data.total_producao)}</h5>
                                        <small class="text-muted">Produção Total</small>
                                        <br><small class="text-info">28 dias</small>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="stat-card bg-danger bg-opacity-10 p-3 rounded">
                                        <h5 class="text-danger mb-1">${this.formatarQuantidade(data.total_saidas)}</h5>
                                        <small class="text-muted">Saídas Total</small>
                                        <br><small class="text-danger">28 dias</small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Tabela Cardex -->
                        <div class="cardex-tabela">
                            <div class="table-responsive" style="max-height: 400px;">
                                <table class="table table-sm table-striped table-hover">
                                    <thead class="table-dark sticky-top">
                                        <tr>
                                            <th>Dia</th>
                                            <th>Data</th>
                                            <th class="text-end">Est. Inicial</th>
                                            <th class="text-end">
                                                Saídas
                                                <button class="btn btn-sm btn-link text-white p-0 ms-2" 
                                                        onclick="modalCardex.abrirCardexExpandido('${codProduto}')"
                                                        title="Ver detalhes de todas as saídas">
                                                    <i class="fas fa-expand-arrows-alt"></i>
                                                </button>
                                            </th>
                                            <th class="text-end">Saldo</th>
                                            <th class="text-end">Produção</th>
                                            <th class="text-end">Est. Final</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${this.renderizarLinhasCardex(data.cardex)}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Alertas -->
                        ${data.alertas && data.alertas.length > 0 ? this.renderizarAlertas(data.alertas) : ''}
                    </div>

                    <!-- Footer -->
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times me-1"></i> Fechar
                        </button>
                        <button type="button" class="btn btn-primary" onclick="modalCardex.exportarCardex('${codProduto}')">
                            <i class="fas fa-download me-1"></i> Exportar Excel
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    renderizarLinhasCardex(cardex) {
        console.log('🔍 DEBUG Cardex - Primeiro dia:', cardex[0]);
        console.log('   - Data original:', cardex[0]?.data);
        console.log('   - Data convertida:', new Date(cardex[0]?.data));
        console.log('   - Data com correção:', new Date(cardex[0]?.data + 'T12:00:00'));
        console.log('   - Data local:', new Date().toLocaleDateString('pt-BR'));
        console.log('   - Timezone offset:', new Date().getTimezoneOffset());

        // Debug dos valores de estoque_final
        console.log('📊 DEBUG - Valores de estoque_final:');
        cardex.slice(0, 5).forEach((dia, idx) => {
            console.log(`   Dia ${idx}: estoque_final = ${dia.estoque_final} (tipo: ${typeof dia.estoque_final})`);
        });

        return cardex.map((dia, index) => {
            const statusClass = this.getStatusClasseCardex(dia);
            const dataFormatada = this.formatarData(dia.data);
            const hasOutput = dia.saidas !== undefined && dia.saidas !== null && dia.saidas > 0;

            return `
                <tr class="${statusClass.rowClass}" data-dia="${index}" data-data="${dia.data}">
                    <td>
                        <strong>D+${index}</strong>
                        ${hasOutput ? `
                            <button class="btn btn-link btn-sm p-0 ms-1"
                                    onclick="modalCardex.togglePedidosDetalhes('${dia.data}', ${index})"
                                    title="Ver pedidos previstos para este dia">
                                <i class="fas fa-chevron-down" id="icon-expand-${index}"></i>
                            </button>
                        ` : ''}
                    </td>
                    <td>${dataFormatada}</td>
                    <td class="text-end">${this.formatarQuantidade(dia.estoque_inicial)}</td>
                    <td class="text-end text-danger">
                        ${hasOutput ? `-${this.formatarQuantidade(dia.saidas)}` : '-'}
                    </td>
                    <td class="text-end">
                        <span class="badge ${dia.saldo <= 0 ? 'bg-danger' : 'bg-secondary'}">
                            ${this.formatarQuantidade(dia.saldo)}
                        </span>
                    </td>
                    <td class="text-end text-success">
                        ${dia.producao !== undefined && dia.producao !== null ? `+${this.formatarQuantidade(dia.producao)}` : '-'}
                    </td>
                    <td class="text-end">
                        <strong class="${dia.estoque_final <= 0 ? 'text-danger' : 'text-success'}">
                            ${this.formatarQuantidade(dia.estoque_final)}
                        </strong>
                    </td>
                    <td>
                        <span class="badge ${statusClass.badgeClass}">
                            ${statusClass.texto}
                        </span>
                    </td>
                </tr>
                <tr id="pedidos-row-${index}" class="pedidos-detalhes-row d-none">
                    <td colspan="8" class="p-0">
                        <div id="pedidos-container-${index}" class="pedidos-container bg-light">
                            <!-- Pedidos serão carregados aqui dinamicamente -->
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    getStatusClasseCardex(dia) {
        if (dia.estoque_final <= 0) {
            return {
                rowClass: 'table-danger',
                badgeClass: 'bg-danger',
                texto: 'Ruptura'
            };
        } else if (dia.estoque_final <= 10) {
            return {
                rowClass: 'table-warning',
                badgeClass: 'bg-warning',
                texto: 'Crítico'
            };
        } else if (dia.producao > 0) {
            return {
                rowClass: '',
                badgeClass: 'bg-info',
                texto: 'Produção'
            };
        } else {
            return {
                rowClass: '',
                badgeClass: 'bg-success',
                texto: 'Normal'
            };
        }
    }

    renderizarAlertas(alertas) {
        return `
            <div class="cardex-alertas mt-4">
                <h6 class="text-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Alertas Identificados
                </h6>
                <div class="list-group">
                    ${alertas.map(alerta => `
                        <div class="list-group-item list-group-item-${alerta.tipo}">
                            <div class="d-flex w-100 justify-content-between">
                                <h6 class="mb-1">${alerta.titulo}</h6>
                                <small>D+${alerta.dia}</small>
                            </div>
                            <p class="mb-1">${alerta.descricao}</p>
                            <small>${alerta.sugestao}</small>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    formatarData(dataStr) {
        // CORREÇÃO: Adicionar 'T12:00:00' para evitar problemas de timezone
        // Quando recebemos apenas a data (ex: "2024-07-28"), o JavaScript
        // pode interpretar como UTC 00:00, que seria o dia anterior no Brasil
        const dataComHora = dataStr.includes('T') ? dataStr : dataStr + 'T12:00:00';
        const data = new Date(dataComHora);

        return data.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: '2-digit'
        });
    }

    abrirCardexExpandido(codProduto) {
        console.log(`📊 Abrindo cardex expandido para produto ${codProduto}`);
        
        // Verificar se o script do cardex expandido está carregado
        if (!window.cardexExpandido) {
            // Carregar script dinamicamente se não estiver carregado
            const script = document.createElement('script');
            script.src = '/static/carteira/js/modal-cardex-expandido.js';
            script.onload = () => {
                if (window.cardexExpandido) {
                    window.cardexExpandido.abrirCardexExpandido(codProduto);
                }
            };
            document.head.appendChild(script);
        } else {
            window.cardexExpandido.abrirCardexExpandido(codProduto);
        }
    }

    exportarCardex(codProduto) {
        console.log(`📊 Exportando cardex para produto ${codProduto}`);

        // Implementação básica de exportação CSV
        try {
            const modal = document.querySelector('.modal.show');
            const table = modal.querySelector('table');

            if (!table) {
                alert('❌ Dados não encontrados para exportação');
                return;
            }

            // Converter tabela para CSV
            let csv = '';
            const rows = table.querySelectorAll('tr');

            rows.forEach(row => {
                const cols = row.querySelectorAll('th, td');
                const rowData = Array.from(cols).map(col =>
                    col.textContent.trim().replace(/,/g, ';')
                ).join(',');
                csv += rowData + '\n';
            });

            // Download do arquivo
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `cardex_${codProduto}_${new Date().toISOString().slice(0, 10)}.csv`;
            link.click();

            console.log('✅ Cardex exportado com sucesso');

        } catch (error) {
            console.error('❌ Erro ao exportar cardex:', error);
            alert('❌ Erro ao exportar dados');
        }
    }

    // Utilitários
    formatarQuantidade(qtd) {
        // Tratar valores null, undefined ou string vazia
        if (qtd === null || qtd === undefined || qtd === '') return '0';

        // Converter para número e formatar
        const numero = parseFloat(qtd);

        // Se não for um número válido, retornar '0'
        if (isNaN(numero)) return '0';

        // Formatar o número (incluindo negativos e zero)
        return numero.toLocaleString('pt-BR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    async togglePedidosDetalhes(data, index) {
        const pedidosRow = document.getElementById(`pedidos-row-${index}`);
        const pedidosContainer = document.getElementById(`pedidos-container-${index}`);
        const icon = document.getElementById(`icon-expand-${index}`);

        if (!pedidosRow) return;

        // Se já está visível, apenas ocultar
        if (!pedidosRow.classList.contains('d-none')) {
            pedidosRow.classList.add('d-none');
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
            return;
        }

        // Mostrar loading
        pedidosRow.classList.remove('d-none');
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
        pedidosContainer.innerHTML = `
            <div class="text-center p-3">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
                <span class="ms-2">Carregando pedidos...</span>
            </div>
        `;

        try {
            // Obter código do produto do modal atual
            const modalTitle = document.querySelector('.modal-title');
            const codProduto = modalTitle ? modalTitle.textContent.split(' - ')[1] : null;

            if (!codProduto) {
                throw new Error('Código do produto não encontrado');
            }

            // Buscar pedidos previstos
            const response = await fetch(`/estoque/api/cardex/${codProduto}/pedidos-previstos`);
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Erro ao carregar pedidos');
            }

            // Filtrar apenas o dia específico
            const pedidosDoDia = result.dados.find(d => d.data === data);

            if (!pedidosDoDia || pedidosDoDia.pedidos.length === 0) {
                pedidosContainer.innerHTML = `
                    <div class="p-3 text-muted text-center">
                        <i class="fas fa-info-circle"></i> Nenhum pedido previsto para este dia
                    </div>
                `;
                return;
            }

            // Renderizar pedidos
            pedidosContainer.innerHTML = `
                <div class="p-3">
                    <h6 class="mb-3 text-primary">
                        <i class="fas fa-box-open me-2"></i>
                        ${pedidosDoDia.total_pedidos} pedido(s) - Total: ${this.formatarQuantidade(pedidosDoDia.total_quantidade)} UN
                    </h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <thead>
                                <tr class="table-secondary">
                                    <th>Pedido</th>
                                    <th>Pedido Cliente</th>
                                    <th>Cliente</th>
                                    <th>Cidade/UF</th>
                                    <th class="text-end">Quantidade</th>
                                    <th>Status</th>
                                    <th>Agendamento</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${pedidosDoDia.pedidos.map(p => `
                                    <tr>
                                        <td><strong>${p.num_pedido}</strong></td>
                                        <td>${p.pedido_cliente}</td>
                                        <td title="${p.cnpj}">${p.cliente}</td>
                                        <td>${p.cidade}/${p.uf}</td>
                                        <td class="text-end"><strong>${this.formatarQuantidade(p.quantidade)}</strong></td>
                                        <td><span class="badge bg-${this.getStatusColor(p.status)}">${p.status}</span></td>
                                        <td>
                                            ${p.agendamento ? `
                                                <small>${p.agendamento}</small>
                                                ${p.protocolo ? `<br><small class="text-muted">Prot: ${p.protocolo}</small>` : ''}
                                            ` : '-'}
                                        </td>
                                    </tr>
                                    ${p.observacoes ? `
                                        <tr>
                                            <td colspan="7" class="ps-4">
                                                <small class="text-muted">
                                                    <i class="fas fa-comment me-1"></i> ${p.observacoes}
                                                </small>
                                            </td>
                                        </tr>
                                    ` : ''}
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

        } catch (error) {
            console.error('Erro ao carregar pedidos:', error);
            pedidosContainer.innerHTML = `
                <div class="p-3 text-danger text-center">
                    <i class="fas fa-exclamation-triangle"></i>
                    Erro ao carregar pedidos: ${error.message}
                </div>
            `;
        }
    }

    getStatusColor(status) {
        const statusColors = {
            'PREVISAO': 'secondary',
            'ABERTO': 'info',
            'COTADO': 'warning',
            'EMBARCADO': 'success',
            'FATURADO': 'primary',
            'NF no CD': 'danger',
            'CANCELADO': 'dark'
        };
        return statusColors[status] || 'secondary';
    }
}

// Disponibilizar globalmente
window.ModalCardex = ModalCardex;
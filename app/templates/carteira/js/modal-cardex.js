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

            // Renderizar modal de cardex
            this.mostrarModalCardex(codProduto, data, dadosProdutos);

        } catch (error) {
            console.error(`❌ Erro ao carregar cardex:`, error);
            alert(`Erro ao carregar cardex: ${error.message}`);
        }
    }

    mostrarModalCardex(codProduto, data, dadosProdutos) {
        // Remover modal existente se houver
        const modalExistente = document.getElementById('modal-cardex');
        if (modalExistente) {
            modalExistente.remove();
        }

        // Criar modal
        const modal = document.createElement('div');
        modal.id = 'modal-cardex';
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
            modal.remove();
        });
    }

    renderizarModalCardex(codProduto, data, dadosProdutos) {
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
                                            <th class="text-end">Saídas</th>
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
        return cardex.map((dia, index) => {
            const statusClass = this.getStatusClasseCardex(dia);
            const dataFormatada = this.formatarData(dia.data);
            
            return `
                <tr class="${statusClass.rowClass}">
                    <td><strong>D+${index}</strong></td>
                    <td>${dataFormatada}</td>
                    <td class="text-end">${this.formatarQuantidade(dia.estoque_inicial)}</td>
                    <td class="text-end text-danger">
                        ${dia.saidas ? `-${this.formatarQuantidade(dia.saidas)}` : '-'}
                    </td>
                    <td class="text-end">
                        <span class="badge ${dia.saldo <= 0 ? 'bg-danger' : 'bg-secondary'}">
                            ${this.formatarQuantidade(dia.saldo)}
                        </span>
                    </td>
                    <td class="text-end text-success">
                        ${dia.producao ? `+${this.formatarQuantidade(dia.producao)}` : '-'}
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
        const data = new Date(dataStr);
        return data.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: '2-digit'
        });
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
            link.download = `cardex_${codProduto}_${new Date().toISOString().slice(0,10)}.csv`;
            link.click();
            
            console.log('✅ Cardex exportado com sucesso');
            
        } catch (error) {
            console.error('❌ Erro ao exportar cardex:', error);
            alert('❌ Erro ao exportar dados');
        }
    }

    // Utilitários
    formatarQuantidade(qtd) {
        if (!qtd) return '0';
        return parseFloat(qtd).toLocaleString('pt-BR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }
}

// Disponibilizar globalmente
window.ModalCardex = ModalCardex;
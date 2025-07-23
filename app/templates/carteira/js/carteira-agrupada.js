/**
 * 🎯 CARTEIRA AGRUPADA - CONTROLADOR PRINCIPAL
 * Gerencia funcionalidades da página de carteira agrupada
 */

class CarteiraAgrupada {
    constructor() {
        this.dropdownSeparacoes = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initDropdownSeparacoes();
        console.log('✅ Carteira Agrupada inicializada');
    }

    setupEventListeners() {
        // Filtros de busca
        this.setupFiltros();
        
        // Botões de expandir/colapsar
        this.setupExpandirColapsar();
        
        // Botões de expansão de detalhes
        this.setupDetalhesExpansao();
    }

    setupFiltros() {
        const filtroBusca = document.getElementById('filtro-busca');
        const filtroStatus = document.getElementById('filtro-status');
        const filtroVendedor = document.getElementById('filtro-vendedor');

        if (filtroBusca) {
            filtroBusca.addEventListener('input', () => this.aplicarFiltros());
        }

        if (filtroStatus) {
            filtroStatus.addEventListener('change', () => this.aplicarFiltros());
        }

        if (filtroVendedor) {
            filtroVendedor.addEventListener('change', () => this.aplicarFiltros());
            this.popularFiltroVendedores();
        }
    }

    setupExpandirColapsar() {
        const btnExpandir = document.getElementById('expandir-todos');
        const btnColapsar = document.getElementById('colapsar-todos');

        if (btnExpandir) {
            btnExpandir.addEventListener('click', () => this.expandirTodos());
        }

        if (btnColapsar) {
            btnColapsar.addEventListener('click', () => this.colapsarTodos());
        }
    }

    setupDetalhesExpansao() {
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-expandir')) {
                const btn = e.target.closest('.btn-expandir');
                const numPedido = btn.dataset.pedido;
                this.toggleDetalhes(numPedido);
            }
        });
    }

    initDropdownSeparacoes() {
        if (window.DropdownSeparacoes) {
            this.dropdownSeparacoes = new window.DropdownSeparacoes();
        } else {
            console.warn('⚠️ DropdownSeparacoes não encontrado');
        }
    }

    // 🎯 FILTROS
    aplicarFiltros() {
        const termoBusca = document.getElementById('filtro-busca')?.value.toLowerCase() || '';
        const statusSelecionado = document.getElementById('filtro-status')?.value || '';
        const vendedorSelecionado = document.getElementById('filtro-vendedor')?.value || '';

        const linhasPedidos = document.querySelectorAll('.pedido-row');
        let totalVisiveis = 0;

        linhasPedidos.forEach(linha => {
            const textoFiltro = linha.dataset.filtro || '';
            const status = linha.dataset.status || '';
            const vendedor = linha.dataset.vendedor || '';

            const matchBusca = !termoBusca || textoFiltro.includes(termoBusca);
            const matchStatus = !statusSelecionado || status === statusSelecionado;
            const matchVendedor = !vendedorSelecionado || vendedor === vendedorSelecionado;

            const mostrar = matchBusca && matchStatus && matchVendedor;
            
            linha.style.display = mostrar ? '' : 'none';
            
            // Ocultar também a linha de detalhes se existe
            const numPedido = linha.dataset.pedido;
            const linhaDetalhes = document.getElementById(`detalhes-${numPedido}`);
            if (linhaDetalhes) {
                linhaDetalhes.style.display = mostrar ? '' : 'none';
            }

            if (mostrar) totalVisiveis++;
        });

        console.log(`🔍 Filtros aplicados: ${totalVisiveis} pedidos visíveis`);
    }

    popularFiltroVendedores() {
        const filtroVendedor = document.getElementById('filtro-vendedor');
        if (!filtroVendedor) return;

        const vendedores = new Set();
        document.querySelectorAll('.pedido-row').forEach(linha => {
            const vendedor = linha.dataset.vendedor;
            if (vendedor) vendedores.add(vendedor);
        });

        // Limpar e popular
        filtroVendedor.innerHTML = '<option value="">Todos vendedores</option>';
        [...vendedores].sort().forEach(vendedor => {
            const option = document.createElement('option');
            option.value = vendedor;
            option.textContent = vendedor;
            filtroVendedor.appendChild(option);
        });
    }

    // 🎯 EXPANDIR/COLAPSAR
    expandirTodos() {
        document.querySelectorAll('.pedido-row:not([style*="display: none"])').forEach(linha => {
            const numPedido = linha.dataset.pedido;
            const detalhesRow = document.getElementById(`detalhes-${numPedido}`);
            const icon = linha.querySelector('.expand-icon');
            
            if (detalhesRow && !detalhesRow.classList.contains('show')) {
                this.expandirDetalhes(numPedido, detalhesRow, icon);
            }
        });
        console.log('📖 Todos os pedidos expandidos');
    }

    colapsarTodos() {
        document.querySelectorAll('.detalhes-row.show').forEach(detalhesRow => {
            const numPedido = detalhesRow.id.replace('detalhes-', '');
            const linha = document.querySelector(`[data-pedido="${numPedido}"]`);
            const icon = linha?.querySelector('.expand-icon');
            
            this.colapsarDetalhes(detalhesRow, icon);
        });
        console.log('📖 Todos os pedidos colapsados');
    }

    // 🎯 DETALHES DOS PEDIDOS
    toggleDetalhes(numPedido) {
        const detalhesRow = document.getElementById(`detalhes-${numPedido}`);
        const linha = document.querySelector(`[data-pedido="${numPedido}"]`);
        const icon = linha?.querySelector('.expand-icon');

        if (!detalhesRow) return;

        if (detalhesRow.classList.contains('show')) {
            this.colapsarDetalhes(detalhesRow, icon);
        } else {
            this.expandirDetalhes(numPedido, detalhesRow, icon);
        }
    }

    expandirDetalhes(numPedido, detalhesRow, icon) {
        detalhesRow.classList.add('show');
        if (icon) {
            icon.classList.remove('fa-chevron-right');
            icon.classList.add('fa-chevron-down');
        }

        // Carregar detalhes se ainda não carregou
        const contentDiv = document.getElementById(`content-${numPedido}`);
        const loadingDiv = document.getElementById(`loading-${numPedido}`);
        
        if (contentDiv && contentDiv.style.display === 'none') {
            this.carregarDetalhes(numPedido, contentDiv, loadingDiv);
        }
    }

    colapsarDetalhes(detalhesRow, icon) {
        detalhesRow.classList.remove('show');
        if (icon) {
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-right');
        }
    }

    async carregarDetalhes(numPedido, contentDiv, loadingDiv) {
        try {
            if (loadingDiv) loadingDiv.style.display = 'block';
            if (contentDiv) contentDiv.style.display = 'none';

            const response = await fetch(`/carteira/api/pedido/${numPedido}/detalhes`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar detalhes');
            }

            if (contentDiv) {
                contentDiv.innerHTML = this.renderizarDetalhes(data);
                contentDiv.style.display = 'block';
            }
            if (loadingDiv) loadingDiv.style.display = 'none';

        } catch (error) {
            console.error(`❌ Erro ao carregar detalhes do pedido ${numPedido}:`, error);
            if (contentDiv) {
                contentDiv.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Erro ao carregar detalhes: ${error.message}
                    </div>
                `;
                contentDiv.style.display = 'block';
            }
            if (loadingDiv) loadingDiv.style.display = 'none';
        }
    }

    renderizarDetalhes(data) {
        if (!data.itens || data.itens.length === 0) {
            return `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p>Nenhum item encontrado para este pedido.</p>
                </div>
            `;
        }

        let html = `
            <div class="detalhes-pedido">
                <div class="table-responsive">
                    <table class="table table-sm table-striped">
                        <thead class="table-primary">
                            <tr>
                                <th>Produto</th>
                                <th>Quantidade</th>
                                <th>Preço Unit.</th>
                                <th>Valor Total</th>
                                <th>Estoque</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        data.itens.forEach(item => {
            html += `
                <tr>
                    <td>
                        <strong>${item.cod_produto}</strong>
                        <br><small class="text-muted">${item.nome_produto || ''}</small>
                    </td>
                    <td class="text-end">
                        ${this.formatarQuantidade(item.qtd_saldo_produto_pedido)}
                    </td>
                    <td class="text-end">
                        ${this.formatarMoeda(item.preco_produto_pedido)}
                    </td>
                    <td class="text-end">
                        <strong>${this.formatarMoeda((item.qtd_saldo_produto_pedido || 0) * (item.preco_produto_pedido || 0))}</strong>
                    </td>
                    <td class="text-end">
                        <span class="badge ${item.estoque > 0 ? 'bg-success' : 'bg-danger'}">
                            ${this.formatarQuantidade(item.estoque)}
                        </span>
                    </td>
                    <td>
                        <span class="badge bg-secondary">${item.status_item || 'Pendente'}</span>
                    </td>
                </tr>
            `;
        });

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        return html;
    }

    // 🎯 UTILITÁRIOS
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
            maximumFractionDigits: 3
        });
    }
}

// 🎯 FUNÇÕES GLOBAIS PARA ONCLICK (BOTÕES DOS CARDS)
function editarSeparacao(loteId) {
    console.log(`✏️ Editar separação ${loteId}`);
    // TODO: Implementar modal de edição
}

function imprimirSeparacao(loteId) {
    console.log(`🖨️ Imprimir separação ${loteId}`);
    // TODO: Implementar impressão
}

function cancelarSeparacao(loteId) {
    if (confirm(`Tem certeza que deseja cancelar a separação ${loteId}?`)) {
        console.log(`🗑️ Cancelar separação ${loteId}`);
        // TODO: Implementar cancelamento
    }
}

function criarSeparacao(numPedido) {
    console.log(`📦 Delegando criação de separação para SeparacaoManager`);
    if (window.separacaoManager) {
        window.separacaoManager.criarSeparacaoCompleta(numPedido);
    } else {
        console.error('❌ Separação Manager não inicializado');
    }
}

function avaliarEstoques(numPedido) {
    console.log(`📊 Avaliar estoques do pedido ${numPedido}`);
    
    // Abrir workspace para visualizar dados de estoque
    const btnExpandir = document.querySelector(`[data-pedido="${numPedido}"].btn-expandir`);
    if (btnExpandir && window.workspace) {
        // Se já está expandido, focar na tabela de produtos
        const detalhesRow = document.getElementById(`detalhes-${numPedido}`);
        if (detalhesRow && detalhesRow.classList.contains('show')) {
            // Já expandido, focar na tabela de produtos
            const tabelaProdutos = detalhesRow.querySelector('.workspace-produtos-table');
            if (tabelaProdutos) {
                tabelaProdutos.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                detalhesRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        } else {
            // Expandir primeiro
            btnExpandir.click();
            
            // Aguardar expansão e focar na tabela
            setTimeout(() => {
                const detalhesExpandido = document.getElementById(`detalhes-${numPedido}`);
                if (detalhesExpandido) {
                    const tabelaProdutos = detalhesExpandido.querySelector('.workspace-produtos-table');
                    if (tabelaProdutos) {
                        tabelaProdutos.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    } else {
                        detalhesExpandido.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }, 800);
        }
    }
}

function solicitarAgendamento(numPedido) {
    console.log(`🗓️ Solicitar agendamento do pedido ${numPedido}`);
    if (window.modalAgendamento) {
        window.modalAgendamento.abrirModalAgendamento(numPedido);
    } else {
        console.error('❌ Modal de agendamento não inicializado');
    }
}

function abrirModalEndereco(numPedido) {
    console.log(`📍 Abrir modal de endereço do pedido ${numPedido}`);
    if (window.modalEndereco) {
        window.modalEndereco.abrirModalEndereco(numPedido);
    } else {
        console.error('❌ Modal de endereço não inicializado');
    }
}

// 🎯 INICIALIZAÇÃO GLOBAL
window.CarteiraAgrupada = CarteiraAgrupada;
/**
 * 🎯 CARTEIRA AGRUPADA - CONTROLADOR PRINCIPAL
 * Gerencia funcionalidades da página de carteira agrupada
 */

class CarteiraAgrupada {
    constructor() {
        this.dropdownSeparacoes = null;
        this.filtrosAtivos = {
            rotas: new Set(),
            incoterms: new Set(),
            subrotas: new Set()
        };
        this.maxFiltrosAtivos = 3; // Máximo de badges selecionados simultaneamente
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initDropdownSeparacoes();
        this.initWorkspace();
        this.initBadgesFiltros();
        console.log('✅ Carteira Agrupada inicializada');
    }

    initWorkspace() {
        // Garantir que o workspace seja criado globalmente
        if (!window.workspace && window.WorkspaceMontagem) {
            window.workspace = new window.WorkspaceMontagem();
            console.log('✅ Workspace global criado');
        } else if (!window.WorkspaceMontagem) {
            console.error('❌ WorkspaceMontagem não encontrado - verifique se o script foi carregado');
        }
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
        const filtroEquipe = document.getElementById('filtro-equipe');

        if (filtroBusca) {
            filtroBusca.addEventListener('input', () => this.aplicarFiltros());
        }

        if (filtroStatus) {
            filtroStatus.addEventListener('change', () => this.aplicarFiltros());
        }

        if (filtroEquipe) {
            filtroEquipe.addEventListener('change', () => this.aplicarFiltros());
            this.popularFiltroEquipes();
        }
    }

    initBadgesFiltros() {
        // Event listeners para badges
        document.querySelectorAll('.badge-filtro').forEach(badge => {
            badge.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🔍 Badge clicado:', badge.dataset.tipo, badge.dataset.valor);
                this.toggleBadgeFiltro(badge);
            });
        });

        // Botões de limpar
        const limparRotas = document.getElementById('limpar-rotas');
        const limparSubrotas = document.getElementById('limpar-subrotas');
        const limparAgendamento = document.getElementById('limpar-agendamento');

        if (limparRotas) {
            limparRotas.addEventListener('click', () => this.limparFiltrosRotas());
        }

        if (limparSubrotas) {
            limparSubrotas.addEventListener('click', () => this.limparFiltrosSubrotas());
        }
        
        if (limparAgendamento) {
            limparAgendamento.addEventListener('click', () => this.limparFiltrosAgendamento());
        }
        
        console.log('✅ Badges de filtros inicializados. Total de badges:', document.querySelectorAll('.badge-filtro').length);
    }

    toggleBadgeFiltro(badge) {
        const tipo = badge.dataset.tipo;
        const valor = badge.dataset.valor;

        // Tratamento especial para agendamento (exclusivo mútuo)
        if (tipo === 'agendamento') {
            this.toggleAgendamento(badge, valor);
            return;
        }

        // Verificar limite de filtros ativos (não se aplica a agendamento)
        const totalAtivos = this.filtrosAtivos.rotas.size +
            this.filtrosAtivos.incoterms.size +
            this.filtrosAtivos.subrotas.size;

        const isActive = badge.classList.contains('ativo');

        if (!isActive && totalAtivos >= this.maxFiltrosAtivos) {
            // Mostrar mensagem de limite
            this.mostrarAlerta('Você pode selecionar no máximo 3 filtros simultaneamente');
            return;
        }

        // Toggle do badge com classe 'ativo' e estilos
        badge.classList.toggle('ativo');
        
        // Aplicar ou remover estilos visuais
        if (badge.classList.contains('ativo')) {
            // Estado ativo (preenchido)
            if (tipo === 'rota') {
                badge.style.backgroundColor = '#0d6efd';
                badge.style.color = 'white';
                badge.style.borderColor = '#0d6efd';
                this.filtrosAtivos.rotas.add(valor);
                // Se ativou SP, mostrar subrotas
                if (valor === 'SP') {
                    this.mostrarSubrotasSP();
                }
            } else if (tipo === 'incoterm') {
                if (valor === 'FOB') {
                    badge.style.backgroundColor = '#ffc107';
                    badge.style.color = '#000';
                    badge.style.borderColor = '#ffc107';
                } else if (valor === 'RED') {
                    badge.style.backgroundColor = '#dc3545';
                    badge.style.color = 'white';
                    badge.style.borderColor = '#dc3545';
                }
                this.filtrosAtivos.incoterms.add(valor);
            } else if (tipo === 'subrota') {
                badge.style.backgroundColor = '#6c757d';
                badge.style.color = 'white';
                badge.style.borderColor = '#6c757d';
                this.filtrosAtivos.subrotas.add(valor);
            }
        } else {
            // Estado inativo (outline)
            badge.style.backgroundColor = 'transparent';
            if (tipo === 'rota') {
                badge.style.color = '#0d6efd';
                badge.style.borderColor = '#0d6efd';
                this.filtrosAtivos.rotas.delete(valor);
                // Se desativou SP, esconder subrotas
                if (valor === 'SP') {
                    this.esconderSubrotasSP();
                }
            } else if (tipo === 'incoterm') {
                if (valor === 'FOB') {
                    badge.style.color = '#ffc107';
                    badge.style.borderColor = '#ffc107';
                } else if (valor === 'RED') {
                    badge.style.color = '#dc3545';
                    badge.style.borderColor = '#dc3545';
                }
                this.filtrosAtivos.incoterms.delete(valor);
            } else if (tipo === 'subrota') {
                badge.style.color = '#6c757d';
                badge.style.borderColor = '#6c757d';
                this.filtrosAtivos.subrotas.delete(valor);
            }
        }

        // Mostrar/ocultar botões de limpar
        this.atualizarBotoesLimpar();

        // Aplicar filtros
        this.aplicarFiltros();

        // Verificar e mostrar subrotas SP se necessário
        this.verificarSubrotasSP();
    }

    verificarSubrotasSP() {
        const container = document.querySelector('.subrotas-sp-container');
        if (!container) return;

        // Mostrar subrotas se rota SP estiver ativa
        const spAtivo = this.filtrosAtivos.rotas.has('SP');
        container.style.display = spAtivo ? 'block' : 'none';
    }
    
    mostrarSubrotasSP() {
        const container = document.querySelector('.subrotas-sp-container');
        if (container) {
            container.style.display = 'block';
        }
    }
    
    esconderSubrotasSP() {
        const container = document.querySelector('.subrotas-sp-container');
        if (container) {
            container.style.display = 'none';
            // Limpar filtros de subrotas ao esconder
            document.querySelectorAll('.badge-subrota').forEach(badge => {
                badge.classList.remove('ativo');
            });
            this.filtrosAtivos.subrotas.clear();
        }
    }

    atualizarBotoesLimpar() {
        const limparRotas = document.getElementById('limpar-rotas');
        const limparSubrotas = document.getElementById('limpar-subrotas');
        const limparAgendamento = document.getElementById('limpar-agendamento');

        if (limparRotas) {
            const temFiltrosRotas = this.filtrosAtivos.rotas.size > 0 || this.filtrosAtivos.incoterms.size > 0;
            limparRotas.style.display = temFiltrosRotas ? 'inline-block' : 'none';
        }

        if (limparSubrotas) {
            limparSubrotas.style.display = this.filtrosAtivos.subrotas.size > 0 ? 'inline-block' : 'none';
        }
        
        if (limparAgendamento) {
            limparAgendamento.style.display = this.filtrosAtivos.agendamento ? 'inline-block' : 'none';
        }
    }

    toggleAgendamento(badge, valor) {
        // Remover ativo de todos os badges de agendamento
        document.querySelectorAll('.badge-agendamento').forEach(b => {
            b.classList.remove('ativo');
            // Restaurar estilo outline (não clicado)
            if (b.dataset.valor === 'sem') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#dc3545';
                b.style.borderColor = '#dc3545';
            } else {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#198754';
                b.style.borderColor = '#198754';
            }
        });
        
        // Se clicou no mesmo que já estava ativo, desativar
        if (this.filtrosAtivos.agendamento === valor) {
            this.filtrosAtivos.agendamento = null;
            document.getElementById('limpar-agendamento').style.display = 'none';
        } else {
            // Ativar o novo com estilo preenchido
            badge.classList.add('ativo');
            if (valor === 'sem') {
                badge.style.backgroundColor = '#dc3545';
                badge.style.color = 'white';
                badge.style.borderColor = '#dc3545';
            } else {
                badge.style.backgroundColor = '#198754';
                badge.style.color = 'white';
                badge.style.borderColor = '#198754';
            }
            this.filtrosAtivos.agendamento = valor;
            document.getElementById('limpar-agendamento').style.display = 'inline-block';
        }
        
        this.aplicarFiltros();
    }

    limparFiltrosRotas() {
        // Limpar badges de rotas e incoterms
        document.querySelectorAll('.badge-rota, .badge-incoterm').forEach(badge => {
            badge.classList.remove('ativo');
            badge.style.backgroundColor = 'transparent';
            
            // Restaurar cores outline
            if (badge.classList.contains('badge-rota')) {
                badge.style.color = '#0d6efd';
                badge.style.borderColor = '#0d6efd';
            } else if (badge.dataset.valor === 'FOB') {
                badge.style.color = '#ffc107';
                badge.style.borderColor = '#ffc107';
            } else if (badge.dataset.valor === 'RED') {
                badge.style.color = '#dc3545';
                badge.style.borderColor = '#dc3545';
            }
        });

        this.filtrosAtivos.rotas.clear();
        this.filtrosAtivos.incoterms.clear();
        this.esconderSubrotasSP();

        this.atualizarBotoesLimpar();
        this.aplicarFiltros();
    }

    limparFiltrosSubrotas() {
        // Limpar badges de subrotas
        document.querySelectorAll('.badge-subrota').forEach(badge => {
            badge.classList.remove('ativo');
            badge.style.backgroundColor = 'transparent';
            badge.style.color = '#6c757d';
            badge.style.borderColor = '#6c757d';
        });

        this.filtrosAtivos.subrotas.clear();

        this.atualizarBotoesLimpar();
        this.aplicarFiltros();
    }
    
    limparFiltrosAgendamento() {
        document.querySelectorAll('.badge-agendamento').forEach(badge => {
            badge.classList.remove('ativo');
            badge.style.backgroundColor = 'transparent';
            
            // Restaurar cores outline
            if (badge.dataset.valor === 'sem') {
                badge.style.color = '#dc3545';
                badge.style.borderColor = '#dc3545';
            } else {
                badge.style.color = '#198754';
                badge.style.borderColor = '#198754';
            }
        });
        this.filtrosAtivos.agendamento = null;
        this.aplicarFiltros();
        document.getElementById('limpar-agendamento').style.display = 'none';
    }

    mostrarAlerta(mensagem) {
        // Criar alerta temporário
        const alerta = document.createElement('div');
        alerta.className = 'alert alert-warning alert-dismissible fade show position-fixed';
        alerta.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 350px;';
        alerta.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${mensagem}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alerta);

        // Remover após 3 segundos
        setTimeout(() => {
            alerta.remove();
        }, 3000);
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
        const equipeSelecionada = document.getElementById('filtro-equipe')?.value || '';

        const linhasPedidos = document.querySelectorAll('.pedido-row');
        let totalVisiveis = 0;

        linhasPedidos.forEach(linha => {
            const textoFiltro = linha.dataset.filtro || '';
            const status = linha.dataset.status || '';
            const equipe = linha.dataset.equipe || '';
            const rota = linha.dataset.rota || '';
            const subrota = linha.dataset.subrota || '';
            const incoterm = linha.dataset.incoterm || 'CIF';
            const agendamento = linha.dataset.agendamento || 'sem';

            // Aplicar filtros básicos
            const matchBusca = !termoBusca || textoFiltro.includes(termoBusca);
            const matchStatus = !statusSelecionado || status === statusSelecionado;
            const matchEquipe = !equipeSelecionada || equipe === equipeSelecionada;
            
            // Filtro de agendamento
            let matchAgendamento = true;
            if (this.filtrosAtivos.agendamento) {
                matchAgendamento = agendamento === this.filtrosAtivos.agendamento;
            }

            let matchBadges = true;

            // Filtros de badges (rotas/incoterms)
            if (this.filtrosAtivos.rotas.size > 0 || this.filtrosAtivos.incoterms.size > 0) {
                matchBadges = false;

                // Verificar incoterms FOB e RED primeiro
                if (this.filtrosAtivos.incoterms.has('FOB') && incoterm === 'FOB') {
                    matchBadges = true;
                } else if (this.filtrosAtivos.incoterms.has('RED') && incoterm === 'RED') {
                    matchBadges = true;
                }
                // Se o pedido é CIF, verificar rotas
                else if (incoterm === 'CIF' && this.filtrosAtivos.rotas.size > 0) {
                    if (this.filtrosAtivos.rotas.has(rota)) {
                        matchBadges = true;
                    }
                }
            }

            // Filtros de subrotas (apenas para SP)
            let matchSubrotas = true;
            if (this.filtrosAtivos.subrotas.size > 0) {
                // Se tem filtro de subrota ativo, só mostra pedidos de SP que tenham a subrota selecionada
                if (linha.dataset.uf === 'SP') {
                    matchSubrotas = this.filtrosAtivos.subrotas.has(subrota);
                } else {
                    // Se não é SP, não mostra quando há filtro de subrota ativo
                    matchSubrotas = false;
                }
            }

            const mostrar = matchBusca && matchStatus && matchEquipe && matchAgendamento && matchBadges && matchSubrotas;

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

        // Atualizar contador de pedidos
        this.atualizarContador(totalVisiveis);

        // Verificar e mostrar/ocultar subrotas SP
        this.verificarSubrotasSP();
    }

    popularFiltroEquipes() {
        const filtroEquipe = document.getElementById('filtro-equipe');
        if (!filtroEquipe) return;

        const equipes = new Set();
        document.querySelectorAll('.pedido-row').forEach(linha => {
            const equipe = linha.dataset.equipe;
            if (equipe) equipes.add(equipe);
        });

        // Limpar e popular
        filtroEquipe.innerHTML = '<option value="">Todas equipes</option>';
        [...equipes].sort().forEach(equipe => {
            const option = document.createElement('option');
            option.value = equipe;
            option.textContent = equipe;
            filtroEquipe.appendChild(option);
        });
    }

    atualizarContador(totalVisiveis) {
        // Atualizar contador de pedidos visíveis
        const contador = document.getElementById('contador-pedidos');
        if (contador) {
            contador.textContent = totalVisiveis;
        }
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

        // Verificar se o conteúdo já foi carregado
        // Se não tem conteúdo HTML ou está oculto, carregar
        if (contentDiv && (!contentDiv.innerHTML.trim() || contentDiv.style.display === 'none')) {
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

            // Tentar carregar o workspace se disponível
            if (window.workspace && window.workspace.abrirWorkspace) {
                console.log(`🔧 Carregando workspace para pedido ${numPedido}`);
                await window.workspace.abrirWorkspace(numPedido);
                // O workspace já renderiza o conteúdo no contentDiv
                return;
            }

            // Fallback: carregar apenas detalhes simples se workspace não disponível
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
}// 🎯 INICIALIZAÇÃO GLOBAL
window.CarteiraAgrupada = CarteiraAgrupada;


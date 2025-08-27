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
            subrotas: new Set(),
            agendamento: null  // null, 'com' ou 'sem'
        };
        this.maxFiltrosAtivos = 3; // Máximo de badges selecionados simultaneamente
        this.init();
    }

    init() {
        console.log('🚀 Inicializando CarteiraAgrupada...');
        this.setupEventListeners();
        this.initDropdownSeparacoes();
        this.initWorkspace();
        this.initBadgesFiltros();
        this.setupInterceptadorBotoes(); // 🆕 Interceptar cliques em botões
        console.log('✅ Carteira Agrupada inicializada');
        
        // Debug: verificar se os badges foram encontrados
        const totalBadges = document.querySelectorAll('.bg-filtro').length;
        if (totalBadges === 0) {
            console.error('❌ ERRO: Nenhum badge .bg-filtro encontrado no DOM!');
        } else {
            console.log(`✅ ${totalBadges} badges de filtro encontrados e configurados`);
        }
        
        // 🆕 Carregar separações compactas para todos os pedidos
        this.carregarTodasSeparacoesCompactas();
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
        // Event listeners para badges - CORREÇÃO: usar .bg-filtro em vez de .badge-filtro
        document.querySelectorAll('.bg-filtro').forEach(badge => {
            // Adicionar cursor pointer para indicar que é clicável
            badge.style.cursor = 'pointer';
            
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
        
        console.log('✅ Badges de filtros inicializados. Total de badges:', document.querySelectorAll('.bg-filtro').length);
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

            // Carregar apenas detalhes do pedido (separações já estão carregadas fora)
            const detalhesResponse = await fetch(`/carteira/api/pedido/${numPedido}/detalhes`);
            const detalhesData = await detalhesResponse.json();

            if (!detalhesResponse.ok || !detalhesData.success) {
                throw new Error(detalhesData.error || 'Erro ao carregar detalhes');
            }

            if (contentDiv) {
                // Renderizar apenas detalhes do pedido
                let html = `
                    <div class="detalhes-pedido">
                        <h6 class="mb-3">
                            <i class="fas fa-list me-2"></i>
                            Produtos do Pedido
                            <span id="loading-estoque-${numPedido}" class="spinner-border spinner-border-sm ms-2" style="display: none;">
                                <span class="visually-hidden">Carregando estoque...</span>
                            </span>
                        </h6>
                        <div id="tabela-produtos-${numPedido}">
                            ${this.renderizarDetalhesBasicos(detalhesData)}
                        </div>
                    </div>
                `;
                
                contentDiv.innerHTML = html;
                contentDiv.style.display = 'block';
            }
            if (loadingDiv) loadingDiv.style.display = 'none';
            
            // 🆕 CARREGAR ESTOQUE DE FORMA ASSÍNCRONA com prioridade alta
            this.carregarEstoqueComPrioridade(numPedido, detalhesData.itens, 'alta');

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

    formatarData(data) {
        if (!data) return '-';
        const d = new Date(data);
        return d.toLocaleDateString('pt-BR');
    }

    formatarPeso(peso) {
        if (!peso) return '0 kg';
        return `${parseFloat(peso).toFixed(2)} kg`;
    }

    formatarPallet(pallet) {
        if (!pallet) return '0';
        return parseFloat(pallet).toFixed(2);
    }

    /**
     * 🆕 CARREGAR TODAS AS SEPARAÇÕES COMPACTAS
     */
    async carregarTodasSeparacoesCompactas() {
        console.log('📦 Carregando separações compactas para todos os pedidos...');
        
        // Buscar todos os pedidos na página
        const pedidoRows = document.querySelectorAll('.pedido-row');
        
        for (const row of pedidoRows) {
            const numPedido = row.dataset.pedido;
            if (numPedido) {
                // Carregar separações compactas para este pedido
                this.carregarSeparacoesCompactasPedido(numPedido);
            }
        }
    }
    
    /**
     * 🆕 CARREGAR SEPARAÇÕES COMPACTAS PARA UM PEDIDO
     */
    async carregarSeparacoesCompactasPedido(numPedido) {
        try {
            // Fazer requisições em paralelo
            const [separacoesResponse, preSeparacoesResponse] = await Promise.all([
                fetch(`/carteira/api/pedido/${numPedido}/separacoes-completas`).catch(() => null),
                fetch(`/carteira/api/pedido/${numPedido}/pre-separacoes`).catch(() => null)
            ]);
            
            let separacoesData = null;
            let preSeparacoesData = null;
            
            if (separacoesResponse && separacoesResponse.ok) {
                separacoesData = await separacoesResponse.json();
            }
            if (preSeparacoesResponse && preSeparacoesResponse.ok) {
                preSeparacoesData = await preSeparacoesResponse.json();
            }
            
            // Renderizar separações compactas se houver dados
            const html = this.renderizarSeparacoesCompactas(separacoesData, preSeparacoesData);
            
            if (html) {
                const container = document.querySelector(`#separacoes-compactas-${numPedido} .separacoes-compactas-container`);
                const row = document.getElementById(`separacoes-compactas-${numPedido}`);
                
                if (container && row) {
                    container.innerHTML = html;
                    row.style.display = 'table-row';
                }
            }
            
        } catch (error) {
            console.error(`❌ Erro ao carregar separações compactas para ${numPedido}:`, error);
        }
    }

    /**
     * 🆕 RENDERIZAÇÃO COMPACTA DE SEPARAÇÕES E PRÉ-SEPARAÇÕES
     */
    renderizarSeparacoesCompactas(separacoesData, preSeparacoesData) {
        const todasSeparacoes = [];
        
        // Adicionar separações confirmadas
        if (separacoesData && separacoesData.success && separacoesData.separacoes) {
            separacoesData.separacoes.forEach(sep => {
                todasSeparacoes.push({
                    tipo: 'Separação',
                    status: sep.status || '',
                    loteId: sep.separacao_lote_id,
                    valor: sep.valor_total || 0,
                    peso: sep.peso_total || 0,
                    pallet: sep.pallet_total || 0,
                    expedicao: sep.expedicao,
                    agendamento: sep.agendamento,
                    protocolo: sep.protocolo,
                    agendamento_confirmado: sep.agendamento_confirmado,
                    embarque: sep.embarque,
                    isSeparacao: true
                });
            });
        }
        
        // Adicionar pré-separações
        if (preSeparacoesData && preSeparacoesData.success && preSeparacoesData.lotes) {
            preSeparacoesData.lotes.forEach(lote => {
                todasSeparacoes.push({
                    tipo: 'Pré-separação',
                    status: '',
                    loteId: lote.lote_id,
                    valor: lote.totais?.valor || 0,
                    peso: lote.totais?.peso || 0,
                    pallet: lote.totais?.pallet || 0,
                    expedicao: lote.data_expedicao,
                    agendamento: lote.data_agendamento,
                    protocolo: lote.protocolo,
                    agendamento_confirmado: lote.agendamento_confirmado || false,
                    embarque: null,
                    isSeparacao: false
                });
            });
        }
        
        // Se não houver nenhuma separação
        if (todasSeparacoes.length === 0) {
            return '';
        }
        
        // Renderizar tabela compacta
        return `
            <div class="separacoes-compactas-container bg-white p-2 border-bottom">
                <div class="table-responsive">
                    <table class="table table-sm table-hover mb-0">
                        <thead style="background-color: #1a2332 !important; border-bottom: 2px solid #2a3442;">
                            <tr>
                                <th width="100" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Tipo</th>
                                <th width="80" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Status</th>
                                <th class="text-end" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Valor</th>
                                <th class="text-end" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Peso</th>
                                <th class="text-end" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Pallet</th>
                                <th class="text-center" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Expedição</th>
                                <th class="text-center" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Agendamento</th>
                                <th style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Protocolo</th>
                                <th class="text-center" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Confirmação</th>
                                <th style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Embarque</th>
                                <th width="220" class="text-center" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${todasSeparacoes.map(item => this.renderizarLinhaSeparacaoCompacta(item)).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    /**
     * 🆕 RENDERIZAR LINHA INDIVIDUAL DA SEPARAÇÃO COMPACTA
     */
    renderizarLinhaSeparacaoCompacta(item) {
        const tipoClass = item.isSeparacao ? 'text-primary' : 'text-warning';
        const statusBadge = item.status ? 
            (item.status === 'COTADO' ? '<span class="badge bg-warning text-dark">COTADO</span>' : 
             item.status === 'ABERTO' ? '<span class="badge bg-secondary">ABERTO</span>' : '') : '';
        
        const confirmacaoBadge = item.agendamento ? 
            (item.agendamento_confirmado ? 
                '<span class="badge bg-success"><i class="fas fa-check-circle"></i> Confirmado</span>' :
                '<span class="badge bg-warning text-dark"><i class="fas fa-hourglass-half"></i> Aguardando</span>') : '-';
        
        const embarqueInfo = item.embarque ? 
            `<span title="${item.embarque.transportadora || 'Sem transportadora'}" style="cursor: help;">
                #${item.embarque.numero || '-'} | ${item.embarque.data_prevista_embarque ? this.formatarData(item.embarque.data_prevista_embarque) : '-'}
             </span>` : '-';
        
        return `
            <tr>
                <td><strong class="${tipoClass}">${item.tipo}</strong></td>
                <td>${statusBadge}</td>
                <td class="text-end text-success">${this.formatarMoeda(item.valor)}</td>
                <td class="text-end">${this.formatarPeso(item.peso)}</td>
                <td class="text-end">${this.formatarPallet(item.pallet)}</td>
                <td class="text-center">${item.expedicao ? this.formatarData(item.expedicao) : '-'}</td>
                <td class="text-center">${item.agendamento ? this.formatarData(item.agendamento) : '-'}</td>
                <td><small>${item.protocolo || '-'}</small></td>
                <td class="text-center">${confirmacaoBadge}</td>
                <td><small>${embarqueInfo}</small></td>
                <td class="text-center">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary btn-sm" 
                                onclick="carteiraAgrupada.abrirModalDatas('${item.loteId}', ${item.isSeparacao})"
                                title="Editar datas">
                            <i class="fas fa-calendar-alt"></i> Datas
                        </button>
                        ${!item.isSeparacao ? `
                            <button class="btn btn-outline-success btn-sm" 
                                    onclick="carteiraAgrupada.confirmarPreSeparacao('${item.loteId}')"
                                    title="Confirmar separação">
                                <i class="fas fa-check"></i> Confirmar
                            </button>
                        ` : ''}
                        <button class="btn btn-outline-info btn-sm" 
                                onclick="carteiraAgrupada.agendarPortal('${item.loteId}', '${item.agendamento || ''}')"
                                title="Agendar no portal">
                            <i class="fas fa-calendar-plus"></i> Agendar
                        </button>
                        ${item.protocolo ? `
                            <button class="btn btn-outline-warning btn-sm" 
                                    onclick="carteiraAgrupada.verificarAgendamento('${item.loteId}', '${item.protocolo}')"
                                    title="Verificar agendamento no portal">
                                <i class="fas fa-search"></i> Ver.Agenda
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }
    
    /**
     * 🆕 RENDERIZAR DETALHES BÁSICOS (sem estoque)
     */
    renderizarDetalhesBasicos(data) {
        if (!data.itens || data.itens.length === 0) {
            return `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p>Nenhum item encontrado para este pedido.</p>
                </div>
            `;
        }

        return `
            <div class="table-responsive">
                <table class="table table-sm table-striped">
                    <thead class="table-primary">
                        <tr>
                            <th>Produto</th>
                            <th class="text-end">Qtd Saldo</th>
                            <th class="text-end">Preço Unit.</th>
                            <th class="text-end">Valor Total</th>
                            <th class="text-end">Estoque</th>
                            <th class="text-end">Menor Est. D+7</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.itens.map(item => `
                            <tr>
                                <td>
                                    <strong>${item.cod_produto}</strong>
                                    <br><small class="text-muted">${item.nome_produto || ''}</small>
                                </td>
                                <td class="text-end">
                                    <strong>${this.formatarQuantidade(item.qtd_saldo_produto_pedido)}</strong>
                                </td>
                                <td class="text-end">
                                    ${this.formatarMoeda(item.preco_produto_pedido)}
                                </td>
                                <td class="text-end">
                                    <strong class="text-success">${this.formatarMoeda((item.qtd_saldo_produto_pedido || 0) * (item.preco_produto_pedido || 0))}</strong>
                                </td>
                                <td class="text-end" id="estoque-${item.cod_produto}">
                                    <span class="spinner-border spinner-border-sm text-primary"></span>
                                </td>
                                <td class="text-end" id="menor-estoque-${item.cod_produto}">
                                    <span class="spinner-border spinner-border-sm text-warning"></span>
                                </td>
                                <td>
                                    <span class="badge bg-secondary">${item.status_item || 'Pendente'}</span>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    /**
     * 🆕 CARREGAR ESTOQUE DE FORMA ASSÍNCRONA
     */
    async carregarEstoqueAssincrono(numPedido, itens) {
        try {
            console.log(`📊 Carregando estoque assíncrono para pedido ${numPedido}`);
            
            // Mostrar loading
            const loadingSpinner = document.getElementById(`loading-estoque-${numPedido}`);
            if (loadingSpinner) {
                loadingSpinner.style.display = 'inline-block';
            }
            
            // Fazer requisição para obter estoque
            const response = await fetch(`/carteira/api/pedido/${numPedido}/estoque`);
            
            if (!response.ok) {
                throw new Error('Erro ao carregar estoque');
            }
            
            const estoqueData = await response.json();
            
            if (estoqueData.success && estoqueData.produtos) {
                // Atualizar cada célula de estoque
                estoqueData.produtos.forEach(produto => {
                    const cellEstoque = document.getElementById(`estoque-${produto.cod_produto}`);
                    const cellMenorEstoque = document.getElementById(`menor-estoque-${produto.cod_produto}`);
                    
                    if (cellEstoque) {
                        const estoque = produto.estoque || produto.estoque_d0 || 0;
                        const badgeClass = estoque > 0 ? 'bg-success' : 'bg-danger';
                        cellEstoque.innerHTML = `
                            <span class="badge ${badgeClass}">
                                ${this.formatarQuantidade(estoque)}
                            </span>
                        `;
                    }
                    
                    if (cellMenorEstoque) {
                        const menorEstoque = produto.menor_estoque_produto_d7 || 0;
                        const badgeClass = menorEstoque <= 0 ? 'bg-danger' : menorEstoque < 10 ? 'bg-warning' : 'bg-secondary';
                        cellMenorEstoque.innerHTML = `
                            <span class="badge ${badgeClass}">
                                ${this.formatarQuantidade(menorEstoque)}
                            </span>
                        `;
                    }
                });
            }
            
            // Esconder loading
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar estoque:', error);
            
            // Esconder loading
            const loadingSpinner = document.getElementById(`loading-estoque-${numPedido}`);
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }
            
            // Mostrar erro nas células
            if (itens) {
                itens.forEach(item => {
                    const cellEstoque = document.getElementById(`estoque-${item.cod_produto}`);
                    const cellMenorEstoque = document.getElementById(`menor-estoque-${item.cod_produto}`);
                    
                    if (cellEstoque) {
                        cellEstoque.innerHTML = '<small class="text-muted">-</small>';
                    }
                    if (cellMenorEstoque) {
                        cellMenorEstoque.innerHTML = '<small class="text-muted">-</small>';
                    }
                });
            }
        }
    }
    
    /**
     * 🆕 FUNÇÕES AUXILIARES PARA BOTÕES
     */
    async abrirModalDatas(loteId, isSeparacao) {
        console.log(`📅 Abrindo modal de datas para ${loteId} (Separação: ${isSeparacao})`);
        
        // Redirecionar para workspace se disponível
        if (window.workspace) {
            if (isSeparacao) {
                window.workspace.editarDatasSeparacao(loteId);
            } else {
                window.workspace.editarDatasPreSeparacao(loteId);
            }
        } else {
            alert('Função de edição de datas em desenvolvimento');
        }
    }
    
    async confirmarPreSeparacao(loteId) {
        console.log(`✅ Confirmando pré-separação ${loteId}`);
        
        try {
            // Buscar dados da pré-separação para verificar se tem agendamento
            const response = await fetch(`/carteira/api/pre-separacao/${loteId}/detalhes`);
            let dadosPreSeparacao = null;
            
            if (response.ok) {
                dadosPreSeparacao = await response.json();
            }
            
            // Confirmar a pré-separação
            if (window.workspace && window.workspace.confirmarSeparacao) {
                await window.workspace.confirmarSeparacao(loteId);
                
                // 🆕 Se houver data de agendamento, agendar automaticamente no portal
                if (dadosPreSeparacao && dadosPreSeparacao.data_agendamento && !dadosPreSeparacao.protocolo) {
                    console.log('🤖 Agendando automaticamente no portal após confirmação...');
                    setTimeout(() => {
                        this.agendarPortal(loteId, dadosPreSeparacao.data_agendamento);
                    }, 2000); // Aguardar 2 segundos após confirmação
                }
            } else {
                if (confirm(`Confirmar pré-separação ${loteId}?`)) {
                    // Fazer confirmação via API se workspace não estiver disponível
                    const confirmResponse = await fetch(`/carteira/api/pre-separacao/${loteId}/confirmar`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                        }
                    });
                    
                    if (confirmResponse.ok) {
                        // 🆕 Agendar automaticamente se tiver data de agendamento
                        if (dadosPreSeparacao && dadosPreSeparacao.data_agendamento && !dadosPreSeparacao.protocolo) {
                            console.log('🤖 Agendando automaticamente no portal após confirmação...');
                            setTimeout(() => {
                                this.agendarPortal(loteId, dadosPreSeparacao.data_agendamento);
                            }, 2000);
                        } else {
                            location.reload();
                        }
                    }
                }
            }
        } catch (error) {
            console.error('❌ Erro ao confirmar pré-separação:', error);
            alert('Erro ao confirmar pré-separação. Verifique o console.');
        }
    }
    
    async agendarPortal(loteId, dataAgendamento) {
        console.log(`📆 Agendando no portal ${loteId}`);
        
        // Redirecionar para workspace se disponível
        if (window.workspace && window.workspace.agendarNoPortal) {
            window.workspace.agendarNoPortal(loteId, dataAgendamento);
        } else if (window.modalSeparacoes && window.modalSeparacoes.agendarNoPortal) {
            window.modalSeparacoes.agendarNoPortal(loteId, dataAgendamento);
        } else {
            alert('Função de agendamento no portal em desenvolvimento');
        }
    }
    
    async verificarAgendamento(loteId, protocolo) {
        console.log(`🔍 Verificando agendamento ${protocolo} para ${loteId}`);
        
        // Redirecionar para workspace se disponível
        if (window.workspace && window.workspace.verificarProtocoloNoPortal) {
            window.workspace.verificarProtocoloNoPortal(loteId, protocolo);
        } else if (window.modalSeparacoes && window.modalSeparacoes.verificarProtocoloNoPortal) {
            window.modalSeparacoes.verificarProtocoloNoPortal(loteId, protocolo);
        } else {
            alert('Função de verificação de protocolo em desenvolvimento');
        }
    }
    
    /**
     * 🆕 SISTEMA DE PRIORIDADES PARA CARREGAMENTO DE ESTOQUE
     */
    filaEstoque = [];
    processandoEstoque = false;
    estoqueTimeoutId = null;
    pausadoPorBotao = false;
    
    carregarEstoqueComPrioridade(numPedido, itens, prioridade = 'normal') {
        // Se está pausado por botão, adicionar à fila mas não processar
        if (this.pausadoPorBotao) {
            const item = { numPedido, itens, prioridade };
            if (prioridade === 'alta') {
                this.filaEstoque.unshift(item);
            } else {
                this.filaEstoque.push(item);
            }
            return;
        }
        
        // Cancelar processamento atual se for de prioridade menor
        if (this.processandoEstoque) {
            clearTimeout(this.estoqueTimeoutId);
            this.processandoEstoque = false;
        }
        
        // Adicionar à fila com prioridade
        const item = { numPedido, itens, prioridade };
        
        if (prioridade === 'alta') {
            // Alta prioridade vai para o início da fila
            this.filaEstoque.unshift(item);
        } else {
            // Normal vai para o final
            this.filaEstoque.push(item);
        }
        
        // Processar fila
        this.processarFilaEstoque();
    }
    
    async processarFilaEstoque() {
        // Se está pausado, não processar
        if (this.pausadoPorBotao) {
            return;
        }
        
        if (this.processandoEstoque || this.filaEstoque.length === 0) {
            // Se não há mais itens, verificar se RupturaEstoque precisa continuar
            if (this.filaEstoque.length === 0 && window.rupturaManager && !window.rupturaManager.pausado) {
                // Retomar análise de ruptura se estava pausada
                setTimeout(() => {
                    if (window.rupturaManager && window.rupturaManager.filaAnalises.length > 0) {
                        window.rupturaManager.processarFilaAnalises();
                    }
                }, 100);
            }
            return;
        }
        
        this.processandoEstoque = true;
        const { numPedido, itens } = this.filaEstoque.shift();
        
        // Processar imediatamente se não houver pausa, senão aguardar
        const delay = this.pausadoPorBotao ? 2000 : 100;
        
        this.estoqueTimeoutId = setTimeout(async () => {
            // Pausar RupturaEstoque enquanto carrega estoque
            if (window.rupturaManager) {
                window.rupturaManager.pausarAnalises();
            }
            
            await this.carregarEstoqueAssincrono(numPedido, itens);
            this.processandoEstoque = false;
            
            // Processar próximo da fila
            if (this.filaEstoque.length > 0) {
                this.processarFilaEstoque();
            } else {
                // Retomar RupturaEstoque quando terminar
                if (window.rupturaManager && !this.pausadoPorBotao) {
                    setTimeout(() => {
                        window.rupturaManager.retomarAnalises();
                    }, 100);
                }
            }
        }, delay);
    }
    
    // Interceptar cliques em botões para pausar carregamento
    setupInterceptadorBotoes() {
        document.addEventListener('click', (e) => {
            const target = e.target;
            const isButton = target.closest('button, .btn, a[href], [onclick]');
            
            if (isButton) {
                console.log('⏸️ Pausando carregamentos - botão clicado');
                
                // Marcar como pausado
                this.pausadoPorBotao = true;
                
                // Pausar carregamento de estoque em andamento
                if (this.processandoEstoque) {
                    clearTimeout(this.estoqueTimeoutId);
                    this.processandoEstoque = false;
                }
                
                // Pausar RupturaEstoque também
                if (window.rupturaManager) {
                    window.rupturaManager.pausarAnalises();
                }
                
                // Reagendar para 2 segundos depois
                setTimeout(() => {
                    console.log('▶️ Retomando carregamentos');
                    this.pausadoPorBotao = false;
                    
                    // Processar fila de estoque com prioridade alta primeiro
                    if (this.filaEstoque.length > 0) {
                        // Reordenar fila por prioridade
                        this.filaEstoque.sort((a, b) => {
                            if (a.prioridade === 'alta' && b.prioridade !== 'alta') return -1;
                            if (a.prioridade !== 'alta' && b.prioridade === 'alta') return 1;
                            return 0;
                        });
                        this.processarFilaEstoque();
                    } else if (window.rupturaManager) {
                        // Se não há estoque para carregar, retomar ruptura
                        window.rupturaManager.retomarAnalises();
                    }
                }, 2000);
            }
        }, true); // Capture phase para interceptar antes
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


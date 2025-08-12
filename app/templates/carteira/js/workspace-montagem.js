/**
 * 🎯 WORKSPACE DE MONTAGEM DE CARGA
 * Sistema de pré-separação com drag & drop
 */

class WorkspaceMontagem {
    constructor() {
        this.preSeparacoes = new Map(); // loteId -> {produtos: [], totais: {}}
        this.separacoesConfirmadas = []; // array de separações confirmadas
        this.produtosSelecionados = new Set();
        this.dadosProdutos = new Map(); // codProduto -> dados completos

        // Inicializar módulos
        this.loteManager = new LoteManager(this);
        this.modalCardex = new ModalCardex();
        this.preSeparacaoManager = new PreSeparacaoManager(this);

        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log('✅ Workspace de Montagem inicializado');
    }

    setupEventListeners() {
        // Detectar quando o dropdown de detalhes é aberto
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-expandir')) {
                const btn = e.target.closest('.btn-expandir');
                const numPedido = btn.dataset.pedido;
                this.abrirWorkspace(numPedido);
            }
        });
    }

    async abrirWorkspace(numPedido) {
        console.log(`🔄 Carregando workspace para pedido ${numPedido}`);

        try {
            // Carregar dados do workspace
            const workspaceResponse = await fetch(`/carteira/api/pedido/${numPedido}/workspace`);
            const workspaceData = await workspaceResponse.json();

            if (!workspaceResponse.ok || !workspaceData.success) {
                throw new Error(workspaceData.error || 'Erro ao carregar workspace');
            }

            // Armazenar dados dos produtos e status do pedido
            workspaceData.produtos.forEach(produto => {
                this.dadosProdutos.set(produto.cod_produto, produto);
            });

            // Armazenar status do pedido
            this.statusPedido = workspaceData.status_pedido || 'ABERTO';

            // Carregar pré-separações existentes usando o manager
            const preSeparacoesData = await this.preSeparacaoManager.carregarPreSeparacoes(numPedido);

            if (preSeparacoesData.success && preSeparacoesData.lotes) {
                // Processar pré-separações carregadas
                const preSeparacoesMap = this.preSeparacaoManager.processarPreSeparacoesCarregadas(preSeparacoesData.lotes);

                // Atualizar Map local
                preSeparacoesMap.forEach((value, key) => {
                    this.preSeparacoes.set(key, value);
                });

                console.log(`✅ Carregadas ${preSeparacoesData.lotes.length} pré-separações existentes`);
            }

            // Carregar separações confirmadas
            const separacoesResponse = await fetch(`/carteira/api/pedido/${numPedido}/separacoes-completas`);
            const separacoesData = await separacoesResponse.json();

            if (separacoesData.success && separacoesData.separacoes) {
                this.separacoesConfirmadas = separacoesData.separacoes;
                console.log(`✅ Carregadas ${separacoesData.separacoes.length} separações confirmadas`);
            }

            // Renderizar workspace no container de detalhes
            const contentDiv = document.getElementById(`content-${numPedido}`);
            const loadingDiv = document.getElementById(`loading-${numPedido}`);

            if (contentDiv) {
                contentDiv.innerHTML = this.renderizarWorkspace(numPedido, workspaceData);
                contentDiv.style.display = 'block';
            }
            if (loadingDiv) {
                loadingDiv.style.display = 'none';
            }

            // Renderizar lotes existentes se houver
            if (preSeparacoesData.success && preSeparacoesData.lotes) {
                await this.renderizarLotesExistentes(numPedido, preSeparacoesData.lotes);
            }

            // Configurar checkboxes e adição de produtos
            requestAnimationFrame(() => {
                console.log('🎯 Inicializando sistema de seleção...');
                this.configurarCheckboxes(numPedido);
            });

        } catch (error) {
            console.error(`❌ Erro ao carregar workspace:`, error);
            this.renderizarErroWorkspace(numPedido, error.message);
        }
    }

    async renderizarLotesExistentes(numPedido, lotes) {
        const container = document.getElementById(`lotes-container-${numPedido}`);
        if (!container || lotes.length === 0) return;

        // Remover placeholder
        const placeholder = container.querySelector('.lote-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // Renderizar cada lote existente
        for (const lote of lotes) {
            // Garantir que o mapa interno tenha os dados necessários para edição de datas
            try {
                if (!this.preSeparacoes) {
                    this.preSeparacoes = new Map();
                }
                // Normalizar produtos carregados do backend para o formato usado pelos handlers
                const produtos = (Array.isArray(lote.produtos) ? lote.produtos : []).map((p) => ({
                    codProduto: p.cod_produto || p.codProduto,
                    preSeparacaoId: p.pre_separacao_id || p.preSeparacaoId,
                    quantidade: p.quantidade,
                    valor: p.valor,
                    peso: p.peso,
                    pallet: p.pallet,
                    loteId: lote.lote_id,
                }));
                this.preSeparacoes.set(lote.lote_id, {
                    loteId: lote.lote_id,
                    dataExpedicao: lote.data_expedicao || '',
                    dataAgendamento: lote.data_agendamento || '',
                    protocolo: lote.protocolo || '',
                    produtos: produtos
                });
            } catch (e) {
                console.warn('Não foi possível registrar lote no mapa de pré-separações:', e);
            }
            const loteCard = document.createElement('div');
            loteCard.className = 'col-md-4 mb-3';
            loteCard.innerHTML = this.loteManager.renderizarCardPreSeparacao(lote);
            container.appendChild(loteCard);

            // Drag & drop removido - usando checkboxes
            const newCard = loteCard.querySelector('.lote-card');
        }

        console.log(`✅ Renderizados ${lotes.length} lotes de pré-separação`);
    }

    renderizarWorkspace(numPedido, data) {
        return `
            <div class="workspace-montagem" data-pedido="${numPedido}">
                <!-- Header do Workspace -->
                <div class="workspace-header bg-primary text-white p-3 rounded-top">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h5 class="mb-0">
                                <i class="fas fa-boxes me-2"></i>
                                Workspace de Montagem - Pedido ${numPedido}
                            </h5>
                            <small>Selecione os produtos e clique em "Adicionar" no lote desejado</small>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="workspace-resumo">
                                <strong>Total: ${this.formatarMoeda(data.valor_total || 0)}</strong>
                                <br><small>${data.produtos.length} produtos</small>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tabela de Produtos (Origem) -->
                <div class="workspace-produtos bg-light p-3">
                    <h6 class="mb-3">
                        <i class="fas fa-list me-2"></i>
                        Produtos do Pedido
                    </h6>
                    ${this.renderizarTabelaProdutos(data.produtos)}
                </div>

                <!-- Área de Separações Confirmadas -->
                ${this.separacoesConfirmadas && this.separacoesConfirmadas.length > 0 ? `
                <div class="workspace-separacoes-confirmadas p-3 bg-light">
                    <h6 class="mb-3">
                        <i class="fas fa-check-circle text-success me-2"></i>
                        Separações Confirmadas
                    </h6>
                    <div class="separacoes-confirmadas-container row" id="separacoes-confirmadas-${numPedido}">
                        ${this.renderizarSeparacoesConfirmadas()}
                    </div>
                </div>
                ` : ''}

                <!-- Área de Lotes (Destino) -->
                <div class="workspace-lotes p-3">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6 class="mb-0">
                            <i class="fas fa-layer-group me-2"></i>
                            Pré-Separações
                        </h6>
                        <button class="btn btn-success btn-sm" onclick="workspace.criarNovoLote('${numPedido}')">
                            <i class="fas fa-plus me-1"></i> Novo Lote
                        </button>
                    </div>
                    <div class="lotes-container row" id="lotes-container-${numPedido}">
                        <!-- Lotes serão criados dinamicamente -->
                        <div class="col-md-4">
                            <div class="card lote-placeholder border-dashed text-center p-4" data-lote-id="placeholder">
                                <i class="fas fa-plus fa-2x text-muted mb-2"></i>
                                <p class="text-muted mb-0">Clique em "Novo Lote" ou arraste produtos aqui</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderizarTabelaProdutos(produtos) {
        // Delegado para WorkspaceTabela
        if (window.workspaceTabela) {
            return window.workspaceTabela.renderizarTabelaProdutos(produtos);
        }
        return `<div class="alert alert-warning">Módulo de tabela não carregado</div>`;
    }

    renderizarSeparacoesConfirmadas() {
        return this.separacoesConfirmadas.map(separacao => {
            const statusClass = this.getStatusClass(separacao.status);

            return `
                <div class="col-md-4 mb-3">
                    <div class="card h-100 border-${statusClass}" id="card-separacao-${separacao.separacao_lote_id}">
                        <div class="card-header bg-${statusClass} bg-opacity-10">
                            <h6 class="mb-0">
                                <i class="fas fa-check me-2"></i>
                                Separação Confirmada
                            </h6>
                            <small>${separacao.separacao_lote_id}</small>
                            <span class="badge bg-${statusClass} float-end">${separacao.status}</span>
                        </div>
                        <div class="card-body">
                            <div class="info-separacao mb-2">
                                <small><strong>Expedição:</strong> ${this.formatarData(separacao.expedicao)}</small><br>
                                <small><strong>Agendamento:</strong> ${separacao.agendamento ? this.formatarData(separacao.agendamento) : '-'}</small><br>
                                <small><strong>Protocolo:</strong> ${separacao.protocolo || '-'}</small>
                            </div>
                            
                            <div class="produtos-separacao">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <h6 class="small mb-0">Produtos (${separacao.produtos.length}):</h6>
                                    ${separacao.produtos.length > 3 ? `
                                        <button class="btn btn-link btn-sm p-0" onclick="workspace.toggleProdutosSeparacao('${separacao.separacao_lote_id}')">
                                            <small id="btn-toggle-${separacao.separacao_lote_id}">Ver todos</small>
                                        </button>
                                    ` : ''}
                                </div>
                                <div id="produtos-resumo-${separacao.separacao_lote_id}">
                                    ${separacao.produtos.slice(0, 3).map(p => `
                                        <small class="d-block mb-1">
                                            • ${p.cod_produto} - ${this.formatarQuantidade(p.qtd_saldo)}un
                                            <span class="text-muted ms-2">
                                                | ${this.formatarMoeda(p.valor_saldo || 0)} 
                                                | ${this.formatarPeso(p.peso || 0)} 
                                                | ${this.formatarPallet(p.pallet || 0)}
                                            </span>
                                        </small>
                                    `).join('')}
                                    ${separacao.produtos.length > 3 ? `<small class="text-muted">... e mais ${separacao.produtos.length - 3} produtos</small>` : ''}
                                </div>
                                <div id="produtos-completo-${separacao.separacao_lote_id}" style="display: none;">
                                    <div class="table-responsive mt-2">
                                        <table class="table table-sm table-hover">
                                            <thead class="table-light">
                                                <tr>
                                                    <th>Código</th>
                                                    <th>Produto</th>
                                                    <th class="text-end">Qtd</th>
                                                    <th class="text-end">Valor</th>
                                                    <th class="text-end">Peso</th>
                                                    <th class="text-end">Pallet</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${separacao.produtos.map(p => `
                                                    <tr>
                                                        <td><small>${p.cod_produto}</small></td>
                                                        <td><small>${p.nome_produto || '-'}</small></td>
                                                        <td class="text-end"><small>${this.formatarQuantidade(p.qtd_saldo)}</small></td>
                                                        <td class="text-end"><small>${this.formatarMoeda(p.valor_saldo || 0)}</small></td>
                                                        <td class="text-end"><small>${this.formatarPeso(p.peso || 0)}</small></td>
                                                        <td class="text-end"><small>${this.formatarPallet(p.pallet || 0)}</small></td>
                                                    </tr>
                                                `).join('')}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="totais-separacao border-top pt-2 mt-2">
                                <div class="row text-center">
                                    <div class="col-4">
                                        <small class="text-success">${this.formatarMoeda(separacao.valor_total)}</small>
                                        <br><small class="text-muted">Valor</small>
                                    </div>
                                    <div class="col-4">
                                        <small class="text-info">${this.formatarPeso(separacao.peso_total)}</small>
                                        <br><small class="text-muted">Peso</small>
                                    </div>
                                    <div class="col-4">
                                        <small class="text-warning">${this.formatarPallet(separacao.pallet_total)}</small>
                                        <br><small class="text-muted">Pallet</small>
                                    </div>
                                </div>
                            </div>
                            
                            ${separacao.status === 'COTADO' && separacao.embarque ? `
                                <div class="alert alert-info p-2 mt-2 mb-0">
                                    <small>
                                        <strong>Embarque #${separacao.embarque.numero || '-'}</strong><br>
                                        ${separacao.embarque.transportadora || 'Sem transportadora'}<br>
                                        Prev: ${separacao.embarque.data_prevista_embarque ? this.formatarData(separacao.embarque.data_prevista_embarque) : '-'}
                                    </small>
                                </div>
                            ` : ''}
                        </div>
                        
                        <!-- Botões de ação -->
                        <div class="card-footer bg-light">
                            <div class="d-flex justify-content-between">
                                <div>
                                    ${separacao.status === 'ABERTO' ? `
                                        <button class="btn btn-warning btn-sm" onclick="workspace.reverterSeparacao('${separacao.separacao_lote_id}')">
                                            <i class="fas fa-undo me-1"></i> Reverter para Pré-Separação
                                        </button>
                                        <button class="btn btn-info btn-sm ms-2" onclick="workspace.editarDatasSeparacao('${separacao.separacao_lote_id}')">
                                            <i class="fas fa-edit me-1"></i> Editar Datas
                                        </button>
                                    ` : ''}
                                </div>
                                <button class="btn btn-primary btn-sm" onclick="workspace.imprimirSeparacao('${separacao.separacao_lote_id}')">
                                    <i class="fas fa-print me-1"></i> Imprimir
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    getStatusClass(status) {
        const statusMap = {
            'ABERTO': 'warning',
            'FATURADO': 'info',
            'COTADO': 'primary',
            'EMBARCADO': 'success',
            'NF no CD': 'secondary'
        };
        return statusMap[status] || 'secondary';
    }

    formatarQuantidade(qtd) {
        if (!qtd) return '0';
        return parseFloat(qtd).toFixed(0);
    }

    formatarData(data) {
        if (!data) return '-';
        const d = new Date(data + 'T00:00:00');
        return d.toLocaleDateString('pt-BR');
    }

    calcularStatusDisponibilidade(produto) {
        if (produto.estoque_hoje >= produto.qtd_pedido) {
            return { classe: 'bg-success', texto: 'Hoje' };
        }

        if (produto.data_disponibilidade) {
            const diasAte = this.calcularDiasAte(produto.data_disponibilidade);
            if (diasAte <= 7) {
                return { classe: 'bg-warning', texto: `${diasAte}d` };
            }
        }

        return { classe: 'bg-danger', texto: 'Sem est.' };
    }

    calcularDiasAte(dataStr) {
        const hoje = new Date();
        const dataTarget = new Date(dataStr);
        const diffTime = dataTarget - hoje;
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }

    /**
     * 🎯 CALCULAR SALDO DISPONÍVEL DO PRODUTO
     * Fórmula: Qtd Pedido - Qtd em Separações - Qtd em Pré-Separações
     */
    calcularSaldoDisponivel(produto) {
        // Delegado para WorkspaceQuantidades
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.calcularSaldoDisponivel(produto);
        }
        return { qtdEditavel: 0, qtdIndisponivel: produto.qtd_pedido || 0 };
    }

    // Delegação para LoteManager

    gerarNovoLoteId() {
        return this.loteManager.gerarNovoLoteId();
    }

    criarNovoLote(numPedido) {
        this.loteManager.criarNovoLote(numPedido);
    }

    /**
     * 🎯 CONFIGURAR CHECKBOXES
     */
    configurarCheckboxes(numPedido) {
        const workspaceElement = document.querySelector(`.workspace-montagem[data-pedido="${numPedido}"]`);
        if (!workspaceElement) return;

        // Checkbox selecionar todos
        const selectAll = workspaceElement.querySelector('#select-all-produtos');
        if (selectAll) {
            selectAll.addEventListener('change', (e) => {
                const checkboxes = workspaceElement.querySelectorAll('.produto-checkbox');
                checkboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                    this.toggleProdutoSelecionado(cb.dataset.produto, cb.checked);
                });
            });
        }

        // Checkboxes individuais
        const checkboxes = workspaceElement.querySelectorAll('.produto-checkbox');
        checkboxes.forEach(cb => {
            cb.addEventListener('change', (e) => {
                this.toggleProdutoSelecionado(e.target.dataset.produto, e.target.checked);
                this.atualizarSelectAll(workspaceElement);
            });
        });

        console.log(`✅ Configurados ${checkboxes.length} checkboxes`);
    }

    /**
     * 🎯 TOGGLE PRODUTO SELECIONADO
     */
    toggleProdutoSelecionado(codProduto, selecionado) {
        if (selecionado) {
            this.produtosSelecionados.add(codProduto);
        } else {
            this.produtosSelecionados.delete(codProduto);
        }

        // Adicionar/remover classe visual
        const tr = document.querySelector(`tr[data-produto="${codProduto}"]`);
        if (tr) {
            tr.classList.toggle('selected', selecionado);
        }

        console.log(`Produtos selecionados: ${this.produtosSelecionados.size}`);
    }

    /**
     * 🎯 ATUALIZAR SELECT ALL
     */
    atualizarSelectAll(workspaceElement) {
        const selectAll = workspaceElement.querySelector('#select-all-produtos');
        const checkboxes = workspaceElement.querySelectorAll('.produto-checkbox');
        const checkedBoxes = workspaceElement.querySelectorAll('.produto-checkbox:checked');

        if (selectAll) {
            selectAll.checked = checkboxes.length > 0 && checkboxes.length === checkedBoxes.length;
            selectAll.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < checkboxes.length;
        }
    }

    /**
     * 🎯 ADICIONAR PRODUTOS SELECIONADOS AO LOTE
     */
    async adicionarProdutosSelecionados(loteId) {
        if (this.produtosSelecionados.size === 0) {
            this.mostrarFeedback('Selecione pelo menos um produto', 'warning');
            return;
        }

        try {
            const produtosParaAdicionar = [];

            // Coletar dados dos produtos selecionados
            this.produtosSelecionados.forEach(codProduto => {
                const produtoData = this.dadosProdutos.get(codProduto);
                const inputQtd = document.querySelector(`.qtd-editavel[data-produto="${codProduto}"]`);
                const quantidade = inputQtd ? parseInt(inputQtd.value) : 0;

                if (produtoData && quantidade > 0) {
                    produtosParaAdicionar.push({
                        codProduto,
                        qtdPedido: quantidade,
                        nomeProduto: produtoData.nome_produto || codProduto
                    });
                }
            });

            if (produtosParaAdicionar.length === 0) {
                this.mostrarFeedback('Nenhum produto válido selecionado ou quantidades zeradas', 'warning');
                return;
            }

            // Adicionar produtos ao lote
            let produtosAdicionados = 0;
            let produtosAtualizados = 0;

            for (const produto of produtosParaAdicionar) {
                const loteData = this.preSeparacoes.get(loteId);
                const produtoExistente = loteData?.produtos.find(p => p.codProduto === produto.codProduto);

                await this.adicionarProdutoNoLote(loteId, produto);

                if (produtoExistente) {
                    produtosAtualizados++;
                } else {
                    produtosAdicionados++;
                }
            }

            // Limpar seleção
            this.limparSelecao();

            // Feedback mais detalhado
            let mensagem = '';
            if (produtosAdicionados > 0 && produtosAtualizados > 0) {
                mensagem = `${produtosAdicionados} produtos adicionados e ${produtosAtualizados} atualizados no lote!`;
            } else if (produtosAdicionados > 0) {
                mensagem = `${produtosAdicionados} produtos adicionados ao lote!`;
            } else {
                mensagem = `${produtosAtualizados} produtos atualizados no lote!`;
            }

            this.mostrarFeedback(mensagem, 'success');

        } catch (error) {
            console.error('❌ Erro ao adicionar produtos:', error);
            this.mostrarFeedback(`Erro ao adicionar produtos: ${error.message}`, 'error');
        }
    }

    /**
     * 🎯 LIMPAR SELEÇÃO
     */
    limparSelecao() {
        // Desmarcar todos os checkboxes
        document.querySelectorAll('.produto-checkbox').forEach(cb => {
            cb.checked = false;
        });

        // Remover classe selected das linhas
        document.querySelectorAll('.produto-origem.selected').forEach(tr => {
            tr.classList.remove('selected');
        });

        // Limpar conjunto de selecionados
        this.produtosSelecionados.clear();

        // Atualizar select all
        const selectAll = document.querySelector('#select-all-produtos');
        if (selectAll) {
            selectAll.checked = false;
            selectAll.indeterminate = false;
        }
    }

    /**
     * 🎯 MOSTRAR FEEDBACK VISUAL
     */
    mostrarFeedback(mensagem, tipo = 'info') {
        // Criar toast notification
        const toast = document.createElement('div');
        toast.className = `toast-feedback toast-${tipo}`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${tipo === 'success' ? '#28a745' : tipo === 'error' ? '#dc3545' : '#ffc107'};
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;

        toast.textContent = mensagem;
        document.body.appendChild(toast);

        // Remover após 3 segundos
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    criarLote(numPedido, loteId) {
        this.loteManager.criarLote(numPedido, loteId);
    }

    removerProdutoDoLote(loteId, codProduto) {
        this.loteManager.removerProdutoDoLote(loteId, codProduto);
    }

    obterNumeroPedido() {
        // Buscar o número do pedido do workspace ativo
        const workspaceElement = document.querySelector('.workspace-montagem[data-pedido]');
        return workspaceElement ? workspaceElement.dataset.pedido : null;
    }

    resetarQuantidadeProduto(codProduto) {
        const input = document.querySelector(`input[data-produto="${codProduto}"]`);
        if (input) {
            const qtdOriginal = parseInt(input.dataset.qtdOriginal) || 0;
            input.value = qtdOriginal;
            input.dataset.qtdSaldo = qtdOriginal;

            // Atualizar span
            const spanSaldo = input.nextElementSibling;
            if (spanSaldo) {
                spanSaldo.textContent = `/${qtdOriginal}`;
            }

            // Atualizar valores calculados
            if (window.workspaceQuantidades) {
                window.workspaceQuantidades.atualizarQuantidadeProduto(input);
            }
        }
    }

    // Delegação para LoteManager (método removido - usar this.loteManager.renderizarCardLote)

    // Delegação para LoteManager (método removido - usar this.loteManager.renderizarProdutosDoLote)

    adicionarProdutoNoLote(loteId, dadosProduto) {
        this.loteManager.adicionarProdutoNoLote(loteId, dadosProduto);

        // Não atualizar aqui - o loteManager já faz isso
        // this.atualizarSaldoNaTabela(dadosProduto.codProduto);
    }

    /**
     * 🎯 ATUALIZAR SALDO DISPONÍVEL NA TABELA APÓS MUDANÇAS
     */
    atualizarSaldoNaTabela(codProduto) {
        const dadosProduto = this.dadosProdutos.get(codProduto);
        if (!dadosProduto) return;

        // Recalcular saldo disponível
        const saldoDisponivel = this.calcularSaldoDisponivel(dadosProduto);

        // Encontrar input de quantidade na tabela
        const input = document.querySelector(`input[data-produto="${codProduto}"]`);
        if (input) {
            // Atualizar atributos do input
            input.dataset.qtdSaldo = Math.floor(saldoDisponivel.qtdEditavel);
            input.max = Math.floor(saldoDisponivel.qtdEditavel);

            // Atualizar o valor se exceder o novo saldo
            const valorAtual = parseInt(input.value) || 0;
            if (valorAtual > saldoDisponivel.qtdEditavel) {
                input.value = Math.floor(saldoDisponivel.qtdEditavel);
                this.atualizarQuantidadeProduto(input);
            }

            // Atualizar o span do saldo
            const spanSaldo = input.nextElementSibling;
            if (spanSaldo) {
                spanSaldo.textContent = `/${Math.floor(saldoDisponivel.qtdEditavel)}`;
                spanSaldo.title = `Saldo disponível: ${this.formatarQuantidade(saldoDisponivel.qtdEditavel)} de ${this.formatarQuantidade(dadosProduto.qtd_pedido)} do pedido`;

                // Visual feedback se saldo mudou
                if (saldoDisponivel.temRestricao) {
                    spanSaldo.classList.add('text-warning');
                } else {
                    spanSaldo.classList.remove('text-warning');
                }
            }
        }
    }

    // Delegação para LoteManager (método removido - usar this.loteManager.recalcularTotaisLote)

    // Delegação para LoteManager (método removido - usar this.loteManager.atualizarCardLote)

    async abrirCardex(codProduto) {
        await this.modalCardex.abrirCardex(codProduto, this.dadosProdutos);
    }

    atualizarQuantidadeProduto(input) {
        // Delegado para WorkspaceQuantidades
        if (window.workspaceQuantidades) {
            window.workspaceQuantidades.atualizarQuantidadeProduto(input);
        }
    }

    atualizarColunasCalculadas(codProduto, novaQtd, dadosProduto) {
        // Delegado para WorkspaceQuantidades
        if (window.workspaceQuantidades) {
            window.workspaceQuantidades.atualizarColunasCalculadas(codProduto, novaQtd, dadosProduto);
        }
    }

    recalcularTotaisLotesComProduto(codProduto) {
        // Delegado para WorkspaceQuantidades
        if (window.workspaceQuantidades) {
            window.workspaceQuantidades.recalcularTotaisLotesComProduto(codProduto);
        }
    }

    // Delegação para ModalCardex (método removido - usar this.modalCardex.mostrarModalCardex)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.renderizarModalCardex)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.renderizarLinhasCardex)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.getStatusClasseCardex)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.renderizarAlertas)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.formatarData)

    exportarCardex(codProduto) {
        this.modalCardex.exportarCardex(codProduto);
    }

    async gerarSeparacao(loteId) {
        console.log(`⚡ Gerar separação para lote ${loteId}`);

        const loteData = this.preSeparacoes.get(loteId);
        if (!loteData || loteData.produtos.length === 0) {
            alert('❌ Lote vazio! Adicione produtos antes de gerar a separação.');
            return;
        }

        // Obter número do pedido
        const numPedido = this.obterNumeroPedido();
        if (!numPedido) {
            alert('❌ Não foi possível identificar o número do pedido.');
            return;
        }

        // 🎯 TRANSFORMAR ESTE LOTE ESPECÍFICO EM SEPARAÇÃO
        if (window.separacaoManager) {
            await window.separacaoManager.transformarLoteEmSeparacao(loteId);

            // Não remover mais o lote após gerar separação (mantém histórico)
            // this.loteManager.removerLote(loteId);
        } else {
            console.error('❌ Separação Manager não disponível');
            alert('❌ Sistema de separação não está disponível');
        }
    }

    async confirmarSeparacao(loteId) {
        console.log(`🔄 Confirmar separação para lote ${loteId}`);

        // Obter número do pedido
        const numPedido = this.obterNumeroPedido();
        if (!numPedido) {
            alert('❌ Não foi possível identificar o número do pedido.');
            return;
        }

        // 🎯 DELEGAR PARA SEPARACAO-MANAGER (Caso 2 - Transformar pré-separação em separação)
        if (window.separacaoManager) {
            await window.separacaoManager.transformarLoteEmSeparacao(loteId);

            // Não remover mais o lote após confirmar separação (mantém histórico)
            // this.loteManager.removerLote(loteId);
        } else {
            console.error('❌ Separação Manager não disponível');
            alert('❌ Sistema de separação não está disponível');
        }
    }


    obterNumeroPedido() {
        // Extrair número do pedido do workspace atual
        const workspaceElement = document.querySelector('.workspace-montagem[data-pedido]');
        return workspaceElement ? workspaceElement.dataset.pedido : null;
    }


    abrirDetalhesLote(loteId) {
        console.log(`🔍 Abrir detalhes do lote ${loteId}`);
        // Modal com detalhes do lote já implementado via card expandido
        const loteData = this.preSeparacoes.get(loteId);
        if (loteData) {
            const cardElement = document.querySelector(`[data-lote-id="${loteId}"]`);
            if (cardElement) {
                cardElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }

    removerLote(loteId) {
        this.loteManager.removerLote(loteId);
    }

    removerProdutoDoLote(loteId, codProduto) {
        this.loteManager.removerProdutoDoLote(loteId, codProduto);

        // 🎯 ATUALIZAR SALDO DISPONÍVEL NA TABELA
        this.atualizarSaldoNaTabela(codProduto);
    }

    renderizarErroWorkspace(numPedido, mensagem) {
        const contentDiv = document.getElementById(`content-${numPedido}`);
        const loadingDiv = document.getElementById(`loading-${numPedido}`);

        if (contentDiv) {
            contentDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Erro ao carregar workspace</strong>
                    <p class="mb-2">${mensagem}</p>
                    <button class="btn btn-sm btn-outline-danger" onclick="location.reload()">
                        <i class="fas fa-redo me-1"></i> Recarregar página
                    </button>
                </div>
            `;
            contentDiv.style.display = 'block';
        }
        if (loadingDiv) {
            loadingDiv.style.display = 'none';
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
        // Para quantidades, sempre mostrar como inteiro
        return Math.floor(qtd).toLocaleString('pt-BR');
    }

    formatarPeso(peso) {
        if (!peso) return '0 kg';
        return `${parseFloat(peso).toFixed(1)} kg`;
    }

    formatarPallet(pallet) {
        if (!pallet) return '0 plt';
        return `${parseFloat(pallet).toFixed(2)} plt`;
    }

    toggleProdutosSeparacao(loteId) {
        const resumo = document.getElementById(`produtos-resumo-${loteId}`);
        const completo = document.getElementById(`produtos-completo-${loteId}`);
        const btnToggle = document.getElementById(`btn-toggle-${loteId}`);
        const card = document.getElementById(`card-separacao-${loteId}`);

        if (resumo && completo && btnToggle && card) {
            if (completo.style.display === 'none') {
                resumo.style.display = 'none';
                completo.style.display = 'block';
                btnToggle.textContent = 'Ver menos';

                // Expandir o card mudando a classe da coluna
                const colParent = card.closest('.col-md-4');
                if (colParent) {
                    // Adicionar transição suave
                    card.style.transition = 'all 0.3s ease';

                    // Mudar de col-md-4 para col-md-6 (50% da largura)
                    colParent.classList.remove('col-md-4');
                    colParent.classList.add('col-md-6');

                    // Elevar o card
                    card.style.zIndex = '10';
                    card.style.position = 'relative';
                    card.classList.add('shadow-lg');
                }
            } else {
                resumo.style.display = 'block';
                completo.style.display = 'none';
                btnToggle.textContent = 'Ver todos';

                // Restaurar o tamanho original
                const colParent = card.closest('.col-md-6');
                if (colParent) {
                    // Voltar para col-md-4
                    colParent.classList.remove('col-md-6');
                    colParent.classList.add('col-md-4');

                    // Remover elevação após transição
                    setTimeout(() => {
                        card.style.zIndex = '';
                        card.classList.remove('shadow-lg');
                    }, 300);
                }
            }
        }
    }

    async reverterSeparacao(loteId) {
        if (!confirm('Deseja reverter esta separação para pré-separação?')) {
            return;
        }

        try {
            const response = await fetch(`/carteira/api/separacao/${loteId}/reverter`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',  // Solicitar JSON
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            // Verificar se a resposta foi bem sucedida
            if (!response.ok) {
                console.error('Resposta com erro:', response.status, response.statusText);
                // Tentar pegar mensagem de erro do corpo
                try {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `Erro HTTP ${response.status}`);
                } catch (e) {
                    throw new Error(`Erro HTTP ${response.status}: ${response.statusText}`);
                }
            }

            const data = await response.json();

            if (data.success || data.ok) {
                // Tentar aplicar parciais HTML se disponíveis
                try {
                    if (data.targets && window.separacaoManager && window.separacaoManager.applyTargets) {
                        await window.separacaoManager.applyTargets(data);
                        
                        // Atualizar contadores se disponíveis
                        if (data.contadores && window.separacaoManager.atualizarContadores) {
                            window.separacaoManager.atualizarContadores(data.contadores);
                        }
                    }
                } catch (applyError) {
                    console.warn('Aviso: Não foi possível aplicar atualizações parciais:', applyError);
                    // Continua mesmo se falhar aplicar parciais
                }
                
                // Mostrar mensagem de sucesso
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'success',
                        title: 'Separação revertida!',
                        text: data.message || 'Separação revertida com sucesso',
                        toast: true,
                        position: 'top-end',
                        timer: 3000,
                        showConfirmButton: false
                    });
                } else {
                    alert('✅ ' + (data.message || 'Separação revertida com sucesso!'));
                }
                
                // Atualizar workspace localmente
                try {
                    this.atualizarListaSeparacoes();
                } catch (updateError) {
                    console.warn('Aviso: Não foi possível atualizar lista local:', updateError);
                }
                
                // Se não conseguiu aplicar parciais, fazer reload
                if (!data.targets || !window.separacaoManager) {
                    setTimeout(() => {
                        location.reload();
                    }, 1500);
                }
            } else {
                alert(`❌ Erro ao reverter separação: ${data.error || 'Erro desconhecido'}`);
            }

        } catch (error) {
            console.error('Erro ao reverter separação:', error);
            
            // Verificar se o erro é de parsing JSON ou se a mensagem contém indicação de sucesso
            const errorMessage = error.message ? error.message.toLowerCase() : '';
            
            if (error instanceof SyntaxError || errorMessage.includes('json')) {
                // Provavelmente a operação funcionou mas retornou HTML ao invés de JSON
                console.log('Possível sucesso com resposta não-JSON, recarregando...');
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'success',
                        title: 'Processando...',
                        text: 'Separação sendo revertida, aguarde...',
                        toast: true,
                        position: 'top-end',
                        timer: 2000,
                        showConfirmButton: false
                    });
                }
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                // Erro real - mostrar mensagem apropriada
                const userMessage = error.message || 'Erro desconhecido ao reverter separação';
                
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'error',
                        title: 'Erro ao reverter',
                        text: userMessage,
                        toast: true,
                        position: 'top-end',
                        timer: 5000,
                        showConfirmButton: false
                    });
                } else {
                    alert(`❌ ${userMessage}`);
                }
            }
        }
    }
    
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    editarDatasSeparacao(loteId) {
        this.abrirModalEdicaoDatas('separacao', loteId);
    }

    editarDatasPreSeparacao(loteId) {
        this.abrirModalEdicaoDatas('pre-separacao', loteId);
    }

    abrirModalEdicaoDatas(tipo, loteId) {
        // Buscar dados atuais
        let dadosAtuais = {};

        if (tipo === 'pre-separacao') {
            // Buscar dados da pré-separação
            const loteData = this.preSeparacoes.get(loteId);
            if (loteData) {
                if (loteData.produtos && loteData.produtos.length > 0) {
                    const primeiroProduto = loteData.produtos[0];
                    const exp = (primeiroProduto.dataExpedicao || loteData.dataExpedicao || '');
                    const ag = (primeiroProduto.dataAgendamento || loteData.dataAgendamento || '');
                    dadosAtuais = {
                        expedicao: (typeof exp === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(exp)) ? exp : '',
                        agendamento: (typeof ag === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(ag)) ? ag : '',
                        protocolo: (primeiroProduto.protocolo || loteData.protocolo || '')
                    };
                } else {
                    const exp = loteData.dataExpedicao || '';
                    const ag = loteData.dataAgendamento || '';
                    dadosAtuais = {
                        expedicao: (typeof exp === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(exp)) ? exp : '',
                        agendamento: (typeof ag === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(ag)) ? ag : '',
                        protocolo: loteData.protocolo || ''
                    };
                }
            }
        } else {
            // Para separações, buscar dos dados carregados
            const separacao = this.separacoesConfirmadas.find(s => s.separacao_lote_id === loteId);
            if (separacao) {
                dadosAtuais = {
                    expedicao: separacao.expedicao || '',
                    agendamento: separacao.agendamento || '',
                    protocolo: separacao.protocolo || ''
                };
            }
        }

        // Criar modal
        const modalHtml = `
            <div class="modal fade" id="modalEdicaoDatas" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-calendar-alt me-2"></i>
                                Editar Datas - ${tipo === 'pre-separacao' ? 'Pré-Separação' : 'Separação'}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="formEdicaoDatas">
                                <div class="mb-3">
                                    <label class="form-label">Data de Expedição</label>
                                    <input type="date" class="form-control" id="dataExpedicao" 
                                           value="${dadosAtuais.expedicao}" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Data de Agendamento</label>
                                    <input type="date" class="form-control" id="dataAgendamento" 
                                           value="${dadosAtuais.agendamento}">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Protocolo</label>
                                    <input type="text" class="form-control" id="protocolo" 
                                           value="${dadosAtuais.protocolo}" 
                                           placeholder="Digite o protocolo">
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                            <button type="button" class="btn btn-primary" onclick="workspace.salvarEdicaoDatas('${tipo}', '${loteId}')">
                                <i class="fas fa-save me-1"></i> Salvar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remover modal anterior se existir
        const modalExistente = document.getElementById('modalEdicaoDatas');
        if (modalExistente) {
            modalExistente.remove();
        }

        // Adicionar modal ao body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Mostrar modal
        const modal = new bootstrap.Modal(document.getElementById('modalEdicaoDatas'));
        modal.show();
    }

    async salvarEdicaoDatas(tipo, loteId) {
        const expedicao = document.getElementById('dataExpedicao').value;
        const agendamento = document.getElementById('dataAgendamento').value;
        const protocolo = document.getElementById('protocolo').value;

        if (!expedicao) {
            alert('Data de expedição é obrigatória!');
            return;
        }

        try {
            const endpoint = tipo === 'pre-separacao'
                ? `/carteira/api/pre-separacao/${loteId}/atualizar-datas`
                : `/carteira/api/separacao/${loteId}/atualizar-datas`;

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    expedicao: expedicao,
                    agendamento: agendamento,
                    protocolo: protocolo
                })
            });

            const data = await response.json();

            if (data.success) {
                // Fechar modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalEdicaoDatas'));
                modal.hide();

                alert('✅ Datas atualizadas com sucesso!');
                location.reload();
            } else {
                alert(`❌ Erro ao atualizar datas: ${data.error}`);
            }

        } catch (error) {
            console.error('Erro ao atualizar datas:', error);
            alert('❌ Erro interno ao atualizar datas');
        }
    }

    imprimirSeparacao(loteId) {
        window.open(`/carteira/separacao/${loteId}/imprimir`, '_blank');
    }
}

// Disponibilizar globalmente
window.WorkspaceMontagem = WorkspaceMontagem;
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
                    data_agendamento: lote.data_agendamento || '',  // Usar nome correto do campo
                    protocolo: lote.protocolo || '',
                    agendamento_confirmado: lote.agendamento_confirmado || false,  // Campo faltando!
                    produtos: produtos,
                    status: lote.status || 'pre_separacao',
                    pre_separacao_id: lote.pre_separacao_id
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

                <!-- 🆕 RENDERIZAÇÃO COMPACTA DE SEPARAÇÕES/PRÉ-SEPARAÇÕES -->
                <div class="separacoes-compactas-container bg-white p-3 border-bottom">
                    ${this.renderizarSeparacoesCompactas(numPedido)}
                </div>

                <!-- Tabela de Produtos (Origem) - Com carregamento assíncrono -->
                <div class="workspace-produtos bg-light p-3">
                    <h6 class="mb-3">
                        <i class="fas fa-list me-2"></i>
                        Produtos do Pedido
                        <span id="loading-produtos-${numPedido}" class="spinner-border spinner-border-sm ms-2" style="display: none;">
                            <span class="visually-hidden">Carregando...</span>
                        </span>
                    </h6>
                    <div id="tabela-produtos-container-${numPedido}">
                        ${this.renderizarTabelaProdutosBasica(data.produtos)}
                    </div>
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
                                <small><strong>Agendamento:</strong> ${separacao.agendamento ? this.formatarData(separacao.agendamento) : '-'}
                                    ${separacao.agendamento && separacao.agendamento_confirmado ? 
                                        '<span class="badge bg-success ms-1"><i class="fas fa-check-circle"></i> Confirmado</span>' : 
                                        separacao.agendamento && !separacao.agendamento_confirmado ? 
                                        '<span class="badge bg-warning ms-1"><i class="fas fa-hourglass-half"></i> Aguardando</span>' : ''
                                    }
                                </small><br>
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
                            
                            <!-- Botões do Portal -->
                            <div class="portal-actions border-top pt-2 mt-2">
                                <div class="d-flex gap-1 justify-content-center flex-wrap">
                                    <button class="btn btn-success btn-sm" 
                                            data-lote="${separacao.separacao_lote_id}"
                                            data-agendamento="${separacao.agendamento || ''}"
                                            onclick="workspace.agendarNoPortal(this.dataset.lote, this.dataset.agendamento)"
                                            title="Agendar no portal do cliente">
                                        <i class="fas fa-calendar-plus"></i> Portal
                                    </button>
                                    <button class="btn btn-info btn-sm"
                                            data-lote="${separacao.separacao_lote_id}"
                                            onclick="workspace.verificarPortal(this.dataset.lote)"
                                            title="Verificar status no portal">
                                        <i class="fas fa-search"></i> Status
                                    </button>
                                    ${separacao.protocolo ? `
                                        <button class="btn btn-warning btn-sm"
                                                data-lote="${separacao.separacao_lote_id}"
                                                data-protocolo="${separacao.protocolo}"
                                                onclick="workspace.verificarProtocoloNoPortal(this.dataset.lote, this.dataset.protocolo)"
                                                title="Verificar protocolo no portal">
                                            <i class="fas fa-sync"></i> Verificar Protocolo
                                        </button>
                                        <span class="badge bg-success align-self-center">
                                            <i class="fas fa-check-circle"></i> ${separacao.protocolo}
                                        </span>
                                    ` : ''}
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

        // Verificar se os dados dos produtos foram carregados
        if (this.dadosProdutos.size === 0) {
            console.warn('⚠️ dadosProdutos está vazio. Tentando recarregar...');
            // Tentar coletar dados dos produtos da tabela diretamente
            await this.coletarDadosProdutosDaTabela();
        }

        try {
            const produtosParaAdicionar = [];

            // Coletar dados dos produtos selecionados
            this.produtosSelecionados.forEach(codProduto => {
                const produtoData = this.dadosProdutos.get(codProduto);
                const inputQtd = document.querySelector(`.qtd-editavel[data-produto="${codProduto}"]`);
                const quantidade = inputQtd ? parseInt(inputQtd.value) : 0;

                // Se não encontrar em dadosProdutos, tentar coletar da tabela
                if (!produtoData) {
                    console.warn(`⚠️ Produto ${codProduto} não encontrado em dadosProdutos. Tentando coletar da tabela...`);
                    const row = document.querySelector(`tr[data-produto="${codProduto}"]`);
                    if (row) {
                        const nomeProduto = row.querySelector('.nome-produto')?.textContent || codProduto;
                        if (quantidade > 0) {
                            produtosParaAdicionar.push({
                                codProduto,
                                qtdPedido: quantidade,
                                nomeProduto: nomeProduto
                            });
                        }
                    }
                } else if (quantidade > 0) {
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
     * 🎯 COLETAR DADOS DOS PRODUTOS DA TABELA (FALLBACK)
     */
    async coletarDadosProdutosDaTabela() {
        console.log('📊 Coletando dados dos produtos da tabela...');
        const rows = document.querySelectorAll('tr.produto-origem');
        
        rows.forEach(row => {
            const codProduto = row.dataset.produto;
            if (codProduto) {
                const nomeProduto = row.querySelector('.nome-produto')?.textContent || '';
                const qtdSaldo = parseFloat(row.querySelector('.qtd-saldo')?.textContent || 0);
                const valor = parseFloat(row.querySelector('.valor')?.textContent?.replace('R$', '').replace(',', '.') || 0);
                
                this.dadosProdutos.set(codProduto, {
                    cod_produto: codProduto,
                    nome_produto: nomeProduto,
                    qtd_saldo_produto_pedido: qtdSaldo,
                    preco_produto_pedido: valor / qtdSaldo || 0
                });
            }
        });
        
        console.log(`✅ Coletados dados de ${this.dadosProdutos.size} produtos`);
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

    async confirmarAgendamentoLote(loteId, tipo) {
        try {
            console.log(`🔄 Confirmando agendamento do lote ${loteId} (${tipo})`);
            
            let endpoint;
            if (tipo === 'pre') {
                // Para pré-separações, precisamos buscar o ID do item
                const loteData = this.preSeparacoes.get(loteId);
                if (!loteData || !loteData.pre_separacao_id) {
                    alert('❌ Não foi possível identificar a pré-separação');
                    return;
                }
                endpoint = `/carteira/api/pre-separacao/${loteData.pre_separacao_id}/confirmar-agendamento`;
            } else {
                // Para separações, usar o lote_id
                endpoint = `/carteira/api/separacao/${loteId}/confirmar-agendamento`;
            }
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.mostrarFeedback('✅ Agendamento confirmado com sucesso', 'success');
                
                // Atualizar dados locais
                const loteData = this.preSeparacoes.get(loteId);
                if (loteData) {
                    loteData.agendamento_confirmado = true;
                    this.preSeparacoes.set(loteId, loteData);
                    
                    // Re-renderizar o card
                    if (this.loteManager) {
                        this.loteManager.atualizarCardLote(loteId);
                    }
                }
                
                // Recarregar dados se necessário
                await this.carregarDadosPedido();
            } else {
                alert('❌ ' + (data.error || 'Erro ao confirmar agendamento'));
            }
        } catch (error) {
            console.error('Erro ao confirmar agendamento:', error);
            alert('❌ Erro ao confirmar agendamento');
        }
    }
    
    async reverterAgendamentoLote(loteId, tipo) {
        try {
            if (!confirm('Tem certeza que deseja reverter a confirmação do agendamento?')) {
                return;
            }
            
            console.log(`🔄 Revertendo confirmação do agendamento do lote ${loteId} (${tipo})`);
            
            let endpoint;
            if (tipo === 'pre') {
                // Para pré-separações, precisamos buscar o ID do item
                const loteData = this.preSeparacoes.get(loteId);
                if (!loteData || !loteData.pre_separacao_id) {
                    alert('❌ Não foi possível identificar a pré-separação');
                    return;
                }
                endpoint = `/carteira/api/pre-separacao/${loteData.pre_separacao_id}/reverter-agendamento`;
            } else {
                // Para separações, usar o lote_id
                endpoint = `/carteira/api/separacao/${loteId}/reverter-agendamento`;
            }
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.mostrarFeedback('✅ Confirmação de agendamento revertida', 'success');
                
                // Atualizar dados locais
                const loteData = this.preSeparacoes.get(loteId);
                if (loteData) {
                    loteData.agendamento_confirmado = false;
                    this.preSeparacoes.set(loteId, loteData);
                    
                    // Re-renderizar o card
                    if (this.loteManager) {
                        this.loteManager.atualizarCardLote(loteId);
                    }
                }
                
                // Recarregar dados se necessário
                await this.carregarDadosPedido();
            } else {
                alert('❌ ' + (data.error || 'Erro ao reverter confirmação'));
            }
        } catch (error) {
            console.error('Erro ao reverter confirmação:', error);
            alert('❌ Erro ao reverter confirmação');
        }
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
        // Usar SweetAlert2 para confirmação elegante
        const result = await Swal.fire({
            title: 'Confirmar Reversão',
            text: 'Deseja reverter esta separação para pré-separação?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#f39c12',
            cancelButtonColor: '#6c757d',
            confirmButtonText: '<i class="fas fa-undo me-1"></i> Sim, Reverter',
            cancelButtonText: 'Cancelar'
        });

        if (!result.isConfirmed) {
            return;
        }

        // Mostrar loading
        Swal.fire({
            title: 'Processando...',
            text: 'Revertendo separação para pré-separação',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

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
                // Mostrar sucesso
                Swal.fire({
                    icon: 'success',
                    title: 'Reversão Concluída!',
                    text: 'A separação foi revertida para pré-separação com sucesso.',
                    confirmButtonColor: '#28a745',
                    confirmButtonText: 'OK'
                }).then(() => {
                    // Atualizar a página sem reload completo
                    this.atualizarWorkspace(loteId);
                });
                
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
                
                // Atualizar workspace localmente sem reload
                try {
                    await this.carregarDadosPedido(); // Recarregar dados
                    this.renderizarSeparacoes(); // Re-renderizar separações
                    this.renderizarPreSeparacoes(); // Re-renderizar pré-separações
                } catch (updateError) {
                    console.warn('Aviso: Atualizando via reload:', updateError);
                    // Se falhar atualização local, fazer reload suave após 1s
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
                }
            } else {
                // Mostrar erro
                Swal.fire({
                    icon: 'error',
                    title: 'Erro ao Reverter',
                    text: data.error || 'Não foi possível reverter a separação',
                    confirmButtonColor: '#dc3545'
                });
            }

        } catch (error) {
            console.error('Erro ao reverter separação:', error);
            
            // Mostrar erro com Swal
            Swal.fire({
                icon: 'error',
                title: 'Erro ao Reverter',
                text: error.message || 'Ocorreu um erro ao reverter a separação',
                confirmButtonColor: '#dc3545'
            });
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
                // Usar diretamente os campos do loteData, como no card que funciona
                const exp = loteData.dataExpedicao || loteData.data_expedicao || '';
                const ag = loteData.data_agendamento || '';
                
                dadosAtuais = {
                    expedicao: (typeof exp === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(exp)) ? exp : '',
                    agendamento: (typeof ag === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(ag)) ? ag : '',
                    protocolo: loteData.protocolo || '',
                    agendamento_confirmado: loteData.agendamento_confirmado || false
                };
            }
        } else {
            // Para separações, buscar dos dados carregados
            const separacao = this.separacoesConfirmadas.find(s => s.separacao_lote_id === loteId);
            if (separacao) {
                dadosAtuais = {
                    expedicao: separacao.expedicao || '',
                    agendamento: separacao.agendamento || '',
                    protocolo: separacao.protocolo || '',
                    agendamento_confirmado: separacao.agendamento_confirmado || false
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
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="agendamentoConfirmado" 
                                               ${dadosAtuais.agendamento_confirmado ? 'checked' : ''}>
                                        <label class="form-check-label" for="agendamentoConfirmado">
                                            <i class="fas fa-check-circle text-success"></i> Agenda Confirmada
                                        </label>
                                    </div>
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
        const agendamentoConfirmado = document.getElementById('agendamentoConfirmado').checked;

        if (!expedicao) {
            Swal.fire({
                icon: 'warning',
                title: 'Campo Obrigatório',
                text: 'Data de expedição é obrigatória!',
                confirmButtonColor: '#0066cc'
            });
            return;
        }

        // Mostrar loading
        Swal.fire({
            title: 'Atualizando...',
            text: 'Salvando alterações das datas',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

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
                    protocolo: protocolo,
                    agendamento_confirmado: agendamentoConfirmado
                })
            });

            const data = await response.json();

            if (data.success) {
                // Fechar modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalEdicaoDatas'));
                modal.hide();

                // Atualizar dados localmente sem recarregar a página
                if (tipo === 'pre-separacao') {
                    const loteData = this.preSeparacoes.get(loteId);
                    if (loteData) {
                        loteData.dataExpedicao = expedicao;
                        loteData.data_expedicao = expedicao;
                        loteData.data_agendamento = agendamento;
                        loteData.protocolo = protocolo;
                        loteData.agendamento_confirmado = agendamentoConfirmado;
                        
                        // Atualizar card
                        const card = document.querySelector(`.card[data-lote-id="${loteId}"]`);
                        if (card) {
                            // Atualizar campos de data no card
                            const expedicaoElem = card.querySelector('.text-info');
                            if (expedicaoElem) {
                                expedicaoElem.innerHTML = `<i class="fas fa-calendar-day"></i> Expedição: ${this.formatarData(expedicao)}`;
                            }
                            
                            const agendamentoElem = card.querySelector('.text-warning');
                            if (agendamentoElem && agendamento) {
                                agendamentoElem.innerHTML = `<i class="fas fa-clock"></i> Agendamento: ${this.formatarData(agendamento)}`;
                            }
                            
                            const protocoloElem = card.querySelector('.text-success');
                            if (protocoloElem && protocolo) {
                                protocoloElem.innerHTML = `<i class="fas fa-hashtag"></i> Protocolo: ${protocolo}`;
                            }
                        }
                    }
                } else {
                    // Atualizar dados de separação
                    const separacao = this.separacoesConfirmadas.find(s => s.separacao_lote_id === loteId);
                    if (separacao) {
                        separacao.expedicao = expedicao;
                        separacao.agendamento = agendamento;
                        separacao.protocolo = protocolo;
                        separacao.agendamento_confirmado = agendamentoConfirmado;
                        
                        // Atualizar card
                        const card = document.querySelector(`.card[data-lote-id="${loteId}"]`);
                        if (card) {
                            // Atualizar campos de data no card
                            const expedicaoElem = card.querySelector('.text-info');
                            if (expedicaoElem) {
                                expedicaoElem.innerHTML = `<i class="fas fa-calendar-day"></i> Expedição: ${this.formatarData(expedicao)}`;
                            }
                            
                            const agendamentoElem = card.querySelector('.text-warning');
                            if (agendamentoElem && agendamento) {
                                agendamentoElem.innerHTML = `<i class="fas fa-clock"></i> Agendamento: ${this.formatarData(agendamento)}`;
                            }
                            
                            const protocoloElem = card.querySelector('.text-success');
                            if (protocoloElem && protocolo) {
                                protocoloElem.innerHTML = `<i class="fas fa-hashtag"></i> Protocolo: ${protocolo}`;
                            }
                        }
                    }
                }

                // Mostrar sucesso
                Swal.fire({
                    icon: 'success',
                    title: 'Datas Atualizadas!',
                    text: `As datas foram atualizadas com sucesso`,
                    toast: true,
                    position: 'top-end',
                    timer: 3000,
                    showConfirmButton: false
                });

            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro ao Atualizar',
                    text: data.error || 'Erro ao atualizar as datas',
                    confirmButtonColor: '#dc3545'
                });
            }

        } catch (error) {
            console.error('Erro ao atualizar datas:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro Interno',
                text: 'Ocorreu um erro ao atualizar as datas. Tente novamente.',
                confirmButtonColor: '#dc3545'
            });
        }
    }

    imprimirSeparacao(loteId) {
        window.open(`/carteira/separacao/${loteId}/imprimir`, '_blank');
    }

    async confirmarAgendamentoLote(loteId, tipo) {
        try {
            console.log(`🔄 Confirmando agendamento do lote ${loteId} (${tipo})`);
            
            let endpoint;
            if (tipo === 'pre') {
                // Para pré-separação, usar endpoint de lote
                endpoint = `/carteira/api/pre-separacao/lote/${loteId}/confirmar-agendamento`;
            } else {
                // Para separação
                endpoint = `/carteira/api/separacao/${loteId}/confirmar-agendamento`;
            }
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.mostrarToast('Agendamento confirmado com sucesso!', 'success');
                // Recarregar dados
                location.reload();
            } else {
                this.mostrarToast('Erro ao confirmar agendamento: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Erro ao confirmar agendamento:', error);
            this.mostrarToast('Erro ao confirmar agendamento', 'error');
        }
    }
    
    async reverterAgendamentoLote(loteId, tipo) {
        try {
            console.log(`🔄 Revertendo confirmação do lote ${loteId} (${tipo})`);
            
            let endpoint;
            if (tipo === 'pre') {
                // Para pré-separação, usar endpoint de lote
                endpoint = `/carteira/api/pre-separacao/lote/${loteId}/reverter-agendamento`;
            } else {
                // Para separação
                endpoint = `/carteira/api/separacao/${loteId}/reverter-agendamento`;
            }
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.mostrarToast('Confirmação de agendamento revertida!', 'success');
                // Recarregar dados
                location.reload();
            } else {
                this.mostrarToast('Erro ao reverter confirmação: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Erro ao reverter confirmação:', error);
            this.mostrarToast('Erro ao reverter confirmação', 'error');
        }
    }

    // Funções do Portal
    async agendarNoPortal(loteId, dataAgendamento) {
        console.log(`📅 Agendando lote ${loteId} no portal`);
        
        // Redirecionar para o modalSeparacoes se existir
        if (window.modalSeparacoes && typeof window.modalSeparacoes.agendarNoPortal === 'function') {
            return window.modalSeparacoes.agendarNoPortal(loteId, dataAgendamento);
        }
        
        // Caso contrário, mostrar mensagem
        this.mostrarToast('Abrindo portal de agendamento...', 'info');
        
        // Fazer requisição direta
        try {
            const response = await fetch('/portal/api/solicitar-agendamento-async', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    lote_id: loteId,
                    tipo: 'separacao',
                    portal: 'atacadao',  // TODO: detectar dinamicamente
                    data_agendamento: dataAgendamento || new Date().toISOString().split('T')[0]
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.mostrarToast(`Agendamento realizado! Protocolo: ${data.protocolo || 'Aguardando'}`, 'success');
                // Recarregar para mostrar o protocolo
                setTimeout(() => location.reload(), 2000);
            } else {
                this.mostrarToast(`Erro: ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('Erro ao agendar:', error);
            this.mostrarToast('Erro ao comunicar com o portal', 'error');
        }
    }
    
    async verificarPortal(loteId) {
        console.log(`🔍 Verificando lote ${loteId} no portal`);
        
        // Redirecionar para o modalSeparacoes se existir
        if (window.modalSeparacoes && typeof window.modalSeparacoes.verificarPortal === 'function') {
            return window.modalSeparacoes.verificarPortal(loteId);
        }
        
        // Caso contrário, abrir em nova aba
        window.open(`/portal/api/comparar-portal/${loteId}`, '_blank');
    }

    async verificarProtocoloNoPortal(loteId, protocolo) {
        console.log(`🔍 Verificando protocolo ${protocolo} no portal para lote ${loteId}`);
        
        // Redirecionar para o modalSeparacoes se existir
        if (window.modalSeparacoes && typeof window.modalSeparacoes.verificarProtocoloNoPortal === 'function') {
            return window.modalSeparacoes.verificarProtocoloNoPortal(loteId, protocolo);
        }
        
        // Caso contrário, implementar localmente
        this.mostrarToast('Verificando protocolo no portal...', 'info');
        
        try {
            const response = await fetch('/portal/atacadao/api/verificar-protocolo-portal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                },
                body: JSON.stringify({
                    lote_id: loteId,
                    protocolo: protocolo
                })
            });

            const data = await response.json();

            if (data.success) {
                // Mostrar resultado
                let mensagem = `Protocolo: ${protocolo}\n`;
                mensagem += `Status: ${data.agendamento_confirmado ? 'Confirmado' : 'Aguardando'}\n`;
                if (data.data_aprovada) {
                    mensagem += `Data aprovada: ${data.data_aprovada}\n`;
                }
                if (data.produtos_portal && data.produtos_portal.length > 0) {
                    mensagem += `\nProdutos no portal: ${data.produtos_portal.length}`;
                }
                
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Verificação do Protocolo',
                        html: mensagem.replace(/\n/g, '<br>'),
                        icon: data.agendamento_confirmado ? 'success' : 'info'
                    });
                } else {
                    alert(mensagem);
                }
                
                // Se confirmado, atualizar página
                if (data.agendamento_confirmado) {
                    setTimeout(() => location.reload(), 3000);
                }
            } else {
                this.mostrarToast(`Erro: ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('Erro ao verificar protocolo:', error);
            this.mostrarToast('Erro ao verificar protocolo', 'error');
        }
    }

    mostrarToast(mensagem, tipo = 'info') {
        // Usar SweetAlert2 se disponível, senão usar alert
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: tipo,
                title: mensagem,
                toast: true,
                position: 'top-end',
                timer: 3000,
                showConfirmButton: false
            });
        } else {
            const icone = tipo === 'success' ? '✅' : tipo === 'error' ? '❌' : 'ℹ️';
            alert(`${icone} ${mensagem}`);
        }
    }

    /**
     * 🆕 RENDERIZAÇÃO COMPACTA DE SEPARAÇÕES E PRÉ-SEPARAÇÕES
     * Mostra todas as separações e pré-separações em uma tabela compacta
     */
    renderizarSeparacoesCompactas(numPedido) {
        // Combinar separações confirmadas e pré-separações
        const todasSeparacoes = [];
        
        // Adicionar separações confirmadas
        if (this.separacoesConfirmadas && this.separacoesConfirmadas.length > 0) {
            this.separacoesConfirmadas.forEach(sep => {
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
        if (this.preSeparacoes && this.preSeparacoes.size > 0) {
            this.preSeparacoes.forEach((preSepa, loteId) => {
                // Calcular totais se não existirem
                let valorTotal = 0;
                let pesoTotal = 0;
                let palletTotal = 0;
                
                if (preSepa.produtos && preSepa.produtos.length > 0) {
                    preSepa.produtos.forEach(prod => {
                        valorTotal += prod.valor || 0;
                        pesoTotal += prod.peso || 0;
                        palletTotal += prod.pallet || 0;
                    });
                }
                
                todasSeparacoes.push({
                    tipo: 'Pré-separação',
                    status: '', // Pré-separação não tem status
                    loteId: loteId,
                    valor: valorTotal || preSepa.totais?.valor || 0,
                    peso: pesoTotal || preSepa.totais?.peso || 0,
                    pallet: palletTotal || preSepa.totais?.pallet || 0,
                    expedicao: preSepa.dataExpedicao || preSepa.data_expedicao,
                    agendamento: preSepa.data_agendamento,
                    protocolo: preSepa.protocolo,
                    agendamento_confirmado: preSepa.agendamento_confirmado || false,
                    embarque: null, // Pré-separações não têm embarque
                    isSeparacao: false
                });
            });
        }
        
        // Se não houver nenhuma separação ou pré-separação
        if (todasSeparacoes.length === 0) {
            return `
                <div class="text-center text-muted py-2">
                    <small><i class="fas fa-info-circle me-1"></i>Nenhuma separação ou pré-separação encontrada</small>
                </div>
            `;
        }
        
        // Renderizar tabela compacta
        return `
            <h6 class="mb-3">
                <i class="fas fa-truck me-2"></i>
                Separações e Pré-Separações
                <span class="badge bg-secondary ms-2">${todasSeparacoes.length}</span>
            </h6>
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead class="table-light">
                        <tr>
                            <th width="100">Tipo</th>
                            <th width="80">Status</th>
                            <th class="text-end">Valor</th>
                            <th class="text-end">Peso</th>
                            <th class="text-end">Pallet</th>
                            <th class="text-center">Expedição</th>
                            <th class="text-center">Agendamento</th>
                            <th>Protocolo</th>
                            <th class="text-center">Confirmação</th>
                            <th>Embarque</th>
                            <th width="200" class="text-center">Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${todasSeparacoes.map(item => this.renderizarLinhaSeparacaoCompacta(item, numPedido)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    /**
     * 🆕 RENDERIZAR LINHA INDIVIDUAL DA SEPARAÇÃO COMPACTA
     */
    renderizarLinhaSeparacaoCompacta(item, numPedido) {
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
                        ${item.isSeparacao ? `
                            <button class="btn btn-outline-primary btn-sm" 
                                    onclick="workspace.editarDatasSeparacao('${item.loteId}')"
                                    title="Editar datas">
                                <i class="fas fa-calendar-alt"></i> Datas
                            </button>
                        ` : `
                            <button class="btn btn-outline-primary btn-sm" 
                                    onclick="workspace.editarDatasPreSeparacao('${item.loteId}')"
                                    title="Editar datas">
                                <i class="fas fa-calendar-alt"></i> Datas
                            </button>
                            <button class="btn btn-outline-success btn-sm" 
                                    onclick="workspace.confirmarSeparacao('${item.loteId}')"
                                    title="Confirmar separação">
                                <i class="fas fa-check"></i> Confirmar
                            </button>
                        `}
                        ${item.agendamento && !item.protocolo ? `
                            <button class="btn btn-outline-success btn-sm" 
                                    onclick="workspace.agendarNoPortal('${item.loteId}', '${item.agendamento}')"
                                    title="Agendar no portal">
                                <i class="fas fa-calendar-plus"></i> Agendar
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }
    
    /**
     * 🆕 RENDERIZAR TABELA DE PRODUTOS BÁSICA (sem estoque)
     * Carrega apenas dados da CarteiraPrincipal inicialmente
     */
    renderizarTabelaProdutosBasica(produtos) {
        // Usar WorkspaceTabela se disponível, mas sem dados de estoque
        if (window.workspaceTabela) {
            // Temporariamente zerar dados de estoque para carregamento inicial
            const produtosBasicos = produtos.map(p => ({
                ...p,
                estoque_hoje: null,
                menor_estoque_7d: null,
                producao_hoje: null,
                estoque_data_expedicao: null
            }));
            return window.workspaceTabela.renderizarTabelaProdutos(produtosBasicos);
        }
        
        // Fallback simples se WorkspaceTabela não estiver disponível
        return `
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Produto</th>
                            <th>Quantidade</th>
                            <th>Valor</th>
                            <th>Estoque</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${produtos.map(p => `
                            <tr>
                                <td>${p.cod_produto} - ${p.nome_produto || ''}</td>
                                <td>${p.qtd_saldo_produto_pedido || 0}</td>
                                <td>${this.formatarMoeda((p.qtd_saldo_produto_pedido || 0) * (p.preco_produto_pedido || 0))}</td>
                                <td><span class="spinner-border spinner-border-sm"></span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    /**
     * 🆕 CARREGAR DADOS DE ESTOQUE DE FORMA ASSÍNCRONA
     * Carrega estoque, projeções e menor_estoque após renderização inicial
     */
    async carregarDadosEstoqueAssincrono(numPedido) {
        try {
            console.log(`📊 Carregando dados de estoque assincronamente para pedido ${numPedido}`);
            
            // Mostrar loading
            const loadingSpinner = document.getElementById(`loading-produtos-${numPedido}`);
            if (loadingSpinner) {
                loadingSpinner.style.display = 'inline-block';
            }
            
            // Fazer requisição para obter dados completos com estoque
            const response = await fetch(`/carteira/api/pedido/${numPedido}/workspace-estoque`);
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar estoque');
            }
            
            // Atualizar dados locais com informações de estoque
            data.produtos.forEach(produto => {
                const dadosExistentes = this.dadosProdutos.get(produto.cod_produto);
                if (dadosExistentes) {
                    // Mesclar dados de estoque com dados existentes
                    Object.assign(dadosExistentes, {
                        estoque_hoje: produto.estoque || produto.estoque_d0,
                        menor_estoque_7d: produto.menor_estoque_produto_d7,
                        producao_hoje: produto.producao_hoje || 0,
                        estoque_data_expedicao: produto.saldo_estoque_pedido,
                        // Adicionar projeções D0-D28 se disponíveis
                        ...Object.fromEntries(
                            Object.entries(produto).filter(([key]) => key.startsWith('estoque_d'))
                        )
                    });
                }
            });
            
            // Re-renderizar tabela com dados completos
            const container = document.getElementById(`tabela-produtos-container-${numPedido}`);
            if (container && window.workspaceTabela) {
                container.innerHTML = window.workspaceTabela.renderizarTabelaProdutos(Array.from(this.dadosProdutos.values()));
            }
            
            // Esconder loading
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }
            
            console.log(`✅ Dados de estoque carregados para ${data.produtos.length} produtos`);
            
        } catch (error) {
            console.error(`❌ Erro ao carregar dados de estoque:`, error);
            
            // Esconder loading em caso de erro
            const loadingSpinner = document.getElementById(`loading-produtos-${numPedido}`);
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }
            
            // Mostrar mensagem de erro inline (não bloquear a interface)
            const container = document.getElementById(`tabela-produtos-container-${numPedido}`);
            if (container) {
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-warning alert-dismissible fade show mt-2';
                alertDiv.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-1"></i>
                    Não foi possível carregar dados de estoque. Trabalhando com dados básicos.
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                container.insertBefore(alertDiv, container.firstChild);
            }
        }
    }
}

// Disponibilizar globalmente
window.WorkspaceMontagem = WorkspaceMontagem;
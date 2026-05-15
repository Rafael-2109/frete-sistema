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
        this.pedidoAtual = null; // Armazenar pedido atual

        // 🆕 Controle de requisições assíncronas de estoque
        this.abortControllerEstoque = null;

        // Inicializar módulos
        this.api = new WorkspaceAPI(); // 🆕 Módulo de API centralizado
        this.loteManager = new LoteManager(this);
        this.modalCardex = new ModalCardex();

        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log('✅ Workspace de Montagem inicializado');
    }

    setupEventListeners() {
        // Removido código desnecessário de esconder/mostrar
    }

    /**
     * 🧹 LIMPAR DADOS DO PEDIDO ANTERIOR
     * Limpa todos os dados antes de carregar um novo pedido
     */
    limparDadosAnteriores() {
        console.log('🧹 Limpando dados do pedido anterior...');

        // Limpar dados dos produtos
        this.dadosProdutos.clear();

        // Limpar produtos selecionados
        this.produtosSelecionados.clear();

        // Limpar pré-separações
        this.preSeparacoes.clear();

        // Limpar separações confirmadas
        this.separacoesConfirmadas = [];

        // Cancelar requisições assíncronas pendentes via API
        if (this.api) {
            this.api.cancelarTodasRequisicoes();
        }

        // Limpar pedido atual
        this.pedidoAtual = null;

        console.log('✅ Dados anteriores limpos');
    }


    async abrirWorkspace(numPedido) {
        console.log(`🔄 Carregando workspace para pedido ${numPedido}`);

        // 🧹 LIMPAR DADOS DO PEDIDO ANTERIOR
        this.limparDadosAnteriores();

        // IMPORTANTE: Armazenar novo pedido ANTES de qualquer operação
        // Isso garante que obterNumeroPedido() sempre retorne o pedido correto
        this.pedidoAtual = numPedido;
        console.log(`📌 Pedido atual definido como: ${this.pedidoAtual}`);

        try {
            // Carregar dados do workspace usando WorkspaceAPI
            const workspaceData = await this.api.buscarWorkspace(numPedido);

            // Verificar se há produtos
            if (!workspaceData.produtos || workspaceData.produtos.length === 0) {
                throw new Error('Nenhum produto encontrado para este pedido');
            }

            // Armazenar dados dos produtos e status do pedido
            workspaceData.produtos.forEach(produto => {
                // Garantir estrutura mínima para cada produto
                const produtoCompleto = {
                    ...produto,
                    qtd_pedido: produto.qtd_pedido || produto.qtd_saldo_produto_pedido || 0,
                    estoque_hoje: produto.estoque_hoje || produto.estoque || 0,
                    menor_estoque_7d: produto.menor_estoque_7d || produto.menor_estoque_produto_d7 || 0,
                    producao_hoje: produto.producao_hoje || 0,
                    preco_unitario: produto.preco_unitario || produto.preco_produto_pedido || 0,
                    peso_unitario: produto.peso_unitario || 0,
                    palletizacao: produto.palletizacao || 1000,
                    data_disponibilidade: produto.data_disponibilidade || null,
                    qtd_disponivel: produto.qtd_disponivel || 0
                };
                this.dadosProdutos.set(produto.cod_produto, produtoCompleto);
            });

            // Armazenar status do pedido
            this.statusPedido = workspaceData.status_pedido || 'ABERTO';

            // 🎯 ÚNICA API: Carregar TODAS as separações (incluindo PREVISAO)
            const separacoesData = await this.api.buscarSeparacoes(numPedido);

            if (separacoesData.success && separacoesData.separacoes) {
                // Processar TODAS as separações de uma vez
                this.todasSeparacoes = separacoesData.separacoes;

                // Atualizar Map local - MANTER ESTRUTURA ORIGINAL DO BACKEND
                separacoesData.separacoes.forEach(sep => {
                    this.preSeparacoes.set(sep.separacao_lote_id, {
                        produtos: sep.produtos || [], // Manter estrutura original
                        totais: {
                            valor: sep.valor_total || 0,
                            peso: sep.peso_total || 0,
                            pallet: sep.pallet_total || 0
                        },
                        status: sep.status,
                        lote_id: sep.separacao_lote_id,
                        expedicao: sep.expedicao,
                        agendamento: sep.agendamento,
                        protocolo: sep.protocolo,
                        agendamento_confirmado: sep.agendamento_confirmado || false,
                        embarque: sep.embarque
                    });
                });

                console.log(`✅ Carregadas ${separacoesData.separacoes.length} separações totais`);
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

            // 🎯 RENDERIZAÇÃO ÚNICA: Todas as separações em uma única área
            if (this.todasSeparacoes && this.todasSeparacoes.length > 0) {
                await this.renderizarTodasSeparacoes(numPedido);
            }

            // Configurar checkboxes e adição de produtos
            requestAnimationFrame(() => {
                console.log('🎯 Inicializando sistema de seleção...');
                this.configurarCheckboxes(numPedido);

                // 🆕 CARREGAR DADOS DE ESTOQUE DE FORMA ASSÍNCRONA
                // Aguardar um pouco para garantir que DOM esteja pronto
                setTimeout(() => {
                    console.log('📊 Carregando dados de estoque assíncronos...');
                    this.carregarDadosEstoqueAssincrono(numPedido);
                }, 500);
            });

        } catch (error) {
            console.error(`❌ Erro ao carregar workspace:`, error);
            this.renderizarErroWorkspace(numPedido, error.message);
        }
    }

    async renderizarTodasSeparacoes(numPedido) {
        const container = document.getElementById(`lotes-container-${numPedido}`);
        if (!container || !this.todasSeparacoes || this.todasSeparacoes.length === 0) return;

        // Remover placeholder se ainda existir
        const placeholder = container.querySelector('.lote-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // Limpar container antes de renderizar
        container.innerHTML = '';

        // Renderizar TODAS as separações usando o card universal
        for (const separacao of this.todasSeparacoes) {
            // Preparar dados no formato do card universal
            const loteData = {
                lote_id: separacao.separacao_lote_id,
                separacao_lote_id: separacao.separacao_lote_id,
                status: separacao.status || 'ABERTO',
                produtos: separacao.produtos || [],
                totais: {
                    valor: separacao.valor_total || 0,
                    peso: separacao.peso_total || 0,
                    pallet: separacao.pallet_total || 0
                },
                expedicao: separacao.expedicao,
                agendamento: separacao.agendamento,
                protocolo: separacao.protocolo,
                agendamento_confirmado: separacao.agendamento_confirmado || false,
                embarque: separacao.embarque
            };

            const loteCard = document.createElement('div');
            loteCard.className = 'col-md-4 mb-3';
            loteCard.innerHTML = this.loteManager.renderizarCardUniversal(loteData);
            container.appendChild(loteCard);
        }

        console.log(`✅ Renderizadas ${this.todasSeparacoes.length} separações no total`);
    }


    renderizarWorkspace(numPedido, data) {
        return `
            <div class="workspace-montagem" data-pedido="${numPedido}">
                <!-- Header do Workspace -->
                <div class="workspace-header p-3 rounded-top border-bottom">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h5 class="mb-0">
                                <i class="fas fa-boxes me-2"></i>
                                Workspace de Montagem - Pedido ${numPedido}
                            </h5>
                            <small class="text-muted">Selecione os produtos e clique em "Adicionar" no lote desejado</small>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="workspace-resumo">
                                <strong>Total: ${this.formatarMoeda(data.valor_total || 0)}</strong>
                                <br><small>${data.produtos.length} produtos</small>
                            </div>
                        </div>
                    </div>
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
                        ${this.renderizarTabelaProdutos(data.produtos)}
                    </div>
                </div>

                <!-- Área Unificada de Separações -->
                <div class="workspace-lotes p-3">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6 class="mb-0">
                            <i class="fas fa-layer-group me-2"></i>
                            Separações
                            ${this.separacoesConfirmadas && this.separacoesConfirmadas.length > 0 ?
                `<span class="badge bg-secondary ms-2">${this.separacoesConfirmadas.length}</span>` : ''}
                        </h6>
                        <button class="btn btn-secondary btn-sm" onclick="workspace.criarNovoLote('${numPedido}')">
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


    getStatusClass(status) {
        const statusMap = {
            'PREVISAO': 'secondary',
            'ABERTO': 'warning',
            'FATURADO': 'success',
            'COTADO': 'warning',
            'EMBARCADO': 'success',
            'NF no CD': 'danger'
        };
        return statusMap[status] || 'secondary';
    }

    /**
     * 🎯 DELEGAR FORMATAÇÃO DE QUANTIDADE (primeira ocorrência)
     * Usa workspace-quantidades para formatação
     */
    formatarQuantidade(qtd) {
        // Usar módulo centralizado se disponível
        if (window.Formatters && window.Formatters.quantidade) {
            const formatted = window.Formatters.quantidade(qtd);
            // Para esta primeira ocorrência, queremos sem decimais
            return formatted ? formatted.split(',')[0] : '0';
        }
        // Fallback para workspaceQuantidades
        if (window.workspaceQuantidades) {
            const formatted = window.workspaceQuantidades.formatarQuantidade(qtd);
            return formatted ? formatted.split(',')[0] : '0';
        }
        // Fallback final
        return (!qtd) ? '0' : parseFloat(qtd).toFixed(0);
    }

    formatarData(data) {
        return window.Formatters.data(data) || '-';
    }

    /**
     * 🎯 DELEGAR CÁLCULO DE STATUS DE DISPONIBILIDADE
     * Usa workspace-quantidades para cálculo completo
     */
    calcularStatusDisponibilidade(produto) {
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.calcularStatusDisponibilidade(produto);
        }
        // Fallback simplificado se workspace-quantidades não estiver disponível
        if (produto.estoque_hoje >= produto.qtd_pedido) {
            return { classe: 'bg-success', texto: 'Hoje' };
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
     * Já está delegando corretamente para WorkspaceQuantidades
     */
    calcularSaldoDisponivel(produto) {
        // Já está delegado para WorkspaceQuantidades
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
                // Verificar se produto existe, compatível com ambas estruturas
                const produtoExistente = loteData?.produtos.find(p =>
                    (p.codProduto === produto.codProduto) ||
                    (p.cod_produto === produto.codProduto)
                );

                await this.loteManager.adicionarProdutoNoLote(loteId, produto);

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
        // Usar módulo centralizado se disponível
        if (window.Notifications && window.Notifications.toast) {
            return window.Notifications.toast(mensagem, tipo);
        }

        // Fallback completo
        // Criar toast notification
        const toast = document.createElement('div');
        toast.className = `toast-feedback toast-${tipo}`;
        const colors = window.Notifications?.getColors?.() || { success: '#28a745', error: '#dc3545', warning: '#ffc107' };
        const bgColor = tipo === 'success' ? colors.success : tipo === 'error' ? colors.error : colors.warning;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${bgColor};
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


    obterNumeroPedido() {
        // CORREÇÃO: Usar o pedido armazenado no objeto, não buscar no DOM
        // Isso evita pegar o pedido errado quando há múltiplos workspaces no DOM
        return this.pedidoAtual;
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

    exportarCardex(codProduto) {
        this.modalCardex.exportarCardex(codProduto);
    }



    // Método unificado para excluir lote/separação (qualquer status)
    async excluirLote(loteId) {
        if (!confirm('Tem certeza que deseja excluir esta separação?')) {
            return;
        }

        console.log(`🗑️ Excluindo lote ${loteId}`);

        // Usar separacao-manager método unificado
        if (window.separacaoManager && typeof window.separacaoManager.excluirSeparacao === 'function') {
            const numPedido = this.numPedidoAtual || document.querySelector('.workspace-montagem')?.dataset.pedido;
            const resultado = await window.separacaoManager.excluirSeparacao(loteId, numPedido);
            if (resultado && resultado.success) {
                this.showToast('Separação excluída com sucesso', 'success');
                location.reload(); // Recarregar para atualizar
            } else {
                this.showToast(resultado?.error || 'Erro ao excluir', 'error');
            }
        } else {
            this.showToast('Função não disponível', 'error');
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

    async confirmarAgendamentoLote(loteId, tipo) {
        try {
            console.log(`🔄 Confirmando agendamento do lote ${loteId} (${tipo})`);

            // Usar sempre o endpoint unificado por lote_id
            const endpoint = `/carteira/api/separacao/${loteId}/confirmar-agendamento`;

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

            // Usar sempre o endpoint unificado por lote_id
            const endpoint = `/carteira/api/separacao/${loteId}/reverter-agendamento`;

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
                    <button class="btn btn-sm btn-outline-secondary" onclick="location.reload()">
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

    /**
     * 🎯 UTILITÁRIOS DE FORMATAÇÃO
     * Delegam todas as formatações para workspace-quantidades
     */
    formatarMoeda(valor) {
        return window.Formatters.moeda(valor);
    }

    // Segunda ocorrência de formatarQuantidade - remover duplicação
    // Já definida anteriormente na linha 479

    formatarPeso(peso) {
        return window.Formatters.peso(peso);
    }

    formatarPallet(pallet) {
        return window.Formatters.pallet(pallet);
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

    // Método unificado de alteração de status
    async alterarStatusSeparacao(loteId, novoStatus) {
        console.log(`🔄 Alterando status de ${loteId} para ${novoStatus}`);

        // Usar separacao-manager se disponível
        if (window.separacaoManager && typeof window.separacaoManager.alterarStatus === 'function') {
            return await window.separacaoManager.alterarStatus(loteId, novoStatus);
        }

        // Fallback direto para API
        try {
            const response = await fetch(`/carteira/api/separacao/${loteId}/alterar-status`, {
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
                    confirmButtonColor: window.Notifications?.colors?.success || '#28a745',
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
                    // Por enquanto, recarregar a página para atualizar
                    location.reload();
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
                    confirmButtonColor: window.Notifications?.colors?.danger || '#dc3545'
                });
            }

        } catch (error) {
            console.error('Erro ao reverter separação:', error);

            // Mostrar erro com Swal
            Swal.fire({
                icon: 'error',
                title: 'Erro ao Reverter',
                text: error.message || 'Ocorreu um erro ao reverter a separação',
                confirmButtonColor: window.Notifications?.colors?.danger || '#dc3545'
            });
        }
    }

    getCSRFToken() {
        return window.Security.getCSRFToken();
    }

    /**
     * 📅 EDITAR DATAS - SIMPLIFICADO (2 níveis em vez de 4)
     * Ponto de entrada único para edição de datas
     */
    editarDatasSeparacao(loteId) {
        console.log(`📅 Editando datas da separação ${loteId}`);
        this.editarDatas(loteId);
    }

    // Manter por compatibilidade mas redirecionar
    editarDatasPreSeparacao(loteId) {
        console.log(`📅 Editando datas (compatível) ${loteId}`);
        this.editarDatas(loteId);
    }

    // Método principal simplificado - busca dados e abre modal diretamente
    async editarDatas(loteId) {
        // 1. Buscar dados de qualquer fonte disponível
        let dadosAtuais = {};

        // Tentar separações confirmadas
        const separacao = this.separacoesConfirmadas.find(s => s.separacao_lote_id === loteId);
        if (separacao) {
            dadosAtuais = {
                expedicao: separacao.expedicao || '',
                agendamento: separacao.agendamento || '',
                protocolo: separacao.protocolo || '',
                agendamento_confirmado: separacao.agendamento_confirmado || false
            };
        }
        // Tentar pré-separações
        else {
            const preSep = this.preSeparacoes.get(loteId);
            if (preSep) {
                const exp = preSep.dataExpedicao || preSep.data_expedicao || preSep.expedicao || '';
                const ag = preSep.dataAgendamento || preSep.data_agendamento || preSep.agendamento || '';
                dadosAtuais = {
                    expedicao: exp,
                    agendamento: ag,
                    protocolo: preSep.protocolo || '',
                    agendamento_confirmado: preSep.agendamento_confirmado || false
                };
            }
            // Tentar buscar da API se necessário
            else {
                try {
                    const response = await fetch(`/carteira/api/separacao/${loteId}/detalhes`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.success && data.separacao) {
                            dadosAtuais = {
                                expedicao: data.separacao.expedicao || '',
                                agendamento: data.separacao.agendamento || '',
                                protocolo: data.separacao.protocolo || '',
                                agendamento_confirmado: data.separacao.agendamento_confirmado || false
                            };
                        }
                    }
                } catch (error) {
                    console.error(`Erro ao buscar dados da separação ${loteId}:`, error);
                }
            }
        }

        // 2. Abrir modal diretamente com os dados
        this.abrirModalDatas(loteId, dadosAtuais);
    }

    /**
     * 📅 ABRIR MODAL DE DATAS - SIMPLIFICADO
     * Método único para abrir o modal com os dados fornecidos
     */
    abrirModalDatas(loteId, dadosAtuais = {}) {
        // Formatar datas para exibição no modal (dd/mm/yyyy)
        const formatarDataParaExibicao = (data) => {
            if (!data) return '';
            if (data && data.includes('-')) {
                const [ano, mes, dia] = data.split('-');
                return `${dia}/${mes}/${ano}`;
            }
            return data;
        };

        // Criar modal
        const modalHtml = `
            <div class="modal fade" id="modalEdicaoDatas" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-calendar-alt me-2"></i>
                                Editar Datas - Separação
                                <span class="badge bg-secondary ms-2">${loteId}</span>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="formEdicaoDatas">
                                <div class="mb-3">
                                    <label class="form-label">Data de Expedição <span class="text-danger">*</span></label>
                                    <input type="date" class="form-control" id="dataExpedicao" 
                                           value="${dadosAtuais.expedicao}" required>
                                    ${dadosAtuais.expedicao ? `<small class="text-muted">Data atual: ${formatarDataParaExibicao(dadosAtuais.expedicao)}</small>` : ''}
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Data de Agendamento</label>
                                    <input type="date" class="form-control" id="dataAgendamento" 
                                           value="${dadosAtuais.agendamento}">
                                    ${dadosAtuais.agendamento ? `<small class="text-muted">Data atual: ${formatarDataParaExibicao(dadosAtuais.agendamento)}</small>` : ''}
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Protocolo</label>
                                    <input type="text" class="form-control" id="protocolo" 
                                           value="${dadosAtuais.protocolo || ''}" 
                                           placeholder="Digite o protocolo">
                                    ${dadosAtuais.protocolo ? `<small class="text-success">Protocolo atual: ${dadosAtuais.protocolo}</small>` : ''}
                                </div>
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="agendamentoConfirmado" 
                                               ${dadosAtuais.agendamento_confirmado ? 'checked' : ''}>
                                        <label class="form-check-label" for="agendamentoConfirmado">
                                            <i class="fas fa-check-circle text-success"></i> Agendamento Confirmado
                                        </label>
                                    </div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                            <button type="button" class="btn btn-primary" onclick="workspace.salvarEdicaoDatas('separacao', '${loteId}')">
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

    // DEPRECATED - Manter vazio para compatibilidade apenas
    // Redireciona para o novo método simplificado
    abrirModalEdicaoDatasDireto(tipo, loteId, dadosAtuais) {
        this.abrirModalDatas(loteId, dadosAtuais);
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
                confirmButtonColor: window.Notifications?.colors?.neutral || '#6c757d'
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
            // Sempre usar endpoint de separação (pre-separacao é compatível)
            const endpoint = `/carteira/api/separacao/${loteId}/atualizar-datas`;

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
                // Atualizar em TODAS as estruturas de dados para garantir consistência

                // 1. Atualizar preSeparacoes (se existir)
                const loteData = this.preSeparacoes.get(loteId);
                if (loteData) {
                    loteData.dataExpedicao = expedicao;
                    loteData.data_expedicao = expedicao;
                    loteData.expedicao = expedicao;  // IMPORTANTE: campo usado na view compacta
                    loteData.data_agendamento = agendamento;
                    loteData.agendamento = agendamento;  // IMPORTANTE: campo usado na view compacta
                    loteData.protocolo = protocolo;
                    loteData.agendamento_confirmado = agendamentoConfirmado;
                }

                // 2. Atualizar separacoesConfirmadas
                const separacao = this.separacoesConfirmadas.find(s => s.separacao_lote_id === loteId);
                if (separacao) {
                    separacao.expedicao = expedicao;
                    separacao.agendamento = agendamento;
                    separacao.protocolo = protocolo;
                    separacao.agendamento_confirmado = agendamentoConfirmado;
                }

                // 3. Atualizar na carteira agrupada (se existir) - CRÍTICO para view compacta
                if (window.carteiraAgrupada && window.carteiraAgrupada.separacoesPorPedido) {
                    for (const [pedido, separacoes] of window.carteiraAgrupada.separacoesPorPedido) {
                        const sep = separacoes.find(s => s.separacao_lote_id === loteId);
                        if (sep) {
                            sep.expedicao = expedicao;
                            sep.agendamento = agendamento;
                            sep.protocolo = protocolo;
                            sep.agendamento_confirmado = agendamentoConfirmado;
                            break;
                        }
                    }
                }

                // 4. Atualizar card visual
                const card = document.querySelector(`.card[data-lote-id="${loteId}"]`);
                if (card && this.loteManager) {
                    // Atualizar dados no Map
                    const loteData = this.preSeparacoes.get(loteId);
                    if (loteData) {
                        loteData.expedicao = expedicao;
                        loteData.agendamento = agendamento;
                        loteData.protocolo = protocolo;
                        loteData.agendamento_confirmado = agendamentoConfirmado;

                        // Re-renderizar o card inteiro para garantir consistência
                        this.loteManager.atualizarCardLote(loteId);
                    }
                }

                // 5. Atualizar a view compacta (CORREÇÃO DO PROBLEMA PRINCIPAL)
                this.atualizarViewCompactaDireto(loteId, expedicao, agendamento, protocolo, agendamentoConfirmado);

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
                    confirmButtonColor: window.Notifications?.colors?.danger || '#dc3545'
                });
            }

        } catch (error) {
            console.error('Erro ao atualizar datas:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro Interno',
                text: 'Ocorreu um erro ao atualizar as datas. Tente novamente.',
                confirmButtonColor: window.Notifications?.colors?.danger || '#dc3545'
            });
        }
    }

    imprimirSeparacao(loteId) {
        window.open(`/carteira/separacao/${loteId}/imprimir`, '_blank');
    }

    // 🧹 TASK 7: Funcao reverterAgendamentoLote duplicada removida
    // (havia 2 definicoes, a 2a sobrescrevia a 1a; mantida apenas a versao
    // completa em ~linha 801 que atualiza preSeparacoes e card sem reload).

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
        return window.PortalAgendamento.verificarProtocoloNoPortal(loteId, protocolo);
    }


    mostrarToast(mensagem, tipo = 'info') {
        // Usar módulo centralizado se disponível
        if (window.Notifications && window.Notifications.toast) {
            return window.Notifications.toast(mensagem, tipo);
        }

        // Fallback para SweetAlert2
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
            // Fallback final
            const icone = tipo === 'success' ? '✅' : tipo === 'error' ? '❌' : 'ℹ️';
            alert(`${icone} ${mensagem}`);
        }
    }

    /**
     * 🆕 CARREGAR DADOS DE ESTOQUE DE FORMA ASSÍNCRONA
     * Carrega estoque, projeções e menor_estoque após renderização inicial
     */
    async carregarDadosEstoqueAssincrono(numPedido) {
        // 🆕 Verificar se o pedido ainda está visível
        const pedidoRow = document.querySelector(`.pedido-row[data-pedido="${numPedido}"]`);
        if (pedidoRow && pedidoRow.style.display === 'none') {
            console.log(`🚫 Pedido ${numPedido} foi filtrado, cancelando carregamento de estoque`);
            return;
        }

        try {
            console.log(`📊 Carregando dados de estoque assincronamente para pedido ${numPedido}`);

            // Mostrar loading
            const loadingSpinner = document.getElementById(`loading-produtos-${numPedido}`);
            if (loadingSpinner) {
                loadingSpinner.style.display = 'inline-block';
            }

            // Fazer requisição usando WorkspaceAPI
            const data = await this.api.buscarEstoqueAssincrono(numPedido);

            // Atualizar dados locais com informações de estoque
            console.log('🔄 Atualizando dados de estoque assíncronos para', data.produtos.length, 'produtos');
            data.produtos.forEach(produto => {
                const dadosExistentes = this.dadosProdutos.get(produto.cod_produto);
                if (dadosExistentes) {
                    // DEBUG: Log do que está sendo atualizado
                    console.log(`📦 Atualizando produto ${produto.cod_produto}:`, {
                        estoque_hoje: produto.estoque_hoje || produto.estoque || 0,
                        data_disponibilidade: produto.data_disponibilidade,
                        qtd_disponivel: produto.qtd_disponivel
                    });

                    // Mesclar dados de estoque com dados existentes (garantir que não sejam undefined)
                    Object.assign(dadosExistentes, {
                        // Campos principais de estoque
                        estoque_hoje: produto.estoque_hoje || produto.estoque || produto.estoque_d0 || 0,
                        estoque: produto.estoque || produto.estoque_hoje || produto.estoque_d0 || 0,
                        menor_estoque_7d: produto.menor_estoque_7d || produto.menor_estoque_produto_d7 || 0,
                        producao_hoje: produto.producao_hoje || 0,
                        estoque_data_expedicao: produto.estoque_data_expedicao || produto.saldo_estoque_pedido || 0,

                        // IMPORTANTE: Adicionar campos de disponibilidade
                        data_disponibilidade: produto.data_disponibilidade || null,
                        qtd_disponivel: produto.qtd_disponivel || 0,

                        // Adicionar projeções D0-D28 se disponíveis
                        ...Object.fromEntries(
                            Object.entries(produto)
                                .filter(([key]) => key.startsWith('estoque_d'))
                                .map(([key, value]) => [key, value || 0])
                        )
                    });
                }
            });

            // 🆕 OPÇÃO 1: Atualizar apenas os valores nas células existentes (sem re-renderizar)
            // Isso evita o flicker e mantém a estrutura da tabela estável
            const tabelaBody = document.querySelector(`#tabela-produtos-container-${numPedido} tbody`);
            if (tabelaBody) {
                // Percorrer cada linha da tabela e atualizar apenas os valores de estoque
                data.produtos.forEach(produto => {
                    const row = tabelaBody.querySelector(`tr[data-produto="${produto.cod_produto}"]`);
                    if (row) {
                        // CORREÇÃO: Usar índices de células em vez de seletores de classe

                        // Atualizar célula de Est.Hoje (6ª coluna - cells[6])
                        const estoqueCell = row.cells[6];
                        if (estoqueCell) {
                            const estoque = Math.floor(produto.estoque || produto.estoque_d0 || 0);
                            const badgeClass = estoque > 100 ? 'bg-success' : estoque > 0 ? 'bg-warning' : 'bg-danger';
                            estoqueCell.innerHTML = `
                                <span class="badge ${badgeClass}" title="Estoque disponível hoje">
                                    ${estoque.toLocaleString('pt-BR')}
                                </span>
                            `;
                        }

                        // Atualizar célula de Est.Min.D+7 (7ª coluna - cells[7])
                        const menor7dCell = row.cells[7];
                        if (menor7dCell) {
                            const menorEstoque = Math.floor(produto.menor_estoque_produto_d7 || 0);
                            const badgeClass = menorEstoque <= 0 ? 'bg-danger' : menorEstoque <= 20 ? 'bg-warning' : 'bg-secondary';
                            menor7dCell.innerHTML = `
                                <span class="badge ${badgeClass}" title="Menor estoque projetado nos próximos 7 dias">
                                    ${menorEstoque.toLocaleString('pt-BR')}
                                </span>
                            `;
                        }

                        // Atualizar célula de Prod.Hoje (8ª coluna - cells[8])
                        const prodHojeCell = row.cells[8];
                        if (prodHojeCell) {
                            const producao = Math.floor(produto.producao_hoje || 0);
                            const badgeClass = producao > 0 ? 'bg-secondary' : 'bg-secondary';
                            prodHojeCell.innerHTML = `
                                <span class="badge ${badgeClass}" title="Quantidade programada para produzir hoje">
                                    ${producao.toLocaleString('pt-BR')}
                                </span>
                            `;
                        }

                        // Atualizar célula de Disponível (9ª coluna - td:nth-child(10))
                        const disponibilidadeCell = row.cells[9]; // 10ª célula (index 9)
                        if (disponibilidadeCell) {
                            // Calcular status de disponibilidade usando a mesma lógica do workspace-tabela.js
                            const qtdPedido = produto.qtd_pedido || produto.qtd_saldo_produto_pedido || 0;
                            const estoqueHoje = produto.estoque || produto.estoque_d0 || 0;
                            const dataDisponivel = produto.data_disponibilidade;
                            const qtdDisponivel = produto.qtd_disponivel || 0;

                            let statusDisponibilidade;

                            // Se tem estoque hoje suficiente
                            if (estoqueHoje >= qtdPedido) {
                                statusDisponibilidade = {
                                    class: 'bg-success text-white',
                                    texto: 'DISPONÍVEL',
                                    detalhes: `${Math.floor(estoqueHoje).toLocaleString('pt-BR')} unidades`
                                };
                            }
                            // Se tem data de disponibilidade futura
                            else if (dataDisponivel && dataDisponivel !== 'Sem previsão') {
                                const hoje = new Date().toISOString().split('T')[0];
                                if (dataDisponivel > hoje) {
                                    const diasFuturo = Math.ceil((new Date(dataDisponivel) - new Date()) / (1000 * 60 * 60 * 24));
                                    // Calcular a data formatada
                                    const dataFutura = new Date();
                                    dataFutura.setDate(dataFutura.getDate() + diasFuturo);
                                    const dia = String(dataFutura.getDate()).padStart(2, '0');
                                    const mes = String(dataFutura.getMonth() + 1).padStart(2, '0');
                                    const dataFormatada = `${dia}/${mes}`;

                                    statusDisponibilidade = {
                                        class: 'bg-secondary text-white',
                                        texto: `${Math.floor(qtdDisponivel).toLocaleString('pt-BR')}`,
                                        detalhes: `D+${diasFuturo} | ${dataFormatada}`
                                    };
                                } else if (qtdDisponivel > 0) {
                                    statusDisponibilidade = {
                                        class: 'bg-warning text-dark',
                                        texto: 'PARCIAL',
                                        detalhes: `${Math.floor(qtdDisponivel).toLocaleString('pt-BR')} disponível`
                                    };
                                }
                            }
                            // Se tem estoque parcial
                            else if (estoqueHoje > 0) {
                                statusDisponibilidade = {
                                    class: 'bg-warning text-dark',
                                    texto: 'PARCIAL',
                                    detalhes: `${Math.floor(estoqueHoje).toLocaleString('pt-BR')} de ${Math.floor(qtdPedido).toLocaleString('pt-BR')}`
                                };
                            }
                            // Sem estoque e sem previsão
                            else {
                                statusDisponibilidade = {
                                    class: 'bg-danger text-white',
                                    texto: 'INDISPONÍVEL',
                                    detalhes: 'Sem estoque'
                                };
                            }

                            // Atualizar HTML da célula
                            disponibilidadeCell.innerHTML = `
                                <span class="badge ${statusDisponibilidade.class}">
                                    ${statusDisponibilidade.texto}
                                </span>
                                ${statusDisponibilidade.detalhes ? `<br><small class="text-muted">${statusDisponibilidade.detalhes}</small>` : ''}
                            `;
                        }

                        // Atualizar ícone de ruptura se existir
                        const rupturaIcon = row.querySelector('.ruptura-icon');
                        if (rupturaIcon && produto.dia_ruptura) {
                            rupturaIcon.innerHTML = `<i class="fas fa-exclamation-triangle text-danger" title="Ruptura prevista"></i>`;
                        }
                    }
                });

                // Não precisa re-configurar checkboxes pois a estrutura não mudou
                console.log('✅ Valores de estoque atualizados sem re-renderizar');
            }

            // Esconder loading
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }

            console.log(`✅ Dados de estoque carregados para ${data.produtos.length} produtos`);

        } catch (error) {
            // 🆕 Ignorar erro de abort (cancelamento)
            if (error.name === 'AbortError') {
                console.log(`✔️ Carregamento de estoque cancelado para pedido ${numPedido}`);
                return;
            }
            // 🆕 Ignorar erro de abort (cancelamento)
            if (error.name === 'AbortError') {
                console.log(`✔️ Carregamento de estoque cancelado para pedido ${numPedido}`);
                return;
            }

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

    // Método para atualizar diretamente a view compacta sem re-renderizar
    atualizarViewCompactaDireto(loteId, expedicao, agendamento, protocolo, agendamentoConfirmado) {
        console.log(`🔄 Atualizando view compacta para lote ${loteId}`);
        console.log(`   Dados: exp=${expedicao}, age=${agendamento}, prot=${protocolo}, conf=${agendamentoConfirmado}`);

        // Buscar linha da separação compacta usando múltiplos seletores
        let linhaCompacta = document.querySelector(`tr[data-lote-id="${loteId}"]`);
        if (!linhaCompacta) {
            // Tentar com ID direto usando novo padrão
            linhaCompacta = document.getElementById(`separacao-compacta-${loteId}`);
        }
        if (!linhaCompacta) {
            // Tentar variações antigas para compatibilidade
            const idVariacoes = [
                `separacoes-compactas-${loteId.replace(/_/g, '')}`,
                `separacoes-compactas-${loteId}`,
                loteId
            ];

            for (const id of idVariacoes) {
                linhaCompacta = document.getElementById(id);
                if (linhaCompacta) break;
            }
        }

        if (linhaCompacta) {
            console.log(`✅ Encontrou linha compacta:`, linhaCompacta);

            // Buscar células da linha
            const celulas = linhaCompacta.querySelectorAll('td');

            // Usar seletores data-field para melhor confiabilidade
            // 🆕 FEAT 4: Indices de fallback ajustados pela insercao da coluna "Embarque" (idx 2):
            // 0=Tipo, 1=Status, 2=Embarque, 3=Valor, 4=Peso, 5=Pallet,
            // 6=Expedicao, 7=Agendamento, 8=Protocolo, 9=Confirmacao
            // Atualizar coluna Expedição
            const celulaExpedicao = linhaCompacta.querySelector('td[data-field="expedicao"]');
            if (celulaExpedicao) {
                console.log(`📅 Atualizando expedição`);
                celulaExpedicao.innerHTML = expedicao ? this.formatarData(expedicao) : '-';
            } else if (celulas[6]) {
                celulas[6].innerHTML = expedicao ? this.formatarData(expedicao) : '-';
            }

            // Atualizar coluna Agendamento
            const celulaAgendamento = linhaCompacta.querySelector('td[data-field="agendamento"]');
            if (celulaAgendamento) {
                console.log(`📅 Atualizando agendamento`);
                celulaAgendamento.innerHTML = agendamento ? this.formatarData(agendamento) : '-';
            } else if (celulas[7]) {
                celulas[7].innerHTML = agendamento ? this.formatarData(agendamento) : '-';
            }

            // Atualizar coluna Protocolo
            const celulaProtocolo = linhaCompacta.querySelector('td[data-field="protocolo"]');
            if (celulaProtocolo) {
                console.log(`🔢 Atualizando protocolo`);
                celulaProtocolo.innerHTML = `<small>${protocolo || '-'}</small>`;
            } else if (celulas[8]) {
                celulas[8].innerHTML = `<small>${protocolo || '-'}</small>`;
            }

            // Atualizar coluna Confirmação
            const celulaConfirmacao = linhaCompacta.querySelector('td[data-field="confirmacao"]');
            if (celulaConfirmacao) {
                console.log(`✅ Atualizando confirmação`);
                if (agendamentoConfirmado) {
                    celulaConfirmacao.innerHTML = '<span class="badge bg-success"><i class="fas fa-check-circle"></i> Confirmado</span>';
                } else if (protocolo) {
                    celulaConfirmacao.innerHTML = '<span class="badge bg-warning text-dark"><i class="fas fa-hourglass-half"></i> Aguardando</span>';
                } else {
                    celulaConfirmacao.innerHTML = '-';
                }
            } else if (celulas[9]) {
                if (agendamentoConfirmado) {
                    celulas[9].innerHTML = '<span class="badge bg-success">Confirmado</span>';
                } else if (protocolo) {
                    celulas[9].innerHTML = '<span class="badge bg-warning">Aguardando</span>';
                } else {
                    celulas[9].innerHTML = '<span class="badge bg-secondary">-</span>';
                }
            }

            // Atualizar também o botão de Datas se existir para passar os novos valores
            const botaoDatas = linhaCompacta.querySelector('button[onclick*="abrirModalDatas"]');
            if (botaoDatas) {
                const novoOnclick = `carteiraAgrupada.abrirModalDatas('${loteId}', true, '${expedicao || ''}', '${agendamento || ''}', '${protocolo || ''}', ${agendamentoConfirmado})`;
                botaoDatas.setAttribute('onclick', novoOnclick);
                console.log(`🔄 Atualizado onclick do botão Datas`);
            }
        } else {
            console.warn(`⚠️ Não encontrou linha compacta para lote ${loteId}`);
        }

        // Atualizar também no carteiraAgrupada se existir
        if (window.carteiraAgrupada) {
            // Atualizar dadosAgrupados
            if (window.carteiraAgrupada.dadosAgrupados && window.carteiraAgrupada.dadosAgrupados.grupos) {
                for (const grupo of window.carteiraAgrupada.dadosAgrupados.grupos) {
                    if (grupo.separacoes_compactas) {
                        const sepCompacta = grupo.separacoes_compactas.find(s => s.lote_id === loteId);
                        if (sepCompacta) {
                            sepCompacta.expedicao = expedicao;
                            sepCompacta.agendamento = agendamento;
                            sepCompacta.protocolo = protocolo;
                            sepCompacta.agendamento_confirmado = agendamentoConfirmado;
                            console.log(`✅ Atualizado sepCompacta em dadosAgrupados`);
                            break;
                        }
                    }
                }
            }
        }
    }
}

// Disponibilizar globalmente
window.WorkspaceMontagem = WorkspaceMontagem;
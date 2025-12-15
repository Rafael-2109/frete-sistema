/**
 * LISTA DE MATERIAIS - Gestão de Estrutura de Produtos (BOM)
 * Utiliza jsTree para visualização hierárquica
 */

// Estado global
const ListaMateriais = {
    produtoAtual: null,
    modoEdicao: false,
    componenteEditando: null,

    /**
     * Inicializa a aplicação
     */
    init() {
        console.log('🚀 Inicializando Lista de Materiais...');
        this.bindEvents();
    },

    /**
     * Vincula eventos
     */
    bindEvents() {
        console.log('🔗 Vinculando eventos...');

        // Busca de produtos
        $('#btn-buscar-produto').on('click', () => this.buscarProdutos());
        $('#input-busca-produto').on('keypress', (e) => {
            if (e.which === 13) this.buscarProdutos();
        });

        // Verificar se botão existe
        const btnListarTodos = $('#btn-listar-todos');
        console.log('✅ Botão "Listar Todos" encontrado:', btnListarTodos.length > 0);

        $('#btn-listar-todos').on('click', () => {
            console.log('🖱️ Botão "Listar Todos" clicado!');
            this.listarTodosProdutos();
        });

        // Ações de componente
        $('#btn-adicionar-componente-raiz, #btn-adicionar-primeiro-componente')
            .on('click', () => this.abrirModalComponente());
        $('#btn-salvar-componente').on('click', () => this.salvarComponente());

        // Validação de código de componente
        $('#cod-produto-componente').on('blur', () => this.validarCodigoComponente());

        // Explosão BOM
        $('#btn-explodir-bom').on('click', () => this.abrirModalExplosao());
        $('#btn-calcular-explosao').on('click', () => this.calcularExplosao());

        // Validação de estrutura
        $('#btn-validar-estrutura').on('click', () => this.validarEstrutura());
    },

    /**
     * Busca produtos
     */
    async buscarProdutos() {
        const busca = $('#input-busca-produto').val().trim();

        if (!busca) {
            toastr.warning('Digite algo para buscar');
            return;
        }

        try {
            const response = await fetch(`/manufatura/api/lista-materiais/produtos-produzidos?busca=${encodeURIComponent(busca)}`);
            const data = await response.json();

            if (data.sucesso) {
                this.exibirProdutos(data.produtos);
            } else {
                toastr.error(data.erro || 'Erro ao buscar produtos');
            }
        } catch (error) {
            console.error('Erro ao buscar produtos:', error);
            toastr.error('Erro ao buscar produtos');
        }
    },

    /**
     * Lista todos os produtos produzidos
     */
    async listarTodosProdutos() {
        console.log('📋 Buscando lista de todos os produtos...');

        try {
            const url = '/manufatura/api/lista-materiais/produtos-produzidos';
            console.log('🌐 Fazendo request para:', url);

            const response = await fetch(url);
            console.log('📡 Response status:', response.status);

            const data = await response.json();
            console.log('📦 Dados recebidos:', data);

            if (data.sucesso) {
                console.log(`✅ ${data.produtos.length} produtos encontrados`);
                this.exibirProdutos(data.produtos);
            } else {
                console.error('❌ Erro na resposta:', data.erro);
                toastr.error(data.erro || 'Erro ao listar produtos');
            }
        } catch (error) {
            console.error('❌ Erro ao listar produtos:', error);
            toastr.error('Erro ao listar produtos: ' + error.message);
        }
    },

    /**
     * Exibe lista de produtos
     */
    exibirProdutos(produtos) {
        console.log('📋 exibirProdutos chamado com', produtos.length, 'produtos');
        console.log('Produtos:', produtos);

        const tbody = $('#tbody-produtos');
        console.log('tbody encontrado:', tbody.length > 0);
        tbody.empty();

        if (produtos.length === 0) {
            console.log('⚠️ Nenhum produto para exibir');
            tbody.append(`
                <tr>
                    <td colspan="5" class="text-center text-muted">
                        <i class="fas fa-inbox fa-2x mb-2"></i>
                        <p>Nenhum produto encontrado</p>
                    </td>
                </tr>
            `);
            $('#area-resultados').fadeIn();
            return;
        }

        produtos.forEach(produto => {
            const badgeEstrutura = produto.tem_estrutura
                ? '<span class="badge badge-tem-estrutura">Tem Estrutura</span>'
                : '<span class="badge badge-sem-estrutura">Sem Estrutura</span>';

            tbody.append(`
                <tr data-cod-produto="${produto.cod_produto}" class="tr-produto-clicavel" style="cursor: pointer;">
                    <td><strong>${produto.cod_produto}</strong></td>
                    <td>${produto.nome_produto}</td>
                    <td>${badgeEstrutura}</td>
                    <td>
                        <i class="fas fa-chevron-down text-primary"></i>
                        <small class="text-muted">Clique para expandir</small>
                    </td>
                </tr>
            `);
        });

        // Event listener para expandir estrutura ao clicar na linha
        console.log('🔗 Vinculando eventos às linhas de produto...');
        const linhas = $('.tr-produto-clicavel');
        console.log(`✅ ${linhas.length} linhas encontradas`);

        $('.tr-produto-clicavel').on('click', (e) => {
            console.log('🖱️ Linha de produto clicada!');
            const $linhaClicada = $(e.currentTarget);
            const cod = $linhaClicada.data('cod-produto');
            console.log(`📦 Código do produto: ${cod}`);

            // Verificar se já está expandido
            const $proxima = $linhaClicada.next('.linha-estrutura-bom');
            if ($proxima.length > 0) {
                // Já expandido, colapsar
                $proxima.slideUp(300, () => $proxima.remove());
                $linhaClicada.find('i.fa-chevron-down').removeClass('fa-chevron-down').addClass('fa-chevron-right');
            } else {
                // Expandir
                this.carregarEstrutura(cod, $linhaClicada);
                $linhaClicada.find('i.fa-chevron-right').removeClass('fa-chevron-right').addClass('fa-chevron-down');
            }
        });

        $('#area-resultados').fadeIn();
    },

    /**
     * Carrega estrutura BOM de um produto
     */
    async carregarEstrutura(codProduto, $linhaClicada) {
        console.log(`🔍 carregarEstrutura chamado para: ${codProduto}`);
        this.produtoAtual = codProduto;

        // Remover linha de estrutura anterior se existir
        $('.linha-estrutura-bom').remove();

        // Criar nova linha expansível (sem cabeçalho repetido)
        const numColunas = $linhaClicada.find('td').length;
        const $linhaEstrutura = $(`
            <tr class="linha-estrutura-bom">
                <td colspan="${numColunas}" class="linha-estrutura-bom-cell">
                    <div id="estrutura-expandida" style="max-width: 100%; overflow-x: hidden;">
                        <div class="d-flex justify-content-end align-items-center mb-2">
                            <div class="btn-group" role="group">
                                <button class="btn btn-sm btn-outline-primary" id="btn-adicionar-componente-inline" title="Adicionar componente">
                                    <i class="fas fa-plus"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-success" id="btn-explodir-bom-inline" title="Explodir BOM completo">
                                    <i class="fas fa-expand"></i>
                                </button>
                            </div>
                        </div>

                        <div id="loading-estrutura-inline" class="text-center py-3">
                            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                            <small class="ms-2">Carregando...</small>
                        </div>

                        <div id="tree-bom-inline" style="display: none;"></div>

                        <div id="empty-estrutura-inline" class="text-center py-3" style="display: none;">
                            <i class="fas fa-box-open fa-2x text-muted mb-2"></i>
                            <p class="text-muted mb-0">Produto sem componentes cadastrados.</p>
                        </div>
                    </div>
                </td>
            </tr>
        `);

        // Inserir após a linha clicada
        $linhaClicada.after($linhaEstrutura);

        // Event listeners
        $('#btn-adicionar-componente-inline').on('click', () => this.abrirModalComponente());

        $('#btn-explodir-bom-inline').on('click', () => this.abrirModalExplosao());

        try {
            const url = `/manufatura/api/lista-materiais/${codProduto}`;
            console.log(`🌐 Fazendo request para: ${url}`);

            const response = await fetch(url);
            console.log(`📡 Response status: ${response.status}`);

            const data = await response.json();
            console.log(`📦 Dados recebidos:`, data);

            if (data.sucesso) {
                console.log('✅ Dados carregados com sucesso');
                console.log(`📊 ${data.componentes.length} componentes encontrados`);

                $('#loading-estrutura-inline').hide();

                if (data.componentes.length === 0) {
                    console.log('⚠️ Nenhum componente - mostrando empty state');
                    $('#empty-estrutura-inline').show();
                } else {
                    console.log('🌳 Renderizando árvore inline...');
                    this.renderizarArvoreInline(data);
                }
            } else {
                console.error('❌ Erro na resposta:', data.erro);
                $('#loading-estrutura-inline').hide();
                $('#empty-estrutura-inline').html(`
                    <i class="fas fa-exclamation-triangle fa-2x text-danger mb-2"></i>
                    <p class="text-danger mb-0">${data.erro || 'Erro ao carregar estrutura'}</p>
                `).show();
            }
        } catch (error) {
            console.error('❌ Erro ao carregar estrutura:', error);
            $('#loading-estrutura-inline').hide();
            $('#empty-estrutura-inline').html(`
                <i class="fas fa-exclamation-triangle fa-2x text-danger mb-2"></i>
                <p class="text-danger mb-0">Erro: ${error.message}</p>
            `).show();
        }
    },

    /**
     * Renderiza árvore BOM inline como TABELA (accordion style)
     */
    renderizarArvoreInline(data) {
        const container = $('#tree-bom-inline');
        container.empty();

        if (data.componentes && data.componentes.length > 0) {
            const tabelaHtml = `
                <table class="table table-sm table-hover bom-table">
                    <thead>
                        <tr>
                            <th style="width: 30px;"></th>
                            <th style="width: 40px;"></th>
                            <th style="width: 120px;">Código</th>
                            <th>Produto</th>
                            <th style="width: 100px;" class="text-end">Quantidade</th>
                            <th style="width: 100px;" class="text-end">Estoque</th>
                            <th style="width: 80px;" class="text-center">Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.renderizarLinhasTabela(data.componentes, 0)}
                    </tbody>
                </table>
            `;
            container.html(tabelaHtml);

            // Vincular eventos
            this.bindAccordionEvents();
        }

        container.show();
    },

    /**
     * Renderiza linhas da tabela BOM (accordion) - VERSÃO HARMONIZADA
     */
    renderizarLinhasTabela(componentes, nivel) {
        if (!componentes || componentes.length === 0) {
            return '';
        }

        return componentes.map(comp => {
            const isIntermediate = comp.tipo_componente && comp.tipo_componente.toUpperCase() === 'INTERMEDIARIO';
            const produtoProduzido = comp.produto_produzido === true;
            const podeExpandir = isIntermediate || produtoProduzido;
            const rowId = `row-${comp.cod_produto_componente}-${Math.random().toString(36).substring(2, 11)}`;

            // Ícone baseado no tipo (usando classes CSS theme-aware)
            let iconeClass = 'fa-leaf';
            let iconeColorClass = 'bom-icon-componente';
            if (comp.tipo_componente) {
                const tipo = comp.tipo_componente.toUpperCase();
                if (tipo === 'ACABADO') {
                    iconeClass = 'fa-cube';
                    iconeColorClass = 'bom-icon-acabado';
                } else if (tipo === 'INTERMEDIARIO') {
                    iconeClass = 'fa-cog';
                    iconeColorClass = 'bom-icon-intermediario';
                }
            }

            // Linha principal com identação progressiva
            let html = `
                <tr class="bom-row bom-row-nivel-${nivel}" data-nivel="${nivel}" data-cod="${comp.cod_produto_componente}" data-row-id="${rowId}">
                    <td class="bom-col-expand">
                        ${podeExpandir ? `
                            <button class="btn-expand-accordion" data-row-id="${rowId}" data-cod="${comp.cod_produto_componente}" title="Expandir estrutura">
                                <i class="fas fa-chevron-right"></i>
                            </button>
                        ` : '<span class="tree-spacer"></span>'}
                    </td>
                    <td class="bom-col-icon">
                        <i class="fas ${iconeClass} ${iconeColorClass}"></i>
                    </td>
                    <td class="bom-col-codigo">
                        <code>${comp.cod_produto_componente}</code>
                    </td>
                    <td class="bom-col-produto">${comp.nome_produto_componente}</td>
                    <td class="bom-col-qtd text-end">
                        ${comp.qtd_utilizada !== null && comp.qtd_utilizada !== undefined ?
                            `<span class="badge rounded-pill bg-secondary">${this.formatarNumero(comp.qtd_utilizada)}</span>`
                            : '<span class="text-muted">-</span>'}
                    </td>
                    <td class="bom-col-estoque text-end">
                        ${comp.estoque_atual !== undefined && comp.estoque_atual !== null ?
                            `<span class="badge rounded-pill ${comp.estoque_atual > 0 ? 'bg-success' : 'bg-danger'}">${this.formatarNumero(comp.estoque_atual)}</span>`
                            : '<span class="text-muted">-</span>'}
                    </td>
                    <td class="bom-col-acoes text-center">
                        <div class="btn-group btn-group-sm" role="group">
                            <button class="btn btn-outline-primary btn-sm" title="Editar">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-outline-danger btn-sm btn-remover" data-id="${comp.id}" title="Remover">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;

            // Linha expansível para sub-componentes
            if (podeExpandir) {
                html += `
                    <tr class="bom-row-children" id="children-${rowId}" style="display: none;">
                        <td colspan="7" class="bom-children-cell">
                            <div class="bom-children-container" data-nivel="${nivel}">
                                <div class="loading-container">
                                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                                        <span class="visually-hidden">Carregando...</span>
                                    </div>
                                    <span class="ms-2 text-muted">Carregando componentes...</span>
                                </div>
                            </div>
                        </td>
                    </tr>
                `;
            }

            return html;
        }).join('');
    },

    /**
     * Renderiza um item BOM (produto) recursivamente - MÉTODO ANTIGO (manter para compatibilidade)
     */
    renderizarItemBOM(item, nivel) {
        const tipoClass = `tipo-${item.tipo.toLowerCase()}`;
        const icone = this.getIconeHTML(item.tipo);
        const hasChildren = item.componentes && item.componentes.length > 0;
        const isIntermediate = item.tipo.toUpperCase() === 'INTERMEDIARIO';
        const produtoProduzido = item.produto_produzido === true;

        // ID único para o item
        const itemId = `bom-item-${item.cod_produto}-${nivel}-${Math.random().toString(36).substring(2, 11)}`;

        // Determinar se deve ter botão de expansão
        // Produtos intermediários OU produtos produzidos com componentes devem ser expansíveis
        const shouldExpand = (isIntermediate || produtoProduzido) && (hasChildren || !item.is_root);

        let html = `
            <div class="bom-item" data-nivel="${nivel}">
                <div class="bom-card ${tipoClass}" data-cod-produto="${item.cod_produto}">
                    ${shouldExpand ? `
                        <div class="bom-expand-btn" data-item-id="${itemId}" data-cod="${item.cod_produto}" data-loaded="false">
                            <i class="fas fa-chevron-right"></i>
                        </div>
                    ` : '<div style="width: 28px;"></div>'}

                    <div class="bom-icon">
                        ${icone}
                    </div>

                    <div class="bom-content">
                        <div class="bom-header">
                            <span class="bom-codigo">${item.cod_produto}</span>
                            <span class="bom-nome" title="${item.nome_produto}">${item.nome_produto}</span>
                            ${item.qtd_utilizada !== null ? `
                                <span class="bom-badge qtd">
                                    <i class="fas fa-calculator"></i> ${this.formatarNumero(item.qtd_utilizada)}
                                </span>
                            ` : ''}
                            ${item.estoque_atual !== undefined && item.estoque_atual !== null ? `
                                <span class="bom-badge ${item.estoque_atual > 0 ? 'bom-badge-estoque-ok' : 'bom-badge-estoque-falta'}">
                                    <i class="fas fa-boxes"></i> ${this.formatarNumero(item.estoque_atual)}
                                </span>
                            ` : ''}
                            ${hasChildren && item.is_root ? `
                                <span class="bom-badge tipo">
                                    <i class="fas fa-layer-group"></i> ${item.componentes.length}
                                </span>
                            ` : ''}
                        </div>
                    </div>

                    <div class="bom-actions">
                        <button class="bom-action-btn btn-editar-componente"
                                data-cod="${item.cod_produto}"
                                title="Editar">
                            <i class="fas fa-edit"></i>
                        </button>
                        ${!item.is_root ? `
                            <button class="bom-action-btn btn-remover-componente"
                                    data-id="${item.id}"
                                    title="Remover">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>

                ${shouldExpand ? `
                    <div class="bom-children" id="${itemId}-children" data-cod="${item.cod_produto}" data-loaded="false">
                        ${hasChildren && item.is_root ?
                            this.renderizarComponentes(item.componentes, nivel + 1) :
                            `<div class="bom-loading">
                                <div class="spinner-border"></div>
                                <span>Clique no botão para expandir...</span>
                            </div>`
                        }
                    </div>
                ` : ''}
            </div>
        `;

        return html;
    },

    /**
     * Renderiza lista de componentes
     */
    renderizarComponentes(componentes, nivel) {
        if (!componentes || componentes.length === 0) {
            return '<div class="bom-empty">Nenhum componente cadastrado</div>';
        }

        return componentes.map(comp => {
            return this.renderizarItemBOM({
                id: comp.id,
                cod_produto: comp.cod_produto_componente,
                nome_produto: comp.nome_produto_componente,
                tipo: comp.tipo_componente,
                qtd_utilizada: comp.qtd_utilizada,
                produto_produzido: comp.produto_produzido || false,
                estoque_atual: comp.estoque_atual,
                componentes: [],
                is_root: false
            }, nivel);
        }).join('');
    },

    /**
     * Vincula eventos do accordion
     */
    bindAccordionEvents() {
        // Expandir/colapsar accordion
        $('.btn-expand-accordion').off('click').on('click', async (e) => {
            e.stopPropagation();
            const $btn = $(e.currentTarget);
            const rowId = $btn.data('row-id');
            const codProduto = $btn.data('cod');
            const $childrenRow = $(`#children-${rowId}`);
            const $icon = $btn.find('i');

            // Se já está expandido, colapsar
            if ($icon.hasClass('fa-chevron-down')) {
                $icon.removeClass('fa-chevron-down').addClass('fa-chevron-right');
                $childrenRow.hide();
                return;
            }

            // Expandir
            $icon.removeClass('fa-chevron-right').addClass('fa-chevron-down');
            $childrenRow.show();

            // Verificar se já foi carregado
            const $container = $childrenRow.find('.bom-children-container');
            if ($container.data('loaded') === 'true') {
                return;
            }

            // Carregar sub-estrutura
            try {
                const response = await fetch(`/manufatura/api/lista-materiais/${codProduto}`);
                const data = await response.json();

                if (data.sucesso && data.componentes.length > 0) {
                    const nivel = parseInt($btn.closest('tr').data('nivel')) + 1;
                    const subLinhas = this.renderizarLinhasTabela(data.componentes, nivel);

                    $container.html(subLinhas);
                    $container.data('loaded', 'true');

                    // Re-vincular eventos
                    this.bindAccordionEvents();
                } else {
                    $container.html(`
                        <tr>
                            <td colspan="7" class="text-center py-2">
                                <small class="text-muted">Nenhum componente cadastrado</small>
                            </td>
                        </tr>
                    `);
                }
            } catch (error) {
                console.error('Erro ao carregar:', error);
                $container.html(`
                    <tr>
                        <td colspan="7" class="text-center py-2">
                            <small class="text-danger"><i class="fas fa-exclamation-triangle"></i> Erro ao carregar</small>
                        </td>
                    </tr>
                `);
            }
        });

        // Botão remover
        $('.btn-remover').off('click').on('click', (e) => {
            e.stopPropagation();
            const id = $(e.currentTarget).data('id');
            if (id) {
                this.confirmarRemocao(id);
            }
        });
    },

    /**
     * Vincula eventos de expansão - MÉTODO ANTIGO (manter para compatibilidade)
     */
    bindExpandEvents() {
        $('.bom-expand-btn').off('click').on('click', async (e) => {
            e.stopPropagation();
            const $btn = $(e.currentTarget);
            const itemId = $btn.data('item-id');
            const codProduto = $btn.data('cod');
            const $children = $(`#${itemId}-children`);
            const isLoaded = $children.data('loaded') === 'true';

            // Se já está expandido, apenas colapsar
            if ($btn.hasClass('expanded')) {
                $btn.removeClass('expanded');
                $children.removeClass('expanded');
                return;
            }

            // Expandir
            $btn.addClass('expanded');

            // Se ainda não carregou, buscar estrutura do intermediário
            if (!isLoaded) {
                $children.html(`
                    <div class="bom-loading">
                        <div class="spinner-border"></div>
                        <span>Carregando estrutura...</span>
                    </div>
                `);

                try {
                    const response = await fetch(`/manufatura/api/lista-materiais/${codProduto}`);
                    const data = await response.json();

                    if (data.sucesso && data.componentes.length > 0) {
                        const nivel = parseInt($btn.closest('.bom-item').data('nivel')) + 1;
                        $children.html(this.renderizarComponentes(data.componentes, nivel));
                        $children.data('loaded', 'true');

                        // Re-vincular eventos nos novos elementos
                        this.bindExpandEvents();
                        this.bindActionButtons();
                    } else {
                        $children.html('<div class="bom-empty">Nenhum componente cadastrado</div>');
                    }
                } catch (error) {
                    console.error('Erro ao carregar sub-estrutura:', error);
                    $children.html(`
                        <div class="bom-empty text-danger">
                            <i class="fas fa-exclamation-triangle"></i> Erro ao carregar
                        </div>
                    `);
                }
            }

            $children.addClass('expanded');
        });

        this.bindActionButtons();
    },

    /**
     * Vincula botões de ação (editar, remover)
     */
    bindActionButtons() {
        $('.btn-editar-componente').off('click').on('click', (e) => {
            e.stopPropagation();
            const codProduto = $(e.currentTarget).data('cod');
            console.log('Editar componente:', codProduto);
            // TODO: Implementar edição
        });

        $('.btn-remover-componente').off('click').on('click', (e) => {
            e.stopPropagation();
            const componenteId = $(e.currentTarget).data('id');
            if (componenteId) {
                this.confirmarRemocao(componenteId);
            }
        });
    },

    /**
     * Retorna HTML do ícone por tipo
     */
    getIconeHTML(tipo) {
        const icones = {
            'ACABADO': '<i class="fas fa-cube"></i>',
            'INTERMEDIARIO': '<i class="fas fa-cog"></i>',
            'COMPONENTE': '<i class="fas fa-leaf"></i>',
            'DESCONHECIDO': '<i class="fas fa-question"></i>',
            'ERRO': '<i class="fas fa-exclamation-triangle"></i>'
        };
        return icones[tipo.toUpperCase()] || icones['DESCONHECIDO'];
    },

    /**
     * Formata número para exibição
     */
    formatarNumero(num) {
        if (num === null || num === undefined) return '-';
        return parseFloat(num).toLocaleString('pt-BR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 6
        });
    },

    /**
     * Renderiza árvore BOM usando jsTree (versão antiga - manter para compatibilidade)
     */
    renderizarArvore(data) {
        const treeData = this.construirDadosArvore(data);

        // Destruir árvore anterior se existir
        $('#tree-bom').jstree('destroy');

        // Criar nova árvore
        $('#tree-bom').jstree({
            core: {
                data: treeData,
                themes: {
                    name: 'default',
                    responsive: true
                },
                check_callback: true
            },
            plugins: ['contextmenu', 'types'],
            types: {
                'acabado': {
                    icon: 'jstree-icon-acabado'
                },
                'intermediario': {
                    icon: 'jstree-icon-intermediario'
                },
                'componente': {
                    icon: 'jstree-icon-componente'
                },
                'erro': {
                    icon: 'jstree-icon-erro'
                }
            },
            contextmenu: {
                items: (node) => this.getContextMenu(node)
            }
        });

        $('#tree-bom').show();
    },

    /**
     * Constrói dados para jsTree
     */
    construirDadosArvore(data) {
        const raiz = {
            id: `raiz_${data.produto.cod_produto}`,
            text: this.formatarTextoNo(
                data.produto.cod_produto,
                data.produto.nome_produto,
                null,
                data.produto.tipo
            ),
            type: data.produto.tipo.toLowerCase(),
            state: { opened: true },
            children: []
        };

        data.componentes.forEach(comp => {
            raiz.children.push({
                id: `comp_${comp.id}`,
                text: this.formatarTextoNo(
                    comp.cod_produto_componente,
                    comp.nome_produto_componente,
                    comp.qtd_utilizada,
                    comp.tipo_componente
                ),
                type: comp.tipo_componente.toLowerCase(),
                data: comp
            });
        });

        return [raiz];
    },

    /**
     * Formata texto do nó da árvore
     */
    formatarTextoNo(codigo, nome, quantidade, tipo) {
        let texto = `<strong>${codigo}</strong> - ${nome}`;

        if (quantidade !== null) {
            texto += ` <span class="badge-quantidade">${quantidade}</span>`;
        }

        return texto;
    },

    /**
     * Menu de contexto para nós da árvore
     */
    getContextMenu(node) {
        const nodeData = node.data;

        // Se é nó raiz
        if (node.id.startsWith('raiz_')) {
            return {
                adicionar: {
                    label: 'Adicionar Componente',
                    icon: 'fas fa-plus',
                    action: () => this.abrirModalComponente()
                }
            };
        }

        // Se é componente
        return {
            editar: {
                label: 'Editar',
                icon: 'fas fa-edit',
                action: () => this.abrirModalComponente(nodeData)
            },
            deletar: {
                label: 'Remover',
                icon: 'fas fa-trash',
                action: () => this.confirmarRemocao(nodeData.id)
            },
            separator: '---------',
            ver_detalhes: {
                label: 'Ver Detalhes',
                icon: 'fas fa-info-circle',
                action: () => this.verDetalhesComponente(nodeData)
            }
        };
    },

    /**
     * Abre modal para adicionar/editar componente
     */
    abrirModalComponente(componente = null) {
        this.modoEdicao = !!componente;
        this.componenteEditando = componente;

        // Resetar formulário
        $('#form-componente')[0].reset();
        $('#info-componente').hide();

        if (this.modoEdicao) {
            // Modo edição
            $('#modalComponenteTitulo').html('<i class="fas fa-edit"></i> Editar Componente');
            $('#componente-id').val(componente.id);
            $('#cod-produto-componente').val(componente.cod_produto_componente).prop('disabled', true);
            $('#qtd-utilizada').val(componente.qtd_utilizada);
            $('#versao').val(componente.versao || 'v1');
        } else {
            // Modo criação
            $('#modalComponenteTitulo').html('<i class="fas fa-plus"></i> Adicionar Componente');
            $('#cod-produto-componente').prop('disabled', false);
        }

        $('#cod-produto-produzido').val(this.produtoAtual);
        $('#nome-produto-produzido').text(`${this.produtoAtual} - ${$('#titulo-produto-estrutura').text()}`);

        const modal = new bootstrap.Modal(document.getElementById('modalComponente'));
        modal.show();
    },

    /**
     * Valida código do componente
     */
    async validarCodigoComponente() {
        const codigo = $('#cod-produto-componente').val().trim();

        if (!codigo) {
            $('#info-componente').hide();
            return;
        }

        try {
            // Buscar dados do produto em CadastroPalletizacao
            // (você pode criar um endpoint específico ou usar a busca existente)
            const response = await fetch(`/manufatura/api/lista-materiais/produtos-produzidos?busca=${codigo}`);
            const data = await response.json();

            if (data.sucesso && data.produtos.length > 0) {
                const produto = data.produtos.find(p => p.cod_produto === codigo);
                if (produto) {
                    $('#nome-componente-info').text(produto.nome_produto);
                    $('#tipo-componente-info').text(produto.tipo);
                    $('#info-componente').fadeIn();
                    return true;
                }
            }

            toastr.warning('Produto não encontrado');
            $('#info-componente').hide();
            return false;
        } catch (error) {
            console.error('Erro ao validar componente:', error);
            return false;
        }
    },

    /**
     * Salva componente (criar ou editar)
     */
    async salvarComponente() {
        const dados = {
            cod_produto_produzido: $('#cod-produto-produzido').val(),
            cod_produto_componente: $('#cod-produto-componente').val().trim(),
            qtd_utilizada: parseFloat($('#qtd-utilizada').val()),
            versao: $('#versao').val().trim() || 'v1'
        };

        // Validações
        if (!dados.cod_produto_componente) {
            toastr.error('Código do componente é obrigatório');
            return;
        }

        if (!dados.qtd_utilizada || dados.qtd_utilizada <= 0) {
            toastr.error('Quantidade deve ser maior que zero');
            return;
        }

        try {
            const url = this.modoEdicao
                ? `/manufatura/api/lista-materiais/${$('#componente-id').val()}`
                : '/manufatura/api/lista-materiais';

            const method = this.modoEdicao ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            });

            const data = await response.json();

            if (data.sucesso) {
                toastr.success(data.mensagem);
                bootstrap.Modal.getInstance(document.getElementById('modalComponente')).hide();

                // Recarregar estrutura
                this.carregarEstrutura(this.produtoAtual);
            } else {
                toastr.error(data.erro || 'Erro ao salvar componente');
            }
        } catch (error) {
            console.error('Erro ao salvar componente:', error);
            toastr.error('Erro ao salvar componente');
        }
    },

    /**
     * Confirma remoção de componente
     */
    confirmarRemocao(componenteId) {
        if (confirm('Deseja realmente remover este componente da estrutura?')) {
            this.removerComponente(componenteId);
        }
    },

    /**
     * Remove componente
     */
    async removerComponente(componenteId) {
        try {
            const response = await fetch(`/manufatura/api/lista-materiais/${componenteId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.sucesso) {
                toastr.success(data.mensagem);
                this.carregarEstrutura(this.produtoAtual);
            } else {
                toastr.error(data.erro || 'Erro ao remover componente');
            }
        } catch (error) {
            console.error('Erro ao remover componente:', error);
            toastr.error('Erro ao remover componente');
        }
    },

    /**
     * Abre modal de explosão BOM
     */
    abrirModalExplosao() {
        $('#qtd-explosao').val(1);
        $('#incluir-estoque-explosao').prop('checked', false);
        $('#resultado-explosao').html('');

        const modal = new bootstrap.Modal(document.getElementById('modalExplosao'));
        modal.show();
    },

    /**
     * Calcula explosão BOM
     */
    async calcularExplosao() {
        const qtd = parseFloat($('#qtd-explosao').val());
        const incluirEstoque = $('#incluir-estoque-explosao').is(':checked');

        if (!qtd || qtd <= 0) {
            toastr.error('Quantidade inválida');
            return;
        }

        try {
            const url = `/manufatura/api/lista-materiais/explodir/${this.produtoAtual}?qtd_necessaria=${qtd}&incluir_estoque=${incluirEstoque}`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.sucesso) {
                this.exibirResultadoExplosao(data, incluirEstoque);
            } else {
                toastr.error(data.erro || 'Erro ao calcular explosão');
            }
        } catch (error) {
            console.error('Erro ao calcular explosão:', error);
            toastr.error('Erro ao calcular explosão');
        }
    },

    /**
     * Exibe resultado da explosão BOM
     */
    exibirResultadoExplosao(data, incluirEstoque) {
        const container = $('#resultado-explosao');
        container.empty();

        if (incluirEstoque) {
            // Exibir com análise de estoque
            const viabilidade = data.viabilidade;
            const classViabilidade = viabilidade.pode_produzir ? '' : 'com-bloqueio';

            container.append(`
                <div class="card card-viabilidade ${classViabilidade} mb-3">
                    <div class="card-body">
                        <h5>Viabilidade de Produção</h5>
                        <p class="mb-2">
                            <strong>Pode produzir:</strong>
                            ${viabilidade.pode_produzir ? '<span class="text-success">✓ SIM</span>' : '<span class="text-danger">✗ NÃO</span>'}
                        </p>
                        <p class="mb-2">
                            <strong>Disponibilidade:</strong> ${viabilidade.percentual_disponibilidade}%
                        </p>
                        ${viabilidade.bloqueios.length > 0 ? `
                            <div class="alert alert-warning">
                                <strong>Bloqueios:</strong>
                                <ul class="mb-0">
                                    ${viabilidade.bloqueios.map(b => `<li>${b}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `);

            if (data.intermediarios_necessarios.length > 0) {
                container.append(`
                    <h6>Intermediários que Precisam Produção:</h6>
                    <ul class="list-group mb-3">
                        ${data.intermediarios_necessarios.map(inter => `
                            <li class="list-group-item">
                                <strong>${inter.cod_produto}</strong> - ${inter.nome_produto}
                                <br><small>Qtd necessária: ${inter.qtd_necessaria} | Falta: ${inter.necessidade_liquida.qtd_falta}</small>
                            </li>
                        `).join('')}
                    </ul>
                `);
            }
        } else {
            // Exibir apenas estrutura
            container.append(this.renderizarEstruturaExplosao(data.estrutura_completa, 0));
        }
    },

    /**
     * Renderiza estrutura explodida recursivamente
     */
    renderizarEstruturaExplosao(item, nivel) {
        const classe = `explosao-nivel-${nivel}`;
        const icone = this.getIconeTipo(item.tipo);

        let html = `<div class="${classe}">
            ${icone} <strong>${item.cod_produto}</strong> - ${item.nome_produto}
            <span class="badge-quantidade">${item.qtd_necessaria}</span>
        </div>`;

        if (item.componentes && item.componentes.length > 0) {
            item.componentes.forEach(comp => {
                html += this.renderizarEstruturaExplosao(comp, nivel + 1);
            });
        }

        return html;
    },

    /**
     * Valida estrutura BOM
     */
    async validarEstrutura() {
        try {
            const response = await fetch(`/manufatura/api/lista-materiais/validar/${this.produtoAtual}`);
            const data = await response.json();

            if (data.sucesso) {
                this.exibirResultadoValidacao(data);
            } else {
                toastr.error(data.erro || 'Erro ao validar estrutura');
            }
        } catch (error) {
            console.error('Erro ao validar estrutura:', error);
            toastr.error('Erro ao validar estrutura');
        }
    },

    /**
     * Exibe resultado da validação
     */
    exibirResultadoValidacao(data) {
        const container = $('#conteudo-validacao');
        container.empty();

        const classeStatus = data.valido ? 'success' : 'danger';
        const textoStatus = data.valido ? '✓ Estrutura Válida' : '✗ Estrutura Inválida';

        container.append(`
            <div class="alert alert-${classeStatus}">
                <h5>${textoStatus}</h5>
            </div>
        `);

        if (data.erros && data.erros.length > 0) {
            container.append(`
                <div class="alert alert-danger alert-validacao">
                    <strong>Erros Encontrados:</strong>
                    <ul>${data.erros.map(e => `<li>${e}</li>`).join('')}</ul>
                </div>
            `);
        }

        if (data.avisos && data.avisos.length > 0) {
            container.append(`
                <div class="alert alert-warning alert-validacao">
                    <strong>Avisos:</strong>
                    <ul>${data.avisos.map(a => `<li>${a}</li>`).join('')}</ul>
                </div>
            `);
        }

        if (data.valido && (!data.erros || data.erros.length === 0) && (!data.avisos || data.avisos.length === 0)) {
            container.append(`
                <p class="text-muted">Nenhum problema encontrado na estrutura.</p>
            `);
        }

        const modal = new bootstrap.Modal(document.getElementById('modalValidacao'));
        modal.show();
    },

    /**
     * Retorna ícone por tipo de produto
     */
    getIconeTipo(tipo) {
        const icones = {
            'ACABADO': '<i class="fas fa-cube text-success"></i>',
            'INTERMEDIARIO': '<i class="fas fa-cog text-warning"></i>',
            'COMPONENTE': '<i class="fas fa-leaf text-primary"></i>',
            'DESCONHECIDO': '<i class="fas fa-question text-muted"></i>',
            'ERRO': '<i class="fas fa-exclamation-triangle text-danger"></i>'
        };
        return icones[tipo] || icones['DESCONHECIDO'];
    }
};

// Inicializar quando DOM estiver pronto
$(document).ready(() => {
    ListaMateriais.init();
});

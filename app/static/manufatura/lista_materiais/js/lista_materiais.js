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
        // Busca de produtos
        $('#btn-buscar-produto').on('click', () => this.buscarProdutos());
        $('#input-busca-produto').on('keypress', (e) => {
            if (e.which === 13) this.buscarProdutos();
        });
        $('#btn-listar-todos').on('click', () => this.listarTodosProdutos());

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
        try {
            const response = await fetch('/manufatura/api/lista-materiais/produtos-produzidos');
            const data = await response.json();

            if (data.sucesso) {
                this.exibirProdutos(data.produtos);
            } else {
                toastr.error(data.erro || 'Erro ao listar produtos');
            }
        } catch (error) {
            console.error('Erro ao listar produtos:', error);
            toastr.error('Erro ao listar produtos');
        }
    },

    /**
     * Exibe lista de produtos
     */
    exibirProdutos(produtos) {
        const tbody = $('#tbody-produtos');
        tbody.empty();

        if (produtos.length === 0) {
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
            const iconeTipo = this.getIconeTipo(produto.tipo);
            const badgeEstrutura = produto.tem_estrutura
                ? '<span class="badge badge-tem-estrutura">Tem Estrutura</span>'
                : '<span class="badge badge-sem-estrutura">Sem Estrutura</span>';

            tbody.append(`
                <tr data-cod-produto="${produto.cod_produto}">
                    <td><strong>${produto.cod_produto}</strong></td>
                    <td>${produto.nome_produto}</td>
                    <td>${iconeTipo} ${produto.tipo}</td>
                    <td>${badgeEstrutura}</td>
                    <td>
                        <button class="btn btn-sm btn-primary btn-visualizar-estrutura"
                                data-cod="${produto.cod_produto}">
                            <i class="fas fa-eye"></i> Ver Estrutura
                        </button>
                    </td>
                </tr>
            `);
        });

        // Event listener para visualizar estrutura
        $('.btn-visualizar-estrutura').on('click', (e) => {
            const cod = $(e.currentTarget).data('cod');
            this.carregarEstrutura(cod);
        });

        $('#area-resultados').fadeIn();
    },

    /**
     * Carrega estrutura BOM de um produto
     */
    async carregarEstrutura(codProduto) {
        this.produtoAtual = codProduto;

        $('#loading-estrutura').show();
        $('#tree-bom, #empty-estrutura').hide();
        $('#area-estrutura').fadeIn();

        try {
            const response = await fetch(`/manufatura/api/lista-materiais/${codProduto}`);
            const data = await response.json();

            if (data.sucesso) {
                // Atualizar título
                const iconeTipo = this.getIconeTipo(data.produto.tipo);
                $('#titulo-produto-estrutura').html(`${iconeTipo} ${data.produto.cod_produto} - ${data.produto.nome_produto}`);
                $('#subtitulo-produto-estrutura').text(`Tipo: ${data.produto.tipo} | Total de componentes: ${data.total_componentes}`);

                if (data.componentes.length === 0) {
                    $('#empty-estrutura').show();
                } else {
                    this.renderizarArvore(data);
                }
            } else {
                toastr.error(data.erro || 'Erro ao carregar estrutura');
            }
        } catch (error) {
            console.error('Erro ao carregar estrutura:', error);
            toastr.error('Erro ao carregar estrutura');
        } finally {
            $('#loading-estrutura').hide();
        }
    },

    /**
     * Renderiza árvore BOM usando jsTree
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

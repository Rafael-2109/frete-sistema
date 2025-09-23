/**
 * 🎯 MODAL DE SEPARAÇÕES
 * Gerencia o modal de visualização de separações com paginação e totalizadores
 */

class ModalSeparacoes {
    constructor() {
        this.modalElement = null;
        this.modal = null;
        this.separacoes = [];
        this.paginaAtual = 1;
        this.separacoesPorPagina = 5;
        this.init();
    }

    init() {
        this.modalElement = document.getElementById('modalSeparacoes');
        if (this.modalElement) {
            this.modal = new bootstrap.Modal(this.modalElement);
        }
        console.log('✅ Modal de Separações inicializado');
    }

    async abrir(numPedido) {
        console.log(`📦 Abrindo modal de separações para pedido ${numPedido}`);

        // Atualizar número do pedido no título
        document.getElementById('modal-pedido-numero').textContent = numPedido;

        // Mostrar loading
        document.getElementById('modal-separacoes-loading').style.display = 'block';
        document.getElementById('modal-separacoes-content').style.display = 'none';

        // Abrir modal
        this.modal.show();

        try {
            // Carregar separações
            await this.carregarSeparacoes(numPedido);
        } catch (error) {
            console.error('❌ Erro ao carregar separações:', error);
            this.mostrarErro('Erro ao carregar separações. Tente novamente.');
        }
    }

    async carregarSeparacoes(numPedido) {
        try {
            const response = await fetch(`/carteira/api/pedido/${numPedido}/separacoes-completas`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar separações');
            }

            this.separacoes = data.separacoes || [];
            this.paginaAtual = 1;

            // Ocultar loading e mostrar conteúdo
            document.getElementById('modal-separacoes-loading').style.display = 'none';
            document.getElementById('modal-separacoes-content').style.display = 'block';

            // Renderizar separações
            this.renderizarSeparacoes();

        } catch (error) {
            throw error;
        }
    }

    renderizarSeparacoes() {
        const container = document.getElementById('modal-separacoes-content');

        console.log(`🎨 Renderizando ${this.separacoes.length} separações`);
        console.log('📦 Dados das separações:', this.separacoes);

        if (this.separacoes.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info text-center">
                    <i class="fas fa-info-circle me-2"></i>
                    Nenhuma separação encontrada para este pedido.
                </div>
            `;
            return;
        }

        // Calcular totais gerais
        const totaisGerais = this.calcularTotaisGerais();

        // Calcular separações da página atual
        const inicio = (this.paginaAtual - 1) * this.separacoesPorPagina;
        const fim = inicio + this.separacoesPorPagina;
        const separacoesPagina = this.separacoes.slice(inicio, fim);

        let html = `
            <!-- Totalizadores Gerais -->
            <div class="card mb-3 border-primary">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0">
                        <i class="fas fa-calculator me-2"></i>
                        Totais de Todas as Separações (${this.separacoes.length} separações)
                    </h6>
                </div>
                <div class="card-body">
                    <div class="row text-center">
                        <div class="col-md-4">
                            <h5 class="text-success">${this.formatarMoeda(totaisGerais.valor)}</h5>
                            <small class="text-muted">Valor Total</small>
                        </div>
                        <div class="col-md-4">
                            <h5 class="text-info">${this.formatarPeso(totaisGerais.peso)}</h5>
                            <small class="text-muted">Peso Total</small>
                        </div>
                        <div class="col-md-4">
                            <h5 class="text-warning">${this.formatarPallet(totaisGerais.pallet)}</h5>
                            <small class="text-muted">Pallets Total</small>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Paginação Superior -->
            ${this.renderizarPaginacao()}

            <!-- Separações da Página -->
            <div class="separacoes-lista">
        `;

        // Renderizar cada separação
        separacoesPagina.forEach((separacao, index) => {
            console.log(`🔍 Separação ${index + 1}:`, {
                lote_id: separacao.separacao_lote_id,
                protocolo: separacao.protocolo,
                status: separacao.status
            });
            html += this.renderizarSeparacao(separacao, inicio + index + 1);
        });

        html += `
            </div>

            <!-- Paginação Inferior -->
            ${this.renderizarPaginacao()}
        `;

        container.innerHTML = html;
    }

    renderizarSeparacao(separacao, numero) {
        const statusClass = this.getStatusClass(separacao.status);
        const statusBadge = this.getStatusBadge(separacao.status);

        let html = `
            <div class="card mb-3 border-${statusClass}">
                <div class="card-header bg-${statusClass} bg-opacity-10">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-box me-2"></i>
                            Separação #${numero} - ${separacao.separacao_lote_id}
                        </h6>
                        ${statusBadge}
                    </div>
                </div>
                <div class="card-body">
                    <!-- Informações Gerais -->
                    <div class="row mb-3">
                        <div class="col-md-3">
                            <strong>Data Expedição:</strong><br>
                            ${this.formatarData(separacao.expedicao)}
                        </div>
                        <div class="col-md-3">
                            <strong>Agendamento:</strong><br>
                            ${separacao.agendamento ? this.formatarData(separacao.agendamento) : '-'}
                        </div>
                        <div class="col-md-3">
                            <strong>Protocolo:</strong><br>
                            ${separacao.protocolo || '-'}
                        </div>
                        <div class="col-md-3">
                            <strong>Status Calculado:</strong><br>
                            ${statusBadge}
                        </div>
                    </div>
        `;

        // Se status for COTADO, mostrar informações do embarque
        if (separacao.status === 'COTADO' && separacao.embarque) {
            html += `
                    <div class="alert alert-info mb-3">
                        <h6 class="alert-heading">
                            <i class="fas fa-truck me-2"></i>
                            Informações do Embarque
                        </h6>
                        <div class="row">
                            <div class="col-md-4">
                                <strong>Número:</strong> ${separacao.embarque.numero || '-'}
                            </div>
                            <div class="col-md-4">
                                <strong>Transportadora:</strong> ${separacao.embarque.transportadora || '-'}
                            </div>
                            <div class="col-md-4">
                                <strong>Previsão:</strong> ${separacao.embarque.data_prevista_embarque ? this.formatarData(separacao.embarque.data_prevista_embarque) : '-'}
                            </div>
                        </div>
                    </div>
            `;
        }

        html += `
                    <!-- Produtos -->
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="mb-0">Produtos (${separacao.produtos.length})</h6>
                        ${separacao.produtos.length > 5 ? `
                            <button class="btn btn-link btn-sm p-0" onclick="window.modalSeparacoes.toggleProdutosSeparacao('${separacao.separacao_lote_id}')">
                                <span id="btn-modal-toggle-${separacao.separacao_lote_id}">Ver todos</span>
                            </button>
                        ` : ''}
                    </div>
                    <div class="table-responsive" id="produtos-tabela-${separacao.separacao_lote_id}">
                        <table class="table table-sm table-hover">
                            <thead class="table-light">
                                <tr>
                                    <th>Código</th>
                                    <th>Produto</th>
                                    <th class="text-end">Quantidade</th>
                                    <th class="text-end">Valor</th>
                                    <th class="text-end">Peso</th>
                                    <th class="text-end">Pallet</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        // Renderizar produtos (mostrar apenas 5 inicialmente se tiver mais)
        const produtosVisiveis = separacao.produtos.length > 5 ? 5 : separacao.produtos.length;
        separacao.produtos.slice(0, produtosVisiveis).forEach(produto => {
            html += `
                                <tr class="produto-visivel-${separacao.separacao_lote_id}">
                                    <td>${produto.cod_produto}</td>
                                    <td>${produto.nome_produto || '-'}</td>
                                    <td class="text-end">${this.formatarQuantidade(produto.qtd_saldo)}</td>
                                    <td class="text-end">${this.formatarMoeda(produto.valor_saldo)}</td>
                                    <td class="text-end">${this.formatarPeso(produto.peso)}</td>
                                    <td class="text-end">${this.formatarPallet(produto.pallet)}</td>
                                </tr>
            `;
        });

        // Renderizar produtos ocultos
        if (separacao.produtos.length > 5) {
            separacao.produtos.slice(5).forEach(produto => {
                html += `
                                <tr class="produto-oculto-${separacao.separacao_lote_id}" style="display: none;">
                                    <td>${produto.cod_produto}</td>
                                    <td>${produto.nome_produto || '-'}</td>
                                    <td class="text-end">${this.formatarQuantidade(produto.qtd_saldo)}</td>
                                    <td class="text-end">${this.formatarMoeda(produto.valor_saldo)}</td>
                                    <td class="text-end">${this.formatarPeso(produto.peso)}</td>
                                    <td class="text-end">${this.formatarPallet(produto.pallet)}</td>
                                </tr>
                `;
            });
        }

        // Totais da separação
        html += `
                            </tbody>
                            <tfoot class="table-secondary">
                                <tr>
                                    <th colspan="2">Totais</th>
                                    <th class="text-end">${separacao.produtos.length} itens</th>
                                    <th class="text-end">${this.formatarMoeda(separacao.valor_total)}</th>
                                    <th class="text-end">${this.formatarPeso(separacao.peso_total)}</th>
                                    <th class="text-end">${this.formatarPallet(separacao.pallet_total)}</th>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                    
                    <!-- Botões do Portal -->
                    <div class="mt-3">
                        <div class="alert alert-light border">
                            <h6 class="alert-heading mb-2">
                                <i class="fas fa-globe me-1"></i> Portal do Cliente
                            </h6>
                            <div class="d-flex gap-2 flex-wrap">
                                <button class="btn btn-success btn-sm" 
                                        data-lote="${separacao.separacao_lote_id}"
                                        data-agendamento="${separacao.agendamento || ''}"
                                        onclick="window.PortalAgendamento.agendarNoPortal(this.dataset.lote, this.dataset.agendamento)">
                                    <i class="fas fa-calendar-plus me-1"></i> Agendar no Portal
                                </button>
                                <button class="btn btn-info btn-sm"
                                        data-lote="${separacao.separacao_lote_id}"
                                        onclick="window.PortalAgendamento.verificarPortal(this.dataset.lote)">
                                    <i class="fas fa-search me-1"></i> Status
                                </button>
                                ${separacao.protocolo ? `
                                    <button class="btn btn-warning btn-sm"
                                            data-lote="${separacao.separacao_lote_id}"
                                            data-protocolo="${separacao.protocolo}"
                                            onclick="window.PortalAgendamento.verificarProtocoloNoPortal(this.dataset.lote, this.dataset.protocolo)">
                                        <i class="fas fa-sync me-1"></i> Verificar Protocolo
                                    </button>
                                    <span class="badge bg-success align-self-center ms-auto">
                                        <i class="fas fa-check-circle me-1"></i> 
                                        Protocolo: ${separacao.protocolo}
                                    </span>
                                ` : `
                                    <span class="badge bg-secondary align-self-center ms-auto">
                                        <i class="fas fa-clock me-1"></i> 
                                        Aguardando agendamento
                                    </span>
                                `}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        return html;
    }

    renderizarPaginacao() {
        const totalPaginas = Math.ceil(this.separacoes.length / this.separacoesPorPagina);

        if (totalPaginas <= 1) return '';

        let html = `
            <nav aria-label="Navegação de separações">
                <ul class="pagination justify-content-center">
                    <li class="page-item ${this.paginaAtual === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="#" onclick="window.modalSeparacoes.irParaPagina(${this.paginaAtual - 1}); return false;">
                            <i class="fas fa-chevron-left"></i>
                        </a>
                    </li>
        `;

        // Páginas
        for (let i = 1; i <= totalPaginas; i++) {
            html += `
                    <li class="page-item ${i === this.paginaAtual ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="window.modalSeparacoes.irParaPagina(${i}); return false;">${i}</a>
                    </li>
            `;
        }

        html += `
                    <li class="page-item ${this.paginaAtual === totalPaginas ? 'disabled' : ''}">
                        <a class="page-link" href="#" onclick="window.modalSeparacoes.irParaPagina(${this.paginaAtual + 1}); return false;">
                            <i class="fas fa-chevron-right"></i>
                        </a>
                    </li>
                </ul>
            </nav>
        `;

        return html;
    }

    irParaPagina(pagina) {
        const totalPaginas = Math.ceil(this.separacoes.length / this.separacoesPorPagina);

        if (pagina < 1) pagina = 1;
        if (pagina > totalPaginas) pagina = totalPaginas;

        this.paginaAtual = pagina;
        this.renderizarSeparacoes();
    }

    calcularTotaisGerais() {
        return this.separacoes.reduce((totais, sep) => {
            totais.valor += sep.valor_total || 0;
            totais.peso += sep.peso_total || 0;
            totais.pallet += sep.pallet_total || 0;
            return totais;
        }, { valor: 0, peso: 0, pallet: 0 });
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

    getStatusBadge(status) {
        const statusClass = this.getStatusClass(status);
        return `<span class="badge bg-${statusClass}">${status}</span>`;
    }

    mostrarErro(mensagem) {
        const container = document.getElementById('modal-separacoes-content');
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${mensagem}
            </div>
        `;
        document.getElementById('modal-separacoes-loading').style.display = 'none';
        container.style.display = 'block';
    }

    // Formatadores
    formatarMoeda(valor) {
        return window.Formatters.moeda(valor);
    }

    formatarPeso(peso) {
        return window.Formatters.peso(peso);
    }

    formatarPallet(pallet) {
        return window.Formatters.pallet(pallet);
    }

    formatarQuantidade(qtd) {
        return window.Formatters.quantidade(qtd);
    }

    formatarData(data) {
        return window.Formatters.data(data) || '-';
    }

    toggleProdutosSeparacao(loteId) {
        const produtosOcultos = document.querySelectorAll(`.produto-oculto-${loteId}`);
        const btnToggle = document.getElementById(`btn-modal-toggle-${loteId}`);

        if (produtosOcultos.length > 0 && btnToggle) {
            const isHidden = produtosOcultos[0].style.display === 'none';

            produtosOcultos.forEach(tr => {
                tr.style.display = isHidden ? '' : 'none';
            });

            btnToggle.textContent = isHidden ? 'Ver menos' : 'Ver todos';
        }
    }



    // Delegar para módulo centralizado
    async verificarPortal(loteId) {
        return window.PortalAgendamento.verificarPortal(loteId);
    }


    // Delegar para módulo centralizado
    abrirModalDePara(produtosSemDePara) {
        return window.PortalAgendamento.abrirModalDePara(produtosSemDePara);
    }

    // FUNÇÃO ORIGINAL REMOVIDA - implementação em portal-agendamento.js
    abrirModalDePara_OLD(produtosSemDePara) {
        if (!produtosSemDePara || produtosSemDePara.length === 0) {
            return;
        }

        const produto = produtosSemDePara[0];

        Swal.fire({
            title: 'Cadastrar De-Para',
            html: `
                <form id="formDePara">
                    <div class="mb-3">
                        <label class="form-label">Nosso Código:</label>
                        <input type="text" class="form-control" value="${produto.codigo}" readonly>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Nossa Descrição:</label>
                        <input type="text" class="form-control" value="${produto.descricao}" readonly>
                    </div>
                    <hr>
                    <div class="mb-3">
                        <label class="form-label">Código Atacadão:</label>
                        <input type="text" id="codigo_atacadao" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Descrição Atacadão:</label>
                        <input type="text" id="descricao_atacadao" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Fator de Conversão:</label>
                        <input type="number" id="fator_conversao" class="form-control" value="1.0" step="0.0001" min="0.0001">
                    </div>
                </form>
            `,
            showCancelButton: true,
            confirmButtonText: 'Salvar',
            cancelButtonText: 'Cancelar',
            preConfirm: () => {
                const codigo_atacadao = document.getElementById('codigo_atacadao').value;
                const descricao_atacadao = document.getElementById('descricao_atacadao').value;
                const fator_conversao = document.getElementById('fator_conversao').value;

                if (!codigo_atacadao || !descricao_atacadao) {
                    Swal.showValidationMessage('Preencha todos os campos obrigatórios');
                    return false;
                }

                return {
                    codigo_nosso: produto.codigo,
                    codigo_atacadao: codigo_atacadao,
                    descricao_atacadao: descricao_atacadao,
                    fator_conversao: parseFloat(fator_conversao)
                };
            }
        }).then((result) => {
            if (result.isConfirmed) {
                // Salvar De-Para via API
                this.salvarDePara(result.value);
            }
        });
    }

    // Função para salvar De-Para
    async salvarDePara(dados) {
        try {
            const response = await fetch('/portal/atacadao/depara/api/criar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                },
                body: JSON.stringify(dados)
            });

            const result = await response.json();

            if (result.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'De-Para Cadastrado!',
                    text: 'Mapeamento criado com sucesso',
                    confirmButtonText: 'OK'
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: result.message || 'Erro ao criar mapeamento',
                    confirmButtonText: 'OK'
                });
            }
        } catch (error) {
            console.error('Erro ao salvar De-Para:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao salvar mapeamento',
                confirmButtonText: 'OK'
            });
        }
    }

    criarModalComparacao() {
        // Remover modal existente se houver
        const existingModal = document.getElementById('modalComparacaoPortal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.id = 'modalComparacaoPortal';
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-exchange-alt"></i> Comparação: Separação × Portal
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="comparacao-loading" class="text-center p-4">
                            <i class="fas fa-spinner fa-spin fa-2x"></i>
                            <p class="mt-2">Carregando dados do portal...</p>
                        </div>
                        <div id="comparacao-content" style="display: none;">
                            <!-- Conteúdo será inserido aqui -->
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" onclick="window.modalSeparacoes.extrairConfirmacoes()">
                            <i class="fas fa-sync me-1"></i> Extrair Confirmações
                        </button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Mostrar modal
        const modalElement = new bootstrap.Modal(modal);
        modalElement.show();
    }

    async carregarDadosComparacao(loteId) {
        try {
            // Buscar dados da separação
            const response = await fetch(`/portal/api/comparar-portal/${loteId}`);
            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Erro ao carregar dados');
            }

            // Renderizar comparação
            this.renderizarComparacao(data);

        } catch (error) {
            console.error('Erro ao carregar comparação:', error);
            document.getElementById('comparacao-content').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> 
                    ${error.message || 'Erro ao carregar dados do portal'}
                </div>
            `;
            document.getElementById('comparacao-loading').style.display = 'none';
            document.getElementById('comparacao-content').style.display = 'block';
        }
    }

    renderizarComparacao(data) {
        const content = document.getElementById('comparacao-content');

        let html = `
            <div class="row">
                <!-- Lado Esquerdo: Separação -->
                <div class="col-md-6">
                    <div class="card border-primary">
                        <div class="card-header bg-primary text-white">
                            <h6 class="mb-0">
                                <i class="fas fa-boxes"></i> Separação (Sistema)
                            </h6>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Código</th>
                                        <th>Produto</th>
                                        <th>Qtd</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.separacao.produtos.map(p => `
                                        <tr>
                                            <td>${p.cod_produto}</td>
                                            <td>${p.nome_produto}</td>
                                            <td>${p.quantidade}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Lado Direito: Portal -->
                <div class="col-md-6">
                    <div class="card border-success">
                        <div class="card-header bg-success text-white">
                            <h6 class="mb-0">
                                <i class="fas fa-globe"></i> Portal (${data.portal || 'Atacadão'})
                            </h6>
                        </div>
                        <div class="card-body">
                            ${data.portal_data ? `
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Código</th>
                                            <th>Mercadoria</th>
                                            <th>Qtd</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.portal_data.produtos.map(p => `
                                            <tr>
                                                <td>${p.codigo}</td>
                                                <td>${p.mercadoria}</td>
                                                <td>${p.quantidade}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                                
                                ${data.portal_data.protocolo ? `
                                    <div class="alert alert-success mt-3">
                                        <i class="fas fa-check-circle"></i>
                                        <strong>Protocolo:</strong> ${data.portal_data.protocolo}
                                    </div>
                                ` : ''}
                            ` : `
                                <div class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle"></i>
                                    Nenhum agendamento encontrado no portal
                                </div>
                            `}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Divergências -->
            ${data.divergencias && data.divergencias.length > 0 ? `
                <div class="alert alert-warning mt-3">
                    <h6><i class="fas fa-exclamation-triangle"></i> Divergências Encontradas:</h6>
                    <ul class="mb-0">
                        ${data.divergencias.map(d => `<li>${d}</li>`).join('')}
                    </ul>
                </div>
            ` : `
                <div class="alert alert-success mt-3">
                    <i class="fas fa-check-circle"></i> 
                    Todos os produtos conferem!
                </div>
            `}
        `;

        content.innerHTML = html;
        document.getElementById('comparacao-loading').style.display = 'none';
        document.getElementById('comparacao-content').style.display = 'block';
    }

    async extrairConfirmacoes() {
        Swal.fire({
            title: 'Extraindo confirmações...',
            text: 'Consultando o portal do cliente',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        try {
            const response = await fetch('/portal/api/extrair-confirmacoes');
            const data = await response.json();

            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Confirmações Extraídas',
                    text: `${data.confirmacoes} confirmações processadas`,
                    confirmButtonText: 'OK'
                });
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: error.message || 'Erro ao extrair confirmações',
                confirmButtonText: 'OK'
            });
        }
    }

    // Delegar para módulo centralizado
    async verificarProtocoloNoPortal(loteId, protocolo) {
        return window.PortalAgendamento.verificarProtocoloNoPortal(loteId, protocolo);
    }

    // FUNÇÃO ORIGINAL REMOVIDA - implementação em portal-agendamento.js
    async verificarProtocoloNoPortal_OLD(loteId, protocolo) {
        console.log(`🔍 Verificando protocolo ${protocolo} no portal`);

        // Mostrar loading
        Swal.fire({
            title: 'Verificando Protocolo...',
            text: `Consultando protocolo ${protocolo} no Portal Atacadão`,
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        try {
            // Fazer chamada para verificar protocolo
            const response = await fetch('/carteira/api/verificar-protocolo-portal', {
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
                // Montar HTML de comparação com tabela unificada
                let htmlComparacao = `
                    <style>
                        .table-comparacao {
                            font-size: 0.85rem;
                        }
                        .table-comparacao th {
                            font-size: 0.9rem;
                            font-weight: 600;
                        }
                        .linha-divergencia {
                            background-color: #ffebee !important;
                        }
                        .texto-divergencia {
                            color: #c62828;
                            font-weight: 600;
                        }
                        .badge-diferenca {
                            font-size: 0.75rem;
                        }
                    </style>
                    
                    <div class="container-fluid">
                        <!-- Status do Agendamento -->
                        <div class="row mb-3">
                            <div class="col-12">
                                <div class="alert ${data.agendamento_confirmado ? 'alert-success' : 'alert-warning'}">
                                    <h6 class="mb-2">
                                        <i class="fas ${data.agendamento_confirmado ? 'fa-check-circle' : 'fa-clock'}"></i>
                                        Status: ${data.agendamento_confirmado ? 'Aguardando check-in' : 'Aguardando aprovação'}
                                    </h6>
                                    ${data.data_aprovada ? `
                                        <p class="mb-1 small"><strong>Entrega aprovada para:</strong> ${this.formatarData(data.data_aprovada)}</p>
                                    ` : ''}
                                    <p class="mb-0 small"><strong>Protocolo:</strong> ${protocolo}</p>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Tabela Unificada -->
                        <div class="row">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header bg-primary text-white py-2">
                                        <h6 class="mb-0">
                                            <i class="fas fa-exchange-alt"></i> Comparação de Produtos
                                        </h6>
                                    </div>
                                    <div class="card-body p-2">
                                        ${data.produtos_unificados && data.produtos_unificados.length > 0 ? `
                                            <div class="table-responsive">
                                                <table class="table table-sm table-hover table-comparacao mb-0">
                                                    <thead class="table-light">
                                                        <tr>
                                                            <th width="15%">Código</th>
                                                            <th width="40%">Descrição</th>
                                                            <th width="12%" class="text-center">Qtd Separação</th>
                                                            <th width="12%" class="text-center">Qtd Agendamento</th>
                                                            <th width="12%" class="text-center">Diferença</th>
                                                            <th width="9%" class="text-center">Status</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        ${data.produtos_unificados.map(p => `
                                                            <tr class="${p.tem_divergencia ? 'linha-divergencia' : ''}">
                                                                <td><small>${p.codigo_nosso}</small></td>
                                                                <td><small>${p.descricao_nossa}</small></td>
                                                                <td class="text-center">
                                                                    <span class="${p.tem_divergencia && p.qtd_separacao !== p.qtd_agendamento ? 'texto-divergencia' : ''}">
                                                                        ${p.qtd_separacao.toFixed(2)}
                                                                    </span>
                                                                </td>
                                                                <td class="text-center">
                                                                    <span class="${p.tem_divergencia && p.qtd_separacao !== p.qtd_agendamento ? 'texto-divergencia' : ''}">
                                                                        ${p.qtd_agendamento.toFixed(2)}
                                                                    </span>
                                                                </td>
                                                                <td class="text-center">
                                                                    ${p.diferenca !== 0 ? `
                                                                        <span class="badge ${p.diferenca > 0 ? 'bg-warning' : 'bg-danger'} badge-diferenca">
                                                                            ${p.diferenca > 0 ? '+' : ''}${p.diferenca.toFixed(2)}
                                                                        </span>
                                                                    ` : `
                                                                        <span class="text-muted">0.00</span>
                                                                    `}
                                                                </td>
                                                                <td class="text-center">
                                                                    ${p.tem_divergencia ?
                        '<i class="fas fa-exclamation-triangle text-danger"></i>' :
                        '<i class="fas fa-check-circle text-success"></i>'
                    }
                                                                </td>
                                                            </tr>
                                                        `).join('')}
                                                    </tbody>
                                                    <tfoot class="table-secondary">
                                                        <tr>
                                                            <th colspan="2">Total</th>
                                                            <th class="text-center">
                                                                ${data.produtos_unificados.reduce((sum, p) => sum + p.qtd_separacao, 0).toFixed(2)}
                                                            </th>
                                                            <th class="text-center">
                                                                ${data.produtos_unificados.reduce((sum, p) => sum + p.qtd_agendamento, 0).toFixed(2)}
                                                            </th>
                                                            <th class="text-center">
                                                                ${data.produtos_unificados.reduce((sum, p) => sum + p.diferenca, 0).toFixed(2)}
                                                            </th>
                                                            <th></th>
                                                        </tr>
                                                    </tfoot>
                                                </table>
                                            </div>
                                        ` : `
                                            <p class="text-muted text-center py-3">Nenhum produto encontrado</p>
                                        `}
                                        
                                        <!-- Produtos não mapeados (se houver) -->
                                        ${data.produtos_nao_mapeados && data.produtos_nao_mapeados.length > 0 ? `
                                            <div class="alert alert-warning mt-3 mb-0">
                                                <h6 class="alert-heading">
                                                    <i class="fas fa-exclamation-triangle"></i> 
                                                    Produtos sem DE-PARA configurado:
                                                </h6>
                                                <small>
                                                    <ul class="mb-0">
                                                        ${data.produtos_nao_mapeados.map(p => `
                                                            <li>Código Atacadão: ${p.codigo_atacadao} - ${p.descricao} (Qtd: ${p.quantidade})</li>
                                                        `).join('')}
                                                    </ul>
                                                </small>
                                            </div>
                                        ` : ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Resumo de divergências -->
                        ${data.divergencias && data.divergencias.length > 0 ? `
                            <div class="row mt-2">
                                <div class="col-12">
                                    <div class="alert alert-info py-2 mb-0">
                                        <small>
                                            <strong>Resumo:</strong> ${data.divergencias.join(' | ')}
                                        </small>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `;

                // Mostrar resultado
                Swal.fire({
                    title: `Protocolo ${protocolo}`,
                    html: htmlComparacao,
                    width: '1100px',
                    showCancelButton: false,
                    confirmButtonText: data.agendamento_confirmado ? 'OK' : 'Atualizar Status',
                    confirmButtonColor: data.agendamento_confirmado ? '#28a745' : '#ffc107'
                }).then((result) => {
                    if (result.isConfirmed && !data.agendamento_confirmado) {
                        // Atualizar status da separação
                        this.atualizarStatusSeparacao(loteId, data.data_aprovada, data.agendamento_confirmado);
                    }
                });

            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: data.message || 'Erro ao verificar protocolo',
                    confirmButtonText: 'OK'
                });
            }
        } catch (error) {
            console.error('Erro ao verificar protocolo:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao comunicar com o servidor',
                confirmButtonText: 'OK'
            });
        }
    }

    async atualizarStatusSeparacao(loteId, dataAprovada, confirmado) {
        try {
            const response = await fetch('/carteira/api/atualizar-status-separacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                },
                body: JSON.stringify({
                    lote_id: loteId,
                    agendamento: dataAprovada,
                    agendamento_confirmado: confirmado
                })
            });

            const data = await response.json();

            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Status Atualizado',
                    text: 'Dados da separação atualizados com sucesso',
                    confirmButtonText: 'OK'
                }).then(() => {
                    // Recarregar separações
                    const numPedido = document.getElementById('modal-pedido-numero').textContent;
                    this.carregarSeparacoes(numPedido);
                });
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: error.message || 'Erro ao atualizar status',
                confirmButtonText: 'OK'
            });
        }
    }
}

// Função global para abrir o modal
window.abrirModalSeparacoes = function (numPedido) {
    if (!window.modalSeparacoes) {
        window.modalSeparacoes = new ModalSeparacoes();
    }
    window.modalSeparacoes.abrir(numPedido);
};

// Disponibilizar globalmente
window.ModalSeparacoes = ModalSeparacoes;
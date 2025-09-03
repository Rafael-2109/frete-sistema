/**
 * 🎯 DROPDOWN SEPARAÇÕES REDESENHADO POR LOTE
 * Cada separacao_lote_id = 1 card com header + dados + botões
 */

class DropdownSeparacoes {
    constructor() {
        this.cacheSeparacoes = new Map();
        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log('✅ Dropdown Separações redesenhado inicializado');
    }

    setupEventListeners() {
        // Dropdown de separações (Bootstrap 5)
        document.addEventListener('shown.bs.dropdown', (e) => {
            if (e.target.classList.contains('dropdown-separacoes')) {
                this.onDropdownAberto(e.target);
                this.ajustarPosicionamentoDropdown(e.target);
            }
        });

        // Reposicionar dropdowns abertos quando janela redimensiona
        window.addEventListener('resize', () => {
            const dropdownsAbertos = document.querySelectorAll('.dropdown-menu.show');
            dropdownsAbertos.forEach(dropdown => {
                const button = dropdown.previousElementSibling;
                if (button && button.classList.contains('dropdown-separacoes')) {
                    this.ajustarPosicionamentoDropdown(button);
                }
            });
        });

        // Reset posicionamento quando dropdown fecha
        document.addEventListener('hidden.bs.dropdown', (e) => {
            if (e.target.classList.contains('dropdown-separacoes')) {
                const dropdownMenu = e.target.nextElementSibling;
                if (dropdownMenu) {
                    dropdownMenu.style.position = '';
                    dropdownMenu.style.left = '';
                    dropdownMenu.style.top = '';
                }
            }
        });
    }

    /**
     * 🎯 AJUSTAR POSICIONAMENTO DO DROPDOWN PARA EVITAR CLIPPING
     */
    ajustarPosicionamentoDropdown(button) {
        const dropdownMenu = button.nextElementSibling;
        if (!dropdownMenu || !dropdownMenu.classList.contains('dropdown-menu')) return;

        // Forçar posicionamento fixed e calcular posição
        const buttonRect = button.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;
        
        // Posicionar dropdown com prioridade para sobrepor regras CSS
        dropdownMenu.style.setProperty('position', 'fixed', 'important');
        dropdownMenu.style.setProperty('left', Math.min(buttonRect.left, viewportWidth - 420) + 'px', 'important');
        
        // Verificar se cabe abaixo ou deve abrir acima
        if (buttonRect.bottom + 500 > viewportHeight) {
            dropdownMenu.style.setProperty('top', Math.max(10, buttonRect.top - 500) + 'px', 'important');
        } else {
            dropdownMenu.style.setProperty('top', buttonRect.bottom + 'px', 'important');
        }
        
        dropdownMenu.style.zIndex = '1200';
    }

    async onDropdownAberto(button) {
        const numPedido = button.dataset.pedido;
        const dropdownContent = document.getElementById(`separacoes-content-${numPedido}`);
        
        if (!dropdownContent) return;

        // Se já carregou, não recarregar
        if (this.cacheSeparacoes.has(numPedido)) {
            return;
        }

        console.log(`🔄 Carregando separações do pedido ${numPedido}`);
        
        try {
            // Mostrar loading
            dropdownContent.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-spinner fa-spin me-2"></i>
                    Carregando separações...
                </div>
            `;

            // Fazer requisição para API
            const response = await fetch(`/carteira/api/pedido/${numPedido}/separacoes`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar separações');
            }

            // Armazenar no cache
            this.cacheSeparacoes.set(numPedido, data);

            // 🎯 RENDERIZAR POR LOTES (NOVO DESIGN)
            this.renderizarSeparacoesPorLote(dropdownContent, data);

            // Atualizar contador no botão (qtd de lotes únicos, não itens)
            const contador = button.querySelector('.contador-separacoes');
            if (contador) {
                const qtdLotes = Object.keys(this.agruparPorLote(data.separacoes)).length;
                contador.textContent = qtdLotes;
            }

        } catch (error) {
            console.error(`❌ Erro ao carregar separações:`, error);
            this.renderizarErro(dropdownContent, error.message);
        }
    }

    /**
     * 🎯 NOVO: Renderizar separações agrupadas por lote
     */
    renderizarSeparacoesPorLote(container, data) {
        if (!data.separacoes || data.separacoes.length === 0) {
            container.innerHTML = this.getTemplateSeparacoesVazias();
            return;
        }

        // 🎯 AGRUPAR POR separacao_lote_id
        const lotes = this.agruparPorLote(data.separacoes);
        
        let html = '<div class="separacoes-lotes">';
        
        // 📦 CRIAR CARD PARA CADA LOTE
        Object.keys(lotes).forEach(loteId => {
            const separacoesDoLote = lotes[loteId];
            html += this.criarCardLote(loteId, separacoesDoLote);
        });

        html += '</div>';
        
        // 📊 RESUMO GERAL
        html += this.criarResumoGeral(data);

        container.innerHTML = html;
    }

    /**
     * 🎯 NOVO: Agrupar separações por lote
     */
    agruparPorLote(separacoes) {
        const lotes = {};
        
        separacoes.forEach(sep => {
            const loteId = sep.separacao_lote_id;
            if (!lotes[loteId]) {
                lotes[loteId] = [];
            }
            lotes[loteId].push(sep);
        });
        
        return lotes;
    }

    /**
     * 🎯 NOVO: Criar card para um lote
     */
    criarCardLote(loteId, separacoes) {
        // Usar primeira separação para dados do lote
        const loteInfo = separacoes[0];
        const totalItens = separacoes.length;
        
        // Calcular totais do lote
        const totais = this.calcularTotaisLote(separacoes);
        
        // 🎯 BUSCAR DADOS DE EMBARQUE/TRANSPORTADORA
        const dadosEmbarque = this.extrairDadosEmbarque(loteInfo);
        const dadosTransportadora = this.extrairDadosTransportadora(loteInfo);

        return `
            <div class="card lote-card mb-3" data-lote-id="${loteId}">
                <!-- 🎯 HEADER COM TRANSPORTADORA + EMBARQUE + BOTÕES -->
                <div class="card-header d-flex justify-content-between align-items-center"
                     style="background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white;">
                    <div class="lote-header-info">
                        <h6 class="mb-0">
                            <i class="fas fa-box me-2"></i>
                            <strong>${loteId}</strong>
                        </h6>
                        <small class="d-block mt-1">
                            ${dadosTransportadora.texto}
                            ${dadosEmbarque.texto}
                        </small>
                    </div>
                    
                    <!-- 🎯 BOTÕES DE AÇÃO -->
                    <div class="lote-acoes">
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-light btn-sm" 
                                    onclick="editarSeparacao('${loteId}')"
                                    title="Editar separação">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-light btn-sm" 
                                    onclick="imprimirSeparacao('${loteId}')"
                                    title="Imprimir separação">
                                <i class="fas fa-print"></i>
                            </button>
                            <button class="btn btn-light btn-sm" 
                                    onclick="cancelarSeparacao('${loteId}')"
                                    title="Cancelar separação">
                                <i class="fas fa-times text-danger"></i>
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- 🎯 CORPO DO CARD COM DADOS E STATUS -->
                <div class="card-body p-3">
                    <div class="row">
                        <!-- STATUS -->
                        <div class="col-md-3">
                            <div class="status-info text-center">
                                <span class="badge bg-${loteInfo.status_class} fs-6">
                                    ${loteInfo.status}
                                </span>
                                <br><small class="text-muted mt-1">Status</small>
                            </div>
                        </div>
                        
                        <!-- TOTAIS -->
                        <div class="col-md-6">
                            <div class="totais-lote">
                                <div class="row text-center">
                                    <div class="col-3">
                                        <strong class="text-success">${this.formatarMoeda(totais.valor)}</strong>
                                        <br><small class="text-muted">Valor</small>
                                    </div>
                                    <div class="col-3">
                                        <strong class="text-primary">${this.formatarPeso(totais.peso)}</strong>
                                        <br><small class="text-muted">Peso</small>
                                    </div>
                                    <div class="col-3">
                                        <strong class="text-info">${this.formatarPallet(totais.pallet)}</strong>
                                        <br><small class="text-muted">Pallets</small>
                                    </div>
                                    <div class="col-3">
                                        <strong class="text-dark">${totalItens}</strong>
                                        <br><small class="text-muted">Itens</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- DATAS -->
                        <div class="col-md-3">
                            <div class="datas-lote">
                                ${loteInfo.expedicao ? `
                                    <small class="text-success">
                                        <i class="fas fa-calendar-alt me-1"></i>
                                        Expedição: ${loteInfo.expedicao}
                                    </small><br>
                                ` : ''}
                                ${loteInfo.agendamento ? `
                                    <small class="text-info">
                                        <i class="fas fa-calendar-check me-1"></i>
                                        Agendamento: ${loteInfo.agendamento}
                                    </small><br>
                                ` : ''}
                                <small class="text-muted">
                                    <i class="fas fa-clock me-1"></i>
                                    Criado: ${loteInfo.criado_em}
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 🎯 NOVO: Calcular totais de um lote
     */
    calcularTotaisLote(separacoes) {
        return separacoes.reduce((totais, sep) => {
            totais.valor += sep.valor_saldo || 0;
            totais.peso += sep.peso || 0;
            totais.pallet += sep.pallet || 0;
            return totais;
        }, { valor: 0, peso: 0, pallet: 0 });
    }

    /**
     * 🎯 NOVO: Extrair dados de embarque
     */
    extrairDadosEmbarque(loteInfo) {
        if (loteInfo.embarque && loteInfo.embarque.numero) {
            return {
                numero: loteInfo.embarque.numero,
                texto: `Embarque: ${loteInfo.embarque.numero}`
            };
        }
        return {
            numero: null,
            texto: ''
        };
    }

    /**
     * 🎯 NOVO: Extrair dados de transportadora
     */
    extrairDadosTransportadora(loteInfo) {
        if (loteInfo.transportadora && loteInfo.transportadora.nome_fantasia) {
            return {
                nome: loteInfo.transportadora.nome_fantasia,
                texto: `${loteInfo.transportadora.nome_fantasia} | `
            };
        }
        return {
            nome: null,
            texto: ''
        };
    }

    /**
     * 🎯 NOVO: Criar resumo geral
     */
    criarResumoGeral(data) {
        const lotes = this.agruparPorLote(data.separacoes);
        const totalLotes = Object.keys(lotes).length;
        
        // Contar lotes embarcados/pendentes
        let lotesEmbarcados = 0;
        let lotesPendentes = 0;
        
        Object.values(lotes).forEach(separacoesDoLote => {
            const primeiraSeperacao = separacoesDoLote[0];
            if (primeiraSeperacao.status === 'EMBARCADO') {
                lotesEmbarcados++;
            } else {
                lotesPendentes++;
            }
        });
        
        return `
            <div class="separacoes-resumo mt-3 pt-3 border-top">
                <div class="row text-center">
                    <div class="col-4">
                        <strong class="text-primary">${totalLotes}</strong>
                        <br><small class="text-muted">Total Lotes</small>
                    </div>
                    <div class="col-4">
                        <strong class="text-success">${lotesEmbarcados}</strong>
                        <br><small class="text-muted">Embarcados</small>
                    </div>
                    <div class="col-4">
                        <strong class="text-warning">${lotesPendentes}</strong>
                        <br><small class="text-muted">Pendentes</small>
                    </div>
                </div>
            </div>
        `;
    }

    getTemplateSeparacoesVazias() {
        return `
            <div class="text-center text-muted py-4">
                <i class="fas fa-inbox fa-2x mb-3"></i>
                <p class="mb-0"><strong>Nenhuma separação encontrada</strong></p>
                <small>Este pedido ainda não possui separações criadas.</small>
            </div>
        `;
    }

    renderizarErro(container, mensagem) {
        container.innerHTML = `
            <div class="alert alert-warning mb-0">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Erro ao carregar separações</strong>
                <p class="mb-2">${mensagem}</p>
                <button class="btn btn-sm btn-outline-warning" onclick="location.reload()">
                    <i class="fas fa-redo me-1"></i> Recarregar página
                </button>
            </div>
        `;
    }

    // 🎯 UTILITÁRIOS
    formatarMoeda(valor) {
        if (!valor) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    formatarPeso(peso) {
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.formatarPeso(peso);
        }
        // Fallback
        if (!peso) return '0 kg';
        return `${parseFloat(peso).toFixed(1)} kg`;
    }

    formatarPallet(pallet) {
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.formatarPallet(pallet);
        }
        // Fallback
        if (!pallet) return '0 plt';
        return `${parseFloat(pallet).toFixed(2)} plt`;
    }
}

// Disponibilizar globalmente
window.DropdownSeparacoes = DropdownSeparacoes;
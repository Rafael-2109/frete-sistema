/**
 * Sistema de Análise de Ruptura de Estoque
 * Corrigido com evidências do código real
 */

class RupturaEstoqueManager {
    constructor() {
        console.log('🚀 RupturaEstoqueManager: Iniciando...');
        this.analisesEmAndamento = new Map(); // Map para armazenar AbortControllers
        this.filaAnalises = []; // Fila de análises pendentes
        this.processandoFila = false; // Flag para controlar processamento
        this.pausado = false; // Flag para pausar completamente
        this.init();
    }
    
    init() {
        console.log('📋 RupturaEstoqueManager: Aguardando DOM...');
        
        // Configurar interceptadores ANTES de adicionar botões
        this.configurarInterceptadores();
        
        // Aguardar um momento para garantir que todos os scripts carregaram
        setTimeout(() => {
            console.log('🔍 RupturaEstoqueManager: Adicionando botões...');
            this.adicionarBotoesRuptura();
            this.configurarHooksSeparacao();
            this.iniciarAnalisesAutomaticas();
        }, 1000);
    }
    
    /**
     * Configura interceptadores para pausar análises
     */
    configurarInterceptadores() {
        const self = this;
        
        // Interceptar TODOS os cliques (capture phase)
        document.addEventListener('click', function(e) {
            const target = e.target;
            const isButton = target.closest('button, .btn, a[href], [onclick]');
            const isRupturaInicial = target.closest('.btn-analisar-ruptura');
            
            // Se clicar em qualquer botão que NÃO seja de ruptura inicial
            if (isButton && !isRupturaInicial) {
                console.log('🛑 Pausando análises - Usuário clicou em:', target.textContent?.trim());
                
                // Pausar TUDO imediatamente
                self.pausarAnalises();
                
                // Retomar após 2 segundos
                setTimeout(() => {
                    console.log('✅ Retomando análises');
                    self.retomarAnalises();
                }, 2000);
            }
        }, true); // true = capture phase (intercepta ANTES)
        
        // Interceptar abertura de modais
        document.addEventListener('show.bs.modal', function() {
            console.log('📋 Modal aberto - pausando análises');
            self.pausarAnalises();
        });
        
        // Retomar quando modal fechar
        document.addEventListener('hidden.bs.modal', function() {
            setTimeout(() => {
                console.log('✅ Modal fechado - retomando análises');
                self.retomarAnalises();
            }, 500);
        });
        
        console.log('✅ Interceptadores configurados');
    }
    
    /**
     * Pausa todas as análises
     */
    pausarAnalises() {
        this.pausado = true;
        this.processandoFila = false;
        
        // Abortar todas as análises em andamento
        this.analisesEmAndamento.forEach((controller, pedido) => {
            console.log(`  → Abortando análise do pedido ${pedido}`);
            controller.abort();
        });
        this.analisesEmAndamento.clear();
        
        // Mostrar indicador visual
        this.atualizarIndicador('pausado');
    }
    
    /**
     * Retoma as análises
     */
    retomarAnalises() {
        if (!this.pausado) return;
        
        this.pausado = false;
        this.atualizarIndicador('processando');
        
        // Retomar processamento da fila
        if (this.filaAnalises.length > 0) {
            this.processarFilaAnalises();
        }
    }
    
    /**
     * Iniciar análises automáticas com fila
     */
    iniciarAnalisesAutomaticas() {
        const tabela = document.getElementById('tabela-carteira');
        if (!tabela) {
            setTimeout(() => this.iniciarAnalisesAutomaticas(), 1000);
            return;
        }
        
        // Buscar todos os pedidos
        const rows = tabela.querySelectorAll('tbody tr.pedido-row');
        
        rows.forEach((row) => {
            const numPedido = row.dataset.pedido;
            const btn = row.querySelector('.btn-analisar-ruptura');
            
            if (numPedido && btn) {
                // Adicionar à fila em vez de analisar imediatamente
                this.filaAnalises.push({ numPedido, btn });
            }
        });
        
        console.log(`📋 ${this.filaAnalises.length} análises na fila`);
        
        // Criar indicador de progresso
        this.criarIndicadorProgresso();
        
        // Iniciar processamento da fila
        this.processarFilaAnalises();
    }
    
    /**
     * Processa a fila de análises
     */
    async processarFilaAnalises() {
        // Se está pausado ou já processando, sair
        if (this.pausado || this.processandoFila) return;
        
        // Se não há itens na fila
        if (this.filaAnalises.length === 0) {
            console.log('✅ Todas as análises concluídas');
            this.removerIndicadorProgresso();
            return;
        }
        
        this.processandoFila = true;
        
        // Pegar próximo item da fila
        const item = this.filaAnalises.shift();
        
        if (item && !this.pausado) {
            await this.analisarRupturaInicial(item.numPedido, item.btn);
        }
        
        this.processandoFila = false;
        
        // Continuar processando se não estiver pausado
        if (!this.pausado) {
            // Pequeno delay entre análises
            setTimeout(() => this.processarFilaAnalises(), 100);
        }
    }
    
    /**
     * Cria indicador de progresso
     */
    criarIndicadorProgresso() {
        if (document.getElementById('ruptura-progresso')) return;
        
        const indicator = document.createElement('div');
        indicator.id = 'ruptura-progresso';
        indicator.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 10px 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
            font-size: 0.9rem;
            display: none;
        `;
        document.body.appendChild(indicator);
    }
    
    /**
     * Atualiza indicador de progresso
     */
    atualizarIndicador(status) {
        const indicator = document.getElementById('ruptura-progresso');
        if (!indicator) return;
        
        if (this.filaAnalises.length === 0 && !this.processandoFila) {
            indicator.style.display = 'none';
            return;
        }
        
        indicator.style.display = 'block';
        
        if (status === 'pausado') {
            indicator.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fas fa-pause-circle text-warning me-2"></i>
                    <span>Análises pausadas (${this.filaAnalises.length} pendentes)</span>
                </div>
            `;
        } else {
            indicator.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fas fa-spinner fa-spin text-primary me-2"></i>
                    <span>Analisando estoque (${this.filaAnalises.length} restantes)</span>
                </div>
            `;
        }
    }
    
    /**
     * Remove indicador de progresso
     */
    removerIndicadorProgresso() {
        const indicator = document.getElementById('ruptura-progresso');
        if (indicator) {
            setTimeout(() => {
                indicator.style.display = 'none';
            }, 2000);
        }
    }
    
    /**
     * Adiciona botões de análise de ruptura
     */
    adicionarBotoesRuptura() {
        // EVIDÊNCIA: Tabela tem ID "tabela-carteira" (linha 184 do HTML)
        const tabela = document.getElementById('tabela-carteira');
        
        if (!tabela) {
            console.error('❌ RupturaEstoqueManager: Tabela #tabela-carteira não encontrada!');
            // Tentar novamente após 2 segundos
            setTimeout(() => this.adicionarBotoesRuptura(), 2000);
            return;
        }
        
        console.log('✅ RupturaEstoqueManager: Tabela encontrada');
        
        // Buscar apenas linhas de pedido (não linhas de detalhe)
        const rows = tabela.querySelectorAll('tbody tr.pedido-row');
        console.log(`📊 RupturaEstoqueManager: ${rows.length} pedidos encontrados`);
        
        let botoesAdicionados = 0;
        
        rows.forEach((row, index) => {
            // Pular se já tem botão
            if (row.querySelector('.btn-analisar-ruptura')) {
                return;
            }
            
            const numPedido = row.dataset.pedido;
            
            if (!numPedido) {
                console.warn(`⚠️ Linha ${index + 1} sem data-pedido`);
                return;
            }
            
            // EVIDÊNCIA: Coluna "Entrega/Obs" tem classe "coluna-entrega-obs" (linha 316 do HTML)
            const celulaObs = row.querySelector('.coluna-entrega-obs');
            
            if (!celulaObs) {
                console.warn(`⚠️ Pedido ${numPedido}: Célula .coluna-entrega-obs não encontrada`);
                return;
            }
            
            // Criar e adicionar botão
            const btnContainer = document.createElement('div');
            btnContainer.className = 'mt-2';
            btnContainer.innerHTML = `
                <button class="btn btn-sm btn-outline-info btn-analisar-ruptura" 
                        data-pedido="${numPedido}"
                        title="Verificar disponibilidade de estoque"
                        style="font-size: 0.75rem;">
                    <i class="fas fa-box me-1"></i>
                    Verificar Estoque
                </button>
            `;
            
            celulaObs.appendChild(btnContainer);
            
            // Adicionar listener para clique manual
            const btn = btnContainer.querySelector('.btn-analisar-ruptura');
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                // Pausar fila e analisar imediatamente este pedido
                this.pausarAnalises();
                this.analisarRuptura(numPedido, btn);
                
                // Retomar fila após 2 segundos
                setTimeout(() => this.retomarAnalises(), 2000);
            });
            
            // NÃO fazer análise inicial aqui (será feita pela fila)
            
            botoesAdicionados++;
        });
        
        console.log(`✅ RupturaEstoqueManager: ${botoesAdicionados} botões adicionados`);
    }
    
    /**
     * Analisa ruptura inicial (automática ao carregar)
     */
    async analisarRupturaInicial(numPedido, btnElement) {
        // Se está pausado, adicionar de volta à fila
        if (this.pausado) {
            this.filaAnalises.unshift({ numPedido, btn: btnElement });
            return;
        }
        
        // Criar AbortController para esta análise
        const controller = new AbortController();
        this.analisesEmAndamento.set(numPedido, controller);
        
        try {
            // Atualizar indicador
            this.atualizarIndicador('processando');
            
            const response = await fetch(`/carteira/api/ruptura/analisar-pedido/${numPedido}`, {
                signal: controller.signal
            });
            
            // Verificar se foi abortado
            if (controller.signal.aborted) {
                // Adicionar de volta à fila
                this.filaAnalises.push({ numPedido, btn: btnElement });
                return;
            }
            
            const data = await response.json();
            
            if (!data.success) {
                btnElement.innerHTML = '<i class="fas fa-box me-1"></i>Verificar Estoque';
                return;
            }
            
            // Atualizar botão com resultado
            if (data.pedido_ok) {
                btnElement.className = 'btn btn-sm btn-success btn-analisar-ruptura';
                btnElement.innerHTML = '<i class="fas fa-check"></i> Pedido OK';
                btnElement.title = 'Todos os itens disponíveis';
            } else {
                // Tem ruptura - mostrar formato novo
                const criticidade = data.resumo?.criticidade || 'MEDIA';
                const cores = {
                    'CRITICA': 'btn-danger',
                    'ALTA': 'btn-warning',
                    'MEDIA': 'btn-info',
                    'BAIXA': 'btn-secondary'
                };
                
                const percentualDisp = Math.round(data.percentual_disponibilidade || data.resumo.percentual_disponibilidade || 0);
                const dataDisp = data.data_disponibilidade_total || data.resumo.data_disponibilidade_total;
                
                let textoData = 'Total Não Disp.';
                if (dataDisp && dataDisp !== 'null' && dataDisp !== null) {
                    const [ano, mes, dia] = dataDisp.split('-');
                    textoData = `Total Disp. ${dia}/${mes}`;
                }
                
                btnElement.className = `btn btn-sm ${cores[criticidade]} btn-analisar-ruptura`;
                btnElement.innerHTML = `
                    <i class="fas fa-exclamation-triangle"></i> 
                    Disp. ${percentualDisp}% | ${textoData}
                `;
                btnElement.title = `${data.resumo.qtd_itens_disponiveis} de ${data.resumo.total_itens} itens disponíveis`;
            }
        } catch (error) {
            // Se foi abortado, adicionar de volta à fila
            if (error.name === 'AbortError') {
                console.log(`Análise de ${numPedido} interrompida`);
                this.filaAnalises.push({ numPedido, btn: btnElement });
                btnElement.innerHTML = '<i class="fas fa-box me-1"></i>Verificar Estoque';
            } else {
                console.error(`Erro na análise inicial do pedido ${numPedido}:`, error);
                btnElement.innerHTML = '<i class="fas fa-box me-1"></i>Verificar Estoque';
            }
        } finally {
            // Remover do mapa de análises em andamento
            this.analisesEmAndamento.delete(numPedido);
        }
    }
    
    /**
     * Analisa ruptura de estoque
     */
    async analisarRuptura(numPedido, btnElement) {
        console.log(`🔍 Analisando ruptura do pedido ${numPedido}...`);
        
        try {
            // Salvar HTML original
            const htmlOriginal = btnElement.innerHTML;
            
            // Mostrar loading
            btnElement.disabled = true;
            btnElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analisando...';
            
            // EVIDÊNCIA: Rotas confirmadas via Python - /carteira/api/ruptura/...
            const response = await fetch(`/carteira/api/ruptura/analisar-pedido/${numPedido}`);
            const data = await response.json();
            
            console.log('📦 Resposta da API:', data);
            
            if (!data.success) {
                throw new Error(data.error || data.message || 'Erro ao analisar pedido');
            }
            
            // Se pedido está OK
            if (data.pedido_ok) {
                btnElement.disabled = false;
                btnElement.className = 'btn btn-sm btn-success';
                btnElement.innerHTML = '<i class="fas fa-check"></i> Pedido OK';
                btnElement.title = 'Todos os itens disponíveis';
                return;
            }
            
            // Se há ruptura, mostrar modal
            this.mostrarModalRuptura(data);
            
            // Atualizar visual do botão com novo formato
            const criticidade = data.resumo?.criticidade || 'MEDIA';
            const cores = {
                'CRITICA': 'btn-danger',
                'ALTA': 'btn-warning',
                'MEDIA': 'btn-info',
                'BAIXA': 'btn-secondary'
            };
            
            // Calcular texto do botão: "Disp. X% | Total Disp/Não Disp"
            const percentualDisp = Math.round(data.percentual_disponibilidade || data.resumo.percentual_disponibilidade || 0);
            const dataDisp = data.data_disponibilidade_total || data.resumo.data_disponibilidade_total;
            
            let textoData = 'Total Não Disp.';
            if (dataDisp && dataDisp !== 'null' && dataDisp !== null) {
                // Formatar data DD/MM
                const [ano, mes, dia] = dataDisp.split('-');
                textoData = `Total Disp. ${dia}/${mes}`;
            }
            
            btnElement.disabled = false;
            btnElement.className = `btn btn-sm ${cores[criticidade]}`;
            btnElement.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i> 
                Disp. ${percentualDisp}% | ${textoData}
            `;
            btnElement.title = `${data.resumo.qtd_itens_disponiveis} de ${data.resumo.total_itens} itens disponíveis`;
            
        } catch (error) {
            console.error('❌ Erro ao analisar ruptura:', error);
            btnElement.disabled = false;
            btnElement.innerHTML = '<i class="fas fa-times"></i> Erro';
            btnElement.className = 'btn btn-sm btn-danger';
            
            // Mostrar erro ao usuário
            if (window.Swal) {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: error.message || 'Erro ao analisar ruptura'
                });
            } else {
                alert('Erro ao analisar ruptura: ' + error.message);
            }
        }
    }
    
    /**
     * Mostra modal com detalhes da ruptura
     */
    mostrarModalRuptura(data) {
        // Salvar dados para reutilização
        this.dadosRuptura = data;
        
        // Criar modal se não existir
        let modal = document.getElementById('modalRuptura');
        if (!modal) {
            modal = this.criarModalRuptura();
        }
        
        const resumo = data.resumo;
        const cores = {
            'CRITICA': 'danger',
            'ALTA': 'warning',
            'MEDIA': 'info',
            'BAIXA': 'secondary'
        };
        
        // Adicionar à navegação se existe
        if (window.modalNav) {
            window.modalNav.pushModal('modalRuptura', `Pedido ${resumo.num_pedido}`, data);
        }
        
        // Título com toggle
        document.getElementById('modalRupturaTitulo').innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    Análise de Ruptura - Pedido ${resumo.num_pedido}
                    <span class="badge bg-${cores[resumo.criticidade]} ms-2">
                        ${resumo.criticidade}
                    </span>
                </div>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-danger active" 
                            onclick="rupturaManager.mostrarItensRuptura()">
                        <i class="fas fa-exclamation-triangle me-1"></i>
                        Ruptura (${resumo.qtd_itens_ruptura})
                    </button>
                    <button type="button" class="btn btn-outline-success" 
                            onclick="rupturaManager.mostrarItensDisponiveis()">
                        <i class="fas fa-check-circle me-1"></i>
                        Disponíveis (${resumo.qtd_itens_disponiveis})
                    </button>
                    <button type="button" class="btn btn-outline-primary" 
                            onclick="rupturaManager.mostrarTodosItens()">
                        <i class="fas fa-list me-1"></i>
                        Todos (${resumo.total_itens})
                    </button>
                </div>
            </div>
        `;
        
        // Resumo
        document.getElementById('modalRupturaResumo').innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="text-center">
                        <strong>Disponibilidade</strong><br>
                        <span class="h4 text-success">${Math.round(resumo.percentual_disponibilidade)}%</span>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <strong>Em Ruptura</strong><br>
                        <span class="h4 text-danger">${resumo.percentual_ruptura}%</span>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <strong>Valor Total</strong><br>
                        <span class="h5">R$ ${this.formatarMoeda(resumo.valor_total_pedido)}</span>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <strong>Valor em Risco</strong><br>
                        <span class="h5 text-danger">R$ ${this.formatarMoeda(resumo.valor_com_ruptura)}</span>
                    </div>
                </div>
            </div>
        `;
        
        // Mostrar itens em ruptura por padrão
        this.mostrarItensRuptura();
        
        // Mostrar modal (Bootstrap 5)
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
    
    /**
     * Mostra itens com ruptura
     */
    mostrarItensRuptura() {
        if (!this.dadosRuptura) return;
        
        const tbody = document.getElementById('modalRupturaItens');
        const itens = this.dadosRuptura.itens || [];
        
        // Atualizar título da seção
        const tituloSecao = tbody.closest('.modal-body').querySelector('h6');
        if (tituloSecao) {
            tituloSecao.innerHTML = '<i class="fas fa-exclamation-triangle text-danger me-2"></i>Itens com Ruptura de Estoque:';
        }
        
        // Atualizar botões de toggle
        this.atualizarBotoesToggle('ruptura');
        
        if (itens.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        <i class="fas fa-check-circle text-success me-2"></i>
                        Nenhum item com ruptura
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = itens.map(item => `
            <tr>
                <td>
                    ${item.cod_produto}
                    <button class="btn btn-sm btn-link p-0 ms-2" 
                            onclick="rupturaManager.abrirCardex('${item.cod_produto}')"
                            title="Ver Cardex">
                        <i class="fas fa-chart-line"></i>
                    </button>
                </td>
                <td>${item.nome_produto}</td>
                <td class="text-end">${this.formatarNumero(item.qtd_saldo)}</td>
                <td class="text-end ${item.estoque_min_d7 < 0 ? 'text-danger' : ''}">
                    ${this.formatarNumero(item.estoque_min_d7)}
                </td>
                <td class="text-end text-danger fw-bold">
                    ${this.formatarNumero(item.ruptura_qtd)}
                </td>
                <td class="text-center">
                    ${item.data_producao ? 
                        `<span class="badge bg-primary">
                            ${this.formatarData(item.data_producao)}
                            <br>
                            <small>${this.formatarNumero(item.qtd_producao)} un</small>
                        </span>` : 
                        '<span class="badge bg-danger">Sem Produção</span>'
                    }
                </td>
                <td class="text-center">
                    ${item.data_disponivel ? 
                        `<span class="badge bg-success">
                            ${this.formatarData(item.data_disponivel)}
                        </span>` : 
                        '<span class="badge bg-secondary">Indisponível</span>'
                    }
                </td>
            </tr>
        `).join('');
    }
    
    /**
     * Mostra itens disponíveis
     */
    mostrarItensDisponiveis() {
        if (!this.dadosRuptura) return;
        
        const tbody = document.getElementById('modalRupturaItens');
        const itens = this.dadosRuptura.itens_disponiveis || [];
        
        // Atualizar título da seção
        const tituloSecao = tbody.closest('.modal-body').querySelector('h6');
        if (tituloSecao) {
            tituloSecao.innerHTML = '<i class="fas fa-check-circle text-success me-2"></i>Itens com Disponibilidade:';
        }
        
        // Atualizar botões de toggle
        this.atualizarBotoesToggle('disponiveis');
        
        if (itens.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                        Nenhum item disponível
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = itens.map(item => `
            <tr>
                <td>
                    ${item.cod_produto}
                    <button class="btn btn-sm btn-link p-0 ms-2" 
                            onclick="rupturaManager.abrirCardex('${item.cod_produto}')"
                            title="Ver Cardex">
                        <i class="fas fa-chart-line"></i>
                    </button>
                </td>
                <td>${item.nome_produto}</td>
                <td class="text-end">${this.formatarNumero(item.qtd_saldo)}</td>
                <td class="text-end text-success">
                    ${this.formatarNumero(item.estoque_min_d7)}
                </td>
                <td class="text-end text-success fw-bold">
                    <i class="fas fa-check"></i> OK
                </td>
                <td class="text-center">
                    <span class="badge bg-success">
                        <i class="fas fa-check"></i> Disponível
                    </span>
                </td>
                <td class="text-center">
                    <span class="badge bg-success">Agora</span>
                </td>
            </tr>
        `).join('');
    }
    
    /**
     * Mostra todos os itens
     */
    mostrarTodosItens() {
        if (!this.dadosRuptura) return;
        
        const tbody = document.getElementById('modalRupturaItens');
        const itensRuptura = this.dadosRuptura.itens || [];
        const itensDisponiveis = this.dadosRuptura.itens_disponiveis || [];
        
        // Atualizar título da seção
        const tituloSecao = tbody.closest('.modal-body').querySelector('h6');
        if (tituloSecao) {
            tituloSecao.innerHTML = '<i class="fas fa-list text-primary me-2"></i>Todos os Itens do Pedido:';
        }
        
        // Atualizar botões de toggle
        this.atualizarBotoesToggle('todos');
        
        const todosItens = [];
        
        // Adicionar itens com ruptura primeiro
        if (itensRuptura.length > 0) {
            todosItens.push(`
                <tr class="table-secondary">
                    <td colspan="7" class="fw-bold">
                        <i class="fas fa-exclamation-triangle text-danger me-2"></i>
                        Itens com Ruptura (${itensRuptura.length})
                    </td>
                </tr>
            `);
            
            itensRuptura.forEach(item => {
                todosItens.push(`
                    <tr>
                        <td>
                            ${item.cod_produto}
                            <button class="btn btn-sm btn-link p-0 ms-2" 
                                    onclick="rupturaManager.abrirCardex('${item.cod_produto}')"
                                    title="Ver Cardex">
                                <i class="fas fa-chart-line"></i>
                            </button>
                        </td>
                        <td>${item.nome_produto}</td>
                        <td class="text-end">${this.formatarNumero(item.qtd_saldo)}</td>
                        <td class="text-end ${item.estoque_min_d7 < 0 ? 'text-danger' : ''}">
                            ${this.formatarNumero(item.estoque_min_d7)}
                        </td>
                        <td class="text-end text-danger fw-bold">
                            ${this.formatarNumero(item.ruptura_qtd)}
                        </td>
                        <td class="text-center">
                            ${item.data_producao ? 
                                `<span class="badge bg-primary">
                                    ${this.formatarData(item.data_producao)}
                                    <br>
                                    <small>${this.formatarNumero(item.qtd_producao)} un</small>
                                </span>` : 
                                '<span class="badge bg-danger">Sem Produção</span>'
                            }
                        </td>
                        <td class="text-center">
                            ${item.data_disponivel ? 
                                `<span class="badge bg-success">
                                    ${this.formatarData(item.data_disponivel)}
                                </span>` : 
                                '<span class="badge bg-secondary">Indisponível</span>'
                            }
                        </td>
                    </tr>
                `);
            });
        }
        
        // Adicionar itens disponíveis
        if (itensDisponiveis.length > 0) {
            todosItens.push(`
                <tr class="table-secondary">
                    <td colspan="7" class="fw-bold">
                        <i class="fas fa-check-circle text-success me-2"></i>
                        Itens Disponíveis (${itensDisponiveis.length})
                    </td>
                </tr>
            `);
            
            itensDisponiveis.forEach(item => {
                todosItens.push(`
                    <tr>
                        <td>
                            ${item.cod_produto}
                            <button class="btn btn-sm btn-link p-0 ms-2" 
                                    onclick="rupturaManager.abrirCardex('${item.cod_produto}')"
                                    title="Ver Cardex">
                                <i class="fas fa-chart-line"></i>
                            </button>
                        </td>
                        <td>${item.nome_produto}</td>
                        <td class="text-end">${this.formatarNumero(item.qtd_saldo)}</td>
                        <td class="text-end text-success">
                            ${this.formatarNumero(item.estoque_min_d7)}
                        </td>
                        <td class="text-end text-success fw-bold">
                            <i class="fas fa-check"></i> OK
                        </td>
                        <td class="text-center">
                            <span class="badge bg-success">
                                <i class="fas fa-check"></i> Disponível
                            </span>
                        </td>
                        <td class="text-center">
                            <span class="badge bg-success">Agora</span>
                        </td>
                    </tr>
                `);
            });
        }
        
        tbody.innerHTML = todosItens.join('');
    }
    
    /**
     * Atualiza estado visual dos botões de toggle
     */
    atualizarBotoesToggle(tipoAtivo) {
        const btnGroup = document.querySelector('#modalRupturaTitulo .btn-group');
        if (!btnGroup) return;
        
        const botoes = btnGroup.querySelectorAll('button');
        botoes.forEach(btn => {
            btn.classList.remove('active');
            
            if (tipoAtivo === 'ruptura' && btn.textContent.includes('Ruptura')) {
                btn.classList.add('active');
            } else if (tipoAtivo === 'disponiveis' && btn.textContent.includes('Disponíveis')) {
                btn.classList.add('active');
            } else if (tipoAtivo === 'todos' && btn.textContent.includes('Todos')) {
                btn.classList.add('active');
            }
        });
    }
    
    /**
     * Abre o modal Cardex para um produto
     */
    abrirCardex(codProduto) {
        // Criar Map com dados dos produtos se necessário
        const dadosProdutos = new Map();
        
        // Adicionar dados dos itens com ruptura
        if (this.dadosRuptura && this.dadosRuptura.itens) {
            this.dadosRuptura.itens.forEach(item => {
                dadosProdutos.set(item.cod_produto, item);
            });
        }
        
        // Adicionar dados dos itens disponíveis
        if (this.dadosRuptura && this.dadosRuptura.itens_disponiveis) {
            this.dadosRuptura.itens_disponiveis.forEach(item => {
                dadosProdutos.set(item.cod_produto, item);
            });
        }
        
        // Integração com o sistema de navegação
        if (window.modalNav) {
            window.modalNav.pushModal('modalCardex', `Cardex - ${codProduto}`, {
                codProduto: codProduto,
                dadosProdutos: dadosProdutos
            });
        }
        
        // Chamar função existente do cardex se disponível
        if (window.modalCardex && window.modalCardex.abrirCardex) {
            window.modalCardex.abrirCardex(codProduto, dadosProdutos);
        } else {
            console.warn('Sistema de Cardex não disponível');
            alert(`Abrindo Cardex para produto ${codProduto}`);
        }
    }
    
    /**
     * Cria estrutura do modal
     */
    criarModalRuptura() {
        const modalHtml = `
            <div class="modal fade" id="modalRuptura" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header bg-info text-white">
                            <h5 class="modal-title" id="modalRupturaTitulo">
                                Análise de Ruptura
                            </h5>
                            <button type="button" class="btn-close btn-close-white" 
                                    data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="modalRupturaResumo" class="alert alert-light">
                                <!-- Resumo -->
                            </div>
                            
                            <h6 class="mt-3">Itens com Ruptura de Estoque:</h6>
                            <div class="table-responsive">
                                <table class="table table-sm table-striped">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>Código</th>
                                            <th>Produto</th>
                                            <th class="text-end">Qtd Saldo</th>
                                            <th class="text-end">Est.Min D+7</th>
                                            <th class="text-end">Ruptura</th>
                                            <th class="text-center">Produção</th>
                                            <th class="text-center">Disponível em</th>
                                        </tr>
                                    </thead>
                                    <tbody id="modalRupturaItens">
                                        <!-- Itens -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" 
                                    data-bs-dismiss="modal">Fechar</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        return document.getElementById('modalRuptura');
    }
    
    /**
     * Configura hooks com separacaoManager
     */
    configurarHooksSeparacao() {
        console.log('🔧 Configurando hooks de separação...');
        
        // EVIDÊNCIA: separacaoManager.applyTargets existe (linha 88 do separacao-manager.js)
        const tentarConfigurar = () => {
            if (window.separacaoManager && window.separacaoManager.applyTargets) {
                console.log('✅ separacaoManager encontrado, configurando hook...');
                
                const originalApplyTargets = window.separacaoManager.applyTargets;
                
                window.separacaoManager.applyTargets = async function(data) {
                    console.log('🔄 Hook applyTargets executado:', data);
                    
                    // Executar método original
                    const resultado = await originalApplyTargets.call(this, data);
                    
                    // Atualizar visual se houver pedido
                    if (data.num_pedido || data.pedido) {
                        const numPedido = data.num_pedido || data.pedido;
                        console.log(`📦 Atualizando visual do pedido ${numPedido}`);
                        window.rupturaManager.atualizarVisualPosSeparacao(numPedido);
                    }
                    
                    return resultado;
                };
                
                console.log('✅ Hook configurado com sucesso');
            } else {
                console.log('⏳ separacaoManager ainda não disponível, tentando novamente...');
                setTimeout(tentarConfigurar, 500);
            }
        };
        
        tentarConfigurar();
    }
    
    /**
     * Atualiza visual após criar separação
     */
    async atualizarVisualPosSeparacao(numPedido) {
        console.log(`🎨 Atualizando visual do pedido ${numPedido}...`);
        
        try {
            // Buscar linha do pedido
            const row = document.querySelector(`tr[data-pedido="${numPedido}"]`);
            
            if (!row) {
                console.warn(`Linha do pedido ${numPedido} não encontrada`);
                return;
            }
            
            // Adicionar classe de sucesso
            row.classList.add('table-success', 'pedido-com-separacao');
            
            // Adicionar animação
            row.style.transition = 'background-color 0.5s';
            row.style.backgroundColor = '#d4edda';
            
            setTimeout(() => {
                row.style.backgroundColor = '';
            }, 2000);
            
            // Chamar API para obter dados atualizados
            const response = await fetch('/carteira/api/ruptura/atualizar-visual-separacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    num_pedido: numPedido
                })
            });
            
            const data = await response.json();
            console.log('📦 Dados atualizados:', data);
            
            // Atualizar data de expedição se existir
            if (data.pedido?.data_expedicao) {
                const campoExpedicao = row.querySelector('.expedicao-info strong');
                if (campoExpedicao) {
                    campoExpedicao.textContent = this.formatarData(data.pedido.data_expedicao);
                }
            }
            
        } catch (error) {
            console.error('❌ Erro ao atualizar visual:', error);
        }
    }
    
    // Funções auxiliares de formatação
    formatarMoeda(valor) {
        return (valor || 0).toFixed(2).replace('.', ',');
    }
    
    formatarNumero(valor) {
        // Sem casas decimais para quantidades
        return Math.round(valor || 0).toLocaleString('pt-BR');
    }
    
    formatarData(dataString) {
        if (!dataString) return '-';
        const [ano, mes, dia] = dataString.split('-');
        return `${dia}/${mes}/${ano}`;
    }
}

// Inicializar após DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM carregado, inicializando RupturaEstoqueManager...');
    window.rupturaManager = new RupturaEstoqueManager();
});

// Re-adicionar botões se tabela for atualizada via AJAX
document.addEventListener('tabela-atualizada', () => {
    console.log('📊 Tabela atualizada, re-adicionando botões...');
    if (window.rupturaManager) {
        window.rupturaManager.adicionarBotoesRuptura();
    }
});
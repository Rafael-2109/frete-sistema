/**
 * Sistema de Análise de Ruptura de Estoque
 * Corrigido com evidências do código real
 */

class RupturaEstoqueManager {
    constructor() {
        console.log('🚀 RupturaEstoqueManager: Iniciando...');
        this.analisesEmAndamento = new Map(); // Map para armazenar AbortControllers por pedido
        this.filaAnalises = []; // Fila de análises pendentes
        this.processandoFila = false; // Flag para controlar processamento da fila
        this.acaoUsuarioEmAndamento = false; // Flag para indicar ação do usuário
        this.delayEntreAnalises = 100; // Delay entre análises (ms)
        this.init();
    }
    
    init() {
        console.log('📋 RupturaEstoqueManager: Aguardando DOM...');
        
        // Configurar interceptadores de prioridade
        this.configurarPrioridades();
        
        // Aguardar um momento para garantir que todos os scripts carregaram
        setTimeout(() => {
            console.log('🔍 RupturaEstoqueManager: Adicionando botões...');
            this.adicionarBotoesRuptura();
            this.configurarHooksSeparacao();
            this.iniciarAnalisesAutomaticas();
        }, 1000);
    }
    
    /**
     * Configura sistema de prioridades para ações do usuário
     */
    configurarPrioridades() {
        const self = this;
        
        // Interceptar TODOS os cliques para dar prioridade
        document.addEventListener('click', (e) => {
            const target = e.target;
            
            // Se clicar em QUALQUER botão ou link (exceto ruptura)
            const isButton = target.closest('button, .btn, a[href], [onclick], .clickable');
            const isRupturaButton = target.closest('.btn-analisar-ruptura');
            
            if (isButton && !isRupturaButton) {
                console.log('🛑 INTERROMPENDO análises - Ação do usuário detectada:', target.textContent?.trim());
                
                // PARAR TUDO IMEDIATAMENTE
                self.acaoUsuarioEmAndamento = true;
                self.processandoFila = false;
                
                // CANCELAR análise em andamento se houver
                if (self.analisesEmAndamento.size > 0) {
                    console.log('🛑 Cancelando análise em andamento para dar prioridade');
                    self.analisesEmAndamento.forEach((controller, pedido) => {
                        controller.abort();
                        // Adicionar de volta à fila para processar depois
                        const btn = document.querySelector(`.btn-analisar-ruptura[data-pedido="${pedido}"]`);
                        if (btn && !btn.classList.contains('analisado')) {
                            self.filaAnalises.unshift({ numPedido: pedido, btn });
                            btn.classList.add('na-fila');
                            btn.style.opacity = '0.5';
                        }
                    });
                    self.analisesEmAndamento.clear();
                }
                
                // Atualizar progresso
                self.atualizarProgresso();
                
                // Retomar após um tempo
                clearTimeout(self.timeoutRetomar);
                self.timeoutRetomar = setTimeout(() => {
                    console.log('✅ Retomando análises de ruptura');
                    self.acaoUsuarioEmAndamento = false;
                    self.processarFilaAnalises();
                }, 3000); // 3 segundos para garantir que a ação complete
            }
        }, true); // Usar capture phase para interceptar ANTES de qualquer outro handler
        
        // Também interceptar mudanças de URL (navegação)
        window.addEventListener('popstate', () => {
            self.acaoUsuarioEmAndamento = true;
            self.cancelarTodasAnalises();
        });
        
        // Interceptar submit de formulários
        document.addEventListener('submit', (e) => {
            console.log('📝 Formulário submetido - pausando análises');
            self.acaoUsuarioEmAndamento = true;
            self.processandoFila = false;
            
            // Cancelar análises em andamento
            if (self.analisesEmAndamento.size > 0) {
                self.analisesEmAndamento.forEach((controller) => {
                    controller.abort();
                });
                self.analisesEmAndamento.clear();
            }
        }, true);
        
        // Interceptar teclas importantes
        document.addEventListener('keydown', (e) => {
            // Se pressionar Enter ou Space em um elemento focado
            if ((e.key === 'Enter' || e.key === ' ') && document.activeElement) {
                const isButton = document.activeElement.closest('button, .btn, a[href]');
                const isRuptura = document.activeElement.closest('.btn-analisar-ruptura');
                
                if (isButton && !isRuptura) {
                    console.log('⌨️ Tecla pressionada em botão - pausando análises');
                    self.acaoUsuarioEmAndamento = true;
                    self.processandoFila = false;
                    
                    clearTimeout(self.timeoutRetomar);
                    self.timeoutRetomar = setTimeout(() => {
                        self.acaoUsuarioEmAndamento = false;
                        self.processarFilaAnalises();
                    }, 3000);
                }
            }
        }, true);
        
        console.log('✅ Sistema de prioridades configurado com interceptadores completos');
    }
    
    /**
     * Inicia análises automáticas com sistema de fila
     */
    iniciarAnalisesAutomaticas() {
        const tabela = document.getElementById('tabela-carteira');
        if (!tabela) {
            setTimeout(() => this.iniciarAnalisesAutomaticas(), 1000);
            return;
        }
        
        // Buscar todos os pedidos que precisam de análise
        const rows = tabela.querySelectorAll('tbody tr.pedido-row');
        
        rows.forEach((row) => {
            const numPedido = row.dataset.pedido;
            const btn = row.querySelector('.btn-analisar-ruptura');
            
            if (numPedido && btn && !btn.classList.contains('analisado')) {
                // Adicionar à fila em vez de analisar imediatamente
                this.filaAnalises.push({ numPedido, btn });
                
                // Marcar botão como "na fila"
                btn.classList.add('na-fila');
                btn.style.opacity = '0.5';
                btn.title = 'Aguardando na fila de análise...';
            }
        });
        
        console.log(`📋 ${this.filaAnalises.length} análises adicionadas à fila`);
        
        // Mostrar indicador de progresso
        this.mostrarProgresso();
        
        // Iniciar processamento da fila
        this.processarFilaAnalises();
    }
    
    /**
     * Mostra indicador de progresso
     */
    mostrarProgresso() {
        // Criar indicador se não existir
        if (!document.getElementById('ruptura-progresso')) {
            const progresso = document.createElement('div');
            progresso.id = 'ruptura-progresso';
            progresso.style.cssText = `
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
            `;
            document.body.appendChild(progresso);
        }
        
        this.atualizarProgresso();
    }
    
    /**
     * Atualiza indicador de progresso
     */
    atualizarProgresso() {
        const progresso = document.getElementById('ruptura-progresso');
        if (!progresso) return;
        
        const total = this.filaAnalises.length;
        const analisados = document.querySelectorAll('.btn-analisar-ruptura.analisado').length;
        
        if (total === 0 && !this.processandoFila) {
            // Esconder quando terminar
            progresso.style.display = 'none';
        } else {
            progresso.style.display = 'block';
            progresso.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fas fa-spinner fa-spin me-2 text-primary"></i>
                    <span>Analisando estoque: ${analisados} de ${analisados + total}</span>
                    ${this.acaoUsuarioEmAndamento ? 
                        '<span class="badge bg-warning ms-2">Pausado</span>' : 
                        '<span class="badge bg-success ms-2">Ativo</span>'
                    }
                </div>
            `;
        }
    }
    
    /**
     * Processa a fila de análises com baixa prioridade
     */
    async processarFilaAnalises() {
        // Se já está processando ou há ação do usuário, sair
        if (this.processandoFila || this.acaoUsuarioEmAndamento) {
            return;
        }
        
        // Se não há itens na fila, sair
        if (this.filaAnalises.length === 0) {
            console.log('✅ Todas as análises de ruptura concluídas');
            this.atualizarProgresso();
            return;
        }
        
        this.processandoFila = true;
        
        // Pegar próximo item da fila
        const item = this.filaAnalises.shift();
        
        if (item && !this.acaoUsuarioEmAndamento) {
            // Remover marcação de "na fila" e colocar em processamento
            if (item.btn) {
                item.btn.classList.remove('na-fila');
                item.btn.style.opacity = '1';
            }
            
            console.log(`⏳ Analisando pedido ${item.numPedido} (${this.filaAnalises.length} restante(s))`);
            
            // Analisar com baixa prioridade
            await this.analisarRupturaBaixaPrioridade(item.numPedido, item.btn);
            
            // Atualizar progresso
            this.atualizarProgresso();
        }
        
        this.processandoFila = false;
        
        // Continuar processando a fila após delay
        if (!this.acaoUsuarioEmAndamento) {
            setTimeout(() => this.processarFilaAnalises(), this.delayEntreAnalises);
        }
    }
    
    /**
     * Analisa ruptura com baixa prioridade
     */
    async analisarRupturaBaixaPrioridade(numPedido, btnElement) {
        // Se há ação do usuário, adicionar de volta à fila e sair
        if (this.acaoUsuarioEmAndamento) {
            console.log(`⏸️ Análise de ${numPedido} pausada - ação do usuário em andamento`);
            this.filaAnalises.unshift({ numPedido, btn: btnElement });
            btnElement.classList.add('na-fila');
            btnElement.style.opacity = '0.5';
            return;
        }
        
        try {
            // Marcar como analisado para não repetir
            btnElement.classList.add('analisado');
            
            // Fazer análise normal
            await this.analisarRuptura(numPedido, btnElement);
        } catch (error) {
            // Se foi abortado, adicionar de volta à fila
            if (error.name === 'AbortError') {
                console.log(`🔄 Análise de ${numPedido} abortada - adicionando de volta à fila`);
                btnElement.classList.remove('analisado');
                this.filaAnalises.unshift({ numPedido, btn: btnElement });
                btnElement.classList.add('na-fila');
                btnElement.style.opacity = '0.5';
            }
        }
    }
    
    /**
     * Configura eventos globais para cancelar análises em andamento
     */
    configurarCancelamentosGlobais() {
        // Cancelar todas as análises ao clicar em qualquer outro botão de ruptura
        document.addEventListener('click', (e) => {
            // Se clicar em um botão de ruptura
            if (e.target.closest('.btn-analisar-ruptura')) {
                const btn = e.target.closest('.btn-analisar-ruptura');
                const numPedido = btn.dataset.pedido;
                
                // Cancelar IMEDIATAMENTE todas as outras análises em andamento
                this.analisesEmAndamento.forEach((controller, pedido) => {
                    if (pedido !== numPedido) {
                        console.log(`🛑 Cancelando IMEDIATAMENTE análise do pedido ${pedido}`);
                        controller.abort();
                        // Restaurar botão imediatamente
                        this.limparAnaliseEmAndamento(pedido);
                    }
                });
            }
            
            // Se clicar em qualquer botão de ação (separação, cotação, etc)
            if (e.target.closest('.btn-separacao, .btn-cotacao, .btn-embarque, .btn-primary, .btn-success')) {
                // Só cancelar se não for um botão de ruptura
                if (!e.target.closest('.btn-analisar-ruptura')) {
                    // Cancelar TODAS as análises em andamento IMEDIATAMENTE
                    this.cancelarTodasAnalises();
                }
            }
        }, true); // Usar capture phase para interceptar antes
        
        // Cancelar ao abrir qualquer modal
        document.addEventListener('show.bs.modal', () => {
            this.cancelarTodasAnalises();
        });
        
        // Cancelar ao navegar para outra página
        window.addEventListener('beforeunload', () => {
            this.cancelarTodasAnalises();
        });
        
        // Cancelar ao pressionar ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                console.log('🛑 ESC pressionado - cancelando todas as análises');
                this.cancelarTodasAnalises();
            }
        });
    }
    
    /**
     * Cancela todas as análises em andamento
     */
    cancelarTodasAnalises() {
        if (this.analisesEmAndamento.size > 0) {
            console.log(`🛑 INTERROMPENDO IMEDIATAMENTE ${this.analisesEmAndamento.size} análise(s)`);
            
            // Abortar todos os controllers IMEDIATAMENTE
            const controllers = Array.from(this.analisesEmAndamento.entries());
            
            // Limpar o Map primeiro para evitar re-entrada
            this.analisesEmAndamento.clear();
            
            // Agora abortar e limpar cada um
            controllers.forEach(([pedido, controller]) => {
                console.log(`  → Abortando análise do pedido ${pedido}`);
                controller.abort();
                // Forçar limpeza imediata do botão
                const btn = document.querySelector(`.btn-analisar-ruptura[data-pedido="${pedido}"]`);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-box me-1"></i>Verificar Estoque';
                    btn.className = 'btn btn-sm btn-outline-info btn-analisar-ruptura';
                }
            });
        }
    }
    
    /**
     * Limpa o estado de análise em andamento de um pedido
     */
    limparAnaliseEmAndamento(numPedido) {
        const btn = document.querySelector(`.btn-analisar-ruptura[data-pedido="${numPedido}"]`);
        if (btn && btn.disabled) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-box me-1"></i>Verificar Estoque';
            btn.className = 'btn btn-sm btn-outline-info btn-analisar-ruptura';
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
            
            // Adicionar listener
            const btn = btnContainer.querySelector('.btn-analisar-ruptura');
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                // Se já tem análise em andamento para este pedido, cancelar
                if (this.analisesEmAndamento.has(numPedido)) {
                    console.log(`🔄 Clique duplo detectado - cancelando análise do pedido ${numPedido}`);
                    const controller = this.analisesEmAndamento.get(numPedido);
                    controller.abort();
                    this.analisesEmAndamento.delete(numPedido);
                    this.limparAnaliseEmAndamento(numPedido);
                    return;
                }
                
                this.analisarRuptura(numPedido, btn);
            });
            
            botoesAdicionados++;
        });
        
        console.log(`✅ RupturaEstoqueManager: ${botoesAdicionados} botões adicionados`);
    }
    
    /**
     * Analisa ruptura de estoque
     */
    async analisarRuptura(numPedido, btnElement) {
        console.log(`🔍 Analisando ruptura do pedido ${numPedido}...`);
        
        // Cancelar análise anterior deste pedido se existir
        if (this.analisesEmAndamento.has(numPedido)) {
            console.log(`🔄 Cancelando análise anterior do pedido ${numPedido}`);
            const controllerAnterior = this.analisesEmAndamento.get(numPedido);
            controllerAnterior.abort();
            this.limparAnaliseEmAndamento(numPedido);
        }
        
        // Criar novo AbortController para esta análise
        const abortController = new AbortController();
        this.analisesEmAndamento.set(numPedido, abortController);
        
        // Salvar referência do botão para restaurar depois
        const htmlOriginal = btnElement.innerHTML;
        const classOriginal = btnElement.className;
        
        try {
            // Mostrar loading
            btnElement.disabled = true;
            btnElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analisando...';
            
            // Configurar timeout curto para detecção rápida de cancelamento
            const timeoutId = setTimeout(() => {
                if (!abortController.signal.aborted) {
                    console.log(`⏱️ Análise do pedido ${numPedido} ainda em andamento...`);
                }
            }, 100);
            
            // Criar Promise que rejeita imediatamente quando o sinal é abortado
            const abortPromise = new Promise((_, reject) => {
                if (abortController.signal.aborted) {
                    reject(new DOMException('Já cancelado', 'AbortError'));
                }
                abortController.signal.addEventListener('abort', () => {
                    console.log(`🛑 Sinal de abort recebido para pedido ${numPedido}`);
                    reject(new DOMException('Análise interrompida', 'AbortError'));
                });
            });
            
            // EVIDÊNCIA: Rotas confirmadas via Python - /carteira/api/ruptura/...
            const fetchPromise = fetch(`/carteira/api/ruptura/analisar-pedido/${numPedido}`, {
                signal: abortController.signal, // Passar o signal para permitir cancelamento
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            // Race entre fetch e abort - o que acontecer primeiro vence
            const response = await Promise.race([fetchPromise, abortPromise]);
            
            clearTimeout(timeoutId);
            
            // Verificar se foi cancelado ANTES de processar resposta
            if (abortController.signal.aborted) {
                console.log(`⚠️ Análise do pedido ${numPedido} foi cancelada antes da resposta`);
                btnElement.disabled = false;
                btnElement.innerHTML = htmlOriginal;
                btnElement.className = classOriginal;
                return;
            }
            
            const data = await response.json();
            
            // Verificar novamente após parse do JSON
            if (abortController.signal.aborted) {
                console.log(`⚠️ Análise do pedido ${numPedido} foi cancelada após resposta`);
                btnElement.disabled = false;
                btnElement.innerHTML = htmlOriginal;
                btnElement.className = classOriginal;
                return;
            }
            
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
            
            // Atualizar visual do botão
            const criticidade = data.resumo?.criticidade || 'MEDIA';
            const cores = {
                'CRITICA': 'btn-danger',
                'ALTA': 'btn-warning',
                'MEDIA': 'btn-info',
                'BAIXA': 'btn-secondary'
            };
            
            btnElement.disabled = false;
            btnElement.className = `btn btn-sm ${cores[criticidade]}`;
            btnElement.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i> 
                ${data.resumo.qtd_itens_ruptura} item(s)
            `;
            btnElement.title = `${data.resumo.percentual_ruptura}% em ruptura`;
            
            // Remover da lista de análises em andamento após sucesso
            this.analisesEmAndamento.delete(numPedido);
            
        } catch (error) {
            // Verificar se foi cancelado (não é erro real)
            if (error.name === 'AbortError' || error.message?.includes('interrompida') || error.message?.includes('cancelado')) {
                console.log(`✅ Análise do pedido ${numPedido} interrompida para priorizar ação do usuário`);
                // Restaurar botão ao estado original IMEDIATAMENTE
                btnElement.disabled = false;
                btnElement.innerHTML = htmlOriginal;
                btnElement.className = classOriginal;
                btnElement.title = 'Verificar disponibilidade de estoque';
                
                // Re-lançar o erro para que seja tratado no nível superior
                throw error;
            } else {
                console.error('❌ Erro ao analisar ruptura:', error);
                btnElement.disabled = false;
                btnElement.innerHTML = '<i class="fas fa-times"></i> Erro';
                btnElement.className = 'btn btn-sm btn-danger';
                btnElement.title = `Erro: ${error.message}`;
                
                // Mostrar erro ao usuário apenas se não for cancelamento
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
            
            // Sempre remover da lista de análises em andamento
            this.analisesEmAndamento.delete(numPedido);
        } finally {
            // Garantir que sempre remove do Map em caso de qualquer saída
            this.analisesEmAndamento.delete(numPedido);
        }
    }
    
    /**
     * Mostra modal com detalhes da ruptura
     */
    mostrarModalRuptura(data) {
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
        
        // Título
        document.getElementById('modalRupturaTitulo').innerHTML = `
            Análise de Ruptura - Pedido ${resumo.num_pedido}
            <span class="badge bg-${cores[resumo.criticidade]}">
                ${resumo.criticidade}
            </span>
        `;
        
        // Resumo
        document.getElementById('modalRupturaResumo').innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <strong>% em Ruptura:</strong> 
                    <span class="text-danger">${resumo.percentual_ruptura}%</span>
                </div>
                <div class="col-md-6">
                    <strong>Itens Afetados:</strong> 
                    ${resumo.qtd_itens_ruptura} de ${resumo.total_itens}
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-md-6">
                    <strong>Valor Total:</strong> 
                    R$ ${this.formatarMoeda(resumo.valor_total_pedido)}
                </div>
                <div class="col-md-6">
                    <strong>Valor em Risco:</strong> 
                    <span class="text-danger">
                        R$ ${this.formatarMoeda(resumo.valor_com_ruptura)}
                    </span>
                </div>
            </div>
        `;
        
        // Tabela de itens
        const tbody = document.getElementById('modalRupturaItens');
        tbody.innerHTML = '';
        
        data.itens.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.cod_produto}</td>
                <td>${item.nome_produto}</td>
                <td class="text-end">${this.formatarNumero(item.qtd_saldo)}</td>
                <td class="text-end">${this.formatarNumero(item.estoque_min_d7)}</td>
                <td class="text-end text-danger fw-bold">
                    ${this.formatarNumero(item.ruptura_qtd)}
                </td>
                <td class="text-center">
                    ${item.data_producao ? `
                        <span class="badge bg-success">
                            ${this.formatarData(item.data_producao)}<br>
                            Qtd: ${this.formatarNumero(item.qtd_producao)}
                        </span>
                    ` : '<span class="text-muted">-</span>'}
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        // Mostrar modal (Bootstrap 5)
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
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
        return (valor || 0).toFixed(3).replace('.', ',');
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
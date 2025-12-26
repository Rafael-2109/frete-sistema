/**
 * Addon de Workers para Sistema de Ruptura
 * Trabalha em conjunto com ruptura-estoque.js existente
 * NÃO modifica o comportamento atual, apenas adiciona funcionalidade de workers
 */

class RupturaWorkerAddon {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.offset = 0;
        this.pollingInterval = null;
        this.pedidosProcessados = new Set();
        this.modoWorkerAtivo = false;
        this.tentativasReconexao = 0;
        this.maxTentativas = 3;
        
        console.log('🔧 RupturaWorkerAddon: Inicializando addon de workers...');
        this.verificarDisponibilidade();
    }
    
    /**
     * Verifica se deve ativar modo worker
     */
    verificarDisponibilidade() {
        // Verificar flag global ou configuração
        const useWorkers = window.RUPTURA_USE_WORKERS || 
                          document.querySelector('meta[name="ruptura-workers"]')?.content === 'true';
        
        if (useWorkers) {
            console.log('✅ Modo Worker ATIVADO');
            this.inicializar();
        } else {
            console.log('ℹ️ Modo Worker desativado - usando modo padrão');
        }
    }
    
    /**
     * Inicializa o addon
     */
    async inicializar() {
        // Aguardar o RupturaEstoqueManager original carregar
        const aguardarManager = setInterval(() => {
            if (window.rupturaManager) {
                clearInterval(aguardarManager);
                console.log('✅ RupturaEstoqueManager detectado, integrando workers...');
                this.integrarComManagerExistente();
            }
        }, 100);
        
        // Timeout de 5 segundos
        setTimeout(() => {
            clearInterval(aguardarManager);
            if (!window.rupturaManager) {
                console.warn('⚠️ RupturaEstoqueManager não encontrado, workers não serão ativados');
            }
        }, 5000);
    }
    
    /**
     * Integra com o RupturaEstoqueManager existente
     */
    integrarComManagerExistente() {
        // Interceptar a função de análise automática
        if (window.rupturaManager && window.rupturaManager.iniciarAnalisesAutomaticas) {
            // Salvar função original
            this.analisarAutomaticaOriginal = window.rupturaManager.iniciarAnalisesAutomaticas.bind(window.rupturaManager);
            
            // Substituir por versão com workers
            window.rupturaManager.iniciarAnalisesAutomaticas = () => {
                console.log('🔄 Redirecionando para processamento com workers...');
                this.iniciarProcessamentoWorkers();
            };
        }
        
        // Adicionar indicador visual de modo worker
        this.adicionarIndicadorWorker();
        
        // Iniciar processamento com workers se a página já carregou
        if (document.readyState === 'complete') {
            this.iniciarProcessamentoWorkers();
        }
    }
    
    /**
     * Adiciona indicador visual de que workers estão ativos
     */
    adicionarIndicadorWorker() {
        const indicator = document.createElement('div');
        indicator.id = 'ruptura-worker-indicator';
        indicator.innerHTML = `
            <div style="
                position: fixed;
                top: 70px;
                right: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 8px 15px;
                border-radius: 20px;
                font-size: 0.85rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                z-index: 1000;
                display: flex;
                align-items: center;
                gap: 8px;
            ">
                <span style="
                    width: 8px;
                    height: 8px;
                    background: #00ff00;
                    border-radius: 50%;
                    animation: pulse 1.5s infinite;
                "></span>
                <span>Workers Ativos (2)</span>
            </div>
        `;
        
        // Adicionar animação
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {
                0% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(1.2); }
                100% { opacity: 1; transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(indicator);
    }
    
    /**
     * Coleta todos os pedidos da tabela
     */
    coletarPedidos() {
        const pedidos = [];
        const rows = document.querySelectorAll('tr.pedido-row');
        
        rows.forEach(row => {
            const numPedido = row.dataset.pedido;
            if (numPedido) {
                pedidos.push(numPedido);
                // Adicionar loading aos botões
                const btn = row.querySelector('.btn-analisar-ruptura');
                if (btn) {
                    btn.disabled = true;
                    btn.innerHTML = '<i class="fas fa-cloud-upload-alt me-1"></i>Enviando...';
                }
            }
        });
        
        console.log(`📦 ${pedidos.length} pedidos coletados para processamento`);
        return pedidos;
    }
    
    /**
     * Inicia processamento com workers
     */
    async iniciarProcessamentoWorkers() {
        if (this.modoWorkerAtivo) {
            console.log('⚠️ Processamento com workers já está ativo');
            return;
        }
        
        this.modoWorkerAtivo = true;
        const pedidos = this.coletarPedidos();
        
        if (pedidos.length === 0) {
            console.log('Nenhum pedido para processar');
            this.modoWorkerAtivo = false;
            return;
        }
        
        // Mostrar progresso
        this.mostrarProgresso(pedidos.length);
        
        try {
            // Enviar para workers
            const response = await fetch('/carteira/api/ruptura/worker/iniciar-processamento', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pedidos: pedidos,
                    session_id: this.sessionId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`✅ ${data.total_pedidos} pedidos enviados para ${data.workers} workers`);
                console.log(`📋 Sessão: ${data.session_id}`);
                console.log(`📦 Dividido em ${data.lotes} lotes`);
                
                // Iniciar polling para buscar resultados
                this.iniciarPolling();
            } else {
                throw new Error(data.error || 'Erro ao iniciar processamento');
            }
            
        } catch (error) {
            console.error('❌ Erro ao iniciar workers:', error);
            this.mostrarErro(error.message);
            
            // Fallback para modo normal se workers falharem
            if (this.tentativasReconexao < this.maxTentativas) {
                this.tentativasReconexao++;
                console.log(`🔄 Tentativa ${this.tentativasReconexao}/${this.maxTentativas} de reconexão...`);
                setTimeout(() => this.iniciarProcessamentoWorkers(), 3000);
            } else {
                console.log('⚠️ Workers indisponíveis, voltando ao modo padrão');
                this.voltarModoNormal();
            }
        }
    }
    
    /**
     * Inicia polling para buscar resultados
     */
    iniciarPolling() {
        // Buscar imediatamente
        this.buscarResultados();
        
        // Continuar buscando a cada 2 segundos
        this.pollingInterval = setInterval(() => {
            this.buscarResultados();
        }, 2000);
    }
    
    /**
     * Busca resultados dos workers
     */
    async buscarResultados() {
        try {
            const response = await fetch(
                `/carteira/api/ruptura/worker/buscar-resultados/${this.sessionId}?offset=${this.offset}`
            );
            
            const data = await response.json();
            
            if (data.success && data.resultados && data.resultados.length > 0) {
                console.log(`📥 Recebidos ${data.novos_resultados} novos resultados`);
                
                // Processar cada resultado
                data.resultados.forEach(resultado => {
                    this.processarResultado(resultado);
                });
                
                // Atualizar offset
                this.offset = data.offset_novo;
                
                // Atualizar progresso
                this.atualizarProgresso(data.progresso, data.total_processados, data.total_esperado);
                
                // Se completo, parar polling
                if (data.completo) {
                    console.log('✅ Processamento completo!');
                    this.finalizarProcessamento();
                }
            }
            
        } catch (error) {
            console.error('❌ Erro ao buscar resultados:', error);
        }
    }
    
    /**
     * Processa resultado individual
     */
    processarResultado(resultado) {
        const numPedido = resultado.num_pedido || resultado.resumo?.num_pedido;
        if (!numPedido) return;
        
        // Evitar duplicatas
        if (this.pedidosProcessados.has(numPedido)) return;
        this.pedidosProcessados.add(numPedido);
        
        // Buscar botão do pedido
        const row = document.querySelector(`tr[data-pedido="${numPedido}"]`);
        if (!row) return;
        
        const btn = row.querySelector('.btn-analisar-ruptura');
        if (!btn) return;
        
        // Atualizar visual do botão usando o formato do sistema atual
        btn.disabled = false;
        
        if (resultado.pedido_ok) {
            // Pedido OK
            btn.className = 'btn btn-sm btn-success btn-analisar-ruptura';
            btn.innerHTML = '<i class="fas fa-check"></i> Pedido OK';
            btn.title = 'Todos os itens disponíveis';
        } else if (resultado.resumo) {
            // Pedido com ruptura
            const criticidade = resultado.resumo.criticidade || 'MEDIA';
            const cores = {
                'CRITICA': 'btn-danger',
                'ALTA': 'btn-warning',
                'MEDIA': 'btn-info',
                'BAIXA': 'btn-secondary'
            };
            
            const percentualDisp = Math.round(resultado.percentual_disponibilidade || resultado.resumo.percentual_disponibilidade || 0);
            const dataDisp = resultado.data_disponibilidade_total || resultado.resumo.data_disponibilidade_total;
            
            let textoData = 'Total Não Disp.';
            if (dataDisp && dataDisp !== 'null' && dataDisp !== null) {
                const [ano, mes, dia] = dataDisp.split('-');
                textoData = `Total Disp. ${dia}/${mes}`;
            }
            
            btn.className = `btn btn-sm ${cores[criticidade]} btn-analisar-ruptura`;
            btn.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i> 
                Disp. ${percentualDisp}% | ${textoData}
            `;
            btn.title = `${resultado.resumo.qtd_itens_disponiveis} de ${resultado.resumo.total_itens} itens disponíveis`;
            
            // Adicionar dados ao botão para o modal funcionar
            btn.dataset.resultado = JSON.stringify(resultado);
        } else {
            // Erro ou sem dados
            btn.className = 'btn btn-sm btn-secondary btn-analisar-ruptura';
            btn.innerHTML = '<i class="fas fa-question"></i> Verificar';
        }
        
        // Manter o comportamento de clique original
        // O RupturaEstoqueManager original cuidará do modal
    }
    
    /**
     * Mostra barra de progresso
     */
    mostrarProgresso(totalPedidos) {
        // Remover progresso anterior se existir
        const progressoAnterior = document.getElementById('ruptura-worker-progress');
        if (progressoAnterior) progressoAnterior.remove();
        
        const progresso = document.createElement('div');
        progresso.id = 'ruptura-worker-progress';
        progresso.innerHTML = `
            <div style="
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: white;
                border: 2px solid #667eea;
                border-radius: 10px;
                padding: 15px 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                z-index: 1050;
                min-width: 350px;
            ">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <i class="fas fa-cog fa-spin text-secondary-color" style="margin-right: 10px;"></i>
                    <strong>Processando com Workers</strong>
                </div>
                <div class="progress" style="height: 25px; margin-bottom: 5px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" 
                         style="width: 0%; background: var(--bs-secondary-bg);">
                        0%
                    </div>
                </div>
                <small class="text-muted">
                    <span id="ruptura-progress-text">Iniciando processamento de ${totalPedidos} pedidos...</span>
                </small>
            </div>
        `;
        document.body.appendChild(progresso);
    }
    
    /**
     * Atualiza progresso
     */
    atualizarProgresso(percentual, processados, total) {
        const barra = document.querySelector('#ruptura-worker-progress .progress-bar');
        const texto = document.getElementById('ruptura-progress-text');
        
        if (barra) {
            barra.style.width = `${percentual}%`;
            barra.textContent = `${Math.round(percentual)}%`;
        }
        
        if (texto) {
            texto.textContent = `Processados: ${processados} de ${total} pedidos (2 workers ativos)`;
        }
    }
    
    /**
     * Finaliza processamento
     */
    finalizarProcessamento() {
        // Parar polling
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        
        // Atualizar progresso para 100%
        const barra = document.querySelector('#ruptura-worker-progress .progress-bar');
        if (barra) {
            barra.style.width = '100%';
            barra.textContent = '100%';
            barra.classList.remove('progress-bar-animated');
            barra.classList.add('bg-success');
        }
        
        // Remover progresso após 3 segundos
        setTimeout(() => {
            const progresso = document.getElementById('ruptura-worker-progress');
            if (progresso) {
                progresso.style.animation = 'fadeOut 0.5s';
                setTimeout(() => progresso.remove(), 500);
            }
        }, 3000);
        
        // Limpar cache da sessão
        this.limparCache();
        
        // Reset
        this.modoWorkerAtivo = false;
        this.offset = 0;
        this.pedidosProcessados.clear();
        
        console.log('✅ Processamento com workers finalizado');
    }
    
    /**
     * Limpa cache da sessão
     */
    async limparCache() {
        try {
            await fetch('/carteira/api/ruptura/worker/limpar-cache', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: this.sessionId })
            });
        } catch (error) {
            console.error('Erro ao limpar cache:', error);
        }
    }
    
    /**
     * Volta ao modo normal (sem workers)
     */
    voltarModoNormal() {
        // Restaurar função original
        if (this.analisarAutomaticaOriginal && window.rupturaManager) {
            window.rupturaManager.iniciarAnalisesAutomaticas = this.analisarAutomaticaOriginal;
            // Chamar função original
            this.analisarAutomaticaOriginal();
        }
        
        // Remover indicador
        const indicator = document.getElementById('ruptura-worker-indicator');
        if (indicator) indicator.remove();
        
        // Limpar progresso
        const progresso = document.getElementById('ruptura-worker-progress');
        if (progresso) progresso.remove();
        
        this.modoWorkerAtivo = false;
    }
    
    /**
     * Mostra erro
     */
    mostrarErro(mensagem) {
        const erro = document.createElement('div');
        erro.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: #dc3545;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 2000;
            max-width: 400px;
        `;
        erro.innerHTML = `
            <strong>⚠️ Erro nos Workers</strong><br>
            <small>${mensagem}</small>
        `;
        document.body.appendChild(erro);
        
        setTimeout(() => erro.remove(), 5000);
    }
    
    /**
     * Gera ID único de sessão
     */
    generateSessionId() {
        return 'worker_session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
}

// Adicionar animação CSS se não existir
if (!document.getElementById('ruptura-worker-styles')) {
    const styles = document.createElement('style');
    styles.id = 'ruptura-worker-styles';
    styles.textContent = `
        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }
    `;
    document.head.appendChild(styles);
}

// Inicializar addon quando DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    // Aguardar um pouco para garantir que ruptura-estoque.js carregou
    setTimeout(() => {
        console.log('🚀 Inicializando RupturaWorkerAddon...');
        window.rupturaWorkerAddon = new RupturaWorkerAddon();
    }, 500);
});
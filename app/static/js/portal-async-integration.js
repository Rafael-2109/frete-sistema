/**
 * INTEGRAÇÃO ASSÍNCRONA PARA PORTAIS DE AGENDAMENTO
 * Substitui chamadas síncronas por assíncronas com feedback em tempo real
 *
 * @author Sistema de Fretes
 * @version 2.0 - Com Redis Queue
 */

// ========================================
// FUNÇÕES AUXILIARES (DEVEM VIR PRIMEIRO)
// ========================================

function getCSRFToken() {
    // Tentar vários métodos para pegar o CSRF token
    return document.querySelector('[name=csrf_token]')?.value ||
           document.querySelector('[name=csrf-token]')?.value ||
           document.querySelector('meta[name="csrf-token"]')?.content ||
           '';
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ========================================
// CONFIGURAÇÃO GLOBAL
// ========================================

window.PortalAsync = {
    // URLs dos endpoints
    endpoints: {
        solicitar: '/portal/api/solicitar-agendamento-async',
        solicitarNF: '/portal/api/solicitar-agendamento-nf-async', // Versão async para NF
        status: '/portal/api/status-job/',
        reprocessar: '/portal/api/reprocessar-integracao/'
    },

    // Configurações de polling otimizadas
    polling: {
        maxTentativas: 40,       // ~2 minutos no total (40 * 3s = 120s)
        intervalo: 3000,         // 3 segundos entre verificações
        intervaloInicial: 20000, // Aguarda 20 segundos antes de começar
        mostrarNotificacao: true // Mostrar notificação discreta
    }
};

// ========================================
// FUNÇÕES DE NOTIFICAÇÃO DISCRETA (CANTO SUPERIOR DIREITO)
// ========================================

function mostrarNotificacaoDiscreta(titulo, mensagem, tipo = 'info') {
    // Remover notificação antiga se existir
    const notificacaoAntiga = document.getElementById('portal-notificacao-discreta');
    if (notificacaoAntiga) {
        notificacaoAntiga.remove();
    }

    // Cores por tipo
    const cores = {
        info: '#17a2b8',
        success: '#28a745',
        warning: '#ffc107',
        error: '#dc3545',
        processing: '#007bff'
    };

    // Criar nova notificação
    const notificacao = document.createElement('div');
    notificacao.id = 'portal-notificacao-discreta';
    notificacao.className = 'portal-notificacao-discreta';
    notificacao.innerHTML = `
        <div class="notificacao-header" style="background: ${cores[tipo]};">
            <span class="notificacao-titulo">${titulo}</span>
            <button class="notificacao-fechar" onclick="esconderNotificacaoDiscreta()">×</button>
        </div>
        <div class="notificacao-body">
            <div class="notificacao-mensagem">${mensagem}</div>
            <div class="notificacao-spinner">
                <div class="spinner-pequeno"></div>
            </div>
        </div>
        <div class="notificacao-progresso">
            <div class="notificacao-progresso-bar" style="width: 0%"></div>
        </div>
    `;
    document.body.appendChild(notificacao);

    // Adicionar CSS se não existir
    if (!document.getElementById('portal-notificacao-styles')) {
        const style = document.createElement('style');
        style.id = 'portal-notificacao-styles';
        style.textContent = `
            .portal-notificacao-discreta {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 320px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 9999;
                animation: slideInRight 0.3s ease-out;
                font-size: 14px;
            }
            .notificacao-header {
                padding: 10px 15px;
                border-radius: 8px 8px 0 0;
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .notificacao-titulo {
                font-weight: 600;
                font-size: 14px;
            }
            .notificacao-fechar {
                background: none;
                border: none;
                color: white;
                font-size: 20px;
                cursor: pointer;
                padding: 0;
                width: 20px;
                height: 20px;
                line-height: 18px;
                opacity: 0.8;
                transition: opacity 0.2s;
            }
            .notificacao-fechar:hover {
                opacity: 1;
            }
            .notificacao-body {
                padding: 12px 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .notificacao-mensagem {
                flex: 1;
                color: #495057;
                font-size: 13px;
            }
            .notificacao-spinner {
                flex-shrink: 0;
            }
            .spinner-pequeno {
                width: 16px;
                height: 16px;
                border: 2px solid #e9ecef;
                border-top-color: #007bff;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            .notificacao-progresso {
                height: 3px;
                background: #e9ecef;
                border-radius: 0 0 8px 8px;
                overflow: hidden;
            }
            .notificacao-progresso-bar {
                height: 100%;
                background: linear-gradient(90deg, #007bff, #28a745);
                transition: width 0.3s ease;
            }
            @keyframes slideInRight {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(400px);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

function atualizarNotificacaoDiscreta(status, tentativa, maxTentativas) {
    const notificacao = document.getElementById('portal-notificacao-discreta');
    if (!notificacao) return;

    const mensagemEl = notificacao.querySelector('.notificacao-mensagem');
    const progressBar = notificacao.querySelector('.notificacao-progresso-bar');

    // Atualizar mensagem baseada no status
    const mensagens = {
        'queued': 'Na fila de processamento...',
        'started': 'Processando agendamento...',
        'processing': 'Enviando para o portal...',
        'finished': 'Agendamento concluído!',
        'failed': 'Erro no processamento'
    };

    if (mensagemEl) {
        mensagemEl.textContent = mensagens[status] || `Verificando... (${tentativa}/${maxTentativas})`;
    }

    // Atualizar barra de progresso
    if (progressBar) {
        const porcentagem = Math.min(Math.round((tentativa / maxTentativas) * 100), 95);
        progressBar.style.width = porcentagem + '%';
    }
}

function esconderNotificacaoDiscreta() {
    const notificacao = document.getElementById('portal-notificacao-discreta');
    if (notificacao) {
        notificacao.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => notificacao.remove(), 300);
    }
}

function mostrarSucessoPortal(titulo, mensagem, referencia) {
    // Usar SweetAlert2 se disponível
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'success',
            title: titulo,
            html: `
                <p>${mensagem}</p>
                <small>Referência: ${referencia}</small>
                <div class="mt-3">
                    <span class="badge bg-success">Processado via Redis Queue</span>
                </div>
            `,
            confirmButtonText: 'OK',
            timer: 5000,
            timerProgressBar: true
        });
    } else {
        alert(`✅ ${titulo}\n${mensagem}\nRef: ${referencia}`);
    }
}

function mostrarErroPortal(titulo, mensagem) {
    // Usar SweetAlert2 se disponível
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'error',
            title: titulo,
            html: `
                <p>${mensagem}</p>
                <div class="mt-3">
                    <button class="btn btn-sm btn-warning" onclick="verificarStatusFilas()">
                        📊 Ver Status das Filas
                    </button>
                </div>
            `,
            confirmButtonText: 'OK'
        });
    } else {
        alert(`❌ ${titulo}\n${mensagem}`);
    }
}

// ========================================
// FUNÇÃO PRINCIPAL
// ========================================

window.agendarNoPortalAtacadaoAsync = async function(entregaId, numeroNf) {
    console.log('🚀 Iniciando agendamento assíncrono para NF:', numeroNf);
    
    // Pegar dados do formulário (se existir)
    const dataAgendamento = document.getElementById('data-agendamento-portal')?.value || 
                           document.getElementById('data-agendamento')?.value ||
                           new Date().toISOString().split('T')[0];
    
    const horaAgendamento = document.getElementById('hora-agendamento-portal')?.value ||
                           document.getElementById('hora-agendamento')?.value;
    
    // Não mostrar modal intrusivo, apenas log
    console.log('📤 Enviando agendamento para processamento...');
    
    try {
        // 1. Enviar para fila assíncrona (nova rota)
        const response = await fetch('/portal/api/solicitar-agendamento-nf-async', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                numero_nf: numeroNf,
                entrega_id: entregaId,
                data_agendamento: dataAgendamento,
                hora_agendamento: horaAgendamento
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Erro ao enviar agendamento');
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Erro ao processar agendamento');
        }
        
        console.log('✅ Job enfileirado:', data.job_id);
        // Notificação discreta ao invés de modal intrusivo
        
        // 2. Iniciar monitoramento do status
        const resultado = await monitorarStatusJob(
            data.job_id,
            data.integracao_id,
            numeroNf
        );
        
        // 3. Processar resultado final
        if (resultado.status === 'finished' && resultado.resultado?.success) {
            mostrarSucessoPortal(
                `Agendamento criado com sucesso!`,
                `Protocolo: ${resultado.resultado.protocolo || 'Aguardando confirmação'}`,
                numeroNf
            );
            
            // Recarregar página após 3 segundos
            setTimeout(() => {
                location.reload();
            }, 3000);
            
        } else if (resultado.status === 'failed') {
            throw new Error(resultado.error || 'Agendamento falhou no processamento');
        }
        
        return resultado;
        
    } catch (error) {
        console.error('❌ Erro no agendamento:', error);
        mostrarErroPortal('Erro no Agendamento', error.message);
        throw error;
    } finally {
        // Limpar notificação se ainda estiver visível
        esconderNotificacaoDiscreta();
    }
};


// ========================================
// FUNÇÃO DE MONITORAMENTO COM FEEDBACK VISUAL
// ========================================

async function monitorarStatusJob(jobId, integracaoId, referencia) {
    const maxTentativas = PortalAsync.polling.maxTentativas;
    const intervalo = PortalAsync.polling.intervalo;
    let tentativa = 0;
    
    // Mostrar notificação inicial discreta
    mostrarNotificacaoDiscreta('Agendamento enviado', 'Aguardando processamento...', 'info');
    
    // Aguardar período inicial antes de começar polling
    console.log(`⏳ Aguardando ${PortalAsync.polling.intervaloInicial/1000}s antes de verificar status...`);
    await sleep(PortalAsync.polling.intervaloInicial);
    
    while (tentativa < maxTentativas) {
        tentativa++;
        
        try {
            const response = await fetch(`${PortalAsync.endpoints.status}${jobId}`);
            const data = await response.json();
            
            // Log reduzido - apenas mudanças de status
            if (tentativa === 1 || tentativa % 10 === 0) {
                console.log(`[Verificação ${tentativa}/${maxTentativas}] Status: ${data.status}`);
            }
            
            // Atualizar notificação discreta
            atualizarNotificacaoDiscreta(data.status, tentativa, maxTentativas);
            
            // Verificar se finalizou
            if (['finished', 'failed'].includes(data.status)) {
                esconderNotificacaoDiscreta();
                return data;
            }
            
            // Aguardar próxima verificação
            await sleep(intervalo);
            
        } catch (error) {
            // Log de erro apenas a cada 5 tentativas
            if (tentativa % 5 === 0) {
                console.warn(`Status check ${tentativa}: ${error.message}`);
            }
        }
    }
    
    esconderNotificacaoDiscreta();
    // Timeout
    throw new Error('Timeout: Agendamento demorou muito para processar (mais de 2 minutos)');
}

// ========================================
// FUNÇÕES DE NOTIFICAÇÃO DISCRETA (CANTO SUPERIOR DIREITO)
// ========================================

function mostrarNotificacaoDiscreta(titulo, mensagem, tipo = 'info') {
    // Remover notificação antiga se existir
    const notificacaoAntiga = document.getElementById('portal-notificacao-discreta');
    if (notificacaoAntiga) {
        notificacaoAntiga.remove();
    }
    
    // Cores por tipo
    const cores = {
        info: '#17a2b8',
        success: '#28a745',
        warning: '#ffc107',
        error: '#dc3545',
        processing: '#007bff'
    };
    
    // Criar nova notificação
    const notificacao = document.createElement('div');
    notificacao.id = 'portal-notificacao-discreta';
    notificacao.className = 'portal-notificacao-discreta';
    notificacao.innerHTML = `
        <div class="notificacao-header" style="background: ${cores[tipo]};">
            <span class="notificacao-titulo">${titulo}</span>
            <button class="notificacao-fechar" onclick="esconderNotificacaoDiscreta()">×</button>
        </div>
        <div class="notificacao-body">
            <div class="notificacao-mensagem">${mensagem}</div>
            <div class="notificacao-spinner">
                <div class="spinner-pequeno"></div>
            </div>
        </div>
        <div class="notificacao-progresso">
            <div class="notificacao-progresso-bar" style="width: 0%"></div>
        </div>
    `;
    document.body.appendChild(notificacao);
    
    // Adicionar CSS se não existir
    if (!document.getElementById('portal-notificacao-styles')) {
        const style = document.createElement('style');
        style.id = 'portal-notificacao-styles';
        style.textContent = `
            .portal-notificacao-discreta {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 320px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 9999;
                animation: slideInRight 0.3s ease-out;
                font-size: 14px;
            }
            .notificacao-header {
                padding: 10px 15px;
                border-radius: 8px 8px 0 0;
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .notificacao-titulo {
                font-weight: 600;
                font-size: 14px;
            }
            .notificacao-fechar {
                background: none;
                border: none;
                color: white;
                font-size: 20px;
                cursor: pointer;
                padding: 0;
                width: 20px;
                height: 20px;
                line-height: 18px;
                opacity: 0.8;
                transition: opacity 0.2s;
            }
            .notificacao-fechar:hover {
                opacity: 1;
            }
            .notificacao-body {
                padding: 12px 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .notificacao-mensagem {
                flex: 1;
                color: #495057;
                font-size: 13px;
            }
            .notificacao-spinner {
                flex-shrink: 0;
            }
            .spinner-pequeno {
                width: 16px;
                height: 16px;
                border: 2px solid #e9ecef;
                border-top-color: #007bff;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            .notificacao-progresso {
                height: 3px;
                background: #e9ecef;
                border-radius: 0 0 8px 8px;
                overflow: hidden;
            }
            .notificacao-progresso-bar {
                height: 100%;
                background: linear-gradient(90deg, #007bff, #28a745);
                transition: width 0.3s ease;
            }
            @keyframes slideInRight {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(400px);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

function atualizarNotificacaoDiscreta(status, tentativa, maxTentativas) {
    const notificacao = document.getElementById('portal-notificacao-discreta');
    if (!notificacao) return;
    
    const mensagemEl = notificacao.querySelector('.notificacao-mensagem');
    const progressBar = notificacao.querySelector('.notificacao-progresso-bar');
    
    // Atualizar mensagem baseada no status
    const mensagens = {
        'queued': 'Na fila de processamento...',
        'started': 'Processando agendamento...',
        'processing': 'Enviando para o portal...',
        'finished': 'Agendamento concluído!',
        'failed': 'Erro no processamento'
    };
    
    if (mensagemEl) {
        mensagemEl.textContent = mensagens[status] || `Verificando... (${tentativa}/${maxTentativas})`;
    }
    
    // Atualizar barra de progresso
    if (progressBar) {
        const porcentagem = Math.min(Math.round((tentativa / maxTentativas) * 100), 95);
        progressBar.style.width = porcentagem + '%';
    }
}

function esconderNotificacaoDiscreta() {
    const notificacao = document.getElementById('portal-notificacao-discreta');
    if (notificacao) {
        notificacao.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => notificacao.remove(), 300);
    }
}

// ========================================
// FUNÇÕES DE UI MELHORADAS (MANTIDAS PARA COMPATIBILIDADE)
// ========================================

function mostrarLoadingPortal(mensagem) {
    // Remover loader antigo se existir
    const loaderAntigo = document.getElementById('portal-async-loader');
    if (loaderAntigo) {
        loaderAntigo.remove();
    }
    
    // Criar novo loader
    const loader = document.createElement('div');
    loader.id = 'portal-async-loader';
    loader.className = 'portal-async-overlay';
    loader.innerHTML = `
        <div class="portal-async-content">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="sr-only">Processando...</span>
            </div>
            <h5 class="text-white mb-2">Agendamento Assíncrono</h5>
            <div class="portal-async-message">${mensagem}</div>
            <div class="progress mt-3" style="width: 300px; display: none;">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 0%"></div>
            </div>
            <small class="text-white-50 mt-2">Sistema processando em background...</small>
        </div>
    `;
    document.body.appendChild(loader);
    
    // Adicionar CSS se não existir
    if (!document.getElementById('portal-async-styles')) {
        const style = document.createElement('style');
        style.id = 'portal-async-styles';
        style.textContent = `
            .portal-async-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.85);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 99999;
                animation: fadeIn 0.3s;
            }
            .portal-async-content {
                text-align: center;
                padding: 30px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            .portal-async-message {
                color: white;
                font-size: 16px;
                margin-top: 10px;
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
}

function esconderLoadingPortal() {
    const loader = document.getElementById('portal-async-loader');
    if (loader) {
        loader.style.animation = 'fadeOut 0.3s';
        setTimeout(() => loader.remove(), 300);
    }
}

function atualizarProgressoPortal(status, tentativa, maxTentativas) {
    const loader = document.getElementById('portal-async-loader');
    if (!loader) return;
    
    const progressBar = loader.querySelector('.progress');
    const progress = loader.querySelector('.progress-bar');
    
    if (status === 'started' && progressBar && progress) {
        progressBar.style.display = 'block';
        const porcentagem = Math.min(Math.round((tentativa / maxTentativas) * 100), 95);
        progress.style.width = porcentagem + '%';
        progress.textContent = porcentagem + '%';
    }
}

function mostrarSucessoPortal(titulo, mensagem, referencia) {
    // Usar SweetAlert2 se disponível
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'success',
            title: titulo,
            html: `
                <p>${mensagem}</p>
                <small>Referência: ${referencia}</small>
                <div class="mt-3">
                    <span class="badge bg-success">Processado via Redis Queue</span>
                </div>
            `,
            confirmButtonText: 'OK',
            timer: 5000,
            timerProgressBar: true
        });
    } else {
        alert(`✅ ${titulo}\n${mensagem}\nRef: ${referencia}`);
    }
}

function mostrarErroPortal(titulo, mensagem) {
    // Usar SweetAlert2 se disponível
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'error',
            title: titulo,
            html: `
                <p>${mensagem}</p>
                <div class="mt-3">
                    <button class="btn btn-sm btn-warning" onclick="verificarStatusFilas()">
                        📊 Ver Status das Filas
                    </button>
                </div>
            `,
            confirmButtonText: 'OK'
        });
    } else {
        alert(`❌ ${titulo}\n${mensagem}`);
    }
}


// ========================================
// VERIFICADOR DE STATUS DAS FILAS
// ========================================

window.verificarStatusFilas = async function() {
    try {
        const response = await fetch('/portal/api/status-filas');
        const data = await response.json();
        
        if (data.success) {
            console.log('📊 Status das Filas:', data.filas);
            
            // Mostrar em modal se possível
            if (typeof Swal !== 'undefined') {
                let html = '<div class="text-start">';
                
                Object.entries(data.filas).forEach(([fila, status]) => {
                    html += `
                        <h6>${fila.toUpperCase()}</h6>
                        <ul>
                            <li>⏳ Pendentes: ${status.pendentes}</li>
                            <li>🔄 Em execução: ${status.em_execucao}</li>
                            <li>✅ Concluídos: ${status.concluidos}</li>
                            <li>❌ Falhados: ${status.falhados}</li>
                        </ul>
                    `;
                });
                
                html += '</div>';
                
                Swal.fire({
                    title: '📊 Status das Filas Redis',
                    html: html,
                    width: 600,
                    confirmButtonText: 'Fechar'
                });
            }
        }
    } catch (error) {
        console.error('Erro ao verificar filas:', error);
    }
};

// ========================================
// COMPATIBILIDADE - REDIRECIONAR ANTIGAS
// ========================================

// ========================================
// INICIALIZAÇÃO
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Sistema de Agendamento Assíncrono carregado');
    console.log('📦 Redis Queue habilitado para processamento em background');
    
    // Adicionar indicador visual de que o sistema assíncrono está ativo
    const indicator = document.createElement('div');
    indicator.innerHTML = `
        <span class="badge bg-success" style="position: fixed; bottom: 10px; right: 10px; z-index: 9999;">
            🚀 Async Mode
        </span>
    `;
    document.body.appendChild(indicator);
    
    // Remover após 5 segundos
    setTimeout(() => indicator.remove(), 5000);
});

console.log('Portal Async Integration v2.0 loaded');
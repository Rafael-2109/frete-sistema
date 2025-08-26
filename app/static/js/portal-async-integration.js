/**
 * INTEGRAÇÃO ASSÍNCRONA PARA PORTAIS DE AGENDAMENTO
 * Substitui chamadas síncronas por assíncronas com feedback em tempo real
 * 
 * @author Sistema de Fretes
 * @version 2.0 - Com Redis Queue
 */

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
    
    // Configurações de polling
    polling: {
        maxTentativas: 120,  // 2 minutos com intervalo de 1s
        intervalo: 1000,     // 1 segundo
        intervaloPrimeiro: 500  // 500ms para primeira verificação
    }
};

// ========================================
// FUNÇÃO PRINCIPAL - SUBSTITUI agendarNoPortalAtacadao
// ========================================

window.agendarNoPortalAtacadaoAsync = async function(entregaId, numeroNf) {
    console.log('🚀 Iniciando agendamento assíncrono para NF:', numeroNf);
    
    // Pegar dados do formulário (se existir)
    const dataAgendamento = document.getElementById('data-agendamento-portal')?.value || 
                           document.getElementById('data-agendamento')?.value ||
                           new Date().toISOString().split('T')[0];
    
    const horaAgendamento = document.getElementById('hora-agendamento-portal')?.value ||
                           document.getElementById('hora-agendamento')?.value;
    
    // Mostrar loading imediatamente
    mostrarLoadingPortal('Enviando agendamento para processamento...');
    
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
        mostrarLoadingPortal('Agendamento em processamento. Aguarde...');
        
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
        esconderLoadingPortal();
    }
};

// ========================================
// FUNÇÃO PARA WORKSPACE (SUBSTITUI agendarNoPortal)
// ========================================

window.agendarNoPortalAsync = async function(loteId, dataAgendamento) {
    console.log('🚀 Iniciando agendamento assíncrono para lote:', loteId);
    
    // Usar data fornecida ou data atual
    dataAgendamento = dataAgendamento || new Date().toISOString().split('T')[0];
    
    // Mostrar loading
    mostrarLoadingPortal('Enviando agendamento para processamento...');
    
    try {
        // 1. Enviar para fila assíncrona
        const response = await fetch('/portal/api/solicitar-agendamento-async', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                lote_id: loteId,
                data_agendamento: dataAgendamento,
                tipo_veiculo: '11'  // Default: Toco-Baú
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
        mostrarLoadingPortal('Agendamento em processamento. Aguarde...');
        
        // 2. Monitorar status
        const resultado = await monitorarStatusJob(
            data.job_id,
            data.integracao_id,
            loteId
        );
        
        // 3. Processar resultado
        if (resultado.status === 'finished' && resultado.resultado?.success) {
            mostrarSucessoPortal(
                `Agendamento criado com sucesso!`,
                `Protocolo: ${resultado.resultado.protocolo || 'Aguardando'}`,
                loteId
            );
            
            // Atualizar workspace se existir
            if (window.workspace) {
                await workspace.carregarDadosPedido();
            }
            
            // Recarregar após 3 segundos
            setTimeout(() => {
                location.reload();
            }, 3000);
            
        } else if (resultado.status === 'failed') {
            throw new Error(resultado.error || 'Agendamento falhou');
        }
        
        return resultado;
        
    } catch (error) {
        console.error('❌ Erro:', error);
        mostrarErroPortal('Erro no Agendamento', error.message);
        throw error;
    } finally {
        esconderLoadingPortal();
    }
};

// ========================================
// FUNÇÃO DE MONITORAMENTO COM FEEDBACK VISUAL
// ========================================

async function monitorarStatusJob(jobId, integracaoId, referencia) {
    const maxTentativas = PortalAsync.polling.maxTentativas;
    const intervalo = PortalAsync.polling.intervalo;
    let tentativa = 0;
    
    // Primeira verificação rápida
    await sleep(PortalAsync.polling.intervaloPrimeiro);
    
    while (tentativa < maxTentativas) {
        tentativa++;
        
        try {
            const response = await fetch(`${PortalAsync.endpoints.status}${jobId}`);
            const data = await response.json();
            
            console.log(`[${tentativa}/${maxTentativas}] Status: ${data.status}`);
            
            // Atualizar interface com progresso
            atualizarProgressoPortal(data.status, tentativa, maxTentativas);
            
            // Verificar se finalizou
            if (['finished', 'failed'].includes(data.status)) {
                return data;
            }
            
            // Mensagens específicas por status
            if (data.status === 'started') {
                mostrarLoadingPortal(`Processando agendamento... (${Math.round(tentativa/maxTentativas*100)}%)`);
            } else if (data.status === 'queued') {
                mostrarLoadingPortal(`Na fila aguardando processamento... (posição estimada)`);
            }
            
            // Aguardar próxima verificação
            await sleep(intervalo);
            
        } catch (error) {
            console.error(`Erro ao verificar status (tentativa ${tentativa}):`, error);
        }
    }
    
    // Timeout
    throw new Error('Timeout: Agendamento demorou muito para processar (mais de 2 minutos)');
}

// ========================================
// FUNÇÕES DE UI MELHORADAS
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
// FUNÇÕES AUXILIARES
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

// Substituir função antiga em listar_entregas.html
if (typeof agendarNoPortalAtacadao !== 'undefined') {
    console.log('🔄 Substituindo agendarNoPortalAtacadao por versão assíncrona');
    window.agendarNoPortalAtacadao = window.agendarNoPortalAtacadaoAsync;
}

// Substituir função antiga em workspace
if (typeof workspace !== 'undefined' && workspace.agendarNoPortal) {
    console.log('🔄 Substituindo workspace.agendarNoPortal por versão assíncrona');
    const originalAgendarNoPortal = workspace.agendarNoPortal.bind(workspace);
    workspace.agendarNoPortal = window.agendarNoPortalAsync;
}

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
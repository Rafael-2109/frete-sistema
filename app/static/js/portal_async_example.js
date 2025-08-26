/**
 * Exemplo de JavaScript para usar o sistema assíncrono de agendamento
 * Substitui a chamada síncrona pela assíncrona com polling de status
 */

// ========================================
// FUNÇÃO PRINCIPAL DE AGENDAMENTO ASSÍNCRONO
// ========================================

async function agendarLoteAsync(loteId, dataAgendamento, horaAgendamento = null) {
    try {
        // 1. Mostrar loading
        mostrarLoading('Enviando agendamento para processamento...');
        
        // 2. Fazer request assíncrono
        const response = await fetch('/portal/api/solicitar-agendamento-async', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                lote_id: loteId,
                data_agendamento: dataAgendamento,
                hora_agendamento: horaAgendamento,
                transportadora: 'Agregado',
                tipo_veiculo: '11'
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.message || 'Erro ao enviar agendamento');
        }
        
        // 3. Iniciar polling do status
        console.log(`✅ Job ${data.job_id} enfileirado!`);
        mostrarLoading('Agendamento em processamento. Aguarde...');
        
        // 4. Verificar status periodicamente
        const resultado = await verificarStatusJob(data.job_id);
        
        // 5. Processar resultado
        if (resultado.status === 'finished' && resultado.resultado?.success) {
            mostrarSucesso(
                `Agendamento criado com sucesso!<br>` +
                `Protocolo: ${resultado.resultado.protocolo}`
            );
        } else if (resultado.status === 'failed') {
            throw new Error(resultado.error || 'Agendamento falhou');
        }
        
        return resultado;
        
    } catch (error) {
        console.error('Erro no agendamento:', error);
        mostrarErro(`Erro: ${error.message}`);
        throw error;
    } finally {
        esconderLoading();
    }
}

// ========================================
// FUNÇÃO DE POLLING DE STATUS
// ========================================

async function verificarStatusJob(jobId, maxTentativas = 60, intervalo = 3000) {
    /**
     * Verifica o status do job periodicamente
     * @param {string} jobId - ID do job no Redis Queue
     * @param {number} maxTentativas - Máximo de tentativas (padrão: 60)
     * @param {number} intervalo - Intervalo entre tentativas em ms (padrão: 3s)
     */
    
    for (let tentativa = 0; tentativa < maxTentativas; tentativa++) {
        try {
            const response = await fetch(`/portal/api/status-job/${jobId}`);
            const data = await response.json();
            
            console.log(`[Tentativa ${tentativa + 1}/${maxTentativas}] Status: ${data.status}`);
            
            // Atualizar interface com status
            atualizarStatusUI(data.status, data.message);
            
            // Verificar se finalizou
            if (['finished', 'failed'].includes(data.status)) {
                return data;
            }
            
            // Aguardar antes da próxima tentativa
            await sleep(intervalo);
            
        } catch (error) {
            console.error(`Erro ao verificar status:`, error);
        }
    }
    
    throw new Error('Timeout: Agendamento demorou muito para processar');
}

// ========================================
// FUNÇÕES AUXILIARES DE UI
// ========================================

function mostrarLoading(mensagem) {
    const loader = document.getElementById('loader') || criarLoader();
    const textoLoader = loader.querySelector('.loader-text');
    if (textoLoader) {
        textoLoader.textContent = mensagem;
    }
    loader.style.display = 'block';
}

function esconderLoading() {
    const loader = document.getElementById('loader');
    if (loader) {
        loader.style.display = 'none';
    }
}

function mostrarSucesso(mensagem) {
    Swal.fire({
        icon: 'success',
        title: 'Sucesso!',
        html: mensagem,
        confirmButtonText: 'OK'
    });
}

function mostrarErro(mensagem) {
    Swal.fire({
        icon: 'error',
        title: 'Erro!',
        html: mensagem,
        confirmButtonText: 'OK'
    });
}

function atualizarStatusUI(status, mensagem) {
    const statusDiv = document.getElementById('status-agendamento');
    if (!statusDiv) return;
    
    const statusClasses = {
        'queued': 'alert-info',
        'started': 'alert-warning',
        'finished': 'alert-success',
        'failed': 'alert-danger'
    };
    
    const statusTextos = {
        'queued': '⏳ Na fila aguardando processamento...',
        'started': '🔄 Processando agendamento...',
        'finished': '✅ Agendamento concluído!',
        'failed': '❌ Erro no agendamento'
    };
    
    statusDiv.className = `alert ${statusClasses[status] || 'alert-secondary'}`;
    statusDiv.innerHTML = `
        <strong>${statusTextos[status] || status}</strong>
        ${mensagem ? `<br>${mensagem}` : ''}
    `;
}

function criarLoader() {
    const loader = document.createElement('div');
    loader.id = 'loader';
    loader.className = 'loader-overlay';
    loader.innerHTML = `
        <div class="loader-content">
            <div class="spinner-border text-primary" role="status">
                <span class="sr-only">Carregando...</span>
            </div>
            <div class="loader-text mt-3">Processando...</div>
        </div>
    `;
    document.body.appendChild(loader);
    
    // CSS inline para o loader
    const style = document.createElement('style');
    style.textContent = `
        .loader-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }
        .loader-content {
            text-align: center;
            color: white;
        }
        .loader-text {
            font-size: 18px;
            margin-top: 10px;
        }
    `;
    document.head.appendChild(style);
    
    return loader;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ========================================
// EXEMPLO DE USO
// ========================================

/*
// Em um botão ou formulário:
document.getElementById('btn-agendar').addEventListener('click', async () => {
    const loteId = document.getElementById('lote_id').value;
    const dataAgendamento = document.getElementById('data_agendamento').value;
    
    try {
        const resultado = await agendarLoteAsync(loteId, dataAgendamento);
        console.log('Resultado final:', resultado);
        
        // Atualizar a página ou tabela
        window.location.reload();
        
    } catch (error) {
        console.error('Erro no agendamento:', error);
    }
});
*/

// ========================================
// INTEGRAÇÃO COM DATATABLES
// ========================================

function adicionarBotaoAgendarAsync(tabela) {
    /**
     * Adiciona botão de agendamento assíncrono no DataTable
     */
    tabela.on('click', '.btn-agendar-async', async function() {
        const tr = $(this).closest('tr');
        const data = tabela.row(tr).data();
        
        const loteId = data.lote_id;
        const dataAgendamento = prompt('Data de agendamento (YYYY-MM-DD):');
        
        if (dataAgendamento) {
            try {
                await agendarLoteAsync(loteId, dataAgendamento);
                tabela.ajax.reload();
            } catch (error) {
                console.error('Erro:', error);
            }
        }
    });
}

// ========================================
// MONITORAMENTO DE FILAS
// ========================================

async function monitorarFilas() {
    /**
     * Mostra status das filas em tempo real
     */
    try {
        const response = await fetch('/portal/api/status-filas');
        const data = await response.json();
        
        if (data.success) {
            console.log('📊 Status das Filas:');
            Object.entries(data.filas).forEach(([fila, status]) => {
                console.log(`  ${fila}:`, status);
            });
        }
    } catch (error) {
        console.error('Erro ao monitorar filas:', error);
    }
}

// Atualizar status das filas a cada 10 segundos (opcional)
// setInterval(monitorarFilas, 10000);

// ========================================
// REPROCESSAMENTO DE ERROS
// ========================================

async function reprocessarIntegracao(integracaoId) {
    /**
     * Reprocessa uma integração que falhou
     */
    try {
        const response = await fetch(`/portal/api/reprocessar-integracao/${integracaoId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarSucesso('Integração enviada para reprocessamento');
            
            // Verificar status do novo job
            return await verificarStatusJob(data.job_id);
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('Erro ao reprocessar:', error);
        mostrarErro(`Erro: ${error.message}`);
    }
}

// Exportar funções para uso global
window.portalAsync = {
    agendarLoteAsync,
    verificarStatusJob,
    monitorarFilas,
    reprocessarIntegracao
};
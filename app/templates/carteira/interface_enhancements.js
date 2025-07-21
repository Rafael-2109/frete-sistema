/**
 * MELHORIAS NA INTERFACE PARA NOVA CONSTRAINT ÚNICA
 * Adiciona tratamento específico para conflitos de pré-separação
 */

/**
 * Trata erros específicos de constraint única
 */
function tratarErroConstraintUnica(errorMessage) {
    if (errorMessage.includes('uq_pre_separacao_contexto_unico') || 
        errorMessage.includes('UNIQUE constraint failed') ||
        errorMessage.includes('duplicate key value')) {
        
        return `❌ CONFLITO DE PRÉ-SEPARAÇÃO

🔍 Já existe uma pré-separação com esta combinação:
• Mesmo pedido e produto
• Mesma data de expedição  
• Mesmo agendamento
• Mesmo protocolo

💡 SOLUÇÕES:
1. Altere a data de expedição
2. Defina um agendamento diferente
3. Use um protocolo distinto
4. Edite a pré-separação existente`;
    }
    
    return errorMessage;
}

/**
 * Melhora o tratamento de erros na criação de pré-separação
 */
function aprimorarTratamentoErros() {
    // Interceptar erros de criação de pré-separação
    const originalFetch = window.fetch;
    
    window.fetch = async function(...args) {
        try {
            const response = await originalFetch.apply(this, args);
            
            // Se for API de pré-separação e houver erro
            if (args[0].includes('/criar-pre-separacao') && !response.ok) {
                const data = await response.clone().json();
                
                if (data.error) {
                    data.error = tratarErroConstraintUnica(data.error);
                }
                
                // Retornar response modificado
                return new Response(JSON.stringify(data), {
                    status: response.status,
                    statusText: response.statusText,
                    headers: response.headers
                });
            }
            
            return response;
            
        } catch (error) {
            throw error;
        }
    };
}

/**
 * Valida contexto único antes de criar pré-separação
 */
function validarContextoUnico(itemId, dataExpedicao, agendamento, protocolo) {
    // Buscar outras pré-separações na interface com mesmo contexto
    const linhas = document.querySelectorAll('tr[data-tipo-item="pre_separacao"]');
    
    for (const linha of linhas) {
        const expedicaoExistente = linha.querySelector('.data-expedicao-pre-separacao')?.value;
        const agendamentoExistente = linha.querySelector('.agendamento-pre-separacao')?.value || '';
        const protocoloExistente = linha.querySelector('.protocolo-pre-separacao')?.value || '';
        
        // Normalizar valores vazios
        const agendamentoNorm = agendamento || '';
        const protocoloNorm = protocolo || '';
        const agendamentoExistenteNorm = agendamentoExistente || '';
        const protocoloExistenteNorm = protocoloExistente || '';
        
        if (expedicaoExistente === dataExpedicao &&
            agendamentoExistenteNorm === agendamentoNorm &&
            protocoloExistenteNorm === protocoloNorm) {
            
            return {
                valido: false,
                mensagem: tratarErroConstraintUnica('Constraint única violada')
            };
        }
    }
    
    return { valido: true };
}

/**
 * Adiciona indicadores visuais para contextos únicos
 */
function adicionarIndicadoresContexto() {
    const linhasPreSeparacao = document.querySelectorAll('tr[data-tipo-item="pre_separacao"]');
    
    // Agrupar por contexto
    const contextos = new Map();
    
    linhasPreSeparacao.forEach(linha => {
        const expedicao = linha.querySelector('.data-expedicao-pre-separacao')?.value;
        const agendamento = linha.querySelector('.agendamento-pre-separacao')?.value || '';
        const protocolo = linha.querySelector('.protocolo-pre-separacao')?.value || '';
        
        const chaveContexto = `${expedicao}|${agendamento}|${protocolo}`;
        
        if (!contextos.has(chaveContexto)) {
            contextos.set(chaveContexto, []);
        }
        
        contextos.get(chaveContexto).push(linha);
    });
    
    // Adicionar badges para contextos únicos
    let corIndex = 0;
    const cores = ['primary', 'success', 'info', 'warning', 'secondary'];
    
    contextos.forEach((linhas, contexto) => {
        if (linhas.length > 1) {
            const cor = cores[corIndex % cores.length];
            corIndex++;
            
            linhas.forEach((linha, index) => {
                const badge = linha.querySelector('.badge-contexto') || document.createElement('span');
                badge.className = `badge badge-${cor} badge-contexto ml-1`;
                badge.textContent = `Grupo ${corIndex}`;
                badge.title = `${linhas.length} pré-separações com mesmo contexto`;
                
                if (!linha.querySelector('.badge-contexto')) {
                    const primeiraColuna = linha.querySelector('td');
                    if (primeiraColuna) {
                        primeiraColuna.appendChild(badge);
                    }
                }
            });
        }
    });
}

// Inicializar melhorias quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Aplicar melhorias de tratamento de erro
    aprimorarTratamentoErros();
    
    // Adicionar indicadores visuais
    adicionarIndicadoresContexto();
    
    // Observar mudanças na tabela para atualizar indicadores
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                // Reagrupar contextos quando a tabela mudar
                setTimeout(adicionarIndicadoresContexto, 100);
            }
        });
    });
    
    // Observar mudanças nas tabelas de pré-separação
    const tabelas = document.querySelectorAll('table');
    tabelas.forEach(tabela => {
        observer.observe(tabela, { childList: true, subtree: true });
    });
});

console.log('✅ Melhorias da interface para constraint única carregadas');
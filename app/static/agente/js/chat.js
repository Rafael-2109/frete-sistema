/**
 * Agente Logistico - Chat JavaScript
 * Versao: 1.1
 * Data: 03/12/2025
 *
 * Features implementadas:
 * - FEAT-001: Seletor de Modelo
 * - FEAT-002: Toggle de Thinking
 * - FEAT-003: Painel de Thinking
 * - FEAT-004: Budget de Tokens Visual
 * - FEAT-006: Timeline de Acoes
 * - FEAT-008: Todo List Visual
 */

// ============================================
// ESTADO GLOBAL
// ============================================
let sessionId = null;
let pendingAction = null;
let totalTokens = 0;
let totalInputTokens = 0;
let totalOutputTokens = 0;
let totalCost = 0;

// FEAT-001: Modelo selecionado
let currentModel = 'claude-sonnet-4-5-20250929';

// FEAT-002: Thinking ativado
let thinkingEnabled = false;

// FEAT-010: Plan Mode ativado
let planModeEnabled = false;

// FEAT-003: Estado do painel de thinking
let thinkingCollapsed = false;

// FEAT-006: Timeline de ações
const actionTimeline = [];

// FEAT-008: Todo list
let currentTodos = [];

// Budget de tokens (configurável)
const TOKEN_BUDGET = 200000;

// FEAT-026: Controle de streaming para Stop
let currentEventSource = null;
let isGenerating = false;

// ============================================
// ELEMENTOS DOM
// ============================================
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const typingContainer = document.getElementById('typing-container');
const typingText = document.getElementById('typing-text');

// Habilita/desabilita botão e auto-resize
messageInput.addEventListener('input', () => {
    sendBtn.disabled = !messageInput.value.trim();
    autoResizeTextarea();
});

// FEAT-029: Listener no FORM para capturar submit (CORRIGE BUG DE RELOAD NO MOBILE)
// O botão é type="submit", então precisamos capturar o evento no form
const chatForm = document.getElementById('chat-form');
chatForm.addEventListener('submit', function(e) {
    e.preventDefault(); // CRÍTICO: Impede reload da página
    if (messageInput.value.trim() && !sendBtn.disabled) {
        sendMessage(e);
    }
});

// FEAT-026: Shift+Enter = nova linha, Enter = enviar
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        // Não precisa mais chamar sendMessage aqui, pois o form.submit será disparado
        // Mas como estamos prevenindo o submit via Enter, precisamos disparar manualmente
        if (messageInput.value.trim() && !sendBtn.disabled) {
            sendMessage(e);
        }
    }
});

/**
 * FEAT-026: Auto-resize do textarea baseado no conteúdo
 */
function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    const newHeight = Math.min(messageInput.scrollHeight, 150); // Max 150px
    messageInput.style.height = newHeight + 'px';
}

/**
 * FEAT-026: Para a geração atual
 */
function stopGeneration() {
    console.log('[CHAT] Interrompendo geração...');

    // FASE 5: Se SDK Client ativo e temos sessionId, chamar /api/interrupt
    // Isso envia interrupt ao ClaudeSDKClient, que emite interrupt_ack no stream
    if (sessionId) {
        fetch('/agente/api/interrupt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        }).then(resp => {
            if (resp.ok) {
                console.log('[CHAT] Interrupt enviado com sucesso');
            } else {
                console.log('[CHAT] Interrupt não disponível (SDK Client desabilitado ou sessão não ativa)');
            }
        }).catch(e => {
            console.warn('[CHAT] Falha ao enviar interrupt:', e);
        });
    }

    // Marca como não gerando (isso vai parar o loop)
    isGenerating = false;

    // Cancela o reader se existir (fallback — funciona com ou sem SDK Client)
    if (currentEventSource && currentEventSource.cancel) {
        try {
            currentEventSource.cancel();
        } catch (e) {
            console.log('[CHAT] Reader já cancelado');
        }
        currentEventSource = null;
    }

    hideTyping();
    hideStopButton();

    // Adiciona mensagem de interrupção (fallback — se interrupt_ack chegar, será mostrado via SSE)
    addMessage('⏹️ *Geração interrompida pelo usuário*', 'assistant');
}

/**
 * FEAT-026: Mostra o botão de stop
 */
function showStopButton() {
    const stopBtn = document.getElementById('stop-btn');
    const sendBtn = document.getElementById('send-btn');
    if (stopBtn) stopBtn.style.display = 'flex';
    if (sendBtn) sendBtn.style.display = 'none';
}

/**
 * FEAT-026: Esconde o botão de stop
 */
function hideStopButton() {
    const stopBtn = document.getElementById('stop-btn');
    const sendBtn = document.getElementById('send-btn');
    if (stopBtn) stopBtn.style.display = 'none';
    if (sendBtn) sendBtn.style.display = 'flex';
}

// ============================================
// FEAT-001: SELETOR DE MODELO
// ============================================
const modelSelector = document.getElementById('model-selector');
const modelDisplay = document.getElementById('model-display');
const modelDescription = document.getElementById('model-description');

// Descrições dos modelos
const MODEL_INFO = {
    'claude-haiku-4-5-20251001': {
        name: 'Haiku',
        description: 'Mais rápido e econômico. Ideal para consultas simples.',
        speed: '⚡⚡⚡',
        cost: '$'
    },
    'claude-sonnet-4-5-20250929': {
        name: 'Sonnet',
        description: 'Equilibrado. Bom para a maioria das tarefas.',
        speed: '⚡⚡',
        cost: '$$'
    },
    'claude-opus-4-5-20251101': {
        name: 'Opus',
        description: 'Mais potente. Para análises complexas e planejamento.',
        speed: '⚡',
        cost: '$$$'
    }
};

modelSelector.addEventListener('change', function() {
    currentModel = this.value;
    const info = MODEL_INFO[currentModel] || { name: 'Claude', description: '' };

    // Atualiza display do modelo
    modelDisplay.textContent = `Claude Agent SDK • ${info.name}`;

    // Atualiza descrição
    if (modelDescription) {
        modelDescription.textContent = info.description;
    }

    console.log('[AGENTE] Modelo alterado para:', currentModel);
});

// ============================================
// FEAT-002: TOGGLE DE THINKING
// ============================================
const thinkingToggle = document.getElementById('thinking-toggle');
const thinkingLabelText = document.getElementById('thinking-label-text');

thinkingToggle.addEventListener('change', function() {
    thinkingEnabled = this.checked;

    // Atualiza texto do label
    if (thinkingLabelText) {
        thinkingLabelText.textContent = this.checked ? 'Pensamento ativo' : 'Pensamento rápido';
    }

    console.log('[AGENTE] Extended Thinking:', thinkingEnabled ? 'ATIVADO' : 'DESATIVADO');
});

// ============================================
// FEAT-010: TOGGLE DE PLAN MODE
// ============================================
const planModeToggle = document.getElementById('plan-mode-toggle');
const planModeLabelText = document.getElementById('plan-mode-label-text');

if (planModeToggle) {
    planModeToggle.addEventListener('change', function() {
        planModeEnabled = this.checked;

        // Atualiza texto do label
        if (planModeLabelText) {
            planModeLabelText.textContent = this.checked ? 'Modo análise' : 'Modo ação';
        }

        console.log('[AGENTE] Plan Mode:', planModeEnabled ? 'ATIVADO (somente leitura)' : 'DESATIVADO');
    });
}

// ============================================
// FEAT-003: PAINEL DE THINKING
// ============================================
function toggleThinkingPanel() {
    const body = document.getElementById('thinking-text');
    const icon = document.getElementById('thinking-toggle-icon');

    thinkingCollapsed = !thinkingCollapsed;
    body.style.display = thinkingCollapsed ? 'none' : 'block';
    icon.className = thinkingCollapsed ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
}

function showThinking(content) {
    const panel = document.getElementById('thinking-panel');
    const text = document.getElementById('thinking-text');
    const status = document.getElementById('thinking-status');

    panel.style.display = 'block';
    status.textContent = 'Pensando...';
    text.innerHTML += formatMessage(content);
    text.scrollTop = text.scrollHeight;
}

function hideThinkingPanel() {
    const status = document.getElementById('thinking-status');
    if (status) {
        status.textContent = 'Concluído';
    }
    // Não esconde automaticamente - deixa visível para o usuário ver o raciocínio
}

function clearThinking() {
    const panel = document.getElementById('thinking-panel');
    const text = document.getElementById('thinking-text');
    panel.style.display = 'none';
    text.innerHTML = '';
}

// ============================================
// FEAT-006: TIMELINE DE AÇÕES
// ============================================
function toggleTimeline() {
    const timeline = document.getElementById('action-timeline');
    timeline.classList.toggle('hidden');
}

function toggleTimelineCollapse() {
    const timeline = document.getElementById('action-timeline');
    timeline.classList.toggle('collapsed');
}

/**
 * FEAT-027: Esconde o painel de timeline
 */
function hideTimeline() {
    const timeline = document.getElementById('action-timeline');
    timeline.classList.add('hidden');
}

/**
 * FEAT-027: Esconde o painel de todos
 */
function hideTodoPanel() {
    const todoPanel = document.getElementById('todo-panel');
    todoPanel.classList.add('hidden');
}

function addTimelineItem(action) {
    actionTimeline.unshift(action);
    renderTimeline();

    // Mostra timeline se estava escondida
    const timeline = document.getElementById('action-timeline');
    timeline.classList.remove('hidden');

    document.getElementById('action-count').textContent = actionTimeline.length;
    document.getElementById('timeline-empty').style.display = 'none';
}

function updateLastTimelineItem(updates) {
    if (actionTimeline.length > 0) {
        Object.assign(actionTimeline[0], updates);
        renderTimeline();
    }
}

function renderTimeline() {
    const container = document.getElementById('timeline-items');

    const toolIcons = {
        'Bash': 'fa-terminal',
        'Read': 'fa-file-alt',
        'Skill': 'fa-magic',
        'Glob': 'fa-search',
        'Grep': 'fa-filter',
        'Write': 'fa-edit',
        'Edit': 'fa-pencil-alt',
        'TodoWrite': 'fa-tasks'
    };

    container.innerHTML = actionTimeline.slice(0, 15).map(a => {
        const iconClass = toolIcons[a.tool_name] || 'fa-cog';
        const statusIcon = a.status === 'success' ? 'fa-check' :
                          a.status === 'error' ? 'fa-times' : 'fa-spinner fa-spin';

        // FEAT-024: Usa descrição amigável quando disponível
        const displayName = a.description || a.tool_name;

        return `
            <div class="timeline-item">
                <div class="timeline-icon ${a.status}">
                    <i class="fas ${statusIcon}"></i>
                </div>
                <div class="timeline-info">
                    <div class="tool-name" title="${a.tool_name}">
                        <i class="fas ${iconClass}"></i>
                        ${displayName}
                    </div>
                    ${a.duration_ms ? `<div class="tool-duration">${a.duration_ms}ms</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function clearTimeline() {
    actionTimeline.length = 0;
    document.getElementById('timeline-items').innerHTML = '';
    document.getElementById('action-count').textContent = '0';
    document.getElementById('timeline-empty').style.display = 'block';
}

// ============================================
// FEAT-008: TODO LIST VISUAL
// ============================================
function updateTodoList(todos) {
    currentTodos = todos;
    const list = document.getElementById('todo-list');
    const progressBar = document.getElementById('todo-progress-bar');
    const progressBadge = document.getElementById('todo-progress-badge');
    const todoPanel = document.getElementById('todo-panel');

    // Mostra painel se houver todos
    if (todos.length > 0) {
        todoPanel.classList.remove('hidden');
    }

    // Renderiza lista
    list.innerHTML = todos.map(todo => {
        const statusIcon = todo.status === 'completed' ? 'fa-check' :
                          todo.status === 'in_progress' ? 'fa-spinner fa-spin' : 'fa-circle';
        const displayText = todo.status === 'in_progress' ? todo.activeForm : todo.content;

        return `
            <li class="todo-item">
                <span class="todo-status ${todo.status}">
                    <i class="fas ${statusIcon}"></i>
                </span>
                <span class="todo-text ${todo.status}">${displayText}</span>
            </li>
        `;
    }).join('');

    // Calcula progresso
    const completed = todos.filter(t => t.status === 'completed').length;
    const inProgress = todos.filter(t => t.status === 'in_progress').length;
    const percent = todos.length > 0 ? Math.round((completed / todos.length) * 100) : 0;

    progressBar.style.width = percent + '%';
    progressBadge.textContent = percent + '%';

    // Cor do badge baseada no progresso
    progressBadge.className = 'badge bg-light ' + (
        percent === 100 ? 'text-success' :
        percent > 50 ? 'text-info' : 'text-primary'
    );

    // FEAT-009: Atualiza barra de progresso geral
    updateGeneralProgressBar(todos, completed, inProgress, percent);
}

// ============================================
// FEAT-009: BARRA DE PROGRESSO GERAL
// ============================================
function updateGeneralProgressBar(todos, completed, inProgress, percent) {
    const container = document.getElementById('progress-bar-container');
    const fill = document.getElementById('progress-bar-fill');
    const status = document.getElementById('progress-status');
    const percentage = document.getElementById('progress-percentage');

    if (!container) return;

    // Mostra barra se houver tarefas
    if (todos.length > 0) {
        container.style.display = 'block';

        // Atualiza porcentagem
        fill.style.width = percent + '%';
        percentage.textContent = percent + '%';

        // Atualiza status
        if (percent === 100) {
            status.textContent = '✓ Todas as tarefas concluídas';
            fill.classList.add('completed');
        } else if (inProgress > 0) {
            const currentTask = todos.find(t => t.status === 'in_progress');
            status.textContent = currentTask ? currentTask.activeForm : 'Processando...';
            fill.classList.remove('completed');
        } else {
            status.textContent = `${completed}/${todos.length} tarefas concluídas`;
            fill.classList.remove('completed');
        }
    } else {
        container.style.display = 'none';
    }
}

function showProgressBar(statusText = 'Processando...') {
    const container = document.getElementById('progress-bar-container');
    const status = document.getElementById('progress-status');
    const fill = document.getElementById('progress-bar-fill');

    if (container) {
        container.style.display = 'block';
        status.textContent = statusText;
        fill.style.width = '0%';
        fill.classList.remove('completed');
    }
}

function hideProgressBar() {
    const container = document.getElementById('progress-bar-container');
    if (container) {
        container.style.display = 'none';
    }
}

function clearTodoList() {
    currentTodos = [];
    document.getElementById('todo-list').innerHTML = '';
    document.getElementById('todo-progress-bar').style.width = '0%';
    document.getElementById('todo-progress-badge').textContent = '0%';
    document.getElementById('todo-panel').classList.add('hidden');

    // FEAT-009: Limpa barra de progresso geral também
    hideProgressBar();
}

// ============================================
// ENVIO DE MENSAGEM
// ============================================
async function sendMessage(event) {
    if (event) event.preventDefault();

    const message = messageInput.value.trim();
    if (!message) return;

    // FEAT-026: Marca como gerando
    isGenerating = true;

    // Adiciona mensagem do usuário
    addMessage(message, 'user');
    messageInput.value = '';
    sendBtn.disabled = true;

    // FEAT-026: Reseta altura do textarea
    messageInput.style.height = 'auto';

    // Limpa thinking anterior
    clearThinking();

    // Mostra indicador e botão stop
    // FEAT-002: Indica quando pensamento profundo está ativo
    if (thinkingEnabled) {
        showTyping('🧠 Pensando profundamente...');
    } else {
        showTyping('Processando...');
    }
    showStopButton(); // FEAT-026

    // FEAT-028: Obtém arquivos anexados
    const files = getAttachedFilesForMessage();

    try {
        const response = await fetch('/agente/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                model: currentModel,              // FEAT-001: Modelo selecionado
                thinking_enabled: thinkingEnabled, // FEAT-002: Thinking ativado
                plan_mode: planModeEnabled,       // FEAT-010: Plan Mode
                files: files                      // FEAT-028: Arquivos anexados
            })
        });

        // FEAT-028: Limpa anexos após envio
        if (files.length > 0) {
            attachedFiles = [];
            renderAttachments();
            updateAttachButton();
            updateFilesPanel();
        }

        if (response.headers.get('content-type')?.includes('text/event-stream')) {
            // Streaming
            await handleStreamResponse(response);
        } else {
            // JSON
            const data = await response.json();
            handleJsonResponse(data);
        }

    } catch (error) {
        console.error('Erro:', error);
        hideTyping();
        addMessage('❌ Erro de conexão. Tente novamente.', 'assistant');
    } finally {
        // FEAT-026: Finaliza geração
        isGenerating = false;
        hideStopButton();
    }
}

// Processa resposta streaming (SSE)
async function handleStreamResponse(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEventType = null;

    // =================================================================
    // TIMEOUT NO READER
    // =================================================================
    // Timeout de 60 segundos entre chunks para detectar conexão perdida.
    // Se o servidor morrer mid-stream, o reader.read() ficaria esperando
    // eternamente sem esse timeout.
    // =================================================================
    const READ_TIMEOUT_MS = 60000; // 60 segundos max entre chunks

    /**
     * Wrapper que adiciona timeout ao reader.read()
     * Se não receber dados em READ_TIMEOUT_MS, rejeita com erro.
     */
    async function readWithTimeout() {
        return Promise.race([
            reader.read(),
            new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Read timeout')), READ_TIMEOUT_MS)
            )
        ]);
    }

    // FEAT-026: Guarda referência para permitir cancelamento
    currentEventSource = {
        reader,
        cancel: () => {
            try {
                reader.cancel();
            } catch (e) {
                console.log('[SSE] Reader já cancelado');
            }
        }
    };

    // Estado da mensagem atual
    const state = {
        text: '',           // Texto acumulado
        msgElement: null,   // Elemento DOM da mensagem
        bubbleElement: null, // Elemento do bubble
        lastTextTime: Date.now(), // FEAT-032: Timestamp do último texto recebido
        lastChunkTime: Date.now() // Timestamp do último chunk recebido (qualquer tipo)
    };

    // FEAT-032: Timeout de feedback - mostra mensagem se ficar muito tempo sem texto
    let feedbackShown = false;
    const FEEDBACK_TIMEOUT = 15000; // 15 segundos

    const feedbackTimer = setInterval(() => {
        if (!isGenerating) {
            clearInterval(feedbackTimer);
            return;
        }
        const elapsed = Date.now() - state.lastTextTime;
        if (elapsed > FEEDBACK_TIMEOUT && !feedbackShown) {
            feedbackShown = true;
            showTyping('⏳ Ainda processando, aguarde...');
            console.log('[SSE] Timeout de feedback ativado após', elapsed, 'ms');
        }
    }, 5000); // Verifica a cada 5 segundos

    try {
        while (true) {
            // FEAT-026: Verifica se foi interrompido
            if (!isGenerating) {
                reader.cancel();
                break;
            }

            try {
                // Usa readWithTimeout em vez de reader.read() direto
                const { done, value } = await readWithTimeout();
                if (done) break;

                // Atualiza timestamp de último chunk
                state.lastChunkTime = Date.now();

                buffer += decoder.decode(value, { stream: true });

                // Processa eventos SSE (formato: event: tipo\ndata: json\n\n)
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        currentEventType = line.slice(6).trim();
                    } else if (line.startsWith('data:')) {
                        try {
                            const data = JSON.parse(line.slice(5));

                            // Cria elemento apenas quando primeiro texto chegar
                            if (currentEventType === 'text' && !state.msgElement) {
                                hideTyping();
                                state.msgElement = createMessageElement('', 'assistant');
                                chatMessages.appendChild(state.msgElement);
                                state.bubbleElement = state.msgElement.querySelector('.message-bubble');
                            }

                            // Processa o evento com estado compartilhado
                            processSSEEvent(currentEventType, data, state);
                            currentEventType = null;
                        } catch (e) {
                            console.error('[SSE] Erro ao parsear JSON:', e, 'linha:', line);
                        }
                    }
                }
            } catch (readError) {
                // =================================================================
                // TRATAMENTO DE TIMEOUT NO READ
                // =================================================================
                if (readError.message === 'Read timeout') {
                    console.error('[SSE] Timeout aguardando dados do servidor (60s)');
                    addMessage(
                        '⚠️ **Conexão com o servidor perdida**\n\n' +
                        'O servidor demorou muito para responder. ' +
                        'Tente enviar sua mensagem novamente.',
                        'assistant'
                    );
                    break;
                }
                // Outros erros - propaga
                throw readError;
            }
        }
    } catch (error) {
        // =================================================================
        // TRATAMENTO DE ERRO GERAL NO STREAM
        // =================================================================
        console.error('[SSE] Erro no stream:', error);

        // Mostra erro amigável se não houver mensagem parcial
        if (!state.text) {
            addMessage(
                `❌ **Erro de conexão**\n\n${error.message || 'Erro desconhecido'}`,
                'assistant'
            );
        }
    } finally {
        // =================================================================
        // CLEANUP GARANTIDO
        // =================================================================
        // Este bloco SEMPRE executa, garantindo que:
        // 1. Timer de feedback é limpo
        // 2. Indicador de typing é escondido
        // 3. Botão de stop é escondido
        // 4. Items pendentes são finalizados
        // =================================================================
        clearInterval(feedbackTimer);
        hideTyping();

        // FIX: Garante que items pendentes sejam finalizados mesmo se stream terminar sem 'done'
        // Isso resolve o problema de "Ações spinning" quando conexão quebra ou timeout
        finalizePendingTimelineItems('success');
        finalizePendingTodos(true);
    }
}

// Processa evento SSE com estado compartilhado
function processSSEEvent(eventType, data, state) {
    try {
        switch (eventType) {
            case 'start':
                // Stream iniciado
                break;

            case 'init':
                // FEAT-030: Captura nosso session_id (não o do SDK)
                if (data.session_id) sessionId = data.session_id;
                break;

            // FEAT-030: Heartbeat para manter conexão viva (ignorar)
            case 'heartbeat':
                console.log('[SSE] Heartbeat recebido:', data.timestamp);
                // Heartbeat também conta como atividade
                state.lastChunkTime = Date.now();
                break;

            // F0.1: Retry automático quando sessão SDK expira
            // Backend detectou sessão expirada e está retentando com nova sessão.
            // Limpa texto parcial (se houver) e mostra feedback ao usuário.
            case 'retry':
                console.log(`[SSE] Retry automático: ${data.reason} (tentativa ${data.attempt})`);
                // Limpa texto parcial acumulado na primeira tentativa
                state.text = '';
                if (state.bubbleElement) {
                    state.bubbleElement.innerHTML = '';
                }
                // Feedback visual discreto
                showTyping(data.message || '🔄 Reconectando...');
                // Conta como atividade para evitar timeout
                state.lastChunkTime = Date.now();
                state.lastTextTime = Date.now();
                break;

            case 'text':
                // FEAT-032: Atualiza timestamp de último texto recebido
                state.lastTextTime = Date.now();

                // Acumula texto no estado compartilhado
                state.text += data.content || '';
                if (state.bubbleElement) {
                    state.bubbleElement.innerHTML = formatMessage(state.text);
                    scrollToBottom();
                }
                hideTyping();
                // FEAT-028: Detecta URLs de arquivos para download
                if (data.content) {
                    detectDownloadUrls(data.content);
                }
                break;

            // FEAT-003: Evento de thinking
            case 'thinking':
                if (thinkingEnabled && data.content) {
                    showThinking(data.content);
                }
                break;

            // FEAT-006: Timeline - Início de tool call
            // FEAT-024: Usa descrição amigável quando disponível
            case 'tool_call': {
                const toolDescription = data.description || data.tool_name || data.content || 'ferramenta';
                showTyping(`🔧 ${toolDescription}...`);

                // Adiciona à timeline com descrição
                addTimelineItem({
                    tool_name: data.tool_name || data.content || 'Tool',
                    description: data.description || '',  // FEAT-024
                    status: 'pending',
                    timestamp: new Date()
                });

                // =================================================================
                // FEEDBACK VISUAL: Timeout para tools longas
                // =================================================================
                // Se a tool demorar mais de 10 segundos, mostra feedback adicional
                // =================================================================
                const toolName = data.tool_name || 'ferramenta';
                setTimeout(() => {
                    if (isGenerating) {
                        // Verifica se ainda está na mesma tool
                        const lastItem = actionTimeline[0];
                        if (lastItem && lastItem.tool_name === toolName && lastItem.status === 'pending') {
                            showTyping(`⏳ ${toolDescription} (ainda processando...)`);
                        }
                    }
                }, 10000); // 10 segundos
                break;
            }

            // FEAT-006: Timeline - Resultado de tool
            case 'tool_result': {
                // MELHORIA: Trata erros de tools adequadamente
                const toolIsError = data.is_error || false;
                const toolResultName = data.tool_name || 'ferramenta';

                if (toolIsError) {
                    // Tool falhou - mostra feedback claro
                    showTyping(`⚠️ ${toolResultName} encontrou um problema...`);
                    updateLastTimelineItem({
                        status: 'error',
                        duration_ms: data.duration_ms || 0
                    });
                    console.warn(`[SSE] Tool '${toolResultName}' retornou erro:`, data.result);
                } else {
                    // Tool executou com sucesso
                    showTyping('📊 Analisando dados...');
                    updateLastTimelineItem({
                        status: 'success',
                        duration_ms: data.duration_ms || 0
                    });
                }
                break;
            }

            // FEAT-008/FEAT-024: Evento de todos (vem do TodoWrite)
            case 'todos': {
                // FEAT-024: Suporta formato {todos: [...]} ou array direto
                const todosData = data.todos || (Array.isArray(data) ? data : null);
                if (todosData && Array.isArray(todosData)) {
                    updateTodoList(todosData);
                }
                break;
            }

            case 'action_pending':
                hideTyping();
                pendingAction = data;
                showConfirmation(data.message || 'Confirmar ação?');
                break;

            case 'interrupt_ack':
                // FASE 5: Interrupt acknowledgment do ClaudeSDKClient
                hideTyping();
                hideThinkingPanel();
                finalizePendingTimelineItems('cancelled');
                finalizePendingTodos(false);
                addMessage('🛑 Operação interrompida.', 'system');
                console.log('[SSE] Interrupt acknowledgment recebido');
                break;

            case 'error':
                hideTyping();
                hideThinkingPanel();

                // FEAT-030: Finaliza todos os items pendentes (timeline e todos)
                finalizePendingTimelineItems('error');
                finalizePendingTodos(false);  // Não marca como completed, apenas para o spinner

                // FEAT-030: Trata sessão expirada
                if (data.session_expired) {
                    console.log('[SSE] Sessão SDK expirada, será criada nova na próxima mensagem');
                    addMessage(`⚠️ A sessão anterior expirou no servidor.\n\n**Mas não se preocupe!** Seu histórico está salvo e a conversa continuará normalmente.`, 'assistant');
                } else {
                    addMessage(`❌ ${data.message || data.content || 'Erro desconhecido'}`, 'assistant');
                }
                break;

            case 'done':
                hideTyping();
                hideThinkingPanel();
                if (data.session_id) sessionId = data.session_id;
                updateMetrics(data.input_tokens, data.output_tokens, data.cost_usd);

                // FEAT-030: Finaliza items pendentes (timeline e todos)
                finalizePendingTimelineItems('success');
                finalizePendingTodos(true);  // Marca como completed
                break;
        }
    } catch (e) {
        // =================================================================
        // TRATAMENTO DE ERRO NO PROCESSAMENTO DE EVENTO
        // =================================================================
        // Se houver erro ao processar um evento específico, loga mas
        // não interrompe o stream. Isso evita que um evento malformado
        // trave toda a interface.
        // =================================================================
        console.error('[SSE] Erro ao processar evento:', eventType, e);
    }
}

/**
 * FEAT-030: Finaliza todos os items pendentes da timeline.
 * Chamado quando o stream termina (done ou error).
 */
function finalizePendingTimelineItems(status = 'success') {
    actionTimeline.forEach(item => {
        if (item.status === 'pending') {
            item.status = status;
        }
    });
    renderTimeline();
}

/**
 * FEAT-030: Finaliza todos os todos que estão em 'in_progress'.
 * Chamado quando o stream termina (done ou error).
 */
function finalizePendingTodos(markAsCompleted = true) {
    if (!currentTodos || currentTodos.length === 0) return;

    let changed = false;
    currentTodos.forEach(todo => {
        if (todo.status === 'in_progress') {
            // Se markAsCompleted=true, marca como completed
            // Se markAsCompleted=false (erro), mantém in_progress mas para o spinner
            todo.status = markAsCompleted ? 'completed' : 'pending';
            changed = true;
        }
    });

    if (changed) {
        updateTodoList(currentTodos);
    }
}

// Processa resposta JSON (síncrono)
function handleJsonResponse(data) {
    hideTyping();

    if (data.success) {
        addMessage(data.response, 'assistant');
        sessionId = data.session_id;

        if (data.metrics) {
            updateMetrics(
                data.metrics.input_tokens,
                data.metrics.output_tokens,
                data.metrics.cost_usd
            );
        }

        if (data.pending_action) {
            pendingAction = data.pending_action;
            showConfirmation(pendingAction.message || 'Confirmar ação?');
        }
    } else {
        addMessage(`❌ ${data.error || 'Erro desconhecido'}`, 'assistant');
    }
}

// Adiciona mensagem ao chat
function addMessage(text, role) {
    const element = createMessageElement(text, role);
    chatMessages.appendChild(element);
    scrollToBottom();
}

// Cria elemento de mensagem
function createMessageElement(text, role) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const icon = role === 'user' ? 'fa-user' : 'fa-robot';
    const formattedText = role === 'user' ? escapeHtml(text) : formatMessage(text);

    div.innerHTML = `
        <div class="message-avatar">
            <i class="fas ${icon}"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble">${formattedText}</div>
            <div class="message-time">${new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
    `;

    return div;
}

// ============================================
// FEAT-023: MARKDOWN AVANÇADO
// ============================================
// Configura marked.js com highlight.js
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function(code, lang) {
            if (typeof hljs !== 'undefined') {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(code, { language: lang }).value;
                    } catch (e) {
                        console.warn('[MARKED] Erro no highlight:', e);
                    }
                }
                // Auto-detect language
                try {
                    return hljs.highlightAuto(code).value;
                } catch (e) {
                    console.warn('[MARKED] Erro no highlightAuto:', e);
                }
            }
            return code;
        }
    });
}

// Formata mensagem com Markdown avançado
function formatMessage(text) {
    // Se marked.js está disponível, usa para renderização completa
    if (typeof marked !== 'undefined') {
        try {
            // Processa markdown
            let html = marked.parse(text);

            // Sanitização básica (remove scripts)
            html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');

            // Adiciona classes para estilo
            html = html.replace(/<table>/g, '<table class="markdown-table">');
            html = html.replace(/<blockquote>/g, '<blockquote class="markdown-quote">');
            html = html.replace(/<pre>/g, '<pre class="markdown-pre">');

            return html;
        } catch (e) {
            console.error('[MARKED] Erro ao processar markdown:', e);
        }
    }

    // Fallback: markdown básico
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/### (.*?)$/gm, '<h6>$1</h6>')
        .replace(/## (.*?)$/gm, '<h5>$1</h5>')
        .replace(/# (.*?)$/gm, '<h4>$1</h4>')
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

// Escapa HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Mostra indicador de digitação
function showTyping(text = 'Pensando...') {
    typingText.textContent = text;
    typingContainer.style.display = 'block';
    scrollToBottom();
}

// Esconde indicador
function hideTyping() {
    typingContainer.style.display = 'none';
}

// Scroll para o final
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// FEAT-004: Atualiza métricas com budget visual (apenas para administradores)
function updateMetrics(inputTokens, outputTokens, costUsd) {
    totalInputTokens += (inputTokens || 0);
    totalOutputTokens += (outputTokens || 0);
    totalTokens = totalInputTokens + totalOutputTokens;
    totalCost += costUsd || 0;

    // Atualiza UI do budget de tokens (admin only)
    const tokenBudget = document.getElementById('token-budget');
    if (tokenBudget) {
        tokenBudget.style.display = 'block';

        // Calcula percentual
        const percent = Math.min((totalTokens / TOKEN_BUDGET) * 100, 100);

        // Atualiza elementos
        document.getElementById('token-percentage').textContent = percent.toFixed(1) + '%';
        document.getElementById('token-input').textContent = totalInputTokens.toLocaleString();
        document.getElementById('token-output').textContent = totalOutputTokens.toLocaleString();
        document.getElementById('token-cost').textContent = totalCost.toFixed(4);

        // Atualiza barra de progresso
        const progressBar = document.getElementById('token-progress-bar');
        progressBar.style.width = percent + '%';

        // Muda cor baseado no uso
        progressBar.classList.remove('warning', 'danger');
        if (percent > 90) {
            progressBar.classList.add('danger');
        } else if (percent > 70) {
            progressBar.classList.add('warning');
        }
    }
}

// Mostra modal de confirmação
function showConfirmation(message) {
    document.getElementById('confirmation-message').textContent = message;
    document.getElementById('confirmation-overlay').style.display = 'flex';
}

// Cancela ação (responde "não" no chat)
function cancelAction() {
    document.getElementById('confirmation-overlay').style.display = 'none';
    pendingAction = null;
    // Envia "não" como resposta para cancelar
    messageInput.value = 'não';
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
}

// Confirma ação (responde "sim" no chat)
function confirmAction() {
    document.getElementById('confirmation-overlay').style.display = 'none';
    pendingAction = null;
    // Envia "sim" como resposta para confirmar
    messageInput.value = 'sim, confirmar';
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
}

// Limpa sessão (local apenas - SDK gerencia sessions automaticamente)
function clearSession() {
    if (!confirm('Limpar toda a conversa?')) return;

    // Limpa estado local (SDK cria nova session automaticamente no próximo chat)
    sessionId = null;
    totalTokens = 0;
    totalInputTokens = 0;
    totalOutputTokens = 0;
    totalCost = 0;

    // Limpa budget de tokens
    const tokenBudget = document.getElementById('token-budget');
    if (tokenBudget) {
        tokenBudget.style.display = 'none';
        document.getElementById('token-percentage').textContent = '0%';
        document.getElementById('token-progress-bar').style.width = '0%';
    }

    // Limpa thinking
    clearThinking();

    // Limpa timeline
    clearTimeline();

    // Limpa todo list
    clearTodoList();

    // Remove mensagens (exceto boas-vindas)
    const messages = chatMessages.querySelectorAll('.message');
    messages.forEach((msg, index) => {
        if (index > 0) msg.remove();
    });

    addMessage('🔄 Conversa limpa. Uma nova sessão será iniciada na próxima mensagem.', 'assistant');
}

// Mostra ajuda
function showHelp() {
    addMessage(`## 📖 Ajuda do Agente Logístico

**Consultas disponíveis:**
- "Tem pedido pendente pro [cliente]?"
- "Quais pedidos estão atrasados?"
- "Quando o pedido [número] estará disponível?"
- "Chegou [produto]?"
- "O que vai dar falta essa semana?"

**Ações:**
- "Criar separação do pedido [número]"
- "Programar envio do [cliente] para [data]"

**Modelos disponíveis:**
- **Haiku** ⚡⚡⚡ - Rápido, ideal para consultas simples
- **Sonnet** ⚡⚡ - Equilibrado, uso geral
- **Opus** ⚡ - Potente, para análises complexas

**Pensamento Profundo:**
Ative o toggle 🧠 para respostas mais elaboradas.
O agente mostrará seu raciocínio antes de responder.

**Dicas:**
- Seja específico com nomes de clientes
- Use números de pedido exatos quando possível
- Para criar separações, confirme a opção desejada
`, 'assistant');
}

// ============================================
// FEAT-011: GERENCIAMENTO DE SESSÕES
// ============================================
let sessionsList = [];
let sidebarOpen = false;

/**
 * FEAT-025: Abre modal de sessões.
 */
function openSessionsModal() {
    const modal = document.getElementById('sessions-modal');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Previne scroll do body
    loadSessions();
}

/**
 * FEAT-025: Fecha modal de sessões.
 */
function closeSessionsModal() {
    const modal = document.getElementById('sessions-modal');
    modal.style.display = 'none';
    document.body.style.overflow = ''; // Restaura scroll
}

/**
 * FEAT-025: Toggle da sidebar de sessões (compatibilidade).
 * @deprecated Use openSessionsModal() e closeSessionsModal()
 */
function toggleSessionsSidebar() {
    openSessionsModal();
}

/**
 * Carrega lista de sessões do servidor.
 */
async function loadSessions() {
    const loading = document.getElementById('sessions-loading');
    const empty = document.getElementById('sessions-empty');

    loading.style.display = 'block';
    empty.style.display = 'none';

    try {
        const response = await fetch('/agente/api/sessions?limit=20', {
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        });

        const data = await response.json();

        loading.style.display = 'none';

        if (data.success && data.sessions.length > 0) {
            sessionsList = data.sessions;
            renderSessions();
            updateSessionsCount(data.sessions.length);
        } else {
            empty.style.display = 'block';
            updateSessionsCount(0);
        }
    } catch (error) {
        console.error('[SESSIONS] Erro ao carregar:', error);
        loading.style.display = 'none';
        empty.innerHTML = '<i class="fas fa-exclamation-triangle fa-2x mb-2 text-warning"></i><p>Erro ao carregar sessões</p>';
        empty.style.display = 'block';
    }
}

/**
 * Renderiza lista de sessões.
 */
function renderSessions() {
    const list = document.getElementById('sessions-list');

    // Remove itens antigos (mantém loading e empty)
    const items = list.querySelectorAll('.session-item');
    items.forEach(item => item.remove());

    // Renderiza sessões
    sessionsList.forEach(session => {
        const item = document.createElement('div');
        item.className = 'session-item' + (session.session_id === sessionId ? ' active' : '');
        item.onclick = () => selectSession(session);

        const dateStr = session.updated_at
            ? new Date(session.updated_at).toLocaleString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            })
            : '';

        item.innerHTML = `
            <div class="session-item-header">
                <span class="session-item-title" title="${escapeHtml(session.title || 'Sem título')}">${escapeHtml(session.title || 'Sem título')}</span>
                <div class="session-item-actions">
                    <button onclick="event.stopPropagation(); renameSessionPrompt(${session.id})" title="Renomear">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="delete" onclick="event.stopPropagation(); deleteSessionConfirm(${session.id})" title="Excluir">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="session-item-preview">${escapeHtml(session.last_message || 'Nenhuma mensagem')}</div>
            <div class="session-item-meta">
                <span>${dateStr}</span>
                <span class="badge bg-secondary">${session.message_count || 0} msgs</span>
            </div>
        `;

        list.appendChild(item);
    });
}

/**
 * FEAT-030: Seleciona uma sessão e carrega histórico de mensagens.
 */
async function selectSession(session) {
    sessionId = session.session_id;
    console.log('[SESSIONS] Sessão selecionada:', sessionId);

    // Fecha modal
    closeSessionsModal();

    // Limpa chat atual (exceto boas-vindas)
    const messages = chatMessages.querySelectorAll('.message');
    messages.forEach((msg, index) => {
        if (index > 0) msg.remove();
    });

    // Limpa timeline e todos
    clearTimeline();
    clearTodoList();

    // Mostra loading
    showTyping('Carregando histórico...');

    try {
        // FEAT-030: Busca histórico de mensagens do servidor
        const response = await fetch(`/agente/api/sessions/${sessionId}/messages`, {
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        });

        const data = await response.json();
        hideTyping();

        if (data.success && data.messages && data.messages.length > 0) {
            console.log(`[SESSIONS] Carregando ${data.messages.length} mensagens`);

            // Renderiza cada mensagem do histórico
            data.messages.forEach(msg => {
                const role = msg.role === 'user' ? 'user' : 'assistant';
                addMessage(msg.content, role);
            });

            // Info de retomada
            addMessage(`📂 **Sessão "${session.title || 'Sem título'}" carregada**\n\nContinue a conversa abaixo...`, 'assistant');

        } else if (data.success && (!data.messages || data.messages.length === 0)) {
            // Sessão existe mas sem mensagens
            addMessage(`📂 Retomando sessão: **${session.title || 'Sem título'}**\n\nNenhuma mensagem anterior encontrada. Inicie a conversa!`, 'assistant');

        } else {
            console.error('[SESSIONS] Erro ao carregar histórico:', data.error);
            addMessage(`⚠️ Não foi possível carregar o histórico da sessão.\n\nContinue de onde parou...`, 'assistant');
        }

    } catch (error) {
        console.error('[SESSIONS] Erro ao carregar histórico:', error);
        hideTyping();
        addMessage(`⚠️ Erro de conexão ao carregar histórico.\n\nContinue de onde parou...`, 'assistant');
    }

    // Atualiza lista para mostrar ativo
    renderSessions();
}

/**
 * Inicia nova sessão.
 */
function startNewSession() {
    sessionId = null;
    totalTokens = 0;
    totalInputTokens = 0;
    totalOutputTokens = 0;
    totalCost = 0;

    // FEAT-025: Fecha modal (se estiver aberto)
    closeSessionsModal();

    // Limpa chat
    clearSession();

    console.log('[SESSIONS] Nova sessão iniciada');
}

/**
 * Prompt para renomear sessão.
 */
function renameSessionPrompt(id) {
    const session = sessionsList.find(s => s.id === id);
    if (!session) return;

    const newTitle = prompt('Novo título:', session.title || '');
    if (newTitle && newTitle.trim()) {
        renameSession(id, newTitle.trim());
    }
}

/**
 * Renomeia sessão no servidor.
 */
async function renameSession(id, title) {
    try {
        const response = await fetch(`/agente/api/sessions/${id}/rename`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({ title })
        });

        const data = await response.json();

        if (data.success) {
            // Atualiza lista local
            const session = sessionsList.find(s => s.id === id);
            if (session) {
                session.title = title;
                renderSessions();
            }
        } else {
            alert('Erro ao renomear: ' + (data.error || 'Erro desconhecido'));
        }
    } catch (error) {
        console.error('[SESSIONS] Erro ao renomear:', error);
        alert('Erro ao renomear sessão');
    }
}

/**
 * Confirmação para excluir sessão.
 */
function deleteSessionConfirm(id) {
    if (confirm('Excluir esta conversa?\nEsta ação não pode ser desfeita.')) {
        deleteSession(id);
    }
}

/**
 * Exclui sessão no servidor.
 */
async function deleteSession(id) {
    try {
        const response = await fetch(`/agente/api/sessions/${id}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        });

        const data = await response.json();

        if (data.success) {
            // Remove da lista local
            sessionsList = sessionsList.filter(s => s.id !== id);
            renderSessions();
            updateSessionsCount(sessionsList.length);

            // Se era a sessão atual, limpa
            const deleted = sessionsList.find(s => s.id === id);
            if (deleted && deleted.session_id === sessionId) {
                sessionId = null;
            }
        } else {
            alert('Erro ao excluir: ' + (data.error || 'Erro desconhecido'));
        }
    } catch (error) {
        console.error('[SESSIONS] Erro ao excluir:', error);
        alert('Erro ao excluir sessão');
    }
}

/**
 * Atualiza badge de contagem de sessões.
 */
function updateSessionsCount(count) {
    const badge = document.getElementById('sessions-count-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }
}

// ============================================
// FEAT-028: UPLOAD/DOWNLOAD DE ARQUIVOS
// ============================================

// Lista de arquivos anexados (pendentes de envio)
let attachedFiles = [];

// Lista de downloads disponíveis
let downloadFiles = [];

// Referência ao input de arquivo
const fileInput = document.getElementById('file-input');

// Event listener para seleção de arquivos
if (fileInput) {
    fileInput.addEventListener('change', handleFileSelect);
}

/**
 * Manipula seleção de arquivos
 */
function handleFileSelect(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    for (const file of files) {
        uploadFile(file);
    }

    // Limpa o input para permitir selecionar o mesmo arquivo novamente
    event.target.value = '';
}

/**
 * Faz upload de um arquivo
 */
async function uploadFile(file) {
    // Verifica tamanho (10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert(`Arquivo "${file.name}" é muito grande. Máximo: 10MB`);
        return;
    }

    // Adiciona à lista com status uploading
    const tempId = 'temp_' + Date.now();
    const fileData = {
        id: tempId,
        name: file.name,
        original_name: file.name,
        size: file.size,
        type: getFileType(file.name),
        status: 'uploading'
    };

    attachedFiles.push(fileData);
    renderAttachments();
    showFilesPanel();

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', sessionId || 'default');

        const response = await fetch('/agente/api/upload', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            // Atualiza o arquivo na lista
            const idx = attachedFiles.findIndex(f => f.id === tempId);
            if (idx !== -1) {
                attachedFiles[idx] = {
                    ...data.file,
                    status: 'ready'
                };
            }
            console.log('[FILES] Upload concluído:', data.file.name);
        } else {
            // Marca como erro
            const idx = attachedFiles.findIndex(f => f.id === tempId);
            if (idx !== -1) {
                attachedFiles[idx].status = 'error';
                attachedFiles[idx].error = data.error;
            }
            console.error('[FILES] Erro no upload:', data.error);
        }
    } catch (error) {
        console.error('[FILES] Erro no upload:', error);
        const idx = attachedFiles.findIndex(f => f.id === tempId);
        if (idx !== -1) {
            attachedFiles[idx].status = 'error';
            attachedFiles[idx].error = error.message;
        }
    }

    renderAttachments();
    updateAttachButton();
}

/**
 * Retorna o tipo do arquivo baseado na extensão
 */
function getFileType(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (['png', 'jpg', 'jpeg', 'gif'].includes(ext)) return 'image';
    if (ext === 'pdf') return 'pdf';
    if (['xlsx', 'xls'].includes(ext)) return 'excel';
    if (ext === 'csv') return 'csv';
    return 'file';
}

/**
 * Retorna o ícone do arquivo baseado no tipo
 */
function getFileIcon(type) {
    const icons = {
        'pdf': 'fa-file-pdf',
        'excel': 'fa-file-excel',
        'csv': 'fa-file-csv',
        'image': 'fa-file-image',
        'file': 'fa-file'
    };
    return icons[type] || 'fa-file';
}

/**
 * Formata tamanho do arquivo
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Renderiza lista de anexos
 */
function renderAttachments() {
    const list = document.getElementById('attachments-list');
    const section = document.getElementById('attachments-section');

    if (!list || !section) return;

    if (attachedFiles.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    list.innerHTML = attachedFiles.map(file => `
        <div class="file-item ${file.status || ''}">
            <div class="file-icon ${file.type}">
                <i class="fas ${getFileIcon(file.type)}"></i>
            </div>
            <div class="file-info">
                <div class="file-name" title="${file.original_name}">${file.original_name}</div>
                <div class="file-size">${formatFileSize(file.size)}</div>
            </div>
            <div class="file-actions">
                <button class="remove" onclick="removeAttachment('${file.id}')" title="Remover">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Remove um anexo
 */
async function removeAttachment(fileId) {
    const file = attachedFiles.find(f => f.id === fileId);
    if (!file) return;

    // Se já foi uploaded, remove do servidor
    if (file.url) {
        try {
            await fetch(file.url, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            });
        } catch (e) {
            console.log('[FILES] Erro ao remover do servidor:', e);
        }
    }

    attachedFiles = attachedFiles.filter(f => f.id !== fileId);
    renderAttachments();
    updateAttachButton();
    updateFilesPanel();
}

/**
 * Limpa todos os anexos
 */
async function clearAttachments() {
    for (const file of attachedFiles) {
        if (file.url) {
            try {
                await fetch(file.url, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                    }
                });
            } catch (e) {}
        }
    }
    attachedFiles = [];
    renderAttachments();
    updateAttachButton();
    updateFilesPanel();
}

/**
 * Adiciona um arquivo à lista de downloads
 */
function addDownloadFile(file) {
    // Evita duplicados
    if (downloadFiles.some(f => f.url === file.url)) return;

    downloadFiles.push(file);
    renderDownloads();
    showFilesPanel();
}

/**
 * Renderiza lista de downloads
 */
function renderDownloads() {
    const list = document.getElementById('downloads-list');
    const section = document.getElementById('downloads-section');

    if (!list || !section) return;

    if (downloadFiles.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    list.innerHTML = downloadFiles.map((file, idx) => `
        <div class="file-item">
            <div class="file-icon ${file.type || 'file'}">
                <i class="fas ${getFileIcon(file.type || 'file')}"></i>
            </div>
            <div class="file-info">
                <div class="file-name" title="${file.name}">${file.name}</div>
                <div class="file-size">${file.size ? formatFileSize(file.size) : ''}</div>
            </div>
            <div class="file-actions">
                <a href="${file.url}" class="download" download title="Baixar">
                    <i class="fas fa-download"></i>
                </a>
                <button class="remove" onclick="removeDownload(${idx})" title="Remover da lista">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Remove um download da lista
 */
function removeDownload(idx) {
    downloadFiles.splice(idx, 1);
    renderDownloads();
    updateFilesPanel();
}

/**
 * Limpa lista de downloads
 */
function clearDownloads() {
    downloadFiles = [];
    renderDownloads();
    updateFilesPanel();
}

/**
 * Mostra o painel de arquivos
 */
function showFilesPanel() {
    const panel = document.getElementById('files-panel');
    if (panel && (attachedFiles.length > 0 || downloadFiles.length > 0)) {
        panel.style.display = 'block';
    }
}

/**
 * Atualiza visibilidade do painel de arquivos
 */
function updateFilesPanel() {
    const panel = document.getElementById('files-panel');
    if (panel) {
        if (attachedFiles.length === 0 && downloadFiles.length === 0) {
            panel.style.display = 'none';
        } else {
            panel.style.display = 'block';
        }
    }
}

/**
 * Atualiza o botão de anexar
 */
function updateAttachButton() {
    const btn = document.querySelector('.btn-attach');
    if (btn) {
        if (attachedFiles.length > 0) {
            btn.classList.add('has-files');
        } else {
            btn.classList.remove('has-files');
        }
    }
}

/**
 * Retorna os arquivos anexados para enviar com a mensagem
 */
function getAttachedFilesForMessage() {
    return attachedFiles
        .filter(f => f.status === 'ready' && f.url)
        .map(f => ({
            name: f.original_name,
            url: f.url,
            type: f.type,
            size: f.size
        }));
}

/**
 * Detecta URLs de arquivos na resposta do agente e adiciona aos downloads
 *
 * Padroes detectados:
 * - URLs HTTP completas terminando em extensoes de arquivo
 * - URLs relativas /agente/api/files/...
 * - Links markdown [texto](url)
 */
function detectDownloadUrls(text) {
    // Detecta padrões de URL de arquivo
    // [^\s\)\"\'\]\>] exclui espacos, ), ", ', ], > para nao capturar marcadores markdown
    const urlPattern = /(?:https?:\/\/[^\s\)\"\'\]\>]+\.(?:xlsx|xls|csv|pdf|png|jpg|jpeg|gif))|(?:\/agente\/api\/files\/[^\s\)\"\'\]\>]+)/gi;
    const matches = text.match(urlPattern);

    if (matches) {
        matches.forEach(url => {
            // Remove caracteres extras que podem ter sido capturados
            url = url.replace(/[\)\]\>]+$/, '');

            const filename = url.split('/').pop().split('?')[0];

            // Extrai nome original (remove prefixo UUID se existir)
            let displayName = filename;
            if (filename.match(/^[a-f0-9]{8}_/)) {
                displayName = filename.substring(9); // Remove "xxxxxxxx_"
            }

            addDownloadFile({
                name: displayName,
                url: url,
                type: getFileType(filename)
            });
        });
    }
}

// ============================================
// INICIALIZAÇÃO
// ============================================
// Carrega contagem de sessões ao iniciar
fetch('/agente/api/sessions?limit=1', {
    headers: {
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
    }
})
.then(r => r.json())
.then(data => {
    if (data.success && data.sessions) {
        // Busca total real
        fetch('/agente/api/sessions?limit=50', {
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
            }
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                updateSessionsCount(data.sessions.length);
            }
        });
    }
})
.catch(() => {});

// Verifica saúde do serviço
fetch('/agente/api/health')
    .then(r => r.json())
    .then(data => {
        if (!data.success || data.status !== 'healthy') {
            addMessage('⚠️ O serviço pode estar com problemas. Algumas funcionalidades podem não funcionar corretamente.', 'assistant');
        }
    })
    .catch(() => {
        // Silencioso
    });

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
let currentModel = 'claude-sonnet-4-6';

// Effort Level (Adaptive Thinking): auto|off|low|medium|high|max
let effortLevel = 'auto';

// FEAT-010: Plan Mode ativado
let planModeEnabled = false;

// Debug Mode (admin only)
let debugModeEnabled = false;

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

// Auto-retry: revive sessão após error_recovery (exit code 1 por inatividade)
let _lastUserMessage = null;
let _autoRetryCount = 0;
const _MAX_AUTO_RETRIES = 1;

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
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
            },
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
    'claude-sonnet-4-6': {
        name: 'Sonnet',
        description: 'Equilibrado. Bom para a maioria das tarefas.',
        speed: '⚡⚡',
        cost: '$$'
    },
    'claude-opus-4-7': {
        name: 'Opus',
        description: 'Mais potente. Para análises complexas e planejamento.',
        speed: '⚡',
        cost: '$$$'
    },
    // Legado: sessoes antigas reportam 4.6 — manter entrada para display correto
    'claude-opus-4-6': {
        name: 'Opus (legado)',
        description: 'Versao anterior. Mesmo preco do 4.7.',
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
// EFFORT LEVEL SELECTOR (Adaptive Thinking)
// ============================================

/**
 * Resolve effort level quando "auto" — baseado no modelo selecionado.
 * Opus → high, Haiku → off, Sonnet/default → medium
 */
function resolveEffortLevel() {
    if (effortLevel !== 'auto') return effortLevel;
    if (currentModel.includes('opus')) return 'high';
    if (currentModel.includes('haiku')) return 'off';
    return 'medium'; // Sonnet = default
}

// Event listeners para botões de effort (delegação no container)
const effortSelector = document.getElementById('effort-selector');
if (effortSelector) {
    effortSelector.querySelectorAll('.effort-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            effortSelector.querySelectorAll('.effort-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            effortLevel = this.dataset.effort;

            // Validação: "max" só para Opus
            if (effortLevel === 'max' && !currentModel.includes('opus')) {
                console.warn('[AGENTE] Effort "max" requer Opus. Usando "high" como fallback.');
            }

            console.log('[AGENTE] Effort level:', effortLevel, '→ resolve:', resolveEffortLevel());
        });
    });
}

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
// DEBUG MODE TOGGLE (Admin only)
// ============================================
const debugModeToggle = document.getElementById('debug-mode-toggle');
const debugModeBanner = document.getElementById('debug-mode-banner');

if (debugModeToggle) {
    // Restaurar de localStorage
    const savedDebug = localStorage.getItem('agent-debug-mode');
    if (savedDebug === 'true') {
        debugModeToggle.checked = true;
        debugModeEnabled = true;
        if (debugModeBanner) debugModeBanner.style.display = 'block';
    }

    debugModeToggle.addEventListener('change', function() {
        debugModeEnabled = this.checked;
        localStorage.setItem('agent-debug-mode', this.checked.toString());

        if (debugModeBanner) {
            debugModeBanner.style.display = this.checked ? 'block' : 'none';
        }

        // Mostrar/ocultar debug panel
        const debugPanel = document.getElementById('debug-panel');
        if (debugPanel) {
            debugPanel.classList.toggle('hidden', !this.checked);
        }

        console.log('[AGENTE] Debug Mode:', debugModeEnabled ? 'ATIVADO' : 'DESATIVADO');
    });
}

// ============================================
// DEBUG PANEL — Stderr output (Admin only)
// ============================================
const MAX_DEBUG_LINES = 500;
let debugLineCount = 0;

function appendDebugLine(line) {
    const debugBody = document.getElementById('debug-body');
    if (!debugBody) return;

    const panel = document.getElementById('debug-panel');
    if (panel && panel.classList.contains('hidden') && debugLineCount === 0) {
        // Auto-show apenas na primeira linha (não reabre se o usuário fechou)
        panel.classList.remove('hidden');
    }

    // Classificar a linha para coloração
    const entry = document.createElement('div');
    entry.className = 'debug-line';
    if (line.includes('[DEBUG]')) {
        entry.classList.add('debug-level-debug');
    } else if (line.includes('[WARN]') || line.includes('[WARNING]')) {
        entry.classList.add('debug-level-warn');
    } else if (line.includes('[ERROR]')) {
        entry.classList.add('debug-level-error');
    }

    const time = new Date().toLocaleTimeString('pt-BR', { hour12: false, fractionalSecondDigits: 1 });
    entry.textContent = `[${time}] ${line}`;
    debugBody.appendChild(entry);

    // Limitar linhas para evitar memory leak
    debugLineCount++;
    if (debugLineCount > MAX_DEBUG_LINES) {
        const first = debugBody.firstChild;
        if (first) debugBody.removeChild(first);
        debugLineCount--;
    }

    // Auto-scroll para o final
    debugBody.scrollTop = debugBody.scrollHeight;

    // Atualizar contador
    const counter = document.getElementById('debug-line-count');
    if (counter) counter.textContent = debugLineCount.toString();
}

function clearDebugPanel() {
    const debugBody = document.getElementById('debug-body');
    if (debugBody) debugBody.innerHTML = '';
    debugLineCount = 0;
    const counter = document.getElementById('debug-line-count');
    if (counter) counter.textContent = '0';
}

function toggleDebugPanel() {
    const panel = document.getElementById('debug-panel');
    if (panel) panel.classList.toggle('hidden');
}

function filterDebugLines(level) {
    const debugBody = document.getElementById('debug-body');
    if (!debugBody) return;
    const lines = debugBody.querySelectorAll('.debug-line');
    lines.forEach(line => {
        if (level === 'all') {
            line.style.display = '';
        } else {
            line.style.display = line.classList.contains(`debug-level-${level}`) ? '' : 'none';
        }
    });
    // Highlight active filter button
    document.querySelectorAll('.debug-filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.level === level);
    });
}

// ============================================
// SDK Structured Output Renderer
// ============================================
function renderStructuredOutput(data, container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'structured-output';

    // Se for array de objetos: renderizar como tabela
    if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'object') {
        wrapper.appendChild(createTable(data));
    } else if (typeof data === 'object' && !Array.isArray(data)) {
        // Objeto: se tem arrays dentro que parecem tabelas, renderizar misto
        const hasArrayProp = Object.values(data).some(v => Array.isArray(v) && v.length > 0 && typeof v[0] === 'object');
        if (hasArrayProp) {
            // Renderizar campos simples como badges + arrays como tabelas
            const simpleFields = document.createElement('div');
            simpleFields.className = 'structured-output-fields';
            for (const [key, val] of Object.entries(data)) {
                if (Array.isArray(val) && val.length > 0 && typeof val[0] === 'object') {
                    const label = document.createElement('div');
                    label.className = 'structured-output-section-label';
                    label.textContent = formatFieldName(key);
                    wrapper.appendChild(label);
                    wrapper.appendChild(createTable(val));
                } else {
                    const badge = createFieldBadge(key, val);
                    simpleFields.appendChild(badge);
                }
            }
            if (simpleFields.childNodes.length > 0) {
                wrapper.insertBefore(simpleFields, wrapper.firstChild);
            }
        } else {
            // Objeto simples: renderizar como JSON collapsible
            wrapper.appendChild(createJsonViewer(data));
        }
    } else {
        // Fallback: JSON puro
        wrapper.appendChild(createJsonViewer(data));
    }

    // Inserir após o conteúdo da mensagem (fallback para container se .message-bubble ausente)
    const bubble = container.querySelector('.message-bubble');
    (bubble || container).appendChild(wrapper);
}

function createTable(rows) {
    const table = document.createElement('table');
    table.className = 'structured-output-table markdown-table';
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    const keys = Object.keys(rows[0]);
    keys.forEach(key => {
        const th = document.createElement('th');
        th.textContent = formatFieldName(key);
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    rows.forEach(row => {
        const tr = document.createElement('tr');
        keys.forEach(key => {
            const td = document.createElement('td');
            const val = row[key];
            td.textContent = val === null || val === undefined ? '-' : String(val);
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
}

function createFieldBadge(key, value) {
    const el = document.createElement('span');
    el.className = 'structured-output-badge';
    const label = document.createElement('span');
    label.className = 'structured-output-badge-label';
    label.textContent = formatFieldName(key);
    const val = document.createElement('span');
    val.className = 'structured-output-badge-value';
    if (typeof value === 'boolean') {
        val.textContent = value ? 'Sim' : 'Nao';
        val.classList.add(value ? 'badge-true' : 'badge-false');
    } else {
        val.textContent = String(value);
    }
    el.appendChild(label);
    el.appendChild(val);
    return el;
}

function createJsonViewer(data) {
    const details = document.createElement('details');
    details.className = 'structured-output-json';
    const summary = document.createElement('summary');
    summary.textContent = 'JSON Output';
    details.appendChild(summary);
    const pre = document.createElement('pre');
    const code = document.createElement('code');
    code.className = 'language-json';
    code.textContent = JSON.stringify(data, null, 2);
    pre.appendChild(code);
    details.appendChild(pre);
    // Tentar highlight se hljs disponível
    if (typeof hljs !== 'undefined') {
        try { hljs.highlightElement(code); } catch(e) { /* ignore */ }
    }
    return details;
}

function formatFieldName(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// ============================================
// FEAT-003: PAINEL DE THINKING
// ============================================
function toggleThinkingPanel() {
    const panel = document.getElementById('thinking-panel');
    const toggleBtn = document.getElementById('thinking-toggle-btn');

    if (panel.style.display === 'none' || panel.style.display === '') {
        // Abrir painel
        panel.style.display = 'block';
        toggleBtn.style.display = 'none';
    } else {
        // Fechar painel totalmente — mostrar botão flutuante
        panel.style.display = 'none';
        const text = document.getElementById('thinking-text');
        if (text && text.innerHTML.trim()) {
            toggleBtn.style.display = 'flex';
        }
    }
}

function showThinking(content) {
    const panel = document.getElementById('thinking-panel');
    const text = document.getElementById('thinking-text');
    const status = document.getElementById('thinking-status');
    const toggleBtn = document.getElementById('thinking-toggle-btn');

    panel.style.display = 'block';
    toggleBtn.style.display = 'none';
    status.textContent = 'Pensando...';
    text.innerHTML += formatMessage(content);
    text.scrollTop = text.scrollHeight;
}

function hideThinkingPanel() {
    const panel = document.getElementById('thinking-panel');
    const status = document.getElementById('thinking-status');
    const toggleBtn = document.getElementById('thinking-toggle-btn');

    if (status) {
        status.textContent = 'Concluído';
    }
    // Auto-colapsa apos conclusao — botão flutuante permite reabrir
    panel.style.display = 'none';
    toggleBtn.style.display = 'flex';
}

function clearThinking() {
    const panel = document.getElementById('thinking-panel');
    const text = document.getElementById('thinking-text');
    const toggleBtn = document.getElementById('thinking-toggle-btn');
    panel.style.display = 'none';
    toggleBtn.style.display = 'none';
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
    _lastUserMessage = message;  // Auto-retry: guarda para possível retry
    _autoRetryCount = 0;         // Reset retry counter para cada nova mensagem
    messageInput.value = '';
    sendBtn.disabled = true;

    // FEAT-026: Reseta altura do textarea
    messageInput.style.height = 'auto';

    // Limpa thinking anterior
    clearThinking();

    // P1-1: Remove chips de sugestão anteriores
    document.querySelectorAll('.suggestion-chips').forEach(el => el.remove());

    // Mostra indicador e botão stop — mensagem varia por effort level
    const resolved = resolveEffortLevel();
    const typingMessages = {
        max:    '🧠 Pensamento máximo...',
        high:   '🧠 Pensando profundamente...',
        medium: '🔍 Analisando...',
        low:    '⚡ Processando rápido...',
        off:    'Processando...',
    };
    showTyping(typingMessages[resolved] || 'Processando...');
    showStopButton(); // FEAT-026

    // FEAT-028: Obtém arquivos anexados
    const files = getAttachedFilesForMessage();

    try {
        const response = await _fetchWithCsrfRetry('/agente/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                model: currentModel,              // FEAT-001: Modelo selecionado
                effort_level: resolveEffortLevel(), // Adaptive Thinking effort
                plan_mode: planModeEnabled,       // FEAT-010: Plan Mode
                debug_mode: debugModeEnabled,     // Debug Mode (admin)
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

// ─── Subagent inline expansible line (#6) ────────────────────────────
// Map agent_id -> DOM element para atualizar linha existente ao receber
// eventos subsequentes (task_progress, subagent_summary, subagent_validation).
const subagentLines = new Map();

function _subagentEscapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = String(str ?? '');
    return div.innerHTML;
}

function renderSubagentLineStart(data) {
    // data: {task_id, task_type, description} ou {agent_id, agent_type}
    const agentId = data.agent_id || data.task_id;
    const agentType = data.agent_type || data.task_type || data.description || 'subagente';

    if (!agentId || subagentLines.has(agentId)) return;  // idempotente

    const messagesContainer = document.getElementById('messages') ||
                              document.querySelector('.messages-container') ||
                              document.querySelector('.chat-messages');
    if (!messagesContainer) {
        console.warn('[subagent-ui] container #messages nao encontrado');
        return;
    }

    const line = document.createElement('div');
    line.className = 'subagent-inline running';
    line.dataset.agentId = agentId;
    line.innerHTML = `
        <span class="subagent-dot"></span>
        <span class="subagent-badge">${_subagentEscapeHtml(agentType)}</span>
        <span class="subagent-meta">executando\u2026</span>
        <span class="subagent-caret">\u25bc</span>
    `;
    line.addEventListener('click', () => toggleSubagentExpand(agentId));
    messagesContainer.appendChild(line);
    subagentLines.set(agentId, line);
}

function renderSubagentLineProgress(data) {
    const agentId = data.agent_id || data.task_id;
    const line = subagentLines.get(agentId);
    if (!line) return;
    const meta = line.querySelector('.subagent-meta');
    const tool = data.last_tool_name || 'processando';
    if (meta) meta.textContent = `usando ${tool}\u2026`;
}

function renderSubagentLineSummary(data) {
    // data: SubagentSummary.to_dict() sanitizado por perfil
    const agentId = data.agent_id;
    if (!agentId) return;

    let line = subagentLines.get(agentId);

    if (!line) {
        // Fallback: evento chegou sem task_started anterior
        const messagesContainer = document.getElementById('messages') ||
                                  document.querySelector('.messages-container') ||
                                  document.querySelector('.chat-messages');
        if (!messagesContainer) return;
        line = document.createElement('div');
        line.className = 'subagent-inline';
        line.dataset.agentId = agentId;
        messagesContainer.appendChild(line);
        subagentLines.set(agentId, line);
        line.addEventListener('click', () => toggleSubagentExpand(agentId));
    }

    line.classList.remove('running');
    line.classList.add('done');

    const numTools = (data.tools_used || []).length;
    const durationSec = Math.round((data.duration_ms || 0) / 100) / 10;
    const costStr = data.cost_usd != null
        ? ` \u00b7 $${Number(data.cost_usd).toFixed(4)}`
        : '';
    const metaText = `${numTools} tool${numTools !== 1 ? 's' : ''} \u00b7 ${durationSec}s${costStr}`;

    line.innerHTML = `
        <span class="subagent-dot"></span>
        <span class="subagent-badge">${_subagentEscapeHtml(data.agent_type || 'subagente')}</span>
        <span class="subagent-meta">${_subagentEscapeHtml(metaText)}</span>
        <span class="subagent-caret">\u25bc</span>
    `;
    line.dataset.summary = JSON.stringify(data);
}

function renderSubagentValidationWarning(data) {
    // data: {agent_id, agent_type, score, reason, flagged_claims}
    const line = subagentLines.get(data.agent_id);
    if (!line) return;

    const badge = line.querySelector('.subagent-badge');
    if (badge && !line.querySelector('.validation-warning')) {
        const warn = document.createElement('span');
        warn.className = 'validation-warning';
        warn.title = `Score: ${data.score} \u2014 ${data.reason || ''}`;
        badge.after(warn);
    }
    line.dataset.validation = JSON.stringify(data);
}

async function toggleSubagentExpand(agentId) {
    const line = subagentLines.get(agentId);
    if (!line) return;

    if (line.classList.contains('expanded')) {
        line.classList.remove('expanded');
        const details = line.querySelector('.subagent-inline-details');
        if (details) details.remove();
        const header = line.querySelector('.subagent-header');
        if (header) {
            // Restaurar do summary
            const data = JSON.parse(line.dataset.summary || '{}');
            const numTools = (data.tools_used || []).length;
            const durationSec = Math.round((data.duration_ms || 0) / 100) / 10;
            const costStr = data.cost_usd != null
                ? ` \u00b7 $${Number(data.cost_usd).toFixed(4)}`
                : '';
            line.innerHTML = `
                <span class="subagent-dot"></span>
                <span class="subagent-badge">${_subagentEscapeHtml(data.agent_type || 'subagente')}</span>
                <span class="subagent-meta">${_subagentEscapeHtml(numTools + ' tools \u00b7 ' + durationSec + 's' + costStr)}</span>
                <span class="subagent-caret">\u25bc</span>
            `;
        }
        return;
    }

    line.classList.add('expanded');
    const originalHtml = line.innerHTML;
    line.innerHTML = `<div class="subagent-header">${originalHtml}</div>`;

    const details = document.createElement('div');
    details.className = 'subagent-inline-details';
    details.textContent = 'Carregando\u2026';
    line.appendChild(details);

    // Descobrir session_id: usar variavel global sessionId do chat.js
    const sid = sessionId;

    if (!sid) {
        details.textContent = 'Erro: sessao nao identificada';
        return;
    }

    try {
        const resp = await fetch(
            `/agente/api/sessions/${sid}/subagents/${agentId}/summary`
        );
        if (!resp.ok) {
            details.textContent = `Erro ${resp.status}`;
            return;
        }
        const payload = await resp.json();
        const s = payload.subagent || {};
        const toolsHtml = (s.tools_used || []).map((t) =>
            `<li><span class="tool-name">${_subagentEscapeHtml(t.name)}</span>` +
            `<span class="tool-result">${_subagentEscapeHtml((t.result_summary || '').slice(0, 120))}</span></li>`
        ).join('');
        const validationHtml = line.dataset.validation
            ? (() => {
                const v = JSON.parse(line.dataset.validation);
                return `<div class="validation-reason">Score ${v.score}: ${_subagentEscapeHtml(v.reason || '')}</div>`;
              })()
            : '';
        const findingsHtml = s.findings_text
            ? `<div style="margin-top:8px;color:var(--agent-text-secondary)">${_subagentEscapeHtml(s.findings_text.slice(0, 400))}</div>`
            : '';
        details.innerHTML = `<ol>${toolsHtml}</ol>${validationHtml}${findingsHtml}`;
    } catch (err) {
        details.textContent = `Erro: ${err.message}`;
    }
}

// ─────────────────────────────────────────────────────────────────────

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
                if (resolveEffortLevel() !== 'off' && data.content) {
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

            // SDK 0.1.48: Subagente iniciou — feedback imediato
            case 'task_started': {
                const taskDesc = data.description || 'subagente';
                const taskType = data.task_type || '';
                const agentLabel = taskType === 'local_agent'
                    ? taskDesc.split(' ').slice(0, 4).join(' ')
                    : taskDesc;
                showTyping(`🤖 Delegando: ${agentLabel}...`);
                addTimelineItem({
                    tool_name: `Subagente`,
                    description: agentLabel,
                    status: 'pending',
                    timestamp: new Date()
                });
                renderSubagentLineStart(data);  // NOVO: linha inline expansivel (#6)
                console.log(`[SSE] Subagente iniciado: ${taskDesc} (type=${taskType})`);
                break;
            }

            // SDK 0.1.48: Progresso de subagente
            case 'task_progress': {
                const progressDesc = data.description || '';
                const lastTool = data.last_tool_name || '';
                if (lastTool) {
                    showTyping(`🤖 Subagente usando ${lastTool}...`);
                }
                renderSubagentLineProgress(data);  // NOVO: atualiza linha inline (#6)
                console.log(`[SSE] Subagente progresso: ${progressDesc} (last_tool=${lastTool})`);
                break;
            }

            // SDK 0.1.48: Subagente concluiu
            case 'task_notification': {
                const notifStatus = data.status || '';
                const notifSummary = data.summary || '';
                const isSuccess = notifStatus === 'completed';

                // Atualiza ultimo item de timeline (subagente)
                updateLastTimelineItem({
                    status: isSuccess ? 'success' : 'error',
                    duration_ms: 0
                });

                if (isSuccess) {
                    showTyping('📋 Processando resultado do subagente...');
                } else {
                    showTyping(`⚠️ Subagente finalizou: ${notifStatus}`);
                }
                console.log(`[SSE] Subagente concluiu: status=${notifStatus} summary=${notifSummary.substring(0, 80)}`);
                break;
            }

            // NOVO (#6): Summary de subagente (dados completos apos conclusao)
            case 'subagent_summary':
                renderSubagentLineSummary(data);
                break;

            // NOVO (#4): Validacao de subagente — icone de aviso na linha
            case 'subagent_validation':
                renderSubagentValidationWarning(data);
                break;

            case 'rate_limit': {
                // SDK 0.1.50: Rate limit event
                const rlStatus = data.status || '';
                if (rlStatus === 'allowed_warning') {
                    showToast('⚠️ Uso elevado da API — respostas podem demorar', 8000);
                    console.log(`[SSE] Rate limit warning: ${(data.utilization * 100).toFixed(0)}% utilizado`);
                } else if (rlStatus === 'rejected') {
                    const resetDate = data.resets_at ? new Date(data.resets_at) : null;
                    const resetStr = resetDate ? resetDate.toLocaleTimeString() : 'em breve';
                    showToast(`🛑 Limite de uso atingido — aguarde até ${resetStr}`, 15000);
                    console.warn(`[SSE] Rate limit REJECTED: type=${data.rate_limit_type}, resets_at=${data.resets_at}`);
                }
                break;
            }

            // SDK stderr callback: debug output do CLI subprocess (admin-only)
            case 'stderr': {
                if (debugModeEnabled) {
                    appendDebugLine(data.line || '');
                }
                break;
            }

            case 'warning': {
                // Resume de sessão falhou — notificar usuário
                const warningMsg = data.content || data.message || 'Aviso do sistema';
                const warnEl = createMessageElement(`⚠️ ${warningMsg}`, 'assistant');
                warnEl.classList.add('message-warning');
                chatMessages.appendChild(warnEl);
                scrollToBottom();
                console.warn(`[SSE] Warning: reason=${data.reason}`, data);
                break;
            }

            case 'error': {
                hideTyping();
                hideThinkingPanel();

                // FEAT-030: Finaliza todos os items pendentes (timeline e todos)
                finalizePendingTimelineItems('error');
                finalizePendingTodos(false);  // Não marca como completed, apenas para o spinner

                // Auto-retry: se process_error (exit code 1 por inatividade) e temos
                // a última mensagem, retry transparente em vez de mostrar erro.
                const isProcessError = data.error_type === 'process_error';
                if (isProcessError && _lastUserMessage && _autoRetryCount < _MAX_AUTO_RETRIES) {
                    _autoRetryCount++;
                    console.log(`[SSE] Process error detected, scheduling auto-retry #${_autoRetryCount}`);
                    addMessage('🔄 Reconectando sessão...', 'assistant');
                    setTimeout(() => {
                        // Remove a mensagem "Reconectando..." antes de reenviar
                        const msgs = document.querySelectorAll('.message.assistant');
                        const lastMsg = msgs[msgs.length - 1];
                        if (lastMsg && lastMsg.textContent.includes('Reconectando')) {
                            lastMsg.remove();
                        }
                        messageInput.value = _lastUserMessage;
                        sendMessage(null);
                    }, 2000);
                    break;
                }

                // FEAT-030: Trata sessão expirada
                if (data.session_expired) {
                    console.log('[SSE] Sessão SDK expirada, será criada nova na próxima mensagem');
                    addMessage(`⚠️ A sessão anterior expirou no servidor.\n\n**Mas não se preocupe!** Seu histórico está salvo e a conversa continuará normalmente.`, 'assistant');
                } else {
                    addMessage(`❌ ${data.message || data.content || 'Erro desconhecido'}`, 'assistant');
                }
                break;
            }

            case 'memory_saved':
                // FEAT-031: Notificação sutil quando memória é salva
                showToast(data.message || '💾 Memória salva', 3000);
                console.log('[SSE] Memória salva:', data);
                break;

            // FEAT-ASK: AskUserQuestion — perguntas interativas do agente
            // O agente quer perguntar algo ao usuário (multiple choice)
            // Renderiza cards clicáveis e envia resposta via POST /api/user-answer
            case 'ask_user_question': {
                hideTyping();
                const questions = data.questions || [];
                const askSessionId = data.session_id || sessionId;

                if (questions.length > 0) {
                    console.log(`[SSE] AskUserQuestion: ${questions.length} pergunta(s)`, questions);
                    renderAskUserQuestion(questions, askSessionId, state);
                }
                break;
            }

            case 'done':
                hideTyping();
                hideThinkingPanel();
                isGenerating = false;  // FIX-6: Para feedbackTimer e sinaliza fim do while loop
                if (data.session_id) sessionId = data.session_id;
                updateMetrics(data.input_tokens, data.output_tokens, data.cost_usd);

                // FEAT-030: Finaliza items pendentes (timeline e todos)
                finalizePendingTimelineItems('success');
                finalizePendingTodos(true);  // Marca como completed

                // SDK structured output: renderizar JSON se output_format ativo
                if (data.structured_output && state.msgElement) {
                    renderStructuredOutput(data.structured_output, state.msgElement);
                }

                // Adicionar botões de feedback à mensagem streamed
                if (state.msgElement && state.text && state.text.trim()) {
                    injectFeedbackButtons(state.msgElement, state.text);
                }

                // Sessao A: Atualizar indicador de contexto
                if (data.context_usage) {
                    updateContextUsage(data.context_usage);
                }
                break;

            // P1-1: Sugestões de prompt contextuais (chips clicáveis)
            case 'suggestions': {
                const suggestions = data.suggestions || [];
                if (suggestions.length > 0 && state.msgElement) {
                    renderSuggestionChips(suggestions, state.msgElement);
                }
                break;
            }

            // P2-3: Aviso de ação destrutiva (reversibilidade)
            case 'destructive_action_warning': {
                renderDestructiveWarning(data, state.msgElement);
                break;
            }
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

/**
 * Exibe um toast de notificação sutil (reutiliza estilo voice-feedback).
 * @param {string} message - Texto do toast
 * @param {number} duration - Duração em ms (default 3000)
 */
function showToast(message, duration = 3000) {
    // Reutilizar elemento existente ou criar novo
    let toast = document.getElementById('agent-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'agent-toast';
        toast.className = 'voice-feedback';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.display = 'flex';
    toast.style.opacity = '1';
    toast.style.transition = 'opacity 0.3s ease';

    // Auto-hide com fade
    clearTimeout(toast._hideTimeout);
    toast._hideTimeout = setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => { toast.style.display = 'none'; }, 300);
    }, duration);
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

    // Botões de feedback apenas para mensagens do assistente com conteúdo
    const feedbackButtons = (role === 'assistant' && text && text.trim()) ? `
        <div class="message-feedback" style="display:flex;gap:4px;margin-top:4px;">
            <button class="feedback-btn" data-rating="positive" title="Boa resposta"
                    style="background:none;border:none;cursor:pointer;padding:2px 6px;border-radius:4px;opacity:0.4;font-size:14px;transition:opacity 0.2s,background 0.2s;"
                    onmouseover="this.style.opacity='1';this.style.background='rgba(255,255,255,0.1)'"
                    onmouseout="if(!this.classList.contains('active'))this.style.opacity='0.4';this.style.background='none'">
                👍
            </button>
            <button class="feedback-btn" data-rating="negative" title="Resposta pode melhorar"
                    style="background:none;border:none;cursor:pointer;padding:2px 6px;border-radius:4px;opacity:0.4;font-size:14px;transition:opacity 0.2s,background 0.2s;"
                    onmouseover="this.style.opacity='1';this.style.background='rgba(255,255,255,0.1)'"
                    onmouseout="if(!this.classList.contains('active'))this.style.opacity='0.4';this.style.background='none'">
                👎
            </button>
        </div>
    ` : '';

    div.innerHTML = `
        <div class="message-avatar">
            <i class="fas ${icon}"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble">${formattedText}</div>
            <div class="message-time">${new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</div>
            ${feedbackButtons}
        </div>
    `;

    // Attach feedback handlers
    if (role === 'assistant' && text && text.trim()) {
        div.querySelectorAll('.feedback-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const rating = this.dataset.rating;
                sendFeedback(rating, text);

                // Visual feedback: destaca o botão clicado, esconde o outro
                const parent = this.closest('.message-feedback');
                parent.querySelectorAll('.feedback-btn').forEach(b => {
                    b.disabled = true;
                    if (b === this) {
                        b.classList.add('active');
                        b.style.opacity = '1';
                    } else {
                        b.style.display = 'none';
                    }
                });

                if (rating === 'positive') {
                    showToast('Obrigado!', 2000);
                } else {
                    showToast('Anotado!', 2000);
                    // Mostrar formulário de correção inline (opcional, baixa fricção)
                    showCorrectionForm(parent, text);
                }
            });
        });
    }

    return div;
}

/**
 * Envia feedback sobre uma resposta do assistente.
 * @param {string} rating - 'positive' ou 'negative'
 * @param {string} context - Texto da mensagem avaliada
 */
function sendFeedback(rating, context, extraData) {
    if (!sessionId) return;

    const payload = {
        session_id: sessionId,
        type: rating,
        data: {
            context: (context || '').substring(0, 500),
            message_text: (context || '').substring(0, 500),  // Sessao E: inclui texto para feedback positivo
        }
    };
    if (extraData) {
        Object.assign(payload.data, extraData);
    }

    _fetchWithCsrfRetry('/agente/api/feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
        },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        console.log('[FEEDBACK] Enviado:', rating, data);
    })
    .catch(err => {
        console.error('[FEEDBACK] Erro ao enviar:', err);
    });
}

/**
 * Mostra formulário inline de correção após thumbs-down.
 * Baixa fricção: o thumbs-down já foi registrado, a correção é opcional.
 */
function showCorrectionForm(feedbackDiv, assistantText) {
    // Não mostrar se já tem formulário
    if (feedbackDiv.querySelector('.correction-form')) return;

    const form = document.createElement('div');
    form.className = 'correction-form';
    form.style.cssText = 'margin-top:8px;padding:8px;border-radius:6px;background:var(--bg-light,#f8f9fa);border:1px solid var(--border-light,#dee2e6);';
    form.innerHTML = `
        <div style="font-size:12px;color:var(--text-muted,#6c757d);margin-bottom:6px;">Quer explicar o erro? (opcional)</div>
        <textarea class="correction-text" placeholder="O que você queria que o agente fizesse?"
            style="width:100%;min-height:48px;padding:6px;border:1px solid var(--border-light,#dee2e6);border-radius:4px;font-size:13px;background:var(--bg,#fff);color:var(--text,#212529);resize:vertical;"
        ></textarea>
        <div style="display:flex;gap:6px;margin-top:6px;align-items:center;">
            <select class="correction-category" style="padding:4px 8px;border:1px solid var(--border-light,#dee2e6);border-radius:4px;font-size:12px;background:var(--bg,#fff);color:var(--text,#212529);">
                <option value="">Categoria do erro</option>
                <option value="routing">Usou ferramenta errada</option>
                <option value="dados">Dados incorretos</option>
                <option value="interpretacao">Entendeu errado o pedido</option>
                <option value="outro">Outro</option>
            </select>
            <button class="correction-submit" style="padding:4px 12px;border:none;border-radius:4px;background:var(--primary,#0d6efd);color:#fff;font-size:12px;cursor:pointer;">Enviar</button>
            <button class="correction-cancel" style="padding:4px 8px;border:none;background:none;color:var(--text-muted,#6c757d);font-size:12px;cursor:pointer;">Cancelar</button>
        </div>
    `;

    feedbackDiv.after(form);

    form.querySelector('.correction-submit').addEventListener('click', () => {
        const correctionText = form.querySelector('.correction-text').value.trim();
        const category = form.querySelector('.correction-category').value;
        if (correctionText || category) {
            sendFeedback('correction', assistantText, {
                correction: correctionText,
                error_category: category,
                source: 'thumbs_down_enriched'
            });
            showToast('Correção registrada!', 2000);
        }
        form.remove();
    });

    form.querySelector('.correction-cancel').addEventListener('click', () => {
        form.remove();
    });
}

/**
 * Injeta botões de feedback (👍👎) em uma mensagem do assistente já renderizada.
 * Usado para mensagens streamed que foram criadas com texto vazio e preenchidas
 * incrementalmente — nesse caso createMessageElement não adiciona os botões.
 * @param {HTMLElement} msgElement - Elemento .message da mensagem
 * @param {string} text - Texto completo da mensagem
 */
function injectFeedbackButtons(msgElement, text) {
    // Evitar duplicação se já tem botões
    if (msgElement.querySelector('.message-feedback')) return;

    const contentDiv = msgElement.querySelector('.message-content');
    if (!contentDiv) return;

    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'message-feedback';
    feedbackDiv.style.cssText = 'display:flex;gap:4px;margin-top:4px;';

    feedbackDiv.innerHTML = `
        <button class="feedback-btn" data-rating="positive" title="Boa resposta"
                style="background:none;border:none;cursor:pointer;padding:2px 6px;border-radius:4px;opacity:0.4;font-size:14px;transition:opacity 0.2s,background 0.2s;"
                onmouseover="this.style.opacity='1';this.style.background='rgba(255,255,255,0.1)'"
                onmouseout="if(!this.classList.contains('active'))this.style.opacity='0.4';this.style.background='none'">
            👍
        </button>
        <button class="feedback-btn" data-rating="negative" title="Resposta pode melhorar"
                style="background:none;border:none;cursor:pointer;padding:2px 6px;border-radius:4px;opacity:0.4;font-size:14px;transition:opacity 0.2s,background 0.2s;"
                onmouseover="this.style.opacity='1';this.style.background='rgba(255,255,255,0.1)'"
                onmouseout="if(!this.classList.contains('active'))this.style.opacity='0.4';this.style.background='none'">
            👎
        </button>
    `;

    contentDiv.appendChild(feedbackDiv);

    // Attach handlers
    feedbackDiv.querySelectorAll('.feedback-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const rating = this.dataset.rating;
            sendFeedback(rating, text);

            const parent = this.closest('.message-feedback');
            parent.querySelectorAll('.feedback-btn').forEach(b => {
                b.disabled = true;
                if (b === this) {
                    b.classList.add('active');
                    b.style.opacity = '1';
                } else {
                    b.style.display = 'none';
                }
            });
            showToast(rating === 'positive' ? '👍 Obrigado!' : '👎 Anotado, vou melhorar!', 2000);
        });
    });
}

// ============================================
// P1-1: SUGESTÕES DE PROMPT — Chips Clicáveis
// ============================================

/**
 * Renderiza chips de sugestão de follow-up abaixo da mensagem do assistente.
 * Cada chip é clicável: preenche o input e auto-envia a mensagem.
 *
 * @param {string[]} suggestions - Array de 2-3 strings com sugestões
 * @param {HTMLElement} msgElement - Elemento .message onde inserir os chips
 */
function renderSuggestionChips(suggestions, msgElement) {
    // Guard: evita duplicação
    if (msgElement.querySelector('.suggestion-chips')) return;

    const contentDiv = msgElement.querySelector('.message-content');
    if (!contentDiv) return;

    const container = document.createElement('div');
    container.className = 'suggestion-chips';

    suggestions.forEach((text, idx) => {
        const chip = document.createElement('button');
        chip.className = 'suggestion-chip';
        chip.textContent = text;
        chip.title = text;

        chip.addEventListener('click', () => {
            // Track suggestion click (best-effort, nao bloqueia)
            try {
                _fetchWithCsrfRetry('/agente/api/feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        type: 'suggestion_click',
                        data: {
                            suggestion_text: text,
                            suggestion_index: idx,
                        }
                    })
                }).catch(() => {}); // best-effort
            } catch (e) { /* ignore */ }

            // Remove todos os chips
            document.querySelectorAll('.suggestion-chips').forEach(el => el.remove());

            // Preenche o input e envia
            messageInput.value = text;
            sendMessage(null);
        });

        container.appendChild(chip);
    });

    contentDiv.appendChild(container);

    // Scroll para mostrar os chips
    scrollToBottom();
}

// ============================================
// P2-3: Aviso de ação destrutiva (reversibilidade)
// ============================================

/**
 * Renderiza aviso de ação destrutiva no chat.
 * Mostra banner informativo sobre a ação que está sendo executada.
 * NÃO bloqueia — apenas notifica. O SDK já usa AskUserQuestion para confirmar.
 *
 * @param {object} data - Dados do evento SSE
 * @param {HTMLElement} msgElement - Elemento de mensagem atual (pode ser null)
 */
function renderDestructiveWarning(data, msgElement) {
    const reversibilityLabels = {
        'irreversible': { text: 'Irreversivel', icon: 'fa-exclamation-triangle', cls: 'destructive-irreversible' },
        'hard_to_reverse': { text: 'Dificil reverter', icon: 'fa-exclamation-circle', cls: 'destructive-hard' },
        'reversible': { text: 'Reversivel', icon: 'fa-info-circle', cls: 'destructive-reversible' },
    };

    const level = reversibilityLabels[data.reversibility] || reversibilityLabels['hard_to_reverse'];

    const banner = document.createElement('div');
    banner.className = `destructive-warning ${level.cls}`;
    banner.innerHTML = `
        <div class="destructive-warning-icon">
            <i class="fas ${level.icon}"></i>
        </div>
        <div class="destructive-warning-content">
            <div class="destructive-warning-title">
                <strong>${escapeHtml(data.description || data.action)}</strong>
                <span class="destructive-warning-badge">${level.text}</span>
            </div>
            <div class="destructive-warning-detail">
                Tool: ${escapeHtml(data.tool_name || '')} &mdash; ${escapeHtml(data.action || '')}
            </div>
        </div>
    `;

    // Insere no chat
    const target = msgElement?.querySelector('.message-content') || document.getElementById('chatMessages');
    if (target) {
        target.appendChild(banner);
        scrollToBottom();
    }

    // Auto-remove após 15 segundos
    setTimeout(() => {
        banner.style.opacity = '0';
        banner.style.transition = 'opacity 0.3s';
        setTimeout(() => banner.remove(), 300);
    }, 15000);
}

// ============================================
// FEAT-ASK: ASKUSERQUESTION — Perguntas Interativas
// ============================================

/**
 * Renderiza perguntas interativas do agente (AskUserQuestion).
 * Exibe cards com opções clicáveis. Suporta single e multi-select.
 * Ao selecionar, envia resposta via POST /api/user-answer.
 *
 * @param {Array} questions - Array de objetos de pergunta do SDK
 * @param {string} askSessionId - Session ID para enviar resposta
 * @param {object} state - Estado do stream (para inserir no chat)
 */
function renderAskUserQuestion(questions, askSessionId, state) {
    // Container para todas as perguntas
    const container = document.createElement('div');
    container.className = 'ask-user-container';

    // Estado das respostas
    const answers = {};
    const selections = {};  // Para multi-select: { questionText: Set<label> }

    questions.forEach((q) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'ask-user-question';

        // Header (chip/tag) — só renderiza se tiver valor
        if (q.header) {
            const headerSpan = document.createElement('span');
            headerSpan.className = 'ask-user-header';
            headerSpan.textContent = q.header;
            questionDiv.appendChild(headerSpan);
        }

        // Texto da pergunta
        const questionText = document.createElement('p');
        questionText.className = 'ask-user-text';
        questionText.textContent = q.question;

        // Opções
        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'ask-user-options';

        if (q.multiSelect) {
            selections[q.question] = new Set();
        }

        (q.options || []).forEach((opt) => {
            const optBtn = document.createElement('button');
            optBtn.className = 'ask-user-option';
            optBtn.innerHTML = `
                <span class="option-label">${escapeHtml(opt.label)}</span>
                <span class="option-desc">${escapeHtml(opt.description || '')}</span>
            `;

            optBtn.addEventListener('click', () => {
                if (q.multiSelect) {
                    // Toggle seleção
                    optBtn.classList.toggle('selected');
                    if (selections[q.question].has(opt.label)) {
                        selections[q.question].delete(opt.label);
                    } else {
                        selections[q.question].add(opt.label);
                    }
                    // Atualiza resposta (labels separados por vírgula)
                    answers[q.question] = Array.from(selections[q.question]).join(', ');
                } else {
                    // Single select: desseleciona outros
                    optionsDiv.querySelectorAll('.ask-user-option').forEach(b => b.classList.remove('selected'));
                    optBtn.classList.add('selected');
                    answers[q.question] = opt.label;

                    // Se é single-select E é a única pergunta, envia imediatamente
                    if (questions.length === 1) {
                        submitAskUserAnswers(container, askSessionId, answers);
                    }
                }
            });

            optionsDiv.appendChild(optBtn);
        });

        // Botão "Outro" (free text) — SDK sempre oferece opção "Other"
        const otherBtn = document.createElement('button');
        otherBtn.className = 'ask-user-option ask-user-other';
        otherBtn.innerHTML = `
            <span class="option-label">Outro</span>
            <span class="option-desc">Digitar resposta personalizada</span>
        `;
        otherBtn.addEventListener('click', () => {
            // FIX: Desselecionar opções anteriores e limpar answer
            if (!q.multiSelect) {
                optionsDiv.querySelectorAll('.ask-user-option').forEach(b => b.classList.remove('selected'));
                otherBtn.classList.add('selected');
                delete answers[q.question]; // Limpa seleção anterior
            }

            // Se já tem input visível, só foca nele
            const existingWrapper = optionsDiv.querySelector('.ask-user-text-input-wrapper');
            if (existingWrapper) {
                const existingInput = existingWrapper.querySelector('.ask-user-text-input');
                if (existingInput) existingInput.focus();
                return;
            }

            // Wrapper com input + botão confirmar (não depender só do Enter)
            const inputWrapper = document.createElement('div');
            inputWrapper.className = 'ask-user-text-input-wrapper';

            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'ask-user-text-input';
            input.placeholder = 'Digite sua resposta...';

            const confirmBtn = document.createElement('button');
            confirmBtn.className = 'ask-user-text-confirm';
            confirmBtn.textContent = '✓';
            confirmBtn.type = 'button';

            // Lógica de confirmação (Enter ou clique no ✓)
            const confirmInput = () => {
                const val = input.value.trim();
                if (!val) return;

                answers[q.question] = val;
                optionsDiv.querySelectorAll('.ask-user-option').forEach(b => b.classList.remove('selected'));
                otherBtn.classList.add('selected');
                otherBtn.querySelector('.option-desc').textContent = val;
                inputWrapper.remove();

                // Auto-envio se single-select com 1 pergunta
                if (questions.length === 1 && !q.multiSelect) {
                    submitAskUserAnswers(container, askSessionId, answers);
                } else {
                    showToast('✓ Resposta capturada', 2000);
                }
            };

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') confirmInput();
            });
            confirmBtn.addEventListener('click', confirmInput);

            inputWrapper.appendChild(input);
            inputWrapper.appendChild(confirmBtn);
            otherBtn.after(inputWrapper);
            input.focus();
        });
        optionsDiv.appendChild(otherBtn);

        questionDiv.appendChild(questionText);
        questionDiv.appendChild(optionsDiv);
        container.appendChild(questionDiv);
    });

    // Botão Enviar (para multi-select ou múltiplas perguntas)
    if (questions.length > 1 || questions.some(q => q.multiSelect)) {
        const submitBtn = document.createElement('button');
        submitBtn.className = 'ask-user-submit';
        submitBtn.textContent = 'Enviar Respostas';
        submitBtn.addEventListener('click', () => {
            // Validar que todas as perguntas foram respondidas
            const unanswered = questions.filter(q => !answers[q.question]);
            if (unanswered.length > 0) {
                showToast(`Responda: ${unanswered[0].header || unanswered[0].question}`, 2000);
                return;
            }
            submitAskUserAnswers(container, askSessionId, answers);
        });
        container.appendChild(submitBtn);
    }

    // Inserir no chat como "mensagem" do assistente
    // NOTA: Usa createMessageElement diretamente (não addMessage) pois
    // addMessage() não retorna o elemento DOM criado.
    const msgElement = createMessageElement('', 'assistant');
    chatMessages.appendChild(msgElement);
    const contentDiv = msgElement.querySelector('.message-content');
    if (contentDiv) {
        contentDiv.innerHTML = '';
        contentDiv.appendChild(container);
    }

    scrollToBottom();
}


/**
 * Envia respostas do AskUserQuestion ao backend.
 * Substitui a UI de seleção por texto confirmando as respostas.
 *
 * @param {HTMLElement} container - Container .ask-user-container
 * @param {string} askSessionId - Session ID
 * @param {object} answers - Dict question → label selecionado
 */
function submitAskUserAnswers(container, askSessionId, answers) {
    // Desabilita botões para evitar duplo-clique
    container.querySelectorAll('button').forEach(b => b.disabled = true);
    container.classList.add('ask-user-submitted');

    // Mostra resumo das respostas selecionadas
    const summary = document.createElement('div');
    summary.className = 'ask-user-summary';
    summary.innerHTML = '<p><strong>✅ Respostas enviadas:</strong></p>';
    Object.entries(answers).forEach(([, answer]) => {
        summary.innerHTML += `<p class="ask-user-answer-line">• ${escapeHtml(answer)}</p>`;
    });

    // Esconde opções e mostra resumo
    container.querySelectorAll('.ask-user-options, .ask-user-submit, .ask-user-text-input').forEach(el => {
        el.style.display = 'none';
    });
    container.appendChild(summary);

    // Enviar ao backend via POST
    const csrfToken = document.querySelector('meta[name="csrf-token"]');

    _fetchWithCsrfRetry('/agente/api/user-answer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(csrfToken ? { 'X-CSRFToken': csrfToken.content } : {}),
        },
        body: JSON.stringify({
            session_id: askSessionId,
            answers: answers,
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Resposta enviada ao agente', 2000);
            showTyping('🤔 Processando sua resposta...');
        } else {
            showToast(`Erro: ${data.error}`, 3000);
            console.error('[ASK_USER] Erro na resposta:', data.error);
        }
    })
    .catch(err => {
        console.error('[ASK_USER] Erro ao enviar resposta:', err);
        showToast('Erro ao enviar resposta', 3000);
    });

    scrollToBottom();
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
        const response = await fetch('/agente/api/sessions?limit=50', {
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
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
                    <button class="export" data-sid="${escapeHtml(session.session_id)}" data-title="${escapeHtml(session.title || 'Conversa')}"
                            onclick="event.stopPropagation(); exportHistoricalSession(this.dataset.sid, this.dataset.title)" title="Exportar">
                        <i class="fas fa-file-export"></i>
                    </button>
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
    if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return 'image';
    if (ext === 'pdf') return 'pdf';
    if (['xlsx', 'xls'].includes(ext)) return 'excel';
    if (ext === 'csv') return 'csv';
    if (['docx', 'doc', 'rtf'].includes(ext)) return 'word';
    if (['txt', 'md', 'json', 'xml', 'log'].includes(ext)) return 'text';
    if (['rem', 'ret', 'cnab'].includes(ext)) return 'bank_cnab';
    if (ext === 'ofx') return 'bank_ofx';
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
        'word': 'fa-file-word',
        'text': 'fa-file-alt',
        'bank_cnab': 'fa-university',
        'bank_ofx': 'fa-money-check-alt',
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

// Helper CSRF — definido antes de qualquer fetch que o use
const _csrfHeader = () => ({
    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
});

// CSRF Auto-Refresh — renova token antes da expiração (WTF_CSRF_TIME_LIMIT = 2h)
async function _refreshCsrfToken() {
    try {
        const resp = await fetch('/agente/api/csrf-token', { credentials: 'same-origin' });
        if (resp.ok) {
            const data = await resp.json();
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta && data.csrf_token) {
                meta.content = data.csrf_token;
                console.log('[CSRF] Token renovado com sucesso');
            }
        }
    } catch (e) {
        console.warn('[CSRF] Falha ao renovar token:', e);
    }
}

// Renova a cada 90 minutos (antes do limite de 2h)
setInterval(_refreshCsrfToken, 90 * 60 * 1000);

/**
 * Wrapper fetch com retry automático em erro CSRF.
 * Detecta csrf_error na resposta, renova o token e retenta 1x.
 */
async function _fetchWithCsrfRetry(url, options = {}) {
    let resp = await fetch(url, options);

    if (resp.status === 400) {
        try {
            const cloned = resp.clone();
            const body = await cloned.json();
            if (body.csrf_error) {
                console.log('[CSRF] Erro detectado, renovando token e retentando...');
                await _refreshCsrfToken();
                // Atualiza o header CSRF nas options
                const headers = new Headers(options.headers || {});
                headers.set('X-CSRFToken', document.querySelector('meta[name="csrf-token"]')?.content || '');
                resp = await fetch(url, { ...options, headers });
            }
        } catch {
            // Se não conseguiu parsear como JSON, retorna a resposta original
        }
    }

    return resp;
}

// Sessao A: Carrega briefing inter-sessao ao iniciar nova sessao
loadAndShowBriefing();


// =============================================================
// SESSAO A: PAINEL DE MEMORIAS
// =============================================================

/**
 * Abre o painel lateral de memorias.
 */
function openMemoriesPanel() {
    const panel = document.getElementById('memories-panel');
    const backdrop = document.getElementById('memories-panel-backdrop');
    if (!panel) return;

    panel.style.display = 'flex';
    backdrop.style.display = 'block';

    // Carregar lista de usuarios (admin) e memorias
    const userSelector = document.getElementById('memories-user-selector');
    if (userSelector && userSelector.options.length <= 1) {
        loadMemoryUsers();
    }

    loadMemories();
}

/**
 * Fecha o painel lateral de memorias.
 */
function closeMemoriesPanel() {
    const panel = document.getElementById('memories-panel');
    const backdrop = document.getElementById('memories-panel-backdrop');
    if (panel) panel.style.display = 'none';
    if (backdrop) backdrop.style.display = 'none';
}

/**
 * Alterna entre abas Memorias e Resumos.
 */
function switchMemoryTab(tab) {
    // Atualizar botoes
    document.querySelectorAll('.memories-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    // Atualizar conteudo
    document.getElementById('memories-tab-content')?.classList.toggle('active', tab === 'memories');
    document.getElementById('summaries-tab-content')?.classList.toggle('active', tab === 'summaries');
    document.getElementById('improvements-tab-content')?.classList.toggle('active', tab === 'improvements');

    // Carregar resumos na primeira vez
    if (tab === 'summaries') {
        const list = document.getElementById('summaries-list');
        if (list && !list.hasChildNodes()) {
            loadSessionSummaries();
        }
    }

    // Sessao E: Carregar melhorias na primeira vez
    if (tab === 'improvements') {
        const list = document.getElementById('improvements-list');
        if (list && !list.hasChildNodes()) {
            loadImprovements('proposed');
        }
    }
}

/**
 * Admin: carrega lista de usuarios com memorias.
 */
function loadMemoryUsers() {
    fetch('/agente/api/memories/users', { headers: _csrfHeader() })
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            const selector = document.getElementById('memories-user-selector');
            if (!selector) return;

            // Limpar opcoes alem da primeira
            while (selector.options.length > 1) selector.remove(1);

            data.users.forEach(u => {
                // Nao duplicar o usuario atual (ja e a primeira opcao)
                const currentUserId = selector.options[0]?.value;
                if (String(u.id) === String(currentUserId)) return;

                const opt = document.createElement('option');
                opt.value = u.id;
                opt.textContent = `${u.nome} (${u.memory_count})`;
                selector.appendChild(opt);
            });
        })
        .catch(e => console.debug('[MEMORIES] Erro ao carregar usuarios:', e));
}

/**
 * Carrega memorias do usuario (ou do usuario selecionado pelo admin).
 */
function loadMemories(userId) {
    const loading = document.getElementById('memories-loading');
    const profileSection = document.getElementById('memories-profile-section');
    const patternsSection = document.getElementById('memories-patterns-section');
    const othersSection = document.getElementById('memories-others-section');
    const emptyState = document.getElementById('memories-empty');

    if (loading) loading.style.display = 'block';
    [profileSection, patternsSection, othersSection, emptyState].forEach(el => {
        if (el) el.style.display = 'none';
    });

    let url = '/agente/api/memories';
    if (userId) url += `?user_id=${userId}`;

    fetch(url, { headers: _csrfHeader() })
        .then(r => r.json())
        .then(data => {
            if (loading) loading.style.display = 'none';

            if (!data.success) {
                if (emptyState) emptyState.style.display = 'flex';
                return;
            }

            let hasContent = false;

            // Perfil (user.xml)
            if (data.profile) {
                hasContent = true;
                if (profileSection) profileSection.style.display = 'block';
                document.getElementById('memories-profile-content').innerHTML =
                    renderMemoryCard(data.profile);
            }

            // Padroes (patterns.xml)
            if (data.patterns && data.patterns.length > 0) {
                hasContent = true;
                if (patternsSection) patternsSection.style.display = 'block';
                document.getElementById('memories-patterns-list').innerHTML =
                    data.patterns.map(p => renderMemoryCard(p)).join('');
            }

            // Outras memorias
            if (data.others && data.others.length > 0) {
                hasContent = true;
                if (othersSection) othersSection.style.display = 'block';
                document.getElementById('memories-others-list').innerHTML =
                    data.others.map(m => renderMemoryCard(m)).join('');
            }

            if (!hasContent && emptyState) {
                emptyState.style.display = 'flex';
            }
        })
        .catch(e => {
            if (loading) loading.style.display = 'none';
            if (emptyState) emptyState.style.display = 'flex';
            console.error('[MEMORIES] Erro ao carregar:', e);
        });
}

/**
 * Renderiza um card de memoria.
 */
/** Cache de conteudo completo das memorias (evita truncar no edit) */
const _memoryContentCache = {};

function renderMemoryCard(memory) {
    const pathShort = memory.path ? memory.path.split('/').pop() : 'memoria';
    const fullContent = memory.content || '';
    const displayContent = escapeHtml(fullContent.length > 2000 ? fullContent.substring(0, 2000) + '...' : fullContent);

    // Cache conteudo completo para uso no edit
    _memoryContentCache[memory.id] = fullContent;

    const conflictBadge = memory.has_potential_conflict
        ? '<span class="memory-meta-badge conflict">Conflito</span>'
        : '';
    const categoryBadge = memory.category
        ? `<span class="memory-meta-badge">${escapeHtml(memory.category)}</span>`
        : '';
    const usageBadge = memory.usage_count > 0
        ? `<span class="memory-meta-badge">Usada ${memory.usage_count}x</span>`
        : '';

    // Sessao E: Badge de review para memorias empresa
    let reviewBadge = '';
    if (memory.escopo === 'empresa') {
        if (memory.reviewed_at) {
            reviewBadge = `<span class="memory-meta-badge reviewed" id="review-badge-${memory.id}">Revisada</span>`;
        } else {
            reviewBadge = `<span class="memory-meta-badge needs-review" id="review-badge-${memory.id}" onclick="event.stopPropagation(); reviewMemory(${memory.id})" title="Clique para marcar como revisada">Revisar</span>`;
        }
    }

    return `
        <div class="memory-card" id="memory-card-${memory.id}">
            <div class="memory-card-header">
                <span class="memory-card-path" title="${escapeHtml(memory.path || '')}">${escapeHtml(pathShort)}</span>
                <div class="memory-card-actions">
                    <button onclick="startEditMemory(${memory.id})" title="Editar">
                        <i class="fas fa-pencil-alt"></i>
                    </button>
                    <button class="btn-delete" data-id="${memory.id}" data-name="${escapeHtml(pathShort)}" onclick="deleteMemory(this.dataset.id, this.dataset.name)" title="Deletar">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </div>
            <div class="memory-card-body" id="memory-body-${memory.id}">${displayContent}</div>
            <div class="memory-card-meta">
                ${categoryBadge}${usageBadge}${conflictBadge}${reviewBadge}
            </div>
        </div>
    `;
}

/**
 * Inicia edicao inline de uma memoria.
 */
function startEditMemory(memoryId) {
    const bodyEl = document.getElementById(`memory-body-${memoryId}`);
    if (!bodyEl) return;

    // Usa cache com conteudo completo (nao o DOM truncado)
    const currentContent = _memoryContentCache[memoryId] || bodyEl.textContent || '';
    bodyEl.innerHTML = `
        <textarea class="memory-edit-textarea" id="memory-edit-${memoryId}">${escapeHtml(currentContent)}</textarea>
        <div class="memory-edit-actions">
            <button class="btn-cancel-edit" onclick="cancelEditMemory(${memoryId})">Cancelar</button>
            <button class="btn-save" onclick="saveEditMemory(${memoryId})">Salvar</button>
        </div>
    `;

    const textarea = document.getElementById(`memory-edit-${memoryId}`);
    if (textarea) textarea.focus();
}

/**
 * Cancela edicao de memoria.
 */
function cancelEditMemory(memoryId) {
    // Recarregar memorias para restaurar estado
    const selector = document.getElementById('memories-user-selector');
    loadMemories(selector?.value);
}

/**
 * Salva edicao de memoria via PUT.
 */
function saveEditMemory(memoryId) {
    const textarea = document.getElementById(`memory-edit-${memoryId}`);
    if (!textarea) return;

    const newContent = textarea.value;

    fetch(`/agente/api/memories/${memoryId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            ..._csrfHeader(),
        },
        body: JSON.stringify({ content: newContent }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Memoria atualizada', 2000);
            const selector = document.getElementById('memories-user-selector');
            loadMemories(selector?.value);
        } else {
            showToast('Erro: ' + (data.error || 'Falha ao salvar'), 3000);
        }
    })
    .catch(e => {
        showToast('Erro ao salvar memoria', 3000);
        console.error('[MEMORIES] Erro save:', e);
    });
}

/**
 * Deleta memoria com confirmacao.
 */
function deleteMemory(memoryId, name) {
    if (!confirm(`Deletar memoria "${name}"?`)) return;

    fetch(`/agente/api/memories/${memoryId}`, {
        method: 'DELETE',
        headers: _csrfHeader(),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Memoria deletada', 2000);
            // Remover card com animacao
            const card = document.getElementById(`memory-card-${memoryId}`);
            if (card) {
                card.style.opacity = '0';
                card.style.transform = 'translateX(20px)';
                card.style.transition = 'all 0.3s';
                setTimeout(() => card.remove(), 300);
            }
        } else {
            showToast('Erro: ' + (data.error || 'Falha ao deletar'), 3000);
        }
    })
    .catch(e => {
        showToast('Erro ao deletar memoria', 3000);
        console.error('[MEMORIES] Erro delete:', e);
    });
}


// =============================================================
// SESSAO A: RESUMOS DE SESSAO
// =============================================================

/**
 * Carrega resumos estruturados de sessoes anteriores.
 */
function loadSessionSummaries() {
    const loading = document.getElementById('summaries-loading');
    const list = document.getElementById('summaries-list');
    const emptyState = document.getElementById('summaries-empty');

    if (loading) loading.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (list) list.innerHTML = '';

    fetch('/agente/api/sessions/summaries?limit=20', { headers: _csrfHeader() })
        .then(r => r.json())
        .then(data => {
            if (loading) loading.style.display = 'none';

            if (!data.success || !data.sessions || data.sessions.length === 0) {
                if (emptyState) emptyState.style.display = 'flex';
                return;
            }

            list.innerHTML = data.sessions.map(s => renderSummaryCard(s)).join('');
        })
        .catch(e => {
            if (loading) loading.style.display = 'none';
            if (emptyState) emptyState.style.display = 'flex';
            console.error('[SUMMARIES] Erro ao carregar:', e);
        });
}

/**
 * Renderiza um card de resumo de sessao (accordion).
 */
function renderSummaryCard(session) {
    const summary = session.summary || {};
    const title = escapeHtml(session.title || 'Sem titulo');
    const date = session.created_at
        ? new Date(session.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
        : '';

    let bodyHtml = '';

    // Resumo geral
    if (summary.resumo_geral) {
        bodyHtml += `<div class="summary-section">
            <div class="summary-section-label">Resumo</div>
            <p style="margin:0">${escapeHtml(summary.resumo_geral)}</p>
        </div>`;
    }

    // Pedidos tratados
    if (summary.pedidos_tratados && summary.pedidos_tratados.length > 0) {
        bodyHtml += `<div class="summary-section">
            <div class="summary-section-label">Pedidos Tratados</div>
            <ul>${summary.pedidos_tratados.map(p => `<li>${escapeHtml(String(p))}</li>`).join('')}</ul>
        </div>`;
    }

    // Decisoes
    if (summary.decisoes_tomadas && summary.decisoes_tomadas.length > 0) {
        bodyHtml += `<div class="summary-section">
            <div class="summary-section-label">Decisoes</div>
            <ul>${summary.decisoes_tomadas.map(d => `<li>${escapeHtml(String(d))}</li>`).join('')}</ul>
        </div>`;
    }

    // Tarefas pendentes
    if (summary.tarefas_pendentes && summary.tarefas_pendentes.length > 0) {
        bodyHtml += `<div class="summary-section">
            <div class="summary-section-label">Tarefas Pendentes</div>
            <ul>${summary.tarefas_pendentes.map(t => `<li>${escapeHtml(String(t))}</li>`).join('')}</ul>
        </div>`;
    }

    // Alertas
    if (summary.alertas && summary.alertas.length > 0) {
        bodyHtml += `<div class="summary-section">
            <div class="summary-section-label">Alertas</div>
            <ul>${summary.alertas.map(a => `<li>${escapeHtml(String(a))}</li>`).join('')}</ul>
        </div>`;
    }

    if (!bodyHtml) {
        bodyHtml = '<p style="color:var(--agent-text-secondary);font-style:italic">Resumo nao detalhado</p>';
    }

    return `
        <div class="summary-card" onclick="this.classList.toggle('expanded')">
            <div class="summary-card-header">
                <span class="summary-card-title">${title}</span>
                <span class="summary-card-date">${date}</span>
                <i class="fas fa-chevron-right summary-card-chevron"></i>
            </div>
            <div class="summary-card-body">${bodyHtml}</div>
        </div>
    `;
}


// =============================================================
// SESSAO A: BRIEFING INTER-SESSAO
// =============================================================

/**
 * Carrega e mostra briefing inter-sessao como card na area de mensagens.
 * Executado uma vez por sessao nova (gate via sessionStorage).
 */
function loadAndShowBriefing() {
    const today = new Date().toDateString();
    const key = `briefing-shown-${today}-${sessionId || 'new'}`;
    if (sessionStorage.getItem(key)) return;

    fetch('/agente/api/briefing', { headers: _csrfHeader() })
        .then(r => r.json())
        .then(data => {
            if (data.success && data.has_content && data.items && data.items.length > 0) {
                renderBriefingCard(data);
                sessionStorage.setItem(key, '1');
            }
        })
        .catch(e => console.debug('[BRIEFING] Nao disponivel:', e));
}

/**
 * Renderiza card de briefing na area de mensagens.
 */
function renderBriefingCard(data) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;

    const iconMap = {
        'last_intent': { icon: 'fa-clipboard-list', cls: 'intent' },
        'odoo_errors': { icon: 'fa-exclamation-triangle', cls: 'error' },
        'import_failures': { icon: 'fa-file-import', cls: 'warning' },
        'memory_alerts': { icon: 'fa-brain', cls: 'warning' },
        'stale_memories': { icon: 'fa-clock', cls: 'info' },
        'intelligence': { icon: 'fa-lightbulb', cls: 'info' },
    };

    const labelMap = {
        'last_intent': item => item.intent_type === 'tarefa_pendente'
            ? `Tarefa pendente: ${item.content}${item.remaining > 0 ? ` (+${item.remaining} outras)` : ''}`
            : `Ultima sessao: ${item.content}`,
        'odoo_errors': item => `${item.total} erro(s) Odoo — ${item.details}`,
        'import_failures': item => `${item.count} falha(s) de importacao de pedidos`,
        'memory_alerts': item => `Alertas de memoria: ${item.details}`,
        'stale_memories': item => `${item.count} memoria(s) empresa sem revisao ha 60+ dias`,
        'intelligence': item => item.content,
    };

    const itemsHtml = data.items.map(item => {
        const info = iconMap[item.type] || { icon: 'fa-info-circle', cls: 'info' };
        const label = labelMap[item.type] ? labelMap[item.type](item) : JSON.stringify(item);
        return `
            <div class="briefing-item">
                <span class="briefing-item-icon ${info.cls}"><i class="fas ${info.icon}"></i></span>
                <span>${escapeHtml(label)}</span>
            </div>
        `;
    }).join('');

    const sinceText = data.since ? `Desde ${escapeHtml(data.since)}` : '';

    const card = document.createElement('div');
    card.className = 'briefing-card';
    card.id = 'briefing-card';
    card.innerHTML = `
        <button class="briefing-card-dismiss" onclick="dismissBriefingCard()" title="Fechar">
            <i class="fas fa-times"></i>
        </button>
        <div class="briefing-card-header">
            <span class="briefing-card-title"><i class="fas fa-bell me-1"></i>O que aconteceu</span>
            <span class="briefing-card-since">${sinceText}</span>
        </div>
        <div class="briefing-items">${itemsHtml}</div>
    `;

    // Inserir apos a mensagem de boas-vindas (primeiro filho)
    const welcomeMsg = chatMessages.querySelector('.message.assistant');
    if (welcomeMsg && welcomeMsg.nextSibling) {
        chatMessages.insertBefore(card, welcomeMsg.nextSibling);
    } else {
        chatMessages.appendChild(card);
    }
}

/**
 * Fecha o card de briefing com animacao.
 */
function dismissBriefingCard() {
    const card = document.getElementById('briefing-card');
    if (!card) return;
    card.style.opacity = '0';
    card.style.transform = 'translateY(-8px)';
    card.style.transition = 'all 0.3s';
    setTimeout(() => card.remove(), 300);
}


// =============================================================
// SESSAO A: INDICADOR DE CONTEXTO
// =============================================================

/** Flag para evitar toast repetido de warning de contexto */
let _contextWarningShown = false;

/**
 * Atualiza o indicador de uso de contexto no header.
 * Chamado pelo SSE event 'done' quando context_usage esta presente.
 */
function updateContextUsage(contextData) {
    if (!contextData) return;

    const percent = contextData.percent || 0;
    const container = document.getElementById('context-indicator');
    const bar = document.getElementById('context-bar-fill');
    const text = document.getElementById('context-text');

    if (!container) return;

    // Mostrar indicador
    container.style.display = 'flex';

    // Atualizar barra e texto
    if (bar) bar.style.width = Math.min(percent, 100) + '%';
    if (text) text.textContent = Math.round(percent) + '%';

    // Classes de warning
    container.classList.remove('context-warning', 'context-critical');
    if (percent >= 90) {
        container.classList.add('context-critical');
    } else if (percent >= 80) {
        container.classList.add('context-warning');
    }

    // Alerta unico quando >= 80%
    if (percent >= 80 && !_contextWarningShown) {
        _contextWarningShown = true;
        showToast(
            `Contexto ${Math.round(percent)}% usado — considere iniciar nova sessao para melhor performance`,
            8000
        );
    }
}


// =============================================================
// SESSAO B: BUSCA EM SESSOES
// =============================================================

/** Timer do debounce de busca */
let _searchDebounceTimer = null;

/**
 * Busca debounced: espera 300ms apos ultima digitacao.
 */
function debouncedSearchSessions(query) {
    const clearBtn = document.getElementById('sessions-search-clear');
    if (clearBtn) clearBtn.style.display = query ? 'flex' : 'none';

    if (_searchDebounceTimer) clearTimeout(_searchDebounceTimer);

    // Min 2 chars para busca server-side (consistente com backend)
    // Query vazia recarrega lista completa
    if (query.trim().length === 1) return;

    _searchDebounceTimer = setTimeout(() => searchSessions(query), 300);
}

/**
 * Executa busca server-side de sessoes.
 */
async function searchSessions(query) {
    const loading = document.getElementById('sessions-loading');
    const empty = document.getElementById('sessions-empty');
    const list = document.getElementById('sessions-list');

    // Remover resultados anteriores e estado "no results"
    list.querySelectorAll('.session-item, .sessions-no-results').forEach(el => el.remove());

    if (loading) loading.style.display = 'block';
    if (empty) empty.style.display = 'none';

    try {
        const q = encodeURIComponent(query.trim());
        const url = q ? `/agente/api/sessions?limit=50&q=${q}` : '/agente/api/sessions?limit=50';

        const response = await fetch(url, { headers: _csrfHeader() });
        const data = await response.json();

        if (loading) loading.style.display = 'none';

        if (data.success && data.sessions.length > 0) {
            sessionsList = data.sessions;
            renderSessions();
            updateSessionsCount(data.sessions.length);
        } else if (query.trim()) {
            // Busca sem resultados
            sessionsList = [];
            const noResults = document.createElement('div');
            noResults.className = 'sessions-no-results';
            noResults.innerHTML = `
                <i class="fas fa-search fa-2x"></i>
                <p>Nenhum resultado para "${escapeHtml(query)}"</p>
            `;
            list.appendChild(noResults);
        } else {
            sessionsList = data.sessions || [];
            if (empty) empty.style.display = 'block';
            updateSessionsCount(0);
        }
    } catch (error) {
        console.error('[SEARCH] Erro na busca:', error);
        if (loading) loading.style.display = 'none';
    }
}

/**
 * Limpa campo de busca e recarrega sessoes.
 */
function clearSessionSearch() {
    const input = document.getElementById('sessions-search-input');
    const clearBtn = document.getElementById('sessions-search-clear');
    if (input) input.value = '';
    if (clearBtn) clearBtn.style.display = 'none';
    loadSessions();
}


// =============================================================
// SESSAO B: EXPORT DE SESSOES HISTORICAS
// =============================================================

/**
 * Exporta uma sessao historica buscando mensagens do banco.
 * Mostra menu de formato (MD/PDF) antes de exportar.
 */
function exportHistoricalSession(sessionIdToExport, title) {
    // Mini-menu de formato via confirm (simples e consistente)
    const format = prompt(
        'Formato de exportacao:\n\n1 - Markdown (.md)\n2 - PDF\n\nDigite 1 ou 2:',
        '1'
    );

    if (!format) return;

    const fmt = format.trim() === '2' ? 'pdf' : 'markdown';

    showToast('Preparando exportacao...', 2000);

    fetch(`/agente/api/sessions/${sessionIdToExport}/messages`, {
        headers: _csrfHeader(),
    })
    .then(r => r.json())
    .then(data => {
        if (!data.success || !data.messages || data.messages.length === 0) {
            showToast('Sessao sem mensagens para exportar', 3000);
            return;
        }

        const conversationData = data.messages.map(msg => ({
            role: msg.role === 'user' ? 'Usuario' : 'Assistente',
            content: msg.content || '',
            time: msg.timestamp
                ? new Date(msg.timestamp).toLocaleString('pt-BR', {
                    day: '2-digit', month: '2-digit',
                    hour: '2-digit', minute: '2-digit'
                })
                : '',
        }));

        const timestamp = new Date().toLocaleString('pt-BR');
        const exportTitle = title || 'Conversa';

        if (fmt === 'markdown') {
            exportHistoricalAsMarkdown(conversationData, timestamp, exportTitle);
        } else {
            exportHistoricalAsPDF(conversationData, timestamp, exportTitle);
        }
    })
    .catch(e => {
        showToast('Erro ao exportar sessao', 3000);
        console.error('[EXPORT] Erro:', e);
    });
}

/**
 * Gera e baixa arquivo Markdown de sessao historica.
 */
function exportHistoricalAsMarkdown(data, timestamp, title) {
    let markdown = `# ${title}\n\n`;
    markdown += `**Exportado em:** ${timestamp}\n\n`;
    markdown += `---\n\n`;

    data.forEach(msg => {
        const icon = msg.role === 'Usuario' ? '\u{1F464}' : '\u{1F916}';
        markdown += `### ${icon} ${msg.role}\n`;
        if (msg.time) markdown += `*${msg.time}*\n\n`;
        markdown += `${msg.content}\n\n`;
        markdown += `---\n\n`;
    });

    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversa-nacom-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('Markdown exportado', 2000);
}

/**
 * Gera e abre janela de impressao PDF de sessao historica.
 */
function exportHistoricalAsPDF(data, timestamp, title) {
    let html = `
        <html>
        <head>
            <meta charset="UTF-8">
            <title>${escapeHtml(title)}</title>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    padding: 40px;
                    max-width: 800px;
                    margin: 0 auto;
                    color: #1f2328;
                    line-height: 1.6;
                }
                h1 {
                    color: #00a88a;
                    border-bottom: 2px solid #00a88a;
                    padding-bottom: 10px;
                }
                .meta {
                    color: #57606a;
                    font-size: 0.9em;
                    margin-bottom: 30px;
                }
                .message {
                    margin: 20px 0;
                    padding: 15px;
                    border-radius: 10px;
                    page-break-inside: avoid;
                }
                .user {
                    background: #e8f4fd;
                    border-left: 4px solid #0284c7;
                }
                .assistant {
                    background: #f0fdf4;
                    border-left: 4px solid #00a88a;
                }
                .role {
                    font-weight: bold;
                    margin-bottom: 5px;
                    font-size: 0.85em;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }
                .time {
                    color: #57606a;
                    font-size: 0.8em;
                }
                .content {
                    white-space: pre-wrap;
                    word-break: break-word;
                }
            </style>
        </head>
        <body>
            <h1>${escapeHtml(title)}</h1>
            <p class="meta">Exportado em ${timestamp} &bull; ${data.length} mensagens</p>
    `;

    data.forEach(msg => {
        const cls = msg.role === 'Usuario' ? 'user' : 'assistant';
        html += `
            <div class="message ${cls}">
                <div class="role">${escapeHtml(msg.role)} <span class="time">${escapeHtml(msg.time || '')}</span></div>
                <div class="content">${escapeHtml(msg.content)}</div>
            </div>
        `;
    });

    html += '</body></html>';

    const printWindow = window.open('', '_blank');
    if (printWindow) {
        printWindow.document.write(html);
        printWindow.document.close();
        printWindow.onload = () => printWindow.print();
        showToast('PDF pronto para impressao', 2000);
    } else {
        showToast('Popup bloqueado — permita popups para exportar PDF', 4000);
    }
}


// =============================================================
// SESSAO E: IMPROVEMENT DIALOGUE + REVIEW MEMORIAS EMPRESA
// =============================================================

/**
 * Carrega sugestoes de melhoria do agente (admin-only).
 */
function loadImprovements(statusFilter) {
    const loading = document.getElementById('improvements-loading');
    const list = document.getElementById('improvements-list');
    const empty = document.getElementById('improvements-empty');
    const filter = document.getElementById('improvements-filter');

    if (loading) loading.style.display = 'block';
    if (empty) empty.style.display = 'none';
    if (list) list.innerHTML = '';
    if (filter) filter.style.display = 'block';

    const url = statusFilter
        ? `/agente/api/improvement-dialogue/admin?status=${statusFilter}&limit=20`
        : '/agente/api/improvement-dialogue/admin?limit=20';

    fetch(url, { headers: _csrfHeader() })
        .then(r => r.json())
        .then(data => {
            if (loading) loading.style.display = 'none';

            if (!data.success || !data.items || data.items.length === 0) {
                if (empty) empty.style.display = 'flex';
                return;
            }

            list.innerHTML = data.items.map(item => renderImprovementCard(item)).join('');
        })
        .catch(e => {
            if (loading) loading.style.display = 'none';
            if (empty) empty.style.display = 'flex';
            console.error('[IMPROVEMENTS] Erro:', e);
        });
}

/**
 * Renderiza card de sugestao de melhoria.
 */
function renderImprovementCard(item) {
    const severityClass = `severity-${item.severity || 'info'}`;
    const statusClass = `status-${item.status || 'proposed'}`;
    const statusLabel = { proposed: 'Pendente', responded: 'Aceita', rejected: 'Rejeitada', verified: 'Verificada' }[item.status] || item.status;
    const categoryLabel = {
        skill_suggestion: 'Skill',
        instruction_request: 'Instrucao',
        prompt_feedback: 'Prompt',
        gotcha_report: 'Gotcha',
        memory_feedback: 'Memoria',
        skill_bug: 'Bug Skill',
    }[item.category] || item.category;

    const actionsHtml = item.status === 'proposed' ? `
        <div class="improvement-card-actions">
            <button class="improvement-btn-accept" onclick="respondImprovement(${item.id}, 'accept')">
                <i class="fas fa-check me-1"></i>Aceitar
            </button>
            <button class="improvement-btn-reject" onclick="respondImprovement(${item.id}, 'reject')">
                <i class="fas fa-times me-1"></i>Rejeitar
            </button>
        </div>
    ` : '';

    const notesHtml = item.implementation_notes
        ? `<div class="improvement-card-category" style="margin-top:4px"><i class="fas fa-reply me-1"></i>${escapeHtml(item.implementation_notes)}</div>`
        : '';

    return `
        <div class="improvement-card" id="improvement-card-${item.id}">
            <div class="improvement-card-header">
                <span class="improvement-card-title">${escapeHtml(item.title)}</span>
                <div class="improvement-card-badges">
                    <span class="improvement-badge ${severityClass}">${escapeHtml(item.severity)}</span>
                    <span class="improvement-badge ${statusClass}">${escapeHtml(statusLabel)}</span>
                </div>
            </div>
            <div class="improvement-card-body">${escapeHtml(item.description)}</div>
            <div class="improvement-card-category"><i class="fas fa-tag me-1"></i>${escapeHtml(categoryLabel)} &bull; ${escapeHtml(item.suggestion_key)}</div>
            ${notesHtml}
            ${actionsHtml}
        </div>
    `;
}

/**
 * Responde a uma sugestao de melhoria (accept/reject).
 */
function respondImprovement(itemId, action) {
    const notes = action === 'reject'
        ? prompt('Motivo da rejeicao (opcional):') || ''
        : '';

    fetch(`/agente/api/improvement-dialogue/${itemId}/respond`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ..._csrfHeader() },
        body: JSON.stringify({ action, notes }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast(action === 'accept' ? 'Sugestao aceita' : 'Sugestao rejeitada', 2000);
            // Recarregar lista
            const filter = document.getElementById('improvements-status-filter');
            loadImprovements(filter?.value || 'proposed');
        } else {
            showToast('Erro: ' + (data.error || 'Falha'), 3000);
        }
    })
    .catch(e => {
        showToast('Erro ao responder', 3000);
        console.error('[IMPROVEMENTS] Erro respond:', e);
    });
}

/**
 * Marca uma memoria empresa como revisada (admin-only).
 */
function reviewMemory(memoryId) {
    fetch(`/agente/api/memories/${memoryId}/review`, {
        method: 'PUT',
        headers: _csrfHeader(),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Memoria marcada como revisada', 2000);
            // Atualizar badge no card
            const badge = document.getElementById(`review-badge-${memoryId}`);
            if (badge) {
                badge.className = 'memory-meta-badge reviewed';
                badge.textContent = 'Revisada';
                badge.onclick = null;
                badge.style.cursor = 'default';
            }
        } else {
            showToast('Erro: ' + (data.error || 'Falha'), 3000);
        }
    })
    .catch(e => {
        showToast('Erro ao revisar', 3000);
        console.error('[REVIEW] Erro:', e);
    });
}


// =============================================================
// SESSAO D: TOUR GUIADO DE PRIMEIRO ACESSO
// =============================================================

const TOUR_STEPS = [
    {
        target: '#message-input',
        title: 'Converse com a IA',
        text: 'Digite sua pergunta aqui. O agente pode consultar pedidos, estoque, fretes e muito mais.',
    },
    {
        target: '#model-selector',
        title: 'Escolha o Modelo',
        text: 'Haiku e rapido e economico. Sonnet e o equilibrado (recomendado). Opus e o mais potente.',
        desktopOnly: true,
    },
    {
        target: '#effort-selector',
        title: 'Nivel de Raciocinio',
        text: 'Controla o quanto a IA "pensa" antes de responder. Auto ajusta ao modelo. Use High para analises complexas.',
        desktopOnly: true,
    },
    {
        target: '.btn-sessions',
        title: 'Historico de Conversas',
        text: 'Acesse conversas anteriores, busque por assunto, e exporte para Markdown ou PDF.',
    },
    {
        target: '.btn-memories',
        title: 'Memorias da IA',
        text: 'Veja o que a IA aprendeu sobre voce e resumos de sessoes anteriores. Voce pode editar ou remover memorias.',
        desktopOnly: true,
    },
];

let _tourCurrentStep = 0;
let _tourOverlay = null;
let _tourHighlight = null;
let _tourTooltip = null;

/**
 * Inicia o tour se for o primeiro acesso do usuario.
 */
function maybeStartTour() {
    if (localStorage.getItem('agent-tour-completed')) return;

    // Delay para o DOM estar pronto e animacoes iniciais terminarem
    setTimeout(() => startTour(), 1500);
}

/**
 * Inicia o tour do zero.
 */
function startTour() {
    _tourCurrentStep = 0;

    // Criar overlay
    _tourOverlay = document.createElement('div');
    _tourOverlay.className = 'tour-overlay';
    _tourOverlay.onclick = (e) => { if (e.target === _tourOverlay) endTour(); };
    document.body.appendChild(_tourOverlay);

    // Criar highlight
    _tourHighlight = document.createElement('div');
    _tourHighlight.className = 'tour-highlight';
    document.body.appendChild(_tourHighlight);

    // Criar tooltip
    _tourTooltip = document.createElement('div');
    _tourTooltip.className = 'tour-tooltip';
    document.body.appendChild(_tourTooltip);

    showTourStep();
}

/**
 * Mostra o step atual do tour.
 */
function showTourStep() {
    const isMobile = window.innerWidth < 768;
    let step = TOUR_STEPS[_tourCurrentStep];

    // Pular steps desktop-only em mobile
    while (step && step.desktopOnly && isMobile) {
        _tourCurrentStep++;
        if (_tourCurrentStep >= TOUR_STEPS.length) {
            endTour();
            return;
        }
        step = TOUR_STEPS[_tourCurrentStep];
    }

    if (!step) {
        endTour();
        return;
    }

    const el = document.querySelector(step.target);
    if (!el) {
        // Elemento nao encontrado — pular step
        _tourCurrentStep++;
        if (_tourCurrentStep >= TOUR_STEPS.length) {
            endTour();
            return;
        }
        showTourStep();
        return;
    }

    // Posicionar highlight
    const rect = el.getBoundingClientRect();
    const pad = 6;
    _tourHighlight.style.top = (rect.top - pad) + 'px';
    _tourHighlight.style.left = (rect.left - pad) + 'px';
    _tourHighlight.style.width = (rect.width + pad * 2) + 'px';
    _tourHighlight.style.height = (rect.height + pad * 2) + 'px';

    // Posicionar tooltip abaixo do elemento (ou acima se nao cabe)
    const total = TOUR_STEPS.filter(s => !s.desktopOnly || !isMobile).length;
    const currentVisible = TOUR_STEPS.slice(0, _tourCurrentStep + 1).filter(s => !s.desktopOnly || !isMobile).length;
    const isLast = _tourCurrentStep >= TOUR_STEPS.length - 1;

    _tourTooltip.innerHTML = `
        <div class="tour-tooltip-title">${step.title}</div>
        <div class="tour-tooltip-text">${step.text}</div>
        <div class="tour-tooltip-footer">
            <span class="tour-tooltip-progress">${currentVisible} de ${total}</span>
            <div class="tour-tooltip-actions">
                <button class="tour-btn-skip" onclick="endTour()">Pular</button>
                <button class="tour-btn-next" onclick="nextTourStep()">${isLast ? 'Concluir' : 'Proximo'}</button>
            </div>
        </div>
    `;

    // Posicionar tooltip
    const tooltipH = 140; // Estimativa
    const below = rect.bottom + 12;
    const above = rect.top - tooltipH - 12;

    if (below + tooltipH < window.innerHeight) {
        _tourTooltip.style.top = below + 'px';
    } else {
        _tourTooltip.style.top = Math.max(8, above) + 'px';
    }
    _tourTooltip.style.left = Math.max(12, Math.min(rect.left, window.innerWidth - 340)) + 'px';

    // Re-trigger animation
    _tourTooltip.style.animation = 'none';
    _tourTooltip.offsetHeight; // reflow
    _tourTooltip.style.animation = '';
}

/**
 * Avanca para o proximo step.
 */
function nextTourStep() {
    _tourCurrentStep++;
    if (_tourCurrentStep >= TOUR_STEPS.length) {
        endTour();
        return;
    }
    showTourStep();
}

/**
 * Finaliza o tour e marca como concluido.
 */
function endTour() {
    localStorage.setItem('agent-tour-completed', '1');

    if (_tourOverlay) { _tourOverlay.remove(); _tourOverlay = null; }
    if (_tourHighlight) { _tourHighlight.remove(); _tourHighlight = null; }
    if (_tourTooltip) { _tourTooltip.remove(); _tourTooltip = null; }
}

// Iniciar tour se primeiro acesso
maybeStartTour();


// =============================================================
// SESSAO F #21: SPRINT-4 MIGRADO DE INLINE (voice, export DOM, favorites)
// =============================================================

// --- VOICE INPUT (Web Speech API) ---
let recognition = null;
let isRecording = false;
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function initVoiceInput() {
    const voiceBtn = document.getElementById('voice-btn');
    if (!SpeechRecognition) {
        if (voiceBtn) { voiceBtn.disabled = true; voiceBtn.title = 'Navegador nao suporta entrada por voz'; }
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'pt-BR';
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => {
        isRecording = true;
        voiceBtn.classList.add('recording');
        voiceBtn.querySelector('i').className = 'fas fa-stop';
        showVoiceFeedback('Ouvindo...', '');
    };

    recognition.onresult = (event) => {
        const textarea = document.getElementById('message-input');
        let finalTranscript = '';
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) { finalTranscript += transcript; }
            else { interimTranscript += transcript; }
        }
        if (interimTranscript) showVoiceFeedback('Ouvindo...', interimTranscript);
        if (finalTranscript) {
            const currentText = textarea.value;
            const separator = currentText && !currentText.endsWith(' ') ? ' ' : '';
            textarea.value = currentText + separator + finalTranscript;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }
    };

    recognition.onerror = (event) => {
        stopVoiceInput();
        if (event.error === 'not-allowed') {
            alert('Permissao de microfone negada. Permita acesso nas configuracoes do navegador.');
        }
    };

    recognition.onend = () => stopVoiceInput();
}

function toggleVoiceInput() {
    if (!recognition) { alert('Entrada por voz nao suportada.'); return; }
    if (isRecording) { recognition.stop(); } else { recognition.start(); }
}

function stopVoiceInput() {
    isRecording = false;
    const voiceBtn = document.getElementById('voice-btn');
    if (voiceBtn) {
        voiceBtn.classList.remove('recording');
        voiceBtn.querySelector('i').className = 'fas fa-microphone';
    }
    hideVoiceFeedback();
}

function showVoiceFeedback(status, transcript) {
    let feedback = document.querySelector('.voice-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'voice-feedback';
        feedback.innerHTML = '<i class="fas fa-microphone"></i><div><div class="voice-text"></div><div class="voice-transcript"></div></div>';
        document.body.appendChild(feedback);
    }
    feedback.querySelector('.voice-text').textContent = status;
    feedback.querySelector('.voice-transcript').textContent = transcript;
    feedback.classList.add('active');
}

function hideVoiceFeedback() {
    const feedback = document.querySelector('.voice-feedback');
    if (feedback) feedback.classList.remove('active');
}

// --- EXPORT CONVERSA DOM (sessao ativa) ---
function exportConversation(format) {
    const messages = document.querySelectorAll('#chat-messages .message');
    if (messages.length <= 1) { showToast('Nenhuma mensagem para exportar', 2000); return; }

    const conversationData = [];
    const timestamp = new Date().toLocaleString('pt-BR');

    messages.forEach((msg, index) => {
        if (index === 0) return;
        const isUser = msg.classList.contains('user');
        const bubble = msg.querySelector('.message-bubble');
        const time = msg.querySelector('.message-time');
        if (bubble) {
            conversationData.push({
                role: isUser ? 'Usuario' : 'Assistente',
                content: bubble.innerText || bubble.textContent,
                time: time ? time.textContent : ''
            });
        }
    });

    if (format === 'markdown') { exportAsMarkdown(conversationData, timestamp); }
    else if (format === 'pdf') { exportAsPDF(conversationData, timestamp); }
}

function exportAsMarkdown(data, timestamp) {
    let markdown = `# Conversa com Nacom Goya IA\n\n**Exportado em:** ${timestamp}\n\n---\n\n`;
    data.forEach(msg => {
        const icon = msg.role === 'Usuario' ? '\u{1F464}' : '\u{1F916}';
        markdown += `### ${icon} ${msg.role}\n`;
        if (msg.time) markdown += `*${msg.time}*\n\n`;
        markdown += `${msg.content}\n\n---\n\n`;
    });
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversa-nacom-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Markdown exportado', 2000);
}

function exportAsPDF(data, timestamp) {
    let html = `<html><head><meta charset="UTF-8"><style>
        body { font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; color: #1f2328; line-height: 1.6; }
        h1 { color: #00a88a; border-bottom: 2px solid #00a88a; padding-bottom: 10px; }
        .meta { color: #57606a; font-size: 0.9em; margin-bottom: 30px; }
        .message { margin: 20px 0; padding: 15px; border-radius: 10px; page-break-inside: avoid; }
        .user { background: #e8f4fd; border-left: 4px solid #0284c7; }
        .assistant { background: #f0fdf4; border-left: 4px solid #00a88a; }
        .role { font-weight: 600; margin-bottom: 8px; } .time { font-size: 0.8em; color: #8b949e; }
        .content { white-space: pre-wrap; }
        pre { background: #1f2328; color: #f0f6fc; padding: 12px; border-radius: 6px; overflow-x: auto; }
    </style></head><body><h1>Conversa com Nacom Goya IA</h1><div class="meta">Exportado em: ${timestamp}</div>`;
    data.forEach(msg => {
        const cls = msg.role === 'Usuario' ? 'user' : 'assistant';
        html += `<div class="message ${cls}"><div class="role">${escapeHtml(msg.role)} <span class="time">${escapeHtml(msg.time || '')}</span></div><div class="content">${escapeHtml(msg.content)}</div></div>`;
    });
    html += '</body></html>';
    const printWindow = window.open('', '_blank');
    if (printWindow) {
        printWindow.document.write(html);
        printWindow.document.close();
        printWindow.onload = () => printWindow.print();
        showToast('PDF pronto para impressao', 2000);
    } else {
        showToast('Popup bloqueado — permita popups para exportar PDF', 4000);
    }
}

// --- FAVORITOS ---
let favorites = JSON.parse(localStorage.getItem('agent-favorites') || '[]');
let favoritesViewActive = false;

function initFavorites() {
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1 && node.classList.contains('message')) addFavoriteButton(node);
            });
        });
    });
    const chatMsgs = document.getElementById('chat-messages');
    if (chatMsgs) {
        observer.observe(chatMsgs, { childList: true });
        chatMsgs.querySelectorAll('.message').forEach(addFavoriteButton);
    }
    createFavoritesModeIndicator();
}

function addFavoriteButton(messageEl) {
    if (messageEl.querySelector('h6') || messageEl.querySelector('.message-actions')) return;
    const messageId = generateMessageId(messageEl);
    messageEl.dataset.messageId = messageId;
    const content = messageEl.querySelector('.message-content');
    if (!content) return;
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';
    const isFav = favorites.includes(messageId);
    actionsDiv.innerHTML = `<button class="btn-favorite ${isFav ? 'favorited' : ''}" aria-label="${isFav ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}" onclick="toggleFavorite('${messageId}')"><i class="fa${isFav ? 's' : 'r'} fa-star"></i></button>`;
    content.appendChild(actionsDiv);
}

function generateMessageId(messageEl) {
    const bubble = messageEl.querySelector('.message-bubble');
    const content = bubble ? bubble.textContent.substring(0, 50) : '';
    const isUser = messageEl.classList.contains('user');
    return `${isUser ? 'user' : 'assistant'}-${hashCode(content)}`;
}

function hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) { hash = ((hash << 5) - hash) + str.charCodeAt(i); hash = hash & hash; }
    return Math.abs(hash).toString(36);
}

function toggleFavorite(messageId) {
    const index = favorites.indexOf(messageId);
    const btn = document.querySelector(`[data-message-id="${messageId}"] .btn-favorite`);
    if (index === -1) {
        favorites.push(messageId);
        if (btn) { btn.classList.add('favorited'); btn.querySelector('i').className = 'fas fa-star'; btn.setAttribute('aria-label', 'Remover dos favoritos'); }
    } else {
        favorites.splice(index, 1);
        if (btn) { btn.classList.remove('favorited'); btn.querySelector('i').className = 'far fa-star'; btn.setAttribute('aria-label', 'Adicionar aos favoritos'); }
        if (favoritesViewActive) {
            const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
            if (messageEl) messageEl.classList.add('hidden-by-filter');
        }
    }
    localStorage.setItem('agent-favorites', JSON.stringify(favorites));
}

function createFavoritesModeIndicator() {
    const chatContainer = document.querySelector('.chat-container');
    if (!chatContainer) return;
    const indicator = document.createElement('div');
    indicator.className = 'favorites-mode-indicator';
    indicator.id = 'favorites-indicator';
    indicator.setAttribute('role', 'status');
    indicator.innerHTML = '<i class="fas fa-star"></i><span>Mostrando apenas favoritos</span><button onclick="toggleFavoritesView()" aria-label="Sair do modo favoritos"><i class="fas fa-times"></i> Sair</button>';
    const progressBar = document.getElementById('progress-bar-container');
    if (progressBar) { progressBar.after(indicator); }
    else { const header = document.querySelector('.chat-header'); if (header) header.after(indicator); }
}

function toggleFavoritesView() {
    favoritesViewActive = !favoritesViewActive;
    const indicator = document.getElementById('favorites-indicator');
    const messages = document.querySelectorAll('#chat-messages .message');
    if (favoritesViewActive) {
        indicator.classList.add('active');
        messages.forEach((msg, index) => {
            if (index === 0) return;
            const messageId = msg.dataset.messageId;
            if (!favorites.includes(messageId)) msg.classList.add('hidden-by-filter');
        });
    } else {
        indicator.classList.remove('active');
        messages.forEach(msg => msg.classList.remove('hidden-by-filter'));
    }
}

// Inicializar voice e favorites
document.addEventListener('DOMContentLoaded', initVoiceInput);
document.addEventListener('DOMContentLoaded', initFavorites);


// =============================================================
// SESSAO C: CONTROLES MOBILE (BOTTOM SHEET)
// =============================================================

/**
 * Abre o bottom sheet de configuracoes mobile.
 * Sincroniza valores atuais do header desktop para os controles mobile.
 */
function openMobileSettings() {
    const sheet = document.getElementById('mobile-settings-sheet');
    const backdrop = document.getElementById('mobile-settings-backdrop');
    if (!sheet) return;

    // Sync estado atual: desktop → mobile
    const desktopModel = document.getElementById('model-selector');
    const mobileModel = document.getElementById('mobile-model-selector');
    if (desktopModel && mobileModel) {
        mobileModel.value = desktopModel.value;
    }

    // Sync effort
    const desktopActive = document.querySelector('#effort-selector .effort-btn.active');
    if (desktopActive) {
        const activeEffort = desktopActive.dataset.effort;
        document.querySelectorAll('.mobile-effort-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.effort === activeEffort);
        });
    }

    // Sync plan mode
    const desktopPlan = document.getElementById('plan-mode-toggle');
    const mobilePlan = document.getElementById('mobile-plan-mode-toggle');
    if (desktopPlan && mobilePlan) {
        mobilePlan.checked = desktopPlan.checked;
    }

    sheet.style.display = 'block';
    backdrop.style.display = 'block';
}

/**
 * Fecha o bottom sheet.
 */
function closeMobileSettings() {
    const sheet = document.getElementById('mobile-settings-sheet');
    const backdrop = document.getElementById('mobile-settings-backdrop');
    if (sheet) sheet.style.display = 'none';
    if (backdrop) backdrop.style.display = 'none';
}

/**
 * Sincroniza mudanca de um controle mobile para o controle desktop correspondente.
 * O desktop control ja tem os event handlers que persistem no localStorage.
 */
function syncMobileSetting(type, value) {
    switch (type) {
        case 'model': {
            const desktopModel = document.getElementById('model-selector');
            if (desktopModel) {
                desktopModel.value = value;
                desktopModel.dispatchEvent(new Event('change'));
            }
            break;
        }
        case 'effort': {
            // Ativar o botao desktop correspondente
            const desktopBtn = document.querySelector(`#effort-selector .effort-btn[data-effort="${value}"]`);
            if (desktopBtn) desktopBtn.click();
            // Atualizar visual mobile
            document.querySelectorAll('.mobile-effort-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.effort === value);
            });
            break;
        }
        case 'plan': {
            const desktopPlan = document.getElementById('plan-mode-toggle');
            if (desktopPlan && desktopPlan.checked !== value) {
                desktopPlan.checked = value;
                desktopPlan.dispatchEvent(new Event('change'));
            }
            break;
        }
    }
}

/**
 * ChatUI — drawer lateral + tabs + lista de threads + painel de mensagens.
 * Task 18 do plano chat-inapp.
 *
 * Integra com ChatClient (Task 17) para receber eventos SSE e refrescar
 * a lista quando drawer estiver aberto.
 */
(function () {
  'use strict';

  let drawerEl = null;
  let currentTipo = '';  // '' = todos; 'dm' | 'group' | 'entity' | 'system_dm'
  let currentThreadId = null;

  // ==========================================================================
  // Utilitarios
  // ==========================================================================
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  function fmtTime(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      const today = new Date();
      if (d.toDateString() === today.toDateString()) {
        return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      }
      return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
    } catch (e) {
      return '';
    }
  }

  async function fetchJSON(url, opts) {
    const resp = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts || {}));
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`${resp.status}: ${text}`);
    }
    return resp.json();
  }

  // ==========================================================================
  // Drawer (carregado on-demand via fetch HTML)
  // ==========================================================================
  async function loadDrawer() {
    if (drawerEl) return drawerEl;
    const resp = await fetch('/api/chat/ui/drawer', { credentials: 'same-origin' });
    if (!resp.ok) {
      console.error('[chat] loadDrawer failed', resp.status);
      return null;
    }
    const html = await resp.text();
    const tmp = document.createElement('div');
    tmp.innerHTML = html.trim();
    drawerEl = tmp.firstElementChild;
    document.body.appendChild(drawerEl);
    wireDrawerEvents();
    return drawerEl;
  }

  function wireDrawerEvents() {
    drawerEl.querySelector('#chat-drawer-close').addEventListener('click', closeDrawer);
    drawerEl.querySelectorAll('.chat-drawer__tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        drawerEl.querySelectorAll('.chat-drawer__tab').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        currentTipo = btn.dataset.tipo || '';
        refreshThreads();
      });
    });
    // Fix A + D: botoes nova conversa / novo grupo
    const newDmBtn = drawerEl.querySelector('#chat-new-dm');
    const newGroupBtn = drawerEl.querySelector('#chat-new-group');
    if (newDmBtn) newDmBtn.addEventListener('click', openNewDmModal);
    if (newGroupBtn) newGroupBtn.addEventListener('click', openNewGroupModal);
  }

  function openDrawer() {
    loadDrawer().then((el) => {
      if (!el) return;
      el.classList.add('open');
      el.setAttribute('aria-hidden', 'false');
      refreshThreads();
    });
  }

  function closeDrawer() {
    if (drawerEl) {
      drawerEl.classList.remove('open');
      drawerEl.setAttribute('aria-hidden', 'true');
    }
  }

  // ==========================================================================
  // Lista de threads
  // ==========================================================================
  async function refreshThreads() {
    if (!drawerEl) return;
    const list = drawerEl.querySelector('#chat-thread-list');
    list.innerHTML = '<div class="text-muted p-3">Carregando...</div>';
    const url = '/api/chat/threads' + (currentTipo ? `?tipo=${encodeURIComponent(currentTipo)}` : '');
    try {
      const data = await fetchJSON(url);
      if (!data.threads || data.threads.length === 0) {
        list.innerHTML = '<div class="text-muted p-3">Nada aqui ainda.</div>';
        return;
      }
      list.innerHTML = data.threads.map(renderThreadItem).join('');
      list.querySelectorAll('[data-thread-id]').forEach((el) => {
        el.addEventListener('click', () => openPanel(parseInt(el.dataset.threadId, 10)));
      });
    } catch (e) {
      list.innerHTML = `<div class="text-danger p-3">Erro ao carregar: ${escapeHtml(e.message)}</div>`;
    }
  }

  function renderThreadItem(t) {
    const title = t.titulo ||
      (t.entity_type ? `${t.entity_type} ${t.entity_id}` : `Thread #${t.id}`);
    const time = fmtTime(t.last_message_at);
    return `
      <div class="chat-thread-item" data-thread-id="${t.id}">
        <div class="chat-thread-item__title">
          <span>${escapeHtml(title)}</span>
          <span class="chat-thread-item__time">${escapeHtml(time)}</span>
        </div>
        <div class="chat-thread-item__preview">${escapeHtml(t.tipo)}</div>
      </div>`;
  }

  // ==========================================================================
  // Painel de mensagens
  // ==========================================================================
  async function openPanel(threadId) {
    currentThreadId = threadId;
    const container = drawerEl.querySelector('#chat-panel-container');
    container.style.display = 'block';
    container.innerHTML = '<div class="p-3 text-muted">Carregando mensagens...</div>';
    try {
      const data = await fetchJSON(`/api/chat/threads/${threadId}/messages`);
      container.innerHTML = renderPanel(threadId, data.messages || []);
      wirePanelEvents(container, threadId);
      scrollMessagesToBottom(container);
      if (window.ChatClient) window.ChatClient.markRead('user', threadId);
    } catch (e) {
      container.innerHTML = `<div class="text-danger p-3">Erro: ${escapeHtml(e.message)}</div>`;
    }
  }

  function renderPanel(threadId, messages) {
    // messages vem em desc, invertemos pra renderizar cronologicamente
    const msgsHtml = messages.slice().reverse().map(renderMessage).join('');
    return `
      <div class="chat-panel">
        <div class="chat-panel__messages" id="chat-panel-messages-${threadId}">${msgsHtml}</div>
        <form class="chat-panel__footer" id="chat-send-form-${threadId}">
          <textarea class="chat-panel__textarea" name="content" rows="2"
                    placeholder="Digite a mensagem..." required></textarea>
          <button type="submit" class="chat-panel__send">Enviar</button>
        </form>
      </div>`;
  }

  function renderMessage(m) {
    const senderLabel = m.sender_type === 'system'
      ? `[${escapeHtml(m.sender_system_source || 'Sistema')}]`
      : `user#${m.sender_user_id}`;
    const classes = ['chat-message', `chat-message--${m.sender_type}`];
    if (m.nivel === 'CRITICO') classes.push('chat-message--critico');
    else if (m.nivel === 'ATENCAO') classes.push('chat-message--atencao');

    const body = m.content == null
      ? '<em class="text-muted">mensagem deletada</em>'
      : escapeHtml(m.content);
    // Fix B: deep_link com URL completa (origin+path) e preview clicavel.
    // Se deep_link for path relativo ("/carteira/..."), exibe window.location.origin + path.
    // Se ja for absoluto (http/https), exibe como eh.
    let deepLinkBlock = '';
    if (m.deep_link) {
      const absoluteUrl = /^https?:\/\//.test(m.deep_link)
        ? m.deep_link
        : window.location.origin + m.deep_link;
      deepLinkBlock = `
        <div class="chat-message__deeplink">
          <i class="fas fa-link chat-message__deeplink-icon"></i>
          <a href="${escapeHtml(absoluteUrl)}" target="_blank" rel="noopener noreferrer"
             title="Abrir em nova aba">${escapeHtml(absoluteUrl)}</a>
        </div>`;
    }
    // Botao de encaminhar — soh para mensagens nao-deletadas
    const forwardBtn = m.deletado_em
      ? ''
      : `<button type="button" class="chat-message__forward"
                 data-fwd="${m.id}" title="Encaminhar"
                 style="float:right;background:none;border:0;cursor:pointer;color:var(--text-muted);font-size:.85rem;">
           <i class="fas fa-share"></i>
         </button>`;
    return `
      <div class="${classes.join(' ')}" data-msg-id="${m.id}">
        <div class="chat-message__sender">
          ${escapeHtml(senderLabel)} &middot; ${escapeHtml(fmtTime(m.criado_em))}
          ${forwardBtn}
        </div>
        <div class="chat-message__body">${body}</div>
        ${deepLinkBlock}
      </div>`;
  }

  // ==========================================================================
  // User picker (autocomplete reutilizavel — Fix A/C)
  // ==========================================================================
  function createUserPicker(opts) {
    // opts: { inputId, resultsId, onPick(user), multi, excludeIds }
    const input = document.getElementById(opts.inputId);
    const results = document.getElementById(opts.resultsId);
    if (!input || !results) return;
    const excludeIds = new Set(opts.excludeIds || []);
    let debounceTimer = null;
    let activeIdx = -1;
    let items = [];

    async function search(q) {
      const url = '/api/chat/users/eligible?limit=20' + (q ? `&q=${encodeURIComponent(q)}` : '');
      try {
        const data = await fetchJSON(url);
        items = (data.users || []).filter((u) => !excludeIds.has(u.id));
        renderResults();
      } catch (e) {
        results.innerHTML = `<div class="chat-user-picker__empty">Erro: ${escapeHtml(e.message)}</div>`;
      }
    }

    function renderResults() {
      if (items.length === 0) {
        results.innerHTML = '<div class="chat-user-picker__empty">Nenhum usuario elegivel</div>';
        return;
      }
      results.innerHTML = items.map((u, i) => `
        <div class="chat-user-picker__item${i === activeIdx ? ' active' : ''}" data-idx="${i}">
          <span class="chat-user-picker__item-name">${escapeHtml(u.nome)}</span>
          <span class="chat-user-picker__item-email">${escapeHtml(u.email)}</span>
        </div>
      `).join('');
      results.querySelectorAll('[data-idx]').forEach((el) => {
        el.addEventListener('click', () => {
          const idx = parseInt(el.dataset.idx, 10);
          const u = items[idx];
          if (!u) return;
          opts.onPick(u);
          if (!opts.multi) {
            input.value = u.nome;
            results.innerHTML = '';
          } else {
            excludeIds.add(u.id);
            input.value = '';
            results.innerHTML = '';
          }
        });
      });
    }

    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      activeIdx = -1;
      debounceTimer = setTimeout(() => search(input.value.trim()), 200);
    });
    input.addEventListener('focus', () => search(input.value.trim()));
    input.addEventListener('keydown', (e) => {
      if (!items.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIdx = Math.min(activeIdx + 1, items.length - 1);
        renderResults();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIdx = Math.max(activeIdx - 1, 0);
        renderResults();
      } else if (e.key === 'Enter' && activeIdx >= 0) {
        e.preventDefault();
        const u = items[activeIdx];
        if (u) {
          opts.onPick(u);
          if (!opts.multi) {
            input.value = u.nome;
          } else {
            excludeIds.add(u.id);
            input.value = '';
          }
          results.innerHTML = '';
          activeIdx = -1;
        }
      } else if (e.key === 'Escape') {
        results.innerHTML = '';
        activeIdx = -1;
      }
    });

    return {
      addExclude(id) { excludeIds.add(id); },
      removeExclude(id) { excludeIds.delete(id); },
      reset() { input.value = ''; results.innerHTML = ''; items = []; activeIdx = -1; },
    };
  }

  // ==========================================================================
  // Modal: Nova conversa DM (Fix A)
  // ==========================================================================
  function openNewDmModal() {
    const existing = document.getElementById('chat-new-dm-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'chat-new-dm-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1100;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div style="background:var(--bg);color:var(--text);padding:1.5rem;border-radius:8px;min-width:400px;max-width:90vw;border:1px solid var(--border);">
        <h4 style="margin-top:0">Nova conversa</h4>
        <div class="chat-user-picker" style="margin-bottom:1rem">
          <label style="display:block;margin-bottom:.25rem">Buscar usuario (nome ou email):</label>
          <input id="chat-newdm-input" type="text" class="form-control"
                 placeholder="Digite para buscar..." autocomplete="off">
          <div id="chat-newdm-results" class="chat-user-picker__results"></div>
        </div>
        <div style="display:flex;gap:.5rem;justify-content:flex-end">
          <button id="chat-newdm-cancel" type="button" class="btn btn-secondary">Cancelar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    const close = () => modal.remove();
    modal.querySelector('#chat-newdm-cancel').addEventListener('click', close);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

    createUserPicker({
      inputId: 'chat-newdm-input',
      resultsId: 'chat-newdm-results',
      onPick: async (user) => {
        try {
          const resp = await fetchJSON('/api/chat/threads/dm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_user_id: user.id }),
          });
          close();
          // Abrir painel imediatamente
          const threadId = resp.thread.id;
          await loadDrawer();
          drawerEl.classList.add('open');
          drawerEl.setAttribute('aria-hidden', 'false');
          await refreshThreads();
          openPanel(threadId);
        } catch (e) {
          alert(`Erro ao iniciar conversa: ${e.message}`);
        }
      },
    });
    document.getElementById('chat-newdm-input').focus();
  }

  // ==========================================================================
  // Modal: Criar grupo (Fix D)
  // ==========================================================================
  function openNewGroupModal() {
    const existing = document.getElementById('chat-new-group-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'chat-new-group-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1100;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div style="background:var(--bg);color:var(--text);padding:1.5rem;border-radius:8px;min-width:440px;max-width:90vw;border:1px solid var(--border);">
        <h4 style="margin-top:0">Novo grupo</h4>
        <div style="margin-bottom:.75rem">
          <label style="display:block;margin-bottom:.25rem">Titulo do grupo:</label>
          <input id="chat-group-titulo" type="text" class="form-control" required
                 placeholder="Ex: Operacao Atacadao">
        </div>
        <div style="margin-bottom:.5rem">
          <label style="display:block;margin-bottom:.25rem">Membros:</label>
          <div id="chat-group-chips" class="chat-chip-list"></div>
          <div class="chat-user-picker">
            <input id="chat-group-input" type="text" class="form-control"
                   placeholder="Buscar e adicionar usuarios..." autocomplete="off">
            <div id="chat-group-results" class="chat-user-picker__results"></div>
          </div>
        </div>
        <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:1rem">
          <button id="chat-group-cancel" type="button" class="btn btn-secondary">Cancelar</button>
          <button id="chat-group-create" type="button" class="btn btn-primary">Criar grupo</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    const close = () => modal.remove();
    modal.querySelector('#chat-group-cancel').addEventListener('click', close);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

    const selectedMembers = new Map();  // id -> user
    const chipsContainer = modal.querySelector('#chat-group-chips');

    function renderChips() {
      chipsContainer.innerHTML = [...selectedMembers.values()].map((u) => `
        <span class="chat-chip" data-id="${u.id}">
          ${escapeHtml(u.nome)}
          <button class="chat-chip__remove" type="button" data-remove="${u.id}" aria-label="Remover">&times;</button>
        </span>
      `).join('');
      chipsContainer.querySelectorAll('[data-remove]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.dataset.remove, 10);
          selectedMembers.delete(id);
          picker.removeExclude(id);
          renderChips();
        });
      });
    }

    const picker = createUserPicker({
      inputId: 'chat-group-input',
      resultsId: 'chat-group-results',
      multi: true,
      onPick: (user) => {
        selectedMembers.set(user.id, user);
        renderChips();
      },
    });

    modal.querySelector('#chat-group-create').addEventListener('click', async () => {
      const titulo = modal.querySelector('#chat-group-titulo').value.trim();
      if (!titulo) {
        alert('Informe o titulo do grupo.');
        return;
      }
      if (selectedMembers.size === 0) {
        alert('Adicione pelo menos 1 membro.');
        return;
      }
      const btn = modal.querySelector('#chat-group-create');
      btn.disabled = true;
      try {
        const resp = await fetchJSON('/api/chat/threads/group', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            titulo,
            member_ids: [...selectedMembers.keys()],
          }),
        });
        close();
        const threadId = resp.thread.id;
        await loadDrawer();
        drawerEl.classList.add('open');
        drawerEl.setAttribute('aria-hidden', 'false');
        await refreshThreads();
        openPanel(threadId);
      } catch (e) {
        alert(`Erro ao criar grupo: ${e.message}`);
      } finally {
        btn.disabled = false;
      }
    });
    document.getElementById('chat-group-titulo').focus();
  }

  function wirePanelEvents(container, threadId) {
    const form = container.querySelector(`#chat-send-form-${threadId}`);
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const textarea = form.querySelector('[name="content"]');
      const content = textarea.value.trim();
      if (!content) return;
      const btn = form.querySelector('.chat-panel__send');
      btn.disabled = true;
      try {
        await fetchJSON('/api/chat/messages', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ thread_id: threadId, content: content }),
        });
        textarea.value = '';
        await openPanel(threadId);  // re-render
      } catch (err) {
        alert(`Erro ao enviar: ${err.message}`);
      } finally {
        btn.disabled = false;
      }
    });

    // Enter envia (Shift+Enter = quebra de linha)
    form.querySelector('[name="content"]').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    });

    // Botoes de encaminhar (Task 20)
    container.querySelectorAll('[data-fwd]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        openForwardModal(parseInt(btn.dataset.fwd, 10));
      });
    });
  }

  // ==========================================================================
  // Forward modal (Task 20)
  // ==========================================================================
  function openForwardModal(messageId) {
    const existing = document.getElementById('chat-fwd-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'chat-fwd-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1100;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div style="background:var(--bg);color:var(--text);padding:1.5rem;border-radius:8px;min-width:400px;max-width:90vw;border:1px solid var(--border);">
        <h4 style="margin-top:0">Encaminhar mensagem</h4>
        <div style="margin-bottom:.75rem">
          <label style="display:block;margin-bottom:.25rem">Thread destino (ID):</label>
          <input id="chat-fwd-thread" type="number" min="1"
                 class="form-control" placeholder="ex: 12" required>
        </div>
        <div style="margin-bottom:1rem">
          <label style="display:block;margin-bottom:.25rem">Comentario (opcional):</label>
          <textarea id="chat-fwd-cmt" rows="2" class="form-control"
                    placeholder="Ex: olha esse alerta"></textarea>
        </div>
        <div style="display:flex;gap:.5rem;justify-content:flex-end">
          <button id="chat-fwd-cancel" type="button" class="btn btn-secondary">Cancelar</button>
          <button id="chat-fwd-send" type="button" class="btn btn-primary">Encaminhar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);

    const close = () => modal.remove();
    modal.querySelector('#chat-fwd-cancel').addEventListener('click', close);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

    modal.querySelector('#chat-fwd-send').addEventListener('click', async () => {
      const dstThread = parseInt(modal.querySelector('#chat-fwd-thread').value, 10);
      const cmt = modal.querySelector('#chat-fwd-cmt').value.trim();
      if (isNaN(dstThread) || dstThread < 1) {
        alert('Informe um ID de thread valido (numerico).');
        return;
      }
      const sendBtn = modal.querySelector('#chat-fwd-send');
      sendBtn.disabled = true;
      try {
        await fetchJSON(`/api/chat/messages/${messageId}/forward`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            destino_thread_id: dstThread,
            comentario: cmt,
          }),
        });
        close();
        if (window.toastr) window.toastr.success('Encaminhada!');
        else alert('Encaminhada!');
      } catch (e) {
        alert(`Erro: ${e.message}`);
      } finally {
        sendBtn.disabled = false;
      }
    });
  }

  function scrollMessagesToBottom(container) {
    const msgs = container.querySelector('.chat-panel__messages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  // ==========================================================================
  // Share screen modal (Task 19)
  // ==========================================================================
  function openShareModal() {
    const existing = document.getElementById('chat-share-modal');
    if (existing) existing.remove();

    // Fix B: URL completa (origin + path + search) no preview
    const fullUrl = window.location.origin + window.location.pathname + window.location.search;
    const modal = document.createElement('div');
    modal.id = 'chat-share-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1100;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div style="background:var(--bg);color:var(--text);padding:1.5rem;border-radius:8px;min-width:440px;max-width:90vw;border:1px solid var(--border);">
        <h4 style="margin-top:0">Compartilhar esta tela</h4>
        <div class="chat-message__deeplink" style="margin-bottom:1rem">
          <i class="fas fa-link chat-message__deeplink-icon"></i>
          <a href="${escapeHtml(fullUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(fullUrl)}</a>
        </div>
        <div class="chat-user-picker" style="margin-bottom:.75rem">
          <label style="display:block;margin-bottom:.25rem">Destinatario (buscar usuario):</label>
          <input id="chat-share-input" type="text" class="form-control"
                 placeholder="Digite nome ou email..." autocomplete="off" required>
          <div id="chat-share-results" class="chat-user-picker__results"></div>
          <input id="chat-share-dst" type="hidden">
        </div>
        <div style="margin-bottom:1rem">
          <label style="display:block;margin-bottom:.25rem">Comentario (opcional):</label>
          <textarea id="chat-share-cmt" rows="3" class="form-control"
                    placeholder="Ex: pode conferir esse pedido?"></textarea>
        </div>
        <div style="display:flex;gap:.5rem;justify-content:flex-end">
          <button id="chat-share-cancel" type="button" class="btn btn-secondary">Cancelar</button>
          <button id="chat-share-send" type="button" class="btn btn-primary" disabled>Compartilhar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);

    const close = () => modal.remove();
    modal.querySelector('#chat-share-cancel').addEventListener('click', close);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

    createUserPicker({
      inputId: 'chat-share-input',
      resultsId: 'chat-share-results',
      onPick: (user) => {
        modal.querySelector('#chat-share-dst').value = user.id;
        modal.querySelector('#chat-share-send').disabled = false;
      },
    });

    modal.querySelector('#chat-share-send').addEventListener('click', async () => {
      const dstId = parseInt(modal.querySelector('#chat-share-dst').value, 10);
      const cmt = modal.querySelector('#chat-share-cmt').value.trim();
      if (isNaN(dstId) || dstId < 1) {
        alert('Selecione um usuario da lista.');
        return;
      }
      const sendBtn = modal.querySelector('#chat-share-send');
      sendBtn.disabled = true;
      try {
        await fetchJSON('/api/chat/share/screen', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            destinatario_user_id: dstId,
            comentario: cmt,
            url: window.location.pathname + window.location.search,
            title: document.title,
          }),
        });
        close();
        if (window.toastr) window.toastr.success('Tela compartilhada!');
        else alert('Tela compartilhada!');
      } catch (e) {
        alert(`Erro: ${e.message}`);
      } finally {
        sendBtn.disabled = false;
      }
    });
    document.getElementById('chat-share-input').focus();
  }

  // ==========================================================================
  // Bootstrap
  // ==========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('chat-toggle');
    if (!toggle) return;
    toggle.addEventListener('click', openDrawer);

    const shareBtn = document.getElementById('chat-share-screen');
    if (shareBtn) shareBtn.addEventListener('click', openShareModal);

    // Atualizar lista/painel quando chegar nova mensagem via SSE
    if (window.ChatClient) {
      window.ChatClient.onEvent((evt, data) => {
        if (!drawerEl || !drawerEl.classList.contains('open')) return;
        if (evt === 'message_new') {
          // Se a msg chegou na thread aberta, recarregar painel
          if (currentThreadId && data.thread_id === currentThreadId) {
            openPanel(currentThreadId);
          } else {
            refreshThreads();  // atualizar lista (last_message_at mudou)
          }
        } else if (evt === 'message_edit' || evt === 'message_delete') {
          if (currentThreadId && data.thread_id === currentThreadId) {
            openPanel(currentThreadId);
          }
        }
      });
    }
  });

  // Exposto para chat_ui externos (tela compartilhada, etc)
  window.ChatUI = {
    open: openDrawer,
    close: closeDrawer,
    refreshThreads,
    openPanel,
    openShareModal,
    openForwardModal,
    openNewDmModal,
    openNewGroupModal,
  };
})();

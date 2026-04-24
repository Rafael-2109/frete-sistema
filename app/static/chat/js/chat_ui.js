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
    const deepLink = m.deep_link
      ? `<div class="chat-message__meta"><a href="${escapeHtml(m.deep_link)}" target="_blank" rel="noopener noreferrer">Abrir contexto</a></div>`
      : '';
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
        ${deepLink}
      </div>`;
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

    const modal = document.createElement('div');
    modal.id = 'chat-share-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1100;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div style="background:var(--bg);color:var(--text);padding:1.5rem;border-radius:8px;min-width:400px;max-width:90vw;border:1px solid var(--border);">
        <h4 style="margin-top:0">Compartilhar esta tela</h4>
        <div style="margin-bottom:.75rem;font-size:.9rem;color:var(--text-muted)">
          <strong>URL:</strong> <code>${escapeHtml(window.location.pathname + window.location.search)}</code>
        </div>
        <div style="margin-bottom:.75rem">
          <label style="display:block;margin-bottom:.25rem">Destinatario (ID do usuario):</label>
          <input id="chat-share-dst" type="number" min="1"
                 class="form-control" placeholder="ex: 42" required>
        </div>
        <div style="margin-bottom:1rem">
          <label style="display:block;margin-bottom:.25rem">Comentario (opcional):</label>
          <textarea id="chat-share-cmt" rows="3" class="form-control"
                    placeholder="Ex: pode conferir esse pedido?"></textarea>
        </div>
        <div style="display:flex;gap:.5rem;justify-content:flex-end">
          <button id="chat-share-cancel" type="button" class="btn btn-secondary">Cancelar</button>
          <button id="chat-share-send" type="button" class="btn btn-primary">Compartilhar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);

    const close = () => modal.remove();
    modal.querySelector('#chat-share-cancel').addEventListener('click', close);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

    modal.querySelector('#chat-share-send').addEventListener('click', async () => {
      const dstRaw = modal.querySelector('#chat-share-dst').value.trim();
      const cmt = modal.querySelector('#chat-share-cmt').value.trim();
      const dstId = parseInt(dstRaw, 10);
      if (isNaN(dstId) || dstId < 1) {
        alert('Informe um ID de usuario valido (numerico).');
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
        // Toast-like feedback (usa toastr se disponivel, senao alert)
        if (window.toastr) {
          window.toastr.success('Tela compartilhada!');
        } else {
          alert('Tela compartilhada!');
        }
      } catch (e) {
        alert(`Erro: ${e.message}`);
      } finally {
        sendBtn.disabled = false;
      }
    });
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
  };
})();

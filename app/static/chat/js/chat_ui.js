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
    return `
      <div class="${classes.join(' ')}">
        <div class="chat-message__sender">${escapeHtml(senderLabel)} &middot; ${escapeHtml(fmtTime(m.criado_em))}</div>
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
  }

  function scrollMessagesToBottom(container) {
    const msgs = container.querySelector('.chat-panel__messages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  // ==========================================================================
  // Bootstrap
  // ==========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('chat-toggle');
    if (!toggle) return;
    toggle.addEventListener('click', openDrawer);

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
  };
})();

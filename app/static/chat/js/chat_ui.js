/**
 * ChatUI — drawer lateral + lista de threads + painel de mensagens.
 *
 * Reformulado (system-chat-redesign): nomes reais (sem "Thread #N"/"user#42"),
 * avatares, bolhas alinhadas, agrupamento + separador de data, reacoes, citacao,
 * barra de acoes (reagir/responder/encaminhar/editar/excluir/copiar link), busca
 * FTS, toasts e modais via classes CSS. Mantem a API window.ChatUI e a integracao
 * com ChatClient (polling).
 */
(function () {
  'use strict';

  let drawerEl = null;
  let currentTipo = '';        // '' = todos; 'dm' | 'group' | 'entity' | 'system_dm'
  let currentThreadId = null;
  let currentThreadMeta = null; // dict da thread aberta (display_name/avatar/tipo)
  const threadCache = new Map();

  // Estado do compose (preservado entre re-renders do painel)
  let replyingTo = null;        // {id, sender_name, preview}
  let editingMessageId = null;  // id da msg sendo editada
  let composeDraft = '';

  const QUICK_EMOJIS = ['\u{1F44D}', '✅', '❤️', '\u{1F602}', '\u{1F389}', '\u{1F440}'];

  // ==========================================================================
  // Utilitarios
  // ==========================================================================
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  // Markdown leve e SEGURO: escapa primeiro, depois injeta apenas <strong>/<code>
  // (tags fixas, sem href) — zero superficie de XSS. Links chegam via deep_link card.
  function renderRich(text) {
    let h = escapeHtml(text);
    h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
    h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    return h.replace(/\n/g, '<br>');
  }

  // Espelho client-side do url_safe do backend (defesa em profundidade no render).
  function isClickableUrl(u) {
    if (!u || typeof u !== 'string') return false;
    if (/[\t\n\r\x00]/.test(u)) return false;
    if (/^https?:\/\//i.test(u)) return true;
    return u.startsWith('/') && !u.startsWith('//');
  }

  function absUrl(u) {
    return /^https?:\/\//i.test(u) ? u : window.location.origin + u;
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
    } catch (e) { return ''; }
  }

  function fmtClock(iso) {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch (e) { return ''; }
  }

  function dateSepLabel(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      const today = new Date();
      const yest = new Date(); yest.setDate(today.getDate() - 1);
      if (d.toDateString() === today.toDateString()) return 'Hoje';
      if (d.toDateString() === yest.toDateString()) return 'Ontem';
      return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch (e) { return ''; }
  }

  function dayKey(iso) {
    try { return new Date(iso).toDateString(); } catch (e) { return ''; }
  }

  async function fetchJSON(url, opts) {
    const resp = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts || {}));
    if (!resp.ok) {
      let msg = `${resp.status}`;
      try {
        const j = await resp.json();
        if (j && j.error) msg = j.error;
      } catch (e) { /* corpo nao-JSON */ }
      throw new Error(msg);
    }
    return resp.json();
  }

  // ==========================================================================
  // Toasts (substitui alert())
  // ==========================================================================
  function toast(msg, type) {
    if (window.toastr) {
      const fn = window.toastr[type === 'error' ? 'error' : type === 'success' ? 'success' : 'info'];
      if (fn) { fn(msg); return; }
    }
    let wrap = document.getElementById('chat-toast-wrap');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.id = 'chat-toast-wrap';
      wrap.className = 'chat-toast-wrap';
      document.body.appendChild(wrap);
    }
    const el = document.createElement('div');
    el.className = 'chat-toast' + (type ? ` chat-toast--${type}` : '');
    el.textContent = msg;
    wrap.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 200); }, 3200);
  }

  // ==========================================================================
  // Modal helper (classes CSS — sem CSS inline)
  // ==========================================================================
  function buildModal(opts) {
    // opts: { id, title, bodyHtml, footerHtml }
    const existing = document.getElementById(opts.id);
    if (existing) existing.remove();
    const modal = document.createElement('div');
    modal.id = opts.id;
    modal.className = 'chat-modal';
    modal.innerHTML = `
      <div class="chat-modal__dialog" role="dialog" aria-modal="true">
        <h4 class="chat-modal__title">${escapeHtml(opts.title)}</h4>
        <div class="chat-modal__content">${opts.bodyHtml || ''}</div>
        ${opts.footerHtml ? `<div class="chat-modal__footer">${opts.footerHtml}</div>` : ''}
      </div>`;
    document.body.appendChild(modal);
    const close = () => modal.remove();
    // Overlay NAO fecha (evita perder form ao navegar no picker). Fecha por Esc.
    modal.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
    return { modal, close };
  }

  // ==========================================================================
  // Avatar
  // ==========================================================================
  function avatarHtml(av, sizeClass) {
    const cls = 'chat-avatar' + (sizeClass ? ' ' + sizeClass : '');
    if (!av) return `<span class="${cls} chat-avatar--icon"><i class="fas fa-comment"></i></span>`;
    if (av.kind === 'icon') {
      return `<span class="${cls} chat-avatar--icon"><i class="fas ${escapeHtml(av.icon || 'fa-comment')}"></i></span>`;
    }
    return `<span class="${cls} chat-avatar--c${av.color_idx || 0}">${escapeHtml(av.text || '?')}</span>`;
  }

  // ==========================================================================
  // Drawer
  // ==========================================================================
  async function loadDrawer() {
    if (drawerEl) return drawerEl;
    const resp = await fetch('/api/chat/ui/drawer', { credentials: 'same-origin' });
    if (!resp.ok) { console.error('[chat] loadDrawer failed', resp.status); return null; }
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
    const newDmBtn = drawerEl.querySelector('#chat-new-dm');
    const newGroupBtn = drawerEl.querySelector('#chat-new-group');
    if (newDmBtn) newDmBtn.addEventListener('click', openNewDmModal);
    if (newGroupBtn) newGroupBtn.addEventListener('click', openNewGroupModal);

    // Busca FTS (debounce)
    const searchInput = drawerEl.querySelector('#chat-search-input');
    if (searchInput) {
      let t = null;
      searchInput.addEventListener('input', () => {
        clearTimeout(t);
        const q = searchInput.value.trim();
        t = setTimeout(() => (q.length >= 2 ? runSearch(q) : refreshThreads()), 250);
      });
    }
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
    list.innerHTML = '<div class="chat-empty"><div class="chat-empty__hint">Carregando...</div></div>';
    const url = '/api/chat/threads' + (currentTipo ? `?tipo=${encodeURIComponent(currentTipo)}` : '');
    try {
      const data = await fetchJSON(url);
      if (!data.threads || data.threads.length === 0) {
        list.innerHTML = `
          <div class="chat-empty">
            <div class="chat-empty__icon"><i class="far fa-comments"></i></div>
            <div class="chat-empty__title">Nenhuma conversa aqui</div>
            <div class="chat-empty__hint">Use os botoes acima para iniciar uma conversa ou criar um grupo.</div>
          </div>`;
        return;
      }
      data.threads.forEach((t) => threadCache.set(t.id, t));
      list.innerHTML = data.threads.map(renderThreadItem).join('');
      list.querySelectorAll('[data-thread-id]').forEach((el) => {
        el.addEventListener('click', () => openPanel(parseInt(el.dataset.threadId, 10)));
      });
    } catch (e) {
      list.innerHTML = `<div class="chat-empty"><div class="chat-empty__hint">Erro ao carregar: ${escapeHtml(e.message)}</div></div>`;
    }
  }

  function renderThreadItem(t) {
    const name = t.display_name || t.titulo || `Conversa ${t.id}`;
    const time = fmtTime(t.last_message_at);
    const unread = t.unread_count || 0;
    let preview = '';
    if (t.preview) {
      const sender = t.preview_sender ? `<b>${escapeHtml(t.preview_sender)}:</b> ` : '';
      preview = sender + escapeHtml(t.preview);
    } else {
      preview = '<span style="opacity:.7">Sem mensagens ainda</span>';
    }
    const badgeCls = t.preview_nivel === 'CRITICO'
      ? 'chat-thread-item__badge'
      : t.tipo === 'system_dm' ? 'chat-thread-item__badge chat-thread-item__badge--nivel'
      : 'chat-thread-item__badge';
    const badge = unread > 0
      ? `<span class="${badgeCls}">${unread > 99 ? '99+' : unread}</span>` : '';
    return `
      <div class="chat-thread-item${unread > 0 ? ' chat-thread-item--unread' : ''}" data-thread-id="${t.id}">
        ${avatarHtml(t.avatar)}
        <div class="chat-thread-item__main">
          <div class="chat-thread-item__title">
            <span class="chat-thread-item__name">${escapeHtml(name)}</span>
            <span class="chat-thread-item__time">${escapeHtml(time)}</span>
          </div>
          <div class="chat-thread-item__preview">${preview}</div>
        </div>
        ${badge}
      </div>`;
  }

  // ==========================================================================
  // Busca FTS
  // ==========================================================================
  async function runSearch(q) {
    if (!drawerEl) return;
    const list = drawerEl.querySelector('#chat-thread-list');
    list.innerHTML = '<div class="chat-empty"><div class="chat-empty__hint">Buscando...</div></div>';
    try {
      const data = await fetchJSON('/api/chat/search?q=' + encodeURIComponent(q));
      if (!data.results || data.results.length === 0) {
        list.innerHTML = `<div class="chat-empty"><div class="chat-empty__title">Nada encontrado</div>
          <div class="chat-empty__hint">Nenhuma mensagem para "${escapeHtml(q)}".</div></div>`;
        return;
      }
      list.innerHTML = data.results.map((r) => `
        <div class="chat-search-result" data-thread-id="${r.thread_id}">
          <div class="chat-search-result__snippet">${escapeHtml(r.content)}</div>
          <div class="chat-search-result__meta">${escapeHtml(fmtTime(r.criado_em))} · conversa #${r.thread_id}</div>
        </div>`).join('');
      list.querySelectorAll('[data-thread-id]').forEach((el) => {
        el.addEventListener('click', () => openPanel(parseInt(el.dataset.threadId, 10)));
      });
    } catch (e) {
      list.innerHTML = `<div class="chat-empty"><div class="chat-empty__hint">Erro na busca: ${escapeHtml(e.message)}</div></div>`;
    }
  }

  // ==========================================================================
  // Painel de mensagens
  // ==========================================================================
  async function openPanel(threadId, opts) {
    opts = opts || {};
    // Preserva rascunho ao re-renderizar (ex.: chegou msg nova via poll).
    if (opts.preserveDraft && currentThreadId === threadId) {
      const ta = drawerEl && drawerEl.querySelector('.chat-panel__textarea');
      if (ta) composeDraft = ta.value;
    } else if (currentThreadId !== threadId) {
      // Troca de thread: limpa estado de compose.
      replyingTo = null; editingMessageId = null; composeDraft = '';
    }
    currentThreadId = threadId;
    currentThreadMeta = threadCache.get(threadId) || null;
    const container = drawerEl.querySelector('#chat-panel-container');
    container.style.display = 'block';
    if (!opts.preserveDraft) {
      container.innerHTML = '<div class="chat-empty"><div class="chat-empty__hint">Carregando mensagens...</div></div>';
    }
    try {
      const data = await fetchJSON(`/api/chat/threads/${threadId}/messages`);
      container.innerHTML = renderPanel(threadId, data.messages || []);
      wirePanelEvents(container, threadId);
      scrollMessagesToBottom(container);
      if (window.ChatClient) window.ChatClient.markRead('user', threadId);
    } catch (e) {
      container.innerHTML = `<div class="chat-empty"><div class="chat-empty__hint">Erro: ${escapeHtml(e.message)}</div></div>`;
    }
  }

  function renderPanel(threadId, messages) {
    const thread = currentThreadMeta || threadCache.get(threadId);
    const title = thread ? (thread.display_name || thread.titulo || `Conversa ${threadId}`) : `Conversa ${threadId}`;
    const subtitle = thread && thread.tipo === 'group'
      ? `${thread.members_count || 0} membros`
      : thread && thread.tipo === 'entity' ? 'Conversa de entidade'
      : thread && thread.tipo === 'system_dm' ? 'Alertas automaticos' : '';

    // messages vem desc -> render cronologico com separadores de data + agrupamento
    const ordered = messages.slice().reverse();
    let html = '';
    let lastDay = null;
    let lastSenderKey = null;
    ordered.forEach((m) => {
      const dk = dayKey(m.criado_em);
      if (dk !== lastDay) {
        html += `<div class="chat-date-sep">${escapeHtml(dateSepLabel(m.criado_em))}</div>`;
        lastDay = dk;
        lastSenderKey = null;
      }
      const senderKey = m.sender_type === 'system' ? 's:' + m.sender_system_source : 'u:' + m.sender_user_id;
      const grouped = senderKey === lastSenderKey;
      html += renderMessage(m, grouped);
      lastSenderKey = senderKey;
    });
    if (!ordered.length) {
      html = '<div class="chat-empty"><div class="chat-empty__hint">Nenhuma mensagem ainda. Diga ola \u{1F44B}</div></div>';
    }

    const canAddMembers = thread && (thread.tipo === 'group' || thread.tipo === 'entity');
    const addMembersBtn = canAddMembers
      ? `<button type="button" id="chat-panel-add-member-${threadId}" class="chat-share-btn" title="Adicionar membro">
           <i class="fas fa-user-plus"></i></button>` : '';

    return `
      <div class="chat-panel">
        <div class="chat-panel__header">
          <button type="button" class="chat-panel__back" id="chat-panel-back-${threadId}" aria-label="Voltar">&larr;</button>
          ${avatarHtml(thread && thread.avatar, 'chat-avatar--sm')}
          <div class="chat-panel__title">
            ${escapeHtml(title)}
            ${subtitle ? `<div style="font-size:.72rem;font-weight:400;color:var(--text-muted)">${escapeHtml(subtitle)}</div>` : ''}
          </div>
          ${addMembersBtn}
        </div>
        <div class="chat-panel__messages" id="chat-panel-messages-${threadId}">${html}</div>
        ${renderComposeExtras()}
        <form class="chat-panel__footer" id="chat-send-form-${threadId}">
          <textarea class="chat-panel__textarea" name="content" rows="1"
                    placeholder="Digite a mensagem..."></textarea>
          <button type="submit" class="chat-panel__send" title="Enviar">
            <i class="fas fa-paper-plane"></i>
          </button>
        </form>
      </div>`;
  }

  function renderComposeExtras() {
    if (editingMessageId) {
      return `<div class="chat-panel__editing-flag">
        <span><i class="fas fa-pen"></i> Editando mensagem</span>
        <button type="button" id="chat-cancel-edit" title="Cancelar edicao">&times;</button>
      </div>`;
    }
    if (replyingTo) {
      return `<div class="chat-panel__replying">
        <div class="chat-panel__replying-body">
          <span class="chat-panel__replying-sender">${escapeHtml(replyingTo.sender_name || '')}</span>
          <span class="chat-panel__replying-preview">${escapeHtml(replyingTo.preview || '')}</span>
        </div>
        <button type="button" class="chat-panel__replying-cancel" id="chat-cancel-reply" title="Cancelar">&times;</button>
      </div>`;
    }
    return '';
  }

  function renderMessage(m, grouped) {
    const classes = ['chat-message'];
    if (m.is_own) classes.push('chat-message--own');
    if (m.sender_type === 'system') classes.push('chat-message--system');
    if (m.nivel === 'CRITICO') classes.push('chat-message--critico');
    else if (m.nivel === 'ATENCAO') classes.push('chat-message--atencao');
    if (m.deletado_em) classes.push('chat-message--deleted');
    if (grouped) classes.push('chat-message--grouped');

    const av = m.sender_type === 'system'
      ? { kind: 'icon', icon: 'fa-bell' }
      : { kind: 'initials', text: (m.sender_name || '?'), color_idx: (m.sender_user_id || 0) % 8 };

    const deleted = !!m.deletado_em;
    const body = deleted
      ? '<em>mensagem removida</em>'
      : renderRich(m.content || '');

    // Citacao (reply)
    let replyBlock = '';
    if (m.reply_to) {
      replyBlock = `
        <div class="chat-message__reply" data-jump="${m.reply_to.id}">
          <span class="chat-message__reply-sender">${escapeHtml(m.reply_to.sender_name || '')}</span>
          <span class="chat-message__reply-preview">${escapeHtml(m.reply_to.preview || '')}</span>
        </div>`;
    }

    // Card de deep link
    let deepLinkBlock = '';
    if (m.deep_link && isClickableUrl(m.deep_link)) {
      const url = absUrl(m.deep_link);
      deepLinkBlock = `
        <div class="chat-message__deeplink">
          <i class="fas fa-up-right-from-square chat-message__deeplink-icon"></i>
          <a class="chat-message__deeplink-label" href="${escapeHtml(url)}" target="_blank"
             rel="noopener noreferrer" title="${escapeHtml(url)}">Abrir link</a>
        </div>`;
    }

    // Reacoes
    let reactionsBlock = '';
    if (m.reactions && m.reactions.length) {
      reactionsBlock = `<div class="chat-message__reactions">` + m.reactions.map((r) => `
        <button type="button" class="chat-reaction${r.mine ? ' chat-reaction--mine' : ''}"
                data-react-toggle="${m.id}" data-emoji="${escapeHtml(r.emoji)}" data-mine="${r.mine ? 1 : 0}">
          <span>${escapeHtml(r.emoji)}</span><span class="chat-reaction__count">${r.count}</span>
        </button>`).join('') + `</div>`;
    }

    // Barra de acoes
    let actions = '';
    if (!deleted) {
      const a = [];
      a.push(`<button type="button" class="chat-message__action" data-action="react" data-msg="${m.id}" title="Reagir"><i class="far fa-face-smile"></i></button>`);
      a.push(`<button type="button" class="chat-message__action" data-action="reply" data-msg="${m.id}" title="Responder"><i class="fas fa-reply"></i></button>`);
      a.push(`<button type="button" class="chat-message__action" data-action="forward" data-msg="${m.id}" title="Encaminhar"><i class="fas fa-share"></i></button>`);
      if (m.deep_link && isClickableUrl(m.deep_link)) {
        a.push(`<button type="button" class="chat-message__action" data-action="copy" data-msg="${m.id}" title="Copiar link"><i class="fas fa-link"></i></button>`);
      }
      if (m.can_edit) {
        a.push(`<button type="button" class="chat-message__action" data-action="edit" data-msg="${m.id}" title="Editar"><i class="fas fa-pen"></i></button>`);
      }
      if (m.can_delete) {
        a.push(`<button type="button" class="chat-message__action chat-message__action--danger" data-action="delete" data-msg="${m.id}" title="Excluir"><i class="fas fa-trash"></i></button>`);
      }
      actions = `<div class="chat-message__actions">${a.join('')}</div>`;
    }

    const senderName = m.sender_type === 'system' ? (m.sender_name || 'Sistema') : (m.sender_name || 'Usuário');
    const edited = m.editado_em ? ' <span class="chat-message__edited">(editado)</span>' : '';

    return `
      <div class="${classes.join(' ')}" data-msg-id="${m.id}"
           data-content="${escapeHtml(m.content || '')}"
           data-sender="${escapeHtml(senderName)}"
           data-deeplink="${escapeHtml(m.deep_link || '')}">
        ${avatarHtml(av, 'chat-avatar--sm')}
        <div class="chat-message__col">
          ${m.is_own ? '' : `<div class="chat-message__sender">${escapeHtml(senderName)}</div>`}
          ${replyBlock}
          <div class="chat-message__body">${body}</div>
          ${deepLinkBlock}
          ${reactionsBlock}
          <div class="chat-message__meta">${escapeHtml(fmtClock(m.criado_em))}${edited}</div>
          ${actions}
        </div>
      </div>`;
  }

  // ==========================================================================
  // Eventos do painel
  // ==========================================================================
  function wirePanelEvents(container, threadId) {
    const form = container.querySelector(`#chat-send-form-${threadId}`);
    const textarea = form ? form.querySelector('[name="content"]') : null;

    if (textarea) {
      textarea.value = composeDraft || '';
      // Auto-resize simples
      const autoSize = () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px';
      };
      textarea.addEventListener('input', autoSize);
      autoSize();
      if (editingMessageId || replyingTo) textarea.focus();

      textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          form.dispatchEvent(new Event('submit', { cancelable: true }));
        } else if (e.key === 'Escape') {
          if (editingMessageId || replyingTo) {
            editingMessageId = null; replyingTo = null;
            openPanel(threadId, { preserveDraft: true });
          }
        }
      });
    }

    if (form) {
      form.addEventListener('submit', (e) => { e.preventDefault(); submitCompose(form, threadId); });
    }

    const cancelReply = container.querySelector('#chat-cancel-reply');
    if (cancelReply) cancelReply.addEventListener('click', () => {
      replyingTo = null; openPanel(threadId, { preserveDraft: true });
    });
    const cancelEdit = container.querySelector('#chat-cancel-edit');
    if (cancelEdit) cancelEdit.addEventListener('click', () => {
      editingMessageId = null; composeDraft = ''; openPanel(threadId);
    });

    const backBtn = container.querySelector(`#chat-panel-back-${threadId}`);
    if (backBtn) backBtn.addEventListener('click', () => {
      currentThreadId = null; currentThreadMeta = null;
      replyingTo = null; editingMessageId = null; composeDraft = '';
      container.style.display = 'none';
      refreshThreads();
    });

    const addBtn = container.querySelector(`#chat-panel-add-member-${threadId}`);
    if (addBtn) addBtn.addEventListener('click', () => openAddMemberModal(threadId));

    // Delegacao das acoes de mensagem
    const msgs = container.querySelector('.chat-panel__messages');
    if (msgs) {
      msgs.addEventListener('click', (e) => {
        const actBtn = e.target.closest('[data-action]');
        if (actBtn) { handleMessageAction(actBtn.dataset.action, parseInt(actBtn.dataset.msg, 10), actBtn, threadId); return; }
        const rx = e.target.closest('[data-react-toggle]');
        if (rx) { toggleReaction(parseInt(rx.dataset.reactToggle, 10), rx.dataset.emoji, rx.dataset.mine === '1', threadId); return; }
        const jump = e.target.closest('[data-jump]');
        if (jump) { highlightMessage(parseInt(jump.dataset.jump, 10)); }
      });
    }
  }

  async function submitCompose(form, threadId) {
    const textarea = form.querySelector('[name="content"]');
    const content = textarea.value.trim();
    if (!content) return;
    const btn = form.querySelector('.chat-panel__send');
    btn.disabled = true;
    try {
      if (editingMessageId) {
        await fetchJSON(`/api/chat/messages/${editingMessageId}`, {
          method: 'PATCH', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content }),
        });
        editingMessageId = null; composeDraft = '';
        toast('Mensagem editada', 'success');
      } else {
        const payload = { thread_id: threadId, content };
        if (replyingTo) payload.reply_to_message_id = replyingTo.id;
        await fetchJSON('/api/chat/messages', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        replyingTo = null; composeDraft = '';
      }
      await openPanel(threadId);
    } catch (err) {
      toast('Erro ao enviar: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
    }
  }

  function handleMessageAction(action, messageId, btn, threadId) {
    const msgEl = btn.closest('[data-msg-id]');
    if (action === 'reply') {
      replyingTo = {
        id: messageId,
        sender_name: msgEl ? msgEl.dataset.sender : '',
        preview: msgEl ? (msgEl.dataset.content || '').slice(0, 120) : '',
      };
      editingMessageId = null;
      openPanel(threadId, { preserveDraft: true });
    } else if (action === 'edit') {
      editingMessageId = messageId;
      replyingTo = null;
      // Sem preserveDraft: queremos SUBSTITUIR o rascunho pelo conteudo da msg
      // (preserveDraft capturaria o textarea atual e sobrescreveria este valor).
      composeDraft = msgEl ? msgEl.dataset.content || '' : '';
      openPanel(threadId);
    } else if (action === 'delete') {
      if (!confirm('Excluir esta mensagem?')) return;
      fetchJSON(`/api/chat/messages/${messageId}`, { method: 'DELETE' })
        .then(() => { toast('Mensagem excluida', 'success'); openPanel(threadId, { preserveDraft: true }); })
        .catch((e) => toast('Erro ao excluir: ' + e.message, 'error'));
    } else if (action === 'forward') {
      openForwardModal(messageId);
    } else if (action === 'copy') {
      const link = msgEl ? msgEl.dataset.deeplink : '';
      if (link && navigator.clipboard) {
        navigator.clipboard.writeText(absUrl(link))
          .then(() => toast('Link copiado', 'success'))
          .catch(() => toast('Nao foi possivel copiar', 'error'));
      }
    } else if (action === 'react') {
      openEmojiPopover(btn, messageId, threadId);
    }
  }

  function openEmojiPopover(anchorBtn, messageId, threadId) {
    document.querySelectorAll('.chat-emoji-pop').forEach((el) => el.remove());
    const pop = document.createElement('div');
    pop.className = 'chat-emoji-pop';
    pop.innerHTML = QUICK_EMOJIS.map((e) => `<button type="button" data-emoji="${e}">${e}</button>`).join('');
    document.body.appendChild(pop);
    const r = anchorBtn.getBoundingClientRect();
    pop.style.top = (window.scrollY + r.top - 40) + 'px';
    pop.style.left = (window.scrollX + r.left) + 'px';
    pop.querySelectorAll('button').forEach((b) => {
      b.addEventListener('click', () => {
        pop.remove();
        toggleReaction(messageId, b.dataset.emoji, false, threadId);
      });
    });
    const closer = (ev) => {
      if (!pop.contains(ev.target)) { pop.remove(); document.removeEventListener('mousedown', closer); }
    };
    setTimeout(() => document.addEventListener('mousedown', closer), 0);
  }

  async function toggleReaction(messageId, emoji, mine, threadId) {
    try {
      if (mine) {
        await fetchJSON(`/api/chat/messages/${messageId}/reactions/${encodeURIComponent(emoji)}`, { method: 'DELETE' });
      } else {
        await fetchJSON(`/api/chat/messages/${messageId}/reactions`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ emoji }),
        });
      }
      openPanel(threadId, { preserveDraft: true });
    } catch (e) {
      // 409 = ja existe (corrida) — apenas re-render.
      openPanel(threadId, { preserveDraft: true });
    }
  }

  function highlightMessage(messageId) {
    const el = drawerEl && drawerEl.querySelector(`[data-msg-id="${messageId}"]`);
    if (!el) return;
    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    el.style.transition = 'background .3s';
    el.style.background = 'var(--semantic-warning-subtle)';
    setTimeout(() => { el.style.background = ''; }, 900);
  }

  function scrollMessagesToBottom(container) {
    const msgs = container.querySelector('.chat-panel__messages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  // ==========================================================================
  // User picker (autocomplete reutilizavel)
  // ==========================================================================
  function createUserPicker(opts) {
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
        </div>`).join('');
      results.querySelectorAll('[data-idx]').forEach((el) => {
        el.addEventListener('mousedown', (ev) => {
          ev.preventDefault();
          const u = items[parseInt(el.dataset.idx, 10)];
          if (!u) return;
          opts.onPick(u);
          if (!opts.multi) {
            input.value = u.nome; results.innerHTML = '';
          } else {
            excludeIds.add(u.id); input.value = '';
            items = items.filter((x) => x.id !== u.id);
            activeIdx = -1; renderResults(); input.focus();
          }
        });
      });
    }

    input.addEventListener('input', () => {
      clearTimeout(debounceTimer); activeIdx = -1;
      debounceTimer = setTimeout(() => search(input.value.trim()), 200);
    });
    input.addEventListener('focus', () => search(input.value.trim()));

    function handleOutsideClick(ev) {
      const container = input.closest('.chat-user-picker');
      if (container && !container.contains(ev.target)) { results.innerHTML = ''; activeIdx = -1; }
    }
    document.addEventListener('mousedown', handleOutsideClick);
    const cleanupObserver = new MutationObserver(() => {
      if (!document.contains(input)) {
        document.removeEventListener('mousedown', handleOutsideClick);
        cleanupObserver.disconnect();
      }
    });
    cleanupObserver.observe(document.body, { childList: true, subtree: true });

    input.addEventListener('keydown', (e) => {
      if (!items.length) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); activeIdx = Math.min(activeIdx + 1, items.length - 1); renderResults(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx = Math.max(activeIdx - 1, 0); renderResults(); }
      else if (e.key === 'Enter' && activeIdx >= 0) {
        e.preventDefault();
        const u = items[activeIdx];
        if (u) {
          opts.onPick(u);
          if (!opts.multi) { input.value = u.nome; results.innerHTML = ''; activeIdx = -1; }
          else { excludeIds.add(u.id); input.value = ''; items = items.filter((x) => x.id !== u.id); activeIdx = -1; renderResults(); }
        }
      } else if (e.key === 'Escape') { results.innerHTML = ''; activeIdx = -1; }
    });

    return {
      addExclude(id) { excludeIds.add(id); },
      removeExclude(id) { excludeIds.delete(id); },
      reset() { input.value = ''; results.innerHTML = ''; items = []; activeIdx = -1; },
    };
  }

  // ==========================================================================
  // Modal: Nova conversa DM
  // ==========================================================================
  function openNewDmModal() {
    const { close } = buildModal({
      id: 'chat-new-dm-modal',
      title: 'Nova conversa',
      bodyHtml: `
        <div class="chat-user-picker chat-modal__field">
          <label>Buscar usuario (nome ou email):</label>
          <input id="chat-newdm-input" type="text" class="form-control" placeholder="Digite para buscar..." autocomplete="off">
          <div id="chat-newdm-results" class="chat-user-picker__results"></div>
        </div>`,
      footerHtml: `<button id="chat-newdm-cancel" type="button" class="btn btn-secondary">Cancelar</button>`,
    });
    document.getElementById('chat-newdm-cancel').addEventListener('click', close);
    createUserPicker({
      inputId: 'chat-newdm-input', resultsId: 'chat-newdm-results',
      onPick: async (user) => {
        try {
          const resp = await fetchJSON('/api/chat/threads/dm', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_user_id: user.id }),
          });
          close();
          await ensureDrawerOpen();
          if (resp.thread) threadCache.set(resp.thread.id, resp.thread);
          await refreshThreads();
          openPanel(resp.thread.id);
        } catch (e) { toast('Erro ao iniciar conversa: ' + e.message, 'error'); }
      },
    });
    document.getElementById('chat-newdm-input').focus();
  }

  // ==========================================================================
  // Modal: Criar grupo
  // ==========================================================================
  function openNewGroupModal() {
    const { modal, close } = buildModal({
      id: 'chat-new-group-modal',
      title: 'Novo grupo',
      bodyHtml: `
        <div class="chat-modal__field">
          <label>Titulo do grupo:</label>
          <input id="chat-group-titulo" type="text" class="form-control" placeholder="Ex: Operacao Atacadao">
        </div>
        <div class="chat-modal__field">
          <label id="chat-group-chips-label">Nenhum membro selecionado ainda</label>
          <div id="chat-group-chips" class="chat-chip-list" style="display:none"></div>
          <div class="chat-user-picker">
            <label>Buscar e adicionar:</label>
            <input id="chat-group-input" type="text" class="form-control" placeholder="Digite nome ou email..." autocomplete="off">
            <div id="chat-group-results" class="chat-user-picker__results"></div>
          </div>
          <div class="chat-modal__hint">Dica: clique em varios nomes para adicionar. Esc fecha a lista.</div>
        </div>`,
      footerHtml: `
        <button id="chat-group-cancel" type="button" class="btn btn-secondary">Cancelar</button>
        <button id="chat-group-create" type="button" class="btn btn-primary">Criar grupo</button>`,
    });
    modal.querySelector('#chat-group-cancel').addEventListener('click', close);

    const selectedMembers = new Map();
    const chipsContainer = modal.querySelector('#chat-group-chips');
    const chipsLabel = modal.querySelector('#chat-group-chips-label');

    function renderChips() {
      const n = selectedMembers.size;
      chipsLabel.textContent = n === 0 ? 'Nenhum membro selecionado ainda' : `${n} membro${n > 1 ? 's' : ''} selecionado${n > 1 ? 's' : ''}:`;
      chipsContainer.style.display = n === 0 ? 'none' : 'flex';
      chipsContainer.innerHTML = [...selectedMembers.values()].map((u) => `
        <span class="chat-chip" data-id="${u.id}">${escapeHtml(u.nome)}
          <button class="chat-chip__remove" type="button" data-remove="${u.id}" aria-label="Remover">&times;</button>
        </span>`).join('');
      chipsContainer.querySelectorAll('[data-remove]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.dataset.remove, 10);
          selectedMembers.delete(id); picker.removeExclude(id); renderChips();
        });
      });
    }

    const picker = createUserPicker({
      inputId: 'chat-group-input', resultsId: 'chat-group-results', multi: true,
      onPick: (user) => { selectedMembers.set(user.id, user); renderChips(); },
    });
    renderChips();

    modal.querySelector('#chat-group-create').addEventListener('click', async () => {
      const titulo = modal.querySelector('#chat-group-titulo').value.trim();
      if (!titulo) { toast('Informe o titulo do grupo.', 'error'); return; }
      if (selectedMembers.size === 0) { toast('Adicione pelo menos 1 membro.', 'error'); return; }
      const btn = modal.querySelector('#chat-group-create');
      btn.disabled = true;
      try {
        const resp = await fetchJSON('/api/chat/threads/group', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ titulo, member_ids: [...selectedMembers.keys()] }),
        });
        close();
        await ensureDrawerOpen();
        if (resp.thread) threadCache.set(resp.thread.id, resp.thread);
        await refreshThreads();
        openPanel(resp.thread.id);
      } catch (e) { toast('Erro ao criar grupo: ' + e.message, 'error'); }
      finally { btn.disabled = false; }
    });
    document.getElementById('chat-group-titulo').focus();
  }

  // ==========================================================================
  // Modal: Adicionar membros
  // ==========================================================================
  function openAddMemberModal(threadId) {
    const { modal, close } = buildModal({
      id: 'chat-add-member-modal',
      title: 'Adicionar membros',
      bodyHtml: `
        <div class="chat-modal__field">
          <label id="chat-addm-chips-label">Nenhum usuario selecionado ainda</label>
          <div id="chat-addm-chips" class="chat-chip-list" style="display:none"></div>
          <div class="chat-user-picker">
            <label>Buscar:</label>
            <input id="chat-addm-input" type="text" class="form-control" placeholder="Digite nome ou email..." autocomplete="off">
            <div id="chat-addm-results" class="chat-user-picker__results"></div>
          </div>
          <div class="chat-modal__hint">Dica: clique em varios nomes para adicionar. Esc fecha a lista.</div>
        </div>`,
      footerHtml: `
        <button id="chat-addm-cancel" type="button" class="btn btn-secondary">Cancelar</button>
        <button id="chat-addm-confirm" type="button" class="btn btn-primary" disabled>Adicionar</button>`,
    });
    modal.querySelector('#chat-addm-cancel').addEventListener('click', close);

    const selected = new Map();
    const chipsContainer = modal.querySelector('#chat-addm-chips');
    const chipsLabel = modal.querySelector('#chat-addm-chips-label');
    const confirmBtn = modal.querySelector('#chat-addm-confirm');

    function renderChips() {
      const n = selected.size;
      chipsLabel.textContent = n === 0 ? 'Nenhum usuario selecionado ainda' : `${n} usuario${n > 1 ? 's' : ''} selecionado${n > 1 ? 's' : ''}:`;
      chipsContainer.style.display = n === 0 ? 'none' : 'flex';
      chipsContainer.innerHTML = [...selected.values()].map((u) => `
        <span class="chat-chip" data-id="${u.id}">${escapeHtml(u.nome)}
          <button class="chat-chip__remove" type="button" data-remove="${u.id}" aria-label="Remover">&times;</button>
        </span>`).join('');
      chipsContainer.querySelectorAll('[data-remove]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.dataset.remove, 10);
          selected.delete(id); picker.removeExclude(id); renderChips();
        });
      });
      confirmBtn.disabled = n === 0;
    }

    const picker = createUserPicker({
      inputId: 'chat-addm-input', resultsId: 'chat-addm-results', multi: true,
      onPick: (user) => { selected.set(user.id, user); renderChips(); },
    });
    renderChips();

    confirmBtn.addEventListener('click', async () => {
      confirmBtn.disabled = true;
      const errors = [];
      for (const u of selected.values()) {
        try {
          await fetchJSON(`/api/chat/threads/${threadId}/members`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: u.id }),
          });
        } catch (e) { errors.push(`${u.nome}: ${e.message}`); }
      }
      close();
      if (errors.length) toast('Alguns erros: ' + errors.join('; '), 'error');
      else toast(`${selected.size} membro(s) adicionado(s)`, 'success');
      openPanel(threadId);
    });
    document.getElementById('chat-addm-input').focus();
  }

  // ==========================================================================
  // Modal: Encaminhar (seletor de conversa OU pessoa — sem digitar ID)
  // ==========================================================================
  async function openForwardModal(messageId) {
    const { modal, close } = buildModal({
      id: 'chat-fwd-modal',
      title: 'Encaminhar mensagem',
      bodyHtml: `
        <div class="chat-modal__tabs">
          <button type="button" class="chat-modal__tab active" data-fwd-tab="conversa">Conversa</button>
          <button type="button" class="chat-modal__tab" data-fwd-tab="pessoa">Pessoa</button>
        </div>
        <div id="chat-fwd-pane-conversa">
          <div class="chat-modal__field">
            <input id="chat-fwd-filter" type="text" class="form-control" placeholder="Filtrar conversas..." autocomplete="off">
          </div>
          <div id="chat-fwd-thread-list" style="max-height:240px;overflow-y:auto"></div>
        </div>
        <div id="chat-fwd-pane-pessoa" style="display:none">
          <div class="chat-user-picker chat-modal__field">
            <label>Buscar usuario (cria/abre uma DM):</label>
            <input id="chat-fwd-user" type="text" class="form-control" placeholder="Digite nome ou email..." autocomplete="off">
            <div id="chat-fwd-user-results" class="chat-user-picker__results"></div>
          </div>
        </div>
        <div class="chat-modal__field">
          <label>Comentario (opcional):</label>
          <textarea id="chat-fwd-cmt" rows="2" class="form-control" placeholder="Ex: olha esse alerta"></textarea>
        </div>`,
      footerHtml: `<button id="chat-fwd-cancel" type="button" class="btn btn-secondary">Cancelar</button>`,
    });
    modal.querySelector('#chat-fwd-cancel').addEventListener('click', close);

    const getCmt = () => modal.querySelector('#chat-fwd-cmt').value.trim();

    async function doForward(destThreadId) {
      try {
        await fetchJSON(`/api/chat/messages/${messageId}/forward`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ destino_thread_id: destThreadId, comentario: getCmt() }),
        });
        close();
        toast('Mensagem encaminhada', 'success');
      } catch (e) { toast('Erro ao encaminhar: ' + e.message, 'error'); }
    }

    // Tabs
    modal.querySelectorAll('[data-fwd-tab]').forEach((tab) => {
      tab.addEventListener('click', () => {
        modal.querySelectorAll('[data-fwd-tab]').forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        const isConversa = tab.dataset.fwdTab === 'conversa';
        modal.querySelector('#chat-fwd-pane-conversa').style.display = isConversa ? 'block' : 'none';
        modal.querySelector('#chat-fwd-pane-pessoa').style.display = isConversa ? 'none' : 'block';
      });
    });

    // Lista de conversas existentes
    const listEl = modal.querySelector('#chat-fwd-thread-list');
    let allThreads = [];
    try {
      const data = await fetchJSON('/api/chat/threads');
      allThreads = (data.threads || []).filter((t) => t.tipo !== 'system_dm');
    } catch (e) { /* ignora */ }

    function renderThreadPicks(filter) {
      const f = (filter || '').toLowerCase();
      const items = allThreads.filter((t) => (t.display_name || '').toLowerCase().includes(f));
      if (!items.length) { listEl.innerHTML = '<div class="chat-user-picker__empty">Nenhuma conversa</div>'; return; }
      listEl.innerHTML = items.map((t) => `
        <div class="chat-pick-thread" data-pick-thread="${t.id}">
          ${avatarHtml(t.avatar, 'chat-avatar--sm')}
          <span class="chat-pick-thread__name">${escapeHtml(t.display_name || ('Conversa ' + t.id))}</span>
        </div>`).join('');
      listEl.querySelectorAll('[data-pick-thread]').forEach((el) => {
        el.addEventListener('click', () => doForward(parseInt(el.dataset.pickThread, 10)));
      });
    }
    renderThreadPicks('');
    modal.querySelector('#chat-fwd-filter').addEventListener('input', (e) => renderThreadPicks(e.target.value));

    // Pessoa -> cria/abre DM e encaminha
    createUserPicker({
      inputId: 'chat-fwd-user', resultsId: 'chat-fwd-user-results',
      onPick: async (user) => {
        try {
          const resp = await fetchJSON('/api/chat/threads/dm', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_user_id: user.id }),
          });
          await doForward(resp.thread.id);
        } catch (e) { toast('Erro: ' + e.message, 'error'); }
      },
    });
  }

  // ==========================================================================
  // Share screen modal (corrigido: inclui hash + texto limpo + toast)
  // ==========================================================================
  function openShareModal() {
    // Inclui o HASH: telas que guardam estado no #fragment (filtros/abas) eram
    // compartilhadas sem ele -> recipiente abria estado diferente ("quebrado").
    const relUrl = window.location.pathname + window.location.search + window.location.hash;
    const fullUrl = window.location.origin + relUrl;
    const { modal, close } = buildModal({
      id: 'chat-share-modal',
      title: 'Compartilhar esta tela',
      bodyHtml: `
        <div class="chat-message__deeplink chat-modal__field">
          <i class="fas fa-up-right-from-square chat-message__deeplink-icon"></i>
          <a class="chat-message__deeplink-label" href="${escapeHtml(fullUrl)}" target="_blank"
             rel="noopener noreferrer" title="${escapeHtml(fullUrl)}">${escapeHtml(document.title || 'Esta tela')}</a>
        </div>
        <div class="chat-user-picker chat-modal__field">
          <label>Destinatario (buscar usuario):</label>
          <input id="chat-share-input" type="text" class="form-control" placeholder="Digite nome ou email..." autocomplete="off">
          <div id="chat-share-results" class="chat-user-picker__results"></div>
          <input id="chat-share-dst" type="hidden">
        </div>
        <div class="chat-modal__field">
          <label>Comentario (opcional):</label>
          <textarea id="chat-share-cmt" rows="3" class="form-control" placeholder="Ex: pode conferir esse pedido?"></textarea>
        </div>`,
      footerHtml: `
        <button id="chat-share-cancel" type="button" class="btn btn-secondary">Cancelar</button>
        <button id="chat-share-send" type="button" class="btn btn-primary" disabled>Compartilhar</button>`,
    });
    modal.querySelector('#chat-share-cancel').addEventListener('click', close);

    createUserPicker({
      inputId: 'chat-share-input', resultsId: 'chat-share-results',
      onPick: (user) => {
        modal.querySelector('#chat-share-dst').value = user.id;
        modal.querySelector('#chat-share-send').disabled = false;
      },
    });

    modal.querySelector('#chat-share-send').addEventListener('click', async () => {
      const dstId = parseInt(modal.querySelector('#chat-share-dst').value, 10);
      if (isNaN(dstId) || dstId < 1) { toast('Selecione um usuario da lista.', 'error'); return; }
      const sendBtn = modal.querySelector('#chat-share-send');
      sendBtn.disabled = true;
      try {
        await fetchJSON('/api/chat/share/screen', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            destinatario_user_id: dstId,
            comentario: modal.querySelector('#chat-share-cmt').value.trim(),
            url: relUrl,
            title: document.title,
          }),
        });
        close();
        toast('Tela compartilhada', 'success');
      } catch (e) { toast('Erro: ' + e.message, 'error'); }
      finally { sendBtn.disabled = false; }
    });
    document.getElementById('chat-share-input').focus();
  }

  async function ensureDrawerOpen() {
    await loadDrawer();
    drawerEl.classList.add('open');
    drawerEl.setAttribute('aria-hidden', 'false');
  }

  // ==========================================================================
  // Bootstrap
  // ==========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('chat-toggle');
    if (toggle) toggle.addEventListener('click', openDrawer);

    const shareBtn = document.getElementById('chat-share-screen');
    if (shareBtn) shareBtn.addEventListener('click', openShareModal);

    if (window.ChatClient) {
      window.ChatClient.onEvent((evt, data) => {
        if (!drawerEl || !drawerEl.classList.contains('open')) return;
        if (evt === 'message_new') {
          if (currentThreadId && data.thread_id === currentThreadId) {
            openPanel(currentThreadId, { preserveDraft: true });
          } else {
            const onList = drawerEl.querySelector('#chat-panel-container');
            if (!onList || onList.style.display === 'none') refreshThreads();
          }
        } else if (evt === 'message_edit' || evt === 'message_delete') {
          if (currentThreadId && data.thread_id === currentThreadId) {
            openPanel(currentThreadId, { preserveDraft: true });
          }
        }
      });
    }
  });

  window.ChatUI = {
    open: openDrawer,
    close: closeDrawer,
    refreshThreads,
    openPanel,
    openShareModal,
    openForwardModal,
    openNewDmModal,
    openNewGroupModal,
    openAddMemberModal,
  };
})();

/**
 * ChatClient — SSE + badges + contadores nao-lidos.
 * Task 17 do plano chat-inapp.
 *
 * Conecta em /api/chat/stream (EventSource), escuta eventos do servidor,
 * atualiza badges na navbar e dispara callbacks para a camada de UI
 * (chat_ui.js, Task 18). Graceful degrade: se fetch inicial falhar ou
 * SSE cair, browser reconecta automaticamente com Last-Event-ID.
 *
 * API publica: window.ChatClient {onEvent, counters, markRead}
 */
(function () {
  'use strict';

  const BADGES = {
    system: document.getElementById('chat-badge-system'),
    user: document.getElementById('chat-badge-user'),
  };

  const State = {
    counters: { system: 0, user: 0 },
    es: null,
    listeners: new Set(),
  };

  function updateBadge(kind) {
    const el = BADGES[kind];
    if (!el) return;
    const n = State.counters[kind];
    if (n > 0) {
      el.textContent = n > 99 ? '99+' : String(n);
      el.classList.remove('hidden');
    } else {
      el.textContent = '0';
      el.classList.add('hidden');
    }
  }

  async function fetchInitialCounters() {
    try {
      const resp = await fetch('/api/chat/unread', { credentials: 'same-origin' });
      if (!resp.ok) return;
      const data = await resp.json();
      State.counters.system = data.system || 0;
      State.counters.user = data.user || 0;
      updateBadge('system');
      updateBadge('user');
    } catch (e) {
      console.warn('[chat] fetch unread failed', e);
    }
  }

  function handleEvent(eventType, data) {
    if (eventType === 'message_new') {
      const kind = data.sender_type === 'system' ? 'system' : 'user';
      State.counters[kind] += 1;
      updateBadge(kind);
    } else if (eventType === 'unread_changed') {
      if (typeof data.system === 'number') State.counters.system = data.system;
      if (typeof data.user === 'number') State.counters.user = data.user;
      updateBadge('system');
      updateBadge('user');
    }
    // notifica listeners externos (chat_ui.js)
    State.listeners.forEach((cb) => {
      try { cb(eventType, data); } catch (e) { console.error('[chat] listener error', e); }
    });
  }

  function connect() {
    if (State.es) {
      try { State.es.close(); } catch (e) { /* noop */ }
    }
    const es = new EventSource('/api/chat/stream');
    State.es = es;

    const EVENTS = [
      'message_new',
      'message_edit',
      'message_delete',
      'reaction_add',
      'reaction_remove',
      'unread_changed',
    ];
    EVENTS.forEach((evtType) => {
      es.addEventListener(evtType, (evt) => {
        let data = {};
        try { data = JSON.parse(evt.data); } catch (e) { /* eventos de hello/heartbeat podem vir sem JSON */ }
        handleEvent(evtType, data);
      });
    });

    es.onerror = () => {
      // EventSource reconecta sozinho. Logar so em dev.
      console.debug('[chat] SSE drop — browser reconectara');
    };
  }

  /**
   * Decrementa contador local quando usuario marca thread como lida.
   * `kind` = 'user' | 'system'. `thread_id` opcional — se passado, POSTa /read.
   * Nota: se a thread tinha N nao-lidas, apenas decrementa 1 localmente. Server
   * vai mandar `unread_changed` com numero absoluto na proxima conexao SSE.
   */
  function markRead(kind, thread_id) {
    if (kind in State.counters && State.counters[kind] > 0) {
      State.counters[kind] = Math.max(0, State.counters[kind] - 1);
      updateBadge(kind);
    }
    if (thread_id != null) {
      fetch(`/api/chat/threads/${encodeURIComponent(thread_id)}/read`, {
        method: 'POST',
        credentials: 'same-origin',
      }).catch((e) => console.warn('[chat] markRead failed', e));
    }
  }

  window.ChatClient = {
    /**
     * Registra listener de eventos SSE. Callback recebe (eventType, data).
     * Retorna funcao para desregistrar.
     */
    onEvent(cb) {
      State.listeners.add(cb);
      return () => State.listeners.delete(cb);
    },
    counters() { return { ...State.counters }; },
    markRead,
    /**
     * Reconnect manual (ex: apos login muda user, precisa trocar de canal).
     * Fecha EventSource atual e reabre.
     */
    reconnect() {
      fetchInitialCounters();
      connect();
    },
  };

  document.addEventListener('DOMContentLoaded', () => {
    // So conectar se botao existe (usuario autenticado, navbar renderizada).
    if (!document.getElementById('chat-toggle')) return;
    fetchInitialCounters();
    connect();
  });
})();

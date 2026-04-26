/**
 * ChatClient — polling + badges + contadores nao-lidos.
 *
 * Historia: originalmente SSE (EventSource em /api/chat/stream). Migrado em
 * 2026-04-24 para polling em /api/chat/poll — SSE mantinha 1 slot de worker
 * gunicorn aberto por user permanentemente (C5 auditoria P0). Com polling,
 * slot e liberado entre pulses (~50ms ocupado a cada 4s).
 *
 * Pulse: 12s quando aba focada; 45s quando visivel sem foco; pausado quando
 * document.hidden. Pulse e agendado dentro de requestIdleCallback (timeout 2s)
 * para nao competir com paint/scroll em paginas pesadas (monitoramento etc).
 * Cadencia anterior (4s/15s) gerava percepcao de travamento — relaxado em
 * 2026-04-26.
 *
 * API publica (contrato mantido — chat_ui.js nao muda):
 *   window.ChatClient.onEvent(cb)   -- registra callback (eventType, data)
 *   window.ChatClient.markRead(kind, thread_id)
 *   window.ChatClient.counters()
 *   window.ChatClient.reconnect()   -- forca poll imediato + reinicia timer
 */
(function () {
  'use strict';

  // 2026-04-26: cadencia relaxada + requestIdleCallback (feedback do usuario:
  // pulse anterior de 4s travava UI). Pulse agora roda em janela de idle do
  // browser, nao competindo com paint/scroll.
  const POLL_INTERVAL_FOCUSED_MS = 12000;  // aba com foco: 12s
  const POLL_INTERVAL_VISIBLE_MS = 45000;  // aba visivel sem foco: 45s
  // document.hidden = pausa total.

  // Fallback para browsers sem requestIdleCallback (Safari < 16.4).
  const ric = window.requestIdleCallback
    ? (cb) => window.requestIdleCallback(cb, { timeout: 2000 })
    : (cb) => setTimeout(cb, 0);

  const BADGES = {
    system: document.getElementById('chat-badge-system'),
    user: document.getElementById('chat-badge-user'),
  };

  const State = {
    counters: { system: 0, user: 0 },
    lastId: 0,
    lastTs: null,
    timer: null,
    inFlight: false,
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

  function dispatch(eventType, data) {
    State.listeners.forEach((cb) => {
      try { cb(eventType, data); } catch (e) { console.error('[chat] listener error', e); }
    });
  }

  async function pollOnce() {
    if (State.inFlight) return;
    State.inFlight = true;
    try {
      const params = new URLSearchParams();
      params.set('since_id', String(State.lastId));
      if (State.lastTs) params.set('since_ts', State.lastTs);
      const resp = await fetch('/api/chat/poll?' + params.toString(), {
        credentials: 'same-origin',
      });
      if (!resp.ok) return;
      const data = await resp.json();

      // Avancar cursor ANTES de despachar — se dispatch lanca, proximo poll
      // nao re-entrega os mesmos eventos.
      if (typeof data.last_id === 'number') State.lastId = data.last_id;
      if (data.server_ts) State.lastTs = data.server_ts;

      // Dispatch: mantem contrato dos eventos SSE (chat_ui.js recebe igual).
      (data.new || []).forEach((m) => dispatch('message_new', m));
      (data.edited || []).forEach((m) => dispatch('message_edit', m));
      (data.deleted || []).forEach((m) => dispatch('message_delete', m));

      // Unread ABSOLUTO (server retorna contagem total, nao delta). Nao incrementar.
      if (data.unread) {
        State.counters.system = data.unread.system || 0;
        State.counters.user = data.unread.user || 0;
        updateBadge('system');
        updateBadge('user');
        dispatch('unread_changed', {
          system: State.counters.system, user: State.counters.user,
        });
      }
    } catch (e) {
      // Network flake / logout / 500 — nao poluir console em prod.
      console.debug('[chat] poll error', e);
    } finally {
      State.inFlight = false;
    }
  }

  function scheduleNext() {
    if (State.timer) { clearTimeout(State.timer); State.timer = null; }
    if (document.hidden) return;
    const interval = document.hasFocus() ? POLL_INTERVAL_FOCUSED_MS : POLL_INTERVAL_VISIBLE_MS;
    State.timer = setTimeout(() => {
      // Espera o browser estar ocioso para nao competir com paint/scroll.
      // Timeout 2s em ric: garante que nao trave indefinidamente em paginas
      // CPU-bound (ex.: tabelas grandes do monitoramento).
      ric(async () => {
        await pollOnce();
        scheduleNext();
      });
    }, interval);
  }

  async function restart() {
    // Poll imediato + reagenda. Usado em voltar-do-background e reconnect().
    await pollOnce();
    scheduleNext();
  }

  function markRead(kind, thread_id) {
    // Decrement otimista — proximo poll traz absoluto e sincroniza.
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
    onEvent(cb) {
      State.listeners.add(cb);
      return () => State.listeners.delete(cb);
    },
    counters() { return { ...State.counters }; },
    markRead,
    reconnect() { restart(); },
  };

  // Visibility API — para de pollar em background, retoma ao voltar.
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      if (State.timer) { clearTimeout(State.timer); State.timer = null; }
    } else {
      restart();
    }
  });

  // Foco/blur ajusta cadencia (4s focado, 15s visivel sem foco). Nao pausa.
  window.addEventListener('focus', scheduleNext);
  window.addEventListener('blur', scheduleNext);

  document.addEventListener('DOMContentLoaded', () => {
    // So inicia se navbar do chat foi renderizada (usuario autenticado).
    if (!document.getElementById('chat-toggle')) return;
    restart();
  });
})();

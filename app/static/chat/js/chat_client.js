/**
 * ChatClient — polling + badges + contadores nao-lidos.
 *
 * Historia: originalmente SSE (EventSource em /api/chat/stream). Migrado em
 * 2026-04-24 para polling em /api/chat/poll — SSE mantinha 1 slot de worker
 * gunicorn aberto por user permanentemente (C5 auditoria P0). Cadencia inicial
 * 4s/15s foi relaxada para 12s/45s em 2026-04-26 (feedback de travamento).
 *
 * 2026-05-13: introduzido lazy bootstrap (S1) + adaptive backoff (S2). Adocao
 * real medida: 3 de 74 users (4%). Sem essa mudanca, 96% dos users pollavam
 * a 12s/45s sem nunca trocar mensagem. Reducao esperada ~85% no HTTP do chat.
 *
 *   Bootstrap (S1):
 *     Boot faz 1 GET /api/chat/bootstrap. Se user nao tem threads + zero unread:
 *     entra em modo 'dormant' (heartbeat 5min em foco apenas). Qualquer evento
 *     ou wake() promove pra 'active' (cadencia normal).
 *
 *   Adaptive backoff (S2):
 *     Apos 3 polls vazios consecutivos em modo 'active', dobra o intervalo ate
 *     teto 5min. Reset a 1× ao receber qualquer evento, markRead ou wake().
 *
 * Pulse e agendado dentro de requestIdleCallback (timeout 2s) para nao competir
 * com paint/scroll em paginas pesadas. document.hidden = pausa total.
 *
 * API publica (contrato mantido — chat_ui.js nao muda):
 *   window.ChatClient.onEvent(cb)   -- registra callback (eventType, data)
 *   window.ChatClient.markRead(kind, thread_id)
 *   window.ChatClient.counters()
 *   window.ChatClient.reconnect()   -- forca poll imediato + reinicia timer
 *   window.ChatClient.wake()        -- sai de dormant + reseta backoff
 */
(function () {
  'use strict';

  const POLL_INTERVAL_FOCUSED_MS = 12000;   // active, aba com foco
  const POLL_INTERVAL_VISIBLE_MS = 45000;   // active, aba visivel sem foco
  const HEARTBEAT_DORMANT_MS = 5 * 60 * 1000; // dormant: 5min em foco apenas
  const BACKOFF_CAP_MS = 5 * 60 * 1000;     // teto absoluto em active+backoff
  const BACKOFF_EMPTY_THRESHOLD = 3;        // polls vazios antes de comecar a dobrar
  // document.hidden = pausa total em ambos os modos.

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
    mode: 'init',          // 'init' | 'dormant' | 'active'
    emptyStreak: 0,        // polls consecutivos sem eventos (S2)
    backoffFactor: 1,      // multiplicador de intervalo em active (S2)
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

  function resetBackoff() {
    State.emptyStreak = 0;
    State.backoffFactor = 1;
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

      const newCount = (data.new || []).length;
      const editedCount = (data.edited || []).length;
      const deletedCount = (data.deleted || []).length;
      const hadEvents = newCount > 0 || editedCount > 0 || deletedCount > 0;

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

      // S2: ajusta backoff. Qualquer evento => modo active + reset.
      // Vazio em active => incrementa streak; passou do threshold, dobra factor.
      if (hadEvents) {
        State.mode = 'active';
        resetBackoff();
      } else if (State.mode === 'active') {
        State.emptyStreak++;
        if (State.emptyStreak >= BACKOFF_EMPTY_THRESHOLD) {
          const next = State.backoffFactor * 2;
          // Cap: max factor de modo que base * factor <= BACKOFF_CAP_MS
          const maxFactor = Math.floor(BACKOFF_CAP_MS / POLL_INTERVAL_FOCUSED_MS);
          State.backoffFactor = Math.min(next, maxFactor);
        }
      }
    } catch (e) {
      // Network flake / logout / 500 — nao poluir console em prod.
      console.debug('[chat] poll error', e);
    } finally {
      State.inFlight = false;
    }
  }

  function computeInterval() {
    if (State.mode === 'dormant') {
      // Dormant so polla em foco (heartbeat). Sem foco mas visivel = pausa.
      return document.hasFocus() ? HEARTBEAT_DORMANT_MS : null;
    }
    // active: respeita foco + backoff factor, com cap absoluto.
    const base = document.hasFocus() ? POLL_INTERVAL_FOCUSED_MS : POLL_INTERVAL_VISIBLE_MS;
    return Math.min(base * State.backoffFactor, BACKOFF_CAP_MS);
  }

  function scheduleNext() {
    if (State.timer) { clearTimeout(State.timer); State.timer = null; }
    if (document.hidden) return;
    const interval = computeInterval();
    if (interval == null) return;  // dormant sem foco = nao agendar
    State.timer = setTimeout(() => {
      // requestIdleCallback evita competir com paint/scroll.
      ric(async () => {
        await pollOnce();
        scheduleNext();
      });
    }, interval);
  }

  async function bootstrap() {
    // 1 GET inicial decide o modo. Se falhar, cai pra modo 'active' classico.
    try {
      const resp = await fetch('/api/chat/bootstrap', { credentials: 'same-origin' });
      if (!resp.ok) {
        State.mode = 'active';
        return scheduleNext();
      }
      const data = await resp.json();
      if (typeof data.last_id === 'number') State.lastId = data.last_id;
      if (data.server_ts) State.lastTs = data.server_ts;
      if (data.unread) {
        State.counters.system = data.unread.system || 0;
        State.counters.user = data.unread.user || 0;
        updateBadge('system');
        updateBadge('user');
      }
      const dormantEligible = !data.has_threads
        && State.counters.system === 0
        && State.counters.user === 0;
      State.mode = dormantEligible ? 'dormant' : 'active';
      scheduleNext();
    } catch (e) {
      console.debug('[chat] bootstrap error, falling back to active', e);
      State.mode = 'active';
      scheduleNext();
    }
  }

  async function restart() {
    // Poll imediato + reagenda. Usado em voltar-do-background e reconnect().
    await pollOnce();
    scheduleNext();
  }

  function wake() {
    // Sai de dormant + reset backoff. Chamado em markRead, click no chat-toggle,
    // ou reconnect. Util quando algo no UI sugere que o user voltou a interagir.
    State.mode = 'active';
    resetBackoff();
    restart();
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
    // Qualquer markRead indica engajamento — wake do dormant + reset backoff.
    if (State.mode === 'dormant' || State.backoffFactor > 1) {
      wake();
    }
  }

  window.ChatClient = {
    onEvent(cb) {
      State.listeners.add(cb);
      return () => State.listeners.delete(cb);
    },
    counters() { return { ...State.counters }; },
    markRead,
    reconnect() { wake(); },
    wake,
  };

  // Visibility API — para de pollar em background, retoma ao voltar.
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      if (State.timer) { clearTimeout(State.timer); State.timer = null; }
    } else {
      // Voltar do background reseta backoff (user provavelmente vai interagir).
      resetBackoff();
      restart();
    }
  });

  // Foco/blur reajusta cadencia (active: 12s focado, 45s visivel).
  // Em dormant: foco habilita heartbeat 5min, blur o desliga.
  window.addEventListener('focus', scheduleNext);
  window.addEventListener('blur', scheduleNext);

  document.addEventListener('DOMContentLoaded', () => {
    // So inicia se navbar do chat foi renderizada (usuario autenticado).
    const toggle = document.getElementById('chat-toggle');
    if (!toggle) return;
    // Click no botao do chat = wake (caso esteja dormente, ja ativa polling antes
    // do drawer abrir; quando chat_ui.js carregar mensagens, ja tem state fresh).
    toggle.addEventListener('click', () => {
      if (State.mode === 'dormant' || State.backoffFactor > 1) wake();
    });
    bootstrap();
  });
})();

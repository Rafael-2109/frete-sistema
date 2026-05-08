/**
 * mobile-zoom.js — Mobile Zoom Control
 *
 * Permite ao usuario ajustar o zoom da pagina em mobile via meta viewport
 * dinamico. O navegador renderiza a pagina como se a viewport fosse maior
 * (X%) e a encolhe nativamente para caber na tela fisica, escalando TUDO
 * uniformemente (texto, botoes, tabelas, modais, forms) sem efeitos
 * colaterais de transform: scale (que quebraria position:fixed e Popper).
 *
 * Estado persistido em localStorage por 2 chaves:
 *   - 'mobile-zoom-level': numero entre MIN_LEVEL e MAX_LEVEL
 *   - 'mobile-zoom-bar-visible': 'true' | 'false' (usuario pode esconder a barra)
 *
 * Aplica APENAS em mobile (window.innerWidth < 768px).
 *
 * Para evitar flash de zoom errado, base.html aplica o viewport
 * inline no <head> antes do CSS carregar (early-paint script).
 */
(function() {
  'use strict';

  const STORAGE_KEY_LEVEL = 'mobile-zoom-level';
  const STORAGE_KEY_VISIBLE = 'mobile-zoom-bar-visible';
  const DEFAULT_LEVEL = 100;
  const MIN_LEVEL = 50;
  const MAX_LEVEL = 100;
  const STEP = 10;
  const WARNING_THRESHOLD = 70; // abaixo disso, marcar barra com classe is-warning
  const MOBILE_BREAKPOINT = 768;
  const VIEWPORT_DEFAULT = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover';

  function isMobile() {
    return window.innerWidth < MOBILE_BREAKPOINT;
  }

  // Helpers seguros para localStorage (Safari iOS modo privado pode lancar QuotaExceededError)
  function safeGet(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeSet(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* ignore */ }
  }

  function getLevel() {
    const stored = parseInt(safeGet(STORAGE_KEY_LEVEL), 10);
    if (isNaN(stored)) return DEFAULT_LEVEL;
    return Math.max(MIN_LEVEL, Math.min(MAX_LEVEL, stored));
  }

  function getMetaViewport() {
    return document.querySelector('meta[name=viewport]');
  }

  function applyZoom(level) {
    const meta = getMetaViewport();
    if (!meta) return;

    if (level === DEFAULT_LEVEL || !isMobile()) {
      meta.setAttribute('content', VIEWPORT_DEFAULT);
      return;
    }

    // screen.width retorna a largura fisica do device (estavel, nao muda com pinch zoom)
    // Em portrait/landscape, varia conforme orientacao
    const physicalWidth = window.screen.width || window.innerWidth;
    // Quanto menor o zoom, MAIOR a viewport virtual (mais conteudo cabe)
    // Ex: zoom 80% em iPhone 428pt -> viewport virtual 535pt
    const virtualWidth = Math.round(physicalWidth * (DEFAULT_LEVEL / level));
    meta.setAttribute(
      'content',
      `width=${virtualWidth}, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover`
    );
  }

  function updateUI(level) {
    const bar = document.querySelector('.mobile-zoom-bar');
    if (!bar) return;

    const levelDisplay = bar.querySelector('.zoom-level');
    if (levelDisplay) levelDisplay.textContent = level + '%';

    const btnDec = bar.querySelector('.btn-zoom-dec');
    const btnInc = bar.querySelector('.btn-zoom-inc');
    if (btnDec) btnDec.disabled = level <= MIN_LEVEL;
    if (btnInc) btnInc.disabled = level >= MAX_LEVEL;

    bar.classList.toggle('is-warning', level < WARNING_THRESHOLD);
  }

  function setLevel(level) {
    level = Math.max(MIN_LEVEL, Math.min(MAX_LEVEL, level));
    safeSet(STORAGE_KEY_LEVEL, String(level));
    applyZoom(level);
    updateUI(level);
    return level;
  }

  function showBar() {
    const bar = document.querySelector('.mobile-zoom-bar');
    const toggle = document.querySelector('.mobile-zoom-toggle');
    if (!bar) return;
    bar.classList.add('is-active');
    if (toggle) toggle.classList.remove('is-active');
    document.body.classList.add('has-mobile-zoom-bar');
    safeSet(STORAGE_KEY_VISIBLE, 'true');
  }

  function hideBar() {
    const bar = document.querySelector('.mobile-zoom-bar');
    const toggle = document.querySelector('.mobile-zoom-toggle');
    if (!bar) return;
    bar.classList.remove('is-active');
    if (toggle) toggle.classList.add('is-active');
    document.body.classList.remove('has-mobile-zoom-bar');
    safeSet(STORAGE_KEY_VISIBLE, 'false');
  }

  function init() {
    const bar = document.querySelector('.mobile-zoom-bar');
    if (!bar) return;

    // Aplica zoom salvo (mesmo se nao for mobile, garante reset para default)
    const level = getLevel();
    applyZoom(level);
    updateUI(level);

    // Em mobile, mostra barra (a menos que usuario tenha escondido)
    if (isMobile()) {
      const barVisible = safeGet(STORAGE_KEY_VISIBLE) !== 'false';
      if (barVisible) {
        showBar();
      } else {
        const toggle = document.querySelector('.mobile-zoom-toggle');
        if (toggle) toggle.classList.add('is-active');
      }
    }

    // Bind eventos (idempotente — botoes existem sempre, mesmo escondidos por CSS)
    const btnDec = bar.querySelector('.btn-zoom-dec');
    const btnInc = bar.querySelector('.btn-zoom-inc');
    const btnReset = bar.querySelector('.btn-zoom-reset');
    const btnHide = bar.querySelector('.btn-zoom-hide');
    const toggle = document.querySelector('.mobile-zoom-toggle');

    if (btnDec) btnDec.addEventListener('click', () => setLevel(getLevel() - STEP));
    if (btnInc) btnInc.addEventListener('click', () => setLevel(getLevel() + STEP));
    if (btnReset) btnReset.addEventListener('click', () => setLevel(DEFAULT_LEVEL));
    if (btnHide) btnHide.addEventListener('click', hideBar);
    if (toggle) toggle.addEventListener('click', showBar);

    // Reaplicar zoom em rotacao/resize (mobile <-> desktop)
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (!isMobile()) {
          // Desktop: reset viewport e ocultar UI (CSS ja faz, mas garante estado JS)
          const meta = getMetaViewport();
          if (meta) meta.setAttribute('content', VIEWPORT_DEFAULT);
          document.body.classList.remove('has-mobile-zoom-bar');
        } else {
          applyZoom(getLevel());
          // Restaura visibilidade da barra conforme preferencia
          const barVisible = safeGet(STORAGE_KEY_VISIBLE) !== 'false';
          if (barVisible && !bar.classList.contains('is-active')) {
            showBar();
          }
        }
      }, 150);
    });
  }

  // Init quando DOM pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

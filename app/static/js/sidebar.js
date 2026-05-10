/**
 * sidebar.js — Nacom Goya Sidebar Manager
 *
 * Responsabilidades:
 *  - Toggle expand/collapse da sidebar (desktop)
 *  - Mobile drawer com backdrop (off-canvas)
 *  - Persistencia do estado em localStorage (`nc-sidebar-state`)
 *  - Auto-detect viewport e ajustar estado inicial
 *  - Submenu accordion inline (modo expandido)
 *  - Flyout on hover (modo colapsado, item com submenu)
 *  - Highlight do menu ativo via path matching
 *  - Atalho de teclado Ctrl+B / Cmd+B
 */
(function () {
    'use strict';

    const SIDEBAR_KEY = 'nc-sidebar-state';
    const BREAKPOINT_DRAWER = 992;
    const BREAKPOINT_COLLAPSE = 1280;

    const shell = document.getElementById('nc-shell');
    if (!shell) return;

    const sidebar = shell.querySelector('.nc-sidebar');
    const toggleBtn = document.getElementById('nc-sidebar-toggle');
    const hamburger = document.getElementById('nc-topbar-hamburger');
    const overlay = document.querySelector('.nc-drawer-overlay');

    /* ──────────────────────────────────────────────────────────────────
       STATE MANAGEMENT
       ────────────────────────────────────────────────────────────────── */

    function setSidebarState(state, persist = true) {
        // Aceita: expanded | collapsed | drawer
        shell.dataset.sidebar = state;
        if (persist && state !== 'drawer') {
            try {
                localStorage.setItem(SIDEBAR_KEY, state);
            } catch (_) { /* localStorage indisponivel: fail-silent */ }
        }
        // Atualiza icone do toggle
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.className = state === 'collapsed'
                    ? 'fas fa-angles-right'
                    : 'fas fa-angles-left';
            }
        }
        // Limpa flyout ativo ao mudar estado
        clearFlyout(true);
    }

    function getStoredState() {
        try {
            const v = localStorage.getItem(SIDEBAR_KEY);
            return (v === 'expanded' || v === 'collapsed') ? v : null;
        } catch (_) { return null; }
    }

    function applyResponsiveState() {
        const w = window.innerWidth;
        if (w < BREAKPOINT_DRAWER) {
            setSidebarState('drawer', false);
        } else if (w < BREAKPOINT_COLLAPSE) {
            // Telas medias: forca colapsada (independente do storage)
            setSidebarState('collapsed', false);
        } else {
            // Desktop wide: respeita storage, default = expanded
            const stored = getStoredState();
            setSidebarState(stored || 'expanded', false);
        }
    }

    /* ──────────────────────────────────────────────────────────────────
       DRAWER (mobile)
       ────────────────────────────────────────────────────────────────── */

    function openDrawer() {
        shell.dataset.drawerOpen = 'true';
        document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
        shell.dataset.drawerOpen = 'false';
        document.body.style.overflow = '';
    }

    /* ──────────────────────────────────────────────────────────────────
       SUBMENU (accordion inline — modo expandido)
       ────────────────────────────────────────────────────────────────── */

    function syncSubmenuAria(item) {
        const trigger = item.querySelector(':scope > [data-toggle="submenu"]');
        if (trigger) {
            trigger.setAttribute('aria-expanded',
                item.classList.contains('nc-sidebar__item--open') ? 'true' : 'false');
        }
    }

    function bindSubmenus() {
        document.querySelectorAll('[data-toggle="submenu"]').forEach(link => {
            // Inicializa aria-expanded
            link.setAttribute('aria-expanded',
                link.closest('.nc-sidebar__item')?.classList.contains('nc-sidebar__item--open')
                    ? 'true' : 'false');
            // Adiciona aria-haspopup para indicar submenu disponivel
            link.setAttribute('aria-haspopup', 'true');

            link.addEventListener('click', (e) => {
                e.preventDefault();
                const item = link.closest('.nc-sidebar__item');
                if (!item) return;
                // No estado colapsado, click em link com submenu nao expande
                // inline (flyout cuida via hover)
                if (shell.dataset.sidebar === 'collapsed') return;
                item.classList.toggle('nc-sidebar__item--open');
                syncSubmenuAria(item);
            });
        });
    }

    /* ──────────────────────────────────────────────────────────────────
       FLYOUT (modo colapsado — hover em item com submenu)
       ────────────────────────────────────────────────────────────────── */

    let flyoutHideTimer = null;
    let activeFlyout = null;
    let activeFlyoutItem = null;

    function buildFlyout(item) {
        const link = item.querySelector('.nc-sidebar__link');
        const submenu = item.querySelector('.nc-sidebar__submenu');
        if (!link || !submenu) return null;

        const label = link.dataset.tooltip
            || link.querySelector('.nc-sidebar__label')?.textContent
            || '';
        const iconEl = link.querySelector('.nc-sidebar__icon');
        const iconClass = iconEl ? iconEl.className.replace('nc-sidebar__icon', '').trim() : '';

        const flyout = document.createElement('div');
        flyout.className = 'nc-sidebar__flyout';
        flyout.setAttribute('role', 'menu');

        // Header
        const header = document.createElement('div');
        header.className = 'nc-sidebar__flyout-header';
        if (iconClass) {
            const i = document.createElement('i');
            i.className = iconClass;
            i.setAttribute('aria-hidden', 'true');
            header.appendChild(i);
        }
        const headerSpan = document.createElement('span');
        headerSpan.textContent = label;
        header.appendChild(headerSpan);
        flyout.appendChild(header);

        // Lista (clona itens do submenu).
        // cloneNode(true) preserva atributos (incluindo nc-sidebar__link--active
        // se ja foi marcado). Re-aplicamos highlight aqui caso o JS nao tenha
        // populado ainda (paginas pre-rendered) ou para itens cuja active flag
        // nao foi propagada.
        const currentPath = window.location.pathname;
        const list = document.createElement('ul');
        list.className = 'nc-sidebar__flyout-list';
        submenu.querySelectorAll(':scope > li').forEach(li => {
            const cloned = li.cloneNode(true);
            // Re-aplica highlight ativo no clone (cloneNode nao roda bindings)
            cloned.querySelectorAll('.nc-sidebar__link').forEach(clonedLink => {
                const href = clonedLink.getAttribute('href');
                if (href && href !== '#' && !href.startsWith('javascript:')) {
                    if (currentPath === href || (href !== '/' && currentPath.startsWith(href))) {
                        clonedLink.classList.add('nc-sidebar__link--active');
                    }
                }
                clonedLink.setAttribute('role', 'menuitem');
            });
            list.appendChild(cloned);
        });
        flyout.appendChild(list);

        return flyout;
    }

    function positionFlyout(flyout, item) {
        const rect = item.getBoundingClientRect();
        flyout.style.top = rect.top + 'px';
        flyout.style.left = (rect.right + 10) + 'px';

        requestAnimationFrame(() => {
            const fRect = flyout.getBoundingClientRect();
            const margin = 8;
            // Ajusta vertical se passar do bottom
            if (fRect.bottom > window.innerHeight - margin) {
                const newTop = Math.max(margin, window.innerHeight - fRect.height - margin);
                flyout.style.top = newTop + 'px';
            }
            // Ajusta horizontal (caso raro: viewport muito estreita)
            if (fRect.right > window.innerWidth - margin) {
                flyout.style.left = (rect.left - fRect.width - 10) + 'px';
            }
            flyout.classList.add('nc-sidebar__flyout--show');
        });
    }

    function clearFlyout(immediate = false) {
        clearTimeout(flyoutHideTimer);
        const fly = activeFlyout;
        if (!fly) return;
        if (immediate) {
            fly.remove();
        } else {
            fly.classList.remove('nc-sidebar__flyout--show');
            setTimeout(() => {
                if (fly.parentNode) fly.remove();
            }, 150);
        }
        activeFlyout = null;
        activeFlyoutItem = null;
    }

    function showFlyout(item) {
        if (shell.dataset.sidebar !== 'collapsed') return;
        if (activeFlyoutItem === item) {
            clearTimeout(flyoutHideTimer);
            return;
        }
        if (activeFlyout) clearFlyout(true);

        const flyout = buildFlyout(item);
        if (!flyout) return; // item sem submenu: tooltip CSS cuida

        document.body.appendChild(flyout);
        activeFlyout = flyout;
        activeFlyoutItem = item;
        positionFlyout(flyout, item);

        flyout.addEventListener('mouseenter', () => clearTimeout(flyoutHideTimer));
        flyout.addEventListener('mouseleave', scheduleFlyoutHide);
    }

    function scheduleFlyoutHide() {
        clearTimeout(flyoutHideTimer);
        flyoutHideTimer = setTimeout(() => clearFlyout(false), 180);
    }

    function bindFlyoutEvents() {
        document.querySelectorAll('.nc-sidebar__item').forEach(item => {
            item.addEventListener('mouseenter', () => {
                if (shell.dataset.sidebar !== 'collapsed') return;
                clearTimeout(flyoutHideTimer);
                showFlyout(item);
            });
            item.addEventListener('mouseleave', () => {
                if (shell.dataset.sidebar !== 'collapsed') return;
                scheduleFlyoutHide();
            });
        });

        // Click fora fecha o flyout
        document.addEventListener('click', (e) => {
            if (!activeFlyout) return;
            if (activeFlyout.contains(e.target)) return;
            if (activeFlyoutItem && activeFlyoutItem.contains(e.target)) return;
            clearFlyout(false);
        });
    }

    /* ──────────────────────────────────────────────────────────────────
       ACTIVE LINK (highlight baseado em request.path)
       ────────────────────────────────────────────────────────────────── */

    function highlightActiveLink() {
        const currentPath = window.location.pathname;
        let bestMatch = null;
        let bestLength = 0;

        document.querySelectorAll('.nc-sidebar__link').forEach(link => {
            const href = link.getAttribute('href');
            if (!href || href === '#' || href.startsWith('javascript:')) return;
            // Match por prefixo: o link mais especifico vence
            if (currentPath === href || (href !== '/' && currentPath.startsWith(href))) {
                if (href.length > bestLength) {
                    bestMatch = link;
                    bestLength = href.length;
                }
            }
        });

        if (bestMatch) {
            bestMatch.classList.add('nc-sidebar__link--active');
            // Abre submenus pai automaticamente + sync ARIA
            let parentItem = bestMatch.closest('.nc-sidebar__item');
            while (parentItem) {
                parentItem.classList.add('nc-sidebar__item--open');
                syncSubmenuAria(parentItem);
                parentItem = parentItem.parentElement?.closest('.nc-sidebar__item');
            }
        }
    }

    /* Limpa classes pre-init aplicadas no <html> pelo inline script no head.
       A partir daqui, o controle do estado fica com data-sidebar no .nc-shell. */
    function clearInitClasses() {
        document.documentElement.classList.remove(
            'nc-sidebar-init-expanded',
            'nc-sidebar-init-collapsed',
            'nc-sidebar-init-drawer'
        );
    }

    /* ──────────────────────────────────────────────────────────────────
       EVENT BINDINGS
       ────────────────────────────────────────────────────────────────── */

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const cur = shell.dataset.sidebar;
            setSidebarState(cur === 'expanded' ? 'collapsed' : 'expanded');
        });
    }

    if (hamburger) {
        hamburger.addEventListener('click', () => {
            if (window.innerWidth < BREAKPOINT_DRAWER) {
                if (shell.dataset.drawerOpen === 'true') {
                    closeDrawer();
                } else {
                    openDrawer();
                }
            } else {
                const cur = shell.dataset.sidebar;
                setSidebarState(cur === 'expanded' ? 'collapsed' : 'expanded');
            }
        });
    }

    if (overlay) {
        overlay.addEventListener('click', closeDrawer);
    }

    // Atalho Ctrl+B / Cmd+B
    document.addEventListener('keydown', (e) => {
        const isToggle = (e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B');
        if (isToggle) {
            // Ignora se foco em input/textarea (usuario pode estar editando)
            const tag = (e.target.tagName || '').toLowerCase();
            if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
            e.preventDefault();
            if (window.innerWidth < BREAKPOINT_DRAWER) {
                shell.dataset.drawerOpen === 'true' ? closeDrawer() : openDrawer();
            } else {
                const cur = shell.dataset.sidebar;
                setSidebarState(cur === 'expanded' ? 'collapsed' : 'expanded');
            }
        }
        // ESC fecha drawer
        if (e.key === 'Escape' && shell.dataset.drawerOpen === 'true') {
            closeDrawer();
        }
    });

    // Resize listener (debounced)
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            applyResponsiveState();
            if (window.innerWidth >= BREAKPOINT_DRAWER) closeDrawer();
        }, 120);
    });

    /* ──────────────────────────────────────────────────────────────────
       INIT
       ────────────────────────────────────────────────────────────────── */

    bindSubmenus();
    bindFlyoutEvents();
    highlightActiveLink();
    applyResponsiveState();
    clearInitClasses();

})();

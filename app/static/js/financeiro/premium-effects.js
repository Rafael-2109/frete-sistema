/**
 * Sistema Financeiro - Premium Visual Effects (LIMPO)
 * ====================================================
 * Apenas efeitos REALMENTE usados: ~80 linhas
 * Efeitos: Scroll Reveal, Stagger, Spotlight
 */

const PremiumEffects = {
    init() {
        // Verificar preferência de reduced motion
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            console.log('PremiumEffects: Reduced motion - disabled');
            return;
        }

        this.initScrollReveal();
        this.initStaggeredChildren();
        this.initSpotlight();

        console.log('PremiumEffects: Initialized');
    },

    // Scroll Reveal - para elementos com classe .reveal
    initScrollReveal() {
        const elements = document.querySelectorAll('.reveal');
        if (!elements.length) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        elements.forEach(el => observer.observe(el));
    },

    // Stagger Children - para containers com classe .stagger-children
    initStaggeredChildren() {
        const containers = document.querySelectorAll('.stagger-children');
        if (!containers.length) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        }, {
            threshold: 0.1
        });

        containers.forEach(container => observer.observe(container));
    },

    // Spotlight - efeito de luz seguindo o mouse
    initSpotlight() {
        const elements = document.querySelectorAll('.spotlight');
        if (!elements.length) return;

        elements.forEach(el => {
            el.addEventListener('mousemove', (e) => {
                const rect = el.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                el.style.setProperty('--spotlight-x', `${x}px`);
                el.style.setProperty('--spotlight-y', `${y}px`);
            });
        });
    }
};

// Inicialização
document.addEventListener('DOMContentLoaded', () => PremiumEffects.init());

// Expor globalmente
window.PremiumEffects = PremiumEffects;

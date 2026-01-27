# Requirements: Padronizacao de Estilos

**Defined:** 2026-01-26
**Core Value:** Todas as telas devem ter cores e contraste funcionais em dark mode E mobile, sem CSS inline hardcoded.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: Sistema de CSS Variables implementado (cores, espacamento, tipografia)
- [x] **FOUND-02**: Dark mode e light mode funcionais em todas as telas padronizadas
- [x] **FOUND-03**: CSS Cascade Layers (@layer) implementado para controle de especificidade
- [x] **FOUND-04**: Bootstrap padronizado na versao 5.3.3 em todos os templates

### Components

- [x] **COMP-01**: Botoes com contraste correto em qualquer tema (dark/light)
- [x] **COMP-02**: Cards com bordas e sombras consistentes usando tokens
- [x] **COMP-03**: Badges com texto legivel (sem branco em fundo claro, sem preto em fundo escuro)
- [x] **COMP-04**: Modais seguindo padrao de cores do tema
- [x] **COMP-05**: Forms com estados de foco visiveis e cores corretas

### Tables

- [x] **TABL-01**: Scroll horizontal funcional no mobile (tabelas rolaveis)
- [x] **TABL-02**: Headers fixos (sticky) em tabelas longas
- [x] **TABL-03**: Hover states visiveis e adaptativos ao tema

### Layout

- [x] **LAYO-01**: Responsividade mobile sem cortes de botoes e conteudo
- [x] **LAYO-02**: Sidebar adaptativa ao tamanho de tela (reinterpreted: navbar mobile responsiveness with 44x44px touch targets)
- [x] **LAYO-03**: Grid system consistente em todas as telas (with overflow protection utilities)

### Migration

- [ ] **MIGR-01**: Remover cores hardcoded (#hex) dos 30+ templates prioritarios
- [ ] **MIGR-02**: Extrair estilos inline de 106 templates para arquivos CSS
- [ ] **MIGR-03**: Eliminar !important desnecessarios (591 existentes)
- [ ] **MIGR-04**: Telas com layout custom (carteira, lista_pedidos) usam tokens para cores

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Tables

- **TABL-04**: Transformacao card-based de tabelas no mobile (alta complexidade)
- **TABL-05**: Virtualizacao para tabelas com muitos registros

### Polish

- **POLI-01**: Estados de loading (skeleton screens)
- **POLI-02**: Empty states consistentes
- **POLI-03**: Toasts padronizados
- **POLI-04**: Keyboard shortcuts para navegacao

### Advanced Theming

- **THEM-01**: Modo de alta densidade (compact view)
- **THEM-02**: Preferencias de usuario persistentes
- **THEM-03**: OKLCH color space para tokens

## Out of Scope

| Feature | Reason |
|---------|--------|
| Redesign de layout | Apenas cores e responsividade, nao mudanca de estrutura |
| Telas de impressao | Mantem estilos proprios para impressao |
| Telas de portal externo | Podem ter branding diferente |
| Build tools (Sass/PostCSS) | Projeto requer CSS puro |
| Tailwind CSS | Incompativel com Bootstrap existente |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| COMP-01 | Phase 2 | Complete |
| COMP-02 | Phase 2 | Complete |
| COMP-03 | Phase 2 | Complete |
| COMP-04 | Phase 2 | Complete |
| COMP-05 | Phase 2 | Complete |
| TABL-01 | Phase 3 | Complete |
| TABL-02 | Phase 3 | Complete |
| TABL-03 | Phase 3 | Complete |
| LAYO-01 | Phase 3 | Complete |
| LAYO-02 | Phase 4 | Complete |
| LAYO-03 | Phase 4 | Complete |
| MIGR-01 | Phase 5, 6, 7 | Pending |
| MIGR-02 | Phase 5, 6, 7 | Pending |
| MIGR-03 | Phase 7 | Pending |
| MIGR-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-01-26*
*Last updated: 2026-01-27 after Phase 4 completion*

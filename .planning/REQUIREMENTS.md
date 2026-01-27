# Requirements: Padronizacao de Estilos

**Defined:** 2026-01-26
**Core Value:** Todas as telas devem ter cores e contraste funcionais em dark mode E mobile, sem CSS inline hardcoded.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [ ] **FOUND-01**: Sistema de CSS Variables implementado (cores, espacamento, tipografia)
- [ ] **FOUND-02**: Dark mode e light mode funcionais em todas as telas padronizadas
- [ ] **FOUND-03**: CSS Cascade Layers (@layer) implementado para controle de especificidade
- [ ] **FOUND-04**: Bootstrap padronizado na versao 5.3.3 em todos os templates

### Components

- [ ] **COMP-01**: Botoes com contraste correto em qualquer tema (dark/light)
- [ ] **COMP-02**: Cards com bordas e sombras consistentes usando tokens
- [ ] **COMP-03**: Badges com texto legivel (sem branco em fundo claro, sem preto em fundo escuro)
- [ ] **COMP-04**: Modais seguindo padrao de cores do tema
- [ ] **COMP-05**: Forms com estados de foco visiveis e cores corretas

### Tables

- [ ] **TABL-01**: Scroll horizontal funcional no mobile (tabelas rolaveis)
- [ ] **TABL-02**: Headers fixos (sticky) em tabelas longas
- [ ] **TABL-03**: Hover states visiveis e adaptativos ao tema

### Layout

- [ ] **LAYO-01**: Responsividade mobile sem cortes de botoes e conteudo
- [ ] **LAYO-02**: Sidebar adaptativa ao tamanho de tela
- [ ] **LAYO-03**: Grid system consistente em todas as telas

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
| FOUND-01 | TBD | Pending |
| FOUND-02 | TBD | Pending |
| FOUND-03 | TBD | Pending |
| FOUND-04 | TBD | Pending |
| COMP-01 | TBD | Pending |
| COMP-02 | TBD | Pending |
| COMP-03 | TBD | Pending |
| COMP-04 | TBD | Pending |
| COMP-05 | TBD | Pending |
| TABL-01 | TBD | Pending |
| TABL-02 | TBD | Pending |
| TABL-03 | TBD | Pending |
| LAYO-01 | TBD | Pending |
| LAYO-02 | TBD | Pending |
| LAYO-03 | TBD | Pending |
| MIGR-01 | TBD | Pending |
| MIGR-02 | TBD | Pending |
| MIGR-03 | TBD | Pending |
| MIGR-04 | TBD | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 0
- Unmapped: 19

---
*Requirements defined: 2026-01-26*
*Last updated: 2026-01-26 after initial definition*

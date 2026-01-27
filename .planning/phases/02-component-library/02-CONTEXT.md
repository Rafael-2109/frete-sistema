# Phase 2: Component Library - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Extrair padrões CSS reutilizáveis dos estilos inline existentes para uma biblioteca de componentes centralizada. Componentes devem funcionar corretamente em dark mode E light mode, seguindo o sistema de elevação visual definido.

</domain>

<decisions>
## Implementation Decisions

### Sistema de Elevação Visual (CRÍTICO)
- **3 níveis de profundidade**: Background → Surface → Elevated
  - Background: Fundo da página (mais escuro em dark, cinza claro ~#f5f5f5 em light)
  - Surface: Cards, containers (tom intermediário)
  - Elevated: Modais, dropdowns, tooltips (mais claro, "mais próximo do usuário")
- **Princípio**: Componentes "mais próximos do usuário" são mais claros
- **Dark mode**: Fundo preto ou muito próximo do preto, clareando em cada nível
- **Light mode**: Fundo cinza claro (~#f5f5f5), clareando até branco em elevated
- **Bordas**: Sutis (1px em tom intermediário) para reforçar separação entre camadas
- **Sombras**: Apenas no nível elevated (modais, dropdowns) — sutil

### Botões
- **Variantes**: Padrão Bootstrap completo (primary, secondary, success, danger, warning, info, light, dark)
- **Tamanhos**: 3 tamanhos (sm, md/default, lg)
- **Estados**: Completo (hover, active, focus, disabled) — todos estilizados
- **Ícones**: Claude decide baseado em padrões existentes no sistema

### Cards
- **Estrutura interna**: Claude decide baseado em uso atual nos templates
- **Variantes semânticas**: card-success, card-warning, card-danger para indicar estado
- **Hover**: Sim, efeito sutil (leve mudança de sombra/borda ao passar mouse)
- **Imagens**: Não precisa — sistema de frete não usa cards com imagens

### Badges
- **Cores**: Semânticas fixas (success=verde, warning=amarelo, danger=vermelho, info=azul)
- **Estilos**: Filled + Outlined (badge-success e badge-outline-success)
- **Tamanho**: Único (simplificado)
- **Temas**: Ajuste automático de luminosidade por tema para manter legibilidade (WCAG contrast)

### Modais
- **Tamanhos**: 3 tamanhos (sm, md/default, lg) — padrão Bootstrap
- **Cores**: Seguem sistema de elevação (nível "elevated")

### Forms
- **Estados de input**: Completo (default, focus, error, success, disabled)
- **Labels obrigatórios**: Asterisco vermelho (*) após label de campos required
- **Espaçamento**: Padronizado via tokens

### Claude's Discretion
- Implementação de ícones em botões (analisar padrões existentes)
- Estrutura interna de cards (card-header, card-body, card-footer) baseada em uso atual
- Valores exatos de cores para cada nível de elevação (seguindo melhores práticas)
- Algoritmo de ajuste de luminosidade para badges por tema

</decisions>

<specifics>
## Specific Ideas

- Sistema de elevação inspirado em Material Design "dark theme" — componentes elevados são mais claros
- Dark mode com fundo preto ou muito próximo (não cinza escuro)
- Light mode com fundo cinza claro (~#f5f5f5), não branco puro — mais confortável para os olhos
- Bordas sutis sempre presentes para separar camadas visualmente
- Sombras apenas para elementos elevated (modais, dropdowns) — minimalista

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-component-library*
*Context gathered: 2026-01-27*

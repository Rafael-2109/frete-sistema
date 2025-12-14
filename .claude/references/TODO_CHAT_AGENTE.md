# TODO - Redesign Chat Agente Web

**Criado**: 14/12/2025
**Status**: Em andamento
**Objetivo**: Adequar chat do agente ao design system frontend-design

---

## Sprint 1 - Correcoes Criticas (CONCLUIDO ✅)

- [x] **P1.1** Corrigir elementos DOM inexistentes no HTML
  - Adicionado `token-percentage`, `token-input`, `token-output`, `token-progress-bar`
  - Container completo: `token-budget-container` com stats e barra de progresso
  - Nota: `thinking-label-text` e `plan-mode-label-text` tem null-check no JS

- [x] **P1.2** Restaurar controles no mobile
  - Override CSS para `.chat-header-center` visivel em tablet (768px)
  - Toggles de thinking/plan mode acessiveis em mobile (480px)
  - Botao anexar visivel: `.btn-attach { display: flex !important }`
  - Compactacao automatica dos elementos em telas pequenas

- [x] **P2.6** Implementar `prefers-reduced-motion` (feito no Sprint 2)

- [x] **P3.1** Persistir preferencias no localStorage
  - Modelo selecionado: `agent-model`
  - Thinking toggle: `agent-thinking`
  - Plan mode toggle: `agent-plan-mode`
  - Tema (dark/light): `agent-theme` (feito no Sprint 2)

---

## Sprint 2 - Design System (CONCLUIDO ✅)

### Fase 2.1 - Estrutura CSS Variables
- [x] Definir paleta de cores (NÃO GitHub) - **Deep Ocean** 🌊
- [x] Criar arquivo `app/static/agente/css/agent-theme.css` (900+ linhas)
- [x] Definir CSS Variables com prefix `--agent-*`
- [x] Implementar Dark Mode (default)
- [x] Implementar Light Mode

### Fase 2.2 - Integração
- [x] Importar `agent-theme.css` no `chat.html`
- [x] Migrar cores hardcoded do `chat.css` para variables (via CSS overrides)
- [x] Adicionar toggle de tema no header
- [x] Sincronizar com `data-theme` e localStorage
- [x] Compatibilidade com `data-bs-theme` (Bootstrap)

### Fase 2.3 - Visual Moments
- [x] Atmospheric background (gradient animado com 2 layers)
- [x] Entry animations com blur (`agent-fadeInUp`, `agent-slideInLeft`, `agent-slideInRight`)
- [x] Progressive glow line em mensagens e cards
- [x] Multi-layer shadow em hover (com glow effect)

### Fase 2.4 - Typography
- [x] Headers com `font-weight: 700` e `letter-spacing: -0.02em`
- [x] Valores grandes em monospace (JetBrains Mono)
- [x] Labels em small caps (uppercase + letter-spacing)
- [x] Fonts: Inter (sans) + JetBrains Mono

### Fase 2.5 - Acessibilidade
- [x] `prefers-reduced-motion` respeitado
- [x] `prefers-contrast: high` respeitado
- [x] Focus states visiveis (outline com accent color)
- [x] Print styles implementados

---

## Sprint 3 - Funcionalidades (PENDENTE)

- [ ] **P3.2** Atalhos de teclado
  - `Cmd/Ctrl+K` - Buscar
  - `Cmd/Ctrl+N` - Nova sessao
  - `Esc` - Fechar modais

- [ ] **P3.3** Autocomplete de comandos (`/`)

- [ ] **P3.4** Indicador visual de conexao (heartbeat)

- [ ] **P3.5** Busca em sessoes anteriores

- [ ] **P3.6** Drag & drop para arquivos

---

## Sprint 4 - Nice to Have (FUTURO)

- [ ] Preview de imagens anexadas
- [ ] Exportar conversa (Markdown/PDF)
- [ ] Notificacoes sonoras
- [ ] Favoritar mensagens
- [ ] Voice input (Web Speech API)

---

## Decisoes Tomadas

| Data | Decisao | Justificativa |
|------|---------|---------------|
| 14/12/2025 | Criar `agent-theme.css` separado | Arquivo `chat.css` já tem 1632 linhas |
| 14/12/2025 | Usar prefix `agent-*` | Identidade propria, nao depende de `fin-*` |
| 14/12/2025 | Comecar pelo Sprint 2 | Design System é base para tudo |
| 14/12/2025 | Paleta **Deep Ocean** 🌊 | Teal/Cyan profissional, similar ao Claude.ai |

---

## Arquivos Modificados

| Arquivo | Linhas | Status | Acao |
|---------|--------|--------|------|
| `app/static/agente/css/chat.css` | 1632 | Mantido | Overrides via agent-theme.css |
| `app/static/agente/css/agent-theme.css` | **~1080** | ✅ CRIADO | CSS Variables + Dark/Light + Visual Moments + Mobile Fixes |
| `app/static/agente/js/chat.js` | 1742 | Mantido | Variaveis globais atualizadas via JS inline |
| `app/agente/templates/agente/chat.html` | **~478** | ✅ EDITADO | Import CSS + Toggle tema + Token Budget + Preferences |

---

## Paleta de Cores Escolhida

> **DEFINIDA**: Deep Ocean 🌊 (14/12/2025)

### Dark Mode (Default)
| Elemento | Cor | Uso |
|----------|-----|-----|
| Background Primary | `#0a1628` | Fundo principal |
| Background Secondary | `#111d2e` | Cards, paineis |
| Background Tertiary | `#1a2942` | Hover, destaques |
| Text Primary | `#f0f6fc` | Texto principal |
| Text Secondary | `#8b949e` | Texto secundario |
| Text Muted | `#6e7681` | Hints, placeholders |
| Accent Primary | `#00d4aa` | Botoes, links, IA avatar |
| Accent Secondary | `#0ea5e9` | User messages, destaques |
| Success | `#10b981` | Confirmacoes |
| Warning | `#f59e0b` | Alertas |
| Danger | `#ef4444` | Erros |
| Border | `rgba(240, 246, 252, 0.1)` | Bordas sutis |

### Light Mode
| Elemento | Cor | Uso |
|----------|-----|-----|
| Background Primary | `#f4f7fa` | Fundo principal |
| Background Secondary | `#ffffff` | Cards, paineis |
| Background Tertiary | `#e8eef4` | Hover, destaques |
| Text Primary | `#1f2328` | Texto principal |
| Text Secondary | `#57606a` | Texto secundario |
| Text Muted | `#8b949e` | Hints, placeholders |
| Accent Primary | `#00a88a` | Botoes, links (darkened) |
| Accent Secondary | `#0284c7` | User messages (darkened) |

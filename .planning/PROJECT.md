# Padronizacao de Estilos do Sistema

## What This Is

Sistema de padronizacao visual para o sistema de gestao de frete da Nacom Goya. O objetivo e unificar cores, brilho e responsividade mobile em todas as telas que nao possuem layout custom especifico, utilizando os design-tokens HSL ja existentes.

## Core Value

**Todas as telas devem ter cores e contraste funcionais em dark mode E mobile, sem CSS inline hardcoded.**

Se apenas uma coisa funcionar, deve ser: textos legiveis (contraste correto) em qualquer tema e telas usaveis no celular.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] REQ-01: Todas as cores devem vir de variaveis CSS (design-tokens), nunca hardcoded
- [ ] REQ-02: Dark mode deve funcionar em todas as telas padronizadas
- [ ] REQ-03: Tabelas devem ter scroll horizontal funcional no mobile
- [ ] REQ-04: Botoes de acao devem ser acessiveis no mobile (nao cortados)
- [ ] REQ-05: Badges devem ter contraste correto em qualquer tema
- [ ] REQ-06: Modais devem seguir padrao de cores do tema
- [ ] REQ-07: Telas com layout custom (carteira, lista_pedidos, manufatura) mantem formato mas usam cores padrao

### Out of Scope

- Redesign de layout — Apenas cores e responsividade, nao mudanca de estrutura
- Telas de impressao — Mantem estilos proprios para impressao
- Telas de portal externo — Podem ter branding diferente
- Performance de CSS — Foco em consistencia, nao otimizacao de bundle

## Context

### Estado Atual

O sistema possui:
- **102 templates** com tags `<style>` inline
- **30+ templates** com cores hexadecimais hardcoded
- Design-tokens bem estruturados em `_design-tokens.css` (hierarquia HSL 0%->5%->10%->15%)
- Bootstrap-overrides com workarounds para estilos inline

### Problema Principal

Telas como `/pallet/v2/controle/solucoes` tem 628 linhas de CSS inline com:
- ~40 cores hardcoded (#f8f9fa, #212529, #198754, etc.)
- Zero uso de variaveis CSS
- Apenas light mode
- Zero media queries para mobile

### Telas que devem MANTER estilos de layout:
- `carteira/` — Dashboard, agrupados, carteira_simples
- `lista_pedidos.html` — Pedidos de venda com hovers semanticos
- `producao/` — Telas de manufatura
- Qualquer tela com cores semanticas de linha (estados)

### Telas que devem ser COMPLETAMENTE padronizadas:
- `pallet/v2/` — Todas as telas do modulo pallets v2
- `portal/` — Central de portais
- `fretes/` — Listagem e visualizacao
- `estoque/` — Movimentacoes e saldo
- `monitoramento/` — Entregas
- E outras telas administrativas

## Constraints

- **Tech stack**: CSS puro + Bootstrap 5 + Jinja2 (sem preprocessadores)
- **Compatibilidade**: Deve manter retrocompatibilidade com telas existentes
- **Incremental**: Mudancas devem ser feitas por modulo, nao big bang
- **Testing**: Validar em Chrome mobile (iPhone) e desktop dark mode

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Usar design-tokens existentes | Ja estao bem estruturados com hierarquia HSL clara | -- Pending |
| Nao usar preprocessadores | Manter stack simples, evitar build steps | -- Pending |
| Migrar por modulo | Reduzir risco, permitir validacao incremental | -- Pending |

---
*Last updated: 2026-01-26 after initialization*

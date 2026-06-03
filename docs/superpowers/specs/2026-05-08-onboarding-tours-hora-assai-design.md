<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Onboarding Tours — Lojas HORA + Motos Assaí

> **Papel:** Onboarding Tours — Lojas HORA + Motos Assaí.

## Indice

- [1. Problema](#1-problema)
- [2. Objetivo](#2-objetivo)
- [3. Decisões arquiteturais](#3-decisões-arquiteturais)
- [4. Arquitetura](#4-arquitetura)
  - [4.1 Layout de arquivos](#41-layout-de-arquivos)
  - [4.2 Contexto injetado no `base.html`](#42-contexto-injetado-no-basehtml)
  - [4.3 Endpoint API](#43-endpoint-api)
  - [4.4 Formato dos tours](#44-formato-dos-tours)
  - [4.5 Engine — API pública](#45-engine-api-pública)
  - [4.6 Tour macro adaptativo](#46-tour-macro-adaptativo)
- [5. Catálogo de tours](#5-catálogo-de-tours)
  - [5.1 HORA (1 macro + 13 mini-tours)](#51-hora-1-macro-13-mini-tours)
  - [5.2 Motos Assaí (1 macro + 9 mini-tours)](#52-motos-assaí-1-macro-9-mini-tours)
- [6. UX](#6-ux)
  - [6.1 Tom dos textos](#61-tom-dos-textos)
  - [6.2 Mobile](#62-mobile)
  - [6.3 Botão "?"](#63-botão)
  - [6.4 Skip / Replay](#64-skip-replay)
  - [6.5 Fim do tour](#65-fim-do-tour)
  - [6.6 Fallback](#66-fallback)
  - [6.7 Acessibilidade](#67-acessibilidade)
- [7. Ferramentas de operação](#7-ferramentas-de-operação)
  - [7.1 `/admin/onboarding/health` (rota admin)](#71-adminonboardinghealth-rota-admin)
  - [7.2 `/admin/onboarding/preview?tour=<id>` (rota admin)](#72-adminonboardingpreviewtourid-rota-admin)
- [8. Manutenção](#8-manutenção)
  - [8.1 Adicionar tour nova](#81-adicionar-tour-nova)
  - [8.2 Quando uma tela muda](#82-quando-uma-tela-muda)
  - [8.3 Reset de localStorage](#83-reset-de-localstorage)
- [9. Plano faseado](#9-plano-faseado)
- [10. Riscos](#10-riscos)
- [11. Referências](#11-referências)
- [Contexto](#contexto)

**Data**: 2026-05-08
**Status**: design aprovado — pendente plano de implementação
**Owner**: Rafael Nascimento (rafael6250@gmail.com)

---

## 1. Problema

Os módulos `app/hora/` (Lojas HORA — B2C varejo motos elétricas) e `app/motos_assai/` (B2B Q.P.A. Sendas/Assaí) foram entregues em 2026-04 e 2026-05 com escopo amplo (~14 e 16 tabelas, dezenas de telas). Usuários reportam **resistência em começar a usar** porque desconhecem os fluxos — não sabem por onde começar nem onde fica cada coisa no menu.

Documentação textual (CLAUDE.md, INVARIANTES.md) é para desenvolvedor, não para usuário final. O sistema não tem nenhum mecanismo de descoberta in-app.

## 2. Objetivo

Reduzir a barreira de entrada nos dois módulos via **guided tour in-app** que:

1. Apresenta o módulo (menu + onde fica cada coisa) no 1º acesso
2. Ensina fluxos críticos passo-a-passo dentro da própria tela onde o usuário está
3. Fica sempre disponível via botão "?" para reconsulta
4. Se adapta às permissões granulares já existentes (HORA) ou à flag admin (Motos Assaí)

Não-objetivos:
- Vídeos, animações, gamificação
- Tutorial fora do app (wiki, central de ajuda externa, YouTube)
- Persistência server-side de progresso (escolha explícita: localStorage)
- Internacionalização (apenas pt-BR)

## 3. Decisões arquiteturais

| Decisão | Escolha | Motivo |
|---|---|---|
| Library | Driver.js 1.3.x (MIT, ~5KB gzip, sem deps) | Validada em demo interativo; já tem highlight + popover + progresso nativo |
| Estilo | Tooltip flutuante com highlight do elemento real | Melhor combate a "desconhecer ONDE clicar" |
| Disparo | Auto no 1º acesso à tela + botão "?" sempre disponível | Atinge resistentes sem ser invasivo |
| Persistência | `localStorage` com chave `onboarding.<modulo>.<tour_id>.<user_id>` | Simplicidade > visibilidade administrativa (decisão do owner) |
| Estrutura | 1 tour macro adaptativo por módulo + N mini-tours por tela crítica | Macro orienta no menu; minis aprofundam fluxos |
| Filtragem por usuário | HORA: `requirePerm: {modulo, acao}` por passo/tour. Assaí: `adminOnly: true` | HORA já tem matriz granular `hora_user_permissao`; Assaí ainda só tem toggle |
| Idioma e tom | pt-BR informal-profissional | Coerente com o resto do sistema |

## 4. Arquitetura

### 4.1 Layout de arquivos

```
app/static/onboarding/
├── lib/
│   ├── driver.min.js          # self-hosted (1.3.1)
│   └── driver.css
├── core/
│   ├── tour_engine.js         # register/start/isVisible/autoStart
│   ├── localstorage_tracker.js
│   └── tour_button.js         # dropdown no header
└── tours/
    ├── hora/
    │   ├── _macro.js
    │   ├── recebimento_nf.js
    │   ├── venda_manual_nova.js
    │   ├── transferencia_nova.js
    │   ├── avaria_nova.js
    │   ├── vendas_aprovar.js
    │   ├── devolucao_venda.js
    │   ├── estoque_lista.js
    │   ├── pecas_estoque.js
    │   ├── modelos_novo.js
    │   ├── modelos_pendencias.js
    │   ├── modelos_unificar.js
    │   ├── tagplus_conta.js
    │   └── permissoes.js
    └── motos_assai/
        ├── _macro.js
        ├── recebimento_wizard.js
        ├── montagem_quick.js
        ├── disponibilizar_quick.js
        ├── separacao_chassi.js
        ├── pedidos_upload.js
        ├── compras_nova.js
        ├── recibos_upload.js
        ├── faturamento.js
        └── modelos_assai.js
```

### 4.2 Contexto injetado no `base.html`

Cada módulo injeta um JSON com permissões do usuário antes de carregar tours:

```html
{# app/templates/hora/base.html #}
<script>
  window.OnboardingContext = {
    user_id: {{ current_user.id }},
    is_admin: {{ (current_user.perfil == 'administrador') | tojson }},
    permissoes: {{ permissoes_matriz | tojson }}
  };
</script>
<script src="{{ url_for('static', filename='onboarding/lib/driver.min.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/tour_engine.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/localstorage_tracker.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/tour_button.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/tours/hora/_macro.js') }}"></script>
{% block onboarding_tours %}{% endblock %}
```

`permissoes_matriz` é fornecido pelo `before_request` do blueprint HORA via `permissao_service.get_matriz(current_user.id)` — retorna `{modulo: {acao: bool}}` para os 21 módulos × 5 ações.

Para Motos Assaí, `permissoes_matriz` é `null` (não há matriz granular ainda). A filtragem usa apenas `is_admin` + `tour.adminOnly`. Quando o módulo ganhar permissões granulares (roadmap futuro do `app/motos_assai/CLAUDE.md`), o mesmo helper pode preencher a chave `permissoes` sem alterar o engine.

### 4.3 Endpoint API

`GET /api/onboarding/permissoes-matriz` — opcional, fallback se a injeção via Jinja falhar.
Retorna o mesmo JSON de `OnboardingContext`. Usado em SPAs eventuais (carteira, futuro), não estritamente necessário para HORA/Assaí (server-side rendered).

### 4.4 Formato dos tours

```javascript
window.OnboardingEngine.register({
  id: 'hora.recebimento_nf',                    // chave única global
  titulo: 'Como receber NF da Motochefe',       // exibido no dropdown "?"
  requirePerm: { modulo: 'recebimentos', acao: 'criar' },
  autoStartRoute: '/hora/recebimentos/novo',    // glob/wildcard suportado
  steps: [
    {
      element: '#nf-upload-area',
      title: 'Suba o PDF da NF',
      description: 'Arraste ou clique para selecionar o DANFE recebido da Motochefe.',
      side: 'bottom',                           // bottom | top | left | right (auto)
      requirePerm: { modulo: 'recebimentos', acao: 'criar' }  // opcional por passo
    },
    // ...
  ],
  onFinish: () => { /* opcional, callback após último passo */ }
});
```

### 4.5 Engine — API pública

```javascript
window.OnboardingEngine = {
  register(tour),                  // adiciona à fila
  start(tourId),                   // dispara manualmente
  isVisible(tourId),               // user pode ver? (filtro permissão)
  listForCurrentRoute(),           // [{id, titulo}] dos tours desta rota
  listAllVisible(),                // [{id, titulo}] todos do módulo
  markSeen(tourId),                // marca como visto
  wasSeen(tourId),                 // já viu?
  resetModule(modulo)              // limpa todas as keys do módulo
};
```

Filtragem (`isVisible`):
```javascript
if (window.OnboardingContext.is_admin) return true;
if (tour.adminOnly) return false;
if (!tour.requirePerm) return true;
const { modulo, acao } = tour.requirePerm;
return window.OnboardingContext.permissoes?.[modulo]?.[acao] === true;
```

### 4.6 Tour macro adaptativo

Em vez de 3 macros (vendedor/gerente/admin), **1 macro com passos filtráveis**. Engine remove passos onde `requirePerm` falha. Resultado: cada usuário vê o macro com o subset de passos correspondente à sua matriz.

```javascript
// _macro.js HORA
window.OnboardingEngine.register({
  id: 'hora.macro',
  titulo: 'Bem-vindo à Lojas HORA',
  autoStartRoute: '/hora/dashboard',
  steps: [
    { element: '#menu-vendas',         title: 'Vendas (NF saída)',     requirePerm: {modulo:'vendas',         acao:'ver'} },
    { element: '#menu-estoque',        title: 'Estoque de motos',       requirePerm: {modulo:'estoque',        acao:'ver'} },
    { element: '#menu-recebimentos',   title: 'Receber da Motochefe',   requirePerm: {modulo:'recebimentos',   acao:'ver'} },
    { element: '#menu-transferencias', title: 'Transferir entre lojas', requirePerm: {modulo:'transferencias', acao:'ver'} },
    { element: '#menu-pecas-estoque',  title: 'Peças e acessórios',     requirePerm: {modulo:'pecas_estoque',  acao:'ver'} },
    { element: '#menu-tagplus',        title: 'NFe via TagPlus',        requirePerm: {modulo:'tagplus',        acao:'ver'} },
    { element: '#menu-modelos',        title: 'Catálogo de modelos',    requirePerm: {modulo:'modelos',        acao:'ver'} },
    { element: '#menu-permissoes',     title: 'Gerenciar usuários',     requirePerm: {modulo:'usuarios',       acao:'ver'} },
    { element: '#help-button',         title: 'Precisou de ajuda?',     description: 'Clique no <strong>?</strong> em qualquer tela para ver o tour daquela tela.' }
  ]
});
```

Macro Motos Assaí segue padrão equivalente, usando `adminOnly: true` em vez de `requirePerm` (até futura matriz granular).

## 5. Catálogo de tours

### 5.1 HORA (1 macro + 13 mini-tours)

| Tour ID | Tela | `requirePerm` |
|---|---|---|
| `hora.macro` | `/hora/dashboard` | (passos filtrados individualmente) |
| `hora.recebimento_nf` | `/hora/recebimentos/novo` | `recebimentos/criar` |
| `hora.venda_manual_nova` | `/hora/tagplus/pedido-venda/novo` | `vendas/criar` |
| `hora.vendas_aprovar` | `/hora/vendas/<id>` | `vendas/aprovar` |
| `hora.devolucao_venda` | `/hora/devolucoes-venda/novo` | `devolucoes_venda/criar` |
| `hora.estoque_lista` | `/hora/estoque` | `estoque/ver` |
| `hora.transferencia_nova` | `/hora/transferencias/nova` | `transferencias/criar` |
| `hora.avaria_nova` | `/hora/avarias/nova` | `avarias/criar` |
| `hora.pecas_estoque` | `/hora/pecas/estoque` | `pecas_estoque/editar` |
| `hora.modelos_novo` | `/hora/modelos/novo` | `modelos/criar` |
| `hora.modelos_pendencias` | `/hora/modelos/pendencias` | `modelos/editar` |
| `hora.modelos_unificar` | `/hora/modelos/unificar` | `modelos/aprovar` |
| `hora.tagplus_conta` | `/hora/tagplus/conta` | `tagplus/editar` |
| `hora.permissoes` | `/hora/permissoes` | `usuarios/ver` |

### 5.2 Motos Assaí (1 macro + 9 mini-tours)

| Tour ID | Tela | Visibilidade |
|---|---|---|
| `assai.macro` | `/motos-assai/dashboard` | (passos com `adminOnly` filtrados) |
| `assai.recebimento_wizard` | `/motos-assai/recibos/<id>/conferir` | universal |
| `assai.montagem_quick` | `/motos-assai/montagem` | universal |
| `assai.disponibilizar_quick` | `/motos-assai/disponibilizar` | universal |
| `assai.separacao_chassi` | `/motos-assai/separacao` | universal |
| `assai.pedidos_upload` | `/motos-assai/pedidos/upload` | `adminOnly` |
| `assai.compras_nova` | `/motos-assai/compras/nova` | `adminOnly` |
| `assai.recibos_upload` | `/motos-assai/recibos/upload` | `adminOnly` |
| `assai.faturamento` | `/motos-assai/faturamento` | `adminOnly` |
| `assai.modelos_assai` | `/motos-assai/modelos` | `adminOnly` |

## 6. UX

### 6.1 Tom dos textos
- pt-BR informal-profissional ("Você", "Clique aqui")
- Cada passo: título ≤5 palavras + descrição 1-2 frases + dica em `<strong>` opcional
- Operacional, não conceitual

### 6.2 Mobile
- Driver.js reposiciona tooltips em telas pequenas
- Botões ≥44px (tap-friendly)
- Em telas com `getUserMedia` (recebimento Assaí QR), tour pausa quando permissão de câmera é solicitada e retoma após resposta

### 6.3 Botão "?"
- Posicionado em `#help-button` no header de cada `base.html`
- Clique abre dropdown com:
  - "Tour da página atual" (se houver tour para a rota)
  - "Tour completo do módulo" (macro)
  - "Resetar tours vistos" (limpa localStorage do módulo)
- Lista filtrada por permissão (não mostra o que o usuário não pode ver)

### 6.4 Skip / Replay
- Botão "Pular" sempre visível durante tour
- Pular = `localStorage[key] = 'pulou'` (mesmo efeito que completar para não disparar de novo)
- Botão "?" sempre dispara, ignorando localStorage

### 6.5 Fim do tour
- Último passo: "Pronto! Sempre que precisar, clique no <strong>?</strong> no canto superior. Bom trabalho."
- Sem celebração, sem badge

### 6.6 Fallback
- Selector inválido → passo é pulado silenciosamente, warning no console
- Tour sempre completável

### 6.7 Acessibilidade
- Navegação por teclado nativa do Driver.js (←/→/Esc)
- `aria-live="polite"` no popover

## 7. Ferramentas de operação

### 7.1 `/admin/onboarding/health` (rota admin)
- Página que itera todos os tours registrados, abre cada `autoStartRoute` em iframe e verifica se cada `step.element` selector existe no DOM
- Tabela resultante: tour_id × passo × selector × encontrado (sim/não)
- Implementação client-side (JS no admin, sem backend que renderize páginas autenticadas)
- Executada manualmente após deploys que mexem em templates HORA/Assaí

### 7.2 `/admin/onboarding/preview?tour=<id>` (rota admin)
- Carrega a tela do tour e dispara automaticamente, ignorando localStorage
- Permite à equipe Nacom revisar tours sem precisar resetar contas de teste

## 8. Manutenção

### 8.1 Adicionar tour nova
1. Criar arquivo em `app/static/onboarding/tours/<modulo>/<nome>.js`
2. Definir `requirePerm` (HORA) ou `adminOnly` (Assaí)
3. Adicionar IDs nos elementos da tela alvo
4. Adicionar `<script>` no template da tela em `{% block onboarding_tours %}`
5. Testar em modo anônimo (limpa localStorage)

### 8.2 Quando uma tela muda
- Se um ID muda: atualizar o tour
- Se um campo é removido: remover o passo correspondente
- `/admin/onboarding/health` sinaliza selectors quebrados após deploy

### 8.3 Reset de localStorage
- Usuário: dropdown "?" → "Resetar tours vistos"
- Admin: pode pedir ao usuário, ou ajustar `localStorage` via DevTools
- Não há reset server-side (decisão de simplicidade)

## 9. Plano faseado

| Fase | Escopo | Entrega | Estimativa |
|---|---|---|---|
| F0 | Foundation: lib + engine + tracker + button + base.html injects + endpoint matriz | Infra carregada, dropdown "?" vazio | 1 dia |
| F1 | Macros adaptativos HORA + Assaí + IDs nos menus | Auto-start no 1º acesso, macro completo | 1-2 dias |
| F2 | Mini-tours operacionais críticos: 7 fluxos diários | Recebimento, venda, transferência, montagem, separação cobertos | 3 dias |
| F3 | Mini-tours administrativos: 15 telas restantes | Cobertura total | 2 dias |
| F4 | `/admin/onboarding/health`, `/admin/onboarding/preview`, microcopy review, testes mobile reais | Feature pronta para anúncio | 1 dia |

**Total: ~8-9 dias úteis.** Pausável após qualquer fase sem deixar lixo.

## 10. Riscos

| Risco | Mitigação |
|---|---|
| Selectors quebrados após mudança de UI | Página `/admin/onboarding/health` + revisão pós-deploy |
| Usuário compartilha navegador (loja física) e tour não dispara para o segundo | localStorage key inclui `user_id`; cada usuário tem suas keys |
| Usuário acha o tour intrusivo | Pode pular sempre; só dispara 1× por usuário+tour |
| Driver.js descontinuado | Library MIT self-hosted; fork interno é trivial se necessário |
| Tour rodar antes do DOM carregar (componentes async) | `tour_engine.autoStartIfFirstVisit` aguarda `DOMContentLoaded` + 200ms para components Bootstrap |
| Permissão muda no meio da sessão e tour fica inconsistente | `OnboardingContext` é injetado a cada render do `base.html`; refresh atualiza |

## 11. Referências

- Demo interativa: `.superpowers/brainstorm/827016-1778253904/content/guided-tour-demo.html`
- Driver.js docs: https://driverjs.com/
- HORA permissões: `app/hora/models/permissao.py:MODULOS_HORA`
- HORA helper de permissão: `app/auth/models.py:Usuario.tem_perm_hora`
- HORA service de permissão: `app/hora/services/permissao_service.py`
- Motos Assaí toggle: `app/auth/models.py:Usuario.pode_acessar_motos_assai`
- Decorator HORA: `app/hora/decorators.py:require_hora_perm`
- Decorator Assaí: `app/motos_assai/decorators.py:require_motos_assai`

## Contexto

_A completar (PAD-A Onda 4)._

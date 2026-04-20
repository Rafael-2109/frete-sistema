# Welcome to Nacom Goya — Sistema de Fretes

## How We Use Claude

Based on Rafael-2109's usage over the last 30 days (380 sessions):

Work Type Breakdown:
  Build Feature      ████████████░░░░░░░░  41%
  Debug Fix          █████░░░░░░░░░░░░░░░  23%
  Plan Design        ████░░░░░░░░░░░░░░░░  18%
  Improve Quality    ███░░░░░░░░░░░░░░░░░  13%
  Analyze Data       █░░░░░░░░░░░░░░░░░░░   5%

Top Skills & Commands:
  /clear                              ████████████████████  105x/month
  /feature-dev:feature-dev            ██████████████████░░   95x/month
  /superpowers:using-superpowers      ███████░░░░░░░░░░░░░   38x/month
  /resolvendo-problemas               ███░░░░░░░░░░░░░░░░░   16x/month
  /effort                             ██░░░░░░░░░░░░░░░░░░    9x/month
  /remote-control                     █░░░░░░░░░░░░░░░░░░░    8x/month
  /rename                             █░░░░░░░░░░░░░░░░░░░    8x/month
  /config                             █░░░░░░░░░░░░░░░░░░░    5x/month
  /claude-md-management:improver      █░░░░░░░░░░░░░░░░░░░    4x/month
  /plugin                             █░░░░░░░░░░░░░░░░░░░    4x/month
  /mcp                                █░░░░░░░░░░░░░░░░░░░    4x/month
  /consultando-sentry                 █░░░░░░░░░░░░░░░░░░░    3x/month

Top MCP Servers:
  render        ████████████████████  1488 calls
  sentry        ██████░░░░░░░░░░░░░░   458 calls
  context7      █░░░░░░░░░░░░░░░░░░░    13 calls

## Your Setup Checklist

### Codebases
- [ ] frete_sistema — github.com/rafael-2109/frete-sistema (Flask + SQLAlchemy + Agent SDK; 500+ arquivos, 120+ tabelas)

### MCP Servers to Activate
- [ ] **render** — metricas/logs/deploys/postgres do Render (producao). Token Bearer no `~/.claude/settings.json`. Pedir token ao Rafael.
- [ ] **sentry** — issues e exceptions do Sentry (org `nacom`, projeto `python-flask`). Token Bearer no settings global. Pedir token ao Rafael.
- [ ] **context7** — documentacao live de libs (SQLAlchemy, Flask, Anthropic SDK). Auto-instalado via plugin `context7@claude-plugins-official`.
- [ ] **github** — gerenciar issues/PRs. Configurar `GITHUB_PERSONAL_ACCESS_TOKEN` no `~/.claude/settings.json`.
- [ ] **playwright** — automacao SSW + Atacadao. `npx -y @playwright/mcp@latest --headless` (ja config).
- [ ] **postgres** — postgres-mcp em modo restricted contra Render Postgres (read-only).

### Skills to Know About
- **/feature-dev:feature-dev** — workflow guiado para desenvolver feature nova (codebase exploration + arquitetura + review). E o cavalo de batalha — usado em quase todo trabalho de feature.
- **/superpowers:using-superpowers** — protocolo de skills (invocar via Skill tool antes de responder). Carregado automaticamente no inicio de sessao.
- **/resolvendo-problemas** — workflow de 7 fases para problemas G/XG (>= 2K LOC, >= 5 arquivos). Usar quando bug for grande/cross-modulo.
- **/effort** — slider de esforco (low/medium/high/xhigh/max). Maioria das tarefas roda em high; max para problemas complexos.
- **/clear** — limpa conversa quando contexto ficou poluido (mais usado: 105x).
- **/claude-md-management:claude-md-improver** — audita/melhora os CLAUDE.md dos modulos.
- **/consultando-sentry** — bugs em producao via MCP Sentry (20 tools).
- **Skills locais de dominio** (24 skills em `.claude/skills/`): `gerindo-expedicao`, `cotando-frete`, `monitorando-entregas`, `rastreando-odoo`, `executando-odoo-financeiro`, `acessando-ssw`, `operando-ssw`, `gerindo-carvia`, `consultando-sql`, etc. Auto-descobertas pelo Claude conforme contexto.
- **Subagentes** (11 em `.claude/agents/`): `analista-carteira`, `especialista-odoo`, `raio-x-pedido`, `gestor-carvia`, `auditor-financeiro`, `controlador-custo-frete`, `gestor-recebimento`, `gestor-devolucoes`, `gestor-estoque-producao`, `analista-performance-logistica`, `desenvolvedor-integracao-odoo`.

## Team Tips

- **Auto Mode global** — `~/.claude/settings.json` ja roda `defaultMode: "auto"`. Acoes seguras passam sem pedir permissao; destrutivas bloqueiam.
- **NUNCA usar dados locais para consultas** — banco local = teste. Producao SOMPRE via MCP Render (`mcp__render__query_render_postgres`). Detalhes em `.claude/references/INFRAESTRUTURA.md`.
- **Timezone** — Brasil naive. Antes de escrever codigo com datetime: ler `.claude/references/REGRAS_TIMEZONE.md`. Hook `ban_datetime_now.py` bloqueia violacoes em PostToolUse.
- **Campos de tabela** — fonte de verdade e `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`, NAO os references (que so tem regras de negocio). Gotchas frequentes: `CarteiraPrincipal.qtd_saldo_produto_pedido` (NAO `qtd_saldo`), `Separacao.qtd_saldo` (NAO `qtd_saldo_produto_pedido`).
- **Migrations** — SEMPRE dois artefatos (`.py` com `create_app()` + `.sql` idempotente para Render Shell). Excecao: data fixes sem DDL.
- **Subagentes** — preferir `Explore` com `model: "sonnet"` quando spawnar via Task (Opus em subagente custa caro). Para implementacao: REVISAR todos os arquivos tocados; resumo do subagente nao e validacao automatica.
- **CLAUDE.md por modulo** — modulos grandes (`app/agente/`, `app/carvia/`, `app/financeiro/`, `app/odoo/`, `app/carteira/`) tem `CLAUDE.md` proprio com gotchas e patterns. SEMPRE ler antes de editar.
- **Cross-verificacao Odoo** — se encontrar inconsistencia em dados Render originados do Odoo, conferir DIRETO no Odoo. Roteamento em `.claude/references/odoo/ROUTING_ODOO.md`.
- **Output style `precision-engineer`** — zero invencao, zero trabalho incompleto, citar fonte (arquivo:linha). E o style padrao do projeto.

## Get Started

1. Rodar `/powerup` para tutorial interativo do Claude Code.
2. Ler `CLAUDE.md` (raiz) + `~/.claude/CLAUDE.md` (regras dev locais).
3. Ler `.claude/references/INDEX.md` para mapa completo de docs.
4. Pedir ao Rafael: tokens MCP (Render, Sentry, GitHub), acesso ao Render workspace `tea-d01amimuk2gs73dhlup0`.
5. Como primeira tarefa: rodar `/feature-dev:feature-dev` em uma issue pequena para sentir o workflow.

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->

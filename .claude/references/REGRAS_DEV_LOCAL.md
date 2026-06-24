<!-- doc:meta
tipo: reference
camada: L2
sot_de: regras de desenvolvimento local (worker RQ, Caddy split, migrations, JSON sanitization, CSS, stack dev)
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-12
-->
# Regras de Desenvolvimento Local

> **Papel:** SOT versionada das regras dev-only do projeto — worker RQ, Caddy split, migrations, JSON sanitization, arquitetura CSS, subdirectory CLAUDE.md e tech stack complemento. Originadas de `~/.claude/CLAUDE.md` (arquivo home do dev), que a partir desta versao passa a ser ponteiro fino para este doc.

**Abra quando:** for adicionar fila RQ, configurar rota de rede, gerar migration DDL, atribuir dict a campo JSON/JSONB, escrever CSS, criar CLAUDE.md de modulo, ou precisar do stack dev-only (Frontend/Jinja2, Artifacts, Mobile, Data/Files, Build/Deploy).

---

## Indice

- [REGRAS DEV](#regras-dev-complementam-regras-universais-do-projeto)
- [WORKER RQ — DEV vs PROD (CRITICO)](#worker-rq--dev-vs-prod-critico)
- [WEB — CADDY SPLIT AGENTE x SISTEMA (CRITICO)](#web--caddy-split-agente-x-sistema-critico)
- [MIGRATIONS](#migrations)
- [JSON SANITIZATION](#json-sanitization-campos-dbjson--jsonb)
- [ARQUITETURA CSS](#arquitetura-css)
- [SUBDIRECTORY CLAUDE.md](#subdirectory-claudemd)
- [REGRAS DEV ADICIONAIS](#regras-dev-adicionais-movidas-do-claudemd-do-projeto)
- [TECH STACK COMPLEMENTO](#tech-stack-complemento-linhas-dev-only-movidas-do-claudemd-raiz--f3-pad-ctx-2026-06-09)
- [FORMATACAO NUMERICA BRASILEIRA](#formatacao-numerica-brasileira-templates-jinja2--movida-do-claudemd-raiz)
- [DESIGN SYSTEM (UI/CSS)](#design-system-uicss--tabela-completa-movida-do-claudemd-raiz)
- [CAMINHOS DO SISTEMA](#caminhos-do-sistema)

---

## REGRAS DEV (complementam REGRAS UNIVERSAIS do projeto)

1. **NUNCA criar tela sem acesso via UI** — TODA tela DEVE ter link no menu (`app/templates/base.html`) ou em tela relacionada
2. **NUNCA mantenha lixo** — codigo substituido DEVE ser removido
3. **QUALIDADE > VELOCIDADE**: Sempre opte por pesquisar demais do que ser rápido mas não verificar algo importante.
4. **COMPONENTES UI**: ANTES de escrever botoes, badges ou elementos com cor: LER `.claude/references/design/GUIA_COMPONENTES_UI.md`

### ANTES DE PROPOR NOVOS ARQUIVOS:
1. **LER** o INDICE DE REFERENCIAS no CLAUDE.md do projeto
2. **VERIFICAR** se conteudo ja existe — se SIM, NAO criar novo
3. **MOSTRAR** o que cada arquivo existente contem antes de criar novo

**Se nao souber onde encontrar uma informacao**: LER `.claude/references/INDEX.md`

---

## WORKER RQ — DEV vs PROD (CRITICO)

**PROD (Render `sistema-fretes-worker-atacadao`) NAO usa `worker_atacadao.py`.**
Usa `start_worker_render.sh` -> `worker_render.py` com `--queues HARDCODED`.

**Adicionar nova fila RQ exige editar 3 arquivos:**

1. `worker_render.py` linha ~143: `--queues default='...,nova_fila,...'`
2. `worker_render.py` linha ~211: `FILAS_PESADAS = {..., 'nova_fila'}` SE pesada (>5min ou alto Odoo/RAM)
3. `start_worker_render.sh` linha ~301: `--queues high,...,nova_fila,default`

**Sintoma se esquecer:** job e enfileirado mas worker nunca processa
(fila nao monitorada). Polling `/status/{job_id}` retorna 404 "job nao encontrado".

**3 perfis de worker** (`worker_render.py:184+`):
- Worker 0 LIGHT-RESERVED: tudo MENOS FILAS_PESADAS (preserva slot interativo)
- Worker 1 FULL: TODAS (unico que pega `impostos` exclusiva)
- Worker 2+ GENERAL: tudo MENOS `impostos`

`worker_atacadao.py` (DEV standalone) tem `--queues` proprio. Manter coerencia
mas NAO substitui edicao do `worker_render.py`+`start_worker_render.sh`.

Memoria detalhada: `memory/worker_render_filas.md`. Bug historico SPED ECD V1.3
(commit `9d4e11d2` 2026-05-14).

---

## WEB — CADDY SPLIT AGENTE x SISTEMA (CRITICO)

> Proxy real = **Caddy** (`Caddyfile` na raiz; NAO ha `nginx.conf`). A regra de afinidade de sessao por processo chama-se **R-SPLIT-NGINX** em `app/agente/CLAUDE.md` (nome historico mantido).

**PROD `sistema-fretes` agora roda Caddy + 2 gunicorn isolados no MESMO container:**

| Path | Proxy | Gunicorn config | Workers x Threads |
|---|---|---|---|
| `/agente/*` | `127.0.0.1:5001` | `gunicorn_config_agente.py` | 1 x 8 |
| `/agente-lojas/*` | `127.0.0.1:5001` | (mesmo gunicorn-agente) | 1 x 8 |
| `/static/*` | Caddy serve do disco | — | — |
| resto | `127.0.0.1:5002` | `gunicorn_config_sistema.py` | 4 x 2 |

`start_render.sh` orquestra: pre_start.py → flask db upgrade → sync incremental →
gunicorn-agente (bg) → gunicorn-sistema (bg) → aguarda health (5001+5002) →
Caddy em foreground com trap SIGTERM/SIGINT + watchdog.

**Motivo (2026-05-27)**: Claude Agent SDK e per-process (Pattern 2 doc oficial
`/hosting`). Multi-worker + sticky session quebrava 409 quando dono ocupado
pos-stream. Detalhes: `app/agente/CLAUDE.md` secao R-SPLIT-NGINX.

**Adicionar nova rota fora de `/agente/` ou `/static/`**: nada a fazer
(cai automaticamente em sistema). **Nova rota em `/agente/`**: cai
automaticamente em agente. **Rota nova precisa SSE em outro path**:
verificar `Caddyfile` — proxy ja repassa SSE (sem buffering por padrao no Caddy).

**Memoria/CPU**: 1×800MB (agente) + 4×400MB (sistema) + 50MB (Caddy) ≈ 2.4GB
de 8GB Pro Plus. Sobra confortavel.

---

## MIGRATIONS

**SEMPRE gerar DOIS artefatos** para DDL (ALTER/CREATE/DROP):
1. `scripts/migrations/NOME.py` — Python com `create_app()` + verificacao before/after
2. `scripts/migrations/NOME.sql` — SQL idempotente para Render Shell (`IF NOT EXISTS`)

Excecao: data fixes (UPDATE/INSERT sem DDL) podem ser apenas Python.

---

## JSON SANITIZATION (campos `db.JSON` / `JSONB`)

**SEMPRE usar `sanitize_for_json()`** ao atribuir dicts vindos de fontes com
`Decimal` / `datetime` / `UUID` / `bytes` a campos `db.Column(db.JSON)` ou `JSONB`.

```python
from app.utils.json_helpers import sanitize_for_json

# ANTES (quebra no flush): TypeError: Object of type Decimal is not JSON serializable
obj.campo_json = resultado_calculadora_frete

# DEPOIS (seguro, idempotente):
obj.campo_json = sanitize_for_json(resultado_calculadora_frete)
```

**Usar SEMPRE quando a fonte e**:
- `CalculadoraFrete.calcular_frete_unificado()` (11 Decimals no `detalhes`)
- Queries SQLAlchemy com colunas `Numeric`/`DECIMAL`
- ORM objects, APIs Odoo, parsers XML/PDF
- Qualquer dict cuja origem voce nao controla 100%

**Guia completo** (quando usar / quando nao precisar / `decimal_as_str` / callsites):
`.claude/references/PADROES_BACKEND.md` secao "JSON Sanitization".

Bug historico que motivou: 2026-04-14, `CotacaoV2Service.calcular_cotacao()`
explodia flush por `detalhes_calculo` com Decimals vindos da `CalculadoraFrete`.

---

## ARQUITETURA CSS

**Sistema de layers** (`main.css`): `tokens → base → components → modules → utilities`
- `bootstrap-theme-override.css` FORA de layers (sobrescreve Bootstrap CDN)

### REGRAS CSS:
1. **NUNCA adicionar `<style>` blocks em templates** — usar CSS de modulo (`modules/_nome.css`)
2. **Badges compartilhados** (3+ modulos): `components/_badges.css` usando API `--_badge-bg/color/border`
3. **Badges de modulo**: no CSS do modulo (`_fretes.css`, `_financeiro.css`, `_manufatura.css`)
4. **Cores**: SEMPRE usar design tokens (`var(--text)`, `var(--bg-light)`, etc.) — NUNCA hex hardcoded
5. **Dark mode**: tokens adaptam automaticamente. Se precisar ajuste: `[data-bs-theme="light"]` selector
6. **Cache-busting de `@import` (Caddy `immutable`)**: o Caddy serve `/static/*` DIRETO do disco
   com `Cache-Control: public, max-age=604800, immutable` (`Caddyfile`) — Flask NÃO intercepta o
   arquivo CSS. `immutable` = o browser nunca revalida. Como os `@import` dentro do `main.css` têm
   URL FIXA (sem `?v=`), editar um `modules/_*.css` NÃO muda a URL → o browser serve a versão velha
   por 7 dias (nem F5 resolve). **Versionar só o `main.css` (via `asset_url`) NÃO basta**: rebaixa o
   `main.css`, mas os `@import` internos continuam com URL fixa e cacheados.
   **Solução:** o `main.css` é servido pela rota `/assets/main.css` (`app/__init__.py` →
   `app/utils/asset_bundler.py`), que reescreve cada `@import` local para `/static/css/...?v=<hash>`.
   Agora a URL do import muda com o conteúdo → o browser rebaixa só o que mudou, sem hard reload.
   `asset_url` continua para JS / CSS-folha (arquivos sem `@import`). **Não voltar o `<link>` do
   `base.html` para `main.css|asset_url`** — reintroduz o bug.

| Arquivo | Papel |
|---------|-------|
| `css/components/_badges.css` | Fonte unica para badges compartilhados |
| `css/bootstrap-theme-override.css` | Ponte Bootstrap CDN → design tokens |
| `css/tokens/_design-tokens.css` | Tokens de design (light/dark) |
| `css/main.css` | Entry point do sistema de layers |
| `css/modules/_*.css` | Estilos por modulo (fretes, financeiro, etc.) |

---

## SUBDIRECTORY CLAUDE.md

> **Manual**: `.claude/references/MANUAL_CLAUDE_MD.md` — template, principios, checklist e exemplo comentado

Modulos complexos tem CLAUDE.md proprio com patterns, convencoes e gotchas de desenvolvimento:

**Criados** (stats dos proprios CLAUDE.md, atualizar ao editar cada modulo):
- `app/agente/CLAUDE.md` — ~51K LOC, 97 arquivos (+ `services/CLAUDE.md` — ~12.8K LOC, 20 arquivos; + `SDK_CHANGELOG.md` — historico SDK 0.1.49-0.2.101)
- `app/agente_lojas/CLAUDE.md` — ~2.2K LOC, 17 arquivos (status M2), agente isolado para Lojas HORA, endpoint `/agente-lojas/*`
- `app/carteira/CLAUDE.md` — ~18.1K LOC, 50 arquivos, 22 JS
- `app/carvia/CLAUDE.md` — ~66K LOC, 104 arquivos, 108 templates (+ 12 sub-docs CONFERENCIA/FINANCEIRO/etc.)
- `app/chat/CLAUDE.md` — ~2.0K LOC, 22 arquivos, chat in-app + alertas sistema unificados
- `app/devolucao/CLAUDE.md` — ~13.9K LOC, 17 arquivos, 7 templates (+ `CLAUDE_MODELOS.md`, `CLAUDE_APIS.md`, `CLAUDE_FLUXOS.md`)
- `app/financeiro/CLAUDE.md` — ~45.1K LOC, 77 arquivos
- `app/fretes/CLAUDE.md` — ~19.0K LOC, 20 arquivos, 43 templates (modulo CORE: lancamento Odoo 16 etapas, CTe, despesas extras, conta corrente)
- `app/hora/CLAUDE.md` — modulo Lojas HORA Motochefe (B2C varejo motos eletricas), 46 tabelas, fronteira estrita NAO-importar de outros modulos
- `app/motos_assai/CLAUDE.md` — ~19.8K LOC, 90 arquivos, modulo B2B Q.P.A. Sendas/Assai (motos eletricas), 29 tabelas prefixo `assai_`, fronteira estrita
- `app/odoo/CLAUDE.md` — ~42.5K LOC, 70 arquivos (inclui subpacote `estoque/` ~19.9K LOC, com `estoque/CLAUDE.md` proprio)
- `app/relatorios_fiscais/CLAUDE.md` — modulo SPED ECD Centralizado (3 companies FB+SC+CD), Leiaute 9, ciclo iterativo de correcoes contra PVA (+ `SPED_ECD_PLANO.md` — inventario de erros vivo entre sessoes)
- `app/seguranca/CLAUDE.md` — ~2K LOC, 14 arquivos, 8 templates
- `app/teams/CLAUDE.md` — ~2.3K LOC, 4 arquivos
- `app/whatsapp/CLAUDE.md` — ~875 LOC, 5 arquivos (canal via OpenClaw + plugin nacom-bridge em `~/.openclaw/plugins/`)
- `app/motochefe/CLAUDE.md` — ~20.7K LOC (distribuidora B2B de motos; hub de navegacao p/ `documentacao/` 26 docs + carga inicial; consumido por hora/motos_assai) [criado 2026-06-19]
- `app/integracoes/CLAUDE.md` — conector TagPlus (OAuth2/NFe/webhooks); hub p/ `tagplus/` 8 docs [criado 2026-06-19]

**Planejados (ainda nao criados):**
- `app/recebimento/CLAUDE.md` — P0 (28.7K LOC, 29 arquivos — maior modulo sem CLAUDE.md)
- `app/pallet/CLAUDE.md` — P1 (13.8K LOC)
- `app/portal/CLAUDE.md` — P2 (15.3K LOC, 40 arquivos — Atacadao/Hodie integration)
- `app/pedidos/CLAUDE.md` — P2 (13.6K LOC, 31 arquivos — leitura PDFs VOE)

---

## REGRAS DEV ADICIONAIS (movidas do CLAUDE.md do projeto)

1. **TIMEZONE HOOK**: Hook `ban_datetime_now.py` bloqueia violacoes de timezone (exit 1). Verificar antes de commitar.
2. **AGENTE LOGISTICO — NAO MISTURAR**: Regras P1-P7 vivem em `.claude/references/negocio/REGRAS_P1_P7.md` e sao REFERENCIADAS por `system_prompt.md` e `analista-carteira.md`. `CLAUDE.md` = dev, `system_prompt.md` = agente web. NUNCA inlinar regras de negocio extensas no system_prompt.
3. **OPENCLAW / PLAYWRIGHT**: Timeouts generosos para tool calls longas (30s+ minimo). Verificar resultados DIRETO no sistema alvo (Odoo, SSW) — NAO confiar apenas no output do Playwright. Despachar jobs via API OpenClaw — NAO rodar dominios de cron manualmente.
4. **PAD-A (docs/scripts)**: ANTES de criar/editar doc ou script: LER `.claude/references/ARQUITETURA_DE_ARTEFATOS.md` ou usar skill `padronizando-docs`. (Movida do CLAUDE.md raiz na F3 PAD-CTX 2026-06-09 — o agente web nao cria docs.)
5. **CONTEXTO DO AGENTE (PAD-CTX)**: ANTES de adicionar/mover conteudo em qualquer camada do contexto do Agente Web (preset, system_prompt, CLAUDE.md raiz, skills, hook, memorias): LER `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md` (criterios de admissao por camada).
6. **SEGFAULT (WSL2)**: `Segmentation fault` (exit 139) neste ambiente WSL2. Dois casos DISTINTOS observados (2026-06-16), com causas diferentes — nao confundir:
   - **pytest (REPRODUZIVEL)**: rodar suites de modulos diferentes JUNTAS crasha por colisao de extensoes nativas C (numpy/pandas/lxml/rapidfuzz) carregadas no MESMO processo (ex.: `tests/carvia/` + `tests/portal_sendas/`). Mitigacao: rodar cada modulo em invocacao pytest SEPARADA.
   - **pre-commit (PONTUAL, NAO reproduzivel)**: `route_template_audit.py` e' ESTATICO/leve (regex + `rglob`; NAO importa `app` nem libs nativas — verificado: o import carrega 0 modulos pesados e roda 5/5 `EXIT=0` isolado). O segfault que ocorreu 1x foi crash de processo PONTUAL de ambiente, NAO defeito do audit. Como o hook usa `set -e`, qualquer crash pontual aborta o commit sem violacao real.
   **Mitigacao**: (1) RE-TENTAR o commit — passa (o crash do pre-commit nao se reproduz); (2) `git commit --no-verify` so' em ultimo caso e quando o commit NAO toca rota/template (unico alvo do audit = `render_template` -> template inexistente), validando depois com `python3 scripts/audits/route_template_audit.py`.

---

## TECH STACK COMPLEMENTO (linhas dev-only movidas do CLAUDE.md raiz — F3 PAD-CTX 2026-06-09)

| Camada | Stack |
|--------|-------|
| **Frontend** | **HTML5 + Jinja2** (templates) · **Bootstrap 5.3.3** (CSS self-hosted via `@layer bootstrap`, JS bundle CDN) · **jQuery 3.6** + jQuery Mask 1.14 (legado) · **HTMX 1.9.11** · Vanilla JS · CSS `@layer` proprio (tokens → base → components → modules → utilities) · **FontAwesome 6.4.0** (CDN) |
| **Artifacts (chat web)** | React 18 + TS + Tailwind + Parcel via Node 20 (NVM lazy install no worker) · bundle.html servido em iframe sandboxed |
| **Mobile App (GPS)** | Capacitor 6 (Android/iOS) — modulo rastreamento de motoristas |
| **Data / Files** | pandas 3.0 · openpyxl · xlsxwriter · pdfplumber + pypdf · weasyprint · python-docx · tesserocr (OCR PT) |
| **Build / Deploy** | `build.sh` + `start_render.sh` (web) · `start_worker_render.sh` (worker) · auto-deploy via `main` branch GitHub |

---

## FORMATACAO NUMERICA BRASILEIRA (templates Jinja2 — movida do CLAUDE.md raiz)

Filtros em `app/utils/template_filters.py`:
```jinja
{{ valor|valor_br }}        {# R$ 1.234,56 #}
{{ valor|valor_br(4) }}     {# R$ 1.234,5678 #}
{{ qtd|numero_br }}         {# 1.234,567 #}
{{ qtd|numero_br(0) }}      {# 1.234 #}
```

---

## DESIGN SYSTEM (UI/CSS) — tabela completa (movida do CLAUDE.md raiz)

| Preciso de... | Documento |
|---------------|-----------|
| Badges, botoes, tabelas (qual classe usar, como criar nova) | `.claude/references/design/GUIA_COMPONENTES_UI.md` |
| Arquitetura CSS (@layer, tokens, components/modules) | `app/static/css/README.md` |
| Auditar codigo existente | `python scripts/audits/ui_audit.py` |
| Detectar regressao antes de commit em CSS/templates | `python scripts/audits/ui_audit_regression.py` |
| **Lint policy bloqueador** (regras P1-P9) | `python scripts/audits/ui_policy_lint.py --enforce-new` (pre-commit) ou `--report-only` (auditoria) |
| Pre-commit hook UI lint (instalar) | `ln -sf ../../scripts/hooks/pre-commit-ui-lint.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit` |
| Analise dimensional (WCAG, headers, etc) | `python scripts/audits/ui_dimension_analysis.py` → `relatorios/ui_dimension_analysis_<data>.md` |
| Detectar regressao VISUAL (pixel diff) antes de commit | `tests/visual/` (capture + compare via Playwright/PIL) |
| Visual regression — credenciais bot | `scripts/seed/create_visual_test_user.py` (cria/atualiza `claude-visual@bot.nacom.com.br`, salva senha so em `.env` — NUNCA commitar) |
| Catalogo de inconsistencias (badges duplicados, tabelas, vars BS) | `relatorios/ui_audit_FINDINGS_<data>.md` |

---

## CAMINHOS DO SISTEMA

> Caminhos por modulo: ver tabela CAMINHOS DO SISTEMA no CLAUDE.md raiz do projeto.

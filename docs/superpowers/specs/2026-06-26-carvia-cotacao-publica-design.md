<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-26
-->
# CarVia — Cotação Rápida: limpeza do PDF, tela pública e persistência — Design

> **Papel:** spec da feature que (1) remove `tipo_carga`/`modalidade` do resultado, (2) cria uma tela de Cotação Rápida **sem login**, e (3) persiste essas cotações públicas e as exibe no fim da Cotação Rápida com login.
>
> **Data:** 2026-06-26 · **Autor:** Rafael (via Claude Code) · **Status:** Em revisão (aguardando aprovação da spec)

## Indice
- [Contexto](#contexto)
- [Decisões](#decisões)
- [Arquitetura](#arquitetura)
- [Parte 1 — Remover tipo_carga + modalidade](#parte-1--remover-tipo_carga--modalidade)
- [Parte 2 — Tela pública sem login](#parte-2--tela-pública-sem-login)
- [Parte 3 — Persistência](#parte-3--persistência)
- [Parte 4 — Exibição na tela com login](#parte-4--exibição-na-tela-com-login)
- [Migration](#migration)
- [Testes](#testes)
- [Arquivos afetados](#arquivos-afetados)
- [Fora de escopo](#fora-de-escopo)

## Contexto

A Cotação Rápida CarVia (`/carvia/cotacao-rapida`) hoje é **efêmera** e exige login + guard `sistema_carvia`. Cota frete de moto por destino (UF/cidade/CEP), com entrada manual (modelo+qtd) ou upload de PDF/imagem lido por IA (Haiku), e emite PDF em papel timbrado (weasyprint).

Arquivos atuais:
- `app/carvia/routes/cotacao_rapida_routes.py` — rotas (todas `@login_required` + guard `sistema_carvia`).
- `app/carvia/services/pricing/cotacao_rapida_service.py` — `CotacaoRapidaService` (motor + histórico).
- `app/carvia/services/parsers/cotacao_rapida_llm_service.py` — leitura LLM.
- `app/templates/carvia/cotacao_rapida/form.html` — tela (Jinja + ~300 linhas de JS inline).
- `app/templates/carvia/cotacao_rapida/imprimir_cotacao.html` — template do PDF.

Fatos de infra confirmados:
- **Não há auth gate global**: o app só protege rotas com `@login_required` (Flask-Login). Rota sem o decorator é pública.
- `base.html` esconde sidebar/menu para anônimo (`{% if current_user.is_authenticated %}`) e sempre injeta `<meta name="csrf-token">` (linha 7) + assets. Logo a tela pública **estende `base.html`** e fica limpa, com CSRF funcional para POSTs anônimos. (Mesmo padrão de `carvia/portal/login.html`.)
- Redis disponível via `app.utils.redis_cache.RedisCache` (atributo `.client`; degrada gracioso se indisponível).

## Decisões

| # | Decisão | Escolha |
|---|---------|---------|
| D1 | Upload IA (Haiku) na tela pública | **Incluir** igual à tela com login |
| D2 | Quando persistir a cotação pública | **Ao calcular** com resultado válido (1 registro por cálculo com opções) |
| D3 | Identificação do solicitante (tela pública) | **Apenas Nome** — obrigatório (sem telefone/e-mail) |
| D4 | Escopo da remoção tipo_carga/modalidade | **PDF e tela web** (com e sem login) |
| D5 | Anti-abuso do LLM exposto | **Rate-limit por IP via Redis** no `upload` e `calcular`, fallback gracioso |
| D6 | Reuso do JS | **Compartilhar**: extrair p/ `static/js/carvia/cotacao_rapida.js` parametrizado; as duas telas usam a mesma fonte |

## Arquitetura

Quatro frentes, isoladas:

1. **UI de resultado** (Parte 1) — só remove 2 badges do PDF e do JS de render.
2. **Tela pública** (Parte 2) — rotas públicas espelho + template + JS compartilhado + rate-limit.
3. **Persistência** (Parte 3) — modelo + service de gravação + migration.
4. **Listagem na tela com login** (Parte 4) — service de leitura + seção no template.

O motor de cotação (`CotacaoRapidaService.cotar`) e o LLM (`extrair_motos_regiao`) são **reusados as-is** pelas rotas públicas. Os helpers de rota (`_resolver_contexto`, `_modelos_orm`, `_ufs_destino_disponiveis`) hoje privados em `cotacao_rapida_routes.py` são extraídos para um módulo comum reusado pelas duas famílias de rota — **fonte única**, sem duplicar a normalização do payload.

## Parte 1 — Remover tipo_carga + modalidade

- `imprimir_cotacao.html`: remover as duas linhas de `<span class="badge">{{ op.tipo_carga }}</span>` e `{{ op.modalidade }}` (atualmente linhas 81-82). Mantém o badge `grupo_cliente`.
- JS de render (compartilhado, ver Parte 2): remover os dois `<span class="badge ...">${esc(op.tipo_carga)}</span>` e `${esc(op.modalidade)}` (form.html atual, linhas 313-314). Mantém `grupo_cliente`.
- **Backend inalterado**: `cotar()`/`_expandir_por_modelo` continuam devolvendo `tipo_carga`/`modalidade` (usados em avisos internos como `f'... ({t.tipo_carga}) ...'`). Só a renderização deixa de exibi-los.

## Parte 2 — Tela pública sem login

URL na **raiz** `/cotacao` (divulgável, curta) — fora do blueprint `carvia` (que tem `url_prefix=/carvia`). Implementada como **blueprint isolado próprio** `cotacao_publica_bp` em `app/carvia/cotacao_publica.py` (mesmo padrão de `app/carvia/portal_cliente.py`): `Blueprint('cotacao_publica', __name__, url_prefix='/cotacao')`, registrado em `app/carvia/__init__.py` `init_app` (ao lado de `portal_cliente_bp`). **Nenhuma rota usa `@login_required` nem o guard `sistema_carvia`.**

Rotas:
- `GET /cotacao` → `render_template('carvia/cotacao_publica/form.html', modelos=..., ufs_destino=...)`. Template estende `base.html` (limpo p/ anônimo).
- `POST /cotacao/calcular` → resolve contexto (helper comum) → `CotacaoRapidaService().cotar(...)` → **se `resultado['opcoes']`: persiste (Parte 3)** → devolve JSON sanitizado. Exige `solicitante_nome` não-vazio no payload (400 se faltar). Rate-limit por IP (D5).
- `POST /cotacao/upload` → `extrair_motos_regiao(...)` (mesmo guard de 20 MB). Rate-limit por IP (D5).
- `POST /cotacao/pdf` → re-cota e gera PDF (mesma lógica da rota logada; reusa `imprimir_cotacao.html` já limpo).
- `GET /cotacao/cep/<cep>` → `resolver_cep` (sem guard).

Template `app/templates/carvia/cotacao_publica/form.html`:
- Estende `base.html`; bloco content = mesma estrutura de 2 colunas do form logado **mais um campo "Nome do solicitante" obrigatório** no card de destino.
- Inclui `<script src="{{ 'js/carvia/cotacao_rapida.js'|asset_url }}">` com `data-*` apontando para os endpoints públicos (`/cotacao/...`) e `data-modo="publico"` (exige nome). Não inclui `_quick_nav.html` (é navegação interna).

JS compartilhado `app/static/js/carvia/cotacao_rapida.js`:
- Extraído do inline de `form.html`. Lê os endpoints e o modo de `data-*` de um nó raiz (ex.: `#cr-app data-endpoint-calcular=... data-endpoint-upload=... data-endpoint-pdf=... data-endpoint-cep=... data-modo=...`).
- No modo `publico`, valida `solicitante_nome` antes de `calcular` e injeta o campo no payload.
- Render sem os badges `tipo_carga`/`modalidade` (Parte 1).
- Servido a **ambas** as telas (logada e pública), eliminando a duplicação.

Rate-limit (D5) — helper `app/carvia/utils/rate_limit.py`:
- `permitir(acao: str, ip: str, *, limite: int, janela_seg: int) -> bool` usando `RedisCache().client` (`INCR` + `EXPIRE` na 1ª ocorrência). Se `client` é `None`/erro → **retorna `True`** (degrada aberto, não derruba a tela).
- Limites iniciais: `upload` = 20/h por IP; `calcular` = 60/h por IP. IP via `request.headers.get('X-Forwarded-For', request.remote_addr)` (1º hop), pois roda atrás do Caddy/Render.
- Excedido → HTTP 429 com `{'ok': False, 'erro': 'Muitas requisições. Tente novamente mais tarde.'}`.

## Parte 3 — Persistência

Modelo `CarviaCotacaoRapidaPublica` em `app/carvia/models/cotacao.py` (exportado em `models/__init__.py`), tabela `carvia_cotacoes_rapidas_publicas`:

| Coluna | Tipo | Nota |
|--------|------|------|
| `id` | Integer PK | |
| `solicitante_nome` | String(160) NOT NULL | D3 |
| `cnpj_cliente` | String(20) NULL | opcional |
| `uf_destino` | String(2) NOT NULL | |
| `cidade_destino` | String(120) NULL | |
| `codigo_ibge` | String(7) NULL | chave canônica de cidade |
| `itens` | JSON NOT NULL | `[{modelo_id, modelo_nome, categoria_nome, quantidade}]` (do `resultado['itens']`) |
| `opcoes` | JSON NOT NULL | snapshot de `resultado['opcoes']` (tabela_nome, valor_total, modelos, lead_time, grupo_cliente) |
| `valor_total_min` | Numeric(15,2) NULL | menor `valor_total` entre as opções (p/ ordenar/listar) |
| `qtd_total_motos` | Integer NULL | soma de `quantidade` dos itens |
| `ip_solicitante` | String(45) NULL | IPv4/IPv6 |
| `user_agent` | String(255) NULL | |
| `criado_em` | DateTime NOT NULL | `agora_brasil_naive()` (convenção naive Brasil) |

Índices: `criado_em` (desc para a listagem), `uf_destino`.

Gravação — método novo no `CotacaoRapidaService`:
```
registrar_cotacao_publica(resultado, *, solicitante_nome, cnpj_cliente, ip, user_agent) -> CarviaCotacaoRapidaPublica
```
- Chamado pela rota pública `calcular` somente quando `resultado['opcoes']`.
- Deriva `valor_total_min`/`qtd_total_motos` do `resultado`; `uf_destino`/`cidade_destino`/`codigo_ibge` de `resultado['regiao']`.
- Falha de gravação **não derruba a resposta da cotação** (try/except com log) — o valor já foi calculado; persistir é efeito colateral.

## Parte 4 — Exibição na tela com login

- Método novo `CotacaoRapidaService.listar_cotacoes_publicas(limit=20) -> List[Dict]` — últimas N por `criado_em desc`, projetando `{criado_em, solicitante_nome, destino (cidade/uf), qtd_total_motos, valor_total_min, opcoes}`.
- Rota `cotacao_rapida()` (com login) passa `cotacoes_publicas=...listar_cotacoes_publicas(20)` ao template.
- `form.html` (logado): **seção no final** (após a coluna de resultado) — título "Cotações da tela pública (sem login)" + tabela: Data · Solicitante · Destino · Nº motos · Menor valor · botão "ver" que expande as opções (a partir do JSON embutido). Renderização server-side (sem novo endpoint).

## Migration

Par DDL + Python (regra CLAUDE.md), no **padrão real do CarVia** (não Alembic — head Alembic está congelado em `7e880edbf40a`):
- `scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.sql` — `CREATE TABLE IF NOT EXISTS ...` + `CREATE INDEX IF NOT EXISTS ...` (idempotente).
- `scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.py` — aplicador (`create_app()` + `db.session.execute(text(<sql>))` + valida via `information_schema`), igual a `carvia_cce.py`. Idempotente, safe re-exec.

## Testes

`tests/carvia/test_cotacao_publica.py`:
1. **Service registra**: `registrar_cotacao_publica` grava 1 linha com os campos derivados corretos (valor_total_min, qtd_total_motos).
2. **Service lista**: `listar_cotacoes_publicas(limit)` retorna em ordem desc e respeita o limite.
3. **Rota pública sem login**: `GET /carvia/cotacao-publica` → 200 sem sessão; `POST .../calcular` com nome → persiste (conta +1) e responde opções.
4. **Nome obrigatório**: `POST .../calcular` sem `solicitante_nome` → 400, nada persistido.
5. **Sem opções não persiste**: payload que zera opções não grava registro.
6. **Rate-limit**: estourar o limite → 429 (com Redis fake/patch); sem Redis → passa (degrada aberto).
7. **Render sem badges**: o PDF/HTML renderizado não contém `tipo_carga`/`modalidade` (smoke no template).

## Arquivos afetados

**Novos**
- `app/carvia/cotacao_publica.py` (blueprint isolado `cotacao_publica_bp`, rotas `/cotacao*`)
- `app/carvia/routes/cotacao_rapida_common.py` (helpers extraídos)
- `app/carvia/utils/rate_limit.py`
- `app/templates/carvia/cotacao_publica/form.html`
- `app/static/js/carvia/cotacao_rapida.js`
- `scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.sql`
- `scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.py` (aplicador, padrão `carvia_cce.py`)
- `tests/carvia/test_cotacao_publica.py`

**Editados**
- `app/carvia/__init__.py` (registrar `cotacao_publica_bp` no `init_app`, ao lado do `portal_cliente_bp`)
- `app/carvia/routes/cotacao_rapida_routes.py` (importar helpers do módulo comum; passar `cotacoes_publicas` ao template)
- `app/carvia/services/pricing/cotacao_rapida_service.py` (+`registrar_cotacao_publica`, +`listar_cotacoes_publicas`)
- `app/carvia/models/cotacao.py` (+modelo) e `app/carvia/models/__init__.py` (export)
- `app/templates/carvia/cotacao_rapida/form.html` (usar JS externo; seção de cotações públicas; remover badges do JS movido)
- `app/templates/carvia/cotacao_rapida/imprimir_cotacao.html` (remover 2 badges)
- `app/carvia/CLAUDE.md` (registrar a feature/rota pública + tabela nova)

## Fora de escopo

- CRUD/gestão das cotações públicas (editar, converter em CarviaCotacao/Pedido). Só registro + listagem.
- Captcha/telefone/e-mail do solicitante (D3 = só nome).
- Notificação/lead-routing (Teams/e-mail) ao chegar cotação pública.
- Alterar o motor de preço ou o histórico por tabela.

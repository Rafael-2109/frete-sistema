<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-07-01
-->
# Alertas de Faturamento por CNPJ (e-mail + Teams)

> **Papel:** desenho da feature que, ao faturar (entrada de NF nova via sync Odoo)
> para um CNPJ cadastrado, dispara um aviso por **e-mail** (lista por CNPJ) e no
> **Teams** (um canal fixo para todos). Cadastro e configuração vivem num card novo
> da **Central Fiscal**. Aprovado por Marcus em 2026-07-01.

> **⚠️ Atualização 2026-07-01 (pós-implementação, correções do Marcus):**
> **(1) Teams removido** — o alerta é **somente por e-mail**. Removidos: `enviar_teams`,
> `montar_texto_teams`, e a **tabela `alerta_faturamento_config`** (existia só para o
> webhook/flags do Teams); o liga/desliga por CNPJ (`ativo`) é o único controle. Ficam
> **2 tabelas** (`alerta_faturamento_cnpj` + `alerta_faturamento_enviado`, `canal='email'`).
> **(2)** Lista de e-mails padrão (`EMAILS_PADRAO`, time Conservas Campo Belo) pré-preenche
> o formulário de novo CNPJ. **(3)** Carga inicial dos **31 CNPJs do Atacadão RJ** via
> `scripts/migrations/2026_07_01_seed_alertas_faturamento_atacadao_rj.py`. As seções abaixo
> descrevem o desenho original (com Teams) e ficam como registro histórico.

## Indice

- [1. Contexto e âncoras verificadas](#1-contexto-e-âncoras-verificadas)
- [2. Decisões aprovadas](#2-decisões-aprovadas)
- [3. Arquitetura](#3-arquitetura)
- [4. Dados (3 tabelas novas)](#4-dados-3-tabelas-novas)
- [5. Gatilho (hook na sync Odoo)](#5-gatilho-hook-na-sync-odoo)
- [6. Serviço de alerta](#6-serviço-de-alerta)
- [7. Canais de envio](#7-canais-de-envio)
- [8. UI (Central Fiscal)](#8-ui-central-fiscal)
- [9. Idempotência e segurança](#9-idempotência-e-segurança)
- [10. Migration](#10-migration)
- [11. Testes](#11-testes)
- [12. Documentação a atualizar](#12-documentação-a-atualizar)
- [13. Fora de escopo (YAGNI)](#13-fora-de-escopo-yagni)

## 1. Contexto e âncoras verificadas

Tudo abaixo foi lido no código antes deste desenho:

- **Central Fiscal** é um hub de cards em `app/recebimento/routes/views.py:130` (rota
  `recebimento_views.central_fiscal`), template `app/templates/recebimento/central_fiscal.html`.
  Adicionar um card novo = editar só o template.
- **Momento do faturamento** = sync de NFs do Odoo em
  `app/odoo/services/faturamento_service.py`, função `importar_faturamento_odoo`.
  - `nfs_novas` (lista, definida em `:710`, `.append` em `:825`) = **NFs realmente
    inseridas** nesta rodada. É o sinal limpo de "acabou de faturar".
  - `cnpjs_processados` (`:773`) inclui TODOS os CNPJs vistos (inclusive só update de
    status) — **não usar** como gatilho de alerta.
  - Já existe um loop pós-sync por CNPJ (`:1126`, SYNC 4 = frete). O hook de alerta
    entra como uma SYNC nova, no mesmo ponto pós-persistência.
- **Cabeçalho da NF** = `RelatorioFaturamentoImportado` (`app/faturamento/models.py:4`).
  Campos disponíveis para o aviso: `numero_nf`, `data_fatura`, `cnpj_cliente`,
  `nome_cliente`, `valor_total`, `municipio`, `estado`. Persistido ANTES do ponto do hook.
- **Carteiro de e-mail** pronto: `app/notificacoes/email_sender.py`
  (`email_sender` singleton, backends SMTP/SES/SendGrid; `EmailTemplates.info/alerta_atencao`).
  Config via env `EMAIL_*` (`EmailConfig.is_configured()`).
- **Teams para canal** já é feito hoje pelo relatório diário
  (`app/faturamento/services/faturamento_diario_teams_service.py`) via ponte
  `POST {TEAMS_FUNCTION_URL}/api/notify` + `conversation_id` do grupo. Para esta feature
  usaremos um **Incoming Webhook / Workflow do Teams** (URL simples que aceita POST JSON),
  configurável na UI — desacopla da ponte do bot e é "pasteável" pelo operador.

## 2. Decisões aprovadas

| # | Decisão | Escolha |
|---|---------|---------|
| D1 | Canais | **E-mail + Teams** |
| D2 | Destino Teams | **Um canal fixo** para todos os avisos (URL única) |
| D3 | Granularidade | **1 aviso por CNPJ por rodada**, juntando as notas novas daquele cliente |
| D4 | Onde configurar | Card novo na **Central Fiscal** → tela de cadastro (CNPJ + e-mails) + campo do canal Teams |
| D5 | Gatilho | Fim da sync Odoo, sobre `nfs_novas` cujo CNPJ está cadastrado e ativo |
| D6 | Não repetir | Registro de envios por NF (idempotência) |
| D7 | Falha isolada | Disparo NUNCA quebra o faturamento |
| D8 | Envio do e-mail | **1 e-mail por CNPJ com todos os endereços em cópia** (1º em `to`, demais em `cc`) |

## 3. Arquitetura

O recurso é **dono do módulo Faturamento** (model + serviço + tela/rota/CRUD), com um
**atalho (card)** na Central Fiscal do módulo Recebimento e **um gancho** na sync Odoo.

```
Sync Odoo (faturamento_service.importar_faturamento_odoo)
  └─ [SYNC 5 NOVA] alerta_faturamento_service.processar_alertas(nfs_novas)
        1. lê cabeçalhos (RelatorioFaturamentoImportado) das nfs_novas
        2. filtra por CNPJ cadastrado + ativo  (AlertaFaturamentoCnpj)
        3. remove NFs já avisadas             (AlertaFaturamentoEnviado)
        4. agrupa por CNPJ  → 1 mensagem/cliente
        5. envia e-mail (lista do CNPJ) + Teams (canal fixo)
        6. grava AlertaFaturamentoEnviado por (numero_nf, canal)
     (try/except total — erro só loga, não propaga)

Central Fiscal (card novo) ──▶ faturamento: tela CRUD de CNPJs + config Teams
```

Unidades isoladas, cada uma com um propósito:
- `app/faturamento/models.py` — 3 models novos (dados).
- `app/faturamento/services/alerta_faturamento_service.py` — lógica de disparo (sem UI).
- `app/faturamento/routes/alertas_faturamento.py` (novo blueprint `alertas_faturamento_bp`,
  prefix `/faturamento/alertas`) — CRUD + config + teste. *(Se o módulo hoje só tem
  `routes.py` monolítico, criar o subpacote `routes/` seguindo o padrão de outros módulos;
  a decisão final fica no plano.)*
- `app/templates/faturamento/alertas/` — telas.
- Edição pontual em `faturamento_service.py` (1 chamada) e em `central_fiscal.html` (1 card).

## 4. Dados (3 tabelas novas)

**`alerta_faturamento_cnpj`** — cadastro (o "local para inserir os CNPJs e e-mails"):

| Coluna | Tipo | Nota |
|--------|------|------|
| `id` | PK | |
| `cnpj` | String(20), UNIQUE, index | normalizado (só dígitos) na gravação |
| `nome_cliente` | String(255), null | preenchido do último cabeçalho conhecido (conveniência) |
| `emails` | Text | lista separada por `;` ou `,` (parse tolerante) |
| `ativo` | Boolean, default True | liga/desliga por CNPJ |
| `criado_em` / `criado_por` / `atualizado_em` | auditoria | `agora_utc_naive` |

**`alerta_faturamento_config`** — configuração global (1 linha):

| Coluna | Tipo | Nota |
|--------|------|------|
| `id` | PK | sempre 1 linha (get-or-create) |
| `teams_webhook_url` | String(500), null | canal fixo do Teams (D2) |
| `teams_ativo` | Boolean, default False | liga/desliga Teams sem apagar a URL |
| `email_ativo` | Boolean, default True | liga/desliga e-mail globalmente |
| `atualizado_em` / `atualizado_por` | auditoria | |

**`alerta_faturamento_enviado`** — log/idempotência (D6):

| Coluna | Tipo | Nota |
|--------|------|------|
| `id` | PK | |
| `numero_nf` | String(20), index | |
| `cnpj` | String(20), index | |
| `canal` | String(10) | `email` / `teams` |
| `status` | String(10) | `ok` / `erro` |
| `detalhe` | Text, null | erro/message_id |
| `enviado_em` | DateTime | |
| — | UNIQUE(`numero_nf`,`canal`) | trava anti-duplicata |

## 5. Gatilho (hook na sync Odoo)

Em `importar_faturamento_odoo`, após as SYNCs existentes (junto ao bloco pós-persistência,
onde `nfs_novas` já existe e o commit do faturamento já ocorreu), adicionar:

```python
# 🚀 SINCRONIZAÇÃO 5: Alertas de faturamento por CNPJ (e-mail + Teams)
try:
    from app.faturamento.services.alerta_faturamento_service import processar_alertas_faturamento
    if nfs_novas:
        processar_alertas_faturamento(nfs_novas)
except Exception as e:
    logger.error(f"Alertas de faturamento falharam (ignorado): {e}", exc_info=True)
```

Import lazy + try/except total = **D7** (nunca derruba a sync). Passa só a lista de
números de NF; o serviço busca os cabeçalhos (dados sempre frescos do banco, sem
threa­ding de payload pelo hook).

## 6. Serviço de alerta

`processar_alertas_faturamento(nfs_novas: list[str]) -> dict`:

1. `cabecalhos = RelatorioFaturamentoImportado.query.filter(numero_nf.in_(nfs_novas), ativo=True)`.
2. Normaliza CNPJ; agrupa cabeçalhos por CNPJ.
3. Para cada CNPJ com registro em `AlertaFaturamentoCnpj` (ativo=True):
   - Descarta NFs já em `AlertaFaturamentoEnviado` (por canal).
   - Se sobrou ≥1 NF: monta 1 mensagem (nome+CNPJ; linhas nº/data/valor/cidade-UF; total).
   - Envia e-mail (se `email_ativo` e há e-mails) e Teams (se `teams_ativo` e há URL).
   - Grava `AlertaFaturamentoEnviado` por NF×canal (ok/erro).
4. Retorna resumo (`{cnpjs: n, emails_ok: n, teams_ok: n, erros: [...]}`) para log.

Conteúdo (D3), igual nos dois canais:
```
Faturamento — <nome_cliente> (CNPJ <cnpj>)
- NF 12345 · 01/07/2026 · R$ 12.345,67 · São Paulo/SP
- NF 12346 · 01/07/2026 · R$ 2.000,00 · Campinas/SP
Total: R$ 14.345,67
```

## 7. Canais de envio

- **E-mail (D8)**: reusa `email_sender.send(to=<1º e-mail>, cc=<demais>, subject=...,
  body_html=EmailTemplates.info(...))` — **1 e-mail por CNPJ com todos os endereços em cópia**.
  Se `EmailConfig.is_configured()` for False, grava `erro` no log (não explode).
- **Teams**: `requests.post(teams_webhook_url, json={...}, timeout=15)` com card/texto simples
  (MessageCard/Adaptive básico). Timeout curto + captura de exceção → log `erro`.

## 8. UI (Central Fiscal)

- **Card novo** em `central_fiscal.html` (bloco "Relatórios" ou seção nova "Alertas"),
  `url_for('alertas_faturamento.index')`, ícone `fa-bell`/`fa-envelope`.
- **Tela `index`**: tabela de CNPJs (CNPJ, nome, e-mails, ativo, ações editar/remover/testar)
  + topo com **config Teams** (URL do canal + `teams_ativo` + `email_ativo`) + botão "testar Teams".
- **Ações** (rotas POST, `@login_required`): criar, editar, remover CNPJ; salvar config;
  testar e-mail (envia para os e-mails do CNPJ) e testar Teams (posta no canal).
- Segue o CSS de cards já usado (`fin-section-card`, `_recebimento.css`), sem novo design system.

## 9. Idempotência e segurança

- Anti-duplicata: UNIQUE(`numero_nf`,`canal`) + checagem antes de enviar (D6). Reprocessar a
  sync não reenvia.
- CNPJ normalizado (só dígitos) na gravação E na comparação (evita falha por máscara).
- `@login_required` em todas as rotas; validação de e-mails (formato) e de URL (https) no CRUD.
- Disparo isolado por try/except (D7); cada CNPJ isolado (erro num não impede os outros).

## 10. Migration

Par obrigatório (regra CLAUDE.md): `scripts/migrations/<seq>_alertas_faturamento.sql`
(DDL: 3 CREATE TABLE + índices + UNIQUE) e `..._alertas_faturamento.py` (idempotente,
`CREATE TABLE IF NOT EXISTS`, seed da linha única de `alerta_faturamento_config`). Numeração/prefixo
conferidos no plano contra `scripts/migrations/`.

## 11. Testes (TDD)

- `alerta_faturamento_service`: agrupa por CNPJ; ignora CNPJ não cadastrado/inativo; não
  reenvia NF já registrada; monta corpo com total correto; erro de canal não derruba os demais;
  `nfs_novas` vazio = no-op.
- Rotas CRUD: criar/editar/remover CNPJ; normalização de CNPJ; salvar config; testar envio.
- Idempotência: 2 execuções seguidas → 1 envio só.
- Hook: `importar_faturamento_odoo` chama o serviço com `nfs_novas` e engole exceção.

## 12. Documentação a atualizar (parte do "pronto")

- `app/faturamento/CLAUDE.md` — nova SYNC 5 + 3 models + blueprint de alertas.
- Gerar schemas JSON das 3 tabelas novas (`.claude/skills/consultando-sql/schemas/tables/`).
- Este spec + entrada no `docs/superpowers/specs/INDEX.md` + plano par em `docs/superpowers/plans/`.

## 13. Fora de escopo (YAGNI)

- Canal por CNPJ no Teams (D2 = canal único).
- Aviso por NF individual (D3 = agrupado).
- Templates de e-mail customizáveis por CNPJ; agendamento; digest diário; reenvio manual em massa.
- Tocar na ponte do bot Teams / `faturamento_diario_teams_service` (usamos webhook próprio).

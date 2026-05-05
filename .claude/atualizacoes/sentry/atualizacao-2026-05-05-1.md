# Atualizacao Sentry — 2026-05-05-1

**Data**: 2026-05-05
**Org**: nacom | **Projeto**: python-flask
**Issues avaliadas**: 32 (production unresolved)
**Issues corrigidas**: 6 (1 fix novo + 5 ja corrigidas em commits anteriores)
**Issues fora de escopo / ignoradas**: 26

## Resumo

Triagem de 32 issues abertas em producao. Aplicado 1 fix novo (PYTHON-FLASK-Q6 — guarda
`current_user.is_authenticated` em `app/templates/hora/base.html` para nao chamar
`tem_perm_hora` em `AnonymousUserMixin` na rota publica `tagplus_oauth_callback`).
Marcadas como resolved 5 issues ja corrigidas em commits anteriores ainda nao
deployadas no momento dos eventos (QG, QM, QH, QF, QC). 26 issues nao corrigiveis:
data issue Odoo persistente (Fatura 543449, 3 issues), erros XML-RPC Odoo externos
(8 issues), tmp scripts ad-hoc (2), shutdown/timeout transientes (5), erros Teams/MCP
isolados (3), erros de negocio (2), Playwright tools/browser issues (3).

---

## Issues Corrigidas

### PYTHON-FLASK-Q6: UndefinedError 'AnonymousUserMixin' has no attribute 'tem_perm_hora'
- **Frequencia**: 3 eventos, 1 usuario
- **Culprit**: `hora.tagplus_oauth_callback` (rota publica sem `@login_required`)
- **Causa raiz**: `app/templates/hora/base.html` chama `current_user.tem_perm_hora(...)`
  diretamente. Em rotas publicas (callback OAuth do TagPlus), `current_user` e
  `AnonymousUserMixin`, que nao tem `tem_perm_hora` (so existe em `Usuario`).
  Jinja levanta `UndefinedError` ao renderizar o template `oauth_result.html`
  que estende `hora/base.html`.
- **Fix**: `app/templates/hora/base.html:5-7,197` — adicionado guarda
  `{% if current_user.is_authenticated %}` ao redor de toda a `.hora-topbar`
  (o navbar com `tem_perm_hora`). Anonymous users nao veem nada do navbar
  HORA, o que e o comportamento desejado em rota publica.
- **Status**: resolved no Sentry

### PYTHON-FLASK-QG / QH: DetachedInstanceError em refresh_if_needed
- **Frequencia**: 38 + 1 = 39 eventos
- **Culprit**: `app.hora.workers.backfill_worker.processar_backfill_job` ->
  `oauth_client.refresh_if_needed` (linha 68 antiga: `token = self.conta.token`)
- **Causa raiz**: backfill chama `db.session.close()` + `db.engine.dispose()` em
  recovery de SSL drop; `self.conta` fica DETACHED; lazy load de `conta.token`
  explode.
- **Fix ja aplicado em commit `2bbfcf23` (`feat(hora/tagplus): ... fix detached session`)**:
  `app/hora/services/tagplus/oauth_client.py:38-66` — novo metodo
  `_ensure_conta_attached()` re-busca a conta da sessao corrente via
  `db.session.get(HoraTagPlusConta, self._conta_id)`. Chamado antes de cada
  acesso a `self.conta.*`. Linha 105-114: query explicita por `conta_id` em vez
  de `self.conta.token` (lazy load).
- **Status**: resolved no Sentry (eventos eram da release pre-fix `6c4dab02` e
  `c7af1834`; release atual `2bbfcf23` ja contem o fix).

### PYTHON-FLASK-QM: DetachedInstanceError em _upsert_emissao_nfe
- **Frequencia**: 3 eventos
- **Culprit**: `backfill_service._upsert_emissao_nfe` (linha 326: `conta_id=conta.id`)
- **Causa raiz**: mesmo padrao — `conta` passado pode estar DETACHED apos
  recovery; acesso a `conta.id` levanta DetachedInstanceError.
- **Fix ja aplicado em commit `2bbfcf23`**:
  `app/hora/services/tagplus/backfill_service.py:346-361` — snapshot defensivo
  de `conta.id` via `int(conta.id)` com fallback para `_sa_inspect(conta).identity[0]`
  caso o acesso direto falhe.
- **Status**: resolved no Sentry (release pre-fix `b6c17646`; release atual ja contem fix).

### PYTHON-FLASK-QF: PendingRollbackError em _atualizar_motos_dos_itens_existentes
- **Frequencia**: 4 eventos
- **Culprit**: `backfill_service._corrigir_chassi_motor_invertido` -> UniqueViolation
  `hora_moto_numero_motor_key` quando moto-bug ainda ocupa o motor que sera
  atribuido a moto correta.
- **Fix ja aplicado em commit `b6c17646` (`fix(hora/tagplus): backfill nao para mais em 50 NFs nem viola UNIQUE`)**:
  `app/hora/services/tagplus/backfill_service.py:1612-1618` — pre-passo libera
  `numero_motor` da moto-bug ANTES de criar/atualizar a moto correta.
- **Status**: resolved no Sentry (release pre-fix `6c4dab02`; release atual ja contem fix).

### PYTHON-FLASK-QC: IntegrityError uq_hora_venda_divergencia_tipo_chassi
- **Frequencia**: 5 eventos, 1 usuario
- **Culprit**: `venda_service._registrar_divergencia` -> INSERT puro em
  `HoraVendaDivergencia` violava UNIQUE em re-execucao do backfill.
- **Fix ja aplicado em commit `b6c17646`**: `app/hora/services/venda_service.py:119-186`
  — agora UPSERT idempotente: procura divergencia existente e atualiza valores;
  preserva resolucoes do operador.
- **Status**: resolved no Sentry (release pre-fix `e7d00c35`; release atual ja contem fix).

---

## Issues Fora de Escopo / Ignoradas

### Data issue Odoo persistente (Fatura 543449 — NF-e 146596)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-HZ | 33 | "Fatura 543449 desbalanceada apos correcao! Diferenca 79.80 muito grande para rebalancear automaticamente". Worker `processar_itens_baixa_job` re-tenta a cada batch e re-loga. |
| PYTHON-FLASK-J0 | 28 | Mesma fatura 543449 — `account.move.action_post` falha porque diario "VENDA DE PRODUCAO" nao tem conta padrao para arredondar diferenca de 79.80. |
| PYTHON-FLASK-QA | 9 | Mesma fatura — `account.move.line.reconcile` retorna "Lancamento ja conciliado". |

**Acao**: nao corrigivel via codigo. Requer ajuste de configuracao Odoo (conta
padrao no diario VND) ou ajuste manual da fatura 543449 no Odoo. Recorrente
porque o job continua tentando processar os mesmos itens (5984-5995, 6006-6008).

### Erros Odoo XML-RPC externos (infra do CIEL — fora de escopo)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-BJ | 54 | `503 Service Unavailable` em sincronizacao Odoo. |
| PYTHON-FLASK-BK | 48 | `503 Service Unavailable` em `account.move.line.search_read`. |
| PYTHON-FLASK-51 | 5 | `Request-sent` em `res.partner.search` (`leitura_pedidos.inserir_odoo`). |
| PYTHON-FLASK-QQ | 4 | `Request-sent` em `product.product.search_read`. |
| PYTHON-FLASK-QZ | 1 | Timeout 120s em `res.partner.search_read` (regime tributario). |
| PYTHON-FLASK-QT | 1 | `503` ao buscar CTe por chave. |
| PYTHON-FLASK-QS | 1 | `503` em `l10n_br_ciel_it_account.dfe.search_read`. |
| PYTHON-FLASK-QP | 1 | `Request-sent` em autenticacao Odoo. |
| PYTHON-FLASK-QN | 1 | `Request-sent` em autenticacao Odoo. |

**Acao**: nada acionavel. Erros transientes do Odoo do CIEL (503s, request-sent
mid-flight). Workers tem retry com backoff.

### Erros de negocio Odoo (raise intencional)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-Q8 | 1 | `sale.order.action_cancel` retorna ValueError "too many values to unpack" — bug Odoo Brasil em record set, nao corrigivel local. |
| PYTHON-FLASK-Q4 | 1 | "Esta Nota nao pode ser alterada pois esta sendo processada" em `hora.venda_nfe_cancelar` — race condition NFe TagPlus, validacao de negocio. |
| PYTHON-FLASK-Q3 | 1 | "Nao ha nenhuma linha faturavel" em `purchase.order.action_create_invoice` — validacao de negocio Odoo (recebimento incompleto). |

### Tmp scripts ad-hoc (Render Shell `<stdin>` / `<string>`)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-Q5 | 2 | Script ad-hoc usando `WHERE odoo_purchase_order_id=40773` (int) numa coluna que e `String(50)` — bug do script, nao do app. |
| PYTHON-FLASK-Q2 | 1 | Script ad-hoc com import errado `app.recebimento.models.produto_fornecedor_depara` — caminho real e `app.recebimento.models` (modulo unico). |

### SSL/Connection transientes

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-QY | 1 | `SSL connection has been closed unexpectedly` ao processar CTe 42148. Worker tem recovery por SSL drop (igual ao QG/QF acima); ocorrencia unica. |
| PYTHON-FLASK-Q1 | 1 | UniqueViolation `ix_picking_recebimento_odoo_picking_id` em `validacao_nf_po.executar_validacao_manual` — race entre 2 workers concorrentes. Provavelmente isolado. |

### Playwright / Browser tools (MCP Playwright)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-QW | 2 | `Page.evaluate: SyntaxError: Illegal return statement` em `tools/call browser_evaluate_js`. Erro do JS passado pelo agente. |
| PYTHON-FLASK-QX | 1 | `Page.goto: Cannot navigate to invalid URL` — agente passou URL invalida. |
| PYTHON-FLASK-QV | 1 | `Locator.fill: Timeout 30000ms` em `browser_type` — elemento nao apareceu. |

### Teams / Agente / consolidacao

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-QR | 1 | "Task was destroyed but it is pending!" em `auth.login` — asyncio shutdown race, transitorio. |
| PYTHON-FLASK-QK | 1 | TEAMS-ASYNC: 2 tentativas falharam — generic erro Teams. |
| PYTHON-FLASK-QJ | 1 | TEAMS-STREAM: timeout aguardando resposta do agente. |
| PYTHON-FLASK-Q9 | 1 | MEMORY_CONSOLIDATOR: UniqueViolation `uq_user_memory_path` durante autoflush. Race entre consolidator e save_memory tool. |

---

## Arquivos modificados

- `app/templates/hora/base.html` — guarda `current_user.is_authenticated` ao redor da
  navbar HORA para evitar `tem_perm_hora` em `AnonymousUserMixin` (PYTHON-FLASK-Q6).

## Metricas

- Issues abertas antes: 32
- Issues fechadas pela triagem: 6 (1 fix novo + 5 ja corrigidas em deploys anteriores)
- Issues abertas depois (esperado): 26
- Reducao: 18.8%

## Observacoes

1. **Q6 fix**: o template `hora/base.html` agora guarda toda a navbar com
   `current_user.is_authenticated`. Como anonymous user em rota publica
   (`tagplus_oauth_callback`) nao tem permissoes, nao ver o navbar e o comportamento
   desejado. Outros templates HORA com `tem_perm_hora` (estoque, modelos, etc.) sao
   acessados apenas via rotas com `@require_hora_perm` ou `@login_required`, entao
   nao precisam do mesmo guard.

2. **Issues ja-fixed em commits anteriores (QG/QM/QH/QF/QC)**: foram triadas como
   "resolved" em vez de aguardar deploy automatico. As releases dos eventos eram
   `6c4dab02`, `c7af1834`, `b6c17646`, `e7d00c35` — todas anteriores ao fix em
   `2bbfcf23` (atual main). Sentry "resolved" agora; reabrira automaticamente se
   reaparecer numa release nova.

3. **Fatura 543449 (HZ/J0/QA, 70 eventos juntos)**: maior fonte de ruido. Necessita
   intervencao Odoo. Worker `baixa_titulos_jobs` re-tenta indefinidamente. Sugestao
   futura (fora desta triagem): adicionar circuito breaker que detecta
   "desbalanceada apos correcao" e marca o item como erro permanente para parar o
   loop de retentativas.

4. **Tmp scripts (Q5/Q2)**: erros de scripts manuais executados em Render Shell.
   Sentry captura via `excepthook` global. Nao sao bugs de codigo; podem ser
   filtrados via `before_send` se incomodarem (decisao do usuario).

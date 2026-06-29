# Atualizacao Sentry — 2026-06-29-1

**Data**: 2026-06-29
**Org/Projeto**: `nacom` / `python-flask` (regionUrl `https://us.sentry.io`)
**Issues avaliadas**: 46 (`is:unresolved environment:production`, janela 30d, ordenadas por frequencia)
**Issues corrigidas (marcadas resolved)**: 2
**Issues fora de escopo**: 1 (feature incompleta exige migration)
**Issues ignoradas/documentadas**: 43
**Arquivos modificados**: 1

---

## Resumo

Triagem de 46 issues abertas. **1 fix NOVO de codigo** (Z8 — `consultar_quants.py`,
script de skill: `json.dumps` estourava `TypeError` com chave-tupla no dict `agregado`)
e **1 ja-corrigida em codigo** (Z2 — `nf_qpa_adapter.py`, regressao do fix da triagem
2026-06-22, evento de release anterior ao fix). Ambas marcadas `resolved` no Sentry com
comentario de rastreio. As 43 restantes ficam fora do escopo de bug tecnico simples:
billing/overload Anthropic, **cluster de 1 unica migration pendente** (`veiculos.custo_km`,
6 issues / ~57 eventos), TagPlus OAuth (infra externa), schema Odoo (`l10n_br...dfe.state`),
e diversos transientes/negocio/scripts.

---

## Issues Corrigidas (marcadas `resolved`)

### PYTHON-FLASK-Z8: TypeError: keys must be str... not tuple — FIX NOVO
- **Frequencia**: 1 evento, 0 usuarios (script de skill, baixa frequencia mas fix trivial e seguro)
- **Culprit**: `consultar_quants.py in _print_quants` (skill `consultando-quant-odoo`)
- **Causa raiz**: com `--agregar --json`, o dict `res['agregado']` e indexado por
  **tupla** `(cod, empresa)`. O caminho texto desempacota a tupla (linha 169), mas o
  caminho JSON chama `json.dumps(res, ...)` — e `json.dumps` rejeita chaves do tipo tupla
  (`keys must be str, int, float, bool or None, not tuple`). So quebra com `--json`.
- **Fix**: `.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py:_print_quants`
  — no ramo `formato == 'json'`, serializa uma **copia rasa** com a chave achatada em
  `"cod|empresa"` (so quando ha chaves-tupla). O caminho texto (nao-JSON) fica **intocado**
  (continua usando a tupla para ordenar/desempacotar).
- **Verificacao**: reproducao inline com a estrutura exata do evento Sentry — codigo antigo
  levanta o `TypeError` reportado; codigo novo serializa OK (chaves achatadas, valores
  preservados). `py_compile` OK.
- **Sentry**: marcada `resolved` + comentario.

### PYTHON-FLASK-Z2: InvalidOperation: ConversionSyntax — JA CORRIGIDA EM CODIGO
- **Frequencia**: 16 eventos, 1 usuario (substatus `regressed`)
- **Culprit**: `motos_assai.faturamento_upload_nf` -> `nf_qpa_adapter.py:importar_nf_qpa`
- **Causa raiz**: `Decimal(str(resultado.get('valor_total', 0)))` cru estourava
  `decimal.InvalidOperation (ConversionSyntax)` quando `valor_total` vinha vazio ou
  nao-numerico (ex.: PDF de Carta de Correcao enviado ao endpoint de NF).
- **Estado em codigo**: **JA RESOLVIDO** pelo commit `181aba751` (guards de import NF
  Q.P.A.). O working tree usa `_to_decimal_safe(resultado.get('valor_total'))` no
  construtor de `AssaiNfQpa` (linha 411) — helper que devolve `Decimal('0')` quando a
  conversao falha (deixando o match seguir como `NAO_RECONCILIADO`). Nao ha mais nenhum
  `Decimal(str(...valor_total...))` cru no caminho. Os divisores `valor_total / n` operam
  sobre o Decimal ja saneado.
- **Por que reabriu**: o evento Sentry e do release `e2dd3bb5` (anterior ao deploy do fix);
  a issue tinha sido resolvida na triagem 2026-06-22 e **regrediu** com eventos pre-fix.
- **Sentry**: marcada `resolved` novamente + comentario de rastreio (commit + release).

---

## Fora de Escopo (feature incompleta — exige migration)

### PYTHON-FLASK-YT: 'cadastro_pendente' is an invalid keyword argument for CarviaModeloMoto
- **Frequencia**: 2 eventos, 1 usuario | `carvia.api_anexar_nf_cotacao`
- **Diagnostico**: `cotacao_v2_routes.py:2089` e `:2989` instanciam
  `CarviaModeloMoto(..., cadastro_pendente=True)`, mas o model
  (`app/carvia/models/config_moto.py:29`) **nao declara a coluna `cadastro_pendente`**.
  Feature de "cadastro pendente" de modelo de moto **incompleta**: falta a migration
  (`ALTER TABLE carvia_modelos_moto ADD COLUMN cadastro_pendente`) + mapeamento no model.
- **Por que nao corrigi**: requer migration (out of scope) E o fix correto NAO e remover o
  kwarg (isso quebraria a feature silenciosamente). Decisao de modelo/migration pendente —
  igual ao reportado na triagem 2026-06-22.

---

## Ignoradas / Documentadas (43)

### Cluster: 1 migration pendente (`veiculos.custo_km`) — 6 issues, ~57 eventos
A coluna `custo_km` esta no model (`app/veiculos/models.py:17`) mas **ausente em prod**
(migration nao aplicada / fora do `build.sh`). Cascata:
- **YQ / YP** — `ProgrammingError UndefinedColumn: veiculos_1.custo_km does not exist`
  (`monitoramento.listar_entregas`, `pedidos.lista_pedidos`)
- **YN / YM / YS / YR** — `InFailedSqlTransaction` (cascata da transacao abortada pelo
  UndefinedColumn em portaria.historico / portaria.dashboard / monitoramento.listar_entregas)
- **Acao**: aplicar a migration de parametros de custo do veiculo em prod (responsabilidade
  dev/migration, NAO do cron). Ja documentado na triagem 2026-06-22.

### Anthropic API — billing / overload / 5xx (infra externa)
- **Y2 / Y4 / Z5** (48/40/35 ev) — `credit balance is too low` nos workers shadow do agente
  (`step_judge`, `triage_shadow`, `plan_verifier`). Billing — nao acionavel por codigo.
- **R5** (46 ev) — `OverloadedError 529` (chat sonnet). **YJ** (38 ev) — `InternalServerError 500`
  (`summarize_session_job`). Transientes do provedor.

### TagPlus OAuth (infra externa / credencial)
- **ZC / ZD** (`HTTPError 400 oauth2/token`), **ZB / ZE** (`refresh_token invalido`) —
  `hora.venda_nfe_*`. Credencial/refresh token TagPlus expirado — renovacao operacional,
  nao bug de codigo.

### Schema Odoo (ERP externo CIEL IT)
- **YV** (23 ev) — `Invalid field 'state' on model 'l10n_br_ciel_it_account.dfe'`
  (Odoo XML-RPC). Schema do ERP mudou — fora do nosso codigo.

### Outras (documentadas, sem acao de codigo)
- **Z6** (66 ev) — `TypeError immutabledict is not a sequence` (`__main__ in main`, worker/CLI;
  sem frame de codigo de aplicacao acionavel no evento — provavelmente shutdown/boot do worker).
- **Z1** (5 ev) — `DataError value too long varchar(64)` (`adhoc_capture_job`) — limite de
  coluna; correcao real = truncar na origem OU migration (borderline, baixo volume).
- **E7** (13 ev) — `[MEMORY_MCP] Texto nao encontrado` — comportamento do agente (old_str stale).
- **Z4** (4 ev) — LLM JSON parse `Extra data` (`carvia.importar`) — saida de modelo malformada,
  ja logada/handled (nao crash de request).
- **YY** (16 ev) — `PendingRollbackError / UniqueViolation` (`hora.nfs_upload_lote`) — duplicata
  de chave (regra de negocio / dado duplicado).
- **Z2-relacionadas / scripts ad-hoc**: Z8 ja corrigida acima; **Z0 / YZ / YB** (subprocess CLI
  do Agent SDK), **HC / G2** (circuit breaker — informativos), **ZM** (SMTP auth), **ZK / ZF**
  (rede OpenClaw / broken pipe), **ZN / ZJ** (autoflush/FK em workers HORA), **ZH** (openpyxl
  IllegalCharacter), **Z3 / ZA** (N+1 perf — refactor), **RH** (ModeloPendenteError — negocio),
  **ZG** (operator `integer ~~* unknown` — type/cast, baixo volume), **YX** (403 simulador),
  **YW** (autoflush CTe), **XY** (.msg ausente /tmp efemero), **M6 / HZ / J8 / Z7** (negocio/
  validacao/404), **ZM/...** — todas < criterio de fix tecnico simples ou fora de escopo.

---

## Metricas

- Issues abertas antes (unresolved/production, 30d): 46
- Marcadas resolved nesta triagem: 2 (Z8 fix novo + Z2 ja-corrigida/regressao)
- Issues abertas depois: 44
- Fix de codigo NOVO: 1 (Z8)
- Arquivos modificados: 1 (`.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py`)

## Nota de continuidade

- **Z2** e **cluster custo_km** e **YT** repetem a triagem 2026-06-22 (`atualizacao-2026-06-22-1.md`):
  Z2 regrediu por eventos pre-fix (codigo OK); custo_km e YT seguem pendentes de migration
  (acao dev, fora do cron). Nenhuma acao de codigo nova nesses.

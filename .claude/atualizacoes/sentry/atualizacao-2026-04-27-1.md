# Atualizacao Sentry — 2026-04-27-1

**Data**: 2026-04-27
**Org**: nacom | **Projeto**: python-flask
**Issues avaliadas**: 20
**Issues corrigidas**: 2
**Issues fora de escopo / ignoradas**: 18

## Resumo

Triagem das 20 issues abertas em producao. Corrigidos 2 bugs tecnicos:
PYTHON-FLASK-PF (LIKE em coluna Integer no portaria.historico / api_embarques) e PYTHON-FLASK-P3 (CarviaCliente sem atributo cnpj — ja resolvido em commit anterior). 18 issues nao corrigiveis: migrations pendentes (4), erros Odoo externos (6), erros de negocio (3), shutdown race condition (3) e perf alerts (2).

---

## Issues Corrigidas

### PYTHON-FLASK-PF: ProgrammingError: operator does not exist: integer ~~ unknown
- **Frequencia**: 1 evento, 1 usuario (rafael@nacomgoya.com.br)
- **Culprit**: `portaria.historico` (route)
- **Causa raiz**: `Embarque.numero` e `db.Column(db.Integer)`, mas o codigo aplicava `.like(f'%{termo}%')` direto. PostgreSQL rejeita LIKE em coluna inteira com operador `~~`.
- **Fix**:
  - `app/portaria/models.py:212` — wrap `Embarque.numero.like(...)` com `db.cast(Embarque.numero, db.String).ilike(...)`
  - `app/portaria/routes.py:626` — mesmo fix em `api_embarques` (mesma classe de bug, mesma rota raiz)
- **Status**: resolved no Sentry

### PYTHON-FLASK-P3: AttributeError: 'CarviaCliente' object has no attribute 'cnpj'
- **Frequencia**: 1 evento, 1 usuario (rafael@nacomgoya.com.br)
- **Culprit**: `carvia.api_previnculo_linhas_candidatas` -> `previnculo_service.listar_candidatos_extrato`
- **Causa raiz**: codigo acessava `cotacao.cliente.cnpj`, mas `CarviaCliente` nao tem campo `cnpj` — CNPJ vive em `CarviaClienteEndereco`.
- **Fix**: ja corrigido em commit `f1c04813` (2026-04-23 15:52 BRT) — `previnculo_service.py:248-257` usa `cotacao.endereco_destino.cnpj` com fallback `cotacao.endereco_origem.cnpj`. O evento Sentry e de 2026-04-23 14:00 BRT, antes do deploy do fix.
- **Status**: resolved no Sentry (verificado que codigo atual nao reproduz)

---

## Issues Ignoradas / Fora de Escopo

### Migrations pendentes (constraint mismatch — NAO corrigir, deploy de migration resolve)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-PJ | 3 | CheckViolation `ck_carvia_pedido_status` ao escrever em `carvia_pedidos.status`. Migration `remover_embarcado_carvia_pedido_status.sql` e/ou `renomear_status_faturado_cotado_carvia_pedidos.sql` precisam estar aplicadas em prod alinhadas com o estado do codigo (`('ABERTO','COTADO','FATURADO','CANCELADO')`). |
| PYTHON-FLASK-PK | 1 | IntegrityError autoflush em `_marcar_pedidos_embarcado` — mesma raiz da PYTHON-FLASK-PJ. |
| PYTHON-FLASK-E1 | 12 | "PO X nao esta mais confirmada (state=to approve)" — mensagem de validacao de negocio (NAO bug). |
| PYTHON-FLASK-P8 | 2 | "Nenhum match encontrado para consolidacao" — validacao de negocio na consolidacao PO (recebimento). |

### Erros Odoo externos (fault XML-RPC, infra do CIEL — fora de escopo)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-DG | 11 | sale.order(72471) deletado no Odoo — record nao existe. |
| PYTHON-FLASK-DJ | 7 | Falha emissao CTe SSW (worker carvia). |
| PYTHON-FLASK-PR | 4 | Erro stock.picking.search XML-RPC. |
| PYTHON-FLASK-P5 | 2 | Generic Fault XML-RPC do Odoo. |
| PYTHON-FLASK-P6 | 2 | Erro l10n_br_ciel_it_account.dfe.line.search_read. |
| PYTHON-FLASK-6X | 14 | Polling expirou apos 600s — VCD2669253. Job `calcular_impostos_odoo` esperando estado externo. |

### Erros de negocio (raise intencional)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-E2 | 12 | Traceback de `consolidar_pos` — ValueError no fluxo de consolidacao (validacao). |
| PYTHON-FLASK-P7 | 2 | Mesmo Traceback "Nenhum match para consolidacao" (recebimento). |

### Race conditions de shutdown (rework, nao trivial)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-PP | 4 | SessionStore mirror_error: cannot schedule new futures after shutdown — ThreadPoolExecutor fechado durante shutdown do worker Teams. |
| PYTHON-FLASK-PN | 4 | Idem (log explicito do mesmo evento). |
| PYTHON-FLASK-PM | 1 | Idem ao salvar tar.gz no S3 mirror. |
| PYTHON-FLASK-PG | 1 | TypeError 'AppContext' nao suporta async context manager — em script externo (`<string>` / __main__ in run). Sem stacktrace acionavel. |

### Performance alerts (fora de escopo de correcao automatica)

| Issue | Eventos | Detalhe |
|-------|---------|---------|
| PYTHON-FLASK-PE | 6 | Consecutive DB Queries — `pedidos.lista_pedidos` (mesmo da triagem 2026-04-06). |
| PYTHON-FLASK-PQ | 1 | Consecutive HTTP — `validacao_nf_po.validar_nf_po`. |

---

## Arquivos modificados

- `app/portaria/models.py` — cast Integer -> String antes de ilike (PYTHON-FLASK-PF)
- `app/portaria/routes.py` — cast Integer -> String antes de ilike (mesma classe)

## Metricas

- Issues abertas antes: 20
- Issues fechadas pela triagem: 2
- Issues abertas depois (esperado): 18 (das quais 4 sao migrations pendentes que se resolvem com deploy)

## Observacoes

1. **PYTHON-FLASK-PJ / PK** sao bloqueadas em estado de migration. As migrations existem em `scripts/migrations/`:
   - `remover_embarcado_carvia_pedido_status.sql` (alvo: `('ABERTO','COTADO','FATURADO','CANCELADO')`)
   - `renomear_status_faturado_cotado_carvia_pedidos.sql` (alvo intermediario sem FATURADO)

   Estado atual do codigo escreve **FATURADO**. Aplicar a primeira em prod resolve. Nao foi aplicada por essa triagem (regra: NAO corrigir migrations).

2. **Race conditions de shutdown (PP/PN/PM)** ocorrem no worker Teams ao salvar mirror em S3 enquanto interpretador esta sendo finalizado. Workaround real seria flush sincrono no atexit hook ou deixar de usar ThreadPoolExecutor mirror — refactor maior, fora do escopo.

# Odoo — Guia de Desenvolvimento

Integracao bidirecional com Odoo ERP via XML-RPC. API-only: sem models SQLAlchemy proprios — le/escreve models de outros modulos (8+). Modulo mais consumido do sistema (37+ arquivos externos importam).

---

## Patterns de Desenvolvimento

### P1: Anti-Detach — Extrair Dados ORM Antes de Operacoes Longas

**Problema**: Operacoes Odoo demoram 60-180s. SQLAlchemy expira a sessao → `"Instance <X> is not bound to a Session"`.

**Solucao**: Extrair valores simples (int, str) de objetos ORM ANTES da operacao longa. No final, re-buscar com `db.session.get()`.

```python
# ANTES da operacao longa (CORRETO)
frete_fatura_id = frete.fatura_frete_id
frete_numero_fatura = frete.fatura_frete.numero_fatura if frete.fatura_frete else None

# ... operacao Odoo de 180s ...

# DEPOIS: re-buscar com sessao nova
frete = db.session.get(Frete, frete_id)
frete.odoo_invoice_id = invoice_id
```

**Fonte**: `app/fretes/services/lancamento_odoo_service.py:728-736`, `app/fretes/services/lancamento_despesa_odoo_service.py`

### P2: Fire-and-Polling para Operacoes > 30s

**Problema**: HTTP timeout (~30s) < duracao real (5-10 min).

**Solucao**: Enqueue RQ → Worker processa → Redis armazena progresso → Frontend polls.

1. `enqueue_job(func, *args, queue_name='recebimento', timeout='15m', retry=Retry(max=3, interval=[30,120,480]))`
2. Worker executa N passos, atualiza Redis: `redis.setex(f'progresso:{id}', TTL, json.dumps({etapa, total, percentual}))`
3. Frontend polls: `GET /status/<id>` a cada 2-5s
4. Lock Redis (`SET nx, ex=1800`) evita duplicacao

**Quando usar**: Qualquer operacao Odoo com multiplos writes sequenciais (ex: criar PO + linhas + impostos + confirmar + criar invoice + confirmar).

**Fonte**: `app/recebimento/services/recebimento_fisico_service.py:482-497`, `app/recebimento/workers/recebimento_lf_jobs.py:28-53`

### P3: Timeout Adaptativo com Reconnect

**Problema**: `socket.setdefaulttimeout()` so afeta sockets NOVOS. Mudar timeout sem reconnect nao tem efeito.

**Solucao**: `timeout_override` em `execute_kw()` faz: `self._models = None` (forca reconnect) → `setdefaulttimeout(novo)` → executa → `finally: restaura timeout + self._models = None`.

- Default: 90s
- Override maximo: 180s (ETAPA 6 do lancamento de frete)
- NUNCA reduzir abaixo de 30s

**Fonte**: `app/odoo/utils/connection.py:156-236`

### P4: Batch Fan-Out (N Queries → Join em Memoria)

**Problema**: Odoo XML-RPC nao suporta JOINs complexos.

**Solucao**:
1. Coletar TODOS os IDs de uma colecao: `set()`
2. 1 batch read: `search_read([('id', 'in', list(ids))])`
3. Dict cache: `{f['id']: f for f in faturas}`
4. JOIN em memoria usando os dicts

```python
# Faturamento: 6 queries batch → 6 dicts → join em memoria
cache_faturas = {f['id']: f for f in faturas}
cache_clientes = {c['id']: c for c in clientes}
cache_produtos = {p['id']: p for p in produtos}
# ... processar usando caches
```

**Anti-pattern**: N+1 queries individuais (100 pedidos x 6 queries = 600 chamadas → 6 com batch).

**Fonte**: `app/odoo/services/faturamento_service.py:83-198`, `app/odoo/services/carteira_service.py` (batch de 100 pedidos)

### P5: Checkpointing — Commit entre Fases Independentes

**Problema**: Sync completa tem 3+ fases. Se fase posterior falha, fases anteriores devem persistir.

**Solucao**: `db.session.commit()` ENTRE fases. Exemplo: sync integrada commita faturamento + status ANTES de iniciar carteira.

**Regra**: SEMPRE faturamento primeiro, depois carteira. Inverter causa perda de saldos.

**Fonte**: `app/odoo/services/sincronizacao_integrada_service.py:70-117`

### P6: Retomada de Processo — Verificar Estado Antes de Recriar

**Problema**: Processo de 16 etapas falhou na etapa 11. Reexecutar nao deve recriar PO (etapa 6).

**Solucao**: `_verificar_lancamento_existente()` busca PO/Invoice existentes no Odoo ANTES de iniciar. Retorna `continuar_de_etapa` (0 = novo, 7+ = retomar).

**Campos persistidos entre etapas**: `dfe_id`, `purchase_order_id`, `invoice_id` — em variaveis locais (nao ORM, ver P1).

**Fonte**: `app/fretes/services/lancamento_odoo_service.py:326-357`

### P7: Commit Antes de Operacao Longa ao Odoo

**Problema**: Manter conexao DB aberta durante 180s de chamada Odoo esgota o pool.

**Solucao**: `db.session.commit()` ANTES de `execute_kw()` com timeout longo. Libera a conexao para outros processos.

**Fonte**: `app/fretes/services/lancamento_odoo_service.py:1509-1512,1630-1633`

---

## Gotchas

| Gotcha | Detalhe | Fonte |
|--------|---------|-------|
| `False` do Odoo ≠ `None` Python | many2one retorna `[id, name]` ou `False`. Converter `False` → `None` | `dfe_utils.py:424-426` |
| CB so conta erros especificos | Keywords: `timeout`, `timed out`, `connection refused`, `connection reset`. Erros de negocio NAO abrem circuit | `circuit_breaker.py:161-170` |
| Incoterm RED muda endereco | Se incoterm = `[RED]` ou ID 16 → endereco vem de `carrier_id/l10n_br_partner_id`, NAO do `partner_shipping_id` | `carteira_mapper.py:321-406` |
| Prefixos Odoo hardcoded | `is_pedido_odoo()` verifica `VSC`, `VCD`, `VFB`. Nova empresa = atualizar `carteira_service.py:64` | `carteira_service.py:40-65` |
| Socket timeout e GLOBAL | `setdefaulttimeout()` afeta TODAS conexoes do processo (nao so Odoo) | `connection.py:60,78,191` |
| Sem models proprios | Este modulo ESCREVE em 8+ models de outros modulos. NUNCA adicionar model aqui | Todos os services |
| Imports LAZY obrigatorios | Models de outros modulos importados DENTRO dos metodos (evita circular import) | Todos os services |
| Ordem de sync | SEMPRE faturamento primeiro, carteira depois. Inverter perde saldos | `sincronizacao_integrada_service.py:70-106` |
| l10n_br _compute stale via XML-RPC | Campos `nfe_infnfe_*` NAO recomputados quando invoice criada via robo → SEFAZ 225. Somente UI (Playwright) forca recomputacao | `playwright_nfe_transmissao.py`, GOTCHAS.md |
| Odoo SPA: NUNCA networkidle | Long-polling mantem conexao aberta. Usar `domcontentloaded` + `wait_for_selector` | `playwright_nfe_transmissao.py:444` |
| IDs de UI frageis | `menu_id=124`, `action=243` mudam se Odoo reinstalar. Preferir URL minima sem eles | IDS_FIXOS.md secao "IDs de UI" |

---

## References

| Preciso de... | Documento |
|---------------|-----------|
| IDs fixos (companies, journals, pickings) | `.claude/references/odoo/IDS_FIXOS.md` |
| Gotchas operacionais (timeouts, campos) | `.claude/references/odoo/GOTCHAS.md` |
| Campos por modelo Odoo | `.claude/references/odoo/MODELOS_CAMPOS.md` |
| Padroes avancados (auditoria, batch, locks) | `.claude/references/odoo/PADROES_AVANCADOS.md` |
| Pipeline recebimento de compras (fases 1-4) | `.claude/references/odoo/PIPELINE_RECEBIMENTO.md` |
| Pipeline recebimento LF (37 etapas, Playwright) | `.claude/references/odoo/PIPELINE_RECEBIMENTO_LF.md` |
| Conversao UoM | `.claude/references/odoo/CONVERSAO_UOM.md` |
| Campos de tabelas locais | `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |

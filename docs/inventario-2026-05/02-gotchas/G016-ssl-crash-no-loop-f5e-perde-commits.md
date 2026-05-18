# G016 — SSL crash no meio do f5e_transmitir_sefaz perde commits

**Descoberta**: 2026-05-18 sub-piloto etapa D (apos G015 fix)
**Severidade**: HIGH (DB local desincroniza com Odoo — gera estado inconsistente)
**Status**: ✅ **FIX IMPLEMENTADO** (2026-05-18 sessao 2 manha) em
`app/odoo/services/inventario_pipeline_service.py`. Combinacao A+B+C:
- **A** (commit antes Playwright): linha ~1014, libera SSL antes da operacao longa
- **B** (try/except + retry + re-fetch): helper `_commit_with_retry()` linha ~161-200
  + `db.session.get(AjusteEstoqueInventario, ajuste_id_local)` apos Playwright
- **C** (TCP keepalive): ja' configurado em `config.py:115-118`
  (keepalives=1, keepalives_idle=30s, keepalives_interval=10s, keepalives_count=5)

---

## Sintoma

Durante `f5e_transmitir_sefaz` (loop Playwright transmitindo SEFAZ para
multiplas invoices), conexao SQL SSL e' fechada inesperadamente:

```
psycopg2.OperationalError: SSL connection has been closed unexpectedly
sqlalchemy.exc.PendingRollbackError: This Session's transaction has been
rolled back due to a previous exception during flush.

[SQL: UPDATE ajuste_estoque_inventario SET status=...
 fase_pipeline='F5e_SEFAZ_OK', chave_nfe='35260518...26032' WHERE id=162898]
```

Apos isso:
- Invoice 626032 SEFAZ-autorizada no Odoo (chave gravada)
- DB local: ajuste 162898 NAO atualizado (commit failed)
- Script crasha — invoices subsequentes (627348) nao sao transmitidas

## Causa raiz

Etapa D pode demorar minutos por invoice (Playwright + tentativas SEFAZ):
- Login Odoo: ~3s
- Abrir invoice, clicar transmitir: ~5s
- Aguardar SEFAZ + polling: 30-60s por tentativa
- Caso `excecao_autorizado`: ate 6+ tentativas
- Total por invoice: 1-10 minutos

Durante esse tempo, SQLAlchemy mantem session aberta. PostgreSQL/PgBouncer
SSL pode timeout/disconnect — proxima `session.flush()` ou `session.commit()`
falha com `OperationalError`.

Pior ainda: o `_registrar_op` (audit) faz autoflush, que pode causar o
PendingRollbackError mesmo antes do commit explicito.

## Estado pos-crash

DB local desincronizado com Odoo:
- Ajustes em `F5d_INVOICE_GERADA` (status='PROPOSTO')
- Invoice no Odoo: `state=posted`, `l10n_br_chave_nf` preenchida

Recuperacao manual via SQL:
```python
# Para cada invoice com chave_nf no Odoo, atualizar ajustes locais
invs = odoo.read('account.move', [inv_id], ['l10n_br_chave_nf', 'l10n_br_xml_aut_nfe'])
chave = invs[0]['l10n_br_chave_nf']
xml = invs[0]['l10n_br_xml_aut_nfe']
xml_size = len(str(xml)) if xml else 0
erro_msg = 'excecao_autorizado_xml_vazio' if xml_size == 0 else 'sefaz_ok'

UPDATE ajuste_estoque_inventario
SET status='EXECUTADO',
    fase_pipeline='F5e_SEFAZ_OK',
    chave_nfe=:chave,
    erro_msg=:erro_msg
WHERE invoice_id_odoo = :inv_id;
```

## Solucao IMPLEMENTADA (2026-05-18 sessao 2 manha)

### Opcao A: commit antes de cada Playwright (defensivo)

Em `f5e_transmitir_sefaz`, fazer `db.session.commit()` ANTES de chamar
`transmitir_nfe_via_playwright` (libera sessao DB durante operacao longa):

```python
for aj in ajustes:
    # ... preparar invoice
    db.session.commit()  # liberar SSL antes de operacao 1-10 min
    resultado = transmitir_nfe_via_playwright(...)
    # Re-buscar ajuste por id (sessao pode ter expirado)
    aj = db.session.get(AjusteEstoqueInventario, ajuste_id)
    aj.chave_nfe = resultado['chave_nf']
    db.session.commit()
```

### Opcao B: try/except + rollback + retry

```python
for aj in ajustes:
    try:
        resultado = transmitir_nfe_via_playwright(...)
        # ... update aj
        db.session.commit()
    except OperationalError as e:
        db.session.rollback()
        db.session.close()
        # Re-conectar e re-buscar
        aj = db.session.get(AjusteEstoqueInventario, ajuste_id)
        # ... retry update
```

### Opcao C: psycopg2 keepalive (config-level)

Adicionar TCP keepalive no SQLALCHEMY_DATABASE_URI:
```
postgresql://user:pass@host:5432/db?keepalives=1&keepalives_idle=30
```

Mantem conexao viva via TCP-level pings, evita SSL idle timeout.

### Recomendacao para LF completo (660 produtos)

Combinar **Opcoes A + C**:
- Config keepalive evita disconnect na maioria dos casos
- Commit antes de cada Playwright libera lock contention
- Try/except + retry com re-busca por ID em caso extremo

## Ref

- G007 (price_unit=0)
- G008 (excecao_autorizado)
- G015 (protecao G007 automatica)
- D006 secao L24 (a ser adicionada)
- Sub-piloto checkpoint final 2026-05-18

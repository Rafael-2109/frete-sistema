<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Audit Log — ajuste_estoque_inventario

> **Papel:** Audit Log — ajuste_estoque_inventario.

## Indice

- [Motivacao](#motivacao)
- [O que captura](#o-que-captura)
- [Schema da audit table](#schema-da-audit-table)
- [Gotchas](#gotchas)
- [Queries uteis](#queries-uteis)
  - [Timeline de 1 ajuste](#timeline-de-1-ajuste)
  - [Quem fez reset EXECUTADO → PROPOSTO (caso NF 626032)](#quem-fez-reset-executado-proposto-caso-nf-626032)
  - [DELETEs (operacao mais critica)](#deletes-operacao-mais-critica)
  - [Atividade da ultima execucao bulk (agrupada por transacao)](#atividade-da-ultima-execucao-bulk-agrupada-por-transacao)
  - [Volume por dia](#volume-por-dia)
- [Convencao: setar `application_name` em scripts](#convencao-setar-application_name-em-scripts)
- [Pos-implantacao](#pos-implantacao)

**Implementado**: 2026-05-18
**Migration**: `scripts/migrations/2026_05_18_audit_ajuste_estoque_inventario.{sql,py}`
**Tabela**: `ajuste_estoque_inventario_audit` (append-only)
**Trigger**: `audit_ajuste_estoque_inventario_trg` (AFTER INSERT/UPDATE/DELETE)

## Motivacao

Durante o ciclo de inventario 2026-05, cancelamentos e resets de ajustes
(EXECUTADO → PROPOSTO) sao feitos via SQL direto sem trilha forense (ex:
NF 626032 SEFAZ — `CHECKPOINT_2026_05_18_NCM_PENDENTE.md:168-180`).

Decisao 2026-05-18 (Rafael): implementar **apenas audit log** (sem bloqueio).
Operacao local com Claude Code; risco maior e perder rastreio, nao agente
deduzindo mudanca errada.

## O que captura

Toda alteracao em `ajuste_estoque_inventario`, **independente da origem**:
- ORM SQLAlchemy (`inventario_pipeline_service.py`)
- SQL direto via psql (operadores, manutencao)
- MCP `text_to_sql` do agente web
- Scripts ad-hoc (`padronizar_migracao.py`, `04b_propor_pre_etapa_cd.py`)
- Claude Code via Bash

## Schema da audit table

| Coluna | Tipo | Descricao |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `ajuste_id` | INTEGER (sem FK) | ID do ajuste — preservado mesmo apos DELETE |
| `tipo_evento` | VARCHAR(10) | INSERT / UPDATE / DELETE |
| `dados_antes` | JSONB | Linha inteira antes (NULL em INSERT) |
| `dados_depois` | JSONB | Linha inteira depois (NULL em DELETE) |
| `campos_alterados` | TEXT[] | So em UPDATE; lista das chaves cujo valor mudou |
| `registrado_em` | TIMESTAMP | `now() AT TIME ZONE 'America/Sao_Paulo'` |
| `registrado_por` | TEXT | `session_user` (role de DB) |
| `aplicacao` | TEXT | `current_setting('application_name')` |
| `client_addr` | INET | `inet_client_addr()` |
| `transaction_id` | BIGINT | `txid_current()` — correlaciona mudancas da mesma TX |

## Gotchas

1. **UPDATE no-op nao loga**: trigger compara `dados_antes` vs `dados_depois`
   via `jsonb_each` e ignora se nenhum campo mudou. Reduz ruido.
2. **Rollback rolla a audit junto**: o trigger e parte da mesma transacao.
   Se o caller faz ROLLBACK, a audit some — mas tambem nao houve mudanca
   real persistida. Comportamento desejado.
3. **`application_name` pode ser NULL**: `current_setting('application_name', true)`
   retorna `''` se nao setado; o trigger converte para NULL. Setar em scripts:
   ```sql
   SET application_name = 'inventario-onda1-bulk';
   ```
   Em Python/SQLAlchemy:
   ```python
   db.session.execute(text("SET application_name = 'inventario-bulk'"))
   ```
4. **`session_user` no DB local sempre `frete_user`**: util em prod onde
   workers/web podem ter roles distintos. Hoje em DEV todos sao `frete_user`,
   diferenciacao vem por `aplicacao`.
5. **Sem FK em `ajuste_id`** (proposital): audit deve sobreviver a DELETE
   do ajuste original. Joins manuais quando necessario.

## Queries uteis

### Timeline de 1 ajuste
```sql
SELECT
    registrado_em,
    tipo_evento,
    registrado_por,
    aplicacao,
    campos_alterados,
    dados_antes->>'status'  AS status_antes,
    dados_depois->>'status' AS status_depois,
    dados_antes->>'fase_pipeline'  AS fase_antes,
    dados_depois->>'fase_pipeline' AS fase_depois,
    dados_antes->>'invoice_id_odoo'  AS invoice_antes,
    dados_depois->>'invoice_id_odoo' AS invoice_depois
FROM ajuste_estoque_inventario_audit
WHERE ajuste_id = 162931
ORDER BY registrado_em;
```

### Quem fez reset EXECUTADO → PROPOSTO (caso NF 626032)
```sql
SELECT
    registrado_em,
    registrado_por,
    aplicacao,
    ajuste_id,
    dados_antes->>'invoice_id_odoo' AS invoice,
    dados_antes->>'chave_nfe' AS chave_antes
FROM ajuste_estoque_inventario_audit
WHERE tipo_evento = 'UPDATE'
  AND 'status' = ANY(campos_alterados)
  AND dados_antes->>'status'  = 'EXECUTADO'
  AND dados_depois->>'status' = 'PROPOSTO'
ORDER BY registrado_em DESC;
```

### DELETEs (operacao mais critica)
```sql
SELECT
    registrado_em,
    registrado_por,
    aplicacao,
    ajuste_id,
    dados_antes->>'ciclo' AS ciclo,
    dados_antes->>'cod_produto' AS produto,
    dados_antes->>'status' AS status_no_delete,
    dados_antes->>'invoice_id_odoo' AS invoice
FROM ajuste_estoque_inventario_audit
WHERE tipo_evento = 'DELETE'
ORDER BY registrado_em DESC
LIMIT 50;
```

### Atividade da ultima execucao bulk (agrupada por transacao)
```sql
SELECT
    transaction_id,
    MIN(registrado_em) AS inicio,
    MAX(registrado_em) AS fim,
    COUNT(*) AS mudancas,
    array_agg(DISTINCT tipo_evento) AS eventos,
    array_agg(DISTINCT registrado_por) AS quem,
    array_agg(DISTINCT aplicacao)     AS app
FROM ajuste_estoque_inventario_audit
WHERE registrado_em > now() - interval '4 hours'
GROUP BY transaction_id
ORDER BY inicio DESC
LIMIT 20;
```

### Volume por dia
```sql
SELECT
    DATE(registrado_em) AS dia,
    tipo_evento,
    COUNT(*) AS qtd
FROM ajuste_estoque_inventario_audit
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

## Convencao: setar `application_name` em scripts

Para que o `aplicacao` na audit identifique a origem, adicionar no inicio
de cada script de inventario:

```python
# Logo apos create_app() + app_context()
db.session.execute(text(
    f"SET application_name = 'inventario-{Path(__file__).stem}'"
))
```

Sem isso, `aplicacao` fica NULL e a forense vira "alguem rodou um SQL,
nao sei qual script".

## Pos-implantacao

- [ ] Adicionar `SET application_name` em `09_executar_onda1_bulk.py`,
      `09b_executar_pre_etapa.py`, `04_propor_ajustes.py`, etc.
- [ ] Verificar se Render `application_name` chega corretamente (vem do
      gunicorn config / variavel de ambiente).
- [ ] Considerar adicionar Camadas 2-5 (imutabilidade, CHECK transicoes,
      bloqueio no agente, reconciliacao Odoo) se nivel de risco aumentar.

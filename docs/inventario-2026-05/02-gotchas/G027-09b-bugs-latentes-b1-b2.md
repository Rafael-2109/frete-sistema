<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G027 — Bugs latentes do `09b_executar_pre_etapa.py` (B1 + B2)

> **Papel:** G027 — Bugs latentes do `09b_executar_pre_etapa.py` (B1 + B2).

## Indice

- [B1 — Validação pré-Odoo não persiste FALHA em DB](#b1-validação-pré-odoo-não-persiste-falha-em-db)
  - [Sintoma](#sintoma)
  - [Consequência](#consequência)
  - [Workaround usado em PROD (sessão 2026-05-18)](#workaround-usado-em-prod-sessão-2026-05-18)
  - [Fix sugerido (futuro)](#fix-sugerido-futuro)
- [B2 — `localizar_doador` não soma múltiplos quants do mesmo lote](#b2-localizar_doador-não-soma-múltiplos-quants-do-mesmo-lote)
  - [Sintoma](#sintoma)
  - [Consequência](#consequência)
  - [Workaround usado em PROD](#workaround-usado-em-prod)
  - [Fix sugerido (futuro)](#fix-sugerido-futuro)
- [Quando fixar](#quando-fixar)
- [Ref](#ref)
- [Contexto](#contexto)

**Data**: 2026-05-18 fim de tarde
**Origem**: extraído de `CHECKPOINT_2026_05_18_CD_FINALIZADO.md` §5 antes do arquivamento parcial
**Severidade**: MEDIUM (não bloqueiam o ciclo, mas geram falhas silenciosas que exigem workaround manual)
**Status**: NÃO CORRIGIDOS — workaround documentado, fix para outra sessão

---

## B1 — Validação pré-Odoo não persiste FALHA em DB

### Sintoma

`executar_transferencia_interna` retorna `{'sucesso': False, 'erro': ...}` nos casos:
- linha 222: `qty <= 0`
- linha 229: `not doador`
- linha 235: `doador['quantity'] < qty - 0.001`

Nesses casos NÃO modifica `ajuste.status` nem persiste em DB. Apenas conta em `stats['*_falha']` e prossegue.

### Consequência

Re-execução continua marcando ajuste como APROVADO no DB → o ciclo nunca destrava. Operador acha que ajustes estão "prontos para rodar" mas todos vão falhar pela mesma razão pré-Odoo.

### Workaround usado em PROD (sessão 2026-05-18)

Marcar manualmente como FALHA via SQL direto com erro_msg descritivo:

```sql
UPDATE ajuste_estoque_inventario
SET status='FALHA', erro_msg='Cat3_DRIFT_POS_PRE_ETAPA: lote X sem saldo doavel',
    fase_pipeline='INTERNO_FALHA'
WHERE id IN (...);
```

### Fix sugerido (futuro)

Em ambos os caminhos serial+thread do `09b`, persistir status quando validação pré-Odoo falha:

```python
if r['sucesso'] is False and not dry_run:
    ajuste.status = 'FALHA'
    ajuste.erro_msg = r['erro']
    ajuste.fase_pipeline = 'INTERNO_FALHA'
    db.session.commit()
```

**Localização do fix**: `scripts/inventario_2026_05/09b_executar_pre_etapa.py` linhas 222, 229, 235 (após cada `return {'sucesso': False, ...}`).

**Risco**: persistência precisa ser thread-safe quando `--max-workers > 1`. Validar com `db.session.begin_nested()` ou usar `db.session.merge()` para evitar conflito de transações entre threads.

---

## B2 — `localizar_doador` não soma múltiplos quants do mesmo lote

### Sintoma

Linha 161 do `09b`:
```python
# Soma de N quants do mesmo lote (split entre quants) — nao implementado
# nesta versao, retorna o primeiro disponivel
```

### Consequência

Lote com qty total suficiente mas fragmentada em 2+ quants falha silenciosamente. Caso real (CD pré-etapa):
- Ajuste 167972 cod=204030500, pediu 10 un do lote X
- Quant 94193: 2 un em `CD/Estoque`
- Quant 131484: 8 un em `CD/Estoque/DEVOLUÇÃO`
- Total disponível: 10 un (= demanda)
- `localizar_doador` retornou apenas o primeiro (2 un) → falha "saldo insuficiente"

### Workaround usado em PROD

Não houve workaround sistemático — único caso (1 de 6897 ajustes) foi marcado como FALHA `Cat3_FRAGMENTADO` e aceito como rabo.

### Fix sugerido (futuro)

Implementar split via loop até atingir qty pedida, executando N transferências em sequência:

```python
def localizar_doador_split(odoo, cod, lote_nome, qty_desejada, location_id, company_id):
    """Retorna lista [(quant_id, qty_a_transferir), ...] que soma >= qty_desejada."""
    quants = odoo.search_read('stock.quant', [
        ['product_id.default_code', '=', cod],
        ['lot_id.name', '=like', lote_nome],
        ['location_id', '=', location_id],
        ['company_id', '=', company_id],
        ['quantity', '>', 0],
    ], ['id', 'quantity', 'reserved_quantity'], order='create_date')

    plano = []
    falta = qty_desejada
    for q in quants:
        livre = q['quantity'] - q['reserved_quantity']
        if livre <= 0:
            continue
        a_pegar = min(livre, falta)
        plano.append((q['id'], a_pegar))
        falta -= a_pegar
        if falta <= 0.001:
            return plano

    return None  # saldo insuficiente
```

**Localização do fix**: `scripts/inventario_2026_05/09b_executar_pre_etapa.py` linha 161 + helper novo.

**Prioridade**: BAIXA (1 caso em 6897 — 0.014%).

---

## Quando fixar

- **B1**: antes de qualquer próxima rodada do `09b` para FB (Onda 6 futura) — sem o fix, operador vai precisar marcar FALHA manualmente de novo
- **B2**: opcional — só vale a pena se análise prévia da Onda 6 FB mostrar muitos casos `FRAGMENTADO`

---

## Ref

- `99-historia/CHECKPOINT_2026_05_18_PRE_ETAPA_CD_EXECUTADA.md` — checkpoint da 1ª rodada CD
- `CHECKPOINT_2026_05_18_CD_FINALIZADO.md` — checkpoint do fechamento CD (referência sessão paralela)
- `00-decisoes/D008-licoes-seguranca-operacional-e1-e2.md` — lições de segurança operacional descobertas na mesma sessão (E1 = duplicação acidental, E2 = workaround stock.lot.name ignorado)
- `08-execucoes/EXECUCAO_PRE_ETAPA_CD_2026_05_18.md` — relatório de execução
- `scripts/inventario_2026_05/09b_executar_pre_etapa.py` — script com bugs

## Contexto

Gotcha — ciclo de inventario NACOM/LF/CD/FB 2026-05. Tema: Bugs latentes do `09b_executar_pre_etapa.py` (B1 + B2)

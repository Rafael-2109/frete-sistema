# Baseline Pré Sprint A — CarVia

**Gerado em**: 2026-04-17 (UTC)
**Fonte**: MCP Render `query_render_postgres` contra `dpg-d13m38vfte5s738t6p50-a` (produção)
**Sessão**: `20260417-141600-carvia-audit`
**Objetivo**: medir esforço real dos itens A1-A4 antes de iniciar implementação.

---

## A0.1 — CTe Comp órfãos (estima item A1)

| Categoria | Qtd |
|-----------|-----|
| Total CTe Complementares | 24 |
| Vinculados a fatura (OK) | 23 |
| **Candidatos a retrolink (A1)** | **1** |
| Aguardando fatura chegar | 0 |

**Candidato identificado**:
- `id=25 COMP-024 cte=191 status=EMITIDO op=192 op_fatura=187 fatura=123-6 (PENDENTE, status_conferencia=PENDENTE)` — criado 2026-04-17
- Fatura elegível (não CONFERIDA/PAGA) → A1 corrigirá imediatamente no primeiro run.

**Impacto A1**: baixo volume. Backfill não precisa batch — script processa 1 registro. Mas código precisa ser corrigido para prevenir acúmulo futuro.

---

## A0.2 — NFs sem item em fatura (estima item A2 — Bug #1)

| Métrica | Qtd |
|---------|-----|
| Faturas afetadas | 1 |
| Items suplementares faltando | 1 |
| Operações com gap | 1 |

**Caso identificado**:
- `fatura=168 numero=112-1 status=PENDENTE op=171 cte=168 nf_id=202 numero_nf=49506 emitente=33119545000251 destinatario=04972092003148`

**Impacto A2**: baixo volume histórico. 1 item suplementar a criar retroativamente. Mesmo racional do A1 — correção é preventiva, evitando que cenário se repita.

---

## A0.3 — CTe Comp sem CTRNC (estima item A3 — Bug #3)

| Bucket | Qtd |
|--------|-----|
| Total sem ctrc_numero | **0** |
| <= 30 dias | 0 |
| 30-90 dias | 0 |
| > 90 dias | 0 |

**Contexto** (por status):
- `FATURADO`: 23 com CTRC (100%)
- `EMITIDO`: 1 com CTRC (100%)

**Impacto A3**: **zero histórico afetado**. Todos os 24 CTe Comp em produção já têm CTRNC. Mas:
- O bug é real no código (`verificar_ctrc_cte_comp_job` retorna SKIPPED quando `ctrc_numero` vazio).
- Pode estar funcionando porque (a) emissão 222 via Playwright sempre captura, OU (b) XMLs importados trazem CTRNC.
- **A3 é preventivo**: assegura que o próximo caso edge (Playwright falha + XML sem ctrc) seja resolvido automaticamente sem intervenção manual.
- **Script backfill do A3 dispensável** (zero candidatos). Mas mudanças de código + feature flag + fluxo automático continuam válidas.

---

## A0.4 — Operações sem XML (bloqueio parcial A4.3)

| tipo_entrada | Total | Com XML | Sem XML |
|--------------|-------|---------|---------|
| IMPORTADO | 143 | 143 | 0 |
| MANUAL_SEM_CTE | 37 | 0 | 37 |

**Total operações**: 180.

**Impacto A4**:
- ✅ **Zero anomalias**: todas operações IMPORTADO têm XML (backfill A4.3 pode processar todas).
- `MANUAL_SEM_CTE` corretamente sem XML (esperado — design).
- **A4.3 backfill**: 143 XMLs para baixar do S3 + re-parsear. ~50 em 2s batch = ~6 min total se S3 colocado. Factível em janela curta.

---

## A0.5 — Números sequenciais duplicados (bloqueia B2)

| Tabela.Coluna | Duplicatas |
|---------------|-----------|
| `carvia_operacoes.cte_numero` | **0** |
| `carvia_subcontratos.cte_numero` | **8 grupos** (16 registros) |
| `carvia_cte_complementares.numero_comp` | **0** |

**Investigação das 8 duplicatas em `carvia_subcontratos.cte_numero`**:

| cte_numero | id_1 (status) | criado_1 | id_2 (status) | criado_2 |
|-----------|---------------|----------|---------------|----------|
| 1178943 | 1 (CANCELADO) | 2026-03-06 | 48 (CONFIRMADO) | 2026-04-13 |
| 1178944 | 2 (CANCELADO) | 2026-03-06 | 49 (CONFIRMADO) | 2026-04-13 |
| 12264 | 8 (CANCELADO) | 2026-03-06 | 47 (CONFIRMADO) | 2026-04-13 |
| 29244 | 34 (CANCELADO) | 2026-03-12 | 66 (CONFIRMADO) | 2026-04-13 |
| 392293 | 11 (CANCELADO) | 2026-03-06 | 50 (CONFIRMADO) | 2026-04-13 |
| 394512 | 36 (CANCELADO) | 2026-03-18 | 68 (CONFIRMADO) | 2026-04-13 |
| 394514 | 37 (CANCELADO) | 2026-03-18 | 69 (CONFIRMADO) | 2026-04-13 |
| 3964 | 40 (CANCELADO) | 2026-03-18 | 56 (CONFIRMADO) | 2026-04-13 |

**Padrão confirmado**: todas as duplicatas são `CANCELADO + CONFIRMADO`. Design legítimo — ao cancelar, subcontrato foi recriado com mesmo `cte_numero`.

**Impacto B2 (UniqueConstraint)**:
- ❌ `UniqueConstraint(cte_numero)` simples FALHARÁ — quebra padrão operacional.
- ✅ Usar **UniqueConstraint parcial**: `WHERE status != 'CANCELADO'`.
- Mesmo padrão já usado em `numero_sequencial_transportadora` (R7 do CLAUDE.md).

**Plano B2 revisado**:
```sql
CREATE UNIQUE INDEX uq_carvia_subcontratos_cte_numero_ativo
  ON carvia_subcontratos(cte_numero)
  WHERE cte_numero IS NOT NULL AND status != 'CANCELADO';
```
Aplicar padrão análogo em `carvia_operacoes.cte_numero` e `carvia_cte_complementares.numero_comp` (ambos sem duplicatas, mas princípio mesmo).

---

## A0.6 — Baseline fatura cliente

| Métrica | Valor |
|---------|-------|
| Total faturas | 155 |
| Soma valor_total | **R$ 281.282,56** |
| Status PENDENTE | 48 |
| Status EMITIDA | 0 |
| Status PAGA | 106 |
| Status CANCELADA | 1 |
| `status_conferencia=CONFERIDO` | 2 |

**Observações**:
- 2 faturas CONFERIDAS → gate A1 (`fatura.pode_editar()`) relevante: CTe Comp tardios para estas 2 faturas não vão auto-vincular até operador reabrir conferência.
- Soma R$ 281K é o baseline — comparar após Sprint A para detectar alterações não esperadas em `valor_total`.

---

## Sumário Executivo

| Item Sprint A | Impacto histórico | Esforço ajustado |
|---------------|-------------------|------------------|
| **A1** (Bug #2) | 1 CTe Comp órfão | Mantém 6-8h (código + teste + script backfill mínimo) |
| **A2** (Bug #1) | 1 fatura afetada, 1 item | Mantém 6-8h (hook retroativo + script backfill mínimo) |
| **A3** (Bug #3) | **0 histórico** — preventivo | Reduzir p/ 3-4h (dispensa script backfill) |
| **A4** (Bug #4) | 143 operações elegíveis backfill | Mantém 8-10h (A4.1 + A4.2); A4.3 backfill ~6 min exec |
| **B2** (UniqueConstraint) | 8 legit duplicates (CANCELADO+CONFIRMADO) | **Redesign**: usar constraint PARCIAL `WHERE status != 'CANCELADO'` |

### Alertas e decisões

- ⚠ **B2 redesenhada**: não usar `UniqueConstraint` simples. Usar parcial. Documentar no CLAUDE.md que `CANCELADO` permite reuso de `cte_numero`.
- ✅ **A3 simplificado**: zero histórico → dispensa script de backfill. Manter apenas mudanças de código (worker refator, enqueue automático, feature flag).
- ✅ **A1/A2 volumes baixos**: scripts backfill triviais (loop sobre 1 registro cada). Podem rodar inline no PR sem risco.
- ✅ **A4.3 factível**: 143 XMLs = ~6min operação. Pode rodar em janela curta fora de horário comercial.
- ℹ **Princípio confirmado**: bugs não são massivos HOJE — sistema está **funcionando na maioria dos casos**. Correções são preventivas para evitar acúmulo.

### Novo esforço total estimado (revisado pós A0)

- Sprint A: 23-30h (antes 25-34h — A3 reduzido)
- Sprint B: 7-12h (mesmo)
- Sprint C: 16-24h (mesmo — inclui A4.3 backfill histórico de 143 XMLs)
- **Total**: 46-66h (antes 52-76h — redução ~12%)

### Recomendação para executar Sprint A

**Ordem mantida**: A3 → A1+A2 → A4.1 → A4.2.

**Prioridade ajustada**: como impacto histórico é baixo, o risco de **regressão** (quebrar o que funciona) > risco de **não-correção**. Disciplina dos princípios NN1-NN6 do plano continua crítica mesmo com volume baixo.

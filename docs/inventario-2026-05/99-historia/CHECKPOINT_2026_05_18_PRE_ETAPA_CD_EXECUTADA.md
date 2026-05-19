# CHECKPOINT — Pre-etapa CD (D007) EXECUTADA (2026-05-18)

**Sessao Claude Code paralela encerrada**: 2026-05-18 ~06:20
**Status global**: Pre-etapa CD (Onda 5) executada em PROD com 97.8% de sucesso.
**Pendencia operacional**: 121 ajustes Cat 2 (vendas reais em curso) + 18 Cat 1
(produtos arquivados) + 12 APROVADO (race condition residual).

> **Sessao paralela** — nao tocou em arquivos de outras sessoes
> (SOT.md, QUICK_START_NEXT_SESSION.md, D004/D005/D006, 03/04 scripts).
> Patches sugeridos em `00-decisoes/D007-PATCHES-PARA-DOCS-EXISTENTES.md`.

---

## 1. Resultado consolidado

| status | ajustes | % | Acao seguinte |
|---|---|---|---|
| ✅ EXECUTADO | **6.746** | **97.8%** | Estado fisico do CD pre-arrumado |
| ⏳ APROVADO restante | 12 | 0.2% | Re-rodar 09b (race condition) |
| ❌ FALHA Cat 1 (arquivados) | 18 | 0.3% | Decisao humana (reativar OU ignorar) |
| ❌ FALHA Cat 2 (vendas reais) | 121 | 1.8% | Aguardar separacoes concluirem, re-rodar |
| **Total Onda 5 CD** | **6.897** | **100%** | |

**Impacto fiscal eliminado**: R$ 33,2 mi em NFs CD↔FB substituido por movimentacao interna.

---

## 2. Estado das ondas (inventario 2026-05)

| Onda | Status | Escopo | Pendencia |
|---|---|---|---|
| 1 — LF↔FB NF | ⚠️ piloto OK (6/1.071 EXECUTADO), bulk em outra sessao | LF | bulk |
| 2 — FB↔CD NF | ⏳ PROPOSTO (TRANSFERIR_FB_CD residual 55 ajustes/R$ 167k) | FB→CD | aprovar + executar |
| 3 — INDISPONIBILIZAR FB | ⏳ PROPOSTO | FB | depois |
| 4 — RENOMEAR_LOTE FB/LF | ⏳ PROPOSTO | FB/LF | depois |
| **5 — Pre-etapa CD (D007)** | **✅ 97.8% EXECUTADO** | **CD** | **132 falhas/aprovados aguardando** |
| 6 — Pre-etapa FB (futuro) | ⏳ não construida | FB | apos sessao paralela terminar |

---

## 3. Arquivos e artefatos criados nesta sessao

### Codigo
- `app/odoo/services/pre_etapa_estoque_service.py` (315 LOC) — planejador parametrizado company_id
- `tests/odoo/services/test_pre_etapa_estoque_service.py` (13 tests passing)
- `scripts/inventario_2026_05/03b_planejar_pre_etapa_cd.py` (~280 LOC)
- `scripts/inventario_2026_05/04b_propor_pre_etapa_cd.py` (~250 LOC) + ACOES_ONDA5
- `scripts/inventario_2026_05/09b_executar_pre_etapa.py` (~600 LOC) — paralelo via ThreadPoolExecutor

### Documentacao
- `docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md` (decisao formal)
- `docs/inventario-2026-05/00-decisoes/D007-PATCHES-PARA-DOCS-EXISTENTES.md` (patches sugeridos)
- `docs/inventario-2026-05/02-gotchas/G024-reserved-quantity-nao-recompute-apos-unlink.md` (renumerado de G006)
- `docs/inventario-2026-05/02-gotchas/G025-orfaos-move-lines-recorrentes-cd.md` (renumerado de G007)
- `docs/inventario-2026-05/EXECUCAO_PRE_ETAPA_CD_2026_05_18.md` (relatorio completo)
- ESTE arquivo (checkpoint)

### Operacao em PROD (Odoo CIEL IT)
- **6.746 ajustes** executados (transferencias internas + ajuste positivo puro)
- **526 stock.move.line** unlinked (orfaos puros)
- **47 stock.quant.reserved_quantity** writes (recompute manual)
- **0 NFs SEFAZ emitidas** (pre-etapa e 100% interna)

### Excel
- `docs/inventario-2026-05/07-relatorios/plano-pre-etapa-cd.xlsx` (gerado por 03b)

### Backups
- `/tmp/backup_inventario_2026_05/ajustes_cd_pre_etapa_20260518_030410.sql` (7.1MB, pre-DELETE)
- `/tmp/backup_inventario_2026_05/ajustes_cd_pre_etapa_04b_*.sql` (auto-backup 04b)
- `/tmp/backup_inventario_2026_05/orfaos_b_min_cd_20260518_060842.json` (526 orfaos com payload completo)

### Scripts auxiliares de inspecao (em /tmp/)
- `/tmp/verify_odoo_subpilot.py` — validacao do sub-piloto
- `/tmp/verify_picking_reserva.py` — inspecao de 1 move_line
- `/tmp/verify_orphan_move_lines.py` — count e distribuicao temporal
- `/tmp/delete_orphans_b_minimo.py` — DELETE cirurgico (executado)
- `/tmp/fix_reserved_quantity.py` — recompute manual de reservas
- `/tmp/diag_remaining_failures.py` — diagnostico falhas restantes

---

## 4. 5 bugs descobertos + fix

| # | Bug | Fix |
|---|---|---|
| 1 | dry-run modificava status no DB | guard `if not dry_run` em `09b` |
| 2 | `operacao_odoo_auditoria.acao` VARCHAR(20) overflow | dict `ACAO_AUDIT_CURTA` com nomes curtos (`cd_pre_pos`, etc) |
| 3 | Arredondamento DB (4 casas) vs Odoo (6 casas) | tolerancia 0.001 + clamp em `StockInternalTransferService` |
| 4 | Paralelizacao limitada pelo Odoo (~2.7x vs 5x teorico) | Odoo serializa internamente — aceitar limite |
| 5 | Produtos arquivados nao processados | decisao: skip + FALHA documentada |

**Adicionais descobertos durante execucao**:
| # | Bug | Fix |
|---|---|---|
| 6 | `reserved_quantity` nao recompute apos unlink de orfa | write direto em `stock.quant` — ver G006 |
| 7 | 825 move_lines orfas no CD acumuladas em 18 meses | DELETE em batches — ver G007 |
| 8 | Race condition Postgres (Cat 99 `<Fault 1>`) | retry resolve (0.09% taxa) |

---

## 5. Comandos rapidos para validar estado

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. Estado Onda 5 CD
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT status, COUNT(*) FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=4
  AND acao_decidida IN ('AJUSTE_CD_TRANSF_INTERNA_POS','AJUSTE_CD_TRANSF_INTERNA_NEG','AJUSTE_CD_POSITIVO_PURO')
GROUP BY status ORDER BY status;
"
# Esperado: APROVADO=12, EXECUTADO=6746, FALHA=139

# 2. Tests
pytest tests/odoo/services/test_pre_etapa_estoque_service.py -p no:randomly -q
# Esperado: 13 passed

# 3. Validar quants do sub-piloto no Odoo
python /tmp/verify_odoo_subpilot.py | grep -E "TOTAL|cod|=== "
```

---

## 6. Proximos passos (TERMINAR O CD)

Escopo desta documentacao: completar a pre-etapa CD. **Nao inclui** Onda 6 FB,
patches em docs de outras sessoes, ou outras ondas.

### Pendencias para fechar o CD

1. **12 APROVADO race condition residual**: re-rodar 09b para destravar.
   ```bash
   python scripts/inventario_2026_05/09b_executar_pre_etapa.py \
       --company-id=4 --confirmar --max-workers=5 --usuario=rafael
   ```

2. **121 FALHA Cat 2 (vendas reais ativas)**:
   - Verificar quais separacoes/pickings estao reservando:
     ```bash
     python /tmp/diag_remaining_failures.py
     ```
   - Aguardar conclusao OU cancelar manualmente no Odoo UI
   - Quando reservas liberarem: reverter FALHA → APROVADO + re-rodar 09b
     ```bash
     PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
     UPDATE ajuste_estoque_inventario
     SET status='APROVADO', erro_msg=NULL, fase_pipeline=NULL
     WHERE ciclo='INVENTARIO_2026_05' AND company_id=4 AND status='FALHA'
       AND erro_msg LIKE 'Quant origem%reservadas em pickings ativos%';
     "
     python scripts/inventario_2026_05/09b_executar_pre_etapa.py \
         --company-id=4 --confirmar --max-workers=5 --usuario=rafael
     ```

3. **18 FALHA Cat 1 (arquivados/sem cadastro)**:
   - Decisao humana — listar produtos:
     ```sql
     SELECT cod_produto, COUNT(*) ajustes
     FROM ajuste_estoque_inventario
     WHERE ciclo='INVENTARIO_2026_05' AND company_id=4 AND status='FALHA'
       AND erro_msg LIKE 'product_id nao resolvido%'
     GROUP BY cod_produto;
     ```
   - Para cada: reativar no Odoo (admin) OU aceitar como nao-tratado

---

## 7. Pendencias bloqueantes

**Nenhuma bloqueante** para os 97.8% executados. As pendencias sao operacionais
(esperar separacoes Cat 2, decisao humana sobre arquivados Cat 1) ou
re-execucao trivial (12 APROVADO race condition).

---

## 8. Como confirmar que pre-etapa funcionou

Validacao no Odoo (sub-piloto detalhado em `EXECUCAO_PRE_ETAPA_CD_2026_05_18.md`):

```
Antes da pre-etapa CD:
  - Lotes Odoo divergentes do inventario fisico
  - 825 orfaos travando ~480k un em reserva
  - 5577 ajustes seriam INDISPONIBILIZAR + 385 NFs CD↔FB

Apos pre-etapa CD:
  - 6746 ajustes EXECUTADO (97.8%)
  - 526 orfaos limpos
  - 47 quants com reserved_quantity corrigido
  - ZERO NFs SEFAZ emitidas (operacao 100% interna)
  - R$ 33,2 mi de valor fiscal eliminado
```

---

## 9. Referencias

- **Decisao D007**: `00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md`
- **Relatorio execucao**: `EXECUCAO_PRE_ETAPA_CD_2026_05_18.md`
- **Gotchas G006, G007**: `02-gotchas/`
- **Patches docs existentes**: `00-decisoes/D007-PATCHES-PARA-DOCS-EXISTENTES.md`
- **Checkpoint piloto LF anterior**: `CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md`

---

## 10. Indice de prompts/comandos uteis

```bash
# === ESTADO ===
# Contagem CD onda 5
psql -c "SELECT status, COUNT(*) FROM ajuste_estoque_inventario WHERE ciclo='INVENTARIO_2026_05' AND company_id=4 AND acao_decidida LIKE 'AJUSTE_CD_%' GROUP BY status;"

# Falhas por categoria
psql -c "SELECT CASE WHEN erro_msg LIKE 'product_id%' THEN 'CAT1' WHEN erro_msg LIKE '%reservadas%' THEN 'CAT2' ELSE 'OUTRO' END, COUNT(*) FROM ajuste_estoque_inventario WHERE status='FALHA' AND company_id=4 GROUP BY 1;"

# === RE-EXECUCAO ===
# Reverter Cat 2 para APROVADO (apos vendas concluirem)
psql -c "UPDATE ajuste_estoque_inventario SET status='APROVADO', erro_msg=NULL, fase_pipeline=NULL WHERE status='FALHA' AND erro_msg LIKE '%reservadas em pickings ativos%' AND company_id=4;"

# Re-rodar 09b paralelo
python scripts/inventario_2026_05/09b_executar_pre_etapa.py --company-id=4 --confirmar --max-workers=5 --usuario=$USER

# === LIMPEZA FUTURA ===
# Listar orfaos
python /tmp/verify_orphan_move_lines.py
# Limpar (cirurgico Cat 2)
python /tmp/delete_orphans_b_minimo.py --confirmar
# Recompute reservas
python /tmp/fix_reserved_quantity.py --confirmar

# === DIAGNOSTICO ===
python /tmp/diag_remaining_failures.py
python /tmp/verify_odoo_subpilot.py
```

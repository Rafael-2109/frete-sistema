# Quick Start — Próxima sessão (pós sub-piloto 10 produtos)

**Data do checkpoint**: 2026-05-18 ~04:30
**Branch**: `main` (commit pendente — muitas mudanças)
**Estado**:
- Sub-piloto bulk 10 produtos executado parcialmente
- **1 NF end-to-end OK** (608631 → entrada FB 608645)
- **1 NF fiscal OK** (608629, FB→LF) — entrada LF feita manualmente via picking 317306
- **1 NF cancelada** (608630 NF 13150) — XML SEFAZ incompleto
- **11 ajustes PROPOSTO** prontos para próxima rodada
- **10 fixes de código aplicados** (resolver_location, skip_backorder, f5b/f5c/f5d multi-ajuste, f5e idempotência invoice, FIFO multi-lote, etc.)

> **Leitura primeira (NOVA SESSAO)**:
> 1. `CHECKPOINT_2026_05_18_SUBPILOTO_FINAL.md` — snapshot completo com lições
> 2. `00-decisoes/D006-...md` — secao "Licoes aprendidas piloto" (5 fixes originais)
> 3. `00-decisoes/D005-...md` — nota padronizacao MIGRAÇÃO

---

## 🎯 PROMPT PRONTO PARA NOVA SESSAO

```
Retomando inventario 2026-05 apos sub-piloto bulk de 10 produtos:
- 1 NF SEFAZ ok end-to-end (608631 RETNA/2026/00031, entrada FB 608645)
- 1 NF FB→LF ok fiscal (608629 RPI/2026/00201), entrada LF manual
- 1 NF cancelada (608630 NF 13150, XML SEFAZ incompleto)
- 11 ajustes PROPOSTO pendentes (10 LF→FB perda + 1 FB→LF industr)
- 10 fixes de codigo aplicados

LER PRIMEIRO (ordem):
1. docs/inventario-2026-05/CHECKPOINT_2026_05_18_SUBPILOTO_FINAL.md
2. docs/inventario-2026-05/00-decisoes/D006-transferir-quantidade-entre-lotes-nao-renomear.md
3. docs/inventario-2026-05/SOT.md §7.4-7.5

OBJETIVO: rodar bulk para os 11 PROPOSTO pendentes + cancelar SEFAZ
da NF 13150 via UI Odoo. Se OK, avancar para LF completo (~660 produtos).

VALIDAR baseline antes:
- pytest tests/odoo/ -p no:randomly -q
- 5 EXECUTADO + 11 PROPOSTO + 5 TRANSF_OK + 3 INDISPONIBILIZAR_LOTE
- 1 entrada LF manual feita (picking 317306, 103000037 10.389 kg)

EXECUTAR proxima rodada (11 ajustes pendentes):
1. Dry-run completo:
     python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
         --company-id=5 --onda=1 --limite-produtos=10 \\
         --max-produtos-picking=5 --dry-run
   Esperado: 2 pickings (1 LF→FB perda 10 ajustes + 1 FB→LF industr 1 ajuste)
   Valor BRL: ~R$ 8.479

2. ETAPA A+B (lote + pickings):
     python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
         --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 \\
         --ate-etapa=B --confirmar --usuario=rafael

3. ETAPA C (aguardar CIEL IT):
     python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
         --company-id=5 --onda=1 --apenas-etapa=C --confirmar --usuario=rafael

4. PAUSE: verificar invoices criadas + price_unit > 0 em todas linhas.
   Se price=0, custo_medio do produto e' 0 OU negativo no Odoo. Corrigir
   no DB local (custo_medio = standard_price) ANTES de rodar Etapa D.

5. ETAPA D (SEFAZ Playwright — IRREVERSIVEL):
     python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
         --company-id=5 --onda=1 --apenas-etapa=D --confirmar --confirmar-sefaz \\
         --usuario=rafael

6. ETAPA E (Entrada FB):
     python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
         --company-id=5 --onda=1 --apenas-etapa=E --confirmar --usuario=rafael
   ATENCAO: etapa E nao filtra acao_decidida=INDUSTRIALIZACAO_FB_LF
   (sentido invertido). Se aparecer 1 RecebimentoLf para 608629, vai falhar.
   Antes de rodar Etapa E: aplicar correcao em etapa_e_entrada_fb para
   filtrar acoes que NAO sao LF→FB (PERDA_LF_FB, DEV_LF_FB, TRANSFERIR_CD_FB).

7. Validar via 08_extrair_pos_execucao.py

8. Cancelar SEFAZ NF 13150 via UI Odoo (justificativa, 24h)

SE TUDO OK -> AVANCAR PARA LF COMPLETO (~660 produtos):
   python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
       --company-id=5 --onda=1 --max-produtos-picking=30 \\
       --confirmar --confirmar-sefaz --usuario=rafael
```

---

## ⚡ Comandos prontos (em ordem)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. Baseline tests
pytest tests/odoo/ -p no:randomly -q | tail -3

# 2. Estado DB final do sub-piloto
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT acao_decidida, status, fase_pipeline, COUNT(*) qty,
       SUM(ABS(qtd_ajuste)*COALESCE(custo_medio,0))::NUMERIC(15,2) valor_brl
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=5
  AND cod_produto IN ('101001001', '102020201', '102020600', '103000011',
                      '103000014', '103000020', '103000037', '103000113',
                      '103000117', '103000122')
GROUP BY acao_decidida, status, fase_pipeline
ORDER BY 1, 2, 3;
"

# 3. Dry-run bulk para confirmar 11 PROPOSTO
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --limite-produtos=10 \
    --max-produtos-picking=5 --dry-run

# 4. ANTES de rodar etapa E: corrigir filtro em etapa_e_entrada_fb
#    (pular acao_decidida = INDUSTRIALIZACAO_FB_LF, DEV_FB_LF, DEV_CD_LF)

# 5. Bulk completo
# python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
#     --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 \
#     --confirmar --confirmar-sefaz --usuario=rafael
```

---

## 📋 Checklist antes de rodar bulk

- [ ] pytest passa baseline
- [ ] 5 EXECUTADO + F5e_SEFAZ_OK confirmado no DB
- [ ] 11 PROPOSTO sem fase confirmado (vai rodar)
- [ ] 5 TRANSF_OK confirmado (skip ETAPA A)
- [ ] Conexao Odoo OK (UID 42)
- [ ] Playwright + Chromium instalados
- [ ] ODOO_USERNAME + ODOO_PASSWORD no .env
- [ ] Certificado SEFAZ valido LF + FB
- [ ] Robo CIEL IT online
- [ ] **Correcao etapa_e_entrada_fb** para filtrar INDUSTRIALIZACAO_FB_LF
- [ ] Cancelamento SEFAZ NF 13150 (manual via UI Odoo, 24h)

---

## 🚨 Riscos para nova rodada

| Risco | Mitigacao |
|---|---|
| price_unit=0 nas linhas (custo zero) | **CORRIGIDO no script** — etapa_b_pickings agora busca standard_price ANTES de criar pickings. Verificar pos Etapa C antes de SEFAZ. |
| SEFAZ rejeita schema XML (multi-linha) | Mitigado pelo fix de price_unit. Se ainda falhar, verificar campos `False`/`None` em invoice_line. |
| XML autorizado vazio (`excecao_autorizado`) | Risco se SEFAZ retornar com ressalva. Solucao: re-baixar XML via UI Odoo OU regenerar nfeProc. |
| Picking inter-company "Empresas incompativeis" | **CORRIGIDO** — resolver_location_destino mapeia locations virtuais por (origem, tipo_op) |
| Backorder picking fica em assigned | **CORRIGIDO** — validar() com skip_backorder=True |
| f5b/f5c/f5d so marcam 1 ajuste por picking | **CORRIGIDO** — _agrupar_por_picking suporta N ajustes |
| f5e re-transmite mesma NF | **CORRIGIDO** — idempotencia por invoice_id |

---

## 🔗 Referencias rapidas

| Documento | Para que serve |
|---|---|
| `CHECKPOINT_2026_05_18_SUBPILOTO_FINAL.md` | Estado completo + 10 lições aprendidas |
| `CHECKPOINT_2026_05_18_BULK_PRONTO.md` | Estado pre-sub-piloto (historico) |
| `CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md` | Estado pre-bulk (historico) |
| `00-decisoes/D004` | Rename + diferenca liquida (superseded por D006) |
| `00-decisoes/D005` | Lote MIGRAÇÃO consolidador (padronizado) |
| `00-decisoes/D006` | TRANSFERIR via inventory adjustment + 5 licoes piloto |
| `02-gotchas/G001..G005` | Armadilhas piloto |
| `SOT.md` | Estado macro |
| Bulk script | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` |
| Entrada FB piloto | `scripts/inventario_2026_05/entrada_fb_piloto.py` |
| Padronizar MIGRAÇÃO | `scripts/inventario_2026_05/padronizar_migracao.py` |
| Pipeline service | `app/odoo/services/inventario_pipeline_service.py` |
| Picking service | `app/odoo/services/stock_picking_service.py` |

---

## 📌 RESUMO EXECUTIVO PARA O USUARIO

**O que funcionou no sub-piloto**:
- 4 transferencias de lote (ETAPA A)
- 3 pickings criados/validados/liberados (ETAPA B) com novo distribuicao FIFO
- 3 invoices criadas pelo robo CIEL IT (ETAPA C)
- 3 NFs SEFAZ autorizadas (ETAPA D) — apos corrigir custo_medio = 0
- 1 entrada FB OK (RecLf 7, invoice 608645)
- 1 entrada LF MANUAL (picking 317306, NF 608629)

**O que precisa fazer na proxima sessao**:
- Rodar bulk para os 11 PROPOSTO restantes (10 LF→FB perda + 1 FB→LF industr)
- Cancelar SEFAZ NF 13150 via UI Odoo (24h)
- Filtrar etapa E para nao tentar entrada FB em NFs FB→LF

**Refators pendentes (nao bloqueiam)**:
- Threshold tolerancia 0.001 em transferir_quantidade_para_lote
- etapa_e_entrada_fb filtrar acoes que vao para FB

**Quando estiver tudo OK**: rodar LF completo (660 produtos) com max-produtos-picking=30.

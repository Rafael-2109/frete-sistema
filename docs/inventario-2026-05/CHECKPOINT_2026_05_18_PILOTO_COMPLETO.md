# CHECKPOINT — Piloto 210030325 LF COMPLETO (2026-05-18)

**Sessao Claude Code encerrada**: 2026-05-18 ~01:45
**Status global**: piloto end-to-end EXECUTADO em PROD com sucesso.
NF-e autorizada SEFAZ. Pronto para bulk da onda 1 (1.071 ajustes LF
restantes).

> Substitui `CHECKPOINT_2026_05_17_FIM_DIA.md` (snapshot anterior do
> trabalho pre-piloto).

---

## 1. Resultado do piloto

**Produto**: `[210030325] ROTULO - MOLHO DE ALHO PET 150 ML - CAMPO BELO`
**Empresa**: LA FAMIGLIA (cid=5)
**6 ajustes** (ids 139003-139008): 4 TRANSFERIR_LOTE + 2 PERDA_LF_FB.

### NF-e
- `account.move.id = 608607`
- name: `RETNA/2026/00029`
- chave SEFAZ: `35260518467441000163550010000131491006086070` (44 dig)
- cstat: `100` (Autorizado o uso da NF-e)
- valor untaxed: R$ 42.808,31 (amount_total=0 — perda interna)

### Estado fisico no Odoo

**LF (origem)**:
- Lote `26014` consolidado:
  - quant 218194 / loc 42 (LF/Estoque): **74.404 un**
  - quant 218196 / loc 53 (LF/Pré-Producao): **7.896 un**
  - **TOTAL: 82.300 un** (= inventario fisico)
- 5 quants antigos zerados (sem lote=32677, 24715×2=60967+189100,
  3009/24=113646, MIGRAÇÃO=176722).

**FB (destino fiscal)**:
- Picking saiu para "Parceiros/Clientes" (location virtual id=5). FB
  NAO recebe estoque automatico — NF de PERDA e' apenas fiscal.

### Pipeline executado

| Etapa | Acao | Resultado |
|---|---|---|
| Pre-flight | Mapear 5 quants reais LF | ✓ |
| Canary F7.6 | NF ref 588209 vs proposta | ✓ batem |
| ETAPA 1 | `criar_se_nao_existe('26014')` | ✓ lot_id=56533 |
| ETAPA 2 | 4 transferencias atomicas | ✓ todas EXATO+PARCIAL |
| ETAPA 3 | Picking LF→FB (CFOP 5903, 2 linhas) | ✓ picking 317290 |
| F5b | `confirmar_e_reservar + button_validate` | ✓ state=done |
| F5c | `action_liberar_faturamento` | ✓ (apos write incoterm+carrier) |
| F5d | aguardar robo CIEL IT criar invoice | ✓ invoice 608607 (~3min) |
| F5d.5 | setar payment_provider_id=38 | ✓ |
| F5e | Playwright SEFAZ | ✓ chave 44 dig, cstat=100 |

---

## 2. Estado do banco

```sql
SELECT id, acao_decidida, status, fase_pipeline, picking_id_odoo,
       invoice_id_odoo, chave_nfe
FROM ajuste_estoque_inventario WHERE id BETWEEN 139003 AND 139008
ORDER BY id;
```

| id | acao | status | fase_pipeline | picking | invoice | chave_nfe |
|---|---|---|---|---|---|---|
| 139003 | RENOMEAR_LOTE | EXECUTADO | TRANSF_OK | — | — | — |
| 139004 | RENOMEAR_LOTE | EXECUTADO | TRANSF_OK | — | — | — |
| 139005 | RENOMEAR_LOTE | EXECUTADO | TRANSF_OK | — | — | — |
| 139006 | RENOMEAR_LOTE | EXECUTADO | TRANSF_OK | — | — | — |
| 139007 | PERDA_LF_FB | EXECUTADO | F5e_SEFAZ_OK | 317290 | 608607 | 352605... |
| 139008 | PERDA_LF_FB | EXECUTADO | F5e_SEFAZ_OK | 317290 | 608607 | 352605... |

**APOS REGENERAR com D004 generalizada (2026-05-18 ~02:10)**:

```sql
SELECT COUNT(*) FILTER (WHERE status='PROPOSTO') proposto,
       COUNT(*) FILTER (WHERE status='EXECUTADO') executado,
       COUNT(*) total
FROM ajuste_estoque_inventario WHERE ciclo='INVENTARIO_2026_05';
-- Atual: PROPOSTO=23207, EXECUTADO=6, total=23213
```

**Comparativo antes (23.633 PROPOSTO) vs depois (23.207 PROPOSTO)**:

| acao_decidida | ANTES | DEPOIS | DIFF |
|---|---|---|---|
| INDISPONIBILIZAR_LOCAL | 948 | 402 | -546 |
| INDISPONIBILIZAR_LOTE | 18.418 | 17.668 | -750 |
| RENOMEAR_LOTE | 640 | **1.799** | +1.159 (D006 em FB+CD) |
| TRANSFERIR_CD_FB | 471 | 362 | -109 |
| TRANSFERIR_FB_CD | 2.087 | 1.907 | -180 |
| DEV_LF_FB / INDUSTRIALIZACAO / PERDA | inalterado (onda 1 LF) | | 0 |
| **TOTAL** | **23.633** | **23.207** | **-426 (-1.8%)** |

**NFs SEFAZ economizadas**: 289 NFs (-8.0%) — ~16h economizadas no bulk.
Backup: `/tmp/backup_inventario_2026_05/ajustes_pre_regen_20260518_020850.sql`.

---

## 3. 5 fixes generalizados (todos commitados em `a8e0d0bb`)

Detalhes completos: `00-decisoes/D006-transferir-quantidade-entre-lotes-nao-renomear.md`
secao "Licoes aprendidas — piloto 210030325 LF (2026-05-18)".

| # | Fix | Onde |
|---|---|---|
| L1 | `StockPickingService` defaults `incoterm=6 (CIF)` + `carrier_id=996 (NACOM)` | `stock_picking_service.py:35-37` |
| L2 | `_resolver_cids_e_menu(company_id)` — LF=5/217, NACOM=1-3-4/124 | `playwright_nfe_transmissao.py:450-462` |
| L3 | `_fechar_modais_tecnicos()` antes de cada click | `playwright_nfe_transmissao.py:580-620` |
| L4 | `_tratar_wizard_confirmacao()` apos Transmitir NF-e | `playwright_nfe_transmissao.py:540-578` |
| L5 | `_garantir_payment_provider()` em F5d (idempotente, fallback reset_to_draft+post) | `inventario_pipeline_service.py:138-220` |

---

## 4. Tests

**117 passing** (97 baseline + 20 novos):
- 4 `criar_se_nao_existe` em `test_stock_lot_service.py`
- 14 em `test_stock_internal_transfer_service.py` (novo arquivo)
- 2 em `test_stock_picking_service.py` (incoterm/carrier defaults)

```bash
pytest tests/odoo/ -p no:randomly -q  # 117 passed
```

---

## 5. Scripts disponiveis

Todos com `--company-id` obrigatorio (regra usuario 2026-05-18):

```bash
# Listar IDs do piloto + capturar hash
python scripts/inventario_2026_05/04_propor_ajustes.py \
    --listar-ids='139003-139008'

# Aprovar subset por hash + company_id (workflow formal)
python scripts/inventario_2026_05/04_propor_ajustes.py \
    --aprovar-ids='139003-139008' \
    --hash=<sha> --company-id=5 --usuario=rafael

# Aprovar onda INTEIRA
python scripts/inventario_2026_05/04_propor_ajustes.py \
    --listar-onda=1
python scripts/inventario_2026_05/04_propor_ajustes.py \
    --aprovar-onda=1 --hash=<sha> --usuario=rafael

# Executar piloto (dry-run primeiro)
python scripts/inventario_2026_05/teste_210030325_lf.py \
    --company-id=5 --dry-run
python scripts/inventario_2026_05/teste_210030325_lf.py \
    --company-id=5 --confirmar --usuario=rafael
python scripts/inventario_2026_05/teste_210030325_lf.py \
    --company-id=5 --confirmar --confirmar-sefaz --usuario=rafael

# Extrair estado pos-execucao (replicavel por filial)
python scripts/inventario_2026_05/08_extrair_pos_execucao.py \
    --ciclo=INVENTARIO_2026_05 --company-id=5

# Debug SEFAZ via Playwright (com screenshots)
python scripts/inventario_2026_05/debug_sefaz_608607.py \
    --company-id=5 --max-tentativas=2 --intervalo-retry=15
```

---

## 6. Pendencias para proxima sessao (bulk onda 1)

### Bloqueantes

1. **Wrapper bulk para onda 1**: ate agora so existe wrapper especifico
   do produto 210030325. Para 1.065 ajustes restantes precisa de
   `09_executar_onda1_bulk.py` que:
   - Itere por (cod_produto, company_id)
   - Use `InventarioPipelineService` em batches
   - Lide com timeouts/erros parciais
2. **Aprovar onda 1**: rodar `--aprovar-onda=1 --hash=<sha>` para
   marcar 1.065 ajustes restantes APROVADO.
3. ~~Decidir sobre regerar onda 2-3 com D004 generalizada~~ ✅ FEITO
   2026-05-18 ~02:10. Resultado: -426 ajustes total, -289 NFs (-8%).
   Ondas 1-4 todas regeradas com D004 generalizada. 6 EXECUTADO do
   piloto preservados.

### Recomendado antes do bulk

4. **Validar onda 1 RENOMEAR_LOTE em outros produtos**: 644 ajustes
   `RENOMEAR_LOTE` na onda 4 — verificar se todos sao casos de
   transferencia (D006) ou se algum e' rename puro.

### Opcional (nao bloqueia bulk)

5. **F7.6 canary fiscal para outras NFs**: caso piloto usou NF ref
   `588209` (PERDA LF→FB). Para industrializacao usar `94457`, para
   transferencia inter-filial usar `94410`, para dev-industrializacao
   usar `147772`. Ver `MATRIZ_INTERCOMPANY` em `operacoes_fiscais.py`.

### Fora desta sessao (concluidos)

- ✅ `build.sh` item 22 com migration `2026_05_17_add_lote_destino_ajuste`
  (rodado em prod pelo usuario)
- ✅ D004 generalizada para FB (cid=1) + CD (cid=4) — alem de LF —
  removido `if cid == 5` no script 03 + recalculo de `lote_destino`
  por acao no script 04. **Pendente**: regerar diffs/ajustes ondas 2-3.

---

## 7. Comandos de validacao para nova sessao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. pytest baseline
pytest tests/odoo/ -p no:randomly -q | tail -3
# Esperado: 117 passed

# 2. Estado DB do piloto (deve estar EXECUTADO)
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT id, acao_decidida, status, fase_pipeline, chave_nfe
FROM ajuste_estoque_inventario
WHERE id BETWEEN 139003 AND 139008 ORDER BY id;
"
# Esperado: 6 rows, todos status=EXECUTADO

# 3. Estado DB onda 1 restante
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT status, COUNT(*) FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05'
  AND acao_decidida IN ('INDUSTRIALIZACAO_FB_LF', 'PERDA_LF_FB',
                        'DEV_FB_LF', 'DEV_LF_FB', 'DEV_CD_LF', 'DEV_LF_CD')
GROUP BY status;
"
# Esperado: PROPOSTO=1065, EXECUTADO=6

# 4. Extrator pos-piloto (deve mostrar 6 EXECUTADO_OK)
python scripts/inventario_2026_05/08_extrair_pos_execucao.py \
    --ciclo=INVENTARIO_2026_05 --company-id=5 --cod-produto=210030325
# Esperado: Resumo (6 ajustes): EXECUTADO_OK 6
```

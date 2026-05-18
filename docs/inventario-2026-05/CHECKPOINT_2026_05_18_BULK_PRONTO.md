# CHECKPOINT — Bulk pronto + Entrada FB integrada + MIGRAÇÃO padronizada (2026-05-18 madrugada)

**Sessao Claude Code encerrada**: 2026-05-18 ~02:50
**Status global**: piloto end-to-end consolidado (LF saida + FB entrada).
Bulk script `09_executar_onda1_bulk.py` criado + validado em dry-run.
Padronizacao MIGRAÇÃO (com Ç) aplicada em Odoo+DB+codigo.

> Substitui `CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md` (snapshot anterior
> apos saida LF, antes da entrada FB).

---

## 1. O que mudou nesta sessao

### 1.1 Entrada FB do piloto concluida

A NF emitida pela LF (608607, RETNA/2026/00029, CFOP 5903) precisava
de contrapartida na FB. Implementacao via padrao "Recebimento LF" ja
existente (`RecebimentoLfOdooService`), que usa o XML autorizado para
criar DFe → PO → picking entrada → invoice in_invoice.

Script criado: `scripts/inventario_2026_05/entrada_fb_piloto.py`.
Recursos:
- Idempotente (busca RecebimentoLf existente por `odoo_lf_invoice_id`)
- Cria 1 RecebimentoLf + 1 lote (auto, CFOP 5903, MIGRAÇÃO)
- Roda pipeline 0-18 (Fase 1-5) SINCRONO (sem RQ — para piloto)
- Fase 6-7 pulada (CFOP 5903 ∈ CFOPS_RETORNO → transfer_status='sem_transferencia')

**Resultado pos-execucao** (piloto 210030325 LF + entrada FB):

| Item | Valor |
|---|---|
| RecebimentoLf | id=4, status=processado, fase=7, etapa=37/37 |
| DFe FB | id=42860 (criado a partir do XML autorizado) |
| PO FB | C2619222 (id=41898, state=purchase) |
| Picking entrada FB | FB/IN/13150 (id=317291, state=done) |
| Invoice FB in_invoice | id=608609 (state=posted, total=R$ 42.808,31) |
| MovimentacaoEstoque local | 1 linha criada |
| transfer_status | sem_transferencia (CFOP 5903 nao vai para CD) |
| FB lote MIGRAÇÃO | +66.532 un = **229.351 un** total (consolidado) |
| LF lote 26014 | **82.300 un** (inalterado) |

### 1.2 Padronizacao MIGRAÇÃO (com Ç)

O sistema aceitava ambas as grafias historicamente:
- `MIGRAÇÃO` (com cedilha + til): lote 30400 antigo, 162.819 un
- `MIGRACAO` (sem cedilha): novo lote 56534 criado pelo piloto, 66.532 un

Padronizado tudo para **MIGRAÇÃO**:

**Odoo**:
- Transferencia: 66.532 un do lot 56534 → lot 30400 (StockInternalTransferService)
- lot 30400 'MIGRAÇÃO': 229.351 un (consolidado)
- lot 56534 'MIGRACAO': 0 un (zerado, pode ser desativado depois)

**DB local**:
- `UPDATE ajuste_estoque_inventario SET lote_destino='MIGRAÇÃO' WHERE lote_destino='MIGRACAO'` (1.236 linhas)
- `UPDATE recebimento_lf_lote SET lote_nome='MIGRAÇÃO' WHERE lote_nome='MIGRACAO'` (1 linha)

**Codigo**:
- `scripts/inventario_2026_05/entrada_fb_piloto.py` (LOTE_DESTINO)
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (fallback lote_destino)
- `scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py` (linhas 74, 369, 402; case-insensitive aceita ambas)
- `scripts/inventario_2026_05/04_propor_ajustes.py` (linha 246)
- `docs/inventario-2026-05/00-decisoes/D005-...md` (nota adicionada)

Script auxiliar criado para repetir a operacao se necessario:
`scripts/inventario_2026_05/padronizar_migracao.py` (idempotente).

### 1.3 Bulk script `09_executar_onda1_bulk.py` (NOVO)

Refatora a abordagem "por produto sequencial" do `teste_210030325_lf.py`
para uma abordagem **por tipo de processo** com ETAPAS pipelinadas:

```
ETAPA A — Transferencias de lote (intra-empresa, sem NF)
    Todos ajustes RENOMEAR_LOTE/TRANSFERIR_LOTE
    Paralelo (semaphore=5). Atomico via inventory adjustment.

ETAPA B — Pickings agrupados (saidas de NF)
    Todos ajustes PERDA/INDUS/DEV
    Agrupa por (company_origem, tipo_op, picking_type_id)
    Chunks de ate `max_produtos_por_picking` produtos
    Cada chunk = 1 picking com N linhas + F5b validar + F5c liberar

ETAPA C — Aguardar invoices CIEL IT (1 polling longo)
    f5d_aguardar_invoices em TODOS pickings de B

ETAPA D — SEFAZ (Playwright serial)
    f5e_transmitir_sefaz em TODAS invoices de C

ETAPA E — Entrada FB (replica entrada_fb_piloto.py em bulk)
    Para cada invoice SEFAZ-autorizada:
        criar RecebimentoLf + RecebimentoLfLote
        chamar RecebimentoLfOdooService.processar_recebimento (sincrono)
```

**Flags principais**:
- `--limite-produtos N`: processar so os primeiros N produtos (sub-piloto)
- `--max-produtos-picking N`: max produtos por picking (default 30)
- `--apenas-etapa A|B|C|D|E`: executar so 1 etapa (retomada)
- `--ate-etapa A|B|C|D|E`: executar ate uma etapa
- `--dry-run` / `--confirmar` / `--confirmar-sefaz`
- `--filtro-cod-produto X,Y,Z`: lista CSV

**Validado em dry-run** (10 produtos, max-produtos-picking=5):
- Total ajustes: 21 (5 RENOMEAR_LOTE + 14 PERDA_LF_FB + 2 INDUSTRIALIZACAO_FB_LF)
- Pickings planejados: 3 (1 grupo LF→FB perda dividido em 2, + 1 grupo FB→LF industrializacao)
- Valor estimado: R$ 8.239

---

## 2. Estado do banco apos esta sessao

```sql
SELECT
    COUNT(*) FILTER (WHERE status='PROPOSTO') proposto,
    COUNT(*) FILTER (WHERE status='EXECUTADO') executado,
    COUNT(*) FILTER (WHERE lote_destino='MIGRAÇÃO') com_cedilha,
    COUNT(*) FILTER (WHERE lote_destino='MIGRACAO') sem_cedilha
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05';
-- proposto=23207, executado=6, com_cedilha=1821, sem_cedilha=0
```

```sql
SELECT id, status, odoo_lf_invoice_id, odoo_picking_name, odoo_invoice_id
FROM recebimento_lf
WHERE id = 4;
-- 4 | processado | 608607 | FB/IN/13150 | 608609
```

---

## 3. Proximos passos planejados

### Teste com 10 produtos (sub-piloto via ordenacao por processo)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 0. Verificar baseline (117 tests + piloto OK)
pytest tests/odoo/ -p no:randomly -q | tail -3

# 1. Dry-run completo (ja feito) — confirma 3 pickings, valor R$ 8.239
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 --dry-run

# 2. Aprovar 10 produtos (caso ainda nao APROVADO)
python scripts/inventario_2026_05/04_propor_ajustes.py --listar-onda=1 | head -30
# (capturar hash)
# python scripts/inventario_2026_05/04_propor_ajustes.py \
#     --aprovar-onda=1 --hash=<sha> --usuario=rafael

# 3. ETAPA A+B (Lote + Pickings, sem aguardar invoices)
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 \
    --ate-etapa=B --confirmar --usuario=rafael

# 4. ETAPA C (aguardar invoices CIEL IT, paralelo polling 30 min max)
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --apenas-etapa=C --confirmar --usuario=rafael

# 5. ETAPA D (SEFAZ Playwright — IRREVERSIVEL apos cstat=100)
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --apenas-etapa=D --confirmar --confirmar-sefaz \
    --usuario=rafael

# 6. ETAPA E (Entrada FB para cada NF SEFAZ-autorizada)
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --apenas-etapa=E --confirmar --usuario=rafael

# 7. Validar pos-execucao por filial (replicavel)
python scripts/inventario_2026_05/08_extrair_pos_execucao.py \
    --ciclo=INVENTARIO_2026_05 --company-id=5
```

### LF completo (apos sub-piloto OK)

```bash
# Substituir --limite-produtos=10 --max-produtos-picking=5 por:
#     --max-produtos-picking=30 (sem --limite-produtos)
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --max-produtos-picking=30 \
    --confirmar --confirmar-sefaz --usuario=rafael
```

**Estimativa LF completo**:
- ETAPA A: ~660 produtos com RENOMEAR_LOTE (174 distintos) × 5-10s cada → ~5 min paralelo
- ETAPA B: 1.069 ajustes PICKING / 30 produtos = ~35 pickings → 35 × 30s validacao = ~18 min
- ETAPA C: 35 invoices aguardando robo CIEL IT → ~10-30 min (depende paralelismo)
- ETAPA D: 35 NFs SEFAZ Playwright × 1-2 min serial = 35-70 min
- ETAPA E: 35 entradas FB × 10s sincrono = ~6 min (poderia ser paralelo se RQ)
- **Total estimado**: 75-130 min vs ~200-300 min na abordagem antiga

### Riscos para o sub-piloto 10 produtos

1. **Lote_origem inexistente no Odoo**: se algum ajuste aponta lote_origem que nao existe, ETAPA A vai falhar (logada como TRANSF_FALHA). Mitigacao: revisar logs apos ETAPA A.
2. **Picking de retorno CFOP=5901 (INDUSTRIALIZACAO_FB_LF)**: ETAPA B agora suporta. Nao testado em produto real ainda. Mitigacao: ja' temos canary historico (NF 94457).
3. **Multi-produto picking**: o pipeline existente cria 1 invoice por picking, mesmo com N produtos. Robo CIEL IT precisa lidar com N linhas — testado em produtos diferentes (recebimento_lf historico)?
4. **Conflito de invoice numero (RETNA)**: cada filial usa sua propria sequencia. Sem risco.
5. **Robo CIEL IT lento sob carga**: G005 risco aberto. Mitigacao: comecar com 10 produtos, observar tempo.

---

## 4. Arquivos modificados (nesta sessao)

**Scripts novos**:
- `scripts/inventario_2026_05/entrada_fb_piloto.py` (NOVO, 240 LOC)
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (NOVO, 540 LOC)
- `scripts/inventario_2026_05/padronizar_migracao.py` (NOVO, 200 LOC)

**Scripts atualizados (padronizacao MIGRAÇÃO)**:
- `scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py` (4 edits)
- `scripts/inventario_2026_05/04_propor_ajustes.py` (3 edits)

**Docs atualizados**:
- `docs/inventario-2026-05/00-decisoes/D005-...md` (nota padronizacao)
- `docs/inventario-2026-05/CHECKPOINT_2026_05_18_BULK_PRONTO.md` (NOVO — este)

**DB local** (UPDATEs):
- `ajuste_estoque_inventario`: 1.236 linhas (`MIGRACAO` → `MIGRAÇÃO`)
- `recebimento_lf_lote`: 1 linha (id=60)
- `recebimento_lf`: 1 linha NOVA (id=4, status=processado)
- `recebimento_lf_lote`: 1 linha NOVA (id=60)

**Odoo** (operacoes):
- DFe FB criado (id=42860)
- PO C2619222 criado, confirmado, aprovado
- Picking FB/IN/13150 (id=317291) validado
- Invoice in_invoice 608609 posted (FB)
- 4 MovimentacaoEstoque locais
- Transferencia 66.532 un MIGRACAO→MIGRAÇÃO no lote consolidador FB

---

## 5. Comandos de validacao rapida

```bash
# Estado piloto + entrada FB
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT id, odoo_lf_invoice_id, odoo_dfe_id, odoo_po_name,
       odoo_picking_name, odoo_invoice_id, status, transfer_status
FROM recebimento_lf WHERE odoo_lf_invoice_id = 608607;
"
# Esperado: 1 row, status=processado, transfer_status=sem_transferencia

# Padronizacao MIGRAÇÃO
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT lote_destino, COUNT(*)
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND lote_destino LIKE 'MIGRA%'
GROUP BY lote_destino;
"
# Esperado: MIGRAÇÃO 1821 | MIGRACAO 0

# Bulk dry-run 10 produtos
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 --dry-run
# Esperado: 21 ajustes, 3 pickings, R$ 8.239
```

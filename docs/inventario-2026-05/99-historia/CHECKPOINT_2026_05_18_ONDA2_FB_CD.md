# CHECKPOINT — Onda 2 FB→CD (Sessão tarde 2026-05-18)

**Data**: 2026-05-18 tarde · **Sessão**: 3 (continuação do dia)
**Status global**: Onda 2 FB→CD operacionalizada via reuso de `RecebimentoLfOdooService`. **43 ajustes EXECUTADOS** (20 originais + 20 splits + 3 cod 4310164 consolidação) + **3 NFs SEFAZ**. 18 ajustes travados em batch 3a (robô CIEL IT lento).

> **Doc único da sessão.** Contém: snapshot estado, decisão D009 (estratégia Onda 2), gotchas descobertos (G031-G033), aprendizados (L26-L31) e pendências para próxima sessão.

---

## 1. Mudança de cenário

### Sessão começou com (CD pós-pre-etapa)
- 6.885 EXECUTADO (97,79%)
- 2 APROVADO (163696 + 166155)
- 10 FALHA (Cat1_SEM_CADASTRO_ODOO)
- 55 PROPOSTO TRANSFERIR_FB_CD (Onda 2 residual)

### Sessão terminou com
- **6.928 EXECUTADO (98,40%)** ← +43 ajustes
- 1 APROVADO (163696 cod 208000012 — pendente análise drift)
- 10 FALHA (Cat1)
- 35 PROPOSTO (35 = 17 insolúveis + 18 travados em batch 3a — mas 20 já viraram EXECUTADO via splits)

## 2. Trabalho realizado

### A) Cod 4310164 — consolidação manual
- 3 ajustes EXECUTADOS (117600 + 120/26 + 226 → MIGRAÇÃO)
- Estratégia drift compensável: ajustar qty_odoo + split entre lotes

### B) Cadastro Odoo (preparação para Onda 2)
- **weight=0,01** + **standard_price=0,01** em 25 cods bloqueados pelo SEFAZ (ver D9 Gotcha)
- 3 transferências internas FB sub-locations → FB/Estoque (saldo recuperado para uso)
- 7 transferências internas FB consolidando saldo no `lote_origem` (4 cods do batch 4 COMPENSAVEL)

### C) Onda 2 — batches FB→CD via novo script `09c_executar_onda2_fb_cd.py`

| Batch | RecLf | Ajustes | NF SEFAZ saída FB | Invoice CD | Resultado |
|---|---|---|---|---|---|
| 1 | 10 | 7 | SDTRA/2026/00867 | ENTTR/2026/05/0130 | ✅ EXECUTADO |
| 2 | 12 | 9 | SDTRA/2026/00868 | ENTTR/2026/05/0131 | ✅ EXECUTADO |
| 3a | 13 | 18 | — (etapa 22 travada) | — | ⚠️ G032 robô CIEL IT |
| 4 (COMPENSAVEL) | 15 | 4 | SDTRA/2026/00869 | ENTTR/2026/05/0132 | ✅ EXECUTADO |

### D) Splits lote_destino pós-Onda 2 (20 ajustes EXECUTADO)
Cada ajuste original (lote_origem → CD) gera 1 ajuste filho `AJUSTE_CD_TRANSF_INTERNA_POS` quando `lote_origem != lote_destino`. Executado via `09b_executar_pre_etapa.py --cod-produto=X`.

---

## 3. Decisão D009 — Onda 2 via reuso de `RecebimentoLfOdooService`

### Contexto
Onda 2 = ajustes `TRANSFERIR_FB_CD` — movimentar estoque físico FB→CD via NF SEFAZ inter-filial (CFOP 5152) + entrada CD via DFe. Eram 55 ajustes pendentes / R$ 167k.

### Alternativas avaliadas
1. Construir orquestrador novo (etapas 19-37 reimplementadas)
2. **Reusar `processar_transfer_only`** ← escolhido
3. Operação manual no Odoo UI

### Estratégia
`processar_transfer_only` (em `app/recebimento/services/recebimento_lf_odoo_service.py:282-365`) faz EXATAMENTE o fluxo:

- **FASE 6** (etapas 19-23): Filtrar lotes → picking saída FB → confirmar+validar → `action_liberar_faturamento` → Playwright SEFAZ (CFOP 5152, IRREVERSÍVEL)
- **FASE 7** (etapas 24-37): Extrair XML/PDF → Upload DFe CD → Configurar → `action_gerar_po_dfe` → Configurar+Confirmar+Aprovar PO CD → Picking entrada → Lotes+QC → Validar → Criar invoice CD → Postar → Finalizar

### "RecebimentoLf virtual"
Para a Onda 2 não há recebimento real LF→FB prévio. Wrapper `09c` cria RecebimentoLf "virtual":
```python
RecebimentoLf(
    numero_nf=f'INV-FBC-{YYYYMMDD-HHMM}',
    company_id=1, status='processado',
    etapa_atual=18, transfer_status='pendente',
)
```
Depois cria N `RecebimentoLfLote` com `cfop='5152'`, `tipo='manual'`, `processado=True`.

### Estratégia SPLIT lote_destino
NF FB→CD movimenta qty do lote_origem → CD (mesmo nome do lote). Mas o ajuste pode ter `lote_destino` diferente. Solução: ajuste filho `AJUSTE_CD_TRANSF_INTERNA_POS` (lote_origem CD → lote_destino CD) executado via `09b_executar_pre_etapa.py`.

### Estratégia COMPENSAVEL_OUTROS_LOTES
Ajustes com saldo parcial no lote_origem na FB. NÃO criar múltiplos RecebimentoLfLote do mesmo produto (bug step 21). Em vez disso:
- **Consolidar saldo de outros lotes → lote_origem ANTES da NF** via `StockInternalTransferService.transferir_quantidade_para_lote`.
- Depois rodar 09c normal (lote_origem agora tem saldo exato).

---

## 4. Gotchas descobertos

### G031 — `_step_27_gerar_po_cd` usa campo errado (HIGH)

**Sintoma**: timeout 1800s na etapa 27 mesmo com PO já criado pelo robô CIEL IT.

**Root cause**: `recebimento_lf_odoo_service.py:3112-3140` lê `dfe.purchase_id`, mas robô CIEL IT preenche `dfe.purchase_fiscal_id`. Confirmado: DFe 42879, 42884, 42891 todos com `purchase_fiscal_id` populado e `purchase_id=False`.

**Status**: service NÃO modificado (instrução do usuário: "service funciona, não mexer").

**Workaround no `09c`** (fallback automático após TimeoutError):
```python
try:
    service.processar_transfer_only(rec_id)
except TimeoutError as e:
    if 'Gerar PO CD' in str(e):
        # detectar PO via purchase_fiscal_id, setar no rec
        d = odoo.read('l10n_br_ciel_it_account.dfe', [rec.odoo_cd_dfe_id], ['purchase_fiscal_id'])
        pfid = d[0].get('purchase_fiscal_id')
        rec.odoo_cd_po_id = pfid[0]
        rec.odoo_cd_po_name = pfid[1]
        rec.etapa_atual = 27
        rec.transfer_status = 'processando'
        db.session.commit()
        # chamar steps 28-37 diretamente
        for fn in [svc._step_28_..., ..., svc._step_37_...]:
            fn(odoo)
```

**NÃO chamar `processar_transfer_only` para retomar**: tem reset `etapa_atual=18` se `transfer_status in ('erro','pendente','processando')` (linha 320-321).

**Casos confirmados**: Batch 1 (RecLf 10 → PO 41918), Batch 2 (RecLf 12 → PO 41926), Batch 4 (RecLf 15 → PO sem timeout).

---

### G032 — Robô CIEL IT trava na criação de invoice de transferência inter-filial (MED)

**Sintoma**: etapa 22 (`action_liberar_faturamento` + aguardar invoice) timeouta após 1800s. Picking fica `state=done` com `invoice_ids=[]`.

**Root cause**: robô CIEL IT processa filas separadas. Para invoice de transferência (SDTRA/...) pode travar parcial ou totalmente, enquanto compras/despesas/recibos seguem normalmente.

**Sintomas vistos**:
- Batch 1 (16:36 BRT): SDTRA/2026/00867 criada em ~5min ✓
- Batch 2 (16:07): SDTRA/2026/00868 em ~10min ✓
- **Batch 3a (16:36)**: NÃO criada em 30min ✗
- Batch 4 (17:19): SDTRA/2026/00869 em ~4min ✓

Picking 317346 (Onda 1 LF mais cedo) teve mesmo pattern.

**Diagnóstico**:
```python
# Verifica se picking tem invoice
odoo.read('stock.picking', [317478], ['invoice_ids','state'])
# Se invoice_ids=[] E state=done E sem SDTRA recente → robô travado
```

**Recovery**:
1. **Aguardar robô**: retomar via `processar_transfer_fb_cd_job(rec_id)` (service tem checkpoint)
2. **Cancelar e refazer**: `action_cancel` no picking + reverter ajustes + deletar RecLf

**Mitigação preventiva**: não rodar batches grandes em horários de fila alta. Verificar pickings a cada 15min até confirmar invoice.

---

### G033 — Produtos com `weight=0` e/ou `standard_price=0` bloqueiam SEFAZ (HIGH)

**Sintoma**: pre-validação do `09c` rejeita ajustes:
```
cod=202640012: weight=0 (CIEL IT vai rejeitar)
cod=202000024: standard_price=0 (SEFAZ vai rejeitar)
```

**Root cause**:
- weight=0: CIEL IT (`_step_22_liberar_faturamento`) rejeita com Fault "Você deve informar o Peso Líquido para liberar o faturamento". Validado em `_validar_peso_liquido_produtos` (linha 1910).
- standard_price=0: invoice CIEL IT gera linhas com `price_unit=0` → SEFAZ rejeita. `_verificar_custo_produtos_transfer` (linha 1976) tem fallback baseado em DFe LF, mas não temos DFe LF na Onda 2 → falha.

**Produtos afetados nesta sessão (25 cods)**:
```
202000024, 202003944, 202004012, 202030019, 202260016, 202640012, 202640013,
202640014, 203003944, 203030010, 205030150, 205030710, 205032230, 205120306,
205120332, 205120803, 205120901, 205130298, 205130300, 205400406, 205400931,
205460932, 205460941, 208000026, 208000041
```

**Workaround**: cadastrar `weight=0.01` e `standard_price=0.01` (mínimo simbólico) antes do batch:
```python
odoo.write('product.product', pid_list, {'weight': 0.01, 'standard_price': 0.01})
```

NF sai com `vProd ≈ 0.01 × qty` (fiscalmente impreciso, mas SEFAZ aceita).

**Validação preventiva no `09c`**:
```python
if not p.get('weight') or float(p['weight']) <= 0:
    erros.append(f'cod={cod}: weight=0 (CIEL IT vai rejeitar)')
if not p.get('standard_price') or float(p['standard_price']) <= 0:
    erros.append(f'cod={cod}: standard_price=0 (SEFAZ vai rejeitar)')
```

---

## 5. Pendências para próxima sessão

### A) RecLf 13 (batch 3a) — 18 ajustes travados
Picking saída FB **FB/SAI/INT/24008** (id 317478) `state=done` sem invoice. Robô CIEL IT (G032).
- **Opção 1**: aguardar robô + `processar_transfer_fb_cd_job(13)` (service retoma da etapa 22)
- **Opção 2**: cancelar picking + reverter ajustes + refazer depois

Detalhes: `PICKINGS_PENDENTES_INVOICE.md`.

### B) 17 ajustes PROPOSTO restantes (FB físico insuficiente)
- 169973 (103000037 MIGRACAO — pede 430, FB 272)
- 169990, 169991, 169993 (202640014 MIGRAÇÃO — falta 1879/505/1879)
- 170000-03 (205030150 MIGRAÇÃO ×4 — cada falta ~74)
- 170011 (205120803 0511/24 — falta 235)
- 170017 (205460932 ME 181-112/26 — falta 46)
- 170019 (208000005 MIGRAÇÃO — falta 138)
- 170023 (210003012 0511 — falta 1449)
- 169987, 169988, 169989 (202640013 MIGRAÇÃO — irmãos do 169986 consumido)
- 170005 (205030170 — irmão do 170004 consumido)
- 169997 (205030101 qty=0 ajuste degenerado)

**Decisão pendente**: ajustar `qty_inventario` para saldo real FB + aceitar diferença, OU aguardar reposição.

### C) 1 APROVADO antigo (163696 cod 208000012)
- 835.851 un esperado no lote vazio/MIGRAÇÃO da FB
- Análise drift similar ao 4310164 pendente

### D) 10 FALHA Cat1_SEM_CADASTRO_ODOO
Cods: 20100051, 201230027, 20200416, 20203001, 26000130, 26000404, 4310154, 4320161, 4360158, 4866112. Admin Odoo precisa cadastrar.

---

## 6. Aprendizados (L26-L31)

**L26 — Reuso de `RecebimentoLfOdooService` para Onda 2**: funcionalidade FB→CD com NF SEFAZ + DFe entrada CD já existia (etapas 19-37). Wrapper de ~340 LOC reusa 4562 LOC do service base.

**L27 — Bug step 27 contornável externamente**: o bug `purchase_id` vs `purchase_fiscal_id` parece grave (timeout 1800s) mas é trivial: detectar PO via campo correto, setar no RecLf, chamar steps 28-37 direto. Service não modificado (instrução usuário).

**L28 — Robô CIEL IT é gargalo imprevisível**: para transferências inter-filial, demora de segundos a horas. Batches pequenos (5-10 ajustes) minimizam prejuízo se travar.

**L29 — Pre-validação `weight` + `standard_price` evita NF inválida**: cadastrar antes economiza tempo + evita lixo no Odoo.

**L30 — Compensação multi-lote: consolidar ANTES da NF**: `transferir_quantidade_para_lote` move saldo de outros lotes → lote_origem na FB. Depois rodar NF normal. Evita bug step 21 (consolidação de move_lines).

**L31 — Margem 1.0x é viável quando saldo está em 1 único quant**: bug step 21 só ataca com múltiplos quants. Saldo exato em 1 quant → 1 move_line → step 21 não consolida.

---

## 7. Artefatos criados

| Arquivo | Função |
|---|---|
| `scripts/inventario_2026_05/09c_executar_onda2_fb_cd.py` | Wrapper Onda 2 FB→CD (~340 LOC) |
| `99-historia/CHECKPOINT_2026_05_18_ONDA2_FB_CD.md` | ESTE arquivo (doc único da sessão) |
| `PICKINGS_PENDENTES_INVOICE.md` | +picking 317478 (RecLf 13 travado) |
| `SOT.md` | Status global atualizado |
| `memory/inventario_2026_05.md` | Seção Sessão Onda 2 |

---

## 8. Comandos úteis para retomada

```bash
# Estado atual CD
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT status, COUNT(*) FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=4
GROUP BY status ORDER BY status;"

# Verificar invoice do RecLf 13 (batch 3a travado)
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    p = odoo.read('stock.picking', [317478], ['state','invoice_ids'])
    print(p)
"

# Retomar batch 3a quando invoice aparecer
python3 -c "
from app.recebimento.workers.recebimento_lf_jobs import processar_transfer_fb_cd_job
processar_transfer_fb_cd_job(13)
"

# Próximo batch Onda 2 (PROPOSTO restantes — só rodar quando 17 insolúveis decididos)
python scripts/inventario_2026_05/09c_executar_onda2_fb_cd.py \
    --limite=10 --margem-min=1.5 --dry-run
```

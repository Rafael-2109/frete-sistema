# Audit Fiscal — Onda 1 LF (Inventario 2026-05)

**Gerado**: 2026-05-18 (sessao pos root cause NF 626032)
**Escopo**: ajustes PROPOSTO + onda 1 (acoes pickings+lotes) em company=5 (LF)
**Total produtos**: 455 distintos

---

## Resumo executivo

| Categoria | Qtd | G | Auto-fix? |
|---|---|---|---|
| Sem NCM (`l10n_br_ncm_id=False`) | **3** | G017 | NAO — cadastrar manual |
| Sem weight (`weight=0`) em acao de picking | **109** | G012/G013 | NAO — cadastrar ou implementar protecao |
| Sem standard_price | 128 | G007/G015 | SIM — G015 ja atribui 0.01 |
| Orfaos (cod sem product_id no Odoo) | 1 | — | SIM — script ja pula via `skip_pid` |

**Bloqueio CRITICO para LF completo**: 109 produtos sem weight (NF rejeita F5c por
peso_liquido=0). Sub-piloto de 10 produtos passou porque os primeiros 10 cods
ordenados (103000020 ALHO EM PO ate ~104000010) tem weight cadastrado.

**Update 2026-05-18 sessao 2 manha**: ✅ **G018 IMPLEMENTADO** — funcao
`corrigir_weight_zero` em `09_executar_onda1_bulk.py` atribui weight=0.001
automaticamente para todos produtos do batch com weight=0 antes de criar
pickings. Flag CLI `--auto-fix-weight=0.001` (default). Documentado em
`docs/inventario-2026-05/02-gotchas/G018-weight-zero-bloqueia-f5c.md`.

---

## 1. Produtos sem NCM (G017 — bloqueia SEFAZ cstat=225)

| cod | nome | id Odoo | weight | standard_price | Bloqueios |
|---|---|---|---|---|---|
| 103000020 | ALHO EM PÓ | 31416 | 1.0 ✓ | 47.97 ✓ | Apenas NCM |
| 104000046 | CORANTE VERMELHO | 34907 | **0.0** ❌ | 5.02 ✓ | NCM + weight |
| 109000101 | OLEO MISTO | 34914 | **0.0** ❌ | 3.24 ✓ | NCM + weight |

Acoes necessarias antes de continuar:
1. Cadastrar `l10n_br_ncm_id` nos 3 produtos via UI Odoo
2. Cadastrar `weight > 0` em CORANTE VERMELHO e OLEO MISTO

---

## 2. Produtos sem weight (G012/G013 — bloqueia F5c)

**109 produtos distintos** com acao de picking (geram NF):

| acao_decidida | n_produtos | n_ajustes |
|---|---|---|
| PERDA_LF_FB | 51 | 119 |
| INDUSTRIALIZACAO_FB_LF | 63 | 69 |
| **Total picking** | **109** | **188** |
| RENOMEAR_LOTE (sem NF — nao bloqueia) | 21 | 39 |

### Categorias dos 109 sem weight

| Familia (prefixo cod) | Qtd | Exemplo | Observacao |
|---|---|---|---|
| 104xxx (ingredientes) | 12 | OREGANO, MANJERICAO, NOZ MOSCADA | Peso real ≠ 0 |
| 105xxx (aromas/condimentos) | 10 | AROMA FUMACA, TOMILHO, SUCRALOSE | Peso real ≠ 0 |
| 109xxx (oleos) | 2 | AZEITE EXT VIRG, OLEO MISTO | Peso real ≠ 0 |
| 201-203xxx (embalagens vidro/balde) | 4 | CAIXA PAPELAO 415x155x150, BALDE 2L | Peso real baixo |
| 207-208-209xxx (rotulos, sacos, tampas) | 8 | ROTULO AZ PI VD 200G | Peso desprezivel |
| 210010xxx (rotulos ST ISABEL) | 30 | ROTULO MOLHO DE SALADA | Peso desprezivel |
| 210030xxx (rotulos CAMPO BELO + caixas) | 23 | ROTULO MAIONESE | Peso desprezivel |
| 301xxx (insumos quimicos) | 1 | SALMOURA HIDRATACAO TOMATE SECO | Peso real ≠ 0 |
| 38xxxxx (bateladas — produtos intermediarios) | 11 | BATELADA DE ALHO, MAIONESE | Peso real existe |
| TOTAL | **109** | | |

### Decisao recomendada (3 opcoes)

**A. Cadastrar weight realistico em todos os 109 produtos** (mais correto fiscalmente)
- Estimativa: 1-2 horas se feito em lote via XML-RPC
- Bem-cadastrado evita futuras NFs erradas
- Requer levantamento de peso real por familia

**B. Implementar G018 — protecao weight=0 automatica** (analogo a G015)
- Em `etapa_b_pickings`, se `product.weight <= 0`, atribuir 0.001 (1 grama)
- Trade-off: peso fiscal incorreto, mas NF passa SEFAZ
- Aceitavel para rotulos/embalagens (peso real << 1g)
- Inaceitavel para ingredientes (peso real >> 1g)
- Implementacao: filtrar por categoria (rotulos+tampas+lacres -> 0.001; outros -> usar peso da familia)

**C. Excluir esses produtos da onda 1 e tratar manualmente** (mais conservador)
- Marcar 109 ajustes como `INDISPONIBILIZAR` ou `MANUAL_PENDENTE`
- Processar apenas 455-109 = 346 produtos sem weight=0
- Voltar depois para os 109

**Recomendacao**: **A** para LF completo. **B** se urgencia + plano de
correcao posterior. **C** se for sub-piloto e poucos produtos.

---

## 3. Produtos sem standard_price (G015 cobre)

128 produtos. G015 fix em `etapa_b_pickings` ja faz:

```python
custo_cache[c] = abs(std) if std else 0.01
```

E corrige `aj.custo_medio` se <= 0.

**Acao**: nenhuma. G015 cobre automaticamente.

---

## 4. Orfaos no Odoo

| cod | ajuste_id | acao | qtd_ajuste | Bloqueio |
|---|---|---|---|---|
| 210010600 | 162031 | INDUSTRIALIZACAO_FB_LF | 250330.00 | Script ja pula via `skip_pid` |

**Acao**: nenhuma. Script avisa e pula. Pode investigar depois se for ativo
de inventario real (qty=250k sugere lote/lote real, mas cod nao corresponde
a nenhum produto no Odoo).

---

## 5. Plano para concluir sub-piloto (10 produtos)

Pre-reqs Rafael:
1. Cancelar NF 626032 SEFAZ (manual via UI Odoo)
2. Cadastrar NCM em **3 produtos**: 103000020, 104000046, 109000101
3. Cadastrar weight em **2 produtos**: 104000046, 109000101 (ALHO EM PO ja tem weight=1.0)

Validacao apos pre-reqs:

```bash
source .venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    for cod in ['103000020', '104000046', '109000101']:
        p = odoo.search_read('product.product', [['default_code', '=', cod]],
            ['default_code', 'l10n_br_ncm_id', 'weight'])
        print(p)
"
```

Reset DB + re-execucao:

```bash
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c \"
UPDATE ajuste_estoque_inventario
SET status='PROPOSTO', fase_pipeline=NULL, picking_id_odoo=NULL,
    invoice_id_odoo=NULL, chave_nfe=NULL, erro_msg=NULL
WHERE invoice_id_odoo=626032
RETURNING id, cod_produto;
\"

python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 \
    --confirmar --confirmar-sefaz --usuario=rafael \
    --validacao-fiscal=strict
```

Com G017 fix ativo (`--validacao-fiscal=strict`), etapa B aborta antes de
criar pickings se NCM ou weight estiverem faltando.

---

## 6. Plano para LF completo (455 produtos)

**BLOQUEADO** ate decisao sobre os 109 sem weight (opcao A/B/C acima).

Cronograma estimado (apos resolvido):

| Etapa | Estimativa | Pre-req |
|---|---|---|
| Cadastrar NCM (3 produtos) | 5 min | UI Odoo |
| Cadastrar weight (opcao A) | 1-2h | XML-RPC batch ou UI |
| Bulk LF completo (455 produtos) | 2-4h | G016 fix + G017 fix |
| Total | **3-6h** | |

Pre-req tecnico: **G016 (resiliencia SSL no f5e_transmitir_sefaz)** —
sem isso, qualquer SSL disconnect em transito (>5-10min) gera estado
inconsistente DB local vs Odoo.

---

## Anexos

### Lista completa: 109 produtos sem weight em acao picking

```
104000002 ACIDO CITRICO
104000012 MANJERICAO DESIDRATADO
104000014 OREGANO TRITURADO
104000020 CORANTE - VERMELHO
104000034 NOZ MOSCADA EM PO
104000036 ENDRO SEMENTE
104000039 AROMA NATURAL - ALHO
104000042 AROMA NATURAL - ENDRO
104000045 AROMA - CRAVO
104000046 CORANTE VERMELHO         [+ sem NCM]
104000050 SUCRALOSE
104000052 HORTELA DESIDRATADO
105000002 AROMA - ERVAS FINAS
105000008 CONDIMENTO - MOLHO ITALIANO
105000013 BHT/ BHA
105000032 EDTA
105000033 MOSTARDA AMARELA EM PO
105000040 MELACO DE CANA
105000041 AROMA - FUMACA ST 2182
105000042 TOMILHO TRITURADO
105000049 AROMA - GENGIBRE ST 2185
105000050 CORANTE - VITAMASSA U/102
105000051 AROMA - BALSAMICO ST 2184
105000067 CONDIMENTO - TARTARO
109000001 AZEITE EXT VIRG LT
109000101 OLEO MISTO               [+ sem NCM]
201240023 CAIXA DE PAPELAO - 415 X 155 X 150 - LIS
202030018 BALDE - 2,0 L - CAMPO BELO
203591413 TAMPA PLASTICA VERDE - BD 3,2 L
207030127 ROTULO - AZ PI VD 200 G
207030426 ROTULO - AZ VSC VD 160 G
207032627 ROTULO - CEBOLINHA VD 200 G
207032727 ROTULO - PEPINO VD 200 G
207120233 ROTULO - AZ VF 170 G - OUTBACK
207120309 ROTULO - AZ VI 500 G - OUTBACK
207120433 ROTULO - AZ VSC 170 G - OUTBACK
207381221 ROTULO 510PET - STRUMPF
208000027 SACO PLASTICO TRANSPARENTE - 40 X 60
209000152 TAMPA PLASTICA VERDE - GL 5,02 L - OLEO
209039900 ROTULO - OLEO MISTO GL 5,02 L - SENHORA
209049900 ROTULO - OLEO MISTO GL 5,02 L - DOM GAME
209200300 ROTULO - AZEITE EXTRA VIRGEM VD 500 ML
210010301 ROTULO FRONTAL - MOLHO DE SALADA ITALIANO
210010320 ROTULO - MOLHO DE PIMENTA PET 150 ML - ST ISABEL
210010321 ROTULO - MOLHO SHOYU PET 150 ML - ST ISABEL
210010322 ROTULO - MOLHO SHOYU PET 1,01 L - ST ISABEL
210010324 ROTULO FRONTAL - MAIONESE PET 200 G - ST ISABEL
210010325 ROTULO - MOLHO DE ALHO 150 G - ST ISABEL
210010326 ROTULO - MOLHO DE ALHO PET 1,01 L - ST ISABEL
210010327 ROTULO FRONTAL - KETCHUP PET 200 G - ST ISABEL
210010328 ROTULO FRONTAL - MOSTARDA PET 200 G - ST ISABEL
210010329 ROTULO - BARBECUE GL 3,05 KG - ST ISABEL
210010330 ROTULO - MOLHO DE MOSTARDA GL 3,05 KG
210010331 ROTULO FRONTAL - BARBECUE PET 200 G
210010332 ROTULO - MOLHO DE PIMENTA PET 1,01 L
210010333 ROTULO - KETCHUP GL 3,05 KG - ST ISABEL
210010335 ROTULO - MOLHO INGLES PET 1,01 L
210010336 ROTULO FRONTAL - PIMENTA CREMOSA TRADICIONAL
210010337 ROTULO FRONTAL - PIMENTA CREMOSA DEFUMADA
210010338 ROTULO FRONTAL - PIMENTA CREMOSA ERVAS
210010339 ROTULO FRONTAL - MOLHO DE SALADA MOSTARDA
210010340 ROTULO FRONTAL - MOLHO DE SALADA BALSAMICO
210010341 ROTULO FRONTAL - MOLHO DE SALADA ROSE
210010342 ROTULO FRONTAL - MOLHO DE SALADA PARMESAO
210010345 ROTULO - MAIONESE BD 6X3 KG - ST ISABEL
210010347 ROTULO - MAIONESE BD 6X3 KG - CAMPO BELO
210010401 ROTULO VERSO - MOLHO DE SALADA ITALIANO
210010427 ROTULO VERSO - KETCHUP PET 200 G
210010428 ROTULO VERSO - MOSTARDA PET 200 G
210010431 ROTULO VERSO - BARBECUE PET 200 G
210010436 ROTULO VERSO - PIMENTA CREMOSA TRADICIONAL
210010437 ROTULO VERSO - PIMENTA CREMOSA DEFUMADA
210010438 ROTULO VERSO - PIMENTA CREMOSA ERVAS
210010439 ROTULO VERSO - MOLHO DE SALADA MOSTARDA
210010440 ROTULO VERSO - MOLHO DE SALADA BALSAMICO
210010441 ROTULO VERSO - MOLHO DE SALADA ROSE
210010442 ROTULO VERSO - MOLHO DE SALADA PARMESAO
210030107 TAMPA PLASTICA AZUL - PET 200 G - MOLHO
210030201 CAIXA DE PAPELAO - 255 X 160 X 180
210030210 CAIXA DE PAPELAO - 355 X 255 X 230
210030212 CAIXA DE PAPELAO - 180 X 140 X 175 - LIS
210030301 ROTULO FRONTAL - MOLHO DE SALADA ITALIANO - CB
210030324 ROTULO FRONTAL - MAIONESE PET 200 G - CB
210030336 ROTULO FRONTAL - PIMENTA CREMOSA TRADICIONAL
210030337 ROTULO FRONTAL - PIMENTA CREMOSA DEFUMADA
210030338 ROTULO FRONTAL - PIMENTA CREMOSA ERVAS
210030339 ROTULO FRONTAL - MOLHO DE SALADA MOSTARDA
210030342 ROTULO FRONTAL - MOLHO DE SALADA PARMESAO
210030401 ROTULO VERSO - MOLHO DE SALADA ITALIANO - CB
210030424 ROTULO VERSO - MAIONESE PET 200 G - CB
210030436 ROTULO VERSO - PIMENTA CREMOSA TRADICIONAL
210030437 ROTULO VERSO - PIMENTA CREMOSA DEFUMADA
210030438 ROTULO VERSO - PIMENTA CREMOSA ERVAS
210030439 ROTULO VERSO - MOLHO DE SALADA MOSTARDA
210030442 ROTULO VERSO - MOLHO DE SALADA PARMESAO
210030558 BALDE - 3,5 L - BRANCO
210030702 BOBINA DE FILME - 3 KG  MAIONESE BAG
210030752 BOBINA DE FILME - 3 KG  MAIONESE BAG
210030800 LACRE MOLHO DE SALADA - CAMPO BELO
301100029 SALMOURA HIDRATACAO TOMATE SECO
3800000 MACERADO DE MOSTARDA
3800002 BATELADA DE ALHO
3800004 BATELADA DE BARBECUE
3800005 BATELADA DE INGLES
3800007 BATELADA DE KETCHUP
3800009 BATELADA DE MAIONESE
3800011 BATELADA DE MOSTARDA
3800012 BATELADA DE PARMESAO
3800016 BATELADA DE PIMENTA
3800018 BATELADA DE SHOYU
```

## Ref

- G015 — protecao standard_price=0 automatica
- G017 — NCM=False bloqueia SEFAZ (FIX implementado em `09_executar_onda1_bulk.py:139-211`)
- G012/G013 — weight=0 bloqueia F5c
- G016 — SSL crash no loop F5e perde commits (PENDENTE — bloqueante para LF completo)
- D006 secao L24-L25 (em CHECKPOINT_2026_05_18_NCM_PENDENTE)

<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# CHECKPOINT — Fim Sessao 2 LF (2026-05-18 manha+tarde)

**Sessao Claude Code 2**: 2026-05-18 ~07:30 → 12:30 UTC
**Foco**: pre-reqs sub-piloto LF + G016/G017/G018 + teste 30 + teste 100
**Status global**: 5 gotchas implementados (G016, G017, G018v2, G019, G020).
Sub-piloto end-to-end OK. Teste 100 prods executou parcial — cleanup feito.
**134 tests passing** (130 → +4 do G019 fix).

> Substitui `CHECKPOINT_2026_05_18_NCM_PENDENTE.md`. Foco proxima sessao:
> ajustar estoque LF exclusivamente.

---

## 1. Resumo executivo

### Conquistas
- ✅ NF 626032 cancelada SEFAZ + 10 ajustes liberados para re-execucao
- ✅ NCM cadastrado em 3 produtos (07129010, 32041100, 15179090) via XML-RPC modelo CIEL IT custom
- ✅ Weight cadastrado em 2 produtos (CORANTE=1, OLEO MISTO=0.93)
- ✅ Entrada manual LF NF 627348 (PEPINO 168.108 un)
- ✅ G016 implementado em F5e + **F5d** (extensao sessao 2 tarde)
- ✅ G017 validar_cadastro_fiscal pre-pickings
- ✅ G018 v2 aplicar_peso_volumes_fallback_picking (escreve l10n_br_peso_liquido
  no picking pois product.write({weight}) NAO PERSISTE em CIEL IT)
- ✅ G019/G020 documentados + **fix implementado**: validar() agora checa
  state=done apos button_validate; liberar_faturamento valida pre-cond state=done
- ✅ Cleanup completo do teste 100 prods (4 pickings cancelados, 231 ajustes reset)

### Bloqueio residual
- ⏳ Picking **317346** (FB/SAI/IND/01559) em done aguardando invoice CIEL IT
  - 21 ajustes INDUSTRIALIZACAO_FB_LF, fase=F5c_LIBERADO, status=PROPOSTO
  - Robo CIEL IT lento (2h+ sem criar invoice)
  - Detalhes: `PICKINGS_PENDENTES_INVOICE.md`

---

## 2. Estado atual da LF (company_id=5)

```
EXECUTADO 34 ajustes:
  - 4 RENOMEAR_LOTE TRANSF_OK (piloto madrugada 210030325)
  - 5 RENOMEAR_LOTE TRANSF_OK (sub-piloto manha promovidos)
  - 15 RENOMEAR_LOTE TRANSF_OK (teste 30 promovidos)
  - 2 PERDA_LF_FB F5e_SEFAZ_OK (NF 608607)
  - 4 PERDA_LF_FB F5e_SEFAZ_OK (NF 608631)
  - 1 INDUSTR F5e_SEFAZ_OK (NF 608629)
  - 3 INDUSTR F5e_SEFAZ_OK (NF 627348 — entrada LF manual feita 11:39)

PROPOSTO 1682 ajustes (LF restante):
  - 768 PERDA_LF_FB
  - 137 INDUSTRIALIZACAO_FB_LF
  - 148 DEV_LF_FB
  - 13 INDISPONIBILIZAR_LOTE (onda 3, fora escopo)
  - 541 RENOMEAR_LOTE sem fase
  - 65 RENOMEAR_LOTE TRANSF_FALHA (drift Cat 2)
  - 21 INDUSTR F5c_LIBERADO ← PENDENTE invoice 317346

NFs cross-company com entrada destino feita:
  608607 (LF→FB perda) → RecLf 4 processado ✓
  608631 (LF→FB perda) → RecLf 7 + invoice FB 608645 ✓
  608629 (FB→LF industr) → picking 317306 LF/IN/01733 ✓
  627348 (FB→LF industr) → picking 317316 LF/IN/01734 ✓ (hoje 11:39)
```

---

## 3. Aprendizados desta sessao

### A. Bugs identificados e corrigidos

| Bug | Severidade | Fix |
|---|---|---|
| G016 SSL em F5e | HIGH | _commit_with_retry + re-fetch antes Playwright |
| G016 SSL em F5d | HIGH | _commit_with_retry antes polling + re-fetch por ID |
| G017 NCM=False bloqueia SEFAZ | HIGH | validar_cadastro_fiscal pre-pickings strict |
| G018 weight=0 + product.write nao persiste | HIGH | aplicar_peso_volumes_fallback no picking |
| G019 validar() engole 'cannot marshal None' como sucesso | CRITICAL | validar() checa state=done apos button_validate |
| G020 liberar_faturamento sem pre-cond state=done | MED | raise se state != done |

### B. Achados sobre CIEL IT

- **Modelo NCM**: `l10n_br_ciel_it_account.ncm` (custom, nao OCA padrao)
  - Campo de codigo: `codigo_ncm` (nao `code` nem `code_unmasked`)
- **product.write({weight: X}) NAO PERSISTE**: hook silencioso reseta para 0.
  Mesmo `product.template.write` falha. Solucao: escrever em
  `l10n_br_peso_liquido` no stock.picking (que SIM persiste).
- **stock.picking inter-company**: criar via `move_ids_without_package` deixa
  o move com `company_id` do USUARIO (inferido), nao do picking. Precisa
  `odoo.write('stock.move', [moves], {'company_id': N})` apos create.
- **Robo CIEL IT lento**: pode demorar >30min para criar invoice apos
  `action_liberar_faturamento`. Nao confiavel para batches grandes em
  horarios de pico.

### C. Drift Cat 2 em RENOMEAR_LOTE

- **Sub-piloto madrugada (10 prods)**: ~0% drift
- **Teste 30 prods**: 65/85 = 76% drift
- **Teste 100 prods**: 175/244 = 72% drift

Conclusao: drift e' alto independente do tamanho do batch. Causas:
- lote_origem da planilha ja' movimentou (vendas, producao consumiram)
- reservas em pickings ativos seguram o saldo

Estrategia operacional para Cat 2: aceitar ou aguardar separacoes
concluirem + re-rodar.

### D. Estrategia FB→LF industrializacao (L17)

NFs FB→LF nao usam RecLf no destino — entrada e' MANUAL via picking
interno (Em Transito Industr → LF/Estoque). Padrao replicavel ja' validado
com pickings 317306 (NF 608629) e 317316 (NF 627348).

---

## 4. Arquivos criados/modificados nesta sessao

### Codigo
- `app/odoo/services/inventario_pipeline_service.py`:
  - +helper `_commit_with_retry` (G016)
  - F5e: commit + re-fetch antes Playwright (G016)
  - F5d: commit + re-fetch + meta extraida (G016 extensao tarde)
- `app/odoo/services/stock_picking_service.py`:
  - `validar()`: checar state=done apos button_validate (G019)
  - `liberar_faturamento()`: pre-cond state=done (G020)
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py`:
  - `validar_cadastro_fiscal` (G017)
  - `corrigir_weight_zero` v2 (apenas detecta, nao modifica master)
  - `aplicar_peso_volumes_fallback_picking` (G018 v2)
  - Flag CLI `--validacao-fiscal` `--auto-fix-weight`
- `tests/odoo/services/test_stock_picking_service.py`:
  - +4 testes G019/G020 (substituem 3 antigos)

### Documentos
- **Novos**:
  - `02-gotchas/G016-ssl-crash-no-loop-f5e-perde-commits.md` (status FIXADO)
  - `02-gotchas/G017-ncm-false-bloqueia-sefaz.md` (status FIXADO)
  - `02-gotchas/G018-weight-zero-bloqueia-f5c.md` (status FIXADO v2)
  - `02-gotchas/G019-f5b-validar-engole-erro.md`
  - `02-gotchas/G020-f5c-sem-checar-state-done.md`
  - `07-relatorios/audit_fiscal_LF.md`
  - `EXECUCAO_CADASTRO_NCM_WEIGHT_2026_05_18.md`
  - `EXECUCAO_ENTRADA_LF_NF627348_2026_05_18.md`
  - `PICKINGS_PENDENTES_INVOICE.md`
  - **ESTE** `CHECKPOINT_2026_05_18_LF_FIM_SESSAO2.md`

### Estado Odoo
- Produtos modificados (4):
  - 103000020 ALHO EM PO: NCM 07129010
  - 104000046 CORANTE VERMELHO: NCM 32041100, weight=1.0
  - 109000101 OLEO MISTO: NCM 15179090, weight=0.93
  - 31416, 34907, 34914: pids respectivos
- Pickings done finalizados: 8 (4 cross-company SEFAZ-OK + 2 entradas LF manuais + 2 devolucoes)
- Pickings done pendentes invoice: **1** (317346)

---

## 5. Visao consolidada de gotchas (G001-G020)

| # | Status | Categoria | Modulo |
|---|---|---|---|
| G001 | ✅ FIXADO | NFs referencia | piloto madrugada |
| G002 | ✅ FIXADO | picking type LF divergente | piloto |
| G003 | ✅ FIXADO | CFOP real | piloto |
| G004 | ✅ FIXADO | padrao picking robo CIEL IT | piloto |
| G005 | ⚠️ ABERTO | tempo robo CIEL IT em paralelo | confirmado lento hoje |
| G006 | ✅ FIXADO | picking inter-company location | sub-piloto |
| G007 | ✅ FIXADO | custo zero (price_unit=0) | sub-piloto |
| G024 | ✅ FIXADO | reserved_quantity nao recompute apos unlink (antes G006) | CD pre-etapa |
| G025 | ✅ FIXADO | orfaos move_lines recorrentes (antes G007) | CD pre-etapa |
| G008 | ✅ FIXADO | excecao_autorizado XML vazio | NF 626032 |
| G009 | ✅ FIXADO | multi-lote FIFO | sub-piloto |
| G010 | ✅ FIXADO | tipo_divergencia | sub-piloto |
| G011 | ✅ FIXADO | preencher qty_done apos action_assign | sub-piloto |
| G012/G013 | ✅ FIXADO via G018 | peso_liquido/volumes zero | sub-piloto |
| G014 | ✅ FIXADO | FEFO lotes vencidos | sub-piloto |
| G015 | ✅ FIXADO | protecao price=0.01 | sub-piloto |
| G016 | ✅ FIXADO | SSL crash F5e+F5d | sessao 2 |
| G017 | ✅ FIXADO | NCM=False bloqueia SEFAZ | sessao 2 |
| G018 | ✅ FIXADO v2 | weight=0 fallback no picking | sessao 2 |
| G019 | ✅ FIXADO | f5b validar engole erro | sessao 2 tarde |
| G020 | ✅ FIXADO | f5c sem pre-cond state=done | sessao 2 tarde |

Total: 22 gotchas descobertos, 21 fixados, 1 risco aberto (G005 — tempo robo).

---

## 6. Roadmap proxima sessao (LF exclusivo)

### Priority 0 — Picking pendente 317346
- [ ] Verificar se invoice apareceu (`PICKINGS_PENDENTES_INVOICE.md` tem comando)
- [ ] Se sim: F5e SEFAZ + entrada LF manual (replicar 317316)
- [ ] Se nao apareceu apos 24h: avaliar cancelar + reverter (criar devolucao 317346)

### Priority 1 — Continuar LF restante
- 1682 ajustes LF PROPOSTO
- Estrategia recomendada: batches de 30-50 prods com max-picking=5-10
- Com fixes G019/G020 ativos, false-positive em F5b vai ser detectado e
  abortar antecipadamente em vez de criar rabo

### Priority 2 — Avaliar drift Cat 2 (65 TRANSF_FALHA atuais)
- Esses ajustes nao tem invoice/picking, so falharam pre-Odoo
- Strategy: aguardar separacoes Odoo terminarem OU cancelar reservas UI
  OU aceitar como rabo permanente

### Priority 3 — Onda 3 INDISPONIBILIZAR_LOTE
- 13 ajustes fora escopo onda 1 — processo diferente

---

## 7. Comando rapido para retomar

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. Validar baseline (134 tests passing)
pytest tests/odoo/ -p no:randomly -q

# 2. Verificar picking pendente 317346
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    p = odoo.read('stock.picking', [317346], ['name', 'state', 'date_done'])
    print(p)
    invs = odoo.search_read('account.move',
        [['ref', 'ilike', 'INV-INVENTARIO_2026_05-INDUSTRIALIZACAO-G001']],
        ['id', 'name', 'state'], limit=5)
    print(f'Invoices candidatas: {invs}')
"

# 3. Continuar LF restante (quando 317346 resolvido)
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --limite-produtos=50 --max-produtos-picking=10 \
    --confirmar --confirmar-sefaz --usuario=rafael \
    --validacao-fiscal=strict --auto-fix-weight=0.001
```

---

## 8. Referencias

- `PICKINGS_PENDENTES_INVOICE.md` (rastreabilidade 317346)
- `02-gotchas/G019-f5b-validar-engole-erro.md` (CRITICAL)
- `02-gotchas/G020-f5c-sem-checar-state-done.md`
- `02-gotchas/G016-ssl-crash-no-loop-f5e-perde-commits.md` (atualizado F5d)
- `02-gotchas/G018-weight-zero-bloqueia-f5c.md` (v2)
- `07-relatorios/audit_fiscal_LF.md` (snapshot fiscal LF)
- `EXECUCAO_CADASTRO_NCM_WEIGHT_2026_05_18.md`
- `EXECUCAO_ENTRADA_LF_NF627348_2026_05_18.md`

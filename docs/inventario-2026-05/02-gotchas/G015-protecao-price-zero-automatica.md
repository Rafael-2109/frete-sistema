# G015 — Protecao automatica price_unit=0 em invoice pos-CIEL IT

**Descoberta**: 2026-05-18 sub-piloto bulk (apos G014 fix)
**Severidade**: HIGH (SEFAZ rejeita XML schema com vUnCom=0)
**Status**: corrigido em `inventario_pipeline_service.py` `_corrigir_price_zero_em_invoice`

---

## Sintoma

Invoice 626032 (RETNA/2026/00032 LF perda) criada pelo robo CIEL IT em
2026-05-18 06:03 tem 2 linhas com `price_unit=0`:
- 101001001 COGUMELO FATIADO qty=4 price=0
- 102020600 AZEITONAS PRETAS TRIT qty=1.385 price=0

Sem correcao, SEFAZ rejeita `Rejeicao: Falha no Schema XML do lote de NFe`
(G007 documentado).

## Causa raiz

Robo CIEL IT criou invoice via API mas nao populou `price_unit` para certos
produtos (talvez por config de margem ou erro intermitente). Apenas alguns
produtos sao afetados — outros 3 vieram com price_unit OK:
- 102020201 AZEITONA PRETA FAT price=9.5557 ✓
- 103000011 PEPINO - IND price=1.0260 ✓
- 103000020 ALHO EM PÓ price=47.9751 ✓

Padrao: produtos cujo `standard_price` no Odoo nao esta sincronizado com
o `custo_medio` do ajuste local podem cair em zero.

## Solucao automatica

Novo metodo `_corrigir_price_zero_em_invoice(invoice_id, aj, executado_por)`
em `InventarioPipelineService` (`inventario_pipeline_service.py`):

```python
def _corrigir_price_zero_em_invoice(self, invoice_id, aj, executado_por):
    # 1. Ler invoice_line_ids
    inv = self.odoo.read('account.move', [invoice_id], ['invoice_line_ids', 'state'])
    lines = self.odoo.read('account.move.line', inv[0]['invoice_line_ids'],
        ['id', 'product_id', 'price_unit'])
    lines_zero = [l for l in lines
                  if l.get('product_id') and (l.get('price_unit') or 0) <= 0]
    if not lines_zero:
        return 0  # idempotente

    # 2. Buscar standard_price dos produtos zerados
    prod_ids = list({l['product_id'][0] for l in lines_zero})
    prods = self.odoo.read('product.product', prod_ids, ['standard_price'])
    std_cache = {p['id']: abs(float(p.get('standard_price') or 0)) or 0.01
                 for p in prods}

    # 3. button_draft + write price_unit + action_post
    self.odoo.execute_kw('account.move', 'button_draft', [[invoice_id]])
    for l in lines_zero:
        pid = l['product_id'][0]
        novo_preco = std_cache.get(pid, 0.01)
        self.odoo.write('account.move.line', [l['id']], {'price_unit': novo_preco})
    self.odoo.execute_kw('account.move', 'action_post', [[invoice_id]])
    return len(lines_zero)
```

Chamado em `f5d_aguardar_invoices` apos detectar invoice criada
(linha 754-764):

```python
# F5d.5: payment_provider_id (existente)
try:
    self._garantir_payment_provider(invoice_id, ajustes_grupo[0], executado_por)
except Exception as e:
    logger.warning(...)
# F5d.6 (NOVO G015): corrigir price_unit=0
try:
    self._corrigir_price_zero_em_invoice(invoice_id, ajustes_grupo[0], executado_por)
except Exception as e:
    logger.warning(...)
```

## Comportamento

- Idempotente: se nao ha price_unit=0, no-op
- Audit: registra operacao em `OperacaoOdooAuditoria` com `fase='F5d.6'`
  e `acao='corrigir_price_zero'`
- Robusto: try/except em volta — se falhar, log warning mas continua

## Validacao

Manual em invoice 626032 (2026-05-18 06:07):
- 2 linhas corrigidas: 101001001 (price 0 -> 12.232), 102020600 (price 0 -> 14.154)
- Re-post OK
- amount_total: R$ 0.00 (CFOP 5901 perda — fiscalmente OK)
- Subtotais: 48.93 + 76.45 + 19.60 + 205.21 + 14.15 = R$ 364.34

## Ref

- G007 (manual: como corrigir price_unit=0 antes de SEFAZ)
- L13 (fix etapa_b: validar custo_medio antes de criar pickings)
- D006 secao L22 (a ser adicionada)

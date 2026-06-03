<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G007 — custo_medio=0 gera price_unit=0 e SEFAZ rejeita schema XML

> **Papel:** G007 — custo_medio=0 gera price_unit=0 e SEFAZ rejeita schema XML.

## Indice

- [Sintoma](#sintoma)
- [Causa raiz](#causa-raiz)
- [Solucao](#solucao)
- [Recuperacao manual (se ainda assim invoice sair com price=0)](#recuperacao-manual-se-ainda-assim-invoice-sair-com-price0)
- [Observacao critica para LF completa](#observacao-critica-para-lf-completa)
- [Ref](#ref)
- [Contexto](#contexto)

**Descoberta**: 2026-05-18 sub-piloto bulk 10 produtos (NF 13150)
**Severidade**: HIGH (NF rejeitada pelo SEFAZ — irreversivel sem cancelar e recriar)
**Status**: corrigido em `09_executar_onda1_bulk.py:400-432`

---

## Sintoma

```
[playwright] NF-e RETNA/2026/00030 nao autorizada
    (tentativa 1/15, situacao=excecao_autorizado,
     cstat=False, xmotivo=Rejeicao: Falha no Schema XML do lote de NFe)
```

Playwright re-transmitiu 15x sem sucesso. Inspecao da invoice mostrou:
- Linha 1: produto 101001001 qty=18 **price_unit=0** subtotal=0
- Linha 3: produto 102020600 qty=1.385 **price_unit=0** subtotal=0

## Causa raiz

NFe schema (`vUnCom`) nao aceita valor 0 nas linhas de produto.
Quando custo_medio do ajuste e' 0, o robo CIEL IT gera invoice line com
price_unit=0 → vUnCom=0 → schema XML invalido → SEFAZ rejeita.

**Por que custo_medio=0?**
- Produto 101001001 (COGUMELO FATIADO IND): `product.standard_price=12.23`
  mas `custo_medio` no ajuste estava 0 (script 03 nao buscou no Odoo)
- Produto 102020600 (AZEITONAS P TRIT): `product.standard_price=-14.15`
  (NEGATIVO — erro de cadastro Odoo CIEL IT)

## Solucao

`etapa_b_pickings` ANTES de criar pickings:
1. Resolve `product_id` + `standard_price` para cada produto
2. Se `custo_medio <= 0`, atualiza no DB:
   - `custo_medio = abs(standard_price)` (negativos → positivos, presume erro cadastro)
   - Se `standard_price = 0`, usa fallback `0.01`

```python
custo_cache: Dict[str, float] = {}
for c in cods_total:
    prods = odoo.search_read('product.product',
        [['default_code', '=', c]], ['id', 'standard_price'], limit=1)
    if prods:
        std = float(prods[0].get('standard_price') or 0)
        custo_cache[c] = abs(std) if std else 0.01

# Validar custo_medio dos ajustes
for aj in picking_ajustes:
    cm = float(aj.custo_medio or 0)
    if cm <= 0:
        novo_cm = custo_cache.get(aj.cod_produto, 0.01)
        aj.custo_medio = novo_cm
db.session.commit()
```

## Recuperacao manual (se ainda assim invoice sair com price=0)

```python
# 1. Reset to draft
odoo.execute_kw('account.move', 'button_draft', [[inv_id]])

# 2. Atualizar price_unit de cada linha
for ml in lines_zero:
    novo_preco = abs(product_standard_price) or 0.01
    odoo.write('account.move.line', [ml['id']], {'price_unit': novo_preco})

# 3. Re-post
odoo.execute_kw('account.move', 'action_post', [[inv_id]])

# 4. Re-transmitir SEFAZ
# (mas se ja consumiu numero_nf, vai virar excecao_autorizado — ver G008)
```

## Observacao critica para LF completa

Pode haver dezenas de produtos com `standard_price = 0` ou negativo no
Odoo CIEL IT. Antes de rodar o bulk LF inteiro:

```sql
-- Listar todos produtos da onda 1 com custo zero
SELECT a.cod_produto, a.custo_medio, COUNT(*)
FROM ajuste_estoque_inventario a
WHERE a.ciclo='INVENTARIO_2026_05' AND a.company_id=5
  AND a.acao_decidida IN ('PERDA_LF_FB', 'INDUSTRIALIZACAO_FB_LF',
                          'DEV_FB_LF', 'DEV_LF_FB')
  AND (a.custo_medio IS NULL OR a.custo_medio <= 0)
GROUP BY a.cod_produto, a.custo_medio;
```

O fix no `etapa_b_pickings` ja corrige automaticamente — mas vale a
pena auditar antes de rodar.

## Ref

- G004 (padrao real e' picking + robo CIEL IT)
- G008 (excecao_autorizado SEFAZ — XML autorizado vazio)
- D006 secao L13

## Contexto

Gotcha — ciclo de inventario NACOM/LF/CD/FB 2026-05. Tema: custo_medio=0 gera price_unit=0 e SEFAZ rejeita schema XML

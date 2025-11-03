# 🧪 Resultado do Teste de Importação Odoo - Compras e Estoque

**Data de Execução**: 2025-10-31T11:15:33.710371
**Odoo URL**: https://odoo.nacomgoya.com.br
**Database**: odoo-17-ee-nacomgoya-prd

---

## 📋 FASE 1: purchase.request (Requisições de Compras)

**Status**: SUCESSO

### Campos Propostos no Sistema:
```
- num_requisicao (name)
- data_requisicao_criacao (create_date)
- data_inicio (date_start)
- usuario_requisicao (requested_by)
- responsavel (assigned_to)
- descricao (description)
- origem (origin)
- cod_produto (line_ids/product_id/default_code)
- nome_produto (line_ids/product_id/name)
- qtd_produto_requisicao (line_ids/product_qty)
- data_necessidade (line_ids/date_required)
- custo_estimado (line_ids/estimated_cost)
- status (state)
- odoo_id (id)
```

### Dados Extraídos do Odoo:

```json
{
  "id": 8004,
  "name": "REQ/FB/06614",
  "state": "approved",
  "date_start": "2025-10-30",
  "create_date": "2025-10-30 13:39:06",
  "requested_by": [
    21,
    "Polyanna Alves de Souza"
  ],
  "assigned_to": false,
  "description": false,
  "line_ids": [
    20437
  ],
  "origin": false,
  "company_id": [
    1,
    "NACOM GOYA - FB"
  ],
  "linhas_detalhadas": [
    {
      "id": 20437,
      "request_id": [
        8004,
        "REQ/FB/06614"
      ],
      "product_id": [
        36788,
        "[210639522] ROTULO SWEET PICKLES 1,01KG - RETANGULAR - BY GEMEOS"
      ],
      "name": "[210639522] ROTULO SWEET PICKLES BD 1,01KG - RETANGULAR - BY GEMEOS",
      "product_qty": 6000.0,
      "product_uom_id": [
        1,
        "Units"
      ],
      "date_required": "2025-11-13",
      "estimated_cost": 0.0,
      "description": false
    }
  ]
}
```

### ✅ Análise:

- [ ] Verificar se campos existem conforme esperado
- [ ] Validar mapeamento de campos relacionais (user_id, product_id)
- [ ] Confirmar formato de datas
- [ ] Analisar estrutura de line_ids

---

## 📦 FASE 2: purchase.order + purchase.order.line (Pedidos de Compras)

**Status**: SUCESSO

### Campos Propostos no Sistema:
```
- num_pedido (name)
- cnpj_fornecedor (partner_id/l10n_br_cnpj)
- raz_social (partner_id/name)
- numero_nf (invoice_ids/name)
- data_pedido_criacao (date_order)
- data_pedido_entrega (date_approve)
- data_pedido_previsao (date_planned)
- cod_produto (order_line/product_id/default_code)
- nome_produto (order_line/product_id/name)
- qtd_produto_pedido (order_line/product_qty)
- preco_produto_pedido (order_line/price_unit)
- confirmacao_pedido (state=purchase)
- odoo_id (id)
```

### Dados Extraídos do Odoo:

```json
{
  "id": 29977,
  "name": "C2514883",
  "state": "purchase",
  "date_order": "2025-10-31 12:00:00",
  "date_approve": "2025-10-31 14:13:43",
  "date_planned": "2025-10-31 12:00:00",
  "partner_id": [
    208180,
    "CIA CARGAS TRANSPORTES E LOGISTICA LTDA"
  ],
  "user_id": [
    695,
    "Talita de Lê Lima"
  ],
  "origin": false,
  "amount_total": 26846.0,
  "currency_id": [
    6,
    "BRL"
  ],
  "order_line": [
    85727
  ],
  "picking_ids": [],
  "invoice_ids": [
    393908
  ],
  "linhas_detalhadas": [
    {
      "id": 85727,
      "order_id": [
        29977,
        "C2514883"
      ],
      "product_id": [
        29993,
        "[800000025] SERVIÇO DE FRETE"
      ],
      "name": "[800000025] SERVICO DE FRETE",
      "product_qty": 1.0,
      "qty_received": 0.0,
      "qty_invoiced": 1.0,
      "price_unit": 26846.00000000001,
      "price_subtotal": 22657.35,
      "price_tax": 4188.65,
      "taxes_id": [
        2232934,
        2232935,
        2232936
      ],
      "product_uom": [
        1,
        "Units"
      ],
      "date_planned": "2025-10-31 12:00:00"
    }
  ]
}
```

### ✅ Análise:

- [ ] Verificar se partner_id contém l10n_br_cnpj
- [ ] Validar campos de quantidade (product_qty, qty_received)
- [ ] Confirmar campos de preço e impostos
- [ ] Analisar estrutura de order_line

---

## 🚚 FASE 3: stock.picking + stock.move (Recebimentos)

**Status**: SUCESSO

### Campos Propostos no Sistema:
```
- numero_recebimento (name)
- data_programada (scheduled_date)
- data_efetiva (date_done)
- origem_documento (origin)
- fornecedor (partner_id/name)
- pedido_compra_vinculado (purchase_id)
- cod_produto (move_ids/product_id/default_code)
- nome_produto (move_ids/product_id/name)
- qtd_recebida (move_ids/quantity)
- data_movimento (move_ids/date)
```

### Dados Extraídos do Odoo:

```json
{
  "id": 181958,
  "name": "FB/IN/00109",
  "state": "done",
  "scheduled_date": "2024-07-03 03:00:00",
  "date_done": "2024-08-13 14:28:14",
  "origin": "C2400084",
  "partner_id": [
    97884,
    "REAL SAFRA COMERCIO E DISTRIBUIDORA DE PRODUTOS ALIMENTICIOS LTDA"
  ],
  "purchase_id": [
    1412,
    "C2400084"
  ],
  "location_dest_id": [
    8,
    "FB/Estoque"
  ],
  "move_ids_without_package": [
    250915
  ],
  "picking_type_id": [
    1,
    "FB: Recebimento (FB)"
  ],
  "movimentos_detalhados": [
    {
      "id": 250915,
      "picking_id": [
        181958,
        "FB/IN/00109"
      ],
      "product_id": [
        30624,
        "[109000055] OLEO DE SOJA"
      ],
      "name": "[109000055] OLEO DE SOJA",
      "product_uom_qty": 38130.0,
      "quantity": 38130.0,
      "product_uom": [
        12,
        "kg"
      ],
      "date": "2024-08-13 14:28:13",
      "state": "done",
      "origin": "C2400084",
      "purchase_line_id": [
        2689,
        "[109000055] OLEO DE SOJA\nOLEO DE SOJA (C2400084)"
      ],
      "location_id": [
        4,
        "Parceiros/Fornecedores"
      ],
      "location_dest_id": [
        8,
        "FB/Estoque"
      ]
    }
  ]
}
```

### ✅ Análise:

- [ ] Verificar se picking_type_id.code='incoming' funciona como filtro
- [ ] Validar campos de quantidade (product_uom_qty vs quantity)
- [ ] Confirmar vínculo com purchase_id
- [ ] Analisar estrutura de move_ids_without_package

---

## 🎯 PRÓXIMOS PASSOS

1. **Revisar JSON completo** em `TESTE_IMPORTACAO_RESULTADO.json`
2. **Validar campos faltantes** ou diferentes do esperado
3. **Ajustar mapeamentos** em `manufatura_mapper.py` se necessário
4. **Confirmar filtros** de importação (states, dates, etc.)
5. **Testar campos relacionais** (partner_id/l10n_br_cnpj, product_id/default_code)
6. **Implementar importação real** após validação

---

**Autor**: Sistema de Fretes  
**Script**: `scripts/teste_importacao_odoo_compras.py`

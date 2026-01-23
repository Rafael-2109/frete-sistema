# Fluxo Completo de Conciliacao PO x DFe

## Visao Geral

A consolidacao e o processo de criar um **PO Conciliador** que casa 100% com a NF-e (DFe),
enquanto os POs originais permanecem com o saldo restante.

## Diagrama do Fluxo

```
┌─────────────────────────────────────────────────────────────────────┐
│ PRE-REQUISITO: ValidacaoNfPoDfe com status='aprovado'               │
│ MatchNfPoItem com status_match='match' para cada item               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASSO 1: Buscar fornecedor no Odoo pelo CNPJ                        │
│                                                                      │
│   cnpj_limpo = ''.join(c for c in str(cnpj) if c.isdigit())        │
│   cnpj_formatado = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/..."      │
│                                                                      │
│   partner_ids = odoo.search(                                         │
│       'res.partner',                                                 │
│       [('l10n_br_cnpj', '=', cnpj_formatado)],                      │
│       limit=1                                                        │
│   )                                                                  │
│   fornecedor_id = partner_ids[0]                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASSO 2: Criar PO Conciliador VAZIO via copy()                       │
│                                                                      │
│   po_referencia_id = pos_para_consolidar[0]['po_id']  # 1o da lista │
│                                                                      │
│   novo_po_id = odoo.execute_kw(                                      │
│       'purchase.order', 'copy', [po_referencia_id],                  │
│       {'default': {                                                  │
│           'partner_id': fornecedor_id,                               │
│           'date_order': validacao.data_nf.isoformat(),               │
│           'origin': f'Conciliacao NF {validacao.numero_nf}',         │
│           'state': 'draft',                                          │
│           'order_line': False,  # Limpar linhas                      │
│       }}                                                             │
│   )                                                                  │
│                                                                      │
│   # FALLBACK: Remover linhas se copy() as criou mesmo assim         │
│   linhas = odoo.search('purchase.order.line',                        │
│                         [[('order_id', '=', novo_po_id)]])           │
│   if linhas:                                                         │
│       odoo.execute_kw('purchase.order.line', 'unlink', [linhas])     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASSO 3: Para CADA item da NF com match                              │
│                                                                      │
│   for match in MatchNfPoItem.filter(status_match='match'):           │
│                                                                      │
│       # 3.1: Buscar alocacoes (suporte multi-PO)                     │
│       alocacoes = MatchAlocacao.filter(match_item_id=match.id)       │
│                                                                      │
│       for aloc in alocacoes:                                         │
│           # 3.2a: CRIAR LINHA no PO Conciliador                      │
│           nova_linha_id = odoo.execute_kw(                            │
│               'purchase.order.line', 'copy',                          │
│               [aloc.odoo_po_line_id],   # <-- Linha ORIGINAL do PO   │
│               {'default': {                                          │
│                   'order_id': po_conciliador_id,                      │
│                   'product_id': product_id,                           │
│                   'product_qty': float(qtd_alocada),  # QTD DA NF    │
│                   'price_unit': preco_nf,             # PRECO DA NF  │
│               }}                                                     │
│           )                                                          │
│                                                                      │
│           # 3.2b: REDUZIR SALDO no PO Original                       │
│           saldo = qtd_po_original - qtd_recebida - qtd_alocada       │
│           odoo.write('purchase.order.line', aloc.odoo_po_line_id,    │
│                      {'product_qty': max(saldo, 0)})                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASSO 4: Confirmar PO Conciliador                                    │
│                                                                      │
│   odoo.execute_kw('purchase.order', 'button_confirm',                │
│                   [po_conciliador_id])                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASSO 5: Vincular DFe ao PO Conciliador                              │
│                                                                      │
│   odoo.write('purchase.order', po_conciliador_id,                    │
│              {'dfe_id': validacao.odoo_dfe_id})                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASSO 6: Atualizar validacao local                                   │
│                                                                      │
│   validacao.status = 'consolidado'                                   │
│   validacao.po_consolidado_id = po_conciliador_id                    │
│   validacao.po_consolidado_name = po_conciliador_name                │
│   validacao.pos_saldo_ids = json.dumps([...])                        │
│   validacao.acao_executada = { ... detalhes completos ... }           │
│   validacao.consolidado_em = datetime.utcnow()                       │
│   db.session.commit()                                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Calculo do Saldo no PO Original

```python
# FORMULA:
# saldo = qtd_po_original - qtd_ja_recebida - qtd_agora_alocada

# Campos lidos da linha original:
linha_original = odoo.read('purchase.order.line', [line_id],
                           ['product_id', 'product_qty', 'qty_received'])

qtd_po_original = Decimal(str(linha_original[0]['product_qty']))
qtd_recebida = Decimal(str(linha_original[0]['qty_received']))

# Cache de consumo (se mesma linha usada por multiplos itens NF):
consumo_anterior = linhas_processadas.get(line_id, Decimal('0'))
consumo_total = consumo_anterior + qtd_alocada
linhas_processadas[line_id] = consumo_total

# Novo saldo:
saldo = qtd_po_original - qtd_recebida - consumo_total
nova_qtd = float(saldo) if saldo > 0 else 0
```

## Ponto Critico: Multi-PO com copy()

Quando a NF cobre 3 POs diferentes:

```
PO-1: Produto A (linha_id=101)  ← PO de REFERENCIA (cabecalho)
PO-2: Produto B (linha_id=202)
PO-3: Produto C (linha_id=303)

PASSO 2: copy(PO-1) → PO Conciliador
  └─ Herda: empresa, condicao pgto, fiscal_position, picking_type
  └─ Sobrescreve: partner_id, date_order, origin, state
  └─ Linhas: LIMPAS (order_line=False ou unlink)

PASSO 3: Para cada alocacao:
  Iteracao 1: copy(linha 101 do PO-1) → Linha A no Conciliador
  Iteracao 2: copy(linha 202 do PO-2) → Linha B no Conciliador
  Iteracao 3: copy(linha 303 do PO-3) → Linha C no Conciliador

RESULTADO:
  Cabecalho: configuracoes do PO-1
  Linha A: CFOP/impostos do PO-1
  Linha B: CFOP/impostos do PO-2
  Linha C: CFOP/impostos do PO-3
```

**IMPORTANTE**: Cada linha e copiada da SUA linha de origem (nao do PO de referencia).
O `aloc.odoo_po_line_id` aponta para a linha correta de cada PO.

## Como o PO de Referencia e Escolhido

```python
# Linha 416 do odoo_po_service.py:
po_referencia_id = pos_para_consolidar[0]['po_id']
# → Simplesmente pega o PRIMEIRO PO da lista
```

Isso e aceitavel porque:
1. Todos os POs sao do **mesmo fornecedor** (mesmo CNPJ)
2. Empresa, fiscal_position e picking_type normalmente sao iguais
3. O que importa por linha (CFOP, impostos) vem de cada linha individual

## Fluxo de Reversao

```python
def reverter_consolidacao(validacao_id):
    # 1. Cancelar POs saldo criados
    # 2. Restaurar quantidades originais nas linhas
    #    → odoo.write(line_id, {'product_qty': qtd_original})
    # 3. Descancelar POs cancelados (state → 'purchase')
    # 4. Remover vinculo DFe → PO (dfe_id: False)
    # 5. Cancelar PO Conciliador
    # 6. Atualizar status local → 'aprovado'
```

## Dados Salvos na Validacao (acao_executada)

```python
validacao.acao_executada = {
    'tipo': 'split_consolidacao',
    'usuario': 'rafael',
    'data': '2026-01-22T15:30:00',
    'po_conciliador': {
        'id': 12345,
        'name': 'PO12345',
        'linhas': [
            {
                'linha_id': 67890,
                'produto': 'PROD001',
                'nome': 'Palmito Acai 300g',
                'qtd': 400.0,
                'preco': 12.50,
                'po_origem': 'PO00100',
                'alocacao_id': 5
            }
        ]
    },
    'pos_originais_ajustados': [
        {
            'po_id': 100,
            'po_name': 'PO00100',
            'linha_id': 101,
            'produto': 'PROD001',
            'qtd_consumida': 400.0,
            'qtd_saldo': 100.0
        }
    ],
    'pos_com_saldo': [
        {'po_id': 100, 'po_name': 'PO00100'}
    ]
}
```

## Endpoints (Rotas)

| Rota | Metodo | Descricao |
|------|--------|-----------|
| `/recebimento/validacao-nf-po/consolidar-pos/<id>` | POST | Executar consolidacao |
| `/recebimento/validacao-nf-po/reverter-consolidacao/<id>` | POST | Reverter consolidacao |
| `/recebimento/validacao-nf-po/preview-consolidacao/<id>` | GET | Tela de preview |

## Template de Preview

`app/templates/recebimento/preview_consolidacao.html` (320 linhas)
- Mostra PO Conciliador que sera criado
- Mostra POs originais e seus ajustes
- Timeline de acoes
- Botao para executar

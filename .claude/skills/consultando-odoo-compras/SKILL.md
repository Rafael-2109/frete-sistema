---
name: consultando-odoo-compras
description: "Consulta pedidos de compra no Odoo (purchase.order, purchase.order.line). Use para: pedidos de compra pendentes, PO por fornecedor, historico de compras, status de recebimento, pedidos aguardando faturamento, PO vinculado a NF de entrada, compras do periodo."
---

# Consultando Odoo - Compras (Purchase Orders)

Skill para consultas de **pedidos de compra** no Odoo ERP.

> **ESCOPO:** Esta skill cobre purchase.order (pedidos de compra) e purchase.order.line (itens).
> Para cadastros (parceiros/transportadoras), use `consultando-odoo-cadastros`.
> Para documentos fiscais (DFE/CTe), use `consultando-odoo-dfe`.
> Para contas a pagar/receber, use `consultando-odoo-financeiro`.

## Script Principal

### consulta.py

```bash
source /home/rafaelnascimento/projetos/frete_sistema/venv/bin/activate && \
python /home/rafaelnascimento/projetos/frete_sistema/.claude/skills/consultando-odoo-compras/scripts/consulta.py [opcoes]
```

## Tipos de Consulta

```
COMPRAS
│
├── Pendentes (--subtipo pendentes)
│   Filtro: state in ['draft', 'sent', 'to approve']
│   Usar: POs aguardando aprovacao ou confirmacao
│
├── Confirmados (--subtipo confirmados)
│   Filtro: state = 'purchase'
│   Usar: POs confirmados, aguardando recebimento
│
├── Recebidos (--subtipo recebidos)
│   Filtro: state = 'done'
│   Usar: POs totalmente recebidos
│
├── A Faturar (--subtipo a-faturar)
│   Filtro: invoice_status = 'to invoice'
│   Usar: POs pendentes de faturamento
│
└── Todos (--subtipo todos)
    Usar: Busca geral de pedidos de compra
```

## Parametros

### Filtros Basicos

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--tipo` | Tipo de consulta (obrigatorio) | `--tipo compras` |
| `--subtipo` | pendentes, confirmados, recebidos, a-faturar, todos | `--subtipo pendentes` |
| `--fornecedor` | Nome do fornecedor | `--fornecedor "vale sul"` |
| `--cnpj` | CNPJ do fornecedor | `--cnpj "32451351"` |
| `--numero-po` | Numero do PO | `--numero-po "PO00123"` |
| `--data-inicio` | Data inicial do pedido | `--data-inicio 2025-01-01` |
| `--data-fim` | Data final do pedido | `--data-fim 2025-12-31` |
| `--limit` | Limite de resultados | `--limit 50` |

### Filtros Avancados

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--valor-min` | Valor minimo do PO | `--valor-min 1000` |
| `--valor-max` | Valor maximo do PO | `--valor-max 50000` |
| `--produto` | Nome do produto (busca nas linhas) | `--produto "pimenta"` |
| `--origem` | Documento de origem | `--origem "SO0001"` |

### Opcoes de Saida

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--detalhes` | Incluir linhas/produtos | flag |
| `--fiscais` | Incluir campos tributarios | flag |
| `--resumo` | Mostrar apenas totalizadores | flag |
| `--json` | Saida em formato JSON | flag |

## Exemplos de Uso

### Pedidos pendentes de aprovacao
```bash
python .../consulta.py --tipo compras --subtipo pendentes
```

### Pedidos de um fornecedor
```bash
python .../consulta.py --tipo compras --fornecedor "vale sul"
```

### Pedidos confirmados aguardando recebimento
```bash
python .../consulta.py --tipo compras --subtipo confirmados
```

### Pedidos pendentes de faturamento
```bash
python .../consulta.py --tipo compras --subtipo a-faturar
```

### Buscar por periodo
```bash
python .../consulta.py --tipo compras --data-inicio 2025-11-01 --data-fim 2025-11-30
```

### Buscar PO especifico com detalhes
```bash
python .../consulta.py --tipo compras --numero-po "PO00123" --detalhes
```

### Buscar por produto
```bash
python .../consulta.py --tipo compras --produto "pupunha" --detalhes
```

### Resumo de compras do periodo
```bash
python .../consulta.py --tipo compras --data-inicio 2025-11-01 --data-fim 2025-11-30 --resumo
```

## Campos Retornados

### Campos Padrao (purchase.order)
- ID, Numero PO, Referencia
- Fornecedor (nome, CNPJ)
- Data pedido, Data prevista entrega
- Valor total, Valor impostos
- Status, Status faturamento, Status recebimento

### Com `--detalhes` (purchase.order.line)
- Produto, Quantidade
- Preco unitario, Subtotal
- CFOP, NCM
- Quantidade recebida, faturada

### Com `--fiscais`
- Totais: ICMS, PIS, COFINS, IPI
- Frete, Seguro, Desconto
- Total NF-e

### Com `--resumo`
- Total de POs
- Valor total
- Valor recebido
- Valor a receber

## Valores de state

| Valor | Descricao |
|-------|-----------|
| `draft` | Rascunho/Cotacao |
| `sent` | Cotacao Enviada |
| `to approve` | Aguardando Aprovacao |
| `purchase` | Pedido Confirmado |
| `done` | Concluido |
| `cancel` | Cancelado |

## Valores de invoice_status

| Valor | Descricao |
|-------|-----------|
| `no` | Nada a Faturar |
| `to invoice` | Aguardando Faturamento |
| `invoiced` | Totalmente Faturado |

## Valores de receipt_status

| Valor | Descricao |
|-------|-----------|
| `pending` | Aguardando |
| `partial` | Parcialmente Recebido |
| `full` | Totalmente Recebido |

## Nao Encontrou o Campo?

Se precisar de um campo que nao esta mapeado, use a skill **descobrindo-odoo-estrutura**:

```bash
source /home/rafaelnascimento/projetos/frete_sistema/venv/bin/activate && \
python /home/rafaelnascimento/projetos/frete_sistema/.claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo purchase.order \
  --buscar-campo "nome_do_campo"
```

## Referencias

- [PURCHASE.md](reference/PURCHASE.md) - Campos dos modelos purchase.order e purchase.order.line

## Relacionado

| Skill | Uso |
|-------|-----|
| consultando-odoo-cadastros | Consultas de parceiros (clientes, fornecedores, transportadoras) |
| consultando-odoo-dfe | Consultas DFE (documentos fiscais, tributos) |
| consultando-odoo-financeiro | Consultas de contas a pagar/receber, vencimentos |
| consultando-odoo-produtos | Consultas de catalogo de produtos (product.product) |
| descobrindo-odoo-estrutura | Descobrir campos/modelos nao mapeados |
| integracao-odoo | Criar novas integracoes (desenvolvimento) |
| agente-logistico | Consultas de carteira, separacoes e estoque |

> **NOTA**: Esta skill eh para CONSULTAS de pedidos de compra em producao.
> Para consultar cadastros, use `consultando-odoo-cadastros`.
> Para consultar DFE/CTe, use `consultando-odoo-dfe`.
> Para consultar contas a pagar/receber, use `consultando-odoo-financeiro`.

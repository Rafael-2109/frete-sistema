---
name: consultando-odoo-financeiro
description: "Consulta contas a pagar e receber no Odoo (account.move, account.move.line). Use para: parcelas vencidas, contas a pagar de fornecedor, vencimentos da semana, saldo devedor por parceiro, relatorio de inadimplencia, faturas pendentes, titulos em aberto."
---

# Consultando Odoo - Financeiro (Contas a Pagar/Receber)

Skill para consultas **financeiras** no Odoo ERP.

> **ESCOPO:** Esta skill cobre account.move (faturas/contas) e account.move.line (parcelas/vencimentos).
> Para cadastros (parceiros/transportadoras), use `consultando-odoo-cadastros`.
> Para documentos fiscais (DFE/CTe), use `consultando-odoo-dfe`.

## Script Principal

### consulta.py

```bash
source /home/rafaelnascimento/projetos/frete_sistema/venv/bin/activate && \
python /home/rafaelnascimento/projetos/frete_sistema/.claude/skills/consultando-odoo-financeiro/scripts/consulta.py [opcoes]
```

## Tipos de Consulta

```
FINANCEIRO
│
├── Contas a Pagar (--subtipo a-pagar)
│   Modelo: account.move (move_type=in_invoice/in_refund)
│   Usar: Faturas de fornecedores pendentes
│
├── Contas a Receber (--subtipo a-receber)
│   Modelo: account.move (move_type=out_invoice/out_refund)
│   Usar: Faturas de clientes pendentes
│
├── Vencidos (--subtipo vencidos)
│   Modelo: account.move.line (date_maturity < hoje)
│   Usar: Parcelas em atraso
│
├── A Vencer (--subtipo a-vencer)
│   Modelo: account.move.line (date_maturity >= hoje)
│   Usar: Parcelas futuras
│
└── Todos (--subtipo todos)
    Usar: Busca geral de movimentos financeiros
```

## Parametros

### Filtros Basicos

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--tipo` | Tipo de consulta (obrigatorio) | `--tipo financeiro` |
| `--subtipo` | a-pagar, a-receber, vencidos, a-vencer, todos | `--subtipo a-pagar` |
| `--parceiro` | Nome ou CNPJ do parceiro | `--parceiro "atacadao"` |
| `--cnpj` | CNPJ do parceiro | `--cnpj "18467441"` |
| `--vencimento-ate` | Data limite vencimento | `--vencimento-ate 2025-12-31` |
| `--vencimento-de` | Data inicial vencimento | `--vencimento-de 2025-01-01` |
| `--limit` | Limite de resultados | `--limit 50` |

### Filtros Avancados

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--valor-min` | Valor minimo do documento | `--valor-min 1000` |
| `--valor-max` | Valor maximo do documento | `--valor-max 50000` |
| `--estado` | Status do documento | `--estado posted` |
| `--pagamento` | Status de pagamento | `--pagamento not_paid` |
| `--dias-atraso` | Minimo de dias em atraso | `--dias-atraso 30` |

### Opcoes de Saida

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--detalhes` | Incluir parcelas/linhas | flag |
| `--resumo` | Mostrar apenas totalizadores | flag |
| `--json` | Saida em formato JSON | flag |

## Exemplos de Uso

### Contas a pagar pendentes
```bash
python .../consulta.py --tipo financeiro --subtipo a-pagar
```

### Contas a pagar de um fornecedor
```bash
python .../consulta.py --tipo financeiro --subtipo a-pagar --parceiro "atacadao"
```

### Contas a receber vencidas
```bash
python .../consulta.py --tipo financeiro --subtipo vencidos
```

### Parcelas vencendo esta semana
```bash
python .../consulta.py --tipo financeiro --subtipo a-vencer --vencimento-ate 2025-12-07
```

### Titulos com mais de 30 dias de atraso
```bash
python .../consulta.py --tipo financeiro --subtipo vencidos --dias-atraso 30
```

### Buscar por CNPJ com detalhes
```bash
python .../consulta.py --tipo financeiro --cnpj "18467441" --detalhes
```

### Resumo de inadimplencia
```bash
python .../consulta.py --tipo financeiro --subtipo vencidos --resumo
```

## Campos Retornados

### Campos Padrao (account.move)
- ID, Nome/Numero
- Parceiro (nome, CNPJ)
- Tipo (a pagar, a receber)
- Data emissao, Data vencimento
- Valor total, Valor residual
- Status, Status pagamento

### Com `--detalhes` (account.move.line)
- Numero da parcela
- Data vencimento
- Valor, Valor residual
- Situacao cobranca
- Nosso numero (boleto)

### Com `--resumo`
- Total de documentos
- Valor total
- Valor pago
- Valor em aberto
- Valor vencido

## Valores de move_type

| Valor | Descricao |
|-------|-----------|
| `out_invoice` | Fatura de cliente (a receber) |
| `out_refund` | Nota credito cliente |
| `in_invoice` | Fatura de fornecedor (a pagar) |
| `in_refund` | Nota credito fornecedor |
| `entry` | Lancamento contabil |

## Valores de state

| Valor | Descricao |
|-------|-----------|
| `draft` | Rascunho |
| `posted` | Lancado |
| `cancel` | Cancelado |

## Valores de payment_state

| Valor | Descricao |
|-------|-----------|
| `not_paid` | Nao pago |
| `partial` | Parcialmente pago |
| `paid` | Pago |
| `in_payment` | Em pagamento |
| `reversed` | Revertido |

## Nao Encontrou o Campo?

Se precisar de um campo que nao esta mapeado, use a skill **descobrindo-odoo-estrutura**:

```bash
source /home/rafaelnascimento/projetos/frete_sistema/venv/bin/activate && \
python /home/rafaelnascimento/projetos/frete_sistema/.claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo account.move \
  --buscar-campo "nome_do_campo"
```

## Referencias

- [FINANCEIRO.md](reference/FINANCEIRO.md) - Campos dos modelos account.move e account.move.line

## Relacionado

| Skill | Uso |
|-------|-----|
| consultando-odoo-cadastros | Consultas de parceiros (clientes, fornecedores, transportadoras) |
| consultando-odoo-dfe | Consultas DFE (documentos fiscais, tributos) |
| consultando-odoo-compras | Consultas de pedidos de compra (purchase.order) |
| consultando-odoo-produtos | Consultas de catalogo de produtos (product.product) |
| descobrindo-odoo-estrutura | Descobrir campos/modelos nao mapeados |
| integracao-odoo | Criar novas integracoes (desenvolvimento) |
| agente-logistico | Consultas de carteira, separacoes e estoque |

> **NOTA**: Esta skill eh para CONSULTAS financeiras em producao.
> Para consultar cadastros, use `consultando-odoo-cadastros`.
> Para consultar DFE/CTe, use `consultando-odoo-dfe`.

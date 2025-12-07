---
name: consultando-odoo-produtos
description: "Consulta produtos no Odoo (product.product, product.template). Use para: catalogo de produtos, buscar por codigo/barcode, NCM de produto, preco de custo/venda, estoque disponivel, fornecedores do produto, categoria de produto, produtos para compra, produtos para venda."
---

# Consultando Odoo - Produtos (Catalogo)

Skill para consultas de **produtos** no Odoo ERP.

> **ESCOPO:** Esta skill cobre product.product (produtos) e product.template (templates de produto).
> Para cadastros (parceiros/transportadoras), use `consultando-odoo-cadastros`.
> Para documentos fiscais (DFE/CTe), use `consultando-odoo-dfe`.
> Para pedidos de compra, use `consultando-odoo-compras`.

## Script Principal

### consulta.py

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/consultando-odoo-produtos/scripts/consulta.py [opcoes]
```

## Tipos de Consulta

```
PRODUTOS
│
├── Ativos (--subtipo ativos)
│   Filtro: active = True
│   Usar: Produtos ativos no sistema
│
├── Inativos (--subtipo inativos)
│   Filtro: active = False
│   Usar: Produtos descontinuados
│
├── Vendaveis (--subtipo vendaveis)
│   Filtro: sale_ok = True
│   Usar: Produtos disponiveis para venda
│
├── Compraveis (--subtipo compraveis)
│   Filtro: purchase_ok = True
│   Usar: Produtos disponiveis para compra
│
├── Estocaveis (--subtipo estocaveis)
│   Filtro: detailed_type = 'product'
│   Usar: Produtos que controlam estoque
│
├── Servicos (--subtipo servicos)
│   Filtro: detailed_type = 'service'
│   Usar: Servicos
│
├── Consumiveis (--subtipo consumiveis)
│   Filtro: detailed_type = 'consu'
│   Usar: Produtos consumiveis (sem estoque)
│
└── Todos (--subtipo todos)
    Usar: Busca geral de produtos
```

## Parametros

### Filtros Basicos

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--tipo` | Tipo de consulta (obrigatorio) | `--tipo produtos` |
| `--subtipo` | ativos, inativos, vendaveis, compraveis, estocaveis, servicos, consumiveis, todos | `--subtipo vendaveis` |
| `--codigo` | Codigo interno (default_code) | `--codigo "PROD001"` |
| `--nome` | Nome do produto | `--nome "pupunha"` |
| `--barcode` | Codigo de barras | `--barcode "7891234567890"` |
| `--categoria` | Nome da categoria | `--categoria "alimentos"` |
| `--limit` | Limite de resultados | `--limit 50` |

### Filtros Avancados

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--ncm` | Codigo NCM | `--ncm "2008.99"` |
| `--fornecedor` | Nome do fornecedor | `--fornecedor "vale sul"` |
| `--preco-min` | Preco de venda minimo | `--preco-min 10` |
| `--preco-max` | Preco de venda maximo | `--preco-max 100` |
| `--com-estoque` | Apenas com estoque disponivel | flag |
| `--sem-estoque` | Apenas sem estoque | flag |

### Opcoes de Saida

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--detalhes` | Incluir fornecedores, estoque e mais campos | flag |
| `--fiscais` | Incluir campos fiscais (NCM, origem, etc) | flag |
| `--resumo` | Mostrar apenas totalizadores | flag |
| `--json` | Saida em formato JSON | flag |

## Exemplos de Uso

### Produtos ativos para venda
```bash
python .../consulta.py --tipo produtos --subtipo vendaveis
```

### Buscar por codigo interno
```bash
python .../consulta.py --tipo produtos --codigo "PROD001"
```

### Buscar por nome
```bash
python .../consulta.py --tipo produtos --nome "pupunha"
```

### Buscar por codigo de barras
```bash
python .../consulta.py --tipo produtos --barcode "7891234567890"
```

### Produtos de uma categoria
```bash
python .../consulta.py --tipo produtos --categoria "conservas"
```

### Produtos por NCM
```bash
python .../consulta.py --tipo produtos --ncm "2008.99" --fiscais
```

### Produtos de um fornecedor
```bash
python .../consulta.py --tipo produtos --fornecedor "vale sul" --detalhes
```

### Produtos com estoque disponivel
```bash
python .../consulta.py --tipo produtos --com-estoque
```

### Resumo do catalogo
```bash
python .../consulta.py --tipo produtos --resumo
```

## Campos Retornados

### Campos Padrao (product.product)
- ID, Nome, Codigo Interno (default_code)
- Codigo de Barras
- Categoria
- Tipo (Estocavel, Consumivel, Servico)
- Preco de Venda, Custo
- Unidade de Medida
- Pode ser vendido, Pode ser comprado

### Com `--detalhes`
- Quantidade em estoque (qty_available)
- Quantidade prevista (virtual_available)
- Fornecedores (seller_ids)
- Peso, Volume
- Descricoes (venda, compra, picking)

### Com `--fiscais`
- NCM (l10n_br_ncm_id)
- Origem do Produto (l10n_br_origem)
- Tipo do Produto BR (l10n_br_tipo_produto)
- FCI (l10n_br_fci)
- CNPJ Fabricante (l10n_br_cnpj_fabricante)
- Informacoes adicionais fiscais

### Com `--resumo`
- Total de produtos
- Produtos ativos/inativos
- Produtos para venda/compra
- Por tipo (estocavel, servico, consumivel)
- Por categoria (top 10)

## Valores de detailed_type

| Valor | Descricao |
|-------|-----------|
| `product` | Produto Estocavel (controla estoque) |
| `consu` | Consumivel (nao controla estoque) |
| `service` | Servico |

## Valores de l10n_br_origem

| Valor | Descricao |
|-------|-----------|
| `0` | Nacional, exceto indicados nos codigos 3, 4, 5 e 8 |
| `1` | Estrangeira - Importacao direta |
| `2` | Estrangeira - Adquirida mercado interno |
| `3` | Nacional - Conteudo importacao > 40% e <= 70% |
| `4` | Nacional - Processos produtivos decreto |
| `5` | Nacional - Conteudo importacao <= 40% |
| `6` | Estrangeira - Importacao direta sem similar |
| `7` | Estrangeira - Mercado interno sem similar |
| `8` | Nacional - Conteudo importacao > 70% |

## Nao Encontrou o Campo?

Se precisar de um campo que nao esta mapeado, use a skill **descobrindo-odoo-estrutura**:

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo product.product \
  --buscar-campo "nome_do_campo"
```

## Referencias

- [PRODUCT.md](reference/PRODUCT.md) - Campos dos modelos product.product e product.template

## Relacionado

| Skill | Uso |
|-------|-----|
| consultando-odoo-cadastros | Consultas de parceiros (clientes, fornecedores, transportadoras) |
| consultando-odoo-dfe | Consultas DFE (documentos fiscais, tributos) |
| consultando-odoo-financeiro | Consultas de contas a pagar/receber, vencimentos |
| consultando-odoo-compras | Consultas de pedidos de compra (purchase.order) |
| descobrindo-odoo-estrutura | Descobrir campos/modelos nao mapeados |
| integracao-odoo | Criar novas integracoes (desenvolvimento) |
| agente-logistico | Consultas de carteira, separacoes e estoque |

> **NOTA**: Esta skill eh para CONSULTAS de produtos em producao.
> Para consultar cadastros, use `consultando-odoo-cadastros`.
> Para consultar DFE/CTe, use `consultando-odoo-dfe`.
> Para consultar contas a pagar/receber, use `consultando-odoo-financeiro`.
> Para consultar pedidos de compra, use `consultando-odoo-compras`.

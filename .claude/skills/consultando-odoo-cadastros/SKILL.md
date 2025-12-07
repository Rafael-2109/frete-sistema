---
name: consultando-odoo-cadastros
description: "Busca fornecedores, clientes e transportadoras no Odoo (res.partner, delivery.carrier). Use para: localizar fornecedor por CNPJ, dados de transportadora, endereco de cliente, inscricao estadual, cadastro de parceiro, consultar ranking cliente/fornecedor."
---

# Consultando Odoo - Cadastros (Parceiros/Transportadoras)

Skill para consultas de **cadastros** no Odoo ERP.

> **ESCOPO:** Esta skill cobre res.partner (clientes, fornecedores) e delivery.carrier (transportadoras).
> Para descobrir campos desconhecidos, use a skill `descobrindo-odoo-estrutura`.

## Script Principal

### consulta.py

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/consultando-odoo-cadastros/scripts/consulta.py [opcoes]
```

## Tipos de Consulta

```
CADASTROS
│
├── Partner (--tipo partner)
│   Modelo: res.partner
│   │
│   ├── Fornecedor (--subtipo fornecedor)
│   │   Usar: Buscar fornecedor, dados para pagamento
│   │
│   ├── Cliente (--subtipo cliente)
│   │   Usar: Dados de cliente, endereco entrega
│   │
│   └── Todos (--subtipo todos)
│       Usar: Busca geral de parceiros
│
└── Transportadora (--tipo transportadora)
    Modelo: delivery.carrier
    Usar: Metodos de entrega, transportadoras disponiveis
```

## Parametros

### Filtros Basicos

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--tipo` | Tipo de consulta (obrigatorio) | `--tipo partner` ou `--tipo transportadora` |
| `--subtipo` | fornecedor, cliente, todos | `--subtipo fornecedor` |
| `--cnpj` | CNPJ/CPF (aceita parcial) | `--cnpj "18467441"` |
| `--nome` | Nome/Razao social (parcial) | `--nome "atacadao"` |
| `--uf` | Estado (UF) | `--uf SP` |
| `--cidade` | Cidade | `--cidade "Sao Paulo"` |
| `--limit` | Limite de resultados | `--limit 50` |

### Filtros Avancados

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--ie` | Inscricao Estadual | `--ie "123456789"` |
| `--ativo` | Apenas ativos (padrao) | flag |
| `--inativos` | Incluir inativos | flag |
| `--email` | Email (parcial) | `--email "@empresa.com"` |

### Opcoes de Saida

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--detalhes` | Incluir todos os campos mapeados | flag |
| `--endereco` | Incluir campos de endereco completo | flag |
| `--fiscal` | Incluir dados fiscais (IE, IM, regime) | flag |
| `--json` | Saida em formato JSON | flag |

## Exemplos de Uso

### Buscar fornecedor por CNPJ
```bash
python .../consulta.py --tipo partner --subtipo fornecedor --cnpj "18467441"
```

### Buscar cliente por nome
```bash
python .../consulta.py --tipo partner --subtipo cliente --nome "atacadao" --uf SP
```

### Buscar parceiro com dados fiscais
```bash
python .../consulta.py --tipo partner --cnpj "12345678" --fiscal --detalhes
```

### Listar transportadoras ativas
```bash
python .../consulta.py --tipo transportadora
```

### Buscar transportadora por nome
```bash
python .../consulta.py --tipo transportadora --nome "correios"
```

### Buscar parceiro com endereco completo
```bash
python .../consulta.py --tipo partner --nome "empresa" --endereco
```

## Campos Retornados

### Campos Padrao (Partner)
- ID, Nome, Nome fantasia
- CNPJ/CPF
- Email, Telefone, Celular
- Ranking cliente/fornecedor

### Com `--endereco`
- Logradouro, Numero, Complemento
- Bairro, Cidade, UF, CEP
- Pais

### Com `--fiscal`
- Inscricao Estadual (IE)
- Inscricao Municipal (IM)
- Regime Tributario
- Indicador IE
- Situacao Cadastral

### Transportadora (Campos Padrao)
- ID, Nome, Ativo
- Tipo de entrega
- Preco fixo, Margem
- Parceiro vinculado

## Nao Encontrou o Campo?

Se precisar de um campo que nao esta mapeado, use a skill **descobrindo-odoo-estrutura**:

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo res.partner \
  --buscar-campo "nome_do_campo"
```

## Referencias

- [PARTNER.md](reference/PARTNER.md) - Campos do modelo res.partner
- [CARRIER.md](reference/CARRIER.md) - Campos do modelo delivery.carrier

## Relacionado

| Skill | Uso |
|-------|-----|
| consultando-odoo-dfe | Consultas DFE (documentos fiscais, tributos) |
| consultando-odoo-financeiro | Consultas de contas a pagar/receber, vencimentos |
| consultando-odoo-compras | Consultas de pedidos de compra (purchase.order) |
| consultando-odoo-produtos | Consultas de catalogo de produtos (product.product) |
| descobrindo-odoo-estrutura | Descobrir campos/modelos nao mapeados |
| integracao-odoo | Criar novas integracoes (desenvolvimento) |
| agente-logistico | Consultas de carteira, separacoes e estoque |

> **NOTA**: Esta skill eh para CONSULTAS de cadastros em producao.
> Para descobrir campos desconhecidos, use `descobrindo-odoo-estrutura`.
> Para documentos fiscais (DFE, CTe), use `consultando-odoo-dfe`.
> Para contas a pagar/receber, use `consultando-odoo-financeiro`.
> Para pedidos de compra, use `consultando-odoo-compras`.
> Para catalogo de produtos, use `consultando-odoo-produtos`.

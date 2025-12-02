---
name: consultando-odoo-dfe
description: "Busca documentos fiscais (DFE) no Odoo: devolucoes, CTe de frete, notas de entrada, tributos (ICMS, PIS, COFINS, IPI, ST). Use para: NF de devolucao, CTe de transportadora, nota de fornecedor, impostos de nota fiscal, localizar documento por chave, CNPJ, nome, numero NF, produto ou periodo."
---

# Consultando Odoo - Documentos Fiscais (DFE)

Skill para consultas de **documentos fiscais** no Odoo ERP.

> **ESCOPO:** Esta skill cobre DFE (devoluções, CTe, notas de entrada, tributos).
> Para descobrir campos desconhecidos, use a skill `descobrindo-odoo-estrutura`.

## Script Principal

### consulta.py

```bash
source /home/rafaelnascimento/projetos/frete_sistema/venv/bin/activate && \
python /home/rafaelnascimento/projetos/frete_sistema/.claude/skills/consultando-odoo-dfe/scripts/consulta.py [opcoes]
```

## Tipos de Consulta

```
DFE (Documentos Fiscais Eletronicos)
│   Modelo: l10n_br_ciel_it_account.dfe
│
├── Devolucao (--subtipo devolucao)
│   Usar: NF de devolucao, retorno de mercadoria
│
├── CTe (--subtipo cte)
│   Usar: Conhecimento de transporte de entrada
│
├── Normal (--subtipo normal)
│   Usar: NF de compra, entrada normal
│
├── Complementar (--subtipo complementar)
│   Usar: Notas complementares
│
└── Ajuste (--subtipo ajuste)
    Usar: Notas de ajuste
```

## Parametros

### Filtros Basicos

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--tipo dfe` | Tipo de consulta (obrigatorio) | `--tipo dfe` |
| `--subtipo` | devolucao, cte, normal, complementar, ajuste, todos | `--subtipo devolucao` |
| `--cliente` | CNPJ ou nome do emitente | `--cliente "93209765"` |
| `--produto` | Nome do produto | `--produto "pimenta"` |
| `--quantidade` | Quantidade aproximada | `--quantidade 784` |
| `--chave` | Chave de acesso (44 digitos) | `--chave 3525...` |
| `--numero-nf` | Numero da NF | `--numero-nf 123456` |
| `--data-inicio` | Data inicial | `--data-inicio 2025-01-01` |
| `--data-fim` | Data final | `--data-fim 2025-12-31` |
| `--limit` | Limite de resultados | `--limit 50` |

### Filtros Avancados (Fase 1)

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--ncm` | NCM do produto (busca nas linhas) | `--ncm 21069090` |
| `--cfop` | CFOP da operacao (busca nas linhas) | `--cfop 5102` |
| `--com-icms-st` | Apenas documentos com ICMS-ST > 0 | flag |
| `--com-ipi` | Apenas documentos com IPI > 0 | flag |
| `--valor-min` | Valor minimo do documento | `--valor-min 1000` |
| `--valor-max` | Valor maximo do documento | `--valor-max 50000` |

### Opcoes de Saida

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--detalhes` | Incluir linhas/produtos | flag |
| `--fiscais` | Incluir campos tributarios (ICMS, PIS, COFINS, IPI, ST) | flag |
| `--pagamentos` | Incluir informacoes de pagamento/vencimento | flag |
| `--json` | Saida em formato JSON | flag |

## Exemplos de Uso

### Buscar devolucao por cliente
```bash
python .../consulta.py --tipo dfe --subtipo devolucao --cliente "atacadao"
```

### Buscar devolucao por quantidade
```bash
python .../consulta.py --tipo dfe --subtipo devolucao --quantidade 784 --detalhes
```

### Buscar CTe por chave
```bash
python .../consulta.py --tipo dfe --subtipo cte --chave 3525...
```

### Buscar NF com informacoes fiscais completas
```bash
python .../consulta.py --tipo dfe --subtipo normal --cliente "fornecedor" --fiscais --detalhes
```

### Buscar por periodo
```bash
python .../consulta.py --tipo dfe --subtipo devolucao --data-inicio 2025-11-01 --data-fim 2025-11-30
```

### Buscar por NCM
```bash
python .../consulta.py --tipo dfe --ncm 4415 --detalhes
```

### Buscar documentos com ICMS-ST
```bash
python .../consulta.py --tipo dfe --com-icms-st --fiscais
```

### Buscar por faixa de valor
```bash
python .../consulta.py --tipo dfe --valor-min 10000 --valor-max 50000
```

### Buscar com informacoes de pagamento
```bash
python .../consulta.py --tipo dfe --subtipo normal --cliente "fornecedor" --pagamentos
```

## Campos Retornados

### Campos Padrao
- Chave de acesso, Numero NF, Serie
- CNPJ e Nome do emitente
- Data de emissao
- Valor total
- Status

### Com `--fiscais`
**Totais do documento:**
- ICMS: Base de calculo, Valor
- ICMS-ST: Base de calculo, Valor
- PIS, COFINS, IPI: Valores
- Frete, Desconto, Outras despesas

**Por linha (com `--detalhes`):**
- NCM, CFOP
- CST e aliquotas de cada tributo

### Com `--pagamentos`
- Numero da parcela
- Data de vencimento
- Valor da duplicata

## Nao Encontrou o Campo?

Se precisar de um campo que nao esta mapeado, use a skill **descobrindo-odoo-estrutura**:

```bash
source /home/rafaelnascimento/projetos/frete_sistema/venv/bin/activate && \
python /home/rafaelnascimento/projetos/frete_sistema/.claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo l10n_br_ciel_it_account.dfe \
  --buscar-campo "nome_do_campo"
```

## Referencias

- [ROADMAP_IMPLEMENTACAO.md](reference/ROADMAP_IMPLEMENTACAO.md) - Roadmap completo com campos e relacionamentos
- [MODELOS_CONHECIDOS.md](reference/MODELOS_CONHECIDOS.md) - Indice de modelos e status
- [DFE.md](reference/DFE.md) - Campos do modelo DFE com tributos

## Relacionado

| Skill | Uso |
|-------|-----|
| consultando-odoo-cadastros | Consultas de parceiros (clientes, fornecedores, transportadoras) |
| consultando-odoo-financeiro | Consultas de contas a pagar/receber, vencimentos |
| descobrindo-odoo-estrutura | Descobrir campos/modelos nao mapeados |
| integracao-odoo | Criar novas integracoes (desenvolvimento) |
| agente-logistico | Consultas de carteira, separacoes e estoque |

> **NOTA**: Esta skill eh para CONSULTAS de DFE em producao.
> Para consultar cadastros (parceiros, transportadoras), use `consultando-odoo-cadastros`.
> Para consultar contas a pagar/receber, use `consultando-odoo-financeiro`.
> Para descobrir campos desconhecidos, use `descobrindo-odoo-estrutura`.
> Para criar novas integracoes, use `integracao-odoo`.

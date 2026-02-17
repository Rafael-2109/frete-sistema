---
name: descobrindo-odoo-estrutura
description: |
  Descobre campos e estrutura de qualquer modelo do Odoo. ULTIMO RECURSO — use apenas quando nenhuma skill Odoo especializada cobre o modelo.

  USAR QUANDO:
  - Modelo desconhecido: "quais campos tem stock.picking?", "estrutura do modelo X"
  - Buscar campo: "qual campo guarda codigo de barras?", "campo de CNPJ no res.partner"
  - Inspecionar registro: "mostra todos os campos do registro 12345", "valor do campo X"
  - Consulta generica: "busque parceiros com CNPJ 93209765", "registros do modelo Y com filtro Z"

  NAO USAR QUANDO:
  - Rastrear fluxo de NF/PO/SO → usar **rastreando-odoo**
  - Criar pagamento/reconciliar extrato → usar **executando-odoo-financeiro**
  - Split/consolidar PO → usar **conciliando-odoo-po**
  - Validar match NF x PO → usar **validacao-nf-po**
  - Recebimento fisico (lotes/quality check) → usar **recebimento-fisico-odoo**
  - Exportar razao geral → usar **razao-geral-odoo**
  - Criar nova integracao → usar **integracao-odoo**
allowed-tools: Read, Bash, Glob, Grep
---

## Quando NAO Usar Esta Skill

| Situacao | Skill Correta | Por que? |
|----------|--------------|----------|
| Rastrear fluxo NF/PO/SO | **rastreando-odoo** | Rastreamento usa modelos ja mapeados |
| Validar match NF x PO | **validacao-nf-po** | Fase 2, dominio especifico |
| Split/consolidar PO | **conciliando-odoo-po** | Fase 3, operacao de PO |
| Recebimento fisico (lotes/quality check) | **recebimento-fisico-odoo** | Fase 4, armazem |
| Pagamentos/extratos/reconciliacao | **executando-odoo-financeiro** | Financeiro |
| Exportar razao geral | **razao-geral-odoo** | Relatorio contabil |
| Criar integracao (service/route) | **integracao-odoo** | Desenvolvimento |

---

# Descobrindo Odoo Estrutura

Skill de **ULTIMO RECURSO** para descoberta de campos e estrutura de modelos Odoo.

## DECISION TREE — Qual Operacao Usar?

| Se a pergunta menciona... | Operacao | Flag |
|----------------------------|----------|------|
| **Listar campos de modelo** | Listar todos os campos | `--listar-campos` |
| **Buscar campo por nome** | Buscar em nomes/descricoes | `--buscar-campo TERMO` |
| **Ver valores de registro** | Inspecionar registro | `--inspecionar ID` |
| **Consulta com filtro** | Consulta generica | `--filtro '[JSON]'` |

### Regras de Decisao

1. **Modelo desconhecido** → `--listar-campos` primeiro para mapear estrutura
2. **Campo especifico** → `--buscar-campo` com termo (ex: "barcode", "cnpj")
3. **Debug de valor** → `--inspecionar ID` para ver todos os campos de um registro
4. **Consulta com dados** → `--filtro` + `--campos` + `--limit`

## Regras de Negocio (Anti-Alucinacao)

### O Agente PODE Afirmar
- Nomes e tipos de campos retornados pelo Odoo
- Valores de registros inspecionados
- Resultados de consultas com filtro

### O Agente NAO PODE Inventar
- Campos que nao existem no modelo (sem verificar)
- Relacionamentos nao retornados pela API
- Valores de campos nao consultados

---

## Script Disponivel

### descobrindo.py

```bash
source .venv/bin/activate && \
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py [opcoes]
```

### Operacoes Disponiveis

| Operacao | Flag | Descricao | Exemplo |
|----------|------|-----------|---------|
| Listar campos | `--listar-campos` | Lista todos os campos do modelo | `--modelo res.partner --listar-campos` |
| Buscar campo | `--buscar-campo` | Busca campo por nome/descricao | `--modelo res.partner --buscar-campo cnpj` |
| Inspecionar | `--inspecionar` | Mostra todos os campos de um registro | `--modelo res.partner --inspecionar 123` |
| Consulta generica | `--filtro` | Consulta com filtro JSON | `--modelo res.partner --filtro '[["name","ilike","teste"]]'` |

### Parametros

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| `--modelo` | Sim | Nome do modelo Odoo (ex: `res.partner`, `account.move`) |
| `--listar-campos` | Nao | Lista todos os campos do modelo |
| `--buscar-campo` | Nao | Termo para buscar nos nomes/descricoes dos campos |
| `--inspecionar` | Nao | ID do registro para inspecionar |
| `--filtro` | Nao | Filtro em formato JSON |
| `--campos` | Nao | Campos a retornar (JSON), usado com --filtro |
| `--limit` | Nao | Limite de resultados (padrao: 10) |
| `--json` | Nao | Saida em formato JSON |

## Exemplos de Uso

### Descobrir campos de um modelo
```bash
python .../descobrindo.py --modelo l10n_br_ciel_it_account.dfe --listar-campos
```

### Buscar campo especifico
```bash
python .../descobrindo.py --modelo res.partner --buscar-campo cnpj
```

### Inspecionar registro
```bash
python .../descobrindo.py --modelo res.partner --inspecionar 123
```

### Consulta generica com filtro
```bash
python .../descobrindo.py \
  --modelo res.partner \
  --filtro '[["vat","ilike","93209765"]]' \
  --campos '["id","name","vat"]' \
  --limit 5
```

---

## Cenarios Praticos de Descoberta

### Cenario 1: Usuario pergunta sobre campo desconhecido

**Situacao**: "Qual o campo que guarda o codigo de barras do produto?"

```bash
# Passo 1: Buscar campos relacionados a "barcode" no modelo product.product
source .venv/bin/activate && \
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo product.product \
  --buscar-campo barcode

# Resultado esperado: Lista campos como barcode, barcode_ids, etc.
```

**Acao apos descoberta**: Documentar em `.claude/references/odoo/MODELOS_CAMPOS.md` se for campo Odoo, ou `.claude/references/modelos/REGRAS_MODELOS.md` se for regra/gotcha de campo local. Para campos, a fonte de verdade sao os schemas auto-gerados em `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`.

---

### Cenario 2: Debug de campo com valor inesperado

**Situacao**: "Qual o valor do campo X no registro Y?"

> **NOTA**: Para RASTREAR documentos (NF, PO, SO), use a skill `rastreando-odoo` em vez desta.

```bash
# Inspecionar TODOS os campos de um registro especifico
source .venv/bin/activate && \
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo res.partner \
  --inspecionar 12345
```

**Resultado**: Ver todos os valores de campos do registro para debug.

---

### Cenario 3: Preparar nova integracao

**Situacao**: "Preciso criar integracao com modelo stock.picking (movimentacao de estoque)"

```bash
# Passo 1: Listar TODOS os campos do modelo
source .venv/bin/activate && \
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo stock.picking \
  --listar-campos \
  --json > /tmp/stock_picking_campos.json

# Passo 2: Buscar campos especificos de interesse
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo stock.picking \
  --buscar-campo partner

python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo stock.picking \
  --buscar-campo origin

# Passo 3: Pegar um registro de exemplo para entender estrutura
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo stock.picking \
  --filtro '[["state","=","done"]]' \
  --limit 1 \
  --inspecionar
```

**Proximo passo**: Usar skill `integracao-odoo` para criar o Service com os campos descobertos.

## Modelos Conhecidos (Referencia)

| Modelo | Descricao | Skill Relacionada |
|--------|-----------|-------------------|
| `l10n_br_ciel_it_account.dfe` | Documentos Fiscais | rastreando-odoo |
| `l10n_br_ciel_it_account.dfe.line` | Linhas dos DFE | rastreando-odoo |
| `res.partner` | Parceiros (clientes, fornecedores) | rastreando-odoo |
| `account.move` | Faturas/Lancamentos | rastreando-odoo |
| `account.move.line` | Linhas de fatura | rastreando-odoo |
| `purchase.order` | Pedidos de compra | rastreando-odoo |
| `sale.order` | Pedidos de venda | rastreando-odoo |
| `product.product` | Produtos | - |

## Fluxo de Trabalho

```
Usuario pergunta sobre dado desconhecido
        │
        ▼
Agent verifica: modelo/campo conhecido?
        │
        ├── SIM → Usa rastreando-odoo para consultar fluxos
        │
        └── NAO → Usa esta skill para descobrir
                    │
                    ▼
              descobrindo.py --modelo X --listar-campos
                    │
                    ▼
              Retorna informacao ao usuario
```

## Relacionado

| Skill | Uso |
|-------|-----|
| rastreando-odoo | Consultas e rastreamento de fluxos documentais (NF, PO, SO, titulos) |
| integracao-odoo | Desenvolvimento de novas integracoes |
| gerindo-expedicao | Consultas de carteira, separacoes e estoque |

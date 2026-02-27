---
name: descobrindo-odoo-estrutura
description: >-
  Esta skill deve ser usada como ULTIMO RECURSO quando nenhuma skill Odoo
  especializada cobre o modelo: "quais campos tem stock.picking?",
  "campo de CNPJ no res.partner", "mostra todos os campos do registro 12345",
  ou precisa explorar estrutura de modelo Odoo desconhecido.
  Nao usar para rastrear documentos (usar rastreando-odoo), criar integracoes
  (usar integracao-odoo), operar financeiro (usar executando-odoo-financeiro),
  ou IDs fixos ja documentados (ler IDS_FIXOS.md via Read).

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

## Regras de Fidelidade de Dados (Anti-Alucinacao)

### OBRIGATORIO — Fidelidade ao Output
- **SEMPRE** usar `--json 2>/dev/null` para capturar output limpo (stderr tem mensagens de diagnostico)
- **NUNCA** citar campos, valores ou totais que NAO aparecem no output JSON do script
- **NUNCA** inventar nomes de campos. Se o output mostra `l10n_br_cnpj`, NAO dizer `cnpj` ou `cnpj_cpf`
- Se `sucesso=false`, reportar o erro EXATAMENTE como retornado, NAO inventar dados

### O Agente PODE Afirmar
- Nomes e tipos de campos retornados pelo Odoo (exatamente como no JSON)
- Valores de registros inspecionados (exatamente como no JSON)
- Total de campos/registros (exatamente como no JSON)

### O Agente NAO PODE Inventar
- Campos que nao existem no modelo (sem verificar)
- Relacionamentos nao retornados pela API
- Valores de campos nao consultados
- Nomes "normalizados" diferentes do retornado (ex: dizer `cnpj` quando o campo e `l10n_br_cnpj`)

---

## Script Disponivel

### descobrindo.py

```bash
source .venv/bin/activate && \
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py [opcoes] --json 2>/dev/null
```

> **IMPORTANTE**: SEMPRE usar `--json 2>/dev/null` para capturar output parseavel. O stderr contem mensagens de diagnostico do PostgreSQL/Flask que poluem o output.

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
| `--campos` | Nao | Campos a retornar (**JSON array**, ex: `'["id","name"]'`), usado com --filtro. NAO usar CSV |
| `--limit` | Nao | Limite de resultados (padrao: 10) |
| `--json` | Nao | Saida em formato JSON |

## Exemplos de Uso

### Descobrir campos de um modelo
```bash
python .../descobrindo.py --modelo l10n_br_ciel_it_account.dfe --listar-campos --json 2>/dev/null
```

### Buscar campo especifico
```bash
python .../descobrindo.py --modelo res.partner --buscar-campo cnpj --json 2>/dev/null
```

### Inspecionar registro
```bash
python .../descobrindo.py --modelo res.partner --inspecionar 123 --json 2>/dev/null
```

### Consulta generica com filtro
```bash
python .../descobrindo.py \
  --modelo res.partner \
  --filtro '[["vat","ilike","93209765"]]' \
  --campos '["id","name","vat"]' \
  --limit 5 --json 2>/dev/null
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
source .venv/bin/activate

# Passo 1: Listar TODOS os campos do modelo
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo stock.picking \
  --listar-campos \
  --json 2>/dev/null > /tmp/stock_picking_campos.json

# Passo 2: Buscar campos especificos de interesse
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo stock.picking \
  --buscar-campo partner --json 2>/dev/null

# Passo 3: Pegar um registro de exemplo (primeiro buscar IDs, depois inspecionar)
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo stock.picking \
  --filtro '[["state","=","done"]]' \
  --campos '["id","name","origin"]' \
  --limit 1 --json 2>/dev/null

# Passo 4: Inspecionar o registro encontrado (usa ID do passo anterior)
python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py \
  --modelo stock.picking \
  --inspecionar 12345 --json 2>/dev/null
```

> **NOTA**: `--filtro` e `--inspecionar` sao MUTUAMENTE EXCLUSIVOS. Para ver detalhes de um registro, primeiro busque IDs com `--filtro`, depois use `--inspecionar ID`.

**Proximo passo**: Usar skill `integracao-odoo` para criar o Service com os campos descobertos.

---

### Cenario 4: Modelo inexistente (tratamento de erro)

**Situacao**: Script retorna `sucesso=false` com mensagem de erro

```json
{
  "sucesso": false,
  "modelo": "ficticio.nao.existe",
  "total": 0,
  "campos": [],
  "erro": "<Fault 2: 'O objeto ficticio.nao.existe não existe'>"
}
```

**Acao**: Reportar o erro EXATAMENTE como retornado. NAO inventar campos para modelo inexistente.

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

---
name: conciliando-transferencias-internas
description: >-
  Esta skill deve ser usada quando o usuario precisa conciliar transferencias
  internas entre contas bancarias da NACOM GOYA no Odoo: "concilie transferencias
  internas", "transferencias entre bancos pendentes", "extrato NACOM GOYA nao
  conciliado", "criar is_internal_transfer", "conciliar pagamento da transferencia
  interna", ou reconciliar extratos de pagamento/recebimento de movimentacoes
  entre contas proprias.

  NAO USAR QUANDO:
  - Reconciliar extrato com titulo de cliente/fornecedor, usar **executando-odoo-financeiro**
  - Apenas consultar/rastrear documentos, usar **rastreando-odoo**
  - Split/consolidar PO, usar **conciliando-odoo-po**
  - Explorar modelo Odoo desconhecido, usar **descobrindo-odoo-estrutura**
allowed-tools: Read, Bash, Glob, Grep
---

## Quando NAO Usar Esta Skill

| Situacao | Skill Correta |
|----------|--------------|
| Reconciliar extrato com titulo de cliente/fornecedor | **executando-odoo-financeiro** |
| Apenas consultar/rastrear documentos | **rastreando-odoo** |
| Split/consolidar PO | **conciliando-odoo-po** |
| Explorar modelo Odoo | **descobrindo-odoo-estrutura** |
| Criar CTe/despesas extras | **integracao-odoo** |

---

# Conciliando Transferencias Internas — NACOM GOYA

Concilia transferencias internas entre contas bancarias da NACOM GOYA no Odoo.
Cobre **2 situacoes** mutuamente exclusivas por par de extrato.

## Parametros (args)

Quando invocada via Skill tool, aceita args para filtrar o escopo da operacao:

| Parametro | Obrigatorio | Descricao | Exemplo |
|-----------|-------------|-----------|---------|
| `--data-inicio` | Nao | Data inicial do range (YYYY-MM-DD) | `--data-inicio 2025-09-01` |
| `--data-fim` | Nao | Data final do range (YYYY-MM-DD) | `--data-fim 2025-09-30` |
| `--valor` | Nao | Filtrar por valor absoluto especifico | `--valor 127501.40` |
| `--journal` | Nao | Filtrar por nome ou ID de journal | `--journal GRAFENO` ou `--journal 883` |

### Exemplos de invocacao

```
# Levantar e conciliar pares de setembro/2025
/conciliando-transferencias-internas --data-inicio 2025-09-01 --data-fim 2025-09-30

# Conciliar apenas GRAFENO↔SICOOB de fevereiro/2025
/conciliando-transferencias-internas --data-inicio 2025-02-01 --data-fim 2025-02-28 --journal GRAFENO

# Conciliar par especifico por valor
/conciliando-transferencias-internas --valor 5203.82 --data-inicio 2025-09-08 --data-fim 2025-09-08

# Sem args: levanta TODOS os pares pendentes (relatorio, sem executar)
/conciliando-transferencias-internas
```

### Comportamento por combinacao de args

| Args fornecidos | Comportamento |
|----------------|--------------|
| Nenhum | Levantar todos os pares pendentes (somente relatorio) |
| `--data-inicio` e `--data-fim` | Levantar + executar conciliacao no range |
| `--data-inicio` + `--journal` | Filtrar por range + journal especifico |
| `--valor` + `--data-inicio` | Buscar par exato (valor + data) e conciliar |

### Parsing dos args

O agente deve interpretar os args e montar o domain do Odoo:

```python
# Exemplo: --data-inicio 2025-09-01 --data-fim 2025-09-30 --journal GRAFENO
domain = [
    '|',
    ['payment_ref', 'ilike', 'NACOM GOYA'],
    ['payment_ref', 'ilike', '61.724.241'],
    ['is_reconciled', '=', False],
    ['to_check', '=', False],
    ['date', '>=', '2025-09-01'],   # --data-inicio
    ['date', '<=', '2025-09-30'],   # --data-fim
    ['journal_id', '=', 883],       # --journal GRAFENO → ID 883
]
```

**Resolucao de journal por nome**:

| Nome | ID |
|------|----|
| GRAFENO | 883 |
| SICOOB | 10 |
| BRADESCO | 388 |
| AGIS GARANTIDA / AGIS | 1046 |
| BRADESCO (copia) | 1054 |
| VORTX GRAFENO / VORTX | 1068 |

---

## Uso Rapido

| Situacao | Funcao | Input |
|----------|--------|-------|
| Ambos extratos nao conciliados | `criar_transferencia_interna_e_conciliar()` | stmt_pag_id, stmt_rec_id, journal_pag_id, journal_rec_id, amount, date |
| Recebimento conciliado, pagamento pendente | `conciliar_pagamento_transferencia_existente()` | stmt_pag_id, amount, date, journal_pag_id |
| Levantar todos os pares pendentes | `levantar_pares_transferencia_interna()` | — (aceita args de filtro) |

Codigo completo: [references/codigo-operacional.md](references/codigo-operacional.md)
Testes validados: [references/fluxo-validado.md](references/fluxo-validado.md)

## REGRAS ANTI-ALUCINACAO

```
NUNCA FAZER:
- NUNCA inventar IDs de journals — consultar Odoo ou IDS_FIXOS.md
- NUNCA usar execute() — usar execute_kw() SEMPRE
- NUNCA assumir "cannot marshal None" e erro — operacao FOI executada
- NUNCA alterar account_id ANTES de partner/payment_ref — account_id DEVE ser ULTIMO write
- NUNCA incluir linhas com "FAV" ou "Movimentação" no matching automatico (falsos positivos)
- NUNCA criar payment sem confirmar par (valor exato + data exata + journals diferentes)

SEMPRE FAZER:
- SEMPRE usar get_odoo_connection() de app.odoo.utils.connection
- SEMPRE filtrar: is_reconciled=False, to_check=False
- SEMPRE usar tolerancia ZERO dias (mesma data exata) no matching
- SEMPRE excluir payment_ref contendo "fav" ou "movimenta" (case-insensitive via .lower())
- SEMPRE verificar is_reconciled apos cada operacao
- SEMPRE reportar resultado por par antes de prosseguir ao proximo
```

## DECISION TREE — Qual Situacao?

```
Linha de extrato com NACOM GOYA / 61.724.241
├── Buscar par: debito (amount<0) + credito (amount>0)
│   └── Mesmo valor absoluto + mesma data + journals diferentes?
│       ├── SIM: Ambos is_reconciled=False?
│       │   ├── SIM → SITUACAO 1 (criar is_internal_transfer + conciliar ambos)
│       │   └── Recebimento reconciliado + Pagamento nao?
│       │       └── SIM → SITUACAO 2 (encontrar titulo pagamento + conciliar)
│       └── NAO: Sem par → Investigar manualmente
└── Filtros de exclusao:
    ├── payment_ref contendo "FAV" → EXCLUIR (pagamento a terceiro)
    └── payment_ref contendo "Movimentação" → EXCLUIR (sem par no destino)
```

## Situacao 1 — Ambos extratos nao conciliados

**Quando**: Debito em journal A + credito em journal B, mesmo valor, mesma data, ambos `is_reconciled=False`.

**Fluxo**: Criar `account.payment` com `is_internal_transfer=True` (journal_id=A, destination_journal_id=B) → `action_post` → Odoo gera paired payment automaticamente → Conciliar AMBOS extratos com suas respectivas linhas PENDENTES.

> Ver [codigo-operacional.md](references/codigo-operacional.md) secao "Situacao 1"

## Situacao 2 — Recebimento ja conciliado, pagamento pendente

**Quando**: Recebimento (credito) ja conciliado com `is_internal_transfer` existente, mas pagamento (debito) ainda `is_reconciled=False`.

**Fluxo**: Buscar `account.payment` existente (is_internal_transfer=True, mesmo valor/data) → Buscar linha PENDENTES(26868) nao reconciliada → Conciliar extrato de pagamento.

> Ver [codigo-operacional.md](references/codigo-operacional.md) secao "Situacao 2"

## Preparacao do Extrato (GOTCHA CRITICO)

`account_id` DEVE ser o **ULTIMO write** antes de `action_post`. Write na statement_line regenera move_lines, revertendo account_id se feito antes.

**Ordem obrigatoria** (dentro de UM ciclo draft→write→post):
1. `button_draft(move_extrato)`
2. Write `partner_id` + `payment_ref` na statement_line
3. Write `name` nas move_lines (re-buscar IDs!)
4. Write `account_id`: TRANSITORIA(22199) → PENDENTES(26868) **[ULTIMO!]**
5. `action_post(move_extrato)`
6. `reconcile([extrato_pendentes_line, payment_pendentes_line])`

## Contas Contabeis

| ID | Codigo | Nome | Uso |
|----|--------|------|-----|
| 26868 | 1110100004 | PENDENTES | Contrapartida do payment |
| 22199 | 1110100003 | TRANSITORIA | Contrapartida do extrato (trocar para PENDENTES) |

## Journals Bancarios (NACOM GOYA - FB, company_id=1)

| ID | Nome | Banco |
|----|------|-------|
| 883 | GRAFENO | Banco Grafeno |
| 10 | SICOOB | Sicoob |
| 388 | BRADESCO | Bradesco |
| 1046 | AGIS GARANTIDA | Agis |
| 1054 | BRADESCO (copia) | Bradesco |
| 1068 | VORTX GRAFENO | Vortx |

## Error Handling

| Cenario | Causa | Acao |
|---------|-------|------|
| `cannot marshal None` | Retorno None do Odoo | IGNORAR — operacao foi executada |
| IDs invalidos apos draft | Odoo recria move_lines | Re-buscar IDs apos cada write na statement_line |
| account_id revertido | Write na statement_line regenera lines | account_id DEVE ser ULTIMO write |
| Payment duplicado | Ja existe transferencia interna | Verificar payments existentes antes de criar |
| Falso positivo | Linha com FAV/Movimentacao | Excluir do matching automatico |

## Testes Validados em Producao (30/03/2026)

| Par | Tipo | Resultado |
|-----|------|-----------|
| 32931 (SICOOB) / 17855 (BRADESCO) | Situacao 1 | OK — R$127.501,40 |
| 10050 (GRAFENO) | Situacao 2 | OK — R$5.203,82 |

## Referencias

| Arquivo | Conteudo |
|---------|----------|
| [codigo-operacional.md](references/codigo-operacional.md) | Funcoes Python completas (4 funcoes) |
| [fluxo-validado.md](references/fluxo-validado.md) | Testes reais com IDs de producao |

## Skills Relacionadas

| Skill | Quando usar |
|-------|-------------|
| [executando-odoo-financeiro](../executando-odoo-financeiro/SKILL.md) | Pagamentos a clientes/fornecedores |
| [rastreando-odoo](../rastreando-odoo/SKILL.md) | Consultar/rastrear documentos |
| [conciliando-odoo-po](../conciliando-odoo-po/SKILL.md) | Split/consolidar POs |

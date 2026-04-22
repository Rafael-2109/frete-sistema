# Formato Canonico das 4 Abas

Fonte autoritativa: `/memories/preferences.xml` do user_id=18 (Marcus Lima), secao `<preference name="baseline_conciliacoes">`.

Arquivo: `extratos_pendentes_mes_journal_<DDmmmYYYY>.xlsx`

---

## Aba 1: "Pendentes Mes x Journal" (posicao 1)

**Fonte**: Odoo `account.bank.statement.line` com `is_reconciled=False`.

**Colunas EXATAS** (nessa ordem):

| Posicao | Nome | Tipo | Calculo |
|---------|------|------|---------|
| A | Mes | texto | `TO_CHAR(date, 'MM/YYYY')` ordenado crescente |
| B | Journal | texto | `account_journal.name` (SICOOB, GRAFENO, BRADESCO, AGIS GARANTIDA, VORTX GRAFENO) |
| C | Linhas | inteiro | `COUNT(*)` pendentes naquele mes+journal |
| D | PGTOS | inteiro | `COUNT(*) FILTER (WHERE amount < 0)` |
| E | Valor Debitos | numerico | `SUM(amount) FILTER (WHERE amount < 0)` — SEMPRE negativo, nao abs |
| F | RECEB. | inteiro | `COUNT(*) FILTER (WHERE amount > 0)` |
| G | Valor Creditos | numerico | `SUM(amount) FILTER (WHERE amount > 0)` |

**Rodape obrigatorio** (imediatamente apos ultima linha de dados):

```
TOTAL | | SUM(C) | SUM(D) | SUM(E) | SUM(F) | SUM(G)
(linha em branco)
Evolucao Baseline
09/Abr/2026 | 8.684
16/Abr/2026 | 6.985 | delta=-1.699
<data_atual> | <total_atual> | delta=<total_atual - 6.985>
```

**Formatacao**:
- Linha TOTAL: negrito + fundo cinza claro (#E8E8E8)
- Valor Debitos: formato `#.##0,00;[Red]-#.##0,00` (vermelho para negativos)
- Valor Creditos: formato `#.##0,00` (positivo)
- Secao Evolucao Baseline: fonte italic, 10pt

---

## Aba 2: "Pendentes" (posicao 2)

**Fonte**: mesma da aba 1, mas linha por linha do extrato.

**Colunas**:

| Posicao | Nome | Tipo | Calculo |
|---------|------|------|---------|
| A | Mes | texto | `TO_CHAR(date, 'MM/YYYY')` |
| B | Journal | texto | `account_journal.name` |
| C | Data | date | `bank_statement_line.date` |
| D | Descricao | texto | `bank_statement_line.payment_ref` ou `name` |
| E | Partner | texto | `res_partner.name` (LEFT JOIN por partner_id, pode ser NULL) |
| F | Valor | numerico | `amount` (preserva sinal: negativo=debito, positivo=credito) |
| G | payment_id | inteiro | `payment_id` (NULL para pendentes de criacao) |

**Filtros**:
- `is_reconciled=False` (obrigatorio)
- Top N por valor absoluto (default N=500)
- Ordenar: mes DESC, amount ABS DESC

**Formatacao**:
- Coluna Valor: formato `#.##0,00;[Red]-#.##0,00`
- Linha de cabecalho: negrito + fundo azul claro (#D9E2F3)
- Freeze pane: primeira linha

---

## Aba 3: "Conciliacoes Dia Anterior" (posicao 3)

**Fonte (UNIAO obrigatoria, escopo Nacom Goya)**:
1. Odoo `account.bank.statement.line` onde `write_date::date = CURRENT_DATE - 1` AND `is_reconciled=True`
2. Local `lancamento_comprovante` onde `status='LANCADO'` AND `DATE(lancado_em) = CURRENT_DATE - 1`

> CarVia (`carvia_conciliacoes`) NAO entra: empresa separada do grupo, fluxo financeiro proprio. Para auditoria CarVia usar skill `gerindo-carvia`.

**ARMADILHA DOCUMENTADA**: consultar apenas uma das fontes Nacom Goya retorna resultado incompleto SEM sinalizacao (exemplo real: reportar 89 linhas quando total correto era 134).

**Colunas EXATAS**:

| Posicao | Nome | Tipo | Calculo |
|---------|------|------|---------|
| A | Usuario | texto | `res_users.name` ou `res_partner.name` via write_uid — NUNCA `SYNC_ODOO_WRITE_DATE` |
| B | Linhas | inteiro | `COUNT(*)` por usuario |
| C | Pgtos | inteiro | `COUNT(*) FILTER (WHERE amount < 0)` |
| D | Valor Debitos | numerico | `SUM(amount) FILTER (WHERE amount < 0)` |
| E | Rec | inteiro | `COUNT(*) FILTER (WHERE amount > 0)` |
| F | Valor Creditos | numerico | `SUM(amount) FILTER (WHERE amount > 0)` |

**Ordenacao**: por total de linhas desc.

**Rodape**:
```
TOTAL | SUM(B) | SUM(C) | SUM(D) | SUM(E) | SUM(F)
```

**Validacao critica**: se algum usuario aparecer como `SYNC_ODOO_WRITE_DATE` ou `SYNC_*`, HA BUG — resolver via JOIN em `res_users` usando `write_uid` antes de entregar.

---

## Aba 4: "Resumo" (posicao 4)

**Fonte**: pivot sobre dados da aba 1.

**Estrutura hierarquica**:

```
Rotulos de Linha          | Soma de PGTOS | Soma de RECEB
---------------------------|---------------|--------------
01/2026 (subtotal verde)   | 450           | 80
  AGIS GARANTIDA           | 20            | 2
  BRADESCO                 | 80            | 15
  GRAFENO                  | 150           | 30
  SICOOB                   | 200           | 33
02/2026 (subtotal verde)   | 520           | 95
  ...
TOTAL GERAL                | SUM(D)        | SUM(F)
```

**Formatacao**:
- Subtotal por mes: fundo `#C6EFCE` (verde claro), negrito
- Sub-itens (journals): indentacao 2 espacos, fonte normal
- Linha "Total Geral": negrito, fundo `#E8E8E8`, topo e base com borda

**Implementacao openpyxl**:
```python
from openpyxl.styles import PatternFill, Font, Border, Side

verde_claro = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
cinza = PatternFill(start_color='E8E8E8', end_color='E8E8E8', fill_type='solid')
bold = Font(bold=True)
```

---

## Ordenacao final do workbook

```python
wb.sheetnames == [
    "Pendentes Mes x Journal",   # aba 1
    "Pendentes",                  # aba 2
    "Conciliacoes Dia Anterior",  # aba 3
    "Resumo",                     # aba 4
]
```

Se nome ou ordem divergir: FALHA. Nao entregar.

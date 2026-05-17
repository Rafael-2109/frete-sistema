# Bloco 9 — Controle e Encerramento do Arquivo Digital

> 4 registros · Paginas PDF 229-232 · Volta ao [INDEX](INDEX.md)
> Registros: 9001, 9900, 9990, 9999

**Conteudo**: estatistica de registros (9900), encerramento do bloco (9990), encerramento do arquivo (9999).

---

## Registro 9001
**Abertura do Bloco 9**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.229 · **Obrig** Sim

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "9001" |
| 02 | IND_DAD | N | 1 | - | S | 0-Com dados, 1-Sem dados |

**Exemplo**: `|9001|0|`

---

## Registro 9900
**Registros do Arquivo**

**Hier** 2 · **Ocor** 1:N · **Chave** [REG_BLC] · **PDF** p.230 · **Obrig** Sim

Identifica quantidade de cada tipo de registro no arquivo. **Todos os tipos de registros existentes no arquivo devem ser totalizados aqui**.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "9900" |
| 02 | REG_BLC | C | 4 | - | S | codigo do registro totalizado (ex: "0150", "I250", etc.) |
| 03 | QTD_REG_BLC | N | - | - | S | total de ocorrencias do registro |

**Regras criticas**:
- REGRA_QTD_REG_BLC_OBRIGATORIO: todos os tipos de registro presentes no arquivo devem ter um 9900 totalizando
- REGRA_REG_BLC_DUPLICIDADE: REG_BLC unico
- REGRA_QTD_REG_BLC: numero real de linhas = QTD_REG_BLC

**Exemplo**: `|9900|0150|10|` (existem 10 registros 0150 no arquivo)

---

## Registro 9990
**Encerramento do Bloco 9**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.231 · **Obrig** Sim

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "9990" |
| 02 | QTD_LIN_9 | N | - | - | S | total linhas Bloco 9 |

**Regra**: REGRA_QTD_LIN_BLOCO9 — total real de linhas = QTD_LIN_9

**Exemplo**: `|9990|100|`

---

## Registro 9999
**Encerramento do Arquivo Digital**

**Hier** 0 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.232 · **Obrig** Sim

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "9999" |
| 02 | QTD_LIN | N | - | - | S | total linhas do arquivo digital |

**Regra**: REGRA_QTD_LIN_ARQUIVO — total real de linhas do arquivo = QTD_LIN

**IMPORTANTE**: 9999.QTD_LIN deve ser igual a I030.QTD_LIN (regra REGRA_IGUAL_QTD_LIN_REG9999) E igual a J900.QTD_LIN (regra REGRA_IGUAL_QTD_LIN_REG9999 do J900).

**Exemplo**: `|9999|10000|`

---

## Composicao dos Livros (Bloco 9)

| Registro | G | R | A | B | Z |
|----------|---|---|---|---|---|
| 9001 | O | O | O | O | O |
| 9900 | O | O | O | O | O |
| 9990 | O | O | O | O | O |
| 9999 | O | O | O | O | O |

---

## Estrutura Final do Arquivo

A ordem de registros do final do arquivo e SEMPRE:

```
...
|J990|<qtd_J>|
|K001|<0 ou 1>|
...registros do bloco K (se aplicavel)...
|K990|<qtd_K>|
|9001|0|
|9900|0000|1|
|9900|0001|1|
|9900|0007|<n>|
... 1 registro 9900 para cada tipo presente ...
|9900|9900|<m>|   ← inclusive ele mesmo
|9900|9990|1|
|9900|9999|1|
|9990|<qtd_9>|
|9999|<qtd_total_arquivo>|
```

**Detalhe sutil**: o proprio 9900 deve ser totalizado em 9900. Cada `|9900|REG_BLC|qtd|` conta como 1 ocorrencia, entao a totalizacao final de 9900 e (numero de tipos distintos no arquivo).

# Bloco C — Informacoes Recuperadas da Escrituracao Contabil Anterior

> 10 registros: `C001`, `C040`, `C050`, `C051`, `C052`, `C150`, `C155`, `C600`, `C650`, `C990`
> Paginas PDF: 88-100
> Volta ao [INDEX](INDEX.md)

**IMPORTANTE**: Os registros do Bloco C **NAO precisam ser importados** — sao preenchidos pelo proprio PGE do Sped Contabil apos recuperacao da ECD anterior (menu Escrituracao → Recuperar ECD anterior).

**Observacao critica**: A ECD a ser recuperada **nao pode** ter o mesmo numero de ordem (NUM_ORD) que outra ECD do mesmo CNPJ + CNPJ_SCP + NIRE, independentemente do ano-calendario.

---

## Registro C001
**Abertura do Bloco C**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.88 · **Obrig** Sim em G/R/B, N em A/Z

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C001" |
| 02 | IND_DAD | N | 1 | - | S | 0-Bloco com dados, 1-Bloco sem dados |

---

## Registro C040
**Identificacao da ECD Recuperada**

**Hier** 2 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.89-91 · **Obrig** F(18) — importado so se ECD assinada

### Campos (19 campos)

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C040" |
| 02 | HASH_ECD_REC | C | 40 | - | S | hash ECD recuperada |
| 03 | DT_INI_ECD_REC | N | 8 | - | S | data inicial |
| 04 | DT_FIN_ECD_REC | N | 8 | - | S | data final |
| 05 | CNPJ_ECD_REC | C | 14 | - | S | CNPJ ECD recuperada |
| 06 | IND_ESC | C | 1 | - | S | G/R/B |
| 07 | COD_VER_LC | C | - | - | S | versao leiaute |
| 08 | NUM_ORD | N | - | - | S | numero ordem da escrituracao |
| 09 | NAT_LIVR | C | 80 | - | S | natureza do livro |
| 10 | IND_SIT_ESP_ECD_REC | N | 1 | - | N | 1-Cisao, 2-Fusao, 3-Incorp, 4-Extincao |
| 11 | IND_NIRE_ECD_REC | N | 1 | - | S | 0-sem NIRE, 1-com NIRE |
| 12 | IND_FIN_ESC_ECD_REC | N | 1 | - | S | 0-Original, 1-Substituta |
| 13 | TIP_ECD_REC | N | 1 | - | - | 0/1/2 |
| 14 | COD_SCP_ECD_REC | C | 14 | - | N | CNPJ SCP |
| 15 | IDENT_MF_ECD_REC | C | 1 | - | S | S/N |
| 16 | IND_ESC_CONS_ECD_REC | C | 1 | - | S | S/N |
| 17 | IND_CENTRALIZADA_ECD_REC | N | 1 | - | N | 0/1 |
| 18 | IND_MUDANCA_PC_ECD_REC | N | 1 | - | N | 0/1 |
| 19 | IND_PLANO_REF_ECD_REC | N | 2 | - | N | 1..10 (mesma tabela do 0000.COD_PLAN_REF) |

---

## Registro C050
**Plano de Contas Recuperado**

**Hier** 3 · **Ocor** 1:N · **Pai** C040 · **Chave** [COD_CTA] · **PDF** p.92 · **Obrig** F(19) — se C040 + assinada

Identifica o plano de contas referente ao arquivo da ECD recuperado (equivale ao I050 da anterior).

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C050" |
| 02 | DT_ALT | N | 8 | - | S | data inclusao/alteracao |
| 03 | COD_NAT | C | 2 | - | S | natureza conta (ver I050) |
| 04 | IND_CTA | C | 1 | - | S | S-Sintetica, A-Analitica |
| 05 | NIVEL | N | - | - | S | nivel hierarquico |
| 06 | COD_CTA | C | - | - | S | codigo da conta |
| 07 | COD_CTA_SUP | C | - | - | N | codigo conta superior |
| 08 | CTA | C | - | - | S | nome da conta |

---

## Registro C051
**Plano de Contas Referencial Recuperado**

**Hier** 4 · **Ocor** 0:N · **Pai** C050 · **Chave** [COD_CCUS]+[COD_CTA_REF] · **PDF** p.93 · **Obrig** F(23) — condicional

Equivale ao I051 da escrituracao recuperada. Nao existe se C040.COD_PLAN_REF vazio.

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C051" |
| 02 | COD_CCUS | C | - | - | N | centro de custo |
| 03 | COD_CTA_REF | C | - | - | S | conta no plano referencial |

---

## Registro C052
**Indicacao dos Codigos de Aglutinacao Recuperados**

**Hier** 4 · **Ocor** 0:N · **Pai** C050 · **Chave** [COD_CCUS]+[COD_AGL] · **PDF** p.94

Equivale ao I052 da escrituracao recuperada. Codigos de aglutinacao usados nas demonstracoes do Bloco J (so contas analiticas).

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C052" |
| 02 | COD_CCUS | C | - | - | N | centro de custo |
| 03 | COD_AGL | C | - | - | S | codigo de aglutinacao |

---

## Registro C150
**Saldos Periodicos Recuperados — Identificacao do Periodo**

**Hier** 3 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.95

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C150" |
| 02 | DT_INI | N | 8 | - | S | data inicial periodo |
| 03 | DT_FIN | N | 8 | - | S | data final periodo |

---

## Registro C155
**Detalhe dos Saldos Periodicos Recuperados**

**Hier** 4 · **Ocor** 1:N · **Pai** C150 · **Chave** [COD_CTA_REC]+[COD_CCUS_REC] · **PDF** p.96-97 · **Obrig** F(20) — se C150 + assinada

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C155" |
| 02 | COD_CTA_REC | C | - | - | S | codigo conta analitica |
| 03 | COD_CCUS_REC | C | - | - | N | centro de custos |
| 04 | VL_SLD_INI_REC | N | 19 | 2 | S | saldo inicial periodo |
| 05 | IND_DC_INI_REC | C | 1 | - | N | D-Devedor, C-Credor |
| 06 | VL_DEB_REC | N | 19 | 2 | S | total debitos |
| 07 | VL_CRED_REC | N | 19 | 2 | S | total creditos |
| 08 | VL_SLD_FIN_REC | N | 19 | 2 | S | saldo final periodo |
| 09 | IND_DC_FIN_REC | C | 1 | - | N | D/C saldo final |

### Regras Criticas

**REGRA_CONTA_C155_INEXISTENTE_I155**: Garante que contas com saldo final != 0 na ECD anterior **existam** na ECD atual (I155). 4 cenarios:
1. Sem mudanca PC + DT_EX_SOCIAL != 31/12 + COD_NAT in [01,02,03,04] + VL_SLD_FIN != 0 → deve existir em I155
2. DT_EX_SOCIAL = 31/12 + COD_NAT = 04 (resultado) + VL_SLD_FIN != 0 → deve existir em I155
3. DT_EX_SOCIAL = 31/12 + COD_NAT in [01,02,03] + VL_SLD_FIN != 0 → deve existir em I155
4. Com mudanca PC (IND_MUDANCA_PC=1) + DT_EX_SOCIAL != 31/12 + COD_NAT in [01,02,03,04] + VL_SLD_FIN != 0 → deve existir I155 + I157 relacionados

**REGRA_NATUREZA_CONTA_C155**: C050.COD_NAT == I050.COD_NAT (mesma natureza para mesma conta entre as 2 ECDs).

---

## Registro C600
**Demonstracoes Contabeis Recuperadas**

**Hier** 2 (na realidade 3 segundo cap 3.2 — verificar) · **Ocor** 1:N · **Chave** [DT_INI]+[DT_FIN]+[ID_DEM] · **PDF** p.98

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C600" |
| 02 | DT_INI | N | 8 | - | S | data inicial |
| 03 | DT_FIN | N | 8 | - | S | data final |
| 04 | ID_DEM | N | 1 | - | S | 1-Demonstracoes da PJ, 2-Consolidadas ou outras PJs |
| 05 | CAB_DEM | C | 65535 | - | N | cabecalho das demonstracoes |

---

## Registro C650
**Demonstracao do Resultado do Exercicio Recuperada**

**Hier** 4 · **Ocor** 1:N · **Pai** C600 · **Chave** [COD_AGL] · **PDF** p.99 · **Obrig** F(22) — se existe C600

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C650" |
| 02 | COD_AGL | C | - | - | S | codigo aglutinacao |
| 03 | NIVEL_AGL | N | - | - | S | nivel codigo aglutinacao |
| 04 | DESCR_COD_AGL | C | - | - | S | descricao |
| 05 | VL_CTA_FIN | N | 19 | 2 | S | saldo final linha |
| 06 | IND_DC_CTA_FIN | C | 1 | - | S | D/C |

---

## Registro C990
**Encerramento do Bloco C**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.100

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "C990" |
| 02 | QTD_LIN_C | N | - | - | S | total linhas Bloco C |

**Regra**: REGRA_QTD_LIN_BLOCO_C — total real = QTD_LIN_C

---

## Composicao dos Livros (Bloco C)

| Registro | G | R | A | B | Z |
|----------|---|---|---|---|---|
| C001 | O | O | N | O | N |
| C040 | F(18) | F(18) | N | F(18) | N |
| C050 | F(19) | F(19) | N | F(19) | N |
| C051 | F(23) | F(23) | N | F(19) | N |
| C052 | F | F | N | F | N |
| C150 | F(19) | F(19) | N | F(19) | N |
| C155 | F(20) | F(20) | N | F(20) | N |
| C600 | F | F | N | F | N |
| C650 | F(22) | F(22) | N | F(22) | N |
| C990 | O | O | N | O | N |

# Bloco I — Lancamentos Contabeis (PRINCIPAL)

> 26 registros · Paginas PDF 101-168 · Volta ao [INDEX](INDEX.md)
> Registros: I001, I010, I012, I015, I020, I030, I050, I051, I052, I053, I075, I100, I150, I155, I157, I200, I250, I300, I310, I350, I355, I500, I510, I550, I555, I990

**Conteudo do bloco**: plano de contas, lancamentos, saldos periodicos, balancetes diarios, contas de resultado, razao auxiliar parametrizavel.

---

## Registro I001
**Abertura do Bloco I**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.101 · **Obrig** Sim

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I001" |
| 02 | IND_DAD | N | 1 | - | S | 0-Com dados, 1-Sem dados |

**Exemplo**: `|I001|0|`

---

## Registro I010
**Identificacao da Escrituracao Contabil**

**Hier** 2 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.102-103 · **Obrig** Sim

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I010" |
| 02 | IND_ESC | C | 1 | - | S | G/R/A/B/Z (ver tipos no [INDEX](INDEX.md#composicao-dos-livros-g--r--a--b--z)) |
| 03 | COD_VER_LC | C | - | - | S | "9.00" (Leiaute 9, ano-calendario 2020+) |

**Regras**: REGRA_VERSAO_LC valida o "9.00".

**Exemplo**: `|I010|G|9.00|`

---

## Registro I012
**Livros Auxiliares ao Diario ou Livro Principal**

**Hier** 3 · **Ocor** 1:N · **PDF** p.104-106 · **Obrig** condicional

**Regras de uso**:
- **Livro Principal** (I010.IND_ESC = R ou B): preencher COM dados dos livros auxiliares A ou Z. Campo 5 (COD_HASH_AUX) OBRIGATORIO.
- **Livro Auxiliar** (I010.IND_ESC = A ou Z): preencher COM dados do livro principal R ou B. Campo 5 NAO preenchido.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I012" |
| 02 | NUM_ORD | N | - | - | S | numero de ordem (>0, sequencial por tipo) |
| 03 | NAT_LIVR | C | 80 | - | S | natureza do livro associado |
| 04 | TIPO | N | 1 | - | S | 0-digital (no Sped), 1-outros |
| 05 | COD_HASH_AUX | C | 40 | - | N | hash do livro auxiliar (so se principal=R/B) |

**Regras**:
- REGRA_OCORRENCIA_UNITARIA_I012: se IND_ESC=A/Z, so 1 ocorrencia
- REGRA_VALIDA_TIPO_LIVRO_AUXILIAR: se 0000.IND_NIRE=1, TIPO deve ser 0 (digital)
- REGRA_CAMPO_COD_HASH_AUX_OBRIGATORIO: se IND_ESC=R/B e TIPO=0, COD_HASH_AUX obrigatorio

**Exemplo (livro principal R declarando auxiliar)**: `|I012|1|DIARIO AUXILIAR DE BANCOS|0|33AE96E3D1A5EE6969D78BDC56551F91AE9558F8|`

---

## Registro I015
**Identificacao das Contas da Escrituracao Resumida**

**Hier** 4 · **Ocor** 0:N · **Pai** I012 · **PDF** p.107-108 · **Obrig** S se I010.IND_ESC in [R, A, Z]

Identifica contas analiticas do livro resumido (R) que recebem lancamentos globais. No livro principal R/B: COD_CTA_RES corresponde a conta **analitica** no I050. No livro auxiliar A/Z: corresponde a conta **sintetica** no I050.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I015" |
| 02 | COD_CTA_RES | C | - | - | S | codigo da conta no plano de contas |

---

## Registro I020
**Campos Adicionais**

**Hier** 3 · **Ocor** 0:N · **PDF** p.109-112 · **Obrig** F(7) — se 0000.IDENT_MF=S

Permite acrescentar campos nao previstos ao final de registros I050 a I355.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I020" |
| 02 | REG_COD | C | 4 | - | S | codigo do registro alvo (I050..I355) |
| 03 | NUM_AD | N | - | - | S | numero sequencial do campo adicional |
| 04 | CAMPO | C | - | - | S | nome do campo adicional |
| 05 | DESCRICAO | C | - | - | N | descricao |
| 06 | TIPO | C | - | - | S | N (numerico, 2 decimais) ou C (caractere) |

**Quando 0000.IDENT_MF=S (moeda funcional)**: criar campos adicionais com nomes EXATOS abaixo (regra REGRA_CAMPOS_ADICIONAIS_OBRIGATORIOS):

| Registro | Campos adicionais obrigatorios (em ordem) |
|----------|-------------------------------------------|
| I155 | VL_SLD_INI_MF (N), IND_DC_INI_MF (C), VL_DEB_MF (N), VL_CRED_MF (N), VL_SLD_FIN_MF (N), IND_DC_FIN_MF (C) |
| I157 | VL_SLD_INI_MF (N), IND_DC_INI_MF (C) |
| I200 | VL_LCTO_MF (N) |
| I250 | VL_DC_MF (N), IND_DC_MF (C) |
| I310 | VAL_DEB_MF (N), VAL_CRED_MF (N) |
| I355 | VL_CTA_MF (N), IND_DC_MF (C) |

**Livro Z + IDENT_MF=S** (caso especial): I155 deve ter `VL_SLD_INI_MF, IND_DC_INI_MF, VL_DEB_MF, VL_CRED_MF, VL_SLD_FIN_MF, IND_DC_MF` (note ultimo nome diferente).

**Exemplo**: `|I020|I310|06|VAL_DEB_MF|TOTAL DOS DEBITOS DO DIA|N|`

---

## Registro I030
**Termo de Abertura**

**Hier** 3 · **Ocor** 1:1 · **PDF** p.113-116 · **Obrig** Sim

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I030" |
| 02 | DNRC_ABERT | C | 17 | - | S | "TERMO DE ABERTURA" (fixo) |
| 03 | NUM_ORD | N | - | - | S | numero ordem do instrumento (>0, sequencial por tipo) |
| 04 | NAT_LIVR | C | 80 | - | S | nome do livro |
| 05 | QTD_LIN | N | - | - | S | total linhas arquivo digital |
| 06 | NOME | C | - | - | S | nome empresarial (= 0000.NOME) |
| 07 | NIRE | N | 11 | - | N | NIRE Junta Comercial |
| 08 | CNPJ | C | 14 | - | S | CNPJ (= 0000.CNPJ) |
| 09 | DT_ARQ | N | 8 | - | N | data arquivamento atos constitutivos |
| 10 | DT_ARQ_CONV | N | 8 | - | N | data conversao sociedade simples → empresaria |
| 11 | DESC_MUN | C | - | - | N | municipio |
| 12 | DT_EX_SOCIAL | N | 8 | - | S | **data encerramento exercicio social** |

**Numeracao livros**: G e R compartilham mesma sequencia. Diarios Auxiliares e Razao Auxiliar tem sequencia propria por especie.

**RAS (Razao Auxiliar Subcontas)**: NAT_LIVR deve ser `RAZAO_AUXILIAR_DAS_SUBCONTAS` (sem MF) ou `RAZAO_AUXILIAR_DAS_SUBCONTAS_MF` (com MF).

**Regras criticas**:
- REGRA_IGUAL_QTD_LIN_REG9999: I030.QTD_LIN == 9999.QTD_LIN
- REGRA_IGUAL_NOME_REG0000: I030.NOME == 0000.NOME
- REGRA_IGUAL_CNPJ_REG0000: I030.CNPJ == 0000.CNPJ
- REGRA_VALIDA_CONTEUDO_NAT_LIVR: I030.NAT_LIVR == J900.NAT_LIVRO
- REGRA_NIRE_UF: 2 primeiros digitos NIRE = codigo UF
- REGRA_CAMPO_OBRIGATORIO_NIRE: NIRE preenchido sse 0000.IND_NIRE=1

**Exemplo**: `|I030|TERMO DE ABERTURA|1|Balancete|500|EMPRESA TESTE|31123456789|11111111000191|01012015||BELO HORIZONTE|31122023|`

---

## Registro I050
**Plano de Contas** (CENTRAL)

**Hier** 3 · **Ocor** 1:N · **Chave** [COD_CTA] · **PDF** p.117-121 · **Obrig** Sim

Plano de contas usado para registro habitual dos fatos. Codigos das contas analiticas sao referenciados em: I015, I155, I250, I310, I355.

**Norma CTG 2001 (R3)**: plano deve ter no minimo **4 niveis** e seguir estrutura patrimonial dos arts. 177-182 da Lei 6.404/76. Apenas contas com saldo ou movimentadas no periodo devem constar.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I050" |
| 02 | DT_ALT | N | 8 | - | S | data inclusao/alteracao |
| 03 | COD_NAT | C | 2 | - | S | natureza (ver tabela) |
| 04 | IND_CTA | C | 1 | - | S | S-Sintetica (grupo), A-Analitica (conta) |
| 05 | NIVEL | N | - | - | S | nivel hierarquico (>=1, +1 a cada mudanca) |
| 06 | COD_CTA | C | - | - | S | codigo da conta |
| 07 | COD_CTA_SUP | C | - | - | N | codigo conta superior (obrig se NIVEL>1) |
| 08 | CTA | C | - | - | S | nome da conta |

### Tabela COD_NAT — Natureza da Conta (CRITICA)

| Cod | Descricao |
|-----|-----------|
| **01** | Contas de Ativo |
| **02** | Contas de Passivo |
| **03** | Patrimonio Liquido |
| **04** | Contas de Resultado |
| **05** | Contas de Compensacao |
| **09** | Outras |

### Regras Criticas

| Regra | O que verifica |
|-------|----------------|
| REGRA_COD_CTA_DUPLICADO | COD_CTA unico no I050 |
| REGRA_AGL_CCUS_VAZIO_PREENCHIDO | Nao pode misturar I052 com COD_CCUS vazio e preenchido com mesmo COD_AGL no mesmo pai |
| REGRA_I051_OBRIGATORIO | Se 0000.COD_PLAN_REF preenchido, todas analiticas precisam mapeamento I051 |
| REGRA_TABELA_NATUREZA | COD_NAT na tabela |
| REGRA_VALIDA_NIVEL_CONTAS | Para G/R/B + IND_CTA=A + COD_NAT in [01,02,03] → NIVEL>=4 |
| REGRA_COD_CTA_IGUAL_COD_CTA_SUP | COD_CTA != COD_CTA_SUP |
| REGRA_COD_CTA_SUP_OBRIGATORIO | Se NIVEL>1, COD_CTA_SUP obrigatorio |
| REGRA_CTA_DE_NIVEL_SUPERIOR_INVALIDA | COD_CTA_SUP deve existir no I050, ser IND_CTA=S e ter NIVEL menor |
| REGRA_NATUREZA_CONTA | Se NIVEL>2, COD_NAT igual ao COD_NAT do pai |
| REGRA_CONTA_SUPERIOR_NAO_SE_APLICA | Se NIVEL=1, COD_CTA_SUP vazio |
| REGRA_ANO_ALT_MAIOR_ANO_FIN | DT_ALT.ano <= 0000.DT_FIN.ano (aviso) |

### Exemplo (hierarquia 4 niveis)

```
|I050|01012023|01|S|1|1||Ativo Sintetica 1|
|I050|01012023|01|S|2|1.1|1|Ativo Sintetica 2|
|I050|01012023|01|S|3|1.1.1|1.1|Ativo Sintetica 3|
|I050|01012023|01|A|4|1.1.1.1|1.1.1|Ativo Analitica 1|
|I050|01012023|01|A|4|1.1.1.2|1.1.1|Ativo Analitica 2|
```

---

## Registro I051
**Plano de Contas Referencial**

**Hier** 4 · **Ocor** 0:N · **Pai** I050 · **Chave** [COD_CCUS] · **PDF** p.122-123 · **Obrig** F(21) — se 0000.COD_PLAN_REF preenchido

DE-PARA entre contas analiticas (ativo/passivo/PL/receitas/despesas) do plano da PJ e plano padronizado da RFB.

**Importante (subcontas auxiliares)**: subcontas auxiliares dos arts. 295, 296, 298, 299 da IN RFB 1.700/2017 devem ser mapeadas para conta referencial **pai** da respectiva subconta.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I051" |
| 02 | COD_CCUS | C | - | - | S(*) | centro de custo (so se interfere no mapeamento) |
| 03 | COD_CTA_REF | C | - | - | S | conta no plano referencial (ver tabela 0000.COD_PLAN_REF) |

(*) Para empresas que optaram pelo RET (IN 1.435/2013, art. 10) com segregacao por centro de custo, COD_CCUS deve ser preenchido.

**Regras**:
- REGRA_REGISTRO_PARA_CONTA_ANALITICA: so existe para I050.IND_CTA=A
- REGRA_NATUREZA_CONTA_DIFERENTE: I050.COD_NAT pai e I051 filha devem ter mesma natureza (01/02/03 ou 04)
- REGRA_CCUS_NO_CENTRO_CUSTOS_N3: COD_CCUS deve existir em I100

**Exemplo**: `|I051||11100009|`

---

## Registro I052
**Indicacao dos Codigos de Aglutinacao**

**Hier** 4 · **Ocor** 0:N · **Pai** I050 · **Chave** [COD_CCUS]+[COD_AGL] · **PDF** p.124-125

Usado para elaboracao das demonstracoes contabeis do Bloco J. Adotar codigo de aglutinacao **valido na data de encerramento** e de **maior detalhamento** usado nas demonstracoes. So para contas analiticas (I050.IND_CTA=A).

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I052" |
| 02 | COD_CCUS | C | - | - | N | centro de custo (so se interfere) |
| 03 | COD_AGL | C | - | - | S | codigo de aglutinacao usado em J100/J150 |

**Regras criticas**:
- REGRA_REGISTRO_PARA_CONTA_ANALITICA: so para I050.IND_CTA=A
- REGRA_COD_CCUS_COD_AGL_DUPLICIDADE: chave (COD_CCUS+COD_AGL) unica
- REGRA_AGLUTINACAO_EM_SINTETICA: **CRITICO** — codigo de aglutinacao usado nas linhas TOTALIZADORAS (sinteticas) do J100/J150 (IND_COD_AGL="T") deve ser **DIFERENTE** dos codigos cadastrados no I052. Causa erro frequente.

**Exemplo**:
```
|I050|01012023|01|S|2|2328.1|2328A|DISPONIVEL|
|I050|03012023|01|A|3|2328.1.0001|2328.1|BANCOS|
|I051|10||1.01.01.02.00|
|I052||1.1|  ← Bancos -> aglutinacao 1.1 (Disponivel)
```

---

## Registro I053
**Subcontas Correlatas**

**Hier** 4 · **Ocor** 0:N · **Pai** I050 · **Chave** [COD_CNT_CORR] · **PDF** p.126-128

Demonstra grupos compostos de uma conta "pai" + subcontas correlatas. Mesma identificacao de grupo pode ser usada para mais de um conjunto.

**Quando NAO informar**: se a propria conta de ativo/passivo for usada como subconta correlata (art. 300, §§3-4, IN 1.700) — nesse caso, I053 nao deve existir.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I053" |
| 02 | COD_IDT | C | 6 | - | S | codigo identif grupo conta-subconta |
| 03 | COD_CNT_CORR | C | - | - | S | codigo da subconta correlata (em I050, so 1 grupo por subconta) |
| 04 | NAT_SUB_CNT | C | 2 | - | S | natureza da subconta (ver tabela) |

### Tabela NAT_SUB_CNT — Natureza da Subconta

| Cod | Descricao | Conta Principal | Fundamento |
|-----|-----------|-----------------|------------|
| 02 | TBU Controlada Direta no Exterior | Participacao Controlada Exterior | Art.76 Lei 12.973/14 |
| 03 | TBU Controlada Indireta no Exterior | Participacao Controlada Exterior | Art.76 Lei 12.973/14 |
| 10 | Goodwill | Participacao Societaria | Art.20,III DL 1.598/77 |
| 11 | Mais Valia | Participacao Societaria | Art.20,II DL 1.598/77 |
| 12 | Menos Valia | Participacao Societaria | Art.20,II DL 1.598/77 |
| 60 | AVJ Reflexo | Participacao Societaria | Arts.24A/24B DL 1.598/77 |
| 65 | AVJ Subscricao Capital | Participacao Societaria | Arts.17/18 Lei 12.973/14 |
| 70 | AVJ Vinculada Ativo/Passivo | Ativo ou Passivo | Arts.13/14 Lei 12.973/14 |
| 71 | AVJ Depreciacao Acumulada | Depreciacao Acumulada | Arts.13§1/14 Lei 12.973/14 |
| 72 | AVJ Amortizacao Acumulada | Amortizacao Acumulada | Arts.13§1/14 Lei 12.973/14 |
| 73 | AVJ Exaustao Acumulada | Exaustao Acumulada | Arts.13§1/14 Lei 12.973/14 |
| 75 | AVP Vinculada Ativo | Ativo | Art.5§1 Lei 12.973/14 |
| 76 | AVP Depreciacao Acumulada | Depreciacao Acumulada | Art.5,III Lei 12.973/14 |
| 77 | AVP Amortizacao Acumulada | Amortizacao Acumulada | Art.5,III Lei 12.973/14 |
| 78 | AVP Exaustao Acumulada | Exaustao Acumulada | Art.5,III Lei 12.973/14 |
| 80 | Mais Valia Anterior - Estagios | Particip Societaria Pais | Art.37§3,I ou 39§1,I Lei 12.973/14 |
| 81 | Menos Valia Anterior - Estagios | Particip Societaria Pais | Art.37§3,I ou 39§1,I Lei 12.973/14 |
| 82 | Goodwill Anterior - Estagios | Particip Societaria Pais | Art.37§3,I ou 39§1,I Lei 12.973/14 |
| 84 | Variacao Mais Valia Anterior | Particip Societaria Pais | Art.37§3,II ou 39§1,II Lei 12.973/14 |
| 85 | Variacao Menos Valia Anterior | Particip Societaria Pais | Art.37§3,II ou 39§1,II Lei 12.973/14 |
| 86 | Variacao Goodwill Anterior | Particip Societaria Pais | Art.37§3,II ou 39§1,II Lei 12.973/14 |
| 90 | Adocao Inicial Vincul/Auxiliar - Ativo/Passivo | Ativo ou Passivo | Arts.66/67 Lei 12.973/14, arts.295-299 IN 1.700/2017 |
| 91 | Adocao Inicial Vincul/Auxiliar - Depreciacao Acum | Depreciacao Acumulada | idem |
| 92 | Adocao Inicial Vincul/Auxiliar - Amortizacao Acum | Amortizacao Acumulada | idem |
| 93 | Adocao Inicial Vincul/Auxiliar - Exaustao Acum | Exaustao Acumulada | idem |

**Regras**:
- REGRA_NAT_090_UNICA_POR_CONTA: maximo 2 subcontas de natureza 90/91/92/93 por conta pai

**Exemplo**: `|I053|FT1234|1.05.01.10|02|`

---

## Registro I075
**Tabela de Historico Padronizado**

**Hier** 3 · **Ocor** 0:N · **Chave** [COD_HIST] · **PDF** p.129 · **Obrig** Facultativo

Define historicos padronizados (unicos por escrituracao) usados no I250.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I075" |
| 02 | COD_HIST | C | - | - | S | codigo unico do historico |
| 03 | DESCR_HIST | C | - | - | S | descricao |

**Exemplo**: `|I075|12345|PAGAMENTO A FORNECEDORES|`

---

## Registro I100
**Centro de Custos**

**Hier** 3 · **Ocor** 0:N · **Chave** [COD_CCUS] · **PDF** p.130 · **Obrig** S se empresa usa centro de custos

Obrigatorio para empresas que usam centros de custo (mesmo que nao necessarios em I051/I052).

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I100" |
| 02 | DT_ALT | N | 8 | - | S | data inclusao/alteracao |
| 03 | COD_CCUS | C | - | - | S | codigo centro de custos |
| 04 | CCUS | C | - | - | S | nome do centro |

**Exemplo**: `|I100|01012005|CC2328-001|DIVISAO A|`

---

## Registro I150
**Saldos Periodicos — Identificacao do Periodo**

**Hier** 3 · **Ocor** 1:12 · **Chave** [DT_INI]+[DT_FIN] · **PDF** p.131-132 · **Obrig** S em G/R/B

Identifica periodo dos saldos contabeis (max mensal, fracao de mes em situacao especial).

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I150" |
| 02 | DT_INI | N | 8 | - | S | data inicial periodo |
| 03 | DT_FIN | N | 8 | - | S | data final periodo |

**Regras criticas**:
- REGRA_CONTINUIDADE_SALDOS_PERIODICOS: deve haver I155 para todos os meses do intervalo do arquivo
- REGRA_DATA_MES: DT_INI/DT_FIN no mesmo mes
- REGRA_DUPLICIDADE_PERIODO_SALDO_PERIODICO: chave unica
- REGRA_DT_INI_INICIO_MES: DT_INI=1o dia do mes (excecao: 0000.DT_INI)
- REGRA_DT_FIN_FIM_MES: DT_FIN=ultimo dia do mes (excecao: 0000.DT_FIN)
- REGRA_VALIDA_MES_I157: se existe I157, mes(I150.DT_INI) = mes(0000.DT_INI)

**Exemplo**: `|I150|01012023|31012023|`

---

## Registro I155
**Detalhe dos Saldos Periodicos** (FILHO DE I150)

**Hier** 4 · **Ocor** 0:N · **Pai** I150 · **Chave** [COD_CTA]+[COD_CCUS] · **PDF** p.133-139 · **Obrig** S se existe I150

Informa saldos das contas contabeis (debitos e creditos mensais para patrimoniais e resultado).

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I155" |
| 02 | COD_CTA | C | - | - | S | conta analitica (deve ser I050.IND_CTA=A) |
| 03 | COD_CCUS | C | - | - | N | centro de custos |
| 04 | VL_SLD_INI | N | 19 | 2 | S | saldo inicial periodo (0 se zero, NUNCA vazio) |
| 05 | IND_DC_INI | C | 1 | - | N | D-Devedor, C-Credor (NUNCA vazio, mesmo se zero) |
| 06 | VL_DEB | N | 19 | 2 | S | total debitos periodo |
| 07 | VL_CRED | N | 19 | 2 | S | total creditos periodo |
| 08 | VL_SLD_FIN | N | 19 | 2 | S | saldo final periodo |
| 09 | IND_DC_FIN | C | 1 | - | N | D/C saldo final (NUNCA vazio) |

**Campos adicionais MF** (se 0000.IDENT_MF=S):
| # | Campo | Tipo | Tam | Dec | Valores |
|---|-------|------|-----|-----|---------|
| 10 | VL_SLD_INI_MF | N | 19 | 2 | saldo inicial em moeda funcional convertido reais |
| 11 | IND_DC_INI_MF | C | 1 | - | D/C |
| 12 | VL_DEB_MF | N | 19 | 2 | total debitos MF |
| 13 | VL_CRED_MF | N | 19 | 2 | total creditos MF |
| 14 | VL_SLD_FIN_MF | N | 19 | 2 | saldo final MF |
| 15 | IND_DC_FIN_MF | C | 1 | - | D/C |

### Regras Criticas (validacoes que mais quebram no PVA)

| Regra | O que verifica |
|-------|----------------|
| REGRA_VALIDACAO_SOMA_SALDO_INICIAL | Em G/R: soma VL_SLD_INI considerando D/C deve ser 0 por periodo |
| REGRA_VALIDACAO_SOMA_SALDO_FINAL | Em G/R: soma VL_SLD_FIN considerando D/C deve ser 0 por periodo |
| REGRA_VALIDACAO_DEB_DIF_CRED | Em G/R: soma VL_DEB == soma VL_CRED por periodo |
| **REGRA_VALIDACAO_SALDO_FINAL** | VL_SLD_FIN = VL_SLD_INI + VL_DEB + VL_CRED (considerando D/C inicial e final) |
| REGRA_VALIDACAO_VALOR_DEB | Soma debitos no I250 = VL_DEB por periodo e conta (G/R/A) |
| REGRA_VALIDACAO_VALOR_CRED | Soma creditos no I250 = VL_CRED por periodo e conta (G/R/A) |
| **REGRA_VALIDACAO_SALDO_INI_DIF_FIN** | A partir do 2o mes: VL_SLD_INI(mes N) = VL_SLD_FIN(mes N-1) — **continuidade** |
| REGRA_DUPLICIDADE_CONTA_SALDO_PERIODICO | Chave (COD_CTA+COD_CCUS) unica por I150 |
| REGRA_CAMPOS_SALDOS_PERIODICOS_DIFERENTE_ZERO | Sem I157 filho, pelo menos 1 valor != 0 (aviso) |
| REGRA_VALIDACAO_VALOR_CRED_BALANCETE | Para B: soma creditos I300/I310 == VL_CRED |
| REGRA_VALIDACAO_VALOR_DEB_BALANCETE | Para B: soma debitos I300/I310 == VL_DEB |
| REGRA_VALIDA_SLD_INI_SOMA_SLD_INI_I157 | VL_SLD_INI = soma VL_SLD_INI dos I157 filhos |
| REGRA_SALDO_INI_INVALIDO | Se ECD anterior recuperada sem mudanca PC: soma VL_SLD_INI = C155.VL_SLD_FIN_REC |
| REGRA_CONTA_I155_INEXISTENTE_C155 | Se ECD recuperada sem mudanca PC: COD_CTA do I155 deve existir em C155 |
| REGRA_NATUREZA_CONTA_I155 | I050.COD_NAT (atual) = C050.COD_NAT (recuperado) para a mesma conta |
| REGRA_VALIDA_SLD_INI_MESMO_EXERC | Conta com saldo!=0 recuperada de C155 deve existir no 1o mes do I155 |

**Exemplo**: `|I155|2328.2.0001||0,00|D|7500,00|5000,00|2500,00|D|`
- saldo inicial = 0 (mas IND_DC_INI="D" obrigatorio)
- debitos 7500 - creditos 5000 = saldo final 2500 Devedor

---

## Registro I157
**Transferencia de Saldos de Plano de Contas Anterior**

**Hier** 5 · **Ocor** 0:N · **Pai** I155 · **Chave** [COD_CTA]+[COD_CCUS] · **PDF** p.140-141 · **Obrig** F(17) — se 0000.IND_MUDANC_PC=1

Informa transferencias de saldos das contas analiticas do plano antigo para novo, quando nao ha lancamentos transferindo em I200/I250.

**Importante**: contas zeradas no ultimo periodo da ECD anterior devem constar no I157 com saldo zero, relacionada a uma conta nova — para a ECF recuperar corretamente.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I157" |
| 02 | COD_CTA | C | - | - | S | conta analitica plano ANTERIOR |
| 03 | COD_CCUS | C | - | - | N | centro custos plano anterior |
| 04 | VL_SLD_INI | N | 19 | 2 | S | saldo inicial periodo |
| 05 | IND_DC_INI | C | 1 | - | N | D/C (obrigatorio mesmo se zero) |

**Campos adicionais MF** (se 0000.IDENT_MF=S): 06=VL_SLD_INI_MF, 07=IND_DC_INI_MF

**Regras**:
- REGRA_CONTA_I157_INEXISTENTE: se ECD recuperada + mudanca PC, COD_CTA deve existir em C155
- REGRA_EXISTE_I157_PERIODO_POSTERIOR: se existe I157, I150.DT_INI = 0000.DT_INI (so 1o mes)
- REGRA_NATUREZA_CONTA_PAI_I157: natureza I155 (01/02/03 ou 04) deve casar com natureza C155 do I157.COD_CTA

**Exemplo**: `|I157|2328.1.0001||1000,00|D|`

---

## Registro I200
**Lancamento Contabil** (CABECALHO)

**Hier** 3 · **Ocor** 1:N · **Chave** [NUM_LCTO] · **PDF** p.142-146 · **Obrig** S em G/R/A

3 tipos de lancamento:
- **N (Normal)**: todos exceto encerramento
- **E (Encerramento)**: zerar contas de resultado na apuracao
- **X (Extemporaneo)**: itens 31-36 da ITG 2000 (R1)

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I200" |
| 02 | NUM_LCTO | C | - | - | S | numero unico do lancamento |
| 03 | DT_LCTO | N | 8 | - | S | data do lancamento |
| 04 | VL_LCTO | N | 19 | 2 | S | valor (soma das partidas mesmo indicador) |
| 05 | IND_LCTO | C | 1 | - | S | N / E / X |
| 06 | DT_LCTO_EXT | N | 8 | - | N | data fato do extemporaneo (obrig se IND_LCTO=X) |

**Campo adicional MF** (se 0000.IDENT_MF=S): 07=VL_LCTO_MF

**Regras criticas**:
- REGRA_VALIDACAO_SALDO_CONTA: soma de lancamentos E para cada (DT_RES, conta) = I355.VL_CTA (D/C invertido)
- REGRA_LCTO_4_FORMULA: lancamento 4a formula (>=2 D e >=2 C) gera aviso — verificar CTG 2001 (R2)
- REGRA_REGISTRO_OBRIGATORIO_I350: se I350 existe, deve existir I200 com IND_LCTO=E (em G/R)
- REGRA_VALIDACAO_VL_LCTO_DEB / VL_LCTO_CRED: para G/R/B, soma debitos do I250 = VL_LCTO E soma creditos do I250 = VL_LCTO
- REGRA_VALIDACAO_VL_LCTO_ESC_AUXILIAR: para A (livro auxiliar), soma D OU soma C do I250 = VL_LCTO (aviso)
- REGRA_DT_LCTO_EXT_OBRIGATORIA: se IND_LCTO=X, DT_LCTO_EXT preenchido
- REGRA_DT_LCTO_EXT_INDEVIDA: se IND_LCTO!=X, DT_LCTO_EXT vazio
- REGRA_DT_LCTO_EXT_INV: DT_LCTO_EXT < 0000.DT_INI (deve ser anterior)
- REGRA_DATA_ANTIGA: DT > 01/01/1980 (aviso)

**Exemplo**: `|I200|1000|02052023|5000,00|N||`

---

## Registro I250
**Partidas do Lancamento**

**Hier** 4 · **Ocor** 1:N · **Pai** I200 · **PDF** p.147-151 · **Obrig** S em G/R/A

Todas contrapartidas (debito/credito) do I200. Soma D = Soma C = I200.VL_LCTO. Para uma mesma conta, soma D = I155.VL_DEB e soma C = I155.VL_CRED.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I250" |
| 02 | COD_CTA | C | - | - | S | conta debitada/creditada (deve ser analitica) |
| 03 | COD_CCUS | C | - | - | N | centro custos |
| 04 | VL_DC | N | 19 | 2 | S | valor da partida |
| 05 | IND_DC | C | 1 | - | S | D-Debito, C-Credito |
| 06 | NUM_ARQ | C | - | - | N | numero/codigo do documento arquivado |
| 07 | COD_HIST_PAD | C | - | - | N | historico padronizado (em I075) |
| 08 | HIST | C | 65535 | - | N | historico completo (ou complementar ao COD_HIST_PAD) |
| 09 | COD_PART | C | - | - | N | participante (em 0150, com relacionamento 0180 ativo) |

**Campos adicionais MF**: 10=VL_DC_MF, 11=IND_DC_MF

**Lancamentos por formula**:
- 1 D + 1 C: 2 registros I250
- 1 D + N C: N+1 registros
- N D + 1 C: N+1 registros
- N D + M C: gera aviso (4a formula — verificar CTG 2001 R2)

**Regras**:
- REGRA_HISTORICO_OBRIGATORIO: HIST OU COD_HIST_PAD preenchido (um dos dois)
- REGRA_LANC_EXT_CONTA_RESULTADO: se I200.IND_LCTO=X (extemporaneo), conta NAO pode ser de resultado (COD_NAT!=04)
- REGRA_VALIDACAO_VALOR_DEB / VALOR_CRED: por periodo+conta, soma debitos no I250 (IND_DC=D) = VL_LCTO

**HIST extemporaneo** (item 32 ITG 2000 R1): deve especificar motivo da correcao, data e numero do lancamento de origem.

**Exemplo (lancamento simples)**:
```
|I200|1000|02032023|5000,00|N|
|I250|1.1||5000,00|D|123||RECEBIMENTO DE CLIENTES – DUPLICATA N. 100.2011||
|I250|1.5||5000,00|C|123||RECEBIMENTO DE CLIENTES – DUPLICATA N. 100.2011||
```

---

## Registro I300
**Balancetes Diarios — Identificacao da Data**

**Hier** 3 · **Ocor** 0:N · **Chave** [DT_BCTE] · **PDF** p.152 · **Obrig** S so em B

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I300" |
| 02 | DT_BCTE | N | 8 | - | S | data do balancete |

**Exemplo**: `|I300|15052023|`

---

## Registro I310
**Detalhes do Balancete Diario**

**Hier** 4 · **Ocor** 1:N · **Pai** I300 · **Chave** [COD_CTA]+[COD_CCUS] · **PDF** p.153-154 · **Obrig** S so em B

Totais de debitos e creditos por conta+CC em determinada data.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I310" |
| 02 | COD_CTA | C | - | - | S | conta analitica |
| 03 | COD_CCUS | C | - | - | N | centro custos |
| 04 | VAL_DEBD | N | 19 | 2 | S | total debitos do dia |
| 05 | VAL_CREDD | N | 19 | 2 | S | total creditos do dia |

**Campos adicionais MF**: 06=VAL_DEB_MF, 07=VAL_CRED_MF (atencao aos nomes em I020)

**Regras**:
- REGRA_VALIDACAO_DC_BALANCETE: soma VAL_DEBD (todas contas) = soma VAL_CREDD (todas contas) por DT_BCTE

**Exemplo**: `|I310|1.1||50000,00|10000,00|`

---

## Registro I350
**Saldos das Contas de Resultado Antes do Encerramento — Identificacao da Data**

**Hier** 3 · **Ocor** 1:12 · **Chave** [DT_RES] · **PDF** p.155-156 · **Obrig** Facultativo

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I350" |
| 02 | DT_RES | N | 8 | - | S | data apuracao resultado |

**Regras**:
- REGRA_ENCERRAMENTO_EXERCICIO: se I030.DT_EX_SOCIAL no intervalo do arquivo e IND_ESC in [G,R,B], deve existir I350 com DT_RES=DT_EX_SOCIAL

**Exemplo**: `|I350|31032023|`

---

## Registro I355
**Detalhes dos Saldos das Contas de Resultado Antes do Encerramento**

**Hier** 4 · **Ocor** 1:N · **Pai** I350 · **Chave** [COD_CTA]+[COD_CCUS] · **PDF** p.157-159 · **Obrig** F(2) — se existe I350

Saldo final de cada conta de resultado **antes** dos lancamentos de encerramento.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I355" |
| 02 | COD_CTA | C | - | - | S | conta de resultado (I050.COD_NAT=04) |
| 03 | COD_CCUS | C | - | - | N | centro custos |
| 04 | VL_CTA | N | 19 | 2 | S | valor saldo final antes encerramento |
| 05 | IND_DC | C | 1 | - | S | D/C |

**Campos adicionais MF**: 06=VL_CTA_MF, 07=IND_DC_MF

**Regras criticas**:
- REGRA_CONTA_RESULTADO: COD_CTA deve ter I050.COD_NAT=04
- REGRA_VALIDACAO_CONTA_RESULTADO: na data de encerramento, soma VL_SLD_FIN dos I155 das contas de resultado = 0
- REGRA_VALIDACAO_SALDO_CONTA: soma lancamentos I200.IND_LCTO=E para (DT_RES, conta) = VL_CTA (D/C invertido)

**Exemplo**: `|I355|4.1||200000,00|C|`

---

## Registros I500/I510/I550/I555 — Razao Auxiliar Parametrizavel (Livro Z)

Usados exclusivamente para livro tipo **Z** (Razao Auxiliar com leiaute customizavel). Permitem definir formato proprio do livro auxiliar.

### I500: Parametros de Impressao

**Hier** 3 · **Ocor** 0:1 · **PDF** p.160 · **Obrig** S em Z

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I500" |
| 02 | TAM_FONTE | N | 2 | - | S | 4 a 12 (impressao A4 paisagem, Courier) |

### I510: Definicao de Campos

**Hier** 3 · **Ocor** 0:N · **PDF** p.161-162 · **Obrig** S em Z

Define os campos do livro Z. Ordem aqui = ordem na visualizacao/impressao.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I510" |
| 02 | NM_CAMPO | C | 16 | - | S | nome sem espacos/especiais |
| 03 | DESC_CAMPO | C | 50 | - | S | descricao (cabecalho coluna) |
| 04 | TIPO_CAMPO | C | 1 | - | S | N ou C |
| 05 | TAM_CAMPO | N | 3 | - | S | tamanho |
| 06 | DEC_CAMPO | N | 2 | - | N | casas decimais (se N) |
| 07 | COL_CAMPO | N | 3 | - | S | largura coluna no relatorio |

**Regras**:
- REGRA_COLUNAS_PAGINA: soma COL_CAMPO + (qtd I510 - 1) = largura max linha (A4 paisagem, fonte Courier)
- REGRA_VALIDA_CONTEUDO_I510_LIVRO_RAS: se I030.NAT_LIVR for RAS, aplica estrutura especifica

### I550: Detalhes (linhas de dados)

**Hier** 3 · **Ocor** 0:N · **PDF** p.163-165 · **Obrig** S em Z

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I550" |
| * | RZ_CONT | varia | varia | varia | N | conteudo dos campos definidos no I510, em ordem, separados por pipe |

**Para RAS especial** (I030.NAT_LIVR = RAZAO_AUXILIAR_DAS_SUBCONTAS[_MF]):
- Campo 3: COD_SUB_CNT (deve estar em I015.COD_CTA_RES)
- Campo 5: CNPJ_INVTD (CNPJ empresa investida, valido, != 0000.CNPJ)
- Campos 10/23: datas validas
- Campo 17/21: SLD_SCNT_INI/FIN (saldo inicial/final subconta)
- Campo 19/20: DEB_SCNT/CRED_SCNT
- Campo 27: IND_ADOC_INI (1-Sim ou 2-Nao)
- Se IND_ADOC_INI=1: NAT_SUB_CNT in [90,91,92,93,94,95]

### I555: Totais

**Hier** 4 · **Ocor** 0:N · **PDF** p.166-167 · **Obrig** Facultativo

Linhas totalizadoras. Mesmos campos do I550, com apenas chaves e totais preenchidos. Demais campos vazios (`||`).

**Exemplo I510 + I550 + I555**:
```
|I510|COD_PROD|CODIGO_DO_PRODUTO|C|13||15|
|I510|DSC_PROD|DESCRICAO_DO_PRODUTO|C|18||20|
|I510|QTD_PROD|QUANTIDADE|N|13|2|15|
|I510|VR_UNIT|VALOR_UNITARIO|N|13|3|15|
|I510|VR_TOT|VALOR_TOTAL|N|13|2|15|
|I550|2001|PRODUTO1|10,10|100|1010|
|I550|2002|PRODUTO2|20,20|100|2020|
|I555|TOTAL|PRODUTO ACABADO|30,30||3030|
```

---

## Registro I990
**Encerramento do Bloco I**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.168 · **Obrig** Sim

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "I990" |
| 02 | QTD_LIN_I | N | - | - | S | total linhas Bloco I |

**Regra**: REGRA_QTD_LIN_BLOCOI — total real = QTD_LIN_I

**Exemplo**: `|I990|1000|`

---

## Composicao dos Livros (Bloco I)

| Registro | G | R | A | B | Z |
|----------|---|---|---|---|---|
| I001 | O | O | O | O | O |
| I010 | O | O | O | O | O |
| I012 | N | O | O | F | O |
| I015 | N | O | O | F | O |
| I020 | F(7) | F(7) | F(7) | F(7) | N |
| I030 | O | O | O | O | O |
| I050 | O | O | O | O | F |
| I051 | F(21) | F(21) | F(21) | F(21) | F(21) |
| I052 | F | F | N | F | N |
| I053 | F | F | N | F | N |
| I075 | F | F | F | N | F |
| I100 | F | F | F | F | F |
| I150 | O | O | F | O | F |
| I155 | O | O | F(3) | O | F(3) |
| I157 | F(17) | F(17) | N | F(17) | N |
| I200 | O | O | O | N | N |
| I250 | O | O | O | N | N |
| I300 | N | N | N | O | N |
| I310 | N | N | N | O | N |
| I350 | F | F | N | F | N |
| I355 | F(2) | F(2) | N | F(2) | N |
| I500 | N | N | N | N | O |
| I510 | N | N | N | N | O |
| I550 | N | N | N | N | O |
| I555 | N | N | N | N | F |
| I990 | O | O | O | O | O |

---

## Notas Operacionais (Dev)

**Bug recorrente PVA — V22-V29 refactor**: A maioria dos erros estruturais do PVA vem de:
1. **I050**: nivel < 4 em conta analitica de natureza 01/02/03 (REGRA_VALIDA_NIVEL_CONTAS)
2. **I050**: COD_NAT do filho diferente do pai quando NIVEL>2 (REGRA_NATUREZA_CONTA)
3. **I052**: COD_AGL repetido entre I052 e linhas sinteticas do J100/J150 (REGRA_AGLUTINACAO_EM_SINTETICA)
4. **I155**: VL_SLD_FIN(N) != VL_SLD_INI(N+1) — continuidade quebrada (REGRA_VALIDACAO_SALDO_INI_DIF_FIN)
5. **I155**: soma debitos I250 != I155.VL_DEB (REGRA_VALIDACAO_VALOR_DEB)
6. **I355**: existe sem ter I200 com IND_LCTO=E correspondente (REGRA_REGISTRO_OBRIGATORIO_I350)
7. **I250**: HIST e COD_HIST_PAD ambos vazios (REGRA_HISTORICO_OBRIGATORIO)
8. **I150**: faltando 1 mes entre os I150 do arquivo (REGRA_CONTINUIDADE_SALDOS_PERIODICOS)
9. **I030**: NAT_LIVR != J900.NAT_LIVRO (REGRA_VALIDA_CONTEUDO_NAT_LIVR)
10. **I030**: QTD_LIN != 9999.QTD_LIN (REGRA_IGUAL_QTD_LIN_REG9999)

**Convencao VL_CTA**: sempre positivo. Sinal vem do IND_DC ("D" ou "C"). Funcao `_ind_dc(saldo, natural)` em `app/relatorios_fiscais/services/sped_ecd_blocks.py:908` inverte natural se saldo<0.

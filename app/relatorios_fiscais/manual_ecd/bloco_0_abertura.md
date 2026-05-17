# Bloco 0 — Abertura, Identificacao e Referencias

> 8 registros: `0000`, `0001`, `0007`, `0020`, `0035`, `0150`, `0180`, `0990`
> Paginas PDF: 64-87
> Volta ao [INDEX](INDEX.md)

---

## Registro 0000
**Abertura do Arquivo Digital e Identificacao do Empresario ou da Sociedade Empresaria**

**Hier** 0 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.64-74 · **Obrig** Sim (todos os livros)

Abre o arquivo da ECD, informa o periodo da escrituracao e identifica a pessoa juridica.

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "0000" |
| 02 | LECD | C | 4 | - | S | "LECD" |
| 03 | DT_INI | N | 8 | - | S | data inicial AAAAMMDD (na verdade ddmmaaaa) |
| 04 | DT_FIN | N | 8 | - | S | data final ddmmaaaa |
| 05 | NOME | C | - | - | S | razao social |
| 06 | CNPJ | C | 14 | - | S | CNPJ PJ (so digitos) — sempre da Socia Ostensiva se SCP |
| 07 | UF | C | 2 | - | S | sigla UF |
| 08 | IE | C | - | - | N | Inscricao Estadual |
| 09 | COD_MUN | N | 7 | - | N | codigo IBGE municipio |
| 10 | IM | C | - | - | N | Inscricao Municipal |
| 11 | IND_SIT_ESP | N | 1 | - | N | 1-Cisao, 2-Fusao, 3-Incorporacao, 4-Extincao |
| 12 | IND_SIT_INI_PER | N | 1 | - | S | 0-Normal, 1-Abertura, 2-Resultante cisao/fusao/inc, 3-Inicio obrig no curso ano |
| 13 | IND_NIRE | N | 1 | - | S | 0-sem NIRE, 1-com NIRE |
| 14 | IND_FIN_ESC | N | 1 | - | S | 0-Original, 1-Substituta |
| 15 | COD_HASH_SUB | C | 40 | - | N | hash da escrituracao substituida (obrig se IND_FIN_ESC=1) |
| 16 | IND_GRANDE_PORTE | N | 1 | - | S | 0-nao, 1-sim (Ativo>240M ou Receita>300M) — gera obrig J935 |
| 17 | TIP_ECD | N | 1 | - | S | 0-nao SCP, 1-socio ostensivo SCP, 2-SCP |
| 18 | COD_SCP | C | 14 | - | N | CNPJ SCP (so se TIP_ECD=2) |
| 19 | IDENT_MF | C | 1 | - | S | S/N moeda funcional (se S → obrig I020) |
| 20 | IND_ESC_CONS | C | 1 | - | S | S/N escrituracoes consolidadas (se S + mes=12 → obrig Bloco K) |
| 21 | IND_CENTRALIZADA | N | 1 | - | S | 0-centralizada, 1-descentralizada (se 1 → obrig 0020) |
| 22 | IND_MUDANC_PC | N | 1 | - | S | 0-sem mudanca plano contas, 1-com mudanca (se 1 → obrig I157) |
| 23 | COD_PLAN_REF | C | 2 | - | N | 1-PJ Lucro Real, 2-PJ Lucro Presumido, 3-Financeiras Real, 4-Seguradoras, 5-Imunes Geral, 6-Imunes Financ, 7-Imunes Segur, 8-Prev Compl, 9-Partidos Politicos, 10-Financeiras Presumido. Vazio = nao mapeia plano referencial |

### Tabelas Internas

**Campo 11 IND_SIT_ESP**: 1-Cisao · 2-Fusao · 3-Incorporacao · 4-Extincao

**Campo 12 IND_SIT_INI_PER**: 0-Normal (1o dia ano/mes) · 1-Abertura · 2-Resultante cisao/fusao/inc · 3-Inicio obrigatoriedade no curso ano

**Campo 07 UF**: AC, AL, AM, AP, BA, DF, CE, ES, GO, MA, MT, MS, MG, PA, PB, PE, PR, PI, RJ, RN, RS, RR, RO, SC, SP, SE, TO (tabela completa com codigos NIRE no PDF p.68)

### Regras de Validacao Criticas

| Regra | O que verifica |
|-------|----------------|
| REGRA_PERIODO_MINIMO_ESCRITURACAO | DT_INI/DT_FIN abrangem no minimo 1 mes (se sem situacao especial) |
| REGRA_PERIODO_MAXIMO_ESCRITURACAO | DT_INI e DT_FIN no mesmo ano |
| REGRA_TAMANHO_ARQUIVO | Arquivo < 5GB OU periodo = 1 mes |
| REGRA_OCORRENCIA_UNITARIA_ARQ | 0000 so 1x por arquivo |
| REGRA_ERRO_ENTIDADE | Se 0007.COD_ENT_REF=05 (TSE) entao COD_PLAN_REF=9 (Partidos Politicos) |
| REGRA_DATA_INI_MAIOR | DT_INI <= DT_FIN |
| REGRA_INICIO_PERIODO | DT_INI = 1o dia do mes E IND_SIT_INI_PER=0 |
| REGRA_FIM_PERIODO | Se IND_SIT_ESP vazio entao DT_FIN = ultimo dia do mes |
| REGRA_VALIDA_CNPJ | CNPJ formacao valida (DV) |
| REGRA_TABELA_UF | UF na tabela |
| REGRA_TABELA_MUNICIPIO | COD_MUN na tabela IBGE |
| REGRA_COD_MUN_INV_UF | Municipio compativel com UF |
| REGRA_HASH_SUBSTITUIDA | Se IND_FIN_ESC=1 entao COD_HASH_SUB preenchido |
| REGRA_VALIDA_HEXADECIMAL | COD_HASH_SUB so [0-9 A-F] uppercase |
| REGRA_SCP_OBRIGATORIO | Se TIP_ECD=2 entao COD_SCP preenchido |
| REGRA_SCP_NAO_PREENCHER | Se TIP_ECD in [0,1] entao COD_SCP vazio |
| REGRA_CNPJ_DIFERENTE_SCP | COD_SCP != CNPJ |
| REGRA_CONGLOMERADO_MES_12 | Se IND_ESC_CONS=S e IND_SIT_ESP vazio entao mes DT_FIN=12 |

### Exemplos de Preenchimento

**Situacao normal**:
```
|0000|LECD|01012023|31122023|EMPRESA TESTE|11111111000199|AM||3434401|99999||0|1|0||0|0||N|N|0|0|1|
```

**Abertura no periodo (inicio 20/03/2023)**:
```
|0000|LECD|20032023|31122023|EMPRESA TESTE|11111111000199|AM||3434401|99999||1|1|0||0|0||N|N|0|0|1|
```

**Incorporacao no periodo (incorporada)**: 1 arquivo soh de 01/01 ate data incorporacao
```
|0000|LECD|01012023|15072023|EMPRESA TESTE|11111111000199|AM||3534401|99999|3|0|0|0||0|0||N|N|0|0|1|
```

**Incorporacao (incorporadora)**: 2 arquivos
- Arquivo 1: 01/01 ate data inc com IND_SIT_ESP=3
- Arquivo 2: 16/(inc+1) ate 31/12 com IND_SIT_INI_PER=2

**Substituta**:
```
|0000|LECD|01012023|31122023|EMPRESA TESTE|11111111000199|AM||3534401|99999||0|1|1|1234567890ABCDEF...|0|0||N|N|0|0|1|
```

---

## Registro 0001
**Abertura do Bloco 0**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.75 · **Obrig** Sim

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "0001" |
| 02 | IND_DAD | N | 1 | - | S | 0-Bloco com dados, 1-Bloco sem dados |

**Exemplo**: `|0001|0|`

---

## Registro 0007
**Outras Inscricoes Cadastrais da Pessoa Juridica**

**Hier** 2 · **Ocor** 0:N · **Pai** 0001 · **PDF** p.76-77 · **Obrig** Sim (todos livros — relacao com tabela entidades)

Inscricoes da PJ que legalmente tem direito de acesso ao livro contabil digital. Codigo Bacen = ID_Bacen Unicad (8 digitos iniciados com "Z").

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "0007" |
| 02 | COD_ENT_REF | C | - | - | S | codigo orgao (ver tabela) |
| 03 | COD_INSCR | C | - | - | N | codigo da PJ no orgao |

### Tabela COD_ENT_REF

| Cod | Descricao |
|-----|-----------|
| 00 | Nenhuma inscricao em outras entidades |
| 01 | Banco Central do Brasil (Bacen) |
| 02 | Superintendencia de Seguros Privados (Susep) |
| 03 | Comissao de Valores Mobiliarios (CVM) |
| 04 | Agencia Nacional de Transportes Terrestres (ANTT) |
| 05 | Tribunal Superior Eleitoral (TSE) |
| AC..TO | Secretaria da Fazenda da respectiva UF |

### Regras

- REGRA_TABELA_INSTITUICOES_CADASTRO: COD_ENT_REF na tabela
- REGRA_VALIDA_INSCRICAO: COD_INSCR segue formato do orgao:
  - 01 (Bacen) → REGRA_VALIDA_ID_BACEN (Z + 7 digitos)
  - 02 (Susep) → REGRA_VALIDA_ID_SUSEP
  - 03 (CVM) → REGRA_VALIDA_ID_CVM

**Exemplo**: `|0007|01|Z1234567|`

---

## Registro 0020
**Escrituracao Contabil Descentralizada**

**Hier** 2 · **Ocor** 0:N · **Pai** 0001 · **PDF** p.78-80 · **Obrig** F(16) — se IND_CENTRALIZADA=1

Preenchido quando PJ usa escrituracao descentralizada (0000.IND_CENTRALIZADA=1). Quando arquivo se refere a **matriz** (IND_DEC=0), os campos 03-08 sao da **filial** (1 registro por filial). Quando arquivo e da **filial** (IND_DEC=1), os campos 03-08 sao da **matriz** (so 1 registro).

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "0020" |
| 02 | IND_DEC | N | 1 | - | S | 0-Escrit Matriz, 1-Escrit Filial |
| 03 | CNPJ | C | 14 | - | S | CNPJ matriz ou filial |
| 04 | UF | C | 2 | - | S | UF matriz ou filial |
| 05 | IE | C | - | - | N | IE matriz ou filial |
| 06 | COD_MUN | N | 7 | - | N | codigo IBGE municipio |
| 07 | IM | C | - | - | N | IM matriz ou filial |
| 08 | NIRE | N | 11 | - | N | NIRE matriz ou filial |

### Regras

- REGRA_OCORRENCIA_0020_ARQ: Se IND_DEC=1 entao 0020 so 1x
- REGRA_CONGLOMERADO_NA_MATRIZ: Se IND_DEC=1 entao 0000.IND_ESC_CONS != "S"
- REGRA_VERIFICA_CNPJ_REG_0000_REG_0020: 8 primeiros digitos do CNPJ iguais aos do 0000.CNPJ
- REGRA_DUPLICIDADE_CNPJ_REG_0000_REG_0020: CNPJ != 0000.CNPJ (deve ser entidade diferente)

**Exemplo (filial declarando matriz)**: `|0020|1|11111111000191|DF|123456|3434401||11111111|`

---

## Registro 0035
**Identificacao das SCP**

**Hier** 2 · **Ocor** 0:N · **Pai** 0001 · **Chave** [COD_SCP] · **PDF** p.81 · **Obrig** F(6) — se TIP_ECD=1

So usado nas ECDs das PJs **socias ostensivas** que possuem SCP, para identificar as SCP no periodo.

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "0035" |
| 02 | COD_SCP | C | 14 | - | S | CNPJ da SCP |
| 03 | NOME_SCP | C | - | - | N | nome da SCP |

### Regras

- REGRA_CNPJ_DIFERENTE_SCP: COD_SCP != 0000.CNPJ

**Exemplo**: `|0035|11111111000291|SCP TESTE 1|`

---

## Registro 0150
**Tabela de Cadastro do Participante**

**Hier** 2 · **Ocor** 0:N · **Pai** 0001 · **Chave** [COD_PART] · **PDF** p.82-84 · **Obrig** Facultativo

Conjunto de informacoes para identificar PFs/PJs com as quais a empresa tem **relacionamento especifico** (somente esses, nao clientes/fornecedores em geral).

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "0150" |
| 02 | COD_PART | C | - | - | S | codigo identif (criado pela PJ) |
| 03 | NOME | C | - | - | S | nome do participante |
| 04 | COD_PAIS | N | 5 | - | S | codigo pais Bacen |
| 05 | CNPJ | C | 14 | - | N | CNPJ |
| 06 | CPF | N | 11 | - | N | CPF |
| 07 | NIT | N | 11 | - | N | NIT/PIS/PASEP/SUS |
| 08 | UF | C | 2 | - | N | UF (so se pais=Brasil) |
| 09 | IE | C | - | - | N | Inscricao Estadual |
| 10 | IE_ST | C | - | - | N | IE substituto tributario |
| 11 | COD_MUN | N | 7 | - | N | codigo IBGE (so se pais=Brasil) |
| 12 | IM | C | - | - | N | Inscricao Municipal |
| 13 | SUFRAMA | C | 9 | - | N | inscricao Suframa |

### Regras

- REGRA_REGISTRO_DUPLICADO: COD_PART unico
- REGRA_TABELA_PAIS: COD_PAIS na tabela Bacen
- REGRA_CAMPO_NAO_OBRIGATORIO_PAIS_BRASIL: UF e COD_MUN so se pais=Brasil

**Exemplo**: `|0150|03|COLIGADA TESTE S.A.|01058|99999999000191|||35|999999||3550508|||`

---

## Registro 0180
**Identificacao do Relacionamento com o Participante**

**Hier** 3 · **Ocor** 0:N · **Pai** 0150 · **PDF** p.85-86 · **Obrig** F(1) — obrigatorio se existe 0150

Codigos de relacionamento dos participantes do 0150, com data inicio e termino do relacionamento.

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "0180" |
| 02 | COD_REL | N | 2 | - | S | codigo relacionamento (ver tabela) |
| 03 | DT_INI_REL | N | 8 | - | S | data inicio relacionamento |
| 04 | DT_FIN_REL | N | 8 | - | N | data termino |

### Tabela COD_REL

| Cod | Descricao |
|-----|-----------|
| 01 | Matriz no exterior |
| 02 | Filial/agencia/dependencia no exterior |
| 03 | Coligada, inclusive equiparada |
| 04 | Controladora |
| 05 | Controlada (exceto subsidiaria integral) |
| 06 | Subsidiaria integral |
| 07 | Controlada em conjunto |
| 08 | Entidade de Proposito Especifico (CVM) |
| 09 | Participante do conglomerado (orgao regulador), exceto se ja se enquadra |
| 10 | Vinculadas (Art. 23 Lei 9.430/96), exceto se ja se enquadra |
| 11 | Localizada em pais com tributacao favorecida (Art. 24 Lei 9.430/96), exceto se ja se enquadra |

**Exemplo**: `|0180|03|23032019||` (Coligada desde 23/03/2019, sem termino)

---

## Registro 0990
**Encerramento do Bloco 0**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.87 · **Obrig** Sim

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "0990" |
| 02 | QTD_LIN_0 | N | - | - | S | total de linhas do Bloco 0 (inclui o proprio 0990) |

### Regras

- REGRA_QTD_LIN_BLOCO0: numero real de linhas = QTD_LIN_0

**Exemplo**: `|0990|100|`

---

## Composicao dos Livros (Bloco 0)

| Registro | G | R | A | B | Z |
|----------|---|---|---|---|---|
| 0000 | O | O | O | O | O |
| 0001 | O | O | O | O | O |
| 0007 | O | O | O | O | O |
| 0020 | F(16) | F(16) | F(16) | F(16) | F(16) |
| 0035 | F(6) | F(6) | N | F(6) | N |
| 0150 | F | F | F | N | F |
| 0180 | F(1) | F(1) | F(1) | N | F(1) |
| 0990 | O | O | O | O | O |

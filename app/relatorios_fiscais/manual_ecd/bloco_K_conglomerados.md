# Bloco K — Conglomerados Economicos

> 11 registros · Paginas PDF 208-228 · Volta ao [INDEX](INDEX.md)
> Registros: K001, K030, K100, K110, K115, K200, K210, K300, K310, K315, K990

**Obrigatoriedade**: Bloco K obrigatorio quando `0000.IND_ESC_CONS = "S"` (escrituracoes consolidadas) E (mes da `0000.DT_FIN = 12` OU `0000.IND_SIT_ESP` preenchido).

**Quem preenche**: empresas **controladoras** obrigadas a apresentar demonstracoes consolidadas (Lei 6.404/76 e/ou CPC 36 — Demonstracoes Consolidadas).

---

## Registro K001
**Abertura do Bloco K**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.208 · **Obrig** F(9) — condicional

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K001" |
| 02 | IND_DAD | N | 1 | - | S | 0-Com dados, 1-Sem dados |

---

## Registro K030
**Periodo da Escrituracao Contabil Consolidada**

**Hier** 2 · **Ocor** 0:1 · **Chave** [DT_INI_CONS] · **PDF** p.209-210 · **Obrig** condicional

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K030" |
| 02 | DT_INI | N | 8 | - | S | data inicial consolidado |
| 03 | DT_FIN | N | 8 | - | S | data final consolidado (= 0000.DT_FIN) |

**Regras criticas**:
- REGRA_OBRIGATORIO_K030: existe sse 0000.IND_ESC_CONS=S E mes(0000.DT_FIN)=12 (caso contrario, NAO deve existir)
- REGRA_IGUAL_DT_FIN_REG0000: K030.DT_FIN = 0000.DT_FIN
- REGRA_PERIODO_CONS: DT_FIN - DT_INI <= 1 ano

**Exemplo**: `|K030|01012023|31122023|`

---

## Registro K100
**Relacao das Empresas Consolidadas**

**Hier** 3 · **Ocor** 0:N · **Chave** [EMP_COD] · **PDF** p.211-214

Identifica empresas que fazem parte da escrituracao consolidada. **Deve existir 1 K100 com CNPJ igual ao do 0000** (a propria empresa titular da ECD).

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K100" |
| 02 | COD_PAIS | N | 5 | - | S | codigo Bacen pais |
| 03 | EMP_COD | N | 4 | - | S | codigo identif empresa (chave interna) |
| 04 | CNPJ | C | 8 | - | N | CNPJ basico (8 digitos) — obrig se pais=Brasil |
| 05 | NOME | C | - | - | S | nome empresarial |
| 06 | PER_PART | N | 8 | 4 | S | % participacao acionaria total (0-100) |
| 07 | EVENTO | C | 1 | - | S | S-Houve evento societario, N-Nao |
| 08 | PER_CONS | N | 8 | 4 | S | % consolidacao do resultado (0-100) |
| 09 | DATA_INI_EMP | N | 8 | - | S | data inicial escrit empresa consolidada |
| 10 | DATA_FIN_EMP | N | 8 | - | S | data final escrit empresa consolidada |

**Regras criticas**:
- REGRA_REGISTRO_OBRIGATORIO_K110: se EVENTO=S, deve existir K110; se EVENTO=N, nao deve existir K110
- REGRA_OBRIGATORIO_K100_CNPJ_0000: deve existir 1 K100 com K100.CNPJ = 0000.CNPJ (8 primeiros digitos)
- REGRA_TABELA_PAISES: COD_PAIS na tabela Bacen
- REGRA_OBRIGATORIO_CNPJ_BRASIL: se CNPJ preenchido, COD_PAIS deve ser "Brasil"
- REGRA_PERC_MENOR_IGUAL_100: PER_PART e PER_CONS <= 100
- REGRA_ANO_IGUAL_ANTERIOR_K030: anos de DATA_INI_EMP/DATA_FIN_EMP = ano K030.DT_INI/DT_FIN ou ano anterior
- REGRA_DATA_FIN_MAIOR_IGUAL: DATA_FIN_EMP >= DATA_INI_EMP
- REGRA_PERIODO_CONS: DATA_FIN_EMP - DATA_INI_EMP <= 1 ano
- REGRA_CONSOLIDADA_FINAL_DIFERENTE: DATA_FIN_EMP != K030.DT_FIN → aviso (se menor) ou erro (se maior)

**Exemplo**: `|K100|105|1234|11111111|EMPRESA PARTICIPANTE Z|30,00|S|100,00|01012023|31122023|`

---

## Registro K110
**Relacao dos Eventos Societarios**

**Hier** 4 · **Ocor** 0:N · **Pai** K100 · **PDF** p.215-216 · **Obrig** F(10) — se K100.EVENTO=S

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K110" |
| 02 | EVENTO | N | 1 | - | S | tipo evento (ver tabela) |
| 03 | DT_EVENTO | N | 8 | - | S | data do evento |

### Tabela EVENTO

| Cod | Descricao |
|-----|-----------|
| 1 | Aquisicao |
| 2 | Alienacao |
| 3 | Fusao |
| 4 | Cisao Parcial |
| 5 | Cisao Total |
| 6 | Incorporacao |
| 7 | Extincao |
| 8 | Constituicao |

**Regras criticas**:
- REGRA_REGISTRO_OBRIGATORIO_K115: se EVENTO in [1..6], deve existir K115
- REGRA_REGISTRO_NAO_DEVE_EXISTIR_K115: se EVENTO in [7, 8], NAO deve existir K115
- REGRA_SOMATORIO_PER_EVT_K115: soma K115.PER_EVT <= 100
- REGRA_ANO_IGUAL_ANTERIOR_POSTERIOR_K030: ano(DT_EVENTO) = ano(K030.DT_FIN) ou ano anterior ou ano posterior

**Exemplo**: `|K110|1|30032023|` (Aquisicao em 30/03/2023)

---

## Registro K115
**Empresas Participantes do Evento Societario**

**Hier** 5 · **Ocor** 0:N · **Pai** K110 · **PDF** p.217-218 · **Obrig** F(11)

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K115" |
| 02 | EMP_COD_PART | N | 4 | - | S | codigo empresa envolvida (em K100) |
| 03 | COND_PART | N | 1 | - | S | 1-Sucessora, 2-Adquirente, 3-Alienante |
| 04 | PER_EVT | N | 8 | 4 | S | % empresa na operacao (0-100) |

**Regras criticas**:
- REGRA_EXISTE_EMP_COD_K100: EMP_COD_PART em K100.EMP_COD
- REGRA_CONDICAO_COMPATIVEL: matriz COND_PART vs K110.EVENTO:
  - COND_PART=1 (Sucessora) → EVENTO in [3,4,5,6]
  - COND_PART=2 (Adquirente) → EVENTO=1
  - COND_PART=3 (Alienante) → EVENTO=2

**Exemplo**: `|K115|1234|1|50,00|`

---

## Registro K200
**Plano de Contas Consolidado**

**Hier** 2 · **Ocor** 1:N · **Chave** [COD_CTA] · **PDF** p.219-221

Plano de contas usado na escrituracao consolidada (analogo ao I050 mas para o grupo).

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K200" |
| 02 | COD_NAT | C | 2 | - | S | natureza (mesma tabela I050: 01/02/03/04/05/09) |
| 03 | IND_CTA | C | 1 | - | S | S-Sintetica, A-Analitica |
| 04 | NIVEL | N | - | - | S | nivel hierarquico (>=1) |
| 05 | COD_CTA | C | - | - | S | codigo da conta |
| 06 | COD_CTA_SUP | C | - | - | N | conta superior (obrig se NIVEL>1) |
| 07 | CTA | C | - | - | S | nome da conta |

**Regras** (analogas ao I050):
- REGRA_ANALITICA_NIVEL_2: se IND_CTA=A e COD_NAT in [01,02,03,04], NIVEL > 2 (aviso)
- REGRA_CONTA_NIVEL_SUPERIOR_NAO_SINTETICA: COD_CTA_SUP deve ser IND_CTA=S
- REGRA_NIVEL_DE_CONTA_NIVEL_SUPERIOR_INVALIDO: nivel pai < nivel filho
- Se NIVEL>2: pai tem mesma COD_NAT

**Exemplo**: `|K200|01|S|1|1||ATIVO|`

---

## Registro K210
**Mapeamento para Planos de Contas das Empresas Consolidadas**

**Hier** 3 · **Ocor** 1:N · **Chave** [COD_EMP]+[COD_CTA_EMP] · **PDF** p.222 · **Obrig** F(13) — se K200.IND_CTA=A

Mapeia cada conta analitica do K200 (consolidado) para a conta correspondente do plano da empresa consolidada.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K210" |
| 02 | COD_EMP | N | 4 | - | S | codigo empresa (em K100.EMP_COD) |
| 03 | COD_CTA_EMP | C | - | - | S | conta da empresa consolidada |

**Regras**:
- REGRA_CONTA_CONSOLIDADA_ANALITICA: conta pai no K200 deve ser IND_CTA=A
- REGRA_EXISTE_EMP_COD_K100: COD_EMP em K100

**Exemplo**: `|K210|1234|1.01.01.01|`

---

## Registro K300
**Saldos das Contas Consolidadas**

**Hier** 3 · **Ocor** 0:N · **Chave** [COD_CTA] · **PDF** p.223-224

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K300" |
| 02 | COD_CTA | C | - | - | S | conta consolidada (em K200, analitica) |
| 03 | VAL_AG | N | 19 | 2 | S | valor absoluto aglutinado (soma das contas individuais) |
| 04 | IND_VAL_AG | C | 1 | - | S | D/C |
| 05 | VAL_EL | N | 19 | 2 | S | valor absoluto das eliminacoes |
| 06 | IND_VAL_EL | C | 1 | - | S | D/C |
| 07 | VAL_CS | N | 19 | 2 | S | valor consolidado (= VAL_AG - VAL_EL) |
| 08 | IND_VAL_CS | C | 1 | - | S | D/C |

**Regras criticas**:
- REGRA_OBRIGATORIEDADE_K310: se VAL_EL > 0, deve existir K310
- REGRA_EXISTE_K200_ANALITICA: COD_CTA em K200 com IND_CTA=A
- REGRA_SOMATORIO_VALOR_ELIMINACOES: VAL_EL = soma K310.VALOR (com indicador D/C)
- REGRA_CALCULO_VALOR_CONSOLIDADO: VAL_CS = VAL_AG - VAL_EL (com sinais D/C)

**Exemplo**: `|K300|1.01.01.01.01|1000,00|D|300,00|D|700,00|D|`

---

## Registro K310
**Empresas Detentoras das Parcelas do Valor Eliminado Total**

**Hier** 4 · **Ocor** 0:N · **Pai** K300 · **Chave** [EMP_COD_PARTE] · **PDF** p.225 · **Obrig** F(12) — se K300.VAL_EL > 0

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K310" |
| 02 | EMP_COD_PARTE | N | 4 | - | S | codigo empresa detentora (em K100) |
| 03 | VALOR | N | 19 | 2 | S | parcela do valor eliminado total |
| 04 | IND_VALOR | C | 1 | - | S | D/C |

**Regra critica**:
- REGRA_SOMATORIO_VALOR_CONTRAPARTIDA: soma K310.VALOR + soma K315.VALOR = 0 (com D/C)

**Exemplo**: `|K310|1234|100,00|D|`

---

## Registro K315
**Empresas Contrapartes das Parcelas do Valor Eliminado Total**

**Hier** 5 · **Ocor** 0:N · **Pai** K310 · **Chave** [EMP_COD_CONTRA]+[COD_CONTRA] · **PDF** p.226-227

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K315" |
| 02 | EMP_COD_CONTRA | N | 4 | - | S | codigo empresa contraparte (em K100) |
| 03 | COD_CONTRA | C | - | - | S | conta consolidada contraparte (em K300) |
| 04 | VALOR | N | 19 | 2 | S | parcela contrapartida (>0) |
| 05 | IND_VALOR | C | 1 | - | S | D/C |

**Regras**:
- REGRA_EMP_COD_CONTRA_DIFERENTE_EMP_COD_PARTE: EMP_COD_CONTRA != K310.EMP_COD_PARTE (aviso)
- REGRA_COD_CTA_DIFERENTE_COD_CONTRA: COD_CONTRA != K300.COD_CTA (aviso)
- REGRA_EXISTE_COD_CTA_K300: COD_CONTRA existe em K300

**Exemplo**: `|K315|5678|2.01.02.01.02|100,00|D|`

---

## Registro K990
**Encerramento do Bloco K**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.228

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "K990" |
| 02 | QTD_LIN_K | N | - | - | S | total linhas Bloco K |

---

## Composicao dos Livros (Bloco K)

| Registro | G | R | A | B | Z |
|----------|---|---|---|---|---|
| K001 | F(9) | F(9) | N | F(9) | N |
| K030 | O | O | N | O | N |
| K100 | O | O | N | O | N |
| K110 | F(10) | F(10) | N | F(10) | N |
| K115 | F(11) | F(11) | N | F(11) | N |
| K200 | O | O | N | O | N |
| K210 | F(13) | F(13) | N | F(13) | N |
| K300 | O | O | N | O | N |
| K310 | F(12) | F(12) | N | F(12) | N |
| K315 | O | O | N | O | N |
| K990 | F(9) | F(9) | N | F(9) | N |

# Capitulo 2 — Dados Tecnicos para Geracao do Arquivo da ECD

> Paginas PDF 52-56 · Volta ao [INDEX](INDEX.md)

---

## 2.1 Introducao

- PJ gera arquivo com recursos proprios
- Arquivo importado para PGE Sped Contabil para: validacao, assinatura digital, transmissao, visualizacao
- A partir da v3.X tambem ha funcionalidade de edicao no proprio PGE

---

## 2.2 Caracteristicas do Arquivo

| Caracteristica | Especificacao |
|----------------|---------------|
| **Formato** | Texto |
| **Codificacao** | ASCII - ISO 8859-1 (Latin-1) |
| **NAO aceitos** | packed decimal, zonados, binarios, float point, EBCDIC, UTF-8 |
| **Organizacao** | Hierarquica (nivel definido em cada registro) |
| **Tamanho** | Variavel por registro |
| **Inicio** | Sempre na coluna 1 |

**Estrutura hipotetica**:
```
Registro 10 - Nivel 1
Registro 20 - Nivel 1
  Registro 30 - Nivel 2
    Registro 40 - Nivel 3
    Registro 50 - Nivel 3
  Registro 60 - Nivel 2
Registro 70 - Nivel 1
```

**Delimitador de campos**: pipe `|` (caractere ASCII 124)
- Antes do primeiro campo + entre cada campo + depois do ultimo
- Pipe NAO pode estar no conteudo dos campos
- Campo vazio: `||` (dois pipes consecutivos)
- Fim de linha: `|` + CRLF (caracteres ASCII 13 e 10)

**Exemplo**:
```
|0150|03|COLIGADA TESTE S.A.|01058|99999999000191|||35|999999||3550508|||
```

---

## 2.3 Regras Gerais de Preenchimento

### 2.3.1 Formato dos Campos

| Tipo | Caracteres permitidos |
|------|----------------------|
| **C (Alfanumerico)** | Todos os caracteres ASCII exceto pipe `\|` (124) e nao imprimiveis (0-31) |
| **N (Numerico)** | Digitos 0-9 + virgula como separador decimal (caractere 44) |

### 2.3.2 Campos Alfanumericos

- Tamanho maximo: 255 caracteres (salvo indicacao distinta)
- Excecoes: `TXT` com 65.536 caracteres

### 2.3.3 Campos Numericos com Casas Decimais

- **SEM** separadores de milhar, sinais (+/-) ou simbolos (%, R$, etc.)
- **COM** virgula como separador decimal
- Respeitar max de casas decimais do campo

**Exemplos**:
| Valor | Formato no arquivo |
|-------|-------------------|
| R$ 1.129.998,99 | `1129998,99` |
| 1.255,42 | `1255,42` |
| 234,567 | `234,567` |
| 10.000 | `10000` ou `10000,00` |
| 17,00% | `17,00` ou `17` |
| 0,00 | `0` ou `0,00` |
| Campo vazio | (vazio) |

### 2.3.4 Campos Numericos — Datas

**Formato**: `ddmmaaaa` (8 digitos, SEM separadores)

| Data | Formato |
|------|---------|
| 01 de Janeiro de 2023 | `01012023` |
| 11.11.2023 | `11112023` |
| 21-03-2023 | `21032023` |
| 09/08/23 | `09082023` |

### 2.3.5 Campos Numericos — Periodos

**Formato**: `mmaaaa` (6 digitos, SEM separadores)

| Periodo | Formato |
|---------|---------|
| Janeiro de 2023 | `012023` |
| 11.2023 | `112023` |
| 03-2023 | `032023` |
| 08/23 | `082023` |

---

## 2.4 Codigos de Identificacao

**CNPJ, CPF, CEP, IE, IM**: todos os digitos com zeros a esquerda. SEM mascaras (sem `.`, `/`, `-`).

### Campos com tamanho fixo

| Campo | Tipo | Tamanho | Exemplo |
|-------|------|---------|---------|
| CPF | N | 11 | `88244044940` (de 882.440.449-40) |
| CPF com zero | N | 11 | `00233344940` |
| NIRE | N | 11 | - |
| CEP | N | 8 | - |
| CNPJ | C | 14 | `123456789000110` |

### Numeros de documentos com mascara

Casos onde mascara FAZ PARTE do conteudo (manter):

| Campo | Exemplo |
|-------|---------|
| NUM_DA | `98.765-43` |
| NUM_DA | `A1B2C-34` |
| Autenticacao DA | `001-1234/02120512345` |
| NUM_PROC | `2002/123456-78` |

---

## 2.5-2.8 Tipos de Tabelas

| Tipo | Mantenedor | Codificacao | Exemplo |
|------|------------|-------------|---------|
| **Externas** | Orgaos terceiros (IBGE, Bacen, RFB, Correios) | Definida pelo orgao | Municipios IBGE (COD_MUN), Paises Bacen (COD_PAIS), Plano Contas Ref RFB (COD_PLAN_REF) |
| **Internas** | SPED (publicada em ato) | Definida no leiaute | IND_SIT_ESP (1-Cisao, 2-Fusao, 3-Incorp, 4-Extincao) |
| **Intrinsecas ao campo** | No proprio leiaute (dominio do campo) | Constam no registro | IND_DAD (0-Com dados, 1-Sem dados) |
| **Elaboradas pela PJ** | A propria empresa | Livre, mas unico por arquivo + mesma chave em todo arquivo | I075.COD_HIST (codigos de historico padronizado criados pela PJ) |

---

## Mapa Rapido dos 4 Tipos de Tabelas

### Externas (mantidas por orgaos)

| Campo | Mantenedor | URL |
|-------|------------|-----|
| COD_MUN (IBGE) | IBGE | www.ibge.gov.br |
| COD_PAIS | Banco Central | www.bcb.gov.br |
| COD_CTA_REF (Plano Contas Referencial) | Receita Federal | gov.br/receitafederal |
| CEP | Correios | www.correios.com.br |

### Internas SPED (mais comuns)

| Tabela | Onde aparece | Codigos |
|--------|--------------|---------|
| UF | 0000.UF, 0020.UF, 0150.UF | AC, AL, AM, AP, BA, DF, CE, ES, GO, MA, MT, MS, MG, PA, PB, PE, PR, PI, RJ, RN, RS, RR, RO, SC, SP, SE, TO |
| IND_SIT_ESP | 0000.IND_SIT_ESP | 1-Cisao, 2-Fusao, 3-Incorporacao, 4-Extincao |
| IND_SIT_INI_PER | 0000.IND_SIT_INI_PER | 0-Normal, 1-Abertura, 2-Resultante cisao/fusao/inc, 3-Inicio obrig curso ano |
| COD_PLAN_REF | 0000.COD_PLAN_REF | 1-PJ Real, 2-PJ Presumido, 3-Financeiras Real, 4-Seguradoras, 5-Imunes Geral, 6-Imunes Financ, 7-Imunes Segur, 8-Prev Compl, 9-Partidos, 10-Financeiras Presumido |
| COD_NAT (I050/K200) | I050.COD_NAT | 01-Ativo, 02-Passivo, 03-PL, 04-Resultado, 05-Compensacao, 09-Outras |
| IND_CTA | I050.IND_CTA | S-Sintetica, A-Analitica |
| COD_REL (0180) | 0180.COD_REL | 01-Matriz exterior, 02-Filial exterior, 03-Coligada, 04-Controladora, 05-Controlada, 06-Subsidiaria integral, 07-Controlada conjunto, 08-EPE CVM, 09-Conglomerado, 10-Vinculadas, 11-Tributacao favorecida |
| COD_ENT_REF (0007) | 0007.COD_ENT_REF | 00-Nenhuma, 01-Bacen, 02-Susep, 03-CVM, 04-ANTT, 05-TSE, AC..TO-Secretarias Fazenda |
| COD_ASSIN (J930) | J930.COD_ASSIN | 001-PJ, 203-Diretor, 204-Conselheiro, 205-Adm, 309-Procurador, 312-Inventariante, 313-Liquidante, 315-Interventor, 401-Titular EIRELI, 801-Empresario, 900-Contador, 940-Auditor, 999-Outros (+ varios judiciais) |
| COD_ASSIN_T (J932) | J932.COD_ASSIN_T | 910-Contador Termo, 920-Auditor Termo |
| TIPO_DOC (J800) | J800.TIPO_DOC | 001-DRA, 002-DFC, 003-DVA, 010-Notas Explicativas, 011-Relatorio Adm, 012-Parecer Auditores, 099-Outros |
| COD_MOT_SUBS (J801) | J801.COD_MOT_SUBS | 001-Mudancas saldos, 002-Alt assinatura, 003-Alt demonstracoes, 004-Alt forma escr, 005-Alt num livro, 099-Outros |
| NAT_SUB_CNT (I053/RAS I510) | I053.NAT_SUB_CNT | 2-TBU Controlada direta exterior, 3-TBU indireta, 10-Goodwill, 11-Mais Valia, 12-Menos Valia, 60-AVJ Reflexo, 65-AVJ Subscricao, 70-78 AVJ/AVP variantes, 80-86 Estagios, 90-93 Adocao Inicial |
| EVENTO (K110) | K110.EVENTO | 1-Aquisicao, 2-Alienacao, 3-Fusao, 4-Cisao Parcial, 5-Cisao Total, 6-Incorporacao, 7-Extincao, 8-Constituicao |
| COND_PART (K115) | K115.COND_PART | 1-Sucessora, 2-Adquirente, 3-Alienante |

### Intrinsecas (no proprio leiaute do campo)

| Tabela | Codigos |
|--------|---------|
| IND_DAD | 0-Com dados, 1-Sem dados |
| IND_NIRE | 0-Sem NIRE, 1-Com NIRE |
| IND_FIN_ESC | 0-Original, 1-Substituta |
| IND_GRANDE_PORTE | 0-Nao, 1-Sim (Ativo>240M ou Receita>300M) |
| TIP_ECD | 0-Nao SCP, 1-Socio ostensivo, 2-SCP |
| IDENT_MF | S-Sim moeda funcional, N-Nao |
| IND_ESC_CONS | S-Consolidadas, N-Nao |
| IND_CENTRALIZADA | 0-Centralizada, 1-Descentralizada |
| IND_MUDANC_PC | 0-Sem mudanca PC, 1-Houve mudanca |
| IND_DC (varios) | D-Devedor, C-Credor |
| IND_DEC (0020) | 0-Escrit Matriz, 1-Escrit Filial |
| IND_LCTO (I200) | N-Normal, E-Encerramento, X-Extemporaneo |
| IND_COD_AGL (J100/J150) | T-Totalizador, D-Detalhe |
| IND_GRP_BAL (J100) | A-Ativo, P-Passivo+PL |
| IND_GRP_DRE (J150) | D-Despesa (reduz lucro), R-Receita (incrementa lucro) |
| IND_TIP (J210) | 0-DLPA, 1-DMPL |
| IND_DC_FAT (J215) | D-Devedor, C-Credor, P-Subtotal positivo, N-Subtotal negativo |
| IND_RESP_LEGAL (J930) | S-Sim, N-Nao |
| ID_DEM (J005/C600) | 1-Demonstracoes PJ, 2-Consolidadas/outras PJs |

### Elaboradas pela PJ

| Tabela | Onde |
|--------|------|
| COD_PART (participantes) | 0150 |
| COD_CTA (plano de contas) | I050 |
| COD_HIST (historico padronizado) | I075 |
| COD_CCUS (centro custos) | I100 |
| NUM_LCTO (lancamentos) | I200 |
| COD_AGL (aglutinacao) | I052/J100/J150 |
| COD_IDT (grupo subconta) | I053 |
| NM_CAMPO (livro Z) | I510 |
| EMP_COD (empresa consolidada) | K100 |

**Regras das tabelas PJ**:
- Codigos unicos no arquivo (chave do registro)
- Mesmo codigo nao pode ter descricoes diferentes
- Mascara opcional no codigo, EXCETO quando necessaria para distinguir (ex: 1.01 vs 10.1)

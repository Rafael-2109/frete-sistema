# Bloco J — Demonstracoes Contabeis

> 13 registros · Paginas PDF 169-207 · Volta ao [INDEX](INDEX.md)
> Registros: J001, J005, J100, J150, J210, J215, J800, J801, J900, J930, J932, J935, J990

**Conteudo**: BP, DRE, DLPA/DMPL, notas explicativas, signatarios, encerramento.

**Funcionamento**: Bloco J usa codigos de aglutinacao definidos em I052. PGE totaliza I155 (saldos periodicos) na data do balanco usando COD_AGL e confere contra J100 (BP). DRE (J150) usa saldos de I355 (resultado antes encerramento). Em moeda funcional (0000.IDENT_MF=S), valores do J vem dos campos `_MF` dos blocos I.

**IMPORTANTE**: codigo de aglutinacao **NAO** e codigo de conta contabil. Contas analiticas (I050) alimentam as linhas das demonstracoes via I052 (que mapeia conta → aglutinacao).

---

## Registro J001
**Abertura do Bloco J**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.169-170

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J001" |
| 02 | IND_DAD | N | 1 | - | S | 0-Com dados, 1-Sem dados |

---

## Registro J005
**Demonstracoes Contabeis (Cabecalho)**

**Hier** 2 · **Ocor** 1:12 · **Chave** [DT_INI]+[DT_FIN]+[ID_DEM] · **PDF** p.171-173

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J005" |
| 02 | DT_INI | N | 8 | - | S | data inicial (deve ser pos ultimo encerramento exercicio) |
| 03 | DT_FIN | N | 8 | - | S | data final |
| 04 | ID_DEM | N | 1 | - | S | 1-Demonstracoes da PJ, 2-Consolidadas/outras PJs |
| 05 | CAB_DEM | C | 65535 | - | N | cabecalho (obrig se ID_DEM=2) |

### Regras Criticas

- REGRA_OBRIGATORIA_DEMONSTRACAO: J100 e J150 devem ser preenchidos
- REGRA_REGISTRO_OBRIGATORIO_J005_FIM_EXERCICIO: se I030.DT_EX_SOCIAL no intervalo e IND_ESC in [G/R/B], deve existir J005 com DT_FIN=DT_EX_SOCIAL + J100 + J150
- REGRA_PERIODO_SUP_UM_ANO: periodo > 1 ano gera aviso
- REGRA_ENC_OBRIGATORIO: se ID_DEM=1 e J005 tem filhos J100+J210, deve existir I350 com DT_RES=J005.DT_FIN
- REGRA_DT_INI_MAIOR_DT_FIN: DT_INI <= DT_FIN
- REGRA_CAB_DEM_OBRIGATORIO: se ID_DEM=2, CAB_DEM obrigatorio
- REGRA_DATA_ANTIGA: data > 01/01/1980 (aviso)

**Exemplo**: `|J005|01012023|31012023|1||`

---

## Registro J100
**Balanco Patrimonial** (CENTRAL)

**Hier** 3 · **Ocor** 1:N · **Pai** J005 · **Chave** [COD_AGL] · **PDF** p.174-179

So 2 linhas de NIVEL=1: **Ativo** (IND_GRP_BAL=A) e **Passivo+PL** (IND_GRP_BAL=P).

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J100" |
| 02 | COD_AGL | C | - | - | S | codigo aglutinacao (em I052 se IND_COD_AGL=D; criado se T) |
| 03 | IND_COD_AGL | C | 1 | - | S | T-Totalizador, D-Detalhe |
| 04 | NIVEL_AGL | N | - | - | S | nivel hierarquico |
| 05 | COD_AGL_SUP | C | - | - | N | codigo aglutinacao superior (obrig se NIVEL>1) |
| 06 | IND_GRP_BAL | C | 1 | - | S | A-Ativo, P-Passivo e PL |
| 07 | DESCR_COD_AGL | C | - | - | S | descricao |
| 08 | VL_CTA_INI | N | 19 | 2 | S | valor inicial periodo |
| 09 | IND_DC_CTA_INI | C | 1 | - | S | D/C inicial |
| 10 | VL_CTA_FIN | N | 19 | 2 | S | valor final periodo |
| 11 | IND_DC_CTA_FIN | C | 1 | - | S | D/C final |
| 12 | NOTA_EXP_REF | C | 12 | - | N | referencia nota explicativa |

### Regras Criticas

| Regra | O que verifica |
|-------|----------------|
| REGRA_SOMA_DAS_PARCELAS_BALANCO_INI/FIN | Linhas T: VL_CTA_INI/FIN = soma das linhas filhas com mesmo COD_AGL_SUP (considerando D/C) |
| REGRA_VALIDA_ATIVO_PASSIVO_INI/FIN | Total Ativo (NIVEL=1, A) = Total Passivo+PL (NIVEL=1, P) |
| REGRA_BALANCO_SALDO_INI/FIN | Soma linhas D do Ativo = Soma linhas D do Passivo |
| **REGRA_VALIDA_BALANCO_SALDO_INI** | Linhas D: VL_CTA_INI = soma I155 saldos iniciais (via COD_AGL no I052) — aviso |
| **REGRA_VALIDA_BALANCO_SALDO_FIN** | Linhas D: VL_CTA_FIN = soma I155 saldos finais (via COD_AGL no I052) — **erro** |
| REGRA_COD_AGL_DUPLICIDADE | COD_AGL unico (se preenchido) |
| **REGRA_OBRIGATORIO_I052** | Se IND_COD_AGL=D, deve existir I052 com mesmo COD_AGL apontando para conta analitica I050.IND_CTA=A |
| REGRA_OBRIGATORIO_I052_MESMO_GRUPO | Natureza I050.COD_NAT da conta deve corresponder ao IND_GRP_BAL do J100 |
| REGRA_EXISTEM_2_NIVEIS_1 | Existem exatamente 2 linhas NIVEL=1, uma A e uma P |
| REGRA_EXISTEM_MAIS_DE_2_NIVEIS_1 | Quantidade NIVEL=1 = 2 (nao mais, nao menos) |
| REGRA_EXISTE_IND_COD_AGLU_DETALHE | Existe ao menos 1 linha IND_COD_AGL=D |
| REGRA_EXISTE_NOTA_EXPLICATIVA | Se NOTA_EXP_REF preenchido, deve existir J800 com TIPO_DOC in [010,011,012,999] |
| REGRA_VALIDA_NIVEL_AGL | NIVEL=1 deve ter IND_COD_AGL=T |
| REGRA_COD_AGL_IGUAL_COD_AGL_SUPERIOR | COD_AGL != COD_AGL_SUP |
| REGRA_CODIGO_AGL_NIVEL_SUPERIOR_INVALIDO | COD_AGL_SUP deve ser IND_COD_AGL=T |

### Exemplo de BP completo

```
|J100|1|T|1||A|Ativo|235000|D|276250|D||
|J100|1.1|T|2|1|A|Ativo Circulante|135000|D|182250|D||
|J100|1000|D|3|1.1|A|Bancos|135000|D|118750|D||
|J100|1001|D|3|1.1|A|Estoques|0|D|36500|D||
|J100|1002|D|3|1.1|A|ICMS a Recuperar|0|D|20000|D||
|J100|1.2|T|2|1|A|Ativo Nao Circulante|100000|D|94000|D||
|J100|1005|D|3|1.2|A|Imoveis|60000|D|60000|D||
|J100|1006|D|3|1.2|A|Veiculos|50000|D|50000|D||
|J100|1007|D|3|1.2|A|Depreciacao Acumulada|10000|C|16000|C||
|J100|2|T|1||P|Passivo|235000|C|276250|C||
|J100|2.1|T|2|2|P|Passivo Circulante|60000|C|76600|C||
|J100|2000|D|3|2.1|P|Arrendamento - Imoveis|75000|C|68750|C|001|
|J100|2.2|T|2|2|P|Patrimonio Liquido|175000|C|199650|C||
|J100|3000|D|3|2.2|P|Capital Integralizado|175000|C|190000|C||
```

---

## Registro J150
**Demonstracao do Resultado do Exercicio (DRE)**

**Hier** 3 · **Ocor** 1:N · **Pai** J005 · **Chave** [COD_AGL] · **PDF** p.180-185

So 1 linha NIVEL=1 (Resultado do Periodo / Lucro Liquido). Demais totalizadores: NIVEL>=2. Ordem visual definida pelo campo NU_ORDEM.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J150" |
| 02 | NU_ORDEM | N | 19 | - | S | ordem visualizacao |
| 03 | COD_AGL | C | - | - | N | codigo aglutinacao |
| 04 | IND_COD_AGL | C | 1 | - | S | T/D |
| 05 | NIVEL_AGL | N | - | - | S | nivel hierarquico |
| 06 | COD_AGL_SUP | C | - | - | N | codigo aglutinacao superior |
| 07 | DESCR_COD_AGL | C | - | - | S | descricao |
| 08 | VL_CTA_INI | N | 19 | 2 | N | saldo do periodo IMEDIATAMENTE ANTERIOR |
| 09 | IND_DC_CTA_INI | C | 1 | - | N | D/C anterior |
| 10 | VL_CTA_FIN | N | 19 | 2 | S | valor final antes encerramento |
| 11 | IND_DC_CTA_FIN | C | 1 | - | S | D/C final |
| 12 | IND_GRP_DRE | C | 1 | - | S | D-Despesa (reduz lucro), R-Receita (incrementa lucro) |
| 13 | NOTA_EXP_REF | C | 12 | - | N | nota explicativa |

### Regras Criticas

| Regra | O que verifica |
|-------|----------------|
| REGRA_SOMA_NIVEIS_DRE | Linhas T: VL_CTA_FIN = soma das filhas com mesmo COD_AGL_SUP (considerando D/C) |
| **REGRA_VALIDA_SALDO_COM_DRE** | Linhas D: VL_CTA_FIN = soma I355 calculada via COD_AGL no I052 |
| REGRA_COD_AGL_DUPLICIDADE | COD_AGL unico |
| REGRA_OBRIGATORIO_I052 | Se IND_COD_AGL=D, deve existir I052 com mesmo COD_AGL apontando conta I050.IND_CTA=A |
| REGRA_OBRIGATORIO_I052_MESMO_GRUPO | I050.COD_NAT=04 (resultado) para contas no J150 |
| **REGRA_VALIDA_SALDO_INI_DRE** | Se ID_DEM=1, periodo dentro ECD: VL_CTA_INI = C650.VL_CTA_FIN (DRE anterior recuperada via mesmo COD_AGL) |
| REGRA_NU_ORDEM_DUPLICADO | NU_ORDEM unico |
| REGRA_NIVEL_1_INEXISTENTE / REGRA_OCO_UNICA_NIVEL_1 | Existe **exatamente 1** linha NIVEL=1 |
| REGRA_EXISTE_NOTA_EXPLICATIVA | Se NOTA_EXP_REF preenchido, J800 com TIPO_DOC in [010,011,012,999] |
| REGRA_VALIDA_NIVEL_AGL | NIVEL=1 → IND_COD_AGL=T |

### Exemplo de DRE completa

```
|J150|16|4|T|1||Resultado do Periodo|20000|C|14650|C|R||
|J150|10|4.1|T|2|4|Lucro Bruto|30000|C|21900|C|R||
|J150|7|4.2|T|3|4.1|Receita Liquida|35000|C|58400|C|R||
|J150|1|4.3|T|4|4.2|Receita Bruta|40000|C|80000|C|R||
|J150|2|4000|D|5|4.3|Receita de Vendas|40000|C|80000|C|R||
|J150|3|4.4|T|4|4.2|Deducoes de Receita|5000|D|21600|D|D||
|J150|4|4001|D|5|4.4|ICMS Sobre Vendas|2000|D|16000|D|D||
|J150|11|4.6|T|2|4|Despesas Operacionais|10000|D|7250|D|D||
|J150|12|4006|D|3|4.6|Depreciacao|5000|D|1000|D|D||
```

---

## Registro J210
**DLPA / DMPL** (Demonstracao Lucros Acumulados / Mutacoes PL)

**Hier** 3 · **Ocor** 1:N · **Pai** J005 · **Chave** [COD_AGL] · **PDF** p.186-188

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J210" |
| 02 | IND_TIP | N | 1 | - | S | 0-DLPA, 1-DMPL |
| 03 | COD_AGL | C | - | - | S | codigo aglutinacao contas analiticas PL |
| 04 | DESCR_COD_AGL | C | - | - | S | descricao |
| 05 | VL_CTA_INI | N | 19 | 2 | S | saldo inicial periodo |
| 06 | IND_DC_CTA_INI | C | 1 | - | S | D/C inicial |
| 07 | VL_CTA_FIN | N | 19 | 2 | S | saldo final periodo |
| 08 | IND_DC_CTA_FIN | C | 1 | - | S | D/C final |
| 09 | NOTAS_EXP_REF | C | 12 | - | N | nota explicativa |

**Regras**:
- REGRA_EXISTE_DLPA_OU_DMPL: todos os J210 do mesmo J005 devem ter mesmo IND_TIP
- REGRA_UNICO_DLPA: se IND_TIP=0 (DLPA), so 1 J210 por J005 (aviso se >1)
- REGRA_VALIDA_DMPL_COM_SALDO_INI/FIN: se ID_DEM=1, VL_CTA_INI = soma I155.VL_SLD_INI para o COD_AGL (mesma data J005.DT_INI = I150.DT_INI). Idem para FIN
- REGRA_EXISTE_AGLUTINACAO_J210: COD_AGL deve existir em I052 com I050.IND_CTA=A
- REGRA_EXISTE_AGL_J210_MESMO_GRUPO: I050.COD_NAT=03 (PL) para a conta
- REGRA_VALIDA_TOT_AGLUTINACAO_J215: VL_CTA_FIN = soma J215.VL_FAT_CONT - VL_CTA_INI

---

## Registro J215
**Fato Contabil que Altera PL**

**Hier** 4 · **Ocor** 1:N · **Pai** J210 · **Chave** [COD_HIST_FAT] · **PDF** p.189

Fatos contabeis que alteram Lucros Acumulados / Prejuizos Acumulados / outras contas do PL. Ordem dos J215 = ordem de exibicao na DMPL. **Primeiro** J215 deve conter o saldo inicial do COD_AGL do J210 pai.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J215" |
| 02 | COD_HIST_FAT | C | - | - | S | codigo do historico do fato |
| 03 | DESC_FAT | C | - | - | S | descricao do fato |
| 04 | VL_FAT_CONT | N | 19 | 2 | S | valor do fato |
| 05 | IND_DC_FAT | C | 1 | - | S | D-Devedor, C-Credor, P-Subtotal positivo, N-Subtotal negativo |

**Exemplo**: `|J215|10|DISTRIBUICAO DO LUCRO DO PERIODO|1000,00|D|`

---

## Registro J800
**Outras Informacoes** (anexar arquivo RTF)

**Hier** 3 · **Ocor** 1:N · **Pai** J005 (?) · **PDF** p.190-191

Anexa arquivo RTF (max 30 MB) com notas explicativas, demonstracoes adicionais, pareceres, relatorios. Conteudo entre `|...|` e indicador final `J800FIM`.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J800" |
| 02 | TIPO_DOC | C | 3 | - | S | ver tabela abaixo |
| 03 | DESC_RTF | C | - | - | N | descricao do arquivo |
| 04 | HASH_RTF | C | 41 | - | N | hash (preenchido pelo PGE) |
| 05 | ARQ_RTF | C | 30MB | - | S | bytes do arquivo RTF |
| 06 | IND_FIM_RTF | C | 7 | - | S | "J800FIM" (fixo) |

### Tabela TIPO_DOC

| Cod | Descricao |
|-----|-----------|
| 001 | Demonstracao do Resultado Abrangente do Periodo |
| 002 | Demonstracao dos Fluxos de Caixa |
| 003 | Demonstracao do Valor Adicionado |
| 010 | Notas Explicativas |
| 011 | Relatorio da Administracao |
| 012 | Parecer dos Auditores |
| 099 | Outros |

---

## Registro J801
**Termo de Verificacao para Fins de Substituicao da ECD**

**Hier** 2 · **Ocor** 0:1 · **Chave** [REG] · **PDF** p.192-194 · **Obrig** F(8) — se 0000.IND_FIN_ESC=1 (Substituta)

Detalha erros que motivaram a substituicao da ECD. Conforme IN RFB 2.003/2021. Estrutura igual ao J800 mas com TIPO_DOC fixo (001) e COD_MOT_SUBS.

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J801" |
| 02 | TIPO_DOC | C | 3 | - | S | "001" (Termo Verificacao Substituicao) |
| 03 | DESC_RTF | C | - | - | N | descricao |
| 04 | COD_MOT_SUBS | C | 10 | - | S | ver tabela |
| 05 | HASH_RTF | C | 41 | - | N | hash |
| 06 | ARQ_RTF | C | 30MB | - | S | bytes RTF |
| 07 | IND_FIM_RTF | C | 7 | - | S | "J801FIM" |

### Tabela COD_MOT_SUBS

| Cod | Descricao |
|-----|-----------|
| 001 | Mudancas de saldos das contas que nao podem ser feitas por lancamentos extemporaneos |
| 002 | Alteracao de assinatura |
| 003 | Alteracao de demonstracoes contabeis |
| 004 | Alteracao da forma de escrituracao contabil |
| 005 | Alteracao do numero do livro |
| 099 | Outros |

**Conteudo do Termo deve incluir**:
I. Identificacao da escrituracao substituida
II. Descricao pormenorizada dos erros
III. Identificacao dos registros com erros
IV. Autorizacao para acesso do CFC
V. Procedimentos pre-acordados executados por auditores (se aplicavel)

**Assinantes obrigatorios** (no J932):
- Profissional da contabilidade que assina os livros substitutos (codigo 910)
- Auditor independente (codigo 920), se demonstracoes auditadas

**Prazo**: substituicao admitida ate fim do prazo de entrega do ano-calendario subsequente.

**Regra**: REGRA_REGISTRO_NAO_DEVE_EXISTIR_NO_RTF: ARQ_RTF nao pode conter tags C001, I001, J001, K001, J800, J801, J900

---

## Registro J900
**Termo de Encerramento**

**Hier** 2 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.195-196 · **Obrig** Sim

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J900" |
| 02 | DNRC_ENCER | C | 21 | - | S | "TERMO DE ENCERRAMENTO" (fixo) |
| 03 | NUM_ORD | N | - | - | S | numero ordem (= I030.NUM_ORD) |
| 04 | NAT_LIVRO | C | 80 | - | S | natureza do livro (= I030.NAT_LIVR) |
| 05 | NOME | C | - | - | S | nome empresarial (= 0000.NOME) |
| 06 | QTD_LIN | N | - | - | S | total linhas (= 9999.QTD_LIN) |
| 07 | DT_INI_ESCR | N | 8 | - | S | data inicio (= 0000.DT_INI) |
| 08 | DT_FIN_ESCR | N | 8 | - | S | data termino (= 0000.DT_FIN) |

**Regras**: todas comparam campos com 0000, I030 e 9999 — devem ser identicos.

**Exemplo**: `|J900|TERMO DE ENCERRAMENTO|100|DIARIO GERAL|EMPRESA TESTE|500|01012023|31012023|`

---

## Registro J930
**Signatarios da Escrituracao** (CRITICO)

**Hier** 3 · **Ocor** 1:N · **Chave** [IDENT_CPF_CNPJ]+[COD_ASSIN] · **PDF** p.197-202

### Regras de Assinatura (RESUMO CRITICO)

**Toda ECD ORIGINAL deve ter PELO MENOS 2 assinaturas**:
1. **Contador/Contabilista** (codigo 900) com e-PF ou e-CPF
2. **Responsavel pela assinatura da ECD** (IND_RESP_LEGAL=S) — pode ser:
   - **e-PJ ou e-CNPJ do declarante** (recomendado, codigo 001)
   - **e-PJ/e-CNPJ de terceiro** (procurador eletronico perante RFB)
   - **e-PF/e-CPF** (representante legal ou procurador, com qualquer codigo exceto 900)

**Regras**:
- O contador (codigo 900) **NUNCA pode ser** o responsavel pela assinatura
- Pode haver qualquer numero de assinaturas alem dessas 2
- Assinatura por e-PJ/e-CNPJ: nao obrigatoria, mas se feita so 1x (codigo 001)
- Certificados podem ser A1 ou A3

### Campos

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J930" |
| 02 | IDENT_NOM | C | - | - | S | nome do signatario |
| 03 | IDENT_CPF_CNPJ | C | 11/14 | - | S | CPF (11) ou CNPJ (14) |
| 04 | IDENT_QUALIF | C | - | - | S | qualificacao (ver tabela) |
| 05 | COD_ASSIN | C | 3 | - | S | codigo qualificacao (ver tabela) |
| 06 | IND_CRC | C | - | - | N | numero inscricao CRC (obrig se COD_ASSIN=900) |
| 07 | EMAIL | C | 60 | - | N | email (obrig se 900) |
| 08 | FONE | C | 14 | - | N | telefone (obrig se 900) |
| 09 | UF_CRC | C | 2 | - | N | UF do CRC (obrig se 900) |
| 10 | NUM_SEQ_CRC | C | - | - | N | formato UF/AAAA/NUMERO |
| 11 | DT_CRC | N | 8 | - | N | data validade CRC |
| 12 | IND_RESP_LEGAL | C | 1 | - | S | S-Responsavel pela assinatura, N-Nao |

### Tabela COD_ASSIN — Qualificacao do Assinante

| Cod | Descricao |
|-----|-----------|
| **001** | Pessoa Juridica (e-CNPJ ou e-PJ) |
| 203 | Diretor |
| 204 | Conselheiro de Administracao |
| 205 | Administrador |
| 206 | Administrador do Grupo |
| 207 | Administrador de Sociedade Filiada |
| 220 | Administrador Judicial - PF |
| 222 | Administrador Judicial - PJ - Profissional Responsavel |
| 223 | Administrador Judicial/Gestor |
| 226 | Gestor Judicial |
| 309 | Procurador |
| 312 | Inventariante |
| 313 | Liquidante |
| 315 | Interventor |
| 401 | Titular PF - EIRELI |
| 801 | Empresario |
| **900** | **Contador/Contabilista** (so e-PF/e-CPF, NUNCA responsavel) |
| 940 | Auditor Independente |
| 999 | Outros |

### Regras Criticas

- REGRA_OBRIGATORIO_ASSIN_CONTADOR: pelo menos 1 J930 com COD_ASSIN=900 e pelo menos 1 com COD_ASSIN!=900
- REGRA_OBRIGATORIO_UM_RESP_LEGAL: pelo menos 1 J930 com IND_RESP_LEGAL=S
- REGRA_QUALIF_INV_RESP_LEGAL: se IND_RESP_LEGAL=S, COD_ASSIN != 900
- REGRA_OBRIGATORIO_CONTADOR: se COD_ASSIN=900, campos IND_CRC + EMAIL + FONE + UF_CRC obrigatorios
- REGRA_VALIDA_FORMATO_SEQUENCIAL_CRC: NUM_SEQ_CRC formato UF/AAAA/NUMERO

**Exemplo**: `|J930|FULANO BELTRANO|12345678900|CONTADOR|900|1SP123456|fulano@gmail.com|2199999999|RJ|RJ/2012/001|31122023|S|`

---

## Registro J932
**Signatarios do Termo de Verificacao para Fins de Substituicao da ECD**

**Hier** 3 · **Ocor** 0:2 · **Chave** [IDENT_CPF_CNPJ_T]+[COD_ASSIN_T] · **PDF** p.203-205 · **Obrig** F(14) — se 0000.IND_FIN_ESC=1 (Substituta)

Campos: estrutura igual ao J930 com sufixo `_T` em cada campo. Tabela de qualificacao especifica.

### Tabela COD_ASSIN_T — Qualificacao do Assinante do Termo

| Cod | Descricao |
|-----|-----------|
| **910** | Contador/Contabilista Responsavel Pelo Termo de Verificacao (obrigatorio em qualquer ECD substituta) |
| **920** | Auditor Independente Responsavel pelo Termo de Verificacao (obrigatorio se auditada) |

### Regras

- REGRA_OBRIGATORIO_CONTADOR_ASS_TERMO: pelo menos 1 J932 com COD_ASSIN_T=910
- REGRA_QUALIF_INVALIDA_ASS_TERMO: se IDENT_CPF_CNPJ_T = CNPJ, COD_ASSIN_T deve ser 920
- REGRA_OBRIGATORIO_ASS_TERMO: campos CRC obrigatorios se COD_ASSIN_T=910

**Exemplo**: `|J932|FULANO|12345678900|CONTADOR/CONTABILISTA RESPONSAVEL...|910|1SP123456|fulano@gmail.com|2199999999|RJ|RJ/2012/001|31122023|`

---

## Registro J935
**Identificacao dos Auditores Independentes**

**Hier** 3 · **Ocor** 1:N · **Chave** [NI_CPF_CNPJ] · **PDF** p.206 · **Obrig** F(15) — se 0000.IND_GRANDE_PORTE=1

Identifica auditores independentes (auditoria obrigatoria para Ativo > R$240M ou Receita > R$300M).

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J935" |
| 02 | NI_CPF_CNPJ | C | 11/14 | - | S | CPF (PF) ou CNPJ (PJ de auditoria) |
| 03 | NOME_AUDITOR_FIRMA | C | - | - | S | nome do auditor ou firma |
| 04 | COD_CVM_AUDITOR | C | - | - | N | registro CVM (obrig se CPF) |

**Exemplo**: `|J935|12345678910|AUDITOR TESTE|1234567890|`

---

## Registro J990
**Encerramento do Bloco J**

**Hier** 1 · **Ocor** 1:1 · **Chave** [REG] · **PDF** p.207

| # | Campo | Tipo | Tam | Dec | Obrig | Valores |
|---|-------|------|-----|-----|-------|---------|
| 01 | REG | C | 4 | - | S | "J990" |
| 02 | QTD_LIN_J | N | - | - | S | total linhas Bloco J |

---

## Composicao dos Livros (Bloco J)

| Registro | G | R | A | B | Z |
|----------|---|---|---|---|---|
| J001 | O | O | O | O | O |
| J005 | F | F | N | F | N |
| J100 | F(5) | F(5) | N | F(5) | N |
| J150 | F(5) | F(5) | N | F(5) | N |
| J210 | F | F | N | F | N |
| J215 | F | F | N | F | N |
| J800 | F | F | N | F | N |
| J801 | F(8) | F(8) | F(8) | F(8) | F(8) |
| J900 | O | O | O | O | O |
| J930 | O | O | O | O | O |
| J932 | F(14) | F(14) | F(14) | F(14) | F(14) |
| J935 | F(15) | F(15) | F(15) | F(15) | F(15) |
| J990 | O | O | O | O | O |

---

## Notas Operacionais (Dev)

**Bug recorrente PVA — V22-V29 refactor**:
1. **J100/J150**: COD_AGL repetido entre I052 e linhas T do J100/J150 (REGRA_AGLUTINACAO_EM_SINTETICA)
2. **J100**: existem != 2 linhas NIVEL=1 (REGRA_EXISTEM_2_NIVEIS_1)
3. **J100**: VL_CTA_FIN das linhas D nao bate com soma I155 via I052 (REGRA_VALIDA_BALANCO_SALDO_FIN — **ERRO bloqueante**)
4. **J100/J150**: linha D sem registro I052 correspondente (REGRA_OBRIGATORIO_I052)
5. **J150**: existe != 1 linha NIVEL=1 (REGRA_OCO_UNICA_NIVEL_1)
6. **J150**: VL_CTA_FIN das linhas D nao bate com soma I355 via I052 (REGRA_VALIDA_SALDO_COM_DRE)
7. **J930**: contador (codigo 900) marcado como IND_RESP_LEGAL=S (REGRA_QUALIF_INV_RESP_LEGAL)
8. **J930**: sem nenhum signatario com IND_RESP_LEGAL=S (REGRA_OBRIGATORIO_UM_RESP_LEGAL)
9. **J930**: contador (900) sem CRC/UF_CRC (REGRA_OBRIGATORIO_CONTADOR)
10. **J900**: campos diferentes de I030/9999/0000 (varias REGRA_IGUAL_*)
11. **V1.7 (Nacom)**: contas de compensacao (COD_NAT=05 / code 5+) excluidas do BP — natureza propria

**Tabela contas natureza diferente e codigos iguais**: ver Cap 1.36 do manual original. Se a empresa usa o mesmo codigo para conta de naturezas diferentes em periodos diferentes, ECD aceita mas demonstracoes podem ter problemas.

**Conclusao da arquitetura J→I→I050**:
- J100/J150 (linha D, COD_AGL=X)
- → I052 (COD_AGL=X aponta para conta COD_CTA=Y, com I050.IND_CTA=A)
- → I050 (conta analitica COD_CTA=Y, COD_NAT compativel)
- → I155 ou I355 (saldos da conta COD_CTA=Y) — somados e conferidos

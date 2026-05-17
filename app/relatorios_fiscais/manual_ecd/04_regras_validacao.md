# Capitulo 4 — Regras de Validacao

> Paginas PDF 233-235 · Volta ao [INDEX](INDEX.md)

---

## Visao Geral do Mecanismo

O PGE executa validacoes em **3 blocos sequenciais**:
1. **Bloco 1** (Estrutura): roda primeiro. Se houver erros, **interrompe** e nao prossegue.
2. **Bloco 2** (Estrutura/Conteudo): so se bloco 1 passou.
3. **Bloco 3** (Regras de Negocio): so se bloco 2 passou.

**Consequencia pratica**: corrigir erros estruturais (faltando pipe, blocos em ordem errada, etc.) **pode revelar novos erros** que so aparecem depois.

### Validacoes adicionais durante transmissao

Alem das regras de validacao do arquivo, durante a transmissao o PGE verifica:

1. **Validade do certificado digital** (assinatura do livro + requerimento) — feito pelo Receitanet
2. **Repeticao de numero de livro** ja enviado (exceto substituidos e indeferidos)
3. **Sobreposicao de periodo** com outra ECD ja enviada
4. **Integridade da transmissao**

### Identificacao Unica de uma ECD

Para detectar duplicacao, sao considerados estes campos combinados:
1. CNPJ
2. Forma de Escrituracao Contabil (G/R/A/B/Z)
3. Numero do livro
4. Natureza do livro (somente se forma=A ou Z)

Se ja existe ECD com mesmos dados:
- Se a anterior esta **indeferida** + hash diferente → nao e duplicada (pode transmitir)
- Caso contrario → considera duplicada

### Identificacao Unica por Periodo

Para detectar sobreposicao, considera-se:
1. CNPJ
2. Forma de Escrituracao Contabil
3. Natureza do livro (somente se forma=A ou Z)

Se periodos sobrepostos, valida equivalencia de formas.

---

## Tipos de Inconsistencia

| Tipo | Comportamento |
|------|---------------|
| **Erro** | Impede execucao do PGE (so funcionalidade "Importacao/Validacao" roda) |
| **Aviso** | Nao impede execucao. Cabe a entidade avaliar se e ou nao um erro |

---

## 4.1. Regras de Validacao Nivel 1

### 4.1.1. Regras de Estrutura 1 (interrompem analise da linha)

| # | Regra | Descricao | Tipo |
|---|-------|-----------|------|
| 01 | **REGRA_HIERARQUIA_ARQUIVO** | Verifica se arquivo esta com organizacao hierarquica correta, conforme nivel definido em cada registro | Erro |
| 02 | **REGRA_ESTRUTURA_INVALIDA** | Registros iniciados na posicao 1, tamanho variavel. Toda linha termina com pipe `\|` + CRLF (caracteres 13 e 10 ASCII). Cada campo delimitado por pipe (inicio E fim). Campo vazio = `\|\|` (apenas pipes). Pipe `\|` NAO pode ser parte do conteudo de campos | Erro |
| 03 | **REGRA_REGISTRO_OBRIGATORIO** | Verifica se tipos obrigatorios estao presentes | Erro |
| 04 | **REGRA_REGISTRO_NAO_SE_APLICA** | Verifica se o tipo de registro aplica-se a escrituracao (G/R/A/B/Z) | Erro |

### 4.1.2. Regras de Estrutura 2 (nao interrompem analise da linha)

| # | Regra | Descricao | Tipo |
|---|-------|-----------|------|
| 01 | **REGRA_CAMPO_INVALIDO** | Verifica se campo foi preenchido com valores validos, tipo e tamanho corretos | Erro |
| 02 | **REGRA_CAMPOS_ADICIONAIS** | Campos adicionais (I020) nao sao validados estruturalmente, mas devem ser permitidos | — |
| 03 | **REGRA_TAMANHO_CAMPO_INVALIDO** | Verifica quantidade de caracteres conforme item "tamanho" da tabela do registro | Erro |
| 04 | **REGRA_VALORES_VALIDOS_INVALIDO** | Verifica se valor esta na lista "valores validos" do campo | Erro |
| 05 | **REGRA_TIPO_CAMPO_RAZAO_AUXILIAR** | Verifica se tipo informado no I510 (TIPO_CAMPO, DEC_CAMPO) corresponde aos valores do I550 | Erro |
| 06 | **REGRA_TAMANHO_ARQUIVO** | Tamanho arquivo < 1GB (na verdade < 5GB conforme cap. 1.11). Se maior, periodo deve ser apenas 1 mes | Erro |

---

## 4.2. Regras de Validacao Nivel 2

> "Os registros que apresentarem erro na validacao nivel 1 nao serao analisados na validacao nivel 2. Todas as regras de validacao de nivel 2 foram apresentadas nos proprios registros do leiaute."

Ou seja: as `REGRA_*` listadas em cada registro (Bloco 0, C, I, J, K, 9) sao todas regras de nivel 2.

---

## Convencoes Gerais (Cap 2.3 — Resumo)

> Repetido aqui por conveniencia. Detalhe completo em [02_dados_tecnicos.md](02_dados_tecnicos.md).

- **Formato**: arquivo texto ASCII ISO 8859-1 (Latin-1)
- **Tipos**:
  - **C** (Alfanumerico): qualquer caractere ASCII exceto pipe `|` e nao imprimiveis (0-31)
  - **N** (Numerico): digitos 0-9 + virgula como separador decimal
- **Tamanho**:
  - C com algarismo: tamanho exato
  - C com `-`: max 255 caracteres
  - C com `65536`: max 65.536 caracteres (excecao)
- **Casas decimais (N)**:
  - Com algarismo: max casas decimais
  - Com `-`: sem casas decimais
- **Datas**: `ddmmaaaa` (sem separadores). Ex: `01012023`
- **Periodos**: `mmaaaa`. Ex: `012023`
- **Numeros**: sem separadores de milhar, sem sinais, virgula opcional. Ex: `1234,56` ou `1234,5` ou `1234`
- **CNPJ**: 14 digitos sem formatacao. Ex: `11111111000199`
- **CPF**: 11 digitos. Ex: `88244044940`
- **CEP**: 8 digitos
- **Codigos com mascara** (documentos, processos): manter caracteres especiais. Ex: `98.765-43`, `2002/123456-78`

---

## Top Erros Mais Comuns (Resumo Pratico V22-V29)

| # | Erro | Causa | Solucao |
|---|------|-------|---------|
| 1 | I050 nivel < 4 em analitica patrimonial | Plano de contas raso | Adicionar niveis intermediarios sinteticos |
| 2 | I050 natureza filho != pai (nivel>2) | Inconsistencia hierarquica | Corrigir COD_NAT do filho ou pai |
| 3 | I052 COD_AGL duplicado em sintetica J100/J150 | Linhas T usaram codigo que esta no I052 | Renomear codigos das linhas T |
| 4 | I155 saldo final != saldo inicial mes seguinte | Continuidade quebrada | Recalcular saldos mensais sequencialmente |
| 5 | I155 soma debitos I250 != VL_DEB | Lancamentos faltando | Verificar todos os I250 do periodo |
| 6 | I355 existe sem I200 IND_LCTO=E | Falta lancamento de encerramento | Adicionar I200 com IND_LCTO=E |
| 7 | I250 HIST e COD_HIST_PAD ambos vazios | Falta historico | Preencher um dos dois |
| 8 | I150 mes faltando | Continuidade de saldos quebrada | Adicionar I150 para o mes ausente |
| 9 | I030 NAT_LIVR != J900.NAT_LIVRO | Termos inconsistentes | Igualar os nomes |
| 10 | I030 QTD_LIN != 9999.QTD_LIN | Contagem total errada | Recalcular total de linhas no final |
| 11 | J100 > 2 ou < 2 linhas NIVEL=1 | Estrutura BP errada | Garantir 1 linha A + 1 linha P em NIVEL=1 |
| 12 | J100/J150 linha D sem I052 | Mapeamento faltando | Adicionar I052 para a conta analitica |
| 13 | J100 VL_CTA_FIN != soma I155 via I052 | Aglutinacao errada | Verificar I052 que aponta para a aglutinacao |
| 14 | J930 contador (900) marcado como IND_RESP_LEGAL=S | Codigo 900 nao pode ser responsavel | Trocar para outro signatario |
| 15 | K030 existe mas IND_ESC_CONS != "S" | Bloco K indevido | Remover bloco K ou marcar IND_ESC_CONS=S |
| 16 | K100 sem CNPJ = 0000.CNPJ | A propria PJ deve estar no K100 | Adicionar K100 com CNPJ proprio |

---

## Glossario de Codigos de Regra

Padrao de nomes das regras (em portugues, maiusculo, com underscore):

- `REGRA_OCORRENCIA_UNITARIA_ARQ` — registro so 1x por arquivo
- `REGRA_OCORRENCIA_UNITARIA_<REG>` — registro so 1x por arquivo, especifico de tipo de registro (ex: I012)
- `REGRA_<CAMPO>_OBRIGATORIO` — campo deve ser preenchido
- `REGRA_VALIDA_<COISA>` — verifica formato/conteudo
- `REGRA_TABELA_<NOME>` — codigo deve existir em tabela
- `REGRA_<CAMPO>_DUPLICADO` / `REGRA_<CAMPO>_DUPLICIDADE` — chave unica
- `REGRA_REGISTRO_DUPLICADO` — registro nao pode aparecer 2x com mesma chave
- `REGRA_IGUAL_<CAMPO_X>_<REG_Y>` — campo X deste registro = campo do registro Y (cross-reference)
- `REGRA_VALIDACAO_<COISA>` — verificacao de regra de negocio (saldos, somas, etc.)
- `REGRA_*_MF` — variante para moeda funcional (se 0000.IDENT_MF=S)

---

## Como Interpretar Erros do PVA

Ao receber lista de erros do PVA, classificar:

1. **Erro estrutural** (Nivel 1): formato, hierarquia, tamanho, pipe. Resolver primeiro.
2. **Erro de campo**: tipo errado, valor invalido, tamanho excedido. Resolver depois.
3. **Erro de regra de negocio** (Nivel 2): consistencia entre registros. Resolver por ultimo, pois geralmente sao consequencia dos anteriores.

Ordem de correcao: 1 → 2 → 3. Apos corrigir nivel 1, executar PVA novamente — novos erros podem aparecer.

**Estrategia para arquivos grandes**: ao inves de fazer 1 PVA por correcao, agrupar correcoes do mesmo nivel e rodar PVA depois. O ground truth da SPED da contadora em `Downloads/` deve ser usado para validar saidas — nunca reler PDF inteiro.

# Opcao 485 — Cadastro de Transportadoras

> **Modulo**: Financeiro
> **Paginas de ajuda**: 6 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Cadastro central de transportadoras subcontratantes e parceiras para geracao de CTRCs em lote a partir de Manifestos, integracao EDI/XML, aprovacao de tabelas de comissionamento e configuracao de integracoes especificas (ex: Azul Cargo).

## Quando Usar
- Cadastrar transportadora subcontratante que usa SSW
- Cadastrar transportadora parceira (redespacho, agenciamento)
- Gerar CTRCs em lote a partir de Manifesto de transportadora SSW (opcao 006)
- Aprovar tabela de comissionamento de subcontratante (opcao 508)
- Configurar integracao com transportadora especifica (ex: Azul Cargo)
- Consultar transportadoras cadastradas (opcao 012)
- Gerar planilha de transportadoras (opcao 928)

## Pre-requisitos
- CNPJ da transportadora
- Dados cadastrais completos (razao social, endereco, telefone, email)
- Sigla unica para identificacao
- Tabela de comissionamento (se subcontratacao - opcao 408)

## Campos / Interface

### Identificacao
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ | Sim | CNPJ da transportadora |
| Sigla | Sim | Sigla unica para identificacao (usada em Manifestos) |
| Razao Social | Sim | Nome da transportadora |
| Nome Fantasia | Nao | Nome comercial |
| Inscricao Estadual | Condicional | Obrigatorio se contribuinte |

### Endereco
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Endereco | Sim | Rua, numero, complemento |
| Bairro | Sim | Bairro |
| Cidade | Sim | Cidade |
| UF | Sim | Estado |
| CEP | Sim | CEP |

### Contato
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Telefone | Nao | Telefone de contato |
| Email | Nao | Email para envio de extratos e CTRBs |

## Fluxo de Uso

### Cadastrar Transportadora Subcontratante
1. Acessar opcao 485
2. Informar CNPJ
3. Preencher dados cadastrais (razao social, endereco, telefone, email)
4. Definir sigla unica (usada em Manifestos)
5. Gravar cadastro
6. Cadastrar tabela de comissionamento (opcao 408)
7. Aguardar aprovacao da tabela pela subcontratada (opcao 508)

### Gerar CTRCs em Lote a partir de Manifesto (Opcao 006)
1. Transportadora subcontratante (que usa SSW) gera Manifesto
2. Acessar opcao 006
3. Informar sigla da transportadora subcontratante (opcao 485)
4. Informar codigo de barras do Manifesto (DAMDFE ou Manifesto Convencional) OU numero do Manifesto (serie + numero com DV)
5. Informar dados do CTRC a ser gerado:
   - Placa do veiculo de coleta (opcao 026) ou placa ficticia ARMAZEM
   - Codigo da mercadoria (opcao 406)
   - Codigo da especie (opcao 407)
   - Conferente (opcao 111 - se controle ativo)
   - CNPJ pagador
   - Valor do frete (se Subcontrato de Transferencia)
   - CNPJ recebedor OU sigla transportadora de redespacho
6. Clicar em "GERAR"
7. Sistema gera CTRC unico correspondente a todos os CTRCs do Manifesto

### Aprovar Tabela de Comissionamento (Opcao 508)
1. Subcontratante cadastra tabela pela opcao 408
2. Subcontratada acessa opcao 508
3. Informar CNPJ da transportadora subcontratante (opcao 485)
4. Visualizar tabelas cadastradas
5. Clicar em "Cod Tabela" para visualizar detalhes
6. Clicar em "Aprovar" para ativar tabela
7. Sistema fornece senha para subcontratante fazer alteracoes

### Consultar Transportadoras Cadastradas (Opcao 012)
1. Acessar opcao 012
2. Informar sigla (cadastrada na opcao 485) OU parte do nome
3. Visualizar relacao de transportadoras

### Gerar Planilha de Transportadoras (Opcao 928)
1. Acessar opcao 928
2. Clicar no botao de gerar
3. Aguardar processamento
4. Acessar opcao 156 (Ver Fila) para visualizar relatorio

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 006 | Geracao de CTRCs em lotes - usa sigla da transportadora e numero do Manifesto |
| 012 | Relacao de transportadoras - consulta cadastros |
| 026 | Cadastro de veiculos - placa usada em geracao de CTRCs |
| 111 | Cadastro de conferentes - usado em geracao de CTRCs (se controle ativo) |
| 388 | Configuracao de recebedor - define exigencia de dados do recebedor |
| 398 | SSWScan - comprovacao de entrega |
| 402 | Atendimento de cidade - verificacao baseada em cidade/UF do recebedor |
| 406 | Tipo de mercadoria - codigo usado em geracao de CTRCs |
| 407 | Especie de mercadoria - codigo usado em geracao de CTRCs |
| 408 | Tabela de comissionamento - cadastrada pela subcontratante |
| 423 | Fator de cubagem - usado em integracoes especificas (ex: Azul) |
| 508 | Aprovacao de tabelas - subcontratada aprova tabela da subcontratante |
| 600 | Importacao de XMLs - usado em integracoes EDI |
| 903 | Configuracoes - controle de conferentes |
| 925 | Permissoes de usuario - permissao para informar frete |
| 928 | Gerar planilha de transportadoras - exporta cadastros |

## Observacoes e Gotchas

### Sigla da Transportadora
- Unica por transportadora
- Usada em geracao de CTRCs em lote (opcao 006)
- Identifica unidade emissora em Manifestos
- Formato: normalmente 3-5 caracteres (ex: ABC, XPTO, MTZ)

### Manifesto de Transportadora SSW
- Gerado por transportadora subcontratante que tambem usa SSW
- Codigo de barras reconhecido: DAMDFE ou Manifesto Convencional
- Alternativamente: serie (sigla da unidade) + numero com DV
- Gera CTRC unico correspondente a todos os CTRCs do Manifesto

### Tipos de Documento Gerados
- **Redespacho**: CNPJ recebedor informado
- **Redespacho Intermediario**: sigla de transportadora de redespacho informada (altera automaticamente tipo)
- **Subcontrato de Transferencia (tipo T)**: valor do frete informado (requer permissao - opcao 925)

### Placa de Veiculo de Coleta
- **Placa real (opcao 026)**: define cidade/UF do veiculo como origem da prestacao
- **Placa ficticia ARMAZEM**: define cidade/UF da unidade emissora como origem da prestacao
- Placa ARMAZEM influencia:
  - Questoes fiscais
  - Calculo do frete (parcela coleta e TRT)
  - Apuracao de producao e resultado do veiculo da frota
  - Remuneracao de veiculos de coleta

### Recebedor
- **CNPJ recebedor**: aquele que deve receber a carga (Ajuste SINIEF 09/2007)
- **Destino (termino) da prestacao**: cidade/UF do recebedor
- Influencia:
  - Definicao da aliquota de ICMS
  - Calculo do frete
  - Verificacao de atendimento da cidade (opcao 402)

### Tabela de Comissionamento
- Cadastrada pela subcontratante (opcao 408)
- Aprovada pela subcontratada (opcao 508)
- Aprovacao fornece senha para subcontratante fazer alteracoes
- Necessaria para calculo de Subcontratos

### Integracao Azul Cargo (ssw3027 / ssw3071)
- **CNPJ raiz**: 09296295
- **Cadastro**: opcao 485
- **Endpoint SSW**: https://ssw.inf.br/api/notfisAzu
- **Token de autenticacao**: fixo e individual por transportadora (definido pelo SSW)
- **Particularidades**:
  - Numero da NF = numero da AWB com serie OUT
  - CNPJ remetente, expedidor e pagador = empresaemissora
  - Volume (m3) = pesocubado / Fator de Cubagem (opcao 423)
  - Codigo consolidador: NFs incluidas apenas em CT-e Redespacho Transferencia (H)
- **Tipos de emissao**:
  - **AWB** (entrega normal): opcao 006 - Subcontrato Recepcao (tipo 3), agrupa por N
  - **BAG** (unitizado, entrega em unidade do cliente): opcao 006 - Redespacho (tipo H), agrupa por E
- **Ocorrencias e baixas**:
  - Duas comprovacoes obrigatorias: foto local de entrega + foto DACTE assinado
  - Ambas com ocorrencia de entrega 01
  - SSWMobile, opcao 038 ou SSWScan (opcao 398)
  - Opcao 388 configurada com "Exige dados do recebedor = S"
  - Primeira ocorrencia = codigo SSW 01
  - Segunda ocorrencia = codigo SSW 19
  - SSW aguarda 7 dias para segunda comprovacao antes de enviar a Azul
- **Redespacho Intermediario**:
  - EDI 3123 disponibilizada (opcao 600)
  - XMLs de AWBs importados pela opcao 600 (CNPJ pagador, expedidor, recebedor)
  - CT-e gerado pela opcao 006 - G (Redespacho Intermediario)

### Tipo de Mercadoria (Opcao 406)
- Define tabela de frete a ser usada no calculo
- Criterio de definicao da tabela

### Especie de Mercadoria (Opcao 407)
- Define criterios de gerenciamento de risco
- Gestao de transporte de produtos controlados

### Conferente (Opcao 111)
- Habilitado apenas se controle de conferentes ativo (opcao 903)
- Informa quem efetuou descarga do veiculo de coleta

### Consulta e Exportacao
- **Opcao 012**: consulta por sigla ou nome (busca parcial)
- **Opcao 928**: gera planilha CSV de todas as transportadoras
- Resultado da opcao 928 visualizado na opcao 156 (fila de processamento)

### Multiempresa
- Se configuracao multi-empresa ativada (opcao 401), transportadoras podem ser separadas por empresa
- Integracao e geracao de CTRCs respeitam empresa configurada

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A05](../pops/POP-A05-cadastrar-fornecedor.md) | Cadastrar fornecedor |
| [POP-A06](../pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos comissoes |
| [POP-A10](../pops/POP-A10-implantar-nova-rota.md) | Implantar nova rota |

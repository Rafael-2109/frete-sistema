# Opcao 551 — Emissao de NF-e

> **Modulo**: Fiscal
> **Paginas de ajuda**: 2 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Efetua emissao e lancamento de NF-es para operacoes que nao geram ICMS ou que exigem documentacao especifica. Permite emitir NF-es de entrada (recebimento, compra) e saida (transferencia, venda de ativos, devolucao). Faturamento de NF-es emitidas pela opcao 551 e feito via opcao 547.

**IMPORTANTE**: O uso fiscalmente correto desta opcao e responsabilidade da transportadora. Digitador deve possuir conhecimentos fiscais sobre emissao de NF-e.

## Quando Usar

### Entradas
- **NF-e emitida por terceiro**: retorno de equipamento de conserto, recebimento de equipamento para teste (operacoes que NAO sao compras)
- **NF-e emitida pela transportadora**: remetente nao e emitente (ex: compra de caminhao de pessoa fisica)

### Saidas
- **Dar saida de bens**: envio de equipamento para conserto, transferencia de bem para outra unidade, venda de ativos, devolucao de mercadorias
- **Venda parcelada de ativos**: CFOP 5551/6551, faturamento via opcao 547, parcelamento via opcao 572, contabilizacao sequencias 102 e 105 (opcao 541)
- **NF-e complementar**: complementa NF-e de saida emitida anteriormente
- **Credito presumido PR**: CFOP 1.949, emitida no mes de apuracao

### Cobrar Servicos
- **NF-e CFOP 5124**: servicos que fazem parte de industrializacao do cliente (imposto ICMS estadual, nao ISS), faturamento via opcao 547

## Pre-requisitos
- Conhecimentos fiscais sobre emissao de NF-e (CFOP, CST, NCM, bases de calculo)
- Fornecedores/destinatarios cadastrados (opcao 478)
- Configuracao de regime tributario (opcao 401)
- Inscricao Municipal (se emitir RPS)
- XML da NF-e do fornecedor (se importar dados)

## Campos / Interface

### Tela Inicial
| Funcao | Descricao |
|--------|-----------|
| **Entrada** | |
| Importar dados da NF-e | Traz XML do fornecedor para facilitar inclusao |
| Incluir NF-e | Inclui NF-e emitida por fornecedor (preencher conforme documento) |
| Emitir NF-e | Transportadora emite NF-e de entrada |
| **Saida** | |
| Emitir NF-e | Transportadora emite NF-e de saida (devolucao: basear em NF-e venda fornecedor) |
| Emitir NF-e complementar | Complementa NF-e emitida anteriormente (informar chave de acesso) |
| Emitir NF-e por arquivo | Gera NF-es via importacao CSV (layout especificado) |
| Incluir NF-e via XML | Importa NF-es emitidas fora do SSW (apenas escrituracao fiscal) |
| **Aprovar, alterar, cancelar** | |
| Aprovar NF-e | Envia ao SEFAZ para autorizacao e impressao DANFE |
| Alterar NF-e | Altera NF-e pendente |
| Cancelar/excluir NF-e | Cancela NF-e (ate 24h apos autorizacao) |
| **Consultar** | |
| Consultar NF-e | Consulta NF-es cadastradas |
| Relacao de NF-e | Relatorio por periodo (inclusao, emissao, entrada) |

### Tela 02 (Dados da NF-e)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CFOP | Sim | Codigo CFOP adequado (responsabilidade do contador) |
| CNPJ/CPF Destinatario | Sim | Deve estar cadastrado como fornecedor (opcao 478) |
| Valor Total Nota | Sim | Total produtos + IPI + ICMS ST |
| Quantidade Volumes | Nao | Quantidade de volumes |
| Peso Real | Nao | Peso real dos produtos |
| Base de calculo ICMS | Nao | Valor base calculo ICMS |
| Valor do ICMS | Nao | Valor total ICMS incidente |
| Valor ICMS desonerado | Nao | Apenas NF saida (Lucro Real, produtos com reducao/isencao) |
| Base calculo ICMS ST | Nao | Se houver substituicao tributaria |
| Valor do ICMS ST | Nao | Valor ICMS com substituicao tributaria |
| Base calculo ICMS monofasico | Nao | Se CST 61 informado |
| Valor ICMS monofasico | Nao | Se CST 61 informado |
| Base Calculo IBS/CBS | Nao | Base calculo IBS e CBS |
| Valor IBS Estadual | Nao | Valor total IBS Estadual |
| Valor CBS | Nao | Valor total CBS |
| Valor do IPI | Nao | Valor total IPI |
| Valor do Frete | Nao | Valor do frete |
| CNPJ Transportador | Nao | Deve estar cadastrado como fornecedor (opcao 478) |
| Conta contabil | Nao* | Para SPED PIS/COFINS (opcao 515) se nao-cumulativo |
| Chave(s) referenciadas | Nao | NF-e (devolucao) ou CT-e |

*Obrigatorio para entradas se regime nao-cumulativo

### Dados do Produto
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Codigo | Sim | Codigo do produto |
| Descricao | Sim | Descricao do produto |
| Valor Total | Sim | Preco unitario x Qtd - Desconto + Despesas acessorias |
| Desconto | Nao | Desconto financeiro |
| Despesas acessorias | Nao | Eventuais despesas repassadas |
| NCM/SH | Sim | Codigo 8 digitos (Nomenclatura Comum Mercosul) |
| GTIN | Nao | Codigo GS1 (Receita Federal) |
| Cod Beneficio fiscal | Nao | Codigo UF 8 digitos (Tabela ANP) |
| CST PIS/COFINS | Sim | Codigo Situacao Tributaria PIS/COFINS |
| Origem da mercadoria | Sim | Nacional ou estrangeira |
| CST ICMS | Sim | Codigo Situacao Tributaria ICMS |
| Percentual diferimento ICMS | Nao | Apenas NF saida (produtos com diferimento) |
| Valor ICMS diferido | Auto | Base x Percentual diferimento x Aliquota |
| CEST | Nao | Codigo substituicao tributaria (produtos sujeitos a ST) |
| CST IBS/CBS | Nao | Codigo Situacao Tributaria IBS/CBS |
| Classificacao Tributaria IBS/CBS | Nao | Codigo Classificacao IBS/CBS |
| Percentual reducao IBS/CBS | Nao | Se CST 200-Aliquota reduzida |
| Base Calculo IBS/CBS | Nao | Nao integram: ICMS, ISS, PIS, COFINS (LC 214/2025 art 12 §2º V) |
| Aliquota IBS Estadual | Nao | 0,1% (LC 214/2025) |
| Aliquota CBS | Nao | 0,9% (LC 214/2025) |
| CST IPI | Nao | Se produto tem incidencia IPI |
| Cod ANP | Nao | Codigo combustivel ANP (Tabela Portal NF-e) |
| Descricao cod ANP | Nao | Descricao codigo ANP |

## Fluxo de Uso

### Emitir NF-e de Entrada
1. Acessar opcao 551
2. Escolher funcao (Importar/Incluir/Emitir)
3. Se importar: carregar XML do fornecedor
4. Preencher dados da NF-e (CFOP, destinatario, valores, bases)
5. Informar conta contabil (se nao-cumulativo)
6. Cadastrar produtos (codigo, descricao, NCM, CSTs, valores)
7. Finalizar inclusao
8. Aprovar NF-e (envia ao SEFAZ)

### Emitir NF-e de Saida
1. Acessar opcao 551
2. Escolher "Emitir NF-e" (saida)
3. Preencher CFOP adequado (5124 para servicos, 5551/6551 para venda ativos, etc.)
4. Informar destinatario, valores, bases
5. Se devolucao: informar chave NF-e de venda do fornecedor
6. Cadastrar produtos
7. Finalizar e aprovar
8. Faturar via opcao 547 (se cobrar)
9. Parcelar via opcao 572 (se venda parcelada)

### ICMS Monofasico Combustiveis (RS)
1. Obter relacao de notas via opcao 433 (link ICMS Monofasico)
2. Emitir NF-e entrada CFOP 1.653, CST 90
3. NAO informar Base de Calculo ICMS
4. NAO informar Aliquota ICMS
5. Valor do ICMS = valor ICMS monofasico a creditar
6. Observacoes: "Credito fiscal adjudicado nos termos do Livro I, art. 31, I, 'a', nota 05 do RICMS"
7. Informar Cod ANP predominante + Descricao
8. Grupo UF origem: indImport=0, cUFOrig=43 (RS), pOrig=100

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 547 | Faturamento manual de DANFEs (NF-es da opcao 551) |
| 572 | Parcelamento de faturas (venda parcelada ativos) |
| 478 | Cadastro fornecedores/destinatarios |
| 515 | SPED PIS/COFINS (usa conta contabil) |
| 541 | Contabilizacao venda ativos (sequencias 102 e 105) |
| 433 | Relacao ICMS Monofasico (link para NF-e ajuste RS) |
| 401 | Multiempresas, regime tributario |

## Observacoes e Gotchas

### Responsabilidade Fiscal
- **Uso correto**: responsabilidade da transportadora
- **Conhecimento obrigatorio**: digitador deve saber informar CFOP, CST, NCM, bases de calculo, aliquotas
- **Contador**: escolha de CFOP deve ser validada pelo contador (erro pode causar problemas em arquivos fiscais)

### Cancelamento
- **Prazo**: ate 24h apos autorizacao
- Apos 24h, NAO e possivel cancelar

### Venda Parcelada de Ativos
- **CFOP**: 5551/6551 para venda de imobilizado
- **Fluxo completo**: opcao 551 (emissao) → opcao 547 (faturamento) → opcao 572 (parcelamento)
- **Contabilizacao**: sequencias 102 e 105 (opcao 541)
- **Exemplo**: venda parcelada de caminhoes para agregados

### ICMS Monofasico (RS)
- **NF-e ajuste obrigatoria**: para EFD reconhecer credito
- **CFOP**: 1.653 entrada, CST 90
- **Particularidade**: NAO informar base/aliquota ICMS, informar apenas valor (credito monofasico)
- **Observacoes obrigatorias**: texto especifico RICMS
- **Grupo UF origem**: dados fixos (RS, nacional, 100%)

### ICMS Monofasico (SC)
- **Diferenca SC**: NAO escritura credito no documento
- **Apropriacao**: via ajuste registro D197
- **Motivo**: evitar inconsistencia em cruzamento SEF/SC entre XML e SPED Fiscal

### IBS/CBS (LC 214/2025)
- **Base calculo**: NAO integram ICMS, ISS, PIS, COFINS (art 12, §2º, V)
- **Aliquotas fixas**: IBS Estadual 0,1%, CBS 0,9%

### Faturamento
- **Exclusivo**: NF-es da opcao 551 so podem ser faturadas pela opcao 547
- **Banco/carteira**: configurar na tela de faturamento (opcao 547)

### Importacao CSV
- Permite emissao em lote via arquivo CSV
- Layout especificado em documentacao especifica (link AQUI no sistema)

### Cadastro Previo
- Fornecedores/destinatarios DEVEM estar cadastrados (opcao 478) antes de emitir NF-e
- Transportador (se informado) tambem deve estar cadastrado como fornecedor

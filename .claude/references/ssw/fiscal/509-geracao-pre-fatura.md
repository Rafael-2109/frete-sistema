# Opcao 509 — Geracao de Pre-Fatura

> **Modulo**: Fiscal
> **Paginas de ajuda**: 2 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Gera pre-fatura no proprio SSW para facilitar o faturamento manual. Permite selecionar CTRCs por periodo, filtros de entrega, importacao de dados CSV e inclusao de adicionais. Pre-fatura sera utilizada posteriormente no faturamento manual (opcao 437).

## Quando Usar
- Faturamento manual que exige pre-autorizacao do cliente
- Necessidade de agrupar CTRCs antes de emitir fatura
- Importacao de relacao de CTRCs autorizados pelo cliente
- Inclusao de adicionais (creditos/debitos) na fatura

## Pre-requisitos
- Cliente configurado com "Tipo de faturamento = Manual" (opcao 384)
- CTRCs emitidos e autorizados pelo SEFAZ
- Multiempresas configurado (opcao 401) se aplicavel
- Adicionais cadastrados (opcao 442) se necessario incluir na pre-fatura

## Campos / Interface

### Tela Inicial
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Empresa | Sim* | Numero da empresa (se multiempresas - opcao 401) |
| CNPJ do cliente | Sim | Cliente pagador (pode ser transportadora subcontratante) |
| Pre-fatura | Nao | Numero da pre-fatura para alteracao |
| Arquivo (impressao) | Nao | F = formato fatura SSW, T = texto, E = Excel |

*Obrigatorio se multiempresas

### Tela Geracao
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ do cliente | Sim | Cliente pagador (deve ter faturamento = Manual na opcao 384) |
| Periodo de emissao | Nao* | Seleciona CTRCs por data de emissao |
| Periodo de autorizacao | Nao* | Seleciona CTRCs por data de autorizacao SEFAZ |
| Com Comprovantes de Entrega | Nao | S = apenas CTRCs com comprovantes recepcionados (opcao 428) |
| Adicionais disponiveis | Info | Exibe creditos/debitos disponiveis (opcao 442) |
| Numero da pre-fatura gerada | Auto | Gerado automaticamente |

*Informar um dos dois periodos

### Rodape (Metodos de Inclusao)
| Funcao | Descricao |
|--------|-----------|
| Digitar documentos | Digitar serie e numero CTRC (numero SSW) |
| Digitar CT-e | Digitar serie e numero da chave CT-e |
| Capturar cod barras DACTE | Capturar codigo de barras do DACTE |
| CTRC origem | Digitar serie e numero CTRC origem (transportadora subcontratante) |
| Apontar documentos | Selecionar CTRCs listados conforme filtros |
| Importar arq CSV | Importar dados de arquivo CSV (ver detalhes abaixo) |
| Apontar adicionais | Selecionar adicionais do periodo para inclusao |

### Importar CSV
| Campo | Descricao |
|-------|-----------|
| Tipo de dado | Nota Fiscal, Pedido, CTRC Origem, CTRC (com DV) ou CT-e |
| Coluna do dado | Numero da coluna no arquivo CSV |
| Linhas | Intervalo de linhas com dados |
| Local do arquivo | Caminho da pasta no computador |

## Fluxo de Uso
1. Acessar opcao 509
2. Informar CNPJ do cliente (deve ser faturamento manual)
3. Definir periodo (emissao OU autorizacao)
4. Opcionalmente filtrar por CTRCs com comprovante de entrega
5. Escolher metodo de inclusao:
   - **Apontar documentos**: marcar CTRCs listados
   - **Digitar**: informar serie/numero manualmente
   - **Importar CSV**: carregar arquivo com relacao de CTRCs
   - **Capturar barras**: usar leitor de codigo de barras
6. Apontar adicionais se necessario
7. Gerar pre-fatura (numero gerado automaticamente)
8. Imprimir pre-fatura se desejado (F/T/E)
9. Utilizar pre-fatura no faturamento manual (opcao 437)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 437 | Faturamento manual (usa pre-fatura gerada) |
| 384 | Configuracao cliente (Tipo de faturamento = Manual) |
| 401 | Multiempresas (define empresa emissora) |
| 442 | Adicionais (creditos/debitos) para inclusao na pre-fatura |
| 428 | Comprovantes de entrega (filtro opcional) |
| 004 | Emissao de CTRC (origem dos dados) |
| 565 | Recepcao pre-fatura Proceda 1.2 (arquivo de cliente) |
| 600 | Importacao layout especifico (se Proceda 1.2 nao atender) |

## Observacoes e Gotchas
- **Pre-requisito cliente**: cliente DEVE estar configurado como "Tipo de faturamento = Manual" (opcao 384), caso contrario nao e possivel gerar pre-fatura
- **Periodo**: usar periodo de emissao OU autorizacao (nao ambos)
- **Comprovantes de entrega**: filtro "S" seleciona apenas CTRCs com comprovante recepcionado via opcao 428
- **Adicionais**: valores de creditos/debitos cadastrados na opcao 442 podem ser incluidos na pre-fatura
- **Metodos de inclusao**: multiplas formas de adicionar CTRCs (digitacao, apontamento, importacao CSV, codigo de barras)
- **CSV flexivel**: importacao CSV permite configurar tipo de dado (NF, Pedido, CTRC Origem, CTRC, CT-e), coluna e linhas
- **CTRC origem**: usado quando transportadora e subcontratada (CTRC da contratante)
- **Numero automatico**: sistema gera numero da pre-fatura automaticamente
- **Impressao**: 3 formatos disponiveis (F = fatura SSW, T = texto, E = Excel)
- **Alteracao**: possivel alterar pre-fatura existente informando numero na tela inicial
- **Proceda 1.2**: se cliente envia arquivo Proceda 1.2, usar opcao 565 para recepcionar (opcao 600 para layouts especificos)

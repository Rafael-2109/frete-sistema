# Opcao 147 — Conferencia de Documentos

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Gera relacao de CTRCs e seus CTRCs Complementares de Romaneios e Manifestos, visando a obtencao do frete total da operacao. Permite exportar dados em arquivo CSV ou relatorio, considerando todos os documentos complementares vinculados.

## Quando Usar
- Conferir carga de um Manifesto ou Romaneio especifico via codigo de barras
- Obter frete total de uma operacao incluindo complementares
- Gerar planilha ou relatorio de CTRCs de um cliente em um periodo
- Enviar automaticamente por e-mail a relacao de documentos

## Pre-requisitos
- Manifestos FEC ou Romaneios emitidos no sistema
- CTRCs vinculados aos Manifestos/Romaneios
- Codigo de barras do Manifesto/Romaneio (para consulta unitaria)
- CNPJ do cliente (para relatorio por periodo)

## Campos / Interface

### Planilha (Consulta Unitaria)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cod. barras Manifesto/Romaneio | Sim (ou uma das alternativas) | Codigo de barras do Manifesto ou Romaneio operacional |
| OU Manifesto (com DV) | Sim (alternativa) | Sigla e numero do Manifesto |
| OU Romaneio (com DV) | Sim (alternativa) | Sigla e numero do Romaneio |
| E-mail | Nao | Se preenchido, a planilha CSV gerada e enviada automaticamente para este endereco |

### Relatorio (Consulta por Periodo)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ/raiz | Sim | CNPJ completo ou raiz (8 primeiros digitos) do cliente remetente, destinatario, pagador ou todos |
| Periodo emissao | Sim | Periodo de emissao dos Manifestos e Romaneios |
| Unidade origem (opc) | Nao | Unidade emissora dos Manifestos ou Romaneios (filtro opcional) |
| Listar em | Sim | T (texto) ou E (planilha Excel) |

## Fluxo de Uso

### Gerar Planilha CSV de um Manifesto/Romaneio
1. Acessar opcao 147
2. Informar codigo de barras do Manifesto/Romaneio OU sigla+numero
3. Opcionalmente, informar e-mail para envio automatico
4. Gerar arquivo CSV (relaciona CTRCs, complementares e primeira NF-e de cada CTRC)

### Gerar Relatorio por Cliente/Periodo
1. Acessar opcao 147
2. Informar CNPJ ou raiz do cliente
3. Definir periodo de emissao
4. Opcionalmente, filtrar por unidade origem
5. Escolher formato de saida (texto ou Excel)
6. Gerar relatorio (relaciona todos os CTRCs, complementares e todas as NF-es)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 181 | Conferencia de carga (versao anterior, opcao 147 e versao ajustada) |
| Manifestos FEC | Fonte de dados para conferencia |
| Romaneios | Fonte de dados para conferencia |
| CTRCs | Documentos principais relacionados |
| CTRCs Complementares | Documentos adicionais incluidos na conferencia |

## Observacoes e Gotchas
- **CTRCs Complementares**: A opcao 147 foi ajustada para considerar os CTRCs Complementares como parte integrante do Manifesto ou Romaneio
- **NF-e na Planilha**: Na exportacao CSV, apenas a primeira NF-e de cada CTRC e relacionada
- **NF-e no Relatorio**: No relatorio por periodo, todas as NF-es do CTRC sao relacionadas
- **Codigo de barras**: Aceita codigo de barras operacional do Manifesto/Romaneio
- **Envio automatico**: Ao preencher o campo de e-mail, a planilha e enviada sem necessidade de acao manual
- **Filtro por CNPJ**: O filtro aceita CNPJ completo ou apenas a raiz (8 digitos), podendo buscar por remetente, destinatario, pagador ou todos

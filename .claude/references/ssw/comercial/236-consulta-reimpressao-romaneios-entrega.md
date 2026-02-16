# Opcao 236 — Consulta e Reimpressao de Romaneios de Entrega

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Efetua consulta e reemissao de Romaneios de Entrega, permitindo localizacao por diversos filtros (numero do romaneio, codigo de barras, CIOT, MDF-e, periodo, placa, motorista) e visualizacao de detalhes, CTRCs vinculados e ocorrencias.

## Quando Usar
- Reimprimir romaneio de entrega para motorista
- Consultar CTRCs vinculados a um romaneio especifico
- Localizar romaneio atraves de CIOT ou MDF-e
- Verificar ocorrencias de um romaneio
- Gerar relatorio Excel de romaneios de um periodo

## Pre-requisitos
- Romaneio de entrega previamente emitido
- Para consulta por MDF-e: MDF-e emitido pela opcao 236

## Campos / Interface

### Tela Inicial (Filtros)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Romaneio (sigla e numero sem DV) | Condicional | Serie e numero do Romaneio de Entregas, sem digito verificador |
| Cod barras Romaneio | Condicional | Codigo de barras do Romaneio |
| CIOT | Condicional | Numero do CIOT para localizar romaneios vinculados |
| MDF-e | Condicional | Codigo de barras do MDF-e para localizar romaneio correspondente |
| EXCEL (Romaneios do periodo) | Nao | N=consulta em tela, S=relatorio em Excel |
| Unidade | Condicional | Unidade emissora dos romaneios desejados (para consulta por periodo) |
| Placa veiculo (opc) | Nao | Placa do veiculo para filtrar romaneios (opcional) |
| CPF motorista (opc) | Nao | CPF do motorista para filtrar romaneios (opcional) |

### Tela Principal (Detalhes)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| PDF | Nao | Botao para imprimir PDF do Romaneio de Entregas |
| CIOT | Nao | Botao para imprimir CIOT do Romaneio de Entregas |
| CTRCs do Romaneio | Nao | Link para relacionar os CTRCs vinculados ao romaneio |
| Ocorrencias | Nao | Mostra ocorrencias do romaneio e permite gravar nova ocorrencia |

## Fluxo de Uso

### Consulta por Romaneio Especifico
1. Informar serie e numero do romaneio (sem DV) OU codigo de barras
2. Visualizar detalhes na tela principal
3. Reimprimir PDF ou CIOT conforme necessario
4. Consultar CTRCs vinculados ou ocorrencias

### Consulta por CIOT ou MDF-e
1. Informar numero do CIOT ou codigo de barras do MDF-e
2. Sistema localiza romaneio(s) vinculado(s)
3. Visualizar detalhes e reimprimir conforme necessario

### Consulta por Periodo
1. Selecionar formato de saida (tela ou Excel)
2. Informar unidade emissora
3. Opcionalmente filtrar por placa de veiculo ou CPF de motorista
4. Gerar listagem de romaneios do periodo

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 236 | Emissao de MDF-e (mesmo numero de opcao — funcionalidade dual: consulta E emissao) |
| 038 | Emissao de Romaneio de Entrega (origem dos romaneios consultados) |

## Observacoes e Gotchas
- **Numero do romaneio SEM digito verificador**: ao informar serie e numero manualmente, NAO incluir o DV
- **Codigo de barras**: alternativa mais rapida e precisa para localizar romaneio (inclui validacao automatica)
- **CIOT pode vincular multiplos romaneios**: um CIOT pode estar associado a mais de um romaneio
- **MDF-e emitido pela opcao 236**: a mesma opcao que consulta/reimprimi romaneios tambem emite MDF-e
- **Arquivos de integracao**: arquivos XML/JSON de Vale Pedagio e CIOT ficam disponiveis nas ocorrencias do romaneio
- **Ocorrencias editaveis**: alem de visualizar, e possivel gravar novas ocorrencias no romaneio
- **Excel para analise massiva**: opcao de gerar Excel e util para analises gerenciais de romaneios por periodo/placa/motorista

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |

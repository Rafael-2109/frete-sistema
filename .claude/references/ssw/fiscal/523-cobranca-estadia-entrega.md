# Opcao 523 — Cobranca de Estadia na Entrega

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Permite emissao de CTRC complementar cobrando estadia ocorrida durante entrega no destinatario. Sistema calcula horas de estadia com base em data/hora de chegada e saida informadas.

## Quando Usar
- Veiculo ficou retido no destinatario aguardando descarga por tempo excessivo
- Necessidade de cobrar estadia na entrega conforme contrato
- Emissao de documento complementar (CTRC/Subcontrato ou RPS) para estadia

## Pre-requisitos
- CTRC original emitido e autorizado
- Informacao de data/hora de chegada e saida no destinatario
- Inscricao Municipal cadastrada (opcao 401) se for emitir RPS
- CTRC referencia NAO pode ser subcontrato se subcontratante usa SSW

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CTRC Referencia (com DV) | Sim | Numero do CTRC original que teve estadia na entrega |
| Horas de estadia em entregas | Info | Link abre opcao 523 para pesquisar CTRCs com possivel estadia |
| Tipo do documento | Sim* | C = CTRC/Subcontrato, R = RPS (campo aparece apenas em Reentrega) |
| Imprime na unidade | Sim | O = unidade origem do CTRC ref, D = unidade destino (se FEC, usa origem) |
| Data de chegada | Sim | Data em que veiculo chegou no destinatario |
| Hora/Minuto da chegada | Sim | Hora e minuto da chegada |
| Data de saida | Sim | Data em que veiculo finalizou entrega |
| Hora/Minuto da saida | Sim | Hora e minuto da saida |

*Obrigatorio apenas em Reentrega

## Fluxo de Uso
1. Acessar opcao 099 (cobranca de estadia na entrega)
2. Opcionalmente usar link "Horas de estadia em entregas" para pesquisar CTRCs candidatos (opcao 523)
3. Informar numero do CTRC referencia (com DV)
4. Se for Reentrega, escolher tipo de documento (C = CTRC/Subcontrato, R = RPS)
5. Escolher unidade emissora (O = origem, D = destino)
6. Informar data e hora de chegada no destinatario
7. Informar data e hora de saida do destinatario
8. Sistema calcula horas de estadia e emite documento complementar

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 099 | Emissao de estadia na entrega (opcao atual) |
| 523 | Pesquisa CTRCs com horas de estadia (link na tela) |
| 401 | Cadastro de unidades (Inscricao Municipal para RPS) |
| 004 | Emissao CTRC/Subcontrato (novo subcontrato se subcontratante usa SSW) |

## Observacoes e Gotchas
- **RPS requer Inscricao Municipal**: so permite emissao de RPS se unidade origem OU destino tiver Inscricao Municipal cadastrada (opcao 401)
- **Subcontrato x SSW**: NAO e permitido emitir subcontrato complementar se subcontratante usa SSW. Neste caso, subcontratante deve emitir CTRC cobrando estadia, e transportadora emite novo subcontrato de recepcao (opcao 004)
- **Unidade emissora**: escolher entre origem (O) ou destino (D) do CTRC referencia
  - Se CTRC referencia for carga fechada (destino FEC), unidade emissora sera sempre origem
- **Pesquisa facilitada**: link "Horas de estadia em entregas" abre opcao 523 para pesquisar CTRCs que podem ter cobranca de estadia
- **Tipo de documento**: campo "Tipo do documento" aparece APENAS em emissao de Reentrega (C = CTRC/Subcontrato, R = RPS)
- **Calculo automatico**: sistema calcula horas de estadia baseado em data/hora chegada vs data/hora saida
- **Tutorial completo**: consultar tutorial "Controle de dificuldade de entrega" para informacoes detalhadas

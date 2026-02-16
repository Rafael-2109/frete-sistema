# Opcao 510 — Pre-Entregas do Parceiro

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Registra entregas confirmadas por parceiros/agencias antes da recepcao dos comprovantes assinados. Permite informar data de entrega antecipadamente para evitar problemas com clientes que exigem comprovacao rapida.

## Quando Usar
- Parceiro confirma entrega mas nao enviou comprovante assinado ainda
- Cliente exige comprovacao de entrega antes do comprovante fisico/digitalizado chegar
- Necessidade de atualizar performance de entregas com informacoes do parceiro
- Geracao de arquivos EDI de ocorrencias com pre-entregas

## Pre-requisitos
- Unidade destino (agencia/parceiro) cadastrada
- CTRCs/Subcontratos pendentes de entrega
- Ocorrencia tipo PRE-ENTREGA cadastrada (geralmente codigo 02)
- Confirmacao de entrega pelo parceiro

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Unidade destino | Sim | Agencia/parceiro responsavel pelas entregas |
| Periodo de emissao | Nao* | Filtro por data de emissao do CTRC |
| OU Previsao de entrega | Nao* | Filtro por data de previsao de entrega |
| Remetente | Nao | Filtro opcional por remetente |
| Codigo da ocorrencia | Sim | Ocorrencia tipo PRE-ENTREGA (geralmente 02) |
| Enviar relatorio por e-mail | Nao | Envia ao parceiro relacao de fretes pendentes para ele informar datas |

*Informar um dos dois periodos

### Relacao dos Fretes
| Campo | Descricao |
|-------|-----------|
| Lista de CTRCs/Subcontratos | CTRCs/Subcontratos pendentes conforme filtros |
| Data da entrega | Informar data indicada pelo parceiro |
| Numero do documento (link) | Clique abre consulta detalhada (opcao 101) |

## Fluxo de Uso
1. Acessar opcao 510
2. Selecionar unidade destino (agencia/parceiro)
3. Definir periodo (emissao OU previsao de entrega)
4. Opcionalmente filtrar por remetente
5. Informar codigo da ocorrencia PRE-ENTREGA (geralmente 02)
6. Opcionalmente enviar relatorio por e-mail ao parceiro
7. Na lista de fretes pendentes, informar data da entrega para cada CTRC/Subcontrato
8. Clicar no numero do documento para consultar detalhes se necessario (opcao 101)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 106 | Performance de Entregas (considera pre-entregas como sucesso) |
| 908 | Configuracao cliente EDI (define se pre-entregas entram no arquivo) |
| 101 | Consulta detalhada do CTRC (link na listagem) |

## Observacoes e Gotchas
- **Problema de atraso**: parceiros podem atrasar envio de comprovantes assinados, causando problemas com clientes que exigem devolvucao ou copias digitalizadas
- **Pre-entrega provisoria**: pre-entrega e um registro provisorio ate que comprovante assinado seja recepcionado
- **Performance de entregas**: opcao 106 considera pre-entregas como entrega bem-sucedida
- **EDI de ocorrencias**: arquivos EDI podem considerar pre-entregas como entrega, se configurado na tabela do cliente (opcao 908)
- **Ocorrencia padrao**: geralmente usa codigo 02 para ocorrencia tipo PRE-ENTREGA
- **E-mail ao parceiro**: funcao de envio de relatorio facilita coleta de informacoes — parceiro devolve relatorio com datas
- **Consulta rapida**: clicar no numero do documento na lista abre consulta detalhada (opcao 101)
- **Filtros combinados**: pode usar periodo de emissao OU previsao de entrega + filtro opcional de remetente

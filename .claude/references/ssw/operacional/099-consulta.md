# Opção 099 — Cobrança de Estadia na Entrega

> **Módulo**: Operacional — Cobrança de Serviços Adicionais
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Emite CTRC Complementar para cobrar estadia na entrega, calculada pelo tempo que motorista aguarda no cliente recebedor.

## Quando Usar
- Cobrar estadia quando motorista aguarda no cliente para realizar entrega
- Emitir CTRC Complementar automaticamente após informar ocorrência de entrega
- Automatizar cobrança via SSWMobile com chegada manual ou automática

## Pré-requisitos
- **Configurações gerais**:
  - Opção 903/Operação: Controle de Estadias = S
  - Opção 405: Ocorrências que pagam estadia configuradas
  - Opção 423: Tabelas de cálculo de valores de estadia
- **Para automatização via SSWMobile**:
  - Opção 903/Operação: SSWMobile/satélite executa saída e chegada automática = S
  - Opção 388/Chegada neste cliente = S (para chegada automática)

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| DACTE referência | Sim | CTRC para cobrança de estadia (não pode ser subcontrato) |
| CTRC referência (com DV) | Sim | Número do CTRC com DV |
| Data/hora chegada | Sim | Data e hora de chegada no cliente |
| Data/hora saída | Sim | Data e hora de saída do cliente |
| Horas de Estadia em Entregas | Não | Link traz opção 523 para localizar CTRCs com possibilidades de cobrança |

## Formas de Cobrança
| Forma | Descrição |
|-------|-----------|
| Emissão direta | Opção 099 — informa manualmente horas de chegada e saída |
| Ocorrência manual | Opção 038 — informa ocorrência de entrega com horas de chegada/saída |
| SSWMobile botão manual | Motorista informa ocorrência SSW 07-Chegada no Cliente via botão Ocorrências |
| SSWMobile automático | Sistema identifica chegada SSW 07 por coordenadas geográficas (raio configurado) |

## Cálculo da Estadia
- **Período**: Entre ocorrência SSW 07-Chegada no Cliente e próxima ocorrência que paga estadia
- **Valor**: Calculado com base na tabela opção 423
- **Emissão**: CTRC Complementar gerado automaticamente quando ocorrência que paga estadia é identificada

## Chegada Automática SSWMobile
1. SSWMobile monitora localização do motorista
2. Sistema verifica se 3 coordenadas geográficas estão dentro do raio de entrega (opção 903/Operação)
3. Sistema registra automaticamente ocorrência SSW 07-Chegada no Cliente
4. Motorista realiza entrega
5. Motorista informa ocorrência que paga estadia
6. Sistema calcula período entre chegada e ocorrência
7. CTRC Complementar gerado automaticamente

## Agendamento de Carregamento
Carregamento pode ocorrer antes da data de agendamento sem alerta nas situações:
- Após 18:00h do dia anterior à entrega agendada
- Após 18:00h da sexta-feira para segunda-feira
- Sábados e domingos para segunda-feira

## Fluxo de Uso — Manual
1. Motorista chega no cliente para entrega
2. Aguarda tempo para realizar entrega
3. Realiza entrega e sai do cliente
4. Usuário acessa opção 099
5. Informa CTRC referência
6. Informa data/hora chegada e data/hora saída
7. Sistema calcula estadia com base na tabela (opção 423)
8. CTRC Complementar emitido (CT-e ou RPS conforme configuração)

## Fluxo de Uso — Automático
1. SSWMobile identifica chegada no cliente (manual ou automático)
2. Registra ocorrência SSW 07-Chegada no Cliente
3. Motorista realiza entrega
4. Motorista informa ocorrência que paga estadia (opção 405)
5. Sistema calcula período entre SSW 07 e ocorrência
6. CTRC Complementar gerado automaticamente (opção 099)

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 038 | Ocorrências de entrega — informa manualmente horas chegada/saída |
| SSWMobile | Chegada manual (botão Ocorrências) ou automática (coordenadas) |
| 903 | Configuração: Controle de Estadias, raio de chegada automática |
| 405 | Cadastro de ocorrências que pagam estadia |
| 423 | Tabelas de cálculo de valores de estadia |
| 388 | Configuração: Chegada neste cliente = S (automática) |
| 523 | Horas de Estadia em Entregas — localiza CTRCs com possibilidades |
| 401 | Inscrição Municipal necessária para emitir RPS |
| 004 | Subcontrato de expedição/recepção para cobrar estadia de subcontratado |
| 056 | Relatório 130 — estadias não cobradas |

## Tipos de Documento
- **CTRC Complementar**: Padrão para cobrança de estadia
- **RPS**: Somente se unidade possui Inscrição Municipal (opção 401)

## Observações e Gotchas
- **Subcontrato com estadia**: Subcontratante deve emitir primeiro CTRC Complementar, depois subcontratada emite subcontrato de expedição/recepção (opção 004)
- **Cálculo automático**: Sistema calcula valor com base na tabela opção 423
- **Chegada automática**: Exige 3 coordenadas geográficas dentro do raio configurado (opção 903/Operação)
- **Raio de entrega**: Configurado por cliente na opção 388
- **Ocorrência SSW 07**: Obrigatória para cálculo de estadia
- **Estadias não cobradas**: Relatórios opção 056/130 e opção 523 mostram estadias pendentes
- **RPS**: Requer Inscrição Municipal cadastrada na opção 401
- **Horários flexíveis**: Carregamento pode ocorrer antes do agendamento em horários específicos
- **CTRC referência**: Não pode ser subcontrato, somente CTRC normal

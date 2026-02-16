# Opção 091 — Controle de CTRCs Segregados

> **Módulo**: Operacional — Controle de Segregação
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Coloca e retira CTRCs em área de segregação enquanto pendências estão sendo resolvidas, impedindo manifestação, romaneamento ou conferência de volumes.

## Quando Usar
- Segregar CTRC com pendência a ser resolvida
- Retirar CTRC da segregação após resolução de pendência
- Consultar CTRCs segregados na unidade

## Pré-requisitos
- CTRC não pode estar em trânsito (manifestado ou romaneado)

## Formas de Segregação
### Segregação do CTRC
- **Opção 091**: Controle de CTRCs segregados
- **Opção 033**: Ocorrências de Transferência
- **Opção 101**: Consulta de CTRC
- **Opção 108**: Instruções para Ocorrências

### Segregação dos Volumes (com código de barras)
- **Opção 291**: Segregar capturando código de barras de todos os volumes do CTRC

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CTRC (com DV) | Sim | Número do CTRC para incluir/retirar da segregação |
| Relacionar segregados | Não | Relaciona CTRCs segregados neste momento |

## Restrições de CTRCs Segregados
- **NÃO podem ser**:
  - Manifestados (opção 020)
  - Romaneados (opção 035)
  - Ter volumes conferidos pelo SSWBar
- **NÃO podem ser segregados**:
  - CTRCs em trânsito (manifestados ou romaneados)

## Fluxo de Uso
### Incluir na Segregação
1. Identificar CTRC com pendência a ser resolvida
2. Acessar opção 091
3. Informar número do CTRC (com DV)
4. Sistema inclui CTRC na área de segregação
5. CTRC não pode mais ser manifestado, romaneado ou conferido

### Retirar da Segregação
1. Pendência resolvida
2. Acessar opção 091
3. Informar número do CTRC (com DV)
4. Sistema retira CTRC da área de segregação
5. CTRC volta a estar disponível para operação normal

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 033 | Ocorrências de Transferência — permite segregação |
| 101 | Consulta de CTRC — permite segregação |
| 108 | Instruções para Ocorrências — permite segregação |
| 291 | Segregação de volumes com código de barras |
| 020 | Emissão de Manifestos — bloqueada para CTRCs segregados |
| 035 | Emissão de Romaneios — bloqueada para CTRCs segregados |
| SSWBar | Conferência de volumes — bloqueada para CTRCs segregados |
| 081 | CTRCs disponíveis para entrega — filtra segregados |
| 179 | Relatório de CTRCs com Pendência — identifica segregados (coluna SEG) |

## Relatório 179 — CTRCs com Pendência
- **Coluna SEG**: X indica CTRC segregado (opção 091)
- **Geração**: Diária, substituída a cada geração
- **Retenção**: Relatório do último dia do mês fica disponível por 13 meses
- **Filtro**: Última ocorrência tipo PENDENCIA ou CLIENTE
- **MTZ**: Todas as unidades
- **Unidade operacional**: Apenas CTRCs localizados na unidade

### Dados Importantes do Relatório 179
| Coluna | Descrição |
|--------|-----------|
| REMETENTE/ABC, DESTINATÁRIO/ABC | Classificação ABC para priorização |
| PREVENTR, ATRA | Previsão de entrega e dias de atraso (negativo=adiantado) |
| SEG | X=segregado (opção 091) |
| DATA PEN | Data de registro da ocorrência (mais antigas=ação imediata) |
| Linha ocorrência | Identifica responsabilidade (cliente ou transportadora) |
| RESUMO POR OCORRÊNCIA | Quantifica CTRCs por ocorrência |
| RESUMO POR UNIDADE | Quantifica CTRCs por unidade (somente MTZ) |

## Observações e Gotchas
- **Segregação do CTRC vs volumes**: Opção 091 segrega o CTRC inteiro, opção 291 segrega volumes individualmente
- **Em trânsito não pode**: CTRCs manifestados ou romaneados não podem ser segregados
- **Bloqueio operacional**: Segregação impede manifestação, romaneamento e conferência SSWBar
- **Consulta**: Link "Relacionar segregados" mostra todos CTRCs segregados no momento
- **Relatório 179**: Gerado diariamente para acompanhamento de pendências, identifica segregados na coluna SEG
- **Priorização**: Usar colunas ATRA (atraso), ABC (classificação) e DATA PEN (antiguidade) para priorizar resoluções

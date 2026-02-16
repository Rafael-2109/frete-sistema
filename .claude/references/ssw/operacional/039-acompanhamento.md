# Opcao 039 — Acompanhamento (Performance de Entregas)

> **Modulo**: Operacional — Relatorios
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Avalia performance mensal de entregas da transportadora e unidades de destino, gerando relatorios analiticos e resumidos de CTRCs entregues no prazo, atrasados por responsabilidade do cliente ou transportadora.

## Quando Usar
- Avaliar performance de entregas mensal
- Identificar CTRCs entregues fora do prazo
- Analisar atrasos por responsabilidade (cliente vs transportadora)
- Gerar indicadores de qualidade operacional

## Pre-requisitos
- CTRCs emitidos e entregues no periodo
- Prazos de transferencia cadastrados (Opcao 403)
- Prazos de entrega cadastrados (Opcao 402)
- Tabela de ocorrencias (Opcao 405)

## Relatorios Disponibilizados

| Relatorio | Descricao |
|-----------|-----------|
| 081 | Performance de Entrega da Unidade Destino (mensal) |
| 082 | CTRCs Atrasados da Unidade Destino (analitico) |
| 083 | Performance por Cliente Emitente (transportadora) |
| 084 | Performance por Cidade Destino (transportadora) |
| 085 | CTRCs Atrasados por Cidade Destino (analitico) |

## Abreviaturas Utilizadas

| Sigla | Significado |
|-------|-------------|
| ENTREGUE | Quantidade CTRCs entregues |
| NOPRAZO | Quantidade CTRCs entregues no prazo |
| ATRASCLI | Atraso responsabilidade cliente (tem ocorrencia cliente) |
| ATRASTRANSP | Atraso responsabilidade transportadora (sem ocorrencia cliente) |
| PERFORM | Performance = NOPRAZO / (ENTREGUE - ATRASCLI) |
| PREVENTR | Data previsao entrega CTRC (calculada na emissao) |
| PREVENTR2 | Data previsao entrega unidade destino (calculada na chegada Opcao 030) |

## Calculo de Datas

### PREVENTR (Previsao Entrega CTRC)
Calculado na emissao do CTRC, recalculado se houver agendamento (Opcao 015):
- Prazo transferencia (Opcao 403) em dias uteis
- + Prazo entrega cidade (Opcao 402) em dias uteis
- + Prazo adicional entrega dificil (Opcao 903)
- + Prazo adicional emissao apos horario corte (Opcao 903)
- Cliente pode ter prazo diferenciado (Opcao 696) que substitui calculo acima

### PREVENTR2 (Previsao Entrega Unidade Destino)
Calculado na chegada veiculo unidade destino (Opcao 030):
- Prazo entrega cidade (Opcao 402) em dias uteis
- + Prazo adicional entrega dificil (Opcao 903)
- + Prazo adicional chegada apos horario corte (Opcao 903)
- CTRCs sem chegada: PREVENTR = PREVENTR2

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 015 | Agendamento (recalcula PREVENTR) |
| 030 | Chegada veiculo (calcula PREVENTR2) |
| 038 | Baixa de entregas |
| 039 | Tabela ocorrencias (define responsabilidade) |
| 082 | Acesso aos relatorios gerenciais |
| 156 | Relatorios processados |
| 402 | Prazo entrega cidade |
| 403 | Prazo transferencia rota |
| 405 | Tabela ocorrencias |
| 696 | Prazo diferenciado por cliente |
| 903 | Prazos adicionais (ED, horario corte) |

## Observacoes e Gotchas

### Calculo de Performance
Formula: `PERFORM = NOPRAZO / (ENTREGUE - ATRASCLI)`

Retira da base de entregues os que tiveram ocorrencias de responsabilidade do cliente.

### Periodo de Referencia
Considerados todos CTRCs **emitidos** no periodo (nao entregues).

### Disponibilizacao
- Relatorios dia 01 e 10: mes anterior
- Relatorio dia 20: mes em curso

### CTRCs Sem Chegada
CTRCs sem chegada na unidade destino: PREVENTR = PREVENTR2

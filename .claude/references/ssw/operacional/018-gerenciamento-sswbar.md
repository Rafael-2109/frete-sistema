# Opcao 018 — Gerenciamento dos SSWBars

> **Modulo**: Operacional — Expedicao
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Monitora todas as operacoes com SSWBAR (sistema de codigo de barras) concluidas e em andamento. Exibe operacoes das ultimas 6 horas com detalhes de conferencia de volumes.

## Quando Usar
- Acompanhar conferencias de volumes em tempo real
- Verificar faltas e sobras de volumes nas operacoes
- Auditar trabalho dos conferentes
- Equipe SSW: finalizar operacoes especificas (funcao adicional)

## Pre-requisitos
- Operacoes SSWBAR iniciadas (coletas, manifestos ou romaneios)
- SSWBAR configurado e em uso

## Campos / Interface

| Campo | Descricao |
|-------|-----------|
| **Placa** | Veiculo processado pelo SSWBar |
| **Funcao** | Tipo de operacao: Descarregar coleta, Carregar Manifesto, Descarregar Manifesto, Carregar Romaneio |
| **Manifestos/Romaneios** | Identificacao dos manifestos/romaneios quando aplicavel |
| **Qtde CTRCs** | Quantidade total de CTRCs conferidos (link relaciona os CTRCs) |
| **Falta volume** | Quantidade de volumes faltantes (link relaciona os CTRCs) |
| **Sobra volumes** | Quantidade de volumes que sobraram (link relaciona os CTRCs) |
| **Conferente** | Login do conferente + total de CTRCs e volumes capturados (entre parenteses) |
| **Iniciada em** | Data e hora de inicio da operacao SSWBar |
| **Finalizado em** | Data e hora de encerramento da operacao |

## Fluxo de Uso
1. Acessar opcao 018 para visualizar operacoes em andamento e finalizadas
2. Verificar status das conferencias (colunas de faltas/sobras)
3. Clicar nos links de CTRCs para ver detalhes especificos
4. (Equipe SSW) Finalizar operacoes especificas se necessario

## Integracao com Outras Opcoes
| Conceito | Relacao |
|----------|---------|
| **SSWBAR** | Sistema de codigo de barras que processa volumes (nao CTRCs diretamente) |
| **Conversao** | Transacoes do SSWBar precisam ser convertidas em CTRCs para continuidade no SSW |

## Observacoes e Gotchas
- **SSWBar processa volumes, NAO CTRCs** — a conversao e feita posteriormente
- Exibe apenas operacoes das **ultimas 6 horas**
- Faltas e sobras de volumes podem ser registradas nos CTRCs
- Links na interface permitem drill-down nos CTRCs relacionados
- Videos disponiveis na documentacao original (video1, video2, video3)

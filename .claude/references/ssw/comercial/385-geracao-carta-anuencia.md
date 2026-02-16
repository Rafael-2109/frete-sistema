# Opcao 385 — Geracao de Carta de Anuencia

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada (fonte: opcao 356)
> **Atualizado em**: 2026-02-14

## Funcao
Gera Carta de Anuencia para faturas liquidadas que se encontravam em cobranca em instituicoes de cobranca (protestadas). Carta de Anuencia e uma declaracao onde o credor (transportadora) autoriza o cancelamento do titulo ou documento de divida protestado.

## Quando Usar
- Fatura protestada foi liquidada e precisa cancelar protesto
- Cliente solicitou Carta de Anuencia para regularizar situacao cadastral
- Necessario gerar Cartas de Anuencia em lote para periodo especifico
- Emitir Carta para fatura NAO protestada (caso especifico)

## Pre-requisitos
- Fatura protestada e liquidada
- Fatura estava em cobranca em instituicao de cobranca

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Fatura | Condicional | Se informada APENAS a fatura, Carta para fatura NAO protestada pode ser emitida |
| Periodo de liquidacao | Condicional | Seleciona faturas protestadas e liquidadas no periodo informado. Periodo pode ser de ate 90 dias quando informado o pagador |
| CNPJ pagador | Nao | Cliente pagador. Se omitido, TODOS os protestados sao considerados. Apenas raiz do CNPJ (8 numeros a esquerda) pode ser informada para considerar todos os CNPJs do cliente |

## Fluxo de Uso

### Geracao Individual (Fatura Especifica)
1. Informar numero da fatura
2. Confirmar dados
3. Sistema emite Carta de Anuencia
4. Ocorrencia e gravada no cliente (opcao 385)

### Geracao em Lote (Periodo + Pagador)
1. Informar periodo de liquidacao (ate 90 dias se informar pagador)
2. Opcionalmente informar CNPJ pagador (raiz com 8 digitos ou CNPJ completo)
3. Sistema seleciona faturas protestadas e liquidadas no periodo
4. Confirmar dados
5. Cartas de Anuencia sao emitidas para todas as faturas selecionadas
6. Ocorrencias sao gravadas no cliente (opcao 385)

### Geracao em Lote (Todos os Clientes)
1. Informar periodo de liquidacao
2. Deixar campo CNPJ pagador em branco
3. Sistema seleciona TODAS as faturas protestadas e liquidadas no periodo (todos os clientes)
4. Confirmar dados
5. Cartas de Anuencia sao emitidas
6. Ocorrencias sao gravadas nos respectivos clientes (opcao 385)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 385 | Cadastro de cliente — ocorrencia de emissao de Carta de Anuencia e gravada |

## Observacoes e Gotchas
- **Carta de Anuencia**: declaracao onde credor (transportadora) autoriza cancelamento de titulo ou documento de divida protestado
- **Valor do titulo**: corresponde ao valor TOTAL da fatura
- **Fatura NAO protestada**: se informar APENAS a fatura (sem periodo/pagador), Carta para fatura NAO protestada pode ser emitida (caso especifico)
- **Raiz do CNPJ**: informar apenas 8 primeiros digitos para considerar TODOS os CNPJs de um cliente (matriz + filiais)
- **Periodo limitado**: ao informar pagador, periodo pode ser de ate 90 dias
- **Ocorrencia automatica**: apos geracao da Carta, ocorrencia e automaticamente gravada no cadastro do cliente (opcao 385)
- **Protestadas + liquidadas**: sistema filtra APENAS faturas que estavam protestadas E foram liquidadas (nao considera faturas liquidadas sem protesto, exceto no caso de fatura individual)
- **Instituicoes de cobranca**: cartas sao geradas para faturas que estavam em cobranca em instituicoes especializadas (bancos, empresas de cobranca, etc.)

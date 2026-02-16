# Opcao 389 — Cadastro de Clientes - Credito

> **Modulo**: Comercial
> **Paginas de ajuda**: 4 paginas consolidadas (323, 583, Prazos, Credito)
> **Atualizado em**: 2026-02-14

## Funcao
Gestao de credito de clientes, incluindo definicao de limites por classificacao ABC, condicao de transporte (S=sim, V=a vista, N=nao transportar), bloqueios automaticos por inadimplencia/inatividade, liberacao provisoria de credito, e configuracao de grupos comerciais para analise consolidada.

## Quando Usar
- Definir ou alterar limite de credito de cliente
- Bloquear ou desbloquear cliente para transporte (Transportar: S/V/N)
- Conceder liberacao provisoria de credito para cliente bloqueado
- Configurar parametros globais de credito por classificacao ABC
- Criar grupos comerciais para consolidacao de CNPJs (relatorios gerenciais)
- Configurar prazos de inadimplencia e inatividade para bloqueio automatico

## Pre-requisitos
- Cliente cadastrado no sistema
- Para grupos comerciais: definir CNPJ principal que representa o grupo

## Campos / Interface

### Credito Individual (Opcao 389)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ do cliente | Sim | Cliente a ser configurado |
| Limite de credito | Nao | Valor maximo de credito concedido ao cliente (individual ou do grupo) |
| Transportar | Sim | S=sim (a prazo), V=a vista, N=nao transportar (bloqueado) |
| Bloqueios ocorrem na | Nao | C=coleta (001), E=geracao de CTRC (004, 006), A=ambos, N=sem bloqueio (quando cliente sem limite) |
| Classificacao ABC | Visualizacao | Classificacao automatica do cliente (A/B/C/Sem) |

### Liberacao Provisoria (Opcao 323)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ do cliente | Sim | Cliente com Transportar=N que tera liberacao provisoria |
| Liberar por (dias) | Sim | Quantidade de dias corridos em que credito ficara liberado. Sugestao: opcao 903/Prazos |
| Excluir vencidas | Nao | Link que exclui todas as liberacoes vencidas |

### Grupo de Clientes (Opcao 583)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ principal | Sim | CNPJ que representa o grupo |
| Nome do grupo | Sim | Nome atribuido ao grupo (inicialmente sugere razao social) |
| Adicionar CNPJ | Nao | Adiciona cliente ao grupo |
| Excluir | Nao | Exclui CNPJ do grupo |
| Limite de Credito (grupo) | Nao | Valor limite de credito do grupo (opcao 389) |
| Creditos tomados | Visualizacao | Valor total de fretes de CTRCs do grupo pendentes de liquidacao |

### Parametros Globais de Credito (Opcao 903/Credito)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Classificacao A | Sim | Limite de credito padrao para clientes A |
| Classificacao B | Sim | Limite de credito padrao para clientes B |
| Classificacao C | Sim | Limite de credito padrao para clientes C |
| Sem classificacao | Sim | Limite para clientes sem classificacao ABC (sem faturamento mes anterior) |
| Bloqueios ocorrem na | Sim | Sugestao para clientes sem limite: C=coleta, E=CTRC, A=ambos, N=sem bloqueio |
| Transportar (novos clientes) | Sim | Sugestao para novos clientes cadastrados: S=sim, V=a vista, N=nao transportar |

### Prazos (Opcao 903/Prazos)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cliente inadimplente, X dias, mudar credito para | Sim | Dias de atraso que muda Transportar para N ou V. Desbloqueio automatico: 09:30h e 12:40h |
| Cliente inativo, apos X meses, mudar credito para | Sim | Meses de inatividade que muda Transportar para N ou V. Verificacao no 1° dia do mes |
| Liberacao provisoria de credito | Sim | Prazo em dias uteis de liberacao provisoria (opcao 323) para cliente com Transportar=N |
| De envio de e-mail de vencimento da fatura | Sim | Dias corridos antes do vencimento. 0=nao envia. Para: T=todos, C=marcados na opcao 384 |
| De envio de e-mail por atraso de pagamento | Sim | 5 prazos em dias uteis para disparo de avisos de atraso/promessa nao cumprida (opcao 480) |
| De acompanhamento das ocorrencias | Sim | Periodo que CTRCs sao considerados em consultas/relatorios (opcao 056, 108). Exceto atrasados (90 dias) |
| De validacao das cotacoes | Sim | Dias corridos que cotacoes (002) podem ser usadas para calculo de frete (004) |

## Fluxo de Uso

### Configurar Credito Individual
1. Acessar opcao 389
2. Informar CNPJ do cliente
3. Definir limite de credito (individual ou grupo)
4. Configurar Transportar (S/V/N)
5. Se necessario, definir onde bloqueios ocorrem (C/E/A/N)
6. Salvar configuracao

### Conceder Liberacao Provisoria
1. Cliente deve estar com Transportar=N (bloqueado)
2. Acessar opcao 323
3. Informar CNPJ do cliente
4. Definir quantidade de dias corridos de liberacao
5. Salvar liberacao provisoria
6. Acompanhar via relatorio 072 (opcao 056)

### Criar Grupo Comercial
1. Acessar opcao 583
2. Informar CNPJ principal que representa o grupo
3. Definir nome do grupo
4. Adicionar CNPJs de clientes que farao parte do grupo
5. Configurar limite de credito do grupo (opcao 389)
6. Grupo passa a ser usado em relatorios: 070 (Maiores Clientes), 073 (Monitoracao)

### Configurar Parametros Globais
1. Acessar opcao 903/Credito
2. Definir limites padrao por classificacao ABC
3. Configurar sugestao de bloqueio (C/E/A/N)
4. Definir condicao padrao para novos clientes (S/V/N)
5. Acessar opcao 903/Prazos
6. Configurar prazos de inadimplencia, inatividade, liberacao provisoria, etc.
7. Salvar configuracoes

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 323 | Liberacao provisoria de credito para clientes com Transportar=N |
| 583 | Grupos comerciais — limite de credito do grupo configurado na opcao 389 |
| 903/Credito | Parametros globais de credito por classificacao ABC |
| 903/Prazos | Prazos de inadimplencia, inatividade, liberacao provisoria, etc. |
| 056 | Relatorios: 072 (Liberacao Provisoria), 070 (Maiores Clientes), 073 (Monitoracao) |
| 384 | Configuracao de envio de e-mail de vencimento/atraso |
| 480 | Promessa de pagamento (disparo de e-mail por nao cumprimento) |
| 483 | Classificacao Especial — nao sofre mudanca automatica de credito |
| 001 | Coleta — bloqueada se Transportar=N ou sem limite e bloqueio=C/A |
| 002 | Cotacao — validade configurada em Prazos |
| 004 | Geracao de CTRC — bloqueada se Transportar=N ou sem limite e bloqueio=E/A |
| 006 | Geracao de CTRC em lote — bloqueada se Transportar=N ou sem limite e bloqueio=E/A |
| 108 | Acompanhamento de ocorrencias — prazo configurado em Prazos |

## Observacoes e Gotchas
- **Desbloqueio automatico**: clientes inadimplentes que liquidam todas as faturas sao desbloqueados automaticamente as 09:30h e 12:40h. Clientes alterados MANUALMENTE para N ou V NAO recebem desbloqueio automatico
- **Classificacao Especial**: clientes com classificacao Especial (opcao 483) NAO sofrem mudanca automatica de credito por inadimplencia/inatividade
- **Grupos comerciais**: classificacao ABC considera todos os CNPJs do grupo como unico cliente. Classificacao obtida e atribuida a TODOS os CNPJs do grupo
- **Creditos tomados**: valor total de fretes de CTRCs do grupo pendentes de liquidacao (visualizado na opcao 583)
- **Liberacao vencida**: opcao 323 possui link para excluir TODAS as liberacoes vencidas de uma vez
- **Relatorio de liberacao**: opcao 056 disponibiliza relatorio 072 "Clientes com Liberacao Provisoria" para acompanhamento
- **Inatividade**: prazo contado a partir da emissao do ULTIMO CTRC que tem o cliente como pagador. Verificacao ocorre sempre no 1° dia do mes
- **Grupo em inatividade**: todos os CNPJs do grupo (opcao 583) sao verificados e processados em conjunto
- **E-mail de vencimento**: Para=T envia para todos clientes que receberam fatura via e-mail; Para=C envia apenas para marcados na opcao 384
- **E-mail de atraso**: 5 prazos em dias uteis para disparo progressivo de avisos. E-mail deve estar cadastrado na opcao 384
- **Validacao de cotacao**: cotacoes (opcao 002) ficam validas por X dias corridos para calculo de frete (opcao 004)
- **Novos clientes**: cadastro simplificado (opcoes 001, 002, 004) usa sugestao configurada em 903/Credito
- **Bloqueio em duas etapas**: C=bloqueia coleta, E=bloqueia CTRC, A=bloqueia ambos, N=nao bloqueia

# Opcao 384 — Cadastro de Clientes

> **Modulo**: Financeiro
> **Paginas de ajuda**: 14 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Cadastro central de clientes com configuracoes de faturamento, cobranca, forma de pagamento, unidade responsavel, entregador, e parametros para envio automatico de faturas e documentos fiscais.

## Quando Usar
- Incluir novo cliente no sistema
- Configurar regras de faturamento (manual, automatico, banco, carteira)
- Definir forma de liquidacao e prazo de vencimento
- Parametrizar envio de faturas por e-mail, Correios ou em maos
- Cadastrar unidade de cobranca e entregador para entrega de faturas
- Configurar mensagens padrao para e-mails de cobranca
- Definir reversao de frete entre pagadores
- Liberar CNPJ para impressao de documentos (opcao 426)

## Pre-requisitos
- Unidade de cobranca cadastrada no sistema (referenciada por sigla)
- Banco e agencia cadastrados (se cobranca bancaria)
- Entregador cadastrado (se entrega em maos)
- Mensagens padrao de e-mail configuradas (opcao 180) para:
  - Envio de fatura/bloqueto
  - Aviso de atraso de pagamento (cobranca)
  - Envio de DACTE/XML (opcao 483)
  - Envio de rastreamento (opcao 383)

## Campos / Interface

### Identificacao
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ/CPF | Sim | Identificacao do cliente pagador |
| Razao Social | Sim | Nome do cliente |
| Inscricao Estadual | Condicional | Obrigatorio se contribuinte |

### Faturamento e Cobranca
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Unidade de cobranca | Sim | Sigla da unidade responsavel pela cobranca |
| Forma de liquidacao | Sim | Banco/Ag/CCor/Cart OU 999 (carteira) OU a vista |
| Prazo de vencimento | Sim | Numero de dias para vencimento (opcao 521 altera em lote) |
| Banco/Ag/CCor/Cart | Condicional | Conta bancaria de cobranca (se nao for carteira/vista) |
| Envia fatura/bloqueto | Nao | Email, Correios, em maos ou nao envia |
| Entregador | Condicional | Codigo do entregador (se entrega em maos) |

### Reversao de Frete
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Novo pagador | Nao | CNPJ para onde reverter fretes (opcao 451) |

### Observacoes
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Texto observacao fatura | Nao | Impresso nas observacoes da fatura |

## Fluxo de Uso

### Inclusao de Novo Cliente
1. Acessar opcao 384
2. Informar CNPJ/CPF e dados cadastrais
3. Configurar unidade de cobranca
4. Definir forma de liquidacao (banco, carteira ou vista)
5. Parametrizar prazo de vencimento
6. Configurar envio de fatura (e-mail, Correios, entregador)
7. Gravar cadastro

### Configuracao de Envio Automatico de Faturas
1. No cadastro do cliente, marcar "Envia fatura/bloqueto por e-mail"
2. Sistema enviara automaticamente na madrugada seguinte ao faturamento
3. Monitorar envios pela opcao 056 - Relatorio 157 (enviadas) e 154 (nao abertas)

### Alteracao em Lote
- **Prazo de vencimento**: opcao 521 (troca em lote por unidade)
- **Conta bancaria**: opcao 517 (troca em lote, inclusive para carteira/vista)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 001 | Coleta - usa dados do cliente e mensagem padrao de e-mail |
| 002 | Cotacao - usa dados do cliente e mensagem padrao de e-mail |
| 096 | Relacao de faturas emitidas - filtra por unidade de cobranca |
| 102 | Ocorrencias do cliente - grava eventos (ex: emissao de declaracao) |
| 180 | Mensagens padrao - define textos para e-mails e observacoes |
| 383 | Rastreamento - envia e-mail com mensagem padrao |
| 396 | Impressao de DACTEs - filtra por "Envia por e-mail/Correios" |
| 398 | Comprovante de Entrega escaneado - vinculado a CTRCs do cliente |
| 401 | Multi-empresa - define empresa do cliente |
| 405 | Ocorrencias de CTRC - define baixa/entrega para faturamento |
| 417, 418 | Tabela de frete - usa mensagem padrao de e-mail |
| 426 | Liberacao de CNPJ para impressao de documentos |
| 428 | Arquivamento de Comprovante de Entrega |
| 436 | Faturamento automatico - usa regras de faturamento do cliente |
| 437 | Faturamento manual - usa banco de cobranca e prazo do cliente |
| 440 | Impressao de faturas - filtra por unidade, entregador, envio Correios/e-mail |
| 442 | Lancamento em CTR/fatura - gera adicionais vinculados ao cliente |
| 443 | Arquivo de remessa - gera para faturas vencidas |
| 445 | Envelope para faturas - usa unidade de cobranca |
| 451 | Reversao de fretes - usa "novo pagador" configurado |
| 457 | Adicionais em fatura - gera credito/debito |
| 459 | Relacao de adicionais - lista por cliente |
| 480 | Controle de cobrancas - filtra por unidade e entregador |
| 481 | Etiquetas para envio - filtra por unidade, entregador e tipo de cobranca |
| 482 | Protocolo para entrega - usa entregador cadastrado |
| 483 | Envio de DACTE/XML - usa mensagem padrao de e-mail |
| 504 | Declaracao de quitacao anual - usa unidade responsavel |
| 509 | Pre-fatura - gerada na transportadora para faturamento manual |
| 517 | Troca conta bancaria - altera em lote |
| 521 | Troca prazo de vencimento - altera em lote |

## Observacoes e Gotchas

### Forma de Liquidacao
- **Banco = 999**: cobranca em carteira (sem boleto bancario)
- **A vista**: frete cobrado pelo motorista entregador
- Sistema sugere banco do cliente no faturamento (opcoes 436, 437)

### Envio Automatico de Faturas
- **E-mail**: enviado na madrugada seguinte ao faturamento
- **Nao enviadas**: listadas em opcao 056 - Relatorio 154
- **Enviadas**: listadas em opcao 056 - Relatorio 157
- **Nao abertas**: clientes que receberam mas nao imprimiram (ate 7 dias antes e 30 dias apos vencimento)

### Entregador
- Obrigatorio se fatura entregue em maos
- Usado para gerar Protocolo de entrega (opcao 482)
- Usado em filtros de impressao de faturas (opcao 440) e etiquetas (opcao 481)

### Unidade de Cobranca
- Define responsavel pela cobranca do cliente
- Usada em filtros de relatorios e impressoes
- Usuario de MTZ (matriz) pode informar qualquer unidade; demais apenas a propria

### Reversao de Frete
- Opcao 451 usa "novo pagador" configurado
- Altera pagador sem modificacao fiscal
- Apenas CTRCs nao faturados e nao liquidados

### Faturamento Automatico vs Manual
- **Automatico (opcao 436)**: usa regras de faturamento do cliente
- **Manual (opcao 437)**: usa banco de cobranca e permite apontamento manual de CTRCs
- Se regras do cliente nao permitem faturamento automatico, usar manual

### Observacoes em Documentos
- Texto padrao impresso em faturas
- Cadastrado por cliente (especifico)
- Diferente de mensagem padrao de e-mail (opcao 180)

### Multiempresa
- Configuracao disponivel se opcao 401 ativada
- Define empresa dona do cadastro

### Integracao com CTRCs
- CTRCs entregues: ultima ocorrencia tipo ENTREGA (opcao 405)
- CTRCs baixados: ultima ocorrencia tipo BAIXA (opcao 405)
- CTRCs de complemento sempre considerados com o de referencia (opcoes 222, 016, 089, 015, 099, 199)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A01](../pops/POP-A01-cadastrar-cliente.md) | Cadastrar cliente |
| [POP-E01](../pops/POP-E01-pre-faturamento.md) | Pre faturamento |
| [POP-E02](../pops/POP-E02-faturar-manualmente.md) | Faturar manualmente |
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |
| [POP-E04](../pops/POP-E04-cobranca-bancaria.md) | Cobranca bancaria |
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |

# Opcao 457 — Manutencao de Faturas

> **Modulo**: Financeiro
> **Paginas de ajuda**: 9 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Manutencao completa de faturas incluindo consulta, alteracao de vencimento, instrucoes bancarias (abater, prorrogar, protestar, sustar protesto, baixar), marcacao para Serasa/Equifax/SPC, marcacao de fatura perdida, retirada de CTRCs da fatura, adicional de credito/debito, repassar para agencias e consulta de pagamentos parciais.

## Quando Usar
- Consultar detalhes de fatura especifica
- Alterar data de vencimento individual
- Enviar instrucoes bancarias (abater, prorrogar, protestar, baixar)
- Marcar faturas para envio ao Serasa (instrucao 96)
- Marcar faturas para baixa do Serasa (instrucao 97)
- Marcar faturas para envio ao Equifax/SPC
- Marcar fatura como perdida
- Retirar CTRC de fatura (para permitir estorno de liquidacao)
- Lancar adicional de credito/debito na fatura
- Repassar fatura para agencia
- Consultar pagamentos parciais de fatura
- Verificar se fatura foi descontada (opcao 448)
- Consultar fatura gerada automaticamente (pre-fatura Natura via ssw1911)

## Pre-requisitos
- Fatura emitida (opcoes 436 ou 437)
- Numero da fatura com digito verificador
- Banco de cobranca configurado (se instrucoes bancarias)
- Ocorrencias bancarias cadastradas (opcao 912)
- Contrato com Serasa/Equifax/SPC (se envio de inadimplencia)

## Campos / Interface

### Consulta de Fatura
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Numero da fatura | Sim | Numero com digito verificador |

### Informacoes Exibidas
| Campo | Descricao |
|-------|-----------|
| Data emissao | Data de emissao da fatura |
| Data vencimento | Data de vencimento original ou alterada |
| Valor total | Valor total da fatura |
| Valor pago | Valor ja liquidado (se pagamento parcial) |
| Saldo | Saldo pendente |
| CNPJ pagador | CNPJ do cliente pagador |
| Banco/Ag/CCor/Cart | Banco de cobranca |
| Situacao | Liquidada, Pendente, Vencida, Perdida, Cancelada, Descontada, etc |
| CTRCs | Relacao de CTRCs incluidos na fatura |
| Adicionais | Creditos/debitos lancados |
| Ocorrencias | Historico de instrucoes bancarias e eventos |

### Instrucoes Bancarias (Siglas)
| Sigla | Descricao | Tipo |
|-------|-----------|------|
| A | Abater | Transmissao (envio) |
| P | Prorrogar | Transmissao |
| R | Protestar | Transmissao |
| S | Sustar Protesto | Transmissao |
| B | Baixar | Transmissao |
| T | Entrada Confirmada | Recepcao |
| L | Liquidado | Recepcao |

### Instrucoes Especiais
| Codigo | Descricao |
|--------|-----------|
| 96 | Marcar para envio ao Serasa/Equifax/SPC |
| 97 | Marcar para baixa do Serasa/Equifax/SPC |

## Fluxo de Uso

### Consultar Fatura
1. Acessar opcao 457
2. Informar numero da fatura (com DV)
3. Visualizar detalhes, CTRCs, adicionais e ocorrencias

### Alterar Data de Vencimento Individual
1. Acessar opcao 457
2. Informar numero da fatura
3. Acessar link "Alterar vencimento"
4. Informar nova data de vencimento
5. Confirmar alteracao
6. Nao permitido para faturas: liquidadas, canceladas ou em arquivo de remessa

### Enviar Instrucao Bancaria (Abater, Prorrogar, Protestar, Baixar)
1. Acessar opcao 457
2. Informar numero da fatura
3. Acessar link "Instrucoes Gerais"
4. Selecionar instrucao (A, P, R, S, B)
5. Confirmar instrucao
6. Instrucao gravada em ocorrencias da fatura
7. Instrucao enviada ao banco via arquivo de remessa (opcao 443)

### Marcar Fatura para Serasa/Equifax/SPC
1. Acessar opcao 457
2. Informar numero da fatura vencida
3. Acessar link "Instrucoes Gerais"
4. Selecionar instrucao 96 (envio ao Serasa/Equifax/SPC)
5. Confirmar marcacao
6. Gerar arquivo pela opcao 334 (Serasa), 336 (Equifax) ou 337 (SPC)
7. Enviar arquivo ao orgao de protecao ao credito

### Baixar Fatura do Serasa/Equifax/SPC
1. Acessar opcao 457
2. Informar numero da fatura
3. Acessar link "Instrucoes Gerais"
4. Selecionar instrucao 97 (baixa do Serasa/Equifax/SPC)
5. Confirmar baixa
6. Baixa seguira automaticamente no proximo arquivo (opcao 334, 336 ou 337)

### Marcar Fatura como Perdida
1. Acessar opcao 457
2. Informar numero da fatura em carteira
3. Acessar link "Marcar como perdida"
4. Informar motivo
5. Confirmar
6. Valor aparece em Situacao Geral (opcao 001) como "PERDIDO (E)"

### Retirar CTRC de Fatura
1. Acessar opcao 457
2. Informar numero da fatura
3. Acessar link "Retirar CTRC"
4. Selecionar CTRC a ser retirado
5. Confirmar retirada
6. CTRC fica disponivel para novo faturamento
7. Necessario antes de estornar liquidacao de CTRC (opcao 429)

### Lancar Adicional (Credito/Debito)
1. Acessar opcao 457
2. Informar numero da fatura
3. Acessar link "Adicional"
4. Informar tipo (credito ou debito), valor e motivo
5. Confirmar lancamento
6. Credito reduz valor da fatura; debito aumenta
7. Adicional disponivel em faturamento manual (opcao 437)

### Repassar Fatura para Agencia
1. Acessar opcao 457
2. Informar numero da fatura
3. Acessar link "Repassar para agencia"
4. Selecionar agencia (opcao 466)
5. Confirmar repasse
6. Valor lancado via CCF (opcao 486)
7. Fatura nao pode ser trocada de banco apos repasse (opcao 465)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 001 | Situacao Geral - mostra valor de faturas perdidas |
| 334 | Gera arquivo PEFIN Serasa - usa instrucao 96/97 |
| 336 | Gera arquivo Equifax - usa instrucao 96/97 |
| 337 | Gera arquivo SPC - usa marcacao de inadimplencia |
| 357 | Faturas perdidas - marca em lote |
| 384 | Cadastro de clientes - configura cobranca de tarifa bancaria |
| 429 | Estorno de liquidacao - requer retirada de CTRC da fatura antes |
| 436 | Faturamento automatico - gera faturas |
| 437 | Faturamento manual - usa adicionais disponiveis |
| 443 | Arquivo de remessa - envia instrucoes bancarias ao banco |
| 444 | Arquivo de retorno - recebe confirmacao de instrucoes e liquidacao |
| 448 | Desconto de duplicatas - atualiza fatura como descontada |
| 459 | Relacao de adicionais - lista adicionais por cliente |
| 465 | Troca bancos de faturas - nao permitido se fatura tem pagamento parcial, em remessa, repassada ou descontada |
| 466 | Cadastro de agencias - destino de repasse |
| 486 | CCF - lanca repasse para agencia |
| 532 | Altera vencimento em lote - complementa alteracao individual |
| 569 | Conciliacao bancaria - impede estorno se conciliada |
| 904 | Cadastro de bancos - define tarifa bancaria cobrada |
| 912 | Ocorrencias bancarias - cadastra instrucoes disponiveis |
| ssw1911 | Pre-fatura Natura - gera fatura automaticamente via Webservice |

## Observacoes e Gotchas

### Instrucoes Bancarias
- **Transmissao (envio)**: A (Abater), P (Prorrogar), R (Protestar), S (Sustar Protesto), B (Baixar)
- **Recepcao**: T (Entrada Confirmada), L (Liquidado)
- Instrucoes enviadas ao banco via arquivo de remessa (opcao 443)
- Confirmacao recebida via arquivo de retorno (opcao 444)
- Ocorrencias cadastradas na opcao 912

### Tarifa Bancaria
- Se ocorrencia configurada como "COBRA CLIENTE = S" (opcao 912)
- Tarifa bancaria (opcao 904) cobrada na proxima fatura
- Cliente deve estar configurado para cobranca de tarifa (opcao 384)

### Situacoes que Impedem Operacoes
- **Troca de banco (opcao 465)**: nao permitido se fatura tem pagamento parcial, em arquivo de remessa, repassada para agencia ou descontada
- **Alteracao de vencimento**: nao permitido se liquidada, cancelada ou em arquivo de remessa
- **Estorno de liquidacao (opcao 429)**: requer retirada de CTRC da fatura antes

### Pagamento Parcial
- Fatura pode ter valor parcialmente liquidado
- Campo "Valor pago" mostra quanto ja foi liquidado
- Campo "Saldo" mostra quanto ainda falta liquidar
- Fatura com pagamento parcial nao pode ter banco trocado (opcao 465)

### Fatura Perdida
- Marcacao individual pela opcao 457
- Marcacao em lote pela opcao 357 (faixa de faturas ou periodo de vencimento)
- Apenas faturas em carteira (banco = 999)
- Valor aparece em Situacao Geral (opcao 001) como "PERDIDO (E)"

### Adicionais (Credito/Debito)
- **Credito**: reduz valor da fatura (ex: desconto concedido, devolucao de mercadoria)
- **Debito**: aumenta valor da fatura (ex: multa, taxa de reentrega)
- Origem: fatura ja emitida ou lancado em CTR/fatura (opcao 442)
- Disponiveis em faturamento manual (opcao 437)
- Relacao de adicionais por cliente (opcao 459)

### Serasa/Equifax/SPC
- **Instrucao 96**: marca para envio ao orgao de protecao ao credito
- **Instrucao 97**: marca para baixa do orgao
- Arquivos gerados pelas opcoes 334 (Serasa), 336 (Equifax), 337 (SPC)
- Envio ao orgao feito manualmente pela transportadora
- Fatura cancelada automaticamente segue para baixa no proximo arquivo

### Natura Pre-Fatura (ssw1911)
- Sistema busca automaticamente pre-faturas no Webservice da Natura
- Fatura gerada automaticamente pode ser consultada na opcao 457
- CNPJ raiz Natura: 71673990

### Repasse para Agencia
- Frete repassado para agencia (opcao 466) via CCF (opcao 486)
- Valor lancado simultaneamente em SAIDAS (despesas) na Situacao Geral (opcao 001)
- Fatura repassada nao pode ter banco trocado (opcao 465)

### Desconto de Duplicatas
- Fatura descontada (opcao 448) nao pode ter banco trocado (opcao 465)
- Situacao "Descontada" visivel na consulta da fatura

### Arquivo Morto
- Faturas liquidadas movidas para arquivo morto apos 90 dias
- Faturas nao liquidadas movidas apos 365 dias da emissao
- Faturas faturadas nao liquidadas NAO vao para arquivo morto
- Retirada do morto pela opcao 101 (se necessario estorno)

### Conciliacao Bancaria
- Nao e possivel estornar liquidacao se conta corrente conciliada (opcao 569)
- Necessario desconciliar antes de estornar

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E02](../pops/POP-E02-faturar-manualmente.md) | Faturar manualmente |
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |
| [POP-E05](../pops/POP-E05-liquidar-fatura.md) | Liquidar fatura |
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
| [POP-F05](../pops/POP-F05-bloqueio-financeiro-ctrc.md) | Bloqueio financeiro ctrc |

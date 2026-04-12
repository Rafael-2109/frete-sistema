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

### Menu da Opcao 457 (confirmado 2026-04-12)

> O menu real da 457 e numerado (68-99), nao por siglas. As siglas A/P/R/S/B sao codigos CNAB do arquivo de remessa (opcao 443), documentadas mais abaixo.

| Opcao | Funcao |
|-------|--------|
| **82** | Incluir CTRC na fatura |
| **92** | Excluir CTRCs da fatura |
| **85** | Mudar data de vencimento |
| **74** | Mudar data de emissao |
| **86** | **Lancamento de credito** — subtraido do valor da fatura (desconto) |
| **87** | **Lancamento de debito** — adicionado ao valor da fatura (multa, taxa) |
| **94** | Troca unidade responsavel pela fatura |
| **83** | Mudar cobranca de carteira para agencia |
| **84** | Mudar de cobranca agencia para carteira |
| **77** | Observacao impressa na fatura |
| **95** | Retira do arq. remessa / Libera geracao novo boleto |
| **90** | Baixa fatura bancaria para carteira |
| **89** | Pagamento parcial da fatura |
| **81** | Estorno de pagamento parcial |
| **73** | Pagamento parcial da fatura por CTRC/Nota |
| **72** | Estorno de pagamento parcial da fatura por CTRC/Nota |
| **88** | Liquidacao da fatura |
| **93** | Estorno de liquidacao de fatura |
| **76** | Descontar titulo bancario |
| **75** | Estorno de desconto titulo bancario |
| **78** | Baixa para carteira fatura descontada em banco |
| **79** | Liquidacao fatura descontada em banco |
| **96** | Marca fatura para inclusao no Serasa/Equifax |
| **97** | Marca fatura p/ baixa no Serasa/Equifax (renegociacao divida) |
| **68** | Marca fatura para inclusao no SPC |
| **69** | Marca fatura p/ baixa no SPC (renegociacao divida) |
| **70** | Marca fatura como protestada |
| **71** | Desmarca fatura como protestada |
| **98** | Fatura perdida nao recebivel |
| **80** | Estorno de Fatura Perdida |
| **91** | Cancelar fatura |
| **99** | Incluir informacao ou instrucao |

### Codigos CNAB (Arquivo de Remessa 443) — NAO sao menu da 457

Estes codigos de transmissao sao enviados ao banco via arquivo de remessa ([opcao 443](./443-gera-arquivo-cobranca.md)) a partir de acoes executadas na 457. Nao sao opcoes de menu.

| Codigo | Descricao | Tipo |
|--------|-----------|------|
| **A** | Abater | Transmissao (envio) |
| **P** | Prorrogar | Transmissao |
| **R** | Protestar | Transmissao |
| **S** | Sustar Protesto | Transmissao |
| **B** | Baixar | Transmissao |
| **T** | Entrada Confirmada | Recepcao (retorno 444) |
| **L** | Liquidado | Recepcao (retorno 444) |

## Fluxo de Uso

### Consultar Fatura
1. Acessar opcao 457
2. Informar numero da fatura (com DV)
3. Visualizar detalhes, CTRCs, adicionais e ocorrencias

### Alterar Data de Vencimento Individual
1. Acessar opcao 457
2. Informar numero da fatura
3. Selecionar **opcao 85** (Mudar data de vencimento)
4. Informar nova data de vencimento
5. Confirmar alteracao
6. Nao permitido para faturas: liquidadas, canceladas ou em arquivo de remessa ja enviado

### Lancar Credito (Desconto) ou Debito (Multa/Taxa)
1. Acessar opcao 457
2. Informar numero da fatura
3. Selecionar **opcao 86** (credito — subtrai do valor) ou **opcao 87** (debito — adiciona ao valor)
4. Informar valor e motivo
5. Confirmar lancamento
6. Sistema atualiza valor da fatura

> **Caso de uso validado 2026-04-12**: Desconto em fatura emitida com valor maior que o negociado, apos 7 dias (CT-e nao pode mais ser cancelado no SEFAZ) — opcao 86 resolve o financeiro. CT-e fiscal permanece com valor original.

### Marcar Fatura para Serasa/Equifax/SPC
1. Acessar opcao 457
2. Informar numero da fatura vencida
3. Selecionar:
   - **opcao 96** — inclusao no Serasa/Equifax
   - **opcao 68** — inclusao no SPC
4. Confirmar marcacao
5. Gerar arquivo pela opcao **334** (Serasa), **336** (Equifax) ou **337** (SPC)
6. Enviar arquivo ao orgao de protecao ao credito

### Baixar Fatura do Serasa/Equifax/SPC (cliente pagou / renegociou)
1. Acessar opcao 457
2. Informar numero da fatura
3. Selecionar:
   - **opcao 97** — baixa no Serasa/Equifax
   - **opcao 69** — baixa no SPC
4. Confirmar baixa
5. Baixa seguira automaticamente no proximo arquivo (opcao 334, 336 ou 337)

### Marcar/Desmarcar Fatura como Protestada
1. Acessar opcao 457
2. Informar numero da fatura
3. Selecionar **opcao 70** (marcar como protestada) ou **opcao 71** (desmarcar)
4. Confirmar

### Marcar Fatura como Perdida
1. Acessar opcao 457
2. Informar numero da fatura em carteira
3. Selecionar **opcao 98** (Fatura perdida nao recebivel)
4. Informar motivo
5. Confirmar
6. Valor aparece em Situacao Geral (opcao 001) como "PERDIDO (E)"
7. Estorno: **opcao 80** (Estorno de Fatura Perdida)

### Cancelar Fatura
1. Acessar opcao 457
2. Informar numero da fatura
3. Selecionar **opcao 91** (Cancelar fatura)
4. Confirmar cancelamento

### Incluir/Excluir CTRC da Fatura
1. Acessar opcao 457
2. Informar numero da fatura
3. Selecionar **opcao 82** (Incluir CTRC) ou **opcao 92** (Excluir CTRCs)
4. Selecionar CTRC
5. Confirmar — CTRC excluido fica disponivel para novo faturamento
6. Necessario (92) antes de estornar liquidacao de CTRC (opcao 429)

### Registrar Pagamento Parcial / Liquidacao
| Operacao | Opcao 457 |
|----------|-----------|
| Pagamento parcial | **89** |
| Estorno pagamento parcial | **81** |
| Pagamento parcial por CTRC/Nota | **73** |
| Estorno pagamento parcial por CTRC/Nota | **72** |
| Liquidacao | **88** |
| Estorno de liquidacao | **93** |

### Mudar Cobranca (Carteira ↔ Agencia)
1. Acessar opcao 457
2. Informar numero da fatura
3. Selecionar **opcao 83** (carteira → agencia) ou **opcao 84** (agencia → carteira)
4. Selecionar agencia (opcao 466) — quando aplicavel
5. Confirmar — valor lancado via CCF (opcao 486)
6. Fatura nao pode ser trocada de banco apos repasse (opcao 465)

### Outras Operacoes
| Operacao | Opcao 457 |
|----------|-----------|
| Mudar data de emissao | **74** |
| Troca unidade responsavel | **94** |
| Observacao impressa na fatura | **77** |
| Retira do arq. remessa / libera novo boleto | **95** |
| Baixa fatura bancaria para carteira | **90** |
| Descontar titulo bancario | **76** |
| Estorno desconto titulo | **75** |
| Baixa p/ carteira fatura descontada | **78** |
| Liquidacao fatura descontada | **79** |
| Incluir informacao ou instrucao | **99** |

### Envio de Codigos CNAB ao Banco (via Remessa 443)

> Estas instrucoes NAO sao executadas na 457 diretamente — sao **geradas** pela 457 e **enviadas** via arquivo de remessa (opcao 443).

1. Executar operacao na 457 (ex: opcao 86 credito → gera CNAB "A" abater)
2. Acessar opcao **443** (Gera Arquivo de Cobranca)
3. Sistema monta arquivo com codigos CNAB correspondentes
4. Enviar arquivo ao banco
5. Retorno do banco via opcao **444** (Cobranca Bancaria — Retorno) traz codigos T (Entrada Confirmada) ou L (Liquidado)

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

### GOTCHA Critico — Menu 457 e numerado, NAO por siglas (corrigido 2026-04-12)

**Erro comum**: Citar A/P/R/S/B como "opcoes" do menu da 457. Errado.

- **Menu da 457**: numerado 68-99 (ver tabela "Menu da Opcao 457" acima)
- **Siglas A/P/R/S/B**: sao **codigos CNAB** de transmissao no arquivo de remessa (opcao 443), **nao sao menu**
- **Siglas T/L**: codigos CNAB de recepcao no arquivo de retorno (opcao 444)

### Codigos CNAB (Fluxo 457 → 443 → Banco → 444)
- **Transmissao (envio)**: A (Abater), P (Prorrogar), R (Protestar), S (Sustar Protesto), B (Baixar)
- **Recepcao**: T (Entrada Confirmada), L (Liquidado)
- Operacao executada na **457** (menu numerado) gera codigo CNAB correspondente
- Codigo enviado ao banco via arquivo de remessa (**443**)
- Confirmacao/retorno recebida via arquivo de retorno (**444**)
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

### Adicionais (Credito/Debito — opcoes 86 e 87 da 457)
- **Opcao 86 — Credito**: reduz valor da fatura (ex: desconto concedido, ajuste ao valor negociado, devolucao de mercadoria)
- **Opcao 87 — Debito**: aumenta valor da fatura (ex: multa, taxa de reentrega)
- Origem: fatura ja emitida ou lancado em CTR/fatura (opcao 442)
- Disponiveis em faturamento manual (opcao 437)
- Relacao de adicionais por cliente (opcao 459)
- **Caso validado 2026-04-12**: desconto em fatura com valor maior que o negociado apos 7 dias (CT-e nao pode mais ser cancelado no SEFAZ) — opcao 86 resolve o financeiro. O CT-e fiscal permanece com valor original (impacta SPED/ICMS).

### Serasa/Equifax/SPC
- **Opcao 96**: inclusao no Serasa/Equifax
- **Opcao 97**: baixa no Serasa/Equifax (renegociacao divida)
- **Opcao 68**: inclusao no SPC
- **Opcao 69**: baixa no SPC (renegociacao divida)
- **Opcoes 70/71**: marcar/desmarcar fatura como protestada (processo distinto)
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

---

## Historico de Correcoes

| Data | Alteracao |
|------|-----------|
| 2026-02-14 | Criacao inicial |
| 2026-04-12 | Correcao — menu da 457 e numerado (68-99), nao por siglas. Siglas A/P/R/S/B reclassificadas como codigos CNAB do arquivo de remessa 443. Adicionada tabela completa do menu. Validado com usuario: opcao 86 funcionou para desconto em fatura apos 7 dias. |

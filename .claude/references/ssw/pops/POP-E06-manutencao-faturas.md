# POP-E06 — Manter Faturas (Prorrogar, Protestar, Baixar)

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: [457](../financeiro/457-manutencao-faturas.md), [443](../financeiro/443-gera-arquivo-cobranca.md), [444](../financeiro/444-cobranca-bancaria.md), [384](../financeiro/384-cadastro-clientes.md), 532
> **Executor atual**: Rafael (nao usa — sem cobranca bancaria)
> **Executor futuro**: Jaqueline

---

## Objetivo

Realizar manutencao completa de faturas incluindo consulta de detalhes, alteracao de vencimento, envio de instrucoes bancarias (abater, prorrogar, protestar, sustar protesto, baixar), marcacao para Serasa/Equifax/SPC, retirada de CTRCs, lancamento de adicionais (credito/debito) e consulta de pagamentos parciais. Este POP cobre o ciclo de vida pos-emissao da fatura.

---

## Quando Executar (Trigger)

- Consultar detalhes de fatura especifica (CTRC incluidos, valor, situacao)
- Cliente solicita prorrogacao de vencimento
- Fatura vencida e cliente nao pagou (necessidade de protesto)
- Cliente pagou parcialmente (registrar pagamento parcial)
- Necessidade de abater valor (desconto concedido)
- Baixar fatura manualmente (por acordo comercial)
- Marcar inadimplente para Serasa/Equifax/SPC
- Retirar CTRC de fatura (para permitir estorno de liquidacao)
- Lancar adicional de credito/debito na fatura
- Verificar se fatura foi descontada ([opcao 448](../financeiro/448-desconto-duplicatas-cadastramento.md))

---

## Frequencia

Por demanda — conforme necessidade operacional/comercial.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Fatura emitida | 436 ou 437 | Fatura existe no sistema |
| Numero da fatura | — | Numero com digito verificador (DV) |
| Banco de cobranca | [384](../financeiro/384-cadastro-clientes.md), [904](../cadastros/904-bancos-contas-bancarias.md) | Se instrucoes bancarias (A, P, R, S, B) |
| Ocorrencias bancarias | 912 | Instrucoes disponiveis para uso |
| Contrato Serasa/SPC | 334, 336, 337 | Se marcacao de inadimplencia |

---

## Passo-a-Passo

### ETAPA 1 — Consultar Fatura

1. Acessar [opcao **457**](../financeiro/457-manutencao-faturas.md) (Manutencao de Faturas)
2. Informar **numero da fatura com DV** (ex: 123456-7)
3. Sistema exibe detalhes completos:

| Informacao | Descricao |
|------------|-----------|
| Data emissao | Data de emissao da fatura |
| Data vencimento | Vencimento original ou alterado |
| Valor total | Valor total da fatura |
| Valor pago | Valor ja liquidado (se pagamento parcial) |
| Saldo | Saldo pendente (total - pago) |
| CNPJ pagador | CNPJ do cliente pagador |
| Banco/Ag/CCor/Cart | Banco de cobranca (999 = carteira propria) |
| Situacao | Liquidada, Pendente, Vencida, Perdida, Cancelada, Descontada, etc |
| CTRCs | Relacao de CTRCs incluidos na fatura |
| Adicionais | Creditos/debitos lancados ([opcao 459](../financeiro/459-cadastro-tde.md)) |
| Ocorrencias | Historico de instrucoes bancarias e eventos |

> **Situacao da fatura**: Indica o status atual. Liquidada = paga completamente. Pendente = aguardando pagamento. Vencida = passou do vencimento sem pagar.

---

### ETAPA 2 — Alterar Vencimento Individual

**Quando usar**: Cliente solicita prorrogacao de vencimento de fatura especifica.

4. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), selecionar **opcao 85** ("Mudar data de vencimento")
5. Informar **nova data de vencimento**
6. Confirmar alteracao
7. Sistema atualiza vencimento

> **RESTRICOES**:
> - NAO permitido para faturas liquidadas, canceladas ou em arquivo de remessa ja enviado
> - Se banco de cobranca (nao carteira 999): apos alterar na 457, instrucao P (prorrogar) e enviada ao banco via arquivo de remessa ([opcao 443](../financeiro/443-gera-arquivo-cobranca.md))

**Alternativa em lote**: Usar opcao **532** para alterar vencimento de varias faturas de uma vez (por faixa de faturas ou periodo de vencimento).

**Alternativa — Mudar data de emissao**: opcao **74** dentro da 457 (uso raro, requerido em casos especificos).

---

### ETAPA 3 — Operacoes Financeiras da Fatura (Menu 457)

**Quando usar**: Qualquer alteracao financeira na fatura apos emissao (desconto, multa, protesto, baixa, liquidacao, cancelamento).

8. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), selecionar a opcao numerada desejada do menu:

**Menu Completo da Opcao 457** (confirmado 2026-04-12):

| Opcao | Funcao | Categoria |
|-------|--------|-----------|
| **82** | Incluir CTRC na fatura | CTRCs |
| **92** | Excluir CTRCs da fatura | CTRCs |
| **85** | Mudar data de vencimento | Datas |
| **74** | Mudar data de emissao | Datas |
| **86** | Lancamento de credito (subtrai do valor da fatura) | Ajuste valor |
| **87** | Lancamento de debito (adiciona ao valor da fatura) | Ajuste valor |
| **94** | Troca unidade responsavel pela fatura | Estrutura |
| **83** | Mudar cobranca de carteira para agencia | Cobranca |
| **84** | Mudar de cobranca agencia para carteira | Cobranca |
| **77** | Observacao impressa na fatura | Info |
| **95** | Retira do arq. remessa / Libera geracao novo boleto | Remessa |
| **90** | Baixa fatura bancaria para carteira | Cobranca |
| **89** | Pagamento parcial da fatura | Pagamentos |
| **81** | Estorno de pagamento parcial | Pagamentos |
| **73** | Pagamento parcial da fatura por CTRC/Nota | Pagamentos |
| **72** | Estorno de pagamento parcial da fatura por CTRC/Nota | Pagamentos |
| **88** | Liquidacao da fatura | Pagamentos |
| **93** | Estorno de liquidacao de fatura | Pagamentos |
| **76** | Descontar titulo bancario | Desconto titulos |
| **75** | Estorno de desconto titulo bancario | Desconto titulos |
| **78** | Baixa para carteira fatura descontada em banco | Desconto titulos |
| **79** | Liquidacao fatura descontada em banco | Desconto titulos |
| **96** | Marca fatura para inclusao no Serasa/Equifax | Inadimplencia |
| **97** | Marca fatura p/ baixa no Serasa/Equifax (renegociacao divida) | Inadimplencia |
| **68** | Marca fatura para inclusao no SPC | Inadimplencia |
| **69** | Marca fatura p/ baixa no SPC (renegociacao divida) | Inadimplencia |
| **70** | Marca fatura como protestada | Protesto |
| **71** | Desmarca fatura como protestada | Protesto |
| **98** | Fatura perdida nao recebivel | Perdas |
| **80** | Estorno de Fatura Perdida | Perdas |
| **91** | Cancelar fatura | Cancelamento |
| **99** | Incluir informacao ou instrucao | Info |

9. Confirmar operacao
10. Operacao gravada em **ocorrencias da fatura**

---

#### IMPORTANTE — Siglas CNAB NAO sao o menu da 457

As siglas **A** (Abater), **P** (Prorrogar), **R** (Protestar), **S** (Sustar Protesto), **B** (Baixar) sao **codigos de transmissao CNAB** enviados ao banco via arquivo de remessa ([opcao 443](../financeiro/443-gera-arquivo-cobranca.md)) — **NAO sao opcoes do menu da 457**. O fluxo correto:

1. Dentro da 457: executar operacao (ex: opcao 86 para lancar credito)
2. Instrucao correspondente e gravada na fatura
3. [Opcao 443](../financeiro/443-gera-arquivo-cobranca.md) gera arquivo de remessa com codigo CNAB apropriado (A/P/R/S/B) para enviar ao banco
4. [Opcao 444](../financeiro/444-cobranca-bancaria.md) recebe retorno do banco com codigos **T** (Entrada Confirmada) ou **L** (Liquidado)

---

### ETAPA 4 — Marcar para Serasa/Equifax/SPC

**Quando usar**: Fatura vencida, cliente inadimplente, necessidade de registrar divida em orgao de protecao ao credito.

14. Na tela de consulta da fatura vencida ([opcao 457](../financeiro/457-manutencao-faturas.md)), selecionar a opcao conforme orgao:

| Orgao | Incluir | Baixar (cliente pagou / renegociou) |
|-------|---------|-------------------------------------|
| Serasa / Equifax | **96** | **97** |
| SPC | **68** | **69** |

15. Confirmar marcacao
16. Instrucao gravada em ocorrencias
17. Gerar arquivo pela opcao **334** (Serasa), **336** (Equifax) ou **337** (SPC)
18. Enviar arquivo ao orgao de protecao ao credito

> **ATENCAO**: Envio ao Serasa/SPC e processo serio com implicacoes legais. Verificar com comercial antes de marcar.

**Observacao — Protesto**: Para marcar/desmarcar fatura como protestada, usar opcao **70** (marcar) ou **71** (desmarcar) dentro da 457. Protesto e processo distinto de Serasa/SPC.

---

### ETAPA 5 — Marcar Fatura como Perdida

**Quando usar**: Fatura irrecuperavel (cliente falido, empresa fechou, acordo de perdao de divida).

19. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), selecionar **opcao 98** ("Fatura perdida nao recebivel")
20. Informar **motivo** (obrigatorio)
21. Confirmar
22. Valor aparece em Situacao Geral ([opcao 001](../operacional/001-cadastro-coletas.md)) como **"PERDIDO (E)"**

**Estorno de fatura perdida**: opcao **80** (Estorno de Fatura Perdida) dentro da 457.

> **RESTRICAO**: Apenas faturas em carteira (banco = 999). Faturas em cobranca bancaria devem ser baixadas primeiro via codigo CNAB "B" (baixar) enviado no arquivo de remessa [opcao 443](../financeiro/443-gera-arquivo-cobranca.md).

**Marcacao em lote**: Usar opcao **357** (Faturas Perdidas) para marcar varias faturas de uma vez (por faixa ou periodo de vencimento).

---

### ETAPA 6 — Retirar CTRC de Fatura

**Quando usar**: CTRC liquidado incorretamente (opcao 429) ou necessidade de estornar liquidacao de CTRC.

23. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), selecionar **opcao 92** ("Excluir CTRCs da fatura")
24. Selecionar CTRC a ser retirado
25. Confirmar retirada
26. CTRC fica disponivel para novo faturamento ([opcao 435](../financeiro/435-pre-faturamento.md))

**Incluir CTRC em fatura existente**: opcao **82** ("Incluir CTRC na fatura") dentro da 457.

> **Pre-requisito obrigatorio**: Retirar CTRC da fatura (opcao 92) ANTES de estornar liquidacao (opcao 429). Sistema nao permite estorno com CTRC em fatura.

---

### ETAPA 7 — Lancar Credito ou Debito (Ajustar Valor)

**Quando usar**: Adicionar credito (desconto, devolucao) ou debito (multa, taxa de reentrega) APOS emissao da fatura.

27. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), selecionar:
    - **Opcao 86** — Lancamento de credito (subtrai do valor da fatura) — para descontos
    - **Opcao 87** — Lancamento de debito (adiciona ao valor da fatura) — para multas/taxas
28. Informar:
    - **Valor**: valor do credito/debito
    - **Motivo**: descricao (ex: "Desconto comercial — ajuste ao valor negociado", "Taxa de reentrega")
29. Confirmar lancamento
30. Sistema atualiza valor da fatura

> **Opcao 86 (credito)**: Reduz valor da fatura. Ex: desconto concedido, ajuste ao valor negociado, devolucao de mercadoria.
> **Opcao 87 (debito)**: Aumenta valor da fatura. Ex: multa, taxa de reentrega.

**Caso de uso validado** (2026-04-12): Desconto em fatura emitida apos 7 dias (prazo SEFAZ de cancelamento do CT-e vencido) — opcao 86 resolve o lado comercial. O CT-e fiscal permanece com o valor original (impacta SPED/ICMS).

**Origem dos adicionais**: Podem ser lancados aqui (opcoes 86/87 da 457) ou vir de CTR/fatura ([opcao 442](../financeiro/442-credito-debito-ctrc-fatura.md)). Relacao de adicionais por cliente disponivel na [opcao 459](../financeiro/459-cadastro-tde.md).

---

### ETAPA 8 — Mudar Cobranca (Carteira ↔ Agencia)

**Quando usar**: Frete repassado para agencia (opcao 466) — registro de transferencia de credito.

31. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), selecionar:
    - **Opcao 83** — Mudar cobranca de carteira para agencia
    - **Opcao 84** — Mudar de cobranca agencia para carteira (reverter)
32. Selecionar **agencia** (opcao 466) — quando aplicavel
33. Confirmar operacao
34. Sistema:
    - Lanca valor via CCF ([opcao 486](../financeiro/486-conta-corrente-fornecedor.md))
    - Lanca em SAIDAS (despesas) na Situacao Geral ([opcao 001](../operacional/001-cadastro-coletas.md))
35. Fatura nao pode mais ter banco trocado (opcao 465)

> **Contexto CarVia**: Repasse para agencia NAO se aplica a operacao CarVia (nao ha agencias). Incluido por completude do POP.

---

### ETAPA 9 — Consultar Pagamentos Parciais

**Quando usar**: Cliente pagou parte da fatura, verificar saldo pendente.

41. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), verificar campos:
    - **Valor pago**: Quanto ja foi liquidado
    - **Saldo**: Quanto ainda falta liquidar
42. Sistema exibe historico de pagamentos parciais
43. Fatura com pagamento parcial NAO pode ter banco trocado (opcao 465)

---

## Tarifa Bancaria

Se ocorrencia configurada como **"COBRA CLIENTE = S"** (opcao 912):
- Tarifa bancaria ([opcao 904](../cadastros/904-bancos-contas-bancarias.md)) cobrada na proxima fatura
- Cliente deve estar configurado para cobranca de tarifa ([opcao 384](../financeiro/384-cadastro-clientes.md))

Codigos CNAB enviados via arquivo de remessa [443](../financeiro/443-gera-arquivo-cobranca.md) que podem gerar tarifa: **A** (abater), **P** (prorrogar), **R** (protestar), **S** (sustar protesto), **B** (baixar).

---

## Situacoes que Impedem Operacoes

| Operacao | Impedimentos |
|----------|--------------|
| Alterar vencimento | Fatura liquidada, cancelada ou em arquivo de remessa |
| Trocar banco (opcao 465) | Pagamento parcial, em remessa, repassada, descontada |
| Estornar liquidacao (opcao 429) | CTRC ainda na fatura (retirar primeiro) |
| Marcar como perdida | Fatura em cobranca bancaria (baixar primeiro) |

---

## Contexto CarVia

### Hoje

- Rafael NAO usa [opcao 457](../financeiro/457-manutencao-faturas.md)
- SEM cobranca bancaria (banco = 999, carteira propria)
- SEM boleto
- Cliente deposita diretamente
- SEM controle de faturas vencidas
- SEM protesto, SEM Serasa

### Futuro (com POP implantado)

- Jaqueline monitora faturas vencidas semanalmente
- Prorrogacao de vencimento (ETAPA 2, opcao 85) para clientes parceiros
- Marcacao de inadimplentes para Serasa (ETAPA 4, opcoes 96/97) — comercial autoriza
- Codigos CNAB via remessa 443 (ETAPA 3) quando migrar para cobranca bancaria (POP-E04)
- Lancamentos de credito/debito (ETAPA 7, opcoes 86/87) para taxas de reentrega, descontos

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Fatura nao encontrada | Numero incorreto ou DV errado | Verificar numero na [opcao 056](../relatorios/056-informacoes-gerenciais.md) ou 437 |
| Vencimento nao pode ser alterado (opcao 85) | Fatura liquidada, cancelada ou em remessa ja enviada | Verificar situacao da fatura |
| Instrucao CNAB nao enviada ao banco | Fatura em carteira (999) | Codigos CNAB A/P/R/S/B via remessa 443 so para cobranca bancaria |
| CTRC nao pode ser retirado (opcao 92) | CTRC ja liquidado ou fatura conciliada (569) | Desconciliar antes ou estornar liquidacao |
| Tarifa nao cobrada | Ocorrencia sem "COBRA CLIENTE = S" (912) | Configurar ocorrencia ou cliente ([384](../financeiro/384-cadastro-clientes.md)) |
| Fatura perdida rejeitada (opcao 98) | Banco diferente de 999 | Baixar fatura primeiro via codigo CNAB "B" no arquivo de remessa [443](../financeiro/443-gera-arquivo-cobranca.md) |
| Credito/debito (86/87) nao aparece | Lancado apos faturamento | Ajuste so aparece na proxima fatura |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Fatura existe | [Opcao 457](../financeiro/457-manutencao-faturas.md) → informar numero → detalhe exibido |
| Vencimento alterado (85) | [Opcao 457](../financeiro/457-manutencao-faturas.md) → detalhe → data vencimento = nova data |
| Credito/debito gravado (86/87) | [Opcao 457](../financeiro/457-manutencao-faturas.md) → ocorrencias/valor → credito/debito registrado |
| CTRC retirado (92) | [Opcao 457](../financeiro/457-manutencao-faturas.md) → CTRCs → CTRC nao aparece mais |
| Fatura cancelada (91) | [Opcao 457](../financeiro/457-manutencao-faturas.md) → situacao → "Cancelada" |
| Marcada como perdida (98) | [Opcao 001](../operacional/001-cadastro-coletas.md) → Situacao Geral → PERDIDO (E) |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-E02 | Faturamento manual — gera faturas |
| POP-E03 | Faturamento automatico — gera faturas |
| POP-E04 | Cobranca bancaria — pre-requisito para instrucoes |
| POP-E05 | Liquidar fatura — proximo passo (registrar pagamento) |
| POP-F04 | Conciliacao bancaria — impede estorno se conciliada |
| POP-E01 | Pre-faturamento — verificar antes de faturar |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |
| 2026-04-12 | 1.1 | Correcao — menu da 457 e numerado (68-99), nao siglas. A/P/R/S/B sao codigos CNAB do arquivo de remessa 443. Validado com usuario (opcao 86 para desconto). |

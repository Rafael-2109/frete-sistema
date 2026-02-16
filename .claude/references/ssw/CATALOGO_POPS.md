# Catalogo de POPs — CarVia Logistica

> **Criado em**: 2026-02-15
> **Fonte**: CARVIA_OPERACAO.md + FLUXOS_PROCESSO.md + 228 docs SSW
> **Objetivo**: Definir TODOS os POPs necessarios para padronizar a operacao CarVia no SSW
> **Uso pelo agente**: Ensinar pessoas, verificar processos via Playwright, auditar conformidade

---

## Estrutura de cada POP

Cada POP seguira este formato quando for escrito:

```
POP-XXX — [Nome]
  Objetivo: O que este procedimento realiza
  Trigger: Quando executar (evento que inicia o processo)
  Executor: Quem faz (funcao/pessoa)
  Frequencia: Diario / Por demanda / Mensal / Unica vez
  Opcoes SSW: Telas envolvidas (com links para docs)
  Pre-requisitos: O que precisa estar pronto antes
  Passo-a-passo: Instrucoes detalhadas tela-a-tela
  Verificacao: Checklist de conferencia
  Erros comuns: O que pode dar errado e como resolver
  Verificacao Playwright: Pontos automatizaveis via browser
  POPs relacionados: Dependencias e sequencia
```

---

## Convencoes

- **Status**: JA FAZ (processo que Rafael ja executa) | A IMPLANTAR (nunca fez) | PARCIAL (faz incompleto)
- **Prioridade**: P0 (urgente/risco legal), P1 (alta), P2 (media), P3 (baixa)
- **Executor futuro**: Quem fara quando a operacao estiver madura
- **Verificavel**: Se o agente pode verificar a execucao via Playwright

---

## Visao Geral — 45 POPs em 7 categorias

| Categoria | POPs | Faixa |
|-----------|------|-------|
| A — Implantacao e Cadastros | 10 | POP-A01 a POP-A10 |
| B — Comercial e Precificacao | 5 | POP-B01 a POP-B05 |
| C — Operacional: Emissao | 7 | POP-C01 a POP-C07 |
| D — Operacional: Transporte e Entrega | 7 | POP-D01 a POP-D07 |
| E — Financeiro: Recebiveis | 6 | POP-E01 a POP-E06 |
| F — Financeiro: Pagaveis | 6 | POP-F01 a POP-F06 |
| G — Compliance, Frota e Gestao | 4 | POP-G01 a POP-G04 |
| **TOTAL** | **45** | |

---

# A — IMPLANTACAO E CADASTROS

POPs para configuracao inicial e manutencao de cadastros base.

| POP | Nome | Opcoes SSW | Status | Prioridade | Executor Futuro | Verificavel |
|-----|------|------------|--------|------------|-----------------|-------------|
| A01 | Cadastrar cliente novo | 483, 384 | JA FAZ | P1 | Jessica/Rafael | Sim |
| A02 | Cadastrar unidade parceira (terceiro) | 401 | JA FAZ | P1 | Rafael | Sim |
| A03 | Cadastrar cidades atendidas | 402 | JA FAZ | P1 | Rafael | Sim |
| A04 | Cadastrar rotas | 403 | JA FAZ | P2 | Rafael | Sim |
| A05 | Cadastrar fornecedor/transportadora | 478 | JA FAZ | P1 | Rafael | Sim |
| A06 | Cadastrar custos/comissoes (subcontratacao) | 408 | JA FAZ | P1 | Rafael | Sim |
| A07 | Cadastrar tabelas de preco por rota | 420 | JA FAZ | P1 | Rafael | Sim |
| A08 | Cadastrar veiculo | 026 | PARCIAL | P2 | Rafael | Sim |
| A09 | Cadastrar motorista | 028 | PARCIAL | P2 | Rafael | Sim |
| A10 | Implantar nova rota completa | 401→402→403→478→408→420 | JA FAZ | P1 | Rafael | Sim |

### Detalhamento

**POP-A01 — Cadastrar cliente novo**
- **Trigger**: Novo cliente aprovado comercialmente
- **Opcoes**: 483 (dados cadastrais) + 384 (parametros de faturamento: tipo A/M, periodicidade, banco, separacao faturas, entregador, prazo vencimento, e-mail para fatura)
- **Ponto critico**: Sem 384 configurado, o faturamento nao funciona corretamente
- **Verificacao Playwright**: Consultar cliente na 483, verificar dados preenchidos na 384

**POP-A02 — Cadastrar unidade parceira (terceiro)**
- **Trigger**: Nova transportadora parceira ou nova filial de parceiro existente
- **Dados necessarios**: Sigla IATA da cidade, dados da transportadora (endereco, telefone), dados do seguro ESSOR, conta bancaria CarVia, dados fiscais CarVia
- **Opcoes**: 401 (Tipo = T - Terceiro)
- **Regra CarVia**: Cada filial de transportadora parceira = uma unidade T com sigla IATA

**POP-A03 — Cadastrar cidades atendidas**
- **Trigger**: Apos criar unidade parceira (A02) ou ampliar area de atendimento
- **Dados necessarios**: Lista de cidades da transportadora, polos (P/R/I), lead times
- **Fonte dos dados**: Vinculos do Sistema Fretes (app Nacom)
- **Opcoes**: 402

**POP-A04 — Cadastrar rotas**
- **Trigger**: Nova unidade parceira criada
- **Opcoes**: 403 (origem = CAR, destino = sigla do parceiro, distancia, UFs percurso)
- **Dado critico**: Distancia e UFs percurso (necessarias para MDF-e e calculo de frete)

**POP-A05 — Cadastrar fornecedor/transportadora**
- **Trigger**: Nova transportadora subcontratada
- **Opcoes**: 478 (CNPJ, razao social, dados bancarios do fornecedor, CCF ativa S/N)
- **Ponto critico**: CCF (Conta Corrente Fornecedor) deve estar ativa para controle de pagamentos

**POP-A06 — Cadastrar custos/comissoes**
- **Trigger**: Apos cadastrar fornecedor (A05) e definir condicoes comerciais
- **Dados necessarios**: Tabela de precos da transportadora parceira (Sistema Fretes = fonte de verdade)
- **Opcoes**: 408
- **Regra CarVia**: Tabela 408 = copia exata do Sistema Fretes

**POP-A07 — Cadastrar tabelas de preco por rota**
- **Trigger**: Apos cadastrar rota (A04) e custos (A06)
- **Opcoes**: 420 (tabela por rota)
- **Regra CarVia**: 3 tabelas por unidade parceira (CARP-[SIGLA]P, CARP-[SIGLA]R, CARP-[SIGLA]I)
- **Ponto critico**: Preco de venda CarVia = custo do parceiro (408) + margem

**POP-A08 — Cadastrar veiculo**
- **Trigger**: Novo veiculo proprio ou agregado que fara cargas diretas
- **Opcoes**: 026 (placa, RNTRC, tipo, proprietario, capacidade)
- **Ponto critico**: RNTRC invalido = SEFAZ rejeita MDF-e

**POP-A09 — Cadastrar motorista**
- **Trigger**: Novo motorista proprio ou agregado
- **Opcoes**: 028 (CPF, CNH, validade, vinculo com proprietario/veiculo)

**POP-A10 — Implantar nova rota completa**
- **Trigger**: Cliente solicita frete para cidade/regiao nao cadastrada
- **Processo composto**: A02 → A03 → A04 → A05 → A06 → A07 (nesta ordem)
- **Estimativa de tempo**: 30-60 minutos
- **Fonte de dados**: Sistema Fretes (app Nacom) para tabelas, vinculos e lead times
- **Verificacao Playwright**: Simular cotacao (002) para a nova rota e confirmar preco

---

# B — COMERCIAL E PRECIFICACAO

POPs para cotacao, formacao de precos e analise comercial.

| POP | Nome | Opcoes SSW | Status | Prioridade | Executor Futuro | Verificavel |
|-----|------|------------|--------|------------|-----------------|-------------|
| B01 | Cotar frete para cliente | 002 | JA FAZ | P1 | Jessica | Sim |
| B02 | Entender formacao de preco (simulacao) | 004, 062, 903 | A IMPLANTAR | P1 | Rafael | Sim |
| B03 | Configurar parametros de frete | 062 | A IMPLANTAR | P1 | Rafael | Sim |
| B04 | Analisar resultado por CTRC | 101 | A IMPLANTAR | P2 | Rafael | Sim |
| B05 | Gerar relatorios gerenciais | 056 | A IMPLANTAR | P2 | Rafael/Jessica | Sim |

### Detalhamento

**POP-B01 — Cotar frete para cliente**
- **Trigger**: Jessica recebe demanda de frete
- **Fluxo**: Analisar no Sistema Fretes → Cotar no SSW (002) → Retornar preco
- **Opcoes**: 002 (cotacao), pode usar simulacao da 004 para fretes mais complexos
- **Verificacao Playwright**: Acessar 002, inserir parametros, capturar resultado

**POP-B02 — Entender formacao de preco (simulacao)**
- **Trigger**: Simulacao na opcao 004 nao calcula corretamente ou resultado inesperado
- **Opcoes**: 004 (simular), 062 (parametros de frete), 903 (parametros gerais que afetam calculo)
- **Objetivo**: Documentar TODOS os componentes do preco: frete peso, frete valor, GRIS, despacho, pedagio, TDE, ICMS, etc.
- **Ponto critico**: Este POP resolvera o problema recorrente de simulacao incorreta

**POP-B03 — Configurar parametros de frete**
- **Trigger**: Setup inicial ou ajuste de parametros de calculo
- **Opcoes**: 062 (desconto maximo, resultado minimo, custos adicionais)
- **Ponto critico**: Rafael nao conhece esta opcao — pode ser a causa da simulacao incorreta

**POP-B04 — Analisar resultado por CTRC**
- **Trigger**: Analise de lucratividade (mensal ou por demanda)
- **Opcoes**: 101 (resultado: receita - custos - comissoes = resultado %)
- **Verificacao Playwright**: Acessar 101, filtrar por periodo, capturar resultado

**POP-B05 — Gerar relatorios gerenciais**
- **Trigger**: Analise de gestao (diaria/semanal/mensal)
- **Opcoes**: 056 (40+ relatorios, 6 objetivos)
- **Relatorios prioritarios CarVia**: Situacao geral, CTRCs atrasados, entregas pendentes, faturamento

---

# C — OPERACIONAL: EMISSAO

POPs para emissao de documentos fiscais e operacionais.

| POP | Nome | Opcoes SSW | Status | Prioridade | Executor Futuro | Verificavel |
|-----|------|------------|--------|------------|-----------------|-------------|
| C01 | Emitir CTe — frete fracionado | 004, 007 | JA FAZ | P1 | Rafael/Jaqueline | Sim |
| C02 | Emitir CTe — carga direta | 004, 007 | JA FAZ | P1 | Rafael | Sim |
| C03 | Emitir CTe complementar | 007 | A IMPLANTAR | P2 | Rafael | Sim |
| C04 | Registrar custos extras (TDE, diaria, pernoite) | 459 | A IMPLANTAR | P2 | Rafael | Sim |
| C05 | Imprimir/reimprimir CTe | 007 | JA FAZ | P1 | Rafael | Sim |
| C06 | Cancelar CTe | 007 | A IMPLANTAR | P2 | Rafael | Sim |
| C07 | Carta de correcao CTe | 007 | A IMPLANTAR | P2 | Rafael | Sim |

### Detalhamento

**POP-C01 — Emitir CTe — frete fracionado**
- **Trigger**: Frete fracionado aprovado, NF do cliente disponivel
- **Fluxo atual**:
  1. Alterar unidade para CAR
  2. Opcao 004: tipo Normal (N), placa "ARMAZEM"
  3. Digitar chave NF-e (44 digitos)
  4. Clicar Simular → verificar valores
  5. Ajustar se necessario
  6. Clicar Play (gravar) → confirmar → nao enviar email
  7. Clicar "Enviar CT-es ao SEFAZ"
- **Verificacao Playwright**: Confirmar CTe autorizado na 007, verificar status SEFAZ

**POP-C02 — Emitir CTe — carga direta**
- **Trigger**: Carga direta aprovada, NF disponivel, veiculo/motorista definidos
- **Diferenca do fracionado**:
  - Placa de coleta = placa REAL do veiculo (nao "ARMAZEM")
  - Requer cadastro previo do motorista (028) e veiculo (026)
  - Apos emissao: criar romaneio (POP-D02) e manifesto (POP-D03)
- **Sequencia obrigatoria**: CTe → Romaneio → MDF-e → EMBARQUE (regra da seguradora)
- **Verificacao Playwright**: CTe autorizado + placa correta

**POP-C03 — Emitir CTe complementar**
- **Trigger**: Necessidade de complementar valor, peso ou imposto de CTe ja emitido
- **Opcoes**: 007 (funcao CTe complementar)
- **Docs SSW**: operacional/007-emissao-cte-complementar.md
- **Cenarios**: Diferenca de frete, complemento de ICMS, ajuste de peso

**POP-C04 — Registrar custos extras**
- **Trigger**: Cobranca de TDE, diaria de caminhao, pernoite, taxa de agendamento, etc.
- **Opcoes**: 459 (relacao de adicionais — debitos e creditos disponiveis para faturar)
- **Docs SSW**: financeiro/459-relacao-adicionais.md
- **Ponto critico**: Custos extras nao cadastrados = nao aparecem na fatura

**POP-C05 — Imprimir/reimprimir CTe**
- **Trigger**: Necessidade de copia do DACTe
- **Opcoes**: 007 (funcao impressao)

**POP-C06 — Cancelar CTe**
- **Trigger**: CTe emitido com erro que nao pode ser corrigido por carta de correcao
- **Opcoes**: 007 (cancelamento — prazo SEFAZ de 7 dias)
- **Risco**: Cancelamento apos embarque = problema com seguradora

**POP-C07 — Carta de correcao CTe**
- **Trigger**: Dados do CTe com erro menor (endereco, CFOP, etc.)
- **Opcoes**: 007
- **Restricao**: Nao altera valores, CNPJ ou chave de acesso

---

# D — OPERACIONAL: TRANSPORTE E ENTREGA

POPs para movimentacao de cargas, romaneio, manifesto e controle de entregas.

| POP | Nome | Opcoes SSW | Status | Prioridade | Executor Futuro | Verificavel |
|-----|------|------------|--------|------------|-----------------|-------------|
| D01 | Contratar veiculo para carga direta | 072 | A IMPLANTAR | P1 | Rafael | Sim |
| D02 | Criar romaneio de entregas | 035 | PARCIAL | P1 | Rafael | Sim |
| D03 | Criar manifesto e emitir MDF-e | 020, 025 | A IMPLANTAR | **P0** | Rafael | Sim |
| D04 | Registrar chegada de veiculo | 030 | A IMPLANTAR | P2 | Stephanie | Sim |
| D05 | Registrar baixa de entrega | 038 | A IMPLANTAR | P1 | Stephanie | Sim |
| D06 | Registrar ocorrencias | 033, 038, 108 | A IMPLANTAR | P1 | Stephanie | Sim |
| D07 | Controlar comprovantes de entrega | 040, 049, 428 | A IMPLANTAR | P2 | Stephanie | Sim |

### Detalhamento

**POP-D01 — Contratar veiculo para carga direta**
- **Trigger**: Carga direta aprovada, veiculo/motorista definidos
- **Opcoes**: 072 (placa, CEP origem, unidade destino, calcula distancia, gera CIOT, vale pedagio)
- **Docs SSW**: operacional/072-contratacao-de-veiculo-de-transferencia.md
- **O que e**: Formalizacao do contrato de transporte com o veiculo. Gera CTRB (Conhecimento de Transporte para terceiros), calcula custo, alimenta a CCF (conta corrente do fornecedor)
- **Tipos**:
  - Carreteiro: CTRB + RPA + CIOT por viagem + retencoes INSS/IR
  - Agregado: OS + CIOT mensal, acerto na CCF
  - Frota propria: CTRB para adiantamentos, sem CIOT
- **Ponto critico**: Sem 072, nao ha registro formal do custo da carga direta

**POP-D02 — Criar romaneio de entregas**
- **Trigger**: CTe emitido para carga direta, veiculo definido
- **Opcoes**: 035 (veiculo, motorista, CTRCs, data entrega)
- **Docs SSW**: operacional/035-romaneio-entregas.md
- **Sequencia**: CTe autorizado → Romaneio (035) → MDF-e (020/025) → Embarque
- **Verificacao Playwright**: Romaneio criado com CTRCs corretos

**POP-D03 — Criar manifesto e emitir MDF-e**
- **Trigger**: Romaneio criado, carga direta interestadual
- **Opcoes**: 020 (manifesto operacional) + 025 (saida de veiculo — emissao MDF-e)
- **Docs SSW**: operacional/020-manifesto-carga.md, operacional/025-saida-veiculo.md
- **OBRIGATORIO para**: Qualquer transporte interestadual
- **Sequencia no SSW**:
  1. Opcao 020: Criar manifesto, carregar CTRCs, informar placa, destino
  2. Opcao 025: Emitir MDF-e ao SEFAZ, impressao DAMDFE
- **Risco se nao fizer**: Multa fiscal + seguro pode nao cobrir sinistro
- **Verificacao Playwright**: MDF-e autorizado no SEFAZ, status "Enviado"

**POP-D04 — Registrar chegada de veiculo**
- **Trigger**: Transportadora parceira confirma entrega na base destino
- **Opcoes**: 030 (captura chegada, encerra MDF-e automaticamente)
- **Contexto CarVia**: Relevante quando CarVia usar transferencias entre bases parceiras
- **Verificacao Playwright**: Status do manifesto = "Chegada registrada"

**POP-D05 — Registrar baixa de entrega**
- **Trigger**: Confirmacao de entrega ao destinatario final
- **Opcoes**: 038 (por romaneio ou digitacao — informar recebedor, data, ocorrencia)
- **Contexto CarVia**: Fundamental para fechar o ciclo operacional
- **Verificacao Playwright**: CTRC com status "Entregue" ou "Baixado"

**POP-D06 — Registrar ocorrencias**
- **Trigger**: Qualquer evento que afete a entrega (atraso, avaria, extravio, reentrega, devolucao)
- **Opcoes**: 033 (ocorrencias de transferencia), 038 (ocorrencias de entrega), 108 (instrucoes/resolucao)
- **Regra SSW**: Nenhuma ocorrencia deve ficar pendente sem instrucoes ao final do dia
- **Verificacao Playwright**: Consultar ocorrencias pendentes

**POP-D07 — Controlar comprovantes de entrega**
- **Trigger**: Apos baixa de entrega
- **Opcoes**: 040 (capa de comprovantes), 049 (controle), 428 (arquivamento)
- **Importancia**: Prova juridica de entrega, necessario para contestacao de clientes, seguro, auditoria
- **Contexto CarVia**: Rafael nao entendia a importancia — comprovante e prova de que a mercadoria foi entregue ao destinatario correto. Sem ele, cliente pode alegar que nao recebeu

---

# E — FINANCEIRO: RECEBIVEIS

POPs para faturamento, cobranca e recebimento.

| POP | Nome | Opcoes SSW | Status | Prioridade | Executor Futuro | Verificavel |
|-----|------|------------|--------|------------|-----------------|-------------|
| E01 | Verificar CTRCs disponiveis para faturamento | 435 | A IMPLANTAR | P1 | Jaqueline | Sim |
| E02 | Faturar manualmente | 437 | JA FAZ | P1 | Jaqueline | Sim |
| E03 | Faturar automaticamente (geral) | 436 | A IMPLANTAR | P2 | Jaqueline | Sim |
| E04 | Emitir cobranca bancaria (boleto) | 444 | A IMPLANTAR | P2 | Jaqueline | Sim |
| E05 | Liquidar/baixar fatura recebida | 048, 458 | A IMPLANTAR | P1 | Jaqueline | Sim |
| E06 | Manter faturas (prorrogar, protestar, baixar) | 457 | A IMPLANTAR | P2 | Jaqueline | Sim |

### Detalhamento

**POP-E01 — Verificar CTRCs disponiveis para faturamento**
- **Trigger**: Antes de faturar (diario ou por demanda)
- **Opcoes**: 435 (lista CTRCs disponiveis, verifica e-mail do cliente, bloqueios)
- **Docs SSW**: financeiro/435-pre-faturamento.md
- **Verificacao Playwright**: Acessar 435, verificar lista, identificar pendencias

**POP-E02 — Faturar manualmente**
- **Trigger**: CTRCs prontos para faturamento
- **Fluxo atual**: Alterar unidade para MTZ → Opcao 437 → Apontar documentos → Selecionar → Gerar fatura
- **Opcoes**: 437
- **Ponto critico**: Hoje Rafael fatura e envia para Jessica que envia ao cliente. Sem boleto, sem cobranca bancaria. Cliente deposita na conta
- **Verificacao Playwright**: Fatura gerada com numero, valor correto

**POP-E03 — Faturar automaticamente (geral)**
- **Trigger**: Setup de faturamento automatico (quando volume justificar)
- **Opcoes**: 436 (faturamento geral — agrupa CTRCs por regras do cliente na 384)
- **Pre-requisito**: 384 configurado para cada cliente (tipo A, periodicidade, separacao, banco)
- **Docs SSW**: financeiro/436-faturamento-geral.md

**POP-E04 — Emitir cobranca bancaria (boleto)**
- **Trigger**: Fatura gerada, cliente nao usa deposito direto
- **Opcoes**: 444 (gera arquivo remessa CNAB 400 ou API para banco)
- **Pre-requisito**: Banco e carteira cadastrados na opcao 904, parametrizados na opcao 384 do cliente
- **Docs SSW**: financeiro/444-cobranca-bancaria.md

**POP-E05 — Liquidar/baixar fatura recebida**
- **Trigger**: Cliente pagou (deposito, boleto, transferencia)
- **Opcoes**: 048 (liquidacao a vista), 458 (caixa — registro de recebimentos)
- **Docs SSW**: financeiro/048-liquidacao-a-vista.md
- **Ponto critico**: Sem liquidacao, o CTe fica "em aberto" e polui relatorios

**POP-E06 — Manter faturas**
- **Trigger**: Fatura vencida, cliente solicita prorrogacao, necessidade de protesto
- **Opcoes**: 457 (instrucoes: abater, prorrogar, protestar, sustar, baixar)
- **Docs SSW**: financeiro/457-manutencao-faturas.md

---

# F — FINANCEIRO: PAGAVEIS

POPs para contas a pagar, CCF e conciliacao.

| POP | Nome | Opcoes SSW | Status | Prioridade | Executor Futuro | Verificavel |
|-----|------|------------|--------|------------|-----------------|-------------|
| F01 | Lancar contas a pagar (despesa) | 475 | A IMPLANTAR | P1 | Jaqueline | Sim |
| F02 | Gerenciar CCF (conta corrente fornecedor) | 486 | A IMPLANTAR | P1 | Jaqueline | Sim |
| F03 | Liquidar/pagar despesa | 476 | A IMPLANTAR | P1 | Jaqueline | Sim |
| F04 | Conciliar banco | 569 | A IMPLANTAR | P1 | Jaqueline | Sim |
| F05 | Registrar bloqueio financeiro de CTRC | 462 | A IMPLANTAR | P2 | Rafael | Sim |
| F06 | Aprovar despesas pendentes | 560 | A IMPLANTAR | P2 | Rafael | Sim |

### Detalhamento

**POP-F01 — Lancar contas a pagar**
- **Trigger**: Receber fatura/NF de transportadora subcontratada ou outra despesa
- **Opcoes**: 475 (programacao de despesas — importar XML SEFAZ ou incluir manualmente)
- **Docs SSW**: financeiro/475-contas-a-pagar.md
- **Fluxo**: CNPJ fornecedor → evento de despesa (503) → dados fiscais → retencoes → gerar lancamento
- **Ponto critico**: Transportadoras subcontratadas que usam SSW podem ter integracao automatica
- **Contexto CarVia**: HOJE nao faz no SSW. Pagamentos sao controlados fora do sistema

**POP-F02 — Gerenciar CCF (conta corrente fornecedor)**
- **Trigger**: Transportadora parceira realiza fretes, acumula creditos/debitos
- **Opcoes**: 486 (debitos: despesas, combustivel. Creditos: CTRB/OS de contratacao 072)
- **Docs SSW**: financeiro/486-conta-corrente-fornecedor.md
- **O que e**: Saldo de cada transportadora parceira — quanto a CarVia deve vs quanto ja pagou
- **Ponto critico**: Sem CCF, nao ha controle de saldo com transportadoras. Risco de pagar a mais ou a menos

**POP-F03 — Liquidar/pagar despesa**
- **Trigger**: Despesa aprovada, data de pagamento
- **Opcoes**: 476 (a vista, cheque, PEF, arquivo bancario)
- **Docs SSW**: financeiro/476-liquidacao-despesas.md

**POP-F04 — Conciliar banco**
- **Trigger**: Diariamente ou ao final do mes
- **Opcoes**: 569 (informar banco/agencia/conta, data, saldo extrato → sistema valida)
- **Pre-requisito**: Todos os lancamentos do periodo registrados (recebiveis + pagaveis)
- **Docs SSW**: contabilidade/569-conciliacao-bancaria.md
- **Efeito colateral**: Periodo conciliado = BLOQUEIO retroativo (nao permite mais alteracoes)
- **Contexto CarVia**: HOJE conciliacao e manual (Rafael calcula). Fundamental para controle

**POP-F05 — Registrar bloqueio financeiro de CTRC**
- **Trigger**: CTRC nao deve ser faturado (pendencia operacional ou comercial)
- **Opcoes**: 462
- **Docs SSW**: referenciado em financeiro/435-pre-faturamento.md (bloqueio aparece na lista 435)

**POP-F06 — Aprovar despesas pendentes**
- **Trigger**: Despesa lancada aguardando aprovacao (se 903 exigir aprovacao centralizada)
- **Opcoes**: 560
- **Docs SSW**: referenciado em financeiro/475-contas-a-pagar.md

---

# G — COMPLIANCE, FROTA E GESTAO

POPs para regras legais, controle de frota e gestao.

| POP | Nome | Opcoes SSW | Status | Prioridade | Executor Futuro | Verificavel |
|-----|------|------------|--------|------------|-----------------|-------------|
| G01 | Sequencia legal obrigatoria (carga direta) | 004→007→035→020→025 | A IMPLANTAR | **P0** | Rafael | Sim |
| G02 | Checklist gerenciadora de risco | Fora SSW + 390 | A IMPLANTAR | **P0** | Rafael | Parcial |
| G03 | Controlar custos de frota | 026, 320, 131, 475 | A IMPLANTAR | P3 | Rafael | Sim |
| G04 | Extrair relatorios para contabilidade | 512, 515, 567 | JA FAZ (contabilidade) | P3 | Contabilidade | Sim |

### Detalhamento

**POP-G01 — Sequencia legal obrigatoria (carga direta)**
- **Trigger**: TODA carga direta (caminhao proprio, agregado ou transportadora)
- **Sequencia INVIOLAVEL**:
  1. Cadastrar motorista (028) e veiculo (026) — se nao cadastrados
  2. Consultar gerenciadora de risco (fora SSW) — motorista/veiculo aprovados?
  3. Emitir CTe (004 → 007) — **ANTES do embarque**
  4. Contratar veiculo (072) — gera CIOT se aplicavel
  5. Criar romaneio (035)
  6. Criar manifesto (020) + emitir MDF-e (025) — se interestadual
  7. SO ENTAO: embarcar mercadoria
- **Risco se violar**: Sinistro sem cobertura do seguro (ESSOR), multa ANTT (CIOT), multa fiscal (MDF-e)
- **Regras especificas da seguradora (a confirmar)**:
  - CT-e DEVE estar autorizado ANTES do inicio do transporte
  - MDF-e DEVE estar ativo durante todo o transporte
  - Motorista e veiculo DEVEM estar aprovados na gerenciadora
  - [CONFIRMAR] Regras sobre NF de outro UF (ex: NF emitida no RJ, operacao iniciando em SP)
- **Verificacao Playwright**: Verificar que CT-e tem data/hora anterior ao embarque, MDF-e esta autorizado

**POP-G02 — Checklist gerenciadora de risco**
- **Trigger**: TODA carga direta, antes do embarque
- **Processo (fora SSW)**: Consultar motorista e veiculo na gerenciadora
- **Dados SSW necessarios**: Veiculo (026), motorista (028), rota (403)
- **Opcao SSW relacionada**: 390 (PGR — Programa de Gerenciamento de Risco)
- **Ponto critico**: Mesmo que a operacao seja pequena, a gerenciadora exige consulta

**POP-G03 — Controlar custos de frota**
- **Trigger**: Periodico (mensal) ou por evento (abastecimento, manutencao)
- **Opcoes**: 026 (cadastro veiculos), 320 (abastecimento), 131 (OS manutencao), 475 (despesas)
- **Contexto CarVia**: 2 caminhoes proprios (VUC + Truck). Hoje sem controle no SSW

**POP-G04 — Extrair relatorios para contabilidade**
- **Trigger**: Mensal (obrigacoes acessorias)
- **Opcoes**: 512 (SPED Fiscal), 515 (SPED Contribuicoes), 567 (fechamento fiscal)
- **Contexto CarVia**: Contabilidade externa ja faz isso. POP para documentar o que ela extrai

---

# MAPA DE DEPENDENCIAS ENTRE POPs

```
SETUP (uma vez por rota/cliente/parceiro)
A01 Cadastrar cliente ──────────────────────────────────────────→ E02 Faturar
A10 Implantar rota ─┐
  A02 Unidade       │
  A03 Cidades       ├─→ B01 Cotar ──→ C01/C02 Emitir CTe ──→ D02 Romaneio
  A04 Rotas         │                                            ↓
  A05 Fornecedor    │                                     D03 Manifesto/MDF-e
  A06 Custos        │                                            ↓
  A07 Tabelas      ─┘                                    G01 Sequencia legal
A08 Veiculo  ──→ D01 Contratar ──→ D03 Manifesto               ↓
A09 Motorista ─┘                                          EMBARQUE
                                                               ↓
OPERACIONAL DIARIO                                      D05 Baixa entrega
C01 CTe fracionado ──→ E01 Pre-fat ──→ E02 Faturar ──→ E05 Liquidar
C02 CTe direto ──→ D02 Romaneio ──→ D03 MDF-e ──→ D05 Baixa ──→ E01 Pre-fat
                                                               ↓
FINANCEIRO                                              D06 Ocorrencias
E02 Faturar ──→ E04 Boleto ──→ E05 Liquidar ──→ F04 Conciliar
F01 Contas pagar ──→ F02 CCF ──→ F03 Liquidar ──→ F04 Conciliar
D01 Contratar ──→ F02 CCF (credito automatico)
```

---

# PRIORIZACAO PARA ESCRITA DOS POPs

## Onda 1 — Urgente / Risco Legal (6 POPs)

| # | POP | Justificativa |
|---|-----|---------------|
| 1 | **G01** — Sequencia legal obrigatoria | Risco de sinistro sem cobertura |
| 2 | **D03** — Manifesto/MDF-e | Obrigatorio interestadual, nunca fizeram |
| 3 | **G02** — Checklist gerenciadora de risco | Complemento do G01 |
| 4 | **C01** — Emitir CTe fracionado | Processo mais frequente, padronizar |
| 5 | **C02** — Emitir CTe carga direta | Segundo mais frequente, mais complexo |
| 6 | **D02** — Romaneio de entregas | Pre-requisito do MDF-e |

## Onda 2 — Operacao Financeira (7 POPs)

| # | POP | Justificativa |
|---|-----|---------------|
| 7 | **E02** — Faturar manualmente | Ja faz, precisa padronizar |
| 8 | **E01** — Pre-faturamento | Verificacao antes de faturar |
| 9 | **E05** — Liquidar fatura | Fechar ciclo financeiro |
| 10 | **F01** — Contas a pagar | Pagar transportadoras no SSW |
| 11 | **F02** — CCF | Controle de saldo com parceiros |
| 12 | **F03** — Liquidar despesa | Complemento do F01 |
| 13 | **D01** — Contratar veiculo | Formalizar custos de carga direta |

## Onda 3 — Cadastros e Comercial (8 POPs)

| # | POP | Justificativa |
|---|-----|---------------|
| 14 | **A10** — Implantar nova rota | Processo frequente, complexo, 10 passos |
| 15 | **A01** — Cadastrar cliente | Base para faturamento |
| 16 | **B01** — Cotar frete | Jessica precisa aprender |
| 17 | **B02** — Formacao de preco | Resolver simulacao incorreta |
| 18 | **B03** — Parametros de frete | Complemento do B02 |
| 19 | **A02** — Unidade parceira | Sub-processo do A10 |
| 20 | **A05** — Fornecedor | Sub-processo do A10 |
| 21 | **A06** — Custos/comissoes | Sub-processo do A10 |

## Onda 4 — Controle e Gestao (10 POPs)

| # | POP | Justificativa |
|---|-----|---------------|
| 22 | **D05** — Baixa de entrega | Fechar ciclo operacional |
| 23 | **D06** — Ocorrencias | Registrar problemas |
| 24 | **D07** — Comprovantes de entrega | Prova juridica |
| 25 | **F04** — Conciliacao bancaria | Controle financeiro |
| 26 | **B04** — Resultado por CTRC | Lucratividade |
| 27 | **B05** — Relatorios gerenciais | Visao de gestao |
| 28 | **E04** — Cobranca bancaria | Profissionalizar |
| 29 | **A08** — Cadastrar veiculo | Complemento |
| 30 | **A09** — Cadastrar motorista | Complemento |
| 31 | **D04** — Chegada de veiculo | Quando tiver transferencias |

## Onda 5 — Complementares (14 POPs)

| # | POP | Justificativa |
|---|-----|---------------|
| 32-45 | C03-C07, A03, A04, A07, E03, E06, F05, F06, G03, G04 | Processos menos frequentes ou ja cobertos indiretamente |

---

# METRICAS

| Metrica | Valor |
|---------|-------|
| Total de POPs definidos | 45 |
| Status JA FAZ | 12 |
| Status PARCIAL | 3 |
| Status A IMPLANTAR | 30 |
| Prioridade P0 (urgente) | 2 |
| Prioridade P1 (alta) | 22 |
| Prioridade P2 (media) | 15 |
| Prioridade P3 (baixa) | 6 |
| Verificaveis via Playwright | 44 (98%) |
| Ondas de escrita | 5 |
| POPs na Onda 1 (urgente) | 6 |

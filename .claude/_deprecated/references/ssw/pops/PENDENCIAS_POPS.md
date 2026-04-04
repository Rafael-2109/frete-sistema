# Pendencias dos POPs — Acoes Necessarias

> **Criado em**: 2026-02-15
> **Objetivo**: Centralizar todas as acoes pendentes identificadas durante a escrita dos POPs.
> **Regra**: Cada pendencia tambem esta marcada com `[CONFIRMAR]` ou `[DEFINIR]` dentro do POP correspondente.

---

## Status Geral

| # | Pendencia | POP(s) | Responsavel | Urgencia | Status |
|---|-----------|--------|-------------|----------|--------|
| 1 | Confirmar regras ESSOR de cobertura do seguro | G01, G02 | Rafael | **URGENTE** | Pendente |
| 2 | Definir quem registra chegada (030) para parceiros tipo T | D03 | Rafael | Alta | Pendente |
| 3 | Verificar regra de NF emitida em UF diferente da operacao | G01, C02 | Rafael + ESSOR | Alta | Pendente |
| 4 | Confirmar limites de valor PGR (390) com ESSOR | G02 | Rafael | Alta | Pendente |
| 5 | Confirmar se gerenciadora exige consulta para valores baixos | G02 | Rafael + ESSOR | Media | Pendente |
| 6 | Cadastrar eventos de despesa (503) para CarVia | F01 | Rafael | Alta | Pendente |
| 7 | Ativar CCF nos fornecedores existentes (478) | F02 | Rafael | Alta | Pendente |
| 8 | Configurar parametros de faturamento por cliente (384) | E01, E02 | Rafael | Alta | Pendente |
| 9 | Cadastrar tabelas de remuneracao (399/499) para veiculos | D01 | Rafael | Media | Pendente |
| 10 | Definir fornecedor de Vale Pedagio (TARGET, SEM PARAR, etc.) | D01 | Rafael | Media | Pendente |
| 11 | Cadastrar conta bancaria/caixa CarVia (904) | E05, F03 | Rafael | Alta | Pendente |
| 12 | Investigar opcao 062 (parametros de frete) — Rafael nao conhece | B02, B03 | Rafael | **URGENTE** | Pendente |
| 13 | Configurar limites de cotacao por rota (469) | B01, B03 | Rafael | Alta | Pendente |
| 14 | Configurar cubagem por cliente (423) | B01, B03 | Rafael | Media | Pendente |
| 15 | Cobrar comprovantes de entrega dos parceiros tipo T | D07 | Stephanie | Alta | Pendente |
| 16 | Confirmar campos do formulario de cadastro de motorista (028) | A09 | Rafael | Baixa | Pendente |
| 17 | Implantar rotina diaria de monitoramento relatorios 011/031 (opcao 056) | B04, B05 | Rafael | Alta | Pendente |

---

## Detalhamento

### PEND-01 — Regras ESSOR de Cobertura do Seguro

**POPs afetados**: G01 (etapa 2), G02 (secao "Regras da Seguradora")

**O que confirmar com a ESSOR**:
1. CT-e DEVE estar autorizado ANTES do inicio do transporte?
2. MDF-e DEVE estar ativo durante todo o transporte interestadual?
3. Motorista DEVE estar aprovado na gerenciadora ANTES do embarque?
4. Veiculo DEVE estar aprovado na gerenciadora ANTES do embarque?
5. Rastreador DEVE estar ativo durante todo o transporte?
6. Qual o prazo maximo entre autorizacao do CT-e e inicio do transporte?
7. Quais situacoes invalidam a cobertura do seguro?

**Como resolver**: Rafael ligar para ESSOR e solicitar documento formal com regras de cobertura. Documentar resposta nos POPs G01 e G02.

**Impacto se nao resolver**: Operacao continua "por intuicao" — risco de sinistro sem cobertura permanece.

---

### PEND-02 — Quem Registra Chegada (030) para Parceiros Tipo T

**POP afetado**: D03 (parte 3 — pos-embarque)

**Situacao**: Quando a CarVia envia carga direta para um parceiro tipo T (ex: Alemar em Campo Grande), alguem precisa registrar a chegada na opcao 030 para encerrar o MDF-e no SEFAZ.

**Opcoes**:
- **A)** Parceiro registra no SSW dele (se usar SSW) — verificar se parceiros CarVia usam SSW
- **B)** Rafael registra manualmente quando recebe confirmacao de entrega do parceiro
- **C)** Aguardar encerramento automatico do SSW (29 dias) — NAO recomendado, pois nao e forma correta

**Como resolver**: Rafael definir qual opcao adotar. Se parceiro usa SSW, verificar se chegada e automatica. Se nao, definir processo manual.

**Impacto se nao resolver**: MDF-es ficam abertos por 29 dias ate encerramento automatico. Pode causar rejeicao de novos MDF-es (duplicidade) e imprecisao nos relatorios.

---

### PEND-03 — NF Emitida em UF Diferente da Operacao

**POPs afetados**: G01 (cenarios especiais), C02 (erros comuns)

**Situacao**: Cliente emite NF em uma UF (ex: RJ) mas a carga esta fisicamente em outra UF (ex: SP, no CD da Nacom em Santana de Parnaiba). A CarVia emite CT-e em SP.

**Perguntas**:
1. A CarVia pode emitir CT-e para NF de outro UF?
2. Qual CFOP usar?
3. Tem implicacao tributaria (ICMS diferencial)?
4. O seguro cobre transporte quando NF e de UF diferente da origem?

**Como resolver**: Consultar contabilidade externa (que tem experiencia com 100+ transportadoras SSW) e confirmar com ESSOR sobre cobertura do seguro.

**Impacto se nao resolver**: Possivel emissao de CT-e com tributacao incorreta ou seguro sem cobertura.

---

### PEND-04 — Limites de Valor PGR (390)

**POP afetado**: G02 (etapa 4)

**Situacao**: A opcao 390 define faixas de valor de mercadoria e requisitos correspondentes (rastreador, isca, escolta). A CarVia nao sabe quais sao os limites definidos pela ESSOR.

**Como resolver**: Consultar ESSOR para obter tabela de faixas de valor e requisitos. Configurar na opcao 390.

**Impacto se nao resolver**: Carga pode sair sem requisitos necessarios (ex: sem isca para carga de alto valor) — seguro pode nao cobrir.

---

### PEND-05 — Consulta Obrigatoria para Valores Baixos

**POP afetado**: G02 (etapa 4)

**Situacao**: Para cargas de baixo valor (ex: MotoChefe com 1 caixa de 60kg valendo R$ 2.000), a gerenciadora pode dispensar consulta formal. Mas nao ha confirmacao.

**Como resolver**: Perguntar a ESSOR se existe valor minimo abaixo do qual a consulta a gerenciadora e dispensavel.

**Impacto se nao resolver**: Operacao pode estar fazendo consultas desnecessarias (perda de tempo) ou deixando de fazer consultas obrigatorias (risco).

---

### PEND-06 — Cadastrar Eventos de Despesa (503)

**POP afetado**: F01 (etapa 2)

**Situacao**: A opcao 475 (Contas a Pagar) exige um "Evento" que classifica a despesa (financeiro, fiscal, contabil). A CarVia nunca usou contas a pagar no SSW, entao os eventos nao estao configurados.

**Eventos tipicos a cadastrar**:
1. Frete subcontratado (pagamento a transportadoras parceiras)
2. Combustivel (frota propria)
3. Pedagio (cargas diretas)
4. Manutencao (veiculos proprios)
5. Seguro (ESSOR — mensal)
6. Aluguel / administrativo

**Como resolver**: Rafael acessar opcao 503 e cadastrar os eventos acima. Cada evento define tratamento fiscal, contabil e financeiro.

**Impacto se nao resolver**: Impossivel lancar despesas no SSW (opcao 475 exige evento).

---

### PEND-07 — Ativar CCF nos Fornecedores Existentes (478)

**POP afetado**: F02 (pre-requisito)

**Situacao**: Para a CCF funcionar, cada fornecedor precisa ter o campo "CCF ativa = S" na opcao 478. Fornecedores ja cadastrados provavelmente estao com CCF desativada.

**Como resolver**: Rafael acessar opcao 478, listar fornecedores ativos e ativar CCF em cada um (especialmente transportadoras parceiras).

**Impacto se nao resolver**: Despesas nao debitam CCF, contratacoes (072) nao creditam CCF. Controle de saldo com parceiros impossivel.

---

### PEND-08 — Configurar Parametros de Faturamento por Cliente (384)

**POPs afetados**: E01 (pre-faturamento), E02 (faturamento manual)

**Situacao**: A opcao 384 define tipo de faturamento (A/M), periodicidade, banco, e-mail, separacao de faturas e prazo. Sem 384 configurada, o faturamento nao funciona corretamente e e-mails nao sao enviados.

**Como resolver**: Para cada cliente ativo, acessar opcao 384 e configurar:
- Tipo = M (manual) — padrao CarVia atual
- Prazo de vencimento
- E-mail para envio automatico
- Banco/carteira (999 = cobranca propria)

**Impacto se nao resolver**: Faturas sem vencimento, sem envio por e-mail, relatorios de pre-faturamento incompletos.

---

### PEND-09 — Cadastrar Tabelas de Remuneracao (399/499)

**POP afetado**: D01 (etapa 3)

**Situacao**: A opcao 072 pode sugerir valor automaticamente se existirem tabelas de remuneracao por rota (399) ou por veiculo (499). Sem estas tabelas, o valor precisa ser informado manualmente a cada contratacao.

**Como resolver**: Quando o volume de cargas diretas justificar, cadastrar tabelas por rota (399) para os destinos mais frequentes.

**Impacto se nao resolver**: Valor de contratacao informado manualmente (nao e bloqueante, apenas menos produtivo).

---

### PEND-10 — Definir Fornecedor de Vale Pedagio

**POP afetado**: D01 (etapa 5)

**Situacao**: Para cargas diretas com terceiros (carreteiros/agregados), o Vale Pedagio e obrigatorio (Resolucao ANTT 2.885/2008). A CarVia precisa definir qual fornecedor usar (TARGET, SEM PARAR, REPOM, etc.) e se usara geracao eletronica integrada ao SSW ou processo manual.

**Como resolver**: Rafael avaliar fornecedores habilitados ANTT e contratar um. Verificar integracao com opcao 072.

**Impacto se nao resolver**: Cargas diretas com terceiros ficam sem Vale Pedagio — multa eletronica em radares ANTT.

---

### PEND-11 — Cadastrar Conta Bancaria/Caixa CarVia (904)

**POPs afetados**: E05 (liquidar fatura), F03 (liquidar despesa)

**Situacao**: Para registrar recebimentos (liquidacao de faturas) e pagamentos (liquidacao de despesas), e necessario ter contas bancarias e caixas cadastrados na opcao 904.

**Como resolver**: Rafael acessar opcao 904 e cadastrar:
- Conta(s) bancaria(s) da CarVia (banco, agencia, conta)
- Caixa (se controle de dinheiro em especie)

**Impacto se nao resolver**: Impossivel liquidar faturas e despesas no SSW.

---

### PEND-12 — Investigar Opcao 062 (Parametros de Frete)

**POPs afetados**: B02 (diagnostico), B03 (etapa 4 inteira)

**Situacao**: A opcao 062 e referenciada na documentacao SSW como "parametros de frete" e como pre-requisito na opcao 101 (Resultado CTRC): "Parametros de frete (Opcao 062): desconto maximo, resultado comercial minimo". Porem, NAO existe documentacao dedicada da opcao 062 nos arquivos SSW coletados, e Rafael **nao conhece esta opcao**.

**Campos esperados (baseado em referencias indiretas)**:
1. Desconto maximo (%) — pode ser complementar ou redundante com 469
2. Resultado comercial minimo (%) — pode ser complementar ou redundante com 469
3. Custos adicionais — mencionado no catalogo como funcao da 062

**O que investigar**:
1. Acessar opcao 062 no SSW → verificar se existe e quais campos tem
2. Comparar com opcao 469 (limites por rota) — redundante ou complementar?
3. Se campos unicos: configurar
4. Documentar todos os campos e valores para referencia

**Como resolver**: Rafael acessar opcao 062 no SSW e documentar todos os campos. Se a opcao nao existir, pode ser que o numero esteja errado ou seja um modulo nao contratado.

**Impacto se nao resolver**: Pode ser a causa dos problemas recorrentes de simulacao incorreta. Parametros faltantes podem gerar calculos errados de desconto e resultado comercial.

---

### PEND-13 — Configurar Limites de Cotacao por Rota (469)

**POPs afetados**: B01 (limites na cotacao), B03 (etapa 2)

**Situacao**: A opcao 469 define limites que controlam a negociacao comercial: valor minimo do frete, desconto maximo NTC, resultado comercial minimo e desconto maximo sobre proposta inicial. A CarVia possivelmente NAO tem 469 configurada para suas rotas.

**Como resolver**: Para cada rota ativa (CAR→parceiro), acessar opcao 469 e configurar:
- Valor minimo frete (R$)
- Desconto maximo NTC (%)
- Resultado comercial minimo (%)
- Desconto maximo proposta inicial (%)

**Impacto se nao resolver**: Cotacoes (002) sem limites — descontos excessivos ou cotacoes abaixo do custo permitidas.

---

### PEND-14 — Configurar Cubagem por Cliente (423)

**POPs afetados**: B01 (cubagem na cotacao), B03 (etapa 3)

**Situacao**: A opcao 423 define cubagem especifica por cliente, sobrescrevendo a cubagem padrao (903 = 300 Kg/m3). Clientes com cargas volumosas (MotoChefe: motos em caixas) ou pesadas (NotCo: paletes) precisam de cubagem ajustada.

**Como resolver**: Para cada cliente ativo, avaliar se cubagem padrao 300 e adequada. Se nao, acessar opcao 423 e configurar cubagem real.

**Impacto se nao resolver**: Preco de frete pode ser inflado (cubagem muito alta) ou subfaturado (cubagem muito baixa) para clientes com cargas especificas.

---

## Proximas Pendencias (Previstas para Onda 5)

| Onda | Pendencia provavel | POP |
|------|-------------------|-----|
| 5 | Configuracao de setores (404) — necessario para controle de retorno | D05 |
| 5 | Definir politica de ocorrencias (405) | D06 |
| 5 | Configurar relatorios gerenciais (056/300) | G03, G04 |

---

## Historico

| Data | Alteracao |
|------|-----------|
| 2026-02-15 | Criacao inicial com 5 pendencias da Onda 1 |
| 2026-02-15 | Adicionadas 6 pendencias da Onda 2 (PEND-06 a PEND-11) |
| 2026-02-16 | Adicionadas 3 pendencias da Onda 3 (PEND-12 a PEND-14). PEND-12 (opcao 062) marcada URGENTE |
| 2026-02-16 | Adicionadas 3 pendencias da Onda 4 (PEND-15 a PEND-17). PEND-17 (rotina monitoramento) marcada Alta |
| 2026-02-16 | Onda 5 COMPLETA (14 POPs). Sem novas pendencias — POPs complementares com [CONFIRMAR] inline. Fase 5C 100% (45/45 POPs) |

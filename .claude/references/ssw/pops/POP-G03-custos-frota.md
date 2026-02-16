# POP-G03 — Controlar Custos de Frota

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: [026](../relatorios/026-cadastro-veiculos.md), [320](../relatorios/320-abastecimento-interno.md), [131](../relatorios/131-ordens-servico.md), [475](../financeiro/475-contas-a-pagar.md)
> **Executor atual**: Rafael (sem controle SSW)
> **Executor futuro**: Rafael

---

## Objetivo

Estabelecer controle sistematico dos custos operacionais de veiculos proprios (VUC e Truck) no SSW, permitindo analise de rentabilidade, planejamento de manutencao e tomada de decisao sobre uso de frota propria vs. terceirizada.

---

## Quando Executar (Trigger)

- **Periodico**: Mensal (analise de custos, fechamento)
- **Por evento**: Abastecimento, manutencao, sinistro, troca de pneu, despesa extraordinaria

---

## Frequencia

- **Abastecimento**: A cada abastecimento (interno ou externo)
- **Manutencao**: Conforme necessidade ou plano preventivo
- **Analise**: Mensal
- **Fechamento**: Mensal (para contabilidade)

---

## Pre-requisitos

| Item | Opcao SSW | O que verificar |
|------|-----------|-----------------|
| Veiculos cadastrados | [026](../relatorios/026-cadastro-veiculos.md) | Placa, RNTRC, tipo, odometro inicial |
| Tipo de veiculo Frota | [097](../operacional/097-controle.md) | "Frota controla"=X, "Possui odometro"=X |
| Bomba interna (opcional) | 321 | Se usar abastecimento interno |
| Fornecedores cadastrados | [478](../financeiro/478-cadastro-fornecedores.md) | Postos, oficinas, fornecedores |
| Eventos de despesa | [503](../fiscal/503-manutencao-de-eventos.md) | Combustivel, manutencao, seguro, IPVA, pneus |
| Plano de contas | 540/526 | Contas contabeis por tipo de despesa |

---

## Passo-a-Passo

### ETAPA 1 — Setup Inicial (Uma vez)

#### 1.1 — Configurar Tipo de Veiculo (Opcao 097)

1. Acessar [opcao **097**](../operacional/097-controle.md) no SSW
2. Criar ou editar tipo de veiculo (ex: "VUC PROPRIO", "TRUCK PROPRIO")
3. Marcar:
   - **"Frota controla"**: X (sim)
   - **"Possui odometro"**: X (sim)
   - **"Possui motor"**: X (sim)
4. Confirmar

> **Por que**: Este campo determina se o SSW gerenciara manutencoes e custos do veiculo.

#### 1.2 — Cadastrar Veiculos (Opcao 026)

5. Acessar [opcao **026**](../relatorios/026-cadastro-veiculos.md)
6. Para cada veiculo proprio (VUC e Truck):

| Campo | Valor | Exemplo |
|-------|-------|---------|
| Placa | Placa oficial | ABC1D23 |
| Tipo de veiculo | Tipo criado em [097](../operacional/097-controle.md) | VUC PROPRIO |
| Quantidade de eixos | Numero de eixos | 2 (VUC), 3 (Truck) |
| Possui odometro | X | X |
| Qtde digitos odometro | 6 | 6 (max 999.999) |
| Km odometro | Quilometragem atual | 45678 |
| Km veiculo | Km total desde compra | 45678 (se novo) |
| Unidade | CAR | CAR |

7. Preencher **medias de consumo** (se disponivel):
   - Media minima: ex. 7,5 km/l
   - Media maxima: ex. 9,5 km/l
8. Confirmar

> **Gotcha**: Se o odometro ja deu voltas, calcular "Qtde voltas" conforme formula: `Km veiculo = (Qtde voltas × 1.000.000) + Km odometro`.

#### 1.3 — Configurar Bomba Interna (Opcional, se usar)

**Se a CarVia instalar bomba interna no CD:**

9. Acessar opcao **321**
10. Informar:

| Campo | Valor |
|-------|-------|
| Codigo | 1 |
| Sigla filial | CAR |
| Descricao | Bomba Interna CD Santana |
| Volume atual (l) | Estoque inicial em litros |
| Valor saida Frota (R$/l) | Preco de custo do combustivel |
| Valor saida Agregado | [CONFIRMAR se aplica] |
| Valor saida Carreteiro | [CONFIRMAR se aplica] |

11. Confirmar

> **Se nao usar bomba interna**: Pular esta etapa. Abastecimentos serao lancados via [opcao 475](../financeiro/475-contas-a-pagar.md) (Contas a Pagar).

#### 1.4 — Cadastrar Fornecedores (Opcao 478)

12. Acessar [opcao **478**](../financeiro/478-cadastro-fornecedores.md)
13. Para cada fornecedor (postos, oficinas, seguradoras):

| Campo | Obrigatorio | Exemplo |
|-------|-------------|---------|
| CNPJ/CPF | Sim | CNPJ do posto |
| Razao social | Sim | Posto Shell Santana |
| Tipo fornecedor | Nao | [deixar vazio ou criar categorias] |
| CCF ativa | Nao | N (para frota nao faz sentido CCF) |
| Dados bancarios | Nao | Preencher se pagar via CCF |

14. Confirmar

> **Fornecedores tipicos**: Postos de combustivel, oficinas mecanicas, borracharias, lava-rapidos, despachantes (IPVA/Licenciamento), seguradoras.

#### 1.5 — Configurar Eventos de Despesa (Opcao 503)

15. Acessar [opcao **503**](../fiscal/503-manutencao-de-eventos.md)
16. Verificar ou criar eventos para despesas de frota:

| Evento | Descricao | Informa consumo | Debita veiculo | Conta contabil |
|--------|-----------|-----------------|----------------|----------------|
| COMBUSTIVEL | Combustivel (externo) | X | X | [conta despesa combustivel] |
| MANUTENCAO | Manutencao corretiva | | X | [conta manutencao] |
| PREVENTIVA | Manutencao preventiva | | X | [conta manutencao] |
| PNEUS | Pneus novos/recapados | | X | [conta pneus] |
| SEGURO | Seguro anual | | X | [conta seguro] |
| IPVA | IPVA anual | | X | [conta impostos] |
| LICENCIAMENTO | Licenciamento anual | | X | [conta impostos] |
| LAVAGEM | Lavagem veiculos | | X | [conta conservacao] |
| MULTAS | Multas transito | | X | [conta multas] |

17. Para **COMBUSTIVEL**: Marcar **"Informa consumo"=X** e **"Debita veiculo"=X**
18. Para os demais: Marcar apenas **"Debita veiculo"=X**
19. Confirmar cada evento

> **Por que "Debita veiculo"**: Este campo permite que o SSW associe a despesa ao veiculo especifico, gerando historico de custos por veiculo.

> **Por que "Informa consumo"**: Este campo aciona o calculo automatico de media de consumo (km/l). Se a media ficar fora dos limites ([026](../relatorios/026-cadastro-veiculos.md)), o SSW gera OS automatica ([131](../relatorios/131-ordens-servico.md)).

---

### ETAPA 2 — Registrar Abastecimentos

#### 2A — Abastecimento INTERNO (se usar bomba interna)

**Opcao [320](../relatorios/320-abastecimento-interno.md)**

1. Acessar [opcao **320**](../relatorios/320-abastecimento-interno.md)
2. Preencher:

| Campo | Valor |
|-------|-------|
| Codigo bomba | 1 (codigo criado em 321) |
| Placa | Placa do veiculo |
| Litros | Quantidade abastecida |
| Odometro | Quilometragem ATUAL (ler no painel do veiculo) |

3. Sistema calcula automaticamente:
   - Valor (litros × preco configurado em 321)
   - Media de consumo: `(Km atual - Km abastecimento anterior) / litros`
4. Confirmar

**O que acontece**:
- Estoque da bomba (321) e reduzido automaticamente
- Odometro do veiculo ([026](../relatorios/026-cadastro-veiculos.md)) e atualizado
- Sistema verifica se media esta dentro dos limites ([026](../relatorios/026-cadastro-veiculos.md)):
  - **Dentro**: Registra normalmente
  - **Fora**: Gera OS automatica na [opcao 131](../relatorios/131-ordens-servico.md) para investigacao

**Quando gera OS automatica**:
- Media < minima configurada (ex: 6 km/l quando minimo e 7,5)
- Media > maxima configurada (ex: 11 km/l quando maximo e 9,5)

> **Gotcha**: Se nao informar odometro corretamente, a media sera incorreta e gerara OS falsa.

#### 2B — Abastecimento EXTERNO (posto de combustivel)

**Opcao [475](../financeiro/475-contas-a-pagar.md)**

1. Acessar [opcao **475**](../financeiro/475-contas-a-pagar.md) — Contas a Pagar
2. Informar:

| Campo | Valor |
|-------|-------|
| Unidade | CAR |
| CNPJ fornecedor | CNPJ do posto |
| Evento | COMBUSTIVEL ([503](../fiscal/503-manutencao-de-eventos.md)) |

3. Preencher dados fiscais:

| Campo | Valor |
|-------|-------|
| Modelo documento | 55 (NF-e) ou 95 (Boleto) ou 99 (Cupom fiscal) |
| Numero NF | Numero da nota fiscal |
| Serie | Serie (se NF-e) |
| Data emissao | Data da NF |
| Data entrada | Data do abastecimento |
| Valor total | Valor total da NF |

4. Preencher dados financeiros:

| Campo | Valor |
|-------|-------|
| Data pagamento | Data que sera pago (se a vista = data entrada) |
| Mes competencia | Mes do abastecimento |

5. Clicar **"Confirmar"**

**Sistema sugere lancamento complementar**:

6. Opcao **576 — Informa Consumo** e sugerida automaticamente (porque evento tem "Informa consumo"=X)
7. Informar:

| Campo | Valor |
|-------|-------|
| Placa | Placa do veiculo |
| Litros | Quantidade abastecida |
| Odometro | Quilometragem ATUAL |

8. Confirmar

**Sistema sugere outro lancamento**:

9. Opcao **577 — Debita Veiculo** e sugerida (porque evento tem "Debita veiculo"=X)
10. Confirmar automaticamente (vincula despesa ao veiculo)

**O que acontece**:
- Despesa fica programada ([475](../financeiro/475-contas-a-pagar.md)) para pagamento
- Odometro do veiculo ([026](../relatorios/026-cadastro-veiculos.md)) e atualizado
- Media de consumo e calculada
- Custo e associado ao veiculo especifico
- Se media fora dos limites → OS automatica ([131](../relatorios/131-ordens-servico.md))

> **Quando usar [475](../financeiro/475-contas-a-pagar.md) vs. [320](../relatorios/320-abastecimento-interno.md)**: Use **320** se tiver bomba interna. Use **475** se abastecer em posto externo.

---

### ETAPA 3 — Registrar Manutencoes

**Opcao [131](../relatorios/131-ordens-servico.md)** (Ordens de Servico)

#### 3.1 — Incluir Nova OS (Manutencao Nao Programada)

**Quando**: Quebra, problema detectado, veiculo com avaria.

1. Acessar [opcao **131**](../relatorios/131-ordens-servico.md)
2. Clicar **"Incluir Ordem de Servico"**
3. Informar:

| Campo | Valor |
|-------|-------|
| Placa | Placa do veiculo |
| Descricao | Descricao do problema (ex: "Troca de oleo motor") |
| Data prevista | Data estimada para resolver |
| Km prevista | (opcional) Quilometragem prevista |

4. Confirmar

**Status da OS**: Pendente (aparece na lista [131](../relatorios/131-ordens-servico.md) e no relatorio 319)

#### 3.2 — Registrar Providencias Tomadas

**Quando**: Manutencao realizada, problema resolvido.

5. Acessar [opcao **131**](../relatorios/131-ordens-servico.md)
6. Clicar sobre a linha da OS pendente
7. Informar:

| Campo | Valor |
|-------|-------|
| Odometro atual | Quilometragem ATUAL (ler no painel do veiculo) |
| Providencias | Descricao detalhada do que foi feito (ex: "Trocado oleo Lubrax 15W40, filtro de oleo Mann W610/3, filtro de ar. Revisao 30.000 km") |

8. Confirmar

**O que acontece**:
- Odometro do veiculo ([026](../relatorios/026-cadastro-veiculos.md)) e atualizado
- OS fica resolvida (sai da lista de pendentes)
- Se houver check-list vinculado (315) ou plano de manutencao (615), proximo agendamento e criado automaticamente

> **Gotcha**: SEMPRE informar odometro corretamente. E a unica forma do SSW manter historico de quilometragem do veiculo.

#### 3.3 — Lancar Despesa da Manutencao

**Quando**: Receber NF da oficina.

9. Acessar [opcao **475**](../financeiro/475-contas-a-pagar.md) — Contas a Pagar
10. Informar CNPJ da oficina, evento **MANUTENCAO** (ou **PREVENTIVA**, conforme tipo)
11. Preencher dados fiscais e financeiros (igual ao abastecimento)
12. Sistema sugere **577 — Debita Veiculo**: Confirmar
13. NO campo **"Observacao"** da despesa ([475](../financeiro/475-contas-a-pagar.md)): Referenciar numero da OS (ex: "OS 00123 — Troca de oleo 30k km")

> **Importante**: Vincular mentalmente a despesa ([475](../financeiro/475-contas-a-pagar.md)) com a OS ([131](../relatorios/131-ordens-servico.md)). O SSW nao faz vinculo automatico, mas o numero da OS na observacao ajuda a rastrear.

---

### ETAPA 4 — Registrar Outras Despesas de Frota

**Opcao [475](../financeiro/475-contas-a-pagar.md)** (mesmo processo do abastecimento externo)

#### 4.1 — Despesas Anuais (IPVA, Licenciamento, Seguro)

1. Acessar [opcao **475**](../financeiro/475-contas-a-pagar.md)
2. Informar CNPJ do fornecedor (Detran, Seguradora)
3. Selecionar evento: **IPVA**, **LICENCIAMENTO**, ou **SEGURO**
4. Preencher dados fiscais e financeiros
5. Sistema sugere **577 — Debita Veiculo**: Confirmar

> **Parcelamento**: Se IPVA for parcelado (3x), criar UMA despesa ([475](../financeiro/475-contas-a-pagar.md)) com 3 parcelas. Usar botao **"Adicionar parcelas"** na tela de despesas.

#### 4.2 — Despesas Eventuais (Lavagem, Multas, Pedagios)

1. Mesma [opcao **475**](../financeiro/475-contas-a-pagar.md)
2. Eventos: **LAVAGEM**, **MULTAS**, ou criar evento especifico
3. Preencher normalmente
4. Debita veiculo (577)

#### 4.3 — Pneus (Compra, Recapagem)

1. [Opcao **475**](../financeiro/475-contas-a-pagar.md), evento **PNEUS**
2. Debita veiculo (577)
3. **Paralelo**: Se o SSW tiver controle de pneus ativo:
   - Cadastrar pneu na opcao **313**
   - Movimentar pneu na [opcao **316**](../relatorios/316-movimentacao-pneus.md) (associar ao veiculo/posicao)

> **Controle de pneus completo**: Ver secao "Contexto CarVia — Controle de Pneus (Futuro)" abaixo.

---

### ETAPA 5 — Analise Mensal de Custos

**Relatorios e Consultas**

#### 5.1 — Relatorio de Custos por Veiculo

**[CONFIRMAR: Opcao especifica para este relatorio — nao identificada na doc]**

Provavel caminho:
- Opcao **056** — Relatorios Gerenciais → Buscar relatorio tipo "Custos de Frota" ou "Despesas por Veiculo"
- **OU** opcao **477** — Consultas de Despesas → Filtrar por veiculo

**Dados a extrair**:
- Total de despesas por veiculo (mes/ano)
- Custo por tipo: Combustivel, Manutencao, Pneus, Seguro, IPVA
- Custo por Km rodado: `Total despesas / Km rodados no periodo`
- Comparativo mes a mes

#### 5.2 — Relatorio de Consumo

**Opcao 322 — Relatorio de Consumo**

1. Acessar opcao **322**
2. Informar periodo (mes/ano)
3. Selecionar veiculo (ou todos)
4. Gerar relatorio

**Dados exibidos**:
- Todos os abastecimentos do periodo
- Medias de consumo (km/l) de cada abastecimento
- Media do mes
- Comparacao com limites configurados ([026](../relatorios/026-cadastro-veiculos.md))
- Outliers (abastecimentos com media fora do normal)

#### 5.3 — Ordens de Servico (Historico)

**Opcao 319 — Relatorios de Ordens de Servico**

1. Acessar [opcao **131**](../relatorios/131-ordens-servico.md) → Clicar **"Imprimir"** (abre opcao 319)
2. **OU** Acessar opcao **319** diretamente
3. Informar periodo e veiculo
4. Gerar relatorio

**Dados exibidos**:
- Todas as OSs do periodo (pendentes e resolvidas)
- Descricao dos problemas
- Providencias tomadas
- Quilometragem de cada OS
- Frequencia de problemas por veiculo

#### 5.4 — Quilometragem de Veiculos

**Opcao 328 — Quilometragem de Veiculos**

1. Acessar opcao **328**
2. Informar periodo
3. Gerar relatorio

**Dados exibidos**:
- Km inicial e final de cada veiculo
- Km rodados no periodo
- Media de km por dia
- Historico de atualizacoes de odometro

---

### ETAPA 6 — Decisao: Usar Veiculo Proprio ou Subcontratar?

**Calculo de Viabilidade**

#### 6.1 — Custo Total Mensal do Veiculo Proprio

Extrair do relatorio de custos (5.1):

```
Custo Fixo Mensal:
+ Seguro anual / 12
+ IPVA anual / 12
+ Licenciamento anual / 12
+ Depreciacao mensal (custo do veiculo / vida util em meses)
= (A) Custo Fixo Mensal

Custo Variavel Mensal (do mes analisado):
+ Combustivel
+ Manutencoes
+ Pneus
+ Lavagens
+ Pedagios
= (B) Custo Variavel Mensal

Custo Total Mensal = (A) + (B)
```

#### 6.2 — Custo por Km Rodado

```
Km rodados no mes (extrair de 328)
Custo por Km = Custo Total Mensal / Km rodados
```

#### 6.3 — Comparar com Custo de Subcontratacao

Extrair custo medio de subcontratacao (agregado ou transportadora):

- **Opcao [408](../comercial/408-comissao-unidades.md)**: Custo de subcontratacao por rota
- **Opcao [486](../financeiro/486-conta-corrente-fornecedor.md)**: Acertos mensais com agregados (CCF)
- **Opcao [475](../financeiro/475-contas-a-pagar.md)**: Despesas com transportadoras parceiras

**Decisao**:
- Se **Custo proprio < Custo subcontratacao**: Usar veiculo proprio
- Se **Custo proprio > Custo subcontratacao**: Subcontratar

> **Exemplo**: Se VUC proprio custa R$ 2,50/km e agregado custa R$ 2,00/km, e mais barato subcontratar.

---

## Contexto CarVia

### Hoje

A CarVia possui 2 caminhoes proprios:
- **1 VUC** (capacidade 3.500 kg)
- **1 Truck** (capacidade 14.000 kg)

**Situacao atual**:
- **SEM controle no SSW** — custos controlados fora do sistema
- Abastecimentos: Postos externos (sem bomba interna)
- Manutencoes: Oficinas terceirizadas
- Rafael **nao sabe** quanto custa operacionalmente cada veiculo
- **Nao compara** custo proprio vs. agregado de forma sistematica

**Risco**:
- Decisao de usar veiculo proprio e baseada em **intuicao**, nao em dados
- Pode estar **perdendo dinheiro** usando veiculo proprio quando agregado seria mais barato
- Sem historico de manutencoes, **nao planeja preventivas** (so corretivas apos quebra)

### Futuro (com POP implantado)

**Com controle SSW**:
- Todos os abastecimentos registrados ([475](../financeiro/475-contas-a-pagar.md) + 576/577)
- Todas as manutencoes registradas ([131](../relatorios/131-ordens-servico.md)) e vinculadas a despesas ([475](../financeiro/475-contas-a-pagar.md))
- Odometro sempre atualizado ([026](../relatorios/026-cadastro-veiculos.md))
- Media de consumo monitorada automaticamente (322)
- Custos totais por veiculo extraidos mensalmente (056/477)
- **Decisao baseada em dados**: Usar proprio ou subcontratar?

**Beneficios**:
- Visibilidade total de custos por veiculo
- Alerta automatico se consumo anormal (OS automatica [131](../relatorios/131-ordens-servico.md))
- Historico de manutencoes para negociacao de revenda
- Planejamento de manutencoes preventivas (via [314](../relatorios/314-check-list-manutencao.md)/315/615 — ver secao "Futuro" abaixo)
- Comparacao objetiva: proprio vs. agregado vs. transportadora

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Media de consumo absurda (100 km/l ou 0,5 km/l) | Odometro informado errado | Conferir odometro no painel do veiculo. Corrigir em [026](../relatorios/026-cadastro-veiculos.md) manualmente (requer usuario FRT) |
| OS automatica gerada sem motivo | Limites de consumo ([026](../relatorios/026-cadastro-veiculos.md)) muito estreitos | Ajustar limites min/max conforme historico real do veiculo |
| Despesa nao aparece no relatorio do veiculo | Evento sem "Debita veiculo"=X | Corrigir evento em [503](../fiscal/503-manutencao-de-eventos.md). Relancar despesa ou ajustar manualmente |
| Odometro nao atualiza | Tipo de veiculo sem "Frota controla"=X | Corrigir em [097](../operacional/097-controle.md). Atualizar manualmente [026](../relatorios/026-cadastro-veiculos.md) (usuario FRT) |
| Abastecimento interno nao debita estoque | Bomba (321) nao configurada ou codigo errado | Verificar codigo bomba em 321 e corrigir em [320](../relatorios/320-abastecimento-interno.md) |
| Proximo check-list nao agendado | Check-list nao vinculado ao veiculo | Criar check-list ([314](../relatorios/314-check-list-manutencao.md)) e vincular (315) |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Veiculo cadastrado com Frota controla | [026](../relatorios/026-cadastro-veiculos.md) → placa → tipo veiculo → [097](../operacional/097-controle.md) → "Frota controla"=X |
| Odometro atualizado | [026](../relatorios/026-cadastro-veiculos.md) → placa → Km veiculo e Km odometro coerentes |
| Medias de consumo configuradas | [026](../relatorios/026-cadastro-veiculos.md) → placa → media minima/maxima preenchidas |
| Bomba interna configurada | 321 → codigo 1 → volume atual, precos |
| Abastecimento registrado | [320](../relatorios/320-abastecimento-interno.md) ou [475](../financeiro/475-contas-a-pagar.md) → verificar lancamento |
| OS pendente ou resolvida | [131](../relatorios/131-ordens-servico.md) → verificar lista de OSs |
| Despesa vinculada ao veiculo | [475](../financeiro/475-contas-a-pagar.md) → despesa → verificar lancamento complementar 577 |
| Relatorio de consumo | 322 → periodo → verificar medias |
| Relatorio de custos | 056 ou 477 → filtrar por veiculo → extrair totais |

---

## Contexto CarVia — Controle de Pneus (Futuro)

**Hoje**: CarVia **nao controla** pneus no SSW.

**Quando for implantar** (prioridade baixa, apos controle basico de custos):

1. **Opcao 313 — Cadastrar Pneu**: Numero fisico, marca, medida, localizacao inicial, Km inicial
2. **[Opcao 316](../relatorios/316-movimentacao-pneus.md) — Movimentar Pneu**: Trocar posicao, retirar para conserto, instalar novo
3. Odometro atualizado automaticamente (025/030/035) → pneus nas posicoes recebem Km
4. **Opcao 317 — Vida do Pneu**: Historico completo desde aquisicao
5. **Opcao 318 — Estoque**: Pneus em almoxarifado

**Beneficio**: Controlar vida util de cada pneu, planejar trocas, identificar pneus problematicos.

---

## Contexto CarVia — Manutencao Preventiva (Futuro)

**Hoje**: CarVia faz **SOMENTE manutencao corretiva** (quando quebra).

**Quando for implantar** (prioridade media, apos controle basico):

### Fluxo F15 — Manutencao Preventiva

1. **[Opcao 314](../relatorios/314-check-list-manutencao.md) — Criar Check-list**: Ex: "Revisao 30.000 km" (lista de itens: oleo, filtros, fluidos)
2. **Opcao 315 — Vincular ao Veiculo**: Check-list → Veiculo → Periodicidade (ex: a cada 30.000 km)
3. Sistema gera OS automaticamente na [opcao **131**](../relatorios/131-ordens-servico.md) quando Km do veiculo atinge limite
4. Equipe resolve OS ([131](../relatorios/131-ordens-servico.md)), informa odometro e providencias
5. Proximo agendamento criado automaticamente (315 recalcula: Km atual + 30.000)

**Alternativa: Plano de Manutencao**

- **Opcao [614](../edi/614-cadastro-planos-manutencao.md)**: Plano com ate 20 itens (ex: "Troca oleo", "Troca filtro ar")
- **Opcao 615**: Vincular plano ao veiculo (periodicidade em dias OU Km)
- Sistema gera OS automatica ([131](../relatorios/131-ordens-servico.md)) conforme plano

**Beneficio**: Reduzir quebras, aumentar vida util, planejar despesas.

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A08 | Cadastrar veiculo — pre-requisito para controle |
| POP-F01 | Lancar contas a pagar — despesas de frota via [475](../financeiro/475-contas-a-pagar.md) |
| POP-F03 | Liquidar despesa — pagar oficinas, postos |
| POP-D01 | Contratar veiculo — quando veiculo proprio faz carga direta, gerar CTRB (072) |
| POP-G04 | Relatorios contabilidade — custos de frota integram fechamento contabil |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |

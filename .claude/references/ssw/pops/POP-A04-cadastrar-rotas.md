# POP-A04 — Cadastrar Rotas

> **Categoria**: A — Implantacao e Cadastros
> **Prioridade**: P2 (Media — necessario para calculo de prazo e MDF-e)
> **Status CarVia**: JA FAZ
> **Opcoes SSW**: 403
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Cadastrar rotas de transferencia entre unidades no SSW da CarVia, definindo prazo de transferencia, hora de corte e quantidade de pedagogios. As rotas sao utilizadas no calculo de previsao de entrega (prazo total = prazo rota + prazo cidade) e no planejamento operacional. Rotas tambem sao criticas para emissao de MDF-e (Manifesto de Documentos Fiscais Eletronicos) em transportes interestaduais, pois informam as UFs percorridas.

---

## Quando Executar (Trigger)

- Nova unidade parceira criada (POP-A02)
- Cliente solicita frete para cidade atendida por novo parceiro
- Parte do processo de implantacao de nova rota (POP-A10)
- Ampliar rede de transferencias entre unidades existentes
- Necessidade de emitir MDF-e para nova origem/destino

---

## Frequencia

Por demanda — a cada novo parceiro ou nova rota de transferencia. Estimativa: 2-5 minutos por rota.

---

## Pre-requisitos

- Unidades origem e destino cadastradas na [opcao 401](../cadastros/401-cadastro-unidades.md):
  - Unidade origem: **CAR** (CarVia Santana de Parnaiba/SP)
  - Unidade destino: Sigla do parceiro (ex: CGR, FOR, SSA, etc.)
- Dados para preencher:
  - Prazo de transferencia em dias uteis (estimativa ou historico)
  - Distancia entre origem e destino (Google Maps ou historico)
  - UFs percorridas no trajeto (critico para MDF-e)
  - Quantidade de pedagogios (opcional, mas importante para custos)
  - Hora de corte (opcional, para controle de chegada de veiculos)

---

## Passo-a-Passo

### ETAPA 1 — Acessar e Iniciar Cadastro

1. Acessar [opcao **403**](../cadastros/403-rotas.md) (Cadastro de Rotas)
2. Tela inicial: SSW mostra rotas ja cadastradas (se houver)
3. Clicar em **Incluir** para criar nova rota

---

### ETAPA 2 — Definir Origem e Destino

4. Preencher os campos de identificacao da rota:

| Campo | Valor CarVia | Observacao |
|-------|--------------|------------|
| **Unidade Origem** | **CAR** | Unidade operacional CarVia em Santana de Parnaiba/SP |
| **Unidade Destino** | Sigla do parceiro | Ex: CGR (Campo Grande), FOR (Fortaleza), SSA (Salvador) |

5. Verificar se a rota ja existe:
   - SSW alerta se a rota CAR → [DESTINO] ja esta cadastrada
   - Se ja existe: acessar para **editar** ao inves de criar nova
   - Se nao existe: prosseguir com cadastro

> **IMPORTANTE**: Rotas sao unidirecionais. CAR → CGR e diferente de CGR → CAR. Para transporte bidirecional (ida e volta), cadastrar ambas as rotas.

---

### ETAPA 3 — Preencher Prazo de Transferencia

6. Informar o **Prazo de Transferencia**:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Prazo de Transferencia** | Dias uteis | Tempo de transito entre origem e destino |

**Como definir o prazo**:
- Distancia < 500 Km: 1 dia
- Distancia 500-1.000 Km: 2 dias
- Distancia 1.000-1.500 Km: 3 dias
- Distancia 1.500-2.500 Km: 4-5 dias
- Distancia > 2.500 Km: 5-7 dias

> **Exemplo CGR**: Santana de Parnaiba/SP → Campo Grande/MS (~1.000 Km) = **2 dias uteis**

7. **Feriados no calculo de prazo**:
   - Prazo de transferencia e contado em **dias uteis**
   - Feriados sao considerados **APOS** a contagem do prazo, no destino
   - Feriados municipais, estaduais e federais afetam o prazo final
   - Veja documentacao SSW para detalhes do algoritmo de calculo

---

### ETAPA 4 — Configurar Hora de Corte (Opcional)

8. Informar **Hora de Corte** (se aplicavel):

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Hora de Corte** | HH:MM | Hora limite para chegada do manifesto na unidade destino |

**Quando usar**:
- Controle de pontualidade de manifestos ([opcao 030](../operacional/030-chegada-de-veiculo.md))
- Manifestos que chegam apos hora de corte sao identificados como **ATRASADO**
- Se unidade destino tiver operacao FEC (fechada), chegada e identificada como **FECHADA**

**Contexto CarVia**:
- CarVia NAO usa hora de corte hoje
- Deixar **vazio** no cadastro

---

### ETAPA 5 — Informar Distancia e Pedagogios

9. Preencher campos opcionais:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Distancia** | Km entre origem e destino | Usar Google Maps ou ferramenta de roteamento |
| **Quantidade de Pedagogios** | Numero de postos de pedagio no trajeto | Usado em tabelas de frete para calculo de pedagio |

**Distancia**:
- Calcular via Google Maps: Santana de Parnaiba/SP → Cidade destino
- Informar valor arredondado (sem decimais)
- Exemplo: SP → Campo Grande/MS = **1.032 Km**

**Quantidade de Pedagogios**:
- Contar postos de pedagio no trajeto principal
- Importante para calculo de custo de frete (tabelas usam R$/frac 100Kg * qtd pedagogios)
- Se nao souber o numero exato, deixar vazio ou estimar

> **NOTA**: Total de pedagogios no frete = pedagogios da rota ([403](../cadastros/403-rotas.md)) + pedagogios da cidade destino ([402](../cadastros/402-cidades-atendidas.md))

---

### ETAPA 6 — Informar UFs Percorridas (Critico para MDF-e)

10. Informar as **UFs percorridas** no trajeto:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **UFs Percurso** | Lista de UFs (ex: SP, MS) | Obrigatorio para emissao de MDF-e |

**Como definir**:
- Listar TODAS as UFs atravessadas no trajeto origem → destino
- Incluir UF de origem e UF de destino
- Ordem: da origem ao destino

**Exemplos**:
- SP → Campo Grande/MS: **SP, MS**
- SP → Fortaleza/CE: **SP, MG, BA, PE, CE**
- SP → Manaus/AM: **SP, MS, MT, RO, AM** (via rodoviaria)

> **CRITICO**: MDF-e EXIGE as UFs percorridas. Sem este campo preenchido, o MDF-e pode ser rejeitado pelo SEFAZ. Verificar rota real no mapa antes de cadastrar.

---

### ETAPA 7 — Salvar Rota

11. Conferir todos os campos preenchidos:
    - Unidade origem = CAR
    - Unidade destino = sigla do parceiro
    - Prazo de transferencia (dias uteis)
    - Distancia (Km)
    - UFs percorridas
    - Quantidade de pedagogios (se conhecido)

12. Clicar em **Gravar** para salvar a rota

13. SSW confirma cadastro e retorna para lista de rotas

---

### ETAPA 8 — Verificar Prazo Total na Cotacao

14. Validar o prazo total calculado:
    - Acessar [opcao **002**](../operacional/002-consulta-coletas.md) (Cotacao)
    - Informar origem = CAR, destino = cidade da rota cadastrada
    - Verificar **prazo de entrega** retornado
    - Prazo total = **Prazo rota ([403](../cadastros/403-rotas.md))** + **Prazo cidade ([402](../cadastros/402-cidades-atendidas.md))**

> **Exemplo CGR**:
> - Prazo rota CAR → CGR: 2 dias ([opcao 403](../cadastros/403-rotas.md))
> - Prazo cidade Campo Grande: 2 dias ([opcao 402](../cadastros/402-cidades-atendidas.md))
> - **Prazo total**: 4 dias uteis (exibido na cotacao 002)

---

## Contexto CarVia

### Hoje

- Rafael cadastra rota ao criar novo parceiro (parte do processo A10)
- Prazo de transferencia: estimado com base em distancia e experiencia
- Distancia: consultada no Google Maps
- UFs percorridas: NAO cadastradas hoje (problema critico para MDF-e)
- Hora de corte: NAO utilizada
- Quantidade de pedagogios: NAO cadastrada (afeta calculo de frete)

### Futuro (com POP implantado)

- UFs percorridas SEMPRE preenchidas (pre-requisito para MDF-e)
- Distancia e pedagogios cadastrados para melhorar calculo de frete
- Prazo de transferencia validado com historico de entregas
- Hora de corte pode ser usada no futuro para controle operacional

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Rota ja existe | Tentou cadastrar rota duplicada (CAR → CGR ja existe) | Acessar rota existente para editar |
| Prazo total incorreto na cotacao | Prazo rota ou prazo cidade errado | Revisar [opcao 403](../cadastros/403-rotas.md) (prazo rota) e 402 (prazo cidade) |
| MDF-e rejeitado por UFs | UFs percorridas nao informadas ou incorretas | Revisar trajeto no mapa, corrigir UFs na 403 |
| Pedagio calculado incorreto | Qtd pedagogios da rota nao cadastrada | Informar pedagogios na 403 e/ou 402 |
| Unidade destino nao encontrada | Unidade parceira nao cadastrada na 401 | Criar unidade (POP-A02) antes de criar rota |
| Hora de corte validando incorretamente | Configuracao da [opcao 030](../operacional/030-chegada-de-veiculo.md) (chegada veiculos) | Verificar parametros na 030, ajustar hora de corte na 403 |
| Rota nao aparece na lista | Filtro de unidade aplicado incorretamente | Limpar filtros ou buscar por unidade origem (CAR) |
| Distancia zerada | Campo nao preenchido | Calcular via Google Maps e informar manualmente |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Rota cadastrada | [Opcao 403](../cadastros/403-rotas.md) → buscar origem CAR → rota aparece na lista |
| Unidades corretas | [Opcao 403](../cadastros/403-rotas.md) → abrir rota → origem=CAR, destino=sigla parceiro |
| Prazo de transferencia | [Opcao 403](../cadastros/403-rotas.md) → abrir rota → prazo em dias uteis |
| Distancia informada | [Opcao 403](../cadastros/403-rotas.md) → abrir rota → campo Distancia > 0 |
| UFs percorridas | [Opcao 403](../cadastros/403-rotas.md) → abrir rota → campo UFs preenchido |
| Qtd pedagogios | [Opcao 403](../cadastros/403-rotas.md) → abrir rota → campo Pedagios > 0 (se aplicavel) |
| Prazo total na cotacao | [Opcao 002](../operacional/002-consulta-coletas.md) → simular frete → prazo = rota + cidade |

---

## Exemplo Completo: Rota CAR → CGR (Campo Grande/MS)

Cadastro da rota para o parceiro Alemar em Campo Grande:

| Campo | Valor | Como obter |
|-------|-------|------------|
| **Unidade Origem** | CAR | Fixo |
| **Unidade Destino** | CGR | Sigla criada no POP-A02 |
| **Prazo de Transferencia** | 2 dias | Distancia ~1.000 Km |
| **Distancia** | 1.032 Km | Google Maps: Santana de Parnaiba → Campo Grande |
| **UFs Percorridas** | SP, MS | Trajeto: SP (origem) → MS (destino) |
| **Qtd Pedagogios** | 5 | Contagem aproximada no trajeto |
| **Hora de Corte** | (vazio) | CarVia nao usa |

**Validacao**:
- Cotacao ([002](../operacional/002-consulta-coletas.md)): CAR → Campo Grande/MS
- Prazo total: 2 (rota) + 2 (cidade) = **4 dias uteis**
- Valor pedagio: calculado com base em 5 postos

---

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| [401](../cadastros/401-cadastro-unidades.md) | Cadastro de unidades — origem e destino devem existir |
| [402](../cadastros/402-cidades-atendidas.md) | Cidades atendidas — prazo total = prazo rota + prazo cidade |
| [002](../operacional/002-consulta-coletas.md) | Cotacao — usa prazo da rota para calcular previsao de entrega |
| [004](../operacional/004-emissao-ctrcs.md) | Emissao CT-e — valida rota e prazo |
| [020](../operacional/020-manifesto-carga.md) | Manifesto de carga — usa UFs percorridas para MDF-e |
| [025](../operacional/025-saida-veiculos.md) | Saida de veiculo — emite MDF-e com UFs da rota |
| [030](../operacional/030-chegada-de-veiculo.md) | Chegada de veiculos — valida hora de corte da rota |
| [408](../comercial/408-comissao-unidades.md) | Comissionamento por rota — comissao especifica tem prioridade |
| [409](../comercial/409-remuneracao-veiculos.md) | Remuneracao de veiculos — usa distancia da rota |
| 060 | Feriados estaduais — considerados no calculo de prazo |
| 395 | Unidades alternativas — rotas devem existir para unidades alternativas |

---

## Observacoes e Gotchas

### Prazo de Transferencia

- Contado em **dias uteis** (nao inclui sabados, domingos e feriados)
- Feriados sao considerados **APOS** a contagem do prazo de transferencia, no destino
- Algoritmo SSW: Soma prazo de transferencia + prazo de entrega da cidade, entao aplica calendario de feriados

### Hora de Corte

- Define horario limite para chegada do manifesto na unidade destino
- Manifestos que chegam apos hora de corte: identificados como **ATRASADO** na [opcao 030](../operacional/030-chegada-de-veiculo.md)
- Se unidade destino tiver operacao FEC (fechada), chegada e identificada como **FECHADA**
- CarVia NAO usa hora de corte hoje

### Quantidade de Pedagogios

- Usada em tabelas de frete para calculo de valor de pedagio
- Total de pedagogios no frete = **pedagogios da rota ([403](../cadastros/403-rotas.md))** + **pedagogios da cidade ([402](../cadastros/402-cidades-atendidas.md))**
- Formula tipica: R$/frac 100Kg * (pedagogios rota + pedagogios cidade)

### Unidades Alternativas

- Opcao 395 permite trocar unidade de coleta/entrega automaticamente
- Rotas devem ser cadastradas para TODAS as unidades alternativas
- CarVia NAO usa unidades alternativas hoje

### Comissionamento

- [Opcao 408](../comercial/408-comissao-unidades.md) permite definir comissao especifica por rota
- Comissao por rota tem **prioridade** sobre comissao geral da unidade
- Permite diferenciar remuneracao por dificuldade ou distancia da rota

### UFs Percorridas (Critico)

- **Obrigatorio para MDF-e** (Manifesto de Documentos Fiscais Eletronicos)
- MDF-e e obrigatorio para transportes **interestaduais** de carga
- SEFAZ valida as UFs declaradas no MDF-e
- Erros nas UFs podem causar rejeicao do MDF-e e multas fiscais
- **Sempre verificar trajeto real no mapa** antes de cadastrar

### Rotas Bidirecionais

- Rotas sao **unidirecionais** no SSW
- CAR → CGR e diferente de CGR → CAR
- Para transporte bidirecional (ida e volta), cadastrar **ambas as rotas**
- Parametros podem ser diferentes (ex: prazo de volta menor por carregar vazio)

### Distancia para Calculo de Frete

- Distancia da rota ([403](../cadastros/403-rotas.md)) + distancia da cidade ([402](../cadastros/402-cidades-atendidas.md))
- Usada em algumas tabelas de frete que calculam por Km rodado
- CarVia usa tabelas por faixa de peso (420), nao por distancia
- Distancia e importante para calculo de **custo de combustivel** e **pedagio**

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A02 | Criar unidade parceira — pre-requisito obrigatorio |
| POP-A03 | Cadastrar cidades — prazo total = prazo rota + prazo cidade |
| POP-A10 | Implantar nova rota completa — este POP e a etapa 4 do A10 |
| POP-D03 | Criar manifesto e emitir MDF-e — usa UFs percorridas da rota |
| POP-D04 | Registrar chegada de veiculo — valida hora de corte |
| POP-C02 | Emitir CT-e carga direta — valida rota para transporte |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5 — sub-processo do POP-A10) |

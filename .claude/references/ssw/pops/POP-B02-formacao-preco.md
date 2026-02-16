# POP-B02 — Entender Formacao de Preco (Simulacao)

> **Categoria**: B — Comercial e Precificacao
> **Prioridade**: P1 (Alta — resolver problema recorrente de simulacao incorreta)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-16
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Documentar TODOS os componentes que formam o preco de um frete no SSW, explicando de onde vem cada parcela, qual opcao do SSW a controla e como diagnosticar quando a simulacao ([opcao 004](../operacional/004-emissao-ctrcs.md)) ou cotacao ([opcao 002](../operacional/002-consulta-coletas.md)) retorna um valor inesperado.

Este POP e mais **explicativo** (como o calculo funciona) do que operacional (como apertar botoes). Resolve o problema recorrente da CarVia: "a simulacao nao calcula certo e Rafael nao entende por que."

---

## Trigger

- Simulacao na [opcao 004](../operacional/004-emissao-ctrcs.md) retorna valor inesperado (muito alto, muito baixo ou zero)
- Cotacao na [opcao 002](../operacional/002-consulta-coletas.md) retorna valor diferente do esperado
- Cliente questiona composicao do frete
- Necessidade de entender margens antes de negociar desconto
- Novo componente de preco aparece na simulacao e ninguem sabe de onde veio

---

## Frequencia

Por demanda — sempre que houver duvida sobre formacao de preco. Recomendado: revisar apos cada implantacao de nova rota (POP-A10).

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Tabela de frete ativa | 417 / 418 / 420 | Tabela existe e Ativa = S para a rota |
| Parametros gerais | 903/Frete | Cubagem padrao, aprovacao, impostos |
| Parametros comerciais cliente | [423](../comercial/423-parametros-comerciais-cliente.md) | Cubagem por cliente, servicos adicionais |
| Custos de subcontratacao | [408](../comercial/408-comissao-unidades.md) | Comissoes das unidades parceiras |
| Tabela NTC (referencia) | [923](../comercial/923-cadastro-tabelas-ntc-generica.md) | Para calculo de desconto sobre NTC |
| Limites de cotacao | 469 / 369 | Valor minimo, resultado minimo |

---

## Passo-a-Passo

### ETAPA 1 — Componentes do Preco: O Que Forma o Frete

O frete no SSW e composto por **13 categorias de parcelas**. Cada parcela pode estar presente ou ausente dependendo da tabela do cliente e dos parametros configurados.

#### 1.1 Parcelas Basicas (sempre presentes)

| # | Parcela | Como e calculada | Onde configurar |
|---|---------|-------------------|-----------------|
| 1 | **Frete Peso** | R$/ton por faixa de peso (tabela progressiva) | Opcao 420 (por rota) ou 417 (combinada) |
| 2 | **Frete Valor (Ad Valorem)** | % sobre valor da mercadoria | [Opcao 417](../comercial/417-418-420-tabelas-frete.md) (combinada) ou 418 (percentual) |
| 3 | **Despacho** | R$ fixo por CTRC | [Opcao 417](../comercial/417-418-420-tabelas-frete.md) / 420 — campo "Despacho" |
| 4 | **Minimo** | Valor minimo garantido — se Frete Peso + Frete Valor + Despacho < Minimo, usa Minimo | [Opcao 417](../comercial/417-418-420-tabelas-frete.md) / 420 — campo "Minimo" |

> **NOTA CarVia**: A CarVia usa principalmente tabelas do tipo 420 (por rota). As tabelas sao organizadas como CARP-[SIGLA][POLO] — ex: CARP-CGRP (Campo Grande Polo).

#### 1.2 Taxas de Risco e Seguro

| # | Parcela | Como e calculada | Onde configurar |
|---|---------|-------------------|-----------------|
| 5 | **GRIS** | % sobre valor da mercadoria (gerenciamento de risco) | Tabela de frete (417/418/420) |
| 6 | **Ad Valorem (seguro)** | % sobre valor da mercadoria (seguro da carga) | Tabela de frete (417/418/420) |

#### 1.3 Pedagio

| # | Parcela | Como e calculada | Onde configurar |
|---|---------|-------------------|-----------------|
| 7 | **Pedagio** | R$ por fracao de 100Kg OU % sobre frete | Tabela de frete (417/418/420) + [opcao 402](../cadastros/402-cidades-atendidas.md) (por cidade) |

#### 1.4 Taxas Condicionais

Estas taxas so aparecem se o destinatario/rota se enquadrar nas condicoes:

| # | Parcela | Condicao para cobrar | Onde configurar | Prioridade |
|---|---------|----------------------|-----------------|------------|
| 8 | **TDE** (Dificil Entrega) | Destinatario marcado "Entrega Dificil" ([483](../cadastros/483-cadastro-clientes.md)) ou CNPJ raiz (394) | Tabela frete > Rota ([427](../comercial/427-resultado-por-cliente.md)) > Generica ([923](../comercial/923-cadastro-tabelas-ntc-generica.md)) > Tabela TDE (487) | 4 niveis |
| 9 | **TDC** (Dificil Coleta) | Configurado na [opcao 483](../cadastros/483-cadastro-clientes.md) do remetente | [Opcao 483](../cadastros/483-cadastro-clientes.md) |  |
| 10 | **TRT** (Restricao Transito) | Municipio com restricao para caminhoes grandes | Opcao 530 (areas por CEP, geral ou por cliente) |  |
| 11 | **TDA** (Dificil Acesso) | Cidade com acesso dificil | [Opcao 402](../cadastros/402-cidades-atendidas.md) (por cidade) ou 404 (por CEP, prioridade sobre 402) |  |
| 12 | **TAR** (Area de Risco) | Area de risco cadastrada | [Opcao 304](../comercial/304-areas-risco.md) |  |

> **Calculo das taxas**: Cada taxa pode ser: R$/ton, % sobre valor mercadoria, ou % sobre frete + minimo em R$. O modelo depende de como foi configurada na tabela ou opcao especifica.

#### 1.5 Coleta e Entrega

| # | Parcela | Condicao para cobrar | Onde configurar |
|---|---------|----------------------|-----------------|
| 13 | **Coleta** | R$ fixo — cobrada se placa de coleta informada (exceto ARMAZEM/ARMA999) | Tabela de frete (417/418/420) |
| 14 | **Entrega** | R$ fixo — NAO cobrada se destino = sigla da unidade ou BALCAO | Tabela de frete (417/418/420) |

> **CarVia fracionado**: Placa = ARMAZEM, portanto coleta geralmente NAO e cobrada.
> **CarVia carga direta**: Placa = placa real do veiculo, portanto coleta PODE ser cobrada.

#### 1.6 Servicos Adicionais

| # | Parcela | Condicao para cobrar | Onde configurar |
|---|---------|----------------------|-----------------|
| 15 | **Agendamento** | Cliente exige agendamento ([483](../cadastros/483-cadastro-clientes.md)) e servico configurado | [Opcao 483](../cadastros/483-cadastro-clientes.md) + 423 |
| 16 | **Paletizacao** | Cliente exige paletizacao ([483](../cadastros/483-cadastro-clientes.md)) e servico configurado | [Opcao 483](../cadastros/483-cadastro-clientes.md) + 423 |
| 17 | **Separacao** | Servico configurado | [Opcao 423](../comercial/423-parametros-comerciais-cliente.md) |
| 18 | **Capatazia** | Servico configurado | [Opcao 423](../comercial/423-parametros-comerciais-cliente.md) |
| 19 | **Veiculo Dedicado** | Servico configurado | [Opcao 423](../comercial/423-parametros-comerciais-cliente.md) |

#### 1.7 Impostos

| # | Parcela | Comportamento | Onde configurar |
|---|---------|---------------|-----------------|
| 20 | **ICMS** | Adicionado ao frete (se ICMS na tabela = N) OU ja incluso (se = S) | [Opcao 483](../cadastros/483-cadastro-clientes.md) + 903/Prazos |
| 21 | **PIS/COFINS** | Adicionado (se PIS/COFINS na tabela = N) OU ja incluso (se = S) | [Opcao 483](../cadastros/483-cadastro-clientes.md) + 903/Prazos |
| 22 | **ISS** | Em vez de ICMS, quando transporte e municipal (mesma cidade) | [Opcao 402](../cadastros/402-cidades-atendidas.md) (aliquota ISS por cidade) |

> **Padrao CarVia**: ICMS na tabela = S e PIS/COFINS na tabela = S (ja inclusos no preco). Portanto, o valor da tabela JA e o valor final para o cliente.

---

### ETAPA 2 — Formula de Calculo do Frete

A formula geral do frete no SSW segue esta logica:

```
FRETE BASE = MAX(Frete Peso + Frete Valor + Despacho, Minimo)

FRETE TOTAL = FRETE BASE
            + GRIS
            + Ad Valorem (seguro)
            + Pedagio
            + TDE (se aplicavel)
            + TDC (se aplicavel)
            + TRT (se aplicavel)
            + TDA (se aplicavel)
            + TAR (se aplicavel)
            + Coleta (se placa real)
            + Entrega (se destino nao e unidade/balcao)
            + Servicos adicionais (agendamento, paletizacao, etc.)
            + Impostos repassados (se nao inclusos na tabela)
```

**Notas importantes**:
- O "Frete Peso" e calculado sobre o **peso de calculo** = MAX(peso real, peso cubado)
- Peso cubado = volume (m3) x cubagem (Kg/m3)
- Cubagem: cliente ([423](../comercial/423-parametros-comerciais-cliente.md)) > transportadora ([903](../cadastros/903-parametros-gerais.md)) — padrao sugerido 300 Kg/m3
- Na base de calculo do ICMS, os valores de TRT ja estao incluidos (calculado antes)
- O campo "Val frete" NAO considera "Impostos Repassados"

---

### ETAPA 3 — De Onde Vem Cada Componente (Mapa de Opcoes)

| Componente | Opcao Primaria | Opcao Secundaria | Opcao Fallback |
|------------|----------------|-------------------|----------------|
| Frete Peso/Valor/Despacho/Minimo | 420 (rota) | [417](../comercial/417-418-420-tabelas-frete.md) (combinada) | [923](../comercial/923-cadastro-tabelas-ntc-generica.md) (NTC) |
| GRIS / Ad Valorem | Tabela de frete do cliente | — | — |
| Pedagio | Tabela de frete | [402](../cadastros/402-cidades-atendidas.md) (por cidade) | — |
| TDE | Tabela frete cliente | Rota ([427](../comercial/427-resultado-por-cliente.md)) | Generica ([923](../comercial/923-cadastro-tabelas-ntc-generica.md)) > Tabela 487 |
| TDC | [483](../cadastros/483-cadastro-clientes.md) (remetente) | — | — |
| TRT | 530 (areas por CEP) | — | — |
| TDA | 404 (por CEP) | [402](../cadastros/402-cidades-atendidas.md) (por cidade) | — |
| TAR | [304](../comercial/304-areas-risco.md) (areas risco) | — | — |
| Coleta / Entrega | Tabela de frete | — | — |
| Servicos adicionais | [423](../comercial/423-parametros-comerciais-cliente.md) (por cliente) | [483](../cadastros/483-cadastro-clientes.md) (flags) | — |
| Cubagem | [423](../comercial/423-parametros-comerciais-cliente.md) (cliente) | 903/Frete (transportadora) | — |
| ICMS/ISS | 410 (tributacao) | [402](../cadastros/402-cidades-atendidas.md) (ISS por cidade) | — |
| PIS/COFINS | 903/Prazos | — | — |
| Desconto max cotacao | [423](../comercial/423-parametros-comerciais-cliente.md) (cliente) | 469 (rota) | [903](../cadastros/903-parametros-gerais.md) (geral) |
| Resultado minimo | 469 (por rota) | 369 (por grupo) | — |

---

### ETAPA 4 — Prioridade de Selecao de Tabelas

O SSW seleciona a tabela de frete seguindo esta prioridade (1 = maior):

| Prioridade | Tipo | Opcao | Criterio |
|------------|------|-------|----------|
| 1 | Frete informado por usuario autorizado | [925](../cadastros/925-cadastro-usuarios.md) | Usuario com permissao "informa frete" |
| 2 | Cotacao contratada | [002](../operacional/002-consulta-coletas.md) | Mesmos criterios (CNPJ, rota, tabela, prazo) |
| 3 | Tabela de Rota (especifica) | [427](../comercial/427-resultado-por-cliente.md) | Origem + destino exatos |
| 4 | Tabela por UF destino | 417/418/420 | UF do destino |
| 5 | Tabela generica cliente | 417/418/420 | Sem restricao de destino |
| 6 | Tabela Generica NTC | [923](../comercial/923-cadastro-tabelas-ntc-generica.md) | Ultima opcao (referencia da transportadora) |

Dentro de cada nivel, a tabela **mais especifica** prevalece:
- Cidade > UF
- Com mercadoria especifica > sem mercadoria
- Com remetente especifico > sem remetente

---

### ETAPA 5 — Como Verificar na Simulacao (Opcao 004)

Para diagnosticar um calculo inesperado:

1. Acessar [opcao **004**](../operacional/004-emissao-ctrcs.md) (Emissao de CTRCs)
2. Preencher dados normais (CNPJ remetente, destinatario, NF, peso, valor, placa)
3. Clicar em **Simular** (NAO gravar ainda)
4. Na tela de resultado, verificar:

| O que verificar | Onde olhar | O que procurar |
|-----------------|------------|----------------|
| Tabela utilizada | Campo "Tabela" no resultado | Confere com tabela esperada? |
| Peso de calculo | Campo "Peso Calc" | E o peso real ou peso cubado? Qual cubagem foi usada? |
| Parcelas individuais | Detalhamento do frete | Cada componente esta correto? |
| Impostos | Campos ICMS/PIS/COFINS | Estao inclusos ou repassados? |
| Taxas condicionais | TDE/TDC/TRT/TDA/TAR | Alguma taxa apareceu que nao deveria? |

5. Para ver a composicao detalhada de um CTRC ja emitido:
   - [Opcao **101**](../comercial/101-resultado-ctrc.md) → pesquisar o CTRC → link **Resultado**
   - Opcao **392** → composicao do frete com link para tabela usada

---

### ETAPA 6 — Problemas Comuns que Causam Calculo Errado

#### Problema 1: Peso cubado muito alto

| Sintoma | Causa | Diagnostico | Solucao |
|---------|-------|-------------|---------|
| Frete muito acima do esperado para o peso | Cubagem padrao (300 Kg/m3) inflando o peso | Verificar peso calculo vs peso real | Configurar cubagem real do cliente na [opcao 423](../comercial/423-parametros-comerciais-cliente.md) |

**Exemplo**: Carga de 100kg, volume 1m3. Com cubagem 300, peso cubado = 300kg. Frete calculado sobre 300kg em vez de 100kg.

#### Problema 2: Tabela errada selecionada

| Sintoma | Causa | Diagnostico | Solucao |
|---------|-------|-------------|---------|
| Frete diferente do esperado (mais alto ou mais baixo) | SSW selecionou tabela diferente (generica vs especifica) | Opcao 392 → ver tabela usada | Verificar prioridade de tabelas. Garantir tabela correta ativa |

#### Problema 3: Taxas inesperadas

| Sintoma | Causa | Diagnostico | Solucao |
|---------|-------|-------------|---------|
| TDE aparecendo sem motivo | Destinatario marcado "Entrega Dificil" na 483 | [Opcao 483](../cadastros/483-cadastro-clientes.md) → campo Entrega Dificil | Desmarcar se nao e entrega dificil |
| TDA aparecendo | Cidade com TDA cadastrado na 402 | [Opcao 402](../cadastros/402-cidades-atendidas.md) → cidade destino → TDA | Verificar se TDA e correto para esta cidade |
| TRT aparecendo | CEP destino em area de restricao (530) | Opcao 530 → verificar CEP | Confirmar se restricao e valida |

#### Problema 4: Impostos duplicados ou ausentes

| Sintoma | Causa | Diagnostico | Solucao |
|---------|-------|-------------|---------|
| Frete total muito acima (impostos somados) | ICMS/PIS na tabela = N (impostos repassados) | [Opcao 483](../cadastros/483-cadastro-clientes.md) → campo "ICMS na tabela" | CarVia: definir S (ja incluso) |
| Frete abaixo do esperado | Impostos ja inclusos mas cliente espera valor + impostos | Conferir parametro 483 + 903 | Alinhar expectativa com configuracao |

#### Problema 5: Simulacao retorna zero ou erro

| Sintoma | Causa | Diagnostico | Solucao |
|---------|-------|-------------|---------|
| Frete = R$ 0,00 | Tabela inativa (Ativa = N) | Opcao 420/417 → campo Ativa | Ativar tabela (Ativa = S) |
| "Rota nao encontrada" | Rota CAR → destino nao existe | [Opcao 403](../cadastros/403-rotas.md) → buscar rota | Cadastrar rota (POP-A10) |
| "Cidade nao atendida" | CEP nao vinculado a unidade | [Opcao 402](../cadastros/402-cidades-atendidas.md) → buscar cidade | Vincular cidade a unidade parceira |

#### Problema 6: Opcao 062 nao configurada [CONFIRMAR]

| Sintoma | Causa | Diagnostico | Solucao |
|---------|-------|-------------|---------|
| Parametros de calculo incorretos ou ausentes | [Opcao 062](../comercial/062-parametros-frete.md) nao configurada ou com valores errados | [CONFIRMAR] Acessar [opcao 062](../comercial/062-parametros-frete.md) e verificar | Ver POP-B03 |

> **NOTA IMPORTANTE**: A [opcao 062](../comercial/062-parametros-frete.md) aparece referenciada na documentacao como "parametros de frete" e e mencionada como algo que Rafael "nao conhece" (CARVIA_OPERACAO.md). E possivel que esta opcao contenha configuracoes criticas que estao causando os problemas de simulacao. Ver POP-B03 para investigacao.

---

### ETAPA 7 — Fluxo de Diagnostico Rapido

Quando uma simulacao retorna valor inesperado, seguir este roteiro:

```
1. QUAL TABELA FOI USADA?
   → Opcao 392 (se CTRC ja emitido) ou verificar na simulacao da 004
   → E a tabela correta? Se nao, verificar prioridade de tabelas (ETAPA 4)

2. QUAL O PESO DE CALCULO?
   → Peso real vs peso cubado
   → Se cubado: qual cubagem? 423 do cliente ou 903 padrao?
   → Se cubagem esta inflando: ajustar na 423 ou informar cubagem real

3. QUAIS PARCELAS APARECEM?
   → Listar cada parcela e verificar se e esperada
   → Taxas condicionais (TDE/TDC/TRT/TDA/TAR) — conferir cadastros

4. IMPOSTOS ESTAO CORRETOS?
   → ICMS na tabela = S ou N? (CarVia padrao: S)
   → PIS/COFINS na tabela = S ou N? (CarVia padrao: S)

5. LIMITES ESTAO CONFIGURADOS?
   → Opcao 469 (por rota) → valor minimo, resultado minimo
   → Opcao 423 → desconto maximo proposta inicial
   → [CONFIRMAR] Opcao 062 → parametros adicionais

6. SE NADA ACIMA EXPLICA:
   → Verificar opcao 903/Frete (parametros gerais)
   → Contatar Suporte SSW se necessario
```

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Problema** | Simulacao na 004 frequentemente nao calcula certo | Diagnosticar causa raiz e corrigir configuracoes |
| **Conhecimento** | Rafael nao sabe todos os componentes do preco | Este POP documenta 100% dos componentes |
| **Opcao 062** | Rafael NAO CONHECE esta opcao | Investigar e configurar (POP-B03) |
| **Cubagem** | Possivelmente usando padrao 300 Kg/m3 | Configurar por cliente na 423 se necessario |
| **Impostos** | ICMS/PIS na tabela = S (ja incluso) | Manter — e o padrao correto para CarVia |
| **Diagnostico** | Trial and error | Seguir fluxo de diagnostico rapido (ETAPA 7) |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Frete 3x acima do esperado | Cubagem padrao inflando peso de calculo | [Opcao 423](../comercial/423-parametros-comerciais-cliente.md) → definir cubagem real do cliente |
| Tabela NTC sendo usada no lugar da tabela CarVia | Tabela especifica inativa ou inexistente | Opcao 420 → verificar se Ativa = S |
| Taxa TDE aparecendo em todas as cotacoes | Todos destinatarios marcados "Entrega Dificil" | [Opcao 483](../cadastros/483-cadastro-clientes.md) → revisar campo Entrega Dificil |
| Resultado comercial negativo | Custo parceiro ([408](../comercial/408-comissao-unidades.md)) maior que preco venda (420) | Revisar margem: preco 420 deve ser > custo 408 |
| Frete de coleta sendo cobrado no fracionado | Placa diferente de ARMAZEM | Na emissao ([004](../operacional/004-emissao-ctrcs.md)): usar placa ARMAZEM para fracionado |
| Simulacao da 002 diferente da 004 | Cotacao considera parametros adicionais (desconto) | Normal — 002 aplica desconto da proposta, 004 usa tabela direta |
| Desconto NTC % inconsistente | Tabela 427 (NTC) desatualizada ou inexistente | [Opcao 923](../comercial/923-cadastro-tabelas-ntc-generica.md)/427 → verificar tarifas NTC vigentes |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Tabela ativa para rota | Opcao 420 → origem CAR + destino → Ativa = S |
| Cubagem do cliente | [Opcao 423](../comercial/423-parametros-comerciais-cliente.md) → CNPJ → campo cubagem preenchido |
| Cubagem padrao transportadora | [Opcao 903](../cadastros/903-parametros-gerais.md)/Frete → campo cubagem padrao |
| ICMS na tabela | [Opcao 483](../cadastros/483-cadastro-clientes.md) → CNPJ cliente → campo "ICMS na tabela" = S |
| Limites por rota | Opcao 469 → filtrar por rota → valores preenchidos |
| Composicao do frete | Opcao 392 → numero CTRC → todas parcelas listadas |
| Resultado do CTRC | [Opcao 101](../comercial/101-resultado-ctrc.md)/Resultado → CTRC → receita vs despesas |
| Custos parceiro | [Opcao 408](../comercial/408-comissao-unidades.md) → unidade parceira → comissoes cadastradas |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-B01 | Cotar frete — usa o calculo documentado aqui |
| POP-B03 | Parametros de frete — configurar opcoes que controlam o calculo |
| POP-A07 | Cadastrar tabelas de preco — criar tabelas 420 por rota |
| POP-A06 | Cadastrar custos/comissoes — custo do parceiro na 408 |
| POP-A10 | Implantar nova rota — inclui tabelas, rotas e cidades |
| POP-C01 | Emitir CT-e fracionado — aplica o calculo na emissao |
| POP-C02 | Emitir CT-e carga direta — aplica o calculo na emissao |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-16 | Criacao inicial — documentacao completa de formacao de preco com 22 parcelas, formula e diagnostico | Claude (Agente Logistico) |

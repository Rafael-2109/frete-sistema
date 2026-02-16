# POP-A03 — Cadastrar Cidades Atendidas

> **Categoria**: A — Implantacao e Cadastros
> **Prioridade**: P1 (Alta — necessario para cotacao e emissao de CT-e)
> **Status CarVia**: JA FAZ
> **Opcoes SSW**: 402
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Cadastrar cidades atendidas pela CarVia atraves de transportadoras parceiras, definindo para cada cidade: unidade responsavel, classificacao de polo (P/R/I), prazos de entrega, parametros operacionais e adicionais de frete. Este cadastro alimenta as tabelas de frete (420) e define as pracas comerciais usadas na cotacao ([002](../operacional/002-consulta-coletas.md)) e emissao de CT-e ([004](../operacional/004-emissao-ctrcs.md)).

---

## Quando Executar (Trigger)

- Apos criar nova unidade parceira (POP-A02)
- Ampliar area de atendimento de parceiro existente
- Cliente solicita frete para cidade nao cadastrada
- Parte do processo de implantacao de nova rota (POP-A10)

---

## Frequencia

Por demanda — a cada novo parceiro ou expansao de area. Estimativa: 3-5 minutos por cidade (30-60 minutos para lote de 10-20 cidades de um parceiro).

---

## Pre-requisitos

- Unidade parceira criada na [opcao 401](../cadastros/401-cadastro-unidades.md) (POP-A02)
- Lista de cidades extraida do Sistema Fretes (app Nacom):
  - Cidades atendidas pelo parceiro
  - Classificacao de cada cidade: P (Polo), R (Regiao) ou I (Interior)
  - Lead times (prazos de entrega em dias uteis)
- Vinculos do Sistema Fretes validados
- Dados adicionais (opcionais): TDA, distancia, pedagogios

---

## Passo-a-Passo

### ETAPA 1 — Acessar e Filtrar Cidades

1. Acessar [opcao **402**](../cadastros/402-cidades-atendidas.md) (Cadastro de Cidades Atendidas)
2. Escolher o filtro apropriado na tela inicial:

| Filtro | Quando usar | Observacao |
|--------|-------------|------------|
| **UF** | Cadastrar varias cidades de uma UF | Traz todas as cidades da UF |
| **Unidade** | Revisar cidades de um parceiro | Traz cidades ja atendidas pela unidade |
| **Cidade/UF** | Cadastrar uma cidade especifica | Busca pontual |

3. **Recomendacao CarVia**: Usar filtro **UF** ao cadastrar novo parceiro (mais rapido)

> **Exemplo CGR**: Filtrar UF = MS para cadastrar todas as cidades do parceiro Alemar em Campo Grande/MS

---

### ETAPA 2 — Localizar e Acessar Cidade

4. Aguardar SSW carregar lista de cidades da UF
5. Localizar a cidade desejada na lista (ordem alfabetica)
6. Clicar na cidade para abrir a tela de cadastro

> **ATENCAO**: Se a cidade nao aparece na lista, ela nao existe na base de CEPs do SSW. Verificar se:
> - Nome da cidade esta correto (ex: "Embu das Artes" vs "Embu")
> - Cidade e muito nova ou foi emancipada recentemente
> - [Opcao 944](../cadastros/944-manutencao-tabela-ceps.md) (atualizacao de CEPs) precisa ser executada

---

### ETAPA 3 — Preencher Dados Operacionais

7. Preencher os campos obrigatorios:

| Campo | Valor CarVia | Observacao |
|-------|--------------|------------|
| **Unidade** | Sigla do parceiro (ex: CGR) | Unidade que atende operacionalmente |
| **Polo** | **P** | Cidade proxima da sede do parceiro |
| **Regiao** | **R** | Cidade de distancia media |
| **Interior** | **I** | Cidade distante ou de dificil acesso |
| **Tipo de frete** | **A** (Ambos) | CarVia atende CIF e FOB |
| **Restrita** | **N** | Usar S apenas para clientes especificos (opcao 134) |
| **Coleta** | **S** | Parceiro faz coletas na cidade |
| **Entrega** | **S** | Parceiro faz entregas na cidade |
| **Prazo de entrega** | Dias uteis conforme Sistema Fretes | Prazo partindo da sede da unidade parceira |

> **REGRA P/R/I**: Usar a classificacao extraida do Sistema Fretes. A classificacao define qual tabela de preco (420) sera aplicada: CARP-[SIGLA]P, CARP-[SIGLA]R ou CARP-[SIGLA]I.

8. **Praca Operacional** (campo automatico):
   - SSW forma automaticamente: Sigla Unidade + P/R/I
   - Exemplo: CGR + P = **CGRP** (Campo Grande Polo)
   - Exemplo: CGR + R = **CGRR** (Campo Grande Regiao)
   - Exemplo: CGR + I = **CGRI** (Campo Grande Interior)

9. **Praca Comercial** (campo opcional):
   - Deixar **vazio** para usar praca operacional
   - Permite agrupar varias cidades na mesma praca comercial para reduzir tabelas
   - CarVia NAO usa pracas comerciais personalizadas — deixar vazio

---

### ETAPA 4 — Preencher Campos Opcionais

10. Configurar campos opcionais conforme necessidade:

| Campo | Quando preencher | Valor tipico |
|-------|------------------|--------------|
| **Distancia** | Deixar vazio — SSW calcula via Google Maps | Calculado automaticamente |
| **Quantidade de pedagogios** | Se conhecido e relevante | Ex: 3 postos |
| **Valor TDA** | Se cidade tem dificil acesso | Ex: R$ 50,00 |
| **Valor SUFRAMA** | Se Zona Franca de Manaus | Ex: R$ 100,00 + 1% valor mercadoria |
| **Valor Coleta/Entrega** | Se cobra taxa fixa via tabela generica ([923](../comercial/923-cadastro-tabelas-ntc-generica.md)) | Ex: R$ 30,00 |
| **Prazo e-commerce** | Se cliente tem operacao e-commerce | Diferente do prazo normal |

> **Prioridade TDA**: [opcao 404](../cadastros/404-setores-coleta-entrega.md) (CEP) > [opcao 423](../comercial/423-parametros-comerciais-cliente.md) (cliente) > [opcao 402](../cadastros/402-cidades-atendidas.md) (cidade). Se configurar TDA aqui, ela tem a menor prioridade.

---

### ETAPA 5 — Configurar Complementos (Link MAIS)

11. Clicar no link **MAIS** (canto superior direito) para acessar complementos
12. Preencher campos adicionais:

| Campo | O que configurar | Observacao |
|-------|------------------|------------|
| **Observacoes** | Informacoes relevantes para cotacao | Aparece na [opcao 002](../operacional/002-consulta-coletas.md) |
| **Coletas/entregas** | Dias de semana que coletas/entregas sao realizadas | Seg a Sex (padrao), Sab (se aplicavel) |
| **Feriados municipais** | Feriados locais da cidade | SSW sugere com base FEBRABAN |
| **Aliquota ISS** | Para emissao RPS/NFS-e (opcoes [004](../operacional/004-emissao-ctrcs.md)/005/006) | Normal ou Substituicao Tributaria |

> **Feriados**: SSW ja traz feriados cadastrados pela FEBRABAN. Revisar e adicionar feriados municipais especificos se necessario. Feriados afetam o calculo de prazo de entrega.

---

### ETAPA 6 — Salvar e Replicar

13. Clicar em **Atualizar** para salvar o cadastro da cidade
14. SSW retorna para a lista de cidades da UF

**Tecnica de Replicacao (economia de tempo)**:

15. Se varias cidades tem a **mesma classificacao** (P, R ou I) e parametros similares:
    - Cadastrar a primeira cidade como modelo
    - Clicar no link **REPLICAR** (canto superior direito da tela da cidade)
    - Selecionar cidades destino na lista
    - SSW replica todos os parametros e calcula distancia via Google Maps automaticamente
    - Ajustar individualmente apenas o campo **Polo/Regiao/Interior** se necessario

> **Exemplo CGR** — Replicacao:
> 1. Cadastrar Campo Grande como modelo (P, prazo 2 dias)
> 2. Replicar para Sidrolandia, Terenos, Dourados — ajustar para R, prazo 3 dias
> 3. Replicar para Corumba, Ponta Pora — ajustar para I, prazo 5 dias

---

### ETAPA 7 — Importar Dados de Parceiro (Recurso Avancado)

**ATENCAO**: Recurso irreversivel — usar com cuidado.

16. Se o parceiro ja usa SSW e as cidades ja estao cadastradas no dominio dele:
    - Clicar em **"Importar dados do parceiro"**
    - Informar **CNPJ do parceiro**
    - Escolher tipo de importacao:
      - Importar cidades nao atendidas
      - Importar cidades atendidas por minha unidade
      - Importar todas as cidades do parceiro
    - Confirmar importacao

17. **POS-IMPORTACAO**:
    - Revisar TODAS as cidades importadas
    - Ajustar classificacao P/R/I conforme tabelas CarVia
    - Verificar prazos de entrega
    - Ajustar unidade responsavel se necessario

> **Contexto CarVia**: NUNCA usar importacao sem aprovacao do Rafael. A importacao pode sobrescrever cidades ja cadastradas e trazer configuracoes incompativeis com o padrao CarVia.

---

## Contexto CarVia

### Hoje

- Rafael cadastra manualmente todas as cidades de cada novo parceiro
- Fonte de dados: Sistema Fretes (app Nacom) — vinculos de cidades + polos + lead times
- Classificacao P/R/I: extraida do Sistema Fretes (fonte de verdade)
- Prazo de entrega: copiado do lead time do Sistema Fretes
- TDA, pedagogios, SUFRAMA: NAO usados hoje (valores zerados)
- Feriados municipais: NAO revisados (aceita sugestao SSW)

### Futuro (com POP implantado)

- Padronizacao do cadastro — mesmos criterios sempre
- Documentacao da fonte de dados (Sistema Fretes)
- Replicacao usada para economizar tempo
- Eventual automacao: sincronizacao Sistema Fretes → SSW (robo)
- Revisao de feriados municipais para cidades criticas (capitais)

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Cidade nao aparece na lista | Nome incorreto ou cidade muito nova | Verificar nome correto, executar [opcao 944](../cadastros/944-manutencao-tabela-ceps.md) (atualizacao CEPs) |
| Cotacao retorna R$ 0,00 | Cidade sem unidade ou classificacao P/R/I incorreta | Verificar unidade preenchida, praca operacional formada corretamente |
| Prazo de entrega errado no calculo | Prazo cadastrado diverge do Sistema Fretes | Revisar prazo na 402, considerar feriados municipais |
| Praca operacional duplicada | Duas cidades com mesma unidade + mesma classificacao P/R/I | Normal — cidades de mesmo polo compartilham praca |
| TDA nao aplicada no CT-e | TDA da cidade tem menor prioridade | Configurar TDA na [opcao 404](../cadastros/404-setores-coleta-entrega.md) (CEP) ou 423 (cliente) |
| Distancia zerada ou incorreta | SSW nao conseguiu calcular via Google Maps | Informar distancia manualmente (em Km) |
| Classificacao P/R/I diverge da tabela 420 | Cidade cadastrada com classificacao diferente da tabela | Corrigir classificacao ou criar tabela correspondente |
| Coleta=N ou Entrega=N bloqueia operacao | Parceiro nao atende coleta/entrega na cidade | Marcar Restrita=S e cadastrar clientes excepcionais na 134 |
| Replicacao sobrescreve cidades ja configuradas | Replicacao sem conferencia | SEMPRE revisar lista antes de confirmar replicacao |
| Importacao de parceiro traz lixo | Parceiro tinha cidades obsoletas ou erradas | EVITAR importacao — preferir cadastro manual |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Cidade cadastrada | [Opcao 402](../cadastros/402-cidades-atendidas.md) → filtrar por unidade → cidade aparece na lista |
| Unidade correta | [Opcao 402](../cadastros/402-cidades-atendidas.md) → abrir cidade → campo Unidade = sigla do parceiro |
| Classificacao P/R/I | [Opcao 402](../cadastros/402-cidades-atendidas.md) → abrir cidade → Polo/Regiao/Interior marcado |
| Praca operacional formada | [Opcao 402](../cadastros/402-cidades-atendidas.md) → abrir cidade → campo Praca Operacional = [SIGLA][P/R/I] |
| Prazo de entrega | [Opcao 402](../cadastros/402-cidades-atendidas.md) → abrir cidade → campo Prazo = dias conforme Sistema Fretes |
| Coleta e Entrega = S | [Opcao 402](../cadastros/402-cidades-atendidas.md) → abrir cidade → Coleta=S, Entrega=S |
| Tipo de frete = A | [Opcao 402](../cadastros/402-cidades-atendidas.md) → abrir cidade → Tipo de frete = Ambos |
| Cotacao reconhece cidade | [Opcao 002](../operacional/002-consulta-coletas.md) → destino = cidade cadastrada → valor retornado > 0 |

---

## Exemplo Completo: Campo Grande/MS (Parceiro Alemar)

Cadastro de 7 cidades do parceiro Alemar (unidade CGR):

| Cidade | UF | Classificacao | Praca | Prazo | Coleta | Entrega | Distancia |
|--------|-----|--------------|-------|-------|--------|---------|-----------|
| Campo Grande | MS | **P** | CGRP | 2 dias | S | S | Auto |
| Sidrolandia | MS | **R** | CGRR | 3 dias | S | S | Auto |
| Terenos | MS | **R** | CGRR | 3 dias | S | S | Auto |
| Dourados | MS | **R** | CGRR | 3 dias | S | S | Auto |
| Corumba | MS | **I** | CGRI | 5 dias | S | S | Auto |
| Ponta Pora | MS | **I** | CGRI | 5 dias | S | S | Auto |
| Tres Lagoas | MS | **I** | CGRI | 4 dias | S | S | Auto |

**Fluxo de cadastro**:
1. Filtrar UF = MS
2. Cadastrar Campo Grande como modelo (P, 2 dias)
3. Replicar para Sidrolandia, Terenos, Dourados → ajustar para R, 3 dias
4. Replicar para Corumba, Ponta Pora → ajustar para I, 5 dias
5. Cadastrar Tres Lagoas manualmente (I, 4 dias — prazo diferente)
6. Verificar cotacao para cada polo ([002](../operacional/002-consulta-coletas.md)): CGRP, CGRR, CGRI

---

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| [401](../cadastros/401-cadastro-unidades.md) | Unidade responsavel — deve existir antes de cadastrar cidades |
| [403](../cadastros/403-rotas.md) | Rotas — prazo total = prazo rota ([403](../cadastros/403-rotas.md)) + prazo cidade ([402](../cadastros/402-cidades-atendidas.md)) |
| 420 | Tabelas de frete — usam praca operacional ([SIGLA][P/R/I]) |
| [002](../operacional/002-consulta-coletas.md) | Cotacao — busca cidade e aplica tabela conforme praca |
| [004](../operacional/004-emissao-ctrcs.md) | Emissao CT-e — valida cidade, unidade e prazo |
| [404](../cadastros/404-setores-coleta-entrega.md) | Setores CEP — TDA por faixa de CEP tem prioridade sobre TDA da cidade |
| [423](../comercial/423-parametros-comerciais-cliente.md) | Tabelas por cliente — TDA do cliente tem prioridade sobre TDA da cidade |
| [427](../comercial/427-resultado-por-cliente.md) | Tabela generica — valores de coleta/entrega (se configurados na 402) |
| [923](../comercial/923-cadastro-tabelas-ntc-generica.md) | Tabela NTC — valores de coleta/entrega via tabela generica |
| 060 | Feriados estaduais — usados no calculo de prazo de entrega |
| 121 | Ajuste de prazos em lote — permite alterar prazos de varias cidades simultaneamente |
| [944](../cadastros/944-manutencao-tabela-ceps.md) | Atualizacao de CEPs — atualiza base de cidades quinzenalmente |

---

## Observacoes e Gotchas

### Praca Operacional vs Praca Comercial

- **Praca Operacional**: Formada automaticamente (sigla unidade + P/R/I). Define a operacao real.
- **Praca Comercial**: Permite agrupar varias pracas operacionais na mesma tabela de frete. CarVia NAO usa — deixar vazio.

### Calculo de Previsao de Entrega

- Prazo total = **Prazo transferencia** (rota 403) + **Prazo entrega** (cidade 402)
- Feriados considerados: municipais ([402](../cadastros/402-cidades-atendidas.md)), estaduais (060) e federais (automatico SSW)
- Prazo e-commerce: se configurado, tem prioridade sobre prazo normal
- Exemplo: CAR → CGR (2 dias) + Campo Grande (2 dias) = **4 dias uteis**

### Operacoes FEC (Fechada ou Completa)

- Cidade com operacao FEC nao precisa ser configurada na 402
- Pode ser cadastrada como FEC se quiser definir praca comercial diferente
- CarVia NAO usa operacao FEC — sempre configura na 402

### Taxas e Valores

- **TDA (Taxa Dificil Acesso)**: Prioridade → [opcao 404](../cadastros/404-setores-coleta-entrega.md) (CEP) > [opcao 423](../comercial/423-parametros-comerciais-cliente.md) (cliente) > [opcao 402](../cadastros/402-cidades-atendidas.md) (cidade)
- **SUFRAMA**: Para Zona Franca de Manaus. Tabelas de frete (420) tem prioridade sobre [opcao 402](../cadastros/402-cidades-atendidas.md)
- **Valor Coleta/Entrega**: Cobrado via Tabela Generica ([opcao 923](../comercial/923-cadastro-tabelas-ntc-generica.md))
- **Pedagogios**: Total = pedagogios da rota ([403](../cadastros/403-rotas.md)) + pedagogios da cidade ([402](../cadastros/402-cidades-atendidas.md))

### Unidades Alternativas

- Opcao 395 permite trocar unidade de coleta/entrega automaticamente
- CarVia NAO usa unidades alternativas hoje
- Se implantar no futuro: rotas devem ser cadastradas para unidades alternativas

### Atualizacao Automatica

- SSW ajusta diariamente: Unidade Responsavel e Unidade de Cobranca → Unidade Operacional
- Clientes configurados na [opcao 483](../cadastros/483-cadastro-clientes.md) com ajuste manual NAO sao alterados
- Divergencias sao listadas na opcao 090

### Importacao e Exportacao

- Funcao "Baixar arquivo CSV / Importar" permite alteracoes em massa
- Importacao de parceiro e **IRREVERSIVEL** — usar com cuidado extremo
- Funcao "Trocar unidades" permite substituir unidades mantendo classificacoes

### Faixas de CEPs

- Baseadas nos Correios
- Alteracoes podem ser feitas pela [opcao 944](../cadastros/944-manutencao-tabela-ceps.md) (requer cuidado)
- SSW atualiza CEPs quinzenalmente desde 2026

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A02 | Criar unidade parceira — pre-requisito obrigatorio |
| POP-A04 | Cadastrar rota — proximo passo apos cadastrar cidades |
| POP-A07 | Cadastrar tabela de preco — usa pracas operacionais ([SIGLA][P/R/I]) |
| POP-A10 | Implantar nova rota completa — este POP e a etapa 3 do A10 |
| POP-B01 | Cotar frete — usa cidades cadastradas para cotacao |
| POP-C01 | Emitir CT-e fracionado — valida cidade e prazo |
| POP-C02 | Emitir CT-e carga direta — valida cidade e prazo |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5 — sub-processo do POP-A10) |

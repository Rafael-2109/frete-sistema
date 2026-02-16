# POP-A07 — Cadastrar Tabelas de Preco por Rota

> **Categoria**: A — Implantacao e Cadastros
> **Prioridade**: P1 (Alta — necessario para cotacao e emissao de CT-e)
> **Status CarVia**: JA FAZ
> **Opcoes SSW**: 420
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Cadastrar tabelas de preco de venda da CarVia para rotas especificas, usando o modelo de faixas de peso progressivas (opcao 420). Cada rota tem 3 tabelas correspondentes aos tres polos de atendimento: P (Polo), R (Regiao) e I (Interior). As tabelas definem valores de frete cobrados dos clientes e sao usadas na cotacao ([002](../operacional/002-consulta-coletas.md)) e emissao de CT-e (004).

**Ponto critico**: O preco de venda CarVia (tabela 420) deve ser igual ao custo do parceiro (tabela 408 — opcao "Custos/Comissoes") mais a margem comercial da CarVia.

---

## Quando Executar (Trigger)

- Apos cadastrar rota (POP-A04) e custos de subcontratacao (POP-A06)
- Nova unidade parceira criada
- Ajuste de precos de venda (reajuste anual, novo cliente, condicao especial)
- Parte do processo de implantacao de nova rota (POP-A10)

---

## Frequencia

Por demanda — a cada novo parceiro ou ajuste de precos. Estimativa: 15-25 minutos para criar as 3 tabelas de uma rota (P, R, I).

---

## Pre-requisitos

- Rota cadastrada entre CAR e unidade destino ([opcao 403](../cadastros/403-rotas.md) — POP-A04)
- Custos de subcontratacao cadastrados ([opcao 408](../comercial/408-comissao-unidades.md) — POP-A06)
- Cidades cadastradas com classificacao P/R/I ([opcao 402](../cadastros/402-cidades-atendidas.md) — POP-A03)
- Tabela de precos do parceiro extraida do Sistema Fretes (fonte de verdade)
- Margem comercial CarVia definida (diferenca entre preco venda e custo)
- Cliente cadastrado ([opcao 483](../cadastros/483-cadastro-clientes.md) — POP-A01) se tabela for especifica

---

## Passo-a-Passo

### ETAPA 1 — Preparar Dados para as 3 Tabelas

1. Extrair do Sistema Fretes a tabela de precos do parceiro:
   - Precos por polo: **P** (Polo), **R** (Regiao), **I** (Interior)
   - Faixas de peso e valores por faixa (R$ fixo ou R$/Kg)
   - Despacho, GRIS, Ad Valorem, Pedagio
   - Valores adicionais: TDE, TDC, TRT, TDA

2. Calcular os precos de venda CarVia:
   - **Preco venda = Preco parceiro (Sistema Fretes) + Margem CarVia**
   - Margem tipica: 15-30% sobre o custo (variar conforme cliente e rota)
   - Aplicar margem em TODAS as faixas de peso

3. Definir a nomenclatura das 3 tabelas:

| Tabela | Nomenclatura | Descricao |
|--------|--------------|-----------|
| Polo | **CARP-[SIGLA]P** | CarVia Polo → [Cidade] Polo |
| Regiao | **CARP-[SIGLA]R** | CarVia Polo → [Cidade] Regiao |
| Interior | **CARP-[SIGLA]I** | CarVia Polo → [Cidade] Interior |

> **Exemplo CGR** (Campo Grande):
> - CARP-CGRP (CarVia → Campo Grande Polo)
> - CARP-CGRR (CarVia → Campo Grande Regiao)
> - CARP-CGRI (CarVia → Campo Grande Interior)

---

### ETAPA 2 — Criar Primeira Tabela (Polo)

4. Acessar opcao **420** (Tabela de Frete por Faixa de Peso)
5. Clicar em **Incluir** para criar nova tabela
6. Preencher os campos de identificacao:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Nome da Tabela** | CARP-[SIGLA]P | Ex: CARP-CGRP |
| **CNPJ Cliente** | (vazio para tabela geral) | Deixar vazio = tabela para todos os clientes |
| **Unidade origem** | **CAR** | Unidade operacional CarVia |
| **Unidade/UF destino** | Sigla do parceiro / UF | Ex: CGR / MS |
| **Ativa** | **S** | Tabela ativa para calculo de frete |
| **Data inicio** | Data atual | Inicio da validade |
| **Data fim** | (vazio) | Indeterminada |

7. Marcar campos de impostos:

| Campo | Valor CarVia | Observacao |
|-------|--------------|------------|
| **ICMS na tabela** | **S** | Preco ja inclui ICMS (nao repassa ao cliente) |
| **ISS na tabela** | **S** | Preco ja inclui ISS (nao repassa ao cliente) |
| **PIS/COFINS na tabela** | **S** | Preco ja inclui PIS/COFINS (nao repassa ao cliente) |

> **IMPORTANTE**: Com impostos **S** (ja inclusos), o valor informado na tabela e o valor **final** cobrado do cliente. Se marcar **N**, o SSW adiciona impostos como parcela separada, aumentando o frete.

---

### ETAPA 3 — Preencher Faixas de Peso (Polo)

8. Clicar na aba/secao **Faixas de Peso**
9. Informar as faixas progressivas conforme tabela do Sistema Fretes + margem CarVia:

**Exemplo ilustrativo** (CARP-CGRP — Polo):

| Faixa (ate Kg) | Tipo | Valor | Observacao |
|----------------|------|-------|------------|
| 50 | R$ fixo | 180,00 | Ate 50 Kg = R$ 180,00 |
| [100](../comercial/100-geracao-emails-clientes.md) | R$ fixo | 280,00 | De 51 a 100 Kg = R$ 280,00 |
| 200 | R$/Kg | 3,20 | De 101 a 200 Kg = 3,20 x peso |
| [500](../comercial/500-liquidacao-parcial-fatura-arquivo.md) | R$/Kg | 2,80 | De 201 a 500 Kg = 2,80 x peso |
| 1.000 | R$/Kg | 2,40 | De 501 a 1.000 Kg = 2,40 x peso |
| 5.000 | R$/Kg | 2,00 | De 1.001 a 5.000 Kg = 2,00 x peso |
| 10.000 | R$/Kg | 1,60 | Acima de 5.000 Kg = 1,60 x peso |

> **NOTA**: Valores acima sao **ILUSTRATIVOS**. Os valores reais vem do Sistema Fretes (custo parceiro) + margem CarVia.

10. Conferir que:
    - Faixas estao em ordem crescente
    - Valores R$/Kg diminuem conforme peso aumenta (preco degressive)
    - Ultima faixa cobre o peso maximo esperado (ex: 10.000 Kg)

---

### ETAPA 4 — Preencher Adicionais (Polo)

11. Clicar na aba/secao **Adicionais**
12. Preencher os valores de adicionais:

**Taxas Percentuais**:

| Adicional | Base Calculo | Valor Tipico | Observacao |
|-----------|--------------|--------------|------------|
| **GRIS** | % valor mercadoria | 0,30% | Gerenciamento de Risco |
| **Ad Valorem** | % valor mercadoria | 0,10% | Seguro da carga |
| **Pedagio** | R$/frac 100Kg | Conforme rota | Ex: R$ 8,00 por fracao de 100Kg |

**Taxas Fixas**:

| Adicional | Valor Tipico | Observacao |
|-----------|--------------|------------|
| **Despacho** | R$ fixo por CTRC | Ex: R$ 35,00 |

**Taxas Condicionais** (configurar se aplicavel):

| Adicional | Calculo | Quando aplicar |
|-----------|---------|----------------|
| **TDE** | R$/ton, % val merc, % frete + min R$ | Destinatario em local de dificil entrega |
| **TDC** | R$/ton, % val merc, % frete + min R$ | Remetente em local de dificil coleta |
| **TRT** | R$/ton, % val merc, % frete + min R$ | Area de restricao de transito |
| **TDA** | R$/ton, % val merc, % frete + min R$ | Area de dificil acesso |

> **Prioridade TDE**: Tabela 420 (aqui) > [opcao 427](../comercial/427-resultado-por-cliente.md) (rota) > [opcao 923](../comercial/923-cadastro-tabelas-ntc-generica.md) (generica) > [opcao 487](../financeiro/487-tabela-tde-externa.md) (especifica). TDE = 0 e reconhecido (zera cobranca).

13. Configurar **Cubagem** (se aplicavel):
    - Cubagem = Kg por metro cubico (m³)
    - Valor tipico: 300 Kg/m³
    - Frete calculado sobre o maior: peso real ou peso cubado
    - Peso cubado = volume (m³) x cubagem

---

### ETAPA 5 — Salvar Primeira Tabela (Polo)

14. Conferir todos os campos preenchidos:
    - Nome: CARP-[SIGLA]P
    - Origem: CAR
    - Destino: sigla do parceiro + UF
    - Ativa: S
    - Impostos: S (ja inclusos)
    - Faixas de peso completas
    - Adicionais configurados

15. Clicar em **Gravar** para salvar a tabela

16. SSW confirma cadastro e retorna para lista de tabelas

---

### ETAPA 6 — Criar Segunda Tabela (Regiao)

17. Repetir **ETAPA 2 a ETAPA 5** para a tabela de **Regiao**:
    - Nome: **CARP-[SIGLA]R** (ex: CARP-CGRR)
    - Demais campos identicos a tabela Polo
    - **Valores diferentes**: Regiao tem precos ~10-20% maiores que Polo

**Exemplo ilustrativo** (CARP-CGRR — Regiao):

| Faixa (ate Kg) | Tipo | Valor | Observacao |
|----------------|------|-------|------------|
| 50 | R$ fixo | 210,00 | (+16% sobre Polo) |
| [100](../comercial/100-geracao-emails-clientes.md) | R$ fixo | 320,00 | (+14% sobre Polo) |
| 200 | R$/Kg | 3,60 | (+12% sobre Polo) |
| [500](../comercial/500-liquidacao-parcial-fatura-arquivo.md) | R$/Kg | 3,20 | (+14% sobre Polo) |
| 1.000 | R$/Kg | 2,80 | (+16% sobre Polo) |
| 5.000 | R$/Kg | 2,30 | (+15% sobre Polo) |
| 10.000 | R$/Kg | 1,90 | (+18% sobre Polo) |

---

### ETAPA 7 — Criar Terceira Tabela (Interior)

18. Repetir **ETAPA 2 a ETAPA 5** para a tabela de **Interior**:
    - Nome: **CARP-[SIGLA]I** (ex: CARP-CGRI)
    - Demais campos identicos a tabela Polo
    - **Valores diferentes**: Interior tem precos ~20-40% maiores que Polo

**Exemplo ilustrativo** (CARP-CGRI — Interior):

| Faixa (ate Kg) | Tipo | Valor | Observacao |
|----------------|------|-------|------------|
| 50 | R$ fixo | 250,00 | (+38% sobre Polo) |
| [100](../comercial/100-geracao-emails-clientes.md) | R$ fixo | 370,00 | (+32% sobre Polo) |
| 200 | R$/Kg | 4,20 | (+31% sobre Polo) |
| [500](../comercial/500-liquidacao-parcial-fatura-arquivo.md) | R$/Kg | 3,80 | (+35% sobre Polo) |
| 1.000 | R$/Kg | 3,40 | (+41% sobre Polo) |
| 5.000 | R$/Kg | 2,80 | (+40% sobre Polo) |
| 10.000 | R$/Kg | 2,30 | (+43% sobre Polo) |

---

### ETAPA 8 — Verificar Tabelas na Cotacao

19. Validar as 3 tabelas criadas:
    - Acessar [opcao **002**](../operacional/002-consulta-coletas.md) (Cotacao)
    - Simular frete para **cidade Polo** da rota:
      - Origem: CAR
      - Destino: cidade Polo (ex: Campo Grande/MS)
      - Peso: 100 Kg (teste)
      - Valor mercadoria: R$ 5.000,00
    - Verificar que a tabela **CARP-[SIGLA]P** foi aplicada
    - Conferir valor retornado

20. Repetir para **cidade Regiao** e **cidade Interior**:
    - Destino Regiao: ex: Sidrolandia/MS
    - Destino Interior: ex: Corumba/MS
    - Verificar que tabelas **CARP-[SIGLA]R** e **CARP-[SIGLA]I** foram aplicadas

21. **Se cotacao retornar valor zerado ou tabela incorreta**:
    - Verificar se tabela esta **Ativa = S**
    - Verificar se cidade de destino tem classificacao P/R/I correta na [opcao 402](../cadastros/402-cidades-atendidas.md)
    - Verificar se praca operacional da cidade bate com o destino da tabela
    - Verificar se origem/destino/UF estao corretos na tabela 420

---

## Contexto CarVia

### Hoje

- Rafael cadastra manualmente as 3 tabelas (P/R/I) para cada rota
- Fonte de precos: Sistema Fretes (tabela do parceiro) + margem CarVia
- Margem aplicada: varia por cliente e rota (15-30%)
- Nomenclatura: CARP-[SIGLA][P/R/I] — padrao rigido
- Impostos: SEMPRE marcados S (ja inclusos)
- TDE, TDC, TRT, TDA: NAO usados hoje (valores zerados)
- Cubagem: NAO configurada

### Futuro (com POP implantado)

- Padronizacao do processo — criterios claros de margem
- Rastreabilidade: tabela 420 (venda) sempre vinculada a tabela 408 (custo)
- Revisao periodica: reajuste anual com base em inflacao e custos
- Possivel automacao: sincronizacao Sistema Fretes → SSW
- Uso de TDE/TDC para clientes especificos
- Cubagem configurada para cargas volumosas

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Cotacao retorna R$ 0,00 | Tabela nao encontrada ou Ativa=N | Verificar se tabela existe, esta ativa, e origem/destino corretos |
| Tabela errada aplicada | Classificacao P/R/I da cidade diverge da tabela | Corrigir classificacao na 402 ou criar tabela correspondente |
| Valor muito alto/baixo | Faixas de peso incorretas ou margem errada | Revisar faixas, recalcular margem com base no Sistema Fretes |
| Frete com imposto duplicado | ICMS/ISS/PIS na tabela = N | Marcar S (ja incluso) — padrao CarVia |
| Pedagio nao calculado | Qtd pedagogios nao configurada na rota ([403](../cadastros/403-rotas.md)) ou cidade ([402](../cadastros/402-cidades-atendidas.md)) | Informar pedagogios na 403 e/ou 402 |
| Despacho nao aplicado | Despacho zerado ou nao informado | Preencher valor de despacho nos adicionais |
| GRIS nao calculado | GRIS zerado ou valor mercadoria nao informado | Configurar GRIS % na tabela, informar valor mercadoria na cotacao |
| Cubagem aplicada incorretamente | Cubagem configurada mas cliente nao usa | Deixar cubagem zerada ou criar tabela especifica por cliente |
| Tabela duplicada | Ja existe tabela com mesmo nome ou origem/destino | Verificar se rota ja foi implantada, usar funcao Editar |
| Margem negativa | Preco venda menor que custo ([408](../comercial/408-comissao-unidades.md)) | Revisar calculo de margem, ajustar faixas de peso |
| Cliente especifico nao usa tabela | CNPJ informado na tabela mas cliente sem vinculo | Deixar CNPJ vazio para tabela geral |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| 3 tabelas criadas | Opcao 420 → pesquisar CARP-[SIGLA] → 3 tabelas (P/R/I) na lista |
| Tabelas ativas | Opcao 420 → abrir cada tabela → Ativa = S |
| Origem/destino corretos | Opcao 420 → abrir cada tabela → origem=CAR, destino=sigla parceiro |
| Faixas de peso completas | Opcao 420 → abrir cada tabela → faixas progressivas ate peso maximo |
| Adicionais configurados | Opcao 420 → abrir cada tabela → GRIS, Ad Valorem, Despacho, Pedagio |
| Impostos inclusos | Opcao 420 → abrir cada tabela → ICMS/ISS/PIS = S |
| Cotacao Polo funciona | [Opcao 002](../operacional/002-consulta-coletas.md) → destino cidade Polo → tabela P aplicada, valor > 0 |
| Cotacao Regiao funciona | [Opcao 002](../operacional/002-consulta-coletas.md) → destino cidade Regiao → tabela R aplicada, valor > 0 |
| Cotacao Interior funciona | [Opcao 002](../operacional/002-consulta-coletas.md) → destino cidade Interior → tabela I aplicada, valor > 0 |
| Valores progressivos | Verificar que Interior > Regiao > Polo (em R$/Kg) |

---

## Exemplo Completo: Tabelas CARP-CGR (Campo Grande/MS)

Resumo das 3 tabelas criadas para a rota CGR (parceiro Alemar):

| Tabela | Nome | Destino | Faixa 100 Kg | Faixa 500 Kg | Despacho | GRIS | Pedagio |
|--------|------|---------|--------------|--------------|----------|------|---------|
| Polo | CARP-CGRP | CGR / MS | R$ 280,00 | R$ 2,80/Kg | R$ 35,00 | 0,30% | R$ 8,00/100Kg |
| Regiao | CARP-CGRR | CGR / MS | R$ 320,00 | R$ 3,20/Kg | R$ 35,00 | 0,30% | R$ 8,00/100Kg |
| Interior | CARP-CGRI | CGR / MS | R$ 370,00 | R$ 3,80/Kg | R$ 35,00 | 0,30% | R$ 8,00/100Kg |

**Validacao**:
- Cotacao ([002](../operacional/002-consulta-coletas.md)): CAR → Campo Grande/MS (100 Kg, R$ 5.000) = R$ 280,00 + R$ 35,00 + R$ 15,00 (GRIS) + R$ 8,00 (pedagio) = **R$ 338,00**
- Cotacao ([002](../operacional/002-consulta-coletas.md)): CAR → Sidrolandia/MS (100 Kg, R$ 5.000) = R$ 320,00 + R$ 35,00 + R$ 15,00 + R$ 8,00 = **R$ 378,00**
- Cotacao ([002](../operacional/002-consulta-coletas.md)): CAR → Corumba/MS (100 Kg, R$ 5.000) = R$ 370,00 + R$ 35,00 + R$ 15,00 + R$ 8,00 = **R$ 428,00**

---

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| [402](../cadastros/402-cidades-atendidas.md) | Cidades atendidas — classificacao P/R/I define qual tabela e aplicada |
| [403](../cadastros/403-rotas.md) | Rotas — deve existir rota CAR → destino |
| [408](../comercial/408-comissao-unidades.md) | Custos/comissoes — custo do parceiro (base para calcular margem) |
| [001](../operacional/001-cadastro-coletas.md) | Coleta — usa tabela para calcular valor estimado |
| [002](../operacional/002-consulta-coletas.md) | Cotacao — aplica tabela conforme origem/destino/polo |
| 004/005/006 | Emissao CTRC/CT-e — aplica tabela no calculo de frete |
| [101](../comercial/101-resultado-ctrc.md) | Resultado CTRC — mostra tabela utilizada e margem |
| 392 | Composicao frete — link para tabela usada |
| 417/418 | Outros tipos de tabela — prioridades diferentes |
| [427](../comercial/427-resultado-por-cliente.md) | Tabela de rota — prioridade sobre tabela geral (420) |
| [423](../comercial/423-parametros-comerciais-cliente.md) | Tabela por cliente — permite adicionais especificos |
| [487](../financeiro/487-tabela-tde-externa.md) | Tabela TDE especifica — TDE por destinatario |
| 494/495 | Tabelas por volume/m³ — alternativas a faixa de peso |
| [923](../comercial/923-cadastro-tabelas-ntc-generica.md) | Tabela NTC — referencia geral |

---

## Observacoes e Gotchas

### Prioridades de Tabelas

Quando ha multiplas tabelas para um cliente/rota, SSW aplica esta ordem de prioridade:
1. **Tabela de Rota** ([opcao 427](../comercial/427-resultado-por-cliente.md)) — maior prioridade
2. **Tabela especifica UF destino** (opcao 420 com UF)
3. **Tabela generica cliente** (opcao 420 sem UF)
4. **Tabela NTC** ([opcao 923](../comercial/923-cadastro-tabelas-ntc-generica.md)) — menor prioridade (referencia)

CarVia usa opcao 420 com UF especifica (prioridade 2).

### Impostos Inclusos vs Repassados

- **ICMS/ISS/PIS na tabela = S**: Valor informado e o valor **final** cobrado do cliente
- **ICMS/ISS/PIS na tabela = N**: SSW adiciona impostos como parcela separada, aumentando o frete
- **Padrao CarVia**: SEMPRE S (ja inclusos) para evitar confusao e garantir preco final

### Cubagem

- Cubagem = Kg por m³
- Peso cubado = volume (m³) x cubagem
- Frete calculado sobre o **maior**: peso real ou peso cubado
- Cubagem padrao: [opcao 423](../comercial/423-parametros-comerciais-cliente.md) (por cliente)
- CarVia NAO usa cubagem hoje — deixar zerada

### TDE (Taxa Dificil Entrega)

- **Prioridade**: Tabela 420 (aqui) > Tabela rota 427 > Tabela generica 923 > Tabela especifica 487
- Destinatario deve estar marcado "Entrega Dificil" ([opcao 483](../cadastros/483-cadastro-clientes.md)) ou raiz CNPJ (opcao 394)
- TDE = 0 e reconhecido (zera cobranca — permite anular TDE em tabela especifica)

### TRT (Taxa Restricao Transito)

- Municipios restringem trafego de caminhoes grandes
- Tabela geral: opcao 530 (por CEP)
- Areas de restricao: geral ou por cliente
- FOB Dirigido: area deve estar no cliente REMETENTE

### Base de Calculo

- Valores com ICMS (integral) quando impostos sao base para calculos secundarios
- "Val frete" NAO considera "Impostos Repassados" (TRT calculado antes, entra na base ICMS)

### Replicacao e Importacao

- **Replicar**: copiar tabela entre clientes/unidades (funcao disponivel na 420)
- **CSV**: baixar, editar, importar (sobrepoe cadastrados)
- Historico de alteracoes: rastreabilidade de mudancas

### FOB Dirigido

- Tabela DEVE estar cadastrada no **cliente REMETENTE** (nao pagador)
- Remetente escolhe transportadora
- Marcar "FOB Dirigido = S" na tabela
- CarVia NAO usa FOB Dirigido hoje

### Simulacao

- Tabela com "Ativa = N" nao e usada em calculos reais
- Permite testar precos antes de ativar
- Util para apresentacoes comerciais ou validacao de custos

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A03 | Cadastrar cidades — classificacao P/R/I define qual tabela e aplicada |
| POP-A04 | Cadastrar rota — deve existir rota CAR → destino |
| POP-A06 | Cadastrar custos — custo parceiro ([408](../comercial/408-comissao-unidades.md)) e base para calcular margem |
| POP-A10 | Implantar nova rota completa — este POP e a etapa 7 do A10 |
| POP-B01 | Cotar frete — usa tabela para calcular valor |
| POP-C01 | Emitir CT-e fracionado — aplica tabela no calculo de frete |
| POP-C02 | Emitir CT-e carga direta — aplica tabela no calculo de frete |
| POP-B04 | Analisar resultado por CTRC — mostra tabela utilizada e margem |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5 — sub-processo do POP-A10) |

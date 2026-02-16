# POP-A10 — Implantar Nova Rota Completa

> **Categoria**: A — Implantacao e Cadastros
> **Prioridade**: P1 (Alta — processo frequente e complexo)
> **Status anterior**: JA FAZ
> **Criado em**: 2026-02-16
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Implantar uma rota completa no SSW da CarVia para atender uma cidade/regiao nao cadastrada, criando todos os cadastros necessarios: unidade do parceiro, cidades atendidas, fornecedor, custos de subcontratacao, rota e tabelas de preco. Este e um processo COMPOSTO que executa sequencialmente os processos A02 a A07 (opcoes [401](../cadastros/401-cadastro-unidades.md) -> [402](../cadastros/402-cidades-atendidas.md) -> [403](../cadastros/403-rotas.md) -> [478](../financeiro/478-cadastro-fornecedores.md) -> [408](../comercial/408-comissao-unidades.md) -> 420).

Ao final, a rota deve estar operacional para cotacao ([002](../operacional/002-consulta-coletas.md)) e emissao de CT-e (004).

---

## Trigger

- Cliente solicita frete para cidade/regiao nao cadastrada no SSW
- Jessica recebe demanda comercial e Rafael identifica que nao existe rota implantada
- Cotacao ([002](../operacional/002-consulta-coletas.md)) retorna erro ou valor zerado por ausencia de tabela/rota

---

## Frequencia

Por demanda — a cada nova regiao de atendimento. Estimativa: 30-60 minutos por rota completa.

---

## Pre-requisitos

| Requisito | Fonte | O que verificar |
|-----------|-------|-----------------|
| Parceiro identificado | Sistema Fretes (app Nacom) | Qual transportadora melhor atende a regiao |
| Tabela de precos do parceiro | Sistema Fretes | Precos por polo (P/R/I) extraidos |
| Vinculos de cidades do parceiro | Sistema Fretes | Cidades atendidas, polos e lead times |
| CNPJ do parceiro | Documentacao | CNPJ da transportadora parceira |
| Endereco do parceiro na cidade | Documentacao | Endereco da filial/base do parceiro |
| Dados CarVia disponiveis | SSW/Documentacao | CNPJ CarVia, conta bancaria CarVia, dados ESSOR |

> **IMPORTANTE**: O Sistema Fretes (app Nacom) e a **fonte de verdade** para precos de transportadoras. O SSW recebe uma versao "CarVia" dessas tabelas (com margem aplicada).

---

## Passo-a-Passo

### ETAPA 1 — Identificar Parceiro e Extrair Dados do Sistema Fretes

1. No **Sistema Fretes** (app Nacom), identificar qual transportadora melhor atende a regiao solicitada
2. Extrair a **tabela de precos** do parceiro:
   - Precos por polo: Polo (P), Regiao (R), Interior (I)
   - Faixas de peso e valores por faixa
   - Despacho, GRIS, Ad Valorem, Pedagio
3. Extrair os **vinculos de cidades**:
   - Lista de cidades atendidas pela filial do parceiro
   - Classificacao de cada cidade: P, R ou I
   - Lead times (prazos de entrega em dias uteis)
4. Definir a **margem CarVia** sobre os precos do parceiro
   - Preco CarVia (tabela 420) = Preco parceiro (tabela 408) + margem

> **Exemplo CGR**: No Sistema Fretes, identificar que a **Alemar Transportes** atende Campo Grande/MS com filial propria. Extrair tabela Alemar com precos para Polo (Campo Grande cidade), Regiao (cidades proximas como Sidrolandia, Terenos) e Interior (cidades distantes como Corumba, Ponta Pora).

---

### ETAPA 2 — Criar Unidade do Parceiro (Opcao 401)

5. Acessar [opcao **401**](../cadastros/401-cadastro-unidades.md)
6. Incluir nova unidade com os dados:

| Campo | Valor | Exemplo CGR |
|-------|-------|-------------|
| **Sigla** | Codigo IATA da cidade (3 letras) | CGR |
| **Tipo** | T (Terceiro) | T |
| **CNPJ** | CNPJ da **CarVia** (nao do parceiro) | CNPJ CarVia |
| **Inscricao Estadual** | IE da CarVia (se aplicavel na UF) | — |
| **Razao Social** | "Transportadora - Cidade/UF" | Alemar - Campo Grande/MS |
| **UF** | UF da cidade destino | MS |
| **Banco/Agencia/Conta** | Conta bancaria da **CarVia** | Conta CarVia |

> **ATENCAO**: O CNPJ na unidade tipo T e o da **CarVia**, nao o do parceiro. O parceiro sera cadastrado como fornecedor (etapa 5). A unidade representa a CarVia operando naquela praca via parceiro.

7. Confirmar cadastro
8. **NAO** configurar parametrizacao fiscal (opcao 920) — unidades tipo T nao emitem documentos fiscais

> **Dados de seguro**: ESSOR Seguros. Configuracao de seguro e global da CarVia, nao por unidade.

---

### ETAPA 3 — Cadastrar Cidades Atendidas (Opcao 402)

9. Acessar [opcao **402**](../cadastros/402-cidades-atendidas.md)
10. Para **cada cidade** extraida do Sistema Fretes, cadastrar:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Unidade** | Sigla criada na etapa 2 (ex: CGR) | Unidade que atende operacionalmente |
| **Polo/Regiao/Interior** | P, R ou I conforme Sistema Fretes | Define a Praca Operacional |
| **Tipo de frete** | A (Ambos) | CarVia atende CIF e FOB |
| **Coleta** | S | Parceiro faz coletas na cidade |
| **Entrega** | S | Parceiro faz entregas na cidade |
| **Prazo de entrega** | Dias uteis conforme Sistema Fretes | Prazo partindo da sede da unidade |
| **Distancia** | Deixar vazio — SSW calcula via Google Maps | Opcional |
| **Qtd Pedagios** | Informar se conhecido | Opcional |

> **Praca Operacional**: Formada automaticamente pela sigla da unidade + P/R/I. Exemplo: CGRP (Campo Grande Polo), CGRR (Campo Grande Regiao), CGRI (Campo Grande Interior).

11. **Tecnica de Replicacao** (economia de tempo):
    - Cadastrar a primeira cidade como modelo (ex: Campo Grande = Polo, prazo 2 dias)
    - Usar funcao **REPLICAR** para cidades com mesma classificacao
    - Ajustar apenas o campo Polo/Regiao/Interior e prazo individualmente

> **Exemplo CGR** — Cidades tipicas:
>
> | Cidade | UF | Classificacao | Prazo |
> |--------|-----|--------------|-------|
> | Campo Grande | MS | **P** (Polo) | 2 dias |
> | Sidrolandia | MS | **R** (Regiao) | 3 dias |
> | Terenos | MS | **R** (Regiao) | 3 dias |
> | Corumba | MS | **I** (Interior) | 5 dias |
> | Ponta Pora | MS | **I** (Interior) | 5 dias |
> | Dourados | MS | **R** (Regiao) | 3 dias |
> | Tres Lagoas | MS | **I** (Interior) | 4 dias |

---

### ETAPA 4 — Cadastrar Rota (Opcao 403)

12. Acessar [opcao **403**](../cadastros/403-rotas.md)
13. Cadastrar a rota de transferencia:

| Campo | Valor | Exemplo CGR |
|-------|-------|-------------|
| **Unidade Origem** | CAR (CarVia Santana de Parnaiba) | CAR |
| **Unidade Destino** | Sigla da etapa 2 | CGR |
| **Prazo de Transferencia** | Dias uteis para transferencia SP → destino | 2 dias |
| **Hora de Corte** | Horario limite para chegada | (deixar padrao) |
| **Qtd Pedagios** | Postos de pedagio no trajeto CAR → destino | (informar se conhecido) |

> **Calculo de prazo total**: Prazo transferencia (rota 403) + Prazo entrega (cidade 402).
> Exemplo: CAR → CGR (2 dias) + Campo Grande Polo (2 dias) = **4 dias uteis** total.

---

### ETAPA 5 — Cadastrar Fornecedor (Opcao 478)

14. Acessar [opcao **478**](../financeiro/478-cadastro-fornecedores.md)
15. Verificar se o parceiro ja esta cadastrado (pesquisar por CNPJ)
    - **Se ja existe**: Verificar se CCF esta ativa (passo 17). Pular para passo 17
    - **Se nao existe**: Prosseguir com cadastro
16. Cadastrar novo fornecedor:

| Campo | Valor | Exemplo CGR |
|-------|-------|-------------|
| **CNPJ** | CNPJ da **transportadora parceira** | CNPJ Alemar |
| **Razao Social** | Nome juridico do parceiro | ALEMAR TRANSPORTES LTDA |
| **Especialidade** | Agencias/Parceiros | Agencias/Parceiros |
| **Ativo** | S | S |
| **UF** | UF da sede do parceiro | MS |
| **Banco/Agencia/Conta** | Conta bancaria do **parceiro** (se pagamentos diretos) | Conta Alemar |

17. **Ativar CCF** (Conta Corrente de Fornecedor):
    - Marcar **"CCF ativada" = S**
    - Definir **Evento padrao**: 503 (evento de subcontratacao — ver PEND-06)
    - Gravar

> **CRITICO**: CCF sem ativacao NAO e reconhecida por processos. A [opcao 408](../comercial/408-comissao-unidades.md) (custos) e a 486 (conta corrente) exigem CCF ativa.

---

### ETAPA 6 — Cadastrar Custos/Comissao (Opcao 408)

18. Acessar [opcao **408**](../comercial/408-comissao-unidades.md)
19. Selecionar a unidade criada na etapa 2 (ex: CGR)
20. Criar **Comissao Geral** (Como Expedidora):

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Subcontratado** | CNPJ do parceiro (cadastrado na etapa 5) | CNPJ Alemar |
| **Data inicial** | Data de hoje | Inicio da parceria |
| **Data final** | (deixar vazio) | Indeterminada |
| **Tipo Frete** | Ambas | CIF e FOB |

21. Preencher os parametros de custo conforme tabela do Sistema Fretes:

| Item | Campo | Valor | Observacao |
|------|-------|-------|------------|
| **3** | Sobre peso — Tabela por faixas | Faixas de peso + valores R$/Kg | Copiar da tabela do parceiro no Sistema Fretes |
| **3** | Despacho | R$ fixo por CTRC | Valor de despacho do parceiro |
| **5** | TDC/TRT/TDA/TAR/Pedagio | Percentuais conforme parceiro | Se aplicavel |
| **4** | Comissao minima | R$ minimo por CTRC | Se parceiro tem minimo |
| **10** | Conta Corrente Fornecedor | **M** (Mapa) | Credito por processamento batch |

> **Ponto chave**: Os valores na [opcao 408](../comercial/408-comissao-unidades.md) refletem o **custo** que a CarVia paga ao parceiro (espelho do Sistema Fretes). A **margem** da CarVia esta na diferenca entre a tabela 420 (preco de venda) e a tabela 408 (custo).

22. Se necessario, criar **tabelas especificas** por rota:
    - Selecionar "Tabelas especificas" → "Por Rota"
    - Rota: CAR → CGR
    - Informar parametros diferenciados

> **Prioridade de calculo**: Especifica por Cliente > Especifica por Cidade > Especifica por Rota > Comissao Geral.

---

### ETAPA 7 — Cadastrar Tabelas de Preco CarVia (Opcao 420)

23. Acessar opcao **420** (Tabela por Faixa de Peso)
24. Criar **3 tabelas** para a rota, seguindo a nomenclatura CarVia:

| Tabela | Origem | Destino | Descricao |
|--------|--------|---------|-----------|
| **CARP-CGRP** | CAR | CGR (Polo) | CarVia Polo → Campo Grande Polo |
| **CARP-CGRR** | CAR | CGR (Regiao) | CarVia Polo → Campo Grande Regiao |
| **CARP-CGRI** | CAR | CGR (Interior) | CarVia Polo → Campo Grande Interior |

25. Para **cada tabela**, preencher:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **CNPJ Cliente** | CNPJ do cliente (ou generico) | Tabela geral ou por cliente |
| **Unidade origem** | CAR | Unidade operacional CarVia |
| **Unidade/UF destino** | CGR / MS | Unidade e UF destino |
| **Ativa** | S | Tabela ativa para calculo |
| **Faixas de peso** | Progressivas conforme precificacao CarVia | Precos COM margem sobre custo ([408](../comercial/408-comissao-unidades.md)) |

26. Preencher as **faixas de peso** (exemplo ilustrativo):

| Faixa (ate Kg) | Valor R$ ou R$/Kg | Observacao |
|----------------|-------------------|------------|
| 50 | R$ 180,00 | Valor fixo |
| [100](../comercial/100-geracao-emails-clientes.md) | R$ 280,00 | Valor fixo |
| 200 | R$ 3,20/Kg | Valor por Kg |
| [500](../comercial/500-liquidacao-parcial-fatura-arquivo.md) | R$ 2,80/Kg | Valor por Kg |
| 1.000 | R$ 2,40/Kg | Valor por Kg |
| 5.000 | R$ 2,00/Kg | Valor por Kg |
| 10.000 | R$ 1,60/Kg | Valor por Kg |

> **NOTA**: Valores acima sao ILUSTRATIVOS. Os valores reais vem do Sistema Fretes + margem CarVia. Cada polo (P/R/I) tem valores diferentes — Interior e mais caro que Polo.

27. Preencher **adicionais** em cada tabela:

| Adicional | Valor tipico | Observacao |
|-----------|-------------|------------|
| **Despacho** | R$ fixo por CTRC | Taxa administrativa |
| **GRIS** | % sobre valor mercadoria | Gerenciamento de risco (ex: 0,30%) |
| **Ad Valorem** | % sobre valor mercadoria | Seguro carga (ex: 0,10%) |
| **Pedagio** | R$/frac 100Kg ou fixo | Pedagio rota |
| **TDE** | Se aplicavel | Taxa Dificil Entrega |
| **TDC** | Se aplicavel | Taxa Dificil Coleta |

28. Repetir para as **3 tabelas** (P, R, I), ajustando valores conforme polo

---

### ETAPA 8 — Verificar Implantacao (Cotacao 002)

29. Acessar [opcao **002**](../operacional/002-consulta-coletas.md) (Cotacao)
30. Simular uma cotacao para validar a rota:

| Campo | Valor teste | Exemplo CGR |
|-------|-------------|-------------|
| **Origem** | CAR | CAR |
| **Destino** | Cidade Polo da nova rota | Campo Grande/MS |
| **Peso** | 100 Kg (teste) | [100](../comercial/100-geracao-emails-clientes.md) |
| **Valor mercadoria** | R$ 5.000,00 (teste) | 5000 |
| **Volumes** | 5 (teste) | 5 |

31. Verificar resultado da cotacao:
    - **Frete peso**: Valor conforme tabela 420 (CARP-CGRP)
    - **Despacho**: Valor fixo conforme tabela
    - **GRIS**: % sobre valor mercadoria
    - **Pedagio**: Conforme configurado
    - **Prazo**: Prazo transferencia ([403](../cadastros/403-rotas.md)) + Prazo entrega ([402](../cadastros/402-cidades-atendidas.md))
    - **Valor total**: Compativel com o esperado

32. **Se cotacao retornar valor zerado ou erro**:
    - Verificar se tabela 420 esta **Ativa = S**
    - Verificar se cidade de destino esta cadastrada ([402](../cadastros/402-cidades-atendidas.md)) com unidade correta
    - Verificar se rota existe ([403](../cadastros/403-rotas.md)) entre CAR e a unidade destino
    - Verificar se praca operacional (P/R/I) da cidade bate com a tabela
    - Verificar se CNPJ do cliente esta correto na tabela 420

33. Simular tambem para cidades de **Regiao** e **Interior** para validar as 3 tabelas

---

## Checklist Final

Usar este checklist para confirmar que todos os cadastros foram feitos corretamente:

| # | Verificacao | Opcao SSW | Status |
|---|------------|-----------|--------|
| 1 | Unidade tipo T criada com sigla IATA | [401](../cadastros/401-cadastro-unidades.md) | [ ] |
| 2 | CNPJ na unidade = CNPJ CarVia | [401](../cadastros/401-cadastro-unidades.md) | [ ] |
| 3 | Conta bancaria = conta CarVia | [401](../cadastros/401-cadastro-unidades.md) | [ ] |
| 4 | Cidades Polo cadastradas com P + prazo | [402](../cadastros/402-cidades-atendidas.md) | [ ] |
| 5 | Cidades Regiao cadastradas com R + prazo | [402](../cadastros/402-cidades-atendidas.md) | [ ] |
| 6 | Cidades Interior cadastradas com I + prazo | [402](../cadastros/402-cidades-atendidas.md) | [ ] |
| 7 | Coleta=S e Entrega=S em todas cidades | [402](../cadastros/402-cidades-atendidas.md) | [ ] |
| 8 | Tipo frete=A (Ambos) em todas cidades | [402](../cadastros/402-cidades-atendidas.md) | [ ] |
| 9 | Rota CAR → [SIGLA] criada com prazo | [403](../cadastros/403-rotas.md) | [ ] |
| 10 | Fornecedor cadastrado com CNPJ do parceiro | [478](../financeiro/478-cadastro-fornecedores.md) | [ ] |
| 11 | CCF ativada = S no fornecedor | [478](../financeiro/478-cadastro-fornecedores.md) | [ ] |
| 12 | Comissao geral cadastrada (custo parceiro) | [408](../comercial/408-comissao-unidades.md) | [ ] |
| 13 | Tabela CARP-[SIGLA]P criada e ativa | 420 | [ ] |
| 14 | Tabela CARP-[SIGLA]R criada e ativa | 420 | [ ] |
| 15 | Tabela CARP-[SIGLA]I criada e ativa | 420 | [ ] |
| 16 | Cotacao Polo retorna valor correto | [002](../operacional/002-consulta-coletas.md) | [ ] |
| 17 | Cotacao Regiao retorna valor correto | [002](../operacional/002-consulta-coletas.md) | [ ] |
| 18 | Cotacao Interior retorna valor correto | [002](../operacional/002-consulta-coletas.md) | [ ] |

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Executor** | Rafael faz tudo manualmente | Rafael (sem delegacao prevista) |
| **Fonte de precos** | Sistema Fretes (app Nacom) | Sistema Fretes (possivel automacao futura) |
| **Tempo por rota** | 30-60 minutos | Reduzir com templates e automacao |
| **Nomenclatura** | CARP-[SIGLA][P/R/I] | Manter padrao |
| **Dados do parceiro** | Extraidos manualmente | Possivel sincronizacao automatica |
| **Validacao** | Cotacao manual ([002](../operacional/002-consulta-coletas.md)) | Cotacao + validacao automatizada |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Cotacao retorna R$ 0,00 | Tabela 420 nao encontrada ou Ativa=N | Verificar se tabela existe, esta ativa, e praca bate com cidade |
| Cotacao nao encontra cidade | Cidade nao cadastrada na 402 | Verificar se cidade foi incluida com unidade correta |
| Prazo de entrega errado | Prazo rota ([403](../cadastros/403-rotas.md)) ou prazo cidade ([402](../cadastros/402-cidades-atendidas.md)) incorreto | Conferir ambos os prazos — total = transferencia + entrega |
| Cidade em polo errado (P/R/I) | Classificacao diverge do Sistema Fretes | Corrigir na 402 — afeta qual tabela 420 e usada |
| Custo ([408](../comercial/408-comissao-unidades.md)) nao calcula | Fornecedor sem CCF ativa | Ativar CCF=S na [opcao 478](../financeiro/478-cadastro-fornecedores.md) |
| Custo ([408](../comercial/408-comissao-unidades.md)) nao calcula | Fornecedor nao cadastrado como transportadora ([485](../financeiro/485-cadastro-transportadoras.md)) | Cadastrar parceiro na [opcao 485](../financeiro/485-cadastro-transportadoras.md) com status ativo |
| Sigla ja existe na 401 | Outra unidade usa a mesma sigla | Usar variacao (ex: CGS se CGR ja existir) |
| Tabela 420 duplicada | Ja existe tabela para mesma origem/destino | Verificar se rota ja foi implantada parcialmente |
| Erro "subcontratado nao encontrado" na 408 | Fornecedor nao esta como transportadora ([485](../financeiro/485-cadastro-transportadoras.md)) | Cadastrar na 485 antes de usar na 408 |
| Margem negativa | Preco venda (420) menor que custo ([408](../comercial/408-comissao-unidades.md)) | Revisar tabelas — ajustar margem no Sistema Fretes |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Unidade criada | [Opcao 401](../cadastros/401-cadastro-unidades.md) → pesquisar sigla → dados corretos |
| Cidades cadastradas | [Opcao 402](../cadastros/402-cidades-atendidas.md) → filtrar por unidade → lista de cidades com P/R/I |
| Rota cadastrada | [Opcao 403](../cadastros/403-rotas.md) → pesquisar CAR → [SIGLA] na lista de destinos |
| Fornecedor com CCF | [Opcao 478](../financeiro/478-cadastro-fornecedores.md) → pesquisar CNPJ parceiro → CCF ativada = S |
| Comissao cadastrada | [Opcao 408](../comercial/408-comissao-unidades.md) → selecionar unidade → comissao geral com CNPJ parceiro |
| Tabelas de preco ativas | Opcao 420 → pesquisar rota → 3 tabelas ativas (P/R/I) |
| Cotacao funciona | [Opcao 002](../operacional/002-consulta-coletas.md) → simular com dados teste → valor retornado > 0 |

---

## Exemplo Completo: Campo Grande/MS (Alemar)

Resumo dos cadastros para a rota CGR completa:

| Etapa | Opcao | O que foi criado |
|-------|-------|-----------------|
| 2 | [401](../cadastros/401-cadastro-unidades.md) | Unidade **CGR**, Tipo T, "Alemar - Campo Grande/MS" |
| 3 | [402](../cadastros/402-cidades-atendidas.md) | 7 cidades: Campo Grande (P), Sidrolandia (R), Terenos (R), Dourados (R), Corumba (I), Ponta Pora (I), Tres Lagoas (I) |
| 4 | [403](../cadastros/403-rotas.md) | Rota **CAR → CGR**, prazo transferencia 2 dias |
| 5 | [478](../financeiro/478-cadastro-fornecedores.md) | Fornecedor CNPJ Alemar, CCF ativa, especialidade Agencias/Parceiros |
| 6 | [408](../comercial/408-comissao-unidades.md) | Comissao geral CGR: faixas de peso = tabela Alemar (custo), CCF forma Mapa |
| 7 | 420 | 3 tabelas: **CARP-CGRP**, **CARP-CGRR**, **CARP-CGRI** (precos com margem) |
| 8 | [002](../operacional/002-consulta-coletas.md) | Cotacao teste: Campo Grande 100Kg R$5.000 → valor calculado e prazo 4 dias |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A02 | Criar unidade parceira ([opcao 401](../cadastros/401-cadastro-unidades.md)) — etapa 2 deste POP |
| POP-A03 | Cadastrar cidades atendidas ([opcao 402](../cadastros/402-cidades-atendidas.md)) — etapa 3 deste POP |
| POP-A04 | Cadastrar rota ([opcao 403](../cadastros/403-rotas.md)) — etapa 4 deste POP |
| POP-A05 | Cadastrar fornecedor ([opcao 478](../financeiro/478-cadastro-fornecedores.md)) — etapa 5 deste POP |
| POP-A06 | Cadastrar custos/comissao ([opcao 408](../comercial/408-comissao-unidades.md)) — etapa 6 deste POP |
| POP-A07 | Cadastrar tabela de preco (opcao 420) — etapa 7 deste POP |
| POP-C01 | Emitir CT-e fracionado — proximo passo apos rota implantada |
| POP-C02 | Emitir CT-e carga direta — variante apos rota implantada |
| POP-F02 | CCF — controle de saldo com parceiro |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-16 | Criacao inicial — processo composto A02-A07 com exemplo CGR/Alemar | Claude (Agente Logistico) |

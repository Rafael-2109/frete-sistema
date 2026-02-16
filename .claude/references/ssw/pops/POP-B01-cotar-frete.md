# POP-B01 — Cotar Frete para Cliente

> **Categoria**: B — Comercial e Precificacao
> **Prioridade**: P1 (Alta — processo ja existente, Jessica precisa aprender)
> **Status anterior**: JA FAZ
> **Criado em**: 2026-02-16
> **Executor atual**: Rafael
> **Executor futuro**: Jessica

---

## Objetivo

Realizar cotacoes de frete no SSW ([opcao 002](../operacional/002-consulta-coletas.md)) para responder demandas de clientes, utilizando a analise previa no Sistema Fretes (app Nacom) como referencia de viabilidade. Ao final, o cliente recebe uma proposta comercial com valor, prazo e condicoes.

O processo atual depende do Rafael: Jessica recebe a demanda, solicita ao Rafael, que cota e retorna o valor. Este POP padroniza o fluxo para que Jessica execute diretamente no SSW, reduzindo o gargalo operacional.

---

## Trigger

- Jessica recebe solicitacao de frete de um cliente (e-mail, telefone, WhatsApp)
- Cliente solicita cotacao para nova rota ou novo volume
- Necessidade de renegociar preco para cliente existente

---

## Frequencia

Por demanda — multiplas vezes por semana conforme prospecao comercial.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Cliente cadastrado | [483](../cadastros/483-cadastro-clientes.md) | CNPJ do pagador existe no SSW |
| Cidades atendidas | [402](../cadastros/402-cidades-atendidas.md) | Origem e destino cadastrados (CEPs validos) |
| Tabelas de frete ativas | 420 (rota) ou 417 (combinada) | Tabela ativa para a rota solicitada |
| Rota cadastrada | [403](../cadastros/403-rotas.md) | Rota CAR → destino existe |
| Limites de cotacao | 469 / 369 | Limites configurados (valor minimo, desconto max) |
| Analise previa no Sistema Fretes | App Nacom | Verificar se rota e viavel e qual parceiro atende |

---

## Passo-a-Passo

### ETAPA 1 — Pre-analise no Sistema Fretes

1. Abrir o **Sistema Fretes** (app Nacom)
2. Verificar se a rota solicitada pelo cliente ja esta mapeada:
   - Qual transportadora parceira atende essa regiao?
   - Qual o custo do parceiro (tabela de custos)?
   - Qual o lead time estimado?
3. Se a rota **NAO existe** no Sistema Fretes:
   - Avaliar viabilidade com Rafael
   - Se viavel: executar POP-A10 (Implantar Nova Rota) ANTES de cotar
   - Se inviavel: informar cliente que a regiao nao e atendida

> **IMPORTANTE**: O Sistema Fretes e a fonte de verdade para precos. A cotacao no SSW reflete as tabelas ja cadastradas. Se a rota nao existe no SSW, a cotacao NAO vai funcionar.

---

### ETAPA 2 — Acessar Opcao 002 no SSW

4. Acessar [opcao **002**](../operacional/002-consulta-coletas.md) (Cotacao de Fretes)
5. Clicar em **Incluir** para nova cotacao

---

### ETAPA 3 — Informar Dados do Pagador

6. Preencher o campo **CNPJ PAGADOR** com o CNPJ do cliente
   - Se nao souber o CNPJ: usar link de pesquisa por nome (minimo 3 caracteres)
   - Se cliente nao existe: cadastrar primeiro (POP-A01)

7. Preencher **MERCADORIA** (codigo do tipo de mercadoria)
   - Se mercadoria definida: informar codigo correto
   - Se mercadoria nao definida: deixar em branco (usa tabela generica)

---

### ETAPA 4 — Preencher Dados da Operacao

8. Preencher os campos da cotacao:

| Campo | O que informar | Exemplo |
|-------|----------------|---------|
| **FRETE** | CIF (1) ou FOB (2) | 1 (CIF = remetente paga) |
| **COLETAR** | S (sim) ou N (nao) | S |
| **ENTREGAR** | S (sim) ou N (nao) | S |
| **CEP ORIGEM** | CEP de coleta da mercadoria | 06501-001 (Santana de Parnaiba) |
| **CEP DESTINO** | CEP de entrega ao destinatario | 79010-010 (Campo Grande/MS) |
| **CNPJ REMET** | Obrigatorio se FOB Dirigido | (informar se FOB) |
| **CNPJ DESTIN** | Obrigatorio se FOB Dirigido | (informar se FOB) |
| **PESO (kg)** | Peso total da mercadoria | [500](../comercial/500-liquidacao-parcial-fatura-arquivo.md) |
| **VALOR MERCADORIA** | Valor total da NF em R$ | 25000.00 |
| **CUBAGEM (m3)** | Volume em metros cubicos | 2.5 |
| **FRETE SUBCONT** | Custo da subcontratacao (se aplicavel) | (informar se subcontratacao) |
| **OUTROS** | Valores adicionais (descarga, balsa, etc.) | 0 |

> **DICA CUBAGEM**: Se nao souber a cubagem, o SSW usa a cubagem padrao do cliente ([opcao 423](../comercial/423-parametros-comerciais-cliente.md)) ou a cubagem padrao da transportadora ([opcao 903](../cadastros/903-parametros-gerais.md), sugestao 300 Kg/m3). Peso de calculo = maior entre peso real e peso cubado.

---

### ETAPA 5 — Simular e Verificar Proposta Inicial

9. Clicar em **Simular** (botao Play no rodape)
10. Sistema exibe a **Proposta Inicial** com:
    - Frete Peso (R$/ton por faixa de peso)
    - Frete Valor (% sobre valor mercadoria — Ad Valorem)
    - Despacho (R$ fixo)
    - GRIS (% sobre valor mercadoria)
    - Pedagio
    - Taxas condicionais (TDE, TDC, TRT, TDA, TAR — se aplicaveis)
    - Coleta (se COLETAR = S e placa informada)
    - Entrega
    - ICMS/PIS/COFINS (se repassados)
11. Verificar os **Limites** exibidos na tela:

| Limite | Origem | Significado |
|--------|--------|-------------|
| Valor Minimo R$ | Opcao 469 | Frete minimo permitido para esta rota |
| Desconto max NTC % | Opcao 469 | Maximo de desconto sobre tabela NTC |
| Min RC % | Opcao 469 | Resultado Comercial minimo exigido |
| Max inicial % | 423 > 469 > 903 | Desconto maximo sobre proposta inicial |

> **Se Proposta Inicial = 0 ou erro**: Verificar se tabela de frete esta ativa (420), se rota existe ([403](../cadastros/403-rotas.md)) e se cidades estao vinculadas ([402](../cadastros/402-cidades-atendidas.md)). Ver secao "Erros Comuns".

---

### ETAPA 6 — Aplicar Desconto (Se Necessario)

12. Se o preco precisa de ajuste:
    - Informar **desconto (%)** ou **acrescimo (%)** sobre a proposta atual
    - Clicar em **Simular** novamente
    - Sistema exibe a **Proposta Atual** (com desconto aplicado)
13. Verificar se a Proposta Atual respeita os limites:
    - Valor acima do minimo?
    - Resultado comercial acima do minimo?
    - Desconto dentro do maximo permitido?

> **Se limite ultrapassado**: O SSW bloqueia a cotacao. Somente usuarios com "Desbloqueia Resultado = SIM" ([opcao 925](../cadastros/925-cadastro-usuarios.md)) podem liberar. Na CarVia, Rafael tem essa permissao.

---

### ETAPA 7 — Decidir: Contratar ou Apenas Informar

14. **Opcao A — Apenas informar o cliente**:
    - Anotar o valor da Proposta Atual
    - NAO contratar no SSW
    - Enviar valor ao cliente por e-mail/WhatsApp

15. **Opcao B — Contratar Valor Variavel** (recomendado):
    - Clicar em **Contratar**
    - Mantem o **percentual de desconto** — se a tabela mudar, o valor do CTRC acompanha
    - Cotacao sera usada automaticamente na emissao do CTRC (se criterios baterem)

16. **Opcao C — Contratar Valor Fixo**:
    - Clicar em **Contratar com Valor Fixo**
    - Mantem o **valor em R$** — mesmo que a tabela mude, CTRC tera exatamente este valor
    - Usar apenas quando preco fixo foi prometido ao cliente

> **QUANDO A COTACAO E USADA NO CTRC**: Automaticamente, se: mesmo CNPJ pagador, mesma tabela de frete, mesma cidade origem/destino, mesmo tipo de mercadoria (se informado), e dentro do prazo de validade (configurado na [opcao 903](../cadastros/903-parametros-gerais.md)/Prazos). O CTRC tera o mesmo percentual de desconto aplicado.

---

### ETAPA 8 — Enviar Cotacao ao Cliente

17. **Processo atual (Jessica)**:
    - Rafael informa o valor para Jessica
    - Jessica envia ao cliente por e-mail ou WhatsApp
    - Jessica acompanha resposta do cliente

18. **Processo futuro (Jessica direto)**:
    - Jessica cota diretamente no SSW ([opcao 002](../operacional/002-consulta-coletas.md))
    - Jessica envia ao cliente
    - Se cliente aprova: Jessica solicita NF ao cliente

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Quem cota** | Rafael (Jessica pede para Rafael) | Jessica cota direto no SSW |
| **Pre-analise** | Rafael verifica no Sistema Fretes | Jessica consulta Sistema Fretes + SSW |
| **Contratar no SSW** | Rafael contrata (ou apenas informa) | Jessica contrata cotacao (valor variavel) |
| **Envio ao cliente** | Rafael → Jessica → cliente | Jessica → cliente |
| **Fretes complexos** | Rafael usa simulacao da 004 tambem | Jessica usa 002, escala para Rafael se complexo |
| **Limites configurados** | Parcialmente (falta verificar 469) | 469 configurada para todas as rotas |
| **Prazo de validade** | Nao acompanha | Configurar na 903/Prazos |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Simulacao retorna R$ 0,00 | Tabela de frete inativa ou inexistente para a rota | Verificar opcao 420 — tabela ativa (S) para rota de origem/destino |
| "Cidade nao atendida" | CEP de destino nao vinculado a nenhuma unidade | Verificar [opcao 402](../cadastros/402-cidades-atendidas.md) — cidade cadastrada com unidade parceira |
| Rota nao encontrada | Rota CAR → destino nao cadastrada | Executar POP-A10 (Implantar Nova Rota) |
| Limite de desconto bloqueado | Desconto excede "Max inicial %" | Reduzir desconto ou pedir liberacao a usuario com "Desbloqueia Resultado" ([925](../cadastros/925-cadastro-usuarios.md)) |
| Resultado comercial negativo | Preco cotado abaixo do custo | Verificar tabela 408 (custos parceiro) vs tabela 420 (preco venda). Margem insuficiente |
| Cubagem incorreta eleva preco | Cubagem padrao (300 Kg/m3) nao reflete carga real | Informar cubagem real (m3) ou configurar cubagem do cliente na [opcao 423](../comercial/423-parametros-comerciais-cliente.md) |
| CNPJ pagador nao encontrado | Cliente nao cadastrado no SSW | Cadastrar cliente (POP-A01) antes de cotar |
| Cotacao nao aplicada no CTRC | Criterios nao bateram (CNPJ, cidade, tabela, prazo) | Verificar: mesmo CNPJ pagador, mesma rota, cotacao dentro da validade |
| TDE/TDA/TRT aparecem inesperados | Destinatario marcado como "Entrega Dificil" ou cidade com restricao | Verificar [opcao 483](../cadastros/483-cadastro-clientes.md) (Entrega Dificil) e [opcao 402](../cadastros/402-cidades-atendidas.md)/530 (TDA/TRT) |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Cotacao criada | [Opcao 002](../operacional/002-consulta-coletas.md) → listar por CNPJ pagador → cotacao aparece com status |
| Valor da proposta | [Opcao 002](../operacional/002-consulta-coletas.md) → detalhe da cotacao → valor Proposta Atual > 0 |
| Cotacao contratada | [Opcao 002](../operacional/002-consulta-coletas.md) → detalhe → status = Contratada |
| Limites respeitados | [Opcao 002](../operacional/002-consulta-coletas.md) → Limites na tela → valores preenchidos e respeitados |
| Tabela utilizada | [Opcao 002](../operacional/002-consulta-coletas.md) → Parcelas → verificar tabela de frete aplicada |
| Rota existe | [Opcao 403](../cadastros/403-rotas.md) → origem CAR + destino = sigla parceiro → rota encontrada |
| Cidades vinculadas | [Opcao 402](../cadastros/402-cidades-atendidas.md) → cidade destino → vinculada a unidade parceira |
| Cliente cadastrado | [Opcao 483](../cadastros/483-cadastro-clientes.md) → CNPJ → dados preenchidos |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A01 | Cadastrar cliente — pre-requisito se cliente nao existe |
| POP-A10 | Implantar nova rota — pre-requisito se rota nao existe |
| POP-B02 | Formacao de preco — entender como o valor e calculado |
| POP-B03 | Parametros de frete — configurar limites e cubagem |
| POP-C01 | Emitir CT-e fracionado — proximo passo apos aprovacao do cliente |
| POP-C02 | Emitir CT-e carga direta — proximo passo para cargas diretas |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-16 | Criacao inicial — [opcao 002](../operacional/002-consulta-coletas.md) com contexto CarVia e transicao Rafael→Jessica | Claude (Agente Logistico) |

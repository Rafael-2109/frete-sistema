# POP-A02 — Cadastrar Unidade Parceira (Terceiro)

> **Categoria**: A — Implantacao e Cadastros
> **Prioridade**: P1 (Alta — base para rotas, cidades, tabelas e operacao com parceiros)
> **Status anterior**: JA FAZ
> **Criado em**: 2026-02-16
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Cadastrar uma nova unidade do tipo **T (Terceiro)** no SSW da CarVia, representando uma transportadora parceira operando em uma cidade/regiao especifica. Cada filial de transportadora parceira equivale a uma unidade T com sigla IATA no SSW.

A unidade criada usa o **CNPJ da CarVia** (nao do parceiro), a **conta bancaria da CarVia** e os **dados fiscais da CarVia**. O parceiro em si sera cadastrado como fornecedor ([opcao 478](../financeiro/478-cadastro-fornecedores.md) — POP-A05).

Ao final, a unidade deve estar pronta para receber cidades ([402](../cadastros/402-cidades-atendidas.md)), rotas ([403](../cadastros/403-rotas.md)), custos ([408](../comercial/408-comissao-unidades.md)) e tabelas (420).

---

## Trigger

- Nova transportadora parceira identificada para atender uma regiao
- Nova filial de parceiro existente precisa ser cadastrada (mesmo parceiro, cidade diferente)
- Jessica recebe demanda comercial para cidade nao atendida — Rafael identifica parceiro e inicia implantacao
- Processo composto POP-A10 (Implantar Nova Rota) aciona este POP como etapa 2

---

## Frequencia

Por demanda — a cada nova cidade/regiao de atendimento. Estimativa: 5-10 minutos por unidade.

---

## Pre-requisitos

| Requisito | Fonte | O que verificar |
|-----------|-------|-----------------|
| Parceiro identificado | Sistema Fretes (app Nacom) | Qual transportadora melhor atende a regiao |
| Sigla IATA da cidade | Tabela IATA ou convenção | Codigo de 3 letras da cidade (ex: CGR, CWB, POA) |
| Nome do parceiro na cidade | Documentacao | Nome da transportadora + cidade/UF |
| CNPJ da CarVia | Documentacao propria | CNPJ usado em todas as unidades T |
| IE da CarVia (se aplicavel) | Documentacao propria | IE da CarVia para a UF correspondente |
| Conta bancaria CarVia | Documentacao propria | Banco, agencia, conta corrente |
| Dados do seguro ESSOR | Documentacao propria | Seguro e global CarVia, nao por unidade |

> **REGRA CARVIA**: Unidade tipo T representa a CarVia operando naquela praca via parceiro. Por isso usa CNPJ, IE, conta e dados fiscais da **CarVia** — nao do parceiro.

---

## Passo-a-Passo

### ETAPA 1 — Definir Sigla IATA da Cidade

1. Identificar a sigla **IATA** da cidade principal que o parceiro atende:

| Cidade | Sigla IATA | Observacao |
|--------|-----------|------------|
| Campo Grande/MS | CGR | Exemplo ja implantado (Alemar) |
| Curitiba/PR | CWB | — |
| Porto Alegre/RS | POA | — |
| Belo Horizonte/MG | BHZ ou CNF | Verificar convenção CarVia |
| Recife/PE | REC | — |
| Salvador/BA | SSA | — |
| Manaus/AM | MAO | — |

2. Verificar se a sigla **ja existe** no SSW:
   - Acessar [opcao **401**](../cadastros/401-cadastro-unidades.md)
   - Pesquisar pela sigla desejada
   - **Se ja existe**: Sigla em uso por outra unidade. Usar variacao (ex: CGS se CGR ja existir)
   - **Se nao existe**: Prosseguir

> **CONVENCAO CARVIA**: Sempre preferir o codigo IATA oficial do aeroporto da cidade. Se houver conflito, usar abreviacao alternativa de 3 letras.

---

### ETAPA 2 — Acessar Opcao 401 e Incluir Nova Unidade

3. Acessar [opcao **401**](../cadastros/401-cadastro-unidades.md) (Cadastro de Unidades)
4. Clicar em **Incluir** nova unidade
5. Preencher os **dados basicos**:

| Campo | Valor | Exemplo CGR |
|-------|-------|-------------|
| **Sigla** | Codigo IATA (3 letras, maiusculas) | CGR |
| **Tipo** | **T** (Terceiro) | T |
| **Razao Social** | "Transportadora - Cidade/UF" | Alemar - Campo Grande/MS |
| **Nome Fantasia** | Mesmo que Razao Social ou abreviado | Alemar CGR |
| **UF** | UF da cidade destino | MS |

> **NOMENCLATURA**: O padrao CarVia para Razao Social e: **[Nome Parceiro] - [Cidade]/[UF]**. Exemplos: "Alemar - Campo Grande/MS", "Braspress - Curitiba/PR", "Jadlog - Porto Alegre/RS".

---

### ETAPA 3 — Preencher Dados Fiscais (CNPJ da CarVia)

6. Preencher os campos fiscais com dados da **CarVia** (nao do parceiro):

| Campo | Valor | Observacao |
|-------|-------|------------|
| **CNPJ** | CNPJ da **CarVia** | Mesmo CNPJ para todas as unidades T |
| **Inscricao Estadual** | IE da CarVia na UF (se aplicavel) | Vazio se CarVia nao tem IE naquela UF |
| **Simples Nacional** | Conforme regime da CarVia | S ou N |
| **Regime PIS/COFINS** | Conforme regime da CarVia | Cumulativo ou Nao Cumulativo |

> **ATENCAO**: O CNPJ na unidade tipo T e SEMPRE o da **CarVia**, nunca o do parceiro. A unidade representa a CarVia operando naquela praca. O parceiro sera cadastrado como fornecedor na [opcao 478](../financeiro/478-cadastro-fornecedores.md) com seu proprio CNPJ.

---

### ETAPA 4 — Preencher Dados Bancarios (Conta da CarVia)

7. Preencher com a conta bancaria da **CarVia**:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Banco** | Banco da CarVia | Codigo do banco |
| **Agencia** | Agencia da CarVia | Numero da agencia |
| **Conta Corrente** | Conta da CarVia | Numero da conta |
| **DV** | Digito verificador (se aplicavel) | Opcional |

> **POR QUE CONTA DA CARVIA**: A unidade tipo T nao tem conta propria — e uma extensao da CarVia. Faturas e cobradas pela CarVia (MTZ), e pagamentos sao feitos pela conta da CarVia.

---

### ETAPA 5 — Confirmar e Gravar

8. Revisar todos os campos preenchidos:
   - Sigla: 3 letras IATA
   - Tipo: T (Terceiro)
   - CNPJ: da CarVia
   - UF: da cidade destino
   - Banco/Conta: da CarVia

9. Clicar em **Confirmar** / **Gravar** para salvar a unidade

10. **NAO** configurar parametrizacao fiscal (opcao 920):
    - Unidades tipo T **nao emitem** documentos fiscais (CT-e, NF-e, MDF-e)
    - Quem emite documentos fiscais e a unidade CAR (filial operacional)
    - Opcao 920 so e necessaria para unidades que emitem documentos

---

### ETAPA 6 — Verificar Cadastro

11. Pesquisar a unidade recem-criada na [opcao **401**](../cadastros/401-cadastro-unidades.md):
    - Digitar a sigla (ex: CGR)
    - Confirmar que todos os dados estao corretos

12. Verificar que a unidade aparece na lista de unidades disponiveis:
    - Ao trocar de unidade no menu do SSW, a nova sigla deve aparecer

---

### ETAPA 7 — Proximo Passo: Cadastrar Cidades e Rotas

13. Com a unidade criada, os proximos cadastros sao:

| Proximo passo | Opcao SSW | POP | Obrigatorio |
|---------------|-----------|-----|-------------|
| Cadastrar cidades atendidas | [402](../cadastros/402-cidades-atendidas.md) | POP-A03 | Sim |
| Cadastrar rota CAR → [SIGLA] | [403](../cadastros/403-rotas.md) | POP-A04 | Sim |
| Cadastrar fornecedor (parceiro) | [478](../financeiro/478-cadastro-fornecedores.md) | POP-A05 | Sim |
| Cadastrar custos/comissao | [408](../comercial/408-comissao-unidades.md) | POP-A06 | Sim |
| Cadastrar tabelas de preco | 420 | POP-A07 | Sim |

> **SE FOR IMPLANTAR ROTA COMPLETA**: Seguir o POP-A10 que coordena todas estas etapas na sequencia correta.

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Executor** | Rafael cria unidades conforme demanda | Rafael (sem delegacao prevista) |
| **CNPJ** | CNPJ da CarVia em todas as unidades T | Manter |
| **Conta bancaria** | Conta unica da CarVia | Manter (pode mudar de banco) |
| **Nomenclatura** | "[Parceiro] - [Cidade]/[UF]" | Manter padrao |
| **Sigla** | IATA da cidade (3 letras) | Manter padrao |
| **Quantidade** | ~5 unidades T ativas | Crescer conforme novos parceiros |
| **Seguro** | ESSOR — configuracao global, nao por unidade | Manter |
| **Opcao 920** | Nao configura em unidades T | Correto — T nao emite documentos |

### Unidades T Existentes (Referencia)

| Sigla | Parceiro | Cidade/UF |
|-------|----------|-----------|
| CGR | Alemar | Campo Grande/MS |
| *(outras a documentar conforme implantacao)* | — | — |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| "Sigla ja existe" | Outra unidade usa a mesma sigla de 3 letras | Usar variacao (ex: CGS, CGB) ou verificar se unidade existente e reutilizavel |
| CNPJ do parceiro no campo CNPJ | Confusao — colocou CNPJ do parceiro em vez do CarVia | Corrigir para CNPJ da **CarVia**. Parceiro vai na [opcao 478](../financeiro/478-cadastro-fornecedores.md) |
| IE invalida para a UF | IE informada nao corresponde a UF da unidade | Verificar se CarVia tem IE naquela UF. Se nao tem, deixar vazio |
| Unidade nao aparece na troca | Cache do SSW ou unidade nao gravada | Atualizar pagina. Verificar se cadastro foi salvo |
| Tentou configurar opcao 920 | Unidade T nao emite documentos fiscais | NAO configurar 920 para tipo T. Somente filiais (CAR) e matriz (MTZ) |
| Cidades nao vinculam a unidade | [Opcao 402](../cadastros/402-cidades-atendidas.md) nao encontra a sigla | Verificar se unidade foi gravada corretamente na 401 |
| Rota nao aceita a unidade | [Opcao 403](../cadastros/403-rotas.md) nao reconhece a sigla | Verificar se unidade esta ativa e sigla esta correta |
| Conta bancaria errada | Informou conta do parceiro em vez da CarVia | Corrigir para conta bancaria da **CarVia** |
| Tipo de unidade incorreto | Marcou Filial em vez de Terceiro (T) | Corrigir tipo para **T**. Filial implica emissao fiscal, T nao |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Unidade criada | [Opcao 401](../cadastros/401-cadastro-unidades.md) → pesquisar sigla → registro encontrado |
| Tipo = T (Terceiro) | [Opcao 401](../cadastros/401-cadastro-unidades.md) → campo tipo = T |
| CNPJ = CarVia | [Opcao 401](../cadastros/401-cadastro-unidades.md) → CNPJ = CNPJ da CarVia (nao do parceiro) |
| UF correta | [Opcao 401](../cadastros/401-cadastro-unidades.md) → UF = UF da cidade destino |
| Razao Social padrao | [Opcao 401](../cadastros/401-cadastro-unidades.md) → formato "[Parceiro] - [Cidade]/[UF]" |
| Dados bancarios CarVia | [Opcao 401](../cadastros/401-cadastro-unidades.md) → Banco/Agencia/Conta = dados CarVia |
| Opcao 920 NAO configurada | Opcao 920 → sigla → sem parametrizacao fiscal |
| Unidade disponivel para 402 | [Opcao 402](../cadastros/402-cidades-atendidas.md) → sigla aparece na lista de unidades |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A10 | Implantar nova rota completa — este POP e a etapa 2 do A10 |
| POP-A03 | Cadastrar cidades atendidas ([402](../cadastros/402-cidades-atendidas.md)) — proximo passo apos criar unidade |
| POP-A04 | Cadastrar rota ([403](../cadastros/403-rotas.md)) — definir rota CAR → [SIGLA] |
| POP-A05 | Cadastrar fornecedor ([478](../financeiro/478-cadastro-fornecedores.md)) — cadastrar parceiro como fornecedor |
| POP-A06 | Cadastrar custos/comissao ([408](../comercial/408-comissao-unidades.md)) — definir custo de subcontratacao |
| POP-A07 | Cadastrar tabela de preco (420) — criar tabelas CARP-[SIGLA][P/R/I] |
| POP-D01 | Contratar veiculo — unidade T e destino da transferencia |
| POP-F02 | CCF — conta corrente do fornecedor vinculado a unidade |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-16 | Criacao inicial — [opcao 401](../cadastros/401-cadastro-unidades.md) tipo T com contexto CarVia | Claude (Agente Logistico) |

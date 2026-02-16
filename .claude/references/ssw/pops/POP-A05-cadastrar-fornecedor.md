# POP-A05 — Cadastrar Fornecedor/Transportadora

> **Categoria**: A — Implantacao e Cadastros
> **Prioridade**: P1 (Alta — base para CCF, custos 408, contratacao 072 e contas a pagar 475)
> **Status anterior**: JA FAZ
> **Criado em**: 2026-02-16
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Cadastrar um novo fornecedor no SSW da CarVia utilizando a [opcao 478](../financeiro/478-cadastro-fornecedores.md) (dados cadastrais, CCF e dados bancarios) e, quando for transportadora parceira de subcontratacao, complementar com a [opcao 485](../financeiro/485-cadastro-transportadoras.md) (cadastro de transportadora). Ao final, o fornecedor deve estar apto para: receber creditos na CCF ([486](../financeiro/486-conta-corrente-fornecedor.md)), ser usado em tabelas de custo ([408](../comercial/408-comissao-unidades.md)), ter contratacoes registradas (072) e receber pagamentos (475/476).

Sem CCF ativada, o fornecedor NAO e reconhecido por processos automaticos — contratacoes nao creditam, acertos de saldo nao funcionam e relatorios ignoram o fornecedor.

---

## Trigger

- Nova transportadora parceira identificada para subcontratacao (redespacho/agenciamento)
- Novo motorista agregado ou carreteiro contratado
- Novo prestador de servico (manutencao, abastecimento, pneus)
- Processo composto POP-A10 (Implantar Nova Rota) aciona este POP como etapa 5

---

## Frequencia

Por demanda — a cada novo parceiro, agregado ou prestador. Estimativa: 5-10 minutos por cadastro completo (478 + 485).

---

## Pre-requisitos

| Requisito | Fonte | O que verificar |
|-----------|-------|-----------------|
| CNPJ/CPF do fornecedor | Documentacao do parceiro | CNPJ valido, situacao ativa na Receita Federal |
| Razao Social e endereco | Contrato ou documentacao | Nome juridico, logradouro, CEP, cidade/UF |
| Dados bancarios do fornecedor | Parceiro informa | Banco, agencia, conta corrente, tipo conta |
| Evento de despesa cadastrado ([503](../fiscal/503-manutencao-de-eventos.md)) | [Opcao 503](../fiscal/503-manutencao-de-eventos.md) no SSW | Evento para acerto automatico de CCF (ver PEND-06) |
| Tipo de fornecedor definido | Rafael define | Agencia/Parceiro, Carreteiro, Agregado, Frota, Prestador |
| Inscricao Estadual (se PJ contribuinte) | Documentacao do parceiro | IE valida ou ISENTO |

> **PEND-06**: Se eventos de despesa ([503](../fiscal/503-manutencao-de-eventos.md)) ainda nao estao cadastrados, o campo "Evento padrao" ficara vazio. Cadastrar eventos ANTES para que o acerto automatico funcione.

---

## Passo-a-Passo

### ETAPA 1 — Verificar se Fornecedor Ja Existe

1. Acessar [opcao **478**](../financeiro/478-cadastro-fornecedores.md)
2. Informar o **CNPJ/CPF** do fornecedor
3. Verificar resultado:
   - **Se ja existe**: Conferir dados cadastrais, verificar se CCF esta ativa. Pular para ETAPA 4 (ativar CCF)
   - **Se nao existe**: Prosseguir com cadastro

> **DICA**: Busca por parte do nome tambem funciona (minimo 3 caracteres). Util quando nao se tem CNPJ em maos.

---

### ETAPA 2 — Preencher Dados Cadastrais (Opcao 478)

4. Preencher os campos de **identificacao**:

| Campo | Obrigatorio | O que preencher | Exemplo |
|-------|-------------|-----------------|---------|
| **CNPJ/CPF** | Sim | CNPJ do fornecedor (14 digitos PJ / 11 digitos PF) | 12.345.678/0001-90 |
| **Razao Social** | Sim | Nome juridico completo | ALEMAR TRANSPORTES E LOGISTICA LTDA |
| **Nome Fantasia** | Nao | Nome comercial | Alemar Transportes |
| **Inscricao Estadual** | Condicional | IE se PJ contribuinte, ou ISENTO | 123.456.789.000 |
| **UF** | Sim | Estado da sede do fornecedor | MS |
| **Ativo** | Sim | Sempre **S** para novo fornecedor | S |

5. Definir a **especialidade** conforme tipo de fornecedor:

| Tipo de Fornecedor | Especialidade | Quando usar |
|--------------------|---------------|-------------|
| Transportadora parceira | Agencias/Parceiros | Subcontratacao, redespacho, agenciamento |
| Motorista autonomo avulso | Carreteiros | Contratacao avulsa de TAC |
| Motorista autonomo fixo | Agregados | Contratacao por periodo de TAC |
| Motorista proprio | Frota | Motoristas CLT da CarVia |
| Oficina, posto, borracharia | Prestadores de servico | Manutencao, abastecimento, pneus |

> **BUSCA PARCIAL**: O campo Especialidade aceita busca parcial (ex: "agen" encontra "Agencias/Parceiros").

---

### ETAPA 3 — Preencher Dados Bancarios (Opcao 478)

6. Preencher os dados bancarios do **fornecedor** (nao da CarVia):

| Campo | Obrigatorio | O que preencher | Observacao |
|-------|-------------|-----------------|------------|
| **Banco** | Condicional | Codigo do banco do fornecedor | Obrigatorio se recebe pagamentos |
| **Agencia** | Condicional | Numero da agencia | Sem digito verificador |
| **Conta Corrente** | Condicional | Numero da conta | Com digito verificador |
| **Tipo de conta** | Condicional | Conta corrente ou poupanca | Padrao: conta corrente |

> **ATENCAO**: Os dados bancarios aqui sao do **FORNECEDOR** (conta dele), nao da CarVia. A conta da CarVia fica na unidade (401). Erro comum: colocar conta da CarVia no campo do fornecedor.

7. Preencher **contato** (se disponivel):

| Campo | O que preencher | Observacao |
|-------|-----------------|------------|
| **Telefone** | Telefone do fornecedor | Para contato operacional |
| **E-mail** | E-mail do fornecedor | Recebe extrato CCF e CTRBs automaticamente |

> **E-MAIL IMPORTANTE**: O e-mail cadastrado aqui e usado para envio automatico de extrato CCF e CTRBs no acerto de saldo. Preencher corretamente.

---

### ETAPA 4 — Ativar CCF (Conta Corrente do Fornecedor)

> **CRITICO**: Esta e a etapa mais importante. CCF sem ativacao NAO e reconhecida por nenhum processo do SSW.

8. No mesmo cadastro da [opcao **478**](../financeiro/478-cadastro-fornecedores.md), preencher os campos de CCF:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **CCF ativada** | **S** | Obrigatorio para qualquer fornecedor que tenha movimentacao financeira |
| **Evento padrao** | Evento de subcontratacao ([503](../fiscal/503-manutencao-de-eventos.md)) | Define classificacao da despesa no acerto automatico |
| **Unidade pagamento** | **CAR** ou **MTZ** | Unidade responsavel pelo pagamento (ver regra abaixo) |

> **EVENTO PADRAO**: Deve ser cadastrado previamente na [opcao 503](../fiscal/503-manutencao-de-eventos.md). Para transportadoras parceiras, usar evento de "Frete subcontratado". Se eventos ainda nao foram cadastrados (PEND-06), deixar vazio e preencher posteriormente.

> **UNIDADE PAGAMENTO**: Define onde o lancamento de Contas a Pagar (475) sera criado no acerto automatico. CarVia usa **MTZ** (centralizado) ou **CAR** (operacional).

9. Clicar em **Gravar** para salvar o cadastro com CCF ativa

---

### ETAPA 5 — Verificar Ativacao da CCF

10. Confirmar que a CCF foi ativada:
    - Acessar [opcao **486**](../financeiro/486-conta-corrente-fornecedor.md) (Conta Corrente do Fornecedor)
    - Informar CNPJ do fornecedor recem-cadastrado
    - **Se abrir a tela de saldo**: CCF esta ativa e funcional
    - **Se der erro ou nao encontrar**: Voltar a [opcao 478](../financeiro/478-cadastro-fornecedores.md) e verificar campo CCF ativada = S

11. (Opcional) Verificar na opcao **535** (Consulta a Fornecedores):
    - Marcar filtro "Com Conta Corrente = S"
    - Confirmar que o novo fornecedor aparece na lista

---

### ETAPA 6 — Cadastrar como Transportadora (Opcao 485)

> **QUANDO FAZER**: Somente se o fornecedor for transportadora parceira de subcontratacao. NAO necessario para carreteiros, agregados ou prestadores de servico.

12. Acessar [opcao **485**](../financeiro/485-cadastro-transportadoras.md)
13. Informar o **CNPJ** da transportadora
14. Preencher os campos:

| Campo | Obrigatorio | Valor | Exemplo |
|-------|-------------|-------|---------|
| **CNPJ** | Sim | CNPJ da transportadora parceira | CNPJ Alemar |
| **Sigla** | Sim | Sigla unica (3-5 caracteres) | ALMR |
| **Razao Social** | Sim | Razao social completa | ALEMAR TRANSPORTES E LOGISTICA LTDA |
| **Nome Fantasia** | Nao | Nome comercial | Alemar |
| **Endereco** | Sim | Endereco completo da sede | Rua X, 100, Bairro Y |
| **Cidade/UF** | Sim | Cidade e estado da sede | Campo Grande/MS |
| **CEP** | Sim | CEP da sede | 79000-000 |

15. Clicar em **Gravar**

> **POR QUE 485**: A [opcao 408](../comercial/408-comissao-unidades.md) (custos/comissoes) exige que o fornecedor esteja cadastrado como transportadora na 485. Sem esse cadastro, a 408 retorna erro "subcontratado nao encontrado".

> **SIGLA 485 vs SIGLA 401**: A sigla na 485 identifica a transportadora (ex: ALMR). A sigla na 401 identifica a unidade/praca (ex: CGR). Sao coisas diferentes — uma transportadora pode ter varias unidades.

---

### ETAPA 7 — Verificar Cadastro Completo

16. Conferir na [opcao **478**](../financeiro/478-cadastro-fornecedores.md):
    - Dados cadastrais preenchidos (CNPJ, razao social, UF)
    - Dados bancarios do fornecedor corretos
    - CCF ativada = S
    - Evento padrao definido (se 503 ja configurada)
    - Ativo = S

17. Conferir na [opcao **485**](../financeiro/485-cadastro-transportadoras.md) (se transportadora):
    - Sigla unica definida
    - Dados cadastrais completos
    - Cadastro ativo

18. Conferir na [opcao **486**](../financeiro/486-conta-corrente-fornecedor.md) (CCF):
    - Tela abre sem erro ao informar CNPJ
    - Saldo inicial = R$ 0,00 (novo fornecedor)

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Quem cadastra** | Rafael cadastra na 478 | Rafael (sem delegacao prevista) |
| **CCF ativada** | Provavelmente NAO ativa nos fornecedores existentes (PEND-07) | Ativar CCF em TODOS os fornecedores com movimentacao |
| **Evento padrao ([503](../fiscal/503-manutencao-de-eventos.md))** | Eventos NAO cadastrados (PEND-06) | Cadastrar eventos: frete subcontratado, combustivel, pedagio, manutencao |
| **Opcao 485** | Rafael cadastra quando precisa da 408 | Cadastrar SEMPRE que for transportadora parceira |
| **Dados bancarios** | Preenchidos para pagamento direto | Manter — base para pagamento via 475/476 |
| **Quantidade fornecedores** | ~20 transportadoras + ~100 motoristas | Crescente conforme novos parceiros |
| **Acerto automatico CCF** | NAO usa (sem eventos 503 nem processamento 903) | Implantar acerto batch por Mapa (forma M) |
| **Contas a pagar SSW** | NAO usa — pagamentos fora do SSW | Implantar uso da 475/476 para controle integrado |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| "CNPJ invalido" | CNPJ digitado incorretamente ou com menos de 14 digitos | Verificar CNPJ correto na documentacao do parceiro |
| CCF nao funciona na 486 | Campo "CCF ativada" nao foi marcado como S | Voltar a 478, marcar CCF ativada = S e gravar |
| 408 diz "subcontratado nao encontrado" | Fornecedor nao cadastrado na [opcao 485](../financeiro/485-cadastro-transportadoras.md) (transportadora) | Cadastrar na 485 ANTES de usar na 408 |
| Contratacao (072) nao credita CCF | CCF desativada ou evento padrao vazio | Ativar CCF=S e definir evento padrao na 478 |
| Dados bancarios da CarVia no fornecedor | Confusao — colocou conta da CarVia em vez da do fornecedor | Corrigir para dados bancarios do **fornecedor** |
| Acerto automatico nao gera despesa | Evento padrao ([503](../fiscal/503-manutencao-de-eventos.md)) nao definido ou nao cadastrado | Cadastrar evento na 503 e vincular ao fornecedor na 478 |
| Fornecedor nao aparece em selecoes | Ativo = N ou CCF desativada | Verificar Ativo=S e CCF ativada=S na 478 |
| E-mail de extrato nao enviado | Campo e-mail vazio na 478 | Preencher e-mail do fornecedor |
| Sigla 485 ja existe | Outra transportadora usa a mesma sigla | Usar variacao (ex: ALM2 se ALMR ja existir) |
| IE invalida | IE informada nao corresponde a UF do fornecedor | Verificar IE no SINTEGRA. Se nao contribuinte, deixar ISENTO |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Fornecedor existe na 478 | [Opcao 478](../financeiro/478-cadastro-fornecedores.md) → pesquisar CNPJ → dados basicos preenchidos |
| CNPJ/UF corretos | [Opcao 478](../financeiro/478-cadastro-fornecedores.md) → conferir CNPJ, UF, razao social |
| Dados bancarios preenchidos | [Opcao 478](../financeiro/478-cadastro-fornecedores.md) → banco, agencia, conta nao vazios |
| CCF ativada | [Opcao 478](../financeiro/478-cadastro-fornecedores.md) → campo CCF ativada = S |
| Evento padrao definido | [Opcao 478](../financeiro/478-cadastro-fornecedores.md) → campo evento padrao nao vazio |
| Fornecedor ativo | [Opcao 478](../financeiro/478-cadastro-fornecedores.md) → campo ativo = S |
| Transportadora na 485 | [Opcao 485](../financeiro/485-cadastro-transportadoras.md) → pesquisar CNPJ → sigla e dados preenchidos |
| CCF funcional na 486 | [Opcao 486](../financeiro/486-conta-corrente-fornecedor.md) → informar CNPJ → tela abre sem erro |
| Fornecedor na consulta 535 | Opcao 535 → filtro "Com CCF = S" → fornecedor na lista |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A10 | Implantar rota completa — este POP e a etapa 5 do A10 |
| POP-A02 | Cadastrar unidade parceira (401) — etapa anterior no A10 |
| POP-A06 | Cadastrar custos/comissao ([408](../comercial/408-comissao-unidades.md)) — proximo passo apos A05 (requer 478 + 485) |
| POP-D01 | Contratar veiculo (072) — credita CCF do fornecedor |
| POP-F01 | Contas a pagar (475) — recebe lancamento do acerto de saldo CCF |
| POP-F02 | CCF — gerenciar saldo com fornecedor (requer CCF ativa) |
| POP-F03 | Liquidar despesa (476) — pagar saldo ao fornecedor |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-16 | Criacao inicial — opcoes [478](../financeiro/478-cadastro-fornecedores.md) e [485](../financeiro/485-cadastro-transportadoras.md) com contexto CarVia e pendencias PEND-06/07 | Claude (Agente Logistico) |

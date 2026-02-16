# POP-A01 — Cadastrar Cliente Novo

> **Categoria**: A — Implantacao e Cadastros
> **Prioridade**: P1 (Alta — base para faturamento, cotacao e emissao de CT-e)
> **Status anterior**: JA FAZ
> **Criado em**: 2026-02-16
> **Executor atual**: Rafael
> **Executor futuro**: Jessica/Rafael

---

## Objetivo

Cadastrar um novo cliente no SSW da CarVia utilizando a [opcao 483](../cadastros/483-cadastro-clientes.md) (dados cadastrais) e a [opcao 384](../financeiro/384-cadastro-clientes.md) (parametros de faturamento). Ao final, o cliente deve estar apto para: receber cotacoes ([002](../operacional/002-consulta-coletas.md)), ter CT-e emitido em seu nome (004/007) e ser faturado corretamente (437/436).

Sem a [opcao 384](../financeiro/384-cadastro-clientes.md) configurada, o faturamento nao funciona corretamente — faturas ficam sem vencimento, sem banco de cobranca e sem envio automatico por e-mail.

---

## Trigger

- Novo cliente aprovado comercialmente (Jessica fecha negociacao)
- Primeiro frete para cliente que ainda nao existe no SSW
- Cotacao ([002](../operacional/002-consulta-coletas.md)) ou emissao de CT-e (004) exige cliente cadastrado

---

## Frequencia

Por demanda — a cada novo cliente. Estimativa: 10-15 minutos por cadastro completo (483 + 384).

---

## Pre-requisitos

| Requisito | Fonte | O que verificar |
|-----------|-------|-----------------|
| CNPJ/CPF do cliente | Documentacao comercial | CNPJ valido, situacao ativa no SEFAZ |
| Razao Social e endereco | NF-e do cliente ou contrato | Nome juridico, logradouro, CEP, cidade/UF |
| Inscricao Estadual | NF-e do cliente ou SINTEGRA | IE valida ou ISENTO |
| E-mail do cliente | Jessica (contato comercial) | E-mail para envio de XML/DACTE e faturas |
| Tipo de cobranca definido | Rafael/Jessica | A VISTA, CARTEIRA (999) ou BANCO |
| Vendedor cadastrado (opcional) | [Opcao 415](../comercial/415-gerenciamento-vendedores.md) | Se for vincular vendedor ao cliente |

---

## Passo-a-Passo

### ETAPA 1 — Verificar se Cliente Ja Existe

1. Acessar [opcao **483**](../cadastros/483-cadastro-clientes.md)
2. Informar o **CNPJ/CPF** do cliente (14 digitos PJ / 11 digitos PF)
3. Verificar resultado:
   - **Se ja existe**: Conferir dados e atualizar se necessario. Pular para ETAPA 4 ([384](../financeiro/384-cadastro-clientes.md))
   - **Se nao existe**: SSW busca em outros dominios para auxiliar preenchimento. Prosseguir com cadastro

> **DICA**: Tambem e possivel buscar por parte do nome (minimo 3 caracteres). Util quando nao se tem CNPJ em maos.

---

### ETAPA 2 — Preencher Dados Basicos (Opcao 483)

4. Preencher os campos de **identificacao**:

| Campo | O que preencher | Exemplo |
|-------|-----------------|---------|
| **CNPJ/CPF** | CNPJ do cliente (14 digitos) | 12.345.678/0001-90 |
| **Tipo** | Automatico (CNPJ ou CPF) | CNPJ |
| **IE** | Inscricao Estadual ou ISENTO | 123.456.789.000 |
| **CFOP** | I-industria, C-comercio, N-nao contribuinte, R-rural | C |
| **SN** | Optante pelo Simples Nacional? S/N | N |
| **Nome** | Razao Social completa | MOTOCHEFE COMERCIO DE MOTOS LTDA |

5. Preencher **endereco**:

| Campo | O que preencher | Observacao |
|-------|-----------------|------------|
| **Endereco** | Logradouro + numero | Rua das Flores, 123 |
| **Complemento** | Sala, andar, bloco (opcional) | Galpao 5 |
| **Bairro** | Obrigatorio | Centro |
| **CEP** | 8 digitos | 06501-001 |
| **Cidade/UF** | Buscar via link se necessario | Santana de Parnaiba/SP |

6. Preencher **contato**:

| Campo | O que preencher | Observacao |
|-------|-----------------|------------|
| **E-mail** | E-mail(s) do cliente | Separar multiplos por ponto-e-virgula |
| **Celular** | Celular do contato | Necessario para SMS |
| **Telefone** | Telefone fixo (opcional) | — |

> **IMPORTANTE**: O e-mail informado aqui atualiza automaticamente o e-mail de cobranca na [opcao 384](../financeiro/384-cadastro-clientes.md) se este estiver vazio. Preencher corretamente desde o inicio.

---

### ETAPA 3 — Configurar Parametros Operacionais (Opcao 483)

7. Preencher os campos operacionais:

| Campo | Valor recomendado CarVia | Observacao |
|-------|--------------------------|------------|
| **Vendedor** | Jessica (se cadastrada na 415) | Vincular vendedor responsavel |
| **Classificacao** | **C** (Comum) | E (Especial) apenas para clientes que exigem negociacao previa |
| **Unidade responsavel** | **CAR** | Unidade operacional CarVia |
| **Resp. automatica** | **A** (Automatica) | SSW ajusta conforme [opcao 402](../cadastros/402-cidades-atendidas.md) |
| **Praca da tabela** | **O** (Operacional) | Usa praca operacional (P/R/I das cidades) |
| **ICMS/ISS na tabela** | **S** (ja incluso) | Padrao CarVia — impostos ja inclusos na tabela 420 |
| **PIS/COFINS na tabela** | **S** (ja incluso) | Padrao CarVia — impostos ja inclusos |
| **Pode agrupar NF** | **N** | Padrao: nao agrupar NFs no CTRC |
| **Verifica CIF/FOB** | **N** | Nao restringir por tipo de frete da cidade |

8. Configurar **cobranca**:

| Campo | Valor CarVia HOJE | Valor CarVia FUTURO |
|-------|-------------------|---------------------|
| **Cobranca** | **CARTEIRA** (banco 999) | BANCO (quando implantar boleto) |
| **Paga TDA** | N | Avaliar por cliente |
| **Paga TDE** | N | Avaliar por cliente |

9. Configurar **servicos adicionais** (se aplicavel ao cliente):

| Campo | Quando marcar S |
|-------|-----------------|
| **Exige agendamento** | Cliente requer agendamento de entrega |
| **Exige paletizacao** | Cliente exige mercadoria paletizada |
| **Entrega dificil** | Destinatario em local de dificil acesso |

10. Clicar em **Atualizar** para salvar o cadastro

---

### ETAPA 4 — Configurar Faturamento (Opcao 384)

> **CRITICO**: Esta etapa e frequentemente PULADA pela CarVia hoje. Sem 384 configurado, faturamento nao funciona corretamente.

11. Acessar [opcao **384**](../financeiro/384-cadastro-clientes.md) — pode ser feito de duas formas:
    - Direto: digitar 384 no menu
    - Via 483: clicar no link **Faturamento** no rodape do cadastro do cliente

12. Informar o **CNPJ** do cliente e acessar

13. Preencher os campos de faturamento:

| Campo | Valor CarVia HOJE | Valor CarVia FUTURO | Observacao |
|-------|-------------------|---------------------|------------|
| **Unidade de cobranca** | **MTZ** | MTZ | Faturamento centralizado na matriz |
| **Forma de liquidacao** | **999** (carteira) | Banco/Ag/Conta | 999 = cobranca propria (sem boleto) |
| **Prazo de vencimento** | **30** dias | Conforme negociacao | Dias corridos apos faturamento |
| **Envia fatura** | **(nao configura)** | **Email** | Habilitar envio automatico |
| **E-mail** | **(vazio)** | E-mail do financeiro do cliente | Para receber faturas automaticamente |
| **Observacao fatura** | (opcional) | Texto padrao se necessario | Impresso na fatura |

> **BANCO 999**: Significa cobranca em carteira — a CarVia nao emite boleto bancario. O cliente deposita/transfere diretamente na conta. Este e o modelo atual da CarVia.

14. Clicar em **Gravar** para salvar configuracao

---

### ETAPA 5 — Verificar Cadastro Completo

15. Conferir na [opcao **483**](../cadastros/483-cadastro-clientes.md):
    - Dados basicos preenchidos (CNPJ, nome, endereco, e-mail)
    - Parametros operacionais corretos (unidade CAR, classificacao, praca)
    - Cobranca definida

16. Conferir na [opcao **384**](../financeiro/384-cadastro-clientes.md):
    - Unidade de cobranca = MTZ
    - Forma de liquidacao definida (999 ou banco)
    - Prazo de vencimento preenchido
    - E-mail preenchido (para envio futuro de faturas)

17. (Opcional) Testar uma **cotacao** na [opcao **002**](../operacional/002-consulta-coletas.md):
    - Informar dados de teste (origem CAR, destino conhecido, peso 100kg)
    - Verificar se retorna preco correto
    - Confirma que o cliente esta apto para operacao

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Quem cadastra** | Rafael cadastra na 483 | Jessica cadastra dados basicos, Rafael valida |
| **Opcao 384** | NAO configura — fatura manual pela 437 | Configurar para TODOS os clientes |
| **Cobranca** | Sem boleto — cliente deposita na conta | Boleto via 444 (POP-E04) |
| **Envio de fatura** | Rafael fatura → Jessica envia ao cliente | Automatico por e-mail (384 configurada) |
| **Prazo vencimento** | Sem prazo formal | 30 dias padrao (ajustar por cliente) |
| **E-mail na 384** | Vazio | Preenchido — habilita envio automatico |
| **Tipo faturamento** | M (manual) — 437 | M (manual) inicialmente, avaliar A (automatico) no futuro |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| "CNPJ invalido" | CNPJ digitado incorretamente ou com menos de 14 digitos | Verificar CNPJ correto na documentacao do cliente |
| SSW assume CFOP=I indevidamente | Nome do cliente contem "industria" | Corrigir CFOP manualmente para C ou N |
| Cotacao nao retorna preco | Cliente sem tabela vinculada ou sem rota | Verificar se rota existe (403) e tabela ativa (420) |
| Fatura sem vencimento | 384 nao configurada ou prazo zerado | Acessar 384 e preencher prazo de vencimento |
| Fatura sem e-mail de envio | E-mail vazio na 384 | Cadastrar e-mail na [opcao 384](../financeiro/384-cadastro-clientes.md) |
| CT-e rejeitado (destinatario inativo) | IE do destinatario com situacao B, N ou S no SEFAZ | Verificar situacao cadastral via SINTEGRA. Alertar cliente |
| E-mail invalido recusado | SSW valida dominio do e-mail | Confirmar e-mail correto com o cliente |
| Simples Nacional incorreto | SN marcado erroneamente — afeta tributacao ICMS | Consultar portal do Simples Nacional ou SEFAZ |
| ICMS/ISS na tabela = N causa frete maior | ICMS adicionado como parcela separada | Definir S (ja incluso) — padrao CarVia |
| Unidade responsavel errada | Automatica pegou unidade incorreta | Mudar para M (manual) e definir CAR |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Cliente existe na 483 | [Opcao 483](../cadastros/483-cadastro-clientes.md) → pesquisar CNPJ → dados basicos preenchidos |
| CNPJ/IE corretos | [Opcao 483](../cadastros/483-cadastro-clientes.md) → conferir CNPJ, IE, CFOP, SN |
| Endereco completo | [Opcao 483](../cadastros/483-cadastro-clientes.md) → CEP, cidade/UF, bairro preenchidos |
| E-mail preenchido | [Opcao 483](../cadastros/483-cadastro-clientes.md) → campo e-mail nao vazio |
| Parametros operacionais | [Opcao 483](../cadastros/483-cadastro-clientes.md) → unidade=CAR, classificacao=C, praca=O |
| 384 configurada | [Opcao 384](../financeiro/384-cadastro-clientes.md) → CNPJ → unidade cobranca, forma liquidacao, prazo preenchidos |
| E-mail na 384 | [Opcao 384](../financeiro/384-cadastro-clientes.md) → campo e-mail preenchido (para envio automatico) |
| Cotacao funciona | [Opcao 002](../operacional/002-consulta-coletas.md) → CNPJ cliente + dados teste → valor retornado > 0 |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-E02 | Faturar manualmente — proximo passo apos cadastro (usa 384) |
| POP-E01 | Pre-faturamento — verificar CTRCs disponiveis para faturar |
| POP-E03 | Faturamento automatico — requer 384 com tipo A |
| POP-C01 | Emitir CT-e fracionado — usa dados do cliente ([483](../cadastros/483-cadastro-clientes.md)) |
| POP-C02 | Emitir CT-e carga direta — usa dados do cliente ([483](../cadastros/483-cadastro-clientes.md)) |
| POP-B01 | Cotar frete — usa dados do cliente para cotacao |
| POP-A10 | Implantar nova rota — pode ser necessario se cliente atende cidade nova |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-16 | Criacao inicial — opcoes [483](../cadastros/483-cadastro-clientes.md) e [384](../financeiro/384-cadastro-clientes.md) com contexto CarVia | Claude (Agente Logistico) |

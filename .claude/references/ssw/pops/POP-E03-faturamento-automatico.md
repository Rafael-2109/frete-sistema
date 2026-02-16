# POP-E03 — Faturar Automaticamente (Faturamento Geral)

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: [436](../financeiro/436-faturamento-geral.md), [384](../financeiro/384-cadastro-clientes.md), [435](../financeiro/435-pre-faturamento.md)
> **Executor atual**: Rafael (nao usa — so fatura manual via [437](../financeiro/437-faturamento-manual.md))
> **Executor futuro**: Jaqueline

---

## Objetivo

Executar o faturamento automatico de todos os CTRCs disponiveis conforme regras cadastradas no cliente ([opcao 384](../financeiro/384-cadastro-clientes.md)). O SSW agrupa CTRCs em faturas seguindo parametrizacoes de periodicidade (mensal, quinzenal, etc.), separacao (por tipo, mercadoria, etc.) e vencimento. Este POP e a alternativa automatizada ao faturamento manual (POP-E02).

---

## Quando Executar (Trigger)

- Faturamento programado (diario, semanal, quinzenal, mensal) conforme periodicidade de cada cliente
- Volume de CTRCs justifica processamento em lote (> 50 CTRCs/cliente)
- Clientes configurados com **Tipo de faturamento = A** (automatico) na [opcao 384](../financeiro/384-cadastro-clientes.md)
- Automatizacao via [opcao 903](../cadastros/903-parametros-gerais.md)/Cobranca programada para 6:00h

---

## Frequencia

- **Diaria** (se [opcao 903](../cadastros/903-parametros-gerais.md) configurada e clientes tipo A existirem)
- **Manual** (antes de ativar automacao — para teste)
- **Por demanda** (faturamento especial fora da programacao)

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Usuario em unidade MTZ | — | Faturamento so pode ser executado por usuario em matriz |
| CTRCs autorizados SEFAZ | [007](../operacional/007-emissao-cte-complementar.md) | CTes com status "Autorizado" |
| Cliente tipo A | [384](../financeiro/384-cadastro-clientes.md) | Tipo de faturamento = A (automatico) |
| Parametros de faturamento | [384](../financeiro/384-cadastro-clientes.md) | Periodicidade, separacao, banco/carteira, vencimento, e-mail |
| Mes contabil nao fechado | [559](../contabilidade/559-saldo-contas-fechamento.md) | Mes de emissao nao pode estar fechado |
| Vias de cobranca (se exigir) | 434 | Cliente com condicao "Via de Cobranca Recepcionada" |

> **ATENCAO**: Cliente com tipo M (manual) NAO sera processado pela [opcao 436](../financeiro/436-faturamento-geral.md). Usar [opcao 437](../financeiro/437-faturamento-manual.md) (POP-E02) para esses clientes.

---

## Passo-a-Passo

### ETAPA 1 — Verificar Pre-Faturamento (Recomendado)

1. Acessar [opcao **435**](../financeiro/435-pre-faturamento.md) (CTRCs Disponiveis para Faturamento)
2. Verificar CTRCs disponiveis por periodicidade:
   - Clientes tipo A
   - E-mails cadastrados (coluna ENV e E-MAILS)
   - Sem bloqueios financeiros (coluna BLOQUEADO)
   - Fora do arquivo morto
3. Resolver pendencias antes de processar (ver POP-E01)

> **Se pular esta etapa**: Risco de faturas nao enviadas (sem e-mail) ou CTRCs bloqueados incluidos indevidamente.

---

### ETAPA 2 — Acessar Opcao 436

4. Verificar que unidade ativa e **MTZ** (matriz)
   - Faturamento geral so pode ser executado na unidade MTZ
5. Acessar [opcao **436**](../financeiro/436-faturamento-geral.md) (Faturamento Geral)

---

### ETAPA 3 — Configurar Parametros de Selecao

6. Preencher filtros de selecao:

| Campo | Valor recomendado | Observacao |
|-------|-------------------|------------|
| **Empresa** | [Deixar vazio = todas] | Apenas se multiempresa configurada |
| **CTRCs autorizados ate** | Data atual | Seleciona CTRCs autorizados ate esta data |
| **Data de emissao da fatura** | Data atual | Pode ser ate 15 dias passados ou ate 5 dias futuros |
| **Tipo de documento** | TODOS | Ou filtrar tipo especifico |
| **Considerar CTRCs baixados** | N | N=nao fatura (exceto complementares e devolvidos) |
| **Considerar CTRCs a vista** | N | **Cuidado**: se S, fatura CTRCs ja cobrados na entrega |
| **Selecionar as filiais** | [Vazio = todas] | Filiais de cobranca conforme [opcao 384](../financeiro/384-cadastro-clientes.md) |
| **Valor minimo da fatura** | [Vazio ou R$ minimo] | Desconsiderado se cliente bloqueado ou prazo limite atingido |
| **Periodicidade de faturamento** | Marcar X nas desejadas | Mensal, quinzenal, decenal, semanal, diario |
| **Data de vencimento** | [Vazio = usa 384] | Se informada, sobrescreve vencimento do cliente |
| **Desconsiderar banco do cliente** | N | N=usa banco do cliente (recomendado) |

> **ATENCAO — Periodicidade**: Marcar X em TODAS as periodicidades que devem ser processadas. Para faturamento diario automatico, marcar X em "diario".

---

### ETAPA 4 — Filtros Opcionais (Se Necessario)

7. Usar filtros opcionais para processamento especifico:

| Filtro | Quando usar |
|--------|-------------|
| **Manifestos (com DV)** | Faturar CTRCs de manifestos especificos |
| **CNPJ do cliente pagador** | Faturar cliente especifico (ignora tipo M/A) |
| **Selecionar CNPJs do grupo** | S=todos CNPJs do grupo ([opcao 583](../financeiro/583-grupo-clientes.md)) |
| **Selecionar CNPJs da raiz** | S=todos CNPJs da raiz (8 primeiros digitos) |
| **Codigo de mercadoria** | Faturar mercadorias especificas (opcao 386) |
| **Banco/Carteira** | Selecionar clientes com este banco. Carteira=999 (cobranca propria) |

> **Filtro CNPJ**: Usar CNPJ especifico FORCA faturamento mesmo se cliente for tipo M (manual). Util para casos excepcionais.

---

### ETAPA 5 — Simulacao (Recomendado)

8. Clicar em **"Simulacao Faturamento Sintetico"**
   - Totaliza por cliente (quantos CTRCs, valor total)
   - NAO gera faturas
9. Ou clicar em **"Simulacao Faturamento Analitico"**
   - Relaciona CTRCs que serao faturados
   - Mais detalhado
10. Conferir resultado da simulacao:
    - Clientes corretos
    - Valores corretos
    - Quantidade de CTRCs por fatura
11. Se erros ou inconsistencias: **PARAR** → Resolver na [opcao 384](../financeiro/384-cadastro-clientes.md) → Refazer simulacao

> **NUNCA pular a simulacao** em producao. Simulacao evita faturas erradas.

---

### ETAPA 6 — Confirmar Processamento

12. Se simulacao OK, **reabrir opcao [436](../financeiro/436-faturamento-geral.md)** com mesmos parametros
13. Clicar em **Confirmar Processamento** (botao principal, nao simulacao)
14. Sistema processa:
    - Agrupa CTRCs conforme parametrizacao de cada cliente ([opcao 384](../financeiro/384-cadastro-clientes.md))
    - Gera faturas
    - Envia faturas por e-mail automaticamente (primeiras horas do dia seguinte)
15. **Aguardar finalizacao** (pode demorar minutos para volume grande)

> **ATENCAO**: NAO submeter novo processamento antes de finalizar anterior. Risco de sobrecarga.

---

### ETAPA 7 — Verificar Resultado

16. Acessar [opcao **457**](../financeiro/457-manutencao-faturas.md) (Manutencao de Faturas)
17. Pesquisar faturas geradas:
    - Por CNPJ do cliente
    - Por data de emissao
18. Verificar:
    - Faturas geradas com valor correto
    - Vencimento correto
    - E-mail enviado (ou programado para envio)
19. Se cliente grande (> 5.000 CTRCs): fatura tera apenas resumo impresso (CTRCs enviados por EDI)

---

## Regras de Agrupamento (Opcao 384)

A [opcao 384](../financeiro/384-cadastro-clientes.md) define como o SSW agrupa CTRCs em faturas:

| Parametro | Opcoes | Como afeta faturamento |
|-----------|--------|------------------------|
| **Tipo** | A=automatico, M=manual | Se M, cliente NAO e processado pela [436](../financeiro/436-faturamento-geral.md) |
| **Periodicidade** | Mensal, quinzenal, decenal, semanal, diario | Quando faturar |
| **Separacao de faturas** | 1-9, C, K, J | Quebra faturas por criterio (ver tabela abaixo) |
| **Banco/Carteira** | Banco cobranca | Boleto ou carteira propria (999) |
| **Prazo vencimento** | Dias | Data vencimento = emissao + prazo |
| **E-mail** | E-mail do pagador | Destino da fatura (obrigatorio) |
| **Entregador** | Login do faturista | "Fatura so meus" filtra por entregador |

### Separacao de Faturas (Opcao 384)

| Codigo | Separa por | Quando usar |
|--------|-----------|-------------|
| 1 | CIF / FOB / Terceiro | Cliente com fretes CIF e FOB misturados |
| 2 | Codigo mercadoria | Mercadorias devem ser faturadas separadamente |
| 3 | Complementar | Separar CTes complementares |
| 4 | ICMS / ISS | Tributacao diferente |
| 5 | Adicionais / Abatimentos | Separar debitos e creditos |
| 6 | Unidade expedidora | Por filial que expediu |
| 7 | UF destino | Por estado de destino |
| 8 | FOB Dirigido | [CONFIRMAR] |
| 9 | PJ / PF | Pessoa juridica vs fisica |
| C | Cidade | Por cidade de destino |
| K | Peso (KG) | [CONFIRMAR] |
| J | CNPJ | Por CNPJ do destinatario (cliente final) |

> **Para CarVia**: A maioria dos clientes nao precisa separacao. Configurar na [opcao 384](../financeiro/384-cadastro-clientes.md) caso necessario.

---

## Contexto CarVia

### Hoje

- Rafael usa APENAS faturamento manual ([437](../financeiro/437-faturamento-manual.md))
- SEM boleto, SEM cobranca bancaria
- Cliente deposita diretamente na conta
- Jessica envia fatura ao cliente por e-mail (fora do SSW)

### Futuro (com POP implantado)

- Clientes grandes (MotoChefe, NotCo) migrados para tipo A (automatico)
- Faturamento automatico diario via [opcao 903](../cadastros/903-parametros-gerais.md) (6:00h)
- E-mail enviado automaticamente pelo SSW
- Cobranca bancaria via [opcao 444](../financeiro/444-cobranca-bancaria.md) (POP-E04)
- Jaqueline monitora apenas excecoes

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Nenhum cliente processado | Todos clientes tipo M ou sem CTRCs disponiveis | Verificar [opcao 384](../financeiro/384-cadastro-clientes.md) (tipo A) e [435](../financeiro/435-pre-faturamento.md) (CTRCs) |
| Fatura com valor zero nao gerada | Creditos maiores que debitos | Sistema nao gera fatura. Verificar [opcao 459](../financeiro/459-cadastro-tde.md) |
| Contabilidade fechada | Mes de emissao fechado ([opcao 559](../contabilidade/559-saldo-contas-fechamento.md)) | Reabrir mes ou usar data corrente |
| Faturas nao enviadas por e-mail | Cliente sem e-mail na [384](../financeiro/384-cadastro-clientes.md) | Cadastrar e-mail antes de faturar |
| Processamento lento | Volume muito grande (> 200.000 CTRCs) | Processar via [opcao 156](../comercial/156-fila-processamento-relatorios.md) ou por filial/cliente |
| Cliente bloqueado nao faturado | Bloqueio cadastral ou financeiro | Resolver bloqueio antes ou usar filtro CNPJ |
| CTRCs a vista faturados | "Considerar CTRCs a vista = S" | Cuidado: duplica cobranca (ja cobrado na entrega) |
| Fatura sem vencimento | Data vencimento nao configurada na 384 | Configurar prazo na [opcao 384](../financeiro/384-cadastro-clientes.md) |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Clientes tipo A existem | [Opcao 384](../financeiro/384-cadastro-clientes.md) → listar clientes → tipo = A |
| Parametros configurados | [Opcao 384](../financeiro/384-cadastro-clientes.md) → CNPJ → periodicidade, banco, e-mail preenchidos |
| CTRCs disponiveis | [Opcao 435](../financeiro/435-pre-faturamento.md) → gerar relatorio → lista nao vazia |
| Simulacao executada | [Opcao 436](../financeiro/436-faturamento-geral.md) → simulacao sintetica → resultado correto |
| Faturas geradas | [Opcao 457](../financeiro/457-manutencao-faturas.md) → pesquisar por data → faturas existem |
| E-mail enviado | [Opcao 457](../financeiro/457-manutencao-faturas.md) → detalhe fatura → historico de e-mail |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-E01 | Pre-faturamento — verificar antes de processar |
| POP-E02 | Faturamento manual — alternativa para clientes tipo M |
| POP-A01 | Cadastrar cliente — inclui configuracao da [opcao 384](../financeiro/384-cadastro-clientes.md) |
| POP-E04 | Cobranca bancaria — gerar boleto apos faturar |
| POP-E05 | Liquidar fatura — registrar recebimento |
| POP-E06 | Manutencao de faturas — alterar vencimento, protestar, baixar |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |

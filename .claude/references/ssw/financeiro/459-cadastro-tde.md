# Opcao 459 — Relacao de Adicionais (Debitos e Creditos)

> **Modulo**: Contas a Receber / CTRCs disponíveis (menu: Contas a Receber > CTRCs disponíveis > 459)
> **Status CarVia**: ACESSIVEL — tela de consulta/exclusao de adicionais disponiveis para faturamento
> **Atualizado em**: 2026-02-16
> **SSW interno**: ssw0182 | Verificado via Playwright em 16/02/2026

## Funcao

**CORRECAO**: A opcao 459 NAO e um cadastro de adicionais. O titulo real e **"Adicionais Disponíveis para Faturar"**. E uma tela de **consulta e exclusao** de adicionais ja registrados que estao disponiveis para entrar no faturamento. A opcao permite listar adicionais por periodo e empresa, e tambem excluir adicionais selecionados.

## Quando Usar

- Registrar custos extras que devem ser cobrados do cliente alem do frete do CTe
- Registrar descontos ou bonificacoes concedidos ao cliente
- Antes do faturamento (opcoes 436/437): adicionais devem estar cadastrados para serem incluidos na fatura
- Corrigir valores sem necessidade de CTe complementar (para pequenos ajustes comerciais)
- Controlar custos operacionais extras por CTRC e por cliente

## Pre-requisitos

- Adicionais ja registrados no sistema (cadastro acontece em OUTRA opcao, provavelmente 442)
- Adicionais disponiveis (nao faturados)

## Campos / Interface — VERIFICADOS

> **Verificado via Playwright em 16/02/2026 contra o SSW real.**

### Secao 1: Consulta de Adicionais

| Campo | Name/ID | Obrigatorio | Descricao |
|-------|---------|-------------|-----------|
| **Empresa** | cod_emp_ctb | Sim | Codigo da empresa contabil (default: "01"). Link para lista de empresas |
| **Periodo de inclusao Adicional (inicio)** | f2 / id=2 | Sim | Data inicio no formato ddmmaa (maxlen=6) |
| **Periodo de inclusao Adicional (fim)** | f3 / id=3 | Sim | Data fim no formato ddmmaa (maxlen=6) |
| **CNPJ do cliente** | f5 / id=5 | Opcional | CNPJ para filtrar por cliente (maxlen=14). Link "findcli" abre lookup |

### Secao 2: Exclusao de Adicionais

| Acao | Botao | Descricao |
|------|-------|-----------|
| **Listar para exclusao** | ► (`ajaxEnvia('EXC_LIS', 0)`) | Relaciona adicionais para selecionar e excluir |

### Acoes Disponiveis

| Botao | Acao |
|-------|------|
| **► (Pesquisar)** | `ajaxEnvia('PES', 0)` — lista adicionais disponiveis no periodo |
| **► (Excluir lista)** | `ajaxEnvia('EXC_LIS', 0)` — relaciona adicionais para exclusao |
| **×** | `btnClose()` — fecha/limpa |
| **?** | Abre ajuda SSW |

### Tipos Comuns de Adicionais (Debitos)

| Tipo | Quando Ocorre | Valor Tipico [CONFIRMAR] |
|------|---------------|--------------------------|
| **TDE** (Taxa Dificuldade Entrega) | Acesso restrito, area rural, morro | R$ 50 - R$ 200 |
| **Diaria de caminhao** | Retencao do veiculo > 2h na descarga | R$ 300 - R$ 500/dia |
| **Pernoite de motorista** | Entrega distante, motorista pernoita | R$ 100 - R$ 200 |
| **Taxa de agendamento** | Cliente exige horario especifico | R$ 50 - R$ 150 |
| **Re-entrega** | Recusa, ausencia, endereco errado | Valor do frete original |
| **Paletizacao** | Cliente solicita carga paletizada | R$ 30 - R$ 80/palete |
| **Hora extra** | Descarga fora do horario previsto | R$ 50 - R$ 150/hora |

### Tipos Comuns de Adicionais (Creditos)

| Tipo | Quando Ocorre |
|------|---------------|
| **Desconto comercial** | Acordo comercial com cliente |
| **Bonificacao por avaria** | Compensacao por avaria parcial |
| **Abatimento** | Reducao negociada no valor do frete |

## Fluxo de Uso

### Cadastrar Adicional

1. Acessar opcao 459
2. Informar numero do CTe/CTRC
3. Selecionar tipo: Debito ou Credito
4. Informar valor do adicional
5. Preencher descricao/justificativa
6. Gravar registro
7. Repetir para cada adicional do periodo

### Verificar Disponibilidade para Faturamento

1. Acessar opcao 435 (CTRCs Disponiveis para Faturamento)
2. Filtrar pelo cliente
3. Verificar se CTe aparece com adicionais vinculados
4. [CONFIRMAR: se adicionais aparecem em coluna separada ou somados ao valor do frete]

### Faturar com Adicionais

1. Opcao 437 (manual): selecionar CTe + adicionais na mesma fatura
2. Opcao 436 (automatico): sistema inclui adicionais automaticamente conforme regras da opcao 384
3. Alternativa: faturar apenas adicionais em fatura separada

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 435 | Pre-faturamento — mostra CTRCs com adicionais disponiveis |
| 436 | Faturamento geral — inclui adicionais automaticamente conforme opcao 384 do cliente |
| 437 | Faturamento manual — operador seleciona CTRCs + adicionais |
| 457 | Manutencao de faturas — pode adicionar debito/credito a fatura existente |
| 462 | Bloqueio financeiro — CTRCs bloqueados nao aparecem, adicionais associados tambem nao |
| 007 | Emissao CTe — alternativa: emitir CTe complementar (POP-C03) em vez de adicional |
| 523 | Horas de Estadia em Entregas (ssw0956) — relatorio de tempo retido, NAO cadastro de diarias |

## Observacoes e Gotchas

- **Opcao 459 NAO cadastra adicionais**: Apenas CONSULTA e EXCLUI adicionais ja registrados. O cadastro real acontece em outra opcao (provavelmente 442 — Credito/Debito em CTRC/Fatura)
- **Dois modos**: Pesquisar (listar adicionais por periodo/empresa/cliente) e Excluir (relacionar adicionais para remocao)
- **Credito maior que debito**: Se creditos (descontos) forem maiores que soma dos fretes + debitos, a fatura nao e gerada
- **CTe ja faturado**: Se CTe ja foi faturado, nao e possivel vincular novo adicional ao CTe. Usar opcao 457 (manutencao de faturas) para adicionar debito/credito direto na fatura
- **Opcao 523 e relatorio de estadia**: Titulo real "Horas de Estadia em Entregas" (ssw0956) — consulta tempos, NAO cadastra diarias

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-C04 | Registrar custos extras — POP completo passo-a-passo para esta opcao |
| POP-E01 | Pre-faturamento — verificar adicionais antes de faturar |
| POP-E02 | Faturar manualmente — incluir adicionais na fatura |
| POP-E03 | Faturamento automatico — adicionais incluidos automaticamente |
| POP-C03 | CTe complementar — alternativa formal para custos extras com documento fiscal |
| POP-D06 | Ocorrencias — evento gerador que pode resultar em custo extra |
| POP-E06 | Manutencao de faturas — adicionais consultados via 459 |
| POP-F05 | Bloqueio financeiro — adicionais de CTRCs bloqueados |

## Status CarVia

| Aspecto | Status |
|---------|--------|
| **Adocao** | VERIFICADO — tela acessivel (consulta/exclusao, NAO cadastro) |
| **Hoje** | Custos extras anotados em planilha. Para CADASTRAR, usar opcao 442 (Credito/Debito CTRC/Fatura), depois 459 para consultar |
| **Executor futuro** | Rafael (registro via 442) / Jaqueline (faturamento via 436/437) |
| **Impacto** | Custos extras nao cadastrados na 442 = nao aparecem na 459 = nao sao faturados = prejuizo |
| **POPs dependentes** | POP-C04 |

# Opcao 459 — Relacao de Adicionais (Debitos e Creditos)

> **Modulo**: Financeiro
> **Status CarVia**: NAO CONHECE
> **Atualizado em**: 2026-02-16

## Funcao

Cadastra e gerencia adicionais financeiros (debitos e creditos) vinculados a CTRCs, que serao incluidos automaticamente no faturamento. Adicionais representam custos extras nao previstos no CTe original (debitos ao cliente) ou descontos/bonificacoes (creditos ao cliente). Exemplos comuns: TDE (Taxa de Dificuldade de Entrega), diarias de caminhao, pernoites, taxas de agendamento, re-entregas, descontos comerciais.

## Quando Usar

- Registrar custos extras que devem ser cobrados do cliente alem do frete do CTe
- Registrar descontos ou bonificacoes concedidos ao cliente
- Antes do faturamento (opcoes 436/437): adicionais devem estar cadastrados para serem incluidos na fatura
- Corrigir valores sem necessidade de CTe complementar (para pequenos ajustes comerciais)
- Controlar custos operacionais extras por CTRC e por cliente

## Pre-requisitos

- CTe original autorizado pelo SEFAZ (opcao 007)
- Evento gerador do custo documentado (foto, relatorio, confirmacao do cliente)
- Valor do adicional definido (tabela contratual ou negociacao)
- [CONFIRMAR: se e necessario tipo/codigo de adicional pre-cadastrado]

## Campos / Interface

> **[CONFIRMAR]**: Campos inferidos do POP-C04 e das referencias nas opcoes 435, 436 e 437. Validar detalhes no ambiente SSW real.

### Tela Principal

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **CTe / CTRC** | Sim | Serie e numero do CTe ao qual o adicional sera vinculado |
| **Tipo** | Sim | Debito (cobrar do cliente) ou Credito (desconto/bonificacao ao cliente) |
| **[CONFIRMAR: Codigo adicional]** | [CONFIRMAR] | Pode haver tipos pre-cadastrados (TDE, diaria, pernoite, agendamento, etc.) |
| **Valor** | Sim | Valor monetario do adicional (R$) |
| **Descricao / Justificativa** | Sim | Texto explicativo do motivo do adicional (confirmado: POP-C04:75 — "Justificativa (texto curto)") |
| **Data do evento** | Sim | Data em que ocorreu o evento gerador (confirmado: POP-C04:61-62) |
| **Cliente** | Automatico | CNPJ do cliente — preenchido automaticamente pelo CTe |

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
| 523 | Cobranca estadia entrega — pode estar relacionado a cobranca de diarias [CONFIRMAR] |

## Observacoes e Gotchas

- **Cadastrar ANTES de faturar**: Adicionais nao cadastrados nao aparecem na fatura. Verificar opcao 459 antes de usar 436/437
- **Credito maior que debito**: Se creditos (descontos) forem maiores que soma dos fretes + debitos, a fatura nao e gerada
- **CTe ja faturado**: Se CTe ja foi faturado, nao e possivel vincular novo adicional ao CTe. Usar opcao 457 (manutencao de faturas) para adicionar debito/credito direto na fatura
- **Separacao de faturas**: A opcao 384 pode configurar separacao por adicionais/abatimentos (codigo 5), gerando faturas separadas para adicionais
- **Alternativa para custos formais**: Para custos extras que precisam de documento fiscal, usar CTe complementar (opcao 007, POP-C03) em vez de adicional
- **[CONFIRMAR]**: Verificar se existe relatorio de adicionais por cliente/periodo para controle gerencial

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
| **Adocao** | NAO CONHECE — Rafael nao sabe onde cadastrar custos extras no SSW |
| **Hoje** | Custos extras anotados em planilha, "encaixados" na proxima cotacao, ou simplesmente nao cobrados (prejuizo) |
| **Executor futuro** | Rafael (registro) / Jaqueline (faturamento) |
| **Impacto** | Custos extras nao cadastrados = nao aparecem na fatura = prejuizo |
| **POPs dependentes** | POP-C04 |

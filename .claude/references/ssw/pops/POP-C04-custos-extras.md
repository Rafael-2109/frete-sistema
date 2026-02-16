# POP-C04 — Registrar Custos Extras (TDE, Diaria, Pernoite)

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: 459
> **Executor atual**: Rafael
> **Executor futuro**: Rafael / Jaqueline

---

## Objetivo

Registrar custos extras (adicionais) que nao foram incluidos no CT-e original, mas devem ser cobrados do cliente. Custos extras comuns: TDE (Taxa de Dificuldade de Entrega), diaria de caminhao, pernoite de motorista, taxa de agendamento, re-entrega, entre outros.

---

## Quando Executar (Trigger)

- Entrega teve dificuldade especial (acesso restrito, descarga demorada)
- Caminhao ficou retido aguardando descarga (diaria)
- Motorista precisou pernoitar no destino (custo adicional)
- Cliente solicitou agendamento especial (taxa)
- Re-entrega por recusa ou ausencia do destinatario
- Qualquer custo extra acordado com o cliente apos emissao do CT-e

---

## Frequencia

Por demanda — processo semanal ou quinzenal, conforme ocorrencias.

---

## Pre-requisitos

- CT-e original JA autorizado e processado
- Ocorrencia ou evento gerador do custo documentado (foto, relatorio, confirmacao)
- Valor do custo extra acordado com cliente (tabela ou negociacao)
- Cliente ciente da cobranca (comunicacao previa)

---

## Passo-a-Passo

### ETAPA 1 — Identificar o Evento Gerador

1. Listar eventos que geraram custos extras no periodo:

| Tipo de Custo | Quando ocorre | Valor tipico [CONFIRMAR] |
|---------------|---------------|--------------------------|
| **TDE** (Taxa Dificuldade Entrega) | Acesso restrito, area rural, favela, morro | R$ 50 - R$ 200 |
| **Diaria de caminhao** | Descarga demorada, retencao > 2h | R$ 300 - R$ 500/dia |
| **Pernoite de motorista** | Entrega longe, motorista pernoita | R$ 100 - R$ 200 |
| **Taxa de agendamento** | Cliente exige agendamento especifico | R$ 50 - R$ 150 |
| **Re-entrega** | Recusa, ausencia, endereco errado | Valor do frete original |
| **Paletizacao** | Cliente solicita carga paletizada | R$ 30 - R$ 80/palete |
| **Hora extra de motorista** | Descarga > horario previsto | R$ 50 - R$ 150/hora |

2. Para cada evento, anotar:
   - [ ] Numero do CT-e relacionado
   - [ ] Data do evento
   - [ ] Tipo de custo extra
   - [ ] Valor a cobrar
   - [ ] Justificativa (texto curto)
   - [ ] Comprovante (se houver — foto, relatorio)

---

### ETAPA 2 — Cadastrar Custo Extra (Opcao 459)

3. Acessar [opcao **459**](../financeiro/459-cadastro-tde.md) (Relacao de Adicionais)
   - [CONFIRMAR] Nome exato da opcao no menu SSW

4. Informar dados do custo extra:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **CT-e** | Serie + numero do CT-e relacionado | O custo sera vinculado a este CT-e |
| **Tipo de adicional** | TDE / Diaria / Pernoite / Outro | [CONFIRMAR] Lista de tipos disponiveis |
| **Data do evento** | Data em que ocorreu o evento | Para controle |
| **Valor** | Valor a cobrar do cliente | Ex: R$ 150,00 |
| **Descricao / Justificativa** | Texto explicativo | Ex: "Entrega em area de dificil acesso" |
| **Debito / Credito** | Debito (cobrar do cliente) | [CONFIRMAR] Se ha opcao credito |
| **Cliente** | CNPJ do cliente | Preenchido automaticamente pelo CT-e |

5. Gravar o registro
6. Repetir para cada custo extra do periodo

---

### ETAPA 3 — Verificar Disponibilidade para Faturamento

7. Acessar [opcao **435**](../financeiro/435-pre-faturamento.md) (Pre-faturamento)
8. Filtrar pelo cliente
9. Verificar:
   - [ ] CT-e aparece na lista com "Adicionais disponíveis"
   - [ ] Valor adicional esta somado ao valor do frete
   - [ ] [CONFIRMAR] Se adicionais aparecem em coluna separada ou somados

---

### ETAPA 4 — Faturar Custos Extras

10. Opcoes de faturamento:

| Estrategia | Quando usar | Opcao SSW |
|------------|-------------|-----------|
| **Fatura separada** | Cliente prefere faturas separadas para custos extras | [437](../financeiro/437-faturamento-manual.md) (manual) |
| **Fatura conjunta** | Incluir custos extras na proxima fatura periodica | [436](../financeiro/436-faturamento-geral.md) (geral) |
| **Complemento no CT-e** | Formalizar custo extra como CT-e complementar | 007 (complementar) |

11. Se fatura separada:
    - [Opcao 437](../financeiro/437-faturamento-manual.md) → Selecionar apenas os "Adicionais" sem o CT-e original
    - Gerar fatura com descricao clara: "Custos Extras ref. CT-e XXXXX"

12. Se fatura conjunta:
    - Aguardar proxima fatura periodica (diaria/semanal/mensal)
    - [Opcao 436](../financeiro/436-faturamento-geral.md) agrupa automaticamente CT-es + adicionais

13. Se complemento no CT-e:
    - Ver POP-C03 (CT-e complementar)
    - Emitir CT-e complementar com valor dos custos extras

---

### ETAPA 5 — Comunicar Cliente

14. Enviar fatura ao cliente com:
    - Detalhamento dos custos extras
    - Justificativa de cada item
    - Comprovantes (se houver — fotos, relatorios)
    - Referencia ao CT-e original

15. Registrar comunicacao no sistema [CONFIRMAR opcao de registro]

---

## Contexto CarVia

### Hoje
Rafael nao sabe onde cadastrar custos extras no SSW. Quando ocorrem:
- Anota manualmente em planilha
- Tenta "encaixar" na proxima cotacao do cliente
- Ou deixa de cobrar (prejuizo)

### Futuro (com POP implantado)
- Registrar custos extras no SSW ([opcao 459](../financeiro/459-cadastro-tde.md))
- Custos automaticamente disponiveis para faturamento
- Rastreabilidade: custo vinculado ao CT-e
- Relatorios de custos extras por cliente e periodo

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Custo extra nao aparece no faturamento | Nao cadastrado na [opcao 459](../financeiro/459-cadastro-tde.md) | Cadastrar adicional antes de faturar |
| Cliente reclama da cobranca | Falta de comunicacao previa | Avisar cliente ANTES de faturar |
| Valor divergente do acordado | Erro de digitacao ou tabela desatualizada | Conferir tabela de custos extras (se houver) |
| Custo extra vinculado ao CT-e errado | Numero do CT-e digitado errado | Excluir registro e cadastrar novamente |
| Impossivel cadastrar adicional | CT-e ja faturado e pago | Usar CT-e complementar (POP-C03) ou fatura avulsa |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Adicional cadastrado | [Opcao 459](../financeiro/459-cadastro-tde.md) → pesquisar CT-e → adicional na lista |
| Disponivel para faturamento | [Opcao 435](../financeiro/435-pre-faturamento.md) → CT-e com "Adicionais disponiveis" |
| Fatura incluindo adicional | [Opcao 437](../financeiro/437-faturamento-manual.md) → fatura gerada → valor total = frete + adicionais |
| Cliente vinculado corretamente | [Opcao 459](../financeiro/459-cadastro-tde.md) → adicional → campo "Cliente" = CNPJ correto |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-C01 | Emitir CTe fracionado — CT-e base para o adicional |
| POP-C02 | Emitir CTe carga direta — CT-e base para o adicional |
| POP-C03 | CT-e complementar — alternativa para formalizar custos extras |
| POP-D06 | Ocorrencias — registro do evento gerador do custo |
| POP-E01 | Pre-faturamento — verificar adicionais disponiveis |
| POP-E02 | Faturar — incluir adicionais na fatura |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |

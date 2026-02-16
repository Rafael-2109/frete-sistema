# POP-C07 — Carta de Correcao CT-e

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: 007
> **Executor atual**: Rafael
> **Executor futuro**: Rafael / Jaqueline

---

## Objetivo

Emitir Carta de Correcao Eletronica (CC-e) para corrigir erros menores em CT-e ja autorizado, sem necessidade de cancelamento. A CC-e e um documento fiscal complementar que retifica dados do CT-e original.

---

## Quando Executar (Trigger)

- CT-e emitido com dados incorretos que **podem** ser corrigidos por carta de correcao
- Erro em endereco de entrega (rua, numero, complemento, bairro)
- Erro em CFOP (Codigo Fiscal de Operacao)
- Erro em dados do produto (descricao, codigo)
- Erro em observacoes ou informacoes complementares
- Qualquer erro que **NAO envolva valores, CNPJ ou chave de acesso**

---

## Frequencia

Ocasional — processo mais simples que cancelamento, usado para correcoes menores.

---

## Pre-requisitos

- CT-e JA autorizado pelo SEFAZ
- Erro identificado e **permitido** para correcao por CC-e (ver restricoes abaixo)
- Dados corretos em maos (para substituir os errados)

---

## Passo-a-Passo

### ETAPA 1 — Verificar se Erro Pode Ser Corrigido por CC-e

1. Consultar lista de campos **PERMITIDOS** para correcao [CONFIRMAR lista completa]:

| Campo | Corrigivel por CC-e | Observacao |
|-------|---------------------|------------|
| **Endereco de entrega** | ✅ Sim | Rua, numero, complemento, bairro, CEP |
| **CFOP** | ✅ Sim | Codigo fiscal de operacao |
| **Descricao do produto** | ✅ Sim | Texto descritivo |
| **Codigo do produto** | ✅ Sim | Codigo interno |
| **Observacoes** | ✅ Sim | Campo de observacoes do CT-e |
| **Informacoes complementares** | ✅ Sim | Textos adicionais |
| **Valor do frete** | ❌ Nao | Usar CT-e complementar (POP-C03) |
| **CNPJ remetente/destinatario** | ❌ Nao | Cancelar e reemitir (POP-C06) |
| **Chave da NF-e** | ❌ Nao | Cancelar e reemitir (POP-C06) |
| **Peso ou quantidade** | ❌ Nao | Usar CT-e complementar (POP-C03) |
| **ICMS** | ❌ Nao | Usar CT-e complementar (POP-C03) |

2. Se erro estiver na lista de **PERMITIDOS**: prosseguir
3. Se erro estiver na lista de **NAO PERMITIDOS**: usar alternativa (cancelamento ou complementar)

---

### ETAPA 2 — Emitir Carta de Correcao (Opcao 007)

4. Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md)
5. Procurar funcao **"Carta de Correcao"** ou link especifico [CONFIRMAR localizacao exata]
6. Informar dados do CT-e a corrigir:

| Campo | Valor |
|-------|-------|
| **CT-e** | Serie + numero do CT-e a corrigir |
| **Chave de acesso** | 44 digitos (opcional, mas recomendado) |

7. Sistema exibe dados atuais do CT-e
8. Informar correcoes:

| Campo | Valor | Exemplo |
|-------|-------|---------|
| **Grupo a corrigir** | Endereco / Produto / Observacao / CFOP | Ex: "Endereco de entrega" |
| **Campo especifico** | Nome do campo dentro do grupo | Ex: "Numero" |
| **Valor anterior (errado)** | Dado atual no CT-e | Ex: "123" |
| **Valor correto** | Dado que deveria estar | Ex: "456" |
| **Justificativa** | Texto livre explicando a correcao | Ex: "Numero do endereco incorreto" |

9. Adicionar multiplas correcoes se necessario (uma CC-e pode corrigir varios campos)

---

### ETAPA 3 — Enviar CC-e ao SEFAZ

10. Clicar **Enviar Carta de Correcao** ou **Transmitir CC-e**
11. Sistema envia CC-e ao SEFAZ
12. Aguardar resposta:
    - **CC-e autorizada**: Recebe numero de sequencia e protocolo SEFAZ
    - **CC-e rejeitada**: Verificar motivo (comum: campo nao permitido, CT-e cancelado)

---

### ETAPA 4 — Verificar CC-e Autorizada

13. Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) e pesquisar pelo CT-e
14. Verificar:
    - [ ] CT-e mostra vinculo com CC-e (numero de sequencia)
    - [ ] Protocolo de autorizacao da CC-e presente
    - [ ] Data/hora da correcao registrada
    - [ ] Campos corrigidos visiveis na consulta

15. Imprimir ou salvar PDF da CC-e (se necessario):
    - CC-e acompanha o DACTE durante o transporte
    - Cliente deve receber XML da CC-e junto com XML do CT-e

---

### ETAPA 5 — Comunicar Cliente e Transportadora

16. Enviar ao cliente:
    - XML da CC-e
    - PDF da CC-e (se solicitado)
    - Explicacao da correcao

17. Se transporte ja iniciou:
    - Comunicar transportadora parceira sobre a correcao
    - Enviar CC-e para acompanhar a carga

---

## Multiplas Cartas de Correcao

Um mesmo CT-e pode ter **multiplas CC-es** emitidas:
- Cada CC-e recebe numero de sequencia (1, 2, 3...)
- CC-es posteriores substituem CC-es anteriores nos campos corrigidos
- Todas as CC-es ficam vinculadas ao CT-e original

**Exemplo**:
1. CC-e 1: Corrige endereco (rua errada)
2. CC-e 2: Corrige CFOP (codigo errado)
3. Resultado: CT-e tem duas CC-es ativas simultaneamente

---

## Alternativas a Carta de Correcao

| Situacao | Alternativa | POP relacionado |
|----------|-------------|-----------------|
| Erro em valor | CT-e complementar | POP-C03 |
| Erro em CNPJ | Cancelar e reemitir | POP-C06 |
| Erro em chave NF-e | Cancelar e reemitir | POP-C06 |
| Erro em peso (afeta frete) | CT-e complementar | POP-C03 |

---

## Contexto CarVia

### Hoje
Rafael nunca emitiu CC-e. Quando ha erro menor:
- Cancela o CT-e (se dentro do prazo)
- Reemite com dados corretos
- Ou "deixa pra la" se erro nao afetar operacao

### Futuro (com POP implantado)
- Usar CC-e para correcoes menores (evitar cancelamento)
- Conhecer quais erros podem ser corrigidos por CC-e
- Evitar cancelamentos desnecessarios (que "poluem" historico fiscal)

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| SEFAZ rejeita: campo nao permitido | Tentou corrigir valor, CNPJ ou chave | Usar CT-e complementar (POP-C03) ou cancelar (POP-C06) |
| SEFAZ rejeita: CT-e cancelado | CT-e foi cancelado antes da CC-e | Impossivel corrigir CT-e cancelado |
| Cliente reclama de multiplas CC-es | Muitas correcoes em sequencia | Planejar correcoes — emitir uma CC-e unica com todas as correcoes |
| CC-e nao aparece no DACTE | Reimpressao sem atualizar | Reimprimir DACTE APOS emitir CC-e |
| Transportadora nao recebeu CC-e | Falta de comunicacao | Enviar XML/PDF da CC-e para transportadora |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| CC-e autorizada | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e → vinculo com CC-e (numero sequencia) |
| Protocolo SEFAZ | [Opcao 101](../comercial/101-resultado-ctrc.md) → CC-e → protocolo presente |
| Campos corrigidos | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e → dados atualizados |
| Multiplas CC-es | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e → lista de CC-es (1, 2, 3...) |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-C01 | Emitir CTe fracionado — CT-e base para correcao |
| POP-C02 | Emitir CTe carga direta — CT-e base para correcao |
| POP-C03 | CT-e complementar — alternativa para erros de valor |
| POP-C06 | Cancelar CTe — alternativa para erros graves |
| POP-C05 | Imprimir CTe — reimprimir DACTE com CC-e |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |

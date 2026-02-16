# POP-C03 — Emitir CT-e Complementar

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: 007
> **Executor atual**: Rafael
> **Executor futuro**: Rafael / Jaqueline

---

## Objetivo

Emitir CT-e complementar para ajustar valores, impostos ou dados de um CT-e ja autorizado. O CT-e complementar e um documento fiscal que "completa" um CT-e original, sendo usado quando o CT-e original foi emitido com valores menores que os devidos.

---

## Quando Executar (Trigger)

- CT-e emitido com valor de frete menor que o devido
- Complemento de ICMS (base de calculo ou aliquota errada)
- Ajuste de peso ou cubagem (gerando diferenca de frete)
- Cobranca de custos extras acordados posteriormente (TDE, diaria, pernoite)
- Cliente solicitou complemento por divergencia contratual

---

## Frequencia

Por demanda — processo excepcional, mas importante conhecer.

---

## Pre-requisitos

- CT-e original JA autorizado pelo SEFAZ ([opcao 007](../operacional/007-emissao-cte-complementar.md))
- Numero do CT-e original (serie + numero)
- Motivo do complemento claramente definido
- Valores corretos calculados (diferenca a complementar)
- Cliente ciente do complemento (se aplicavel)

---

## Passo-a-Passo

### ETAPA 1 — Identificar o CT-e Original

1. Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) (consulta de CTRC)
2. Pesquisar pelo CT-e original (por numero, chave ou NF-e)
3. Anotar:
   - [ ] Numero do CT-e original (serie + numero)
   - [ ] Chave de acesso (44 digitos)
   - [ ] Valor original do frete
   - [ ] Valor correto (que deveria ter sido cobrado)
   - [ ] Diferenca a complementar

---

### ETAPA 2 — Calcular Valores do Complemento

4. Definir tipo de complemento:

| Tipo | Quando usar | Exemplo |
|------|-------------|---------|
| **Complemento de Valor de Frete** | Frete calculado errado, tabela desatualizada | Frete era R$ 500, cobrado R$ 400 → complementar R$ 100 |
| **Complemento de ICMS** | Base de calculo ou aliquota errada | ICMS era 12%, cobrado 7% → complementar diferenca |
| **Complemento de Peso** | Peso real maior que declarado | Peso declarado 500kg, real 800kg → recalcular frete |
| **Complemento de Outros Valores** | TDE, diaria, pernoite nao incluidos | TDE de R$ 150 nao cobrada → complementar R$ 150 |

5. Calcular valores:
   - Valor do complemento = Valor correto - Valor original
   - ICMS do complemento (se aplicavel)
   - Componentes do frete (frete peso, GRIS, pedagio, etc.)

---

### ETAPA 3 — Emitir CT-e Complementar (Opcao 007)

6. Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md)
7. Procurar funcao **"CT-e Complementar"** ou link especifico para complementares
   - [CONFIRMAR] A funcao pode estar em menu lateral ou botao na tela inicial da 007

8. Informar dados do CT-e original:

| Campo | Valor |
|-------|-------|
| **CT-e original** | Serie + numero do CT-e a complementar |
| **Chave de acesso** | 44 digitos do CT-e original |
| **Tipo de complemento** | Valor / ICMS / Outros |

9. Informar valores do complemento:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Valor do complemento** | Diferenca entre correto e original | Ex: R$ 100,00 |
| **Frete Peso** | Diferenca no frete peso | Se aplicavel |
| **GRIS** | Diferenca no GRIS | Se aplicavel |
| **Pedagio** | Diferenca no pedagio | Se aplicavel |
| **TDE/TDC/TAR** | Taxas adicionais | Se aplicavel |
| **ICMS do complemento** | Calculado automaticamente | Ou informar manualmente |
| **Observacao** | Motivo do complemento | Texto livre, explicar ao cliente |

10. Gravar pre-CTRC complementar
11. Enviar ao SEFAZ (botao "Enviar CT-es ao SEFAZ")
12. Aguardar autorizacao:
    - **Autorizado**: CT-e complementar recebe numero proprio e protocolo
    - **Rejeitado**: Verificar motivo (comum: CT-e original cancelado, valores zerados)

---

### ETAPA 4 — Verificar Vinculacao

13. Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) e pesquisar pelo CT-e complementar
14. Verificar:
    - [ ] CT-e complementar autorizado
    - [ ] Campo "CT-e referenciado" aponta para o CT-e original
    - [ ] Valor total = valor do CT-e original + valor do complemento

15. Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) e pesquisar pelo CT-e original
16. Verificar:
    - [ ] CT-e original mostra vinculo com o complementar
    - [ ] Status permanece "Autorizado" (nao e cancelado)

---

### ETAPA 5 — Faturamento do Complemento

17. O CT-e complementar entra automaticamente no faturamento (opcao [435](../financeiro/435-pre-faturamento.md)/[437](../financeiro/437-faturamento-manual.md))
18. Opcoes de faturamento:
    - **Fatura separada**: Emitir fatura apenas com o CT-e complementar
    - **Fatura conjunta**: Incluir complemento na proxima fatura periodica do cliente
    - **Boleto avulso**: Se cliente ja pagou o CT-e original

19. Enviar fatura ao cliente com EXPLICACAO clara do motivo do complemento

---

## Contexto CarVia

### Hoje
Rafael nunca emitiu CT-e complementar. Se houver erro de valor, ele:
- Cancela o CT-e original (se dentro do prazo de 7 dias)
- Reemite com valor correto
- Ou "deixa pra la" se diferenca for pequena

### Futuro (com POP implantado)
- Usar CT-e complementar quando cancelamento nao for possivel (prazo vencido ou mercadoria ja embarcada)
- Formalizar cobranc a de custos extras acordados posteriormente
- Evitar cancelamentos desnecessarios (que "poluem" historico fiscal)

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| SEFAZ rejeita: CT-e original cancelado | CT-e original foi cancelado antes do complemento | Nao e possivel complementar CT-e cancelado. Emitir novo CT-e normal |
| SEFAZ rejeita: valor zerado | Complemento com valor R$ 0,00 | Verificar se valores foram informados corretamente |
| SEFAZ rejeita: chave invalida | Chave do CT-e original errada | Conferir chave de acesso (44 digitos) na [opcao 101](../comercial/101-resultado-ctrc.md) |
| Cliente reclama do complemento | Falta de comunicacao previa | Avisar cliente ANTES de emitir complemento |
| Complemento nao aparece no faturamento | CT-e complementar nao vinculado ao cliente | Verificar [opcao 435](../financeiro/435-pre-faturamento.md) — deve aparecer na lista |
| Valor do complemento divergente | Calculo manual errado | Usar simulacao da [opcao 004](../operacional/004-emissao-ctrcs.md) para calcular diferenca |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| CT-e complementar autorizado | [Opcao 007](../operacional/007-emissao-cte-complementar.md) → fila "Autorizados" → CT-e complementar presente |
| Vinculacao correta | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e complementar → campo "CT-e referenciado" = CT-e original |
| CT-e original nao cancelado | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e original → status = "Autorizado" |
| Valor total correto | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e original + complementar = valor correto |
| Faturamento disponivel | [Opcao 435](../financeiro/435-pre-faturamento.md) → CT-e complementar na lista |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-C01 | Emitir CTe fracionado — processo base |
| POP-C02 | Emitir CTe carga direta — processo base |
| POP-C04 | Custos extras — alternativa ao complemento para TDE/diaria |
| POP-C06 | Cancelar CTe — alternativa quando prazo permite |
| POP-E02 | Faturar — proximo passo (faturar o complemento) |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |

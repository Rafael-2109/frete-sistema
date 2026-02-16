# POP-C06 — Cancelar CT-e

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: 004, 024, 007
> **Executor atual**: Rafael
> **Executor futuro**: Rafael / Jaqueline

---

## Objetivo

Cancelar CT-e autorizado pelo SEFAZ quando houver erro que nao pode ser corrigido por carta de correcao. O cancelamento invalida o CT-e perante o fisco, impedindo que seja usado para transporte ou faturamento.

---

## Quando Executar (Trigger)

- CT-e emitido com dados errados que nao podem ser corrigidos por carta de correcao (POP-C07)
- Cliente cancelou o pedido antes do embarque
- Mercadoria nao sera transportada (perda total, devolucao ao remetente sem transporte)
- Duplicidade de CT-e (emitido em duplicidade por engano)
- CNPJ remetente ou destinatario errado
- Chave da NF-e errada (impossivel corrigir por carta de correcao)

---

## Frequencia

Excepcional — processo de correcao que deve ser evitado, mas importante conhecer.

---

## Pre-requisitos

- CT-e JA autorizado pelo SEFAZ
- Prazo: **Dentro de 7 dias** da data de autorizacao (limite SEFAZ) [CONFIRMAR prazo exato]
- Mercadoria **NAO embarcada** (risco de sinistro sem cobertura se ja embarcou)
- CT-e **NAO incluido em Manifesto** (ou Manifesto cancelado antes — ver restricao)
- CT-e **NAO faturado** ou fatura nao paga (fatura sera cancelada automaticamente)

---

## Passo-a-Passo

### ETAPA 1 — Verificar se Cancelamento e Possivel

1. Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) (Consulta de CTRC)
2. Pesquisar pelo CT-e a cancelar
3. Verificar:

| Condicao | Status | Se NAO atender |
|----------|--------|----------------|
| **Prazo** | Dentro de 7 dias da autorizacao | Impossivel cancelar — usar CT-e complementar (POP-C03) ou suportar erro |
| **Manifesto** | Nao manifestado OU Manifesto cancelado | Cancelar Manifesto primeiro (opcao 024) |
| **Embarque** | Mercadoria NAO embarcada | **RISCO CRITICO** — cancelar apos embarque = seguro pode nao cobrir sinistro |
| **Faturamento** | Nao faturado OU fatura nao paga | Avisar cliente — fatura sera cancelada |

4. Se TODAS as condicoes forem atendidas: prosseguir
5. Se ALGUMA condicao NAO for atendida: PARAR e avaliar alternativas

---

### ETAPA 2 — Cancelar Manifesto (Se Aplicavel)

6. Se CT-e ja foi incluido em Manifesto:
   - Acessar opcao **024** (Cancelamento de Manifesto)
   - Pesquisar pelo Manifesto que contem o CT-e
   - Verificar: Manifesto **NAO pode ter recebido saida** (opcao 025)
   - Se saida ja foi dada: **Impossivel cancelar Manifesto** — mercadoria ja embarcou
   - Cancelar Manifesto
   - Retornar a este POP para cancelar o CT-e

---

### ETAPA 3 — Cancelar CT-e (Opcao 004 ou 007)

#### Metodo A — Cancelamento pela Opcao 004 (Pre-CTRC)

7. Se CT-e ainda esta em **Pre-CTRC** (nao enviado ao SEFAZ):
   - Acessar [opcao **004**](../operacional/004-emissao-ctrcs.md)
   - Link no rodape: **"Cancelar"**
   - Informar numero do CTRC
   - Sistema pergunta: **"Confirma cancelamento?"** → **Sim**
   - Pre-CTRC cancelado (nao envia nada ao SEFAZ)

#### Metodo B — Cancelamento pela Opcao 007 (CT-e Autorizado)

8. Se CT-e JA autorizado pelo SEFAZ:
   - Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md)
   - Procurar funcao **"Cancelar CT-e"** ou link especifico [CONFIRMAR localizacao exata]
   - Informar:

| Campo | Valor |
|-------|-------|
| **CT-e** | Serie + numero do CT-e a cancelar |
| **Chave de acesso** | 44 digitos (opcional, mas recomendado) |
| **Motivo do cancelamento** | Texto livre — ex: "CNPJ destinatario incorreto" |

9. Clicar **Cancelar CT-e**
10. Sistema envia pedido de cancelamento ao SEFAZ
11. Aguardar resposta:
    - **Cancelamento autorizado**: CT-e recebe status "Cancelado"
    - **Cancelamento rejeitado**: Verificar motivo (comum: prazo vencido, CT-e ja manifestado)

---

### ETAPA 4 — Verificar Cancelamento

12. Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) e pesquisar pelo CT-e
13. Verificar:
    - [ ] Status = **"Cancelado"**
    - [ ] Protocolo de cancelamento SEFAZ presente
    - [ ] Data/hora do cancelamento registrada
    - [ ] Motivo do cancelamento visivel

14. Se CT-e estava em Manifesto:
    - Verificar que Manifesto foi cancelado (opcao 024 ou [025](../operacional/025-saida-veiculos.md))
    - Verificar que nao ha MDF-e ativo com este CT-e

---

### ETAPA 5 — Efeitos Colaterais e Proximos Passos

15. Efeitos automaticos do cancelamento:

| Efeito | Descricao |
|--------|-----------|
| **Fatura cancelada** | Se CT-e estava em fatura, fatura e cancelada automaticamente |
| **Boleto cancelado** | Se boleto foi emitido, e cancelado |
| **Averbacao cancelada** | Seguradora recebe cancelamento automaticamente (AT&M) |
| **CCF ajustada** | Se CT-e gerou credito/debito em CCF, e estornado [CONFIRMAR] |

16. Proximos passos:
    - **Se erro foi corrigido**: Emitir novo CT-e com dados corretos (POP-C01 ou POP-C02)
    - **Se transporte nao ocorrera**: Nenhum proximo passo — operacao encerrada
    - **Se cliente ja pagou**: Reembolsar ou compensar em proxima fatura

---

## Alternativas ao Cancelamento

| Situacao | Alternativa | POP relacionado |
|----------|-------------|-----------------|
| Erro menor (endereco, CFOP) | Carta de correcao | POP-C07 |
| Valor errado | CT-e complementar | POP-C03 |
| Prazo de cancelamento vencido | Suportar erro ou emitir complementar | POP-C03 |
| Mercadoria ja embarcou | **NAO CANCELAR** — risco de sinistro sem cobertura | POP-G01 |

---

## Contexto CarVia

### Hoje
Rafael cancela CT-es quando necessario, mas:
- Nao sabe todas as restricoes (prazo, manifesto, embarque)
- Nao conhece alternativas (carta de correcao, complementar)
- Risco de cancelar apos embarque sem perceber o risco

### Futuro (com POP implantado)
- Checklist de pre-condicoes antes de cancelar
- Conhecimento de alternativas (evitar cancelamento desnecessario)
- Ciencia do risco de cancelar apos embarque

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| SEFAZ rejeita: prazo vencido | Mais de 7 dias da autorizacao | Usar CT-e complementar (POP-C03) ou suportar erro |
| SEFAZ rejeita: CT-e manifestado | CT-e incluido em Manifesto nao cancelado | Cancelar Manifesto primeiro (opcao 024) |
| Sistema bloqueia cancelamento | CT-e em fatura paga ou manifesto com saida | Contactar Equipe SSW para orientacao |
| Cancelamento apos embarque | Erro operacional critico | **RISCO** — seguro pode nao cobrir sinistro. Contactar seguradora IMEDIATAMENTE |
| Cliente reclama de fatura cancelada | Falta de comunicacao | Avisar cliente ANTES de cancelar CT-e |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| CT-e cancelado | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e → status = "Cancelado" |
| Protocolo de cancelamento | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e → protocolo SEFAZ presente |
| Fatura cancelada | [Opcao 437](../financeiro/437-faturamento-manual.md) → pesquisar fatura → status = "Cancelada" |
| Manifesto cancelado | Opcao 024 ou [025](../operacional/025-saida-veiculos.md) → Manifesto → status = "Cancelado" |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-C01 | Emitir CTe fracionado — reemitir apos cancelamento |
| POP-C02 | Emitir CTe carga direta — reemitir apos cancelamento |
| POP-C03 | CT-e complementar — alternativa ao cancelamento |
| POP-C07 | Carta de correcao — alternativa para erros menores |
| POP-D03 | Manifesto/MDF-e — cancelar manifesto antes do CT-e |
| POP-G01 | Sequencia legal — NAO cancelar apos embarque |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |

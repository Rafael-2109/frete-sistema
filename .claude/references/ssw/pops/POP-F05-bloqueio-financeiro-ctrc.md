# POP-F05 — Registrar Bloqueio Financeiro de CTRC

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: [462](../financeiro/462-bloqueio-financeiro-ctrc.md), [435](../financeiro/435-pre-faturamento.md)
> **Executor atual**: Rafael (nao usa)
> **Executor futuro**: Rafael

---

## Objetivo

Registrar bloqueio financeiro de CTRCs para impedir faturamento ate resolucao de pendencia operacional ou comercial. CTRCs bloqueados NAO aparecem disponiveis para faturamento ([opcao 435](../financeiro/435-pre-faturamento.md)) e NAO sao incluidos no faturamento automatico ([opcao 436](../financeiro/436-faturamento-geral.md)) ou manual ([opcao 437](../financeiro/437-faturamento-manual.md)). Este POP protege contra cobranca indevida.

---

## Quando Executar (Trigger)

- CTRC com pendencia operacional (avaria, extravio, atraso severo)
- Cliente contesta valor do frete ANTES do faturamento
- CTRC com erro de emissao que impacta valor (peso, mercadoria, destino)
- Acordo comercial de nao cobrar temporariamente
- CTRC complementar pendente (aguardando emissao)
- Cliente solicita suspensao de cobranca ate resolucao de problema

---

## Frequencia

Por demanda — conforme necessidade operacional/comercial.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| CTRC emitido e autorizado | [007](../operacional/007-emissao-cte-complementar.md) | CTRC existe no SSW e foi autorizado pelo SEFAZ |
| CTRC nao faturado | [435](../financeiro/435-pre-faturamento.md) ou [437](../financeiro/437-faturamento-manual.md) | CTRC ainda nao incluido em fatura |
| Motivo do bloqueio | — | Justificativa clara (obrigatorio) |

> **ATENCAO**: Se CTRC ja foi faturado, NAO e possivel bloquear. Necessario retirar CTRC da fatura primeiro ([opcao 457](../financeiro/457-manutencao-faturas.md), POP-E06).

---

## Passo-a-Passo

### ETAPA 1 — Acessar Opcao 462

1. Acessar [opcao **462**](../financeiro/462-bloqueio-financeiro-ctrc.md) (Bloqueio Financeiro de CTRCs)
2. [CONFIRMAR: Verificar se e necessario estar em unidade especifica]

---

### ETAPA 2 — Identificar CTRC

3. Informar dados do CTRC a ser bloqueado:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Numero do CTRC** | Numero com serie | Ex: 123456 serie 1 |
| **[CONFIRMAR: Filial emissora]** | Sigla da filial | Ex: CAR |
| **[CONFIRMAR: Data emissao]** | Data de emissao | Se sistema solicitar |

4. Sistema exibe dados do CTRC:
   - Numero e serie
   - Data emissao
   - Cliente
   - Valor
   - Situacao atual

---

### ETAPA 3 — Registrar Bloqueio

5. Preencher dados do bloqueio:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **[CONFIRMAR: Tipo de bloqueio]** | [Opcoes do sistema] | Pode ter tipos pre-cadastrados |
| **Motivo** | Descricao clara | Obrigatorio — justificar bloqueio |
| **[CONFIRMAR: Data limite]** | Data prevista | Se bloqueio temporario |
| **[CONFIRMAR: Responsavel]** | Login | Quem bloqueou |

6. Exemplo de motivos:
   - "Avaria na entrega — aguardando acordo comercial"
   - "Cliente contesta valor — aguardando analise comercial"
   - "Erro de peso no CTe — aguardando CTe complementar"
   - "Acordo: nao cobrar ate resolucao de ocorrencia 12345"
   - "Extravio total — aguardando resolucao seguro"

7. Confirmar bloqueio
8. Sistema registra bloqueio

---

### ETAPA 4 — Verificar Bloqueio Ativo

9. Acessar [opcao **435**](../financeiro/435-pre-faturamento.md) (CTRCs Disponiveis para Faturamento)
10. Preencher filtros:
    - **Considerar bloq. financeiro**: S (para ver bloqueados)
11. Gerar relatorio
12. Verificar coluna **BLOQUEADO**:
    - CTRC bloqueado aparece marcado
    - Motivo do bloqueio visivel [CONFIRMAR]

> **REGRA**: CTRC bloqueado NAO sera incluido no faturamento automatico ([436](../financeiro/436-faturamento-geral.md)) mesmo se todas as outras condicoes forem atendidas.

---

### ETAPA 5 — Desbloquear CTRC (Quando Resolver)

**Quando usar**: Pendencia resolvida, CTRC pode ser faturado.

13. Acessar [opcao **462**](../financeiro/462-bloqueio-financeiro-ctrc.md)
14. Informar numero do CTRC bloqueado
15. Localizar bloqueio ativo [CONFIRMAR: como localizar]
16. Informar:
    - **Motivo do desbloqueio**: "Resolvido: cliente aceitou valor"
    - **Data resolucao**: Data atual
17. Confirmar desbloqueio
18. Sistema remove bloqueio

19. Verificar na [opcao 435](../financeiro/435-pre-faturamento.md):
    - CTRC agora aparece disponivel para faturamento
    - Coluna BLOQUEADO vazia

---

## Cenarios de Uso (CarVia)

### Cenario 1 — Avaria na Entrega

**Situacao**: Cliente MotoChefe recebeu carga com avaria. Aguardando acordo comercial sobre valor do frete.

**Acao**:
1. Registrar bloqueio do CTRC ([opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md))
2. Motivo: "Avaria na entrega CTRC 12345 — aguardando acordo comercial MotoChefe"
3. Comercial negocia com cliente
4. Acordo: desconto de 20% no frete
5. Lancar adicional de credito na fatura ([opcao 459](../financeiro/459-cadastro-tde.md))
6. Desbloquear CTRC ([opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md))
7. Faturar normalmente (com adicional de desconto)

---

### Cenario 2 — Erro de Peso no CTe

**Situacao**: CTe emitido com peso incorreto (digitado 1.000 kg, correto 1.500 kg). Valor cobrado a menor.

**Acao**:
1. Registrar bloqueio do CTRC original ([opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md))
2. Motivo: "Peso incorreto — aguardando CTe complementar"
3. Emitir CTe complementar ([opcao 007](../operacional/007-emissao-cte-complementar.md), POP-C03) com diferenca de peso
4. Desbloquear CTRC original ([opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md))
5. Faturar CTRC original + complementar juntos

---

### Cenario 3 — Cliente Contesta Valor

**Situacao**: Cliente NotCo contesta frete antes do faturamento. Alega que negociou preco diferente.

**Acao**:
1. Registrar bloqueio do CTRC ([opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md))
2. Motivo: "Cliente contesta valor — aguardando analise comercial"
3. Comercial verifica: preco esta correto conforme tabela
4. Comercial explica ao cliente
5. Cliente aceita
6. Desbloquear CTRC ([opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md))
7. Faturar normalmente

---

## Contexto CarVia

### Hoje

- Rafael NAO usa [opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md)
- Se houver pendencia: simplesmente nao fatura o CTRC
- Risco: esquecer de faturar depois
- SEM controle formal de bloqueios

### Futuro (com POP implantado)

- Bloqueio registrado formalmente na [opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md)
- Motivo documentado
- Relatorio de CTRCs bloqueados ([opcao 435](../financeiro/435-pre-faturamento.md))
- Alerta se bloqueio muito antigo (> 30 dias)
- Rastreabilidade: quem bloqueou, quando, por que

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| CTRC nao pode ser bloqueado | CTRC ja faturado | Retirar CTRC da fatura primeiro ([opcao 457](../financeiro/457-manutencao-faturas.md)) |
| CTRC nao encontrado | Numero/serie incorreto | Verificar na [opcao 007](../operacional/007-emissao-cte-complementar.md) ou 101 |
| Bloqueio nao impede faturamento | [CONFIRMAR: configuracao] | Verificar se bloqueio foi gravado corretamente |
| Desbloquear nao funciona | [CONFIRMAR: motivo] | Verificar se ha restricoes |
| CTRC bloqueado aparece em [435](../financeiro/435-pre-faturamento.md) | Filtro "Considerar bloq. financeiro = N" | Marcar S para ver bloqueados |

---

## Indicadores de Saude

| Indicador | Bom | Atencao | Critico |
|-----------|-----|---------|---------|
| CTRCs bloqueados (total) | 0-2 | 3-5 | 6+ |
| Bloqueios > 30 dias | 0 | 1 | 2+ |
| Bloqueios sem motivo claro | 0 | — | Qualquer |

**Acao se critico**: Revisar bloqueios semanalmente. Resolver ou documentar melhor.

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Bloqueio registrado | [Opcao 435](../financeiro/435-pre-faturamento.md) → filtro "Considerar bloq. financeiro = S" → CTRC aparece bloqueado |
| Motivo do bloqueio | [CONFIRMAR: onde visualizar motivo] |
| CTRC nao faturado | [Opcao 437](../financeiro/437-faturamento-manual.md) → CNPJ cliente → CTRC NAO aparece disponivel |
| Desbloqueio efetuado | [Opcao 435](../financeiro/435-pre-faturamento.md) → CTRC aparece sem bloqueio |
| Historico de bloqueios | [CONFIRMAR: se existe historico] |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-E01 | Pre-faturamento — identifica CTRCs bloqueados |
| POP-E02 | Faturamento manual — nao inclui bloqueados |
| POP-E03 | Faturamento automatico — nao inclui bloqueados |
| POP-E06 | Manutencao de faturas — retirar CTRC se ja faturado |
| POP-C03 | Emitir CTe complementar — cenario de bloqueio por erro |

---

## Notas Importantes

> **[CONFIRMAR]**: Este POP foi escrito SEM documentacao dedicada da [opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md). Informacoes sobre bloqueio aparecem de forma indireta na documentacao da [opcao 435](../financeiro/435-pre-faturamento.md) (pre-faturamento). Campos especificos da tela 462 estao marcados com [CONFIRMAR] e devem ser validados no ambiente SSW real.

Campos a confirmar no SSW:
1. Unidade necessaria para acessar [462](../financeiro/462-bloqueio-financeiro-ctrc.md)
2. Campos da tela de bloqueio (tipo, data limite, responsavel)
3. Como localizar bloqueio existente para desbloquear
4. Onde visualizar motivo do bloqueio na [opcao 435](../financeiro/435-pre-faturamento.md)
5. Se existe relatorio dedicado de CTRCs bloqueados
6. Se existe historico de bloqueios/desbloqueios

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) — com campos [CONFIRMAR] |

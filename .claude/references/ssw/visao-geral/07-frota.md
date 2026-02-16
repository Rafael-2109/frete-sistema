# 07 — Frota

> **Fonte**: `visao_geral_frota.htm` (02/11/2019)
> **Links internos**: 50 | **Imagens**: 1

## Sumario

Modulo de gestao de frota integrado ao operacional e contas a pagar. Funciona via Ordens de Servico (OS) pendentes que a equipe de frota deve resolver.

---

## Funcionalidades

| Funcionalidade | Objetivo | Trigger automatico |
|----------------|----------|-------------------|
| **Pneus** | Evitar extravio, acompanhar durabilidade | Quilometragem da operacao |
| **Manutencoes** | Lembrar preventivas e registrar corretivas | Quilometragem ou data |
| **Consumo de Combustivel** | Evitar perdas por desvio/problema mecanico | Lancamento no Contas a Pagar |
| **Ordens de Servico** | Agenda da equipe Frotas | Todos os itens acima |

---

## Arquitetura

Tudo gira em torno de **Ordens de Servico Pendentes** ([opção 131](../relatorios/131-ordens-servico.md)):

```
OPERAÇÃO (quilometragem)  →  ┐
CONTAS A PAGAR (consumo)  →  │→  ORDENS DE SERVIÇO (131)
VENCIMENTOS (IPVA, etc.)  →  │      ↓
OS AVULSAS (qualquer user) → ┘   EQUIPE FROTAS resolve
```

### Fontes de OS automaticas
1. **Consumo fora da media** — media < minimo ou > maximo cadastrado no veiculo ([opção 026](../relatorios/026-cadastro-veiculos.md))
2. **Manutencao preventiva** — quilometragem atinge limite de check-list/plano
3. **Pendencias veiculo/motorista** — vencimento IPVA, seguro, tacografo diariamente
4. **OS avulsas** — qualquer usuario autorizado (ex: portaria identifica lampada queimada)

---

## 1. Consumo de Combustivel

### Fontes de dados
| Opcao | Fonte | Calcula media |
|-------|-------|---------------|
| [475](../financeiro/475-contas-a-pagar.md) | Programacao de despesas (evento tipo INFORMA CONSUMO, [opção 503](../fiscal/503-manutencao-de-eventos.md)) | Sim |
| [320](../relatorios/320-abastecimento-interno.md) | Abastecimento por bomba interna | Sim |

- Medias min/max cadastradas no veiculo ([opção 026](../relatorios/026-cadastro-veiculos.md))
- Fora dos limites → OS automatica ([opção 131](../relatorios/131-ordens-servico.md))

### Consultas
| Opcao | Funcao |
|-------|--------|
| 322 | Relatorio de consumo no mes (todos abastecimentos + medias) |
| 576 | Informar consumo complementar (abastecimentos fora [opção 475](../financeiro/475-contas-a-pagar.md)) |

---

## 2. Manutencoes

### Configuracao
| Opcao | Funcao |
|-------|--------|
| [314](../relatorios/314-check-list-manutencao.md) | Cadastro de check-list (baseado no manual do fabricante) |
| 315 | Vinculacao check-list → veiculo (por placa) |
| [614](../edi/614-cadastro-planos-manutencao.md) | Planos de manutencao (atividades com agendamento km/data) |
| 615 | Vinculacao plano → veiculo |

### Funcionamento
- Quilometragem atualizada automaticamente pela operacao (API Google)
- Quilometragem consultavel (opção 328)
- OS geradas automaticamente conforme check-list e planos ([opção 131](../relatorios/131-ordens-servico.md), opção 319)
- Realizar manutencao na [opção 131](../relatorios/131-ordens-servico.md) → gera automaticamente OS futura

---

## 3. Pneus

### Processo
1. **Numerar** todo pneu (numeradores eletricos)
2. **Cadastrar** (opção 313) — dados, localizacao, quilometragem, ocorrencias
3. **Movimentar** ([opção 316](../relatorios/316-movimentacao-pneus.md)) — troca de posicao, retirada para conserto/reforma/almoxarifado

### Atualizacao automatica
- Operacao do veiculo ([opção 025](../operacional/025-saida-veiculos.md), [030](../operacional/030-chegada-de-veiculo.md), [035](../operacional/035-romaneio-entregas.md)) → pneus nas posicoes recebem quilometragem

### Consultas
| Opcao | Funcao |
|-------|--------|
| [026](../relatorios/026-cadastro-veiculos.md) (rodape) | Pneus do veiculo nas posicoes |
| 317 | Vida do pneu (historico completo desde aquisicao) |
| 318 | Pneus em estoque (almoxarifados) |
| [120](../operacional/120-chegada-veiculo-sem-manifesto.md) | Autorizacao entrada/saida — lista pneus por posicao (conferencia portaria) |

---

## 4. Ordens de Servico

Agenda da equipe ([opção 131](../relatorios/131-ordens-servico.md), relatorio opção 319):
- Manutencoes preventivas (quilometragem)
- Consumo fora da media (lancamento despesa [opção 475](../financeiro/475-contas-a-pagar.md))
- Corretivas manuais ([opção 131](../relatorios/131-ordens-servico.md))
- Vencimentos (seguro, IPVA, tacografo — [opção 026](../relatorios/026-cadastro-veiculos.md))

> Todas as OS ficam pendentes ate que a equipe tome providencias.

---

## 5. Implantacao

1. Cadastrar tipos de veiculos ([opção 097](../operacional/097-controle.md)) — define se tem motor, odometro, controle SSWFrota
2. Cadastrar todos os veiculos + carretas ([opção 026](../relatorios/026-cadastro-veiculos.md)) com quilometragem/odometro
3. Cadastrar todos os pneus (opção 313)
4. Solicitar liberacao ao Suporte SSW

---

## Contexto CarVia

### Opcoes que CarVia usa
*Nenhuma — CarVia tem 2 caminhoes mas nao controla frota no SSW.*

### Opcoes que CarVia NAO usa (mas deveria)
| Opcao | Funcao | Impacto |
|-------|--------|---------|
| [026](../relatorios/026-cadastro-veiculos.md) | Cadastro de veiculos (medias consumo, quilometragem, vencimentos) | Sem cadastro, impossivel gerar OS automaticas ou controlar consumo |
| 320 | Abastecimento interno (bomba propria) | Sem registro de abastecimento, impossivel calcular media de consumo |
| [131](../relatorios/131-ordens-servico.md) | Ordens de Servico pendentes (agenda da equipe Frotas) | Sem OS, manutencoes preventivas passam despercebidas |
| [475](../financeiro/475-contas-a-pagar.md) | Contas a Pagar (evento INFORMA CONSUMO) | Sem integracao, consumo nao alimenta medias automaticas |

### Status de Implantacao
- **G03**: NAO IMPLANTADO — modulo de frota inteiro sem uso

### Responsaveis
- **Atual**: Ninguem (modulo nao implantado)
- **Futuro**: Rafael (plano de implantacao de controle de frota)

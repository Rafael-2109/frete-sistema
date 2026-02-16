# Opção 131 — Ordens de Serviço e Providências do Veículo

> **Módulo**: Frota
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Registra Ocorrências e Ordens de Serviço do veículo e gerencia providências tomadas. Permite atualização do odômetro e agendamento futuro de check-lists e planos de manutenção.

## Quando Usar
- Registrar Ordem de Serviço (exige providências)
- Registrar Ocorrência simples (não exige providências)
- Informar providências tomadas para OSs pendentes
- Atualizar odômetro do veículo
- Consultar histórico de OSs e ocorrências do veículo

## Pré-requisitos
- Módulo Frota ativado pelo SSW
- Veículo cadastrado
- Para OSs automáticas: processos operacionais ou Contas a Pagar configurados
- Para check-lists: opção 314 (cadastro) e opção 315 (vinculação)
- Para planos de manutenção: opção 615

## Processo

```
Processos operacionais/Contas a Pagar
         ↓
  Gravam OSs automaticamente
         ↓
    Opção 131 - Registra providências
         ↓
  Agendamento futuro (check-list/Plano Manutenção)
```

### Ordens de Serviço vs Ocorrências
- **Ordem de Serviço**: exige providências
- **Ocorrência**: não exige providências (apenas registro)

### Relação de OSs Pendentes
- Opção 319 - Lista OSs aguardando providências

## Campos / Interface

### Tela Inicial

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Incluir** | | |
| Ordem de serviço placa | Não | Grava nova OS (exige providências) |
| Ocorrência placa | Não | Grava nova Ocorrência (não exige providências) |
| **Listar cadastradas** | | |
| Ordem de Serviço | Não | Consulta OS por número, registra providência, atualiza odômetro |
| Período de agendamento | Não | Seleciona OSs por data de agendamento (pode ser futura) |
| Odômetro atual adicionar | Não | Seleciona OSs agendadas por km (odômetro atual + km informada) |

### Tela Principal

#### Parte Superior
| Botão | Função |
|-------|--------|
| **Incluir ocorrência** | Grava nova ocorrência (não exige providências) |
| **Incluir Ordem de Serviço** | Grava nova OS (exige providências) |
| **Imprimir** | Abre opção 319 (relatórios de gestão de OSs) |

#### Lista de OSs/Ocorrências
| Coluna | Descrição |
|--------|-----------|
| **Filial** | Sigla da unidade do usuário que incluiu |
| **Placa** | Placa do veículo |
| **OS** | Número da OS (vazio para Ocorrência) |
| **Data prevista** | Data de agendamento |
| **Km prevista** | Quilometragem de agendamento |
| **Alterar** | Altera data ou km de agendamento |
| **Descrição** | Descrição da OS ou Ocorrência |
| **Inclusão** | Data de inclusão |
| **Usuário** | Usuário de inclusão |
| **Providência** | Descrição da providência tomada. "PENDENTE" indica que ainda não foi registrada |

### Registro de Providências
Ao clicar sobre a linha de uma OS:

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Odômetro atual** | Sim | Atualiza odômetro do veículo com quilometragem real (opção 026) |
| **Providências** | Sim | Descrição das providências tomadas para resolver a OS |

## Fluxo de Uso

### Incluir Nova OS/Ocorrência
1. Acesse opção 131
2. Clique em "Ordem de serviço placa" (exige providências) ou "Ocorrência placa" (não exige)
3. Informe placa do veículo
4. Preencha descrição e agendamento (data ou km)
5. Confirme

### Consultar e Dar Providência
1. Acesse opção 131
2. Informe número da OS ou use filtros (período/odômetro)
3. Clique sobre a linha da OS pendente
4. Informe odômetro atual (buscar no veículo)
5. Descreva as providências tomadas
6. Confirme

### Gerar Relatórios
1. Na tela principal, clique em "Imprimir"
2. Sistema abre opção 319 (relatórios de gestão)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 026 | Odômetro do veículo |
| 314 | Cadastro de Check-lists |
| 315 | Vinculação Check-list a veículos |
| 317 | Vida do pneu (usa odômetro) |
| 319 | Relatórios de OSs e providências |
| 615 | Planos de Manutenção |

## Observações e Gotchas

### Odômetro do Veículo
- Atualizado **automaticamente** por operações (saídas/chegadas de Manifestos via API Google)
- Atualizado **manualmente** ao informar providências nesta opção 131

### Agendamento de Próximas OSs
- Ao confirmar providência, check-lists (opção 315) ou Planos de Manutenção (opção 615) são agendados automaticamente
- Agendamento futuro por **data** ou **quilometragem**

### Primeiro Agendamento
- Check-list: ocorre na vinculação ao veículo (opção 315)
- Planos de Manutenção: conforme configuração (opção 615)

### OSs Automáticas
- Processos operacionais gravam OSs automaticamente
- Contas a Pagar grava OSs automaticamente
- Veja detalhes em documentação específica do módulo Frota

### Relação Veículos x Check-list
- Opção 045 - Lista veículos e seus check-lists vinculados

### Filtros de Seleção
- **Período de agendamento**: por data (inclusive futuras)
- **Odômetro atual adicionar**: por quilometragem (odômetro atual + km informada)

### Status PENDENTE
- Texto "PENDENTE" na coluna Providência indica que providência ainda não foi registrada
- Apenas OSs (não Ocorrências) exigem providências

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A08](../pops/POP-A08-cadastrar-veiculo.md) | Cadastrar veiculo |
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |

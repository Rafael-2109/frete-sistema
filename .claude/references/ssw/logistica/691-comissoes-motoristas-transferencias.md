# Opção 691 — Comissões de Motoristas de Transferências

> **Módulo**: Logística
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Configura o cálculo de comissão de motorista de transferência da Frota.

## Quando Usar
- Para cadastrar parâmetros de comissionamento por motorista da Frota
- Para definir bases de cálculo e percentuais de comissão
- Para configurar débitos automáticos de despesas

## Pré-requisitos
- Motorista cadastrado no sistema
- Configuração de eventos de despesa (opção 503) para débito de comissão

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Comissão (%) | Sim | Percentual aplicado sobre base de cálculo (para crédito) e sobre despesas (para débito) |
| Base de cálculo | Sim | Manifesto ou CTRB |
| Debitar despesas | Sim | S habilita débito (opção 578 e bomba interna opção 320) |
| Diária | Não | Valor da diária em R$ (horas totais ÷ 24h) |
| Por Km | Não | Valor por Km em R$ (usa distância da rota do CTRB) |

### Base de Cálculo - Manifesto
Pode ser definida de duas formas:
- **Base de cálculo**: Parcelas dos fretes dos CTRCs (Frete Peso, Frete Valor, Pedágio, Outros, abate ou não ICMS)
- **OU Frete Proporcional**: Parte do frete do CTRC correspondente ao percurso de transferência (FRTPROP no Manifesto)

### Base de Cálculo - CTRB
- **Frete**: Com S, comissão paga sobre valor do CTRB (receita para frota)

## Fluxo de Uso

### Cadastro de Comissão
1. Acessar opção 691
2. Selecionar motorista
3. Definir percentual de comissão
4. Escolher base de cálculo (Manifesto ou CTRB)
5. Configurar débito de despesas (S/N)
6. Opcionalmente, definir diária e valor por Km
7. Confirmar cadastro

### Apuração da Comissão
- **Créditos**: Lançados automaticamente na chegada do veículo (opção 030)
- **Débitos**: Lançados no momento do repasse da despesa (opção 578) ou abastecimento (opção 320)
- **Saldo**: Visualizado na Conta Corrente do Fornecedor (CCF, opção 486)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 030 | Chegada do veículo - lança crédito de comissão automaticamente |
| 486 | Conta Corrente do Fornecedor - apuração da comissão |
| 503 | Cadastro de eventos de despesa com débito de comissão |
| 578 | Debitar comissão do motorista (despesas) |
| 320 | Abastecimento na bomba interna - débito de comissão |

## Observações e Gotchas

### Lançamentos na CCF (opção 486)
**Créditos**:
- Lançados automaticamente na chegada do Manifesto ou CTRB (opção 030)
- Aplicado percentual da comissão sobre base de cálculo configurada

**Débitos**:
- Ocorrem no momento do repasse da despesa (opção 578) ou abastecimento (opção 320)
- Aplicado **mesmo percentual da comissão de crédito**
- Objetivo: Incentivar motorista a reduzir despesas

**Outros créditos adicionais**:
- **Diária**: Quantidade de horas totais ÷ 24h × valor da diária
- **Por Km**: Quilometragem da distância na rota do CTRB × valor por Km
- **Chegada forçada**: Não credita comissão por Km

### Débito de Despesas
Para debitar, o motorista (opção 691) deve estar configurado como "desconta despesa".

Despesas debitadas:
- Despesas lançadas pela opção 578 com evento (opção 503) configurado como "DEBITA COMISSÃO DE MOTORISTA"
- Abastecimentos na bomba interna (opção 320)

### Saldo e Acerto
- **Saldo da CCF**: Comissão a ser paga ao motorista (opção 486)
- **Acerto**: Envia saldo ao Contas a Pagar (opção 475)

### Critérios Importantes
- **Lançamento único no mês**: Parcela já lançada não será lançada novamente
- **Base CTRB - chegada forçada**: Na emissão de outro CTRB antes do destino, não credita comissão por Km
- **Frete Proporcional (FRTPROP)**: Parte do frete correspondente ao percurso de transferência em relação à distância total

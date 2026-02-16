# Opção 403 — Cadastro de Rotas

> **Módulo**: Cadastros
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Define rotas de transferência entre unidades, incluindo prazo de transferência, hora de corte e quantidade de pedágios. As rotas são utilizadas no cálculo de previsão de entrega e no planejamento operacional.

## Quando Usar
- Cadastrar novas rotas de transferência entre unidades
- Definir prazos de transferência entre filiais
- Configurar hora de corte para chegada de veículos
- Informar quantidade de pedágios no trajeto entre unidades
- Configurar comissionamento específico por rota (via opção 408)

## Pré-requisitos
- Opção 401: Cadastro de unidades (origem e destino da rota devem existir)

## Campos / Interface

A opção 403 é utilizada de forma indireta. A documentação consolidada mostra que os principais campos são:

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Unidade Origem | Sim | Unidade de origem da rota |
| Unidade Destino | Sim | Unidade de destino da rota |
| Prazo de Transferência | Sim | Tempo em dias úteis para transferência entre as unidades |
| Hora de Corte | Não | Hora limite para chegada do manifesto na unidade destino |
| Quantidade de Pedágios | Não | Número de postos de pedágio no trajeto |

## Fluxo de Uso

### Cadastrar Nova Rota
1. Acessar opção 403
2. Informar unidade de origem
3. Informar unidade de destino
4. Definir prazo de transferência (dias úteis)
5. Configurar hora de corte (se aplicável)
6. Informar quantidade de pedágios
7. Salvar rota

### Uso no Cálculo de Previsão de Entrega
- Prazo total = Prazo de transferência (rota) + Prazo de entrega (cidade destino)
- Feriados municipais, estaduais e federais são considerados após contagem do prazo de transferência

### Configurar Comissionamento por Rota
- Usar opção 408 para definir comissão específica por rota
- Comissão por rota tem prioridade sobre comissão geral da unidade

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 030 | Chegada de veículos (valida hora de corte da rota) |
| 060 | Feriados estaduais (considerados no cálculo de prazo após transferência) |
| 401 | Cadastro de unidades (define unidades origem/destino das rotas) |
| 402 | Cidades atendidas (quantidade de pedágios da cidade + rota) |
| 408 | Comissionamento por rota (prioridade sobre comissão geral) |
| 409 | Remuneração de veículos de coleta/entrega |

## Observações e Gotchas

### Prazo de Transferência
- Contado em dias úteis
- Feriados são considerados APÓS a contagem do prazo de transferência, no destino
- Veja documentação detalhada sobre cálculo de previsão de entrega (referenciada nas ajudas)

### Hora de Corte
- Define horário limite para chegada do manifesto na unidade destino
- Manifestos que chegam após hora de corte são identificados como ATRASADO na opção 030
- Se unidade destino tiver operação FEC (fechada), chegada é identificada como FECHADA

### Quantidade de Pedágios
- Usada em tabelas de frete para cálculo de valor de pedágio
- Pode ser complementada com pedágios da cidade (opção 402)
- Total de pedágios = pedágios da rota + pedágios da cidade

### Unidades Alternativas
- Rotas devem ser cadastradas para todas as unidades alternativas (opção 395)
- Opção 395 permite trocar unidade automaticamente, mas a rota deve existir

### Comissionamento
- Comissão específica por rota (opção 408) tem prioridade sobre comissão geral
- Permite diferenciar remuneração por dificuldade ou distância da rota

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A02](../pops/POP-A02-cadastrar-unidade-parceira.md) | Cadastrar unidade parceira |
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
| [POP-A06](../pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos comissoes |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-A10](../pops/POP-A10-implantar-nova-rota.md) | Implantar nova rota |
| [POP-B01](../pops/POP-B01-cotar-frete.md) | Cotar frete |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-G02](../pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist gerenciadora risco |

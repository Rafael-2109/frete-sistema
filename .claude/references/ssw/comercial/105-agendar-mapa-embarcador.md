# Opção 105 — Agendar Processamento Mapa do Embarcador

> **Módulo**: Comercial/Financeiro
> **Referência interna**: Opção 963
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Agendar o processamento do Mapa do Embarcador, que relaciona os CTRCs a pagar para transportadoras contratadas. O sistema processa automaticamente os fretes e deduz valores de mercadorias com ocorrências que indicam perdas.

## Quando Usar

- Configurar dias mensais para processamento automático de fretes a pagar
- Definir período retroativo para considerar ocorrências de entregas
- Configurar códigos de ocorrências que autorizam pagamento ou débito de mercadorias
- Gerar mapas para envio ao Contas a Pagar

## Campos / Interface

### Configurações de Agendamento

- **Agendar para**: Até 5 dias do mês para processamento (executado nas primeiras horas do dia)
- **Retroagindo**: Quantos dias antes da data de processamento devem ser consideradas as ocorrências

### Códigos de Ocorrências

- **Pagar frete**: Até 5 códigos de ocorrências (conforme tabela da opção 405) que autorizam pagamento do frete à transportadora
- **Debitar valor mercadoria**: Códigos que debitam o valor da mercadoria à transportadora via Mapa

## Integração com Outras Opções

- **Opção 105 (CEE)**: Cadastro de transportadoras contratadas via CEE
- **Opção 405**: Tabela de códigos de ocorrências do embarcador (informadas on-line pelas transportadoras)
- **Opção 056**: Consulta de mapas processados (disponível nas unidades que emitiram CEE e na MTZ-matriz)
- **Contas a Pagar**: Recebe o mapa processado para efetuar pagamentos

## Observações e Gotchas

### Exemplo de Configuração

Para considerar ocorrências do mês anterior completo:
- **Agendar para**: 10
- **Retroagindo**: 10 dias

Isso resolve a situação em que os meses possuem quantidade de dias diferentes.

### Conversão de Códigos

A conversão do código da transportadora para o código da embarcadora é efetuada automaticamente pelo sistema.

### Prazo de Retroação

Dar um prazo adequado de retroação é necessário para que ocorrências que debitam mercadoria tenham tempo de ser resolvidas pela transportadora antes do processamento.

### Disponibilidade do Mapa

O mapa processado fica disponível no dia do processamento na opção 056, tanto nas unidades que emitiram o CEE quanto na unidade MTZ-matriz.

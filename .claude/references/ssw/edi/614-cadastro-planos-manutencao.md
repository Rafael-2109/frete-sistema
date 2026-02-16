# Opção 614 — Cadastro de Planos de Manutenção

> **Módulo**: EDI
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Cadastro de Plano de Manutenção com agendamento individual dos itens para veículos da frota.

## Quando Usar
- Para cadastrar planos de manutenção preventiva de veículos
- Para criar agendamentos individuais de atividades de manutenção
- Antes de vincular plano a um veículo (opção 615)

## Pré-requisitos
- Nenhum pré-requisito específico

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Descrição | Sim | Identifica plano com nome do veículo ou tipo a que se destina |
| Item | Sim | Atividade numerada de 1 a 20 |
| Descrição (item) | Sim | Descrição da atividade de manutenção a ser executada |
| Dias | Condicional | Quantidade de dias até a próxima execução do item (ou Km) |
| Km | Condicional | OU quantidade de Km até a próxima execução do item (ou Dias) |

## Fluxo de Uso
1. Clicar em "Novo Plano" (numeração automática)
2. Informar descrição do plano
3. Cadastrar atividades de manutenção (até 20 itens)
4. Para cada item, informar:
   - Descrição da atividade
   - Agendamento por Dias OU Km
5. Confirmar cadastro
6. Vincular plano ao veículo pela opção 615
7. Ordem de Serviço será gerada para cada item do plano
8. Atendimento de cada ordem informado pela opção 131

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 615 | Vincula Plano de Manutenção ao veículo |
| 131 | Informar atendimento/conclusão da Ordem de Serviço |
| 045 | Relação de veículos e planos vinculados |

## Observações e Gotchas
- **Numeração automática**: Sistema gera número do plano automaticamente
- **Até 20 itens**: Cada plano pode ter até 20 atividades de manutenção
- **Agendamento individual**: Cada item tem seu próprio agendamento (dias OU km)
- **Duplicar**: Link permite duplicar plano com nova numeração
- **Excluir**: Link permite excluir plano completo
- **Geração de OS**: Sistema gera Ordem de Serviço para cada item do plano
- **Primeiro agendamento**: Ocorre já na vinculação do plano ao veículo (opção 615)
- **Próximo agendamento**: Gerado quando se informa conclusão do serviço na opção 131

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |

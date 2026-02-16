# Opção 813 — Avaliação da Equipe SSW

> **Módulo**: Embarcador (Interno SSW)
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Permite que mensalmente toda a equipe SSW avalie todos os membros da equipe, subsidiando premiação mensal e PLR.

## Quando Usar
- Mensalmente, até o dia 20 do mês
- Para avaliar membros da equipe com quem se teve relacionamento no mês anterior
- Para subsidiar cálculo de prêmio mensal e PLR (Participação nos Lucros e Resultados)

## Pré-requisitos
- Código de acesso enviado por e-mail (sigiloso)
- Ser membro da equipe SSW

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Código para voltar | Sim | Enviado por e-mail, sigiloso, usado para votar todos os meses |
| Notas (1 a 10) | Condicional | Para cada membro com quem teve relacionamento no mês |

## Fluxo de Uso
1. Receber código sigiloso por e-mail
2. Acessar opção 813 até o dia 20 do mês
3. Para cada membro da equipe com quem teve relacionamento:
   - Atribuir nota de 1 a 10 conforme afirmação: "Ele ajuda a mim e ao SSW a atingir os objetivos"
4. Confirmar avaliações
5. Notas podem ser alteradas livremente até o dia 20 do mês

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 056 (Relatório 255) | PLR SSW - usa notas para cálculo de premiação mensal e PLR anual |
| 811 | Fila de Solicitações - relacionado com avaliação de trabalho |

## Observações e Gotchas

### Critério de Avaliação
**Afirmação base**: "Ele ajuda a mim e ao SSW a atingir os objetivos"
- **Nota 10**: Membro ajuda muito tanto a mim como o SSW a atingir objetivos
- **Nota ZERO**: Não pode ser utilizada (reconhecida como sem nota)
- **Sem relacionamento**: Não atribuir nota

### Regras Importantes
- **Alteração livre**: Nota pode ser alterada até o dia 20 do mês
- **Código sigiloso**: Enviado por e-mail para cada membro
- **Prazo**: Até dia 20 do mês (dados encaminhados para FOLHA após esse dia)
- **Relatório**: Disponível com média das notas atribuídas por todos
- **Impressão limitada**: Relatório imprime apenas 1/3 das maiores médias
- **Menor nota excluída**: A menor nota é excluída do cálculo da média
- **Apenas 5 maiores**: São impressas as 5 maiores médias
- **Versão completa**: Disponível para a Folha com todas as médias

### Objetivo
Tornar as avaliações do trabalho em homeworking mais precisas e justas, subsidiando:
- **Prêmio mensal**: 1% das liquidações menos impostos, dividido proporcionalmente às notas
- **PLR anual**: Meio salário base aplicando-se notas obtidas ao longo do ano

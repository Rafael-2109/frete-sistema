# Opção 559 — Saldo das Contas / Fechamento Contábil

> **Módulo**: Contabilidade
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Calcula saldos finais das contas contábeis, permite informar saldos provisórios e controla o fechamento/abertura de períodos contábeis. O fechamento impede novos lançamentos no período.

## Quando Usar
- Mensalmente, após conclusão de todos os lançamentos do período
- Início do uso da Contabilidade no SSW (informar saldos iniciais)
- Migração de outro sistema contábil (transferência de saldos)
- Necessidade de bloquear/desbloquear período para lançamentos

## Pré-requisitos
- Plano de Contas configurado (opção 540)
- Lançamentos do período finalizados
- Mês anterior fechado (para calcular saldos do mês atual)

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Mês | Sim | Mês/ano de referência (formato MM/AAAA) |
| Situação | Auto | Aberto ou Fechado (exibido pelo sistema) |

## Fluxo de Uso

### Cálculo de Saldos Mensal
1. Acessar opção 559
2. Informar mês/ano para cálculo
3. Verificar se mês anterior está fechado
4. Clicar em "CALCULAR SALDOS"
5. Sistema processa todos os lançamentos do mês
6. Clicar em "VER SALDOS" para conferir saldos finais
7. Clicar em "FECHAR/ABRIR" para fechar período

### Informar Saldo Inicial (Migração)
1. Acessar opção 559
2. Informar primeiro mês de uso no SSW
3. Clicar em "INFORMAR SALDO"
4. Para cada conta:
   - Informar código da conta no SSW
   - Informar complemento (se aplicável)
   - Informar saldo final do sistema anterior
   - **Conta sistema anterior**: Informar código da conta no sistema antigo (para transferência no SPED ECD)
5. Salvar saldos informados
6. Mês seguinte utilizará estes saldos como saldo inicial

### Reabertura de Período
1. Acessar opção 559
2. Informar mês/ano a ser reaberto
3. Clicar em "FECHAR/ABRIR"
4. Sistema reabria período e remove saldos dos meses seguintes
5. Realizar ajustes necessários
6. Recalcular saldos e fechar novamente

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 540 | Plano de Contas — estrutura de contas para cálculo de saldos |
| 558 | Lançamentos Manuais — período deve estar aberto para lançar |
| 541 | Lançamentos Automáticos — período deve estar aberto para processar |
| 534 | ECD — transferência de saldos via registros I200 e I250 quando informado "conta sistema anterior" |
| 548 | Livro Razão — exibe saldos calculados por esta opção |
| 561 | Balanço Patrimonial — utiliza saldos calculados |
| 562 | DRE — utiliza saldos calculados |

## Observações e Gotchas
- **Cálculo manual obrigatório**: Saldos NÃO são calculados automaticamente; deve-se acionar manualmente por esta opção
- **Dependência do mês anterior**: Só é possível calcular saldos se mês anterior estiver fechado
- **Reabertura remove saldos futuros**: Ao abrir um mês, saldos de todos os meses seguintes são removidos e devem ser recalculados
- **Saldo final = saldo anterior + lançamentos**: Saldo final do mês = saldo final do mês anterior + todos os lançamentos do mês
- **Fechamento bloqueia lançamentos**: Mês fechado não permite novos lançamentos ou alterações
- **Não é possível fechar sem calcular**: Sistema exige cálculo de saldos antes de permitir fechamento
- **Transferência SPED ECD**: Ao informar "conta sistema anterior" na tela de Informar Saldo, o saldo é transferido via registros I200 e I250 no arquivo ECD (opção 534)
- **Saldos provisórios**: Saldos informados manualmente são provisórios e servem para permitir cálculo do mês seguinte quando mês anterior não está fechado no sistema anterior
- **Cálculo por conta**: Sistema calcula saldo de todas as contas do Plano de Contas, respeitando natureza (débito/crédito)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |

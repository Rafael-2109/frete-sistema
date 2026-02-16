# Opção 540 — Plano de Contas

> **Módulo**: Contabilidade
> **Páginas de ajuda**: 1 página consolidada (nota: arquivo lido era opção 543)
> **Atualizado em**: 2026-02-14

## Função
Cadastra e gerencia o Plano de Contas Contábil, definindo a estrutura de contas utilizadas nos lançamentos contábeis, relatórios e arquivos fiscais (ECD, ECF).

## Quando Usar
- Início do uso do módulo de Contabilidade no SSW
- Criação ou alteração da estrutura de contas contábeis
- Configuração de complementos de contas (banco, unidade, CNPJ, cidade, etc.)
- Mapeamento para geração de SPED ECD e ECF

## Pré-requisitos
- Conhecimento da estrutura contábil da empresa
- Definição do regime de tributação (Lucro Real ou Lucro Presumido)

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Código da Conta | Sim | Código estruturado em até 4 níveis (hierarquia) |
| Descrição | Sim | Nome/descrição da conta contábil |
| Tipo de Complemento | Condicional | CNPJ, unidade, banco, cidade, inscrição municipal/estadual, etc. |
| Natureza | Sim | Débito ou Crédito (comportamento natural da conta) |

## Fluxo de Uso
1. Acessar opção 540
2. Definir estrutura hierárquica de contas (1º ao 4º nível)
3. Cadastrar contas sintéticas (totalizadoras) e analíticas (recebem lançamentos)
4. Configurar tipo de complemento para contas que necessitam detalhamento
5. Validar estrutura para SPED ECD (opção 534) e ECF (opção 570)

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 543 | Consulta de Lançamentos — exibe código completo da conta (tabelada + complemento) |
| 558 | Lançamentos Manuais — utiliza contas do Plano para registro de débitos/créditos |
| 559 | Saldo das Contas — calcula saldos finais com base no Plano de Contas |
| 534 | ECD — estrutura utilizada na geração dos livros digitais |
| 570 | ECF — estrutura utilizada na geração da Escrituração Fiscal |
| 541 | Lançamentos Automáticos — mapeamento de contas para lançamentos automáticos |

## Observações e Gotchas
- **Código completo da conta**: Formado pela parte tabelada (Plano de Contas) + complemento (CNPJ, unidade, banco, etc.)
- **Complemento banco**: Tamanho deve ser de 18 dígitos: 3 para banco, 5 para agência, 10 para conta corrente
- **Hierarquia de níveis**: Contas sintéticas totalizam contas analíticas subordinadas
- **Contas analíticas**: Apenas contas analíticas (último nível) recebem lançamentos
- **Transferência de saldos**: Ao migrar de outro sistema, informar conta do sistema anterior na opção 559/Informar Saldo para transferência via registros I200 e I250 do SPED ECD
- **Sem pontos ou espaços**: Código da conta deve ser informado sem pontos ou espaços nos lançamentos via CSV (opção 558)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-F01](../pops/POP-F01-contas-a-pagar.md) | Contas a pagar |
| [POP-F04](../pops/POP-F04-conciliacao-bancaria.md) | Conciliacao bancaria |

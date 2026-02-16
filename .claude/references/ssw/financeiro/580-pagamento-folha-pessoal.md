# Opção 580 — Pagamento da Folha de Pessoal

> **Módulo**: Financeiro/Contas a Pagar
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função
Efetuar controle e lançamento de pagamentos de salários no Contas a Pagar através de importação de arquivo CSV, mantendo sigilo e automatizando o processo de pagamento via arquivo bancário.

## Quando Usar
Quando for necessário:
- Processar folha de pagamento de funcionários de forma automatizada
- Manter sigilo dos dados de salários (sistema gera 1 lançamento total por evento, não individualizado)
- Preparar arquivo de pagamento para envio ao banco (opção 522)
- Gerar relatórios de folha por período, unidade ou funcionário

## Pré-requisitos
- Funcionários cadastrados como fornecedores (opção 478) com campo "Tipo de Operação" preenchido (código do banco para FOLHA DE PAGAMENTO)
- Filial pagadora cadastrada como fornecedor (opção 478)
- Arquivo CSV com relação de funcionários e valores
- Se usar pagamento via arquivo bancário: produto FOLHA DE PAGAMENTO contratado com banco

## Campos / Interface

### Tela Inicial — Menu de Funções

| Função | Descrição |
|--------|-----------|
| Importação da FOLHA DE PESSOAL | Importar arquivo CSV com dados dos salários |
| Manutenção da FOLHA | Inclusão, alteração e exclusão de registros |
| Relatório | Gerar relatório por período, unidade e funcionários |
| Liberação para C Pagar | Efetuar lançamento de despesa (opção 475) com base no arquivo importado |
| Cadastro de funcionário | Acessar opção 478 para cadastrar funcionário como fornecedor |

### Tela — Importação da Folha de Pessoal

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Folha mês/ano | Sim | Mês de referência da Folha sendo importada |
| Sigla unidade | Não | Unidade pagadora — se omitida, usa do arquivo (coluna C) |
| Evento | Não | Evento a ser atribuído na despesa (opção 475) — sobrepõe arquivo (coluna D) |
| Arquivo CSV | Sim | Layout: Coluna A (CPF funcionário), B (valor salário), C (sigla unidade opcional), D (código evento opcional) — **SEM linha de cabeçalho** |

### Tela — Liberação para Contas a Pagar

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Mês/ano | Sim | Mês de referência para **seleção** dos salários a serem liberados |
| Data de pagamento | Sim | Data de pagamento atribuída à despesa (opção 475) |
| Competência mês/ano | Sim | Data de competência atribuída à despesa (opção 475) |
| Data de entrada | Sim | Data de entrada atribuída à despesa (opção 475) |

## Fluxo de Uso

### Preparação (executar uma vez)
1. Cadastrar funcionários como fornecedores (opção 478):
   - Informar CPF, dados bancários (Banco/Agência/Conta, tipo de conta)
   - Informar Chave PIX e Tipo chave PIX (se aplicável)
   - **IMPORTANTE**: Preencher campo "Tipo de Operação" com código do banco para FOLHA DE PAGAMENTO (se usar opção 522)
2. Cadastrar filial pagadora como fornecedor (opção 478)
3. Preparar arquivo CSV no formato especificado

### Processamento mensal
4. Acessar opção 580
5. Clicar em "Importação da FOLHA DE PESSOAL"
6. Informar mês/ano de referência
7. Informar sigla unidade e evento (se deseja sobrepor arquivo)
8. Selecionar arquivo CSV
9. Importar
10. **Opcional**: Acessar "Manutenção da FOLHA" para ajustes manuais
11. **Opcional**: Gerar "Relatório" para conferência
12. Clicar em "Liberação para C Pagar"
13. Informar mês/ano, data de pagamento, competência e data de entrada
14. Confirmar — sistema cria **1 lançamento por evento** na opção 475 (fornecedor = filial, parcelas = valores dos funcionários)
15. Processar pagamento via arquivo bancário (opção 522) se configurado

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 478 | Cadastro de Fornecedor — funcionários e filial devem ser cadastrados aqui ANTES de usar opção 580 |
| 478 → Baixar CSV / Importar | Permite cadastrar funcionários em lote via CSV (útil para cadastro inicial) |
| 475 | Contas a Pagar — recebe lançamento de despesa da folha (1 por evento) |
| 522 | Contas a Pagar via arquivo — gera arquivo de pagamento para banco (produto FOLHA DE PAGAMENTO) |
| 535 | Relação de Fornecedores — consulta fornecedores cadastrados |

## Observações e Gotchas

- **Sigilo mantido**: Sistema faz **1 único lançamento por evento** no Contas a Pagar (opção 475) — fornecedor é a **filial**, não o funcionário individual. Valores dos funcionários ficam como parcelas internas, não visíveis em relatórios gerais

- **Arquivo CSV — LAYOUT OBRIGATÓRIO**:
  - Coluna A: CPF do funcionário (só números)
  - Coluna B: Valor do salário
  - Coluna C: Sigla da unidade (opcional — se omitida, usar campo na tela de importação)
  - Coluna D: Código do evento (opcional — se omitido, usar campo na tela de importação)
  - **SEM linha de cabeçalho**

- **Tipo de Operação no cadastro de funcionário**: Campo obrigatório em opção 478 APENAS se transportadora utiliza Contas a Pagar via arquivo (opção 522) com produto FOLHA DE PAGAMENTO contratado do banco

- **Fornecedor = Filial**: Na despesa gerada (opção 475), o fornecedor é a **filial pagadora**, não o funcionário. Isso mantém sigilo dos valores individuais

- **Parcelas = Funcionários**: Valores dos funcionários ficam como parcelas da despesa, permitindo pagamento individualizado via arquivo bancário (opção 522)

- **Mês/ano na liberação**: Campo "Mês/ano" seleciona quais salários (importados anteriormente) serão liberados — permite importar folhas de múltiplos meses e liberar conforme necessário

- **Multiempresas**: Para transportadoras com multiempresas (opção 401), pagamento é realizado nas respectivas Matrizes Contábeis

- **Importação em lote de funcionários**: Opção 478 possui link "Baixar arquivo CSV / Importar" que permite cadastrar múltiplos funcionários como fornecedores de uma vez — útil para cadastro inicial

- **Relatórios**: Função "Relatório" permite filtrar por período, unidade e funcionários antes de liberar para Contas a Pagar — recomendado para conferência

- **Manutenção manual**: Após importação, é possível fazer ajustes manuais via "Manutenção da FOLHA" antes de liberar

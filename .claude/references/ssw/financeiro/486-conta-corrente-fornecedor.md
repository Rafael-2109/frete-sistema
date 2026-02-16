# Opção 486 — Conta Corrente do Fornecedor (CCF)

> **Módulo**: Financeiro
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Controla transações informais de débito e crédito com fornecedores (agregados, carreteiros, parceiros). Funciona como uma conta corrente paralela ao Contas a Pagar, permitindo lançamentos rápidos e acertos posteriores. Integra automaticamente com CTRBs, Ordens de Serviço e Contas a Pagar.

## Quando Usar
- Débito de despesas em agregados/carreteiros (combustível, pedágios, etc.)
- Crédito de fretes pagos (CTRBs de coleta, transferência)
- Acerto de saldos de agregados e parceiros
- Controle financeiro simplificado com fornecedores frequentes
- Débito de abastecimentos em bomba interna (veículos de terceiros)

## Pré-requisitos
- Fornecedor com CCF ativa (opção 478)
- Categoria de fornecedor definida: Agente/Parceiro, Proprietário de veículo, Motorista
- Para acertos: Despesa programada no Contas a Pagar (opção 475)

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Fornecedor** | Sim | CNPJ/CPF do fornecedor com CCF ativa (opção 478) |
| **Tipo de lançamento** | Sim | Débito (despesas) ou Crédito (fretes pagos) |
| **Valor** | Sim | Valor da transação |
| **Data** | Sim | Data do lançamento na CCF |
| **Histórico** | Não | Descrição da transação |

## Abas / Sub-telas

**Lançar:**
- Débito manual (despesas do fornecedor)
- Crédito manual (pagamentos ao fornecedor)

**Extrato:**
- Movimentação completa da CCF
- Saldo atual

**Saldo:**
- Consulta rápida de saldo

## Fluxo de Uso

### Débito Manual (Despesa)
1. Acessar opção 486
2. Selecionar fornecedor
3. Clicar em "Lançar"
4. Informar tipo=Débito
5. Informar valor, data e histórico
6. Confirmar lançamento
7. Sistema gera lançamento contábil automático conforme categoria:
   - Coleta agregado: Crédito seq. 42, Débito seq. 25
   - Transferência agregado: Crédito seq. 43, Débito seq. 25
   - Agente/Parceiro: Crédito seq. 44, Débito seq. 25
   - Motorista Frota: Crédito seq. 63/11, Débito seq. 19

### Crédito (Pagamento)
1. Emitir CTRB/OS (opção 072/075)
2. Sistema credita automaticamente CCF
3. Ou: Lançamento manual via "Lançar" → Crédito

### Acerto de Saldo
1. Verificar saldo na CCF (opção 486)
2. Programar acerto no Contas a Pagar (opção 475)
3. Sistema gera lançamento automático na CCF
4. Liquidar despesa (opção 476)

### Cancelamento de CTRB/OS
1. Cancelar CTRB/OS (opção 074)
2. Sistema debita CCF automaticamente (estorna crédito)
3. Ajustes financeiros automáticos (opção 475, 476)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 072 | Emissão de CTRB credita CCF automaticamente |
| 074 | Cancelamento de CTRB/OS debita CCF (estorna crédito) |
| 075 | Emissão de OS credita CCF automaticamente |
| 320 | Abastecimento interno debita CCF (veículos terceiros) |
| 408 | Cadastro de agentes/parceiros (categoria) |
| 027 | Cadastro de proprietários de veículos (categoria) |
| 028 | Cadastro de motoristas (categoria) |
| 475 | Contas a Pagar (acertos geram lançamento automático) |
| 476 | Liquidação de despesas (acertos de CCF) |
| 478 | Cadastro de fornecedores (ativar CCF) |
| 503 | Eventos com "Debita CCF" ativa |
| 541 | Lançamentos automáticos contábeis |
| 569 | Conciliação bancária (impede cancelamentos em data conciliada) |
| 577 | Debita veículo (após lançar despesa evento específico) |
| 611 | Extratos e saldos de todas CCFs |

## Observações e Gotchas

- **CCF deve estar ativa**: Configurar no fornecedor (opção 478) antes de usar
- **Lançamentos automáticos**:
  - CTRB/OS credita CCF na emissão
  - Cancelamento debita CCF (estorna)
  - Acerto via opção 475 gera lançamento automático
  - Abastecimento interno (opção 320) debita CCF para veículos terceiros
- **Categorias de fornecedor**: Define contas contábeis automáticas (opção 541)
- **Impedimento de cancelamento**: CTRB/OS não pode ser cancelado se alterar data já conciliada (opção 569)
- **Contabilização automática**: Varia conforme categoria (sequenciais 19, 25, 42, 43, 44, 63/11)
- **Eventos com CCF**: Despesas com evento configurado "Debita CCF" abrem opção 577 automaticamente
- **Relatórios gerais**: Opção 611 relaciona saldos de todas CCFs ativas
- **Seleção de fornecedores** (opção 611):
  - T=todos com CCF ativa
  - A=apenas agentes/parceiros
  - P=proprietários de veículos
  - M=motoristas
- **Extrato**: Período limitado a 31 dias (opção 611)
- **Integração Contas a Pagar**: Despesas de fornecedores com CCF debitam simultaneamente a conta corrente

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A05](../pops/POP-A05-cadastrar-fornecedor.md) | Cadastrar fornecedor |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
| [POP-F01](../pops/POP-F01-contas-a-pagar.md) | Contas a pagar |
| [POP-F02](../pops/POP-F02-ccf-conta-corrente-fornecedor.md) | Ccf conta corrente fornecedor |
| [POP-F03](../pops/POP-F03-liquidar-despesa.md) | Liquidar despesa |
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |

# Opcao 048 — Liquidacao a Vista (Fretes FOB)

> **Modulo**: Financeiro — Liquidacao
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Liquidar fretes FOB A VISTA recebidos pelo motorista no ato da entrega. Gera relacao de fretes liquidados pela unidade para confrontar com extrato bancario.

## Quando Usar
- Liquidar fretes FOB A VISTA recebidos por motorista
- Confrontar liquidacoes da unidade com extrato bancario
- Conciliar recebimentos de fretes

## Pre-requisitos
- Frete FOB A VISTA informado em Opcao 038 (Receber frete)
- Conta bancaria cadastrada (Opcao 456)

## Campos / Interface (Opcao 452 - Relatorio)

| Campo | Descricao |
|-------|-----------|
| Empresa | Para transportadoras multiempresas |
| Considerar | Liquidados por todos ou por usuario especifico (M - mim) |
| Arquivo Excel | Gera arquivo Excel |
| Unidade de liquidacao | Opcional para MTZ |
| Banco/ag/ccor | Conta bancaria |
| Periodo de liquidacao | Data da liquidacao |
| Periodo de credito no caixa | Data credito conta bancaria (Opcao 456) |
| Periodo de operacao do sistema | Data que usuario operou sistema |

## Fluxo de Uso
1. Motorista recebe frete FOB A VISTA na entrega
2. Informar valor recebido em Opcao 038 (campo "Receber frete")
3. Liquidar fretes via Opcao 048
4. Gerar relatorio Opcao 452 para confrontar com extrato bancario

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 038 | Informar frete FOB A VISTA recebido |
| 048 | Liquidacao de fretes |
| 452 | Relatorio fretes liquidados unidade |
| 456 | Cadastro contas bancarias / Conciliacao |
| 457 | Liquidacao alternativa |
| 569 | Conciliacao completa (todas unidades) |
| 571 | Liquidacao alternativa |
| 669 | Conciliacao completa (todas unidades) |

## Observacoes e Gotchas

### Confronto com Extrato Bancario
Liquidacoes da unidade devem ser **confrontadas com extrato bancario** para auxiliar conciliacao (Opcao 456).

### Conciliacao Completa
Conciliacao de todas unidades via Opcao 569 e 669.

### Util para Usuario Especifico
Opcao "Liquidados por M - mim" identifica liquidacoes de usuarios especificos.

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E04](../pops/POP-E04-cobranca-bancaria.md) | Cobranca bancaria |
| [POP-E05](../pops/POP-E05-liquidar-fatura.md) | Liquidar fatura |

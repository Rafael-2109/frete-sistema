# Fluxos de Processo End-to-End — SSW Sistemas

> **Versao**: 1.1 (split em arquivos individuais)
> **Fonte**: 227 docs de opcoes + 12 visoes gerais
> **Cobertura**: 20 fluxos, 120+ opcoes referenciadas

## Roteamento

Cada fluxo esta em `.claude/references/ssw/fluxos/FNN.md`. Ler apenas o fluxo relevante.

| Dominio | Fluxo | Titulo | Arquivo |
|---------|-------|--------|---------|
| Operacional | F01 | Coleta de Mercadoria | `F01.md` |
| Operacional | F02 | Expedicao / Emissao CT-e | `F02.md` |
| Operacional | F03 | Transferencia entre Unidades | `F03.md` |
| Operacional | F04 | Chegada e Descarga | `F04.md` |
| Operacional | F05 | Entrega ao Destinatario | `F05.md` |
| Financeiro | F06 | Faturamento | `F06.md` |
| Financeiro | F07 | Liquidacao e Cobranca | `F07.md` |
| Financeiro | F08 | Contas a Pagar | `F08.md` |
| Financeiro | F09 | Conciliacao Bancaria | `F09.md` |
| Fiscal | F10 | Fechamento Fiscal | `F10.md` |
| Contabil | F11 | Fechamento Contabil | `F11.md` |
| Comercial | F12 | Comissionamento de Vendedor | `F12.md` |
| Parcerias | F13 | Contratacao de Veiculo para Transferencia | `F13.md` |
| Parcerias | F14 | Remuneracao Coleta/Entrega (Agregados) | `F14.md` |
| Frota | F15 | Manutencao Preventiva | `F15.md` |
| Frota | F16 | Controle de Pneus | `F16.md` |
| Frota | F17 | Consumo de Combustivel | `F17.md` |
| Municipal | F18 | Emissao de RPS/NFS-e | `F18.md` |
| Logistica | F19 | Gestao de Estoque (Logistica/Armazenagem) | `F19.md` |
| Embarcador | F20 | Embarcador: Expedicao | `F20.md` |

## Mapa Geral de Dependencias

```
F01 Coleta → F02 Expedicao → F03 Transferencia → F04 Chegada → F05 Entrega
                                      ↓                              ↓
                                F13 Contratacao                 F14 Remuneracao
                                      ↓                              ↓
                                      └──────── F08 Contas a Pagar ←─┘
                                                      ↓
F05 Entrega → F06 Faturamento → F07 Liquidacao → F09 Conciliacao
                                                      ↓
                                      F10 Fechamento Fiscal → F11 Fechamento Contabil
```

## Palavras-chave por Fluxo

| Palavra-chave | Fluxo |
|---------------|-------|
| coleta, coletar, retirada | F01 |
| expedicao, CT-e, CTE, CTRC, emissao | F02 |
| transferencia, transbordo, redespacho | F03 |
| chegada, descarga, avaria | F04 |
| entrega, canhoto, ocorrencia entrega | F05 |
| faturamento, fatura cliente, cobranca | F06 |
| liquidacao, baixa titulo, boleto | F07 |
| contas a pagar, pagamento fornecedor | F08 |
| conciliacao, banco, extrato | F09 |
| fiscal, ICMS, SPED, EFD | F10 |
| contabil, balancete, razao | F11 |
| comissao, vendedor | F12 |
| contratacao, agregado, veiculo terceiro | F13 |
| remuneracao, frete agregado | F14 |
| manutencao, preventiva, OS | F15 |
| pneu, recapagem | F16 |
| combustivel, abastecimento | F17 |
| RPS, NFS-e, ISS, municipal | F18 |
| estoque, armazenagem, WMS | F19 |
| embarcador, despacho proprio | F20 |

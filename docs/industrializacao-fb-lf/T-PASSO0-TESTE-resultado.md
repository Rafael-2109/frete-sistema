# T-PASSO0-TESTE — Teste controlado do repoint (Bloqueador 1) ✅ PASSOU

**Data:** 2026-05-29 · **Execução:** `scripts/teste_controlado_repoint.py --execute` (uid 42)

## Objetivo
Provar que trocar as contas de estoque da categoria **no contexto da LF** (`ir.property`) redireciona o lançamento de valoração (SVL) para **terceiros (net-zero)** em vez de resultado/ativo-próprio. Era o ponto "raciocinado, não testado" (`DIRETRIZ.md:67`).

## Cobaia
categ **104** (PA/MOLHOS/LIQUIDOS, n_prod=1 LF) · produto **4870110** MOLHO SHOYU GL 3X5,02L · quant 264103 LF/Estoque (saldo 280).

## Antes (estado real)
| campo | conta |
|---|---|
| valoração | 1150100007 PRODUTO-ACABADO (próprio) |
| entrada | **3201000002 VARIAÇÕES POSITIVAS** (resultado ⚠️) |
| saída | 3201000003 VARIAÇÕES NEGATIVAS (resultado ⚠️) |

## Repoint aplicado (contexto LF, temporário)
valoração→`1150200001`(26140) · entrada/saída→`1150200002`(26141) · produção mantida `1150100004`.

## Resultado dos lançamentos (account.move reais)
| Movimento | account.move | Lançamento |
|---|---|---|
| Ajuste **+1** (entrada) | `ESTOQ/2026/05/6737` | **D 1150200001 28,30 / C 1150200002 28,30** ✅ |
| Ajuste **−1** (saída) | `ESTOQ/2026/05/6738` | **D 1150200002 28,30 / C 1150200001 28,30** ✅ |

`entrada_ok=True · saida_ok=True · saldo_restaurado=True (280) · categoria_restaurada=True`

## Conclusão
✅ **Premissa confirmada.** O mecanismo de config por categoria (company-dependent) funciona: entrada/saída de estoque na LF passam a lançar **net-zero em terceiros**, sem inflar ativo próprio nem tocar conta de resultado. Aprovado para rollout (após decisões do Contador).

## Rastro deixado
2 lançamentos posted net-zero no diário ESTOQUE LF (28,30 / −28,30). Saldo de estoque inalterado.

## Pendências (não cobertas por este teste)
- **Fase 2 — MO**: validar consumo→produção→terceiros (conta `1150100004`) — após decisão do Contador.
- Fluxo fiscal das 5 etapas (CFOPs/NFs).
- Regularização dos −R$ 25,4M já postados (LF) e R$ 785k (FB).

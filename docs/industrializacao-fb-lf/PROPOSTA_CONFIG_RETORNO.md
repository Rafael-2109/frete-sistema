# PROPOSTA — Config das operações + journals de RETORNO (G5a+G5b)

> Proposta concreta (**read-only/design — nenhuma escrita feita**) para corrigir a entrada de retorno na FB (OP5). Base: grounding 2026-05-30 (`scripts/proposta_retorno_grounding.py`). ⚠️ **Config GLOBAL** (afeta todos os retornos de industrialização) — exige OK Rafael + Contador antes de qualquer escrita; piloto **testa**.

## Estado atual (o que existe)
| Linha retorno | DFe CFOP orig | Operação hoje | `movimento_estoque` | Conta hoje |
|---|---|---|---|---|
| 1124 (PA+serviço) | 5124 | 3064/3134/1917 "Industrializ. efetuada p/ outra empresa" | **True** | journal ENTSI → 1150100011 |
| 1902 (insumos consumidos) | 5902 | **2027/2807** "Retorno merc. remetida p/ industrializ." | **True** ❌ | 1150100011 (re-infla) |
| 1903 (sobras) | 5903 | 838/3120 "Entrada retorno material não aplicado" | True | — |

Atribuição operação↔linha = campo **`l10n_br_cfop_orig_id`** (CFOP da DFe → operação). Conta = `tipo_pedido_entrada` → journal → `account_no_payment_id`.

🔴 **Nó contábil**: a remessa (saída) abre na **ATIVA `5101010001`** (id 22800), mas TODOS os journals de entrada FB creditam **PASSIVA** (`5101020001` id22815 / `5101020002` id22816). Logo o retorno **não baixa** a ATIVA → ciclo nunca fecha (ATIVA 60,8M ≠ PASSIVA 17,98M).

## Mudanças propostas (mecanismo provado = config por-linha)

### G5b — parar o double-count (insumos consumidos não re-entram) — UNAMBÍGUO
- **Mudança**: a operação do CFOP 1902 (2027/2807) → **`l10n_br_movimento_estoque = False`**.
- **Efeito**: a linha 1902 vira simbólica → **0 stock.move → 0 SVL → 0 double-count** (elimina o R$785k). Contabilmente inquestionável (insumos consumidos estão dentro do PA, não retornam fisicamente).
- ⚠️ Decisão: ajustar as ops 2027/2807 existentes (global) **ou** criar operação nova dedicada ao fluxo FB↔LF (isola o piloto). **Recomendado: criar nova** (`Retorno insumo industrializ. SIMBÓLICO FB↔LF`, cfop_orig=5902, intra=1902, movimento_estoque=False) p/ não afetar outros retornos no piloto.

### G5a — baixar a ATIVA `5101010001` no retorno — DEPENDE DO CONTADOR
- **Falta**: um journal de **entrada** (purchase) com `account_no_payment_id = 5101010001` (ATIVA). **Não existe** → criar.
- **Design A (recomendado — fecha o ciclo na ATIVA)**: criar journal **"ENTRADA - RETORNO DE INDUSTRIALIZAÇÃO"** (purchase, `account_no_payment_id = 22800 / 5101010001`); a operação do 1902 usa `tipo_pedido_entrada` → esse journal. Resultado: retorno **credita 5101010001** → `saldo do ciclo = 0`.
- **Design B (usar a família PASSIVA)**: manter a entrada na PASSIVA e reconciliar ATIVA×PASSIVA periodicamente. Não fecha por lançamento (acumula). ❌ não recomendado.
- ❓ **Contador decide A vs B** + se a perna RETORNO (`5101010002`/`5101020002`) entra no desenho.

### 🔴 "3 PERNAS" — como o custo dos insumos (Ic) entra no valor do PA — CONTADOR
O PA deve valer `Ic + S` (insumos + serviço). Mas: o AVCO do PA vem do **price_unit da linha física 1124**; um journal dá **1 conta** por linha. A entrada ideal é de 3 pernas: `D PA(Ic+S) / C FORNECEDORES(S) / C 5101010001(Ic)` — **não nativa** no CIEL IT (1 par por linha). Opções p/ o Contador:
- (i) PA valorado só por S; baixa de Ic via lançamento de regularização periódico.
- (ii) LF declara o PA na 1124 por `Ic+S`; split S/Ic resolvido por posição fiscal (a verificar) ou ajuste.
- (iii) custo dos insumos incorporado ao PA via custo da MO (BoM), sem baixa explícita na 1124.

### G5a/serviço 5124 + G6 (físico) — config
- 1124: manter `movimento_estoque=True` (PA entra). **SEM ICMS** (confirmado em NF real 2026-05-30 — CBS/IBS/PIS/COFINS, zero ICMS; não mexer em imposto).
- Rotear DFe de retorno → **pt52** (`src=26489`). G6.

## Sequência proposta (após OKs)
1. **Contador valida**: Design A (baixar ATIVA), tratamento das 3 pernas (i/ii/iii). *(ICMS 5124: resolvido — não há ICMS.)*
2. Criar (dry-run→exec) o journal de entrada + operação(ões) de retorno (1902 `movimento_estoque=False` + journal ATIVA; 1903; ajuste 1124).
3. Rotear retorno → pt52.
4. **Piloto 4870112**: 1 ciclo completo; medir critérios objetivos (GOALS §B): `5101010001=0`, `0 re-entrada de componentes`, `26489=0`, PA valorado por `Ic+S`.

## O que está PRONTO p/ decidir já (sem Contador)
- **G5b** (1902 `movimento_estoque=False`) é contabilmente inquestionável e elimina o double-count — pode ser a 1ª mudança isolada, criando operação nova dedicada (não-global). As demais (G5a/3-pernas/ICMS) dependem do Contador.

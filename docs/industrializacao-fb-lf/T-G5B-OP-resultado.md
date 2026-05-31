# T-G5B-OP — Criação da operação simbólica do retorno (lever G5b) ✅

**Data:** 2026-05-30 · **Script:** `scripts/g5b_piloto_criar_operacao.py --execute`

## Feito
Criada operação fiscal **id 3252** "Retorno insumo industrializ. SIMBOLICO (G5b PILOTO) FB-LF" — cópia fiel da **op 2027** (`Retorno de mercadoria remetida p/ industrialização`) com **apenas 3 overrides**:
| Campo | op 2027 (base) | op 3252 (nova) |
|---|---|---|
| `name` | Retorno de mercadoria remetida... | Retorno insumo ... SIMBOLICO (G5b PILOTO) |
| `l10n_br_movimento_estoque` | True | **False** ← o lever G5b |
| `l10n_br_cfop_orig_id` | 5902 | **False** (isolada — aplicar manual, não auto-seleciona) |

Tudo o mais **idêntico** (CFOP intra 1902 / inter 2902, `tipo_operacao=entrada`, `tipo_pedido_entrada=serv-industrializacao`, `gera_cpv=False`, fiscal_tags, mensagem). **Zero impacto fiscal** (e esta op não tem ICMS — confirmado).

## Efeito esperado
Quando aplicada na linha 1902 (insumos consumidos) de um retorno: `movimento_estoque=False` → **nenhum stock.move** → nenhum SVL → **componentes não re-entram no estoque** (elimina o double-count R$785k).

## Isolamento / reversão
- Sem `cfop_orig` → NÃO entra na seleção automática → **não afeta nenhum retorno existente**.
- Aplicação: manual no retorno-piloto (`l10n_br_operacao_manual=True` + `l10n_br_operacao_id=3252` na linha 1902).
- Reversível: desativar/excluir a op (nunca usada em doc real ainda).

## Pendente (mini-E2E)
Validar o efeito num ciclo real do 4870112 (remessa→produção→retorno→entrada FB com op 3252 na linha 1902). NÃO fecha o ciclo contábil (G5a baixa de `5101010001` + 3 pernas dependem do Contador) — o piloto valida **só o G5b** (estoque não infla).

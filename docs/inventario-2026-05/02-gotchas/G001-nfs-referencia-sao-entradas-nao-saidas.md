# G001 — NFs de referência do prompt são ENTRADAS, não SAÍDAS

**Descoberto em:** 2026-05-17 (audit F0)
**Severidade:** ALTA — afeta o desenho dos 4 services de NF

## Contexto

O prompt original (`app/agente/prompts/prompt_inventario.md`) lista 4 NFs como referência para a estrutura de cada CFOP de saída:

| Prompt diz | CFOP esperado | Direção esperada |
|---|---|---|
| NF 94457 | 5901 (saída) | FB→LF industrialização |
| NF 13075 | 5903 (saída) | LF→FB perda |
| NF 147772 | 5949 (saída) | FB↔LF dev-industrializacao |
| NF 94410 | 5152 (saída) | CD↔FB transf-filial |

## Achado do audit

A busca por `l10n_br_numero_nota_fiscal` retorna registros em `account.move` com características que **não são saídas**:

| NF | `account.move.id` | `name` | CFOP da linha | `fiscal_position_id` | `company_id` |
|---|---|---|---|---|---|
| 94457 | 607443 | RPI/2026/00200 | **5901** ✅ saída | 25 REMESSA P/ INDUSTRIALIZAÇÃO | 1 FB ✅ |
| 13075 | 588577 | RETNA/2026/04/0008 | **1903** ⚠️ entrada | 97 ENTRADA: RETORNO NÃO APLICADO | 1 FB ⚠️ (esperado LF) |
| 147772 | 603226 | ENTRE/2026/05/0002 | **1949** ⚠️ entrada | 86 ENTRADA - RETRABALHO | 5 LF |
| 94410 | 606166 | ENTTR/2026/05/0100 | **1152** ⚠️ entrada | 50 ENTRADA - TRANSFERÊNCIA ENTRE FILIAIS | 4 CD |

**Padrão**: 3 das 4 NFs (13075, 147772, 94410) são as **NFs de entrada** na empresa destinatária — espelho fiscal das saídas correspondentes. Apenas NF 94457 (industrializacao) bateu como saída direta.

## Implicações

1. Para emitir NF de SAÍDA via `account_move_intercompany_service.executar()`, **não podemos copiar do template da NF 13075/147772/94410** — copiaríamos campos de entrada (CFOP 1xxx, fiscal_position de entrada, company errada).

2. Precisamos buscar as **NFs de SAÍDA correspondentes**. Possibilidades:
   - Mesmo número fiscal mas em `company_id` da origem (ex: NF 13075 deve existir também em company_id=5 LF como saída CFOP 5903)
   - Número diferente (cada empresa numera suas saídas separadamente)

3. **Decisão de design afetada**:
   - Trocar NFs de referência por NFs de SAÍDA reais
   - OU manter as NFs de entrada como referência mas mapear "para gerar saída, preciso desses campos invertidos"

## Ação proposta

1. Investigar se NF 13075 também existe em `company_id=5` (LF) como `move_type='out_invoice'`
2. Idem para 147772 (origem dependendo da direção) e 94410 (FB)
3. Atualizar `MATRIZ_INTERCOMPANY[*]['nf_referencia']` com as NFs **de saída** corretas
4. Registrar premissa P11 no spec

## Observação adicional

`l10n_br_tipo_pedido` retornou:
- NF 94457 → `'industrializacao'` ✅
- NF 13075/147772/94410 → `False` (vazio)

Confirma que `l10n_br_tipo_pedido` é setado nas SAÍDAS, não nas entradas. Reforça a tese acima.

---
## Resultado da investigação (audit 00b)

### NF 94457
- **1 NF(s) de saída encontrada(s)** com mesmo número.
  - `account.move.id=607443` company=[1, 'NACOM GOYA - FB'] cfop_linha=5901 l10n_br_tipo_pedido='industrializacao'

### NF 13075
- **6 NF(s) de saída encontrada(s)** com mesmo número.
  - `account.move.id=588209` company=[5, 'LA FAMIGLIA - LF'] cfop_linha=5903 l10n_br_tipo_pedido='perda'
  - `account.move.id=169098` company=[4, 'NACOM GOYA - CD'] cfop_linha=5101 l10n_br_tipo_pedido='venda'
  - `account.move.id=169096` company=[4, 'NACOM GOYA - CD'] cfop_linha=5401 l10n_br_tipo_pedido='venda'
  - `account.move.id=169097` company=[4, 'NACOM GOYA - CD'] cfop_linha=5151 l10n_br_tipo_pedido='transf-filial'
  - `account.move.id=169058` company=[4, 'NACOM GOYA - CD'] cfop_linha=5102 l10n_br_tipo_pedido='venda'
  - `account.move.id=169060` company=[4, 'NACOM GOYA - CD'] cfop_linha=5920 l10n_br_tipo_pedido='vasilhame'

### NF 147772
- **1 NF(s) de saída encontrada(s)** com mesmo número.
  - `account.move.id=590839` company=[4, 'NACOM GOYA - CD'] cfop_linha=5949 l10n_br_tipo_pedido='dev-industrializacao'

### NF 94410
- **1 NF(s) de saída encontrada(s)** com mesmo número.
  - `account.move.id=604472` company=[1, 'NACOM GOYA - FB'] cfop_linha=5152 l10n_br_tipo_pedido='transf-filial'

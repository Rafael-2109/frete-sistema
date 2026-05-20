# D012 — Ajuste de estoque LF via planilha direta (criar saldo + realocação)

**Data**: 2026-05-20
**Decisão do usuário**: ajustar estoque LF diretamente por planilha, via
inventory adjustment, SEM emissão de NF e SEM transferir de MIGRAÇÃO/Indisponível.

## Contexto

Após as ondas de PERDA/INDUSTR via NF (D004/D011) e a consolidação em
`P-15/05`, restaram acertos finos de saldo na LF (company 5) que o usuário
passou a enviar em planilhas simples. Dois tipos:

| Planilha | Aba | Colunas | Natureza |
|----------|-----|---------|----------|
| Pasta16  | `AJUSTE POSITIVO` | EMP, COD, PROD, LOTE, AJUSTE POSITIVO | criar saldo (só +) |
| Pasta17  | `alteração lote`  | filial, cod, nome_produto, lote, QTD | realocação +/- (net-zero por produto) |

## Decisão — mecanismo: inventory adjustment PURO

- Operar direto em `stock.quant` via `inventory_quantity` + `action_apply_inventory`.
- **NÃO** é transferência de `MIGRAÇÃO`/`Indisponível` (D011 / `15r_transferencia_reversa.py`).
- **NÃO** é NF SEFAZ (pipeline D004). A contraparte contábil é o
  `Estoque Virtual/Ajuste de Estoque` (gerado automaticamente pelo Odoo).
- `QTD > 0` aumenta; `QTD < 0` reduz (delta com sinal). "Ajuste" = delta a
  SOMAR ao saldo atual (não saldo final).

## Regras consolidadas

1. **`P-15/05` muda de significado por planilha — SEMPRE confirmar:**
   - Pasta16 (criar saldo): `P-15/05` = **lote REAL** a criar (produtos `tracking=lot`).
   - Pasta17 (realocação): `P-15/05` = **placeholder de "sem lote"** (`lot_id=False`);
     o saldo "sem lote" da LF está materializado como lote `P-15/05` em LF/Estoque.
2. **Lote com vírgula = lote LITERAL real** (não split). Ver [G036](../02-gotchas/G036-lote-virgula-literal-e-duplicado-operador-igual.md).
3. **Resolver lot_id via `in`** (lotes duplicados + bug operador `=`). Ver G036.
4. **Redução multi-local**: consome de `LF/Estoque (42)` → `LF/Pré-Produção (53)`.
   Locais virtuais `Produção (39)` / `Ajuste de Estoque (38)` só com flag
   `--incluir-virtual` (consumo após esgotar físico).
5. **Aumento**: sempre em `LF/Estoque (42)`.
6. **Net-zero ATÔMICO por produto**: se qualquer redução de um produto não cobrir
   o saldo necessário, o produto inteiro é PULADO (não aplica os aumentos
   sozinhos → não infla estoque).
7. Locais: `COMPANY_LOCATIONS` = FB 8 / CD 32 / LF 42 (`app/odoo/constants/locations.py`).

## Scripts

- `scripts/inventario_2026_05/criar_saldo_positivo_lf.py` — Pasta16 (criar saldo).
- `scripts/inventario_2026_05/ajuste_estoque_lf_pasta17.py` — Pasta17 (realocação).

Ambos: dry-run default, `--confirmar` grava, log JSON em `auditoria/`, **não
idempotentes** (re-rodar a mesma planilha re-aplica). Verificação pós-exec:
re-consultar `quant_id` do log e comparar com o valor esperado.

## Resultados

- **Pasta16**: 25 lotes criados na LF (194.736,5551 un), 25/25 verificados.
- **Pasta17**: **138/147 produtos** aplicados (134 físico + 4 compostos
  literais), net-zero por produto, 380/380 quants verificados no Odoo.
- **9 produtos NÃO aplicáveis** (Pasta17): lotes-alvo com saldo líquido
  zero/negativo (já movidos/zerados) → planilha dessincronizada. Ver
  [PENDENCIAS.md P12](../PENDENCIAS.md).

## Riscos / observações

- Inventory adjustment direto **não passa por NF** — adequado para acerto interno
  de saldo entre lotes/locais da MESMA company; NÃO usar para movimento
  inter-company (esse exige o pipeline D004).
- Re-rodar `--confirmar` na mesma planilha duplica o efeito (não idempotente).
- Saldo preso em locais virtuais (38/39) com pares +/- indica operação anterior
  pela metade — investigar antes de forçar redução de lá.

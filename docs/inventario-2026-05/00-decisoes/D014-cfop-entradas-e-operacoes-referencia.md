<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D014 — CFOP de ENTRADA, regra por tipo de produto e operações de referência

> **Papel:** D014 — CFOP de ENTRADA, regra por tipo de produto e operações de referência.

**Data:** 2026-05-21
**Decidida por:** Rafael (validação fiscal 2026-05-21)
**Fonte:** validação XML-RPC **read-only** no Odoo PROD (faturas posted reais, par saída↔entrada via chave SEFAZ)
**Complementa/corrige:** D000 (audit), D001, D002 (matriz), P011
**Implementação:** `app/odoo/constants/operacoes_fiscais.py` (`MATRIZ_INTERCOMPANY` + `resolver_entrada`)

---

## 1. Motivação

A `MATRIZ_INTERCOMPANY` mapeava só a **saída** (out_invoice). Faltava a contraparte de **entrada** (in_invoice no destino) e a regra de CFOP **por tipo de produto** na industrialização por encomenda. Esta decisão consolida ambas, confirmadas no Odoo.

## 2. Regra de CFOP por TIPO DE PRODUTO (industrialização por encomenda FB↔LF)

| CFOP saída | Entrada | Tipo produto | Significado |
|---|---|---|---|
| **5901** | 1901 | 1,2,3 | FB→LF: remessa de **insumo** p/ industrializar |
| **5124** | 1124 | **4** | LF→FB: **produto acabado** industrializado + cobrança do serviço |
| **5902** | 1902 | 1,2,3 | LF→FB: retorno de **insumo utilizado** (par interno de 5124 na NF) |
| **5903** | 1903 | 1,2,3 | LF→FB: retorno de **insumo NÃO aplicado** (operação `perda`) |
| **5949** | 1949 | **4** | retrabalho/retorno/**ajuste de estoque** de produto (uso do agente) |
| **5921** | 1920 (não confirmado) | 2 | LF→FB: remessa de **vasilhame/sacaria** |

**Regras invioláveis (Rafael 2026-05-21):**
- **5902 NUNCA se aplica a produto acabado (tipo 4).** É exclusivo de insumo (tipo 1,2,3). Produto acabado é **5124** (com cobrança) ou **5949** (ajuste/retorno).
- **5902 e 5903 não são "par obrigatório"**: 152 NFs LF→FB → 96 só-5902 (VND), 56 só-5903 (RETNA), **0 com ambos**. O par de 5902 **dentro da mesma NF é o 5124** (produto acabado).

## 3. Matriz completa SAÍDA ↔ ENTRADA (confirmada no Odoo)

### Operações de AJUSTE de inventário

| Operação | Direção | tipo_pedido | Saída fp/CFOP | Entrada fp/CFOP/tipo_entrada | NFs referência |
|---|---|---|---|---|---|
| industrializacao | FB→LF | industrializacao | 25 / **5901** | 131 / **1901** / serv-industrializacao | RPI/2026/00200 → ENTIN/2026/05/0032 |
| perda | LF→FB | perda | 91 / **5903** | 97 / **1903** / retorno | RETNA/2026/00025 → RETNA/2026/04/0008 |
| dev-industrializacao | CD→LF | dev-industrializacao | 74 / **5949** | 86 / **1949** / retorno | RRET/2026/00008 → ENTRE/2026/05/0002 |
| dev-industrializacao | LF→CD | dev-industrializacao | 89 / **5949** | 87 / **1949** / outro | SARET/2026/00002 → ENTRE/2026/05/0001 |
| dev-industrializacao | LF→FB | dev-industrializacao | 89 / **5949** | (sem precedente válido) / 1949 | — |
| dev-industrializacao | FB→LF | dev-industrializacao | 74 / **5949** | 86 / 1949 (assumido, P011) | — (0 NFs) |
| transf-filial | FB→CD | transf-filial | 20 / **5152** | 50 / **1152** / transf-filial | SDTRA/2026/00881 → ENTTR/2026/05/0146 |
| transf-filial | CD→FB | transf-filial | 49 / **5151** | 22 / **1151** / transf-filial | SDTRA/2026/00344 → ENTTR/2026/05/0052 |

> Entradas de transf-filial usam fp **distintas** por direção: CD recebe via fp 50, FB recebe via fp 22.

### Operações de REFERÊNCIA (fluxo RecebimentoLF — NÃO usadas pelo ajuste de inventário)

| Operação | Direção | tipo_pedido | Saída fp/CFOP | Entrada fp/CFOP/tipo_entrada | NFs referência |
|---|---|---|---|---|---|
| venda-industrializacao | LF→FB | venda-industrializacao | 111 / **5124**(prod 4) + **5902**(insumo 1,2,3) | 88 / **1124** + **1902** / serv-industrializacao | VND/2026/00308 → ENTSI/2026/05/0034 |
| vasilhame | LF→FB | dev-vasilhame | 64 / **5921** | **não confirmada** (1920 candidato) | VAS/2026/00160 → (sem in_invoice) |

## 4. Erro conhecido no Odoo

NFs de **produto acabado (tipo 4) emitidas com CFOP 5902** — ex.: **SARET/2026/00006-9** (LF→FB) — são **classificação fiscal incorreta**: deveriam ser **5949** (ajuste/retorno) ou **5124** (industrialização com cobrança). **Não usar como precedente.** Levantamento completo das NFs afetadas: pendente (read-only, sob demanda).

## 5. Correções a documentos anteriores

- **D002 §"Variante histórica em LF→CD: 89 vs 64"**: a fp **64** NÃO é variante de `dev-industrializacao` LF→CD/5949. É operação **própria** `dev-vasilhame` **LF→FB**, CFOP **5921** (série VAS). Confirmado VAS/2026/00160.
- **D002 / P011**: `dev-industrializacao` LF→FB usa **5949** (produto tipo 4), não 5902. O 5902 visto em SARET LF→FB é erro (item 4).
- **D000 "itens em aberto"**: fiscal_position por company para 5901/5903/5949/5152/5151 — **todas confirmadas** nesta decisão.

## 6. Mudança na implementação

`app/odoo/constants/operacoes_fiscais.py`:
- Adicionado bloco **`entrada`** (fp + cfop + `l10n_br_tipo_pedido_entrada`) por direção nas 4 operações de ajuste.
- Adicionadas as 2 operações de **referência** (`venda-industrializacao`, `vasilhame`), marcadas com `uso` e fora de `resolver_operacao_por_tipo_produto`.
- Nova função **`resolver_entrada(tipo, origem, destino)`**.
- `cfop_esperado` de `venda-industrializacao` é dict por classe de produto (NF mista).
- 28 testes em `tests/odoo/constants/test_operacoes_fiscais.py`.

## 7. Pendências

- [ ] Confirmar a NF de **entrada do vasilhame** (CFOP 1920? fp? — remessa 5921 não gerou in_invoice por chave).
- [ ] Levantar todas as NFs com **produto tipo 4 + 5902** (erro de classificação) para correção.
- [ ] `dev-industrializacao` **FB→LF (1,5)** e **LF→FB (5,1)** sem precedente válido de 5949 → **canary fiscal** antes de bulk.

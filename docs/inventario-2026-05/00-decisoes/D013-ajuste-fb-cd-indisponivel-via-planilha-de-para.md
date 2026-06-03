<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D013 — Ajuste FB+CD via planilha De→Para (Estoque ↔ Indisponível)

> **Papel:** D013 — Ajuste FB+CD via planilha De→Para (Estoque ↔ Indisponível).

## Indice

- [Contexto](#contexto)
- [Decisão — mecanismo: inventory adjustment em 2 passos](#decisão-mecanismo-inventory-adjustment-em-2-passos)
- [Regras de resolução (confirmadas pelo usuário)](#regras-de-resolução-confirmadas-pelo-usuário)
- [Script](#script)
- [Resultados (execução 2026-05-20 02:52–03:51)](#resultados-execução-2026-05-20-02520351)
- [Riscos / observações](#riscos-observações)

**Data**: 2026-05-20
**Decisão do usuário**: ajustar estoque FB (company 1) e CD (company 4) por planilha
no formato **De-Local/De-Lote → Para-Local/Para-Lote**, via inventory adjustment em
2 passos, transferindo entre `Estoque` e `Indisponivel` (D011), SEM emissão de NF.

## Contexto

Sequência de D011 (locais `{emp}/Indisponivel`) e D012 (ajuste LF puro). Agora o
usuário envia planilhas FB/CD com a **direção explícita** (origem e destino de
local **e** lote por linha), não só um delta:

| Planilha | Aba | Colunas | Linhas |
|----------|-----|---------|--------|
| AJUSTE FB.xlsx | `AJUSTES FB` | filial, cod, nome_produto, De-Local, De-Lote, Para-Local, Para-Lote, **diff_qtd** | 2259 |
| TRANSF CD.xlsx | `Planilha1` | EMP, CODIGO, PRODUTO, De-Local, De-Lote, Para-Local, Para-Lote, **QTD** | 101 |

Duas direções por planilha:
- **SAÍDA** `{emp}/Estoque/<lote>` → `{emp}/Indisponivel/MIGRAÇÃO` (remove saldo que sobra).
- **RETORNO** `{emp}/Indisponivel/MIGRAÇÃO` → `{emp}/Estoque/<lote>` (devolve ao estoque com lote real).

`qtd` é **sempre positiva (magnitude)**; a direção vem dos campos De/Para — diferente
de D010 (sinal de diff_qtd) e D012 (delta com sinal).

## Decisão — mecanismo: inventory adjustment em 2 passos

Para cada linha: (1) reduz `inventory_quantity` do(s) quant(s) de origem; (2) aumenta/cria
o quant de destino. Cada lado gera contraparte automática no `Estoque Virtual/Ajuste de
Inventario`; o líquido é apenas o deslocamento origem→destino. Padrão idêntico a
`mover_migracao_para_indisponivel.transferir_entre_locations` e
`StockInternalTransferService.transferir_entre_lotes`, mas mudando **local E lote** ao mesmo tempo.

**NÃO** é NF SEFAZ (acerto interno da mesma company). **NÃO** é renomeação de lote.

## Regras de resolução (confirmadas pelo usuário)

1. **`FB/Estoque`, `CD/Estoque`, `CD/*` como ORIGEM = WILDCARD**: o lote é buscado em
   **qualquer location interna** da company exceto `Indisponivel`. O saldo do inventário
   fica espalhado nas "pastas" usadas (`FB/Pré-Produção/Linha Manual|Balde|Vidro|Salmoura`,
   `FB/Pós-Produção`, `CD/Estoque/*`), **não** na location raiz.
   - Usuário (2026-05-20): *"Pratileiras não são usadas. O motivo de CD/* é para procurar
     em todas as outras pastas"*. As prateleiras CD (`R-XX/N-X/P-nn`, ~2700 locations) têm
     saldo zero — buscar em todas as internas já as ignora.
   - **Sem essa regra**: 816/2146 linhas FB davam `SEM_SALDO` falso (saldo em sub-locations).
   - Quando `FB/Estoque`/`CD/Estoque` é **DESTINO** (retorno), usa loc fixo (8 / 32).

2. **De-Lote vazio (NaN) em origem de estoque/wildcard = lote `P-15/05`**: o saldo do
   inventário foi consolidado no lote da contagem de 15/05. 103/135 linhas FB sem-lote
   batem exato com P-15/05. Se P-15/05 não existe p/ o produto → `LOTE_ORIGEM_INEXISTENTE`
   (não adivinhar lote datado).

3. **Lote `MIGRAÇÃO`**: cada produto tem 2 variantes (`MIGRAÇÃO` com acento e `MIGRACAO`
   sem); o saldo fica em uma delas. Resolver pelo lote com **maior saldo na location** em
   questão (origem do retorno = Indisponivel; destino da saída = consolidar onde já há
   saldo). Ver [G036](../02-gotchas/G036-lote-virgula-literal-e-duplicado-operador-igual.md).

4. **Lote literal (inclui `-`)**: busca exata via `StockLotService.buscar_por_nome`
   (operador `in` + `=like`, nunca `=`). `-` é um lote real no CIEL IT.

5. **CLAMP / saldo fresco**: lê o saldo **fresco do Odoo por linha**. Se `qty > saldo_livre`
   por ≤ 0,001 (arredondamento) → clamp ao saldo; se maior → transfere o disponível e marca
   `clamp_parcial` (delta não transferido = divergência de inventário, não erro). `reserved_quantity`
   que impediria o saldo restante → **PULA** o quant (não cancela picking).

6. **Locais (D011)**: FB/Estoque=8, FB/Indisponivel=31088, CD/Estoque=32, CD/Indisponivel=31090.

## Script

`scripts/inventario_2026_05/ajuste_fb_cd_indisponivel.py`:
- Dry-run default; `--confirmar` grava; `--arquivo FB|CD|AMBOS`; `--so-direcao SAIDA|RETORNO`;
  `--retomar-de N` (retomada pós-crash); `--apenas-linhas`; `--limite`.
- **Checkpoint incremental** do log JSON a cada 100 linhas + retry resiliente (backoff)
  para erros transitórios XML-RPC (503/timeout/SSL).
- **Não idempotente** (re-rodar a mesma planilha re-aplica). Verificação pós-exec:
  re-consultar `quant_id` do log + comparar.

## Resultados (execução 2026-05-20 02:52–03:51)

- **CD**: 98/101 EXECUTADO (68 saída + 30 retorno), 0 falhas. 219.753 + 16.889 un.
- **FB**: 2154/2259 EXECUTADO (2046 saída + 108 retorno), 0 falhas. ~28,6M un → FB/Indisponivel
  (subiu para ~158,4M).
- **108 exceções** (ver [PENDENCIAS.md P13](../PENDENCIAS.md) + `Downloads/EXCECOES_AJUSTE_FB_CD_2026_05_20.xlsx`).
- Detalhe: [EXECUCAO_AJUSTE_FB_CD_INDISPONIVEL_2026_05_20.md](../08-execucoes/EXECUCAO_AJUSTE_FB_CD_INDISPONIVEL_2026_05_20.md).

## Riscos / observações

- **Operações concorrentes**: durante os 56 min de execução, industrializações FB→LA FAMIGLIA
  consumiram saldo de 52 lotes (rótulos P-15/05) antes das linhas correspondentes. O saldo-fresco
  protegeu (essas linhas viraram `SEM_SALDO`, sem mover). Em runs longos, contar com concorrência.
- Inventory adjustment **não passa por NF** — apenas acerto interno da MESMA company.
- O valor de `diff_qtd`/`QTD` da planilha vem do **monitor de inventário**, podendo divergir do
  saldo físico Odoo (ex: cod 109000100 OLEO — monitor 40,4M vs Odoo 6,3M). Confirmar a fonte antes
  de tratar como quantidade física.

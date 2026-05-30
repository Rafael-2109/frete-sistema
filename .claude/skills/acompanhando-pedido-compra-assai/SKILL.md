---
name: acompanhando-pedido-compra-assai
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre pedidos VOE
  Q.P.A. (vendas para Sendas/Assai) ou compras Motochefe (vinculadas N:N
  aos pedidos): "como esta o pedido VOE 12345?", "compras Motochefe abertas",
  "MA-2026-0001 ja chegou?", "pedidos pendentes Q.P.A.". Mostra status,
  totais por loja, vinculacoes pedido-compra.

  USAR QUANDO:
  - "pedido VOE 12345"
  - "compra Motochefe MA-2026-0001"
  - "pedidos abertos Q.P.A."
  - "compras pendentes Motochefe"

  NAO USAR PARA:
  - Estoque/pipeline (usar consultando-estoque-assai)
  - Chassis individuais (usar rastreando-chassi-assai)
  - Separacoes/NFs (usar acompanhando-saida-assai)
allowed-tools: Read, Bash, Glob, Grep
---

# Acompanhando Pedido/Compra Motos Assai

Consulta pedidos VOE Q.P.A. (1 por loja x modelo) e compras Motochefe
(consolidacoes N->1 dos pedidos, com numero MA-AAAA-NNNN).

---

## Modelo de dados

- `assai_pedido_venda` (numero, status, criado_em)
- `assai_pedido_venda_item` (pedido_id, loja_id, modelo_id, qtd_pedida, valor_unitario)
- `assai_compra_motochefe` (numero, data_emissao, status, criada_em)
- `assai_compra_motochefe_pedido` (compra_id, pedido_id) — N:N

**Status pedido**: `ABERTO`, `PARCIALMENTE_FATURADO`, `FATURADO`, `CANCELADO`
(legados `EM_PRODUCAO`/`SEPARANDO`/`FATURADO_PARCIAL` removidos — Big Bang Task 19, 2026-05-13)
**Status compra**: `ABERTA`, `RECEBIMENTO_PARCIAL`, `FECHADA`, `CANCELADA`

---

## Args

- `--pedido-id <id>` ou `--numero-pedido <num>` - pedido especifico
- `--compra-id <id>` ou `--numero-compra "MA-2026-0001"` - compra especifica
- `--somente-abertos` - pedidos != FATURADO/CANCELADO + compras != FECHADA/CANCELADA

---

## Invocacao

```bash
python .claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py \
    --somente-abertos
```

---

## Output JSON

```json
{
  "pedidos": [
    {
      "id": 1, "numero": "VOE-12345", "status": "ABERTO",
      "criado_em": "...", "lojas_distintas": 38, "total_itens": 114,
      "total_qtd": 380,
      "compras_vinculadas": [{"id": 5, "numero": "MA-2026-0003", "status": "ABERTA"}]
    }
  ],
  "compras": [
    {
      "id": 5, "numero": "MA-2026-0003", "status": "ABERTA",
      "data_emissao": "...", "criada_em": "...",
      "pedidos_vinculados": [{"id": 1, "numero": "VOE-12345", "status": "ABERTO"}]
    }
  ],
  "exit_code": 0
}
```

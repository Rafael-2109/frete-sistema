---
name: acompanhando-saida-assai
description: >-
  Skill READ para separacoes em andamento e NFs Q.P.A. importadas no modulo
  Motos Assai: separacoes ativas (EM_SEPARACAO/FECHADA) e NFs com resultado
  de match (BATEU/DIVERGENTE/NAO_RECONCILIADO). Gatilhos: "separacoes abertas
  Q.P.A.", "NF Q.P.A. 12345 bateu?", "ha divergencias em NFs?", "qual loja
  recebeu NF X?". NAO usar para carregamento (escaneio fisico) ->
  carregando-motos-assai. Matriz USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# Acompanhando Saida Motos Assai

Consulta separacoes em andamento e NFs Q.P.A. importadas com resultado de match.

## Quando usar / Quando NAO usar

**USAR QUANDO:**
- "separacoes em andamento Q.P.A." / "separacoes abertas"
- "NF Q.P.A. 12345 importada?" / "NF Q.P.A. 12345 bateu?" / "match BATEU?"
- "divergencias em NFs"
- "qual loja recebeu NF X?"

**NAO USAR PARA:**
- Estoque -> `consultando-estoque-assai`
- Chassi individual -> `rastreando-chassi-assai`
- Pedidos/compras -> `acompanhando-pedido-compra-assai`
- Carregamento (etapa entre Separacao e NF) -> `carregando-motos-assai`

---

## Modelo de dados

- `assai_separacao` (pedido_id, loja_id, status, iniciada_em)
- `assai_separacao_item` (separacao_id, chassi, modelo_id, valor_unitario_qpa)
- `assai_nf_qpa` (chave_44, numero, separacao_id, loja_id, status_match, importada_em)
- `assai_nf_qpa_item` (nf_id, chassi, separacao_item_id, tipo_divergencia)

**Status separacao**: `EM_SEPARACAO`, `FECHADA`, `FATURADA`, `CANCELADA`
**Status match NF**: `BATEU`, `DIVERGENTE`, `NAO_RECONCILIADO`

---

## Args

- `--separacao-id <id>` - separacao especifica
- `--somente-abertas` - separacoes em EM_SEPARACAO ou FECHADA
- `--nfs-recentes` - ultimas 20 NFs Q.P.A. importadas
- `--divergentes` - apenas NFs com match DIVERGENTE/NAO_RECONCILIADO

---

## Invocacao

```bash
python .claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py \
    --somente-abertas
```

---

## Output JSON

```json
{
  "separacoes": [
    {
      "id": 5, "pedido_id": 1, "loja_id": 10,
      "loja_numero": "LJ123", "loja_nome": "SENDAS LJ123 SP", "loja_uf": "SP",
      "status": "EM_SEPARACAO", "iniciada_em": "...",
      "total_chassis": 7, "total_modelos": [{"modelo": "SOL", "qtd": 5}]
    }
  ],
  "nfs_qpa": [
    {
      "id": 3, "numero": "12345", "chave_44": "...", "data_emissao": "...",
      "status_match": "BATEU", "loja_id": 10,
      "separacao_id": 5, "total_itens": 7, "total_divergentes": 0,
      "importada_em": "..."
    }
  ],
  "exit_code": 0
}
```

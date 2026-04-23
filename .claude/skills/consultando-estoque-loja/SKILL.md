---
name: consultando-estoque-loja
description: >-
  Esta skill deve ser usada pelo Agente Lojas HORA quando o usuario pergunta
  sobre estoque de motos nas lojas HORA: "quantas motos tenho?", "quanto tem
  de <modelo>?", "o chassi XYZ ja chegou?", "quais motos estao em transito?",
  ou precisa conferir disponibilidade fisica por loja. Respeita
  automaticamente o escopo do usuario via <loja_context> (usuario escopado
  ve so sua loja; admin ve todas).

  USAR QUANDO:
  - "quantas motos tenho aqui?"
  - "quantas <modelo> tem disponivel?"
  - "quanto tenho em estoque?"
  - "o chassi XXX ja chegou?"
  - "quais motos em transito?"

  NAO USAR PARA:
  - Historico completo de um chassi (usar rastreando-chassi)
  - Conferencia de recebimento (usar conferindo-recebimento — M2)
  - Venda/baixa de estoque (usar registrando-venda — M3)
  - Estoque Nacom Goya (usar gerindo-expedicao — agente diferente)
allowed-tools: Read, Bash, Glob, Grep
---

# Consultando Estoque Loja HORA

Consulta o estoque fisico de motos eletricas nas lojas HORA, respeitando
escopo por loja do usuario.

---

## Quando Usar Esta Skill

USE para:
- Contagem de estoque: "quantas motos tenho?", "quanto de <modelo>?"
- Verificar chassi: "o chassi MC172XXX ja chegou?"
- Motos em transito: "quais motos pedidas mas nao recebidas?"
- Visao por loja (admin): "como esta o estoque de cada loja?"

NAO USE para:
- Historico detalhado de UM chassi -> usar `rastreando-chassi`
- Conferencia fisica de recebimento -> usar `conferindo-recebimento`
- Venda B2C -> usar `registrando-venda`

---

## REGRAS CRITICAS

### 1. GUARDRAIL ANTI-ALUCINACAO
**PROIBIDO** inferir quantidades ou status sem rodar o script.
Se o script retornou vazio: diga "nao ha motos cadastradas com esses criterios"
em vez de inventar.

### 2. RESPEITAR <loja_context>
O bloco `<loja_context>` injetado no prompt define o escopo:
- `pode_ver_todas: true` -> pode consultar qualquer `loja_id`
- `pode_ver_todas: false` + `loja_ids_permitidas: [X]` -> SEMPRE passar `--loja-ids X`
- NUNCA passar `--loja-ids` fora desse conjunto.

### 3. MOTOS SEM EVENTO = EM TRANSITO
Uma moto em `hora_moto` sem linha em `hora_moto_evento` NAO esta em estoque
de nenhuma loja — esta em transito (pedido/NF ja lancada, mas nao recebida
fisicamente). Mostrar em categoria separada.

### 4. ULTIMO EVENTO = POSICAO ATUAL
Estoque de uma loja = chassis cujo ULTIMO evento (ordenado por timestamp DESC)
tem `tipo='RECEBIDA'` E `loja_id=<loja>`.

---

## DECISION TREE

| Pergunta do usuario | Parametros do script |
|---------------------|----------------------|
| "quantas motos?" (generico) | `--resumo` |
| "quanto de PMX?" | `--modelo "PMX"` |
| "chassi MC172 chegou?" | `--chassi MC172922511890568` |
| "motos em transito?" | `--incluir-transito --so-transito` |
| admin: "estoque por loja" | `--por-loja` |

Sempre incluir `--loja-ids <X,Y,...>` quando `pode_ver_todas: false`.

---

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python .claude/skills/consultando-estoque-loja/scripts/consultando_estoque_loja.py \
    --loja-ids 2 \
    --resumo
```

Output: JSON imprimido em stdout.

---

## Output JSON

```json
{
  "escopo_aplicado": {"loja_ids": [2], "modelo": null, "chassi": null},
  "lojas": [
    {"id": 2, "apelido": "MOTOCHEFE BRAGANCA", "cidade": "BRAGANCA PAULISTA"}
  ],
  "totais": {"estoque": 1, "transito": 0, "vendido": 0},
  "por_modelo": [
    {"modelo": "PMX", "estoque": 1, "transito": 0}
  ],
  "motos": [
    {
      "chassi": "MC172922511890568",
      "modelo": "PMX", "cor": "preta", "ano_modelo": 2026,
      "loja_atual_id": 2, "loja_atual": "MOTOCHEFE BRAGANCA",
      "status": "estoque",
      "ultimo_evento": {"tipo": "RECEBIDA", "timestamp": "2026-04-22T21:50"}
    }
  ],
  "_debug": {"query_ms": 42}
}
```

---

## Referencias

- Schema: `.claude/skills/consultando-sql/schemas/tables/hora_moto.json`
- Schema eventos: `.claude/skills/consultando-sql/schemas/tables/hora_moto_evento.json`
- Invariante: `app/hora/CLAUDE.md` secao "Invariante central"

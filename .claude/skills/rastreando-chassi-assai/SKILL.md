---
name: rastreando-chassi-assai
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre o historico
  completo de UM chassi do modulo Motos Assai (B2B Q.P.A.): "cade o chassi
  MZX1234?", "historico do chassi X", "essa moto Q.P.A. ja foi separada?",
  "quando o chassi Y chegou ao CD?". Retorna eventos cronologicos, recibo
  Motochefe de origem, separacao ativa (se houver), NF Q.P.A. (se faturada),
  validacao de regex contra modelo.

  USAR QUANDO:
  - "cade o chassi MZX...?"
  - "historico do chassi"
  - "essa moto Q.P.A. ja foi vendida/separada?"
  - "em que recibo veio o chassi X?"

  NAO USAR PARA:
  - Estoque agregado (usar consultando-estoque-assai)
  - Chassis Lojas HORA (usar rastreando-chassi)
  - Pedido/compra do chassi (usar acompanhando-pedido-compra-assai)
allowed-tools: Read, Bash, Glob, Grep
---

# Rastreando Chassi Motos Assai

Mostra historico completo de UM chassi: eventos cronologicos, recibo de origem,
separacao ativa, NF Q.P.A. (se faturada).

---

## Invocacao

```bash
python .claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py \
    --chassi MZX1234567890
```

Output: JSON com historico completo.

---

## Output JSON

```json
{
  "encontrado": true,
  "chassi": "MZX1234",
  "moto": {
    "id": 42, "modelo_id": 1, "modelo_codigo": "SOL", "cor": "preta",
    "ano": 2026, "criada_em": "..."
  },
  "status_efetivo": "DISPONIVEL",
  "eventos": [
    {"id": 100, "tipo": "DISPONIVEL", "ocorrido_em": "...", "operador": "..."},
    {"id": 99, "tipo": "MONTADA", "ocorrido_em": "...", "operador": "..."},
    {"id": 98, "tipo": "ESTOQUE", "ocorrido_em": "...", "operador": "..."}
  ],
  "recibo_origem": {
    "id": 5, "compra_id": 3, "data_recebimento": "..."
  },
  "separacao_ativa": null,
  "nf_qpa": null,
  "regex_check": {"ok": true, "regex_usado": "^MZX[0-9]{13}$"},
  "exit_code": 0
}
```

Quando chassi nao existe: `{"encontrado": false, "chassi": "...", "mensagem": "..."}`.

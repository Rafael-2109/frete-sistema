---
name: consultando-estoque-assai
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre estoque ou pipeline
  de motos do modulo Motos Assai (B2B Q.P.A. Sendas/Assai): "quantas motos
  disponiveis?", "estoque por modelo Q.P.A.", "quanto de SOL temos?", "pipeline
  de motos Assai", "quantas em ESTOQUE/MONTADA/DISPONIVEL/SEPARADA?". Retorna
  totais por estagio (ESTOQUE/MONTADA/PENDENTE/DISPONIVEL/SEPARADA/FATURADA),
  por modelo e lista de motos com pendencia.

  USAR QUANDO:
  - "quantas motos Q.P.A. disponiveis?"
  - "estoque por modelo Assai"
  - "quanto de SOL/X11_MINI/DOT temos?"
  - "pipeline de motos hoje"
  - "quais chassis em PENDENTE?"

  NAO USAR PARA:
  - Historico de UM chassi especifico (usar rastreando-chassi-assai)
  - Pedidos VOE Q.P.A. ou compras Motochefe (usar acompanhando-pedido-compra-assai)
  - Separacoes ou NFs Q.P.A. (usar acompanhando-saida-assai)
  - Estoque Lojas HORA (usar consultando-estoque-loja)
  - Estoque Nacom Goya (usar gerindo-expedicao)
allowed-tools: Read, Bash, Glob, Grep
---

# Consultando Estoque Motos Assai

Consulta o pipeline de motos do modulo Motos Assai (B2B Q.P.A.) por estagio
de evento (ESTOQUE/MONTADA/PENDENTE/DISPONIVEL/SEPARADA/FATURADA).

---

## Quando Usar

USE para:
- Contagem por estagio: "quantas DISPONIVEL?", "quantas em PENDENTE?"
- Filtro por modelo: "quanto de SOL?"
- Resumo geral do pipeline

NAO USE para:
- Historico de UM chassi -> `rastreando-chassi-assai`
- Pedidos/compras -> `acompanhando-pedido-compra-assai`
- Separacoes/NFs -> `acompanhando-saida-assai`

---

## REGRAS CRITICAS

### 1. STATUS = ULTIMO EVENTO
Estado atual de uma moto = ultimo evento em `assai_moto_evento` ordenado
por `ocorrido_em DESC`. NUNCA usar coluna `status` (nao existe). Usar helper
`status_efetivo(chassi)`.

### 2. MOTO SEM EVENTO = NAO CONTA
`AssaiMoto` sem evento e estado invalido (deveria ter pelo menos ESTOQUE).
Nao conta nos totais de pipeline.

### 3. EVENTOS_EM_ESTOQUE
Estes eventos contam como "em estoque": ESTOQUE, MONTADA, PENDENTE, DISPONIVEL.
SEPARADA, FATURADA, CANCELADA, MOTO_FALTANDO sao "fora de estoque".

---

## Decision Tree

| Pergunta do usuario | Args |
|---------------------|------|
| "quantas motos?" | `--resumo` |
| "quanto de SOL?" | `--modelo SOL` |
| "por modelo" | `--por-modelo` |
| "por estagio" | `--por-estagio` |

---

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python .claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py --resumo
```

Output: JSON em stdout.

---

## Output JSON

```json
{
  "totais": {
    "estoque": 12, "montada": 8, "pendente": 2,
    "disponivel": 15, "separada": 7, "faturada": 230
  },
  "por_modelo": [
    {"modelo": "SOL", "estoque": 5, "montada": 3, "disponivel": 8, "separada": 4, "faturada": 100}
  ],
  "por_cd": [],
  "motos_pendentes": [
    {"chassi": "MZX1234", "descricao_pendencia": "...", "criado_em": "..."}
  ],
  "vazio": false,
  "exit_code": 0
}
```

NOTA: `por_cd` retorna [] nesta versao (CD nao esta direto em assai_moto;
seria join via recibo->compra->cd).

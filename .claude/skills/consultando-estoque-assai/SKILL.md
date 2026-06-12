---
name: consultando-estoque-assai
description: >-
  Skill READ para estoque e pipeline de motos do modulo Motos Assai (B2B
  Q.P.A. Sendas/Assai): totais por estagio
  (ESTOQUE/MONTADA/PENDENTE/DISPONIVEL/SEPARADA/FATURADA), por modelo e motos
  com pendencia. Gatilhos: "quantas motos Q.P.A. disponiveis?", "estoque por
  modelo Assai", "quanto de SOL temos?", "pipeline de motos hoje". NAO usar
  para historico de UM chassi -> rastreando-chassi-assai. Matriz
  USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# Consultando Estoque Motos Assai

Consulta o pipeline de motos do modulo Motos Assai (B2B Q.P.A.) por estagio
de evento (ESTOQUE/MONTADA/PENDENTE/DISPONIVEL/SEPARADA/FATURADA).

---

## Quando usar / Quando NAO usar

**USAR QUANDO:**
- Contagem por estagio: "quantas DISPONIVEL?", "quantas em PENDENTE?",
  "quantas em ESTOQUE/MONTADA/DISPONIVEL/SEPARADA?", "quais chassis em PENDENTE?"
- Filtro por modelo: "quanto de SOL/X11_MINI/DOT temos?", "estoque por modelo Q.P.A."
- Resumo geral do pipeline: "pipeline de motos Assai", "pipeline de motos hoje"

**NAO USAR PARA:**
- Historico de UM chassi especifico -> `rastreando-chassi-assai`
- Pedidos VOE Q.P.A. ou compras Motochefe -> `acompanhando-pedido-compra-assai`
- Separacoes ou NFs Q.P.A. -> `acompanhando-saida-assai`
- Estoque Lojas HORA -> `consultando-estoque-loja`
- Estoque Nacom Goya -> `gerindo-expedicao`

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

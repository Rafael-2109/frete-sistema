---
name: conferindo-recebimento
description: >-
  Skill READ do Agente Lojas HORA para status de conferencia de recebimento
  (em andamento ou concluida): conferidos vs pendentes, divergencias e fotos.
  Respeita escopo de loja. Gatilhos: "como esta a conferencia da NF X?",
  "quantos chassis faltam conferir?", "tem divergencia no recebimento?",
  "status do recebimento 5?". NAO usar para pecas faltando ->
  consultando-pecas-faltando. Matriz USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# Conferindo Recebimento HORA

Mostra o progresso de uma conferencia fisica de recebimento: chassis
conferidos vs pendentes, divergencias e detalhes.

---

## Quando usar / Quando NAO usar

**USAR QUANDO:**
- "como esta a conferencia da NF X?" / "como esta a conferencia do recebimento 5?"
- "quantos chassis faltam conferir?" / "quantos chassis faltam na NF 36612?"
- "tem divergencia no recebimento?" / "tem divergencia aberta?"
- "qual o resultado da conferencia do recebimento 1?"
- "fotos das divergencias"
- "quais chassis do meu ultimo recebimento?"
- "lista recebimentos em andamento"

**NAO USAR PARA:**
- Status de pedido / ciclo de pedido completo -> `acompanhando-pedido`
- Estoque agregado -> `consultando-estoque-loja`
- Historico de 1 chassi -> `rastreando-chassi`
- Pecas faltando (registros com foto) -> `consultando-pecas-faltando`

---

## REGRAS CRITICAS

### 1. RESPEITAR ESCOPO
Filtra `hora_recebimento.loja_id = ANY(loja_ids)`.
Operador de uma loja NAO ve recebimentos de outra.

### 2. CHASSIS ESPERADOS vs CONFERIDOS
- Esperados: `hora_nf_entrada_item WHERE nf_id = recebimento.nf_id`
- Conferidos: `hora_recebimento_conferencia WHERE recebimento_id = X`
- Faltando: esperados - conferidos

### 3. DIVERGENCIAS
`tipo_divergencia` nao-nulo = conferencia com problema.
Expor `detalhe_divergencia` para operador entender.

---

## Invocacao

```bash
python .claude/skills/conferindo-recebimento/scripts/conferindo_recebimento.py \
    --loja-ids 2
    # opcional: --recebimento-id 5
    # opcional: --nf-numero 36612
    # opcional: --somente-abertos
```

---

## Output JSON (exemplo)

```json
{
  "escopo_aplicado": {"loja_ids": [2], "pode_ver_todas": false},
  "total_recebimentos": 1,
  "recebimentos": [
    {
      "id": 1, "status": "ABERTO",
      "loja_id": 2, "loja_apelido": "MOTOCHEFE BRAGANCA",
      "data_recebimento": "2026-04-22",
      "operador": "Rafael",
      "nf": {
        "id": 1, "numero_nf": "36612", "serie_nf": "000",
        "data_emissao": "2026-04-06",
        "nome_emitente": "LAIOUNS..."
      },
      "progresso": {
        "esperados": 22, "conferidos": 1,
        "faltando": 21, "divergencias": 0,
        "percentual_conferido": 4.5
      },
      "ultimas_conferencias": [
        {"numero_chassi": "MC172...", "conferido_em": "2026-04-22T21:50",
         "qr_code_lido": true, "divergencia": null, "operador": "Rafael"}
      ],
      "chassis_faltando": ["MC172...2", "MC172...3", ...],
      "divergencias_abertas": []
    }
  ]
}
```

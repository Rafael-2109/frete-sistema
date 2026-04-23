---
name: rastreando-chassi
description: >-
  Esta skill deve ser usada pelo Agente Lojas HORA quando o usuario pergunta
  sobre o historico de UM chassi especifico: "cade o chassi XYZ?", "onde esta
  o chassi ABC?", "historico completo do chassi X", "essa moto foi vendida?",
  "quando o chassi Y chegou?". Cruza dados de pedido, NF de entrada,
  recebimento, eventos e venda. Respeita escopo da loja via <loja_context>.

  USAR QUANDO:
  - "cade o chassi XYZ?"
  - "historico do chassi MC172..."
  - "essa moto ja foi vendida?"
  - "quando o chassi X chegou?"
  - "em que pedido veio o chassi Y?"

  NAO USAR PARA:
  - Contagem/visao agregada (usar consultando-estoque-loja)
  - Venda B2C (usar registrando-venda — M3)
  - Rastreamento cross-agente Nacom (chassis de caminhao) — nao se aplica
allowed-tools: Read, Bash, Glob, Grep
---

# Rastreando Chassi HORA

Mostra o historico completo de uma moto atraves do chassi, cruzando pedido,
NF de entrada, recebimento, eventos, venda e devolucoes.

---

## Quando Usar Esta Skill

USE para:
- "cade o chassi MC172922511890568?"
- "historico do chassi"
- "essa moto foi vendida?"
- "em que pedido veio essa moto?"

NAO USE para:
- Contagem de estoque -> usar `consultando-estoque-loja`
- Registrar venda/baixa -> skill de M3

---

## REGRAS CRITICAS

### 1. GUARDRAIL ANTI-ALUCINACAO
NAO inferir eventos que nao vieram do script. Se o script diz
`eventos: []`, dizer "nao ha eventos registrados para este chassi".

### 2. RESPEITAR ESCOPO
Se `<loja_context>` indica `pode_ver_todas: false`:
- O script filtra automaticamente: se o chassi nao teve evento
  em loja permitida, retorna `access_denied: true`.
- Operador tentando ver chassi de outra loja recebe 404-like:
  "Chassi nao encontrado no seu escopo".

### 3. ORDEM CRONOLOGICA
Eventos retornam em ORDEM CRONOLOGICA ASCENDENTE. Primeiro evento
= mais antigo. Ultimo = estado atual.

---

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python .claude/skills/rastreando-chassi/scripts/rastreando_chassi.py \
    --loja-ids 2 \
    --chassi MC172922511890568
```

Output: JSON imprimido em stdout com secoes `moto`, `pedido`,
`nf_entrada`, `recebimento`, `eventos`, `venda`, `devolucao`.

---

## Output JSON (exemplo)

```json
{
  "escopo_aplicado": {"loja_ids": [2], "pode_ver_todas": false},
  "encontrado": true,
  "access_denied": false,
  "moto": {
    "numero_chassi": "MC172922511890568",
    "modelo": "PMX", "cor": "preta", "ano_modelo": 2026,
    "numero_motor": "..."
  },
  "pedido": {
    "id": 1, "numero": "P-0001", "status": "recebido",
    "preco_compra_esperado": 8500.00
  },
  "nf_entrada": {
    "id": 1, "numero": "12345", "preco_real": 8500.00
  },
  "recebimento": {
    "id": 1, "loja_id": 2, "conferido_em": "2026-04-22T21:50",
    "operador": "Rafael de Carvalho Nascimento",
    "qr_code_lido": true, "divergencia": null
  },
  "eventos": [
    {"tipo": "RECEBIDA", "loja_id": 2, "timestamp": "2026-04-22T21:50", "operador": "..."}
  ],
  "venda": null,
  "devolucao": null,
  "estado_atual": {
    "status": "estoque",
    "loja_id": 2, "loja_apelido": "MOTOCHEFE BRAGANCA"
  }
}
```

Quando chassi nao existe: `{"encontrado": false, "motivo": "chassi nao cadastrado"}`
Quando fora do escopo: `{"encontrado": true, "access_denied": true, "motivo": "chassi pertence a outra loja"}`

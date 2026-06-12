---
name: rastreando-chassi
description: >-
  Skill READ do Agente Lojas HORA para historico de UM chassi especifico,
  cruzando pedido, NF de entrada, recebimento, eventos e venda. Respeita
  escopo da loja via <loja_context>. Gatilhos: "cade o chassi XYZ?",
  "historico completo do chassi X", "essa moto foi vendida?", "em que pedido
  veio o chassi Y?". NAO usar para contagem/visao agregada ->
  consultando-estoque-loja. Matriz USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# Rastreando Chassi HORA

Mostra o historico completo de uma moto atraves do chassi, cruzando pedido,
NF de entrada, recebimento, eventos, venda e devolucoes.

---

## Quando usar / Quando NAO usar

**USAR QUANDO:**
- "cade o chassi MC172922511890568?" / "onde esta o chassi ABC?"
- "historico do chassi MC172..."
- "essa moto (ja) foi vendida?"
- "quando o chassi X chegou?"
- "em que pedido veio essa moto?"

**NAO USAR PARA:**
- Contagem de estoque / visao agregada -> `consultando-estoque-loja`
- Consultar venda B2C -> `consultando-venda-loja`
- Registrar venda/baixa -> skill de M3
- Rastreamento cross-agente Nacom (chassis de caminhao) — nao se aplica

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

---

## Tipos de evento (`eventos[].tipo`)

Fonte de verdade: `app/hora/services/estoque_service.py`.

- **Em estoque** (`EVENTOS_EM_ESTOQUE`): RECEBIDA, CONFERIDA, TRANSFERIDA,
  CANCELADA (transferencia cancelada), AVARIADA, FALTANDO_PECA,
  EMPRESTIMO_ENTRADA, RESSARCIMENTO_SAIDA.
- **Fora do estoque** (`EVENTOS_FORA_ESTOQUE`): RESERVADA, VENDIDA, DEVOLVIDA,
  NF_EMITIDA, NF_CANCELADA, EMPRESTIMO_SAIDA, RESSARCIMENTO_ENTRADA.
- **Em transito**: EM_TRANSITO (limbo — moto entre lojas).

O `estado_atual` deriva do ULTIMO evento. Eventos mais novos podem aparecer no
estado bruto (ex: "avariada", "em_transito") — sao validos e intermediarios.

---
name: acompanhando-pedido
description: >-
  Skill READ do Agente Lojas HORA para status de pedidos da HORA para a
  Motochefe (ciclo pedido -> NF -> recebimento). Respeita escopo de loja via
  <loja_context>. Gatilhos: "meu pedido X ja chegou?", "pedidos pendentes",
  "pedido 001 esta faturado?", "quais motos faltam receber?". NAO usar para
  conferencia fisica em andamento -> conferindo-recebimento. Matriz
  USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# Acompanhando Pedido HORA

Acompanha o ciclo de um pedido da HORA para a Motochefe: pedido -> NF de
entrada -> recebimento fisico -> conferencia chassi-por-chassi.

---

## Quando usar / Quando NAO usar

**USAR QUANDO:**
- Status de pedidos abertos: "meu pedido 001 ja chegou?", "pedido 001 ta faturado?"
- Lista de pedidos pendentes: "quais pedidos abertos?", "qual pedido ta na
  fila?", "status dos pedidos"
- Qtd declarada vs recebida: "faltam quantas motos do pedido X?", "quais
  motos faltam receber?"
- Acompanhar o ciclo pedido -> NF -> recebimento

**NAO USAR PARA:**
- Estoque agregado -> `consultando-estoque-loja`
- Historico de 1 chassi -> `rastreando-chassi`
- Pecas faltando -> `consultando-pecas-faltando`
- Conferencia fisica em andamento -> `conferindo-recebimento`
- Pedidos Nacom Goya (outro dominio)

---

## REGRAS CRITICAS

### 1. RESPEITAR ESCOPO
`<loja_context>` define filtro em `hora_pedido.loja_destino_id`.
Operador de Tatuape NAO ve pedidos de Braganca.

### 2. QTD DECLARADA vs RECEBIDA
- Declarada: `COUNT(hora_pedido_item WHERE pedido_id=X)`
- Recebida: `COUNT(hora_recebimento_conferencia WHERE recebimento.nf_id IN (NFs do pedido))`

### 3. STATUS DERIVADO
O campo `hora_pedido.status` e a fonte primaria. Mas usar derivacao
secundaria para detalhar:
- Sem NF vinculada -> "aguardando NF"
- Com NF sem recebimento -> "NF recebida"
- Com recebimento aberto -> "em conferencia"
- Todos chassis conferidos sem divergencia -> "conferido ok"
- Conferidos com divergencia -> "conferido com divergencia"

---

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python .claude/skills/acompanhando-pedido/scripts/acompanhando_pedido.py \
    --loja-ids 2
    # opcional: --numero-pedido 001
    # opcional: --somente-abertos
```

---

## Output JSON (exemplo)

```json
{
  "escopo_aplicado": {"loja_ids": [2], "pode_ver_todas": false},
  "pedidos": [
    {
      "id": 1, "numero_pedido": "001",
      "loja_destino_id": 1, "loja_apelido": "MOTOCHEFE TATUAPE",
      "apelido_detectado": "TATUAPE",
      "status": "em conferencia",
      "status_derivado": "em conferencia",
      "data_pedido": "2026-04-20",
      "itens_declarados": 22,
      "nfs": [
        {
          "id": 1, "numero_nf": "36612", "serie_nf": "000",
          "valor_total": 7940.82, "emitente": "LAIOUNS..."
        }
      ],
      "itens_nf_total": 22,
      "recebimentos": [{"id": 1, "status": "aberto", "conferidos": 1, "divergencias": 0}],
      "chassis_conferidos": 1,
      "chassis_faltando": 21,
      "divergencias": 0
    }
  ],
  "total_pedidos": 1
}
```

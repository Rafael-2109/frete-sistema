---
name: carregando-motos-assai
description: >-
  Esta skill deve ser usada para CONSULTAR e OPERAR o carregamento (etapa fisica
  entre Separacao e NF) no modulo Motos Assai (B2B Q.P.A.): "carregamentos em
  andamento", "status do carregamento X", "quantos chassis escaneados", "inicia
  carregamento do pedido P loja L", "escaneia o chassi MZX no carregamento X",
  "finaliza o carregamento X", "cancela o carregamento X", "reabre o carregamento
  X". Modo READ para consultar; modo WRITE (dry-run obrigatorio + --confirmar +
  --user-id) para iniciar/escanear/finalizar/cancelar/alterar.

  USAR QUANDO:
  - "carregamentos em andamento" / "status do carregamento 12"
  - "inicia carregamento do pedido 9 loja 2"
  - "escaneia chassi MZX1234 no carregamento 12"
  - "finaliza/cancela/reabre o carregamento 12"

  NAO USAR PARA:
  - Estoque agregado (usar consultando-estoque-assai)
  - Historico de UM chassi (usar rastreando-chassi-assai)
  - Eventos de moto montagem/disponibilizar/separar (usar registrando-evento-moto-assai)
  - Separacoes / NFs Q.P.A. (usar acompanhando-saida-assai)
  - Conferir recibo Motochefe (usar conferindo-recibo-assai)
allowed-tools: Read, Bash, Glob, Grep
---

# Carregando Motos Assai — carregamento Q.P.A. (READ + WRITE)

Consulta e opera o carregamento (etapa fisica entre Separacao FECHADA e NF Q.P.A.,
escaneia chassi por chassi). Reusa `carregamento_service`.

## REGRAS CRITICAS

### 1. WRITE exige salvaguardas
Operacoes de escrita exigem `--user-id` (valida `pode_acessar_motos_assai()`).
Sem `--confirmar` = **preview dry-run** (nada e alterado). Com `--confirmar` = efetiva.

### 2. Estados
`EM_CARREGAMENTO -> FINALIZADO -> CANCELADO`. `--alterar` reabre FINALIZADO -> EM_CARREGAMENTO
(regride a Separacao vinculada CARREGADA -> FECHADA). CANCELADO nao reabre.

### 3. `finalizar` tem efeito de cadeia
`--finalizar` roda o algoritmo de finalizacao (integra status do pedido + espelho da
separacao no fluxo Nacom). Pode falhar com excedente se escaneou alem do planejado.

## Operacoes

| Op | Args | Tipo |
|----|------|------|
| `--listar` | [`--status` `--pedido-id` `--loja-id` `--separacao-id`] | READ |
| `--detalhar` | `--carregamento-id` | READ |
| `--iniciar` | `--pedido-id` `--loja-id` `--user-id` `--confirmar` | WRITE |
| `--escanear` | `--carregamento-id` `--chassi` `--user-id` `--confirmar` | WRITE |
| `--cancelar-item` | `--item-id` `--user-id` `--confirmar` | WRITE |
| `--finalizar` | `--carregamento-id` `--user-id` `--confirmar` | WRITE |
| `--cancelar` | `--carregamento-id` `--motivo` (>=3) `--user-id` `--confirmar` | WRITE |
| `--alterar` | `--carregamento-id` `--user-id` `--confirmar` | WRITE |

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python .claude/skills/carregando-motos-assai/scripts/carregando_motos_assai.py --listar --loja-id 2
python .claude/skills/carregando-motos-assai/scripts/carregando_motos_assai.py --detalhar --carregamento-id 12
# WRITE: dry-run primeiro, depois --confirmar
python .claude/skills/carregando-motos-assai/scripts/carregando_motos_assai.py --escanear --carregamento-id 12 --chassi MZX1234 --user-id 18
python .claude/skills/carregando-motos-assai/scripts/carregando_motos_assai.py --escanear --carregamento-id 12 --chassi MZX1234 --user-id 18 --confirmar
```

Exit codes: 0 ok · 2 args invalidos · 3 sem autorizacao · 4 dry-run preview · 5 erro de service.

## Skills Relacionadas
| Skill | Quando |
|-------|--------|
| acompanhando-saida-assai | separacoes + NFs Q.P.A. |
| registrando-evento-moto-assai | eventos de moto (montagem/disponibilizar/separar) |
| consultando-estoque-assai | estoque/pipeline agregado |

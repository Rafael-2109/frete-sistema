---
name: conferindo-recibo-assai
description: >-
  Esta skill deve ser usada para operar a conferencia de recibos Motochefe no
  modulo Motos Assai (B2B Q.P.A.): listar recibos pendentes, ver detalhes de
  conferencia (chassis conferidos vs faltantes, divergencias), registrar
  conferencia de chassi (valida modelo/cor + cria evento ESTOQUE) e finalizar
  recibo (marca faltantes como MOTO_FALTANDO). Modo READ para consultar e
  modo WRITE com dry-run obrigatorio para operacoes que mutam dados.

  USAR QUANDO:
  - "quais recibos Q.P.A. pendentes de conferencia?"
  - "status do recibo 12"
  - "registrar conferencia chassi MZX1234 no recibo 12"
  - "finalizar recibo 12 com faltantes"
  - "quantos chassis ja conferidos no recibo 5?"

  NAO USAR PARA:
  - Estoque agregado (usar consultando-estoque-assai)
  - Historico de UM chassi (usar rastreando-chassi-assai)
  - Pedidos VOE / compras Motochefe (usar acompanhando-pedido-compra-assai)
  - Eventos pos-recebimento ESTOQUE->MONTADA->DISPONIVEL (usar registrando-evento-moto-assai)
  - Separacoes / NFs Q.P.A. (usar acompanhando-saida-assai)
  - Recebimento Lojas HORA (usar conferindo-recebimento)
allowed-tools: Read, Bash, Glob, Grep
---

# Conferindo Recibo Motos Assai

Skill READ + WRITE para operar a conferencia de recibos Motochefe (recebimento
fisico no CD da Q.P.A./Sendas/Assai). Cobre listagem de recibos pendentes,
detalhe de conferencia (chassis conferidos vs faltantes, divergencias),
registro de conferencia individual e finalizacao do recibo.

---

## Quando Usar

USE para:
- Listar recibos com status pendente (AGUARDANDO/EM_CONFERENCIA)
- Ver detalhe de UM recibo (itens conferidos, faltantes, divergencias)
- Registrar conferencia de UM chassi (cria/atualiza moto + evento ESTOQUE)
- Finalizar recibo (marca todos faltantes como MOTO_FALTANDO)

NAO USE para:
- Eventos pos-recebimento (MONTADA/DISPONIVEL/PENDENTE) -> `registrando-evento-moto-assai`
- Estoque agregado por modelo -> `consultando-estoque-assai`
- Historico cronologico de 1 chassi -> `rastreando-chassi-assai`

---

## REGRAS CRITICAS

### 1. WRITE EXIGE --user-id + --confirmar
- `--user-id` obrigatorio em qualquer operacao WRITE
- Default e dry-run; precisa `--confirmar` para executar de fato
- User precisa flag `sistema_motos_assai` ou perfil `administrador`

### 2. EXIT CODES
- `0` sucesso (READ ou WRITE confirmado)
- `1` erro de validacao (`RecebimentoValidationError`)
- `2` erro de infraestrutura (DB, app boot)
- `3` usuario nao autorizado (sem permissao)
- `4` confirmacao faltando (dry-run default sem --confirmar)
- `5` conflito 409 (`RecebimentoConflictError`, race condition — pode retry)

### 3. STATUS DO RECIBO
- `RECEBIDO_AGUARDANDO_CONFERENCIA` (estado inicial; nada conferido)
- `EM_CONFERENCIA` (>=1 chassi conferido)
- `CONCLUIDO` (finalizado, zero divergencias)
- `COM_DIVERGENCIA` (finalizado, com >=1 MOTO_FALTANDO/MODELO_DIFERENTE/etc.)

Pendentes = `RECEBIDO_AGUARDANDO_CONFERENCIA` + `EM_CONFERENCIA`.

### 4. RECEBIMENTO COMO SOT
Se cor/modelo conferidos divergem do recibo, o service atualiza
`AssaiMoto.cor`/`modelo_id` (excecao autorizada a invariante 3 do modulo).

---

## Args

### READ (sem mutacao)
- `--listar-pendentes` — recibos com status AGUARDANDO/EM_CONFERENCIA
- `--recibo-id <id>` — detalhe (itens, conferidos, faltantes, divergencias)

### WRITE (com mutacao; exige --user-id e --confirmar)
- `--registrar-chassi --recibo-id <id> --chassi <X> --modelo-id <m> --cor <c> --user-id <u> [--confirmar] [--avaria-fisica]`
- `--finalizar-recibo --recibo-id <id> --user-id <u> [--confirmar] [--confirmar-faltantes]`

`--dry-run` e o comportamento padrao em WRITE; usar `--confirmar` para executar.

---

## Decision Tree

| Pergunta do usuario | Args |
|---------------------|------|
| "recibos pendentes" | `--listar-pendentes` |
| "status do recibo X" | `--recibo-id X` |
| "registrar chassi MZX no recibo 12 modelo SOL cor branca" | `--registrar-chassi --recibo-id 12 --chassi MZX --modelo-id <id> --cor branca --user-id <u> --confirmar` |
| "finalizar recibo 12 com faltantes" | `--finalizar-recibo --recibo-id 12 --user-id <u> --confirmar-faltantes --confirmar` |

---

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
# READ
python .claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py --listar-pendentes
python .claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py --recibo-id 12

# WRITE - dry-run (preview)
python .claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py \
    --registrar-chassi --recibo-id 12 --chassi MZX1234 --modelo-id 3 --cor BRANCA --user-id 5

# WRITE - executar de fato
python .claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py \
    --registrar-chassi --recibo-id 12 --chassi MZX1234 --modelo-id 3 --cor BRANCA --user-id 5 --confirmar
```

Output: JSON em stdout.

---

## Output JSON — READ `--listar-pendentes`

```json
{
  "modo": "listar_pendentes",
  "recibos": [
    {
      "id": 12, "numero_recibo": "RM-2026-0042", "compra_id": 7,
      "status": "EM_CONFERENCIA",
      "data_recibo": "2026-05-07",
      "total_motos_declarado": 30,
      "total_itens": 30,
      "total_conferidos": 18,
      "total_divergencias": 2,
      "criado_em": "2026-05-07T..."
    }
  ],
  "total": 1,
  "exit_code": 0
}
```

---

## Output JSON — READ `--recibo-id`

```json
{
  "modo": "detalhe_recibo",
  "recibo": {
    "id": 12, "numero_recibo": "RM-2026-0042", "compra_id": 7,
    "status": "EM_CONFERENCIA",
    "data_recibo": "2026-05-07",
    "equipe": "HAROLDO SP",
    "conferente_motochefe": "JOAO",
    "total_motos_declarado": 30
  },
  "itens_conferidos": [
    {"id": 1, "chassi": "MZX1234", "modelo_id": 3,
     "modelo_texto_recibo": "SOL", "cor_texto": "BRANCA",
     "conferido": true, "qr_code_lido": true,
     "tipo_divergencia": null, "foto_s3_key": "..."}
  ],
  "itens_faltantes": [
    {"id": 2, "chassi": "MZX5678", "modelo_id": 3,
     "modelo_texto_recibo": "SOL", "cor_texto": "BRANCA",
     "conferido": false, "tipo_divergencia": null}
  ],
  "totais": {
    "declarado": 30, "no_recibo": 30, "conferidos": 18, "faltantes": 12,
    "divergencias": 2
  },
  "exit_code": 0
}
```

---

## Output JSON — WRITE dry-run (default sem --confirmar)

```json
{
  "modo": "registrar_chassi",
  "dry_run": true,
  "preview": {
    "recibo_id": 12, "chassi": "MZX1234",
    "modelo_id": 3, "cor": "BRANCA",
    "user_id": 5
  },
  "mensagem": "Dry-run. Use --confirmar para executar de fato.",
  "exit_code": 4
}
```

---

## Output JSON — WRITE confirmado (sucesso)

```json
{
  "modo": "registrar_chassi",
  "dry_run": false,
  "ok": true,
  "item_id": 245,
  "chassi": "MZX1234",
  "tipo_divergencia": null,
  "exit_code": 0
}
```

---

## Output JSON — WRITE conflito 409

```json
{
  "modo": "registrar_chassi",
  "ok": false,
  "error": "Chassi MZX1234 ja conferido — atualize a tela",
  "retry": true,
  "exit_code": 5
}
```

---

## Output JSON — WRITE finalizar com faltantes

```json
{
  "modo": "finalizar_recibo",
  "dry_run": false,
  "ok": false,
  "error": "12 chassis nao conferidos. Confirme MOTO_FALTANDO ou continue conferindo.",
  "hint": "Reexecute com --confirmar-faltantes",
  "exit_code": 1
}
```

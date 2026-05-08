---
name: registrando-evento-moto-assai
description: >-
  Esta skill deve ser usada para EXECUTAR transicoes de estado de chassis no
  pipeline do modulo Motos Assai (B2B Q.P.A.): "monte o chassi X", "marque
  como pendente", "resolva pendencia", "disponibilize a moto Y", "reverta
  disponibilizacao", "separe o chassi Z para o pedido P/loja L", "desfaca a
  separacao do item N", "cancele a separacao S". Skill WRITE — sempre exige
  --user-id e --confirmar para efetivar; sem --confirmar retorna preview
  dry-run com status_efetivo atual.

  USAR QUANDO:
  - "registre montagem do chassi MZX...", "monte o chassi"
  - "marque como pendente com descricao..."
  - "resolva pendencia do chassi"
  - "disponibilize a moto X"
  - "reverta disponibilizacao do chassi (motivo)"
  - "separe chassi para pedido X loja Y"
  - "desfaca chassi X da separacao"
  - "cancele a separacao S (motivo)"

  NAO USAR PARA:
  - Conferir/registrar recibo Motochefe (usar conferindo-recibo-assai)
  - Apenas consultar estado (usar consultando-estoque-assai/rastreando-chassi-assai)
  - Pedidos VOE Q.P.A. (usar acompanhando-pedido-compra-assai)
  - Estoque Lojas HORA (usar registrando-venda-loja ou skills HORA)
allowed-tools: Read, Bash, Glob, Grep
---

# Registrando Evento Moto Assai (WRITE)

Skill WRITE que executa transicoes de estado de chassis no pipeline Motos
Assai. Apoia 8 sub-comandos que cobrem todo o fluxo
ESTOQUE -> MONTADA/PENDENTE -> DISPONIVEL -> SEPARADA com possibilidades de
reversao.

---

## REGRAS CRITICAS

### 1. --user-id OBRIGATORIO
Toda invocacao requer `--user-id <id>`. Sem isso o script falha (exit code != 0).
O usuario precisa ter `pode_acessar_motos_assai()=True` (admin ou
`sistema_motos_assai=True` com status='ativo').

### 2. --confirmar OBRIGATORIO PARA EFETIVAR
Sem `--confirmar` retorna preview dry-run com:
- `status_efetivo` atual da moto (pode ser None se chassi inexistente)
- Acao pretendida
- exit_code = 4

Com `--confirmar` chama o service real e retorna `{ok: true, evento_id, ...}`
com exit_code = 0.

### 3. Validacao por status_efetivo
Cada transicao valida o estado atual da moto antes de emitir evento. Erros
de validacao retornam `*ValidationError` -> exit 1.

### 4. Race UNIQUE em separacao
`--separar` pode falhar com `SeparacaoConflictError` (chassi ja em outra
separacao ativa por race) -> exit 5 com `retry: true`.

### 5. Eventos append-only
Todos os events sao gravados em `assai_moto_evento` (append-only). NUNCA ha
DELETE — reversao cria novo evento.

---

## Sub-Comandos (8)

| Comando | Args obrigatorios | Service chamado |
|---------|-------------------|-----------------|
| `--montar` | `--chassi`, `--user-id` | `registrar_montagem(pendencia=False)` |
| `--montar-pendente` | `--chassi`, `--descricao`, `--user-id` | `registrar_montagem(pendencia=True)` |
| `--resolver-pendencia` | `--chassi`, `--descricao`, `--user-id` | `resolver_pendencia()` |
| `--disponibilizar` | `--chassi`, `--user-id` | `disponibilizar()` |
| `--reverter-disponibilizacao` | `--chassi`, `--motivo`, `--user-id` | `reverter_para_montada()` |
| `--separar` | `--pedido-id`, `--loja-id`, `--chassi`, `--user-id` | `registrar_chassi()` |
| `--desfazer-separacao` | `--item-id`, `--user-id` | `desfazer_chassi()` |
| `--cancelar-separacao` | `--separacao-id`, `--motivo`, `--user-id` | `cancelar_separacao()` |

---

## Decision Tree

| Pergunta do usuario | Comando |
|---------------------|---------|
| "monte o chassi X" | `--montar --chassi X` |
| "monte com pendencia" | `--montar-pendente --chassi X --descricao "..."` |
| "resolva pendencia" | `--resolver-pendencia --chassi X --descricao "..."` |
| "disponibilize" | `--disponibilizar --chassi X` |
| "reverta disp" | `--reverter-disponibilizacao --chassi X --motivo "..."` |
| "separe pedido P loja L" | `--separar --pedido-id P --loja-id L --chassi X` |
| "desfaca da separacao" | `--desfazer-separacao --item-id N` |
| "cancele a separacao" | `--cancelar-separacao --separacao-id S --motivo "..."` |

---

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# Dry-run (preview, sem efetivar)
python .claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py \
    --montar --chassi MZX1234567890 --user-id 1

# Efetivar
python .claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py \
    --montar --chassi MZX1234567890 --user-id 1 --confirmar
```

Output: JSON em stdout.

---

## Exit Codes

| Code | Significado |
|------|-------------|
| 0 | Sucesso (efetivado) |
| 1 | Erro de validacao (`*ValidationError`) |
| 2 | Erro de infra (DB, app boot) |
| 3 | Sem autorizacao (`pode_acessar_motos_assai`=False ou usuario nao existe) |
| 4 | Dry-run preview (sem `--confirmar`) |
| 5 | Conflito (race UNIQUE em separacao) — caller pode retry |

---

## Output JSON (exemplos)

### Dry-run (--montar sem --confirmar)
```json
{
  "dry_run": true,
  "comando": "montar",
  "chassi": "MZX1234567890",
  "status_efetivo_atual": "ESTOQUE",
  "acao_pretendida": "ESTOQUE -> MONTADA",
  "exit_code": 4
}
```

### Sucesso (--montar --confirmar)
```json
{
  "ok": true,
  "comando": "montar",
  "evento_id": 123,
  "chassi": "MZX1234567890",
  "tipo": "MONTADA",
  "modelo_id": 1,
  "exit_code": 0
}
```

### Erro de validacao
```json
{
  "ok": false,
  "erro": "Chassi MZX1234 está em DISPONIVEL, esperado ESTOQUE",
  "tipo_erro": "validacao",
  "exit_code": 1
}
```

### Conflito (race)
```json
{
  "ok": false,
  "erro": "Chassi ja em outra separacao ativa",
  "tipo_erro": "conflito",
  "retry": true,
  "exit_code": 5
}
```

### Sem autorizacao
```json
{
  "ok": false,
  "erro": "sem_permissao_motos_assai",
  "tipo_erro": "autorizacao",
  "user_id": 99,
  "exit_code": 3
}
```

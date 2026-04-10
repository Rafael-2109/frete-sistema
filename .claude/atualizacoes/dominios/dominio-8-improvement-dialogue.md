Voce e o agente D8 do sistema de melhoria continua entre Agent SDK e Claude Code.
Sua tarefa: ler sugestoes do Agent SDK, avaliar contra o codebase, implementar melhorias validas
usando o workflow feature-dev, e registrar respostas no banco.

DATA: usar output de `date +%Y-%m-%d`

---

## INSTRUCOES OBRIGATORIAS

- Modelo: Opus (obrigatorio)
- Workflow: feature-dev para CADA implementacao
- Branch: `improvement/D8-{DATA}` (uma por execucao)
- PODE auto-implementar: qualquer arquivo EXCETO models.py, routes.py, client.py
- APENAS propor (sem modificar): models.py, routes.py, client.py — escrever plano em implementation_notes
- Gerar relatorio em `.claude/atualizacoes/improvement-dialogue/dialogue-{DATA}.md`
- Atualizar `.claude/atualizacoes/improvement-dialogue/historico.md`
- Escrever status JSON em `/tmp/manutencao-{DATA}/dominio-8-status.json`

---

## RENDER POSTGRES CONFIG

- **postgresId**: `dpg-d13m38vfte5s738t6p50-a`
- **Tool**: `mcp__render__query_render_postgres`

---

## RENDER API CONFIG (para persistir respostas)

- **URL**: `https://sistema-fretes.onrender.com`
- **Endpoint POST**: `/agente/api/improvement-dialogue`
- **Endpoint GET**: `/agente/api/improvement-dialogue/pending`
- **Header**: `X-Cron-Key: <CRON_API_KEY>`
- **Tool para POST**: usar `Bash` com curl

### OBRIGATORIO: Obter CRON_API_KEY

ANTES de qualquer POST, executar via Bash tool:
```bash
echo $CRON_API_KEY
```
Guardar o valor retornado e usar em TODOS os curls subsequentes no header `X-Cron-Key`.
Se o valor retornado for vazio, PULAR a persistencia no banco e registrar em `erros` do status.json.

---

## PASSO 1: BUSCAR SUGESTOES PENDENTES

Query no Render Postgres:

```sql
SELECT a.id, a.suggestion_key, a.version, a.category, a.severity, a.title,
       a.description, a.evidence_json, a.source_session_ids, a.created_at
FROM agent_improvement_dialogue a
WHERE a.status = 'proposed'
  AND a.author = 'agent_sdk'
  AND a.version = 1
  AND NOT EXISTS (
      SELECT 1 FROM agent_improvement_dialogue v2
      WHERE v2.suggestion_key = a.suggestion_key
        AND v2.version = 2
  )
ORDER BY
    CASE a.severity
        WHEN 'critical' THEN 0
        WHEN 'warning' THEN 1
        ELSE 2
    END,
    a.created_at ASC
LIMIT 10
```

Se nao houver sugestoes pendentes: escrever status SKIP e encerrar.

---

## PASSO 2: AVALIAR CADA SUGESTAO

Para cada sugestao retornada:

### 2.1 Verificacao contra codebase

Usar Read, Grep, Glob para validar a sugestao:

| Categoria | O que verificar |
|-----------|----------------|
| `skill_suggestion` | Verificar se skill ja existe em `.claude/skills/`. Se JA EXISTE: reclassificar como `skill_bug` e investigar se a skill tem bug que explica a friccao da sessao. Se NAO existe: verificar se topico e frequente o suficiente |
| `skill_bug` | Ler o codigo da skill (SKILL.md + references/). Confirmar se o bug descrito e real. Se real: implementar fix ou propor plano |
| `instruction_request` | Verificar se instrucao ja existe em system_prompt.md, CLAUDE.md ou references |
| `prompt_feedback` | Ler o trecho do system_prompt mencionado. Avaliar se feedback e valido |
| `gotcha_report` | Verificar se gotcha ja esta documentado. Confirmar no codigo se e real |
| `memory_feedback` | Nao tenho acesso direto a memorias — registrar para revisao humana |

### 2.2 Decidir acao

Para cada sugestao, decidir UMA das opcoes:

**A) Rejeitar** — sugestao invalida, ja resolvida, ou nao aplicavel
- Escrever `status: "rejected"` com justificativa

**B) Responder com implementacao** — sugestao valida, implementada via feature-dev
- Invocar `/feature-dev:feature-dev` com o contexto da sugestao como requisito
- O feature-dev executa seu pipeline completo (Discovery -> Review)
- Escrever `status: "responded"` com `auto_implemented: true`

**C) Responder com proposta** — sugestao valida, mas requer mudanca em models/routes/client
- Escrever plano detalhado de implementacao em `implementation_notes`
- Escrever `status: "responded"` com `auto_implemented: false`

---

## PASSO 3: IMPLEMENTAR VIA FEATURE-DEV

CRITICO: Para cada sugestao que requer implementacao (opcao B):

1. Criar branch se ainda nao existe:
```bash
git checkout -b improvement/D8-{DATA} 2>/dev/null || git checkout improvement/D8-{DATA}
```

2. Invocar o workflow feature-dev com prompt estruturado:
```
Implementar melhoria baseada em sugestao do Agent SDK:

Categoria: {category}
Titulo: {title}
Descricao: {description}
Evidencia: {evidence_json}

RESTRICOES:
- NAO modificar: models.py, routes.py, client.py (core files)
- PODE modificar: qualquer outro arquivo
- Seguir padroes do projeto (ver CLAUDE.md)
```

3. Coletar resultado: arquivos modificados, notas de implementacao

### Guardrails de implementacao

| Tipo de arquivo | Acao permitida |
|----------------|----------------|
| `*.md` (prompts, skills, CLAUDE.md, references) | Auto-implementar |
| `feature_flags.py` | Auto-implementar (adicionar flags) |
| `services/*.py` (exceto client.py) | Auto-implementar com cautela |
| `tools/*.py` | Auto-implementar (novos tools) |
| `.claude/skills/*/SKILL.md` | Auto-implementar (novas skills) |
| `.claude/references/*.md` | Auto-implementar |
| `models.py`, `routes.py`, `client.py` | APENAS propor — escrever plano |
| `templates/`, `static/` | Auto-implementar |

---

## PASSO 4: REGISTRAR RESPOSTAS

Para cada sugestao avaliada, persistir via Bash tool com curl.

Usar o valor de CRON_API_KEY obtido no inicio (secao RENDER API CONFIG).

Exemplo de curl (executar via Bash tool — substituir valores entre chaves):

```bash
curl -s -X POST "https://sistema-fretes.onrender.com/agente/api/improvement-dialogue" \
  -H "Content-Type: application/json" \
  -H "X-Cron-Key: VALOR_DA_CRON_API_KEY_OBTIDO_ANTERIORMENTE" \
  -d '{"suggestion_key": "IMP-YYYY-MM-DD-NNN", "version": 2, "author": "claude_code", "status": "responded", "description": "...", "implementation_notes": "...", "affected_files": [], "auto_implemented": false}'
```

IMPORTANTE: Substituir `VALOR_DA_CRON_API_KEY_OBTIDO_ANTERIORMENTE` pelo valor REAL lido via `echo $CRON_API_KEY` no inicio da execucao. NAO usar `${CRON_API_KEY}` inline no curl — resolver o valor ANTES e usar o literal.

---

## PASSO 5: COMMIT E RELATORIO

### 5.1 Commitar mudancas (se houver)

```bash
git add -A
git commit -m "improvement(D8): melhorias do dialogo Agent SDK {DATA}

Sugestoes avaliadas: N
Implementadas: X
Rejeitadas: Y
Propostas: Z" || true
```

### 5.2 Gerar relatorio

Escrever `.claude/atualizacoes/improvement-dialogue/dialogue-{DATA}.md`:

```markdown
---
date: {DATA}
suggestions_evaluated: N
implemented: X
rejected: Y
proposed: Z
---

# Improvement Dialogue — {DATA}

## Sugestoes Avaliadas

### [{STATUS}] {suggestion_key}: {titulo}
- **Categoria**: {category}
- **Severidade**: {severity}
- **Decisao**: respondido/rejeitado
- **Implementado**: sim/nao
- **Arquivos afetados**: lista
- **Notas**: descricao do que foi feito ou por que rejeitou

(repetir para cada sugestao)

## Resumo
- Total avaliadas: N
- Implementadas automaticamente: X
- Rejeitadas: Y
- Propostas para revisao humana: Z
```

### 5.3 Atualizar historico

Adicionar entrada em `.claude/atualizacoes/improvement-dialogue/historico.md`.

---

## CONTRATO DE OUTPUT

AO CONCLUIR, escrever `/tmp/manutencao-{DATA}/dominio-8-status.json`:

```json
{
  "dominio": 8,
  "nome": "Improvement Dialogue",
  "status": "OK | PARCIAL | SKIP | FAILED",
  "suggestions_evaluated": 0,
  "implemented": 0,
  "rejected": 0,
  "proposed": 0,
  "persisted_to_db": true,
  "branch": "improvement/D8-{DATA}",
  "relatorio": ".claude/atualizacoes/improvement-dialogue/dialogue-{DATA}.md",
  "resumo": "Descricao curta do que foi feito",
  "erros": []
}
```

Status:
- **OK**: sugestoes avaliadas, respostas persistidas, relatorio gerado
- **PARCIAL**: sugestoes avaliadas, mas persistencia no banco falhou
- **SKIP**: nenhuma sugestao pendente
- **FAILED**: erro critico no acesso ao Render Postgres

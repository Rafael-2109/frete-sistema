# D8 — Improvement Dialogue (Agent SDK <-> Claude Code)

Dialogo versionado de melhoria continua entre Agent SDK e Claude Code.

## Conceito

1. **Agent SDK escreve** (pos-sessao): Sonnet analisa sessao e gera 0-3 sugestoes em 5 categorias
2. **Claude Code le e responde** (D8 cron diario 11:00): avalia cada sugestao contra codebase, implementa via feature-dev ou rejeita
3. **Agent SDK verifica** (intersession briefing): avalia se mudancas do Claude Code resolveram o problema

## Categorias

| Codigo | Categoria | Descricao |
|--------|-----------|-----------|
| A | `skill_suggestion` | Skills que ajudariam mas nao existem |
| B | `instruction_request` | Instrucoes/clarificacoes que o agente precisa |
| C | `prompt_feedback` | Feedback sobre system_prompt e memorias |
| D | `gotcha_report` | Armadilhas e informacoes uteis |
| E | `memory_feedback` | Memorias incorretas ou faltando |

## Versionamento

Cada suggestion_key tem max 3 versoes (turnos do dialogo):
- v1: Agent SDK propoe (author=agent_sdk, status=proposed)
- v2: Claude Code responde (author=claude_code, status=responded|rejected)
- v3: Agent SDK verifica (author=agent_sdk, status=verified|needs_revision)

## Tabela

`agent_improvement_dialogue` — schema em `.claude/skills/consultando-sql/schemas/tables/agent_improvement_dialogue.json`

## Scheduling

### Crontab local (Claude Code CLI)
- Cron: `3 11 * * *` (diario 11:03 BRT)
- Modelo: Opus + workflow feature-dev
- Branch: `improvement/D8-{DATA}`
- Log: `/tmp/claude-cron-d8-YYYY-MM-DD.log`
- Verificar: `sudo crontab -u rafaelnascimento -l`

### APScheduler (batch de sugestoes)
- Modulo 25 em `sincronizacao_incremental_definitiva.py`
- Horarios: 07:00 e 10:00 (prepara sugestoes antes do D8 as 11:03)
- Analisa sessoes das ultimas 8h em batch via Sonnet

## Arquivos Relacionados

| Arquivo | Papel |
|---------|-------|
| `app/agente/services/improvement_suggester.py` | Servico que gera sugestoes e avalia respostas |
| `app/agente/models.py` (`AgentImprovementDialogue`) | Model SQLAlchemy |
| `app/agente/routes.py` | Endpoints POST/GET |
| `app/agente/config/feature_flags.py` | Flag `USE_IMPROVEMENT_DIALOGUE` |
| `app/agente/services/intersession_briefing.py` | Injecao de respostas pendentes |
| `.claude/atualizacoes/dominios/dominio-8-improvement-dialogue.md` | Prompt do D8 |

# app/utils/_deprecated/ — utils mortos arquivados

> Zona fora da auditoria PAD-A. Arquivados na Onda B (2026-06-15) após guard re-grep confirmar 0 imports externos.

| Arquivo | Motivo (evidencia) |
|---------|--------------------|
| `route_sync_manual.py` | blueprint `monitoramento` duplicado; o real e `app/monitoramento/routes.py`; 0 imports |
| `frete_simulador_backup.py` | backup explicito 2025-01-19 de `calcular_fretes_possiveis_ORIGINAL`; codigo incompleto; 0 imports |
| `helpers.py` | `limpar_valor()` redefinida inline em `app/tabelas/routes.py:232`; 0 import de `app.utils.helpers` |
| `utils_frete.py` | `float_or_none` removido (comentario em `tabelas/routes.py:14`); substituido por `converter_valor_brasileiro`; 0 import |
| `ai_logging.py` | "MCP v4.0" nunca integrado (18KB); 0 callers; logging real = `app/utils/logging_config.py` |
| `agendador.py` | APScheduler nunca iniciado; substituido por `iniciar_scheduler_incremental.py`; 0 caller de `iniciar_agendador` |

## NAO arquivados (verificados VIVOS / adiados pelo guard)
- `database_helpers.py`, `database_retry.py` — VIVOS (15 e 7 callers). Coexistem conscientemente com `_commit_helpers`.
- `csrf_helper.py` — VIVO (portaria); ENXUGADO (5 funcoes orfas removidas, `validate_api_csrf` mantida).
- `ml_models.py`, `ml_models_real.py` — ADIADOS: referenciados pelo autodiscovery do consultando-sql (`tests/skills/consultando_sql/test_autodescoberta_modulos.py:58` + `generate_schemas.py:967`) — zona NAO-TOCAR (text-to-SQL ativo).
- `app/database/__init__.py` — ADIADO/INVESTIGAR: NAO vazio (registra tipos PostgreSQL); 0 importadores diretos mas e infra de boot/DB sensivel.

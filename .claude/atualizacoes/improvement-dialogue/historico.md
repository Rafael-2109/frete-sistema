# Historico — D8 Improvement Dialogue

Indice de execucoes do dialogo de melhoria Agent SDK <-> Claude Code.

| # | Data | Avaliadas | Implementadas | Rejeitadas | Propostas | Status |
|---|------|-----------|---------------|------------|-----------|--------|
| 1 | 2026-04-01 | 4 | 1 | 2 | 1 | PARCIAL (CSRF no POST) |
| 2 | 2026-04-02 | 8 | 0 | 6 | 2 | PARCIAL (permissoes + sem CRON_API_KEY) |
| 3 | 2026-04-03 | 8 | 2 | 5 | 1 | OK |
| 4 | 2026-04-07 | 4 | 2 | 1 | 1 | PARCIAL (permissoes + sem CRON_API_KEY) |

## 2026-04-07
- **Branch**: improvement/D8-2026-04-07
- IMP-2026-04-07-002: R0 auto_save — adicionado enfase de timing (salvar IMEDIATAMENTE)
- IMP-2026-04-07-003: R0d scope_awareness — nova regra para evitar reutilizacao de contexto errado
- IMP-2026-04-07-001: rejeitado (save_memory ja trata PermissionError)
- IMP-2026-04-06-001: proposta regex fix (permissao negada)

## 2026-04-03
- **Branch**: improvement/D8-2026-04-03
- IMP-007/008: Sit 2 auto-escala para 2b + payment_ref preservado em narration
- IMP-001: proposta para deteccao de falha sistematica em client.py
- IMP-002/003/004: rejeitados (funcionalidade ja existe)
- IMP-005/006: rejeitados (supersedidos por 007/008)

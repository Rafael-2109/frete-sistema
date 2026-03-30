# Manutencao Semanal Consolidada — 2026-03-30

**Data**: 2026-03-30
**Dominios executados**: 7
**Dominios OK**: 3 | **PARCIAL**: 4 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 8/9 CLAUDE.md atualizados. LOC/arquivos corrigidos. Data 30/03/2026. Modulo pedidos adicionado. |
| 2 | References Audit | PARCIAL | P0-P2 revisados. 2 fixes identificados mas nao aplicados (permissao .claude/) |
| 3 | Memorias Cleanup | PARCIAL | 24/24 auditadas. 4 consolidadas em 2. 6 trimadas (~76% reducao). MEMORY.md 67 linhas. |
| 4 | Sentry Triage | OK | 42 issues avaliadas, 0 corrigiveis. 39 XML-RPC Faults Odoo, 2 transientes, 1 migration. |
| 5 | Test Runner | OK | 204/204 testes PASSED em 11.22s. Suite 100% verde. |
| 6 | Memory Eval | PARCIAL | Health score 79/100. Queries OK. Relatorio nao escrito (permissao). |
| 7 | Agent Intelligence Report | PARCIAL | Queries executadas. Relatorio nao persistido (permissao). |

## Metricas

### CLAUDE.md (D1)
- Arquivos auditados: 9/9, modificados: 8
- Atualizacoes: contagens LOC (agente 25.6K, carvia 33.3K/52arqs/77templates, financeiro 70arqs, odoo 18.3K)
- Novo modulo: pedidos adicionado ao CAMINHOS DO SISTEMA
- Novo util: cached_lookups.py documentado no odoo/CLAUDE.md

### References (D2)
- Arquivos revisados: ~30 (P0-P2 completo, P3-P4 scan)
- Fixes pendentes (permissao bloqueou):
  1. QUERIES_MAPEAMENTO.md:55 — qtd_saldo para qtd_saldo_produto_pedido
  2. PADROES_AVANCADOS.md:37,40,48 — 3x datetime.utcnow() para datetime.now()

### Memorias (D3)
- Auditadas: 24, removidas: 4, consolidadas: 4 em 2, trimadas: 6
- Reducao de volume: ~2300 linhas para ~550 linhas (76%)
- MEMORY.md: 67 linhas (limite: 150)

### Sentry (D4)
- Issues avaliadas: 42, corrigidas: 0, ignoradas: 42
- 39 Odoo XML-RPC Faults (infra externa)
- 1 migration pendente (PYTHON-FLASK-K)
- 0 usuarios afetados

### Tests (D5)
- Total: 204, passed: 204, failed: 0, taxa: 100%
- Tempo total: 11.22s

### Memory Eval (D6)
- Health score: 79/100

### Agent Intelligence Report (D7)
- 8 queries executadas no Render Postgres

## Erros e Falhas

### Problema recorrente: Permissao .claude/
Sandbox trata .claude/ como sensivel. Relatorios detalhados salvos em /tmp/manutencao-2026-03-30/.
Recomendacao: revisar configuracao de permissoes para .claude/atualizacoes/ em futuras execucoes.

### Fixes pendentes (D2)
1. .claude/references/modelos/QUERIES_MAPEAMENTO.md:55 — qtd_saldo para qtd_saldo_produto_pedido
2. .claude/references/odoo/PADROES_AVANCADOS.md:37,40,48 — datetime.utcnow() para datetime.now()

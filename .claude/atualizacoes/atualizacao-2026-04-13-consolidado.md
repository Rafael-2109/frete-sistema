# Manutencao Semanal Consolidada — 2026-04-13

**Data**: 2026-04-13
**Dominios executados**: 7
**Dominios OK**: 4 | **PARCIAL**: 3 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | PARCIAL | 9/9 auditados, 1 corrigido (CarVia templates 87->93). Relatorio/historico nao escritos (permissao). |
| 2 | References Audit | PARCIAL | 37 arquivos revisados (P0-P4). 1 caminho quebrado, 4 line numbers defasados. Versoes OK. |
| 3 | Memorias Cleanup | OK | 20 memorias auditadas, 2 atualizadas. MEMORY.md 65 linhas, frontmatter 20/20 OK. |
| 4 | Sentry Triage | OK | 26 issues avaliadas, 2 resolvidas no Sentry (fixes ja existiam). 0 arquivos modificados. |
| 5 | Test Runner | OK | 329/329 testes OK (100%), 16.10s. +41 testes vs anterior. |
| 6 | Memory Eval | OK | Health score 84/100 (+3). 197 memorias, 391 sessoes, 21 usuarios. 7 recomendacoes. |
| 7 | Agent Intelligence Report | PARCIAL | Health score 74/100 (+29pts). Resolution rate 36.7%->71.0%. DB persistence nao tentada. |

## Metricas

### CLAUDE.md (D1)
- Arquivos auditados: 9/9, modificados: 1
- Divergencia corrigida: CarVia template count (87->93)

### References (D2)
- Arquivos revisados: 37, corrigidos: 0 (permissao negada)
- Divergencias: REGRAS_MODELOS.md (path cadastros->cadastros_agendamento), REGRAS_CARTEIRA_SEPARACAO.md (4 line numbers)
- Versoes de dependencias: todas corretas

### Memorias (D3)
- Auditadas: 20 memorias, atualizadas: 2 (skills_inventario 5->23, ssw_operacoes 11->18)
- MEMORY.md: 65 linhas (limite: 150), frontmatter: 20/20 corretos

### Sentry (D4)
- Issues avaliadas: 26, resolvidas: 2, ignoradas: 11, fora de escopo: 13

### Tests (D5)
- Total: 329, passed: 329, failed: 0, taxa: 100%, tempo: 16.10s

### Memory Eval (D6)
- Health score: 84/100, memorias: 197, cold: 15 (7.6%), stale 60d: 2 (1.0%), KG coverage: 52.8%

### Agent Intelligence Report (D7)
- Health score: 74/100 (+29), sessoes: 169, resolution rate: 71.0%, trend: improving
- Outlier: sessao USD 128.62 (conciliacao transferencias, 269 msgs)
- Skill gaps: frete (21), separacao (18), nota_fiscal (13)

## Erros e Falhas

### D1, D2 (PARCIAL)
- Subagentes nao conseguiram escrever relatorios/historicos por restricao de permissao

### D7 (PARCIAL)
- Persistencia no banco nao tentada (subagente sem acesso a Bash/curl)
- Correcoes pendentes D2: REGRAS_MODELOS.md e REGRAS_CARTEIRA_SEPARACAO.md

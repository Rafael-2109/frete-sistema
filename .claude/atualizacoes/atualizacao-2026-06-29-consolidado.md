# Manutencao Semanal Consolidada — 2026-06-29

**Data**: 2026-06-29
**Dominios executados**: 7
**Dominios OK**: 6 | **PARCIAL**: 1 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9 auditados, 6 modificados (carvia, financeiro, agente, odoo, raiz + tree carvia/financeiro). Caminhos novos verificados; tech stack confere requirements.txt. |
| 2 | References Audit | OK | 47 arquivos P0-P2 revisados, 5 corrigidos, 0 caminhos quebrados. C8 global: 7 orfaos -> 7 corrigidos (docs/superpowers wirados). |
| 3 | Memorias Cleanup | OK | 187 auditadas, 0 removidas (todos os 10 candidatos com trabalho em aberto). MEMORY.md 72 linhas. Estrutura impecavel. |
| 4 | Sentry Triage | OK | 46 issues avaliadas, 2 corrigidas (1 fix novo + 1 ja-corrigida), 43 documentadas, 1 fora de escopo. |
| 5 | Test Runner | PARCIAL | 5456 testes: 5417 passed / 4 failed / 35 skipped (99.93%). As 4 falhas sao meta-testes de toolchain/flag-drift, nao logica de negocio. Sem correlacao com D4. |
| 6 | Memory Eval | OK | Health 86/100 (estavel). 850 memorias, 1019 sessoes, 31 usuarios. 7 recomendacoes. KG linking parado (R1 P0). |
| 7 | Agent Intelligence Report | OK | Health 66 (+2), friction 39 (-3), trend improving. 303 sessoes, 11 recs, 10 backlog. Persistido no banco (report_id 9). |

## Metricas

### CLAUDE.md
- Arquivos auditados: 9/9, modificados: 6 (carvia, financeiro, agente, odoo, raiz; +tree carvia/financeiro)
- Intocados por consistencia 100%: carteira, seguranca, teams

### References
- Arquivos revisados (P0-P2): 47, corrigidos: 5
- Caminhos quebrados: 0
- C8 (alcancabilidade global): 7 orfaos -> 7 corrigidos (5 plans/specs em docs/superpowers/ wirados + doc:meta + correcao C5/C6 induzida)

### Memorias
- Auditadas: 187, removidas: 0, consolidadas: 0, atualizadas: 0
- MEMORY.md: 72 linhas (teto 150), 9.9KB
- 0 links quebrados, 0 orfaos, frontmatter 187/187 OK

### Sentry
- Issues avaliadas: 46, corrigidas: 2, ignoradas/documentadas: 43, fora de escopo: 1
- Fix novo: `consultar_quants.py` (Z8 — json.dumps com chave-tupla no dict agregado; achatado em `cod|empresa` so no ramo JSON, reproduzido e verificado)
- Ja-corrigida: Z2 (regressao do fix `_to_decimal_safe`, evento de release anterior ao deploy)
- Destaque documentado: cluster de 1 migration pendente `veiculos.custo_km` (6 issues, ~57 eventos)

### Tests
- Total: 5456, passed: 5417, failed: 4, error: 0, skipped: 35, taxa: 99.93%
- Correlacoes com D4: 0 (todos os testes que exercitam `consultar_quants.py` passaram)
- Ciclo muito mais saudavel: 4 falhas vs 89-137 nos ciclos anteriores; falhas cronicas de DB-state pollution sumiram
- As 4 falhas (meta-testes, nao negocio):
  1. `test_default_da_flag_judge_source_e_off` — drift env var `AGENT_DIRECTIVE_JUDGE_SOURCE` em `feature_flags.py`
  2. `test_infra_evolution_flags_confronta_feature_flags` — drift env var `AGENT_CAPABILITY_REGISTRY` em `feature_flags.py`
  3. `test_doc_audit_report_only_roda` — timeout >60s do `doc_audit.py` (near-dup O(n^2), reincidente do ciclo 06-08)
  4. `test_c6_zerado_apos_isencao_skill_md` — 3 docs sem TOC (DESIGN.md, `app/agente/services/CLAUDE.md`, `docs/roteirizacao/ESTADO.md`)

### Memory Eval (Producao)
- Health score: 86/100 (estavel vs 06-22)
- Total memorias: 850 (+120), cold: 107 (12.59%), stale 60d: 22 (2.59%)
- Sessoes: 1019 (marco de 1000), usuarios unicos: 31 (28 ativos 30d)
- Eficacia 0.812, correcoes 0.382 (subindo)
- Recomendacoes: 7 (R1 P0 = backfill KG linking — pipeline parado ha 3 ciclos, coverage 28.8%; empresa 70.4% nunca revisada, recorde 11o ciclo)

### Agent Intelligence Report
- Health score: 66/100 (+2)
- Sessoes analisadas: 303, friction score: 39 (-3)
- Recomendacoes: 11 (2 critical), backlog: 10 itens
- Trend: **improving** (resolution sobe 3a semana: 73.9%; custo estavel ~$320/sem; no_tools minimo 2.3%)
- Persistido no banco: SIM (report_id 9, HTTP 200)
- Criticos: memoria nociva u18 (4a semana, eficacia 0.0/8 correcoes) + cluster u78 Motos Assai (3 memorias eficacia-0)
- Gap novo: import estruturado de NF Motos Assai (outlier $115.30/140msgs, sessao travada por OOM Gunicorn)

## Erros e Falhas

- **D5 (PARCIAL)**: 4 testes falharam — todos meta-testes de toolchain/lint/flag-drift, nenhum de logica de negocio (detalhe acima). Nenhuma correlacao com o fix do D4. Itens reincidentes a tratar fora do cron: timeout do `doc_audit.py` (O(n^2) near-dup) e os 2 flag-drifts em `feature_flags.py`.
- Demais dominios (D1-D4, D6, D7): sem erros.

## Acoes de Follow-up Sugeridas (fora do escopo do cron — revisao manual)

1. **doc_audit.py O(n^2)**: timeout >60s reincidente (ciclo 06-08 e 06-29) — otimizar deteccao near-dup.
2. **feature_flags.py flag-drift**: alinhar `AGENT_DIRECTIVE_JUDGE_SOURCE` e `AGENT_CAPABILITY_REGISTRY` aos testes (ou vice-versa).
3. **3 docs sem TOC** (C6): DESIGN.md, `app/agente/services/CLAUDE.md`, `docs/roteirizacao/ESTADO.md`.
4. **migration veiculos.custo_km** pendente em producao (6 issues Sentry, ~57 eventos).
5. **KG linking parado** (D6 R1 P0): backfill do pipeline de linking de memorias (3 ciclos sem novos links).
6. **memoria nociva u18** `quando-pergunta-detalhes-de-um-cluster` (D7, 4a semana, eficacia 0.0) — candidata a remocao.

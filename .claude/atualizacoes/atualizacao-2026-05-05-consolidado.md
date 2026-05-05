# Manutencao Semanal Consolidada — 2026-05-05

**Data**: 2026-05-05
**Dominios executados**: 7
**Dominios OK**: 6 | **PARCIAL**: 1 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9/9 auditados, 9 modificados (datas atualizadas). Unica mudanca estrutural: `agente/sdk/shutdown_state.py` documentado em `app/agente/CLAUDE.md` (71/35.3K -> 72/35.4K). CarVia +600 LOC sem novos arquivos. |
| 2 | References Audit | OK | 39 arquivos revisados (P0:20 + P1:10 + P2:9). 3 divergencias factuais corrigidas em AGENT_TEMPLATES.md e AGENT_DESIGN_GUIDE.md (12->13 subagents). 0 caminhos quebrados. |
| 3 | Memorias Cleanup | OK | Sexta auditoria, sistema saudavel em steady-state. 1 atualizacao em skills_inventario.md (operando-ssw 18->22 scripts). MEMORY.md 70/150 linhas. |
| 4 | Sentry Triage | OK | 32 issues avaliadas, 6 marcadas resolved. 1 fix novo aplicado: hora/base.html guarda `current_user.is_authenticated` antes de chamar `tem_perm_hora`. 26 fora de escopo. |
| 5 | Test Runner | PARCIAL | 766 testes em 96.13s, 749 passed, 17 failed (97.78%). 15 falhas por migration nao aplicada localmente (nao bug de codigo). 2 falhas reincidentes em carvia (mock SSW bypass). |
| 6 | Memory Eval | OK | Health score 86/100 (+1, NOVO RECORDE). 317 memorias, 502 sessoes, 23 usuarios. Eficacia 0.641 (melhor da serie). 9 recomendacoes geradas. |
| 7 | Agent Intelligence Report | OK | Health score 70/100 (+6, trend improving). Resolution rate 87.5% (semana 04/05). 12 recomendacoes ativas, 2 fechadas. Persistido no banco (report_id=1). |

## Metricas

### CLAUDE.md
- Arquivos auditados: 9/9
- Arquivos modificados: 9 (datas atualizadas)
- Mudanca estrutural: 1 (agente/sdk +1 arquivo)
- Caminhos quebrados: 0

### References
- Arquivos revisados em profundidade: 39
- Arquivos corrigidos: 2
- Divergencias factuais corrigidas: 3
- Caminhos quebrados: 0
- Pendencia historica: `odoo/IDS_FIXOS.md` product_tmpl_id 34 (aberta desde Jan/2026)

### Memorias
- Auditadas: 29
- Removidas: 0
- Consolidadas: 0
- Atualizadas: 1
- MEMORY.md: 70/150 linhas (47% do limite)

### Sentry
- Issues avaliadas: 32
- Issues corrigidas (fix novo): 1 (PYTHON-FLASK-Q6)
- Issues marcadas resolved (fixes anteriores): 5
- Issues fora de escopo: 26
- Arquivos modificados: 1 (`app/templates/hora/base.html`)

### Tests
- Total: 766
- Passed: 749
- Failed: 17
- Skipped/Error: 0
- Taxa: 97.78%
- Tempo: 96.13s
- Correlacoes com D4: 0

### Memory Eval (Producao)
- Health score: **86/100** (+1, NOVO RECORDE)
- Total memorias: 317 (+20, +6.7%)
- Total sessoes: 502 (+41)
- Usuarios unicos: 23
- Cold tier: 37 (+5)
- Stale 60d: 6 (+1)
- KG coverage: 40.1% (-1.3pp — 5o ciclo de queda)
- Eficacia media: 0.641 (+4.6%)
- Recomendacoes: 9

### Agent Intelligence Report
- Health score: **70/100** (+6)
- Friction score: 28/100 (-4)
- Sessoes analisadas: 143 (-5.3% vs ciclo anterior)
- Recomendacoes ativas: 12 (2 CRITICAL, 7 WARNING, 3 INFO)
- Recomendacoes fechadas no ciclo: 2
- Backlog total: 12 itens
- Trend: **improving** (4a semana consecutiva)
- Resolution rate (parcial 04/05): 87.5%
- Persistencia DB: OK (report_id=1)

## Erros e Falhas

### D5 — Test Runner (PARCIAL)

**Grupo A — 15 falhas em `tests/hora/test_pedido_workflow.py`**
- Erro: `UndefinedColumn: column "modalidade_frete" of relation "hora_venda"`
- Causa raiz: migration `scripts/migrations/hora_21_venda_modalidade_frete_parcelas.sql` (commit `8c6a483a`) NAO aplicada no banco local
- Fix recomendado: aplicar migration localmente (autorizado por feedback memorias)

**Grupo B — 2 falhas reincidentes em `tests/carvia/test_a3_ctrnc_cte_comp.py`**
- `TestCasoBVerificacao::test_ctrc_confirmado_retorna_ok`: assert `'CORRIGIDO' == 'OK'`
- `TestCasoBVerificacao::test_ctrc_divergente_corrigido`: assert `'CAR-164-3' == 'CAR-113-9'`
- Causa: patch path do mock `resolver_ctrc_ssw` errado, worker bate SSW real
- **Reincidencia**: mesmo bug do ciclo 2026-04-27, ainda nao corrigido
- Fix recomendado: revisar patch path em fixture do teste

## Acoes Prioritarias (Backlog Critico)

Do D7 (Agent Intelligence Report):

1. **REC-2026-04-13-001 — Circuit breaker para outliers de custo** (4 semanas em backlog)
   - Outlier $151.80 reentrou no top 10 esta semana
   - Severity: CRITICAL (auto-escalated apos 4 semanas)

2. **REC-2026-04-06-003 — Skill gaps frete/separacao/estoque** (40% das sessoes)
   - 19 sessoes em cada gap, oportunidade alta de melhoria

3. **REC-2026-05-05-002 — High_cost +10.6pp**
   - Sessoes longas/caras subiram esta semana, investigar antes de virar regressao

Do D6 (Memory Eval):

1. **R1 [URGENTE] — Auditar 11 memorias zero-efficacy** (91 carregamentos perdidos, 5o ciclo sem auditoria)
2. **R2 [CRITICO] — `user-xml-nao-atualiza-por-threshold`** (386 usos, efficacy 0.124)
3. **R3 [ALTO] — Reverter queda KG coverage** (5o ciclo consecutivo)
4. **R4 [ALTO] — Implementar `reviewed_at` em memorias empresa** (5o ciclo, 136 memorias afetadas)
5. **R5 [ALTO] — Recalibrar extrator `learned/expertise_*`**

## Tendencias

- **D6 — Memory Eval**: Health score em recorde historico (86/100), eficacia em alta (0.641), mas KG coverage continua caindo
- **D7 — Agent Intelligence**: Trend improving (4 semanas consecutivas), resolution rate atingiu 87.5% (acima da meta 80%)
- **D5 — Tests**: Suite cresceu de 737 para 766 testes (+29). Taxa caiu para 97.78% (de 99.73%) por divergencia ambiental, nao codigo

## Artefatos

- Branch: `manutencao/semanal-2026-05-05`
- Commits atomicos: 7 (1 por dominio + consolidado)
- Status JSONs: `/tmp/manutencao-2026-05-05/dominio-{1..7}-status.json`
- Relatorios individuais:
  - `.claude/atualizacoes/claude_md/atualizacao-2026-05-05-1.md`
  - `.claude/atualizacoes/references/atualizacao-2026-05-05-1.md`
  - `.claude/atualizacoes/memorias/atualizacao-2026-05-05-1.md`
  - `.claude/atualizacoes/sentry/atualizacao-2026-05-05-1.md`
  - `.claude/atualizacoes/tests/atualizacao-2026-05-05-1.md`
  - `.claude/atualizacoes/memory-eval/atualizacao-2026-05-05-1.md`
  - `.claude/atualizacoes/agent-reports/report-2026-05-05.md`

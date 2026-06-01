# Manutencao Semanal Consolidada — 2026-06-01

**Data**: 2026-06-01
**Dominios executados**: 7
**Dominios OK**: 6 | **PARCIAL**: 1 | **FAILED**: 0

> Orquestracao em 3 estagios: Estagio 1 (D1-D4 paralelos) -> Estagio 2 (D5-D7 paralelos) -> Estagio 3 (consolidacao). Todos os 7 status.json foram escritos; nenhum agente falhou em escrever status.

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9/9 auditados, **8 modificados** (real vs HEAD; `app/agente/CLAUDE.md` ja estava correto). SDK 0.1.80->0.2.87 na raiz; agente 80->96 arq; odoo 63->70 arq (estoque +Skills 7/8). |
| 2 | References Audit | OK | 39 revisados (P0-P2 profundo, P3-P4 scan), 5 corrigidos, 0 caminhos quebrados. Opus 4.7->4.8, 48->51 skills, +3 skills Odoo no INDEX, callsites/paths corrigidos. |
| 3 | Memorias Cleanup | OK | 113 topic files auditados, frontmatter 113/113 OK, 0 orfaos. MEMORY.md 156->148 linhas (31.6KB->19.7KB) por condensacao (0 conhecimento deletado). 1 link quebrado corrigido. |
| 4 | Sentry Triage | OK | 23 issues avaliadas, **3 resolved** (W4 fix novo de import-path; WB+WD ja corrigidas em main), 14 ignoradas, 6 fora escopo. 1 arquivo de codigo modificado. |
| 5 | Test Runner | PARCIAL | 2575 testes: 2483 passed, 36 failed, 49 error, 7 skipped (**96.69%**). Todas as falhas pre-existentes/ambientais. **0 correlacoes com D4**. |
| 6 | Memory Eval (Prod) | OK | Health **86/100** (+2, iguala recorde). Eficacia 0.656->0.812. Cold 8.93%. KG e o calcanhar (44.6% coverage, 1582 orfas). 7 recomendacoes. |
| 7 | Agent Intelligence Report | OK | Health **70/100**, friction 38, 231 sessoes/30d, 13 recomendacoes, 13 backlog (3 CRITICAL). Persistido no banco (report_id=5, HTTP 200). Trend **STABLE**. |

## Metricas

### CLAUDE.md (D1)
- Arquivos auditados: **9/9**, modificados: **8** (D1 reportou 9; `app/agente/CLAUDE.md` ficou sem diff vs HEAD pois o skill `claude-md-improver` rodou em paralelo e ja o atualizara)
- Destaques: raiz SDK `0.1.80 (CLI 2.1.138)` -> `0.2.87 (CLI 2.1.150)`; `app/agente` 80->96 arquivos (~41.9K->~48.9K LOC, flywheel Ondas 0-4 em main); `app/odoo` 63->70 arquivos (estoque/ 13->19 com Skills 7/8 + orchestrator inventario_pipeline)

### References (D2)
- Arquivos revisados: **39**, corrigidos: **5**, caminhos quebrados: **0**
- Corrigidos: `STUDY_PROMPT_ENGINEERING_2026.md` (Opus 4.7->4.8, 48->51 skills), `AGENT_DESIGN_GUIDE.md` (tier Opus +4.8), `INDEX.md` (+3 skills Odoo), `PADROES_BACKEND.md` (callsites sanitize_for_json), `negocio/MARGEM_CUSTEIO.md` (caminho real `app/custeio/services/`)
- Pendencia historica: `odoo/IDS_FIXOS.md:112` product_tmpl_id FRETE requer MCP Odoo (fora de escopo estatico)

### Memorias (D3)
- Auditadas: **113**, removidas: **0**, consolidadas: **0** (indice condensado, sem deletar), atualizadas: **1**
- MEMORY.md: **156 -> 148 linhas** (31.6KB -> 19.7KB), dentro do budget de 150 linhas
- `picking_317346_pendente` mantido como candidato a remocao (nao verificavel sem Odoo live)

### Sentry (D4)
- Issues avaliadas: **23**, corrigidas: **3**, ignoradas: **14**, fora de escopo: **6**
- Fix novo: W4 import-path `app.carvia.services.cotacao_service` -> `...pricing.cotacao_service` em `cotando_subcontrato_carvia.py`
- WB+WD ja corrigidas em main (commit `4477faa4d`), eventos pre-fix — marcadas resolved sem novo codigo

### Tests (D5)
- Total: **2575**, passed: **2483**, failed: **36**, error: **49**, skipped: **7**, taxa: **96.69%**
- Correlacoes com D4: **0** (D4 mexeu so em script de skill sem cobertura em `tests/`)
- Falhas pre-existentes: 22 fixtures PDF ausentes (motos_assai), 34 errors `hora` UniqueViolation, 14 errors ARRAY incompativel com SQLite, testes batendo Odoo ao vivo
- **Gotcha ambiental**: `.env` sobrepoe `DATABASE_URL=sqlite` do `pytest.ini`, fazendo testes baterem Postgres+Odoo reais (state pollution entre runs)

### Memory Eval (Producao) (D6)
- Health score: **86/100** (+2 vs 84 do ciclo 2026-05-25; iguala recorde da serie)
- Total memorias: **494**, sessoes: **724**, cold: **44 (8.93%)**, stale 60d: **69 (13.99%)**, usuarios: **31**
- Recomendacoes: **7**
- Pontos fracos: KG coverage 44.6% (1582 entidades orfas), 50% memorias empresa nunca revisadas, `correction_count` zerado infla score em ~15 pts

### Agent Intelligence Report (D7)
- Health score: **70/100** (de 72), friction score: **38**
- Sessoes analisadas: **231** (+24.9% vs ciclo anterior)
- Recomendacoes: **13**, backlog: **13 itens** (3 CRITICAL, 5 WARNING, 5 INFO; 3 novos, 2 fechados)
- Trend: **stable** (rebaixado de "improving" por custo semanal +286% e 5 novos outliers $26-44)
- Persistido no banco: **sim** (report_id=5, HTTP 200)
- Gaps de skill escalando 3a semana: embarque (+65%), transportadora (+71%), faturamento (+29%)

## Erros e Falhas

Nenhum dominio FAILED. Apenas 1 PARCIAL:

- **D5 (Test Runner) — PARCIAL**: a suite executou completa mas com 36 failed + 49 errors. Todas as falhas sao **pre-existentes e ambientais** (perfil quase identico ao ciclo 2026-05-25), nao regressoes deste ciclo. Para rodar a suite completa o agente precisou: (1) ignorar 1 ImportError de coleta (`tests/agente_lojas/test_todos_parser.py`, teste orfao apos remocao de `_try_parse_todos` no commit `f0567257a`); (2) sobrescrever `--maxfail=5` do `pytest.ini`. **Nenhum codigo de teste ou producao foi alterado pelo D5.**

## Observacoes do Orquestrador

1. **`dominio-8-improvement-dialogue.md` existe** em `.claude/atualizacoes/dominios/` (criado 2026-06-01 01:22) mas **NAO faz parte do protocolo de orquestracao atual** (que define apenas D1-D7, estagios 4+3). Nao foi executado. Avaliar inclusao em ciclo futuro / revisar o protocolo do orquestrador.
2. **Diagnostico Pyright** apos o fix do D4: `cotando_subcontrato_carvia.py:186` marcado como codigo inalcancavel. O D4 sinalizou um bug latente separado (`listar_opcoes_transportadora` ausente na classe atual) que esta fora do escopo "missing import" — registrado aqui para acompanhamento, nao corrigido.
3. **Arquivos pre-existentes preservados**: mudancas nao relacionadas a manutencao (`docs/industrializacao-fb-lf/*`, `.claude/AUDITORIA_SKILLS_*`, `scripts/inventario_2026_05/*`) foram mantidas intactas no working tree e **nao incluidas** em nenhum commit deste ciclo.
4. **MEMORY.md real** (em `~/.claude/projects/.../memory/`) foi reescrito pelo D3 mas vive **fora do repo** — apenas o relatorio do D3 entrou no commit.

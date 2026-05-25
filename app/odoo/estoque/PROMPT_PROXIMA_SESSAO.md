# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v8

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão. Mantém você dentro do plano global sem desviar.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, **5+ commits sobre `main`@b4f7b24c — último commit v7-extras**). `main` continua VIVO em paralelo (Rafael commita lá) — verificar se avançou e considerar rebase incremental ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^ODOO_' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
```

## ✅ GAP RESERVAS RESOLVIDO em v7 (2026-05-24)

A sessão v7 fechou o gap arquitetural "tratar reserva ATIVA pré-transferência" (caso 71 cods PAUSADO em v6.1):
- **4 átomos novos**: Skill 9 `listar_move_lines_por_quant` + `listar_pickings_por_quant` (cross-ref via tupla G030); Skill 2.4 `unreserve_picking` + `find_orphan_mls`.
- **Fluxo 2.6** `fluxos/2.6-tratar-reserva-bloqueia-transferencia.md` com 5 caminhos seguros (A=cancel/B=devolver/C=unreserve/D=outro lote/E=cirurgia órfã).
- **Regra inviolável** no prompt do `gestor-estoque-odoo`: "PRE-CHECK reserva via Skill 9 ANTES de Skill 2".
- **Tabela "5 caminhos"** em SKILL.md da Skill 2.4.
- **Gotcha G030** documentado (`stock.move.line.quant_id` é computed `store: False` — filtro IGNORADO; cross-ref via tupla obrigatório).
- **88 writes em PROD validados**: 1 cancel FB/INT/08022 + 80 chamadas Skill 2 MODO C + 3 P-15/05 MODO B + 4 reversões (incidente race condition).
- **230 pytest verdes** (196 anterior + 33 novos + 1 H1 draft).

## ⚠️ REGRAS INVIOLÁVEIS NOVAS (v7-extras — LER ANTES DE QUALQUER AÇÃO)

1. **EXECUTAR FLUXOS = subagente, NÃO principal** (lição que custou ~150k tokens em v7):
   - Para EXECUTAR fluxos sobre caso real (auditoria + write em PROD via composição de skills), SEMPRE spawn `gestor-estoque-odoo` via Task tool.
   - Use o principal APENAS para IMPLEMENTAR átomos novos / debugar gaps arquiteturais / refatorar services.
   - Economia esperada: ~30-50% tokens em batches de 80+ chamadas.

2. **`--quiet` em CLIs estoque** (NOVO v7-extras): todos os 7 CLIs aceitam `--quiet` (suprime Flask boot ~50 linhas/call). Use SEMPRE em batches via subprocess. JSON output não é afetado.

3. **`--forcar-concorrencia`** (NOVO v7-extras): scripts CLI agora detectam concorrência via `pgrep -f` no startup. Default = sys.exit(2) se outro processo igual rodando (previne incidente race condition v7). Use `--forcar-concorrencia` SÓ quando ciente.

4. **Log JSON é fonte de verdade** (lição v7): NUNCA confiar em `tee` background (pode falhar silenciosamente). Sempre parsear JSON do log salvo pelo script (`/tmp/log_*.json` para batches).

## PENDÊNCIAS RESIDUAIS (não-bloqueantes — pode resolver na v8 ou postergar)

| Item | Quantidade | Comando recomendado |
|---|---|---|
| Cod **105000003** (P-15/05 literal — lote real, qty 430 do plano caso 71-cods) | 1 cod | Skill 1 `--quant-id 261857 --delta -430 --confirmar` + ajustar destino MIGRAÇÃO Indisp `--quant-id <X> --delta +430 --confirmar` (resolver quant destino via Skill 9) |
| Cod **4739199** (lote 353/25 — FALHA_QUANT_NEGATIVO no smoke v7) | 1 cod | Investigar saldo atual via Skill 9; pode já ter sido reduzido pelo batch principal — verificar antes de tocar |
| **5 cods MIGRAÇÃO pulados** (103000113, 103000117, 104000054, 105000021, 105000038) | 5 cods | Rafael decide via fluxo 2.6: cancelar pickings (caminhos A/B) ou aceitar saldo bloqueado. Pickings: FB/FB/EMB/11673+11674 (MO ativa centavos) + FB/OUT/01046 (DEVOLUcaO LA FAMIGLIA ~890un — risco fiscal) |
| Plano Etapa B (67 chamadas separadas) | — | NÃO necessário — MODO C atomic já fez Etapa A+B atomic |

## FOCOS POSSÍVEIS PARA v8 (escolher 1 ao iniciar a sessão)

### Foco A (RECOMENDADO se pendências forem prioridade): Resolver residuais via subagente
- Spawnar `gestor-estoque-odoo` com prompt: "Resolver pendências v7-residuais — cod 105000003 + cod 4739199 + 5 cods MIGRAÇÃO".
- O subagente seguirá fluxo 2.6 automaticamente para os 5 cods MIGRAÇÃO; Skill 1 direta para os 2 individuais.
- Tempo estimado: ~30-60min, ~40-60k tokens (vs ~150k se principal orquestrar).
- Risco: baixo (pendências bem mapeadas; subagente segue regras invioláveis).

### Foco B: Skill 8 `faturando-odoo` (DESBLOQUEADA pela ONDA 0.4 v3)
- Skill MACRO mais perigosa (NF→SEFAZ irreversível).
- Service `InventarioPipelineService` existe — capinar para `app/odoo/estoque/orchestrators/inventario_pipeline.py` + shim. Pattern Skill 5.
- Pre-flight quarteto fiscal G035/G017/G007/G018 obrigatório.
- Smoke 1-ajuste antes de batch (regra inviolável SEFAZ).
- ~6-8h, ~200-300k tokens.
- Risco: ALTO (SEFAZ irreversível; robô CIEL IT externo timing).

### Foco C: Skill 7 `escriturando-odoo` (entrada IC + DFe)
- Pré-cond: Skill 2 ✅ + Skill 5 ✅. Mais simples que Skill 8 (sem SEFAZ direto).
- ~4-6h, ~150-200k tokens.

### Foco D: Capinar `09b_executar_pre_etapa.py` (C3 macro Skill 6)
- Fecha ciclo Skill 6 (planejar+propor+aprovar+executor): capina `09b` → `orchestrators/pre_etapa_executor.py`.
- Macro C3 que delega Skills 1+2.
- ~3-4h, ~80-120k tokens.

### Foco E: Code-review v7 dos 4 átomos novos (deferida v7-extras)
- Spawn 2 code-reviewers paralelos (já feito em v7 — 1 HIGH + 4 MED corrigidos). Re-rodar se quiser cobertura adicional.

## LEITURAS OBRIGATÓRIAS ANTES DE AGIR (ordem)

1. `app/odoo/estoque/CLAUDE.md` — constituição (§1 princípio fundador, §6 catálogo 7 skills, §8 invariantes).
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF (estado v7 + próximos passos).
3. `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` §13 + §13.8.1 (sessão v7 completa + melhorias v7-extras + lições operacionais).
4. `.claude/agents/gestor-estoque-odoo.md` — invariantes (8 regras, das quais 3 são v7-novas: PRE-CHECK reserva, EXECUTAR-FLUXOS-subagente, --quiet/--forcar/log-JSON).
5. **Se foco = A (residuais via subagente)**:
   - `app/odoo/estoque/fluxos/2.6-tratar-reserva-bloqueia-transferencia.md` (fluxo + 5 caminhos)
   - `.claude/skills/operando-reservas-odoo/SKILL.md` (tabela "5 caminhos seguros")
   - `.claude/skills/consultando-quant-odoo/SKILL.md` (3 modos: quants/move-lines/pickings)
6. **Se foco = B (Skill 8)**:
   - `app/odoo/services/inventario_pipeline_service.py`
   - `docs/inventario-2026-05/02-gotchas/G004*.md`, `G011*.md`, `G016*.md`, `G023*.md` (já codificados em picking.py), `G035*.md`, `G017*.md`, `G007*.md`, `G018*.md` (quarteto fiscal pré-SEFAZ).
   - Memórias: `[[ciel_it_quirks]]`, `[[picking_317346_pendente]]`, `[[skill5_picking_pattern]]`.
7. Memórias-chave gerais:
   - `[[arquitetura_orquestrador_odoo]]` — princípio fluxos>>skills
   - `[[caso_real_tratar_reservas_pre_transferencia]]` — caso v7 RESOLVIDO (referência histórica)
   - `[[gotcha_g030_quant_id_store_false]]` — cross-ref via tupla
   - `[[fluxo_2_6_pattern]]` — pattern 5-caminhos
   - `[[skill5_picking_pattern]]` — pattern capinagem retroativa
   - `[[feedback_skills_demanda_driven]]` — skills nascem de casos reais
   - `[[feedback_incompletude_quebra_regras]]` — C7-C10 invioláveis

## REGRAS INVIOLÁVEIS (não negociáveis — herdadas + v7-novas)

1. `--dry-run` antes do real; confirmação explícita antes de SEFAZ/irreversível.
2. NUNCA criar script ad-hoc — capinar a skill. `/tmp/` OK (descartável).
3. `fluxos>>skills` — caso novo = folha de fluxo, NÃO skill nova.
4. Skills nascem de DEMANDAS REAIS — não implementar átomos especulativamente.
5. C7-C10 são INVIOLÁVEIS — completar cada checkpoint com artefato concreto.
6. Verificar resultado DIRETO no Odoo — não confiar só no output.
7. Operação VIVA — preservar ad-hocs até cada átomo maturar.
8. Premissas pesquisadas e validadas ANTES de compor átomos.
9. Após qualquer unlink em MLs em quants com reserved=0: chamar `zerar_reserved_residual` (G027).
10. Ao retomar FALHAs: cruzar `mo_id`/`quant_id`/etc. com pedido original — NÃO aplicar política homogênea.
11. Composição de átomos propaga `delta_esperado` a CADA chamada.
12. `--corrigir-para-esperado` em batch SEMPRE rodar `--dry-run` primeiro.
13. Pytest baseline ANTES de modificar service (atualizar baseline em mudanças).
14. TIMEZONE: NUNCA `datetime.now()` em código novo — usar `from app.utils.timezone import agora_brasil_naive`.
15. **(v6)** Skill 6 `pre_etapa.py`: pytest baseline 19 verdes.
16. **(v4)** Skill 2 `transfer.py`: pytest baseline 52 verdes. CUIDADO com modo C — invariante G031 crítica.
17. **(v3)** Skill 5 `picking.py`: pytest baseline 42 verdes. NÃO quebrar invariante G019/G020 (re-abre ONDA 0.4 + quebra Skill 8).
18. **(v5)** Skill 4 `mo.py`: pytest baseline 29 verdes. CUIDADO com guard G-MO-01 (consumo>0=furo contábil).
19. **(v7)** Skill 9 `consulta_quant.py`: pytest baseline 19 verdes. NÃO usar `quant_id` direto (G030 — store:False).
20. **(v7)** Skill 2.4 `reserva.py`: pytest baseline 15 verdes (14 originais + 1 H1 draft fix). `unreserve_picking` recusa state ∈ {done, cancel, draft}.
21. **(v7) PRE-CHECK reserva ANTES Skill 2**: SEMPRE verificar `reserved>0` via Skill 9 dos quants candidatos a DOAR. Se sim, INVESTIGAR pickings via fluxo 2.6 ANTES de chamar Skill 2.
22. **(v7) `stock.move.line.quant_id` é COMPUTED `store: False`** (G030): NUNCA filtrar por ele direto. Skill 9 faz cross-ref via tupla automaticamente.
23. **(v7-extras) EXECUTAR FLUXOS = subagente, NÃO principal**: para casos reais, spawn `gestor-estoque-odoo` via Task tool.
24. **(v7-extras) `--quiet` em batches via subprocess** + `--forcar-concorrencia` SÓ quando ciente.
25. **(v7-extras) Log JSON é fonte de verdade** — não confiar em `tee` background.

## ARQUITETURA — árvore de decisão

```
1  NF inter-company (emissão/SEFAZ entre filiais)
   1.1  só faturamento (saída)              → fluxos/1.1.* (faturando-odoo ⬜ ← FOCO B)
   1.2  só entrada/escrituração
        1.2.1 inventário (DFe próprio)      → fluxos/1.2.1 (escriturando-odoo ⬜ ← FOCO C)
        1.2.2 COMPRAS (DFe fornecedor)      → DELEGAR a gestor-recebimento
   1.3  transferência completa              → fluxos/1.3 ⬜
2  Estoque (SEM NF — galho 1.x se com NF)
   2.1 ajuste de saldo (1 quant; planilha)  → ajustando-quant-odoo ✅ [folha 2.1]
   2.2 realocar saldo (lote↔lote / loc↔loc / MIGRA↔Indisp via MODO C)
                                            → transferindo-interno-odoo 🟡 [folha 2.2]
   2.3 transferir saldo entre CÓDIGOS       → (skill transferencia-saldo-codigo) ⬜
   2.4 cancelar reserva / cirurgia ML / unreserve picking / find_orphan
                                            → operando-reservas-odoo 🟡 [folha 2.4]
   2.5 cancelar/validar/devolver picking    → operando-picking-odoo 🟡 [folha 2.5]
   2.6 TRATAR reserva ATIVA pré-transferência (pré-cond INVIOLÁVEL Skill 2)
                                            → fluxo composto 9+2.4+5+2 [folha 2.6]
   2.9 CONSULTA AO VIVO (quants/MLs/pickings cross-ref reverso)
                                            → consultando-quant-odoo 🟡 [folha 2.9]
3  Produção / PCP
   3.1 cancelar MO (single/batch — guard G-MO-01) → operando-mo-odoo 🟡 [folha 3.1]
4  Planejamento de ajustes (READ Odoo + WRITE banco local)
   4.1 PRE-ETAPA inventario CD/FB D007      → planejando-pre-etapa-odoo 🟡 [folha 4.1]
```

## CHECKLIST DA SESSÃO v8

```
[ ] Setup (cd worktree + venv + ODOO_*)
[ ] Verificar se main avançou: git fetch origin main && git log --oneline <commit-v7>..origin/main
[ ] Se avançou: rebase incremental ANTES de iniciar
[ ] Pytest baseline: 230 verdes esperado (rodar full suite estoque)
[ ] Ler ROADMAP_SKILLS HANDOFF + VALIDACAO §13+§13.8.1 + 5 memórias-chave
[ ] AskUserQuestion com Rafael: foco A (residuais via subagente) | B (Skill 8) | C (Skill 7) | D (09b executor) | E (code-review v7 extra)
[ ] Se foco A: spawn gestor-estoque-odoo via Task tool (NÃO orquestrar do principal)
[ ] Se foco B/C/D: implementar via principal seguindo pattern Skills 4/5/6
[ ] Após writes em PROD: verificar resultado DIRETO no Odoo (regra inviolável 6)
[ ] Code-review paralelo (2 reviewers) ao fim da sessão
[ ] Atualizar ROADMAP_SKILLS HANDOFF + VALIDACAO §14 + memórias
[ ] Commit consolidado + atualizar este PROMPT_PROXIMA_SESSAO.md (v9)
```

## NÃO-FAZER (red flags v8)

- ❌ Criar scripts ad-hoc em `scripts/inventario_2026_05/` (capinar a skill)
- ❌ Implementar átomos previstos sem demanda real
- ❌ Marcar C# como ✅ sem entregar artefato concreto
- ❌ Modificar `quant.py`, `transfer.py`, `picking.py`, `reserva.py`, `mo.py`, `pre_etapa.py`, `consulta_quant.py` sem rodar pytest ANTES e DEPOIS
- ❌ Compor átomos sem propagar `delta_esperado`
- ❌ Usar `datetime.now()` em código novo (hook bloqueia)
- ❌ Filtrar `stock.move.line` por `quant_id` direto (G030 — ignorado pelo Odoo)
- ❌ Cancelar MO com `consumo_total > 0` sem unbuild (G-MO-01)
- ❌ Quebrar G019/G020 em `picking.py` (re-abre ONDA 0.4)
- ❌ Quebrar G031 em Skill 2 modo C (MIGRAÇÃO POR PRODUTO)
- ❌ **(v7-extras)** ORQUESTRAR FLUXOS do agente principal (use subagente)
- ❌ **(v7-extras)** Rodar batch SEM `--quiet` (polui ~50 linhas/call × N)
- ❌ **(v7-extras)** Confiar em `tee` background — parsear JSON do log salvo pelo script
- ❌ **(v7-extras)** Disparar batch sem checar concorrência via `pgrep -f` (scripts já fazem isso automaticamente; respeitar exit 2)

---END---

## NOTAS PARA RAFAEL (não fazem parte do prompt)

- v7 fechou gap reservas com 88 writes PROD validados (1 cancel + 80 MODO C + 3 P-15/05 MODO B + 4 reversões pós-incidente race condition).
- v7-extras (commit follow-up): `_cli_utils.py` NOVO + 7 CLIs atualizados com `--quiet`+`--forcar-concorrencia` + regra subagent no prompt + CR1+CR2 fixes (1 HIGH + 4 MED + 1 LOW aplicados + 1 teste novo H1 draft) + memória nova `[[gotcha_g030_quant_id_store_false]]` + `[[fluxo_2_6_pattern]]` + VALIDACAO §13.8.1.
- Pendências residuais documentadas (3 itens não-bloqueantes).
- Estimativa de economia em v8 com regras v7-extras: ~50-100k tokens por caso real.

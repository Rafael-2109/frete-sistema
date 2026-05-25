# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v9

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão. Mantém você dentro do plano global sem desviar.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, **commits ao fim de v8: bf53ea84 (v7) + 507e5e36 (v7-extras) + <commit-v8> sobre `main`@b4f7b24c**). `main` continua VIVO em paralelo (Rafael commita lá) — verificar se avançou e considerar rebase incremental ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^ODOO_' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
```

## ✅ CASO 71 cods 100% CONCLUÍDO em v8 (2026-05-25)

A jornada completa (v7 + v7-extras + v8 + cirurgia) processou **~115 writes PROD, ~22.500 un transferidas** para FB/Indisponivel. Status final do plano original:
- **67/67 cods executáveis OK** (100%)
- **4 SKIP planejados** desde início (103 PEPINO, 46 VINAGRE TRIPLO sem saldo; X105000022 descontinuado; 301000003 em FB/Pos-Producao)
- **0 PARCIAL, 0 FALHA**

**Marcos da jornada:**
- v7: gap arquitetural reservas RESOLVIDO + 4 átomos novos + fluxo 2.6 + G030 (88 writes PROD)
- v7-extras: `_cli_utils.py` + `--quiet` + `--forcar-concorrencia` + regra subagent + CR fixes
- v8: 13 pendências residuais resolvidas (11 via caminho D + 2 via cirurgia FB/OUT/01046)
- Cirurgia v8: pattern atômico NOVO `cirurgia → zerar_residual → MODO C` validado (876 un destravadas)

## ⚠️ REGRAS INVIOLÁVEIS NOVAS (v7-extras + v8 — LER ANTES DE QUALQUER AÇÃO)

1. **EXECUTAR FLUXOS = subagente, NÃO principal** (v7-extras — lição que custou ~150k tokens em v7):
   - Para EXECUTAR fluxos sobre caso real, SEMPRE spawn `gestor-estoque-odoo` via Task tool.
   - Use o principal APENAS para IMPLEMENTAR átomos novos / debugar gaps arquiteturais / refatorar services.
   - Economia esperada: ~30-50% tokens em batches de 80+ chamadas.

2. **CIRURGIA (E) PREFERIDA sobre CANCELAR (A) quando picking tem MIX MLs válidas + bloqueantes** (v8 — lição FB/OUT/01046):
   - SEMPRE listar TODAS as MLs do picking via Skill 9 modo pickings ANTES de cancelar.
   - Se houver >1 ML válida de outros cods/devoluções → USAR cirurgia (Skill 2.4 `cancelar_moves_orfaos` + `--zerar-residual` + Skill 2 MODO C).
   - Cancelar inteiro só se picking é 100% bloqueante/fantasma.

3. **`--quiet` em CLIs estoque** (v7-extras): todos os 7 CLIs aceitam `--quiet`. Use SEMPRE em batches via subprocess. JSON output não é afetado.

4. **`--forcar-concorrencia`** (v7-extras): scripts CLI detectam concorrência via `pgrep -f`. Default = sys.exit(2) se outro processo igual rodando. Use `--forcar-concorrencia` SÓ quando ciente.

5. **Log JSON é fonte de verdade** (v7): NUNCA confiar em `tee` background (pode falhar silenciosamente). Sempre parsear JSON do log salvo pelo script.

## PENDÊNCIAS RESIDUAIS

**ZERO pendências operacionais do caso 71 cods.** Apenas pendência cosmética:
- **3 moves residuais com qty=0 no picking FB/OUT/01046** (cosmético, aguarda validação manual pelo time fiscal no Odoo UI — `button_validate` cancela automaticamente)

## FOCOS POSSÍVEIS PARA v9 (escolher 1 ao iniciar a sessão)

### Foco A: Skill 8 `faturando-odoo` (RECOMENDADO — DESBLOQUEADA pela ONDA 0.4 v3)
- Skill MACRO mais perigosa (NF→SEFAZ irreversível).
- Service `InventarioPipelineService` existe — capinar para `app/odoo/estoque/orchestrators/inventario_pipeline.py` + shim. Pattern Skill 5.
- Pre-flight quarteto fiscal G035/G017/G007/G018 obrigatório.
- Smoke 1-ajuste antes de batch (regra inviolável SEFAZ).
- ~6-8h, ~200-300k tokens.
- Risco: ALTO (SEFAZ irreversível; robô CIEL IT externo timing).

### Foco B: Skill 7 `escriturando-odoo` (entrada IC + DFe)
- Pré-cond: Skill 2 ✅ + Skill 5 ✅. Mais simples que Skill 8 (sem SEFAZ direto).
- ~4-6h, ~150-200k tokens.

### Foco C: Capinar `09b_executar_pre_etapa.py` (C3 macro Skill 6)
- Fecha ciclo Skill 6 (planejar+propor+aprovar+executor): capina `09b` → `orchestrators/pre_etapa_executor.py`.
- Macro C3 que delega Skills 1+2.
- ~3-4h, ~80-120k tokens.

### Foco D: Limpeza de moves residuais FB/OUT/01046 (manual no Odoo UI)
- Cancelar 3 moves (1161587, 1161611, 1161613) que ficaram com qty=0 após cirurgia v8.
- ~5min manual no Odoo UI (não há CLI — `stock.move._action_cancel` é privado G025).
- Cosmético, não-bloqueante.

### Foco E: Outro caso real que Rafael trouxer
- Subagente `gestor-estoque-odoo` já preparado com regras v7-v8 codificadas.
- SEMPRE spawn via Task tool (regra inviolável 1).

## LEITURAS OBRIGATÓRIAS ANTES DE AGIR (ordem)

1. `app/odoo/estoque/CLAUDE.md` — constituição.
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF (estado v8 + próximos passos).
3. `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` §13 + §14 (sessão v7 + v8 completas + lições operacionais §13.8.1 + cirurgia §14.4).
4. `.claude/agents/gestor-estoque-odoo.md` — invariantes (9 regras: 5 originais + PRE-CHECK reserva v7 + EXECUTAR-FLUXOS-subagente v7-extras + CIRURGIA preferida v8 + log-JSON v7).
5. **Se foco = A (Skill 8 faturando)**:
   - `app/odoo/services/inventario_pipeline_service.py`
   - `docs/inventario-2026-05/02-gotchas/G004*.md`, `G011*.md`, `G016*.md`, `G023*.md` (já codificados em picking.py), `G035*.md`, `G017*.md`, `G007*.md`, `G018*.md` (quarteto fiscal pré-SEFAZ).
   - Memórias: `[[ciel_it_quirks]]`, `[[picking_317346_pendente]]`, `[[skill5_picking_pattern]]`.
6. **Se foco = B (Skill 7 escriturando)**:
   - `docs/inventario-2026-05/02-gotchas/G023*.md`, `G034*.md`
   - Memória: `[[escrituracao_entrada_lf_dfe]]`
7. **Se foco = C (09b executor)**:
   - `scripts/inventario_2026_05/_validados/planejando-pre-etapa-odoo/` (museum vivo)
   - Memória: `[[skill6_planejar_pre_etapa_pattern]]`
8. **Se foco = E (caso real)**:
   - Spawn `gestor-estoque-odoo` via Task tool com prompt curto descrevendo o caso
9. Memórias-chave gerais:
   - `[[arquitetura_orquestrador_odoo]]` — princípio fluxos>>skills
   - `[[caso_real_tratar_reservas_pre_transferencia]]` — caso v7+v8 RESOLVIDO 100% (referência histórica)
   - `[[gotcha_g030_quant_id_store_false]]` — cross-ref via tupla
   - `[[fluxo_2_6_pattern]]` — pattern 5-caminhos + cirurgia v8
   - `[[skill5_picking_pattern]]` — pattern capinagem retroativa
   - `[[feedback_skills_demanda_driven]]` — skills nascem de casos reais
   - `[[feedback_incompletude_quebra_regras]]` — C7-C10 invioláveis

## REGRAS INVIOLÁVEIS (não negociáveis — herdadas + v7 + v8)

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
20. **(v7)** Skill 2.4 `reserva.py`: pytest baseline 15 verdes. `unreserve_picking` recusa state ∈ {done, cancel, draft}.
21. **(v7) PRE-CHECK reserva ANTES Skill 2**: SEMPRE verificar `reserved>0` via Skill 9 dos quants candidatos a DOAR. Se sim, INVESTIGAR pickings via fluxo 2.6 ANTES de chamar Skill 2.
22. **(v7) `stock.move.line.quant_id` é COMPUTED `store: False`** (G030): NUNCA filtrar por ele direto. Skill 9 faz cross-ref via tupla automaticamente.
23. **(v7-extras) EXECUTAR FLUXOS = subagente, NÃO principal**: para casos reais, spawn `gestor-estoque-odoo` via Task tool.
24. **(v7-extras) `--quiet` em batches via subprocess** + `--forcar-concorrencia` SÓ quando ciente.
25. **(v7-extras) Log JSON é fonte de verdade** — não confiar em `tee` background.
26. **(v8 NOVA) CIRURGIA (E) PREFERIDA sobre CANCELAR (A) em pickings MIX**: SEMPRE listar TODAS as MLs do picking antes de cancelar. Se >1 ML válida de outros cods → cirurgia preserva picking.
27. **(v8 NOVA) Pattern atômico cirurgia → zerar_residual → MODO C**: composição de 3 chamadas para destravamento completo de quants reservados. Codificado no fluxo 2.6 caminho E.

## ARQUITETURA — árvore de decisão

```
1  NF inter-company (emissão/SEFAZ entre filiais)
   1.1  só faturamento (saída)              → fluxos/1.1.* (faturando-odoo ⬜ ← FOCO A)
   1.2  só entrada/escrituração
        1.2.1 inventário (DFe próprio)      → fluxos/1.2.1 (escriturando-odoo ⬜ ← FOCO B)
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
                                            (5 caminhos A/B/C/D/E + regra v8 cirurgia preferida)
   2.9 CONSULTA AO VIVO (quants/MLs/pickings cross-ref reverso)
                                            → consultando-quant-odoo 🟡 [folha 2.9]
3  Produção / PCP
   3.1 cancelar MO (single/batch — guard G-MO-01) → operando-mo-odoo 🟡 [folha 3.1]
4  Planejamento de ajustes (READ Odoo + WRITE banco local)
   4.1 PRE-ETAPA inventario CD/FB D007      → planejando-pre-etapa-odoo 🟡 [folha 4.1]
```

## CHECKLIST DA SESSÃO v9

```
[ ] Setup (cd worktree + venv + ODOO_*)
[ ] Verificar se main avançou: git fetch origin main && git log --oneline <commit-v8>..origin/main
[ ] Se avançou: rebase incremental ANTES de iniciar
[ ] Pytest baseline: 230 verdes esperado (rodar full suite estoque)
[ ] Ler ROADMAP_SKILLS HANDOFF + VALIDACAO §13+§14 + 5 memórias-chave
[ ] AskUserQuestion com Rafael: foco A (Skill 8 faturando RECOMENDADO) | B (Skill 7 escriturando) | C (09b executor) | D (limpeza moves residuais) | E (caso real novo)
[ ] Se foco A/B/C: implementar via principal seguindo pattern Skills 4/5/6 (IMPLEMENTAR código = principal OK)
[ ] Se foco E: SPAWN gestor-estoque-odoo via Task tool (NÃO orquestrar do principal — regra inviolável 23)
[ ] Após writes em PROD: verificar resultado DIRETO no Odoo (regra inviolável 6)
[ ] Code-review paralelo (2 reviewers) ao fim da sessão
[ ] Atualizar ROADMAP_SKILLS HANDOFF + VALIDACAO §15 + memórias
[ ] Commit consolidado + atualizar este PROMPT_PROXIMA_SESSAO.md (v10)
```

## NÃO-FAZER (red flags v9)

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
- ❌ **(v8)** CANCELAR picking inteiro (caminho A) sem antes listar TODAS as MLs via Skill 9 modo pickings — se houver MLs válidas de outros cods, usar cirurgia (E)
- ❌ **(v8)** Pular zerar_reserved_residual após cirurgia que faz unlink de MLs — reserved fica negativo

---END---

## NOTAS PARA RAFAEL (não fazem parte do prompt)

- v8 fechou o caso 71 cods 100% (67/67 executáveis OK + 4 SKIP planejados). Total ~115 writes PROD da jornada v7+v7-extras+v8+cirurgia.
- Lição mais importante v8: **caminho E (cirurgia) é PREFERIDO sobre A (cancelar)** quando picking tem MIX MLs válidas + bloqueantes. Codificado como invariante #26 no prompt do gestor.
- Pattern v8 NOVO: `cirurgia → zerar_residual → MODO C` atomicamente destrava qualquer picking MIX. Validado FB/OUT/01046 (876 un, 23 MLs preservadas).
- Cosmético pendente: 3 moves residuais com qty=0 no FB/OUT/01046 — Odoo cancela automaticamente quando operador valida (não bloqueia).
- Próxima sessão (v9) RECOMENDADO: **Skill 8 faturando-odoo** (DESBLOQUEADA + última macro perigosa antes de fluxos inter-company completos). Cuidado SEFAZ irreversível.

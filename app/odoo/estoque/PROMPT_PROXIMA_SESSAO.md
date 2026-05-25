# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v10

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão. Mantém você dentro do plano global sem desviar.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, **commits ao fim de v9: bf53ea84 (v7) + 507e5e36 (v7-extras) + 4e30c468 (v8) + 6a73c6fa (v9) sobre `main`@b4f7b24c**). `main` continua VIVO em paralelo (Rafael commita lá) — verificar se avançou e considerar rebase incremental ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
```

## ✅ SKILL 6 CICLO COMPLETO em v9 (2026-05-25)

Capina `09b_executar_pre_etapa.py` (746 LOC) → `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (~580 LOC). Skill 6 passa de 4 modos → 5 modos:
- `planejar` (READ Odoo + grava JSON+Excel) — v6
- `propor` (WRITE banco local DELETE+INSERT) — v6
- `listar-onda` (READ + hash sha256) — v6
- `aprovar-onda` (WRITE banco local com hash check) — v6
- **`executar-onda` (WRITE Odoo via orchestrator C3 macro) — v9 NOVO** (compõe Skills 1+2 com guard delta_esperado propagado + auditoria + paralelização)

**Modernizações vs 09b legacy:**
- API v2: `transferir_quantidade_para_lote` v1 → v2 (guard CICLAMATO)
- PURO: `odoo.create('stock.quant')` direto → Skill 1 `ajustar_quant(criar_se_faltar=True, delta_esperado=qty)`
- Output: print/banner → dict JSON estruturado (regra v7)

**Pytest baseline: 251 verdes** (230 v8 + 21 orchestrator novo).
**Smokes C6**: 3 verdes (incluindo dry-run real com ajuste APROVADO id=163696 NEG 835k un — dispatch correto).

## ✅ CASO 71 cods 100% CONCLUÍDO em v8 (referência histórica)

A jornada v7 + v7-extras + v8 + cirurgia processou **~115 writes PROD, ~22.500 un transferidas** para FB/Indisponivel. Status final: 67/67 cods executáveis OK + 4 SKIP planejados.

## ⚠️ REGRAS INVIOLÁVEIS NOVAS (v7-extras + v8 + v9 — LER ANTES DE QUALQUER AÇÃO)

1. **EXECUTAR FLUXOS = subagente, NÃO principal** (v7-extras — lição que custou ~150k tokens em v7):
   - Para EXECUTAR fluxos sobre caso real, SEMPRE spawn `gestor-estoque-odoo` via Task tool.
   - Use o principal APENAS para IMPLEMENTAR átomos novos / debugar gaps arquiteturais / refatorar services.
   - Economia esperada: ~30-50% tokens em batches de 80+ chamadas.

2. **CIRURGIA (E) PREFERIDA sobre CANCELAR (A) quando picking tem MIX MLs válidas + bloqueantes** (v8):
   - SEMPRE listar TODAS as MLs do picking via Skill 9 modo pickings ANTES de cancelar.
   - Se houver >1 ML válida de outros cods/devoluções → USAR cirurgia (Skill 2.4 `cancelar_moves_orfaos` + `--zerar-residual` + Skill 2 MODO C).

3. **`--quiet` em CLIs estoque** (v7-extras): todos os 8 CLIs aceitam `--quiet`. Use SEMPRE em batches via subprocess. JSON output não é afetado.

4. **`--forcar-concorrencia`** (v7-extras): scripts CLI detectam concorrência via `pgrep -f`. Default = sys.exit(2). Use `--forcar-concorrencia` SÓ quando ciente.

5. **Log JSON é fonte de verdade** (v7): NUNCA confiar em `tee` background. Sempre parsear JSON do log salvo pelo script.

6. **(v9 NOVA) Pre-cond inviolável Skill 6 `executar-onda`**: ajustes status='APROVADO' obrigatório. Rodar `aprovar-onda` ANTES (que exige hash fresh de `listar-onda`).

7. **(v9 NOVA) Canary OBRIGATÓRIO antes de bulk `executar-onda`**: `--limite 1 --confirmar` + verificar Odoo direto ANTES de `--max-workers 5`. Sem canary, FALHAS bulk podem cascatear.

## PENDÊNCIAS RESIDUAIS

**ZERO pendências operacionais** do caso 71 cods + ZERO da Skill 6. Apenas pendências cosméticas:
- **3 moves residuais com qty=0 no picking FB/OUT/01046** (cosmético, aguarda validação manual no Odoo UI)
- **1 ajuste APROVADO real id=163696** (NEG cod=208000012 cid=4 qty=835.851,71 un MIGRAÇÃO) — aguardando aprovação do Rafael para canary `executar-onda --confirmar`

## FOCOS POSSÍVEIS PARA v10 (escolher 1 ao iniciar a sessão)

### Foco A: Skill 8 `faturando-odoo` (RECOMENDADO — DESBLOQUEADA pela ONDA 0.4 v3 + Skill 6 v9)
- Skill MACRO mais perigosa (NF→SEFAZ irreversível).
- Service `InventarioPipelineService` existe — capinar para `app/odoo/estoque/orchestrators/inventario_pipeline.py`. Pattern similar à Skill 6 v9 (orchestrator C3 macro compondo Skills 1+2+5).
- Pre-flight quarteto fiscal G035/G017/G007/G018 obrigatório.
- Smoke 1-ajuste antes de batch (regra inviolável SEFAZ).
- ~6-8h, ~200-300k tokens.
- Risco: ALTO (SEFAZ irreversível; robô CIEL IT externo timing).

### Foco B: Skill 7 `escriturando-odoo` (entrada IC + DFe)
- Pré-cond: Skill 2 ✅ + Skill 5 ✅. Mais simples que Skill 8 (sem SEFAZ direto).
- ~4-6h, ~150-200k tokens.

### Foco C: Smoke `executar-onda --confirmar` real em PROD (1 ajuste APROVADO id=163696)
- Canary do orchestrator pre_etapa_executor capinado em v9.
- 1 ajuste só (NEG cod 208000012 cid=4, 835k un MIGRAÇÃO).
- ~30min (canary dry-run + revisão Rafael + canary real + verificação Odoo).
- Risco: MÉDIO (valor alto 835k un + estado parcial se FALHA_AUMENTO).

### Foco D: Limpeza de moves residuais FB/OUT/01046 (manual no Odoo UI)
- Cancelar 3 moves (1161587, 1161611, 1161613) qty=0 após cirurgia v8.
- ~5min manual no Odoo UI (não há CLI — `stock.move._action_cancel` é privado G025).
- Cosmético, não-bloqueante.

### Foco E: Outro caso real que Rafael trouxer
- Subagente `gestor-estoque-odoo` já preparado com regras v7-v8-v9 codificadas.
- SEMPRE spawn via Task tool (regra inviolável 1).

## LEITURAS OBRIGATÓRIAS ANTES DE AGIR (ordem)

1. `app/odoo/estoque/CLAUDE.md` — constituição.
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF (estado v9 + próximos passos).
3. `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` §13 + §14 + **§15 v9** (sessão v9 09b capinado + smokes + decisões-chave).
4. `.claude/agents/gestor-estoque-odoo.md` — invariantes (9 regras: 5 originais + PRE-CHECK reserva v7 + EXECUTAR-FLUXOS-subagente v7-extras + CIRURGIA preferida v8 + log-JSON v7 + executor v9).
5. **Se foco = A (Skill 8 faturando)**:
   - `app/odoo/services/inventario_pipeline_service.py`
   - `docs/inventario-2026-05/02-gotchas/G004*.md`, `G011*.md`, `G016*.md`, `G023*.md` (já codificados em picking.py), `G035*.md`, `G017*.md`, `G007*.md`, `G018*.md` (quarteto fiscal pré-SEFAZ).
   - Memórias: `[[ciel_it_quirks]]`, `[[picking_317346_pendente]]`, `[[skill5_picking_pattern]]`, **[[skill6_planejar_pre_etapa_pattern]]** (pattern orchestrator C3 reaproveitável).
6. **Se foco = B (Skill 7 escriturando)**:
   - `docs/inventario-2026-05/02-gotchas/G023*.md`, `G034*.md`
   - Memória: `[[escrituracao_entrada_lf_dfe]]`
7. **Se foco = C (smoke executar-onda real)**:
   - `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (entry-point `executar_onda_pre_etapa`)
   - `.claude/skills/planejando-pre-etapa-odoo/SKILL.md` (sub-fluxo 4.1.e)
   - Comando: `python .claude/skills/planejando-pre-etapa-odoo/scripts/planejar_pre_etapa.py --modo executar-onda --company-id 4 --cod-produto 208000012 --usuario rafael --confirmar`
   - Antes: validar `--dry-run` retorna 1 APROVADO + plano coerente; verificar Odoo direto após `--confirmar`.
8. **Se foco = E (caso real)**:
   - Spawn `gestor-estoque-odoo` via Task tool com prompt curto descrevendo o caso
9. Memórias-chave gerais:
   - `[[arquitetura_orquestrador_odoo]]` — princípio fluxos>>skills
   - `[[caso_real_tratar_reservas_pre_transferencia]]` — caso v7+v8 RESOLVIDO 100%
   - `[[gotcha_g030_quant_id_store_false]]` — cross-ref via tupla
   - `[[fluxo_2_6_pattern]]` — pattern 5-caminhos + cirurgia v8
   - `[[skill5_picking_pattern]]` — pattern capinagem retroativa
   - **[[skill6_planejar_pre_etapa_pattern]]** — pattern orchestrator C3 macro v9 (reaproveitável para Skill 8)
   - `[[feedback_skills_demanda_driven]]` — skills nascem de casos reais
   - `[[feedback_incompletude_quebra_regras]]` — C7-C10 invioláveis

## REGRAS INVIOLÁVEIS (não negociáveis — herdadas + v7 + v8 + v9)

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
15. **(v6)** Skill 6 `pre_etapa.py`: pytest baseline 21 verdes.
16. **(v4)** Skill 2 `transfer.py`: pytest baseline 52 verdes. CUIDADO com modo C — invariante G031 crítica.
17. **(v3)** Skill 5 `picking.py`: pytest baseline 42 verdes. NÃO quebrar invariante G019/G020.
18. **(v5)** Skill 4 `mo.py`: pytest baseline 29 verdes. CUIDADO com guard G-MO-01.
19. **(v7)** Skill 9 `consulta_quant.py`: pytest baseline 19 verdes. NÃO usar `quant_id` direto (G030).
20. **(v7)** Skill 2.4 `reserva.py`: pytest baseline 15 verdes. `unreserve_picking` recusa state ∈ {done, cancel, draft}.
21. **(v7) PRE-CHECK reserva ANTES Skill 2**: SEMPRE verificar `reserved>0` via Skill 9.
22. **(v7) `stock.move.line.quant_id` é COMPUTED `store: False`** (G030).
23. **(v7-extras) EXECUTAR FLUXOS = subagente, NÃO principal**.
24. **(v7-extras) `--quiet` em batches** + `--forcar-concorrencia` SÓ quando ciente.
25. **(v7-extras) Log JSON é fonte de verdade** — não confiar em `tee` background.
26. **(v8) CIRURGIA (E) PREFERIDA sobre CANCELAR (A) em pickings MIX**.
27. **(v8) Pattern atômico cirurgia → zerar_residual → MODO C**.
28. **(v9 NOVA) Skill 6 `pre_etapa_executor.py`: pytest baseline 21 verdes**. Total Skill 6: 42 verdes (21 service + 21 orchestrator).
29. **(v9 NOVA) `executar-onda` exige status='APROVADO'** — rodar `aprovar-onda` antes.
30. **(v9 NOVA) Canary OBRIGATÓRIO em `executar-onda` real**: `--limite 1 --confirmar` + verificar Odoo direto ANTES de `--max-workers 5`.
31. **(v9 NOVA) `--max-workers > 5` sobrecarrega Odoo XML-RPC** — sweet spot é 5; serial (1) é seguro.

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
4  Planejamento + EXECUÇÃO de ajustes (READ Odoo + WRITE banco local + WRITE Odoo C3)
   4.1 PRE-ETAPA inventario CD/FB D007 (5 modos: planejar+propor+listar+aprovar+EXECUTAR-ONDA v9)
                                            → planejando-pre-etapa-odoo 🟡 [folha 4.1]
```

## CHECKLIST DA SESSÃO v10

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar se main avançou: git fetch origin main && git log --oneline 6a73c6fa..origin/main
[ ] Se avançou: rebase incremental ANTES de iniciar
[ ] Pytest baseline: 251 verdes esperado (rodar full suite estoque)
[ ] Ler ROADMAP_SKILLS HANDOFF + VALIDACAO §13+§14+§15 + 5 memórias-chave (incluindo skill6_planejar_pre_etapa_pattern v9)
[ ] AskUserQuestion com Rafael: foco A (Skill 8 faturando RECOMENDADO) | B (Skill 7 escriturando) | C (smoke executar-onda real id=163696) | D (limpeza moves residuais) | E (caso real novo)
[ ] Se foco A/B: implementar via principal seguindo pattern Skill 6 v9 (orchestrator C3 macro reaproveitável)
[ ] Se foco C: spawn gestor-estoque-odoo via Task tool (regra inviolável 23 — executar fluxos = subagente)
[ ] Se foco E: SPAWN gestor-estoque-odoo via Task tool
[ ] Após writes em PROD: verificar resultado DIRETO no Odoo (regra inviolável 6)
[ ] Code-review paralelo (2 reviewers) ao fim da sessão
[ ] Atualizar ROADMAP_SKILLS HANDOFF + VALIDACAO §16 + memórias
[ ] Commit consolidado + atualizar este PROMPT_PROXIMA_SESSAO.md (v11)
```

## NÃO-FAZER (red flags v10)

- ❌ Criar scripts ad-hoc em `scripts/inventario_2026_05/` (capinar a skill)
- ❌ Implementar átomos previstos sem demanda real
- ❌ Marcar C# como ✅ sem entregar artefato concreto
- ❌ Modificar `quant.py`, `transfer.py`, `picking.py`, `reserva.py`, `mo.py`, `pre_etapa.py`, `consulta_quant.py`, **`pre_etapa_executor.py`** sem rodar pytest ANTES e DEPOIS
- ❌ Compor átomos sem propagar `delta_esperado`
- ❌ Usar `datetime.now()` em código novo (hook bloqueia)
- ❌ Filtrar `stock.move.line` por `quant_id` direto (G030)
- ❌ Cancelar MO com `consumo_total > 0` sem unbuild (G-MO-01)
- ❌ Quebrar G019/G020 em `picking.py` (re-abre ONDA 0.4)
- ❌ Quebrar G031 em Skill 2 modo C (MIGRAÇÃO POR PRODUTO)
- ❌ **(v7-extras)** ORQUESTRAR FLUXOS do agente principal (use subagente)
- ❌ **(v7-extras)** Rodar batch SEM `--quiet`
- ❌ **(v7-extras)** Confiar em `tee` background — parsear JSON do log salvo
- ❌ **(v7-extras)** Disparar batch sem checar concorrência via `pgrep -f`
- ❌ **(v8)** CANCELAR picking inteiro (caminho A) sem antes listar TODAS as MLs via Skill 9
- ❌ **(v8)** Pular zerar_reserved_residual após cirurgia que faz unlink de MLs
- ❌ **(v9)** Rodar `executar-onda --confirmar` sem canary `--limite 1 --confirmar` antes — cascateia FALHAs em produtos similares
- ❌ **(v9)** `executar-onda --max-workers > 5` — sobrecarrega Odoo XML-RPC (sweet spot 5; serial 1 é seguro)
- ❌ **(v9)** Re-rodar `executar-onda` sobre ajustes FALHA sem corrigir root cause — FALHA fica até operador alterar manualmente para APROVADO

---END---

## NOTAS PARA RAFAEL (não fazem parte do prompt)

- v9 fechou o ciclo da Skill 6 (5 modos: planejar→propor→listar→aprovar→executar). Orchestrator C3 macro `pre_etapa_executor.py` compõe Skills 1+2 com guard delta_esperado propagado.
- Pattern reaproveitável para Skill 8 faturando-odoo (próxima sessão recomendada): mesmo pattern de orchestrator C3 em `orchestrators/`, mesmas regras de helpers privados + auditoria + paralelização + modo dry-run/confirmar.
- 1 ajuste APROVADO real existe (id=163696 NEG cod=208000012 cid=4 qty=835.851,71 un MIGRAÇÃO). Aguardando aprovação para canary `executar-onda --confirmar`. **Cuidado**: valor alto, verificar Odoo diretamente após canary.
- Pytest baseline saltou de 230 → 251 (+21 testes orchestrator). 16 scripts SUPERADOS (era 15 + 09b v9).
- Próxima sessão (v10) RECOMENDADO: **Skill 8 faturando-odoo** (última macro perigosa antes de fluxos inter-company completos). Pattern Skill 6 v9 orchestrator é reaproveitável.

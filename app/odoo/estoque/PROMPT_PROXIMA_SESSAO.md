# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo)

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão. Mantém você dentro do plano global sem desviar.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, base ainda em `main`@b4f7b24c — nada commitado ainda na branch). `main` continua VIVO em paralelo (Rafael commita lá) — verificar se avançou e considerar rebase incremental ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^ODOO_' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
```

## FOCO RECOMENDADO: Skill 4 `operando-mo-odoo` (próxima ordem bottom-up)

**Por quê:**
1. **Bottom-up correto**: única skill WRITE intra-estoque restante (depois Skill 7 escriturar + Skill 8 faturar = macros perigosos).
2. **Service GAP** — criar do zero (`app/odoo/estoque/scripts/mo.py` + `StockMOService`). Sem capinagem de service legado.
3. **Gotchas claros e específicos**:
   - `consumo>0` cancelamento = furo contábil (bloquear).
   - `manual_consumption` não reserva via `action_assign` (caso real PROD documentado).
   - Componente preso em local errado (Indisponivel/Estoque vs location_src declarado da MO).
4. **Demanda recorrente**: cancelar MO antigas/obsoletas em FB e CD é operação periódica.
5. **Não-irreversível** (diferente de Skill 8 SEFAZ); operação segura para experimentar pattern.

**Escopo da Skill 4 (C1 mineração inicial):**

- **Scripts-fonte conhecidos no MAPA_SCRIPTS:**
  - `cancelar_mos.py` (base argparse, filtro data/estado).
  - `14_cancelar_mos_antigas_fb.py` (filtro `consumo=0`; sub-locais Pré-Prod).
- **Operações esperadas (átomos compostos):**
  - `cancelar_mo(mo_id, motivo)` — wrapper sobre `mrp.production.action_cancel`. Guard: `consumo_total > 0` → bloqueia (furo contábil).
  - `cancelar_mo_em_massa(filtro_mos, max_n)` — batch com filtros (data, estado, ausência de consumo).
  - `criar_mo(args)` — produção manual a partir de BOM. Apenas se demanda real surgir.
  - `alterar_mo(mo_id, args)` — mudar location_src/quantidade. Caso real PROD documentado em `[[mo_componente_local_consumo]]`.
- **Gotchas-invariante a codificar:**
  - **G-MO-01** (consumo > 0 = furo): bloquear cancelamento; usar `unbuild` em vez de `action_cancel` se preciso reverter consumo (cross-skill com Skill 1).
  - **G-MO-02** (`manual_consumption` ≠ `action_assign`): MO com `manual_consumption=True` exige preencher `move_line.qty_done` manualmente; `action_assign` não reserva.
  - **G-MO-03** (componente em local errado): MO `confirmed` com componente em Indisponivel/Estoque (não no `location_src` declarado) → MO trava. Fix: transferência interna (Skill 2 modo B) ANTES de `action_assign`.
  - **G-MO-04** (`picked=True` em MO `to_close/done`): não mexer; herdado de Skill 2.4 G026.

**Alternativa válida 1**: **Skill 8 `faturando-odoo`** se houver demanda urgente para faturamento inter-company. **AGORA DESBLOQUEADA** pela ONDA 0.4 fechada (Skill 5 v3 codificou invariante G019/G020). Service `InventarioPipelineService` já existe; falta capinagem + SKILL.md + CLI. **MACRO perigoso** (NF→SEFAZ irreversível); requer cuidado especial. ~6-8h.

**Alternativa válida 2**: **Fluxos compostos** da Skill 2 (`2.2.D010`, `2.2.D012`, `2.2.D013`) — folhas filhas cobrindo orquestradores de planilha (15, 15r, transferir_lote, transferir_local_pasta22, ajuste_fb_cd_indisponivel, mover_migracao, relotar). Implementar SOMENTE se padrão se repetir com 2+ casos reais cada.

## Estado atual (sessão 2026-05-24 v4 fechada — Skill 2 modo C + ONDA 0.4 fechada + incidente G031 + fix)

**5 skills no catálogo do `gestor-estoque-odoo`:**
- ✅ **Skill 1 `ajustando-quant-odoo`** MATURADA — 100 ajustes PROD 2026-05-23; 30 pytest; 5 scripts SUPERADOS; guard `delta_esperado`.
- 🟡 **Skill 2 `transferindo-interno-odoo`** mín viável + **MODO C PROD** — 55 pytest (modo C +18 testes); 2 scripts SUPERADOS; **3 modos atômicos** (A lote→lote / B loc→loc / **C `--para-indisponivel` cross loc+lote consolidando MIGRAÇÃO POR PRODUTO**); delega `ajustar_quant`×2; G021/G022/G027/**G031** codificados; **1 execução PROD validada** (4.319 un em 23s pós-incidente G031 + fix; rollback testado).
- 🟡 **Skill 2.4 `operando-reservas-odoo`** mín viável — 3 átomos validados PROD 2026-05-23 (6 pickings + 15 quants).
- 🟡 **Skill 5 `operando-picking-odoo`** mín viável — 42 pytest; 3 átomos (cancelar, validar com G019/G020 invariante, devolver idempotente); **FECHA ONDA 0.4**; 1 script SUPERADO; 6 casos dry-run PROD 100% bate.
- 🟡 **Skill 9 `consultando-quant-odoo`** mín viável (READ ancillary) — 2 átomos.

**Marcos da sessão v4:**
- **MODO C `transferir_para_indisponivel`** estreou em PROD: 1ª `--confirmar` falhou 16/16 (incidente G031); rollback 100% via Skill 1; fix arquitetural (resolver MIGRAÇÃO POR PRODUTO via `lot_svc.criar_se_nao_existe`); 2ª `--confirmar` 16/16 OK em 23s.
- **G031 documentado**: `docs/inventario-2026-05/02-gotchas/G031-lot-migracao-por-produto.md`. Constant `LOTES_MIGRACAO_POR_COMPANY` deprecada com `DeprecationWarning`. Zero callers reais confirmado por grep.
- **CR3#7 fix**: `scripts/inventario_2026_05/fat_lf_cleanup.py:41` tinha mesmo bug `create_returns` parser que `picking.devolver` pré-v3 — sincronizado (aceita 3 shapes: dict/int/list).
- **`rollback_hint`** machine-readable em `FALHA_AUMENTO` (transferir_para_indisponivel) — operador-acionável.

**12 scripts em `_validados/`** (5 ajustando-quant + 3 operando-reservas + 2 transferindo-interno + 1 operando-picking). **~94 scripts ad-hoc continuam VIVOS** (operação viva).

**Pytest baseline: 146 verdes** (30 quant + 55 transfer + 19 lot + 42 picking).

## LEITURAS OBRIGATÓRIAS ANTES DE AGIR (ordem)

1. `app/odoo/estoque/CLAUDE.md` — constituição (§1 princípio fundador, §4 fluxos>>skills, §6 catálogo com 5 skills + ONDA 0.4 ✅, §8 invariantes, §12 invariantes execução).
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF (estado v4 + próximos passos + ordem bottom-up atualizada).
3. `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` §9 (Skill 2 v4 + MODO C + incidente G031 + 17 findings code-review + pre-mortem 4 dimensões).
4. **NOVO para Skill 4**:
   - `docs/inventario-2026-05/02-gotchas/G031-lot-migracao-por-produto.md` — lição arquitetural sobre constants `lot_id`/`*_id_por_company`.
   - `app/odoo/constants/picking_types.py` — IDs por company (analisar se há picking_type específico para MO; ver `mrp_production` picking_type 12/22 etc).
   - `.claude/references/odoo/MODELOS_CAMPOS.md` — campos de `mrp.production`, `mrp.bom`, `stock.move` (consumo via `move_raw_ids`).
   - `.claude/references/odoo/GOTCHAS.md` — buscar gotchas existentes sobre MO (G026 picked=True).
5. **Memórias-chave**:
   - `[[arquitetura_orquestrador_odoo]]` — princípio das 5 camadas + fluxos>>skills.
   - `[[skill5_picking_pattern]]` — pattern Skill 5 (referência para capinagem/atomo NOVO).
   - `[[skill2_transfer_interno_pattern]]` — pattern composição (`ajustar_quant`×2 + `delta_esperado`) + **§incidente G031 v4** + MODO C.
   - `[[mo_componente_local_consumo]]` — caso real PROD 2026-05-20 (G-MO-03).
   - `[[reaproveitar-semiacabado-orfao-mo-cancelada]]` — caso real PROD 2026-05-22 (interação MO + unbuild + cross-skill).
   - `[[feedback-skills-demanda-driven]]` — skills nascem de casos reais; átomos previstos permanecem ⬜ até demanda surgir.
   - `[[feedback-incompletude-quebra-regras]]` — C7-C10 INVIOLÁVEIS.

## REGRAS INVIOLÁVEIS (não negociáveis)

1. **`--dry-run` antes do real**; confirmação explícita antes de SEFAZ/irreversível.
2. **NUNCA criar script ad-hoc** — capinar a skill. Workspace `/tmp/` é OK (descartável).
3. **`fluxos>>skills`** — caso novo = folha de fluxo, NÃO skill nova.
4. **Skills nascem de DEMANDAS REAIS** — não implementar átomos especulativamente. **PARA SKILL 4**: justificar cada átomo novo com caso real ou bug ABERTO documentado.
5. **C7-C10 são INVIOLÁVEIS** — completar cada checkpoint com artefato concreto.
6. **Verificar resultado DIRETO no Odoo** — não confiar só no output. **CRÍTICO para Skill 4** dado G-MO-01 (consumo=0 não garante reversibilidade contábil; sempre confirmar via UI após write).
7. **Operação VIVA** — preservar ad-hocs até cada átomo maturar; arquivar SUPERADO só após C9.
8. **Premissas pesquisadas e validadas ANTES de compor átomos.**
9. **Após qualquer `unlink` em MLs em quants com `reserved=0`**: chamar `zerar_reserved_residual` (G027 da skill 2.4).
10. **Ao retomar FALHAs**: cruzar `mo_id`/`quant_id`/etc. com pedido original — NÃO aplicar política homogênea.
11. **Composição de átomos propaga `delta_esperado` a CADA chamada** (regra inviolável 11 — herda dos modos A/B/C da Skill 2).
12. **`--corrigir-para-esperado` em batch SEMPRE rodar `--dry-run` primeiro** e revisar manualmente.
13. **Antes de modificar `app/odoo/estoque/scripts/quant.py`**: pytest baseline 30 verdes.
14. **Antes de modificar `app/odoo/estoque/scripts/transfer.py`**: pytest baseline 55 verdes (3 modos: A 33 + B 4 + C 18). **CUIDADO** com modo C — invariante G031 (resolver MIGRAÇÃO POR PRODUTO) é crítica; quebrá-la repete o incidente PROD.
15. **Antes de modificar `app/odoo/estoque/scripts/picking.py`**: pytest baseline 42 verdes. **CUIDADO** especial com `validar()` e `liberar_faturamento()` (invariante G019/G020 que destrava Skill 8 — quebrá-las re-abre a ONDA 0.4).
16. **TIMEZONE**: NUNCA `datetime.now()` em código novo — usar `from app.utils.timezone import agora_brasil_naive` (regra `.claude/references/REGRAS_TIMEZONE.md`; hook `ban_datetime_now.py` BLOQUEIA Edit/Write).
17. **(NOVO Skill 4) G-MO-01 furo contábil**: NUNCA cancelar MO com `consumo_total > 0` sem `unbuild` prévio. Skill 4 DEVE bloquear default — `--forcar-com-consumo` exige `--confirmar` extra.
18. **(NOVO pós-G031) `stock.lot` é POR PRODUTO**: NUNCA usar `lot_id` de constant (`LOTES_*_POR_COMPANY`) como FK universal. SEMPRE resolver via `lot_svc.buscar_por_nome(nome, product_id, company_id)` ou `lot_svc.criar_se_nao_existe(...)`. Aplica a TODAS as skills futuras (Skill 4 MO usa `lot_id` em `move_raw_ids` e `move_finished_ids` — checar).
19. **(NOVO pós-G031) Constants `_id_POR_COMPANY`**: antes de usar como FK em WRITE, verificar se o ID é **uma-por-company** (OK: `COMPANY_LOCATIONS`, `LOCAIS_INDISPONIVEL`, `COMPANY_PARTNER_ID`) ou **um-por-produto/instância** (RISCO: `LOTES_MIGRACAO_POR_COMPANY` ← deprecated).
20. **`rollback_hint` em FALHA_AUMENTO**: composições atomicas DEVEM reportar `rollback_hint` machine-readable (chamada exata `ajustar_quant` para reverter) — pattern estabelecido em Skill 2 modo C (CR3#5).

## ARQUITETURA — relembrar a árvore de decisão

```
1  NF inter-company (emissão/SEFAZ entre filiais)
   1.1  só faturamento (saída)              → fluxos/1.1.* (faturando-odoo ⬜ DESBLOQUEADA pós-ONDA 0.4)
   1.2  só entrada/escrituração
        1.2.1 inventário (DFe próprio)      → fluxos/1.2.1 (escriturando-odoo ⬜)
        1.2.2 COMPRAS (DFe fornecedor)      → DELEGAR a gestor-recebimento
   1.3  transferência completa              → fluxos/1.3 ⬜
2  Estoque (SEM NF — galho 1.x se com NF)
   2.1 ajuste de saldo (1 quant; planilha)  → ajustando-quant-odoo ✅ [folha 2.1]
   2.2 realocar saldo (lote↔lote / loc↔loc / **MIGRA↔Indisp via MODO C atômico v4**)
                                            → transferindo-interno-odoo 🟡 [folha 2.2] (3 modos)
   2.3 transferir saldo entre CÓDIGOS       → (skill transferencia-saldo-codigo) ⬜
   2.4 cancelar reserva / cirurgia ML       → operando-reservas-odoo 🟡 [folha 2.4]
   2.5 cancelar/validar/devolver picking    → operando-picking-odoo 🟡 [folha 2.5]
   2.9 CONSULTA AO VIVO (quants/MLs)        → consultando-quant-odoo 🟡 [folha 2.9]
3  Produção / PCP
   3.1 cancelar/criar/alterar MO            → operando-mo-odoo ⬜  ← FOCO PROPOSTO
```

## CHECKLIST DA SESSÃO

```
[ ] Setup (cd worktree + venv + ODOO_*)
[ ] Verificar se main avançou: git fetch origin main && git log --oneline b4f7b24c..origin/main
[ ] Se avançou: rebase incremental ANTES de iniciar
[ ] Pytest baseline: pytest tests/odoo/services/test_stock_quant_adjustment_service.py test_stock_internal_transfer_service.py test_stock_lot_service.py test_stock_picking_service.py (esperado: 146 verdes)
[ ] Ler ROADMAP_SKILLS HANDOFF + VALIDACAO_FINAL_SESSAO §9 + G031 + memórias-chave
[ ] Confirmar com Rafael: Skill 4 MO (foco recomendado), Skill 8 faturando (desbloqueada), fluxos compostos Skill 2, ou outra prioridade
[ ] Se Skill 4: C1 mineração — ler integral `cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py` + memória [[mo_componente_local_consumo]] + [[reaproveitar-semiacabado-orfao-mo-cancelada]]
[ ] Investigar AO VIVO 1 MO real em FB/CD via Skill 9 (consultar `mrp.production`)
[ ] Service novo `app/odoo/estoque/scripts/mo.py` — criar do zero seguindo pattern Skill 5 (capinada) ou Skill 1 (do zero)
[ ] Cada átomo novo: C1-C10 SEM PULAR ETAPAS
[ ] Testes pytest cobrindo gotchas-invariante ANTES do C2 final (lição Skill 5 v3)
[ ] Smoke test 1-MO em PROD antes de batch (lição Skill 2 v4)
[ ] Validar resultado direto no Odoo (regra inviolável 6)
[ ] Final da sessão: N code-reviewers paralelos + atualizar VALIDACAO_FINAL_SESSAO §N + memórias + PROMPT_PROXIMA_SESSAO
```

## NÃO-FAZER (red flags)

- ❌ Criar scripts ad-hoc em `scripts/inventario_2026_05/` (capinar a skill)
- ❌ Implementar átomos previstos sem demanda real
- ❌ Marcar C# como ✅ sem entregar o artefato concreto
- ❌ Responder com números vagos (sempre verificar somatória bate com input)
- ❌ Aplicar `Δ=-qty_atual` em retomada sem cruzar pedido original (use `--delta-esperado <pedido>`)
- ❌ Pular `zerar_reserved_residual` após unlink de MLs em quants já com `reserved=0`
- ❌ Mover scripts para `_validados/` sem corrigir `sys.path` `parents[2]→parents[4]`
- ❌ Tocar `main` (worktree `feat/estoque-odoo` — coordenar merge depois)
- ❌ Modificar `quant.py`, `transfer.py`, `picking.py`, ou `reserva.py` sem rodar pytest ANTES e DEPOIS
- ❌ Compor átomos sem propagar `delta_esperado` (regra inviolável 11)
- ❌ Usar `datetime.now()` em código novo (regra inviolável 16 — hook bloqueia)
- ❌ Quebrar invariante G019/G020 em `picking.py` `validar()`/`liberar_faturamento()` (re-abre ONDA 0.4)
- ❌ Quebrar invariante G031 em Skill 2 modo C — `transferir_para_indisponivel` DEVE usar `lot_svc.criar_se_nao_existe` POR PRODUTO (re-introduzir constant universal repete incidente PROD)
- ❌ (NOVO Skill 4) Cancelar MO com `consumo_total > 0` sem unbuild — furo contábil garantido (G-MO-01)
- ❌ (NOVO Skill 4) Confiar em `action_assign` reservar componente de MO com `manual_consumption=True` — não funciona (G-MO-02)
- ❌ (NOVO pós-G031) Usar `LOTES_MIGRACAO_POR_COMPANY` (ou qualquer constant `lot_id`) como FK em `stock.quant.create`/`write` — SEMPRE resolver POR PRODUTO via `lot_svc`
- ❌ Compor átomo de operação parcialmente irreversível sem reportar `rollback_hint` machine-readable (lição CR3#5 Skill 2 v4)

## Logs de auditoria

### Sessão 23/05 (104 ajustes negativos + cirurgia em 6 pickings)
```
scripts/inventario_2026_05/auditoria/
  log_2.1_ajuste_planilha_*.json   (4 logs)
  log_2.4_operar_reservas_*.json
  log_2.4_zerar_reserved_residual_*.json
```

### Sessão 24/05 v1 cleanup
```
scripts/inventario_2026_05/auditoria/
  log_2.1_reversao_ciclamato_20260524_000000.json
  log_2.4_zerar_residual_orfao_aroma_20260524_000001.json
/tmp/comunicado_pickings_20260524.md
```

### Sessão 24/05 v2 Skill 2 (sem --confirmar)
```
/tmp/log_skill2_C6_validacao_dry_run.json  (3 casos)
docs/inventario-2026-05/consolidacao/MINERACAO_SKILL2_2026_05_24.md  (versionado)
```

### Sessão 24/05 v3 Skill 5 (sem --confirmar)
```
/tmp/log_skill5_C6_validacao_dry_run.json  (6 casos vs PROD)
```

### Sessão 24/05 v4 Skill 2 modo C (incidente + rollback + fix + sucesso)
```
scripts/inventario_2026_05/auditoria/
  log_2.2_para_indisp_20260524_105037.json          (1ª --confirmar — FALHA 16/16 G031)
  log_2.1_ROLLBACK_para_indisp_falha_20260524_105219.json  (rollback 100% OK em ~10s)
  log_2.2_para_indisp_FIX_20260524_110128.json      (2ª --confirmar — OK 16/16 em 23s, 4.319 un)
/tmp/skill2_modoC_dry_run_14_casos.json             (dry-run pré-fix)
```

Comece pela leitura dos 5 docs obrigatórios (CLAUDE.md + ROADMAP + VALIDACAO §9 + G031 + memórias). Verificar pytest baseline 146 verdes. Confirme com Rafael o foco da sessão. **Recomendação**: Skill 4 `operando-mo-odoo` (próxima na ordem bottom-up; service GAP do zero; gotchas claros G-MO-01/02/03/04). Antes de qualquer write em PROD: smoke test 1-MO + verificação direta no Odoo + pytest baseline pós-mudança.

---END---

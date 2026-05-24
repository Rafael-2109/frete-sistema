# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo)

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão. Mantém você dentro do plano global sem desviar.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, **commit atual `b8ed3b5c` — base `main`@b4f7b24c + 2 commits feat/estoque-odoo**). `main` continua VIVO em paralelo (Rafael commita lá) — verificar se avançou e considerar rebase incremental ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^ODOO_' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
```

## FOCO RECOMENDADO: Skill 8 `faturando-odoo` (DESBLOQUEADA pela ONDA 0.4)

**Por quê:**
1. **Macro perigoso DESBLOQUEADO**: ONDA 0.4 fechada em 2026-05-24 v3 codificou G019/G020 no `picking.py` (re-le state pós-button_validate, raise se != 'done'). Skill 8 agora pode confiar em `svc.validar()` sem false-positives.
2. **Service existe** (`InventarioPipelineService` em `app/odoo/services/inventario_pipeline_service.py`) — capinagem retroativa para `app/odoo/estoque/orchestrators/inventario_pipeline.py` + shim. Pattern Skill 5.
3. **Ordem bottom-up correta** após Skill 4: todas as skills WRITE intra-estoque estão ✅/🟡 mín viável; Skill 8 é a última macro perigosa antes de fluxos inter-company.
4. **Gotchas conhecidos** (~20 documentados em docs/inventario-2026-05/02-gotchas/): G004 (picking→robô→SEFAZ), G011 (preencher qty_done), G016 (SSL crash), quarteto fiscal pré-SEFAZ G035/G017/G007/G018, G028 (over-reservation). G019/G020 já codificados.
5. **CRÍTICO: irreversível** (NF→SEFAZ). Cuidado especial: smoke 1 ajuste antes de batch; verificar invoice criada por robô CIEL IT em cada caso.

**Escopo da Skill 8 (C1 mineração inicial):**

- **Scripts-fonte conhecidos no MAPA_SCRIPTS:**
  - `09_executar_onda1_bulk` (pipeline macro A-F — etapa única).
  - `09c_executar_onda2_fb_cd` (transfer_only etapas 19-37 — saída inter-company FB↔CD).
  - `fat_lf_02_carregar` (TIPO→ação driver).
  - `fat_lf_04_executar` (driver etapas B-F).
  - `fat_lf_05_executar_clean` (G028 reserva multi-lote pós-rename).
  - `fat_lf_cleanup` (devolução/cancelamento — já parcialmente capinado em Skill 5 `devolver`).
  - `fat_lf_resume.sh` (loop B→D SSL-resiliente).
  - `teste_210030325` (caso isolado para exemplo no fluxo).
- **Operações esperadas (átomos macro + etapas para recuperação):**
  - `faturar_ajuste(ajuste_id)` (macro A-F) — picking → reservar → preencher qty_done → validar (Skill 5 ✅) → liberar_faturamento → aguardar invoice robô CIEL IT.
  - `faturar_etapa_x(ajuste_id, etapa)` — etapas isoladas para recuperar de falhas parciais.
  - `faturar_em_massa(criterio)` — batch sobre N ajustes (canary `--limite 1` obrigatório).
- **Gotchas-invariante a codificar:**
  - **G004** (assinatura do átomo): picking → robô CIEL IT → SEFAZ. Estrutural, não validador.
  - **G011** (preencher qty_done): pipeline preenche antes de chamar `validar()` (não delegar a caller externo — fazer parte do átomo).
  - **G016** (SSL crash loop F5e): retry + keepalive na conexão.
  - **G019/G020** (já codificados em Skill 5 `picking.py` — usar `svc.validar()`).
  - **Quarteto fiscal pré-SEFAZ (G035/G017/G007/G018)**: validador checa+corrige+bloqueia ANTES de transmitir (gtin_validator). Pre-flight obrigatório.
  - **G028** (consolidar_move_lines pós-rename): chamada via `svc.validar(linhas_esperadas=)` (Skill 5 já cobre).
  - **Quarteto fiscal pré-SEFAZ**: NCM false, custo zero, weight zero, barcode inválido → quebra SEFAZ Schema 225. Validador deve corrigir+bloquear.
  - **Ordem**: faturar→entrada; sleep; validar→liberar (guard clauses entre átomos).
  - **Tempo irredutível**: robô CIEL IT externo — polling+timeout dá resultado determinístico, NUNCA tempo fixo.

**Alternativa válida 1**: **Skill 7 `escriturando-odoo`** (SÓ ENTRADA — DFe próprio → in_invoice → saldo). Pré-requisito: contrato estável de transfer (Skill 2 ✅) e picking (Skill 5 ✅). Mais simples que Skill 8 (sem SEFAZ direto). Cobre `entrada_fb_piloto` etapas 0-18, `escriturar_dfe_lf` (Fluxo A inventário, NÃO reusa RecebimentoLf). ~4-6h.

**Alternativa válida 2**: **Fluxos compostos** da Skill 2 (`2.2.D010`, `2.2.D012`, `2.2.D013`) — folhas filhas cobrindo orquestradores de planilha (15, 15r, transferir_lote, transferir_local_pasta22, ajuste_fb_cd_indisponivel, mover_migracao, relotar). Implementar SOMENTE se padrão se repetir com 2+ casos reais cada.

**Alternativa válida 3**: **Skill 6 `planejando-pre-etapa-odoo`** (planner READ+valida; isolado). Cobre `03b_planejar_pre_etapa_cd`, `04b_propor_pre_etapa_cd`, `09b_executar_pre_etapa`. Service existe (`PreEtapaEstoqueService`); falta SKILL.md + CLI + folha de fluxo. Bom para quebrar inércia se Skill 8 parecer pesada demais.

## Estado atual (sessão 2026-05-24 v5 fechada — Skill 4 NOVA + 175 pytest verdes)

**5 skills no catálogo do gestor-estoque-odoo:**
- ✅ Skill 1 `ajustando-quant-odoo` MATURADA — 100 ajustes PROD 2026-05-23; 30 pytest; 5 scripts SUPERADOS; guard delta_esperado.
- 🟡 Skill 2 `transferindo-interno-odoo` mín viável + MODO C PROD — 52 pytest (modo C +15 testes); 2 scripts SUPERADOS; 3 modos atômicos (A lote→lote / B loc→loc / C `--para-indisponivel` cross loc+lote consolidando MIGRAÇÃO POR PRODUTO); delega `ajustar_quant`×2; G021/G022/G027/G031 codificados; 1 execução PROD validada (4.319 un em 23s pós-incidente G031 + fix; rollback testado).
- 🟡 Skill 2.4 `operando-reservas-odoo` mín viável — 3 átomos validados PROD 2026-05-23 (6 pickings + 15 quants).
- 🟡 Skill 5 `operando-picking-odoo` mín viável — 42 pytest; 3 átomos (cancelar, validar com G019/G020 invariante, devolver idempotente); FECHA ONDA 0.4; 1 script SUPERADO; 6 casos dry-run PROD 100% bate.
- 🟡 **Skill 4 `operando-mo-odoo` mín viável NOVA (2026-05-24 v5)** — 1ª skill WRITE criada do zero (sem service legado em `services/`); 29 pytest (26 baseline + 3 cobrindo code-review fixes); 2 átomos (`cancelar_mo` + `cancelar_mos_em_massa`) + helper `medir_consumo_mo`; guard G-MO-01 INVIOLÁVEL (consumo>0 = furo contábil; CLI V1 NÃO expõe `forcar_consumo`); G019-like re-le state pós action_cancel; idempotência state=cancel = NOOP validada AO VIVO em FB/OP/BALDE/00009; status NOVO `cancel_deleted` para cascade customizado Odoo; 4 dry-run PROD 100% bate; 2 scripts SUPERADOS; 9 code-review findings (4 HIGH + 4 MED + 1 LOW) aplicados.
- 🟡 Skill 9 `consultando-quant-odoo` mín viável (READ ancillary) — 2 átomos.

**Marcos da sessão v5:**
- Skill 4 criada do zero seguindo pattern Skill 1 (sem service legado para capinar) — pattern mais limpo que Skill 5 (capinagem retroativa).
- Investigação AO VIVO ANTES do C1 final revelou volumes reais (FB 10k+ MOs, CD 17, LF 3.4k), idempotência action_cancel não documentada, campo `qty_produced` ≠ consumo.
- Princípio demanda-driven validado novamente: `criar_mo` e `alterar_mo` NÃO implementados (sem caso real isolado); `alterar_mo` é fluxo cross-skill (ver [[mo_componente_local_consumo]]); `mrp.unbuild` documentado mas skill separada (futura).
- Code-review paralelo (code + docs) pegou 9 bugs ortogonais — pattern reaproveitável.
- Auditoria G031 callers reais: **ZERO** (pendência §9.7 v4 ✅ RESOLVIDA — só 2 matches em docs descrevendo o incidente).

**13 scripts em `_validados/`** (5 ajustando-quant + 3 operando-reservas + 2 transferindo-interno + 1 operando-picking + 2 operando-mo). ~92 scripts ad-hoc continuam VIVOS (operação viva).

**Pytest baseline: 175 verdes** (30 quant + 52 transfer + 19 lot + 42 picking + 29 mo + 3 CR fixes). 5 falhas em `test_inventario_pipeline_service.py` são **pré-existentes** (não relacionadas a estoque-odoo; Skill 8 capinará esse service).

## LEITURAS OBRIGATÓRIAS ANTES DE AGIR (ordem)

1. `app/odoo/estoque/CLAUDE.md` — constituição (§1 princípio fundador, §4 fluxos>>skills, §6 catálogo com 5 skills WRITE + 1 READ, §8 invariantes, §12 invariantes execução).
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF (estado v5 + próximos passos + ordem bottom-up atualizada).
3. `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` §10 (Skill 4 v5 + pre-mortem 4 dimensões + 9 findings code-review).
4. `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` §9 (Skill 2 v4 + MODO C + incidente G031 + 17 findings code-review).
5. **Se foco = Skill 8 `faturando-odoo`** (recomendado):
   - `app/odoo/services/inventario_pipeline_service.py` (service legado a capinar; ~20 gotchas codificados).
   - `docs/inventario-2026-05/02-gotchas/G004-padrao-real-eh-picking-robo-CIEL-IT.md` — assinatura do átomo macro.
   - `docs/inventario-2026-05/02-gotchas/G011-preencher-qty-done-faltando.md` — pré-cond `validar()`.
   - `docs/inventario-2026-05/02-gotchas/G016-ssl-crash-no-loop-f5e-perde-commits.md` — retry + keepalive.
   - `docs/inventario-2026-05/02-gotchas/{G035,G017,G007,G018}.md` — quarteto fiscal pré-SEFAZ.
   - `docs/inventario-2026-05/02-gotchas/G019-f5b-validar-engole-erro.md` + `G020-f5c-sem-checar-state-done.md` (✅ JÁ CODIFICADOS em Skill 5).
   - Memórias: `[[ciel_it_quirks]]` (NCM custom, weight não persiste, barcode → SEFAZ 225), `[[picking_317346_pendente]]` (caso de invoice CIEL IT lento), `[[skill5_picking_pattern]]` (pattern capinagem reaproveitável).
6. **Se foco = Skill 7 `escriturando-odoo`**:
   - `docs/inventario-2026-05/02-gotchas/G023-etapa-f-entrada-destino-manual.md` (consolidar MLs entrada).
   - `docs/inventario-2026-05/02-gotchas/G034-robo-ciel-it-aplica-defaults-pt-66-em-dev-industr.md` (CFOP entrada 1xxx ≠ saída 5xxx; PT 97/88 criados).
   - Memória: `[[escrituracao_entrada_lf_dfe]]` (action_gerar_po_dfe usa company USUÁRIO — forçar allowed_company_ids; tipo='serv-industrializacao' p/ CFOP 1901).
7. Memórias-chave gerais:
   - `[[arquitetura_orquestrador_odoo]]` — princípio das 5 camadas + fluxos>>skills.
   - `[[skill4_mo_pattern]]` — pattern de skill criada do zero + guard G-MO-01 + cancel_deleted (lição reaproveitável).
   - `[[skill5_picking_pattern]]` — pattern capinagem + atomo NOVO + ONDA 0.4 fechada.
   - `[[skill2_transfer_interno_pattern]]` §incidente G031 v4 + MODO C — `stock.lot` é POR PRODUTO.
   - `[[feedback_skills_demanda_driven]]` — skills nascem de casos reais; átomos previstos ⬜ até demanda surgir.
   - `[[feedback_incompletude_quebra_regras]]` — C7-C10 INVIOLÁVEIS.

## REGRAS INVIOLÁVEIS (não negociáveis)

1. `--dry-run` antes do real; confirmação explícita antes de SEFAZ/irreversível.
2. NUNCA criar script ad-hoc — capinar a skill. Workspace `/tmp/` é OK (descartável).
3. `fluxos>>skills` — caso novo = folha de fluxo, NÃO skill nova.
4. Skills nascem de DEMANDAS REAIS — não implementar átomos especulativamente. **PARA SKILL 8**: justificar cada átomo macro com pipeline real; etapas isoladas só se demanda de retomada surgir.
5. C7-C10 são INVIOLÁVEIS — completar cada checkpoint com artefato concreto.
6. Verificar resultado DIRETO no Odoo — não confiar só no output. CRÍTICO para Skill 8 (SEFAZ irreversível); confirmar invoice criada por robô CIEL IT em cada caso.
7. Operação VIVA — preservar ad-hocs até cada átomo maturar; arquivar SUPERADO só após C9.
8. Premissas pesquisadas e validadas ANTES de compor átomos.
9. Após qualquer unlink em MLs em quants com reserved=0: chamar `zerar_reserved_residual` (G027 da skill 2.4).
10. Ao retomar FALHAs: cruzar `mo_id`/`quant_id`/etc. com pedido original — NÃO aplicar política homogênea.
11. Composição de átomos propaga `delta_esperado` a CADA chamada (regra inviolável 11 — herda dos modos A/B/C da Skill 2).
12. `--corrigir-para-esperado` em batch SEMPRE rodar `--dry-run` primeiro e revisar manualmente.
13. Antes de modificar `app/odoo/estoque/scripts/quant.py`: pytest baseline 30 verdes.
14. Antes de modificar `app/odoo/estoque/scripts/transfer.py`: pytest baseline 52 verdes (3 modos: A 33 + B 4 + C 15). CUIDADO com modo C — invariante G031 (resolver MIGRAÇÃO POR PRODUTO) é crítica.
15. Antes de modificar `app/odoo/estoque/scripts/picking.py`: pytest baseline 42 verdes. CUIDADO especial com `validar()` e `liberar_faturamento()` (invariante G019/G020 que destrava Skill 8 — quebrá-las re-abre a ONDA 0.4 E QUEBRA SKILL 8 EM USO).
16. **(NOVO Skill 4)** Antes de modificar `app/odoo/estoque/scripts/mo.py`: pytest baseline 29 verdes. CUIDADO com guard G-MO-01 (consumo>0=furo contábil — quebrá-lo permite cancelamento que cria furo). Status `cancel_deleted` é INVARIANTE.
17. TIMEZONE: NUNCA `datetime.now()` em código novo — usar `from app.utils.timezone import agora_brasil_naive` (regra `.claude/references/REGRAS_TIMEZONE.md`; hook `ban_datetime_now.py` BLOQUEIA Edit/Write).
18. **(NOVO Skill 4)** G-MO-01 furo contábil: NUNCA cancelar MO com `consumo_total > 0` sem unbuild prévio. CLI V1 da Skill 4 NÃO expõe `forcar_consumo` — operador DEVE usar `mrp.unbuild` via fluxo cross-skill se precisar reverter consumo.
19. **(pós-G031)** `stock.lot` é POR PRODUTO no Odoo CIEL IT — NUNCA usar `lot_id` de uma constant como FK universal. SEMPRE resolver via `lot_svc.buscar_por_nome(nome, product_id, company_id)` ou `lot_svc.criar_se_nao_existe(...)`. **Auditoria 2026-05-24 v5 confirmou ZERO callers reais** de `LOTES_MIGRACAO_POR_COMPANY[` em código WRITE (só 2 matches em docs descrevendo o incidente).
20. Constants `_id_POR_COMPANY`: antes de usar como FK em WRITE, verificar se o ID é uma-por-company (OK: `COMPANY_LOCATIONS`, `LOCAIS_INDISPONIVEL`, `COMPANY_PARTNER_ID`) ou um-por-produto/instância (RISCO: `LOTES_MIGRACAO_POR_COMPANY` ← deprecated).
21. `rollback_hint` em FALHA_AUMENTO: composições atomicas DEVEM reportar `rollback_hint` machine-readable (chamada exata `ajustar_quant` para reverter) — pattern estabelecido em Skill 2 modo C (CR3#5).
22. **(NOVO Skill 8)** Pre-flight quarteto fiscal ANTES de SEFAZ: validar NCM, custo>0, weight>0, barcode válido (G035/G017/G007/G018). Bloquear transmissão se algum falhar — Schema 225 reject custa retrabalho fiscal.
23. **(NOVO Skill 8)** Polling+timeout para robô CIEL IT (G016 SSL): nunca confiar em tempo fixo. Loop B→D com retry e keepalive.

## ARQUITETURA — relembrar a árvore de decisão

```
1  NF inter-company (emissão/SEFAZ entre filiais)
   1.1  só faturamento (saída)              → fluxos/1.1.* (faturando-odoo ⬜ ← FOCO PROPOSTO)
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
   3.1 cancelar MO (single ou batch — guard G-MO-01) → operando-mo-odoo 🟡 [folha 3.1] (3.1.c MO com consumo DELEGADO mrp.unbuild)
```

## CHECKLIST DA SESSÃO

```
[ ] Setup (cd worktree + venv + ODOO_*)
[ ] Verificar se main avançou: git fetch origin main && git log --oneline b8ed3b5c..origin/main
[ ] Se avançou: rebase incremental ANTES de iniciar
[ ] Pytest baseline: pytest tests/odoo/services/test_stock_quant_adjustment_service.py test_stock_internal_transfer_service.py test_stock_lot_service.py test_stock_picking_service.py test_stock_mo_service.py (esperado: 175 verdes)
[ ] Ler ROADMAP_SKILLS HANDOFF + VALIDACAO_FINAL_SESSAO §10 + G031 + memórias-chave
[ ] Confirmar com Rafael: Skill 8 faturando (foco recomendado), Skill 7 escriturando, fluxos compostos Skill 2, Skill 6 pre-etapa, ou outra prioridade
[ ] Se Skill 8: C1 mineração — ler integral `09_executar_onda1_bulk`, `09c_executar_onda2_fb_cd`, `fat_lf_02_carregar`, `fat_lf_04_executar`, `fat_lf_05_executar_clean`, `fat_lf_cleanup`, `fat_lf_resume.sh`, `teste_210030325` + ler 6 gotchas G004/G011/G016/G028/G019/G020 + quarteto fiscal G035/G017/G007/G018 + memórias [[ciel_it_quirks]] [[skill5_picking_pattern]]
[ ] Investigar AO VIVO 1 ajuste pendente real via Skill 9 (consultar `account.move` + picking source pendente)
[ ] Capinar `app/odoo/services/inventario_pipeline_service.py` → `app/odoo/estoque/orchestrators/inventario_pipeline.py` (NÃO em `scripts/` — Skill 8 é macro C3) + shim em `services/`
[ ] Cada átomo novo: C1-C10 SEM PULAR ETAPAS
[ ] Testes pytest cobrindo gotchas-invariante (G011 pre-cond, G016 retry, quarteto fiscal pré-SEFAZ) ANTES do C2 final
[ ] Smoke test 1-ajuste em PROD antes de batch (CRÍTICO — SEFAZ irreversível)
[ ] Validar resultado direto no Odoo (regra inviolável 6) — confirmar invoice criada por robô CIEL IT
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
- ❌ Modificar `quant.py`, `transfer.py`, `picking.py`, `reserva.py`, ou `mo.py` sem rodar pytest ANTES e DEPOIS
- ❌ Compor átomos sem propagar `delta_esperado` (regra inviolável 11)
- ❌ Usar `datetime.now()` em código novo (regra inviolável 17 — hook bloqueia)
- ❌ Quebrar invariante G019/G020 em `picking.py` `validar()`/`liberar_faturamento()` (re-abre ONDA 0.4 + QUEBRA SKILL 8)
- ❌ Quebrar invariante G031 em Skill 2 modo C — `transferir_para_indisponivel` DEVE usar `lot_svc.criar_se_nao_existe` POR PRODUTO
- ❌ Quebrar guard G-MO-01 em `mo.py` `cancelar_mo` — permitir consumo>0 sem unbuild garante furo contábil
- ❌ Cancelar MO com `consumo_total > 0` sem unbuild — furo contábil garantido (G-MO-01)
- ❌ Confiar em `action_assign` reservar componente de MO com `manual_consumption=True` — não funciona (G-MO-02)
- ❌ Usar `LOTES_MIGRACAO_POR_COMPANY` (ou qualquer constant `lot_id`) como FK em `stock.quant.create`/`write` — SEMPRE resolver POR PRODUTO via `lot_svc`
- ❌ Compor átomo de operação parcialmente irreversível sem reportar `rollback_hint` machine-readable (lição CR3#5 Skill 2 v4)
- ❌ **(NOVO Skill 8)** Transmitir SEFAZ sem pre-flight quarteto fiscal G035/G017/G007/G018 — Schema 225 reject custa retrabalho fiscal
- ❌ **(NOVO Skill 8)** Confiar em tempo fixo para robô CIEL IT criar invoice — usar polling+timeout (irredutível externo)
- ❌ **(NOVO Skill 8)** Pular smoke test 1-ajuste antes de batch — SEFAZ é irreversível por NF
- ❌ Recompor Skill 5 `validar()`/`liberar_faturamento()` na Skill 8 — USAR via `svc.validar(linhas_esperadas=)` confiando no invariante já codificado

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

### Sessão 24/05 v5 Skill 4 NOVA (sem --confirmar)
```
/tmp/log_skill4_C6_validacao_dry_run.json  (4 casos PROD: NOOP idempotente, DRY_RUN_OK, FALHA_FURO_CONTABIL, batch)
scripts/inventario_2026_05/auditoria/
  log_skill4_mo_dryrun_20260524_115*.json   (4 logs individuais)
```

Comece pela leitura dos 4 docs obrigatórios (CLAUDE.md + ROADMAP + VALIDACAO §10 + memórias). Verificar pytest baseline 175 verdes. Confirme com Rafael o foco da sessão. **Recomendação**: Skill 8 `faturando-odoo` (DESBLOQUEADA pela ONDA 0.4; macro perigoso — cuidado com SEFAZ irreversível; smoke test 1-ajuste antes de batch obrigatório). Antes de qualquer write em PROD: pre-flight quarteto fiscal + verificação direta no Odoo + pytest baseline pós-mudança.

---END---

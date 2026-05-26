Continue o trabalho do orquestrador-Odoo. Worktree: /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo (branch feat/estoque-odoo). main continua VIVO em paralelo. Verificar se avancou e considerar rebase ANTES de iniciar.

## ✅ RESPOSTAS VALIDADAS — investigadas + corrigidas pelo Rafael no fim da v17.5

**Q1 — Skill 7 V1 STRICT (raise NotImplementedError se cnpj!=LF ou recebedor!=FB) eh correto?**
RESPOSTA: **NAO. V1 STRICT eh ANTIPADRAO.** Rafael corrigiu (2026-05-26):
> "O papel principal da Skill eh Escriturar uma NF no Odoo, e nao apenas escriturar transferencia. A skill devera ser capaz de escriturar uma NF independente da particularidade dela, o que define os parametros deverao ser os fluxos junto com as constants + 'pre'. Com isso a skill devera ser capaz de vincular qualquer NF desde a criacao da skill, o que limitara o que ela pode escriturar serao os fluxos."

- Skill 7 deve ser **ATOMICA mas ABRANGENTE** (1 objeto Odoo: DFe/account.move)
- Limites = FLUXOS + CONSTANTS + PRE-FLIGHT (NAO o atomo)
- Estado atual da Skill 7 (v17.5) eh um wrapper RESTRITO sobre RecebimentoLfOdooService
- **Tendencia futura (Rafael)**: extrair Skill 7 do RecebimentoLfOdoo p/ que no futuro RecebimentoLfOdoo se torne wrapper de escriturando-odoo (inversao da relacao atual)
- Referencia do FLUXO CORRETO: `scripts/inventario_2026_05/escriturar_dfe_lf.py` (FLUXO A — comentario "NAO reusar RecebimentoLfOdooService — direcao inversa")
- **AGENDAR refator para v19+** (escopo v18 mantido em recovery+SKILL.md)

**Q2 — As N NFs recebidas no Render — quais direcoes?**
RESPOSTA: PROD HOJE usa exclusivamente LF→FB. 67 RecebimentoLf no DB local:
- 100% recebedor = `company_id=1` (FB)
- 94% emitente = `'18.467.441/0001-63'` (CNPJ LF)
- ZERO outras direcoes
- **MAS isso NAO justifica V1 STRICT.** Skill 7 deve ser ampla por design — o uso atual eh contingencial.

**Q3 — Os 4 conceitos (operacao / tipo_pedido / CFOP / picking_type) sao ligados?**
RESPOSTA: PARCIALMENTE derivados, MAS CFOP NAO eh apenas informacional (Rafael corrigiu):
- `l10n_br_tipo_pedido` mora em `stock.picking.type` (PT 53 FB Exped Industr → `tipo_pedido='industrializacao'`); ao escolher picking_type_id deriva tipo_pedido
- CFOP eh derivado pelo motor fiscal via `fiscal_position_id` + impostos
- **GOTCHA REAL (Rafael)**: "se a operacao nao estiver cadastrada, eh necessario setar o CFOP". Isto significa que `cfop_esperado` em MATRIZ_INTERCOMPANY tem USO PRATICO (nao apenas log).
- **DECISAO**: manter MATRIZ_INTERCOMPANY com cfop_esperado; documentar como **G036 — operacao nao cadastrada exige CFOP explicito** (gotcha novo a adicionar em `.claude/references/odoo/GOTCHAS.md`).
- IMPORTANTE: tambem ha referencia adicional a 'tipo_pedido' em DFe (`l10n_br_ciel_it_account.dfe.l10n_br_tipo_pedido` — CHAVE para derivar CFOP correto na escrituracao — ex: 'serv-industrializacao' → CFOP 1901).

**Q4 — PT 19 LF/IN eh o correto para INDUSTRIALIZACAO_FB_LF?**
RESPOSTA: SIM, **PT 19 confirmado** (validado em `escriturar_dfe_lf.py` L36: `PICKING_TYPE_LF = 19`). Rafael corrigiu meu erro v17.5:
- v17.5 disse "PT 64 talvez seja melhor" — INCORRETO
- Rafael: "Industrializacao com retorno das mercadorias na mesma NF nao utilizamos no inventario, apenas no servico em prod, nao se confunda"
- PT 64 LF/RECEB/IND eh para SERVICO em PROD (industrializacao com retorno em 2 CFOPs na mesma NF — CFOP 1124 PA + 1902 insumos)
- PT 19 LF/IN eh o usado para INDUSTRIALIZACAO no inventario (CFOP 1901)
- **PERMANECE** `PICKING_TYPE_ENTRADA_DESTINO_MANUAL[5]=19`

**Q5 — Robo CIEL IT cria picking entrada AUTOMATICO no CD para TRANSFERIR_FB_CD?**
RESPOSTA: NAO. Rafael corrigiu o entendimento — eh assim para QUALQUER NF emitida:
> "Nao cria picking assim como nenhuma NF emitida cria automaticamente. O que cria picking eh a escrituracao da NF no DFe que se nao me engano cria o picking atraves do pedido de compras gerado por confirmar o DFe. O 'gotcha' aqui eh que o DFe demora muito para aparecer a NF emitida, portanto utilizamos o XML da NF emitida para criarmos o DFe."

- Fluxo CORRETO: NF SEFAZ-OK → DFe (escriturado, com XML da NF para acelerar) → action_gerar_po_dfe → PO confirma → picking NATIVO criado pelo Odoo via PO
- Picking nativo: tem `purchase_id` preenchido, `partner_id` correto, vincula ao caminho fiscal completo
- v17.5 ETAPA F atomo `criar_picking_entrada_destino_manual` (Skill 5) cria picking SEM PO+partner — eh **PALIATIVO/ANTIPADRAO**, nao o caminho correto
- **8 pickings INV-* PT 19 criados manualmente em PROD**: Rafael disse "Nao deveria ser necessario, o DFe deveria criar o PO que por sua vez criaria os pickings". Investigar se eram realmente necessarios ou se foi erro arquitetural.

---

## 📐 REVISAO ARQUITETURAL NECESSARIA — agendar v19+

A v17.5 fechou pipeline A-F LIVE, mas a auditoria com Rafael apos a sessao identificou **2 antipadroes arquiteturais a corrigir**:

### Antipadrao 1: Skill 7 V1 STRICT (raise NotImplementedError)
- Skill 7 atual eh wrapper restrito de RecebimentoLfOdooService
- Correto: extrair logica de escrituracao do RecebimentoLfOdoo para Skill 7 atomica + abrangente
- RecebimentoLfOdoo no futuro vira wrapper da Skill 7
- **Esperado v19+**: refatorar Skill 7 conforme `escriturar_dfe_lf.py` (FLUXO A); atomos: `escriturar_dfe(dfe_id, tipo, company_destino)` + `criar_invoice_from_po(po_id)` + ...

### Antipadrao 2: ETAPA F orchestrator Skill 8 cria picking manual via Skill 5
- v17.5 ETAPA F chama atomo Skill 5 `criar_picking_entrada_destino_manual` (cria picking sem PO/partner)
- Correto: ETAPA F deveria ser FLUXO L3 que compoe:
  - Skill 7: `escriturar_dfe(...)` → PO criada → picking nativo (com PO+partner)
  - Skill 5: `preencher_lotes_picking(picking_id, lote='MIGRAÇÃO')` (atomo a criar)
  - Skill 7: `criar_invoice_from_po(po_id)` → ENTIN CFOP 1901
- Skill 5 atomo `criar_picking_entrada_destino_manual` permanece como CAMINHO B paliativo (DFe demora) mas NAO eh o caminho principal
- **Esperado v19+**: criar FLUXO L3 `1.2.1-escriturar-dfe-industrializacao.md` + atomo Skill 5 `preencher_lotes_picking` + reescrever ETAPA F para invocar FLUXO

### Antipadrao 3 (relacionado): orchestrator Skill 8 NUNCA deveria estar chamando Skill 5 ou Skill 7 INLINE — eh FLUXO L3 que compoe
- Constituicao §6 reforcada: "Fluxo >> Skill"
- v17.5 ETAPA F chama Skill 5 atomo diretamente do orchestrator — viola §6
- v17.5 ETAPA E chama Skill 7 atomo do orchestrator — viola §6 (mas menos grave que v17 que era inline)
- **Esperado v19+**: extrair ETAPA E e ETAPA F do orchestrator para FLUXOS L3; orchestrator Skill 8 = SO SAIDA (A→B→C→D); FLUXO L3 1.3 compõe Skill 8 saida + Skill 7 entrada

---

## 🚨 LEIA ANTES DE TUDO — REGRAS DE ESCOPO INVIOLAVEIS (v17.5 licao custosa)

**NUNCA inline logica de skill no orchestrator Skill 8 `faturando-odoo`.** Isso ja custou uma sessao inteira em v17.5 — v17 colocou ~420 LOC de logica RecebimentoLf inline em `executar_etapa_e` e violou constituicao §6 do `app/odoo/estoque/CLAUDE.md`.

**Regra de ouro (constituicao §6 — INVIOLAVEL)**:
- `faturando-odoo` (Skill 8) = SO SAIDA (NF→robô CIEL IT→SEFAZ)
- `escriturando-odoo` (Skill 7) = SO ENTRADA (escritura DFe → PO → invoice; objeto = account.move + DFe)
- `operando-picking-odoo` (Skill 5) = SO picking (cancelar/validar/devolver/preencher lotes/criar inter-company)
- ... cada skill 1 OBJETO Odoo + 1 RESPONSABILIDADE
- Quem une SAIDA + ENTRADA + Picking = **FLUXO L3** (`fluxos/1.3-transferencia-completa.md`), NAO o orchestrator

**Antes de codar qualquer logica nova no orchestrator, PERGUNTE**:
1. "Esta logica cria registros locais + invoca svc externo + agrega dados? → atomo C3 macro, NAO orchestrator"
2. "Esta logica toca stock.picking? → Skill 5, NAO orchestrator"
3. "Esta logica toca account.move/DFe? → Skill 7 (escriturando-odoo)"
4. "Esta logica combina 2+ skills? → FLUXO L3, NAO orchestrator"
5. "NAO SEI" → **PARE e AVISE Rafael** ANTES de implementar

**Padrao correto do orchestrator pos-v17.5**: apenas (a) filtro de ajustes, (b) agrupamento, (c) loop, (d) invocacao de atomo OU FLUXO L3, (e) mapeamento de status → contadores. NADA MAIS.

## Setup OBRIGATORIO (worktree sem .env)

    cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
    source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
    set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
    git fetch origin main && git log --oneline HEAD..origin/main

## CONTEXTO ATUAL — v17.5 ENTREGOU pipeline A-F MAS COM 2 ANTIPADROES a corrigir v19+

Sessao v17.5 (commit e8bfea73 +1870/-510) entregou:
- Skill 7 `escriturando-odoo` NOVA (atomo wrapper restrito RecebimentoLfOdoo) — **antipadrao 1, a refatorar v19+**
- ETAPA E rewrite delegando atomo Skill 7 (~420 LOC → ~180 LOC; constituicao §6 parcialmente restaurada)
- ETAPA F EXPANSION canary: DEV_FB_LF + TRANSFERIR_FB_CD habilitados via flag `--auto-confirma-direcao-nova` — **caminho PALIATIVO (antipadrao 2), refator v19+**
- PT 50 CD/IN/INTER descoberto via audit Odoo 2026-05-26 (TRANSFERIR_FB_CD: src=6, dest=32)
- LOCATION_ORIGEM_POR_DIRECAO dict substitui hardcode 26489
- 513 pytest verdes (+11 net v17.5)
- 2 code-reviewers paralelos: 3 findings aplicados

**Status global v17.5:** 14 checkpoints concluidos de 24. Pipeline A-F LIVE mas com 2 antipadroes documentados. Pendentes v18: recovery + SKILL.md Skill 8. Pendentes v19+: refator Skill 7 + FLUXO L3 escriturar-dfe + arquivar `criar_picking_entrada_destino_manual` como caminho B paliativo.

## PRIORIDADE v18 — Recovery + SKILL.md Skill 8 + Smokes (escopo mantido)

### Sub-objetivo S1: C14 Recovery `--resume` modo CLI

Adicionar entry-point `executar_pipeline_resume` em `app/odoo/estoque/orchestrators/faturamento_pipeline.py`:

```python
def executar_pipeline_resume(
    self,
    *,
    ciclo: str,
    apenas_etapa: str,  # 'B', 'C', 'D', 'E' ou 'F'
    max_iter: int = 18,
    timeout_iter_s: int = 900,
    detector_stagnation: bool = True,
    company_origem_id: Optional[int] = None,
    confirmar_sefaz: bool = False,
    auto_confirma_direcao_nova: bool = False,
    usuario: str = 'faturamento_pipeline_resume',
) -> Dict[str, Any]:
    """Loop com detector stagnation que executa ETAPA escolhida ate' tudo OK
    OU max_iter atingido. Substitui scripts shell fat_lf_resume.sh +
    fat_lf_resume_entrada.sh.

    Returns:
      dict com iteracoes_executadas, restantes_por_fase, motivo_parada
      (TUDO_OK / STAGNATION / MAX_ITER).
    """
```

CLI: `--modo resume --apenas-etapa E --max-iter 30 --timeout-iter 600`.

Esperado: 3+ pytest novos (mockando ondas) + smoke shell script substitutivo OK.

### Sub-objetivo S2: C15 SKILL.md `faturando-odoo`

Criar `.claude/skills/faturando-odoo/SKILL.md` + scripts/ dir.

Contrato:
```
objeto:     stock.picking (saida) + account.move (saida) + Playwright SEFAZ
input:      --modo {canary|bulk|resume|consolidar}
            --ciclo NOME --etapas LISTA [--company-origem-id ID] [--cod-produto X]
            [--limite N] [--confirmar] [--confirmar-sefaz]
            [--auto-confirma-direcao-nova] [--pular-pre-flight]
output:     dict por ETAPA com status + contadores + tempo_ms
pre-cond:   PRE-FLIGHT sub-skill C5 OK (ou --pular-pre-flight)
pos-cond:   NF autorizada SEFAZ (futuro: + DFe escriturado via FLUXO L3 chamando Skill 7)
gotchas-invariante: G011 timing CIEL IT + G016 SSL + G018 weight + G019/G020
                    picking state + G022 over-reservation + G023 company_id +
                    G034 fiscal setup + G035 barcode + G036 operacao nao cadastrada
                    exige CFOP explicito + D-OPS-3 tracking + D-OPS-5 produto sem lote
modos:      dry-run default; --confirmar real; --confirmar-sefaz nivel 2
            (IRREVERSIVEL); --auto-confirma-direcao-nova canary ETAPA F (paliativo)
status:     EXECUTADO_OK | EXECUTADO_PARCIAL | FALHA_USO | BLOQUEADO_SEFAZ |
            DRY_RUN_OK | DRY_RUN_PARCIAL | PRE_FLIGHT_BLOQUEADO
```

5+ receitas:
1. Canary 1 ajuste (testar pipeline end-to-end no real)
2. Bulk onda completa (100+ ajustes, ETAPA D irreversivel)
3. Resume apos crash mid-ETAPA D (Playwright SEFAZ rejeitou alguns)
4. Pre-flight isolado (sub-skill C5 sem dispatch da Skill 8)
5. **NOTA**: ETAPA F atual eh PALIATIVO (caminho B). Refator v19+ para fluxo L3.

Cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper).

### Sub-objetivo S3: C16+C17 Smokes dry-run + ate >=520 pytest

Smokes documentados em log JSON `/tmp/log_skill8_smokes_v18_*.json`:
- ETAPA F canary DEV_FB_LF com flag (mock — paliativo)
- ETAPA F canary TRANSFERIR_FB_CD com flag (mock — paliativo)
- Pipeline E+F com ajustes em F5e_SEFAZ_OK
- Pre-flight cod com cadastro fiscal inconsistente (G017 NCM ou G035 barcode)

Pytest >=520 (atual 513 +7 esperado: 3 recovery + 2 SKILL.md flow + 2 smokes wrap)

### Sub-objetivo S4: Atualizar docs + commit v18

- CLAUDE.md estoque §6 (recovery + SKILL.md Skill 8 LIVE + secao "antipadroes detectados v17.5 — refator v19+")
- ROADMAP HANDOFF v18 (entry NOVA acima da v17.5)
- PLANEJAMENTO §0 (status + checkpoints atualizados) + §12 trilha v18
- `.claude/references/odoo/GOTCHAS.md`: adicionar **G036 — operacao nao cadastrada exige CFOP explicito**
- Memoria patterns se houver
- Commit consolidado v18

## INVESTIGACOES OPCIONAIS v18 (para canary REAL)

1. **Identificar candidato canary**: rodar query SQL/Odoo p/ achar 1 ajuste em F5e_SEFAZ_OK com acao_decidida=PERDA_LF_FB ou DEV_LF_FB que ainda nao foi processado em RecebimentoLf. Confirmar com Rafael antes de canary REAL.

2. **Validar caminho canary DEV_FB_LF**: se Rafael disponibilizar 1 ajuste real, validar fiscal_position fp 74 (FB→LF retrabalho assumido — sem precedente PROD). Se SEFAZ rejeitar com cstat=225, fp 74 esta errado e precisa ajuste em MATRIZ_INTERCOMPANY.

## LEITURAS OBRIGATORIAS (ordem)

1. app/odoo/estoque/CLAUDE.md (constituicao §6 catalogo Skill 7+8 LIVE — secao "antipadroes detectados v17.5")
2. app/odoo/estoque/ROADMAP_SKILLS.md HANDOFF v17.5 (esta sessao terminou)
3. app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md §0 + §10.6 + §12 trilha v17.5 + C14 + C15 checkpoints
4. **scripts/inventario_2026_05/escriturar_dfe_lf.py** (FLUXO A correto de escrituracao — referencia para refator Skill 7 v19+; NOTE: "NAO reusar RecebimentoLfOdooService — direcao inversa")
5. Memoria [[skill7-escriturando-pattern]] (pattern v17.5 — V1 STRICT documentado como antipadrao)
6. Memoria [[skill8-pipeline-completo-v17]] (status v17 + 11 fixes)
7. Memoria [[feedback-constituicao-skill-so-responsabilidade]] (anti-padrao inline v17.5)
8. app/odoo/estoque/orchestrators/faturamento_pipeline.py (pipeline atual + executar_etapa_e v17.5 delegada)
9. app/odoo/estoque/scripts/escrituracao.py (atomo Skill 7 V1 STRICT — ANTIPADRAO a refatorar v19+)
10. .claude/skills/escriturando-odoo/SKILL.md (modelo de SKILL.md para Skill 8)
11. scripts/inventario_2026_05/fat_lf_resume.sh (script shell SUPERADO p/ inspirar logica de recovery)

## CHECKLIST v18

[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde HEAD v17.5 (commit e8bfea73)
[ ] Pytest baseline: 513 verdes esperado
[ ] AskUserQuestion confirmar escopo S1-S4 + criterios de aceite
[ ] S1 Capinar `executar_pipeline_resume` + 3+ pytest
[ ] S2 Criar `.claude/skills/faturando-odoo/SKILL.md` com 5+ receitas
[ ] S3 Smokes documentados + pytest >=520
[ ] Documentar G036 em `.claude/references/odoo/GOTCHAS.md`
[ ] >=1 code-reviewer paralelo (SKILL.md richness + recovery edge cases)
[ ] S4 Docs atualizadas (incluir secao "antipadroes detectados v17.5 — refator v19+") + commit v18
[ ] Atualizar PROMPT_PROXIMA_SESSAO.md para v19 (REFATOR Skill 7 abrangente + FLUXO L3 escriturar-dfe + arquivar criar_picking_entrada_destino_manual)

## REGRAS INVIOLAVEIS (v17.5)

94. `faturando-odoo` (Skill 8) = SO SAIDA. NUNCA inclui logica de criar RecebimentoLf ou escriturar entrada. Quem une saida (D) + entrada (E) e' o FLUXO L3.

95. `escriturando-odoo` (Skill 7) = SO ENTRADA (objeto = account.move + DFe). Atomo deve ser ABRANGENTE — limite eh fluxos+constants+pre, NAO o atomo. V1 STRICT atual eh ANTIPADRAO.

96. `LOCATION_ORIGEM_POR_DIRECAO` dict varia por acao (NAO hardcode 26489).

97. `PICKING_TYPE_ENTRADA_DESTINO_MANUAL[5]=19` (LF/IN Recebimento) — confirmado em `escriturar_dfe_lf.py`. PT 64 LF/RECEB/IND eh para SERVICO em prod (industrializacao com retorno 2 CFOPs na mesma NF), NAO inventario.

98. Flag `--auto-confirma-direcao-nova` obrigatoria para ETAPA F canary em real-run — **caminho B PALIATIVO** (DEV_FB_LF + TRANSFERIR_FB_CD sem precedente PROD). Caminho A (correto fiscalmente) = escriturar DFe via Skill 7 ampliada (v19+).

99. **NOVO v17.5 — G036**: operacao nao cadastrada no Odoo exige setar CFOP explicito (`l10n_br_cfop_id`). MATRIZ_INTERCOMPANY com `cfop_esperado` tem uso real (nao apenas log).

## NAO-FAZER (red flags v18)

X Implementar recovery sem testes de detector stagnation
X Criar SKILL.md sem 5+ receitas concretas + trade-offs
X Mexer no RecebimentoLfOdooService (NAO MEXER — 4562 LOC validados PROD)
X Mexer no script 09 (NAO MEXER — regra v14a-ops)
X Mexer no atomo Skill 7 sem necessidade (V1 STRICT antipadrao MAS estavel para uso atual; refator v19+)
X **Criar mais pickings via `criar_picking_entrada_destino_manual` em PROD sem Rafael autorizar** (eh paliativo; caminho correto eh DFe→PO→picking nativo via Skill 7 ampliada)
X **Usar V1 STRICT (raise NotImplementedError) como padrao em novas skills** — Skill 7 V1 STRICT eh ANTIPADRAO documentado; novas skills devem ser ABRANGENTES desde o inicio (limite via fluxos+constants+pre, nao via raise no atomo)
X Esquecer cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md estoque §6)

## CRONOGRAMA REVISADO (apos correcoes Rafael v17.5)

v17 (concluida 2026-05-25): pipeline A-F LIVE + 11 fixes | commit e0a29f21
v17.5 (concluida 2026-05-26): REVERT E + Skill 7 V1 STRICT + ETAPA F canary | commit e8bfea73 — **2 antipadroes documentados**
**v18 (proxima)**: C14 recovery + C15 SKILL.md Skill 8 + C17 smokes + G036 em GOTCHAS | Risco Medio (escopo conservador, sem mexer nos antipadroes)
**v19 (NOVA — agendar)**: REFATOR Skill 7 (extrair de RecebimentoLfOdoo + tornar abrangente — referencia `escriturar_dfe_lf.py`) + criar atomo Skill 5 `preencher_lotes_picking` + criar FLUXO L3 1.2.1 escriturar-dfe-industrializacao | Risco Alto (refator arquitetural)
v20: Reescrever ETAPA F orchestrator para invocar FLUXO L3 (em vez de Skill 5 inline) + arquivar `criar_picking_entrada_destino_manual` como caminho B paliativo documentado | Risco Alto
v21: C18 folhas fluxos restantes (1.1 faturamento completo + 1.3 transferencia completa) + C19 cross-refs final + C20 canary REAL PROD | Risco Alto
v22+: C21 bulk REAL PROD + C22 code-review final + C23 commit + arquivar 09_* | Risco Alto

Total restante: 5 sessoes (v18 → v22+).

## ESTADO ATUAL — apos v17.5 (PIPELINE A-F LIVE + 2 antipadroes documentados)

Resumo:
- Pipeline A-F funcional via orchestrator (commit e8bfea73)
- Skill 7 `escriturando-odoo` LIVE com V1 STRICT (antipadrao 1 — refator v19+)
- ETAPA F canary com flag --auto-confirma-direcao-nova (caminho B PALIATIVO — refator v19+)
- 513 pytest verdes
- 14/24 checkpoints concluidos
- 2 code-reviewers paralelos validaram v17.5 (3 fixes aplicados)
- 4 correcoes Rafael pos-v17.5 documentadas como antipadroes a corrigir
- Smoke dry-run PROD: ETAPA E cod 104000003 via atomo Skill 7 em 765ms

## REFERENCIAS RAPIDAS

- Commit v17.5: e8bfea73
- Commit v17: e0a29f21
- Commit v16: f4f964fc
- Baseline pytest: 513 verdes em 14.53s
- Audit Odoo 2026-05-26: PT 50 CD/IN/INTER (TRANSFERIR_FB_CD) src=6 dest=32; PT 19 LF/IN confirmado em `escriturar_dfe_lf.py` (INDUSTRIALIZACAO_FB_LF); PT 64 LF/RECEB/IND NAO usar (eh para servico em prod com 2 CFOPs na mesma NF)
- Memoria v17.5: [[skill7-escriturando-pattern]] (V1 STRICT documentado como ANTIPADRAO)
- Memoria v17: [[skill8-pipeline-completo-v17]]
- **Referencia FLUXO A correto (escrituracao DFe)**: `scripts/inventario_2026_05/escriturar_dfe_lf.py` — base para refator Skill 7 v19+

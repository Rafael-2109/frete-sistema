Continue o trabalho do orquestrador-Odoo. Worktree: /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo (branch feat/estoque-odoo). main continua VIVO em paralelo. Verificar se avancou e considerar rebase ANTES de iniciar.

## ✅ RESPOSTAS VALIDADAS — questoes investigadas no fim da v17.5 (Rafael apontou suposicoes nao-confirmadas; investiguei antes de finalizar prompt)

**Q1 — Skill 7 V1 STRICT bloqueia TRANSFERIR_CD_FB?**
RESPOSTA: SIM, e esta CORRETO. O service externo `RecebimentoLfOdooService` (4562 LOC, NAO MEXER) eh hardcoded LF→FB→CD:
- `COMPANY_FB=1` (recebedor); `COMPANY_LF=5` (emitente — coletado do invoice); `COMPANY_CD=4` (destino transfer FASE 6+7)
- `CNPJ_FB='61.724.241/0001-78'` usado em filtros internos (linha 2921)
- **NAO existe** `CNPJ_CD` para emissao no service
- TRANSFERIR_CD_FB (CD emite NF, FB recebe) NAO eh suportado por este service — precisaria service paralelo (`RecebimentoCdFbOdooService` futuro) ou broadening do existente
- V1 STRICT raise NotImplementedError esta correto: protege contra invocacao indevida ate' v2

**Q2 — As N NFs recebidas no Render — quais direcoes?**
RESPOSTA: PROD CONFIRMA exclusivamente LF→FB. 67 RecebimentoLf no DB local (sincronizado):
- 100% recebedor = `company_id=1` (FB)
- 94% emitente = `'18.467.441/0001-63'` (CNPJ LF — Discovery)
- 4 cancelados/erro sem cnpj
- ZERO CD→FB; ZERO outras direcoes
- Status: 57 processado, 6 erro, 4 cancelado
- **V1 STRICT (LF→FB) alinha 100% com uso atual de PROD.** Expansao futura V2 (CD→FB) so' quando demanda real surgir.

**Q3 — Os 4 conceitos (operacao / tipo_pedido / CFOP / picking_type) sao ligados?**
RESPOSTA: SIM, parcialmente. Mapa real:
- `l10n_br_tipo_pedido` mora em `stock.picking.type` (NAO em `account.fiscal.position`). Ex: PT 53 FB Exped Industr → `tipo_pedido='industrializacao'`. Logo: **picking_type_id ja' deriva tipo_pedido automaticamente**.
- CFOP eh derivado pelo motor fiscal do Odoo via `fiscal_position_id` + impostos da invoice. Nao se passa CFOP explicito ao criar invoice (Odoo decide).
- `account.fiscal.position` NAO tem campo direto de CFOP nem tipo_pedido (validado: `cfop_keys=[]`, `tipo_pedido_keys=[]` ao listar fields_get da FP 25)
- **Conclusao**: 2 conceitos REALMENTE independentes (`picking_type_id` + `fiscal_position_id`); os outros 2 (CFOP + tipo_pedido) sao DERIVADOS.
- **Implicacao para MATRIZ_INTERCOMPANY**: `cfop_esperado` eh "validacao/log informacional" (Odoo decide o real); `l10n_br_tipo_pedido` eh "derivado do picking_type". MATRIZ pode simplificar — manter so' `fiscal_position_id` + `l10n_br_tipo_pedido` (para validacao), descartar `cfop_esperado` redundante. Mas isto eh refator ortogonal — NAO MEXER em v18 sem demanda.

**Q4 — PT 19 LF/IN vs PT 64 LF/RECEB/IND (qual para INDUSTRIALIZACAO_FB_LF)?**
RESPOSTA: AMBOS sem `l10n_br_tipo_pedido` configurado (False), mesmo dest=42 LF/Estoque, mesmo src=26489 Em Trans. Industr.. Diferenca eh so' o `name`:
- PT 19: "Recebimento (LF)" — generico
- PT 64: "Recebimentos Industrialização (LF)" — dedicado por nome
- Historico PROD: **4 pickings INV-* (317306, 317316, 320467, 320476) usaram PT 19** (validado SEFAZ-OK)
- PT 19 funciona (PROD), PT 64 talvez seja "mais correto" fiscalmente — mas SEM diferenca configural detectavel via XML-RPC
- **DECISAO v17.5 (mantida v18)**: PT 19 (alinha com precedente PROD). Trocar para PT 64 seria gratuito — requer canary fiscal sem evidencia clara de beneficio. Permanece como `PICKING_TYPE_ENTRADA_DESTINO_MANUAL[5]=19`.

**Q5 — Robo CIEL IT cria picking entrada AUTOMATICO no CD para TRANSFERIR_FB_CD?**
RESPOSTA: NAO. Invoice ENTTR/2026/05/0173 (CD recebe FB, CFOP 1152) tem `picking_ids=[]` VAZIO:
- `stock_move_id: False` (sem move associado)
- `picking_ids: []` (sem picking ligado)
- `picking_ok: True` (campo computed — provavelmente "esta OK do ponto de vista contabil")
- Conclusao: **robo NAO cria picking automaticamente** para CFOP 1152 inter-filial
- **ETAPA F canary TRANSFERIR_FB_CD esta CORRETA**: criar picking entrada manual via Skill 5 atomo `criar_picking_entrada_destino_manual` (PT 50 CD/IN/INTER, src=6, dest=32) eh NECESSARIO, nao redundante.

**Q3 BONUS — `D17 ACAO_PARA_CFOP_ENTRADA`**: explicacao final.
- Esse mapa popula `RecebimentoLfLote.cfop` (campo do model LOCAL, NAO passa ao Odoo)
- Service externo usa `cfop` do lote para decidir como preencher lote no Odoo (CFOP 1902 = auto; outros = manual)
- Logo: D17 eh para LOGICA INTERNA do service externo, nao para criar invoice no Odoo

---

## 📋 DECISOES V18 (fundamentadas pelas respostas)

1. **NAO broadening da Skill 7 V1 STRICT em v18** — alinhada com 100% de PROD; expandir CD→FB so' quando demanda real surgir.
2. **NAO refatorar MATRIZ_INTERCOMPANY em v18** — `cfop_esperado` informacional mantido (escopo ortogonal).
3. **PT 19 mantido para INDUSTRIALIZACAO_FB_LF** — sem evidencia de PT 64 ser melhor; alinha precedente PROD.
4. **ETAPA F canary TRANSFERIR_FB_CD mantido** — confirmado que robo nao cria picking auto.
5. **DEV_FB_LF canary mantido** (sem precedente PROD; fp 86 assumido) — somente real-run via Rafael pode validar fiscal.

---

## 🚨 LEIA ANTES DE TUDO — REGRAS DE ESCOPO INVIOLAVEIS (v17.5 lição custosa)

**NUNCA inline logica de skill no orchestrator Skill 8 `faturando-odoo`.** Isso ja' custou uma sessao inteira em v17.5 — v17 colocou ~420 LOC de logica RecebimentoLf inline em `executar_etapa_e` e violou constituicao §6 do `app/odoo/estoque/CLAUDE.md`.

**Regra de ouro (constituicao §6 — INVIOLAVEL)**:
- `faturando-odoo` (Skill 8) = SO SAIDA (NF→robô CIEL IT→SEFAZ)
- `escriturando-odoo` (Skill 7) = SO ENTRADA (RecebimentoLf + svc externo)
- `operando-picking-odoo` (Skill 5) = SO picking (cancelar/validar/devolver/criar inter-company)
- ... cada skill 1 OBJETO Odoo + 1 RESPONSABILIDADE
- Quem une SAIDA + ENTRADA + Picking = **FLUXO L3** (`fluxos/1.3-transferencia-completa.md`), NAO o orchestrator

**Antes de codar qualquer logica nova no orchestrator, PERGUNTE**:
1. "Esta logica cria registros locais + invoca svc externo + agrega dados? → atomo C3 macro, NAO orchestrator"
2. "Esta logica toca stock.picking? → Skill 5, NAO orchestrator"
3. "Esta logica toca RecebimentoLf? → Skill 7 atomo `criar_recebimento_orchestrado`"
4. "Esta logica cria account.move/invoice? → futura Skill (ou Skill 8 macro entry-point — confirmar com Rafael)"
5. "NAO SEI" → **PARE e AVISE Rafael** ANTES de implementar

**Padrao correto do orchestrator pos-v17.5**: apenas (a) filtro de ajustes, (b) agrupamento, (c) loop, (d) invocacao de atomo, (e) mapeamento de status → contadores. NADA MAIS. Nunca `db.session.add(NovoModelo(...))` nem `svc_externo = ServiceXYZ()` no orchestrator.

**Se VOCÊ (futura sessão) detectar que esta prestes a inline logica nova no orchestrator** (alem dos 5 padroes acima), PARE. Releia o ALERTA da §3 do CLAUDE.md estoque ("ARMADILHA SUPERADA v17.5"). Considere: **criar nova skill ou estender skill existente** antes de codar inline.

## Setup OBRIGATORIO (worktree sem .env)

    cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
    source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
    set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
    git fetch origin main && git log --oneline HEAD..origin/main

## CONTEXTO ATUAL — v17.5 ENTREGOU Skill 7 + ETAPA F canary; PIPELINE A-F COMPLETO E ALINHADO §6

Sessao v17.5 (commit e8bfea73 +1870/-510) entregou:
- Skill 7 `escriturando-odoo` NOVA (atomo C3 macro `criar_recebimento_orchestrado`) — encapsula RecebimentoLf + agg lotes + svc externo
- ETAPA E rewrite delegando atomo Skill 7 (reduzida de ~420 LOC para ~180 LOC; constituicao §6 restaurada)
- ETAPA F EXPANSION canary: DEV_FB_LF + TRANSFERIR_FB_CD habilitados via flag `--auto-confirma-direcao-nova` (default False)
- PT 50 CD/IN/INTER descoberto via audit Odoo 2026-05-26 (TRANSFERIR_FB_CD: src=6 Em Transito Filiais, dest=32 CD/Estoque)
- LOCATION_ORIGEM_POR_DIRECAO dict substitui hardcode 26489
- Cross-refs: subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md estoque §6 + ROADMAP HANDOFF v17.5 + PLANEJAMENTO C24 NOVO
- 513 pytest verdes (+11 net v17.5)
- 2 code-reviewers paralelos: 3 findings aplicados (F1 HIGH conf 85 broadened HIGH-3 + F3 HIGH conf 82 teste novo + F4 MED conf 80 doc tradeoff)

**Status global v17.5:** 14 checkpoints concluidos de 24. Pipeline A-F LIVE + Skill 7 LIVE. Pendentes: recovery + SKILL.md Skill 8 + canary REAL PROD + bulk PROD.

## PRIORIDADE v18 — Recovery + SKILL.md Skill 8 + Smokes

### Sub-objetivo S1: C14 Recovery `--resume` modo CLI (Task)

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

### Sub-objetivo S2: C15 SKILL.md `faturando-odoo` (Task)

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
pos-cond:   NF autorizada SEFAZ + RecebimentoLf processado (via Skill 7) +
            picking entrada destino done (via Skill 5)
gotchas-invariante: G011 timing CIEL IT + G016 SSL + G018 weight + G019/G020
                    picking state + G022 over-reservation + G023 company_id +
                    G034 fiscal setup + G035 barcode + D-OPS-3 tracking +
                    D-OPS-5 produto sem lote
modos:      dry-run default; --confirmar real; --confirmar-sefaz nivel 2
            (IRREVERSIVEL); --auto-confirma-direcao-nova canary ETAPA F
status:     EXECUTADO_OK | EXECUTADO_PARCIAL | FALHA_USO | BLOQUEADO_SEFAZ |
            DRY_RUN_OK | DRY_RUN_PARCIAL | PRE_FLIGHT_BLOQUEADO
```

5+ receitas:
1. Canary 1 ajuste (testar pipeline end-to-end no real)
2. Bulk onda completa (100+ ajustes, ETAPA D irreversivel)
3. Resume apos crash mid-ETAPA D (Playwright SEFAZ rejeitou alguns)
4. Pre-flight isolado (sub-skill C5 sem dispatch da Skill 8)
5. Canary direcao nova FB->CD (--auto-confirma-direcao-nova)

Cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper).

### Sub-objetivo S3: C16+C17 Smokes dry-run + ate >=520 pytest (Task)

Smokes documentados em log JSON `/tmp/log_skill8_smokes_v18_*.json`:
- ETAPA F canary DEV_FB_LF com flag (caso real se houver; senao mock)
- ETAPA F canary TRANSFERIR_FB_CD com flag (caso real se houver; senao mock)
- Pipeline E+F com ajustes em F5e_SEFAZ_OK (cods com fluxo completo no INVENTARIO_2026_05)
- Pre-flight cod com cadastro fiscal inconsistente (G017 NCM ou G035 barcode)

Pytest >=520 (atual 513 +7 esperado: 3 recovery + 2 SKILL.md flow + 2 smokes wrap)

### Sub-objetivo S4: Atualizar docs + commit v18 (Task)

- CLAUDE.md estoque §6 (recovery + SKILL.md Skill 8 LIVE)
- ROADMAP HANDOFF v18 (entry NOVA acima da v17.5)
- PLANEJAMENTO §0 (status + checkpoints atualizados) + §12 trilha v18
- Memoria patterns se houver
- Commit consolidado v18

## INVESTIGACOES OPCIONAIS v18 (para canary REAL)

1. **Identificar candidato canary**: rodar query SQL/Odoo p/ achar 1 ajuste em F5e_SEFAZ_OK com acao_decidida=PERDA_LF_FB ou DEV_LF_FB que ainda nao foi processado em RecebimentoLf. Confirmar com Rafael antes de canary REAL.

2. **Validar caminho canary DEV_FB_LF**: se Rafael disponibilizar 1 ajuste real, validar fiscal_position fp 74 (FB->LF retrabalho assumido — sem precedente PROD). Se SEFAZ rejeitar com cstat=225, fp 74 esta errado e precisa ajuste em MATRIZ_INTERCOMPANY.

3. **Validar caminho canary TRANSFERIR_FB_CD**: se Rafael disponibilizar 1 ajuste real FB->CD, validar PT 50 + src=6 + dest=32 + invoice CFOP 1152. Robo CIEL IT pode ja' criar entrada DFe automatica — investigar antes de criar picking entrada manual (pode ser desnecessario).

## LEITURAS OBRIGATORIAS (ordem)

1. app/odoo/estoque/CLAUDE.md (constituicao §6 catalogo Skill 7+8 LIVE)
2. app/odoo/estoque/ROADMAP_SKILLS.md HANDOFF v17.5 (esta sessao terminou)
3. app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md §0 + §10.6 + §12 trilha v17.5 + C14 + C15 checkpoints
4. Memoria [[skill7-escriturando-pattern]] (pattern criacao Skill 7)
5. Memoria [[skill8-pipeline-completo-v17]] (status v17 + 11 fixes)
6. app/odoo/estoque/orchestrators/faturamento_pipeline.py (pipeline atual + executar_etapa_e v17.5 delegada)
7. app/odoo/estoque/scripts/escrituracao.py (atomo Skill 7 V1)
8. .claude/skills/escriturando-odoo/SKILL.md (modelo de SKILL.md para Skill 8)
9. scripts/inventario_2026_05/fat_lf_resume.sh (script shell SUPERADO p/ inspirar logica de recovery)

## CHECKLIST v18

[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde HEAD v17.5 (commit e8bfea73)
[ ] Pytest baseline: 513 verdes esperado
[ ] AskUserQuestion confirmar escopo S1-S4 + criterios de aceite
[ ] S1 Capinar `executar_pipeline_resume` + 3+ pytest
[ ] S2 Criar `.claude/skills/faturando-odoo/SKILL.md` com 5+ receitas
[ ] S3 Smokes documentados + pytest >=520
[ ] >=1 code-reviewer paralelo (SKILL.md richness + recovery edge cases)
[ ] S4 Docs atualizadas + commit v18
[ ] Atualizar PROMPT_PROXIMA_SESSAO.md para v19 (folhas fluxo + canary REAL + bulk REAL)

## REGRAS INVIOLAVEIS PRESERVADAS (v17.5)

94. `faturando-odoo` (Skill 8) = SO SAIDA. NUNCA inclui logica de criar
    RecebimentoLf ou escriturar entrada. Quem une saida (D) + entrada (E)
    e' o FLUXO L3.

95. `escriturando-odoo` (Skill 7) = SO ENTRADA. Encapsula RecebimentoLf
    + agg lotes + svc externo.

96. `LOCATION_ORIGEM_POR_DIRECAO` dict varia por acao (NAO hardcode 26489).

97. `PICKING_TYPE_ENTRADA_DESTINO_MANUAL` mapeia CD=50 + LF=19 (DEV_FB_LF
    reusa LF=19; LF/RECEB/IND PT 64 NAO usado — sem evidencia configural de ser melhor que PT 19 (ambos sem `l10n_br_tipo_pedido`); precedente PROD 4 pickings em PT 19).

98. Flag `--auto-confirma-direcao-nova` obrigatoria para ETAPA F canary
    em real-run (DEV_FB_LF + TRANSFERIR_FB_CD sem precedente PROD).

## NAO-FAZER (red flags v18)

X Implementar recovery sem testes de detector stagnation
X Criar SKILL.md sem 5+ receitas concretas + trade-offs
X Mexer no RecebimentoLfOdooService (NAO MEXER — 4562 LOC validados PROD)
X Mexer no script 09 (NAO MEXER — regra v14a-ops)
X Mexer no atomo Skill 7 sem necessidade (V1 STRICT V1 estavel)
X Esquecer cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md estoque §6)

## CRONOGRAMA REVISADO (apos v17.5)

v17 (concluida 2026-05-25): pipeline A-F LIVE + 11 fixes | commit e0a29f21
v17.5 (concluida 2026-05-26): REVERT E + Skill 7 + ETAPA F canary | commit e8bfea73
**v18 (proxima)**: C14 recovery + C15 SKILL.md Skill 8 + C17 smokes | Risco Medio
v19: C18 folhas fluxos (1.1 faturamento completo) + C19 cross-refs final + C20 canary REAL PROD | Risco Alto
v20+: C21 bulk REAL PROD + C22 code-review final + C23 commit + arquivar 09_* | Risco Alto

Total restante: 3 sessoes (v18 -> v20+).

## ESTADO ATUAL — apos v17.5 (PIPELINE A-F LIVE + SKILL 7 LIVE + ALINHADO §6)

Resumo:
- Pipeline A-F funcional via orchestrator (commit e8bfea73)
- Skill 7 `escriturando-odoo` LIVE (atomo C3 macro)
- ETAPA F canary com flag --auto-confirma-direcao-nova
- 513 pytest verdes
- 14/24 checkpoints concluidos
- 2 code-reviewers paralelos validaram v17.5 (3 fixes aplicados)
- Smoke dry-run PROD: ETAPA E cod 104000003 via atomo Skill 7 em 765ms

## REFERENCIAS RAPIDAS

- Commit v17.5: e8bfea73
- Commit v17: e0a29f21
- Commit v16: f4f964fc
- Baseline pytest: 513 verdes em 14.53s
- Audit Odoo 2026-05-26: PT 50 CD/IN/INTER (TRANSFERIR_FB_CD) src=6 dest=32; PT 19 LF/IN mantido (INDUSTRIALIZACAO_FB_LF — 4 pickings PROD); PT 64 LF/RECEB/IND NAO usado (sem evidencia configural de ser melhor — ambos sem tipo_pedido)
- Memoria v17.5: [[skill7-escriturando-pattern]]
- Memoria v17: [[skill8-pipeline-completo-v17]]

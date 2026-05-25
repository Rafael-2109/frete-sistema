# app/odoo/estoque — Operações de Escrita de Estoque no Odoo

**Status:** EM CONSTRUÇÃO (ONDA 0 concluída 2026-05-22; ONDA 0.4 ✅ fechada 2026-05-24 v3 — G019/G020 codificadas no service; **Skill 2 `transferindo-interno-odoo` ✅ MATURADA ARQUITETURALMENTE em 2026-05-25 v12 + ✅ FIX D-OPS-5 em v14b** — 3 modos atomicos + helper alto-nivel `distribuir_para_indisponivel` com fallback Modo B + flag `--cleanup-pos-bulk`; demanda 158 cods FB PROD 100% efetiva; bug `_listar_quants_origem` L1145+1147 RESOLVIDO em v14b com `aceita_tracking_none=True` default + atomo modo C aceita `lot_id_origem=None` validando product.tracking; 9 pytest novos + canary PROD 1 un cod 208000043 sem lote validado em ~1.5s + reversão completa; **Skill 5 `operando-picking-odoo` ESTENDIDA em 2026-05-25 v15a** com 3 atomos inter-company (`criar_picking_inter_company` codifica D-OPS-3 tracking='none' · `validar_picking_inter_company` fluxo F5b + G018 peso/volumes · `criar_picking_entrada_destino_manual` ETAPA F G023 + idempotencia origin); +19 pytest verdes (42→61 stock_picking_service); centralizadas constants ETAPA F em `app/odoo/constants/picking_types.py`; smoke PROD validou D-OPS-3 fix em 6 cods v14a-ops; **Skill 6 `planejando-pre-etapa-odoo` 🟡 mín viável COMPLETA v9** — 5 modos planejar/propor/listar/aprovar/executar-onda; **Skill 8 `faturando-odoo` ⬜ PLANEJADA + 3 MINERAÇÕES + TESTE REAL 6 CODS PROD v14a-ops + SUB-SKILL C5 PRONTA v14b + 3 ATOMOS INTER-COMPANY v15a** — documento vivo `PLANEJAMENTO_SKILL8_FATURANDO.md` com 24 checkpoints + §7.5 (5 dificuldades operacionais D-OPS-1..D-OPS-5); sub-skill `auditando-cadastro-fiscal-odoo` PERFIL V1 INVENTARIO ✅ COMPLETA (v14b — 14 pytest, smoke PROD OK, cross-refs aplicados); fix Skill 2 D-OPS-5 ✅ APLICADO + canary PROD validado; baseline pytest 435 verdes (416 + 19 v15a)) | **Atualizado:** 2026-05-25 v15a
**Audiência:** Claude Code (dev) + agente web. Doc **machine-first** — contratos e regras.

Pacote-destino da consolidação dos ~105 scripts ad-hoc de inventário (`scripts/inventario_2026_05/`) em **átomos versáteis e auto-seguros** (services), consumidos por **skills** (`.claude/skills/`) + o subagente **`gestor-estoque-odoo`** (`.claude/agents/`). Este CLAUDE.md é a **constituição** da arquitetura.

> Roadmap da migração (transitório): `app/odoo/estoque/ROADMAP_SKILLS.md`.
> Mineração dos 105 scripts (transitória, some quando a migração fechar): `docs/inventario-2026-05/consolidacao/{MAPA_ASSUNTOS,MAPA_SCRIPTS,PLANO_MIGRACAO}.md`.

---

## 0. Por que existe

Os 105 scripts ad-hoc nasceram de "não procurar → recriar" sob pressão. Objetivo: **nunca mais criar script ad-hoc** para operar o Odoo. Toda escrita passa a ser disparada via **skills-átomos** compostas em **fluxos**, orquestradas pelo `gestor-estoque-odoo`. Executor = **Claude Code E agente web**.

## 1. PRINCÍPIO FUNDADOR (inviolável)

> Toda operação de escrita no Odoo é um **átomo versátil e auto-seguro**:
> - **versátil** — serve N fluxos variando args; nunca assume um fluxo específico;
> - **auto-seguro** — gotchas do seu objeto codificados DENTRO como invariante (validador/guard/retry), não na memória do agente;
> - **2 modos** — `--dry-run` (default seguro: calcula e mostra o plano, não escreve) → `--confirmar` (executa).
>
> Os **fluxos** que compõem átomos vivem em **referências navegáveis** (`fluxos/`, árvore progressive disclosure), não em código nem no prompt.
>
> O subagente **pesquisa premissas → navega a árvore → compõe átomos → confirma**. NUNCA recompõe lógica perigosa do zero, NUNCA inventa SQL/XML-RPC, NUNCA cria script ad-hoc.

## 2. AS 5 CAMADAS

```
[L4] gestor-estoque-odoo (subagente WRITE)  → .claude/agents/gestor-estoque-odoo.md
        pesquisa premissas · navega árvore · compõe · mostra plano · confirma
[L3] REFERÊNCIAS de fluxo  → app/odoo/estoque/fluxos/ (árvore 1/2/3…)
        cada FOLHA = premissas + sequência de átomos + args + exemplo + gotchas
[L2] SKILLS = átomos versáteis por objeto  → .claude/skills/<skill>/
        SKILL.md (contrato + receitas) + scripts/ (--dry-run + --confirmar)
[L1] SERVICES / primitivas  → app/odoo/estoque/scripts/ (C1/C2) e orchestrators/ (C3)
        gotchas codificados, testados (pytest)
[L0] CONSTANTS  → app/odoo/constants/  (locations · operacoes_fiscais · picking_types · ids_diversos)
```
Dependência: cada camada só conhece a de baixo. L4 nunca pula direto para L1 sem passar por uma skill (L2).

## 3. CONTRATO DE ÁTOMO COMPONÍVEL (o coração)

Para muitos fluxos comporem poucos átomos, cada skill DECLARA um contrato (bloco obrigatório na `SKILL.md`):
```
## Contrato
- objeto:        <model Odoo principal> (ex: stock.quant)
- input:         <args nomeados>
- output:        <dict estruturado p/ encadear>
- pré-condições: <estado exigido do Odoo>
- pós-condições: <estado garantido>
- gotchas-invariante: <lista que o átomo trata sozinho>
- modos:         --dry-run (default) → --confirmar
```
**Composição (pipe):** o `output` de um átomo alimenta o `input` do próximo. **Regra de ouro:** o átomo NUNCA embute outro fluxo. `faturando-odoo` SÓ fatura (saída); `escriturando-odoo` SÓ escritura (entrada). Quem une é o FLUXO (L3).

## 4. PILAR: fluxos >> skills

Poucos átomos (~8, estáveis) ⟷ MUITOS fluxos (dezenas, crescem). Regras:
1. **Átomo genérico e estável.** Caso de negócio novo = nova folha de fluxo, NÃO skill nova. Caso "não cabe" nos args → avaliar arg faltante (estender retrocompatível) antes de criar átomo.
2. **Inteligência de negócio vive nos fluxos (L3)**, não nas skills (L2) nem no prompt (L4).
3. **Proibido** 1-skill-por-fluxo (explosão combinatória).

## 5. ÁRVORE DE FLUXOS vs PROMPT ENXUTO (progressive disclosure)

O prompt do subagente (L4) carrega só a **árvore de DECISÃO** (galhos), sem citar skills. Ao descer num ramo, carrega a **folha sob demanda** (`fluxos/<id>-<slug>.md`). Convenção e formato da folha: `app/odoo/estoque/fluxos/README.md`.

## 6. CATÁLOGO DE ÁTOMOS (skills ~8 WRITE + 1 READ ancillary — por objeto, versáteis)

### Skills WRITE (8 — ordem bottom-up, ver ROADMAP_SKILLS)

| Skill | Objeto Odoo | Service base (L1) | Camada | Status |
|-------|-------------|-------------------|--------|--------|
| `ajustando-quant-odoo` | stock.quant | `scripts/quant.py` (StockQuantAdjustmentService) | C1 | ✅ **MATURADA** (100 ajustes em prod 2026-05-23) |
| `transferindo-interno-odoo` | transferência interna intra-empresa (lote→lote mesma loc / loc→loc mesmo lote / MIGRAÇÃO↔Indisponível) | `scripts/transfer.py` (delega `ajustar_quant`×2 com `delta_esperado` propagado; G021/G022/G027) | C2 | 🟡 **mín viável** (33 pytest verdes; 2 scripts SUPERADOS 2026-05-24; orquestradores de planilha permanecem VIVOS) |
| `operando-mo-odoo` | mrp.production (cancelar — V1; criar/alterar sem demanda) | [`scripts/mo.py`](scripts/mo.py) (StockMOService — V1 criado 2026-05-24 v5; guard G-MO-01 furo contabil) | C2 | 🟡 **mín viável** (26 pytest verdes; 4 dry-run PROD validados; ainda 0 `--confirmar` em PROD) |
| `operando-reservas-odoo` | stock.move.line + stock.picking + stock.quant (residual) | [`scripts/reserva.py`](scripts/reserva.py) (StockReservaService) | C1/C2 | 🟡 **mín viável** (3 átomos · 6 pickings/15 quants em prod 2026-05-23) |
| `operando-picking-odoo` | stock.picking (cancelar/validar/devolver — criar/alterar-lote sem demanda) + **v15a: 3 átomos inter-company** (`criar_picking_inter_company` codifica D-OPS-3 · `validar_picking_inter_company` fluxo F5b + G018 · `criar_picking_entrada_destino_manual` ETAPA F G023+idempotencia origin) | [`scripts/picking.py`](scripts/picking.py) (StockPickingService) | C2 | 🟡 **mín viável estendida v15a** (6 átomos · **61 pytest verdes** (42 + 19 novos v15a) · invariante G019/G020 fechada · 6 casos dry-run PROD 2026-05-24 v3 · smoke v15a 6 cods v14a-ops validou D-OPS-3 detection) |
| `faturando-odoo` | **SÓ SAÍDA**: NF→robô CIEL IT→SEFAZ | `orchestrators/inventario_pipeline.py` (saída) | C3 | ⬜ |
| `escriturando-odoo` | **SÓ ENTRADA**: DFe/NF→in_invoice→saldo | pipeline (entrada) + escriturar_dfe | C3 | ⬜ |
| `planejando-pre-etapa-odoo` | planner+executor D007 (READ Odoo + WRITE banco local + **WRITE Odoo C3 macro v9**; 5 modos: planejar/propor/listar/aprovar/**executar-onda**) | [`scripts/pre_etapa.py`](scripts/pre_etapa.py) (PreEtapaEstoqueService + 7 helpers + 4 constantes; capinado v6) + [`orchestrators/pre_etapa_executor.py`](orchestrators/pre_etapa_executor.py) (executar_onda_pre_etapa compondo Skills 1+2; capinado v9) | C2 + C3 | 🟡 **mín viável COMPLETA** (42 pytest verdes — 21 service + 21 orchestrator; 5 modos CLI; hash sha256 anti-replay; capina 03b+04b+09b — ciclo completo planejar→propor→aprovar→executar fechado) |

### Skills READ ancillary (1 — sob demanda, complementam as WRITE)

| Skill | Objeto Odoo | Service base (L1) | Camada | Status |
|-------|-------------|-------------------|--------|--------|
| `consultando-quant-odoo` | stock.quant (read ao vivo via XML-RPC) | [`scripts/consulta_quant.py`](scripts/consulta_quant.py) (StockQuantQueryService) | READ | 🟡 **mín viável** (2 átomos · `listar_quants` + `auditar_pares` · auditoria pós-WRITE validada) |

### Sub-skills PRE-FLIGHT (1 — auditoria de cadastro fiscal antes de SEFAZ)

| Sub-skill | Objeto Odoo | Service base (L1) | Camada | Status |
|-----------|-------------|-------------------|--------|--------|
| `auditando-cadastro-fiscal-odoo` | product.product + l10n_br_ncm + stock.lot (G014) + AjusteEstoqueInventario (D-OPS-2) | [`scripts/cadastro_fiscal_audit.py`](scripts/cadastro_fiscal_audit.py) (CadastroFiscalAuditService) | READ-only + WRITE opcional G035 | 🟡 **mín viável V1** (perfil 'inventario'; cobre G017+G018+G035+G014 + D-OPS-2/3; **14 pytest verdes** + smoke PROD 6 cods 987ms; delegada pela Skill 8 v15+) |

Não-skills: `lot` (stock.lot) = **utils** em `_utils.py`. Leitura/diff/SOT batch (~33 scripts) = continuam ad-hoc operação viva.
Mapeamento script-fonte→átomo: `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`. Checkpoints: `app/odoo/estoque/ROADMAP_SKILLS.md`.

## 7. GRANULARIDADE (fluxo perigoso = 2 níveis)

Faturamento/escrituração tocam SEFAZ (irreversível): **átomo macro** (default) **+ átomos de etapa** (recuperação). Espelha `09_bulk` + `fat_lf_resume.sh` (saída) / `fat_lf_resume_entrada.sh` (entrada).

## 8. DETERMINISMO DOS GOTCHAS (gotcha = invariante codificado)

| Classe | Exemplos | Como vira determinístico | Onde |
|--------|----------|--------------------------|------|
| estrutural | G004 (picking→robô→SEFAZ) | é a assinatura do átomo | átomo |
| pré-flight fiscal | G035/G017/G007/G018 (→SEFAZ 225) | validador checa+corrige+bloqueia antes de transmitir (`gtin_validator`) | pré-condição |
| reserva | G028, G011 | guard em `validar()` (G028=`consolidar_move_lines`) | átomo picking |
| infra | G016 SSL | retry + keepalive | conexão |
| ordem | faturar→entrada; sleep; validar→liberar | guard clause (átomo N recusa se estado de N-1 ausente) | pré-condição |

**Pré-requisito bloqueante:** ~~G019/G020 ABERTOS~~ **G019/G020 FECHADAS no service** (2026-05-24 v3 — `validar()` re-lê `state` pós-`button_validate` e raise `RuntimeError` se != 'done'; `liberar_faturamento()` valida pré-cond `state=done` antes; cobertos por 8 testes pytest em `test_stock_picking_service.py`). Docs G019/G020 atualizadas de PROPOSTO → IMPLEMENTADO. Skill 8 `faturando-odoo` agora pode invocar `svc.validar()` confiando no invariante.
**Irredutível:** tempo do robô CIEL IT (externo) — polling+timeout dá resultado determinístico, nunca tempo.

## 9. SUBAGENTE `gestor-estoque-odoo` (WRITE)

Papel: orquestrar operações de escrita + **pesquisar premissas obrigatórias**. Loop: identificar → navegar árvore → carregar folha → pesquisar/validar premissas → compor em `--dry-run` → mostrar plano → `--confirmar` → verificar no Odoo. Diferenciado de `gestor-estoque-producao` (READ-ONLY). Prompt: `.claude/agents/gestor-estoque-odoo.md`.

## 10. FRONTEIRAS (delegar, não absorver)

| Assunto | Dono |
|---------|------|
| Consultar/projetar estoque (sem alterar) | `gestor-estoque-producao` (READ-ONLY) |
| Recebimento de COMPRAS (DFe fornecedor, 4 fases) | `gestor-recebimento` (árvore 1.2.2 delega) |
| CTe (frete) / pallet | módulos `fretes` / `pallet` |
| Diagnóstico cross-area NF/PO/financeiro | `especialista-odoo` |
| Criar/alterar código de integração | `desenvolvedor-integracao-odoo` |

## 11. ESTRUTURA DO PACOTE

```
app/odoo/estoque/
  __init__.py                          fachada
  CLAUDE.md                            este doc (constituição)
  ROADMAP_SKILLS.md                    task-list da migração (transitório) — HANDOFF v13 atualizado
  VALIDACAO_FINAL_SESSAO.md            historico consolidado das sessoes (§1-§16)
  PLANEJAMENTO_SKILL8_FATURANDO.md     **planejamento vivo MACRO Skill 8 — sobrevive N sessoes** (v13+)
  _utils.py                            resolvers de PREMISSAS: resolver_empresa, resolver_produto, EMPRESAS (✅) + (futuro) buscar_quant, _registrar_op, norm_lote
  scripts/                             átomos C1/C2 (quant, transfer, lot, picking, mo, reserva, pre_etapa)
  orchestrators/                       átomos C3 macro (pre_etapa_executor ✅, faturamento_pipeline ⬜ v15+)
  fluxos/                              folhas da árvore (L3, progressive disclosure)
# COMPAT: app/odoo/services/<nome>_service.py vira SHIM (re-export) — preserva 105 scripts + testes ativos
# **NOVO PATTERN v13 (skills MACRO C3 multi-sessao):** criar `PLANEJAMENTO_SKILL<N>_<NOME>.md` quando a capinagem exigir 3+ sessoes (criterio: SEFAZ irreversivel + estado distribuido + 4+ etapas dependentes). Regra inviolavel 0 do planejamento: LER inteiro + atualizar checkpoint ativo ANTES de qualquer modificacao em codigo.
```

## 12. INVARIANTES DE EXECUÇÃO (toda operação WRITE)

1. `--dry-run` sempre primeiro → mostrar plano.
2. Confirmação explícita antes de `--confirmar` (irreversível: SEFAZ).
3. Premissas pesquisadas E validadas antes de compor.
4. Verificar resultado DIRETO no Odoo (não confiar só no output).
5. Operação VIVA: 105 scripts ad-hoc intactos até o átomo maturar; arquivar SUPERADO só após checklist do ROADMAP/`PLANO_MIGRACAO §7`.

## 13. PONTEIROS

- Roadmap (capinar): `app/odoo/estoque/ROADMAP_SKILLS.md` (HANDOFF v13 atualizado)
- Historico consolidado: `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` (§1-§16)
- **Planejamento Skill 8 MACRO (sobrevive N sessoes):** `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (v13+) — **OBRIGATORIO LER ANTES de tocar Skill 8**
- Folhas de fluxo: `app/odoo/estoque/fluxos/`
- Subagente: `.claude/agents/gestor-estoque-odoo.md`
- Mineração script→átomo: `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`
- Assunto×camada×gotchas: `docs/inventario-2026-05/consolidacao/MAPA_ASSUNTOS.md`
- Estrutura/shims: `docs/inventario-2026-05/consolidacao/PLANO_MIGRACAO.md`
- IDs fixos / Gotchas Odoo: `.claude/references/odoo/IDS_FIXOS.md` · `.claude/references/odoo/GOTCHAS.md`
- Padrão skill completo: `~/.claude/projects/.../memory/feedback_skill_padrao_completo.md`

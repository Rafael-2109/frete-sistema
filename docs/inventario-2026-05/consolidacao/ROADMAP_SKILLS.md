# ROADMAP_SKILLS — task-list física (capinar átomo por átomo)

**Criado:** 2026-05-22 | **Constituição:** [`ARQUITETURA_ORQUESTRADOR_ODOO.md`](ARQUITETURA_ORQUESTRADOR_ODOO.md) | **Mineração:** [`MAPA_SCRIPTS.md`](MAPA_SCRIPTS.md)
**Para:** Claude Code + agente web. Este é o **arquivo de progresso vivo** da migração 105-scripts → ~8 skills-átomos + subagente `gestor-estoque-odoo`.

> **Como usar:** 1 assunto por vez, bottom-up. Antes de capinar QUALQUER átomo: `find scripts/inventario_2026_05 -name '*.py'` (operação VIVA — o nº muda) e **ler integral** os scripts-fonte (a situação no MAPA_SCRIPTS foi inferida, não lida — validar reabrindo). Preservar os ad-hoc até o átomo maturar; arquivar SUPERADO só após C9.

---

## CHECKLIST FIXO POR SKILL (instanciado em cada seção abaixo)

```
[ ] C1  Minerar scripts-fonte: LER INTEGRAL, extrair lógica + gotchas + edge cases (não confiar na situação inferida)
[ ] C2  Service base em app/odoo/estoque/ com gotchas codificados como INVARIANTE + testes pytest verdes
[ ] C3  Contrato de átomo definido (input · output · pré-cond · pós-cond · gotchas-invariante) — ver ARQUITETURA §3
[ ] C4  SKILL.md em .claude/skills/<skill>/ (contrato + receitas caso→args + gotchas + fronteira NÃO-USAR)
[ ] C5  scripts/<skill>/*.py: --dry-run (default seguro) + --confirmar; importam app.odoo.estoque
[ ] C6  VALIDAÇÃO POR REPRODUÇÃO (scripts ad-hoc = evals — ver seção abaixo): p/ CADA script-fonte CORRETO, skill --dry-run com os mesmos inputs → plano BATE (ground-truth: log auditoria/ se já rodou; ou script --dry-run se reexecutável)
[ ] C7  Registrar: gestor-estoque-odoo (skills:) + ROUTING_SKILLS.md + tool_skill_mapper.py + cross-refs
[ ] C8  Referência(s) de fluxo em consolidacao/fluxos/ que compõem o átomo (se já houver fluxo que o use)
[ ] C9  MOVER cada script VALIDADO → scripts/inventario_2026_05/_validados/<skill>/ (após confirmar 0 imports externos) + registrar linha em _validados/<skill>/VALIDACAO.md
[ ] C10 MAPA_SCRIPTS situação→SUPERADO + atualizar status neste ROADMAP
```

**Doc por skill (item "documentar após substituir"):** a própria `SKILL.md` é a doc de uso (CC+agente). Além dela: marcar MAPA_SCRIPTS (C10) e migrar o conteúdo de `manuais/<service>.md` para dentro da SKILL.md.

---

## ESTRATÉGIA DE VALIDAÇÃO — os scripts ad-hoc SÃO os evals

Não criamos evals sintéticos. Os ~105 scripts ad-hoc **corretos** são o **ground-truth**: um átomo só "atende" quando **reproduz** o que eles fazem. Aprovado → o script é **movido para `_validados/<skill>/`** (registro físico de progresso).

**Protocolo por script-fonte:**
1. **Triar (no C1)** — classificar cada script-fonte:
   - `EVAL` = correto + reproduzível → vira caso de validação;
   - `COM-BUG` = bug/dead-code conhecido (ex: `ajuste_estoque_lf_pasta17` docstring stale) → a skill faz o **CERTO**; divergência é **melhoria**, não falha (anotar);
   - `JÁ-MORTO` = discovery/pontual → não é eval, arquiva em `_historico/` (não em `_validados/`).
2. **Reproduzir em `--dry-run`:**
   - script **reexecutável** (idempotente, tem `--dry-run`): rodar `script --dry-run` **E** `skill --dry-run` com os mesmos inputs → comparar o **plano** (produto/lote/local/qtd/sinal);
   - script **já executado** (input consumido): comparar `skill --dry-run` vs `auditoria/log_*.json` (o que de fato rodou).
3. **PASSOU** (plano bate) → `git mv` do script para `scripts/inventario_2026_05/_validados/<skill>/` + linha em `_validados/<skill>/VALIDACAO.md` (`script · inputs · ground-truth · resultado · data`).
4. **NÃO bateu** → investigar antes de mover: bug no átomo (corrigir) · bug no script (anotar, skill mantém o certo) · semântica diferente (ajustar args/`--semantica`).

**Pastas (distintas):** `_validados/<skill>/` = comprovadamente coberto pela skill (com evidência) · `_historico/` = JÁ-MORTO sem reuso · `_ad-hoc/` = ainda ativo, não capinado. Rastreabilidade: "quais ad-hoc o átomo X já cobre" = `ls _validados/<skill>/`.

> ⚠️ Mover só após **0 imports externos** ao script (C9) — a maioria é standalone (executável), mas conferir. Operação VIVA: se um script validado ainda for necessário para rodar, a skill (que o reproduz) é quem roda agora.

---

## ONDA 0 — pré-requisitos (desbloqueiam tudo)

```
[ ] 0.1  Materializar app/odoo/estoque/ (scripts/ orchestrators/ _utils.py __init__.py) + shims em services/ (PLANO_MIGRACAO §1/§7)
[ ] 0.2  Esqueleto subagente .claude/agents/gestor-estoque-odoo.md (prompt = árvore de DECISÃO §5; WRITE; diferenciar de gestor-estoque-producao)
[ ] 0.3  Esqueleto consolidacao/fluxos/ + README com a convenção de folha (ARQUITETURA §5.1)
[ ] 0.4  (bloqueia faturamento) FECHAR G019/G020 — validar() engole erro / marca done falso
```

---

## ORDEM DE EXECUÇÃO (bottom-up)

| Onda | Skill | Por quê nesta ordem |
|------|-------|---------------------|
| 1 | `ajustando-quant-odoo` | **PILOTO** — service+manual+orquestrador já existem; valida o padrão skill+subagente+fluxo ponta-a-ponta |
| 2 | `transferindo-interno-odoo` | mais usada; `transferir_lote.py` já é o genérico (promover, não recriar) |
| 3 | `operando-reservas-odoo` · `operando-mo-odoo` · `operando-picking-odoo` | cancelamentos/limpeza (gaps); base concreta já existe |
| 4 | `planejando-pre-etapa-odoo` | planner; isolado |
| 5 | `escriturando-odoo` | entrada IC + DFe; depende de contrato estável de transfer |
| 6 | `faturando-odoo` | **ÚLTIMO** — macro perigoso (SEFAZ); exige ONDA 0.4 (G019/G020) fechada |

---

## SKILL 1 — `ajustando-quant-odoo`  (PILOTO)  ⬜
- **Objeto:** stock.quant | **Camada:** C1 | **Service:** `StockQuantAdjustmentService` ✅ (existe + manual + 22 testes; orquestrador `ajuste_inventario.py` existe)
- **Scripts-fonte (MAPA_SCRIPTS):** SUPERADOS já cobertos → 11, 12, 13, 14_v2, criar_saldo. AO-CAPINAR (composições) → limpar_quants_ghost, zerar_negativos, corrigir_reserved_negativo, fat_lf_03_prestage, fat_lf_06_consolidar_validos.
- **Gotchas-invariante:** G028 (consolidar_move_lines), G029 (payment_provider), action_apply_inventory infla quant NEGATIVO (usar picking p/ destino negativo), `=`→`in` em lot.name (G002).
- **Checkpoints:** C1 ⬜ · C2 ✅(service) ⬜(composições) · C3 ⬜ · C4 ⬜ · C5 ⬜ · C6 ⬜ · C7 ⬜ · C8 ⬜ · C9 ⬜ · C10 ⬜

## SKILL 2 — `transferindo-interno-odoo`  ⬜
- **Objeto:** transferência interna | **Camada:** C2 | **Service:** `StockInternalTransferService` 🟡 (falta manual) + `transferir_lote.py` (PROMOVER net-zero)
- **Scripts-fonte:** 10, 13_transferencia_migracao_fb, 15_transferencia_para_migracao, 15r, 15_transferir_preprod, 17_transferir_preprod_lf, substituir_lote_205030410, transferir_lote, transferir_local_pasta22, recuperar_aumentos_falhos, mover_migracao_para_indisponivel, ajuste_fb_cd_indisponivel, transferir_indisp_para_estoque_p15_cd, relotar_migracao_para_lotes_fb, transferir_fluxo_c, padronizar_migracao(→utils lote).
- **Semânticas (explícitas via arg, nunca inferir):** D010 sinal diff_qtd · D012 delta · D013 De-Para+wildcard (ARQUITETURA/MAPA §7).
- **Gotchas-invariante:** G028, G021, G022, G027, lot_id de empresa errada (filtrar company_id), 2 lotes MIGRAÇÃO/produto.
- **Checkpoints:** C1–C10 ⬜

## SKILL 3 — `operando-reservas-odoo`  ⬜
- **Objeto:** stock.move.line | **Camada:** C1/C2 | **Service:** GAP → criar (base: `limpar_reservas_fantasma.py`, action_unreserve + reassign)
- **Scripts-fonte:** remover_reservas_saida (base 4 companies), cancelar_reservas_migracao (G024/G025), limpar_reservas_fantasma, auditoria/teste_unlink_moveline_fantasma (canary validação).
- **Gotchas-invariante:** G024/G025 (unlink move.line órfã + recompute manual reserved_quantity), reserved_uom_qty inexistente Odoo 16.
- **Checkpoints:** C1–C10 ⬜

## SKILL 4 — `operando-mo-odoo`  ⬜
- **Objeto:** mrp.production | **Camada:** C2 | **Service:** GAP → criar
- **Scripts-fonte:** cancelar_mos (base argparse), 14_cancelar_mos_antigas_fb (filtro consumo=0).
- **Gotchas-invariante:** consumo>0 = furo contábil (bloquear cancelamento), manual_consumption não reserva via action_assign, componente preso em local errado.
- **Checkpoints:** C1–C10 ⬜

## SKILL 5 — `operando-picking-odoo`  ⬜
- **Objeto:** stock.picking | **Camada:** C2 | **Service:** `StockPickingService` 🟡 (falta manual)
- **Scripts-fonte:** 16_cancelar_pickings_fantasmas (filtro >7d/origin C24xxx) + etapas de 09/fat_lf_05; (criar/devolver/alterar-lote a destilar do pipeline).
- **Gotchas-invariante:** G011 (qty_done assign↔validate), G023 (entrada destino auto), G019/G020 (validar engole erro — ABERTOS, ver ONDA 0.4).
- **Checkpoints:** C1–C10 ⬜

## SKILL 6 — `planejando-pre-etapa-odoo`  ⬜
- **Objeto:** planner (read+valida) | **Camada:** C2 | **Service:** `PreEtapaEstoqueService` 🟡 (falta manual)
- **Scripts-fonte:** 03b_planejar_pre_etapa_cd, 04b_propor_pre_etapa_cd, 09b_executar_pre_etapa (executor → orchestrators/pre_etapa_executor), 04_propor_ajustes.
- **Gotchas-invariante:** D007 (consolidar em MIGRAÇÃO p/ minimizar NF); planner NÃO escreve (quem escreve cai em transfer/quant).
- **Checkpoints:** C1–C10 ⬜

## SKILL 7 — `escriturando-odoo`  (SÓ ENTRADA)  ⬜
- **Objeto:** entrada DFe/NF → in_invoice | **Camada:** C3 (macro + etapas E→F) | **Service:** pipeline (etapa entrada) + `escriturar_dfe_lf.py` (assunto NOVO)
- **Scripts-fonte:** entrada_fb_piloto (etapas 0-18), escriturar_dfe_lf (Fluxo A, NÃO reusa RecebimentoLf), fat_lf_resume_entrada.sh (resiliente a hang robô).
- **Gotchas-invariante:** G034 (CFOP entrada 1xxx ≠ saída 5xxx), G023, quirk DFe status 04, action_gerar_po_dfe usa company do USUÁRIO (forçar allowed_company_ids), tipo='serv-industrializacao' p/ CFOP 1901.
- **Fronteira:** recebimento de COMPRAS → gestor-recebimento; CTe → fretes; pallet → pallet.
- **Checkpoints:** C1–C10 ⬜

## SKILL 8 — `faturando-odoo`  (SÓ SAÍDA — ÚLTIMO)  ⬜
- **Objeto:** NF saída→robô CIEL IT→SEFAZ | **Camada:** C3 (macro + etapas B→D) | **Service:** `InventarioPipelineService` 🟡 (macro, ~20 gotchas, falta manual)
- **PRÉ-REQUISITO:** ONDA 0.4 (G019/G020 fechados).
- **Scripts-fonte:** 09_executar_onda1_bulk (A-F), 09c_executar_onda2_fb_cd (transfer_only 19-37), fat_lf_02_carregar (TIPO→ação), fat_lf_04_executar (driver B-F), fat_lf_05_executar_clean (G028 reserva multi-lote), fat_lf_cleanup (return+cancel+reset), fat_lf_resume.sh (loop B→D SSL-resiliente), teste_210030325 (→ exemplo no fluxo).
- **Gotchas-invariante:** G004, G011, G016 (SSL), G019/G020 (fechar antes), quarteto fiscal G035/G017/G007/G018 (pré-flight cstat 225), G028.
- **Checkpoints:** C1–C10 ⬜

---

## NÃO VIRAM SKILL (registro)
- **Leitura/diff/SOT** (39 scripts: monitor/*, 01, 08, comparar_sot_*, confronto_4_fontes, diff_*, etc.) → `consultando-sql` + `monitor/` (consolidar as 9 variações SOT é trabalho de leitura, não átomo write).
- **JÁ-MORTO** (discovery F0: 00-00e, auditoria/investiga_*, baixar_xml_preview_626032, debug_sefaz_608607) → arquivar em `_historico/`.
- **`operando-lote`** (stock.lot) = **utils** em `app/odoo/estoque/_utils.py` (chamado por skills 1/2).

---

## LEGENDA
⬜ não iniciado · 🟡 parcial · ✅ concluído · C# = checkpoint do checklist fixo.
Atualizar status do checkpoint e da skill A CADA avanço (este arquivo é o progresso vivo).

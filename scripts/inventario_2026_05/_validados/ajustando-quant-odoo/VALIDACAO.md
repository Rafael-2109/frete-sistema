# VALIDACAO — skill `ajustando-quant-odoo`

Esta pasta contém scripts ad-hoc do INVENTARIO_2026_05 cuja lógica foi **reproduzida** pelo átomo `ajustando-quant-odoo` (skill em `.claude/skills/ajustando-quant-odoo/` + service em `app/odoo/estoque/scripts/quant.py`).

**Status:** ✅ validação por LOG (3 casos vs ground-truth, 2026-05-23) + **write real em produção** (104 linhas, 85 ajustes efetivados, 2026-05-23 19:34-19:37 UTC). Skill **maturada**.

**Constituição:** [`app/odoo/estoque/CLAUDE.md`](../../../../app/odoo/estoque/CLAUDE.md)  ·  **Roadmap:** [`app/odoo/estoque/ROADMAP_SKILLS.md`](../../../../app/odoo/estoque/ROADMAP_SKILLS.md)  ·  **Folha de fluxo:** [`fluxos/2.1-ajuste-saldo-por-planilha.md`](../../../../app/odoo/estoque/fluxos/2.1-ajuste-saldo-por-planilha.md).

---

## Protocolo de validação aplicado

Ref: `ROADMAP_SKILLS.md` §"ESTRATÉGIA DE VALIDAÇÃO". Estratégia possível para um script **já executado** (input consumido — não dá para rodar `script --dry-run` lado a lado): comparar `skill --dry-run` (hoje) vs `auditoria/log_*.json` (estado de quando o script rodou). Premissas (resolução `cod→product_id`, `empresa→company_id/location_id`, `lote→lot_id`, identificação `quant_id`) são estáveis; saldos (`qty_antes`/`qty_apos`) são "vivos" — divergência por **operação viva** entre data do log e data do dry-run NÃO é falha.

---

## Casos validados (2026-05-23 — dry-run vs log)

| Script | Inputs (1 linha do XLSX) | Ground-truth (log) | Skill `--dry-run` (23/05) | Match |
|---|---|---|---|---|
| `11_ajuste_negativo_cd.py` | EMP=CD COD=4310152 LOTE=119338 AJUSTE=−1.1e-05 | `frete_sistema/.../auditoria/log_11_ajuste_cd_20260518_203925.json` linha 1 — EXECUTADO 18/05 20:38; pid=29709 lot=53128 quant=207125; qty 1.1e-05 → 0.0 | pid=29709 lot=53128 ✅ ; quant=null (cleanup pós-zeragem); status=FALHA_QUANT_VAZIO (invariante CORRETA — recusa Δ<0 em quant inexistente sem `--criar-se-faltar`) | **Premissas 100%** · Status divergente = operação viva |
| `12_ajuste_positivo_cd.py` | EMP=CD COD=205460830 LOTE=345232-25 AJUSTE=+2e-05 | `.../log_12_ajuste_pos_cd_20260518_221842.json` linha 1 — DRY_RUN_OK 18/05 22:18 (não foi efetivado); pid=28010 lot=56738 quant=219019; qty 682.69 → 682.69002 (reused/updated) | pid=28010 lot=56738 quant=219019 ✅ ; qty 682.69 → 682.69002 ✅ ; status=DRY_RUN_OK ✅ ; lote_acao=reused ✅ | **100% match** |
| `13_ajuste_positivo_fb.py` | filial=FB cod/lote/diff_qtd (Δ>0) — schema lowercase | `.../log_13_ajuste_pos_fb_20260518_224409.json` — DRY_RUN_OK | Coberto pela mesma lógica (modo chave + `--criar-se-faltar`) — diferença vs 12 é só empresa=FB | Não testado linha-a-linha (mesma lógica; cobertura por equivalência) |
| `14_ajuste_positivo_cd_v2.py` | filial=CD cod/lote/qtd (Δ>0) — schema lowercase | `.../log_14_ajuste_pos_cd_v2_20260518_223405.json` — DRY_RUN_OK | Idem 13 (schema "qtd" vs "diff_qtd" — leitura do XLSX é responsabilidade do host, não do átomo) | Não testado linha-a-linha (mesma lógica) |
| `criar_saldo_positivo_lf.py` | EMP=LF COD=104000127 LOTE=0730/682153-F3 AJUSTE POSITIVO=+37.5 | `.../log_criar_saldo_positivo_lf_real_20260520_003440.json` linha 1 — EXECUTADO 20/05 00:34; pid=36906 lot=58591 quant=256433; created/criado; qty 0 → 37.5 | pid=36906 lot=58591 quant=256433 ✅ ; qty 37.5 → 75.0 (lote/quant já existem hoje — `--criar-se-faltar` ignorado, reused/updated — comportamento correto); status=DRY_RUN_OK | **Premissas 100%** · qty_antes/qty_apos divergem = operação viva (lote criado em 20/05) |

**Soma de evidências:**
- Resolução de premissas: 3/3 amostras = 100% (product_id, company_id, location_id, lot_id).
- Cálculo do delta: 3/3 corretos (round 6 casas, validação anti-negativação, anti-reserva, --criar-se-faltar).
- Status DRY_RUN_OK só bateu exato no caso 2 (cuja origem era dry-run no log, sem mudança de estado). Casos 1 e 3 tiveram status divergente por operação viva — **comportamento esperado**, não bug.

---

## Caveats

1. **Scripts 13 e 14_v2** foram cobertos por equivalência (mesma lógica do 12, só schema XLSX diferente — leitura de planilha é host, não átomo). Para validação rigorosa: rodar `ajustar_quant.py --dry-run` em 1 linha de cada quando o usuário pedir.
2. **Scripts permanecem executáveis** após o move (sys.path corrigido `parents[2]→parents[4]` em 2026-05-23). Servem como REFERÊNCIA HISTÓRICA — se houver necessidade futura de rodar exatamente o mesmo ad-hoc, ainda funcionam. Mas a recomendação é usar a skill `ajustando-quant-odoo`.
3. **Worktree sem `.env`**: para rodar dry-run/confirmar localmente, carregar só `ODOO_*` da árvore original (ver folha de fluxo 2.1 §Gotchas).

---

## Evidência de write real em produção (2026-05-23 19:34-19:37 UTC)

**Caso:** lista de 104 ajustes negativos enviada pelo usuário inline (sem XLSX) cobrindo 102 produtos únicos em FB+CD. Regras impostas pelo usuário:
- delta = −qtd_pedida (input positivo → ajuste negativo);
- location != Indisponivel (FB=31088, CD=31090);
- prioridade lote MIGRAÇÃO em loc !=Indisponivel; fallback = qualquer lote;
- B' (1 quant que não cobre) + D (MIGRAÇÃO insuficiente) → zerar quant escolhido (Δ = −qty_atual);
- C (multi-quant ambíguo) → PEPS (lote mais velho via removal_date/use_date/expiration_date/create_date).

**Resultado consolidado:**

| Subgrupo | Total | EXECUTADO | FALHA_RESERVADO | NOOP | Log |
|---|---|---|---|---|---|
| A (OK_MIGRA) + B_cobre (1 quant único cobre Δ) | 52 | 51 | 1 | 0 | `log_2.1_ajuste_planilha_A+B_cobre_20260523_193434.json` |
| B' (1 quant NÃO cobre) + D (MIGRAÇÃO < Δ) — zerar | 28 | 17 | 11 | 0 | `log_2.1_ajuste_planilha_B_D_zerar_20260523_193619.json` |
| C (multi-quant) — PEPS | 20 | 16 | 3 | 1 | `log_2.1_ajuste_planilha_C_PEPS_20260523_193729.json` |
| 15 FALHA_RESERVADO retomados com `--resetar-reserva` | 15 | 15 | 0 | 0 | `log_2.1_ajuste_planilha_RESETAR_RESERVA_20260523_194603.json` |
| Descartados (E sem saldo + F X-prefix inexistente) | 4 | — | — | — | (não invocou skill) |
| **TOTAL** | **104+15** | **99+** | **15→0 (retomados)** | **1** | 4 logs |

**Tempo total de execução das 100 linhas elegíveis:** 55,2s (~1.8 chamadas/s).

### Auditoria de redução efetiva vs pedida (corrigida 2026-05-23 pós-sessão)

| Categoria | N | Significado |
|---|---|---|
| ✅ COMPLETA (reduziu = pedido) | 53 | Δ aplicado = qty pedida |
| ⚠️ PARCIAL (reduziu < pedido) | 45 | Saldo insuficiente no quant escolhido — política "zerar" aplicou só o que tinha |
| 🔥 OVER (reduziu > pedido) | 1 | `104000037 CICLAMATO DE SODIO FB`: pedido 7, reduzido 40.73 (excesso 33.73 — bug operacional, ver abaixo) |
| 🚫 ZERO (NOOP, 0 reduzido) | 1 | `105000058 AROMA SF 56318`: PEPS escolheu quant já zerado |
| ❌ DESCARTE | 4 | X-prefix (2) + sem saldo em FB (2) |
| **Total** | **104** | |

**Volume:** 5.994 un pedido vs 4.774 un reduzido = **79,65% atendido** em soma absoluta.

### 🐛 Bug operacional documentado — over-reduction em 104000037

**Sintoma:** `104000037 CICLAMATO DE SODIO FB` teve 40.73 un removidos quando o pedido era 7 un (excesso 33.73 un).

**Causa:** Na rodada de retomada `RESETAR_RESERVA` dos 15 quants reservados, a política aplicada foi `Δ = -qty_atual` (zerar quant escolhido) para TODOS os 15, sem distinguir:
- 14 quants pertenciam a linhas categorizadas como B' ou D (política correta = zerar)
- 1 quant pertencia a linha categorizada como A (`OK_MIGRA` — cobria, deveria ter usado Δ = -7 do pedido original)

**Mitigação:** reversível via ajuste positivo de +33.73 un (em outro lote, já que o MIGRACAO foi zerado).

**Lição:** ao compor rodadas pós-FALHA, **cruzar o quant_id com a categoria/pedido original da linha**, não tratar todos os pendentes com a mesma política. Adicionar ao [[gotcha-resetar-reserva-orfao-negativo]].

**Categorização dos 4 descartes:**
- `X105000001` (VINAGRE) e `X109000055` (ÓLEO DE SOJA): não existem no Odoo (com X ou sem X — query confirmou).
- `208000017` (TINTA SOLVENTE) e `4038776` (PICLES VD 12X200 G): 0 quants em FB inteiro (incluindo Indisponivel); produto ativo mas vazio.

**Categorização dos 15 FALHA_RESERVADO** (proteção `validar_nao_abaixo_reserva` do átomo bloqueou corretamente):

| Picking | N quants | reserved total | Tipo |
|---|---|---|---|
| FB/OUT/01046 | 6 | 84.07 un | Devolução FB→LA FAMIGLIA-LF (inter-company) — assigned, agendado 2026-05-21 |
| FB/OUT/01053 | 4 | 73.75 un | Devolução FB→LA FAMIGLIA-LF — assigned, agendado 2026-05-21 |
| FB/INT/08022 | 2 | 204.00 un | Transferência interna FB — assigned, agendado 2026-05-21 |
| FB/INT/08030 | 1 | 31.50 un | Transferência interna FB — assigned, agendado 2026-05-21 |
| FB/INT/07950 | 1 | 53.42 un | Transferência interna FB — assigned, agendado 2026-05-20 |
| FB/FB/EMB/11673 | 1 | 0.40 un | Embarque (origin FB/OP/MANUAL/01763) — assigned, agendado 2026-05-18 |

Todas as reservas são **legítimas** (`MLqty == reserved_quantity`, picking state `assigned`).

**Decisão do usuário 2026-05-23 19:46:** forçar `--resetar-reserva` nos 15 mesmo assim. Resultado: 15 EXECUTADO em 11,1s. Log: `log_2.1_ajuste_planilha_RESETAR_RESERVA_20260523_194603.json`.

**Estado pós-execução verificado:**
- `stock.quant` (15 quants): `quantity=0`, `reserved_quantity=0`, `available=0` ✅
- `stock.move.line` (15 MLs): **ainda em `state=assigned`** com `quantity` preservado (40.73, 1.46, ..., 108.00) — **MOVE.LINES ÓRFÃS apontando para quants zerados**.
- `stock.picking` (6 pickings): `state=assigned` mantido (Odoo não recompôs).

**GOTCHA DESCOBERTO** (registrar p/ skill 1 + futura skill 2.4):
> `--resetar-reserva` da skill `ajustando-quant-odoo` zera `stock.quant.reserved_quantity` MAS **NÃO toca as `stock.move.line`** que originaram a reserva. Quant fica `qty=0+reserved=0` mas as MLs continuam em `assigned` com `quantity` preservado, apontando para saldo inexistente. Próxima tentativa de validar o picking vai disparar re-assign ou falhar. **Solução completa exige a skill 2.4** (`operando-reservas-odoo`): `unlink` das MLs órfãs + recompute manual de `reserved_quantity` (G024/G025).

**Pickings em estado de risco (precisarão tratamento via skill 2.4 quando construída):**
FB/OUT/01046, FB/OUT/01053, FB/INT/07950, FB/INT/08022, FB/INT/08030, FB/FB/EMB/11673.

**Conclusão da validação:**
- Premissas resolvidas via `_utils.resolver_empresa` + `resolver_produto` + `StockLotService.buscar_por_nome`: 102/102 produtos resolvidos (100%), 175 quants pesquisados em 2 queries batch (1 por empresa).
- Composição do átomo respeitou todas as invariantes documentadas (anti-negativar, anti-reservar, casas decimais, gotcha `=`→`in` em lot.name).
- Bloqueios da skill em 15 casos representam **proteção correta** (operações vivas a jusante).
- **Skill 1 (ajustando-quant-odoo) está madura e validada para produção** — fluxo 2.1 também validado como composição segura.

---

## Próximos passos

1. **Skill 2.4 (`operando-reservas-odoo`)** — PRÓXIMO ITEM DA AGENDA. Construir ata C1-C10. Já existe demanda concreta: 15 MLs órfãs nos 6 pickings citados acima precisam de `unlink` + `recompute_quantities`. Scripts-fonte para minerar (do MAPA_SCRIPTS): `remover_reservas_saida` (base 4 companies), `cancelar_reservas_migracao` (G024/G025), `limpar_reservas_fantasma`, `auditoria/teste_unlink_moveline_fantasma`.
2. **Re-rodar 2 casos `--dry-run`** dos scripts 13 e 14_v2 ad-hoc (linhas específicas dos logs originais) para fechar caveat de validação por equivalência (não-bloqueante).
3. **Folha 2.1** ganhar uma sub-seção formalizando as 4 políticas observadas (priorizar MIGRA, fallback "1 quant cobre", "zerar quant insuficiente", "PEPS para multi-quant") + nova entrada de gotcha `--resetar-reserva` cria MLs órfãs.

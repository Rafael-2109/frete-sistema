# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo)

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão. Mantém você dentro do plano global sem desviar.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, base atualizada via fast-forward em 2026-05-24 → `main`@b4f7b24c). NADA commitado ainda na branch — `main` continua VIVO em paralelo (Rafael commita lá).

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^ODOO_' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
```

## Estado atual (sessão 2026-05-24 v2 fechada — Skill 2 maturada)

**4 skills no catálogo do `gestor-estoque-odoo`:**
- ✅ **Skill 1 `ajustando-quant-odoo`** MATURADA — 100 ajustes em PROD 2026-05-23; 30 pytest; 5 scripts SUPERADOS; guard `delta_esperado` (2026-05-24 v1)
- 🟡 **Skill 2 `transferindo-interno-odoo`** mín viável (NOVA 2026-05-24 v2) — 33 pytest (com 2 testes FALHA_AUMENTO novos); 2 scripts SUPERADOS; 2 modos atômicos (A lote→lote / B loc→loc); delega `ajustar_quant`×2 com `delta_esperado` propagado; G021/G022/G027 codificados como invariante; **0 execuções `--confirmar` em PROD**
- 🟡 **Skill 2.4 `operando-reservas-odoo`** mín viável — 3 átomos: `cancelar_moves_orfaos`, `cancelar_picking_inteiro`, `zerar_reserved_residual` (6 pickings + 15 quants validados 2026-05-23)
- 🟡 **Skill 9 `consultando-quant-odoo`** mín viável (READ ancillary) — 2 átomos: `listar_quants` (9 params), `auditar_pares`

**10 scripts em `_validados/`** (5 ajustando-quant + 3 operando-reservas + 2 transferindo-interno). `_validados/consultando-quant-odoo/` tem só VALIDACAO.md (C9 ⏸️).

## LEITURAS OBRIGATÓRIAS ANTES DE AGIR (ordem)

1. `app/odoo/estoque/CLAUDE.md` — constituição (§1 princípio fundador, §4 fluxos>>skills, §6 catálogo, §12 invariantes)
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF (estado atual + próximos passos)
3. `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` — auditoria final + code-review + pre-mortem + pendências (§7 = Skill 2 v2)
4. Memórias-chave:
   - `[[arquitetura_orquestrador_odoo]]` — princípio das 5 camadas + fluxos>>skills
   - `[[skill2_transfer_interno_pattern]]` — **NOVA 2026-05-24 v2** — pattern emergente da Skill 2 (ajustar_quant×2, 2 modos, G021/G022)
   - `[[gotcha-resetar-reserva-orfao-negativo]]` — `--resetar-reserva` + unlink ML = reserved NEGATIVO; OBRIGATÓRIO chamar `zerar_reserved_residual` ao final
   - `[[feedback-skills-demanda-driven]]` — skills nascem de casos reais; átomos previstos permanecem ⬜ até demanda surgir
   - `[[feedback-incompletude-quebra-regras]]` — incompletude = não seguir regras; C7-C10 INVIOLÁVEIS

## REGRAS INVIOLÁVEIS (não negociáveis)

1. **`--dry-run` antes do real**; confirmação explícita antes de SEFAZ/irreversível.
2. **NUNCA criar script ad-hoc** — capinar a skill. Workspace `/tmp/` é OK (descartável).
3. **`fluxos>>skills`** — caso novo = folha de fluxo, NÃO skill nova. Skill nova só com 2+ casos reais que não cabem em fluxo.
4. **Skills nascem de DEMANDAS REAIS** — não implementar átomos especulativamente.
5. **C7-C10 são INVIOLÁVEIS** — completar cada checkpoint com artefato concreto (não só "marcar feito"). Incompletude = violação de regras.
6. **Verificar resultado DIRETO no Odoo** — não confiar só no output de scripts/services.
7. **Operação VIVA** — preservar ad-hocs até cada átomo maturar; arquivar SUPERADO só após C9.
8. **Premissas pesquisadas e validadas ANTES de compor átomos.**
9. **Após qualquer `unlink` em MLs em quants com `reserved=0`**: chamar `zerar_reserved_residual` (G027 da skill 2.4).
10. **Ao retomar FALHAs**: cruzar `quant_id` com pedido original — NÃO aplicar política homogênea (lição do bug `104000037 CICLAMATO`, 2026-05-23).
11. **Composição de átomos propaga `delta_esperado` a CADA chamada** (regra inviolável 11 — Skill 2 v2 codifica isso por default em `transferir_entre_lotes_v2` / `transferir_entre_locations`).
12. **`--corrigir-para-esperado` em batch SEMPRE rodar `--dry-run` primeiro** e revisar manualmente as linhas auto-corrigidas.
13. **Antes de modificar `app/odoo/estoque/scripts/quant.py`**: `pytest tests/odoo/services/test_stock_quant_adjustment_service.py` (baseline 30 verdes). Se quebrar, NÃO commitar.
14. **(NOVO 2026-05-24 v2) Antes de modificar `app/odoo/estoque/scripts/transfer.py`**: `pytest tests/odoo/services/test_stock_internal_transfer_service.py` (baseline 33-35 verdes — 33 mín, 35 se incluir 2 testes novos de FALHA_AUMENTO). Se quebrar, NÃO commitar.

## Pendências do code-review (não-bloqueantes restantes)

Identificadas pelos code-reviewers em 2026-05-24 v2. CR2#3 foi corrigido ainda na sessão (linha do fork removida em ROUTING_SKILLS). Restam:

| # | Sev | Arquivo | Pendência |
|---|-----|---------|-----------|
| CR1#3 | IMP | `transfer.py:392-393` | `_melhor_lote_migracao_na_loc` zero-saldo fallback (`lids[0]`) untested |
| CR1#4 | IMP | `test_v2_resetar_reserva_origem_propaga` | assertion `write.call_count == 3` é fragil (implementation detail); melhor asserir `res['reducao_origem']['acao']` |
| CR2#2 | IMP | `MAPA_SCRIPTS.md` | 3 scripts (`transferir_indisp_para_estoque_p15_cd`, `ajuste_fb_cd_indisponivel`, `transferir_local_pasta22`) aparecem em DUAS seções (transfer.py E quant.py+MIGRAÇÃO↔Indisponível) — dual-ownership ambíguo, pré-existente à sessão |
| ~~CR2#3~~ | ~~IMP~~ | ~~`ROUTING_SKILLS.md:32`~~ | ✅ **CORRIGIDO 2026-05-24 v2** — fork "via gestor OU direto" removido; linha consolidada na geral, triggers ampliados |

Não-bloqueantes da sessão v1 (continuam pendentes — listadas em VALIDACAO_FINAL_SESSAO §2):
- 8 issues cosméticas (cobertas em §"pendências cosméticas restantes" — tratar conforme próxima sessão tocar nos arquivos).

## Próxima skill do roadmap (escolha em sessão futura)

1. **Skill 4 `operando-mo-odoo`** — próxima na ordem bottom-up. Cobre `cancelar_mos.py` e `14_cancelar_mos_antigas_fb.py`. **Service GAP — criar do zero.** Gotchas: consumo>0 = furo contábil (bloquear cancelamento), `manual_consumption` não reserva via `action_assign`, componente preso em local errado.

2. **Skill 5 `operando-picking-odoo`** — `StockPickingService` parcial existe. Cobre `16_cancelar_pickings_fantasmas` + etapas 09/fat_lf_05 (criar/devolver/alterar-lote a destilar). Gotchas: G011 (qty_done assign↔validate), G023 (entrada destino auto), G019/G020 (validar engole erro — ABERTOS).

3. **Fluxos compostos da Skill 2** — escrever folhas filhas (`2.2.D010`, `2.2.D012`, `2.2.D013`) para cobrir orquestradores de planilha (13, 15, 15r, transferir_lote, transferir_local_pasta22, ajuste_fb_cd_indisponivel, mover_migracao, relotar). Implementar somente se padrão se repetir com 2+ casos reais cada.

4. **Skill 2 extensões** — adicionar args `--lot-id-origem`/`--lot-id-destino` na CLI (cobre `padronizar_migracao` sem ambiguidade); `transferir_quantidade_para_lote_v2` com destino sem lote (atualmente ValueError); cobertura do zero-saldo fallback em `_melhor_lote_migracao_na_loc`.

5. **Demandas reais** orientam — cada caso real revela novos átomos necessários. As 3 últimas sessões provaram isso (skills 1/2/2.4/9 nasceram de demandas concretas).

## ARQUITETURA — relembrar a árvore de decisão

```
1  NF inter-company (emissão/SEFAZ entre filiais)
   1.1 só faturamento (saída)             → fluxos/1.1.* (faturando-odoo ⬜)
   1.2 só entrada/escrituração            → fluxos/1.2.1 (escriturando-odoo ⬜)
   1.3 transferência completa (saída+entrada) → fluxos/1.3 ⬜
2  Estoque (sem NF)
   2.1 ajuste de saldo (1 quant; planilha) → ajustando-quant-odoo ✅ [folha 2.1]
   2.2 realocar saldo (lote↔lote mesma loc / loc↔loc mesmo lote / MIGRA↔Indisp) → transferindo-interno-odoo 🟡 [folha 2.2]  ← NOVA 2026-05-24
   2.3 transferir saldo entre CÓDIGOS → (skill transferencia-saldo-codigo) ⬜
   2.4 cancelar reserva / cirurgia ML / picking → operando-reservas-odoo 🟡 [folha 2.4]
   2.5 cancelar/criar/devolver picking genérico → operando-picking-odoo ⬜
   2.9 CONSULTA AO VIVO (quants/MLs) → consultando-quant-odoo 🟡 [folha 2.9]
3  Produção / PCP
   3.1 cancelar/criar/alterar MO → operando-mo-odoo ⬜
```

## CHECKLIST DA SESSÃO

```
[ ] Setup (cd worktree + venv + ODOO_*)
[ ] Ler ROADMAP_SKILLS HANDOFF + VALIDACAO_FINAL_SESSAO §7
[ ] Verificar pytest baseline: pytest tests/odoo/services/test_stock_internal_transfer_service.py tests/odoo/services/test_stock_quant_adjustment_service.py (esperado: 65 verdes; se < 65 INVESTIGAR antes de mexer)
[ ] Considerar rebase incremental (main pode ter avançado de novo)
[ ] Confirmar com Rafael: Skill 4 (recomendado) OU Skill 5 OU fluxos compostos Skill 2 OU outra prioridade
[ ] Cada átomo novo: C1-C10 SEM PULAR ETAPAS
[ ] Final da sessão: N code-reviewers + atualizar VALIDACAO_FINAL_SESSAO + memórias relevantes
[ ] Atualizar PROMPT_PROXIMA_SESSAO para a próxima
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
- ❌ Modificar `transfer.py` ou `quant.py` sem rodar pytest ANTES e DEPOIS
- ❌ Compor átomos sem propagar `delta_esperado` (regra inviolável 11)

## Logs de auditoria

### Sessão 23/05 (104 ajustes negativos + cirurgia em 6 pickings)
```
scripts/inventario_2026_05/auditoria/
  log_2.1_ajuste_planilha_A+B_cobre_20260523_193434.json   (52 lines)
  log_2.1_ajuste_planilha_B_D_zerar_20260523_193619.json   (28)
  log_2.1_ajuste_planilha_C_PEPS_20260523_193729.json      (20)
  log_2.1_ajuste_planilha_RESETAR_RESERVA_20260523_194603.json (15)
  log_2.4_operar_reservas_20260523_220239.json             (6 pickings)
  log_2.4_zerar_reserved_residual_20260523_220404.json     (15 quants)
```

### Sessão 24/05 v1 cleanup (resolução das pendências bloqueantes)
```
scripts/inventario_2026_05/auditoria/
  log_2.1_reversao_ciclamato_20260524_000000.json          (1 quant — +33.7319 un CICLAMATO)
  log_2.4_zerar_residual_orfao_aroma_20260524_000001.json  (1 quant — órfão AROMA)
/tmp/
  comunicado_pickings_20260524.md                          (texto para operadores físicos)
```

### Sessão 24/05 v2 Skill 2 (sem --confirmar em PROD)
```
/tmp/
  skill2-mineracao-sintese.md                              (sintese arquitetural)
  log_skill2_C6_validacao_dry_run.json                     (3 casos dry-run validados)
```

Comece pela leitura dos 3 docs obrigatórios + memórias-chave + verificar pytest baseline (esperado 65 verdes Skill 2 + Skill 1). Confirme com Rafael o foco da sessão (recomendação: Skill 4 `operando-mo-odoo` ou Skill 5 `operando-picking-odoo`, ambas próximas na ordem bottom-up). Confirme antes de iniciar qualquer write na produção.

---END---

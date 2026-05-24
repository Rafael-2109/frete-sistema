# VALIDACAO_FINAL_SESSAO — 2026-05-23

> Documento consolidado da sessão de 23/05/2026 (2 sessões consecutivas: 104 ajustes negativos + auditoria pós-WRITE). 3 skills nasceram/maturaram: `ajustando-quant-odoo` (✅), `operando-reservas-odoo` (🟡), `consultando-quant-odoo` (🟡).

**Conteúdo:** auditoria final do efetuado · code-review consolidado · pre-mortem rigoroso · pendências.

---

## 1. Auditoria final — redução efetiva vs pedida

### Resumo numérico (104 pares cod+empresa)

| Categoria | N | Volume |
|---|---|---|
| ✅ COMPLETA (reduziu = pedido) | **53** | — |
| ⚠️ PARCIAL (reduziu < pedido) | **45** | saldo insuficiente; muitos com diff < 1 un (precisão de arredondamento) |
| 🔥 OVER (reduziu > pedido) | **1** | `104000037 CICLAMATO DE SODIO FB`: pedido 7, reduzido 40.73 (excesso 33.73 un — bug operacional, ver §3) |
| 🚫 ZERO (NOOP, 0 reduzido) | **1** | `105000058 AROMA SF 56318 FB`: PEPS escolheu quant já zerado |
| ❌ DESCARTE | **4** | X-prefix (2: `X105000001 VINAGRE`, `X109000055 OLEO DE SOJA`) + sem saldo em FB (2: `208000017 TINTA`, `4038776 PICLES`) |
| **Total** | **104 ✓** | |

**Volume:** 5.994 un pedido vs **4.774 un reduzido = 79,65% atendido** em soma absoluta.

### Estado pós-operação dos quants ajustados (auditar_pares pós-fix CR1#7)

| Classificação | N | Significado |
|---|---|---|
| `totalmente_zerado` | 17 | qty=0 em qualquer lugar |
| `so_indisp` | 45 | saldo só em location Indisponivel |
| `com_saldo_nao_indisp` | 39 | saldo legítimo em outros lotes/locais (não tocados) |
| `quant_orfao_reserva` | **1** | `qty=0 + reserved≠0` (NOVO achado pós-fix) |
| `sem_produto` | 2 | X-prefix |
| Total | 104 ✓ | |

**🔍 Achado novo via fix CR1#7:** `104000039 AROMA NATURAL - ALHO FB` em `FB/Pré-Produção/Linha Manual` (location 4067), quant id=260657: `qty=0` e `reserved=-0.6` (NEGATIVO). **Órfão pré-existente** (não estava na lista de 15 que limpamos). Tratamento pendente — operador físico decide.

---

## 2. Code-review consolidado (4 reviewers paralelos)

### Bugs operacionais corrigidos NESTA sessão

| # | Achado | Confiança | Status |
|---|---|---|---|
| **CR1#4** | SKILL.md skill 2.4 prometia `--move-ids`, CLI usa `--moves-writes` | 95% | ✅ **CORRIGIDO** (SKILL.md alinhado) |
| **CR1#5** | `zerar_reserved_residual` sem CLI; SKILL.md sugere "OBRIGATÓRIO" | 90% | ✅ **CORRIGIDO** (CLI agora aceita 3 modos: cirurgia / cancelar-picking / zerar-residual) |
| **CR1#7** | `auditar_pares` filtrava `quantity != 0`, perdia MLs órfãs | 85% | ✅ **CORRIGIDO** (domain agora `quantity != 0 OR reserved_quantity != 0`); descobriu 1 par órfão adicional |
| **CR2#1** | Subagente sem links `[folha 2.4]` e `[folha 2.9]` | 100% | ✅ **CORRIGIDO** (3 galhos linkam folhas) |
| **CR2#3** | Árvore promete "pickings" em 2.9, mas só quants/MLs implementados | 100% | ✅ **CORRIGIDO** (README + subagente refletem escopo real) |
| **CR3#1** | "Skills — Inventario Completo (41 invocaveis)" desatualizado | 100% | ✅ **CORRIGIDO** (41 → 44) |
| **CR3#3** | VALIDACAO.md skill 9 listava C7-C10 como "próximos passos" | 100% | ✅ **CORRIGIDO** (seção "Status C7-C10 concluídos") |
| **CR4#3** | Link `[[arquitetura-orquestrador-odoo]]` (dashes) vs filename underscores | 90% | ✅ **CORRIGIDO** (padronizado underscores) |
| **CR4#5** | "quando houver demanda" contradiz `feedback_incompletude_quebra_regras` | 90% | ✅ **CORRIGIDO** (justificativa explícita ou status atualizado em ambas VALIDACAO) |

**9 issues prioritárias corrigidas.** Skill 2.4 ganhou 1 modo CLI novo (`--zerar-residual`) e skill 9 ganhou classificação `quant_orfao_reserva`.

### Pendências cosméticas restantes (8 issues — baixa prioridade)

| # | Achado | Mitigação proposta |
|---|---|---|
| CR1#1 | G002 atribuído à `quant.py` quando pertence à CLI/StockLotService | Mover nota no SKILL.md para gotcha-da-CLI |
| CR1#2 | CLI `ajustar_quant.py:81` ignora `--criar-se-faltar` com `--valor-absoluto` ou Δ≤0 sem erro | Adicionar `ap.error(...)` explícito |
| CR1#3 | Status `FALHA_CRIAR_LOTE` listado mas service nunca emite (CLI sem try/except) | Envolver `criar_se_nao_existe` em try/except retornando o status |
| CR1#6 | `pares_cod_empresa` e `auditar_pares` da skill 9 não expostos na CLI | Adicionar `--pares-cod-empresa` à CLI |
| CR2#2 | Premissa "verificar reserved=0 pré-cirurgia" não está formal na fluxo 2.4 | Adicionar item 7 às Premissas |
| CR3#2 | MAPA_SCRIPTS diz "7-param", código real tem 9 params em `listar_quants` | Alinhar contagem |
| CR4#1 | Memória `feedback_incompletude` cita "84+118" sem ponteiro para query | Adicionar referência à query inline |
| CR4#4 | VALIDACAO.md skill 1: "Adicionar ao [[gotcha-resetar...]]" redundante (já foi feito) | Remover instrução |

**Decisão:** pendências cosméticas registradas; tratar conforme próxima sessão tocar nos arquivos.

---

## 3. Pre-mortem rigoroso

### Riscos operacionais (impacto: operadores físicos / Odoo de produção)

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Operador tenta validar `FB/INT/07950` ou `FB/OUT/01053` (cancelados)** | Baixa | Baixo (Odoo aceita; picking sumiu do radar) | Sistema sinaliza `state=cancel`; operador re-prioriza |
| **Operador tenta validar pickings com cirurgia (`EMB/11673`, `INT/08022`, `INT/08030`, `OUT/01046`) com MLs reduzidas** | Média | Médio (vai consumir menos do que esperado) | Já documentado em VALIDACAO skill 2.4; operadores devem ser avisados (FORA do escopo desta sessão) |
| **`104000037 CICLAMATO DE SODIO FB`: 33.73 un over-reduzidas** | Realizada | Médio (saldo contábil errado) | Reversível por ajuste positivo +33.73 un em qq lote válido; **AÇÃO FUTURA** |
| **`104000039 AROMA NATURAL - ALHO FB` em Pré-Produção/Linha Manual: quant órfão `qty=0+reserved=-0.6`** | Realizada | Baixo (saldo pequeno, mas estado fantasma) | Aplicar `zerar_reserved_residual` via skill 2.4 CLI; **AÇÃO FUTURA** |
| **Saldo fantasma em Indisponivel (45 pares)** | Realizada | Variável (operadores podem tentar usar) | Documentado em [[estoque-fantasma-migracao-indisponivel]]; operação viva — usuário decide quando consolidar |

### Riscos técnicos (impacto: código / Odoo / sessões futuras)

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Próxima sessão usa `--resetar-reserva` sem chamar `zerar_reserved_residual` após** | Alta | Alto (estado fantasma negativo) | Documentado em [[gotcha_resetar_reserva_orfao_negativo]] + fluxo 2.4 + SKILL.md skill 2.4 + memória |
| **Próxima sessão zera quant via `Δ=-qty_atual` em retomada SEM cruzar pedido original** | ~~Média~~ MITIGADA 2026-05-24 | ~~Alto~~ Médio (guard bloqueia ou auto-corrige) | **Guard `delta_esperado` implementado no service `quant.py` 2026-05-24** (29 pytest verdes). Modo bloqueio (default): aborta com FALHA_DELTA_DIVERGENTE. Modo auto-correção (`--corrigir-para-esperado`): aplica delta_esperado. Doc em SKILL.md `ajustando-quant-odoo` + memória [[gotcha-resetar-reserva-orfao-negativo]] §"Guard implementado". |
| **`stock.move._action_cancel` é PRIVADO XML-RPC** | Realizada | (já mitigado) | Workaround `unlink ML + write product_uom_qty` codificado no service + documentado em G025 |
| **Scripts em `_validados/` rodando fora de contexto (parents[4] errado)** | Baixa | Médio (ImportError) | sys.path corrigido em cada um + header de "ARQUIVADO" + memória |
| **Skill 9 promete consultar pickings mas só quants/MLs estão implementados** | Média | Baixo (agente entrega query parcial) | Documentado em fluxo 2.9 e README; átomo `listar_pickings` previsto |
| **Worktree `feat/estoque-odoo` sem `.env`** | Alta (cada sessão nova) | Baixo (Odoo falha em autenticar) | `set -a; . <(grep -E '^ODOO_' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a` documentado no ROADMAP HANDOFF |

### Riscos de processo (impacto: continuidade do plano de migração)

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Merge conflict ao trazer `feat/estoque-odoo` → `main`** (Rafael commita em paralelo) | Alta | Médio (rebase manual) | Branch ainda não commitada; quando o usuário aprovar, fazer rebase incremental sobre main atualizado |
| **Próxima sessão sem contexto da arquitetura `fluxos>>skills`** | Alta | Alto (criar skills/scripts ad-hoc) | ROADMAP HANDOFF + CLAUDE.md §1-§12 + memória [[arquitetura_orquestrador_odoo]] + [[feedback-skills-demanda-driven]] |
| **Próxima sessão pula etapas C7-C10** | Média | Médio (skills incompletas) | Memória [[feedback_incompletude_quebra_regras]] |
| **Esquecer de invocar code-reviewers ao final da sessão** | Média | Médio (bugs latentes) | Adicionar à memória de processo (NÃO criada ainda) |
| **Perda do `/tmp/auditoria_*.json` antes de documentar** | Alta (sessão fecha) | Baixo (logs em auditoria/ persistem) | Logs `log_2.{1,4}_*.json` em `scripts/inventario_2026_05/auditoria/` (gitversionados quando commitados) |

---

## 4. O que está OBJETIVAMENTE validado

### Code (skill 1, 2.4, 9)
- ✅ Service `quant.py`: 22 testes pytest verdes (sessão anterior)
- ✅ Service `reserva.py`: 3 átomos implementados, 1 caso real validado (6 pickings + 15 quants)
- ✅ Service `consulta_quant.py`: 2 átomos, dogfooded com 104 pares (auditar_pares=104 ✓)
- ✅ 3 CLIs com `--help` funcionando
- ✅ 4 logs JSON em `scripts/inventario_2026_05/auditoria/log_2.1_*.json` + 2 em `log_2.4_*.json`
- ✅ 100 chamadas write efetivadas no Odoo (84 sucessoa skill 1 + 1 NOOP + 15 retomadas + 4 cirurgia/cancel skill 2.4 + 15 zerar_residual)

### Docs cross-arquivo
- ✅ Subagente `gestor-estoque-odoo.md` lista 5 skills + árvore decisão atualizada com galhos `[folha 2.1/2.4/2.9]`
- ✅ ROUTING_SKILLS.md: Skills Odoo (12) + 44 invocaveis total
- ✅ tool_skill_mapper.py: 3 entradas Odoo (Write/Read)
- ✅ CLAUDE.md raiz: tabela SUBAGENTES expandida com status 3 skills
- ✅ MAPA_SCRIPTS.md: 2 seções novas (reserva.py, consulta_quant.py) + 8 scripts SUPERADOS
- ✅ ROADMAP_SKILLS.md: SKILL 1 ✅ MATURADA, SKILL 3 🟡, SKILL 9 🟡 ANCILLARY, HANDOFF atualizado
- ✅ 3 folhas de fluxo: 2.1, 2.4, 2.9
- ✅ 3 VALIDACAO.md: 1 + 2.4 + 9 (com status C7-C10)
- ✅ 3 memórias novas: gotcha_resetar_reserva, feedback_skills_demanda_driven, feedback_incompletude_quebra_regras

### Operação no Odoo
- ✅ 15 quants ajustados (zerados via `--resetar-reserva` + `zerar_reserved_residual` em sequência)
- ✅ 4 pickings com cirurgia bem-sucedida (`EMB/11673`, `INT/08022`, `INT/08030`, `OUT/01046`)
- ✅ 2 pickings cancelados (`INT/07950`, `OUT/01053`)
- ✅ 0 quants com `reserved < 0` em FB/Estoque (limpos pelo `zerar_reserved_residual`)
- ⚠️ 1 quant órfão pré-existente identificado (`104000039 FB/Pré-Produção/Linha Manual`)
- ⚠️ 1 over-reduction (`104000037`, 33.73 un excedentes) — reversível

---

## 5. Pendências para próxima sessão

### Bloqueantes operacionais — ✅ RESOLVIDAS em 2026-05-24 00:00 UTC (sessão de cleanup)

1. ✅ **Reversão over-reduction `104000037 CICLAMATO DE SODIO FB`** — ajuste **+33.7319 un** aplicado no quant **229937** (lote `MI074-177/25`, FB/Estoque, `lot_id=57545`): `qty=5.0136 → 38.7455`, `reserved=0`. Lote escolhido pelo usuário (recusou P-15/05 e MIGRACAO sem cedilha). Verificado direto no Odoo via `search_read stock.quant`. Log: [`auditoria/log_2.1_reversao_ciclamato_20260524_000000.json`](../../scripts/inventario_2026_05/auditoria/log_2.1_reversao_ciclamato_20260524_000000.json).
2. ✅ **Quant órfão `104000039 AROMA NATURAL - ALHO FB/Pré-Produção/Linha Manual`** — quant **260657** zerado via `operar_reserva.py --zerar-residual --quant-ids 260657 --confirmar`: `reserved=-0.6 → 0` (qty já era 0). Verificado direto no Odoo. Log: [`auditoria/log_2.4_zerar_residual_orfao_aroma_20260524_000001.json`](../../scripts/inventario_2026_05/auditoria/log_2.4_zerar_residual_orfao_aroma_20260524_000001.json).
3. ✅ **Comunicado dos 6 pickings tocados** gerado em [`/tmp/comunicado_pickings_20260524.md`](file:///tmp/comunicado_pickings_20260524.md) e entregue ao usuário. Detalha 4 cirurgias (FB/FB/EMB/11673, FB/INT/08022, FB/INT/08030, FB/OUT/01046) + 2 cancelamentos (FB/INT/07950, FB/OUT/01053) com produtos afetados (verificados direto no Odoo via `search_read stock.move`).

### Não-bloqueantes (próxima sessão)
4. **Skill 2** (`transferindo-interno-odoo`): próxima na ordem bottom-up; C1 mineração de 16 scripts (`transfer.py` MAPA_SCRIPTS).
5. **8 issues cosméticas** do code-review (lista §2 acima).

### Observação operacional (lição reforçada)
Ao escolher lote para ajuste positivo de reversão, o usuário **recusou** as 2 primeiras propostas (P-15/05 e MIGRACAO sem cedilha) e preferiu **lote real menor** (MI074-177/25, qty pré 5.0136 → pós 38.7455). Lição: usuário prefere ajuste em lote real produtivo ao invés de "lote consolidador" do inventário, mesmo quando o saldo final fica grande relativo ao saldo prévio. Atualizar memória [[feedback_ajuste_positivo_criar_saldo]] com este detalhe (atualmente a memória sugere P-15/05 como default).

---

## 6. Sessão 2026-05-24: Guard `delta_esperado` + validação cancelamentos (gaps 1+2 fechados)

### Gap 1 — Causa do over-reduction (mitigada)
Implementado guard no service `app/odoo/estoque/scripts/quant.py` com 2 novos parâmetros:
- `delta_esperado` (Optional[float]): pedido original de ajuste. Quando informado, valida `|ajuste_aplicado − delta_esperado| <= tolerancia_delta`.
- `tolerancia_delta` (float, default 0.1): tolerância absoluta.
- `corrigir_para_esperado` (bool, default False): quando divergente, AUTO-CORRIGE aplicando `delta_esperado` em vez de bloquear. Status passa a `EXECUTADO_AUTO_CORRIGIDO`.

CLI `ajustar_quant.py` expõe via `--delta-esperado`, `--tolerancia-delta`, `--corrigir-para-esperado`. Smoke test com quant 229937: dry-run mostrou `divergencia=40.7319 > tolerancia=0.1 → FALHA_DELTA_DIVERGENTE` no modo bloqueio, e `qty_apos=31.7455 ajuste_aplicado=-7.0 status=DRY_RUN_OK auto_correcao_aplicada=true` no modo auto-corrigir.

7 testes pytest novos (29 total no service, todos passam):
- `test_delta_esperado_bate_executa`
- `test_delta_esperado_diverge_aborta`
- `test_delta_esperado_dentro_tolerancia_passa`
- `test_sem_delta_esperado_mantem_comportamento`
- `test_delta_esperado_dry_run_tambem_aborta`
- `test_corrigir_para_esperado_aplica_delta_esperado`
- `test_corrigir_para_esperado_sem_divergencia_nao_marca_auto`

### Gap 2 — Cancelamentos OUT/01053 e INT/07950 (validados)
Consultado `stock.move.move_dest_ids` para os 6 moves cancelados — **TODOS retornaram lista vazia (`[]`)**:

```
move 1161870 state=cancel prod=105000083 move_dest_ids=[]  move_orig_ids=[]
move 1161871 state=cancel prod=105000084 move_dest_ids=[]  move_orig_ids=[]
move 1161872 state=cancel prod=105000075 move_dest_ids=[]  move_orig_ids=[]
move 1161873 state=cancel prod=105000076 move_dest_ids=[]  move_orig_ids=[]
move 1161874 state=cancel prod=105000077 move_dest_ids=[]  move_orig_ids=[]
move 1150537 state=cancel prod=4856125  move_dest_ids=[]  move_orig_ids=[]
```

**Conclusão:** Os cancelamentos são self-contained — NÃO há picking espelho em LF aguardando entrada que ficou pendurada. Nenhuma ação necessária.

### Saldos verificados pós-cancelamento (XML-RPC ao vivo):
- INT/07950 (MAIONESE VERDE `4856125`): 53.4170 un em !=Indisp + 0 MOs ativas esperando consumo.
- OUT/01053 (5 produtos `105000083/084/075/076/077`): todos com saldo suficiente em !=Indisp.

---

## 7. Sessão 2026-05-24 v2: Skill 2 `transferindo-interno-odoo` maturando (C1-C10)

> Tarde de 2026-05-24. Iniciada após o cleanup matinal (§6). Foco: maturação da Skill 2 — átomo C2 de transferência interna intra-empresa no Odoo.

### Rebase incremental main → worktree (ANTES de iniciar)

- **Status**: 5 commits trazidos por fast-forward (HEAD: 8d755573 → b4f7b24c). 0 conflitos no `git stash pop` (trabalho da sessão anterior preservado).
- **Reconciliação de docs**: 2 arquivos `docs/inventario-2026-05/consolidacao/{ROADMAP_SKILLS,ARQUITETURA_ORQUESTRADOR_ODOO}.md` (criados em paralelo pelo Rafael em main, versões antigas) foram convertidos em **ponteiros** para `app/odoo/estoque/{ROADMAP_SKILLS,CLAUDE}.md` (fonte única de verdade). Histórico git preservado; links externos antigos continuam funcionando.
- **4 ad-hocs novos do main** integrados em `scripts/inventario_2026_05/` (operação viva): `ajuste_quant_cd.py` (usa Skill 1 — adoção orgânica), `consolidar_lote_104000015_sal_fb.py` (caso real Skill 2 — minerado), `corrigir_fantasma_104000015_sal_fb.py` (skill 1 + documenta bug `action_apply_inventory infla negativo`), `desfazer_ajustes_indevidos_lf.py` (skill 1 com `valor_absoluto=0`).

### Estrutura final do service `app/odoo/estoque/scripts/transfer.py`

- **Movido via `git mv`** de `app/odoo/services/stock_internal_transfer_service.py` → `app/odoo/estoque/scripts/transfer.py`. Shim preservado em `app/odoo/services/stock_internal_transfer_service.py` (re-export, mesma assinatura — 5+ consumidores ativos intactos).
- **Constantes adicionadas:** `TOL_ARREDONDAMENTO=0.001`, `LOTES_MIGRACAO_VARIANTES=['MIGRAÇÃO', 'MIGRACAO', 'MIGRAÇAO']`, `LOTE_MIGRACAO_CANONICO='MIGRAÇÃO'`. Função `is_migracao(nome)` utility.
- **Helpers privados:** `_lotes_migracao_ids` (G021 filter company_id), `_melhor_lote_migracao_na_loc` (G022 escolhe maior saldo + fallback primeiro), `_quant_svc` (lazy-init cache do StockQuantAdjustmentService).
- **Helpers públicos:** `resolver_lote_origem` (3 retornos: lot_id literal, MIGRACAO consolidado, ou None para P-15/05 proxy), `resolver_lote_destino` (cria canônico MIGRAÇÃO se nenhum existe).
- **Métodos v1 preservados** (compat): `transferir_entre_lotes`, `transferir_quantidade_para_lote` (12 testes originais verdes).
- **Métodos v2 novos** (delegam a `ajustar_quant` propagando `delta_esperado=±qty` por default):
  - `transferir_entre_lotes_v2(product_id, company_id, location_id, qty, lot_id_origem, lot_id_destino, resetar_reserva_origem=False, tolerancia_delta=0.001, dry_run=False)`
  - `transferir_entre_locations(product_id, company_id, lot_id, qty, location_id_origem, location_id_destino, resetar_reserva_origem=False, tolerancia_delta=0.001, dry_run=False)`
  - `transferir_quantidade_para_lote_v2(...)` — wrapper que resolve destino e chama v2 (ValueError se destino sem lote).
- **Status retornos**: `EXECUTADO` | `DRY_RUN_OK` | `FALHA_REDUCAO` (origem falhou, aumento NÃO chamado) | `FALHA_AUMENTO` (origem reduziu mas aumento falhou — operação parcial gravada).

### Pytest baseline
- `tests/odoo/services/test_stock_internal_transfer_service.py`: **33 verdes** (14 originais preservados + 19 novos cobrindo helpers + v2 + gotchas).
- `tests/odoo/services/test_stock_quant_adjustment_service.py`: **30 verdes** (Skill 1 preservada).
- `tests/odoo/services/test_stock_lot_service.py`: **19 verdes** (dependência preservada).
- **Total: 82 verdes**.

### Skill `.claude/skills/transferindo-interno-odoo/`
- `SKILL.md` (~270 linhas): contrato + receitas 6 casos + armadilhas 10 itens + composição em fluxos + validação por reprodução.
- `scripts/transferir.py` (CLI): 2 modos exclusivos (A `--lote-origem/--lote-destino` | B `--loc-origem/--loc-destino [--lote]`), default `--dry-run`, exit codes `0/1/2/4`.

### Folha de fluxo `app/odoo/estoque/fluxos/2.2-realocar-saldo.md`
8 sub-casos identificados na mineração (2.2.a até 2.2.h) cobertos: lote↔lote mesma loc; local↔local mesmo lote; lote→MIGRAÇÃO consolidador; MIGRAÇÃO→lote real; net-zero planilha multi-empresa; wildcard De-Local; multi-grafia consolidação; unreserve→transfer→reassign (cross-skill).

### Validação C6 (3 casos dry-run vs Odoo PROD ao vivo)

| Caso | Modo | Ground-truth | Resultado | Interpretação |
|---|---|---|---|---|
| `cod 104000015 --empresa FB --qty 35 --lote-origem MIGRAÇÃO --lote-destino 'MI 027-098/26'` | A | 10_emergenciais E01 executado 18/05 | FALHA_REDUCAO (MIGRAÇÃO consumida) | Coerente com histórico ✓ |
| `cod 210030325 --empresa FB --qty 66532 --lote-origem MIGRACAO --lote-destino MIGRAÇÃO` | A | padronizar_migracao executado 18/05 | FALHA_LOTE 'origem==destino' | Limitação CLI documentada (precisa `--lot-id`) |
| `cod 104000015 --empresa FB --qty 100 --lote 'MI 027-098/26' --loc-origem 8 --loc-destino 31088` | B | mover_migracao pattern | DRY_RUN_OK plano completo em 47ms | Cenário felizmente reproduzível ✓ |

Log: `/tmp/log_skill2_C6_validacao_dry_run.json`.

### Cross-refs C7 (4 arquivos atualizados)

- `.claude/agents/gestor-estoque-odoo.md`: skills + árvore 2.2 com link [folha 2.2]
- `.claude/references/ROUTING_SKILLS.md`: 45 invocaveis (1 nova linha "transferencia intra-empresa específica" + ampliação da geral)
- `app/agente/services/tool_skill_mapper.py`: `'transferindo-interno-odoo': 'Estoque Odoo (Write)'`
- `CLAUDE.md` raiz: descrição do `gestor-estoque-odoo` ampliada

### C9-C10 Arquivamento e MAPA_SCRIPTS/ROADMAP

- **2 scripts SUPERADOS** movidos para `scripts/inventario_2026_05/_validados/transferindo-interno-odoo/`:
  - `10_executar_emergenciais_fb.py` (10 casos hardcoded MIGRAÇÃO→lote)
  - `padronizar_migracao.py` (1 caso hardcoded com limitação documentada)
  - Ambos com sys.path corrigido (`parents[2]→parents[4]`) e header de arquivado.
- **16+ scripts permanecem VIVOS** (orquestradores de planilha + cross-skill + COM-BUG) — aguardam fluxos compostos ou refator.
- VALIDACAO.md detalhado por script + lista de limitações + próximas evoluções.
- MAPA_SCRIPTS.md atualizado (status SUPERADO/AO-CAPINAR-VIVO).
- ROADMAP_SKILLS.md atualizado (Skill 2 status 🟡 + HANDOFF v2 + contagem global + próximos passos + ordem de execução).

### Limitação conhecida (documentada para futuro)

**`padronizar_migracao` case**: a CLI da Skill 2 aceita só nomes de lote (`--lote-origem`/`--lote-destino`). Para consolidar 2 grafias literais ESPECÍFICAS de MIGRAÇÃO (sem cedilha → com cedilha), ambas reconhecidas como variantes pelo `is_migracao()`, a CLI **não funciona** (detecta `lote origem == destino`). Workaround atual: chamar `StockInternalTransferService.transferir_entre_lotes_v2(lot_id_origem=X, lot_id_destino=Y)` diretamente em Python, ou usar o script-fonte arquivado (museum vivo). **Próxima evolução**: adicionar args `--lot-id-origem`/`--lot-id-destino` quando demanda real surgir.

### Status global pós-2026-05-24 v2

| Skill | Status | Notas |
|---|---|---|
| 1 `ajustando-quant-odoo` | ✅ MATURADA | 30 pytest, 5 scripts SUPERADOS, 100 ajustes em PROD 23/05 |
| 2 `transferindo-interno-odoo` | 🟡 mín viável (NOVA) | 33 pytest, 2 scripts SUPERADOS, 0 --confirmar em PROD |
| 2.4 `operando-reservas-odoo` | 🟡 mín viável | 3 scripts SUPERADOS, 6 pickings + 15 quants validados 23/05 |
| 9 `consultando-quant-odoo` (READ) | 🟡 mín viável | Auditoria pós-WRITE validada 23/05 |
| 4-8 (MO/picking/preetapa/escriturar/faturar) | ⬜ | Próximas ondas |

**Conclusão da sessão**: Skill 2 entrou no catálogo como mín viável. O ÁTOMO está pronto (35 testes incluindo 2 FALHA_AUMENTO, 4 métodos, helpers MIGRACAO, propagação delta_esperado). A ORQUESTRAÇÃO de planilha (D010/D012/D013) permanece via scripts ad-hoc VIVOS até demanda real justificar fluxos compostos.

### Fechamento (correções pós code-review da sessão)

3 erros descobertos pelos code-reviewers e CORRIGIDOS ainda na sessão (não viraram pendência):

1. **CR1#1 (CLI `--lote-origem ''` bloqueado)**: corrigido — `is not None` substituiu `bool(truthy)` em `.claude/skills/transferindo-interno-odoo/scripts/transferir.py`. Smoke test: `--lote-origem '' --lote-destino MIGRAÇÃO` agora aceita proxy P-15/05.
2. **CR1#2 (`FALHA_AUMENTO` `qty_transferida=qty` em estado parcial)**: corrigido — `qty_transferida=0.0` + `qty_reduzida_origem` novo campo para auditoria/rollback. 2 testes novos cobrindo o cenário.
3. **CR2#1 (`CLAUDE.md §6` mostrava ⬜)**: corrigido — `🟡 mín viável (33 pytest verdes; 2 scripts SUPERADOS 2026-05-24; orquestradores de planilha permanecem VIVOS)`.

E 3 erros descobertos pelo USUÁRIO Rafael na revisão final:

4. **CR2#3 (fork em ROUTING_SKILLS viola fluxos>>skills)**: corrigido — linha extra "via gestor-estoque-odoo OU direto" REMOVIDA; triggers consolidados na linha geral "ESTOQUE ODOO (WRITE)" — ROTEAMENTO SEMPRE via subagente.
5. **Gap doc — `app/odoo/CLAUDE.md`**: shim mark adicionada (`stock_internal_transfer_service.py # SHIM 2026-05-24`); nova seção "Subpacote estoque/" com tabela de skills+status criada.
6. **Gap doc — findings do subagente Explore**: persistidos em `docs/inventario-2026-05/consolidacao/MINERACAO_SKILL2_2026_05_24.md` (versionado no git, sobrevive ao /clear).

**Pytest final pós-correções: 86 verdes** (37 transfer + 30 quant + 19 lot) — após 3 últimas correções:

7. **CR1#3 (zero-saldo fallback untested)**: corrigido — 2 testes novos cobrindo (a) fallback `lids[0]` quando nenhuma variante tem saldo na loc; (b) boundary case onde NENHUMA variante existe → `(None, [])`.
8. **CR1#4 (assertion frágil `write.call_count == 3`)**: corrigido — assertion comportamental `'reset_reserva' in res['reducao_origem']['acao']` (resistente a otimizações futuras em `ajustar_quant`).
9. **CR2#2 (dual-ownership 3 scripts em MAPA_SCRIPTS)**: corrigido — `ajuste_fb_cd_indisponivel`, `transferir_local_pasta22`, `transferir_indisp_para_estoque_p15_cd` movidos para seção `scripts/transfer.py` (orquestradores que compõem Skill 2 modo B/A wildcard); nota arquitetural explicativa adicionada na seção `quant.py + MIGRAÇÃO↔Indisponível`. Apenas 2 scripts permanecem lá: `mover_migracao_para_indisponivel` (CSV de pulados — lógica adicional além de transferência) e `executar_fluxo_b_vivas` (fluxo composto cross-skill cancel+return+transfer).

**Skill 2 fechada com 0 pendências não-bloqueantes.** Próxima sessão pode focar Skill 4/5 (MO/picking) ou fluxos compostos da Skill 2 (D010/D012/D013) sem dívida arquitetural pendente.

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

> **Nota histórica:** esta tabela reflete o estado da sessão v2 (2026-05-24). Estado atual v5 (2026-05-24): Skill 4 (MO) e Skill 5 (picking) viraram 🟡 mín viável; restam Skill 6 (pre-etapa), 7 (escriturar), 8 (faturar) — esta última DESBLOQUEADA pela ONDA 0.4 fechada em v3. Ver §10 para sessão v5 completa.

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

---

## 8. Sessão 2026-05-24 v3: Skill 5 `operando-picking-odoo` maturando + FECHA ONDA 0.4 (G019/G020)

> Sessão da tarde 2026-05-24 v3. Iniciada após v2 (Skill 2). Foco: maturação da Skill 5 — átomo C2 de operações de picking + descoberta arquitetural crítica.

### Achado crítico — premissa do prompt desatualizada (parcialmente)

O prompt da sessão afirmava que **G019/G020/G011/G023 eram BUGS ABERTOS** bloqueantes da Skill 8 (faturando-odoo). Investigação contra código revelou:

| Gotcha | Doc status (antes) | Código real | Pytest cobrindo |
|---|---|---|---|
| G019 (validar engole 'cannot marshal None') | PROPOSTO | ✅ FIX em `validar()` (linhas 407-481) | 5 testes pré-existentes |
| G020 (liberar_faturamento sem pré-cond state=done) | PROPOSTO | ✅ FIX em `liberar_faturamento()` (linhas 500-525) | 3 testes pré-existentes |
| G011 (preencher_qty_done faltando) | "corrigido pipeline" | ✅ Helper existe (linhas 295-337) | 2 testes pré-existentes |
| G023 (consolidar_move_lines over-reservation) | ✅ IMPLEMENTADO | ✅ Método existe (linhas 144-293) | 0 testes (gap descoberto) |

**Discrepância resolvida**: docs/CLAUDE/ROADMAP atualizados para refletir que ONDA 0.4 estava FECHADA NO CÓDIGO desde 2026-05-18, faltando só:
- Pytest cobrindo G023 (8 testes novos adicionados)
- Pytest cobrindo `ajustar_qty_done_pelo_disponivel` (6 testes novos)
- Pytest cobrindo `validar(linhas_esperadas=)` G023 inline (2 testes novos)
- Capinagem `services/ → estoque/scripts/`
- Atualização dos docs de gotcha (PROPOSTO → IMPLEMENTADO)

### Estrutura final dos artefatos

- **Service `app/odoo/estoque/scripts/picking.py`**: capinado de `services/`; método NOVO `devolver()` adicionado (derivado de `fat_lf_cleanup.reverter_picking` PROD 2026-05-20). Shim preservado em `services/stock_picking_service.py` (6 consumidores ativos intactos).
- **Pytest baseline**: 19 originais + 16 novos baseline (G023/ajustar_qty_done/validar-com-linhas) + 7 cobrindo `devolver` = **42 testes verdes**.
- **Total tests baseline 2026-05-24 v3**: 30 quant + 37 transfer + 19 lot + 42 picking = **128 verdes**.
- **Skill `.claude/skills/operando-picking-odoo/`**: SKILL.md (~280 linhas) com 3 átomos + 3 fluxos compostos (2.5.a/b/c) + armadilhas; `scripts/operar_picking.py` (CLI 3 modos `--modo cancelar/validar/devolver`, `--dry-run` default).
- **Folha de fluxo `app/odoo/estoque/fluxos/2.5-cancelar-validar-devolver-picking.md`**: 3 sub-casos + cross-skill com Skill 2.4 documentado.
- **Validação C6 dry-run vs Odoo PROD**: 6 casos 100% bate (pid 321147 assigned cancelar/devolver; 321146 assigned validar; 321150 done devolver/cancelar; 321107 cancel NOOP). Log em `/tmp/log_skill5_C6_validacao_dry_run.json`.
- **Cross-refs C7**: subagente + ROUTING_SKILLS (46 invocaveis + 14 Skills Odoo) + tool_skill_mapper + CLAUDE.md raiz + app/odoo/CLAUDE.md.
- **Arquivamento C9**: `16_cancelar_pickings_fantasmas` movido para `_validados/operando-picking-odoo/` (sys.path corrigido parents[2]→parents[4]; header de arquivado) + VALIDACAO.md detalhada.
- **Docs G019/G020 atualizadas** (PROPOSTO → IMPLEMENTADO; Ref paths atualizados de `services/` para `estoque/scripts/`).
- **ROADMAP ONDA 0.4** marcada `[X] FECHADO 2026-05-24 v3`.

### Code-review consolidado (2 reviewers paralelos)

**Reviewer #1 (code)** → 4 HIGH findings, **TODOS CORRIGIDOS NA MESMA SESSÃO**:

1. **CR1#1 (picking.py:560)**: `create_returns` pode retornar `[8888]` (lista 1-id em algumas versões Odoo) — guard original aceitava só `dict` ou `int`. CORRIGIDO: aceita os 3 shapes; guard explícito contra `bool` (subclasse de `int` em Python).
2. **CR1#2 (test_devolver_state_final_nao_done_raises)**: `search_read.side_effect` tinha `[[], []]` (2º elemento `[]` causava 0 MLs, branch incompleto). CORRIGIDO: 2º elemento agora `[{id, qty, qty_done}]`, plus assertion `write.assert_any_call qty_done=5.0`.
3. **CR1#3 (operar_picking.py:282-283)**: double-read do state em `devolver_single` (svc.devolver já garante state=done). CORRIGIDO: usa `state_devolucao='done'` deterministicamente (lê só `name` se necessário).
4. **CR1#4 (operar_picking.py TIMEZONE)**: `datetime.now()` viola REGRAS_TIMEZONE.md (Brasil naive). CORRIGIDO: `from app.utils.timezone import agora_brasil_naive`.

**Reviewer #2 (docs)** → 5 HIGH + 2 MED findings, **TODOS CORRIGIDOS**:

5. **CR2#1 (CLAUDE.md:3)**: header "Atualizado 2026-05-22" mas conteúdo é v3. CORRIGIDO: "2026-05-24" + nota ONDA 0.4 ✅.
6. **CR2#3 (G019.md Ref)**: cita `services/stock_picking_service.py` (path antigo). CORRIGIDO: `estoque/scripts/picking.py:407-481`.
7. **CR2#4 (G020.md Ref)**: idem. CORRIGIDO: `estoque/scripts/picking.py:500-525`.
8. **CR2#5 (MAPA_SCRIPTS fat_lf_cleanup)**: status "SUPERADO" inconsistente com VALIDACAO.md ("permanece VIVO"). CORRIGIDO: status `AO-CAPINAR-VIVO` + nota explicativa.
9. **CR2#6 (gestor-estoque-odoo.md:19)**: warning "ESQUELETO" desatualizado (sugeria parar para skills 1/2/3/5/9 que estão LIVES). CORRIGIDO: lista explícita de LIVES vs NÃO INICIADAS.
10. **CR2#7 (SKILL.md frontmatter)**: "depende de invariante G019/G020 já fechada neste service" — frasing ambígua. CORRIGIDO: "ONDA 0.4 ✅ fechada 2026-05-24 v3, destrava implementação da Skill 8".

**Pendência cosmética** (CR2#2 LOW — subtotal Fase 0 35 vs total 42): mantida no SKILL.md como está (Fase 0 = 35 verdes pós-baseline; total = 42 com `devolver`). Não bloqueia.

### Pytest final pós-correções

**128 verdes** (30 quant + 37 transfer + 19 lot + 42 picking) em 2.86s. Mantém baseline integral pós-9 correções HIGH.

### Status global da skill 5

🟡 mín viável (3 átomos: `cancelar`, `validar` com G019/G020 invariante, `devolver` NOVO com idempotência via `origin ilike`). 0 execuções `--confirmar` em PROD nesta sessão (demanda-driven). **FECHA ONDA 0.4** — Skill 8 `faturando-odoo` agora pode confiar no invariante de `svc.validar()`.

### Próximos passos (escolha em sessão futura)

1. **Skill 4 `operando-mo-odoo`** — próxima na ordem bottom-up (única WRITE intra-estoque restante).
2. **Skill 8 `faturando-odoo`** — **AGORA DESBLOQUEADA** pela ONDA 0.4 fechada; é a skill MACRO (NF→SEFAZ) — cuidado especial.
3. **Skill 7 `escriturando-odoo`** — entrada IC + DFe; depende de contrato estável de transfer + picking (ambos ✅).
4. **Fluxos compostos** (Skill 2 D010/D012/D013, Skill 5.a com batch fantasma novo).

---

## 9. Sessão 2026-05-24 v4: Skill 2 MODO C `transferir_para_indisponivel` estreia em PROD + incidente G031 + fix

> Após sessão v3 (Skill 5). Foco: demanda real do Rafael de "Transfere esses 16 produtos pra Indisponivel" virou átomo novo + 1º incidente arquitetural real da Skill 2.

### 9.1 Cronologia

| # | Evento | Resultado |
|---|---|---|
| 1 | Achado inicial: pulei `resolver_empresa`/constants | Reconheci e corrigi caminho |
| 2 | Decisões coletadas (consolidar MIGRAÇÃO, 4529301 NOOP, 104000033 -0,028) | 3 decisões aplicadas |
| 3 | C2 service `transferir_para_indisponivel` v1 (composição A+B encadeada) | Bug: dry-run falha (Passo 2 antes do Passo 1 commitar) |
| 4 | Refactor para 1 passo direto (`ajustar_quant` 2x) | Dry-run 14/14 OK |
| 5 | C3-C5 CLI modo C + 12 testes pytest v1 | 140 verdes |
| 6 | `--confirmar` v1 em PROD | ⚠️ **16/16 FALHA_AUMENTO** ("lote MIGRAÇÃO vinculado a outro produto") |
| 7 | Diagnóstico: `LOTES_MIGRACAO_POR_COMPANY[1]=30482` é `lot_id` de UM produto; usar como FK universal falha | Causa raiz isolada (G031) |
| 8 | Rollback via Skill 1 `ajustar_quant +qty criar_se_faltar=True` em 16 lotes origem | ✅ **16/16 EXECUTADO**; 4.319,4019 un restauradas em ~10s |
| 9 | Insight Rafael: "lote é por produto, usar busca tipo ilike/like igual Odoo" | Confirmou direção do fix |
| 10 | Fix v2: aceita `nome_lote_destino='MIGRAÇÃO'` (str), resolve POR PRODUTO via `lot_svc.criar_se_nao_existe` em real; `buscar_por_nome` em dry-run | Service refatorado |
| 11 | 3 testes pytest novos cobrindo o fix (15 total modo C) | 143 verdes |
| 12 | Constants `LOTES_MIGRACAO_POR_COMPANY` documentadas como HISTÓRICO/EXEMPLO + nova `NOME_LOTE_MIGRACAO_POR_COMPANY` | Locations.py atualizado |
| 13 | Dry-run pós-fix valida resolução POR PRODUTO (lot_id_destino=57932 ≠ 30482) | OK |
| 14 | `--confirmar` v2 em PROD | ✅ **16/16 EXECUTADO** em 23s; 4.319,4019 un movidas |
| 15 | Verificação direta Odoo: 16/16 origem zerada + MIGRAÇÃO somando exato | Estado validado |
| 16 | Docs atualizados (SKILL.md + fluxo 2.2 + G031 + ROADMAP + memória) | C7-C10 fechado |

### 9.2 Métricas finais

- **143 pytest verdes** (30 quant + 52 transfer + 19 lot + 42 picking). Transfer subiu de 37→52 com 15 testes novos modo C.
- **6 dry-run PROD validados** (3 modo C iniciais + 3 negativos).
- **2 `--confirmar` PROD em sequência** (1ª falhou, 2ª OK após fix).
- **1 rollback PROD** (16/16 OK em ~10s).
- **4.319,4019 un movidas** (FB/Estoque → FB/Indisp lote MIGRAÇÃO POR PRODUTO).
- **1 lote criado on-demand** (4829012 produto não tinha MIGRAÇÃO; criou lot_id=59829).
- **Logs auditoria**:
  - `log_2.2_para_indisp_20260524_105037.json` (1ª `--confirmar` — falha)
  - `log_2.1_ROLLBACK_para_indisp_falha_20260524_105219.json` (rollback OK)
  - `log_2.2_para_indisp_FIX_20260524_110128.json` (2ª `--confirmar` — OK)

### 9.3 Pre-mortem rigoroso

#### Riscos operacionais (impacto: PROD)

| Risco | Probabilidade | Impacto | Mitigação atual | Mitigação adicional |
|---|---|---|---|---|
| **Outra constant `lot_id` universal usada em WRITE futuro** | Alta (humano repete padrão) | Alto (estado parcial; rollback manual) | G031 doc; comentário em locations.py | **Auditoria grep `LOTES_*\[` em todo codebase** (próxima sessão) |
| **MODO C com `--lote LOTE_REAL` errado** (ex.: lote de outro produto) | Média | Médio (FALHA_REDUCAO/AUMENTO; sem dano) | `lot_svc.buscar_por_nome` filtra `product_id` (G021 herdado) | Adicionar validação pré-flight no CLI |
| **Falha de rede entre `ajustar_quant -qty` e `ajustar_quant +qty`** | Baixa | Alto (estado parcial inrecuperável sem auditoria) | `qty_reduzida_origem` reportado | **Helper automático de rollback** baseado em log JSON |
| **Lote MIGRAÇÃO criado on-demand sem aprovação fiscal** | Média (16 produtos teste, 1 criação) | Médio (lote orfão se transferência rollback) | `lote_destino_criado_agora=True` reportado em auditoria | Pre-flight check + flag `--criar-lote-destino` opcional |
| **`origem` em sub-location não-padrão** (não FB/Estoque) | Baixa | Baixo (falha clara `FALHA_QUANT_VAZIO`) | `location_id_origem` override aceito | OK |
| **Rerodar MODO C após sucesso** (idempotência) | Alta | Médio (saldo é movido 2x; conta inflada) | Service NÃO tem guard contra duplo movimento | **Adicionar log/cache de operações recentes** OU pre-check "saldo origem > 0" |

#### Riscos técnicos (impacto: código + integração)

| Risco | Probabilidade | Impacto | Mitigação atual |
|---|---|---|---|
| **Pyright stale reportando imports `app.odoo.estoque.scripts.*` não resolvíveis** | Alta | Baixo (apenas IDE; runtime OK) | Documentado; ignorar |
| **`stock_lot_service` lança erro em `criar` se nome já existe** (race condition) | Baixa | Médio | `criar_se_nao_existe` já trata via fallback `buscar_por_nome` em `except` |
| **`StockLotService.buscar_por_nome` retorna lot_id de produto DIFERENTE** se filtro company_id falhar | Baixa | Alto (mesmo bug G031) | Filtro `product_id` + `company_id` no service (G021) |
| **`criar_se_nao_existe` falhar em dry-run-then-real**: dry-run valida com lote inexistente (`FALHA_LOTE_DESTINO_INEXISTENTE`), real cria lote ok, próximo dry-run vê lote existente — divergência de plano | Média | Baixo (operacional — dry-run "stale" mostra plano diferente) | Documentar comportamento em SKILL.md |

#### Riscos de processo (impacto: continuidade)

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Próxima sessão usa constants `lot_id` universal sem ler G031** | Alta | Alto (replica incidente) | G031 + comentário extenso em locations.py + memória atualizada |
| **Skill 5/6/7/8 futura introduz mesmo padrão** | Média | Alto | Princípio "resolver POR PRODUTO via service" deve aparecer em CLAUDE.md §contrato de átomo |
| **Esquecer de auditar OUTROS lugares que usam `LOTES_MIGRACAO_POR_COMPANY`** | Alta | Alto | Seção "Outros lugares que podem ter mesma falha" em G031.md tem comando `grep` acionável |
| **Devolução do saldo Indisp para Estoque** (operação inversa) sem skill equivalente | Média | Médio (operadores improvisam) | Documentar inversa como caso 2.2.d existente (MIGRA→lote real) |

#### Riscos arquiteturais (impacto: aposentar/refatorar)

| Risco | Probabilidade | Impacto | Mitigação proposta |
|---|---|---|---|
| **Constants `lot_id` ficarem como dead code** após N skills migrarem | Alta | Baixo (limpa codebase) | Quando todos usarem `lot_svc`, REMOVER `LOTES_MIGRACAO_POR_COMPANY` (apenas manter `NOME_*`) |
| **Pattern "resolver via lot_svc" repetir-se em 4-5 skills** sem helper compartilhado | Média | Baixo (duplicação) | Considerar `_utils.resolver_lote_consolidador(odoo, nome, pid, cid)` em sessão futura |
| **Rollback automático**: não há padrão para reverter estado parcial sem intervenção humana | Média | Médio (incidentes maiores) | Macro `--rollback-from-log <path>` futuro (não bloqueante) |

### 9.4 Aprendizados estruturais

1. **stock.lot é POR PRODUTO no Odoo CIEL IT** — nunca usar `lot_id` como FK universal. ETL/Migration que herdar lots de mestre por nome precisa criar 1 lot por (nome × produto × company).
2. **Dry-run só simula chave, não FK** — testes de FK só disparam em `--confirmar`. Adicionar smoke test "1 unidade real" pode ser etapa intermediária entre dry-run e batch completo.
3. **Estado parcial em composições compostas é INEVITÁVEL** — não tem como ser totalmente atômico em RPC distribuído. Solução: relatório claro + rollback documentado (testado nesta sessão).
4. **Constants em `app/odoo/constants/`** devem distinguir explicitamente entre (a) IDs universais (`COMPANY_LOCATIONS`, `LOCAIS_INDISPONIVEL` — por company, faz sentido) e (b) IDs "por instância" (lot, product, partner — NÃO universal). Adicionar comentário-padrão em cada arquivo.
5. **Lição Rafael**: "lote é por produto, usar `ilike`/`like` igual Odoo" — princípio geral de busca via serviço (não cache de IDs).

### 9.5 Pendências (não-bloqueantes)

1. **Auditoria grep `LOTES_*_POR_COMPANY\[` em todo codebase** — verificar se outras skills usam como FK.
2. **Smoke test 1-unidade** (`--confirmar` em 1 caso antes de batch) como passo intermediário.
3. **Helper `_utils.resolver_lote_consolidador`** se pattern se repetir.
4. **Macro `--rollback-from-log`** futuro.
5. **CLI `--nome-lote-destino`** custom (atualmente hardcoded "MIGRAÇÃO" via service).

**Conclusão**: Skill 2 mín viável evolui para 3 modos (A/B/C). Incidente G031 expôs risco arquitetural — corrigido + documentado + pattern escalável codificado. PROD validado: 4.319,4019 un movidas em 23s.

### 9.6 Code-review consolidado (3 reviewers paralelos pós-implementação)

**Reviewer 1 (code)**, **Reviewer 2 (docs)**, **Reviewer 3 (arquitetura)** retornaram total de **17 findings** (4 HIGH cada x 3 + alguns MED/LOW). Aplicadas correções HIGH/MED + 1 bug crítico cross-arquivo:

| # | Sev | Reviewer | Issue | Status |
|---|---|---|---|---|
| **CR1#1** | HIGH | code | CLI `_FALHAS` sem `FALHA_LOTE_DESTINO_INEXISTENTE` → exit 4 falso em dry-run sem lote MIGRAÇÃO | ✅ corrigido + removidos `FALHA_PASSO_1/2` stale |
| **CR1#3+CR3#1** | HIGH | code+arq | Help text `--para-indisponivel` ainda referencia `LOTES_MIGRACAO_POR_COMPANY` (defeated constant) | ✅ corrigido — agora cita `lot_svc.criar_se_nao_existe` |
| **CR1#4** | MED | code | Test comment em `test_transferir_para_indisponivel_cd` reforça constant antiga | ✅ comment atualizado para citar G031 |
| **CR1#5** | HIGH | code | Sem teste cobrindo `EXECUTADO_AUTO_CORRIGIDO` como sucesso (gap de regressão) | ✅ +1 teste novo |
| **CR2#1** | HIGH | docs | SKILL.md frontmatter diz "2 modos atômicos" | ✅ "3 modos atômicos" |
| **CR2#2** | HIGH | docs | ROADMAP linha 23 contradição interna "37→40" vs linha 71 "37→52" | ✅ alinhado para "37→52" |
| **CR2#3** | MED | docs | ROADMAP ORDEM DE EXECUÇÃO row Skill 2 "33 pytest, 2 modos" stale | ✅ "52 pytest, 3 modos + MODO C PROD" |
| **CR2#4** | MED | docs | Ambiguidade `FALHA_PASSO_1/2` vs `FALHA_REDUCAO/AUMENTO` | ✅ removido PASSO_1/2; ROADMAP nota refactor |
| **CR2#5** | LOW | docs | Memory "14+ orquestradores" vs SKILL.md "16+" | ✅ memory atualizado |
| **CR3#2** | HIGH | arq | `LOTES_MIGRACAO_POR_COMPANY` ainda importável sem guard | ✅ DeprecationWarning + comentário extenso |
| **CR3#5** | MED | arq | FALHA_AUMENTO sem `rollback_hint` machine-readable | ✅ `rollback_hint` dict adicionado + 2 testes |
| **CR3#6** | MED | arq | Tree galho 2.2 sem "SEM NF" como disambiguation | ✅ atualizado em subagente |
| **CR3#7** | **CRITICAL** | arq | `fat_lf_cleanup.py:41` tem mesmo bug `create_returns` que `picking.devolver` pré-v3 (não trata `list`/`bool`); script VIVO em PROD | ✅ parser sincronizado com v3 (aceita 3 shapes) |
| **CR3#7b** | MED | arq | MAPA_SCRIPTS Skill 8 table inconsistente (status `AO-CAPINAR` vs Skill 5 table `AO-CAPINAR-VIVO`) | ✅ Skill 8 row atualizada |
| CR3#3 | LOW | arq | Outras constants `COMPANY_PARTNER_ID`, `INCOTERM_CIF`, `CARRIER_NACOM` | ✅ confirmadas safe (uma-por-company, não per-product) |
| CR3#4 | LOW | arq | `picking.devolver` G019 pattern já correto | ✅ confirmado |
| CR3#8 | LOW | arq | Pattern "resolver POR PRODUTO via lot_svc" é geral, não MIGRAÇÃO-only | ✅ documentado conclusão; sem ação (premature abstraction) |

**Pytest pós-correções**: **146 verdes** (era 143; +3 testes: `EXECUTADO_AUTO_CORRIGIDO`, `rollback_hint`, `rollback_hint dry-run None`).

**Achado mais crítico (CR3#7)**: `scripts/inventario_2026_05/fat_lf_cleanup.py:41` continuava com parser `create_returns` antigo (`new_pid = res.get('res_id') if isinstance(res, dict) else res`) — mesmo bug que `picking.devolver` na v3 pre-CR1#1. Se o Odoo retornasse uma lista `[pid]` em vez de dict ou int, fat_lf_cleanup silenciosamente passava a lista como `picking_id` em `search_read`, fazendo a validação subsequente retornar vazio e a função reportar sucesso falso. Sincronizado com a v3.

### 9.7 Pendências da sessão (não-bloqueantes)

1. ✅ **RESOLVIDA em 2026-05-24 v5**: Auditar `grep -rn "LOTES_MIGRACAO_POR_COMPANY\[" app/ scripts/` — **ZERO callers reais** confirmado (apenas 2 matches em docs descrevendo o incidente: ROADMAP §sessão v4 + este VALIDACAO §9.1). Sem código WRITE usando a constant como FK universal.
2. Smoke test 1-unidade (`--confirmar` em 1 caso antes de batch) como padrão entre dry-run e batch completo.
3. Helper `_utils.resolver_lote_consolidador(nome, pid, cid)` se padrão se repetir com nome diferente de "MIGRAÇÃO" (premature agora).
4. Macro `--rollback-from-log <path>` futuro — automatizar reversão usando `rollback_hint` reportado.
5. CLI `--nome-lote-destino` custom (atualmente hardcoded "MIGRAÇÃO" via default; service aceita).

---

## 10. Sessão 2026-05-24 v5: Skill 4 `operando-mo-odoo` nasce + 4 dry-run PROD + 9 findings code-review

> Após sessão v4 (Skill 2 modo C + G031). Foco: criar Skill 4 do zero (sem service legado) seguindo ordem bottom-up. Demanda real: cancelar MOs antigas/zumbi periodicamente em FB (caso 120 MOs em 2026-05-20 validou pattern em PROD).

### 10.1 Cronologia

| # | Evento | Resultado |
|---|---|---|
| 1 | Setup + pytest baseline 146 verdes | OK |
| 2 | C1 mineração: 2 scripts-fonte (`cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py`) + investigação AO VIVO via `/tmp/investigar_mos_skill4.py` | 10.000 MOs FB, 17 CD, 3367 LF; idempotência action_cancel validada em FB/OP/BALDE/00009 |
| 3 | C2 service `mo.py` (NOVO — do zero pattern Skill 1) + shim preventivo `services/stock_mo_service.py` | 26 testes pytest verdes baseline |
| 4 | C3-C5 SKILL.md + CLI `operar_mo.py` (single OR batch) | Help text + --dry-run default + exit codes 0/1/2/4 |
| 5 | C6 dry-run vs PROD 4 casos (NOOP idempotente, DRY_RUN_OK sem consumo, FALHA_FURO_CONTABIL consumo=1410.05, batch FB ate 2025-06) | 100% bate; log em `/tmp/log_skill4_C6_validacao_dry_run.json` |
| 6 | C7 cross-refs: subagente + ROUTING_SKILLS (46→47 invocaveis, 14→15 Skills Odoo) + tool_skill_mapper + CLAUDE.md raiz + app/odoo/CLAUDE.md | 6 arquivos atualizados |
| 7 | C8 folha `app/odoo/estoque/fluxos/3.1-cancelar-mo.md` (3 sub-casos a/b/c; 3.1.c DELEGADO para mrp.unbuild) | Pattern progressive disclosure |
| 8 | C9-C10 arquivar `cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py` para `_validados/operando-mo-odoo/` (sys.path parents[2]→parents[4]; museum vivo validado via import) | MAPA_SCRIPTS + ROADMAP + README fluxos atualizados |
| 9 | Code-review paralelo (2 reviewers): 9 findings reais (4 HIGH + 4 MED + 1 LOW) | Ver §10.4 abaixo |
| 10 | Fixes aplicados: order server-side no search_read, warning consumo='qualquer', tratamento `None` pós-cancel, ROUTING_SKILLS galho 6, README fluxos status, SKILL.md "4 casos", refinar cross-skill 3.1.c | +3 testes (29 verdes total Skill 4) |
| 11 | Baseline final: **175 pytest verdes** (146 antigos + 29 Skill 4) | ✅ |

### 10.2 Métricas finais

- **29 pytest verdes** (Skill 4 — 26 baseline + 3 cobrindo CR fixes).
- **175 pytest verdes totais** (172 anterior + 3 da Skill 4).
- **4 dry-run PROD validados** (todos sem `--confirmar` em PROD nesta sessão; pattern já validado em PROD em sessão anterior 2026-05-20 via scripts-fonte).
- **0 execuções `--confirmar`** em PROD nesta sessão (demanda-driven).
- **2 scripts SUPERADOS** (`cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py` → `_validados/operando-mo-odoo/`).
- **2 docs novos**: `app/odoo/estoque/fluxos/3.1-cancelar-mo.md` (folha) + `_validados/operando-mo-odoo/VALIDACAO.md`.
- **1 service novo**: `app/odoo/estoque/scripts/mo.py` (~380 linhas) + shim `services/stock_mo_service.py`.
- **1 SKILL.md + 1 CLI** em `.claude/skills/operando-mo-odoo/`.

### 10.3 Pre-mortem 4 dimensões

#### Riscos operacionais (impacto: PROD)

| Risco | Probabilidade | Impacto | Mitigação atual | Mitigação adicional |
|---|---|---|---|---|
| **Operador usa `--consumo qualquer` esperando cancelar MOs com consumo** | Média | Baixo (todas FALHA_FURO_CONTABIL — sem efeito mas confuso) | Warning logado (CR fix M3) | Considerar erro fatal no service |
| **Cancelamento de MO `in progress` real (operador apontando)** | Baixa-Média | Médio (perde apontamento parcial) | Default `--states draft,confirmed,progress,to_close` inclui progress; recomenda CLI doc filtrar | Adicionar flag `--excluir-progress` opcional como helper |
| **MO mãe-filha (multi-nível semi-acabado)**: cancelar acabado deixa semi órfão | Média | Médio (fluxo cross-skill manual) | Docs em SKILL.md + memória [[reaproveitar-semiacabado-orfao-mo-cancelada]] | Verificar via Skill 9 antes — não automatizado |
| **Cascade delete da MO (config customizada Odoo)** | Baixa | Baixo (CR fix M1 trata como EXECUTADO) | `cancel_deleted` status retornado | Logar caso real se ocorrer (auditoria) |
| **Search_read sem limit em batch de 10.000+ MOs FB** | Média (FB tem 10k+ MOs cumulativas) | Médio (Python sort lento, RAM ~50MB para 10k dicts) | order server-side ASC (CR fix H1) | Iteração futura: search + read em batches de 500 |

#### Riscos técnicos (impacto: código + integração)

| Risco | Probabilidade | Impacto | Mitigação atual |
|---|---|---|---|
| **Pyright stale reportando `app.odoo.estoque.scripts.mo` não resolvível** | Alta | Baixo (apenas IDE) | Documentado em §9.3 |
| **Idempotência action_cancel em state=cancel** | Alta (validado AO VIVO) | Baixo | NOOP retornado sem RPC extra |
| **`mrp.production.action_cancel` retorna `True` em sucesso** | Alta | Baixo | Code reapproved não checar retorno; checa apenas state pós |
| **`stock.move.quantity` campo correto (vs product_qty)** | Alta | Médio se errado | Validado em scripts-fonte + investigação AO VIVO; comentado no service |

#### Riscos de processo (impacto: continuidade)

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Próxima sessão usa Skill 4 sem ler G-MO-01 docs** | Média | Alto (cancelar com consumo = furo) | SKILL.md + fluxo 3.1 + service docstring + memória |
| **Skill 4 evolui para criar/alterar MO sem demanda real** | Baixa | Médio (premature implementation) | Princípio demanda-driven documentado; átomos previstos marcados ⬜ |
| **Operador esquece de pre-flight via Skill 9 antes de batch** | Média | Médio (cancela MO de produto crítico) | Receita docs CLI mostra dry-run obrigatório; canary `--limite 1` documentado |
| **Cross-skill com mrp.unbuild manual (3.1.c)** falha por operador errar args XML-RPC | Alta | Médio (lotes errados na devolução) | Memória `[[reaproveitar-semiacabado-orfao-mo-cancelada]]` documenta procedimento |

#### Riscos arquiteturais (impacto: aposentar/refatorar)

| Risco | Probabilidade | Impacto | Mitigação proposta |
|---|---|---|---|
| **Demanda real para `mrp.unbuild` virar skill** se 2+ casos repetirem | Baixa-Média | Baixo (criar skill nova `mrp-unbuild-odoo`) | Acompanhar — RFC quando padrão repetir |
| **Demanda real para `alterar_mo` (mover componente, mudar qty) virar fluxo composto** | Média | Baixo (criar folha cross-skill 3.2) | Caso real existe ([[mo_componente_local_consumo]]); aguardar 2+ ocorrências |
| **Helper `medir_consumo_mo` reutilizado em outras skills** (planejamento, auditoria) | Média | Baixo (mover para `_utils`) | Conforme demanda |

### 10.4 Code-review consolidado (2 reviewers paralelos)

**Reviewer 1 (code)** focou em `mo.py` + `test_stock_mo_service.py` + `operar_mo.py`. **Reviewer 2 (docs/arquitetura)** focou em SKILL.md + fluxo 3.1 + ROADMAP + cross-refs.

| # | Sev | Rev | Issue | Status |
|---|---|---|---|---|
| **CR1-H1** | HIGH | code | `cancelar_mos_em_massa` search_read sem `order` (Python sort 10k+ MOs) | ✅ `order='create_date asc'` server-side + comentário explica por que não usar `limit=max_n` (pré-filtro de consumo precisa de TUDO antes do trim) |
| **CR1-M1** | MED | code | `_ler_mo` retorna `None` após action_cancel → FALHA_STATE_INESPERADO falso | ✅ Tratado como `EXECUTADO` com `state_apos='cancel_deleted'` + warning log + 1 teste novo |
| **CR1-M3** | MED | code | `consumo='qualquer'` sem `forcar_consumo=True` silenciosamente bloqueia todas | ✅ Warning logado em entry-point de `cancelar_mos_em_massa` + 1 teste novo |
| CR1-LOW1 | LOW | code | `mo.py` sem `__all__` (shim `from ... import *` exporta tudo) | ⏸️ Não bloqueia; aceitável (constants úteis) |
| CR1-LOW2 | LOW | code | `_salvar_log` path `scripts/inventario_2026_05/auditoria/` envelhece mal | ⏸️ Conscientizado; refatorar quando inventory project encerrar |
| CR1-LOW3 | LOW | code | `import pytest` inline em 1 teste | ⏸️ Estilo menor |
| **CR2-H1** | HIGH | docs | `fluxos/README.md` linha 51, 54: status `2.5`/`3.1` mostrados como ⬜ (incorreto — ambos 🟡) | ✅ Atualizado para 🟡 com link folha |
| **CR2-H2** | HIGH | docs | `ROUTING_SKILLS.md` galho 6 (ESTOQUE WRITE) não lista `operando-mo-odoo` (agrupa em "em construção") | ✅ Adicionada linha explícita no galho 6 |
| CR2-H3 | LOW | docs | Divergência "14" (v3) vs "15" (v5) Skills Odoo entre checkpoints | ⏸️ Não bloqueia (transição entre sessões correta) |
| **CR2-M1** | MED | docs | `SKILL.md` seção Validação: "C6: 2-3 casos" mas real é 4 | ✅ Atualizado para "4 casos" + descrição completa |
| **CR2-M2** | MED | docs | `fluxos/3.1-cancelar-mo.md` cross-skill: Skill 2 listada como "pré-condição de 3.1.c" mas 3.1.c é DELEGADO | ✅ Refinado: Skill 2 apenas como referência de contexto relacionado |
| CR2-LOW1-4 | LOW | docs | Vários menores (description frontmatter, ponteiro VALIDACAO_FINAL §10 stale) | ⏸️ Não bloqueia; §10 agora existe (este texto) |

### 10.5 Pytest final pós-correções

**175 verdes totais** (172 anterior + 3 da Skill 4 cobrindo CR1-M1, CR1-M3, CR1-H1). Skill 4 isolada: **29 verdes** em 0.78s.

### 10.6 Aprendizados estruturais

1. **Pattern de criar skill do zero**: Skill 4 (sem service legado) seguiu pattern de Skill 1 (criar do zero) mais bem-sucedido que tentar adaptar Skill 5 (capinar service existente). Diferenças: (a) sem shim retroativo (criamos shim preventivo para futuro); (b) sem testes prévios para preservar (escrever todos do zero foi mais limpo); (c) sem risco de quebrar consumers ativos.
2. **Investigação AO VIVO é crítica para skills WRITE em domínios novos**: rodar `/tmp/investigar_mos_skill4.py` antes do C1 final revelou (a) idempotência confirmada (não documentada), (b) volumes reais (FB 10k MOs vs CD 17 vs LF 3.4k) que mudaram a estratégia de filtros default, (c) confirmação que `qty_produced ≠ consumo` (campo correto é `stock.move.quantity`).
3. **Code-review paralelo (code + docs) pega bugs ortogonais**: reviewer code achou OOM/M1 não-relacionados ao que o reviewer docs achou (status incoerente no README + ROUTING galho 6 sem skill listada). Sem ambos, 4 fixes HIGH/MED ficariam abertos.
4. **G019-like pattern reaproveitável**: re-le state pós-ação é invariante geral, não específica de pickings. Skill 4 aplica em `cancelar_mo` (verifica state='cancel' pós-action_cancel).
5. **Princípio demanda-driven validado novamente**: `criar_mo` e `alterar_mo` estavam previstos no briefing inicial mas NÃO implementados — sem demanda real. Mantidos como ⬜ no catálogo. Pattern alinhado com [[feedback_skills_demanda_driven]].
6. **Status `cancel_deleted`** (M1 fix): novo precedente para skills futuras que cancelam objetos Odoo com cascade customizado (M0s, vouchers, journals).

### 10.7 Pendências da sessão v5 (não-bloqueantes)

1. **Smoke test `--confirmar 1 MO` real** em PROD quando demanda surgir (canary `--limite 1` antes de batch — padrão sessão).
2. **Skill `mrp-unbuild-odoo`** futura se padrão 3.1.c (MO com consumo) repetir 2+ casos.
3. **Skill `alterar_mo`** (mover componente, ajustar qty) — implementar como folha de fluxo composto 3.2 se padrão repetir.
4. **Helper `_utils.medir_consumo_mo`** se for usado por outras skills (planejamento, auditoria).
5. **Refatorar batch para `search` + `read` chunked** se executions reais em batch >5000 MOs surgirem (atualmente Python sort de 10k é OK ~50ms).
6. **`--excluir-progress` flag opcional** se incidente de cancelar MO em produção ativa ocorrer.

---

## 11. Sessão 2026-05-24 v6: Skill 6 `planejando-pre-etapa-odoo` nasce + capina 03b+04b + 9 findings CR

> Após sessão v5 (Skill 4 NOVA). Foco: criar Skill 6 capinando os 2 scripts-fonte do planner D007 da pre-etapa CD/FB (03b planejar + 04b propor/listar/aprovar). Demanda: workflow Onda 5 (CD) ja rodou em PROD em sessoes anteriores via 03b/04b ad-hoc — capinar para uniformizar com pattern Skills 1-5.

### 11.1 Cronologia

| # | Evento | Resultado |
|---|---|---|
| 1 | Setup + pytest baseline 175 verdes | OK |
| 2 | Verificação main: avancou 1 commit cosmético (`fb494608` skip D8) — sem rebase | OK |
| 3 | C1 mineração 4 arquivos integral: `03b_planejar_pre_etapa_cd` (planner READ), `04b_propor_pre_etapa_cd` (WRITE banco local + workflow hash), `09b_executar_pre_etapa` (executor C3 — DELEGADO, NAO entra na Skill), `pre_etapa_estoque_service.py` (service + 4 dataclasses + algoritmo 10-passos D007) + 13 testes pytest existentes | 4 arquivos lidos completos |
| 4 | C2 capinar `services/pre_etapa_estoque_service.py` → `estoque/scripts/pre_etapa.py` + shim. Estendido com 7 helpers top-level (`enriquecer_quants_para_planejar`, `_serializar_plano_em_dicts`, `gerar_excel_plano_pre_etapa`, `planejar_pre_etapa_batch_company`, `_calcular_hash_onda`, `_fazer_backup_pg_dump`, `propor_ajustes_pre_etapa`, `listar_onda_pre_etapa`, `aprovar_onda_pre_etapa`) + 4 constantes do workflow (`ACOES_INTERNAS_POR_CID`, `ONDA_NUM_POR_CID`, `ACAO_RESIDUAL_FB_CD`, `COMPANY_LOCATIONS_PRE_ETAPA`) | 13 testes pytest originais preservados via shim |
| 5 | C3-C5 SKILL.md + CLI `.claude/skills/planejando-pre-etapa-odoo/scripts/planejar_pre_etapa.py` (4 modos exclusive: planejar/propor/listar-onda/aprovar-onda; `--dry-run` default em modos write; listar-onda sempre READ; exit codes 0/1/2/4) + 6 testes pytest novos cobrindo helpers I/O | 19 verdes |
| 6 | C6 validação dry-run: 3 smokes CLI (FALHA_INPUT_AUSENTE exit 1, FALHA_USO exit 2, DRY_RUN_OK inputs vazios exit 4); log `/tmp/log_skill6_C6_validacao_dry_run.json`. Limitações documentadas: listar-onda em PG local (SQLite stub sem tabela; futura sessão) e batch real com Odoo (scripts 01+02 nao rodaram nesta worktree). | 3 smokes OK |
| 7 | C7 cross-refs: subagente (description + skills + header v5→v6 + galho 4 NOVO), ROUTING_SKILLS (47→48 invocaveis + 15→16 Skills Odoo + galho 6 ESTOQUE WRITE), tool_skill_mapper (`'planejando-pre-etapa-odoo': 'Estoque Odoo (Write)'`), CLAUDE.md módulo (§6 catálogo + header status) | 5 arquivos atualizados |
| 8 | C8 folha de fluxo `app/odoo/estoque/fluxos/4.1-pre-etapa-cd-d007.md` com 4 sub-casos a/b/c/d (preview, re-aprovar, Onda 6 FB futura, debug subset cods) + README atualizado com galho 4 NOVO | Pattern progressive disclosure |
| 9 | C9-C10 arquivar `03b_planejar_pre_etapa_cd.py` + `04b_propor_pre_etapa_cd.py` para `_validados/planejando-pre-etapa-odoo/` (sys.path parents[2]→parents[4]; museum vivo validado via import); `09b_executar_pre_etapa.py` permanece VIVO (C3 macro pendente). VALIDACAO.md criada. MAPA_SCRIPTS + ROADMAP + este doc atualizados | 2 SUPERADOS + 1 VIVO |
| 10 | Code-review paralelo (2 reviewers): 8 + 7 = 15 findings reais (3 HIGH + 8 MED + 4 LOW + 1 retratado). Ver §11.4 abaixo | Logs em `/tmp/skill6_*_review_findings.md` |
| 11 | Fixes aplicados: F1 savepoint, F2 getattr hash, F3 LISTADO exit code, F4 guard cod outlier, F6 FileNotFoundError pg_dump (code); F1 ROUTING 46→48, F2 C6 ✅, F3 C2 19 testes, F4 numeração fluxo 4.1.x, F5 canary --limite (docs) | +2 testes (CR-F2 getattr defensivo + CR-F4 guard outliers) = 21 verdes |
| 12 | Baseline final: **196 pytest verdes** (175 anterior + 21 da Skill 6) | ✅ |

### 11.2 Métricas finais

- **21 pytest verdes** (Skill 6 — 13 originais preservados + 6 helpers novos + 2 cobrindo CR fixes).
- **196 pytest verdes totais** (175 anterior + 21 da Skill 6).
- **3 smokes CLI** validando exit codes corretos (1/2/4).
- **0 execuções `--confirmar`** em PROD nesta sessão (pattern já validado em PROD em sessões anteriores via scripts-fonte; smoke real do `planejar --confirmar` requer scripts 01+02 rodados).
- **2 scripts SUPERADOS** (03b + 04b → `_validados/planejando-pre-etapa-odoo/`).
- **1 script permanece VIVO** (09b executor — C3 macro pendente capinagem; documentado).
- **2 docs novos**: `app/odoo/estoque/fluxos/4.1-pre-etapa-cd-d007.md` (folha) + `_validados/planejando-pre-etapa-odoo/VALIDACAO.md`.
- **1 service estendido**: `app/odoo/estoque/scripts/pre_etapa.py` (~720 LOC base + ~410 LOC novos = ~1130 LOC) + shim `services/pre_etapa_estoque_service.py`.
- **1 SKILL.md + 1 CLI** em `.claude/skills/planejando-pre-etapa-odoo/`.

### 11.3 Pre-mortem 4 dimensões

#### Riscos operacionais (impacto: PROD)

| Risco | Probabilidade | Impacto | Mitigação atual | Mitigação adicional |
|---|---|---|---|---|
| **Usuario roda `planejar --confirmar` com inputs antigos `/tmp/`** | Média | Médio (plano stale; planeja sobre snapshot velho) | Timestamp no JSON output; usuario revisa Excel antes de propor | Adicionar warning se mtime de inputs > 24h |
| **Usuario aprova onda sem listar primeiro** | Baixa-Média | Baixo (hash divergente bloqueia; FALHA_HASH_DIVERGENTE) | Anti-replay com sha256 sólido (CR-F2 reforçado com getattr defensivo) | Workflow doc em SKILL.md/4.1 obriga listar→aprovar |
| **Operador edita JSON do plano manualmente antes de propor** | Baixa | Médio (CR-F4: cods outliers no JSON quebravam tipo_de_cod com ValueError) | Guard `_cod_valido` filtra e loga warning; ignorados retornados em `cods_ignorados_outlier` | Pre-validate JSON schema antes de chamar propor |
| **`propor` chamado de Flask route com transação ativa** | Média (web/agente) | Alto SEM CR-F1 (rollback nuke transação do caller) | CR-F1 savepoint isola operação; caller decide commit/rollback do parent | Doc em SKILL.md/contrato — "service usa savepoint, seguro em qq sessão" |
| **pg_dump backup falha por `pg_dump` ausente do PATH** | Média (CI/Docker) | Baixo SEM CR-F6 (`FileNotFoundError` opaco) | CR-F6 mensagem actionable "instale postgresql-client" | Default OFF (operador opt-in); fallback graceful |

#### Riscos técnicos (impacto: código + integração)

| Risco | Probabilidade | Impacto | Mitigação atual |
|---|---|---|---|
| **Odoo retorna `product_id` como int em vez de [id, name] tuple** (CR-F5 latente) | Baixa | Médio (enriquecimento silenciosamente perde produto) | Documentado em CR-F5 findings; defensive isinstance check pendente — pattern do script 01 sempre passa tupla |
| **ORM `AjusteEstoqueInventario` evolui sem aviso (renomear `lote_odoo`)** | Baixa-Média | Alto SEM CR-F2 (hash silencioso colapsa) | CR-F2 getattr com default '' mantém hash calculável; teste pytest 20 valida |
| **Pyright stale reportando `app.odoo.estoque.scripts.pre_etapa` não resolvível** | Alta | Baixo (apenas IDE) | Padrão de skill capinada (skills 4, 5, 6 todas têm — IDE reindex resolve) |

#### Riscos de processo (impacto: continuidade)

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Próxima sessão usa Skill 6 sem ler G-PRE-01..10 docs** | Média | Médio (caller esquece de filtrar quants_fb pos-etapa FB) | SKILL.md + fluxo 4.1 + service docstring documentam |
| **Skill 6 evolui sem implementar testes para propor/listar/aprovar (CR-F10)** | Média | Médio (WRITE paths sem cobertura — bug silencioso em PROD) | Pendência documentada; próxima sessão se demanda real surgir |
| **09b executor permanece VIVO indefinidamente** | Alta | Baixo (operação viva — não bloqueia outras skills) | Documentado como C3 macro pendente em ROADMAP/CLAUDE.md §6 |
| **Operador roda `aprovar-onda` em PG local sem tabela migrada** | Média (SQLite stub) | Baixo (FALHA_BANCO claro) | Limitação documentada em SKILL.md §C6 + VALIDACAO §11.5 |

#### Riscos arquiteturais (impacto: aposentar/refatorar)

| Risco | Probabilidade | Impacto | Mitigação proposta |
|---|---|---|---|
| **Skill 6 cresce além de 4 modos** (operador quer `--modo executar`) | Média-Alta | Baixo-Médio (Skill 6 fica monolítica) | Manter Skill 6 SÓ planner+propor+listar+aprovar; executar é Skill futura (capinagem 09b para `orchestrators/pre_etapa_executor.py`) |
| **Workflow hash usado em outras skills** (Ondas 1-4 via 04_propor_ajustes) | Média | Baixo (helpers reutilizáveis) | `_calcular_hash_onda` e `aprovar_onda_pre_etapa` podem ser usados sob demanda; ondas 1-4 permanecem em 04_propor_ajustes |

### 11.4 Code-review consolidado (2 reviewers paralelos)

**Reviewer 1 (code)** focou em `pre_etapa.py` (helpers + constantes novos) + `planejar_pre_etapa.py` CLI + 6 testes novos. **Reviewer 2 (docs/arquitetura)** focou em SKILL.md + fluxo 4.1 + cross-refs (subagente, ROUTING, mapper, CLAUDE.md, ROADMAP, MAPA_SCRIPTS, VALIDACAO).

| # | Sev | Rev | Issue | Status |
|---|---|---|---|---|
| **CR1-F1** | CRITICAL | code | `propor_ajustes_pre_etapa` rollback() nuke transação do caller (Flask route, agente) | ✅ `db.session.begin_nested()` savepoint isola; rollback/commit dentro do savepoint |
| **CR1-F2** | CRITICAL | code | `_calcular_hash_onda` AttributeError silencioso se ORM evolui | ✅ getattr defensivo com defaults; +1 teste pytest validando |
| **CR1-F3** | IMPORTANT | code | `_emitir` exit 4 para LISTADO/LISTADO_VAZIO em dry_run=True programático | ✅ READ-only statuses sempre exit 0 antes do check dry_run |
| **CR1-F4** | IMPORTANT | code | `tipo_de_cod` raise ValueError/IndexError para cods outliers manualmente editados | ✅ Guard `_cod_valido` em propor + log + cods_ignorados_outlier no retorno; +1 teste |
| CR1-F5 | IMPORTANT | code | `enriquecer_quants` latente TypeError se Odoo retornar bare int | ⏸️ Documentado em pre-mortem §11.3; defensive isinstance pendente (pattern script 01 sempre tupla) |
| **CR1-F6** | IMPORTANT | code | `_fazer_backup_pg_dump` FileNotFoundError sem mensagem útil | ✅ try/except FileNotFoundError com mensagem actionable |
| CR1-F9 | LOW | code | Test outliers sem `assert call_count == 2` | ⏸️ Não bloqueia; cobertura via runtime |
| CR1-F10 | IMPORTANT | code | Zero testes para propor/listar/aprovar (WRITE paths) | ⏸️ Pendência documentada; +2 testes parciais (CR-F2 + CR-F4); cobertura WRITE completa = sessão futura |
| **CR2-F1** | HIGH | docs | ROUTING_SKILLS §Skills Inventario "46 invocaveis" — deveria ser 48 | ✅ Atualizado |
| **CR2-F2** | HIGH | docs | SKILL.md C6 "pendente" vs ROADMAP+VALIDACAO ✅ | ✅ Substituído por sumário real dos 3 smokes + limitações |
| **CR2-F3** | HIGH | docs | SKILL.md C2 "13 testes" vs frontmatter "19 testes" | ✅ Alinhado para 19 (13 + 6 helpers) |
| **CR2-F4** | MED | docs | SKILL.md "Fluxo 6.1/6.2/6.3" invenção; árvore canônica usa 4.1.a/b/c/d | ✅ Renomeado + link para folha 4.1; sub-fluxos 4.1.a/b/c/d |
| **CR2-F5** | MED | docs | SKILL.md Fluxo 4.1 step 7 omite canary `--limite 1` | ✅ Adicionado padrão canary + bulk no SKILL.md |
| CR2-F6 | LOW | docs | VALIDACAO.md mistura pytest+CLI smokes em tabela | ⏸️ Cosmético; não bloqueia |
| CR2-F7 | LOW | docs | SKILL.md frontmatter description tem nota arquitetural longa | ⏸️ Mantido — útil contexto para agente |

**8 issues HIGH/MED corrigidas + 2 testes novos cobrindo correções. 5 cosméticos LOW deferidos.**

### 11.5 Pytest final pós-correções

**196 verdes totais** (175 anterior + 21 da Skill 6 cobrindo CR-F2 getattr + CR-F4 outliers + helpers + originais). Skill 6 isolada: **21 verdes** em 0.68s.

### 11.6 Aprendizados estruturais

1. **Pattern Skill 6 = capinagem retroativa pesada**: combina pattern Skill 5 (git mv + shim) com extensão substantiva do service (7 helpers I/O novos + 4 constantes). Mais complexo que Skills 4/5 mas seguindo a mesma estrutura. Pattern reutilizável para Skill 7/8 que tambem capinam services existentes com I/O.
2. **Savepoint > rollback() em services chamados por Flask routes/agente**: padrão estabelecido aqui (CR-F1) replica `[[gotcha_commit_service_vaza_savepoint]]` mas para rollback. Adicionar como invariante: services que ROLAM TX devem usar savepoint.
3. **getattr defensivo em hash anti-replay**: CR-F2 lição — ORM evolui silenciosamente, hash não pode raise AttributeError. Pattern reaproveitável: qualquer hash baseado em atributos ORM deve usar getattr.
4. **Guard de outliers em WRITE quando READ filtra**: CR-F4 lição — se `planejar` filtra outliers mas `propor` consome JSON externo, este precisa REFAZER o filtro. Não confiar em invariantes da camada anterior.
5. **Pytest mock-based para WRITE paths é limitado**: cobertura real de propor/listar/aprovar exige Flask app_context + sessão SQLAlchemy + tabela migrada (PG local). Documentar como pendência (CR-F10) sem bloquear maturidade da skill.
6. **Princípio demanda-driven validado novamente**: a Skill 6 NASCEU porque o pattern 03b+04b ja rodou em PROD múltiplas vezes (Onda 5 do CD em sessões anteriores). Não foi premature implementation.

### 11.7 Pendências da sessão v6 (não-bloqueantes)

1. **Smoke `planejar --confirmar` real em PROD** quando demanda surgir (precisa scripts 01+02 rodados + Odoo PROD).
2. **Smoke `propor`/`listar-onda`/`aprovar-onda` real em PG local** com tabela `ajuste_estoque_inventario` migrada (não disponível nesta worktree SQLite).
3. **Testes integrados para propor/listar/aprovar** (CR-F10): cobertura WRITE paths completa em sessão futura — mockar AjusteEstoqueInventario.query ou setup PG local.
4. **Capinagem `09b_executar_pre_etapa.py`** para `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (C3 macro) quando padrão for usado novamente — atualmente VIVO ad-hoc.
5. **Defensive isinstance em `enriquecer_quants_para_planejar`** (CR-F5): proteger contra Odoo retornar bare int em product_id se a API mudar.
6. **Helper `_utils.enriquecer_quants_raw`** se for usado por outras skills (Skill 9 query, futuro orchestrator).

---

## 12. Sessao 2026-05-24 v6.1: Caso REAL 71 cods Indisponivel PAUSADO — gap arquitetural reservas ativas

> Apos sessao v6 (Skill 6 nasce), usuario pediu para validar Skill 2 modo A+B com caso real: 71 cods em FB para mover para FB/Indisponivel em 2 etapas (lote->MIGRACAO + FB/Estoque->FB/Indisp). Auditoria AO VIVO revelou gap arquitetural significativo — gestor/skills nao tem ferramentas claras para tratar RESERVAS ATIVAS bloqueando transferencias futuras. **Caso PAUSADO sem nenhum write em PROD.**

### 12.1 Cronologia

| # | Evento | Resultado |
|---|---|---|
| 1 | Usuario aciso sobre limitacao reserved=0 forcado na Skill 6 enriquecer + pediu validacao Skill 2 modo A+B com caso real | Plano de 2 etapas formulado |
| 2 | Plano de execucao + setup: salvar 71 cods em TSV + verificar CLI Skill 9 | OK |
| 3 | Auditoria batch AO VIVO via Skill 9 (`consultar_quants.py --cods <71> --empresas FB`) | 190 quants retornados, COM `reserved_quantity` real |
| 4 | Analisador Python classifica 71 cods em 5 categorias (GREEN/SKIP-sem-saldo/SKIP-sublocation/FLAG-quase-100%/FLAG-50%) | Padrao identificado: lote 13206 + MIGRACAO FB/Estoque reservados em 5+ cods |
| 5 | Gerador de plano A+B (`gerar_plano_indisp.py`): 67 cods em plano (4 SKIP), 95 chamadas Etapa A, 67 chamadas Etapa B | Plano detalhado em `plano_etapa_A.tsv` + `plano_etapa_B.tsv` |
| 6 | AskUserQuestion 3 questoes para decisao das 3 categorias (4a/4b/SKIP) | USUARIO INTERROMPEU — apontou gap arquitetural |
| 7 | Usuario: "Vi voce quebrando a cabeça para resolver as reservas... gestor precisa saber resolver isso pela skill ou helpers. Registre as duvidas e problemas." | Pivot para REGISTRO + sem execucao |
| 8 | Avaliacao da estrutura: Skill 2.4 + Skill 9 + fluxo 2.4 + prompt subagente | 4 gaps identificados (vide 12.3) |
| 9 | Artefatos de registro: `docs/.../casos-pendentes/CASO_PENDENTE_RESERVAS_71_CODS_2026_05_24.md` + memoria `[[caso_real_tratar_reservas_pre_transferencia]]` + inputs preservados | OK |

### 12.2 Metricas

- **0 execucoes** em PROD (auditoria foi READ-only Skill 9)
- **1 chamada XML-RPC** READ batch (`consultar_quants.py` — 190 quants em ~3s)
- **5 arquivos preservados** em `docs/inventario-2026-05/casos-pendentes/`
- **1 doc completo** do caso (CASO_PENDENTE_RESERVAS_71_CODS_2026_05_24.md ~280 linhas)
- **1 memoria nova** + entry em MEMORY.md

### 12.3 Gap arquitetural identificado (4 dimensoes)

| # | Dimensao | Status atual | O que faltou |
|---|---|---|---|
| 1 | **Mapeamento conceitual** | Reservas ORFAS (post-mortem) cobertas (Skill 2.4) | Reservas ATIVAS (ante-mortem) bloqueando transferencias — NAO MAPEADO |
| 2 | **Implementacao (atomos)** | Skill 9 retorna `reserved_quantity` real; Skill 2.4 cobre cirurgia/cancel/residual | Faltam: `listar_pickings_por_quant`, `listar_move_lines_por_quant`, `unreserve_picking`, `find_orphan_mls` |
| 3 | **Wiring (fluxos)** | Fluxo 2.4 cobre orfa | Falta fluxo 2.6 "tratar reserva ativa pre-transferencia" |
| 4 | **Direcionamento (prompt)** | Subagente lista Skills 2.4, 5, 9 | Falta regra inviolavel "checar reservas via Skill 9 ANTES de Skill 2" |
| 5 | **Doc operacional** | Gotcha [[gotcha_resetar_reserva_orfao_negativo]] cobre orfas | Falta tabela "5 caminhos seguros para desreservar" (A=cancel / B=devolver / C=unreserve / D=outro lote / E=cirurgia orfa) |

### 12.4 Padrao operacional descoberto

**Lote `13206` reservado em 3 cods** (4899027 + 4890128 + 4902852 — molhos salada/pesto). Lote nao se repete (eh especifico por produto) — entao sao **3 reservas distintas** em produtos diferentes mas com mesmo nome de lote (codificacao do operador?).

**Lote `MIGRACAO` em FB/Estoque reservado em 5 cods** (103000113, 104000054, 105000021, 105000038, 103000117). Cada produto tem seu proprio stock.lot.id=MIGRACAO (gotcha G031). 5 reservas distintas — provavelmente picking unico cruzando os 5 cods, ou 5 pickings separados.

**Hipotese a validar (P2 do roteiro):** existe 1 picking ativo que reserva os 5+3=8 cods simultaneamente? Investigacao SQL/XML-RPC necessaria — sem o atomo `listar_pickings_por_quant`, query deve ser ad-hoc:
```sql
SELECT sml.picking_id, sp.name, sp.state, pp.default_code, sl.name as lot, sml.quantity
FROM stock_move_line sml
JOIN stock_picking sp ON sml.picking_id=sp.id
JOIN product_product pp ON sml.product_id=pp.id
LEFT JOIN stock_lot sl ON sml.lot_id=sl.id
WHERE sml.state IN ('assigned','partially_available') AND sml.company_id=1
  AND ((sl.name='13206' AND pp.default_code IN ('4899027','4890128','4902852'))
    OR (sl.name='MIGRAÇÃO' AND pp.default_code IN ('103000113','104000054','105000021','105000038','103000117')));
```

### 12.5 Decisoes pendentes (a serem tomadas em sessao futura)

3 questoes que **AskUserQuestion** apresentou ao usuario (interrompido):
1. **Cat 4a (4 cods 99%):** reduzir qty para saldo livre? skip? tocar reserva?
2. **Cat 4b (5 cods 50%):** skip? cobertura parcial? cancelar pickings primeiro?
3. **Cat SKIP (4 cods):** confirmar skip? transferir 301000003 de Pos-Producao primeiro?

Mais decisoes pendentes (descobertas pos-pausa):
4. **Etapa B impactada:** 5 cods tem MIGRACAO em FB/Estoque ja reservada — Etapa B vai falhar ao tentar mover qty_total. Como tratar?
5. **Prioridade implementacao gap:** P1 (implementar atomos faltantes ANTES) ou P2 (consultando-sql ad-hoc agora, atomos depois)?

### 12.6 Aprendizados estruturais (para integrar nas Skills/prompt)

1. **Auditoria batch READ-only ANTES de WRITE batch eh INVARIANTE operacional**: 1 chamada Skill 9 economizou ~14 chamadas perigosas (4 SKIP + 9 FLAG + 1 Pos-Producao). Adicionar como regra ao prompt do gestor.
2. **`reserved_quantity` real eh fonte de verdade — `reserved=0 forcado` (Skill 6 enriquecer) eh false negative** que ja confundiu nesta sessao. Resolver via opcao B do gap reserved (modificar script 01 para incluir reserved_quantity).
3. **Padrao de reserva sistemica** (mesmo lote/MIGRACAO reservado em multiplos cods) indica picking ativo de operacao em andamento — NAO devemos tocar sem entender o que esta rolando.
4. **Gestor precisa de READ inverso ML→quant**: o usuario falou explicitamente que o gestor "precisa saber resolver isso pela skill ou helpers". Atomo `listar_pickings_por_quant` na Skill 9 eh prioridade 1.
5. **5 caminhos para desreservar precisam estar DOCUMENTADOS** com explicacao de risco — operador (e agente) precisa saber a diferenca.

### 12.7 Artefatos preservados (referencia da proxima sessao)

| Arquivo | Conteudo |
|---|---|
| `docs/inventario-2026-05/casos-pendentes/CASO_PENDENTE_RESERVAS_71_CODS_2026_05_24.md` | Doc completo (~280 linhas): pedido + auditoria + classificacao + gap + decisoes |
| `docs/inventario-2026-05/casos-pendentes/transferencias_indisp_2026_05_24.tsv` | 71 cods originais com qty solicitada |
| `docs/inventario-2026-05/casos-pendentes/audit_fb_indisp.json` | 190 quants brutos retornados pela Skill 9 (com reserved_quantity real) |
| `docs/inventario-2026-05/casos-pendentes/audit_indisp_classificado.json` | Classificacao detalhada dos 71 cods |
| `docs/inventario-2026-05/casos-pendentes/plano_etapa_A.tsv` | 95 chamadas Skill 2 modo A (cod/lote/qty) |
| `docs/inventario-2026-05/casos-pendentes/plano_etapa_B.tsv` | 67 chamadas Skill 2 modo B (cod/lote/qty) |
| Memoria `[[caso_real_tratar_reservas_pre_transferencia]]` | Resumo do caso + gap + roteiro retomada |

### 12.8 Confirmacao: zero writes em PROD

Auditoria: 1 chamada `consultar_quants.py` (READ-only via XML-RPC).
**Modificacoes Odoo PROD: zero.**
**Modificacoes banco PG PROD: zero.**
**Modificacoes filesystem PROD: zero.**
**Apenas: 5 arquivos copiados de `/tmp/` para `docs/inventario-2026-05/casos-pendentes/` (rastreabilidade) + doc/memoria/VALIDACAO §12 atualizadas (registro).**

### 12.9 Status final

- Caso PAUSADO no checkpoint "AskUserQuestion 3 decisoes pendentes"
- Plano A+B gerado e preservado, pronto para retomada
- Gap arquitetural REGISTRADO em 3 lugares (doc caso + memoria + esta §12)
- Sem commit — usuario decide na proxima sessao (priorizar gap fix vs retomar caso vs ambos)

---

## 13. Sessao 2026-05-24 v7: Gap reservas pre-transferencia RESOLVIDO — 4 atomos novos + fluxo 2.6 + G030

> Apos sessao v6.1 (caso 71-cods PAUSADO). Rafael escolheu P1 (caminho completo: implementar 4 gaps ANTES de retomar caso, transformando o caso em validacao do novo fluxo).

### 13.1 Cronologia

| # | Evento | Resultado |
|---|---|---|
| 1 | Setup + pytest baseline 196 verdes | OK |
| 2 | Verificacao main: nenhum commit novo (`fb494608` ja conhecido) | OK |
| 3 | AskUserQuestion sobre estrategia P1 vs P2 vs Skill 8 vs Skill 6 09b | Rafael escolheu P1 |
| 4 | **Fase A — Pesquisa AO VIVO** (probe `/tmp/investigar_unreserve_skill24.py`) | 4 descobertas chaves (vide 13.2) |
| 5 | **Fase B — Skill 9 extensao**: 2 atomos novos `listar_move_lines_por_quant`/`listar_pickings_por_quant` + CLI 2 modos + 19 pytest | OK |
| 6 | **Smoke C6 modo pickings**: FALHOU — Skill 9 retornou 30+ pickings com lixo (quants random) | **G030 DESCOBERTO** |
| 7 | Investigacao G030: `fields_get` revelou quant_id `store: False` | Documentado em gotchas/G030 |
| 8 | Fix codificado: cross-ref via TUPLA (product, lot, location, company) em vez de quant_id direto | 19 pytest verdes pos-fix |
| 9 | **Smoke C6 modo pickings pos-fix**: SUCESSO — 1 picking FB/INT/08022 com 3 MLs lote 13206 (1035.083 un) | 100% bate caso real |
| 10 | **Smoke C6 modo pickings MIGRAÇÃO**: 3 pickings (EMB MO ativa + OUT DEVOLUcaO LF) com 6 MLs | 100% bate auditoria v6.1 |
| 11 | **Fase C — Skill 2.4 extensao**: 2 atomos novos `unreserve_picking` (do_unreserve + guard G_UNRESERVE_TRAVA) + `find_orphan_mls` (READ-only via Skill 9) + CLI 2 modos + 14 pytest | OK |
| 12 | **Smoke C6 unreserve_picking**: dry-run FB/INT/08022 OK (n_mls=4); --confirmar em CD/OUT/02001 state=cancel = FALHA_STATE corretamente | Pre-state guard OK |
| 13 | **Smoke C6 find_orphan**: 3 quants lote 13206 = 0 orfaos (esperado — todos com saldo) | OK |
| 14 | **Fase D — Folha fluxo 2.6**: 5 caminhos seguros (A=cancel/B=devolver/C=unreserve/D=outro lote/E=cirurgia orfa) + regra selecao D→E→A→B→C + README dos fluxos atualizado | OK |
| 15 | **Fase E — Regra inviolavel no prompt + tabela 5-caminhos**: subagente `gestor-estoque-odoo` "PRE-CHECK reserva ANTES de Skill 2" + invariante G030; SKILL.md 2.4 estendida; SKILL.md 9 estendida com 3 contratos | OK |
| 16 | **Fase F — Validacao caso real**: AskUserQuestion estrategia α/β/γ/δ → Rafael escolheu β (cancelar 1 + pular 3) | OK |
| 17 | **WRITE PROD**: FB/INT/08022 (id=320753) cancelado via Skill 5 `--modo cancelar --confirmar` em 1.43s | EXECUTADO |
| 18 | **Verificacao direto no Odoo**: Skill 9 modo pickings → 0 pickings reservando os 3 quants. reserved=0 em todos 3 quants confirmado | ✅ |
| 19 | **Batch dry-run completo**: 84 chamadas MODO C — 79 DRY_RUN_OK + 5 falhas (1 LOTE_DESTINO_INEXISTENTE esperado + 4 FALHA_LOTE P-15/05) em 385s | OK |
| 20 | AskUserQuestion P-15/05: Rafael escolheu opcao 3 (executar 80 + tratar 4 P-15/05 via MODO B) | Plano confirmado |
| 21 | **Batch --confirmar MODO C principal**: 84 chamadas em 512s — **80 EXECUTADO em PROD** + 4 FALHA_LOTE (P-15/05 esperado) | ✅ |
| 22 | **Batch P-15/05 --confirmar MODO B**: 3 chamadas em 19s — **3 EXECUTADO em PROD** (208000043, 602000006, 208000044). 1 PULADO (105000003 — lote literal P-15/05 interpretado como proxy; tratar via Skill 1 ajustar_quant em sessao futura) | ✅ |
| 23 | **INCIDENTE OPERACIONAL**: por timing/race entre background do batch principal e smoke `--limite 3 --confirmar` rodado em paralelo + batch pt2 `--start 3` (matado mid-flight). Possivel duplicacao de items 12+13 (207030327+206030034) | DETECTADO |
| 24 | Auditoria duplicacoes via Skill 9 comparando qty_real vs qty_esperado: **2 duplicacoes confirmadas** (items 12+13 — 504 un cada). Items 1+2 do smoke nao chegaram a duplicar (qty_antes=0 do smoke = batch principal ja tinha reduzido) | OK |
| 25 | **REVERSAO 2 duplicacoes via Skill 1 ajustar_quant**: 4 chamadas (207030327 origem +504 + destino -504; 206030034 origem +504 + destino -504). Todas EXECUTADO | ✅ |
| 26 | Auditoria final pos-reversao: estados restaurados corretamente. **Total operacoes PROD validadas: 88 WRITES** (1 cancel + 80 Etapa A+B MODO C + 3 P-15/05 MODO B + 4 reversao) | ✅ |
| 27 | **Fase G — C7-C10**: ROADMAP atualizado, memoria nova G030 + fluxo_2_6_pattern, memoria caso atualizada (RESOLVIDO), VALIDACAO §13 atualizado pos-batch, logs PROD preservados em casos-pendentes/ | OK |

### 13.2 Descobertas Fase A (probe AO VIVO)

| # | Achado | Impacto |
|---|---|---|
| 1 | **G030**: `stock.move.line.quant_id` e' COMPUTED `store: False` (string UI "Pick From"). Filtro IGNORADO pelo Odoo CIEL IT. | Cross-ref ML→quant DEVE ser via TUPLA `(product, lot, location, company)`. Codificado em Skill 9. |
| 2 | `stock.picking.do_unreserve` e' XML-RPC publico, retorna None em state=cancel (NOOP silencioso) | Skill 2.4 `unreserve_picking` codifica + guard pre-state |
| 3 | `stock.picking._action_unreserve` NÃO EXISTE (Fault method does not exist) | Skill 2.4 usa SOMENTE `do_unreserve` |
| 4 | Caso real lote 13206: 1 picking FB/INT/08022 (Transferencia Interna, sem origem/partner, 3 MLs 1035.083 un) | Candidato natural caminho A (cancelar) |
| 5 | Caso real MIGRAÇÃO FB/Estoque: 3 pickings (FB/FB/EMB/11673+11674 MO ativa origin=FB/OP/MANUAL + FB/OUT/01046 DEVOLUÇÃO LA FAMIGLIA partner=LF) | Risco fiscal — caminhos D ou PULAR |

### 13.3 Metricas finais

- **4 atomos novos**: 2 READ (Skill 9 modo move-lines/pickings) + 2 WRITE (Skill 2.4 unreserve_picking + find_orphan_mls)
- **33 pytest novos**: 19 Skill 9 query (`test_stock_quant_query_service.py` NOVO) + 14 Skill 2.4 reserva (`test_stock_reserva_service.py` NOVO)
- **229 pytest verdes totais** (196 anterior + 19 query + 14 reserva = 229)
- **5 smokes PROD**: 2 Skill 9 (lote 13206 + MIGRAÇÃO FB) + 3 Skill 2.4 (unreserve dry-run + state=cancel falha + find_orphan zerados)
- **1 WRITE PROD validado**: Skill 5 cancelar FB/INT/08022 em 1.43s, verificacao direto no Odoo OK
- **1 NOVO fluxo**: `fluxos/2.6-tratar-reserva-bloqueia-transferencia.md` (~250 linhas, 5 caminhos, exemplo caso real)
- **1 NOVO gotcha**: G030 documentado em `docs/inventario-2026-05/02-gotchas/G030-quant-id-em-stock-move-line-eh-computed.md`
- **6 docs atualizados**: SKILL.md 9 + SKILL.md 2.4 + agente gestor-estoque-odoo (description+header+arvore+invariantes) + fluxos/README + ROADMAP_SKILLS + esta §13
- **2 memorias atualizadas**: `caso_real_tratar_reservas_pre_transferencia` (RESOLVIDO) + nova `gotcha_g030_quant_id_store_false` + MEMORY.md

### 13.4 Pre-mortem (4 dimensoes)

#### Riscos operacionais (impacto: PROD)

| Risco | Probabilidade | Impacto | Mitigacao atual |
|---|---|---|---|
| **Usuario chama Skill 2 sem PRE-CHECK reserva** | Baixa-Media | Alto (Odoo retorna erro qty<demanda OU transferencia incompleta) | Regra inviolavel no prompt + tabela 5-caminhos + fluxo 2.6. Sub-agente carrega no boot. |
| **Caminho C (unreserve) deixa picking TRAVADO em assigned** | Media (operacional) | Medio (precisa intervencao manual no Odoo UI) | Output emite "aviso G_UNRESERVE_TRAVA" + verifica `n_mls_depois==0`. Doc da skill recomenda caminho A se travar. |
| **Caminho A (cancelar) em picking fiscal sem consultar Fiscal** | Media | Alto (NF de devolucao invalidada) | Doc da skill alerta; fluxo 2.6 destaca `origin contendo "Devolução"` como red flag. Caso real v7: 3 pickings MIGRAÇÃO PULADOS (1 era DEVOLUcaO LF). |
| **Caminho E (cirurgia) sem `zerar_reserved_residual` apos** | Media | Medio (quant `reserved` negativo) | Doc da skill + fluxo 2.4 obriga zerar_residual apos cirurgia. Skill 2.4 expoe modo `--zerar-residual`. |
| **G030 reaparece** (Odoo CIEL IT upgrade muda `quant_id`) | Baixa | Alto (Skill 9 modo pickings retorna lixo silenciosamente) | Pytest cobrindo cross-ref via tupla. Doc G030. Probe `fields_get` em sessao futura se observar regressao. |

#### Riscos tecnicos (impacto: codigo + integracao)

| Risco | Probabilidade | Impacto | Mitigacao |
|---|---|---|---|
| **Domain compound OR-AND falha em Odoo 18+** | Baixa | Medio (Skill 9 modo pickings retorna vazio) | Codigo testado contra Odoo 17 CIEL IT. Sintaxe ['|']*(N-1) + N x [AND, AND, AND, AND] e' padrao OR canonico. |
| **`unreserve_picking` em picking com cancel cascade complicado** | Baixa | Medio (state pos imprevisivel) | Re-le state apos action. Output sempre inclui state_antes/depois. |
| **`find_orphan_mls` retorna FP em TOL muito pequeno** | Baixa | Baixo (extra cleanup desnecessario) | TOL=0.0001 (1e-4) testado contra valores reais 0.00005 vs 0.001. |

#### Riscos de processo (impacto: continuidade)

| Risco | Probabilidade | Impacto | Mitigacao |
|---|---|---|---|
| **Proxima sessao usa Skill 2 sem ler regra inviolavel** | Media | Medio (volta gap original) | Regra na 2a posicao da lista de invariantes do subagente; obrigatorio carregar no boot. |
| **Fluxo 2.6 nao documenta caminho NOVO descoberto** | Media | Baixo (operacao funciona, doc fica desatualizada) | Adicionar como sub-caso na proxima sessao real. |
| **Batch Etapa A+B nao executa em --confirmar nesta sessao** | Alta (intencional — alta carga) | Baixo (pode rodar em proxima sessao) | Dry-run completo + log preservado. Rafael decide quando executar real. |

#### Riscos arquiteturais (impacto: aposentar/refatorar)

| Risco | Probabilidade | Impacto | Mitigacao |
|---|---|---|---|
| **Atomos `unreserve_picking`/`find_orphan_mls` nunca usados** | Baixa | Baixo (cobertura defensiva) | Demanda comprovada pelo caso 71-cods. Pattern composavel para fluxos futuros. |
| **Skill 2.4 cresce alem de 5 atomos** (operador quer `unreserve_mo`) | Media | Baixo-Medio | Atomo `unreserve_mo` ja CATALOGADO no service. Adicionar quando demanda real surgir. |
| **Skill 9 vira batch monolitico** (operador quer `listar_pickings(filtros)` direto) | Baixa | Baixo | Atomo previsto `listar_pickings(states, type_ids, partner_ids)` mantido no catalogo. |

### 13.5 Aprendizados estruturais

1. **Probe AO VIVO ANTES de pytest mock-based eh INVARIANTE para Skill READ Odoo**: descoberto que minha hipotese inicial sobre `quant_id` estava errada por nao ter feito probe real. 16 pytest viraram 19 apos refactor pos-G030. **Adicionar como regra ao pattern de criar skill READ Odoo**.
2. **Pattern de gotcha "campo X e' computed store:False"**: campos many2one/many2many em Odoo CIEL IT podem ser computed UI-only. ANTES de filtrar via `('X', 'in', [...])` SEMPRE rodar `fields_get(model, ['X'], {'attributes': ['store']})`. Adicionar como checklist para novas skills READ.
3. **Composicao Skill 2.4 → Skill 9 (cross-skill READ)**: `find_orphan_mls` reaproveita `listar_move_lines_por_quant` internamente. Pattern reutilizavel: WRITE skill que precisa READ usa outra skill READ internamente, ao inves de duplicar logica.
4. **Demanda-driven validado novamente**: 4 atomos NOVOS nasceram do caso real 71-cods (gap real, nao especulativo). Skill 9 atomos previstos `listar_pickings(filtros)` permanecem ⬜ — implementar quando demanda surgir.
5. **Caminhos seguros tabela como pattern**: a tabela "5 caminhos A/B/C/D/E" da Skill 2.4 SKILL.md vira pattern para outras decisoes operacionais com risco variavel — abstraindo escolha tecnica em decisao de risco. Pattern reaproveitavel.
6. **Regra inviolavel no prompt do subagente como anti-regression**: codificar premissas operacionais (pre-check reserva) como invariante elimina riscos futuros sem precisar repetir o caso original.

### 13.6 Pendencias da sessao v7 (nao-bloqueantes)

1. **Batch Etapa A+B em `--confirmar` PROD**: ✅ EXECUTADO em v7 (CR2-H2 v7-fix). 80 chamadas MODO C em 512s + 3 P-15/05 MODO B + 4 reversoes (incidente race condition) = 87 transferencias efetivadas. Pendentes residuais: ver §13.9 (1 cod 105000003 + 5 cods MIGRACAO pulados). Log PROD preservado em `docs/inventario-2026-05/casos-pendentes/log_batch_71cods_PRINCIPAL_2026_05_24.json`.
2. **Code-review paralelo (2 reviewers)** sobre 4 atomos novos + fluxo 2.6 + SKILL.mds. Adicionar como pendencia se houver tempo proximo da sessao.
3. **Atomo `unreserve_mo`** (Skill 2.4) — implementar quando demanda real surgir (mrp.production.do_unreserve + opcao reassign).
4. **Atomo `listar_pickings(filtros)`** (Skill 9) — query independente de quant_ids, conforme demanda.
5. **Doc operacional "5 caminhos"** em formato visual (flowchart Mermaid?) — fluxo 2.6 ja tem tabela textual; visual opcional.
6. **Atualizar `caso_real_tratar_reservas_pre_transferencia` apos batch --confirmar** — adicionar evidencia do volume final.

### 13.7 Confirmacao: estado PROD

| Acao | Quantidade | Resultado |
|---|---|---|
| Skill 5 cancel FB/INT/08022 | 1 picking | ✅ EXECUTADO (1.43s, verificado direto no Odoo) |
| Skill 2 MODO C `--confirmar` (Etapa A+B atomic) | 80 chamadas em 512s | ✅ 80 EXECUTADO em PROD (lote_real → MIGRAÇÃO em FB/Indisponivel) |
| Skill 2 MODO B `--confirmar` (P-15/05) | 3 chamadas em 19s | ✅ 3 EXECUTADO em PROD (sem-lote FB/Estoque → FB/Indisponivel) |
| Skill 1 ajustar_quant `--confirmar` (reversao 2 duplicacoes) | 4 chamadas | ✅ 4 EXECUTADO em PROD (estados restaurados ao esperado pos-batch unico) |
| Skill 9 modo pickings (READ) | 4 smokes | OK (lote 13206 + MIGRAÇÃO + pos-cancel + auditoria 207030327/206030034) |
| Skill 9 modo quants (READ) | 5 smokes | OK (validacoes pre/pos varias) |
| Skill 2.4 unreserve_picking dry-run | 1 smoke | OK |
| Skill 2.4 find_orphan_mls (READ) | 1 smoke | OK |

**Modificacoes Odoo PROD: 88 WRITES** (1 cancel + 80 transferencias MODO C + 3 transferencias MODO B + 4 ajustes reversao).
**Modificacoes banco PG PROD: zero.**
**Modificacoes filesystem PROD: zero.**

### 13.8 Lição operacional: race condition em batch background

**Causa do incidente:** o batch principal `--confirmar` foi disparado em background; o `tee` buferizou silenciosamente o output (arquivo .log ficou vazio). Achei (incorretamente) que o batch tinha morrido. Em paralelo rodei:
1. Smoke `--limite 3 --confirmar` (foreground, 3 items)
2. Batch pt2 `--start 3` (background, items 4-84)

Quando o batch principal terminou (em 23:41), gerou log JSON normalmente. Mas a essa altura ja havia smoke (potencial duplicacao items 1-3) + pt2 (potencial duplicacao items 4-N).

**Auditoria detectou apenas 2 duplicacoes** porque:
- Items 1-3 do smoke: qty_antes=0 (batch principal ja tinha reduzido) → smoke deu EXECUTADO 2 + FALHA_REDUCAO 1
- Items 4-11 do pt2: mesma logica — items ja processados → FALHA_QUANT_NEGATIVO silencioso
- Items 12-13 do pt2: SALDO GRANDE (3000+, 11944+) permitiu segunda reducao = DUPLICOU
- Items 14-26 do pt2: smoke morto antes de chegar (foi morto mid-item 27)

**Reversao via Skill 1 ajustar_quant 2x por cod (origem +qty + destino -qty)** funcionou perfeitamente — Skill 1 com `--quant-id` direto e' o atomo mais simples e seguro para correcao cirurgica.

**Licoes:**
1. **NUNCA disparar batch background sem verificar se nao ha outro batch igual ja rodando** — adicionar `pgrep -f` no inicio do script para detectar.
2. **Logs JSON sao a fonte de verdade — `tee` em background pode falhar** sem aviso. Confiar no log JSON dentro do script Python.
3. **Auditoria pos-batch via Skill 9 e' INVARIANTE** — comparar qty_real vs qty_esperado_calculado detecta duplicacoes/perdas automaticamente.
4. **Skill 1 ajustar_quant `--quant-id N --delta X --confirmar`** e' a ferramenta mais segura para correcao individual de duplicacoes — usar em vez de re-rodar batch.

### 13.8.1 IMPLEMENTACAO das 3 melhorias evitam-repeticao (Q1+Q2+Q3 v7-extras)

Apos o incidente, implementei 3 melhorias evitam-repeticao (registradas em commit consolidado):

**Q1: `--quiet` em todos CLIs de skills estoque** (7 scripts atualizados via `_cli_utils.py`):
- `app/odoo/estoque/_cli_utils.py` NOVO — helper compartilhado com:
  - `silenciar_stdout()` context manager (suprime stdout + stderr + logging INFO/DEBUG durante create_app)
  - `criar_app_silencioso(quiet=False)` wrapper
  - `adicionar_args_padrao(ap)` adiciona --quiet + --forcar-concorrencia ao argparse
  - `setup_cli_completo(__file__, quiet, forcar)` setup unificado
- CLIs aplicados: ajustar_quant.py, transferir.py, operar_picking.py, operar_mo.py, operar_reserva.py, consultar_quants.py, planejar_pre_etapa.py
- Reducao observada: ~50 linhas/call → 0 linhas/call (apenas JSON output)
- Limitacao: 4 prints diretos no inicio (`✅ Tipos PostgreSQL`) acontecem ANTES do import de `setup_cli_completo` ser executado — sao do `from app import create_app` chain. Solucao parcial: redirect funciona apos esse ponto. Solucao completa exigiria wrapper bash que redireciona stdout do processo Python — postergado.

**Q2: `verificar_concorrencia(script_path)` via pgrep -f** (mesmo helper `_cli_utils.py`):
- Detecta processos concorrentes do MESMO script via `pgrep -f <basename>`
- Exclui PID atual + PPID (subshell)
- Retorna lista de PIDs concorrentes; vazia = OK
- `verificar_concorrencia_e_avisar(__file__, forcar=False)` emite aviso em stderr + retorna False
- `setup_cli_completo` chama-o automaticamente; sys.exit(2) se houver concorrencia sem --forcar-concorrencia
- Aplicado nos mesmos 7 CLIs via `setup_cli_completo`
- Override: `--forcar-concorrencia` flag prossegue mesmo com aviso (uso consciente em PROD)

**Q3: Regra inviolavel "EXECUTAR FLUXOS = subagente, não principal"** (em `.claude/agents/gestor-estoque-odoo.md`):
- Adicionada como 6a invariante (depois das 5 originais)
- Texto: "Para EXECUTAR fluxos sobre caso real (em vez de IMPLEMENTAR código novo), SEMPRE spawnar `gestor-estoque-odoo` via Task tool ao invés de orquestrar do agente principal."
- Justificativas codificadas: (1) prompt enxuto carrega árvore de decisão sob demanda — ~30-50% menos tokens; (2) regra PRE-CHECK reserva seguida automaticamente; (3) árvore de fluxos guia composição correta.
- Tambem adicionado: "USE `--quiet` em batches via subprocess" + "Log JSON é fonte de verdade (não `tee` background)".

**Esperado para v8:** se Rafael pedir EXECUTAR (ex.: rodar caso 105000003 pendente ou tratar 5 cods MIGRACAO), agente principal deve SPAWNAR subagente — nao orquestrar diretamente. Tokens estimados: ~40-60k para caso de tamanho similar a F (88 writes), vs ~150k da v7.

### 13.9 Pendencias residuais (apos sessao v7)

| Item | Quantidade | Acao recomendada |
|---|---|---|
| Cod 105000003 (P-15/05 literal) | 1 cod (qty 430 do plano) | Skill 1 ajustar_quant no quant_id=261857 + ajustar_quant +430 no destino MIGRAÇÃO Indisp |
| Cod 4739199 (FALHA_QUANT_NEGATIVO no smoke) | 1 cod (qty 362.75) | Investigar saldo atual; pode ja ter sido processado pelo batch principal |
| Cods MIGRAÇÃO pulados (estrategia β) | 5 cods | Rafael decide: cancelar pickings (caminhos A/B do fluxo 2.6) ou aceitar saldo bloqueado |
| Plano Etapa B (transferir MIGRAÇÃO FB/Estoque → FB/Indisp) | 67 chamadas | NÃO necessario — MODO C ja faz isso atomic em Etapa A+B unica. Plano B pode ser descartado. |

---

## 14. Sessao 2026-05-25 v8: 13 pendencias residuais resolvidas (8 PARCIAL + 5 MIGRACAO) + cirurgia FB/OUT/01046

> Apos sessao v7-extras (commit 507e5e36). Rafael pediu "transfira os 8 pendentes + os 5 MIGRACAO". Auditoria 71 cods identificou status real, batch v8 fechou 11 cods diretamente, cirurgia FB/OUT/01046 destravou os 3 ultimos.

### 14.1 Cronologia

| # | Evento | Resultado |
|---|---|---|
| 1 | Auditoria 71 cods (`/tmp/auditar_71cods.py`) consolidando logs v7+v7-P-15/05 | 54 OK + 8 PARCIAL + 5 MIGRACAO PULADO + 4 SKIP_planejado |
| 2 | Investigacao alternativas para 5 MIGRACAO via Skill 9 | 3 cods (103000113, 105000021, 105000038) tem outros lotes livres (caminho D); 2 cods (103000117, 104000054) parcialmente cobertos pelo D |
| 3 | Plano consolidado: 20 chamadas (14 MODO C + 6 Skill 1) | Dry-run 20/20 OK em 94s |
| 4 | Batch v8 `--confirmar`: 20 chamadas PROD | **20/20 EXECUTADO em 116s** — todas as transferencias planejadas |
| 5 | Auditoria pos-v8 | 65 OK + 2 PARCIAL (103000117 + 104000054 ainda bloqueados por FB/OUT/01046) + 4 SKIP_planejado |
| 6 | Rafael consulta: picking FB/OUT/01046 foi revertido na realidade — "ajuste o estoque" | Decidiu: cirurgia (preserva picking) em vez de cancelar |
| 7 | Investigacao AO VIVO do picking FB/OUT/01046 | **23 MLs** (nao 3!) — 20 sao devolucoes validas de outros cods + 3 sao os bloqueantes |
| 8 | Identificacao moves parent: cada uma das 3 MLs alvo tem move 1:1 (1161587/103000117, 1161611/103000113, 1161613/104000054) | Cirurgia segura: unlink 3 MLs + zerar product_uom_qty dos 3 moves |
| 9 | Cirurgia (Skill 2.4 cancelar_moves_orfaos) | CIRURGIA_OK em 1.24s — 3 MLs unlinked, 3 moves zerados, picking preservado com 20 MLs validas |
| 10 | Zerar reserved residual (Skill 2.4) | ZERAR_RESIDUAL_OK em 0.75s — 3 quants com reserved=0 |
| 11 | 3x Skill 2 MODO C transferindo lote MIGRACAO livre para FB/Indisp | 3/3 EXECUTADO (890.4646 un total) |
| 12 | Auditoria final consolidando v7+v7-P-15/05+v8+cirurgia | **67/67 cods executaveis OK (100%) + 4 SKIP planejados** = 71/71 conforme plano |

### 14.2 Metricas finais (v7 + v7-extras + v8 + cirurgia)

| Operacao | Volume |
|---|---:|
| Cancel FB/INT/08022 (Skill 5 v7) | 1 picking, 3 MLs lote 13206 desbloqueado |
| Skill 2 MODO C batch principal (v7) | 80 chamadas, ~13k un, 512s |
| Skill 2 MODO B P-15/05 (v7) | 3 chamadas, 2.458 un, 19s |
| Skill 1 reversao duplicacoes (v7 incidente race condition) | 4 ajustes, 504 un cada |
| Skill 2 MODO C + Skill 1 batch v8 residuais | 20 chamadas, ~5.940 un, 116s |
| Skill 2.4 cirurgia FB/OUT/01046 (v8) | 1 cirurgia (3 MLs unlinked + 3 moves zerados) |
| Skill 2.4 zerar_reserved_residual (v8) | 3 quants residuais |
| Skill 2 MODO C destravamento pos-cirurgia (v8) | 3 chamadas, 890.46 un |
| **TOTAL JORNADA** | **~115 writes PROD, ~22.500 un transferidas para FB/Indisponivel** |

### 14.3 Estado final do plano (71 cods → FB/Indisp)

- **67 cods OK_TOTAL** (100% dos executaveis)
- **4 SKIP planejados** desde inicio (103 PEPINO, 46 VINAGRE TRIPLO sem saldo; X105000022 descontinuado X-prefix; 301000003 em FB/Pos-Producao)
- **0 PARCIAL** (todas pendencias resolvidas)
- **0 FALHA**

### 14.4 Cirurgia FB/OUT/01046 — consistencia tecnica

**Antes:** picking state=assigned, 23 MLs, 3 MLs bloqueando quants MIGRACAO FB/Estoque (103000117 620.32 + 103000113 14.35 + 104000054 255.79 un).

**Apos cirurgia:**
- 23 MLs → 20 MLs (3 unlinked)
- 3 moves (1161587/1161611/1161613) com product_uom_qty=0, state=assigned ainda
- Picking continua state=assigned, processavel normalmente
- Quants origem: reserved=0 (apos zerar_reserved_residual)
- Lotes MIGRACAO livres → transferidos via MODO C (890 un para MIGRACAO FB/Indisp)

**Consequencia operacional:** quando operador validar o picking via Odoo UI, as 20 MLs validas processam normalmente. Os 3 moves com qty=0 ficam pendurados ate o operator processar — Odoo limpa automaticamente em alguns fluxos (cancel automatico em moves com qty=0 apos validate). Se o operador fiscal quiser limpar 100%, pode cancelar manualmente os 3 moves no Odoo UI (cosmetico, nao-urgente).

**Por que essa abordagem (e nao outra):**
- Cancelar picking inteiro (Skill 5 cancelar): perderia as 20 MLs validas de devolucoes de outros cods
- do_unreserve no picking (Skill 2.4 unreserve_picking): liberaria TODAS as 23 MLs (incluindo as 20 que precisam permanecer reservadas)
- Cirurgia: unico caminho que **preserva picking + libera quants alvo + impacto auditavel**

### 14.5 Licoes operacionais reforcadas

1. **Cirurgia (Skill 2.4 cancelar_moves_orfaos) eh PREFERIDA sobre Skill 5 cancelar quando picking tem MIX MLs validas + bloqueantes** — adicionada como invariante no fluxo 2.6 caminho E.
2. **Auditoria pre-tratamento ALWAYS via Skill 9 modo pickings** — descobriu 23 MLs (nao 3 como assumido apenas pelos 5 cods MIGRACAO). Skill 5 cancelar teria causado dano.
3. **Pattern "cirurgia → zerar residual → MODO C"** — composicao de 3 skills resolve o caso completo. Codificar como receita explicita no fluxo 2.6.
4. **Caminho D (outro lote alternativo) eh o MAIS SEGURO** — 11 cods MIGRACAO resolvidos no v8 sem mexer em picking, apenas usando lotes alternativos livres. Aplicavel em ~60-70% dos casos quando estoque distribuido em multiplos lotes.

### 14.6 Confirmacao: estado PROD

| Acao | Quantidade | Resultado |
|---|---|---|
| Batch v8 (20 chamadas) | 14 MODO C + 6 Skill 1 | ✅ 20/20 EXECUTADO |
| Cirurgia FB/OUT/01046 | 1 cirurgia | ✅ CIRURGIA_OK (3 MLs + 3 moves) |
| Zerar reserved residual | 3 quants | ✅ ZERAR_RESIDUAL_OK |
| MODO C destravamento | 3 chamadas | ✅ 3/3 EXECUTADO (890 un) |
| Auditoria final 71 cods | comparacao | ✅ 67/67 executaveis OK + 4 SKIP planejado = 100% |

**Modificacoes Odoo PROD v8: 24 writes** (20 batch + 1 cirurgia + 3 MODO C destravamento; zerar_residual eh complemento de cirurgia).
**Modificacoes banco PG PROD: zero.**
**Modificacoes filesystem PROD: zero.**

**Total acumulado da jornada (v7 + v7-extras + v8): ~115 writes PROD.**

### 14.7 Pendencias residuais (apos v8 + cirurgia)

- **3 moves do picking FB/OUT/01046 com qty=0** (cosmetico): aguardam validacao manual no Odoo UI pelo time fiscal. Nao bloqueia operacao.
- **NENHUMA pendencia operacional** do plano 71 cods.

---

## 15. Sessao 2026-05-25 v9: 09b capinado → orchestrator C3 macro Skill 6 (ciclo completo)

### 15.1 Contexto

Plano da sessao v9: capinar `09b_executar_pre_etapa.py` (746 LOC, executor da pre-etapa Onda 5/6 — composicao C3 macro de Skills 1+2) para `app/odoo/estoque/orchestrators/pre_etapa_executor.py`, fechando o ciclo da Skill 6 (planejar→propor→listar→aprovar→executar).

**Foco escolhido por Rafael (AskUserQuestion)**: Foco C — Capinar 09b. Estimativa ~3-4h. Risco BAIXO (sem SEFAZ; pattern ja validado em PROD em sessoes anteriores).

### 15.2 Mudancas realizadas

| Tipo | Item | Detalhes |
|------|------|---------|
| **CRIAR** | `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (~580 LOC) | Orchestrator C3 macro. Entry-point `executar_onda_pre_etapa()`. Compoe Skills 1 (`StockQuantAdjustmentService.ajustar_quant` para PURO com guard delta_esperado=qty) + 2 (`StockInternalTransferService.transferir_quantidade_para_lote_v2` para POS/NEG com delta_esperado propagado em `-origem`/`+destino`). Mantem auditoria via `OperacaoOdooAuditoria.registrar` + paralelizacao via `ThreadPoolExecutor` (cada thread cria app_context + conexao Odoo + svcs proprios). |
| **CRIAR** | `tests/odoo/services/test_pre_etapa_executor_orchestrator.py` (21 testes) | Helpers (`_resolver_product_id`, `_buscar_quants_produto_cid`, `_localizar_doador`), `_avaliar_sucesso_v2`, execucao individual dry-run (`_executar_transferencia_interna` doador OK / sem doador / insuficiente; `_executar_positivo_puro` dry-run validando guard delta_esperado propagado para Skill 1), entry-point (`executar_onda_pre_etapa` FALHA_USO company_id invalido, FALHA_NENHUM_APROVADO ciclo inexistente), constantes (ACOES_INTERNAS_POR_CID, ACAO_AUDIT_CURTA, LOTE_MIGRACAO). |
| **MODIFICAR** | `.claude/skills/planejando-pre-etapa-odoo/scripts/planejar_pre_etapa.py` | Adicionado modo `executar-onda` (5o modo). Funcao `modo_executar_onda(args)`. Args novos: `--limite`, `--cod-produto`, `--max-workers`. Status novos: `EXECUTADO_ONDA`, `DRY_RUN_OK_EXECUTADO`, `FALHA_NENHUM_APROVADO`. Atualizados `_FALHAS_STATUS`, `_REAL_OKS`, `_DRY_OKS`. |
| **MODIFICAR** | `.claude/skills/planejando-pre-etapa-odoo/SKILL.md` | Header v6→v9 (5 modos). Frontmatter `description` atualizada (executar-onda + triggers novos). Contrato `executar-onda` completo (objeto/input/output/pre-cond/pos-cond/gotchas/modos/status). Receitas: 5 linhas novas (canary/sub-piloto/bulk/single produto/preview). Sub-fluxo 4.1.e adicionado. Armadilhas executar-onda (5 novas). Exemplos 9-13 novos. Validacao: 22→48 testes/smokes. NAO-FAZER: 3 red flags executar-onda novos. |
| **MODIFICAR** | `app/odoo/estoque/fluxos/4.1-pre-etapa-cd-d007.md` | Titulo: 4 modos→5 modos. Passo F reescrito (orchestrator desta skill). G-PRE-10 reescrito (orchestrator C3 v9). Exemplo passo 7 atualizado. Sub-caso 4.1.e (executar Onda APROVADA, 9 passos). Cross-skill: Skill 1+2 menciona v9 + orchestrator. |
| **MODIFICAR** | `.claude/agents/gestor-estoque-odoo.md` | `description` atualizada (executor C3 + Skills 1+2). Header v7→v9 (executar-onda + orchestrator). Galho 4.1 atualizado (5 modos + orchestrator). |
| **MOVER** | `scripts/inventario_2026_05/09b_executar_pre_etapa.py` → `_validados/planejando-pre-etapa-odoo/` | `git mv`. Header ARQUIVADO adicionado (aviso + receita Skill 6 + diferencas vs capinado). sys.path corrigido `parents[2]→parents[4]`. Smoke import museum vivo verde para 3 arquivos (03b+04b+09b). |
| **MODIFICAR** | `scripts/inventario_2026_05/_validados/planejando-pre-etapa-odoo/VALIDACAO.md` | Header v6→v9. 09b movido de VIVO para SUPERADO (com detalhes da composicao Skills 1+2 + 21 testes pytest + 3 smokes CLI). Cobertura: 22→48 testes/smokes. C7-C10 marcados como concluidos v6+v9. |
| **MODIFICAR** | `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md` | Secao pre_etapa.py renomeada para incluir `orchestrators/pre_etapa_executor.py`. Linha 09b: status VIVO→SUPERADO 2026-05-25 v9 com detalhes da composicao. |
| **MODIFICAR** | `app/odoo/estoque/ROADMAP_SKILLS.md` | HANDOFF: secao "Sessao 2026-05-25 v9" adicionada com 11 bullets. Baseline 230→251. Status global: 16 scripts SUPERADOS (era 15). Secao SKILL 6: titulo atualizado (5 modos), checkpoints C1-C10 expandidos com detalhes v9, status global → 🟡 mín viável COMPLETA. |
| **MODIFICAR** | `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` (este arquivo) | Secao §15 nova. |

### 15.3 Decisoes-chave

**Decisao 1: API v2 propagada vs reutilizar v1 legado.**
- 09b legacy chamava `transferir_quantidade_para_lote` (v1 — sem guard delta_esperado). v2 (`transferir_quantidade_para_lote_v2`) delega para `ajustar_quant`x2 com `delta_esperado=±qty` propagado em ambos passos.
- **Decisao**: usar v2 sempre — guard CICLAMATO ativo protege contra bug operacional (politica homogenea em retomada de FALHA).
- **Trade-off**: v2 e' ~10% mais lenta que v1 (2 calls a `ajustar_quant`). Aceito — robustez > velocidade marginal.

**Decisao 2: PURO via Skill 1 vs `odoo.create('stock.quant')` direto.**
- 09b legacy fazia `odoo.create('stock.quant', {...})` + `action_apply_inventory` DIRETO (sem usar Skill 1).
- **Decisao**: refatorar para `quant_svc.ajustar_quant(criar_se_faltar=True, delta_esperado=qty)` — guard CICLAMATO + identificacao via tupla (product, company, location, lot) consistente com resto do sistema.
- **Trade-off**: ligeiramente mais chamadas internas (resolve lote -> ajusta), mas mesma quantidade de calls XML-RPC.

**Decisao 3: Helpers privados no orchestrator (nao expor como skills).**
- `_resolver_product_id`, `_buscar_quants_produto_cid`, `_localizar_doador`, `_avaliar_sucesso_v2` permanecem PRIVADOS no orchestrator (prefixo `_`).
- **Razao**: sao especificos do flow pre-etapa (estrutura ajuste_estoque_inventario + lote_origem/destino por nome). Promover a skills genericas seria precoce.

**Decisao 4: Auditoria via `OperacaoOdooAuditoria` preservada.**
- 09b legacy registrava em `operacao_odoo_auditoria` com `pipeline_etapa='ONDA_5_PRE_ETAPA'` + external_id unico por ajuste.
- **Decisao**: preservar 100% — auditoria e' usada para rastrear cada ajuste tocado em PROD. Sem auditoria, retomada de FALHAs perde contexto.

**Decisao 5: Paralelizacao via `ThreadPoolExecutor` preservada.**
- 09b legacy ja suportava `--max-workers` (default 1 serial; 5 para bulk ~5x).
- **Decisao**: preservar pattern exato. Cada thread cria app_context + conexao Odoo + svcs (Skill 1+2) proprios — Flask-SQLAlchemy scoped session funciona corretamente.
- **Nota**: documentar trade-off `max_workers > 5` sobrecarrega Odoo XML-RPC (rate limit) — esta na armadilha v9 do SKILL.md.

### 15.4 Smokes C6 detalhes

**Smoke 1**: company_id invalido (999) → argparse rejeita em `choices=[4, 1]` antes mesmo de chamar a funcao. Exit 2. **DUPLA validacao**: argparse + `executar_onda_pre_etapa` ambos checam.

**Smoke 2**: ciclo inexistente (`CICLO_INEXISTENTE_TEST_v9`) → query AjusteEstoqueInventario retorna []. Resposta: `status=FALHA_NENHUM_APROVADO`, `ajustes_total=0`, `produtos_total=0`, tempo 869ms. Exit 1. JSON estruturado salvo em `scripts/inventario_2026_05/auditoria/log_skill6_pre_etapa_executar_onda_dryrun_20260525_012909.json`.

**Smoke 3 (REAL dry-run)**: ciclo INVENTARIO_2026_05 cid=4 → encontrou **1 ajuste APROVADO real** (id=163696, cod=208000012, product_id=28108, NEG, qty=835.851,71). Dispatch correto:
- `produtos[0].pos_total=0, neg_total=1, puro_total=0` ✓
- `neg_results[0].resultado.sucesso=None` (dry-run nao confirma) ✓
- `neg_results[0].resultado.plano.status=DRY_RUN_OK` (Skill 2 v2 OK em dry-run) ✓
- `plano.lot_id_origem=None` (P-15/05 quant sem lote) ✓
- `plano.lot_id_destino=56779` (MIGRAÇÃO resolvido via `resolver_lote_destino` com `criar_se_faltar=False` em dry-run) ✓
- Tempo: 1.9s (Odoo conectado UID=42 + read quants + dry-run composto)
- Exit 4 (DRY_RUN_OK_EXECUTADO) ✓

**Confirmado**: composicao Skill 2 v2 + guard delta_esperado propagado + auditoria + dispatch por `acao_decidida` funcionam end-to-end em dry-run real.

### 15.5 Pendencias residuais (apos v9)

- **NENHUMA pendencia operacional** — Skill 6 5 modos completos.
- **Smoke `--confirmar` real em PROD**: nao executado nesta sessao porque so havia 1 ajuste APROVADO (id=163696 valor alto 835k un — exige aprovacao explicita do Rafael antes). Pattern ja validado em PROD em sessoes anteriores via 09b legacy.
- **Pyright warnings cosmeticos** em `pre_etapa_executor.py`: 3 imports `app.odoo.estoque.*` nao resolvem (PYTHONPATH falso positivo) — runtime OK.
- **`--quiet` nao suprime 100% dos logs Flask** (~30 linhas escapam antes do silenciar_stdout context) — nao bloqueador (JSON output preservado).

### 15.6 Confirmacao: estado PROD apos v9

| Acao | Resultado |
|---|---|
| Modificacoes Odoo PROD em v9 | **ZERO** (apenas dry-runs) |
| Modificacoes banco PG PROD em v9 | **ZERO** (apenas reads do AjusteEstoqueInventario) |
| Modificacoes filesystem PROD em v9 | 4 logs JSON em `scripts/inventario_2026_05/auditoria/log_skill6_pre_etapa_executar_onda_dryrun_*.json` (auditoria das smokes; nao toca dados de negocio) |
| Pytest baseline v9 | 230 → **258 verdes** (+21 orchestrator + 7 code-review fixes) |
| Arquivos modificados | 14 (CRIAR: 2 + MODIFICAR: 11 + MOVER: 1) |

### 15.8 Code Review (commit 6a73c6fa)

Code-reviewer (Agent feature-dev:code-reviewer) detectou **8 findings reais** no commit `6a73c6fa`. **Todos os 8 aplicados** em commit subsequente. Resumo:

| Finding | Severidade | Tipo | Arquivo:Linha | Fix |
|---|---|---|---|---|
| BUG-1 | HIGH | Dry-run engana operador | `pre_etapa_executor.py` `_executar_positivo_puro` | Guard `DRY_RUN_OK_LOTE_A_CRIAR` quando lote_destino nominal nao existe (em vez de chamar Skill 1 com `lot_id=None` que simularia ajuste no proxy P-15/05) |
| BUG-2 | HIGH | Contador `produtos_ok` em dry-run | `pre_etapa_executor.py` `_processar_produto` else fallback | Separar semantica via novos contadores `produtos_dry`, `produtos_sem_ajuste`, `pos/neg/puro_dry`. Caso "anomalia em modo real" loga warning |
| EDGE-1 | HIGH | In-place doador[quantity] entre POS+NEG | `pre_etapa_executor.py` `_executar_transferencia_interna` docstring | Docstring expandida documentando comportamento intencional + edge case dry-run (sem decremento) que pode mostrar OK em sequencias inviaveis |
| PATTERN-1 | HIGH | `EXECUTADO_AUTO_CORRIGIDO` dead code | `pre_etapa_executor.py` `_avaliar_sucesso_v2` | Removido do set de sucesso (flat status v2 nunca propaga). Docstring atualizado sem ref a linha hardcoded |
| EDGE-2 | MED | `sucesso=None` em dry-run nao incrementa nenhum contador | (corrigido com BUG-2) | Novos contadores `*_dry` distinguem dry-run de NOOP real |
| EDGE-3 | MED | `expire_all()` sem `commit()` previo pode ler stale | `pre_etapa_executor.py` `executar_onda_pre_etapa` docstring | Pre-condicao "sessao caller deve estar limpa" documentada |
| DOC-1 | LOW | Docstring referencia "linha 542 transfer.py" desatualizada | `pre_etapa_executor.py:336-337` | Substituida por nome de funcao (`transferir_entre_lotes_v2`) |
| PATTERN-2 | LOW | `ACAO_AUDIT_CURTA` duplicada em orchestrator | `pre_etapa_executor.py:54-61` + `pre_etapa.py` | Movida para `pre_etapa.py` (fonte unica) + gerador programatico a partir de `ACOES_INTERNAS_POR_CID`. Preserva nomes legacy 09b validado por novo pytest |

**Smoke pos-fix validou BUG-2** (`/tmp/smoke_pos_fix_v9.json`):
- Antes (v9 sem fix): `contadores={produtos_ok=1, neg_ok=0, ...}` (semanticamente confuso — 1 produto OK com 0 ajustes confirmados em dry-run)
- Pos-fix v9: `contadores={produtos_ok=0, produtos_dry=1, neg_dry=1, ...}` (claro — 1 produto em dry-run, 1 ajuste NEG simulado)

**7 testes pytest novos** cobrindo fixes: `test_acao_audit_curta_importada_de_pre_etapa`, `test_acao_audit_curta_preserva_nomes_legacy_09b`, `test_executar_positivo_puro_dry_run_lote_inexistente_nao_engana`, `test_executar_positivo_puro_dry_run_lote_p15_nao_dispara_guard_bug1`, `test_avaliar_sucesso_v2_simplificado_sem_auto_corrigido`, `test_contadores_iniciais_incluem_dry_e_sem_ajuste`, `test_novos_contadores_fabrica_dicts_independentes`. **Baseline pytest: 251 → 258 verdes.**

### 15.9 Pre-mortem (4 dimensoes — 6 meses adiante)

Cenarios imaginados de "como `executar-onda` pode falhar em PROD" — usado para guiar v10 + sessoes futuras.

#### Dimensao 1: Bugs reais que podem aparecer em PROD

- **PM-1 (MITIGADO v9)**: dry-run mostra ajuste em proxy P-15/05 mas em --confirmar vai para lote nominal recem-criado → confunde operador. Mitigado por BUG-1 fix (guard `DRY_RUN_OK_LOTE_A_CRIAR`).
- **PM-2 (PARCIAL)**: bulk de 100+ produtos sem `--quiet` polui logs com ~30 linhas de boot Flask por chamada. Mitigado parcialmente (`--quiet` reduz mas nao zera). Operadores em PROD usar `--quiet` SEMPRE.
- **PM-3 (LATENTE)**: paralelizacao `max_workers > 5` sobrecarrega Odoo XML-RPC (rate limit + timeouts SSL G016). Documentado em armadilhas mas NAO enforced no codigo. Risco: operador passa `--max-workers 20` por engano e quebra Odoo PROD. Mitigacao futura: clamp automatico no codigo (`min(max_workers, 5)`) + warning.
- **PM-4 (LATENTE)**: doador in-place updated entre POS+NEG do mesmo lote. Se plano original previu mais qty do que o lote tem, ajustes subsequentes falham com mensagem "quant origem X tem Y un". Documentado em docstring CR-EDGE-1, mas operador pode interpretar como bug e tentar workaround errado.
- **PM-5 (LATENTE)**: `OperacaoOdooAuditoria.registrar` em lazy import com try/except amplo. Se falhar (DB down, schema migrado), perde registro de auditoria silenciosamente. Em pos-incidente pode haver gap. Mitigacao futura: re-raise em modo `--strict-audit`.

#### Dimensao 2: Limitacoes descobertas tarde

- **PM-6**: nao ha retry interno em XML-RPC failure. Cada chamada `ajustar_quant`/`transferir_quantidade_para_lote_v2` sem retry — timeout temporario do Odoo causa FALHA imediata. **Mitigacao**: hook `tenacity` retry em sessao futura quando padrao se repetir.
- **PM-7**: ausencia de telemetria de progresso. Bulk de 1000 produtos pode rodar 30 minutos sem feedback. Operador nao sabe se travou ou se esta processando. **Mitigacao**: progress callback opcional (impressao a cada 10 produtos) em sessao futura.
- **PM-8**: retomada de FALHAs requer operador alterar `ajuste.status='FALHA'` -> `'APROVADO'` manualmente em SQL ou via UI. Nao ha CLI `--modo re-aprovar-falhas`. Risco: operador esquece de re-aprovar e ajustes ficam FALHA para sempre.
- **PM-9**: composicao via `transferir_quantidade_para_lote_v2` chama 2 vezes XML-RPC (`ajustar_quant` x2). Bulk de 1000 POS+NEG vira 4000 calls XML-RPC (vs 2000 do legacy v1). Perdas de performance ~2x em batches grandes.

#### Dimensao 3: Decisoes que podem se mostrar erradas

- **PM-10**: helpers privados `_resolver_product_id`, `_buscar_quants_produto_cid`, `_localizar_doador` NAO promovidos a skills. Risco: orchestrator Skill 8 faturando vai precisar dos mesmos helpers e duplicara. Mitigacao em v10: avaliar promover para `consultando-quant-odoo` (Skill 9) ou `_utils.py`.
- **PM-11**: lazy imports `from app import db` dentro de funcoes. Pattern correto para tests sem app, mas overhead pequeno acumula em bulks. Verificar se PROD reclamar.
- **PM-12**: contador `produtos_sem_ajuste` em modo REAL acompanhado de warning loga, mas operador pode ignorar warning no JSON. Mitigacao: bubble-up para status agregado se `produtos_sem_ajuste > 0`.

#### Dimensao 4: O que falta para `executar-onda --confirmar` funcionar 100% em PROD

1. **Canary REAL ainda nao executado** (1 ajuste APROVADO id=163696 NEG 835k un MIGRAÇÃO em CD). Foco C da v10 cobre.
2. **Retry em XML-RPC failure** (PM-6) — proximo refactor.
3. **Cap automatico max_workers** (PM-3) — fix trivial em sessao futura.
4. **CLI re-aprovar-falhas** (PM-8) — modo 6 da Skill 6 quando demanda.
5. **Telemetria de progresso** (PM-7) — nice-to-have.

### 15.10 Decisoes-chave v9 (revisitando pos-CR + pre-mortem)

- **Decisao 6 (NOVA — CR v9)**: dry-run NUNCA simula ajuste no quant errado para "parecer que funcionou". Se ha incerteza sobre o estado real (lote nao existe), retornar status especifico (`DRY_RUN_OK_LOTE_A_CRIAR`) e dar visibilidade total ao operador. Aplicavel a TODAS as skills WRITE futuras.
- **Decisao 7 (NOVA — CR v9)**: contadores devem ter semantica DISTINTA para dry-run vs NOOP real vs anomalia. Nunca colapsar "tudo zero" em `produtos_ok`. Aplicavel a TODAS as skills WRITE com composicao.
- **Decisao 8 (NOVA — CR v9)**: constantes que cruzam multiplos modulos vivem em UM lugar so (fonte unica). Importar via `from`, nunca duplicar. Aplicar `ACAO_AUDIT_CURTA` como exemplo + adicionar regra ao CLAUDE.md modulo.

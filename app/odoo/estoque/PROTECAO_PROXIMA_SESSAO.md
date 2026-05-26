# PROTEÇÃO DAS PRÓXIMAS SESSÕES do orquestrador-Odoo

**Criado em:** 2026-05-26 v18 (Fase 0 — após auditoria Rafael sobre desvios documentais acumulados em ~10 sessões).
**Audiência:** Claude Code (dev) + agente web em qualquer sessão futura tocando `gestor-estoque-odoo` / `app/odoo/estoque/`.
**Status:** VIVO — sessão que detectar novo antipadrão DEVE atualizar este documento ANTES do commit final.

> **Por que este documento existe**: nas 10 sessões anteriores, o catálogo §6 da constituição misturou "skill atômica L2" com "orchestrator C3 macro". Isso legitimou que Skill 8 `faturando-odoo` violasse o princípio fundador §1 (1 skill = 1 átomo). Resultado: v17 colocou 420 LOC inline em ETAPA E (1 sessão inteira para reverter). v17.5 deixou ETAPA F com Skill 5 atomo inline (antipadrão 2). v18 G037 criado com premissa errada por não ler docstring de constants. Este documento é o ESCUDO contra repetir esses desvios.

---

## ANTES DE QUALQUER COISA, LEIA NESTA ORDEM

1. **Este documento INTEIRO** (você está nele). Especialmente "NUNCA FAZER" e "ANTIPADRÕES REINCIDENTES".
2. `app/odoo/estoque/CLAUDE.md` §1 (princípio fundador) + §3 (contrato átomo) + §6 (catálogo) + §6.5 (antipadrões) + §14 (histórico de desvios).
3. `.claude/agents/gestor-estoque-odoo.md` (subagente — antipadrões + loop + árvore).
4. `app/odoo/estoque/ROADMAP_SKILLS.md` (estado atual + próximo passo APENAS — histórico em VALIDACAO).
5. `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` §0 (se for Skill 8).
6. `app/odoo/constants/operacoes_fiscais.py` **header** (60 linhas iniciais — MATRIZ_INTERCOMPANY + regra de CFOP por tipo).
7. `app/odoo/constants/picking_types.py` **header** (15 linhas iniciais — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO).

**Se pular qualquer um destes**, você reincide nos antipadrões abaixo.

---

## NUNCA FAZER (lista negra inviolável)

| # | Antipadrão | Por que é proibido | Onde a regra mora |
|---|------------|---------------------|-------------------|
| N1 | Skill L2 com 2+ objetos Odoo | Viola §1 ("1 skill = 1 átomo") + §3 ("átomo NUNCA embute outro fluxo") | CLAUDE.md §1+§3 |
| N2 | Orchestrator C3 invocando outra skill INLINE no orchestrator | Viola §6 — composição = FLUXO L3, NÃO inline | CLAUDE.md §3 + §6.5 antipadrão 3 |
| N3 | `raise NotImplementedError` em pre-cond de átomo (V1 STRICT) | API footgun — operador não consegue dry-run hipotético | CLAUDE.md §6.5 antipadrão 4 |
| N4 | Criar script ad-hoc em `scripts/inventario_2026_05/` | Inteiro objetivo do orquestrador é eliminar scripts ad-hoc | CLAUDE.md §0 |
| N5 | Hardcodar CFOP em código (`l10n_br_cfop_id=5949`) | Motor fiscal Odoo deriva via `fiscal_position_id` + `l10n_br_tipo_pedido` | `operacoes_fiscais.py:17,119` |
| N6 | Adicionar invariante histórica no prompt do subagente ("NOVA v7 — lição XYZ") | Prompt é essencial atemporal; lições viram `[[memory-pattern]]` | gestor-estoque-odoo.md |
| N7 | Adicionar bloco "Sessao XYZ" no ROADMAP HANDOFF | HANDOFF = estado atual + próximo passo; histórico em VALIDACAO | ROADMAP_SKILLS.md topo |
| N8 | Comentar deprecated mantendo constant ativa no código | L0 = dados, sem semântica histórica. Remove e atualiza callers | CLAUDE.md §2 (L0) |
| N9 | Criar gotcha sem ler `operacoes_fiscais.py` + `picking_types.py` INTEIROS | Premissa pode contradizer docstring (caso G037 v18) | Esta seção |
| N10 | Inventar SQL/XML-RPC ou improvisar quando skill não existe | Subagente DEVE parar e avisar Rafael | gestor-estoque-odoo.md invariantes |
| N11 | Mexer em `app/recebimento/services/recebimento_lf_odoo_service.py` (4562 LOC) | Validado em PROD; serve de FONTE de mineração — NÃO MEXER | Regra v14a-fix |
| N12 | Mexer em `app/fretes/services/lancamento_odoo_service.py` (16 etapas) | Idem — fonte de mineração para Skill 7 ABRANGENTE v19+ | Regra v19+ |
| N13 | Mexer em `scripts/inventario_2026_05/09_executar_onda1_bulk.py` | SUPERADO ao final v22+; antes disso é referência viva | Regra v14a-ops |
| N14 | Acumular múltiplos `PROMPT_PROXIMA_SESSAO_*.md` no root de `app/odoo/estoque/` | Antes de v18 Fase 0 existiam 8 prompts cumulativos — confunde a próxima sessão sobre qual é o "vivo" | `PROMPT_PROXIMA_SESSAO.md §0 + §6.2` — sempre 1 vivo no root; executado vai para `_prompts_executados/` |
| N15 | Reescrever §0 / §1 / §6 do `PROMPT_PROXIMA_SESSAO.md` por sessão | São atemporais. Reescrever quebra a convenção e força próximas sessões a redescobrir | `PROMPT_PROXIMA_SESSAO.md §0` — apenas §2-§5 são por-sessão |

---

## SEMPRE FAZER

1. **Dry-run antes do real** — sem exceção, mesmo se "achar que entende".
2. **Antes de criar fluxo L3**, conferir que átomos existem (`ROADMAP_SKILLS.md` + `CLAUDE.md §6`).
3. **Antes de criar nova skill**, perguntar: "isto é caso de negócio novo? Então é FLUXO L3, não skill."
4. **Antes de criar gotcha novo**, ler docstrings de `operacoes_fiscais.py` + `picking_types.py` INTEIROS. (Lição G037 v18.)
5. **Verificar resultado DIRETO no Odoo** após write (não confiar só no output do script).
6. **Quando duvidar**, AVISAR Rafael e PARAR — sem improvisar.
7. **Spawn subagente `gestor-estoque-odoo` via Task tool** para EXECUTAR fluxos sobre caso real. Use principal APENAS para IMPLEMENTAR átomos novos ou debugar gaps arquiteturais. (Lição v7 — ~150k tokens evitáveis.)
8. **Pesquisar premissas ANTES de compor** — produto, empresa, lote, FIFO, qtds, CFOP, saldo. Premissa inválida = PARAR com erro claro.

---

## ANTIPADRÕES REINCIDENTES (que custaram sessões inteiras)

> Cada item: o quê + sessão + commit do fix + onde está documentado.

### AR1 — Skill 8 ETAPA E inline 420 LOC (v17 → revert v17.5)

- **O quê**: v17 implementou `executar_etapa_e` do orchestrator `faturando-odoo` (Skill 8) com 420 LOC criando `RecebimentoLf` + agregação + invocação do service externo INLINE no orchestrator. Logicamente operação de ENTRADA embutida em orchestrator de SAÍDA.
- **Por que aconteceu**: o orchestrator "podia" tecnicamente fazer. Logica complexa. Foi mais rápido inline do que criar Skill 7. Mas acoplou Skill 8 a `RecebimentoLfOdooService` e violou "1 skill = 1 responsabilidade".
- **Custo**: 1 sessão inteira (v17.5) para criar Skill 7 + revert + migrar testes + 3 fixes de code-review.
- **Como evitar**: ao implementar composição no orchestrator que envolva "criar registros locais + invocar svc externo + agregar dados", PARE e pergunte: "isso é átomo de outra skill?". Se SIM, usar. Se NÃO existe, AVISAR Rafael ANTES de implementar inline.
- **Onde**: `CLAUDE.md §3 ARMADILHA SUPERADA v17.5` + `VALIDACAO_FINAL_SESSAO.md` v17/v17.5.

### AR2 — Skill 8 ETAPA F invoca Skill 5 atomo INLINE (v17.5+v18 — refator v19+)

- **O quê**: `executar_etapa_f` do orchestrator `faturando-odoo` invoca `criar_picking_entrada_destino_manual` (Skill 5 atomo) DIRETO no orchestrator. Picking criado SEM PO+partner (caminho B paliativo).
- **Por que aconteceu**: DFe demora ~30min para aparecer; caminho A (DFe→PO→picking nativo) bloqueia v17.5. Caminho B paliativo desbloqueou pipeline.
- **Status**: DOCUMENTADO como antipadrão 2 em `CLAUDE.md §6.5`. Refator agendado v19+ via FLUXO L3 1.2.1 + Skill 7 ABRANGENTE.
- **Como evitar**: quando precisar invocar 2+ skills numa etapa de orchestrator, criar FLUXO L3 e fazer o orchestrator chamar o FLUXO (não as skills direto).
- **Onde**: `CLAUDE.md §6.5 antipadrão 2` + `SKILL.md faturando-odoo` ANTIPADROES.

### AR3 — Skill 7 V1 STRICT (`raise NotImplementedError`) (v17.5 — refator v19+)

- **O quê**: `EscrituracaoLfService.criar_recebimento_orchestrado` raise se `cnpj_emitente != LF` OU `company_id_recebedor != FB`, mesmo em dry-run.
- **Por que aconteceu**: V1 escopo restrito a LF→FB para destravar Skill 8 ETAPA E. Limite via raise no átomo em vez de FLUXOS+CONSTANTS+PRE-FLIGHT.
- **Status**: DOCUMENTADO como antipadrão 1+4 em `CLAUDE.md §6.5`. Skill 7 deve ser ATÔMICA mas ABRANGENTE (1 objeto Odoo, sem restringir direção).
- **Como evitar**: nova skill ABRANGENTE desde início. Limite vem de FLUXOS L3 que escolhem args, NÃO de raise no átomo. Dry-run sempre planeja (mesmo direções não implementadas).
- **Onde**: `CLAUDE.md §6.5 antipadrões 1+4` + `SKILL.md escriturando-odoo` CHECKLIST V2.

### AR4 — G037 v18 criado com premissa errada (sem ler docstring) (v18)

- **O quê**: criei G037 em v18 dizendo "MATRIZ_INTERCOMPANY[acao]['cfop_esperado'] tem USO PRATICO (nao apenas log)". Mas `operacoes_fiscais.py:17` JÁ DIZIA "informacional/log. Real e decidido pelo Odoo".
- **Por que aconteceu**: criei o gotcha sem ler `operacoes_fiscais.py` inteiro — Rafael perguntou explicitamente "voce leu esses 2 arquivos?".
- **Status**: REESCRITO em F0.8 (Fase 0 v18) com escopo restrito ao caminho B paliativo (picking ETAPA F manual sem PO).
- **Como evitar**: SEMPRE ler `operacoes_fiscais.py` + `picking_types.py` INTEIROS antes de criar gotcha sobre operações fiscais (N9 acima).
- **Onde**: `docs/inventario-2026-05/02-gotchas/G037-*.md` reescrito.

### AR6 — Acúmulo de `PROMPT_PROXIMA_SESSAO_*.md` no root (v18 Fase 0)

- **O quê**: até 2026-05-26 v18, existiam **8 prompts** acumulados em `app/odoo/estoque/`: `PROMPT_PROXIMA_SESSAO.md` (atual) + 7 `PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`. Sessão nova ficava confusa: qual é o "vivo"? E o root poluído.
- **Por que aconteceu**: cada sessão criava prompt novo sem regra clara de arquivamento; sufixo `_EXECUTED_<data>` foi convencionado mas não havia pasta de destino dedicada.
- **Correção v18 Fase 0**: criada pasta `_prompts_executados/` + movidos os 8 prompts antigos. Convenção atemporal codificada em `PROMPT_PROXIMA_SESSAO.md §0 + §6.2`: 1 só vivo no root; executado vai para a pasta; §0/§1/§6 atemporais (copiar literal); §2-§5 por-sessão (reescrever).
- **Como evitar**: N14+N15 acima. Ao terminar sessão, seguir `PROMPT_PROXIMA_SESSAO.md §6.2` (renomear executado + criar novo com escopo N+1 preservando §0/§1/§6 literais).

### AR5 — Catálogo §6 mistura skill L2 com orchestrator C3 (origem do problema)

- **O quê**: `CLAUDE.md §6` cataloga `faturando-odoo` e `escriturando-odoo` (e `planejando-pre-etapa-odoo`) como skills com camada "C3". Tabela "Skills WRITE (8)" mistura átomos L2 com orchestrators C3 macro.
- **Por que aconteceu**: catálogo evoluiu organicamente sem revisão crítica. Skills "ganham status de catálogo" e o agente trata todas como atômicas L2.
- **Status**: REORGANIZADO em F0.2 (Fase 0 v18) em 3 tabelas distintas (Skills L2, Orchestrators C3, Fluxos L3).
- **Como evitar**: ao adicionar skill nova, perguntar: "qual OBJETO Odoo único?" Se "vários" ou "orchestra", é C3 macro, vai para outra tabela; NÃO entra no catálogo de skills L2.
- **Onde**: `CLAUDE.md §6` (3 tabelas) + §14 Histórico de desvios.

---

## LIÇÕES "EXPENSIVE" QUE NÃO PRECISA DESCOBRIR DE NOVO

Memories acessíveis via `mcp__memory__view_memories`:

- `[[constituicao-skill-so-responsabilidade]]` — lição custosa v17.5 sobre "1 skill = 1 responsabilidade" violada em v17
- `[[feedback-executar-fluxos-subagente]]` — spawn subagente vs principal (v7 ~150k tokens evitáveis)
- `[[fluxo-2-6-pattern]]` — tratar reserva ATIVA pré-Skill 2 (caminho A/B/C/D/E)
- `[[skill2-distribuir-indisp-pattern]]` — cleanup pós-bulk obrigatório
- `[[skill5-picking-pattern]]` — invariante G019/G020 + 3 átomos inter-company v15a
- `[[skill7-escriturando-pattern]]` — V1 STRICT documentado como antipadrão v17.5
- `[[skill8-pipeline-completo-v17]]` — 11 fixes pos-3 reviewers v17
- `[[skill8-recovery-pattern]]` — `executar_pipeline_resume` substitui scripts shell v18
- `[[gotcha-g031-lot-migracao-por-produto]]` — `stock.lot` é POR PRODUTO no CIEL IT
- `[[gotcha-g030-quant-id-em-stock-move-line-eh-computed]]` — filter por `quant_id` retorna lixo
- `[[gotcha-resetar-reserva-orfao-negativo]]` — fluxo Skill 1 + Skill 2.4 gera reserved negativo

---

## SE ENCONTRAR CONTRADIÇÃO NA DOCUMENTAÇÃO

1. **PARE** — não improvise interpretação.
2. **Reporte ao Rafael** — descreva qual doc diz X e qual diz Y, com `file:line`.
3. **Atualize a documentação ANTES de mexer em código** — Fase 0 sempre vem antes de Fase 1+.
4. **Documente o desvio em §14 do `CLAUDE.md` estoque** — para que próxima sessão saiba que esse específico já foi detectado e corrigido.

> Exemplo concreto v18: docstring `operacoes_fiscais.py:17` dizia "informacional/log" mas G037 dizia "USO PRATICO". Eu (Claude) NÃO PAREI — criei G037 errado. Rafael detectou. Resultado: Fase 0 antes de qualquer refator v19+.

---

## REGRA DE MANUTENÇÃO

Esta documentação é VIVA. **Sessão que detectar novo antipadrão DEVE atualizar este documento ANTES do commit final**. Concretamente:

1. Detectou novo antipadrão reincidente? Adicione em "ANTIPADRÕES REINCIDENTES" (AR5+).
2. Detectou nova lição expensive? Adicione em "LIÇÕES EXPENSIVE" com link memory.
3. Detectou novo "nunca fazer"? Adicione em "NUNCA FAZER" (N14+).
4. Atualizou? Cite no commit message: `+ atualizado PROTECAO_PROXIMA_SESSAO.md (ARN antipadrao XYZ)`.

**Não atualizar quando deveria = você está condenando a próxima sessão a redescobrir o mesmo problema.**

---

## REFERÊNCIAS RÁPIDAS

- Constituição: `app/odoo/estoque/CLAUDE.md`
- Subagente: `.claude/agents/gestor-estoque-odoo.md`
- ROADMAP: `app/odoo/estoque/ROADMAP_SKILLS.md`
- Histórico: `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md`
- Planejamento Skill 8: `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`
- Fluxos L3: `app/odoo/estoque/fluxos/`
- Constants: `app/odoo/constants/operacoes_fiscais.py` + `picking_types.py`
- Gotchas: `docs/inventario-2026-05/02-gotchas/` + `.claude/references/odoo/GOTCHAS.md`
- IDs fixos: `.claude/references/odoo/IDS_FIXOS.md`

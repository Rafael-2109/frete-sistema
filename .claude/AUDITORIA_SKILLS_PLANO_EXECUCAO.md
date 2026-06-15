# Plano de Execução das Sugestões da Auditoria de Skills

> Companion de `AUDITORIA_SKILLS_2026-05-29.md`. Decisões tomadas com o Rafael em 2026-05-30.
> Status (2026-06-15): **Ondas 0/A/B/C(a)/D/E1/F(venda)/F(carregamento) MERGEADAS (git: 473b7c9be D, bb83a3640 E, 3e07e6944 F, 34c9ec8c1 F2; worktrees ja removidos). Falta: F `transferencia-saldo-codigo` + Onda G (renomes). Prioridade Rafael: F > G > mais testes.** (companions DRIFT_MAP/PROJETO_CONSOLIDACAO/PROMPT_PROXIMA_SESSAO arquivados em `.claude/_deprecated/` na limpeza 2026-06-15.)
> Forense git (wf_192add78) confirmou: os 6 commits da auditoria (6c5cfe037, 7c6ecb0fd, f2c39789f, 894f6fc63, 869fb3052, 88e59dfb1) são TODOS alcançáveis a partir do HEAD atual (d87765cc8); conteúdo presente no working tree (dpg=0, buscando-rotas=0, ROUTING=51, 3 scripts órfãos ABSENT, py_compile OK). Branches/worktrees skills/onda-b e skills/onda-c já removidos (cleanup pós-merge). **C(b) REVERTIDA por decisão do Rafael** (ANTIPADRÕES + CHECKLIST seguem inline em faturando-odoo). **Onda D concluída** — ver §Onda D — RESULTADO. Próximo gate: E (testes, baixo risco).

## Decisões (Rafael, 2026-05-30)
- **Branch**: worktree por onda (a partir do HEAD da `main`).
- **Ritmo**: executar 1 onda, mostrar diff, PARAR para revisão, só então seguir.
- **Skills faltantes (Onda F)**: construir — mas "pensar juntos com calma" (brainstorming + spec por skill ANTES de codar).
- **Renames (Onda G)**: Rafael pediu avaliação de segurança antes de decidir (ver §Rename Safety).

## Protocolo por mudança (inviolável)
1. Re-verificar a fonte de verdade AO VIVO no momento da edição (NÃO confiar nos números de linha do relatório — podem estar velhos).
2. Editar → verificação objetiva (py_compile / import / --help / grep das refs) → self-audit.
3. Skill = pacote: checklist "padrão completo" (SCRIPTS.md + evals + ROUTING_SKILLS.md + tool_skill_mapper.py + cross-refs "NÃO USAR PARA" + agents).
4. Worktree isolado por onda; commit só após revisão do Rafael.

## Sequenciamento (risco crescente)
| Onda | Conteúdo | Risco | Runtime? | Status |
|---|---|---|---|---|
| 0 (P0) | consultando-estoque-loja (bug estoque), consultando-sentry (tools fantasma), acompanhando-pedido-compra-assai (status mortos) | — | sim/doc | ✅ FEITO+VERIFICADO (uncommitted na main) |
| A | staleness doc-only (7 itens) | Baixo | NÃO | ✅ MERGEADA (544f4eb35) |
| B | infra: ROUTING contagem, tool_skill_mapper, remover 3 órfãos operando-ssw | Baixo-médio | não | ✅ MERGEADA (894f6fc63 + 88e59dfb1) — viva na main |
| C | hardcodes (postgresId), faturando-odoo −118L p/ references | Médio | não | ✅ C(a) MERGEADA (869fb3052); ❌ C(b) REVERTIDA (manter ANTIPADRÕES inline) |
| D | consolidar resolver_entidades → SoT em `app/resolvedores/` | Médio-alto | SIM | ✅ **EXECUTADA local 2026-06-01** (commit `c694c6c2f`, branch `skills/onda-d-resolvedores`, NÃO pushada). 97 pytest, 3 reviewers, baseline zero-regressão, bug accent corrigido. **Merge pendente** (decisão Rafael). Detalhes ↓ §Onda D — RESULTADO |
| E | testes: conciliando-transferencias-internas, CT-e operando-ssw | Baixo | não | ✅ **E1 FEITA** (branch `skills/onda-e-testes`, 68 testes pytest determinístico; evals LLM VETADOS por custo; resto = backlog) |
| F | construir skills faltantes (venda HORA M3, carregamento Assai, transferencia-saldo-codigo) | Médio | sim | 🟡 **2/3 FEITAS** (`consultando-venda-loja` + `carregando-motos-assai` em branches; falta `transferencia-saldo-codigo`) |
| G | renames (4 substantivos + sufixo -hora) — só após aprovação | ALTO (breaking) | sim | ⬜ |

## ONDA A — escopo exato (doc-only, nenhum .py muda)
Worktree: `.claude/worktrees/skills-onda-a` (branch `skills/onda-a-staleness` @ 400b0634).

1. **monitorando-entregas/SCRIPTS.md** (≈L18): tabela `monitoramento_entregas` → `entregas_monitoradas`.
   - Fonte de verdade: schema `consultando-sql/schemas/tables/entregas_monitoradas.json` (nome correto). O script real consulta `FROM entregas_monitoradas`.
2. **acessando-ssw/SKILL.md** (≈L20): "228 docs" → **309** (CONFIRMADO via `find .claude/references/ssw -name '*.md' | wc -l` = 309). Reconferir POPs/fluxos na hora. Sugestão: tornar aproximado ("~300 docs") para não re-drift.
3. **razao-geral-odoo/SKILL.md** (≈L82): exemplo `company_ids=[4, 1, 3]` → incluir **5 (La Famiglia)**. CONFIRMAR company_id da LF em `references/odoo/IDS_FIXOS.md` antes.
4. **validacao-nf-po/SKILL.md**: ref `recebimento-fisico` → `recebimento-fisico-odoo` (L≈340); neutralizar labels "NOVO - Jan/2026" (L≈201/216).
5. **gerindo-agente/SKILL.md**: remover linha duplicada `MEMORY_SEMANTIC_SEARCH` (L151 vs L155 — manter uma).
6. **parseando-sped-ecd/SKILL.md** (≈L26): exemplo fixo em `V21` → versão corrente (CONFIRMAR versão atual; finding citou V36; `ls ~/SPED_ECD_NACOM_GOYA_*.txt` não retornou — localizar o path real). Sugestão: usar placeholder `<VERSAO>` p/ não re-drift.
7. **rastreando-chassi/SKILL.md**: documentar conjunto amplo de eventos no output/estado (não muda script). Fonte de verdade `app/hora/services/estoque_service.py`:
   - EM_ESTOQUE = RECEBIDA, CONFERIDA, TRANSFERIDA, CANCELADA, AVARIADA, FALTANDO_PECA, EMPRESTIMO_ENTRADA, RESSARCIMENTO_SAIDA
   - FORA = RESERVADA, VENDIDA, DEVOLVIDA, NF_EMITIDA, NF_CANCELADA, EMPRESTIMO_SAIDA, RESSARCIMENTO_ENTRADA
   - EM_TRANSITO = limbo (trânsito)

Verificação Onda A: `git diff` no worktree + grep das refs antigas (devem sumir, exceto notas).

## Rename Safety (§ resposta a "pode fazer com segurança? Avalie isso")
**Veredito: É possível com segurança, MAS só vale com I/O saudável e como onda dedicada — porque renomear skill tem raio de impacto grande e mecânico.** Superfície de referência a varrer por nome (cada uma DEVE ser atualizada senão quebra roteamento):
1. Diretório `.claude/skills/<nome>/` (rename físico).
2. `.claude/references/ROUTING_SKILLS.md` (árvore + desambiguações + inventário/contagem).
3. `app/agente/services/tool_skill_mapper.py` (SKILL_TO_CATEGORY).
4. `app/agente_lojas/...skills_whitelist.py` / `SKILLS_PERMITIDAS` (para nomes HORA).
5. Frontmatter `skills:` de subagentes (ex: analista-carteira `skills: [gerindo-expedicao, ...]`).
6. Cross-refs "NÃO USAR PARA" nas descriptions de OUTRAS skills.
7. Slash commands em `.claude/commands/` que citam a skill.
8. evals/ (referências internas) + qualquer doc que cite o nome.

**Método seguro**: 1 nome por commit; `grep -rIl "<nome-antigo>"` (excluindo .venv/worktrees) ANTES → atualizar TODAS as ocorrências → `grep` DEPOIS provando zero refs órfãs (exceto histórico). O risco é puramente "esquecer um site de referência" — eliminado por grep exaustivo. Candidatos: visao-produto, validacao-nf-po, razao-geral-odoo, recebimento-fisico-odoo (+ cluster HORA p/ simetria -hora, maior).

## Onda D — RESULTADO (2026-06-01)
Consolidou `resolver_entidades` (monolito `gerindo-expedicao` + split `resolvendo-entidades`) em
`app/resolvedores/` (12 arq, ORM, núcleo + 2 fachadas: "rica" p/ os 9 importadores Python via shim;
`_cli` p/ os 7 CLIs / 8 subagentes). Scripts viraram wrappers finos. −2858 linhas de duplicação.
Validado: **97 pytest**, 3 code-reviewers, baseline wrapper-novo vs CLI-antigo = **zero regressão**
(exceto cidade-accent corrigido de propósito).

- **Onde**: worktree `frete_sistema_resolvedores`, branch `skills/onda-d-resolvedores`, commit `c694c6c2f` (NÃO pushado).
- **SOT da Onda D** (detalhe completo): `docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md` (no worktree) + memória `onda_d_resolvedores.md`.
- **Correções ao DRIFT_MAP** (reverificadas ao vivo): **8 subagentes** (não 10); bug accent era **só da split**; `app/utils/grupo_empresarial.py` **INCOMPATÍVEL** (formato de prefixo diferente — não acoplar); `ABREVIACOES_PRODUTO` morto no monolito (SoT = `product_search`).
- **Mudanças de comportamento deliberadas** (Rafael): `formatar_sugestao_pedido` (TypeError) corrigido; uniformização `qtd_saldo>0` nas funções ricas com `fonte=separacao` (afeta `consultando_situacao_pedidos`).
- **Pendências port-fiel ADIADAS** (não-regressão; candidatas a onda futura): `resolver_cidade` rico carrega 27k linhas via `query.all()` (sem caller ativo); wildcards `%`/`_` no termo afetam ILIKE.

## Onda E/F — RESULTADO (2026-06-02)

**4 branches executadas, NENHUMA mergeada/pushada** (worktrees preservados):

| Branch | Worktree | Entrega | Verificação |
|---|---|---|---|
| `skills/onda-d-resolvedores` | `frete_sistema_resolvedores` | resolver_entidades → app/resolvedores | 97 pytest (sessão anterior) |
| `skills/onda-e-testes` (`0aa9155f2`) | `frete_sistema_onda_e` | pytest p/ conciliando-transf + CT-e operando-ssw | 68 testes, $0 |
| `skills/onda-f-venda-hora` | `frete_sistema_onda_f` | skill READ `consultando-venda-loja` (HORA M3 venda) + wrapper `venda_service.validar_desconto_tabela` | 13 testes |
| `skills/onda-f-carregamento-assai` | `frete_sistema_onda_f2` | skill READ+WRITE `carregando-motos-assai` (carregamento Assaí) | 13 testes, PAD-A-conforme |

**Decisões/aprendizados (em memória):**
- **Evals LLM VETADOS por custo** → cobertura de skill = **pytest determinístico** (extrai código de markdown / importlib de scripts + mock; zero DB/PROD/token). Ver `feedback_evals_llm_caros_preferir_pytest`.
- **Prioridade Rafael: F > G > mais testes** (criar skills faltantes > renomear > cobrir testes de baixo risco).
- **PAD-A** (mergeado `357193fbe`): docs novas conformadas (spec=`explanation`, plano=`how-to`, TOC heading=`Indice`, SKILL.md isento de doc:meta). Gotchas em `pad_a_conformance_gotchas`.
- **Resto da Onda E = backlog** (READ fat-skills, SSW cadastro): baixo ROI; risco-alto WRITE já coberto (cluster estoque-odoo via tests/odoo/services, SPED e Assaí já têm pytest). **NÃO iterar.**
- **DEFERIDO p/ migração PAD-A project-wide:** retrofit de `doc:meta` em 2 docs legados tocados pelo wiring (`.claude/references/ROUTING_SKILLS.md`, `app/motos_assai/CLAUDE.md`) — flagados C1 pelo `--enforce-touched` (violação pré-existente, NÃO introduzida).

## Próximos passos (ordem sugerida — prioridade F > G > testes)
1. **Onda F — `transferencia-saldo-codigo`** (ganho rápido): service + teste JÁ EXISTEM (`tests/odoo/services/test_transferencia_saldo_codigo_service.py`); falta só o **wrapper de skill**. Brainstorming curto (READ vs WRITE) + spec + plano + pytest, PAD-A-conforme. ⬜
2. **Onda G** (ALTO, breaking): renames (4 substantivos: visao-produto, validacao-nf-po, razao-geral-odoo, recebimento-fisico-odoo + cluster `-hora` simétrico ao `-assai`) — só após aprovação; método em §Rename Safety; grep exaustivo, 1 nome/commit. ⬜
3. **Integração das 4 branches** (timing do Rafael): merge/PR de D/E/F-venda/F-carregamento. `main` local pode estar à frente de `origin/main` — alinhar antes. Merge de D dispara deploy do gunicorn-agente (runtime).
4. **Migração PAD-A project-wide** (separada): retrofit `doc:meta` nos docs legados gerenciados (ROUTING_SKILLS.md, app/*/CLAUDE.md, etc.). NÃO misturar com branches de skill.

# Plano de Execução das Sugestões da Auditoria de Skills

> Companion de `AUDITORIA_SKILLS_2026-05-29.md`. Decisões tomadas com o Rafael em 2026-05-30.
> Status: **Onda A interrompida por degradação de I/O da sessão (reads truncando) — retomar em sessão nova.**

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
| A | staleness doc-only (7 itens) | Baixo | NÃO | ⏸️ worktree criado, edits NÃO iniciadas (I/O) |
| B | infra: ROUTING contagem, tool_skill_mapper, remover 3 órfãos operando-ssw | Baixo-médio | não | ⬜ |
| C | hardcodes (postgresId, model IDs), faturando-odoo −118L p/ references | Médio | não | ⬜ |
| D | consolidar resolver_entidades (medir drift → SoT em app/ → migrar c/ teste regressão) | Médio-alto | SIM | ⬜ |
| E | testes: conciliando-transferencias-internas, CT-e operando-ssw | Baixo | não | ⬜ |
| F | construir skills faltantes (HORA venda M3, carregamento Assai) — brainstorming+spec antes | Médio | sim | ⬜ |
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

## Retomar
- Onda A: worktree pronto; aplicar os 7 itens acima com o protocolo; `git diff` p/ revisão.
- P0: decidir commit (na main ou mover p/ branch própria).

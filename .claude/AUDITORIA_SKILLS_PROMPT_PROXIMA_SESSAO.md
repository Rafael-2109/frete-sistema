# Prompt — próxima sessão (Auditoria de Skills / Nacom Goya)

Continuação do **PLANO DE AUDITORIA DE SKILLS**. Ondas 0/A/B/C(a) MERGEADAS na main.
Ondas **D, E1, F(venda), F(carregamento)** EXECUTADAS em **4 branches separadas, NÃO mergeadas**.

## ANTES DE QUALQUER COISA, LEIA (índice + fonte + estado):
1. `.claude/AUDITORIA_SKILLS_PLANO_EXECUCAO.md` — **SOT/índice das ondas**. Foco em §"Onda E/F — RESULTADO" + §"Próximos passos" (status, sequenciamento, Rename Safety).
2. `.claude/AUDITORIA_SKILLS_2026-05-29.md` — relatório original (findings por skill; gaps em L50-64).
3. Memórias: `auditoria_skills_onda_e_f_estado` (estado das branches), `feedback_evals_llm_caros_preferir_pytest`, `pad_a_conformance_gotchas`, `feedback_skill_padrao_completo`, `feedback_worktree_branches_paralelas`.

## ESTADO (4 branches aguardando integração — NENHUMA pushada/mergeada):
- `skills/onda-d-resolvedores` (worktree `frete_sistema_resolvedores`) — resolver_entidades → app/resolvedores.
- `skills/onda-e-testes` (`0aa9155f2`, worktree `frete_sistema_onda_e`) — 68 testes pytest determinístico.
- `skills/onda-f-venda-hora` (worktree `frete_sistema_onda_f`) — skill READ `consultando-venda-loja` + wrapper `venda_service.validar_desconto_tabela`.
- `skills/onda-f-carregamento-assai` (worktree `frete_sistema_onda_f2`) — skill READ+WRITE `carregando-motos-assai`.

## PADRÕES NOVOS DESTA LINHAGEM (CRÍTICO — não repetir os erros já corrigidos):
- **NÃO criar evals.json/trigger_eval_set.json** (Rafael vetou por custo de token). Cobertura de skill = **pytest determinístico**: skill com código-em-markdown → extrair blocos + mock Odoo; skill com scripts .py → `importlib` + mock dos services (zero DB/PROD/token). Templates prontos: `tests/skills/conciliando_transferencias_internas/`, `tests/skills/operando_ssw/`, `tests/skills/carregando_motos_assai/`.
- **PAD-A** (doc enforcement, merge `357193fbe`): docs novas precisam de `doc:meta`. Spec=`tipo: explanation` (Papel+Contexto), plano=`tipo: how-to` (Papel), TOC heading literal `## Indice` (não "Sumário"), SKILL.md **isento** de doc:meta (só TOC se >100L). Registrar no INDEX do hub (specs/plans). Verificar: `python scripts/audits/doc_audit.py --strict --path <arq>`. **NÃO** retrofitar docs legados gigantes tocados pelo wiring (defere p/ migração PAD-A). Detalhes: `pad_a_conformance_gotchas`.
- **Prioridade Rafael: F > G > mais testes.**

## PROTOCOLO INVIOLÁVEL (igual às ondas anteriores):
- Reverifique a fonte AO VIVO (não confie em nº de linha; main mudou de linhagem).
- **Worktree próprio por tarefa** a partir do HEAD da main (`git worktree add ... -b skills/onda-X ... main`). **PEÇA PERMISSÃO antes de qualquer `git checkout`** no working tree principal (costuma estar em `main` com trabalho do Rafael). Garanta `.env`/DATABASE_URL no worktree (cp .env).
- Skill = pacote completo (`feedback_skill_padrao_completo`: SCRIPTS.md/scripts + **pytest** + ROUTING_SKILLS + tool_skill_mapper + cross-refs "NÃO USAR PARA" + agents/whitelist).
- Brainstorming + spec ANTES de codar skill nova (superpowers:brainstorming → writing-plans → executing-plans → finishing). Para skill WRITE: incluir PRE-MORTEM na spec.
- Verificação objetiva (pytest/py_compile/--help/grep/doc_audit) + self-audit. Considere code-reviewer no fim.
- **NÃO commite/mergeie/pushe sem aprovação.** PARE para revisão ao fim da onda (mostre o diff).

## FOCO sugerido (pergunte ao Rafael qual seguir ANTES de começar):
1. **Onda F — `transferencia-saldo-codigo`** (RECOMENDADO, ganho rápido): service + teste JÁ EXISTEM (`tests/odoo/services/test_transferencia_saldo_codigo_service.py`); citada como destino em `ajustando-quant-odoo` e `transferindo-interno-odoo` mas sem skill. Só falta o **wrapper de skill** (decidir READ vs WRITE no brainstorming — provável WRITE, padrão estoque-odoo: dry-run+confirmar).
2. **Onda G** — renames (4 substantivos: visao-produto, validacao-nf-po, razao-geral-odoo, recebimento-fisico-odoo + cluster `-hora` simétrico ao `-assai`). ALTO risco (breaking de roteamento); método em §Rename Safety; grep exaustivo, 1 nome/commit.
3. **Integração das 4 branches** (merge/PR — timing do Rafael; merge de D dispara deploy do gunicorn-agente).
4. **Migração PAD-A project-wide** (separada): retrofit `doc:meta` nos docs legados gerenciados.

Pergunte ao Rafael qual das 4 frentes seguir antes de iniciar.

<!-- doc:meta
tipo: explanation
camada: L3
sot_de: skill carregando-motos-assai (design)
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Spec — Skill `carregando-motos-assai` (Onda F / Motos Assaí carregamento READ+WRITE)

> **Papel:** blueprint de design da skill READ+WRITE de carregamento Motos Assaí. **Abra quando:** for implementar/revisar a skill, entender o escopo dos 8 modos, as salvaguardas WRITE ou o pré-mortem.

**Data:** 2026-06-02
**Status:** design aprovado (brainstorming) — aguardando review da spec antes do plano
**Onda:** F (auditoria de skills) — fecha gap "Assai carregamento sem skill" (relatório `AUDITORIA_SKILLS_2026-05-29.md` L54)
**Worktree:** `frete_sistema_onda_f2`, branch `skills/onda-f-carregamento-assai` (base main `357193fbe`)

---

## Contexto

O **carregamento** (etapa física entre Separação FECHADA e NF Q.P.A. — escaneia chassi por chassi na carga) já está LIVE em `app/motos_assai`: model `AssaiCarregamento`/`AssaiCarregamentoItem`, `carregamento_service`, `routes/carregamento.py`. Status `EM_CARREGAMENTO → FINALIZADO → CANCELADO`.

**Não existe skill** para o agente operar/consultar carregamento. A spec de skills Assai (`2026-05-08-motos-assai-skills-agents-design.md`) é **anterior** ao carregamento (criado em 2026-05-12) — logo é gap genuíno, não deferral. As 6 skills atuais não cobrem: `acompanhando-saida-assai` (READ) = separações + NFs; `registrando-evento-moto-assai` (WRITE) = eventos de **moto** (montagem/disponibilizar/separar/cancelar). Carregamento é entidade separada com escaneamento próprio.

## 2. Objetivo

Criar **`carregando-motos-assai`** (READ + WRITE) para o cluster Motos Assaí, espelhando `conferindo-recibo-assai` (READ+WRITE de etapa física com escaneamento). Filosofia da spec de skills (D2): operadores de chão executam WRITE via chat **com salvaguardas** (`--user-id` obrigatório + `--dry-run` default + `--confirmar` + checa `pode_acessar_motos_assai()`).

### Não-objetivos (YAGNI)
- Não reimplementa lógica de carregamento — **reusa `carregamento_service`** (criar/escanear/cancelar/finalizar/alterar).
- Não toca o algoritmo §6 de finalização (integra pedido_status + separacao_mirror dentro do service).
- Sem novo modelo/migration (entidade já existe).

## 3. Escopo

### READ (sem `--user-id`/`--confirmar`)
| Op | Args | Saída |
|----|------|-------|
| `--listar` | [`--status` `--pedido-id` `--loja-id` `--separacao-id`] | lista carregamentos (id, status, pedido/loja/sep, contadores, timestamps) |
| `--detalhar` | `--carregamento-id N` | detalhe (header + itens escaneados: chassi/modelo, escaneado_em) |

### WRITE (`--user-id` obrigatório + `pode_acessar_motos_assai()` + `--dry-run` default / `--confirmar`)
| Op | Args | Service |
|----|------|---------|
| `--iniciar` | `--pedido-id` `--loja-id` | `criar_carregamento(pedido_id, loja_id, operador_id)` |
| `--escanear` | `--carregamento-id` `--chassi` | `escanear_carregamento_item(carregamento_id, chassi, operador_id)` |
| `--cancelar-item` | `--item-id` | `cancelar_carregamento_item(item_id, operador_id)` |
| `--finalizar` | `--carregamento-id` | `finalizar_carregamento(carregamento_id, operador_id)` (algoritmo §6 + pedido_status + separacao_mirror) |
| `--cancelar` | `--carregamento-id` `--motivo` | `cancelar_carregamento(carregamento_id, motivo, operador_id)` (motivo ≥3 chars) |
| `--alterar` | `--carregamento-id` | `alterar_carregamento(carregamento_id, operador_id)` — reabre FINALIZADO→EM_CARREGAMENTO (regride Sep CARREGADA→FECHADA) |

## 4. Arquitetura

**1 skill, 1 script** `carregando_motos_assai.py`, **action-flags** (espelha `registrando-evento-moto-assai` + `conferindo-recibo-assai`):
- `create_app()` + `app_context()`; saída `json.dumps`.
- **READ**: query via service/ORM read (ou SQL bruto) → JSON.
- **WRITE**: `--user-id` obrigatório → checa `Usuario.pode_acessar_motos_assai()` (senão **exit 3**). Sem `--confirmar` → **preview dry-run (exit 4)** mostrando ação + estado atual, SEM mutar. Com `--confirmar` → chama service + **`db.session.commit()`** (service faz `flush()`, caller commita — [[gotcha_commit_service_vaza_savepoint]]).
- Trata as 6 exceptions com mensagem clara + exit code: `CarregamentoValidationError` (não existe/args), `CarregamentoStateError` (transição inválida), `CarregamentoConflictError` (race/duplicado), `CarregamentoExcedenteError` (escaneou além do planejado), `CarregamentoCrossLojaError` (chassi de outra loja). Mapear para exit codes (ex.: 1 genérico, 2 validação, 5 conflito) consistentes com o cluster.

**Exit codes** (espelhar `registrando-evento-moto-assai`): 0 ok, 3 sem autorização, 4 dry-run preview, demais = erro.

### 4.1 Reuso de service (assinaturas verificadas — `carregamento_service.py`)
- `criar_carregamento(pedido_id, loja_id, operador_id)` (L81)
- `escanear_carregamento_item(carregamento_id, chassi, operador_id)` (L118)
- `cancelar_carregamento_item(item_id, operador_id)` (L227)
- `cancelar_carregamento(carregamento_id, motivo, operador_id)` (L255; motivo ≥3 chars)
- `alterar_carregamento(carregamento_id, operador_id)` (L302; FINALIZADO→EM_CARREGAMENTO)
- `finalizar_carregamento(carregamento_id, operador_id)` (L400; pode raise `CarregamentoExcedenteError`)

## 5. Pacote completo (wiring)
1. `.claude/skills/carregando-motos-assai/SKILL.md` (description USAR/NÃO-USAR + READ/WRITE + salvaguardas; `allowed-tools: Read, Bash, Glob, Grep`).
2. `.claude/skills/carregando-motos-assai/scripts/carregando_motos_assai.py`.
3. `.claude/agents/gestor-motos-assai.md` — adicionar `carregando-motos-assai` ao frontmatter `skills:` **[verificar lista exata na impl]**.
4. `.claude/references/ROUTING_SKILLS.md` — linha de roteamento no cluster Assaí + inventário "Skills motos_assai (6)" → (7).
5. `app/agente/services/tool_skill_mapper.py` — categoria Assaí (ex.: `'carregando-motos-assai': 'Pipeline Saída Q.P.A.'` ou categoria equivalente — **verificar categoria dos irmãos na impl**).
6. `app/motos_assai/CLAUDE.md` — tabela "Skills + Agente" (6→7) + roadmap (remover/atualizar nota de skill faltante).
7. Cross-ref: `acompanhando-saida-assai` NÃO-USAR-PARA → apontar carregamento para `carregando-motos-assai`.

## 6. Testes (determinístico, $0, sem DB — [[feedback_evals_llm_caros_preferir_pytest]])
`tests/skills/carregando_motos_assai/test_carregando_motos_assai.py`:
- Carrega script via `importlib`; **mocka** as 6 funções do `carregamento_service` + `Usuario.pode_acessar_motos_assai` + `db` (commit).
- Testa: roteamento de action-flag; READ shaping (listar/detalhar com SQL/ORM mockado); WRITE dry-run (não chama service, exit 4) vs `--confirmar` (chama service + commit); `pode_acessar_motos_assai=False` → exit 3; `--user-id` ausente em WRITE → erro; tratamento de cada exception → exit code + mensagem.
- Sem evals LLM.

## 7. PRE-MORTEM (obrigatório — skill WRITE; §5 da spec de skills Assaí)
1. **Operador escaneia chassi de outra loja** → `CarregamentoCrossLojaError` capturada, mensagem clara, exit != 0. (service já valida)
2. **Excedente (escaneou além do planejado)** → `finalizar`/`escanear` levanta `CarregamentoExcedenteError`; skill reporta, não força.
3. **Dry-run vaza WRITE** → garantir que SEM `--confirmar` o service WRITE NÃO é chamado (preview só lê). Teste explícito.
4. **Commit sem flush ou flush sem commit** → service faz flush, skill commita só com `--confirmar`; em dry-run faz rollback/nada. Teste de não-commit em dry-run.
5. **Reabrir CANCELADO** → `alterar_carregamento` levanta `CarregamentoStateError` (CANCELADO não reabre); skill reporta. (service já valida)

## 8. Critérios de aceite
- Skill invocável; READ (listar/detalhar) + 6 WRITE ops; `--user-id` obrigatório em WRITE; dry-run default; `--confirmar` efetiva + commita.
- Reusa `carregamento_service` (sem reimplementar); trata as 6 exceptions; exit codes consistentes com o cluster.
- pytest determinístico verde (mock, sem DB); `py_compile` + `--help` OK.
- Wiring completo (SKILL.md + gestor-motos-assai + ROUTING + tool_skill_mapper + CLAUDE.md + cross-ref).
- **PAD-A**: verificar se spec/plano/SKILL.md exigem `doc:meta` via `padronizando-docs` (PAD-A mergeado em main 2026-06-02) — decisão pendente com o dono.

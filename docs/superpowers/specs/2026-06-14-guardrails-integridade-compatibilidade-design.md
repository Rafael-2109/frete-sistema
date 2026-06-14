<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-14
-->

# Design: Guardrails de Integridade & Compatibilidade (local-first)

> **Papel:** especificar os guardrails que hoje NÃO existem (ou estão dormentes) e
> que agregam em *integridade de dados* e *compatibilidade/contratos*, rodando
> localmente (hooks Claude Code + pre-commit), reusando o padrão PAD-A.
> **Escopo final (enxuto):** A0 + A1 + B2.

## Contexto

Levantamento de 2026-06-14 (sessão Claude Code). Operação com dados REAIS exige
integridade/compatibilidade fortes. Já existe infraestrutura de guardrail madura,
mas parte está desligada. O escopo foi deliberadamente enxugado em diálogo com o
usuário (ver §5 — decisões): cortou-se o que ele não erra na prática (migrations).

---

## 1. Achados do levantamento (baseline verificado)

### 1.1 Duas camadas de guardrail já existentes

| Camada | Onde vive | Dispara | Bloqueia? |
|--------|-----------|---------|-----------|
| **A. Hook Claude Code** | `.claude/hooks/*.py` + `.claude/settings.json` | durante o dev (Write/Edit/Stop/Agent) | sim (PreToolUse `deny`) ou avisa (stderr) |
| **B. Auditor pre-commit** | `scripts/audits/X_audit.py` + `scripts/hooks/pre-commit-X-lint.sh` | no `git commit` | sim (`set -e`), modo `--enforce-added` |

Cadeia pre-commit atual (`scripts/hooks/pre-commit`): `ui-lint → doc-lint →
script-lint → prompt-lint → claude-md-stats`. Dispatcher em `.git/hooks/pre-commit`.
Hooks Claude Code ligados: SessionStart `validar-estrutura`; PreToolUse Write|Edit
`pad_creation_gate`; PreToolUse Edit `pad_sot_modulo`; Stop `pad_stop_completude`.

### 1.2 Hooks escritos mas DORMENTES (existem, ausentes do settings.json)

- `ban_datetime_now.py` — integridade de timezone (`REGRAS_TIMEZONE.md`).
- `lembrar-regenerar-schemas.py` — regenera schema JSON (fonte de verdade) ao editar model.
- `lembrar-migration-par.py` — par `.py`+`.sql` (fora de escopo, ver §5).

### 1.3 Descoberta-chave (MEDIDA, não assumida)

O `lembrar-regenerar-schemas.py` foi desligado porque "mudar 1 campo reordenava
~50% dos campos". **Esse problema já foi corrigido** pelo subsistema "S0" do
`generate_schemas.py` (write-if-changed + ordenação canônica de todos os `set`;
`_dump_canonical` com `indent=2`, sem `sort_keys`, newline fixo). Provas desta sessão:

- Gerador a partir do working tree limpo → `0 escritos, 331 inalterados` (saída ==
  commitado ⇒ determinística).
- Inserir 1 coluna **no meio** do model `veiculos` e regenerar → `1 escrito`; diff do
  schema = **só o campo novo** (+6 linhas), **zero reordenação**. Revertido, git limpo.

**Consequência:** A0 vira "verificar (✓ feito) + religar com segurança".

### 1.4 Fundamentação do B2 (verificada)

- **0 blueprints** com `template_folder` custom → todo `render_template('x.html')`
  resolve em `app/templates/x.html` (resolução simples, sem falso-positivo por folder).
- 775 chamadas `render_template`; a esmagadora maioria com argumento **literal**
  (dinâmicos = ignoráveis). 699 templates `.html` em `app/templates`.

---

## 2. Arquitetura da solução

Princípio: **estender o padrão existente, não criar framework novo.**
- **Camada A (feedback):** hook Claude Code PostToolUse → avisa/age ao editar.
- **Camada B (gate):** auditor em `scripts/audits/` + wrapper em `scripts/hooks/`
  adicionado à cadeia `scripts/hooks/pre-commit`. Modo staged/`--enforce-added`.
  Bypass preservado: `git commit --no-verify`.

Config: estilo `scripts/audits/artefato_lint.config.json`. Aceite: **pytest
determinístico** por guardrail de camada B (preferência do Rafael — sem evals LLM).

---

## 3. Especificação dos fluxos (escopo final)

### A0 — Religar regeneração de schema (determinismo provado)
- **Ação:** adicionar `lembrar-regenerar-schemas.py` ao `settings.json` em
  `PostToolUse` matcher `Write|Edit`. Hook já idempotente; NUNCA apaga órfãos auto.
- **Correção necessária (descoberta na implementação):** o gerador leva ~45s
  (importa o app inteiro). O hook tinha `subprocess.run(timeout=30)` → estourava E,
  pior, rodaria SÍNCRONO travando o agente 45s a cada edição de model. Trocado por
  `subprocess.Popen(start_new_session=True)` — dispara em BACKGROUND e retorna em 0s.
- **Camada:** A. **Bloqueia?** Não.
- **Aceite:** editar um model → hook retorna imediato + regeneração em background;
  git mostra só o delta real; demais schemas intocados.

### A1 — Religar `ban_datetime_now` (integridade de timezone)
- **Ação:** adicionar `ban_datetime_now.py` ao `settings.json` em `PostToolUse`
  Write|Edit. (NÃO incluir `lembrar-migration-par` — ver §5.)
- **Camada:** A. **Bloqueia?** Não (PostToolUse → surfaça aviso; não desfaz a edição).
- **Aceite:** Write/Edit com `datetime.now()` naive → aviso citando
  `agora_utc_naive()`; exceções de timing/`timezone.py` continuam liberadas.

### B2 — Wiring rota↔template (pre-commit)
- **Arquivos:** `scripts/audits/route_template_audit.py` (novo) +
  `scripts/hooks/pre-commit-route-template-lint.sh` (novo) + entrada na cadeia
  `scripts/hooks/pre-commit`.
- **Lógica:** para cada `render_template('x.html')` **literal** em `.py` staged,
  verificar que `app/templates/x.html` existe → senão **block** (typo/arquivo ausente).
  Ignorar `render_template(var)` e f-strings (não-decidíveis). Suportar multilinha
  (`render_template(\n  '...'`). Resolução fixa em `app/templates/` (0 folders custom).
  Opcional (warn, fase 2): templates `.html` órfãos sem nenhum `render_template`.
- **Camada:** B. **Bloqueia?** Sim. Modo staged-only (`--enforce-added`).
- **Aceite (pytest):** rota referenciando template inexistente → exit≠0; existente →
  exit 0; `render_template(variavel)` → ignorado (exit 0).

---

## 4. Ordem de implementação (ROI)

1. **A0 + A1** — editar `.claude/settings.json` (custo ~zero; determinismo provado).
2. **B2** — novo audit + wrapper + entrada na cadeia + pytest.

A0/A1 são uma edição de config; B2 é o único item com código novo + testes.

---

## 5. Decisões registradas (cortes deste design)

- **A2 (gate de drift schema↔model):** cortado — redundante com A0 (auto-regenera);
  o usuário não erra drift na prática.
- **A3 (migration safety lint) e B1 (migration-pair hard gate):** cortados — o usuário
  não erra migrations; pair só era problema "antigamente" e não se justifica como gate.
- **`lembrar-migration-par` em camada A:** não religar (mesma razão).
- **Índice de sessões em aberto / handoff curado automático:** descartado após análise.
  O `.remember/now.md` já é atualizado automaticamente a cada turno (hook PostToolUse
  do plugin `remember`), então fechar a janela NÃO perde o estado; um índice de
  sessões abertas traria mais máquina (heartbeat + GC anti-zumbi) do que dor resolvida.
- **B3 (nome de campo front↔back↔DB), CI/Render, lint genérico, segurança:** fora das
  dimensões escolhidas / exigem spike próprio.

---

## 6. Plano de testes

`tests/audits/test_route_template_audit.py` (novo) com fixtures de `.py` simulando
rotas (template existente, inexistente, dinâmico, multilinha). A0/A1 validados por
smoke manual (editar model/`.py` observando stderr e regeneração). Sem evals LLM.

---

## 7. Status de implementação (2026-06-14) — CONCLUÍDO

Arquivos tocados/criados:
- `.claude/settings.json` — A0+A1 ligados em `PostToolUse` `Write|Edit`.
- `.claude/hooks/lembrar-regenerar-schemas.py` — execução trocada para background.
- `scripts/audits/route_template_audit.py` — audit B2 (novo).
- `scripts/audits/route_template_baseline.json` — baseline (22 rotas legadas, novo).
- `scripts/hooks/pre-commit-route-template-lint.sh` — wrapper B2 (novo).
- `scripts/hooks/pre-commit` — B2 adicionado à cadeia.
- `tests/audits/test_route_template_audit.py` — 19 testes (novo).

Validações executadas:
- A1: hook bloqueia `datetime.now()` naive, libera `datetime.now(tz)`.
- A0: hook retorna em 0s e dispara o gerador em background (gerador = ~45s,
  determinístico, git limpo).
- B2: 19/19 pytest verdes; smoke do gate (render novo quebrado → exit 1; válido →
  exit 0); `--all` com baseline → 0 achados.

> **Importante (atenção do A0):** os hooks do Claude Code só recarregam em NOVA
> sessão — A0/A1 entram em vigor a partir da próxima sessão.

### Achado lateral — backlog de limpeza (NÃO bloqueia)

O B2 detectou **22 rotas que renderizam template inexistente** (500 latente se
chamadas), congeladas no baseline. Candidatas a corrigir/remover (rotas mortas):
`fretes/lancar_fretes.html`, `localidades/dashboard.html`, `main/consulta_cliente.html`,
`main/relatorio_gerencial.html`, `main/odoo_integration.html`,
`manufatura/lista_materiais/estrutura.html`, `portal/configuracao.html`,
`portal/depara.html`, entre outras (lista completa em `route_template_baseline.json`).
Para auditar tudo: `python scripts/audits/route_template_audit.py --all --report-only`.

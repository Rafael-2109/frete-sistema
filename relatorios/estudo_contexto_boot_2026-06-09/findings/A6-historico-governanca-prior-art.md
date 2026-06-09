# A6 — Histórico, Governança e Prior Art Interno

**Subagente**: A6 (missão: evitar re-litigar o já decidido)
**Data**: 2026-06-09
**Repositório**: /home/rafaelnascimento/projetos/frete_sistema

---

## 1. Histórico do system_prompt.md — linha do tempo medida

### 1.1 Contagem de commits

- `system_prompt.md`: **100 commits** (2025-12-01 → 2026-06-09)
- `preset_operacional.md`: **7 commits** (2026-03-17 → 2026-06-05)

### 1.2 Crescimento de linhas — marcos verificados

| Hash | Data | Linhas | Evento |
|------|------|--------|--------|
| `b28dfaf30` | 2025-12-01 | 136 | Criação inicial do agente logístico |
| `2801018dc` | 2025-12-08 | 271 | Primeiras regras de negócio |
| `abcd90967` | 2025-12-13 | 448 | Consolidação inicial |
| `0a7d4fdac` | 2026-02-01 | 506 | Adição de capacidades SQL |
| `d32b5cf62` | 2026-04-12 | 406 | **Ponto de referência v4.2.0 (407L)**  ← "MUITO BOM" QUALITY_REVIEW |
| `86668052e` | 2026-04-12 | 529 | Quality Review findings aplicados → v4.3.0 (+122L) |
| `83cebd948` | 2026-05-13 | 726 | Melhorias D8 |
| `b156804cb` | 2026-05-21 | 822 | Melhorias D8 +40L |
| `f0567257a` | 2026-05-25 | 840 | SDK 0.2.82→0.2.87 |
| `5bd993455` | 2026-06-04 | **862** | **PICO** — language_policy + descoberta HORA |
| `34e4c899c` | 2026-06-05 | 858 | FASE 1 dedup (-4L) |
| `1c60d0bfe` | 2026-06-05 | 750 | **FASE 2 poda altitude** (-108L) |
| `fee8f1f17` | 2026-06-05 | 765 | **Restaura `<why>` cortados** (+15L — lição crítica) |
| `b1caa6286` | 2026-06-09 | **784** | HEAD atual |

**Conclusão numérica verificada:** 407L (abr/2026) → 862L (jun/2026 pico) = +112% em ~6 semanas. Recuo por poda: 862 → 784 (-78L, -9%).

### 1.3 preset_operacional.md

| Hash | Data | Linhas | Evento |
|------|------|--------|--------|
| `de1fe38e2` | 2026-03-17 | 75 | Criação com USE_CUSTOM_SYSTEM_PROMPT |
| `ab38769d8` | 2026-03-17 | 116 | Ativação como default |
| `3740880a7` | 2026-03-31 | 111 | GC memórias frias |
| `c03ec6ce9` | 2026-06-04 | 100 | Remove knowledge cutoff errado (FASE 1) |
| `34e4c899c` | 2026-06-05 | 97 | Dedup language/business_snapshot (FASE 1) |
| `785298a97` | 2026-06-05 | **117** | **T3.1: security_invariants no PRESET (FASE 3)** |

Arquivo fonte: `app/agente/prompts/preset_operacional.md:117` linhas atuais.

---

## 2. Governança FASE 5 — scripts e mecanismo exato

### 2.1 Localização dos artefatos

| Artefato | Caminho | Papel |
|----------|---------|-------|
| Hook principal | `scripts/hooks/pre-commit-prompt-lint.sh` | Detecta staging dos 3 arquivos → chama audit.py |
| Audit script | `scripts/audits/prompt_size_audit.py` | Medição + gating (`--check-delta`) |
| Baseline | `scripts/audits/prompt_size_baseline.json` | Estado de referência para delta |
| Dispatcher | `.git/hooks/pre-commit` | Chama `scripts/hooks/pre-commit` (encadeador) |
| Encadeador | `scripts/hooks/pre-commit` | ui-lint → doc-lint → script-lint → **prompt-lint** → claude-md-stats |

### 2.2 Funcionamento exato do `--check-delta`

O `pre-commit-prompt-lint.sh` vigia os 3 arquivos concatenados em `_build_full_system_prompt()`:
- `app/agente/prompts/preset_operacional.md`
- `app/agente/prompts/system_prompt.md`
- `app/agente/config/empresa_briefing.md`

Se algum dos 3 estiver staged, executa:
```
python3 scripts/audits/prompt_size_audit.py --check-delta
```

O script compara linhas atuais vs `prompt_size_baseline.json`:
- Se `system_prompt.md` atual > baseline OU total > baseline → **exit 1** (bloqueia commit)
- Se crescimento, exibe a régua R-EXEC-5 (princípio vs procedimento)
- Redução nunca bloqueia
- Bypass: `git commit --no-verify` (emergencial)

### 2.3 Baseline atual (HEAD)

```json
{
  "preset_operacional.md": {"linhas": 117, "bytes": 5079, "tokens": 1451},
  "system_prompt.md":      {"linhas": 784, "bytes": 48134, "tokens": 13752},
  "empresa_briefing.md":   {"linhas": 81,  "bytes": 5084,  "tokens": 1452},
  "total":                 {"linhas": 982, "bytes": 58297, "tokens": 16656}
}
```

Fonte: `scripts/audits/prompt_size_baseline.json` (lido diretamente).

### 2.4 Outros gates de tamanho/qualidade

- `--check N`: teto absoluto de linhas (bloqueador se total > N) — disponível mas não configurado como gate obrigatório
- `--update-claude-md`: atualiza bloco auto-medido no `app/agente/CLAUDE.md` (entre marcadores `<!-- prompt-size:start -->` e `<!-- prompt-size:end -->`)
- Cadência de review trimestral: próxima jul/2026 (registrada em `app/agente/CLAUDE.md:309`)
- **eval-gate**: baseado em golden dataset `.claude/evals/subagents/` (15 casos pilotos, 3 agents). Julgamento **MANUAL** (não automático). Sem CI/CD em PR (R14 ainda ABERTA).

---

## 3. Documentos "já decidido" — resumo do prior art

### 3.1 STUDY_PROMPT_ENGINEERING_2026.md — status e recomendações abertas que tocam o problema

**Status**: documento de referência criado em 2026-04-12 (data da avaliação v4.2.0).

**Pontos fortes já implementados** (NÃO re-litigar):
- XML tags estruturado ✅
- Progressive disclosure (skills) ✅
- 5-layer architecture ✅
- Prompt caching separation (vars dinâmicas via hook) ✅
- Flat subagent hierarchy (12 agents) ✅
- Constitutional L1-L4 ✅ (adicionado em v4.3.0)
- Dynamic context injection via hook ✅

**Recomendações ABERTAS que tocam macro-estrutura, redundância e memória:**

| ID | Recomendação | Status |
|----|-------------|--------|
| **G9** | Overtriggering audit (CRITICAL/MUST) | Downgraded P0→P3; 94% correto conforme audit R1 |
| **G1** | Few-shot `<example>` no system prompt | ABERTA — empurrado para R17 em skills |
| **G4** | Adaptive thinking não adotado explicitamente | ABERTA (R6 P1) |
| **G5** | Prefill audit | FECHADA — zero uso |
| **G6** | Golden dataset limitado (15 casos) | ABERTA (R5 P1) |
| **G13** | Memory content validation (injection) | ABERTA (R8 P1) |
| **G14** | Skill selection accuracy metric | ABERTA (R13 P2) |
| **RT-6.4** | 80 tok/skill × 50 skills = 4000 tok overhead | Relevante — 28 skills expostas no boot |
| **K: Context Management** | Dynamic injection via hook = padrão correto | JÁ IMPLEMENTADO; não mover vars para static |
| **L6** | Dynamic content via UserPromptSubmit hook | Padrão exemplar — session_context é o modelo correto |
| **PM-2.2** | Risco de context bloat via few-shot | Contramedida: few-shot em skills, não no system prompt global |
| **PM-2.1** | Dial back agressivo (CRITICAL/MUST) pode causar regressão comportamental | CONFIRMADO empiricamente pelo audit R1 — não fazer em lote |

**Lacunas de segurança com status:**

| Gap | Status |
|-----|--------|
| S1 PROMPT_INJECTION_HARDENING | ✅ FECHADO (R2 2026-04-12) |
| S2 session_context injection | ✅ FECHADO (R3 conforme) |
| S3 Memory injection (pgvector) | ABERTA (R8 P1) |
| S4 Subagent MCP output | ABERTA (R9 P2) |
| S5 Meta-instruction injection | FECHADO PARCIAL (security_invariants T3.1 aplicado) |

### 3.2 STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md — achados aplicados vs abertos

**Score v4.2.0:** 4.39/5 (MUITO BOM). Avaliação de um artefato que **não existe mais** (tinha 407L; hoje 784L).

**Findings aplicados em v4.3.0 (2026-04-12):**
- Q2: Constitutional hierarchy L1-L4 ✅
- Q3: Parallel tool calls bloco ✅
- Q4: Self-check pre-return em R2 ✅
- Q5: Context awareness prompt ✅
- Q6: Padronizar tags R0-R0d ✅
- Q7: Separar environment / business_snapshot ✅
- Q8: R10 Erros Transientes ✅
- CG1/CG2/CG5/CG6 ✅

**Findings NÃO aplicados (abertos):**
- **Q1**: Zero few-shot `<example>` formais → empurrado para R17 (skills, não system prompt)

**Dimensões mais fracas identificadas (tocar neste estudo):**
- **E (Thinking/Reasoning) = 2.6/5** — ausência de few-shot, self-check
- **F (Agentic Systems) = 3.25/5**
- **M (Constitutional Hierarchy) = 3.67/5** (tinha 3/5 antes, agora explícita)

**Lição da avaliação:** "tokens baratos (cache hit 10%); ROI de enxugamento BAIXO" — o problema não é tamanho, é redundância semântica + altitude errada.

### 3.3 ROADMAP_PROMPT_ENGINEERING_2026.md — R1-R17, status por prioridade

**P0 (todos fechados):**
- R1: Audit CRITICAL/MUST ✅ → 94% correto, downgrade P0→P3
- R2: PROMPT_INJECTION_HARDENING.md ✅
- R3: session_context audit ✅ conforme
- R4: Prefill audit ✅ zero uso

**P1 (todos ABERTOS):**
- R5: Golden dataset 15→50+ casos ❌ ABERTO
- R6: Adaptive thinking migration ❌ ABERTO
- R7: Context awareness prompt ❌ ABERTO (bloco planejado, não aplicado)
- R8: Memory injection validation ❌ ABERTO

**P2 (todos ABERTOS):**
- R9: Red team framework ❌
- R10: Tool error handling doc ❌
- R11: Cost tracking / cache hit rate ❌ (gap de instrumentação)
- R3b: XML escape user_name ❌
- R12: Multi-model LLM-as-judge ❌
- R13: Skill selection accuracy ❌

**P3 (todos ABERTOS):**
- R14: CI/CD evals em PR ❌
- R15: Structured outputs framework ❌
- R16: Agent Teams evaluation ❌
- R17: Few-shot em skills específicas ❌

**Conclusão de prioridade para este estudo:** R5 (golden dataset) é bloqueador de qualquer mudança comportamental validada. R6/R7/R8 são os P1 mais próximos do problema de macro-estrutura.

### 3.4 PROMPT_INJECTION_HARDENING.md — o que está fechado

- 12 seções, 6 layers defense in depth ✅
- Layer 3 (System Prompt Hardening): `<security_invariants>` + `<meta_instruction_alert>` aplicados no PRESET em T3.1 (`785298a97`) ✅
- Layer 2 (Prompt Templating): user input NÃO concatenado no system prompt ✅
- Gap ainda aberto: memory content validation (R8 P1)

---

## 4. agente/CLAUDE.md — evidências de arquitetura de contexto, R-SPLIT e caching

### 4.1 R-SPLIT-NGINX (afinidade de sessão)

Localização: `app/agente/CLAUDE.md:141` → `sdk/sticky_session.py` (R-SPLIT-NGINX Pattern 2).

No CLAUDE.md global: agente roda em gunicorn-agente (1 worker × 8 threads, porta 5001) isolado do gunicorn-sistema (4 workers × 2, porta 5002). Caddy faz proxy por path. Motivação: Claude Agent SDK é per-process; multi-worker quebra 409 após stream.

Relevância para contexto de boot: o boot sempre ocorre no mesmo processo gunicorn-agente (1 worker). Sem risco de split de contexto.

### 4.2 Prompt cache

`app/agente/CLAUDE.md:281` → `_format_system_prompt()` (guard cache): vars dinâmicas (`{data_atual}`, `{usuario_nome}`, `{user_id}`) extraídas do static system_prompt e injetadas via `_user_prompt_submit_hook()` como `<session_context>`. Sistema prompt estático = cache hits. Padrão L6 do STUDY = exemplar.

### 4.3 Governança FASE 5 — documentada em app/agente/CLAUDE.md:295-309

Seção "Governança do prompt (FASE 5 — impede a acreção de voltar)":
- Checklist OBRIGATÓRIO antes de adicionar regra (R-EXEC-5)
- Gatilho automático (pre-commit --check-delta)
- Cadência trimestral (próxima jul/2026)

### 4.4 3-layer architecture-alvo (plano 2026-06-04)

Definida em `docs/superpowers/plans/2026-06-04-refactor-governanca-prompt-agente.md:102-108`:
- **Camada 0** (system prompt, estático): identidade + constituição + regras como PRINCÍPIO + routing de alto nível
- **Camada 1** (skills/refs/hook, sob demanda): procedimento hiper-específico + enforcement determinístico
- **Camada 2** (injeção por turno): memórias/diretrizes com TETO, ordenadas estável→volátil

Esta arquitetura ainda é a "régua" vigente — está em uso nos checks R-EXEC-5.

---

## 5. Evidência da FASE 2 — reversão dos `<why>` cortados (M1 da avaliação)

**Commit que cortou os `<why>`:**
- `1c60d0bfe` (2026-06-05): FASE 2 poda de altitude, 858→750 linhas. Procedimento hiper-específico removido CORRETAMENTE. Mas `<why>` também foram comprimidos para perseguir target de -150/-250 linhas.

**Commit que RESTAUROU os `<why>`:**
- `fee8f1f17` (2026-06-05): "restaura `<why>` (A2/força) cortados por perseguir a métrica errada"

**Mensagem do commit fee8f1f17 (texto completo verificado):**
> "Correção após LER as FONTES do plano (STUDY + QUALITY_REVIEW) — que eu não havia verificado antes da T2.2. A meta da 'poda de altitude' NÃO é tamanho: STUDY insight #7: prompt vazado do Opus 4.6 ~200K tok com redundância INTENCIONAL — Anthropic não segue 'short prompts'; o recomendado é ponto de partida, não ceiling. QUALITY_REVIEW: 'tokens baratos (cache 10%); ROI de enxugamento é BAIXO'. QUALITY_REVIEW marca os `<why>` como Top Strength (A2 = 5/5)."

**Lição documentada em app/agente/CLAUDE.md:305:**
> "Motivacao (`<why>`) e' FORCA, nao gordura — explicar o porque melhora instruction following (A2 Top Strength 5/5). Comprimir SO' procedimento, NUNCA motivacao. (Licao da FASE 2: cortar `<why>` degradou e foi revertido — `fee8f1f17`.)"

---

## 6. Experimentos e ablações realizadas com resultados

### 6.1 R1 — Audit CRITICAL/MUST/NEVER/ALWAYS (2026-04-12)

**Método**: grep classificação das 117 ocorrências.
**Resultado**: 94% corretas (safety L1 + domain L3 + headers). Apenas 7 soft candidates.
**Decisão**: dial back em lote CANCELADO (alto risco PM-2.1 confirmado empiricamente).
**Lição**: linguagem imperativa em L1/safety é MAIS segura que positiva (STUDY RT-5.1). Projetos maduros com safety-critical NÃO devem dial back.

### 6.2 FASE 2 — Poda de altitude (2026-06-05)

**Método**: remover procedimento hiper-específico (R11.x, R12.x, R3.1) → Camada 1 (skills/refs).
**Resultado antes de correção**: 858→750 linhas (-108L), mas com `<why>` comprimidos.
**Resultado após correção**: 858→765 (-93L), todos os `<why>` restaurados.
**Lição**: meta é altitude, não tamanho. Procedimento sai; motivação fica.

### 6.3 T2.1 — Gate runtime action_update_taxes (2026-06-05)

**Commit**: `8954563fe`
**Método**: gate determinístico em código bloqueando `action_update_taxes` (regra R11.1 que estava no prompt).
**Resultado**: procedimento Odoo-específico saiu do prompt para enforcement de código.
**Validação**: pytest determinístico (não LLM eval).

### 6.4 T3.1 — security_invariants no PRESET (2026-06-05)

**Commit**: `785298a97`
**Decisão arquitetural**: vai no preset_operacional (dono de safety/awareness), NÃO no system_prompt. Evita defense em 2 lugares.
**Resultado**: preset 97→117 linhas. Consolida injection prevention em único lugar.

### 6.5 QUALITY REVIEW aplicado (2026-04-12 tarde) — v4.2.0 → v4.3.0

**Método**: 11 findings (Q2-Q8, CG1-CG2, CG5-CG6) aplicados em 1 commit coerente.
**Validação**: XML parse OK + 23 `<rule>` tags + 18/18 grep checks.
**Sem golden dataset** antes/depois (risco aceito, rollback pronto via git).
**Delta**: 407L → ~507L (+100L, +25%).

### 6.6 F1 + F2 — Custo/latência (fast-path baseline Marcus, abril/maio 2026)

Não é diretamente sobre o boot, mas relacionado: `baseline_fastpath.py` implementou fast-path determinístico sem LLM para tarefa repetitiva de Marcus (user_id=18). Flag `AGENT_BASELINE_FASTPATH`. Resultado: redução de custo em casos estruturados.

---

## 7. O que NÃO foi encontrado / gaps de informação

- Nenhum resultado quantitativo de judge score ou eval pass rate documentado nos commits (o golden dataset é manual, sem histórico de resultados).
- Cache hit rate não instrumentado (`agent_sessions.data` guarda só `total_tokens` scalar — R11 ABERTO).
- Não há ablação A/B dos blocos advisory (`world_model`, `skill_hints`) — C4 da avaliação do agente é hipótese, não medida.
- Resultados de judge para FASE 2 (poda de altitude) são verificações determinísticas (pytest + grep), não LLM judge.
- Nenhum teste vetorial formal de prompt injection (R9 ABERTO).

---

## 8. Referências cruzadas

| Documento | Caminho | Status |
|-----------|---------|--------|
| Plano refactor-governança | `docs/superpowers/plans/2026-06-04-refactor-governanca-prompt-agente.md` | FASE 3 parcialmente aberta |
| Study | `.claude/references/STUDY_PROMPT_ENGINEERING_2026.md` | Referência ativa |
| Quality Review | `.claude/references/STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` | Referência ativa |
| Roadmap | `.claude/references/ROADMAP_PROMPT_ENGINEERING_2026.md` | P1-P3 ABERTOS |
| Hardening | `.claude/references/PROMPT_INJECTION_HARDENING.md` | Layer 3 aplicada; R8 aberto |
| Baseline | `scripts/audits/prompt_size_baseline.json` | 982L / 16.6K tok |
| Audit script | `scripts/audits/prompt_size_audit.py` | Ativo, armado |
| Hook | `scripts/hooks/pre-commit-prompt-lint.sh` | Ativo |
| Agente CLAUDE.md gov. | `app/agente/CLAUDE.md:295-309` | Regras vigentes |

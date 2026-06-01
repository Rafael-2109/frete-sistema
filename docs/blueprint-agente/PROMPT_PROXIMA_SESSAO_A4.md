# PROMPT — Iniciar A4 (promoção de diretriz) SEM repetir o drift da sessão A3

> Estado em 2026-06-01. A3 (gate de regressão) está MERGEADA em main, PUSHADA (deploy PROD),
> flags OFF. Próximo: A4-batch — a última feature do flywheel, a mais arriscada (muda comportamento
> ATIVO do agente). Fonte da verdade: `docs/blueprint-agente/EXECUCAO.md`.

---

## LIÇÃO DA SESSÃO A3 (ler PRIMEIRO — é o motivo deste prompt existir)

Na sessão A3 houve um **drift de interpretação**: depois de medir o baseline, o Claude quis
"reescrever os golden datasets para alinhar ao ambiente" — tratando o sintoma errado. O Rafael
mandou **RELER A SPEC**, e a releitura revelou que a A3 é **gate de regressão** (mede Δ código-antes
vs depois), NÃO um vestibular que dá nota. O score absoluto era de baixo valor por design; o viés
do dataset se cancela no Δ. **A resposta sobre o telos estava na própria documentação do projeto
(`eixos/A-flywheel.md`), que o próprio Claude escreveu.**

**REGRA INVIOLÁVEL DESTA SESSÃO (anti-drift):**
1. **ANTES de qualquer código ou decisão de escopo da A4, RELER na íntegra:**
   - `eixos/A-flywheel.md` seção 2.3 (§ "Promoção automática gated por eval") + Fase A4 (§ Parte 3).
   - `critica/A-flywheel.md` — a elevação `attribution_judge` + os 3 ajustes obrigatórios + o
     risco de **reward-hacking** (C1) que a A4 introduz se feita errado.
   - `eixos/A-flywheel.md` Ruptura #2 e #4 (o que a A4 liga e por que estava OFF).
2. **NÃO inventar dicotomia para o usuário quando a spec já decide.** Se surgir uma escolha de
   escopo, primeiro PERGUNTAR à doc: "a spec já responde isto?". Só levar ao Rafael o que a doc
   genuinamente deixa em aberto.
3. **O telos da A4 (da spec):** ligar `USE_OPERATIONAL_DIRECTIVES` COM SEGURANÇA (Ruptura #2) —
   promover uma heurística empresa a `<operational_directives>` (diretriz obrigatória) só depois de
   um pipeline: candidata → shadow/A-B → **regression-gate (a A3 que acabamos de construir)** →
   promove → monitora drift → auto-despromove. A4 varia **DIRETRIZ** (a A3 varia código — não
   confundir; foi um erro recorrente na sessão A3).

---

## O QUE JÁ EXISTE PARA A A4 (recon feita na sessão A3 — confirmar antes de usar)

- `app/agente/services/directive_promotion_service.py` (LÓGICA SHADOW, flag OFF):
  - `propose_directive_from_plan(...)`: plano-completed → candidata.
  - `evaluate_and_promote(candidate, baseline_score, candidate_score)`: **já implementa a hierarquia
    correta da spec** — `_tem_falha_odoo` (âncora ambiental R9, anti-reward-hacking) é checada ANTES
    do gate de score; depois `eval_gate(baseline, candidate, report_only)`; shadow só LOGA
    (`would_promote`, não escreve). `_persist_directive` é **stub NotImplementedError**.
  - Flag: `AGENT_DIRECTIVE_PROMOTION` (OFF) + `USE_OPERATIONAL_DIRECTIVES` (OFF).
- `_build_operational_directives` (`memory_injection.py:420`): JÁ MONTA o bloco
  `<operational_directives priority="critical">` (seleção por importance>=0.7, ordena por
  effective_count). O R0d do system_prompt já instrui o agente a tratar como REGRA. **Pronto e
  parado** — a A4 só liga isto com o gate na frente.
- A3 (recém-construída, esta sessão): `run_eval_regression_gate` + `eval_gate` + `agent_eval_scores`
  + `agent_eval_case` (calibração). É o **regression-gate** que o pipeline A4 consome.

## O QUE FALTA (a A4-batch — recon + plano + impl):
- **Job batch (D8)** que varre PlanStates bem-sucedidos → `propose_directive_from_plan` →
  `evaluate_and_promote` (gate A3 + anti-gaming R9) → (gated) promove.
- **Migration dupla** `directive_status` (estado: `candidata|shadow|ativa|despromovida`) — coluna nova,
  NÃO redefinir in-place (lição da crítica: 3 consumidores acoplados a `effective_count`).
- `_persist_directive` real (hoje stub).
- **DECISÃO DE DESIGN ABERTA (levar ao Rafael):** a spec pede A/B shadow ("injeta diretriz só p/ %
  do tráfego, mede Δ com vs sem"). Isso depende de instrumentar "qual diretriz rodou em qual turno"
  — que NÃO existe (a crítica E §1.3 e §4 apontam). Avaliar: A4 V1 começa só com o regression-gate
  OFFLINE (golden dataset, sem A/B de produção) — a spec PERMITE (`A-flywheel.md:266` análogo ao da
  A3). O A/B de produção fica para A4 V2 (depende de A1 `agent_turn_quality`, que é shadow).

---

## CADÊNCIA (mantida — a que funcionou na A3):
- **Subagent-driven**: 1 subagente/tarefa (implementer TDD) + spec-review + code-review adversarial.
- **Verificação do Claude entre etapas**: rodar a SUÍTE COMPLETA `pytest tests/agente/ -q` (não só os
  testes do item — na A3 a suíte completa pegou uma regressão que o teste isolado não viu).
- **TUDO flag-OFF**. Migration dupla se houver schema. **NÃO pushar sem autorização** (push=deploy).
- Best-effort INV-6. Âncora ambiental Odoo R9 DOMINA (anti-reward-hacking — crítico na A4).
- Atualizar `EXECUCAO.md` a cada item.
- **Gotcha ambiente**: worktree sem `.env` → `export DATABASE_URL` da raiz (localhost) antes de pytest.
- **Gotcha persistência**: serviços que rodam invokes longos antes de tocar DB sofrem SSL-drop —
  rodar a parte longa FORA do app_context, persistir com conexão fresca (ver A3-R2/fix SSL-drop).

## SETUP:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema/.claude/worktrees/agente-evolucao  # OU nova worktree
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
export DATABASE_URL=$(grep -E '^DATABASE_URL=' /home/rafaelnascimento/projetos/frete_sistema/.env | head -1 | cut -d= -f2-)
git fetch origin main   # A3 já está em main; partir de lá
```

## PRIMEIRO PASSO DA SESSÃO (não pular):
1. Reler os 3 docs da seção "LIÇÃO" acima.
2. Rodar o recon read-only da A4 (confirmar o que existe vs o que a recon da A3 anotou).
3. APRESENTAR o plano writing-plans da A4 ANTES de codar — destacando a DECISÃO ABERTA (V1 offline
   vs A/B produção) para o Rafael decidir. NÃO iniciar implementação sem o OK do plano.

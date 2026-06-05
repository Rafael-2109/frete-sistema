<!-- doc:meta
tipo: how-to
camada: L3
sot_de: prompt de retomada da proxima sessao do refactor do prompt do Agente Web (FASE 2)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-05
-->
# Prompt para a próxima sessão — Refactor do Prompt do Agente (FASE 2)

> **Papel:** texto para colar ao iniciar a próxima sessão de Claude Code e retomar o
> refactor do prompt do Agente Web na **FASE 2 (poda de altitude)**. O handoff também está
> no topo do plano.

## Cole isto ao iniciar a nova sessão

```
Retome o refactor do prompt do Agente Web — agora a FASE 2 (poda de altitude).

ANTES DE QUALQUER ACAO, leia o plano:
  docs/superpowers/plans/2026-06-04-refactor-governanca-prompt-agente.md
Foque em: Regras de Execucao INVIOLAVEIS (R-EXEC-1..6), o Rastreamento, e as
Notas de execucao das FASES 0 e 1.

Estado (tudo em PROD):
- FASE 0 fechada. T0.2 resolvido: a tabela agent_session_costs estava vazia
  porque a flag AGENT_COST_TRACKER_PERSIST estava OFF (NAO era bug de codigo;
  a hipotese "savepoint orfao" foi refutada por TDD — ha commit-on-teardown).
  A flag ja' foi LIGADA + deploy. Baseline de tamanho congelado = 1036 linhas
  / ~17,4K tok.
- FASE 1 completa: higiene factual + dedup (cutoff, context_awareness, language,
  business_snapshot). Cada conceito com dono unico, info 100% preservada.

PRIMEIRO ATO desta sessao (barato, fecha T0.2 empiricamente): confirmar via MCP
Render que agent_session_costs JA TEM linhas (a flag esta ON ha' ~1 dia). Se sim,
H1 confirmado e o T0.3 ganha custo/cache real. Se nao, investigar.

Proximo = FASE 2 (poda de altitude). O system_prompt ainda tem 858 linhas (o
inchaco que originou este plano). ORDEM CRITICA E INVIOLAVEL:
  T2.1 (estender o gate runtime PreToolUse para Odoo-write R11.1/R12) ANTES de
  T2.2 (comprimir as regras hiper-especificas no prompt).
A defesa vira CODIGO (gate, testavel por pytest) ANTES de o texto sair do prompt.

Regras que valem para esta sessao (licoes das anteriores — NAO repetir os erros):
- R-EXEC-3: verifique a premissa de CADA task ANTES de executar. Premissa critica
  da T2.1: o gate runtime cobre 100% do que R11/R12 defendem? HOJE NAO —
  action_update_taxes (R11.1) nao esta coberto pelo gate; UPDATE/DELETE em massa
  via Bash/SQL pode nao ser interceptavel como as tools Odoo nomeadas. Trecho que
  SO' o prompt protege NAO pode ser podado (T2.2) sem defesa equivalente — senao
  e' "fazer pela metade".
- SEM LLM eval. A prova de "antes/depois" e' DETERMINISTICA: pytest do gate +
  prompt_size_audit (tamanho caiu) + smoke + balanco de tags. Rafael VETA eval LLM
  caro ("custou fortuna e nada conclusivo").
- HIPOTESE BARATA PRIMEIRO: se algo "nao funciona/nao produz dado", a 1a suspeita
  e' flag OFF — checar/ligar antes de diagnostico de codigo. (T0.2 foi tempo
  perdido num diagnostico errado para algo que era so' a flag.)
- 1 commit por task; sem [skip render]; rollback documentado = git revert.
- Nao seguir o plano "na risca" cego: ele e' a regua, nao a ordem de marcha.

Comece confirmando o estado REAL (git, flag/tabela de custo, suite pytest do
agente verde) e me apresente o plano da FASE 2 — com a premissa do gate ja'
verificada — ANTES de tocar em qualquer coisa.
```

## Contexto rápido (se a nova sessão precisar)

- **Origem:** avaliação do prompt do Agente Web em 2026-06-04 (system_prompt ~862 linhas /
  ~15K tok; doc afirmava ~2,7K — 6,5x defasada; crescimento por acreção reativa).
- **O que já foi feito (2 sessões):**
  - FASE 1 — higiene/dedup: cutoff factual, `context_awareness`, `language`, `business_snapshot`.
    Cada conceito com dono único; tamanho 1054→1036 linhas. Validação determinística.
  - FASE 0 — reenquadrada (R-EXEC-3 sobre R-EXEC-1): **sem golden dataset LLM**; prova
    determinística. T0.2 (instrumentação de custo) resolvido = só ligar a flag.
- **Lição central das 2 sessões:** o trabalho gigante de T0.2 (diagnóstico de "savepoint
  órfão") foi desperdício — a causa era a flag OFF. Para a FASE 2: testar a hipótese mais
  barata primeiro, verificar premissa, e provar por pytest/medição (nunca LLM).
- **FASE 2 — o que ela faz:** tira procedimento hiper-específico da Camada 0 (system_prompt)
  **sem remover defesa**. T2.1 garante o enforcement determinístico (gate runtime) ANTES de
  T2.2 comprimir o texto. Alvo: −150 a −250 linhas, zero regressão no gate (pytest).
- **Premissa GATED da FASE 2 (já mapeada):** o gate runtime (`permissions.py:306-375,917-950`,
  flag `AGENT_REVERSIBILITY_CHECK`) hoje cobre `ajustando-quant`/`transferindo-interno`/
  `planejando-pre-etapa`, mas **NÃO** `action_update_taxes` (R11.1) nem UPDATE/DELETE em massa
  via Bash. Estender o gate é T2.1; o que não for cobrível por gate não pode sair do prompt.

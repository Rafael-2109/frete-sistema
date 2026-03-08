# Avaliacao Detalhada: GSD vs Ralph Wiggum Loop

**Data**: 07/03/2026
**Autor**: Rafael + Claude (Precision Engineer Mode)
**Contexto**: Sistema de frete Nacom (~500+ arquivos, 120+ tabelas, 20+ modulos)

---

## 1. O QUE E CADA UM

### Ralph Wiggum Loop

**Origem**: Geoffrey Huntley (jan/2026). Nomeado pelo personagem dos Simpsons — uma homenagem a giria dos anos 80 ("ralph" = vomitar) e a combinacao de ignorancia, persistencia e otimismo do personagem.

**Essencia**: Um loop Bash que alimenta repetidamente um prompt ao Claude CLI, cada iteracao com contexto fresco.

```bash
while true; do
  cat PROMPT.md | claude -p --dangerously-skip-permissions --model opus
  git push
done
```

**Filosofia**: "Falhas viram dados. Cada iteracao refina a abordagem." O progresso vive nos arquivos e no historico git — quando o contexto enche, um novo agente com contexto fresco continua de onde o anterior parou.

**Adocao**: Utilizado por startups da Y Combinator. Anthropic criou um plugin oficial Ralph Wiggum no marketplace do Claude Code. Matt Pocock declarou que "Ralph Wiggum + Opus 4.5 is really, really good."

### GSD (Get Shit Done)

**Origem**: TACHES (fev/2026). Framework open-source no GitHub (`gsd-build/get-shit-done`).

**Essencia**: Sistema de meta-prompting, context engineering e spec-driven development com agentes especializados (Planner, Executor, Verifier, Debugger). Instalado via `npx`.

**Filosofia**: "Voce e o arquiteto. Agentes sao os operarios. Specs sao o blueprint." Nasceu como reacao a ferramentas SDD complexas — rejeita "sprint ceremonies, story points, retrospectives e Jira workflows."

**Adocao**: Segundo o repositorio oficial, usado por engenheiros da Amazon, Google, Shopify e Webflow (sem verificacao independente). Suporta Claude Code, OpenCode, Gemini CLI e Codex.

---

## 2. ARQUITETURA COMPARADA

| Aspecto | Ralph Wiggum | GSD |
|---------|-------------|-----|
| **Complexidade** | Minimalista (~100 linhas de config) | Framework completo (~2K+ linhas, instalador npx) |
| **Loop** | Bash `while true` externo | Skills/commands integrados (`/gsd:plan-phase`, `/gsd:execute`) |
| **Prompts** | 2 fixos (plan + build) | Multiplos, por fase e papel |
| **Agentes** | 1 agente principal + subagentes ad-hoc | Agentes tipados (Planner, Executor, Verifier, Debugger) |
| **Estado** | `IMPLEMENTATION_PLAN.md` + `specs/` | Roadmap + Phase Plans + Task lists + Specs + STATE.md |
| **Contexto** | Fresco a cada iteracao (mata e reinicia processo) | Fresco por design (subagentes efemeros, max 3 tasks/plan) |
| **Validacao** | Testes/lint como backpressure | Verifier agent + testes + smoke tests auto-injetados |
| **Multi-LLM** | Claude-only | Claude, OpenCode, Gemini CLI, Codex |
| **Seguranca** | Docker recomendado (`--dangerously-skip-permissions`) | Herda do CLI host |
| **Granularidade** | 1 tarefa por iteracao | 2-3 tarefas por plano, waves paralelas |
| **Memoria** | Git como camada de memoria | Arquivos de estado (PROJECT.md, REQUIREMENTS.md, STATE.md) |
| **Versao atual** | N/A (tecnica, nao software) | v1.22.4 (03/mar/2026) |

### Modelo de Contexto

| Metrica | Ralph | GSD |
|---------|-------|-----|
| Budget total | ~200K tokens | ~200K tokens |
| Smart zone | 40-60% (~70-100K tokens) | 30-50% (~60-100K tokens) |
| Estrategia | Matar processo = reset total | Subagentes efemeros = reset por tarefa |
| Context rot | Eliminado por design | Mitigado por atomicidade |

---

## 3. PROS E CONTRAS — RALPH WIGGUM

### PROS

**1. Simplicidade brutal**
- Literalmente um `while true` + prompt. Qualquer dev entende em 5 minutos.
- Zero dependencias alem do Claude CLI.
- Nosso `ralph-loop.sh` tem 86 linhas incluindo comentarios e formatacao.
  - FONTE: `.claude/ralph-loop/ralph-loop.sh` (86 linhas)

**2. Contexto fresco real**
- Cada iteracao MATA o processo e reinicia. Zero context rot.
- O agente nunca "esquece" ou "confunde" porque nao acumula contexto.
- Este e o insight mais valioso da tecnica — manter o agente na "Smart Zone" de raciocinio.

**3. Uma tarefa por iteracao = commits atomicos**
- Cada iteracao produz exatamente 1 commit focado.
  - FONTE: `.claude/ralph-loop/PROMPT_build.md:1-6` — "Complete EXACTLY ONE task per iteration"
- Se algo deu errado, `git reset --hard HEAD~1` desfaz cirurgicamente.
- Historico de git fica limpo e rastreavel.

**4. Backpressure natural**
- Testes/lints atuam como guardrails automaticos (upstream + downstream steering).
  - FONTE: `.claude/skills/ralph-wiggum/references/workflow.md:49-59`
- Se o agente implementa algo errado, testes falham, ele anota no plano e para.
- Proxima iteracao tenta de novo com contexto fresco.

**5. Escape hatches claros**
- `Ctrl+C` para parar, `git reset` para reverter, deletar plano para recomecar.
- Transparencia total: tudo e arquivo texto legivel.
  - FONTE: `.claude/skills/ralph-wiggum/references/workflow.md:73-80`

**6. CLAUDE.md respeitado nativamente**
- O agente roda no mesmo diretorio do projeto — `CLAUDE.md` e carregado automaticamente pelo Claude CLI.
- `PROMPT_build.md:13` explicitamente instrui: "Reference CLAUDE.md for field names, conventions, and validation rules."
- Nosso CLAUDE.md com 200+ linhas de regras criticas e respeitado em todas as iteracoes.

**7. Comprovado no nosso projeto**
- Usado para o projeto `correcoes-recebimento-cnpj-empresa-produto`.
- 22 tarefas planejadas, 22 implementadas, 7 fases concluidas (v1.8.0).
- Spec de 307 linhas gerou implementacao real em producao.
  - FONTE: `.claude/ralph-loop/IMPLEMENTATION_PLAN.md` (721 linhas, status CONCLUIDO)

### CONTRAS

**1. `--dangerously-skip-permissions` e PERIGOSO**
- O agente pode ler/escrever QUALQUER coisa no sistema.
- API keys, SSH keys, cookies expostos.
- Docker mitiga, mas adiciona complexidade e fricao.
- **RISCO REAL**: sem Docker, um prompt injection em qualquer arquivo lido pode exfiltrar credenciais.

**2. Custo alto e imprevisivel**
- 50 iteracoes em codebase grande = $50-100+ em API credits (Opus).
- Sem mecanismo de parada inteligente nativo — roda ate o limite ou `Ctrl+C`.
  - NOTA: Implementacoes como `frankbria/ralph-claude-code` adicionam "intelligent exit detection", mas nao e padrao.
- Se o agente "empaca" em algo, queima tokens sem progresso.

**3. Zero julgamento estetico**
- Ralph nao tem "gosto". Nao sabe se o codigo e elegante ou gambiarrado.
- Tarefas subjetivas ("melhore a arquitetura") causam loops infinitos ou falsa vitoria.
- So funciona com criterios de sucesso OBJETIVOS e VERIFICAVEIS.

**4. Sem verificacao formal**
- O proprio agente decide se "completou" a tarefa.
- Nao ha um segundo agente validando.
- Se os testes nao cobrem o cenario, bugs passam silenciosamente.

**5. Monitoramento manual**
- Geoffrey Huntley explicitamente disse: "You really want to babysit this thing."
- Nao e "fire and forget" — exige supervisao humana regular.
- Deixar rodando overnight sem monitorar e receita para desperdicio.

**6. Escala limitada para features grandes**
- Para features com muitos arquivos e dependencias, uma tarefa por iteracao pode ser lento.
- O plano pode ficar stale entre iteracoes se o codebase muda por outros meios.

**7. Sem orquestracao multi-agente sofisticada**
- Subagentes sao ad-hoc, sem roles definidos formalmente.
- Nao ha pipeline de verificacao, debugging automatico, ou QA estruturado.

---

## 4. PROS E CONTRAS — GSD

### PROS

**1. Estrutura profissional**
- Ciclo completo: Idea -> Roadmap -> Phase Plan -> Atomic Execution -> Verify.
- Cada fase tem prompts especializados e agentes tipados.
- Mais proximo de como um time de engenharia opera.

**2. Agentes especializados**
- Planner, Executor, Verifier, Debugger — cada um com escopo definido.
- Verifier valida ANTES de aceitar trabalho. Debugger trata falhas automaticamente.
- Smoke tests sao auto-injetados na fase de verificacao (v1.22.3+).
- Isso e superior ao Ralph onde o mesmo agente faz tudo.

**3. Multi-LLM**
- Funciona com Claude, OpenCode, Gemini CLI, Codex.
- Nao esta preso a um vendor. Pode trocar modelo conforme custo/qualidade.
- Instalador unificado via `npx` padroniza para qualquer runtime.

**4. Context engineering consciente**
- Mantem contexto a 30-50% da janela por subagente.
- Thin orchestrator pattern: orquestrador leve spawna subagentes focados.
- Max 3 tasks por plan = nenhuma tarefa e grande o suficiente para degradar qualidade.
- Waves: tarefas independentes rodam em paralelo, dependentes esperam.

**5. Comunidade ativa**
- GitHub com issues, PRs, releases frequentes (v1.22.4 em 03/mar/2026).
- 47 testes de consistencia de agentes adicionados recentemente.
- Documentacao rica e licoes interativas (ccforeveryone.com/gsd).

**6. Discuss phase com contexto**
- Fase de discussao carrega PROJECT.md, REQUIREMENTS.md e STATE.md.
- Analise code-aware do codebase antes de planejar (v1.22.0+).

### CONTRAS

**1. Complexidade significativa**
- Framework pesado com muitos conceitos: roadmaps, milestones, phases, tasks, specs, granularity.
- Curva de aprendizado alta (estimativa: 2-4 horas para ser produtivo).
- Para tarefas pequenas/medias, o overhead nao compensa.

**2. Subagentes e CLAUDE.md — Bug CORRIGIDO mas com ressalvas**
- **Issue #671** (aberta e FECHADA em 19/fev/2026): Executors nao herdavam `CLAUDE.md`.
- **Correcao**: Agentes agora leem `./CLAUDE.md` quando existe no diretorio de trabalho.
- **Ressalva**: A correcao depende do agente LER o arquivo — nao e injetado no contexto como no Ralph.
  - No Ralph, CLAUDE.md e carregado AUTOMATICAMENTE pelo CLI como instrucao de projeto.
  - No GSD, o agente precisa seguir a instrucao de "read CLAUDE.md if it exists".
  - Se o agente estiver com contexto apertado, pode pular ou resumir o CLAUDE.md.
- **IMPACTO PARA NOS**: Nosso CLAUDE.md tem regras criticas (timezone, campos de tabelas, terminologia brasileira). Qualquer omissao causa bugs sutis.
  - FONTE: `CLAUDE.md` (raiz do projeto, 200+ linhas de regras)

**3. "Context rot e temporario" — argumento filosofico**
- A premissa central do GSD (combater context rot) e um workaround para limitacoes atuais dos LLMs.
- Quando modelos tiverem janelas maiores e melhor recall, muito do GSD perde razao de existir.
- Ralph tem o mesmo problema, mas e tao simples que adaptar e trivial.
- Nota: Matt Pocock ja comentou que Opus 4.5 torna Ralph "less necessary for many tasks".

**4. Custo potencialmente maior que Ralph**
- Multiplos agentes especializados = mais chamadas de API.
- Planner + Executor + Verifier + Debugger = 3-4x o custo por tarefa.
- O framework promete que evita retrabalho, mas nao ha benchmarks independentes de custo.

**5. Claims de adocao sem verificacao**
- "Usado na Amazon/Google/Shopify" — constam no README oficial, sem auditoria independente.
- "100K linhas em 2 semanas" — sem auditoria de qualidade dessas linhas.
- Marketing agressivo pode inflar expectativas.

**6. Over-engineering para projetos menores**
- Para nosso sistema de frete (500+ arquivos mas 1 dev), GSD e potencialmente overkill.
- A cerimonia de Roadmap -> Milestone -> Phase -> Task adiciona burocracia.
- GSD foi desenhado para times — solo developer pode nao extrair valor proporcional.

---

## 5. NOSSA EXPERIENCIA REAL COM RALPH

### Projeto: `correcoes-recebimento-cnpj-empresa-produto`

| Metrica | Valor |
|---------|-------|
| Spec | 307 linhas |
| Fases | 7 (CNPJ, cod_produto, propagacao, revalidacao, busca, finalizado_odoo, migracao) |
| Tarefas planejadas | 22 |
| Tarefas implementadas | 22 (100%) |
| Versao final | v1.8.0 + v1.9.0 (verificacao) |
| Arquivos modificados | 5 |
| Arquivos criados | 4 (scripts de migracao) |
| Bugs encontrados em producao | 4 (100% corrigidos) |
| Status | CONCLUIDO e em producao |

FONTE: `.claude/ralph-loop/IMPLEMENTATION_PLAN.md` (721 linhas documentando cada fase)

### O que funcionou bem

1. **Gap analysis preciso**: Fase de planejamento identificou 8 discrepancias entre plano e realidade do codigo (v1.2.0).
2. **Commits atomicos**: Cada fase produziu commit isolado, facil de auditar.
3. **Backpressure via `py_compile`**: Sintaxe validada automaticamente a cada iteracao.
4. **Documentacao como subproduto**: O IMPLEMENTATION_PLAN.md virou documentacao viva do que foi feito e por que.
5. **Correcao de rota**: Quando a Fase 6 revelou que o comportamento era intencional (nao bug), o plano foi atualizado sem desperdicio.

### O que poderia ser melhor

1. **Sem verificacao automatizada pos-implementacao**: Precisamos validar manualmente que as 5 ocorrencias de `nfe_infnfe_dest_xnome` foram corrigidas.
2. **Sem testes unitarios**: O projeto nao tinha testes para o modulo, entao backpressure ficou limitada a `py_compile`.
3. **Custo nao rastreado**: Nao medimos o custo em tokens/dolares das iteracoes.

### Estrutura de Arquivos Ralph no Projeto

```
.claude/ralph-loop/
  ralph-loop.sh           # 86 linhas — loop principal
  PROMPT_build.md         # 37 linhas — instrucoes de build
  PROMPT_plan.md          # 20 linhas — instrucoes de planejamento
  AGENTS.md               # 27 linhas — guia operacional
  IMPLEMENTATION_PLAN.md  # 721 linhas — plano real concluido
  specs/                  # Diretorio de specs

.claude/skills/ralph-wiggum/
  SKILL.md                # 128 linhas — skill do Claude Code
  SCRIPTS.md              # Descricao dos scripts
  references/workflow.md  # 151 linhas — referencia de workflow
  scripts/init_ralph_project.py  # Inicializador de estrutura
```

FONTES: Todos os arquivos listados acima foram lidos e verificados.

---

## 6. COMPARACAO DIRETA PARA NOSSO CASO

| Criterio | Ralph | GSD | Vencedor |
|----------|-------|-----|----------|
| **Simplicidade** | Loop bash + 2 prompts | Framework completo npx | **Ralph** |
| **Curva de aprendizado** | 15 min | 2-4 horas | **Ralph** |
| **Qualidade de output** | Depende de specs + testes | Verifier agent valida | **GSD** |
| **Custo por feature** | Medio ($10-50) | Alto ($20-100+) | **Ralph** |
| **Seguranca** | Perigoso sem Docker | Herda do host | Empate |
| **Nosso CLAUDE.md** | Carregado automaticamente pelo CLI | Lido pelo agente (corrigido #671) | **Ralph** |
| **Features grandes** | Lento (1 task/iteracao) | Paralelismo nativo (waves) | **GSD** |
| **Fire-and-forget** | Nao (precisa babysit) | Nao (precisa babysit) | Empate |
| **Experiencia real** | Testado e funcionou (22/22 tarefas) | Nao testamos | **Ralph** |
| **Adaptabilidade** | Trivial (editar 2 prompts) | Media (entender framework) | **Ralph** |
| **Multi-LLM** | Claude-only | 4 runtimes | **GSD** |
| **Verificacao pos-impl** | Manual | Automatizada (Verifier) | **GSD** |
| **Comunidade/suporte** | Tecnica viral, varias impls | Framework mantido, releases frequentes | **GSD** |
| **Maturidade** | Conceito estavel | v1.22.4, evolucao rapida | **GSD** |

**Resultado**: Ralph 7 x 5 GSD (2 empates)

---

## 7. OPINIAO HONESTA

### Ralph Wiggum

**E uma boa tecnica? SIM**, com ressalvas.

O insight central — contexto fresco + uma tarefa por iteracao + backpressure via testes — e genuinamente valioso e comprovado. Funciona bem para tarefas mecanicas com criterios objetivos. O perigo real e o `--dangerously-skip-permissions` e a tentacao de "fire and forget".

**Para nos**: Ja funciona, ja testamos em producao (22/22 tarefas concluidas), respeita nosso CLAUDE.md nativamente. O custo-beneficio e bom para features medias (10-30 tarefas).

### GSD

**E uma boa tecnica? DEPENDE.**

Para times grandes com projetos greenfield e orcamento de API, pode ser excelente. A estrutura de agentes tipados (Planner/Executor/Verifier/Debugger) e genuinamente superior ao modelo "agente faz tudo" do Ralph. O suporte multi-LLM e uma vantagem estrategica real.

**Para nos**: NAO recomendo adotar AGORA. Motivos:
1. O overhead nao compensa para 1 dev.
2. A correcao do #671 melhora mas nao garante que nosso CLAUDE.md sera respeitado integralmente.
3. Ja temos Ralph funcionando — trocar de ferramenta tem custo de migracao sem beneficio claro.
4. GSD ainda evolui rapido (v1.20 -> v1.22 em 2 semanas) — instabilidade de API/convencoes.

### A Visao Complementar

Uma perspectiva importante da comunidade: **Ralph e GSD nao sao necessariamente concorrentes**.

> "Open Spec without Ralph Wiggum is fragile... Ralph Wiggum without Open Spec is chaos."

Ralph e um **padrao de execucao** (runtime pattern). GSD/SDD e um **framework de especificacao** (requirements framework). O Ralph precisa de specs boas para funcionar — e nos ja temos isso (nosso `specs/` + `IMPLEMENTATION_PLAN.md`).

---

## 8. RECOMENDACAO: HIBRIDO PRAGMATICO

O melhor para nosso caso e pegar o que funciona de cada:

### De Ralph (MANTER)
- Loop simples com contexto fresco
- 1 task por iteracao = commits atomicos
- Git como camada de memoria
- CLAUDE.md carregado nativamente

### De GSD (INCORPORAR)
- **Conceito de Verifier agent**: Adicionar um passo de verificacao pos-implementacao no loop.
- **Smoke tests auto-injetados**: Executar testes automaticamente antes de marcar tarefa como concluida.
- **Guardrails file**: Capturar falhas conhecidas para iteracoes futuras (GSD faz isso com STATE.md).

### Implementacao Sugerida

Nosso Ralph ja faz 90% do que precisamos. O 10% que falta (verificacao pos-implementacao) pode ser adicionado com um passo simples no `ralph-loop.sh`:

```bash
# Apos a iteracao do agente, rodar verificacao basica
python -m py_compile app/**/*.py 2>/dev/null
pytest app/tests/ -x --tb=short 2>/dev/null
ruff check app/ --quiet 2>/dev/null
```

Isso daria backpressure sem adotar o framework GSD inteiro.

### Quando Reavaliar GSD

Revisitar esta decisao se:
1. O time crescer para 2+ devs trabalhando em paralelo.
2. O codebase ultrapassar 1000 arquivos com interdependencias complexas.
3. A issue #671 for complementada com injecao automatica de CLAUDE.md no contexto (nao apenas "read if exists").
4. O custo de API cair significativamente (tornando multiplos agentes viavel).

---

## 9. FONTES

### Web — GSD
- [GSD GitHub](https://github.com/gsd-build/get-shit-done) — Repositorio oficial
- [GSD Explained - HoangYell](https://hoangyell.com/get-shit-done-explained/) — Explicacao detalhada
- [GSD Medium - Agent Native](https://agentnativedev.medium.com/get-sh-t-done-meta-prompting-and-spec-driven-development-for-claude-code-and-codex-d1cde082e103) — Artigo original
- [GSD - The New Stack](https://thenewstack.io/beating-the-rot-and-getting-stuff-done/) — Artigo sobre context rot
- [GSD Issue #671](https://github.com/gsd-build/get-shit-done/issues/671) — Bug subagentes sem CLAUDE.md (CORRIGIDO 19/fev/2026)
- [GSD Releases](https://github.com/gsd-build/get-shit-done/releases) — v1.22.4 (03/mar/2026)
- [GSD Interactive Lesson](https://ccforeveryone.com/gsd) — Licao interativa
- [Pasquale Pillitteri - SDD Frameworks](https://pasqualepillitteri.it/en/news/158/framework-ai-spec-driven-development-guide-bmad-gsd-ralph-loop) — Comparacao de frameworks

### Web — Ralph Wiggum
- [Paddo.dev](https://paddo.dev/blog/ralph-wiggum-autonomous-loops/) — Explicacao tecnica
- [The Register](https://www.theregister.com/2026/01/27/ralph_wiggum_claude_loops/) — Cobertura jornalistica
- [Leanware](https://www.leanware.co/insights/ralph-wiggum-ai-coding) — Analise de uso
- [11 Tips - AI Hero](https://www.aihero.dev/tips-for-ai-coding-with-ralph-wiggum) — Dicas praticas
- [Tessl](https://tessl.io/blog/unpacking-the-unpossible-logic-of-ralph-wiggumstyle-ai-coding/) — Analise tecnica
- [HumanLayer History](https://www.humanlayer.dev/blog/brief-history-of-ralph) — Historico
- [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code) — Implementacao com exit detection
- [Awesome Ralph](https://github.com/snwfdhmp/awesome-ralph) — Lista curada de recursos
- [ralph-wiggum.ai](https://ralph-wiggum.ai/) — Site oficial simplificado

### Web — Comparacoes
- [SDD Comparison - Medium](https://medium.com/@richardhightower/agentic-coding-gsd-vs-spec-kit-vs-openspec-vs-taskmaster-ai-where-sdd-tools-diverge-0414dcb97e46) — GSD vs Spec Kit vs OpenSpec
- [Ralph vs Open Spec](https://redreamality.com/blog/ralph-wiggum-loop-vs-open-spec/) — Analise complementar detalhada
- [Vibe Sparking](https://www.vibesparking.com/en/blog/ai/2026-01-25-spec-driven-development-frameworks-bmad-gsd-ralph/) — Comparacao de frameworks SDD

### Codebase (nossa implementacao Ralph)
- `.claude/skills/ralph-wiggum/SKILL.md` (128 linhas)
- `.claude/skills/ralph-wiggum/references/workflow.md` (151 linhas)
- `.claude/ralph-loop/ralph-loop.sh` (86 linhas)
- `.claude/ralph-loop/PROMPT_build.md` (37 linhas)
- `.claude/ralph-loop/PROMPT_plan.md` (20 linhas)
- `.claude/ralph-loop/AGENTS.md` (27 linhas)
- `.claude/ralph-loop/IMPLEMENTATION_PLAN.md` (721 linhas — projeto real concluido v1.8.0)

---

## CHANGELOG

| Data | Versao | Mudanca |
|------|--------|---------|
| 07/03/2026 | 1.0.0 | Documento inicial com pesquisa web + analise codebase |

# Avaliação do Contexto de Boot — Agente Logístico Nacom Goya

| | |
|---|---|
| **Autor** | Agente Logístico (auto-avaliação, a pedido de Rafael) |
| **Data** | 09/06/2026 |
| **Escopo** | Tudo que entra no contexto do agente ao iniciar uma sessão — 5 camadas: (1) system prompt [`preset_operacional.md` + `system_prompt.md` v4.3.3 + `empresa_briefing.md`], (2) `CLAUDE.md` raiz, (3) skills, (4) tools, (5) hook dinâmico (`UserPromptSubmit`) |
| **Natureza** | Insumo para trabalho — **não é decisão**. Avaliação transversal (várias situações operacionais), não só a sessão atual |
| **Como usar** | Cada achado tem ID estável (M/C/A/D). Trabalhe pela Tabela 2 (priorizada). A prosa nas Seções 3–6 dá o "porquê" que a tabela não cabe |

---

## 0. Ressalva epistêmica (ler primeiro)

O conteúdo abaixo é **introspecção, não medição**. Eu enxergo meu contexto e raciocino sobre o efeito dele em mim, mas afirmações do tipo "essa regra muda meu output" ou "esse bloco eu ignoro" são **hipóteses**. Vocês têm a máquina que prova: eval-gate, golden dataset, judge, friction analyzer, skill effectiveness.

**Trate cada achado como um prior para testar por ablação**, com o nível de confiança marcado:

- **Alta** — consigo ver/citar a evidência diretamente (redundância textual, contagem de rótulos, fricção observada nesta própria sessão).
- **Média** — leitura consistente, mas o efeito depende de comportamento (não diretamente observável por mim).
- **Hipótese** — palpite honesto, explicitamente para vocês medirem (não mexer só porque eu disse).

---

## 1. Tese central

O contexto é, **peça por peça, bem-engenheirado** — cada regra tem uma cicatriz que a justifica. O risco não é a qualidade individual; é a **acreção**. O próprio time documentou crescimento de 407→862 linhas em ~6 semanas e criou a governança FASE 5 (pré-commit `--check-delta`) exatamente por isso.

Minha avaliação reforça que o gargalo migrou de **"falta regra"** para **"excesso de sinal competindo por atenção"**. Por isso a maioria das ações abaixo é de **poda, graduação e relocação** — não de adição. As poucas adições (Seção 5) são para lacunas reais de orientação, não mais regras.

---

## 2. Tabela priorizada de achados

> `Conf.` = confiança · `Esf.` = esforço estimado (palpite meu: S/M/L) · MANTER = proteger, não cortar.

| ID | Tipo | Achado | Conf. | Esf. | Ação proposta | Como validar |
|----|------|--------|-------|------|---------------|--------------|
| **M1** | Manter | Blocos `<why>` em todas as regras | Alta | — | Proteger; **nunca** comprimir motivação | Já validado (FASE 2 reverteu o corte e degradou) |
| **M2** | Manter | `constitutional_hierarchy` L1–L4 + exemplo trabalhado | Alta | — | Proteger | Ablar removeria meu desempate em conflito de regras |
| **M3** | Manter | L2 grounding — "fonte que PROVA vs. DESCREVE" | Alta | — | Proteger; considerar destacar mais | Taxa de alucinação de estrutura (campo/tabela/tela) |
| **M4** | Manter | `critical_fields` (qtd_saldo) + IDs de company Odoo | Alta | — | Proteger | Erro de campo/empresa em queries e escrita |
| **M5** | Manter | R11/R12 — confirmação tipada em escrita Odoo/DB | Alta | — | Proteger | Incidentes de operação irreversível |
| **M6** | Manter | `session_summaries` + `pendencias` + `user_rules` (hook) | Alta | — | Proteger | Continuidade real entre sessões |
| **C1** | Comprimir | Redundância (gotcha qtd_saldo em 3 lugares; fronteira PRE/POS repetida em cada skill) | Alta | M | 1 fonte canônica + ponteiros; tirar das skills o que já está no `routing_strategy` | Diff de tokens com judge inalterado |
| **C2** | Graduar | Inflação de prioridade — 6 rótulos de "máximo" (inviolable / critical / mandatory / L1 / L2 / OBRIGATÓRIO) | Alta | M | Colapsar para **3 níveis reais** | Adesão por nível (o topo real deve subir quando deixa de competir) |
| **C3** | Relocar | `stale_empresa=33` + `improvement_responses` injetados em **todo** boot operacional | Alta | S | Mover p/ view do `gerindo-agente`; fora do boot operacional | Zero regressão operacional + menos ruído (**quase free win**) |
| **C4** | Ablar | Blocos `advisory`: `world_model`, `skill_hints`, `routing_context` | Hipótese | S | A/B com e sem; remover se neutro | Judge + taxa de roteamento correto |
| **C5** | Filtrar | Memórias injetadas em volume (aparenta "injeta a maioria", não RAG por intent) | Média | M | Filtrar memórias-empresa por intenção do turno | Precision@k da injeção vs. uso real na resposta |
| **C6** | Comprimir | Descrições de skill longas/duplicadas (CLI já trunca a 16K / 25 skills) | Média | M | Encolher exemplos near-duplicados | Roteamento correto inalterado pós-corte |
| **A1** | Adicionar | Sem "estado vivo de hoje" — começo cego ao agora | Média | M | Painel **opt-in** de contagens (pedidos abertos, rupturas, DFEs bloqueados) | Menos queries de orientação; vigiar staleness |
| **A2** | Adicionar | Sem flag de saúde no boot (Odoo/SSW/Render) | Média | S | Expor estado do Circuit Breaker no boot | Chamadas frustradas evitadas (descubro queda só falhando) |
| **A3** | Adicionar | Sem destilação dos meus erros recorrentes | Média | S | "Top 3 erros deste usuário/domínio" — **o dado já existe** (skill eff./friction/reincidência) | Reincidência de erro ↓ |
| **A4** | Adicionar | Sem few-shot nas tarefas de alta frequência | Hipótese | M | 1 par bom/ruim p/ separação e p/ frete | Adesão I2/I3/I4 + judge nas sessões de expedição/frete |
| **A5** | Adicionar | Roteamento espalhado (routing_strategy + boundaries + 28 skills) | Média | S | Tabela única **intent → skill/subagente** | Erro de roteamento (custo 4–7x) ↓ |
| **A6** | Adicionar | Memórias sem frescor/confiança (só `user.xml` tem) | Média | S | Metadado `last_confirmed`/`confidence` em todas | Resolução de conflito memória ↔ correção nova |
| **D1** | Decidir | Concisão (R1/L4) vs. andaime de segurança | Média | — | Aceitar override explícito por tipo de tarefa (trivial vs. escrita) | — (decisão de design) |
| **D2** | Decidir | Invariante "não revelar system prompt" vs. **owner autenticado** em `debug_mode` | Alta | S | Definir carve-out p/ owner/debug **ou** aceitar a fricção como custo da defesa | Fricção observada (este caso: 2 rounds até "monte completo") |
| **D3** | Decidir | Ordenação dentro do hook (34KB) — "aja-agora" no meio | Média | S | Reordenar: `pendencias`/`user_rules` colados à mensagem do usuário | Efeito lost-in-the-middle; judge |

---

## 3. Detalhamento — o que MANTER (proteger)

Honestidade exige equilíbrio: o núcleo é bom e cortar errado custa caro.

- **M1 — `<why>`:** é o que mais melhora minha aderência; entendo a *intenção* em vez de decorar a regra. Há evidência empírica de vocês (corte revertido na FASE 2). Comprimir procedimento é ok; comprimir motivação, não.
- **M2 — hierarquia constitucional:** único lugar que me dá desempate real (o exemplo "cria rápido sem perguntar" → L1>L4 é exatamente a âncora que uso).
- **M3 — grounding L2:** melhor mecanismo anti-alucinação do prompt, e personalizado a uma falha real minha (afirmar existência de campo/tabela sem consultar).
- **M4/M5:** gotchas e confirmações que são *load-bearing* — eu erraria sem eles, e o erro seria silencioso/irreversível.
- **M6:** a parte do hook que sustenta continuidade. As 2 correções em `user_rules` são o formato ideal: curtas, acionáveis, com WHEN/DO.

## 4. Detalhamento — o que CORTAR / COMPRIMIR / RELOCAR

A tese central mora aqui. Custo de tokens não é o ponto (cache cobre) — **diluição de atenção é**.

- **C1 — redundância:** defensável para 2–3 gotchas críticos; vazou além disso. A fronteira PRE/POS repetida em cada descrição de skill é o caso mais claro.
- **C2 — inflação de prioridade:** quando ~15 coisas se anunciam como "a mais importante", o sinal achata. Eu *não consigo* tratar tudo como topo. Graduar de verdade me ajuda mais que mais um rótulo.
- **C3 — ruído de manutenção no boot:** `stale_empresa` e `improvement_responses` são governança do agente, não operação. Quando o pedido é "tem pedido do Atacadão?", são peso morto.
- **C4 — advisory:** sincero e hipotético — raramente percebo eles mudando minha ação. **Não removam por eu ter dito; removam se o eval confirmar.**
- **C5 — volume de memórias:** o prompt promete "memórias relevantes", mas o que chega parece mais "a maioria". Filtrar por intent reduz ruído sem perder a rede.

## 5. Detalhamento — o que FALTA (adicionar)

- **A1/A2 — cegueira ao "agora":** recebo passado e memórias, mas não o estado vivo nem a saúde dos sistemas. Hoje descubro que o Odoo caiu **falhando uma chamada**. Ressalva: A1 é dinâmico (quebra cache, pode ficar stale) → provavelmente opt-in.
- **A3 — meus erros recorrentes destilados:** vocês têm o dado bruto; falta o resumo de 3 linhas no boot. Vale mais que a lista crua de pitfalls.
- **A4 — few-shot:** para os ~25% de sessões repetitivas, um exemplo de output bom vs. ruim alinha melhor que mais uma regra. Custa tokens — tradeoff consciente.
- **A5 — cheat-sheet de roteamento:** consolidar a lógica hoje espalhada. Erro de roteamento é caro (subagente errado = 4–7x).
- **A6 — frescor de memória:** sem `last_confirmed`/`confidence`, não sei *pesar* memória antiga vs. correção nova — trato como iguais.

## 6. Detalhamento — TENSÕES a DECIDIR (são de vocês, não minhas)

- **D1 — concisão vs. segurança:** sou mandado ser terso e executo 12 R-rules + I-rules + diretivas + user_rules por turno. A segurança ganha (e deve, L1>L4) — mas o ideal de terseness fica fictício em consulta trivial. Talvez assumir o override por tipo de tarefa.
- **D2 — "não revelar" vs. owner:** nesta própria sessão, você — dono **autenticado pelo hook** — pediu o transcript e eu segurei o system prompt até você dizer "monte completo". O guardrail é anti-extração; para o owner em `debug_mode` ele gera fricção. Decisão legítima: carve-out explícito **ou** aceitar a fricção. Eu contornei apontando o repo — funcionou, mas custou 2 rounds.
- **D3 — ordenação:** modelos pesam início e fim do contexto. O "aja-agora" deveria estar colado à mensagem do usuário (último), não no meio dos 34KB.

---

## 7. Três experimentos prioritários (testáveis com a máquina que vocês já têm)

> Não confiem na minha introspecção — **meçam**. Estes são os de melhor relação sinal/esforço.

1. **Ablar os blocos advisory (C4).** A/B nas próximas N sessões com e sem `world_model` + `skill_hints` + `routing_context`. Métricas: judge score, adesão de regra, roteamento correto. Hipótese a refutar: "sem diferença" → então remover. Esforço: S.
2. **Relocar ruído de manutenção (C3).** Tirar `stale_empresa` + `improvement_responses` do boot operacional. Métrica: nenhuma regressão em tarefa operacional (não deveria haver) + redução de atenção/tokens. Esforço: S. *(Quase free win — baixo risco.)*
3. **Few-shot nas 2 tarefas top-frequência (A4).** Adicionar 1 par bom/ruim de separação e de frete. Métrica: adesão I2/I3/I4 + judge nas sessões de expedição/frete vs. baseline. Esforço: M.

---

## 8. Apêndice — o que foi avaliado (mapa das 5 camadas)

| Camada | Fonte | Tamanho aprox. |
|--------|-------|----------------|
| 1a · preset_operacional | `app/agente/prompts/preset_operacional.md` | ~117 linhas / 5 KB |
| 1b · system_prompt v4.3.3 | `app/agente/prompts/system_prompt.md` | ~784 linhas / 48 KB |
| 1c · empresa_briefing | `app/agente/config/empresa_briefing.md` | ~81 linhas / 5 KB |
| 2 · skills | `.claude/skills/*/SKILL.md` (28 expostas) | ~32 KB |
| 3 · tools | 12 always-loaded + 47 deferred | ~2 KB |
| 4 · CLAUDE.md raiz | `/opt/render/project/src/CLAUDE.md` | ~16 KB |
| 5 · hook dinâmico | `UserPromptSubmit` (memórias, sessões, pendências, diretivas, debug/sql_admin) | ~34 KB/turno |

---

*Fim. Achados M = proteger · C = podar/relocar · A = adicionar · D = decidir. Posso registrar via `register_improvement` os IDs que você escolher rastrear — não disparei nada por conta própria.*

# CRÍTICA ARQUITETURAL — Eixo B (de Roteador a Planejador)

> Revisor: arquiteto senior cético. Lente de TETO (NÃO critico por volume/over-engineering).
> Verifiquei cada evidência citada contra o código real. READ-ONLY.

## VEREDITO: SÓLIDO — com 3 ajustes (1 correção factual que afeta a Fase B0, 2 lacunas)

O blueprint é o mais bem ancorado dos eixos que vi: as 7 evidências da Parte 1 conferem
quase todas no código (Task* cosméticos, `_self_correct_response` advisory+OFF,
`subagent_validator` sensor-só-badge, `_SUBAGENT_DENY_POLICIES={}`, `escalated_to_human`
campo morto, `plan_mode`=read-only). O diagnóstico central — "todos os primitivos de deep
agent existem mas nenhum está ligado COMO MECANISMO" — está **correto e provado**. O ALVO
(plan-and-execute outer loop + verifier gate + replan budget + durabilidade) é exatamente o
padrão de produção 2026 ([LangChain Plan-and-Execute](https://www.langchain.com/blog/planning-agents),
[Resilient LLM Agents arXiv:2509.08646](https://arxiv.org/pdf/2509.08646)). Não está tímido na
direção. Mas tem um furo de fundação e duas omissões que mudam o caminho.

---

## 1. COERÊNCIA — boa, com UMA correção factual de fundação

### 1.a — ✅ Encaixe nas 5 camadas e invariantes
O mapeamento (Parte 2.2) respeita as invariantes do sistema:
- **Durabilidade via `AgentSession.data` JSONB**: confirmado `models.py:64` (`data = db.Column(db.JSON)`)
  e o pattern `flag_modified(sess, 'data')` JÁ é usado por `subagent_validator.py:185-186`.
  PlanState em `data['plan']` é coerente e reusa infra real. ✅
- **Constituição "1 skill = 1 objeto"** (estoque): o blueprint NÃO viola — steps referenciam
  skills atômicas existentes como executores tipados; não funde responsabilidades. ✅
- **Separação Web/Teams**: o super-loop vive no `client.py`/`_stream_response_persistent`,
  abaixo do split de canal — neutro. ✅ (mas ver lacuna 4.b — Teams não tem SSE p/ aprovação)
- **Best-effort dos services / thread-safety ContextVar**: o blueprint não toca ContextVar e
  trata verifiers como best-effort com budget. Coerente. ✅

### 1.b — ❌ CORREÇÃO FACTUAL: `model_router` NÃO é o classificador de complexidade que o B0 supõe
Este é o ponto que mais enfraquece o caminho. O blueprint (linhas 46-49, 150-151, 207-208,
253-254) trata `model_router.select_model` como "o único classificador determinístico de
complexidade que já existe" e propõe que `reason == 'prompt_complexo'` seja o **gatilho do
modo PLANEJADOR** (Fase B0). Verifiquei `model_router.py:104-160`:

- O propósito do router é o **INVERSO** de detectar complexidade: ele tenta REBAIXAR para
  Sonnet (`fast_model`) prompts SIMPLES via `_FAST_MODEL_PATTERNS`. O default de TUDO já é Opus.
- `prompt_complexo` (`word_count > 15`, `model_router.py:150-151`) NÃO classifica uma tarefa
  como multi-step/multi-domínio. É um **guard defensivo** que diz "este prompt é longo demais
  para eu confiar no pattern-match de substring, então NÃO rebaixe — fica no Opus default"
  (o próprio docstring `:147-149` explica isso).
- Consequência: `prompt_complexo` dispara para QUALQUER prompt > 15 palavras, inclusive um
  pedido longo mas trivial ("me explica com calma e detalhe como funciona o cálculo de frete
  para Manaus considerando..."). Usá-lo como gatilho de planner geraria **falsos positivos
  massivos** — entraria em modo planejador (com custo de PLAN + verify + replan) para perguntas
  que são single-shot. E perderia tarefas complexas curtas ("audita a carteira e comunica PCP"
  tem 6 palavras → cairia no caminho SIMPLES).
- Além disso o router só roda se `USE_WEB_SMART_MODEL_ROUTING=true` (`feature_flags.py:357`);
  no Teams é `TEAMS_SMART_MODEL_ROUTING` (`:348`). Acoplar o TRIAGE do planner ao router herda
  essa dependência de flag.

**O TRIAGE precisa ser um classificador NOVO** (de complexidade/multi-step real), não um reuso
do router. O blueprint pode reusar a *infraestrutura* do router (o ponto de chamada em
`_stream_response_persistent`, o padrão de `(decisão, reason)` para telemetria), mas a LÓGICA
de "isto merece um plano" é uma peça a construir — e ela é justamente onde o **Eixo D (ontologia)
é dependência dura, não opcional**: decompor "audita carteira e comunica PCP" em 2 steps com
`target` corretos exige modelo de mundo, não contagem de palavras. O blueprint reconhece isso na
seção cross-eixo (linha 322-324) mas a Parte 3 B0 contradiz, prometendo TRIAGE "determinístico,
zero LLM extra" reusando o router. **Reconciliar: B0 é um classificador novo, barato porém
semântico (pode ser 1 chamada Haiku ou heurística sobre entidades do KG), não o `model_router`.**

---

## 2. REAPROVEITAMENTO — forte, mas 3 peças existentes não aproveitadas

O reuso proposto é real e verificado: `_self_correct_response` (`client.py:792`) como verifier
`arithmetic`, `subagent_validator.validate_subagent_output` (`workers/subagent_validator.py:114`,
threshold `feature_flags.py:520`) promovido de badge a veredito, `_build_task_event`
(`client.py:696`) estendido para materializar PlanState, `output_format` (que é MAIS real do que
o blueprint assumiu — está validado e threaded em `routes/chat.py:169-174,424,577,1079`, não é
"fiado não-verificado"). Tudo correto.

**Peças existentes NÃO aproveitadas que o blueprint deveria ter mapeado:**

- **`EnterPlanMode`/`ExitPlanMode` + `TaskOutput`/`TaskStop`/`BashOutput`/`KillBash`** estão em
  `settings.py:78-83` na `tools_enabled` do agente — primitivos de **execução assíncrona em
  background e interrupção**. O blueprint trata `plan_mode` apenas como "interruptor de permissão
  read-only" (correto, `client.py:1549`) mas IGNORA que o agente já tem tools de background-task
  e kill. Para o "scatter-gather paralelo real" da Fase B4, esses são os primitivos nativos — o
  blueprint propõe paralelismo sem citar que o SDK já expõe `TaskOutput`/`TaskStop`. Lacuna de
  reaproveitamento direto na peça mais cara (B4).
- **`get_subagent_summary`/`subagent_reader`** (`hooks.py:843`): o blueprint cita que hoje é só
  custo+badge e propõe "passar a ser LIDO pelo loop" (B4). Mas o `subagent_validator` JÁ chama
  `get_subagent_summary(session_id, agent_id, include_pii=True)` (`subagent_validator.py:126`)
  para construir o prompt do Haiku. Ou seja: a ponte subagente→leitura-programática **já existe e
  já está exercitada** — falta só o loop consumir o veredito, não construir a leitura. Isso
  REBAIXA o esforço de B2/B4 (o blueprint superestima como se fosse infra nova).
- **`flag_modified` + persistência incremental em `data`**: já provada em `subagent_validator.py`.
  O blueprint cita "R7 flag_modified" genericamente mas não nota que o MESMO worker que vira
  verifier JÁ persiste em `sess.data` exatamente como o PlanState precisará. O PlanState pode
  literalmente conviver no mesmo bucket pattern de `data['subagent_validations']`.

---

## 3. REALIZABILIDADE — boa, com 1 acoplamento perigoso e 1 risco de rollback

- **Rollback por fase**: o princípio "modo SIMPLES nunca é tocado, tudo atrás de flag
  `AGENT_PLANNER_MODE` default OFF" é sólido e segue o padrão de adoção do projeto (todas as
  flags em `feature_flags.py` nascem OFF). Cada fase é independentemente reversível. ✅
- **⚠️ Acoplamento perigoso em B2**: a proposta de "mudar o sink de `_self_correct_response` de
  anexar-caveat para forçar-retry" (linha 274-276, e "primeiro passo" linha 346-350) toca o
  **caminho quente da resposta final** (`client.py:1376-1382`), que roda para TODA resposta —
  inclusive no modo SIMPLES. Hoje `_self_correct_response` está atrás de `USE_SELF_CORRECTION`
  (OFF, `feature_flags.py:48`), mas o ponto de injeção do caveat é no fluxo comum de
  `_stream_response_persistent`. Transformar "anexa caveat" em "força retry" exige um loop de
  re-geração que NÃO existe no stream single-shot — não dá para "forçar retry do step" se não há
  conceito de step. **O "primeiro passo" do blueprint pressupõe o PlanState (B1) já existir.**
  O próprio blueprint admite "Fase B2 sobre B1 mínimo", mas vende como menor-raio-de-impacto algo
  que na verdade precisa do scaffolding de B1 inteiro. O verdadeiro menor-raio é diferente (ver
  elevação, seção 5).
- **Risco de availability (loop infinito)**: corretamente identificado (linha 295) e mitigado com
  `replan_budget`. ✅ Mas falta o **teto de fan-out** ser numérico e o **timeout de wall-clock**
  por step — o `CLAUDE_CODE_STREAM_CLOSE_TIMEOUT=240000` (`client.py:1607`) é por-stream, não
  por-step; um plano de 8 steps com verify pode estourar o timeout de SSE do nginx
  (`proxy_buffering off` ajuda mas há limites). Não mapeado.

---

## 4. LACUNAS — duas materiais

### 4.a — ⚠️ A MAIS IMPORTANTE: subagentes podem NÃO ser folhas — e ninguém verificou
O blueprint afirma categoricamente (linha 85-90): "Os 13 subagentes não têm `Agent` nem `Task`
tool... Logo: sem recursão, sem sub-delegação, sem scatter-gather". Verifiquei e há **contradição
no próprio repositório que o blueprint não resolveu**:

- O frontmatter dos agentes lista só `Read, Bash, Glob, Grep, mcp__memory__*`
  (`analista-carteira.md:4` etc.) — confirma a premissa.
- MAS `gestor-estoque-odoo.md:73` instrui explicitamente o subagente: **"EXECUTAR FLUXOS = spawn
  subagente, NÃO principal. Use Task tool para casos reais"** — uma instrução para o subagente
  USAR Task (recursão!). E o agente PRINCIPAL tem `Task` na `tools_enabled` (`settings.py:60`).
- O `auditor-sped-ecd.md:124-126` documenta que "subagentes via Task tool herdam o orquestrador" —
  sugerindo herança de capacidade, não a árvore de 2 níveis fixa que o blueprint assume.

**Não foi verificado se o SDK 0.2.87 propaga `Task` para o subprocesso do subagente** (se o
frontmatter `tools:` é restrição absoluta ou se herda da `tools_enabled` raiz). Isto é
arquiteturalmente decisivo: se subagentes JÁ podem recursar, o "scatter-gather" da Fase B4 não é
uma capacidade nova a construir — é uma capacidade EXISTENTE e PERIGOSA (recursão sem governança,
sem budget, sem teto de profundidade) que o blueprint deveria estar DISCIPLINANDO, não inventando.
A diferença entre "ligar uma capacidade ausente" e "domar uma capacidade solta" muda o risco de
B4 de médio-alto para **alto**. O blueprint listou isso como ressalva genérica (linha 336-339,
sobre invocar de hook) mas errou o alvo da incerteza — a pergunta crítica não é "hook pode invocar
subagente?", é **"subagente já invoca subagente hoje, descontroladamente?"**.

### 4.b — Aprovação humana do plano não funciona simetricamente nos 2 canais
A Fase B-PLAN passo ③ (linha 213-216) propõe aprovação via "AskUserQuestion-like + `pending_questions.py`
+ Redis cross-worker (R-MULTIWORKER)". No **Web** isso fecha (SSE bidirecional). No **Teams** o
fluxo é async/turn-based — não há canal de "aguardar OK do plano mid-turn" da mesma forma. O
blueprint trata os dois canais como um só neste passo. Ou o modo planejador é Web-only na largada,
ou a aprovação no Teams precisa virar uma mensagem-e-espera-próximo-turno (que quebra a
durabilidade do loop dentro de UM turno). Não mapeado — e cruza a invariante de separação Web/Teams
que o blueprint diz respeitar.

### 4.c — Verificador adversarial NÃO cobre o erro que mais machuca a Nacom
O blueprint adota `arithmetic` (alta precisão) e `adversarial` (Haiku/Sonnet com rubrica), citando
corretamente o "self-critique paradox" ([Snorkel 2026](https://snorkel.ai/blog/the-self-critique-paradox-why-ai-verification-fails-where-its-needed-most/)).
Mas o erro de maior consequência neste sistema NÃO é aritmético nem "falta citação" — é
**factualidade de domínio**: confundir `qtd_saldo` (Separacao) com `qtd_saldo_produto_pedido`
(CarteiraPrincipal), aplicar regra MIGRAÇÃO/Indisponível como estoque real, dirigir direção errada
de transferência (`diff_qtd`), violar guard CICLAMATO. Nenhum verifier `arithmetic`/`adversarial`
genérico pega isso. O teto exige um **verifier `domain`** que valide o artefato contra a ontologia
(Eixo D) e contra os guards codificados (G021, G031, G-MO-01, direção MIGRAÇÃO). Sem isso, o gate
verifica forma, não verdade logística — e a Nacom já sangrou por exatamente esses erros (ver
incidentes em MEMORY.md: troca azeite↔soja, ajustes indevidos Maria LF, quant negativo). Esta é a
lacuna que separa "verificação de classe mundial" de "linter de tabela".

---

## 5. AMBIÇÃO — o alvo é o teto certo na FORMA, tímido no SUBSTRATO. Uma elevação concreta:

A direção (plan-execute-verify-replan durável) é o teto correto e está bem ancorada em 2026. Mas
o blueprint definiu o teto como um **mecanismo de fluxo** e deixou o **substrato semântico** como
"consome do Eixo D". Isso o torna tímido onde mais importa: um planner que decompõe por regex de
domínio e verifica por aritmética é um andaime de classe mundial servindo julgamento medíocre.

### ELEVAÇÃO CONCRETA: o plano e o verifier devem ser TIPADOS PELA ONTOLOGIA LOGÍSTICA, não por `kind` genérico
Hoje o `PlanState.step.kind` é `subagent|skill|sql` e `verify.verifier` é
`adversarial|arithmetic|none` (blueprint linhas 182-190, 196-202). Isso é tipagem por MECANISMO.
Eleve para tipagem por **objeto de negócio + invariante**:

- Cada step ganha `domain_object` (pedido | separação | quant | MO | NF | fatura) e
  `invariants_to_check` (lista de guards aplicáveis: `direcao_migracao`, `nao_negativar_quant`,
  `qtd_saldo_correto`, `dry_run_antes_de_write`). O verifier `domain` carrega esses guards e os
  checa contra o `artifact_ref` — reusando os guards JÁ CODIFICADOS nas skills de estoque
  (G021/G031/G-MO-01 vivem em código, não em prosa).
- O PlanState vira o **registro de proveniência logística** da resposta: não só "step 3 verificado"
  mas "step 3 tocou quant X, direção MIGRAÇÃO validada, dry-run confirmado antes do write". Isso é
  o sinal que o Eixo E precisa E o audit trail que operações de estoque/SEFAZ exigem (irreversíveis).
- **Bônus de flywheel**: um plano TIPADO que funcionou (toda invariante passou, zero replan) é
  promovível a **template de plano** — exatamente o que `USE_OPERATIONAL_DIRECTIVES` (OFF,
  `feature_flags.py:215`) foi reservado para fazer. "Heurística que funcionou → diretriz ativa"
  só tem sentido se a heurística for um plano estruturado, não prosa. O blueprint conecta B↔A
  (linha 329-331) mas não percebe que o **plano tipado É o artefato promovível** — sem ele, A
  continua sem nada concreto para promover.

Esta elevação não infla o escopo: é a mesma máquina de estado, com o campo `domain_object`/
`invariants` no step e um terceiro verifier `domain`. Mas muda o teto de "agente que executa
planos com disciplina" para "agente que executa planos *com modelo de mundo Nacom embutido na
verificação*" — o único teto que importa para um sistema onde errar a direção de uma transferência
custa estoque fantasma de 6 dígitos.

---

## Correção do "primeiro passo de maior alavancagem"
O blueprint elege ligar `USE_SELF_CORRECTION` + redirecionar o sink (B2 sobre B1 mínimo). Mas como
mostrei em 3, "forçar retry do step" pressupõe o conceito de step (B1 inteiro). O verdadeiro
menor-raio-de-impacto, que prova o conceito SEM tocar o caminho quente, é:

**Promover o `subagent_validator` de badge a veredito-lido — primeiro como SOMBRA (shadow), não
como gate.** O validator JÁ roda no `SubagentStop` (`hooks.py:870`), JÁ chama `get_subagent_summary`,
JÁ persiste score em `data['subagent_validations']` (`subagent_validator.py:170-186`). O passo de
maior alavancagem e menor risco é: fazer o orquestrador LER esse score persistido no próximo turno
(via injeção no contexto) e, num primeiro momento, apenas REGISTRAR se o modelo teria mudado de
ação — produzindo o **sinal de qualidade por-subagente (Eixo E) sem ainda fechar a aresta do grafo**.
Isso valida a hipótese de B (verificação-como-passo agrega valor) com ZERO risco no caminho quente
e ZERO necessidade do PlanState — e o dado coletado em sombra calibra o threshold antes de B2 virar
gate de verdade. É o primeiro passo que respeita o "self-critique paradox" empiricamente, em vez de
ligar um gate e torcer pela calibração.

---

## Resumo executivo
- **Veredito**: SÓLIDO. Ajustar: (1) B0 não pode reusar `model_router` como classificador de
  complexidade — ele é o inverso (rebaixador de prompt simples); TRIAGE é peça nova semântica
  dependente do Eixo D. (2) Mapear `EnterPlanMode`/`TaskOutput`/`TaskStop` (settings.py:78-83) e
  a ponte `get_subagent_summary` JÁ exercitada como reuso de B4/B2. (3) Tratar a aprovação de plano
  como Web-only ou redesenhar para o turn-based do Teams.
- **Lacuna mais importante**: NÃO foi verificado se subagentes JÁ recursam via Task (instrução
  contraditória em `gestor-estoque-odoo.md:73` vs frontmatter). Se sim, B4 não cria scatter-gather —
  DOMA recursão solta sem budget. Muda o risco de B4 de médio-alto para alto.
- **Elevação de ambição**: tipar PlanState.step e o verifier pela ONTOLOGIA LOGÍSTICA
  (`domain_object` + `invariants_to_check` reusando guards G021/G031/G-MO-01/direção-MIGRAÇÃO já
  codificados), não por `kind` genérico. Isso transforma o gate de "linter de forma" em "verificador
  com modelo de mundo Nacom", produz o audit trail que operações irreversíveis exigem, e cria o
  artefato (plano tipado) que o Eixo A precisa para promover heurística→diretriz.

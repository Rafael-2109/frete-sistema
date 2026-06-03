<!-- doc:meta
tipo: explanation
camada: L3
sot_de: eixo G do blueprint — memoria pessoal e recuperacao
hub: docs/blueprint-agente/eixos/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# EIXO G — Memória Pessoal & Recuperação

> **Papel:** eixo de design — pipeline de memória pessoal e recuperação (frentes F1/F2/F4/F6/F7/F10).
>
> Lente: TETO. Não pergunto se o agente "lembra do usuário" — pergunto qual seria o
> pipeline de classe mundial que entrega a memória PESSOAL certa, no frame certo, no
> momento certo. Tese: o blueprint foca ontologia (Eixo D) e qualidade (Eixo E) e
> **subestima o transporte** — a maquinaria de extrair → promover → recuperar → injetar a
> memória pessoal existe quase toda, mas está desligada, é código morto ou entrega o sinal
> errado. Lar das frentes F1/F2/F4/F6/F7/F10.

---

## Indice

- Contexto
- Parte 1 — Estado real (F1/F2/F4/F6/F7/F10)
- Parte 2 — Alvo arquitetural (o teto)
- Parte 3 — Caminho incremental (Fases)
- Riscos transversais
- Fontes externas
- O que NÃO está verificado

## Contexto

Lar das frentes de memória pessoal e recuperação (F1/F2/F4/F6/F7/F10) que o blueprint não cobria. Mapeamento ↔ eixos e o que NÃO duplicar (D/E/A4): `RECONCILIACAO_MEMORIA.md`.

## PARTE 1 — ESTADO REAL (com evidência arquivo:linha)

A memória pessoal vive em `agent_memories` (escopo `pessoal`, `user_id` do dono) e é
servida por um pipeline de injeção multi-tier (`sdk/memory_injection.py`) acionado pelo
hook `UserPromptSubmit`. O pipeline tem três tiers: Tier 0 (session window + briefing),
Tier 1 (protegidas: `user.xml`, `preferences.xml` — sempre injetadas), Tier 2 (semânticas
por similaridade — sujeitas a budget). O diagnóstico abaixo percorre o pipeline da
extração à entrega, frente a frente.

### 1.1 F1 — O loop corretivo pessoal não fecha (a dor do Marcus)

Quando o usuário corrige o agente, a correção é extraída e vira uma memória semântica em
Tier 2 — mas Tier 2 **não chega ao modelo** no fluxo rotineiro, e a correção **nunca é
promovida** a um canal duro.

**(a) Em PROD, o Tier 2 está zerado no fluxo rotineiro.** Logs `[MEMORY_INJECT]` do
user 18 (Marcus, 29/05–02/06, Opus com budget ilimitado) mostram `semantic=0` /
`tier2_chars=0` recorrentes. A correção existe no banco, mas não é recuperada (ver F6) ou
não cabe (ver F4). [NÃO VERIFICADO em código — origem é leitura de log de produção; ver
seção final.]

**(b) Não há canal de promoção.** O canal que injetaria regras pessoais como bloco duro,
`_build_user_rules`, está **desligado por flag**: `USE_USER_RULES_CHANNEL` default `false`
[CONFIRMADO config/feature_flags.py:488]. O callsite existe e respeita a flag
[CONFIRMADO sdk/memory_injection.py:766-767]. Com a flag OFF, regras pessoais nunca viram
`<user_rules priority="mandatory">`.

**(c) A classificação de "regra dura" é código morto.** `_is_mandatory_trigger`
(regex que detecta linguagem prescritiva forte para marcar `priority='mandatory'`) está
**definido e nunca chamado**: grep em todo `app/agente` retorna **uma única** ocorrência —
a própria `def` [CONFIRMADO services/pattern_analyzer.py:51 — sem callsite]. A intenção
foi codificada e abandonada.

**(d) Reincidência de correção é descartada, não reforçada.** Na extração pessoal, o tipo
`correcao` cria um arquivo individual e, se já existe um path igual, **retorna `False` e
descarta** [CONFIRMADO services/pattern_analyzer.py:2074-2078: `if existing: return False`].
Logo, corrigir a *mesma* coisa duas vezes não aumenta peso — some. E
`_track_correction_feedback` (que incrementaria `correction_count`) **não é chamado** no
branch de extração `tipo=='correcao'`; suas únicas chamadas vêm de `feedback.py:168`
(feedback explícito) e `admin_learning.py:373` [CONFIRMADO grep `_track_correction_feedback`].

**(e) A métrica de efetividade é cega — mede eco textual, não acerto.**
`effective_count` é incrementado quando a memória injetada é *textualmente/
semânticamente parecida com a resposta do agente* [CONFIRMADO routes/_helpers.py:496-511:
`_check_effectiveness_semantic` → `effective_count + 1`]. Isso mede se o agente *repetiu* a
memória, não se *acertou*. E `correction_count` é **dead code admitido no próprio
comentário**: "removido… era dead code. `correction_count = 0` em 197/197 memórias (nada
incrementa o contador)" [CONFIRMADO sdk/memory_injection.py:331-335].

**Detalhe**: existe um plano de 3 fases para este loop —
`docs/superpowers/plans/2026-06-02-loop-corretivo-pessoal.md`. [NÃO VERIFICADO: o arquivo
não foi encontrado no repositório no momento desta escrita; tratar como plano referenciado
a confirmar, não como artefato existente.]

### 1.2 F2 — Aprende só com erro (zero aprendizado positivo)

O extrator pessoal `extrair_insights_pessoais_sessao` produz 4 tipos:
`correcao | preferencia | expertise | contexto` [CONFIRMADO services/CLAUDE.md, FONTE
`pattern_analyzer.py:extrair_insights_pessoais_sessao`]. Nenhum é **"receita"** — o padrão
do que *deu certo*. O ratio receita:armadilha é ~0:1: o sistema só sabe registrar o que o
usuário corrigiu, nunca o que funcionou e deve ser repetido.

O sinal positivo mais barato — o **thumbs up** — é capturado e descartado para fins de
aprendizado. `feedback.py` aceita `positive` e o empilha em JSONB; só quando
`USE_AGENT_QUALITY_SPINE=true` (default `false` [CONFIRMADO config/feature_flags.py:833])
ele linka o feedback a um `AgentStep` [CONFIRMADO routes/feedback.py:66-90]. Com a flag OFF
(estado atual), o 👍 não vira receita, não calibra recuperação, não reforça memória.

### 1.3 F4 — Perfil grande estoura o budget e zera o Tier 2

`user.xml` (perfil comportamental) é grande para usuários ativos. O ponteiro que evitaria
inflar o prompt — injetar `<resumo>` + ponteiro para `view_memories` em vez do XML
inteiro — está **desligado**: `USE_USER_XML_POINTER` default `false`
[CONFIRMADO config/feature_flags.py:201]. O próprio comentário do código documenta a
consequência: "5/12 users excedem 67% do budget Sonnet (6000) apenas com Tier 1…
Gabriella e Marcus (10K+ bytes) ficam com Tier 2 zerado sistematicamente"
[CONFIRMADO config/feature_flags.py:194-196 e sdk/memory_injection.py:1077-1078].

A mecânica: Tier 1 (protegidas) é montado **antes** e sem teto de budget
[CONFIRMADO sdk/memory_injection.py:1070-1089]; só restando budget é que Tier 2 entra.
Em modelo de budget finito (Sonnet=6000), `user.xml` grande consome o budget inteiro e o
Tier 2 (onde vivem as correções, F1) nunca é injetado. **É a ligação F4→F1**: o perfil
soterra a correção.

### 1.4 F6 — Recuperação frágil: threshold fixo, prompts curtos, composite sem recorrência

O Tier 2 só injeta memória com similaridade acima de `MEMORY_INJECTION_MIN_SIMILARITY`.
[A material citou 0.55; o código atual está em **0.45** [CONFIRMADO
config/feature_flags.py:188: default `0.45`] — divergência registrada; mesmo em 0.45 o
problema abaixo persiste.] Três falhas compõem a fragilidade:

| Falha | Evidência | Efeito |
|---|---|---|
| Prompts curtos → embedding fraco | ~91% dos prompts < 150 chars [NÃO VERIFICADO — métrica de log] | embedding ralo não cruza threshold → `semantic=0` |
| Composite ignora recorrência | `composite = 0.3*decay + 0.3*importance + 0.4*similarity` [CONFIRMADO sdk/memory_injection.py:945] | nada premia "isso já apareceu N vezes"; correção repetida não sobe |
| Fallback prioriza recência/empresa, não relevância | se semântico vazio, cai em `order_by(updated_at.desc()).limit(15)` incluindo `user_id=0` [CONFIRMADO sdk/memory_injection.py:1013-1028] | recupera o recente, não o pertinente |

Não há **HyDE** nem **query expansion**: o prompt cru do usuário é embeddado direto. Para
um prompt curto e ambíguo ("e a conciliação?"), o embedding não tem densidade para casar
com a memória correta — e o sistema desiste para a recência.

### 1.5 F7 — Continuidade: janela de 5 + work_context sobrescrito (contaminação)

A continuidade entre sessões tem duas pernas:
- **Session window** = últimas 5 sessões [CONFIRMADO sdk/memory_injection.py:142+
  `_build_session_window`: "últimas 5 sessões", `.limit(5)`], formatadas ~150 chars cada,
  injetadas em Tier 0 [CONFIRMADO sdk/hooks.py:776-778].
- **`work_context.xml`** (contexto de trabalho corrente) é **sobrescrito
  incondicionalmente** a cada extração de tipo `contexto`: `existing.content = content`
  [CONFIRMADO services/pattern_analyzer.py:2064-2072].

O OVERWRITE é a raiz do **caso Marcus**: ele trabalhava conciliação financeira; uma
sessão de motos (outro domínio) rodou depois e **soterrou** o `work_context` de
conciliação. Na sessão seguinte, o agente "continuou" do contexto errado. Não há noção de
*domínio dominante* nem de *mesclar* — a última sessão sempre vence.

### 1.6 F10 — Amnésia do subagente

Subagentes têm permissão de **escrever** memória (compartilham os MCP tools de memória),
mas **não recebem injeção** de memória de domínio no spawn. O hook `SubagentStart` existe
[CONFIRMADO sdk/hooks.py:434 `_subagent_start_hook`] — e poderia injetar via
`additionalContext` — mas há um **BUG FIX 2026-05-26 que removeu deliberadamente o
`additionalContext`** porque ele causava o subagente a responder "conforme instrução do
SubagentStart hook" e dar `end_turn` precoce [CONFIRMADO sdk/hooks.py:516-538]. O gancho
existe e está desarmado por bug histórico. Resultado: o subagente entra sem saber o que o
agente principal e o usuário já estabeleceram — recomeça do zero.

### 1.7 Diagnóstico em uma frase

A maquinaria de memória pessoal está **construída e desligada**: extração funciona, mas a
promoção é flag-OFF + código morto (F1), o aprendizado é só de erro (F2), o perfil grande
zera o canal onde a correção vive (F4→F1), a recuperação desiste para recência (F6), a
continuidade é sobrescrita pela última sessão (F7) e o subagente não recebe nada (F10) —
ou seja, o sinal pessoal existe no banco e **morre no transporte**.

---

## PARTE 2 — ALVO ARQUITETURAL (o teto)

### 2.1 Princípio: memória pessoal é um SISTEMA DE ESCRITA-RECONCILIADA + RECUPERAÇÃO ADAPTATIVA

O estado-final trata memória não como "salvar texto e buscar por similaridade", mas como
um pipeline com **reconciliação no write-time** e **recuperação adaptativa no read-time**,
com um **canal garantido** para regras promovidas. Quatro pilares, ancorados na literatura
2026 de agent memory:

1. **Reconciliador write-time (ADD/UPDATE/DELETE/NOOP).** Toda nova memória passa por uma
   decisão explícita contra o que já existe — em vez do `return False` que descarta (F1d).
   Corrigir a mesma coisa duas vezes = **UPDATE** (reforça/atualiza), não NOOP silencioso.
   É o mecanismo do **Mem0** (arXiv:2504.19413), que extrai candidatos e os reconcilia com
   a memória existente como operação de primeira classe.
2. **Aprendizado POSITIVO (tipo "receita") + feedback 👍.** Adicionar um 5º tipo de
   extração pessoal — *procedural positivo* — e fechar o loop do thumbs up para reforçá-lo.
   É o **Memp** (arXiv:2508.06433): construir e atualizar uma memória *procedural* de
   trajetórias bem-sucedidas, não só de falhas.
3. **Core memory editável + canal duro de regras.** As regras pessoais promovidas vivem em
   um bloco imperativo fora do budget de Tier 2 — espelhando os `operational_directives`
   do Eixo A (A4) e a *core memory* do **MemGPT/CoALA** (arXiv:2309.02427): um bloco pequeno,
   editável, sempre presente, distinto da memória recuperável.
4. **Recuperação adaptativa.** **HyDE** (Gao et al. 2022) para prompts curtos (gera uma
   hipótese de resposta, embedda *ela*), **threshold adaptativo por tamanho de prompt**, e
   um **reranking** que injeta recorrência no composite. Mais um *just-in-time*
   `recall(topic)` como tool (padrão Anthropic *context engineering*): o agente puxa
   memória sob demanda em vez de receber tudo no prompt.

```
       WRITE-TIME (reconciliado)            READ-TIME (adaptativo)
  ┌──────────────────────────────┐   ┌──────────────────────────────────┐
  candidatos (correção/receita/   │   prompt curto? → HyDE → embedding   │
  preferência/expertise/contexto) │   threshold(len(prompt))             │
        │                         │   composite + recorrência (rerank)   │
   reconciliador ADD/UPDATE/      │   recall(topic) tool (just-in-time)  │
   DELETE/NOOP (Mem0)             │            │                         │
        │                         │            ▼                         │
   ┌────┴─────────────┐           │   ┌────────────────────────────┐     │
   CORE (regras duras,│ Tier 2    │   CANAL DURO  +  Tier 2          │     │
   fora do budget) ───┼──────────────▶ <user_rules mandatory>  semântica│  │
   PROCEDURAL (receitas)          │   (espelha A4)            (recall)    │
   SEMÂNTICA (resto)  │           │   anti-contaminação work_context     │
   └──────────────────┘           │   + injeção em SUBAGENTE (F10)        │
                                   └──────────────────────────────────────┘
```

### 2.2 Modelo de dados-alvo

Reaproveita `agent_memories` (já tem `escopo`, `importance_score`, `category`,
`correction_count`, `effective_count`) e adiciona três conceitos:

| Conceito | Onde encaixa | Para que |
|---|---|---|
| `category='procedural'` + tipo `receita` | nova categoria em `agent_memories` | aprendizado positivo (F2); paralela a `correction` |
| `recurrence_count` (re-uso real) | nova coluna ou reuso de `correction_count`/`effective_count` com semântica corrigida | premiar recorrência no composite (F6); reforçar correção repetida (F1d) |
| `promoted_at` / `priority='mandatory'` | flag em `agent_memories` | marca a memória que subiu ao canal duro `<user_rules>` (F1b/c) |
| `work_context` versionado por domínio | reuso de `AgentMemory` com path por domínio (`/context/work_context_{dominio}.xml`) | anti-contaminação (F7) |

O **canal duro** não é tabela nova: é um *render* — memórias `priority='mandatory'` (ou
promovidas pelo reconciliador) montadas como `<user_rules priority="mandatory">` em Tier 0,
fora do orçamento de Tier 2. Espelha exatamente o que `_build_user_rules` já sabe fazer
[config/feature_flags.py:488].

### 2.3 Encaixe nas 5 camadas do SDK

| Camada SDK | Componente do alvo G |
|---|---|
| **1. System prompt** | bloco `<user_rules priority="mandatory">` (Tier 0) — frame imperativo, espelha `operational_directives` do A4; **fora do budget** de Tier 2 |
| **2. Tools** | nova tool MCP `recall(topic)` — recuperação *just-in-time* sob demanda do agente (complementa a injeção automática, não substitui) |
| **3. Skills** | reconciliador write-time como passo do extrator pessoal (`pattern_analyzer`); HyDE/rerank no pipeline de injeção |
| **4. Subagents** | injeção de memória de domínio no `SubagentStart` via `additionalContext` (F10) — re-armar o gancho desarmado pelo bug 2026-05-26 |
| **5. Control (hooks)** | `UserPromptSubmit` ganha threshold adaptativo + HyDE; `SubagentStart` ganha contexto; extração pós-sessão dispara reconciliação |

---

## PARTE 3 — CAMINHO INCREMENTAL (reaproveitando o existente)

> Ordenado por dependência e alavancagem. Cada fase: tipo de mudança ([LIGAR]/[AJUSTAR]/
> [CONSTRUIR]), dependência cross-eixo, flag, e o que destrava. **Dependências de eixo:
> E (medição) ANTES dos atuadores que precisam saber se "deu certo"; F (gate de escrita
> empresa) ANTES de promover regra que vaze para escopo empresa.**

### Fase G-F1 — Fechar o loop corretivo pessoal (o plano de 3 fases)
**[LIGAR] + [AJUSTAR] + [CONSTRUIR] · alta alavancagem (é a dor do Marcus).**
- [LIGAR] `USE_USER_RULES_CHANNEL` (config/feature_flags.py:488) após validar com piloto —
  o canal `_build_user_rules` já está cabeado (sdk/memory_injection.py:766).
- [CONSTRUIR] **dar callsite** a `_is_mandatory_trigger` (pattern_analyzer.py:51, hoje
  morto) no extrator de correção/preferência, marcando `priority='mandatory'`.
- [AJUSTAR] trocar o `return False` que descarta correção repetida
  (pattern_analyzer.py:2074-2078) por UPDATE/reforço (`recurrence_count += 1`); chamar
  `_track_correction_feedback` no branch `tipo=='correcao'`.
- [AJUSTAR] corrigir a métrica cega: separar `effective_count` (eco, _helpers.py:496-511)
  de um sinal de *acerto* real vindo do Eixo E.
- **Segue o plano `2026-06-02-loop-corretivo-pessoal.md` (3 fases).** [confirmar/escrever]
- **Dep**: E (para o sinal de acerto substituir o eco textual). **Destrava**: a correção
  do usuário finalmente persiste com peso e é injetada no frame certo.

### Fase G-F4 — Liberar budget para a correção caber
**[LIGAR] + [AJUSTAR] · esforço P · risco baixo. Pré-requisito de eficácia do G-F1.**
- [LIGAR] `USE_USER_XML_POINTER` (config/feature_flags.py:201) — substitui `user.xml`
  inteiro por resumo+ponteiro quando excede threshold em budget finito
  (sdk/memory_injection.py:1084-1089).
- [AJUSTAR] **reservar uma fatia de budget para Tier 2** mesmo quando Tier 1 é grande, OU
  mover o canal duro (G-F1) para fora do budget de Tier 2 (já é o desenho do 2.2).
- **Dep**: nenhuma (é fundação). **Destrava**: Tier 2 deixa de zerar para Gabriella/Marcus
  (config/feature_flags.py:194-196) → a correção promovida e a semântica voltam a chegar.

### Fase G-F2 — Aprendizado positivo (tipo receita + feedback 👍)
**[CONSTRUIR] · esforço M.**
- [CONSTRUIR] 5º tipo de extração pessoal `receita` (`category='procedural'`) — o que deu
  certo, em frame prescritivo (regra R de prescritivo vs descritivo, services/CLAUDE.md).
- [LIGAR/AJUSTAR] fechar o loop do thumbs up: hoje `positive` só linka a `AgentStep` com
  `USE_AGENT_QUALITY_SPINE=true` (default OFF, config/feature_flags.py:833;
  routes/feedback.py:66-90) — ligar a flag e usar o 👍 para **reforçar** a receita.
- **Dep**: E (o spine `AgentStep`/`USE_AGENT_QUALITY_SPINE` é maquinaria do Eixo E — reusar,
  não duplicar). **Destrava**: ratio receita:armadilha sai de 0:1; o agente repete o que
  funcionou.

### Fase G-F6 — Recuperação adaptativa (HyDE + threshold + reranking)
**[CONSTRUIR] + [AJUSTAR] · esforço M-G · risco médio (qualidade de recall).**
- [CONSTRUIR] **HyDE** (Gao et al. 2022) no pipeline de injeção: para prompt curto, gerar
  hipótese de resposta e embeddar *ela* — resolve os ~91% de prompts < 150 chars.
- [AJUSTAR] **threshold adaptativo** por `len(prompt)`: relaxar
  `MEMORY_INJECTION_MIN_SIMILARITY` (hoje 0.45, config/feature_flags.py:188) para prompts
  curtos/expandidos por HyDE.
- [AJUSTAR] **reranking com recorrência**: adicionar termo de recorrência ao composite
  (hoje `0.3*decay + 0.3*imp + 0.4*sim`, sdk/memory_injection.py:945) — premiar memória
  que já provou útil/foi corrigida N vezes.
- [CONSTRUIR] tool `recall(topic)` *just-in-time* (camada 2 SDK).
- **Dep**: G-F1 (recorrência precisa de `recurrence_count` populado). **Destrava**:
  `semantic=0` deixa de ser default; a memória pertinente é recuperada, não a recente.

### Fase G-F7 — Anti-contaminação do work_context + ciclo de pendências
**[AJUSTAR] · esforço M.**
- [AJUSTAR] **eliminar o OVERWRITE incondicional** (pattern_analyzer.py:2064-2072): manter
  `work_context` por **domínio dominante** (path por domínio) ou mesclar via summaries —
  a sessão de motos não pode soterrar a de conciliação (caso Marcus).
- [AJUSTAR] cruzar com o session window (5 sessões, memory_injection.py:142) e o
  intersession briefing para um ciclo de pendências por domínio.
- **Dep**: D (ontologia define o "domínio" de forma robusta). **Destrava**: continuidade
  deixa de ser refém da última sessão.

### Fase G-F10 — Injeção de memória de domínio no subagente
**[AJUSTAR] · esforço M · risco médio (regressão do bug 2026-05-26).**
- [AJUSTAR] re-armar `_subagent_start_hook` (sdk/hooks.py:434) para injetar memória de
  domínio via `additionalContext` — **com cuidado**: o bug histórico (hooks.py:516-538) era
  o subagente responder "conforme o hook" e dar `end_turn`. A injeção precisa ser
  *contexto* explicitamente marcado como referência, não instrução.
- **Dep**: D (qual memória de domínio injetar) + E (medir se a injeção melhora ou regride o
  subagente). **Destrava**: subagente para de recomeçar do zero.

### Riscos transversais
- **Inchar o canal duro → omissão** (lost-in-the-middle / degradação por contagem de
  instruções, **IFScale** arXiv:2507.11538): cap `MANDATORY_RULES_MAX_COUNT` (~12,
  espelhando `MANDATORY_MAX_COUNT=5` já existente em config/feature_flags.py:217).
- **Budget starvation**: G-F4 deve ir antes de empurrar mais coisa para o prompt.
- **Falso-merge no dedup**: o reconciliador write-time pode fundir memórias distintas;
  validar com threshold + revisão (reusar o motor de dedup `_check_memory_duplicate`).
- **Regressão Web/Teams**: qualquer mudança em `memory_injection`/`hooks`/`feature_flags`
  afeta os dois canais — **testar no Teams** (export crítico, app/agente/CLAUDE.md).

### Fontes externas (ancoragem do alvo)
- **Mem0** — Building Production-Ready AI Agents with Scalable Long-Term Memory
  (arXiv:2504.19413) — reconciliação ADD/UPDATE/DELETE/NOOP no write-time.
- **ACE** — Agentic Context Engineering (arXiv:2510.04618) — contexto como playbook evolutivo.
- **IFScale** — degradação de obediência por contagem de instruções (arXiv:2507.11538) —
  cap do canal duro.
- **Memp** — Procedural Memory for LLM Agents (arXiv:2508.06433) — aprendizado positivo
  (memória de trajetórias bem-sucedidas).
- **CoALA** — Cognitive Architectures for Language Agents (arXiv:2309.02427) — tipologia de
  memória (working/episodic/semantic/procedural) + core editável.
- **Generative Agents** (arXiv:2304.03442) — recuperação por recência+importância+
  relevância (o composite que F6 implementa parcialmente, sem recorrência).
- **HyDE** — Precise Zero-Shot Dense Retrieval without Relevance Labels (Gao et al. 2022) —
  hipótese de resposta para prompts curtos.
- **Anthropic** — *Effective context engineering for AI agents* — just-in-time recall.

---

### O que NÃO está verificado

- **`semantic=0` / `tier2_chars=0` em PROD (F1a, F4)**: origem é leitura de log
  `[MEMORY_INJECT]` do user 18 (29/05–02/06), não inspecionei o banco PROD nem os logs
  diretamente nesta análise. Tratado como sintoma reportado, coerente com a mecânica de
  budget (1.3) que está confirmada em código.
- **~91% dos prompts < 150 chars (F6)**: métrica de log, não verificada por query nesta
  sessão. Afeta o ganho esperado do HyDE, não o desenho.
- **Threshold de similaridade**: a material citou 0.55; o código em
  `config/feature_flags.py:188` está em **0.45**. Divergência registrada — pode ter sido
  ajustado em produção via env (`AGENT_MEMORY_MIN_SIMILARITY`) ou a material referia outro
  ponto. O problema de F6 (prompts curtos + composite sem recorrência) independe do valor.
- **Plano `docs/superpowers/plans/2026-06-02-loop-corretivo-pessoal.md` (F1)**: **não foi
  encontrado** no repositório no momento da escrita. As 3 fases descritas em G-F1 derivam
  da material; o plano precisa ser confirmado/escrito antes de execução.
- **`AgentStep` / `USE_AGENT_QUALITY_SPINE` (F2)**: a tabela `agent_step`
  [CONFIRMADO models.py:2203, migration 2026_05_30] e a flag (default OFF) existem — é
  maquinaria do Eixo E que G-F2 reusa. Não verifiquei o esquema completo de `AgentStep`
  nem se o backfill histórico de 👍 é viável; afeta a riqueza do reforço positivo inicial.
- **Caso Marcus (F1/F7)**: a narrativa (correção que não persiste; sessão de motos
  soterrando conciliação) vem da material/memória, não de uma sessão reproduzida aqui. A
  *mecânica* que a explica (OVERWRITE em pattern_analyzer.py:2064-2072; budget em
  memory_injection.py:1070-1089) está confirmada em código.

# Crítica Arquitetural — Eixo E (Observabilidade de Qualidade)

> Revisor: arquiteto sênior cético. Lente de TETO (NUNCA critico por volume/over-engineering).
> Veredito, lacuna principal e elevação de ambição no final.

---

## Resumo do veredito

**AJUSTAR (sólido na visão, frágil na fundação).** O diagnóstico (Parte 1) é o mais bem
ancorado dos eixos que li: cada claim que verifiquei bate com o código
(orphan columns nunca escritas — `grep` confirma 0 writes; `_count_resolved` é proxy de
atividade — `insights_service.py:233,239,244` confirmado; sentiment score descartado no
callsite — `chat.py:560` captura só `enriched_prompt`, `detect_frustration` retorna
`(is_frustrated, score)` em `sentiment_detector.py:167`). O ALVO (Quality Signal Spine)
é coerente e a taxonomia implícito/explícito/judge/ground-truth é a certa para 2026.

**Mas a fundação (Fase E0) repousa sobre uma premissa de identidade de turno que o
código contradiz** — e isso, não corrigido, faz o spine inteiro nascer com uma chave
quebrada. É o tipo de erro que só aparece em produção, semanas depois, quando ninguém
consegue fazer o JOIN entre `turn_quality`, `feedback` e o dashboard. Detalho abaixo.

---

## 1. COERÊNCIA

### 1.1 Encaixe nas 5 camadas: correto, com uma imprecisão na camada 5

O mapeamento da seção 2.2 está certo (judge offline → subagent camada 4; harness →
skill camada 3; directive → camada 1). **Mas a camada 5 (hooks) é onde mora o defeito
estrutural** — ver seção 2 desta crítica. O `_stop_hook` escolhido como ponto de injeção
NÃO tem acesso à identidade de turno que o spine precisa. Isso não é detalhe de
implementação; é uma incoerência entre o desenho (turn_quality keyed por
`session_id`+`turn_index`+`message_id`, §2.3) e o ponto de captura escolhido (§2.2 + Fase E0).

### 1.2 Respeito às invariantes existentes

- **R10 (PRIMARY thread vs DEFESA generator)** — *violada implicitamente*. O blueprint
  propõe gravar `turn_quality` no `_stop_hook` (Fase E0). Mas a mensagem do assistente
  (com seu `id` = `msg_{uuid4}`, mintado em `models.py:245`) é escrita pela **thread
  daemon PRIMARY** (`run_async_stream`, R10 no CLAUDE.md), num `finally` que roda *após*
  o turno completar. O `_stop_hook` roda em outro contexto async, sem Flask app context
  (`hooks.py:406-420` cria um `create_app()` próprio justamente porque não tem), e
  conhece apenas o `sdk_session_id` efêmero (`hooks.py:376` `hook_input.get('session_id')`).
  **Introduzir uma terceira escrita correlacionada ao turno via `_stop_hook` adiciona um
  novo participante exatamente na corrida que R10 foi construída para domar.** O blueprint
  não reconhece R10 (não a cita) — é a invariante mais relevante do eixo e foi omitida.

- **best-effort dos services (R1)** — respeitada. O blueprint reusa o SAVEPOINT pattern de
  `insert_metric` (`models.py:1664-1719`, citado na Fase E0). Bom.

- **Constituição do estoque "1 skill = 1 objeto"** — o subagent `avaliador-qualidade` +
  skill `avaliando-qualidade-agente` (§2.2) respeitam a separação. Sem objeção.

- **Separação Web/Teams** — *lacuna não tratada*. O `_stop_hook` é compartilhado por Web
  e Teams (CLAUDE.md: "Teams + Web compartilham hook"). O spine de qualidade nasceria nos
  dois canais — correto — mas `feedback.py` (thumbs up/down) é **só Web**. O Teams tem
  feedback via Adaptive Card num fluxo completamente diferente (R4). O blueprint trata
  `feedback.py` como a fonte única de sinal explícito (§2.3, Fase E0) e ignora que metade
  do tráfego (Teams) não passa por ali. Sinal explícito do Teams fica órfão.

### 1.3 A fusão (§2.6 / E4) é coerente mas o acoplamento com o Eixo A é subespecificado

"Heurística só vira regra se os turnos que a aplicaram tiverem `fused_score` alto" (§2.6)
é a tese certa. Mas *atribuir* um `fused_score` a "os turnos que aplicaram a heurística X"
exige rastrear **qual diretriz/memória foi injetada em qual turno** — e isso não existe
hoje (memory_injection roda no boot, `memory_injection.py`, sem registrar por-turno o que
injetou). O blueprint assume essa atribuição como dada. É uma dependência de instrumentação
(do Eixo A ou D) que o E4 precisa, e não está mapeada.

---

## 2. REAPROVEITAMENTO

O reaproveitamento proposto é **majoritariamente correto e específico** — esse é o ponto
mais forte do blueprint. Clonar `subagent_validator.py` para o judge do principal (E2) é
exatamente certo: o esqueleto (Haiku `subagent_validator.py:28`, JSON `{score,reason,
flagged}` `:30-42`, Redis pubsub `:79-97`) está pronto. Reusar `sql_evaluator_falses_service`
como motor de calibração (E3) também — confirmei o mecanismo: embedding do par →
`cosine_similarity > threshold` → injeta contra-exemplo (`sql_evaluator_falses_service.py:1-21`,
`THRESHOLD_DEFAULT=0.80` `:35`). É genuinamente a mesma máquina.

### Peças existentes NÃO aproveitadas (que deveriam):

1. **`session_summarizer` já estrutura `acoes_usuario` por sessão** (`session_summarizer.py:79`,
   CLAUDE.md). O detector de correção N+1 (E1) reinventa a classificação "o user corrigiu?"
   quando o summarizer já produz uma leitura estruturada das ações do usuário. Não é
   substituto perfeito (summarizer é por-sessão, E1 quer por-turno), mas o blueprint deveria
   ao menos descartar explicitamente esse reuso — não o menciona.

2. **`AgentInvocationMetric.insert_metric` já resolve o problema de "gravar métrica
   correlacionada a uma execução fora do Flask context"** — e o blueprint reusa o SAVEPOINT,
   mas **não reusa a lição de chave**: `insert_metric` keia por `session_id =
   hook_input.get('session_id')` (`hooks.py:91`), que é o **SDK session_id efêmero**, NÃO
   nosso UUID. O blueprint herda silenciosamente essa chave errada (§2.3 lista `session_id`
   como "contexto do turno" sem dizer QUAL dos dois IDs — e R1 do CLAUDE.md grita que
   confundir os dois "causa sessão perdida"). Reaproveitar o pattern é certo; reaproveitar
   a chave sem perceber que ela é o ID errado para fazer JOIN com `feedback.py`/dashboard
   (que usam nosso UUID) é o bug latente nº 1.

3. **A lista de marcadores de frustração está duplicada** (`sentiment_detector.py:31-61` vs
   `friction_analyzer.py:336-340`) — o blueprint aponta isso (1.4d) e promete unificar na
   E1. Bom. Mas não aproveita que `friction_analyzer.analyze_friction` **já computa
   `repeated_queries`** (`friction_analyzer.py:319-373`) — que é exatamente o sinal
   "re-pergunta = falha" que a E1 quer minerar. A E1 propõe um classificador novo no início
   de cada turno quando o `repeated_queries` já existe (offline, é verdade — mas a lógica de
   detecção de repetição é reusável, não precisa ser reescrita).

---

## 3. REALIZABILIDADE

### Fase E0 — NÃO entrega valor com a chave proposta (precisa de pré-fase)

A E0 grava `turn_quality` no `_stop_hook`. Dois bloqueios reais:

- **Identidade de turno indisponível no ponto de injeção.** O `msg_id` do assistente
  (`models.py:245`) é mintado pela thread PRIMARY, não pelo hook. O `_stop_hook` só vê o
  `sdk_session_id`. Para keyar `turn_quality` corretamente (nosso UUID + msg_id), a escrita
  tem de acontecer **onde o nosso UUID e o msg_id coexistem** — ou seja, no callsite de
  persistência (`add_assistant_message`, R10 PRIMARY), NÃO no hook. O blueprint inverteu o
  ponto de captura. Isso transforma a E0 de "P, risco baixo" em "M, risco médio" e muda a
  arquitetura: o probe implícito deveria pendurar-se no **fim da thread PRIMARY** (onde
  `full_text` e msg_id existem), com o hook servindo apenas de gatilho assíncrono para o
  judge (E2), não de gravador do registro canônico.

- **`feedback.py` é session-level, não turn-level.** Verifiquei: `feedback.py` recebe só
  `session_id` (`feedback.py:46`), sem `message_id`/`turn_index`. Migrar para
  `turn_quality.explicit_feedback` (E0) exige que o **frontend passe a enviar qual turno**
  recebeu o thumbs — mudança em `chat.js` + contrato SSE (R8: 3 camadas). O blueprint
  trata isso como "migrar feedback.py" (uma linha), subestimando que é uma mudança de
  contrato frontend↔backend de 3 camadas. Rollback existe (flag), mas o esforço está
  mal-dimensionado.

**Rollback**: a tabela nova + flag dão rollback limpo. OK. O acoplamento perigoso é o
ponto de escrita: se escrito no hook, acopla o spine à corrida R10.

### Fase E1/E2/E3 — realizáveis, rollback OK

E2 (clonar validator) e E3 (reusar calibração) são as fases mais sólidas e com melhor
rollback (flags `USE_TURN_QUALITY_JUDGE`, harness offline não toca prod). Sem objeção
material além da herança de chave (§2.2 acima).

### Fase E4 — acoplamento com Eixo A bem-sinalizado, mas a interface é vaga

"Substituir `resolution_rate` no `_calc_health_score`" (`insights_service.py:368`) é
concreto e bom. O acoplamento com `USE_OPERATIONAL_DIRECTIVES` (`feature_flags.py:215`)
depende da atribuição turno→diretriz que não existe (ver 1.3). Risco real de E4 virar
"feito pela metade" porque a dependência upstream (instrumentar qual diretriz rodou em
qual turno) não está nem na E4 nem mapeada como dependência cross-eixo.

---

## 4. LACUNAS (o que o blueprint NÃO considerou)

1. **[A mais importante] Identidade de turno / colisão de IDs.** Detalhada em §2.2 e §3.
   O spine inteiro pressupõe uma chave de turno estável e joinável com `feedback.py` e o
   dashboard. O ponto de captura escolhido (`_stop_hook`) só tem o ID errado (SDK efêmero),
   e o ID certo (nosso UUID + msg_id) vive na thread PRIMARY governada por R10. **Sem
   resolver isso primeiro, E0 grava lixo não-joinável.**

2. **Teams como cidadão de segunda classe no sinal explícito.** §1.2 acima. Metade do
   tráfego não passa por `feedback.py`.

3. **Custo do judge online em turnos longos de tool-use (Odoo).** O blueprint cita
   amostragem (`QUALITY_JUDGE_SAMPLE_RATE`) para controlar custo, mas o input do judge
   inclui "tool_calls/results do turno" (§2.4). Turnos de inventário Odoo têm **dezenas de
   tool calls com resultados grandes** (o próprio `subagent_validator._build_user_prompt`
   trunca a 300/500 chars por tool, `:67-69`). Truncar a esse ponto num turno de 40 writes
   de estoque destrói a informação que o judge precisaria para julgar correctness. O
   blueprint não trata o caso de turno-com-trajetória-longa, que é justamente o turno de
   MAIOR valor e MAIOR risco do sistema (escrita Odoo). Ver elevação de ambição.

4. **Quem fecha o ciclo de calibração no Teams/sem-UI?** A E3 depende de "Rafael/admin
   discorda do judge (UI de revisão)". O `sql_evaluator_falses_service` é alimentado por
   `register_improvement` (MCP tool, `:5`) — um caminho que já existe e o blueprint poderia
   reusar como fonte de discordância sem construir UI nova. Não menciona.

5. **Versionamento do judge é citado (`judge_prompt_version`, §2.3) mas sem política de
   re-baseline.** Quando o prompt do judge muda, os `fused_score` históricos viram
   incomparáveis — e o health_score (E4) tem uma descontinuidade. Não há plano para isso
   (o `AgentInvocationMetric` tem o mesmo problema com `source`, mas ao menos separa
   dev/prod). Risco de o KPI de qualidade ter saltos artificiais a cada tuning do judge.

---

## 5. AMBIÇÃO — o alvo ficou TÍMIDO para ESTE sistema

O alvo proposto (um `fused_score ∈ [0,1]` + `label` por turno) é o estado-da-arte de
**2024-2025** (LLM-as-judge com calibração). É bom, mas para um agente cujo valor real está
em **trajetórias de escrita Odoo multi-step** (cancelar MO → transferir lote → escriturar
DFe → faturar SEFAZ — irreversível), um escalar por turno é a granularidade errada.

A literatura 2026 já saltou para **Process Reward Models (PRM) / step-level credit
assignment**: atribuir qualidade a cada AÇÃO da trajetória, não à resposta inteira
([AgentPRM, WWW 2026](https://dl.acm.org/doi/10.1145/3774904.3792551);
[STeCa, arXiv 2502.14276](https://arxiv.org/pdf/2502.14276);
[Verified Critical Step Optimization, arXiv 2602.03412](https://arxiv.org/abs/2602.03412)).
A tese central: num turno de N passos, um único passo errado (o `--confirmar` no quant
errado) é catastrófico e invisível num score agregado de turno — o turno pode parecer
"bom" (resposta fluente, tools rodaram) e ter executado uma escrita destrutiva.

### Elevação concreta (1, executável, reusa o existente):

**Promover o spine de turn-level para STEP-level, ancorado no audit hook determinístico
Odoo que JÁ existe (R9, `AGENT_ODOO_AUDIT_HOOK`).** O sistema já correlaciona cada
`execute_kw` Odoo a um `AGENT_TOOL_USE_ID` + sessão (`hooks.py` PreToolUse →
`operacao_odoo_auditoria`, CLAUDE.md R9). Isso é, *de fato*, um log de trajetória por-passo
já instrumentado — o substrato exato de um PRM. O teto não é `turn_quality`; é
**`step_quality`**: uma nota por AÇÃO de risco (toda escrita Odoo com `--confirmar`),
fundindo:
- o resultado determinístico da ação (sucesso/rollback/guard disparado — já em
  `operacao_odoo_auditoria`),
- o judge avaliando *aquele passo* contra a intenção (não o turno inteiro),
- o dry-run vs confirmado (o sistema já força dry-run-first em toda skill WRITE — é um
  par natural "previsto vs executado" para credit assignment).

Isso transforma o sinal de "essa conversa foi boa?" para "**essa transferência de 320k
unidades foi a transferência certa?**" — que é a pergunta que importa num sistema que
move estoque real. E reusa `operacao_odoo_auditoria` (R9) + o invariante dry-run-first
(constituição do estoque) como fonte de ground-truth de passo, sem inventar instrumentação
nova. O `turn_quality` do blueprint vira a *agregação* do `step_quality`, não a unidade
fundamental. Para os turnos sem Odoo (consulta), degrada graciosamente para o turn-level
do blueprint.

> Por que isso NÃO é over-engineering (lente de teto): o risco assimétrico já existe —
> uma escrita Odoo errada custa horas de reversão (memória `troca-codigo-azeite-soja-cd`,
> `ajustes-indevidos-maria-lf`). Medir qualidade no nível do turno deixa o sinal mais caro
> e arriscado do sistema (o passo de escrita) sem observabilidade própria. O teto de um
> agente operacional de estoque É o PRM de trajetória.

---

## Retorno

**Veredito: AJUSTAR.** Visão e reaproveitamento sólidos (diagnóstico impecável, clones de
`subagent_validator`/`sql_evaluator_falses` corretos), mas a **fundação (E0) está ancorada
no ponto de captura errado** e ignora a invariante R10.

**O quê ajustar:** mover a escrita canônica de `turn_quality` do `_stop_hook` para o fim
da thread PRIMARY (onde nosso UUID + msg_id coexistem, R10); usar o hook só como gatilho
assíncrono do judge. Resolver a chave de identidade (nosso UUID, não o SDK efêmero) ANTES
da E0 — senão o spine nasce não-joinável com `feedback.py` e o dashboard.

**Lacuna mais importante:** identidade de turno. O ID que o `_stop_hook` oferece
(`sdk_session_id`, `hooks.py:376`) não é o que `feedback.py` (`feedback.py:46`) e o
dashboard usam (nosso UUID, R1). Sem reconciliar isso, E0 grava registros que não
fazem JOIN com nada — e o blueprint relega o problema a uma nota de rodapé ("verificar se
`_stop_hook` recebe message_id", Parte 3) quando é o bloqueio nº 1.

**Elevação de ambição:** subir o spine de **turn-level para step-level (PRM)**, ancorado
no audit hook Odoo determinístico que já existe (R9 `operacao_odoo_auditoria`) + o
invariante dry-run-first. Medir qualidade por AÇÃO de risco (cada escrita Odoo confirmada),
não por resposta — porque num agente que move estoque real, o passo errado é catastrófico e
invisível num score agregado de turno.

## Fontes

- [AgentPRM: Process Reward Models for LLM Agents — WWW 2026](https://dl.acm.org/doi/10.1145/3774904.3792551)
- [STeCa: Step-level Trajectory Calibration — arXiv 2502.14276](https://arxiv.org/pdf/2502.14276)
- [Verified Critical Step Optimization for LLM Agents — arXiv 2602.03412](https://arxiv.org/abs/2602.03412)

# Frameworks cognitivos aristotélicos para agentes de IA em produção

**A arquitetura cognitiva aristotélica mapeia de forma notavelmente precisa para sistemas de agentes LLM modernos — não como metáfora, mas como scaffolding de engenharia prático.** A cadeia deliberativa bouleusis → proairesis → praxis encontra implementação direta no extended thinking do Claude, no Plan Mode e na execução gated por hooks. As Quatro Causas se tornam um checklist estruturado pré-ação executável via system prompts. E a memória de erro como habituação computacional (ethismos → hexis) já possui implementações de nível produção através de padrões Reflexion e knowledge graph memory. Este relatório fornece templates de prompt concretos, padrões de código e designs de arquitetura para implementar as três camadas no stack do frete_sistema e no workflow com Claude Code.

---

## As Quatro Causas como checklist de raciocínio pré-ação

O padrão mais imediatamente implementável é codificar as Quatro Causas de Aristóteles como framework de análise estruturada no system prompt do agente. Pesquisas confirmam que **checklists estruturados pré-ação melhoram o raciocínio de LLMs em 26-32%** (Wang 2023, Zhou 2024), e as Quatro Causas fornecem um quadro analítico filosoficamente completo que mapeia de forma limpa para operações de agentes.

Aqui está uma seção concreta de system prompt para os agentes do frete_sistema:

```xml
<protocolo_deliberacao>
Antes de executar qualquer ação, analise usando o framework das Quatro Causas:

<causa_material>
Quais dados, recursos e inputs estão envolvidos? Qual é o substrato 
desta operação? Liste tabelas específicas, APIs, inputs do usuário e 
documentos de contexto sendo consumidos. Sinalize dados faltantes ou incertos.
</causa_material>

<causa_formal>
Qual padrão, estrutura ou regra se aplica? Qual protocolo ou heurística 
do knowledge graph corresponde a esta situação? Qual é a forma esperada 
da solução correta?
</causa_formal>

<causa_eficiente>
Qual mecanismo impulsiona este resultado? Qual é a cadeia causal de 
input a output? Qual agente, ferramenta ou processo é responsável por 
cada etapa de transformação?
</causa_eficiente>

<causa_final>
Qual é o propósito (telos) desta ação? Como ela serve o objetivo real 
do usuário? Como seria o sucesso, e o que constituiria fracasso? Esta 
ação está alinhada com os objetivos do sistema?
</causa_final>

<avaliacao_confianca>
Avalie sua confiança (0-100) em cada análise de causa. Se qualquer causa 
pontuar abaixo de 70, sinalize para revisão humana antes de prosseguir.
</avaliacao_confianca>
</protocolo_deliberacao>
```

Isso funciona porque Claude responde bem a raciocínio estruturado com tags XML — a própria documentação da Anthropic recomenda tags `<thinking>` e `<answer>` para separar raciocínio de output. O framework das Quatro Causas força **análise exaustiva** antes da ação: a causa material detecta problemas de qualidade de dados, a causa formal ativa padrões relevantes do knowledge graph, a causa eficiente traça cadeias causais, e a causa final previne desvio de objetivo.

Para o sistema de roteamento, implemente isso como **etapa de deliberação pré-roteamento**. Antes do roteador despachar para um subagente, o agente principal completa a análise das Quatro Causas, que então se torna parte do contexto passado ao subagente. Isso espelha a distinção aristotélica onde phronesis (sabedoria prática do orquestrador) guia techne (conhecimento técnico do especialista).

O framework SELF-DISCOVER do Google DeepMind valida esta abordagem empiricamente. Ele melhora performance do GPT-4 em **até 32% no BigBench-Hard** enquanto requer 10-40x menos chamadas de inferência que chain-of-thought com self-consistency. SELF-DISCOVER funciona fazendo o modelo selecionar e compor módulos de raciocínio relevantes para a tarefa — as Quatro Causas servem precisamente como tais módulos.

---

## Bouleusis como transparência deliberativa acionável

A cadeia bouleusis → proairesis → praxis (deliberação → escolha → ação) mapeia diretamente para três funcionalidades do Claude: extended thinking, structured output e execução gated por hooks. O desafio de engenharia chave é tornar a deliberação **visível e acionável** em vez de trancada dentro do raciocínio interno do modelo.

**Extended thinking como bouleusis.** O extended thinking do Claude (configurável via `budget_tokens` ou modo adaptivo) fornece um espaço dedicado para raciocínio passo-a-passo antes da geração de resposta. Em workflows agênticos, **thinking intercalado** permite que Claude raciocine entre chamadas de ferramentas — deliberando sobre resultados antes de decidir a próxima ação. Isso é bouleusis implementado no nível de inferência:

```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000  # Mínimo 1.024; maior = deliberação mais profunda
    },
    messages=[{"role": "user", "content": task_description}]
)

# Extrair deliberação (bouleusis) e decisão (proairesis) separadamente
for block in response.content:
    if block.type == "thinking":
        store_deliberation(block.thinking)  # Log no knowledge graph
    elif block.type == "text":
        execute_decision(block.text)  # Prosseguir para praxis
```

**Execução gated por confiança como proairesis.** A etapa de escolha (proairesis) requer que o agente se comprometa com uma ação baseada na qualidade da deliberação. Implemente isso através de structured output com scoring de confiança:

```python
decision_schema = {
    "type": "object",
    "properties": {
        "resumo_deliberacao": {"type": "string"},
        "confianca": {"type": "number", "minimum": 0, "maximum": 100},
        "acao_escolhida": {"type": "string"},
        "acoes_alternativas": {"type": "array", "items": {"type": "string"}},
        "avaliacao_risco": {"type": "string"},
        "requer_revisao_humana": {"type": "boolean"}
    }
}
```

Quando a confiança cai abaixo de um threshold, o sistema roteia para revisão humana em vez de executar. Pesquisa sobre calibração de confiança mostra que **confiança verbalizada de LLMs tende à superconfiança** (Xiong et al., ICLR 2024), então calibre seu threshold empiricamente — comece em 80 e ajuste com base nas taxas de falsa-confiança observadas.

**Hooks como portões de praxis.** O hook `PreToolUse` do Claude Agent SDK fornece a camada de enforcement mecânico. Antes de qualquer ferramenta executar, um hook pode verificar que a deliberação ocorreu e atendeu padrões de qualidade:

```python
async def require_deliberation(input_data, tool_use_id, context):
    # Verificar que o agente completou análise das Quatro Causas
    if "causa_material" not in str(context.get("recent_reasoning", "")):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": 
                    "Ação bloqueada: complete a deliberação das Quatro Causas antes de executar."
            }
        }
    return {}
```

Esta arquitetura de três camadas (extended thinking → decisão estruturada → execução gated por hook) impõe mecanicamente a cadeia deliberativa aristotélica. A deliberação é transparente porque thinking blocks são extraíveis, decisões são JSON estruturado, e hooks criam trilha de auditoria.

---

## Dynamis/energeia como avaliação de risco pré-mortem

A distinção potencialidade/atualidade de Aristóteles se traduz em um padrão de engenharia concreto: antes de executar (energeia/atualidade), o agente mapeia modos potenciais de falha (dynamis/potencialidade). Pesquisa sobre a técnica pré-mortem de Gary Klein mostra que **imaginar que um projeto já falhou aumenta a capacidade de identificar causas de falha em 30%**.

Implemente isso como análise pré-ação obrigatória no system prompt:

```xml
<analise_pre_mortem>
Antes de executar esta ação, imagine que ela JÁ FALHOU.

1. CENÁRIOS DE FALHA: Gere 3-5 formas específicas que isso poderia dar errado.
   Para cada: descreva a falha, avalie probabilidade (1-10), avalie severidade (1-10).

2. SINAIS DE ALERTA: Quais indicadores precoces sinalizariam cada falha?

3. DYNAMIS NEGATIVA (potencialidades negativas):
   - Integridade de dados: O input poderia estar corrompido, desatualizado ou incompleto?
   - Estado do sistema: Operações concorrentes poderiam criar race conditions?
   - Impacto no usuário: Esta ação poderia causar dano irreversível aos dados do usuário?
   - Risco de cascata: Falha aqui poderia disparar falhas em sistemas downstream?

4. CONTRAMEDIDAS: Para cada cenário de alto risco (probabilidade × severidade > 30):
   - PREVENIR: Como impedir que isso aconteça
   - DETECTAR: Como perceber cedo
   - RECUPERAR: Como reverter ou mitigar

5. DECISÃO: Prosseguir, prosseguir-com-salvaguardas, ou escalar-para-humano?
</analise_pre_mortem>
```

Para o frete_sistema especificamente, codifique **armadilhas** (memórias de erro) de falhas passadas como padrões de dynamis negativa no knowledge graph. Quando a análise pré-mortem roda, o agente consulta o knowledge graph para falhas passadas similares. Isso cria um loop de feedback onde cada falha enriquece avaliações de risco futuras — habituação computacional em ação.

O padrão OODA-subagents do repositório `al3rez/ooda-subagents` demonstra isso concretamente com Claude Code: quatro subagentes em `.claude/agents/` implementam Observar (scan de logs e contexto), Orientar (identificar padrões e riscos), Decidir (recomendar estratégia) e Agir (executar com salvaguardas).

---

## Ciclo BDI mapeado para arquitetura de system prompt

O modelo Belief-Desire-Intention fornece o framework mais prático para estruturar o system prompt do agente em seções funcionais. Pesquisa do APXML e do paper ChatBDI (AAMAS 2025) confirma que **BDI funciona melhor como scaffolding conceitual para organização de prompt**, não como arquitetura simbólica literal.

Estruture o system prompt do agente principal do frete_sistema em três seções explícitas:

```xml
<crencas>
<!-- Atualizadas a cada turno a partir de contexto, queries ao KG e resultados de ferramentas -->
Estado atual do sistema: {resumo_estado}
Contexto do usuário: {perfil_usuario, historico_sessao}
Restrições conhecidas: {protocolos_ativos do knowledge graph}
Observações recentes: {resultados_ferramentas, flags_erro}
Confiança nas crenças: {scores de confiança por crença}
Armadilhas relevantes: {padrões de erro recuperados para este contexto}
Heurísticas relevantes: {atalhos de padrão recuperados}
</crencas>

<desejos>
<!-- Relativamente estáveis na sessão; atualizados pelos objetivos do usuário -->
Objetivo principal: {objetivo declarado do usuário}
Objetivos do sistema: {confiabilidade, precisão, satisfação_usuario}
Restrições: {limites de segurança, limites de recursos, escopo de autorização}
Ordenação de prioridade: {quais objetivos têm precedência em conflito}
</desejos>

<intencoes>
<!-- Plano de ação comprometido; persiste até conclusão ou revisão -->
Plano atual: {sequência de ação passo-a-passo}
Etapa atual: {qual etapa estamos executando agora}
Recursos comprometidos: {quais subagentes alocados, quais ferramentas reservadas}
Critérios de conclusão: {como sabemos que terminamos}
Gatilhos de revisão: {o que causaria revisão do plano}
</intencoes>
```

O insight chave da literatura acadêmica é que **crenças em agentes LLM são compostas** — combinam conhecimento paramétrico (pesos do modelo), informação contextual (conteúdo do prompt), conhecimento recuperado (RAG/knowledge graph) e conhecimento inferido (raciocínio chain-of-thought). A taxonomia epistemológica do seu knowledge graph mapeia diretamente:

- **Armadilhas** (memórias de erro) → crenças sobre o que NÃO fazer, recuperadas por similaridade ao contexto atual
- **Heurísticas** (atalhos de padrão) → crenças sobre o que GERALMENTE funciona, ativadas por correspondência de padrões
- **Protocolos** (regras procedurais) → intenções pré-comprometidas, ativadas por condições de gatilho

---

## Memória de erro como ethismos computacional

O conceito aristotélico de ethismos (habituação) → hexis (disposição estável) → phronesis (sabedoria prática) descreve como a prática repetida constrói julgamento confiável. No seu sistema de agentes, isso se traduz em: **episódios individuais de erro → padrões de erro generalizados → regras procedurais que previnem recorrência**.

O padrão Reflexion (Shinn et al., NeurIPS 2023) fornece a implementação fundacional. Após cada ação, o agente reflete sobre o resultado, gera uma lição textual e armazena em memória episódica. Em tarefas similares subsequentes, essas reflexões são recuperadas e injetadas no contexto. Reflexion alcançou **14% de melhoria de acurácia** em benchmarks de raciocínio e completou 130/134 tarefas do AlfWorld quando combinado com ReAct.

Para o stack PostgreSQL/Knowledge Graph, implemente um pipeline de consolidação de memória em três tiers:

**Tier 1 — Episódico (armadilhas brutas).** Armazene cada erro como episódio timestamped com contexto completo: o que aconteceu, o que foi tentado, o que deu errado, qual teria sido a ação correta. Use o knowledge graph existente com entidades linkadas a episódios de erro.

**Tier 2 — Semântico (heurísticas generalizadas).** Periodicamente consolide erros episódicos em padrões generalizados. Uma etapa de sumarização dirigida por LLM extrai a lição transferível: "Ao processar cálculos de frete com CEPs faltantes, sempre valide completude do endereço antes de rotear para o subagente de cálculo." O framework ReasoningBank (Ouyang et al. 2025) demonstra que destilar estratégias de raciocínio generalizáveis de sucessos e falhas **economiza aproximadamente 2x em custos operacionais** ao evitar tentativa-e-erro repetida.

**Tier 3 — Procedural (protocolos codificados).** Quando uma heurística foi validada em múltiplos contextos, promova-a a protocolo — uma regra hard codificada no system prompt ou CLAUDE.md. Isso espelha a progressão aristotélica de prática para disposição estável.

Implemente **decaimento de crença** (do implementation OODA com Cloudflare Workers): scores de confiança em memórias armazenadas decaem com o tempo (τ=0.95 por ciclo), então padrões de erro desatualizados naturalmente carregam menos peso. Isso previne que o agente sobre-indexe em modos de falha obsoletos — uma forma de esquecimento computacional que espelha como a habituação biológica se adapta a ambientes em mudança.

---

## Claude Code como ambiente de desenvolvimento aristotélico

A arquitetura do Claude Code mapeia quase perfeitamente para o framework aristotélico, requerendo apenas organização deliberada para ativar.

**CLAUDE.md como memória epistemológica.** Estruture o CLAUDE.md do projeto com categorias epistemológicas explícitas. Mantenha abaixo de 200 linhas (recomendação da Anthropic) e use `@imports` para profundidade:

```markdown
# frete_sistema — CLAUDE.md

## Armadilhas (memórias de erro — NÃO repita estes)
@.claude/memory/armadilhas.md

## Heurísticas (atalhos de padrão — tente estes primeiro)
@.claude/memory/heuristicas.md

## Protocolos (regras procedurais — SEMPRE siga estes)
- Nunca modifique schema do banco sem arquivo de migration
- Sempre rode `pytest tests/` antes de commitar
- Roteie cálculos de frete pelo subagente de validação primeiro
- Use structured output para toda comunicação inter-agente
- Regras R1-R7 do Teams bot são invioláveis

## Decisões de arquitetura
@.claude/memory/arquitetura.md

## Comandos de build/test
- Test: `pytest tests/ -v`
- Lint: `ruff check .`
- Run: `flask run --debug`
```

O arquivo `.claude/memory/armadilhas.md` acumula padrões de erro entre sessões. O sistema de auto-memória do Claude Code já salva insights de debugging em `~/.claude/projects/<projeto>/memory/`, mas ao estruturar isso explicitamente com categorias epistemológicas, você ativa o pipeline habituação → disposição → sabedoria.

**Plan Mode como bouleusis.** O comando `/plan` (Shift+Tab duas vezes) impõe deliberação read-only antes de qualquer modificação de código. Planos persistem como markdown em `~/.claude/plans/` e sobrevivem `/clear` e compactação de contexto. Use Plan Mode sistematicamente para qualquer mudança tocando mais de 3 arquivos. Para máxima qualidade deliberativa, use **Opus Plan Mode** (Opção 4 em `/model`), que usa Opus para planejamento e Sonnet para execução com contexto de 1M.

Enriqueça seus prompts de plano para incluir antecipação de consequências:

```
Planeje o refatoramento do módulo de roteamento. Antes de propor mudanças:
1. Liste todos os módulos que dependem do módulo de roteamento
2. Para cada dependência, descreva o que quebraria se a interface mudar
3. Identifique a mudança mais arriscada (maior raio de explosão)
4. Proponha a sequência de mudanças que minimize risco em cada etapa
5. Defina pontos de rollback após cada mudança importante
```

**Subagentes como especialistas em techne.** Crie subagentes customizados em `.claude/agents/` para papéis especializados. Cada subagente recebe seu próprio system prompt e permissões de ferramentas — esta é a divisão phronimos/techne implementada mecanicamente:

```markdown
---
name: validador-frete
description: "Valida inputs de cálculo de frete e detecta erros comuns"
tools: ["Read", "Grep", "Glob", "Bash"]
model: sonnet
---
Você é um especialista em validação de frete. Seu papel é verificar 
integridade de dados antes que cálculos prossigam.

Verifique: CEPs faltantes, formatos de peso inválidos, pares 
origem/destino incompatíveis, e quaisquer padrões correspondentes a 
armadilhas conhecidas em .claude/memory/armadilhas.md.

Sempre produza JSON estruturado com validacao_passou (boolean), 
problemas (array) e confianca (0-100).
```

**Hooks como enforcement de dynamis negativa.** Configure hooks pré-ação em `.claude/settings.json` para impor análise pré-mortem antes de operações destrutivas:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Edit|Write|Bash",
      "hooks": [{
        "type": "prompt",
        "prompt": "Antes desta edição: O que pode dar errado? Liste 2 riscos."
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "cd $PROJECT_DIR && python -m pytest tests/ --tb=short -q 2>&1 | tail -5"
      }]
    }]
  }
}
```

O hook `PreToolUse` com prompt força Claude a articular riscos antes de editar. O hook `PostToolUse` com comando roda testes após cada edição — feedback imediato que habilita o padrão Reflexion dentro do workflow de codificação.

**Extended thinking para bouleusis profunda.** Ao trabalhar em decisões arquiteturais complexas, use os gatilhos escaláveis de thinking do Claude Code: "think hard" → "think harder" → "ultrathink." Cada nível aumenta o budget de thinking, dando ao modelo mais espaço de deliberação. Para decisões críticas de produção, solicite explicitamente que Claude externalize seu raciocínio: "Escreva seu raciocínio completo numa seção `## Log de Decisão` do arquivo relevante antes de implementar."

---

## Padrões concretos de prompt que implementam estes frameworks

A pesquisa revelou diversas técnicas validadas de prompt engineering que são estruturalmente equivalentes a raciocínio aristotélico, independentemente de sua rotulação.

**Metacognitive Prompting** (Wang 2023) implementa um ciclo deliberativo de cinco estágios que espelha bouleusis: Compreensão → Julgamento Preliminar → Avaliação Crítica → Decisão Final → Avaliação de Confiança. Melhorou performance de LLMs em **até 26.9%** em tarefas de NLU. O estágio de avaliação crítica — "Existem interpretações alternativas? Você poderia estar errado?" — implementa diretamente o conceito de Aristóteles de examinar alternativas concorrentes antes da escolha.

**SELF-DISCOVER** (Google DeepMind 2024) faz o modelo primeiro selecionar módulos de raciocínio relevantes para uma tarefa, adaptá-los ao contexto específico, e então compô-los em um plano de raciocínio estruturado. Isso é proairesis (escolha deliberada de meios) implementada computacionalmente. As estruturas de raciocínio transferem entre famílias de modelos, sugerindo que capturam raciocínio genuinamente intrínseco à tarefa.

**O padrão Reflexion** implementa ethismos através de reinforcement learning verbal: tentar → refletir sobre falha → armazenar lição → retentar com sabedoria acumulada. Sem atualização de pesos necessária — aprendizado acontece através de injeção de memória episódica.

**Deliberative alignment** (abordagem da OpenAI para modelos série-o) treina modelos para raciocinar explicitamente através de especificações de segurança em seu chain-of-thought antes de responder. Esta é a implementação mais literal de bouleusis em produção: o modelo identifica princípios relevantes, raciocina sobre se a requisição viola cada um, e gera resposta compatível com a política. O resultado é uma **redução simultânea tanto em compliance com jailbreak quanto em sobre-recusa** — uma melhoria de Pareto.

Para triagem de consequências essenciais vs. acidentais (distinção de Aristóteles entre propriedades essenciais e acidentais), use este padrão de prompt:

```xml
<triagem_consequencias>
Para a ação proposta, classifique cada consequência:

ESSENCIAL (muda resultado fundamental):
- Esta consequência alteraria se o objetivo central do usuário é alcançado?
- Esta consequência é irreversível?
- Esta consequência afeta integridade de dados ou estado do sistema permanentemente?

ACIDENTAL (variação menor, não muda resultado central):
- Isso é puramente cosmético ou de formatação?
- Pode ser facilmente corrigido depois?
- Afeta apenas metadados não-críticos?

REGRA DE DECISÃO: Endereçe todas as consequências essenciais antes de agir.
Registre consequências acidentais para otimização posterior. Nunca permita
que preocupações acidentais bloqueiem ação sobre objetivos essenciais.
</triagem_consequencias>
```

---

## Conclusão e prioridade de implementação

As três camadas aristotélicas — deliberação estruturada, antecipação de consequências e habituação de erro — não são abstrações filosóficas que requerem tradução para engenharia. São **design patterns com implementações mecânicas diretas** no ecossistema Claude. As Quatro Causas viram checklists pré-ação com tags XML executáveis via hooks. Bouleusis vive em thinking blocks extraíveis pela API. Ethismos opera através de memória episódica estilo Reflexion com decaimento de crença no knowledge graph PostgreSQL.

O insight mais relevante desta pesquisa é que **a divisão phronesis/techne mapeia exatamente para o padrão orquestrador-trabalhador** que domina sistemas multi-agente em produção. O agente principal do frete_sistema é o phronimos — ele delibera, julga contexto e delega. Os subagentes são technitai — executam conhecimento técnico especializado. A taxonomia epistemológica do knowledge graph (armadilha/heurística/protocolo) implementa a progressão ethismos → hexis → phronesis que Aristóteles descreveu como o caminho da prática à sabedoria.

**Prioridade imediata de implementação:**

1. **Adicionar o bloco de deliberação das Quatro Causas** ao system prompt do agente principal — forçando análise estruturada antes de cada ação consequente
2. **Estruturar CLAUDE.md com categorias epistemológicas explícitas** e `@imports` para armadilhas, heurísticas e protocolos
3. **Criar hook `PreToolUse`** impondo análise pré-mortem em operações destrutivas
4. **Implementar decaimento de crença** nas memórias de erro do knowledge graph para que padrões desatualizados percam influência naturalmente

Cada um desses itens é realizável em uma única sessão de desenvolvimento e produz melhoria mensurável na qualidade de raciocínio do agente.
# Confiabilidade de Subagentes — Protocolo Operacional

**Ultima Atualizacao**: 13/02/2026

---

## Por Que Este Documento Existe

Subagentes trabalham com ~100K tokens de contexto mas retornam um **resumo compactado** (~1-2K tokens) ao agente principal. Ratio de compressao: **10:1 a 50:1**. O principal NAO tem acesso ao trace de raciocinio, tool calls intermediarios, hipoteses descartadas ou dados brutos que geraram o resumo.

**Consequencia**: Se o subagente produzir informacao incorreta e o principal nao detectar pela propria experiencia, o erro **propaga silenciosamente**. Nao existe mecanismo automatico de validacao.

---

## Falhas Documentadas

| Tipo | Descricao | Risco |
|------|-----------|-------|
| **Fabricacao de output** | Subagente Bash gera output sem executar comandos (Issue #21585) | Debug de problema inexistente |
| **Alucinacao MCP** | Tools MCP project-scoped falham silenciosamente, resultados fabricados (Issue #13898) | Dados ficticios aceitos como reais |
| **Perda de contexto** | Apos 2-3 resumes, "correcoes" alucinadas aparecem (Issue #11712) | Dados corretos sobrescritos |
| **Alucinacao de input** | Em ~120K tokens, modelo gera `###Human:` fabricado (Issue #10628) | Instrucoes fantasma executadas |

---

## O Que Se Perde na Compressao

| Categoria | Exemplo | Impacto |
|-----------|---------|---------|
| Raciocinio intermediario | Hipoteses descartadas, becos sem saida | Principal nao sabe POR QUE |
| Dados brutos de tools | Conteudo de arquivos, outputs de grep | Impossivel cross-check |
| Sinais de confianca | Incerteza do subagente | Tudo parece igualmente certo |
| Resultados negativos | O que NAO foi encontrado | Principal assume que existe |
| Assuncoes feitas | Interpretacoes de ambiguidade | Herdadas sem saber |

---

## Protocolo de Mitigacao

### M1: File-System como Memoria Compartilhada (PRINCIPAL)

O subagente escreve findings detalhados em arquivo. O principal le o arquivo para verificacao, bypassando a compressao lossy.

**Diretorio padrao**: `/tmp/subagent-findings/`

**Formato do arquivo**:
```markdown
# Findings: {nome-agente} — {timestamp}

## Tarefa
{descricao da tarefa recebida}

## Fatos Verificados
- {afirmacao} — FONTE: {arquivo:linha} ou {modelo.campo = valor}

## Inferencias
- {conclusao deduzida} — BASEADA EM: {fatos que suportam}

## Nao Encontrado
- {item buscado mas nao achado} — BUSCADO EM: {onde procurou}

## Assuncoes
- {decisao tomada sem confirmacao explicita}

## Dados Brutos Relevantes
{outputs de scripts, trechos de arquivos — o que for crucial}
```

### M2: Prompts Estruturados com Definition of Done

Todo prompt de subagente DEVE incluir criterios de output:
- "Distinga fatos verificados de inferencias"
- "Inclua file_path:line para cada afirmacao"
- "Reporte o que NAO encontrou"
- "Marque assuncoes como [ASSUNCAO]"
- "Escreva findings detalhados em /tmp/subagent-findings/"

### M3: Subagentes Read-Only para Pesquisa

Para tarefas de **pesquisa/diagnostico**, preferir subagentes com tools read-only (Explore, Plan). Limita blast radius de output incorreto.

Para tarefas de **implementacao**, usar agentes com tools completos (general-purpose), mas o principal DEVE verificar o resultado.

### M4: Verificacao pelo Principal

Apos receber output de subagente, o principal DEVE:

1. **Checar arquivo de findings** em `/tmp/subagent-findings/` (se existir)
2. **Cross-check** afirmacoes criticas contra fontes primarias
3. **Desconfiar** de dados que nao pode verificar independentemente
4. **Nunca propagar** dados de subagente sem evidencia propria se a decisao for critica

---

## Guia para o Agente Principal

### Ao Spawnar Subagente via Task Tool

```
PROMPT TEMPLATE (adicionar ao final):

---
PROTOCOLO DE OUTPUT (OBRIGATORIO):
1. Crie /tmp/subagent-findings/ se nao existir
2. Escreva findings detalhados em /tmp/subagent-findings/{nome}-{contexto}.md
3. No resumo retornado, DISTINGA fatos de inferencias
4. REPORTE o que buscou e NAO encontrou
5. MARQUE assuncoes com [ASSUNCAO]
6. CITE fontes (arquivo:linha) para toda afirmacao
---
```

### Quando Verificar (Matriz de Risco)

| Tipo de Tarefa | Risco se Errado | Verificacao Necessaria |
|----------------|-----------------|------------------------|
| Pesquisa exploratoria | Baixo | Ler resumo, confiar |
| Diagnostico de problema | Medio | Ler findings detalhados |
| Levantamento de dados para decisao | Alto | Cross-check dados criticos |
| Implementacao de codigo | Alto | Revisar TODOS os arquivos tocados |
| Operacao no Odoo/producao | Critico | Verificar ANTES de executar |

### Sinais de Alerta no Output do Subagente

Desconfiar quando:
- Output muito "limpo" sem nuances ou incertezas
- Dados numericos suspeitamente redondos
- Afirmacoes sem citacao de fonte
- Ausencia de secao "nao encontrado"
- Resultado contradiz conhecimento previo do principal

---

## Fontes

- Anthropic Context Engineering: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Claude Code Sub-agents: https://code.claude.com/docs/en/sub-agents
- Fabricacao de output: https://github.com/anthropics/claude-code/issues/21585
- Alucinacao MCP: https://github.com/anthropics/claude-code/issues/13898
- Perda de contexto resume: https://github.com/anthropics/claude-code/issues/11712
- Multi-Agent Failures (arXiv:2503.13657): https://arxiv.org/pdf/2503.13657
- Error Amplification (arXiv:2512.08296): https://arxiv.org/abs/2512.08296

# Detalhamento das 7 Fases

---

## Fase 0: ESCOPO (Agente Principal, sem subagentes)

**Proposito**: Delimitar o problema ANTES de qualquer pesquisa.

### Atividades

1. Decompor o pedido do usuario em **problema declarado** (1-3 frases)
2. Listar **perguntas de pesquisa** numeradas e atomicas
3. Classificar complexidade:
   - **P** (pontual): 1 arquivo, < 200 LOC → resolver direto, sem skill
   - **M** (modulo): multi-arquivo, mesmo modulo, < 2K LOC → pesquisa direta pelo principal
   - **G** (grande): cross-modulo, < 10K LOC → subagentes de pesquisa
   - **XG** (extra-grande): system-wide, 10K+ LOC → subagentes em ondas
4. Identificar modulos afetados e CLAUDE.md relevantes
5. Decidir: precisa de subagentes? (P/M = nao, G/XG = sim)

### Gate de Saida

- [ ] Problema definido em 1-3 frases
- [ ] Perguntas de pesquisa listadas (numeradas, atomicas)
- [ ] Complexidade classificada (P/M/G/XG)
- [ ] Modulos e CLAUDE.md relevantes identificados
- [ ] Decisao sobre subagentes tomada

### Budget de Contexto: ~5%

---

## Fase 1: PESQUISA ATOMICA (Subagentes Read-Only)

**Proposito**: Coletar FATOS verificados atraves de unidades atomicas de pesquisa.

### Principio Chave

Em vez de 1 subagente fazer "pesquise o problema", spawnar N subagentes cada um respondendo UMA pergunta. Cada pergunta produz 1 arquivo de findings.

### Tipos de Pergunta

| Tipo | Padrao | Output |
|------|--------|--------|
| INVENTARIO | "Liste todos os arquivos em {modulo} com LOC, proposito e exports" | Manifesto de arquivos |
| DEPENDENCIA | "Mapeie todos os imports para dentro e fora de {arquivo}" | Grafo de dependencias |
| COMPORTAMENTO | "Trace o caminho de codigo para {operacao} de entrada a saida" | Call chain |
| DADOS | "Documente schema e relacionamentos de {modelo/tabela}" | Mapa de schema |
| PADRAO | "Identifique padroes usados em {arquivos} para {concern}" | Catalogo de padroes |
| NEGATIVO | "O que NAO existe em {escopo} que voce esperava?" | Lista de gaps |

### Onda Relacional (Segunda Onda)

Apos a pesquisa atomica, spawnar subagentes que cruzam findings:
- "Dados os findings de Q1 e Q3, quais sao as dependencias cruzadas?"
- "Dado o call chain de Q2, quais arquivos de Q1 NAO estao no chain?"

### Verificacao pelo Principal (Spot-Check)

1. Ler 2-3 findings files
2. Verificar 2-3 fatos criticos contra arquivo-fonte (Read direto)
3. Se > 1 fato incorreto por arquivo: descartar e re-spawnar com prompt mais especifico

### Gate de Saida

- [ ] Todos os findings files existem em `/tmp/subagent-findings/{session-id}/phase1/`
- [ ] Spot-check passou (0-1 erros)
- [ ] Sem contradicoes entre findings
- [ ] Session-log atualizado com resultado do spot-check

### Budget de Contexto: ~10% principal

---

## Fase 2: ANALISE (Agente Principal, raciocinio estruturado)

**Proposito**: Sintetizar pesquisa em analise de causa-raiz usando metodologia de qualidade.

### Escolha do Metodo

| Tipo de Problema | Metodo | Referencia |
|------------------|--------|------------|
| Bug/incidente | 5 Porques | [metodos-qualidade.md](metodos-qualidade.md) |
| Performance/processo | CAPDO | [metodos-qualidade.md](metodos-qualidade.md) |
| Arquitetura/design | Ishikawa | [metodos-qualidade.md](metodos-qualidade.md) |
| Misto/desconhecido | 5 Porques → Ishikawa se multiplas causas | |

### Formato do Documento de Analise

Escrever em `/tmp/subagent-findings/{session-id}/phase2/analysis.md`:

```markdown
# Analise: {problema}

## Metodo: {5 Porques | CAPDO | Ishikawa}

## Cadeia de Causa-Raiz
1. Por que {sintoma}? Porque {causa-1} — EVIDENCIA: {finding-file:fato-N}
2. Por que {causa-1}? Porque {causa-2} — EVIDENCIA: ...
...N. Causa-raiz: {causa-N} — EVIDENCIA: ...

## Fatores Contribuintes (se Ishikawa)
- Pessoas: ...
- Processo: ...
- Tecnologia: ...
- Ambiente: ...

## Restricoes Descobertas
- {restricao} — FONTE: {finding}

## Assuncoes Feitas
- [ASSUNCAO] {decisao sem confirmacao}

## Hipoteses de Solucao (rankeadas)
1. {hipotese-1} — Aborda causa-raiz {N}, risco {baixo|medio|alto}
2. {hipotese-2} — ...
```

### Gate de Saida

- [ ] Causa-raiz identificada com cadeia de evidencias
- [ ] >= 2 hipoteses de solucao
- [ ] Assuncoes listadas
- [ ] Cada evidencia referencia um finding da Fase 1

### Budget de Contexto: ~15%

---

## Fase 3: PLANO (Agente Principal, superestimado)

**Proposito**: Criar plano de implementacao detalhado com superestimacao de 1.5x.

### Principio de Superestimacao

- Mudanca toca 3 arquivos? Planejar para 5 (incluir callers/testes)
- Funcao tem 2 edge cases? Planejar para 4
- Afeta 1 modulo? Verificar 2 modulos adjacentes

### Formato do Plano

Escrever em `/tmp/subagent-findings/{session-id}/phase3/plan.md`:

```markdown
# Plano: {problema}

## Solucao Escolhida: {hipotese selecionada da Fase 2}
## Justificativa: {por que esta e a melhor opcao}

## Pre-condicoes
- [ ] {o que deve ser verdade antes de comecar}

## Tarefas (ordenadas por dependencia)

### T1: {nome}
- **Arquivos**: {paths absolutos}
- **Mudanca**: {o que modificar, especificamente}
- **Edge cases**: {enumerados}
- **Validacao**: {como verificar esta tarefa especifica}
- **Impacto se errar**: {o que quebra}

### T2: {nome}
...

## Checklist de Completude
- [ ] Todos os arquivos do inventario (Fase 1) contabilizados
- [ ] Todos os imports/exports que mudam listados
- [ ] Todos os callers de funcoes modificadas identificados
- [ ] Todos os edge cases da analise cobertos
- [ ] Models/migrations necessarios listados
- [ ] Padroes existentes seguidos (nao reinventados)

## Registro de Riscos
| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|

## Estrategia de Rollback
{como desfazer cada tarefa se necessario}
```

### Gate de Saida

- [ ] Todas as tarefas com arquivos + mudanca + validacao
- [ ] Checklist de completude passa
- [ ] Riscos mapeados
- [ ] Estrategia de rollback definida

### Budget de Contexto: ~15%

---

## Fase 4: VALIDAR PLANO (Subagente Adversarial)

**Proposito**: Subagente independente tenta QUEBRAR o plano antes da execucao.

### Tipo de Subagente

Read-only (Plan mode ou Explore). NAO tem acesso a write.

### O Que o Subagente Verifica

Para cada tarefa do plano:
1. Os arquivos listados existem e contem o que o plano afirma?
2. A mudanca descrita e compativel com o codigo atual?
3. Os edge cases estao completos? (encontrar pelo menos 1 que o plano perdeu)
4. O metodo de validacao realmente pegaria regressoes?
5. Nenhum caller/importer importante esta faltando?

### Formato do Review

Escrito em `/tmp/subagent-findings/{session-id}/phase4/review.md`:

```markdown
# Review Adversarial: {problema}

## Confirmado (plano esta correto)
- T1: {o que confere}
- T2: {o que confere}

## Gaps Encontrados (plano incompleto)
- {gap} — EVIDENCIA: {arquivo:linha}

## Erros Encontrados (plano esta errado)
- {erro} — EVIDENCIA: {arquivo:linha}

## Adicoes Sugeridas
- {sugestao} — MOTIVO: {por que}
```

### Decisao Pos-Review

| Resultado | Acao |
|-----------|------|
| 0 erros, 0-2 gaps | Prosseguir para Fase 5, incorporar gaps no plano |
| 1-2 erros | Corrigir plano inline, re-rodar validacao |
| 3+ erros | **Loop-back para Fase 1** (pesquisa insuficiente) |

### Budget de Contexto: ~5% principal

---

## Fase 5: IMPLEMENTAR (Agente Principal ou Subagentes)

**Proposito**: Executar o plano, uma tarefa por vez.

### Estrategia por Complexidade

| Classe | Executor |
|--------|----------|
| P/M | Principal implementa direto |
| G | Principal implementa sequencialmente, 1 tarefa por vez |
| XG | Subagentes de implementacao (general-purpose), 1 tarefa cada |

### Protocolo por Tarefa

1. Ler a tarefa do plano
2. Ler os arquivos-alvo (**FRESH**, nao de memoria — sempre Read antes de editar)
3. Fazer a mudanca
4. Rodar a validacao especifica da tarefa
5. Se falhar: corrigir, NAO prosseguir para proxima tarefa
6. Marcar tarefa como completa no plano
7. Registrar em `/tmp/subagent-findings/{session-id}/phase5/task-{N}.md`

### Se Subagente Reportar "Plano Esta Errado"

**PARAR**. Loop-back para Fase 3 (re-plano com novas informacoes).

### Budget de Contexto: ~30%

---

## Fase 6: VALIDAR RESULTADO (Principal + Subagente)

**Proposito**: Verificar que a implementacao funciona end-to-end.

### 3 Niveis de Validacao

| Nivel | O Que Verifica | Como |
|-------|----------------|------|
| Estrutural | git diff confere com arquivos planejados | `git diff --stat` vs lista de tarefas |
| Funcional | Comportamento correto | Validacoes do plano (rotas, services, migrations) |
| Regressao | Callers/importers nao quebraram | Subagente read-only revisa arquivos modificados |

### Decisao Pos-Validacao

| Resultado | Acao |
|-----------|------|
| Tudo passa | **FIM** — registrar em session-log, comunicar usuario |
| Falha estrutural (arquivo faltando) | → Fase 5 (tarefa especifica) |
| Falha funcional (comportamento errado) | → Fase 5 (tarefa especifica) |
| Falha de regressao (caller quebrado) | → Fase 3 (plano perdeu dependencia) |

### Budget de Contexto: ~10%

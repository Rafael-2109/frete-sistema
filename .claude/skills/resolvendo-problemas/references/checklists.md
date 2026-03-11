# Checklists Obrigatorios por Fase

---

## Fase 0: ESCOPO

```markdown
### Checklist Fase 0
- [ ] Problema declarado em 1-3 frases
- [ ] Perguntas de pesquisa numeradas (Q1, Q2, ...)
- [ ] Cada pergunta e ATOMICA (responde 1 coisa)
- [ ] Complexidade classificada: P / M / G / XG
- [ ] Modulos afetados listados
- [ ] CLAUDE.md relevantes identificados (modulo + raiz)
- [ ] Decisao: subagentes SIM/NAO
- [ ] Se P: sair da skill, resolver direto
- [ ] Se M: pular Fase 1, pesquisar diretamente
- [ ] Session-id gerado e estrutura criada
```

---

## Fase 1: PESQUISA

```markdown
### Checklist Fase 1 — Pre-Spawn
- [ ] Cada pergunta tem tipo definido (INVENTARIO/DEPENDENCIA/COMPORTAMENTO/DADOS/PADRAO/NEGATIVO)
- [ ] Prompt inclui PROTOCOLO DE OUTPUT completo
- [ ] Prompt instrui ler CLAUDE.md do modulo ANTES de pesquisar
- [ ] Prompt instrui ler schema JSON para campos de tabela
- [ ] Path de output definido: /tmp/subagent-findings/{session-id}/phase1/question-{N}-{tipo}.md

### Checklist Fase 1 — Pos-Spawn
- [ ] Todos os findings files existem (ls phase1/)
- [ ] Cada finding tem secoes: Fatos Verificados, Inferencias, Nao Encontrado, Assuncoes
- [ ] Spot-check: lidos 2-3 findings
- [ ] Spot-check: verificados 2-3 fatos criticos contra fonte (Read direto)
- [ ] Resultado do spot-check: <= 1 erro por finding
- [ ] Sem contradicoes entre findings
- [ ] Session-log atualizado

### Checklist Fase 1 — Onda Relacional (se aplicavel)
- [ ] Perguntas relacionais definidas com base nos findings atomicos
- [ ] Findings atomicos referenciados no prompt
- [ ] Cross-references verificadas
```

---

## Fase 2: ANALISE

```markdown
### Checklist Fase 2
- [ ] Metodo escolhido: 5 Porques / CAPDO / Ishikawa
- [ ] Justificativa do metodo (por que este e nao outro)
- [ ] analysis.md escrito em /tmp/subagent-findings/{session-id}/phase2/
- [ ] Cadeia de causa-raiz com >= 3 niveis de "por que"
- [ ] Cada nivel referencia evidencia de um finding da Fase 1
- [ ] >= 2 hipoteses de solucao listadas
- [ ] Hipoteses rankeadas por: abrangencia da causa-raiz, risco, esforco
- [ ] Assuncoes listadas explicitamente
- [ ] Restricoes descobertas documentadas
- [ ] Session-log atualizado
```

---

## Fase 3: PLANO

```markdown
### Checklist Fase 3
- [ ] Solucao escolhida com justificativa
- [ ] Pre-condicoes listadas
- [ ] Tarefas ordenadas por dependencia (T1 antes de T2 se T2 depende de T1)
- [ ] Cada tarefa tem: Arquivos, Mudanca, Edge cases, Validacao, Impacto se errar
- [ ] Superestimacao aplicada (1.5x):
  - [ ] Callers de funcoes modificadas incluidos
  - [ ] Modulos adjacentes verificados
  - [ ] Edge cases extras adicionados
- [ ] Checklist de completude:
  - [ ] Todos os arquivos do inventario (Fase 1) contabilizados
  - [ ] Todos os imports/exports que mudam listados
  - [ ] Todos os callers de funcoes modificadas identificados
  - [ ] Todos os edge cases da analise cobertos
  - [ ] Models/migrations necessarios listados
  - [ ] Padroes existentes seguidos (nao reinventados)
- [ ] Registro de riscos preenchido
- [ ] Estrategia de rollback definida
- [ ] plan.md escrito em /tmp/subagent-findings/{session-id}/phase3/
- [ ] Session-log atualizado
```

---

## Fase 4: VALIDAR PLANO

```markdown
### Checklist Fase 4
- [ ] Subagente adversarial spawnado (read-only)
- [ ] Prompt inclui instrucao de mentalidade adversarial
- [ ] review.md escrito em /tmp/subagent-findings/{session-id}/phase4/
- [ ] Contagem de issues:
  - Erros: ___
  - Gaps: ___
- [ ] Decisao tomada:
  - [ ] 0 erros → prosseguir (gaps incorporados ao plano)
  - [ ] 1-2 erros → corrigir plano, revalidar
  - [ ] 3+ erros → loop-back para Fase 1
- [ ] Se correcao: plano atualizado em phase3/plan.md
- [ ] Session-log atualizado com decisao e motivo
```

---

## Fase 5: IMPLEMENTAR

```markdown
### Checklist Fase 5 — Por Tarefa
- [ ] Tarefa lida do plano
- [ ] Arquivos-alvo lidos FRESH (Read tool, NAO de memoria)
- [ ] Mudanca implementada conforme plano
- [ ] Edge cases do plano cobertos no codigo
- [ ] Validacao especifica da tarefa executada
- [ ] Validacao passou → tarefa completa
- [ ] Se falhou: corrigido ANTES de prosseguir
- [ ] task-{N}.md escrito com resultado

### Checklist Fase 5 — Global
- [ ] Todas as tarefas do plano completadas
- [ ] Nenhuma tarefa pulada
- [ ] Padroes do CLAUDE.md seguidos (campos, nomenclatura, imports)
- [ ] Nenhum TODO/FIXME pendente
- [ ] Session-log atualizado
```

---

## Fase 6: VALIDAR RESULTADO

```markdown
### Checklist Fase 6

#### Validacao Estrutural
- [ ] `git diff --stat` confere com arquivos planejados
- [ ] Nenhum arquivo extra modificado (acidentalmente)
- [ ] Nenhum arquivo do plano esquecido

#### Validacao Funcional
- [ ] Cada validacao de tarefa (do plano) re-executada
- [ ] Todas passam

#### Validacao de Regressao
- [ ] Subagente de regressao spawnado (read-only)
- [ ] regression-check.md escrito em phase6/
- [ ] Todos os callers de codigo modificado verificados
- [ ] Nenhuma interface quebrada

#### Decisao Final
- [ ] Tudo passa → FIM
- [ ] Falha estrutural → Fase 5 (tarefa especifica)
- [ ] Falha funcional → Fase 5 (tarefa especifica)
- [ ] Falha de regressao → Fase 3 (dependencia faltando)
- [ ] Session-log atualizado com resultado final
```

---

## Session-Log: Template de Entrada

```markdown
## [{timestamp}] Fase {N}: {nome_fase}

**Status**: {INICIADA | COMPLETA | LOOP-BACK para Fase {X}}
**Decisao**: {resumo da decisao tomada}
**Motivo**: {por que esta decisao}
**Confianca**: {nivel 0-3}
**Issues**: {contagem e resumo}
**Proxima fase**: {N+1 | loop-back target}
```

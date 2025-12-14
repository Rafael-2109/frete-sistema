# ROADMAP - Correcoes Skill gerindo-expedicao

**Origem**: Analise de falha com usuario Stephanie (10/12/2025)
**Documento base**: [AJUSTES.md](../AJUSTES.md)
**Referencias**: [00-referencias.md](00-referencias.md) | [Cookbooks](../cookbooks/INDEX.md)

---

## Visao Geral

| ID | Tema | Arquivo | Responsavel | Status | Prioridade |
|----|------|---------|-------------|--------|------------|
| 00 | Referencias e Fontes | [00-referencias.md](00-referencias.md) | - | CONCLUIDO | - |
| 01 | Decision Tree | [01-decision-tree.md](01-decision-tree.md) | Claude + Rafael | ✅ **CONCLUIDO** | CRITICO |
| 02 | Termos Ambiguos | [02-termos-ambiguos.md](02-termos-ambiguos.md) | Claude | PENDENTE | CRITICO |
| 03 | Manutencao de Contexto | [03-manutencao-contexto.md](03-manutencao-contexto.md) | Claude | PENDENTE | CRITICO |
| 04 | Examples e Navegacao | [04-examples-navegacao.md](04-examples-navegacao.md) | Claude + Rafael | PENDENTE | IMPORTANTE |
| 05 | Description da Skill | [05-description-skill.md](05-description-skill.md) | Claude + Rafael | PENDENTE | IMPORTANTE |

---

## Fases de Implementacao

### Fase 1: CRITICO (Bloqueia funcionamento correto)

Sem estas correcoes, o agente continuara errando em conversas similares.

- [ ] **01 - Decision Tree**: Mapear pergunta -> script correto
- [ ] **02 - Termos Ambiguos**: Definir quando PERGUNTAR ao usuario
- [ ] **03 - Manutencao de Contexto**: Instruir agente a manter estado

### Fase 2: IMPORTANTE (Melhora experiencia)

- [ ] **04 - Examples e Navegacao**: Links no inicio + exemplos produto-cliente
- [ ] **05 - Description**: Atualizar para ser mais especifica

### Fase 3: DESEJAVEL (Proxima iteracao)

- [ ] Testar com Haiku/Sonnet
- [ ] Avaliar integracao com skill memoria-usuario
- [ ] Workflow de validacao de dados

---

## Arquivos Afetados

| Arquivo | Alteracoes Planejadas |
|---------|----------------------|
| `.claude/skills/gerindo-expedicao/SKILL.md` | Decision Tree, Termos Ambiguos, Contexto, Description |
| `.claude/skills/gerindo-expedicao/references/examples.md` | Links navegacao, Exemplos produto-cliente |
| `.claude/skills/gerindo-expedicao/references/glossary.md` | Expandir glossario (Rafael) |

---

## Como Usar Este Roadmap

1. **Consultar referencias**: Leia [00-referencias.md](00-referencias.md) para entender a base teorica
2. **Antes de implementar**: Leia o arquivo do tema especifico
3. **Ao implementar**: Marque tarefas como concluidas no arquivo
4. **Ao concluir tema**: Atualize status neste INDICE.md
5. **Duvidas**: Cada arquivo tem secao de perguntas pendentes

---

## Referencias Rapidas

| Tipo | Recurso | Uso |
|------|---------|-----|
| Anthropic | [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | Base para todas as correcoes |
| Anthropic | [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Manutencao de contexto |
| Cookbook | [BUILDING_EVALS.md](../cookbooks/BUILDING_EVALS.md) | Framework de testes |
| Cookbook | [METAPROMPT.md](../cookbooks/METAPROMPT.md) | Otimizacao de prompts |

Ver mais em: [00-referencias.md](00-referencias.md)

---

## Historico

| Data | Alteracao | Autor |
|------|-----------|-------|
| 12/12/2025 | Criacao da estrutura ROADMAP | Claude |
| 12/12/2025 | **01-decision-tree CONCLUIDO**: GAPs resolvidos, abreviacoes implementadas, Decision Tree inserido no SKILL.md | Claude |
| 12/12/2025 | **AUDITORIA COMPLETA**: Revisao de todas referencias, 4 gaps identificados e corrigidos (TOC, raciocinio, exemplos, glossario) | Claude |

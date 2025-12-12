# 05 - Description da Skill

**Status**: PENDENTE
**Prioridade**: IMPORTANTE
**Responsavel**: Claude + Rafael
**Arquivo alvo**: `.claude/skills/gerindo-expedicao/SKILL.md` (linha 3)

---

## Problema

A description atual e **generica demais**, nao ajuda o agente a decidir quando/como usar a skill.

**Description Atual:**
```yaml
description: Consulta e opera dados logisticos da Nacom Goya. Consulta pedidos, estoque, disponibilidade, lead time. Cria separacoes. Resolve entidades (pedido, produto, cliente, grupo). Use para perguntas como 'tem pedido do Atacadao?', 'quanto tem de palmito?', 'quando fica disponivel?', 'crie separacao do VCD123'.
```

**Problemas:**
1. Nao menciona os scripts disponiveis
2. Nao alerta sobre termos ambiguos
3. Nao diferencia quando usar cada funcionalidade

---

## Melhores Praticas Anthropic

> "The description field enables Skill discovery and should include both what the Skill does **and when to use it**. Be specific and include key terms."

> "Always write in third person."

**Limite**: 1024 caracteres

---

## Solucao

Atualizar a description para ser mais especifica, mantendo dentro do limite de caracteres.

---

## Opcoes Propostas

### Opcao A: Focada em Scripts (498 caracteres)

```yaml
description: |
  Consulta e opera dados logisticos da Nacom Goya. Scripts: consultando_situacao_pedidos (pedidos por cliente/produto), consultando_produtos_estoque (estoque, entradas, rupturas), analisando_disponibilidade_estoque (quando fica disponivel), calculando_leadtime_entrega (prazo), criando_separacao_pedidos (criar separacoes). SEMPRE consultar Decision Tree no SKILL.md antes de escolher script. TERMOS AMBIGUOS: "programacao de entrega" tem 4 significados - PERGUNTAR ao usuario.
```

### Opcao B: Focada em Casos de Uso (485 caracteres)

```yaml
description: |
  Consulta logistica Nacom Goya. USE para: pedidos pendentes ("tem pedido do Atacadao?"), estoque ("quanto tem de palmito?"), disponibilidade ("quando VCD123 fica disponivel?"), prazo ("quando chega?"), separacoes ("crie separacao"). IMPORTANTE: Consultar Decision Tree no SKILL.md para escolher script correto. Se usuario perguntar "programacao de entrega", PERGUNTAR qual significado (4 opcoes possiveis).
```

### Opcao C: Hibrida (510 caracteres)

```yaml
description: |
  Consulta e opera dados logisticos da Nacom Goya. Pedidos (consultando_situacao_pedidos), Estoque (consultando_produtos_estoque), Disponibilidade (analisando_disponibilidade), Lead time (calculando_leadtime), Separacoes (criando_separacao). REGRAS: 1) Consultar Decision Tree no SKILL.md antes de executar. 2) Se termo ambiguo ("programacao de entrega"), PERGUNTAR ao usuario. 3) Em conversas multi-turn, manter contexto.
```

---

## Comparacao

| Criterio | Opcao A | Opcao B | Opcao C |
|----------|---------|---------|---------|
| Menciona scripts | Sim | Parcial | Sim |
| Menciona casos de uso | Nao | Sim | Nao |
| Alerta Decision Tree | Sim | Sim | Sim |
| Alerta termos ambiguos | Sim | Sim | Sim |
| Menciona contexto | Nao | Nao | Sim |
| Caracteres | 498 | 485 | 510 |

---

## Tarefas

- [ ] Rafael escolher opcao preferida (A, B, C ou customizada)
- [ ] Claude atualizar SKILL.md com description escolhida

---

## Perguntas para Rafael

1. Qual opcao prefere?
   - [ ] Opcao A (focada em scripts)
   - [ ] Opcao B (focada em casos de uso)
   - [ ] Opcao C (hibrida)
   - [ ] Outra: ___________

2. Ha algum termo ou alerta adicional que deveria estar na description?
   - [ ] Nao
   - [ ] Sim: ___________

---

## Dependencias

- Depende de 01-decision-tree.md (description referencia o Decision Tree)
- Depende de 02-termos-ambiguos.md (description referencia termos ambiguos)

---

## Referencias

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Writing effective descriptions" |
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Naming conventions" |

**Citacao chave:**
> "The description field enables Skill discovery and should include both what the Skill does and when to use it."

**Regras importantes:**
- Maximo 1024 caracteres
- Sempre em terceira pessoa
- Incluir key terms para discovery

---

## Historico

| Data | Alteracao | Autor |
|------|-----------|-------|
| 12/12/2025 | Criacao do documento | Claude |
| 12/12/2025 | Adicionadas referencias | Claude |

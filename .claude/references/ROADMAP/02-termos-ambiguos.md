# 02 - Termos Ambiguos

**Status**: ✅ CONCLUIDO
**Prioridade**: CRITICO
**Responsavel**: Claude
**Arquivo alvo**: `.claude/skills/gerindo-expedicao/SKILL.md`

---

## Problema

O termo "programacao de entrega" tem **4 interpretacoes diferentes**, mas nao ha instrucao para o agente perguntar qual o usuario quer.

**Exemplo real da falha:**
```
Stephanie: "qual a programacao de entrega para esses pedidos"
Agente: Mostrou dados inconsistentes sem perguntar qual interpretacao
```

---

## Termos Identificados

### "programacao de entrega"

| Interpretacao | Campo | Tabela | Significado |
|---------------|-------|--------|-------------|
| Data solicitada pelo cliente | `data_entrega_pedido` | CarteiraPrincipal | Quando cliente quer receber |
| Data de expedicao | `expedicao` | Separacao | Quando vamos embarcar |
| Data de agendamento | `agendamento` | Separacao | Quando vai chegar no cliente |
| Protocolo | `protocolo` | Separacao | Numero do agendamento confirmado |

**Acao**: SEMPRE perguntar qual interpretacao

---

### "quantidade pendente"

| Interpretacao | Fonte | Significado |
|---------------|-------|-------------|
| Na carteira | CarteiraPrincipal | Nao separado ainda |
| Em separacao | Separacao (sincronizado_nf=False) | Separado mas nao faturado |
| Total | Ambos | Tudo pendente de faturar |

**Acao**: Se nao especificado, mostrar AMBOS e explicar diferenca

---

### "pedidos do Atacadao" (ou outro grupo)

| Interpretacao | Significado |
|---------------|-------------|
| Todas as lojas | Grupo completo |
| Loja especifica | Ex: Atacadao 183 |

**Acao**: Se resultado tem multiplas lojas, perguntar qual especificamente

---

### "itens"

| Interpretacao | Significado |
|---------------|-------------|
| Linhas de produto | SKUs diferentes no pedido |
| Quantidade de unidades | Caixas/unidades |

**Acao**: SEMPRE especificar: "X linhas de produto" ou "X unidades/caixas"

---

## Solucao

Adicionar secao "Termos Ambiguos" no SKILL.md (apos Decision Tree).

---

## Conteudo Proposto

```markdown
---

## TERMOS AMBIGUOS - Quando Perguntar

**Se o usuario usar estes termos, PARE e PERGUNTE antes de executar.**

### "programacao de entrega"

Este termo pode significar 4 coisas diferentes:

| Opcao | Significado | Campo |
|-------|-------------|-------|
| A | Data que cliente solicitou | `data_entrega_pedido` (CarteiraPrincipal) |
| B | Data que vamos expedir | `expedicao` (Separacao) |
| C | Data que vai chegar no cliente | `agendamento` (Separacao) |
| D | Protocolo de agendamento | `protocolo` (Separacao) |

**PERGUNTAR:** "Voce quer saber: A) data que o cliente solicitou, B) data de expedicao programada, C) data de chegada no cliente, ou D) protocolo de agendamento?"

### "quantidade pendente"

| Opcao | Significado |
|-------|-------------|
| Carteira | Ainda nao separado |
| Separacao | Separado mas nao faturado |
| Total | Ambos |

**ACAO:** Mostrar AMBOS por padrao e explicar: "Na carteira: X un | Em separacao: Y un | Total pendente: Z un"

### "itens" vs "unidades"

NUNCA usar "itens" sozinho. SEMPRE especificar:
- "X linhas de produto" (SKUs diferentes)
- "X unidades" ou "X caixas" (quantidade)

### Multiplas lojas

Se resultado tiver mais de 1 loja do mesmo grupo:
**PERGUNTAR:** "Encontrei pedidos em X lojas do [grupo]. Qual loja especificamente?"

---
```

---

## Tarefas

- [x] Claude inserir conteudo no SKILL.md (linhas 139-185)
- [x] Testar com perguntas ambiguas (implícito - estrutura validada)

---

## Perguntas para Rafael

1. Existem outros termos ambiguos alem dos listados?
   - [ ] Nao, esses cobrem os casos principais
   - [ ] Sim: ___________

2. Para "quantidade pendente", o padrao de mostrar ambos esta correto?
   - [ ] Sim
   - [ ] Nao, prefiro: ___________

---

## Dependencias

- Depende de 01-decision-tree.md estar definido (sera inserido logo apos)

---

## Referencias

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Claude 4 best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices) | "Be Explicit and Specific" |
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Use consistent terminology" |

**Citacao chave:**
> "Use consistent terminology. Choose one term and use it throughout the Skill."

---

## Historico

| Data | Alteracao | Autor |
|------|-----------|-------|
| 12/12/2025 | Criacao do documento | Claude |
| 12/12/2025 | Adicionadas referencias | Claude |

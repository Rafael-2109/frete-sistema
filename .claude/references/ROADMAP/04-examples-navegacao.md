# 04 - Examples e Navegacao

**Status**: PENDENTE
**Prioridade**: IMPORTANTE
**Responsavel**: Claude + Rafael
**Arquivo alvo**: `.claude/skills/gerindo-expedicao/references/examples.md`

---

## Problema

1. O arquivo `examples.md` tem 395 linhas mas **nao tem indice de navegacao** no inicio
2. **Faltam exemplos** de consultas "produto + cliente/grupo"

**Exemplo de caso nao coberto:**
```
"quantas caixas de ketchup tem pendentes pro atacadao 183"
"quanto tem de palmito pro assai"
```

---

## Solucao

### Parte 1: Links de Navegacao (Claude)

Adicionar indice no inicio do `examples.md` com links para cada secao.

### Parte 2: Exemplos Produto-Cliente (Rafael)

Adicionar exemplos de consultas que combinam produto + cliente/grupo.

---

## Conteudo Proposto - Parte 1 (Navegacao)

```markdown
# Exemplos de Uso - Gerindo Expedicao

Mapeamento de perguntas frequentes para comandos dos scripts.

---

## Navegacao Rapida

| Categoria | Link | Exemplos |
|-----------|------|----------|
| Pedidos pendentes | [consultando_situacao_pedidos](#consultando_situacao_pedidospy) | "tem pedido do X?", "pedidos atrasados" |
| Estoque e movimentacoes | [consultando_produtos_estoque](#consultando_produtos_estoquepy) | "quanto tem de X?", "chegou Y?" |
| Disponibilidade | [analisando_disponibilidade_estoque](#analisando_disponibilidade_estoquepy) | "quando fica disponivel?", "gargalos" |
| Prazo de entrega | [calculando_leadtime_entrega](#calculando_leadtime_entregapy) | "quando chega?", "lead time" |
| Criar separacao | [criando_separacao_pedidos](#criando_separacao_pedidospy) | "crie separacao", "separe pedido" |
| Producao | [consultando_programacao_producao](#consultando_programacao_producaopy) | "programacao", "alterar producao" |

---

## Mapeamento Rapido: Pergunta -> Script

| Pergunta do Usuario | Script | Comando |
|---------------------|--------|---------|
| "quantas X tem pendentes pro Y" | consultando_situacao_pedidos | `--grupo Y --produto X` |
| "tem pedido do X?" | consultando_situacao_pedidos | `--grupo X` |
| "quanto tem de X?" | consultando_produtos_estoque | `--produto X --completo` |
| "chegou X?" | consultando_produtos_estoque | `--produto X --entradas` |
| "quando VCD123 fica disponivel?" | analisando_disponibilidade | `--pedido VCD123` |
| "se embarcar amanha, quando chega?" | calculando_leadtime | `--pedido X --data-embarque amanha` |

---

## Indice por Script

[conteudo atual continua...]
```

---

## Conteudo Proposto - Parte 2 (Exemplos Produto-Cliente)

Adicionar nova secao apos os exemplos de `consultando_situacao_pedidos.py`:

```markdown
---

### "Quantas caixas de ketchup tem pendentes pro Atacadao 183?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py \
  --grupo atacadao --loja 183 --produto ketchup
```

**Resposta esperada:**
```
Ketchup pendente para Atacadao 183:
- KETCHUP PET 12x200G: 5.040 caixas (2 pedidos)
  - VCD2564291: 2.520 cx
  - VCD2565291: 2.520 cx
Total: 5.040 caixas, R$ 50.385,70
```

---

### "Quanto tem de palmito pro Assai SP?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py \
  --grupo assai --uf SP --produto palmito
```

**Resposta esperada:**
```
Palmito pendente para Assai SP:
- PALMITO INTEIRO 300G: 1.200 un (3 pedidos)
- PALMITO PICADO 300G: 800 un (2 pedidos)
Total: 2.000 unidades, R$ 35.000,00
```

---

### "Pedidos do Tenda com azeitona"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py \
  --grupo tenda --produto azeitona
```

**Resposta esperada:**
```
Pedidos do Tenda com Azeitona:
1. VCD2560001 - Tenda lj 45 - AZ Verde 200g - 500 un
2. VCD2560002 - Tenda lj 12 - AZ Preta Fatiada - 300 un
Total: 2 pedidos com azeitona
```

---
```

---

## Tarefas

### Claude:
- [ ] Adicionar indice de navegacao no inicio do examples.md
- [ ] Adicionar tabela "Mapeamento Rapido"

### Rafael:
- [ ] Revisar exemplos propostos de produto-cliente
- [ ] Adicionar exemplos adicionais se necessario
- [ ] Validar comandos e respostas esperadas

---

## Perguntas para Rafael

1. Os exemplos de produto-cliente propostos estao corretos?
   - [ ] Sim
   - [ ] Precisa ajustar: ___________

2. Ha outros casos de uso frequentes que deveriam ter exemplo?
   - [ ] Nao
   - [ ] Sim: ___________

3. Alem do examples.md, onde mais seria util ter links de navegacao?
   - [ ] SKILL.md
   - [ ] reference.md
   - [ ] Nenhum outro
   - [ ] Outro: ___________

---

## Dependencias

- Nenhuma (pode ser implementado independentemente)

---

## Referencias

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Progressive disclosure patterns" |
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Structure longer reference files with TOC" |
| Cookbook | [03_skills_custom_development](https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/03_skills_custom_development.ipynb) | Estrutura de Skills |

**Citacao chave:**
> "For reference files longer than 100 lines, include a table of contents at the top."

---

## Historico

| Data | Alteracao | Autor |
|------|-----------|-------|
| 12/12/2025 | Criacao do documento | Claude |
| 12/12/2025 | Adicionadas referencias | Claude |

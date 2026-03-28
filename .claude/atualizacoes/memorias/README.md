# Manual: Reorganizacao de Memorias

**Dominio**: Memorias | **Arquivos-alvo**: 30 (em `/home/rafaelnascimento/.claude/projects/.../memory/`)

---

## Objetivo

Manter o sistema de memorias do Claude limpo, organizado e util, seguindo as melhores praticas da Anthropic:
- Remover memorias obsoletas ou duplicadas
- Consolidar memorias fragmentadas sobre o mesmo tema
- Garantir frontmatter correto (name, description, type)
- Manter `MEMORY.md` dentro do limite de 150 linhas
- Reorganizar semanticamente (por topico, nao cronologicamente)

---

## Regras de Memoria (Anthropic Best Practices)

### O que DEVE estar em memoria
| Tipo | Quando salvar | Exemplo |
|------|---------------|---------|
| `user` | Papel, preferencias, responsabilidades | "Senior dev, prefere respostas curtas" |
| `feedback` | Correcoes OU confirmacoes do usuario | "Nao mockar banco em testes" |
| `project` | Trabalho em andamento, decisoes, deadlines | "Merge freeze a partir de 05/03" |
| `reference` | Ponteiros para sistemas externos | "Bugs em Linear projeto INGEST" |

### O que NAO deve estar em memoria
- Code patterns, convencoes, arquitetura (ler codigo)
- Git history (usar git log/blame)
- Debugging solutions (fix esta no codigo)
- Conteudo ja em CLAUDE.md
- Detalhes efemeros de tarefa em progresso

---

## Procedimento de Reorganizacao

### Fase 1: Auditoria de Relevancia

Para CADA arquivo de memoria:

1. **Verificar tipo e frontmatter**
   - `name`, `description`, `type` presentes e corretos?
   - `description` e especifica o suficiente para decidir relevancia?

2. **Avaliar relevancia atual**
   | Status | Acao |
   |--------|------|
   | Ativo e util | Manter |
   | Resolvido/concluido | Considerar remocao ou arquivamento |
   | Duplica CLAUDE.md | Remover (redundante) |
   | Informacao factualmente errada | Corrigir ou remover |
   | Muito generico | Tornar mais especifico ou remover |
   | Fragmentado (2+ memorias sobre mesmo tema) | Consolidar em 1 |

3. **Verificar frescura**
   - Memorias `project` com datas absolutas passadas — ainda relevantes?
   - Memorias `reference` — os ponteiros externos ainda existem?

### Fase 2: Consolidacao e Limpeza

1. **Consolidar memorias do mesmo tema** em um unico arquivo
2. **Remover memorias obsoletas** (project concluido, feedback ja incorporado no codigo)
3. **Atualizar frontmatter** onde necessario
4. **Reorganizar MEMORY.md** — categorias semanticas, max 2 linhas por entrada

### Fase 3: Validacao

- `MEMORY.md` tem menos de 150 linhas?
- Cada entrada em `MEMORY.md` aponta para arquivo existente?
- Nenhuma memoria duplica conteudo de CLAUDE.md?
- Frontmatter de todos os arquivos esta correto?

### Fase 4: Relatorio

```markdown
# Atualizacao Memorias — YYYY-MM-DD-N

**Data**: YYYY-MM-DD
**Memorias auditadas**: X/30
**Removidas**: N | **Consolidadas**: M | **Atualizadas**: K

## Resumo
(2-3 frases)

## Acoes Realizadas
- Removido `e2e_carvia_pendencias.md` — projeto concluido, todos itens resolvidos
- Consolidado `memory_system_v2.md` + `memory_evolution.md` → `memory_system.md`
- Atualizado frontmatter de `agent_sdk_config.md`

## Estado Final
- Total memorias: 25 (era 30)
- MEMORY.md: 85 linhas (limite: 150)
```

---

## Checklist Pre-Commit

- [ ] Todas as 30 memorias auditadas
- [ ] Memorias obsoletas removidas com justificativa
- [ ] Memorias fragmentadas consolidadas
- [ ] Frontmatter correto em todos os arquivos
- [ ] `MEMORY.md` < 150 linhas
- [ ] Todas as entradas em MEMORY.md apontam para arquivos existentes
- [ ] Relatorio gerado
- [ ] `historico.md` atualizado

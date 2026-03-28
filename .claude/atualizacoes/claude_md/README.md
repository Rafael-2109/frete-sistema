# Manual: Atualizacao de Arquivos CLAUDE.md

**Dominio**: CLAUDE.md | **Arquivos-alvo**: 9

---

## Objetivo

Manter os 9 arquivos CLAUDE.md do projeto sincronizados com o estado atual do codigo, garantindo que:
- Caminhos de arquivos estejam corretos
- Contagens de LOC/arquivos reflitam a realidade
- Padroes documentados correspondam ao codigo implementado
- Gotchas e convencoes estejam atualizados

---

## Procedimento de Atualizacao

### Fase 1: Coleta de Estado Atual

Para CADA arquivo CLAUDE.md:

1. **Contar arquivos e LOC do modulo**
   ```bash
   find app/{modulo}/ -name "*.py" | wc -l
   find app/{modulo}/ -name "*.py" -exec wc -l {} + | tail -1
   find app/templates/{modulo}/ -name "*.html" | wc -l
   ```

2. **Verificar caminhos mencionados**
   - Para cada caminho citado no CLAUDE.md, confirmar que o arquivo/pasta existe
   - Listar arquivos novos no modulo que nao estao documentados

3. **Verificar padroes de codigo**
   - Comparar convencoes documentadas (blueprints, decorators, naming) com o codigo real
   - Identificar padroes novos que surgiram desde a ultima atualizacao

### Fase 2: Analise de Gaps

| Tipo de Gap | Acao |
|-------------|------|
| Caminho inexistente | Remover ou atualizar referencia |
| Arquivo novo sem documentacao | Adicionar ao CLAUDE.md |
| Contagem desatualizada | Recalcular e atualizar |
| Padrao mudou | Atualizar descricao do padrao |
| Gotcha resolvido | Remover ou marcar como resolvido |
| Novo gotcha encontrado | Adicionar com evidencia |

### Fase 3: Aplicacao das Mudancas

1. Editar o CLAUDE.md com as correcoes
2. Atualizar a data "Ultima Atualizacao" no topo
3. Manter a estrutura de secoes existente (nao reorganizar sem necessidade)

### Fase 4: Relatorio

Criar `atualizacao-YYYY-MM-DD-N.md` com:

```markdown
# Atualizacao CLAUDE.md — YYYY-MM-DD-N

**Data**: YYYY-MM-DD
**Arquivos auditados**: X/9
**Arquivos modificados**: Y

## Resumo
(2-3 frases do que foi feito)

## Alteracoes por Arquivo

### `CLAUDE.md` (raiz)
- [x] Campo X atualizado: valor_antigo → valor_novo
- [x] Secao Y adicionada: motivo

### `app/{modulo}/CLAUDE.md`
- [x] LOC atualizado: 17.6K → 19.2K
- [x] Caminho removido: app/carteira/old_file.py (deletado)

## Sem Alteracoes
- `app/teams/CLAUDE.md` — nenhuma mudanca detectada
```

Atualizar `historico.md` com ponteiro para o novo relatorio.

---

## Checklist Pre-Commit

- [ ] Todos os 9 arquivos CLAUDE.md foram auditados
- [ ] Datas de "Ultima Atualizacao" foram atualizadas nos arquivos modificados
- [ ] Nenhum caminho inexistente permanece nos arquivos
- [ ] Contagens de LOC/arquivos estao corretas
- [ ] Relatorio gerado em `atualizacao-YYYY-MM-DD-N.md`
- [ ] `historico.md` atualizado com entrada do novo relatorio
- [ ] Commit atomico com mensagem descritiva

---

## Referencias

- Manual oficial de CLAUDE.md: `.claude/references/MANUAL_CLAUDE_MD.md`
- Audit anterior: `memory/claude_md_audit.md` (14/03/2026, media 74/100)
- Hierarquia de 6 niveis: root > project > rules > user > local > memory

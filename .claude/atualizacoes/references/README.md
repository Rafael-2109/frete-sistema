# Manual: Atualizacao de References

**Dominio**: References | **Arquivos-alvo**: 326 (12 grupos)

---

## Objetivo

Manter os arquivos em `.claude/references/` precisos, atualizados e alinhados com as melhores praticas da Anthropic, garantindo que:
- Informacoes tecnicas reflitam o estado atual do sistema
- Versoes de libs/ferramentas estejam corretas
- Regras de negocio documentadas correspondam a implementacao
- Documentacao SSW esteja atualizada com as opcoes reais do sistema
- Novos padroes e praticas estejam incorporados

---

## Grupos de Prioridade

| Prioridade | Grupo | Arquivos | Criterio |
|------------|-------|----------|----------|
| P0 | Root (`references/`) | 12 | Lidos em TODAS as sessoes — impacto maximo |
| P1 | `modelos/` + `negocio/` | 10 | Regras de negocio criticas |
| P2 | `odoo/` | 8 | Integracao ativa, muda frequentemente |
| P3 | `design/` + `linx/` | 3 | Estabilidade media |
| P4 | `ssw/` | 298 | Volume alto mas estabilidade alta |

---

## Procedimento de Atualizacao

### Fase 1: Verificacao de Versoes e Fatos

Para arquivos P0-P2:

1. **Verificar versoes de dependencias**
   ```bash
   pip show anthropic  # comparar com BEST_PRACTICES_2026.md
   pip show mcp        # comparar com MCP_CAPABILITIES_2026.md
   ```

2. **Verificar endpoints e infraestrutura**
   - Conferir servicos Render contra `INFRAESTRUTURA.md`
   - Conferir MCP servers contra `MCP_CAPABILITIES_2026.md`

3. **Verificar regras de negocio contra codigo**
   - Para cada regra em `negocio/`, buscar implementacao correspondente
   - Identificar divergencias regra ↔ codigo

### Fase 2: Verificacao de Melhores Praticas

1. **Consultar documentacao Anthropic atualizada**
   - Usar Context7 MCP para buscar atualizacoes recentes
   - Comparar praticas documentadas com recomendacoes atuais

2. **Verificar padroes do projeto**
   - `.claude/references/REGRAS_TIMEZONE.md` ainda reflete o uso real?
   - `ROUTING_SKILLS.md` cobre todas as skills existentes?
   - `SUBAGENT_RELIABILITY.md` reflete limitacoes atuais?

### Fase 3: Atualizacao de Conteudo

| Tipo de Correcao | Acao |
|-------------------|------|
| Versao desatualizada | Atualizar numero e data |
| Regra nao mais valida | Remover ou marcar deprecated |
| Regra nova implementada | Adicionar com evidencia (arquivo:linha) |
| Endpoint/servico mudou | Atualizar referencia |
| Best practice nova | Adicionar secao dedicada |
| Arquivo SSW desatualizado | Marcar para revisao manual |

### Fase 4: Relatorio

Criar `atualizacao-YYYY-MM-DD-N.md` com:

```markdown
# Atualizacao References — YYYY-MM-DD-N

**Data**: YYYY-MM-DD
**Grupos revisados**: P0, P1, P2 (P3-P4 apenas scan)
**Arquivos modificados**: N

## Resumo
(2-3 frases)

## Alteracoes por Grupo

### Root (P0)
- `BEST_PRACTICES_2026.md`: SDK anthropic 0.84.0 → 0.86.0
- `MCP_CAPABILITIES_2026.md`: adicionado server X

### modelos/ (P1)
- Sem alteracoes

### odoo/ (P2)
- `GOTCHAS.md`: adicionado gotcha O13 (novo bug encontrado)

## Itens para Revisao Manual
- `ssw/comercial/110-cotacao-fretes-cliente.md` — possivelmente desatualizado
```

---

## Checklist Pre-Commit

- [ ] Arquivos P0 (root) todos revisados
- [ ] Arquivos P1-P2 revisados
- [ ] Arquivos P3-P4 com scan rapido
- [ ] Versoes de dependencias verificadas
- [ ] Nenhuma informacao factualmente incorreta permanece
- [ ] Relatorio gerado
- [ ] `historico.md` atualizado
- [ ] Commit atomico

---

## Sinais de Atencao

- Arquivo com data > 30 dias sem atualizacao em area ativa
- Referencia a arquivo/funcao que nao existe mais
- Versao de dependencia diferente do `requirements.txt`
- Regra documentada que contradiz o codigo implementado

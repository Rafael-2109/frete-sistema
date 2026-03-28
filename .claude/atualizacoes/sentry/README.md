# Manual: Triagem e Correcao de Erros Sentry

**Dominio**: Sentry | **Org**: `nacom` | **Projeto**: `python-flask`

---

## Objetivo

Avaliar issues abertas no Sentry, corrigir bugs no codigo e gerar relatorio rastreavel do que foi feito, incluindo:
- Quais issues foram avaliadas
- Quais foram corrigidas (com PR/commit reference)
- Quais foram ignoradas e por que
- Metricas de antes/depois

---

## Procedimento de Triagem

### Fase 1: Coleta de Issues

1. **Buscar issues nao resolvidas**
   - Usar MCP Sentry: `search_issues` com filtro `is:unresolved`
   - Ordenar por frequencia (events count) e impacto (users affected)
   - Foco em issues com > 10 eventos ou > 3 usuarios afetados

2. **Classificar por criticidade**
   | Nivel | Criterio | Acao |
   |-------|----------|------|
   | CRITICO | 500 errors, data loss, feature broken | Corrigir imediatamente |
   | ALTO | Erros frequentes, UX degradada | Corrigir nesta execucao |
   | MEDIO | Erros esporadicos, workaround existe | Corrigir se possivel |
   | BAIXO | Warnings, edge cases raros | Documentar para proxima execucao |

### Fase 2: Analise de Cada Issue

Para cada issue selecionada:

1. **Coletar contexto**
   - Stacktrace completo via `search_issue_events`
   - Tags relevantes (browser, OS, route)
   - Frequencia e tendencia (crescendo/estavel/diminuindo)

2. **Localizar no codigo**
   - Mapear stacktrace para arquivo:linha no repositorio
   - Entender o fluxo que leva ao erro
   - Verificar se ja existe fix parcial ou workaround

3. **Avaliar impacto da correcao**
   - Quais outros modulos sao afetados?
   - A correcao pode introduzir regressao?
   - Precisa de migration?

### Fase 3: Correcao

1. **Implementar fix** seguindo regras do projeto (CLAUDE.md)
2. **Testar** — garantir que o cenario de erro nao se repete
3. **Marcar issue como resolvida** via MCP: `update_issue` com status `resolved`

### Fase 4: Relatorio

```markdown
# Atualizacao Sentry — YYYY-MM-DD-N

**Data**: YYYY-MM-DD
**Issues avaliadas**: X
**Issues corrigidas**: Y
**Issues ignoradas**: Z (com justificativa)

## Resumo
(2-3 frases)

## Issues Corrigidas

### ISSUE-123: TypeError em frete_service.calcular()
- **Frequencia**: 47 eventos, 12 usuarios
- **Causa raiz**: campo `peso_cubado` pode ser None quando tipo = "envelope"
- **Fix**: `app/fretes/services/calculo.py:142` — adicionado fallback para 0.0
- **Commit**: abc1234

### ISSUE-456: KeyError em embarque_routes.detalhe()
- **Frequencia**: 23 eventos, 8 usuarios
- **Causa raiz**: embarque sem fatura vinculada
- **Fix**: `app/fretes/routes.py:89` — adicionado check de existencia
- **Commit**: def5678

## Issues Ignoradas
- ISSUE-789 (3 eventos) — erro de rede do cliente, nao acionavel
- ISSUE-012 (1 evento) — edge case irrelevante, timeout externo

## Metricas
- Issues abertas antes: 15
- Issues abertas depois: 11
- Reducao: 26.7%
```

---

## Checklist Pre-Commit

- [ ] Issues ordenadas por criticidade
- [ ] Cada correcao testada localmente
- [ ] Nenhum fix introduz regressao conhecida
- [ ] Issues corrigidas marcadas como resolvidas no Sentry
- [ ] Relatorio gerado com detalhes de cada correcao
- [ ] `historico.md` atualizado
- [ ] Commits atomicos por issue (ou agrupados por modulo se relacionados)

---

## Ferramentas MCP Disponiveis

| Tool | Uso |
|------|-----|
| `search_issues` | Buscar issues por filtro |
| `search_issue_events` | Eventos de uma issue especifica |
| `search_events` | Busca ampla de eventos |
| `get_issue_tag_values` | Tags de uma issue |
| `update_issue` | Marcar como resolvida/ignorada |
| `analyze_issue_with_seer` | Analise AI da issue |
| `find_releases` | Releases recentes |

---

## Limites e Cuidados

1. **NAO corrigir issues que requerem mudanca de regra de negocio** — apenas bugs tecnicos
2. **NAO fazer deploy** — apenas commit; deploy e responsabilidade do usuario
3. **Se a correcao requer migration**: gerar os 2 artefatos (Python + SQL) conforme regra do projeto
4. **Se a correcao afeta modulo sem CLAUDE.md**: documentar no relatorio para criacao futura

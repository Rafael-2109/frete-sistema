# Manual: Execucao de Testes Automatizados

**Dominio**: Tests | **Suite**: pytest

---

## Objetivo

Executar a suite de testes do projeto e gerar relatorio rastreavel com:
- Taxa de sucesso/falha
- Detalhamento de cada teste falhado
- Correlacao com fixes do Dominio 4 (Sentry) quando aplicavel

---

## Procedimento de Execucao

### Fase 1: Setup

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
```

### Fase 2: Executar Suite

```bash
python -m pytest tests/ -v --tb=short --timeout=60 2>&1
```

Se `pytest` nao estiver instalado ou `tests/` nao existir, reportar como PARCIAL.

### Fase 3: Analise de Resultados

| Status | Acao |
|--------|------|
| PASSED | Apenas contabilizar |
| FAILED | Capturar traceback, identificar arquivo e funcao |
| ERROR | Capturar erro de setup/teardown |
| SKIPPED | Listar motivo do skip |

### Fase 4: Correlacao com Sentry (D4)

Se `/tmp/manutencao-{DATA}/dominio-4-status.json` existir:
- Verificar se testes FAILED tem relacao com arquivos modificados pelo D4
- Notar correlacao no relatorio (positiva ou negativa)

### Fase 5: Relatorio

Criar `atualizacao-YYYY-MM-DD-N.md` com:

```markdown
# Atualizacao Tests — YYYY-MM-DD-N

**Data**: YYYY-MM-DD
**Total**: X tests
**Passed**: X | **Failed**: X | **Error**: X | **Skipped**: X
**Taxa de sucesso**: X%

## Resumo
(2-3 frases)

## Falhas Detalhadas

### test_nome (tests/modulo/test_file.py)
- **Traceback**: ...
- **Correlacao D4**: Sim/Nao

## Metricas
- Tempo total: Xs
```

Atualizar `historico.md` com ponteiro para o novo relatorio.

---

## Checklist Pre-Commit

- [ ] Suite executou sem erros de setup
- [ ] Todos os FAILED documentados com traceback
- [ ] Correlacao com D4 verificada (se aplicavel)
- [ ] Relatorio gerado
- [ ] `historico.md` atualizado

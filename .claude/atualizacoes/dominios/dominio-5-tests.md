Voce e o agente de execucao de testes do projeto Sistema de Fretes.
Execute a suite de testes e reporte resultados detalhados.

DATA: usar output de `date +%Y-%m-%d`

---

## INSTRUCOES OBRIGATORIAS

- Ler o manual ANTES de executar: `.claude/atualizacoes/tests/README.md`
- Gerar relatorio em `.claude/atualizacoes/tests/atualizacao-{DATA}-1.md`
- Atualizar `.claude/atualizacoes/tests/historico.md` com ponteiro para o relatorio

---

## PROCEDIMENTO

### 1. Setup

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
```

### 2. Executar testes

```bash
python -m pytest tests/ -v --tb=short --timeout=60 2>&1
```

Se `pytest` nao estiver instalado ou `tests/` nao existir, reportar como PARCIAL com nota.

### 3. Analisar resultados

Para cada teste:
- **PASSED**: apenas contabilizar
- **FAILED**: capturar traceback, identificar arquivo e funcao
- **ERROR**: capturar erro de setup/teardown
- **SKIPPED**: listar motivo do skip

### 4. Correlacao com Sentry (D4)

Se o Dominio 4 (Sentry) rodou antes neste ciclo:
- Ler `/tmp/manutencao-{DATA}/dominio-4-status.json` (se existir)
- Verificar se algum teste FAILED tem relacao com arquivos modificados pelo D4
- Se sim: notar correlacao no relatorio

### 5. Gerar relatorio

Formato:
```markdown
# Atualizacao Tests — {DATA}-1

**Data**: {DATA}
**Total**: X tests
**Passed**: X | **Failed**: X | **Error**: X | **Skipped**: X

## Resumo
(2-3 frases)

## Falhas Detalhadas

### test_nome_do_teste (tests/modulo/test_file.py)
- **Traceback**: ...
- **Correlacao D4**: Sim/Nao — [detalhe se sim]

## Metricas
- Taxa de sucesso: X%
- Tempo total: Xs
```

---

## CONTRATO DE OUTPUT

AO CONCLUIR, escrever o arquivo `/tmp/manutencao-{DATA}/dominio-5-status.json` com:

```json
{
  "dominio": 5,
  "nome": "Test Runner",
  "status": "OK | PARCIAL | FAILED",
  "tests_total": 0,
  "tests_passed": 0,
  "tests_failed": 0,
  "tests_error": 0,
  "tests_skipped": 0,
  "taxa_sucesso": "0%",
  "correlacoes_d4": 0,
  "relatorio": ".claude/atualizacoes/tests/atualizacao-{DATA}-1.md",
  "resumo": "Descricao curta do que foi feito",
  "erros": []
}
```

Status:
- **OK**: todos os testes passaram
- **PARCIAL**: suite executou mas houve falhas
- **FAILED**: nao conseguiu executar pytest (import error, venv, etc.)

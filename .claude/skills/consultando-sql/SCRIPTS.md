# Scripts — Consultando SQL (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. generate_schemas.py

**Proposito:** Gera schemas JSON a partir dos modelos SQLAlchemy do projeto. Produz um arquivo JSON por tabela em `schemas/tables/`. Fonte de verdade para campos de TODAS as tabelas.

```bash
source .venv/bin/activate && \
python .claude/skills/consultando-sql/scripts/generate_schemas.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--stats` | Exibir estatisticas de geracao (total tabelas, campos, etc.) | flag |

**Saida:**
- Gera arquivos JSON em `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
- Cada arquivo contem: nome da tabela, colunas (nome, tipo, nullable, PK, FK, default), indices e constraints
- Output: texto com contagem de tabelas processadas

**Nota:** Este script e executado automaticamente pelo hook `lembrar-regenerar-schemas.py` ao editar `models.py`.

---

## 2. text_to_sql.py

**Proposito:** Converte perguntas em linguagem natural para consultas SQL. Usa catalogo de 104 tabelas ativas para gerar SQL read-only validado via Evaluator-Optimizer.

```bash
source .venv/bin/activate && \
python .claude/skills/consultando-sql/scripts/text_to_sql.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pergunta` / `-p` | Pergunta em linguagem natural (OBRIGATORIO) | `--pergunta "top 10 clientes por faturamento"` |
| `--debug` | Mostrar SQL gerado antes de executar | flag |

**Pipeline interno:**
1. Carrega catalogo de tabelas (schemas JSON)
2. Gera SQL via LLM a partir da pergunta
3. Valida SQL (read-only, sem DDL/DML)
4. Executa query no banco
5. Retorna resultados formatados

**Retorno JSON:**
```json
{
  "sucesso": true,
  "pergunta": "top 10 clientes por faturamento",
  "sql": "SELECT ... LIMIT 10",
  "resultados": [...],
  "total": 10,
  "tempo_ms": 250
}
```

**Restricoes de seguranca:**
- Apenas SELECT (rejeita INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE)
- Query read-only via transaction
- Timeout de execucao aplicado

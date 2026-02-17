# Scripts — Acessando SSW (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Nao requer ambiente virtual para `resolver_opcao_ssw.py` (opera no filesystem).
Requer `.venv` para `consultar_documentacao_ssw.py` se usar modo semantica (embeddings).

---

## 1. consultar_documentacao_ssw.py

**Proposito:** Busca textual na documentacao SSW (228 arquivos .md). Suporta 3 modos: regex, semantica e hibrida (default). NAO usa Flask/app context.

```bash
python .claude/skills/acessando-ssw/scripts/consultar_documentacao_ssw.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--busca` | Texto a buscar (OBRIGATORIO) | `--busca "contas a pagar"` |
| `--limite` | Max resultados (default: 10) | `--limite 5` |
| `--diretorio` | Filtrar por subdiretorio (pops, operacional, etc.) | `--diretorio pops` |
| `--modo` | Modo de busca: `regex`, `semantica` ou `hibrida` (default: hibrida) | `--modo regex` |

**Modos de busca:**

| Modo | Descricao | Requer Embeddings |
|------|-----------|-------------------|
| `regex` | Busca por expressao regular nos arquivos .md | Nao |
| `semantica` | Busca por similaridade vetorial (Voyage AI) | Sim |
| `hibrida` | Combina regex + semantica (default) | Sim (fallback regex) |

**Retorno JSON:**
```json
{
  "sucesso": true,
  "modo": "hibrida",
  "total": 5,
  "resultados": [
    {"arquivo": "opcao_436.md", "titulo": "Contas a Pagar", "score": 0.95, "trecho": "..."}
  ]
}
```

---

## 2. resolver_opcao_ssw.py

**Proposito:** Resolve opcao SSW por numero ou nome. Retorna doc .md, URL de ajuda e POP associado. Opera diretamente no filesystem (sem Flask/create_app).

```bash
python .claude/skills/acessando-ssw/scripts/resolver_opcao_ssw.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--numero` | Numero da opcao SSW (ex: 436, 004) | `--numero 436` |
| `--nome` | Nome/descricao da opcao (busca parcial) | `--nome "contas a pagar"` |

**Regra:** Ao menos um de `--numero` ou `--nome` deve ser fornecido.

**Retorno JSON:**
```json
{
  "sucesso": true,
  "opcao": {
    "numero": "436",
    "nome": "Contas a Pagar",
    "doc_md": "conteudo do arquivo .md",
    "url_ajuda": "https://...",
    "pop": "POP associado ou null"
  }
}
```

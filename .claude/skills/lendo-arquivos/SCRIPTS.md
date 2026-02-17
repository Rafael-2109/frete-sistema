# Scripts — Lendo Arquivos (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. ler.py

**Proposito:** Le arquivos Excel (.xlsx, .xls) e CSV (.csv) enviados pelo usuario via upload. Retorna conteudo estruturado como JSON para o agente processar e analisar.

```bash
source .venv/bin/activate && \
python .claude/skills/lendo-arquivos/scripts/ler.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--url` | URL do arquivo no formato `/agente/api/files/...` ou caminho absoluto (OBRIGATORIO) | `--url "/agente/api/files/default/abc_teste.xlsx"` |
| `--limite` | Limite de linhas a retornar (default: 1000) | `--limite 100` |
| `--aba` | Nome ou indice da aba para Excel (default: primeira) | `--aba "Vendas"`, `--aba 2` |
| `--cabecalho` | Linha do cabecalho, 0-indexed (default: 0) | `--cabecalho 1` |

**Resolucao de caminhos:**

O script converte URLs do agente para caminhos locais, tentando multiplos locais:
1. `/tmp/agente_files/{session_id}/{filename}` (skills)
2. `/tmp/agente_files/{user_id}/{session_id}/{filename}` (uploads do usuario)
3. Caminho direto se for path absoluto

**Formatos suportados:**

| Formato | Extensao | Deteccao |
|---------|----------|----------|
| Excel moderno | `.xlsx` | Via openpyxl |
| Excel legado | `.xls` | Via xlrd |
| CSV | `.csv` | Auto-deteccao de separador (`;`, `,`, `\t`, `\|`) |

**Retorno JSON:**
```json
{
  "sucesso": true,
  "arquivo": {
    "nome": "abc_teste.xlsx",
    "tipo": "excel",
    "tamanho": 25600,
    "tamanho_formatado": "25.0 KB",
    "abas": ["Vendas", "Custos"],
    "aba_lida": "Vendas"
  },
  "dados": {
    "colunas": ["Nome", "Valor", "Data"],
    "total_linhas": 5000,
    "linhas_retornadas": 1000,
    "registros": [{"Nome": "...", "Valor": 123.45, "Data": "2025-01-01"}]
  },
  "resumo": "Arquivo EXCEL com 5000 linhas e 3 colunas (limitado). Colunas: Nome, Valor, Data"
}
```

**Tratamento de dados:**
- NaN convertido para `null`
- Datas convertidas para ISO format (`.isoformat()`)
- Decimal convertido para float
- Nomes de colunas limpos (`strip()`)

**Dependencias:** `pandas`, `openpyxl` (xlsx), `xlrd` (xls legado).

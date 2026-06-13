<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/skills/exportando-arquivos/SKILL.md
superseded_by: —
atualizado: 2026-06-02
-->
# Scripts — Exportando Arquivos (Detalhes)

> **Papel:** Scripts — Exportando Arquivos (Detalhes).

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. exportar.py

**Proposito:** Gera arquivos para download (Excel, CSV, JSON, Imagem ou Texto/Codigo). Recebe dados via stdin (JSON) para formatos tabulares, caminho de imagem via parametro, ou caminho de arquivo de texto/codigo ja escrito (formato `texto`, alias `md` — .md/.txt/.py/.sql/.json/...). Salva em `/tmp/agente_files/default/` e retorna URL acessivel via HTTP.

```bash
# Para Excel/CSV/JSON (dados via stdin):
echo '{"dados": [...]}' | python .claude/skills/exportando-arquivos/scripts/exportar.py [parametros]

# Para imagem (caminho via parametro):
source .venv/bin/activate && \
python .claude/skills/exportando-arquivos/scripts/exportar.py --formato imagem --imagem /caminho/imagem.png --nome screenshot
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--formato` | Formato do arquivo: `excel`, `csv`, `json`, `imagem` ou `texto` (alias `md`) (OBRIGATORIO) | `--formato excel` |
| `--nome` | Nome do arquivo sem extensao (OBRIGATORIO) | `--nome relatorio_vendas` |
| `--titulo` | Titulo da planilha (apenas Excel) | `--titulo "Vendas Jan/2026"` |
| `--colunas` | Colunas a incluir (JSON array, opcional) | `--colunas '["nome","valor"]'` |
| `--imagem` | Caminho da imagem a exportar (apenas formato imagem) | `--imagem /tmp/grafico.png` |
| `--arquivo` | Caminho do arquivo de texto/codigo JA ESCRITO a entregar (apenas formato texto/md) | `--arquivo /tmp/piloto.py` |

**Modos de operacao:**

| Modo | Formato | Entrada | Descricao |
|------|---------|---------|-----------|
| Excel | `--formato excel` | stdin JSON `{"dados": [...]}` | Gera .xlsx com formatacao (cabecalho azul, moeda BR, largura auto) |
| Excel multi-abas | `--formato excel` | stdin JSON `{"abas": [...]}` | Gera .xlsx com VARIAS abas (cada aba = `{titulo, dados, colunas?}`); titulo truncado a 31 chars, duplicatas recebem sufixo `_N` |
| CSV | `--formato csv` | stdin JSON | Gera .csv com separador ponto-e-virgula (`;`) e encoding utf-8-sig |
| Texto/Codigo | `--formato texto` (alias `md`) | `--arquivo` (.md/.txt/.py/.sql/.json/... ja escrito) | Copia para o diretorio SERVIDO preservando extensao, com guard de entrega + URL verificada. Binarios rejeitados. (casos reais: dump .md 2026-06-10; script .py IMP-2026-06-12-006) |
| JSON | `--formato json` | stdin JSON | Gera .json formatado com indent=2 |
| Imagem | `--formato imagem` | `--imagem` path | Copia imagem (png/jpg/gif) para pasta de downloads |

**Formato do stdin (Excel/CSV/JSON):**
```json
{
  "dados": [
    {"col1": "valor1", "col2": 123.45},
    {"col1": "valor2", "col2": 678.90}
  ]
}
```

**Formato do stdin (Excel MULTI-ABAS — apenas `--formato excel`):**
```json
{
  "abas": [
    {"titulo": "Fantasmas Ativos", "dados": [{"nome": "A", "valor": 10.5}]},
    {"titulo": "Bloqueados", "dados": [{"id": 1}], "colunas": ["id"]},
    {"titulo": "Sem Vinculo", "dados": [{"user": "x", "email": "x@y.z"}]}
  ]
}
```
- Cada aba: `titulo` (nome da sheet, truncado a 31 chars), `dados` (linhas), `colunas` (subconjunto/ordem opcional).
- Titulos duplicados recebem sufixo `_1`, `_2`... (Excel rejeita sheets homonimas).
- `dados: []` gera uma aba vazia sem quebrar. O retorno inclui `arquivo.abas` (qtd) e `registros` (soma de todas as abas).
- Multi-abas e exclusivo do Excel; `csv`/`json` usam `{"dados": [...]}`.

**Retorno JSON:**
```json
{
  "sucesso": true,
  "arquivo": {
    "nome": "abc12345_relatorio.xlsx",
    "nome_original": "relatorio.xlsx",
    "url": "/agente/api/files/default/abc12345_relatorio.xlsx",
    "url_completa": "https://sistema-fretes.onrender.com/agente/api/files/default/abc12345_relatorio.xlsx",
    "tamanho": 15360,
    "tamanho_formatado": "15.0 KB",
    "registros": 42,
    "formato": "excel"
  },
  "mensagem": "Arquivo EXCEL criado com 42 registros!",
  "instrucao_agente": "..."
}
```

**Guard de entrega (P7 #787):** apos gerar o arquivo, o script confirma que ele
existe no diretorio servido e e NAO-VAZIO antes de declarar `sucesso: true`. Se o
arquivo sair ausente ou com 0 bytes, retorna `sucesso: false` + `erro` ("Falha na
verificacao de entrega: ...") e `arquivo: null` — NUNCA entrega URL de download
para um arquivo quebrado. Ao receber `sucesso: false`, NAO informe link ao usuario.

**Dependencias:** `pandas`, `xlsxwriter` (Excel), `shutil` (imagem).

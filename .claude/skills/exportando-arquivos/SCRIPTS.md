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

**Proposito:** Gera arquivos para download (Excel, CSV, JSON ou Imagem). Recebe dados via stdin (JSON) para formatos tabulares, ou caminho de imagem via parametro. Salva em `/tmp/agente_files/default/` e retorna URL acessivel via HTTP.

```bash
# Para Excel/CSV/JSON (dados via stdin):
echo '{"dados": [...]}' | python .claude/skills/exportando-arquivos/scripts/exportar.py [parametros]

# Para imagem (caminho via parametro):
source .venv/bin/activate && \
python .claude/skills/exportando-arquivos/scripts/exportar.py --formato imagem --imagem /caminho/imagem.png --nome screenshot
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--formato` | Formato do arquivo: `excel`, `csv`, `json` ou `imagem` (OBRIGATORIO) | `--formato excel` |
| `--nome` | Nome do arquivo sem extensao (OBRIGATORIO) | `--nome relatorio_vendas` |
| `--titulo` | Titulo da planilha (apenas Excel) | `--titulo "Vendas Jan/2026"` |
| `--colunas` | Colunas a incluir (JSON array, opcional) | `--colunas '["nome","valor"]'` |
| `--imagem` | Caminho da imagem a exportar (apenas formato imagem) | `--imagem /tmp/grafico.png` |

**Modos de operacao:**

| Modo | Formato | Entrada | Descricao |
|------|---------|---------|-----------|
| Excel | `--formato excel` | stdin JSON | Gera .xlsx com formatacao (cabecalho azul, moeda BR, largura auto) |
| CSV | `--formato csv` | stdin JSON | Gera .csv com separador ponto-e-virgula (`;`) e encoding utf-8-sig |
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

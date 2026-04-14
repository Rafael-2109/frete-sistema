# Scripts — Lendo Documentos (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao da skill
`lendo-documentos`.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. ler_doc.py

**Proposito**: le arquivos Word (.docx), CNAB (.ret/.rem/.cnab) e OFX (.ofx)
enviados pelo usuario via upload. Retorna conteudo estruturado como JSON.

Complementa `lendo-arquivos` (Excel/CSV). PDF e imagens NAO passam por este
script — vao direto como content blocks nativos do Claude (Fase B — 2026-04-14).

```bash
source .venv/bin/activate && \
python .claude/skills/lendo-documentos/scripts/ler_doc.py [parametros]
```

### Parametros

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--url` | URL do arquivo (`/agente/api/files/...`) ou caminho absoluto **(OBRIGATORIO)** | `--url "/agente/api/files/default/abc.docx"` |
| `--tipo` | Forca parser: `auto\|docx\|cnab\|ret\|rem\|ofx` (default `auto` por extensao) | `--tipo cnab` |
| `--limite` | Max paragraphs (docx) / detalhes (cnab) / transacoes (ofx) (default 1000) | `--limite 100` |
| `--offset` | Offset para paginacao (default 0) | `--offset 200` |

### Resolucao de caminhos

O script converte URLs do agente para caminhos locais, tentando multiplos locais:
1. `/tmp/agente_files/{session_id}/{filename}` (skills)
2. `/tmp/agente_files/{user_id}/{session_id}/{filename}` (uploads do usuario)
3. Caminho direto se for path absoluto

### Formatos suportados

| Formato | Extensao | Parser | Layout / Encoding |
|---------|----------|--------|---------------------|
| Word moderno | `.docx` | `python-docx` | OOXML |
| Word legado | `.doc` | ❌ NAO suportado | Instruir converter para .docx ou .pdf |
| CNAB retorno | `.ret`, `.cnab` | `app.financeiro.services.cnab400_parser_service.Cnab400ParserService` | BMP 274, latin-1 |
| CNAB remessa | `.rem` | Parser estrutural local (header/detalhe/trailer cru) | Generico (layout varia por banco), latin-1 |
| OFX | `.ofx` | `app.financeiro.services.ofx_parser_service.parsear_ofx` | SGML, latin-1 |
| RTF | `.rtf` | ❌ NAO suportado (v1) | Planejado: `striprtf` |

### Retorno JSON — Word (.docx)

```json
{
  "sucesso": true,
  "arquivo": {
    "nome": "contrato.docx",
    "tipo": "docx",
    "tamanho": 48230,
    "tamanho_formatado": "47.1 KB"
  },
  "dados": {
    "metadata": {
      "titulo": "Contrato de Servico",
      "autor": "Rafael Nascimento",
      "created": "2026-03-01T10:30:00",
      "modified": "2026-04-10T15:22:00",
      "paragraphs_count": 42,
      "tables_count": 3
    },
    "paragraphs": ["Clausula 1: ...", "..."],
    "tables": [[["col1", "col2"], ["val1", "val2"]]],
    "total_paragraphs": 42,
    "paragraphs_retornados": 42
  },
  "resumo": "Word com 42 paragraphs e 3 tabelas. Autor: Rafael Nascimento"
}
```

### Retorno JSON — CNAB retorno (.ret / .cnab)

```json
{
  "sucesso": true,
  "arquivo": {"nome": "retorno.ret", "tipo": "cnab", "tamanho": 50000},
  "dados": {
    "banco": "BMP Money Plus",
    "codigo_banco": "274",
    "empresa": "NACOM GOYA INDUSTRIA",
    "cnpj_empresa": "12.345.678/0001-90",
    "data_arquivo": "2026-04-14",
    "total_detalhes": 125,
    "detalhes_retornados": 125,
    "qtd_titulos_trailer": 125,
    "valor_total_trailer": 845670.23,
    "header": {...},
    "trailer": {...},
    "detalhes": [
      {
        "numero_linha": 2,
        "nosso_numero": "1234567890",
        "seu_numero": "143820/001",
        "codigo_ocorrencia": "06",
        "descricao_ocorrencia": "Liquidação Normal",
        "data_ocorrencia": "2026-04-14",
        "data_credito": "2026-04-14",
        "valor_titulo": 6775.40,
        "valor_pago": 6775.40,
        "cnpj_pagador": "11.222.333/0001-44"
      }
    ],
    "erros": []
  },
  "resumo": "CNAB BMP Money Plus: 125 titulos, valor total trailer R$ 845670.23"
}
```

### Retorno JSON — OFX (.ofx)

```json
{
  "sucesso": true,
  "arquivo": {"nome": "extrato.ofx", "tipo": "ofx", "tamanho": 12000},
  "dados": {
    "acctid": "450782",
    "dtstart": "2026-01-01",
    "dtend": "2026-01-31",
    "total_transacoes": 87,
    "transacoes_retornadas": 87,
    "transacoes": [
      {
        "trntype": "DEBIT",
        "dtposted": "2026-01-28",
        "trnamt": -1597.02,
        "fitid": "202601281597021",
        "checknum": "20834751",
        "memo": "DÉB.TIT.COMPE EFETIVADO",
        "name": "PAG BOLETO"
      }
    ]
  },
  "resumo": "OFX conta 450782: 87 transacoes (2026-01-01 a 2026-01-31)"
}
```

### Retorno JSON — CNAB remessa (.rem)

```json
{
  "sucesso": true,
  "arquivo": {"nome": "remessa.rem", "tipo": "rem"},
  "dados": {
    "formato": "CNAB400 remessa (estrutural, sem extracao de campos)",
    "total_detalhes": 42,
    "detalhes_retornados": 42,
    "header": {"numero_linha": 1, "tipo": "0", "tamanho": 400, "conteudo": "0..."},
    "trailer": {"numero_linha": 44, "tipo": "9", "tamanho": 400, "conteudo": "9..."},
    "detalhes": [
      {"numero_linha": 2, "tipo": "1", "tamanho": 400, "conteudo": "1..."}
    ]
  },
  "resumo": "CNAB remessa estrutural: 42 registros (sem extracao de campos — layout varia por banco)"
}
```

### Tratamento de dados

- `Decimal` convertido para `float` (via `decimal_default` no `json.dumps`)
- `date` / `datetime` convertidos para ISO format (`.isoformat()`)
- `NaN` convertido para `null`
- CNAB valores monetarios: parser ja divide centavos por 100, retorna float em reais
- `linha_original` removida dos detalhes CNAB (poluente, ja temos campos parseados)

### Dependencias

| Tipo | Dependencia | Observacao |
|------|-------------|------------|
| `.docx` | `python-docx==1.1.2` | `pip install python-docx==1.1.2` |
| `.ret/.cnab` | `app.financeiro.services.cnab400_parser_service` | Standalone (stdlib apenas) |
| `.rem` | stdlib | Sem dependencia externa |
| `.ofx` | `app.financeiro.services.ofx_parser_service` | Standalone (stdlib apenas) |

### Erros comuns

| Erro | Causa | Solucao |
|------|-------|---------|
| `Arquivo nao encontrado` | URL/caminho invalido | Conferir URL do anexo |
| `Dependencia nao instalada: python-docx` | Lib faltando | `pip install python-docx==1.1.2` |
| `Extensao sem suporte: .X` | Tipo errado | Suportados: `.docx`, `.ret`, `.rem`, `.cnab`, `.ofx` |
| `sucesso: true` + `total_detalhes: 0` | Arquivo vazio | **NAO e erro** — informar que nao ha dados |
| `cnab.erros` nao vazio | Linhas CNAB mal formatadas | Reportar quantas linhas + tipo |
| Caracteres estranhos em nomes | Encoding divergente | Arquivo em encoding nao-latin1 — reportar |

### Exemplos de uso

```bash
# Word
python .claude/skills/lendo-documentos/scripts/ler_doc.py \
  --url "/agente/api/files/default/abc_contrato.docx"

# CNAB retorno
python .claude/skills/lendo-documentos/scripts/ler_doc.py \
  --url "/agente/api/files/default/abc_retorno.ret"

# OFX extrato Sicoob
python .claude/skills/lendo-documentos/scripts/ler_doc.py \
  --url "/agente/api/files/default/abc_extrato.ofx"

# Paginar CNAB grande (titulos 100-200)
python .claude/skills/lendo-documentos/scripts/ler_doc.py \
  --url "..." --limite 100 --offset 100

# Forcar tipo quando extensao for ambigua
python .claude/skills/lendo-documentos/scripts/ler_doc.py \
  --url "/tmp/extrato_sem_extensao" --tipo ofx
```

---
name: lendo-documentos
description: >-
  Esta skill deve ser usada quando o usuario envia arquivo Word (.docx),
  CNAB retorno (.ret), CNAB remessa (.rem), CNAB generico (.cnab) ou OFX
  (Open Financial Exchange) e pede "analise esse documento", "le esse retorno
  bancario", "confere essa remessa", "o que tem nesse OFX", "extrai as
  transacoes desse extrato". Complementa `lendo-arquivos` (Excel/CSV).
  Reutiliza parsers ja validados em producao em app/financeiro/services.
  Retorna conteudo estruturado como JSON para o agente analisar.

  NAO USAR QUANDO:
  - Arquivo Excel (.xlsx, .xls) ou CSV → usar **lendo-arquivos**
  - PDF → ja vai como document block nativo Claude (Fase B 2026-04-14), sem skill
  - Imagem (png, jpg, etc) → ja vai como image block nativo (Vision API)
  - Criar/exportar arquivo → usar **exportando-arquivos**
  - Executar reconciliacao no Odoo apos ler → usar **executando-odoo-financeiro**
allowed-tools: Read, Bash, Glob, Grep
---

# Lendo Documentos — Word e Bancarios

Skill para leitura de documentos de texto estruturado enviados por upload:

- **Word (.docx)**: paragraphs, tables, metadata (titulo, autor, datas)
- **CNAB retorno (.ret / .cnab)**: layout BMP 274 via `Cnab400ParserService`
- **CNAB remessa (.rem)**: parser estrutural basico (header / detalhe / trailer)
- **OFX (.ofx)**: extrato bancario SGML/XML via `parsear_ofx`

> **PDF** e **imagens** NAO passam por esta skill — vao diretamente para o Claude
> como content blocks nativos apos upload (Fase B — 2026-04-14).

---

## Regras de Fidelidade (OBRIGATORIAS)

```
R1: NUNCA inventar dados que nao estao no output do script
R2: NUNCA arredondar valores monetarios — reportar EXATO como retornado
R3: CNAB valores sao em CENTAVOS — o parser JA divide por 100 (retorna float reais)
R4: Se o script retornar null em algum campo, reportar como "nao informado"
R5: Para .rem, o parser NAO extrai campos (layout varia por banco) — descrever
    limitacao se o usuario pedir valores especificos, e retornar o conteudo
    posicional cru para o agente fazer parse heuristico
R6: Sempre executar o script ANTES de responder — NAO usar Read diretamente
R7: Se houver erros de parse (lista `erros` no CNAB), reportar quantos e tipos
```

---

## Script Principal

```bash
source .venv/bin/activate && \
python .claude/skills/lendo-documentos/scripts/ler_doc.py [opcoes]
```

---

## Parametros

| Parametro | Obrigatorio | Descricao | Exemplo |
|-----------|-------------|-----------|---------|
| `--url` | Sim | URL do anexo OU caminho absoluto | `--url /tmp/agente_files/abc.docx` |
| `--tipo` | Nao | Forca tipo (default `auto` pela extensao) | `--tipo docx`, `--tipo cnab`, `--tipo ofx` |
| `--limite` | Nao | Max linhas/transacoes retornadas (default 1000) | `--limite 50` |
| `--offset` | Nao | Offset para paginacao (default 0) | `--offset 100` |

### Valores validos de `--tipo`

- `auto` (default): detecta pela extensao
- `docx`: forca parser Word
- `ret` ou `cnab`: forca parser CNAB400 (layout BMP 274)
- `rem`: forca parser remessa estrutural
- `ofx`: forca parser OFX (SGML/XML, latin-1)

---

## Exemplos de Uso

### Ler Word
```bash
source .venv/bin/activate && \
python .claude/skills/lendo-documentos/scripts/ler_doc.py \
  --url "/agente/api/files/default/abc_contrato.docx"
```

### Ler CNAB retorno
```bash
python .claude/skills/lendo-documentos/scripts/ler_doc.py \
  --url "/agente/api/files/default/abc_retorno.ret"
```

### Ler OFX extrato bancario
```bash
python .claude/skills/lendo-documentos/scripts/ler_doc.py \
  --url "/agente/api/files/default/abc_extrato.ofx"
```

### Paginacao (CNAB / OFX grandes)
```bash
# Primeiros 100 titulos
python .../ler_doc.py --url "..." --limite 100

# Proximos 100 titulos
python .../ler_doc.py --url "..." --limite 100 --offset 100
```

---

## Retorno JSON

### Word (.docx)

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
    "paragraphs": ["Clausula 1: ...", "Clausula 2: ...", "..."],
    "tables": [
      [["Item", "Valor"], ["Frete", "R$ 1.500,00"]]
    ],
    "total_paragraphs": 42,
    "paragraphs_retornados": 42
  },
  "resumo": "Word com 42 paragraphs e 3 tabelas. Autor: Rafael Nascimento"
}
```

### CNAB retorno (.ret / .cnab)

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
        "cnpj_pagador": "11.222.333/0001-44",
        ...
      }
    ],
    "erros": []
  },
  "resumo": "CNAB BMP Money Plus: 125 titulos, valor total R$ 845670.23"
}
```

### OFX (.ofx)

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
        "refnum": "20834751",
        "memo": "DÉB.TIT.COMPE EFETIVADO",
        "name": "PAG BOLETO"
      }
    ]
  },
  "resumo": "OFX conta 450782: 87 transacoes (2026-01-01 a 2026-01-31)"
}
```

### CNAB remessa estrutural (.rem)

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
  "resumo": "CNAB remessa estrutural: 42 registros (sem extracao de campos — use parser especifico do banco)"
}
```

---

## Formatos Suportados — Resumo

| Formato | Extensao | Parser | Layout |
|---------|----------|--------|--------|
| Word | `.docx` | `python-docx` | OOXML |
| Word legado | `.doc` | **NAO suportado** | Converter para .docx ou PDF |
| CNAB retorno | `.ret`, `.cnab` | `Cnab400ParserService` | BMP 274 (extract campos) |
| CNAB remessa | `.rem` | Parser estrutural basico | Bruto por tipo (0/1/9) |
| OFX | `.ofx` | `parsear_ofx` | SGML/XML, latin-1 |

---

## Notas Importantes

- **CNAB layout**: o parser atual foi validado para **BMP 274**. Outros bancos
  (Santander, Itau, Bradesco, Caixa) podem ter campos em posicoes ligeiramente
  diferentes. Se o `nome_banco` do header nao for BMP, alertar o usuario antes
  de usar valores extraidos como fonte de verdade.

- **Word legado (.doc binario Word 97-2003)**: NAO suportado por `python-docx`.
  Solucao: converter para `.docx` ou `.pdf` antes de enviar.

- **Arquivos grandes**: use `--limite` e `--offset` para paginar. CNAB de 10K
  titulos deve ser lido em lotes de 500-1000 para evitar output estouro de
  contexto.

- **Encoding CNAB/OFX**: arquivos bancarios brasileiros geralmente usam
  `latin-1` (ISO-8859-1). O parser decodifica automaticamente, mas se vir
  caracteres estranhos em nomes (ex: "OPERA??ES"), o arquivo foi gerado em
  encoding diferente — informar o usuario.

- **Bug historico CNAB**: arquivos com datas ano > 50 sao interpretados como
  1950-1999. Ano <= 49 vira 2000-2049. Se voce ver data do ano 1970 em um
  arquivo de 2026, o arquivo tem AA incorreto no campo de data.

---

## Tratamento de Erros

| Erro | Causa | Solucao |
|------|-------|---------|
| `Arquivo nao encontrado` | URL/caminho invalido | Verificar URL do anexo |
| `Dependencia nao instalada: python-docx` | Lib faltando | `pip install python-docx==1.1.2` |
| `Extensao sem suporte: .X` | Tipo errado | Suportados: .docx, .ret, .rem, .cnab, .ofx |
| `sucesso: true` + `total_detalhes: 0` | Arquivo vazio | **NAO e erro** — informar que nao ha dados |
| `cnab.erros` nao vazio | Linhas mal formatadas | Reportar quantas linhas + tipo do erro |

---

## Cenarios Compostos

### "Confere esse retorno CNAB e me diz quantos titulos liquidaram"
1. Execute a skill com `--tipo cnab`
2. Filtre `detalhes` por `codigo_ocorrencia in ('06', '07', '08', '17')` (liquidacoes)
3. Conte e some `valor_pago`
4. Reporte ao usuario

### "Quanto saiu da minha conta em janeiro?"
1. Execute a skill com `--tipo ofx`
2. Filtre `transacoes` por `trntype == 'DEBIT'`
3. Some `trnamt` (valores negativos)
4. Reporte o total

### "Extrai as clausulas desse contrato Word"
1. Execute a skill com `--tipo docx`
2. Percorra `paragraphs` buscando "Clausula N:"
3. Agrupe e apresente ao usuario

### "Esse retorno bancario pode ser reconciliado no Odoo?"
1. Primeiro leia o .ret com esta skill
2. Depois invoque `executando-odoo-financeiro` para criar payments + reconciliar
3. NAO tente reconciliar apenas com dados locais

---

## Referencias

- `references/formatos-bancarios.md` — CNAB400 / OFX layouts e limitacoes
- `app/financeiro/services/cnab400_parser_service.py` — fonte do parser CNAB
- `app/financeiro/services/ofx_parser_service.py` — fonte do parser OFX
- `app/financeiro/CLAUDE.md` — guia de desenvolvimento do modulo financeiro

---

## Relacionado

| Skill | Uso |
|-------|-----|
| `lendo-arquivos` | Excel (.xlsx, .xls) e CSV |
| `exportando-arquivos` | Criar arquivos para download |
| `executando-odoo-financeiro` | Reconciliar payments Odoo apos ler CNAB/OFX |
| `rastreando-odoo` | Auditar titulos, extratos e conciliacoes (leitura) |

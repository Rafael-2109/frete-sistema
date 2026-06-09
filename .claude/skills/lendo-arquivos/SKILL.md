---
name: lendo-arquivos
description: >-
  Le arquivo ENVIADO pelo usuario e retorna JSON fiel: Excel/CSV, Word .docx,
  CNAB .ret/.rem/.cnab, OFX. Gatilhos: "analise essa planilha", "le esse
  retorno bancario", "confere essa remessa", "o que tem nesse OFX/Word".
  NAO usar para: criar/exportar arquivo -> exportando-arquivos;
  PDF/imagem -> nativos (sem skill); dados do sistema -> consultando-sql.
allowed-tools: Read, Bash, Glob, Grep
---

# Lendo Arquivos — Processar Uploads do Usuario

## Indice

- [Escopo e roteamento por extensao](#escopo-e-roteamento-por-extensao)
- [Regras de Fidelidade (OBRIGATORIAS)](#regras-de-fidelidade-obrigatorias)
- [Script 1 — ler.py (Excel/CSV)](#script-1--lerpy-excelcsv)
- [Script 2 — ler_doc.py (Word / CNAB / OFX)](#script-2--ler_docpy-word--cnab--ofx)
- [Cenarios Compostos](#cenarios-compostos)
- [Tratamento de Erros](#tratamento-de-erros)
- [Detalhe completo](#detalhe-completo)
- [Relacionado](#relacionado)

## Escopo e roteamento por extensao

Skill UNICA para **leitura de arquivos enviados pelo usuario** via upload.
Dois scripts, roteados pela EXTENSAO do arquivo:

| Familia | Extensoes | Script |
|---------|-----------|--------|
| Tabular | `.xlsx`, `.xls`, `.csv` | `scripts/ler.py` |
| Documental | `.docx`, `.ret`, `.rem`, `.cnab`, `.ofx` | `scripts/ler_doc.py` |

> **Consolidacao (2026-06-09, F2.3 PAD-CTX)**: a antiga skill `lendo-documentos`
> foi unificada aqui — mesmo proposito (ler upload e devolver JSON fiel), scripts
> preservados. Se algum fluxo antigo citar `lendo-documentos`, use esta skill.
>
> **Outros formatos**: PDF e imagens NAO passam por esta skill — vao como content
> blocks nativos do Claude. Criar/exportar arquivo para download → `exportando-arquivos`.

## Regras de Fidelidade (OBRIGATORIAS)

```
R1: NUNCA inventar dados que nao estao no output do script
R2: NUNCA arredondar valores — reportar EXATAMENTE como retornado
R3: NUNCA renomear colunas/campos — usar os nomes EXATOS do JSON
R4: Se o script retornar null, reportar como "vazio/nulo/nao informado" — NAO preencher
R5: Se o usuario pedir calculo (soma, media), fazer sobre registros REAIS retornados
R6: Arquivo vazio (0 linhas/0 detalhes) NAO e erro — informar que nao ha dados
R7: Sempre executar o script ANTES de responder — NUNCA ler o arquivo com Read tool
R8: CNAB: valores ja vem em reais (parser divide centavos por 100); se a lista
    `erros` vier nao-vazia, reportar quantos e de que tipo
```

## Script 1 — ler.py (Excel/CSV)

```bash
source .venv/bin/activate && \
python .claude/skills/lendo-arquivos/scripts/ler.py --url "CAMINHO_OU_URL" [opcoes]
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| `--url` | Sim | URL do anexo (`/agente/api/files/...`) OU caminho absoluto |
| `--limite` | Nao | Limite de linhas (default 1000) |
| `--aba` | Nao | Nome ou indice da aba (Excel) |
| `--cabecalho` | Nao | Linha do cabecalho, 0-indexed (default 0) |

- Separador CSV auto-detectado (`;` `,` tab `|`); encoding UTF-8 com BOM ok.
- Colunas "Unnamed: 0" no retorno = cabecalho errado → tentar `--cabecalho 1`.
- Retorno: `dados.registros` (lista de dicts), `dados.total_linhas` (real, antes
  do limite), `arquivo.abas`/`aba_lida` (Excel). Datas em ISO; NaN → null;
  booleanos Excel viram 1.0/0.0.

## Script 2 — ler_doc.py (Word / CNAB / OFX)

```bash
source .venv/bin/activate && \
python .claude/skills/lendo-arquivos/scripts/ler_doc.py --url "CAMINHO_OU_URL" [opcoes]
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| `--url` | Sim | URL do anexo OU caminho absoluto |
| `--tipo` | Nao | Forca parser: `auto\|docx\|cnab\|ret\|rem\|ofx` (default `auto`) |
| `--limite` / `--offset` | Nao | Paginacao (default 1000/0) — use em CNAB/OFX grandes |

| Formato | Parser | Nota |
|---------|--------|------|
| `.docx` | python-docx | paragraphs + tables + metadata. `.doc` legado NAO suportado (converter) |
| `.ret`/`.cnab` | `Cnab400ParserService` (app/financeiro) | layout validado = BMP 274; outro banco no header → alertar antes de confiar nos campos |
| `.rem` | estrutural basico | NAO extrai campos (layout varia por banco) — retorna conteudo posicional cru |
| `.ofx` | `parsear_ofx` (app/financeiro) | SGML/XML latin-1; transacoes com trntype/dtposted/trnamt |

- Encoding bancario = latin-1 (auto); caracteres "OPERA??ES" = arquivo em outro
  encoding — informar o usuario.
- Datas CNAB com AA>50 viram 19xx — data "1970" em arquivo recente = AA errado na origem.

## Cenarios Compostos

- **"Leia e some a coluna X"**: executar script → somar sobre `dados.registros`;
  se `total_linhas > linhas_retornadas`, avisar que a soma e parcial.
- **"Compare com o sistema"**: 1) ler arquivo aqui; 2) consultar via skill/SQL
  apropriada; 3) cruzar na resposta.
- **"Quantos titulos liquidaram nesse retorno?"**: `--tipo cnab` → filtrar
  `detalhes` por `codigo_ocorrencia in ('06','07','08','17')` → contar/somar `valor_pago`.
- **"Quanto saiu da conta no mes?"**: `--tipo ofx` → filtrar `trntype == 'DEBIT'`
  → somar `trnamt`.
- **"Reconcilia esse retorno no Odoo?"**: ler aqui PRIMEIRO; depois
  `executando-odoo-financeiro` (nunca reconciliar so com dados locais).

## Tratamento de Erros

| Erro | Solucao |
|------|---------|
| `Arquivo nao encontrado` | conferir URL do anexo / caminho absoluto |
| `Formato/extensao sem suporte` | tabular: xlsx/xls/csv · documental: docx/ret/rem/cnab/ofx |
| `Dependencia nao instalada` | `pip install pandas openpyxl xlrd python-docx` |
| `sucesso: true` + 0 linhas/detalhes | NAO e erro — informar arquivo vazio |

## Detalhe completo

JSON de retorno por formato e resolucao de caminhos: ver `SCRIPTS.md` (mesma
pasta) — referencia integral dos dois scripts. Layouts bancarios:
`references/formatos-bancarios.md`.

## Relacionado

| Skill | Uso |
|-------|-----|
| exportando-arquivos | CRIAR/EXPORTAR arquivos para download |
| executando-odoo-financeiro | Reconciliar payments Odoo apos ler CNAB/OFX |
| consultando-sql | Dados do sistema (sem arquivo de entrada) |

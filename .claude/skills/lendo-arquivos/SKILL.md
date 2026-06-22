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
- [Analise alem da leitura (read-only)](#analise-alem-da-leitura-read-only)
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

## Analise alem da leitura (read-only)

A leitura fiel (R1-R7) e o **DEFAULT**. Esta secao e analise EXPLORATORIA sob
demanda — read-only, **NUNCA escreve no sistema**. Ao REPORTAR numeros, R1-R4
continuam valendo: nao inventar, nao arredondar, nao renomear. Use so quando o
usuario pede uma pergunta analitica (distribuicao, completude, consistencia,
diff). **Nao vire engine generica**: 1 heredoc focado responde a pergunta; nao
construa pipeline de dados.

### Padrao canonico (2 passos)

**PASSO 1** — rodar `ler.py` UMA vez para ver `colunas`, `abas`/`aba_lida` e
`total_linhas` (orienta a analise; nao precisa de mais).

**PASSO 2** — Bash heredoc com pandas lendo o **ARQUIVO INTEIRO** via
`url_para_caminho`. **NUNCA analise sobre `dados.registros` do JSON do ler.py —
ele vem TRUNCADO em 1000 linhas (`--limite` default 1000); contagem/soma sairiam
erradas.** Molde de import:

```bash
source .venv/bin/activate && python3 - <<'PY'
import sys
sys.path.insert(0, '.claude/skills/lendo-arquivos/scripts')
from ler import url_para_caminho
import pandas as pd
caminho = url_para_caminho("CAMINHO_OU_URL")
df = pd.read_excel(caminho)        # ou pd.read_csv(caminho, sep=';')
# ... analise abaixo ...
PY
```

### Receitas

(a) **Distribuicao** de uma coluna (NaN conta como categoria):
```python
print(df["LOJA"].value_counts(dropna=False))
```

(b) **Completude** de colunas obrigatorias:
```python
obrig = ["LOJA", "CNPJ", "MODELO"]
print(df[obrig].isna().sum())                       # nulos por coluna
print("linhas c/ alguma obrig nula:", df[obrig].isna().any(axis=1).sum())
```

(c) **Consistencia 1:1 entre 2 colunas — BIDIRECIONAL** (os DOIS sentidos sao
defeito):
```python
loja_n_cnpj = df.groupby("LOJA")["CNPJ"].nunique()
cnpj_n_loja = df.groupby("CNPJ")["LOJA"].nunique()
print("1 LOJA com N CNPJ:\n", loja_n_cnpj[loja_n_cnpj > 1])
print("1 CNPJ com N LOJA:\n", cnpj_n_loja[cnpj_n_loja > 1])
```

(d) **Diff vs sistema** — extraia o SET de chaves AQUI e **delegue o cruzamento a
`consultando-sql`** (NAO consulte SQL nesta skill):
```python
chaves = sorted(df["CNPJ"].dropna().astype(str).unique())
print("total chaves:", len(chaves)); print(chaves)
```
Depois leve `chaves` para `consultando-sql` cruzar com o banco.

(e) **Simulacao de exclusao** (quais linhas restam se remover N chaves):
```python
remover = {"001", "002"}
antes = len(df); df2 = df[~df["LOJA"].astype(str).isin(remover)]
print("antes:", antes, "depois:", len(df2))
print(df2["MODELO"].value_counts())                 # vs df["MODELO"].value_counts()
```

### Ponteiro final

Para regra de negocio especifica, escreva pandas ad-hoc seguindo o molde acima.
**Anti-retry-storm**: rode UM heredoc completo que ja responde a pergunta toda,
em vez de N tentativas incrementais.

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

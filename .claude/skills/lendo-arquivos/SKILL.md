---
name: lendo-arquivos
description: >-
  Esta skill deve ser usada quando o usuario envia arquivo Excel ou CSV e
  pede "analise essa planilha", "o que tem nesse Excel?", "importa os dados
  desse CSV", "confere os valores dessa planilha", ou precisa processar
  arquivo enviado. Retorna conteudo como JSON para analise.
  Nao usar para criar ou exportar arquivo (usar exportando-arquivos),
  ler arquivo de codigo ou texto (usar Read diretamente), ou processar
  dados sem arquivo de entrada (usar consultando-sql).

  NAO USAR QUANDO:
  - CRIAR/exportar arquivo para download → usar **exportando-arquivos**
  - Ler arquivo de codigo/texto do projeto → usar Read tool
  - Consultar dados do sistema → usar skill de consulta apropriada
allowed-tools: Read, Bash, Glob, Grep
---

# Lendo Arquivos - Processar Uploads do Usuario

Skill para **leitura de arquivos** enviados pelo usuario via upload.

> **ESCOPO:** Esta skill processa Excel (.xlsx, .xls) e CSV.
>
> **Outros formatos** (2026-04-14):
> - **Word (.docx), CNAB (.ret/.rem/.cnab), OFX** → usar `lendo-documentos`
> - **PDF, imagens** → processados nativamente pelo Claude (sem skill, Fase B)
> - **Criar/exportar** arquivos para download → `exportando-arquivos`
> - **Consultas Odoo** (NF, PO, SO, titulos) → `rastreando-odoo`

## Regras de Fidelidade (OBRIGATORIAS)

```
R1: NUNCA inventar dados que nao estao no output do script
R2: NUNCA arredondar valores — reportar EXATAMENTE como retornado
R3: NUNCA renomear colunas — usar os nomes EXATOS do JSON
R4: Se o script retornar null, reportar como "vazio/nulo" — NAO preencher
R5: Se o usuario pedir calculo (soma, media), fazer sobre registros REAIS
R6: Se o arquivo estiver vazio (0 linhas), informar que nao ha dados — NAO e erro
R7: Sempre executar o script ANTES de responder — NUNCA ler o arquivo com Read tool
```

## Script Principal

### ler.py

```bash
source .venv/bin/activate && \
python .claude/skills/lendo-arquivos/scripts/ler.py [opcoes]
```

## Tipos de Arquivo

```
FORMATOS SUPORTADOS
│
├── Excel (.xlsx)
│   Engine: openpyxl
│   Usar: Planilhas modernas (2007+)
│
├── Excel (.xls)
│   Engine: xlrd
│   Usar: Planilhas legado (97-2003)
│
└── CSV (.csv)
    Separadores: ; , \t |
    Deteccao automatica (sem precisar informar)
    Usar: Arquivos texto estruturados
```

## Parametros

### Parametros Principais

| Parametro | Obrigatorio | Descricao | Exemplo |
|-----------|-------------|-----------|---------|
| `--url` | Sim | URL do arquivo ou **caminho absoluto** | `--url /tmp/agente_files/abc.xlsx` |
| `--limite` | Nao | Limite de linhas (default: 1000) | `--limite 100` |
| `--aba` | Nao | Nome ou indice da aba (Excel) | `--aba 0` ou `--aba "Dados"` |
| `--cabecalho` | Nao | Linha do cabecalho, 0-indexed (default: 0) | `--cabecalho 1` |

### Quando usar `--cabecalho`

O default (`--cabecalho 0`) assume que a primeira linha e o cabecalho.
Use `--cabecalho 1` quando a planilha tem titulo ou linhas de metadados acima dos dados.
Se nao souber, tente primeiro sem o parametro. Se as colunas vierem estranhas (ex: "Unnamed: 0"), tente `--cabecalho 1`.

### Quando usar `--url` com caminho absoluto

O `--url` aceita TANTO URLs do agente (`/agente/api/files/...`) QUANTO caminhos absolutos (`/home/.../arquivo.xlsx`, `/tmp/arquivo.csv`).
Para arquivos locais do projeto, use o caminho absoluto completo.

## Exemplos de Uso

### Ler arquivo Excel
```bash
source .venv/bin/activate && \
python .claude/skills/lendo-arquivos/scripts/ler.py \
  --url "/agente/api/files/default/abc123_planilha.xlsx"
```

### Ler com caminho absoluto
```bash
source .venv/bin/activate && \
python .claude/skills/lendo-arquivos/scripts/ler.py \
  --url "/tmp/dados_cliente.xlsx"
```

### Ler com limite de linhas
```bash
python .../ler.py --url "/agente/api/files/default/dados.xlsx" --limite 50
```

### Ler aba especifica
```bash
python .../ler.py --url "/agente/api/files/default/multi.xlsx" --aba "Vendas"
```

### Ler CSV
```bash
python .../ler.py --url "/agente/api/files/default/dados.csv"
```

## Retorno JSON

```json
{
  "sucesso": true,
  "arquivo": {
    "nome": "planilha.xlsx",
    "tipo": "excel",
    "tamanho": 15234,
    "tamanho_formatado": "14.9 KB",
    "abas": ["Dados", "Resumo"],
    "aba_lida": "Dados"
  },
  "dados": {
    "colunas": ["Pedido", "Cliente", "Valor"],
    "total_linhas": 150,
    "linhas_retornadas": 100,
    "registros": [
      {"Pedido": "VCD123", "Cliente": "ATACADAO", "Valor": 50000},
      {"Pedido": "VCD456", "Cliente": "ASSAI", "Valor": 75000}
    ]
  },
  "resumo": "Arquivo EXCEL com 150 linhas e 3 colunas (limitado). Colunas: Pedido, Cliente, Valor"
}
```

### Campos importantes no retorno

| Campo | Significado |
|-------|-------------|
| `sucesso` | `true` se o arquivo foi lido com sucesso |
| `dados.total_linhas` | Total REAL de linhas no arquivo (antes do limite) |
| `dados.linhas_retornadas` | Quantas linhas estao em `registros` (apos limite) |
| `dados.registros` | Lista de dicts — CADA dict e uma linha com colunas como chaves |
| `arquivo.abas` | Apenas para Excel — lista de TODAS as abas disponiveis |
| `arquivo.aba_lida` | Apenas para Excel — qual aba foi efetivamente lida |

## Cenarios Compostos

### "Leia o arquivo e some a coluna X"
1. Execute o script normalmente
2. Percorra `dados.registros` e some os valores da coluna
3. **Use apenas os valores retornados** — nao invente valores extras
4. Se `total_linhas > linhas_retornadas`, avise que a soma e parcial

### "Compare este arquivo com dados do sistema"
1. Primeiro leia o arquivo com esta skill
2. Depois consulte o sistema com a skill apropriada (consultando-sql, etc.)
3. Cruze os dados manualmente na resposta

### "O arquivo tem dados de quais clientes?"
1. Execute o script
2. Liste valores UNICOS da coluna de clientes encontrados nos registros
3. **NAO consulte o banco** — a pergunta e sobre o ARQUIVO

## Tratamento de Erros

| Erro | Causa | Solucao |
|------|-------|---------|
| `sucesso: false` + `erro: "Arquivo nao encontrado"` | URL/caminho invalido | Verificar URL do anexo ou caminho |
| `sucesso: false` + `erro: "Formato nao suportado"` | Extensao invalida | Apenas xlsx, xls, csv |
| `sucesso: false` + `erro: "Dependencia nao instalada"` | Biblioteca faltando | `pip install pandas openpyxl xlrd` |
| `sucesso: true` + `total_linhas: 0` | Arquivo vazio | **NAO e erro** — informar que nao ha dados |
| Colunas "Unnamed: 0" | Cabecalho errado | Tentar `--cabecalho 1` |

## Conversoes Automaticas

| Tipo Original | Conversao |
|---------------|-----------|
| Datas | ISO 8601 (YYYY-MM-DD) |
| Numeros | float/int preservado |
| NaN/vazio | null |
| Texto | string |
| Booleanos | 1.0/0.0 (Excel converte para numerico) |

## Notas

- Limite padrao: 1000 linhas (para evitar respostas muito grandes)
- Para arquivos grandes, use `--limite` para obter amostra
- Separador CSV eh detectado automaticamente (`;`, `,`, `\t`, `|`)
- Encoding: UTF-8 com BOM suportado
- **Booleanos em Excel**: True/False sao convertidos para 1.0/0.0 pelo pandas

## Fluxo de Uso

Quando o usuario anexar um arquivo e pedir "analise essa planilha":

1. **Identificar caminho** do arquivo (URL do anexo ou caminho local)
2. **Executar script** (OBRIGATORIO — nao usar Read tool para ler planilhas):
   ```bash
   source .venv/bin/activate && python .claude/skills/lendo-arquivos/scripts/ler.py --url "CAMINHO_DO_ARQUIVO"
   ```
3. **Verificar sucesso** no JSON retornado
4. **Analisar dados** usando APENAS os registros retornados
5. **Responder ao usuario** com insights dos dados reais

## Relacionado

| Skill | Uso |
|-------|-----|
| exportando-arquivos | CRIAR/EXPORTAR arquivos para download |
| rastreando-odoo | Consultas e rastreamento de fluxos Odoo |
| gerindo-expedicao | Consultas de carteira, separacoes e estoque |

> **NOTA**: Esta skill eh para LEITURA de arquivos do usuario.
> Para criar arquivos para download, use `exportando-arquivos`.

---
name: exportando-arquivos
description: >-
  Esta skill deve ser usada quando o usuario pede "exporte para Excel",
  "gere planilha", "relatorio em CSV", "quero baixar esses dados",
  "salve screenshot para download", ou precisa gerar arquivos para download.
  SEMPRE usar esta skill em vez de Write para criar arquivos de download.
  Nao usar para ler arquivos enviados pelo usuario (usar lendo-arquivos),
  consultar dados sem exportar (usar consultando-sql), ou exportar razao
  geral do Odoo (usar razao-geral-odoo que ja gera Excel).

  NAO USAR QUANDO:
  - LER arquivo enviado pelo usuario → usar **lendo-arquivos**
  - Criar arquivo de codigo/config (nao download) → usar Write tool
  - Consultar dados sem exportar → usar skill de consulta apropriada primeiro
allowed-tools: Read, Bash, Glob, Grep
---

# Exportando Arquivos - Gerar Downloads para Usuario

Skill para **criacao de arquivos** que o usuario pode baixar.

> **ESCOPO:** Esta skill CRIA arquivos Excel, CSV e JSON para download.
> Para LER arquivos enviados pelo usuario, use `lendo-arquivos`.

## REGRAS CRITICAS

### R1: NUNCA usar Write tool para arquivos de download
```
PROIBIDO: Write("/tmp/relatorio.xlsx", conteudo)
CORRETO:  echo '{"dados": [...]}' | python exportar.py --formato excel --nome relatorio
```
O script gera UUID no nome, salva em `/tmp/agente_files/default/`, e retorna URL acessivel via HTTP.

### R2: SEMPRE usar url_completa na resposta
```
ERRADO:  /agente/api/files/default/abc_pedidos.xlsx  (URL relativa — QUEBRA no Render)
CORRETO: https://sistema-fretes.onrender.com/agente/api/files/default/abc_pedidos.xlsx
```
O campo `arquivo.url_completa` do retorno JSON ja contem a URL com dominio. Copiar EXATAMENTE.

### R3: NUNCA inventar dados para preencher o arquivo
```
PROIBIDO: Criar dados fictícios quando o usuario nao forneceu
PROIBIDO: Completar colunas que o usuario nao pediu
CORRETO:  Usar SOMENTE os dados fornecidos pelo usuario ou retornados por outra skill
```
Se o usuario pedir "exporta os pedidos do Atacadao" sem dados, PRIMEIRO buscar dados com skill apropriada (gerindo-expedicao, consultando-sql, etc.), DEPOIS exportar.

### R4: Fidelidade ao output do script
```
PROIBIDO: Dizer "arquivo com 10 registros" se script retornou registros=5
PROIBIDO: Inventar tamanho do arquivo sem ler do campo tamanho_formatado
CORRETO:  Citar valores EXATOS do JSON de retorno (registros, tamanho, nome)
```

### R5: Tratar erros sem inventar alternativas
```
Se script retornar sucesso=false:
  - Informar o EXATO erro retornado pelo script
  - NAO inventar solucao alternativa (ex: "vou criar manualmente")
  - NAO usar Write tool como fallback

Erros comuns:
  - "Nenhum dado recebido via stdin" → echo vazio ou pipe incorreto
  - "JSON invalido" → verificar aspas e estrutura
  - "Campo dados vazio" → lista vazia, informar usuario
  - "Imagem nao encontrada" → caminho errado, pedir caminho correto
```

## Script Principal

### exportar.py

```bash
source .venv/bin/activate && \
echo '{"dados": [...]}' | python .claude/skills/exportando-arquivos/scripts/exportar.py [opcoes]
```

## Formatos de Saida

```
FORMATOS SUPORTADOS
│
├── Excel (.xlsx)
│   Engine: xlsxwriter
│   Recursos: Formatacao, cabecalho colorido, largura auto
│   Colunas com "valor/preco/custo/total" recebem formato moeda automaticamente
│
├── CSV (.csv)
│   Separador: ponto-e-virgula (;)
│   Encoding: UTF-8 com BOM (compativel Excel BR)
│
├── JSON (.json)
│   Formatacao: indentado, UTF-8
│   Suporta Decimal e datetime automaticamente
│
└── Imagem (.png, .jpg, .jpeg, .gif)
    Copia imagem existente para pasta de downloads
    NAO precisa de stdin — usa --imagem /caminho/arquivo.png
```

## Parametros

| Parametro | Obrigatorio | Descricao | Exemplo |
|-----------|-------------|-----------|---------|
| `--formato` | Sim | Formato: `excel`, `csv`, `json` ou `imagem` | `--formato excel` |
| `--nome` | Sim | Nome do arquivo (sem extensao) | `--nome pedidos_atacadao` |
| `--titulo` | Nao | Titulo da planilha (Excel, max 31 chars) | `--titulo "Pedidos Atacadao"` |
| `--colunas` | Nao | Colunas a incluir (JSON array) | `--colunas '["Pedido","Cliente"]'` |
| `--imagem` | Sim* | Caminho da imagem (*apenas formato imagem) | `--imagem /tmp/screenshot.png` |

### Entrada de Dados (Excel/CSV/JSON)

Dados via **stdin** no formato JSON:
```json
{
  "dados": [
    {"Pedido": "VCD123", "Cliente": "ATACADAO 123", "Valor": 50000},
    {"Pedido": "VCD456", "Cliente": "ATACADAO 456", "Valor": 75000}
  ]
}
```

### Imagens (sem stdin)

```bash
python exportar.py --formato imagem --imagem /tmp/grafico.png --nome vendas
```

## Exemplos de Uso

### Excel com titulo e colunas filtradas
```bash
source .venv/bin/activate && \
echo '{"dados": [{"Pedido": "VCD001", "Cliente": "ATACADAO", "Valor": 50000}]}' | \
python .claude/skills/exportando-arquivos/scripts/exportar.py \
  --formato excel \
  --nome pedidos_atacadao \
  --titulo "Pedidos Atacadao" \
  --colunas '["Pedido", "Valor"]'
```

### CSV simples
```bash
source .venv/bin/activate && \
echo '{"dados": [{"Nome": "Produto A", "Preco": 10.5}]}' | \
python .claude/skills/exportando-arquivos/scripts/exportar.py \
  --formato csv \
  --nome produtos
```

### JSON
```bash
source .venv/bin/activate && \
echo '{"dados": [{"id": 1, "nome": "teste"}]}' | \
python .claude/skills/exportando-arquivos/scripts/exportar.py \
  --formato json \
  --nome dados
```

### Imagem
```bash
source .venv/bin/activate && \
python .claude/skills/exportando-arquivos/scripts/exportar.py \
  --formato imagem \
  --imagem /tmp/screenshot.png \
  --nome grafico_vendas
```

## Retorno JSON

```json
{
  "sucesso": true,
  "arquivo": {
    "nome": "abc123_pedidos.xlsx",
    "nome_original": "pedidos.xlsx",
    "url": "/agente/api/files/default/abc123_pedidos.xlsx",
    "url_completa": "https://sistema-fretes.onrender.com/agente/api/files/default/abc123_pedidos.xlsx",
    "tamanho": 15234,
    "tamanho_formatado": "14.9 KB",
    "registros": 10,
    "formato": "excel"
  },
  "mensagem": "Arquivo EXCEL criado com 10 registros!",
  "instrucao_agente": "..."
}
```

**Campos para usar na resposta:**
- `arquivo.url_completa` → link de download (OBRIGATORIO)
- `arquivo.registros` → quantidade de registros
- `arquivo.tamanho_formatado` → tamanho humano (ex: "14.9 KB")
- `arquivo.nome_original` → nome original do arquivo

## Fluxo Completo (Composicao com Outras Skills)

Quando o usuario pedir "exporte os 10 maiores pedidos para Excel":

1. **Buscar dados** usando skill apropriada (ex: `consultando-sql`, `gerindo-expedicao`)
2. **Formatar como JSON**: `{"dados": [resultado_da_consulta]}`
3. **Executar script**: `echo '{"dados": [...]}' | python exportar.py --formato excel --nome pedidos`
4. **Ler retorno JSON** e extrair `arquivo.url_completa`
5. **Responder ao usuario** com link para download usando url_completa

## Formatacao Automatica (Excel)

| Tipo de Coluna | Formatacao Aplicada |
|----------------|---------------------|
| Valor, Preco, Custo, Total | R$ #,##0.00 |
| Cabecalho | Negrito, fundo azul (#4472C4), texto branco |
| Largura | Auto-ajuste ate 50 caracteres |

## Notas

- Arquivos salvos em `/tmp/agente_files/default/` com UUID no nome
- URL acessivel via HTTP no Render
- Tamanho maximo recomendado: 10MB
- Arquivos removidos apos 24h (limpeza do /tmp)
- CSV usa ponto-e-virgula (`;`) como separador (padrao brasileiro)
- JSON serializa `Decimal` e `datetime` automaticamente

## Relacionado

| Skill | Uso |
|-------|-----|
| lendo-arquivos | LER arquivos enviados pelo usuario |
| consultando-sql | Consultar dados para depois exportar |
| gerindo-expedicao | Dados de carteira/separacao para exportar |
| rastreando-odoo | Dados Odoo (NF, PO, SO) para exportar |
| razao-geral-odoo | Exporta razao geral (JA gera Excel, NAO precisa desta skill) |

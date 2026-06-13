---
name: exportando-arquivos
description: >-
  Gera arquivos Excel/CSV/JSON/MD para download (usar em vez de Write).
  Gatilhos: "exporte para Excel", "gere planilha", "relatorio em
  CSV", "quero baixar esses dados", "salve screenshot para download",
  "exporte/entregue esse documento .md".
  Anti-gatilhos: LER upload do usuario -> lendo-arquivos; exportar razao geral
  Odoo -> razao-geral-odoo.
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
O script gera UUID no nome, salva em `$AGENTE_FILES_ROOT/agente_files/default/` (default `/tmp/agente_files/default/`), e retorna URL acessivel via HTTP. O diretorio e o MESMO que a rota de download serve — nunca depende de `$TMPDIR` (que difere entre o subprocesso CLI e o gunicorn).

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

### R6: Entrega atomica — link na mesma mensagem da confirmacao (I7)

**Reforca a regra `I7` do system_prompt do agente.**

```
PROIBIDO: Confirmar geracao em uma mensagem e postar o link em outra
PROIBIDO: Anunciar "arquivo gerado", "link acima", "preparando download"
          sem o link literal (`https://...`) na mesma mensagem
PROIBIDO: Mensagens de progresso intermediarias ("script OK", "extraindo
          dados", "gerando link...") quando o script retorna em <30s
CORRETO:  Aguardar o JSON de retorno do script, extrair `arquivo.url_completa`
          e responder UMA UNICA vez com link + resumo + dados
```

**Self-check antes de enviar resposta de geracao**:
- [ ] O link clicavel completo (`https://sistema-fretes.onrender.com/...`) esta no texto?
- [ ] O resumo (registros + tamanho) esta no texto?
- [ ] Se houver dados estruturados (tabelas), estao inline na mesma mensagem?

Se qualquer item faltar → NAO envie. Aguarde ter tudo pronto.

**ANTI-PADRAO PROIBIDO** (sessoes 4cc8c1f6 e ed2fa68c, 07/05/2026 — 3 e 12
perguntas "gerou?" antes de receber o link, respectivamente): confirmar
execucao do script em mensagem separada do link forca o usuario a
perguntar repetidamente se o arquivo foi gerado. Geracao + entrega do
link sao ATOMICAS do ponto de vista do usuario.

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
├── Imagem (.png, .jpg, .jpeg, .gif)
│   Copia imagem existente para pasta de downloads
│   NAO precisa de stdin — usa --imagem /caminho/arquivo.png
│
└── Texto / Codigo (.md, .txt, .py, .sql, .json, .log, .csv, .xml, .yaml/.yml, .sh, .ini, .cfg, .toml, .rst, .env)
    Copia um arquivo de texto/codigo JA ESCRITO para a pasta de downloads
    NAO precisa de stdin — usa --arquivo /caminho/arquivo.ext --formato texto
    Extensao original PRESERVADA. Binarios (.bin/.exe/...) sao rejeitados de proposito.
    (formato `md` segue valido como alias retrocompativel de `texto`)
```

> **Quando usar `texto` vs `excel/csv/json`**: `excel/csv/json` recebem DADOS via stdin
> e GERAM o arquivo. `texto` ENTREGA um arquivo ja escrito (relatorio .md, script .py,
> dump .sql) sem precisar de `cp` manual ao diretorio servido — a rota de download
> serve qualquer dessas extensoes (forca download para nao-imagens).

## Parametros

| Parametro | Obrigatorio | Descricao | Exemplo |
|-----------|-------------|-----------|---------|
| `--formato` | Sim | Formato: `excel`, `csv`, `json`, `imagem` ou `texto` (alias `md`) | `--formato excel` |
| `--nome` | Sim | Nome do arquivo (sem extensao) | `--nome pedidos_atacadao` |
| `--titulo` | Nao | Titulo da planilha (Excel, max 31 chars) | `--titulo "Pedidos Atacadao"` |
| `--colunas` | Nao | Colunas a incluir (JSON array) | `--colunas '["Pedido","Cliente"]'` |
| `--imagem` | Sim* | Caminho da imagem (*apenas formato imagem) | `--imagem /tmp/screenshot.png` |
| `--arquivo` | Sim** | Caminho do arquivo texto/codigo ja escrito (**apenas formato texto/md) | `--arquivo /tmp/script.py` |

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

### Texto / Codigo ja escrito (sem stdin)

Entrega um arquivo de texto/codigo JA EXISTENTE (relatorio .md, script .py, dump .sql)
para download — sem `cp` manual ao diretorio servido:

```bash
# Entregar um script .py
python exportar.py --formato texto --arquivo /tmp/piloto.py --nome piloto

# Entregar um relatorio .md (formato `md` segue valido como alias)
python exportar.py --formato md --arquivo /tmp/relatorio.md --nome relatorio
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

### Excel com MULTIPLAS abas
Para relatorios com varias secoes (ex: aba 1 = principais, aba 2 = bloqueados,
aba 3 = complementar), envie `{"abas": [...]}` em vez de `{"dados": [...]}`:
```bash
source .venv/bin/activate && \
echo '{"abas": [
  {"titulo": "Fantasmas Ativos", "dados": [{"nome": "A", "valor": 10.5}]},
  {"titulo": "Bloqueados", "dados": [{"id": 1}], "colunas": ["id"]},
  {"titulo": "Sem Vinculo", "dados": [{"user": "x", "email": "x@y.z"}]}
]}' | \
python .claude/skills/exportando-arquivos/scripts/exportar.py \
  --formato excel \
  --nome relatorio_vinculacao
```
Cada aba = `{titulo, dados, colunas?}`. Titulo truncado a 31 chars; duplicatas recebem
sufixo. So o Excel suporta multi-abas (csv/json usam `{"dados": [...]}`).

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

- Arquivos salvos em `$AGENTE_FILES_ROOT/agente_files/default/` (default `/tmp/agente_files/default/`) com UUID no nome
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

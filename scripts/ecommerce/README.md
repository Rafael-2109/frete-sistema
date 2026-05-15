# scripts/ecommerce

Migracao do site Motochefe Maringa (Tray Commerce) -> Bagy.

## Ordem correta de execucao

| # | Fase | Script | Output |
|---|------|--------|--------|
| 1 | **XEROX visual** (mirror completo) | `bash xerox_site.sh` | `mirror/` (HTML, CSS, JS, imagens) |
| 2 | **Extrair tema** (CSS, tokens, fontes) | `python extract_theme.py` | `tema_referencia/` (CSS pronto + assets) |
| 2b | **Preview do XEROX no proprio sistema** | (ja integrado) | `/ecommerce-preview/` no menu MotoChefe |
| 3 | **Setup Bagy** (manual, no painel) | — | conta + plano Escala + tema base + CSS custom + fontes + imagens |
| 4 | **Exportar catalogo** | `python export_tray_to_bagy.py` | `output/produtos_bagy.csv` (+ auxiliares) |
| 5 | **Importar catalogo na Bagy** (manual) | — | produtos no ar |
| 6 | **Cadastrar variacoes** dos 29 produtos (manual) | — | variantes completas |
| 7 | **Integracao com frete_sistema** (futuro) | `app/ecommerce/` (a criar) | webhooks pedido + sync estoque |

### Fase 2b — Preview no proprio sistema

Apos rodar `xerox_site.sh`, o XEROX fica acessivel via Flask em
`http://localhost:5000/ecommerce-preview/` (link no menu MotoChefe -> Preview Site).

- **Apenas DEV**: em prod o `mirror/` nao existe (gitignored), retorna 503
- **Login obrigatorio** (qualquer usuario autenticado)
- **URLs reescritas on-the-fly**: links absolutos do site original viram `/ecommerce-preview/...`
- **Charset convertido**: HTML ISO-8859-1 -> UTF-8
- **Path traversal bloqueado** (`safe_join`)
- **Tolerancia a wget caotico**: glob resolve variantes com query string e sufixos extras
- **Codigo**: `app/ecommerce_preview/` (~200 LOC, modulo TEMPORARIO — remove apos Bagy)

> **Por que esta ordem importa**: a Bagy NAO aceita upload direto de tema HTML/CSS pronto.
> Ela tem editor visual + slot CSS custom + secoes HTML. O XEROX serve como **referencia**
> para reconstruir o visual usando os mecanismos da Bagy.

---

## Scripts disponiveis

### 1. `xerox_site.sh` — Mirror completo do site

```bash
bash scripts/ecommerce/xerox_site.sh
# ou para outra loja:
bash scripts/ecommerce/xerox_site.sh https://outra-loja-tray.com.br
```

**O que baixa**:
- Home + paginas de categoria + paginas de produto (depth=3)
- CSS, JS, fontes (CDN tcdn.com.br + Google Fonts)
- Imagens de produto (CDN tcdn.com.br/img/img_prod/...)
- Banners, logo, icones do tema
- Paginas institucionais (quem-somos, contato, politica, etc.)

**O que NAO baixa**:
- Carrinho, checkout, login, cadastro (paginas dinamicas — recriar na Bagy)
- Scripts de tracking (GA, GTM — reconfigurar na Bagy)
- Resultados de busca, filtros, paginacao

**Limites**: 500MB quota, 2MB/s rate limit, 30s timeout, 0.5s wait entre requests.

**Output**: `scripts/ecommerce/mirror/`

### 2. `extract_theme.py` — Extrai tema para reaplicar na Bagy

```bash
python scripts/ecommerce/extract_theme.py
python scripts/ecommerce/extract_theme.py --mirror-dir /caminho/mirror
```

**Output em `scripts/ecommerce/tema_referencia/`**:

| Arquivo | Conteudo | Uso na Bagy |
|---------|----------|-------------|
| `css_custom_bagy.css` | CSS consolidado pronto para colar | Editor visual -> Configuracoes -> CSS customizado |
| `design_tokens.json` | Cores, fontes, breakpoints (`--color_primary: #f4c400`) | Referencia para cores no editor visual |
| `fontes.txt` | Fontes Google detectadas (Montserrat) | Editor visual -> Tipografia |
| `imagens_tema/` | Logo, banners, icones | Upload manual (Editor visual -> Imagens) |
| `html_referencia/` | HTML das paginas-chave | Copiar texto institucional |
| `inventario.txt` | Relatorio textual de tudo encontrado | Checklist de migracao |

### 3. `export_tray_to_bagy.py` — Exporta catalogo de produtos

```bash
python scripts/ecommerce/export_tray_to_bagy.py
python scripts/ecommerce/export_tray_to_bagy.py --quick  # sem descricao rica
```

**Output em `scripts/ecommerce/output/`**:

| Arquivo | Linhas | Uso |
|---------|--------|-----|
| `produtos_bagy.csv` | 53 | Importar via painel Bagy: Produtos -> Importar |
| `categorias.csv` | 9 | Criar ANTES no painel Bagy (1 e A_CLASSIFICAR — revisar 6 produtos) |
| `marcas.csv` | 9 | Criar ANTES no painel Bagy |
| `imagens.csv` | 171 | Bagy puxa direto da URL CDN |
| `produtos_com_variacao.csv` | 29 | Variantes manual (API publica Tray nao expoe atributos) |
| `tray_raw_dump.json` | — | Referencia / re-export |

**Bugs ja corrigidos durante self-test**:
- `price_compare="0"` -> string vazia para produtos sem promocao
- `price` <-> `price_compare` invertidos (mapeamento Tray -> Bagy)
- HTML entities (`&ccedil;`) decodificadas
- Slugs genericos (`todos/...`, sem prefixo) sinalizados como `A_CLASSIFICAR`

---

## Limitacoes conhecidas

### XEROX (xerox_site.sh)
- **Reject regex amplo**: pode pegar links genericos com palavras "checkout"/"login" no slug. Auditar `mirror/` antes de usar.
- **CSS minificado**: arquivos vem do CDN minificados (1 linha). `extract_theme.py` nao reformata. Use prettier/cssbeautify se quiser editar.
- **JS proprietario Tray**: scripts como `priceRebuilder`, `cartService` sao do Tray e NAO rodam fora dele. **Nao copiar** para Bagy.

### Extract theme (extract_theme.py)
- **Heuristica de imagens de tema**: filtra por keywords (logo, banner, icon). Pode pegar/perder algumas. Revisar `imagens_tema/`.
- **Design tokens**: extrai apenas variaveis `--xxx: yyy;`. Tema pode usar SASS variables compiladas (sem `--` no output) — invisiveis para o regex.

### Catalogo (export_tray_to_bagy.py)
- **Variacoes**: 29 produtos com `has_variation=1`. API publica Tray nao expoe atributos das variantes (`/web_api/products/{id}/variants` requer OAuth). Cadastrar manualmente ou pagar API Bagy (R$ 99/mes).
- **Dimensoes** (peso/altura/largura/profundidade): nao expostas na API publica. Vazio no CSV. Preencher antes do go-live (calculo de frete depende).
- **Header CSV Bagy**: nomes baseados em pesquisa publica da doc, nao em template baixado. Validar contra modelo oficial (painel Bagy -> Produtos -> Importar -> Baixar modelo) antes do primeiro import.

---

## Custos estimados

| Item | Mensal |
|------|--------|
| Bagy plano Escala (acesso CSS) | R$ 119 (1o ano) -> R$ 199 |
| Bagy API REST (integracao com frete_sistema) | R$ 99 |
| Hospedagem de imagens | incluso no plano Bagy |
| **Total** | **R$ 218 (1o ano) -> R$ 298** |

---

## Dependencias

- `wget` 1.21+ (XEROX)
- Python 3.10+ (`requests`, `beautifulsoup4` ja em `requirements.txt`)
- `bash` (xerox_site.sh)

Nenhum dos scripts depende do Flask app (`create_app()`) — todos sao standalone.

---

## Replicar para outras filiais (futuro)

Se houver outras lojas Motochefe a serem migradas, basta rodar:

```bash
bash scripts/ecommerce/xerox_site.sh https://outra-filial.com.br
python scripts/ecommerce/extract_theme.py --mirror-dir mirror_outra
python scripts/ecommerce/export_tray_to_bagy.py \
    --store-url https://outra-filial.com.br \
    --output-dir output_outra
```

Os 3 scripts aceitam parametros para isolar saidas e processar lojas diferentes
sem conflito.

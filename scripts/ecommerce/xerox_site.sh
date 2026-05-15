#!/usr/bin/env bash
#
# XEROX completo do site Tray (Motochefe Maringa) -> referencia visual
# para reconstrucao na Bagy.
#
# Baixa: HTML de paginas (home + categorias + produtos + institucionais),
#        CSS/JS do tema (CDN tcdn.com.br),
#        imagens (produtos, banners, icones),
#        fontes (Google Fonts).
#
# NAO baixa: paginas dinamicas (carrinho, checkout, login, busca, filtros),
#            scripts de tracking (GA, GTM — recriar na Bagy do zero).
#
# Uso:
#   bash scripts/ecommerce/xerox_site.sh
#   bash scripts/ecommerce/xerox_site.sh https://outra-loja-tray.com.br
#
# Output:
#   scripts/ecommerce/mirror/
#     ├── www.motochefemaringa.com.br/  (HTML pages)
#     ├── images.tcdn.com.br/           (CSS, JS, images)
#     └── fonts.googleapis.com/         (CSS de fontes)
#

set -euo pipefail

STORE_URL="${1:-https://www.motochefemaringa.com.br}"
OUTPUT_DIR="${2:-$(dirname "$0")/mirror}"
LOG_FILE="${OUTPUT_DIR}/wget.log"

# Hosts permitidos: site original + CDNs do tema/imagens + Google Fonts
DOMAINS="www.motochefemaringa.com.br,images.tcdn.com.br,fonts.googleapis.com,fonts.gstatic.com"

# Reject regex: paginas dinamicas que NAO interessam para o XEROX
# (carrinho, checkout, login, busca, sessao PHP, queries com query string)
REJECT_REGEX='(carrinho|pedido|checkout|cart|comparador|transID|pag_parcelado|logout|login|cadastro|central-do-cliente|busca|search|filtro|wishlist|comparar|transID|recovery|pag_seguro|webhooks?|verifica|empresa-info|skype|update_carrinho)'

# Header HTTP de browser real (Tray bloqueia user-agents genericos)
USER_AGENT='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

mkdir -p "${OUTPUT_DIR}"

echo "=== XEROX site Tray ==="
echo "Origem:    ${STORE_URL}"
echo "Destino:   ${OUTPUT_DIR}"
echo "Dominios:  ${DOMAINS}"
echo "Inicio:    $(date -Iseconds)"
echo

# Limites de seguranca:
#   --level=3       : home -> categoria -> produto (suficiente para XEROX)
#   --quota=500m    : teto de 500MB (catalogo Motochefe estimado em ~80MB)
#   --limit-rate=2m : 2MB/s (cortesia com servidor)
#   --wait=0.5      : pausa entre requests (evita rate limit Azion)
#   --random-wait   : aleatoriza para parecer humano
wget \
    --recursive \
    --level=3 \
    --convert-links \
    --adjust-extension \
    --page-requisites \
    --no-parent \
    --span-hosts \
    --domains="${DOMAINS}" \
    --reject-regex="${REJECT_REGEX}" \
    --exclude-directories=/loja \
    --user-agent="${USER_AGENT}" \
    --wait=0.5 \
    --random-wait \
    --limit-rate=2m \
    --quota=500m \
    --tries=2 \
    --timeout=30 \
    --no-verbose \
    -o "${LOG_FILE}" \
    -P "${OUTPUT_DIR}" \
    "${STORE_URL}/" \
    || true   # wget retorna != 0 quando rejeita arquivos por --reject-regex (nao e erro real)

echo
echo "=== Concluido ==="
echo "Fim:       $(date -Iseconds)"
echo "Tamanho:   $(du -sh "${OUTPUT_DIR}" | cut -f1)"
echo "Arquivos:  $(find "${OUTPUT_DIR}" -type f | wc -l)"
echo "Log:       ${LOG_FILE}"
echo
echo "Estrutura:"
find "${OUTPUT_DIR}" -maxdepth 2 -type d | sort | sed 's|^|  |'
echo
echo "Proximo passo: python scripts/ecommerce/extract_theme.py"

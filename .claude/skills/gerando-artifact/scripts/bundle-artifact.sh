#!/bin/bash
#
# bundle-artifact.sh — Empacota projeto Vite/React em bundle.html auto-contido.
#
# Adaptado de anthropics/skills/web-artifacts-builder/scripts/bundle-artifact.sh
# Diferenca: npm em vez de pnpm; output path absoluto opcional via $BUNDLE_OUT.
#
# Uso (rodar do raiz do projeto):
#   bash bundle-artifact.sh
#
# Variaveis de ambiente:
#   BUNDLE_OUT  Opcional. Caminho absoluto de output (default: ./bundle.html)

set -e

OUTPUT_PATH="${BUNDLE_OUT:-bundle.html}"

# ===== Validacao =====
if [ ! -f "package.json" ]; then
  echo "ERRO: package.json nao encontrado. Rode do raiz do projeto." >&2
  exit 1
fi

if [ ! -f "index.html" ]; then
  echo "ERRO: index.html nao encontrado." >&2
  exit 2
fi

echo "[bundle] Output destino: $OUTPUT_PATH"

# ===== Instalar deps de bundling =====
# Pin de versao deliberado:
#   - parcel + @parcel/config-default DEVEM bater EXATAMENTE (Parcel resolve
#     @parcel/config-default via require interno do @parcel/core; se npm faz
#     hoisting estranho com latest, parcel acha um stub e falha com
#     "Cannot find extended parcel config" mesmo apos npm install OK).
#   - --legacy-peer-deps evita falhas silenciosas de peer dep com Vite/TS recente.
#   - --no-audit --no-fund encurta o install em alguns segundos (acumula em prod).
PARCEL_VERSION="2.12.0"
# parcel-resolver-tspaths e html-inline pinados em ultima versao publicada
# (ambos sao pacotes inativos — pinar elimina variacao futura se autor publicar
# versao quebrada ou registry deprecar).
RESOLVER_TSPATHS_VERSION="0.0.9"
HTML_INLINE_VERSION="1.2.0"
echo "[bundle] Instalando parcel@$PARCEL_VERSION + deps..."
npm install -D \
  --legacy-peer-deps --no-audit --no-fund \
  "parcel@$PARCEL_VERSION" \
  "@parcel/config-default@$PARCEL_VERSION" \
  "parcel-resolver-tspaths@$RESOLVER_TSPATHS_VERSION" \
  "html-inline@$HTML_INLINE_VERSION"

# ===== Validacao pos-install =====
# Falha cedo com mensagem clara se @parcel/config-default nao foi resolvido
# para o top-level node_modules. Sintoma do bug original: parcel build retornava
# "Cannot find module @parcel/config-default" apos npm install exit 0.
if [ ! -d "node_modules/@parcel/config-default" ]; then
  echo "ERRO: node_modules/@parcel/config-default ausente apos npm install." >&2
  echo "[bundle] Conteudo de node_modules/@parcel/:" >&2
  ls -la node_modules/@parcel/ >&2 2>/dev/null || echo "(diretorio nao existe)" >&2
  echo "[bundle] node_modules/parcel/node_modules/@parcel/ (caso de nested install):" >&2
  ls -la node_modules/parcel/node_modules/@parcel/ >&2 2>/dev/null || echo "(diretorio nao existe)" >&2
  exit 4
fi
echo "[bundle] OK: @parcel/config-default em node_modules/@parcel/config-default"

# ===== Parcel config com path alias =====
if [ ! -f ".parcelrc" ]; then
  echo "[bundle] Criando .parcelrc..."
  cat > .parcelrc << 'EOF'
{
  "extends": "@parcel/config-default",
  "resolvers": ["parcel-resolver-tspaths", "..."]
}
EOF
fi

# ===== Clean build anterior =====
echo "[bundle] Limpando dist anterior..."
rm -rf dist bundle.html

# ===== Build com Parcel =====
echo "[bundle] Buildando com Parcel..."
npx parcel build index.html --dist-dir dist --no-source-maps

# ===== Inline tudo =====
echo "[bundle] Inlining assets em HTML unico..."
npx html-inline dist/index.html > "$OUTPUT_PATH"

# ===== Validar =====
if [ ! -f "$OUTPUT_PATH" ]; then
  echo "ERRO: bundle.html nao foi gerado." >&2
  exit 3
fi

# Sanity check: bundle deve conter JS inlined (nao apenas <script src=>).
# html-inline e pacote inativo ha 10 anos — se Parcel mudar formato de output
# no futuro, queremos falha imediata em vez de bundle quebrado em prod.
if ! grep -qE '<script[^>]*>[^<]' "$OUTPUT_PATH"; then
  echo "ERRO: bundle.html nao contem JS inlined (apenas <script src= externo)." >&2
  echo "[bundle] Inspecionar tags <script> no output:" >&2
  grep -oE '<script[^>]*[/>]' "$OUTPUT_PATH" | head -5 >&2
  exit 5
fi

FILE_SIZE=$(du -b "$OUTPUT_PATH" | cut -f1)
FILE_SIZE_HUMAN=$(du -h "$OUTPUT_PATH" | cut -f1)

echo "[bundle] OK — $OUTPUT_PATH ($FILE_SIZE_HUMAN, $FILE_SIZE bytes)"

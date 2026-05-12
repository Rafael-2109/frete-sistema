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
echo "[bundle] Instalando parcel + html-inline..."
npm install -D parcel @parcel/config-default parcel-resolver-tspaths html-inline

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

FILE_SIZE=$(du -b "$OUTPUT_PATH" | cut -f1)
FILE_SIZE_HUMAN=$(du -h "$OUTPUT_PATH" | cut -f1)

echo "[bundle] OK — $OUTPUT_PATH ($FILE_SIZE_HUMAN, $FILE_SIZE bytes)"

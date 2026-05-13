#!/bin/bash
#
# bundle-artifact.sh — Empacota projeto Vite/React em bundle.html auto-contido.
#
# Migrado para pnpm em 2026-05-13 (skill oficial Anthropic web-artifacts-builder).
#
# Pista diagnostica que motivou a migracao:
#   * funcionava em DEV local com npm
#   * falhava SO em prod (Render) com npm
# A simetria "dev OK / prod fail" revela que a causa raiz e AMBIENTE,
# nao codigo — npm hoisting heuristico + cache de tarball mutavel em FS
# peculiar do Render causavam exit 0 com node_modules/@parcel/ vazio.
#
# Diferenca vs npm: pnpm usa CAS store (content-addressable) com hash validation
# e hoisting deterministico via .pnpm/<pkg>@<ver>/node_modules/<pkg> symlinks.
# Mesmo layout em qualquer ambiente — elimina a divergencia dev/prod.
#
# Resolve bug onde `npm install` retornava exit 0 mas
# node_modules/@parcel/config-default ficava AUSENTE (3 retries falhavam
# identicamente — ver logs srv-d2muidggjchc73d4segg 2026-05-13 11:36:44).
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

# ===== Garantir pnpm =====
# Node 20+ vem com corepack built-in. Se pnpm nao esta no PATH, ativar via
# corepack (start_worker_render.sh ja faz isso, mas defesa em profundidade).
if ! command -v pnpm &> /dev/null; then
  echo "[bundle] pnpm nao encontrado — tentando corepack enable..."
  if command -v corepack &> /dev/null; then
    corepack enable 2>&1 | tail -5
    corepack prepare pnpm@latest --activate 2>&1 | tail -5
  else
    echo "ERRO: pnpm e corepack ausentes. Adicionar 'corepack enable' ao start." >&2
    exit 2
  fi
fi

# ===== Diagnostico de ambiente =====
echo "[bundle] === DIAGNOSTICO ==="
echo "[bundle] PWD:    $PWD"
echo "[bundle] Output: $OUTPUT_PATH"
echo "[bundle] Node:   $(command -v node 2>/dev/null || echo 'NAO ENCONTRADO') ($(node -v 2>&1))"
echo "[bundle] pnpm:   $(command -v pnpm 2>/dev/null || echo 'NAO ENCONTRADO') ($(pnpm -v 2>&1))"
echo "[bundle] disk:   $(df -h . 2>&1 | tail -1 | awk '{print $4" free of "$2}')"
echo "[bundle] pnpm store: $(pnpm store path 2>&1 | tail -1)"
echo "[bundle] === FIM DIAGNOSTICO ==="

# ===== Instalar deps de bundling (Parcel + plugins) =====
# Pinning de versao deliberado (evita variacao entre builds):
#   - parcel + @parcel/config-default DEVEM bater EXATAMENTE (Parcel resolve
#     @parcel/config-default via require interno; descasamento → "Cannot find
#     extended parcel config").
#   - parcel-resolver-tspaths + html-inline sao pacotes inativos — pinar evita
#     surpresa se autor publicar versao quebrada ou registry deprecar.
PARCEL_VERSION="2.12.0"
RESOLVER_TSPATHS_VERSION="0.0.9"
HTML_INLINE_VERSION="1.2.0"

echo "[bundle] Instalando Parcel + plugins via pnpm..."
pnpm add -D \
  "parcel@$PARCEL_VERSION" \
  "@parcel/config-default@$PARCEL_VERSION" \
  "parcel-resolver-tspaths@$RESOLVER_TSPATHS_VERSION" \
  "html-inline@$HTML_INLINE_VERSION"

# ===== Sanity check: deps criticas presentes =====
# IMPORTANTE: pnpm hoista apenas deps DIRETAS no top-level node_modules/.
# Transitivas (ex: @parcel/core, dep de @parcel/config-default) ficam APENAS
# em .pnpm/<pkg>@<ver>/node_modules/<pkg>/ — NAO ha symlink top-level.
# Validar transitivas via `node -e require.resolve(...)` (resolution Node real).
echo "[bundle] Validando deps diretas no top-level node_modules/..."
for pkg in "@parcel/config-default" "parcel" "parcel-resolver-tspaths" "html-inline"; do
  if [ ! -e "node_modules/$pkg" ]; then
    echo "ERRO: node_modules/$pkg AUSENTE apos pnpm install." >&2
    echo "[bundle] === DIAGNOSTICO POS-FALHA ===" >&2
    echo "[bundle] node_modules/@parcel/ (top-level):" >&2
    ls -la node_modules/@parcel/ >&2 2>/dev/null || echo "(nao existe)" >&2
    echo "[bundle] node_modules/.pnpm/ entries (primeiras 20):" >&2
    ls node_modules/.pnpm/ 2>&1 | head -20 >&2 || echo "(.pnpm/ nao existe)" >&2
    echo "[bundle] pnpm list parcel deps:" >&2
    pnpm list parcel @parcel/config-default 2>&1 | head -15 >&2
    echo "[bundle] disk apos install: $(df -h . | tail -1)" >&2
    exit 4
  fi
done

# @parcel/core e dep transitive de @parcel/config-default — NAO valida via
# `node -e require.resolve()` porque pnpm strict mode nao hoista transitivas
# para o top-level. Confirma via pnpm list (le pnpm-lock.yaml + .pnpm/).
echo "[bundle] Validando @parcel/core via pnpm list..."
if ! pnpm list --depth=Infinity @parcel/core 2>/dev/null | grep -q '@parcel/core'; then
  echo "ERRO: @parcel/core nao instalado — Parcel vai falhar em build." >&2
  echo "[bundle] node_modules/.pnpm/@parcel+core* entries:" >&2
  ls node_modules/.pnpm/ 2>&1 | grep -i 'parcel.core' >&2 || echo "(nenhum)" >&2
  exit 4
fi
echo "[bundle] OK: deps diretas + @parcel/core presentes."

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
pnpm exec parcel build index.html --dist-dir dist --no-source-maps

# ===== Inline tudo =====
echo "[bundle] Inlining assets em HTML unico..."
pnpm exec html-inline dist/index.html > "$OUTPUT_PATH"

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

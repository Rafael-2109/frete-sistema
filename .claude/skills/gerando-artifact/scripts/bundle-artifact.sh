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

# ===== Diagnostico de ambiente =====
# Capturar info que ajuda a debugar falhas Render-especificas (where node, npm
# version, cwd, disk free, npm cache config). Custa <100ms e e essencial para
# triagem quando o install falha silenciosamente.
echo "[bundle] === DIAGNOSTICO ==="
echo "[bundle] PWD: $PWD"
echo "[bundle] Node: $(command -v node 2>/dev/null || echo 'NAO ENCONTRADO') ($(node -v 2>&1))"
echo "[bundle] npm:  $(command -v npm 2>/dev/null || echo 'NAO ENCONTRADO') ($(npm -v 2>&1))"
echo "[bundle] disk: $(df -h . 2>&1 | tail -1 | awk '{print $4" free of "$2}')"
echo "[bundle] npm cache: $(npm config get cache 2>&1)"
echo "[bundle] === FIM DIAGNOSTICO ==="

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

# Cache npm DEDICADO por build (evita corrupcao cross-job no Render, onde
# multiplos workers podem rodar `npm install` paralelo no mesmo cache global e
# corromper o tarball cache → install retorna 0 mas escreve dir vazio).
NPM_CACHE_DIR="$(mktemp -d -t npm-cache-XXXXXX)"
trap 'rm -rf "$NPM_CACHE_DIR" 2>/dev/null || true' EXIT
echo "[bundle] npm cache dedicado: $NPM_CACHE_DIR"

# Helper: install + valida. $1=descricao curta, $2=pkg-alvo, $@(3+)=args de npm install.
# Retorna 0 se OK, > 0 se falhou.
# CUIDADO: usa PIPESTATUS para pegar exit code do `npm install`, NAO do `tail`
# (pipeline retorna exit do ultimo comando por padrao). `set +e` local porque
# o script tem `set -e` global e a funcao precisa retornar codigo de erro
# para o caller fazer fallback.
_npm_install_and_validate() {
  local desc="$1"; shift
  local target_pkg="$1"; shift
  echo "[bundle] ($desc) npm install $*"
  set +e
  npm install --cache "$NPM_CACHE_DIR" "$@" 2>&1 | tail -25
  local rc=${PIPESTATUS[0]}
  set -e
  if [ "$rc" -ne 0 ]; then
    echo "[bundle] ($desc) npm install exit=$rc" >&2
    return 1
  fi
  if [ ! -d "node_modules/$target_pkg" ]; then
    echo "[bundle] ($desc) node_modules/$target_pkg AUSENTE apos install" >&2
    return 2
  fi
  echo "[bundle] ($desc) OK: node_modules/$target_pkg presente"
  return 0
}

# ===== ETAPA 1: parcel + @parcel/config-default (CRITICOS) =====
# Instalar isoladamente os dois pacotes que JA falharam em prod, sem misturar
# com plugins inativos (resolver-tspaths/html-inline) que podem causar
# resolucao estranha.
echo "[bundle] [1/3] Instalando parcel + @parcel/config-default..."
_npm_install_and_validate \
  "parcel-core" \
  "@parcel/config-default" \
  -D --legacy-peer-deps --no-audit --no-fund \
  "parcel@$PARCEL_VERSION" \
  "@parcel/config-default@$PARCEL_VERSION" \
  || {
    # ===== FALLBACK A: limpar cache npm + retry =====
    # Cache npm corrompido e a hipotese #1 do bug Render. Limpar + reinstalar.
    echo "[bundle] Fallback A: limpar npm cache + retry" >&2
    npm cache clean --force --cache "$NPM_CACHE_DIR" 2>&1 | tail -5 >&2 || true
    rm -rf node_modules/@parcel node_modules/parcel 2>/dev/null || true
    _npm_install_and_validate \
      "parcel-core-retry" \
      "@parcel/config-default" \
      -D --legacy-peer-deps --no-audit --no-fund --force \
      "parcel@$PARCEL_VERSION" \
      "@parcel/config-default@$PARCEL_VERSION" \
      || {
        # ===== FALLBACK B: install isolado SEM package-lock =====
        # Hipotese: package-lock.json do Vite causa hoisting estranho com Parcel.
        # `--no-package-lock --no-save` faz npm puro: baixa tarball, extrai em
        # node_modules/, sem tocar package.json/lock.
        echo "[bundle] Fallback B: install sem package-lock + sem save" >&2
        _npm_install_and_validate \
          "parcel-isolated" \
          "@parcel/config-default" \
          --no-package-lock --no-save --no-audit --no-fund --legacy-peer-deps \
          "parcel@$PARCEL_VERSION" \
          "@parcel/config-default@$PARCEL_VERSION" \
          || {
            # ===== DIAGNOSTICO FINAL ANTES DE FALHAR =====
            echo "ERRO: node_modules/@parcel/config-default ausente apos 3 tentativas." >&2
            echo "[bundle] === DIAGNOSTICO POS-FALHA ===" >&2
            echo "[bundle] node_modules/@parcel/:" >&2
            ls -la node_modules/@parcel/ >&2 2>/dev/null || echo "(nao existe)" >&2
            echo "[bundle] node_modules/parcel/node_modules/@parcel/:" >&2
            ls -la node_modules/parcel/node_modules/@parcel/ >&2 2>/dev/null || echo "(nao existe)" >&2
            echo "[bundle] node_modules/ entries (primeiras 30):" >&2
            ls node_modules/ 2>&1 | head -30 >&2
            echo "[bundle] npm ls @parcel/config-default:" >&2
            npm ls @parcel/config-default 2>&1 | head -10 >&2
            echo "[bundle] disk apos install: $(df -h . | tail -1)" >&2
            exit 4
          }
      }
  }

# ===== ETAPA 2: plugins (resolver-tspaths + html-inline) =====
echo "[bundle] [2/3] Instalando plugins Parcel..."
_npm_install_and_validate \
  "parcel-plugins" \
  "parcel-resolver-tspaths" \
  -D --legacy-peer-deps --no-audit --no-fund \
  "parcel-resolver-tspaths@$RESOLVER_TSPATHS_VERSION" \
  "html-inline@$HTML_INLINE_VERSION" \
  || {
    echo "ERRO: falha instalando parcel-resolver-tspaths/html-inline." >&2
    exit 6
  }

# ===== ETAPA 3: validacao final consolidada =====
echo "[bundle] [3/3] Validando install final..."
for pkg in "@parcel/config-default" "@parcel/core" "parcel" "parcel-resolver-tspaths" "html-inline"; do
  if [ ! -d "node_modules/$pkg" ]; then
    echo "ERRO: node_modules/$pkg ausente apos install completo." >&2
    exit 4
  fi
done
echo "[bundle] OK: todas as 5 deps de bundling presentes em node_modules/"

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

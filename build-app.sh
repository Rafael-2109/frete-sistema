#!/bin/bash

# 🚀 SCRIPT DE BUILD - RASTREAMENTO NACOM APP
# Automatiza todo o processo de build do APK

set -e  # Para na primeira erro

echo "================================================"
echo "🚀 BUILD RASTREAMENTO NACOM - APP ANDROID"
echo "================================================"
echo ""

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funções auxiliares
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. Verificar dependências
log_info "Verificando dependências..."

if ! command -v npm &> /dev/null; then
    log_error "npm não encontrado. Instale Node.js primeiro."
    exit 1
fi

if ! command -v npx &> /dev/null; then
    log_error "npx não encontrado. Instale Node.js primeiro."
    exit 1
fi

log_success "Dependências OK"

# 2. Instalar/atualizar packages npm
log_info "Instalando/atualizando packages npm..."
npm install
log_success "Packages npm instalados"

# 3. Sincronizar código web → Android
log_info "Sincronizando código web para Android..."
npx cap sync android
log_success "Código sincronizado"

# 4. Build APK Debug
log_info "Compilando APK (modo debug)..."
cd android
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    log_success "APK compilado com sucesso!"
else
    log_error "Falha ao compilar APK"
    exit 1
fi

cd ..

# 5. Localizar APK
APK_PATH="android/app/build/outputs/apk/debug/app-debug.apk"

if [ -f "$APK_PATH" ]; then
    log_success "APK gerado em: $APK_PATH"

    # Informações do APK
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    log_info "Tamanho: $APK_SIZE"

    # Copiar para raiz do projeto
    cp "$APK_PATH" "rastreamento-nacom-debug.apk"
    log_success "APK copiado para: rastreamento-nacom-debug.apk"
else
    log_error "APK não encontrado!"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ BUILD CONCLUÍDO COM SUCESSO!"
echo "================================================"
echo ""
echo "📱 APK Gerado:"
echo "   └─ rastreamento-nacom-debug.apk ($APK_SIZE)"
echo ""
echo "📲 Para instalar no celular:"
echo "   1. Via USB (ADB):"
echo "      $ adb install rastreamento-nacom-debug.apk"
echo ""
echo "   2. Via Arquivo:"
echo "      - Envie o APK por WhatsApp/Email"
echo "      - Abra no celular e instale"
echo ""
echo "🔧 Para testar:"
echo "   - Abra o app no celular"
echo "   - Escaneie QR Code de um embarque"
echo "   - Aceite os termos LGPD"
echo "   - Permita localização (sempre/background)"
echo "   - GPS iniciará automaticamente!"
echo ""
echo "================================================"

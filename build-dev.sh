#!/bin/bash

# 🚀 BUILD DESENVOLVIMENTO - RASTREAMENTO NACOM
# Gera APK apontando para servidor local (http://192.168.1.100:5000)

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================================"
echo -e "${BLUE}🛠️  BUILD DESENVOLVIMENTO - RASTREAMENTO NACOM${NC}"
echo "================================================"
echo ""

# 1. Copiar config de desenvolvimento
echo -e "${BLUE}📋 Configurando para DESENVOLVIMENTO...${NC}"
cp capacitor.config.dev.json capacitor.config.json
echo -e "${GREEN}✅ Config DEV ativado (servidor: http://192.168.1.100:5000)${NC}"
echo ""

# 2. Instalar dependências
echo -e "${BLUE}📦 Instalando dependências npm...${NC}"
npm install
echo -e "${GREEN}✅ Dependências instaladas${NC}"
echo ""

# 3. Sincronizar
echo -e "${BLUE}🔄 Sincronizando código web → Android...${NC}"
npx cap sync android
echo -e "${GREEN}✅ Código sincronizado${NC}"
echo ""

# 4. Build APK Debug
echo -e "${BLUE}🔨 Compilando APK DEBUG...${NC}"
cd android
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ APK compilado com sucesso!${NC}"
else
    echo -e "${YELLOW}❌ Falha ao compilar APK${NC}"
    exit 1
fi

cd ..

# 5. Copiar APK
APK_PATH="android/app/build/outputs/apk/debug/app-debug.apk"

if [ -f "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    cp "$APK_PATH" "rastreamento-nacom-dev.apk"

    echo ""
    echo "================================================"
    echo -e "${GREEN}✅ BUILD DEV CONCLUÍDO!${NC}"
    echo "================================================"
    echo ""
    echo -e "${BLUE}📱 APK Gerado:${NC}"
    echo "   └─ rastreamento-nacom-dev.apk ($APK_SIZE)"
    echo ""
    echo -e "${YELLOW}⚠️  ATENÇÃO: Este APK aponta para:${NC}"
    echo "   http://192.168.1.100:5000"
    echo "   (Servidor de desenvolvimento local)"
    echo ""
    echo -e "${BLUE}📲 Para instalar:${NC}"
    echo "   adb install rastreamento-nacom-dev.apk"
    echo ""
else
    echo -e "${YELLOW}❌ APK não encontrado!${NC}"
    exit 1
fi

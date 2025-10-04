#!/bin/bash

# 🚀 BUILD PRODUÇÃO - RASTREAMENTO NACOM
# Gera APK apontando para servidor de produção (https://sistema-fretes.onrender.com)

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "================================================"
echo -e "${RED}🚀 BUILD PRODUÇÃO - RASTREAMENTO NACOM${NC}"
echo "================================================"
echo ""

# Confirmação
echo -e "${YELLOW}⚠️  ATENÇÃO: Este build será para PRODUÇÃO${NC}"
echo -e "${YELLOW}   Servidor: https://sistema-fretes.onrender.com${NC}"
echo ""
read -p "Continuar? (s/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${BLUE}Build cancelado.${NC}"
    exit 0
fi

# 1. Copiar config de produção
echo ""
echo -e "${BLUE}📋 Configurando para PRODUÇÃO...${NC}"
cp capacitor.config.prod.json capacitor.config.json
echo -e "${GREEN}✅ Config PROD ativado (servidor: https://sistema-fretes.onrender.com)${NC}"
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

# 4. Build APK Debug (para testes)
echo -e "${BLUE}🔨 Compilando APK PRODUÇÃO (debug mode)...${NC}"
cd android
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ APK compilado com sucesso!${NC}"
else
    echo -e "${RED}❌ Falha ao compilar APK${NC}"
    exit 1
fi

cd ..

# 5. Copiar APK
APK_PATH="android/app/build/outputs/apk/debug/app-debug.apk"

if [ -f "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    cp "$APK_PATH" "rastreamento-nacom-prod.apk"

    echo ""
    echo "================================================"
    echo -e "${GREEN}✅ BUILD PRODUÇÃO CONCLUÍDO!${NC}"
    echo "================================================"
    echo ""
    echo -e "${BLUE}📱 APK Gerado:${NC}"
    echo "   └─ rastreamento-nacom-prod.apk ($APK_SIZE)"
    echo ""
    echo -e "${GREEN}✅ Este APK aponta para:${NC}"
    echo "   https://sistema-fretes.onrender.com"
    echo "   (Servidor de PRODUÇÃO)"
    echo ""
    echo -e "${BLUE}📲 Para instalar:${NC}"
    echo "   adb install rastreamento-nacom-prod.apk"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANTE:${NC}"
    echo "   - Distribua apenas para motoristas autorizados"
    echo "   - Certifique-se que o servidor está rodando"
    echo "   - Para build assinado (release), use ./build-release.sh"
    echo ""
else
    echo -e "${RED}❌ APK não encontrado!${NC}"
    exit 1
fi

# Restaurar config dev
echo -e "${BLUE}🔄 Restaurando config de desenvolvimento...${NC}"
cp capacitor.config.dev.json capacitor.config.json
echo -e "${GREEN}✅ Config DEV restaurado${NC}"

#!/bin/bash

# 🔧 SETUP ANDROID SDK - RASTREAMENTO NACOM
# Configura Android SDK após instalação do Android Studio

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "================================================"
echo -e "${BLUE}🔧 SETUP ANDROID SDK${NC}"
echo "================================================"
echo ""

# 1. Verificar se Android Studio está instalado
echo -e "${BLUE}1️⃣  Verificando Android Studio...${NC}"

if command -v android-studio &> /dev/null; then
    echo -e "${GREEN}✅ Android Studio encontrado via snap${NC}"
    ANDROID_STUDIO_PATH=$(which android-studio)
    echo -e "   Localizado em: $ANDROID_STUDIO_PATH"
else
    echo -e "${YELLOW}⚠️  Android Studio não encontrado no PATH${NC}"
    echo ""
    echo "Procurando em locais comuns..."

    # Locais comuns do Android Studio
    POSSIBLE_PATHS=(
        "$HOME/Android/Sdk"
        "/snap/android-studio/current/android-studio/jbr"
        "$HOME/android-studio"
        "/usr/local/android-studio"
    )

    ANDROID_HOME_FOUND=false
    for path in "${POSSIBLE_PATHS[@]}"; do
        if [ -d "$path" ]; then
            echo -e "${GREEN}✅ Encontrado: $path${NC}"
            ANDROID_HOME_CANDIDATE="$path"
            ANDROID_HOME_FOUND=true
            break
        fi
    done

    if [ "$ANDROID_HOME_FOUND" = false ]; then
        echo -e "${RED}❌ Android SDK não encontrado automaticamente${NC}"
        echo ""
        echo -e "${YELLOW}INSTRUÇÕES MANUAIS:${NC}"
        echo "1. Aguarde a instalação do Android Studio terminar"
        echo "2. Abra o Android Studio:"
        echo "   $ android-studio"
        echo ""
        echo "3. No wizard inicial:"
        echo "   - Escolha 'Standard Installation'"
        echo "   - Aguarde download do SDK"
        echo ""
        echo "4. Após instalação, o SDK estará em:"
        echo "   ~/Android/Sdk"
        echo ""
        echo "5. Execute este script novamente:"
        echo "   $ ./setup-android-sdk.sh"
        echo ""
        exit 1
    fi
fi

echo ""

# 2. Detectar localização do Android SDK
echo -e "${BLUE}2️⃣  Detectando Android SDK...${NC}"

# Tentar variável de ambiente primeiro
if [ -n "$ANDROID_HOME" ] && [ -d "$ANDROID_HOME" ]; then
    SDK_PATH="$ANDROID_HOME"
    echo -e "${GREEN}✅ ANDROID_HOME já definido: $SDK_PATH${NC}"
else
    # Procurar em locais padrão
    if [ -d "$HOME/Android/Sdk" ]; then
        SDK_PATH="$HOME/Android/Sdk"
        echo -e "${GREEN}✅ SDK encontrado em: $SDK_PATH${NC}"
    else
        echo -e "${YELLOW}⚠️  SDK não encontrado em $HOME/Android/Sdk${NC}"
        echo ""
        echo "Digite o caminho completo do Android SDK:"
        echo "(Geralmente: $HOME/Android/Sdk)"
        read -p "Caminho: " SDK_PATH

        if [ ! -d "$SDK_PATH" ]; then
            echo -e "${RED}❌ Caminho inválido: $SDK_PATH${NC}"
            exit 1
        fi
    fi
fi

echo ""

# 3. Configurar variáveis de ambiente
echo -e "${BLUE}3️⃣  Configurando variáveis de ambiente...${NC}"

# Adicionar ao .bashrc se não existir
if ! grep -q "ANDROID_HOME" "$HOME/.bashrc"; then
    echo "" >> "$HOME/.bashrc"
    echo "# Android SDK - Configurado automaticamente" >> "$HOME/.bashrc"
    echo "export ANDROID_HOME=$SDK_PATH" >> "$HOME/.bashrc"
    echo "export PATH=\$PATH:\$ANDROID_HOME/platform-tools" >> "$HOME/.bashrc"
    echo "export PATH=\$PATH:\$ANDROID_HOME/cmdline-tools/latest/bin" >> "$HOME/.bashrc"
    echo "export PATH=\$PATH:\$ANDROID_HOME/emulator" >> "$HOME/.bashrc"

    echo -e "${GREEN}✅ Variáveis adicionadas ao ~/.bashrc${NC}"
else
    echo -e "${YELLOW}⚠️  ANDROID_HOME já existe no ~/.bashrc${NC}"
fi

# Exportar para sessão atual
export ANDROID_HOME="$SDK_PATH"
export PATH="$PATH:$ANDROID_HOME/platform-tools"
export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin"

echo -e "${GREEN}✅ Variáveis exportadas para sessão atual${NC}"
echo ""

# 4. Criar android/local.properties
echo -e "${BLUE}4️⃣  Criando android/local.properties...${NC}"

if [ -f "android/local.properties" ]; then
    echo -e "${YELLOW}⚠️  Arquivo já existe, substituindo...${NC}"
fi

echo "## Auto-gerado por setup-android-sdk.sh" > android/local.properties
echo "sdk.dir=$SDK_PATH" >> android/local.properties

echo -e "${GREEN}✅ Arquivo criado com sucesso${NC}"
echo -e "   Conteúdo: sdk.dir=$SDK_PATH"
echo ""

# 5. Verificar Java
echo -e "${BLUE}5️⃣  Verificando Java JDK...${NC}"

if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1)
    echo -e "${GREEN}✅ Java instalado: $JAVA_VERSION${NC}"
else
    echo -e "${RED}❌ Java não encontrado${NC}"
    echo "Instale OpenJDK 17 ou superior:"
    echo "  $ sudo apt install openjdk-17-jdk"
    exit 1
fi

echo ""

# 6. Testar adb
echo -e "${BLUE}6️⃣  Testando ADB (Android Debug Bridge)...${NC}"

if [ -f "$ANDROID_HOME/platform-tools/adb" ]; then
    ADB_VERSION=$("$ANDROID_HOME/platform-tools/adb" version 2>&1 | head -n 1)
    echo -e "${GREEN}✅ ADB disponível: $ADB_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  ADB não encontrado em platform-tools${NC}"
    echo "Execute no Android Studio: SDK Manager > Android SDK > SDK Tools > Android SDK Platform-Tools"
fi

echo ""

# 7. Verificar Gradle
echo -e "${BLUE}7️⃣  Verificando Gradle wrapper...${NC}"

if [ -f "android/gradlew" ]; then
    echo -e "${GREEN}✅ Gradle wrapper presente${NC}"
    chmod +x android/gradlew
    echo -e "${GREEN}✅ Permissões de execução concedidas${NC}"
else
    echo -e "${RED}❌ Gradle wrapper não encontrado${NC}"
    echo "Execute: npx cap sync android"
fi

echo ""
echo "================================================"
echo -e "${GREEN}✅ SETUP CONCLUÍDO!${NC}"
echo "================================================"
echo ""
echo -e "${BLUE}📋 Próximos passos:${NC}"
echo ""
echo "1️⃣  Recarregar variáveis de ambiente:"
echo "   $ source ~/.bashrc"
echo ""
echo "2️⃣  Testar build do APK:"
echo "   $ ./build-dev.sh"
echo ""
echo "3️⃣  Se der erro, reinicie o terminal e tente novamente"
echo ""
echo -e "${YELLOW}💡 DICA:${NC}"
echo "   Para verificar se tudo está OK:"
echo "   $ echo \$ANDROID_HOME"
echo "   (deve mostrar: $SDK_PATH)"
echo ""

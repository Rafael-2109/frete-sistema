#!/bin/bash
# Script para instalar LibreOffice no Render sem sudo
# Usa versão portável que não precisa de permissões de sistema

echo "🚀 Instalando LibreOffice para o Worker do Render..."

# Criar diretório para LibreOffice
LIBREOFFICE_DIR="$HOME/.local/libreoffice"
mkdir -p "$LIBREOFFICE_DIR"

# Baixar LibreOffice Portable (versão sem instalação)
echo "📥 Baixando LibreOffice Portable..."

# Opção 1: Tentar baixar versão AppImage (mais leve)
APPIMAGE_URL="https://download.documentfoundation.org/libreoffice/stable/7.6.3/appimage/LibreOffice-still-x86_64.AppImage"

if command -v wget &> /dev/null; then
    wget -q --show-progress "$APPIMAGE_URL" -O "$LIBREOFFICE_DIR/libreoffice.AppImage"
elif command -v curl &> /dev/null; then
    curl -L "$APPIMAGE_URL" -o "$LIBREOFFICE_DIR/libreoffice.AppImage"
else
    echo "❌ Nem wget nem curl disponíveis. Instalando wget..."
    pip install wget
    python -c "import wget; wget.download('$APPIMAGE_URL', out='$LIBREOFFICE_DIR/libreoffice.AppImage')"
fi

# Verificar se baixou
if [ -f "$LIBREOFFICE_DIR/libreoffice.AppImage" ]; then
    echo "✅ LibreOffice AppImage baixado"

    # Tornar executável
    chmod +x "$LIBREOFFICE_DIR/libreoffice.AppImage"

    # Extrair AppImage (não precisa de FUSE no Render)
    echo "📦 Extraindo LibreOffice..."
    cd "$LIBREOFFICE_DIR"
    ./libreoffice.AppImage --appimage-extract > /dev/null 2>&1

    if [ -d "$LIBREOFFICE_DIR/squashfs-root" ]; then
        echo "✅ LibreOffice extraído com sucesso"

        # Criar script wrapper para facilitar o uso
        cat > "$HOME/.local/bin/libreoffice" << 'EOF'
#!/bin/bash
exec "$HOME/.local/libreoffice/squashfs-root/AppRun" "$@"
EOF

        chmod +x "$HOME/.local/bin/libreoffice"

        # Adicionar ao PATH se necessário
        export PATH="$HOME/.local/bin:$PATH"

        # Testar instalação
        if "$HOME/.local/bin/libreoffice" --version 2>/dev/null | grep -q "LibreOffice"; then
            echo "✅ LibreOffice instalado e funcionando!"
            "$HOME/.local/bin/libreoffice" --version
        else
            echo "⚠️ LibreOffice instalado mas não testado (normal no build)"
        fi
    else
        echo "❌ Erro ao extrair AppImage"

        # Fallback: Tentar usar diretamente sem extrair
        echo "🔄 Tentando configurar para uso direto..."
        ln -sf "$LIBREOFFICE_DIR/libreoffice.AppImage" "$HOME/.local/bin/libreoffice"
    fi
else
    echo "❌ Erro ao baixar LibreOffice"

    # Opção 2: Fallback para versão tar.gz
    echo "🔄 Tentando versão alternativa (tar.gz)..."

    TAR_URL="https://download.documentfoundation.org/libreoffice/stable/7.6.3/deb/x86_64/LibreOffice_7.6.3_Linux_x86-64_deb.tar.gz"

    wget -q --show-progress "$TAR_URL" -O "/tmp/libreoffice.tar.gz" || \
    curl -L "$TAR_URL" -o "/tmp/libreoffice.tar.gz"

    if [ -f "/tmp/libreoffice.tar.gz" ]; then
        echo "📦 Extraindo versão tar.gz..."
        tar -xzf "/tmp/libreoffice.tar.gz" -C "$LIBREOFFICE_DIR"

        # Encontrar o executável
        LIBREOFFICE_BIN=$(find "$LIBREOFFICE_DIR" -name "soffice" -type f 2>/dev/null | head -1)

        if [ -n "$LIBREOFFICE_BIN" ]; then
            ln -sf "$LIBREOFFICE_BIN" "$HOME/.local/bin/libreoffice"
            echo "✅ LibreOffice configurado via tar.gz"
        else
            echo "❌ Executável não encontrado no tar.gz"
        fi

        rm -f "/tmp/libreoffice.tar.gz"
    fi
fi

# Limpar arquivo AppImage original para economizar espaço
if [ -f "$LIBREOFFICE_DIR/libreoffice.AppImage" ] && [ -d "$LIBREOFFICE_DIR/squashfs-root" ]; then
    rm -f "$LIBREOFFICE_DIR/libreoffice.AppImage"
    echo "🧹 AppImage original removido para economizar espaço"
fi

# Verificação final
echo ""
echo "=========================================="
if [ -f "$HOME/.local/bin/libreoffice" ] || [ -L "$HOME/.local/bin/libreoffice" ]; then
    echo "✅ INSTALAÇÃO CONCLUÍDA!"
    echo "LibreOffice está em: $HOME/.local/bin/libreoffice"
    echo ""
    echo "Para usar no Python:"
    echo "  subprocess.run(['$HOME/.local/bin/libreoffice', '--headless', ...])"
else
    echo "❌ INSTALAÇÃO FALHOU"
    echo "LibreOffice não pôde ser instalado no Render"
    echo "Use a alternativa xlsxwriter no código"
fi
echo "=========================================="
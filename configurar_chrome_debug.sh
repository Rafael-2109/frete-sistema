#!/bin/bash

# Script para configurar Chrome com porta de debug para automação do portal

echo "🔧 Configurando Chrome com Debug Port..."

# 1. Fechar todas as instâncias do Chrome
echo "📍 Fechando instâncias existentes do Chrome..."
pkill -f chrome || true
pkill -f chromium || true

# 2. Criar diretório para perfil de debug
CHROME_DEBUG_DIR="/tmp/chrome-debug-profile"
echo "📁 Criando diretório de perfil: $CHROME_DEBUG_DIR"
mkdir -p "$CHROME_DEBUG_DIR"

# 3. Detectar comando do Chrome
if command -v google-chrome &> /dev/null; then
    CHROME_CMD="google-chrome"
elif command -v google-chrome-stable &> /dev/null; then
    CHROME_CMD="google-chrome-stable"
elif command -v chromium-browser &> /dev/null; then
    CHROME_CMD="chromium-browser"
elif command -v chromium &> /dev/null; then
    CHROME_CMD="chromium"
else
    echo "❌ Chrome não encontrado! Instale com:"
    echo "   sudo apt-get install google-chrome-stable"
    exit 1
fi

echo "✅ Usando comando: $CHROME_CMD"

# 4. Iniciar Chrome com debug port
echo "🚀 Iniciando Chrome com debug port 9222..."
echo ""
echo "IMPORTANTE:"
echo "1. Uma nova janela do Chrome será aberta"
echo "2. Faça login manual no portal do Atacadão"
echo "3. Mantenha esta janela aberta enquanto usar o sistema"
echo ""

# Executar Chrome com debug
$CHROME_CMD \
    --remote-debugging-port=9222 \
    --user-data-dir="$CHROME_DEBUG_DIR" \
    --no-first-run \
    --no-default-browser-check \
    --disable-popup-blocking \
    --disable-translate \
    --start-maximized \
    "https://b2b.atacadao.com.br/" &

echo ""
echo "✅ Chrome iniciado com sucesso!"
echo ""
echo "📝 Para verificar se está funcionando:"
echo "   Acesse: http://localhost:9222/json/version"
echo ""
echo "🔐 Próximos passos:"
echo "   1. Faça login no portal do Atacadão"
echo "   2. Navegue até a área de agendamento"
echo "   3. Mantenha a janela aberta"
echo "   4. Use o sistema de fretes normalmente"
echo ""
echo "⚠️  Para parar o Chrome debug, use: pkill -f 'remote-debugging-port=9222'"
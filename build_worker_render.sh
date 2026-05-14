#!/bin/bash
# =====================================================
# BUILD SCRIPT DO WORKER NO RENDER
# Inclui retry agressivo para downloads PyPI.
# =====================================================
#
# Por que existe: o build do worker falhou consistentemente
# em 2026-05-14 por timeout no download do playwright (46.2 MB)
# do PyPI mirror — sempre interrompia em ~9.7 MB.
#
# Solucao: pip --retries 10 --timeout 300 + pre-download do
# playwright antes do install completo, garantindo cache local.
#
# Para usar este script: configurar buildCommand do worker no
# Dashboard Render para `bash build_worker_render.sh` (substitui
# o command inline anterior `pip install -r requirements.txt &&
# python -m playwright install chromium && bash install_libreoffice_render.sh`).

set -e

echo "=========================================="
echo "BUILD WORKER ATACADAO/SENDAS"
echo "=========================================="

# 1. Atualizar pip (resume-retries esta em 25.3+)
echo "Atualizando pip..."
pip install --upgrade pip

# 2. Pre-download do playwright (que falha frequente — baixar isolado)
# Se falhar AQUI nao quebra o build inteiro, retry mais agressivo abaixo.
echo "Pre-baixando playwright (com retry agressivo)..."
for i in 1 2 3 4 5; do
    if pip download --retries 10 --timeout 300 --no-deps --dest /tmp/wheels playwright==1.58.0; then
        echo "Playwright pre-baixado na tentativa $i"
        break
    fi
    echo "Tentativa $i falhou, aguardando 10s..."
    sleep 10
done

# 3. Install full requirements (usa cache do pre-download se OK)
echo "Instalando requirements.txt..."
pip install --retries 10 --timeout 300 \
    --find-links /tmp/wheels \
    -r requirements.txt

# 4. Playwright Chromium
echo "Instalando Playwright Chromium..."
python -m playwright install chromium

# 5. LibreOffice (para conversao docx/xlsx em portal atacadao)
echo "Instalando LibreOffice..."
bash install_libreoffice_render.sh

echo ""
echo "=========================================="
echo "BUILD WORKER CONCLUIDO COM SUCESSO"
echo "=========================================="

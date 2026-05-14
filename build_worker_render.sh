#!/bin/bash
# =====================================================
# BUILD SCRIPT DO WORKER NO RENDER
# =====================================================
#
# CAUSA RAIZ (descoberta 2026-05-14): web (sistema-fretes) tem
# `serviceDetails.cache.profile: no-cache` que limpa cache do build a cada
# deploy; worker NAO tem essa config, entao cache de pip persiste.
#
# Em ~14/05 01:21 UTC o cache do worker corrompeu com wheel PARCIAL
# do playwright-1.58.0 (9.7 MB de 46.2 MB). Builds subsequentes
# encontravam o arquivo no cache e falhavam com 'incomplete-download'
# em LOOP — 12+ builds falhadas seguidas com mesmo tamanho exato.
#
# Solucao via codigo: --no-cache-dir em todos pip install. Garante que
# pip nao usa nem grava cache local — sempre baixa fresh do PyPI.
#
# Solucao alternativa (sem editar este script): no Dashboard, fazer
# Manual Deploy -> "Clear build cache & deploy" para limpar cache 1x.
# Mas se nao adicionar cache.profile=no-cache na config do servico,
# o problema pode reincidir no futuro.

set -e

echo "=========================================="
echo "BUILD WORKER ATACADAO/SENDAS"
echo "=========================================="

# 1. Atualizar pip
echo "Atualizando pip..."
pip install --no-cache-dir --upgrade pip

# 2. Install requirements SEM cache (evita corrupcao por wheels parciais)
echo "Instalando requirements.txt (--no-cache-dir)..."
pip install --no-cache-dir --retries 5 --timeout 180 -r requirements.txt

# 3. Playwright Chromium (usa cache do binario, nao do wheel pip)
echo "Instalando Playwright Chromium..."
python -m playwright install chromium

# 4. LibreOffice (para conversao docx/xlsx em portal atacadao)
echo "Instalando LibreOffice..."
bash install_libreoffice_render.sh

echo ""
echo "=========================================="
echo "BUILD WORKER CONCLUIDO COM SUCESSO"
echo "=========================================="

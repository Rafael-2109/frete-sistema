#!/bin/bash

# Build script para Render com correção de migrações

echo "=== INICIANDO DEPLOY NO RENDER ==="

# 0. Baixar dados de treinamento do Tesseract OCR (para OCR de comprovantes)
# O wheel tesserocr já inclui a lib C compilada. Falta apenas o por.traineddata.
# apt-get não funciona no Render, então baixamos direto do GitHub.
TESSDATA_DIR="/opt/render/project/src/tessdata"
mkdir -p "$TESSDATA_DIR"
echo "Baixando dados Tesseract (por.traineddata)..."
curl -fsSL -o "$TESSDATA_DIR/por.traineddata" \
    "https://github.com/tesseract-ocr/tessdata_fast/raw/main/por.traineddata" \
    && echo "✅ Tesseract tessdata baixado com sucesso em $TESSDATA_DIR" \
    || echo "⚠️ Falha ao baixar tessdata, OCR pode não funcionar"
export TESSDATA_PREFIX="$TESSDATA_DIR"

# 1. Instalar dependências
echo "Instalando dependências..."
pip install -r requirements.txt

# 2. Instalar Playwright e navegadores (para Portal Atacadão)
echo "Instalando Playwright e nest-asyncio..."
pip install playwright nest-asyncio
playwright install chromium
playwright install-deps chromium || echo "Dependências instaladas pelo Render"

# 3. Instalar modelo spaCy português
echo "Instalando modelo spaCy português..."
python -m spacy download pt_core_news_sm || echo "spaCy pode não estar instalado, continuando..."

# 3. Verificar e corrigir migrações
echo "Verificando migrações..."

# Verificar se há múltiplas heads
if flask db heads | grep -q "Multiple head revisions"; then
    echo "Múltiplas heads detectadas, criando merge..."
    flask db merge heads -m "Merge múltiplas heads automaticamente"
fi

# Verificar se há heads não aplicadas
if ! flask db current | grep -q "(head)"; then
    echo "Aplicando migrações..."
    flask db upgrade
else
    echo "Banco já está atualizado"
fi

# 4. Verificar e aplicar migração hora_agendamento
echo "Verificando campo hora_agendamento..."
mkdir -p scripts
python scripts/deploy_render.py || echo "Script de verificação falhou, continuando..."

# 5. Inicializar banco se necessário
echo "Inicializando banco..."
python init_db.py

# 6. Backfill CarVia: preencher icms_aliquota de operacoes antigas via XML.
# Idempotente — so atualiza operacoes com icms_aliquota IS NULL e
# cte_xml_path populado. Recem-corrigido para suportar ICMSOutraUF
# (CFOP 5932/6932, frete prestado por transportador de outra UF).
echo "Backfill icms_aliquota CarVia (idempotente)..."
python scripts/migrations/add_icms_aliquota_carvia_operacoes.py \
    || echo "⚠️ Backfill icms_aliquota falhou, continuando deploy..."

# 7. Migration CarVia Escopo C (2026-04-14): conferencia migra de Sub para Frete.
# Ordem obrigatoria: add fields -> rename aprovacoes -> cc frete_id -> drop sub fields.
# Todas idempotentes (IF EXISTS / IF NOT EXISTS + guards).
# Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md

echo "Migration CarVia 1/4: campos conferencia em carvia_fretes..."
python scripts/migrations/carvia_frete_conferencia_fields.py \
    || echo "⚠️ Migration carvia_frete_conferencia_fields falhou, continuando deploy..."

echo "Migration CarVia 2/4: rename aprovacoes subcontrato -> frete..."
python scripts/migrations/carvia_aprovacoes_rename_frete.py \
    || echo "⚠️ Migration carvia_aprovacoes_rename_frete falhou, continuando deploy..."

echo "Migration CarVia 3/4: frete_id em conta_corrente..."
python scripts/migrations/carvia_cc_frete_id.py \
    || echo "⚠️ Migration carvia_cc_frete_id falhou, continuando deploy..."

echo "Migration CarVia 4/4: drop campos conferencia obsoletos de Sub..."
python scripts/migrations/carvia_drop_sub_conferencia_fields.py \
    || echo "⚠️ Migration carvia_drop_sub_conferencia_fields falhou, continuando deploy..."


echo "Build concluído com sucesso!"


# Linha antiga mantida por compatibilidade (pode ser removida depois)
python aplicar_migracao_render.py || echo "Migration already applied"

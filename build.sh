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

# 7. SessionStore v0.1.64 — tabela claude_session_store (Fase A dual-run).
# Idempotente via IF NOT EXISTS. Ativa mirror automatico quando
# AGENT_SDK_SESSION_STORE_ENABLED=true (feature flag).
echo "Criando tabela claude_session_store (SessionStore v0.1.64 Fase A)..."
python scripts/migrations/2026_04_21_claude_session_store.py \
    || echo "⚠️ Migration claude_session_store falhou, continuando deploy..."

# 8. HORA 23: tabela hora_emprestimo_moto (emprestimo entre lojas).
# Idempotente (CREATE TABLE IF NOT EXISTS + DO $$ guards).
echo "HORA 23: emprestimo entre lojas..."
python scripts/migrations/hora_23_emprestimo_moto.py \
    || echo "⚠️ Migration hora_23 falhou, continuando deploy..."

# 9. HORA 29: unificacao de modelos (N nomes -> 1 canonico).
# Cria hora_modelo_alias + hora_modelo_pendente + ALTER hora_modelo
# (3 cols: merged_em_id, merged_em, merged_por). Idempotente.
echo "HORA 29: unificacao de modelos (alias + pendencias)..."
python scripts/migrations/hora_29_modelo_alias.py \
    || echo "⚠️ Migration hora_29 falhou, continuando deploy..."

# 10b. HORA 34: multiplas formas de pagamento por pedido (1:N) + exige_aut_id.
echo "HORA 34: multiplas formas de pagamento + AUT/ID..."
python scripts/migrations/hora_34_pagamento_multiformas.py \
    || echo "⚠️ Migration hora_34 falhou, continuando deploy..."

# 10c. HORA 35: cleanup de motos vinculadas a aliases mergidos.
echo "HORA 35: cleanup motos em aliases mergidos..."
python scripts/migrations/hora_35_cleanup_alias_motos.py \
    || echo "⚠️ Migration hora_35 falhou, continuando deploy..."

# 10d. HORA 36: campo consumidor_final em hora_venda (NF-e TagPlus).
# Boolean nullable: NULL=infere via doc, TRUE/FALSE=explicito do operador.
# Idempotente (ADD COLUMN IF NOT EXISTS).
echo "HORA 36: campo consumidor_final em hora_venda..."
python scripts/migrations/hora_36_consumidor_final.py \
    || echo "⚠️ Migration hora_36 falhou, continuando deploy..."

# 10. HORA 30: seed inicial de hora_modelo_alias.
# Para cada modelo existente, cria alias NOME_LIVRE com nome_modelo
# + aliases TAGPLUS_CODIGO/TAGPLUS_PRODUTO_ID a partir do legado
# hora_tagplus_produto_map. Tambem cria modelo sentinela DESCONHECIDO
# com aliases para CHASSI_EXTRA_DESCONHECIDO/MODELO_DESCONHECIDO/NAO_INFORMADO
# (evita pendencias em loop em recebimento). Idempotente.
echo "HORA 30: seed de aliases iniciais..."
python scripts/migrations/hora_30_seed_aliases_atuais.py \
    || echo "⚠️ Seed hora_30 falhou, continuando deploy..."

# Migrations motos_assai (01-08): removidas do build apos deploy concluido em
# 2026-05-08. Scripts permanecem em scripts/migrations/ como historico — rodar
# manualmente apenas em fresh install / staging novo (ordem: 02, 01, 07, 08
# DDLs primeiro; depois 03, 04, 05, 06 seeds).

echo "Build concluído com sucesso!"


# Linha antiga mantida por compatibilidade (pode ser removida depois)
python aplicar_migracao_render.py || echo "Migration already applied"

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

# 11. MOTOS ASSAI 02: coluna sistema_motos_assai em usuarios (toggle de acesso).
# Idempotente (DO $$ + IF NOT EXISTS). Roda antes do schema para liberar login
# de usuarios com a flag mesmo se schema falhar.
echo "MOTOS ASSAI 02: coluna sistema_motos_assai em usuarios..."
python scripts/migrations/motos_assai_02_toggle_usuario.py \
    || echo "⚠️ Migration motos_assai_02 falhou, continuando deploy..."

# 12. MOTOS ASSAI 01: schema completo do modulo (16 tabelas assai_*).
# Cadastros, identidade da moto, pipeline pedido->compra->recibo, separacao+NF.
# Idempotente (CREATE TABLE/INDEX IF NOT EXISTS).
echo "MOTOS ASSAI 01: schema 16 tabelas..."
python scripts/migrations/motos_assai_01_schema.py \
    || echo "⚠️ Migration motos_assai_01 falhou, continuando deploy..."

# 13. MOTOS ASSAI 03: seed CD 'Operacao VOE' (single record, campos opcionais).
# Idempotente (skip se ja existe).
echo "MOTOS ASSAI 03: seed CD..."
python scripts/migrations/motos_assai_03_seed_cd.py \
    || echo "⚠️ Seed motos_assai_03 falhou, continuando deploy..."

# 14. MOTOS ASSAI 04: seed 39 lojas Assai (extraidas de 285.xlsx BASE LOJAS).
# Idempotente (skip se numero ja existe).
echo "MOTOS ASSAI 04: seed 39 lojas Assai..."
python scripts/migrations/motos_assai_04_seed_lojas.py \
    || echo "⚠️ Seed motos_assai_04 falhou, continuando deploy..."

# 15. MOTOS ASSAI 05: seed 3 modelos canonicos (X11_MINI, DOT, SOL) + aliases.
# Regex de chassi aprovados em 2026-05-07. Idempotente (skip se codigo existe).
echo "MOTOS ASSAI 05: seed modelos + aliases..."
python scripts/migrations/motos_assai_05_seed_modelos.py \
    || echo "⚠️ Seed motos_assai_05 falhou, continuando deploy..."

# 16. MOTOS ASSAI 06: seed CarviaModeloMoto SOL (cubagem CarVia para NFs Q.P.A.).
# Idempotente: skip se nome SOL já existe. Dimensões: 158x45x80 cm (classe DOT).
echo "MOTOS ASSAI 06: seed CarviaModeloMoto SOL..."
python scripts/migrations/motos_assai_06_carvia_modelo_sol.py \
    || echo "⚠️ Seed motos_assai_06 falhou, continuando deploy..."

# 17. MOTOS ASSAI 07: UNIQUE (recibo_id, chassi) em assai_recibo_item (idempotente).
echo "MOTOS ASSAI 07: UNIQUE index assai_recibo_item..."
python scripts/migrations/motos_assai_07_unique_recibo_item.py \
    || echo "⚠️ Migration motos_assai_07 falhou, continuando deploy..."

# 18. MOTOS ASSAI 08: campos de geocoding (lat, lng, provider, geocoded_at) em assai_loja.
# Idempotente (DO $$ + IF NOT EXISTS). NAO geocoda lojas — so adiciona colunas.
echo "MOTOS ASSAI 08: geocoding fields em assai_loja..."
python scripts/migrations/motos_assai_08_loja_geocoding.py \
    || echo "⚠️ Migration motos_assai_08 falhou, continuando deploy..."

echo "Build concluído com sucesso!"


# Linha antiga mantida por compatibilidade (pode ser removida depois)
python aplicar_migracao_render.py || echo "Migration already applied"

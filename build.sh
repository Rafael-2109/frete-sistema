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

# 10e. WhatsApp module: usuarios.whatsapp_autorizado + index parcial +
# tabela whatsapp_tasks. Idempotente (ADD COLUMN IF NOT EXISTS,
# CREATE INDEX IF NOT EXISTS, CREATE TABLE IF NOT EXISTS).
# Backend: app/whatsapp/. Plugin OpenClaw em ~/.openclaw/plugins/nacom-bridge/.
# Requer envs OPENCLAW_PLUGIN_TOKEN e OPENCLAW_GATEWAY_TOKEN no Render
# (gateway OpenClaw e externo ao Render — apenas para envio de notificacoes
# de fora; conversas inbound dependem do gateway local).
echo "WhatsApp: usuarios.whatsapp_autorizado + whatsapp_tasks..."
python scripts/migrations/2026_05_09_whatsapp_module.py \
    || echo "⚠️ Migration whatsapp_module falhou, continuando deploy..."

# 10. F8 (2026-05-09): tabela agent_session_costs para persistencia opcional
# do CostTracker (cross-deploy). Habilitada via flag AGENT_COST_TRACKER_PERSIST.
# Sem flag, tabela fica vazia — comportamento legado in-memory preservado.
# Idempotente (CREATE TABLE/INDEX IF NOT EXISTS).
echo "Agente: agent_session_costs (cost_tracker persistente)..."
python scripts/migrations/2026_05_09_agent_session_costs.py \
    || echo "⚠️ Migration agent_session_costs falhou, continuando deploy..."

# 11. HORA 30: seed inicial de hora_modelo_alias.
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

# 12. Pessoal (2026-05-10): corrige bugs do dedup de pessoal_transacoes.
# Causa: hash usava `documento` cru (sensivel a zero-a-esquerda) e `valor`
# Decimal sem precisao canonica (50 vs 50.00 -> hashes distintos). Re-importacoes
# do mesmo extrato criavam duplicatas. Ordem importante:
#   12a. Limpa duplicatas remanescentes detectadas pelo algoritmo NOVO.
#   12b. Regenera todos os hash_transacao com algoritmo NOVO.
#   12c. Reaplica heuristica L4 (PAGTO POR DEB EM C/C, etc) em transacoes que
#        ficaram com excluir_relatorio=False por bug em propagar_para_pendentes.
# Todos idempotentes (rodar 2x = nada faz).
echo "Pessoal: limpar duplicatas detectadas pelo dedup v2..."
python scripts/migrations/limpar_duplicatas_dedup_v2.py --aplicar \
    || echo "⚠️ limpar_duplicatas_dedup_v2 falhou, continuando deploy..."

echo "Pessoal: regenerar hash_transacao com algoritmo novo..."
python scripts/migrations/recalcular_hash_transacao_pessoal.py --aplicar \
    || echo "⚠️ recalcular_hash_transacao_pessoal falhou, continuando deploy..."

echo "Pessoal: re-aplicar heuristica L4 em transacoes orfas..."
python scripts/migrations/recategorizar_pendentes_pessoal.py --aplicar \
    || echo "⚠️ recategorizar_pendentes_pessoal falhou, continuando deploy..."

# 13. Custeio (2026-05-10): auditoria + Sprint 1+2+3 — 4 migrations DDL.
# Aplicacao em ordem: partial UNIQUE (C8) -> CHECK constraints (C12)
# -> soft delete columns (C17) -> audit log table (C16). Todas idempotentes.
# Ordem importa apenas porque CHECK constraints de tipo_custo_selecionado
# ja contemplam MANUAL/PRODUCAO conhecidos em prod (sem violacoes).

# 13a. C8: partial UNIQUE em custo_considerado(cod_produto) WHERE custo_atual=TRUE
# Valida ausencia de duplicatas antes de aplicar (aborta se encontrar).
echo "Custeio C8: partial UNIQUE custo_considerado..."
python scripts/migrations/partial_unique_custo_considerado.py \
    || echo "⚠️ Migration partial_unique_custo_considerado falhou, continuando deploy..."

# 13b. C12: 9 CHECK constraints (tipo_custo_selecionado, tipo_produto, status,
# mes/ano, percentuais, vigencias). Valida violacoes antes de aplicar.
echo "Custeio C12: CHECK constraints..."
python scripts/migrations/check_constraints_custeio.py \
    || echo "⚠️ Migration check_constraints_custeio falhou, continuando deploy..."

# 13c. C17: soft delete em CustoFrete e ParametroCusteio.
# Adiciona colunas ativo/desativado_em/desativado_por + indices.
echo "Custeio C17: soft delete CustoFrete e ParametroCusteio..."
python scripts/migrations/soft_delete_custeio.py \
    || echo "⚠️ Migration soft_delete_custeio falhou, continuando deploy..."

# 13d. C16: tabela audit_log_custeio + 7 indices.
# CREATE TABLE IF NOT EXISTS — totalmente idempotente.
echo "Custeio C16: audit_log_custeio..."
python scripts/migrations/audit_log_custeio.py \
    || echo "⚠️ Migration audit_log_custeio falhou, continuando deploy..."

# 14. Agente (2026-05-11): backfill KG links para memorias antigas sem entidades.
# Roda extract_and_link_entities sobre memorias com is_directory=false,
# content>=100 chars e SEM entrada em agent_memory_entity_links. Idempotente
# via NOT EXISTS — execucoes subsequentes processam 0 memorias.
# Layer 1 (regex) zero custo; Layer 2 (Voyage) ~$0.0001/mem; Layer 3 (Sonnet)
# pulado em batch. Total estimado primeira execucao: <$0.05, ~5-10min.
# Resolve queda historica de KG coverage (52.8% → 43.24% em 6 ciclos).
echo "Agente: backfill KG links em memorias antigas..."
python scripts/maintenance/backfill_kg_links.py --apply \
    || echo "⚠️ Backfill KG links falhou, continuando deploy..."

echo "Build concluído com sucesso!"


# Linha antiga mantida por compatibilidade (pode ser removida depois)
python aplicar_migracao_render.py || echo "Migration already applied"

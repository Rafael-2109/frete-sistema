#!/bin/bash

# Build script para Render com correção de migrações

echo "=== INICIANDO DEPLOY NO RENDER ==="

# nginx eh instalado no start_render.sh (Render Python Runtime NAO permite
# apt-get no build.sh — so no start, igual ao chromium-browser).

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

# 4. (deploy_render.py movido para o bloco RUN_LEGACY_MIGRATIONS — ver abaixo)
mkdir -p scripts

# 5. Inicializar banco se necessário (db.create_all idempotente) — SEMPRE
echo "Inicializando banco..."
python init_db.py

# 5b. Migration idempotente FORA do guard (Fase 3 loop corretivo): adiciona as colunas
#     error_signature/harmful_count/helpful_count + indice em agent_memories. NECESSARIA a
#     cada deploy ate consolidar — db.create_all (init_db) NAO faz ALTER de coluna nova em
#     tabela existente, e o `flask db upgrade` (alembic) nao cobre este script manual.
#     ADD COLUMN IF NOT EXISTS -> no-op apos a 1a vez. CRITICO: o codigo da Fase 3 grava em
#     colunas NOT NULL; sem esta migration, INSERT em agent_memories quebraria no deploy.
echo "Fase 3 loop corretivo: migration agent_memories (error_signature/harmful/helpful)..."
python scripts/migrations/2026_06_02_agent_memories_error_signature.py \
    || echo "⚠️ migration error_signature falhou — verificar (continuando deploy)..."

# 5c. Otimizacao lista_pedidos (2026-06-07): desnormaliza equipe_vendas em separacao
#     (coluna + backfill) e recria VIEW pedidos v8 + MV mv_pedidos SEM o LEFT JOIN
#     carteira_principal (~710ms -> ~26ms/scan na Parte 1). ORDEM OBRIGATORIA: a coluna
#     roda ANTES da VIEW — a v8 le s.equipe_vendas (guard aborta sem a coluna) e o model
#     novo quebraria queries em separacao sem ela. Idempotentes (ADD COLUMN IF NOT EXISTS
#     + DROP/CREATE VIEW) -> no-op apos consolidar. REMOVER deste arquivo apos o 1o deploy.
echo "Otimizacao lista_pedidos (1/2): coluna separacao.equipe_vendas + backfill..."
python scripts/migrations/add_equipe_vendas_separacao.py \
    || echo "⚠️ migration equipe_vendas (coluna) falhou — verificar (continuando deploy)..."
echo "Otimizacao lista_pedidos (2/2): VIEW pedidos v8 + MV sem JOIN carteira_principal..."
python scripts/migrations/alterar_view_pedidos_v8.py \
    || echo "⚠️ migration VIEW v8 falhou — verificar (continuando deploy)..."

# ============================================================================
# MIGRATIONS HISTORICAS — guardadas pela flag RUN_LEGACY_MIGRATIONS (default 0).
#
# Avaliacao caso-a-caso (2026-06-01): TODAS sao idempotentes e JA estao
# aplicadas em PROD, portanto no-op no deploy normal. Cada uma rodava num
# processo Python isolado chamando create_app() (~10-15s em PROD); ~55 delas
# somavam ~12-14min do build. Agora so rodam em DB novo / DR / staging,
# setando RUN_LEGACY_MIGRATIONS=1 no Render. Scripts permanecem versionados
# (NADA deletado — apenas deixam de rodar a cada deploy ja consolidado).
#
# PERMANECEM ativos FORA deste guard (idempotentes legitimos a cada deploy):
#   flask db upgrade · init_db.py · sped_ecd_rules_indexer · bootstrap_ontologia
# ============================================================================
if [ "${RUN_LEGACY_MIGRATIONS:-0}" = "1" ]; then
echo ">>> RUN_LEGACY_MIGRATIONS=1 — aplicando migrations historicas (DB novo/DR)..."

# 4b. deploy_render.py: ALTER hora_agendamento (one-shot ja aplicado) + mapa CTRC
#     do SSW. NOTA: tambem re-roda 'flask db upgrade' e 'add_icms_aliquota'
#     (ambos redundantes com este build.sh) — por isso vive dentro do guard.
echo "deploy_render: hora_agendamento + CTRC map (legado)..."
python scripts/deploy_render.py || echo "Script de verificação falhou, continuando..."

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
# DESATIVADO 2026-05-18: cleanup one-shot ja aplicado em prod. Para re-rodar
# manualmente (apos novo merge de aliases): Render Shell ->
#   python scripts/migrations/hora_35_cleanup_alias_motos.py
# echo "HORA 35: cleanup motos em aliases mergidos..."
# python scripts/migrations/hora_35_cleanup_alias_motos.py \
#     || echo "⚠️ Migration hora_35 falhou, continuando deploy..."

# 10d. HORA 36: campo consumidor_final em hora_venda (NF-e TagPlus).
# Boolean nullable: NULL=infere via doc, TRUE/FALSE=explicito do operador.
# Idempotente (ADD COLUMN IF NOT EXISTS).
echo "HORA 36: campo consumidor_final em hora_venda..."
python scripts/migrations/hora_36_consumidor_final.py \
    || echo "⚠️ Migration hora_36 falhou, continuando deploy..."

# 10e. HORA 41: campo autopropelido em hora_modelo (classificacao Autopropelido
# vs Ciclomotor). Controla os textos exibidos em `inf_contribuinte` da NF-e
# (garantia, CNH, ATPV — Res. CONTRAN 996/2023). NOT NULL DEFAULT TRUE
# (HORA vende predominantemente bicicletas eletricas); operador ajusta
# ciclomotores caso a caso em /hora/modelos. Idempotente.
echo "HORA 41: campo autopropelido em hora_modelo..."
python scripts/migrations/hora_41_modelo_autopropelido.py \
    || echo "⚠️ Migration hora_41 falhou, continuando deploy..."

# 10f. WhatsApp module: usuarios.whatsapp_autorizado + index parcial +
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

# 12. CarVia: tabela carvia_anexos (anexos polimorficos Frete + Subcontrato).
# Paridade Nacom (comprovante + e-mail). Idempotente (CREATE TABLE IF NOT EXISTS
# via metadata SQLAlchemy). Despesas mantem carvia_custo_entrega_anexos.
echo "CarVia: tabela carvia_anexos (anexos Frete + Subcontrato)..."
python scripts/migrations/criar_carvia_anexos.py \
    || echo "⚠️ Migration criar_carvia_anexos falhou, continuando deploy..."

# 13. Inventario (2026-05-27): snapshot freeze MOV/SIST em inventario_snapshot_odoo.
# +5 cols Numeric(15,3) DEFAULT 0 (mov_compras/vendas/consumo/producao/sist_total).
# Idempotente (IF NOT EXISTS). Resolve gap temporal ODOO vs MOV/SIST no Confronto.
echo "Inventario: snapshot freeze MOV/SIST..."
python scripts/migrations/2026_05_27_inventario_snapshot_freeze_mov.py \
    || echo "⚠️ Migration inventario_snapshot_freeze_mov falhou, continuando deploy..."

# Migrations motos_assai (01-08): removidas do build apos deploy concluido em
# 2026-05-08. Scripts permanecem em scripts/migrations/ como historico — rodar
# manualmente apenas em fresh install / staging novo (ordem: 02, 01, 07, 08
# DDLs primeiro; depois 03, 04, 05, 06 seeds).

# 12. Pessoal (2026-05-10): corrige bugs do dedup de pessoal_transacoes.
# DESATIVADO 2026-05-18: os 3 scripts ja foram aplicados em prod e sao
# idempotentes mas custosos (varrem pessoal_transacoes inteiro a cada deploy).
# Para re-rodar manualmente (apos nova queda de qualidade do hash): Render Shell:
#   python scripts/migrations/limpar_duplicatas_dedup_v2.py --aplicar
#   python scripts/migrations/recalcular_hash_transacao_pessoal.py --aplicar
#   python scripts/migrations/recategorizar_pendentes_pessoal.py --aplicar
# echo "Pessoal: limpar duplicatas detectadas pelo dedup v2..."
# python scripts/migrations/limpar_duplicatas_dedup_v2.py --aplicar \
#     || echo "⚠️ limpar_duplicatas_dedup_v2 falhou, continuando deploy..."
#
# echo "Pessoal: regenerar hash_transacao com algoritmo novo..."
# python scripts/migrations/recalcular_hash_transacao_pessoal.py --aplicar \
#     || echo "⚠️ recalcular_hash_transacao_pessoal falhou, continuando deploy..."
#
# echo "Pessoal: re-aplicar heuristica L4 em transacoes orfas..."
# python scripts/migrations/recategorizar_pendentes_pessoal.py --aplicar \
#     || echo "⚠️ recategorizar_pendentes_pessoal falhou, continuando deploy..."

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

# 14. Pedido Compras (2026-05-11): backfill cnpj_fornecedor NULL via Odoo.
# Problema: sync incremental usa filtro write_date dentro de janela (-90min).
# Partner Odoo alterado APOS criacao do PO nao re-sincroniza, deixando POs
# ativos com cnpj_fornecedor=NULL e bloqueando silenciosamente o match NF x PO.
# Investigacao: agent_sessions.id=560 (Teams Rafael, 11/05/2026, NF 143343 Novacki).
# Script idempotente — busca POs ativos com cnpj_fornecedor IS NULL e
# re-sincroniza via purchase.order.partner_id -> res.partner.l10n_br_cnpj.
# Limite de 500 POs por execucao para nao estourar tempo de build; restantes
# convergem via scheduler step 4.6 (auto-heal incremental).
echo "Pedido Compras: backfill cnpj_fornecedor NULL via Odoo..."
python scripts/migrations/backfill_cnpj_pedido_compras_via_odoo.py --aplicar --max-pos 500 \
    || echo "⚠️ Backfill cnpj pedido_compras falhou, continuando deploy..."

# 15. Motos Assai (2026-05-12): integracao com fluxo Nacom de pedidos (lista_pedidos).
# Adiciona cabecalho pedido x loja com 4 campos de agendamento, override em
# AssaiSeparacao e tabela placeholder de qtd planejada por modelo. Ajusta UNIQUE
# para permitir N separacoes FECHADAS por (pedido, loja) — fluxo de carregamentos
# sucessivos. Ordem importa: 10 antes de 11/12 (nao depende, mas legibilidade).
echo "Motos Assai 10: AssaiPedidoVendaLoja (cabecalho 4 campos)..."
python scripts/migrations/motos_assai_10_pedido_venda_loja.py \
    || echo "⚠️ Migration motos_assai_10 falhou, continuando deploy..."

echo "Motos Assai 11: 4 campos override em assai_separacao..."
python scripts/migrations/motos_assai_11_separacao_4campos.py \
    || echo "⚠️ Migration motos_assai_11 falhou, continuando deploy..."

echo "Motos Assai 12: assai_separacao_saldo_modelo + ajuste UNIQUE..."
python scripts/migrations/motos_assai_12_separacao_saldo_modelo.py \
    || echo "⚠️ Migration motos_assai_12 falhou, continuando deploy..."

# 15a. Motos Assai 13 (2026-05-12): drop UNIQUE em_separacao.
# Regra de negocio: separacoes = veiculos; N veiculos podem carregar
# paralelamente do mesmo (pedido, loja). Concorrencia de chassi protegida
# via lock pessimista em AssaiMoto + validacao status.
echo "Motos Assai 13: drop UNIQUE em_separacao..."
python scripts/migrations/motos_assai_13_drop_unique_em_separacao.py \
    || echo "⚠️ Migration motos_assai_13 falhou, continuando deploy..."

# 15b. Motos Assai 14 (2026-05-12 — code review fix): chassi_assai em `separacao` Nacom.
# Bug pre-existente: UNIQUE em (lote, cod_produto) bloqueava 2 chassis do mesmo
# modelo no mesmo lote ASSAI-SEP-*. Corrige granularidade para 1 linha por chassi.
echo "Motos Assai 14: chassi_assai em separacao + ajuste UNIQUE..."
python scripts/migrations/motos_assai_14_chassi_assai_em_separacao.py \
    || echo "⚠️ Migration motos_assai_14 falhou, continuando deploy..."

# 15c. Motos Assai 15 (2026-05-12 — HOTFIX): Migration 10 falhou em prod por
# falta de DEFAULT FALSE em agendamento_confirmado (criado via db.create_all
# sem server_default). Re-aplica DEFAULT + re-executa backfill todo. Idempotente.
echo "Motos Assai 15: HOTFIX DEFAULT agendamento_confirmado + rerodar backfill..."
python scripts/migrations/motos_assai_15_fix_default_agendamento_confirmado.py \
    || echo "⚠️ Migration motos_assai_15 falhou, continuando deploy..."

# 15d. Motos Assai 16-28 (2026-05-14 reconciliacao): migrations 16-28 nunca
# foram para o build.sh; algumas foram aplicadas manualmente via Render Shell
# em prod, outras (22/24/27) ficaram fora — esta secao alinha o deploy.
# 23 e 25 ficam de fora porque sao backfills explicitamente manuais por
# docstring (rodar 1x apos deploy, nao a cada build).
# Todas idempotentes: IF NOT EXISTS / DO $$ ... IF EXISTS guards.

echo "Motos Assai 16: pos_venda_ocorrencia + anexo..."
python scripts/migrations/motos_assai_16_pos_venda_ocorrencia.py \
    || echo "⚠️ Migration motos_assai_16 falhou, continuando deploy..."

echo "Motos Assai 17: cleanup separacoes orfas..."
python scripts/migrations/motos_assai_17_cleanup_sep_2_orfa.py \
    || echo "⚠️ Migration motos_assai_17 falhou, continuando deploy..."

echo "Motos Assai 18: assai_carregamento + item..."
python scripts/migrations/motos_assai_18_carregamento.py \
    || echo "⚠️ Migration motos_assai_18 falhou, continuando deploy..."

echo "Motos Assai 19: assai_divergencia (8 tipos centralizados)..."
python scripts/migrations/motos_assai_19_divergencia.py \
    || echo "⚠️ Migration motos_assai_19 falhou, continuando deploy..."

echo "Motos Assai 20: assai_pedido_excel (parser/confianca)..."
python scripts/migrations/motos_assai_20_pedido_excel.py \
    || echo "⚠️ Migration motos_assai_20 falhou, continuando deploy..."

echo "Motos Assai 21: backfill status pedido (4 status novos)..."
python scripts/migrations/motos_assai_21_simplificar_status_pedido.py \
    || echo "⚠️ Migration motos_assai_21 falhou, continuando deploy..."

echo "Motos Assai 22: cancelada_em + cancelada_por_id em assai_nf_qpa..."
python scripts/migrations/motos_assai_22_nf_cancelamento_campos.py \
    || echo "⚠️ Migration motos_assai_22 falhou, continuando deploy..."

# 23 (backfill NFs orfas) — RODAR MANUAL: docstring exige.

echo "Motos Assai 24: CHECK constraints aceitam novos status..."
python scripts/migrations/motos_assai_24_check_status_aceitar_novos.py \
    || echo "⚠️ Migration motos_assai_24 falhou, continuando deploy..."

# 25 (backfill divergencias legadas) — RODAR MANUAL.

echo "Motos Assai 26: assai_nf_qpa_item_vinculo_historico..."
python scripts/migrations/motos_assai_26_vinculo_historico.py \
    || echo "⚠️ Migration motos_assai_26 falhou, continuando deploy..."

echo "Motos Assai 27: UNIQUE parcial NF ativa por separacao..."
python scripts/migrations/motos_assai_27_unique_nf_sep_ativa.py \
    || echo "⚠️ Migration motos_assai_27 falhou, continuando deploy..."

echo "Motos Assai 28: CCe como entidade (match reverso)..."
python scripts/migrations/motos_assai_28_cce_entidade.py \
    || echo "⚠️ Migration motos_assai_28 falhou, continuando deploy..."

# 15e. Motos Assai 29 (2026-05-14): devolucao por NF de venda Q.P.A. (NFd).
# Cria 3 tabelas (assai_devolucao_nfd / _item / _anexo) + flag devolvido em
# assai_nf_qpa_item. recalcular_status_pedido EXCLUI SeparacaoItem ligado a
# NfQpaItem.devolvido=TRUE da contagem qtd_faturada (saldo do MODELO retorna
# ao pedido de vendas). Idempotente (CREATE TABLE/INDEX IF NOT EXISTS,
# ADD COLUMN IF NOT EXISTS).
echo "Motos Assai 29: devolucao por NF de venda Q.P.A. (NFd)..."
python scripts/migrations/motos_assai_29_devolucao.py \
    || echo "⚠️ Migration motos_assai_29 falhou, continuando deploy..."

# 15f. Motos Assai backfill match NFs (2026-05-17): REMOVIDO DO BUILD (2026-05-18).
# Motivo: a parte3 cria pedido PLACEHOLDER `BACKFILL-2026-05-17` quando a loja
# da NF nao tem AssaiPedidoVendaLoja real cadastrada — e RECRIA o pedido +
# separacao a cada deploy (re-emitindo eventos SEPARADA/FATURADA nos chassis).
# Confirmado em prod 2026-05-17: NF 1737 ficou vinculada ao pedido placeholder
# id=3 numero='BACKFILL-2026-05-17' loja Aricanduva — eventos rodaram 2x em
# deploys consecutivos. Para re-rodar manualmente (apos novos recibos / NFs
# importadas), use Render Shell:
#   python scripts/migrations/motos_assai_backfill_match_nfs_2026_05_17.py
# python scripts/migrations/motos_assai_backfill_match_nfs_2026_05_17.py \
#     || echo "⚠️ Backfill motos_assai falhou, continuando deploy..."

# 15f.b Cleanup do pedido placeholder BACKFILL + desvinculacao da NF 1737.
# REMOVIDO do build apos primeira execucao em prod (commit f837adce 2026-05-18).
# Script permanece em scripts/migrations/ — idempotente, pode ser re-executado
# manualmente via Render Shell se o placeholder reaparecer:
#   python scripts/migrations/remover_pedido_backfill_e_desvincular_nf_1737.py
# echo "Motos Assai cleanup: remover pedido BACKFILL + desvincular NF 1737..."
# python scripts/migrations/remover_pedido_backfill_e_desvincular_nf_1737.py \
#     || echo "⚠️ Cleanup BACKFILL falhou, continuando deploy..."

# 15g. Motos Assai 31 (2026-05-17): novo tipo de divergencia
# CHASSI_FATURADO_SEM_RECIBO no CHECK constraint. _calcular_match agora exige
# AssaiReciboItem(conferido=True, ativo=True) — bloqueia NF de virar BATEU se
# chassi nao tem origem em recibo Motochefe (defesa contra parser PDF errado,
# digitacao errada na conferencia, faturamento sem recebimento fisico).
# Idempotente (DROP IF EXISTS + recriar CHECK).
echo "Motos Assai 31: CHECK constraint CHASSI_FATURADO_SEM_RECIBO..."
python scripts/migrations/motos_assai_31_divergencia_tipo_faturado_sem_recibo.py \
    || echo "⚠️ Migration motos_assai_31 falhou, continuando deploy..."

# 16. Remessa VORTX Conversor/Validador (2026-05-12): tabela remessa_vortx_conversao.
# Auditoria de operacoes de conversao (BMP/274 -> VORTX/310) e validacao read-only
# de arquivos CNAB 400 externos via UI em /remessa-vortx/converter e /validar.
# Idempotente (CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS).
echo "Remessa VORTX 16: auditoria conversor/validador externo..."
python scripts/migrations/2026_05_12_add_remessa_vortx_conversao.py \
    || echo "⚠️ Migration remessa_vortx_conversao falhou, continuando deploy..."

# 17. Agente Artifacts (2026-05-12): tabela agente_artifacts.
# Artifacts (bundle.html auto-contido) gerados pela skill gerando-artifact.
# Build async via worker RQ dedicado (worker_artifacts.py, fila 'artifacts').
# Idempotente (CREATE TABLE IF NOT EXISTS + indices + check constraint).
echo "Agente Artifacts 17: tabela agente_artifacts..."
python scripts/migrations/2026_05_12_agente_artifacts.py \
    || echo "⚠️ Migration agente_artifacts falhou, continuando deploy..."

# 18a. SPED ECD Embeddings (2026-05-16): tabela sped_ecd_rule_embeddings.
# Manual ECD Leiaute 9 + iteracoes PLANO + gotchas CLAUDE.md -> pgvector HNSW.
# Consumido pela skill auditando-sped-vs-manual (subagente auditor-sped-ecd).
# Idempotente (CREATE TABLE IF NOT EXISTS + pgvector hnsw cosine).
echo "SPED ECD 18a: tabela sped_ecd_rule_embeddings..."
python scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.py \
    || echo "⚠️ Migration sped_ecd_rule_embeddings falhou, continuando deploy..."

# 18b. SPED ECD indexer — MOVIDO para fora do guard (roda SEMPRE). Ver fim do build.sh.

# 19. Inventario 2026-05 (2026-05-18): operacao_odoo_auditoria.
# Tabela POLIMORFICA de auditoria de operacoes Odoo (account.move, stock.picking,
# stock.lot, etc.) com external_id UNIQUE para idempotencia. Substitui o padrao
# fretes-especifico (LancamentoFreteOdooAuditoria em app/fretes/models.py:1047-1134).
# Consumida pelo InventarioPipelineService + futuras operacoes diarias.
# Idempotente (CREATE TABLE IF NOT EXISTS + 3 indexes).
# Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §7.1
echo "Inventario 19: tabela operacao_odoo_auditoria (polimorfica)..."
python scripts/migrations/2026_05_18_operacao_odoo_auditoria.py \
    || echo "⚠️ Migration operacao_odoo_auditoria falhou, continuando deploy..."

# 20. Inventario 2026-05 (2026-05-18): ajuste_estoque_inventario.
# Tabela enxuta que controla ciclos de inventario fisico (suporta multiplos
# ciclos via campo `ciclo`). Uma linha por divergencia (produto, company, lote)
# detectada. Idempotente.
echo "Inventario 20: tabela ajuste_estoque_inventario..."
python scripts/migrations/2026_05_18_ajuste_estoque_inventario.py \
    || echo "⚠️ Migration ajuste_estoque_inventario falhou, continuando deploy..."

# 21. Inventario 2026-05 (2026-05-19): pipeline batch ALTER.
# Adiciona fase_pipeline + picking_id_odoo + invoice_id_odoo + chave_nfe em
# ajuste_estoque_inventario, e pipeline_etapa em operacao_odoo_auditoria.
# Origem da decisao: D003 (pipeline em batches) apos G004 (padrao real eh
# picking+robo CIEL IT+Playwright, nao account.move direto).
# Idempotente (ADD COLUMN IF NOT EXISTS).
echo "Inventario 21: ALTER pipeline batch (fase_pipeline + 4 colunas)..."
python scripts/migrations/2026_05_19_add_fase_pipeline.py \
    || echo "⚠️ Migration add_fase_pipeline falhou, continuando deploy..."

# 22. Inventario 2026-05 (2026-05-18): audit log ajuste_estoque_inventario.
# Cria tabela ajuste_estoque_inventario_audit (append-only) + trigger AFTER
# INSERT/UPDATE/DELETE que captura toda alteracao em ajuste_estoque_inventario
# independente da origem (ORM, SQL direto, MCP, psql, scripts).
# Foco: forense de cancelamentos/reset EXECUTADO->PROPOSTO durante ciclo
# inventario 2026-05. Idempotente.
echo "Inventario 22: audit log ajuste_estoque_inventario..."
python scripts/migrations/2026_05_18_audit_ajuste_estoque_inventario.py \
    || echo "⚠️ Migration audit_ajuste_estoque_inventario falhou, continuando deploy..."

# 22b. Audit Hook deterministico Odoo (2026-05-28): rastrear toda chamada XML-RPC
# write em OdooConnection.execute_kw, correlacionando com session_id do agente web.
# ADD COLUMN session_id/tool_use_id/agent_type + indexes + incorpora v21 (ALTER
# COLUMN acao/status/pipeline_etapa). Idempotente (ADD COLUMN IF NOT EXISTS).
# Ativacao gradual via AGENT_ODOO_AUDIT_HOOK=true (default OFF — zero overhead
# enquanto desligada). Ver app/odoo/CLAUDE.md secao P8.
echo "Inventario 22b: audit hook deterministico (session_id em operacao_odoo_auditoria)..."
python scripts/migrations/2026_05_28_operacao_odoo_auditoria_session.py \
    || echo "⚠️ Migration operacao_odoo_auditoria_session falhou, continuando deploy..."

# 22c. NF Transferencia inter-filiais (2026-05-28): snapshot fiscal de NFs
# inter-company (FB↔CD↔LF) com cross-ref destino. 4 migrations:
#   - nf_transferencia_snapshot       (tabelas snapshot + produto_snapshot)
#   - em_transito_inventario_snapshot (3 colunas em_transito_* em inventario_snapshot_odoo)
#   - nf_transferencia_desconsiderada (flag por NF para EXCLUIR do em_transito; sobrevive ao refresh)
#   - nf_transferencia_timestamps     (3 colunas DateTime: emissao_hora, picking_data_hora, invoice_destino_data_hora)
# Ordem: snapshot ANTES de desconsiderada/timestamps (FK logica via account_move_id_origem).
echo "Fiscal 22c.1: tabelas nf_transferencia_snapshot + produtos..."
python scripts/migrations/2026_05_28_nf_transferencia_snapshot.py \
    || echo "⚠️ Migration nf_transferencia_snapshot falhou, continuando deploy..."

echo "Fiscal 22c.2: em_transito_inventario_snapshot (3 colunas em_transito_*)..."
python scripts/migrations/2026_05_28_add_em_transito_inventario_snapshot.py \
    || echo "⚠️ Migration em_transito_inventario_snapshot falhou, continuando deploy..."

echo "Fiscal 22c.3: nf_transferencia_desconsiderada (flag por NF)..."
python scripts/migrations/2026_05_28_nf_transferencia_desconsiderada.py \
    || echo "⚠️ Migration nf_transferencia_desconsiderada falhou, continuando deploy..."

echo "Fiscal 22c.4: nf_transferencia_timestamps (3 colunas DateTime)..."
python scripts/migrations/2026_05_28_nf_transferencia_timestamps.py \
    || echo "⚠️ Migration nf_transferencia_timestamps falhou, continuando deploy..."

# 23. CarVia agendamento (2026-05-21): horario de agendamento + VIEW pedidos v7.
# Feature CarVia: campo de horario (HH:MM) na cotacao comercial, propagado para
# EmbarqueItem + EntregaMonitorada (AgendamentoEntrega) e exibido em lista_pedidos
# via VIEW. A v7 da VIEW TAMBEM corrige a regressao do agendamento_confirmado
# (projetava FALSE para CarVia desde a v4/v5) — substitui a necessidade da v6.
# ORDEM OBRIGATORIA: 23a (colunas) ANTES de 23b (VIEW) — a v7 referencia
# carvia_cotacoes.horario_agenda. Ambas idempotentes.
# MANUTENCAO: se uma v8 da VIEW pedidos for criada, ATUALIZAR 23b para a versao
# mais recente — senao a v7 sobrescreve a v8 a cada deploy.
echo "CarVia 23a: colunas horario_agenda (carvia_cotacoes) + hora_agendamento (embarque_itens)..."
python scripts/migrations/add_horario_agendamento_carvia.py \
    || echo "⚠️ Migration add_horario_agendamento_carvia falhou, continuando deploy..."

echo "CarVia 23b: VIEW pedidos v7 (horario_agendamento + agendamento_confirmado CarVia)..."
python scripts/migrations/alterar_view_pedidos_union_carvia_v7.py \
    || echo "⚠️ Migration view_pedidos_v7 falhou, continuando deploy..."

# 24. UoM compra VIDRO 200 G (2026-05-28): o De-Para (NADIR) sincronizou MI(181)
# em product.supplierinfo.product_uom (related -> uom_po_id store), inflando o
# price_unit dos Pedidos de Compra ~10^6x (PO C2619539: R$ 25,6 bi). Reverte o
# De-Para -> Units e garante uom_po_id=Units no Odoo (best-effort). Idempotente.
echo "UoM compra VIDRO 200 G: revert MI -> Units (De-Para + Odoo)..."
python scripts/migrations/2026_05_28_corrigir_uom_compra_vidro_206200004.py \
    || echo "⚠️ Migration corrigir_uom_compra_vidro falhou, continuando deploy..."

# 25. Deprecar odoo_product_uom_id no De-Para (2026-05-29): apos o fix de codigo
# (DeparaService nao grava mais product_uom no supplierinfo), zera o campo obsoleto
# em todos os De-Paras p/ nenhum fluxo legado reescrever uom_po_id. Idempotente.
echo "De-Para: deprecar odoo_product_uom_id (zerar campo obsoleto)..."
python scripts/migrations/2026_05_29_deprecar_odoo_product_uom_id_depara.py \
    || echo "⚠️ Migration deprecar_odoo_product_uom_id falhou, continuando deploy..."

# 26. Evolucao do Agente (2026-05-31): fundacao do Blueprint (Ondas 0-4).
# 26a tabela agent_step (S0a, entidade de passo/turno) + 26b proveniencia
# bi-temporal no KG (D3). Migrations duplas idempotentes (IF NOT EXISTS).
# 26c bootstrap de ontologia canonica (D2) — SELF-SKIP se AGENT_ONTOLOGY != true
# (CLI exige a flag); idempotente (increment_mentions=False -> nao infla mention_count).
# Todas best-effort (|| echo) — falha nao quebra o deploy.
echo "Agente 26a: tabela agent_step (S0a)..."
python scripts/migrations/2026_05_30_agent_step.py \
    || echo "⚠️ Migration agent_step falhou, continuando deploy..."

echo "Agente 26b: proveniencia bi-temporal no KG (D3)..."
python scripts/migrations/2026_05_31_kg_bitemporal.py \
    || echo "⚠️ Migration kg_bitemporal falhou, continuando deploy..."

# 26c. Bootstrap ontologia — MOVIDO para fora do guard (so se AGENT_ONTOLOGY=true). Ver fim.

# 26d. A3 gate de regressao (2026-06-01): baseline de eval por-agente + calibracao.
# agent_eval_scores (baseline score por run, A3 Fase 1) + agent_eval_case (1 linha
# por caso p/ spot-check humano 5-10%, A3-R3). Ambas idempotentes (IF NOT EXISTS).
# Necessarias ANTES de ligar AGENT_EVAL_GATE / AGENT_EVAL_CALIBRATION (senao o eval
# falha por tabela inexistente em prod — SKIP_DB_CREATE=true). Best-effort (|| echo).
echo "Agente 26d.1: tabela agent_eval_scores (A3 baseline)..."
python scripts/migrations/2026_05_31_agent_eval_scores.py \
    || echo "⚠️ Migration agent_eval_scores falhou, continuando deploy..."

echo "Agente 26d.2: tabela agent_eval_case (A3-R3 calibracao)..."
python scripts/migrations/2026_06_01_agent_eval_case.py \
    || echo "⚠️ Migration agent_eval_case falhou, continuando deploy..."

# 26e. A4 promocao de diretriz (2026-06-01): coluna directive_status em agent_memories
# (ciclo de vida candidata|shadow|ativa|despromovida). Idempotente (ADD COLUMN IF NOT EXISTS).
# Necessaria ANTES de ligar AGENT_OPERATIONAL_DIRECTIVES (senao _build_operational_directives
# cai em UndefinedColumn e desliga TODAS as diretrizes silenciosamente). Best-effort (|| echo).
echo "Agente 26e: coluna directive_status em agent_memories (A4)..."
python scripts/migrations/2026_06_01_agent_memories_directive_status.py \
    || echo "⚠️ Migration agent_memories_directive_status falhou, continuando deploy..."

# 27. Inventario Ciclico (2026-05-31): contagem parcial por quant + plano de ajustes.
# Cria tabelas inventario_contagem + inventario_contagem_item (granularidade quant).
# Idempotente (model.__table__.create(checkfirst=True)). Confronto inalterado.
echo "Inventario 27: tabelas inventario_contagem + inventario_contagem_item..."
python scripts/migrations/inventario_contagem_create.py \
    || echo "⚠️ Migration inventario_contagem falhou, continuando deploy..."

else
  echo ">>> RUN_LEGACY_MIGRATIONS!=1 — pulando migrations historicas (ja aplicadas em PROD)."
fi
# ============================================================================
# SEMPRE (idempotentes leves, fora do guard) — rodam a cada deploy.
# ============================================================================

# SPED ECD indexer: re-embeda regras SO se Manual/PLANO/CLAUDE.md mudaram
# (content_hash skip => ~$0 e ~5s quando nada mudou). Requer VOYAGE_API_KEY —
# sem ela, falha graceful (deploy continua).
echo "SPED ECD: re-indexar regras (idempotente, skip se nada mudou)..."
python -m app.embeddings.indexers.sped_ecd_rules_indexer \
    || echo "⚠️ Indexer sped_ecd_rules falhou, continuando deploy..."

# Agente 26c: bootstrap de ontologia (D2). FONTE UNICA da flag = o proprio script
# (os.getenv("AGENT_ONTOLOGY","false").lower()=="true"); sem a flag ele faz
# sys.exit(1), engolido pelo || echo. NAO duplicar a flag no bash: quando voce
# ligar a flag no gate (ex.: "True"/"1"), o .lower() do script casa e um teste
# bash "= true" exato NAO casaria. Hoje AGENT_ONTOLOGY=OFF em PROD => no-op.
echo "Agente 26c: bootstrap de ontologia (so escreve se AGENT_ONTOLOGY=true)..."
python scripts/agente/bootstrap_ontologia.py \
    || echo "ℹ️ Bootstrap ontologia pulado (AGENT_ONTOLOGY off) ou falhou — continuando deploy..."

echo "Build concluído com sucesso!"


# DESATIVADO 2026-05-18: linha legacy ja consolidada via flask db upgrade.
# Migrations sao gerenciadas via secao 3 (flask db upgrade) e scripts
# explicitos no build.sh — aplicar_migracao_render.py era helper antigo.
# python aplicar_migracao_render.py || echo "Migration already applied"

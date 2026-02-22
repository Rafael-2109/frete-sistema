#!/usr/bin/env python3
"""
Backfill fator_conversao — 3 tabelas De-Para + recálculo quantidade_convertida
===============================================================================

Corrige registros De-Para com fator_conversao=1.0 cujo produto tem padrão NxM,
mas SOMENTE quando a unidade do XML (nf_devolucao_linha) confirma ser tipo UNIDADE.

Classificação de unidade usa SUBSTRING MATCH (não exact match), cobrindo variantes
com sufixo numérico: UN1, UND9, BD1, PT1, PC1, BL2, etc.
Replica _normalizar_unidade_deterministico() de ai_resolver_service.py:623-663.

Regra de negócio:
- Mesmo cliente + mesmo código pode pedir em UND ou CX
- Se unidade XML = tipo UNIDADE → fator deve ser N (extraído do NxM no nome do produto)
- Se unidade XML = CX ou não encontrada → fator=1.0 está correto, não mexer

Fonte de verdade para unidade: nf_devolucao_linha.unidade_medida (extraída do XML da NF-e)

Fases:
- Fase A: depara_produto_cliente (JOIN nf_devolucao_linha via prefixo_cnpj + codigo_cliente)
- Fase B: portal_atacadao_produto_depara (JOIN nf_devolucao_linha via cnpj_cliente + codigo_atacadao)
- Fase C: portal_sendas_produto_depara (JOIN nf_devolucao_linha via cnpj_cliente + codigo_sendas)
- Fase D: Recalcular quantidade_convertida em nf_devolucao_linha históricas

Executar:
    source .venv/bin/activate
    python scripts/migrations/backfill_depara_fator_conversao.py              # dry-run
    python scripts/migrations/backfill_depara_fator_conversao.py --execute    # executa

Data: 21/02/2026
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Padrões para classificação de unidade — SUBSTRING MATCH
# Replica _normalizar_unidade_deterministico() de ai_resolver_service.py:623-663
# CAIXA verificada primeiro: 'PACOTE' contém 'PC' mas é CAIXA
_PADROES_CAIXA = ['CX', 'CAIXA', 'BOX', 'FD', 'FARDO', 'PCT', 'PACOTE', 'TAMBOR']
_PADROES_UNIDADE = [
    'UND', 'UNID', 'UN', 'UNI',       # unidade e variantes
    'PC', 'PECA', 'PÇ',               # peça
    'BD', 'BALDE', 'BLD',             # balde
    'SC', 'SACO',                      # saco
    'PT', 'POTE',                      # pote
    'BL', 'BA',                        # balde/barra
    'SH', 'SACHE',                     # sachê
]


def _eh_unidade(unidade: str) -> bool:
    """
    Verifica se unidade é tipo UNIDADE (não caixa) — SUBSTRING MATCH.

    Replica a lógica de _normalizar_unidade_deterministico() do
    ai_resolver_service.py (linhas 623-663), cobrindo variantes com
    sufixo numérico: UN1, UND9, BD1, PT1, PC1, BL2, etc.

    CAIXA é verificada primeiro: 'PACOTE' contém 'PC' mas é CAIXA.
    """
    if not unidade:
        return False
    unidade_upper = unidade.upper().strip()
    # CAIXA primeiro (mais específico — evitar falsos positivos)
    if any(u in unidade_upper for u in _PADROES_CAIXA):
        return False
    # UNIDADE (substring match — cobre UN1, UND9, BD1, PT1, etc.)
    if any(u in unidade_upper for u in _PADROES_UNIDADE):
        return True
    # Caso especial: 'U' sozinho
    if unidade_upper == 'U':
        return True
    return False


def _fase_a_depara_produto_cliente(dry_run: bool) -> dict:
    """
    Fase A: depara_produto_cliente

    Estratégia:
    1. Seleciona registros com fator=1.0 + produto com padrão NxM
    2. Para cada, busca unidade do XML via nf_devolucao_linha (mais recente)
    3. Se unidade é tipo UNIDADE → atualiza fator + preenche unidade_medida_cliente se NULL
    4. Se unidade é CX ou NULL → mantém fator=1.0
    """
    stats = {
        'total_fator_1': 0,
        'com_padrao_nxm': 0,
        'unidade_encontrada_xml': 0,
        'unidade_tipo_unidade': 0,
        'unidade_tipo_caixa': 0,
        'sem_unidade_xml': 0,
        'atualizados_fator': 0,
        'atualizados_unidade': 0,
        'erros': 0,
    }

    logger.info("=" * 70)
    logger.info("FASE A: depara_produto_cliente")
    logger.info("=" * 70)

    # -------------------------------------------------------------------------
    # Análise: candidatos com fator=1.0, produto com NxM, + unidade do XML
    # -------------------------------------------------------------------------
    analysis_query = text("""
        SELECT
            dp.id,
            dp.nosso_codigo,
            dp.prefixo_cnpj,
            dp.codigo_cliente,
            dp.descricao_nosso,
            dp.unidade_medida_cliente,
            dp.unidade_medida_nosso,
            cp.nome_produto,
            CAST(SUBSTRING(cp.nome_produto FROM '(\\d+)[Xx]\\d+') AS INTEGER) AS novo_fator,
            latest_xml.unidade_medida AS unidade_xml
        FROM depara_produto_cliente dp
        JOIN cadastro_palletizacao cp ON dp.nosso_codigo = cp.cod_produto
        LEFT JOIN LATERAL (
            SELECT ndl.unidade_medida
            FROM nf_devolucao_linha ndl
            JOIN nf_devolucao nd ON ndl.nf_devolucao_id = nd.id
            WHERE ndl.codigo_produto_cliente = dp.codigo_cliente
              AND SUBSTRING(nd.cnpj_emitente, 1, 8) = dp.prefixo_cnpj
              AND ndl.unidade_medida IS NOT NULL
            ORDER BY nd.data_registro DESC
            LIMIT 1
        ) latest_xml ON true
        WHERE dp.fator_conversao = 1.0
          AND dp.ativo = true
          AND cp.nome_produto ~ '\\d+[Xx]\\d+'
          AND CAST(SUBSTRING(cp.nome_produto FROM '(\\d+)[Xx]\\d+') AS INTEGER) > 1
        ORDER BY dp.id
    """)

    rows = db.session.execute(analysis_query).fetchall()
    stats['com_padrao_nxm'] = len(rows)

    # Contar total com fator=1.0 (incluindo sem NxM)
    total_query = text("""
        SELECT COUNT(*) FROM depara_produto_cliente
        WHERE fator_conversao = 1.0 AND ativo = true
    """)
    stats['total_fator_1'] = db.session.execute(total_query).scalar()

    logger.info(f"  Total com fator=1.0:    {stats['total_fator_1']}")
    logger.info(f"  Com padrão NxM:         {stats['com_padrao_nxm']}")

    if not rows:
        logger.info("  Nenhum candidato com padrão NxM.")
        return stats

    # Classificar cada registro
    updates_fator = []      # (id, novo_fator) — atualizar fator_conversao
    updates_unidade = []    # (id, unidade_xml) — preencher unidade_medida_cliente NULL

    for row in rows:
        dp_id = row[0]
        nosso_codigo = row[1]
        prefixo = row[2]
        codigo_cli = row[3]
        # row[4] = descricao_nosso (presente no SELECT para debug manual)
        unidade_cli = row[5]
        # row[6] = unidade_medida_nosso (presente no SELECT para debug manual)
        nome_produto = row[7]
        novo_fator = row[8]
        unidade_xml = row[9]

        if unidade_xml:
            stats['unidade_encontrada_xml'] += 1

            if _eh_unidade(unidade_xml):
                stats['unidade_tipo_unidade'] += 1
                updates_fator.append((dp_id, novo_fator))

                # Se unidade_medida_cliente é NULL, preencher com a do XML
                if not unidade_cli:
                    updates_unidade.append((dp_id, unidade_xml))

                logger.info(
                    f"  [UPDATE] id={dp_id} | {prefixo}/{codigo_cli} -> {nosso_codigo} | "
                    f"'{nome_produto}' | fator: 1.0 -> {novo_fator} | "
                    f"unidade_xml={unidade_xml}"
                )
            else:
                stats['unidade_tipo_caixa'] += 1
                logger.debug(
                    f"  [SKIP-CX] id={dp_id} | {prefixo}/{codigo_cli} | "
                    f"unidade_xml='{unidade_xml}' (tipo caixa, fator=1.0 correto)"
                )
        else:
            stats['sem_unidade_xml'] += 1
            logger.debug(
                f"  [SKIP-NULL] id={dp_id} | {prefixo}/{codigo_cli} | "
                f"sem unidade no XML (não atualizar)"
            )

    logger.info(f"\n  Resumo análise:")
    logger.info(f"    Unidade encontrada no XML:  {stats['unidade_encontrada_xml']}")
    logger.info(f"    - Tipo UNIDADE (atualizar): {stats['unidade_tipo_unidade']}")
    logger.info(f"    - Tipo CAIXA (manter):      {stats['unidade_tipo_caixa']}")
    logger.info(f"    Sem unidade no XML (manter): {stats['sem_unidade_xml']}")

    # -------------------------------------------------------------------------
    # Execução
    # -------------------------------------------------------------------------
    if dry_run:
        stats['atualizados_fator'] = len(updates_fator)
        stats['atualizados_unidade'] = len(updates_unidade)
        logger.info(f"\n  DRY-RUN: {len(updates_fator)} fator + {len(updates_unidade)} unidade seriam atualizados")
        return stats

    # Step 1: Preencher unidade_medida_cliente onde NULL
    if updates_unidade:
        logger.info(f"\n  Preenchendo unidade_medida_cliente para {len(updates_unidade)} registros...")
        try:
            for dp_id, unidade_xml in updates_unidade:
                db.session.execute(text("""
                    UPDATE depara_produto_cliente
                    SET unidade_medida_cliente = :unidade,
                        atualizado_em = NOW(),
                        atualizado_por = 'backfill_fator_conversao'
                    WHERE id = :id AND unidade_medida_cliente IS NULL
                """), {'unidade': unidade_xml, 'id': dp_id})
                stats['atualizados_unidade'] += 1
            db.session.commit()
            logger.info(f"    {stats['atualizados_unidade']} unidades preenchidas")
        except Exception as e:
            db.session.rollback()
            logger.error(f"    Erro ao preencher unidades: {e}")
            stats['erros'] += len(updates_unidade)

    # Step 2: Atualizar fator_conversao
    if updates_fator:
        logger.info(f"\n  Atualizando fator_conversao para {len(updates_fator)} registros...")
        CHUNK_SIZE = 50
        for i in range(0, len(updates_fator), CHUNK_SIZE):
            chunk = updates_fator[i:i + CHUNK_SIZE]
            try:
                for dp_id, novo_fator in chunk:
                    db.session.execute(text("""
                        UPDATE depara_produto_cliente
                        SET fator_conversao = :fator,
                            unidade_medida_nosso = COALESCE(unidade_medida_nosso, 'CX'),
                            atualizado_em = NOW(),
                            atualizado_por = 'backfill_fator_conversao'
                        WHERE id = :id
                    """), {'fator': novo_fator, 'id': dp_id})
                    stats['atualizados_fator'] += 1
                db.session.commit()
                logger.info(f"    Chunk {i // CHUNK_SIZE + 1}: {len(chunk)} registros")
            except Exception as e:
                db.session.rollback()
                stats['erros'] += len(chunk)
                logger.error(f"    Erro no chunk {i // CHUNK_SIZE + 1}: {e}")

    return stats


def _fase_b_portal_atacadao(dry_run: bool) -> dict:
    """
    Fase B: portal_atacadao_produto_depara

    JOIN nf_devolucao_linha via SUBSTRING(cnpj, 1, 8) + codigo_atacadao.
    Tabela NÃO tem campos unidade_medida_cliente/nosso nem atualizado_por.
    """
    stats = {
        'total_fator_1': 0,
        'com_padrao_nxm': 0,
        'unidade_encontrada_xml': 0,
        'unidade_tipo_unidade': 0,
        'unidade_tipo_caixa': 0,
        'sem_unidade_xml': 0,
        'atualizados': 0,
        'erros': 0,
    }

    logger.info("\n" + "=" * 70)
    logger.info("FASE B: portal_atacadao_produto_depara")
    logger.info("=" * 70)

    # Contar total
    total_query = text("""
        SELECT COUNT(*) FROM portal_atacadao_produto_depara
        WHERE fator_conversao = 1.0 AND ativo = true
    """)
    stats['total_fator_1'] = db.session.execute(total_query).scalar()

    # Análise com unidade do XML
    analysis_query = text("""
        SELECT
            dp.id,
            dp.codigo_nosso,
            dp.codigo_atacadao,
            dp.cnpj_cliente,
            cp.nome_produto,
            CAST(SUBSTRING(cp.nome_produto FROM '(\\d+)[Xx]\\d+') AS INTEGER) AS novo_fator,
            latest_xml.unidade_medida AS unidade_xml
        FROM portal_atacadao_produto_depara dp
        JOIN cadastro_palletizacao cp ON dp.codigo_nosso = cp.cod_produto
        LEFT JOIN LATERAL (
            SELECT ndl.unidade_medida
            FROM nf_devolucao_linha ndl
            JOIN nf_devolucao nd ON ndl.nf_devolucao_id = nd.id
            WHERE ndl.codigo_produto_cliente = dp.codigo_atacadao
              AND dp.cnpj_cliente IS NOT NULL
              AND SUBSTRING(nd.cnpj_emitente, 1, 8) = SUBSTRING(dp.cnpj_cliente, 1, 8)
              AND ndl.unidade_medida IS NOT NULL
            ORDER BY nd.data_registro DESC
            LIMIT 1
        ) latest_xml ON true
        WHERE dp.fator_conversao = 1.0
          AND dp.ativo = true
          AND cp.nome_produto ~ '\\d+[Xx]\\d+'
          AND CAST(SUBSTRING(cp.nome_produto FROM '(\\d+)[Xx]\\d+') AS INTEGER) > 1
        ORDER BY dp.id
    """)

    rows = db.session.execute(analysis_query).fetchall()
    stats['com_padrao_nxm'] = len(rows)

    logger.info(f"  Total com fator=1.0:    {stats['total_fator_1']}")
    logger.info(f"  Com padrão NxM:         {stats['com_padrao_nxm']}")

    if not rows:
        logger.info("  Nenhum candidato com padrão NxM.")
        return stats

    updates = []

    for row in rows:
        dp_id = row[0]
        codigo_nosso = row[1]
        codigo_atacadao = row[2]
        cnpj = row[3]
        nome_produto = row[4]
        novo_fator = row[5]
        unidade_xml = row[6]

        if unidade_xml:
            stats['unidade_encontrada_xml'] += 1
            if _eh_unidade(unidade_xml):
                stats['unidade_tipo_unidade'] += 1
                updates.append((dp_id, novo_fator))
                logger.info(
                    f"  [UPDATE] id={dp_id} | {cnpj}/{codigo_atacadao} -> {codigo_nosso} | "
                    f"'{nome_produto}' | fator: 1.0 -> {novo_fator} | "
                    f"unidade_xml={unidade_xml}"
                )
            else:
                stats['unidade_tipo_caixa'] += 1
                logger.debug(
                    f"  [SKIP-CX] id={dp_id} | unidade_xml='{unidade_xml}'"
                )
        else:
            stats['sem_unidade_xml'] += 1
            logger.debug(f"  [SKIP-NULL] id={dp_id} | sem unidade no XML")

    logger.info(f"\n  Resumo análise:")
    logger.info(f"    Unidade encontrada no XML:  {stats['unidade_encontrada_xml']}")
    logger.info(f"    - Tipo UNIDADE (atualizar): {stats['unidade_tipo_unidade']}")
    logger.info(f"    - Tipo CAIXA (manter):      {stats['unidade_tipo_caixa']}")
    logger.info(f"    Sem unidade no XML (manter): {stats['sem_unidade_xml']}")

    if dry_run:
        stats['atualizados'] = len(updates)
        logger.info(f"\n  DRY-RUN: {len(updates)} registros seriam atualizados")
        return stats

    if updates:
        logger.info(f"\n  Atualizando {len(updates)} registros...")
        try:
            for dp_id, novo_fator in updates:
                db.session.execute(text("""
                    UPDATE portal_atacadao_produto_depara
                    SET fator_conversao = :fator,
                        atualizado_em = NOW()
                    WHERE id = :id
                """), {'fator': novo_fator, 'id': dp_id})
                stats['atualizados'] += 1
            db.session.commit()
            logger.info(f"    {stats['atualizados']} registros atualizados")
        except Exception as e:
            db.session.rollback()
            stats['erros'] += len(updates)
            logger.error(f"    Erro: {e}")

    return stats


def _fase_c_portal_sendas(dry_run: bool) -> dict:
    """
    Fase C: portal_sendas_produto_depara

    JOIN nf_devolucao_linha via SUBSTRING(cnpj, 1, 8) + codigo_sendas.
    Tabela NÃO tem campos unidade_medida_cliente/nosso nem atualizado_por.
    """
    stats = {
        'total_fator_1': 0,
        'com_padrao_nxm': 0,
        'unidade_encontrada_xml': 0,
        'unidade_tipo_unidade': 0,
        'unidade_tipo_caixa': 0,
        'sem_unidade_xml': 0,
        'atualizados': 0,
        'erros': 0,
    }

    logger.info("\n" + "=" * 70)
    logger.info("FASE C: portal_sendas_produto_depara")
    logger.info("=" * 70)

    # Contar total
    total_query = text("""
        SELECT COUNT(*) FROM portal_sendas_produto_depara
        WHERE fator_conversao = 1.0 AND ativo = true
    """)
    stats['total_fator_1'] = db.session.execute(total_query).scalar()

    # Análise com unidade do XML
    analysis_query = text("""
        SELECT
            dp.id,
            dp.codigo_nosso,
            dp.codigo_sendas,
            dp.cnpj_cliente,
            cp.nome_produto,
            CAST(SUBSTRING(cp.nome_produto FROM '(\\d+)[Xx]\\d+') AS INTEGER) AS novo_fator,
            latest_xml.unidade_medida AS unidade_xml
        FROM portal_sendas_produto_depara dp
        JOIN cadastro_palletizacao cp ON dp.codigo_nosso = cp.cod_produto
        LEFT JOIN LATERAL (
            SELECT ndl.unidade_medida
            FROM nf_devolucao_linha ndl
            JOIN nf_devolucao nd ON ndl.nf_devolucao_id = nd.id
            WHERE ndl.codigo_produto_cliente = dp.codigo_sendas
              AND dp.cnpj_cliente IS NOT NULL
              AND SUBSTRING(nd.cnpj_emitente, 1, 8) = SUBSTRING(dp.cnpj_cliente, 1, 8)
              AND ndl.unidade_medida IS NOT NULL
            ORDER BY nd.data_registro DESC
            LIMIT 1
        ) latest_xml ON true
        WHERE dp.fator_conversao = 1.0
          AND dp.ativo = true
          AND cp.nome_produto ~ '\\d+[Xx]\\d+'
          AND CAST(SUBSTRING(cp.nome_produto FROM '(\\d+)[Xx]\\d+') AS INTEGER) > 1
        ORDER BY dp.id
    """)

    rows = db.session.execute(analysis_query).fetchall()
    stats['com_padrao_nxm'] = len(rows)

    logger.info(f"  Total com fator=1.0:    {stats['total_fator_1']}")
    logger.info(f"  Com padrão NxM:         {stats['com_padrao_nxm']}")

    if not rows:
        logger.info("  Nenhum candidato com padrão NxM.")
        return stats

    updates = []

    for row in rows:
        dp_id = row[0]
        codigo_nosso = row[1]
        codigo_sendas = row[2]
        cnpj = row[3]
        nome_produto = row[4]
        novo_fator = row[5]
        unidade_xml = row[6]

        if unidade_xml:
            stats['unidade_encontrada_xml'] += 1
            if _eh_unidade(unidade_xml):
                stats['unidade_tipo_unidade'] += 1
                updates.append((dp_id, novo_fator))
                logger.info(
                    f"  [UPDATE] id={dp_id} | {cnpj}/{codigo_sendas} -> {codigo_nosso} | "
                    f"'{nome_produto}' | fator: 1.0 -> {novo_fator} | "
                    f"unidade_xml={unidade_xml}"
                )
            else:
                stats['unidade_tipo_caixa'] += 1
                logger.debug(
                    f"  [SKIP-CX] id={dp_id} | unidade_xml='{unidade_xml}'"
                )
        else:
            stats['sem_unidade_xml'] += 1
            logger.debug(f"  [SKIP-NULL] id={dp_id} | sem unidade no XML")

    logger.info(f"\n  Resumo análise:")
    logger.info(f"    Unidade encontrada no XML:  {stats['unidade_encontrada_xml']}")
    logger.info(f"    - Tipo UNIDADE (atualizar): {stats['unidade_tipo_unidade']}")
    logger.info(f"    - Tipo CAIXA (manter):      {stats['unidade_tipo_caixa']}")
    logger.info(f"    Sem unidade no XML (manter): {stats['sem_unidade_xml']}")

    if dry_run:
        stats['atualizados'] = len(updates)
        logger.info(f"\n  DRY-RUN: {len(updates)} registros seriam atualizados")
        return stats

    if updates:
        logger.info(f"\n  Atualizando {len(updates)} registros...")
        try:
            for dp_id, novo_fator in updates:
                db.session.execute(text("""
                    UPDATE portal_sendas_produto_depara
                    SET fator_conversao = :fator,
                        atualizado_em = NOW()
                    WHERE id = :id
                """), {'fator': novo_fator, 'id': dp_id})
                stats['atualizados'] += 1
            db.session.commit()
            logger.info(f"    {stats['atualizados']} registros atualizados")
        except Exception as e:
            db.session.rollback()
            stats['erros'] += len(updates)
            logger.error(f"    Erro: {e}")

    return stats


def _fase_d_recalcular_quantidade_convertida(dry_run: bool) -> dict:
    """
    Fase D: Recalcular quantidade_convertida em nf_devolucao_linha

    Após atualizar fator_conversao nas tabelas de-para (Fases A/B/C),
    recalcula quantidade_convertida para linhas históricas onde:
    - produto_resolvido = true
    - unidade_medida é tipo UNIDADE (substring match)
    - produto tem padrão NxM com N > 1 (via cadastro_palletizacao)
    - quantidade_convertida nunca foi calculada ou foi com fator=1 (= quantidade)
    """
    stats = {
        'candidatos_sql': 0,
        'candidatos_unidade': 0,
        'atualizados': 0,
        'erros': 0,
    }

    logger.info("\n" + "=" * 70)
    logger.info("FASE D: Recalcular quantidade_convertida (linhas históricas)")
    logger.info("=" * 70)

    # Buscar linhas candidatas: produto resolvido, com NxM, conversão ausente/incorreta
    query = text("""
        SELECT
            ndl.id,
            ndl.quantidade,
            ndl.quantidade_convertida,
            ndl.qtd_por_caixa,
            ndl.unidade_medida,
            ndl.codigo_produto_interno,
            cp.nome_produto,
            CAST(SUBSTRING(cp.nome_produto FROM '(\\d+)[Xx]\\d+') AS INTEGER) AS novo_fator,
            cp.peso_bruto AS peso_bruto_produto
        FROM nf_devolucao_linha ndl
        JOIN cadastro_palletizacao cp ON ndl.codigo_produto_interno = cp.cod_produto
        WHERE ndl.produto_resolvido = true
          AND ndl.quantidade IS NOT NULL
          AND ndl.quantidade > 0
          AND ndl.unidade_medida IS NOT NULL
          AND TRIM(ndl.unidade_medida) != ''
          AND cp.nome_produto ~ '\\d+[Xx]\\d+'
          AND CAST(SUBSTRING(cp.nome_produto FROM '(\\d+)[Xx]\\d+') AS INTEGER) > 1
          AND (
            ndl.quantidade_convertida IS NULL
            OR ndl.qtd_por_caixa IS NULL
            OR ndl.qtd_por_caixa <= 1
          )
        ORDER BY ndl.id
    """)

    rows = db.session.execute(query).fetchall()
    stats['candidatos_sql'] = len(rows)
    logger.info(f"  Candidatos SQL (resolvido + NxM + sem conversão): {len(rows)}")

    if not rows:
        logger.info("  Nenhuma linha para recalcular.")
        return stats

    # Filtrar por unidade tipo UNIDADE (Python-side, substring match)
    updates = []
    for row in rows:
        ndl_id = row[0]
        quantidade = float(row[1])
        qtd_convertida_atual = float(row[2]) if row[2] else None
        qtd_por_caixa_atual = row[3]
        unidade_medida = row[4]
        codigo_produto = row[5]
        # row[6] = nome_produto (presente no SELECT para debug manual)
        novo_fator = row[7]
        peso_bruto_produto = float(row[8]) if row[8] else None

        if not _eh_unidade(unidade_medida):
            continue

        stats['candidatos_unidade'] += 1

        nova_qtd_convertida = round(quantidade / novo_fator, 3)
        novo_peso = round(nova_qtd_convertida * peso_bruto_produto, 2) if peso_bruto_produto else None

        updates.append({
            'id': ndl_id,
            'qtd_por_caixa': novo_fator,
            'quantidade_convertida': nova_qtd_convertida,
            'peso_bruto': novo_peso,
        })

        logger.info(
            f"  [UPDATE] ndl.id={ndl_id} | {codigo_produto} | "
            f"un={unidade_medida} | qtd={quantidade} | "
            f"qtd_conv: {qtd_convertida_atual} -> {nova_qtd_convertida} | "
            f"fator: {qtd_por_caixa_atual or 1} -> {novo_fator}"
        )

    logger.info(f"\n  Resumo análise:")
    logger.info(f"    Candidatos SQL:              {stats['candidatos_sql']}")
    logger.info(f"    Tipo UNIDADE (recalcular):    {stats['candidatos_unidade']}")
    logger.info(f"    Tipo CAIXA/OUTRO (skip):      {stats['candidatos_sql'] - stats['candidatos_unidade']}")

    if dry_run:
        stats['atualizados'] = len(updates)
        logger.info(f"\n  DRY-RUN: {len(updates)} linhas seriam recalculadas")
        return stats

    if updates:
        logger.info(f"\n  Recalculando {len(updates)} linhas...")
        CHUNK_SIZE = 100
        for i in range(0, len(updates), CHUNK_SIZE):
            chunk = updates[i:i + CHUNK_SIZE]
            try:
                for upd in chunk:
                    if upd['peso_bruto'] is not None:
                        db.session.execute(text("""
                            UPDATE nf_devolucao_linha
                            SET qtd_por_caixa = :qtd_por_caixa,
                                quantidade_convertida = :quantidade_convertida,
                                peso_bruto = :peso_bruto,
                                atualizado_em = NOW()
                            WHERE id = :id
                        """), {
                            'id': upd['id'],
                            'qtd_por_caixa': upd['qtd_por_caixa'],
                            'quantidade_convertida': upd['quantidade_convertida'],
                            'peso_bruto': upd['peso_bruto'],
                        })
                    else:
                        db.session.execute(text("""
                            UPDATE nf_devolucao_linha
                            SET qtd_por_caixa = :qtd_por_caixa,
                                quantidade_convertida = :quantidade_convertida,
                                atualizado_em = NOW()
                            WHERE id = :id
                        """), {
                            'id': upd['id'],
                            'qtd_por_caixa': upd['qtd_por_caixa'],
                            'quantidade_convertida': upd['quantidade_convertida'],
                        })

                    stats['atualizados'] += 1

                db.session.commit()
                logger.info(f"    Chunk {i // CHUNK_SIZE + 1}: {len(chunk)} linhas")
            except Exception as e:
                db.session.rollback()
                stats['erros'] += len(chunk)
                logger.error(f"    Erro no chunk {i // CHUNK_SIZE + 1}: {e}")

    return stats


def backfill_fator_conversao(dry_run: bool = True) -> dict:
    """
    Orquestra o backfill nas 3 tabelas de De-Para.

    Returns:
        dict com estatísticas consolidadas
    """
    logger.info("=" * 70)
    logger.info("BACKFILL fator_conversao — 3 TABELAS DE-PARA")
    logger.info(f"Modo: {'DRY-RUN (nenhuma alteração será feita)' if dry_run else 'EXECUÇÃO REAL'}")
    logger.info(f"Regra: Só atualiza se unidade do XML (nf_devolucao_linha) for tipo UNIDADE")
    logger.info("=" * 70)

    # Fases A/B/C: Atualizar fator_conversao nas tabelas de-para
    stats_a = _fase_a_depara_produto_cliente(dry_run)
    stats_b = _fase_b_portal_atacadao(dry_run)
    stats_c = _fase_c_portal_sendas(dry_run)

    # Fase D: Recalcular quantidade_convertida em linhas históricas
    stats_d = _fase_d_recalcular_quantidade_convertida(dry_run)

    # Relatório consolidado
    total_depara_atualizados = (
        stats_a.get('atualizados_fator', 0)
        + stats_b.get('atualizados', 0)
        + stats_c.get('atualizados', 0)
    )
    total_linhas_recalculadas = stats_d.get('atualizados', 0)
    total_erros = (
        stats_a.get('erros', 0)
        + stats_b.get('erros', 0)
        + stats_c.get('erros', 0)
        + stats_d.get('erros', 0)
    )

    logger.info("\n" + "=" * 70)
    logger.info("RELATÓRIO CONSOLIDADO")
    logger.info("=" * 70)
    logger.info(f"  FASE A (depara_produto_cliente):")
    logger.info(f"    Total fator=1.0:         {stats_a['total_fator_1']}")
    logger.info(f"    Com NxM:                 {stats_a['com_padrao_nxm']}")
    logger.info(f"    Unidade XML encontrada:  {stats_a['unidade_encontrada_xml']}")
    logger.info(f"    Tipo UNIDADE (update):   {stats_a['unidade_tipo_unidade']}")
    logger.info(f"    Tipo CAIXA (skip):       {stats_a['unidade_tipo_caixa']}")
    logger.info(f"    Sem unidade XML (skip):  {stats_a['sem_unidade_xml']}")
    logger.info(f"    Fator atualizados:       {stats_a['atualizados_fator']}")
    logger.info(f"    Unidade preenchida:      {stats_a['atualizados_unidade']}")

    logger.info(f"\n  FASE B (portal_atacadao):")
    logger.info(f"    Total fator=1.0:         {stats_b['total_fator_1']}")
    logger.info(f"    Com NxM:                 {stats_b['com_padrao_nxm']}")
    logger.info(f"    Unidade XML encontrada:  {stats_b['unidade_encontrada_xml']}")
    logger.info(f"    Tipo UNIDADE (update):   {stats_b['unidade_tipo_unidade']}")
    logger.info(f"    Tipo CAIXA (skip):       {stats_b['unidade_tipo_caixa']}")
    logger.info(f"    Sem unidade XML (skip):  {stats_b['sem_unidade_xml']}")
    logger.info(f"    Atualizados:             {stats_b['atualizados']}")

    logger.info(f"\n  FASE C (portal_sendas):")
    logger.info(f"    Total fator=1.0:         {stats_c['total_fator_1']}")
    logger.info(f"    Com NxM:                 {stats_c['com_padrao_nxm']}")
    logger.info(f"    Unidade XML encontrada:  {stats_c['unidade_encontrada_xml']}")
    logger.info(f"    Tipo UNIDADE (update):   {stats_c['unidade_tipo_unidade']}")
    logger.info(f"    Tipo CAIXA (skip):       {stats_c['unidade_tipo_caixa']}")
    logger.info(f"    Sem unidade XML (skip):  {stats_c['sem_unidade_xml']}")
    logger.info(f"    Atualizados:             {stats_c['atualizados']}")

    logger.info(f"\n  FASE D (recalcular quantidade_convertida):")
    logger.info(f"    Candidatos SQL:          {stats_d['candidatos_sql']}")
    logger.info(f"    Tipo UNIDADE:            {stats_d['candidatos_unidade']}")
    logger.info(f"    Recalculados:            {stats_d['atualizados']}")

    logger.info(f"\n  TOTAL CONSOLIDADO:")
    logger.info(f"    De-para {'seriam atualizados' if dry_run else 'atualizados'}:     {total_depara_atualizados}")
    logger.info(f"    Linhas {'seriam recalculadas' if dry_run else 'recalculadas'}:     {total_linhas_recalculadas}")
    logger.info(f"    Erros: {total_erros}")

    if dry_run:
        logger.info("\n>>> DRY-RUN: nenhuma alteração foi feita. Use --execute para aplicar. <<<")

    return {
        'fase_a': stats_a,
        'fase_b': stats_b,
        'fase_c': stats_c,
        'fase_d': stats_d,
        'total_depara_atualizados': total_depara_atualizados,
        'total_linhas_recalculadas': total_linhas_recalculadas,
        'total_erros': total_erros,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Backfill fator_conversao em 3 tabelas De-Para'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Executa de fato (default: dry-run)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mostra registros com SKIP (debug level)'
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger(__name__).setLevel(logging.DEBUG)

    app = create_app()
    with app.app_context():
        result = backfill_fator_conversao(dry_run=not args.execute)

    return 0 if result['total_erros'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reconciliação Completa Odoo ↔ Local (Contas a Receber + Pagar)
==============================================================

Compara TODOS os títulos elegíveis no Odoo com os registros locais.
Identifica gaps em AMBAS as direções:
- Títulos no Odoo que faltam no local (não importados)
- Títulos locais sem correspondência no Odoo (órfãos)

Causas raiz dos gaps:
- limit=5000 na sync incremental (corrigido com paginação)
- Sync full usa filtros restritivos (balance > 0 / amount_residual < 0)
- Títulos antigos criados antes da implantação da sync

Uso:
    # Diagnóstico completo (sem importar)
    python scripts/reconciliar_titulos_odoo.py --dry-run

    # Diagnóstico apenas receber
    python scripts/reconciliar_titulos_odoo.py --tipo receber --dry-run

    # Importar faltantes elegíveis
    python scripts/reconciliar_titulos_odoo.py --importar

    # Importar apenas empresa FB (Odoo company_id=1)
    python scripts/reconciliar_titulos_odoo.py --empresa 1 --importar

Autor: Sistema de Fretes
Data: 2026-02-22
"""

import argparse
import logging
import sys
import os

# Setup path para imports do app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.utils.timezone import agora_utc_naive
from app.odoo.utils.connection import get_odoo_connection
from app.financeiro.models import ContasAReceber, ContasAPagar

logger = logging.getLogger(__name__)

# ===================================================================
# CONSTANTES
# ===================================================================

# Odoo company_ids elegíveis para sincronização
# FONTE: .claude/references/odoo/IDS_FIXOS.md:10-15
# FB=1, SC=3, CD=4 (LF=5 não é mapeada localmente)
ODOO_COMPANY_IDS_ELEGIVEIS = [1, 3, 4]


def configurar_logging(verbose=False):
    """Configura logging para o script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


# ===================================================================
# FUNÇÕES DE BUSCA
# ===================================================================

def buscar_ids_odoo_paginado(connection, filtros, batch_size=1000):
    """
    Busca TODOS os IDs elegíveis no Odoo usando paginação.

    Usa execute_kw direto porque connection.search() não suporta offset.
    FONTE: app/odoo/utils/connection.py:255-261

    Args:
        connection: Conexão Odoo autenticada
        filtros: Domain filters para search
        batch_size: Tamanho do batch (default 1000)

    Returns:
        list[int]: Todos os IDs encontrados
    """
    todos_ids = []
    offset = 0
    while True:
        ids = connection.execute_kw(
            'account.move.line', 'search', [filtros],
            {'limit': batch_size, 'offset': offset}
        )
        if not ids:
            break
        todos_ids.extend(ids)
        offset += batch_size
        logger.info(
            f"   📄 Página {offset // batch_size}: "
            f"+{len(ids)} IDs (total: {len(todos_ids)})"
        )
    return todos_ids


def buscar_odoo_line_ids_locais(tipo):
    """
    Busca TODOS os odoo_line_ids do banco local.

    Args:
        tipo: 'receber' ou 'pagar'

    Returns:
        set[int]: Set de odoo_line_ids existentes localmente
    """
    Model = ContasAReceber if tipo == 'receber' else ContasAPagar

    results = db.session.query(Model.odoo_line_id).filter(
        Model.odoo_line_id.isnot(None)
    ).all()

    return set(r[0] for r in results)


def contar_registros_locais_total(tipo):
    """
    Conta TODOS os registros locais (com e sem odoo_line_id).

    Args:
        tipo: 'receber' ou 'pagar'

    Returns:
        tuple[int, int]: (total, com_odoo_line_id)
    """
    Model = ContasAReceber if tipo == 'receber' else ContasAPagar

    total = db.session.query(Model.id).count()
    com_line_id = db.session.query(Model.id).filter(
        Model.odoo_line_id.isnot(None)
    ).count()

    return total, com_line_id


# ===================================================================
# CATEGORIZAÇÃO
# ===================================================================

def categorizar_faltantes(connection, ids_faltantes, batch_size=500):
    """
    Busca detalhes dos IDs faltantes e categoriza.

    Categorias:
    - elegiveis: têm NF-e, vencimento, empresa mapeada → importáveis
    - sem_nf: x_studio_nf_e é False/vazio
    - sem_vencimento: date_maturity é False
    - empresa_nao_mapeada: company_id não está em [1, 3, 4]
    - nao_posted: parent_state mudou desde o search inicial

    Args:
        connection: Conexão Odoo autenticada
        ids_faltantes: list[int] de IDs para categorizar
        batch_size: Tamanho do batch para read

    Returns:
        dict com categorias e contagens
    """
    resultado = {
        'elegiveis': [],
        'sem_nf': 0,
        'sem_vencimento': 0,
        'empresa_nao_mapeada': 0,
        'nao_posted': 0,
        'erro_leitura': 0,
        'total': len(ids_faltantes),
    }

    campos_minimos = [
        'id', 'company_id', 'x_studio_nf_e',
        'date_maturity', 'parent_state'
    ]

    for i in range(0, len(ids_faltantes), batch_size):
        batch = ids_faltantes[i:i + batch_size]
        try:
            records = connection.read('account.move.line', batch, campos_minimos)
            if not records:
                resultado['erro_leitura'] += len(batch)
                continue

            for r in records:
                company_id = r.get('company_id', [None, None])
                if isinstance(company_id, (list, tuple)):
                    company_id = company_id[0]

                nf = r.get('x_studio_nf_e')
                vencimento = r.get('date_maturity')
                parent_state = r.get('parent_state')

                if parent_state != 'posted':
                    resultado['nao_posted'] += 1
                elif not nf or nf is False:
                    resultado['sem_nf'] += 1
                elif not vencimento or vencimento is False:
                    resultado['sem_vencimento'] += 1
                elif company_id not in ODOO_COMPANY_IDS_ELEGIVEIS:
                    resultado['empresa_nao_mapeada'] += 1
                else:
                    resultado['elegiveis'].append(r['id'])

        except Exception as e:
            logger.error(f"   ❌ Erro ao categorizar batch {i}: {e}")
            resultado['erro_leitura'] += len(batch)
            continue

        processados = min(i + batch_size, len(ids_faltantes))
        if processados % 2000 == 0 or processados == len(ids_faltantes):
            logger.info(
                f"   📊 Categorizados: {processados}/{len(ids_faltantes)} "
                f"(elegíveis até agora: {len(resultado['elegiveis'])})"
            )

    return resultado


# ===================================================================
# IMPORTAÇÃO — CONTAS A RECEBER
# ===================================================================

def importar_receber(connection, ids_elegiveis, dry_run=False, batch_size=500):
    """
    Importa títulos a receber faltantes do Odoo.

    Reutiliza a lógica do SincronizacaoContasReceberService:
    - _buscar_dados_parceiros() para enriquecer com CNPJ/UF
    - Transformação idêntica a _sincronizar_por_write_date (linhas 268-301)
    - _processar_registro() para criar/atualizar

    FONTE: sincronizacao_contas_receber_service.py:457

    Args:
        connection: Conexão Odoo autenticada
        ids_elegiveis: list[int] de IDs a importar
        dry_run: Se True, apenas simula
        batch_size: Tamanho do batch

    Returns:
        dict com estatísticas {novos, atualizados, erros}
    """
    from app.financeiro.services.sincronizacao_contas_receber_service import (
        SincronizacaoContasReceberService
    )

    stats = {'novos': 0, 'atualizados': 0, 'erros': 0}

    if dry_run:
        logger.info(f"   🔍 DRY RUN: {len(ids_elegiveis)} títulos seriam importados")
        return stats

    service = SincronizacaoContasReceberService()
    service._resetar_estatisticas()

    # Mesmos campos usados em _sincronizar_por_write_date
    # FONTE: sincronizacao_contas_receber_service.py:228-236
    campos = [
        'company_id', 'x_studio_tipo_de_documento_fiscal',
        'x_studio_nf_e', 'l10n_br_cobranca_parcela', 'l10n_br_paga',
        'partner_id', 'date', 'date_maturity',
        'balance', 'amount_residual', 'desconto_concedido',
        'desconto_concedido_percentual',
        'payment_provider_id', 'x_studio_status_de_pagamento',
        'account_type', 'move_type', 'parent_state',
        'write_date', 'create_date',
    ]

    for i in range(0, len(ids_elegiveis), batch_size):
        batch_ids = ids_elegiveis[i:i + batch_size]

        try:
            # Buscar dados completos
            records = connection.read('account.move.line', batch_ids, campos)
            if not records:
                continue

            # Buscar parceiros para enriquecimento
            partner_ids = list(set(
                r.get('partner_id', [None, None])[0]
                for r in records if r.get('partner_id')
            ))
            partner_map = service._buscar_dados_parceiros(connection, partner_ids)

            # Transformar registros para formato esperado por _processar_registro
            # Mesma lógica de _sincronizar_por_write_date:268-301
            registros_transformados = []
            for record in records:
                partner_id = record.get('partner_id', [None, None])[0]
                p_data = partner_map.get(partner_id, {})

                balance = float(record.get('balance', 0) or 0)
                desconto = float(record.get('desconto_concedido', 0) or 0)

                transformed = {
                    'odoo_line_id': record.get('id'),
                    'company_id_nome': record.get('company_id', [None, ''])[1] or '',
                    'x_studio_nf_e': record.get('x_studio_nf_e'),
                    'l10n_br_cobranca_parcela': record.get('l10n_br_cobranca_parcela'),
                    'partner_id_nome': record.get('partner_id', [None, ''])[1] or '',
                    'partner_cnpj': p_data.get('cnpj'),
                    'partner_raz_social': p_data.get('raz_social'),
                    'partner_raz_social_red': p_data.get('raz_social_red'),
                    'partner_state': p_data.get('uf'),
                    'date': record.get('date'),
                    'date_maturity': record.get('date_maturity'),
                    'desconto_concedido_percentual': record.get(
                        'desconto_concedido_percentual', 0
                    ),
                    'saldo_total': balance + desconto,
                    'amount_residual': float(record.get('amount_residual', 0) or 0),
                    'payment_provider_id_nome': (
                        record.get('payment_provider_id', [None, None])[1]
                        if isinstance(
                            record.get('payment_provider_id'), (list, tuple)
                        )
                        else None
                    ),
                    'l10n_br_paga': record.get('l10n_br_paga'),
                    'x_studio_status_de_pagamento': record.get(
                        'x_studio_status_de_pagamento'
                    ),
                }
                registros_transformados.append(transformed)

            # Pre-carregar existentes para este batch (evita N+1)
            odoo_line_ids = [
                r.get('odoo_line_id') for r in registros_transformados
                if r.get('odoo_line_id')
            ]
            contas_por_line_id = {}
            for c in ContasAReceber.query.filter(
                ContasAReceber.odoo_line_id.in_(odoo_line_ids)
            ).all():
                if c.odoo_line_id:
                    contas_por_line_id[c.odoo_line_id] = c

            # Processar cada registro
            for row in registros_transformados:
                try:
                    service._processar_registro(row, contas_por_line_id, {})
                except Exception as e:
                    logger.error(f"   ❌ Erro processando receber: {e}")
                    service.estatisticas['erros'] += 1

            db.session.commit()
            batch_num = i // batch_size + 1
            total_batches = (len(ids_elegiveis) + batch_size - 1) // batch_size
            logger.info(
                f"   ✅ Batch {batch_num}/{total_batches}: "
                f"{len(records)} processados "
                f"(novos: {service.estatisticas['novos']}, "
                f"erros: {service.estatisticas['erros']})"
            )

        except Exception as e:
            logger.error(f"   ❌ Erro no batch {i}: {e}")
            db.session.rollback()
            stats['erros'] += len(batch_ids)

    stats['novos'] = service.estatisticas['novos']
    stats['atualizados'] = service.estatisticas['atualizados']
    stats['erros'] += service.estatisticas['erros']
    return stats


# ===================================================================
# IMPORTAÇÃO — CONTAS A PAGAR
# ===================================================================

def importar_pagar(connection, ids_elegiveis, dry_run=False, batch_size=500):
    """
    Importa títulos a pagar faltantes do Odoo.

    Reutiliza a lógica do SincronizacaoContasAPagarService:
    - _buscar_cnpjs_fornecedores() para enriquecer com CNPJ
    - _processar_registro() para criar/atualizar (aceita raw Odoo dict)

    FONTE: sincronizacao_contas_pagar_service.py:443

    Args:
        connection: Conexão Odoo autenticada
        ids_elegiveis: list[int] de IDs a importar
        dry_run: Se True, apenas simula
        batch_size: Tamanho do batch

    Returns:
        dict com estatísticas {novos, atualizados, erros}
    """
    from app.financeiro.services.sincronizacao_contas_pagar_service import (
        SincronizacaoContasAPagarService
    )

    stats = {'novos': 0, 'atualizados': 0, 'erros': 0}

    if dry_run:
        logger.info(f"   🔍 DRY RUN: {len(ids_elegiveis)} títulos seriam importados")
        return stats

    service = SincronizacaoContasAPagarService(connection=connection)
    service._resetar_estatisticas()

    for i in range(0, len(ids_elegiveis), batch_size):
        batch_ids = ids_elegiveis[i:i + batch_size]

        try:
            # Buscar dados completos (mesmos campos do service)
            # FONTE: sincronizacao_contas_pagar_service.py:42-61
            records = connection.read(
                'account.move.line', batch_ids, service.CAMPOS_ODOO
            )
            if not records:
                continue

            # Buscar CNPJs dos fornecedores
            partner_ids = list(set(
                r.get('partner_id', [None, None])[0]
                for r in records if r.get('partner_id')
            ))
            cnpj_map = service._buscar_cnpjs_fornecedores(partner_ids)

            # Pre-carregar existentes para este batch (evita N+1)
            odoo_line_ids = [r.get('id') for r in records if r.get('id')]
            contas_por_line_id = {}
            for c in ContasAPagar.query.filter(
                ContasAPagar.odoo_line_id.in_(odoo_line_ids)
            ).all():
                if c.odoo_line_id:
                    contas_por_line_id[c.odoo_line_id] = c

            # Processar cada registro (aceita raw Odoo dict)
            for row in records:
                try:
                    service._processar_registro(
                        row, cnpj_map, contas_por_line_id, {}
                    )
                except Exception as e:
                    logger.error(f"   ❌ Erro processando pagar: {e}")
                    service.estatisticas['erros'] += 1

            db.session.commit()
            batch_num = i // batch_size + 1
            total_batches = (len(ids_elegiveis) + batch_size - 1) // batch_size
            logger.info(
                f"   ✅ Batch {batch_num}/{total_batches}: "
                f"{len(records)} processados "
                f"(novos: {service.estatisticas['novos']}, "
                f"erros: {service.estatisticas['erros']})"
            )

        except Exception as e:
            logger.error(f"   ❌ Erro no batch {i}: {e}")
            db.session.rollback()
            stats['erros'] += len(batch_ids)

    stats['novos'] = service.estatisticas['novos']
    stats['atualizados'] = service.estatisticas['atualizados']
    stats['erros'] += service.estatisticas['erros']
    return stats


# ===================================================================
# RECONCILIAÇÃO PRINCIPAL
# ===================================================================

def reconciliar_tipo(connection, tipo, empresa_filtro=None,
                     importar=False, dry_run=False):
    """
    Executa reconciliação para um tipo (receber ou pagar).

    Fluxo:
    1. Buscar TODOS os IDs elegíveis no Odoo (paginado, sem limit)
    2. Buscar TODOS os odoo_line_ids locais
    3. Comparar sets → faltantes + órfãos
    4. Categorizar faltantes (sem NF, sem vencimento, etc.)
    5. Relatório detalhado
    6. Opcionalmente importar elegíveis

    Args:
        connection: Conexão Odoo autenticada
        tipo: 'receber' ou 'pagar'
        empresa_filtro: Odoo company_id para filtrar (None = todas)
        importar: Se True, importa faltantes
        dry_run: Se True, apenas simula importação

    Returns:
        dict com resultado completo da reconciliação
    """
    tipo_label = "CONTAS A RECEBER" if tipo == 'receber' else "CONTAS A PAGAR"
    account_type = 'asset_receivable' if tipo == 'receber' else 'liability_payable'

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"🔍 RECONCILIAÇÃO: {tipo_label}")
    logger.info("=" * 70)

    # ---------------------------------------------------------------
    # 1. Buscar TODOS os IDs elegíveis no Odoo (paginado)
    # ---------------------------------------------------------------
    logger.info("\n[1/5] Buscando TODOS os IDs no Odoo (paginado)...")

    filtros = [
        ['account_type', '=', account_type],
        ['parent_state', '=', 'posted'],
    ]

    # Filtro de empresa (Odoo company_id)
    company_ids = ODOO_COMPANY_IDS_ELEGIVEIS
    if empresa_filtro:
        company_ids = [empresa_filtro]
    filtros.append(['company_id', 'in', company_ids])

    logger.info(f"   Filtros: {filtros}")

    odoo_ids = buscar_ids_odoo_paginado(connection, filtros)
    odoo_ids_set = set(odoo_ids)
    logger.info(f"   ✅ {len(odoo_ids_set)} IDs únicos no Odoo")

    # ---------------------------------------------------------------
    # 2. Buscar TODOS os odoo_line_ids locais
    # ---------------------------------------------------------------
    logger.info("\n[2/5] Buscando odoo_line_ids locais...")
    local_ids = buscar_odoo_line_ids_locais(tipo)
    total_local, com_line_id = contar_registros_locais_total(tipo)
    logger.info(
        f"   ✅ {len(local_ids)} com odoo_line_id "
        f"(total registros locais: {total_local})"
    )

    # ---------------------------------------------------------------
    # 3. Comparar sets
    # ---------------------------------------------------------------
    logger.info("\n[3/5] Comparando sets...")
    faltam_no_local = odoo_ids_set - local_ids
    orfaos_locais = local_ids - odoo_ids_set

    logger.info(f"   📊 Faltam no local (Odoo - Local): {len(faltam_no_local)}")
    logger.info(f"   📊 Órfãos locais (Local - Odoo):   {len(orfaos_locais)}")

    # ---------------------------------------------------------------
    # 4. Categorizar faltantes
    # ---------------------------------------------------------------
    logger.info("\n[4/5] Categorizando faltantes...")
    categorias = {
        'elegiveis': [], 'sem_nf': 0, 'sem_vencimento': 0,
        'empresa_nao_mapeada': 0, 'nao_posted': 0, 'erro_leitura': 0,
        'total': 0,
    }

    if faltam_no_local:
        categorias = categorizar_faltantes(
            connection, list(faltam_no_local)
        )

    # ---------------------------------------------------------------
    # 5. Relatório
    # ---------------------------------------------------------------
    logger.info("\n[5/5] Relatório")
    cobertura = (
        (len(local_ids) / len(odoo_ids_set) * 100) if odoo_ids_set else 0
    )
    cobertura_pos = (
        ((len(local_ids) + len(categorias['elegiveis'])) / len(odoo_ids_set) * 100)
        if odoo_ids_set else 0
    )

    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info(f"║  RELATÓRIO: {tipo_label:^48}║")
    logger.info("╠══════════════════════════════════════════════════════════════╣")
    logger.info(f"║  Total Odoo (posted, empresas mapeadas): {len(odoo_ids_set):>10,}        ║")
    logger.info(f"║  Total Local (registros):                {total_local:>10,}        ║")
    logger.info(f"║  Total Local (com odoo_line_id):         {com_line_id:>10,}        ║")
    logger.info(f"║  Cobertura atual:                        {cobertura:>9.1f}%        ║")
    logger.info("╠══════════════════════════════════════════════════════════════╣")
    logger.info(f"║  Faltam no local:                        {len(faltam_no_local):>10,}        ║")
    logger.info(f"║    → Elegíveis (importáveis):            {len(categorias['elegiveis']):>10,}        ║")
    logger.info(f"║    → Sem NF-e:                           {categorias['sem_nf']:>10,}        ║")
    logger.info(f"║    → Sem vencimento:                     {categorias['sem_vencimento']:>10,}        ║")
    logger.info(f"║    → Empresa não mapeada:                {categorias['empresa_nao_mapeada']:>10,}        ║")
    logger.info(f"║    → Não posted (race condition):        {categorias['nao_posted']:>10,}        ║")
    if categorias['erro_leitura'] > 0:
        logger.info(f"║    → Erro de leitura:                    {categorias['erro_leitura']:>10,}        ║")
    logger.info("╠══════════════════════════════════════════════════════════════╣")
    logger.info(f"║  Órfãos locais (sem match Odoo):         {len(orfaos_locais):>10,}        ║")
    logger.info("╠══════════════════════════════════════════════════════════════╣")
    logger.info(f"║  Cobertura pós-importação (projetada):   {cobertura_pos:>9.1f}%        ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")

    resultado = {
        'tipo': tipo,
        'odoo_total': len(odoo_ids_set),
        'local_total': total_local,
        'local_com_line_id': com_line_id,
        'cobertura_pct': round(cobertura, 1),
        'cobertura_projetada_pct': round(cobertura_pos, 1),
        'faltam_no_local': len(faltam_no_local),
        'elegiveis': len(categorias['elegiveis']),
        'sem_nf': categorias['sem_nf'],
        'sem_vencimento': categorias['sem_vencimento'],
        'empresa_nao_mapeada': categorias['empresa_nao_mapeada'],
        'nao_posted': categorias['nao_posted'],
        'orfaos_locais': len(orfaos_locais),
    }

    # ---------------------------------------------------------------
    # 6. Importar se solicitado
    # ---------------------------------------------------------------
    if importar and categorias['elegiveis']:
        modo = "DRY RUN" if dry_run else "IMPORTAÇÃO"
        logger.info("")
        logger.info(
            f"📥 {modo}: {len(categorias['elegiveis'])} títulos elegíveis..."
        )

        if tipo == 'receber':
            stats = importar_receber(
                connection, categorias['elegiveis'], dry_run
            )
        else:
            stats = importar_pagar(
                connection, categorias['elegiveis'], dry_run
            )

        logger.info(
            f"   📊 Resultado: +{stats['novos']} novos, "
            f"{stats['atualizados']} atualizados, "
            f"{stats['erros']} erros"
        )
        resultado['importacao'] = stats
    elif importar and not categorias['elegiveis']:
        logger.info("\n   ℹ️ Nenhum título elegível para importar")

    return resultado


# ===================================================================
# MAIN
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Reconciliação Odoo ↔ Local (Contas a Receber + Pagar)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Diagnóstico completo (recomendado executar primeiro)
  python scripts/reconciliar_titulos_odoo.py --dry-run

  # Diagnóstico apenas receber
  python scripts/reconciliar_titulos_odoo.py --tipo receber --dry-run

  # Importar faltantes (após validar com --dry-run)
  python scripts/reconciliar_titulos_odoo.py --importar

  # Importar apenas empresa FB
  python scripts/reconciliar_titulos_odoo.py --empresa 1 --importar

  # Importar com log detalhado
  python scripts/reconciliar_titulos_odoo.py --importar -v
        """
    )
    parser.add_argument(
        '--tipo', choices=['receber', 'pagar', 'ambos'], default='ambos',
        help='Tipo de títulos (default: ambos)'
    )
    parser.add_argument(
        '--empresa', type=int, choices=[1, 3, 4],
        help='Odoo company_id: 1=FB, 3=SC, 4=CD (default: todas)'
    )
    parser.add_argument(
        '--importar', action='store_true',
        help='Importar títulos faltantes do Odoo para o local'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Apenas relatar, sem importar (mesmo com --importar)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Logging detalhado (DEBUG)'
    )

    args = parser.parse_args()

    configurar_logging(args.verbose)

    inicio = agora_utc_naive()

    logger.info("=" * 70)
    logger.info("🔄 RECONCILIAÇÃO COMPLETA ODOO ↔ LOCAL")
    logger.info(f"📅 Início: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📋 Tipo: {args.tipo}")
    logger.info(f"🏢 Empresa: {args.empresa or 'Todas (FB=1, SC=3, CD=4)'}")
    logger.info(f"📥 Importar: {'Sim' if args.importar else 'Não'}")
    logger.info(f"🔍 Dry Run: {'Sim' if args.dry_run else 'Não'}")
    logger.info("=" * 70)

    # Criar app Flask para contexto de banco de dados
    app = create_app()

    with app.app_context():
        # 1. Conectar ao Odoo
        logger.info("\n🔌 Conectando ao Odoo...")
        connection = get_odoo_connection()
        if not connection.authenticate():
            logger.error("❌ Falha na autenticação com Odoo")
            sys.exit(1)
        logger.info("✅ Conectado ao Odoo")

        resultados = []

        # 2. Executar reconciliação por tipo
        if args.tipo in ('receber', 'ambos'):
            resultado = reconciliar_tipo(
                connection, 'receber',
                empresa_filtro=args.empresa,
                importar=args.importar,
                dry_run=args.dry_run
            )
            resultados.append(resultado)

        if args.tipo in ('pagar', 'ambos'):
            resultado = reconciliar_tipo(
                connection, 'pagar',
                empresa_filtro=args.empresa,
                importar=args.importar,
                dry_run=args.dry_run
            )
            resultados.append(resultado)

        # 3. Resumo final
        fim = agora_utc_naive()
        duracao = (fim - inicio).total_seconds()

        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 RESUMO FINAL")
        logger.info("=" * 70)

        for r in resultados:
            tipo_label = "Receber" if r['tipo'] == 'receber' else "Pagar"
            logger.info(
                f"  {tipo_label}: "
                f"Odoo={r['odoo_total']:,} | "
                f"Local={r['local_com_line_id']:,} | "
                f"Cobertura={r['cobertura_pct']}% | "
                f"Faltam={r['faltam_no_local']:,} "
                f"(elegíveis={r['elegiveis']:,}) | "
                f"Órfãos={r['orfaos_locais']:,}"
            )
            if 'importacao' in r:
                imp = r['importacao']
                logger.info(
                    f"    → Importados: +{imp['novos']} novos, "
                    f"{imp['atualizados']} atualizados, "
                    f"{imp['erros']} erros"
                )

        logger.info("")
        logger.info(
            f"✅ Concluído em {duracao:.0f}s "
            f"({fim.strftime('%Y-%m-%d %H:%M:%S')})"
        )


if __name__ == '__main__':
    main()

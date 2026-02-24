#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amostra de Títulos Odoo Faltantes
==================================

Extrai N títulos do Odoo que NÃO existem no banco local, com dados
completos e análise automática do motivo de exclusão.

Estratégia resiliente (evita SSL drop e display_name crash):
1. search() no Odoo → só IDs, sem display_name
2. db.session.close() → fresh SSL connection
3. Query local → checar quais IDs já existem
4. read() com campos explícitos → evita search_read + display_name
5. Imprimir exemplos com análise

Bugs conhecidos evitados:
- SSL drop: conexão PostgreSQL Render expira após ~2min idle durante queries Odoo
  Mitigação: db.session.close() antes de cada query local
- display_name crash: search_read com partner_id dispara _compute_display_name
  que falha em l10n_br_inscricao_fiscal_imovel (coluna faltante)
  Mitigação: read() com IDs + busca separada em res.partner

Uso:
    python scripts/amostra_titulos_odoo_faltantes.py --tipo pagar --quantidade 5
    python scripts/amostra_titulos_odoo_faltantes.py --tipo receber --quantidade 10

Autor: Sistema de Fretes
Data: 2026-02-23
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
ODOO_COMPANY_IDS_ELEGIVEIS = [1, 3, 4]

# Mapeamento company_id → sigla para display
COMPANY_SIGLA = {1: 'FB', 3: 'SC', 4: 'CD'}

# CNPJs raiz do grupo Nacom (para detectar transações intercompany)
# FONTE: .claude/references/odoo/IDS_FIXOS.md:18-25
CNPJS_RAIZ_GRUPO = ['61.724.241', '18.467.441']

# Tamanho da página de search no Odoo
SEARCH_PAGE_SIZE = 500

# Campos detalhados para read() no account.move.line
# partner_id é incluído com fallback — se read() falhar por display_name
# crash, tentamos novamente sem partner_id e buscamos res.partner separado
CAMPOS_DETALHADOS = [
    'id', 'name', 'ref',
    'x_studio_nf_e', 'l10n_br_cobranca_parcela',
    'company_id',
    'date', 'date_maturity',
    'credit', 'balance', 'amount_residual',
    'l10n_br_paga', 'reconciled',
    'account_type', 'parent_state',
    'write_date', 'create_date',
    'move_id',
]


def configurar_logging(verbose=False):
    """Configura logging para o script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


# ===================================================================
# ANÁLISE AUTOMÁTICA
# ===================================================================

def analisar_motivo_nao_importado(record, tipo, partner_cnpj=''):
    """
    Analisa por que um título Odoo não foi importado pelo sync.

    Verifica contra os filtros dos services de sincronização:
    - Pagar: amount_residual < 0, date_maturity >= D-90, partner não-intercompany
      FONTE: sincronizacao_contas_pagar_service.py:384-431, :504-508
    - Receber: balance > 0, date_maturity != False, company != LA FAMIGLIA
      FONTE: contas_receber_service.py:53-116, :314

    Args:
        record: Dict com dados do Odoo
        tipo: 'receber' ou 'pagar'
        partner_cnpj: CNPJ formatado do parceiro (para check intercompany)

    Returns:
        list[str]: Lista de motivos identificados
    """
    motivos = []
    agora = agora_utc_naive()

    # 0. Check intercompany (grupo Nacom — FB/SC/CD/LF)
    if partner_cnpj and any(
        partner_cnpj.startswith(raiz) for raiz in CNPJS_RAIZ_GRUPO
    ):
        motivos.append(
            f"Transação intercompany — parceiro pertence ao grupo Nacom "
            f"(CNPJ {partner_cnpj})"
        )

    # 1. Check NF-e
    nf = record.get('x_studio_nf_e')
    if not nf or nf is False or str(nf).strip() in ('', '0'):
        motivos.append("Sem NF-e (x_studio_nf_e vazio/zero)")

    # 2. Check vencimento
    vencimento = record.get('date_maturity')
    if not vencimento or vencimento is False:
        motivos.append("Sem data de vencimento (date_maturity=False)")

    # 3. Check filtro de saldo (diferente por tipo)
    if tipo == 'pagar':
        amount_residual = float(record.get('amount_residual', 0) or 0)
        if amount_residual >= 0:
            motivos.append(
                f"Título quitado — amount_residual={amount_residual:.2f} "
                f"(full sync exige < 0 para payable)"
            )

        # Check janela de vencimento (D-90)
        # FONTE: sincronizacao_contas_pagar_service.py — default data_inicio=D-90
        if vencimento and vencimento is not False:
            try:
                from datetime import datetime as dt_mod
                dt_venc = dt_mod.strptime(str(vencimento), '%Y-%m-%d')
                dias_atras = (agora - dt_venc).days
                if dias_atras > 90:
                    motivos.append(
                        f"Vencimento há {dias_atras} dias — "
                        f"fora da janela padrão do full sync (D-90)"
                    )
            except (ValueError, TypeError):
                pass
    else:  # receber
        balance = float(record.get('balance', 0) or 0)
        if balance <= 0:
            motivos.append(
                f"Título quitado — balance={balance:.2f} "
                f"(full sync exige > 0 para receivable)"
            )

        # Check date_maturity (receber filtra date_maturity != False)
        # Já coberto pelo check #2 acima

    # 4. Se nenhum motivo encontrado
    if not motivos:
        motivos.append(
            "Título elegível — pode ter sido perdido por limit=5000 antigo "
            "ou gap de timing na sync incremental"
        )

    return motivos


def formatar_valor_br(valor):
    """Formata valor como R$ brasileiro."""
    if valor is None or valor is False:
        return 'N/A'
    try:
        v = abs(float(valor))
        return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return str(valor)


# ===================================================================
# BUSCA PRINCIPAL
# ===================================================================

def buscar_amostra(connection, tipo, quantidade=5):
    """
    Busca N títulos faltantes com dados completos.

    Estratégia anti-SSL-drop e anti-display_name:
    1. search() no Odoo (só IDs, sem display_name)
    2. db.session.close() para fresh SSL connection
    3. Query local para excluir existentes
    4. read() com campos explícitos
    5. Partner info via search_read separado em res.partner

    Args:
        connection: Conexão Odoo autenticada
        tipo: 'receber' ou 'pagar'
        quantidade: Número de exemplos desejados

    Returns:
        list[dict]: Lista de resultados formatados
    """
    account_type = (
        'asset_receivable' if tipo == 'receber'
        else 'liability_payable'
    )
    tipo_label = "CONTAS A RECEBER" if tipo == 'receber' else "CONTAS A PAGAR"
    Model = ContasAReceber if tipo == 'receber' else ContasAPagar

    logger.info(f"\n{'=' * 60}")
    logger.info(f"🔍 AMOSTRA: {tipo_label}")
    logger.info(f"{'=' * 60}")

    # ---------------------------------------------------------------
    # 1. search() no Odoo — só IDs, sem display_name
    # ---------------------------------------------------------------
    logger.info("\n[1/4] Buscando IDs no Odoo (search, sem display_name)...")

    filtros = [
        ['account_type', '=', account_type],
        ['parent_state', '=', 'posted'],
        ['company_id', 'in', ODOO_COMPANY_IDS_ELEGIVEIS],
    ]
    logger.info(f"   Filtros: {filtros}")

    faltantes_encontrados = []
    offset = 0
    max_paginas = 10  # Segurança: máximo 5000 IDs verificados

    while (len(faltantes_encontrados) < quantidade
           and offset < max_paginas * SEARCH_PAGE_SIZE):
        odoo_ids = connection.execute_kw(
            'account.move.line', 'search', [filtros],
            {'limit': SEARCH_PAGE_SIZE, 'offset': offset}
        )

        if not odoo_ids:
            logger.info(f"   ⚠️ Sem mais IDs no Odoo (offset={offset})")
            break

        logger.info(
            f"   📄 Página {offset // SEARCH_PAGE_SIZE + 1}: "
            f"{len(odoo_ids)} IDs (offset={offset})"
        )

        # ---------------------------------------------------------------
        # 2. Fresh DB connection (evita SSL drop)
        # ---------------------------------------------------------------
        db.session.close()

        # ---------------------------------------------------------------
        # 3. Query local — quais já existem?
        # ---------------------------------------------------------------
        local_existentes = set(
            r[0] for r in db.session.query(Model.odoo_line_id)
            .filter(Model.odoo_line_id.in_(odoo_ids))
            .all()
        )

        novos_faltantes = [
            id_ for id_ in odoo_ids if id_ not in local_existentes
        ]
        faltantes_encontrados.extend(novos_faltantes)

        logger.info(
            f"   ✅ {len(novos_faltantes)} faltantes nesta página "
            f"(total acumulado: {len(faltantes_encontrados)})"
        )

        offset += SEARCH_PAGE_SIZE

    if not faltantes_encontrados:
        logger.info("\n   ℹ️ Nenhum título faltante encontrado!")
        return []

    # Pegar apenas a quantidade solicitada
    amostra_ids = faltantes_encontrados[:quantidade]
    logger.info(f"\n   Selecionados {len(amostra_ids)} IDs para detalhamento: {amostra_ids}")

    # ---------------------------------------------------------------
    # 4. read() com campos detalhados
    # ---------------------------------------------------------------
    logger.info(f"\n[2/4] Buscando detalhes de {len(amostra_ids)} títulos...")

    # Tentar com partner_id primeiro (read() é mais seguro que search_read)
    campos_com_partner = CAMPOS_DETALHADOS + ['partner_id']
    try:
        records = connection.read(
            'account.move.line', amostra_ids, campos_com_partner
        )
        logger.info("   ✅ read() com partner_id OK")
    except Exception as e:
        logger.warning(f"   ⚠️ read() com partner_id falhou: {e}")
        logger.info("   🔄 Tentando sem partner_id...")
        records = connection.read(
            'account.move.line', amostra_ids, CAMPOS_DETALHADOS
        )
        logger.info("   ✅ read() sem partner_id OK")

    if not records:
        logger.error("   ❌ Nenhum registro retornado pelo read()")
        return []

    # ---------------------------------------------------------------
    # 5. Buscar info de parceiros separadamente
    # Evita display_name crash usando search_read no res.partner
    # (o crash é no account.move.line, não no res.partner)
    # ---------------------------------------------------------------
    logger.info(f"\n[3/4] Buscando dados de fornecedores/clientes...")

    partner_ids = set()
    for r in records:
        pid = r.get('partner_id')
        if pid and isinstance(pid, (list, tuple)):
            partner_ids.add(pid[0])
        elif pid and isinstance(pid, int):
            partner_ids.add(pid)

    partner_map = {}
    if partner_ids:
        try:
            partners = connection.search_read(
                'res.partner',
                [['id', 'in', list(partner_ids)]],
                ['id', 'name', 'l10n_br_cnpj']
            )
            partner_map = {p['id']: p for p in partners}
            logger.info(f"   ✅ {len(partner_map)} parceiros obtidos")
        except Exception as e:
            logger.warning(f"   ⚠️ Falha ao buscar parceiros: {e}")
            logger.info("   Continuando sem dados de parceiro...")
    else:
        logger.info("   ℹ️ Nenhum partner_id encontrado nos registros")

    # ---------------------------------------------------------------
    # 6. Montar resultado
    # ---------------------------------------------------------------
    logger.info(f"\n[4/4] Montando amostra...")

    resultados = []
    for r in records:
        # Extrair partner info
        pid = r.get('partner_id')
        partner_id_num = None
        partner_nome_odoo = None
        if pid and isinstance(pid, (list, tuple)):
            partner_id_num = pid[0]
            partner_nome_odoo = pid[1] if len(pid) > 1 else None
        elif pid and isinstance(pid, int):
            partner_id_num = pid

        p_info = partner_map.get(partner_id_num, {})

        # Extrair company info
        company = r.get('company_id', [None, None])
        company_id = (
            company[0] if isinstance(company, (list, tuple)) else company
        )
        company_nome = (
            company[1]
            if isinstance(company, (list, tuple)) and len(company) > 1
            else '?'
        )
        company_sigla = COMPANY_SIGLA.get(company_id, '?')

        # Extrair move info
        move = r.get('move_id', [None, None])
        move_nome = (
            move[1]
            if isinstance(move, (list, tuple)) and len(move) > 1
            else str(move)
        )

        # Valor original depende do tipo
        # PAGAR: credit = valor original (positivo)
        # RECEBER: balance = valor original
        # FONTE: sync_filters.md — value_original field
        if tipo == 'pagar':
            valor_original = float(r.get('credit', 0) or 0)
        else:
            valor_original = float(r.get('balance', 0) or 0)

        amount_residual = float(r.get('amount_residual', 0) or 0)

        # Análise automática (com CNPJ para detectar intercompany)
        partner_cnpj_raw = p_info.get('l10n_br_cnpj') or ''
        motivos = analisar_motivo_nao_importado(r, tipo, partner_cnpj=partner_cnpj_raw)

        resultados.append({
            'record': r,
            'partner_id': partner_id_num,
            'partner_nome': (
                p_info.get('name') or partner_nome_odoo or 'N/A'
            ),
            'partner_cnpj': p_info.get('l10n_br_cnpj') or 'N/A',
            'company_id': company_id,
            'company_sigla': company_sigla,
            'company_nome': company_nome,
            'move_nome': move_nome,
            'valor_original': valor_original,
            'amount_residual': amount_residual,
            'motivos': motivos,
        })

    return resultados


# ===================================================================
# EXIBIÇÃO
# ===================================================================

def exibir_amostra(resultados, tipo):
    """
    Exibe a amostra formatada no console.

    Args:
        resultados: Lista de dicts formatados por buscar_amostra()
        tipo: 'receber' ou 'pagar'
    """
    tipo_label = "A RECEBER" if tipo == 'receber' else "A PAGAR"

    for i, item in enumerate(resultados, 1):
        r = item['record']

        print(f"\n{'═' * 60}")
        print(f"  TÍTULO {i}/{len(resultados)} — {tipo_label}")
        print(f"{'═' * 60}")

        print(f"  Odoo Line ID:    {r.get('id')}")
        print(f"  NF-e:            {r.get('x_studio_nf_e') or '(vazio)'}")
        print(f"  Parcela:         {r.get('l10n_br_cobranca_parcela') or '(vazio)'}")
        print(
            f"  Empresa:         {item['company_sigla']} "
            f"(company_id={item['company_id']})"
        )
        print(f"  Move:            {item['move_nome']}")
        print(f"  Emissão:         {r.get('date') or 'N/A'}")
        print(f"  Vencimento:      {r.get('date_maturity') or 'N/A'}")
        print(f"  Valor Original:  {formatar_valor_br(item['valor_original'])}")
        print(f"  Valor Residual:  {formatar_valor_br(item['amount_residual'])}")

        print(f"  {'─' * 40}")
        print(f"  Status:")
        print(f"    l10n_br_paga:    {r.get('l10n_br_paga')}")
        print(f"    reconciled:      {r.get('reconciled')}")
        print(f"    amount_residual: {item['amount_residual']:.2f}")

        # Conclusão de status
        paga = r.get('l10n_br_paga')
        reconciled = r.get('reconciled')
        if paga:
            conclusao = "PAGO (l10n_br_paga=True)"
        elif reconciled and abs(item['amount_residual']) < 0.01:
            conclusao = (
                "PAGO (reconciled + residual≈0, mas l10n_br_paga=False)"
            )
        elif abs(item['amount_residual']) < 0.01:
            conclusao = "QUITADO (residual≈0, mas flags não marcadas)"
        else:
            conclusao = f"EM ABERTO (residual={item['amount_residual']:.2f})"
        print(f"    → Conclusão:     {conclusao}")

        print(f"  {'─' * 40}")
        label_parceiro = "Fornecedor" if tipo == 'pagar' else "Cliente"
        print(f"  {label_parceiro}:")
        print(f"    Partner ID:      {item['partner_id'] or 'N/A'}")
        print(f"    CNPJ:            {item['partner_cnpj']}")
        print(f"    Nome:            {item['partner_nome']}")

        print(f"  {'─' * 40}")
        print(f"  Metadata:")
        print(f"    write_date:      {r.get('write_date') or 'N/A'}")
        print(f"    create_date:     {r.get('create_date') or 'N/A'}")

        print(f"  {'─' * 40}")
        print(f"  POR QUE NÃO FOI IMPORTADO:")
        for motivo in item['motivos']:
            print(f"    → {motivo}")

        print(f"{'═' * 60}")


# ===================================================================
# MAIN
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Amostra de títulos Odoo faltantes no banco local',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # 5 títulos a pagar faltantes
  python scripts/amostra_titulos_odoo_faltantes.py --tipo pagar --quantidade 5

  # 10 títulos a receber faltantes
  python scripts/amostra_titulos_odoo_faltantes.py --tipo receber --quantidade 10

  # Com log detalhado
  python scripts/amostra_titulos_odoo_faltantes.py --tipo pagar -v
        """
    )
    parser.add_argument(
        '--tipo', choices=['receber', 'pagar'], required=True,
        help='Tipo de títulos'
    )
    parser.add_argument(
        '--quantidade', '-n', type=int, default=5,
        help='Quantidade de exemplos (default: 5)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Logging detalhado (DEBUG)'
    )

    args = parser.parse_args()
    configurar_logging(args.verbose)

    inicio = agora_utc_naive()

    logger.info("=" * 60)
    logger.info("📋 AMOSTRA DE TÍTULOS ODOO FALTANTES")
    logger.info(f"📅 Início: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📋 Tipo: {args.tipo}")
    logger.info(f"📊 Quantidade: {args.quantidade}")
    logger.info("=" * 60)

    # Criar app Flask para contexto de banco de dados
    app = create_app()

    with app.app_context():
        # Conectar ao Odoo
        logger.info("\n🔌 Conectando ao Odoo...")
        connection = get_odoo_connection()
        if not connection.authenticate():
            logger.error("❌ Falha na autenticação com Odoo")
            sys.exit(1)
        logger.info("✅ Conectado ao Odoo")

        # Buscar amostra
        resultados = buscar_amostra(connection, args.tipo, args.quantidade)

        if resultados:
            exibir_amostra(resultados, args.tipo)

            # Resumo rápido
            print(f"\n{'=' * 60}")
            print(f"  RESUMO: {len(resultados)} títulos analisados")
            print(f"{'=' * 60}")

            # Contagem por motivo
            contagem_motivos = {}
            for item in resultados:
                for m in item['motivos']:
                    # Agrupar por prefixo do motivo (antes do " —")
                    chave = m.split(' —')[0].split(' (')[0]
                    contagem_motivos[chave] = contagem_motivos.get(chave, 0) + 1

            for motivo, count in sorted(
                contagem_motivos.items(), key=lambda x: -x[1]
            ):
                print(f"  {count}x {motivo}")
            print(f"{'=' * 60}")
        else:
            logger.info(
                "\n⚠️ Nenhum título faltante encontrado! "
                "Todos os IDs verificados já existem localmente."
            )

        # Tempo total
        fim = agora_utc_naive()
        duracao = (fim - inicio).total_seconds()
        logger.info(
            f"\n✅ Concluído em {duracao:.0f}s "
            f"({fim.strftime('%Y-%m-%d %H:%M:%S')})"
        )


if __name__ == '__main__':
    main()

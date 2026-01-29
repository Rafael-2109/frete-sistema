# -*- coding: utf-8 -*-
"""
Serviço de Vinculação OFX → Comprovante → Odoo
=================================================

Fluxo:
1. Parseia arquivo OFX extraindo FITID + CHECKNUM de cada transação
2. Vincula com ComprovantePagamentoBoleto via CHECKNUM = numero_agendamento
3. Busca linhas do extrato no Odoo em batch (1 query por período)
4. Grava IDs do Odoo no comprovante vinculado

Uso:
    from app.financeiro.services.ofx_vinculacao_service import processar_ofx_e_vincular

    resultado = processar_ofx_e_vincular(
        arquivo_bytes=conteudo,
        nome_arquivo='extrato_sic_2026-01-28.ofx',
        usuario='Rafael'
    )
"""

import logging
from datetime import timedelta

from app import db
from app.financeiro.models_comprovante import ComprovantePagamentoBoleto
from app.financeiro.services.ofx_parser_service import parsear_ofx
from app.utils.timezone import agora_brasil

logger = logging.getLogger(__name__)


def _buscar_linhas_odoo_batch(dtstart, dtend):
    """
    Busca TODAS as linhas de extrato do Odoo no período expandido (±1 dia).

    Retorna dict {ref: dados_linha} para lookup O(1) por FITID.
    Em caso de erro na conexão, retorna dict vazio (vinculação Odoo fica pendente).
    """
    try:
        from app.odoo.utils.connection import get_odoo_connection

        connection = get_odoo_connection()
        connection.authenticate()

        # Expandir período: -1 dia no início, +1 dia no fim
        date_start = (dtstart - timedelta(days=1)).isoformat()
        date_end = (dtend + timedelta(days=1)).isoformat()

        logger.info(
            f"[OFX Vinculação] Buscando linhas Odoo: "
            f"período {date_start} a {date_end}"
        )

        linhas = connection.search_read(
            'account.bank.statement.line',
            [
                ['date', '>=', date_start],
                ['date', '<=', date_end],
            ],
            fields=[
                'id', 'ref', 'move_id', 'statement_id',
                'journal_id', 'is_reconciled', 'amount',
            ],
        )

        # Montar dict por ref (FITID) para lookup O(1)
        odoo_por_ref = {}
        for linha in linhas:
            ref = linha.get('ref')
            if ref:
                odoo_por_ref[ref] = {
                    'statement_line_id': linha['id'],
                    'move_id': linha['move_id'][0] if isinstance(linha.get('move_id'), (list, tuple)) else linha.get('move_id'),
                    'statement_id': linha['statement_id'][0] if isinstance(linha.get('statement_id'), (list, tuple)) else linha.get('statement_id'),
                    'journal_id': linha['journal_id'][0] if isinstance(linha.get('journal_id'), (list, tuple)) else linha.get('journal_id'),
                    'is_reconciled': linha.get('is_reconciled', False),
                }

        logger.info(
            f"[OFX Vinculação] Odoo retornou {len(linhas)} linhas, "
            f"{len(odoo_por_ref)} com ref (FITID) indexadas"
        )
        return odoo_por_ref

    except Exception as e:
        logger.error(f"[OFX Vinculação] Erro ao buscar linhas do Odoo: {e}")
        return {}


def processar_ofx_e_vincular(
    arquivo_bytes: bytes,
    nome_arquivo: str,
    usuario: str,
) -> dict:
    """
    Processa arquivo OFX e vincula transações com comprovantes + Odoo.

    Args:
        arquivo_bytes: Conteúdo do arquivo OFX.
        nome_arquivo: Nome do arquivo OFX (para registro).
        usuario: Nome do usuário que importou.

    Returns:
        dict com resumo:
        {
            'sucesso': bool,
            'total_transacoes': int,
            'com_checknum': int,
            'vinculados_comprovante': int,
            'vinculados_odoo': int,
            'sem_comprovante': int,
            'sem_odoo': int,
            'ja_vinculados': int,
            'erros': int,
            'detalhes': [
                {
                    'checknum': str,
                    'fitid': str,
                    'valor': float,
                    'data': str,
                    'memo': str,
                    'status_comprovante': 'vinculado' | 'sem_match' | 'ja_vinculado' | 'erro',
                    'status_odoo': 'vinculado' | 'sem_match' | 'nao_buscou' | 'erro',
                    'mensagem': str,
                },
                ...
            ]
        }
    """
    resultado = {
        'sucesso': False,
        'total_transacoes': 0,
        'com_checknum': 0,
        'vinculados_comprovante': 0,
        'vinculados_odoo': 0,
        'sem_comprovante': 0,
        'sem_odoo': 0,
        'ja_vinculados': 0,
        'erros': 0,
        'detalhes': [],
    }

    # ─── FASE 0: Parsear OFX ─────────────────────────────────────────
    try:
        ofx = parsear_ofx(arquivo_bytes)
    except Exception as e:
        logger.error(f"[OFX Vinculação] Erro ao parsear OFX: {e}")
        resultado['erros'] = 1
        resultado['detalhes'].append({
            'checknum': None,
            'fitid': None,
            'valor': None,
            'data': None,
            'memo': None,
            'status_comprovante': 'erro',
            'status_odoo': 'erro',
            'mensagem': f'Erro ao parsear OFX: {str(e)}',
        })
        return resultado

    transacoes = ofx.get('transacoes', [])
    resultado['total_transacoes'] = len(transacoes)

    if not transacoes:
        resultado['sucesso'] = True
        return resultado

    # Filtrar transações com CHECKNUM
    transacoes_com_checknum = [t for t in transacoes if t.get('checknum')]
    resultado['com_checknum'] = len(transacoes_com_checknum)

    if not transacoes_com_checknum:
        resultado['sucesso'] = True
        logger.info(
            f"[OFX Vinculação] Nenhuma transação com CHECKNUM em {nome_arquivo}"
        )
        return resultado

    # ─── FASE 1: Match OFX → Comprovante (local) ─────────────────────
    # Buscar todos os comprovantes que podem casar (batch)
    checknums = [t['checknum'] for t in transacoes_com_checknum]
    comprovantes_existentes = ComprovantePagamentoBoleto.query.filter(
        ComprovantePagamentoBoleto.numero_agendamento.in_(checknums)
    ).all()

    # Dict para lookup O(1)
    comprovantes_por_agendamento = {
        c.numero_agendamento: c for c in comprovantes_existentes
    }

    # Vincular cada transação com comprovante
    comprovantes_vinculados = []  # Lista de (comprovante, fitid) para Fase 2

    for trn in transacoes_com_checknum:
        checknum = trn['checknum']
        fitid = trn.get('fitid')
        detalhe = {
            'checknum': checknum,
            'fitid': fitid,
            'valor': float(trn['trnamt']) if trn.get('trnamt') else None,
            'data': trn['dtposted'].strftime('%d/%m/%Y') if trn.get('dtposted') else None,
            'memo': trn.get('memo'),
            'status_comprovante': 'sem_match',
            'status_odoo': 'nao_buscou',
            'mensagem': '',
        }

        comprovante = comprovantes_por_agendamento.get(checknum)

        if not comprovante:
            detalhe['status_comprovante'] = 'sem_match'
            detalhe['mensagem'] = f'CHECKNUM {checknum} sem comprovante correspondente'
            resultado['sem_comprovante'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        # Verificar se já foi vinculado com OFX anteriormente
        if comprovante.ofx_fitid:
            detalhe['status_comprovante'] = 'ja_vinculado'
            detalhe['status_odoo'] = 'vinculado' if comprovante.odoo_statement_line_id else 'sem_match'
            detalhe['mensagem'] = (
                f'Comprovante já vinculado anteriormente '
                f'(FITID: {comprovante.ofx_fitid})'
            )
            resultado['ja_vinculados'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        # Gravar dados OFX no comprovante
        try:
            comprovante.ofx_fitid = fitid
            comprovante.ofx_checknum = checknum
            comprovante.ofx_memo = trn.get('memo')
            comprovante.ofx_valor = trn.get('trnamt')
            comprovante.ofx_data = trn.get('dtposted')
            comprovante.ofx_arquivo_origem = nome_arquivo

            detalhe['status_comprovante'] = 'vinculado'
            detalhe['mensagem'] = f'Vinculado com FITID {fitid}'
            resultado['vinculados_comprovante'] += 1

            # Guardar para Fase 2
            if fitid:
                comprovantes_vinculados.append((comprovante, fitid))

        except Exception as e:
            detalhe['status_comprovante'] = 'erro'
            detalhe['mensagem'] = f'Erro ao vincular: {str(e)}'
            resultado['erros'] += 1
            logger.error(
                f"[OFX Vinculação] Erro ao vincular CHECKNUM {checknum}: {e}"
            )

        resultado['detalhes'].append(detalhe)

    # ─── FASE 2: Batch query no Odoo ─────────────────────────────────
    odoo_por_ref = {}
    if comprovantes_vinculados and ofx.get('dtstart') and ofx.get('dtend'):
        odoo_por_ref = _buscar_linhas_odoo_batch(
            ofx['dtstart'], ofx['dtend']
        )

    # ─── FASE 3: Vincular Comprovante → Odoo (lookup local) ──────────
    agora = agora_brasil()
    for comprovante, fitid in comprovantes_vinculados:
        odoo_linha = odoo_por_ref.get(fitid)

        # Encontrar o detalhe correspondente para atualizar status
        detalhe_correspondente = None
        for d in resultado['detalhes']:
            if d['fitid'] == fitid and d['status_comprovante'] == 'vinculado':
                detalhe_correspondente = d
                break

        if odoo_linha:
            try:
                comprovante.odoo_statement_line_id = odoo_linha['statement_line_id']
                comprovante.odoo_move_id = odoo_linha.get('move_id')
                comprovante.odoo_statement_id = odoo_linha.get('statement_id')
                comprovante.odoo_journal_id = odoo_linha.get('journal_id')
                comprovante.odoo_is_reconciled = odoo_linha.get('is_reconciled', False)
                comprovante.odoo_vinculado_em = agora

                resultado['vinculados_odoo'] += 1

                if detalhe_correspondente:
                    detalhe_correspondente['status_odoo'] = 'vinculado'
                    detalhe_correspondente['mensagem'] += (
                        f' | Odoo line_id={odoo_linha["statement_line_id"]}'
                    )
            except Exception as e:
                resultado['erros'] += 1
                if detalhe_correspondente:
                    detalhe_correspondente['status_odoo'] = 'erro'
                    detalhe_correspondente['mensagem'] += f' | Erro Odoo: {str(e)}'
                logger.error(
                    f"[OFX Vinculação] Erro ao gravar Odoo para FITID {fitid}: {e}"
                )
        else:
            resultado['sem_odoo'] += 1
            if detalhe_correspondente:
                detalhe_correspondente['status_odoo'] = 'sem_match'
                detalhe_correspondente['mensagem'] += (
                    ' | FITID não encontrado no Odoo (extrato pode não estar importado)'
                )

    # ─── FASE 4: Commit ──────────────────────────────────────────────
    try:
        db.session.commit()
        resultado['sucesso'] = True
        logger.info(
            f"[OFX Vinculação] Concluído: "
            f"{resultado['vinculados_comprovante']} comprovantes vinculados, "
            f"{resultado['vinculados_odoo']} com Odoo, "
            f"{resultado['sem_comprovante']} sem comprovante, "
            f"{resultado['sem_odoo']} sem Odoo, "
            f"{resultado['ja_vinculados']} já vinculados, "
            f"{resultado['erros']} erros"
        )
    except Exception as e:
        db.session.rollback()
        resultado['erros'] += 1
        logger.error(f"[OFX Vinculação] Erro no commit: {e}")
        resultado['detalhes'].append({
            'checknum': None,
            'fitid': None,
            'valor': None,
            'data': None,
            'memo': None,
            'status_comprovante': 'erro',
            'status_odoo': 'erro',
            'mensagem': f'Erro ao salvar no banco: {str(e)}',
        })

    return resultado

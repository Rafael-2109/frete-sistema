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

import json
import logging
from datetime import datetime, timedelta

from app import db
from app.financeiro.models_comprovante import (
    ComprovantePagamentoBoleto,
    LancamentoComprovante,
)
from app.financeiro.services.ofx_parser_service import parsear_ofx
from app.utils.timezone import agora_brasil

logger = logging.getLogger(__name__)


def _buscar_linhas_odoo_batch(dtstart, dtend):
    """
    Busca TODAS as linhas de extrato do Odoo no período expandido (±1 dia).

    Retorna tupla (dict {ref: dados_linha}, connection) para lookup O(1) por FITID.
    A conexão é retornada para reuso em queries subsequentes (ex: conciliação pré-existente).
    Em caso de erro na conexão, retorna (dict vazio, None).
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
        return odoo_por_ref, connection

    except Exception as e:
        logger.error(f"[OFX Vinculação] Erro ao buscar linhas do Odoo: {e}")
        return {}, None


def _buscar_dados_conciliacao_preexistente(connection, linhas_reconciliadas):
    """
    Busca dados da conciliação pré-existente no Odoo para statement lines já reconciliadas.

    Navega via account.partial.reconcile para encontrar o título (payable) reconciliado,
    funcionando tanto para full quanto partial reconcile.

    Args:
        connection: Conexão Odoo já autenticada.
        linhas_reconciliadas: dict {comprovante_id: {'statement_line_id': int, 'odoo_move_id': int}}

    Returns:
        dict {comprovante_id: {
            'titulo': {move_line_id, move_id, move_name, partner_id, partner_name,
                       company_id, nf_numero, parcela, credit, amount_residual, date_maturity,
                       full_reconcile_id, reconciled},
            'full_reconcile_extrato_id': int ou None,
            'payment_id': int ou None,
            'payment_name': str ou None,
        }}
    """
    if not linhas_reconciliadas or not connection:
        return {}

    resultado = {}

    try:
        # Mapear move_id → comprovante_id para lookup reverso
        move_id_para_comp = {}
        odoo_move_ids = []
        for comp_id, dados in linhas_reconciliadas.items():
            move_id = dados.get('odoo_move_id')
            if move_id:
                move_id_para_comp[move_id] = comp_id
                odoo_move_ids.append(move_id)

        if not odoo_move_ids:
            return {}

        # ─── QUERY 1: move_lines do extrato com partial reconciles ──────
        # Busca linhas de débito dos moves do extrato que participam de reconciliação
        move_lines_extrato = connection.search_read(
            'account.move.line',
            [
                ['move_id', 'in', odoo_move_ids],
                ['debit', '>', 0],
            ],
            fields=[
                'id', 'move_id', 'matched_debit_ids', 'matched_credit_ids',
                'full_reconcile_id',
            ],
        )

        if not move_lines_extrato:
            logger.info(
                f"[OFX Conciliação] Nenhuma move_line de débito encontrada "
                f"para {len(odoo_move_ids)} move_ids de extrato"
            )
            return {}

        # Coletar todos os partial_reconcile IDs e mapear move_id → dados
        todos_partial_ids = []
        extrato_por_move_id = {}  # move_id → {full_reconcile_extrato_id, partial_ids}
        for ml in move_lines_extrato:
            move_id_val = ml.get('move_id')
            move_id = move_id_val[0] if isinstance(move_id_val, (list, tuple)) else move_id_val

            matched_credit = ml.get('matched_credit_ids', []) or []
            matched_debit = ml.get('matched_debit_ids', []) or []
            partial_ids = matched_credit + matched_debit

            full_rec = ml.get('full_reconcile_id')
            full_rec_id = full_rec[0] if isinstance(full_rec, (list, tuple)) and full_rec else (
                full_rec if full_rec else None
            )

            if partial_ids:
                todos_partial_ids.extend(partial_ids)
                extrato_por_move_id[move_id] = {
                    'full_reconcile_extrato_id': full_rec_id,
                    'partial_ids': partial_ids,
                    'move_line_id': ml['id'],
                }

        if not todos_partial_ids:
            logger.info(
                f"[OFX Conciliação] Nenhum partial_reconcile encontrado "
                f"nas move_lines dos extratos"
            )
            return {}

        # ─── QUERY 2: account.partial.reconcile → counterpart lines ─────
        partial_reconciles = connection.search_read(
            'account.partial.reconcile',
            [['id', 'in', list(set(todos_partial_ids))]],
            fields=['id', 'credit_move_id', 'debit_move_id', 'amount'],
        )

        if not partial_reconciles:
            logger.info("[OFX Conciliação] Nenhum partial_reconcile retornado")
            return {}

        # Coletar counterpart line IDs (linhas do "outro lado" da reconciliação)
        # Para linhas de débito do extrato, o counterpart é o credit_move_id
        counterpart_line_ids = set()
        # Mapear partial_id → dados para referência
        partial_por_id = {pr['id']: pr for pr in partial_reconciles}

        for move_id, dados_extrato in extrato_por_move_id.items():
            for pid in dados_extrato['partial_ids']:
                pr = partial_por_id.get(pid)
                if pr:
                    # O extrato tem linha de débito, então o counterpart é credit_move_id
                    credit_move = pr.get('credit_move_id')
                    credit_id = credit_move[0] if isinstance(credit_move, (list, tuple)) else credit_move
                    if credit_id:
                        counterpart_line_ids.add(credit_id)
                    # Também incluir debit_move_id (pode ser o título em alguns cenários)
                    debit_move = pr.get('debit_move_id')
                    debit_id = debit_move[0] if isinstance(debit_move, (list, tuple)) else debit_move
                    if debit_id and debit_id != dados_extrato['move_line_id']:
                        counterpart_line_ids.add(debit_id)

        if not counterpart_line_ids:
            logger.info("[OFX Conciliação] Nenhum counterpart line encontrado")
            return {}

        # ─── QUERY 3: Buscar dados dos títulos (payable) ────────────────
        titulos = connection.search_read(
            'account.move.line',
            [
                ['id', 'in', list(counterpart_line_ids)],
                ['account_type', '=', 'liability_payable'],
            ],
            fields=[
                'id', 'move_id', 'partner_id', 'company_id',
                'x_studio_nf_e', 'l10n_br_cobranca_parcela',
                'credit', 'amount_residual', 'date_maturity',
                'full_reconcile_id', 'reconciled',
            ],
        )

        if not titulos:
            logger.info(
                f"[OFX Conciliação] Nenhum título payable encontrado entre "
                f"{len(counterpart_line_ids)} counterpart lines"
            )
            return {}

        # Indexar títulos por ID para lookup
        titulos_por_id = {t['id']: t for t in titulos}

        # ─── MONTAGEM DO RESULTADO ──────────────────────────────────────
        # Para cada comprovante reconciliado, encontrar o título correspondente
        for move_id, dados_extrato in extrato_por_move_id.items():
            comp_id = move_id_para_comp.get(move_id)
            if not comp_id:
                continue

            # Buscar título via partial_reconcile chain
            titulo_encontrado = None
            for pid in dados_extrato['partial_ids']:
                pr = partial_por_id.get(pid)
                if not pr:
                    continue

                # Verificar credit_move_id
                credit_move = pr.get('credit_move_id')
                credit_id = credit_move[0] if isinstance(credit_move, (list, tuple)) else credit_move
                if credit_id and credit_id in titulos_por_id:
                    titulo_encontrado = titulos_por_id[credit_id]
                    break

                # Verificar debit_move_id
                debit_move = pr.get('debit_move_id')
                debit_id = debit_move[0] if isinstance(debit_move, (list, tuple)) else debit_move
                if debit_id and debit_id in titulos_por_id:
                    titulo_encontrado = titulos_por_id[debit_id]
                    break

            if not titulo_encontrado:
                logger.warning(
                    f"[OFX Conciliação] comp_id={comp_id}: extrato reconciliado "
                    f"mas título payable não encontrado na cadeia de reconciliação"
                )
                continue

            # Extrair dados do título
            t = titulo_encontrado
            partner_val = t.get('partner_id')
            partner_id = partner_val[0] if isinstance(partner_val, (list, tuple)) else partner_val
            partner_name = partner_val[1] if isinstance(partner_val, (list, tuple)) and len(partner_val) > 1 else ''

            move_id_val = t.get('move_id')
            titulo_move_id = move_id_val[0] if isinstance(move_id_val, (list, tuple)) else move_id_val
            titulo_move_name = move_id_val[1] if isinstance(move_id_val, (list, tuple)) and len(move_id_val) > 1 else ''

            company_val = t.get('company_id')
            company_id = company_val[0] if isinstance(company_val, (list, tuple)) else company_val

            full_rec_titulo = t.get('full_reconcile_id')
            full_rec_titulo_id = full_rec_titulo[0] if isinstance(full_rec_titulo, (list, tuple)) and full_rec_titulo else (
                full_rec_titulo if full_rec_titulo else None
            )

            # Parsear vencimento
            vencimento_str = t.get('date_maturity')
            vencimento = None
            if vencimento_str and vencimento_str != '2000-01-01':
                if isinstance(vencimento_str, str):
                    try:
                        vencimento = datetime.strptime(vencimento_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass

            resultado[comp_id] = {
                'titulo': {
                    'move_line_id': t['id'],
                    'move_id': titulo_move_id,
                    'move_name': titulo_move_name,
                    'partner_id': partner_id,
                    'partner_name': partner_name,
                    'company_id': company_id,
                    'nf_numero': str(t.get('x_studio_nf_e') or ''),
                    'parcela': t.get('l10n_br_cobranca_parcela'),
                    'credit': abs(float(t.get('credit', 0))),
                    'amount_residual': abs(float(t.get('amount_residual', 0))),
                    'date_maturity': vencimento,
                    'full_reconcile_id': full_rec_titulo_id,
                    'reconciled': t.get('reconciled', False),
                },
                'full_reconcile_extrato_id': dados_extrato.get('full_reconcile_extrato_id'),
            }

        logger.info(
            f"[OFX Conciliação] Dados de conciliação encontrados para "
            f"{len(resultado)}/{len(linhas_reconciliadas)} comprovantes reconciliados"
        )
        return resultado

    except Exception as e:
        logger.error(
            f"[OFX Conciliação] Erro ao buscar dados de conciliação pré-existente: {e}",
            exc_info=True,
        )
        return {}


def _criar_lancamento_pre_conciliado(comprovante, dados_conciliacao):
    """
    Cria LancamentoComprovante com status LANCADO para conciliação pré-existente no Odoo.

    Args:
        comprovante: ComprovantePagamentoBoleto já vinculado com extrato.
        dados_conciliacao: Dict retornado por _buscar_dados_conciliacao_preexistente.

    Returns:
        LancamentoComprovante criado (já adicionado à sessão).
    """
    titulo = dados_conciliacao['titulo']

    lanc = LancamentoComprovante(
        comprovante_id=comprovante.id,
        # Dados do título Odoo
        odoo_move_line_id=titulo['move_line_id'],
        odoo_move_id=titulo['move_id'],
        odoo_move_name=titulo['move_name'],
        odoo_partner_id=titulo['partner_id'],
        odoo_partner_name=titulo['partner_name'],
        odoo_company_id=titulo['company_id'],
        nf_numero=titulo['nf_numero'],
        parcela=titulo['parcela'],
        odoo_valor_original=titulo['credit'],
        odoo_valor_residual=titulo['amount_residual'],
        odoo_vencimento=titulo['date_maturity'],
        # Match
        match_score=100,
        match_criterios=json.dumps(
            ['CONCILIACAO_PRE_EXISTENTE_ODOO'],
            ensure_ascii=False,
        ),
        diferenca_valor=abs(
            float(comprovante.valor_pago or 0) - titulo['credit']
        ),
        beneficiario_e_financeira=False,
        # Status LANCADO direto
        status='LANCADO',
        lancado_em=agora_brasil(),
        lancado_por='importacao_ofx',
        # Reconciliação
        odoo_full_reconcile_id=titulo.get('full_reconcile_id'),
        odoo_full_reconcile_extrato_id=dados_conciliacao.get('full_reconcile_extrato_id'),
    )

    db.session.add(lanc)
    return lanc


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
            'ja_conciliados_odoo': int,
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
                    'status_odoo': 'vinculado' | 'ja_conciliado' | 'sem_match' | 'nao_buscou' | 'erro',
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
        'ja_conciliados_odoo': 0,
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
    odoo_connection = None  # Reutilizada na FASE 3.5 para conciliação pré-existente
    if comprovantes_vinculados and ofx.get('dtstart') and ofx.get('dtend'):
        odoo_por_ref, odoo_connection = _buscar_linhas_odoo_batch(
            ofx['dtstart'], ofx['dtend']
        )

    # ─── FASE 3: Vincular Comprovante → Odoo (lookup local) ──────────
    agora = agora_brasil()
    # Coletar comprovantes com extrato já reconciliado para busca batch (FASE 3.5)
    comprovantes_reconciliados = {}  # {comp.id: {'statement_line_id': ..., 'odoo_move_id': ...}}
    # Mapear fitid → comprovante para referência na FASE 3.5
    comprovante_por_fitid = {}

    for comprovante, fitid in comprovantes_vinculados:
        odoo_linha = odoo_por_ref.get(fitid)
        comprovante_por_fitid[fitid] = comprovante

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

                # Coletar para busca de conciliação pré-existente (FASE 3.5)
                if odoo_linha.get('is_reconciled'):
                    comprovantes_reconciliados[comprovante.id] = {
                        'statement_line_id': odoo_linha['statement_line_id'],
                        'odoo_move_id': odoo_linha.get('move_id'),
                        'fitid': fitid,
                    }

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

    # ─── FASE 3.5: Conciliação pré-existente (batch) ────────────────
    if comprovantes_reconciliados and odoo_connection:
        logger.info(
            f"[OFX Vinculação] {len(comprovantes_reconciliados)} comprovante(s) "
            f"com extrato já reconciliado. Buscando dados da conciliação..."
        )

        dados_conciliacao = _buscar_dados_conciliacao_preexistente(
            odoo_connection, comprovantes_reconciliados
        )

        for comp_id, dados in dados_conciliacao.items():
            try:
                # Buscar comprovante pelo fitid associado
                dados_rec = comprovantes_reconciliados.get(comp_id)
                if not dados_rec:
                    continue
                fitid = dados_rec.get('fitid')
                comprovante = comprovante_por_fitid.get(fitid)
                if not comprovante:
                    continue

                # Criar LancamentoComprovante LANCADO
                lanc = _criar_lancamento_pre_conciliado(comprovante, dados)

                resultado['ja_conciliados_odoo'] += 1

                # Atualizar detalhe OFX correspondente
                for d in resultado['detalhes']:
                    if d['fitid'] == fitid and d['status_comprovante'] == 'vinculado':
                        titulo = dados['titulo']
                        d['status_odoo'] = 'ja_conciliado'
                        d['mensagem'] += (
                            f' | Conciliação pré-existente: '
                            f'NF {titulo["nf_numero"]}'
                            f'{f"/{titulo["parcela"]}" if titulo.get("parcela") else ""}'
                            f' | {titulo["partner_name"]}'
                            f' | R$ {titulo["credit"]:.2f}'
                            f' | Lançamento #{lanc.id} criado como LANCADO'
                        )
                        break

                logger.info(
                    f"  Conciliação pré-existente: comp_id={comp_id} → "
                    f"título={dados['titulo']['move_name']} "
                    f"NF={dados['titulo']['nf_numero']}"
                )

            except Exception as e:
                resultado['erros'] += 1
                logger.error(
                    f"[OFX Conciliação] Erro ao criar lançamento pré-conciliado "
                    f"para comp_id={comp_id}: {e}",
                    exc_info=True,
                )

    # ─── FASE 4: Commit ──────────────────────────────────────────────
    try:
        db.session.commit()
        resultado['sucesso'] = True
        logger.info(
            f"[OFX Vinculação] Concluído: "
            f"{resultado['vinculados_comprovante']} comprovantes vinculados, "
            f"{resultado['vinculados_odoo']} com Odoo, "
            f"{resultado['ja_conciliados_odoo']} já conciliados, "
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

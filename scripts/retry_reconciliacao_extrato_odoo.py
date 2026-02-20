"""
Retry Reconciliacao Extrato x Odoo
====================================

Busca items de extrato que tiveram titulo baixado mas extrato NAO reconciliado
no Odoo (status='TITULO_BAIXADO' ou status='CONCILIADO' com is_reconciled=False)
e re-tenta a reconciliacao.

Fluxo para cada item:
1. Verificar is_reconciled no Odoo (statement_line)
2. Buscar payment vinculado e seu partner
3. Preparar extrato (1 ciclo draft→write→post via metodo consolidado)
4. Buscar linha PENDENTES do payment (fresca apos prepare)
5. Buscar linha do extrato (fresca apos prepare)
6. Reconciliar payment PENDENTES ↔ extrato

Pre-requisitos:
    source .venv/bin/activate

Execute:
    python scripts/retry_reconciliacao_extrato_odoo.py --dry-run          # Diagnostico
    python scripts/retry_reconciliacao_extrato_odoo.py --executar         # Executar
    python scripts/retry_reconciliacao_extrato_odoo.py --executar --limit 10  # Primeiros 10
    python scripts/retry_reconciliacao_extrato_odoo.py --status TITULO_BAIXADO  # So TITULO_BAIXADO
    python scripts/retry_reconciliacao_extrato_odoo.py --item-ids 123,456  # IDs especificos
"""

import sys
import os
import argparse
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logger = logging.getLogger(__name__)

# Constantes Odoo (mesmo que nos services)
CONTA_TRANSITORIA = 22199
CONTA_PAGAMENTOS_PENDENTES = 26868

RELATORIO_JSON = '/tmp/retry_reconciliacao_relatorio.json'


def buscar_candidatos(status_filtro=None, item_ids=None, limit=None):
    """
    Busca ExtratoItem candidatos a retry de reconciliacao.

    Criterios:
    - payment_id NOT NULL (tem payment criado)
    - statement_line_id NOT NULL (tem extrato vinculado)
    - move_id NOT NULL (tem move no Odoo)
    - status IN ('TITULO_BAIXADO', 'CONCILIADO') — por padrao ambos

    Returns:
        Lista de ExtratoItem
    """
    from app.financeiro.models import ExtratoItem

    query = ExtratoItem.query.filter(
        ExtratoItem.payment_id.isnot(None),
        ExtratoItem.statement_line_id.isnot(None),
        ExtratoItem.move_id.isnot(None),
    )

    if item_ids:
        query = query.filter(ExtratoItem.id.in_(item_ids))
    else:
        if status_filtro:
            query = query.filter(ExtratoItem.status == status_filtro)
        else:
            query = query.filter(
                ExtratoItem.status.in_(['TITULO_BAIXADO', 'CONCILIADO'])
            )

    query = query.order_by(ExtratoItem.id)

    if limit:
        query = query.limit(limit)

    return query.all()


def buscar_candidatos_baixa_pag(limit=None):
    """
    Busca BaixaPagamentoItem candidatos (GAP 3).

    Criterios:
    - payment_id NOT NULL
    - statement_line_id NOT NULL
    - status = 'CONCILIADO'
    """
    from app.financeiro.models import BaixaPagamentoItem

    query = BaixaPagamentoItem.query.filter(
        BaixaPagamentoItem.payment_id.isnot(None),
        BaixaPagamentoItem.statement_line_id.isnot(None),
        BaixaPagamentoItem.status == 'CONCILIADO',
    )

    query = query.order_by(BaixaPagamentoItem.id)

    if limit:
        query = query.limit(limit)

    return query.all()


def verificar_is_reconciled(conn, statement_line_id):
    """
    Verifica se a statement_line esta reconciliada no Odoo.

    Returns:
        dict com {is_reconciled, move_id, partner_id} ou None se nao encontrada
    """
    try:
        results = conn.search_read(
            'account.bank.statement.line',
            [['id', '=', statement_line_id]],
            fields=['is_reconciled', 'move_id', 'partner_id', 'amount'],
            limit=1,
        )
        if results:
            r = results[0]
            move_id = r.get('move_id')
            if isinstance(move_id, (list, tuple)):
                move_id = move_id[0]
            partner = r.get('partner_id')
            partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner
            return {
                'is_reconciled': r.get('is_reconciled', False),
                'move_id': move_id,
                'partner_id': partner_id,
                'amount': r.get('amount', 0),
            }
    except Exception as e:
        logger.warning(f"Erro ao verificar statement_line {statement_line_id}: {e}")
    return None


def buscar_payment_data(conn, payment_id):
    """
    Busca dados do payment no Odoo.

    Returns:
        dict com {move_id, partner_id, partner_name, state, payment_type} ou None
    """
    try:
        results = conn.search_read(
            'account.payment',
            [['id', '=', payment_id]],
            fields=['move_id', 'partner_id', 'state', 'payment_type'],
            limit=1,
        )
        if results:
            r = results[0]
            move_id = r.get('move_id')
            if isinstance(move_id, (list, tuple)):
                move_id = move_id[0]
            partner = r.get('partner_id')
            partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner
            partner_name = partner[1] if isinstance(partner, (list, tuple)) else ''
            return {
                'move_id': move_id,
                'partner_id': partner_id,
                'partner_name': partner_name,
                'state': r.get('state'),
                'payment_type': r.get('payment_type'),
            }
    except Exception as e:
        logger.warning(f"Erro ao buscar payment {payment_id}: {e}")
    return None


def buscar_linha_pendentes_payment(conn, payment_id, tipo='receber'):
    """
    Busca a linha na conta PAGAMENTOS PENDENTES do payment.
    Para inbound (receber): busca DEBIT > 0.
    Para outbound (pagar): busca CREDIT > 0.

    Returns:
        dict com {id, debit, credit, reconciled} ou None
    """
    payment = buscar_payment_data(conn, payment_id)
    if not payment or not payment.get('move_id'):
        return None

    move_id = payment['move_id']

    if tipo == 'pagar':
        filtro_valor = ['credit', '>', 0]
    else:
        filtro_valor = ['debit', '>', 0]

    try:
        linhas = conn.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id],
                ['account_id', '=', CONTA_PAGAMENTOS_PENDENTES],
                filtro_valor,
                ['reconciled', '=', False],
            ],
            fields=['id', 'debit', 'credit', 'amount_residual', 'reconciled', 'account_id'],
        )
        return linhas[0] if linhas else None
    except Exception as e:
        logger.warning(f"Erro ao buscar PENDENTES do payment {payment_id}: {e}")
        return None


def buscar_linha_extrato_fresca(conn, move_id):
    """
    Busca a linha do extrato (credit > 0 ou debit > 0) na conta PENDENTES
    apos prepare. Retorna a linha que NAO esta reconciliada.

    Returns:
        dict com {id, credit, debit, reconciled} ou None
    """
    try:
        linhas = conn.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id],
                ['account_id', '=', CONTA_PAGAMENTOS_PENDENTES],
                ['reconciled', '=', False],
            ],
            fields=['id', 'debit', 'credit', 'amount_residual', 'reconciled'],
        )
        return linhas[0] if linhas else None
    except Exception as e:
        logger.warning(f"Erro ao buscar linha extrato do move {move_id}: {e}")
        return None


def reconciliar_odoo(conn, line1_id, line2_id):
    """
    Reconcilia duas linhas de account.move.line.
    Retorna True se OK, False se falhou.
    """
    try:
        conn.execute_kw(
            'account.move.line',
            'reconcile',
            [[line1_id, line2_id]]
        )
        return True
    except Exception as e:
        if "cannot marshal None" in str(e):
            # Operacao executou com sucesso (O6)
            return True
        logger.error(f"Erro ao reconciliar {line1_id} <-> {line2_id}: {e}")
        return False


def processar_item(conn, baixa_service, item, dry_run=False):
    """
    Processa um ExtratoItem: verifica e tenta reconciliar extrato no Odoo.

    Returns:
        dict com resultado do processamento
    """
    resultado = {
        'item_id': item.id,
        'statement_line_id': item.statement_line_id,
        'payment_id': item.payment_id,
        'status_antes': item.status,
        'acao': None,
        'sucesso': False,
        'mensagem': '',
    }

    # 1. Verificar is_reconciled no Odoo
    stmt_data = verificar_is_reconciled(conn, item.statement_line_id)
    if not stmt_data:
        resultado['acao'] = 'SKIP'
        resultado['mensagem'] = f'Statement line {item.statement_line_id} nao encontrada no Odoo'
        return resultado

    if stmt_data['is_reconciled']:
        resultado['acao'] = 'JA_RECONCILIADO'
        resultado['sucesso'] = True
        resultado['mensagem'] = 'Extrato ja reconciliado no Odoo'

        # Atualizar status local se era TITULO_BAIXADO
        if not dry_run and item.status == 'TITULO_BAIXADO':
            item.status = 'CONCILIADO'
            item.mensagem = (
                f"{item.mensagem or ''} | Retry: ja reconciliado no Odoo, status corrigido"
            )
            resultado['mensagem'] += ' — status local corrigido para CONCILIADO'
        return resultado

    # 2. Buscar payment
    payment_data = buscar_payment_data(conn, item.payment_id)
    if not payment_data:
        resultado['acao'] = 'SKIP'
        resultado['mensagem'] = f'Payment {item.payment_id} nao encontrado no Odoo'
        return resultado

    if payment_data['state'] != 'posted':
        resultado['acao'] = 'SKIP'
        resultado['mensagem'] = f'Payment state={payment_data["state"]} (nao posted)'
        return resultado

    partner_id = payment_data['partner_id']
    partner_name = payment_data['partner_name']

    # Determinar tipo (receber/pagar) baseado nos vinculos do item
    tipo = 'receber' if item.titulo_receber_id else 'pagar'

    if dry_run:
        # Verificar se tem PENDENTES line disponivel
        pendentes = buscar_linha_pendentes_payment(conn, item.payment_id, tipo)
        resultado['acao'] = 'DRY_RUN'
        resultado['sucesso'] = True
        resultado['mensagem'] = (
            f'Candidato valido: tipo={tipo}, partner={partner_name}, '
            f'pendentes_line={"SIM" if pendentes else "NAO"}'
        )
        resultado['tem_pendentes'] = pendentes is not None
        return resultado

    # 3. Preparar extrato (1 ciclo consolidado)
    rotulo = item.mensagem[:100] if item.mensagem else f'Retry reconciliacao item {item.id}'

    preparou = baixa_service.preparar_extrato_para_reconciliacao(
        move_id=item.move_id,
        statement_line_id=item.statement_line_id,
        partner_id=partner_id,
        rotulo=rotulo,
        conta_destino=CONTA_PAGAMENTOS_PENDENTES,
    )

    if not preparou:
        resultado['acao'] = 'ERRO_PREPARE'
        resultado['mensagem'] = f'Falha ao preparar extrato (move_id={item.move_id})'
        return resultado

    # 4. Buscar PENDENTES line do payment (fresca)
    pendentes_line = buscar_linha_pendentes_payment(conn, item.payment_id, tipo)
    if not pendentes_line:
        resultado['acao'] = 'ERRO_PENDENTES'
        resultado['mensagem'] = (
            f'Linha PENDENTES nao encontrada para payment {item.payment_id} '
            f'(tipo={tipo}) — pode ja estar reconciliada'
        )
        return resultado

    # 5. Buscar linha extrato (fresca apos prepare)
    extrato_line = buscar_linha_extrato_fresca(conn, item.move_id)
    if not extrato_line:
        resultado['acao'] = 'ERRO_EXTRATO_LINE'
        resultado['mensagem'] = (
            f'Linha extrato PENDENTES nao encontrada no move {item.move_id} '
            f'apos prepare — pode ja estar reconciliada'
        )
        return resultado

    # 6. Reconciliar
    pendentes_id = pendentes_line['id']
    extrato_id = extrato_line['id']

    logger.info(
        f"  Reconciliando: payment_line={pendentes_id} <-> extrato_line={extrato_id}"
    )

    ok = reconciliar_odoo(conn, pendentes_id, extrato_id)
    if not ok:
        resultado['acao'] = 'ERRO_RECONCILE'
        resultado['mensagem'] = (
            f'Falha ao reconciliar {pendentes_id} <-> {extrato_id}'
        )
        return resultado

    # 7. Verificar resultado
    stmt_check = verificar_is_reconciled(conn, item.statement_line_id)
    is_now_reconciled = stmt_check and stmt_check.get('is_reconciled', False)

    # 8. Atualizar status local
    if is_now_reconciled:
        item.status = 'CONCILIADO'
        item.mensagem = (
            f"{item.mensagem or ''} | Retry: extrato reconciliado com sucesso"
        )
    else:
        item.mensagem = (
            f"{item.mensagem or ''} | Retry: reconcile executado mas is_reconciled ainda False"
        )

    resultado['acao'] = 'RECONCILIADO'
    resultado['sucesso'] = True
    resultado['is_reconciled_apos'] = is_now_reconciled
    resultado['mensagem'] = (
        f'Reconciliado: {pendentes_id} <-> {extrato_id}, '
        f'is_reconciled={is_now_reconciled}'
    )

    return resultado


def main():
    parser = argparse.ArgumentParser(
        description='Retry de reconciliacao de extrato no Odoo'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas diagnosticar, sem executar')
    parser.add_argument('--executar', action='store_true',
                        help='Executar reconciliacao (obrigatorio para alterar)')
    parser.add_argument('--status', type=str, default=None,
                        help='Filtrar por status (TITULO_BAIXADO ou CONCILIADO)')
    parser.add_argument('--item-ids', type=str, default=None,
                        help='IDs especificos (separados por virgula)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limite de itens a processar')

    args = parser.parse_args()

    if not args.dry_run and not args.executar:
        parser.print_help()
        print("\nUse --dry-run para diagnostico ou --executar para correcao.")
        sys.exit(1)

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    # Parse item_ids
    item_ids = None
    if args.item_ids:
        item_ids = [int(x.strip()) for x in args.item_ids.split(',')]

    dry_run = args.dry_run

    from app import create_app
    app = create_app()

    with app.app_context():
        from app import db
        from app.odoo.utils.connection import get_odoo_connection

        # =====================================================================
        # Fase 1: Buscar candidatos
        # =====================================================================
        print("=" * 70)
        print(f"RETRY RECONCILIACAO EXTRATO x ODOO {'(DRY-RUN)' if dry_run else '(EXECUTAR)'}")
        print(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 70)

        candidatos = buscar_candidatos(
            status_filtro=args.status, item_ids=item_ids, limit=args.limit,
        )

        print(f"\nCandidatos encontrados: {len(candidatos)}")
        if not candidatos:
            print("Nenhum item candidato. Nada a fazer.")
            sys.exit(0)

        # Estatisticas rapidas
        por_status = {}
        for c in candidatos:
            s = c.status or 'NULL'
            por_status[s] = por_status.get(s, 0) + 1
        print("Por status:")
        for s, count in sorted(por_status.items()):
            print(f"  {s}: {count}")

        # =====================================================================
        # Fase 2: Conectar ao Odoo
        # =====================================================================
        print(f"\nConectando ao Odoo...")
        conn = get_odoo_connection()
        if not conn.authenticate():
            print("ERRO: Falha na autenticacao com Odoo")
            sys.exit(1)
        print("Conectado ao Odoo.\n")

        # Instanciar service para usar preparar_extrato_para_reconciliacao()
        from app.financeiro.services.baixa_pagamentos_service import BaixaPagamentosService
        baixa_service = BaixaPagamentosService()

        # =====================================================================
        # Fase 3: Processar
        # =====================================================================
        resultados = []
        contadores = {
            'total': len(candidatos),
            'ja_reconciliado': 0,
            'reconciliado': 0,
            'skip': 0,
            'erro': 0,
            'dry_run': 0,
        }

        for idx, item in enumerate(candidatos, 1):
            print(f"\n[{idx}/{len(candidatos)}] Item #{item.id} "
                  f"(stmt={item.statement_line_id}, pay={item.payment_id}, "
                  f"status={item.status})")

            resultado = processar_item(conn, baixa_service, item, dry_run=dry_run)
            resultados.append(resultado)

            acao = resultado.get('acao', '')
            print(f"  → {acao}: {resultado['mensagem']}")

            if acao == 'JA_RECONCILIADO':
                contadores['ja_reconciliado'] += 1
            elif acao == 'RECONCILIADO':
                contadores['reconciliado'] += 1
            elif acao == 'DRY_RUN':
                contadores['dry_run'] += 1
            elif acao.startswith('SKIP'):
                contadores['skip'] += 1
            elif acao.startswith('ERRO'):
                contadores['erro'] += 1

        # =====================================================================
        # Fase 4: Commit e Relatorio
        # =====================================================================
        if not dry_run:
            db.session.commit()
            print("\n  Commit realizado.")

        # Relatorio
        print("\n" + "=" * 70)
        print("RESUMO")
        print("=" * 70)
        print(f"  Total processados:     {contadores['total']}")
        if dry_run:
            print(f"  Candidatos validos:    {contadores['dry_run']}")
            tem_pendentes = sum(1 for r in resultados if r.get('tem_pendentes'))
            sem_pendentes = sum(1 for r in resultados if r.get('acao') == 'DRY_RUN' and not r.get('tem_pendentes'))
            print(f"    Com PENDENTES line:  {tem_pendentes}")
            print(f"    Sem PENDENTES line:  {sem_pendentes}")
        else:
            print(f"  Reconciliados:         {contadores['reconciliado']}")
        print(f"  Ja reconciliados:      {contadores['ja_reconciliado']}")
        print(f"  Pulados (skip):        {contadores['skip']}")
        print(f"  Erros:                 {contadores['erro']}")

        # Salvar JSON
        relatorio = {
            'gerado_em': datetime.now().isoformat(),
            'modo': 'dry_run' if dry_run else 'executar',
            'filtros': {
                'status': args.status,
                'item_ids': item_ids,
                'limit': args.limit,
            },
            'contadores': contadores,
            'resultados': resultados,
        }

        with open(RELATORIO_JSON, 'w') as f:
            json.dump(relatorio, f, indent=2, default=str)
        print(f"\n  Relatorio: {RELATORIO_JSON}")

        print("\n" + "=" * 70)
        print("FIM")
        print("=" * 70)


if __name__ == '__main__':
    main()

"""
Script de Backfill: Importar POs do tipo rem-conta-ordem

Importa pedidos de compra do tipo "Entrada: Remessa por Conta e Ordem"
que nao foram capturados pela sincronizacao incremental (tipo nao estava
no whitelist TIPOS_RELEVANTES).

Pipeline completo:
  Fase 0:  Importar POs do Odoo -> tabela pedido_compras
  Fase 0b: Importar requisicoes e alocacoes vinculadas
  Fase 1:  Validacao fiscal (ValidacaoFiscalService)
  Fase 2:  Validacao NF x PO (ValidacaoNfPoService)

Uso:
    python scripts/backfill_pedidos_rem_conta_ordem.py [options]

Exemplos:
    # Testar sem alterar dados
    python scripts/backfill_pedidos_rem_conta_ordem.py --dry-run --po-id 37080

    # Importar PO especifico
    python scripts/backfill_pedidos_rem_conta_ordem.py --po-id 37080

    # Importar lote pequeno
    python scripts/backfill_pedidos_rem_conta_ordem.py --limit 10

    # Importar todos desde 01/01/2025
    python scripts/backfill_pedidos_rem_conta_ordem.py --data-inicio 01/01/2025

    # Importar todos
    python scripts/backfill_pedidos_rem_conta_ordem.py

    # Apenas importar POs, sem validacao fiscal
    python scripts/backfill_pedidos_rem_conta_ordem.py --skip-validacao
"""

import sys
import os
import argparse
import logging
import traceback
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.manufatura.models import PedidoCompras
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.services.pedido_compras_service import PedidoComprasServiceOtimizado
from app.odoo.services.requisicao_compras_service import RequisicaoComprasService
from app.odoo.services.alocacao_compras_service import AlocacaoComprasServiceOtimizado

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('backfill_rem_conta_ordem')


def _parse_data_inicio(valor: str) -> datetime:
    """Converte string DD/MM/YYYY em datetime. Levanta ValueError se invalido."""
    try:
        return datetime.strptime(valor, '%d/%m/%Y')
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Data invalida: '{valor}'. Use formato DD/MM/YYYY (ex: 01/01/2025)"
        )


def fase_0_importar_pos(connection, po_service, args) -> dict:
    """
    Fase 0: Buscar POs rem-conta-ordem no Odoo e importar via PedidoComprasService.

    Reutiliza a logica de batch loading do service para consistencia.
    Commit atomico: nada e persistido ate o commit explicito no main().
    """
    logger.info("=" * 80)
    logger.info("FASE 0: IMPORTAR POs rem-conta-ordem")
    logger.info("=" * 80)

    # Montar domain de busca
    domain = [
        ['l10n_br_tipo_pedido', '=', 'rem-conta-ordem'],
        ['state', 'in', ['purchase', 'done']]
    ]

    if args.po_id:
        domain.append(['id', '=', args.po_id])
        logger.info(f"  Filtro: PO ID = {args.po_id}")

    if args.data_inicio:
        data_iso = args.data_inicio.strftime('%Y-%m-%d')
        domain.append(['date_order', '>=', data_iso])
        logger.info(f"  Filtro: date_order >= {data_iso}")

    # Campos necessarios (verificados no Odoo)
    fields = [
        'id', 'name', 'state', 'partner_id', 'date_order', 'write_date',
        'order_line', 'l10n_br_tipo_pedido', 'company_id', 'dfe_id',
        'date_planned', 'picking_ids', 'invoice_ids',
        'incoterm_id',
    ]

    logger.info("  Buscando POs no Odoo...")
    pedidos_odoo = connection.search_read(
        'purchase.order',
        domain,
        fields=fields,
        limit=args.limit or 0
    )

    if not pedidos_odoo:
        logger.info("  Nenhum PO rem-conta-ordem encontrado no Odoo")
        return {'pos_encontrados': 0, 'linhas_novas': 0, 'linhas_atualizadas': 0}

    logger.info(f"  Encontrados {len(pedidos_odoo)} POs no Odoo")

    if args.dry_run:
        for po in pedidos_odoo:
            partner = po.get('partner_id')
            partner_name = partner[1] if partner else 'N/A'
            dfe = po.get('dfe_id')
            dfe_info = f"DFE={dfe[0]}" if dfe else "sem DFE"
            logger.info(
                f"  [DRY-RUN] PO {po['name']} | {po['state']} | "
                f"{partner_name} | {dfe_info} | "
                f"{len(po.get('order_line', []))} linhas"
            )
        return {
            'pos_encontrados': len(pedidos_odoo),
            'linhas_novas': 0,
            'linhas_atualizadas': 0,
            'dry_run': True
        }

    # Reutilizar logica batch do service
    logger.info("  Carregando fornecedores em batch...")
    fornecedores_cache = po_service._buscar_fornecedores_batch(pedidos_odoo)

    logger.info("  Carregando linhas em batch...")
    todas_linhas = po_service._buscar_todas_linhas_batch(pedidos_odoo)

    logger.info("  Carregando produtos em batch...")
    produtos_cache = po_service._buscar_todos_produtos_batch(todas_linhas)

    logger.info("  Carregando DFEs em batch...")
    dfes_cache = po_service._buscar_dfes_batch(pedidos_odoo)

    logger.info("  Carregando pedidos existentes no BD local...")
    pedidos_existentes_cache = po_service._carregar_pedidos_existentes()

    logger.info("  Processando pedidos...")
    resultado = po_service._processar_pedidos_otimizado(
        pedidos_odoo,
        todas_linhas,
        produtos_cache,
        pedidos_existentes_cache,
        fornecedores_cache,
        dfes_cache
    )

    # SEM commit aqui — commit atomico no main()
    logger.info(f"  Fase 0 preparada: {resultado['pedidos_novos']} novos, "
                f"{resultado['pedidos_atualizados']} atualizados, "
                f"{resultado['linhas_processadas']} linhas")

    return {
        'pos_encontrados': len(pedidos_odoo),
        'linhas_novas': resultado['pedidos_novos'],
        'linhas_atualizadas': resultado['pedidos_atualizados'],
        'linhas_processadas': resultado['linhas_processadas'],
        'linhas_ignoradas': resultado['linhas_ignoradas'],
    }


def fase_0b_importar_requisicoes_alocacoes(args) -> dict:
    """
    Fase 0b: Importar requisicoes e alocacoes vinculadas aos POs importados.

    Usa primeira_execucao=True com janela larga (1 ano) para capturar tudo.
    Os services fazem dedup automatico via chave composta.

    NOTA: Os services (AlocacaoComprasServiceOtimizado, RequisicaoComprasService)
    comitam internamente. Nao adicionamos commits redundantes aqui.
    """
    logger.info("=" * 80)
    logger.info("FASE 0b: IMPORTAR REQUISICOES + ALOCACOES")
    logger.info("=" * 80)

    if args.dry_run:
        logger.info("  [DRY-RUN] Pulando importacao de requisicoes e alocacoes")
        return {'requisicoes': 0, 'alocacoes': 0, 'dry_run': True}

    resultado = {}

    # Alocacoes primeiro (vinculam requisicao -> PO)
    try:
        logger.info("  Sincronizando alocacoes...")
        alocacao_service = AlocacaoComprasServiceOtimizado()
        res_alocacoes = alocacao_service.sincronizar_alocacoes_incremental(
            minutos_janela=525600,  # 1 ano
            primeira_execucao=True
        )
        resultado['alocacoes'] = res_alocacoes.get('alocacoes_novas', 0)
        logger.info(f"  Alocacoes: {resultado['alocacoes']} novas")
    except Exception as e:
        logger.warning(f"  Erro ao sincronizar alocacoes (nao-fatal): {e}")
        resultado['alocacoes'] = 0
        resultado['erro_alocacoes'] = str(e)

    # Requisicoes
    try:
        logger.info("  Sincronizando requisicoes...")
        req_service = RequisicaoComprasService()
        res_requisicoes = req_service.sincronizar_requisicoes_incremental(
            minutos_janela=525600,  # 1 ano
            primeira_execucao=True
        )
        resultado['requisicoes'] = res_requisicoes.get('requisicoes_novas', 0)
        logger.info(f"  Requisicoes: {resultado['requisicoes']} novas")
    except Exception as e:
        logger.warning(f"  Erro ao sincronizar requisicoes (nao-fatal): {e}")
        resultado['requisicoes'] = 0
        resultado['erro_requisicoes'] = str(e)

    return resultado


def fase_1_2_validacao(args) -> dict:
    """
    Fase 1+2: Revalidar DFEs dos POs importados.

    Para cada PO que tem dfe_id, executa:
    - Fase 1: Validacao fiscal (ValidacaoFiscalService.validar_nf)
    - Fase 2: Validacao NF x PO (ValidacaoNfPoService.validar_dfe)

    Cada DFE e validado dentro de um savepoint atomico — falha em um
    nao impede a validacao dos demais.

    Query otimizada: busca apenas dfe_id com DISTINCT direto no BD,
    sem carregar objetos ORM completos.
    """
    from app.recebimento.services.validacao_fiscal_service import ValidacaoFiscalService
    from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService

    logger.info("=" * 80)
    logger.info("FASE 1+2: VALIDACAO FISCAL + NF x PO")
    logger.info("=" * 80)

    # Query otimizada: buscar apenas dfe_ids distintos, sem carregar ORM completo
    # Usa indice ix_pedido_compras_tipo_pedido + idx_pedido_dfe
    query = (
        db.session.query(PedidoCompras.dfe_id)
        .filter(
            PedidoCompras.tipo_pedido == 'rem-conta-ordem',
            PedidoCompras.dfe_id.isnot(None),
            PedidoCompras.dfe_id != '',
        )
    )

    if args.po_id:
        # Filtrar por PO Odoo ID usando campo local (sem chamada extra ao Odoo)
        query = query.filter(
            PedidoCompras.odoo_purchase_order_id == str(args.po_id)
        )
        logger.info(f"  Filtro: odoo_purchase_order_id = {args.po_id}")

    if args.data_inicio:
        query = query.filter(
            PedidoCompras.data_pedido_criacao >= args.data_inicio.date()
        )
        logger.info(f"  Filtro: data_pedido_criacao >= {args.data_inicio.strftime('%d/%m/%Y')}")

    dfe_ids = {row[0] for row in query.distinct().all()}

    if not dfe_ids:
        logger.info("  Nenhum DFE vinculado encontrado para validar")
        return {'validados_fase1': 0, 'validados_fase2': 0}

    logger.info(f"  {len(dfe_ids)} DFEs unicos para validar")

    if args.dry_run:
        for dfe_id in sorted(dfe_ids):
            logger.info(f"  [DRY-RUN] Validaria DFE {dfe_id}")
        return {'validados_fase1': 0, 'validados_fase2': 0, 'dry_run': True}

    fiscal_service = ValidacaoFiscalService()
    nfpo_service = ValidacaoNfPoService()

    stats = {'validados_fase1': 0, 'validados_fase2': 0, 'erros': 0}

    for dfe_id in sorted(dfe_ids):
        # Savepoint atomico por DFE — falha nao contamina proximos
        try:
            savepoint = db.session.begin_nested()

            # Fase 1: Validacao Fiscal
            logger.info(f"  DFE {dfe_id}: Executando validacao fiscal (Fase 1)...")
            res_fiscal = fiscal_service.validar_nf(dfe_id)
            status_fiscal = res_fiscal.get('status', 'erro')
            logger.info(f"    Fase 1: {status_fiscal}")
            stats['validados_fase1'] += 1

            # Fase 2: Validacao NF x PO
            logger.info(f"  DFE {dfe_id}: Executando validacao NF x PO (Fase 2)...")
            res_nfpo = nfpo_service.validar_dfe(dfe_id)
            status_nfpo = res_nfpo.get('status', 'erro')
            logger.info(f"    Fase 2: {status_nfpo}")
            stats['validados_fase2'] += 1

            savepoint.commit()

        except Exception as e:
            savepoint.rollback()
            logger.error(f"  DFE {dfe_id}: Erro na validacao (rollback savepoint) — {e}")
            stats['erros'] += 1

    # Commit final da fase 1+2 (persiste todos os savepoints bem-sucedidos)
    db.session.commit()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Backfill: Importar POs do tipo rem-conta-ordem'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular sem gravar no BD'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limitar numero de POs'
    )
    parser.add_argument(
        '--po-id',
        type=int,
        default=None,
        help='Processar PO especifico (ex: 37080)'
    )
    parser.add_argument(
        '--data-inicio',
        type=_parse_data_inicio,
        default=None,
        help='Data de inicio para filtro (DD/MM/YYYY). Filtra date_order no Odoo e data_pedido_criacao local.'
    )
    parser.add_argument(
        '--skip-validacao',
        action='store_true',
        help='Pular Fase 1+2 (importar POs apenas)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Tamanho do batch para commits (default: 50)'
    )

    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        inicio = datetime.now()
        logger.info("=" * 80)
        logger.info("BACKFILL: PEDIDOS rem-conta-ordem")
        logger.info(f"  Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  Dry-run: {args.dry_run}")
        logger.info(f"  Limit: {args.limit or 'sem limite'}")
        logger.info(f"  PO ID: {args.po_id or 'todos'}")
        logger.info(f"  Data inicio: {args.data_inicio.strftime('%d/%m/%Y') if args.data_inicio else 'sem filtro'}")
        logger.info(f"  Skip validacao: {args.skip_validacao}")
        logger.info("=" * 80)

        try:
            # Conectar ao Odoo
            connection = get_odoo_connection()
            uid = connection.authenticate()
            if not uid:
                logger.error("Falha na autenticacao com Odoo")
                sys.exit(1)
            logger.info(f"  Autenticado no Odoo (uid={uid})")

            po_service = PedidoComprasServiceOtimizado()

            # FASE 0: Importar POs (sem commit — acumula no session)
            res_fase0 = fase_0_importar_pos(connection, po_service, args)

            # Commit atomico da Fase 0: tudo ou nada
            if not args.dry_run:
                db.session.commit()
                logger.info("  Fase 0 commitada com sucesso")

            # FASE 0b: Requisicoes + Alocacoes (apenas se importou POs)
            # NOTA: Services comitam internamente — atomicidade por service
            res_fase0b = {}
            if res_fase0.get('linhas_novas', 0) > 0 or res_fase0.get('linhas_atualizadas', 0) > 0:
                res_fase0b = fase_0b_importar_requisicoes_alocacoes(args)
            else:
                logger.info("\nFASE 0b: Pulada (nenhum PO novo/atualizado)")

            # FASE 1+2: Validacao fiscal + NF x PO
            # Cada DFE e atomico via savepoint + commit final
            res_fase12 = {}
            if not args.skip_validacao:
                res_fase12 = fase_1_2_validacao(args)
            else:
                logger.info("\nFASE 1+2: Pulada (--skip-validacao)")

            # RESUMO
            tempo = (datetime.now() - inicio).total_seconds()
            logger.info("")
            logger.info("=" * 80)
            logger.info("RESUMO DO BACKFILL")
            logger.info("=" * 80)
            logger.info(f"  Tempo total: {tempo:.1f}s")
            logger.info(f"  POs encontrados no Odoo: {res_fase0.get('pos_encontrados', 0)}")
            logger.info(f"  Linhas novas: {res_fase0.get('linhas_novas', 0)}")
            logger.info(f"  Linhas atualizadas: {res_fase0.get('linhas_atualizadas', 0)}")
            logger.info(f"  Linhas processadas: {res_fase0.get('linhas_processadas', 0)}")
            if res_fase0b:
                logger.info(f"  Alocacoes importadas: {res_fase0b.get('alocacoes', 0)}")
                logger.info(f"  Requisicoes importadas: {res_fase0b.get('requisicoes', 0)}")
            if res_fase12:
                logger.info(f"  DFEs validados Fase 1: {res_fase12.get('validados_fase1', 0)}")
                logger.info(f"  DFEs validados Fase 2: {res_fase12.get('validados_fase2', 0)}")
                if res_fase12.get('erros', 0) > 0:
                    logger.warning(f"  Erros de validacao: {res_fase12['erros']}")
            if args.dry_run:
                logger.info("  ** MODO DRY-RUN — nenhuma alteracao feita **")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Erro fatal no backfill: {e}")
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)


if __name__ == '__main__':
    main()

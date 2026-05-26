"""
Service de limpeza de MovimentacaoEstoque criadas indevidamente pelo Recebimento LF.
====================================================================================

Contexto (2026-05-26):
    O servico de Recebimento LF estava gravando MovimentacaoEstoque para TODOS
    os lotes processados (componentes + produto acabado). Componentes (CFOP=1902,
    tipo='auto') NAO devem entrar como compra — sao retorno de industrializacao,
    nao aquisicao. Isso inflava o estoque indevidamente.

    Fix aplicado em `recebimento_lf_odoo_service.py:_criar_movimentacoes_estoque`.
    Este service apaga retroativamente as movimentacoes erroneas geradas pelos
    recebimentos LF processados entre `data_inicio` e hoje.

Criterio de identificacao (composicao restritiva):
    1. tipo_origem = 'ODOO'
    2. ativo = TRUE
    3. local_movimentacao = 'COMPRA'
    4. odoo_picking_id pertence a RecebimentoLf processado >= data_inicio
    5. lote_nome igual ao numero_nf do RecebimentoLf (assinatura de componente
       auto-copiado: o service usa lote_nome=numero_nf quando tipo='auto')
    6. observacao LIKE 'Recebimento LF%' (confirma origem)

Salvaguardas:
    - dry_run=True por padrao
    - so deleta movimentacoes sem vinculo a separacao/embarque/pedido_compras/
      recebimento_fisico/recebimento_lote/baixa/abatimento/producao_pai
    - retorna lista detalhada do que sera deletado
"""

import logging
from datetime import date

from sqlalchemy import and_, or_

from app import db
from app.estoque.models import MovimentacaoEstoque
from app.recebimento.models import RecebimentoLf

logger = logging.getLogger(__name__)

DATA_INICIO_DEFAULT = date(2026, 5, 17)


def listar_candidatos(data_inicio=None):
    """
    Retorna query SQLAlchemy com as MovimentacaoEstoque candidatas a deletar.

    Args:
        data_inicio: data minima de criacao do RecebimentoLf (default 2026-05-17)
    """
    if data_inicio is None:
        data_inicio = DATA_INICIO_DEFAULT

    # Subquery: pickings + numero_nf de RecebimentoLf no periodo
    recs_subq = db.session.query(
        RecebimentoLf.odoo_picking_id.label('picking_id'),
        RecebimentoLf.numero_nf.label('numero_nf'),
    ).filter(
        RecebimentoLf.criado_em >= data_inicio,
        RecebimentoLf.odoo_picking_id.isnot(None),
        RecebimentoLf.numero_nf.isnot(None),
    ).subquery()

    # Movimentacoes que batem TODOS os criterios
    q = (
        db.session.query(MovimentacaoEstoque)
        .join(
            recs_subq,
            and_(
                MovimentacaoEstoque.odoo_picking_id == db.cast(recs_subq.c.picking_id, db.String),
                MovimentacaoEstoque.lote_nome == recs_subq.c.numero_nf,
            ),
        )
        .filter(
            MovimentacaoEstoque.tipo_origem == 'ODOO',
            MovimentacaoEstoque.ativo.is_(True),
            MovimentacaoEstoque.local_movimentacao == 'COMPRA',
            MovimentacaoEstoque.observacao.like('Recebimento LF%'),
            # Salvaguardas: nao tocar movimentacoes vinculadas a outros fluxos
            MovimentacaoEstoque.separacao_lote_id.is_(None),
            MovimentacaoEstoque.codigo_embarque.is_(None),
            MovimentacaoEstoque.pedido_compras_id.is_(None),
            MovimentacaoEstoque.recebimento_fisico_id.is_(None),
            MovimentacaoEstoque.recebimento_lote_id.is_(None),
            MovimentacaoEstoque.producao_pai_id.is_(None),
            or_(
                MovimentacaoEstoque.qtd_abatida.is_(None),
                MovimentacaoEstoque.qtd_abatida == 0,
            ),
            or_(
                MovimentacaoEstoque.baixado.is_(None),
                MovimentacaoEstoque.baixado.is_(False),
            ),
        )
    )
    return q


def limpar_movimentacoes_componentes_lf(dry_run=True, data_inicio=None, max_delete=None):
    """
    Apaga (ou simula) MovimentacaoEstoque de componentes geradas pelo Recebimento LF.

    Args:
        dry_run: se True (default), apenas reporta o que seria deletado
        data_inicio: data minima (default 2026-05-17)
        max_delete: limite hard de seguranca; se total > max_delete, aborta

    Returns:
        dict com:
          - dry_run: bool
          - data_inicio: str
          - total: int (qtd de movimentacoes candidatas)
          - qtd_total_unidades: float (soma de qtd_movimentacao)
          - por_recebimento: list[dict] (resumo agrupado)
          - amostra: list[dict] (ate 20 primeiros registros com detalhes)
          - deletadas: int (0 se dry_run)
          - abortado: bool (True se max_delete excedido)
          - abortado_motivo: str
    """
    if data_inicio is None:
        data_inicio = DATA_INICIO_DEFAULT

    q = listar_candidatos(data_inicio=data_inicio)
    candidatas = q.order_by(MovimentacaoEstoque.criado_em).all()
    total = len(candidatas)
    qtd_total = sum(float(m.qtd_movimentacao or 0) for m in candidatas)

    # Agrupamento por recebimento (via odoo_picking_id)
    por_picking = {}
    for m in candidatas:
        key = m.odoo_picking_id
        if key not in por_picking:
            por_picking[key] = {
                'odoo_picking_id': key,
                'total': 0,
                'qtd_total': 0.0,
            }
        por_picking[key]['total'] += 1
        por_picking[key]['qtd_total'] += float(m.qtd_movimentacao or 0)

    # Enriquecer com numero_nf via consulta a recebimento_lf
    if por_picking:
        recs = (
            RecebimentoLf.query
            .filter(RecebimentoLf.odoo_picking_id.in_([
                int(k) for k in por_picking.keys() if k and k.isdigit()
            ]))
            .all()
        )
        for r in recs:
            key = str(r.odoo_picking_id)
            if key in por_picking:
                por_picking[key]['numero_nf'] = r.numero_nf
                por_picking[key]['odoo_picking_name'] = r.odoo_picking_name
                por_picking[key]['rec_id'] = r.id

    por_recebimento = sorted(
        por_picking.values(),
        key=lambda x: x.get('rec_id') or 0,
    )

    amostra = []
    for m in candidatas[:20]:
        amostra.append({
            'id': m.id,
            'cod_produto': m.cod_produto,
            'nome_produto': m.nome_produto,
            'qtd_movimentacao': float(m.qtd_movimentacao or 0),
            'lote_nome': m.lote_nome,
            'odoo_picking_id': m.odoo_picking_id,
            'odoo_move_id': m.odoo_move_id,
            'observacao': m.observacao,
            'criado_em': m.criado_em.isoformat() if m.criado_em else None,
        })

    result = {
        'dry_run': dry_run,
        'data_inicio': data_inicio.isoformat() if isinstance(data_inicio, date) else str(data_inicio),
        'total': total,
        'qtd_total_unidades': qtd_total,
        'por_recebimento': por_recebimento,
        'amostra': amostra,
        'deletadas': 0,
        'abortado': False,
        'abortado_motivo': None,
    }

    if dry_run:
        logger.info(
            f"[limpar_movs_componentes_lf] DRY-RUN: {total} movimentacoes "
            f"candidatas, {qtd_total:.3f} unidades"
        )
        return result

    if max_delete is not None and total > max_delete:
        result['abortado'] = True
        result['abortado_motivo'] = (
            f"total {total} excede max_delete={max_delete} (salvaguarda)"
        )
        logger.error(
            f"[limpar_movs_componentes_lf] ABORTADO: {result['abortado_motivo']}"
        )
        return result

    # EXECUCAO REAL
    ids_para_deletar = [m.id for m in candidatas]
    if not ids_para_deletar:
        return result

    try:
        deletadas = (
            MovimentacaoEstoque.query
            .filter(MovimentacaoEstoque.id.in_(ids_para_deletar))
            .delete(synchronize_session=False)
        )
        db.session.commit()
        result['deletadas'] = deletadas
        logger.info(
            f"[limpar_movs_componentes_lf] EXECUTADO: {deletadas} movimentacoes "
            f"deletadas (esperado {total})"
        )
    except Exception as e:
        db.session.rollback()
        result['abortado'] = True
        result['abortado_motivo'] = f"Erro ao deletar: {type(e).__name__}: {e}"
        logger.exception(
            f"[limpar_movs_componentes_lf] FALHA ao deletar: {e}"
        )
        raise

    return result

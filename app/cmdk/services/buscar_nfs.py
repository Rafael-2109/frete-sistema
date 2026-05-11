"""
Busca de NFs (Notas Fiscais) para o Ctrl+K.

Faz match em RelatorioFaturamentoImportado por numero_nf e nome_cliente,
LEFT JOIN com EntregaMonitorada (origem='NACOM') para enriquecer com status
de entrega, datas e transportadora.

Permissoes:
- perfil 'vendedor' com vendedor_vinculado: filtra apenas NFs do vendedor
- demais perfis: ve tudo
"""
from __future__ import annotations

import re
import time
from typing import Optional

from flask import current_app
from flask_login import current_user
from sqlalchemy import func, or_

from app import db
from app.faturamento.models import RelatorioFaturamentoImportado as RFI
from app.monitoramento.models import EntregaMonitorada


CANDIDATES_POOL = 40
MIN_CNPJ_DIGITS = 4


def buscar(q: str, user=None, limit: int = 6) -> list[dict]:
    """
    Busca NFs por query livre.

    Args:
        q: query do usuario
        user: Usuario (default current_user)
        limit: maximo de resultados

    Returns:
        Lista de dicts:
        {
            'tipo': 'nf',
            'id': '12345',
            'label': 'NF 12345',
            'subtitle': 'ATACADAO MANAUS  R$ 12.450,00  Faturada 14/04/2026',
            'url': '/monitoramento/listar_entregas?numero_nf=12345',
            'badge': {'label': 'Em transito', 'tone': 'info'},
            'icon': 'fas fa-receipt',
            'score': 0.85,
        }
    """
    user = user if user is not None else current_user
    q = (q or '').strip()
    if len(q) < 2:
        return []

    # Strip prefixo "nf " ou "nf:" se usuario digitou
    q_clean = re.sub(r'^nf[:\s]+', '', q, flags=re.IGNORECASE).strip() or q

    started = time.time()
    q_digits = re.sub(r'\D', '', q_clean)

    filters = [
        RFI.numero_nf.ilike(f'%{q_clean}%'),
        RFI.nome_cliente.ilike(f'%{q_clean}%'),
    ]
    if len(q_digits) >= MIN_CNPJ_DIGITS:
        filters.append(RFI.cnpj_cliente.like(f'%{q_digits}%'))

    # GROUP BY numero_nf evita duplicatas quando a NF tem multiplas EntregaMonitorada
    # (M1 fix). Usa func.bool_or/max para agregar campos de entrega.
    base = (
        db.session.query(
            RFI.numero_nf.label('numero_nf'),
            func.max(RFI.nome_cliente).label('nome_cliente'),
            func.max(RFI.cnpj_cliente).label('cnpj_cliente'),
            func.max(RFI.municipio).label('municipio'),
            func.max(RFI.estado).label('estado'),
            func.max(RFI.valor_total).label('valor_total'),
            func.max(RFI.data_fatura).label('data_fatura'),
            func.max(RFI.vendedor).label('vendedor'),
            func.max(RFI.equipe_vendas).label('equipe_vendas'),
            func.bool_or(EntregaMonitorada.entregue).label('entregue'),
            func.bool_or(EntregaMonitorada.nf_cd).label('nf_cd'),
            func.max(EntregaMonitorada.data_embarque).label('data_embarque'),
            func.max(EntregaMonitorada.data_hora_entrega_realizada).label('data_entrega'),
            func.max(EntregaMonitorada.transportadora).label('transportadora'),
        )
        .outerjoin(
            EntregaMonitorada,
            db.and_(
                EntregaMonitorada.numero_nf == RFI.numero_nf,
                EntregaMonitorada.origem == 'NACOM',
            ),
        )
        .filter(RFI.ativo.is_(True))
        .filter(or_(*filters))
        .group_by(RFI.numero_nf)
    )

    base = _aplicar_filtro_vendedor(base, user)

    rows = (
        base.order_by(func.max(RFI.data_fatura).desc().nullslast())
        .limit(CANDIDATES_POOL)
        .all()
    )

    if not rows:
        _log(q, 0, started)
        return []

    scored = [
        (_calcular_score(row, q_clean, q_digits), _formatar_resultado(row))
        for row in rows
    ]
    scored = [(s, item) for s, item in scored if s > 0]
    scored.sort(key=lambda t: -t[0])

    out = [{**item, 'score': round(score, 3)} for score, item in scored[:limit]]
    _log(q, len(out), started)
    return out


def _aplicar_filtro_vendedor(query, user) -> object:
    if not getattr(user, 'is_authenticated', False):
        return query
    perfil = getattr(user, 'perfil', None)
    vendedor = getattr(user, 'vendedor_vinculado', None)
    if perfil == 'vendedor' and vendedor:
        return query.filter(RFI.vendedor == vendedor)
    return query


def _calcular_score(row, q: str, q_digits: str) -> float:
    """
    Score:
        1.00 = numero_nf exato
        0.95 = numero_nf starts with
        0.90 = numero_nf contains
        0.85 = CNPJ contains digits
        0.70 = nome_cliente contains
    """
    q_lower = q.lower()
    nf = (row.numero_nf or '').lower()
    nome = (row.nome_cliente or '').lower()
    cnpj = row.cnpj_cliente or ''

    if nf == q_lower:
        return 1.00
    if nf.startswith(q_lower):
        return 0.95
    if q_lower in nf:
        return 0.90
    if q_digits and len(q_digits) >= MIN_CNPJ_DIGITS and q_digits in cnpj:
        return 0.85
    if q_lower in nome:
        return 0.70
    return 0.0


def _formatar_resultado(row) -> dict:
    cliente = row.nome_cliente or '—'
    municipio_uf = (
        f"{row.municipio}/{row.estado}"
        if row.municipio and row.estado else
        (row.municipio or row.estado or '—')
    )
    valor = float(row.valor_total or 0)
    valor_fmt = (
        f"R$ {valor:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.')
    )

    data_info = ''
    if row.data_entrega:
        data_info = f"Entregue {row.data_entrega.strftime('%d/%m/%Y')}"
    elif row.data_embarque:
        data_info = f"Embarcou {row.data_embarque.strftime('%d/%m/%Y')}"
    elif row.data_fatura:
        data_info = f"Faturada {row.data_fatura.strftime('%d/%m/%Y')}"

    subtitle_parts = [cliente, municipio_uf, valor_fmt, data_info]
    subtitle = '  •  '.join(p for p in subtitle_parts if p and p != '—')

    return {
        'tipo': 'nf',
        'id': row.numero_nf,
        'label': f"NF {row.numero_nf}",
        'subtitle': subtitle,
        'url': f'/monitoramento/listar_entregas?numero_nf={row.numero_nf}',
        'badge': _badge_status(row),
        'icon': 'fas fa-receipt',
        'extra': {
            'cnpj_cliente': row.cnpj_cliente,
            'transportadora': row.transportadora,
            'vendedor': row.vendedor,
        },
    }


def _badge_status(row) -> Optional[dict]:
    """Mapeia status entrega para badge."""
    if row.entregue:
        return {'label': 'Entregue', 'tone': 'success'}
    if row.nf_cd:
        return {'label': 'No CD', 'tone': 'warning'}
    if row.data_embarque:
        return {'label': 'Em trânsito', 'tone': 'info'}
    if row.data_fatura:
        return {'label': 'Faturada', 'tone': 'secondary'}
    return None


def _log(q: str, n_results: int, started: float) -> None:
    elapsed_ms = (time.time() - started) * 1000
    try:
        current_app.logger.info(
            f"[cmdk.buscar_nfs] q={q!r} results={n_results} took_ms={elapsed_ms:.1f}"
        )
    except RuntimeError:
        pass

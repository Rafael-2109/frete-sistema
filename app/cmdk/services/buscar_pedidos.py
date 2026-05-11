"""
Busca de pedidos para o Ctrl+K.

Faz match em CarteiraPrincipal (filtro ativo=True) com GROUP BY num_pedido,
agregando totais. Aplica scoring por tipo de match (num_pedido > CNPJ > razao
social > pedido_cliente).

Permissoes:
- perfil 'vendedor' com vendedor_vinculado: filtra apenas pedidos do vendedor
- demais perfis logistica/financeiro/admin: ve tudo
"""
from __future__ import annotations

import re
import time
from typing import Optional

from flask import current_app
from flask_login import current_user
from sqlalchemy import or_, func

from app import db
from app.carteira.models import CarteiraPrincipal


# =============================================================================
# Constantes
# =============================================================================

# Maximo de candidatos puxados do banco antes do scoring (LIMIT da query)
CANDIDATES_POOL = 40

# Tamanho minimo de digitos para considerar busca por CNPJ
MIN_CNPJ_DIGITS = 4

# Regex para detectar prefixos de pedido conhecidos (case-insensitive)
PEDIDO_PREFIX_RE = re.compile(r'^[VvKk][CcFf][DdLl]?\d+', re.IGNORECASE)


# =============================================================================
# API publica
# =============================================================================

def buscar(q: str, user=None, limit: int = 6) -> list[dict]:
    """
    Busca pedidos por query livre. Retorna lista ordenada por relevancia.

    Args:
        q: query do usuario (string livre)
        user: Usuario (default current_user)
        limit: maximo de resultados

    Returns:
        Lista de dicts com formato:
        {
            'tipo': 'pedido',
            'id': 'VCD12345',
            'label': 'VCD12345',
            'subtitle': 'ATACADAO MANAUS  R$ 45.230,50  23 itens',
            'url': '/cmdk/pedido/VCD12345',
            'badge': {'label': 'Pedido de venda', 'tone': 'info'},
            'icon': 'fas fa-shopping-cart',
            'score': 0.92,
        }
    """
    user = user if user is not None else current_user
    q = (q or '').strip()
    if len(q) < 2:
        return []

    started = time.time()
    q_digits = re.sub(r'\D', '', q)

    # ----------------------------------------------------------------- filtros
    filters = []
    filters.append(CarteiraPrincipal.num_pedido.ilike(f'%{q}%'))
    filters.append(CarteiraPrincipal.raz_social_red.ilike(f'%{q}%'))
    filters.append(CarteiraPrincipal.raz_social.ilike(f'%{q}%'))
    filters.append(CarteiraPrincipal.pedido_cliente.ilike(f'%{q}%'))
    if len(q_digits) >= MIN_CNPJ_DIGITS:
        filters.append(CarteiraPrincipal.cnpj_cpf.like(f'%{q_digits}%'))

    where_clause = or_(*filters)

    # ----------------------------------------------------- GROUP BY num_pedido
    base = (
        db.session.query(
            CarteiraPrincipal.num_pedido.label('num_pedido'),
            func.max(CarteiraPrincipal.raz_social_red).label('raz_social_red'),
            func.max(CarteiraPrincipal.raz_social).label('raz_social'),
            func.max(CarteiraPrincipal.cnpj_cpf).label('cnpj_cpf'),
            func.max(CarteiraPrincipal.pedido_cliente).label('pedido_cliente'),
            func.max(CarteiraPrincipal.municipio).label('municipio'),
            func.max(CarteiraPrincipal.estado).label('estado'),
            func.max(CarteiraPrincipal.vendedor).label('vendedor'),
            func.max(CarteiraPrincipal.equipe_vendas).label('equipe_vendas'),
            func.max(CarteiraPrincipal.status_pedido).label('status_pedido'),
            func.max(CarteiraPrincipal.data_pedido).label('data_pedido'),
            # valor_total: SUM(qtd_pedido * preco) — valor total do pedido,
            # independente do que ja foi faturado (subtitle Ctrl+K)
            func.sum(
                CarteiraPrincipal.qtd_produto_pedido
                * CarteiraPrincipal.preco_produto_pedido
            ).label('valor_total'),
            func.sum(
                CarteiraPrincipal.qtd_saldo_produto_pedido
                * CarteiraPrincipal.preco_produto_pedido
            ).label('valor_saldo'),
            func.count(CarteiraPrincipal.id).label('qtd_itens'),
        )
        .filter(CarteiraPrincipal.ativo.is_(True))
        .filter(where_clause)
    )

    base = _aplicar_filtro_vendedor(base, user)

    # GROUP BY + LIMIT pool de candidatos
    rows = (
        base.group_by(CarteiraPrincipal.num_pedido)
        .order_by(func.max(CarteiraPrincipal.data_pedido).desc())
        .limit(CANDIDATES_POOL)
        .all()
    )

    if not rows:
        _log(q, 0, started)
        return []

    # ----------------------------------------------------- scoring + ordenacao
    scored = [
        (_calcular_score(row, q, q_digits), _formatar_resultado(row))
        for row in rows
    ]
    scored = [(s, item) for s, item in scored if s > 0]
    scored.sort(key=lambda t: -t[0])

    out = [{**item, 'score': round(score, 3)} for score, item in scored[:limit]]
    _log(q, len(out), started)
    return out


# =============================================================================
# Helpers internos
# =============================================================================

def _aplicar_filtro_vendedor(query, user) -> object:
    """
    Se perfil = 'vendedor' E tem vendedor_vinculado, filtra carteira.
    Caso contrario, retorna query inalterada.
    """
    if not getattr(user, 'is_authenticated', False):
        return query
    perfil = getattr(user, 'perfil', None)
    vendedor = getattr(user, 'vendedor_vinculado', None)
    if perfil == 'vendedor' and vendedor:
        return query.filter(CarteiraPrincipal.vendedor == vendedor)
    return query


def _calcular_score(row, q: str, q_digits: str) -> float:
    """
    Score baseado em onde o match ocorreu:
        1.00 = num_pedido exato (case-insensitive)
        0.95 = num_pedido starts with
        0.90 = num_pedido contains
        0.85 = CNPJ contains digits
        0.75 = raz_social_red contains
        0.65 = raz_social contains
        0.55 = pedido_cliente contains
    """
    q_lower = q.lower()
    num = (row.num_pedido or '').lower()
    raz_red = (row.raz_social_red or '').lower()
    raz = (row.raz_social or '').lower()
    ped_cli = (row.pedido_cliente or '').lower()
    cnpj = row.cnpj_cpf or ''

    if num == q_lower:
        return 1.00
    if num.startswith(q_lower):
        return 0.95
    if q_lower in num:
        return 0.90
    if q_digits and len(q_digits) >= MIN_CNPJ_DIGITS and q_digits in cnpj:
        return 0.85
    if q_lower in raz_red:
        return 0.75
    if q_lower in raz:
        return 0.65
    if q_lower in ped_cli:
        return 0.55
    return 0.0


def _formatar_resultado(row) -> dict:
    """Formata linha de query como dict de resultado para o Ctrl+K."""
    cliente = row.raz_social_red or row.raz_social or '—'
    municipio_uf = (
        f"{row.municipio}/{row.estado}"
        if row.municipio and row.estado else
        (row.municipio or row.estado or '—')
    )
    valor = float(row.valor_total or 0)
    valor_fmt = (
        f"R$ {valor:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.')
    )
    # Mostra "(saldo R$ X)" apenas se houver diferenca (parte ja faturada)
    valor_saldo = float(row.valor_saldo or 0)
    saldo_info = ''
    if valor_saldo and abs(valor_saldo - valor) > 0.01:
        saldo_fmt = (
            f"R$ {valor_saldo:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.')
        )
        saldo_info = f"saldo {saldo_fmt}"

    subtitle_parts = [cliente, municipio_uf, valor_fmt, saldo_info, f"{row.qtd_itens} itens"]
    subtitle = '  •  '.join(p for p in subtitle_parts if p and p != '—')

    badge = _badge_status(row.status_pedido)

    return {
        'tipo': 'pedido',
        'id': row.num_pedido,
        'label': row.num_pedido,
        'subtitle': subtitle,
        'url': f'/cmdk/pedido/{row.num_pedido}',
        'badge': badge,
        'icon': 'fas fa-shopping-cart',
        'extra': {
            'cnpj_cpf': row.cnpj_cpf,
            'vendedor': row.vendedor,
            'equipe_vendas': row.equipe_vendas,
        },
    }


def _badge_status(status: Optional[str]) -> Optional[dict]:
    """Mapeia status_pedido para badge {label, tone}."""
    if not status:
        return None
    status_norm = status.strip().lower()
    if 'cancel' in status_norm:
        return {'label': 'Cancelado', 'tone': 'danger'}
    if 'cota' in status_norm:
        return {'label': 'Cotação', 'tone': 'warning'}
    if 'venda' in status_norm:
        return {'label': 'Pedido de venda', 'tone': 'success'}
    return {'label': status[:20], 'tone': 'secondary'}


def _log(q: str, n_results: int, started: float) -> None:
    elapsed_ms = (time.time() - started) * 1000
    try:
        current_app.logger.info(
            f"[cmdk.buscar_pedidos] q={q!r} results={n_results} took_ms={elapsed_ms:.1f}"
        )
    except RuntimeError:
        pass  # fora do app context (testes)

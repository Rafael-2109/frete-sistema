"""
Projecao de estoque dos produtos do pedido (Ctrl+K raio-X).

Reusa ServicoEstoqueSimples + UnificacaoCodigos para calcular projecao
D0-D14 dos itens do pedido (de-duplicando codigos unificados).

Formato de retorno e compativel com modal-projecao-linha.js, permitindo
reusar o mesmo modal renderizando dados de origens diferentes.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from app import db
from app.carteira.models import CarteiraPrincipal
from app.estoque.models import UnificacaoCodigos
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.producao.models import CadastroPalletizacao


logger = logging.getLogger(__name__)

DIAS_PROJECAO = 14


def montar_projecao_estoque_pedido(num_pedido: str) -> Optional[dict]:
    """
    Monta projecao de estoque para todos os produtos ativos do pedido.

    Resolve UnificacaoCodigos para de-duplicar (1 produto canonico por familia
    unificada), busca cadastro para nome do produto, calcula projecao D0-D14
    em batch via ServicoEstoqueSimples.

    Returns:
        dict no formato esperado por modal-projecao-linha.js:
        {
            'success': True,
            'num_pedido': 'VCD123',
            'cod_produto_clicado': None,        # nao ha 1 clicado neste modo
            'codigos_destaque': [...],          # cods que aparecem no pedido
            'datas': ['2026-05-11', ...],
            'produtos': [
                {'cod_produto', 'nome_produto', 'estoque_atual',
                 'saida':[...], 'producao':[...], 'saldo':[...]}
            ]
        }
        ou None se pedido nao existir.
    """
    # 1. Pegar todos os cod_produto ativos do pedido
    rows = (
        db.session.query(CarteiraPrincipal.cod_produto)
        .filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo.is_(True),
        )
        .distinct()
        .all()
    )
    if not rows:
        return None

    cods_pedido = [r.cod_produto for r in rows if r.cod_produto]
    if not cods_pedido:
        return None

    # 2. Coletar codigos canonicos unicos (de-dup via UnificacaoCodigos)
    canonicos: dict[str, str] = {}  # {cod_canonico: cod_original_no_pedido}
    for cod_orig in cods_pedido:
        try:
            cod_canonico = str(UnificacaoCodigos.get_codigo_unificado(cod_orig))
        except Exception:
            cod_canonico = cod_orig
        if cod_canonico not in canonicos:
            canonicos[cod_canonico] = cod_orig

    cods_canonicos = list(canonicos.keys())

    # 3. Buscar nomes dos produtos via CadastroPalletizacao
    cadastros = (
        CadastroPalletizacao.query
        .filter(CadastroPalletizacao.cod_produto.in_(cods_canonicos))
        .all()
    )
    nomes = {c.cod_produto: c.nome_produto for c in cadastros}

    # 4. Calcular projecao em batch
    try:
        projecoes = ServicoEstoqueSimples.calcular_multiplos_produtos(
            cods_canonicos,
            dias=DIAS_PROJECAO,
            entrada_em_d_plus_1=False,  # Modal analitico (igual /projecao-linha)
        )
    except Exception as e:
        logger.error(
            f"[cmdk.projecao_pedido] calcular_multiplos_produtos falhou para "
            f"num_pedido={num_pedido}: {e}",
            exc_info=True,
        )
        projecoes = {}

    # 5. Montar datas D0-D14
    hoje = date.today()
    datas = [(hoje + timedelta(days=d)).isoformat() for d in range(DIAS_PROJECAO + 1)]

    # 6. Montar resposta por produto
    produtos_resposta = []
    for cod in cods_canonicos:
        proj = projecoes.get(cod, {})
        projecao_dias = proj.get('projecao', [])

        saida, producao, saldo = [], [], []
        for i in range(DIAS_PROJECAO + 1):
            if i < len(projecao_dias):
                dia = projecao_dias[i]
                saida.append(round(dia.get('saida', 0) or 0))
                producao.append(round(dia.get('entrada', 0) or 0))
                saldo.append(round(dia.get('saldo_final', 0) or 0))
            else:
                saida.append(0)
                producao.append(0)
                saldo.append(0)

        produtos_resposta.append({
            'cod_produto': cod,
            'nome_produto': nomes.get(cod) or canonicos[cod],
            'estoque_atual': round(proj.get('estoque_atual', 0) or 0),
            'saida': saida,
            'producao': producao,
            'saldo': saldo,
        })

    # Ordenar produtos por nome (estabilidade visual)
    produtos_resposta.sort(key=lambda p: (p['nome_produto'] or '').lower())

    logger.info(
        f"[cmdk.projecao_pedido] num_pedido={num_pedido} "
        f"produtos_brutos={len(cods_pedido)} canonicos={len(cods_canonicos)}"
    )

    return {
        'success': True,
        'num_pedido': num_pedido,
        'cod_produto_clicado': None,
        'codigos_destaque': cods_canonicos,  # todos sao do pedido
        'datas': datas,
        'produtos': produtos_resposta,
    }


def codigos_canonicos_do_pedido(num_pedido: str) -> list[str]:
    """
    Retorna lista de codigos canonicos (apos UnificacaoCodigos) para os produtos
    do pedido — usado pelo modal de projecao por linha para destacar quais
    produtos da linha aparecem no pedido.
    """
    rows = (
        db.session.query(CarteiraPrincipal.cod_produto)
        .filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo.is_(True),
        )
        .distinct()
        .all()
    )
    cods = [r.cod_produto for r in rows if r.cod_produto]
    canonicos = set()
    for cod in cods:
        try:
            canonicos.add(str(UnificacaoCodigos.get_codigo_unificado(cod)))
        except Exception:
            canonicos.add(cod)
    return sorted(canonicos)

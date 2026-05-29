"""
Service de criacao de CadastroPalletizacao basico
=================================================

OBJETIVO:
    Garantir (idempotente) que exista um CadastroPalletizacao para um produto,
    criando um cadastro BASICO (codigo + nome + palletizacao/peso zerados) quando
    ele ainda nao existe, com os flags produto_comprado / produto_produzido /
    produto_vendido definidos pela NATUREZA do produto.

CONTEXTO (2026-05-28):
    Produtos comprados produtivos/revenda (sync de compras — entrada_material_service)
    e produtos acabados de industrializacao LF (recebimento_lf_odoo_service) passam a
    ser registrados em MovimentacaoEstoque mesmo sem cadastro previo. Este service
    cria o cadastro minimo necessario.

    Padrao herdado de app/estoque/routes.py:488-497 (auto-criar com pallet/peso 0).

NAO COMMITA:
    Faz db.session.add + flush; o CALLER eh responsavel pelo commit. Isso evita
    vazar transacao/savepoint quando chamado de dentro de um fluxo maior.
"""
import logging
from typing import Optional, Tuple

from app import db
from app.producao.models import CadastroPalletizacao

logger = logging.getLogger(__name__)

# Naturezas suportadas (alinhadas com app/odoo/utils/classificacao_produto.py)
NATUREZA_PRODUTIVO = 'PRODUTIVO'      # materia-prima / embalagem / semi-acabado / insumo
NATUREZA_REVENDA = 'REVENDA'          # mercadoria para revenda (tipo fiscal 00)
NATUREZA_ACABADO_LF = 'ACABADO_LF'    # produto acabado vindo da industrializacao LF

# Natureza -> flags do CadastroPalletizacao
_FLAGS_POR_NATUREZA = {
    NATUREZA_PRODUTIVO: {
        'produto_comprado': True,
        'produto_produzido': False,
        'produto_vendido': False,
    },
    NATUREZA_REVENDA: {
        'produto_comprado': True,
        'produto_produzido': False,
        'produto_vendido': True,
    },
    NATUREZA_ACABADO_LF: {
        'produto_comprado': False,
        'produto_produzido': True,
        'produto_vendido': True,
    },
}


def garantir_cadastro_basico(
    cod_produto: str,
    nome_produto: str,
    natureza: str,
    criado_por: Optional[str] = None,
) -> Tuple[CadastroPalletizacao, bool]:
    """
    Garante que exista um CadastroPalletizacao para cod_produto.

    Idempotente: se ja existe, retorna o existente sem alterar nada. Se nao
    existe, cria um cadastro basico (palletizacao=0, peso_bruto=0) com os flags
    da natureza informada.

    Args:
        cod_produto: codigo interno do produto (default_code do Odoo)
        nome_produto: nome/descricao do produto (truncado em 255 chars)
        natureza: 'PRODUTIVO' | 'REVENDA' | 'ACABADO_LF' (define os flags)
        criado_por: identificacao de quem criou (apenas log)

    Returns:
        (cadastro, criado): a instancia (existente ou nova) e bool indicando se
        foi criada agora.

    Raises:
        ValueError: se cod_produto vazio ou natureza desconhecida.
    """
    if not cod_produto:
        raise ValueError("cod_produto vazio ao garantir CadastroPalletizacao")

    flags = _FLAGS_POR_NATUREZA.get(natureza)
    if flags is None:
        raise ValueError(
            f"Natureza desconhecida '{natureza}' "
            f"(esperado: {sorted(_FLAGS_POR_NATUREZA)})"
        )

    cod = str(cod_produto).strip()

    existente = CadastroPalletizacao.query.filter_by(cod_produto=cod).first()
    if existente:
        return existente, False

    cadastro = CadastroPalletizacao(
        cod_produto=cod,
        nome_produto=(str(nome_produto).strip() if nome_produto else cod)[:255],
        palletizacao=0,
        peso_bruto=0,
        ativo=True,
        **flags,
    )
    db.session.add(cadastro)
    db.session.flush()  # garante visibilidade/PK; commit fica com o caller

    logger.info(
        f"[CadastroPalletizacao] Auto-criado basico: {cod} "
        f"('{cadastro.nome_produto}') natureza={natureza} "
        f"(comprado={flags['produto_comprado']}, produzido={flags['produto_produzido']}, "
        f"vendido={flags['produto_vendido']}) por={criado_por or 'sistema'}"
    )
    return cadastro, True

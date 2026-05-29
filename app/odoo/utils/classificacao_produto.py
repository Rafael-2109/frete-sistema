"""
Classificacao de produtos do Odoo para registro em MovimentacaoEstoque
=======================================================================

OBJETIVO:
    Decidir se um produto vindo de uma ENTRADA (compra) deve ser registrado em
    MovimentacaoEstoque e qual a "natureza" dele, com base na CATEGORIA
    (categ_id do Odoo) e no TIPO FISCAL (l10n_br_tipo_produto / SPED Bloco 0200).

CONTEXTO (2026-05-28):
    O sync de entradas de compra (entrada_material_service) so registrava
    produtos ja cadastrados em CadastroPalletizacao com produto_comprado=True.
    Produtos comprados SEM cadastro eram PULADOS. Esta classificacao identifica
    quais produtos comprados sao "produtivos ou de revenda", para criar cadastro
    basico e registrar a movimentacao.

CRITERIO (decidido com o usuario):
    Registra (natureza != None) se:
      - categoria-raiz in {MATERIA PRIMA, EMBALAGEM, SEMI ACABADOS}  -> PRODUTIVO
      - OU l10n_br_tipo_produto in {01,02,06,10}                     -> PRODUTIVO
      - OU l10n_br_tipo_produto == '00' (Mercadoria para Revenda)    -> REVENDA
    Caso contrario (USO E CONSUMO, DESPESAS, ATIVO FIXO, SERVICO, ATIVO
    INTANGIVEL, categoria generica "TODOS", etc) -> None (NAO registrar).

    A categoria-raiz eh o classificador PRINCIPAL porque ~88% dos produtos tem
    l10n_br_tipo_produto vazio (False) no Odoo CIEL IT. A revenda, porem, so eh
    identificavel via tipo fiscal '00' (nao ha categoria-raiz "REVENDA").

FONTES (exploracao Odoo ao vivo 2026-05-28):
    - product.product.categ_id retorna [id, complete_name], onde complete_name eh
      a hierarquia "TODOS / MATERIA PRIMA / MP NAC / PALMITO".
    - l10n_br_tipo_produto (selection): 00..10, 99. Ver SPED Bloco 0200 TIPO_ITEM.
"""
from typing import Optional

# Categorias-raiz (2o segmento do complete_name "TODOS / <RAIZ> / ...") que
# representam produtos usados na producao.
CATEGORIAS_RAIZ_PRODUTIVAS = {
    'MATERIA PRIMA',
    'EMBALAGEM',
    'SEMI ACABADOS',
}

# Tipos fiscais (l10n_br_tipo_produto) considerados PRODUTIVOS:
# 01 = Materia Prima | 02 = Embalagem | 06 = Produto Intermediario | 10 = Outros insumos
TIPOS_FISCAIS_PRODUTIVOS = {'01', '02', '06', '10'}

# 00 = Mercadoria para Revenda
TIPO_FISCAL_REVENDA = '00'

# Naturezas retornadas (alinhadas com cadastro_palletizacao_service._FLAGS_POR_NATUREZA)
NATUREZA_PRODUTIVO = 'PRODUTIVO'
NATUREZA_REVENDA = 'REVENDA'


def extrair_categoria_raiz(complete_name: Optional[str]) -> Optional[str]:
    """
    Extrai a categoria-raiz de negocio a partir do complete_name do Odoo.

    O Odoo devolve categ_id como [id, complete_name], onde complete_name eh a
    hierarquia completa: "TODOS / MATERIA PRIMA / MP NAC / PALMITO". A
    categoria-raiz de negocio eh o 2o segmento ("MATERIA PRIMA").

    Args:
        complete_name: caminho completo da categoria (ex "TODOS / MATERIA PRIMA / ...")

    Returns:
        Categoria-raiz em UPPER, sem espacos nas pontas, ou None:
          - "TODOS / MATERIA PRIMA / MP NAC" -> "MATERIA PRIMA"
          - "TODOS"                          -> None (categoria generica)
          - None / "" / "   "                -> None
    """
    if not complete_name:
        return None
    partes = [p.strip() for p in complete_name.split('/') if p.strip()]
    if not partes:
        return None
    # Topo esperado: "TODOS". A categoria-raiz de negocio eh o segmento seguinte.
    if partes[0].upper() == 'TODOS':
        if len(partes) < 2:
            return None  # produto direto em "TODOS" = generico
        return partes[1].upper()
    # Arvore sem "TODOS" no topo: usar o 1o segmento como raiz.
    return partes[0].upper()


def classificar_natureza_compra(
    categoria_raiz: Optional[str],
    tipo_produto: Optional[str],
) -> Optional[str]:
    """
    Classifica a natureza de um produto comprado para fins de registro de estoque.

    Args:
        categoria_raiz: categoria-raiz ja extraida (ver extrair_categoria_raiz).
        tipo_produto: valor de l10n_br_tipo_produto (ex '00','01'...). O Odoo
                      retorna False quando vazio — tratado como None.

    Returns:
        'REVENDA'   -> produto de revenda (tipo fiscal 00)
        'PRODUTIVO' -> materia-prima / embalagem / semi-acabado / intermediario / insumo
        None        -> NAO registrar (uso e consumo, despesas, ativo, servico, generico)
    """
    # Odoo manda False quando o campo selection esta vazio
    tipo = tipo_produto if tipo_produto else None
    raiz = categoria_raiz.upper() if categoria_raiz else None

    # 1) Revenda eh identificavel SOMENTE pelo tipo fiscal
    if tipo == TIPO_FISCAL_REVENDA:
        return NATUREZA_REVENDA

    # 2) Produtivo por categoria-raiz (criterio principal)
    if raiz in CATEGORIAS_RAIZ_PRODUTIVAS:
        return NATUREZA_PRODUTIVO

    # 3) Produtivo por tipo fiscal explicito (reforco quando preenchido)
    if tipo in TIPOS_FISCAIS_PRODUTIVOS:
        return NATUREZA_PRODUTIVO

    return None


def classificar_produto_odoo(
    categ_complete_name: Optional[str],
    tipo_produto: Optional[str],
) -> Optional[str]:
    """
    Conveniencia: extrai a categoria-raiz do complete_name e classifica.

    Args:
        categ_complete_name: complete_name vindo de product.product.categ_id[1]
        tipo_produto: l10n_br_tipo_produto (pode ser False/None)

    Returns:
        'PRODUTIVO' | 'REVENDA' | None
    """
    raiz = extrair_categoria_raiz(categ_complete_name)
    return classificar_natureza_compra(raiz, tipo_produto)

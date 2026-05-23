"""
Matriz de obrigatoriedade do cadastro de produto (CADASTROS MORTAIS).

Cada regra possui DUAS dimensoes:
    - Severidade (BLOQ / ALERTA / INFO) — urgencia
    - Categoria  (ORFAO_PURO / REPARAR_MESTRE / CADASTRO_FALTANTE) — tipo de acao

A categoria define qual MODAL/TELA usar para corrigir.

Versao 2 (26/05/2026): redefinida com base nos cadastros mortais informados:
    1. custo_considerado (apenas comprados)
    2. BOM (apenas produzidos)
    3. capacidade produtiva (apenas produzido + vendido)
    4. CadastroPalletizacao
        - Universal: categoria, materia_prima, embalagem
        - Vendido:   palletizacao, peso_bruto, medidas
        - Produzido: linha_producao
        - Comprado:  lead_time, lote_minimo_compra
"""

# ---------------------------------------------------------------------------
# Severidade
# ---------------------------------------------------------------------------
SEVERIDADE_BLOQ = "BLOQ"
SEVERIDADE_ALERTA = "ALERTA"
SEVERIDADE_INFO = "INFO"

# ---------------------------------------------------------------------------
# Flag (origem da regra)
# ---------------------------------------------------------------------------
FLAG_VENDIDO = "vendido"
FLAG_PRODUZIDO = "produzido"
FLAG_COMPRADO = "comprado"
FLAG_UNIVERSAL = "universal"

# ---------------------------------------------------------------------------
# Categoria de ACAO (qual modal/tela abrir)
# ---------------------------------------------------------------------------
CATEGORIA_ORFAO_PURO = "orfao_puro"           # cadastrar produto no mestre (CREATE)
CATEGORIA_REPARAR_MESTRE = "reparar_mestre"   # campo faltando no proprio mestre (UPDATE)
CATEGORIA_CADASTRO_FALTANTE = "cadastro_faltante"  # criar registro em outra tabela (CREATE externo)

# ---------------------------------------------------------------------------
# Acao (qual modal abrir)
# ---------------------------------------------------------------------------
ACAO_CRIAR_MESTRE = "criar_mestre"                       # modal_criar_mestre
ACAO_EDITAR_MESTRE = "editar_mestre"                     # modal_editar_mestre
ACAO_ADD_BOM = "add_bom"                                 # modal_add_bom
ACAO_ADD_RECURSO = "add_recurso"                         # modal_add_recurso
ACAO_ADD_CUSTO_CONSIDERADO = "add_custo_considerado"     # modal_add_custo_considerado

CLASSE_BADGE = {
    SEVERIDADE_BLOQ: "danger",
    SEVERIDADE_ALERTA: "warning",
    SEVERIDADE_INFO: "info",
}

ICONE_CATEGORIA = {
    CATEGORIA_ORFAO_PURO: "fa-ghost",
    CATEGORIA_REPARAR_MESTRE: "fa-wrench",
    CATEGORIA_CADASTRO_FALTANTE: "fa-puzzle-piece",
}

ROTULO_CATEGORIA = {
    CATEGORIA_ORFAO_PURO: "Orfaos Puros (sem cadastro)",
    CATEGORIA_REPARAR_MESTRE: "Reparar Mestre",
    CATEGORIA_CADASTRO_FALTANTE: "Cadastros Faltantes",
}

DESCRICAO_CATEGORIA = {
    CATEGORIA_ORFAO_PURO: (
        "Codigos de produto que aparecem em transacionais (CarteiraPrincipal, "
        "Faturamento, MovimentacaoEstoque, etc.) mas nao existem em "
        "cadastro_palletizacao. Solucao: criar no mestre."
    ),
    CATEGORIA_REPARAR_MESTRE: (
        "Produto existe no mestre, mas tem campos obrigatorios faltando. "
        "Solucao: editar diretamente o mestre cadastro_palletizacao."
    ),
    CATEGORIA_CADASTRO_FALTANTE: (
        "Produto OK no mestre, mas falta cadastro em tabela externa necessaria "
        "(BOM, capacidade produtiva, custo considerado). "
        "Solucao: criar registro na tabela faltante."
    ),
}

# ---------------------------------------------------------------------------
# Definicao das regras — 14 cadastros mortais
# ---------------------------------------------------------------------------

REGRAS = [
    # ===== M) UNIVERSAIS (todo produto, independente das flags) =====
    {
        "id": "M1",
        "flag": FLAG_UNIVERSAL,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_ORFAO_PURO,
        "acao": ACAO_CRIAR_MESTRE,
        "titulo": "Sem cadastro no mestre",
        "descricao": (
            "cod_produto aparece em transacional (CarteiraPrincipal, Faturamento, "
            "MovimentacaoEstoque, etc.) sem registro em cadastro_palletizacao."
        ),
    },
    {
        "id": "M2",
        "flag": FLAG_UNIVERSAL,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "categoria_produto",
        "titulo": "Sem categoria",
        "descricao": "Todo produto precisa de categoria_produto preenchida.",
    },
    {
        "id": "M3",
        "flag": FLAG_UNIVERSAL,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "tipo_materia_prima",
        "titulo": "Sem tipo de materia-prima",
        "descricao": "Todo produto precisa de tipo_materia_prima preenchido.",
    },
    {
        "id": "M4",
        "flag": FLAG_UNIVERSAL,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "tipo_embalagem",
        "titulo": "Sem tipo de embalagem",
        "descricao": "Todo produto precisa de tipo_embalagem preenchido.",
    },

    # ===== V) VENDIDO =====
    {
        "id": "V1",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "palletizacao",
        "titulo": "Sem palletizacao",
        "descricao": "Produto vendido precisa de palletizacao > 0 para calcular pallets de embarque.",
    },
    {
        "id": "V2",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "peso_bruto",
        "titulo": "Sem peso bruto",
        "descricao": "Produto vendido precisa de peso_bruto > 0 para cotacao de frete.",
    },
    {
        "id": "V3",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "altura_cm",
        "titulo": "Sem medidas (altura/largura/comprimento)",
        "descricao": "Produto vendido precisa de altura, largura e comprimento para calculo de cubagem.",
    },

    # ===== P) PRODUZIDO =====
    {
        "id": "P1",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "linha_producao",
        "titulo": "Sem linha de producao",
        "descricao": "Produto produzido precisa de linha_producao definida no mestre.",
    },
    {
        "id": "P2",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_ADD_BOM,
        "titulo": "Sem estrutura (BOM)",
        "descricao": "Produto produzido sem componentes em lista_materiais — producao nao consome insumos.",
    },
    {
        "id": "P3",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_ADD_RECURSO,
        "titulo": "Sem capacidade produtiva",
        "descricao": (
            "Produto produzido E vendido sem registro em recursos_producao com "
            "capacidade_unidade_minuto > 0. Necessario para acabados (produtos finais)."
        ),
    },
    {
        "id": "P4",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_CRIAR_MESTRE,
        "titulo": "Componente do BOM sem cadastro",
        "descricao": (
            "lista_materiais aponta componentes (cod_produto_componente) que nao "
            "existem em cadastro_palletizacao. O componente em si aparece na aba "
            "Orfaos Puros; o produto pai aparece aqui para indicar qual BOM esta "
            "incompleto."
        ),
    },

    # ===== C) COMPRADO =====
    {
        "id": "C1",
        "flag": FLAG_COMPRADO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "lead_time",
        "titulo": "Sem lead time",
        "descricao": "Produto comprado precisa de lead_time para planejamento de compra.",
    },
    {
        "id": "C2",
        "flag": FLAG_COMPRADO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "lote_minimo_compra",
        "titulo": "Sem lote minimo de compra",
        "descricao": "Produto comprado precisa de lote_minimo_compra para emissao de PO viavel.",
    },
    {
        "id": "C3",
        "flag": FLAG_COMPRADO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_ADD_CUSTO_CONSIDERADO,
        "titulo": "Sem custo considerado",
        "descricao": (
            "Produto comprado sem registro em custo_considerado com custo_atual=true. "
            "Necessario para custeio de COGS. Produtos PRODUZIDOS recebem custo via BOM "
            "(tela /custeio/definicao), nao precisam aparecer aqui."
        ),
    },
]


def regra_por_id(regra_id: str) -> dict | None:
    for r in REGRAS:
        if r["id"] == regra_id:
            return r
    return None


def regras_por_categoria(categoria: str) -> list[dict]:
    return [r for r in REGRAS if r["categoria"] == categoria]


def regras_por_flag(flag: str) -> list[dict]:
    return [r for r in REGRAS if r["flag"] == flag]

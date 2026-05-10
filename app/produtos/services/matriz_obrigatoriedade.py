"""
Matriz de obrigatoriedade do cadastro de produto.

Cada regra ganhou DUAS dimensoes:
    - Severidade (BLOQ / ALERTA / INFO) - urgencia
    - Categoria  (ORFAO_PURO / REPARAR_MESTRE / CADASTRO_FALTANTE / DIVERGENCIA) - tipo de acao

A categoria define qual MODAL/TELA usar para corrigir.
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
CATEGORIA_DIVERGENCIA = "divergencia"         # mestre vs transacional divergem

# ---------------------------------------------------------------------------
# Acao (qual modal abrir)
# ---------------------------------------------------------------------------
ACAO_CRIAR_MESTRE = "criar_mestre"                       # modal_criar_mestre
ACAO_EDITAR_MESTRE = "editar_mestre"                     # modal_editar_mestre
ACAO_ADD_BOM = "add_bom"                                 # modal_add_bom
ACAO_ADD_RECURSO = "add_recurso"                         # modal_add_recurso
ACAO_ADD_PERFIL_FISCAL = "add_perfil_fiscal"             # modal_add_perfil_fiscal
ACAO_LINK_DEPARA_ATACADAO = "link_depara_atacadao"       # link
ACAO_LINK_DEPARA_SENDAS = "link_depara_sendas"           # link
ACAO_LINK_PRECO_REDE = "link_preco_rede"                 # link informativo
ACAO_RESOLVER_NOME = "resolver_nome"                     # modal_resolver_nome
ACAO_RESOLVER_PESO = "resolver_peso"                     # modal_resolver_peso
ACAO_INFO = "info"                                       # apenas informativo

CLASSE_BADGE = {
    SEVERIDADE_BLOQ: "danger",
    SEVERIDADE_ALERTA: "warning",
    SEVERIDADE_INFO: "info",
}

ICONE_CATEGORIA = {
    CATEGORIA_ORFAO_PURO: "fa-ghost",
    CATEGORIA_REPARAR_MESTRE: "fa-wrench",
    CATEGORIA_CADASTRO_FALTANTE: "fa-puzzle-piece",
    CATEGORIA_DIVERGENCIA: "fa-not-equal",
}

ROTULO_CATEGORIA = {
    CATEGORIA_ORFAO_PURO: "Orfaos Puros (sem cadastro)",
    CATEGORIA_REPARAR_MESTRE: "Reparar Mestre",
    CATEGORIA_CADASTRO_FALTANTE: "Cadastros Faltantes",
    CATEGORIA_DIVERGENCIA: "Divergencias",
}

DESCRICAO_CATEGORIA = {
    CATEGORIA_ORFAO_PURO: (
        "Codigos de produto que aparecem em transacionais (faturamento, separacao, etc.) "
        "mas nao existem em cadastro_palletizacao. Solucao: criar no mestre."
    ),
    CATEGORIA_REPARAR_MESTRE: (
        "Produto existe no mestre, mas tem campos obrigatorios faltando. "
        "Solucao: editar diretamente o mestre cadastro_palletizacao."
    ),
    CATEGORIA_CADASTRO_FALTANTE: (
        "Produto OK no mestre, mas falta cadastro em tabelas externas necessarias "
        "(BOM, capacidade, perfil fiscal, etc.). Solucao: criar registro na tabela faltante."
    ),
    CATEGORIA_DIVERGENCIA: (
        "Produto cadastrado, mas valores no mestre diferem dos valores em tabelas transacionais "
        "(faturamento, carteira). Investigar qual e a verdade e atualizar."
    ),
}

# ---------------------------------------------------------------------------
# Definicao das regras
# ---------------------------------------------------------------------------

REGRAS = [
    # ===== A) produto_vendido = TRUE =====
    {
        "id": "A1",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "palletizacao",
        "titulo": "Palletizacao zero ou nula",
        "descricao": "Produto vendido precisa de palletizacao > 0 para calcular pallets de embarque.",
    },
    {
        "id": "A2",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "peso_bruto",
        "titulo": "Peso bruto zero ou nulo",
        "descricao": "Produto vendido precisa de peso_bruto > 0 para cotacao de frete.",
    },
    {
        "id": "A3",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_INFO,
        "categoria": CATEGORIA_DIVERGENCIA,
        "acao": ACAO_INFO,
        "titulo": "Sem unidade de medida na carteira",
        "descricao": "carteira_principal.unid_medida_produto vazio. O mestre nao tem essa coluna (gap conhecido).",
    },
    {
        "id": "A4",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_ALERTA,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_LINK_DEPARA_ATACADAO,
        "titulo": "Sem De-Para Atacadao",
        "descricao": "Produto faturado para CNPJ Atacadao sem registro em portal_atacadao_produto_depara.",
    },
    {
        "id": "A5",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_ALERTA,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_LINK_DEPARA_SENDAS,
        "titulo": "Sem De-Para Sendas",
        "descricao": "Produto faturado para CNPJ Sendas/Assai sem registro em portal_sendas_produto_depara.",
    },
    {
        "id": "A6",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_ALERTA,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_LINK_PRECO_REDE,
        "titulo": "Sem preco em tabela rede",
        "descricao": "Produto faturado sem preco vigente em tabela_rede_precos.",
    },
    {
        "id": "A7",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_INFO,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "altura_cm",
        "titulo": "Sem dimensoes fisicas",
        "descricao": "Produto sem altura/largura/comprimento dificulta calculo de cubagem.",
    },
    {
        "id": "A8",
        "flag": FLAG_VENDIDO,
        "severidade": SEVERIDADE_INFO,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "categoria_produto",
        "titulo": "Sem categoria",
        "descricao": "categoria_produto e tipo_embalagem nao preenchidos.",
    },

    # ===== B) produto_produzido = TRUE =====
    {
        "id": "B1",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "linha_producao",
        "titulo": "Sem linha de producao",
        "descricao": "Produto produzido precisa de linha_producao definida no mestre.",
    },
    {
        "id": "B2",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "disparo_producao",
        "titulo": "Sem disparo de producao",
        "descricao": "Produto produzido precisa de disparo_producao (MTO/MTS).",
    },
    {
        "id": "B3",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_ADD_BOM,
        "titulo": "Sem estrutura (BOM)",
        "descricao": "Produto produzido sem componentes em lista_materiais. Producao nao consome insumos.",
    },
    {
        "id": "B4",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "custo_produto",
        "titulo": "Sem custo definido",
        "descricao": "Sem custo_produto no mestre e sem custo_considerado.custo_atual=true.",
    },
    {
        "id": "B5",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_ADD_RECURSO,
        "titulo": "Sem capacidade produtiva",
        "descricao": "Produto produzido sem registro em recursos_producao com capacidade_unidade_minuto > 0.",
    },
    {
        "id": "B6",
        "flag": FLAG_PRODUZIDO,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_CRIAR_MESTRE,
        "titulo": "Componente BOM orfao",
        "descricao": "lista_materiais aponta componentes que nao existem em cadastro_palletizacao.",
    },

    # ===== C) produto_comprado = TRUE =====
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
        "categoria": CATEGORIA_CADASTRO_FALTANTE,
        "acao": ACAO_ADD_PERFIL_FISCAL,
        "titulo": "Sem perfil fiscal",
        "descricao": "Produto comprado sem nenhum registro em perfil_fiscal_produto_fornecedor (NCM/CFOP/aliquotas).",
    },
    {
        "id": "C3",
        "flag": FLAG_COMPRADO,
        "severidade": SEVERIDADE_ALERTA,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "lote_minimo_compra",
        "titulo": "Sem lote minimo de compra",
        "descricao": "lote_minimo_compra nao definido — comprador pode emitir PO inviavel.",
    },
    {
        "id": "C4",
        "flag": FLAG_COMPRADO,
        "severidade": SEVERIDADE_ALERTA,
        "categoria": CATEGORIA_REPARAR_MESTRE,
        "acao": ACAO_EDITAR_MESTRE,
        "campo_alvo": "custo_produto",
        "titulo": "Sem custo de referencia",
        "descricao": "custo_produto no mestre nao definido para item comprado.",
    },

    # ===== D) universais =====
    {
        "id": "D1",
        "flag": FLAG_UNIVERSAL,
        "severidade": SEVERIDADE_BLOQ,
        "categoria": CATEGORIA_ORFAO_PURO,
        "acao": ACAO_CRIAR_MESTRE,
        "titulo": "Orfao puro: cod_produto sem cadastro",
        "descricao": "cod_produto aparece em transacional sem registro no mestre.",
    },
    {
        "id": "D2",
        "flag": FLAG_UNIVERSAL,
        "severidade": SEVERIDADE_ALERTA,
        "categoria": CATEGORIA_DIVERGENCIA,
        "acao": ACAO_RESOLVER_NOME,
        "titulo": "Nome divergente entre tabelas",
        "descricao": "nome_produto no mestre difere do nome_produto em transacionais.",
    },
    {
        "id": "D3",
        "flag": FLAG_UNIVERSAL,
        "severidade": SEVERIDADE_ALERTA,
        "categoria": CATEGORIA_DIVERGENCIA,
        "acao": ACAO_RESOLVER_PESO,
        "titulo": "Peso divergente",
        "descricao": "peso_bruto do mestre divergente de peso_unitario_produto em faturamento (>5%).",
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

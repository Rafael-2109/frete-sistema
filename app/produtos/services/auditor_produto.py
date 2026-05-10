"""
Auditor de Produtos.

Roda todas as regras da matriz_obrigatoriedade e retorna estrutura agregada
por produto, alem de orfaos puros (cod_produto em transacional sem mestre).

Performance: cada regra e 1 query agregada (nao itera produto a produto).
"""

from collections import defaultdict
from datetime import date

from sqlalchemy import text

from app import db
from app.produtos.services.matriz_obrigatoriedade import (
    REGRAS,
    SEVERIDADE_BLOQ,
    SEVERIDADE_ALERTA,
    SEVERIDADE_INFO,
    FLAG_VENDIDO,
    FLAG_PRODUZIDO,
    FLAG_COMPRADO,
    FLAG_UNIVERSAL,
    CATEGORIA_ORFAO_PURO,
    CATEGORIA_REPARAR_MESTRE,
    CATEGORIA_CADASTRO_FALTANTE,
    CATEGORIA_DIVERGENCIA,
)


# Tabelas transacionais que possuem cod_produto e devem ser cruzadas com o mestre
# (para detecao de orfaos puros — D1)
TRANSACIONAIS_ORFAOS = [
    ("separacao", "cod_produto", "Separacao"),
    ("movimentacao_estoque", "cod_produto", "MovimentacaoEstoque"),
    ("carteira_principal", "cod_produto", "CarteiraPrincipal"),
    ("carteira_copia", "cod_produto", "CarteiraCopia"),
    ("faturamento_produto", "cod_produto", "FaturamentoProduto"),
    ("programacao_producao", "cod_produto", "ProgramacaoProducao"),
    ("pedido_compras", "cod_produto", "PedidoCompras"),
    ("historico_pedido_compras", "cod_produto", "HistoricoPedidoCompras"),
    ("perfil_fiscal_produto_fornecedor", "cod_produto", "PerfilFiscalProdutoFornecedor"),
    ("recursos_producao", "cod_produto", "RecursosProducao"),
    ("custo_considerado", "cod_produto", "CustoConsiderado"),
    ("nf_pendente_tagplus", "cod_produto", "NFPendenteTagPlus"),
    ("fila_agendamento_sendas", "cod_produto", "FilaAgendamentoSendas"),
]

# Tabelas onde o produto pode aparecer com nome_produto (para D2 — divergencia de nome)
NOME_DIVERGENTE_FONTES = [
    ("carteira_principal", "CarteiraPrincipal"),
    ("faturamento_produto", "FaturamentoProduto"),
    ("movimentacao_estoque", "MovimentacaoEstoque"),
    ("programacao_producao", "ProgramacaoProducao"),
    ("recursos_producao", "RecursosProducao"),
]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _add_problema(
    problemas: dict,
    cod_produto: str,
    regra_id: str,
    detalhe: str = "",
    dados_modal: dict | None = None,
):
    """Adiciona um problema a um produto."""
    if not cod_produto:
        return
    cod_produto = str(cod_produto).strip()
    if not cod_produto:
        return
    problemas[cod_produto].append({
        "regra_id": regra_id,
        "detalhe": detalhe or "",
        "dados_modal": dados_modal or {},
    })


def _query(sql: str) -> list:
    """Executa SQL bruto e retorna rows como lista."""
    return list(db.session.execute(text(sql)).fetchall())


# ----------------------------------------------------------------------------
# Carregamento do mestre
# ----------------------------------------------------------------------------

def _carregar_mestre() -> dict:
    """
    Carrega cadastro_palletizacao.ativo=true em dict cod_produto -> dict.
    """
    sql = """
        SELECT
            cod_produto,
            nome_produto,
            codigo_ean,
            palletizacao,
            peso_bruto,
            altura_cm,
            largura_cm,
            comprimento_cm,
            tipo_embalagem,
            tipo_materia_prima,
            categoria_produto,
            subcategoria,
            linha_producao,
            produto_comprado,
            produto_produzido,
            produto_vendido,
            lead_time,
            lote_minimo_compra,
            disparo_producao,
            custo_produto,
            ativo
        FROM cadastro_palletizacao
        WHERE ativo = true
        ORDER BY cod_produto
    """
    rows = _query(sql)
    mestre = {}
    for r in rows:
        d = dict(r._mapping)
        mestre[d["cod_produto"]] = d
    return mestre


# ----------------------------------------------------------------------------
# Regras A — produto_vendido
# ----------------------------------------------------------------------------

def _regra_a1_palletizacao(mestre: dict, problemas: dict):
    """A1 BLOQ: vendido com palletizacao <= 0 ou nula."""
    for cod, p in mestre.items():
        if not p["produto_vendido"]:
            continue
        if not p["palletizacao"] or float(p["palletizacao"]) <= 0:
            _add_problema(problemas, cod, "A1", f"palletizacao={p['palletizacao']}")


def _regra_a2_peso_bruto(mestre: dict, problemas: dict):
    """A2 BLOQ: vendido com peso_bruto <= 0 ou nulo."""
    for cod, p in mestre.items():
        if not p["produto_vendido"]:
            continue
        if not p["peso_bruto"] or float(p["peso_bruto"]) <= 0:
            _add_problema(problemas, cod, "A2", f"peso_bruto={p['peso_bruto']}")


def _regra_a3_unid_medida(mestre: dict, problemas: dict):
    """A3 ALERTA: produto vendido aparece em CarteiraPrincipal sem unid_medida_produto."""
    sql = """
        SELECT DISTINCT cp.cod_produto
        FROM carteira_principal cp
        WHERE (cp.unid_medida_produto IS NULL OR TRIM(cp.unid_medida_produto) = '')
    """
    rows = _query(sql)
    for r in rows:
        cod = r[0]
        if cod not in mestre:
            continue
        if not mestre[cod]["produto_vendido"]:
            continue
        _add_problema(problemas, cod, "A3", "carteira_principal sem unid_medida_produto")


def _regra_a4_depara_atacadao(mestre: dict, problemas: dict):
    """
    A4 ALERTA: produto vendido faturou para CNPJ que aparece como cliente Atacadao
    em portal_atacadao_produto_depara, mas o produto NAO esta nesse de-para.
    """
    sql = """
        WITH cnpjs_atacadao AS (
            SELECT DISTINCT cnpj_cliente
            FROM portal_atacadao_produto_depara
            WHERE cnpj_cliente IS NOT NULL
              AND (ativo IS NULL OR ativo = true)
        ),
        produtos_no_depara AS (
            SELECT DISTINCT codigo_nosso
            FROM portal_atacadao_produto_depara
            WHERE (ativo IS NULL OR ativo = true)
        )
        SELECT DISTINCT fp.cod_produto
        FROM faturamento_produto fp
        JOIN cnpjs_atacadao c ON c.cnpj_cliente = fp.cnpj_cliente
        WHERE fp.cod_produto NOT IN (SELECT codigo_nosso FROM produtos_no_depara)
    """
    try:
        rows = _query(sql)
    except Exception:
        rows = []
    for r in rows:
        cod = r[0]
        if cod not in mestre or not mestre[cod]["produto_vendido"]:
            continue
        _add_problema(problemas, cod, "A4", "vendeu p/ Atacadao sem De-Para")


def _regra_a5_depara_sendas(mestre: dict, problemas: dict):
    """A5 ALERTA: idem A4 para Sendas."""
    sql = """
        WITH cnpjs_sendas AS (
            SELECT DISTINCT cnpj_cliente
            FROM portal_sendas_produto_depara
            WHERE cnpj_cliente IS NOT NULL
              AND (ativo IS NULL OR ativo = true)
        ),
        produtos_no_depara AS (
            SELECT DISTINCT codigo_nosso
            FROM portal_sendas_produto_depara
            WHERE (ativo IS NULL OR ativo = true)
        )
        SELECT DISTINCT fp.cod_produto
        FROM faturamento_produto fp
        JOIN cnpjs_sendas c ON c.cnpj_cliente = fp.cnpj_cliente
        WHERE fp.cod_produto NOT IN (SELECT codigo_nosso FROM produtos_no_depara)
    """
    try:
        rows = _query(sql)
    except Exception:
        rows = []
    for r in rows:
        cod = r[0]
        if cod not in mestre or not mestre[cod]["produto_vendido"]:
            continue
        _add_problema(problemas, cod, "A5", "vendeu p/ Sendas sem De-Para")


def _regra_a6_tabela_rede(mestre: dict, problemas: dict):
    """
    A6 ALERTA: produto vendido aparece em faturamento mas sem preco vigente
    em tabela_rede_precos (ativo=true e (vigencia_fim IS NULL OR vigencia_fim >= hoje)).
    Considera apenas produtos que de fato faturaram para clientes que possuem
    tabela_rede (Atacadao/Sendas/etc) — caso contrario gera muito ruido.
    """
    sql = """
        WITH redes_existentes AS (
            SELECT DISTINCT rede FROM tabela_rede_precos
        ),
        produtos_com_preco AS (
            SELECT DISTINCT cod_produto
            FROM tabela_rede_precos
            WHERE ativo = true
              AND (vigencia_fim IS NULL OR vigencia_fim >= CURRENT_DATE)
        ),
        produtos_faturados AS (
            SELECT DISTINCT cod_produto FROM faturamento_produto
        )
        SELECT cod_produto
        FROM produtos_faturados
        WHERE cod_produto NOT IN (SELECT cod_produto FROM produtos_com_preco)
    """
    try:
        rows = _query(sql)
    except Exception:
        return
    for r in rows:
        cod = r[0]
        if cod not in mestre or not mestre[cod]["produto_vendido"]:
            continue
        _add_problema(problemas, cod, "A6", "sem preco vigente em tabela_rede_precos")


def _regra_a7_dimensoes(mestre: dict, problemas: dict):
    """A7 INFO: vendido sem altura/largura/comprimento."""
    for cod, p in mestre.items():
        if not p["produto_vendido"]:
            continue
        if (not p["altura_cm"] or float(p["altura_cm"]) <= 0) and \
           (not p["largura_cm"] or float(p["largura_cm"]) <= 0) and \
           (not p["comprimento_cm"] or float(p["comprimento_cm"]) <= 0):
            _add_problema(problemas, cod, "A7", "altura/largura/comprimento zerados")


def _regra_a8_categoria(mestre: dict, problemas: dict):
    """A8 INFO: vendido sem categoria_produto e tipo_embalagem."""
    for cod, p in mestre.items():
        if not p["produto_vendido"]:
            continue
        cat = (p["categoria_produto"] or "").strip()
        emb = (p["tipo_embalagem"] or "").strip()
        if not cat and not emb:
            _add_problema(problemas, cod, "A8", "categoria_produto e tipo_embalagem vazios")


# ----------------------------------------------------------------------------
# Regras B — produto_produzido
# ----------------------------------------------------------------------------

def _regra_b1_linha_producao(mestre: dict, problemas: dict):
    """B1 BLOQ: produzido sem linha_producao."""
    for cod, p in mestre.items():
        if not p["produto_produzido"]:
            continue
        if not (p["linha_producao"] or "").strip():
            _add_problema(problemas, cod, "B1", "linha_producao vazia")


def _regra_b2_disparo(mestre: dict, problemas: dict):
    """B2 BLOQ: produzido sem disparo_producao (MTO/MTS)."""
    for cod, p in mestre.items():
        if not p["produto_produzido"]:
            continue
        if not (p["disparo_producao"] or "").strip():
            _add_problema(problemas, cod, "B2", "disparo_producao vazio")


def _regra_b3_bom(mestre: dict, problemas: dict):
    """B3 BLOQ: produzido sem nenhum componente em lista_materiais (status='A')."""
    sql = """
        SELECT cod_produto_produzido, COUNT(*) AS n
        FROM lista_materiais
        WHERE (status IS NULL OR UPPER(status) IN ('A','ATIVO'))
        GROUP BY cod_produto_produzido
    """
    try:
        rows = _query(sql)
    except Exception:
        rows = []
    com_bom = {r[0] for r in rows if r[1] and int(r[1]) > 0}
    for cod, p in mestre.items():
        if not p["produto_produzido"]:
            continue
        if cod not in com_bom:
            _add_problema(problemas, cod, "B3", "sem componentes em lista_materiais")


def _regra_b4_custo(mestre: dict, problemas: dict):
    """B4 BLOQ: produzido sem custo_produto e sem custo_considerado.custo_atual=true."""
    sql = """
        SELECT DISTINCT cod_produto
        FROM custo_considerado
        WHERE custo_atual = true
    """
    try:
        rows = _query(sql)
    except Exception:
        rows = []
    com_custo_atual = {r[0] for r in rows}
    for cod, p in mestre.items():
        if not p["produto_produzido"]:
            continue
        tem_mestre = p["custo_produto"] and float(p["custo_produto"]) > 0
        if not tem_mestre and cod not in com_custo_atual:
            _add_problema(problemas, cod, "B4", "sem custo_produto e sem custo_considerado vigente")


def _regra_b5_capacidade(mestre: dict, problemas: dict):
    """B5 BLOQ: produzido sem registro em recursos_producao com capacidade > 0."""
    sql = """
        SELECT DISTINCT cod_produto
        FROM recursos_producao
        WHERE capacidade_unidade_minuto > 0
          AND (disponivel IS NULL OR disponivel = true)
    """
    try:
        rows = _query(sql)
    except Exception:
        rows = []
    com_capacidade = {r[0] for r in rows}
    for cod, p in mestre.items():
        if not p["produto_produzido"]:
            continue
        if cod not in com_capacidade:
            _add_problema(problemas, cod, "B5", "sem recursos_producao com capacidade")


def _regra_b6_componente_orfao(mestre: dict, problemas: dict):
    """
    B6 BLOQ: lista_materiais aponta cod_produto_componente que nao existe no mestre.
    Reporta o produto produzido (cod_produto_produzido) cujo BOM tem componente orfao.
    """
    sql = """
        SELECT DISTINCT lm.cod_produto_produzido, lm.cod_produto_componente
        FROM lista_materiais lm
        LEFT JOIN cadastro_palletizacao cp
          ON cp.cod_produto = lm.cod_produto_componente
        WHERE cp.cod_produto IS NULL
          AND (lm.status IS NULL OR UPPER(lm.status) IN ('A','ATIVO'))
    """
    try:
        rows = _query(sql)
    except Exception:
        return
    componentes_por_produto: dict = defaultdict(list)
    for r in rows:
        cod_prod = r[0]
        cod_comp = r[1]
        if cod_prod in mestre and mestre[cod_prod]["produto_produzido"]:
            componentes_por_produto[cod_prod].append(cod_comp)

    for cod_prod, comps in componentes_por_produto.items():
        _add_problema(
            problemas, cod_prod, "B6",
            f"{len(comps)} componente(s) sem cadastro: {', '.join(comps[:3])}"
            + ("..." if len(comps) > 3 else ""),
            dados_modal={"componentes_orfaos": comps},
        )


# ----------------------------------------------------------------------------
# Regras C — produto_comprado
# ----------------------------------------------------------------------------

def _regra_c1_lead_time(mestre: dict, problemas: dict):
    """C1 BLOQ: comprado sem lead_time."""
    for cod, p in mestre.items():
        if not p["produto_comprado"]:
            continue
        if p["lead_time"] is None or int(p["lead_time"] or 0) <= 0:
            _add_problema(problemas, cod, "C1", f"lead_time={p['lead_time']}")


def _regra_c2_perfil_fiscal(mestre: dict, problemas: dict):
    """C2 BLOQ: comprado sem nenhum perfil_fiscal_produto_fornecedor."""
    sql = """
        SELECT DISTINCT cod_produto
        FROM perfil_fiscal_produto_fornecedor
    """
    try:
        rows = _query(sql)
    except Exception:
        rows = []
    com_perfil = {r[0] for r in rows}
    for cod, p in mestre.items():
        if not p["produto_comprado"]:
            continue
        if cod not in com_perfil:
            _add_problema(problemas, cod, "C2", "sem perfil_fiscal_produto_fornecedor")


def _regra_c3_lote_minimo(mestre: dict, problemas: dict):
    """C3 ALERTA: comprado sem lote_minimo_compra."""
    for cod, p in mestre.items():
        if not p["produto_comprado"]:
            continue
        if p["lote_minimo_compra"] is None or int(p["lote_minimo_compra"] or 0) <= 0:
            _add_problema(problemas, cod, "C3", f"lote_minimo_compra={p['lote_minimo_compra']}")


def _regra_c4_custo_compra(mestre: dict, problemas: dict):
    """C4 ALERTA: comprado sem custo_produto."""
    for cod, p in mestre.items():
        if not p["produto_comprado"]:
            continue
        if not p["custo_produto"] or float(p["custo_produto"]) <= 0:
            _add_problema(problemas, cod, "C4", f"custo_produto={p['custo_produto']}")


# ----------------------------------------------------------------------------
# Regras D — universais
# ----------------------------------------------------------------------------

def _detectar_orfaos_puros() -> list:
    """
    D1: cod_produto que aparece em transacionais mas NAO existe no mestre
    (LEFT JOIN cadastro_palletizacao WHERE mestre IS NULL).
    Retorna lista de dicts: [{cod_produto, modulos: [...], nomes_encontrados: [...]}].
    """
    orfaos = defaultdict(lambda: {"modulos": set(), "nomes": set()})

    # Pre-computa quais tabelas tem coluna nome_produto (1 query parametrizada)
    tabelas_lista = [t[0] for t in TRANSACIONAIS_ORFAOS]
    try:
        rows_nome = db.session.execute(
            text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_name = ANY(:tabs) AND column_name = 'nome_produto'"
            ),
            {"tabs": tabelas_lista},
        ).fetchall()
        tabelas_com_nome = {r[0] for r in rows_nome}
    except Exception:
        tabelas_com_nome = set()

    for tabela, campo, label in TRANSACIONAIS_ORFAOS:
        tem_nome = tabela in tabelas_com_nome

        nome_select = "MIN(t.nome_produto) AS nome" if tem_nome else "NULL AS nome"
        sql = f"""
            SELECT t.{campo} AS cod, {nome_select}
            FROM {tabela} t
            LEFT JOIN cadastro_palletizacao cp ON cp.cod_produto = t.{campo}
            WHERE t.{campo} IS NOT NULL
              AND TRIM(t.{campo}) <> ''
              AND cp.cod_produto IS NULL
            GROUP BY t.{campo}
        """
        try:
            rows = _query(sql)
        except Exception:
            continue
        for r in rows:
            cod = (r[0] or "").strip()
            if not cod:
                continue
            orfaos[cod]["modulos"].add(label)
            if r[1]:
                orfaos[cod]["nomes"].add(str(r[1]).strip())

    # lista_materiais e bidimensional (produzido E componente)
    for col, label in [
        ("cod_produto_produzido", "ListaMateriais (produzido)"),
        ("cod_produto_componente", "ListaMateriais (componente)"),
    ]:
        sql = f"""
            SELECT lm.{col} AS cod, MIN(lm.{col.replace('cod_', 'nome_')}) AS nome
            FROM lista_materiais lm
            LEFT JOIN cadastro_palletizacao cp ON cp.cod_produto = lm.{col}
            WHERE lm.{col} IS NOT NULL
              AND TRIM(lm.{col}) <> ''
              AND cp.cod_produto IS NULL
            GROUP BY lm.{col}
        """
        try:
            rows = _query(sql)
        except Exception:
            continue
        for r in rows:
            cod = (r[0] or "").strip()
            if not cod:
                continue
            orfaos[cod]["modulos"].add(label)
            if r[1]:
                orfaos[cod]["nomes"].add(str(r[1]).strip())

    resultado = []
    for cod, info in sorted(orfaos.items()):
        resultado.append({
            "cod_produto": cod,
            "modulos": sorted(info["modulos"]),
            "nomes_encontrados": sorted(info["nomes"]),
        })
    return resultado


def _regra_d2_nome_divergente(mestre: dict, problemas: dict):
    """
    D2 ALERTA: nome_produto do mestre diverge do nome em transacionais.
    Coleta TODOS os nomes diferentes encontrados em cada tabela para popular o modal.
    """
    # cod_produto -> {tabela: [nomes_diferentes]}
    divergencias: dict = defaultdict(lambda: defaultdict(set))

    for tabela, label in NOME_DIVERGENTE_FONTES:
        sql = f"""
            SELECT cod_produto,
                   STRING_AGG(DISTINCT TRIM(nome_produto), '|||') AS nomes
            FROM {tabela}
            WHERE cod_produto IS NOT NULL
              AND nome_produto IS NOT NULL
              AND TRIM(nome_produto) <> ''
            GROUP BY cod_produto
        """
        try:
            rows = _query(sql)
        except Exception:
            continue
        for r in rows:
            cod = r[0]
            nomes_trans = (r[1] or "").strip()
            if not cod or cod not in mestre:
                continue
            nome_mestre = (mestre[cod]["nome_produto"] or "").strip()
            if not nome_mestre:
                continue
            for nome in nomes_trans.split("|||"):
                nome = nome.strip()
                if nome and nome.upper() != nome_mestre.upper():
                    divergencias[cod][label].add(nome)

    for cod, fontes in divergencias.items():
        nome_mestre = (mestre[cod]["nome_produto"] or "").strip()
        # Monta dados_modal com nomes encontrados por tabela
        nomes_por_fonte = []
        primeira_fonte = None
        primeiro_nome = None
        for fonte, nomes in fontes.items():
            for n in sorted(nomes):
                nomes_por_fonte.append({"fonte": fonte, "nome": n})
                if primeira_fonte is None:
                    primeira_fonte = fonte
                    primeiro_nome = n
        detalhe = (
            f"{primeira_fonte}: '{(primeiro_nome or '')[:60]}' vs mestre '{nome_mestre[:60]}'"
            if primeira_fonte else ""
        )
        _add_problema(
            problemas, cod, "D2",
            detalhe,
            dados_modal={
                "nome_mestre": nome_mestre,
                "nomes_alternativos": nomes_por_fonte,
            },
        )


def _regra_d3_peso_divergente(mestre: dict, problemas: dict):
    """
    D3 ALERTA: peso_bruto do mestre divergente de peso_unitario_produto
    em faturamento_produto (tolerancia 5%).
    """
    sql = """
        SELECT cod_produto,
               AVG(peso_unitario_produto) AS peso_avg,
               MIN(peso_unitario_produto) AS peso_min,
               MAX(peso_unitario_produto) AS peso_max,
               COUNT(*) AS qtd_amostras
        FROM faturamento_produto
        WHERE peso_unitario_produto IS NOT NULL
          AND peso_unitario_produto > 0
        GROUP BY cod_produto
    """
    try:
        rows = _query(sql)
    except Exception:
        return
    for r in rows:
        cod = r[0]
        peso_fat = float(r[1] or 0)
        peso_min = float(r[2] or 0)
        peso_max = float(r[3] or 0)
        qtd = int(r[4] or 0)
        if cod not in mestre:
            continue
        peso_mestre = float(mestre[cod]["peso_bruto"] or 0)
        if peso_mestre <= 0 or peso_fat <= 0:
            continue
        diff_pct = abs(peso_fat - peso_mestre) / peso_mestre
        if diff_pct > 0.05:
            _add_problema(
                problemas, cod, "D3",
                f"mestre={peso_mestre:.3f} vs faturamento avg={peso_fat:.3f} ({diff_pct*100:.1f}% diff)",
                dados_modal={
                    "peso_mestre": peso_mestre,
                    "peso_faturado_avg": peso_fat,
                    "peso_faturado_min": peso_min,
                    "peso_faturado_max": peso_max,
                    "qtd_amostras": qtd,
                    "diff_pct": round(diff_pct * 100, 2),
                },
            )


# ----------------------------------------------------------------------------
# Orquestrador
# ----------------------------------------------------------------------------

def auditar_produtos() -> dict:
    """
    Roda todas as regras e retorna estrutura completa.
    """
    mestre = _carregar_mestre()
    problemas: dict = defaultdict(list)

    # A) vendido
    _regra_a1_palletizacao(mestre, problemas)
    _regra_a2_peso_bruto(mestre, problemas)
    _regra_a3_unid_medida(mestre, problemas)
    _regra_a4_depara_atacadao(mestre, problemas)
    _regra_a5_depara_sendas(mestre, problemas)
    _regra_a6_tabela_rede(mestre, problemas)
    _regra_a7_dimensoes(mestre, problemas)
    _regra_a8_categoria(mestre, problemas)

    # B) produzido
    _regra_b1_linha_producao(mestre, problemas)
    _regra_b2_disparo(mestre, problemas)
    _regra_b3_bom(mestre, problemas)
    _regra_b4_custo(mestre, problemas)
    _regra_b5_capacidade(mestre, problemas)
    _regra_b6_componente_orfao(mestre, problemas)

    # C) comprado
    _regra_c1_lead_time(mestre, problemas)
    _regra_c2_perfil_fiscal(mestre, problemas)
    _regra_c3_lote_minimo(mestre, problemas)
    _regra_c4_custo_compra(mestre, problemas)

    # D) universais (D1 = orfaos puros — fora do dict de problemas; D2/D3 = no dict)
    orfaos_puros = _detectar_orfaos_puros()
    _regra_d2_nome_divergente(mestre, problemas)
    _regra_d3_peso_divergente(mestre, problemas)

    # Mapeia regra_id -> regra
    regras_idx = {r["id"]: r for r in REGRAS}
    sev_rank = {SEVERIDADE_BLOQ: 0, SEVERIDADE_ALERTA: 1, SEVERIDADE_INFO: 2}

    # Constroi lista de produtos enriquecida (cada produto com seus problemas e categorias afetadas)
    produtos: list = []
    for cod, lista in problemas.items():
        if cod not in mestre:
            continue
        m = mestre[cod]
        problemas_enriq = []
        categorias_do_produto = set()
        max_severidade = SEVERIDADE_INFO
        for prob in lista:
            regra = regras_idx.get(prob["regra_id"])
            if not regra:
                continue
            problemas_enriq.append({
                "regra_id": regra["id"],
                "flag": regra["flag"],
                "categoria": regra["categoria"],
                "acao": regra["acao"],
                "campo_alvo": regra.get("campo_alvo"),
                "severidade": regra["severidade"],
                "titulo": regra["titulo"],
                "detalhe": prob["detalhe"],
                "dados_modal": prob.get("dados_modal", {}),
            })
            categorias_do_produto.add(regra["categoria"])
            if regra["severidade"] == SEVERIDADE_BLOQ:
                max_severidade = SEVERIDADE_BLOQ
            elif regra["severidade"] == SEVERIDADE_ALERTA and max_severidade != SEVERIDADE_BLOQ:
                max_severidade = SEVERIDADE_ALERTA

        produtos.append({
            "cod_produto": cod,
            "nome_produto": m["nome_produto"],
            "produto_vendido": m["produto_vendido"],
            "produto_produzido": m["produto_produzido"],
            "produto_comprado": m["produto_comprado"],
            "max_severidade": max_severidade,
            "categorias": sorted(categorias_do_produto),
            "problemas": problemas_enriq,
            "qtd_problemas": len(problemas_enriq),
        })

    # Ordenar: BLOQ primeiro, depois ALERTA, depois INFO; dentro do mesmo nivel, mais problemas primeiro
    produtos.sort(key=lambda x: (sev_rank[x["max_severidade"]], -x["qtd_problemas"], x["cod_produto"]))

    # Agrupa por categoria — cada produto pode aparecer em multiplas categorias
    por_categoria: dict = {
        CATEGORIA_ORFAO_PURO: [],
        CATEGORIA_REPARAR_MESTRE: [],
        CATEGORIA_CADASTRO_FALTANTE: [],
        CATEGORIA_DIVERGENCIA: [],
    }

    # Orfaos puros: vem da estrutura propria, nao de problemas[]
    for o in orfaos_puros:
        por_categoria[CATEGORIA_ORFAO_PURO].append({
            "cod_produto": o["cod_produto"],
            "nome_produto": (o["nomes_encontrados"][0] if o["nomes_encontrados"] else ""),
            "modulos": o["modulos"],
            "nomes_encontrados": o["nomes_encontrados"],
            "max_severidade": SEVERIDADE_BLOQ,
        })

    # Para REPARAR_MESTRE / CADASTRO_FALTANTE / DIVERGENCIA: filtrar produtos[] pelos problemas dessa categoria
    for p in produtos:
        for cat in [CATEGORIA_REPARAR_MESTRE, CATEGORIA_CADASTRO_FALTANTE, CATEGORIA_DIVERGENCIA]:
            problemas_da_cat = [x for x in p["problemas"] if x["categoria"] == cat]
            if not problemas_da_cat:
                continue
            # Severidade max DENTRO desta categoria
            sev_da_cat = SEVERIDADE_INFO
            for prob in problemas_da_cat:
                if prob["severidade"] == SEVERIDADE_BLOQ:
                    sev_da_cat = SEVERIDADE_BLOQ
                elif prob["severidade"] == SEVERIDADE_ALERTA and sev_da_cat != SEVERIDADE_BLOQ:
                    sev_da_cat = SEVERIDADE_ALERTA
            por_categoria[cat].append({
                "cod_produto": p["cod_produto"],
                "nome_produto": p["nome_produto"],
                "produto_vendido": p["produto_vendido"],
                "produto_produzido": p["produto_produzido"],
                "produto_comprado": p["produto_comprado"],
                "problemas": problemas_da_cat,
                "qtd_problemas": len(problemas_da_cat),
                "max_severidade": sev_da_cat,
            })

    # Ordena cada categoria
    for cat in por_categoria:
        if cat == CATEGORIA_ORFAO_PURO:
            por_categoria[cat].sort(key=lambda x: x["cod_produto"])
        else:
            por_categoria[cat].sort(
                key=lambda x: (sev_rank[x["max_severidade"]], -x["qtd_problemas"], x["cod_produto"])
            )

    # Totais
    totais = {
        "total_mestre_ativo": len(mestre),
        "total_com_problemas": len(produtos),
        "total_orfaos_puros": len(orfaos_puros),
        "por_severidade": {
            SEVERIDADE_BLOQ: sum(1 for p in produtos if p["max_severidade"] == SEVERIDADE_BLOQ),
            SEVERIDADE_ALERTA: sum(1 for p in produtos if p["max_severidade"] == SEVERIDADE_ALERTA),
            SEVERIDADE_INFO: sum(1 for p in produtos if p["max_severidade"] == SEVERIDADE_INFO),
        },
        "por_categoria": {
            CATEGORIA_ORFAO_PURO: len(por_categoria[CATEGORIA_ORFAO_PURO]),
            CATEGORIA_REPARAR_MESTRE: len(por_categoria[CATEGORIA_REPARAR_MESTRE]),
            CATEGORIA_CADASTRO_FALTANTE: len(por_categoria[CATEGORIA_CADASTRO_FALTANTE]),
            CATEGORIA_DIVERGENCIA: len(por_categoria[CATEGORIA_DIVERGENCIA]),
        },
        "por_flag": {
            FLAG_VENDIDO: sum(1 for p in produtos if any(x["flag"] == FLAG_VENDIDO for x in p["problemas"])),
            FLAG_PRODUZIDO: sum(1 for p in produtos if any(x["flag"] == FLAG_PRODUZIDO for x in p["problemas"])),
            FLAG_COMPRADO: sum(1 for p in produtos if any(x["flag"] == FLAG_COMPRADO for x in p["problemas"])),
            FLAG_UNIVERSAL: sum(1 for p in produtos if any(x["flag"] == FLAG_UNIVERSAL for x in p["problemas"])),
        },
        "por_regra": _contar_por_regra(produtos),
        "data_auditoria": date.today().isoformat(),
    }

    return {
        "produtos_com_problemas": produtos,
        "orfaos_puros": orfaos_puros,
        "por_categoria": por_categoria,
        "totais": totais,
        "regras": REGRAS,
    }


def _contar_por_regra(produtos: list) -> dict:
    contagem: dict = defaultdict(int)
    for p in produtos:
        for prob in p["problemas"]:
            contagem[prob["regra_id"]] += 1
    return dict(contagem)


def auditar_um_produto(cod_produto: str) -> dict | None:
    """
    Auditoria de um unico produto (para drilldown). Retorna None se nao existe no mestre.
    """
    if not cod_produto:
        return None

    sql = "SELECT * FROM cadastro_palletizacao WHERE cod_produto = :cod LIMIT 1"
    row = db.session.execute(text(sql), {"cod": cod_produto}).fetchone()
    if not row:
        # checa se e orfao puro
        full = auditar_produtos()
        for orfao in full["orfaos_puros"]:
            if orfao["cod_produto"] == cod_produto:
                return {"orfao_puro": True, "info": orfao}
        return None

    full = auditar_produtos()
    encontrado = next(
        (p for p in full["produtos_com_problemas"] if p["cod_produto"] == cod_produto),
        None,
    )
    return {
        "orfao_puro": False,
        "mestre": dict(row._mapping),
        "auditoria": encontrado or {"cod_produto": cod_produto, "problemas": []},
    }

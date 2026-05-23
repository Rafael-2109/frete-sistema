"""
Auditor de Produtos (CADASTROS MORTAIS).

Roda todas as regras da matriz_obrigatoriedade e retorna estrutura agregada
por produto, alem de orfaos puros (cod_produto em transacional sem mestre).

Performance: cada regra e 1 query agregada (nao itera produto a produto).

Versao 2 (26/05/2026): 14 regras (M1-M4, V1-V3, P1-P4, C1-C3).
Removidas regras obsoletas (A3-A8 antigas, B2, B4-mestre, C2-perfil_fiscal,
C4-custo_mestre, D2-nome, D3-peso).
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
)


# Tabelas transacionais que possuem cod_produto e devem ser cruzadas com o mestre
# (para detecao de orfaos puros — M1).
#
# FOCO: produtos que precisam de cadastro mestre (BOM, producao, faturamento).
# CarteiraPrincipal e a fonte PREFERENCIAL — pedido nasce na carteira antes de
# virar separacao, entao um produto novo aparece la primeiro.
#
# Tabelas DELIBERADAMENTE EXCLUIDAS (geravam ~94% de falsos positivos):
#   - pedido_compras / historico_pedido_compras: uso e consumo (etiquetas,
#     embalagens, etc.) que nao precisam de cadastro no mestre.
#   - perfil_fiscal_produto_fornecedor: 2.831 entradas de uso e consumo
#     cadastradas so para fins fiscais.
#   - fila_agendamento_sendas: cod_produto la pode ser codigo do CLIENTE.
TRANSACIONAIS_ORFAOS = [
    ("separacao", "cod_produto", "Separacao"),
    ("movimentacao_estoque", "cod_produto", "MovimentacaoEstoque"),
    ("carteira_principal", "cod_produto", "CarteiraPrincipal"),
    ("carteira_copia", "cod_produto", "CarteiraCopia"),
    ("faturamento_produto", "cod_produto", "FaturamentoProduto"),
    ("programacao_producao", "cod_produto", "ProgramacaoProducao"),
    ("recursos_producao", "cod_produto", "RecursosProducao"),
    ("custo_considerado", "cod_produto", "CustoConsiderado"),
    ("nf_pendente_tagplus", "cod_produto", "NFPendenteTagPlus"),
]

# Filtros adicionais por tabela (WHERE extra aplicado na deteccao de orfaos).
# Mantem o cruzamento da tabela mas exclui linhas que sabidamente NAO sao
# produtos do mestre (ex: motos Assai/B2B Q.P.A. usam codigos como
# DOT/SOL/X11_MINI em separacao com chassi_assai preenchido — dominio separado).
FILTROS_ORFAOS_EXTRA = {
    "separacao": "(t.chassi_assai IS NULL OR TRIM(t.chassi_assai) = '')",
}


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


def _is_vazio(valor) -> bool:
    """True se valor e None, string vazia ou apenas espacos."""
    if valor is None:
        return True
    return not str(valor).strip()


# ----------------------------------------------------------------------------
# Carregamento do mestre
# ----------------------------------------------------------------------------

def _carregar_mestre() -> dict:
    """Carrega cadastro_palletizacao.ativo=true em dict cod_produto -> dict."""
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
# Regras M — UNIVERSAIS (todo produto, independente das flags)
# ----------------------------------------------------------------------------

def _regra_m2_categoria(mestre: dict, problemas: dict):
    """M2 BLOQ: categoria_produto vazio."""
    for cod, p in mestre.items():
        if _is_vazio(p["categoria_produto"]):
            _add_problema(problemas, cod, "M2", "categoria_produto vazio")


def _regra_m3_materia_prima(mestre: dict, problemas: dict):
    """M3 BLOQ: tipo_materia_prima vazio."""
    for cod, p in mestre.items():
        if _is_vazio(p["tipo_materia_prima"]):
            _add_problema(problemas, cod, "M3", "tipo_materia_prima vazio")


def _regra_m4_embalagem(mestre: dict, problemas: dict):
    """M4 BLOQ: tipo_embalagem vazio."""
    for cod, p in mestre.items():
        if _is_vazio(p["tipo_embalagem"]):
            _add_problema(problemas, cod, "M4", "tipo_embalagem vazio")


# ----------------------------------------------------------------------------
# Regras V — VENDIDO
# ----------------------------------------------------------------------------

def _regra_v1_palletizacao(mestre: dict, problemas: dict):
    """V1 BLOQ: vendido com palletizacao <= 0 ou nula."""
    for cod, p in mestre.items():
        if not p["produto_vendido"]:
            continue
        if not p["palletizacao"] or float(p["palletizacao"]) <= 0:
            _add_problema(problemas, cod, "V1", f"palletizacao={p['palletizacao']}")


def _regra_v2_peso_bruto(mestre: dict, problemas: dict):
    """V2 BLOQ: vendido com peso_bruto <= 0 ou nulo."""
    for cod, p in mestre.items():
        if not p["produto_vendido"]:
            continue
        if not p["peso_bruto"] or float(p["peso_bruto"]) <= 0:
            _add_problema(problemas, cod, "V2", f"peso_bruto={p['peso_bruto']}")


def _regra_v3_dimensoes(mestre: dict, problemas: dict):
    """V3 BLOQ: vendido sem altura/largura/comprimento (todas zeradas/nulas)."""
    for cod, p in mestre.items():
        if not p["produto_vendido"]:
            continue
        alt = float(p["altura_cm"] or 0)
        larg = float(p["largura_cm"] or 0)
        comp = float(p["comprimento_cm"] or 0)
        if alt <= 0 and larg <= 0 and comp <= 0:
            _add_problema(problemas, cod, "V3", "altura, largura e comprimento zerados")


# ----------------------------------------------------------------------------
# Regras P — PRODUZIDO
# ----------------------------------------------------------------------------

def _regra_p1_linha_producao(mestre: dict, problemas: dict):
    """P1 BLOQ: produzido sem linha_producao."""
    for cod, p in mestre.items():
        if not p["produto_produzido"]:
            continue
        if _is_vazio(p["linha_producao"]):
            _add_problema(problemas, cod, "P1", "linha_producao vazia")


def _regra_p2_bom(mestre: dict, problemas: dict):
    """P2 BLOQ: produzido sem nenhum componente em lista_materiais (status='A')."""
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
            _add_problema(problemas, cod, "P2", "sem componentes em lista_materiais")


def _regra_p3_capacidade(mestre: dict, problemas: dict):
    """P3 BLOQ: PRODUZIDO + VENDIDO (acabado) sem recurso/capacidade."""
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
        if not (p["produto_produzido"] and p["produto_vendido"]):
            continue
        if cod not in com_capacidade:
            _add_problema(problemas, cod, "P3", "sem recursos_producao com capacidade")


def _regra_p4_componente_orfao(mestre: dict, problemas: dict):
    """
    P4 BLOQ: lista_materiais aponta cod_produto_componente que nao existe no mestre.
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
            problemas, cod_prod, "P4",
            f"{len(comps)} componente(s) sem cadastro: {', '.join(comps[:3])}"
            + ("..." if len(comps) > 3 else ""),
            dados_modal={"componentes_orfaos": comps},
        )


# ----------------------------------------------------------------------------
# Regras C — COMPRADO
# ----------------------------------------------------------------------------

def _regra_c1_lead_time(mestre: dict, problemas: dict):
    """C1 BLOQ: comprado sem lead_time."""
    for cod, p in mestre.items():
        if not p["produto_comprado"]:
            continue
        if p["lead_time"] is None or int(p["lead_time"] or 0) <= 0:
            _add_problema(problemas, cod, "C1", f"lead_time={p['lead_time']}")


def _regra_c2_lote_minimo(mestre: dict, problemas: dict):
    """C2 BLOQ: comprado sem lote_minimo_compra."""
    for cod, p in mestre.items():
        if not p["produto_comprado"]:
            continue
        if p["lote_minimo_compra"] is None or int(p["lote_minimo_compra"] or 0) <= 0:
            _add_problema(problemas, cod, "C2", f"lote_minimo_compra={p['lote_minimo_compra']}")


def _regra_c3_custo_considerado(mestre: dict, problemas: dict):
    """
    C3 BLOQ: comprado sem registro em custo_considerado.custo_atual=true.
    Produtos PRODUZIDOS recebem custo via BOM (tela /custeio/definicao) — nao
    se aplica essa regra para eles.
    """
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
        if not p["produto_comprado"]:
            continue
        if cod not in com_custo_atual:
            _add_problema(problemas, cod, "C3", "sem custo_considerado.custo_atual=true")


# ----------------------------------------------------------------------------
# M1 — orfaos puros (sem mestre)
# ----------------------------------------------------------------------------

def _detectar_orfaos_puros() -> list:
    """
    M1: cod_produto que aparece em transacionais mas NAO existe no mestre
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
        filtro_extra = FILTROS_ORFAOS_EXTRA.get(tabela)
        where_extra = f"AND {filtro_extra}" if filtro_extra else ""
        sql = f"""
            SELECT t.{campo} AS cod, {nome_select}
            FROM {tabela} t
            LEFT JOIN cadastro_palletizacao cp ON cp.cod_produto = t.{campo}
            WHERE t.{campo} IS NOT NULL
              AND TRIM(t.{campo}) <> ''
              AND cp.cod_produto IS NULL
              {where_extra}
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

    # lista_materiais e bidimensional (produzido E componente) — P4 cobre o
    # caso do produzido, aqui marcamos o COMPONENTE orfao para aparecer na
    # categoria Orfao Puro com botao "Cadastrar mestre".
    for col, label in [
        ("cod_produto_componente", "ListaMateriais (componente)"),
    ]:
        sql = f"""
            SELECT lm.{col} AS cod, MIN(lm.{col.replace('cod_', 'nome_')}) AS nome
            FROM lista_materiais lm
            LEFT JOIN cadastro_palletizacao cp ON cp.cod_produto = lm.{col}
            WHERE lm.{col} IS NOT NULL
              AND TRIM(lm.{col}) <> ''
              AND cp.cod_produto IS NULL
              AND (lm.status IS NULL OR UPPER(lm.status) IN ('A','ATIVO'))
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


# ----------------------------------------------------------------------------
# Orquestrador
# ----------------------------------------------------------------------------

def auditar_produtos() -> dict:
    """Roda todas as regras e retorna estrutura completa."""
    mestre = _carregar_mestre()
    problemas: dict = defaultdict(list)

    # M) UNIVERSAIS (M1 vem em _detectar_orfaos_puros separadamente)
    _regra_m2_categoria(mestre, problemas)
    _regra_m3_materia_prima(mestre, problemas)
    _regra_m4_embalagem(mestre, problemas)

    # V) VENDIDO
    _regra_v1_palletizacao(mestre, problemas)
    _regra_v2_peso_bruto(mestre, problemas)
    _regra_v3_dimensoes(mestre, problemas)

    # P) PRODUZIDO
    _regra_p1_linha_producao(mestre, problemas)
    _regra_p2_bom(mestre, problemas)
    _regra_p3_capacidade(mestre, problemas)
    _regra_p4_componente_orfao(mestre, problemas)

    # C) COMPRADO
    _regra_c1_lead_time(mestre, problemas)
    _regra_c2_lote_minimo(mestre, problemas)
    _regra_c3_custo_considerado(mestre, problemas)

    # M1) Orfaos puros — fora do dict de problemas
    orfaos_puros = _detectar_orfaos_puros()

    # Mapeia regra_id -> regra
    regras_idx = {r["id"]: r for r in REGRAS}
    sev_rank = {SEVERIDADE_BLOQ: 0, SEVERIDADE_ALERTA: 1, SEVERIDADE_INFO: 2}

    # Constroi lista de produtos enriquecida
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

    # Ordenar: BLOQ primeiro, depois ALERTA, depois INFO; mais problemas primeiro
    produtos.sort(key=lambda x: (sev_rank[x["max_severidade"]], -x["qtd_problemas"], x["cod_produto"]))

    # Agrupa por categoria — cada produto pode aparecer em multiplas categorias
    por_categoria: dict = {
        CATEGORIA_ORFAO_PURO: [],
        CATEGORIA_REPARAR_MESTRE: [],
        CATEGORIA_CADASTRO_FALTANTE: [],
    }

    # Orfaos puros: vem da estrutura propria
    for o in orfaos_puros:
        por_categoria[CATEGORIA_ORFAO_PURO].append({
            "cod_produto": o["cod_produto"],
            "nome_produto": (o["nomes_encontrados"][0] if o["nomes_encontrados"] else ""),
            "modulos": o["modulos"],
            "nomes_encontrados": o["nomes_encontrados"],
            "max_severidade": SEVERIDADE_BLOQ,
        })

    # REPARAR_MESTRE / CADASTRO_FALTANTE: filtrar produtos[] pelos problemas dessa categoria
    for p in produtos:
        for cat in [CATEGORIA_REPARAR_MESTRE, CATEGORIA_CADASTRO_FALTANTE]:
            problemas_da_cat = [x for x in p["problemas"] if x["categoria"] == cat]
            if not problemas_da_cat:
                continue
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
    """Auditoria de um unico produto (drilldown). None se nao existe no mestre."""
    if not cod_produto:
        return None

    sql = "SELECT * FROM cadastro_palletizacao WHERE cod_produto = :cod LIMIT 1"
    row = db.session.execute(text(sql), {"cod": cod_produto}).fetchone()
    if not row:
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

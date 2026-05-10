"""
Rotas do modulo de Auditoria de Produtos.

Acesso: link a partir de /producao/palletizacao -> botao "Auditoria".

Rotas:
    GET  /produtos/auditoria                            tela principal
    GET  /produtos/auditoria/exportar                   download Excel
    GET  /produtos/api/produto/<cod>                    detalhes para modal
    POST /produtos/api/mestre                           cria registro no mestre (orfao puro)
    PUT  /produtos/api/mestre/<cod>                     atualiza mestre (Editar/Reparar)
    POST /produtos/api/bom-item                         cria item de BOM
    POST /produtos/api/recurso                          cria recurso de producao
    POST /produtos/api/perfil-fiscal                    cria perfil fiscal produto/fornecedor
    POST /produtos/api/sincronizar-nome/<cod>           atualiza nome_produto no mestre
    POST /produtos/api/atualizar-peso/<cod>             atualiza peso_bruto no mestre
"""

from io import BytesIO
from datetime import datetime, date

from flask import Blueprint, render_template, jsonify, make_response, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import text

from app import db
from app.produtos.services.auditor_produto import auditar_produtos
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
    CLASSE_BADGE,
    ICONE_CATEGORIA,
    ROTULO_CATEGORIA,
    DESCRICAO_CATEGORIA,
)
from app.utils.timezone import agora_utc_naive


produtos_bp = Blueprint("produtos", __name__, url_prefix="/produtos")


# ============================================================================
# TELA principal + EXPORTACAO
# ============================================================================

@produtos_bp.route("/auditoria")
@login_required
def auditoria():
    """Tela principal de auditoria — agrupa por 4 categorias de acao."""
    busca = request.args.get("busca", "").strip()

    try:
        resultado = auditar_produtos()
    except Exception as e:
        flash(f"Erro ao executar auditoria: {e}", "error")
        return redirect(url_for("producao.listar_palletizacao"))

    if busca:
        b = busca.upper()
        for cat, lista in resultado["por_categoria"].items():
            resultado["por_categoria"][cat] = [
                p for p in lista
                if b in (p.get("cod_produto") or "").upper()
                or b in (p.get("nome_produto") or "").upper()
            ]

    return render_template(
        "produtos/auditoria.html",
        por_categoria=resultado["por_categoria"],
        totais=resultado["totais"],
        regras=REGRAS,
        classe_badge=CLASSE_BADGE,
        icone_categoria=ICONE_CATEGORIA,
        rotulo_categoria=ROTULO_CATEGORIA,
        descricao_categoria=DESCRICAO_CATEGORIA,
        busca=busca,
        # constantes
        SEVERIDADE_BLOQ=SEVERIDADE_BLOQ,
        SEVERIDADE_ALERTA=SEVERIDADE_ALERTA,
        SEVERIDADE_INFO=SEVERIDADE_INFO,
        FLAG_VENDIDO=FLAG_VENDIDO,
        FLAG_PRODUZIDO=FLAG_PRODUZIDO,
        FLAG_COMPRADO=FLAG_COMPRADO,
        FLAG_UNIVERSAL=FLAG_UNIVERSAL,
        CAT_ORFAO=CATEGORIA_ORFAO_PURO,
        CAT_MESTRE=CATEGORIA_REPARAR_MESTRE,
        CAT_FALTANTE=CATEGORIA_CADASTRO_FALTANTE,
        CAT_DIV=CATEGORIA_DIVERGENCIA,
    )


@produtos_bp.route("/auditoria/exportar")
@login_required
def auditoria_exportar():
    """Exporta o resultado da auditoria em Excel."""
    try:
        import pandas as pd
        resultado = auditar_produtos()
    except Exception as e:
        flash(f"Erro ao gerar exportacao: {e}", "error")
        return redirect(url_for("produtos.auditoria"))

    pc = resultado["por_categoria"]
    totais = resultado["totais"]

    # Aba 0: Resumo
    df_resumo = pd.DataFrame([
        {"Metrica": "Produtos ativos no mestre", "Valor": totais["total_mestre_ativo"]},
        {"Metrica": "Produtos com problemas", "Valor": totais["total_com_problemas"]},
        {"Metrica": "Orfaos puros", "Valor": totais["total_orfaos_puros"]},
        {"Metrica": f"Reparar mestre", "Valor": totais["por_categoria"][CATEGORIA_REPARAR_MESTRE]},
        {"Metrica": f"Cadastros faltantes", "Valor": totais["por_categoria"][CATEGORIA_CADASTRO_FALTANTE]},
        {"Metrica": f"Divergencias", "Valor": totais["por_categoria"][CATEGORIA_DIVERGENCIA]},
        {"Metrica": "Data auditoria", "Valor": totais["data_auditoria"]},
    ])

    # Aba 1: Orfaos puros
    df_orfaos = pd.DataFrame([
        {
            "cod_produto": o["cod_produto"],
            "modulos": ", ".join(o["modulos"]),
            "nomes_encontrados": " | ".join(o["nomes_encontrados"]),
        }
        for o in pc[CATEGORIA_ORFAO_PURO]
    ]) if pc[CATEGORIA_ORFAO_PURO] else pd.DataFrame(
        columns=["cod_produto", "modulos", "nomes_encontrados"]
    )

    def _flatten(produtos: list) -> list:
        rows = []
        for p in produtos:
            for prob in p["problemas"]:
                rows.append({
                    "cod_produto": p["cod_produto"],
                    "nome_produto": p["nome_produto"],
                    "vendido": "S" if p["produto_vendido"] else "",
                    "produzido": "S" if p["produto_produzido"] else "",
                    "comprado": "S" if p["produto_comprado"] else "",
                    "regra_id": prob["regra_id"],
                    "severidade": prob["severidade"],
                    "campo_alvo": prob.get("campo_alvo") or "",
                    "titulo": prob["titulo"],
                    "detalhe": prob["detalhe"],
                })
        return rows

    df_mestre = pd.DataFrame(_flatten(pc[CATEGORIA_REPARAR_MESTRE]))
    df_faltante = pd.DataFrame(_flatten(pc[CATEGORIA_CADASTRO_FALTANTE]))
    df_divergencia = pd.DataFrame(_flatten(pc[CATEGORIA_DIVERGENCIA]))

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_resumo.to_excel(writer, sheet_name="Resumo", index=False)
        df_orfaos.to_excel(writer, sheet_name="Orfaos Puros", index=False)
        df_mestre.to_excel(writer, sheet_name="Reparar Mestre", index=False)
        df_faltante.to_excel(writer, sheet_name="Cadastros Faltantes", index=False)
        df_divergencia.to_excel(writer, sheet_name="Divergencias", index=False)

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    timestamp = agora_utc_naive().strftime("%Y%m%d_%H%M%S")
    response.headers["Content-Disposition"] = (
        f"attachment; filename=auditoria_produtos_{timestamp}.xlsx"
    )
    return response


# ============================================================================
# API: GET detalhes do produto
# ============================================================================

@produtos_bp.route("/api/produto/<path:cod_produto>")
@login_required
def api_produto_detalhes(cod_produto: str):
    """Retorna mestre + estatisticas de uso (para preencher modais)."""
    cod_produto = cod_produto.strip()
    if not cod_produto:
        return jsonify({"sucesso": False, "erro": "cod_produto vazio"}), 400

    sql_mestre = "SELECT * FROM cadastro_palletizacao WHERE cod_produto = :cod LIMIT 1"
    row = db.session.execute(text(sql_mestre), {"cod": cod_produto}).fetchone()
    mestre = dict(row._mapping) if row else None

    # Sanitiza dados nao-JSON-friendly
    def _serializar(d: dict) -> dict:
        out = {}
        for k, v in d.items():
            if isinstance(v, (datetime, date)):
                out[k] = v.isoformat()
            elif hasattr(v, "__float__") and not isinstance(v, (bool, int, float, str)):
                try:
                    out[k] = float(v)
                except Exception:
                    out[k] = str(v)
            else:
                out[k] = v
        return out

    if mestre:
        mestre = _serializar(mestre)

    # Contagens auxiliares
    extras: dict = {}
    try:
        extras["bom_componentes"] = db.session.execute(text(
            "SELECT COUNT(*) FROM lista_materiais WHERE cod_produto_produzido=:c"
        ), {"c": cod_produto}).scalar() or 0
        extras["recursos"] = db.session.execute(text(
            "SELECT COUNT(*) FROM recursos_producao WHERE cod_produto=:c"
        ), {"c": cod_produto}).scalar() or 0
        extras["perfis_fiscais"] = db.session.execute(text(
            "SELECT COUNT(*) FROM perfil_fiscal_produto_fornecedor WHERE cod_produto=:c"
        ), {"c": cod_produto}).scalar() or 0
        extras["depara_atacadao"] = db.session.execute(text(
            "SELECT COUNT(*) FROM portal_atacadao_produto_depara WHERE codigo_nosso=:c"
        ), {"c": cod_produto}).scalar() or 0
        extras["depara_sendas"] = db.session.execute(text(
            "SELECT COUNT(*) FROM portal_sendas_produto_depara WHERE codigo_nosso=:c"
        ), {"c": cod_produto}).scalar() or 0
        extras["precos_rede"] = db.session.execute(text(
            "SELECT COUNT(*) FROM tabela_rede_precos WHERE cod_produto=:c"
        ), {"c": cod_produto}).scalar() or 0
    except Exception:
        pass

    return jsonify({
        "sucesso": True,
        "cod_produto": cod_produto,
        "mestre": mestre,
        "extras": extras,
    })


# ============================================================================
# API WRITE: mestre (CREATE / UPDATE)
# ============================================================================

CAMPOS_MESTRE_EDITAVEIS = [
    "nome_produto",
    "codigo_ean",
    "palletizacao",
    "peso_bruto",
    "altura_cm",
    "largura_cm",
    "comprimento_cm",
    "tipo_embalagem",
    "tipo_materia_prima",
    "categoria_produto",
    "subcategoria",
    "linha_producao",
    "produto_comprado",
    "produto_produzido",
    "produto_vendido",
    "lead_time",
    "lote_minimo_compra",
    "disparo_producao",
    "custo_produto",
]


class _CoerceError(ValueError):
    """Erro de coercao — valor nao convertivel para o tipo esperado."""


def _coerce(campo: str, valor):
    """Converte string -> tipo apropriado para SQL.

    Retorna None apenas quando valor de entrada e None/'' (omitido).
    Levanta _CoerceError quando o valor existe mas nao pode ser convertido —
    evitando que valor invalido vire NULL silencioso no banco.
    """
    if valor is None or valor == "":
        return None
    if campo in ("palletizacao", "peso_bruto", "altura_cm", "largura_cm", "comprimento_cm", "custo_produto"):
        try:
            return float(valor)
        except Exception:
            raise _CoerceError(f"{campo} invalido: '{valor}' nao e numerico")
    if campo in ("lead_time", "lote_minimo_compra"):
        try:
            return int(valor)
        except Exception:
            raise _CoerceError(f"{campo} invalido: '{valor}' nao e inteiro")
    if campo in ("produto_comprado", "produto_produzido", "produto_vendido"):
        if isinstance(valor, bool):
            return valor
        return str(valor).strip().lower() in ("true", "1", "sim", "s", "yes")
    return str(valor).strip()


@produtos_bp.route("/api/mestre", methods=["POST"])
@login_required
def api_criar_mestre():
    """Cria novo registro em cadastro_palletizacao (resolve orfao puro)."""
    dados = request.get_json(silent=True) or {}
    cod = (dados.get("cod_produto") or "").strip()
    if not cod:
        return jsonify({"sucesso": False, "erro": "cod_produto obrigatorio"}), 400

    existe = db.session.execute(
        text("SELECT 1 FROM cadastro_palletizacao WHERE cod_produto=:c"), {"c": cod}
    ).fetchone()
    if existe:
        return jsonify({"sucesso": False, "erro": f"Produto {cod} ja existe"}), 409

    nome = (dados.get("nome_produto") or "").strip()
    try:
        pall = _coerce("palletizacao", dados.get("palletizacao"))
        peso = _coerce("peso_bruto", dados.get("peso_bruto"))
    except _CoerceError as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 400

    vendido = bool(_coerce("produto_vendido", dados.get("produto_vendido"))) if "produto_vendido" in dados else True

    if not nome:
        return jsonify({"sucesso": False, "erro": "nome_produto obrigatorio"}), 400
    if not isinstance(pall, (int, float)) or pall < 0:
        return jsonify({"sucesso": False, "erro": "palletizacao invalida (deve ser numerico >= 0)"}), 400
    if not isinstance(peso, (int, float)) or peso < 0:
        return jsonify({"sucesso": False, "erro": "peso_bruto invalido (deve ser numerico >= 0)"}), 400
    # Quando vendido, exigir > 0 (regra A1/A2 — coerente com auditor)
    if vendido and pall <= 0:
        return jsonify({"sucesso": False, "erro": "palletizacao deve ser > 0 para produto vendido"}), 400
    if vendido and peso <= 0:
        return jsonify({"sucesso": False, "erro": "peso_bruto deve ser > 0 para produto vendido"}), 400

    valores = {"cod_produto": cod, "nome_produto": nome, "palletizacao": pall, "peso_bruto": peso, "ativo": True}
    for c in CAMPOS_MESTRE_EDITAVEIS:
        if c in ("nome_produto", "palletizacao", "peso_bruto"):
            continue
        if c in dados:
            try:
                valores[c] = _coerce(c, dados.get(c))
            except _CoerceError as e:
                return jsonify({"sucesso": False, "erro": str(e)}), 400

    cols = ", ".join(valores.keys())
    placeholders = ", ".join(f":{k}" for k in valores.keys())

    try:
        db.session.execute(
            text(
                f"INSERT INTO cadastro_palletizacao ({cols}, created_at, updated_at) "
                f"VALUES ({placeholders}, NOW(), NOW())"
            ),
            valores,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"sucesso": False, "erro": str(e)}), 500

    return jsonify({"sucesso": True, "cod_produto": cod, "mensagem": f"Produto {cod} criado"})


@produtos_bp.route("/api/mestre/<path:cod_produto>", methods=["PUT"])
@login_required
def api_atualizar_mestre(cod_produto: str):
    """Atualiza campos de cadastro_palletizacao (resolve REPARAR_MESTRE)."""
    cod_produto = cod_produto.strip()
    dados = request.get_json(silent=True) or {}

    existe = db.session.execute(
        text("SELECT 1 FROM cadastro_palletizacao WHERE cod_produto=:c"), {"c": cod_produto}
    ).fetchone()
    if not existe:
        return jsonify({"sucesso": False, "erro": "Produto nao encontrado"}), 404

    sets = []
    valores = {"cod": cod_produto}
    for campo in CAMPOS_MESTRE_EDITAVEIS:
        if campo not in dados:
            continue
        try:
            v = _coerce(campo, dados.get(campo))
        except _CoerceError as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 400
        # Validacao basica para NOT NULL fields
        if campo in ("nome_produto", "palletizacao", "peso_bruto") and (v is None or v == ""):
            return jsonify({"sucesso": False, "erro": f"{campo} nao pode ser vazio"}), 400
        sets.append(f"{campo} = :{campo}")
        valores[campo] = v

    if not sets:
        return jsonify({"sucesso": False, "erro": "Nenhum campo informado"}), 400

    sql = (
        f"UPDATE cadastro_palletizacao "
        f"SET {', '.join(sets)}, updated_at = NOW() "
        f"WHERE cod_produto = :cod"
    )
    try:
        db.session.execute(text(sql), valores)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"sucesso": False, "erro": str(e)}), 500

    return jsonify({"sucesso": True, "cod_produto": cod_produto, "campos_atualizados": list(valores.keys() - {"cod"})})


# ============================================================================
# API WRITE: BOM (lista_materiais)
# ============================================================================

@produtos_bp.route("/api/bom-item", methods=["POST"])
@login_required
def api_criar_bom_item():
    """Cria item em lista_materiais (resolve B3/B6)."""
    dados = request.get_json(silent=True) or {}
    cod_produzido = (dados.get("cod_produto_produzido") or "").strip()
    cod_componente = (dados.get("cod_produto_componente") or "").strip()
    qtd = dados.get("qtd_utilizada")

    if not cod_produzido or not cod_componente:
        return jsonify({"sucesso": False, "erro": "cod_produto_produzido e cod_produto_componente sao obrigatorios"}), 400
    try:
        qtd = float(qtd)
        if qtd <= 0:
            raise ValueError
    except Exception:
        return jsonify({"sucesso": False, "erro": "qtd_utilizada invalida (>0)"}), 400

    # Validar que ambos existem no mestre
    mestre_check = db.session.execute(
        text(
            "SELECT cod_produto, nome_produto FROM cadastro_palletizacao "
            "WHERE cod_produto IN (:p, :c)"
        ),
        {"p": cod_produzido, "c": cod_componente},
    ).fetchall()
    encontrados = {r[0]: r[1] for r in mestre_check}
    if cod_produzido not in encontrados:
        return jsonify({"sucesso": False, "erro": f"Produto produzido {cod_produzido} nao existe no mestre"}), 400
    if cod_componente not in encontrados:
        return jsonify({"sucesso": False, "erro": f"Componente {cod_componente} nao existe no mestre. Cadastre-o primeiro."}), 400

    # Verificar se ja existe combinacao ativa
    ja_existe = db.session.execute(
        text(
            "SELECT id FROM lista_materiais "
            "WHERE cod_produto_produzido=:p AND cod_produto_componente=:c "
            "AND (status IS NULL OR UPPER(status) IN ('A','ATIVO'))"
        ),
        {"p": cod_produzido, "c": cod_componente},
    ).fetchone()
    if ja_existe:
        return jsonify({"sucesso": False, "erro": "BOM ja existe para este par produzido/componente"}), 409

    user = getattr(current_user, "nome", "auditoria_produtos")
    try:
        db.session.execute(
            text(
                "INSERT INTO lista_materiais ("
                "cod_produto_produzido, nome_produto_produzido, "
                "cod_produto_componente, nome_produto_componente, "
                "qtd_utilizada, status, criado_em, criado_por"
                ") VALUES ("
                ":cp, :np, :cc, :nc, :qtd, 'A', NOW(), :user"
                ")"
            ),
            {
                "cp": cod_produzido, "np": encontrados[cod_produzido],
                "cc": cod_componente, "nc": encontrados[cod_componente],
                "qtd": qtd, "user": user,
            },
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"sucesso": False, "erro": str(e)}), 500

    return jsonify({"sucesso": True, "mensagem": f"Componente {cod_componente} adicionado ao BOM de {cod_produzido}"})


# ============================================================================
# API WRITE: recurso_producao
# ============================================================================

@produtos_bp.route("/api/recurso", methods=["POST"])
@login_required
def api_criar_recurso():
    """Cria registro em recursos_producao (resolve B5)."""
    dados = request.get_json(silent=True) or {}
    cod = (dados.get("cod_produto") or "").strip()
    linha = (dados.get("linha_producao") or "").strip()
    try:
        qtd_caixa = int(dados.get("qtd_unidade_por_caixa") or 0)
        capacidade = float(dados.get("capacidade_unidade_minuto") or 0)
    except Exception:
        return jsonify({"sucesso": False, "erro": "qtd_unidade_por_caixa ou capacidade invalidos"}), 400

    if not cod or not linha or qtd_caixa <= 0 or capacidade <= 0:
        return jsonify({"sucesso": False, "erro": "Campos obrigatorios: cod_produto, linha_producao, qtd_unidade_por_caixa>0, capacidade_unidade_minuto>0"}), 400

    # nome_produto a partir do mestre
    row = db.session.execute(
        text("SELECT nome_produto FROM cadastro_palletizacao WHERE cod_produto=:c"), {"c": cod}
    ).fetchone()
    if not row:
        return jsonify({"sucesso": False, "erro": f"Produto {cod} nao existe no mestre"}), 400
    nome = row[0]

    # qtd_lote_ideal/minimo, eficiencia, tempo_setup — opcionais
    qtd_ideal = dados.get("qtd_lote_ideal")
    qtd_minimo = dados.get("qtd_lote_minimo")
    eficiencia = dados.get("eficiencia_media")
    tempo_setup = dados.get("tempo_setup")

    try:
        db.session.execute(
            text(
                "INSERT INTO recursos_producao ("
                "cod_produto, nome_produto, linha_producao, qtd_unidade_por_caixa, "
                "capacidade_unidade_minuto, qtd_lote_ideal, qtd_lote_minimo, "
                "eficiencia_media, tempo_setup, disponivel, criado_em"
                ") VALUES ("
                ":cod, :nome, :linha, :qcaixa, :cap, :qideal, :qmin, :ef, :setup, true, NOW()"
                ")"
            ),
            {
                "cod": cod, "nome": nome, "linha": linha,
                "qcaixa": qtd_caixa, "cap": capacidade,
                "qideal": qtd_ideal, "qmin": qtd_minimo,
                "ef": eficiencia, "setup": tempo_setup,
            },
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"sucesso": False, "erro": str(e)}), 500

    return jsonify({"sucesso": True, "mensagem": f"Recurso de producao criado para {cod}"})


# ============================================================================
# API WRITE: perfil fiscal produto/fornecedor
# ============================================================================

@produtos_bp.route("/api/perfil-fiscal", methods=["POST"])
@login_required
def api_criar_perfil_fiscal():
    """Cria perfil fiscal minimo (resolve C2)."""
    dados = request.get_json(silent=True) or {}
    cod = (dados.get("cod_produto") or "").strip()
    cnpj_fornecedor = (dados.get("cnpj_fornecedor") or "").strip()
    ncm = (dados.get("ncm_esperado") or "").strip()

    if not cod or not cnpj_fornecedor:
        return jsonify({"sucesso": False, "erro": "cod_produto e cnpj_fornecedor sao obrigatorios"}), 400

    row = db.session.execute(
        text("SELECT nome_produto FROM cadastro_palletizacao WHERE cod_produto=:c"), {"c": cod}
    ).fetchone()
    if not row:
        return jsonify({"sucesso": False, "erro": f"Produto {cod} nao existe no mestre"}), 400
    nome = row[0]

    cfops = (dados.get("cfop_esperados") or "").strip()
    cnpj_compradora = (dados.get("cnpj_empresa_compradora") or "").strip() or None
    user = getattr(current_user, "nome", "auditoria_produtos")

    try:
        db.session.execute(
            text(
                "INSERT INTO perfil_fiscal_produto_fornecedor ("
                "cnpj_empresa_compradora, cnpj_fornecedor, cod_produto, nome_produto, "
                "ncm_esperado, cfop_esperados, criado_por, criado_em"
                ") VALUES ("
                ":cc, :cf, :cod, :nome, :ncm, :cfops, :user, NOW()"
                ")"
            ),
            {
                "cc": cnpj_compradora, "cf": cnpj_fornecedor, "cod": cod, "nome": nome,
                "ncm": ncm or None, "cfops": cfops or None, "user": user,
            },
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"sucesso": False, "erro": str(e)}), 500

    return jsonify({"sucesso": True, "mensagem": f"Perfil fiscal {cod} x {cnpj_fornecedor} criado"})


# ============================================================================
# API WRITE: resolver divergencias (D2/D3) — atualizar mestre
# ============================================================================

@produtos_bp.route("/api/sincronizar-nome/<path:cod_produto>", methods=["POST"])
@login_required
def api_sincronizar_nome(cod_produto: str):
    """D2: atualiza nome_produto do mestre."""
    cod_produto = cod_produto.strip()
    dados = request.get_json(silent=True) or {}
    novo_nome = (dados.get("novo_nome") or "").strip()
    if not novo_nome:
        return jsonify({"sucesso": False, "erro": "novo_nome obrigatorio"}), 400

    existe = db.session.execute(
        text("SELECT 1 FROM cadastro_palletizacao WHERE cod_produto=:c"), {"c": cod_produto}
    ).fetchone()
    if not existe:
        return jsonify({"sucesso": False, "erro": "Produto nao encontrado"}), 404

    try:
        db.session.execute(
            text("UPDATE cadastro_palletizacao SET nome_produto=:n, updated_at=NOW() WHERE cod_produto=:c"),
            {"n": novo_nome, "c": cod_produto},
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"sucesso": False, "erro": str(e)}), 500

    return jsonify({"sucesso": True, "mensagem": f"Nome atualizado no mestre para '{novo_nome}'"})


@produtos_bp.route("/api/atualizar-peso/<path:cod_produto>", methods=["POST"])
@login_required
def api_atualizar_peso(cod_produto: str):
    """D3: atualiza peso_bruto do mestre."""
    cod_produto = cod_produto.strip()
    dados = request.get_json(silent=True) or {}
    try:
        novo_peso = float(dados.get("novo_peso") or 0)
    except Exception:
        return jsonify({"sucesso": False, "erro": "novo_peso invalido"}), 400
    if novo_peso <= 0:
        return jsonify({"sucesso": False, "erro": "novo_peso deve ser > 0"}), 400

    existe = db.session.execute(
        text("SELECT 1 FROM cadastro_palletizacao WHERE cod_produto=:c"), {"c": cod_produto}
    ).fetchone()
    if not existe:
        return jsonify({"sucesso": False, "erro": "Produto nao encontrado"}), 404

    try:
        db.session.execute(
            text("UPDATE cadastro_palletizacao SET peso_bruto=:p, updated_at=NOW() WHERE cod_produto=:c"),
            {"p": novo_peso, "c": cod_produto},
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"sucesso": False, "erro": str(e)}), 500

    return jsonify({"sucesso": True, "mensagem": f"peso_bruto atualizado no mestre para {novo_peso}"})

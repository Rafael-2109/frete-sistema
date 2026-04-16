"""
Rotas API para gerenciamento de Saldo Standby
"""

from flask import Blueprint, jsonify, request, render_template, send_file
from flask_login import login_required, current_user
from decimal import Decimal
from sqlalchemy import case, func
import json
import io
import logging
from app.utils.timezone import agora_utc_naive

from app import db
from app.carteira.models import CarteiraPrincipal, SaldoStandby

logger = logging.getLogger(__name__)

standby_bp = Blueprint("standby", __name__, url_prefix="/api/standby")


def _obter_dados_standby():
    """Obtém dados de standby enriquecidos com CarteiraPrincipal (dedup + detecção cancelados).

    Returns:
        tuple: (lista_pedidos, total_duplicados, total_cancelados)
    """
    active_statuses = ["ATIVO", "BLOQ. COML.", "SALDO"]

    # Dedup: min(id) per (num_pedido, cod_produto) — ignora duplicatas
    keep_ids = (
        db.session.query(func.min(SaldoStandby.id))
        .filter(SaldoStandby.status_standby.in_(active_statuses))
        .group_by(SaldoStandby.num_pedido, SaldoStandby.cod_produto)
    )

    # Contar duplicatas
    total_ativos = (
        db.session.query(func.count(SaldoStandby.id))
        .filter(SaldoStandby.status_standby.in_(active_statuses))
        .scalar() or 0
    )
    total_unicos = (
        db.session.query(func.count())
        .select_from(keep_ids.subquery())
        .scalar() or 0
    )
    total_duplicados = total_ativos - total_unicos

    # Agregação principal (apenas rows dedupadas)
    pedidos_standby = (
        db.session.query(
            SaldoStandby.num_pedido,
            SaldoStandby.cnpj_cliente,
            SaldoStandby.nome_cliente,
            SaldoStandby.tipo_standby,
            SaldoStandby.status_standby,
            SaldoStandby.data_pedido,
            func.sum(SaldoStandby.qtd_saldo).label("qtd_total"),
            func.sum(SaldoStandby.valor_saldo).label("valor_total"),
            func.sum(SaldoStandby.peso_saldo).label("peso_total"),
            func.sum(SaldoStandby.pallet_saldo).label("pallet_total"),
            func.count(SaldoStandby.cod_produto).label("total_itens"),
        )
        .filter(SaldoStandby.id.in_(keep_ids))
        .group_by(
            SaldoStandby.num_pedido,
            SaldoStandby.cnpj_cliente,
            SaldoStandby.nome_cliente,
            SaldoStandby.tipo_standby,
            SaldoStandby.status_standby,
            SaldoStandby.data_pedido,
        )
        .all()
    )

    if not pedidos_standby:
        return [], total_duplicados, 0

    # Batch: num_pedidos únicos
    num_pedidos = list(set(p.num_pedido for p in pedidos_standby))

    # Batch: CarteiraPrincipal — raz_social_red, municipio, estado + detecção cancelado
    carteira_data = (
        db.session.query(
            CarteiraPrincipal.num_pedido,
            func.min(CarteiraPrincipal.raz_social_red).label("raz_social_red"),
            func.min(CarteiraPrincipal.municipio).label("municipio"),
            func.min(CarteiraPrincipal.estado).label("estado"),
            func.sum(
                case(
                    (CarteiraPrincipal.status_pedido != "Cancelado", 1),
                    else_=0,
                )
            ).label("linhas_ativas"),
        )
        .filter(CarteiraPrincipal.num_pedido.in_(num_pedidos))
        .group_by(CarteiraPrincipal.num_pedido)
        .all()
    )
    carteira_lookup = {c.num_pedido: c for c in carteira_data}

    # Batch: produtos (dedupados)
    produtos_dedup = (
        SaldoStandby.query
        .filter(SaldoStandby.id.in_(keep_ids))
        .filter(SaldoStandby.num_pedido.in_(num_pedidos))
        .all()
    )
    produtos_por_pedido = {}
    for prod in produtos_dedup:
        produtos_por_pedido.setdefault(prod.num_pedido, []).append(prod)

    # Batch: nome_produto
    nomes = (
        db.session.query(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
        )
        .filter(CarteiraPrincipal.num_pedido.in_(num_pedidos))
        .all()
    )
    nome_lookup = {(n.num_pedido, n.cod_produto): n.nome_produto for n in nomes}

    # Build result
    total_cancelados = 0
    resultado = []

    for pedido in pedidos_standby:
        cart = carteira_lookup.get(pedido.num_pedido)
        na_carteira = cart is not None
        cancelado = not na_carteira or (cart.linhas_ativas or 0) == 0
        if cancelado:
            total_cancelados += 1

        produtos = produtos_por_pedido.get(pedido.num_pedido, [])
        produtos_lista = [
            {
                "cod_produto": prod.cod_produto,
                "nome_produto": nome_lookup.get((prod.num_pedido, prod.cod_produto), ""),
                "qtd_saldo": float(prod.qtd_saldo),
                "valor_saldo": float(prod.valor_saldo),
                "peso_saldo": float(prod.peso_saldo) if prod.peso_saldo else 0,
                "pallet_saldo": float(prod.pallet_saldo) if prod.pallet_saldo else 0,
            }
            for prod in produtos
        ]

        primeiro_item = produtos[0] if produtos else None
        observacoes = []
        if primeiro_item and primeiro_item.observacoes:
            try:
                observacoes = json.loads(primeiro_item.observacoes)
            except (json.JSONDecodeError, ValueError):
                observacoes = []

        resultado.append(
            {
                "num_pedido": pedido.num_pedido,
                "cnpj_cliente": pedido.cnpj_cliente,
                "nome_cliente": pedido.nome_cliente,
                "raz_social_red": cart.raz_social_red if cart else "",
                "uf": cart.estado if cart else "",
                "cidade": cart.municipio if cart else "",
                "tipo_standby": pedido.tipo_standby,
                "status_standby": pedido.status_standby,
                "data_pedido": pedido.data_pedido.strftime("%d/%m/%Y") if pedido.data_pedido else "",
                "qtd_total": float(pedido.qtd_total),
                "valor_total": float(pedido.valor_total),
                "peso_total": float(pedido.peso_total) if pedido.peso_total else 0,
                "pallet_total": float(pedido.pallet_total) if pedido.pallet_total else 0,
                "total_itens": pedido.total_itens,
                "produtos": produtos_lista,
                "observacoes": observacoes,
                "total_observacoes": len(observacoes),
                "na_carteira": na_carteira,
                "cancelado": cancelado,
            }
        )

    return resultado, total_duplicados, total_cancelados


@standby_bp.route("/criar", methods=["POST"])
@login_required
def criar_standby():
    """Cria um registro de Saldo Standby"""
    try:
        data = request.get_json()

        # Validar dados obrigatórios
        required_fields = ["num_pedido", "tipo_standby"]
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Campo {field} é obrigatório"}), 400

        num_pedido = data["num_pedido"]
        tipo_standby = data["tipo_standby"]

        # Buscar itens da carteira para o pedido
        itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()

        if not itens_carteira:
            return jsonify({"success": False, "message": "Pedido não encontrado na carteira"}), 404

        # Verificar se pedido já está em standby
        standby_existente = SaldoStandby.query.filter(
            SaldoStandby.num_pedido == num_pedido, SaldoStandby.status_standby.in_(["ATIVO", "BLOQ. COML.", "SALDO"])
        ).first()

        if standby_existente:
            return jsonify({"success": False, "message": "Pedido já está em standby"}), 400

        # Importar CadastroPalletizacao para calcular peso e pallet
        from app.producao.models import CadastroPalletizacao
        
        # Criar registros de standby para cada item
        registros_criados = []
        for item in itens_carteira:
            # Buscar dados de palletização para o produto
            palletizacao = CadastroPalletizacao.query.filter_by(
                cod_produto=item.cod_produto,
                ativo=True
            ).first()
            
            # Calcular peso e pallet baseado na palletização
            qtd_saldo = float(item.qtd_saldo_produto_pedido)
            
            if palletizacao:
                # Usar cálculos da palletização
                peso_calculado = qtd_saldo * float(palletizacao.peso_bruto) if palletizacao.peso_bruto else 0
                pallet_calculado = qtd_saldo / float(palletizacao.palletizacao) if palletizacao.palletizacao and palletizacao.palletizacao > 0 else 0
            else:
                # NOTA: Campos peso e pallet não existem em CarteiraPrincipal - usar 0 como default
                peso_calculado = 0
                pallet_calculado = 0
            
            novo_standby = SaldoStandby(
                origem_separacao_lote_id="",  # Campo removido de CarteiraPrincipal - mantido vazio para compatibilidade
                num_pedido=item.num_pedido,
                cod_produto=item.cod_produto,
                cnpj_cliente=item.cnpj_cpf,
                nome_cliente=item.raz_social or item.raz_social_red or "",
                qtd_saldo=qtd_saldo,
                valor_saldo=Decimal(str(qtd_saldo)) * Decimal(str(item.preco_produto_pedido or 0)),
                peso_saldo=peso_calculado,
                pallet_saldo=pallet_calculado,
                data_pedido=item.data_pedido,
                tipo_standby=tipo_standby,
                status_standby="ATIVO",
                criado_por=(
                    getattr(current_user, "nome", None) or getattr(current_user, "username", None) or "Sistema"
                ),
            )
            db.session.add(novo_standby)
            registros_criados.append({"cod_produto": item.cod_produto, "qtd": qtd_saldo})

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Pedido {num_pedido} enviado para standby com sucesso",
                "itens": registros_criados,
            }
        )

    except Exception as e:
        logger.error(f"Erro ao criar standby: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@standby_bp.route("/status/<num_pedido>", methods=["GET"])
@login_required
def verificar_status_standby(num_pedido):
    """Verifica se um pedido está em standby e retorna o status"""
    try:
        standby = (
            SaldoStandby.query.filter_by(num_pedido=num_pedido)
            .filter(SaldoStandby.status_standby.in_(["ATIVO", "BLOQ. COML.", "SALDO", "CONFIRMADO"]))
            .first()
        )

        if standby:
            return jsonify(
                {
                    "success": True,
                    "em_standby": True,
                    "status_standby": standby.status_standby,
                    "tipo_standby": standby.tipo_standby,
                }
            )
        else:
            return jsonify({"success": True, "em_standby": False})

    except Exception as e:
        logger.error(f"Erro ao verificar status standby: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@standby_bp.route("/adicionar-observacao", methods=["POST"])
@login_required
def adicionar_observacao_standby():
    """Adiciona uma observação ao histórico do pedido em standby"""
    try:
        data = request.get_json()
        num_pedido = data.get("num_pedido")
        observacao = data.get("observacao")
        
        if not num_pedido or not observacao:
            return jsonify({"success": False, "message": "Dados incompletos"}), 400
        
        # Buscar todos os itens do pedido
        itens_standby = SaldoStandby.query.filter(
            SaldoStandby.num_pedido == num_pedido
        ).all()
        
        if not itens_standby:
            return jsonify({"success": False, "message": "Pedido não encontrado em standby"}), 404
        
        # Criar nova entrada de observação
        nova_observacao = {
            "data": agora_utc_naive().strftime("%d/%m/%Y %H:%M"),
            "usuario": current_user.nome if hasattr(current_user, "nome") else "Sistema",
            "texto": observacao
        }
        
        # Atualizar observações em todos os itens do pedido
        for item in itens_standby:
            # Carregar observações existentes ou criar lista vazia
            if item.observacoes:
                try:
                    observacoes_existentes = json.loads(item.observacoes)
                except (json.JSONDecodeError, ValueError):
                    observacoes_existentes = []
            else:
                observacoes_existentes = []
            
            # Adicionar nova observação
            observacoes_existentes.append(nova_observacao)
            
            # Salvar como JSON
            item.observacoes = json.dumps(observacoes_existentes, ensure_ascii=False)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Observação adicionada com sucesso",
            "observacao": nova_observacao
        })
        
    except Exception as e:
        logger.error(f"Erro ao adicionar observação: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@standby_bp.route("/atualizar-status", methods=["POST"])
@login_required
def atualizar_status_standby():
    """Atualiza o status de um pedido em standby"""
    try:
        data = request.get_json()
        num_pedido = data.get("num_pedido")
        novo_status = data.get("novo_status")

        if not num_pedido or not novo_status:
            return jsonify({"success": False, "message": "Dados incompletos"}), 400

        # Atualizar todos os itens do pedido
        itens_standby = SaldoStandby.query.filter(SaldoStandby.num_pedido == num_pedido).all()

        if not itens_standby:
            return jsonify({"success": False, "message": "Pedido não encontrado em standby"}), 404

        for item in itens_standby:
            item.status_standby = novo_status
            if novo_status == "CONFIRMADO":
                item.data_resolucao = agora_utc_naive()
                item.resolvido_por = current_user.nome if hasattr(current_user, "nome") else "Sistema"
                item.resolucao_final = "RETORNO_CARTEIRA"

        db.session.commit()

        return jsonify({"success": True, "message": f"Status atualizado para {novo_status}"})

    except Exception as e:
        logger.error(f"Erro ao atualizar status standby: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@standby_bp.route("/listar", methods=["GET"])
@login_required
def listar_standby():
    """Lista todos os pedidos em standby (dedupados, enriquecidos com carteira)"""
    try:
        resultado, total_duplicados, total_cancelados = _obter_dados_standby()
        return jsonify({
            "success": True,
            "pedidos": resultado,
            "total_duplicados": total_duplicados,
            "total_cancelados": total_cancelados,
        })
    except Exception as e:
        logger.error(f"Erro ao listar standby: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@standby_bp.route("/estatisticas", methods=["GET"])
@login_required
def estatisticas_standby():
    """Retorna estatísticas dos pedidos em standby"""
    try:
        # Estatísticas por status
        stats_status = (
            db.session.query(
                SaldoStandby.status_standby,
                func.count(func.distinct(SaldoStandby.num_pedido)).label("qtd_pedidos"),
                func.sum(SaldoStandby.valor_saldo).label("valor_total"),
            )
            .filter(SaldoStandby.status_standby.in_(["ATIVO", "BLOQ. COML.", "SALDO"]))
            .group_by(SaldoStandby.status_standby)
            .all()
        )

        resultado = {"por_status": []}

        for stat in stats_status:
            resultado["por_status"].append(
                {
                    "status": stat.status_standby,
                    "qtd_pedidos": stat.qtd_pedidos,
                    "valor_total": float(stat.valor_total) if stat.valor_total else 0,
                }
            )

        # Total geral
        total_geral = (
            db.session.query(
                func.count(func.distinct(SaldoStandby.num_pedido)).label("total_pedidos"),
                func.sum(SaldoStandby.valor_saldo).label("valor_total"),
            )
            .filter(SaldoStandby.status_standby.in_(["ATIVO", "BLOQ. COML.", "SALDO"]))
            .first()
        )

        resultado["total"] = {
            "pedidos": total_geral.total_pedidos or 0,
            "valor": float(total_geral.valor_total) if total_geral.valor_total else 0,
        }

        return jsonify({"success": True, "estatisticas": resultado})

    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas standby: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@standby_bp.route("/exportar", methods=["GET"])
@login_required
def exportar_standby():
    """Exporta pedidos em standby para Excel"""
    try:
        import pandas as pd

        resultado, _, _ = _obter_dados_standby()

        dados = []
        for pedido in resultado:
            dados.append({
                "Pedido": pedido["num_pedido"],
                "CNPJ": pedido["cnpj_cliente"],
                "Razao Social": pedido["nome_cliente"],
                "Nome Reduzido": pedido["raz_social_red"],
                "UF": pedido["uf"],
                "Cidade": pedido["cidade"],
                "Data Pedido": pedido["data_pedido"],
                "Tipo": pedido["tipo_standby"],
                "Status": pedido["status_standby"],
                "Valor Total": pedido["valor_total"],
                "Peso Total (kg)": pedido["peso_total"],
                "Pallet Total": pedido["pallet_total"],
                "Itens": pedido["total_itens"],
                "Na Carteira": "Sim" if pedido["na_carteira"] else "Nao",
                "Cancelado": "Sim" if pedido["cancelado"] else "Nao",
            })

        df = pd.DataFrame(dados)
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Standby", index=False)

            worksheet = writer.sheets["Standby"]
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2 if len(df) > 0 else len(col) + 2
                worksheet.set_column(i, i, min(max_len, 40))

        output.seek(0)
        nome_arquivo = f"standby_{agora_utc_naive().strftime('%Y%m%d_%H%M')}.xlsx"

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=nome_arquivo,
        )
    except Exception as e:
        logger.error(f"Erro ao exportar standby: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@standby_bp.route("/limpar-cancelados-duplicados", methods=["POST"])
@login_required
def limpar_cancelados_duplicados():
    """Remove registros duplicados e marca cancelados/orfaos como CONFIRMADO"""
    try:
        active_statuses = ["ATIVO", "BLOQ. COML.", "SALDO"]
        agora = agora_utc_naive()
        usuario = getattr(current_user, "nome", None) or getattr(current_user, "username", "Sistema")
        removidos = 0
        pedidos_cancelados = 0

        # 1. Duplicatas: marcar como CONFIRMADO/DUPLICADO
        keep_ids = (
            db.session.query(func.min(SaldoStandby.id))
            .filter(SaldoStandby.status_standby.in_(active_statuses))
            .group_by(SaldoStandby.num_pedido, SaldoStandby.cod_produto)
        )

        duplicados = SaldoStandby.query.filter(
            SaldoStandby.status_standby.in_(active_statuses),
            ~SaldoStandby.id.in_(keep_ids),
        ).all()

        for dup in duplicados:
            dup.status_standby = "CONFIRMADO"
            dup.resolucao_final = "DUPLICADO"
            dup.data_resolucao = agora
            dup.resolvido_por = f"{usuario} (limpeza)"
            removidos += 1

        # 2. Cancelados/orfaos: pedidos sem linha ativa na carteira
        num_pedidos = [
            p.num_pedido for p in
            db.session.query(SaldoStandby.num_pedido)
            .filter(SaldoStandby.status_standby.in_(active_statuses))
            .distinct()
            .all()
        ]

        if num_pedidos:
            pedidos_validos = set(
                p.num_pedido for p in
                db.session.query(CarteiraPrincipal.num_pedido)
                .filter(
                    CarteiraPrincipal.num_pedido.in_(num_pedidos),
                    CarteiraPrincipal.status_pedido != "Cancelado",
                )
                .distinct()
                .all()
            )

            orfaos = [p for p in num_pedidos if p not in pedidos_validos]

            if orfaos:
                itens = SaldoStandby.query.filter(
                    SaldoStandby.num_pedido.in_(orfaos),
                    SaldoStandby.status_standby.in_(active_statuses),
                ).all()

                for item in itens:
                    item.status_standby = "CONFIRMADO"
                    item.resolucao_final = "CANCELADO"
                    item.data_resolucao = agora
                    item.resolvido_por = f"{usuario} (limpeza)"

                pedidos_cancelados = len(orfaos)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Limpeza concluida: {removidos} registros duplicados e {pedidos_cancelados} pedidos cancelados resolvidos",
            "removidos": removidos,
            "cancelados": pedidos_cancelados,
        })
    except Exception as e:
        logger.error(f"Erro na limpeza de standby: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# View para template de standby
@standby_bp.route("/visualizar")
@login_required
def visualizar_standby():
    """Renderiza o template de visualização de standby"""
    return render_template("carteira/standby.html")

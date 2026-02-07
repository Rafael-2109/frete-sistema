"""
Rotas API para gerenciamento de Saldo Standby
"""

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func
import logging
from app.utils.timezone import agora_utc_naive

from app import db
from app.carteira.models import CarteiraPrincipal, SaldoStandby

logger = logging.getLogger(__name__)

standby_bp = Blueprint("standby", __name__, url_prefix="/api/standby")


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
        import json
        from datetime import datetime
        
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
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
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
    """Lista todos os pedidos em standby agrupados"""
    try:
        # Buscar pedidos em standby agrupados
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
            .filter(SaldoStandby.status_standby.in_(["ATIVO", "BLOQ. COML.", "SALDO"]))
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

        # Importar CarteiraPrincipal para buscar nome_produto
        from app.carteira.models import CarteiraPrincipal
        
        resultado = []
        for pedido in pedidos_standby:
            # Buscar produtos do pedido
            produtos = SaldoStandby.query.filter_by(num_pedido=pedido.num_pedido).all()

            produtos_lista = []
            for prod in produtos:
                # Buscar nome do produto na CarteiraPrincipal
                item_carteira = CarteiraPrincipal.query.filter_by(
                    num_pedido=prod.num_pedido,
                    cod_produto=prod.cod_produto
                ).first()
                
                nome_produto = item_carteira.nome_produto if item_carteira else ""
                
                produtos_lista.append(
                    {
                        "cod_produto": prod.cod_produto,
                        "nome_produto": nome_produto,
                        "qtd_saldo": float(prod.qtd_saldo),
                        "valor_saldo": float(prod.valor_saldo),
                        "peso_saldo": float(prod.peso_saldo) if prod.peso_saldo else 0,
                        "pallet_saldo": float(prod.pallet_saldo) if prod.pallet_saldo else 0,
                    }
                )

            # Buscar observações do primeiro item (são iguais para todos)
            import json
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
                    "total_observacoes": len(observacoes)
                }
            )

        return jsonify({"success": True, "pedidos": resultado})

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


# View para template de standby
@standby_bp.route("/visualizar")
@login_required
def visualizar_standby():
    """Renderiza o template de visualização de standby"""
    return render_template("carteira/standby.html")

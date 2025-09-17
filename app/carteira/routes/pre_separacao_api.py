"""
APIs para gerenciamento de pré-separações
Sistema de persistência para drag & drop do workspace
MIGRADO: PreSeparacaoItem → Separacao (status='PREVISAO')
"""

from flask import jsonify, request, current_app
from flask_login import login_required
from datetime import datetime
from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao  # MIGRADO: Usando Separacao ao invés de PreSeparacaoItem
from app.carteira.utils.separacao_utils import calcular_peso_pallet_produto
from app.utils.lote_utils import gerar_lote_id as gerar_novo_lote_id  # Função padronizada
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)




@carteira_bp.route("/api/pedido/<num_pedido>/pre-separacoes")
@login_required
def listar_pre_separacoes(num_pedido):
    """
    API para listar pré-separações existentes de um pedido
    Usado para carregar o workspace com dados já salvos
    """
    try:
        # MIGRADO: Buscar Separacao com status='PREVISAO'
        pre_separacoes = Separacao.query.filter(
            Separacao.num_pedido == num_pedido, 
            Separacao.status == 'PREVISAO'  # MIGRADO: Status único para pré-separação
        ).all()

        # Agrupar por separacao_lote_id
        lotes = {}
        for pre_sep in pre_separacoes:
            lote_key = pre_sep.separacao_lote_id

            if lote_key not in lotes:
                lotes[lote_key] = {
                    "lote_id": lote_key,
                    "data_expedicao": (
                        pre_sep.expedicao.strftime('%Y-%m-%d') if pre_sep.expedicao else None  # MIGRADO: data_expedicao_editada → expedicao
                    ),
                    "data_agendamento": (
                        pre_sep.agendamento.strftime('%Y-%m-%d') if pre_sep.agendamento else None  # MIGRADO: data_agendamento_editada → agendamento
                    ),
                    "agendamento_confirmado": pre_sep.agendamento_confirmado,  # Este campo existe em Separacao
                    "protocolo": pre_sep.protocolo,  # MIGRADO: protocolo_editado → protocolo
                    "status": "pre_separacao",
                    "produtos": [],
                    "totais": {"valor": 0, "peso": 0, "pallet": 0},
                    "pre_separacao_id": pre_sep.id,
                }

            # Calcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(
                pre_sep.cod_produto, float(pre_sep.qtd_saldo)  # MIGRADO: qtd_selecionada_usuario → qtd_saldo
            )

            produto_data = {
                "pre_separacao_id": pre_sep.id,
                "cod_produto": pre_sep.cod_produto,
                "nome_produto": pre_sep.nome_produto,
                "quantidade": float(pre_sep.qtd_saldo),  # MIGRADO: qtd_selecionada_usuario → qtd_saldo
                "valor": float(pre_sep.valor_saldo or 0),  # MIGRADO: valor_original_item → valor_saldo
                "peso": peso_calculado,
                "pallet": pallet_calculado,
            }

            lotes[lote_key]["produtos"].append(produto_data)
            lotes[lote_key]["totais"]["valor"] += produto_data["valor"]
            lotes[lote_key]["totais"]["peso"] += produto_data["peso"]
            lotes[lote_key]["totais"]["pallet"] += produto_data["pallet"]

        return jsonify(
            {"success": True, "num_pedido": num_pedido, "lotes": list(lotes.values()), "total_lotes": len(lotes)}
        )

    except Exception as e:
        logger.error(f"Erro ao listar pré-separações do pedido {num_pedido}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500

"""
APIs reais para o workspace de montagem de carga
"""

import logging

from flask import jsonify
from flask_login import login_required
from sqlalchemy import and_, func

from app import db
from app.carteira.models import CarteiraPrincipal
from app.carteira.utils.workspace_utils import processar_dados_workspace_produto
# Estoque agora é carregado assincronamente via /workspace-estoque
from app.producao.models import CadastroPalletizacao
from app.separacao.models import Separacao

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route("/api/pedido/<num_pedido>/workspace")
@login_required
def workspace_pedido_real(num_pedido):
    """
    API real para dados do workspace de montagem
    Retorna produtos do pedido com dados completos de estoque
    """
    try:
        # Buscar produtos do pedido na carteira
        produtos_carteira = (
            db.session.query(
                CarteiraPrincipal.cod_produto,
                CarteiraPrincipal.nome_produto,
                CarteiraPrincipal.qtd_saldo_produto_pedido.label("qtd_pedido"),
                CarteiraPrincipal.preco_produto_pedido.label("preco_unitario"),
                CarteiraPrincipal.expedicao,
                # Dados de palletização
                CadastroPalletizacao.peso_bruto.label("peso_unitario"),
                CadastroPalletizacao.palletizacao,
                # Dados básicos (estoque será calculado via SaldoEstoque)
                CarteiraPrincipal.estoque.label("estoque_hoje"),
            )
            .outerjoin(
                CadastroPalletizacao,
                and_(
                    CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto,
                    CadastroPalletizacao.ativo == True,
                ),
            )
            .filter(CarteiraPrincipal.num_pedido == num_pedido, CarteiraPrincipal.ativo == True)
            .all()
        )

        if not produtos_carteira:
            return jsonify({"success": False, "error": f"Pedido {num_pedido} não encontrado ou sem itens ativos"}), 404

        # MIGRADO: Status do pedido não é mais necessário aqui
        # O status agora está em cada Separacao individual
        
        # OTIMIZAÇÃO: Buscar TODAS as separações do pedido DE UMA VEZ (fora do loop!)
        separacoes_agrupadas = db.session.query(
            Separacao.cod_produto,
            func.sum(Separacao.qtd_saldo).label('qtd_total')
        ).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.sincronizado_nf == False  # Apenas não sincronizados
        ).group_by(
            Separacao.cod_produto
        ).all()
        
        # Criar dicionário para lookup rápido O(1)
        qtd_por_produto = {sep.cod_produto: float(sep.qtd_total or 0) for sep in separacoes_agrupadas}
        
        # Processar produtos e calcular dados complementares
        produtos_processados = []
        valor_total = 0

        for produto in produtos_carteira:
            # OTIMIZAÇÃO: NÃO buscar estoque aqui - será feito assincronamente via /workspace-estoque
            # Isso evita duplicação e melhora performance inicial
            resumo_estoque = None  # Será preenchido pela chamada assíncrona
            
            # Processar dados BÁSICOS do produto (sem estoque detalhado)
            produto_data = processar_dados_workspace_produto(produto, resumo_estoque)

            if produto_data:
                # OTIMIZADO: Usar lookup O(1) ao invés de query no banco
                qtd_separacoes = qtd_por_produto.get(produto.cod_produto, 0)
                
                # Adicionar as quantidades aos dados do produto
                produto_data['qtd_pre_separacoes'] = 0  # MIGRADO: Não existe mais distinção
                produto_data['qtd_separacoes'] = qtd_separacoes
                
                # Calcular qtd_saldo disponível (quantidade do pedido - separações)
                qtd_pedido = produto_data.get('qtd_pedido', 0)
                produto_data['qtd_saldo'] = qtd_pedido - produto_data['qtd_separacoes']
                
                produtos_processados.append(produto_data)
                valor_total += produto_data["qtd_pedido"] * produto_data["preco_unitario"]

        return jsonify(
            {
                "success": True,
                "num_pedido": num_pedido,
                "valor_total": valor_total,
                "produtos": produtos_processados,
                "total_produtos": len(produtos_processados),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao buscar workspace do pedido {num_pedido}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500

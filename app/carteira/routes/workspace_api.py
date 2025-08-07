"""
APIs reais para o workspace de montagem de carga
"""

import logging

from flask import jsonify
from flask_login import login_required
from sqlalchemy import and_, func

from app import db
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.carteira.utils.workspace_utils import processar_dados_workspace_produto
# USAR NOVO SISTEMA DE ESTOQUE EM TEMPO REAL
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.pedidos.models import Pedido
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

        # Buscar status do pedido
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        status_pedido = pedido.status if pedido else 'ABERTO'
        
        # Processar produtos e calcular dados complementares
        produtos_processados = []
        valor_total = 0

        for produto in produtos_carteira:
            # Obter projeção completa do produto usando Sistema de Estoque em Tempo Real
            projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(produto.cod_produto, dias=28)
            
            # Converter formato para compatibilidade com workspace_utils
            if projecao_completa:
                resumo_estoque = {
                    'estoque_inicial': projecao_completa['estoque_atual'],
                    'estoque_atual': projecao_completa['estoque_atual'],
                    'menor_estoque_d7': projecao_completa.get('menor_estoque_d7'),
                    'dia_ruptura': projecao_completa.get('dia_ruptura'),
                    'projecao_29_dias': projecao_completa.get('projecao', []),
                    'status_ruptura': 'CRÍTICO' if projecao_completa.get('dia_ruptura') else 'OK'
                }
            else:
                resumo_estoque = None

            # Processar dados do produto usando função utilitária
            produto_data = processar_dados_workspace_produto(produto, resumo_estoque)

            if produto_data:
                # Calcular quantidade em pré-separações ativas
                qtd_pre_separacoes = db.session.query(
                    func.coalesce(func.sum(PreSeparacaoItem.qtd_selecionada_usuario), 0)
                ).filter(
                    PreSeparacaoItem.num_pedido == num_pedido,
                    PreSeparacaoItem.cod_produto == produto.cod_produto,
                    PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).scalar()
                
                # Calcular quantidade em separações confirmadas
                qtd_separacoes = db.session.query(
                    func.coalesce(func.sum(Separacao.qtd_saldo), 0)
                ).join(
                    Pedido,
                    Separacao.separacao_lote_id == Pedido.separacao_lote_id
                ).filter(
                    Separacao.num_pedido == num_pedido,
                    Separacao.cod_produto == produto.cod_produto,
                    Pedido.status.in_(['ABERTO', 'COTADO'])
                ).scalar()
                
                # Adicionar as quantidades aos dados do produto
                produto_data['qtd_pre_separacoes'] = float(qtd_pre_separacoes or 0)
                produto_data['qtd_separacoes'] = float(qtd_separacoes or 0)
                
                produtos_processados.append(produto_data)
                valor_total += produto_data["qtd_pedido"] * produto_data["preco_unitario"]

        return jsonify(
            {
                "success": True,
                "num_pedido": num_pedido,
                "status_pedido": status_pedido,
                "valor_total": valor_total,
                "produtos": produtos_processados,
                "total_produtos": len(produtos_processados),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao buscar workspace do pedido {num_pedido}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500

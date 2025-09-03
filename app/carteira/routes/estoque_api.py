"""
API para carregar dados de estoque de forma assíncrona
"""

from flask import jsonify
from flask_login import login_required
from sqlalchemy import and_, func
from app.carteira.models import CarteiraPrincipal
# MIGRADO: ServicoEstoqueTempoReal -> ServicoEstoqueSimples (02/09/2025)
from app.estoque.services.estoque_simples import ServicoEstoqueSimples as ServicoEstoqueTempoReal
from app.producao.models import CadastroPalletizacao
from app.separacao.models import Separacao
from app.carteira.utils.workspace_utils import processar_dados_workspace_produto
from app import db
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/estoque', methods=['GET'])
@login_required
def obter_estoque_pedido(num_pedido):
    """
    Retorna dados de estoque para produtos de um pedido específico
    Usado para carregamento assíncrono após renderização inicial
    """
    try:
        # Buscar produtos do pedido com dados de estoque
        produtos = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido
        ).all()
        
        produtos_estoque = []
        
        for produto in produtos:
            # USAR ServicoEstoqueTempoReal IGUAL ao workspace_api.py
            try:
                projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(produto.cod_produto, dias=28)
            except Exception as e:
                logger.warning(f"Erro ao buscar projeção para produto {produto.cod_produto}: {e}")
                projecao_completa = None
            
            if projecao_completa and isinstance(projecao_completa, dict):
                # Usar dados calculados pelo serviço (VALORES REAIS)
                produto_estoque = {
                    'cod_produto': produto.cod_produto,
                    'estoque': projecao_completa['estoque_atual'],
                    'estoque_d0': projecao_completa.get('estoque_d0', projecao_completa['estoque_atual']),
                    'menor_estoque_produto_d7': projecao_completa.get('menor_estoque_d7', 0),
                    'saldo_estoque_pedido': float(produto.saldo_estoque_pedido or 0),
                    'dia_ruptura': projecao_completa.get('dia_ruptura')
                }
                
                # Adicionar projeções D0-D28 calculadas
                for i, valor in enumerate(projecao_completa.get('projecao', [])):
                    if i < 29:
                        produto_estoque[f'estoque_d{i}'] = valor
                
                produtos_estoque.append(produto_estoque)
            else:
                # Fallback se o serviço falhar
                produtos_estoque.append({
                    'cod_produto': produto.cod_produto,
                    'estoque': float(produto.estoque or 0),
                    'estoque_d0': float(produto.estoque_d0 or 0),
                    'menor_estoque_produto_d7': float(produto.menor_estoque_produto_d7 or 0),
                    'saldo_estoque_pedido': float(produto.saldo_estoque_pedido or 0),
                    # Adicionar projeções D0-D28 se necessário
                    **{f'estoque_d{i}': float(getattr(produto, f'estoque_d{i}', 0) or 0) for i in range(29)}
                })
        
        return jsonify({
            'success': True,
            'produtos': produtos_estoque,
            'total': len(produtos_estoque)
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar estoque do pedido {num_pedido}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/workspace-estoque', methods=['GET'])
@login_required
def obter_workspace_estoque(num_pedido):
    """
    Retorna dados completos de estoque para o workspace (carregamento assíncrono)
    Inclui projeções, produção programada e análise de ruptura
    CORRIGIDO: Usa CadastroPalletizacao e workspace_utils para consistência
    MELHORADO: Adiciona logs detalhados e tratamento de timeout
    """
    import time
    inicio = time.time()
    logger.info(f"=== Iniciando busca de estoque para pedido {num_pedido} ===")
    
    try:
        # CORREÇÃO 1: Buscar produtos com JOIN em CadastroPalletizacao para peso/pallet corretos
        produtos_carteira = (
            db.session.query(
                CarteiraPrincipal.cod_produto,
                CarteiraPrincipal.nome_produto,
                CarteiraPrincipal.qtd_saldo_produto_pedido.label("qtd_pedido"),
                CarteiraPrincipal.preco_produto_pedido.label("preco_unitario"),
                CarteiraPrincipal.expedicao,
                # Dados de palletização CORRETOS via CadastroPalletizacao
                CadastroPalletizacao.peso_bruto.label("peso_unitario"),
                CadastroPalletizacao.palletizacao,
                # Dados básicos
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
            return jsonify({"success": False, "error": f"Pedido {num_pedido} não encontrado"}), 404
        
        # CORREÇÃO 2: Buscar TODAS as separações do pedido DE UMA VEZ (otimização)
        separacoes_agrupadas = db.session.query(
            Separacao.cod_produto,
            func.sum(Separacao.qtd_saldo).label('qtd_total')
        ).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.sincronizado_nf == False
        ).group_by(
            Separacao.cod_produto
        ).all()
        
        # Criar dicionário para lookup rápido O(1)
        qtd_por_produto = {sep.cod_produto: float(sep.qtd_total or 0) for sep in separacoes_agrupadas}
        
        produtos_completos = []
        valor_total = 0
        produtos_com_erro = []
        
        logger.info(f"Processando {len(produtos_carteira)} produtos do pedido {num_pedido}")
        
        for idx, produto in enumerate(produtos_carteira, 1):
            # Obter projeção completa do produto com medição de tempo
            try:
                inicio_produto = time.time()
                logger.debug(f"[{idx}/{len(produtos_carteira)}] Calculando projeção para produto {produto.cod_produto}")
                
                projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(produto.cod_produto, dias=28)
                
                tempo_produto = (time.time() - inicio_produto) * 1000
                if tempo_produto > 100:  # Log se demorar mais de 100ms
                    logger.warning(f"Produto {produto.cod_produto} demorou {tempo_produto:.0f}ms para calcular projeção")
                    
            except Exception as e:
                logger.error(f"ERRO ao buscar projeção para produto {produto.cod_produto}: {e}", exc_info=True)
                produtos_com_erro.append({
                    'cod_produto': produto.cod_produto,
                    'erro': str(e)
                })
                projecao_completa = None
            
            # CORREÇÃO 3: Usar workspace_utils para consistência com workspace_api.py
            if projecao_completa and isinstance(projecao_completa, dict):
                resumo_estoque = {
                    'estoque_inicial': projecao_completa.get('estoque_atual', 0),
                    'estoque_atual': projecao_completa.get('estoque_atual', 0),
                    'menor_estoque_d7': projecao_completa.get('menor_estoque_d7', 0),
                    'menor_estoque_7d': projecao_completa.get('menor_estoque_d7', 0),  # Adicionar alias
                    'dia_ruptura': projecao_completa.get('dia_ruptura'),
                    'projecao_29_dias': projecao_completa.get('projecao', []),
                    'projecao': projecao_completa.get('projecao', []),  # Adicionar alias
                    'qtd_disponivel': 0,  # Será calculado em workspace_utils
                    'status_ruptura': 'CRÍTICO' if projecao_completa.get('dia_ruptura') else 'OK'
                }
            else:
                resumo_estoque = None
            
            # CORREÇÃO 4: Usar processar_dados_workspace_produto para TODOS os cálculos
            produto_data = processar_dados_workspace_produto(produto, resumo_estoque)
            
            # DEBUG: Log dos dados processados
            logger.info(f"[DEBUG] Produto {produto.cod_produto}:")
            logger.info(f"  - estoque_hoje do produto_data: {produto_data.get('estoque_hoje') if produto_data else 'None'}")
            logger.info(f"  - estoque_atual do resumo: {resumo_estoque.get('estoque_atual') if resumo_estoque else 'None'}")
            logger.info(f"  - estoque do produto original: {getattr(produto, 'estoque_hoje', 'Não tem')}")
            
            if produto_data:
                # Adicionar quantidades de separações
                qtd_separacoes = qtd_por_produto.get(produto.cod_produto, 0)
                produto_data['qtd_pre_separacoes'] = 0  # Não existe mais distinção
                produto_data['qtd_separacoes'] = qtd_separacoes
                produto_data['qtd_saldo'] = produto_data.get('qtd_pedido', 0) - qtd_separacoes
                
                # Adicionar projeções D0-D28 para compatibilidade
                if resumo_estoque and resumo_estoque.get('projecao_29_dias'):
                    for i, valor in enumerate(resumo_estoque['projecao_29_dias']):
                        if i < 29:
                            produto_data[f'estoque_d{i}'] = valor if valor is not None else 0
                
                # Adicionar campos extras que o frontend espera
                produto_data['qtd_saldo_produto_pedido'] = produto_data.get('qtd_pedido', 0)
                produto_data['preco_produto_pedido'] = produto_data.get('preco_unitario', 0)
                produto_data['menor_estoque_produto_d7'] = produto_data.get('menor_estoque_7d', 0)
                produto_data['saldo_estoque_pedido'] = produto_data.get('estoque_data_expedicao', 0)
                produto_data['dia_ruptura'] = resumo_estoque.get('dia_ruptura') if resumo_estoque else None
                produto_data['estoque'] = produto_data.get('estoque_hoje', 0)
                produto_data['estoque_d0'] = produto_data.get('estoque_hoje', 0)
                
                produtos_completos.append(produto_data)
                valor_total += produto_data["qtd_pedido"] * produto_data["preco_unitario"]
        
        tempo_total = (time.time() - inicio) * 1000
        logger.info(f"=== Busca de estoque concluída para pedido {num_pedido} ===")
        logger.info(f"Tempo total: {tempo_total:.0f}ms | Produtos: {len(produtos_completos)} sucesso, {len(produtos_com_erro)} erro")
        
        if produtos_com_erro:
            logger.error(f"Produtos com erro: {produtos_com_erro}")
        
        return jsonify({
            'success': True,
            'produtos': produtos_completos,
            'total': len(produtos_completos),
            'valor_total': valor_total,  # Adicionado para consistência
            'tempo_processamento': tempo_total,
            'produtos_com_erro': len(produtos_com_erro)
        })
        
    except Exception as e:
        tempo_total = (time.time() - inicio) * 1000
        logger.error(f"ERRO FATAL ao buscar estoque completo do pedido {num_pedido} após {tempo_total:.0f}ms: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
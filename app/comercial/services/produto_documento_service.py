"""
Service para buscar e processar produtos de documentos (NF, Separação, Saldo)
================================================================================

Este módulo fornece funções para buscar produtos detalhados de cada tipo de documento:
- NF: Produtos de FaturamentoProduto com cálculos de peso e pallet
- Separação: Produtos de Separacao agrupados por lote
- Saldo: Produtos de CarteiraPrincipal descontando separações não sincronizadas

Autor: Sistema de Fretes
Data: 2025-01-21
"""

from sqlalchemy import func
from app import db
from app.faturamento.models import FaturamentoProduto
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from app.producao.models import CadastroPalletizacao
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ProdutoDocumentoService:
    """Service para buscar produtos detalhados de documentos"""

    @staticmethod
    def obter_produtos_documento(
        tipo_documento: str,
        identificador: str,
        num_pedido: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retorna os produtos de um documento específico.

        Args:
            tipo_documento: Tipo do documento ('NF', 'Separacao', 'Saldo')
            identificador: ID único do documento (numero_nf, separacao_lote_id, ou num_pedido para saldo)
            num_pedido: Número do pedido (opcional, usado para Saldo)

        Returns:
            Dict contendo lista de produtos e totais
        """
        try:
            if tipo_documento == 'NF':
                produtos = ProdutoDocumentoService._obter_produtos_nf(identificador)
            elif tipo_documento == 'Separacao':
                produtos = ProdutoDocumentoService._obter_produtos_separacao(identificador)
            elif tipo_documento == 'Saldo':
                # Para saldo, o identificador é o próprio num_pedido
                produtos = ProdutoDocumentoService._obter_produtos_saldo(identificador)
            else:
                produtos = []

            # Calcular totais
            total_quantidade = sum(p.get('quantidade', 0) for p in produtos)
            total_valor = sum(p.get('valor', 0) for p in produtos)
            total_peso = sum(p.get('peso', 0) for p in produtos)
            total_pallet = sum(p.get('pallet', 0) for p in produtos)

            return {
                'produtos': produtos,
                'totais': {
                    'quantidade': float(total_quantidade),
                    'valor': float(total_valor),
                    'peso': float(total_peso),
                    'pallet': float(total_pallet)
                }
            }

        except Exception as e:
            logger.error(f"Erro ao obter produtos do documento {tipo_documento} {identificador}: {e}")
            return {
                'produtos': [],
                'totais': {
                    'quantidade': 0,
                    'valor': 0,
                    'peso': 0,
                    'pallet': 0
                }
            }

    @staticmethod
    def _obter_produtos_nf(numero_nf: str) -> List[Dict[str, Any]]:
        """
        Busca produtos de uma NF específica.
        OTIMIZADO: Usa LEFT JOIN para buscar palletização em 1 única query.

        Args:
            numero_nf: Número da nota fiscal

        Returns:
            Lista de produtos da NF com cálculos de peso e pallet
        """
        try:
            # OTIMIZAÇÃO: Buscar produtos da NF com LEFT JOIN em CadastroPalletizacao
            # Reduz de N+1 queries para 1 única query
            produtos_nf = db.session.query(
                FaturamentoProduto.cod_produto,
                FaturamentoProduto.nome_produto,
                FaturamentoProduto.qtd_produto_faturado,
                FaturamentoProduto.preco_produto_faturado,
                FaturamentoProduto.valor_produto_faturado,
                CadastroPalletizacao.peso_bruto,
                CadastroPalletizacao.palletizacao
            ).outerjoin(
                CadastroPalletizacao,
                CadastroPalletizacao.cod_produto == FaturamentoProduto.cod_produto
            ).filter(
                FaturamentoProduto.numero_nf == numero_nf,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).all()

            produtos = []
            for produto in produtos_nf:
                # Calcular peso e pallet
                qtd = float(produto.qtd_produto_faturado or 0)

                if produto.peso_bruto:
                    peso_total = qtd * float(produto.peso_bruto or 0)
                    pallet_total = qtd / float(produto.palletizacao) if produto.palletizacao else 0
                else:
                    peso_total = 0
                    pallet_total = 0

                produtos.append({
                    'codigo': produto.cod_produto,
                    'produto': produto.nome_produto,
                    'quantidade': qtd,
                    'preco': float(produto.preco_produto_faturado or 0),
                    'valor': float(produto.valor_produto_faturado or 0),
                    'peso': round(peso_total, 2),
                    'pallet': round(pallet_total, 2)
                })

            return produtos

        except Exception as e:
            logger.error(f"Erro ao buscar produtos da NF {numero_nf}: {e}")
            return []

    @staticmethod
    def _obter_produtos_separacao(separacao_lote_id: str) -> List[Dict[str, Any]]:
        """
        Busca produtos de uma separação específica.

        Args:
            separacao_lote_id: ID do lote de separação

        Returns:
            Lista de produtos da separação
        """
        try:
            # Buscar produtos da separação
            produtos_separacao = db.session.query(
                Separacao.cod_produto,
                Separacao.nome_produto,
                func.sum(Separacao.qtd_saldo).label('qtd_total'),
                func.sum(Separacao.valor_saldo).label('valor_total'),
                func.sum(Separacao.peso).label('peso_total'),
                func.sum(Separacao.pallet).label('pallet_total')
            ).filter(
                Separacao.separacao_lote_id == separacao_lote_id,
                Separacao.sincronizado_nf == False
            ).group_by(
                Separacao.cod_produto,
                Separacao.nome_produto
            ).all()

            produtos = []
            for produto in produtos_separacao:
                qtd = float(produto.qtd_total or 0)
                valor = float(produto.valor_total or 0)

                # Calcular preço unitário
                preco_unitario = valor / qtd if qtd > 0 else 0

                produtos.append({
                    'codigo': produto.cod_produto,
                    'produto': produto.nome_produto,
                    'quantidade': qtd,
                    'preco': round(preco_unitario, 2),
                    'valor': valor,
                    'peso': float(produto.peso_total or 0),
                    'pallet': float(produto.pallet_total or 0)
                })

            return produtos

        except Exception as e:
            logger.error(f"Erro ao buscar produtos da separação {separacao_lote_id}: {e}")
            return []

    @staticmethod
    def _obter_produtos_saldo(num_pedido: str) -> List[Dict[str, Any]]:
        """
        Busca produtos do saldo de um pedido (CarteiraPrincipal - Separações não sincronizadas).
        OTIMIZADO: Usa subquery e LEFT JOIN para reduzir de N+1 queries para 1.

        Args:
            num_pedido: Número do pedido

        Returns:
            Lista de produtos do saldo
        """
        try:
            # OTIMIZAÇÃO: Subquery para calcular total separado por produto
            subquery_separacoes = db.session.query(
                Separacao.cod_produto,
                func.coalesce(func.sum(Separacao.qtd_saldo), 0).label('qtd_separada')
            ).filter(
                Separacao.num_pedido == num_pedido,
                Separacao.sincronizado_nf == False
            ).group_by(Separacao.cod_produto).subquery()

            # OTIMIZAÇÃO: Query única com LEFT JOINs
            # - LEFT JOIN com separações para obter qtd_separada
            # - LEFT JOIN com palletização para obter peso/pallet
            produtos_carteira = db.session.query(
                CarteiraPrincipal.cod_produto,
                CarteiraPrincipal.nome_produto,
                CarteiraPrincipal.qtd_saldo_produto_pedido,
                CarteiraPrincipal.preco_produto_pedido,
                func.coalesce(subquery_separacoes.c.qtd_separada, 0).label('qtd_separada'),
                CadastroPalletizacao.peso_bruto,
                CadastroPalletizacao.palletizacao
            ).outerjoin(
                subquery_separacoes,
                subquery_separacoes.c.cod_produto == CarteiraPrincipal.cod_produto
            ).outerjoin(
                CadastroPalletizacao,
                CadastroPalletizacao.cod_produto == CarteiraPrincipal.cod_produto
            ).filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).all()

            produtos = []
            for produto_cart in produtos_carteira:
                # Calcular saldo real (carteira - separações não sincronizadas)
                qtd_saldo = float(produto_cart.qtd_saldo_produto_pedido or 0) - float(produto_cart.qtd_separada or 0)

                # Só incluir se houver saldo positivo
                if qtd_saldo <= 0:
                    continue

                # Calcular valores
                preco = float(produto_cart.preco_produto_pedido or 0)
                valor_total = preco * qtd_saldo

                if produto_cart.peso_bruto:
                    peso_total = qtd_saldo * float(produto_cart.peso_bruto or 0)
                    pallet_total = qtd_saldo / float(produto_cart.palletizacao) if produto_cart.palletizacao else 0
                else:
                    peso_total = 0
                    pallet_total = 0

                produtos.append({
                    'codigo': produto_cart.cod_produto,
                    'produto': produto_cart.nome_produto,
                    'quantidade': round(qtd_saldo, 2),
                    'preco': preco,
                    'valor': round(valor_total, 2),
                    'peso': round(peso_total, 2),
                    'pallet': round(pallet_total, 2)
                })

            return produtos

        except Exception as e:
            logger.error(f"Erro ao buscar produtos do saldo do pedido {num_pedido}: {e}")
            return []

    @staticmethod
    def _formatar_valor(valor: Any) -> str:
        """
        Formata um valor para exibição.

        Args:
            valor: Valor a ser formatado

        Returns:
            String formatada ou '-' se for 0 ou None
        """
        if valor is None or valor == 0:
            return '-'
        return str(round(float(valor), 2))
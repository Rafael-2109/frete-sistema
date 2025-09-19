"""
Service para debug de cálculos de pedidos
==========================================

Este módulo ajuda a diagnosticar problemas nos cálculos de valores dos pedidos.

Autor: Sistema de Fretes
Data: 2025-01-19
"""

from sqlalchemy import func, distinct
from app import db
from app.carteira.models import CarteiraPrincipal
from app.faturamento.models import FaturamentoProduto
from app.monitoramento.models import EntregaMonitorada
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PedidoDebugService:
    """Service para debug de valores de pedidos"""

    @staticmethod
    def debug_valores_pedido(cnpj: str, num_pedido: str):
        """
        Retorna informações detalhadas sobre os cálculos de um pedido
        para ajudar a identificar divergências.
        """
        resultado = {
            'num_pedido': num_pedido,
            'cnpj': cnpj,
            'carteira_principal': {},
            'faturamento': {},
            'entregas': {},
            'resumo': {}
        }

        try:
            # 1. Debug CarteiraPrincipal - Listar TODOS os itens
            itens_carteira = db.session.query(
                CarteiraPrincipal.cod_produto,
                CarteiraPrincipal.nome_produto,
                CarteiraPrincipal.qtd_produto_pedido,
                CarteiraPrincipal.preco_produto_pedido,
                CarteiraPrincipal.qtd_saldo_produto_pedido,
                CarteiraPrincipal.data_pedido,
                CarteiraPrincipal.incoterm,
                (CarteiraPrincipal.qtd_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_item'),
                (CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_saldo_item')
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.num_pedido == num_pedido
            ).all()

            # Processar itens da carteira
            itens_lista = []
            total_pedido = Decimal('0')
            total_saldo = Decimal('0')

            for item in itens_carteira:
                valor_item = Decimal(str(item.valor_item or 0))
                valor_saldo = Decimal(str(item.valor_saldo_item or 0))

                itens_lista.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_produto': float(item.qtd_produto_pedido or 0),
                    'preco': float(item.preco_produto_pedido or 0),
                    'qtd_saldo': float(item.qtd_saldo_produto_pedido or 0),
                    'valor_item': float(valor_item),
                    'valor_saldo': float(valor_saldo),
                    'data_pedido': item.data_pedido.strftime('%d/%m/%Y') if item.data_pedido else None,
                    'incoterm': item.incoterm
                })

                total_pedido += valor_item
                total_saldo += valor_saldo

            resultado['carteira_principal'] = {
                'qtd_itens': len(itens_lista),
                'itens': itens_lista,
                'valor_total_calculado': float(total_pedido),
                'valor_saldo_calculado': float(total_saldo)
            }

            # Verificar também com query agregada
            valor_agregado = db.session.query(
                func.sum(
                    CarteiraPrincipal.qtd_produto_pedido *
                    CarteiraPrincipal.preco_produto_pedido
                ).label('valor_total'),
                func.sum(
                    CarteiraPrincipal.qtd_saldo_produto_pedido *
                    CarteiraPrincipal.preco_produto_pedido
                ).label('valor_saldo'),
                func.count(CarteiraPrincipal.id).label('total_linhas')
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.num_pedido == num_pedido
            ).first()

            if valor_agregado:
                resultado['carteira_principal']['valor_total_query'] = float(valor_agregado.valor_total or 0)
                resultado['carteira_principal']['valor_saldo_query'] = float(valor_agregado.valor_saldo or 0)
                resultado['carteira_principal']['total_linhas'] = valor_agregado.total_linhas

            # 2. Debug FaturamentoProduto
            itens_faturamento = db.session.query(
                FaturamentoProduto.numero_nf,
                FaturamentoProduto.cod_produto,
                FaturamentoProduto.nome_produto,
                FaturamentoProduto.qtd_produto_faturado,
                FaturamentoProduto.preco_produto_faturado,
                FaturamentoProduto.valor_produto_faturado,
                FaturamentoProduto.incoterm
            ).filter(
                FaturamentoProduto.cnpj_cliente == cnpj,
                FaturamentoProduto.origem == num_pedido
            ).all()

            # Processar itens faturados
            faturamento_lista = []
            total_faturado = Decimal('0')
            nfs_distintas = set()

            for item in itens_faturamento:
                valor_faturado = Decimal(str(item.valor_produto_faturado or 0))

                faturamento_lista.append({
                    'numero_nf': item.numero_nf,
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_faturada': float(item.qtd_produto_faturado or 0),
                    'preco_faturado': float(item.preco_produto_faturado or 0),
                    'valor_faturado': float(valor_faturado),
                    'incoterm': item.incoterm
                })

                total_faturado += valor_faturado
                if item.numero_nf:
                    nfs_distintas.add(item.numero_nf)

            resultado['faturamento'] = {
                'qtd_itens': len(faturamento_lista),
                'qtd_nfs': len(nfs_distintas),
                'nfs': list(nfs_distintas),
                'itens': faturamento_lista,
                'valor_total_faturado': float(total_faturado)
            }

            # Verificar com query agregada
            valor_faturado_agregado = db.session.query(
                func.sum(FaturamentoProduto.valor_produto_faturado).label('total'),
                func.count(distinct(FaturamentoProduto.numero_nf)).label('qtd_nfs')
            ).filter(
                FaturamentoProduto.cnpj_cliente == cnpj,
                FaturamentoProduto.origem == num_pedido
            ).first()

            if valor_faturado_agregado:
                resultado['faturamento']['valor_total_query'] = float(valor_faturado_agregado.total or 0)
                resultado['faturamento']['qtd_nfs_query'] = valor_faturado_agregado.qtd_nfs

            # 3. Debug Entregas (se houver NFs)
            if nfs_distintas:
                entregas = db.session.query(
                    EntregaMonitorada.numero_nf,
                    EntregaMonitorada.valor_nf,
                    EntregaMonitorada.status_finalizacao,
                    EntregaMonitorada.data_entrega_prevista
                ).filter(
                    EntregaMonitorada.numero_nf.in_(list(nfs_distintas))
                ).all()

                entregas_lista = []
                total_entregue = Decimal('0')

                for entrega in entregas:
                    is_entregue = entrega.status_finalizacao == 'Entregue'
                    valor_nf = Decimal(str(entrega.valor_nf or 0))

                    entregas_lista.append({
                        'numero_nf': entrega.numero_nf,
                        'valor_nf': float(valor_nf),
                        'status': entrega.status_finalizacao,
                        'entregue': is_entregue,
                        'data_prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y') if entrega.data_entrega_prevista else None
                    })

                    if is_entregue:
                        total_entregue += valor_nf

                resultado['entregas'] = {
                    'qtd_nfs_monitoradas': len(entregas_lista),
                    'entregas': entregas_lista,
                    'valor_total_entregue': float(total_entregue)
                }

            # 4. Resumo e Diagnóstico
            valor_total_pedido = resultado['carteira_principal'].get('valor_total_calculado', 0)
            valor_total_faturado = resultado['faturamento'].get('valor_total_faturado', 0)
            valor_total_entregue = resultado['entregas'].get('valor_total_entregue', 0)

            # Se não tem valor na carteira, usar valor faturado como total
            if valor_total_pedido == 0 and valor_total_faturado > 0:
                valor_total_pedido = valor_total_faturado

            resultado['resumo'] = {
                'valor_total_pedido': valor_total_pedido,
                'valor_total_faturado': valor_total_faturado,
                'valor_total_entregue': valor_total_entregue,
                'saldo_carteira': resultado['carteira_principal'].get('valor_saldo_calculado', 0),
                'saldo_calculado': max(0, valor_total_pedido - valor_total_faturado)
            }

            # Adicionar diagnóstico
            resultado['diagnostico'] = []

            if resultado['carteira_principal'].get('valor_total_calculado', 0) != resultado['carteira_principal'].get('valor_total_query', 0):
                resultado['diagnostico'].append("⚠️ Divergência entre cálculo manual e query agregada na CarteiraPrincipal")

            if valor_total_faturado > valor_total_pedido and valor_total_pedido > 0:
                resultado['diagnostico'].append(f"⚠️ Valor faturado ({valor_total_faturado}) maior que valor do pedido ({valor_total_pedido})")

            if resultado['carteira_principal'].get('qtd_itens', 0) == 0 and resultado['faturamento'].get('qtd_itens', 0) > 0:
                resultado['diagnostico'].append("ℹ️ Pedido não está mais na carteira, apenas no faturamento")

            return resultado

        except Exception as e:
            logger.error(f"Erro no debug do pedido {num_pedido}: {e}")
            resultado['erro'] = str(e)
            return resultado
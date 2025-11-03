"""
Script de Teste: Importação Completa de Compras
===============================================

Testa a importação completa do fluxo:
1. Requisições de Compra (purchase.request.line)
2. Pedidos de Compra (purchase.order.line)
3. Alocações (purchase.request.allocation)

Valida relacionamentos N:N entre Requisições e Pedidos

Autor: Sistema de Fretes
Data: 01/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.odoo.services.requisicao_compras_service_otimizado import RequisicaoComprasServiceOtimizado
from app.odoo.services.pedido_compras_service import PedidoComprasServiceOtimizado
from app.odoo.services.alocacao_compras_service import AlocacaoComprasServiceOtimizado
from app.manufatura.models import RequisicaoCompras, PedidoCompras, RequisicaoCompraAlocacao
from sqlalchemy import func


def exibir_estatisticas():
    """Exibe estatísticas do banco de dados"""
    print()
    print("=" * 80)
    print("📊 ESTATÍSTICAS DO BANCO DE DADOS")
    print("=" * 80)
    print()

    # Requisições
    total_requisicoes = RequisicaoCompras.query.count()
    requisicoes_odoo = RequisicaoCompras.query.filter_by(importado_odoo=True).count()
    print(f"📋 Requisições de Compra:")
    print(f"   Total: {total_requisicoes}")
    print(f"   Importadas do Odoo: {requisicoes_odoo}")
    print()

    # Pedidos
    total_pedidos = PedidoCompras.query.count()
    pedidos_odoo = PedidoCompras.query.filter_by(importado_odoo=True).count()
    print(f"📦 Pedidos de Compra:")
    print(f"   Total: {total_pedidos}")
    print(f"   Importados do Odoo: {pedidos_odoo}")
    print()

    # Alocações
    total_alocacoes = RequisicaoCompraAlocacao.query.count()
    print(f"🔗 Alocações (N:N):")
    print(f"   Total: {total_alocacoes}")
    print()

    # Relacionamentos
    if total_alocacoes > 0:
        # Requisições com alocações
        requisicoes_com_alocacao = db.session.query(
            func.count(func.distinct(RequisicaoCompraAlocacao.requisicao_compra_id))
        ).scalar()

        # Pedidos com alocações
        pedidos_com_alocacao = db.session.query(
            func.count(func.distinct(RequisicaoCompraAlocacao.pedido_compra_id))
        ).filter(RequisicaoCompraAlocacao.pedido_compra_id.isnot(None)).scalar()

        # Alocações sem pedido
        alocacoes_sem_pedido = RequisicaoCompraAlocacao.query.filter_by(
            pedido_compra_id=None
        ).count()

        print(f"🔗 Relacionamentos:")
        print(f"   Requisições com alocações: {requisicoes_com_alocacao}")
        print(f"   Pedidos com alocações: {pedidos_com_alocacao}")
        print(f"   Alocações sem pedido: {alocacoes_sem_pedido}")
        print()


def exibir_exemplos_relacionamentos():
    """Exibe exemplos de relacionamentos"""
    print()
    print("=" * 80)
    print("📋 EXEMPLOS DE RELACIONAMENTOS")
    print("=" * 80)
    print()

    # Exemplo 1: Requisição → Alocações → Pedidos
    requisicao = RequisicaoCompras.query.join(
        RequisicaoCompraAlocacao
    ).first()

    if requisicao:
        print(f"📌 Exemplo 1: Requisição → Alocações → Pedidos")
        print(f"   Requisição: {requisicao.num_requisicao}")
        print(f"   Produto: {requisicao.cod_produto} - {requisicao.nome_produto}")
        print(f"   Quantidade requisitada: {requisicao.qtd_produto_requisicao}")
        print()

        # Buscar alocações via relationship
        if hasattr(requisicao, 'alocacoes') and requisicao.alocacoes:
            print(f"   Alocações ({len(requisicao.alocacoes)}):")
            for aloc in requisicao.alocacoes[:5]:  # Mostrar até 5
                pedido_info = f"Pedido: {aloc.pedido.num_pedido}" if aloc.pedido else "SEM PEDIDO"
                print(f"      - {pedido_info}")
                print(f"        Qtd alocada: {aloc.qtd_alocada}")
                print(f"        Qtd aberta: {aloc.qtd_aberta}")
                print(f"        Status: {aloc.purchase_state}")
                print()
        else:
            print("   ⚠️  Nenhuma alocação encontrada")

    print()

    # Exemplo 2: Pedido → Alocações → Requisições
    pedido = PedidoCompras.query.join(
        RequisicaoCompraAlocacao,
        RequisicaoCompraAlocacao.pedido_compra_id == PedidoCompras.id
    ).first()

    if pedido:
        print(f"📌 Exemplo 2: Pedido → Alocações → Requisições")
        print(f"   Pedido: {pedido.num_pedido}")
        print(f"   Fornecedor: {pedido.raz_social or 'N/A'}")
        print(f"   Produto: {pedido.cod_produto} - {pedido.nome_produto}")
        print(f"   Quantidade: {pedido.qtd_produto_pedido}")
        print(f"   Preço unitário: R$ {pedido.preco_produto_pedido}")
        print()

        # Buscar alocações via relationship
        if hasattr(pedido, 'alocacoes') and pedido.alocacoes:
            print(f"   Alocações ({len(pedido.alocacoes)}):")
            for aloc in pedido.alocacoes[:5]:  # Mostrar até 5
                print(f"      - Requisição: {aloc.requisicao.num_requisicao}")
                print(f"        Qtd alocada: {aloc.qtd_alocada}")
                print(f"        % atendimento: {aloc.percentual_alocado()}%")
                print()
        else:
            print("   ⚠️  Nenhuma alocação encontrada")

    print()


def teste_importacao_completa():
    """
    Testa importação completa do fluxo de compras
    """
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("🧪 TESTE DE IMPORTAÇÃO COMPLETA - COMPRAS")
        print("=" * 80)
        print()

        # Exibir estatísticas ANTES
        print("📊 ANTES DA IMPORTAÇÃO:")
        exibir_estatisticas()

        # PASSO 1: Importar Requisições
        print()
        print("=" * 80)
        print("PASSO 1: Importando Requisições de Compra")
        print("=" * 80)
        print()

        service_requisicoes = RequisicaoComprasServiceOtimizado()
        resultado_req = service_requisicoes.sincronizar_requisicoes_incremental(
            minutos_janela=10080,  # 7 dias
            primeira_execucao=False
        )

        print()
        print(f"✅ Resultado Requisições:")
        print(f"   Novas: {resultado_req.get('requisicoes_novas', 0)}")
        print(f"   Atualizadas: {resultado_req.get('requisicoes_atualizadas', 0)}")
        print(f"   Linhas processadas: {resultado_req.get('linhas_processadas', 0)}")
        print(f"   Tempo: {resultado_req.get('tempo_execucao', 0):.2f}s")

        # PASSO 2: Importar Pedidos
        print()
        print("=" * 80)
        print("PASSO 2: Importando Pedidos de Compra")
        print("=" * 80)
        print()

        service_pedidos = PedidoComprasServiceOtimizado()
        resultado_ped = service_pedidos.sincronizar_pedidos_incremental(
            minutos_janela=10080,  # 7 dias
            primeira_execucao=False
        )

        print()
        print(f"✅ Resultado Pedidos:")
        print(f"   Novos: {resultado_ped.get('pedidos_novos', 0)}")
        print(f"   Atualizados: {resultado_ped.get('pedidos_atualizados', 0)}")
        print(f"   Linhas processadas: {resultado_ped.get('linhas_processadas', 0)}")
        print(f"   Tempo: {resultado_ped.get('tempo_execucao', 0):.2f}s")

        # PASSO 3: Importar Alocações
        print()
        print("=" * 80)
        print("PASSO 3: Importando Alocações (Relacionamentos N:N)")
        print("=" * 80)
        print()

        service_alocacoes = AlocacaoComprasServiceOtimizado()
        resultado_aloc = service_alocacoes.sincronizar_alocacoes_incremental(
            minutos_janela=10080,  # 7 dias
            primeira_execucao=False
        )

        print()
        print(f"✅ Resultado Alocações:")
        print(f"   Novas: {resultado_aloc.get('alocacoes_novas', 0)}")
        print(f"   Atualizadas: {resultado_aloc.get('alocacoes_atualizadas', 0)}")
        print(f"   Ignoradas: {resultado_aloc.get('alocacoes_ignoradas', 0)}")
        print(f"   Tempo: {resultado_aloc.get('tempo_execucao', 0):.2f}s")

        # Exibir estatísticas DEPOIS
        print()
        print("📊 DEPOIS DA IMPORTAÇÃO:")
        exibir_estatisticas()

        # Exibir exemplos de relacionamentos
        exibir_exemplos_relacionamentos()

        # Resumo final
        print()
        print("=" * 80)
        print("✅ TESTE CONCLUÍDO COM SUCESSO")
        print("=" * 80)
        print()
        print("📋 Resumo:")
        print(f"   Requisições: +{resultado_req.get('requisicoes_novas', 0)} novas")
        print(f"   Pedidos: +{resultado_ped.get('pedidos_novos', 0)} novos")
        print(f"   Alocações: +{resultado_aloc.get('alocacoes_novas', 0)} novas")
        print()
        tempo_total = (
            resultado_req.get('tempo_execucao', 0) +
            resultado_ped.get('tempo_execucao', 0) +
            resultado_aloc.get('tempo_execucao', 0)
        )
        print(f"   ⏱️  Tempo total: {tempo_total:.2f}s")
        print()


if __name__ == '__main__':
    teste_importacao_completa()

#!/usr/bin/env python3
"""
Script para VISUALIZAR onde adicionar filtro de tipo de pedido
=================================================================

Este script mostra as mudanças necessárias no carteira_service.py
para filtrar apenas pedidos de Venda e Bonificação.

NÃO FAZ ALTERAÇÕES - apenas mostra o que seria alterado.
"""

def mostrar_correcoes():
    """
    Mostra as correções necessárias
    """
    print("="*80)
    print("🔍 ANÁLISE DO PROBLEMA")
    print("="*80)

    print("\n❌ PROBLEMA IDENTIFICADO:")
    print("   - CarteiraPrincipal está importando TODOS os tipos de pedido")
    print("   - Incluindo: Transferências internas, devoluções, etc")
    print("   - Faltando filtro de tipo de pedido no carteira_service.py")

    print("\n✅ SOLUÇÃO PROPOSTA:")
    print("   - Adicionar filtro para aceitar APENAS:")
    print("     • 'venda' = Saída: Venda")
    print("     • 'bonificacao' = Saída: Remessa p/ Bonificação")

    print("\n📝 ALTERAÇÕES NECESSÁRIAS EM carteira_service.py:")
    print("="*80)

    # LOCAL 1: Modo incremental com datas (linha ~114)
    print("\n1️⃣ LINHA ~114 - Modo incremental com datas:")
    print("   ANTES:")
    print("""
    domain = [
        ('order_id.state', 'in', ['draft', 'sent', 'sale', 'done'])
    ]
    """)
    print("   DEPOIS:")
    print("""
    domain = [
        '&',  # AND entre os filtros
        ('order_id.state', 'in', ['draft', 'sent', 'sale', 'done']),
        '|',  # OR entre tipos de pedido
        ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
        ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao')
    ]
    """)

    # LOCAL 2: Modo incremental normal (linha ~124)
    print("\n2️⃣ LINHA ~124 - Modo incremental normal:")
    print("   ANTES:")
    print("""
    domain = [
        ('order_id.write_date', '>=', data_corte.isoformat()),
        ('order_id.write_date', '<=', momento_atual.isoformat()),
        ('order_id.state', 'in', ['draft', 'sent', 'sale'])
    ]
    """)
    print("   DEPOIS:")
    print("""
    domain = [
        '&',
        ('order_id.write_date', '>=', data_corte.isoformat()),
        ('order_id.write_date', '<=', momento_atual.isoformat()),
        ('order_id.state', 'in', ['draft', 'sent', 'sale']),
        '|',  # OR entre tipos de pedido
        ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
        ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao')
    ]
    """)

    # LOCAL 3: Modo tradicional com pedidos existentes (linha ~134)
    print("\n3️⃣ LINHA ~134 - Modo tradicional com pedidos existentes:")
    print("   ANTES:")
    print("""
    domain = [
        '&',
        ('order_id.state', 'in', ['draft', 'sent', 'sale', 'invoiced']),
        '|',
        ('qty_saldo', '>', 0),
        ('order_id.name', 'in', list(pedidos_na_carteira))
    ]
    """)
    print("   DEPOIS:")
    print("""
    domain = [
        '&',  # AND entre todos os filtros
        ('order_id.state', 'in', ['draft', 'sent', 'sale', 'invoiced']),
        '|',  # OR entre tipos de pedido
        ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
        ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
        '|',  # OR entre saldo e pedidos existentes
        ('qty_saldo', '>', 0),
        ('order_id.name', 'in', list(pedidos_na_carteira))
    ]
    """)

    # LOCAL 4: Modo tradicional carteira vazia (linha ~144)
    print("\n4️⃣ LINHA ~144 - Modo tradicional carteira vazia:")
    print("   ANTES:")
    print("""
    domain = [
        ('qty_saldo', '>', 0),
        ('order_id.state', 'in', ['draft', 'sent', 'sale'])
    ]
    """)
    print("   DEPOIS:")
    print("""
    domain = [
        '&',
        ('qty_saldo', '>', 0),
        ('order_id.state', 'in', ['draft', 'sent', 'sale']),
        '|',  # OR entre tipos de pedido
        ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
        ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao')
    ]
    """)

    print("\n" + "="*80)
    print("📊 TAMBÉM PRECISA ATUALIZAR O SCRIPT SEM FILTRO")
    print("="*80)

    print("\nNo arquivo importar_historico_sem_filtro.py, linha ~254:")
    print("   ANTES:")
    print("""
    domain = [
        ('order_id.date_order', '>=', data_inicio),
        ('order_id.date_order', '<=', data_fim),
        ('order_id.state', 'in', ['draft', 'sent', 'sale', 'done'])
    ]
    """)
    print("   DEPOIS:")
    print("""
    domain = [
        ('order_id.date_order', '>=', data_inicio),
        ('order_id.date_order', '<=', data_fim),
        ('order_id.state', 'in', ['draft', 'sent', 'sale', 'done']),
        '|',  # OR entre tipos de pedido
        ('order_id.l10n_br_tipo_pedido', '=', 'venda'),
        ('order_id.l10n_br_tipo_pedido', '=', 'bonificacao')
    ]
    """)

    print("\n" + "="*80)
    print("💡 IMPACTO ESPERADO")
    print("="*80)
    print("\n✅ APÓS APLICAR AS CORREÇÕES:")
    print("   • NÃO importará mais transferências internas")
    print("   • NÃO importará devoluções")
    print("   • NÃO importará outros tipos não desejados")
    print("   • APENAS pedidos de Venda e Bonificação")

    print("\n⚠️ IMPORTANTE:")
    print("   • Isso afetará TODOS os processos:")
    print("     - Importação histórica")
    print("     - Scheduler de sincronização")
    print("     - Busca manual de carteira")

    print("\n🔧 PARA APLICAR AS CORREÇÕES:")
    print("   1. Confirme que os valores 'venda' e 'bonificacao' estão corretos")
    print("   2. Execute o script de aplicação das correções")
    print("   3. Teste primeiro em ambiente local")
    print("   4. Depois aplique em produção")

    print("\n" + "="*80)
    print("✅ ANÁLISE CONCLUÍDA")
    print("="*80)


if __name__ == "__main__":
    mostrar_correcoes()
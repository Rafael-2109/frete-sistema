#!/usr/bin/env python3
"""
Script para testar e debugar os valores dos pedidos
"""

from app import create_app
from app.comercial.services.pedido_debug_service import PedidoDebugService
import json

def debug_pedido(cnpj, num_pedido):
    """Debug de um pedido específico"""

    print(f"\n{'='*80}")
    print(f"DEBUG DO PEDIDO: {num_pedido}")
    print(f"CNPJ: {cnpj}")
    print(f"{'='*80}")

    resultado = PedidoDebugService.debug_valores_pedido(cnpj, num_pedido)

    # Mostrar resultados formatados
    print("\n📊 CARTEIRA PRINCIPAL:")
    cart = resultado['carteira_principal']
    print(f"  - Quantidade de itens: {cart.get('qtd_itens', 0)}")
    print(f"  - Valor Total (calculado): R$ {cart.get('valor_total_calculado', 0):,.2f}")
    print(f"  - Valor Total (query): R$ {cart.get('valor_total_query', 0):,.2f}")
    print(f"  - Valor Saldo: R$ {cart.get('valor_saldo_calculado', 0):,.2f}")

    if cart.get('itens'):
        print("\n  Detalhamento dos itens:")
        for i, item in enumerate(cart['itens'], 1):
            print(f"    {i}. {item['cod_produto']} - {item['nome_produto'][:30]}")
            print(f"       Qtd: {item['qtd_produto']:.2f} x R$ {item['preco']:.2f} = R$ {item['valor_item']:,.2f}")

    print("\n💰 FATURAMENTO:")
    fat = resultado['faturamento']
    print(f"  - Quantidade de itens: {fat.get('qtd_itens', 0)}")
    print(f"  - Quantidade de NFs: {fat.get('qtd_nfs', 0)}")
    print(f"  - Valor Total Faturado: R$ {fat.get('valor_total_faturado', 0):,.2f}")

    print("\n📦 ENTREGAS:")
    ent = resultado.get('entregas', {})
    if ent:
        print(f"  - NFs Monitoradas: {ent.get('qtd_nfs_monitoradas', 0)}")
        print(f"  - Valor Total Entregue: R$ {ent.get('valor_total_entregue', 0):,.2f}")
    else:
        print("  - Sem dados de entrega")

    print("\n📈 RESUMO:")
    res = resultado['resumo']
    print(f"  - Valor Total do Pedido: R$ {res['valor_total_pedido']:,.2f}")
    print(f"  - Valor Total Faturado: R$ {res['valor_total_faturado']:,.2f}")
    print(f"  - Valor Total Entregue: R$ {res['valor_total_entregue']:,.2f}")
    print(f"  - Saldo em Carteira: R$ {res['saldo_carteira']:,.2f}")

    if resultado.get('diagnostico'):
        print("\n⚠️ DIAGNÓSTICO:")
        for msg in resultado['diagnostico']:
            print(f"  {msg}")

    # Salvar JSON completo para análise
    filename = f"debug_{num_pedido}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 Debug completo salvo em: {filename}")

    return resultado

if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        # Testar os pedidos problemáticos
        print("\n" + "="*80)
        print("TESTANDO PEDIDOS COM PROBLEMAS IDENTIFICADOS")
        print("="*80)

        # Pedido 1: VCD2542978
        debug_pedido('75.315.333/0183-18', 'VCD2542978')

        # Pedido 2: VCD2520538
        debug_pedido('75.315.333/0183-18', 'VCD2520538')

        print("\n" + "="*80)
        print("DEBUG CONCLUÍDO - Verifique os arquivos JSON gerados")
        print("="*80)
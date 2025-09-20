#!/usr/bin/env python3
"""
Script para testar a estratégia simplificada de sincronização de faturamento
Busca apenas NFs criadas nas últimas 26 horas
"""

import sys
from datetime import datetime

def testar_estrategia_simples():
    """Testa a estratégia simplificada de busca de NFs"""

    print("="*60)
    print("TESTE DA ESTRATÉGIA SIMPLIFICADA DE SINCRONIZAÇÃO")
    print("="*60)

    try:
        from app import create_app
        from app.odoo.services.faturamento_service import FaturamentoService

        app = create_app()
        with app.app_context():
            print("\n1. Testando sincronização com estratégia simplificada...")
            print("   - Busca: NFs criadas nas últimas 26 horas")
            print("   - Motivo: Só NFs com menos de 24h podem ser canceladas")

            service = FaturamentoService()

            # Testar o método otimizado diretamente
            print("\n2. Executando busca otimizada em modo incremental...")
            resultado = service.obter_faturamento_otimizado(
                usar_filtro_postado=False,  # Não filtrar por posted para pegar canceladas
                limite=0,
                modo_incremental=True,
                minutos_janela=40  # Não usado na estratégia simplificada
            )

            if resultado['sucesso']:
                print("\n✅ Busca executada com sucesso!")

                stats = resultado.get('estatisticas', {})
                print(f"\n📊 ESTATÍSTICAS:")
                print(f"   - Total de linhas do Odoo: {stats.get('total_linhas_odoo', 0)}")
                print(f"   - Janela de busca: {stats.get('janela_horas', 0)} horas")
                print(f"   - Registros processados: {resultado.get('total_registros', 0)}")

                # Mostrar algumas NFs como exemplo
                dados = resultado.get('dados', [])
                if dados:
                    print(f"\n📋 Exemplos de NFs encontradas (mostrando até 10):")

                    nfs_vistas = set()
                    contador = 0
                    for item in dados:
                        nf = item.get('numero_nf')
                        status = item.get('status_nf', 'N/A')
                        if nf and nf not in nfs_vistas and contador < 10:
                            nfs_vistas.add(nf)
                            contador += 1
                            print(f"   - NF {nf}: {item.get('nome_cliente', 'N/A')} ({status})")

                    # Contar por status
                    status_count = {}
                    for item in dados:
                        status = item.get('status_nf', 'N/A')
                        status_count[status] = status_count.get(status, 0) + 1

                    print(f"\n📊 Distribuição por Status:")
                    for status, count in status_count.items():
                        print(f"   - {status}: {count} itens")

            else:
                print(f"\n❌ Erro: {resultado.get('erro')}")

            # Testar sincronização completa
            print("\n3. Testando sincronização incremental completa...")
            resultado_completo = service.sincronizar_faturamento_incremental(
                minutos_janela=40,  # Não usado
                primeira_execucao=False
            )

            if resultado_completo.get('sucesso'):
                print("\n✅ Sincronização completa executada!")
                print(f"   - Novos: {resultado_completo.get('registros_novos', 0)}")
                print(f"   - Atualizados: {resultado_completo.get('registros_atualizados', 0)}")
                print(f"   - Tempo: {resultado_completo.get('tempo_execucao', 0):.2f}s")

                # Verificar se pegou NFs antigas
                print("\n4. Verificando se trouxe NFs antigas...")

                # Buscar uma NF antiga específica para testar
                from app.faturamento.models import FaturamentoProduto
                nf_antiga = FaturamentoProduto.query.filter_by(numero_nf='132656').first()
                if nf_antiga:
                    print(f"   ⚠️ NF 132656 (antiga) está no banco: {nf_antiga.updated_at}")
                else:
                    print(f"   ✅ NF 132656 (antiga) não foi sincronizada")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    sucesso = testar_estrategia_simples()
    sys.exit(0 if sucesso else 1)
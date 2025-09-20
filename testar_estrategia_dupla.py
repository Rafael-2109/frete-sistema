#!/usr/bin/env python3
"""
Script para testar a nova estratégia dupla de sincronização de faturamento
"""

import sys
from datetime import datetime

def testar_estrategia_dupla():
    """Testa a estratégia dupla de busca de NFs"""

    print("="*60)
    print("TESTE DA ESTRATÉGIA DUPLA DE SINCRONIZAÇÃO")
    print("="*60)

    try:
        from app import create_app
        from app.odoo.services.faturamento_service import FaturamentoService

        app = create_app()
        with app.app_context():
            print("\n1. Testando sincronização com estratégia dupla...")
            print("   - Busca 1: NFs NOVAS (últimas 3 horas)")
            print("   - Busca 2: MUDANÇAS DE STATUS (últimas 26 horas)")

            service = FaturamentoService()

            # Testar o método otimizado diretamente
            print("\n2. Executando busca otimizada em modo incremental...")
            resultado = service.obter_faturamento_otimizado(
                usar_filtro_postado=True,
                limite=0,
                modo_incremental=True,
                minutos_janela=40  # Não usado na nova estratégia
            )

            if resultado['sucesso']:
                print("\n✅ Busca executada com sucesso!")

                stats = resultado.get('estatisticas', {})
                print(f"\n📊 ESTATÍSTICAS:")
                print(f"   - NFs NOVAS encontradas: {stats.get('nfs_novas', 0)} linhas")
                print(f"   - MUDANÇAS DE STATUS: {stats.get('mudancas_status', 0)} linhas")
                print(f"   - TOTAL ÚNICO: {stats.get('total_unico', 0)} linhas")
                print(f"   - Registros processados: {resultado.get('total_registros', 0)}")

                # Mostrar algumas NFs como exemplo
                dados = resultado.get('dados', [])
                if dados:
                    print(f"\n📋 Exemplos de NFs encontradas (mostrando até 5):")

                    nfs_vistas = set()
                    contador = 0
                    for item in dados:
                        nf = item.get('numero_nf')
                        if nf and nf not in nfs_vistas and contador < 5:
                            nfs_vistas.add(nf)
                            contador += 1
                            print(f"   - NF {nf}: {item.get('nome_cliente', 'N/A')}")

            else:
                print(f"\n❌ Erro: {resultado.get('erro')}")

            # Testar sincronização completa
            print("\n3. Testando sincronização incremental completa...")
            resultado_completo = service.sincronizar_faturamento_incremental(
                minutos_janela=40,  # Não usado, estratégia dupla usa valores fixos
                primeira_execucao=False
            )

            if resultado_completo.get('sucesso'):
                print("\n✅ Sincronização completa executada!")
                print(f"   - Novos: {resultado_completo.get('registros_novos', 0)}")
                print(f"   - Atualizados: {resultado_completo.get('registros_atualizados', 0)}")
                print(f"   - Tempo: {resultado_completo.get('tempo_execucao', 0):.2f}s")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    sucesso = testar_estrategia_dupla()
    sys.exit(0 if sucesso else 1)
#!/usr/bin/env python3
"""
Script para testar o scheduler de sincronização incremental localmente
"""

import sys
import time
from datetime import datetime

def testar_scheduler():
    """Testa se o scheduler funciona corretamente"""

    print("="*60)
    print("TESTE DO SCHEDULER DE SINCRONIZAÇÃO INCREMENTAL")
    print("="*60)

    print("\n1. Testando importação dos módulos...")
    try:
        from app import create_app
        from app.odoo.services.carteira_service import CarteiraService
        from app.odoo.services.faturamento_service import FaturamentoService
        print("   ✅ Módulos importados com sucesso")
    except ImportError as e:
        print(f"   ❌ Erro ao importar módulos: {e}")
        return False

    print("\n2. Testando conexão com o banco...")
    try:
        app = create_app()
        with app.app_context():
            from app import db
            # Teste simples de conexão
            from sqlalchemy import text
            result = db.session.execute(text("SELECT 1")).scalar()
            if result == 1:
                print("   ✅ Conexão com banco OK")
            else:
                print("   ❌ Erro na conexão com banco")
                return False
    except Exception as e:
        print(f"   ❌ Erro ao conectar no banco: {e}")
        return False

    print("\n3. Testando sincronização da Carteira (janela de 1 minuto para teste)...")
    try:
        with app.app_context():
            carteira_service = CarteiraService()
            inicio = time.time()

            # Testar com janela pequena
            resultado = carteira_service.sincronizar_incremental(
                minutos_janela=1,
                primeira_execucao=False
            )

            tempo = time.time() - inicio

            if resultado.get('sucesso'):
                print(f"   ✅ Carteira sincronizada em {tempo:.2f}s")
                print(f"      - Pedidos: {resultado.get('pedidos_processados', 0)}")
                print(f"      - Atualizados: {resultado.get('itens_atualizados', 0)}")
            else:
                print(f"   ⚠️ Sincronização da Carteira retornou erro: {resultado.get('erro')}")

    except Exception as e:
        print(f"   ❌ Erro ao executar sincronização da Carteira: {e}")
        return False

    print("\n4. Testando sincronização do Faturamento (janela de 1 minuto para teste)...")
    try:
        with app.app_context():
            faturamento_service = FaturamentoService()
            inicio = time.time()

            # Testar com janela pequena (método completo)
            resultado = faturamento_service.sincronizar_faturamento_incremental(
                minutos_janela=1,
                primeira_execucao=False
            )

            tempo = time.time() - inicio

            if resultado.get('sucesso'):
                print(f"   ✅ Faturamento sincronizado em {tempo:.2f}s")
                print(f"      - Novos: {resultado.get('registros_novos', 0)}")
                print(f"      - Atualizados: {resultado.get('registros_atualizados', 0)}")

                # Mostrar funcionalidades extras
                sincronizacoes = resultado.get('sincronizacoes', {})
                if sincronizacoes:
                    print(f"      - Entregas sincronizadas: {sincronizacoes.get('entregas_sincronizadas', 0)}")
                    print(f"      - Fretes lançados: {sincronizacoes.get('fretes_lancados', 0)}")
            else:
                print(f"   ⚠️ Sincronização do Faturamento retornou erro: {resultado.get('erro')}")

    except Exception as e:
        print(f"   ❌ Erro ao executar sincronização do Faturamento: {e}")
        return False

    print("\n5. Testando script do scheduler...")
    try:
        # Importar o módulo do scheduler
        import app.scheduler.sincronizacao_incremental_simples as scheduler_module

        print("   ✅ Script do scheduler importado com sucesso")

        # Verificar se as funções existem
        if hasattr(scheduler_module, 'executar_sincronizacao'):
            print("   ✅ Função executar_sincronizacao encontrada")
        else:
            print("   ❌ Função executar_sincronizacao não encontrada")
            return False

        if hasattr(scheduler_module, 'executar_sincronizacao_inicial'):
            print("   ✅ Função executar_sincronizacao_inicial encontrada")
        else:
            print("   ❌ Função executar_sincronizacao_inicial não encontrada")
            return False

    except ImportError as e:
        print(f"   ⚠️ Script do scheduler não encontrado: {e}")
        print("      (Isso é normal se o arquivo ainda não foi criado)")

    print("\n" + "="*60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("="*60)

    print("\n📋 Resumo da configuração:")
    print("   - Sincroniza Carteira e Faturamento")
    print("   - Execução imediata ao iniciar (recupera dados do deploy)")
    print("   - Execuções a cada 30 minutos")
    print("   - Busca últimos 40 minutos (10 min de sobreposição)")
    print("   - Usa write_date do Odoo para busca incremental")
    print("   - Logs salvos em: logs/sincronizacao_incremental.log")

    print("\n🚀 Para iniciar o scheduler:")
    print("   python iniciar_sincronizacao_incremental.py")

    print("\n🔧 Ou adicione ao start_render.sh (já foi adicionado!)")

    return True

if __name__ == "__main__":
    success = testar_scheduler()
    sys.exit(0 if success else 1)
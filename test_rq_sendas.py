#!/usr/bin/env python3
"""
Script de teste para verificar a integração do Redis Queue com o Sendas
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_redis_connection():
    """Testa conexão com Redis"""
    print("🔍 Testando conexão com Redis...")
    try:
        from app.portal.workers import get_redis_connection
        redis_conn = get_redis_connection()
        redis_conn.ping()
        print("✅ Redis conectado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao conectar no Redis: {e}")
        print("   Certifique-se que o Redis está rodando: redis-server")
        return False


def test_queue_creation():
    """Testa criação da fila Sendas"""
    print("\n🔍 Testando criação da fila 'sendas'...")
    try:
        from app.portal.workers import get_queue
        queue = get_queue('sendas')
        print(f"✅ Fila 'sendas' criada: {queue.name}")
        print(f"   Jobs na fila: {len(queue)}")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar fila: {e}")
        return False


def test_job_import():
    """Testa importação do job do Sendas"""
    print("\n🔍 Testando importação do job...")
    try:
        from app.portal.workers.sendas_jobs import processar_agendamento_sendas
        print(f"✅ Função importada: {processar_agendamento_sendas.__name__}")
        print(f"   Docstring: {processar_agendamento_sendas.__doc__[:100]}...")
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar job: {e}")
        return False


def test_enqueue_dummy_job():
    """Testa estrutura de enfileiramento (sem executar job real)"""
    print("\n🔍 Testando estrutura de enfileiramento...")
    try:
        from app.portal.workers import get_queue
        from rq import Queue
        
        # Apenas verifica se a fila pode ser criada
        queue = get_queue('sendas')
        
        if isinstance(queue, Queue):
            print(f"✅ Estrutura de enfileiramento funcional!")
            print(f"   Queue name: {queue.name}")
            print(f"   Jobs ativos: {len(queue)}")
            print(f"   Connection: Redis")
            print("   (Job real não executado - teste apenas estrutural)")
            return True
        else:
            print("❌ Fila não é uma instância válida de Queue")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao verificar estrutura: {e}")
        return False


def test_database_models():
    """Testa se os modelos do banco estão acessíveis"""
    print("\n🔍 Testando modelos do banco de dados...")
    try:
        from app.portal.models import PortalIntegracao, PortalLog
        print("✅ Modelos importados:")
        print(f"   - PortalIntegracao: {PortalIntegracao.__tablename__}")
        print(f"   - PortalLog: {PortalLog.__tablename__}")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar modelos: {e}")
        return False


def test_sendas_classes():
    """Testa se as classes do Sendas estão acessíveis"""
    print("\n🔍 Testando classes do Sendas...")
    try:
        from app.portal.sendas.consumir_agendas import ConsumirAgendasSendas
        from app.portal.sendas.preencher_planilha import PreencherPlanilhaSendas
        print("✅ Classes do Sendas importadas:")
        print(f"   - ConsumirAgendasSendas")
        print(f"   - PreencherPlanilhaSendas")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar classes do Sendas: {e}")
        print(f"   Detalhes: {e}")
        return False


def main():
    print("="*60)
    print("🚀 TESTE DE INTEGRAÇÃO REDIS QUEUE - SENDAS")
    print("="*60)
    
    tests = [
        test_redis_connection,
        test_queue_creation,
        test_job_import,
        test_database_models,
        test_sendas_classes,
        test_enqueue_dummy_job
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*60)
    print(f"📊 RESULTADO: {passed} testes passaram, {failed} falharam")
    
    if failed == 0:
        print("✅ TODOS OS TESTES PASSARAM! O sistema está pronto.")
        print("\n📝 Para iniciar o worker:")
        print("   rq worker sendas default --url redis://localhost:6379/0")
        print("\n📝 Para monitorar:")
        print("   rq info --url redis://localhost:6379/0")
    else:
        print("❌ Alguns testes falharam. Verifique os erros acima.")
    
    print("="*60)


if __name__ == "__main__":
    main()
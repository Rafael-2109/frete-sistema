#!/usr/bin/env python3
"""
Script para testar o worker assíncrono localmente
"""

import os
import sys
from redis import Redis
from rq import Queue
import time

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Importar job de teste do módulo separado
from test_jobs import teste_simples

def main():
    print("🧪 TESTE DO WORKER REDIS LOCAL")
    print("=" * 50)
    
    # 1. Verificar Redis
    print("\n1️⃣ Verificando conexão Redis...")
    try:
        redis_conn = Redis.from_url('redis://localhost:6379/0')
        redis_conn.ping()
        print("   ✅ Redis conectado!")
    except Exception as e:
        print(f"   ❌ Erro ao conectar no Redis: {e}")
        print("   Execute: sudo service redis-server start")
        return False
    
    # 2. Criar fila
    print("\n2️⃣ Criando fila de teste...")
    queue = Queue('teste', connection=redis_conn)
    print(f"   📦 Fila 'teste' criada")
    print(f"   📊 Jobs na fila: {len(queue)}")
    
    # 3. Enfileirar job
    print("\n3️⃣ Enfileirando job de teste...")
    job = queue.enqueue(teste_simples)
    print(f"   📋 Job ID: {job.id}")
    print(f"   📊 Status: {job.get_status()}")
    
    # 4. Instruções
    print("\n" + "=" * 50)
    print("📋 AGORA EXECUTE O WORKER EM OUTRO TERMINAL:")
    print("-" * 50)
    print("python worker_atacadao.py --queues teste --verbose")
    print("-" * 50)
    print("\n⏳ Aguardando processamento...")
    
    # 5. Monitorar
    for i in range(10):
        time.sleep(1)
        status = job.get_status()
        print(f"   [{i+1}/10] Status: {status}")
        
        if status == 'finished':
            print(f"\n✅ JOB CONCLUÍDO!")
            print(f"   Resultado: {job.result}")
            return True
        elif status == 'failed':
            print(f"\n❌ JOB FALHOU!")
            print(f"   Erro: {job.exc_info}")
            return False
    
    print("\n⏱️ Timeout - execute o worker!")
    return False

if __name__ == "__main__":
    main()
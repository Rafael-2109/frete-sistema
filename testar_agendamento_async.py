#!/usr/bin/env python3
"""
Script para testar o agendamento assíncrono completo
"""

import os
import sys
import time
from redis import Redis
from rq import Queue
import requests
from datetime import datetime

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    print("🧪 TESTE DO AGENDAMENTO ASSÍNCRONO")
    print("=" * 50)
    
    # 1. Verificar Redis
    print("\n1️⃣ Verificando Redis...")
    try:
        redis_conn = Redis.from_url('redis://localhost:6379/0')
        redis_conn.ping()
        print("   ✅ Redis conectado!")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        print("   Execute: sudo service redis-server start")
        return False
    
    # 2. Verificar filas
    print("\n2️⃣ Verificando filas...")
    queue_atacadao = Queue('atacadao', connection=redis_conn)
    print(f"   📦 Fila 'atacadao': {len(queue_atacadao)} jobs")
    
    # 3. Criar job de teste manual
    print("\n3️⃣ Enfileirando job de teste...")
    from app.portal.workers.atacadao_jobs import processar_agendamento_atacadao
    from app.portal.workers import enqueue_job
    
    # Dados de teste
    dados_teste = {
        'lote_id': 'TESTE-001',
        'pedido_cliente': 'PC-TESTE-123',
        'data_agendamento': '2025-08-30',
        'hora_agendamento': '10:00',
        'peso_total': 100.5,
        'produtos': [
            {
                'codigo': 'PROD001',
                'nome': 'Produto Teste',
                'quantidade': 10,
                'peso': 100.5
            }
        ]
    }
    
    try:
        # Enfileirar job diretamente
        job = queue_atacadao.enqueue(
            processar_agendamento_atacadao,
            999999,  # ID fictício
            dados_teste,
            job_timeout='30m'
        )
        
        print(f"   ✅ Job enfileirado!")
        print(f"   📋 Job ID: {job.id}")
        print(f"   📊 Status: {job.get_status()}")
        
        # 4. Monitorar
        print("\n4️⃣ Monitorando processamento...")
        print("-" * 50)
        print("⚠️  CERTIFIQUE-SE DE QUE O WORKER ESTÁ RODANDO!")
        print("   Em outro terminal: python worker_atacadao.py")
        print("-" * 50)
        
        for i in range(10):
            time.sleep(2)
            status = job.get_status()
            print(f"   [{i+1}/10] Status: {status}")
            
            if status == 'finished':
                print(f"\n✅ JOB PROCESSADO COM SUCESSO!")
                print(f"   Resultado: {job.result}")
                break
            elif status == 'failed':
                print(f"\n❌ JOB FALHOU!")
                print(f"   Erro: {job.exc_info}")
                break
        
        # 5. Verificar endpoint HTTP
        print("\n5️⃣ Testando endpoint HTTP assíncrono...")
        print("   ⚠️  CERTIFIQUE-SE DE QUE A APLICAÇÃO ESTÁ RODANDO!")
        print("   Em outro terminal: python app.py")
        
        input("\n   Pressione ENTER quando app.py estiver rodando...")
        
        # Fazer request de teste
        url = "http://localhost:5000/portal/api/status-filas"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"   ✅ Endpoint funcionando!")
                data = response.json()
                print(f"   📊 Filas: {list(data.get('filas', {}).keys())}")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erro ao acessar endpoint: {e}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ TESTE CONCLUÍDO!")
    print("\n📋 RESUMO:")
    print("1. Redis: OK")
    print("2. Enfileiramento: OK")
    print("3. Worker: Precisa estar rodando")
    print("4. Endpoints assíncronos: Configurados")
    print("\n🎯 PRÓXIMOS PASSOS:")
    print("1. Execute: python worker_atacadao.py")
    print("2. Execute: python app.py")
    print("3. Teste no navegador com um pedido real")

if __name__ == "__main__":
    main()
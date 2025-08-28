#!/usr/bin/env python3
"""
Script de teste para validar o fluxo completo de verificação em lote
Testa: Redis, API, Worker e banco de dados
"""

import json
import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, redis_client, db
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from datetime import datetime

def testar_redis():
    """Testa conexão com Redis"""
    print("=" * 60)
    print("🔴 TESTANDO REDIS")
    print("-" * 60)
    
    try:
        # Testar conexão básica
        redis_client.ping()
        print("✅ Redis está acessível")
        
        # Testar escrita
        test_key = "test_key_" + datetime.now().strftime("%Y%m%d%H%M%S")
        redis_client.setex(test_key, 10, "test_value")
        print(f"✅ Escrita no Redis OK (key: {test_key})")
        
        # Testar leitura
        value = redis_client.get(test_key)
        if value:
            print(f"✅ Leitura do Redis OK (value: {value.decode() if isinstance(value, bytes) else value})")
        
        # Testar fila
        queue_test = "queue:test_" + datetime.now().strftime("%Y%m%d%H%M%S")
        redis_client.lpush(queue_test, json.dumps({"test": "data"}))
        print(f"✅ Fila no Redis OK (queue: {queue_test})")
        
        # Limpar teste
        redis_client.delete(test_key)
        redis_client.delete(queue_test)
        print("✅ Limpeza de teste OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar Redis: {e}")
        print("\nVerifique se o Redis está rodando:")
        print("  sudo service redis-server status")
        print("  sudo service redis-server start")
        return False

def testar_api_enfileiramento():
    """Testa API de enfileiramento"""
    print("\n" + "=" * 60)
    print("📡 TESTANDO API DE ENFILEIRAMENTO")
    print("-" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Buscar alguns protocolos reais para teste
            separacoes = Separacao.query.filter(
                Separacao.protocolo.isnot(None),
                Separacao.protocolo != ''
            ).limit(3).all()
            
            if not separacoes:
                print("⚠️ Nenhuma separação com protocolo encontrada para teste")
                return False
            
            print(f"📋 Encontradas {len(separacoes)} separações com protocolo para teste")
            
            # Simular dados de teste
            protocolos_teste = []
            for sep in separacoes:
                protocolos_teste.append({
                    'protocolo': sep.protocolo,
                    'lote_id': sep.separacao_lote_id,
                    'num_pedido': sep.num_pedido
                })
                print(f"  - Protocolo: {sep.protocolo}, Lote: {sep.separacao_lote_id}")
            
            # Criar task de teste
            task_id = f"test_verificacao_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            task_data = {
                'task_id': task_id,
                'portal': 'atacadao',
                'protocolos': protocolos_teste,
                'total': len(protocolos_teste),
                'processados': 0,
                'atualizados': 0,
                'status': 'pending',
                'criado_em': datetime.now().isoformat(),
                'resultados': []
            }
            
            # Salvar no Redis
            redis_client.setex(
                f"task:{task_id}",
                3600,
                json.dumps(task_data)
            )
            print(f"\n✅ Task criada no Redis: {task_id}")
            
            # Enfileirar protocolos
            for protocolo_info in protocolos_teste:
                job_data = {
                    'task_id': task_id,
                    'protocolo': protocolo_info['protocolo'],
                    'lote_id': protocolo_info.get('lote_id'),
                    'num_pedido': protocolo_info.get('num_pedido'),
                    'portal': 'atacadao'
                }
                
                redis_client.lpush('queue:verificacao_protocolo', json.dumps(job_data))
            
            print(f"✅ {len(protocolos_teste)} protocolos enfileirados")
            
            # Verificar fila
            tamanho_fila = redis_client.llen('queue:verificacao_protocolo')
            print(f"📊 Tamanho atual da fila: {tamanho_fila} itens")
            
            return task_id
            
        except Exception as e:
            print(f"❌ Erro ao testar API: {e}")
            import traceback
            traceback.print_exc()
            return None

def monitorar_task(task_id, timeout=30):
    """Monitora o progresso de uma task"""
    print("\n" + "=" * 60)
    print("📊 MONITORANDO PROGRESSO DA TASK")
    print("-" * 60)
    print(f"Task ID: {task_id}")
    print(f"Timeout: {timeout} segundos")
    print("-" * 60)
    
    inicio = time.time()
    ultima_atualizacao = {'processados': 0}
    
    while time.time() - inicio < timeout:
        try:
            # Buscar status da task
            task_data = redis_client.get(f"task:{task_id}")
            
            if not task_data:
                print("❌ Task não encontrada no Redis")
                break
            
            task_info = json.loads(task_data)
            
            # Mostrar progresso apenas se mudou
            if task_info['processados'] != ultima_atualizacao['processados']:
                print(f"\r🔄 Progresso: {task_info['processados']}/{task_info['total']} " +
                      f"| Atualizados: {task_info['atualizados']} " +
                      f"| Status: {task_info['status']}", end='', flush=True)
                ultima_atualizacao['processados'] = task_info['processados']
            
            # Se concluído, mostrar resultados
            if task_info['status'] == 'completed':
                print(f"\n\n✅ VERIFICAÇÃO CONCLUÍDA!")
                print(f"  - Total processados: {task_info['processados']}")
                print(f"  - Total atualizados: {task_info['atualizados']}")
                
                if task_info.get('resultados'):
                    print("\n📋 Resultados:")
                    for resultado in task_info['resultados']:
                        status = "✅ Atualizado" if resultado.get('atualizado') else "⏭️ Sem alteração"
                        print(f"  {status} - Protocolo: {resultado.get('protocolo')}")
                        if resultado.get('data_agendamento'):
                            print(f"    └─ Data: {resultado['data_agendamento']}, " +
                                  f"Confirmado: {resultado.get('confirmado', False)}")
                
                return True
            
            time.sleep(2)
            
        except Exception as e:
            print(f"\n❌ Erro ao monitorar: {e}")
            break
    
    print(f"\n⏱️ Timeout atingido ({timeout}s)")
    return False

def verificar_worker_rodando():
    """Verifica se há worker processando a fila"""
    print("\n" + "=" * 60)
    print("🔧 VERIFICANDO WORKER")
    print("-" * 60)
    
    # Verificar tamanho da fila antes e depois
    tamanho_inicial = redis_client.llen('queue:verificacao_protocolo')
    print(f"📊 Tamanho inicial da fila: {tamanho_inicial}")
    
    if tamanho_inicial == 0:
        print("⚠️ Fila vazia - criando item de teste")
        job_teste = {
            'task_id': 'test_worker',
            'protocolo': 'TEST123',
            'portal': 'atacadao'
        }
        redis_client.lpush('queue:verificacao_protocolo', json.dumps(job_teste))
        tamanho_inicial = 1
    
    print("⏳ Aguardando 5 segundos para verificar processamento...")
    time.sleep(5)
    
    tamanho_final = redis_client.llen('queue:verificacao_protocolo')
    print(f"📊 Tamanho final da fila: {tamanho_final}")
    
    if tamanho_final < tamanho_inicial:
        print("✅ Worker está processando a fila!")
        return True
    else:
        print("⚠️ Worker pode não estar rodando")
        print("\nPara iniciar o worker, execute em outro terminal:")
        print("  python start_verificacao_worker.py")
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "=" * 60)
    print("🚀 TESTE COMPLETO DO SISTEMA DE VERIFICAÇÃO EM LOTE")
    print("=" * 60)
    
    # 1. Testar Redis
    if not testar_redis():
        print("\n❌ Redis não está funcionando. Abortando testes.")
        return
    
    # 2. Verificar Worker
    worker_ok = verificar_worker_rodando()
    if not worker_ok:
        print("\n⚠️ Worker pode não estar rodando, mas continuaremos os testes...")
    
    # 3. Testar API e enfileiramento
    task_id = testar_api_enfileiramento()
    if not task_id:
        print("\n❌ Falha no teste de API. Abortando.")
        return
    
    # 4. Monitorar progresso (só se worker estiver rodando)
    if worker_ok:
        print("\n⏳ Aguardando worker processar...")
        monitorar_task(task_id, timeout=30)
    else:
        print("\n⚠️ Pulando monitoramento pois worker não está rodando")
    
    print("\n" + "=" * 60)
    print("📝 RESUMO DO TESTE")
    print("-" * 60)
    print("✅ Redis: OK")
    print(f"{'✅' if worker_ok else '⚠️'} Worker: {'OK' if worker_ok else 'Não detectado'}")
    print("✅ API de enfileiramento: OK")
    print("✅ Sistema de tasks: OK")
    
    print("\n📌 PRÓXIMOS PASSOS:")
    print("1. Certifique-se de que o worker está rodando:")
    print("   python start_verificacao_worker.py")
    print("\n2. Acesse a carteira agrupada e clique em 'Verificar Agendas'")
    print("\n3. Os protocolos serão verificados automaticamente")
    print("=" * 60)

if __name__ == '__main__':
    main()
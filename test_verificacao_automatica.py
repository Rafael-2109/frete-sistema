#!/usr/bin/env python3
"""
Script de teste para verificação automática de protocolos pendentes
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.separacao.models import Separacao
import json

def testar_busca_protocolos_pendentes():
    """Testa busca de protocolos pendentes"""
    print("=" * 60)
    print("🔍 TESTANDO BUSCA DE PROTOCOLOS PENDENTES")
    print("-" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Buscar separações com protocolo válido e não confirmado
            query = db.session.query(Separacao).filter(
                Separacao.protocolo.isnot(None),
                Separacao.protocolo != '',
                Separacao.protocolo != 'Vazio',
                Separacao.protocolo != 'vazio',
                Separacao.agendamento_confirmado == False
            )
            
            separacoes = query.all()
            
            print(f"📊 Total de separações encontradas: {len(separacoes)}")
            
            # Agrupar por protocolo único
            protocolos_unicos = {}
            for sep in separacoes:
                if sep.protocolo not in protocolos_unicos:
                    protocolos_unicos[sep.protocolo] = {
                        'protocolo': sep.protocolo,
                        'lote_id': sep.separacao_lote_id,
                        'num_pedido': sep.num_pedido,
                        'cliente': sep.raz_social_red,
                        'data_agendamento': sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None,
                        'confirmado': sep.agendamento_confirmado
                    }
            
            protocolos_lista = list(protocolos_unicos.values())
            
            print(f"✅ Total de protocolos únicos pendentes: {len(protocolos_lista)}")
            
            # Mostrar primeiros 10 protocolos
            print("\n📋 Primeiros protocolos pendentes:")
            for i, proto in enumerate(protocolos_lista[:10], 1):
                print(f"{i:2}. Protocolo: {proto['protocolo']}")
                print(f"    Cliente: {proto['cliente']}")
                print(f"    Data Agend: {proto['data_agendamento'] or 'Sem data'}")
                print(f"    Confirmado: {proto['confirmado']}")
                print(f"    Lote ID: {proto['lote_id']}")
                print("-" * 40)
            
            if len(protocolos_lista) > 10:
                print(f"... e mais {len(protocolos_lista) - 10} protocolos")
            
            # Estatísticas
            print("\n📊 ESTATÍSTICAS:")
            print(f"- Total de protocolos únicos pendentes: {len(protocolos_lista)}")
            print(f"- Total de separações afetadas: {len(separacoes)}")
            
            # Contar protocolos por data
            por_data = {}
            for proto in protocolos_lista:
                data = proto['data_agendamento'] or 'Sem data'
                por_data[data] = por_data.get(data, 0) + 1
            
            print("\n📅 Protocolos por data de agendamento:")
            for data, count in sorted(por_data.items())[:10]:
                print(f"  {data}: {count} protocolos")
            
            return len(protocolos_lista)
            
        except Exception as e:
            print(f"❌ Erro ao buscar protocolos: {e}")
            import traceback
            traceback.print_exc()
            return 0

def verificar_redis_disponivel():
    """Verifica se Redis está disponível"""
    print("\n" + "=" * 60)
    print("🔴 VERIFICANDO REDIS")
    print("-" * 60)
    
    try:
        import redis
        import os
        
        REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        if REDIS_URL.startswith('redis://'):
            redis_client = redis.from_url(REDIS_URL, decode_responses=False)
        else:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
        
        redis_client.ping()
        print("✅ Redis está disponível")
        
        # Verificar fila
        tamanho_fila = redis_client.llen('queue:verificacao_protocolo')
        print(f"📊 Tamanho da fila de verificação: {tamanho_fila} itens")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis não está disponível: {e}")
        print("\nPara iniciar o Redis:")
        print("  sudo service redis-server start")
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "=" * 60)
    print("🚀 TESTE DO SISTEMA DE VERIFICAÇÃO AUTOMÁTICA")
    print("=" * 60)
    
    # 1. Verificar Redis
    redis_ok = verificar_redis_disponivel()
    
    # 2. Buscar protocolos pendentes
    total_pendentes = testar_busca_protocolos_pendentes()
    
    # Resumo
    print("\n" + "=" * 60)
    print("📝 RESUMO DO TESTE")
    print("-" * 60)
    print(f"{'✅' if redis_ok else '❌'} Redis: {'Disponível' if redis_ok else 'Indisponível'}")
    print(f"✅ Protocolos pendentes encontrados: {total_pendentes}")
    
    if total_pendentes > 0:
        print("\n📌 PRÓXIMOS PASSOS:")
        print("1. Certifique-se de que o worker está rodando:")
        print("   python start_verificacao_worker.py")
        print("\n2. Acesse a carteira agrupada")
        print("\n3. Clique no botão 'Verificar Todos Pendentes'")
        print(f"\n4. Confirme a verificação de {total_pendentes} protocolos")
        print("\n5. Aguarde o processamento e veja o relatório de alterações")
    else:
        print("\n⚠️ Não há protocolos pendentes para verificar")
        print("Todos os protocolos já estão confirmados ou não há protocolos válidos")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
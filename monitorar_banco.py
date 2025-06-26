#!/usr/bin/env python3
"""
🏥 MONITORAMENTO DE SAÚDE DO BANCO DE DADOS
Script para verificar e manter a saúde das conexões
"""

import os
import sys
import time
from datetime import datetime
import psutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text, pool
from config import IS_POSTGRESQL


def verificar_saude_banco():
    """Verifica a saúde do banco de dados"""
    app = create_app()
    
    with app.app_context():
        print("\n🏥 MONITORAMENTO DE SAÚDE DO BANCO")
        print("=" * 60)
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🗄️  Tipo: {'PostgreSQL' if IS_POSTGRESQL else 'SQLite'}")
        
        # 1. Testar conexão
        try:
            inicio = time.time()
            result = db.session.execute(text('SELECT 1')).scalar()
            tempo = (time.time() - inicio) * 1000
            print(f"✅ Conexão OK - Tempo: {tempo:.1f}ms")
        except Exception as e:
            print(f"❌ ERRO DE CONEXÃO: {e}")
            return False
        
        # 2. Estatísticas do pool (apenas PostgreSQL)
        if IS_POSTGRESQL and hasattr(db.engine.pool, 'status'):
            pool_status = db.engine.pool.status()
            print(f"\n📊 POOL DE CONEXÕES:")
            print(f"  • Size: {db.engine.pool.size()}")
            print(f"  • Checked out: {db.engine.pool.checkedout()}")
            print(f"  • Overflow: {db.engine.pool.overflow()}")
            print(f"  • Total: {db.engine.pool.total()}")
        
        # 3. Queries ativas
        if IS_POSTGRESQL:
            try:
                active = db.session.execute(text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                    AND application_name = 'frete_sistema'
                """)).scalar()
                
                idle = db.session.execute(text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'idle' 
                    AND application_name = 'frete_sistema'
                """)).scalar()
                
                print(f"\n🔍 CONEXÕES:")
                print(f"  • Ativas: {active}")
                print(f"  • Idle: {idle}")
                
                # Conexões antigas
                old_connections = db.session.execute(text("""
                    SELECT pid, state, query_start, state_change
                    FROM pg_stat_activity
                    WHERE application_name = 'frete_sistema'
                    AND state_change < NOW() - INTERVAL '5 minutes'
                    ORDER BY state_change
                """)).fetchall()
                
                if old_connections:
                    print(f"\n⚠️  CONEXÕES ANTIGAS (>5 min):")
                    for conn in old_connections:
                        idade = datetime.now() - conn.state_change.replace(tzinfo=None)
                        print(f"  • PID {conn.pid}: {conn.state} há {idade}")
                
            except Exception as e:
                print(f"⚠️  Não foi possível obter estatísticas: {e}")
        
        # 4. Performance do sistema
        print(f"\n💻 SISTEMA:")
        print(f"  • CPU: {psutil.cpu_percent(interval=1)}%")
        print(f"  • Memória: {psutil.virtual_memory().percent}%")
        
        # 5. Teste de carga
        print(f"\n🏃 TESTE DE CARGA (10 queries):")
        tempos = []
        for i in range(10):
            try:
                inicio = time.time()
                db.session.execute(text('SELECT 1')).scalar()
                tempo = (time.time() - inicio) * 1000
                tempos.append(tempo)
            except Exception as e:
                print(f"  ❌ Query {i+1}: ERRO - {e}")
                
        if tempos:
            print(f"  • Média: {sum(tempos)/len(tempos):.1f}ms")
            print(f"  • Min: {min(tempos):.1f}ms")
            print(f"  • Max: {max(tempos):.1f}ms")
        
        # 6. Recomendações
        print(f"\n💡 RECOMENDAÇÕES:")
        if IS_POSTGRESQL:
            if idle > 10:
                print("  ⚠️  Muitas conexões idle - considere reduzir pool_size")
            if tempos and max(tempos) > 100:
                print("  ⚠️  Latência alta - verifique a rede ou carga do banco")
            if not old_connections:
                print("  ✅ Nenhuma conexão antiga - pool está saudável")
        
        return True


def limpar_conexoes_antigas():
    """Limpa conexões antigas do PostgreSQL"""
    if not IS_POSTGRESQL:
        print("⚠️  Limpeza disponível apenas para PostgreSQL")
        return
    
    app = create_app()
    
    with app.app_context():
        try:
            # Termina conexões idle antigas
            result = db.session.execute(text("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE application_name = 'frete_sistema'
                AND state = 'idle'
                AND state_change < NOW() - INTERVAL '10 minutes'
            """))
            
            count = result.rowcount
            db.session.commit()
            
            print(f"✅ {count} conexões antigas terminadas")
            
        except Exception as e:
            print(f"❌ Erro ao limpar conexões: {e}")
            db.session.rollback()


def monitoramento_continuo(intervalo=60):
    """Monitora continuamente a saúde do banco"""
    print(f"🔄 Monitoramento contínuo a cada {intervalo}s")
    print("Pressione Ctrl+C para parar\n")
    
    try:
        while True:
            verificar_saude_banco()
            print(f"\n⏳ Próxima verificação em {intervalo}s...")
            time.sleep(intervalo)
    except KeyboardInterrupt:
        print("\n👋 Monitoramento encerrado")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor de Saúde do Banco')
    parser.add_argument('--continuo', '-c', action='store_true',
                       help='Monitoramento contínuo')
    parser.add_argument('--limpar', '-l', action='store_true',
                       help='Limpar conexões antigas')
    parser.add_argument('--intervalo', '-i', type=int, default=60,
                       help='Intervalo em segundos (padrão: 60)')
    
    args = parser.parse_args()
    
    if args.limpar:
        limpar_conexoes_antigas()
    elif args.continuo:
        monitoramento_continuo(args.intervalo)
    else:
        verificar_saude_banco() 
#!/usr/bin/env python
"""
Script para corrigir o problema do pedido_id_old na tabela cotacao_itens
Execute com: python fix_cotacao_pedido_id.py
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Carregar variáveis de ambiente
load_dotenv()

def fix_pedido_id_old():
    """
    Corrige a coluna pedido_id_old para permitir NULL
    """
    # Pegar DATABASE_URL do ambiente
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada nas variáveis de ambiente")
        print("   Configure em .env ou exporte: export DATABASE_URL='postgresql://...'")
        return False
    
    # Corrigir URL se necessário (postgres:// -> postgresql://)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print(f"📊 Conectando ao banco de dados...")
    print(f"   URL: {database_url[:30]}...")  # Mostra só início da URL por segurança
    
    try:
        # Criar engine
        engine = create_engine(database_url)
        
        with engine.begin() as conn:
            # 1. Verificar estado atual
            print("\n1️⃣ Verificando estado atual da coluna pedido_id_old...")
            result = conn.execute(text("""
                SELECT 
                    column_name,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'cotacao_itens' 
                AND column_name = 'pedido_id_old'
            """))
            
            row = result.fetchone()
            if row:
                print(f"   - Coluna: {row[0]}")
                print(f"   - Permite NULL: {row[1]}")
                print(f"   - Valor padrão: {row[2]}")
                
                if row[1] == 'YES':
                    print("✅ Coluna já permite NULL! Nada a fazer.")
                    return True
            else:
                print("⚠️ Coluna pedido_id_old não encontrada!")
                return False
            
            # 2. Alterar coluna
            print("\n2️⃣ Alterando coluna para permitir NULL...")
            conn.execute(text("""
                ALTER TABLE cotacao_itens 
                ALTER COLUMN pedido_id_old DROP NOT NULL
            """))
            print("   ✅ Alteração executada")
            
            # 3. Verificar se funcionou
            print("\n3️⃣ Verificando alteração...")
            result = conn.execute(text("""
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_name = 'cotacao_itens' 
                AND column_name = 'pedido_id_old'
            """))
            
            row = result.fetchone()
            if row and row[0] == 'YES':
                print("   ✅ Coluna agora permite NULL!")
                
                # 4. Contar registros com NULL (opcional)
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM cotacao_itens 
                    WHERE pedido_id_old IS NULL
                """))
                count = result.scalar()
                print(f"\n📊 Estatísticas:")
                print(f"   - Registros com pedido_id_old NULL: {count}")
                
                return True
            else:
                print("   ❌ Erro: Coluna ainda não permite NULL")
                return False
                
    except Exception as e:
        print(f"\n❌ Erro ao executar: {e}")
        return False

def main():
    """
    Função principal
    """
    print("="*60)
    print("🔧 FIX COTACAO_ITENS - PEDIDO_ID_OLD")
    print("="*60)
    
    # Verificar se tem app context
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            success = fix_pedido_id_old()
    except ImportError:
        # Se não conseguir importar app, tenta direto com SQLAlchemy
        success = fix_pedido_id_old()
    
    print("="*60)
    if success:
        print("✅ SUCESSO! Problema corrigido.")
        print("\n📝 Próximos passos:")
        print("1. Reinicie o servidor Flask")
        print("2. Teste a cotação manual novamente")
    else:
        print("❌ FALHOU! Verifique os erros acima.")
        print("\n💡 Alternativa:")
        print("Execute o SQL manualmente no banco de dados:")
        print("ALTER TABLE cotacao_itens ALTER COLUMN pedido_id_old DROP NOT NULL;")
    print("="*60)

if __name__ == "__main__":
    main()
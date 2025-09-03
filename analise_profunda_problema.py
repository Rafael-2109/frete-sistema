#!/usr/bin/env python3
"""
ANÁLISE PROFUNDA: Por que apenas 1 pedido aparece
"""

from app import create_app, db
app = create_app()
from app.pedidos.models import Pedido
from sqlalchemy import text

def analisar():
    with app.app_context():
        print("=" * 80)
        print("ANÁLISE PROFUNDA DO PROBLEMA")
        print("=" * 80)
        
        # 1. Verificar o que existe no banco
        print("\n1. VERIFICANDO O QUE EXISTE NO BANCO:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT 
                table_name,
                table_type
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name LIKE '%pedido%'
            ORDER BY table_name
        """))
        
        for row in result:
            print(f"  {row.table_name}: {row.table_type}")
        
        # 2. Testar usando o modelo Python Pedido
        print("\n2. TESTANDO MODELO PYTHON Pedido:")
        print("-" * 40)
        
        try:
            # Tentar query simples
            count = Pedido.query.count()
            print(f"  Pedido.query.count() = {count}")
            
            # Pegar primeiro pedido
            primeiro = Pedido.query.first()
            if primeiro:
                print(f"  Primeiro pedido: {primeiro.num_pedido} - Lote: {primeiro.separacao_lote_id}")
            
            # Listar alguns
            print("\n  Primeiros 5 pedidos via SQLAlchemy:")
            pedidos = Pedido.query.limit(5).all()
            for p in pedidos:
                print(f"    - {p.num_pedido}: {p.status}")
                
        except Exception as e:
            print(f"  ❌ Erro ao usar modelo Pedido: {e}")
            
        # 3. Verificar se há triggers ou functions
        print("\n3. VERIFICANDO TRIGGERS E FUNCTIONS:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT 
                trigger_name,
                event_manipulation,
                event_object_table
            FROM information_schema.triggers
            WHERE trigger_schema = 'public'
              AND (event_object_table = 'pedidos' OR event_object_table = 'separacao')
        """))
        
        triggers = list(result)
        if triggers:
            print("  Triggers encontradas:")
            for row in triggers:
                print(f"    - {row.trigger_name} on {row.event_object_table} ({row.event_manipulation})")
        else:
            print("  Nenhuma trigger encontrada")
            
        # 4. Verificar se VIEW tem RULES
        print("\n4. VERIFICANDO RULES DA VIEW:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT 
                rulename,
                definition
            FROM pg_rules
            WHERE schemaname = 'public'
              AND tablename = 'pedidos'
        """))
        
        rules = list(result)
        if rules:
            print(f"  {len(rules)} rules encontradas na VIEW pedidos")
            for row in rules:
                print(f"    - {row.rulename}")
        else:
            print("  Nenhuma rule encontrada")
            
        # 5. Verificar o que a aplicação vê
        print("\n5. TESTANDO DIFERENTES FORMAS DE ACESSAR:")
        print("-" * 40)
        
        # Via raw SQL
        result = db.session.execute(text("SELECT COUNT(*) FROM pedidos"))
        count_sql = result.scalar()
        print(f"  SELECT COUNT(*) FROM pedidos = {count_sql}")
        
        # Via SQLAlchemy ORM
        from sqlalchemy import func
        count_orm = db.session.query(func.count(Pedido.id)).scalar()
        print(f"  Via SQLAlchemy ORM = {count_orm}")
        
        # 6. HIPÓTESE: Problema pode ser no models.py
        print("\n6. VERIFICANDO DEFINIÇÃO DO MODELO:")
        print("-" * 40)
        
        # Verificar se o modelo tem algum filtro default
        print(f"  Tabela do modelo: {Pedido.__tablename__}")
        print(f"  É VIEW? {Pedido.__table_args__.get('info', {}).get('is_view', False) if hasattr(Pedido, '__table_args__') else 'Não definido'}")
        
        # 7. HIPÓTESE: Pode estar usando tabela backup
        print("\n7. VERIFICANDO SE ESTÁ USANDO TABELA BACKUP:")
        print("-" * 40)
        
        # Tentar acessar pedidos_backup
        result = db.session.execute(text("""
            SELECT COUNT(*) as total
            FROM pedidos_backup_20250903
        """))
        count_backup = result.scalar()
        print(f"  pedidos_backup_20250903 tem {count_backup} registros")
        
        # 8. SOLUÇÃO PROPOSTA
        print("\n" + "=" * 80)
        print("DIAGNÓSTICO E SOLUÇÃO:")
        print("=" * 80)
        
        if count_sql != count_orm:
            print("❌ PROBLEMA IDENTIFICADO:")
            print("   O modelo Python está retornando quantidade diferente do SQL direto!")
            print("   Isso indica que o modelo pode estar apontando para tabela errada")
            print("\nSOLUÇÃO:")
            print("   1. Verificar app/pedidos/models.py")
            print("   2. Garantir que __tablename__ = 'pedidos'")
            print("   3. Garantir que está marcado como VIEW")
        elif count_sql == 1:
            print("❌ PROBLEMA CONFIRMADO:")
            print("   A VIEW realmente tem apenas 1 registro!")
            print("\nPOSSÍVEL CAUSA:")
            print("   A VIEW foi recriada incorretamente ou com filtro errado")
            print("\nSOLUÇÃO:")
            print("   Recriar a VIEW com o SQL correto")
        else:
            print("⚠️ INVESTIGAÇÃO:")
            print(f"   A VIEW tem {count_sql} registros")
            print("   Mas a aplicação mostra apenas 1")
            print("\nPOSSÍVEIS CAUSAS:")
            print("   1. Filtro adicional na aplicação")
            print("   2. Cache da aplicação")
            print("   3. Problema de permissões")
            print("   4. Aplicação usando conexão diferente")

if __name__ == "__main__":
    analisar()
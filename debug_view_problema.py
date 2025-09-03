#!/usr/bin/env python3
"""
Debug: Por que a VIEW mostra apenas 1 pedido
"""

from app import create_app, db
app = create_app()
from sqlalchemy import text

def debug():
    with app.app_context():
        print("=" * 80)
        print("DEBUG: VIEW MOSTRANDO APENAS 1 PEDIDO")
        print("=" * 80)
        
        # 1. Verificar quantos pedidos a VIEW mostra
        print("\n1. CONTAGEM NA VIEW:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT COUNT(*) as total
            FROM pedidos
        """))
        
        row = result.first()
        print(f"Total de pedidos na VIEW: {row.total}")
        
        # 2. Verificar quantos lotes únicos existem em separacao
        print("\n2. LOTES ÚNICOS EM SEPARACAO:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT 
                COUNT(DISTINCT separacao_lote_id) as lotes_unicos,
                COUNT(*) as total_registros
            FROM separacao
            WHERE separacao_lote_id IS NOT NULL
        """))
        
        row = result.first()
        print(f"Lotes únicos em separacao: {row.lotes_unicos}")
        print(f"Total de registros: {row.total_registros}")
        
        # 3. Verificar quantos excluindo PREVISAO
        print("\n3. EXCLUINDO STATUS='PREVISAO':")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT 
                COUNT(DISTINCT separacao_lote_id) as lotes_unicos,
                COUNT(*) as total_registros
            FROM separacao
            WHERE separacao_lote_id IS NOT NULL
              AND status != 'PREVISAO'
        """))
        
        row = result.first()
        print(f"Lotes únicos sem PREVISAO: {row.lotes_unicos}")
        print(f"Total de registros sem PREVISAO: {row.total_registros}")
        
        # 4. Verificar a definição atual da VIEW
        print("\n4. DEFINIÇÃO ATUAL DA VIEW:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT definition 
            FROM pg_views 
            WHERE viewname = 'pedidos'
            AND schemaname = 'public'
        """))
        
        view_def = result.first()
        if view_def:
            # Verificar o WHERE clause
            if 'WHERE' in view_def.definition:
                where_index = view_def.definition.index('WHERE')
                group_index = view_def.definition.index('GROUP BY') if 'GROUP BY' in view_def.definition else len(view_def.definition)
                where_clause = view_def.definition[where_index:group_index]
                print(f"WHERE clause da VIEW:")
                print(where_clause[:500])
        else:
            print("❌ VIEW não encontrada!")
            
        # 5. Testar query diretamente
        print("\n5. TESTANDO QUERY DA VIEW DIRETAMENTE:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT COUNT(*) as total
            FROM (
                SELECT s.separacao_lote_id
                FROM separacao s
                WHERE s.separacao_lote_id IS NOT NULL
                  AND s.status != 'PREVISAO'
                GROUP BY s.separacao_lote_id
            ) as teste
        """))
        
        row = result.first()
        print(f"Query direta (agrupando e filtrando): {row.total} lotes")
        
        # 6. Verificar se há algum problema com o filtro
        print("\n6. TESTANDO SEM FILTRO DE STATUS:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT COUNT(*) as total
            FROM (
                SELECT s.separacao_lote_id
                FROM separacao s
                WHERE s.separacao_lote_id IS NOT NULL
                GROUP BY s.separacao_lote_id
            ) as teste
        """))
        
        row = result.first()
        print(f"Sem filtro de status: {row.total} lotes")
        
        # 7. Listar os primeiros pedidos da VIEW
        print("\n7. PRIMEIROS PEDIDOS NA VIEW:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT separacao_lote_id, num_pedido, status
            FROM pedidos
            LIMIT 10
        """))
        
        count = 0
        for row in result:
            count += 1
            print(f"{count}. Lote: {row.separacao_lote_id}")
            print(f"   Pedido: {row.num_pedido}")
            print(f"   Status: {row.status}")
        
        if count == 0:
            print("❌ NENHUM pedido encontrado na VIEW!")
        
        # 8. Verificar se o problema é com agregação
        print("\n8. VERIFICANDO PROBLEMA DE AGREGAÇÃO:")
        print("-" * 40)
        
        # Verificar se há lotes com mistura de status
        result = db.session.execute(text("""
            SELECT 
                separacao_lote_id,
                STRING_AGG(DISTINCT status, ', ' ORDER BY status) as status_no_lote,
                COUNT(*) as itens
            FROM separacao
            WHERE separacao_lote_id IS NOT NULL
            GROUP BY separacao_lote_id
            HAVING 'PREVISAO' = ANY(STRING_TO_ARRAY(STRING_AGG(DISTINCT status, ','), ','))
            LIMIT 5
        """))
        
        print("Lotes que contêm PREVISAO (serão excluídos):")
        for row in result:
            print(f"  Lote: {row.separacao_lote_id}")
            print(f"    Status no lote: {row.status_no_lote}")
            print(f"    Itens: {row.itens}")

if __name__ == "__main__":
    debug()
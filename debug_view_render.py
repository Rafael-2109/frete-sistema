#!/usr/bin/env python3
"""
Debug da VIEW pedidos - comparação Local vs Render
Execute este script tanto local quanto no Render para comparar
"""
import os
import sys
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def debug_view():
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*70)
        print(f"DEBUG VIEW PEDIDOS - {datetime.now()}")
        print(f"DATABASE: {os.environ.get('DATABASE_URL', 'LOCAL')[:50]}...")
        print("="*70)
        
        # 1. Verificar estrutura da tabela separacao
        print("\n1. ESTRUTURA DA TABELA SEPARACAO:")
        result = db.session.execute(db.text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'separacao'
            AND column_name IN ('separacao_lote_id', 'status', 'sincronizado_nf')
            ORDER BY ordinal_position
        """)).fetchall()
        
        for col in result:
            print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
        
        # 2. Contar registros
        print("\n2. CONTAGEM DE REGISTROS:")
        
        # Total de separações
        total = db.session.execute(db.text("SELECT COUNT(*) FROM separacao")).fetchone()[0]
        print(f"  Total separações: {total}")
        
        # Com lote_id
        com_lote = db.session.execute(db.text(
            "SELECT COUNT(*) FROM separacao WHERE separacao_lote_id IS NOT NULL"
        )).fetchone()[0]
        print(f"  Com lote_id: {com_lote}")
        
        # Status != PREVISAO
        nao_previsao = db.session.execute(db.text(
            "SELECT COUNT(*) FROM separacao WHERE status != 'PREVISAO'"
        )).fetchone()[0]
        print(f"  Status != PREVISAO: {nao_previsao}")
        
        # Ambos critérios
        ambos = db.session.execute(db.text("""
            SELECT COUNT(DISTINCT separacao_lote_id) 
            FROM separacao 
            WHERE separacao_lote_id IS NOT NULL 
            AND status != 'PREVISAO'
        """)).fetchone()[0]
        print(f"  Atendem ambos critérios (lotes únicos): {ambos}")
        
        # 3. Verificar a VIEW
        print("\n3. VERIFICAR SE VIEW EXISTE:")
        view_exists = db.session.execute(db.text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.views 
                WHERE table_name = 'pedidos'
            )
        """)).fetchone()[0]
        
        if view_exists:
            print("  ✅ VIEW 'pedidos' existe")
            
            # Contar registros na VIEW
            view_count = db.session.execute(db.text("SELECT COUNT(*) FROM pedidos")).fetchone()[0]
            print(f"  Total na VIEW: {view_count}")
            
            # Se há discrepância
            if view_count != ambos:
                print(f"  ⚠️ DISCREPÂNCIA: VIEW tem {view_count} mas deveria ter {ambos}")
        else:
            print("  ❌ VIEW 'pedidos' NÃO EXISTE!")
        
        # 4. Exemplos de registros
        print("\n4. EXEMPLOS DE SEPARAÇÕES QUE DEVERIAM APARECER:")
        exemplos = db.session.execute(db.text("""
            SELECT separacao_lote_id, num_pedido, status, sincronizado_nf
            FROM separacao
            WHERE separacao_lote_id IS NOT NULL 
            AND status != 'PREVISAO'
            LIMIT 5
        """)).fetchall()
        
        for ex in exemplos:
            print(f"  Lote: {ex[0]}, Pedido: {ex[1]}, Status: {ex[2]}, Sync: {ex[3]}")
            
            # Verificar se está na VIEW
            if view_exists:
                na_view = db.session.execute(db.text(
                    "SELECT COUNT(*) FROM pedidos WHERE separacao_lote_id = :lote"
                ), {"lote": ex[0]}).fetchone()[0]
                
                if na_view == 0:
                    print(f"    ❌ NÃO está na VIEW!")
                else:
                    print(f"    ✅ Está na VIEW")
        
        # 5. Verificar valores de sincronizado_nf
        print("\n5. VALORES DE sincronizado_nf:")
        valores_sync = db.session.execute(db.text("""
            SELECT sincronizado_nf, COUNT(*)
            FROM separacao
            GROUP BY sincronizado_nf
            ORDER BY sincronizado_nf
        """)).fetchall()
        
        for val, count in valores_sync:
            print(f"  sincronizado_nf = {val}: {count} registros")
        
        print("\n" + "="*70)
        print("FIM DO DEBUG")
        print("="*70)

if __name__ == "__main__":
    debug_view()
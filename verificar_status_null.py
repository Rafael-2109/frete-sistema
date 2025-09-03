#!/usr/bin/env python3
"""
Verificar registros em Separacao com status NULL ou sem status
"""

from app import create_app, db
app = create_app()
from sqlalchemy import text

def verificar():
    with app.app_context():
        print("=" * 80)
        print("VERIFICAÇÃO: CAMPO STATUS EM SEPARACAO")
        print("=" * 80)
        
        # 1. Verificar distribuição de status incluindo NULL
        print("\n1. DISTRIBUIÇÃO DE STATUS EM SEPARACAO:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT 
                COALESCE(status, 'NULL/VAZIO') as status_display,
                COUNT(*) as total,
                COUNT(DISTINCT separacao_lote_id) as lotes_unicos
            FROM separacao
            WHERE separacao_lote_id IS NOT NULL
            GROUP BY status
            ORDER BY total DESC
        """))
        
        total_geral = 0
        for row in result:
            total_geral += row.total
            print(f"Status '{row.status_display}': {row.total} registros, {row.lotes_unicos} lotes")
            if row.status_display == 'NULL/VAZIO':
                print(f"  ⚠️ PROBLEMA: {row.total} registros sem status!")
        
        print(f"\nTotal geral: {total_geral} registros")
        
        # 2. Verificar registros sem status
        print("\n2. ANALISANDO REGISTROS SEM STATUS:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT COUNT(*) as total
            FROM separacao
            WHERE (status IS NULL OR status = '')
              AND separacao_lote_id IS NOT NULL
        """))
        
        row = result.first()
        sem_status = row.total
        
        if sem_status > 0:
            print(f"❌ {sem_status} registros sem status definido!")
            
            # Mostrar exemplos
            print("\nExemplos de registros sem status:")
            result = db.session.execute(text("""
                SELECT separacao_lote_id, num_pedido, cod_produto, 
                       criado_em, cotacao_id, numero_nf, sincronizado_nf
                FROM separacao
                WHERE (status IS NULL OR status = '')
                  AND separacao_lote_id IS NOT NULL
                LIMIT 5
            """))
            
            for row in result:
                print(f"\nLote: {row.separacao_lote_id}")
                print(f"  Pedido: {row.num_pedido}")
                print(f"  Produto: {row.cod_produto}")
                print(f"  Criado: {row.criado_em}")
                print(f"  Cotação ID: {row.cotacao_id}")
                print(f"  NF: {row.numero_nf}")
                print(f"  Sincronizado NF: {row.sincronizado_nf}")
        else:
            print("✅ Todos os registros têm status preenchido!")
        
        # 3. Análise de como preencher status faltantes
        print("\n3. ANÁLISE PARA PREENCHIMENTO DE STATUS:")
        print("-" * 40)
        
        # Registros sem status por situação
        result = db.session.execute(text("""
            SELECT 
                CASE 
                    WHEN sincronizado_nf = true THEN 'FATURADO (tem sincronizado_nf)'
                    WHEN numero_nf IS NOT NULL THEN 'FATURADO (tem numero_nf)'
                    WHEN cotacao_id IS NOT NULL THEN 'COTADO (tem cotacao_id)'
                    ELSE 'ABERTO (sem cotacao/nf)'
                END as status_sugerido,
                COUNT(*) as total
            FROM separacao
            WHERE (status IS NULL OR status = '')
              AND separacao_lote_id IS NOT NULL
            GROUP BY status_sugerido
            ORDER BY total DESC
        """))
        
        sugestoes = []
        for row in result:
            sugestoes.append(row)
            print(f"{row.status_sugerido}: {row.total} registros")
        
        if sugestoes:
            print("\n4. SCRIPT SQL PARA CORRIGIR:")
            print("-" * 40)
            print("-- Atualizar status baseado em outros campos:")
            print()
            
            # Gerar SQL para cada caso
            print("-- 1. Marcar como FATURADO onde tem sincronizado_nf:")
            print("UPDATE separacao SET status = 'FATURADO'")
            print("WHERE (status IS NULL OR status = '')")
            print("  AND separacao_lote_id IS NOT NULL")
            print("  AND sincronizado_nf = true;")
            print()
            
            print("-- 2. Marcar como FATURADO onde tem numero_nf:")
            print("UPDATE separacao SET status = 'FATURADO'")
            print("WHERE (status IS NULL OR status = '')")
            print("  AND separacao_lote_id IS NOT NULL")
            print("  AND numero_nf IS NOT NULL;")
            print()
            
            print("-- 3. Marcar como COTADO onde tem cotacao_id:")
            print("UPDATE separacao SET status = 'COTADO'")
            print("WHERE (status IS NULL OR status = '')")
            print("  AND separacao_lote_id IS NOT NULL")
            print("  AND cotacao_id IS NOT NULL;")
            print()
            
            print("-- 4. Marcar como ABERTO o restante:")
            print("UPDATE separacao SET status = 'ABERTO'")
            print("WHERE (status IS NULL OR status = '')")
            print("  AND separacao_lote_id IS NOT NULL;")
            
        # 5. Verificar outros campos novos
        print("\n5. VERIFICANDO OUTROS CAMPOS NOVOS:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status IS NULL THEN 1 END) as status_null,
                COUNT(CASE WHEN nf_cd IS NULL THEN 1 END) as nf_cd_null,
                COUNT(CASE WHEN data_embarque IS NULL THEN 1 END) as data_embarque_null,
                COUNT(CASE WHEN cidade_normalizada IS NULL THEN 1 END) as cidade_norm_null,
                COUNT(CASE WHEN separacao_impressa IS NULL THEN 1 END) as impressa_null
            FROM separacao
            WHERE separacao_lote_id IS NOT NULL
        """))
        
        row = result.first()
        print(f"Total de registros: {row.total}")
        print(f"  status NULL: {row.status_null}")
        print(f"  nf_cd NULL: {row.nf_cd_null}")
        print(f"  data_embarque NULL: {row.data_embarque_null}")
        print(f"  cidade_normalizada NULL: {row.cidade_norm_null}")
        print(f"  separacao_impressa NULL: {row.impressa_null}")

if __name__ == "__main__":
    verificar()
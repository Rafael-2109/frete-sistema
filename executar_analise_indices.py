#!/usr/bin/env python3
"""
Script para análise completa de índices do banco de dados
Identifica índices redundantes, não utilizados e oportunidades de otimização
"""

import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from app.utils.timezone import agora_utc_naive
from tabulate import tabulate

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do banco
# Extrai da DATABASE_URL se disponível
database_url = os.getenv('DATABASE_URL', '')
if database_url:
    # Parse DATABASE_URL: postgresql://user:password@host:port/database
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if match:
        DB_CONFIG = {
            'user': match.group(1),
            'password': match.group(2),
            'host': match.group(3),
            'port': match.group(4),
            'database': match.group(5)
        }
    else:
        DB_CONFIG = {
            'host': 'localhost',
            'database': 'frete_sistema',
            'user': 'postgres',
            'password': 'postgres',
            'port': '5432'
        }
else:
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'frete_sistema'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
        'port': os.getenv('DB_PORT', '5432')
    }

def conectar_db():
    """Estabelece conexão com o banco de dados"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

def analisar_indices_nao_usados(cursor):
    """Identifica índices que nunca foram utilizados"""
    print("\n" + "="*80)
    print("1. ÍNDICES NUNCA UTILIZADOS (CANDIDATOS À REMOÇÃO)")
    print("="*80)
    
    query = """
    SELECT 
        schemaname,
        tablename,
        indexname,
        pg_size_pretty(pg_relation_size(indexrelid)) AS tamanho,
        'DROP INDEX IF EXISTS ' || indexname || ';' AS comando_remocao
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
        AND idx_scan = 0
        AND indexrelname NOT LIKE '%_pkey'
        AND indexrelname NOT LIKE '%_unique'
    ORDER BY pg_relation_size(indexrelid) DESC
    """
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    if resultados:
        headers = ['Schema', 'Tabela', 'Índice', 'Tamanho', 'Comando Remoção']
        print(tabulate(resultados, headers=headers, tablefmt='grid'))
        
        # Calcula economia total
        cursor.execute("""
            SELECT pg_size_pretty(SUM(pg_relation_size(indexrelid))) 
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public' AND idx_scan = 0
                AND indexrelname NOT LIKE '%_pkey'
                AND indexrelname NOT LIKE '%_unique'
        """)
        economia = cursor.fetchone()[0]
        print(f"\n💡 Economia potencial removendo índices não usados: {economia}")
    else:
        print("✅ Nenhum índice não utilizado encontrado!")
    
    return len(resultados)

def analisar_indices_duplicados(cursor):
    """Identifica índices duplicados ou redundantes"""
    print("\n" + "="*80)
    print("2. ÍNDICES DUPLICADOS/REDUNDANTES")
    print("="*80)
    
    query = """
    WITH index_columns AS (
        SELECT 
            t.relname AS table_name,
            i.relname AS index_name,
            array_agg(a.attname ORDER BY k.i) AS column_names,
            pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
            idx.idx_scan AS scan_count
        FROM pg_index ix
        JOIN pg_class t ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_stat_user_indexes idx ON idx.indexrelname = i.relname
        CROSS JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS k(attnum, i)
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
        WHERE n.nspname = 'public'
            AND NOT ix.indisprimary
            AND NOT ix.indisunique
        GROUP BY t.relname, i.relname, i.oid, idx.idx_scan
    )
    SELECT 
        ic1.table_name,
        ic1.index_name AS indice_1,
        ic1.column_names AS colunas_1,
        ic1.scan_count AS uso_1,
        ic2.index_name AS indice_2,
        ic2.column_names AS colunas_2,
        ic2.scan_count AS uso_2,
        CASE 
            WHEN ic1.column_names = ic2.column_names THEN 'DUPLICADO EXATO'
            WHEN ic1.column_names @> ic2.column_names THEN 'IND1 CONTÉM IND2'
            WHEN ic2.column_names @> ic1.column_names THEN 'IND2 CONTÉM IND1'
        END AS tipo
    FROM index_columns ic1
    JOIN index_columns ic2 ON 
        ic1.table_name = ic2.table_name 
        AND ic1.index_name < ic2.index_name
        AND (ic1.column_names @> ic2.column_names 
             OR ic2.column_names @> ic1.column_names
             OR ic1.column_names = ic2.column_names)
    ORDER BY ic1.table_name
    """
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    if resultados:
        headers = ['Tabela', 'Índice 1', 'Colunas 1', 'Uso 1', 'Índice 2', 'Colunas 2', 'Uso 2', 'Tipo']
        for row in resultados:
            print(f"\nTabela: {row[0]}")
            print(f"  Índice 1: {row[1]} (Colunas: {row[2]}, Uso: {row[3]})")
            print(f"  Índice 2: {row[4]} (Colunas: {row[5]}, Uso: {row[6]})")
            print(f"  Tipo: {row[7]}")
            if row[3] < row[6]:
                print(f"  💡 Recomendação: DROP INDEX {row[1]}; -- Menos usado")
            else:
                print(f"  💡 Recomendação: DROP INDEX {row[4]}; -- Menos usado")
    else:
        print("✅ Nenhum índice duplicado encontrado!")
    
    return len(resultados)

def analisar_indices_grandes_pouco_usados(cursor):
    """Identifica índices grandes com pouco uso"""
    print("\n" + "="*80)
    print("3. ÍNDICES GRANDES COM POUCO USO")
    print("="*80)
    
    query = """
    SELECT 
        tablename,
        indexname,
        pg_size_pretty(pg_relation_size(indexrelid)) AS tamanho,
        idx_scan AS num_usos,
        CASE 
            WHEN idx_scan > 0 THEN 
                ROUND((pg_relation_size(indexrelid)::numeric / 1024 / 1024) / idx_scan, 2)
            ELSE NULL
        END AS mb_por_uso
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
        AND pg_relation_size(indexrelid) > 10485760  -- Maior que 10MB
        AND idx_scan < 1000
    ORDER BY pg_relation_size(indexrelid) DESC
    LIMIT 20
    """
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    if resultados:
        headers = ['Tabela', 'Índice', 'Tamanho', 'Nº Usos', 'MB/Uso']
        print(tabulate(resultados, headers=headers, tablefmt='grid'))
    else:
        print("✅ Todos os índices grandes estão sendo bem utilizados!")
    
    return len(resultados)

def analisar_fks_sem_indices(cursor):
    """Identifica foreign keys sem índices"""
    print("\n" + "="*80)
    print("4. FOREIGN KEYS SEM ÍNDICES")
    print("="*80)
    
    query = """
    SELECT DISTINCT
        c.conname AS constraint_name,
        t.relname AS table_name,
        a.attname AS column_name
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
    WHERE c.contype = 'f'
        AND n.nspname = 'public'
        AND NOT EXISTS (
            SELECT 1
            FROM pg_index ix
            WHERE ix.indrelid = t.oid
                AND a.attnum = ANY(ix.indkey)
        )
    ORDER BY t.relname, a.attname
    """
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    if resultados:
        headers = ['Constraint', 'Tabela', 'Coluna']
        print(tabulate(resultados, headers=headers, tablefmt='grid'))
        print(f"\n⚠️  {len(resultados)} foreign keys sem índices encontradas!")
        print("💡 Criar índices nessas colunas pode melhorar performance de JOINs e DELETEs")
    else:
        print("✅ Todas as foreign keys possuem índices!")
    
    return len(resultados)

def analisar_fragmentacao(cursor):
    """Analisa fragmentação (bloat) dos índices"""
    print("\n" + "="*80)
    print("5. FRAGMENTAÇÃO DOS ÍNDICES (BLOAT > 30%)")
    print("="*80)
    
    query = """
    WITH index_bloat AS (
        SELECT 
            schemaname,
            tablename,
            indexname,
            pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
            ROUND(
                100.0 * pg_relation_size(indexrelid) / 
                NULLIF(pg_relation_size(tableid), 0), 2
            ) AS index_ratio
        FROM pg_stat_user_indexes
        JOIN pg_index ON indexrelid = indexrelid
        JOIN pg_class ON pg_class.oid = indexrelid
        WHERE schemaname = 'public'
            AND pg_relation_size(indexrelid) > 1048576  -- > 1MB
    )
    SELECT 
        tablename,
        indexname,
        index_size,
        index_ratio || '%' AS ratio_to_table,
        'REINDEX INDEX CONCURRENTLY ' || indexname || ';' AS comando
    FROM index_bloat
    WHERE index_ratio > 30
    ORDER BY index_ratio DESC
    LIMIT 20
    """
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    if resultados:
        headers = ['Tabela', 'Índice', 'Tamanho', 'Ratio', 'Comando REINDEX']
        print(tabulate(resultados, headers=headers, tablefmt='grid'))
        print("\n💡 Execute REINDEX durante janela de manutenção para melhor performance")
    else:
        print("✅ Nenhum índice com fragmentação significativa encontrado!")
    
    return len(resultados)

def gerar_resumo_executivo(cursor):
    """Gera resumo executivo da análise"""
    print("\n" + "="*80)
    print("RESUMO EXECUTIVO")
    print("="*80)
    
    # Estatísticas gerais
    cursor.execute("""
        SELECT 
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE idx_scan = 0) AS nao_usados,
            COUNT(*) FILTER (WHERE idx_scan > 0 AND idx_scan < 100) AS pouco_usados,
            COUNT(*) FILTER (WHERE idx_scan >= 100) AS bem_usados,
            pg_size_pretty(SUM(pg_relation_size(indexrelid))) AS tamanho_total,
            pg_size_pretty(SUM(pg_relation_size(indexrelid)) FILTER (WHERE idx_scan = 0)) AS espaco_desperdicado
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
    """)
    
    stats = cursor.fetchone()
    
    print(f"""
📊 ESTATÍSTICAS GERAIS:
    • Total de índices: {stats[0]}
    • Nunca usados: {stats[1]} ({round(stats[1]*100/stats[0], 1)}%)
    • Pouco usados (<100): {stats[2]} ({round(stats[2]*100/stats[0], 1)}%)
    • Bem usados (>=100): {stats[3]} ({round(stats[3]*100/stats[0], 1)}%)
    • Espaço total em índices: {stats[4]}
    • Espaço desperdiçado: {stats[5] or '0 bytes'}
    """)

def gerar_script_otimizacao(cursor, problemas):
    """Gera script SQL com todas as otimizações recomendadas"""
    print("\n" + "="*80)
    print("GERANDO SCRIPT DE OTIMIZAÇÃO")
    print("="*80)
    
    filename = f"otimizacao_indices_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.sql"
    
    with open(filename, 'w') as f:
        f.write("-- =====================================================\n")
        f.write("-- SCRIPT DE OTIMIZAÇÃO DE ÍNDICES\n")
        f.write(f"-- Gerado em: {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- =====================================================\n\n")
        
        f.write("-- ATENÇÃO: Execute este script em horário de baixa demanda\n")
        f.write("-- Faça backup antes de executar!\n\n")
        
        f.write("BEGIN;\n\n")
        
        # Índices não usados
        f.write("-- 1. REMOVER ÍNDICES NÃO UTILIZADOS\n")
        cursor.execute("""
            SELECT 'DROP INDEX IF EXISTS ' || indexname || '; -- Economia: ' || 
                   pg_size_pretty(pg_relation_size(indexrelid))
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public' AND idx_scan = 0
                AND indexrelname NOT LIKE '%_pkey'
                AND indexrelname NOT LIKE '%_unique'
            ORDER BY pg_relation_size(indexrelid) DESC
        """)
        
        for row in cursor.fetchall():
            f.write(f"{row[0]}\n")
        
        f.write("\n-- 2. REINDEXAR ÍNDICES FRAGMENTADOS\n")
        f.write("-- Execute FORA da transação (CONCURRENTLY não funciona em transação)\n")
        f.write("-- COMMIT;\n")
        
        cursor.execute("""
            SELECT DISTINCT 'REINDEX INDEX CONCURRENTLY ' || indexname || ';'
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public' AND idx_scan > 0
            ORDER BY 1
        """)
        
        for row in cursor.fetchall():
            f.write(f"-- {row[0]}\n")
        
        f.write("\n-- COMMIT;\n")
        f.write("-- Revise os comandos acima antes de executar!\n")
    
    print(f"✅ Script de otimização salvo em: {filename}")
    print(f"📋 Total de problemas identificados: {problemas}")
    
    return filename

def main():
    """Função principal"""
    print("🔍 ANÁLISE DE ÍNDICES DO SISTEMA DE FRETE")
    print("="*80)
    
    conn = conectar_db()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        problemas = 0
        
        # Executa análises
        problemas += analisar_indices_nao_usados(cursor)
        problemas += analisar_indices_duplicados(cursor)
        problemas += analisar_indices_grandes_pouco_usados(cursor)
        problemas += analisar_fks_sem_indices(cursor)
        problemas += analisar_fragmentacao(cursor)
        
        # Gera resumo
        gerar_resumo_executivo(cursor)
        
        # Gera script de otimização
        if problemas > 0:
            script_file = gerar_script_otimizacao(cursor, problemas)
            
            print("\n" + "="*80)
            print("📌 PRÓXIMOS PASSOS:")
            print("="*80)
            print(f"""
1. Revise o script gerado: {script_file}
2. Execute em ambiente de teste primeiro
3. Faça backup do banco de produção
4. Execute durante janela de manutenção
5. Monitore a performance após as mudanças
            """)
        else:
            print("\n✅ Nenhum problema significativo encontrado nos índices!")
            
    except Exception as e:
        print(f"❌ Erro durante análise: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
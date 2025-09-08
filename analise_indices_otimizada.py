#!/usr/bin/env python3
"""
Script otimizado para análise de índices do banco de dados PostgreSQL
Identifica índices redundantes, não utilizados e oportunidades de otimização
"""

import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime
import re

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do banco
database_url = os.getenv('DATABASE_URL', '')
if database_url:
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if match:
        DB_CONFIG = {
            'user': match.group(1),
            'password': match.group(2),
            'host': match.group(3),
            'port': match.group(4),
            'database': match.group(5)
        }

def conectar_db():
    """Estabelece conexão com o banco de dados"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None

def print_table(data, headers):
    """Imprime dados em formato de tabela"""
    if not data:
        return
    
    # Calcula largura máxima para cada coluna
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(str(header))
        for row in data:
            if i < len(row) and row[i] is not None:
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(min(max_width, 50))  # Limita a 50 caracteres
    
    # Imprime cabeçalho
    header_line = " | ".join(str(h).ljust(w)[:w] for h, w in zip(headers, col_widths))
    print(header_line)
    print("-" * len(header_line))
    
    # Imprime dados
    for row in data:
        row_line = " | ".join(str(r if r is not None else '').ljust(w)[:w] 
                             for r, w in zip(row, col_widths))
        print(row_line)

def analisar_indices_completos(cursor):
    """Análise completa de todos os índices"""
    print("\n" + "="*80)
    print("1. ANÁLISE COMPLETA DOS ÍNDICES")
    print("="*80)
    
    query = """
    SELECT 
        i.schemaname,
        i.tablename,
        i.indexname,
        pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamanho,
        s.idx_scan AS num_scans,
        CASE 
            WHEN s.idx_scan = 0 THEN 'NUNCA USADO'
            WHEN s.idx_scan < 10 THEN 'POUCO USADO'
            WHEN s.idx_scan < 100 THEN 'USO MODERADO'
            ELSE 'MUITO USADO'
        END AS categoria_uso
    FROM pg_indexes i
    JOIN pg_stat_user_indexes s ON i.indexname = s.indexrelname 
        AND i.tablename = s.relname 
        AND i.schemaname = s.schemaname
    WHERE i.schemaname = 'public'
    ORDER BY s.idx_scan ASC, pg_relation_size(s.indexrelid) DESC
    LIMIT 50
    """
    
    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if resultados:
            headers = ['Schema', 'Tabela', 'Índice', 'Tamanho', 'Scans', 'Categoria']
            print_table(resultados, headers)
            
            # Estatísticas
            nunca_usados = sum(1 for r in resultados if r[4] == 0)
            pouco_usados = sum(1 for r in resultados if 0 < r[4] < 100)
            print(f"\n📊 Resumo: {nunca_usados} nunca usados, {pouco_usados} pouco usados")
        else:
            print("✅ Nenhum índice encontrado")
            
    except Exception as e:
        print(f"❌ Erro na análise: {e}")

def analisar_indices_nao_usados(cursor):
    """Identifica índices que nunca foram utilizados"""
    print("\n" + "="*80)
    print("2. ÍNDICES NUNCA UTILIZADOS (CANDIDATOS À REMOÇÃO)")
    print("="*80)
    
    query = """
    SELECT 
        s.schemaname,
        s.relname AS tablename,
        s.indexrelname AS indexname,
        pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamanho,
        'DROP INDEX IF EXISTS ' || s.indexrelname || ';' AS comando_remocao
    FROM pg_stat_user_indexes s
    WHERE s.schemaname = 'public'
        AND s.idx_scan = 0
        AND s.indexrelname NOT LIKE '%_pkey'
        AND s.indexrelname NOT LIKE '%_unique'
        AND s.indexrelname NOT LIKE '%_key'
    ORDER BY pg_relation_size(s.indexrelid) DESC
    """
    
    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if resultados:
            headers = ['Schema', 'Tabela', 'Índice', 'Tamanho', 'Comando']
            print_table(resultados, headers)
            
            # Economia total
            cursor.execute("""
                SELECT pg_size_pretty(SUM(pg_relation_size(indexrelid))) 
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public' 
                    AND idx_scan = 0
                    AND indexrelname NOT LIKE '%_pkey'
                    AND indexrelname NOT LIKE '%_unique'
            """)
            economia = cursor.fetchone()[0]
            print(f"\n💰 Economia potencial: {economia}")
        else:
            print("✅ Todos os índices estão sendo utilizados!")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    return len(resultados) if resultados else 0

def analisar_indices_duplicados(cursor):
    """Identifica índices duplicados em mesmas colunas"""
    print("\n" + "="*80)
    print("3. ÍNDICES DUPLICADOS OU REDUNDANTES")
    print("="*80)
    
    query = """
    WITH index_info AS (
        SELECT 
            n.nspname AS schema_name,
            t.relname AS table_name,
            i.relname AS index_name,
            array_to_string(array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)), ', ') AS columns,
            pg_size_pretty(pg_relation_size(i.oid)) AS size,
            s.idx_scan AS scans
        FROM pg_index ix
        JOIN pg_class t ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_stat_user_indexes s ON s.indexrelid = i.oid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        WHERE n.nspname = 'public'
            AND NOT ix.indisprimary
            AND NOT ix.indisunique
        GROUP BY n.nspname, t.relname, i.relname, i.oid, s.idx_scan
    )
    SELECT 
        a.table_name,
        a.index_name AS index1,
        a.columns AS cols1,
        a.scans AS scans1,
        b.index_name AS index2,
        b.columns AS cols2,
        b.scans AS scans2
    FROM index_info a
    JOIN index_info b ON a.table_name = b.table_name 
        AND a.columns = b.columns
        AND a.index_name < b.index_name
    ORDER BY a.table_name, a.index_name
    """
    
    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if resultados:
            print("\n⚠️  Índices duplicados encontrados:\n")
            for row in resultados:
                print(f"Tabela: {row[0]}")
                print(f"  📍 {row[1]} (colunas: {row[2]}, scans: {row[3]})")
                print(f"  📍 {row[4]} (colunas: {row[5]}, scans: {row[6]})")
                if row[3] < row[6]:
                    print(f"  💡 Remover: DROP INDEX {row[1]}; -- menos usado")
                else:
                    print(f"  💡 Remover: DROP INDEX {row[4]}; -- menos usado")
                print()
        else:
            print("✅ Nenhum índice duplicado encontrado!")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    return len(resultados) if resultados else 0

def analisar_indices_grandes_pouco_usados(cursor):
    """Identifica índices grandes mas pouco utilizados"""
    print("\n" + "="*80)
    print("4. ÍNDICES GRANDES COM POUCO USO")
    print("="*80)
    
    query = """
    SELECT 
        s.relname AS tablename,
        s.indexrelname AS indexname,
        pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamanho,
        s.idx_scan AS scans,
        CASE 
            WHEN s.idx_scan > 0 THEN 
                ROUND((pg_relation_size(s.indexrelid)::numeric / 1048576) / s.idx_scan, 2)
            ELSE 999999
        END AS mb_por_uso
    FROM pg_stat_user_indexes s
    WHERE s.schemaname = 'public'
        AND pg_relation_size(s.indexrelid) > 10485760  -- > 10MB
        AND s.idx_scan < 1000
    ORDER BY mb_por_uso DESC
    LIMIT 20
    """
    
    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if resultados:
            headers = ['Tabela', 'Índice', 'Tamanho', 'Scans', 'MB/Uso']
            print_table(resultados, headers)
            print("\n💡 Considere remover índices com alto MB/Uso")
        else:
            print("✅ Todos os índices grandes estão sendo bem utilizados!")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    return len(resultados) if resultados else 0

def analisar_tabelas_principais(cursor):
    """Analisa índices das tabelas principais do sistema"""
    print("\n" + "="*80)
    print("5. ANÁLISE DAS TABELAS PRINCIPAIS")
    print("="*80)
    
    tabelas_principais = [
        'carteira_principal',
        'separacao',
        'pedidos',
        'pre_separacao_item',
        'embarques',
        'embarque_items',
        'faturamento_produto',
        'cadastro_palletizacao'
    ]
    
    for tabela in tabelas_principais:
        print(f"\n📋 Tabela: {tabela}")
        print("-" * 40)
        
        query = f"""
        SELECT 
            i.indexname,
            pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamanho,
            s.idx_scan AS scans,
            CASE 
                WHEN s.idx_scan = 0 THEN '❌ NUNCA USADO'
                WHEN s.idx_scan < 100 THEN '⚠️  POUCO USADO'
                ELSE '✅ BEM USADO'
            END AS status
        FROM pg_indexes i
        JOIN pg_stat_user_indexes s ON i.indexname = s.indexrelname
        WHERE i.tablename = '{tabela}'
            AND i.schemaname = 'public'
        ORDER BY s.idx_scan DESC
        """
        
        try:
            cursor.execute(query)
            indices = cursor.fetchall()
            
            if indices:
                for idx in indices:
                    print(f"  • {idx[0]}: {idx[1]} | Scans: {idx[2]} | {idx[3]}")
            else:
                print("  ⚠️  Nenhum índice encontrado")
                
        except Exception as e:
            print(f"  ❌ Erro ao analisar: {e}")

def analisar_foreign_keys_sem_indices(cursor):
    """Identifica FKs sem índices correspondentes"""
    print("\n" + "="*80)
    print("6. FOREIGN KEYS SEM ÍNDICES")
    print("="*80)
    
    query = """
    WITH fk_info AS (
        SELECT 
            c.conname AS constraint_name,
            t.relname AS table_name,
            array_agg(a.attname ORDER BY k.ordinality) AS fk_columns
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, ordinality)
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
        WHERE c.contype = 'f'
            AND n.nspname = 'public'
        GROUP BY c.conname, t.relname
    )
    SELECT 
        f.table_name,
        f.constraint_name,
        array_to_string(f.fk_columns, ', ') AS columns,
        'CREATE INDEX idx_' || f.table_name || '_' || 
            array_to_string(f.fk_columns, '_') || 
            ' ON ' || f.table_name || ' (' || 
            array_to_string(f.fk_columns, ', ') || ');' AS create_cmd
    FROM fk_info f
    WHERE NOT EXISTS (
        SELECT 1
        FROM pg_index i
        JOIN pg_class ic ON ic.oid = i.indexrelid
        JOIN pg_class tc ON tc.oid = i.indrelid
        WHERE tc.relname = f.table_name
            AND i.indkey::integer[] @> (
                SELECT array_agg(a.attnum)
                FROM unnest(f.fk_columns) AS col
                JOIN pg_attribute a ON a.attrelid = tc.oid AND a.attname = col
            )
    )
    ORDER BY f.table_name
    """
    
    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if resultados:
            print("\n⚠️  Foreign Keys sem índices:\n")
            for row in resultados:
                print(f"Tabela: {row[0]}")
                print(f"  FK: {row[1]}")
                print(f"  Colunas: {row[2]}")
                print(f"  💡 {row[3]}\n")
        else:
            print("✅ Todas as FKs possuem índices!")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    return len(resultados) if resultados else 0

def gerar_resumo_executivo(cursor):
    """Gera resumo executivo da análise"""
    print("\n" + "="*80)
    print("RESUMO EXECUTIVO")
    print("="*80)
    
    try:
        # Total de índices
        cursor.execute("""
            SELECT 
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE idx_scan = 0) AS nao_usados,
                COUNT(*) FILTER (WHERE idx_scan < 100) AS pouco_usados,
                pg_size_pretty(SUM(pg_relation_size(indexrelid))) AS tamanho_total,
                pg_size_pretty(
                    COALESCE(SUM(pg_relation_size(indexrelid)) FILTER (WHERE idx_scan = 0), 0)
                ) AS espaco_desperdicado
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
        """)
        
        stats = cursor.fetchone()
        
        print(f"""
📊 ESTATÍSTICAS GERAIS:
    • Total de índices: {stats[0]}
    • Nunca usados: {stats[1]} ({round(stats[1]*100/stats[0] if stats[0] > 0 else 0, 1)}%)
    • Pouco usados (<100 scans): {stats[2]} ({round(stats[2]*100/stats[0] if stats[0] > 0 else 0, 1)}%)
    • Espaço total em índices: {stats[4]}
    • Espaço desperdiçado: {stats[4]}
        """)
        
        # Top tabelas com mais índices
        cursor.execute("""
            SELECT 
                relname,
                COUNT(*) AS num_indices,
                pg_size_pretty(SUM(pg_relation_size(indexrelid))) AS tamanho
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            GROUP BY relname
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """)
        
        print("\n📈 TOP 5 TABELAS COM MAIS ÍNDICES:")
        for row in cursor.fetchall():
            print(f"    • {row[0]}: {row[1]} índices ({row[2]})")
            
    except Exception as e:
        print(f"❌ Erro no resumo: {e}")

def gerar_script_otimizacao(cursor, arquivo_saida="otimizacao_indices.sql"):
    """Gera script SQL com recomendações de otimização"""
    print("\n" + "="*80)
    print("GERANDO SCRIPT DE OTIMIZAÇÃO")
    print("="*80)
    
    try:
        with open(arquivo_saida, 'w') as f:
            f.write("-- =====================================================\n")
            f.write("-- SCRIPT DE OTIMIZAÇÃO DE ÍNDICES\n")
            f.write(f"-- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-- =====================================================\n\n")
            
            f.write("-- ⚠️  ATENÇÃO:\n")
            f.write("-- 1. Execute em horário de baixa demanda\n")
            f.write("-- 2. Faça backup antes\n")
            f.write("-- 3. Teste em ambiente de desenvolvimento primeiro\n\n")
            
            f.write("BEGIN;\n\n")
            
            # Índices não utilizados
            f.write("-- REMOVER ÍNDICES NÃO UTILIZADOS\n")
            f.write("-- =====================================\n\n")
            
            cursor.execute("""
                SELECT 
                    'DROP INDEX IF EXISTS ' || indexrelname || '; -- ' || 
                    pg_size_pretty(pg_relation_size(indexrelid)) || ' liberados'
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public' 
                    AND idx_scan = 0
                    AND indexrelname NOT LIKE '%_pkey'
                    AND indexrelname NOT LIKE '%_unique'
                    AND indexrelname NOT LIKE '%_key'
                ORDER BY pg_relation_size(indexrelid) DESC
            """)
            
            drops = cursor.fetchall()
            if drops:
                for drop in drops:
                    f.write(f"{drop[0]}\n")
            else:
                f.write("-- Nenhum índice não utilizado encontrado\n")
            
            f.write("\n\nCOMMIT;\n\n")
            
            # REINDEX para manutenção
            f.write("-- REINDEXAR ÍNDICES (MANUTENÇÃO)\n")
            f.write("-- Execute FORA de transação!\n")
            f.write("-- =====================================\n\n")
            
            cursor.execute("""
                SELECT DISTINCT
                    '-- REINDEX INDEX CONCURRENTLY ' || indexrelname || ';'
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public' 
                    AND idx_scan > 0
                ORDER BY 1
                LIMIT 20
            """)
            
            for reindex in cursor.fetchall():
                f.write(f"{reindex[0]}\n")
            
            f.write("\n-- Fim do script\n")
            
        print(f"✅ Script salvo em: {arquivo_saida}")
        
        # Mostra preview
        with open(arquivo_saida, 'r') as f:
            lines = f.readlines()[:30]
            print("\n📄 Preview do script:")
            print("".join(lines))
            
    except Exception as e:
        print(f"❌ Erro ao gerar script: {e}")

def main():
    """Função principal"""
    print("="*80)
    print("🔍 ANÁLISE DE ÍNDICES - SISTEMA DE FRETE")
    print("="*80)
    
    conn = conectar_db()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        # Análises
        analisar_indices_completos(cursor)
        analisar_indices_nao_usados(cursor)
        analisar_indices_duplicados(cursor)
        analisar_indices_grandes_pouco_usados(cursor)
        analisar_tabelas_principais(cursor)
        analisar_foreign_keys_sem_indices(cursor)
        
        # Resumo e script
        gerar_resumo_executivo(cursor)
        gerar_script_otimizacao(cursor)
        
        print("\n" + "="*80)
        print("✅ ANÁLISE CONCLUÍDA COM SUCESSO!")
        print("="*80)
        
        print("""
📌 PRÓXIMOS PASSOS:
1. Revise o script 'otimizacao_indices.sql'
2. Execute em ambiente de teste primeiro
3. Faça backup antes de aplicar em produção
4. Execute durante janela de manutenção
5. Monitore performance após mudanças
        """)
        
    except Exception as e:
        print(f"\n❌ Erro durante análise: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()

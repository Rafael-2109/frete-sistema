#!/usr/bin/env python3
"""
Health Check do Banco de Dados PostgreSQL.

Executa diagnosticos de saude: indices, cache, conexoes, vacuum, bloat, sequences.

Uso:
    python health_check_banco.py --all
    python health_check_banco.py --check unused_indexes cache_hit_rate
    python health_check_banco.py --check top_queries --limit 10
    python health_check_banco.py --check table_sizes --limit 20
"""

import argparse
import json
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

CHECKS_DISPONIVEIS = [
    'unused_indexes',
    'duplicate_indexes',
    'top_queries',
    'cache_hit_rate',
    'connections',
    'index_bloat',
    'table_sizes',
    'vacuum_stats',
    'sequence_capacity',
]


def executar_sql(db, sql: str) -> list:
    """Executa SQL read-only e retorna lista de dicts."""
    from sqlalchemy import text
    with db.engine.connect() as conn:
        result = conn.execute(text(sql))
        colunas = list(result.keys())
        return [dict(zip(colunas, row)) for row in result.fetchall()]


def check_unused_indexes(db, limite: int = 50) -> dict:
    """Indices com 0 scans desde o ultimo reset de estatisticas."""
    sql = f"""
    SELECT
        s.schemaname AS schema,
        s.relname AS tabela,
        s.indexrelname AS indice,
        pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamanho,
        pg_relation_size(s.indexrelid) AS tamanho_bytes,
        s.idx_scan AS scans,
        s.idx_tup_read AS tuplas_lidas,
        s.idx_tup_fetch AS tuplas_buscadas
    FROM pg_stat_user_indexes s
    JOIN pg_index i ON s.indexrelid = i.indexrelid
    WHERE s.idx_scan = 0
      AND NOT i.indisunique
      AND NOT i.indisprimary
      AND s.schemaname = 'public'
    ORDER BY pg_relation_size(s.indexrelid) DESC
    LIMIT {limite};
    """
    rows = executar_sql(db, sql)

    total_bytes = sum(r['tamanho_bytes'] for r in rows)

    for r in rows:
        del r['tamanho_bytes']

    return {
        'check': 'unused_indexes',
        'descricao': 'Indices nunca utilizados (0 scans) — candidatos a remocao',
        'total': len(rows),
        'espaco_desperdicado': _pretty_bytes(total_bytes),
        'espaco_desperdicado_bytes': total_bytes,
        'dados': rows,
        'acao_sugerida': 'Avaliar remocao dos indices nao usados para liberar espaco e reduzir overhead de escrita'
    }


def check_duplicate_indexes(db, limite: int = 50) -> dict:
    """Indices com mesma definicao na mesma tabela."""
    sql = f"""
    SELECT
        n.nspname AS schema,
        ct.relname AS tabela,
        array_agg(ci.relname ORDER BY ci.relname) AS indices,
        pg_get_indexdef(i.indexrelid) AS definicao,
        count(*) AS quantidade,
        sum(pg_relation_size(i.indexrelid)) AS tamanho_total_bytes
    FROM pg_index i
    JOIN pg_class ct ON ct.oid = i.indrelid
    JOIN pg_class ci ON ci.oid = i.indexrelid
    JOIN pg_namespace n ON n.oid = ct.relnamespace
    WHERE n.nspname = 'public'
    GROUP BY n.nspname, ct.relname, pg_get_indexdef(i.indexrelid)
    HAVING count(*) > 1
    ORDER BY sum(pg_relation_size(i.indexrelid)) DESC
    LIMIT {limite};
    """
    rows = executar_sql(db, sql)

    total_bytes = sum(r.get('tamanho_total_bytes', 0) or 0 for r in rows)

    for r in rows:
        r['tamanho_total'] = _pretty_bytes(r.get('tamanho_total_bytes', 0) or 0)
        if 'tamanho_total_bytes' in r:
            del r['tamanho_total_bytes']
        # Converter array do postgres para lista Python
        if isinstance(r.get('indices'), str):
            r['indices'] = r['indices'].strip('{}').split(',')

    return {
        'check': 'duplicate_indexes',
        'descricao': 'Indices duplicados (mesma definicao na mesma tabela)',
        'total': len(rows),
        'espaco_desperdicado': _pretty_bytes(total_bytes),
        'dados': rows,
        'acao_sugerida': 'Remover indices duplicados, manter apenas um de cada definicao'
    }


def check_top_queries(db, limite: int = 10) -> dict:
    """Top queries mais lentas via pg_stat_statements."""
    # Verificar se pg_stat_statements esta disponivel
    try:
        check = executar_sql(db, "SELECT 1 FROM pg_stat_statements LIMIT 1;")
    except Exception:
        return {
            'check': 'top_queries',
            'descricao': 'Top queries por tempo total de execucao',
            'disponivel': False,
            'aviso': 'pg_stat_statements nao esta habilitado. Execute: CREATE EXTENSION IF NOT EXISTS pg_stat_statements;',
            'dados': []
        }

    sql = f"""
    SELECT
        substring(query, 1, 200) AS query_resumida,
        calls AS chamadas,
        round(total_exec_time::numeric, 2) AS tempo_total_ms,
        round(mean_exec_time::numeric, 2) AS tempo_medio_ms,
        round(min_exec_time::numeric, 2) AS tempo_min_ms,
        round(max_exec_time::numeric, 2) AS tempo_max_ms,
        round(stddev_exec_time::numeric, 2) AS desvio_padrao_ms,
        rows AS linhas_retornadas,
        round((shared_blks_hit::numeric / NULLIF(shared_blks_hit + shared_blks_read, 0)) * 100, 2) AS cache_hit_pct
    FROM pg_stat_statements
    WHERE query NOT LIKE 'SET %'
      AND query NOT LIKE 'SHOW %'
      AND query NOT LIKE 'BEGIN%'
      AND query NOT LIKE 'COMMIT%'
      AND query NOT LIKE 'ROLLBACK%'
      AND query NOT LIKE '%pg_stat%'
      AND query NOT LIKE '%pg_catalog%'
      AND userid = (SELECT usesysid FROM pg_user WHERE usename = current_user)
    ORDER BY total_exec_time DESC
    LIMIT {limite};
    """
    rows = executar_sql(db, sql)

    # Converter Decimal para float para JSON
    for r in rows:
        for k, v in r.items():
            if hasattr(v, 'as_integer_ratio'):  # Decimal/float
                r[k] = float(v)

    return {
        'check': 'top_queries',
        'descricao': f'Top {limite} queries por tempo total de execucao',
        'disponivel': True,
        'total': len(rows),
        'dados': rows,
        'acao_sugerida': 'Analisar queries com alto tempo_total_ms. Usar EXPLAIN ANALYZE para investigar planos de execucao.'
    }


def check_cache_hit_rate(db, limite: int = 0) -> dict:
    """Taxa de acerto do buffer cache (shared_buffers)."""
    sql = """
    SELECT
        sum(heap_blks_read) AS blocos_disco,
        sum(heap_blks_hit) AS blocos_cache,
        round(
            sum(heap_blks_hit)::numeric /
            NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100, 2
        ) AS hit_rate_pct
    FROM pg_statio_user_tables;
    """
    rows = executar_sql(db, sql)

    # Index cache hit rate
    sql_idx = """
    SELECT
        sum(idx_blks_read) AS idx_blocos_disco,
        sum(idx_blks_hit) AS idx_blocos_cache,
        round(
            sum(idx_blks_hit)::numeric /
            NULLIF(sum(idx_blks_hit) + sum(idx_blks_read), 0) * 100, 2
        ) AS idx_hit_rate_pct
    FROM pg_statio_user_indexes;
    """
    rows_idx = executar_sql(db, sql_idx)

    heap = rows[0] if rows else {}
    idx = rows_idx[0] if rows_idx else {}

    hit_rate = float(heap.get('hit_rate_pct', 0) or 0)
    idx_hit_rate = float(idx.get('idx_hit_rate_pct', 0) or 0)

    # Classificar saude
    if hit_rate >= 99:
        status = 'EXCELENTE'
    elif hit_rate >= 95:
        status = 'BOM'
    elif hit_rate >= 90:
        status = 'ATENCAO'
    else:
        status = 'CRITICO'

    return {
        'check': 'cache_hit_rate',
        'descricao': 'Taxa de acerto do buffer cache (shared_buffers)',
        'status': status,
        'heap': {
            'hit_rate_pct': hit_rate,
            'blocos_cache': int(heap.get('blocos_cache', 0) or 0),
            'blocos_disco': int(heap.get('blocos_disco', 0) or 0),
        },
        'index': {
            'hit_rate_pct': idx_hit_rate,
            'blocos_cache': int(idx.get('idx_blocos_cache', 0) or 0),
            'blocos_disco': int(idx.get('idx_blocos_disco', 0) or 0),
        },
        'acao_sugerida': 'Hit rate < 95% indica shared_buffers insuficiente ou working set maior que a memoria disponivel'
    }


def check_connections(db, limite: int = 0) -> dict:
    """Conexoes ativas, idle e breakdown por estado."""
    sql = """
    SELECT
        state,
        count(*) AS quantidade,
        max(extract(epoch from (now() - state_change)))::integer AS max_duracao_seg
    FROM pg_stat_activity
    WHERE pid <> pg_backend_pid()
    GROUP BY state
    ORDER BY quantidade DESC;
    """
    rows = executar_sql(db, sql)

    sql_max = """
    SELECT setting::integer AS max_connections
    FROM pg_settings
    WHERE name = 'max_connections';
    """
    max_rows = executar_sql(db, sql_max)
    max_conn = max_rows[0]['max_connections'] if max_rows else 100

    total = sum(r['quantidade'] for r in rows)

    for r in rows:
        if r['state'] is None:
            r['state'] = 'null (backend)'

    return {
        'check': 'connections',
        'descricao': 'Conexoes ativas por estado',
        'max_connections': max_conn,
        'total_ativas': total,
        'utilizacao_pct': round(total / max_conn * 100, 1),
        'por_estado': rows,
        'acao_sugerida': 'Conexoes idle > 50% do total indicam pool mal configurado. idle in transaction > 5min indicam transacoes abandonadas.'
    }


def check_index_bloat(db, limite: int = 20) -> dict:
    """Estimativa de bloat em indices via relacao tamanho real vs esperado."""
    sql = f"""
    SELECT
        s.schemaname AS schema,
        s.relname AS tabela,
        s.indexrelname AS indice,
        pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamanho_atual,
        pg_relation_size(s.indexrelid) AS tamanho_bytes,
        s.idx_scan AS scans,
        s.idx_tup_read AS tuplas_lidas
    FROM pg_stat_user_indexes s
    WHERE s.schemaname = 'public'
      AND pg_relation_size(s.indexrelid) > 1048576  -- > 1MB
    ORDER BY pg_relation_size(s.indexrelid) DESC
    LIMIT {limite};
    """
    rows = executar_sql(db, sql)

    for r in rows:
        tamanho = r.get('tamanho_bytes', 0) or 0
        scans = r.get('scans', 0) or 0
        # Heuristica: indice grande com poucos scans = potencial bloat
        r['eficiencia'] = 'BAIXA' if scans < 100 and tamanho > 10485760 else 'OK'
        del r['tamanho_bytes']

    return {
        'check': 'index_bloat',
        'descricao': 'Maiores indices com analise de eficiencia (tamanho > 1MB)',
        'nota': 'Sem pgstattuple, a estimativa de bloat e aproximada. Indices grandes com poucos scans merecem atencao.',
        'total': len(rows),
        'dados': rows,
        'acao_sugerida': 'Indices com eficiencia BAIXA podem ser removidos ou recriados com REINDEX CONCURRENTLY'
    }


def check_table_sizes(db, limite: int = 20) -> dict:
    """Maiores tabelas por tamanho total (dados + indices + toast)."""
    sql = f"""
    SELECT
        schemaname AS schema,
        relname AS tabela,
        pg_size_pretty(pg_total_relation_size(relid)) AS tamanho_total,
        pg_total_relation_size(relid) AS tamanho_total_bytes,
        pg_size_pretty(pg_relation_size(relid)) AS tamanho_dados,
        pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS tamanho_indices_toast,
        n_live_tup AS linhas_vivas,
        n_dead_tup AS linhas_mortas,
        CASE WHEN n_live_tup > 0
            THEN round(n_dead_tup::numeric / n_live_tup * 100, 2)
            ELSE 0
        END AS dead_ratio_pct
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(relid) DESC
    LIMIT {limite};
    """
    rows = executar_sql(db, sql)

    total_bytes = sum(r.get('tamanho_total_bytes', 0) or 0 for r in rows)

    for r in rows:
        dead = float(r.get('dead_ratio_pct', 0) or 0)
        r['precisa_vacuum'] = dead > 10
        del r['tamanho_total_bytes']

    return {
        'check': 'table_sizes',
        'descricao': f'Top {limite} maiores tabelas por tamanho total',
        'tamanho_total_top': _pretty_bytes(total_bytes),
        'total': len(rows),
        'dados': rows,
        'acao_sugerida': 'Tabelas com dead_ratio > 10% precisam de VACUUM. Tabelas muito grandes podem precisar de particionamento.'
    }


def check_vacuum_stats(db, limite: int = 30) -> dict:
    """Tabelas com mais dead tuples ou que nao recebem vacuum ha muito tempo."""
    sql = f"""
    SELECT
        schemaname AS schema,
        relname AS tabela,
        n_live_tup AS linhas_vivas,
        n_dead_tup AS linhas_mortas,
        CASE WHEN n_live_tup > 0
            THEN round(n_dead_tup::numeric / n_live_tup * 100, 2)
            ELSE 0
        END AS dead_ratio_pct,
        last_vacuum,
        last_autovacuum,
        last_analyze,
        last_autoanalyze,
        vacuum_count,
        autovacuum_count
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
      AND n_dead_tup > 0
    ORDER BY n_dead_tup DESC
    LIMIT {limite};
    """
    rows = executar_sql(db, sql)

    # Converter datetimes para string
    for r in rows:
        for k in ['last_vacuum', 'last_autovacuum', 'last_analyze', 'last_autoanalyze']:
            if r.get(k):
                r[k] = str(r[k])

    problematicas = [r for r in rows if float(r.get('dead_ratio_pct', 0) or 0) > 10]

    return {
        'check': 'vacuum_stats',
        'descricao': 'Tabelas com dead tuples (candidatas a VACUUM)',
        'total_com_dead': len(rows),
        'total_problematicas': len(problematicas),
        'dados': rows,
        'acao_sugerida': 'Tabelas com dead_ratio > 10% devem receber VACUUM ANALYZE. Se autovacuum nao esta atuando, verificar configuracao.'
    }


def check_sequence_capacity(db, limite: int = 0) -> dict:
    """Sequences proximas do limite maximo do tipo de dado."""
    sql = """
    SELECT
        sequencename AS sequencia,
        data_type AS tipo,
        last_value AS valor_atual,
        max_value AS valor_maximo,
        CASE data_type
            WHEN 'integer' THEN 2147483647
            WHEN 'bigint' THEN 9223372036854775807
            WHEN 'smallint' THEN 32767
        END AS limite_tipo,
        round(
            (last_value::numeric /
            CASE data_type
                WHEN 'integer' THEN 2147483647
                WHEN 'bigint' THEN 9223372036854775807
                WHEN 'smallint' THEN 32767
            END) * 100, 4
        ) AS uso_pct
    FROM pg_sequences
    WHERE schemaname = 'public'
      AND last_value IS NOT NULL
    ORDER BY uso_pct DESC;
    """
    rows = executar_sql(db, sql)

    # Converter tipos numericos grandes para compatibilidade JSON
    for r in rows:
        r['valor_atual'] = int(r.get('valor_atual', 0) or 0)
        r['valor_maximo'] = int(r.get('valor_maximo', 0) or 0)
        r['limite_tipo'] = int(r.get('limite_tipo', 0) or 0)
        r['uso_pct'] = float(r.get('uso_pct', 0) or 0)

    alertas = [r for r in rows if r['uso_pct'] > 50]
    atencao = [r for r in rows if 10 < r['uso_pct'] <= 50]

    # Filtrar para output: so mostrar top 10 + alertas
    dados = rows[:10]
    if alertas:
        for a in alertas:
            if a not in dados:
                dados.append(a)

    return {
        'check': 'sequence_capacity',
        'descricao': 'Capacidade das sequences (risco de overflow INTEGER)',
        'total_sequences': len(rows),
        'alertas_criticos': len(alertas),
        'atencao': len(atencao),
        'dados': dados,
        'acao_sugerida': 'Sequences com uso > 50% INTEGER devem ser migradas para BIGINT antes de atingir o limite (2.1 bilhoes).'
    }


def _pretty_bytes(nbytes: int) -> str:
    """Formata bytes para leitura humana."""
    if nbytes < 1024:
        return f"{nbytes} B"
    elif nbytes < 1048576:
        return f"{nbytes / 1024:.1f} KB"
    elif nbytes < 1073741824:
        return f"{nbytes / 1048576:.1f} MB"
    else:
        return f"{nbytes / 1073741824:.2f} GB"


# Mapa de funcoes de check
CHECK_FUNCTIONS = {
    'unused_indexes': check_unused_indexes,
    'duplicate_indexes': check_duplicate_indexes,
    'top_queries': check_top_queries,
    'cache_hit_rate': check_cache_hit_rate,
    'connections': check_connections,
    'index_bloat': check_index_bloat,
    'table_sizes': check_table_sizes,
    'vacuum_stats': check_vacuum_stats,
    'sequence_capacity': check_sequence_capacity,
}


def main():
    parser = argparse.ArgumentParser(description='Health Check do Banco PostgreSQL')
    parser.add_argument('--check', '-c', nargs='+', choices=CHECKS_DISPONIVEIS,
                        help='Checks especificos a executar')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Executar TODOS os checks')
    parser.add_argument('--limit', '-l', type=int, default=20,
                        help='Limite de resultados por check (default: 20)')
    parser.add_argument('--resumo', '-r', action='store_true',
                        help='Apenas resumo (sem dados detalhados)')

    args = parser.parse_args()

    if not args.check and not args.all:
        parser.error('Especifique --check ou --all')

    checks_para_executar = CHECKS_DISPONIVEIS if args.all else args.check

    from app import create_app, db
    app = create_app()

    resultados = {
        'sucesso': True,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'checks_executados': len(checks_para_executar),
        'resultados': {}
    }

    erros = []

    with app.app_context():
        for check_name in checks_para_executar:
            try:
                func = CHECK_FUNCTIONS[check_name]
                resultado = func(db, limite=args.limit)

                if args.resumo and 'dados' in resultado:
                    # No modo resumo, mostrar apenas contagem
                    resultado['dados'] = f'({len(resultado["dados"])} registros — use sem --resumo para detalhes)'

                resultados['resultados'][check_name] = resultado
            except Exception as e:
                erros.append({'check': check_name, 'erro': str(e)})
                resultados['resultados'][check_name] = {
                    'check': check_name,
                    'erro': str(e)
                }

    if erros:
        resultados['erros'] = erros
        resultados['sucesso'] = len(erros) < len(checks_para_executar)

    # Gerar resumo executivo se --all
    if args.all:
        resumo = _gerar_resumo_executivo(resultados['resultados'])
        resultados['resumo_executivo'] = resumo

    print(json.dumps(resultados, indent=2, ensure_ascii=False, default=str))


def _gerar_resumo_executivo(resultados: dict) -> dict:
    """Gera resumo executivo a partir dos resultados de todos os checks."""
    problemas = []
    destaques = []

    # Cache hit rate
    cache = resultados.get('cache_hit_rate', {})
    if cache.get('status') in ('CRITICO', 'ATENCAO'):
        problemas.append(f"Cache hit rate {cache.get('status')}: {cache.get('heap', {}).get('hit_rate_pct', 0)}%")
    else:
        destaques.append(f"Cache hit rate: {cache.get('heap', {}).get('hit_rate_pct', 0)}% ({cache.get('status', 'N/A')})")

    # Unused indexes
    unused = resultados.get('unused_indexes', {})
    if unused.get('total', 0) > 0:
        problemas.append(f"{unused['total']} indices nao usados ({unused.get('espaco_desperdicado', 'N/A')} desperdicado)")

    # Duplicate indexes
    dup = resultados.get('duplicate_indexes', {})
    if dup.get('total', 0) > 0:
        problemas.append(f"{dup['total']} grupos de indices duplicados")

    # Vacuum
    vacuum = resultados.get('vacuum_stats', {})
    if vacuum.get('total_problematicas', 0) > 0:
        problemas.append(f"{vacuum['total_problematicas']} tabelas precisam de VACUUM (dead_ratio > 10%)")

    # Sequences
    seq = resultados.get('sequence_capacity', {})
    if seq.get('alertas_criticos', 0) > 0:
        problemas.append(f"{seq['alertas_criticos']} sequences com uso > 50% — risco de overflow")

    # Connections
    conn = resultados.get('connections', {})
    if conn.get('utilizacao_pct', 0) > 80:
        problemas.append(f"Conexoes em {conn['utilizacao_pct']}% do limite ({conn['total_ativas']}/{conn['max_connections']})")
    else:
        destaques.append(f"Conexoes: {conn.get('total_ativas', 'N/A')}/{conn.get('max_connections', 'N/A')} ({conn.get('utilizacao_pct', 0)}%)")

    # Table sizes
    sizes = resultados.get('table_sizes', {})
    destaques.append(f"Top tabelas: {sizes.get('tamanho_total_top', 'N/A')}")

    # Classificacao geral
    if any('CRITICO' in p for p in problemas):
        saude_geral = 'CRITICO'
    elif len(problemas) > 3:
        saude_geral = 'ATENCAO'
    elif len(problemas) > 0:
        saude_geral = 'BOM (com observacoes)'
    else:
        saude_geral = 'EXCELENTE'

    return {
        'saude_geral': saude_geral,
        'total_problemas': len(problemas),
        'problemas': problemas,
        'destaques': destaques,
    }


if __name__ == '__main__':
    main()

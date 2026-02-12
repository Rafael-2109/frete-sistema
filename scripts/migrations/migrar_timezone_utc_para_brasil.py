"""
Migration: Converter colunas datetime de UTC para Brasil (UTC-3)
================================================================

CONTEXTO:
O sistema armazenava timestamps via agora_utc_naive() em UTC.
Esta migration ajusta TODOS os registros existentes subtraindo 3 horas.

EXECUÇÃO:
  # Dry-run (apenas lista o que seria alterado):
  python scripts/migrations/migrar_timezone_utc_para_brasil.py --dry-run

  # Execução real:
  python scripts/migrations/migrar_timezone_utc_para_brasil.py

  # Forçar re-execução (ignora flag de idempotência):
  python scripts/migrations/migrar_timezone_utc_para_brasil.py --force

IDEMPOTÊNCIA:
  Usa tabela _migration_tz_progress para rastrear cada tabela.coluna processada.
  Se interrompida (ex: SSL drop), re-executar retoma de onde parou.
  Usa _migration_log para registrar conclusão final.

RESILIÊNCIA:
  - Commit por tabela (não transação única) para evitar SSL timeout
  - Retry automático com reconexão em caso de SSL drop
  - Tracking granular: cada tabela.coluna registrada individualmente
"""
import sys
import os
import argparse
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect as sa_inspect

# Nomes de colunas que são auto-geradas (timestamps do sistema)
COLUNAS_AUTO_TIMESTAMP = {
    # Padrão português
    'criado_em', 'atualizado_em', 'alterado_em',
    'processado_em', 'validado_em', 'confirmado_em', 'aprovado_em',
    'enviado_em', 'lido_em', 'respondida_em', 'completado_em',
    'importado_em', 'sincronizado_em', 'fechado_em',
    'calculado_em', 'executado_em', 'diagnosticado_em',
    'inativado_em', 'solicitado_em', 'adicionado_em',
    'consolidado_em',
    # Padrão inglês
    'created_at', 'updated_at', 'changed_at',
    # Campos específicos que são auto-gerados
    'data_criacao', 'data_alerta', 'data_processamento',
    'data_execucao', 'data_hora', 'data_contagem',
    'data_abertura', 'data_autorizacao', 'data_registro',
    'data_importacao', 'data_confirmacao_odoo',
    'vigencia_inicio', 'ultima_utilizacao', 'valido_ate',
}

# Tabelas que NÃO devem ser migradas
TABELAS_EXCLUIDAS = {
    '_migration_log',           # Controle de migrations
    '_migration_tz_progress',   # Progresso desta migration
    'alembic_version',          # Controle de migrations Alembic
}

MIGRATION_NAME = 'migrar_timezone_utc_para_brasil_v1'
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos


def criar_tabelas_controle(engine):
    """Cria tabelas de controle se não existirem."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _migration_log (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(200) NOT NULL UNIQUE,
                executado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                detalhes TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _migration_tz_progress (
                id SERIAL PRIMARY KEY,
                tabela VARCHAR(200) NOT NULL,
                coluna VARCHAR(200) NOT NULL,
                registros_atualizados INTEGER NOT NULL DEFAULT 0,
                processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tabela, coluna)
            )
        """))


def ja_executada(engine):
    """Verifica se esta migration já foi finalizada."""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT 1 FROM _migration_log WHERE migration_name = :name"
        ), {'name': MIGRATION_NAME})
        return result.fetchone() is not None


def coluna_ja_processada(engine, tabela, coluna):
    """Verifica se uma coluna específica já foi processada."""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT 1 FROM _migration_tz_progress "
            "WHERE tabela = :tab AND coluna = :col"
        ), {'tab': tabela, 'col': coluna})
        return result.fetchone() is not None


def registrar_coluna_processada(engine, tabela, coluna, count):
    """Registra que uma coluna foi processada com sucesso."""
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO _migration_tz_progress (tabela, coluna, registros_atualizados) "
            "VALUES (:tab, :col, :cnt) "
            "ON CONFLICT (tabela, coluna) DO NOTHING"
        ), {'tab': tabela, 'col': coluna, 'cnt': count})


def registrar_conclusao(engine, detalhes):
    """Registra que a migration foi concluída."""
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO _migration_log (migration_name, detalhes) "
            "VALUES (:name, :det) "
            "ON CONFLICT (migration_name) DO NOTHING"
        ), {'name': MIGRATION_NAME, 'det': detalhes})


def descobrir_colunas_datetime(engine):
    """Descobre TODAS as colunas TIMESTAMP cujos nomes estão na lista."""
    inspector = sa_inspect(engine)
    resultado = {}

    for table_name in sorted(inspector.get_table_names()):
        if table_name in TABELAS_EXCLUIDAS:
            continue

        colunas_afetadas = []
        for col in inspector.get_columns(table_name):
            col_name = col['name']
            col_type = str(col['type']).upper()

            if 'TIMESTAMP' not in col_type and 'DATETIME' not in col_type:
                continue

            if col_name in COLUNAS_AUTO_TIMESTAMP:
                colunas_afetadas.append(col_name)

        if colunas_afetadas:
            resultado[table_name] = sorted(colunas_afetadas)

    return resultado


def coletar_amostra(conn, table_name, colunas, limite=5):
    """Coleta amostra de valores para verificação."""
    col_list = ', '.join(colunas)
    try:
        result = conn.execute(text(
            f"SELECT {col_list} FROM {table_name} "
            f"WHERE {colunas[0]} IS NOT NULL "
            f"ORDER BY {colunas[0]} DESC LIMIT :lim"
        ), {'lim': limite})
        return [dict(row._mapping) for row in result]
    except Exception as e:
        return [{'erro': str(e)}]


def contar_registros(conn, table_name, coluna):
    """Conta registros não-nulos de uma coluna."""
    try:
        result = conn.execute(text(
            f"SELECT COUNT(*) FROM {table_name} WHERE {coluna} IS NOT NULL"
        ))
        return result.scalar()
    except Exception:
        return 0


def atualizar_tabela_com_retry(engine, table, cols):
    """
    Atualiza uma tabela com retry em caso de falha de conexão.
    Cada tabela tem sua própria transação (commit por tabela).
    Colunas já processadas são puladas.
    """
    resultados = []

    for col in cols:
        # Pular colunas já processadas (retomada)
        if coluna_ja_processada(engine, table, col):
            print(f"  ⏭️  {table}.{col}: já processada (retomada)")
            continue

        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                with engine.begin() as conn:
                    result = conn.execute(text(
                        f"UPDATE {table} SET {col} = {col} - INTERVAL '3 hours' "
                        f"WHERE {col} IS NOT NULL"
                    ))
                    count = result.rowcount

                # Registrar progresso FORA da transação do UPDATE
                registrar_coluna_processada(engine, table, col, count)

                if count > 0:
                    resultados.append((col, count))
                    print(f"  ✅ {table}.{col}: {count} registros atualizados")
                else:
                    print(f"  ⬚ {table}.{col}: 0 registros (tabela vazia)")
                break  # sucesso, próxima coluna

            except Exception as e:
                erro_str = str(e)
                if tentativa < MAX_RETRIES and ('SSL' in erro_str or 'EOF' in erro_str
                                                 or 'closed' in erro_str
                                                 or 'recovery' in erro_str):
                    print(f"  ⚠️  {table}.{col}: erro na tentativa {tentativa}/{MAX_RETRIES}: "
                          f"{erro_str[:80]}")
                    print(f"      Aguardando {RETRY_DELAY}s antes de reconectar...")
                    time.sleep(RETRY_DELAY)
                    # Forçar descarte de conexões stale
                    engine.dispose()
                else:
                    print(f"  ❌ {table}.{col}: FALHA após {tentativa} tentativas: "
                          f"{erro_str[:120]}")
                    raise

    return resultados


def executar_migration(dry_run=False, force=False):
    """Executa a migration principal."""
    app = create_app()

    with app.app_context():
        engine = db.engine

        # === BLOCO 1: Criar tabelas de controle e verificar idempotência ===
        criar_tabelas_controle(engine)

        if not force and ja_executada(engine):
            print(f"⚠️  Migration '{MIGRATION_NAME}' já foi executada.")
            print("   Use --force para re-executar.")
            return

        # Contar progresso existente (retomada)
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM _migration_tz_progress"
            ))
            progresso_existente = result.scalar() or 0

        if progresso_existente > 0 and not force:
            print(f"📋 Retomando migration: {progresso_existente} colunas já processadas")

        # === BLOCO 2: Discovery ===
        colunas_por_tabela = descobrir_colunas_datetime(engine)

        total_tabelas = len(colunas_por_tabela)
        total_colunas = sum(len(cols) for cols in colunas_por_tabela.values())

        print(f"\n{'='*70}")
        print(f"  MIGRATION: UTC → Brasil (UTC-3)")
        print(f"  Modo: {'DRY-RUN (nenhuma alteração será feita)' if dry_run else 'EXECUÇÃO REAL'}")
        print(f"  Tabelas afetadas: {total_tabelas}")
        print(f"  Colunas afetadas: {total_colunas}")
        if progresso_existente > 0:
            print(f"  Já processadas: {progresso_existente} (retomada)")
        print(f"{'='*70}\n")

        # === BLOCO 3: Amostra BEFORE ===
        print("📋 BEFORE — Amostra de dados (primeiras 5 tabelas):")
        amostras_before = {}
        with engine.connect() as conn:
            for i, (table, cols) in enumerate(colunas_por_tabela.items()):
                count = contar_registros(conn, table, cols[0])
                if i < 5 and count > 0:
                    amostra = coletar_amostra(conn, table, cols)
                    amostras_before[table] = amostra
                    print(f"  {table} ({count} registros): {cols}")
                    for row in amostra[:2]:
                        print(f"    → {row}")
                elif i < 20:
                    print(f"  {table} ({count} registros): {cols}")

            if total_tabelas > 20:
                print(f"  ... e mais {total_tabelas - 20} tabelas")

        if dry_run:
            print("\n🔍 DRY-RUN: Nenhuma alteração foi feita.")
            print("\nSQL que seria executado:")
            for table, cols in colunas_por_tabela.items():
                for col in cols:
                    print(f"  UPDATE {table} SET {col} = {col} - INTERVAL '3 hours' WHERE {col} IS NOT NULL;")
            return

        # === BLOCO 4: Descobrir e desabilitar triggers problemáticos ===
        print("\n🔍 Verificando triggers problemáticos...")
        triggers_desabilitados = []

        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT t.event_object_table, t.trigger_name
                FROM information_schema.triggers t
                WHERE t.action_statement LIKE '%update_updated_at_column%'
                  AND NOT EXISTS (
                    SELECT 1 FROM information_schema.columns c
                    WHERE c.table_name = t.event_object_table
                      AND c.column_name = 'updated_at'
                  )
            """))
            for row in result:
                table_name, trigger_name = row[0], row[1]
                conn.execute(text(
                    f"ALTER TABLE {table_name} DISABLE TRIGGER {trigger_name}"
                ))
                triggers_desabilitados.append((table_name, trigger_name))
                print(f"  🔇 Desabilitado: {table_name}.{trigger_name}")

        if not triggers_desabilitados:
            print("  Nenhum trigger problemático encontrado.")

        # === BLOCO 5: Execução com commit POR TABELA ===
        print("\n🔄 Executando migration (commit por tabela)...")
        registros_atualizados = 0
        detalhes_tabelas = []
        tabelas_processadas = 0

        for table, cols in colunas_por_tabela.items():
            resultados = atualizar_tabela_com_retry(engine, table, cols)
            for col, count in resultados:
                registros_atualizados += count
                detalhes_tabelas.append(f"{table}.{col}: {count}")

            tabelas_processadas += 1
            if tabelas_processadas % 50 == 0:
                print(f"  --- Progresso: {tabelas_processadas}/{total_tabelas} tabelas ---")

        # === BLOCO 5b: Re-habilitar triggers ===
        if triggers_desabilitados:
            with engine.begin() as conn:
                for table_name, trigger_name in triggers_desabilitados:
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ENABLE TRIGGER {trigger_name}"
                    ))
                    print(f"  🔊 Re-habilitado: {table_name}.{trigger_name}")

        print(f"\n✅ Migration concluída: {registros_atualizados} registros atualizados")

        # === BLOCO 6: Verificação AFTER ===
        print("\n📋 AFTER — Amostra de dados (verificação):")
        with engine.connect() as conn:
            for table in list(amostras_before.keys())[:5]:
                cols = colunas_por_tabela[table]
                amostra_after = coletar_amostra(conn, table, cols)
                print(f"  {table}:")
                for before, after in zip(amostras_before[table][:2], amostra_after[:2]):
                    print(f"    BEFORE: {before}")
                    print(f"    AFTER:  {after}")

        # === BLOCO 7: Registrar conclusão ===
        # Contar total real de registros processados
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT SUM(registros_atualizados) FROM _migration_tz_progress"
            ))
            total_real = result.scalar() or 0

        detalhes_str = (
            f"Tabelas: {total_tabelas}, Colunas: {total_colunas}, "
            f"Registros: {total_real}\n" +
            '\n'.join(detalhes_tabelas[:50])
        )
        registrar_conclusao(engine, detalhes_str)
        print(f"\n📝 Migration registrada em _migration_log como '{MIGRATION_NAME}'")
        print(f"   Total de registros processados: {total_real}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Migrar timestamps de UTC para Brasil (UTC-3)'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas mostra o que seria alterado, sem executar')
    parser.add_argument('--force', action='store_true',
                        help='Forçar re-execução mesmo se já executada')
    args = parser.parse_args()

    executar_migration(dry_run=args.dry_run, force=args.force)

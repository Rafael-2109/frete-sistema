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
  Usa tabela _migration_log para registrar execução.
  Não executa duas vezes a menos que --force seja passado.
"""
import sys
import os
import argparse
from datetime import datetime

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

# Tabelas que NÃO devem ser migradas (dados de sistema externo ou já corretos)
TABELAS_EXCLUIDAS = {
    '_migration_log',       # Tabela de controle desta migration
    'alembic_version',      # Controle de migrations Alembic
}

MIGRATION_NAME = 'migrar_timezone_utc_para_brasil_v1'


def criar_tabela_migration_log(conn):
    """Cria tabela de controle de migrations se não existir."""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS _migration_log (
            id SERIAL PRIMARY KEY,
            migration_name VARCHAR(200) NOT NULL UNIQUE,
            executado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            detalhes TEXT
        )
    """))
    conn.commit()


def ja_executada(conn):
    """Verifica se esta migration já foi executada."""
    result = conn.execute(text(
        "SELECT 1 FROM _migration_log WHERE migration_name = :name"
    ), {'name': MIGRATION_NAME})
    return result.fetchone() is not None


def registrar_execucao(conn, detalhes):
    """Registra que a migration foi executada."""
    conn.execute(text(
        "INSERT INTO _migration_log (migration_name, detalhes) VALUES (:name, :det)"
    ), {'name': MIGRATION_NAME, 'det': detalhes})
    conn.commit()


def descobrir_colunas_datetime(engine):
    """
    Usa SQLAlchemy inspect para descobrir TODAS as colunas TIMESTAMP
    cujos nomes estão na lista de auto-gerados.

    Returns:
        dict: {table_name: [col_name, ...]}
    """
    inspector = sa_inspect(engine)
    resultado = {}

    for table_name in sorted(inspector.get_table_names()):
        if table_name in TABELAS_EXCLUIDAS:
            continue

        colunas_afetadas = []
        for col in inspector.get_columns(table_name):
            col_name = col['name']
            col_type = str(col['type']).upper()

            # Apenas colunas TIMESTAMP (não DATE)
            if 'TIMESTAMP' not in col_type and 'DATETIME' not in col_type:
                continue

            if col_name in COLUNAS_AUTO_TIMESTAMP:
                colunas_afetadas.append(col_name)

        if colunas_afetadas:
            resultado[table_name] = sorted(colunas_afetadas)

    return resultado


def coletar_amostra(conn, table_name, colunas, limite=5):
    """Coleta amostra de valores antes/depois para verificação."""
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


def executar_migration(dry_run=False, force=False):
    """Executa a migration principal."""
    app = create_app()

    with app.app_context():
        engine = db.engine

        # === BLOCO 1: Verificação de idempotência ===
        with engine.connect() as conn:
            criar_tabela_migration_log(conn)

            if not force and ja_executada(conn):
                print(f"⚠️  Migration '{MIGRATION_NAME}' já foi executada.")
                print("   Use --force para re-executar.")
                return

        # === BLOCO 2: Discovery ===
        colunas_por_tabela = descobrir_colunas_datetime(engine)

        total_tabelas = len(colunas_por_tabela)
        total_colunas = sum(len(cols) for cols in colunas_por_tabela.values())

        print(f"\n{'='*70}")
        print(f"  MIGRATION: UTC → Brasil (UTC-3)")
        print(f"  Modo: {'DRY-RUN (nenhuma alteração será feita)' if dry_run else 'EXECUÇÃO REAL'}")
        print(f"  Tabelas afetadas: {total_tabelas}")
        print(f"  Colunas afetadas: {total_colunas}")
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
        # Alguns triggers referenciam updated_at mas a tabela usa atualizado_em
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

        # === BLOCO 5: Execução com transação ===
        print("\n🔄 Executando migration...")
        registros_atualizados = 0
        detalhes_tabelas = []

        with engine.begin() as conn:  # auto-commit no final
            for table, cols in colunas_por_tabela.items():
                for col in cols:
                    result = conn.execute(text(
                        f"UPDATE {table} SET {col} = {col} - INTERVAL '3 hours' "
                        f"WHERE {col} IS NOT NULL"
                    ))
                    count = result.rowcount
                    registros_atualizados += count
                    if count > 0:
                        detalhes_tabelas.append(f"{table}.{col}: {count}")
                        print(f"  ✅ {table}.{col}: {count} registros atualizados")
                    else:
                        print(f"  ⬚ {table}.{col}: 0 registros (tabela vazia)")

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

        # === BLOCO 7: Registrar execução ===
        with engine.connect() as conn:
            detalhes_str = f"Tabelas: {total_tabelas}, Colunas: {total_colunas}, " \
                          f"Registros: {registros_atualizados}\n" + \
                          '\n'.join(detalhes_tabelas[:50])
            registrar_execucao(conn, detalhes_str)
            print(f"\n📝 Migration registrada em _migration_log como '{MIGRATION_NAME}'")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrar timestamps de UTC para Brasil (UTC-3)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas mostra o que seria alterado, sem executar')
    parser.add_argument('--force', action='store_true',
                        help='Forçar re-execução mesmo se já executada')
    args = parser.parse_args()

    executar_migration(dry_run=args.dry_run, force=args.force)

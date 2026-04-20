"""Migracao de configuracao do modulo Pessoal entre bancos (local → producao).

Exporta 5 tabelas de CONFIGURACAO (sem extratos/transacoes/orcamentos):
  1. pessoal_membros
  2. pessoal_categorias
  3. pessoal_exclusoes_empresa
  4. pessoal_contas         (FK → membros)
  5. pessoal_regras_categorizacao  (FK → categorias, membros)

Uso:
  # LOCAL
  python scripts/migrate_pessoal_config.py --export
    -> gera scripts/dumps/pessoal_config_dump.sql

  # PRODUCAO (Render Shell)
  python scripts/migrate_pessoal_config.py --import --dry-run
  python scripts/migrate_pessoal_config.py --import

Pre-requisito em producao:
  python scripts/migrations/pessoal_features_f1_f2_f4.py  (cria colunas F1/F4)

Seguranca:
- --import ABORTA se qualquer das 5 tabelas tem dados em producao
- Preserva IDs originais (producao esta vazia)
- Reseta sequences (setval) ao final de cada tabela
- Transacao unica: rollback total em caso de erro
"""
import argparse
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# Garantir import de app/ mesmo executando de scripts/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


DUMP_FILE = ROOT / "scripts" / "dumps" / "pessoal_config_dump.sql"

TABELAS = [
    # (nome_tabela, colunas_preservadas_em_ordem, sequence_name)
    (
        "pessoal_membros",
        ["id", "nome", "nome_completo", "papel", "ativo", "criado_em"],
        "pessoal_membros_id_seq",
    ),
    (
        "pessoal_categorias",
        ["id", "nome", "grupo", "icone", "ordem_exibicao", "ativa", "criado_em"],
        "pessoal_categorias_id_seq",
    ),
    (
        "pessoal_exclusoes_empresa",
        ["id", "padrao", "descricao", "ativo"],
        "pessoal_exclusoes_empresa_id_seq",
    ),
    (
        "pessoal_contas",
        [
            "id", "nome", "tipo", "banco", "agencia", "numero_conta",
            "ultimos_digitos_cartao", "membro_id", "ativa", "criado_em",
        ],
        "pessoal_contas_id_seq",
    ),
    (
        "pessoal_regras_categorizacao",
        [
            "id", "padrao_historico", "tipo_regra", "categoria_id", "membro_id",
            "categorias_restritas_ids", "cpf_cnpj_padrao", "valor_min", "valor_max",
            "vezes_usado", "confianca", "origem", "ativo",
            "criado_em", "atualizado_em",
        ],
        "pessoal_regras_categorizacao_id_seq",
    ),
]


# =============================================================================
# EXPORT
# =============================================================================

def _sql_literal(v):
    """Converte valor Python para literal SQL."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    if isinstance(v, (date, datetime)):
        return f"'{v.isoformat()}'"
    # String: escapar aspas simples duplicando
    s = str(v).replace("'", "''")
    return f"'{s}'"


def _check_colunas_existem(conn, tabela: str, colunas: list[str]) -> list[str]:
    """Retorna subset de colunas que realmente existem na tabela local."""
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :t"
    ), {"t": tabela})
    existentes = {row[0] for row in result}
    faltando = [c for c in colunas if c not in existentes]
    if faltando:
        print(f"  [WARN] Colunas ausentes em {tabela} (serao puladas): {faltando}")
    return [c for c in colunas if c in existentes]


def exportar():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            linhas = []
            linhas.append("-- ==============================================")
            linhas.append("-- Dump de CONFIGURACAO do modulo Pessoal")
            linhas.append(f"-- Gerado em: {datetime.now().isoformat()}")
            linhas.append("-- Aplicar em banco de PRODUCAO VAZIO (5 tabelas)")
            linhas.append("-- ==============================================")
            linhas.append("")
            linhas.append("BEGIN;")
            linhas.append("")

            totais = {}
            for tabela, colunas, seq in TABELAS:
                cols_reais = _check_colunas_existem(conn, tabela, colunas)
                if not cols_reais:
                    print(f"  [SKIP] {tabela}: nenhuma coluna conhecida encontrada")
                    continue

                cols_sql = ", ".join(cols_reais)
                rows = conn.execute(text(
                    f"SELECT {cols_sql} FROM {tabela} ORDER BY id"
                )).fetchall()

                totais[tabela] = len(rows)
                print(f"  [OK] {tabela}: {len(rows)} registros")

                if not rows:
                    continue

                linhas.append(f"-- {tabela} ({len(rows)} registros)")
                for row in rows:
                    valores = ", ".join(_sql_literal(v) for v in row)
                    linhas.append(
                        f"INSERT INTO {tabela} ({cols_sql}) VALUES ({valores});"
                    )

                # Resetar sequence
                linhas.append(
                    f"SELECT setval('{seq}', "
                    f"COALESCE((SELECT MAX(id) FROM {tabela}), 1), "
                    f"EXISTS (SELECT 1 FROM {tabela}));"
                )
                linhas.append("")

            linhas.append("COMMIT;")
            linhas.append("")

            DUMP_FILE.parent.mkdir(parents=True, exist_ok=True)
            DUMP_FILE.write_text("\n".join(linhas), encoding="utf-8")

            print(f"\n=== Export concluido ===")
            print(f"Arquivo: {DUMP_FILE}")
            print(f"Total por tabela: {totais}")


# =============================================================================
# IMPORT
# =============================================================================

def importar(dry_run: bool = False):
    if not DUMP_FILE.exists():
        print(f"ERRO: arquivo {DUMP_FILE} nao encontrado. Rode --export primeiro.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        # Safety: abortar se producao ja tem dados
        with db.engine.connect() as conn:
            print("=== Verificando estado do banco alvo ===")
            ja_populadas = []
            for tabela, _, _ in TABELAS:
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar() or 0
                    if count > 0:
                        ja_populadas.append((tabela, count))
                        print(f"  [WARN] {tabela}: {count} registros ja existem")
                    else:
                        print(f"  [OK] {tabela}: vazia")
                except Exception as e:
                    print(f"  [ERRO] {tabela} nao existe ou inacessivel: {e}")
                    sys.exit(1)

            if ja_populadas:
                print("\nERRO: banco alvo nao esta vazio. Abortando.")
                print("Tabelas com dados:")
                for t, c in ja_populadas:
                    print(f"  - {t}: {c} registros")
                print("\nSe quer reimportar mesmo assim: TRUNCATE manual antes.")
                sys.exit(1)

        # Executar dump
        sql = DUMP_FILE.read_text(encoding="utf-8")
        n_inserts = sql.count("INSERT INTO")
        n_setvals = sql.count("setval")
        print(f"\n=== Dump a aplicar ===")
        print(f"  INSERTs: {n_inserts}")
        print(f"  setvals: {n_setvals}")

        if dry_run:
            print("\n[DRY-RUN] Nenhuma mudanca aplicada.")
            print("Para aplicar, remova --dry-run")
            return

        print("\n=== Aplicando dump ===")
        with db.engine.begin() as conn:
            # Executar statement-by-statement para melhor erro
            stmts = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
            aplicados = 0
            for stmt in stmts:
                if stmt.upper() in ("BEGIN", "COMMIT"):
                    continue
                try:
                    conn.execute(text(stmt))
                    aplicados += 1
                except Exception as e:
                    print(f"ERRO no statement: {stmt[:100]}...")
                    print(f"  {e}")
                    raise

            print(f"\n[OK] {aplicados} statements aplicados")

        # Verificar contagem final
        with db.engine.connect() as conn:
            print("\n=== Estado final ===")
            for tabela, _, _ in TABELAS:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
                print(f"  {tabela}: {count} registros")

        print("\n=== Import concluido ===")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Migrar configuracao Pessoal entre bancos")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--export", action="store_true", help="Exporta do banco local para SQL")
    grupo.add_argument("--import", dest="do_import", action="store_true", help="Importa SQL no banco atual")
    parser.add_argument("--dry-run", action="store_true", help="No import, nao aplica mudancas")

    args = parser.parse_args()

    if args.export:
        print("=== EXPORT (banco atual → arquivo) ===")
        print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'local .env')[:50]}...")
        exportar()
    elif args.do_import:
        print("=== IMPORT (arquivo → banco atual) ===")
        print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'local .env')[:50]}...")
        if args.dry_run:
            print("MODO: dry-run\n")
        importar(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

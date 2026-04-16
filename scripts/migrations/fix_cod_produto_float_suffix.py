"""
Fix: Remover sufixo ".0" de cod_produto em tabelas afetadas por importacao Excel.

CAUSA RAIZ:
    pd.read_excel() sem dtype=str le inteiros como float64.
    str(4210155.0) gera "4210155.0" em vez de "4210155".

TABELAS AFETADAS:
    - cadastro_palletizacao (cod_produto) -- tem UNIQUE index
    - movimentacao_estoque (cod_produto, cod_produto_raiz)
    - programacao_producao (cod_produto)
    - recursos_producao (cod_produto)
    - previsao_demanda (cod_produto)
    - custo_considerado (cod_produto)

CAMINHOS DE IMPORTACAO VULNERAVEIS (corrigir no codigo):
    - app/producao/routes.py:321 (palletizacao)
    - app/producao/routes.py:548 (programacao)
    - app/estoque/routes.py:408 (movimentacoes)
    - app/manufatura/routes/recursos_producao_routes.py:344
    - app/manufatura/routes/previsao_demanda_routes.py:437
    - app/custeio/routes/custeio_routes.py:1035

SEGURANCA: Idempotente. So atinge codigos puramente numericos com sufixo .0
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text

# Regex PostgreSQL: codigo composto apenas de digitos + ".0" no final
REGEX_FLOAT_SUFFIX = r'^[0-9]+\.0$'

TABELAS_CORRECAO = [
    # (tabela, coluna, audit_clause, tem_unique_constraint)
    ('cadastro_palletizacao', 'cod_produto', "updated_at = NOW()", True),
    ('movimentacao_estoque', 'cod_produto',
     "atualizado_em = NOW(), atualizado_por = 'migration_fix_float_suffix'", False),
    ('movimentacao_estoque', 'cod_produto_raiz',
     "atualizado_em = NOW(), atualizado_por = 'migration_fix_float_suffix'", False),
    ('programacao_producao', 'cod_produto', None, False),
    ('recursos_producao', 'cod_produto', None, False),
    ('previsao_demanda', 'cod_produto', None, False),
    ('custo_considerado', 'cod_produto', None, False),
]


def _strip_dot_zero(value: str) -> str:
    """Remove sufixo .0 de string numerica: '4210155.0' -> '4210155'."""
    if value.endswith('.0') and value[:-2].isdigit():
        return value[:-2]
    return value


def diagnostico(conn):
    """Conta registros com sufixo .0 em cada tabela."""
    print("\n=== DIAGNOSTICO: cod_produto com sufixo '.0' ===\n")
    total = 0
    for tabela, coluna, _, _ in TABELAS_CORRECAO:
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} ~ :pattern"),
            {'pattern': REGEX_FLOAT_SUFFIX},
        )
        count = result.scalar()
        total += count
        status = f"  {count:>6} registros" if count > 0 else "      0 (limpo)"
        print(f"  {tabela}.{coluna:<20s} {status}")

        # Mostrar exemplos se houver registros afetados
        if count > 0:
            exemplos = conn.execute(
                text(f"SELECT {coluna} FROM {tabela} WHERE {coluna} ~ :pattern LIMIT 5"),
                {'pattern': REGEX_FLOAT_SUFFIX},
            ).fetchall()
            valores = [row[0] for row in exemplos]
            print(f"    exemplos: {valores}")

    print(f"\n  TOTAL: {total} registros afetados\n")
    return total


def corrigir(conn):
    """Remove sufixo .0 de cod_produto em todas as tabelas afetadas.

    Estrategia: busca registros afetados via SELECT, depois aplica UPDATE
    usando Python para a transformacao (evita complexidade de regex em SQL
    parametrizado via SQLAlchemy text()).
    """
    total_corrigido = 0

    for tabela, coluna, audit_clause, tem_unique in TABELAS_CORRECAO:
        # Buscar registros afetados
        rows = conn.execute(
            text(f"SELECT id, {coluna} FROM {tabela} WHERE {coluna} ~ :pattern"),
            {'pattern': REGEX_FLOAT_SUFFIX},
        ).fetchall()

        if not rows:
            continue

        # Para tabelas com UNIQUE, verificar conflitos
        skip_ids = set()
        if tem_unique:
            # Buscar valores-alvo que ja existem
            for row_id, valor_atual in rows:
                valor_corrigido = _strip_dot_zero(valor_atual)
                conflito = conn.execute(
                    text(f"SELECT id FROM {tabela} WHERE {coluna} = :val AND id != :rid"),
                    {'val': valor_corrigido, 'rid': row_id},
                ).fetchone()
                if conflito:
                    skip_ids.add(row_id)
                    print(f"  AVISO: {tabela}.{coluna} id={row_id}: "
                          f"'{valor_atual}' -> '{valor_corrigido}' CONFLITO (id={conflito[0]} ja existe)")

        # Aplicar UPDATE por lote
        ids_para_corrigir = [r[0] for r in rows if r[0] not in skip_ids]
        if not ids_para_corrigir:
            continue

        set_clause = f"{coluna} = REGEXP_REPLACE({coluna}, :regex, '')"
        if audit_clause:
            set_clause += f", {audit_clause}"

        result = conn.execute(
            text(f"UPDATE {tabela} SET {set_clause} WHERE id = ANY(:ids)"),
            {'regex': r'\.0$', 'ids': ids_para_corrigir},
        )
        count = result.rowcount
        total_corrigido += count
        if count > 0:
            print(f"  {tabela}.{coluna:<20s}  {count} registros corrigidos")

    return total_corrigido


def main():
    app = create_app()
    with app.app_context():
        # ANTES
        with db.engine.connect() as conn:
            total_antes = diagnostico(conn)

        if total_antes == 0:
            print("Nenhum registro para corrigir. Banco ja esta limpo.")
            return

        # Confirmar execucao
        if '--dry-run' in sys.argv:
            print("=== DRY RUN: nenhuma alteracao foi feita ===")
            return

        resposta = input(f"\nCorrigir {total_antes} registros? (s/N): ").strip().lower()
        if resposta != 's':
            print("Cancelado pelo usuario.")
            return

        # CORRIGIR
        with db.engine.begin() as conn:
            total_corrigido = corrigir(conn)

        print(f"\n=== {total_corrigido} registros corrigidos ===\n")

        # DEPOIS
        with db.engine.connect() as conn:
            total_depois = diagnostico(conn)

        if total_depois > 0:
            print(f"AVISO: {total_depois} registros restantes (conflitos UNIQUE — resolver manualmente)")
        else:
            print("SUCESSO: 0 registros com sufixo '.0' restantes.")


if __name__ == '__main__':
    main()

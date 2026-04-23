"""Migration HORA 12: redesign do recebimento (conferencia cega + auditoria).

Adiciona:
- hora_recebimento: qtd_declarada, finalizado_em, amplia status para VARCHAR(30).
- hora_recebimento_conferencia: ordem, confirmado_em, modelo_id_conferido,
  cor_conferida, avaria_fisica, substituida, substituida_por_id.
- hora_conferencia_divergencia (tabela nova, 1-N por conferencia).
- hora_conferencia_auditoria (tabela nova, append-only).

Troca UNIQUE(recebimento_id, numero_chassi) por UNIQUE PARCIAL com substituida=false.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def tabela_existe(nome: str) -> bool:
    return bool(db.session.execute(
        db.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ),
        {'t': nome},
    ).scalar())


def coluna_existe(tabela: str, coluna: str) -> bool:
    return bool(db.session.execute(
        db.text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {'t': tabela, 'c': coluna},
    ).scalar())


def verificar_antes():
    print("[BEFORE]")
    print(f"  hora_recebimento.qtd_declarada existe? "
          f"{coluna_existe('hora_recebimento', 'qtd_declarada')}")
    print(f"  hora_recebimento_conferencia.ordem existe? "
          f"{coluna_existe('hora_recebimento_conferencia', 'ordem')}")
    print(f"  hora_conferencia_divergencia existe? "
          f"{tabela_existe('hora_conferencia_divergencia')}")
    print(f"  hora_conferencia_auditoria existe? "
          f"{tabela_existe('hora_conferencia_auditoria')}")


def executar_migration():
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'hora_12_recebimento_conferencia_cega.sql',
    )
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    assert coluna_existe('hora_recebimento', 'qtd_declarada')
    assert coluna_existe('hora_recebimento', 'finalizado_em')
    assert coluna_existe('hora_recebimento_conferencia', 'ordem')
    assert coluna_existe('hora_recebimento_conferencia', 'confirmado_em')
    assert coluna_existe('hora_recebimento_conferencia', 'modelo_id_conferido')
    assert coluna_existe('hora_recebimento_conferencia', 'cor_conferida')
    assert coluna_existe('hora_recebimento_conferencia', 'avaria_fisica')
    assert coluna_existe('hora_recebimento_conferencia', 'substituida')
    assert coluna_existe('hora_recebimento_conferencia', 'substituida_por_id')
    assert tabela_existe('hora_conferencia_divergencia')
    assert tabela_existe('hora_conferencia_auditoria')
    print("[AFTER] Todos os objetos presentes")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 12 concluida")

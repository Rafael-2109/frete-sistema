#!/usr/bin/env python3
"""
Migration: Remover extensao unaccent para viabilizar upgrade PG 16 -> 18
Data: 2026-02-18
Descricao: Substitui f_unaccent() (wrapper da extensao unaccent) por funcao pura
           baseada em translate(), eliminando dependencia da extensao.
           O modulo comercial/diretoria continua chamando f_unaccent() normalmente.

ARTEFATOS REMOVIDOS:
    - Extensao: unaccent
    - Funcao: f_unaccent(text) (wrapper antigo)
    - Indice: idx_carteira_raz_social_red_unaccent (residual)

ARTEFATOS CRIADOS:
    - Funcao: f_unaccent(text) (nova, baseada em translate())
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado antes da migration"""
    # Verificar se extensao unaccent existe
    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_extension WHERE extname = 'unaccent'
        )
    """))
    extensao_existe = result.scalar()

    # Verificar se funcao f_unaccent existe
    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_proc
            WHERE proname = 'f_unaccent'
        )
    """))
    funcao_existe = result.scalar()

    # Verificar todos os indices que dependem de f_unaccent
    result = conn.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE indexname IN (
            'idx_carteira_raz_social_red_unaccent',
            'idx_carteira_raz_social_unaccent',
            'idx_carteira_pedido_cliente_unaccent',
            'idx_carteira_num_pedido_unaccent'
        )
        ORDER BY indexname
    """))
    indices_existentes = [row[0] for row in result]

    print(f"[BEFORE] Extensao unaccent existe: {extensao_existe}")
    print(f"[BEFORE] Funcao f_unaccent existe: {funcao_existe}")
    print(f"[BEFORE] Indices dependentes encontrados: {indices_existentes or '(nenhum)'}")

    return extensao_existe, funcao_existe, indices_existentes


def executar_migration(extensao_existe, funcao_existe, indices_existentes):
    """Executa a migration dentro de uma transacao"""
    with db.engine.begin() as conn:
        # 1. Dropar TODOS os indices que dependem de f_unaccent
        todos_indices = [
            'idx_carteira_raz_social_red_unaccent',
            'idx_carteira_raz_social_unaccent',
            'idx_carteira_pedido_cliente_unaccent',
            'idx_carteira_num_pedido_unaccent',
        ]
        for idx in todos_indices:
            if idx in indices_existentes:
                print(f"[EXEC] Dropando indice {idx}...")
                conn.execute(db.text(f"DROP INDEX IF EXISTS {idx}"))
                print(f"[EXEC] Indice {idx} dropado.")
            else:
                print(f"[EXEC] Indice {idx} nao existe, pulando.")

        # 2. Dropar funcao wrapper antiga
        if funcao_existe:
            print("[EXEC] Dropando funcao f_unaccent antiga...")
            conn.execute(db.text(
                "DROP FUNCTION IF EXISTS f_unaccent(text)"
            ))
            print("[EXEC] Funcao antiga dropada.")
        else:
            print("[EXEC] Funcao f_unaccent nao existe, pulando drop.")

        # 3. Criar funcao substituta pura (baseada em translate)
        print("[EXEC] Criando funcao f_unaccent pura (translate)...")
        conn.execute(db.text("""
            CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text AS $$
              SELECT translate(
                $1,
                'áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇñÑ',
                'aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUCnN'
              );
            $$ LANGUAGE sql IMMUTABLE STRICT
        """))
        print("[EXEC] Funcao f_unaccent pura criada.")

        # 4. Dropar extensao unaccent
        if extensao_existe:
            print("[EXEC] Dropando extensao unaccent...")
            conn.execute(db.text(
                "DROP EXTENSION IF EXISTS unaccent"
            ))
            print("[EXEC] Extensao unaccent dropada.")
        else:
            print("[EXEC] Extensao unaccent nao existe, pulando.")


def verificar_depois(conn):
    """Verifica estado apos a migration"""
    # Extensao deve NAO existir
    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_extension WHERE extname = 'unaccent'
        )
    """))
    extensao_existe = result.scalar()

    # Funcao f_unaccent deve existir (a nova, pura)
    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_proc
            WHERE proname = 'f_unaccent'
        )
    """))
    funcao_existe = result.scalar()

    # Nenhum indice dependente deve existir
    result = conn.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE indexname IN (
            'idx_carteira_raz_social_red_unaccent',
            'idx_carteira_raz_social_unaccent',
            'idx_carteira_pedido_cliente_unaccent',
            'idx_carteira_num_pedido_unaccent'
        )
    """))
    indices_restantes = [row[0] for row in result]

    # Testar funcao substituta
    result = conn.execute(db.text(
        "SELECT f_unaccent('São Paulo')"
    ))
    teste_sp = result.scalar()

    result = conn.execute(db.text(
        "SELECT f_unaccent('INDÚSTRIA')"
    ))
    teste_ind = result.scalar()

    result = conn.execute(db.text(
        "SELECT f_unaccent('café')"
    ))
    teste_cafe = result.scalar()

    print(f"[AFTER] Extensao unaccent existe: {extensao_existe}")
    print(f"[AFTER] Funcao f_unaccent existe: {funcao_existe}")
    print(f"[AFTER] Indices restantes: {indices_restantes or '(nenhum)'}")
    print(f"[AFTER] f_unaccent('São Paulo') = '{teste_sp}'")
    print(f"[AFTER] f_unaccent('INDÚSTRIA') = '{teste_ind}'")
    print(f"[AFTER] f_unaccent('café') = '{teste_cafe}'")

    # Validacoes
    erros = []
    if extensao_existe:
        erros.append("Extensao unaccent ainda existe!")
    if not funcao_existe:
        erros.append("Funcao f_unaccent nao foi criada!")
    if indices_restantes:
        erros.append(f"Indices ainda existem: {indices_restantes}")
    if teste_sp != 'Sao Paulo':
        erros.append(f"f_unaccent('São Paulo') retornou '{teste_sp}' (esperado: 'Sao Paulo')")
    if teste_ind != 'INDUSTRIA':
        erros.append(f"f_unaccent('INDÚSTRIA') retornou '{teste_ind}' (esperado: 'INDUSTRIA')")
    if teste_cafe != 'cafe':
        erros.append(f"f_unaccent('café') retornou '{teste_cafe}' (esperado: 'cafe')")

    if erros:
        for e in erros:
            print(f"[ERRO] {e}")
        sys.exit(1)
    else:
        print("\n[OK] Migration concluida com sucesso!")
        print("[OK] Extensao unaccent removida, funcao f_unaccent pura ativa.")
        print("[OK] Upgrade PG 16 -> 18 desbloqueado.")


def main():
    app = create_app()
    with app.app_context():
        # BEFORE — conexao separada
        with db.engine.connect() as conn:
            extensao_existe, funcao_existe, indices_existentes = verificar_antes(conn)

        # EXECUTE — transacao auto-commit
        executar_migration(extensao_existe, funcao_existe, indices_existentes)

        # AFTER — conexao separada
        with db.engine.connect() as conn:
            verificar_depois(conn)


if __name__ == '__main__':
    main()

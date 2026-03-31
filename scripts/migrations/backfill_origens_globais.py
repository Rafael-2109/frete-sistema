"""
Migration: Converter origens por cliente em origens globais
============================================================

Origens (tipo=ORIGEM) devem ser SEMPRE globais (cliente_id=NULL).
Este script:
  1. Identifica origens com cliente_id NOT NULL
  2. Para cada uma, verifica se ja existe global com mesmo CNPJ
     - Se sim: re-aponta FKs (cotacoes) para a global e deleta a por-cliente
     - Se nao: converte para global (seta cliente_id=NULL)
  3. Mostra resumo

Uso:
    source .venv/bin/activate && python scripts/migrations/backfill_origens_globais.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_antes():
    """Mostra estado atual."""
    result = db.session.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE cliente_id IS NOT NULL AND tipo = 'ORIGEM') AS origens_cliente,
            COUNT(*) FILTER (WHERE cliente_id IS NULL AND tipo = 'ORIGEM') AS origens_globais,
            COUNT(*) FILTER (WHERE tipo = 'DESTINO') AS destinos
        FROM carvia_cliente_enderecos
    """))
    row = result.fetchone()
    print(f"  Origens por cliente: {row[0]}")
    print(f"  Origens globais:     {row[1]}")
    print(f"  Destinos:            {row[2]}")
    return row[0]  # qtd origens por cliente


def executar_migration():
    """Converte origens por cliente em globais."""

    # 1. Listar origens por cliente
    origens_cliente = db.session.execute(text("""
        SELECT id, cliente_id, cnpj, razao_social, fisico_uf, fisico_cidade,
               fisico_logradouro, fisico_numero, fisico_bairro, fisico_cep,
               fisico_complemento, receita_uf, receita_cidade, receita_logradouro,
               receita_numero, receita_bairro, receita_cep, receita_complemento,
               principal, criado_por, criado_em
        FROM carvia_cliente_enderecos
        WHERE tipo = 'ORIGEM' AND cliente_id IS NOT NULL
        ORDER BY id
    """)).fetchall()

    if not origens_cliente:
        print("[SKIP] Nenhuma origem por cliente encontrada.")
        return

    convertidas = 0
    mescladas = 0
    relink_cotacoes = 0

    for orig in origens_cliente:
        orig_id = orig[0]
        cnpj = orig[2]

        if not cnpj:
            # Origem sem CNPJ — converter direto para global
            db.session.execute(text("""
                UPDATE carvia_cliente_enderecos
                SET cliente_id = NULL
                WHERE id = :id
            """), {'id': orig_id})
            convertidas += 1
            print(f"  [CONVERTIDA] id={orig_id} (sem CNPJ) -> global")
            continue

        # Verificar se ja existe global com mesmo CNPJ
        global_existente = db.session.execute(text("""
            SELECT id FROM carvia_cliente_enderecos
            WHERE tipo = 'ORIGEM' AND cliente_id IS NULL AND cnpj = :cnpj
            LIMIT 1
        """), {'cnpj': cnpj}).fetchone()

        if global_existente:
            global_id = global_existente[0]
            # Re-apontar cotacoes que usam esta origem para a global
            updated = db.session.execute(text("""
                UPDATE carvia_cotacoes
                SET endereco_origem_id = :global_id
                WHERE endereco_origem_id = :old_id
            """), {'global_id': global_id, 'old_id': orig_id})
            relink_cotacoes += updated.rowcount

            # Deletar a origem por cliente (agora orfã)
            db.session.execute(text("""
                DELETE FROM carvia_cliente_enderecos WHERE id = :id
            """), {'id': orig_id})
            mescladas += 1
            print(f"  [MESCLADA] id={orig_id} cnpj={cnpj} -> global id={global_id} ({updated.rowcount} cotacoes re-linkadas)")
        else:
            # Converter para global
            db.session.execute(text("""
                UPDATE carvia_cliente_enderecos
                SET cliente_id = NULL
                WHERE id = :id
            """), {'id': orig_id})
            convertidas += 1
            print(f"  [CONVERTIDA] id={orig_id} cnpj={cnpj} -> global")

    db.session.commit()
    print(f"\n  Resultado: {convertidas} convertidas, {mescladas} mescladas, {relink_cotacoes} cotacoes re-linkadas")


def verificar_depois():
    """Valida que nao restam origens por cliente."""
    result = db.session.execute(text("""
        SELECT COUNT(*) FROM carvia_cliente_enderecos
        WHERE tipo = 'ORIGEM' AND cliente_id IS NOT NULL
    """)).scalar()
    if result == 0:
        print("  [OK] Zero origens por cliente restantes.")
    else:
        print(f"  [ATENCAO] Ainda restam {result} origens por cliente!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: Converter origens por cliente em globais")
        print("=" * 60)

        print("\n[ANTES]")
        qtd = verificar_antes()

        if qtd == 0:
            print("\n[SKIP] Nenhuma origem por cliente. Migration idempotente.")
        else:
            print(f"\n[EXECUTANDO] Processando {qtd} origens por cliente...")
            executar_migration()

        print("\n[DEPOIS]")
        verificar_depois()
        print("\n[CONCLUIDO]")

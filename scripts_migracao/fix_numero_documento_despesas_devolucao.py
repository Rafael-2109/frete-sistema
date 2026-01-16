"""
Script de correção: Corrige numero_documento de despesas de devolução

Despesas de devolução estavam sendo criadas com numero_documento='NFD-XXXX',
mas o lançamento de freteiros filtra apenas:
- numero_documento IS NULL
- numero_documento = ''
- numero_documento = 'PENDENTE_FATURA'

Este script corrige despesas existentes para que apareçam no lançamento de freteiros.

Data: 2025-01-16
"""
import sys
import os

# Adiciona o diretório raiz ao path para importar os módulos da aplicação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def listar_despesas_afetadas():
    """Lista despesas de devolução com numero_documento incorreto"""
    app = create_app()
    with app.app_context():
        try:
            resultado = db.session.execute(text("""
                SELECT
                    de.id,
                    de.tipo_despesa,
                    de.numero_documento,
                    de.numero_nfd,
                    de.transportadora_id,
                    de.frete_id,
                    f.transportadora_id as transportadora_frete_id
                FROM despesas_extras de
                JOIN fretes f ON de.frete_id = f.id
                WHERE de.tipo_despesa = 'DEVOLUÇÃO'
                AND de.numero_documento IS NOT NULL
                AND de.numero_documento != ''
                AND de.numero_documento != 'PENDENTE_FATURA'
                AND de.numero_documento NOT LIKE '%CTe%'
                ORDER BY de.id DESC
            """))

            despesas = resultado.fetchall()

            if not despesas:
                print("Nenhuma despesa de devolução com numero_documento incorreto encontrada.")
                return

            print(f"\n{'='*80}")
            print(f"DESPESAS DE DEVOLUÇÃO COM numero_documento INCORRETO")
            print(f"{'='*80}")
            print(f"\n{'ID':<8} {'Tipo':<12} {'Documento Atual':<20} {'NFD':<15} {'Transp Desp':<12} {'Transp Frete':<12}")
            print("-" * 80)

            for d in despesas:
                transp_desp = d[4] if d[4] else '-'
                transp_frete = d[6]
                alternativa = '*' if d[4] and d[4] != d[6] else ''
                print(f"{d[0]:<8} {d[1]:<12} {d[2]:<20} {d[3] or '-':<15} {transp_desp:<12} {transp_frete:<12} {alternativa}")

            print(f"\nTotal: {len(despesas)} despesas")
            print("* = Transportadora alternativa (diferente do frete)")

        except Exception as e:
            print(f"Erro: {e}")


def corrigir_despesas():
    """Corrige numero_documento de despesas de devolução"""
    app = create_app()
    with app.app_context():
        try:
            # Primeiro, lista as despesas que serão afetadas
            resultado = db.session.execute(text("""
                SELECT COUNT(*)
                FROM despesas_extras
                WHERE tipo_despesa = 'DEVOLUÇÃO'
                AND numero_documento IS NOT NULL
                AND numero_documento != ''
                AND numero_documento != 'PENDENTE_FATURA'
                AND numero_documento NOT LIKE '%CTe%'
            """))

            total = resultado.scalar()

            if total == 0:
                print("Nenhuma despesa para corrigir.")
                return

            print(f"\n{total} despesas serão corrigidas...")

            # Executa a correção
            db.session.execute(text("""
                UPDATE despesas_extras
                SET
                    numero_documento = 'PENDENTE_FATURA',
                    tipo_documento = 'PENDENTE_DOCUMENTO'
                WHERE tipo_despesa = 'DEVOLUÇÃO'
                AND numero_documento IS NOT NULL
                AND numero_documento != ''
                AND numero_documento != 'PENDENTE_FATURA'
                AND numero_documento NOT LIKE '%CTe%'
            """))

            db.session.commit()
            print(f"✅ {total} despesas corrigidas com sucesso!")
            print("   numero_documento = 'PENDENTE_FATURA'")
            print("   tipo_documento = 'PENDENTE_DOCUMENTO'")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fix: Corrige numero_documento de despesas de devolução')
    parser.add_argument('--listar', action='store_true', help='Apenas listar despesas afetadas')
    parser.add_argument('--corrigir', action='store_true', help='Executar correção')

    args = parser.parse_args()

    if args.listar:
        listar_despesas_afetadas()
    elif args.corrigir:
        corrigir_despesas()
    else:
        print("Use --listar para ver despesas afetadas ou --corrigir para executar a correção")
        print("\nExemplo:")
        print("  python fix_numero_documento_despesas_devolucao.py --listar")
        print("  python fix_numero_documento_despesas_devolucao.py --corrigir")

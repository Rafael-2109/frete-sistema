"""
Script: Limpar erro_lancamento de registros com status LANCADO.

Problema: 160+ registros têm status='LANCADO' (sucesso) mas mantêm
erro_lancamento preenchido com mensagens como:
- "já estão reconciliados" (142 registros)
- "não há mais nada a pagar" (17 registros)
- "ensure_one" (1 registro)

Esses erros são residuais — o lançamento FOI realizado com sucesso
(status=LANCADO) mas o campo de erro não foi limpo.

Impacto: Causa confusão em relatórios e consultas do agente.

Uso local:
    source .venv/bin/activate
    python scripts/fix_erro_lancamento_lancado.py

Uso Render Shell:
    python scripts/fix_erro_lancamento_lancado.py

Data: 06/02/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def limpar_erro_lancamento():
    """Limpa erro_lancamento de registros que foram lançados com sucesso."""
    app = create_app()
    with app.app_context():
        # 1. Diagnóstico: quantos registros afetados
        diagnostico = db.session.execute(text("""
            SELECT
                erro_lancamento,
                COUNT(*) as qtd
            FROM lancamento_comprovante
            WHERE status = 'LANCADO' AND erro_lancamento IS NOT NULL
            GROUP BY erro_lancamento
            ORDER BY qtd DESC
        """))
        rows = diagnostico.fetchall()

        if not rows:
            print("Nenhum registro LANCADO com erro_lancamento encontrado. Nada a fazer.")
            return

        print("=== DIAGNÓSTICO ===")
        total = 0
        for row in rows:
            print(f"  [{row[1]:>3}] {row[0][:80]}")
            total += row[1]
        print(f"  Total: {total} registros")
        print()

        # 2. Executar limpeza
        result = db.session.execute(text("""
            UPDATE lancamento_comprovante
            SET erro_lancamento = NULL
            WHERE status = 'LANCADO' AND erro_lancamento IS NOT NULL
        """))
        print(f"=== LIMPEZA ===")
        print(f"  Registros atualizados: {result.rowcount}")

        # 3. Commit
        db.session.commit()
        print("  Commit realizado com sucesso.")

        # 4. Verificação
        verificacao = db.session.execute(text("""
            SELECT COUNT(*)
            FROM lancamento_comprovante
            WHERE status = 'LANCADO' AND erro_lancamento IS NOT NULL
        """))
        restantes = verificacao.scalar()
        print(f"\n=== VERIFICAÇÃO ===")
        print(f"  Registros LANCADO com erro_lancamento restantes: {restantes}")

        if restantes == 0:
            print("  OK — Limpeza completa.")
        else:
            print(f"  AVISO — Ainda restam {restantes} registros (verificar manualmente).")


if __name__ == '__main__':
    limpar_erro_lancamento()

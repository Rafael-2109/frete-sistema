"""Migration one-shot (R18): REVERTER arquivamento 'Cancelada por Transferencia'.

Historico da abordagem R18:
1. Primeira versao (descartada): ao virar transferencia efetiva, a
   EntregaMonitorada era marcada com status_finalizacao='Cancelada por
   Transferencia'. Problema: status ambiguo — a NF nao foi cancelada, ela
   apenas nao deve ser monitorada.
2. Versao final (atual): a visibilidade e controlada por FILTRO na query
   de `/monitoramento/listar_entregas` (ver `app/monitoramento/routes.py`).
   NAO alteramos status — preservamos historico e evitamos ambiguidade.

Esta migration:
- Reverte eventuais arquivamentos feitos pela versao descartada (se algum
  ambiente rodou a 1a versao antes do fix).
- Idempotente: WHERE status_finalizacao='Cancelada por Transferencia'
  impede re-execucao pisando em outras linhas.
- Seguro: apenas toca linhas com esse status especifico.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Conta linhas com status 'Cancelada por Transferencia'."""
    total = db.session.execute(db.text("""
        SELECT COUNT(*)
        FROM entregas_monitoradas
        WHERE origem = 'CARVIA'
          AND status_finalizacao = 'Cancelada por Transferencia'
    """)).scalar()
    print(f"[BEFORE] {total} EntregaMonitorada com status 'Cancelada por Transferencia' (a reverter)")
    return total


def executar_migration():
    """Reverte status para NULL (remove marcacao)."""
    resultado = db.session.execute(db.text("""
        UPDATE entregas_monitoradas
        SET status_finalizacao = NULL,
            finalizado_por = NULL,
            finalizado_em = NULL
        WHERE origem = 'CARVIA'
          AND status_finalizacao = 'Cancelada por Transferencia'
    """))
    db.session.commit()
    print(f"[OK] {resultado.rowcount} EntregaMonitorada revertidas (status_finalizacao=NULL)")


def verificar_depois():
    """Confirma que nenhuma linha resta com esse status."""
    restantes = db.session.execute(db.text("""
        SELECT COUNT(*)
        FROM entregas_monitoradas
        WHERE status_finalizacao = 'Cancelada por Transferencia'
    """)).scalar()
    print(f"[AFTER] {restantes} linhas com status 'Cancelada por Transferencia' (esperado: 0)")
    assert restantes == 0, f"Esperado 0, obtido {restantes}"


def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration R18: REVERTER 'Cancelada por Transferencia'")
        print("=" * 60)
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("=" * 60)
        print("Migration concluida com sucesso.")


if __name__ == '__main__':
    main()

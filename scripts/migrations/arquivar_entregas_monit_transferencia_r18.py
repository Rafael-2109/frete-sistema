"""Migration one-shot (R18): arquivar EntregaMonitorada de NF transferencia efetiva.

Contexto: ate esta data, o sync CarVia -> EntregaMonitorada criava linha
autonoma para QUALQUER CarviaNf importada, incluindo NFs que posteriormente
viraram transferencia efetiva (vinculadas via carvia_nf_vinculos_transferencia).

Apos a correcao R18 em sincronizar_entregas_carvia.py, novas importacoes
ja skippam transferencias efetivas. Esta migration limpa o historico:
marca `status_finalizacao='Cancelada por Transferencia'` nas entregas ja
existentes que se tornaram transferencias efetivas, preservando historico
de agendamentos/comentarios (nao deleta).

Regras de seguranca:
- Se operador ja finalizou manualmente (status_finalizacao IS NOT NULL),
  a entrega e preservada — nao sobrescrevemos trabalho manual.
- Limitacao conhecida: `carvia_nfs.numero_nf` NAO e unique (mesma NF em
  emitentes diferentes). Filtramos por `cn.status = 'ATIVA'` para alinhar
  com o criterio do sync original (sincronizar_entregas_carvia.py usa
  `filter_by(numero_nf=..., status='ATIVA')`). Ainda assim, se duas
  CarviaNf ATIVAS tiverem mesmo numero_nf e apenas uma for transferencia
  efetiva, a EntregaMonitorada correspondente sera arquivada — o mesmo
  comportamento herdado do sync, nao e regressao desta migration.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Conta EntregaMonitorada origem=CARVIA que sao transferencia efetiva."""
    total_candidatas = db.session.execute(db.text("""
        SELECT COUNT(*)
        FROM entregas_monitoradas em
        JOIN carvia_nfs cn ON cn.numero_nf = em.numero_nf AND cn.status = 'ATIVA'
        JOIN carvia_nf_vinculos_transferencia vt ON vt.nf_transferencia_id = cn.id
        WHERE em.origem = 'CARVIA'
          AND em.status_finalizacao IS NULL
    """)).scalar()
    ja_finalizadas = db.session.execute(db.text("""
        SELECT COUNT(*)
        FROM entregas_monitoradas em
        JOIN carvia_nfs cn ON cn.numero_nf = em.numero_nf AND cn.status = 'ATIVA'
        JOIN carvia_nf_vinculos_transferencia vt ON vt.nf_transferencia_id = cn.id
        WHERE em.origem = 'CARVIA'
          AND em.status_finalizacao IS NOT NULL
    """)).scalar()
    print(f"[BEFORE] {total_candidatas} EntregaMonitorada a arquivar")
    print(f"[BEFORE] {ja_finalizadas} ja finalizadas (serao preservadas)")
    return total_candidatas


def executar_migration():
    """Arquiva as EntregaMonitorada elegiveis (preserva finalizadas)."""
    resultado = db.session.execute(db.text("""
        UPDATE entregas_monitoradas em
        SET status_finalizacao = 'Cancelada por Transferencia',
            finalizado_por = 'Sistema CarVia (R18 migration)',
            finalizado_em = NOW()
        FROM carvia_nfs cn
        JOIN carvia_nf_vinculos_transferencia vt
          ON vt.nf_transferencia_id = cn.id
        WHERE em.origem = 'CARVIA'
          AND em.status_finalizacao IS NULL
          AND cn.numero_nf = em.numero_nf
          AND cn.status = 'ATIVA'
    """))
    db.session.commit()
    print(f"[OK] {resultado.rowcount} EntregaMonitorada arquivadas")


def verificar_depois():
    """Verifica que nao restam transferencias efetivas ativas."""
    restantes = db.session.execute(db.text("""
        SELECT COUNT(*)
        FROM entregas_monitoradas em
        JOIN carvia_nfs cn ON cn.numero_nf = em.numero_nf AND cn.status = 'ATIVA'
        JOIN carvia_nf_vinculos_transferencia vt ON vt.nf_transferencia_id = cn.id
        WHERE em.origem = 'CARVIA'
          AND em.status_finalizacao IS NULL
    """)).scalar()
    arquivadas = db.session.execute(db.text("""
        SELECT COUNT(*)
        FROM entregas_monitoradas
        WHERE origem = 'CARVIA'
          AND status_finalizacao = 'Cancelada por Transferencia'
    """)).scalar()
    print(f"[AFTER] {restantes} transferencias efetivas ainda ATIVAS (esperado: 0)")
    print(f"[AFTER] {arquivadas} EntregaMonitorada com status 'Cancelada por Transferencia'")
    assert restantes == 0, f"Esperado 0 transferencias efetivas ativas, obtido {restantes}"


def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration R18: arquivar EntregaMonitorada de transferencias")
        print("=" * 60)
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("=" * 60)
        print("Migration concluida com sucesso.")


if __name__ == '__main__':
    main()

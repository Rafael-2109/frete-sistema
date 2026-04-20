"""
Reconciliacao historica: converte linhas de LancamentoFreteOdooAuditoria
com status=ERRO para status=SUCESSO quando o lancamento JA FOI COMPLETADO
(frete/despesa em LANCADO_ODOO OU auditoria etapa=16 SUCESSO para o mesmo
frete_id/despesa_extra_id).

Motivacao:
    Varias operacoes do lancamento (ETAPA 6, 11, 13, 15, ...) falham
    transitoriamente (timeout upstream, 502 Bad Gateway, corrida de estado
    'deve ser provisorio', etc.) mas sao retomadas com sucesso numa execucao
    posterior. A retomada re-executa a etapa e gera uma nova linha SUCESSO,
    porem a linha ERRO original fica no historico e inflaciona o Sentry /
    relatorios operacionais.

Criterio de reconciliacao:
    Auditoria status='ERRO' E (qualquer uma):
      - fretes.id = auditoria.frete_id com status='LANCADO_ODOO'
      - despesas_extras.id = auditoria.despesa_extra_id com status='LANCADO_ODOO'
      - EXISTS auditoria etapa=16 status='SUCESSO' para o mesmo frete_id/despesa_extra_id

Acao:
    UPDATE status='SUCESSO', mensagem concatenada com ' | Reconciliado por
    script (<timestamp UTC>): lancamento foi completado posteriormente'.
    Se o campo purchase_order_id estiver NULL e o frete/despesa tiver PO
    confirmado, tambem preenche.

Uso (Render Shell):
    cd /opt/render/project/src && python scripts/migrations/reconciliar_auditoria_erro_to_sucesso.py
    # dry-run (nao altera):
    python scripts/migrations/reconciliar_auditoria_erro_to_sucesso.py --dry-run

Idempotente: so atualiza linhas com status='ERRO'.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Apenas reporta, nao altera')
    args = parser.parse_args()

    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        sql_select = text(
            """
            WITH completos_frete AS (
                SELECT id AS frete_id, odoo_purchase_order_id AS po_final
                  FROM fretes
                 WHERE status = 'LANCADO_ODOO'
            ),
            completos_despesa AS (
                SELECT id AS despesa_extra_id, odoo_purchase_order_id AS po_final
                  FROM despesas_extras
                 WHERE status = 'LANCADO_ODOO'
            ),
            concluiu16 AS (
                SELECT DISTINCT frete_id, despesa_extra_id, purchase_order_id AS po_final
                  FROM lancamento_frete_odoo_auditoria
                 WHERE etapa = 16 AND status = 'SUCESSO'
            )
            SELECT
                a.id AS audit_id,
                a.frete_id,
                a.despesa_extra_id,
                a.etapa,
                a.metodo_odoo,
                a.purchase_order_id AS po_atual,
                COALESCE(cf.po_final, cd.po_final, c16f.po_final, c16d.po_final) AS po_detectado,
                CASE
                    WHEN cf.frete_id IS NOT NULL THEN 'frete LANCADO_ODOO'
                    WHEN cd.despesa_extra_id IS NOT NULL THEN 'despesa LANCADO_ODOO'
                    WHEN c16f.frete_id IS NOT NULL THEN 'audit etapa 16 SUCESSO (frete)'
                    WHEN c16d.despesa_extra_id IS NOT NULL THEN 'audit etapa 16 SUCESSO (despesa)'
                END AS fonte,
                a.executado_em
            FROM lancamento_frete_odoo_auditoria a
            LEFT JOIN completos_frete cf ON cf.frete_id = a.frete_id AND a.frete_id IS NOT NULL
            LEFT JOIN completos_despesa cd ON cd.despesa_extra_id = a.despesa_extra_id AND a.despesa_extra_id IS NOT NULL
            LEFT JOIN concluiu16 c16f ON c16f.frete_id = a.frete_id AND a.frete_id IS NOT NULL
            LEFT JOIN concluiu16 c16d ON c16d.despesa_extra_id = a.despesa_extra_id AND a.despesa_extra_id IS NOT NULL
            WHERE a.status = 'ERRO'
              AND (
                  cf.frete_id IS NOT NULL
               OR cd.despesa_extra_id IS NOT NULL
               OR c16f.frete_id IS NOT NULL
               OR c16d.despesa_extra_id IS NOT NULL
              )
            ORDER BY a.etapa, a.executado_em DESC
            """
        )

        candidatos = db.session.execute(sql_select).mappings().all()

        print(f"[RECONCILIAR] Encontrados {len(candidatos)} candidato(s) ERRO em lancamentos completos.")

        # Sumario por etapa
        from collections import Counter
        por_etapa = Counter(row['etapa'] for row in candidatos)
        for etapa in sorted(por_etapa):
            print(f"  etapa {etapa:02d}: {por_etapa[etapa]} ocorrencia(s)")

        if not candidatos:
            print("[RECONCILIAR] Nada a fazer.")
            return 0

        if args.dry_run:
            print("\n[RECONCILIAR] Detalhe (primeiros 20):")
            for row in candidatos[:20]:
                print(
                    f"  audit_id={row['audit_id']} etapa={row['etapa']} "
                    f"frete={row['frete_id']} despesa={row['despesa_extra_id']} "
                    f"metodo={row['metodo_odoo']} fonte={row['fonte']} "
                    f"po_detectado={row['po_detectado']}"
                )
            print("[RECONCILIAR] --dry-run ativo: nenhum UPDATE executado.")
            return 0

        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        sql_update = text(
            """
            UPDATE lancamento_frete_odoo_auditoria
               SET status = 'SUCESSO',
                   purchase_order_id = COALESCE(purchase_order_id, :po_detectado),
                   mensagem = COALESCE(mensagem, '')
                       || ' | Reconciliado por script (' || :stamp
                       || '): lancamento foi completado posteriormente (fonte: ' || :fonte || ')'
             WHERE id = :audit_id
               AND status = 'ERRO'
            """
        )

        atualizados = 0
        for row in candidatos:
            result = db.session.execute(
                sql_update,
                {
                    'po_detectado': int(row['po_detectado']) if row['po_detectado'] else None,
                    'stamp': stamp,
                    'fonte': row['fonte'] or 'desconhecida',
                    'audit_id': int(row['audit_id']),
                },
            )
            if result.rowcount:
                atualizados += 1

        db.session.commit()
        print(f"\n[RECONCILIAR] {atualizados} auditoria(s) atualizada(s) para SUCESSO.")

        # Verificacao pos-UPDATE: auditorias ERRO remanescentes
        verif = db.session.execute(
            text(
                """
                SELECT etapa, COUNT(*) AS qtd
                FROM lancamento_frete_odoo_auditoria
                WHERE status = 'ERRO'
                GROUP BY etapa
                ORDER BY etapa
                """
            )
        ).mappings().all()
        print("[RECONCILIAR] Auditorias ERRO remanescentes (legitimas, em lancamentos NAO completados):")
        total_legitimo = 0
        for row in verif:
            print(f"  etapa {row['etapa']:02d}: {row['qtd']}")
            total_legitimo += row['qtd']
        print(f"  TOTAL: {total_legitimo}")

        return 0


if __name__ == '__main__':
    sys.exit(main())

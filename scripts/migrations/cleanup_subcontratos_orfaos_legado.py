"""
Cleanup: CTes Subcontrato orfaos do fluxo legado (pre-CarviaFrete)
===================================================================

Data fix (sem DDL) — remove CarviaSubcontrato criados via importacao
direta de CTe XML antes do pipeline unificado portaria -> CarviaFrete
-> CarviaSubcontrato.

Criterio de "orfao legado":
    frete_id IS NULL
    AND fatura_transportadora_id IS NULL
    AND status NOT IN ('FATURADO', 'CONFERIDO')

Tambem impoe:
  - 0 CarviaFaturaTransportadoraItem apontando via subcontrato_id
  - 0 CarviaCustoEntrega apontando (blindagem extra — FK tem SET NULL)
  - 0 CarviaFrete legado apontando via subcontrato_id

O delete usa AdminService.excluir_subcontrato_orfao() para garantir:
  - Desconciliacao: reverte CC compensadas + delete movs CC
  - Delete de aprovacoes pendentes
  - CarviaAdminAudit com snapshot completo (fonte unica de verdade
    pos-delete)

Modo dry-run: imprime os candidatos sem executar. Modo execucao:
processa um por um (cada sub = uma transacao), para que um erro
pontual nao abrande os demais.

Uso:
    # Dry-run (padrao — apenas lista)
    python scripts/migrations/cleanup_subcontratos_orfaos_legado.py

    # Execucao real
    python scripts/migrations/cleanup_subcontratos_orfaos_legado.py --execute

    # Execucao com motivo customizado
    python scripts/migrations/cleanup_subcontratos_orfaos_legado.py --execute \\
        --motivo "Limpeza backfill pre-fluxo-fatura 2026-04-13"

PRE-REQUISITO: schema atualizado com as migrations:
    - carvia_subcontratos.frete_id (vinculo CarviaFrete)
    - carvia_custos_entrega.subcontrato_id
    - carvia_aprovacoes_subcontrato (tabela)
    - carvia_conta_corrente_transportadoras (tabela)

Em ambientes locais com migrations atrasadas, o script falha com
UndefinedColumn. Destinado primariamente ao Render (producao). Para o
Render Shell, prefira `cleanup_subcontratos_orfaos_legado.sql`.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


QUERY_CANDIDATOS = text("""
    SELECT
        s.id,
        s.cte_numero,
        s.status,
        s.cte_valor,
        s.valor_cotado,
        s.criado_em::date AS criado,
        s.operacao_id,
        t.razao_social AS transportadora
    FROM carvia_subcontratos s
    LEFT JOIN transportadoras t ON t.id = s.transportadora_id
    WHERE s.frete_id IS NULL
      AND s.fatura_transportadora_id IS NULL
      AND s.status NOT IN ('FATURADO', 'CONFERIDO')
      -- Blindagem extra (espelha guards do AdminService.excluir_subcontrato_orfao
      -- e tmp_orfaos no SQL bulk — manter os 3 caminhos sincronizados)
      AND NOT EXISTS (
          SELECT 1 FROM carvia_fatura_transportadora_itens i
          WHERE i.subcontrato_id = s.id
      )
      AND NOT EXISTS (
          SELECT 1 FROM carvia_custos_entrega ce
          WHERE ce.subcontrato_id = s.id
      )
      AND NOT EXISTS (
          SELECT 1 FROM carvia_fretes f
          WHERE f.subcontrato_id = s.id
      )
      AND NOT EXISTS (
          SELECT 1 FROM carvia_conciliacoes c
          WHERE c.tipo_documento = 'subcontrato' AND c.documento_id = s.id
      )
      AND NOT EXISTS (
          SELECT 1 FROM carvia_conta_corrente_transportadoras cc
          WHERE cc.subcontrato_id = s.id
            AND cc.fatura_transportadora_id IS NOT NULL
      )
    ORDER BY s.id
""")


def listar_candidatos():
    """Retorna lista de dicts com os orfaos candidatos a exclusao."""
    rows = db.session.execute(QUERY_CANDIDATOS).fetchall()
    return [dict(r._mapping) for r in rows]


def imprimir_tabela(candidatos):
    if not candidatos:
        print("Nenhum candidato encontrado.")
        return

    print(f"\n{len(candidatos)} CTe(s) Subcontrato orfao(s) encontrado(s):\n")
    print(f"{'ID':>4} | {'CTe':>10} | {'Status':>11} | {'Valor':>10} | {'Criado':>10} | Transportadora")
    print("-" * 100)
    for c in candidatos:
        valor = float(c.get('cte_valor') or c.get('valor_cotado') or 0)
        print(
            f"{c['id']:>4} | "
            f"{(c['cte_numero'] or '-'):>10} | "
            f"{c['status']:>11} | "
            f"{valor:>10.2f} | "
            f"{str(c['criado']):>10} | "
            f"{(c['transportadora'] or '-')[:50]}"
        )
    print()


def executar(motivo, executado_por):
    from app.carvia.services.admin.admin_service import AdminService

    candidatos = listar_candidatos()
    if not candidatos:
        print("Nada a fazer — 0 candidatos.")
        return

    imprimir_tabela(candidatos)
    print(f"Motivo: {motivo}")
    print(f"Executor: {executado_por}\n")

    resposta = input(
        f"Confirma exclusao permanente de {len(candidatos)} subcontratos? (sim/NAO): "
    ).strip().lower()
    if resposta != 'sim':
        print("Abortado pelo usuario.")
        return

    service = AdminService()
    sucessos = 0
    falhas = []

    for cand in candidatos:
        sub_id = cand['id']
        try:
            resultado = service.excluir_subcontrato_orfao(
                sub_id=sub_id,
                motivo=motivo,
                executado_por=executado_por,
            )
            if resultado['sucesso']:
                print(f"  [OK] #{sub_id} {cand['cte_numero'] or ''} — audit #{resultado['auditoria_id']}")
                sucessos += 1
            else:
                print(f"  [FAIL] #{sub_id}: {resultado['mensagem']}")
                falhas.append((sub_id, resultado['mensagem']))
        except Exception as e:
            db.session.rollback()
            print(f"  [ERROR] #{sub_id}: {e}")
            falhas.append((sub_id, str(e)))

    print(f"\n==== RESUMO ====")
    print(f"Sucessos: {sucessos}/{len(candidatos)}")
    print(f"Falhas:   {len(falhas)}")
    if falhas:
        print("\nFalhas detalhadas:")
        for sid, msg in falhas:
            print(f"  #{sid}: {msg}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Executar delete real (sem esta flag, apenas lista candidatos)'
    )
    parser.add_argument(
        '--motivo',
        default='Limpeza CTes Subcontrato orfaos do fluxo legado pre-CarviaFrete',
        help='Motivo registrado em CarviaAdminAudit (min 10 chars)'
    )
    parser.add_argument(
        '--executor',
        default='admin@cleanup-script',
        help='Identificador do executor (registrado em CarviaAdminAudit)'
    )
    args = parser.parse_args()

    if len(args.motivo) < 10:
        print("ERRO: motivo precisa ter no minimo 10 caracteres.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        # BEFORE
        total_before = db.session.execute(
            text("SELECT COUNT(*) FROM carvia_subcontratos")
        ).scalar()
        orfaos_before = db.session.execute(
            text("""
                SELECT COUNT(*) FROM carvia_subcontratos
                WHERE frete_id IS NULL AND fatura_transportadora_id IS NULL
                  AND status NOT IN ('FATURADO', 'CONFERIDO')
            """)
        ).scalar()
        print(f"BEFORE: {total_before} subcontratos no total, {orfaos_before} orfaos candidatos")

        if args.execute:
            executar(args.motivo, args.executor)

            # AFTER (so faz sentido apos execucao real)
            total_after = db.session.execute(
                text("SELECT COUNT(*) FROM carvia_subcontratos")
            ).scalar()
            orfaos_after = db.session.execute(
                text("""
                    SELECT COUNT(*) FROM carvia_subcontratos
                    WHERE frete_id IS NULL AND fatura_transportadora_id IS NULL
                      AND status NOT IN ('FATURADO', 'CONFERIDO')
                """)
            ).scalar()
            print(f"\nAFTER:  {total_after} subcontratos no total, {orfaos_after} orfaos restantes")
        else:
            print("\n[DRY-RUN] Nenhuma mudanca sera aplicada. Use --execute para rodar.\n")
            candidatos = listar_candidatos()
            imprimir_tabela(candidatos)


if __name__ == '__main__':
    main()

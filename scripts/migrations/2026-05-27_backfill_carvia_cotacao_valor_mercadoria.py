"""
Data fix: corrige valor_mercadoria inflado em CarviaCotacao + status ABERTO em
CarviaPedido com NF ativa.

Data: 2026-05-27
Bug original:
  1. app/carvia/routes/cotacao_v2_routes.py:_agregar_totais_nfs_cotacao +
     api_anexar_nf_cotacao somavam CarviaNf.valor_total (valor INFLADO com
     impostos/frete/etc) em vez de soma de CarviaPedidoItem.valor_total
     (valor de mercadoria). Resultado: cotacoes ficaram com valor_mercadoria
     maior que a soma real dos pedidos, gerando linhas COT- duplicadas com
     PED- na VIEW mv_pedidos (parte 2A: saldo residual > 0,01).

  2. app/carvia/routes/cotacao_v2_routes.py wizard POST /carvia/cotacoes
     (linhas 1196-1365) e pedido_routes.py api_anexar_nf_pedido criavam pedidos
     com numero_nf preenchido mas nao chamavam o hook
     atualizar_status_pedido_carvia_pelo_faturamento. Pedidos ficaram com
     status='ABERTO' mesmo com NF ativa.

Este backfill (idempotente):
  A. Recalcula valor_mercadoria das cotacoes afetadas usando soma real de
     CarviaPedidoItem.valor_total (mercadoria, sem impostos).
  B. Atualiza status='FATURADO' onde TODOS os itens do pedido tem NF e a NF
     esta ATIVA em CarviaNf.

Reexecucao: SAFE — usa filtros que so atualizam registros com inconsistencia.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        from sqlalchemy import text

        print('\n=== PARTE A: Recalcular valor_mercadoria das cotacoes ===')

        # Identificar cotacoes onde valor_mercadoria > soma_real_pedidos
        cotacoes_inflados = db.session.execute(text("""
            WITH soma_real AS (
                SELECT
                    p.cotacao_id,
                    SUM(pi.valor_total) AS soma_itens
                FROM carvia_pedidos p
                JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
                WHERE p.status != 'CANCELADO'
                  AND pi.numero_nf IS NOT NULL
                  AND pi.numero_nf != ''
                GROUP BY p.cotacao_id
            )
            SELECT
                c.id,
                c.numero_cotacao,
                c.valor_mercadoria AS valor_atual,
                sr.soma_itens AS valor_real
            FROM carvia_cotacoes c
            JOIN soma_real sr ON sr.cotacao_id = c.id
            WHERE c.valor_mercadoria > sr.soma_itens + 0.01
              AND c.status NOT IN ('CANCELADO', 'CANCELADA')
            ORDER BY (c.valor_mercadoria - sr.soma_itens) DESC
        """)).fetchall()

        print(f'[INFO] Cotacoes inflados: {len(cotacoes_inflados)}')

        cotacoes_corrigidos = 0
        for row in cotacoes_inflados:
            cot_id = row.id
            cot_num = row.numero_cotacao
            atual = float(row.valor_atual)
            real = float(row.valor_real)
            print(f'  [{cot_num}] valor_mercadoria {atual:,.2f} -> {real:,.2f} (-{atual - real:,.2f})')
            db.session.execute(
                text("""
                    UPDATE carvia_cotacoes
                    SET valor_mercadoria = :valor_real
                    WHERE id = :cot_id
                """),
                {'cot_id': cot_id, 'valor_real': real}
            )
            cotacoes_corrigidos += 1

        if cotacoes_corrigidos > 0:
            db.session.commit()
            print(f'[COMMIT A] {cotacoes_corrigidos} cotacoes atualizadas')
        else:
            print('[NOOP A] Nenhuma cotacao inflada encontrada')

        print('\n=== PARTE B: Atualizar status ABERTO -> FATURADO ===')

        # Identificar pedidos com status='ABERTO' onde TODOS os itens tem NF preenchida
        # e pelo menos UMA dessas NFs esta ATIVA em CarviaNf.
        pedidos_aberto_com_nf = db.session.execute(text("""
            SELECT
                p.id AS pedido_id,
                p.numero_pedido,
                p.cotacao_id,
                COUNT(pi.id) AS qtd_itens,
                COUNT(pi.numero_nf) FILTER (
                    WHERE pi.numero_nf IS NOT NULL AND pi.numero_nf != ''
                ) AS itens_com_nf
            FROM carvia_pedidos p
            JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
            WHERE p.status = 'ABERTO'
            GROUP BY p.id, p.numero_pedido, p.cotacao_id
            HAVING COUNT(pi.id) > 0
               AND COUNT(pi.numero_nf) FILTER (
                   WHERE pi.numero_nf IS NOT NULL AND pi.numero_nf != ''
               ) = COUNT(pi.id)
        """)).fetchall()

        print(f'[INFO] Pedidos candidatos a FATURADO: {len(pedidos_aberto_com_nf)}')

        pedidos_corrigidos = 0
        for row in pedidos_aberto_com_nf:
            pid = row.pedido_id
            pnum = row.numero_pedido

            # Validar que pelo menos UMA NF do pedido esta ATIVA
            nf_ativa_count = db.session.execute(
                text("""
                    SELECT COUNT(DISTINCT cn.id)
                    FROM carvia_pedido_itens pi
                    JOIN carvia_nfs cn ON cn.numero_nf = pi.numero_nf
                    WHERE pi.pedido_id = :pid
                      AND cn.status = 'ATIVA'
                """),
                {'pid': pid}
            ).scalar()

            if not nf_ativa_count or nf_ativa_count == 0:
                print(f'  [SKIP] {pnum}: nenhuma NF ATIVA — mantem ABERTO')
                continue

            db.session.execute(
                text("""
                    UPDATE carvia_pedidos
                    SET status = 'FATURADO', atualizado_em = NOW()
                    WHERE id = :pid AND status = 'ABERTO'
                """),
                {'pid': pid}
            )
            print(f'  [OK] {pnum} ABERTO -> FATURADO ({nf_ativa_count} NF(s) ATIVA(s))')
            pedidos_corrigidos += 1

        if pedidos_corrigidos > 0:
            db.session.commit()
            print(f'[COMMIT B] {pedidos_corrigidos} pedidos atualizados')
        else:
            print('[NOOP B] Nenhum pedido para atualizar')

        print('\n=== RESUMO ===')
        print(f'  Cotacoes corrigidas: {cotacoes_corrigidos}')
        print(f'  Pedidos corrigidos:  {pedidos_corrigidos}')


if __name__ == '__main__':
    main()

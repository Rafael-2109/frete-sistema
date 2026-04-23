"""Backfill: alinhar carvia_cotacoes.valor_mercadoria com soma dos itens (vProd).

Contexto (2026-04-23):
- Criar cotacao via NF populava valor_mercadoria com NF.valor_total (vNF, inclui
  IPI/frete/seguro). Os pedido_itens recebem valor_total_item = vProd por item.
- Isso gera residual (vNF - vProd) que aparece como "sobra" no provisorio/VIEW
  pedidos. Ver COT-55..59 (COT-56/57/58 tinham sobra de R$ 41,79/42,58/37,93).
- Fix aplicado no JS (criar.js -> atualizarTotaisNfs soma itens em vez de vNF).
- Este script normaliza as cotacoes ja criadas + EmbarqueItem + CarviaFrete.

Seguro de rodar multiplas vezes (idempotente).
Rodar localmente: python scripts/migrations/backfill_cot_valor_mercadoria_vprod.py
Rodar em prod (Render Shell): mesmo comando apos deploy.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app, db  # noqa: E402


def backfill():
    app = create_app()
    with app.app_context():
        # 1. Cotacoes com valor_mercadoria != soma dos pedido_itens
        # Inclui flag se algum embarque da cotacao ja saiu (data_embarque preenchida).
        divergentes = db.session.execute(db.text("""
            SELECT c.id, c.numero_cotacao,
                   c.valor_mercadoria AS atual,
                   COALESCE((SELECT SUM(pi.valor_total)
                    FROM carvia_pedidos p
                    JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
                    WHERE p.cotacao_id = c.id), 0) AS soma_itens,
                   EXISTS (
                    SELECT 1 FROM embarque_itens ei
                    JOIN embarques e ON e.id = ei.embarque_id
                    WHERE ei.carvia_cotacao_id = c.id
                      AND ei.status = 'ativo'
                      AND e.data_embarque IS NOT NULL
                   ) AS embarque_saiu
            FROM carvia_cotacoes c
            WHERE c.status NOT IN ('CANCELADO')
              AND c.valor_mercadoria IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM carvia_pedidos p2
                JOIN carvia_pedido_itens pi2 ON pi2.pedido_id = p2.id
                WHERE p2.cotacao_id = c.id
              )
            ORDER BY c.id
        """)).fetchall()

        seguros = []
        pulados = []
        for r in divergentes:
            atual = float(r.atual)
            novo = float(r.soma_itens)
            if abs(atual - novo) <= 0.01 or novo <= 0:
                continue
            delta = atual - novo
            # Casos PULADOS (exigem analise manual):
            # - delta NEGATIVO: valor_mercadoria < soma_itens (anomalia, nao e o padrao vNF/vProd)
            # - embarque JA SAIU: risco de alterar peso pos-frete
            motivo_pular = None
            if delta < -0.01:
                motivo_pular = 'delta negativo (anomalia — provavel edicao manual ou NF anexada pos-criacao)'
            elif r.embarque_saiu:
                motivo_pular = 'embarque ja saiu (data_embarque preenchida) — risco de alterar peso pos-frete'
            if motivo_pular:
                pulados.append((r.id, r.numero_cotacao, atual, novo, delta, motivo_pular))
            else:
                seguros.append((r.id, r.numero_cotacao, atual, novo, delta))

        print(f"[BACKFILL] Cotacoes seguras para atualizar: {len(seguros)}")
        for cid, num, atual, novo, delta in seguros:
            print(f"  {num} (id={cid}): {atual:.2f} -> {novo:.2f} (sobra={delta:.2f})")

        if pulados:
            print(f"\n[BACKFILL] Cotacoes PULADAS (revisar manualmente): {len(pulados)}")
            for cid, num, atual, novo, delta, motivo in pulados:
                print(f"  {num} (id={cid}): {atual:.2f} vs soma_itens={novo:.2f} (delta={delta:+.2f})")
                print(f"     MOTIVO: {motivo}")

        if not seguros:
            print("\n[BACKFILL] Nada a fazer em cotacoes seguras.")
            return

        resp = input(f"\nAtualizar {len(seguros)} cotacoes seguras + EI + CarviaFrete? [s/N]: ")
        if resp.strip().lower() != 's':
            print("[BACKFILL] Abortado.")
            return
        cots_para_atualizar = [(cid, num, atual, novo) for cid, num, atual, novo, _ in seguros]

        total_cots = 0
        total_eis = 0
        total_fretes = 0

        for cid, num, _atual, novo in cots_para_atualizar:
            # 1a. Atualizar valor_mercadoria da cotacao
            db.session.execute(
                db.text("UPDATE carvia_cotacoes SET valor_mercadoria = :v WHERE id = :id"),
                {'v': novo, 'id': cid},
            )
            total_cots += 1

            # 1b. Corrigir EmbarqueItem CARVIA-PED-* — peso = SOMA(NF.peso_bruto)
            # Pedido pode ter multiplos itens apontando para N NFs distintas.
            # Agregamos peso DISTINCT por NF antes pra evitar fanout em pedidos
            # com multiplos itens da mesma NF.
            eis_atualizados = db.session.execute(db.text("""
                UPDATE embarque_itens ei
                SET peso = sub.peso_total
                FROM (
                    SELECT 'CARVIA-PED-' || p.id::text AS lote_id,
                           SUM(n.peso_bruto) AS peso_total
                    FROM carvia_pedidos p
                    JOIN (
                        SELECT DISTINCT pedido_id, numero_nf
                        FROM carvia_pedido_itens
                        WHERE numero_nf IS NOT NULL AND numero_nf <> ''
                    ) pi ON pi.pedido_id = p.id
                    JOIN carvia_nfs n ON n.numero_nf = pi.numero_nf
                    WHERE p.cotacao_id = :cot_id
                    GROUP BY p.id
                ) sub
                WHERE ei.separacao_lote_id = sub.lote_id
                  AND ei.status = 'ativo'
                  AND ABS(COALESCE(ei.peso, 0) - COALESCE(sub.peso_total, 0)) > 0.001
            """), {'cot_id': cid}).rowcount
            total_eis += eis_atualizados

            # 1c. Corrigir CarviaFrete.peso_total — match por NF unica no frete.
            # Pula fretes multi-NF (numeros_nfs CSV) pra evitar match ambiguo.
            fretes_atualizados = db.session.execute(db.text("""
                UPDATE carvia_fretes cf
                SET peso_total = n.peso_bruto
                FROM carvia_nfs n
                WHERE cf.numeros_nfs = n.numero_nf
                  AND cf.numeros_nfs NOT LIKE '%,%'
                  AND cf.status = 'PENDENTE'
                  AND cf.fatura_cliente_id IS NULL
                  AND n.numero_nf IN (
                    SELECT DISTINCT pi.numero_nf
                    FROM carvia_pedidos p
                    JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
                    WHERE p.cotacao_id = :cot_id
                      AND pi.numero_nf IS NOT NULL
                      AND pi.numero_nf <> ''
                  )
                  AND ABS(COALESCE(cf.peso_total, 0) - COALESCE(n.peso_bruto, 0)) > 0.001
            """), {'cot_id': cid}).rowcount
            total_fretes += fretes_atualizados

            print(f"  [{num}] cotacao ok, {eis_atualizados} EI, {fretes_atualizados} CarviaFrete")

        db.session.commit()
        print(f"\n[BACKFILL] Commit ok. Totais: {total_cots} cotacoes, {total_eis} EI, {total_fretes} CarviaFrete")

        # Verificacao after
        print("\n[VERIFY] Cotacoes apos backfill:")
        for cid, _num, _atual, _novo in cots_para_atualizar:
            row = db.session.execute(db.text("""
                SELECT c.numero_cotacao, c.valor_mercadoria,
                       COALESCE((SELECT SUM(pi.valor_total)
                        FROM carvia_pedidos p
                        JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
                        WHERE p.cotacao_id = c.id), 0) AS soma_itens
                FROM carvia_cotacoes c WHERE c.id = :id
            """), {'id': cid}).first()
            if row:
                diff = abs(float(row.valor_mercadoria) - float(row.soma_itens))
                status = 'OK' if diff < 0.01 else f'DIVERGE {diff:.2f}'
                print(f"  {row.numero_cotacao}: valor={row.valor_mercadoria} soma_itens={row.soma_itens} [{status}]")


if __name__ == '__main__':
    backfill()

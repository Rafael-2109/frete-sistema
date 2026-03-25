"""
Migration: Criar tabela carvia_nf_veiculos + renomear numeracao cotacao/pedido.

Executar: python scripts/migrations/criar_tabela_carvia_nf_veiculos.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        # 1. Criar tabela carvia_nf_veiculos
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS carvia_nf_veiculos (
                id SERIAL PRIMARY KEY,
                nf_id INTEGER NOT NULL REFERENCES carvia_nfs(id) ON DELETE CASCADE,
                chassi VARCHAR(30) NOT NULL,
                modelo VARCHAR(100),
                cor VARCHAR(50),
                valor NUMERIC(15,2),
                ano VARCHAR(20),
                numero_motor VARCHAR(30),
                criado_em TIMESTAMP DEFAULT NOW()
            )
        """))
        db.session.execute(db.text(
            "CREATE INDEX IF NOT EXISTS ix_carvia_nf_veiculos_nf_id ON carvia_nf_veiculos(nf_id)"
        ))
        db.session.execute(db.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_nf_veiculo_chassi ON carvia_nf_veiculos(chassi)"
        ))
        print("Tabela carvia_nf_veiculos criada.")

        # 2. Renomear numeracao cotacoes: COT-XXX -> COT-{id}
        cotacoes = db.session.execute(db.text(
            "SELECT id, numero_cotacao FROM carvia_cotacoes ORDER BY id"
        )).fetchall()
        renomeadas = 0
        for cot_id, num in cotacoes:
            novo = f'COT-{cot_id}'
            if num != novo:
                db.session.execute(db.text(
                    "UPDATE carvia_cotacoes SET numero_cotacao = :novo WHERE id = :id"
                ), {'novo': novo, 'id': cot_id})
                renomeadas += 1
        print(f"Cotacoes renomeadas: {renomeadas}")

        # 3. Renomear numeracao pedidos: PED-CV-XXX -> PED-{cotacao_id}-{seq}
        pedidos = db.session.execute(db.text(
            "SELECT id, numero_pedido, cotacao_id FROM carvia_pedidos ORDER BY cotacao_id, id"
        )).fetchall()
        seq_por_cot = {}
        renomeados = 0
        for ped_id, num, cot_id in pedidos:
            seq = seq_por_cot.get(cot_id, 0) + 1
            seq_por_cot[cot_id] = seq
            novo = f'PED-{cot_id}-{seq}'
            if num != novo:
                db.session.execute(db.text(
                    "UPDATE carvia_pedidos SET numero_pedido = :novo WHERE id = :id"
                ), {'novo': novo, 'id': ped_id})
                renomeados += 1
        print(f"Pedidos renomeados: {renomeados}")

        db.session.commit()
        print("Migration concluida.")


if __name__ == '__main__':
    run()

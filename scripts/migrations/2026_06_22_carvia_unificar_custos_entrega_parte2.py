"""Migration de DADOS (one-shot, idempotente) PARTE 2: unifica custos de entrega
duplicados onde os DOIS lados ja tem vinculo financeiro fechado.

Mantem o lado Rafael (1, 7: CTe Comp FATURADO + emissao + operacao correta + PAGO),
transfere a FT 51 do lado Thalita (52, 53) para eles e deleta 52/53. Tambem
reclassifica o custo 21 (OUTROS -> GNRE_ICMS). A FT 51 mantem o total (180).

Logica SQL em 2026_06_22_carvia_unificar_custos_entrega_parte2.sql (SOT).
Idempotente. Uso:
    python scripts/migrations/2026_06_22_carvia_unificar_custos_entrega_parte2.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402
from app import create_app, db  # noqa: E402

SQL_FILE = os.path.join(
    os.path.dirname(__file__),
    '2026_06_22_carvia_unificar_custos_entrega_parte2.sql',
)


def _scalar(sql, **p):
    return db.session.execute(text(sql), p).scalar()


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        ft51_antes = _scalar(
            "SELECT string_agg(id::text||'='||valor::text, ',' ORDER BY id) "
            "FROM carvia_custos_entrega WHERE fatura_transportadora_id = 51")
        tipo21_antes = _scalar("SELECT tipo_custo FROM carvia_custos_entrega WHERE id = 21")
        print(f'ANTES: FT51 contem [{ft51_antes}] | custo21.tipo={tipo21_antes}')

        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()

        # --- validacoes ---
        c1_ft = _scalar("SELECT fatura_transportadora_id FROM carvia_custos_entrega WHERE id = 1")
        c1_frete = _scalar("SELECT frete_id FROM carvia_custos_entrega WHERE id = 1")
        c7_ft = _scalar("SELECT fatura_transportadora_id FROM carvia_custos_entrega WHERE id = 7")
        c7_frete = _scalar("SELECT frete_id FROM carvia_custos_entrega WHERE id = 7")
        tipo21 = _scalar("SELECT tipo_custo FROM carvia_custos_entrega WHERE id = 21")
        restam_52_53 = _scalar(
            "SELECT count(*) FROM carvia_custos_entrega WHERE id IN (52, 53)")
        ft51_depois = _scalar(
            "SELECT string_agg(id::text||'='||valor::text, ',' ORDER BY id) "
            "FROM carvia_custos_entrega WHERE fatura_transportadora_id = 51")
        ft51_soma = _scalar(
            "SELECT COALESCE(SUM(valor),0) FROM carvia_custos_entrega "
            "WHERE fatura_transportadora_id = 51")
        print(
            f'DEPOIS: custo1 FT={c1_ft} frete={c1_frete} | custo7 FT={c7_ft} frete={c7_frete} | '
            f'custo21.tipo={tipo21} | restam 52/53={restam_52_53} | FT51=[{ft51_depois}] soma={ft51_soma}')

        assert c1_ft == 51 and c1_frete == 135, 'Custo 1 nao recebeu FT 51 / frete 135'
        assert c7_ft == 51 and c7_frete == 115, 'Custo 7 nao recebeu FT 51 / frete 115'
        assert tipo21 == 'GNRE_ICMS', 'Custo 21 nao reclassificado'
        assert restam_52_53 == 0, 'Duplicatas 52/53 nao deletadas'
        assert float(ft51_soma) == 180.00, f'FT 51 mudou de total! soma={ft51_soma} (esperado 180.00)'
        print('OK — parte 2 unificada (1<-52, 7<-53, 21->GNRE); FT 51 preservada em 180,00.')


if __name__ == '__main__':
    main()

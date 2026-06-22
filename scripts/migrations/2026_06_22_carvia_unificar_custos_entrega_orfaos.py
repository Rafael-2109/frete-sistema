"""Migration de DADOS (one-shot, idempotente): unifica Custos de Entrega CarVia duplicados.

Contexto: custos 54-58 nasceram orfaos de operacao (criados pela tela "por frete" em
19/05, quando frete.operacao_id ainda era NULL) e foram recriados em 22/06 (ids 78-82)
com operacao+fornecedor. Os ANTIGOS carregam o vinculo de Fatura Transportadora
(IRREVERSIVEL: FT 63 PAGA, FT 64 CONFERIDA) -> sobrevivem e recebem operacao+fornecedor;
os NOVOS sao deletados. Caso 77: re-vincula do CTe Comp 30 (cancelado) para o 31 (emitido).

Logica SQL em 2026_06_22_carvia_unificar_custos_entrega_orfaos.sql (SOT).
Idempotente. Uso:
    python scripts/migrations/2026_06_22_carvia_unificar_custos_entrega_orfaos.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402
from app import create_app, db  # noqa: E402

SQL_FILE = os.path.join(
    os.path.dirname(__file__),
    '2026_06_22_carvia_unificar_custos_entrega_orfaos.sql',
)

ANTIGOS = (54, 55, 56, 57, 58)
NOVOS = (78, 79, 80, 81, 82)


def _scalar(sql, **params):
    return db.session.execute(text(sql), params).scalar()


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        # --- ANTES ---
        orfaos = _scalar(
            "SELECT COUNT(*) FROM carvia_custos_entrega "
            "WHERE id IN :ids AND operacao_id IS NULL", ids=ANTIGOS,
        )
        novos = _scalar(
            "SELECT COUNT(*) FROM carvia_custos_entrega WHERE id IN :ids", ids=NOVOS,
        )
        cte77 = _scalar("SELECT cte_complementar_id FROM carvia_custos_entrega WHERE id = 77")
        print(f'ANTES: antigos orfaos (op IS NULL)={orfaos}/5 | duplicados novos presentes={novos}/5 | custo77.cte_comp={cte77}')

        # --- APLICA ---
        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()

        # --- DEPOIS + validacoes ---
        ainda_orfaos = _scalar(
            "SELECT COUNT(*) FROM carvia_custos_entrega "
            "WHERE id IN :ids AND operacao_id IS NULL", ids=ANTIGOS,
        )
        novos_restantes = _scalar(
            "SELECT COUNT(*) FROM carvia_custos_entrega WHERE id IN :ids", ids=NOVOS,
        )
        cte77_depois = _scalar("SELECT cte_complementar_id FROM carvia_custos_entrega WHERE id = 77")
        emissao23 = _scalar("SELECT custo_entrega_id FROM carvia_emissao_cte_complementar WHERE id = 23")
        anexo_54 = _scalar("SELECT COUNT(*) FROM carvia_custo_entrega_anexos WHERE custo_entrega_id = 54")
        anexo_57 = _scalar("SELECT COUNT(*) FROM carvia_custo_entrega_anexos WHERE custo_entrega_id = 57")
        print(
            f'DEPOIS: antigos orfaos={ainda_orfaos} (esp 0) | duplicados restantes={novos_restantes} (esp 0) | '
            f'custo77.cte_comp={cte77_depois} (esp 31) | emissao23.custo={emissao23} (esp 77) | '
            f'anexos[54]={anexo_54} anexos[57]={anexo_57}'
        )

        assert ainda_orfaos == 0, 'Ainda ha custos antigos sem operacao_id'
        assert novos_restantes == 0, 'Duplicados novos nao foram deletados'
        assert cte77_depois == 31, 'Custo 77 nao re-vinculado ao CTe Comp 31'
        assert emissao23 == 77, 'Emissao 23 (sucesso) nao amarrada ao custo 77'
        print('OK — custos de entrega unificados (5 pares + caso 77).')


if __name__ == '__main__':
    main()

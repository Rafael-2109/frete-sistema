"""Migration HORA 54: separa a permissao 'aprovacoes' de 'comissao' (#5b).

A aprovacao gerencial do pedido (desconto acima do teto, frete, brinde) deixou
de usar a permissao `comissao/aprovar` e passou a usar `aprovacoes/aprovar` —
'comissao' ficou so com config + relatorio. Esta migration faz o BACKFILL
idempotente: quem ja tinha comissao/aprovar recebe aprovacoes (ver + aprovar),
preservando o acesso dos gerentes atuais.

Sem DDL — hora_user_permissao.modulo ja e VARCHAR(40), 'aprovacoes' cabe.
Idempotente — ON CONFLICT (user_id, modulo) DO UPDATE.

Uso:
    python scripts/migrations/hora_54_aprovacoes_perm.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_BACKFILL = """
INSERT INTO hora_user_permissao
    (user_id, modulo, pode_ver, pode_criar, pode_editar, pode_apagar, pode_aprovar, atualizado_em)
SELECT user_id, 'aprovacoes', TRUE, FALSE, FALSE, FALSE, TRUE,
       (NOW() AT TIME ZONE 'America/Sao_Paulo')
FROM hora_user_permissao
WHERE modulo = 'comissao' AND pode_aprovar = TRUE
ON CONFLICT (user_id, modulo) DO UPDATE
    SET pode_ver = TRUE, pode_aprovar = TRUE,
        atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo')
"""

SQL_CONTA = (
    "SELECT COUNT(*) FROM hora_user_permissao "
    "WHERE modulo = :mod AND pode_aprovar = TRUE"
)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            origem = conn.execute(text(SQL_CONTA), {'mod': 'comissao'}).scalar()
            antes = conn.execute(text(SQL_CONTA), {'mod': 'aprovacoes'}).scalar()
            print(f'Origem (comissao/aprovar): {origem}')
            print(f'aprovacoes/aprovar antes:  {antes}')

            conn.execute(text(SQL_BACKFILL))

            depois = conn.execute(text(SQL_CONTA), {'mod': 'aprovacoes'}).scalar()
            print(f'aprovacoes/aprovar depois: {depois}')

        print('\nMigration HORA 54 concluida com sucesso.')


if __name__ == '__main__':
    main()

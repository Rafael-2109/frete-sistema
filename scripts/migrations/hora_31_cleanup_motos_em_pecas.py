"""Migration HORA 31: cleanup de motos cadastradas como peca pelo backfill TagPlus.

Causa-raiz: `executar_backfill_produtos_pecas` em
`app/hora/services/tagplus/backfill_service.py` pulava motos via
`ncm.startswith('8711')`, mas o TagPlus retorna NCM vazio em todos os produtos,
entao a heuristica nunca disparou e codigos MT-* (motos) foram cadastrados em
hora_peca + hora_tagplus_peca_map.

Limpeza em producao (2026-05-06):
  peca_id=6   MT-MC20            'Ciclomotor MC20 3000W'
  peca_id=207 MT-X12 10 - 18X    'Scooter Eletrica X12-10 1000w'

Ambos sem uso (zero pedidos, vendas, NFs de entrada, movimentos). Os outros 17
IDs originalmente reportados ja haviam sido removidos manualmente em sessao
anterior.

O fix da heuristica vai junto no commit (passa a olhar tambem
hora_tagplus_produto_map para detectar moto mesmo sem NCM).

Uso:
    python scripts/migrations/hora_31_cleanup_motos_em_pecas.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

IDS_PARA_LIMPAR = (6, 207)


def _contar(conn, tabela: str, coluna: str = 'id') -> set[int]:
    sql = text(
        f"SELECT {coluna} AS id FROM {tabela} WHERE {coluna} = ANY(:ids)"
    )
    rows = conn.execute(sql, {'ids': list(IDS_PARA_LIMPAR)}).fetchall()
    return {r.id for r in rows}


def _validar_zero_uso(conn) -> tuple[bool, list[str]]:
    """Garante que nenhum dos IDs tem uso transacional. Bloqueia DELETE se houver."""
    checks = [
        ('hora_pedido_item', 'peca_id'),
        ('hora_venda_item_peca', 'peca_id'),
        ('hora_nf_entrada_item_peca', 'peca_id'),
        ('hora_peca_movimento', 'peca_id'),
    ]
    erros: list[str] = []
    for tabela, coluna in checks:
        sql = text(
            f"SELECT COUNT(*) AS qtd FROM {tabela} WHERE {coluna} = ANY(:ids)"
        )
        qtd = conn.execute(sql, {'ids': list(IDS_PARA_LIMPAR)}).scalar() or 0
        if qtd:
            erros.append(f'{tabela}.{coluna} tem {qtd} registros referenciando IDs alvo')
    return (len(erros) == 0, erros)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            ids_peca_antes = _contar(conn, 'hora_peca')
            ids_map_antes = _contar(conn, 'hora_tagplus_peca_map', coluna='peca_id')

            print('Estado antes:')
            print(f'  hora_peca IDs alvo presentes: {sorted(ids_peca_antes)}')
            print(f'  hora_tagplus_peca_map IDs alvo presentes: {sorted(ids_map_antes)}')

            if not ids_peca_antes and not ids_map_antes:
                print('\nNada a remover (idempotente — alvos ja ausentes).')
                return

            ok, erros = _validar_zero_uso(conn)
            if not ok:
                print('\nABORTADO: IDs alvo possuem uso transacional:')
                for e in erros:
                    print(f'  - {e}')
                sys.exit(1)
            print('  uso transacional: 0 (seguro deletar)')

            removidos_map = conn.execute(
                text(
                    "DELETE FROM hora_tagplus_peca_map "
                    "WHERE peca_id = ANY(:ids) RETURNING peca_id"
                ),
                {'ids': list(IDS_PARA_LIMPAR)},
            ).fetchall()
            removidos_peca = conn.execute(
                text(
                    "DELETE FROM hora_peca "
                    "WHERE id = ANY(:ids) RETURNING id, codigo_interno"
                ),
                {'ids': list(IDS_PARA_LIMPAR)},
            ).fetchall()

            print('\nDeletes executados:')
            print(f'  hora_tagplus_peca_map: {len(removidos_map)} linhas '
                  f'(peca_ids={[r.peca_id for r in removidos_map]})')
            print(f'  hora_peca: {len(removidos_peca)} linhas '
                  f'(ids={[(r.id, r.codigo_interno) for r in removidos_peca]})')

        with db.engine.begin() as conn:
            ids_peca_depois = _contar(conn, 'hora_peca')
            ids_map_depois = _contar(conn, 'hora_tagplus_peca_map', coluna='peca_id')

        print('\nEstado depois:')
        print(f'  hora_peca IDs alvo presentes: {sorted(ids_peca_depois)}')
        print(f'  hora_tagplus_peca_map IDs alvo presentes: {sorted(ids_map_depois)}')

        if ids_peca_depois or ids_map_depois:
            print('\nERRO: IDs alvo ainda presentes apos DELETE.')
            sys.exit(1)

        print('\nMigration HORA 31 concluida com sucesso.')


if __name__ == '__main__':
    main()
